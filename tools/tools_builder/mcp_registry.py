# mcp_registry.py
# Manages MCP server connections and generates tool_definition-compatible
# entries that FunctionBuilder / ToolRegistry can absorb directly.
#
# KEY CONCEPTS
# ------------
# MCPServerConfig     — ONE connection to ONE server process. Registered once,
#                       shared across all affordances that reference it.
#                       Never duplicated — doing so would spin extra subprocesses.
#
# MCPAffordanceConfig — ONE tool_definitions entry. Multiple affordances can
#                       share a server_key with no extra connection cost.
#                       Controls tool filtering, availability gating, and
#                       how MCP prompts are surfaced to the agent.
#
#   Prompt handling (two distinct paths)
#   ─────────────────────────────────────
#   inject_prompts  — Parameterless prompts only. Called at context-build
#                     time; rendered text becomes agent_information. Prompts
#                     with required arguments are skipped with a warning.
#   prompt_tools    — Prompts WITH arguments exposed as callable tools.
#                     Arguments are converted to an OpenAI function-calling
#                     schema (all strings, per MCP spec). The agent calls
#                     these deliberately, just like any other tool.
#                     Collisions with an actual tool name raise an error.
#
# JSON config (mcp_config.json) — Drop-in compatible with Claude Desktop /
#                       Cursor format. Standard entries get always_available
#                       defaults. Power users can add an optional "affordance"
#                       block to any server entry for full gating control.
#                       Python-declared affordances always take precedence
#                       over JSON-declared ones if registry_keys clash.
#
# Transport notes
# ---------------
# stdio — discovered once at startup (subprocess opened, tools listed, closed).
#         Each tool call reopens a fresh subprocess. No persistent connection
#         held; avoids anyio task-group / asyncio.run() boundary errors.
# http  — persistent session kept alive in _exit_stack for the lifetime
#         of the registry. Server manages its own process.
#
# Drop this file at: tools/tools_builder/mcp_registry.py

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


# ---------------------------------------------------------------------------
# OS-agnostic command resolution
# ---------------------------------------------------------------------------

def _resolve_command(command: str) -> str:
    """
    Resolve a bare command name to its full path inside the active virtual-env
    (bin/ on Unix, Scripts/ on Windows), falling back to PATH lookup.

    Examples
    --------
    "npx"       → "npx"                                (on PATH wherever Node is installed)
    "colab-mcp" → "/venv/bin/colab-mcp"               (Unix)
                  "C:\\venv\\Scripts\\colab-mcp.exe"  (Windows)

    Absolute paths are returned unchanged.
    """
    if os.path.isabs(command):
        return command

    venv_bin = os.path.dirname(sys.executable)

    # On Windows executables may carry .exe or .cmd suffixes.
    candidates = (
        [command + ".exe", command + ".cmd", command]
        if sys.platform == "win32"
        else [command]
    )

    for candidate in candidates:
        full = os.path.join(venv_bin, candidate)
        if os.path.isfile(full):
            return full

    # Not found in venv — let the OS resolve via PATH.
    return command


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MCPServerConfig:
    """
    Defines ONE connection to ONE MCP server.
    Register once per server; share across as many affordances as needed.

    Fields
    ------
    server_key  — internal identity (e.g. "canva"). Must be unique.
    transport   — "stdio" (local subprocess) or "http" (remote / Docker).
    command     — executable for stdio (bare name or absolute path).
                  Automatically resolved via _resolve_command() for OS safety.
    args        — CLI arguments for stdio.
    env         — extra environment variables merged into the subprocess env.
    url         — endpoint URL for http transport.
    """
    server_key: str
    transport: Literal["stdio", "http"]

    # stdio
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None

    # http
    url: str | None = None

    def validate(self) -> None:
        if self.transport == "stdio" and not self.command:
            raise ValueError(
                f"MCPServerConfig '{self.server_key}': stdio transport requires 'command'."
            )
        if self.transport == "http" and not self.url:
            raise ValueError(
                f"MCPServerConfig '{self.server_key}': http transport requires 'url'."
            )

    @property
    def resolved_command(self) -> str | None:
        """OS-safe executable path. Always use this instead of self.command."""
        return _resolve_command(self.command) if self.command else None


