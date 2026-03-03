# Extending Behaviors

This guide covers how to extend what the agent can do and perceive — writing tool classes, registering affordance blocks, implementing new object types, and building simulation systems the agent interacts with through the world.

If you haven't read the [Overview](OVERVIEW.md) yet, start there. The concepts of Rooms, Objects, and Affordances are assumed throughout.

---

## The Shape of an Extension

Every behavioral extension has the same three-part shape, regardless of complexity:

1. **Implement** — write a Python class with methods that do the work
2. **Define** — write the JSON schema that tells the agent what it can call and how
3. **Register** — add an affordance block to `tool_registry.py` connecting the two and declaring activation conditions

These three always happen together. An implementation without a registration does nothing. A registration without a definition produces a malformed tool.

---

## The State Manager

Any tool that reads or writes world state does so through a single object: `InventoryHouseManager`. You receive it as a constructor argument. You never instantiate it yourself and never reach past it into its internals.
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager


class MyTool:
    def __init__(self, state_manager, signal_callback=None):
        self.state_manager: InventoryHouseManager = state_manager
        self._signal_callback = signal_callback

    def _send_signal(self, signal_data: dict) -> None:
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Signal error in {self.__class__.__name__}: {e}")
```

This is the complete constructor. Two parameters: the state manager and an optional signal callback. No references to sub-services, no direct state access.

`InventoryHouseManager` is a facade over several internal services. Bypassing it skips validation, produces unpredictable return types, and makes your tool fragile to internal refactors. The one known exception is a narrow bypass in `BaseTools` — treat it as technical debt, not a pattern.

---

## Part 1 — Implementing a Tool Class

**Every agent-facing method must return a `str`.** The agent receives tool output as plain text. Internal helpers may return whatever is convenient.

### The State Manager API

All methods are called on `self.state_manager`.

#### Finding objects
```python
find_item(
    item_id: int,
    required_type: str | None = None,
    required_location: Literal["inventory", "room", "accessible"] | None = None,
) -> ItemLookupResult
```

| `required_location` | Meaning |
|---|---|
| `None` | Search everywhere — inventory and all rooms |
| `"inventory"` | Must be in the agent's inventory |
| `"room"` | Must be in any room |
| `"accessible"` | Inventory **or** the current room |

Always check `result.success` before accessing `result.item_data`.
```python
result = self.state_manager.find_item(item_id, required_type="book", required_location="inventory")
if not result.success:
    return result.error
item_data = result.item_data  # safe to access now
```

#### Creating objects

---

## Using the Item Store

Any tool that needs to *create* objects from blueprints — rather than just find or mutate existing ones — uses `ItemStore` to fetch those blueprints by name. The store walks the entire `inventory_items/items_provider/items_data/` directory tree on initialization and makes every defined blueprint available by name.
```python
from inventory_items.items_provider.item_store import ItemStore

class MyTool:
    def __init__(self, state_manager, signal_callback=None):
        self.state_manager = state_manager
        self._signal_callback = signal_callback
        self.item_store = ItemStore("inventory_items/items_provider/items_data")
```

Fetch a blueprint by its exact `name` field, then pass it directly to `create_item`:
```python
blueprint = self.item_store.get_item("Apple")
if not blueprint:
    return "Error: Could not find blueprint for 'Apple'."
```
## Creating a blueprint on runtime

You can create a raw blueprit for dynamic creation of items, an example of this in the code base is in the book tools,

```python
from inventory_items.item_pydantic_models import validate_item_dict # Import the validation function for items

book_data = {
    "name": book_name.strip(),
    "descriptions": [description.strip()],
    "static": False,
    "type": ["book"],
    "chapters": [],
    "is_locked": False,
}
blueprint, error = validate_item_dict(book_data) # This returns a tuple, if there is an error, the item data is None
if error:
    return f"Error validating book data: {error}"
```
Finally instantiate your item either with the blueprint of the store or your own:

```python
result = self.state_manager.create_item("inventory", None, blueprint)
if not result.success:
    return result.error
```

`get_item` returns `None` if the name isn't found — always guard against this before passing to `create_item`.

```

`ItemStore` is stateless once initialized — instantiate it once in `__init__` and reuse it across all method calls. The blueprints it returns are plain dicts; `create_item` handles making them into live objects with IDs and persisted state.


