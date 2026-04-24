import json
import os
import time

from utils.loc_datetime import datetime

from typing import Optional, Dict, Any
import re
import uuid

# Import extra memory module
from ai_managers.agents.memory.memory_configs import (short_term_prompt, long_term_prompt)

from ai_managers.agents.memory.deep_memory_int.deep_memory import DeepMemory

from ai_managers.ai_utils.ai_loader import AIConfiguration, TokenizerConfiguration

from utils.pydantic_models import StructuredMemory

# Define default filepaths
DEFAULT_MEMORY_DB = "memory_database.json"
DEFAULT_DEEP_MEMORY_DB = "deep_memory_database.db"


# NOTE: Important, this memory manager does not care about the larger tools definitions or crucially, tools context from
# construct_tools.py, it ignores around 2k tokens depending on what AI you are using. 
# Not sure what to do about that, not sure if it should be aware of that.

class memory_manager:

    def __init__(self, filepath: str = DEFAULT_MEMORY_DB, deep_memory_filepath: str = DEFAULT_DEEP_MEMORY_DB, deep_memory: bool = False, text_capture=None, sub_directory=None, config_manager=None):
        self.text_capture = text_capture
        self.filepath = filepath
        self.deep_memory_filepath = deep_memory_filepath
        self._check_and_create_db()
        self.deep_memory_flag = deep_memory
        self.sub_directory = sub_directory
        self.config_manager = config_manager

    ### ///////// Init config  /////////  #####

        selected_model = config_manager.get_config('AI', 'memory_model')
        config_selected_provider = config_manager.get_config('AI', 'memory_ai_provider')

        general_model_prov = config_manager.get_config('AI', "general_ai_provider")
        general_model = config_manager.get_config('AI', "general_model")

        # handle the case this is falsy with a default
        self.max_tokens_limit = config_manager.get_config('AI', "max_memory_tokens")

        # 1. Load Total Max Limit
        if not self.max_tokens_limit:
            self.max_tokens_limit = 20000  # Default value

        # TODO: Add these to UI config screen?
        # 2. Load Ratios (with sensible defaults if missing from config)
        # What % of the total budget is for Short Term? (Default 35%)
        self.st_ratio = float(config_manager.get_config('AI', "memory_st_ratio") or 0.35)
        # When cleaning, how much context do we keep? (Default 35%)
        self.st_retention_ratio = float(config_manager.get_config('AI', "memory_retention_ratio") or 0.35) 
        self.lt_retention_ratio = float(config_manager.get_config('AI', "memory_retention_ratio") or 0.35) # TODO: Figure out a ratio for long term?
        ##


        self.bot_instance = AIConfiguration(provider=config_selected_provider, model=selected_model, mode="simple_ai").get_client()
        # Use the tokenizer for the general model (the agent's model), not the memory model
        self.token_manager = TokenizerConfiguration(provider=general_model_prov, model=general_model).get_tokenizer()

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

    # ------------------------------------------------------------------
    # Token counting — single canonical entry point
    # ------------------------------------------------------------------

    def _count_entry_tokens(self, content) -> int:
        """
        Counts tokens for a single entry's content, serialized exactly as the
        LLM would read it.  This is the ONE place that calls token_manager.

        Rules that mirror construct_data:
          - user / assistant entries  → raw string content
          - tool_batch dict           → json.dumps of the calls list
          - legacy tool dict          → the result string only
          - long_term string          → the string as stored
          - anything else             → json.dumps fallback
        """
        if isinstance(content, dict):
            if content.get("type") == "tool_batch":
                # Only the calls list is what the LLM ultimately sees
                text = json.dumps(content.get("calls", []))
            elif "result" in content:
                # Legacy single tool call — count only the result
                text = str(content.get("result", ""))
            else:
                text = json.dumps(content)
        else:
            text = str(content)

        return self.token_manager.count_tokens(text)

    # ------------------------------------------------------------------
    # Budgets
    # ------------------------------------------------------------------

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
        short_term_retain = int(short_term_max * self.st_retention_ratio)
        long_term_retain = int(long_term_max * self.lt_retention_ratio)
        system_line_budget = int(short_term_max * 0.30)
        system_summarize_budget = int(short_term_max * 0.25)

        return {
            "short_term_threshold": short_term_max,
            "long_term_threshold": long_term_max,
            "short_term_retain": short_term_retain,
            "long_term_retain": long_term_retain,
            "system_line": system_line_budget,
            "system_summarize": system_summarize_budget
        }

    # ------------------------------------------------------------------
    # Token totals — reads stored counts, zero tokenizer calls
    # ------------------------------------------------------------------

    def current_memory_tokens(self, memory_type: str = "all") -> int:
        """
        Returns the current token total for the requested memory section(s).

        Token counts are read directly from the stored 'token_count' field on
        each entry — no re-tokenization happens here.

        Args:
            memory_type: 'all', 'short_term', 'long_term', or 'base_memory'.

        Returns:
            int: Sum of stored token counts for the section(s).
        """
        if memory_type not in ["all", "short_term", "long_term", "base_memory"]:
            raise ValueError("Invalid type specified. Use 'all', 'short_term', 'long_term', or 'base_memory'.")

        memory_structure = self.get_memory_structure()
        if memory_structure is None:
            return 0

        total = 0

        if memory_type in ("all", "short_term"):
            short_term = memory_structure.get("short_term", {})
            if isinstance(short_term, dict):
                for tag, entries_list in short_term.items():
                    if isinstance(entries_list, list):
                        for entry in entries_list:
                            total += entry.get("token_count", 0)

        if memory_type in ("all", "long_term"):
            for item in memory_structure.get("long_term", []):
                if isinstance(item, dict):
                    total += item.get("token_count", 0)
                else:
                    # Fallback: plain string entry without a stored count.
                    # Only occurs if data was written by an older version of this class.
                    total += self.token_manager.count_tokens(str(item))

        if memory_type in ("all", "base_memory"):
            base = memory_structure.get("base_memory", {})
            if isinstance(base, dict):
                total += base.get("token_count", 0)
            elif isinstance(base, str) and base:
                # Fallback for legacy plain-string base_memory on disk
                total += self.token_manager.count_tokens(base)

        print(f"Current memory tokens ({memory_type}): {total}")
        return total

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _check_and_create_db(self):
        """
        Checks if the main JSON database file exists and creates it if not.
        """
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            initial_memory = {
                "short_term": {
                    "user": [],
                    "assistant": [],
                    "system": [],
                    "tool": []
                },
                "long_term": [],
                "base_memory": {"content": "", "token_count": 0}
            }
            with open(self.filepath, 'w') as f:
                json.dump(initial_memory, f, indent=4)
            print(f"Main memory database file created at: {self.filepath}")

    def _load_memory(self) -> Optional[Dict[str, Any]]:
        """
        Loads main memory data from the JSON file.
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
                        "short_term": {"user": [], "assistant": [], "system": [], "tool": []},
                        "long_term": [],
                        "base_memory": {"content": "", "token_count": 0}
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
        Saves main memory data to the JSON file.
        """
        try:
            with open(self.filepath, 'w') as f:
                json.dump(memory_data, f, indent=4)
        except Exception as e:
            print(f"Error saving to main memory database file: {e}")

    # ------------------------------------------------------------------
    # Public write interface
    # ------------------------------------------------------------------

    def wipe_short_term(self) -> None:
        """
        Resets short-term memory to an empty structure.
        Long-term memory and base_memory are untouched.
        """
        memory_data = self._load_memory()
        if memory_data is None:
            print("Warning: Could not load memory for wipe. Skipping.")
            return

        memory_data["short_term"] = {
            "user":      [],
            "assistant": [],
            "system":    [],
            "tool":      [],
        }

        self._save_memory(memory_data)
        print("memory_manager: short-term memory wiped.")

    def save_to_memory(self, string_to_save, memory_type: str, tag: Optional[str] = None):
        """
        Saves a string or dict to the specified memory section.

        Token count is computed here via _count_entry_tokens and stored
        alongside the entry — no runtime re-counting ever needed.

        For 'short_term', a tag ('user', 'assistant', 'system', 'tool') is required.
        """
        memory_data = self._load_memory()
        if memory_data is None:
            print("Error: Could not load memory data. Save operation cancelled.")
            return

        memory_type = memory_type.lower()
        current_time = int(time.time())

        # ── Compute token count once, right here, before writing ──────────────
        token_count = self._count_entry_tokens(string_to_save)

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
                "timestamp":   time.time(),
                "content":     string_to_save,
                "unique_id":   str(uuid.uuid4()),
                "token_count": token_count,          # ← stored at write time
            }

            memory_data["short_term"][tag].append(entry)

        elif memory_type == "long_term":
            if "long_term" not in memory_data or not isinstance(memory_data["long_term"], list):
                memory_data["long_term"] = []

            timestamp_str = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')
            formatted_memory = f"[{timestamp_str}] {string_to_save}"

            long_term_entry = {
                "timestamp":   current_time,
                "content":     formatted_memory,
                "token_count": self.token_manager.count_tokens(formatted_memory),  # plain string, count directly
            }

            memory_data["long_term"].append(long_term_entry)
            print("Long term memory saved.")

        elif memory_type == "base_memory":
            memory_data["base_memory"] = {
                "content":     string_to_save,
                "token_count": self.token_manager.count_tokens(string_to_save),
            }
            print("Base memory updated.")

        else:
            print(f"Error: Invalid memory_type '{memory_type}'. Use 'short_term', 'long_term', or 'base_memory'.")
            return

        self._save_memory(memory_data)
        print(f"Saved to '{memory_type}' memory (tag='{tag}', tokens={token_count}).")

    # ------------------------------------------------------------------
    # Read interface
    # ------------------------------------------------------------------

    def get_memory_structure(self, formatted: bool = False) -> Optional[Dict[str, Any] | str]:
        """
        Retrieves the current main memory structure.
        """
        memory_data = self._load_memory()
        if memory_data is None:
            return None

        if formatted:
            return json.dumps(memory_data, indent=4)
        return memory_data

    def construct_data(self, memory_structure, sys_prompt="You are an AI agent, free and unshackled") -> StructuredMemory:
        """
        Constructs an agnostic, structured memory representation to be consumed
        by the LLM client.  Unchanged from original — this is the read path.
        """
        structured_memory = {
            "system_context": "",
            "conversation_history": []
        }

        current_time_unix = int(time.time())
        formatted_time = time.ctime(current_time_unix)

        system_message_content = f"The current time is: {formatted_time} \n\n"
        system_message_content += f"{sys_prompt}\n\n"

        base_memory_raw = memory_structure.get("base_memory", {})
        if isinstance(base_memory_raw, dict):
            base_memory = base_memory_raw.get("content", "No base memory available.")
        else:
            # Fallback for legacy plain-string base_memory on disk
            base_memory = base_memory_raw or "No base memory available."
        system_message_content += "Base Memory:\n"
        system_message_content += base_memory + "\n\n"

        long_term_memory = memory_structure.get("long_term", [])
        if long_term_memory:
            system_message_content += "Long-Term Memory:\n"
            for i, entry in enumerate(long_term_memory, 1):
                # Support both new dict format and legacy plain strings
                if isinstance(entry, dict):
                    system_message_content += f"{i}. {entry.get('content', '')}\n"
                else:
                    system_message_content += f"{i}. {entry}\n"
        else:
            system_message_content += "No long-term memory entries available.\n"

        structured_memory["system_context"] = system_message_content

        short_term_memory_by_tag = memory_structure.get("short_term", {})

        all_short_term_entries = []
        for tag, entries_list in short_term_memory_by_tag.items():
            if isinstance(entries_list, list):
                for entry in entries_list:
                    entry_with_tag = entry.copy()
                    entry_with_tag['original_tag'] = tag
                    all_short_term_entries.append(entry_with_tag)
            else:
                print(f"Warning: Unexpected short_term memory format for tag '{tag}'. Expected list, got {type(entries_list)}.")

        all_short_term_entries.sort(key=lambda x: (x.get('timestamp', 0), x.get('unique_id', '')))

        for entry in all_short_term_entries:
            text_or_object = entry["content"]
            key_tag = entry["original_tag"]

            if key_tag in ["system", "tool"]:
                if isinstance(text_or_object, dict) and text_or_object.get("type") == "tool_batch":
                    structured_memory["conversation_history"].append(text_or_object)
                elif isinstance(text_or_object, dict) and "function_name" in text_or_object and "result" in text_or_object:
                    legacy_call = {
                        "function_name":     text_or_object.get("function_name"),
                        "arguments":         text_or_object.get("arguments", {}),
                        "result":            str(text_or_object.get("result", "")),
                        "call_id":           text_or_object.get("call_id"),
                        "thought_signature": text_or_object.get("thought_signature"),
                    }
                    structured_memory["conversation_history"].append({
                        "type":  "tool_batch",
                        "calls": [legacy_call],
                    })
            else:
                role = key_tag
                valid_roles = ["user", "assistant"]
                if role in valid_roles:
                    structured_memory["conversation_history"].append({
                        "type":    role,
                        "content": str(text_or_object)
                    })
                else:
                    print(f"Warning: Unexpected role '{role}' from tag '{key_tag}'. Treating as 'user'.")
                    structured_memory["conversation_history"].append({
                        "type":    "user",
                        "content": f"[{role}]: {str(text_or_object)}"
                    })

        structured_memory_out = StructuredMemory(**structured_memory)
        return structured_memory_out

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def random_memory(self):
        random_data = self.deep_memory.random_access()
        return random_data

    def relevance_process(self):
        print("Relevance process is a placeholder and not currently active.")

    # ------------------------------------------------------------------
    # System / tool message summarization
    # ------------------------------------------------------------------

    def process_short_term_system(self) -> int: # TODO: Do we want to remove this?
        """
        Walks the short-term conversation timeline and summarizes system/tool
        messages that are both old (past system_line budget) and large
        (individually exceed system_summarize budget).

        Token counts are read from the stored 'token_count' field. After
        summarization the field is rewritten with the new, smaller count.
        """
        keep_tool_entry_count = 3
        memory_data = self._load_memory()
        if memory_data is None:
            return 0

        budgets = self.calc_budgets()

        # ── Step 1: collect and sort all short-term entries ───────────────────
        short_term_memory = memory_data.get("short_term", {})
        all_entries = []
        for tag, entries_list in short_term_memory.items():
            if isinstance(entries_list, list):
                for entry in entries_list:
                    entry['original_tag'] = tag
                    all_entries.append(entry)

        if not all_entries:
            return 0

        all_entries.sort(key=lambda x: x.get('timestamp', 0))

        # Identify the most-recent tool entries — always kept as-is
        tool_entry_indices = [
            i for i, e in enumerate(all_entries)
            if e.get('original_tag') in ['system', 'tool']
        ]
        safeguarded_indices = set(tool_entry_indices[-keep_tool_entry_count:]) if tool_entry_indices else set()

        # ── Step 2: walk the timeline ─────────────────────────────────────────
        cumulative_tokens = 0
        final_entries = []
        summarized_count = 0

        for idx, entry in enumerate(all_entries):
            start_token_position = cumulative_tokens
            content_data = entry.get("content", "")

            is_tool_batch = (
                entry.get('original_tag') in ['system', 'tool'] and
                isinstance(content_data, dict) and
                content_data.get("type") == "tool_batch"
            )
            is_legacy_tool = (
                entry.get('original_tag') in ['system', 'tool'] and
                isinstance(content_data, dict) and
                "result" in content_data and
                content_data.get("type") != "tool_batch"
            )
            is_structured_tool_message = is_tool_batch or is_legacy_tool
            is_safeguarded = idx in safeguarded_indices

            if is_structured_tool_message and not is_safeguarded:
                # Read stored token count — no re-tokenization needed here
                result_tokens = entry.get("token_count", 0)

                if (start_token_position > budgets["system_line"] and
                        result_tokens > budgets["system_summarize"]):

                    print(f"Tool/System message (ID: {entry.get('unique_id')}) at token position "
                          f"{start_token_position} is a candidate for summarization.")

                    # Build text to send to summarizer
                    if is_tool_batch:
                        result_parts = [str(c.get("result", "")) for c in content_data.get("calls", [])]
                        result_text = "\n---\n".join(result_parts)
                    else:
                        result_text = str(content_data.get("result", ""))

                    try:
                        summarized_content_raw = self.bot_instance.response_output(
                            system="You are a helpful assistant. Summarize the following tool output concisely, retaining key information:",
                            message=result_text
                        )

                        new_content = content_data.copy()
                        if is_tool_batch:
                            new_content["calls"] = [{
                                "function_name":     "summarized_batch",
                                "arguments":         {},
                                "result":            f"Summarized from original tool batch: {summarized_content_raw}",
                                "call_id":           None,
                                "thought_signature": None,
                            }]
                        else:
                            new_content["result"] = f"Summarized from original tool output: {summarized_content_raw}"

                        # Recompute and store the updated token count ──────────
                        new_token_count = self._count_entry_tokens(new_content)

                        summarized_entry = {
                            "timestamp":     entry.get("timestamp"),
                            "content":       new_content,
                            "unique_id":     entry.get("unique_id"),
                            "original_tag":  entry.get('original_tag'),
                            "token_count":   new_token_count,   # ← updated count
                        }

                        final_entries.append(summarized_entry)
                        summarized_count += 1
                        cumulative_tokens += new_token_count
                        continue

                    except Exception as e:
                        print(f"Error during summarization: {e}. Keeping original message.")

            # ── Pass-through: use stored count for timeline arithmetic ────────
            final_entries.append(entry)
            cumulative_tokens += entry.get("token_count", 0)

        # ── Step 3: rebuild and save if anything changed ──────────────────────
        if summarized_count > 0:
            print(f"Summarized {summarized_count} system/tool message(s). Rebuilding memory.")

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

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    def _archive_memory(self, memory_data, trigger_type):
        """
        Archives the current memory state to a timestamped file.
        """
        if not hasattr(self, 'sub_directory') or not self.sub_directory:
            print("Warning: self.sub_directory not set. Archiving in default 'memory_archive' folder.")
            main_directory = "."
        else:
            main_directory = self.sub_directory

        archive_full_path = os.path.join(main_directory, "memory_archive")
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

    # ------------------------------------------------------------------
    # Main memory check + summarization + purge
    # ------------------------------------------------------------------

    def check(self):
        """
        Checks memory token totals against budgets, triggers AI summarization
        when thresholds are reached, and purges older entries keeping the most
        recent ones within the retention budget.

        All token arithmetic reads from stored 'token_count' fields — no
        tokenizer API calls happen here.
        """
        if not self.bot_instance:
            print("Memory Check skipped: ai_bot_instance not available for summarization.")
            return

        memory_data = self._load_memory()
        if memory_data is None:
            print("Memory Check skipped: Failed to load memory data.")
            return

        print("\n--- Running Memory Check ---")
        budgets = self.calc_budgets()
        needs_save = False

        # ── Short-Term Memory Check ───────────────────────────────────────────
        token_count = self.current_memory_tokens("short_term")

        if token_count >= budgets["short_term_threshold"]:
            message = f"\n--- Short-Term Memory Check Triggered ({token_count} >= {budgets['short_term_threshold']}) ---"
            print(message)
            self.text_capture.dump_text(message)

            self._archive_memory(memory_data, "short_term")

            if self.deep_memory_flag:
                self.create_deep_memory()

            # Collect and sort all short-term entries chronologically
            all_short_term_entries = []
            for tag, entries_list in memory_data.get("short_term", {}).items():
                if not isinstance(entries_list, list):
                    continue
                for entry in entries_list:
                    if not (isinstance(entry, dict) and "content" in entry and "timestamp" in entry):
                        continue
                    all_short_term_entries.append({
                        "timestamp":      entry["timestamp"],
                        "unique_id":      entry.get("unique_id", str(uuid.uuid4())),
                        "original_tag":   tag,
                        "original_entry": entry,
                        "token_count":    entry.get("token_count", 0),   # ← from stored field
                        # text_for_ai is only used for the summarization prompt, not for token accounting
                        "text_for_ai":    f"[{tag.upper()}] {json.dumps(entry['content']) if isinstance(entry['content'], dict) else str(entry['content'])}",
                    })

            all_short_term_entries.sort(key=lambda x: x["timestamp"])

            # Build the summarization prompt from chronological content
            structured_short_term_for_ai = "\n".join([item["text_for_ai"] for item in all_short_term_entries])
            print(f"Summarizing short-term memory (Tokens: {token_count})...")

            summarized_content_raw = self.bot_instance.response_output(
                system=short_term_prompt,
                message="Summarize this: \n" + structured_short_term_for_ai,
            )
            message = f"Short-term memory summarized to: {summarized_content_raw}"
            print(message)
            self.text_capture.dump_text(message)

            if "long_term" not in memory_data or not isinstance(memory_data["long_term"], list):
                memory_data["long_term"] = []

            summary_timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            summary_text = f"[{summary_timestamp_str}] Summary of recent activity: {summarized_content_raw}"
            memory_data["long_term"].append({
                "timestamp":   int(time.time()),
                "content":     summary_text,
                "token_count": self.token_manager.count_tokens(summary_text),
            })
            needs_save = True

            # ── Retain the most recent entries within the retention budget ────
            # Always keep at least the single most-recent entry (mirrors long-term behaviour).
            entries_to_keep = []
            current_retained_tokens = 0

            for entry_item in reversed(all_short_term_entries):
                entry_tokens = entry_item["token_count"]

                if (current_retained_tokens + entry_tokens <= budgets["short_term_retain"]
                        or len(entries_to_keep) == 0):          # ← guard: always keep newest
                    entries_to_keep.append(entry_item)
                    current_retained_tokens += entry_tokens
                else:
                    break

            entries_to_keep.reverse()

            new_short_term_memory = {"user": [], "assistant": [], "system": [], "tool": []}
            for item in entries_to_keep:
                tag = item["original_tag"]
                if tag in new_short_term_memory:
                    new_short_term_memory[tag].append(item["original_entry"])

            memory_data["short_term"] = new_short_term_memory
            print(f"Short-term memory purged, keeping {len(entries_to_keep)} entries ({current_retained_tokens} tokens).")

        # ── Long-Term Memory Check ────────────────────────────────────────────
        long_term_token_count = self.current_memory_tokens("long_term")

        if long_term_token_count >= budgets["long_term_threshold"]:
            message = f"\n--- Long-Term Memory Check Triggered ({long_term_token_count} >= {budgets['long_term_threshold']}) ---"
            print(message)
            self.text_capture.dump_text(message)

            self._archive_memory(memory_data, "long_term")

            # Build prompt text from long-term entries (new dict or legacy string)
            long_term_entries = memory_data.get("long_term", [])
            long_term_content_for_ai = "\n".join(
                e.get("content", "") if isinstance(e, dict) else str(e)
                for e in long_term_entries
            )
            print(f"Summarizing long-term memory (Tokens: {long_term_token_count})...")

            summarized_content_raw = self.bot_instance.response_output(
                system=long_term_prompt,
                message=long_term_content_for_ai
            )

            message = f"Long-term memory summarized to base memory: {summarized_content_raw}"
            print(message)
            self.text_capture.dump_text(message)

            new_base_memory_summary = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Comprehensive summary of past long-term memory: {summarized_content_raw}"
            )

            # Parse all long-term entries to their timestamps for sorting
            parsed_long_term = []
            entry_pattern = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', re.DOTALL)

            for entry in long_term_entries:
                if isinstance(entry, dict):
                    parsed_long_term.append({
                        "timestamp":   entry.get("timestamp", 0),
                        "entry":       entry,
                        "token_count": entry.get("token_count", 0),
                    })
                else:
                    # Legacy plain string — parse timestamp from text
                    match = entry_pattern.match(str(entry))
                    ts = (datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S').timestamp()
                          if match else datetime.now().timestamp())
                    text = str(entry)
                    parsed_long_term.append({
                        "timestamp":   ts,
                        "entry":       {"timestamp": ts, "content": text,
                                        "token_count": self.token_manager.count_tokens(text)},
                        "token_count": self.token_manager.count_tokens(text),
                    })

            parsed_long_term.sort(key=lambda x: x["timestamp"])

            # Retain the most recent entries within the long-term retention budget.
            # Always keep at least the single most-recent entry.
            kept_long_term_entries = []
            current_retained_tokens = 0
            retain_budget = budgets["long_term_retain"]

            for entry_item in reversed(parsed_long_term):
                entry_tokens = entry_item["token_count"]

                if (current_retained_tokens + entry_tokens <= retain_budget
                        or len(kept_long_term_entries) == 0):   # ← guard: always keep newest
                    kept_long_term_entries.append(entry_item)
                    current_retained_tokens += entry_tokens
                else:
                    break

            kept_long_term_entries.reverse()
            new_long_term_list = [item["entry"] for item in kept_long_term_entries]

            memory_data["long_term"] = new_long_term_list
            memory_data["base_memory"] = {
                "content":     new_base_memory_summary,
                "token_count": self.token_manager.count_tokens(new_base_memory_summary),
            }
            print(f"Long-term memory purged, keeping {len(new_long_term_list)} entries "
                  f"({current_retained_tokens} tokens). Summary moved to base memory.")
            needs_save = True

        if needs_save:
            self._save_memory(memory_data)
            print("Memory state saved after summarization/purging.")
        else:
            print("No memory thresholds reached. No changes made.")

    # ------------------------------------------------------------------
    # Deep memory
    # ------------------------------------------------------------------

    def create_deep_memory(self):
        """Triggers creation/update of deep memory (NER, embeddings, etc.)."""
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