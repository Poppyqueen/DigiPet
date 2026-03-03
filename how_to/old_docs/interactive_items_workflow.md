# Workflow: Creating Interactive Items and Tools

This guide details the process for adding new interactive items (like furniture or appliances)
and their associated tools to the DigiPet codebase.

---

## 1. Define the Items

Create JSON blueprints for your items in `inventory_items/items_provider/items_data/`.

- **Location**: Choose an appropriate subdirectory (e.g., `furniture/`, `food_n_drinks/`).
- **Structure**:
    ```json
    {
        "name": "My Interactive Item",
        "descriptions": ["A description of the item."],
        "static": true,
        "type": ["furniture", "my_new_type"],
        "stackable": false,
        "custom_state_key": 0
    }
    ```
- **Adding a new type**: If your item needs a new type tag (e.g., `my_new_type`), you need to
  do two things in `inventory_items/item_pydantic_models.py`:
  1. Add the string to the `item_types` list.
  2. If the new type introduces required fields, create a field contract mixin and register it:
      ```python
      class MyNewTypeFields(BaseModel):
          model_config = ConfigDict(extra="allow")
          custom_state_key: int = Field(description="Tracks the current state of this item.")

      TYPE_FIELD_CONTRACTS["my_new_type"] = MyNewTypeFields
      ```
     Types with no required fields beyond the base (name, descriptions, static, type, stackable)
     do not need a mixin — just adding to `item_types` is sufficient.

---

## 2. Implement the Logic (Tool Class)

Create a new Python file in `tools/tools_folder/` (e.g., `my_item_tools.py`).

### Class Structure

Your class receives the `state_manager` (the `InventoryHouseManager` facade) and a
`signal_callback`. The facade is the **only** dependency you should hold — do not store
references to sub-services such as `inventory_service`.

```python
from inventory_items.items_provider.item_store import ItemStore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager

class MyItemTools:
    def __init__(self, state_manager, signal=None):
        self.state_manager: InventoryHouseManager = state_manager
        self.item_store = ItemStore("inventory_items/items_provider/items_data")
        self._signal_callback = signal

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from {self.__class__.__name__}: {e}")
```

### Accessing Item Data

Use `state_manager.find_item()` to look up and validate items. It returns an
`ItemLookupResult` — **always check `.success` before accessing `.item_data`**.

```python
result = self.state_manager.find_item(
    item_id,
    required_type="my_new_type",    # optional — item's type list must include this
    required_location="inventory"   # "inventory", "room", or "accessible"
)
if not result.success:
    return result.error

item_data = result.item_data  # safe to access only after success check
```

`required_location` values:

| Value | Meaning |
|---|---|
| `"inventory"` | Item must be in the player's inventory |
| `"room"` | Item must be in the current room |
| `"accessible"` | Item must be in inventory **or** the current room |
| `None` (default) | Item can be anywhere in state |

> **Do not call `inventory_service.get_validated_item_data()` directly.**
> That method is deprecated and exists only as a migration shim. All item lookups must go
> through `state_manager.find_item()`.

### Modifying Item State

Use `state_manager.set_item_attribute()` to update any field on an existing item.
**Never modify `item_data` keys directly** — the dict returned by `find_item` is a live
reference into the state store. Writing to it directly bypasses the stacking system and
will cause silent bugs on stackable items: the change will not trigger a stack split, and
multiple items in a stack will incorrectly share state.

```python
# CORRECT
attr_result = self.state_manager.set_item_attribute(item_id, "custom_state_key", new_value)
if not attr_result.success:
    return f"Failed to update item: {attr_result.message}"

# CORRECT — nested write into a sub-dict field using the path parameter
attr_result = self.state_manager.set_item_attribute(
    item_id, "contents", new_dict, path=["dispenser_state"]
)
# writes item_data["dispenser_state"]["contents"] = new_dict
# intermediate dicts are created automatically if absent

# WRONG — direct key modification, bypasses stacking logic entirely
item_data["custom_state_key"] = new_value
```

