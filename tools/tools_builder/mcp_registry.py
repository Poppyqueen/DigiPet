"""
mcp_registry.py
---------------
Manages MCP server connections and generates tool_definition-compatible
entries that FunctionBuilder / ToolRegistry can absorb directly.

All async work runs on the persistent mcp_loop from async_loop.py.
Sessions (both stdio and http) are kept alive in _exit_stack for the
lifetime of the registry — no more fresh-subprocess-per-call workaround.

Transport notes
---------------
stdio — persistent subprocess kept alive via stdio_client in _exit_stack.
        One process per server for the game session. Clean shutdown via close().
http  — persistent session kept alive in _exit_stack. Same pattern as stdio.

Both transports now use identical caller factories — the stdio/http distinction
only matters during connect_server().
"""

from __future__ import annotations

import json
import os
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from pygame_runtime.async_loop import mcp_loop


# ---------------------------------------------------------------------------
# OS-agnostic command resolution  (unchanged)
# ---------------------------------------------------------------------------

def _resolve_command(command: str) -> str:
    if os.path.isabs(command):
        return command
    venv_bin   = os.path.dirname(sys.executable)
    candidates = (
        [command + ".exe", command + ".cmd", command]
        if sys.platform == "win32"
        else [command]
    )
    for candidate in candidates:
        full = os.path.join(venv_bin, candidate)
        if os.path.isfile(full):
            return full
    return command


# ---------------------------------------------------------------------------
# Data classes  (unchanged)
# ---------------------------------------------------------------------------

@dataclass
class MCPServerConfig:
    server_key: str
    transport:  Literal["stdio", "http"]
    command:    str | None        = None
    args:       list[str]         = field(default_factory=list)
    env:        dict[str, str] | None = None
    url:        str | None        = None

    def validate(self) -> None:
        if self.transport == "stdio" and not self.command:
            raise ValueError(f"MCPServerConfig '{self.server_key}': stdio requires 'command'.")
        if self.transport == "http" and not self.url:
            raise ValueError(f"MCPServerConfig '{self.server_key}': http requires 'url'.")

    @property
    def resolved_command(self) -> str | None:
        return _resolve_command(self.command) if self.command else None


@dataclass
class MCPAffordanceConfig:
    registry_key:   str
    server_key:     str
    include_tools:  list[str] = field(default_factory=list)
    exclude_tools:  list[str] = field(default_factory=list)
    inject_prompts: list[str] = field(default_factory=list)
    prompt_tools:   list[str] = field(default_factory=list)
    item_types:     list[str] = field(default_factory=list)
    room_types:     list[str] = field(default_factory=list)
    use_level:      str       = "always_available"


# ---------------------------------------------------------------------------
# JSON config loader  (unchanged from your version)
# ---------------------------------------------------------------------------

def _connection_fingerprint(entry: dict) -> str:
    import hashlib
    if "url" in entry:
        raw = f"http:{entry['url']}"
    else:
        cmd     = entry.get("command", "")
        args    = "|".join(entry.get("args", []))
        env_str = ",".join(
            f"{k}={v}" for k, v in sorted((entry.get("env") or {}).items())
        )
        raw = f"stdio:{cmd}:{args}:{env_str}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def load_json_configs(
    config_path: str | Path | None = None,
) -> tuple[list[MCPServerConfig], list[MCPAffordanceConfig]]:
    if config_path is None:
        this_dir     = Path(__file__).resolve().parent
        project_root = this_dir.parent.parent
        config_path  = project_root / "mcp_config.json"

    config_path = Path(config_path)
    if not config_path.exists():
        return [], []

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[MCP] WARNING: Could not parse {config_path.name}: {exc}")
        return [], []

    server_pool:        dict[str, MCPServerConfig]  = {}
    affordance_configs: list[MCPAffordanceConfig]   = []

    for name, entry in raw.get("mcpServers", {}).items():
        if name.startswith("_"):
            continue
        fingerprint = _connection_fingerprint(entry)
        if fingerprint not in server_pool:
            try:
                if "url" in entry:
                    server_cfg = MCPServerConfig(
                        server_key=fingerprint, transport="http", url=entry["url"]
                    )
                else:
                    server_cfg = MCPServerConfig(
                        server_key=fingerprint, transport="stdio",
                        command=entry.get("command", ""),
                        args=entry.get("args", []),
                        env=entry.get("env") or None,
                    )
                server_cfg.validate()
                server_pool[fingerprint] = server_cfg
                print(f"[MCP] New server pooled as '{fingerprint}' (via '{name}').")
            except Exception as exc:
                print(f"[MCP] WARNING: Skipping '{name}': {exc}")
                continue
        else:
            print(f"[MCP] '{name}' shares connection '{fingerprint}'.")

        aff_raw = entry.get("affordance", {})
        affordance_configs.append(MCPAffordanceConfig(
            registry_key   = name,
            server_key     = fingerprint,
            use_level      = aff_raw.get("use_level",      "always_available"),
            item_types     = aff_raw.get("item_types",     []),
            room_types     = aff_raw.get("room_types",     []),
            include_tools  = aff_raw.get("include_tools",  []),
            exclude_tools  = aff_raw.get("exclude_tools",  []),
            inject_prompts = aff_raw.get("inject_prompts", []),
            prompt_tools   = aff_raw.get("prompt_tools",   []),
        ))

    return list(server_pool.values()), affordance_configs


