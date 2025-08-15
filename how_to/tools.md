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

### Core Architecture

The `FunctionBuilder` class uses several key data structures:

1. **`_room_type_data`** - Maps room types to their available functions and definitions
2. **`_environmental_item_functions`** - Functions available when specific item types are present in the room
3. **`_item_specific_functions`** - Functions available when specific item types are in the agent's inventory
4. **`base_function_map`** - Always-available core functions

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

## How to add new room types and their tools?

### Step 1: Create your tool functions

First, create your tool functions in the appropriate module within `tools/tools_folder/`:

```python
# In tools/tools_folder/my_new_room_tools.py
class MyNewRoomTools:
    def __init__(self, state_manager, signal_callback):
        self.state_manager = state_manager
        self.signal_callback = signal_callback
    
    def take_a_seat(self, item_id):
        """A function for you to sit on any seat, chair or valid item you see around."""
        return f"Sat on: {item_id}"
```

### Step 2: Create tool definitions

Create the JSON-like tool definitions in `tools/my_tools.py`:

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
    ...
]
```

### Step 3: Import and register in construct_tools.py

Add your imports at the top:

```python
# Import your tool definitions
from .my_tools import seat_tools

# Import your tool handler
from tools.tools_folder.my_new_room_tools import MyNewRoomTools
```

Initialize your tool handler in `__init__`:

```python
def __init__(self, state_manager=None, signal=None, subdirectory=None, memory_manager=None, config_manager=None):
    # ... existing initialization ...
    
    # Initialize your room tools
    self.my_new_room = MyNewRoomTools(self.state_manager, self._signal_callback)
```

Add to `_room_type_data`:

```python
self._room_type_data = {
    # ... existing room types ...
    "my_special_room": {
        "functions": {
            "special_room_action": self.my_new_room.special_room_action
        },
        "definitions": my_new_room_tools,
        "current_info": self.my_new_room.get_room_info  # Optional info function * 
    }
}
```
* current_info is an optional function for those tools tied to a room, it should return a string that gives information for display in the GUI about the state of this tool. i.e our gardening room informs about the state of the plots. 

## How to add optional external integrations?

### Step 1: Add configuration option

In your configuration system, add an enable flag:

```python
# In your config file
[Tools]
enable_my_service = true
```

### Step 2: Conditional import and initialization

Add conditional logic in `FunctionBuilder.__init__`:

```python
def __init__(self, ...):
    # Get configuration
    my_service_enabled = config_manager.get_config('Tools', "enable_my_service")
    
    # Conditional import
    if my_service_enabled:
        try:
            from utils import my_service_handler
        except ImportError as e:
            print(f"Warning: Could not import my_service_handler, disabling. Error: {e}")
            my_service_enabled = False
    
    # Initialize to None first
    self.my_service = None
    
    # Conditional initialization
    if my_service_enabled:
        try:
            self.my_service = my_service_handler.MyServiceTools()
            print("MyServiceTools instance created.")
        except Exception as e:
            print(f"Error instantiating MyServiceTools: {e}")
            self.my_service = None
```

### Step 3: Dynamic registration

Add to the dynamic section of `_room_type_data`:

```python
def __init__(self, ...):
    # ... after base _room_type_data initialization ...
    
    # Dynamically add optional integrations
    if self.my_service:
        self._room_type_data["my_service_type"] = {
            "functions": {
                "my_service_function": self.my_service.some_function
            },
            "definitions": my_service_tools
        }
        print("My service tools added to room type data.")
```

## How to add item-specific functions?

### For inventory items (items the agent carries):

```python
# Add to _item_specific_functions
self._item_specific_functions = {
    "my_item_type": {
        "use_special_item": self.state_manager.use_special_item,
        "examine_closely": self.state_manager.examine_item_closely
    }
}

# Add corresponding definitions
self._item_specific_definitions = {
    "my_item_type": my_item_tools
}
```

### For environmental items (items present in room):

```python
# Add to _environmental_item_functions
self._environmental_item_functions = {
    "interactive_furniture": {
        "interact_with_furniture": self.room_tools.interact_with_furniture
    }
}

# Add corresponding definitions
self._environmental_item_definitions = {
    "interactive_furniture": furniture_interaction_tools
}
```

## How to add always-available base functions?

Add to the `base_function_map` in `__init__`:

```python
self.base_function_map = {
    # ... existing base functions ...
    "my_global_function": self.my_global_handler.global_function,
    "another_base_function": self.state_manager.another_function
}
```

Don't forget to add the corresponding definitions to `base_tools` in `tools/my_tools.py`.

## Important implementation notes

**Tool Definition Requirements:**
- Tool definition `name` must exactly match the function name in the mapping
- Parameter names and types in definitions must match the actual function signatures
- The `required` array should list all non-optional parameters

**Dynamic Construction:**
- `construct_map()` is called automatically before each function call
- The system checks room types, environmental items, and inventory every time
- Functions are only available when their contextual requirements are met

**Error Handling:**
- Failed imports disable entire optional integrations gracefully
- Missing functions return helpful error messages to the agent
- The system continues working even if individual components fail

**Performance Considerations:**
- Tool construction happens dynamically but caching could be added
- Large numbers of conditional imports may slow initialization
- Consider lazy loading for heavy external services

**Configuration Dependencies:**
- Optional integrations require proper configuration management
- Failed services should disable cleanly without breaking the system
- Always provide fallback behavior when external services are unavailable

## Context and Information System

The system also provides contextual information to the AI agent:

```python
# Get current context for the LLM
context = function_builder.construct_context()

# Get room-specific information for GUI
room_info = function_builder.get_current_room_info()
```

**Context includes:**
- Current time and location
- Agent's emotional state and available emotes
- Inventory and room contents
- Current stats (hunger, energy, etc.)
- Weather information (for outdoor rooms)
- Room-type-specific details

This ensures the AI agent always has complete awareness of its current situation and capabilities.