@dataclass
class MCPAffordanceConfig:
    """
    Defines ONE tool_definitions entry over an already-connected server.

    Multiple affordances may reference the same server_key — no extra
    subprocess or session is created.

    Fields
    ------
    registry_key    — key in tool_definitions (e.g. "mcp_canvas_designer").
    server_key      — must match a connected MCPServerConfig.server_key.

    include_tools   — if non-empty, only these tool names are exposed.
                      Empty list (default) = all discovered tools exposed.
    exclude_tools   — tool names to suppress. Applied after include_tools.
                      Empty list (default) = nothing suppressed.

    inject_prompts  — Parameterless MCP prompt names. Rendered at
                      context-build time and surfaced as agent_information.
                      Prompts with required arguments are skipped with a warning.

    prompt_tools    — MCP prompt names WITH arguments to expose as callable
                      tools. Arguments become the function signature (all
                      strings, per MCP spec). The agent calls these
                      deliberately, just like any other tool.
                      Collision with an actual tool name raises an error at
                      registration time.

    item_types      — availability gating (mirrors hand-written tool entries).
    room_types      — availability gating.
    use_level       — "always_available" | "dual_use" | "room_only" | "inventory_only".
                      Defaults to "always_available" when not specified.
    """
    registry_key: str
    server_key: str

    include_tools:  list[str] = field(default_factory=list)
    exclude_tools:  list[str] = field(default_factory=list)
    inject_prompts: list[str] = field(default_factory=list)
    prompt_tools:   list[str] = field(default_factory=list)

    item_types: list[str] = field(default_factory=list)
    room_types: list[str] = field(default_factory=list)
    use_level:  str       = "always_available"


# ---------------------------------------------------------------------------
# JSON config loader — Claude Desktop / Cursor compatible
# ---------------------------------------------------------------------------

def _connection_fingerprint(entry: dict) -> str:
    """
    Derive a stable, unique key that identifies one physical server process.

    Two JSON entries with identical connection parameters (same command+args
    or same url) produce the same fingerprint and will share one connection.
    The entry name (registry_key) is intentionally excluded — it's an
    affordance-level concept, not a connection-level one.

    The fingerprint is a short hex digest so it is safe to use as a dict key
    and readable enough in log output.
    """
    import hashlib

    if "url" in entry:
        raw = f"http:{entry['url']}"
    else:
        cmd  = entry.get("command", "")
        args = "|".join(entry.get("args", []))
        # env is included because different env vars can meaningfully change
        # server behaviour (e.g. MYINSTANTS_VOLUME), so treat those as
        # distinct servers even if command+args match.
        env_str = ",".join(
            f"{k}={v}" for k, v in sorted((entry.get("env") or {}).items())
        )
        raw = f"stdio:{cmd}:{args}:{env_str}"

    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def load_json_configs(
    config_path: str | Path | None = None,
) -> tuple[list[MCPServerConfig], list[MCPAffordanceConfig]]:
    """
    Parse mcp_config.json and return (server_configs, affordance_configs).

    Connection pooling
    ------------------
    Multiple JSON entries that share identical connection parameters
    (same command+args+env, or same url) are automatically pooled — only
    one MCPServerConfig is returned for them, and all their affordances
    point at the same server_key. No extra subprocess or session is opened.

    This means the canva_designer / canva_assets split that previously
    required repeating the connection block now works correctly from JSON:
    both entries produce separate affordances that share one connection.

    Standard format  (Claude Desktop / Cursor compatible — works as-is)
    --------------------------------------------------------------------
    {
        "mcpServers": {
            "my_server": {
                "command": "npx",
                "args": ["-y", "some-mcp-package"],
                "env": { "KEY": "value" }
            },
            "remote_server": {
                "url": "http://localhost:8080/mcp"
            }
        }
    }

    Extended format  (optional "affordance" block per server)
    ----------------------------------------------------------
    {
        "mcpServers": {
            "canva_designer": {
                "url": "http://localhost:9090/mcp",
                "affordance": {
                    "use_level":     "room_only",
                    "item_types":    ["canvas_designer_station"],
                    "include_tools": ["create_design", "add_element"]
                }
            },
            "canva_assets": {
                "url": "http://localhost:9090/mcp",
                "affordance": {
                    "use_level":     "dual_use",
                    "item_types":    ["canvas_asset_terminal"],
                    "include_tools": ["list_assets", "export_design"]
                }
            }
        }
    }
    Both canva_* entries share the same url → one connection, two affordances.

    Affordance field reference
    --------------------------
    All fields optional. Omitting the block gives always_available defaults.

      use_level      "always_available" | "dual_use" | "room_only" | "inventory_only"
      item_types     list[str]  agent must have/see an item of one of these types
      room_types     list[str]  agent must be in a matching room
      include_tools  list[str]  whitelist — omit or [] means ALL tools
      exclude_tools  list[str]  blacklist — applied after include, omit or [] = nothing hidden
      inject_prompts list[str]  parameterless MCP prompt names → agent_information
      prompt_tools   list[str]  MCP prompts with arguments → callable tools

    Priority
    --------
    Python-declared affordances in ToolRegistry always win over JSON-declared
    ones when registry_keys collide (handled in ToolRegistry._connect_mcp).

    Parameters
    ----------
    config_path
        Path to the JSON file. Defaults to mcp_config.json at the project root
        (two directories above this file).
    """
    if config_path is None:
        this_dir     = Path(__file__).resolve().parent
        project_root = this_dir.parent.parent      # tools/tools_builder/ → project root
        config_path  = project_root / "mcp_config.json"

    config_path = Path(config_path)
    if not config_path.exists():
        return [], []

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[MCP] WARNING: Could not parse {config_path.name}: {exc}")
        return [], []

    # fingerprint → MCPServerConfig  (deduplicated pool)
    server_pool:        dict[str, MCPServerConfig]    = {}
    affordance_configs: list[MCPAffordanceConfig]     = []

    for name, entry in raw.get("mcpServers", {}).items():
        # Skip comment-only keys (JSON doesn't have real comments)
        if name.startswith("_"):
            continue

        fingerprint = _connection_fingerprint(entry)

        # --- Build MCPServerConfig only if this connection is new ---
        if fingerprint not in server_pool:
            try:
                if "url" in entry:
                    server_cfg = MCPServerConfig(
                        server_key = fingerprint,
                        transport  = "http",
                        url        = entry["url"],
                    )
                else:
                    server_cfg = MCPServerConfig(
                        server_key = fingerprint,
                        transport  = "stdio",
                        command    = entry.get("command", ""),
                        args       = entry.get("args", []),
                        env        = entry.get("env") or None,
                    )
                server_cfg.validate()
                server_pool[fingerprint] = server_cfg
                print(f"[MCP] New server connection pooled as '{fingerprint}' (first seen via '{name}').")
            except Exception as exc:
                print(f"[MCP] WARNING: Skipping '{name}' in {config_path.name}: {exc}")
                continue
        else:
            print(f"[MCP] '{name}' shares connection with existing pool entry '{fingerprint}' — no extra process.")

        # --- Affordance config (always one per named entry) ---
        aff_raw = entry.get("affordance", {})
        affordance_configs.append(MCPAffordanceConfig(
            registry_key   = name,
            server_key     = fingerprint,          # points at the pooled connection
            use_level      = aff_raw.get("use_level",      "always_available"),
            item_types     = aff_raw.get("item_types",     []),
            room_types     = aff_raw.get("room_types",     []),
            include_tools  = aff_raw.get("include_tools",  []),
            exclude_tools  = aff_raw.get("exclude_tools",  []),
            inject_prompts = aff_raw.get("inject_prompts", []),
            prompt_tools   = aff_raw.get("prompt_tools",   []),
        ))

        suffix = f" (affordance: {aff_raw})" if aff_raw else " (default affordance)"
        print(f"[MCP] Affordance '{name}' registered{suffix}.")

    return list(server_pool.values()), affordance_configs


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

