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
from typing import Optional, Dict, Any, List # Import typing helpers
import re
from collections import OrderedDict

# Import extra memory module
from memory.deep_memory import DeepMemory # <--- Import DeepMemory here

from utils.tokens_handle import token_manager

from memory.memory_configs import (short_term_prompt, long_term_prompt)

# from memory.memory_providers.openai_memory_ai_provider import OpenAIMemoryAI
# from memory.memory_providers.gemini_memory_ai_provider import GeminiMemoryAI

from utils.utils_ai_providers.gemini_provider import GeminiProv
from utils.utils_ai_providers.openai_provider import OpenAIProv

import configparser

config = configparser.ConfigParser()
config.read('main_config.ini')
system_prompt = config['AI']['sys_prompt']
selected_model= config['AI']['memory_model']
config_selected_provider = config['AI']['memory_ai_provider']


# available_providers = {
#     "gemini": {
#         "client":GeminiMemoryAI},
#     "openai": {
#         "client":OpenAIMemoryAI}
# }


available_providers = {
    "gemini": {
        "client":GeminiProv},
    "openai": {
        "client":OpenAIProv}
}


# 4. Use the mapping dictionary to get the actual JSON structure
if config_selected_provider in available_providers:
    config_client = available_providers[config_selected_provider]["client"]
    print(f"Loaded state: {config_selected_provider}")
    print(config_client)

else:
    print(f"Error: '{config_selected_provider}' is not a recognized state.")
    # Handle the error, perhaps by falling back to a default state




# Define default filepaths
DEFAULT_MEMORY_DB = "memory_database.json"
DEFAULT_DEEP_MEMORY_DB = "deep_memory_database.json"

class memory_manager:

    # These numbers need to be adjusted to find an optimal spot, lower seems to be better for coherence during conversation and summarization.

    # These now are replaced with token thresholds, but kept for reference.
    # SHORT_TERM_THRESHOLD = 20  # Number of short-term entries before summarizing
    # LONG_TERM_THRESHOLD = 10   # Number of long-term entries before summarizing


    SHORT_TERM_KEEP_COUNT = 10  # Number of latest short-term entries to keep after summarizing
    LONG_TERM_KEEP_COUNT = 5   # Number of latest long-term entries to keep after summarizing


