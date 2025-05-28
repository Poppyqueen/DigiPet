# an endpoint for an AI agent 


import os
import sys
import subprocess
import sys # Often needed for standard streams


# Import AI framework

from inventory_items.inventory_manager import InventoryHouseManager
from memory.memory_handle import memory_manager # Assuming this is the correct import for your memory class
from ai_managers.ai_handle import ai_bot # Assuming this is the correct import for your AI class
from tools.tools_builder.construct_tools import FunctionBuilder
# Import Utils
from utils.capture_text import TextCapture # Import the text capture class

# NEW: Import TTS Providers
from tts_providers.base_tts_provider import BaseTTSProvider
from tts_providers.macos_say_provider import MacOSSaiProvider
from tts_providers.espeak_ng_provider import ESpeakNGProvider

# Define default filepaths (these are just the base names now)
DEFAULT_MEMORY_DB = "cli_memory.json"
DEFAULT_DEEP_MEMORY_DB = "cli_deep_memory.json"
DEFAULT_AI_LOG = "cli_ai_log.txt"
DEFAULT_INVENTORY_FOLDER = "inventory" # Assuming you have an inventory subdirectory

class CLIChatbot:
    # MODIFIED: Changed tts_flag to tts_provider_id
    def __init__(self, system_prompt="You are a helpful assistant.", sub_directory="default_convo", deep_memory=False, base_model="gpt-4.1-nano", select_memory_model="gpt-4.1-nano", tts_provider_id: str | None = None, signal_callback=None, voice=None, lang="en"):
        """Initialize the CLI chatbot with AI bot and memory systems."""
        # --- Use the subdirectory structure ---
        # Ensure the directory exists
        os.makedirs(sub_directory, exist_ok=True) # Ensure the target directory is created

        # Construct full paths within the subdirectory
        memory_filepath = os.path.join(sub_directory, DEFAULT_MEMORY_DB)
        deep_memory_filepath = os.path.join(sub_directory, DEFAULT_DEEP_MEMORY_DB)
        ai_data_filepath = os.path.join(sub_directory, DEFAULT_AI_LOG)
        inventory_filepath = os.path.join(sub_directory, DEFAULT_INVENTORY_FOLDER) # Assuming you have an inventory subdirectory
        # --- End subdirectory structure ---
        self.sys_prompt = system_prompt
        self.deep_memory_flag = deep_memory
        self._signal_callback = signal_callback # Store the callback

        # Add a recursion depth limit to prevent infinite loops
        self.max_recursion_depth = 10 # Allow up to 10 consecutive AI calls (including function calls and final response)

        # REMOVED: self.tts = tts_flag
        self.last_response = None # Store the last response for potential use

        # NEW: TTS Provider Initialization
        self.tts_provider: BaseTTSProvider | None = None
        if tts_provider_id:
            if tts_provider_id == "macos_say":
                self.tts_provider = MacOSSaiProvider(signal_callback=self._signal_callback)
            elif tts_provider_id == "espeak_ng":
                self.tts_provider = ESpeakNGProvider(signal_callback=self._signal_callback, voice_name=voice)

            # Add more elifs here for other providers as they are created
            else:
                print(f"Warning: Unknown TTS provider ID '{tts_provider_id}'. TTS will be disabled.")
                self.tts_provider = None
        
        if self.tts_provider and not self.tts_provider.is_available():
            print(f"Warning: Selected TTS provider '{tts_provider_id}' is not available on this system. TTS will be disabled.")
            self.tts_provider = None


        try:
            # Initialize with the full paths
            self.text_capture = TextCapture(filepath=ai_data_filepath)  # Initialize text capture

            self.memory = memory_manager(
                filepath=memory_filepath,
                deep_memory_filepath=deep_memory_filepath,
                deep_memory=deep_memory, # Pass the deep memory flag
                text_capture=self.text_capture,
                sub_directory=sub_directory
            )
            # Add tools that need usage of the memory structure

            self.state_manager=InventoryHouseManager(inventory_filepath, self._signal_callback, self.memory)

            self.functions_builder = FunctionBuilder(state_manager=self.state_manager, signal=self._signal_callback, subdirectory=sub_directory, memory_manager=self.memory)  # Initialize the function builder

            self.ai = ai_bot(data_filepath=ai_data_filepath, act_model=base_model, functions_builder=self.functions_builder, state_manager=self.state_manager, signal=self._signal_callback, memory_manager=self.memory) # 4.1-nano is the newest widely available model
            # REMOVED: self.tts = tts_flag # Set to True if you want to enable text-to-speech output
            # REMOVED: self._current_tts_process = None


        except ImportError as e:
             print(f"FATAL: Could not import dependencies ({e}). Ensure ai_handle.py and memory_handle.py exist.")
             sys.exit(1)
        except Exception as e:
            # Print the full traceback for better debugging if needed
            import traceback
            traceback.print_exc()
            print(f"FATAL: Could not initialize AI or Memory systems ({e}). Exiting.")
            sys.exit(1)

        self.running = True
        #self.clear_screen()

    def _send_signal(self, signal_data):
        if self._signal_callback:
            print(f"Chatbot signaling: {signal_data}")
            self._signal_callback(signal_data)
        else:
            print(f"Chatbot attempted to signal, but no callback registered: {signal_data}")


    def get_room_name_out(self, id):
        """
        Returns the name of the room tied to the ID passed
        """
        return self.state_manager.get_room_name(id)
    def get_current_location(self):
        """
        Returns the name of the current room, or an error string if current room is invalid.
        """
        return self.state_manager.get_current_room_name()

    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')


    async def _get_ai_response_sequence(self, current_mem_structure: dict, current_full_prompt: str, depth: int = 0) -> str:
        """
        Recursively gets responses from the AI, handling function calls until a text response is received.

        Args:
            current_mem_structure: The current memory structure to pass to the AI.
            current_full_prompt: The full system/user prompt for the AI to consider.
            depth: Current recursion depth (internal counter to prevent infinite loops).

        Returns:
            The final text response from the AI after processing any function calls.
            Returns an error message string if max depth is reached or an error occurs.
        """
        if depth >= self.max_recursion_depth:
            print(f"\n⚠️ Warning: Max recursion depth ({self.max_recursion_depth}) reached.")
            stats_to_monitor = ["fullness", "hydration", "energy"]
            #  Decrease the stats
            # Decrease stats each function call set
            for stat_name in stats_to_monitor:
                self.state_manager.adjust_stat(stat_name, -10)

            self.memory.save_to_memory(f"\n⚠️ Warning: Max recursion depth ({self.max_recursion_depth}) You have been heavily penalized with some of your wellness stats", "short_term", "system")
            #self.memory.save_to_memory(f"\n⚠️ Warning: Max recursion depth ({self.max_recursion_depth}) reached. Do not output any more functions.", "short_term", "system")
            return "Error: Max recursion depth reached while processing AI response chain."

        print(f"\n🤖 Thinking... (Call Depth: {depth})") # Added depth indicator

        try:


            # Call the AI with the current memory state and prompt
            # Ensure mem_structure is passed correctly (should be a dictionary)

            # This function is the main API call, it sends the information necesary, returns a stringed response for any tool calls if any were made
            # Returns a function_flag if any message was a tool call, for us to process here
            function_flag, response_content = await self.ai.adventure_response(
                current_mem_structure if isinstance(current_mem_structure, dict) else {},
                current_full_prompt, depth, self.max_recursion_depth
            )


            # add a deep memory search here to enhance the system context with relevant entries to the events in the chain of tool calls?
            # 2. Search Deep Memory based on current context (from the latest function call)
            # (This system needs improvements, and I am not sure if it improves or worsens the system)
            #print("Searching deep memory for relevant context...") # Redundant print
            deep_memory_context = ""
            if self.deep_memory_flag:
                # search_deep_memory is assumed to return List[str]
                found_excerpts_list = self.memory.search_deep_memory()
                if found_excerpts_list:
                    # Deduplicate using a set
                    unique_excerpts_list = list(set(found_excerpts_list))

                    print(f"Found {len(unique_excerpts_list)} relevant excerpts (after deduplication).")
                    # Create a formatted string with a clear header
                    deep_memory_context = "\n\nRelevant information from deep memory:\n"
                    deep_memory_context += "\n".join([f"- {excerpt}" for excerpt in unique_excerpts_list])
                    # Add the random excerpts to the context *only if deep memory is enabled*
                    deep_memory_context += "\n\n"
                    print(f"Deep memory context inside tools: {deep_memory_context}")
                else:
                    print("No relevant excerpts found.")

            if function_flag:
                print("*** Function call, decreasing wellness stats")
                stats_to_monitor = ["fullness", "hydration", "energy"]
                #  Decrease the stats
                # Decrease stats each function call set
                for stat_name in stats_to_monitor:
                    self.state_manager.adjust_stat(stat_name, -.1)
                    print(f"decreased stat: {stat_name} by: 1")

                print(f"⚙️ Function call detected (Depth: {depth}). Processing...")
                self.text_capture.dump_text(f"Function Call (Depth {depth}):")
                self.text_capture.dump_text(f"{response_content}") # response_content contains the function call payload
                self.text_capture.dump_text(f"**************")


            # Change this, we will pass the recursion depth to adventure response, and remove tools from it when we reach a limit

                # depth_message=""
                # if depth == self.max_recursion_depth-3:
                #     depth_message="Depth of function calling reached the limit, your next message must not contain any function call."

                # elif depth >= self.max_recursion_depth/2:
                #     depth_message="Depth of function calling reached half way to the limit, please consider outputting your final message"

                function_result = f"Function response: {response_content}" # Assuming response_content is the function output/confirmation


                # If deep memory active, we add the retrieved memories from it and append it to the function result of the agent.
                if self.memory.deep_memory and self.deep_memory_flag:
                    function_result = f"Deep memories retrieved: {deep_memory_context} Function response: {response_content}, Depth: {depth}" # Assuming response_content is the function output/confirmation

                # Save the function *result* to memory so the AI can see it
                # Use 'system' or similar role if your AI model supports it,

                print(f"DEBUG: We are sending this as the tool call response: {function_result}")

                # We have changed this to the system tag
                self.memory.save_to_memory(function_result, "short_term", "system")
                print(f"✅ Saved function result to memory. Getting next AI response...")

                # Get the updated memory structure after saving the function result
                updated_mem_structure = self.memory.get_memory_structure()
                if updated_mem_structure is None:
                     print("Error: Could not load updated main memory structure after function call. Proceeding with potentially stale memory.")
                     updated_mem_structure = {} # Provide default empty fallback

                # Recursively call self to get the next response in the chain
                return await self._get_ai_response_sequence(updated_mem_structure, current_full_prompt, depth + 1)

            else:

                # Not a function call - this is the final text response
                print(f"✅ No function call detected (Depth: {depth}). This is the final response.")
                print("Cleaning context...") # Added context cleaning step
                self.text_capture.dump_text("*******")
                #self.text_capture.dump_text("Removing system messages from memory...") # Log the removal of system messages




                # Clean up tool context from memory after generating last response
                self.memory.process_short_term_system() # This now gives the system message a time-life to system messages of 1 tick in 'global' memory
                
                
                # Remove system messages from memories after tool process is done 

                # This creates an interesting effect, while it does help reduce tokenage usage, the information in system context is a lot
                # of the times lost and does not get into regular system processing. 
                # An specific example, room IDs, the system agent will manage to get this information, but the main agent doesn't broadcast
                # back the IDs out of system messages, an the IDs are then lost and never "learnt", as they are removed from context
                # maybe with better prompting this could be kept, but it seems better to simply keep the system messages to enter into long term memories

                # For now we will keep removing them, it is just much more optimized, and prompting will probs fix it

                # Probably some prompt telling the agent to always verbalize specific and functional learnt knowledge 
                # The memory summarizer might also need some more prompting



                self.text_capture.dump_text("*******")
                # This is optional but keeps the token usage low and context clean


                #print(f"\n🤖 Response:\n{response_content}")



                self.text_capture.dump_text(f"AI Response (Depth {depth}):")
                self.text_capture.dump_text(f"{response_content}") # response_content is the text response
                self.text_capture.dump_text(f"**************")


                # Save the final AI text response to memory
                self.memory.save_to_memory(response_content, "short_term", "assistant")
                #print(f"Saved final AI response to short-term memory.") # Redundant print

                # Return the final text response
                return response_content

        except Exception as e:
            print(f"\n❌ Error generating response during sequence (Depth {depth}): {e}")
            # Log the error in text capture as well
            self.text_capture.dump_text(f"Error during AI response sequence (Depth {depth}): {e}")
            self.text_capture.dump_text(f"**************")
            return f"Error generating response: {e}" # Return error message

    def add_items_room(self, room_id, item):
        result = self.state_manager.create_item("room", room_id ,item)
        room_name = self.state_manager.get_room_name(room_id)
        #self.memory.save_to_memory(f"A package of helpful items has been delivered for you in the room {room_name}! Enjoy.", "short_term", "system")
        return result



    # --- NEW: Pet Theme Color Bridge Methods ---

    def get_pet_color(self) -> tuple[int, int, int] | None:
        """Bridge to InventoryHouseManager.get_pet_color()."""
        if self.state_manager: # Defensive check
            return self.state_manager.get_pet_color()
        return (100, 255, 100) # Fallback default if manager isn't ready

    def set_pet_color(self, color: tuple[int, int, int]):
        """Bridge to InventoryHouseManager.set_pet_color()."""
        if self.state_manager: # Defensive check
            self.state_manager.set_pet_color(color)
            # Optional: send a signal? Maybe not needed, game.py updates state directly
            # self._signal_callback({"type": "pet_color_changed", "color": color})


    def is_color_configured(self) -> bool:
        """Bridge to InventoryHouseManager.is_color_configured()."""
        if self.state_manager: # Defensive check
            return self.state_manager.is_color_configured()
        return False # Default to not configured if manager isn't ready


    def set_color_configured(self, configured: bool):
        """Bridge to InventoryHouseManager.set_color_configured()."""
        if self.state_manager: # Defensive check
            self.state_manager.set_color_configured(configured)

    # MODIFIED: Refactored to use TTS Provider
    def process_response_with_tts(self, final_ai_response):
        """
        Processes the AI response, including TTS if enabled, stopping
        any existing TTS process first using the active TTS provider.
        """
        if self.tts_provider and self.tts_provider.is_available():
            # Stop any currently playing speech before starting a new one
            self.tts_provider.stop()
            # Start new speech synthesis
            self.tts_provider.synthesize(final_ai_response)
        else:
            # If TTS is not enabled or not available, ensure no lingering process from a previous run
            if self.tts_provider:
                self.tts_provider.stop() # Even if not available, ensure internal process is cleaned up


    async def process_input(self, message, role="user"):
        """Process user input and generate AI response."""
        joined_random_entity = ""

        # Capture  input to logger
        self.text_capture.dump_text(f"{role}:")
        self.text_capture.dump_text(f"{message}")
        self.text_capture.dump_text(f"**************")

        # 1. Save  input to short-term memory
        self.memory.save_to_memory(message, "short_term", f"{role}")

        # 2. Search Deep Memory based on current context (before generating response)
        deep_memory_context = ""
        if self.deep_memory_flag:
            found_excerpts_list = self.memory.search_deep_memory()
            if found_excerpts_list:
                unique_excerpts_list = list(set(found_excerpts_list))

                print(f"Found {len(unique_excerpts_list)} relevant excerpts (after deduplication).")
                deep_memory_context = "\n\nRelevant information from deep memory:\n"
                deep_memory_context += "\n".join([f"- {excerpt}" for excerpt in unique_excerpts_list])
                deep_memory_context += joined_random_entity
                deep_memory_context += "\n\n"
            else:
                print("No relevant excerpts found.")

        # 3. Get current standard memory structure
        mem_structure = self.memory.get_memory_structure() # This structure should include the user input we just added
        if mem_structure is None:
             print("Error: Could not load main memory structure. Proceeding without it.")
             mem_structure = {"short_term": {}, "long_term": [], "base_memory": ""} # Provide default empty

        # 4. Construct the dynamic prompt including deep memory context
        tools_context=self.functions_builder.construct_context()

        base_prompt = self.sys_prompt
        full_prompt = base_prompt + tools_context
        if deep_memory_context:
             full_prompt += f"\n\n{deep_memory_context}\nUse any relevant information above to inform your response."

        steps=self.get_steps()

        full_prompt += f"\n\n You have been in your digital home for: {steps} steps. Your own size is relative to this!"

        # 5. Get AI response (now handled recursively)
        final_ai_response = await self._get_ai_response_sequence(
            mem_structure if isinstance(mem_structure, dict) else {},
            full_prompt
        )

        self.add_steps(1) # add a step to the counter