```python
create_item(
    target_location: str,           # "inventory" or "room"
    target_location_id: int | None, # room ID if placing in a room; None for inventory
    item_creation_data: dict | list[dict],
    quantity: int = 1,
    fallback_to_room: bool = True,
) -> ItemCreationResult
```

If targeting inventory and it's full, `fallback_to_room=True` places the object in the current room. Check `result.location` to know where it actually landed.
```python
result = self.state_manager.create_item("inventory", None, blueprint)
if not result.success:
    return result.error
new_id = result.created_ids[0]
placed_at = result.location
```

#### Removing objects
```python
remove_item(item_id: int, quantity: int = 1) -> ItemRemovalResult
```

`quantity=0` removes the entire stack. Finds the object's location automatically.

#### Mutating object state
```python
set_item_attribute(
    item_id: int,
    key: str,
    value: any,
    quantity: int = 1,
    path: list[str] | None = None,
) -> SetItemAttributeResult
```

Use `path` for nested writes: `path=["dispenser_state"]` writes to `item_data["dispenser_state"][key]`.

**Never write to `item_data` keys directly.** The dict from `find_item` is a live reference into state. Direct writes bypass the stacking system and cause silent bugs on stackable objects.

> ⚠ `SetItemAttributeResult` has no `.error` field. On failure, the reason is in `.message`. Always use `.message` when reading the failure reason on this type.
```python
result = self.state_manager.set_item_attribute(item_id, "charged", False)
if not result.success:
    return result.message  # not .error — this type has no .error field
```

**Working with list fields** — always deepcopy before modifying, never mutate the live list:
```python
import copy
current = copy.deepcopy(item_data.get("chapters", []))
current.append({"title": title, "content": content, "is_locked": False})
self.state_manager.set_item_attribute(item_id, "chapters", current)
```

#### Inventory and room state
```python
get_inventory_state() -> InventoryStateResult
```

Returns a snapshot of inventory and current room contents with pre-formatted strings ready for agent responses.
```python
state = self.state_manager.get_inventory_state()
return f"{state.inventory_summary}\n{state.room_summary}"
```

#### Room data
```python
get_current_room_data() -> RoomDataResult
get_room_data(room_id: int) -> RoomDataResult
get_all_rooms_data() -> list[RoomDataResult]
```

Use `room.room_types` to validate the agent is in the right place:
```python
room = self.state_manager.get_current_room_data()
if "kitchen" not in room.room_types:
    return "You can't do that here."
```

#### Stats
```python
adjust_stat(stat_name: str, amount: int | float) -> StatsResult
get_stats() -> StatsResult
```

Valid stat names: `energy`, `hydration`, `fullness`. Additive — pass negative to decrease.

**Always apply stat costs after confirming success, never before.**
```python
ACTION_COSTS = {"energy": -2.0, "hydration": -1.0}

def _apply_costs(self, costs: dict) -> str:
    parts = []
    for stat, amount in costs.items():
        self.state_manager.adjust_stat(stat, amount)
        parts.append(f"{amount:+.1f} {stat}")
    return ", ".join(parts)
```

#### Navigation and currency
```python
get_current_room_id() -> int
get_current_room_name() -> str
set_current_room(room_id: int | float | str) -> str

get_currency() -> GetCurrencyResult
adjust_currency(amount: int) -> AdjustCurrencyResult
```

### Multi-step operations and rollback

Validate all inputs first. If anything fails mid-way, undo completed steps in reverse order.
```python
created_ids = []
for blueprint in blueprints_to_create:
    result = self.state_manager.create_item("inventory", None, blueprint)
    if not result.success:
        for created_id in reversed(created_ids):
            self.state_manager.remove_item(created_id, quantity=0)
        return f"Failed: {result.error}"
    created_ids.extend(result.created_ids)

# All outputs created — now safe to consume source objects
for source_id in sources_to_consume:
    self.state_manager.remove_item(source_id, quantity=0)
```

### Signals

Fire-and-forget messages to the UI. Always wrap them in `_send_signal`.
```python
# Icon popup (default)
self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/my_icon.png"})

# Icon popup (stronger — for completions and discoveries)
self._send_signal({"type": "show_icon_popup", "icon_path": "...", "popup_type": 2})

# Text popup
self._send_signal({"type": "show_message_popup", "message": "Something happened."})
```