# ---------------------------------------------------------------------------
# Helpers  (unchanged)
# ---------------------------------------------------------------------------

async def _safe_list_prompts(session) -> list:
    try:
        result = await session.list_prompts()
        return result.prompts
    except Exception as exc:
        if "method not found" not in str(exc).lower():
            print(f"[MCP] WARNING: list_prompts failed: {exc}")
        return []


def _prompt_to_definition(prompt) -> dict:
    p_args   = getattr(prompt, "arguments", None) or []
    props    = {}
    required = []
    for arg in p_args:
        is_req = getattr(arg, "required", False)
        desc   = getattr(arg, "description", "") or ""
        if not is_req:
            desc = f"(optional) {desc}".strip()
        props[arg.name] = {"type": "string", "description": desc}
        if is_req:
            required.append(arg.name)
    return {
        "type":        "function",
        "name":        prompt.name,
        "description": (getattr(prompt, "description", "") or
                        "Renders a parameterized prompt template."),
        "parameters":  {"type": "object", "properties": props, "required": required},
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class MCPRegistry:
    """
    Manages MCP server connections and affordance entry construction.

    All sessions (stdio and http) are persistent, managed by _exit_stack,
    and live on the mcp_loop event loop. No fresh-subprocess-per-call.

    Usage (inside ToolRegistry._connect_mcp — now sync)
    ----------------------------------------------------
    registry = MCPRegistry()
    for server_cfg in server_configs:
        mcp_loop.run_sync(registry.connect_server(server_cfg))
    for affordance in affordance_configs:
        if registry.is_connected(affordance.server_key):
            entry = registry.build_affordance_entry(affordance)
            tool_definitions[affordance.registry_key] = entry
    """

    def __init__(self) -> None:
        self._exit_stack:     AsyncExitStack             = AsyncExitStack()
        self._sessions:       dict[str, ClientSession]   = {}
        self._tool_cache:     dict[str, list]            = {}
        self._prompt_cache:   dict[str, list]            = {}
        self._server_configs: dict[str, MCPServerConfig] = {}

    # ------------------------------------------------------------------
    # Phase 1 — connect servers
    # ------------------------------------------------------------------

    async def connect_server(self, config: MCPServerConfig) -> None:
        """
        Open a persistent session and cache tools + prompts.
        Both stdio and http now use _exit_stack — same pattern, same lifetime.

        Must be called via mcp_loop.run_sync() so the session is created
        on the persistent loop and stays there.
        """
        config.validate()

        if config.transport == "stdio":
            params = StdioServerParameters(
                command=config.resolved_command,
                args=config.args,
                env=config.env,
            )
            read, write = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )
        else:  # http
            read, write, _ = await self._exit_stack.enter_async_context(
                streamablehttp_client(config.url)
            )

        # Session setup is identical for both transports from here
        session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await session.initialize()

        tool_list   = await session.list_tools()
        prompt_list = await _safe_list_prompts(session)

        self._sessions[config.server_key]       = session
        self._tool_cache[config.server_key]     = tool_list.tools
        self._prompt_cache[config.server_key]   = prompt_list
        self._server_configs[config.server_key] = config

        tool_names   = [t.name for t in tool_list.tools]
        prompt_names = [p.name for p in prompt_list]
        print(f"[MCP] Connected '{config.server_key}' ({config.transport}): "
              f"tools={tool_names} prompts={prompt_names}")

    # ------------------------------------------------------------------
    # Phase 2 — build affordance entries  (sync, no change needed)
    # ------------------------------------------------------------------

    def build_affordance_entry(self, affordance: MCPAffordanceConfig) -> dict:
        """Unchanged — builds the tool_definitions entry from cached data."""
        server_key = affordance.server_key
        if server_key not in self._tool_cache:
            raise RuntimeError(f"Server '{server_key}' not connected.")

        all_tools   = self._tool_cache[server_key]
        all_prompts = self._prompt_cache.get(server_key, [])
        session     = self._sessions[server_key]

        # Tool filtering
        tools = all_tools
        if affordance.include_tools:
            include_set = set(affordance.include_tools)
            tools = [t for t in tools if t.name in include_set]
        if affordance.exclude_tools:
            exclude_set = set(affordance.exclude_tools)
            tools = [t for t in tools if t.name not in exclude_set]

        # Callables + definitions — now using the persistent session directly
        functions: dict = {
            t.name: self._make_caller(session, t.name)
            for t in tools
        }
        definitions: list = [
            {
                "type":        "function",
                "name":        t.name,
                "description": t.description or f"Tool from MCP server '{server_key}'.",
                "parameters":  t.inputSchema or {"type": "object", "properties": {}},
            }
            for t in tools
        ]

        # prompt_tools
        if affordance.prompt_tools:
            prompt_map = {p.name: p for p in all_prompts}
            for pt_name in affordance.prompt_tools:
                if pt_name not in prompt_map:
                    print(f"[MCP] WARNING: prompt_tool '{pt_name}' not found — skipping.")
                    continue
                if pt_name in functions:
                    raise RuntimeError(
                        f"[MCP] '{affordance.registry_key}': prompt_tool '{pt_name}' "
                        f"collides with an actual tool name."
                    )
                functions[pt_name]  = self._make_prompt_caller(session, pt_name)
                definitions.append(_prompt_to_definition(prompt_map[pt_name]))
                print(f"[MCP] '{affordance.registry_key}': prompt '{pt_name}' registered as tool.")

        # inject_prompts → agent_information
        agent_info_fn = None
        if affordance.inject_prompts:
            prompt_map  = {p.name: p for p in all_prompts}
            valid_names = []
            for inj_name in affordance.inject_prompts:
                if inj_name not in prompt_map:
                    print(f"[MCP] WARNING: inject_prompt '{inj_name}' not found — skipping.")
                    continue
                p_args   = getattr(prompt_map[inj_name], "arguments", None) or []
                required = [a for a in p_args if getattr(a, "required", False)]
                if required:
                    print(f"[MCP] WARNING: inject_prompt '{inj_name}' has required args "
                          f"{[a.name for a in required]} — use prompt_tools instead. Skipping.")
                    continue
                valid_names.append(inj_name)

            if valid_names:
                _session = session
                _names   = valid_names

                async def agent_info_fn() -> str:
                    parts = []
                    for prompt_name in _names:
                        try:
                            result = await _session.get_prompt(prompt_name, arguments={})
                            text   = "\n".join(
                                msg.content.text for msg in result.messages
                                if hasattr(msg.content, "text") and msg.content.text
                            )
                            parts.append(f"[{prompt_name}]\n{text}")
                        except Exception as exc:
                            parts.append(f"[{prompt_name}] (unavailable: {exc})")
                    return "\n\n".join(parts)

        entry: dict = {
            "functions":   functions,
            "definitions": definitions,
            "use_level":   affordance.use_level,
        }
        if affordance.item_types:
            entry["item_types"] = affordance.item_types
        if affordance.room_types:
            entry["room_types"] = affordance.room_types
        if agent_info_fn:
            entry["agent_information"]   = agent_info_fn
            entry["display_information"] = agent_info_fn

        return entry

    # ------------------------------------------------------------------
    # Caller factories — unified, session-based, no transport branching
    # ------------------------------------------------------------------

    def _make_caller(self, session: ClientSession, tool_name: str):
        async def _caller(**kwargs) -> str:
            result = await session.call_tool(tool_name, arguments=kwargs)
            parts  = []
            for b in result.content:
                if hasattr(b, "text") and b.text:
                    parts.append(b.text)
                elif hasattr(b, "resource"):
                    r = b.resource
                    if hasattr(r, "text") and r.text:
                        parts.append(r.text)
                    elif hasattr(r, "contents") and r.contents:
                        parts.append(str(r.contents))
            return "\n".join(parts) if parts else "(no output)"

        _caller.__name__ = tool_name
        _caller._is_mcp_caller = True      # ← marker
        return _caller

    def _make_prompt_caller(self, session: ClientSession, prompt_name: str):
        async def _prompt_caller(**kwargs) -> str:
            str_args = {k: str(v) for k, v in kwargs.items()}
            result   = await session.get_prompt(prompt_name, arguments=str_args)
            parts    = [
                msg.content.text for msg in result.messages
                if hasattr(msg.content, "text") and msg.content.text
            ]
            return "\n".join(parts) if parts else "(empty prompt response)"

        _prompt_caller.__name__ = prompt_name
        _prompt_caller._is_mcp_caller = True   # ← marker
        return _prompt_caller

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def is_connected(self, server_key: str) -> bool:
        return server_key in self._tool_cache

    async def close(self) -> None:
        """Close all sessions. Must be called via mcp_loop.run_sync()."""
        await self._exit_stack.aclose()
        self._sessions.clear()
        self._tool_cache.clear()
        self._prompt_cache.clear()
        self._server_configs.clear()
        print("[MCP] All sessions closed.")