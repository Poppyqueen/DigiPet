# Tool Construction System: How to Build and Manage AI Agent Tools

## What is the Tool Construction System?

The Tool Construction System is the central hub that dynamically builds and manages all available functions and tools for the AI agent based on the current context. It consists of the `FunctionBuilder` class in `construct_tools.py`, which intelligently determines what tools are available based on:

- **Current room types** - Different room types provide different capabilities
- **Environmental items** - Items present in the current room that can be interacted with
- **Inventory items** - Items the agent is carrying that unlock specific functions
- **Base functions** - Always-available core functions
- **Optional integrations** - External services that can be enabled/disabled via configuration

The system dynamically constructs both function mappings (what the agent can actually do) and tool definitions (what the LLM knows about available functions) every time they're needed, ensuring the agent only has access to contextually relevant tools.

## How does the system work?

### Core Architecture - The Unified Tool Definition Map

The `FunctionBuilder` class now uses a single, unified data structure, **`self.tool_definitions`**, to manage all tools and their availability logic. Each entry in this map defines a *Tool Block* and its conditions for use via the `use_level` key:

| Key Structure | Description |
| :--- | :--- |
| `tool_definitions` | The singular dictionary containing all Tool Blocks. |
| **`"functions"`** | A dictionary mapping function names to actual Python method references. |
| **`"definitions"`** | A list of JSON-like tool definitions (for the LLM). |
| **`"use_level"`** | The key that defines availability: `"always_available"`, `"room_type"`, `"inventory_only"`, or `"dual_use"`. |
| **`"room_types"`** | *Optional List*. A list of room type strings that enable the tool. |
| **`"item_types"`** | *Optional List*. A list of item type strings (in inventory or environment) that enable the tool. |
| **`"display_information"`** | *Optional Function*. A method reference that provides string-based state information for the GUI. |

### Dynamic Tool Construction Process

```python
# 1. Initialize FunctionBuilder with dependencies
function_builder = FunctionBuilder(
    state_manager=state_manager,
    signal=signal_callback,
    subdirectory=data_directory,
    memory_manager=memory_manager,
    config_manager=config_manager
)

# 2. Construct available functions dynamically
function_builder.construct_map()

# 3. Get tool definitions for LLM
available_tools = function_builder.construct_tools()

# 4. Call functions dynamically
result = await function_builder.call_function("function_name", {"arg1": "value1"})
```

## How to add a New Tool Block (Room, Item, or Base Tools)?

The process for adding any new tool set (whether room-based, item-based, or dual-use) is unified:

### Step 1: Create your tool functions

Create your tool functions in the appropriate module within `tools/tools_folder/` and instantiate the handler class in `FunctionBuilder.__init__`.

```python
# In tools/tools_folder/my_new_tools.py
class MyNewTools:
    def __init__(self, state_manager, signal_callback):
        self.state_manager = state_manager
        self.signal_callback = signal_callback
    
    def take_a_seat(self, item_id: int):
        """A function for you to sit on any seat, chair or valid item you see around."""
        # ... implementation ...
        return f"Sat on: {item_id}"
```

### Step 2: Create tool definitions

Create the JSON-like tool definitions list in a dedicated file (e.g., `tools/my_tools.py`) and import it into `construct_tools.py`.

```python
# In tools/my_tools.py
seat_tools=[
    {
        "type": "function",
        "name": "take_a_seat",
        "description": "A function for you to sit on any seat, chair or valid item you see around.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The item ID you want to take a seat on."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    }
    # ... more tools ...
]
```

### Step 3: Register in `_init_unified_tool_definitions`

Add a new entry to the `self.tool_definitions` map within `FunctionBuilder._init_unified_tool_definitions` (or `_add_conditional_tools` for optional tools), configuring the `use_level` and contextual requirements.

#### Example 1: Room-Type Specific Tool Block (`use_level: "room_type"`)

Tools only available when the agent is in a room with a specific type.

