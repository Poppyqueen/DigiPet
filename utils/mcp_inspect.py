#!/usr/bin/env python3
# mcp_inspect.py
# ─────────────────────────────────────────────────────────────────────────────
# Diagnostic tool for exploring any MCP server before wiring it into the
# framework. Accepts the same JSON format as mcp_config.json so you can
# copy-paste directly from your config.
#
# Usage
# ─────
#   # Pass a server entry as inline JSON
#   python mcp_inspect.py '{"command": "colab-mcp"}'
#   python mcp_inspect.py '{"command": "npx", "args": ["-y", "myinstants-mcp@latest"]}'
#
#   # Pass a JSON file (any single server entry, or a full mcpServers block)
#   python mcp_inspect.py server.json
#   python mcp_inspect.py mcp_config.json --server github_readonly_mcp
#
#   # HTTP server
#   python mcp_inspect.py '{"url": "http://localhost:8080/mcp"}'
#
#   # Dump raw JSON instead of pretty report
#   python mcp_inspect.py '{"command": "colab-mcp"}' --json
#
#   # Override server key used in generated skeleton
#   python mcp_inspect.py '{"command": "colab-mcp"}' --server-key colab
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import argparse
import asyncio
import json
import os
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

def _schema_summary(schema: dict | None) -> str:
    if not schema:
        return "(no parameters)"
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    if not props:
        return "(no parameters)"
    parts = []
    for name, info in props.items():
        typ = info.get("type", "any")
        req = "" if name in required else "?"
        parts.append(f"{name}{req}: {typ}")
    return ", ".join(parts)


# ── config loading ────────────────────────────────────────────────────────────

def load_server_config(source: str, server_name: str | None) -> tuple[dict, str]:
    """
    Parse the source string as either:
      - A JSON file path (with optional --server to pick one entry)
      - An inline JSON string

    Returns (server_entry_dict, derived_server_key).
    """
    # Try as file path first
    if os.path.exists(source):
        with open(source) as f:
            data = json.load(f)

        # If it's a full mcp_config.json with mcpServers block
        if "mcpServers" in data:
            servers = data["mcpServers"]
            if server_name:
                if server_name not in servers:
                    print(f"✗ Server '{server_name}' not found in mcpServers block.", file=sys.stderr)
                    print(f"  Available: {', '.join(servers.keys())}", file=sys.stderr)
                    sys.exit(1)
                entry = servers[server_name]
                return entry, server_name
            elif len(servers) == 1:
                name, entry = next(iter(servers.items()))
                return entry, name
            else:
                print("File contains multiple servers. Specify one with --server:", file=sys.stderr)
                for name in servers:
                    print(f"  {name}", file=sys.stderr)
                sys.exit(1)

        # Single server entry directly in the file
        return data, server_name or os.path.splitext(os.path.basename(source))[0]

    # Try as inline JSON string
    try:
        entry = json.loads(source)
        return entry, server_name or "server"
    except json.JSONDecodeError:
        print(f"✗ Could not parse as JSON or find file: {source!r}", file=sys.stderr)
        sys.exit(1)


def entry_to_connection_params(entry: dict) -> tuple[str, str | None, list[str], str | None, dict | None]:
    """
    Extract (transport, command, args, url, env) from a server entry dict.
    Accepts both mcp_config.json format and Claude Desktop mcpServers format.
    """
    url     = entry.get("url")
    command = entry.get("command")
    args    = entry.get("args", [])
    env_raw = entry.get("env", {}) or {}

    # Resolve env — expand any values that reference real env vars
    env = {}
    for k, v in env_raw.items():
        if v and not v.startswith("<"):
            env[k] = v
        elif os.getenv(k):
            # fall back to host environment if placeholder value
            env[k] = os.getenv(k)

    if not env:
        env = None

    transport = "http" if url else "stdio"
    return transport, command, args, url, env


# ── core inspection ───────────────────────────────────────────────────────────

