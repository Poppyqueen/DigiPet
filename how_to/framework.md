# How Components Relate in the AI Agent's Interactive World

The AI agent's interactive world is built upon three deeply interconnected core systems: Items, Environments (Rooms/Houses), and Tools. These systems work in concert to define the agent's capabilities and interactions.

## 1. Items

Items are the fundamental objects within the project. Their characteristics and type are crucial as they dictate their potential uses and how they interact with the other systems.

*   **Placement:** Items can be placed within an environment (room).
*   **Inventory:** Items can be carried in an agent's inventory.
*   **Agent Interaction:** Items can directly affect an agent's stats (e.g., consuming food).
*   **Crucial Information:** An item's **`type`** is the primary trigger field. It is used by the Tool Construction System to determine if item-specific actions should be enabled.

## 2. Environments (Houses/Rooms)

Environments, such as houses or individual rooms, define the spaces an AI agent inhabits. They are characterized by their structure, appearance, and, most importantly, their contents.

*   **Definition:** Environments are defined by their structure, appearance, and contents.
*   **Initial State:** An environment's initial state is populated with items.
*   **Room Types:** **`room_types`** are key identifiers that serve as direct triggers for room-specific tools (e.g., a room with the type `planting_garden` enables gardening tools).
*   **Environmental Items:** Items present in the room also contribute context. Tools configured with a **`dual_use`** level can be enabled by the presence of a matching item's `type` in the room, even if the agent is not holding it (e.g., a `seat` item in the room enables the `take_a_seat` tool).

## 3. Tools

Tools represent the actions that the AI agent can perform. Unlike static abilities, the availability of tools is dynamically constructed based on the agent's current context. This is the point where all three systems converge.

*   **Dynamic Availability:** Tools are not static; their availability is dynamically constructed via the `FunctionBuilder` every time they are needed.
*   **Unified Tool Definition:** The `FunctionBuilder` uses a single, unified map of "Tool Blocks." Each Tool Block is explicitly configured with a `use_level` and a list of required `room_types` or `item_types`.
*   **Enabling Tools via `use_level`:** The system determines tool availability by checking the following contextual rules:
    *   **`always_available`:** The tool is always present (e.g., `move_to_room`).
    *   **`room_type`:** The tool is available only if the current room's `room_types` list contains a required type (e.g., `planting_garden`).
    *   **`inventory_only`:** The tool is available only if the agent's inventory contains an item with a required `type` (e.g., a `book` item enables `read_chapter`).
    *   **`room_only`:** The tool is available only if the current room contains an item with a required `type` (e.g., a `dispenser` item enables `refill_dispenser`).
    *   **`dual_use`:** The tool is available if a required `item_type` is found either in the agent's inventory *or* as an environmental item in the current room (e.g., a `laptop` enables `browse_auction_house` whether carried or placed on a desk).

**In essence, the `type` fields of Items and the `room_types` of Environments act as explicit, structured affordances that the Tool Construction System uses to decide which actions the agent can perform based on its `use_level` criteria.**

## Simple Representation of the Relationship (Updated)

The relationship between these components can be visualized as a cyclical dependency where context continuously drives capability.

1.  **Environment Definition:** An Environment (a room) is initially defined with specific **`Room Types`** and an initial set of **`Items`** (environmental items).
2.  **Agent Inventory:** An agent may possess additional **`Items`** in its inventory.
3.  **Context Analysis:** The **`Tool Construction System (FunctionBuilder)`** continuously analyzes the `current Environment`'s **`Room Types`** and the **`type`** of all **`Items`** (both environmental and in inventory).
4.  **Tool Enabling:** Based on the analysis matching the configured **`use_level`** of each Tool Block, the system dynamically enables a specific set of **`Tools`** for the AI agent to use.
5.  **Action and Context Change:** The AI agent performs an action using an enabled `Tool`. This action can potentially alter its `environment` or `inventory`, thereby changing the context and, as a result, enabling a new set of `Tools`.