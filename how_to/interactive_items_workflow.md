# Workflow: Creating Interactive Items and Tools

This guide details the process for adding new interactive items (like furniture or appliances) and their associated tools to the DigiPet codebase. It follows the patterns established by the "Candy Dispenser" implementation.

## 1. Define the Items
Create JSON blueprints for your items in `inventory_items/items_provider/items_data/`.

*   **Location**: Choose an appropriate subdirectory (e.g., `furniture/`, `food_n_drinks/`).
*   **Structure**:
    ```json
    {
        "name": "My Interactive Item",
        "descriptions": [
            "A description of the item.",
            "Status: Initial state"
        ],
        "static": true,
        "type": ["furniture", "my_new_type"],
        "custom_state_key": 0  // Add custom keys for state tracking
    }
    ```
*   **Note**: If you need a new item type (e.g., `my_new_type`), add it to the `item_types` list in `utils/pydantic_models.py`.

## 2. Implement the Logic (Tool Class)
Create a new Python file in `tools/tools_folder/` (e.g., `my_item_tools.py`).

### Class Structure
Your class should accept the `state_manager` (which is the `InventoryHouseManager` facade) and a `signal_callback`.

```python
from inventory_items.items_provider.item_store import ItemStore

class MyItemTools:
    def __init__(self, state_manager, signal=None):
        self.state = state_manager  # InventoryHouseManager instance
        self.item_store = ItemStore("inventory_items/items_provider/items_data")
        self._signal_callback = signal
```

### Best Practices
*   **State Access**: Use `self.state.inventory_service` to find and validate items.
    ```python
    item_info = self.state.inventory_service._find_item_info_by_id(item_id)
    item_data = item_info["item_data"]
    ```
*   **Item Creation**: Use `self.state.create_item()` to add new items to the world. Fetch blueprints using `self.item_store.get_item("Item Name")`.
*   **State Persistence**: Modify the `item_data` dictionary directly (e.g., `item_data["custom_state_key"] = new_value`), then explicitly persist the changes to the `StateStore`.
    ```python
    # Helper to persist changes
    state_store = self.state._state_store
    if location == "inventory":
        state_store.update_state_section("inventory", state_store.get_state_section("inventory"))
    elif location == "room":
        state_store.update_state_section("rooms", state_store.get_state_section("rooms"))
    ```
*   **UI Feedback**: Use `self._send_signal()` to show popups or messages.
    ```python
    self._send_signal({"type": "show_message", "message": "Action complete!"})
    ```

## 3. Register the Tools
You need to register your new tools in two places.

### A. `tools/tools_builder/construct_tools.py`
1.  **Import**: Import your class.
2.  **Initialize**: Instantiate it in `__init__` (e.g., `self.my_tools = MyItemTools(...)`).
3.  **Define**: Add an entry to `self.tool_definitions` in `_init_unified_tool_definitions`.
    ```python
    "my_new_type": {
        "functions": {
            "my_action": self.my_tools.my_action
        },
        "definitions": my_item_tools_json, # Defined in step 3B
        "item_types": ["my_new_type"],
        "use_level": "dual_use" # or "room_type", "inventory_only"
    }
    ```

### B. `tools/tools_builder/my_tools.py`
Add the JSON schema definition for your tool functions. This tells the AI how to call them.
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

## 4. Enable Purchase (Optional)
If the item should be buyable, add its file path to `price_ranges` in `tools/tools_folder/auction_house.py`.

```python
"furniture/my_new_items.json": { "minimum": 100, "maximum": 200, "available_for_purchase": True }
```

## 5. Verification
Create a test script in `tests/` to mock the `InventoryHouseManager` and `StateStore` to verify your logic in isolation before running the full game.
