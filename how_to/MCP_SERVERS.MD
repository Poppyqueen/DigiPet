# MCP Servers

This document covers every MCP server the framework can connect to,
what external runtimes each one needs, and how to configure them.

---

## How MCP servers are registered

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
        },
        ...
    }
}
```
You can leave the mcpServers key empty if you don't want any server.


### Per-agent config snapshots

The first time an agent boots, the root `mcp_config.json` is cloned into
that agent's own directory. From that point on, the agent's MCP behavior
is controlled entirely by its own copy — changes to root do not affect
existing agents. To update an existing agent, edit its config directly or
delete it so it gets re-cloned from root on next boot.

Valid item types for each agent are determined by its own config snapshot.
Items with types not present in that snapshot are quarantined on load
(kept but inaccessible) rather than deleted — they may belong to a server
that is temporarily disconnected.

### Connection pooling

If two entries share identical connection parameters (same `url`, or same
`command` + `args` + `env`), the framework opens exactly one subprocess or
session regardless of how many affordance entries reference it. This means
you can split one server into multiple affordances with no penalty:

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
---

## Affordance block reference

All fields are optional. Omitting the entire `"affordance"` block gives
`always_available` access with all tools exposed. Reserve `always_available`
for unique integrations like memory tools — for everything else, define
a `use_level` and `item_types` to gate access properly.

| Field | Type | Default | Description |
|---|---|---|---|
| `use_level` | string | `"always_available"` | `"always_available"` · `"dual_use"` · `"room_only"` · `"inventory_only"` |
| `item_types` | list[str] | `[]` | Agent must have or see an item with one of these types |
| `room_types` | list[str] | `[]` | Agent must be in a room matching one of these types |
| `include_tools` | list[str] | `[]` | Whitelist of tool names — empty means **all** tools |
| `exclude_tools` | list[str] | `[]` | Blacklist of tool names — applied after include |
| `inject_prompts` | list[str] | `[]` | Parameterless MCP prompts fetched and injected into agent context at runtime |
| `prompt_tools` | list[str] | `[]` | MCP prompts with arguments — exposed as callable tools the agent can invoke |

---

## Included example servers

The root `mcp_config.json.example` template includes these entries as reference.
— they require external setup described below.

---

### colab-mcp (Google Colab)

Connects to a running Google Colab notebook session.

**Install:**
```bash
pip install git+https://github.com/googlecolab/colab-mcp
```

**Config:**
```json
"google_colab": {
    "command": "colab-mcp",
    "affordance": {
        "use_level": "dual_use",
        "item_types": ["colab_endpoint"]
    }
}
```

The command resolves automatically to the `colab-mcp` script in your venv's
`bin` directory. No path configuration needed.

**Item type gate:** `colab_endpoint`

---

### github-mcp-server (GitHub, read-only via Docker)

Read-only GitHub integration via the official GitHub MCP server image.

**Requirements:**
- Docker installed and running
- A GitHub personal access token in your `.env` file

**`.env` format** — no quotes around the value:
```
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_yourtokenhere
```

**Config:**
```json
"github_readonly_mcp": {
    "command": "docker",
    "args": [
        "run", "-i", "--rm",
        "--env-file", ".env",
        "-e", "GITHUB_READ_ONLY",
        "ghcr.io/github/github-mcp-server"
    ],
    "env": {
        "GITHUB_READ_ONLY": "1"
    },
    "affordance": {
        "use_level": "dual_use",
        "item_types": ["github_mcp_endpoint"],
        "exclude_tools": ["list_commits"]
    }
}
```

**Item type gate:** `github_mcp_endpoint`

---

### myinstants soundboard

Soundboard tools via [myinstants-mcp](https://github.com/austenstone/myinstants-mcp).

**Requirements:** Node.js with `npx` — https://nodejs.org

**Config:**
```json
"austenstone_myinstants": {
    "command": "npx",
    "args": ["-y", "myinstants-mcp@latest"],
    "env": { "MYINSTANTS_VOLUME": "0.8" },
    "affordance": {
        "use_level": "inventory_only",
        "item_types": ["sound_effects_apparatus"]
    }
}
```

The package auto-installs on first run via `-y`. No manual `npm install` needed.

**Item type gate:** `sound_effects_apparatus`

---

### HTTP server example (Tamagotchi)

Example of connecting to a locally running HTTP MCP service.

```json
"tamagotchi_mcp": {
    "url": "http://localhost:8000/mcp",
    "affordance": {
        "use_level": "inventory_only",
        "item_types": ["tamagotchi_device"]
    }
}
```

Any MCP server that speaks HTTP can be connected this way — just point
`url` at its endpoint.

**Item type gate:** `tamagotchi_device`

---

### Local test server

A minimal stdio server at `servers/test_server.py`. Useful as a starting
point for writing your own custom MCP server. Demonstrates splitting one
server into multiple affordances:

```json
"mcp_test_ping": {
    "command": "python",
    "args": ["servers/test_server.py"],
    "affordance": {
        "use_level": "dual_use",
        "item_types": ["_test_point_ping"],
        "include_tools": ["ping"]
    }
},
"mcp_test_add": {
    "command": "python",
    "args": ["servers/test_server.py"],
    "affordance": {
        "use_level": "inventory_only",
        "item_types": ["_test_point_add"],
        "include_tools": ["add_numbers"]
    }
},
"mcp_test_awareness": {
    "command": "python",
    "args": ["servers/test_server.py"],
    "affordance": {
        "use_level": "inventory_only",
        "item_types": ["_test_point_awareness"],
        "exclude_tools": ["add_numbers", "ping"],
        "prompt_tools": ["say_hello"],
        "inject_prompts": ["daily_reminder"]
    }
}
```

Three affordances, one server process — connection pooling handles the rest.

---

## Adding your own server

1. Find or build an MCP server. The [MCP registry](https://github.com/modelcontextprotocol/servers)
   lists community servers. Most npm-based ones work via `npx -y package-name`.

2. Add an entry to `mcp_config.json`:
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

3. Create an in-game item with `type: ["my_endpoint_type"]` so the agent
   can access the tools. If you omit the affordance block entirely, the tools
   are always available regardless of items or room.


    3.5. You can use `inventory_items/items_validation/items_schema_test.py` to run inference on an AI to generate a base item with your new type based on a prompt. If you pass game-valid types, it will construct your item sharing those types.

    **Basic usage:**
    ```bash
    python -m inventory_items.items_validation.items_schema_test \
        --types tamagotchi_device toggleable \
        --prompt "A futuristic glowing wristband, it hosts a small virtual companion"
    ```

    **All available arguments:**

    | Argument | Default | Description |
    |---|---|---|
    | `--types` | `toggleable tamagotchi_device` | One or more item types (space-separated). Must be game-valid types. |
    | `--prompt` | `"One example of this item..."` | Natural language description of the item to generate. |
    | `--provider` | `openai` | AI provider to use. Must be one of the configured `simple_ai` providers. |
    | `--model` | `gpt-5-mini` | Specific model name for the chosen provider. |

    **Example with all arguments:**
    ```bash
    python -m inventory_items.items_validation.items_schema_test \
        --types tamagotchi_device toggleable \
        --prompt "A futuristic glowing wristband" \
        --provider openai \
        --model gpt-5-mini
    ```

    The script initializes an AI client via `AIConfiguration`, builds a structured output schema from the provided types using `build_llm_schema_for_types`, and prints the resulting item as indented JSON.


4. Restart. The server is discovered and connected at startup — its tools
   appear in the agent's tool pool according to the affordance rules.

### Command resolution

For `stdio` servers, `command` is resolved against your venv's `bin`
directory automatically. Bare names like `colab-mcp`, `python`, or `npx`
all work without specifying full paths. Absolute paths also work if needed.

For `http` servers, only `url` is required — no command resolution.