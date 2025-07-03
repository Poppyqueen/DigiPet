# deep_memory.py

import os

import json
from typing import List, TYPE_CHECKING # Import TYPE_CHECKING
import time
import random

# Import utils
from utils.pydantic_models import look_ner_structure, save_ner_structure # Import from pydantic_models.py

# Use TYPE_CHECKING to allow type hint without circular import at runtime
if TYPE_CHECKING:
    from memory.memory_handle import memory_manager # This import only happens for type checkers

class DeepMemory:
    """
    A class to manage a deep memory system for an LLM agent.
    This module is designed to handle a "deep memory" system for an LLM agent,
    the concept is based on associative memory, where a global memory is used to
    store and retrieve information not readily available in the current context window.
    """
    # Add type hint using string literal or TYPE_CHECKING
    def __init__(self, filepath: str, ai_bot_instance=None, memory_instance: 'memory_manager' = None):
        """
        Initialize the DeepMemory instance.

        Args:
            filepath (str): Path to the JSON file where deep memory data is stored.
            ai_bot_instance: An instance of the AI bot for processing.
            memory_instance ('memory_manager'): An instance of the memory_manager.
        """
        if memory_instance is None:
             # If you absolutely need a default, it makes coupling tighter.
             # Consider requiring it to be passed in.
             # from memory_handle import memory_manager # Avoid this if possible
             # print("Warning: No memory_instance provided to DeepMemory. Functionality may be limited.")
             # self.memory = memory_manager() # Creates a default, potentially unwanted memory manager
             raise ValueError("DeepMemory requires a memory_manager instance.") # Better to enforce
        else:
            self.memory = memory_instance

        self.filepath = filepath
        self._check_and_create_db() # Check/create deep memory file
        self.memory_data = self._load_memory() # Load deep memory data

        # Use provided bot instance or create a new one if needed
        if ai_bot_instance:
            self.bot_instance = ai_bot_instance
        elif self.memory and hasattr(self.memory, 'bot_instance'): # Try to get bot from memory_manager
             self.bot_instance = self.memory.bot_instance
        else:
            raise ValueError("DeepMemory could not obtain an ai_bot instance.")

        if not self.bot_instance:
             raise ValueError("DeepMemory could not obtain an ai_bot instance.")

    def _check_and_create_db(self):
        """
        Internal function to check if the JSON database file exists and create it if not.
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
             # Initialize with an empty entity list structure
            initial_deep_memory = {"entities": []}
            with open(self.filepath, 'w') as f:
                json.dump(initial_deep_memory, f, indent=4)
                print(f"Deep memory database file created at: {self.filepath}")
        else:
            print(f"Deep memory database file already exists at: {self.filepath}")


    def _load_memory(self):
        """
        Internal function to load deep memory data from the JSON file.
        """
        if not os.path.exists(self.filepath):
            self._check_and_create_db() # Ensure file exists before trying to load

        try:
            with open(self.filepath, 'r') as f:
                # Handle empty file case
                content = f.read()
                if not content:
                    print(f"Warning: Deep memory file {self.filepath} is empty. Initializing.")
                    return {"entities": []}
                return json.loads(content)
        except FileNotFoundError:
            # Should be handled by _check_and_create_db, but as a fallback
            print(f"Error: Database file not found at {self.filepath}.")
            return {"entities": []} # Return default structure
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.filepath}. File might be corrupted. Re-initializing.")
            return {"entities": []} # Return default structure

    def _save_memory(self, memory_data):
        """
        Internal function to save deep memory data to the JSON file.
        """
        try:
            if memory_data is not None:
                with open(self.filepath, 'w') as f:
                    json.dump(memory_data, f, indent=4)
            else:
                print("Warning: No deep memory data to save (memory_data is None).")
        except Exception as e:
            print(f"Error saving to deep memory database file: {e}")

    def create_memory(self):
        """
        Creates memory by extracting NER from the associated memory_manager's
        structure and updating the deep memory database.
        """
        import json # Import here to only use when needed

        if not self.memory:
            print("Error: DeepMemory has no associated memory_manager instance.")
            return

        structure = self.memory.get_memory_structure() # Use the injected instance
        #print("DEBUG: Calling save_ner_process with structure:", json.dumps(structure, indent=2))
        ner_response_pydantic = self.bot_instance.save_ner_process(structure)

        if ner_response_pydantic is None:
            #print("No NER response received from save_ner_process, skipping deep memory update.")
            return
        if not isinstance(ner_response_pydantic, save_ner_structure):
             #print(f"Error: Expected save_ner_process to return save_ner_structure, got {type(ner_response_pydantic)}")
             return

        ner_response_dict = ner_response_pydantic.model_dump()
        new_entities = ner_response_dict.get("entities", [])
        #print(f"DEBUG: New entities extracted: {new_entities}")

        # Load the current state of deep memory *before* merging
        existing_memory_data = self._load_memory()

        if existing_memory_data is None:
            print("Could not load existing deep memory, creating new deep memory file.")
            memory_to_save = {"entities": new_entities} # Initialize structure correctly
        else:
            memory_to_save = existing_memory_data # Start with existing memory
            existing_entities = memory_to_save.get("entities", [])

            if not isinstance(existing_entities, list):
                print("Warning: 'entities' in existing deep memory is not a list. Resetting.")
                existing_entities = []

            # --- Merging Logic ---
            entity_map = {entity.get("Named_Entity").lower(): entity for entity in existing_entities if entity.get("Named_Entity")} # Use lowercased keys

            for new_entity in new_entities:
                entity_name = new_entity.get("Named_Entity")
                new_excerpts = new_entity.get("excerpts", [])

                if not entity_name: # Skip entities without a name
                    #print(f"Warning: Skipping new entity without a 'Named_Entity': {new_entity}")
                    continue

                if entity_name.lower() in entity_map: # Case-insensitive check
                    # Entity exists, merge excerpts
                    existing_entity = entity_map[entity_name.lower()] # Retrieve using lowercase key
                    existing_excerpts = existing_entity.get("excerpts", [])
                    if not isinstance(existing_excerpts, list): # Ensure excerpts is a list
                        existing_excerpts = []
                    # Add only unique new excerpts
                    for excerpt in new_excerpts:
                        if excerpt not in existing_excerpts:

                            existing_excerpts.append(f"{excerpt}. (added on {time.strftime('%Y-%m-%d %H:%M:%S')})") # Add timestamp
                    existing_entity["excerpts"] = existing_excerpts
                else:
                    # Entity is new, add it to the map and the list
                    # Do not store lowercase key in the list, keep original entity for saving
                    existing_entities.append(new_entity)
            # --- End Merging Logic ---

            memory_to_save["entities"] = existing_entities # Update the entities list

        #print("DEBUG: Deep Memory state after merge:", json.dumps(memory_to_save, indent=2))
        self._save_memory(memory_to_save)
        self.memory_data = memory_to_save # Update in-memory cache
        self.summarize_deep_memory()
        #print("Deep memory updated.")

    def summarize_deep_memory(self):
        """
        Based on threasholds, this function looks for individual entities in the deep memory structure and summarizes them if necessary.
        """
        # Load the latest deep memory data for searching
        current_deep_memory = self._load_memory()
        if current_deep_memory is None:
            print("Deep memory data not loaded, cannot perform search.")
            return []

        entities_in_memory = current_deep_memory.get("entities", [])
        if not isinstance(entities_in_memory, list):
            print("Warning: 'entities' in deep memory data is not a list, search might fail.")
            return []

        updated_entities = False # Flag to track if any entity was updated

        for entity in entities_in_memory:
            entity_name = entity.get("Named_Entity")
            excerpts = entity.get("excerpts", [])
            if isinstance(excerpts, list):
                # Check if the number of excerpts exceeds a threshold
                if len(excerpts) > 5:
                    # Summarize the excerpts
                    summarized_excerpts = self.bot_instance.summarize_excerpts(excerpts, entity_name)
                    # Update the entity with the summarized excerpts
                    entity["excerpts"] = summarized_excerpts
                    #print(f"Summarized excerpts for entity '{entity_name}'.")
                    updated_entities = True # Set flag to True because an entity was updated
                else:
                    #print(f"Entity '{entity_name}' has {len(excerpts)} excerpts, no summarization needed.")
                    continue

        if updated_entities: # Only save if something was actually updated
            self._save_memory(current_deep_memory) # Save the modified deep memory back to file
            self.memory_data = current_deep_memory # Update in-memory cache
            print("Deep memory summarized entities saved.")
        else:
            print("No entities needed summarization, deep memory not saved.")


    def random_access(self):
        """
        Provides a random access of a random entity and its excerpts from deep memory.
        Returns it as a dictionary.
        """
        # Load the latest deep memory data for searching
        current_deep_memory = self._load_memory()
        if current_deep_memory is None:
            print("Deep memory data not loaded, cannot perform search.")
            return {}

        entities_in_memory = current_deep_memory.get("entities", [])
        if not isinstance(entities_in_memory, list):
            print("Warning: 'entities' in deep memory data is not a list, search might fail.")
            return {}

        if not entities_in_memory:
            print("No entities found in deep memory.")
            return {}

        random_entity = random.choice(entities_in_memory)
        random_excerpts = random_entity.get("excerpts", [])
        if not isinstance(random_excerpts, list):
            print(f"Warning: Excerpts for entity '{random_entity.get('Named_Entity')}' is not a list: {random_excerpts}")
            return {}
        #print(f"Randomly selected entity: {random_entity.get('Named_Entity')}")
        #print(f"Excerpts: {random_excerpts}")
        return random_entity



    def search_memory_excerpts(self) -> List[str]:
        """
        Searches deep memory for entities matching the NER terms extracted
        from the associated memory_manager's current structure.

        Returns:
            List[str]: A list of relevant excerpts found.
        """
        if not self.memory:
            print("Error: DeepMemory has no associated memory_manager instance.")
            return []

        structure = self.memory.get_memory_structure() # Use the injected instance
        #print("DEBUG: Calling look_ner_process with structure:", json.dumps(structure, indent=2))
        ner_pydantic = self.bot_instance.look_ner_process(structure)

        if ner_pydantic is None:
            print("No NER response received from look_ner_process, cannot perform deep memory search.")
            return []
        if not isinstance(ner_pydantic, look_ner_structure):
             print(f"Error: Expected look_ner_process to return look_ner_structure, got {type(ner_pydantic)}")
             return []

        search_ner_strings = ner_pydantic.named_entities
        #print(f"DEBUG: NER terms to search in deep memory: {search_ner_strings}")

        # Load the latest deep memory data for searching
        current_deep_memory = self._load_memory()
        if current_deep_memory is None:
            print("Deep memory data not loaded, cannot perform search.")
            return []

        entities_in_memory = current_deep_memory.get("entities", [])
        if not isinstance(entities_in_memory, list):
            print("Warning: 'entities' in deep memory data is not a list, search might fail.")
            return []

        found_excerpts = []
        if not search_ner_strings:
            #print("DEBUG: No NER terms provided for search.")
            return []

        #print(f"DEBUG: Searching {len(entities_in_memory)} entities in deep memory.")
        for search_ner_string in search_ner_strings:
            search_lower = search_ner_string.lower() # Case-insensitive search
            for entity in entities_in_memory:
                entity_name = entity.get("Named_Entity")
                if entity_name and entity_name.lower() == search_lower: # Case-insensitive comparison already here
                    excerpts = entity.get("excerpts", [])
                    if isinstance(excerpts, list):
                        # Add excerpts that are not already found
                        for excerpt in excerpts:
                             if excerpt not in found_excerpts:
                                 found_excerpts.append(excerpt)
                        #print(f"DEBUG: Found {len(excerpts)} excerpts for entity '{entity_name}'.")
                    else:
                        print(f"Warning: Excerpts for entity '{entity_name}' is not a list: {excerpts}")
                    # Assuming entity names are unique, break inner loop once found
                    break


        #print(f"DEBUG: Total unique excerpts found: {len(found_excerpts)}")
        return found_excerpts
