![Multiple screens displaying a 'Digital Pet' application with various interfaces and color themes.](style/images/int_utils/digipet_designs_transparent.png)

# AI Digital Pet Simulation

DigiPet is an engine for building virtual environments — rooms and items authored once as reusable building blocks, assembled into **Scenes** — for a tool-calling AI agent to inhabit and act within autonomously.

## Project Overview

A Scene is built from two reusable catalogues — a Room Store and an Item Store — plus a layout manifest describing how a specific set of rooms connects together and what starts in them. Several Scenes ship with the project (a default home, a compact home, a walled garden, and more), and new ones can be authored entirely through JSON — see `how_to/DESIGNING_SCENES.md`. The agent that inhabits a Scene is a digital pet; key components manage its game state, AI tools, and memory.

*   **Core Game:** The main game logic and Pygame initialization are handled in `game.py`.

*   **AI Agent & Interface:** An AI chatbot module, `CLIChatbot`, acts as an endpoint for the AI agent and is integrated into `game.py`. It manages signals and interactions. It uses a providers ABCs system supporting OpenAI, Gemini, Groq and Ollama, OpenRouter and Llama.cpp.

*   **Environment State:** The `InventoryHouseManager` (`inventory_items/inventory_manager.py`) is the central facade managing the world state, including rooms, items (in rooms and player inventory), and the pet's statistics and emotes. State is saved to a JSON file using unique numerical IDs. Supported item types are defined in `inventory_items/items_validation/item_pydantic_models.py`. A variety of items have unique keys and validation provided by the pydantic models. 

*   **Environment Affordances (Tools & Perception):** The AI interacts with its environment through an **affordances system** split across three files:

    - `tool_registry.py` — service initialization and the `tool_definitions` dict
    - `tool_availability.py` — stateless availability logic
    - `construct_tools.py` — runtime dispatch, map construction, and context building

    Affordances are organized into blocks, each gated by access rules — combinations of room types, item types, item location (inventory vs. room), and power state. They serve two purposes:

    - **Action Affordances** — Callable tools the agent can use to interact with the world. Can be room-type specific, always available, inventory-item-specific, or triggered by environmental items.

    - **Perception Affordances** (`agent_information`) — Information the agent passively receives without calling a tool, analogous to peripheral vision. Automatically injected into context when access rules are met. A block can exist with no callable functions at all, serving purely as a perception rule.

    **Token Efficiency Through Ambient Perception:** The perception layer reduces token costs by eliminating observation tool calls. Information like lighthouse pressure state or garden conditions is simply present in context when the agent is in the right room, eliminating dedicated observation turns and their associated history retransmissions.

    See `how_to/TOOL_FRAMEWORK.md` for the full guide on adding new affordances.

*   **Memory System:** The default memory system (`memory_manager`) is a rolling window of summarized memory, kept at short-term, long-term, and base levels stored in JSON files. **Deep Memory** (`DeepMemory`) is an optional, experimental layer on top of this: it uses Named Entity Recognition (NER) extraction during consolidation — a separate LLM call extracts entities, their characteristics, and sources from exchanges, then creates embeddings. During retrieval (on each message), current exchanges are compared against entity embeddings to surface relevant context.

*   **Content Generation:** Content generation is currently a dev/creative-time task, not an in-runtime feature. Item and room definitions are authored via YAML manifests and generated with an LLM through `data_constructors/dev_crafter/batch_process.py`, validated against the same Pydantic contracts used everywhere else — see `manifest_lunar_items.yaml` for an example manifest, and `how_to/DESIGNING_SCENES.md` for the full workflow. An older in-runtime generation path (`bundles_construct.py`, `tv_data_construct.py`, `room_generator.py`) still exists in the codebase but its UI entry point has been removed and it predates the current Pydantic contract system — treat it as legacy, not the supported path.

