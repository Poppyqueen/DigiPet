# Tool Construction System: How to Build and Manage AI Agent Affordances

## What is the Tool Construction System?

The Tool Construction System (now more accurately called the **Affordance Construction System**) is the central hub that dynamically builds and manages all available functions, tools, and perception for the AI agent based on the current context. It consists of three files working together, living inside tools/tools_builder/:

| File | Responsibility |
| :--- | :--- |
| `tool_registry.py` | Service initialization + the `tool_definitions` dict |
| `tool_availability.py` | Stateless availability logic — can be tested in isolation |
| `construct_tools.py` | Runtime mechanics — dispatch, map construction, context building |

The system intelligently determines what the agent can do and what it passively perceives based on:

- **Current room types** — Different room types provide different capabilities and awareness
- **Environmental items** — Items present in the current room
- **Inventory items** — Items the agent is carrying
- **Base functions** — Always-available core functions
- **Optional integrations** — External services enabled/disabled via configuration

---

## Core Architecture — The Unified Affordance Definition Map

The heart of the system is **`tool_definitions`** — a single dictionary in `ToolRegistry` that manages all affordances and their availability rules. Each entry is an *Affordance Block*.

| Key | Description |
| :--- | :--- |
| **`"functions"`** | *Optional dict*. Maps function names to Python method references (action affordances). Omit for perception-only blocks. |
| **`"definitions"`** | List of JSON-like tool definitions for the LLM (from `my_tools.py`). |
| **`"use_level"`** | Item-based availability: `"always_available"`, `"inventory_only"`, `"room_only"`, `"dual_use"`. Controls where items must be located. |
| **`"room_types"`** | *Optional list*. Active when current room has any of these types. Works additively (OR logic) with `item_types`. If room types exists, use level is not required. (Maybe change that?)|
| **`"item_types"`** | *Optional list*. Item types that enable the affordance. Location requirement set by `use_level`. |
| **`"display_information"`** | *Optional function*. Returns state info for the GUI (observer perspective — can be omniscient). |
| **`"agent_information"`** | *Optional function*. Returns perception info injected into agent context automatically (agent perspective — must be token-efficient and embodied). |

### Availability Logic

An affordance block becomes active when **any** of these match:

1. `"use_level": "always_available"` — always active
2. `room_types` match — current room has any listed type
3. `item_types` match — matching item exists in the location required by `use_level`

Room type and item type checks combine with OR logic. A powered-off item (has `power_toggle: false`) will not activate its affordances even if location matches.

**`use_level` only controls item location requirements:**

| Value | Meaning |
| :--- | :--- |
| `"always_available"` | Special — ignores all other conditions |
| `"inventory_only"` | Item must be in agent's inventory |
| `"room_only"` | Item must be in current room |
| `"dual_use"` | Item can be in either location |

---

## Initialization Phase Order

**This order is load-bearing. Breaking it causes silent crashes.**

```
Phase 1 — Services with no availability dependency
          (room_tools, garden_manager, images_lab, maze, A_Life, optional services)

Phase 2 — Build tool_definitions
          (_build_tool_definitions — references Phase 1 service methods, they must exist first)

Phase 3 — Build toolset_checker
          (make_toolset_checker — needs tool_definitions dict to exist)

Phase 4 — Services that need the toolset_checker
          (LighthouseController and any future service that queries tool availability)

Phase 5 — Tool blocks that reference Phase 4 services
          (_add_lighthouse_tools — appends to tool_definitions after lighthouse exists)
```

**Rule:** If a service needs `toolset_checker` → Phase 4. If a tool block references that service → Phase 5 via a dedicated `_add_*_tools()` method, **not** inside `_build_tool_definitions`.

This is the most common source of errors. If you see `AttributeError: 'ToolRegistry' object has no attribute 'X'` during init, a tool block is referencing a service that hasn't been created yet.

---

## Understanding `display_information` vs `agent_information`

This is a critical architectural distinction:

**`display_information`** — For the GUI/human observer. Can include omniscient information, full text, detailed maps, or data the agent shouldn't know. Prioritizes completeness.

