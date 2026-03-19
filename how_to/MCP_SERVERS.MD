# MCP Servers

This document covers every MCP server the framework can connect to,
what external runtimes each one needs, and how to enable or configure them.

---

## How MCP servers are registered

There are two ways to add an MCP server:

### 1. `mcp_config.json` (recommended for most users)

Drop an `mcp_config.json` file at the project root. The format is identical
to what Claude Desktop and Cursor use, so you can copy an existing config
directly. Add an optional `"affordance"` block to control availability
inside the framework.

```json
{
    "mcpServers": {
        "my_server": {
            "command": "npx",
            "args": ["-y", "some-mcp-package@latest"],
            "affordance": {
                "use_level":  "inventory_only",
                "item_types": ["my_item_type"]
            }
        }
    }
}
```

**Connection pooling** — if two entries share identical connection parameters
(same `url`, or same `command`+`args`+`env`), the framework detects the match
via a connection fingerprint and opens exactly one subprocess or session,
regardless of how many affordance entries reference it. This means you can
split one server into multiple affordances directly from JSON with no penalty:

```json
{
    "mcpServers": {
        "canva_designer": {
            "url": "http://localhost:9090/mcp",
            "affordance": { "item_types": ["canvas_designer_station"], "include_tools": ["create_design"] }
        },
        "canva_assets": {
            "url": "http://localhost:9090/mcp",
            "affordance": { "item_types": ["canvas_asset_terminal"], "include_tools": ["export_design"] }
        }
    }
}
```

One Canva process, two affordances, zero redundant connections.

See `mcp_config.json` at the project root for a fully annotated example.

### 2. `tool_registry.py` (for power users / affordance-heavy setups)

Add entries to `_get_mcp_server_configs()` and `_get_mcp_affordance_configs()`
in `tools/tools_builder/tool_registry.py`. This approach lets you split one
server into multiple affordances (different tool subsets, different item gates)
without repeating the connection definition. Python-declared entries always
take precedence over JSON entries if keys clash.

---

## Affordance block reference

All fields are optional. Omitting the entire `"affordance"` block gives
`always_available` access with all tools exposed — safe default.

| Field | Type | Default | Description |
|---|---|---|---|
| `use_level` | string | `"always_available"` | `"always_available"` · `"dual_use"` · `"room_only"` · `"inventory_only"` |
| `item_types` | list[str] | `[]` | Agent must have or see an item with one of these types |
| `room_types` | list[str] | `[]` | Agent must be in a room matching one of these types |
| `include_tools` | list[str] | `[]` | Whitelist of tool names — empty means **all** tools |
| `exclude_tools` | list[str] | `[]` | Blacklist of tool names — applied after include |
| `inject_prompts` | list[str] | `[]` | MCP prompt names to fetch and add to agent context |

---

## Built-in optional servers

These are declared in `tool_registry.py` and toggled via `[Tools]` config flags.

---

### myinstants

Soundboard tools via the [myinstants-mcp](https://github.com/austenstone/myinstants-mcp) package.

**External runtime required:** Node.js (which includes `npx`)
- Download: https://nodejs.org
- Verify: `node --version` and `npx --version` in your terminal

**Enable:** set `enable_mcp_myinstants = true` in your config file.

The package is auto-installed on first run via `npx -y`. No manual `npm install` needed.

**Item type gate:** `sound_effects_apparatus` — the agent must be holding an
item of this type to access the soundboard tools.

---

### mcp_colab

Google Colab integration via [colab-mcp](https://pypi.org/project/colab-mcp/).

**External runtime required:** none beyond the Python venv.

**Install:**
```bash
pip install colab-mcp
```

**Enable:** set `enable_mcp_colab = true` in your config file.

**Known issue:** `open_colab_browser_connection` returns false in some
environments. Tracked upstream — check the repo issues for current status.

**Item type gate:** `colab_endpoint`

---

### mcp_test (local example server)

A minimal stdio server defined in `servers/test_server.py`.
Useful as a starting point for writing your own custom MCP server
without any external runtime or package.

**Enable:** set `enable_mcp_test = true` in your config file.

**Item type gate:** `test_server_endpoint`

---

## Adding your own server

1. Find or build an MCP server. The [MCP registry](https://github.com/modelcontextprotocol/servers)
   lists community servers. Most npm-based ones work via `npx -y package-name`.

2. Add it to `mcp_config.json`:
   ```json
   {
       "mcpServers": {
           "my_new_server": {
               "command": "npx",
               "args": ["-y", "my-mcp-package@latest"],
               "affordance": {
                   "use_level":  "dual_use",
                   "item_types": ["my_endpoint_type"]
               }
           }
       }
   }
   ```

3. Create an in-game item with `item_type: "my_endpoint_type"` so the agent
   can access the tools. If you omit the affordance block entirely the tools
   are always available regardless of items or room.

4. Restart the application. The server will be discovered and connected
   at startup; its tools appear in the agent's tool pool according to the
   affordance rules.