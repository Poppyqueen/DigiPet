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

Your class should accept the `state_manager` (the `InventoryHouseManager` facade) and a `signal_callback`.

```python
from inventory_items.items_provider.item_store import ItemStore

class MyItemTools:
    def __init__(self, state_manager, signal=None):
        self.state = state_manager  # InventoryHouseManager instance
        self.item_store = ItemStore("inventory_items/items_provider/items_data")
        self._signal_callback = signal
```

### Accessing Item Data

Use `get_validated_item_data()` to find and validate items. It returns the live item dict
and an error message — always check the error before proceeding.

```python
item_data, error = self.state.inventory_service.get_validated_item_data(
    item_id, required_type="my_new_type"
)
if error:
    return error
```

### Modifying Item State — the only correct pattern

**Never modify `item_data` keys directly.** The item dict returned by `get_validated_item_data`
is a live reference into the state store. Writing to it directly (`item_data["key"] = value`)
bypasses the stacking system and will cause silent bugs on stackable items — the change
will not trigger a stack split, and multiple items in a stack will incorrectly share state.

Always use `set_item_attribute` instead:

```python
# CORRECT
self.state.inventory_service.set_item_attribute(item_id, "custom_state_key", new_value)

# CORRECT — nested write (e.g. into dispenser_state)
self.state.inventory_service.set_item_attribute(
    item_id, "contents", new_dict, path=["dispenser_state"]
)

# WRONG — direct key modification, do not use
item_data["custom_state_key"] = new_value
self.state.inventory_service.persist_item_changes(item_id)
```

`set_item_attribute` handles stacking fingerprint comparison, stack splitting when needed,
state persistence, and UI signals automatically. `persist_item_changes` is no longer the
right tool for modifying item state — it exists only as an internal persistence helper.

If you see `item_data["key"] = value` followed by `persist_item_changes` anywhere in the
codebase, mark it with `# TODO: DIRECT ITEM KEY MOD` so it can be updated.

### Working with list fields (chapters, descriptions, effects)

When the attribute you're updating is a list (e.g. adding a chapter to a book, appending
a description), always work on a `deepcopy` of the current value — never mutate the list
in place before passing it to `set_item_attribute`. Mutating the live list first poisons
the before-fingerprint and prevents stack splits from triggering correctly.

```python
import copy

# CORRECT
current = copy.deepcopy(item_data.get("chapters", []))
current.append({"title": chapter_title, "content": content})
self.state.inventory_service.set_item_attribute(item_id, "chapters", current)

# WRONG — appending to the live reference before calling set_item_attribute
item_data["chapters"].append({"title": chapter_title, "content": content})
self.state.inventory_service.set_item_attribute(item_id, "chapters", item_data["chapters"])
```

### Creating Items

Use `create_item()` to add new items to the world. Fetch blueprints using `ItemStore`:

```python
blueprint = self.item_store.get_item("My Interactive Item")
self.state.create_item("room", room_id, blueprint)
```

### UI Feedback

Use signals for short popups or transient messages:

```python
self._send_signal({"type": "show_message_popup", "message": "Action complete!"})
self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/my_icon.png"})
```

---

## 3. Register the Tools

### A. `tools/tools_builder/construct_tools.py`

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

Add the JSON schema definition for your tool functions. This tells the AI how to call them:

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

Create a test script in `tests/` that mocks `InventoryHouseManager` and `StateStore`
to verify your logic in isolation before running the full game.