# mcp_registry.py
# Manages MCP server connections and generates tool_definition-compatible
# entries that FunctionBuilder / ToolRegistry can absorb directly.
#
# stdio servers: connect briefly to discover tools, then close.
#                Each tool call opens a fresh subprocess connection.
# http servers:  persistent session for the lifetime of the registry.
#
# Drop this file at: tools/tools_builder/mcp_registry.py

from __future__ import annotations

from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Literal

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client


@dataclass
class MCPServerConfig:
    """
    Describes one MCP server and how it maps into the tool_definitions dict.

    registry_key  — the key used in tool_definitions, e.g. "mcp_reddit"
    transport     — "stdio" (local subprocess) or "http" (remote / Docker)

    stdio fields  — command + args + optional env vars
    http fields   — url pointing at the running server's MCP endpoint

    The availability fields (item_types, room_types, use_level) plug directly
    into ToolAvailabilityChecker — identical to any hand-written tool entry.
    Leave item_types and room_types empty to make the tools always available.
    """
    registry_key: str
    transport: Literal["stdio", "http"]

    # --- stdio-specific ---
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None

    # --- http-specific ---
    url: str | None = None

    # --- availability (mirrors existing tool_definitions conventions) ---
    item_types: list[str] = field(default_factory=list)
    room_types: list[str] = field(default_factory=list)
    use_level: str = "always_available"

    def validate(self) -> None:
        if self.transport == "stdio" and not self.command:
            raise ValueError(
                f"MCPServerConfig '{self.registry_key}': stdio transport requires 'command'."
            )
        if self.transport == "http" and not self.url:
            raise ValueError(
                f"MCPServerConfig '{self.registry_key}': http transport requires 'url'."
            )


class MCPRegistry:
    """
    Manages MCP tool discovery and call dispatch.

    stdio servers — discovered once at startup (subprocess opened, tools
                    listed, subprocess closed). Each tool call reopens a
                    fresh subprocess. No persistent connection held across
                    the asyncio.run() boundary, so no anyio task-group errors.

    http servers  — persistent session kept alive in _exit_stack for the
                    lifetime of the registry. Server manages its own process.
    """

    def __init__(self) -> None:
        self._exit_stack = AsyncExitStack()
        self._sessions: dict[str, ClientSession] = {}       # http only
        self._tool_cache: dict[str, list] = {}              # all transports
        self._configs: dict[str, MCPServerConfig] = {}      # all transports

    async def connect(self, config: MCPServerConfig) -> None:
        """
        Discover tools from one MCP server.

        stdio — opens subprocess, calls list_tools(), closes subprocess.
                No session is stored; tool calls reopen on demand.
        http  — opens a persistent session stored in _exit_stack.
        """
        config.validate()

        if config.transport == "stdio":
            params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env,
            )
            # Open, discover, close — don't hold the connection open.
            # This avoids the anyio task-group / asyncio.run() boundary error.
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tool_list = await session.list_tools()
                    self._tool_cache[config.registry_key] = tool_list.tools
                    self._configs[config.registry_key] = config

        else:  # http — persistent session is fine; server is independent
            read, write, _ = await self._exit_stack.enter_async_context(
                streamablehttp_client(config.url)
            )
            session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            tool_list = await session.list_tools()
            self._sessions[config.registry_key] = session
            self._tool_cache[config.registry_key] = tool_list.tools
            self._configs[config.registry_key] = config

        names = [t.name for t in self._tool_cache[config.registry_key]]
        print(f"[MCP] Discovered '{config.registry_key}' ({config.transport}): {names}")

    # ------------------------------------------------------------------
    # Caller factories
    # ------------------------------------------------------------------

    def _make_caller(self, config: MCPServerConfig, tool_name: str):
        """
        Returns an async callable for one tool.

        http  — uses the persistent session directly.
        stdio — opens a fresh subprocess per call (clean, no shared state).
        """
        if config.transport == "http":
            session = self._sessions[config.registry_key]

            async def _http_caller(**kwargs) -> str:
                result = await session.call_tool(tool_name, arguments=kwargs)
                parts = [
                    b.text for b in result.content
                    if hasattr(b, "text") and b.text
                ]
                return "\n".join(parts) if parts else "(no output)"

            _http_caller.__name__ = tool_name
            return _http_caller

        else:  # stdio
            params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env,
            )

            async def _stdio_caller(**kwargs) -> str:
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments=kwargs)
                        parts = [
                            b.text for b in result.content
                            if hasattr(b, "text") and b.text
                        ]
                        return "\n".join(parts) if parts else "(no output)"

            _stdio_caller.__name__ = tool_name
            return _stdio_caller

    # ------------------------------------------------------------------
    # tool_definitions entry builder
    # ------------------------------------------------------------------

    def build_tool_definition_entry(self, config: MCPServerConfig) -> dict:
        """
        Returns a dict shaped exactly like a ToolRegistry tool_definitions entry,
        ready to be merged into self.tool_definitions.

        Availability keys (item_types, room_types, use_level) are copied from
        the config so ToolAvailabilityChecker gates them normally.
        """
        if config.registry_key not in self._tool_cache:
            raise RuntimeError(
                f"MCPRegistry: no tool cache for '{config.registry_key}'. "
                "Call connect() before build_tool_definition_entry()."
            )

        mcp_tools = self._tool_cache[config.registry_key]

        # One async callable per tool
        functions: dict[str, callable] = {
            tool.name: self._make_caller(config, tool.name)
            for tool in mcp_tools
        }

        # Turn into OpenAI function-calling format.
        definitions = [
            {
                "type": "function",
                "name": t.name,
                "description": (
                    t.description
                    or f"Tool provided by MCP server '{config.registry_key}'."
                ),
                "parameters": (
                    t.inputSchema
                    if t.inputSchema
                    else {"type": "object", "properties": {}}
                ),
            }
            for t in mcp_tools
        ]

        entry: dict = {
            "functions":   functions,
            "definitions": definitions,
            "use_level":   config.use_level,
        }

        if config.item_types:
            entry["item_types"] = config.item_types
        if config.room_types:
            entry["room_types"] = config.room_types

        return entry

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def is_connected(self, registry_key: str) -> bool:
        return registry_key in self._tool_cache

    async def close(self) -> None:
        """Close persistent http sessions. stdio has no sessions to close."""
        await self._exit_stack.aclose()
        self._sessions.clear()
        self._tool_cache.clear()
        self._configs.clear()
        print("[MCP] All sessions closed.")