async def inspect(
    transport: str,
    command:   str | None,
    args:      list[str],
    url:       str | None,
    env:       dict | None,
) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamablehttp_client

    result: dict[str, Any] = {
        "server_info": None,
        "tools":       [],
        "prompts":     [],
        "resources":   [],
        "raw_content_sample": {},  # tool_name -> raw content blocks for debug
        "errors":      {},
    }

    async def _do_inspect(session: ClientSession):
        await session.initialize()

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
                    "name":         t.name,
                    "description":  t.description or "",
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
                    "name":        r.name,
                    "uri":         str(r.uri),
                    "mime_type":   r.mimeType or "unknown",
                    "description": r.description or "",
                }
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

    # Tools
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

    # Prompts
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

    # Resources
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

    # Errors
    if data["errors"]:
        _section("ERRORS DURING DISCOVERY")
        for k, v in data["errors"].items():
            print(f"  ✗ {k}: {v}")

    # Generated skeleton
    tool_names   = [t["name"] for t in tools]
    prompt_names = [p["name"] for p in prompts]
    resource_uris = [r["uri"] for r in resources]

    _section("READY-TO-PASTE SKELETON  (copy into tool_registry.py)")

    if transport == "stdio":
        args_repr = json.dumps(args)
        conn_block = f"""        MCPServerConfig(
            server_key = "{server_key}",
            transport  = "stdio",
            command    = "{command}",
            args       = {args_repr},
        ),"""
    else:
        conn_block = f"""        MCPServerConfig(
            server_key = "{server_key}",
            transport  = "http",
            url        = "{url}",
        ),"""

    print(f"""
  # ── In _get_mcp_server_configs() ──────────────────────────────────────
{conn_block}

  # ── In _get_mcp_affordance_configs() ──────────────────────────────────
  # Full access affordance (all {len(tool_names)} tools)
        MCPAffordanceConfig(
            registry_key = "mcp_{server_key}_full",
            server_key   = "{server_key}",
            use_level    = "always_available",
        ),""")

    if tool_names:
        first_three = json.dumps(tool_names[:3])
        more = f"  # + {len(tool_names)-3} more" if len(tool_names) > 3 else ""
        print(f"""
  # Fine-tuned affordance example
        MCPAffordanceConfig(
            registry_key  = "mcp_{server_key}_custom",
            server_key    = "{server_key}",
            include_tools = {first_three},{more}
            item_types    = ["{server_key}_endpoint"],
            use_level     = "dual_use",
        ),""")

    if prompt_names:
        print(f"""
  # Affordance with prompt injection
        MCPAffordanceConfig(
            registry_key   = "mcp_{server_key}_guided",
            server_key     = "{server_key}",
            inject_prompts = {json.dumps(prompt_names)},
            item_types     = ["{server_key}_endpoint"],
            use_level      = "dual_use",
        ),""")

    if resource_uris:
        uri_comment = "\n  #   ".join(resource_uris)
        print(f"""
  # Available resource URIs:
  #   {uri_comment}
        MCPAffordanceConfig(
            registry_key          = "mcp_{server_key}_resources",
            server_key            = "{server_key}",
            resource_context_mode = "names_only",
            item_types            = ["{server_key}_endpoint"],
            use_level             = "dual_use",
        ),""")

    _hr("─")
    print(f"  * = required parameter")
    print(f"  Total: {len(tool_names)} tools · {len(prompt_names)} prompts · {len(resource_uris)} resources")
    _hr("─")
    print()


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Inspect an MCP server using the same JSON format as mcp_config.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # Inline JSON (quote the whole thing)
          python mcp_inspect.py '{"command": "colab-mcp"}'
          python mcp_inspect.py '{"command": "npx", "args": ["-y", "myinstants-mcp@latest"]}'
          python mcp_inspect.py '{"url": "http://localhost:8080/mcp"}'

          # Docker server — args as a JSON array, no shell quoting headaches
          python mcp_inspect.py '{"command":"docker","args":["run","-i","--rm","-e","GITHUB_PERSONAL_ACCESS_TOKEN","ghcr.io/github/github-mcp-server","--read-only"],"env":{"GITHUB_PERSONAL_ACCESS_TOKEN":"ghp_..."}}'

          # From your mcp_config.json (pick one server by name)
          python mcp_inspect.py mcp_config.json --server github_readonly_mcp

          # Raw JSON output
          python mcp_inspect.py '{"command": "colab-mcp"}' --json
        """),
    )
    parser.add_argument(
        "source",
        help="Inline JSON string, or path to a JSON file (single entry or full mcp_config.json)"
    )
    parser.add_argument(
        "--server", default=None,
        help="When source is a full mcp_config.json, pick this server by name"
    )
    parser.add_argument(
        "--server-key", default=None,
        help="Override the server_key used in the generated skeleton"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Dump raw discovery data as JSON"
    )

    args = parser.parse_args()

    entry, derived_key = load_server_config(args.source, args.server)
    server_key = args.server_key or derived_key

    transport, command, cmd_args, url, env = entry_to_connection_params(entry)

    if transport == "stdio" and not command:
        print("✗ No 'command' found in server entry.", file=sys.stderr)
        sys.exit(1)
    if transport == "http" and not url:
        print("✗ No 'url' found in server entry.", file=sys.stderr)
        sys.exit(1)

    try:
        data = asyncio.run(inspect(
            transport = transport,
            command   = command,
            args      = cmd_args,
            url       = url,
            env       = env,
        ))
    except Exception as e:
        print(f"\n✗ Connection failed: {type(e).__name__}: {e}", file=sys.stderr)
        if transport == "stdio":
            print(f"\n  Check that '{command}' is installed and reachable.", file=sys.stderr)
            print(f"  Try: which {command}", file=sys.stderr)
        else:
            print(f"\n  Check that the server is running at {url}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print_report(
            data,
            server_key = server_key,
            transport  = transport,
            command    = command,
            args       = cmd_args,
            url        = url,
        )


if __name__ == "__main__":
    main()