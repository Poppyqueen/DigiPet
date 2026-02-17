# Tool Construction System: How to Build and Manage AI Agent Affordances

## What is the Tool Construction System?

The Tool Construction System (now more accurately called the **Affordance Construction System**) is the central hub that dynamically builds and manages all available functions, tools, and perception for the AI agent based on the current context. It consists of the `FunctionBuilder` class in `construct_tools.py`, which intelligently determines what the agent can do and what it passively perceives based on:

- **Current room types** - Different room types provide different capabilities and awareness
- **Environmental items** - Items present in the current room that can be interacted with or observed
- **Inventory items** - Items the agent is carrying that unlock specific functions or awareness
- **Base functions** - Always-available core functions
- **Optional integrations** - External services that can be enabled/disabled via configuration

The system dynamically constructs both function mappings (what the agent can actually do), tool definitions (what the LLM knows about available functions), and perception context (what the agent passively knows about its environment) every time they're needed, ensuring the agent only has access to contextually relevant affordances.

## How does the system work?

### Core Architecture - The Unified Affordance Definition Map

The `FunctionBuilder` class uses a single, unified data structure, **`self.tool_definitions`** (to be renamed in the future), to manage all affordances and their availability logic. Each entry in this map defines an *Affordance Block* and its conditions for use.

