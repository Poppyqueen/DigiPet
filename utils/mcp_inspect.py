#!/usr/bin/env python3
# mcp_inspect.py
# ─────────────────────────────────────────────────────────────────────────────
# Diagnostic tool for exploring any MCP server before wiring it into the
# framework.  Connects, discovers everything the server exposes, and prints
# a full report plus a ready-to-paste MCPServerConfig / MCPAffordanceConfig
# skeleton.
#
# Usage
# ─────
#   # stdio server (installed package / script)
#   python mcp_inspect.py --transport stdio --command colab-mcp
#   python mcp_inspect.py --transport stdio --command python --args servers/my_server.py
#
#   # http server (already running, e.g. Docker)
#   python mcp_inspect.py --transport http --url http://localhost:8080/mcp
#
# Optional flags
#   --server-key  NAME    override the server_key used in the generated skeleton
#   --json                dump raw discovery data as JSON instead of pretty report
# ─────────────────────────────────────────────────────────────────────────────

# Example to inspect the myinstants MCP server, auto installing if not available.
# Make sure you have Node.js/npx to run this server.
# python -m utils.mcp_inspect --transport stdio --command npx --args="-y" --args="myinstants-mcp@latest" 
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import textwrap
from typing import Any


# ── helpers ──────────────────────────────────────────────────────────────────

def _hr(char="─", width=72):
    print(char * width)

def _section(title: str):
    print()
    _hr()
    print(f"  {title}")
    _hr()

def _indent(text: str, prefix: str = "    ") -> str:
    return textwrap.indent(str(text), prefix)

def _schema_summary(schema: dict | None) -> str:
    """One-line summary of a JSON Schema input_schema."""
    if not schema:
        return "(no parameters)"
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    if not props:
        return "(no parameters)"
    parts = []
    for name, info in props.items():
        typ   = info.get("type", "any")
        req   = "" if name in required else "?"
        parts.append(f"{name}{req}: {typ}")
    return ", ".join(parts)


# ── core inspection ───────────────────────────────────────────────────────────

