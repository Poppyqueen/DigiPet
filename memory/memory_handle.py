# memory_handle.py
# Memory handle is a module to manage memory storage for an LLM, the system can be integrated into various situations where an agent needs
# to maintain a constant memory.

# It helps you set up a JSON database, to do different kinds of querries for memory management, the memory manager class contains functions to save
# memories into different sections and engage in a 'check' to summarize memories above our thesholds.

# Needs revamp

import json
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List # Import typing helpers

# Import extra memory module
from memory.deep_memory import DeepMemory # <--- Import DeepMemory here

from utils.memory_ai_helper import memory_ai
from utils.tokens_handle import token_manager
import configparser

config = configparser.ConfigParser()
config.read('main_config.ini')
system_prompt = config['AI']['sys_prompt']

# Define default filepaths
DEFAULT_MEMORY_DB = "memory_database.json"
DEFAULT_DEEP_MEMORY_DB = "deep_memory_database.json"

class memory_manager:

    # These numbers need to be adjusted to find an optimal spot, lower seems to be better for coherence during conversation and summarization.
    SHORT_TERM_THRESHOLD = 30  # Number of short-term entries before summarizing
    LONG_TERM_THRESHOLD = 10   # Number of long-term entries before summarizing
    SHORT_TERM_KEEP_COUNT = 15  # Number of latest short-term entries to keep after summarizing
    LONG_TERM_KEEP_COUNT = 5   # Number of latest long-term entries to keep after summarizing

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

        self.bot_instance = memory_ai(self.text_capture)

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

    def current_memory_tokens(self)-> int:
        memory_structure=self.get_memory_structure()
        constructed_data=self.construct_data(memory_structure, system_prompt)
        def extract_content_to_string(messages):
            """
            Extracts the content from a list of message dictionaries into a single string.

            Args:
                messages: A list of dictionaries, where each dictionary is expected
                        to have a 'content' key.

            Returns:
                A single string containing all the 'content' values concatenated,
                separated by newlines.
            """
            all_content = []
            for message in messages:
                # Check if the 'content' key exists in the dictionary
                if 'content' in message:
                    all_content.append(message['content'])
                # Optional: Handle cases where 'content' key is missing
                # else:
                #     print(f"Warning: Message dictionary missing 'content' key: {message}")

            # Join all the collected content strings with a newline separator
            return "\n".join(all_content)
        string_memory=extract_content_to_string(constructed_data)
        return self.token_manager.num_tokens_from_string(string_memory)


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
        Constructs the data to be sent to the OpenAI API for processing in a multi-turn format.
        It expects a memory structure and a system prompt.

        Creates an initial 'developer' message containing time, base prompt, base memory,
        and long-term memory. Then, processes short-term memory entries:
        'system_' and '0_system_' keys become separate 'system' messages.
        Other keys ('user_', 'assistant_', etc.) become messages with their corresponding roles.
        Messages are added in chronological order based on short-term keys.

        Args:
            memory_structure (dict): The dictionary representing the memory structure.
                                     Expected keys: 'base_memory', 'long_term', 'short_term'.
            sys_prompt (str): The base system prompt to include in the developer message.

        Returns:
            list: A list of message dictionaries formatted for the OpenAI API.
        """
        messages = []

        # --- Construct the initial 'developer' message (keeping original structure) ---
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

        developer_message = {
            "role": "developer",
            "content": system_message_content
        }
        messages.append(developer_message) # Add the initial developer message

        # --- Process Short-Term Memory entries ---
        short_term_memory = memory_structure.get("short_term", {})

        # Sort keys to maintain chronological order for conversation turns
        # Assumes keys like "user_timestamp", "assistant_timestamp", "0_system_timestamp", etc.
        # Sort keys based on the numeric timestamp part
        sorted_short_term_keys = sorted(short_term_memory.keys(), key=lambda k: int(k.split('_')[-1]))

        for key in sorted_short_term_keys:
            text = short_term_memory[key]
            message_entry = None # Initialize message entry

            # Check if the key is a system variant
            if key.startswith("0_system_") or key.startswith("system_"):
                 # Create a system message from this entry
                 message_entry = {
                     "role": "system",
                     "content": text
                 }
                 # Note: The '0_' or 'system_' prefix is implicitly handled
                 # by just assigning the "system" role and using the value as content.

            else:
                 # Process non-system keys (user, assistant, etc.)
                 # Extract the role from the key (e.g., "user_123" -> "user")
                 # Use split('_', 1) to handle potential underscores within the identifier part
                 parts = key.split('_', 1)
                 if len(parts) > 0:
                    role = parts[0]
                    # Basic validation for common API roles, excluding 'system' which is handled above
                    valid_roles = ["user", "assistant", "tool"]
                    if role in valid_roles:
                         message_entry = {"role": role, "content": text}
                    else:
                         # Handle unexpected roles - maybe default to user?
                         print(f"Warning: Unexpected role '{role}' extracted from key '{key}'. Treating as 'user'.")
                         # Include original role and key for context if defaulting
                         message_entry = {"role": "user", "content": f"[{role} - {key}]: {text}"}
                 else:
                    # Handle keys with no underscore - unexpected, treat as user?
                    print(f"Warning: Key '{key}' in short_term has no underscore. Treating as 'user'.")
                    message_entry = {"role": "user", "content": f"[Key: {key}]: {text}"}

            # Append the created message entry if one was generated
            if message_entry:
                messages.append(message_entry)


        # print("👾👾 👾👾 THESE ARE THE MESSAGES WE ARE SENDING INTO THE AI 👾👾 👾👾")
        # print(messages)
        return messages

    def random_memory(self):
        random_data=self.deep_memory.random_access()
        return random_data

    def save_to_memory(self, string_to_save: str, memory_type: str, tag: Optional[str] = None):
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
            saved_content = f"Time of the exchange: {formatted_time}\n Exchange: {string_to_save}"

            # Ensure 'short_term' exists and is a dict
            if "short_term" not in memory_data or not isinstance(memory_data["short_term"], dict):
                memory_data["short_term"] = {}

            # Create a unique key using the tag and timestamp
            key = f"{tag}_{current_time}" # Timestamp ensures chronological order when sorted
            memory_data["short_term"][key] = saved_content

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
        # Consider more specific logging later if needed
        # print(f"Saved to '{memory_type}' memory.")

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
        
    def process_short_term_system(self) -> int:
        """
        Processes system-tagged entries in the short_term memory section.

        First, removes entries tagged as '0_system_'.
        Second, finds entries tagged as 'system_' and renames them
        by prepending '0_' (e.g., 'system_foo' becomes '0_system_foo').

        Finally, saves the updated memory structure if any changes occurred.

        Returns:
            int: The total number of entries that were removed (0_system_)
                 or processed (system_ renamed to 0_system_).
        """
        memory_data = self._load_memory()
        if memory_data is None:
            print("Error: Could not load memory data. Cannot process system messages.")
            return 0 # Indicate nothing affected due to error

        # Access the short_term section, default to an empty dict if it doesn't exist
        # or is not a dict (defensive coding)
        short_term_memory = memory_data.get("short_term", {})
        if not isinstance(short_term_memory, dict):
            print("Warning: short_term memory structure is not a dictionary. Cannot process system messages.")
            return 0

        removed_0_count = 0
        processed_count = 0 # Count of system_ keys that were renamed
        total_affected = 0

        # --- Step 1: Remove existing '0_system_' entries ---
        keys_to_remove_0 = []
        # Collect keys to remove because we can't modify the dict during iteration
        for key in short_term_memory.keys():
            if key.startswith("0_system_"):
                keys_to_remove_0.append(key)

        # Remove the identified entries
        for key in keys_to_remove_0:
            try:
                del short_term_memory[key]
                removed_0_count += 1
                # print(f"Removed old system short-term memory with key: {key}") # Optional logging
            except KeyError:
                # Should not happen if list is built from current keys
                pass # Key was already removed

        # --- Step 2: Find and process 'system_' entries (rename to '0_system_') ---
        # Collect keys to process *after* removal in case a key was just removed
        keys_to_process = []
        for key in short_term_memory.keys():
             if key.startswith("system_"):
                 keys_to_process.append(key)

        # Process the identified entries by renaming
        for old_key in keys_to_process:
            # Ensure the key still exists before trying to access/delete
            if old_key in short_term_memory:
                new_key = "0_" + old_key
                try:
                    # Copy the value to the new key
                    short_term_memory[new_key] = short_term_memory[old_key]
                    # Delete the old key
                    del short_term_memory[old_key]
                    processed_count += 1
                    # print(f"Processed system short-term memory: Renamed '{old_key}' to '{new_key}'") # Optional logging
                except KeyError:
                    # Should not happen if key existence is checked, but defensive
                    pass # Key was unexpectedly modified or removed during processing

        total_affected = removed_0_count + processed_count

        # Update the memory_data dictionary with the modified short_term section
        memory_data["short_term"] = short_term_memory

        # Save the updated memory data if any items were affected
        if total_affected > 0:
            self._save_memory(memory_data)
            print(f"Processed short-term system messages: Removed {removed_0_count} old entries and processed {processed_count} new entries.")
        else:
            print("No short-term system messages found to process or remove.")

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

        non_system_entry_count = 0
        total_entry_count = 0 # Keep track of total count for logging

        if isinstance(short_term_memory, dict):
            total_entry_count = len(short_term_memory)
            # Count entries where the key does NOT start with '_system_'
            non_system_entry_count = len([key for key in short_term_memory.keys() if not key.startswith('_system_')])

        # Check if the threshold is reached based on non-system entries count
        if non_system_entry_count >= self.SHORT_TERM_THRESHOLD:
                

            self._archive_memory(self._load_memory(), "short_term")

            if self.deep_memory_flag:
                self.create_deep_memory()

            # Sort keys chronologically using the timestamp part
            try:
                # Ensure keys have the expected format before sorting
                valid_keys = [k for k in short_term_memory.keys() if '_' in k and k.split('_')[-1].isdigit()]
                sorted_short_term_keys = sorted(valid_keys, key=lambda k: int(k.split('_')[-1]))
            except ValueError as e:
                print(f"Error sorting short-term keys (check key format 'tag_timestamp'): {e}")
                sorted_short_term_keys = list(short_term_memory.keys()) # Fallback to unsorted

            structured_short_term = ""
            for key in sorted_short_term_keys:
                # Extract tag and handle potential key format issues
                parts = key.split('_')
                tag = parts[0].capitalize() if parts else "Unknown"
                structured_short_term += f"[{tag}]: {short_term_memory[key]}\n" # Assuming value is the string to summarize

            if structured_short_term:
                #print("DEBUG: Calling AI to summarize short-term memory...")
                try:
                    summary_short_term = self.bot_instance.summarize_memories(structured_short_term, "short_term")
                    if summary_short_term:
                        #print(f"DEBUG: Short-term summary created: {summary_short_term[:100]}...")
                        # Add summary to long-term memory (will be saved later)
                        if "long_term" not in memory_data or not isinstance(memory_data["long_term"], list):
                            memory_data["long_term"] = []
                        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        memory_data["long_term"].append(f"[{timestamp_str}] [Summary of recent conversation]: {summary_short_term}")
                        #print("DEBUG: Summary added to long-term memory queue.")
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
        # Use potentially updated memory_data (if short-term summary was added)
        long_term_memory = memory_data.get("long_term", [])
        if isinstance(long_term_memory, list) and len(long_term_memory) >= self.LONG_TERM_THRESHOLD:
            print(f"\n--- Long-Term Memory Check Triggered ({len(long_term_memory)} >= {self.LONG_TERM_THRESHOLD}) ---")

            self._archive_memory(self._load_memory(), "long_term")


            structured_long_term = ""
            for i, entry in enumerate(long_term_memory):
                # Handle potential dicts or just strings
                entry_text = entry.get("memory") if isinstance(entry, dict) else str(entry)
                structured_long_term += f"[Entry {i+1}]: {entry_text}\n"

            base_memory_content = memory_data.get("base_memory", "")
            # Ensure base_memory is a string
            if not isinstance(base_memory_content, str):
                 base_memory_content = str(base_memory_content)

            # Combine Base and Long-Term for context during summarization
            structured_for_ai = f"Current Base Memory:\n{base_memory_content}\n\nRecent Long-Term Memories to Summarize and Integrate:\n{structured_long_term}"

            if structured_long_term: # Only summarize if there are long-term entries
                print("DEBUG: Calling AI to summarize long-term memory into base memory...")
                try:
                    summary_long_term_base = self.bot_instance.summarize_memories(structured_for_ai, "long_term")
                    if summary_long_term_base:
                        print(f"DEBUG: Base memory summary created: {summary_long_term_base[:100]}...")
                        memory_data["base_memory"] = summary_long_term_base # Update base memory
                        print("DEBUG: Base memory updated with summary.")
                        needs_save = True

                        # Purge oldest long-term memories AFTER summarization
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