---

## Part 2 — Writing the Tool Definition

Tool definitions live in `tools/tools_builder/my_tools.py`. They tell the agent what a tool is called, what it does, and what arguments it takes.
```python
my_tool_definitions = [
    {
        "type": "function",
        "name": "my_action",
        "description": "A clear description of what the action does and when to use it.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The ID of the object to act on."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    }
]
```

**Function names, argument names, and types must match the Python method exactly.** A mismatch causes a silent dispatch failure — the agent calls the tool and nothing happens.

---

## Part 3 — Registering an Affordance Block

Affordance blocks live in `tools/tools_builder/tool_registry.py`, inside `_build_tool_definitions`. Each block is an entry in `self.tool_definitions`.

### Block structure
```python
"my_block_key": {
    "functions": {
        "my_action": self.my_tool.my_action,  # name must match definition exactly
    },
    "definitions": my_tool_definitions,
    "use_level": "inventory_only",
    "item_types": ["my_object_type"],
    "room_types": ["my_room_type"],               # optional
    "display_information": self.my_tool.get_display_info,      # optional, for the GUI
    "agent_information":   self.my_tool.get_agent_perception,  # optional, passive perception
}
```

### Activation conditions

A block becomes active when **any** of these match:

| Condition | When it fires |
|---|---|
| `"use_level": "always_available"` | Always active |
| `room_types` match | Agent's current room has any listed type |
| `item_types` match | Matching object exists at the location required by `use_level` |

`use_level` controls where objects must be:

| Value | Meaning |
|---|---|
| `"always_available"` | Active regardless of objects or room |
| `"inventory_only"` | Object must be in the agent's inventory |
| `"room_only"` | Object must be in the current room |
| `"dual_use"` | Object can be in either location |

`use_level` is only required when `item_types` is present. A togglable object with `power_toggle: false` will not activate its block even if location matches.

### Block examples

**Room-type block — active when the agent is in a specific room type:**
```python
"darkroom": {
    "functions": {"develop_photo": self.room_tools.darkroom.develop_photo},
    "definitions": darkroom_tools,
    "room_types": ["darkroom"],
    "agent_information": self.room_tools.darkroom.get_perception,
}
```

**Inventory-only item block:**
```python
"special_key": {
    "functions": {"use_special_key": self.room_tools.use_special_key},
    "definitions": special_key_tools,
    "item_types": ["special_key"],
    "use_level": "inventory_only",
}
```

**Dual-use item block — active whether carried or in the room:**
```python
"seat": {
    "functions": {"take_a_seat": self.room_tools.living_room.take_a_seat},
    "definitions": seat_tools,
    "item_types": ["seat"],
    "use_level": "dual_use",
}
```

**Combined room + item (OR logic):**
```python
"fresnel_lens_interior": {
    "functions": {"get_fresnel_rotation": self.lighthouse.lantern.get_fresnel_rotation},
    "definitions": fresnel_lens_tools,
    "room_types": ["fresnel_lens_interior"],
    "item_types": ["fresnel_lens_apparatus"],
    "use_level": "room_only",
    "agent_information": self.lighthouse.lantern.get_fresnel_rotation,
}
```

**Perception-only block — no callable functions, just passive awareness:**
```python
"outdoors_view": {
    "definitions": [],
    "room_types": ["outdoors_view"],
    "agent_information": self.room_tools.garden.get_weather_perception,
}
```

When the agent is in a room tagged `outdoors_view`, weather information is injected into its context every turn — no tool call needed.

### `display_information` vs `agent_information`

**`agent_information`** — what the agent *passively perceives*. Injected into agent context every turn. Must be token-efficient and written from the agent's embodied perspective — only what it would naturally know from being in that situation.

**`display_information`** — what the GUI shows a human observer. Can be omniscient, verbose, or include data the agent shouldn't have. Prioritizes completeness over token cost.

Many simple blocks can share the same function for both. Complex simulation systems need separate implementations because the observer and the agent need fundamentally different pictures.

---

## Initialization Phase Order

