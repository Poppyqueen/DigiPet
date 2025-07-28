# deep_memory.py

from typing import List
import json


# Import utils
from utils.pydantic_models import save_ner_structure # Import from pydantic_models.py

from utils.embeddings_providers.openai_embeddings import OpenAIEmbeddingProvider
from utils.embeddings_providers.google_embeddings import GoogleEmbeddingProvider
from utils.embeddings_providers.ollama_embeddings import OllamaEmbeddingProvider


from utils.utils_ai_providers.gemini_provider import GeminiProv
from utils.utils_ai_providers.openai_provider import OpenAIProv
from utils.utils_ai_providers.groq_provider import GroqProv
from utils.utils_ai_providers.ollama_provider import OllamaProv


# --- We will now use both the DatabaseManager and EmbeddingOperations ---
from memory.deep_memory_db_managers.deep_memory_database import DatabaseManager
from memory.deep_memory_db_managers.embedding_operations import EmbeddingOperations
import configparser




class DeepMemory:
    """
    A class to manage a deep memory system for an LLM agent using an SQLite backend.
    This module handles the storage and retrieval of structured information (entities and their
    characteristics) identified via semantic similarity of their embeddings.
    """
    def __init__(self, filepath: str, logger=None):
        """
        Initialize the DeepMemory instance.

        Args:
            filepath (str): Path to the SQLite database file.
        """
        self.log=logger


        self.db_manager = DatabaseManager(filepath)
        # --- Initialize EmbeddingOperations to handle similarity searches ---
        self.embedding_op = EmbeddingOperations(filepath)
        
        self.db_manager.create_tables()

    ### ///////// Init config  /////////  #####
        main_config = configparser.ConfigParser()
        main_config.read('main_config.ini')
        embeddings_config_selected_provider = main_config['AI_DeepMemory']['deep_memory_embeddings_provider']

        embeddings_available_providers = {
            "google": {"client": GoogleEmbeddingProvider},
            "openai": {"client": OpenAIEmbeddingProvider},
            "ollama": {"client": OllamaEmbeddingProvider}
        }

        if embeddings_config_selected_provider in embeddings_available_providers:
            embeddings_config_client = embeddings_available_providers[embeddings_config_selected_provider]["client"]
            print(f"Deep Memory using embedding provider: {embeddings_config_selected_provider}")
        else:
            print(f"Error: '{embeddings_config_selected_provider}' is not a recognized provider. Falling back to OpenAI.")
            embeddings_config_client = OpenAIEmbeddingProvider



        ai_config_model_name = main_config['AI_DeepMemory']['deep_memory_ai']
        ai_config_model_provider = main_config['AI_DeepMemory']['deep_memory_ai_provider']

        ai_bot_providers = {
            "gemini": {
                "client": GeminiProv
            },
            "openai": {
                "client": OpenAIProv
            },
            "groq": {
                "client": GroqProv
            },
            "ollama": {
                "client": OllamaProv
            }
        }

        # 4. Use the mapping dictionary to get the actual JSON structure
        if ai_config_model_provider in ai_bot_providers:
            ai_config_client = ai_bot_providers[ai_config_model_provider]["client"]
            print(f"Loaded state: {ai_config_model_provider}")
            print(ai_config_client)

        else:
            print(f"Error: '{ai_config_model_provider}' is not a recognized state.")
            # Handle the error, perhaps by falling back to a default state


        self.bot_instance = ai_config_client(selected_model=ai_config_model_name)

        self.embeddings_ai = embeddings_config_client()

        self._message_embeddings_cache = {}


    def _concatenate_n_strings(self, string_list, num_to_grab, insert="\n"):
        """
        Concatenates a specified number of strings from the beginning of a list.
        Allows a special "all" tag for num_to_grab to concatenate all strings.

        Args:
            string_list (list): A list of strings.
            num_to_grab (int or str): The number of strings to grab from the beginning
                                    of the list to concatenate. Can be an integer or
                                    the string "all" (case-insensitive) to grab all entries.
            insert (str): The string to insert between concatenated strings. Defaults to a newline.

        Returns:
            str: A single string formed by concatenating the specified number
                of strings, or an empty string if num_to_grab is 0 or less (and not "all"),
                or if the list is empty.
        """
        if not isinstance(string_list, list):
            raise TypeError("Input 'string_list' must be a list.")
        if not all(isinstance(s, str) for s in string_list):
            raise TypeError("All elements in 'string_list' must be strings.")

        # Validate num_to_grab
        if not (isinstance(num_to_grab, int) or (isinstance(num_to_grab, str) and num_to_grab.lower() == "all")):
            raise TypeError("Input 'num_to_grab' must be an integer or the string 'all'.")

        if not string_list:
            return ""

        if isinstance(num_to_grab, int):
            if num_to_grab < 0:
                print("Warning: num_to_grab is negative. Returning an empty string.")
                return ""
            if num_to_grab == 0:
                return ""
            # Ensure we don't try to grab more strings than available
            actual_num_to_grab = min(num_to_grab, len(string_list))
        else:  # num_to_grab is "all"
            actual_num_to_grab = len(string_list)

        # Use slice notation to get the desired number of strings and then join them
        final_string = insert.join(string_list[:actual_num_to_grab])
        return final_string


    def _search_entities(self, memory_structure)->save_ner_structure:

        """
        This function searches the current memory structure for entities and their characteristics, returns a pydantic structure
        with the nested entities and characteristics, aswell as a map of sources from messages with their message UID
        """

        # Define the threshold for considering two entities the same

        # 1. Format and persist messages from short-term memory
        all_messages = []
        for source, messages in memory_structure.get("short_term", {}).items():
            for msg in messages:
                msg_copy = msg.copy()
                msg_copy['source'] = source
                all_messages.append(msg_copy)

        all_messages.sort(key=lambda x: x['timestamp'])

        if not all_messages:
            print("No messages in short-term memory to process.")
            return

        formatted_memory_list = [
            f"####\ntimestamp: {msg['timestamp']}\nsource: {msg['source']}\nunique_id: {msg['unique_id']}\ncontent: {json.dumps(msg['content']) if isinstance(msg['content'], dict) else msg['content']}\n####"
            for msg in all_messages
        ]
        formatted_memory_string = "\n\n".join(formatted_memory_list)

        # 2. Call LLM for structured data extraction
        system_message = (
            "You are a sophisticated data extraction agent. Analyze the provided memory transcript. "
            "Identify key named entities (objects, people, projects, concepts, etc.). For each entity, "
            "consolidate all related information into a list of distinct 'INTRINSIC' textual description or mention of specific characteristics. "
            "Intrinsic qualities are properties that an object has in itself, independently of anything else—they don't depend on the object's relationship to other things."
            "For each characteristic, list the 'unique_id' of the source message(s)."
            "Examples include observable and quantifiable qualities such as specific materials, colors or shapes for objects:"
            "Red rubber, Bouncy and stiff, Has a particular shine to it, It has the ID 000020"
            "You also have to extract entities from contextual clues, exchanges, and patterns observed in behaviors or mentioned qualities."
            "If possible, also extract associative or symbolic meaning as characteristics of the entities, specially if quantifiable qualities are missing"
        )

        try:
            ner_response_pydantic = self.bot_instance.structured_output(
                system=system_message,
                user=formatted_memory_string,
                structure=save_ner_structure
            )
        except Exception as e:
            print(f"An error occurred during the LLM call: {e}")
            return

        if not ner_response_pydantic or not isinstance(ner_response_pydantic, save_ner_structure):
            print(f"Failed to get a valid structured response from the LLM. Type: {type(ner_response_pydantic)}")
            return
        
        print(f"LLM processing complete. Found {len(ner_response_pydantic.entities)} potential entities to process.")
        
        return ner_response_pydantic
    



    def _process_similar_results(self, similar_results, threshold, entity_name=""):
        """Helper to process similar results and format them."""
        memory_results = []
        if similar_results:
            for result in similar_results:
                if result['similarity_score'] >= threshold:
                    print(f"\nFound similar entity (ID: {result['entity_id']}) for '{entity_name}' with score {result['similarity_score']:.4f}. Saving info for context.")
                    
                    # Safely get entity name
                    name_record = self.db_manager.get_entity_by_id(result['entity_id'])
                    result_name = name_record.get('name') if name_record else "Unknown Entity"

                    raw_qualities = result['raw_text']
                    
                    # Get messages, which are expected to be list of dictionaries from the DB
                    messages_dicts = self.db_manager.get_messages_for_entity_current_characteristic(result['entity_id'])

                    # Ensure messages_dicts is a list; if not, initialize as empty list
                    if not isinstance(messages_dicts, list):
                        print(f"Warning: get_messages_for_entity_current_characteristic for entity {result['entity_id']} did not return a list. Received type: {type(messages_dicts)}. Treating as empty list.")
                        messages_dicts = []

                    # Transform list of dictionaries into a list of strings (message contents)
                    messages_contents = []
                    for msg_dict_from_db in messages_dicts:
                        # The key for the original message data is 'raw_json'
                        if isinstance(msg_dict_from_db, dict) and 'raw_json' in msg_dict_from_db:
                            try:
                                # The 'raw_json' field is already a dictionary when retrieved from the DB,
                                # so json.loads() is not needed here.
                                original_msg_data = msg_dict_from_db['raw_json']

                                if not isinstance(original_msg_data, dict):
                                    print(f"Warning: 'raw_json' content is not a dictionary as expected for message ID {msg_dict_from_db.get('id', 'N/A')}: {original_msg_data}. Skipping.")
                                    continue # Skip this message if raw_json isn't a dictionary

                                # The 'content' field within original_msg_data can be a string or a dict
                                if 'content' in original_msg_data:
                                    content = original_msg_data['content']
                                    # Ensure content is a string before appending
                                    messages_contents.append(json.dumps(content) if isinstance(content, dict) else str(content))
                                else:
                                    print(f"Warning: 'content' key missing in original_msg_data for message ID {msg_dict_from_db.get('id', 'N/A')}: {original_msg_data}. Skipping.")
                            except Exception as e: # Catch any other unexpected errors during processing
                                print(f"Error processing message from DB (ID: {msg_dict_from_db.get('id', 'N/A')}): {original_msg_data} - {e}. Skipping this message.")
                        else:
                            # This block will now only be hit if the top-level dict is malformed or 'raw_json' is missing
                            print(f"Warning: Message dictionary from DB format unexpected or 'raw_json' key missing (ID: {msg_dict_from_db.get('id', 'N/A')}): {msg_dict_from_db}. Skipping this message.")

                    # Now pass the list of strings to _concatenate_n_strings
                    concat = self._concatenate_n_strings(messages_contents, 5)
                    
                    result_message = f"Entity name:{result_name}\nRaw qualities of Identified object:{raw_qualities}\nSource messages for memories:{concat}"
                    memory_results.append(result_message)
        return memory_results
    
    def quick_search(self, memory_structure: dict, characteristics_flag=False) -> str:
        """
        This function performs a quick search within the current memory structure,
        either by processing entities and their characteristics using LLM embeddings
        (if characteristics_flag is True) or by directly embedding individual messages
        for similarity comparison.

        It searches the current memory structure for entities/messages and compares them
        with entities/messages in the DB using cosine similarity of embeddings.

        Returns a well-structured, formatted string for injection into an LLM context window.
        """
        self.log.dump_text("###########")

        init_message = f"DEEP MEMORIES QUICK SEARCH INITIALIZED"
        print(init_message)
        self.log.dump_text(init_message)

        # Define the threshold for finding entities that might be relatively similar
        CHARACTERISTICS_SIMILARITY_THRESHOLD = 0.6
        NO_CHAR_SIMILARITY_THRESHOLD = 0.5

        memory_results = ["\n"]
        memory_context = ""
        
        # New set to store unique characteristic IDs to avoid duplicates
        processed_characteristic_ids = set()

        # Check if the database has entries
        db_has_data = self.db_manager.has_data()  # Assuming this returns True if has data.

        if not db_has_data:
            message = "Database is empty. No search can be performed."
            print(message)
            self.log.dump_text(message)
            self.log.dump_text("\nDEEP MEMORIES QUICK SEARCH ENDED ")
            self.log.dump_text("\n###########")
            return ""

        if characteristics_flag:
            message = "Process for Characteristics search"
            print(message)
            self.log.dump_text(message)
            entities_result = self._search_entities(memory_structure)  # Renamed to avoid conflict with list 'entities'

            if not entities_result or not entities_result.entities:
                message = "No entities found for characteristics search."
                print(message)
                self.log.dump_text(message)
                return ""

            # 3. Process each potential entity from the LLM response
            for entity_data in entities_result.entities:
                entity_name = entity_data.named_entity.strip()
                if not entity_name:
                    message = "  Entity name is empty. Skipping."
                    print(message)
                    self.log.dump_text(message)
                    continue

                # Consolidate new characteristics and generate a query embedding
                new_characteristics_text = ". ".join([char.characteristic for char in entity_data.characteristics])
                new_characteristics_text = f"{entity_name}. {new_characteristics_text}"
                if not new_characteristics_text:
                    message = f"  No characteristics text for '{entity_name}'. Skipping."
                    print(message)
                    self.log.dump_text(message)
                    continue

                try:
                    query_embedding = self.embeddings_ai.make_embeddings(new_characteristics_text)
                    query_embedding = query_embedding.squeeze()
                    message = f"  Successfully generated embedding for '{entity_name}'."
                    print(message)
                    self.log.dump_text(message)
                except Exception as e:
                    message = f"  Error generating embedding for '{entity_name}': {e}"
                    print(message)
                    self.log.dump_text(message)
                    continue

                # Search for similar entities
                similar_results = self.embedding_op.search_similar_characteristics(query_embedding, top_n=6)

                # Process and format similar results, now adding deduplication
                for result in similar_results:
                    # Only add if the characteristic ID hasn't been processed yet and meets threshold
                    if result["characteristic_id"] not in processed_characteristic_ids and \
                       result["similarity_score"] >= CHARACTERISTICS_SIMILARITY_THRESHOLD:
                        memory_results.extend(self._process_similar_results(
                            [result], CHARACTERISTICS_SIMILARITY_THRESHOLD, entity_name
                        ))
                        processed_characteristic_ids.add(result["characteristic_id"])


            memory_context = self._concatenate_n_strings(memory_results, "all")

        else:  # No characteristics search (direct message embedding comparison)
            message = "Process for No characteristics search:"
            print(message)
            self.log.dump_text(message)

            # 1. Format and persist messages from short-term memory
            all_messages = []
            for source, messages in memory_structure.get("short_term", {}).items():
                for msg in messages:
                    msg_copy = msg.copy()
                    msg_copy['source'] = source
                    all_messages.append(msg_copy)

            all_messages.sort(key=lambda x: x['timestamp'])

            if not all_messages:
                message = "No messages in short-term memory to process."
                print(message)
                self.log.dump_text(message)
                return ""
                        # Use an internal cache for message embeddings within this method call
            # This cache is cleared with each call to quick_search for `else` block

