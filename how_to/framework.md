# How Components Relate in the AI Agent's Interactive World

The AI agent's interactive world is built upon three deeply interconnected core systems: Items, Environments (Rooms/Houses), and Affordances (Tools & Perception). These systems work in concert to define the agent's capabilities and awareness.

## 1. Items

Items are the fundamental objects within the project. Their characteristics and type are crucial as they dictate their potential uses and how they interact with the other systems.

*   **Placement:** Items can be placed within an environment (room).
*   **Inventory:** Items can be carried in an agent's inventory.
*   **Agent Interaction:** Items can directly affect an agent's stats (e.g., consuming food).
*   **Crucial Information:** An item's **`type`** is the primary trigger field. It is used by the Affordance Construction System to determine if item-specific actions or perceptions should be enabled.

## 2. Environments (Houses/Rooms)

Environments, such as houses or individual rooms, define the spaces an AI agent inhabits. They are characterized by their structure, appearance, and, most importantly, their contents.

*   **Definition:** Environments are defined by their structure, appearance, and contents.
*   **Initial State:** An environment's initial state is populated with items.
*   **Room Types:** **`room_types`** are key identifiers that serve as direct triggers for room-specific affordances (e.g., a room with the type `planting_garden` enables gardening tools and garden-related awareness).
*   **Environmental Items:** Items present in the room also contribute context. Affordances configured with a **`dual_use`** level can be enabled by the presence of a matching item's `type` in the room, even if the agent is not holding it (e.g., a `seat` item in the room enables the `take_a_seat` tool).

## 3. Affordances (Tools & Perception)

Affordances represent both the actions that the AI agent can perform and the information it passively perceives. Unlike static abilities, the availability of affordances is dynamically constructed based on the agent's current context. This is the point where all three systems converge.

*   **Dynamic Availability:** Affordances are not static; their availability is dynamically constructed via the `FunctionBuilder` every time they are needed.
*   **Unified Affordance Definition:** The `FunctionBuilder` uses a single, unified map of "Affordance Blocks." Each Affordance Block is explicitly configured with a `use_level` and a list of required `room_types` or `item_types`.
*   **Two Types of Affordances:**
    *   **Action Affordances (`functions`):** Callable tools the agent can use to interact with the world (e.g., `dig_hole`, `prepare_food`, `read_chapter`).
    *   **Perception Affordances (`agent_information`):** Information the agent passively receives without needing to call a tool, analogous to peripheral vision. This ambient awareness is automatically injected into the agent's context. A block can exist with no callable functions at all, serving purely as a perception rule (e.g., `outdoors_view` grants weather awareness in certain room types).

*   **Affordances block logic:** The system determines affordance availability by checking the following contextual rules:
    
    | Key | Description |
    | :--- | :--- |
    | **`"use_level"`** | Item-based availability: `"always_available"`, `"inventory_only"`, `"room_only"`, `"dual_use"`. Controls where items must be located. |
    | **`"room_types"`** | *Optional list*. Active when current room has any of these types. Works additively (OR logic) with `item_types`. If room types exists, use level is not required. (Maybe change that?)|
    | **`"item_types"`** | *Optional list*. Item types that enable the affordance. Location requirement set by `use_level`. |

**In essence, the `type` fields of Items and the `room_types` of Environments act as explicit, structured affordances that the Affordance Construction System uses to decide which actions the agent can perform and what information the agent passively perceives based on its `use_level` criteria.**

## Simple Representation of the Relationship (Updated)

The relationship between these components can be visualized as a cyclical dependency where context continuously drives capability and awareness.

1.  **Environment Definition:** An Environment (a room) is initially defined with specific **`Room Types`** and an initial set of **`Items`** (environmental items).
2.  **Agent Inventory:** An agent may possess additional **`Items`** in its inventory.
3.  **Context Analysis:** The **`Affordance Construction System (FunctionBuilder)`** continuously analyzes the `current Environment`'s **`Room Types`** and the **`type`** of all **`Items`** (both environmental and in inventory).
4.  **Affordance Enabling:** Based on the analysis matching the configured **`use_level`** of each Affordance Block, the system dynamically enables a specific set of **`Action Tools`** and **`Perception Information`** for the AI agent.
5.  **Action and Context Change:** The AI agent performs an action using an enabled `Tool`, or reasons about its environment using passively-received `Perception Information`. Actions can potentially alter its `environment` or `inventory`, thereby changing the context and, as a result, enabling a new set of `Affordances`.

## Token Efficiency Note

The perception layer provides a token efficiency benefit: by injecting contextual awareness directly into the system prompt (via `construct_context`), the agent can reason about environmental state without needing to call observation tools first. This eliminates extra turns and their associated conversation history retransmissions, resulting in net token savings over multi-step interactions despite the added context in each prompt.