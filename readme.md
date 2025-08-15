![Multiple screens displaying a 'Digital Pet' application with various interfaces and color themes.](style/images/int_utils/digipet_designs_transparent.png)

# AI Digital Pet Simulation

This project implements a simulation environment for a digital pet, controlled by an AI agent, within a house setting. It features environment state management, AI interaction capabilities through tooling system, and a multi-layered memory system.

## Project Overview

The core of the project involves an AI agent acting as a digital pet in a simulated house. Key components manage the game state, AI tools, and memory.

*   **Core Game:** The main game logic and Pygame initialization are handled in `game.py`.

*   **AI Agent & Interface:** An AI chatbot module, `CLIChatbot`, acts as an endpoint for the AI agent and is integrated into `game.py`. It manages signals and interactions. It uses a providers ABCs system supporting OpenAI, Gemini, Groq and Ollama.

*   **Environment State:** The `InventoryHouseManager` is central to managing the world state, including rooms, items (in rooms and player inventory), and the pet's statistics and emotes. State is saved to a JSON file using unique numerical IDs. Supported item types include tool, consumable, misc, key, weapon, armor, furniture, book, and plant. The only items that contain unique functions for now are `books`, `consumable` and `seed`.

*   **AI Interaction (Tools):** The AI interacts by calling predefined "tools" or "functions". These tools are defined in JSON structures and linked to Python functions. Tools can be **room-type specific** (e.g., `dig_hole` in the garden type, `prepare_food` in the kitchen type), **base tools** (always available, e.g., `move_to_room`, `examine_item`), **inventory-item-specific** (e.g., book functions), or **environmental-items** (e.g sitting) The availability of tools is dynamically determined based on the AI's current room and inventory. Room types are determined as a list of types for each room/environment.

*   **Memory System:** The system includes a comprehensive memory manager (`memory_manager`) and a deep memory system (`DeepMemory`). It handles short-term, long-term, and base memory, often stored in JSON files. Memory checks can trigger summarization, and deep memory uses Named Entity Recognition (NER) extraction during consolidation. Relevant deep memory context is included in the AI's prompt. Deep memory initialization requires instances of `memory_manager`. The system uses an LLM tasked with NER which extracts entities during a **consolidation** process, their characteristics and sources in exchanges, then makes embeddings of these entities. During **retrieval** which happens on each message is managed by comparing the current exchanges to our entities embeddings.

*   **Content Generation:** AI models are used in separate scripts (`bundles_construct.py`, `tv_data_construct.py`, `room_generator.py`) to generate game data definitions for bundles, care packages, room descriptions, TV channel names and program content. This generation typically happens **outside the main runtime**.

*   **Item Components:** Specific logic for item types, like books (`BookComponent`) or stats modification (`StatsComponent`), is handled by separate components. An items definitions data store has been introduced and applied across the system.

*   **GUI configurations manager:** A dedicated menu to managing the loading and creation of different Pets.

## Real life context integration:

Room/environment descriptions, which are prompted into the Pet each time it changes environments change based on the current time from the user's PC using datetime, the system also uses OpenMeteo to retrieve weather data from given coordinates set up inside the .env file. This weather data is currently used as context information for the agent if in the garden room, or tied to specific functions (look out the window is a function that retrieves the weather for the agent). The weather also affects the gardening system, which applies water levels to the plots based on real life rain information every 30 minutes.

While the coordinates are configurable right now, the time is not. There are a few areas that would have to change for us to be able to set the time based on the configured coordinates instead of the direct machine current time. 

It includes optional integrations for the Agent to use *YouTube*, *MusicBrainz*, *Discogs* and *Bluesky* with conditional importing.

## Pet Play Modules:
*   **A-Life Simulation:** A grid-based A-Life simulation component exists within the lab room (`ALIFE_research` room type). It has its own manager (`ALifeManager`) and supports entity types like plants, herbivores, and carnivores. This is used by the agent to play with and "study".

*   **Harvesting Garden** A type of room, which allows the agent to engage in gardening related activities. It can plant, water and harvest items from it. It is a gamified idle garden simulation based on watering levels for the agent to take care of. Based on in-game ticks for plant growth.

*   **Cooking System** A simple cooking integration, works as a specialized "AI cook". A boundless, AI crafting system for our agent. With the given items and a recipe, a separate AI call will be invoked to generate dynamic item structures to return and give to our Pet. Uses pydantic validation for the AI items created by the cooking agent.

*   **TV Entertainment** Outside the main runtime, TV channels and programs are created within a defined structure. During runtime, our Pet can interact with a TV to retrieve random TV shows based on the current time. Individual programs are mapped to natural language names for different times of the day in our structure.

*   **Books** The book items give the ability to the agent to read. Books are also created outside the main runtime. They are missing an AI crafter helper for now. While focused on narrative entertainment for the agent, if an environment and set of tools is a bit too complex, you can make a book describing the agent how to interact with your tools. 

* **Wikipedia** Wikipedia access for the agent to look for and read Wikipedia articles.

## Setup

To set up the project, you will typically follow these steps:

1.  **Clone the Repository:** Obtain the project files. (This step is not explicitly described in the sources but is a standard prerequisite).

   
2.  **Create a Virtual Environment:** It is highly recommended to use a virtual environment to manage dependencies.
    ```bash
    python -m venv .venv
    ```
3.  **Activate the Virtual Environment:**
    *   On Windows:
        ```bash
        .venv\Scripts\activate
        ```
    *   On macOS and Linux:
        ```bash
        source .venv/bin/activate
        ```

4.  **Install Dependencies:** Install the required Python packages using `pip`. The project includes a `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Create a `.env` file:** The system requires certain configuration values to be set as environment variables. Create a file named `.env` in the root directory of the project. An .env.example file is included for ease of configuration

2.  **Configure Location:** For features like weather integration (`open_meteo_handle`), the system reads latitude and longitude from the environment. **You must add `LATITUDE`, `LONGITUDE` and `OPENAI_API_KEY` to your `.env` file**.
    ```env
    LATITUDE=your_latitude_here
    LONGITUDE=your_longitude_here
    OPENAI_API_KEY=your_openai_key
    ```
    **Failure to set these variables will result in an error and exit**.

3.  **Configure AI Providers API Keys:** The AI Chatbot and memory systems interact with the OpenAI API. You will need to set your Providers API keys as an environment variable.
    ```env
    OPENAI_API_KEY=your_openai_api_key_here
    ```

4.  **Deep Memory Flag:** Note that the `deep_memory` flag in the `CLIChatbot` initialization is urged to be set to `False` currently due to token usage concerns. It is set to `False` in the example initialization. Needs redesign.

## Running the Project

The main entry point for the Pygame version of the game is `game.py`. The `CLIChatbot` also appears to have a command-line interface mode.

1.  **Ensure Configuration:** Make sure your `.env` file is correctly set up, especially with `LATITUDE`, `LONGITUDE`.

3.  **Run the Game:** Navigate to the project's root directory in your terminal (with the virtual environment activated) and run:
    ```
    python game.py
    ```
4. **Configuration Screen** Here you can create a new agent in a GUI or load any agents previously created.

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

* Inside the folder how_to there are two newly included tutorials that explain the process of adding new tools and rooms for the agent during the first initialization. 

## To-do: 

#### Short term:
* Implementing different providers for TTS, local and cloud that work across different OSes.
* Add more things to this list

#### Long Term:
* Implement Anthropic's MCP for connecting servers into the Pet, turning the current project into an MPC client.
* Refactor the pygame implementation of the agent, state and configs so we can have various agents active at the same time on the same runtime.
* Re-do the "deep memory" system from 0 with better techniques.