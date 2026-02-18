# AI Agent Tool Framework: Creating and Managing Tools

This document explains how to add new tools to the AI agent framework. It reflects the current architecture after the refactor that separated tool definitions, availability logic, and service initialization into distinct files.

## File Structure

```
tools/
  construct_tools.py      # FunctionBuilder — runtime dispatch, context building
  tool_registry.py        # Service initialization + tool_definitions dict
  tool_availability.py    # Availability logic (no imports from services or state)
  my_tools.py             # Tool definitions (JSON-like structures for the LLM)
  tools_folder/           # Actual implementations
```

### What each file owns

**`my_tools.py`** — defines *what* tools look like to the LLM: name, description, parameters. Pure data, no logic.

**`tool_registry.py`** — owns two things that belong together: service instances (`garden_manager`, `lighthouse`, etc.) and the `tool_definitions` dict that wires service methods to tool keys. Initialization follows a strict phase order (see below).

**`tool_availability.py`** — stateless availability logic. `ItemContext`, `ToolAvailabilityChecker`, `ItemToolMapper`, and `make_toolset_checker`. No imports from services or state — can be tested in isolation.

**`construct_tools.py`** — runtime mechanics. Builds the live `function_map`, constructs the tool list the LLM sees, dispatches calls, builds the context string.

---

## The `tool_definitions` Dict

The heart of the system. Lives in `tool_registry.py`. Each entry is a **tool block** — a named group of related functions with rules for when they're available.

```python
"planting_garden": {
    "functions": {
        "plant_seed":   self.garden_manager.plant_seed,
        "water_plot":   self.garden_manager.water_plot,
    },
    "definitions": harvesting_garden_tools,   # from my_tools.py
    "room_types": ["planting_garden"],         # available in these room types
    "display_information": self.garden_manager.get_garden_summary,  # shown in GUI
    "agent_information":   self.garden_manager.get_garden_summary,  # shown to agent
}
```

### Availability rules

A tool block becomes active when **any** of these match the current state:

| Key | Meaning |
|-----|---------|
| `"use_level": "always_available"` | Always active, no conditions |
| `"room_types": [...]` | Active when current room has any of these types |
| `"item_types": [...]` + `"use_level": "inventory_only"` | Active when a matching item is in inventory |
| `"item_types": [...]` + `"use_level": "room_only"` | Active when a matching item is in the current room |
| `"item_types": [...]` + `"use_level": "dual_use"` | Active when a matching item is anywhere (room or inventory) |

Room type and item type checks can coexist in the same block — either match activates it.

### Information-only blocks

A block doesn't need `"functions"` — it can exist purely to gate `agent_information` or `display_information` access by room type:

```python
"outdoors_view": {
    "definitions": garden_room_tools,
    "room_types": ["outdoors_view"],
    "agent_information": self.room_tools.garden.display_information,
}
```

---

## Initialization Phase Order

**This order is load-bearing.** Breaking it causes silent crashes.

```
Phase 1 — Services with no availability dependency
          (garden_manager, images_lab, maze, A_Life, optional services...)

Phase 2 — Build tool_definitions
          (references Phase 1 service methods — they must exist first)

Phase 3 — Build toolset_checker
          (needs tool_definitions dict to exist)

Phase 4 — Services that need the toolset_checker
          (LighthouseController receives is_toolset_available=self.toolset_checker)

Phase 5 — Tool blocks that reference Phase 4 services
          (_add_lighthouse_tools() appends to tool_definitions after lighthouse exists)
```

**Rule:** If a service needs `toolset_checker` → it goes in Phase 4. If a tool block references that service → it goes in Phase 5 via a dedicated `_add_*_tools()` method, not inside `_build_tool_definitions`.

---

## Adding a New Tool: Step by Step

### Simple case — new function in an existing tool block

**1. Implement the function** in the appropriate service file. It must return a string.

```python
# tools_folder/rooms_tools.py (or wherever fits)
def ring_bell(self) -> str:
    return "You ring the bell. It echoes through the room."
```

**2. Add the definition** to the appropriate list in `my_tools.py`:

```python
living_room_tools = [
    # ... existing definitions ...
    {
        "type": "function",
        "name": "ring_bell",
        "description": "Ring the bell in the living room.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
]
```

**3. Add the function** to the relevant tool block in `tool_registry.py`:

```python
"living_room": {
    "functions": {
        "look_at_window": self.room_tools.living_room.look_at_window,
        "ring_bell":      self.room_tools.living_room.ring_bell,   # ← add here
    },
    ...
}
```

That's it. The availability system picks it up automatically.

---

### New tool block — new room or item type

**1–2.** Implement the function and add its definition to `my_tools.py` (same as above, possibly in a new list).

**3. Add a new tool block** to `_build_tool_definitions` in `tool_registry.py`:

```python
"darkroom": {
    "functions": {
        "develop_photo": self.room_tools.darkroom.develop_photo,
    },
    "definitions": darkroom_tools,       # your new list from my_tools.py
    "room_types": ["darkroom"],
    "display_information": self.room_tools.darkroom.get_status,
    "agent_information":   self.room_tools.darkroom.get_status,
}
```

---

### New tool block for a Phase 4 service (like lighthouse)

If your tool block references a service initialized in Phase 4, it **cannot** go in `_build_tool_definitions`. Add it to a dedicated method and call it after Phase 4:

```python
# In __init__, after self.my_service = MyService(...):
self._add_my_service_tools()

# New method:
def _add_my_service_tools(self):
    svc = self.my_service
    self.tool_definitions["my_tool_block"] = {
        "functions": {
            "do_thing": svc.do_thing,
        },
        "definitions": my_service_tools,
        "room_types": ["my_room"],
    }
```

---

### Optional/conditional tools

For tools gated by a config flag or optional service (YouTube, Discogs, etc.), add them in `_add_conditional_tools`:

```python
def _add_conditional_tools(self, state_manager):
    if self.my_feature_enabled:
        self.tool_definitions["my_feature"] = {
            "functions": {
                "do_feature_thing": self.my_service.do_thing,
            },
            "definitions": my_feature_tools,
            "item_types": ["my_item_type"],
            "use_level": "dual_use",
        }
```

---

## Using `toolset_checker` Inside Services

Services initialized in Phase 4 receive a `toolset_checker` callable. Use it to check whether a given tool block is currently active — for example, to decide whether to surface an event to the agent:

```python
class MyService:
    def __init__(self, ..., toolset_checker=None):
        self.toolset_checker = toolset_checker

    def _should_surface_event(self, affordance_key: str) -> bool:
        if not self.toolset_checker:
            return False
        return self.toolset_checker(affordance_key)
```

The `affordance_key` is the primary key of a tool block in `tool_definitions` (e.g. `"lamp"`, `"iov_pressure"`). Events in the lighthouse simulation carry `event_affordances_keys` for exactly this purpose — the checker filters them before they reach the agent.

---

## Key Rules

- **Names must match exactly** between `my_tools.py` definitions and Python function/argument names.
- **All tool functions must return a string** — this is what the agent receives.
- **Derived state is never persisted** — only `PhysicalState` and `Controls` are saved to JSON. Always recompute derived state on load.
- **Don't reference `self.lighthouse` (or any Phase 4 service) inside `_build_tool_definitions`** — use `_add_lighthouse_tools()` or equivalent instead.
- **`tool_definitions` is shared by reference** between `ToolRegistry` and `FunctionBuilder`. Mutations anywhere are reflected everywhere — intentional, but worth knowing.