# --- wellness stats check -----

        stats_to_monitor = ["fullness", "hydration", "energy"]
        low_threshold = 10
        recovery_amount = 40

        # 1. Decrease the stats
        for stat_name in stats_to_monitor:
            self.state_manager.adjust_stat(stat_name, -1)

        # 2. Get the *updated* stats dictionary using the helper
        stats_data = self.state_manager.get_stats(True) # Assuming get_stats is a method of state_manager

        # 3. Check if any of the monitored stats are below the threshold
        low_stat_detected = False
        if stats_data is not None:
            for stat_name in stats_to_monitor:
                current_value = stats_data.get(stat_name, float('inf'))

                if current_value <= low_threshold:
                    low_stat_detected = True
                    break
        else:
            print("Warning: Could not retrieve valid stats data to check thresholds.")


        # 4. If a low stat was detected, perform the consequences
        if low_stat_detected:
            self._send_signal({"type": "sleep", "duration": 900})
            self.memory.save_to_memory("You passed out! Be more careful with your basic necessities.", "short_term", "system")
            self.memory.save_to_memory("After 15 minutes you wake up on the exact same spot you fainted, still feeling weak.", "short_term", "system")

            # 5. Increase the stats for recovery if passed out
            for stat_name in stats_to_monitor:
                self.state_manager.adjust_stat(stat_name, recovery_amount)

            print("AI agent passed out")


