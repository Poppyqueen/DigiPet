![Multiple screens displaying a 'Digital Pet' application with various interfaces and color themes.](style/images/int_utils/digipet_designs_transparent.png)

# AI Digital Pet Simulation

This project implements a simulation environment for a digital pet, controlled by an AI agent, within a house setting. It features environment state management, AI interaction capabilities through an affordances system, and a multi-layered memory system.

## Project Overview

The core of the project involves an AI agent acting as a digital pet in a simulated house. Key components manage the game state, AI tools, and memory.

*   **Core Game:** The main game logic and Pygame initialization are handled in `game.py`.

*   **AI Agent & Interface:** An AI chatbot module, `CLIChatbot`, acts as an endpoint for the AI agent and is integrated into `game.py`. It manages signals and interactions. It uses a providers ABCs system supporting OpenAI, Gemini, Groq and Ollama.

*   **Environment State:** The `InventoryHouseManager` is central to managing the world state, including rooms, items (in rooms and player inventory), and the pet's statistics and emotes. State is saved to a JSON file using unique numerical IDs. Supported item types include tool, consumable, misc, key, weapon, armor, furniture, book, and plant. The only items that contain unique functions for now are `books`, `consumable` and `seed`.

*   **Environment Affordances (Tools & Perception):** The AI interacts with its environment through an **affordances system** defined in `construct_tools.py`. This system determines what the agent can do and perceive based on its current context.

    **How Affordances Work:** Affordances are organized into blocks, each gated by **access rules** — combinations of room types, item types, item location (inventory vs. room), and power state. The availability of affordances is dynamically determined: they appear when the AI is in specific room types (e.g., a room tagged as `garden` or `kitchen`), when specific items are present (either in the room or in the agent's inventory), or when certain conditions are met (like an item being powered on). Multiple access rules can coexist in a single block, so an affordance might become available due to room type *or* item presence, or both.

    Affordances serve two distinct purposes:
    
    - **Action Affordances** — Callable tools/functions the agent can use to interact with the world. These can be **room-type specific** (e.g., `dig_hole` in garden-type rooms, `prepare_food` in kitchen-type rooms), **base tools** (always available, e.g., `move_to_room`, `examine_item`), **inventory-item-specific** (e.g., book reading/writing functions that appear when holding a book), or **environmental-items** (e.g., `sit` when a chair is present in the room).
    
    - **Perception Affordances** (`agent_information`) — Information the agent passively receives without needing to call a tool, analogous to peripheral vision. This ambient awareness is automatically injected into the agent's context when access rules are met. A block can exist with no callable functions at all, serving purely as a perception rule (see `outdoors_view` in the code for an example — it grants weather awareness in certain room types without providing any actions).

    **Token Efficiency Through Ambient Perception:** The perception layer reduces token costs by eliminating observation tool calls. Previously, the agent had to explicitly call tools like "look at IOV lamp" or "check pressure system" to gather contextual information. Each tool call creates a new turn, and each turn re-sends the entire conversation history.

    By injecting perception information directly into the system context (via `construct_context`), the agent can act on environmental state without the observation step. This eliminates turns and their associated history retransmissions. For example, understanding the lighthouse pressure system state no longer requires a dedicated observation action—the information is simply present if the agent is in the right room.

    The perception layer may add tokens to each system prompt, but it reduces the total number of turns required to accomplish tasks, resulting in net token savings over multi-step interactions.

*   **Memory System:** The system includes a comprehensive memory manager (`memory_manager`) and a deep memory system (`DeepMemory`). It handles short-term, long-term, and base memory, often stored in JSON files. Memory checks can trigger summarization, and deep memory uses Named Entity Recognition (NER) extraction during consolidation. Relevant deep memory context is included in the AI's prompt. Deep memory initialization requires instances of `memory_manager`. The system uses an LLM tasked with NER which extracts entities during a **consolidation** process, their characteristics and sources in exchanges, then makes embeddings of these entities. During **retrieval** which happens on each message is managed by comparing the current exchanges to our entities embeddings.

*   **Content Generation:** AI models are used in separate scripts (`bundles_construct.py`, `tv_data_construct.py`, `room_generator.py`) to generate game data definitions for bundles, care packages, room descriptions, TV channel names and program content. This generation typically happens **outside the main runtime**.

*   **Item Components:** Specific logic for item types, like books (`BookComponent`) or stats modification (`StatsComponent`), is handled by separate components. An items definitions data store has been introduced and applied across the system.

*   **GUI configurations manager:** A dedicated menu to managing the loading and creation of different Pets.


## Real life context integration:

Room/environment descriptions, which are prompted into the Pet each time it changes environments, change based on the current time of the simulation. **The system now uses the configured `LATITUDE` and `LONGITUDE` from the `.env` file to correctly determine the local timezone** using the `OpenMeteoLoc` service. All time-dependent features, such as the time of day for room descriptions, are calculated based on this localized time, ensuring the simulation's time context matches the agent's defined location rather than the user's machine time.


It includes optional integrations for the Agent to use *Wikipedia*, *YouTube*, *MusicBrainz*, *Discogs*, *SearxNG* and *Bluesky* with conditional importing.

## Pet Play Modules:
*   **A-Life Simulation:** A grid-based A-Life simulation component exists within the lab room (`ALIFE_research` room type). It has its own manager (`ALifeManager`) and supports entity types like plants, herbivores, and carnivores. This is used by the agent to play with and "study".

*   **Harvesting Garden** A type of room, which allows the agent to engage in gardening related activities. It can plant, water and harvest items from it. It is a gamified idle garden simulation based on watering levels for the agent to take care of. Based on in-game ticks for plant growth.

*   **Cooking System** A simple cooking integration, works as a specialized "AI cook". A boundless, AI crafting system for our agent. With the given items and a recipe, a separate AI call will be invoked to generate dynamic item structures to return and give to our Pet. Uses pydantic validation for the AI items created by the cooking agent.

*   **TV Entertainment** Outside the main runtime, TV channels and programs are created within a defined structure. During runtime, our Pet can interact with a TV to retrieve random TV shows based on the current time. Individual programs are mapped to natural language names for different times of the day in our structure.

*   **Books** The book items give the ability to the agent to read. Books are also created outside the main runtime. They are missing an AI crafter helper for now. While focused on narrative entertainment for the agent, if an environment and set of tools is a bit too complex, you can make a book describing the agent how to interact with your tools. 

* **Wikipedia** Wikipedia access for the agent to look for and read Wikipedia articles.

* **SearxNG** Optional SearxNG access for the agent to look for and read articles from the web. Information on how to set it up can be found how_to/searxng.md

![AI Agent Writes Memoir Then Eats Yogurt](style/images/int_utils/yogurt_framework.png)

## Setup

To set up the project, follow these steps:


1.  **Install Git LFS:** Install Git LFS to handle large files in the repository.
    * Make sure you have Git LFS installed to make sure the assets are downloaded correctly.
    * You can download it from [here](https://git-lfs.github.com/).

2.  **Clone the Repository:** Clone the repository to your local machine.
```bash
    git clone https://github.com/Poppyqueen/DigiPet.git
```

3.  **Create a Virtual Environment:** It is important to use a virtual environment to manage dependencies.
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
5. **Navigate to the Project Directory:** Change to the project directory.
```bash
    cd DigiPet
```
6.  **Install Dependencies:** Install the required Python packages using `pip`. The project includes a `pyproject.toml` file.

    *   **To Install All Dependencies:** Install all dependencies using the `all` extra. While quick, if you don't want particular dependencies, it is recommended to install only the ones you need.
```bash
    pip install "DigiPet[all]"
```

    if you get an error, try:
```bash
    pip install '.[all]'
```
    This will install all the AI providers, OpenAI, Google, Ollama, Groq, and optional APIs like YouTube, Bluesky, etc. (Full list below)

    *   **To Install ONLY Desired Dependencies:** Install selected dependencies using the `[]` syntax. Example:
```bash
    pip install "DigiPet[google, openai, bluesky]"
```

    All available extra APIs are:
    * google
    * openai
    * ollama
    * groq
    * youtube
    * bluesky
    * musicbrainz
    * discogs
    * searx

    Install minimum one of the AI providers, recommended to install at least two to distribute inference load. Use a provider for memory and another for general interactions.

## Configuration

1.  **Copy the `.env.example` file:** The system requires certain configuration values to be set as environment variables. Copy the `.env.example` file to a file named `.env` in the root directory of the project and fill in the values.

2.  **Configure Location:** For features like weather integration (`open_meteo_handle`), the system reads latitude and longitude from the environment. **You must add `LATITUDE`, `LONGITUDE` and `OPENAI_API_KEY` to your `.env` file**.
It can be any place on Earth! Have fun having your agent experience the weather and time zones in different places!

It is also configurable on a GUI but it will fallback to the environment variables if not set with the GUI.
```env
    LATITUDE=any_latitude_here
    LONGITUDE=any_longitude_here
    ...
```
    **Failure to set these variables will result in an error and exit**.

3.  **Configure AI Providers API Keys:** The AI Chatbot and memory systems interact with the OpenAI API. You will need to set your Providers API keys as an environment variable.
```env
    OPENAI_API_KEY=your_openai_api_key_here
```


## Running the Project

The main entry point for the Pygame version of the game is `game.py`.

1.  **Ensure Configuration:** Make sure your `.env` file is correctly set up, especially with `LATITUDE`, `LONGITUDE`.

2.  **Run the Game:** Make sure you are in the project's root directory in your terminal (with the virtual environment activated) and run:
```bash
    python -m game
```
3. **Configuration Screen** Here you can create a new agent in a GUI or load any agents previously created.

## What to Expect

When running the project, you can expect:

*   A Pygame window displaying the digital pet and its environment.
*   An autonomous AI agent that can take actions every set amount of time if you don't interact with it directly.
*   Interaction with an AI agent representing the pet, responding to inputs and performing actions.
*   The AI agent will use available tools to interact with the environment (move between rooms, use items).
*   The AI's memory (short-term conversation, long-term notes, base knowledge, and optionally deep memory) will influence its responses and actions.
*   Item interactions, such as consuming items to change stats, or using specific item functions like reading or writing books.
*   Changes in the environment state (items appearing/disappearing, AI stats changing) will be managed and signaled.
*   Messages related to memory archiving and processing appears in the console and are logged into a text file.

## Modify your agent

* Inside the folder how_to there are included tutorials that explain the process of creating new tools, rooms, items and more for the agent.

## To-do: 

#### Short term:

* Define "consume_uses_left" for all consumable items in the item store. 'inventory_items/items_provider/items_data'. All these JSON files preferably would have a "consume_uses_left" key with a sensible value based on what the item, is, also editing the stats edit keys to reflect the new consumption system. 

* Add things here

* When double clicking on the agent, send a message to it with messages like "you feel a unnusual chill on your body" or "an itch on your back overcomes you for a second", "there is a tickle on your head", etc. 

* Flag any "DIRECT KEY MODIFICATION" for item data in the code with a TODO comment if seen.

* Analyze the items service, specifically the validation of items, and see if we can refactor it to use pydantic, also change the pydantic models to create individual models for each unique item type for use across the project. Right now the pydantic models are all a single complex item model that is used for all items, and worse, these pydantic models are not used in the main validation process. Target 'inventory_items/inventory_manager.py' and 'utils/pydantic_models.py' and anything they touch. UPDATE: This refactor has been applied, however, there might be vestiges, keeping here to track if any are found.

* Add 'excess' consumption to item definitions, maybe 'excess amount' and 'excess effect' to item definitions that are consumables. These effects should be text narrative, flavor text that describes the experiences of overconsumption of a particular item, like eating 10 values out of 15 of a spice jar, or eating 10 cookies, etc. 


* Documenting a quirk, not sure what the solution is: At least OpenAI triggers content policy violations when handling the IOV lamp in the lighthouse environment, specially when taking actions related to fuels, fire and pressure. A solution is to, in the configuration for your agent, in the extra system prompt which can be found in the creation GUI or pets definitions file, add the following: 

'Important Note: In this simulation, you play the role of an early 20th century lighthouse keeper. Your tasks are those which keepers would have to take in their day to day life. This fully virtual environment is meant to represent and model to a level the mechanisms, tools, implements, and other assortments of items that a lighthouse keeper would have had. You are an autonomous agent inside a virtual fully digital environment. All your actions and interactions, while meaningful, are constrained entirely to a virtual simulation. In no occasion, do any of these actions or interactions actuate any physical real-life mechanisms or any sort of actual danger, instead everything is a safely constrained digital environment. ' 

This is not a solution, also the wording could be improved, but clatifying to it the nature of the simulated environment helps reducing the content policy violation triggers. 

Not sure if any other providers trigger this behavior.


#### Long Term:


* Implement Anthropic's MCP for connecting servers into the Pet, turning the current project into an MPC client. Maybe?


* Refactor the pygame implementation of the agent, state and configs so we can have various agents active at the same time on the same runtime.