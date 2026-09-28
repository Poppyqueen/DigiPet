I call this project 'Digipet', it could have a more appropiate name. 
It started with an attempt to make a virtual house for an agent to be in, which now should allow to create a variety of environments, not only a house now. 

I've been working on this for a while and it is a bit of a mess. A loved mess. Hope it's an understandable mess.

The agent features a chatbox, however, it runs on an autonomous loop, initiating actions if left idle for long enough (5 minutes default).

It can 'inhabit' its environment, through basic interactions and custom items affordances. Environments consist of interconnected rooms, or areas it can traverse by giving commands. 

Tool calling is gated behind an 'affordances' system, which broadcasts context and tool definitions to the agent only during the right context. I.E., TV tools are only percieved by the agent if the current room contains a TV item. This I think is a neat natural design that sidesteps the issue of bloating the agent with unrelated tools or context. 

It features a simple memory system, a rolling window that gets summarized into different "buckets" of memory types, which all end up into a general main memory string. It's workable. It also features a 'deep memory' system, which is experimental, expensive and inefficient. 

One can create new code, build and register new items with novel interactions, items are endpoints for the tool calling agent. 

There is also an environmental aspect based on location. You can configure a set of coordinates, global or per agent, and the engine will pull diverse forms of data relevant to that area, 'tools/tools_folder/outdoors_perception.py' and 'tools/tools_folder/tools_helpers/outdoors_helpers'. It features for now, weather, marine, ornithology, astronomical data. All of these use different tools to create a representation of real world data based on the coordinates. (astro gives the agent a sky to observe, 24 hours pattern featuring solar, lunar and stars observation, ornithology gives access to Xeno-Canto, to pull relevant birds to the location and time. All of these are translated into natural language or text for the agent to have in its context.)

It features a gardening idle minigame for the agent, some other interactive features are also available for it. 
The current engine features a few custom environments already built. The most unique of these is the lighthouse, which contains a simulation of an early 20th century, late victorian set of interactive elemets for the agent to roleplay and engage with the maintanance of a lighthouse. 

Some systems are extensible, you can design new plants for the gardening system, or create new stations for the transmittion items (tvs, radio, intercom). 

There is an AI powered crafting system used sporadically across the codebase. During runtime, a separate AI with structured outputs is used to craft items on the fly, the cooking system is the main example of this, the agent passes a set of validated items into the crafter AI, and using out pydantic models, the crafter AI returns the result of the preparation of the agent. 

The backend for the agent simulation is controlled under a facade pattern. All existing tools use a controller facade to interact and alter the game state, which manages inventory, stacking, and the logic of game state.

The game features a cold store of items, which are registered into the store, and the engine can grab and pull from. 

It features a UI interface, using pygame, with a main menu screen to manage existing agents and create new agents. The new agent creation UI takes configuration settings for the AI provider, model, style configurations and crucially, environment selection. The engine reads the selected environment from the options, clones the environment definition into an agent directory and from there on it works and manages the state over the agent's unique state.

Items are defined in pydantic, this does validation during initialization and for the AI crafter, it also doubles as documentation for existing item types. The item store is a directory of json items that follow these pydantic definitions. 

Main readme in how_to/readme.md
detailed technical docs, how_to/main

There is an incomplete, unregistered environment, lunar environment that needs work. 
A fishing mechanic was planned. 
A lot of details need attention.




Guided Tour:
pygame_int contains the pygame interface logic
pygame_runtime contains the pygame engine

ai_managers holds all AI related operations, an agent, a simple provider, tokenizers, etc.

inventory_items holds game logic, state managers, item types definitions, etc. The most important thing here to accostume to is inventory_items/inventory_manager.py, which is a facade for the game state manager. To use when creating new interactions and logic. All the tools the agent uses that require world manipulation use it. 

see inventory_items/items_validation/item_pydantic_models.py for all the existing item types, 

inventory_items/items_validation/room_pydantic_models.py for the room types

tools/ has all the logic to the agent available actions, 
tools/tools_builder holds the engine logic for broadcasting tool definitions to the agent. Does not need any changes for new tools but on the registry, 

tools/tools_builder/tool_registry.py, here you register tools and wire the methods and functions in tools/tools_folder to the agent definitions. This allows for some configurations on the broadcast level of each of these tools.

You can also create 'perception' affordances (tools), which are automatically injected into the AI context when in the correct environment, situation or inventory. Managed alongside tools, configurable as tools.

(also write the LLM tool definitions in an OpenAI function calling pattern here: tools/tools_builder/my_tools.py)


tools/tools_folder contains the bulk of the codebase, a bunch of disparate tools that mask as items or rooms interactions, 

check out tools/tools_folder/base_tools.py for the most basic examples of tools

check tools/tools_folder/dispenser_tools.py, 

tools/tools_folder/cranny_tools.py

and finally 
tools/tools_folder/plants_controller.py

note, these tools, most break down into a facade pattern or 'controller', where the entry point, (cranny_tools.py, dispenser_tools.py, plants_controller.py), delegate deep logic into a helper, for the controller only to manage the state interactions with inventory_manager.py


...

There's a lot of stuff. 

hope you already read this here 

Main readme in readme.md
detailed technical docs, how_to/main

there is still more stuff tho

Claude needs a tokenizer, that required an API key I think. One could make a dummy tokenizer if daring.