**This order is load-bearing. Breaking it causes silent crashes.**
```
Phase 1 — Instantiate services
          (room_tools, garden_manager, images_lab, maze, A-Life, optional services)

Phase 2 — Build tool_definitions
          (_build_tool_definitions — references Phase 1 methods, which must exist first)

Phase 3 — Build toolset_checker
          (make_toolset_checker — needs tool_definitions to exist)

Phase 4 — Services that need the toolset_checker
          (LighthouseController and anything that queries tool availability)

Phase 5 — Tool blocks referencing Phase 4 services
          (_add_lighthouse_tools and similar — appended after Phase 4 init)
```

**The rule:** if a service needs `toolset_checker` → Phase 4. If a tool block references that service → Phase 5, via a dedicated `_add_*_tools()` method, never inside `_build_tool_definitions`.

If you see `AttributeError: 'ToolRegistry' object has no attribute 'X'` during startup, a block is referencing a service that doesn't exist yet at that point in initialization.

### The `toolset_checker`

Phase 4 services receive a `toolset_checker` callable — a function that accepts a block key and returns whether that affordance is currently active. Use it to filter output to only what the agent can currently perceive:
```python
class MyService:
    def __init__(self, state_manager, signal, is_toolset_available=None):
        self.is_toolset_available = is_toolset_available

    def format_events(self, events):
        return "\n".join(
            event.message
            for event in events
            if any(self.is_toolset_available(key) for key in event.affordance_keys)
        )
```

The argument is the primary key of a block in `tool_definitions` (e.g. `"lamp"`, `"seat"`).

---

## Optional External Integrations

For tools that depend on external services or feature flags:
```python
# Step 1 — add a config flag
# [Tools]
# enable_my_service = true

# Step 2 — conditional Phase 1 init
self.my_service = None
if config_manager.get_config("Tools", "enable_my_service"):
    try:
        from tools.tools_folder.services import my_service_handler
        self.my_service = my_service_handler.MyServiceTools()
    except Exception as e:
        print(f"MyService failed to load: {e}")

# Step 3 — register in _add_conditional_tools
def _add_conditional_tools(self, state_manager):
    if self.my_service:
        self.tool_definitions["my_service"] = {
            "functions": {"my_service_action": self.my_service.do_thing},
            "definitions": my_service_tools,
            "item_types": ["my_service_item"],
            "use_level": "dual_use",
        }
```

---

## Part 4 — Choosing a State Pattern

### Pattern 1 — Object-Embedded State

**Use when:** state describes the object itself — a fill level, an on/off toggle, contents, a counter.

The tool class is entirely stateless. All state lives in the object's dict, persisted automatically by `set_item_attribute`. Multiple instances of the same object type each carry independent state naturally.

**Define the initial state in the blueprint:**
```json
{
    "name": "My Dispenser",
    "type": ["furniture", "dispenser"],
    "static": true,
    "stackable": false,
    "dispenser_state": { "contents": {} }
}
```

**Reading:**
```python
result = self.state_manager.find_item(item_id, required_type="dispenser", required_location="room")
if not result.success:
    return result.error
contents = result.item_data.get("dispenser_state", {}).get("contents", {})
```

**Writing — always copy-on-write, never mutate in place:**
```python
current = result.item_data.get("dispenser_state", {}).get("contents", {})
new_contents = dict(current)
new_contents["lemon candy"] -= 1
if new_contents["lemon candy"] <= 0:
    del new_contents["lemon candy"]
self.state_manager.set_item_attribute(item_id, "contents", new_contents, path=["dispenser_state"])
```

The `path` parameter writes to `item_data["dispenser_state"]["contents"]`. Intermediate dicts are created automatically if absent.

---

### Pattern 2 — External System State

**Use when:** the tool manages an independent simulation or system whose state exists completely outside the inventory. The object in the world is a terminal — a way to interact with the system, not a container for its data.

Examples in the codebase: the A-Life lab (`tools/tools_folder/alife_controller.py`), the lighthouse lamp system (`tools/tools_folder/lighthouse_controller.py`).

A dedicated **Manager class** in `tools/tools_folder/tools_helpers/` owns a JSON file and handles all persistence. A **Controller class** in `tools/tools_folder/` wraps the manager and is what the registry instantiates.