```python
self.tool_definitions["my_special_room"] = {
    "functions": {
        "take_a_seat": self.my_new_tools.take_a_seat
    },
    "definitions": seat_tools,
    "room_types": ["my_special_room"],
    "display_information": self.my_new_tools.get_room_info, # Optional
    "use_level": "room_type"
}
```

#### Example 2: Inventory-Only Item Tool Block (`use_level: "inventory_only"`)

Tools only available if an item of a specific type is in the agent's inventory.

```python
self.tool_definitions["my_inventory_item"] = {
    "functions": {
        "use_special_item": self.state_manager.use_special_item
    },
    "definitions": my_item_tools,
    "item_types": ["special_key"],
    "use_level": "inventory_only"
}
```

#### Example 3: Dual-Use Item Tool Block (`use_level: "dual_use"`)

Tools available if an item of a specific type is in the inventory *or* present in the current room.

```python
self.tool_definitions["interactive_furniture"] = {
    "functions": {
        "interact_with_furniture": self.room_tools.interact_with_furniture
    },
    "definitions": furniture_interaction_tools,
    "item_types": ["interactive_furniture"],
    "use_level": "dual_use"
}
```

#### Example 4: Always Available Base Tool Block (`use_level: "always_available"`)

The core tool set, available regardless of location or inventory. This block only requires the `functions`, `definitions`, and `use_level` keys.

```python
self.tool_definitions["base_functions"] = {
    "functions": {
        "move_to_room": self.state_manager.set_current_room,
        "emit_inner_thought": emit_inner_thought
    },
    "definitions": base_tools,
    "use_level": "always_available"
}
```

## How to add Optional External Integrations?

Optional external services (like YouTube, Bluesky, etc.) are handled by conditional initialization in `__init__` and registration in `_add_conditional_tools`.

### Step 1: Add configuration option

Ensure your configuration system has an enable flag (e.g., `[Tools] enable_my_service = true`).

### Step 2: Conditional initialization in `__init__`

```python
def __init__(self, ...):
    # ... other initialization ...
    
    # Get configuration
    my_service_enabled = config_manager.get_config('Tools', "enable_my_service")
    self.my_service = None
    
    # Conditional import and initialization
    if my_service_enabled:
        try:
            from tools.tools_folder.services import my_service_handler
            self.my_service = my_service_handler.MyServiceTools()
            print("MyServiceTools instance created.")
        except Exception as e:
            print(f"Error with MyService tools: {e}")
            self.my_service = None
            
    # ...
    self._add_conditional_tools()
```

### Step 3: Dynamic registration in `_add_conditional_tools`

Add the Tool Block to the unified map only if the handler was successfully initialized.

```python
def _add_conditional_tools(self):
    """Add optional tools to the unified map if they were successfully initialized."""
    # ... existing conditional tools ...
    
    if self.my_service:
        self.tool_definitions["my_service_tools"] = {
            "functions": {
                "my_service_function": self.my_service.some_function
            },
            "definitions": my_service_tools_definitions,
            # Tools can be available via room type or a portable item
            "room_types": ["my_service_room_type"],
            "item_types": ["my_service_item_type"], 
            "use_level": "dual_use" 
        }
        print("My service tools added to unified definitions.")
```

## Context and Information System (Updated)

The system also provides contextual information to the AI agent and the GUI:

```python
# Get current context for the LLM
context = function_builder.construct_context()

# Get room-specific information for GUI (Updated function name)
room_info = function_builder.get_current_tools_info() 
```

The function **`get_current_tools_info()`** dynamically checks all *available* Tool Blocks for a defined **`"display_information"`** function and executes it, compiling all contextual information into a single, comprehensive string for display in the GUI.

**Context includes:**
- Current time and location
- Agent's emotional state and available emotes
- Inventory and room contents (details kept minimal for LLM)
- Current stats (hunger, energy, etc.)
- Weather information (for outdoor rooms, only if `garden` room type is active)
- Room-type-specific details (collected from available tool's `display_information` functions)

This ensures the AI agent always has complete awareness of its current situation and capabilities.