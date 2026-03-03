# State Manager API — Developer Guide

**Audience:** Developers building agent tools that interact with game state
**System:** Pygame + AI Agent hybrid — `InventoryHouseManager` as the state facade

---

## Table of Contents

1. [Overview: What Is This System?](#1-overview)
2. [Why Use the API Facade?](#2-why-use-the-api-facade)
3. [Architecture at a Glance](#3-architecture-at-a-glance)
4. [Creating a Tool: Anatomy and Setup](#4-creating-a-tool)
5. [API Reference — All Public Methods](#5-api-reference)
6. [Return Objects Reference](#6-return-objects-reference)
7. [Interaction Patterns — How to Do Things](#7-interaction-patterns)
8. [Signals](#8-signals)
9. [Full Example Tool](#9-full-example-tool)
10. [What Not to Do](#10-what-not-to-do)

---

## 1. Overview

This system combines a **Pygame game simulation** with an **AI agent** that operates inside that simulation as an in-world entity. The agent perceives and acts on the game world through **tools** — Python classes that expose methods the agent can call.

Tools can do two fundamentally different things:

- **Stateless work** — web search, text generation, external API calls. These don't touch the game at all. See `AISearXNG` as a reference for this pattern.
- **Stateful work** — reading and modifying the game world: inventory, stats, rooms, currency. These tools receive a `state_manager` handle and interact with game state exclusively through it.

This guide is about the **stateful** category.

The state manager is an instance of `InventoryHouseManager`. It is the **single authoritative interface** for any tool that wants to read or write game state. You receive it as a constructor argument. You do not instantiate it yourself, and you do not reach past it into its internals.

---

## 2. Why Use the API Facade?

The `InventoryHouseManager` is a facade over several internal service objects:

- `InventoryService` — item creation, lookup, removal, attribute mutation
- `RoomManager` — room navigation and data
- `StatTracker` — pet/player stats
- `PetStateManager` — emotes, steps, currency

You might be tempted to do this:

```python
# ❌ DO NOT DO THIS
self.state_manager.inventory_service.some_internal_method(...)
self.state_manager.pet_state_manager.set_current_emote(emote)
```

There are several reasons this is wrong:

**Internal APIs are unstable.** The service classes are implementation details. Their method names, signatures, and existence can change. The facade's public interface is what's guaranteed to be stable.

**Bypassing the facade skips validation.** Methods on the facade perform type checking, location validation, error normalization, and stacking logic. Calling internal methods directly means you skip all of that and may corrupt state silently.

**Return types become unpredictable.** The facade always returns typed result objects (`ItemLookupResult`, `ItemCreationResult`, etc.) with a consistent `.success` / `.message` / `.error` shape. Internal methods may return raw strings, tuples, or nothing at all.

**Circular dependency risk.** The services have carefully resolved dependencies between them. Bypassing the facade and calling one service from inside another (outside of the controlled setup in `InventoryHouseManager.__init__`) can create subtle ordering bugs.

The only exception is `BaseTools`, which has a narrow documented bypass for `drop_item` and `pick_up_item`. Don't treat that as a pattern to follow — it's a known technical debt, explicitly marked as such in the source.

---

## 3. Architecture at a Glance

```
Game Engine / Orchestrator
        │
        ▼
InventoryHouseManager   ◄──── Your tool receives this
  (public facade)
        │
   ┌────┴────────────────────┐
   │                         │
InventoryService         RoomManager
ItemLookupResult         RoomDataResult
ItemCreationResult
ItemRemovalResult
SetItemAttributeResult
        │
   StatTracker          PetStateManager
   StatsResult          AdjustCurrencyResult
                        GetCurrencyResult
        │
   StateStore  ◄──── Reads/writes persistent JSON state
```

Your tool sits entirely above `InventoryHouseManager`. It never sees anything below it.

---

## 4. Creating a Tool

### Minimal Structure

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
        """Safely fire a UI signal. No-op if no callback is registered."""
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Signal error in {self.__class__.__name__}: {e}")

    def do_something(self) -> str:
        # Your logic here — always return a str for agent-facing methods
        ...
```

### Constructor Parameters

| Parameter | Type | Purpose |
|---|---|---|
| `state_manager` | `InventoryHouseManager` | All game state access |
| `signal_callback` | `callable \| None` | Fire UI events (popups, sounds). Optional. |

The game engine passes both when registering your tool. If your tool has no reason to send signals, you may omit the parameter, but keeping it is recommended for forward compatibility.

### Return Types

Methods exposed as **agent tools** should always return a `str`. The agent consumes plain text. Use the `.message` and `.error` fields from result objects to build your return string.

Methods used only **internally** (helpers, validators) may return whatever is convenient.

---

## 5. API Reference

All methods below are on `self.state_manager` (an `InventoryHouseManager` instance).

---

### Item Lookup

```python
find_item(
    item_id: int,
    required_type: str | None = None,
    required_location: Literal["inventory", "room", "accessible"] | None = None,
) -> ItemLookupResult
```

Locate an item anywhere in game state, with optional filters.

| `required_location` | Meaning |
|---|---|
| `None` | Search the entire state — inventory and all rooms |
| `"inventory"` | Must be in the player's inventory |
| `"room"` | Must be in any room |
| `"accessible"` | Inventory **or** current room only |

`required_type` checks against the item's `type` list. For example, `required_type="seed"` will only match items whose `type` field contains `"seed"`.

Always check `result.success` before using `result.item_data`.

---

### Item Creation

```python
create_item(
    target_location: str,          # "inventory" or "room"
    target_location_id: int | None, # Room ID if placing in a room; None for inventory
    item_creation_data: dict | list[dict],
    quantity: int = 1,
    fallback_to_room: bool = True,
) -> ItemCreationResult
```

Create one or more items. Pass a dict for a single item template, or a list of dicts to create several different items in one call.

If `target_location="inventory"` and the inventory is full, and `fallback_to_room=True`, the item is placed in the current room instead. The result's `.location` field tells you where it actually ended up.

Item template dict format:
```python
item_data = {
    "name": "Apple",
    "type": ["food", "consumable"],
    "descriptions": ["A crisp apple."],
    "static": False,
    # ... any additional custom fields
}
```

---

### Item Removal

```python
remove_item(
    item_id: int,
    quantity: int = 1,
) -> ItemRemovalResult
```

Remove one or more units of an item from wherever it currently is. Pass `quantity=0` to remove the entire stack. The item does not need to be in a specific location — the method finds it.

---

### Item Attribute Mutation

```python
set_item_attribute(
    item_id: int,
    key: str,
    value: any,
    quantity: int = 1,
    path: list[str] | None = None,
) -> SetItemAttributeResult
```

Modify a field on an item in-place. The item is found automatically regardless of location.

Use `path` to write to a nested key:
```python
# Sets item_data["dispenser_state"]["contents"] = new_value
state_manager.set_item_attribute(item_id, "contents", new_value, path=["dispenser_state"])
```

`quantity` controls how many units of a stack are affected. Pass `0` or a number `>=` the stack size to affect all units.

This method handles stack re-evaluation automatically. You do not need to manage stacking logic yourself.

---

### Inventory State

```python
get_inventory_state() -> InventoryStateResult
```

Returns a complete snapshot of the player's inventory and the current room's items. Includes pre-formatted display strings, agent-readable summaries, and typed `InventoryItemEntry` lists.

This is the right method for context-building and "what do I have?" type tools.

---

### Room Data

```python
get_current_room_data() -> RoomDataResult

get_room_data(room_id: int) -> RoomDataResult

get_all_rooms_data() -> list[RoomDataResult]
```

Retrieve room information. `get_current_room_data()` returns the room the player is currently in.

`RoomDataResult.room_types` is a list of strings like `["planting_garden"]` or `["service_room", "indoor"]`. Use this to validate player location before allowing an action.

`RoomDataResult.extra_data` contains any non-standard fields defined on the room, such as custom plot data.

---

### Stats

```python
get_stats() -> StatsResult

adjust_stat(
    stat_name: str,  # e.g. "fullness", "hydration", "energy"
    amount: int | float,
) -> StatsResult
```

Read or modify pet/player stats. `adjust_stat` is additive — pass a negative number to decrease. The stat name is case-insensitive and whitespace-stripped.

---

### Currency

```python
get_currency() -> GetCurrencyResult

adjust_currency(amount: int) -> AdjustCurrencyResult
```

Read or modify the shared currency pool. `amount` is additive; use negative values to deduct.

---

### Navigation

```python
set_current_room(room_id: int | float | str) -> str
```

Move the player to a different room. Returns a narrative string describing the transition. The ID is coerced to `int` internally.

---

### Emotes and Steps

```python
get_current_emote() -> str
get_possible_emotes() -> str

add_steps(amount: int) -> None
get_steps() -> int
```

Read and modify the pet's emote and step count. These are mainly used for agent context construction and game loop bookkeeping.

---

## 6. Return Objects Reference

All state-modifying methods return a typed result object. Every result object follows the same contract:

| Field | Type | Always Present? | Meaning |
|---|---|---|---|
| `success` | `bool` | ✅ | Whether the operation succeeded |
| `message` | `str` | ✅ (most types) | Human-readable outcome. Safe to return to agent. |
| `error` | `str \| None` | ✅ | `None` on success; reason string on failure |

On success: `error` is `None`, data fields are populated.
On failure: `error` is a string, data fields are `None` or empty.

### ItemLookupResult

Additional fields on success:

| Field | Type | Meaning |
|---|---|---|
| `item_data` | `dict` | The raw item dict. Mutable reference into state. |
| `location` | `"inventory" \| "room"` | Where the item was found |
| `location_id` | `int \| None` | Room ID if in a room |
| `location_name` | `str \| None` | Room name if in a room |

### ItemCreationResult

| Field | Type | Meaning |
|---|---|---|
| `created_ids` | `list[int]` | IDs of all created/merged stacks |
| `location` | `"inventory" \| "room"` | Where items were actually placed |

### InventoryStateResult

| Field | Type | Meaning |
|---|---|---|
| `inventory_items` | `list[InventoryItemEntry]` | Typed inventory entries |
| `room_items` | `list[InventoryItemEntry]` | Typed current-room entries |
| `inventory_summary` | `str` | Ready-to-use agent string, e.g. `"Items in your inventory: Apple (ID:000042) x1"` |
| `room_summary` | `str` | Ready-to-use agent string for room |
| `inventory_display_strings` | `list[str]` | Per-item display strings for GUI |
| `room_display_strings` | `list[str]` | Per-item display strings for GUI |
| `room_id` | `int` | Current room ID at query time |
| `room_name` | `str` | Current room name at query time |

### StatsResult

| Field | Type | Meaning |
|---|---|---|
| `stats` | `dict` | Full stats dict, e.g. `{"fullness": 72.5, "hydration": 60.0, "energy": 88.0}` |

### AdjustCurrencyResult / GetCurrencyResult

| Field | Type | Meaning |
|---|---|---|
| `currency` | `int` | Current currency value after the operation |

---

## 7. Interaction Patterns

### Pattern 1: Find → Validate → Act

The most common pattern. Look up an item, check it meets requirements, then do something with it or to it.

```python
def use_medkit(self, item_id: int) -> str:
    # 1. Find the item — must be in inventory and be a healing item
    result = self.state_manager.find_item(
        item_id,
        required_type="healing",
        required_location="inventory",
    )
    if not result.success:
        return result.error  # e.g. "Item 42 not found in inventory."

    item_data = result.item_data
    heal_amount = item_data.get("heal_amount", 10)

    # 2. Apply the effect
    stat_result = self.state_manager.adjust_stat("energy", heal_amount)
    if not stat_result.success:
        return stat_result.error

    # 3. Consume the item
    remove_result = self.state_manager.remove_item(item_id)
    if not remove_result.success:
        return remove_result.error

    self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/heal.png"})
    return f"You use the {item_data['name']}. Recovered {heal_amount} energy. {remove_result.message}"
```

---

### Pattern 2: Location Check → Act

Validate the player is in the right place before allowing an action.

```python
def do_room_specific_action(self) -> str:
    room_data = self.state_manager.get_current_room_data()

    if "my_room_type" not in room_data.room_types:
        return "You can't do that here."

    # ... proceed with action
```

---

### Pattern 3: Create and Place Items

```python
def give_reward(self, quantity: int) -> str:
    item_template = {
        "name": "Gold Coin",
        "type": ["currency", "collectible"],
        "descriptions": ["A shiny coin."],
        "static": False,
        "value": 1,
    }

    result = self.state_manager.create_item(
        target_location="inventory",
        target_location_id=None,
        item_creation_data=item_template,
        quantity=quantity,
        fallback_to_room=True,  # Place in room if inventory is full
    )

    if not result.success:
        return f"Could not give reward: {result.error}"

    return result.message  # e.g. "Created 3x Gold Coin in inventory."
```

---

### Pattern 4: Mutate Item State

Modify a field on an existing item. Common for consumables with charges, containers with contents, or items with tracked state.

```python
def mark_item_used(self, item_id: int) -> str:
    result = self.state_manager.set_item_attribute(item_id, "used", True)
    if not result.success:
        return f"Failed to update item: {result.error}"
    return result.message
```

For nested state:
```python
# item_data["dispenser_state"]["charges"] = new_charges
result = self.state_manager.set_item_attribute(
    item_id, "charges", new_charges, path=["dispenser_state"]
)
```

---

### Pattern 5: Building Agent Context

When your tool needs to report the state of the world to the AI agent:

```python
def describe_situation(self) -> str:
    inventory_state = self.state_manager.get_inventory_state()
    stats = self.state_manager.get_stats()
    currency = self.state_manager.get_currency()

    parts = [
        inventory_state.inventory_summary,
        inventory_state.room_summary,
        f"Stats: {stats.stats}",
        f"Currency: {currency.currency}",
    ]
    return "\n".join(parts)
```

---

### Pattern 6: Stat Costs

Actions in this system consume stats. Apply costs after validating success, not before.

```python
ACTION_COSTS = {
    "energy": -1.5,
    "hydration": -1.0,
}

def _apply_costs(self, cost_dict: dict, multiplier: float = 1.0) -> str:
    parts = []
    for stat, amount in cost_dict.items():
        total = amount * multiplier
        self.state_manager.adjust_stat(stat, total)
        parts.append(f"{total:+.2f} {stat}")
    return ", ".join(parts)

def do_tiring_action(self) -> str:
    # ... do the action first ...

    cost_summary = self._apply_costs(ACTION_COSTS)
    return f"Action completed. Costs: {cost_summary}."
```

---

### Pattern 7: Read Item Data Without Modifying It

`find_item` returns a reference into state via `item_data`. If you need to read a field, you can do so directly. If you need to derive a modified copy without writing it back, work on a copy:

```python
import copy

result = self.state_manager.find_item(item_id)
if not result.success:
    return result.error

item_copy = copy.deepcopy(result.item_data)  # Safe copy — won't affect state
# ... use item_copy for local logic only
```

Only write back using `set_item_attribute`. Do not modify `result.item_data` in-place with the intention of persisting it — the state store manages persistence; you must go through the API.

---

## 8. Signals

The `signal_callback` is a callable passed to your tool at construction. It sends messages to the game's UI layer — icon popups, sound triggers, and other non-state side effects.

Always wrap signal calls:

```python
def _send_signal(self, signal_data: dict) -> None:
    if self._signal_callback:
        try:
            self._signal_callback(signal_data)
        except Exception as e:
            print(f"Signal error in {self.__class__.__name__}: {e}")
```

### Common Signal Formats

```python
# Show an icon popup (default style)
self._send_signal({
    "type": "show_icon_popup",
    "icon_path": "style/images/action_icons/some_icon.png",
})

# Show an icon popup with alternate style
self._send_signal({
    "type": "show_icon_popup",
    "icon_path": "style/images/action_icons/some_icon.png",
    "popup_type": 2,
})
```

Signals are fire-and-forget. Your tool logic should not depend on them succeeding. They are cosmetic enhancements only.

---

## 9. Full Example Tool

A complete tool that lets the agent craft items by consuming ingredients.

```python
"""
crafting_tool.py

Allows the AI agent to combine inventory items into a crafted product.
Demonstrates: location checks, multi-item lookup, item removal, item creation,
stat costs, and signals.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager


CRAFT_COSTS = {
    "energy": -3.0,
    "hydration": -1.5,
}


class CraftingTool:
    """
    Provides item crafting functionality to the AI agent.
    Ingredients must all be in the player's inventory.
    The crafted item is placed in the inventory (with room fallback).
    """

    def __init__(self, state_manager, signal_callback=None):
        self.state_manager: InventoryHouseManager = state_manager
        self._signal_callback = signal_callback

    # ------------------------------------------------------------------ #
    # Private Helpers                                                      #
    # ------------------------------------------------------------------ #

    def _send_signal(self, signal_data: dict) -> None:
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"CraftingTool signal error: {e}")

    def _apply_stat_costs(self, cost_dict: dict) -> str:
        parts = []
        for stat, amount in cost_dict.items():
            self.state_manager.adjust_stat(stat, amount)
            parts.append(f"{amount:+.2f} {stat}")
        return ", ".join(parts)

    # ------------------------------------------------------------------ #
    # Public API (Agent-facing)                                            #
    # ------------------------------------------------------------------ #

    def craft_item(
        self,
        ingredient_ids: list[int],
        result_item_template: dict,
        result_quantity: int = 1,
    ) -> str:
        """
        Attempt to craft an item by consuming a list of ingredient items.

        All ingredients must be in the player's inventory. On success, each
        ingredient is removed and the result item is created.

        Args:
            ingredient_ids:      List of item IDs to consume.
            result_item_template: Item dict for the crafted result.
            result_quantity:     How many of the result to produce.

        Returns:
            A string describing the outcome. Always safe to return to the agent.
        """
        if not ingredient_ids:
            return "No ingredients specified. Nothing to craft."

        # --- 1. Validate all ingredients exist in inventory ---
        validated_ingredients = []
        for item_id in ingredient_ids:
            lookup = self.state_manager.find_item(
                item_id,
                required_location="inventory",
            )
            if not lookup.success:
                return f"Missing ingredient: {lookup.error}"
            validated_ingredients.append((item_id, lookup.item_data))

        # --- 2. Remove all ingredients ---
        removal_messages = []
        for item_id, item_data in validated_ingredients:
            removal = self.state_manager.remove_item(item_id)
            if not removal.success:
                # Partial failure: some ingredients may already be removed.
                # Return error — the caller (agent) should handle recovery narrative.
                return f"Crafting interrupted: could not remove {item_data.get('name', item_id)}. {removal.error}"
            removal_messages.append(item_data.get("name", str(item_id)))

        # --- 3. Create the crafted item ---
        creation = self.state_manager.create_item(
            target_location="inventory",
            target_location_id=None,
            item_creation_data=result_item_template,
            quantity=result_quantity,
            fallback_to_room=True,
        )

        if not creation.success:
            return f"Ingredients consumed but crafting failed: {creation.error}"

        # --- 4. Apply stat costs ---
        cost_summary = self._apply_stat_costs(CRAFT_COSTS)

        # --- 5. Signal the UI ---
        self._send_signal({
            "type": "show_icon_popup",
            "icon_path": "style/images/action_icons/craft.png",
            "popup_type": 2,
        })

        # --- 6. Build agent response ---
        consumed = ", ".join(removal_messages)
        result_name = result_item_template.get("name", "item")
        return (
            f"Crafted {result_quantity}x {result_name} successfully. "
            f"Consumed: {consumed}. "
            f"Placed in: {creation.location}. "
            f"Stat costs: {cost_summary}."
        )
```

---

## 10. What Not to Do

### ❌ Bypass the facade

```python
# Wrong — reaches into internal service directly
self.state_manager.inventory_service.drop_item(item_id, 1)
self.state_manager.pet_state_manager.set_current_emote("happy")
```

```python
# Correct — use the public facade
# (If a method you need doesn't exist on the facade, request it be added)
```

---

### ❌ Ignore result.success

```python
# Wrong — will crash or silently use None if lookup failed
result = self.state_manager.find_item(item_id)
name = result.item_data["name"]  # item_data is None on failure!
```

```python
# Correct
result = self.state_manager.find_item(item_id)
if not result.success:
    return result.error
name = result.item_data["name"]
```

---

### ❌ Mutate item_data without writing back

```python
# Wrong — modifies the in-memory dict directly but does not persist the change
result = self.state_manager.find_item(item_id)
result.item_data["charged"] = False  # This does NOT save to state
```

```python
# Correct — write back through the API
self.state_manager.set_item_attribute(item_id, "charged", False)
```

---

### ❌ Apply stat costs before confirming success

```python
# Wrong — costs the player even if the action fails
self.state_manager.adjust_stat("energy", -5)
result = self.state_manager.do_something()
if not result.success:
    return result.error  # Player already paid the cost for nothing
```

```python
# Correct — deduct costs only after confirming success
result = self.state_manager.do_something()
if not result.success:
    return result.error
self.state_manager.adjust_stat("energy", -5)
```

---

### ❌ Return non-string values from agent-facing methods

```python
# Wrong — the agent receives this value as tool output; it must be a string
def get_info(self) -> dict:
    return self.state_manager.get_stats().stats
```

```python
# Correct — serialize for the agent
def get_info(self) -> str:
    stats = self.state_manager.get_stats()
    if not stats.success:
        return stats.error
    return f"Current stats: {stats.stats}"
```

---

### ❌ Crash on signal failure

```python
# Wrong — if callback is None or raises, tool breaks
self._signal_callback({"type": "show_icon_popup", ...})
```

```python
# Correct — always guard signal calls
def _send_signal(self, data):
    if self._signal_callback:
        try:
            self._signal_callback(data)
        except Exception as e:
            print(f"Signal failed: {e}")
```