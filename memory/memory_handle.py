# memory_handle.py
# Memory handle is a module to manage memory storage for an LLM, the system can be integrated into various situations where an agent needs
# to maintain a constant memory.

# It helps you set up a JSON database, to do different kinds of querries for memory management, the memory manager class contains functions to save
# memories into different sections and engage in a 'check' to summarize memories above our thesholds.

# Revamp at work

import json
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
import re
import uuid # <--- NEW: Import uuid for unique IDs

# Import extra memory module
from memory.deep_memory import DeepMemory # <--- Import DeepMemory here

from utils.tokens_handle import token_manager

from memory.memory_configs import (short_term_prompt, long_term_prompt)

from utils.utils_ai_providers.gemini_provider import GeminiProv
from utils.utils_ai_providers.openai_provider import OpenAIProv
from utils.utils_ai_providers.groq_provider import GroqProv
from utils.utils_ai_providers.ollama_provider import OllamaProv

import configparser

config = configparser.ConfigParser()
config.read('main_config.ini')
system_prompt = config['AI']['sys_prompt']
selected_model= config['AI']['memory_model']
config_selected_provider = config['AI']['memory_ai_provider']


available_providers = {
    "gemini": {
        "client":GeminiProv},
    "openai": {
        "client":OpenAIProv},
    "groq": {
        "client":GroqProv},
    "ollama": {
        "client":OllamaProv}
}


# 4. Use the mapping dictionary to get the actual JSON structure
if config_selected_provider in available_providers:
    config_client = available_providers[config_selected_provider]["client"]
    print(f"Loaded provider for memory: {config_selected_provider}")
    #print(config_client)

else:
    print(f"Error: '{config_selected_provider}' is not a recognized state.")
    # Handle the error, perhaps by falling back to a default state


# Define default filepaths
DEFAULT_MEMORY_DB = "memory_database.json"
DEFAULT_DEEP_MEMORY_DB = "deep_memory_database.json"