**`agent_information`** — What the agent **passively perceives** by being in a context — analogous to peripheral vision. Automatically injected into `construct_context()` every turn. Must be:
- Token-efficient (concise, relevant)
- From the agent's embodied perspective (no omniscient knowledge)
- Appropriate to know without taking an action

Many simple blocks can share the same function for both. Complex systems (A-Life, maze, Wikipedia) need separate implementations because the observer needs more or different information than the agent should passively receive.

---

## The `toolset_checker` — For Services That Need Availability Queries

Services initialized in Phase 4 receive a `toolset_checker` callable. This lets them ask "is affordance block X currently active?" without holding a reference to `FunctionBuilder` or any state directly.

```python
class MyService:
    def __init__(self, state_manager, signal, is_toolset_available=None):
        self.is_toolset_available = is_toolset_available

    def _format_events(self, events):
        formatted = []
        for event in events:
            if any(self.is_toolset_available(key) for key in event.affordance_keys):
                formatted.append(event.message)
        return "\n".join(formatted)
```

The argument passed is the **primary key** of a tool block in `tool_definitions` (e.g. `"lamp"`, `"iov_pressure"`). Events in the lighthouse simulation carry `event_affordances_keys` for exactly this purpose — the checker filters them so the agent only receives events for things it can currently perceive.

---

## How to Add a New Affordance Block

### Step 1: Implement the functions

Create your tool functions in the appropriate module within `tools/tools_folder/`. All functions **must return a string**.

```python
# tools/tools_folder/my_new_tools.py
class MyNewTools:
    def __init__(self, state_manager, signal_callback):
        self.state_manager = state_manager
        self.signal_callback = signal_callback

    def take_a_seat(self, item_id: int) -> str:
        return f"You sit down on item {item_id}. Comfortable."

    def get_seat_perception(self) -> str:
        """Agent perspective — token-efficient."""
        return "You notice a comfortable-looking chair nearby."
```

### Step 2: Add the definition to `my_tools.py`

```python
seat_tools = [
    {
        "type": "function",
        "name": "take_a_seat",
        "description": "Sit on a seat, chair, or other suitable item.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The item ID to sit on."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    }
]
```

### Step 3: Register in `tool_registry.py`

Instantiate the service in Phase 1, then add the tool block. **Where** you add it depends on whether it references a Phase 4 service:

- **References only Phase 1 services** → add inside `_build_tool_definitions`
- **References a Phase 4 service** → add inside a dedicated `_add_*_tools()` method called after Phase 4

#### Example: Room-type block
```python
"darkroom": {
    "functions": {
        "develop_photo": self.room_tools.darkroom.develop_photo,
    },
    "definitions": darkroom_tools,
    "room_types": ["darkroom"],
    "display_information": self.room_tools.darkroom.get_status,
    "agent_information":   self.room_tools.darkroom.get_perception,
}
```

#### Example: Inventory-only item block
```python
"special_key": {
    "functions": {
        "use_special_key": self.room_tools.use_special_key,
    },
    "definitions": special_key_tools,
    "item_types": ["special_key"],
    "use_level": "inventory_only",
}
```

#### Example: Dual-use item block (room or inventory)
```python
"seat": {
    "functions": {
        "take_a_seat": self.room_tools.living_room.take_a_seat,
    },
    "definitions": seat_tools,
    "item_types": ["seat"],
    "use_level": "dual_use",
}
```

#### Example: Combined room type + item type (OR logic)
```python
"fresnel_lens_interior": {
    "functions": {
        "fresnel_rotation_state": self.lighthouse.lighthouse_manager.lantern.get_fresnel_rotation,
    },
    "definitions": fresnel_lens_tools,
    "room_types": ["fresnel_lens_interior"],   # active in this room type
    "item_types": ["fresnel_lens_apparatus"],  # OR when this item is in the room
    "use_level": "room_only",
    "display_information": self.lighthouse.lighthouse_manager.lantern.get_fresnel_rotation,
    "agent_information":   self.lighthouse.lighthouse_manager.lantern.get_fresnel_rotation,
}
```

