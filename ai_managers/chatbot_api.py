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




# Define default filepaths (these are just the base names now)
DEFAULT_MEMORY_DB = "cli_memory.json"
DEFAULT_DEEP_MEMORY_DB = "cli_deep_memory.json"
DEFAULT_AI_LOG = "cli_ai_log.txt"
DEFAULT_INVENTORY_FOLDER = "inventory" # Assuming you have an inventory subdirectory

class CLIChatbot:
    def __init__(self, system_prompt="You are a helpful assistant.", sub_directory="default_convo", deep_memory=False, base_model="gpt-4.1-nano", select_memory_model="gpt-4.1-nano", tts_flag=False, signal_callback=None):
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

        self.tts = tts_flag # Set to True if you want to enable text-to-speech output
        self.last_response = None # Store the last response for potential use

        try:
            # Initialize with the full paths
            # Ensure your ai_bot supports act_model="gpt-4.1-nano" or change it
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

            #self.blsk=bluesky_bot()

            self.functions_builder = FunctionBuilder(state_manager=self.state_manager, signal=self._signal_callback, subdirectory=sub_directory)  # Initialize the function builder

            self.ai = ai_bot(data_filepath=ai_data_filepath, act_model=base_model, memory_model=select_memory_model, functions_builder=self.functions_builder, state_manager=self.state_manager, signal=self._signal_callback) # 4.1-nano is the newest widely available model
            self.tts = tts_flag # Set to True if you want to enable text-to-speech output

            self._current_tts_process = None


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


    def _get_ai_response_sequence(self, current_mem_structure: dict, current_full_prompt: str, depth: int = 0) -> str:
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
            self.memory.save_to_memory(f"\n⚠️ Warning: Max recursion depth ({self.max_recursion_depth}) reached. Do not output any more functions.", "short_term", "system")
            return "Error: Max recursion depth reached while processing AI response chain."

        print(f"\n🤖 Thinking... (Call Depth: {depth})") # Added depth indicator

        try:


            # Call the AI with the current memory state and prompt
            # Ensure mem_structure is passed correctly (should be a dictionary)

            # This function is the main API call, it sends the information necesary, returns a stringed response for any tool calls if any were made
            # Returns a function_flag if any message was a tool call, for us to process here
            function_flag, response_content = self.ai.adventure_response(
                current_mem_structure if isinstance(current_mem_structure, dict) else {},
                current_full_prompt
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

            # else: # Redundant print
            #    print("Deep Memory system not initialized, skipping search.")




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


                depth_message=""
                if depth == self.max_recursion_depth-3:
                    depth_message="Depth of function calling reached the limit, your next message must not contain any function call."

                elif depth >= self.max_recursion_depth/2:
                    depth_message="Depth of function calling reached half way to the limit, please consider outputting your final message"

                function_result = f"Function response: {response_content}, Depth: {depth}, {depth_message}" # Assuming response_content is the function output/confirmation


                # If deep memory active, we add the retrieved memories from it and append it to the function result of the agent.
                if self.memory.deep_memory and self.deep_memory_flag:
                    function_result = f"Deep memories retrieved: {deep_memory_context} Function response: {response_content}, Depth: {depth}, {depth_message}" # Assuming response_content is the function output/confirmation

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
                return self._get_ai_response_sequence(updated_mem_structure, current_full_prompt, depth + 1)

            else:

                # Not a function call - this is the final text response
                print(f"✅ No function call detected (Depth: {depth}). This is the final response.")
                print("Cleaning context...") # Added context cleaning step
                self.text_capture.dump_text("*******")
                #self.text_capture.dump_text("Removing system messages from memory...") # Log the removal of system messages




                # Clean up tool context from memory after generating last response
                self.memory.remove_system_short_term_memories() # Remove system messages from memories after tool process is done 

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

    def process_response_with_tts(self, final_ai_response):
        """
        Processes the AI response, including TTS if enabled, stopping
        any existing TTS process first.
    
        """
        # This works in the CLI in macos, however it needs a compatibility update, 
        # for the pygame implementation this could be managed with a signal and some kind of system
        # that creates an audio file to play it with pygame. Some clean-up would be needed with such an implementation

        if self.tts: # Check if TTS is enabled *first*
            if sys.platform == 'darwin': # Then check if the *correct* platform for 'say'
                try:
                    # 'say' command works on macOS
                    subprocess.run(['say', final_ai_response], check=True)
                except FileNotFoundError:
                    print("Error: 'say' command not found. Are you sure you are on macOS?")
                except Exception as e:
                     print(f"An error occurred while running 'say': {e}")

    def process_input(self, message, role="user"):
        """Process user input and generate AI response."""
        # Prepare random deep memory context if enabled

        joined_random_entity = ""
        # if self.deep_memory_flag:
        #     random_memory_data = self.memory.random_memory()

        #     # Validate random_memory_data and excerpts
        #     if isinstance(random_memory_data, dict):
        #          random_excerpts = random_memory_data.get("excerpts", [])
        #          if isinstance(random_excerpts, list):
        #             # print(f"Randomly selected entity: {random_memory_data.get('Named_Entity')}")
        #             # print(f"Excerpts: {random_excerpts}")
        #             joined_random_excerpts = "\n".join(random_excerpts)
        #             # Ensure Named_Entity is a string before formatting
        #             entity_name = str(random_memory_data.get('Named_Entity', 'Unknown Entity'))
        #             joined_random_entity = f"\nRandomly selected entity: {entity_name}\n{joined_random_excerpts}"
        #          else:
        #             print(f"Warning: Excerpts for entity '{random_memory_data.get('Named_Entity')}' is not a list: {random_excerpts}")
        #     else:
        #          print(f"Warning: random_memory() did not return a dictionary: {random_memory_data}")


        # Capture  input to logger
        self.text_capture.dump_text(f"{role}:")
        self.text_capture.dump_text(f"{message}")
        self.text_capture.dump_text(f"**************")

        # 1. Save  input to short-term memory
        # The most recent  input is saved into the memory structure, which then is used to generate the response automatically
        self.memory.save_to_memory(message, "short_term", f"{role}")
        #print(f"Saved  input to short-term memory.") # Redundant print

        # 2. Search Deep Memory based on current context (before generating response)
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
                deep_memory_context += joined_random_entity
                deep_memory_context += "\n\n"
            else:
                print("No relevant excerpts found.")
        # else: # Redundant print
        #    print("Deep Memory system not initialized, skipping search.")


        # 3. Get current standard memory structure
        # This initial structure includes the newly saved user input
        mem_structure = self.memory.get_memory_structure() # This structure should include the user input we just added
        if mem_structure is None:
             print("Error: Could not load main memory structure. Proceeding without it.")
             mem_structure = {"short_term": {}, "long_term": [], "base_memory": ""} # Provide default empty

        # 4. Construct the dynamic prompt including deep memory context


        tools_context=self.functions_builder.construct_context()


        base_prompt = self.sys_prompt
        full_prompt = base_prompt + tools_context
        if deep_memory_context:
            
             # Add deep memory context to the prompt
             full_prompt += f"\n\n{deep_memory_context}\nUse any relevant information above to inform your response."

        steps=self.get_steps()

        full_prompt += f"\n\n You have been in your digital home for: {steps} steps. Your own size is relative to this!"
        # Note: The memory structure itself is passed separately to the AI call (self.ai.adventure_response)
        # This deep_memory_context is added to the *prompt string* for models that can process it there.
        # Ensure your AI model's underlying implementation (`adventure_response`) correctly combines
        # the memory structure (likely as chat message history) and the full_prompt string.

        # 5. Get AI response (now handled recursively)
        # The recursive function prints intermediate steps and the final response,
        # and saves all intermediate function results and the final response to memory.


        final_ai_response = self._get_ai_response_sequence(
            mem_structure if isinstance(mem_structure, dict) else {},
            full_prompt
        )
        self.add_steps(1) # add a step to the counter


# --- wellness stats check -----

        # Adjust stats, reduce them a bit to introduce penalization per action 
        # we will implement whatever "penalization" is in here, 
        # here for the implementation of pygame we will send a signal to the pygame thread that is running this agent
        # there we will then simulate a "faint" for the agent, which will prevent autonomous actions of the agent for a set amount of time
        # while the pygame implementation is managing this timer, here, if we reach this point will just restore the stats a bit immediately,
        # we will also append a system message to the memory telling the agent that it fainted and for what reasons


        stats_to_monitor = ["fullness", "hydration", "energy"]
        low_threshold = 10
        recovery_amount = 40

        # 1. Decrease the stats
        # This loop is concise and correct for the decrease step
        for stat_name in stats_to_monitor:
            self.state_manager.adjust_stat(stat_name, -1)

        # 2. Get the *updated* stats dictionary using the helper
        # This gets the dictionary containing "fullness", "hydration", etc.
        # Returns None if state is corrupted or missing the 'stats' key
        stats_data = self.state_manager.get_stats(True) # Assuming get_stats is a method of state_manager

        # 3. Check if any of the monitored stats are below the threshold
        # We can only do this check if we successfully got the stats data
        low_stat_detected = False
        if stats_data is not None:
            for stat_name in stats_to_monitor:
                # Access the value from the stats_data dictionary returned by the helper
                # Use .get() for safety again, although _get_stats_data should validate keys
                current_value = stats_data.get(stat_name, float('inf'))

                if current_value <= low_threshold:
                    low_stat_detected = True
                    # Found one low stat, no need to check others
                    break
        else:
            # Handle the case where stats_data could not be retrieved/validated
            # Maybe log a warning or raise an error if this indicates a critical state issue
            print("Warning: Could not retrieve valid stats data to check thresholds.")


        # 4. If a low stat was detected, perform the consequences
        # This block only runs if stats_data was valid AND a stat was below threshold
        if low_stat_detected:
            # The original code sent the signal before saving the memory
            self._send_signal({"type": "sleep", "duration": 900})
            # Save memory message - now correctly only happens when passing out
            self.memory.save_to_memory("You passed out! Be more careful with your basic necessities.", "short_term", "system")
            self.memory.save_to_memory("After 15 minutes you wake up on the exact same spot you fainted, still feeling weak.", "short_term", "system")

            # 5. Increase the stats for recovery if passed out
            # The _get_stats_data check above didn't block this in the original logic flow
            for stat_name in stats_to_monitor:
                self.state_manager.adjust_stat(stat_name, recovery_amount)

            print("AI agent passed out")



# --- extra part of the function -----


        # 6. Perform memory check (summarization, purging)
        # This happens automatically based on thresholds in memory_manager
        # Perform this *after* the entire AI response sequence is complete
        print("Performing memory check...")
        self.last_response = final_ai_response # Store the last response for potential TTS
        self.memory.check()
        if self.tts:
            # --- 1. Check for and stop existing TTS process ---
            if self._current_tts_process is not None:
                # Use poll() to check if the process is still running.
                # poll() returns None if the process hasn't terminated yet.
                if self._current_tts_process.poll() is None:
                    print("Stopping previous 'say' process...")
                    try:
                        # Use terminate() to send a SIGTERM signal (graceful stop)
                        # Or use kill() to send a SIGKILL signal (forceful stop)
                        # kill() is often more reliable for simple command-line tools like 'say'
                        self._current_tts_process.kill()

                        # Optional: Give the process a moment to terminate gracefully
                        # self._current_tts_process.wait(timeout=1)

                    except ProcessLookupError:
                        # The process likely finished naturally between the poll() check
                        # and the kill() call. This is fine, just ignore the error.
                        pass
                    except Exception as e:
                        print(f"Error stopping previous process: {e}")

            # --- 2. Start the new TTS process ---
            print(f"Starting new 'say' process for: {final_ai_response[:50]}...") # Log start
            try:
                # Use subprocess.Popen to run the command in the background.
                # We store the Popen object so we can manage it later.
                self._current_tts_process = subprocess.Popen(
                    ['say', final_ai_response],
                    # Optional: Use DEVNULL to discard stdout/stderr if 'say'
                    # produces output you don't want in your console.
                    # stdout=subprocess.DEVNULL,
                    # stderr=subprocess.DEVNULL
                )
                # Do NOT call .wait() here, as that would make your program
                # pause until the TTS finishes, defeating the background goal.

            except FileNotFoundError:
                print("Error: 'say' command not found. Make sure you are on macOS.")
                self._current_tts_process = None # Clear the reference on failure
            except Exception as e:
                print(f"Error starting 'say' process: {e}")
                self._current_tts_process = None # Clear the reference on failure

        else: # If self.tts is False
            # If TTS is disabled, make sure to stop any currently running process
            if self._current_tts_process is not None:
                if self._current_tts_process.poll() is None:
                     print("TTS disabled, stopping current 'say' process...")
                     try:
                        self._current_tts_process.kill()
                        # self._current_tts_process.wait(timeout=1)
                     except ProcessLookupError:
                        pass
                     except Exception as e:
                         print(f"Error stopping process: {e}")

                self._current_tts_process = None # Clear the reference regardless

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
                self.process_input(user_input)
                print("-" * 60) # Separator after response

        except KeyboardInterrupt:
            print("\n\nProgram interrupted by user. Exiting gracefully...")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            import traceback
            traceback.print_exc() # Print traceback for unexpected errors
        finally:
            print("\nThank you for using the Memory-Enabled AI Chatbot!")

    def shutdown(self):
        self._current_tts_process.kill()


def main():
    """Examply entry point for the application."""


    # Example usage: set deep_memory=True to enable
    chatbot = CLIChatbot(
        system_prompt="You are a unique and independent digital entity. You can process function calls if needed.",
        sub_directory="base_bot", # Change this to your desired subdirectory
        deep_memory=False, # Set to True to test deep memory features
        base_model="gpt-4.1-mini", # Change to your desired base conversation model
        select_memory_model="gpt-4.1-mini", # Change to your desired model for memory
        tts_flag=True # Set to True to enable text-to-speech output (only macOS for now)
    )
    message=chatbot.process_input("Hello!") # To send an individual message to the bot, for use as an endpoint for the bot
    chatbot.run() # To use the chatbot with CLI

if __name__ == "__main__":
    main()