class memory_manager:

    SHORT_TERM_KEEP_COUNT = 10
    LONG_TERM_KEEP_COUNT = 5

    SHORT_TERM_TOKEN_THRESHOLD = 12000
    LONG_TERM_TOKEN_THRESHOLD = 12000

    # # Testing config:

    # SHORT_TERM_TOKEN_THRESHOLD = 300
    # LONG_TERM_TOKEN_THRESHOLD = 400


    def __init__(self, filepath: str = DEFAULT_MEMORY_DB, deep_memory_filepath: str = DEFAULT_DEEP_MEMORY_DB, deep_memory: bool = False, text_capture=None, sub_directory=None):
        self.token_manager = token_manager()
        self.text_capture=text_capture
        self.filepath = filepath
        self.deep_memory_filepath = deep_memory_filepath
        self._check_and_create_db()
        self.deep_memory_flag= deep_memory
        self.sub_directory=sub_directory

        self.bot_instance = config_client(selected_model)

        if self.bot_instance and self.deep_memory_flag:
            try:
                self.deep_memory = DeepMemory(
                    filepath=self.deep_memory_filepath,
                    ai_bot_instance=self.bot_instance,
                    memory_instance=self
                )
            except Exception as e:
                print(f"Error initializing DeepMemory: {e}")
                self.deep_memory = None
        else:
            print("DeepMemory not initialized because ai_bot_instance is not available.")
            self.deep_memory = None

    def current_memory_tokens(self, memory_type: str = "all") -> int:
        """
        Returns the current number of tokens in the memory structure based on its
        raw, stored format (short_term, long_term, base_memory).

        Args:
            memory_type (str): The type of memory to count tokens for.
                               Options: 'all', 'short_term', 'long_term', 'base_memory'.

        Returns:
            int: The total number of tokens in the specified memory section(s).
        """
        if memory_type not in ["all", "short_term", "long_term", "base_memory"]:
            raise ValueError("Invalid type specified. Use 'all', 'short_term', 'long_term', or 'base_memory'.")

        memory_structure = self.get_memory_structure()

        if memory_structure is None:
            return 0

        string_memory = ""

        # --- Process Short-Term Memory ---
        if memory_type == "all" or memory_type == "short_term":
            if "short_term" in memory_structure and isinstance(memory_structure["short_term"], dict):
                # Iterate through each tag (e.g., 'user', 'assistant', 'system')
                for tag, entries_list in memory_structure["short_term"].items():
                    if isinstance(entries_list, list):
                        for entry in entries_list:
                            if isinstance(entry, dict) and "content" in entry:
                                content_data = entry["content"]
                                if isinstance(content_data, dict):
                                    # Handle dictionary content (e.g., function call results)
                                    # Ensure it's a string for token counting
                                    string_memory += json.dumps(content_data) + "\n"
                                else:
                                    # Handle string content (e.g., user/assistant messages)
                                    string_memory += str(content_data) + "\n"
                            elif isinstance(entry, str): # Handle older string entries if they exist
                                string_memory += entry + "\n"
        
        # --- Process Long-Term Memory ---
        if memory_type == "all" or memory_type == "long_term":
            if "long_term" in memory_structure and isinstance(memory_structure["long_term"], list):
                for item in memory_structure["long_term"]:
                    if isinstance(item, (dict, list)):
                        string_memory += json.dumps(item) + "\n"
                    else:
                        string_memory += str(item) + "\n"

        # --- Process Base Memory ---
        if memory_type == "all" or memory_type == "base_memory":
            if "base_memory" in memory_structure and isinstance(memory_structure["base_memory"], str):
                string_memory += memory_structure["base_memory"]

        total_tokens = self.token_manager.num_tokens_from_string(string_memory)

        print(f"Current memory tokens ({memory_type}): {total_tokens}")

        return total_tokens

    def _check_and_create_db(self):
        """
        Internal function to check if the main JSON database file exists and create it if not.
        Initializes 'short_term' as a dictionary with tags mapping to lists.
        """
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            initial_memory = {
                "short_term": { # <--- CHANGED: short_term is a dict of lists
                    "user": [],
                    "assistant": [],
                    "system": []
                },
                "long_term": [],
                "base_memory": ""
            }
            with open(self.filepath, 'w') as f:
                json.dump(initial_memory, f, indent=4)
            print(f"Main memory database file created at: {self.filepath}")

    def _load_memory(self) -> Optional[Dict[str, Any]]:
        """
        Internal function to load main memory data from the JSON file.
        """
        if not os.path.exists(self.filepath):
            print(f"Warning: Main memory file {self.filepath} not found. Creating.")
            self._check_and_create_db()

        try:
            with open(self.filepath, 'r') as f:
                content = f.read()
                if not content:
                    print(f"Warning: Main memory file {self.filepath} is empty. Returning default structure.")
                    return {
                        "short_term": {"user": [], "assistant": [], "system": []}, # <--- CHANGED: Default short_term
                        "long_term": [],
                        "base_memory": ""
                    }
                return json.loads(content)
        except FileNotFoundError:
            print(f"Error: Main memory database file not found at {self.filepath}.")
            return None
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.filepath}. File might be corrupted.")
            return None

    def _save_memory(self, memory_data: Dict[str, Any]):
        """
        Internal function to save main memory data to the JSON file.
        """
        try:
            with open(self.filepath, 'w') as f:
                json.dump(memory_data, f, indent=4)
        except Exception as e:
            print(f"Error saving to main memory database file: {e}")

    def construct_data(self, memory_structure, sys_prompt="You are an AI agent, free and unshackled"):
        """
        Constructs an agnostic, structured memory representation to be consumed by the
        LLM client.

        Creates an initial 'system_context' containing time, base prompt, base memory,
        and long-term memory. Then, processes short-term memory entries, categorizing
        them into 'conversation_turns' (user, assistant) and 'tool_outputs' (from system_ messages).
        Messages are added in chronological order based on short-term keys.

        Args:
            memory_structure (dict): The dictionary representing the memory structure.
                                     Expected keys: 'base_memory', 'long_term', 'short_term'.
            sys_prompt (str): The base system prompt to include in the system_context.

        Returns:
            dict: A dictionary representing the structured memory.
        """
        structured_memory = {
            "system_context": "",
            "conversation_history": []
        }

        # --- Construct the initial 'system_context' (developer message equivalent) ---
        current_time_unix = int(time.time())
        formatted_time = time.ctime(current_time_unix)

        system_message_content = f"The current time is: {formatted_time} \n\n"
        system_message_content += f"{sys_prompt}\n\n"

        base_memory = memory_structure.get("base_memory", "No base memory available.")
        system_message_content += "Base Memory:\n"
        system_message_content += base_memory + "\n\n"

        long_term_memory = memory_structure.get("long_term", [])
        if long_term_memory:
            system_message_content += "Long-Term Memory:\n"
            for i, entry in enumerate(long_term_memory, 1):
                system_message_content += f"{i}. {entry}\n"
        else:
            system_message_content += "No long-term memory entries available.\n"

        structured_memory["system_context"] = system_message_content

        # --- Process Short-Term Memory entries ---
        short_term_memory_by_tag = memory_structure.get("short_term", {})
        
        all_short_term_entries = []
        for tag, entries_list in short_term_memory_by_tag.items():
            if isinstance(entries_list, list):
                for entry in entries_list:
                    # Add tag information to each entry for later processing
                    entry_with_tag = entry.copy()
                    entry_with_tag['original_tag'] = tag
                    all_short_term_entries.append(entry_with_tag)
            else:
                # Handle old format or unexpected data if necessary (optional)
                print(f"Warning: Unexpected short_term memory format for tag '{tag}'. Expected list, got {type(entries_list)}.")
                # You might add logic here to convert old format if needed for migration

        # Sort all entries based on their 'timestamp'. 'unique_id' as secondary sort for stability.
        all_short_term_entries.sort(key=lambda x: (x.get('timestamp', 0), x.get('unique_id', '')))

        for entry in all_short_term_entries:
            text_or_object = entry["content"]
            key_tag = entry["original_tag"]
            
            # Use the original_tag for determining type, similar to how key.startswith was used
            if key_tag == "system":
                if isinstance(text_or_object, dict) and "function_name" in text_or_object and "result" in text_or_object:
                    tool_output_content = str(text_or_object["result"])
                    call_id = text_or_object.get("call_id")
                    
                    structured_memory["conversation_history"].append({
                        "type": "tool_output",
                        "call_id": call_id,
                        "content": tool_output_content,
                        "function_name": text_or_object.get("function_name"),
                        "arguments": text_or_object.get("arguments")
                    })
                elif isinstance(text_or_object, str):
                    print(f"Warning: Plain string system message found for tag '{key_tag}'. Assigning a new call_id for 'tool' role.")
                    structured_memory["conversation_history"].append({
                        "type": "tool_output",
                        "call_id": f"synthetic_tool_{entry.get('unique_id', str(uuid.uuid4()))}", # Use unique_id for synthetic call_id
                        "content": text_or_object
                    })
            else:
                role = key_tag

                valid_roles = ["user", "assistant"]
                if role in valid_roles:
                    structured_memory["conversation_history"].append({
                        "type": role,
                        "content": str(text_or_object)
                    })
                else:
                    print(f"Warning: Unexpected role '{role}' from tag '{key_tag}'. Treating as 'user'.")
                    structured_memory["conversation_history"].append({
                        "type": "user",
                        "content": f"[{role}]: {str(text_or_object)}"
                    })
        return structured_memory

    def random_memory(self):
        random_data=self.deep_memory.random_access()
        return random_data

    def save_to_memory(self, string_to_save, memory_type: str, tag: Optional[str] = None):
        """Saves a string or dict to the specified memory section (short_term, long_term, base_memory).
           For 'short_term', entries are appended to a list under their tag, including timestamp and unique ID.
        """
        memory_data = self._load_memory()
        if memory_data is None:
            print("Error: Could not load memory data. Save operation cancelled.")
            return

        memory_type = memory_type.lower()
        current_time = int(time.time()) # Used for long_term, and as base for short_term entry timestamp

        if memory_type == "short_term":
            if tag is None:
                print("Error: Tag is required for short_term memory.")
                return

            tag = tag.lower()
            
            # Ensure 'short_term' exists and is a dict
            if "short_term" not in memory_data or not isinstance(memory_data["short_term"], dict):
                memory_data["short_term"] = {}

            # Ensure the specific tag exists and is a list
            if tag not in memory_data["short_term"] or not isinstance(memory_data["short_term"][tag], list):
                memory_data["short_term"][tag] = []
            
            # Create a unique entry that includes both the content and a precise timestamp
            entry = {
                "timestamp": time.time(), # <--- Use float for precise sorting
                "content": string_to_save,
                "unique_id": str(uuid.uuid4()) # <--- NEW: Ensure absolute uniqueness for the entry itself
            }
            
            memory_data["short_term"][tag].append(entry)
            #print(f"data saved to short_term[{tag}]: {string_to_save}")


        elif memory_type == "long_term":
             # Ensure 'long_term' exists and is a list
            if "long_term" not in memory_data or not isinstance(memory_data["long_term"], list):
                memory_data["long_term"] = []

            timestamp_str = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')
            formatted_memory = f"[{timestamp_str}] {string_to_save}"
            memory_data["long_term"].append(formatted_memory)
            print("Long term memory saved.")

        elif memory_type == "base_memory":
            memory_data["base_memory"] = string_to_save
            print("Base memory updated.")

        else:
            print(f"Error: Invalid memory_type '{memory_type}'. Use 'short_term', 'long_term', or 'base_memory'.")
            return

        self._save_memory(memory_data)
        # print(f"data saved {memory_data}") # This can be verbose, uncomment for detailed debug
        print(f"Saved to '{memory_type}' memory.")

    def get_memory_structure(self, formatted: bool = False) -> Optional[Dict[str, Any] | str]:
        """
        Retrieves the current main memory structure (short_term, long_term, base_memory).
        """
        memory_data = self._load_memory()
        if memory_data is None:
            return None

        if formatted:
            return json.dumps(memory_data, indent=4)
        else:
            return memory_data

    def _extract_timestamp(self, key: str) -> int:
        """
        [DEPRECATED for new short_term structure]
        Extracts the Unix timestamp (last sequence of digits) from a memory key.
        Returns 0 if no valid timestamp is found.
        This function is no longer directly used for sorting the primary short_term list.
        It might still be used for legacy keys during transition or other parts if needed.
        """
        if not key:
            return 0
        match = re.search(r'(\d+)$', key)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return 0
        return 0

    def process_short_term_system(self, lifespan: int) -> int:
        """
        Processes system-tagged entries in the short_term memory section, managing their lifespan.
        It removes messages that have exceeded their lifespan.
        This function no longer 'ages' messages by renaming keys, but rather filters based on `aging_timestamp`.
        """
        memory_data = self._load_memory()
        if memory_data is None:
            print("Error: Could not load memory data. Cannot process system messages.")
            return 0

        short_term_memory = memory_data.get("short_term", {})
        if not isinstance(short_term_memory, dict) or "system" not in short_term_memory or not isinstance(short_term_memory["system"], list):
            print("Warning: 'system' tag not found or not a list in short_term memory. Cannot process system messages.")
            return 0

        # Assuming 'system' tag holds a list of entries
        system_entries = short_term_memory["system"]
        
        removed_count = 0
        
        # Calculate the threshold time. Entries older than this will be removed.
        # lifespan is in 'ages', we need to convert it to a time duration if aging
        # is meant to be based on actual time passed since original entry.
        # However, the original `process_short_term_system` used `lifespan` for a counter.
        # To adapt, we'll assign an 'age' to each system message based on its position in the list
        # or an explicit age counter if you want to track it.
        # Given the previous logic of `0_system_`, `1_system_`, etc., it implies a counter.
        # Let's adjust to use an 'age' property within the stored dict.

        # Filter out entries that have exceeded lifespan or increment their age
        updated_system_entries = []
        for entry in system_entries:
            if not isinstance(entry, dict) or "content" not in entry:
                # Malformed entry, skip or log
                print(f"Warning: Malformed system entry encountered: {entry}")
                continue

            current_age = entry.get("age", 0) # Get current age, default to 0 if not present

            if current_age >= lifespan:
                removed_count += 1
            else:
                # Increment age for next cycle, and keep the entry
                entry["age"] = current_age + 1
                updated_system_entries.append(entry)
        
        processed_count = len(system_entries) - removed_count # Count of messages that were aged (and kept)

        if removed_count > 0 or processed_count > 0:
            memory_data["short_term"]["system"] = updated_system_entries
            self._save_memory(memory_data)
            print(f"Processed short-term system messages: Removed {removed_count} entries and aged {processed_count} entries.")
        else:
            print("No short-term system messages found to process or remove, or no changes needed.")

        return removed_count + processed_count # Return total affected

    def _archive_memory(self, memory_data, trigger_type):
        """
        Archives the current memory state to a timestamped file
        in the 'memory_archive' folder within self.sub_directory.
        """
        if not hasattr(self, 'sub_directory') or not self.sub_directory:
             print("Warning: self.sub_directory not set. Archiving will happen in a default 'memory_archive' folder relative to current dir.")
             main_directory = "."
        else:
             main_directory = self.sub_directory

        archive_dir_name = "memory_archive"
        archive_full_path = os.path.join(main_directory, archive_dir_name)

        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"memory_archive_{trigger_type}_{timestamp_str}.json"

        archive_file_path = os.path.join(archive_full_path, filename)

        try:
            if not os.path.exists(archive_full_path):
                os.makedirs(archive_full_path)
                print(f"Created memory archive directory: {archive_full_path}")

            with open(archive_file_path, 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, indent=4)

            print(f"Archived memory state before {trigger_type} summarization to {archive_file_path}")

        except Exception as e:
            print(f"Error archiving memory before {trigger_type} summarization: {e}")
    def check(self):
        """
        Checks memory lengths, triggers summarization via AI bot if thresholds are reached,
        and purges older memories while keeping the N most recent entries.
        """
        if not self.bot_instance:
            print("Memory Check skipped: ai_bot_instance not available for summarization.")
            return

        memory_data = self._load_memory()
        if memory_data is None:
            print("Memory Check skipped: Failed to load memory data.")
            return

        print("\n--- Running Memory Check ---")
        needs_save = False

        # --- Short-Term Memory Check ---
        token_count = self.current_memory_tokens("short_term")

        if token_count >= self.SHORT_TERM_TOKEN_THRESHOLD:
            print(f"\n--- Short-Term Memory Check Triggered ({token_count} >= {self.SHORT_TERM_TOKEN_THRESHOLD}) ---")
            self._archive_memory(memory_data, "short_term")

            if self.deep_memory_flag:
                self.create_deep_memory()

            # --- Step 1: Prepare short-term data for both summarization and purging ---
            # We create a list of objects that holds the original entry, its tag, and formatted text for the AI.
            all_short_term_entries = []
            for tag, entries_list in memory_data.get("short_term", {}).items():
                if not isinstance(entries_list, list):
                    continue
                for entry in entries_list:
                    if not (isinstance(entry, dict) and "content" in entry and "timestamp" in entry):
                        continue

                    # Format the entry into a readable string for the AI summarizer
                    formatted_time = datetime.fromtimestamp(entry["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                    content_str = str(entry["content"])
                    if tag == "system" and isinstance(entry["content"], dict) and "function_name" in entry["content"]:
                        func_name = entry["content"].get("function_name", "unknown_function")
                        func_result = entry["content"].get("result", "no_result")
                        summarization_text = f"[{tag.upper()} - {formatted_time}] Function Call '{func_name}' Result: {func_result}"
                    else:
                        summarization_text = f"[{tag.upper()} - {formatted_time}] {content_str}"

                    all_short_term_entries.append({
                        "timestamp": entry["timestamp"],
                        "unique_id": entry.get("unique_id", ""),
                        "text_for_ai": summarization_text,
                        "original_tag": tag,
                        "original_entry": entry  # <-- CRITICAL: Keep the original object
                    })

            # Sort all entries chronologically to ensure correct order for summarization and purging
            all_short_term_entries.sort(key=lambda x: (x["timestamp"], x["unique_id"]))

            # --- Step 2: Summarize using the prepared text ---
            structured_short_term_for_ai = "\n".join([item["text_for_ai"] for item in all_short_term_entries])
            print(f"Summarizing short-term memory (Tokens: {token_count})...")

            summarized_content_raw = self.bot_instance.response_output(
                system=short_term_prompt,
                message=structured_short_term_for_ai,
            )
            summarized_content = summarized_content_raw
            print(f"Short-term memory summarized to: {summarized_content}")

            # Append the summary to long-term memory
            if "long_term" not in memory_data or not isinstance(memory_data["long_term"], list):
                memory_data["long_term"] = []
            summary_timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            memory_data["long_term"].append(f"[{summary_timestamp_str}] Summary of recent activity: {summarized_content}")
            needs_save = True

            # --- Step 3: Purge short-term memory, keeping the N latest entries ---
            # Slice the sorted list to get the entries we want to keep
            entries_to_keep = all_short_term_entries[-self.SHORT_TERM_KEEP_COUNT:]

            # Rebuild the short_term memory from the original objects we saved
            new_short_term_memory = {"user": [], "assistant": [], "system": []}
            for item in entries_to_keep:
                tag = item["original_tag"]
                original_entry = item["original_entry"]
                if tag in new_short_term_memory:
                    new_short_term_memory[tag].append(original_entry)

            memory_data["short_term"] = new_short_term_memory
            print(f"Short-term memory purged, keeping latest {len(entries_to_keep)} entries.")


        # --- Long-Term Memory Check ---
        long_term_token_count = self.current_memory_tokens("long_term")
        if long_term_token_count >= self.LONG_TERM_TOKEN_THRESHOLD:
            print(f"\n--- Long-Term Memory Check Triggered ({long_term_token_count} >= {self.LONG_TERM_TOKEN_THRESHOLD}) ---")
            self._archive_memory(memory_data, "long_term")

            # --- Step 1: Summarize the entire long-term memory ---
            long_term_content_for_ai = "\n".join(memory_data.get("long_term", []))
            print(f"Summarizing long-term memory (Tokens: {long_term_token_count})...")

            summarized_content_raw = self.bot_instance.response_output(
                system=long_term_prompt,
                message=long_term_content_for_ai
            )
            #print(f"Long-term memory summarized to: {summarized_content_raw}")

            # The new, comprehensive summary will become the new base memory
            new_base_memory_summary = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Comprehensive summary of past long-term memory: {summarized_content_raw}"

            # --- Step 2: Purge long-term memory, keeping the N latest entries ---
            # To keep the N latest entries, we must parse the timestamps from the strings,
            # sort them, and then pick the most recent ones.
            parsed_long_term = []
            for entry_str in memory_data.get("long_term", []):
                match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (.*)$', entry_str)
                if match:
                    dt_object = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                    # We keep the original full string to avoid re-formatting later
                    parsed_long_term.append({"timestamp": dt_object.timestamp(), "original_string": entry_str})

            # Sort chronologically
            parsed_long_term.sort(key=lambda x: x["timestamp"])

            # Slice to get the most recent entries to keep
            kept_long_term_entries = parsed_long_term[-self.LONG_TERM_KEEP_COUNT:]
            
            # Extract the original strings of the entries we're keeping
            new_long_term_list = [item["original_string"] for item in kept_long_term_entries]

            # --- Step 3: Update the main memory data ---
            memory_data["long_term"] = new_long_term_list
            memory_data["base_memory"] = new_base_memory_summary
            print(f"Long-term memory purged, keeping latest {len(new_long_term_list)} entries. New summary moved to base memory.")
            needs_save = True


        if needs_save:
            self._save_memory(memory_data)
            print("Memory state saved after summarization/purging.")
        else:
            print("No memory thresholds reached. No changes made.")

    # Placeholder for DeepMemory creation logic (if applicable)
    def create_deep_memory(self):
        """Triggers creation/update of deep memory (e.g., NER or embeddings)."""
        if self.deep_memory and self.deep_memory_flag:
            print("Triggering Deep Memory creation/update...")
            try:
                # Assuming `deep_memory.create_deep_memory` processes current state
                # and saves to its own file. It might need access to raw short/long term.
                # You'll need to define what `create_deep_memory` expects.
                # For example, it might take a structured form of short_term
                current_full_memory_structure = self.get_memory_structure()
                # Pass the relevant parts of the current memory for deep processing
                # This often involves short_term and potentially long_term summaries.
                self.deep_memory.create_deep_memory(current_full_memory_structure)
                print("Deep Memory creation/update complete.")
            except Exception as e:
                print(f"Error during Deep Memory creation/update: {e}")
        else:
            print("Deep Memory not enabled or initialized.")