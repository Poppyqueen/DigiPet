# DigiPet TODO Checklist

This document tracks all `TODO:` comments found in the DigiPet codebase.

## AI Managers & Agents
- [ ] **chatbot_api.py:94** - Allow up to n consecutive AI calls (including function calls and final response)
- [ ] **chatbot_api.py:113** - Move TTS client loading into the Main AI Loader
- [ ] **ai_handle.py:43** - Document the `mem_structure` parameter (it does not equal the `StructuredMemory` object)
- [ ] **user_interface_api.py:5** - Re-evaluate if this concept should be integrated into the final product
- [ ] **user_interface_api.py:11** - Refactor to use the `ai_handle` that `chatbot_api` uses
- [ ] **command_translator.py:13** - Refactor to use the `ai_handle` that `chatbot_api` uses
- [ ] **groq_client.py:87** - Remove the silly `time.sleep(60)` way to stay under TPM free tier limit

## Tools & Builders
- [ ] **construct_tools.py:6** - Refactor to separate into different files (services initialization vs Affordance blocks)
- [ ] **construct_tools.py:159** - Check why tool definitions ignoring 'room_type'
- [ ] **construct_tools.py:480** - Create `agent_information` for `ALIFE_research`
- [ ] **construct_tools.py:528** - Create `agent_information` for `maze`
- [ ] **construct_tools.py:734** - Add `agent_information` for `wikipedia` if determined necessary
- [ ] **construct_tools.py:750** - Think if we want an `agent_information` key for `youtube`
- [ ] **construct_tools.py:801** - Think if we want an `agent_information` key for `bluesky`
- [ ] **construct_tools.py:815** - Think if we want an `agent_information` key for `searxng`
- [ ] **lighthouse_controller.py:8** - Add popup signals to all methods
- [ ] **lighthouse_controller.py:9** - Add keys more in depth for items like the oiler, kerosene containers, hand_fire_source, etc.
- [ ] **lighthouse_controller.py:109, 130, 237, 294, 309, 330, 346, 384, 398, 420** - Add signals for icon popups
- [ ] **lighthouse_controller.py:437** - Change name and descriptive texts for `accessible_room_light_check`, register along with other rooms
- [ ] **images_lab.py:10** - Make `TOTAL_IMAGES_LIMIT` configurable
- [ ] **garden_tools.py:933** - Implement water source item with water level for `water_plot`
- [ ] **ai_cook.py:1** - Refactor to use new pydantic models
- [ ] **ai_cook.py:87** - Investigate why AI response sometimes hangs (OpenAI as cook)

## Inventory & Models
- [ ] **book_service.py:164** - Fix direct modification of state in `book_data["chapters"]`
- [ ] **item_pydantic_models.py:6** - Register lighthouse items that require mixins
- [ ] **item_pydantic_models.py:45** - Check if any item types need particular key mixins definitions
- [ ] **pydantic_models.py:8** - Move memory structures to memory manager at some point

## Data Constructors
- [ ] **base_state_construct.py:17** - Move `UNIQUE_TYPES` to the pydantic models file
- [ ] **room_generator.py:18** - Decide what to do with `room_types` import
- [ ] **room_generator.py:324** - Move hardcoded image directories to a single place
- [ ] **bundles_construct.py:61** - Update prompt to be more concise and clear

## TTS Providers
- [ ] **base_tts_provider.py:4** - Implement a new method for each TTS provider to get available voices
- [ ] **piper_provider.py:19** - Figure out how to change `use_cuda` on the fly (preferably without torch)

## Game Logic
- [ ] **game.py:380, 416, 1432** - Abstract the ticks so they can be used for other things
- [ ] **game.py:396** - Move `lighthouse_tick` call, preferably after abstraction of the tick function

## Helpers & Documentation
- [ ] **fresnel_lens.py:63** - Remove rotation speed management (managed by clockwork timed mechanism instead)
- [ ] **fresnel_lens.py:256** - Use time provider to make a map instead of `day` flag
- [ ] **interactive_items_workflow.md:99** - Update code marked with `# TODO: DIRECT ITEM KEY MOD`