# --- extra part of the function -----


        # 6. Perform memory check (summarization, purging)
        print("Performing memory check...")
        self.last_response = final_ai_response # Store the last response for potential TTS

        # MODIFIED: Calling the new process_response_with_tts
        self.process_response_with_tts(final_ai_response)

        self.memory.check()
        
        return final_ai_response # Return the final text response


# Bridge to inventory manager

    def get_steps(self):
        return self.state_manager.get_steps()
    
    def set_steps(self, count: int):
        return self.state_manager.set_steps(count)
    
    def add_steps(self, amount: int):
        return self.state_manager.add_steps(amount)

    def get_wellness_states(self):
        return self.state_manager.get_stats(True)

    def get_inventories(self):
        """
        Delegated.
        Lists the items in the current room and inventory
        Returns:
            list_room_items_names, list_inventory_item_names
        """
        return self.state_manager.list_inventories()

    def add_message_out(self, message, role):
        self.memory.save_to_memory(message, "short_term", f"{role}")
        return
    
    def run(self):
        """loop for the chatbot as a CLI"""
        try:
            while self.running:
                # Get user input
                user_input = input("\n💬 You: ").strip()

                # Check if input is empty
                if not user_input:
                    continue

                # Handle special commands
                if self.handle_special_commands(user_input):
                    print("-" * 60) # Separator after command execution
                    continue

                # Process regular chat input
                # The process_input method now handles the recursive AI calls
                # and prints the final response itself.
                # We can store the final response if needed, but printing is done inside.
                self.process_input(user_input) # This is async, but run() isn't. In a CLI, this is typically fine.
                                                # For a real async loop (e.g., with asyncio), you'd await it.
                                                # For simple CLI demo, synchronous call is OK.
                print("-" * 60) # Separator after response

        except KeyboardInterrupt:
            print("\n\nProgram interrupted by user. Exiting gracefully...")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            import traceback
            traceback.print_exc() # Print traceback for unexpected errors
        finally:
            print("\nThank you for using the Memory-Enabled AI Chatbot!")
            self.shutdown() # Ensure shutdown is called on exit

    def shutdown(self):
        # NEW: Ensure the TTS provider's process is stopped on shutdown
        if self.tts_provider:
            self.tts_provider.stop()

        if self.state_manager:
            self.state_manager.save_state()
        # REMOVED: self._current_tts_process.kill()


