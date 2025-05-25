# Adding New Tools to the Digital Pet System

Adding new tools to the digital pet system involves defining the tool's interface in a structured format and implementing the actual logic, with a core component dynamically linking the two. The system utilizes a modular tool system where the AI agent can perform actions controllable by virtual environment location and player inventory. These actions are abstracted as "tools" or "function-callable actions."

---

## Core Components of a Tool

There are two main parts to a tool:

### 1. Tool Definitions

These are formal specifications of the tools, outlining their name, what they do, and what parameters they require.

*   **Location:** `tools/tools_builder/my_tools.py`
*   **Content:** `tools/tools_builder/my_tools.py` contains JSON-structured tool descriptions organized by virtual locations or contexts like "lab room," "kitchen," "garden," and more.
*   **Structure:** Each tool entry includes:
    *   `name`: The tool's identifier.
    *   `description`: A textual explanation of its purpose.
    *   `schema`: A detailed schema defining the expected parameters with types, descriptions, and required fields.
*   **Purpose:** This file does not implement any logic itself but serves as a formal interface specification that defines the actions the AI agent can perform.

### 2. Tool Implementations

This is the actual Python code that executes the logic when a tool is invoked.

*   **Location:** Reside in various modules, often within the `tools/tools_folder/` directory.
*   **Examples:** Modules for AI-assisted crafting (`crafting_table.py`), Bluesky social media posting (`bluesky_handle.py`), and various room-specific actions (`rooms_tools.py`), It is not necesary for room specific tools you create to be inside this `rooms_tools.py` but it works as examples.
*   **Functionality:** The `rooms_tools.py` module, for instance, contains classes for different rooms, with methods implementing actions relevant to that room (e.g., preparing food in the kitchen, digging in the garden).

---

## Connecting Definitions and Implementations: The FunctionBuilder

The system connects these definitions and implementations through a component called the `FunctionBuilder`.

*   **Location:** `tools/tools_builder/construct_tools.py`
*   **Role:** This class is a centralized system for managing and constructing "tools." It dynamically assembles mappings from the function names (defined in `tools/tools_builder/my_tools.py`) to the callable Python objects that implement the logic, based on the AI agent's current environment and inventory context.
*   **Execution:** When the AI agent requests a function call (based on its output, processed by `ai_managers/ai_handle.py`), the `FunctionBuilder` dispatches the call dynamically via its `call_function` method.

---

## Workflow for Adding a New Tool

To add a new tool to this system, a developer would generally follow these steps:

1.  **Implement the Tool's Logic:**
    *   Write the Python code for the function or class method that will perform the desired action. This code contains the core functionality of the new tool.
    *   **Interactions:** This implementation might interact with the game state manager (`InventoryHouseManager` in `inventory_manager.py`) to modify player stats, inventory, or the environment. It would likely also use the `_send_signal` callback to trigger UI updates or notifications.

2.  **Define the Tool's Interface in `tools/tools_builder/my_tools.py`:**
    *   Add a new entry to the relevant section in `tools/tools_builder/my_tools.py`.
    *   This entry will be a dictionary (or JSON object) specifying:
        *   The tool's `name`.
        *   A clear `description` of what it does (crucial for the AI to understand when to use the tool).
        *   A `schema` defining the parameters the AI needs to provide when calling this tool.

3.  **Integrate the Implementation with the `FunctionBuilder`:**
    *   Modify the `FunctionBuilder` class in `tools/tools_builder/construct_tools.py` to map the tool name defined in `my_tools.py` to the newly implemented function or method.
    *   This involves updating the internal dictionaries or logic within `FunctionBuilder` that it uses to assemble its runtime map of available tools based on context (e.g., adding the new function to a dictionary mapping a specific room type to its callable functions).

By following these steps, the new tool's definition is available for the AI to understand, its implementation is present in the codebase, and the `FunctionBuilder` knows how to call the implementation when the AI requests the tool by its defined name, taking the specified parameters.