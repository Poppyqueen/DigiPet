
# AI Agent Tool Framework: Creating New Tools

This document explains the basic structure for adding new tools to the AI agent framework using the provided `construct_tools.py` and `my_tools.py` files.

## Framework Overview

This framework uses a `FunctionBuilder` class to manage which tools are available to the AI agent based on its current state (like the room it's in or items it possesses). Tool definitions are stored in `my_tools.py` as structured data, and the actual tool logic resides in separate Python files (e.g., within a `tools_folder`).

The core idea is:

1.  **Define** the tool's structure (name, description, parameters) in `my_tools.py`.
2.  **Implement** the tool's functionality as a Python function or class method.
3.  **Integrate** the definition and implementation in `construct_tools.py` so the `FunctionBuilder` knows about it and can make it available to the AI agent under the correct conditions.

A key requirement is that **any tool meant for the AI agent to call must return a string describing the result of the action in natural language.** This string is what the AI agent receives as the output of the tool call.

## Creating a Simple New Tool

Let's walk through creating a simple tool. We'll create a tool called `greet_world` that simply returns a greeting message. This tool will be available in the `base_tools`, meaning it's always available.

**Step 1: Write the Python Function**

First, write the Python code for your tool. It should be a function that accepts arguments (if any) and returns a string explaining its result. You'll likely place this in a file within your `tools_folder` directory, perhaps alongside other utility functions.

Let's add it to a file like `tools_folder/my_simple_tools.py`:

```python
# tools_folder/my_simple_tools.py

def greet_world(name: str):
    """
    Greets a person by name.

    Args:
        name: The name of the person to greet.

    Returns:
        A string greeting the person.
    """
    if not name:
        return "Hello, world!"
    return f"Hello, {name}!"

# You could add other simple, general-purpose tools here
# def say_goodbye(name: str):
#    if not name:
#        return "Goodbye, world!"
#    return f"Goodbye, {name}!"
```

**Step 2: Define the Tool in `my_tools.py`**

Now, define the tool's structure in `my_tools.py`. We'll add it to the `base_tools` list since it's always available.

Open `my_tools.py` and add the following dictionary to the `base_tools` list:

```python
# my_tools.py

# Here are our JSON structures for defining the tools...

base_tools = [
    # ... existing base tool definitions ...
    { # Add this new dictionary to the base_tools list
        "type": "function",
        "name": "greet_world", # MUST match the Python function name exactly
        "description": "Greets a person by name. Useful for saying hello.", # Clear description for the AI
        "parameters": {
            "type": "object",
            "properties": {
                "name": { # MUST match the Python function argument name exactly
                    "type": "string",
                    "description": "The name of the person to greet. Use 'world' if no specific name is mentioned."
                }
            },
            "required": [ # List any required arguments
                "name"
            ],
            "additionalProperties": False
        }
    },
    # ... rest of the existing base tool definitions ...
]

# ... rest of my_tools.py (other lists like library_tools, mirror_tools, etc.) ...
```

**Crucial Points:**

* The `"name"` in the definition (`"greet_world"`) **must** exactly match the Python function name (`def greet_world(...)`).
* The keys under `"properties"` (`"name"`) **must** exactly match the Python function's argument names (`name` in `def greet_world(name)`).
* The `"type"` in the definition (`"string"`) should match the expected Python type.
* The `"description"` is vital for the AI to understand how and when to use the tool.

**Step 3: Integrate the Tool in `construct_tools.py`**

Finally, integrate your new function and its definition into the `FunctionBuilder` so it can be used.

Open `construct_tools.py`:

1.  **Import the Python function:** Add an import statement for your new function.

    ```python
    # construct_tools.py

    # Import necessary components...
    # ... existing imports ...

    # Import your simple tools functions
    from tools_folder.my_simple_tools import greet_world
    # If you added other functions to my_simple_tools.py, import them too
    # from tools_folder.my_simple_tools import say_goodbye

    # Import tools and their definitions from the tools folder
    # ... existing imports from .my_tools ...
    ```

2.  **Add the function mapping:** Since `greet_world` is a base tool, add it to the `self.base_function_map` in the `__init__` method. Map the tool name string (`"greet_world"`) to the actual Python function object (`greet_world`).

    ```python
    # construct_tools.py (__init__ method)

    class FunctionBuilder:
        def __init__(self, library_path="working_directory", room_handler=None, inventory_handler=None, crafter=None, emote_folder=None):
            # ... existing initializations ...

            # Create the mapping dictionary for base functions
            self.base_function_map = {
                #"get_weather": get_weather, # Example of imported function
                # ... existing base function mappings ...
                "greet_world": greet_world, # Add your new function mapping here
                # "say_goodbye": say_goodbye, # Example of another mapping
            }

            # Store the imported tool definitions
            # ... existing storage of definitions ...
            # No need to add a new list storage if it's in base_tools

            # ... rest of __init__ ...
    ```

3.  **Ensure definition is included:** Since we added the definition to `base_tools` in `my_tools.py`, and `construct_tools.py` already extends `all_potential_definitions` with `self._base_tools_definitions` and then filters based on `self.function_map`, the `greet_world` definition will automatically be included when `construct_tools` is called. No changes are needed in `construct_tools` or `construct_map` for a simple base tool.

**For Conditional Tools (More Advanced):**

If your tool should only be available in a specific room (like `library_tools`) or with a specific item (like `mirror_tools`), you would:

* Create a new list or add to an existing conditional list in `my_tools.py` (Step 2).
* Import this new list in `construct_tools.py` and store it (Step 3a, 3b).
* In `construct_map`, add an `if current_room == "your_room":` or `if self.inventory_handler.verify_item_in_inventory("your_item"):` block. Inside this block, add your tool's mapping to `self.function_map.update(...)` (similar to how `library_functions` or `item_functions` are added).
* In `construct_tools`, add a matching `if` block to `all_potential_definitions.extend(...)` to include the tool definition list when the condition is met.

## Key Takeaways for Creating Tools

* **`my_tools.py`:** Defines *what* the tool looks like to the AI (name, description, parameters).
* **Tool Implementation (e.g., `tools_folder/*.py`):** Implements *how* the tool works in Python. **Must return a string result.**
* **`construct_tools.py`:** Links the definition to the implementation and controls *when* the tool is available via `construct_map` and `construct_tools`.
* **Matching Names:** Function/method names and argument names must match *exactly* between `my_tools.py` and the Python code.
* **Return String:** Your tool's Python function/method **must** return a natural language string describing the outcome for the AI.
* **Dependency Injection:** If your tool needs access to other parts of the system (inventory, room state, etc.), implement it as a method in a class and pass an instance of that class to the `FunctionBuilder` during initialization, then call the method via that instance.