**The Manager:**
```python
# tools/tools_folder/tools_helpers/my_system_manager.py
import json
from pathlib import Path

class MySystemManager:
    def __init__(self, base_path: str):
        self.filepath = Path(base_path) / "MySystem_Data" / "my_system_data.json"
        self._state = self._load()

    def _load(self) -> dict:
        if not self.filepath.exists():
            default = {"current_id": "", "records": {}}
            self._save(default)
            return default
        try:
            with open(self.filepath) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            default = {"current_id": "", "records": {}}
            self._save(default)
            return default

    def _save(self, state: dict = None):
        data = state if state is not None else self._state
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2)
```

Key rules: save after every mutation, never batch writes speculatively. On a corrupted or missing file, write and return a clean default rather than crashing.

**The Controller:**
```python
# tools/tools_folder/my_system_controller.py
class MySystemController:
    def __init__(self, state_manager, signal, base_path: str):
        self.state_manager = state_manager
        self._signal_callback = signal
        self.manager = MySystemManager(base_path)

        # Active initialization — resume last state or start fresh
        pointer = self.manager.get_pointer()
        if pointer["current_id"]:
            self._resume(pointer["current_id"])
        else:
            self._create_new()

    def do_action(self) -> str:
        result = self.simulation.step()
        if result.success:
            self.manager.set_pointer(self.simulation.current_id)
        return result.message
```

Active initialization is the key distinction from Pattern 1. On every startup the controller reads saved state and either resumes or starts fresh — the world always lands in a consistent state.

**Two sub-variants exist within Pattern 2:**

*Single-file snapshot* (Lighthouse): one JSON file holds the complete current state, overwritten on every action. Derived state is never persisted — only source values go to JSON, everything else is recomputed on load.

*Registry + archive files* (A-Life): a small metadata file tracks a pointer and a registry of all simulation runs. Each run is archived as its own file. Right choice when the system has multiple independent sessions the agent can switch between.

### Choosing

| | Pattern 1 — Object-Embedded | Pattern 2 — External System |
|---|---|---|
| State lives in | Object dict, inventory system | JSON files in a dedicated data directory |
| Tool class holds | `state_manager` only | Manager + simulation objects |
| Persistence | Automatic via `set_item_attribute` | Dedicated Manager class |
| Initialization | None — stateless | Active: resume saved state or create fresh |
| Multiple instances | Each object has independent state naturally | Single system per tool type |
| Good for | Fill levels, toggles, contents, counters | Simulations, multi-session systems, anything with its own lifecycle |

---

## Enabling Purchase

Add the object's file path to `price_ranges` in `tools/tools_folder/auction_house.py`:
```python
"furniture/my_new_items.json": {"minimum": 100, "maximum": 200, "available_for_purchase": True}
```

---

## Testing

Run `game.py` with the `user_player` flag to bypass the agent memory system and interact with your object directly in the game:
```
python game.py user_player
```

---

## Quick Reference — What Not to Do

**❌ Bypass the facade**
```python
self.state_manager.inventory_service.some_internal_method(...)  # wrong
# If a method you need is missing from the facade, request it be added
```

**❌ Ignore result.success**
```python
# Wrong — crashes if lookup failed
result = self.state_manager.find_item(item_id)
name = result.item_data["name"]

# Correct
if not result.success:
    return result.error
name = result.item_data["name"]
```

**❌ Mutate item_data directly**
```python
result.item_data["charged"] = False                               # wrong
self.state_manager.set_item_attribute(item_id, "charged", False)  # correct
```

**❌ Apply stat costs before confirming success**
```python
# Wrong — agent pays even when the action fails
self.state_manager.adjust_stat("energy", -5)
result = self.state_manager.do_something()
if not result.success:
    return result.error

# Correct — costs come after success
result = self.state_manager.do_something()
if not result.success:
    return result.error
self.state_manager.adjust_stat("energy", -5)
```

**❌ Return non-strings from agent-facing methods**
```python
def get_info(self) -> dict:                # wrong
    return self.state_manager.get_stats().stats

def get_info(self) -> str:                 # correct
    stats = self.state_manager.get_stats()
    return f"Current stats: {stats.stats}"
```

**❌ Reference Phase 4 services inside `_build_tool_definitions`**
```python
# Wrong — service doesn't exist yet at this point in init
"lantern": {"functions": {"do_thing": self.lighthouse.do_thing}, ...}

# Correct — use a dedicated method called after Phase 4
def _add_lighthouse_tools(self):
    self.tool_definitions["lantern"] = {"functions": {"do_thing": self.lighthouse.do_thing}, ...}
```