#### Example: Perception-only block (no functions)
```python
"outdoors_view": {
    # No "functions" key — perception only
    "definitions": garden_room_tools,
    "room_types": ["outdoors_view"],
    "agent_information": self.room_tools.garden.display_information,
}
```

When the agent is in a room with type `"outdoors_view"`, it automatically receives weather information in its context without calling any function.

#### Example: Phase 5 block (references a Phase 4 service)
```python
# In __init__, after self.lighthouse = LighthouseController(...):
self._add_lighthouse_tools()

def _add_lighthouse_tools(self):
    lh = self.lighthouse
    self.tool_definitions["lantern_room"] = {
        "functions": {
            "get_lantern_room_interior_status": lh.get_lantern_room_interior_status,
            "clean_condensation":               lh.clean_condensation,
        },
        "definitions": lantern_room_tools,
        "room_types": ["lantern_room"],
        "display_information": lh.get_lantern_room_interior_status,
        "agent_information":   lh.get_lantern_room_interior_status,
    }
```

---

## How to Add Optional External Integrations

### Step 1: Add a config flag

Ensure your configuration has an enable flag: `[Tools] enable_my_service = true`.

### Step 2: Conditional initialization in Phase 1

```python
self.my_service = None
if config_manager.get_config("Tools", "enable_my_service"):
    try:
        from tools.tools_folder.services import my_service_handler
        self.my_service = my_service_handler.MyServiceTools()
        print("MyServiceTools instance created.")
    except Exception as e:
        print(f"Error with MyService tools: {e}")
```

### Step 3: Register in `_add_conditional_tools`

```python
def _add_conditional_tools(self, state_manager):
    if self.my_service:
        self.tool_definitions["my_service"] = {
            "functions": {
                "my_service_action": self.my_service.do_thing,
            },
            "definitions": my_service_tools,
            "item_types": ["my_service_item"],
            "use_level": "dual_use",
        }
        print("My service tools added.")
```

---

## Context and Information System

### For the Agent (LLM context)

`construct_context()` automatically calls `get_current_tools_info(flag="agent")` internally, which:

- Checks all active affordance blocks for an `agent_information` function
- Executes each and collects the results
- Injects this perception data into the system context on every turn

The agent always has passive awareness of its current situation without needing observation actions.

**Agent context includes:**
- Current time and location
- Emotional state and available emotes
- Inventory and room contents
- Current stats (hunger, energy, etc.)
- Passive perception from all active `agent_information` functions

### For the GUI

```python
room_info = function_builder.get_current_tools_info(flag="display")
```

With `flag="display"`, the same method checks for `display_information` functions instead — which can provide more verbose, omniscient, or detailed data appropriate for human observers.

---

## Token Efficiency Through Perception

By injecting perception into context rather than requiring tool calls, the system reduces turn costs:

**Without passive perception:**
- Turn 1: Agent calls `look_at_lamp` (sends full history)
- Turn 2: Agent calls `check_pressure` (sends full history + turn 1)
- Turn 3: Agent acts (sends full history + turns 1–2)

**With passive perception:**
- Turn 1: Lamp and pressure state already in context. Agent acts immediately.

The perception layer adds tokens to each system prompt but eliminates observation turns — net savings over multi-step interactions.

---

## Key Rules

- **Names must match exactly** between `my_tools.py` definitions and Python function/argument names
- **All tool functions must return a string** — this is what the agent receives
- **Derived state is never persisted** — only source state (`PhysicalState`, `Controls`) goes to JSON; derived state is always recomputed on load
- **Don't reference Phase 4 services inside `_build_tool_definitions`** — use a dedicated `_add_*_tools()` method called after Phase 4
- **`tool_definitions` is shared by reference** between `ToolRegistry` and `FunctionBuilder` — intentional, mutations anywhere are reflected everywhere
- **`agent_information` must be embodied and token-efficient** — it's injected on every turn; omniscient or verbose data belongs in `display_information` only