# Using the instance-level cache for message embeddings
            for msg in all_messages:
                # Use a unique identifier for the message for caching.
                # A combination of 'source' and 'unique_id' is robust.
                message_key = f"{msg['source']}-{msg['unique_id']}"

                query_embedding = None
                if message_key in self._message_embeddings_cache: # <-- NOW USING INSTANCE CACHE
                    query_embedding = self._message_embeddings_cache[message_key]
                    message = f"  Using cached embedding for message: {message_key}"
                    print(message)
                    self.log.dump_text(message)
                else:
                    try:
                        # Ensure content is string for embedding
                        content_to_embed = json.dumps(msg['content']) if isinstance(msg['content'], dict) else str(msg['content'])
                        query_embedding = self.embeddings_ai.make_embeddings(content_to_embed)
                        query_embedding = query_embedding.squeeze()
                        self._message_embeddings_cache[message_key] = query_embedding # <-- NOW STORING IN INSTANCE CACHE
                        message = f"  Generated and cached embedding for message: {message_key}"
                        print(message)
                        self.log.dump_text(message)
                    except Exception as e:
                        message = f"  Error generating embedding for message {message_key}: {e}"
                        print(message)
                        self.log.dump_text(message)
                        continue

                # Search for similar entities (or messages, depending on your DB indexing)
                similar_results = self.embedding_op.search_similar_characteristics(query_embedding, top_n=4)

                # Process and format similar results. Here, we don't have a specific 'entity_name'
                # from the original message, so it will be an empty string in the print statement.
                for result in similar_results:
                    # Apply deduplication here as well, based on characteristic_id
                    if result["characteristic_id"] not in processed_characteristic_ids and \
                       result["similarity_score"] >= NO_CHAR_SIMILARITY_THRESHOLD:
                        memory_results.extend(self._process_similar_results(
                            [result], NO_CHAR_SIMILARITY_THRESHOLD
                        ))
                        processed_characteristic_ids.add(result["characteristic_id"])

            memory_context = self._concatenate_n_strings(memory_results, "all")

        debug_message = f"DEBUG MEMORIES EXTRACTED FROM QUICK SEARCH: \n - {memory_context}"
        print(debug_message)
        self.log.dump_text(f"MEMORIES EXTRACTED FROM QUICK SEARCH: \n - {memory_context}")
        self.log.dump_text("DEEP MEMORIES QUICK SEARCH ENDED")
        self.log.dump_text("###########")

        return memory_context
        
    def create_memory(self, memory_structure: dict):
        """
        Processes a memory structure to extract entities, and based on embedding similarity,
        either creates a new entity or merges information with an existing one.

        Args:
            memory_structure (dict): A dictionary containing the agent's short-term memory.
        """
        self.log.dump_text("############")

        message = "Starting deep memory creation process with similarity-based identification..."
        print(message)
        self.log.dump_text(message)
        
        SIMILARITY_THRESHOLD = 0.85

        self._message_embeddings_cache={} # Drop the messages cache as some will removed when this is called

        # 1. Format and persist messages from short-term memory
        all_messages = []
        for source, messages in memory_structure.get("short_term", {}).items():
            for msg in messages:
                msg_copy = msg.copy()
                msg_copy['source'] = source
                all_messages.append(msg_copy)

        all_messages.sort(key=lambda x: x['timestamp'])

        if not all_messages:
            message = "No messages in short-term memory to process."
            print(message)
            self.log.dump_text(message)
            return

        message_id_map = {}
        for msg in all_messages:
            message_pk = self.db_manager.add_message(
                source_unique_id=msg['unique_id'],
                source_tag=msg['source'],
                msg_type="short_term_context",
                raw_data_dict=msg
            )
            if message_pk:
                message_id_map[msg['unique_id']] = message_pk


        ner_response_pydantic=self._search_entities(memory_structure)

        if not ner_response_pydantic or not isinstance(ner_response_pydantic, save_ner_structure):
            message = f"Failed to get a valid structured response from the LLM. Type: {type(ner_response_pydantic)}"
            print(message)
            self.log.dump_text(message)
            return
        
        message = f"LLM processing complete. Found {len(ner_response_pydantic.entities)} potential entities to process."
        print(message)
        self.log.dump_text(message)

        # 3. Process each potential entity from the LLM response
        for entity_data in ner_response_pydantic.entities:
            entity_name = entity_data.named_entity.strip()
            message = f"Processing entity: '{entity_name}'"
            print(message)
            self.log.dump_text(message)
            if not entity_name:
                message = "  Entity name is empty. Skipping."
                print(message)
                self.log.dump_text(message)
                continue

            new_characteristics_text = ". ".join([char.characteristic for char in entity_data.characteristics])
            new_characteristics_text = f"{entity_name}. {new_characteristics_text}"
            message = f"  Consolidated characteristics text: '{new_characteristics_text}'"
            print(message)
            self.log.dump_text(message)
            if not new_characteristics_text:
                message = f"  No characteristics text for '{entity_name}'. Skipping."
                print(message)
                self.log.dump_text(message)
                continue

            try:
                query_embedding = self.embeddings_ai.make_embeddings(new_characteristics_text)
                query_embedding = query_embedding.squeeze()
                message = f"  Successfully generated embedding for '{entity_name}'."
                print(message)
                self.log.dump_text(message)
            except Exception as e:
                message = f"  Error generating embedding for '{entity_name}': {e}"
                print(message)
                self.log.dump_text(message)
                continue

            entity_id = None
            final_text_to_embed = new_characteristics_text
            
            similar_results = self.embedding_op.search_similar_characteristics(query_embedding, top_n=1)

            if similar_results:
                top_match = similar_results[0]
                if top_match['similarity_score'] > SIMILARITY_THRESHOLD:
                    message = f"\nFound similar entity (ID: {top_match['entity_id']}) for '{entity_name}' with score {top_match['similarity_score']:.4f}. Merging info."
                    print(message)
                    self.log.dump_text(message)
                    entity_id = top_match['entity_id']
                    existing_char_text = top_match['raw_text']
                    final_text_to_embed = existing_char_text + ". " + new_characteristics_text
                    message = "Re-generating embedding for merged text."
                    print(message)
                    self.log.dump_text(message)
                    query_embedding = self.embeddings_ai.make_embeddings(final_text_to_embed)
                    query_embedding = query_embedding.squeeze()
                else:
                    message = f"\nTop match for '{entity_name}' is below threshold (score: {top_match['similarity_score']:.4f}). Creating new entity."
                    print(message)
                    self.log.dump_text(message)
            else:
                message = f"\nNo existing entities found. Creating new entity for '{entity_name}'."
                print(message)
                self.log.dump_text(message)

            if entity_id is None:
                entity_id = self.db_manager.add_entity(name=entity_name)
                if not entity_id:
                    message = f"Error: Failed to create new entity '{entity_name}'. Skipping."
                    print(message)
                    self.log.dump_text(message)
                    continue
                message = f"Created new entity '{entity_name}' with ID: {entity_id}"
                print(message)
                self.log.dump_text(message)

            latest_version = self.db_manager.get_latest_characteristic_version(entity_id)
            new_version = latest_version + 1

            characteristic_id = self.db_manager.add_characteristics(
                entity_id=entity_id,
                raw_text=final_text_to_embed,
                version=new_version,
                embeddings_array=query_embedding
            )

            if not characteristic_id:
                message = f"Error: Failed to save characteristics for entity ID {entity_id}. Skipping."
                print(message)
                self.log.dump_text(message)
                continue
            
            message = f"Saved new characteristics (v{new_version}) with ID: {characteristic_id}"
            print(message)
            self.log.dump_text(message)

            self.db_manager.update_entity_current_characteristics(entity_id, characteristic_id)
            
            all_source_message_uids = {uid for char in entity_data.characteristics for uid in char.messages_sources_ids}
            
            for uid in all_source_message_uids:
                message_pk = message_id_map.get(uid)
                if message_pk:
                    self.db_manager.link_characteristic_to_message(characteristic_id, message_pk, score=1.0)
                else:
                    message = f"Warning: Could not find database message ID for source unique_id '{uid}' to link."
                    print(message)
                    self.log.dump_text(message)
        
        message = "\nDeep memory update process finished."
        print(message)
        self.log.dump_text(message)
        self.log.dump_text("\n############")


    # --- The functions below are the OLD versions and need a complete rewrite to work with SQLite. ---
    # They are kept as placeholders or for future implementation.
    
    def summarize_deep_memory(self):
        print("Function 'summarize_deep_memory' needs to be updated for SQLite integration.")
        pass

    def random_access(self):
        print("Function 'random_access' needs to be updated for SQLite integration.")
        return {}

    def search_memory_excerpts(self) -> List[str]:
        print("Function 'search_memory_excerpts' needs to be updated for SQLite integration.")
        return []