| Key Structure | Description |
| :--- | :--- |
| `tool_definitions` | The singular dictionary containing all Affordance Blocks. |
| **`"functions"`** | *Optional Dictionary*. Maps function names to actual Python method references (action affordances). Can be omitted for perception-only blocks. |
| **`"definitions"`** | A list of JSON-like tool definitions (for the LLM). |
| **`"use_level"`** | The key that defines item-based availability: `"always_available"`, `"inventory_only"`, `"room_only"`, `"dual_use"`. Determines where items must be located to enable the affordance. Note: `"room_type"` is no longer a valid use_level value. |
| **`"room_types"`** | *Optional List*. A list of room type strings. If present, the affordance is available when the agent is in a room with any of these types. This works **additively** (OR logic) with `item_types`. |
| **`"item_types"`** | *Optional List*. A list of item type strings that enable the affordance. Where these items must be located is determined by `use_level`: `"inventory_only"` (agent's inventory), `"room_only"` (current room), or `"dual_use"` (either location). |
| **`"display_information"`** | *Optional Function*. A method reference that provides string-based state information for the GUI (observer perspective). |
| **`"agent_information"`** | *Optional Function*. A method reference that provides string-based perception information injected into the agent's context automatically (agent perspective). |

### Understanding Affordance Availability Logic

**Affordances become available through OR logic combining room types and item types:**

An affordance block is available if **ANY** of these conditions are met:

1. **`use_level: "always_available"`** — Always available regardless of context
2. **`room_types` match** — The current room has any of the specified types (if `room_types` is present)
3. **`item_types` match** — An item with a matching type exists in the appropriate location (determined by `use_level`)

**Important:** The `room_types` key works independently of `use_level`. If you specify `room_types`, the affordance will be available in those room types regardless of what `use_level` you set (except `always_available`, which makes everything else irrelevant).

**Examples of combined availability:**
```python
# Available in garden rooms OR when holding a shovel
{
    "room_types": ["garden"],
    "item_types": ["shovel"],
    "use_level": "inventory_only"  # Only affects where the shovel must be
}

# Available in lighthouse rooms OR when a lens apparatus is in the room
{
    "room_types": ["fresnel_lens_interior"],
    "item_types": ["fresnel_lens_apparatus"],
    "use_level": "room_only"  # Only affects where the apparatus must be
}
```

**The `use_level` flag only controls item location requirements:**

- `"inventory_only"` — Items must be in the agent's inventory
- `"room_only"` — Items must be present in the current room
- `"dual_use"` — Items can be in either location
- `"always_available"` — Special case, ignores all other conditions

### Understanding `display_information` vs `agent_information`

This is a critical architectural distinction:

- **`display_information`**: Returns data for the GUI/human observer. This can include omniscient information, full article text, detailed maps, or "secret" data the agent shouldn't know. It prioritizes completeness over token efficiency.

- **`agent_information`**: Returns data that represents what the agent **passively perceives** by being in a context, analogous to peripheral vision. This is automatically injected into `construct_context()` on every turn. It must be:
  - Token-efficient (concise, relevant)
  - From the agent's embodied perspective (no omniscient knowledge)
  - Appropriate for the agent to know without taking an action

Many simple affordance blocks can share the same function for both (e.g., `get_lamp_status`), but complex systems (A-Life simulation, maze, Wikipedia) need separate implementations because the observer needs more/different information than the agent should passively perceive.

### Dynamic Affordance Construction Process
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

# 5. Get agent perception context (automatically called in construct_context)
perception_info = function_builder.get_current_tools_info(flag="agent")
```

## How to add a New Affordance Block (Room, Item, or Base)?

The process for adding any new affordance set (whether room-based, item-based, or dual-use) is unified:

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
    
    def get_seat_info(self):
        """Perception info about nearby seats (agent perspective)."""
        # ... implementation ...
        return "You notice a comfortable-looking chair nearby."
```

### Step 2: Create tool definitions

Create the JSON-like tool definitions list in a dedicated file (e.g., `tools/my_tools.py`) and import it into `construct_tools.py`. These match the OpenAI tool schema.
```python
# In tools/my_tools.py
seat_tools = [
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

#### Example 1: Room-Type Specific Affordance Block

Affordances only available when the agent is in a room with a specific type. Note that `use_level` can be set to any value except `always_available` — it's the presence of `room_types` that determines room-based availability.
```python
self.tool_definitions["my_special_room"] = {
    "functions": {
        "special_room_action": self.my_new_tools.special_room_action
    },
    "definitions": special_room_tools,
    "room_types": ["my_special_room"],  # Available in rooms with this type
    "display_information": self.my_new_tools.get_room_info,  # For GUI
    "agent_information": self.my_new_tools.get_room_perception,  # For agent context
    # "use_level": "dual_use"  # Use level is not needed when no item_types is specified
}
```

#### Example 2: Inventory-Only Item Affordance Block

Affordances only available if an item of a specific type is in the agent's inventory.
```python
self.tool_definitions["my_inventory_item"] = {
    "functions": {
        "use_special_item": self.state_manager.use_special_item
    },
    "definitions": my_item_tools,
    "item_types": ["special_key"],
    "use_level": "inventory_only"  # Item must be in inventory
}
```

#### Example 3: Dual-Use Item Affordance Block

Affordances available if an item of a specific type is in the inventory *or* present in the current room.
```python
self.tool_definitions["interactive_furniture"] = {
    "functions": {
        "interact_with_furniture": self.room_tools.interact_with_furniture
    },
    "definitions": furniture_interaction_tools,
    "item_types": ["interactive_furniture"],
    "use_level": "dual_use"  # Item can be in inventory OR room
}
```

#### Example 4: Always Available Base Affordance Block

The core affordance set, available regardless of location or inventory. This block only requires the `functions`, `definitions`, and `use_level` keys.
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

#### Example 5: Room-Only Item Affordance Block

Affordances only available if an item of a specific type is present in the current room.
```python
self.tool_definitions["my_room_item"] = {
    "functions": {
        "use_special_item": self.state_manager.use_special_item
    },
    "definitions": my_item_tools,
    "item_types": ["special_key"],
    "use_level": "room_only"  # Item must be in the room
}
```

#### Example 6: Combined Room and Item Affordance Block

Affordances available in specific room types **OR** when specific items are present. This demonstrates the additive (OR) logic.
```python
self.tool_definitions["fresnel_lens_interior"] = {
    "functions": {
        "fresnel_rotation_state": self.lighthouse.get_fresnel_rotation
    },
    "definitions": fresnel_lens_tools,
    "room_types": ["fresnel_lens_interior"],  # Available in these rooms
    "item_types": ["fresnel_lens_apparatus", "fresnel_lens"],  # OR when these items are in room
    "use_level": "room_only",  # Only affects item location requirement
    "agent_information": self.lighthouse.get_fresnel_rotation
}
```

In this example, the affordance is available if:
- The agent is in a room of type `"fresnel_lens_interior"`, OR
- An item of type `"fresnel_lens_apparatus"` or `"fresnel_lens"` is present in the current room

#### Example 7: Perception-Only Affordance Block (no functions)

An affordance block that provides only ambient awareness, with no callable actions. This is useful for granting the agent passive knowledge about adjacent or related spaces.
```python
self.tool_definitions["outdoors_view"] = {
    # Note: No "functions" key — this is perception only
    "definitions": garden_room_tools,  # Still needed for structural consistency
    "room_types": ["outdoors_view"],  # Available in these room types
    "use_level": "dual_use",  # Arbitrary when no item_types specified
    "agent_information": self.room_tools.garden.display_information  # Weather info
}
```

In this example, when the agent is in a room with type `"outdoors_view"`, it automatically receives weather information in its context without needing to call any function.

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

Add the Affordance Block to the unified map only if the handler was successfully initialized.
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
            # Affordances can be available via room type or a portable item
            "room_types": ["my_service_room_type"],
            "item_types": ["my_service_item_type"], 
            "use_level": "dual_use"
        }
        print("My service tools added to unified definitions.")
```

## Context and Information System

The system provides contextual information in two distinct ways:

### For the Agent (LLM Context)
```python
# Get current context for the LLM (includes perception automatically)
context = function_builder.construct_context()
```

The `construct_context()` method automatically calls `get_current_tools_info(flag="agent")` internally, which:
- Checks all currently available Affordance Blocks for an `agent_information` function
- Executes each found function and collects the results
- Injects this perception data into the agent's system context on every turn

This ensures the AI agent always has passive awareness of its current situation without needing to take observation actions.

**Agent context includes:**
- Current time and location
- Agent's emotional state and available emotes
- Inventory and room contents (minimal details)
- Current stats (hunger, energy, etc.)
- Weather information (for outdoor-aware rooms via `agent_information`)
- Contextual perception (from all available affordance blocks' `agent_information` functions)

### For the GUI (Display Information)
```python
# Get room-specific information for GUI display
room_info = function_builder.get_current_tools_info(flag="display")  # default
```

With `flag="display"` (the default), `get_current_tools_info()` instead checks for `display_information` functions, which can provide more verbose, omniscient, or detailed data appropriate for human observers but not the agent.

## Token Efficiency Through Perception

By injecting perception information directly into the system context rather than requiring tool calls, the system reduces token costs:

**Old System:**
- Agent calls `look_at_lamp` (turn 1, sends full history)
- Agent calls `check_pressure` (turn 2, sends full history + turn 1)
- Agent acts on information (turn 3, sends full history + turns 1-2)

**New System:**
- Lamp and pressure state already in context (no turn cost)
- Agent acts immediately (turn 1, sends full history)

The perception layer adds tokens to each system prompt, but eliminates observation turns, resulting in net savings over multi-step interactions.