#. Deciding on token thresholds for summarization will have to be done with some testing, these are just initial values.

    # SHORT_TERM_TOKEN_THRESHOLD = 30000  # Token threshold for short-term memory before summarizing
    # LONG_TERM_TOKEN_THRESHOLD = 25000   # Token threshold for long-term memory before summarizing

    # Selected:
    SHORT_TERM_TOKEN_THRESHOLD = 12000  # Token threshold for short-term memory before summarizing
    LONG_TERM_TOKEN_THRESHOLD = 12000  # Token threshold for long-term memory before summarizing


    # SHORT_TERM_TOKEN_THRESHOLD = 300  # Token threshold for short-term memory before summarizing
    # LONG_TERM_TOKEN_THRESHOLD = 300  # Token threshold for long-term memory before summarizing


    def __init__(self, filepath: str = DEFAULT_MEMORY_DB, deep_memory_filepath: str = DEFAULT_DEEP_MEMORY_DB, deep_memory: bool = False, text_capture=None, sub_directory=None):
        """
        Initializes the memory manager.

        Args:
            ai_bot_instance: An optional instance of the AI bot. If None, created internally.
            filepath (str): Path to the main JSON database file for short/long/base memory.
            deep_memory_filepath (str): Path to the JSON database file for deep memory (NER).
        """
        self.token_manager = token_manager()
        self.text_capture=text_capture
        self.filepath = filepath
        self.deep_memory_filepath = deep_memory_filepath
        self._check_and_create_db() # Check/create main memory file
        self.deep_memory_flag= deep_memory # Store deep memory flag
        self.sub_directory=sub_directory

        # Use provided bot instance or create a new one if needed

        self.bot_instance = config_client(selected_model)

        # Initialize DeepMemory - AFTER bot_instance is set
        if self.bot_instance and self.deep_memory_flag:
            try:
                self.deep_memory = DeepMemory(
                    filepath=self.deep_memory_filepath,
                    ai_bot_instance=self.bot_instance,
                    memory_instance=self # Pass this memory_manager instance
                )
                #print(f"DeepMemory initialized with file: {self.deep_memory_filepath}")
            except Exception as e:
                print(f"Error initializing DeepMemory: {e}")
                self.deep_memory = None
        else:
            print("DeepMemory not initialized because ai_bot_instance is not available.")
            self.deep_memory = None # Ensure deep_memory attribute exists

                


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

        if memory_structure is None: # Check for None from get_memory_structure
            return 0

        string_memory = ""

        # --- Process Short-Term Memory ---
        if memory_type == "all" or memory_type == "short_term":
            if "short_term" in memory_structure and isinstance(memory_structure["short_term"], dict):
                # We need to sort keys to ensure consistent token counting if order matters
                # (though for pure token count, order of concatenation doesn't change total)
                # Sorting also ensures consistent output for string_memory for debugging.
                sorted_short_term_keys = sorted(memory_structure["short_term"].keys(), key=lambda k: int(k.split('_')[-1]))

                for key in sorted_short_term_keys:
                    value = memory_structure["short_term"][key]
                    if isinstance(value, dict):
                        # If the value is a dictionary (like your 0_system_ messages)
                        # We need to serialize it to a string for token counting.
                        # For system messages acting as tool outputs, we concatenate key info and result.
                        if "function_name" in value and "result" in value:
                            string_memory += f"{key}: function_name='{value['function_name']}', arguments={json.dumps(value['arguments'])}, result='{value['result']}'\n"
                        else:
                            # Fallback for any other dictionary structure in short_term
                            string_memory += f"{key}: {json.dumps(value)}\n"
                    else:
                        # For string values (user, assistant)
                        string_memory += f"{key}: {value}\n"

        # --- Process Long-Term Memory ---
        if memory_type == "all" or memory_type == "long_term":
            if "long_term" in memory_structure and isinstance(memory_structure["long_term"], list):
                for item in memory_structure["long_term"]:
                    # Assuming long_term items might be dicts, lists or strings.
                    # Convert to string representation.
                    if isinstance(item, (dict, list)):
                        string_memory += json.dumps(item) + "\n"
                    else:
                        string_memory += str(item) + "\n"

        # --- Process Base Memory ---
        if memory_type == "all" or memory_type == "base_memory":
            if "base_memory" in memory_structure and isinstance(memory_structure["base_memory"], str):
                string_memory += memory_structure["base_memory"]

        # Counts the tokens of the aggregated string
        total_tokens = self.token_manager.num_tokens_from_string(string_memory)

        print(f"Current memory tokens ({memory_type}): {total_tokens}")

        return total_tokens

    # def current_memory_tokens(self)-> int:
    #     memory_structure=self.get_memory_structure()
    #     print(f"Memory structure: {memory_structure}")
    #     constructed_data=self.construct_data(memory_structure, system_prompt)
    #     def extract_content_to_string(messages):
    #         """
    #         Extracts the content from a list of message dictionaries into a single string.

    #         Args:
    #             messages: A list of dictionaries, where each dictionary is expected
    #                     to have a 'content' key.

    #         Returns:
    #             A single string containing all the 'content' values concatenated,
    #             separated by newlines.
    #         """
    #         all_content = []
    #         for message in messages:
    #             # Check if the 'content' key exists in the dictionary
    #             if 'content' in message:
    #                 all_content.append(message['content'])
    #             # Optional: Handle cases where 'content' key is missing
    #             else:
    #                 print(f"Warning: Message dictionary missing 'content' key: {message}")

    #         # Join all the collected content strings with a newline separator
    #         return "\n".join(all_content)
    #     string_memory=extract_content_to_string(constructed_data)
    #     #print(f"Extracted memories: {string_memory}")
    #     return self.token_manager.num_tokens_from_string(string_memory)


    def _check_and_create_db(self):
        """
        Internal function to check if the main JSON database file exists and create it if not.
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            initial_memory = {
                "short_term": {},
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
            self._check_and_create_db() # Create if missing

        try:
            with open(self.filepath, 'r') as f:
                content = f.read()
                if not content:
                    print(f"Warning: Main memory file {self.filepath} is empty. Returning default structure.")
                    return {"short_term": {}, "long_term": [], "base_memory": ""}
                return json.loads(content)
        except FileNotFoundError:
            print(f"Error: Main memory database file not found at {self.filepath}.")
            return None
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.filepath}. File might be corrupted.")
            return None # Indicate error

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
                  Example:
                  {
                      "system_context": "...",
                      "conversation_history": [
                          {"type": "user", "content": "hello there! can you please move to the garden"},
                          {"type": "tool_output", "call_id": "tool_call_1751576848", "content": "Available rooms: living_room (ID:000001), kitchen (ID:000002), bathroom (ID:000003), bedroom (ID:000000), computer_room (ID:000004), garden (ID:000005), white_room (ID:000006), lab_room (ID:000007)"},
                          {"type": "assistant", "content": "Error communicating with OpenAI: Error code: 400 - {'error': {'message': \"Invalid type for 'input[2].content': expected one of an array of objects or string, but got an object instead.\", 'type': 'invalid_request_error', 'param': 'input[2].content', 'code': 'invalid_type'}}"}
                      ]
                  }
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
        short_term_memory = memory_structure.get("short_term", {})

        # Sort keys to maintain chronological order for conversation turns
        sorted_short_term_keys = sorted(short_term_memory.keys(), key=lambda k: int(k.split('_')[-1]))

        for key in sorted_short_term_keys:
            text_or_object = short_term_memory[key]

            # Check if the key is a system variant (now specifically for tool outputs)
            if key.startswith("0_system_") or key.startswith("system_"):
                if isinstance(text_or_object, dict) and "function_name" in text_or_object and "result" in text_or_object:
                    # This is a tool output message from a previous function call
                    tool_output_content = str(text_or_object["result"])

                    
                    structured_memory["conversation_history"].append({
                        "type": "tool_output",
                        "call_id": text_or_object["call_id"],
                        "content": tool_output_content,
                        "function_name":text_or_object["function_name"],
                        "arguments":text_or_object["arguments"]
                        
                    })
                elif isinstance(text_or_object, str):
                    # Per your instruction, plain string system messages also become tool messages.
                    # We generate a unique call_id for them.
                    print(f"Warning: Plain string system message found for key '{key}'. Assigning a new call_id for 'tool' role.")
                    structured_memory["conversation_history"].append({
                        "type": "tool_output", # Treated as a generic tool output for a system message
                        "call_id": f"", # Unique ID for this synthetic tool message
                        "content": text_or_object
                    })
            else:
                # Process non-system keys (user, assistant, etc.)
                parts = key.rsplit('_', 1)
                role = "unknown"
                if len(parts) > 1:
                    role_with_potential_prefix = parts[0]
                    if '_' in role_with_potential_prefix:
                        role = role_with_potential_prefix.split('_', 1)[1] 
                    else:
                        role = role_with_potential_prefix
                else:
                    role = parts[0]

                valid_roles = ["user", "assistant"]
                if role in valid_roles:
                    structured_memory["conversation_history"].append({
                        "type": role,
                        "content": str(text_or_object)
                    })
                else:
                    print(f"Warning: Unexpected role '{role}' extracted from key '{key}'. Treating as 'user'.")
                    structured_memory["conversation_history"].append({
                        "type": "user",
                        "content": f"[{role} - {key}]: {str(text_or_object)}"
                    })
        return structured_memory


    def random_memory(self):
        random_data=self.deep_memory.random_access()
        return random_data

    def save_to_memory(self, string_to_save, memory_type: str, tag: Optional[str] = None):
        """Saves a string to the specified memory section (short_term, long_term, base_memory).

        Args:
            string_to_save (str): The content to save.
            memory_type (str): 'short_term', 'long_term', or 'base_memory'.
            tag (Optional[str]): Required only for 'short_term' (e.g., 'user', 'assistant').
        """
        memory_data = self._load_memory()
        if memory_data is None:
            print("Error: Could not load memory data. Save operation cancelled.")
            return # Stop if loading failed

        memory_type = memory_type.lower()
        current_time = int(time.time()) # Keep as timestamp for sorting keys

        if memory_type == "short_term":
            if tag is None:
                print("Error: Tag is required for short_term memory.")
                return

            tag = tag.lower()
            # Store raw string, formatting can happen on retrieval if needed
            # Or keep formatting here if it's always desired
            formatted_time = time.ctime(current_time) # Human-readable for storage
            saved_content = string_to_save

            # Ensure 'short_term' exists and is a dict
            if "short_term" not in memory_data or not isinstance(memory_data["short_term"], dict):
                memory_data["short_term"] = {}

            # Create a unique key using the tag and timestamp
            key = f"{tag}_{current_time}" # Timestamp ensures chronological order when sorted
            
            memory_data["short_term"][key] = saved_content
            print(f"data saved {saved_content}")


        elif memory_type == "long_term":
             # Ensure 'long_term' exists and is a list
            if "long_term" not in memory_data or not isinstance(memory_data["long_term"], list):
                memory_data["long_term"] = []

            # Format the timestamp as a human-readable date/time
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
        print(f"data saved {memory_data}")
        # Consider more specific logging later if needed
        print(f"Saved to '{memory_type}' memory.")

    def get_memory_structure(self, formatted: bool = False) -> Optional[Dict[str, Any] | str]:
        """
        Retrieves the current main memory structure (short_term, long_term, base_memory).

        Args:
            formatted (bool): If True, returns a formatted JSON string.
                              If False (default), returns the raw dictionary.

        Returns:
            Optional[Dict[str, Any] | str]: The memory structure, or None if loading fails.
        """
        memory_data = self._load_memory()
        if memory_data is None:
            return None # Propagate loading error

        if formatted:
            return json.dumps(memory_data, indent=4)
        else:
            return memory_data

    def _extract_timestamp(self, key: str) -> int:
        """
        Extracts the Unix timestamp (last sequence of digits) from a memory key.
        Returns 0 if no valid timestamp is found.
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
        Ensures the memory remains chronologically ordered by timestamp after processing.

        System messages are aged by incrementing a counter in their key prefix.
        Messages reaching or exceeding their 'lifespan' are removed.
        New 'system_' messages are initialized with an age of 0.

        Args:
            lifespan (int): The maximum age a system message can reach before being removed.
                            A message with a prefix of `lifespan_system_` will be removed
                            in the current processing cycle.

        Returns:
            int: The total number of entries that were removed or processed (aged).
        """
        memory_data = self._load_memory()
        if memory_data is None:
            print("Error: Could not load memory data. Cannot process system messages.")
            return 0

        short_term_memory = memory_data.get("short_term", {})
        if not isinstance(short_term_memory, dict):
            print("Warning: short_term memory structure is not a dictionary. Cannot process system messages.")
            return 0

        removed_count = 0
        processed_count = 0 # Count of messages that were aged/renamed
        
        keys_to_remove = []
        keys_to_age = {} # Maps old_key -> new_key for aging

        # --- Step 1: Identify messages to remove and messages to age/rename ---
        # Iterate over a copy of keys as we'll be modifying the conceptual state
        for key in list(short_term_memory.keys()):
            if key.startswith("system_"):
                # New system message, will be initialized with age 0
                # Example: "system_175..." -> "0_system_175..."
                keys_to_age[key] = f"0_{key}"
                processed_count += 1 # This counts as processing (initial aging)
            elif "_system_" in key:
                parts = key.split("_system_", 1)
                try:
                    current_age = int(parts[0])
                    original_suffix = "system_" + parts[1] # Reconstruct original "system_foo" part
                    
                    if current_age >= lifespan:
                        # Message has reached or exceeded its lifespan, mark for removal
                        keys_to_remove.append(key)
                        removed_count += 1
                    else:
                        # Message needs to be aged
                        new_age = current_age + 1
                        keys_to_age[key] = f"{new_age}_{original_suffix}"
                        processed_count += 1 # This counts as processing (aging)
                except ValueError:
                    # Not an aged system message, or malformed, ignore for this process
                    pass
        
        # --- Step 2: Prepare entries for a chronological rebuild ---
        # This list will hold (timestamp, key, value) tuples for all *retained* entries,
        # using their final keys after aging.
        entries_for_rebuild = []

        for original_key, value in short_term_memory.items():
            if original_key in keys_to_remove:
                # This entry is marked for removal, so skip adding it to the rebuild list
                continue
            
            final_key = original_key
            if original_key in keys_to_age:
                # This entry is being aged/renamed, use its new key
                final_key = keys_to_age[original_key]
            
            # Extract timestamp from the FINAL key
            timestamp = self._extract_timestamp(final_key)
            entries_for_rebuild.append((timestamp, final_key, value))

        # --- Step 3: Sort entries chronologically by timestamp ---
        # This is the crucial step to ensure correct ordering.
        entries_for_rebuild.sort(key=lambda x: x[0]) # Sort by the timestamp element (index 0 of the tuple)

        # --- Step 4: Rebuild the short_term_memory dictionary in sorted order ---
        # Using OrderedDict explicitly states the intent to preserve insertion order,
        # which will now be chronological. (Python 3.7+ dicts also preserve order).
        new_short_term_memory = OrderedDict() 
        for timestamp, key, value in entries_for_rebuild:
            new_short_term_memory[key] = value
        
        total_affected = removed_count + processed_count

        if total_affected > 0:
            memory_data["short_term"] = new_short_term_memory
            self._save_memory(memory_data)
            print(f"Processed short-term system messages: Removed {removed_count} entries and aged {processed_count} entries. Rebuilt memory chronologically.")
        else:
            print("No short-term system messages found to process or remove, or no changes needed.")
            # If nothing was removed or aged, the memory is already in its correct state,
            # so no need to save changes.

        return total_affected

    def _archive_memory(self, memory_data, trigger_type):
        """
        Archives the current memory state to a timestamped file
        in the 'memory_archive' folder within self.sub_directory.
        """
        # Use self.sub_directory as the base path
        # Add a check in case self.sub_directory is not set for some reason
        if not hasattr(self, 'sub_directory') or not self.sub_directory:
             print("Warning: self.sub_directory not set. Archiving will happen in a default 'memory_archive' folder relative to current dir.")
             main_directory = "." # Use current directory as fallback
        else:
             main_directory = self.sub_directory

        archive_dir_name = "memory_archive" # Just the name of the archive folder
        # The full path to the directory where archives will be stored
        archive_full_path = os.path.join(main_directory, archive_dir_name)

        # Use a sortable timestamp format
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"memory_archive_{trigger_type}_{timestamp_str}.json"

        # The full path including the directory and filename
        archive_file_path = os.path.join(archive_full_path, filename)

        try:
            # Create the archive directory if it doesn't exist
            # Use the FULL PATH for exists and makedirs
            if not os.path.exists(archive_full_path):
                # os.makedirs creates intermediate directories if needed
                os.makedirs(archive_full_path)
                print(f"Created memory archive directory: {archive_full_path}")

            # Save the memory data to the full file path
            with open(archive_file_path, 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, indent=4) # Use indent for readability

            print(f"Archived memory state before {trigger_type} summarization to {archive_file_path}")

        except Exception as e:
            print(f"Error archiving memory before {trigger_type} summarization: {e}")


    # --- The `check` function to be updated ---
    def check(self):
        """
        Checks memory lengths, triggers summarization via AI bot if thresholds are reached,
        and purges older memories. Requires ai_bot_instance to be available.
        """
        if not self.bot_instance:
            print("Memory Check skipped: ai_bot_instance not available for summarization.")
            return

        memory_data = self._load_memory()
        if memory_data is None:
            print("Memory Check skipped: Failed to load memory data.")
            return

        print("\n--- Running Memory Check ---")
        needs_save = False # Flag to save only once at the end if changes were made

        # --- Short-Term Memory Check ---
        short_term_memory = memory_data.get("short_term", {})

        token_count = self.current_memory_tokens("short_term")

        # Use token_count for the threshold check
        if token_count >= self.SHORT_TERM_TOKEN_THRESHOLD:
            print(f"\n--- Short-Term Memory Check Triggered ({token_count} >= {self.SHORT_TERM_TOKEN_THRESHOLD}) ---")

            # Archive the memory *before* summarization/purging for historical record
            self._archive_memory(self._load_memory(), "short_term") # Pass the original, loaded state

            if self.deep_memory_flag:
                self.create_deep_memory()

            # Prepare string for summarization from short_term_memory
            structured_short_term = ""
            if isinstance(short_term_memory, dict):
                try:
                    # Sort keys chronologically using the timestamp part
                    # Ensure keys have the expected format before sorting
                    valid_keys = [k for k in short_term_memory.keys() if '_' in k and k.split('_')[-1].isdigit()]
                    sorted_short_term_keys = sorted(valid_keys, key=lambda k: int(k.split('_')[-1]))
                except ValueError as e:
                    print(f"Error sorting short-term keys (check key format 'tag_timestamp'): {e}")
                    sorted_short_term_keys = list(short_term_memory.keys()) # Fallback to unsorted

                for key in sorted_short_term_keys:
                    value = short_term_memory[key]
                    # This is the crucial part: handling the new dictionary format
                    if isinstance(value, dict):
                        # For system messages that are function results
                        if "function_name" in value and "result" in value:
                            # Format for AI summarization: include relevant details
                            structured_short_term += f"[{key.split('_')[0].capitalize()} - Function Call: {value['function_name']}]: Result: {value['result']}\n"
                        else:
                            # For any other dict, just dump it
                            structured_short_term += f"[{key.split('_')[0].capitalize()}]: {json.dumps(value)}\n"
                    else:
                        # For string values (user, assistant, simple system messages if any)
                        parts = key.rsplit('_', 1)
                        tag = parts[0].capitalize() if parts else "Unknown"
                        structured_short_term += f"[{tag}]: {value}\n"

            if structured_short_term:
                print("DEBUG: Calling AI to summarize short-term memory...")
                try:
                    summary_short_term = self.bot_instance.response_output(system=short_term_prompt, message=structured_short_term)
                    if summary_short_term:
                        print(f"DEBUG: Short-term summary created: {summary_short_term[:100]}...")
                        # Add summary to long-term memory
                        if "long_term" not in memory_data or not isinstance(memory_data["long_term"], list):
                            memory_data["long_term"] = []
                        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        memory_data["long_term"].append(f"[{timestamp_str}] [Summary of recent conversation]: {summary_short_term}")
                        print("DEBUG: Summary added to long-term memory queue.")
                        needs_save = True

                        # Purge oldest short-term memories
                        if len(sorted_short_term_keys) > self.SHORT_TERM_KEEP_COUNT:
                            keys_to_keep = sorted_short_term_keys[-self.SHORT_TERM_KEEP_COUNT:]
                            memory_data["short_term"] = {key: short_term_memory[key] for key in keys_to_keep}
                            print(f"Short-term memory purged, keeping latest {self.SHORT_TERM_KEEP_COUNT} entries.")
                        else:
                            print("Short-term memory below purge threshold after summarization.")
                    else:
                        print("Warning: AI returned an empty short-term summary.")
                except Exception as e:
                    print(f"Error during short-term summarization: {e}")
            else:
                print("DEBUG: No structured short-term memory to summarize.")

        # --- Long-Term Memory Check ---
        token_count = self.current_memory_tokens("long_term") # Use the helper for token count
        long_term_memory = memory_data.get("long_term", [])

        # Use token_count for the threshold check
        if token_count >= self.LONG_TERM_TOKEN_THRESHOLD:
            print(f"\n--- Long-Term Memory Check Triggered ({token_count} >= {self.LONG_TERM_TOKEN_THRESHOLD}) ---")

            # Archive the memory *before* summarization/purging for historical record
            self._archive_memory(self._load_memory(), "long_term") # Pass the original, loaded state

            structured_long_term = ""
            for i, entry in enumerate(long_term_memory):
                entry_text = entry.get("memory") if isinstance(entry, dict) else str(entry)
                structured_long_term += f"[Entry {i+1}]: {entry_text}\n"

            base_memory_content = memory_data.get("base_memory", "")
            if not isinstance(base_memory_content, str):
                 base_memory_content = str(base_memory_content)

            structured_for_ai = f"Current Base Memory:\n{base_memory_content}\n\nRecent Long-Term Memories to Summarize and Integrate:\n{structured_long_term}"

            if structured_long_term:
                print("DEBUG: Calling AI to summarize long-term memory into base memory...")
                try:
                    summary_long_term_base = self.bot_instance.response_output(system=long_term_prompt, message=structured_for_ai)
                    if summary_long_term_base:
                        print(f"DEBUG: Base memory summary created: {summary_long_term_base[:100]}...")
                        memory_data["base_memory"] = summary_long_term_base
                        print("DEBUG: Base memory updated with summary.")
                        needs_save = True

                        if len(long_term_memory) > self.LONG_TERM_KEEP_COUNT:
                            memory_data["long_term"] = long_term_memory[-self.LONG_TERM_KEEP_COUNT:]
                            print(f"Long-term memory purged, keeping latest {self.LONG_TERM_KEEP_COUNT} entries.")
                        else:
                             print("Long-term memory below purge threshold after summarization.")
                    else:
                        print("Warning: AI returned an empty long-term/base summary.")
                except Exception as e:
                    print(f"Error during long-term/base summarization: {e}")
            else:
                print("DEBUG: No structured long-term memory to summarize.")

        # Save memory if any changes occurred
        if needs_save:
            print("\nSaving updated memory state...")
            self._save_memory(memory_data)
        else:
            print("\nNo changes requiring memory save.")

        print("--- Memory Check Completed ---")


    # --- Deep Memory Integration Methods ---

    def create_deep_memory(self):
        """
        Triggers the creation and update process for the deep memory (NER extraction).
        Requires DeepMemory to be initialized.
        """
        if self.deep_memory:
            print("\n--- Triggering Deep Memory Creation/Update ---")
            try:
                self.deep_memory.create_memory()
            except Exception as e:
                 print(f"Error during deep memory creation: {e}")
        else:
            print("Deep Memory Creation skipped: DeepMemory system not initialized.")

    def search_deep_memory(self) -> List[str]:
        """
        Triggers a search in the deep memory based on the current main memory state.
        Requires DeepMemory to be initialized.

        Returns:
            List[str]: A list of relevant excerpts found in deep memory, or empty list.
        """
        if self.deep_memory and self.deep_memory_flag:
            print("\n--- Triggering Deep Memory Search ---")
            try:
                return self.deep_memory.search_memory_excerpts()
            except Exception as e:
                 print(f"Error during deep memory search: {e}")
                 return [] # Return empty list on error
        else:
            print("Deep Memory Search skipped: DeepMemory system not initialized.")
            return [] # Return empty list


# --- Example Usage ---
if __name__ == "__main__":

    # --- Setup ---
    # Define unique filepaths for this test run to avoid conflicts
    test_main_mem_file = "test_main_memory.json"
    test_deep_mem_file = "test_deep_memory.json"

    # Clean up previous test files if they exist
    if os.path.exists(test_main_mem_file): os.remove(test_main_mem_file)
    if os.path.exists(test_deep_mem_file): os.remove(test_deep_mem_file)

    print(f"--- Initializing Memory Manager ---")
    # Assumes ai_handle.py and pydantic_models.py exist and are functional
    # If ai_handle.py needs setup (like API keys), ensure that's handled.
    try:
        memory_system = memory_manager(
            filepath=test_main_mem_file,
            deep_memory_filepath=test_deep_mem_file
        )
    except ImportError as e:
         print(f"FATAL: Could not import dependencies ({e}). Exiting example.")
         exit()
    except Exception as e:
        print(f"FATAL: Could not initialize memory_manager ({e}). Exiting example.")
        exit()


    # --- Basic Memory Operations ---
    print("\n--- Populating Short-Term Memory ---")
    memory_system.save_to_memory("User said hello.", "short_term", "user")
    memory_system.save_to_memory("Assistant responded cordially.", "short_term", "assistant")
    memory_system.save_to_memory("User asked about the weather in London.", "short_term", "user")
    memory_system.save_to_memory("Assistant mentioned it's rainy.", "short_term", "assistant")

    print("\n--- Populating Long-Term Memory ---")
    memory_system.save_to_memory("Key fact: Project 'Phoenix' started last month.", "long_term")
    memory_system.save_to_memory("Reminder: Follow up with Dr. Aris.", "long_term")

    print("\n--- Setting Base Memory ---")
    memory_system.save_to_memory("The AI's name is Oracle. It aims to be helpful.", "base_memory")

    print("\n--- Memory Structure Before Checks (Formatted) ---")
    print(memory_system.get_memory_structure(formatted=True))

    # --- Deep Memory Operations (Requires functional AI) ---
    # Note: These depend heavily on the AI's ability to extract NER correctly.
    # Mocking the AI would be needed for reliable unit tests.
    if memory_system.deep_memory:
        # Create deep memory based on the current state
        memory_system.create_deep_memory()

        # Search deep memory
        # The AI needs to identify searchable terms (like 'London', 'Project Phoenix', 'Dr. Aris')
        # from the current memory context when search_deep_memory is called.
        found_excerpts = memory_system.search_deep_memory()
        if found_excerpts:
            print("\n--- Excerpts Found in Deep Memory ---")
            for excerpt in found_excerpts:
                print(f"- {excerpt}")
        else:
            print("\n--- No Excerpts Found in Deep Memory (or search terms not identified) ---")
    else:
        print("\n--- Deep Memory Operations Skipped (DeepMemory not initialized) ---")


    # --- Memory Check and Summarization (Requires functional AI) ---
    print("\n--- Running Memory Check (will summarize if thresholds met) ---")
    # Add more entries to potentially trigger summarization
    print("Adding more short-term entries...")
    for i in range(memory_system.SHORT_TERM_THRESHOLD):
         memory_system.save_to_memory(f"Filler message {i+1}", "short_term", "user" if i % 2 == 0 else "assistant")

    print("Adding more long-term entries...")
    for i in range(memory_system.LONG_TERM_THRESHOLD):
         memory_system.save_to_memory(f"Filler long-term note {i+1}", "long_term")

    # Run the check - this might call the AI multiple times if thresholds are hit
    memory_system.check()

    print("\n--- Memory Structure After Check (Formatted) ---")
    print(memory_system.get_memory_structure(formatted=True))

    # --- Optional: Final Deep Memory Update & Search after Check ---
    if memory_system.deep_memory:
        print("\n--- Running Deep Memory Create/Update Again After Check ---")
        memory_system.create_deep_memory() # Update with summarized info potentially

        print("\n--- Running Deep Memory Search Again After Check ---")
        found_excerpts_after = memory_system.search_deep_memory()
        if found_excerpts_after:
            print("\n--- Excerpts Found in Deep Memory (After Check) ---")
            for excerpt in found_excerpts_after:
                print(f"- {excerpt}")
                continue
        else:
            print("\n--- No Excerpts Found in Deep Memory (After Check) ---")

    print("\n--- Example Run Finished ---")

    # Optional: Clean up test files
    # print("\nCleaning up test files...")
    # if os.path.exists(test_main_mem_file): os.remove(test_main_mem_file)
    # if os.path.exists(test_deep_mem_file): os.remove(test_deep_mem_file)