`set_item_attribute` handles stacking fingerprint comparison, stack splitting when needed,
and state persistence automatically.

> If you see `item_data["key"] = value` anywhere in the codebase, mark it with
> `# TODO: DIRECT ITEM KEY MOD` so it can be updated.

**Always check `.success` on the return value** — a failure here will silently leave
state inconsistent if not handled.

### Working with List Fields

When the attribute you are updating is a list (e.g. chapters, descriptions, effects),
always work on a `deepcopy` of the current value — never mutate the list in place before
passing it to `set_item_attribute`. Mutating the live list first poisons the
before-fingerprint and prevents stack splits from triggering correctly.

```python
import copy

# CORRECT
current = copy.deepcopy(item_data.get("chapters", []))
current.append({"title": chapter_title, "content": content})
self.state_manager.set_item_attribute(item_id, "chapters", current)

# WRONG — appending to the live reference before calling set_item_attribute
item_data["chapters"].append({"title": chapter_title, "content": content})
self.state_manager.set_item_attribute(item_id, "chapters", item_data["chapters"])
```

### Removing Items

Use `state_manager.remove_item()` to delete an item from wherever it currently is.
Always check the result.

```python
removal_result = self.state_manager.remove_item(item_id)
if not removal_result.success:
    return f"Could not remove item: {removal_result.error}"
```

To remove only part of a stack, pass `quantity`:

```python
removal_result = self.state_manager.remove_item(item_id, quantity=3)
```

Pass `quantity=0` to remove the entire stack regardless of size. The default (`quantity=1`)
removes one unit. The method finds the item's location automatically — you do not need to
specify inventory or room.

> **Note:** The facade does not currently expose an `internal` flag on `remove_item`.
> Inventory refresh signals are always sent on removal. If suppressing them during an
> internal transaction is needed, this is a known gap — track as a future facade addition.

### Creating Items

Use `state_manager.create_item()` to add new items to the world. Fetch blueprints from
`ItemStore`. The facade handles inventory-full fallback automatically — by default
(`fallback_to_room=True`) items that don't fit in inventory are placed in the current room
instead. Check `.location` on the result if you need to know where they actually landed.

```python
blueprint = self.item_store.get_item("My Interactive Item")
creation_result = self.state_manager.create_item(
    target_location="inventory",
    target_location_id=None,       # None when targeting inventory; room ID when targeting a room
    item_creation_data=blueprint,
    quantity=1,                    # how many to create; defaults to 1
    fallback_to_room=True,         # if inventory full, place in current room instead
)

if not creation_result.success:
    return f"Could not create item: {creation_result.error}"

new_id           = creation_result.created_ids[0]
actual_location  = creation_result.location  # may differ from requested if fallback triggered
```

You can also pass a list of blueprints to create multiple different items in one call:

```python
creation_result = self.state_manager.create_item("inventory", None, [blueprint_a, blueprint_b])
```

### Multi-Step Operations and Rollback

If your action modifies state in more than one step (e.g. create new items then consume
source ingredients), you must implement a rollback path. The rule is:

1. Validate **all** inputs before touching any state.
2. Create output items first.
3. Consume / remove source items only after all creation succeeds.
4. On any failure mid-way, undo completed steps in reverse order.

```python
created_ids = []

for blueprint in blueprints_to_create:
    result = self.state_manager.create_item("inventory", None, blueprint)
    if not result.success:
        # Roll back already-created items before returning
        for created_id in reversed(created_ids):
            self.state_manager.remove_item(created_id, quantity=0)
        return f"Failed to create item: {result.error}"
    created_ids.extend(result.created_ids)

# All outputs created — now safe to consume source items
for source_id in sources_to_consume:
    self.state_manager.remove_item(source_id, quantity=0)
```

### Adjusting Stats

