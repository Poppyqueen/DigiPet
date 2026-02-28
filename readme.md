![Multiple screens displaying a 'Digital Pet' application with various interfaces and color themes.](style/images/int_utils/digipet_designs_transparent.png)

# AI Digital Pet Simulation

This project implements a simulation environment for a digital pet, controlled by an AI agent, within a house setting. It features environment state management, AI interaction capabilities through an affordances system, and a multi-layered memory system.

## Project Overview

The core of the project involves an AI agent acting as a digital pet in a simulated house. Key components manage the game state, AI tools, and memory.

*   **Core Game:** The main game logic and Pygame initialization are handled in `game.py`.

*   **AI Agent & Interface:** An AI chatbot module, `CLIChatbot`, acts as an endpoint for the AI agent and is integrated into `game.py`. It manages signals and interactions. It uses a providers ABCs system supporting OpenAI, Gemini, Groq and Ollama.

*   **Environment State:** The `InventoryHouseManager` is central to managing the world state, including rooms, items (in rooms and player inventory), and the pet's statistics and emotes. State is saved to a JSON file using unique numerical IDs. Supported item types are defined in `inventory_items/item_pydantic_models.py`. A variety of items have unique keys and validation provided by the pydantic models. 

*   **Environment Affordances (Tools & Perception):** The AI interacts with its environment through an **affordances system** split across three files:

    - `tool_registry.py` — service initialization and the `tool_definitions` dict
    - `tool_availability.py` — stateless availability logic
    - `construct_tools.py` — runtime dispatch, map construction, and context building

    Affordances are organized into blocks, each gated by access rules — combinations of room types, item types, item location (inventory vs. room), and power state. They serve two purposes:

    - **Action Affordances** — Callable tools the agent can use to interact with the world. Can be room-type specific, always available, inventory-item-specific, or triggered by environmental items.

    - **Perception Affordances** (`agent_information`) — Information the agent passively receives without calling a tool, analogous to peripheral vision. Automatically injected into context when access rules are met. A block can exist with no callable functions at all, serving purely as a perception rule.

    **Token Efficiency Through Ambient Perception:** The perception layer reduces token costs by eliminating observation tool calls. Information like lighthouse pressure state or garden conditions is simply present in context when the agent is in the right room, eliminating dedicated observation turns and their associated history retransmissions.

    See `how_to/TOOL_FRAMEWORK.md` for the full guide on adding new affordances.

*   **Memory System:** The system includes a comprehensive memory manager (`memory_manager`) and a deep memory system (`DeepMemory`). It handles short-term, long-term, and base memory stored in JSON files. Deep memory uses Named Entity Recognition (NER) extraction during consolidation — a separate LLM call extracts entities, their characteristics, and sources from exchanges, then creates embeddings. During retrieval (on each message), current exchanges are compared against entity embeddings to surface relevant context.

*   **Content Generation:** AI models are used in separate scripts (`bundles_construct.py`, `tv_data_construct.py`, `room_generator.py`) to generate game data definitions for bundles, care packages, room descriptions, and TV content. This generation happens **outside the main runtime**.

*   **Item Components:** Specific logic for item types, like books (`BookComponent`) or stats modification (`StatsComponent`), is handled by separate components. An items definitions data store is used across the system.

*   **GUI Configuration Manager:** A dedicated menu for managing the loading and creation of different Pets.


## Real Life Context Integration

Room and environment descriptions change based on the current time of the simulation. The system uses `LATITUDE` and `LONGITUDE` from the `.env` file to determine local timezone via the `OpenMeteoLoc` service. All time-dependent features are calculated based on this localized time, ensuring the simulation's context matches the agent's defined location rather than the user's machine time.

Optional integrations for the agent include *Wikipedia*, *YouTube*, *MusicBrainz*, *Discogs*, *SearxNG*, and *Bluesky*.

## Pet Play Modules

*   **A-Life Simulation:** A grid-based A-Life simulation in the lab room (`ALIFE_research` room type). Supports entity types like plants, herbivores, and carnivores for the agent to observe and study.

*   **Harvesting Garden:** A room type enabling gardening activities — planting, watering, and harvesting. A gamified idle garden simulation driven by in-game ticks for plant growth.

*   **Cooking System:** A specialized AI cook integration. A boundless crafting system where a separate AI call generates dynamic item structures from given ingredients and a recipe. Uses Pydantic validation for AI-generated items.

*   **TV Entertainment:** TV channels and programs are created outside the main runtime within a defined structure. During runtime the agent can interact with a TV to retrieve programs based on current time.

*   **Books:** Book items let the agent read. Books are created outside the main runtime. While focused on narrative entertainment, they can also be used to document complex tool environments for the agent.