async def inspect(
    transport: str,
    command:   str | None,
    args:      list[str],
    url:       str | None,
    env:       dict | None,
) -> dict[str, Any]:
    """
    Connect to the server, collect everything, return a structured dict.
    """
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamablehttp_client

    result: dict[str, Any] = {
        "server_info":  None,
        "tools":        [],
        "prompts":      [],
        "resources":    [],
        "errors":       {},
    }

    async def _do_inspect(session: ClientSession):
        await session.initialize()

        # Server info
        try:
            result["server_info"] = {
                "name":    session.server_info.name    if session.server_info else "unknown",
                "version": session.server_info.version if session.server_info else "unknown",
            }
        except Exception as e:
            result["errors"]["server_info"] = str(e)

        # Tools
        try:
            tl = await session.list_tools()
            result["tools"] = [
                {
                    "name":        t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema,
                }
                for t in tl.tools
            ]
        except Exception as e:
            result["errors"]["tools"] = str(e)

        # Prompts
        try:
            pl = await session.list_prompts()
            prompts = []
            for p in pl.prompts:
                entry = {
                    "name":        p.name,
                    "description": p.description or "",
                    "arguments":   [],
                }
                # Try fetching the prompt to see its rendered content
                try:
                    fetched = await session.get_prompt(p.name, {})
                    entry["messages"] = [
                        {
                            "role":    m.role,
                            "content": m.content.text
                                       if hasattr(m.content, "text")
                                       else str(m.content),
                        }
                        for m in fetched.messages
                    ]
                except Exception as pe:
                    entry["fetch_error"] = str(pe)
                if hasattr(p, "arguments") and p.arguments:
                    entry["arguments"] = [
                        {
                            "name":        a.name,
                            "description": a.description or "",
                            "required":    a.required,
                        }
                        for a in p.arguments
                    ]
                prompts.append(entry)
            result["prompts"] = prompts
        except Exception as e:
            result["errors"]["prompts"] = str(e)

        # Resources
        try:
            rl = await session.list_resources()
            resources = []
            for r in rl.resources:
                entry = {
                    "name":     r.name,
                    "uri":      str(r.uri),
                    "mime_type": r.mimeType or "unknown",
                    "description": r.description or "",
                }
                # Try reading a preview (first 300 chars)
                try:
                    content = await session.read_resource(r.uri)
                    raw = ""
                    for block in content.contents:
                        if hasattr(block, "text"):
                            raw = block.text
                            break
                    entry["preview"] = raw[:300] + ("…" if len(raw) > 300 else "")
                except Exception as re:
                    entry["read_error"] = str(re)
                resources.append(entry)
            result["resources"] = resources
        except Exception as e:
            result["errors"]["resources"] = str(e)

    # ── connect ──
    if transport == "stdio":
        params = StdioServerParameters(command=command, args=args, env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await _do_inspect(session)
    else:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await _do_inspect(session)

    return result


# ── pretty report ─────────────────────────────────────────────────────────────

def print_report(data: dict, server_key: str, transport: str,
                 command: str | None, args: list[str], url: str | None):

    info = data["server_info"] or {}
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print(f"║  MCP Inspector — {info.get('name','?')}  v{info.get('version','?')}".ljust(71) + "║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    # ── Tools ──
    tools = data["tools"]
    _section(f"TOOLS  ({len(tools)} found)")
    if not tools:
        print("    (none)")
    for t in tools:
        print(f"  ▸ {t['name']}")
        if t["description"]:
            for line in textwrap.wrap(t["description"], width=65):
                print(f"      {line}")
        print(f"      params: {_schema_summary(t['input_schema'])}")
        schema = t.get("input_schema") or {}
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        if props:
            for pname, pinfo in props.items():
                req_mark = " *" if pname in required else ""
                pdesc = pinfo.get("description", "")
                ptype = pinfo.get("type", "any")
                print(f"        · {pname} ({ptype}){req_mark}  {pdesc}")
        print()

    # ── Prompts ──
    prompts = data["prompts"]
    _section(f"PROMPTS  ({len(prompts)} found)")
    if not prompts:
        print("    (none)")
    for p in prompts:
        print(f"  ▸ {p['name']}")
        if p["description"]:
            print(f"      {p['description']}")
        if p.get("arguments"):
            print("      arguments:")
            for a in p["arguments"]:
                req = " *" if a["required"] else ""
                print(f"        · {a['name']}{req}  {a['description']}")
        if p.get("messages"):
            print("      rendered preview:")
            for m in p["messages"]:
                preview = m["content"][:200].replace("\n", " ")
                print(f"        [{m['role']}] {preview}{'…' if len(m['content'])>200 else ''}")
        if p.get("fetch_error"):
            print(f"      (could not fetch: {p['fetch_error']})")
        print()

    # ── Resources ──
    resources = data["resources"]
    _section(f"RESOURCES  ({len(resources)} found)")
    if not resources:
        print("    (none)")
    for r in resources:
        print(f"  ▸ {r['name']}")
        print(f"      uri:  {r['uri']}")
        print(f"      mime: {r['mime_type']}")
        if r["description"]:
            print(f"      desc: {r['description']}")
        if r.get("preview"):
            print(f"      preview: {r['preview'][:120]}{'…' if len(r['preview'])>120 else ''}")
        if r.get("read_error"):
            print(f"      (could not read: {r['read_error']})")
        print()

    # ── Errors ──
    if data["errors"]:
        _section("ERRORS DURING DISCOVERY")
        for k, v in data["errors"].items():
            print(f"  ✗ {k}: {v}")

    # ── Generated skeleton ──
    _section("READY-TO-PASTE SKELETON  (copy into tool_registry.py)")

    tool_names = [t["name"] for t in tools]
    prompt_names = [p["name"] for p in prompts]
    resource_uris = [r["uri"] for r in resources]

    conn_block = ""
    if transport == "stdio":
        args_repr = repr(args)
        conn_block = f"""        MCPServerConfig(
            server_key = "{server_key}",
            transport  = "stdio",
            command    = sys.executable,   # or full path to: {command}
            args       = {args_repr},
        ),"""
    else:
        conn_block = f"""        MCPServerConfig(
            server_key = "{server_key}",
            transport  = "http",
            url        = "{url}",
        ),"""

    print(f"""
  # ── In _get_mcp_server_configs() ─────────────────────────────────────
{conn_block}

  # ── In _get_mcp_affordance_configs() ─────────────────────────────────
  # Full access affordance (all {len(tool_names)} tools)
        MCPAffordanceConfig(
            registry_key = "mcp_{server_key}_full",
            server_key   = "{server_key}",
            use_level    = "always_available",
        ),
""")

    if tool_names:
        print(f"""  # Fine-tuned affordance example (pick the tools you want)
        MCPAffordanceConfig(
            registry_key  = "mcp_{server_key}_custom",
            server_key    = "{server_key}",
            include_tools = {json.dumps(tool_names[:3])},{"  # first 3 shown — extend as needed" if len(tool_names) > 3 else ""}
            item_types    = ["{server_key}_endpoint"],
            use_level     = "dual_use",
        ),
""")

    if prompt_names:
        print(f"""  # Affordance with prompt injection
        MCPAffordanceConfig(
            registry_key   = "mcp_{server_key}_guided",
            server_key     = "{server_key}",
            inject_prompts = {json.dumps(prompt_names)},
            item_types     = ["{server_key}_endpoint"],
            use_level      = "dual_use",
        ),
""")

    if resource_uris:
        print(f"""  # Available resource URIs (use resource_context_mode to inject):
  #   {chr(10)+"  #   ".join(resource_uris)}
  #
  # Example with resource context:
        MCPAffordanceConfig(
            registry_key          = "mcp_{server_key}_with_resources",
            server_key            = "{server_key}",
            resource_context_mode = "names_only",   # or "full" for small servers
            item_types            = ["{server_key}_endpoint"],
            use_level             = "dual_use",
        ),
""")

    _hr("─")
    print(f"  * = required parameter")
    print(f"  Total: {len(tool_names)} tools · {len(prompt_names)} prompts · {len(resource_uris)} resources")
    _hr("─")
    print()


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Inspect an MCP server and generate framework config skeletons.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python mcp_inspect.py --transport stdio --command colab-mcp
          python mcp_inspect.py --transport stdio --command python --args servers/my_server.py
          python mcp_inspect.py --transport http  --url http://localhost:8080/mcp
          python mcp_inspect.py --transport stdio --command mcp-server-fetch --json
        """),
    )
    parser.add_argument(
        "--transport", required=True, choices=["stdio", "http"],
        help="Connection type: stdio (subprocess) or http (running server)"
    )
    parser.add_argument(
        "--command", default=None,
        help="[stdio] Command to run (e.g. 'colab-mcp', 'python')"
    )
    parser.add_argument(
        "--args", nargs="*", default=[],
        help="[stdio] Arguments to pass to the command (e.g. servers/my_server.py)"
    )
    parser.add_argument(
        "--url", default=None,
        help="[http] Full URL of the MCP endpoint (e.g. http://localhost:8080/mcp)"
    )
    parser.add_argument(
        "--env", nargs="*", default=[],
        metavar="KEY=VALUE",
        help="[stdio] Environment variables to set (e.g. API_KEY=abc123)"
    )
    parser.add_argument(
        "--server-key", default=None,
        help="Override the server_key used in generated skeleton (default: derived from command/url)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Dump raw discovery data as JSON instead of pretty report"
    )

    args = parser.parse_args()

    # Validate
    if args.transport == "stdio" and not args.command:
        parser.error("--command is required for stdio transport")
    if args.transport == "http" and not args.url:
        parser.error("--url is required for http transport")

    # Parse env vars
    env = None
    if args.env:
        env = {}
        for item in args.env:
            if "=" not in item:
                parser.error(f"--env values must be KEY=VALUE, got: {item!r}")
            k, v = item.split("=", 1)
            env[k] = v

    # Derive server_key
    if args.server_key:
        server_key = args.server_key
    elif args.transport == "stdio":
        server_key = (args.command or "server").split("/")[-1].replace("-", "_").replace(".py", "")
    else:
        from urllib.parse import urlparse
        server_key = urlparse(args.url).hostname.replace(".", "_").replace("-", "_")

    # Run
    try:
        data = asyncio.run(inspect(
            transport = args.transport,
            command   = args.command,
            args      = args.args,
            url       = args.url,
            env       = env,
        ))
    except Exception as e:
        print(f"\n✗ Connection failed: {type(e).__name__}: {e}", file=sys.stderr)
        print("\nCheck that:", file=sys.stderr)
        if args.transport == "stdio":
            print(f"  · '{args.command}' is installed and on PATH", file=sys.stderr)
            print(f"  · Try: which {args.command}", file=sys.stderr)
        else:
            print(f"  · The server is running at {args.url}", file=sys.stderr)
            print(f"  · Try: curl {args.url}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print_report(
            data,
            server_key = server_key,
            transport  = args.transport,
            command    = args.command,
            args       = args.args,
            url        = args.url,
        )


if __name__ == "__main__":
    main()