def main():
    """Examply entry point for the application."""
    # This example demonstrates a synchronous CLI chat.
    # If you intend to use `process_input` in an async context (e.g., a web server),
    # you would need to run the main loop with `asyncio.run()`.
    import asyncio # Import asyncio for demonstration if you want to run sync code with an async method

    # Example usage: set deep_memory=True to enable
    # MODIFIED: Changed tts_flag to tts_provider_id
    # To use macOS 'say': tts_provider_id="macos_say"
    # To use eSpeak NG: tts_provider_id="espeak_ng" (ensure espeak-ng is installed)
    # To disable TTS: tts_provider_id=None (or any unrecognized string)
    
    # Example for testing with a specific provider:
    # chatbot = CLIChatbot(
    #     system_prompt="You are a unique and independent digital entity. You can process function calls if needed.",
    #     sub_directory="base_bot",
    #     deep_memory=False,
    #     base_model="gpt-4.1-mini",
    #     select_memory_model="gpt-4.1-mini",
    #     tts_provider_id="macos_say" # or "espeak_ng"
    # )

    # To run a single async message:
    # async def run_single_message():
    #     chatbot = CLIChatbot(
    #         system_prompt="You are a unique and independent digital entity. You can process function calls if needed.",
    #         sub_directory="base_bot",
    #         deep_memory=False,
    #         base_model="gpt-4.1-mini",
    #         select_memory_model="gpt-4.1-mini",
    #         tts_provider_id="macos_say" # or "espeak_ng"
    #     )
    #     print("Sending initial message...")
    #     response = await chatbot.process_input("Hello! How are you today?")
    #     print(f"Bot's initial response: {response}")
    #     chatbot.shutdown() # Ensure shutdown on single message completion
    #
    # asyncio.run(run_single_message())


    # To use the chatbot with CLI (this will still work synchronously for input/output,
    # but the internal async calls will implicitly run if not explicitly awaited in the loop context)
    # For robust async CLI, you'd integrate an async event loop (like asyncio.run in a wrapper).
    # For this current CLI `run` method, `await` is not used directly, which means the process_input
    # will run, but `await` inside it will create a "nested" event loop if not already in one.
    # This is a common pattern for "hybrid" sync/async applications.

    # Recommended way to run a CLI that uses async methods:
    async def cli_main_async():
        chatbot = CLIChatbot(
            system_prompt="You are a unique and independent digital entity. You can process function calls if needed.",
            sub_directory="base_bot",
            deep_memory=False,
            base_model="gpt-4.1-mini",
            select_memory_model="gpt-4.1-mini",
            tts_provider_id="macos_say" # Set to "macos_say", "espeak_ng", or None
        )
        # We start the chatbot loop from within an async function
        # This will allow `await` inside process_input to work correctly.
        try:
            while chatbot.running:
                user_input = input("\n💬 You: ").strip()
                if not user_input:
                    continue
                if chatbot.handle_special_commands(user_input):
                    print("-" * 60)
                    continue
                # Await the async process_input call
                await chatbot.process_input(user_input)
                print("-" * 60)
        except KeyboardInterrupt:
            print("\n\nProgram interrupted by user. Exiting gracefully...")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\nThank you for using the Memory-Enabled AI Chatbot!")
            chatbot.shutdown()

    asyncio.run(cli_main_async())


if __name__ == "__main__":
    main()