*   **Wikipedia:** Wikipedia access for the agent to search and read articles.

*   **SearxNG:** Optional SearxNG integration for web search and article retrieval. Setup guide in `how_to/searxng.md`.

![AI Agent Writes Memoir Then Eats Yogurt](style/images/int_utils/yogurt_framework.png)

## Setup

1.  **Install Git LFS:** Install Git LFS to handle large files in the repository.
    * Download from [here](https://git-lfs.github.com/).

2.  **Clone the Repository:**
```bash
git clone https://github.com/Poppyqueen/DigiPet.git
```

3.  **Create a Virtual Environment:**
```bash
python -m venv .venv
```

4.  **Activate the Virtual Environment:**
    *   On Windows:
```bash
.venv\Scripts\activate
```
    *   On macOS and Linux:
```bash
source .venv/bin/activate
```

5. **Navigate to the Project Directory:**
```bash
cd DigiPet
```

6.  **Install Dependencies:**

    *   **All dependencies:**
```bash
pip install "DigiPet[all]"
```
    If you get an error, try:
```bash
pip install '.[all]'
```

    *   **Selected dependencies only:**
```bash
pip install "DigiPet[google, openai, bluesky]"
```

    Available extras:
    * `google`, `openai`, `ollama`, `groq` — AI providers (install at least one, recommended two)
    * `youtube`, `bluesky`, `musicbrainz`, `discogs`, `searx` — optional integrations

## Configuration

1.  **Copy `.env.example` to `.env`** and fill in the values.

2.  **Required variables:**
```env
LATITUDE=any_latitude_here
LONGITUDE=any_longitude_here
OPENAI_API_KEY=your_openai_api_key_here
```
    Location can be anywhere on Earth. Failure to set these will result in an error on startup.

3.  Location and some settings are also configurable via the GUI, which will take precedence over the `.env` values.

## Running the Project

```bash
python -m game
```

The configuration screen will appear first — create a new agent or load a previously created one.

## What to Expect

*   A Pygame window displaying the digital pet and its environment.
*   An autonomous AI agent that acts every set amount of time if you don't interact directly.
*   The agent uses available tools to interact with the environment (move between rooms, use items, manage the lighthouse, tend the garden, etc.).
*   The agent's memory (short-term conversation, long-term notes, base knowledge, deep memory) influences responses and actions.
*   Item interactions: consuming items changes stats; books can be read and written; seeds can be planted.
*   Environment state changes are managed and signaled to the GUI.
*   Console output and a log file capture memory archiving and processing activity.

> **Note — Lighthouse and Content Policy:** At least OpenAI triggers content policy violations when handling the IOV lamp, particularly actions involving fuel, fire, and pressure. Adding the following to your agent's extra system prompt (in the creation GUI or pet definitions file) reduces this:
>
> *"Important Note: In this simulation, you play the role of an early 20th century lighthouse keeper. Your tasks are those which keepers would have to take in their day to day life. This fully virtual environment is meant to represent and model to a level the mechanisms, tools, implements, and other assortments of items that a lighthouse keeper would have had. You are an autonomous agent inside a virtual fully digital environment. All your actions and interactions, while meaningful, are constrained entirely to a virtual simulation. In no occasion, do any of these actions or interactions actuate any physical real-life mechanisms or any sort of actual danger, instead everything is a safely constrained digital environment."*
>
> This is a workaround, not a solution. It is not known whether other providers exhibit the same behavior.

## Modifying Your Agent

The `how_to/` folder contains guides for creating new tools, rooms, items, and more.

## To-do

#### Short term

* IMPORTANT: Update pyproject.toml to include the new OpenRouter dependencies

* Define `consume_uses_left` for all consumable items in the item store (`inventory_items/items_provider/items_data`). All JSON files there should have a `consume_uses_left` key with a sensible value, and stats edit keys updated to reflect the new consumption system.

* Refactor data constructors and the environment generation process, use the new pydantic definitions and improve the system in general

* When double-clicking on the agent, send it a message like "you feel an unusual chill on your body" or "an itch on your back overcomes you for a second".

* Flag any direct key modification of item data in the code with a `TODO: DIRECT KEY MODIFICATION` comment.

* Add `excess` consumption to consumable item definitions — `excess_amount` and `excess_effect` (flavor text describing overconsumption).

* Add sound settings (backend and GUI) for background music, sound effects, autonomous agent calls, and TTS — with volume and mute controls.

* Wearables for the pet?

#### Long term

* Implement Anthropic's MCP for connecting servers, turning the project into an MCP client.

* Refactor the Pygame implementation so multiple agents can be active simultaneously on the same runtime.