Use `state_manager.adjust_stat()` for any stat change. Define cost dictionaries at module
level rather than scattering magic numbers through your methods, and apply them through a
shared helper:

```python
MY_ACTION_COSTS = {
    "energy":    -0.5,
    "hydration": -0.3,
}

def _apply_costs(self, cost_dict, multiplier=1):
    for stat, amount in cost_dict.items():
        self.state_manager.adjust_stat(stat, amount * multiplier)
```

Valid stat names: `energy`, `hydration`, `fullness`.

`adjust_stat` does not return a result object — stat adjustments are fire-and-forget.

### UI Feedback

```python
self._send_signal({"type": "show_message_popup", "message": "Action complete!"})

# Standard popup (brief)
self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/my_icon.png"})

# Stronger popup (used for completions and discoveries)
self._send_signal({"type": "show_icon_popup", "icon_path": "...", "popup_type": 2})

# Inventory refresh signals (sent automatically by create_item / remove_item,
# but can be triggered manually if you update state through other paths)
self._send_signal({"type": "room_inventory",   "item_list": [...]})
self._send_signal({"type": "player_inventory", "item_list": [...]})
```

---

## 2b. Managing Tool State

Some tools are stateless — they just read and write item data via `state_manager`. Others
need to persist state of their own, either because the state belongs to the item itself
(like a dispenser's inventory of candies) or because the tool manages an independent
simulation system that exists outside the inventory entirely (like the lighthouse or the
ALife lab).

There are two established patterns. Choose the one that matches your tool's nature.

---

### Pattern 1 — Item-Embedded State

**Use when:** The state describes the item itself. There's no simulation running
independently — the item just has fields that change over time (fill level, contents,
on/off state, etc.).

**How it works:** The tool class is entirely stateless. All state lives inside the item's
dict in the inventory system, persisted automatically by `set_item_attribute`. Multiple
instances of the same item type each carry their own independent state naturally, since
each is a separate dict in the store.

#### Defining the initial state

Embed the state fields directly in the item's JSON blueprint. They will be present on the
item dict from the moment it is created.

```json
{
    "name": "My Dispenser",
    "type": ["furniture", "dispenser"],
    "static": true,
    "stackable": false,
    "dispenser_state": {
        "contents": {}
    }
}
```

There is no `__init__` work to do — the tool class constructor only stores `state_manager`
and `signal`. No manager object, no file path, no load call.

#### Reading state

Call `find_item()` as usual, then read the sub-key from `item_data`:

```python
def examine_dispenser(self, item_id: int):
    result = self.state_manager.find_item(item_id, required_type="dispenser", required_location="room")
    if not result.success:
        return result.error

    item_data = result.item_data
    dispenser_state = item_data.get("dispenser_state", {})
    contents = dispenser_state.get("contents", {})
    total = sum(contents.values())
    return f"The dispenser has {total} candies left."
```

#### Writing state

Always build a new dict (copy-on-write) and pass it to `set_item_attribute` with
`path=` pointing at the parent sub-key. Never mutate `item_data` or any nested dict
inside it directly.

```python
# Read current contents
current_contents = item_data.get("dispenser_state", {}).get("contents", {})

# Build modified copy
new_contents = dict(current_contents)
new_contents[selected_candy] -= 1
if new_contents[selected_candy] <= 0:
    del new_contents[selected_candy]

# Single authoritative write
self.state_manager.set_item_attribute(
    item_id, "contents", new_contents, path=["dispenser_state"]
)
```

The `path` parameter tells `set_item_attribute` to write at
`item_data["dispenser_state"]["contents"]` rather than at the top level. Intermediate
dicts are created automatically if absent. The stacking fingerprint comparison uses the
top-level path segment (`"dispenser_state"` in this case), so nested writes on
non-stacking keys are handled correctly.

> **Why copy-on-write matters here too.** `item_data` is a live reference into the state
> store. If you mutate a nested dict directly before calling `set_item_attribute`, you
> corrupt the before-fingerprint that `set_item_attribute` uses to detect whether a stack
> needs splitting. Always build a fresh dict from the current values, then pass it in.

---

### Pattern 2 — External System State

**Use when:** The tool manages an independent simulation or system whose state exists
completely outside the inventory. The system has its own lifecycle — it can be running,
paused, resumed across sessions — and the item in the world is just a terminal to interact
with it, not the container for its data.

Examples: the ALife simulation lab, the lighthouse lamp system.

**How it works:** A dedicated Manager class in `tools/tools_folder/tools_helpers/` owns a
JSON file and handles all load/save. The Controller class in `tools/tools_folder/` wraps
the manager, and is what the registry actually instantiates. The controller receives
`base_path` from the registry at construction time and passes it down to the manager,
which creates its own subdirectory inside it.

#### The Manager class (persistence layer)

The manager's only responsibilities are: know where the file is, load it on init, save
it after every mutation. It holds the in-memory state dict and exposes methods to read
and update it.

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

    def get_pointer(self) -> dict:
        return {"current_id": self._state.get("current_id", "")}

    def set_pointer(self, record_id: str):
        self._state["current_id"] = record_id
        self._save()
```

Key rules for the manager:
- Call `_save()` after every mutation — never batch writes speculatively.
- Create the data directory in `_save()` using `mkdir(parents=True, exist_ok=True)` so
  the first write always succeeds even if the directory doesn't exist yet.
- On a corrupted or missing file, write and return a clean default rather than crashing.

#### The Controller class (game boundary layer)

The controller is what the registry instantiates. It receives `base_path` and passes it
to the manager. It also holds a reference to the simulation/system object and coordinates
between them: delegate the action to the system, then tell the manager to persist what
changed.

```python
# tools/tools_folder/my_system_controller.py
from tools.tools_folder.tools_helpers.my_system_manager import MySystemManager
from tools.tools_folder.tools_helpers.my_simulation import MySimulation

class MySystemController:
    def __init__(self, state_manager, signal, base_path: str):
        self.state_manager = state_manager
        self._signal_callback = signal

        self.manager = MySystemManager(base_path)
        self.simulation = MySimulation()

        # Active initialization — resume last known state or start fresh
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

Active initialization is the key difference from Pattern 1. On every startup the
controller reads the saved pointer, decides whether a previous state can be resumed, and
either loads it or creates a fresh one. The game world always lands in a consistent state
regardless of how it was last left.

#### Two sub-variants

Both ALife and Lighthouse follow this pattern, but differ in how they structure their
persisted data:

**Single-file snapshot** (Lighthouse): One JSON file holds the complete current state of
the simulation as a flat snapshot. Every action results in a full overwrite of the file.
On load, the state is deserialized field-by-field into typed objects (dataclasses). Derived
state is never persisted — only source values (`PhysicalState`, `Controls`) go to JSON;
everything else is recomputed on load.

```
Lighthouse_Data/
    lighthouse_data.json    ← complete lamp + lantern room state, overwritten on every action
```

**Registry + archive files** (ALife): A small metadata JSON tracks a pointer (currently
active simulation ID and tick) plus a registry of all known simulations. Each simulation
run is archived as its own file when created. On load the controller reads the pointer,
finds the corresponding archive file path in the registry, and loads that file into the
simulation object.

```
ALife_Data/
    alife_data.json             ← pointer + simulation registry (small, overwritten often)
    simulations/
        SIM_20240101_120000_1234567890.json   ← individual simulation archive
        SIM_20240102_093000_9876543210.json
        ...
```

The registry variant is the right choice when the system has multiple independent runs or
sessions that the agent can switch between. The single-file variant is right when there is
only ever one active state to track.

#### When to save

Both variants save after every mutation. For the single-file variant this means a full
`_save_state()` call at the end of every action method — even if the action only changed
one value. For the registry variant, `_save()` is called inside every mutating method on
the manager, and archive files are written once at creation time and never modified again.

The pattern is always: mutate in memory first, then save. Never try to write partial state
or defer saves to a later flush.

---

### Choosing the right pattern

| | Pattern 1 — Item-Embedded | Pattern 2 — External System |
|---|---|---|
| State lives in | Item dict, inventory system | JSON files in a dedicated data directory |
| Tool class holds | `state_manager` only | Manager + simulation objects |
| Persistence owner | Inventory system (automatic) | Dedicated Manager class |
| Initialization | None — tool class is stateless | Active: load saved state, resume or create fresh |
| Multiple instances | Each item has independent state naturally | Single system per tool type |
| Good for | Item fill levels, on/off state, contents, counters | Simulations, multi-session systems, anything with its own lifecycle |

---

## 3. Register the Tools (Detailed How-To inside `how_to/tools.md`)

### A. `tools/tools_builder/tool_registry.py`

1. **Import** your class at the top.
2. **Instantiate** it in `__init__`:
    ```python
    self.my_tools = MyItemTools(state_manager, signal)
    ```
3. **Add** an entry to `self.tool_definitions` in `_init_unified_tool_definitions`:
    ```python
    "my_new_type": {
        "functions": {
            "my_action": self.my_tools.my_action
        },
        "definitions": my_item_tools_json,
        "item_types": ["my_new_type"],
        "use_level": "dual_use"  # or "room_type", "inventory_only", "room_only"
    }
    ```

### B. `tools/tools_builder/my_tools.py`

Add the JSON schema definition for your tool functions:

```python
my_item_tools_json = [
    {
        "type": "function",
        "name": "my_action",
        "description": "Description of what the action does.",
        "parameters": { ... }
    }
]
```

---

## 4. Enable Purchase (Optional)

If the item should be buyable, add its file path to `price_ranges` in
`tools/tools_folder/auction_house.py`:

```python
"furniture/my_new_items.json": { "minimum": 100, "maximum": 200, "available_for_purchase": True }
```

---

## 5. Verification

You can run game.py with the flag "user_player" to bypass the agent memory system and test your item directly in the game.

---

## Appendix A: state_manager Public API

`InventoryHouseManager` is a thin facade that delegates all calls to the appropriate
internal service. The complete set of methods relevant to tool implementation is below.
Methods marked ⚠ have known issues or pending changes noted inline.

### Item Methods

#### `find_item(item_id, required_type=None, required_location=None)` → `ItemLookupResult`

Unified item lookup with optional type and location filters. The primary entry point for
all item access.

```python
result = self.state_manager.find_item(item_id, required_type="seed", required_location="inventory")
if not result.success:
    return result.error
item_data = result.item_data
```

#### `create_item(target_location, target_location_id, item_creation_data, quantity=1, fallback_to_room=True)` → `ItemCreationResult`

Creates one or more items. `item_creation_data` accepts a single dict or a list of dicts.
When targeting inventory with `fallback_to_room=True`, overflow goes to the current room.

```python
result = self.state_manager.create_item("inventory", None, blueprint)
result = self.state_manager.create_item("room", room_id, blueprint)
result = self.state_manager.create_item("inventory", None, [bp_a, bp_b], quantity=3)
```

#### `remove_item(item_id, quantity=1)` → `ItemRemovalResult` ⚠

Removes units of an item from wherever it currently is. `quantity=0` removes the entire
stack. Locates the item automatically.

```python
result = self.state_manager.remove_item(item_id)              # remove 1 unit
result = self.state_manager.remove_item(item_id, quantity=0)  # remove entire stack
```

> ⚠ No `internal` flag is exposed — inventory refresh signals are always sent. Suppressing
> them during internal transactions is a known gap requiring a future facade addition.

#### `set_item_attribute(item_id, key, value, quantity=1, path=None)` → `SetItemAttributeResult` ⚠

Modifies a single attribute on an item, handling stack splitting automatically. Use `path`
for nested writes into sub-dicts.

```python
result = self.state_manager.set_item_attribute(item_id, "filled", True)
result = self.state_manager.set_item_attribute(item_id, "contents", data, path=["dispenser_state"])
```

> ⚠ `SetItemAttributeResult` is inconsistent with the other result types — see Appendix B.

### Stat Methods

#### `adjust_stat(stat_name, amount)` → `None`

Adjusts a stat by the given amount (positive or negative). No return value.

Valid stat names: `energy`, `hydration`, `fullness`.

#### `get_stats(internal=False)` → `str | dict`

Returns current stats. `internal=False` returns a formatted string; `internal=True`
returns the raw dict.

### Room / Location Methods

#### `get_current_room_id()` → `int`

Returns the current room ID as an integer.

#### `get_current_room_name()` → `str`

Returns the display name of the current room.

#### `get_room_name(room_id)` → `str`

Returns the display name for any room by its ID.

#### `set_current_room(room_id)` → result

Moves the player to the specified room. Accepts int, float, or str — coerced to int
internally.

---

## Appendix B: Result Models

All item operations return typed Pydantic result objects. The models validate field
consistency on construction — you cannot accidentally build a success result without an
ID, or a failure result without an error message.

### `ItemLookupResult`

```
success        bool         Whether the lookup passed all filters.
item_data      dict | None  Live reference into state store. None on failure.
location       str | None   "inventory" or "room". None on failure.
location_id    int | None   Room ID when location=="room", else None.
location_name  str | None   Room name when location=="room", else None.
error          str | None   Failure reason. None on success.
```

```python
result = state_manager.find_item(item_id)
if not result.success:
    return result.error      # always present on failure

item      = result.item_data   # live reference — do not write directly
location  = result.location    # "inventory" or "room"
```

### `ItemCreationResult`

```
success      bool          Whether at least one item was created.
created_ids  list[int]     IDs of every item or stack created/merged into. Empty on failure.
location     str | None    Where items actually landed. None on failure.
message      str           Always populated. Safe to append without checking success first.
error        str | None    Failure reason. None on success.
```

```python
result = state_manager.create_item(...)
if not result.success:
    return result.error

new_id   = result.created_ids[0]
placed   = result.location    # may differ from requested if fallback triggered
```

### `ItemRemovalResult`

```
success   bool        Whether the removal succeeded.
message   str         Always populated. Mirrors error on failure.
error     str | None  Failure reason. None on success.
```

```python
result = state_manager.remove_item(item_id)
if not result.success:
    return result.error   # also available as result.message
```

### `SetItemAttributeResult` ⚠

```
success   bool   Whether the attribute was set.
message   str    Human-readable result. Always populated.
```

> ⚠ **This model does not follow the same conventions as the others.** Specifically:
>
> - No `.error` field — failure reason is in `.message` instead.
> - No `.ok()` / `.fail()` convenience constructors.
> - `.message` carries both success descriptions and failure reasons, so you cannot safely
>   append it to an output list without checking `.success` first — unlike `ItemCreationResult`
>   and `ItemRemovalResult` where `.message` is always safe to use.
>
> **Recommended fix** — align with the other result types:
> ```python
> class SetItemAttributeResult(BaseModel):
>     success: bool
>     message: str
>     error: str | None = None
>
>     @classmethod
>     def ok(cls, message: str) -> SetItemAttributeResult:
>         return cls(success=True, message=message, error=None)
>
>     @classmethod
>     def fail(cls, error: str) -> SetItemAttributeResult:
>         return cls(success=False, message=error, error=error)
> ```
>
> Until this is changed, always use `.message` to read the reason — `.error` does not exist.

```python
result = state_manager.set_item_attribute(item_id, "key", value)
if not result.success:
    return result.message   # .error does not exist on this type
```