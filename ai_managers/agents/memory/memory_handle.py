import json
import os
import time
# from datetime import datetime

from utils.loc_datetime import datetime

from typing import Optional, Dict, Any
import re
import uuid

# Import extra memory module
from ai_managers.agents.memory.memory_configs import (short_term_prompt, long_term_prompt)

from ai_managers.agents.memory.deep_memory_int.deep_memory import DeepMemory

from ai_managers.ai_utils.ai_loader import AIConfiguration, TokenizerConfiguration

# Define default filepaths
DEFAULT_MEMORY_DB = "memory_database.json"
DEFAULT_DEEP_MEMORY_DB = "deep_memory_database.db"

class memory_manager:

    # # # # # New token-based retention budgets
    # # # # # Memory summarizarion thresholds for individual token lenghts for each category
    # SHORT_TERM_TOKEN_THRESHOLD = 22000
    # LONG_TERM_TOKEN_THRESHOLD = 22000

    # # Determines how much of the recent entries in tokens are kept after summarization
    # SHORT_TERM_RETAIN_TOKEN_BUDGET = 4000
    # LONG_TERM_RETAIN_TOKEN_BUDGET = 4000

    # # "Line in the sand", if any system message is above our token "line in the sand", it will check if there is a summarization needed for it
    # # the idea is that it is a point where the conversation might be too old for this specifc message to be relevant anymore
    # # a smarter system would get info on what specifics to retain after summarization, right now it is a simple contextless summarization process
    # SYSTEM_MESSAGE_LINE_THRESHOLD = 6000
    # # Individual message token threshold: if a system message is above this, try to summarize it
    # SYSTEM_MESSAGE_SUMMARIZE_THRESHOLD = 3000


    # # # Test settings
    # # Memory summarizarion thresholds for individual token lenghts for each category
    # SHORT_TERM_TOKEN_THRESHOLD = 11000
    # LONG_TERM_TOKEN_THRESHOLD = 11000

    # # Determines how much of the recent entries in tokens are kept after summarization
    # SHORT_TERM_RETAIN_TOKEN_BUDGET = 2000
    # LONG_TERM_RETAIN_TOKEN_BUDGET = 2000

    # SYSTEM_MESSAGE_LINE_THRESHOLD = 4000
    # # Individual message token threshold: if a system message is above this, try to summarize it
    # SYSTEM_MESSAGE_SUMMARIZE_THRESHOLD = 1500

    # ##########
    # SHORT_TERM_RETAIN_TOKEN_BUDGET = 300
    # LONG_TERM_RETAIN_TOKEN_BUDGET = 300

    # SHORT_TERM_TOKEN_THRESHOLD = 1000
    # LONG_TERM_TOKEN_THRESHOLD = 1000

    # SYSTEM_MESSAGE_LINE_THRESHOLD = 1200
    # # Individual message token threshold: if a system message is above this, try to summarize it
    # SYSTEM_MESSAGE_SUMMARIZE_THRESHOLD = 2000




    def __init__(self, filepath: str = DEFAULT_MEMORY_DB, deep_memory_filepath: str = DEFAULT_DEEP_MEMORY_DB, deep_memory: bool = False, text_capture=None, sub_directory=None, config_manager=None):
        self.text_capture=text_capture
        self.filepath = filepath
        self.deep_memory_filepath = deep_memory_filepath
        self._check_and_create_db()
        self.deep_memory_flag= deep_memory
        self.sub_directory=sub_directory
        self.token_counters_cache = {} # <--- NEW: Cache for token counts
        self.config_manager = config_manager 

    ### ///////// Init config  /////////  #####


        selected_model= config_manager.get_config('AI','memory_model')
        config_selected_provider = config_manager.get_config('AI','memory_ai_provider')

        general_model_prov= config_manager.get_config('AI', "general_ai_provider")
        general_model=config_manager.get_config('AI', "general_model")


        # handle the case this is falsy with a default
        self.max_tokens_limit = config_manager.get_config('AI', "max_memory_tokens")

        # 1. Load Total Max Limit
        if not self.max_tokens_limit:
            self.max_tokens_limit = 20000  # Default value

        
        # These configs could be added to the config manager, in the GUI? but we are using defaults for now
        # Not sure if we want to make this configurable or not

        # 2. Load Ratios (with sensible defaults if missing from config)
        # What % of the total budget is for Short Term? (Default 35%)
        self.st_ratio = float(config_manager.get_config('AI', "memory_st_ratio") or 0.35)
        
        # When cleaning, how much context do we keep? (Default 35%)
        # e.g., if ST max is 10k, we keep the last 3.5k tokens after summarizing
        self.retention_ratio = float(config_manager.get_config('AI', "memory_retention_ratio") or 0.35)

        self.bot_instance = AIConfiguration(provider=config_selected_provider,model=selected_model,mode="simple_ai").get_client()

        # Use the tokenizer for the general model, (the agent's model), instead of the memory model
        self.token_manager = TokenizerConfiguration(provider=general_model_prov,model=general_model).get_tokenizer()

        if self.bot_instance and self.deep_memory_flag:
            try:
                self.deep_memory = DeepMemory(deep_memory_filepath, self.text_capture, config_manager)
            except Exception as e:
                print(f"Error initializing DeepMemory: {e}")
                self.deep_memory = None
        else:
            print("DeepMemory not initialized because ai_bot_instance is not available.")
            self.deep_memory = None
            self.deep_memory_flag = False

        print(f"DEBUG: BUDGETS: {self.calc_budgets()}")


    def calc_budgets(self) -> dict:
        """
        Calculates memory thresholds dynamically based on the max_tokens_limit 
        and the defined allocation ratios.
        """
        
        # 1. Calculate the ceiling for Short Term vs Long Term
        # Example: 20,000 limit * 0.7 = 14,000 tokens for Short Term
        short_term_max = int(self.max_tokens_limit * self.st_ratio)
        
        # Example: Remaining 6,000 tokens for Long Term
        long_term_max = int(self.max_tokens_limit - short_term_max)

        # 2. Calculate Retention Budgets (How much to keep after a purge)
        # This keeps the most recent context while dumping the middle.
        short_term_retain = int(short_term_max * self.retention_ratio)
        long_term_retain = int(long_term_max * self.retention_ratio)

        # 3. Calculate System Message specific thresholds
        # These are used to decide when to summarize a giant tool output in the middle of a chat.
        # We scale these based on the Short Term budget, not the global budget.
        
        # "Line in the sand": If a tool message is deeper in history than this, we check it.
        # Example: 30% into the short term history.
        system_line_budget = int(short_term_max * 0.30) 
        
        # "Summarize Threshold": If a tool message is larger than this, we crunch it.
        # Example: 25% of the short term budget.
        system_summarize_budget = int(short_term_max * 0.25)

        return {
            "short_term_threshold": short_term_max,
            "long_term_threshold": long_term_max,
            "short_term_retain": short_term_retain,
            "long_term_retain": long_term_retain,
            "system_line": system_line_budget,
            "system_summarize": system_summarize_budget
        }


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
                # Iterate through each tag (e.g., 'user', 'assistant', 'system', 'tool')
                for tag, entries_list in memory_structure["short_term"].items():
                    if isinstance(entries_list, list):
                        for entry in entries_list:
                            if isinstance(entry, dict) and "content" in entry:
                                content_data = entry["content"]
                                if isinstance(content_data, dict):
                                    # Handle dictionary content (e.g., function call results)
                                    # We want to exclude 'context' if it exists
                                    temp_content_data = content_data.copy() # Create a copy to modify
                                    if "context" in temp_content_data:
                                        del temp_content_data["context"] # Remove context before dumping

                                    # Only add to string_memory if there's still content left
                                    if temp_content_data:
                                        string_memory += json.dumps(temp_content_data) + "\n"
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

        total_tokens = self.token_manager.count_tokens(string_memory)
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
                "short_term": {
                    "user": [],
                    "assistant": [],
                    "system": [],
                    "tool": []  # <--- UPDATED: Added new tool tag
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
                        "short_term": {"user": [], "assistant": [], "system": [], "tool": []}, # <--- UPDATED: Default short_term
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
        them into 'conversation_turns' (user, assistant) and 'tool_outputs' (from system/tool messages).
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
                print(f"Warning: Unexpected short_term memory format for tag '{tag}'. Expected list, got {type(entries_list)}.")

        # Sort all entries based on their 'timestamp'. 'unique_id' as secondary sort for stability.
        all_short_term_entries.sort(key=lambda x: (x.get('timestamp', 0), x.get('unique_id', '')))

        for entry in all_short_term_entries:
            text_or_object = entry["content"]
            key_tag = entry["original_tag"]

            # --- UPDATED: Handle 'system' and 'tool' tags for tool outputs ---
            if key_tag in ["system", "tool"]:
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
                # elif isinstance(text_or_object, str):
                #     print(f"Warning: Plain string system message found for tag '{key_tag}'. Treating as 'user'")
                #     structured_memory["conversation_history"].append({
                #         "type": "user",
                #         "content": text_or_object
                #     })
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
        """Saves a string or dict to the specified memory section.
           For 'short_term', a tag ('user', 'assistant', 'system', 'tool') is required.
           Entries are appended to a list under their tag, including timestamp and unique ID.
        """
        memory_data = self._load_memory()
        if memory_data is None:
            print("Error: Could not load memory data. Save operation cancelled.")
            return

        memory_type = memory_type.lower()
        current_time = int(time.time())

        if memory_type == "short_term":
            if tag is None:
                print("Error: Tag is required for short_term memory.")
                return

            tag = tag.lower()

            if "short_term" not in memory_data or not isinstance(memory_data["short_term"], dict):
                memory_data["short_term"] = {"user": [], "assistant": [], "system": [], "tool": []}

            if tag not in memory_data["short_term"] or not isinstance(memory_data["short_term"][tag], list):
                memory_data["short_term"][tag] = []

            entry = {
                "timestamp": time.time(),
                "content": string_to_save,
                "unique_id": str(uuid.uuid4())
            }

            memory_data["short_term"][tag].append(entry)

        elif memory_type == "long_term":
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
        print(f"Saved to '{memory_type}' memory under tag '{tag}'.")

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

    def relevance_process(self):
        """
        This function is a placeholder for future semantic relevance processing.
        It is not currently implemented in this version but serves as a conceptual
        point for potential future enhancements to memory management.
        """
        print("Relevance process is a placeholder and not currently active.")
    def process_short_term_system(self) -> int:
        """
        Processes short-term memory by creating a "token timeline" of the entire
        conversation. It identifies system and tool messages that appear after a specific
        token position (SYSTEM_MESSAGE_LINE_THRESHOLD) and summarizes them if they are
        individually large enough (SYSTEM_MESSAGE_SUMMARIZE_THRESHOLD).

        This function should be run periodically as it has no internal "total token" trigger.
        """

        keep_tool_entry_count = 3
        memory_data = self._load_memory()
        if memory_data is None:
            return 0

        # --- Step 1: Get ALL short-term messages and order them chronologically ---
        short_term_memory = memory_data.get("short_term", {})
        all_entries = []
        for tag, entries_list in short_term_memory.items():
            if isinstance(entries_list, list):
                for entry in entries_list:
                    entry['original_tag'] = tag  # Temporarily tag for rebuilding
                    all_entries.append(entry)

        if not all_entries:
            return 0

        all_entries.sort(key=lambda x: x.get('timestamp', 0))

        # Identify which entries should be safeguarded
        tool_entries_indices = [
            i for i, entry in enumerate(all_entries)
            if entry.get('original_tag') in ['system', 'tool']
        ]
        # Get indices of the last 'keep_tool_entry_count' tool messages
        safeguarded_indices = set(tool_entries_indices[-keep_tool_entry_count:]) if tool_entries_indices else set()

        # --- Step 2: Walk the "token timeline" and process messages ---
        cumulative_tokens = 0
        final_entries = []
        summarized_count = 0

        for idx, entry in enumerate(all_entries):
            start_token_position = cumulative_tokens
            content_data = entry.get("content", "")

            # --- The Core Logic ---
            # --- UPDATED: Check if the entry is a structured system OR tool message ---
            is_structured_tool_message = (
                entry.get('original_tag') in ['system', 'tool'] and
                isinstance(content_data, dict) and
                "result" in content_data
            )

            # Check if this specific entry is safeguarded
            is_safeguarded = idx in safeguarded_indices

            if is_structured_tool_message and not is_safeguarded:
                result_text = str(content_data.get("result", ""))
                result_tokens = self.token_manager.count_tokens(result_text)

                # Now check if it meets the criteria for summarization
                if (start_token_position > self.calc_budgets()["system_line"] and
                        result_tokens > self.calc_budgets()["system_summarize"]):

                    print(f"Tool/System message (ID: {entry.get('unique_id')}) at token position {start_token_position} is a candidate for summarization.")

                    try:
                        summarized_content_raw = self.bot_instance.response_output(
                            system="You are a helpful assistant. Summarize the following tool output concisely, retaining key information:",
                            message=result_text
                        )

                        new_content = content_data.copy()
                        new_content["result"] = f"Summarized from original tool output: {summarized_content_raw}"

                        summarized_entry = {
                            "timestamp": entry.get("timestamp"),
                            "content": new_content,
                            "unique_id": entry.get("unique_id"),
                            "original_tag": entry.get('original_tag')
                        }

                        final_entries.append(summarized_entry)
                        summarized_count += 1

                        cumulative_tokens += self.token_manager.count_tokens(json.dumps(new_content))
                        continue

                    except Exception as e:
                        print(f"Error during summarization: {e}. Keeping original message.")

            # --- Pass-Through Logic ---
            final_entries.append(entry)
            if isinstance(content_data, dict):
                timeline_tokens = self.token_manager.count_tokens(json.dumps(content_data))
            else:
                timeline_tokens = self.token_manager.count_tokens(str(content_data))
            cumulative_tokens += timeline_tokens

        # --- Step 3: Rebuild and save the short-term memory if changes were made ---
        if summarized_count > 0:
            print(f"Summarized {summarized_count} system/tool message(s). Rebuilding memory.")

            # --- UPDATED: Initialize with 'tool' tag ---
            new_short_term_memory = {"user": [], "assistant": [], "system": [], "tool": []}
            for entry in final_entries:
                tag = entry.pop('original_tag')
                if tag in new_short_term_memory:
                    new_short_term_memory[tag].append(entry)

            memory_data["short_term"] = new_short_term_memory
            self._save_memory(memory_data)
        else:
            print("No system or tool messages met the criteria for summarization.")

        return summarized_count

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
        and purges older memories based on a token budget, keeping the most recent entries.
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

        if token_count >= self.calc_budgets()["short_term_threshold"]:
            message=f"\n--- Short-Term Memory Check Triggered ({token_count} >= {self.calc_budgets()['short_term_threshold']}) ---"
            print(message)
            self.text_capture.dump_text(message)

            self._archive_memory(memory_data, "short_term")

            if self.deep_memory_flag:
                self.create_deep_memory() # Creating a "Deep Memory" when a short-term summarization process is triggered

            all_short_term_entries = []
            for tag, entries_list in memory_data.get("short_term", {}).items():
                if not isinstance(entries_list, list):
                    continue
                for entry in entries_list:
                    if not (isinstance(entry, dict) and "content" in entry and "timestamp" in entry):
                        continue

                    formatted_time = datetime.fromtimestamp(entry["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                    content_data = entry["content"]

                    if isinstance(content_data, dict):
                        temp_content_data = content_data.copy()
                        if "context" in temp_content_data:
                            del temp_content_data["context"]
                        text_for_tokens = json.dumps(temp_content_data) if temp_content_data else ""
                    else:
                        text_for_tokens = str(content_data)

                    all_short_term_entries.append({
                        "timestamp": entry["timestamp"],
                        "unique_id": entry.get("unique_id", str(uuid.uuid4())),
                        "text_for_ai": f"[{tag.upper()} - {formatted_time}] {text_for_tokens}",
                        "original_tag": tag,
                        "original_entry": entry,
                        "tokens": self.token_counters_cache.get(entry.get("unique_id"), self.token_manager.count_tokens(text_for_tokens))
                    })
                    if entry.get("unique_id") not in self.token_counters_cache:
                        self.token_counters_cache[entry.get("unique_id")] = all_short_term_entries[-1]["tokens"]

            all_short_term_entries.sort(key=lambda x: x["timestamp"])

            structured_short_term_for_ai = "\n".join([item["text_for_ai"] for item in all_short_term_entries])
            print(f"Summarizing short-term memory (Tokens: {token_count})...")

            summarized_content_raw = self.bot_instance.response_output(
                system=short_term_prompt,
                message="Summarize this: \n" + structured_short_term_for_ai,
            )
            summarized_content = summarized_content_raw
            message=f"Short-term memory summarized to: {summarized_content}"
            print(message)
            self.text_capture.dump_text(message)

            if "long_term" not in memory_data or not isinstance(memory_data["long_term"], list):
                memory_data["long_term"] = []
            summary_timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            memory_data["long_term"].append(f"[{summary_timestamp_str}] Summary of recent activity: {summarized_content}")
            needs_save = True

            entries_to_keep = []
            current_retained_tokens = 0

            for entry_item in reversed(all_short_term_entries):
                unique_id = entry_item.get("unique_id")
                if unique_id and unique_id in self.token_counters_cache:
                    entry_tokens = self.token_counters_cache[unique_id]
                else:
                    entry_tokens = self.token_manager.count_tokens(entry_item["text_for_ai"])
                    if unique_id:
                        self.token_counters_cache[unique_id] = entry_tokens

                if current_retained_tokens + entry_tokens <= self.calc_budgets()["short_term_retain"]:
                    entries_to_keep.append(entry_item)
                    current_retained_tokens += entry_tokens
                else:
                    break

            entries_to_keep.reverse()

            # --- UPDATED: Initialize with 'tool' tag for rebuilding ---
            new_short_term_memory = {"user": [], "assistant": [], "system": [], "tool": []}
            for item in entries_to_keep:
                tag = item["original_tag"]
                original_entry = item["original_entry"]
                if tag in new_short_term_memory:
                    new_short_term_memory[tag].append(original_entry)

            memory_data["short_term"] = new_short_term_memory
            print(f"Short-term memory purged, keeping latest {len(entries_to_keep)} entries ({current_retained_tokens} tokens).")

        # --- Long-Term Memory Check ---
        long_term_token_count = self.current_memory_tokens("long_term")
        if long_term_token_count >= self.calc_budgets()["long_term_threshold"]:
            message=f"\n--- Long-Term Memory Check Triggered ({long_term_token_count} >= {self.calc_budgets()['long_term_threshold']}) ---"
            print(message)
            self.text_capture.dump_text(message)

            self._archive_memory(memory_data, "long_term")

            long_term_content_for_ai = "\n".join(memory_data.get("long_term", []))
            print(f"Summarizing long-term memory (Tokens: {long_term_token_count})...")

            summarized_content_raw = self.bot_instance.response_output(
                system=long_term_prompt,
                message=long_term_content_for_ai
            )

            message=f"Long-term memory summarized to base memory: {summarized_content_raw}"
            print(message)
            self.text_capture.dump_text(message)

            new_base_memory_summary = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Comprehensive summary of past long-term memory: {summarized_content_raw}"

            parsed_long_term = []
            for entry_str in memory_data.get("long_term", []):
                match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (.*)$', entry_str)
                if match:
                    dt_object = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                    parsed_long_term.append({"timestamp": dt_object.timestamp(), "original_string": entry_str})

            parsed_long_term.sort(key=lambda x: x["timestamp"])

            kept_long_term_entries = []
            current_retained_tokens = 0
            for entry_item in reversed(parsed_long_term):
                entry_tokens = self.token_manager.count_tokens(entry_item["original_string"])

                if current_retained_tokens + entry_tokens <= self.calc_budgets()["long_term_retain"]:
                    kept_long_term_entries.append(entry_item)
                    current_retained_tokens += entry_tokens
                else:
                    break

            kept_long_term_entries.reverse()
            new_long_term_list = [item["original_string"] for item in kept_long_term_entries]

            memory_data["long_term"] = new_long_term_list
            memory_data["base_memory"] = new_base_memory_summary
            print(f"Long-term memory purged, keeping latest {len(new_long_term_list)} entries ({current_retained_tokens} tokens). New summary moved to base memory.")
            needs_save = True

        if needs_save:
            self._save_memory(memory_data)
            print("Memory state saved after summarization/purging.")
        else:
            print("No memory thresholds reached. No changes made.")

    def create_deep_memory(self):
        """Triggers creation/update of deep memory (e.g., NER or embeddings)."""
        if self.deep_memory and self.deep_memory_flag:
            print("Triggering Deep Memory creation/update...")
            try:
                current_full_memory_structure = self.get_memory_structure()
                self.deep_memory.create_memory(current_full_memory_structure)
                print("Deep Memory creation/update complete.")
            except Exception as e:
                print(f"Error during Deep Memory creation/update: {e}")
        else:
            print("Deep Memory not enabled or initialized.")