*   **Item Behaviors:** Item-type-specific behavior (e.g. books) is implemented in tool classes under `tools/tools_folder/` — see `tools/tools_folder/book_tools.py` — which are subordinate to, and act only through, the `InventoryHouseManager` facade. This replaces the older pattern of separate sibling components (`BookComponent`, `StatsComponent`) sitting alongside the state manager; there is now a single state-management facade, and item behavior implementations call into it rather than living next to it. An items definitions data store (`ItemStore`) is used across the system.

*   **GUI Configuration Manager:** A dedicated menu for managing the loading and creation of different Pets.


## Real Life Context Integration

Room and environment descriptions change based on the current time of the simulation. The system uses `LATITUDE` and `LONGITUDE` from the `.env` file to determine local timezone via the `OpenMeteoLoc` service. All time-dependent features are calculated based on this localized time, ensuring the simulation's context matches the agent's defined location rather than the user's machine time.

Optional integrations for the agent include *Wikipedia*, *YouTube*, *MusicBrainz*, *Discogs*, *SearxNG*, and *Bluesky*.

## Pet Play Modules

*   **A-Life Simulation:** A grid-based A-Life simulation for the agent to observe and study, provided through an item of type `ALIFE_interface` rather than a dedicated room type. Supports entity types like plants, herbivores, and carnivores.

*   **Harvesting Garden:** A room type (`open_soil_zone`) enabling gardening activities — planting, watering, and harvesting. A gamified idle garden simulation driven by in-game ticks for plant growth.

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
pip install '.[all]'
```

    *   **Selected dependencies only:**
```bash
pip install ".[google, openai, bluesky]"
```

    Available extras:
    * `google`, `openai`, `ollama`, `groq`, `openrouter` — AI providers (install at least one, recommended two)
    * `youtube`, `bluesky`, `musicbrainz`, `discogs`, `searxng` — optional integrations

## Configuration

1.  **Copy `.env.example` to `.env`** and fill in the values.

2.  **Required variables:**
```env
LATITUDE=any_latitude_here
LONGITUDE=any_longitude_here
```
    Location can be anywhere on Earth. Failure to set these will result in an error on startup.

3.  Location and some settings are also configurable via the GUI, which will take precedence over the `.env` values.

### Important Coordinates Note: While these coordinates are managed by env secrets, the codebase does not take care to hide or remove this data from logs or terminal.

## Running the Project

```bash
python -m game
```


### Running with Llama.cpp (Local)

To use a local model with this framework, you must serve your GGUF file using the `llama-server` binary included with llama.cpp.

**Standard Command:**
llama-server 

**Framework Configuration:**
Ensure your `LlamaCppProv` is pointing to the correct address. By default, it looks for:
http://localhost:8080/v1

in:
    ai_managers/agents/agent_clients/llama_cpp_client.py

    ai_managers/simple_ai/providers/llama_cpp_provider.py


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

> **XenoCanto Note - Output and recordings licensing.** The XenoCanto implementation features a setting to toggle Non Derivatives and Non Commercial recordings. Both toggled to filter them out as default. 
>
> Change this in: utils/xeno_canto_api.py


## Modifying Your Agent

The `how_to/` folder contains guides for creating new tools, rooms, items, and more. Start with `how_to/DESIGNING_SCENES.md` for building worlds (rooms, items, layouts, Scenes) without writing Python, and `how_to/ITEM_SYSTEM_DOCS.md` for the full, auto-generated item-type reference. For adding new agent capabilities in Python, see `how_to/TOOL_FRAMEWORK.md` and `how_to/EXTENDING_BEHAVIORS.md`.

## To-do

#### Short term


* Make sure room music in rooms definitions can be null 

* Define `consume_uses_left` for all consumable items in the item store (`inventory_items/items_provider/items_data`). All JSON files there should have a `consume_uses_left` key with a sensible value, and stats edit keys updated to reflect the new consumption system.

* Refactor data constructors and the environment generation process, use the new pydantic definitions and improve the system in general

* When double-clicking on the agent, send it a message like "you feel an unusual chill on your body" or "an itch on your back overcomes you for a second".

* Add sound settings (backend and GUI) for background music, sound effects, autonomous agent calls, and TTS — with volume and mute controls.

* Wearables for the pet?