async def _safe_list_prompts(session) -> list:
    """
    Call list_prompts on a connected session and return the prompt list.
    Returns [] if the server doesn't implement the prompts capability —
    'Method not found' is a normal MCP response meaning no prompt support.
    """
    try:
        result = await session.list_prompts()
        return result.prompts
    except Exception as exc:
        if "method not found" not in str(exc).lower():
            print(f"[MCP] WARNING: list_prompts failed unexpectedly: {exc}")
        return []


def _prompt_to_definition(prompt) -> dict:
    """
    Convert an MCP prompt object to an OpenAI function-calling definition.

    MCP spec: all prompt arguments are strings. Optional arguments are
    marked non-required and noted as optional in their description.
    """
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
                        "Renders a parameterized prompt template from the MCP server."),
        "parameters": {
            "type":       "object",
            "properties": props,
            "required":   required,
        },
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class MCPRegistry:
    """
    Manages MCP server connections and affordance entry construction.

    Typical usage (inside ToolRegistry._connect_mcp)
    -------------------------------------------------
    registry = MCPRegistry()

    # Phase 1 — one connection per physical server
    for server_cfg in server_configs:
        await registry.connect_server(server_cfg)

    # Phase 2 — one tool_definitions entry per affordance
    for affordance in affordance_configs:
        if registry.is_connected(affordance.server_key):
            entry = registry.build_affordance_entry(affordance)
            tool_definitions[affordance.registry_key] = entry
    """

    def __init__(self) -> None:
        self._exit_stack:     AsyncExitStack             = AsyncExitStack()
        self._sessions:       dict[str, ClientSession]   = {}   # http only
        self._tool_cache:     dict[str, list]            = {}   # server_key → tools
        self._prompt_cache:   dict[str, list]            = {}   # server_key → prompts
        self._server_configs: dict[str, MCPServerConfig] = {}

    # ------------------------------------------------------------------
    # Phase 1 — connect servers
    # ------------------------------------------------------------------

    async def connect_server(self, config: MCPServerConfig) -> None:
        """
        Discover tools from one MCP server and cache them.

        stdio — opens subprocess, lists tools, closes. No session stored.
        http  — opens a persistent session managed by _exit_stack.
        """
        config.validate()

        if config.transport == "stdio":
            params = StdioServerParameters(
                command=config.resolved_command,
                args=config.args,
                env=config.env,
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tool_list   = await session.list_tools()
                    prompt_list = await _safe_list_prompts(session)
                    self._tool_cache[config.server_key]     = tool_list.tools
                    self._prompt_cache[config.server_key]   = prompt_list
                    self._server_configs[config.server_key] = config

        else:  # http
            read, write, _ = await self._exit_stack.enter_async_context(
                streamablehttp_client(config.url)
            )
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

        tool_names   = [t.name for t in self._tool_cache[config.server_key]]
        prompt_names = [p.name for p in self._prompt_cache[config.server_key]]
        print(f"[MCP] Connected '{config.server_key}' ({config.transport}): "
              f"tools={tool_names} prompts={prompt_names}")

    # ------------------------------------------------------------------
    # Phase 2 — build affordance entries
    # ------------------------------------------------------------------

    def build_affordance_entry(self, affordance: MCPAffordanceConfig) -> dict:
        """
        Return a tool_definitions-compatible dict for one affordance.

        Tool filtering
        --------------
        include_tools empty AND exclude_tools empty → all tools exposed (common case).
        include_tools non-empty                     → only listed tools exposed.
        exclude_tools non-empty                     → listed tools removed (after include).

        Prompt handling
        ---------------
        inject_prompts → parameterless prompts only, rendered as agent_information.
                         Prompts with required arguments are skipped with a warning.
        prompt_tools   → prompts with arguments exposed as callable tools alongside
                         regular tools. Collision with an actual tool name is an error.
        """
        server_key = affordance.server_key
        if server_key not in self._tool_cache:
            raise RuntimeError(
                f"Server '{server_key}' not connected. "
                "Call connect_server() before build_affordance_entry()."
            )

        all_tools     = self._tool_cache[server_key]
        all_prompts   = self._prompt_cache.get(server_key, [])
        server_config = self._server_configs[server_key]

        # --- Tool filtering ---
        tools = all_tools
        if affordance.include_tools:
            include_set = set(affordance.include_tools)
            tools = [t for t in tools if t.name in include_set]
        if affordance.exclude_tools:
            exclude_set = set(affordance.exclude_tools)
            tools = [t for t in tools if t.name not in exclude_set]

        # --- Tool callables + definitions ---
        functions: dict = {
            t.name: self._make_caller(server_config, t.name)
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

        # --- prompt_tools: prompts with arguments → callable tools ---
        if affordance.prompt_tools:
            prompt_map = {p.name: p for p in all_prompts}
            for pt_name in affordance.prompt_tools:
                if pt_name not in prompt_map:
                    print(f"[MCP] WARNING: prompt_tool '{pt_name}' not found on "
                          f"server '{server_key}' — skipping.")
                    continue
                if pt_name in functions:
                    raise RuntimeError(
                        f"[MCP] '{affordance.registry_key}': prompt_tool '{pt_name}' "
                        f"collides with an actual tool of the same name on server "
                        f"'{server_key}'. Rename one of them."
                    )
                p_args = getattr(prompt_map[pt_name], "arguments", None) or []
                functions[pt_name] = self._make_prompt_caller(server_config, pt_name)
                definitions.append(_prompt_to_definition(prompt_map[pt_name]))
                print(f"[MCP] '{affordance.registry_key}': prompt '{pt_name}' "
                      f"registered as tool ({len(p_args)} arg(s)).")

        # --- inject_prompts: parameterless prompts → agent_information ---
        agent_info_fn = None
        if affordance.inject_prompts:
            prompt_map   = {p.name: p for p in all_prompts}
            valid_names: list[str] = []
            for inj_name in affordance.inject_prompts:
                if inj_name not in prompt_map:
                    print(f"[MCP] WARNING: inject_prompt '{inj_name}' not found on "
                          f"server '{server_key}' — skipping.")
                    continue
                p_args   = getattr(prompt_map[inj_name], "arguments", None) or []
                required = [a for a in p_args if getattr(a, "required", False)]
                if required:
                    req_names = [a.name for a in required]
                    print(f"[MCP] WARNING: inject_prompt '{inj_name}' has required "
                          f"arguments {req_names} — cannot inject without values. "
                          f"Use prompt_tools instead. Skipping.")
                    continue
                valid_names.append(inj_name)

            if valid_names:
                _names      = valid_names
                _server_cfg = server_config

                async def agent_info_fn() -> str:
                    parts = []
                    for prompt_name in _names:
                        try:
                            text = await self._call_get_prompt(_server_cfg, prompt_name)
                            parts.append(f"[{prompt_name}]\n{text}")
                        except Exception as exc:
                            parts.append(f"[{prompt_name}] (unavailable: {exc})")
                    return "\n\n".join(parts)

        # --- Assemble entry ---
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


        print(f"[MCP BUILD DEBUG] {affordance.registry_key} functions: {[(k, type(v).__name__) for k,v in functions.items()]}")

        return entry

    # ------------------------------------------------------------------
    # Caller factories
    # ------------------------------------------------------------------
    def _make_caller(self, config: MCPServerConfig, tool_name: str):
        """
        Return an async callable for one tool.
        http  — reuses the persistent session (no subprocess overhead).
        stdio — opens a fresh subprocess per call (stateless, safe across
                the asyncio.run() boundary).
        """
        if config.transport == "http":
            session = self._sessions[config.server_key]

            async def _http_caller(**kwargs) -> str:
                result = await session.call_tool(tool_name, arguments=kwargs)
                parts = []
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

            _http_caller.__name__ = tool_name
            return _http_caller

        else:  # stdio — fresh subprocess per call
            params = StdioServerParameters(
                command=config.resolved_command,
                args=config.args,
                env=config.env,
            )
            
            async def _stdio_caller(**kwargs) -> str:
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments=kwargs)
                        parts = []
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

            _stdio_caller.__name__ = tool_name
            return _stdio_caller

    def _make_prompt_caller(self, config: MCPServerConfig, prompt_name: str):
        """
        Return an async callable that renders an MCP prompt with arguments.
        Accepts **kwargs matching the prompt's argument list (all coerced to str).
        Returns the rendered messages joined as a single string.
        """
        if config.transport == "http":
            session = self._sessions[config.server_key]

            async def _http_prompt_caller(**kwargs) -> str:
                str_args = {k: str(v) for k, v in kwargs.items()}
                result   = await session.get_prompt(prompt_name, arguments=str_args)
                parts    = [
                    msg.content.text
                    for msg in result.messages
                    if hasattr(msg.content, "text") and msg.content.text
                ]
                return "\n".join(parts) if parts else "(empty prompt response)"

            _http_prompt_caller.__name__ = prompt_name
            return _http_prompt_caller

        else:  # stdio — fresh subprocess per call
            params = StdioServerParameters(
                command=config.resolved_command,
                args=config.args,
                env=config.env,
            )

            async def _stdio_prompt_caller(**kwargs) -> str:
                str_args = {k: str(v) for k, v in kwargs.items()}
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.get_prompt(prompt_name, arguments=str_args)
                        parts  = [
                            msg.content.text
                            for msg in result.messages
                            if hasattr(msg.content, "text") and msg.content.text
                        ]
                        return "\n".join(parts) if parts else "(empty prompt response)"

            _stdio_prompt_caller.__name__ = prompt_name
            return _stdio_prompt_caller

    # ------------------------------------------------------------------
    # Prompt helper (used by inject_prompts)
    # ------------------------------------------------------------------

    async def _call_get_prompt(self, config: MCPServerConfig, prompt_name: str) -> str:
        """Fetch a named prompt from the server."""
        if config.transport == "http":
            session = self._sessions[config.server_key]
            result  = await session.get_prompt(prompt_name, arguments={})
        else:
            params = StdioServerParameters(
                command=config.resolved_command,
                args=config.args,
                env=config.env,
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.get_prompt(prompt_name, arguments={})

        parts = [
            msg.content.text
            for msg in result.messages
            if hasattr(msg.content, "text") and msg.content.text
        ]
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def is_connected(self, server_key: str) -> bool:
        return server_key in self._tool_cache

    async def close(self) -> None:
        """Close persistent http sessions. stdio has no sessions to close."""
        await self._exit_stack.aclose()
        self._sessions.clear()
        self._tool_cache.clear()
        self._prompt_cache.clear()
        self._server_configs.clear()
        print("[MCP] All sessions closed.")