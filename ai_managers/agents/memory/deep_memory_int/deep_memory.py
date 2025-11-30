# deep_memory.py

from typing import List
import json
import time
import numpy as np



# Import utils
from .....utils.pydantic_models import save_ner_structure # Import from pydantic_models.py
from .....utils.loc_datetime import datetime

from ....ai_utils.ai_loader import EmbeddingsConfiguration, AIConfiguration


# --- We will now use both the DatabaseManager and EmbeddingOperations ---
from .deep_memory_db.deep_memory_database import DatabaseManager
from .deep_memory_db.embedding_operations import EmbeddingOperations





class DeepMemory:
    """
    A class to manage a deep memory system for an LLM agent using an SQLite backend.
    This module handles the storage and retrieval of structured information (entities and their
    characteristics) identified via semantic similarity of their embeddings.
    """
    def __init__(self, filepath: str, logger=None, config_manager=None):
        """
        Initialize the DeepMemory instance.

        Args:
            filepath (str): Path to the SQLite database file.
        """
        self.log=logger

        config_manager


        self.db_manager = DatabaseManager(filepath)
        # --- Initialize EmbeddingOperations to handle similarity searches ---
        self.embedding_op = EmbeddingOperations(filepath)
        
        self.db_manager.create_tables()

    ### ///////// Init config  /////////  #####

        embeddings_config_selected_provider = config_manager.get_config('AI_DeepMemory','deep_memory_embeddings_provider')



        ai_config_model_name = config_manager.get_config('AI_DeepMemory','deep_memory_ai')
        ai_config_model_provider = config_manager.get_config('AI_DeepMemory','deep_memory_ai_provider')

        self.bot_instance = AIConfiguration(provider=ai_config_model_provider,model=ai_config_model_name,mode="simple_ai").get_client()

        self.embeddings_ai = EmbeddingsConfiguration(embeddings_config_selected_provider).get_embeddings()

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
    


    def _prepare_and_filter_messages_optimized(self, memory_structure: dict, max_messages: int) -> list:
        """
        Intelligently prepare and filter messages using multiple strategies.
        """
        all_messages = []
        for source, messages in memory_structure.get("short_term", {}).items():
            for msg in messages:
                msg_copy = msg.copy()
                msg_copy['source'] = source
                # Add content length for filtering
                content_str = json.dumps(msg['content']) if isinstance(msg['content'], dict) else str(msg['content'])
                msg_copy['content_length'] = len(content_str)
                all_messages.append(msg_copy)

        if len(all_messages) <= max_messages:
            return all_messages

        # Sort by timestamp (most recent first)
        all_messages.sort(key=lambda x: x['timestamp'], reverse=True)
        
        filtered_messages = []


        
        # Strategy 1: Always include most recent messages (30% of quota)
        recent_quota = max(2, int(max_messages * 0.3))
        filtered_messages.extend(all_messages[:recent_quota])
        remaining_quota = max_messages - len(filtered_messages)
        
        # Strategy 2: Include substantial messages (messages > 50 chars, up to 40% of remaining quota)
        if remaining_quota > 0:
            substantial_quota = max(1, int(remaining_quota * 0.4))
            substantial_messages = [
                msg for msg in all_messages[recent_quota:] 
                if msg['content_length'] > 50
            ][:substantial_quota]
            filtered_messages.extend(substantial_messages)
            remaining_quota = max_messages - len(filtered_messages)
        
        # # Strategy 3: Include keyword-rich messages
        # if remaining_quota > 0:
        #     important_keywords = ['important', 'remember', 'note', 'task', 'project', 'decision', 'action', 'todo']
        #     keyword_messages = []
            
        #     for msg in all_messages[len(filtered_messages):]:
        #         if any(msg in filtered_messages for msg in [msg]):  # Skip already included
        #             continue
        #         content_str = json.dumps(msg['content']) if isinstance(msg['content'], dict) else str(msg['content'])
        #         if any(keyword in content_str.lower() for keyword in important_keywords):
        #             keyword_messages.append(msg)
            
        #     filtered_messages.extend(keyword_messages[:remaining_quota])
        #     remaining_quota = max_messages - len(filtered_messages)
        
        # Strategy 4: Fill with diverse sources
        if remaining_quota > 0:
            sources_in_selection = {msg['source'] for msg in filtered_messages}
            diverse_messages = [
                msg for msg in all_messages
                if msg not in filtered_messages and msg['source'] not in sources_in_selection
            ][:remaining_quota]
            filtered_messages.extend(diverse_messages)
        
        return filtered_messages[:max_messages]

    def _cluster_similar_messages_optimized(self, messages: list) -> list:
        """
        Improved message clustering with better performance and accuracy.
        """
        if len(messages) <= 3:
            return [(msg, [msg]) for msg in messages]
        
        clusters = []
        unclustered = messages.copy()
        CLUSTERING_SIMILARITY_THRESHOLD = 0.75  # Slightly lower for better clustering
        
        # Process messages by content length (longer messages first as better representatives)
        unclustered.sort(key=lambda x: x.get('content_length', 0), reverse=True)
        
        while unclustered:
            representative = unclustered.pop(0)
            cluster = [representative]
            
            rep_content = json.dumps(representative['content']) if isinstance(representative['content'], dict) else str(representative['content'])
            
            # Skip very short messages as representatives
            if len(rep_content.strip()) < 10:
                clusters.append((representative, cluster))
                continue
            
            try:
                rep_embedding = self.embeddings_ai.make_embeddings(rep_content).squeeze()
                rep_norm = np.linalg.norm(rep_embedding)
                
                if rep_norm == 0:
                    clusters.append((representative, cluster))
                    continue
                    
            except Exception as e:
                clusters.append((representative, cluster))
                continue
            
            # Find similar messages with vectorized comparison
            to_remove = []
            for i, msg in enumerate(unclustered):
                # Skip very different sources unless content is very similar
                source_bonus = 0.1 if msg['source'] == representative['source'] else 0
                
                msg_content = json.dumps(msg['content']) if isinstance(msg['content'], dict) else str(msg['content'])
                
                try:
                    msg_embedding = self.embeddings_ai.make_embeddings(msg_content).squeeze()
                    msg_norm = np.linalg.norm(msg_embedding)
                    
                    if msg_norm == 0:
                        continue
                    
                    similarity = np.dot(rep_embedding, msg_embedding) / (rep_norm * msg_norm)
                    adjusted_threshold = CLUSTERING_SIMILARITY_THRESHOLD - source_bonus
                    
                    if similarity > adjusted_threshold:
                        cluster.append(msg)
                        to_remove.append(i)
                        
                except Exception:
                    continue
            
            # Remove clustered messages (reverse order to maintain indices)
            for i in reversed(to_remove):
                unclustered.pop(i)
            
            clusters.append((representative, cluster))
        
        return clusters

    def _get_or_generate_embedding_optimized(self, message: dict, message_key: str):
        """
        Optimized embedding generation with better error handling.
        """
        if message_key in self._message_embeddings_cache:
            return self._message_embeddings_cache[message_key]
        
        try:
            content_to_embed = json.dumps(message['content']) if isinstance(message['content'], dict) else str(message['content'])
            
            # Skip very short content
            if len(content_to_embed.strip()) < 5:
                return None
                
            query_embedding = self.embeddings_ai.make_embeddings(content_to_embed).squeeze()
            
            # Validate embedding
            if np.linalg.norm(query_embedding) == 0:
                return None
                
            self._message_embeddings_cache[message_key] = query_embedding
            return query_embedding
            
        except Exception as e:
            self.log.dump_text(f"Error generating embedding for message {message_key}: {e}")
            return None

    def _rank_and_filter_results_optimized(self, all_results: list, base_threshold: float,
                                        max_results: int, processed_char_ids: set, processed_entity_ids: set) -> list:
        """
        Advanced ranking and filtering with entity-level deduplication.
        """

        # Remove already processed characteristics
        filtered_results = [r for r in all_results if r["characteristic_id"] not in processed_char_ids]

        if not filtered_results:
            print("No new results to process after filtering.")
            return []

        # Enhanced scoring with multiple factors
        for result in filtered_results:
            score = result["similarity_score"]
            cluster_bonus = min(0.15, result.get('cluster_weight', 1) * 0.05)
            recency_bonus = 0
            if result.get('extracted_at_timestamp'):
                try:
                    timestamp = datetime.fromisoformat(result['extracted_at_timestamp'])
                    days_old = (datetime.now() - timestamp).days
                    recency_bonus = max(0, min(0.1, (30 - days_old) / 300))
                except:
                    pass
            entity_diversity_bonus = 0.05 if result["entity_id"] not in processed_entity_ids else -0.1
            result["final_score"] = score + cluster_bonus + recency_bonus + entity_diversity_bonus

        # Sort by enhanced score
        filtered_results.sort(key=lambda x: x["final_score"], reverse=True)

        # Apply adaptive threshold with entity diversity
        final_results = []
        seen_entities = set()

        # First pass: high-quality results
        for result in filtered_results:
            if (len(final_results) >= max_results or
                result["final_score"] < base_threshold):
                break
            final_results.append(result)
            seen_entities.add(result["entity_id"])
            processed_entity_ids.add(result["entity_id"])

        # Second pass: fill remaining slots with diverse entities if needed
        if len(final_results) < max_results * 0.7:
            remaining_slots = max_results - len(final_results)
            diverse_results = [
                r for r in filtered_results[len(final_results):]
                if r["entity_id"] not in seen_entities and r["final_score"] >= base_threshold * 0.8
            ][:remaining_slots]
            final_results.extend(diverse_results)
            for result in diverse_results:
                seen_entities.add(result["entity_id"])
                processed_entity_ids.add(result["entity_id"])

        # --- NEW: Final pass for entity deduplication ---
        deduplicated_results = []
        final_seen_entities = set()
        for result in final_results:
            if result["entity_id"] not in final_seen_entities:
                deduplicated_results.append(result)
                final_seen_entities.add(result["entity_id"])

        return deduplicated_results

    def _format_results_optimized(self, results: list) -> list:
        """
        Format results with enhanced context and efficiency.
        """
        if not results:
            return []
        
        # Batch get entity names for efficiency
        entity_ids = list(set(r["entity_id"] for r in results))
        entity_names = self.db_manager.get_entity_names_batch(entity_ids)
        
        formatted_results = []
        
        for result in results:
            entity_name = entity_names.get(result["entity_id"], "Unknown Entity")
            
            # Get source messages efficiently
            messages_dicts = self.db_manager.get_messages_for_entity_current_characteristic(result['entity_id'])
            
            # Process messages with error handling
            messages_contents = []
            if isinstance(messages_dicts, list):
                for msg_dict in messages_dicts[:2]:  # Limit to first 2 message for brevity
                    if isinstance(msg_dict, dict) and 'raw_json' in msg_dict:
                        try:
                            original_msg_data = msg_dict['raw_json']
                            if isinstance(original_msg_data, dict) and 'content' in original_msg_data:
                                content = original_msg_data['content']
                                content_str = json.dumps(content) if isinstance(content, dict) else str(content)
                                # Truncate very long messages
                                if len(content_str) > 200:
                                    content_str = content_str[:200] + "..."
                                messages_contents.append(content_str)
                        except Exception as e:
                            print(f"Error processing message for entity {result['entity_id']}: {e}")
            
            # Create concise context string
            source_context = " | ".join(messages_contents) if messages_contents else "No recent context"
            
            # Update entity access time for tracking
            self.db_manager.update_entity_last_access(result["entity_id"])
            
            result_message = (
                f"Entity: {entity_name} (Score: {result['final_score']:.3f})\n"
                f"Characteristics: {result['raw_text']}\n"
                f"Context: {source_context}\n"
            )
            
            formatted_results.append(result_message)
        
        return formatted_results

    def _handle_characteristics_search_optimized(self, memory_structure: dict, threshold: float, 
                                            processed_ids: set, max_results: int) -> str:
        """
        Optimized characteristics-based search with similar improvements.
        """
        message = "Process for Characteristics search (OPTIMIZED):"
        print(message)
        self.log.dump_text(message)
        
        entities_result = self._search_entities(memory_structure)
        
        if not entities_result or not entities_result.entities:
            message = "No entities found for characteristics search."
            print(message)
            self.log.dump_text(message)
            return ""
        
        memory_results = ["\n"]
        processed_entity_ids = set()
        
        # Limit entity processing for performance
        entities_to_process = entities_result.entities[:max_results]
        
        for entity_data in entities_to_process:
            entity_name = entity_data.named_entity.strip()
            if not entity_name:
                continue
            
            # Consolidate characteristics
            new_characteristics_text = ". ".join([char.characteristic for char in entity_data.characteristics])
            new_characteristics_text = f"{entity_name}. {new_characteristics_text}"
            
            if not new_characteristics_text:
                continue
            
            try:
                query_embedding = self.embeddings_ai.make_embeddings(new_characteristics_text).squeeze()
            except Exception as e:
                print(f"Error generating embedding for '{entity_name}': {e}")
                continue
            
            # Use optimized search
            similar_results = self.embedding_op.search_similar_characteristics_optimized(
                query_embedding, 
                top_n=min(4, max_results // len(entities_to_process) + 1),
                min_threshold=threshold
            )
            
            # Process results with deduplication
            for result in similar_results:
                if (result["characteristic_id"] not in processed_ids and 
                    result["entity_id"] not in processed_entity_ids and 
                    len(memory_results) < max_results):
                    
                    formatted_result = self._format_single_result_optimized(result, entity_name)
                    if formatted_result:
                        memory_results.append(formatted_result)
                        processed_ids.add(result["characteristic_id"])
                        processed_entity_ids.add(result["entity_id"])
        
        memory_context = self._concatenate_n_strings(memory_results, "all")
        return memory_context

    def _format_single_result_optimized(self, result: dict, query_entity_name: str = "") -> str:
        """
        Format a single result efficiently.
        """
        try:
            # Get entity name
            name_record = self.db_manager.get_entity_by_id(result['entity_id'])
            result_name = name_record.get('name') if name_record else "Unknown Entity"
            
            raw_qualities = result['raw_text']
            
            # Get limited message context
            messages_dicts = self.db_manager.get_messages_for_entity_current_characteristic(result['entity_id'])
            
            if isinstance(messages_dicts, list) and messages_dicts:
                # Take only first 2 messages and truncate
                messages_contents = []
                for msg_dict in messages_dicts[:2]:
                    if isinstance(msg_dict, dict) and 'raw_json' in msg_dict:
                        try:
                            original_msg_data = msg_dict['raw_json']
                            if isinstance(original_msg_data, dict) and 'content' in original_msg_data:
                                content = original_msg_data['content']
                                content_str = json.dumps(content) if isinstance(content, dict) else str(content)
                                if len(content_str) > 150:
                                    content_str = content_str[:150] + "..."
                                messages_contents.append(content_str)
                        except:
                            continue
                
                concat = " | ".join(messages_contents) if messages_contents else "No context"
            else:
                concat = "No context"
            
            query_info = f" (Query: {query_entity_name})" if query_entity_name else ""
            
            return (f"Entity: {result_name}{query_info} (Score: {result['similarity_score']:.3f})\n"
                    f"Qualities: {raw_qualities}\n"
                    f"Context: {concat}\n")
            
        except Exception as e:
            print(f"Error formatting result: {e}")
            return None
        

    def create_memory(self, memory_structure: dict):
        """
        Processes a memory structure to extract entities, and based on embedding similarity,
        either creates a new entity or merges information with an existing one.

        Uses a large AI LLM call, basically re-ingesting the recent short-term memories up to their token limits
        It analyzes the whole entries and tries to extract entities alongside sources.

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




    ###### rework

    def quick_search_optimized(self, memory_structure: dict, characteristics_flag=False, current_context="") -> str:
        """
        Optimized version of quick_search with intelligent filtering, clustering, and deduplication.
        Significantly reduces token usage while maintaining relevance.
        """
        self.log.dump_text("###########")
        
        init_message = "DEEP MEMORIES QUICK SEARCH INITIALIZED (OPTIMIZED)"
        print(init_message)
        self.log.dump_text(init_message)

        # Adaptive thresholds based on database size
        db_size = self.db_manager.get_total_characteristics_count()
        #CHARACTERISTICS_SIMILARITY_THRESHOLD = max(0.65, 0.85 - (db_size / 5000))
        NO_CHAR_SIMILARITY_THRESHOLD = max(0.55, 0.75 - (db_size / 5000))
        
        # Dynamic limits based on database size
        if db_size < 100:
            MAX_MEMORY_RESULTS = 20
            MAX_MESSAGES_TO_PROCESS = 15
        elif db_size < 500:
            MAX_MEMORY_RESULTS = 15
            MAX_MESSAGES_TO_PROCESS = 10
        else:
            MAX_MEMORY_RESULTS = 10
            MAX_MESSAGES_TO_PROCESS = 8
        
        memory_results = ["\n"]
        processed_characteristic_ids = set()
        processed_entity_ids = set()  # Track entities to avoid duplicates

        if not self.db_manager.has_data():
            message = "Database is empty. No search can be performed."
            print(message)
            self.log.dump_text(message)
            return ""

        if characteristics_flag: # DO NOT USE THIS 
            # return self._handle_characteristics_search_optimized(
            #     memory_structure, CHARACTERISTICS_SIMILARITY_THRESHOLD, 
            #     processed_characteristic_ids, MAX_MEMORY_RESULTS
            # )
            return "LLM Based quick search disabled."
        
        else:  # Optimized direct message embedding comparison
            message = f"Process for No characteristics search (OPTIMIZED): Max {MAX_MESSAGES_TO_PROCESS} messages, {MAX_MEMORY_RESULTS} results"
            print(message)
            self.log.dump_text(message)

            # 1. Prepare and intelligently filter messages
            all_messages = self._prepare_and_filter_messages_optimized(memory_structure, MAX_MESSAGES_TO_PROCESS)
            
            if not all_messages:
                message = "No messages in short-term memory to process."
                print(message)
                self.log.dump_text(message)
                return ""
            

            # Add current context as a pseudo-message for embedding comparison
            context_unique_id = f"context_{int(time.time() * 1000)}"


            context_structure = {
                "source": "current_context",
                "content": current_context.strip(),
                "timestamp": time.time(),
                "content_length": len(current_context.strip()),
                "unique_id": context_unique_id  # Now includes unique_id
            }

            all_messages.append(context_structure)

            all_messages.sort(key=lambda x: x['timestamp'], reverse=True)

            # 2. Cluster similar messages to reduce redundant processing
            message_clusters = self._cluster_similar_messages_optimized(all_messages)
            message = f"Clustered {len(all_messages)} messages into {len(message_clusters)} clusters"
            print(message)
            self.log.dump_text(message)
            
            # 3. Process clusters with smart result aggregation
            all_similarity_results = []
            
            for cluster_representative, cluster_messages in message_clusters:
                message_key = f"{cluster_representative['source']}-{cluster_representative['unique_id']}"
                
                # Get or generate embedding for representative message
                query_embedding = self._get_or_generate_embedding_optimized(cluster_representative, message_key)
                if query_embedding is None:
                    continue
                    
                # Dynamic search parameters based on cluster size and database size
                cluster_weight = min(2.0, len(cluster_messages) / 2.0)  # Larger clusters get more results
                dynamic_top_n = min(8, max(3, int(4 * cluster_weight)))
                
                # Use optimized search
                similar_results = self.embedding_op.search_similar_characteristics_optimized(
                    query_embedding, 
                    top_n=dynamic_top_n,
                    min_threshold=NO_CHAR_SIMILARITY_THRESHOLD * 0.7  # Slightly lower for initial filtering
                )

                if cluster_representative.get('source') == 'current_context':
                    cluster_weight *= 1.5  # Boost context relevance
                
                # Enhance results with cluster context
                for result in similar_results:
                    result['cluster_size'] = len(cluster_messages)
                    result['cluster_weight'] = cluster_weight
                    result['representative_message'] = cluster_representative
                    all_similarity_results.append(result)

            # DEBUG

                print(f"Processed cluster: {cluster_representative['unique_id']} with {len(cluster_messages)} messages")

            # 4. Intelligently rank, deduplicate and filter results
            final_results = self._rank_and_filter_results_optimized(
                all_similarity_results, 
                NO_CHAR_SIMILARITY_THRESHOLD,
                MAX_MEMORY_RESULTS,
                processed_characteristic_ids,
                processed_entity_ids
            )
            
            message = f"Filtered {len(all_similarity_results)} raw results to {len(final_results)} final results"
            print(message)
            self.log.dump_text(message)
            
            # 5. Format results with enhanced context
            memory_results.extend(self._format_results_optimized(final_results))

            memory_context = self._concatenate_n_strings(memory_results, "all")

        debug_message = f"OPTIMIZED QUICK SEARCH complete. Context length: {len(memory_context)} characters"
        print(debug_message)
        self.log.dump_text(f"MEMORIES EXTRACTED FROM OPTIMIZED QUICK SEARCH (Length: {len(memory_context)})")
        self.log.dump_text("DEEP MEMORIES QUICK SEARCH ENDED")
        self.log.dump_text("###########")

        print(memory_context)

        return memory_context
