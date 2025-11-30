# main endpoint for an AI agent 


import os
import sys
import time

# Import AI framework

from inventory_items.inventory_manager import InventoryHouseManager
from ai_managers.agents.memory.memory_handle import memory_manager # Assuming this is the correct import for your memory class
from ai_managers.agents.ai_handle import ai_bot # Assuming this is the correct import for your AI class
from tools.tools_builder.construct_tools import FunctionBuilder
# Import Utils
from utils.capture_text import TextCapture # Import the text capture class

# NEW: Import TTS Providers
from tts_providers.base_tts_provider import BaseTTSProvider
from tts_providers.macos_say_provider import MacOSSaiProvider
from tts_providers.espeak_ng_provider import ESpeakNGProvider

from ai_managers.ai_utils.ai_loader import AIConfiguration

from utils.loc_datetime import datetime

from dotenv import load_dotenv


from utils.open_meteo_handle import OpenMeteoLoc

import asyncio
load_dotenv()

my_latitude = os.getenv("LATITUDE")
my_longitude = os.getenv("LONGITUDE")





# Default filepaths 
DEFAULT_MEMORY_DB = "memory.json"
DEFAULT_DEEP_MEMORY_DB = "deep_memory.db"
DEFAULT_AI_LOG = "ai_log.txt"
DEFAULT_INVENTORY_FOLDER = "inventory" 

class CLIChatbot:
    # MODIFIED: Changed tts_flag to tts_provider_id
    def __init__(self, config_manager, signal_callback=None, bots_archive_dir="data_archive"):
        """Initialize the CLI chatbot with AI bot and memory systems."""
        print("Initializing CLI Chatbot...")
        # --- Use the subdirectory structure ---
        # Ensure the directory exists
        voice = config_manager.get_config('game_settings','selected_voice')
        tts_provider_id = config_manager.get_config('game_settings','tts_provider')
        pet_name = config_manager.get_config('AI','pets_folder') # This will create a folder for the pet backend making a unique agent with its own memory and inventory and state

        lat=config_manager.get_config('location','latitude')
        long=config_manager.get_config('location','longitude')

        message="using provided location from config."
        if not lat or not long:
            lat = my_latitude
            long = my_longitude
            message="using default location from environment variables."
        self.open_meteo = OpenMeteoLoc(long=long, lat=lat) # Initialize with coordinates
        datetime.set_coordinates(lat,long)

        # Location data for the agent:
        print(f"Agent {pet_name} Initialized with location info {message}:")
        print(f"  Latitude: {lat}")
        print(f"  Longitude: {long}")
        print(f"  Timezone: {self.open_meteo.get_timezone()}")
        print(f"  Current Weather: {self.open_meteo.get_full_weather()}")
    

        sub_directory=os.path.join(bots_archive_dir,"bots",pet_name)
        os.makedirs(sub_directory, exist_ok=True) # Ensure the target directory is created

        # Construct full paths within the subdirectory
        memory_filepath = os.path.join(sub_directory, DEFAULT_MEMORY_DB)
        deep_memory_filepath = os.path.join(sub_directory, DEFAULT_DEEP_MEMORY_DB)
        ai_data_filepath = os.path.join(sub_directory, DEFAULT_AI_LOG)
        inventory_filepath = os.path.join(sub_directory, DEFAULT_INVENTORY_FOLDER) # Assuming you have an inventory subdirectory
        # --- End subdirectory structure ---
        self.sys_prompt = config_manager.get_config('AI','sys_prompt')
        self.deep_memory_flag = config_manager.get_config("AI_DeepMemory", "deep_memory_flag")
        self._signal_callback = signal_callback # Store the callback

        #print(f"DEBUG DEEP MEMORY FLAG {self.deep_memory_flag}")
        # Add a recursion depth limit to prevent infinite loops
        self.max_recursion_depth = 8 # Allow up to n consecutive AI calls (including function calls and final response)

        # REMOVED: self.tts = tts_flag
        self.last_response = None # Store the last response for potential use


    ### ///////// Init config  /////////  #####

        # load provider for the selected main AI model

        config_selected_provider = config_manager.get_config('AI','general_ai_provider')
        config_select_model = config_manager.get_config('AI','general_model')
        

        selected_client=AIConfiguration(provider=config_selected_provider,model=config_select_model,mode="agent").get_client()

        

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
                deep_memory= self.deep_memory_flag, # Pass the deep memory flag
                text_capture=self.text_capture,
                sub_directory=sub_directory,
                config_manager=config_manager

            )
            # Add tools that need usage of the memory structure

            self.state_manager=InventoryHouseManager(inventory_filepath, self._signal_callback, config_manager)

            self.functions_builder = FunctionBuilder(state_manager=self.state_manager, signal=self._signal_callback, subdirectory=sub_directory, memory_manager=self.memory, config_manager=config_manager, open_meteo=self.open_meteo)  # Initialize the function builder

            self.ai = ai_bot(data_filepath=ai_data_filepath, act_model=config_select_model, functions_builder=self.functions_builder, state_manager=self.state_manager, signal=self._signal_callback, memory_manager=self.memory, llm_client=selected_client) # 4.1-nano is the newest widely available model

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


    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')


    async def _get_ai_response_sequence(self, current_mem_structure: dict, current_full_prompt: str=None, depth: int = 0) -> str:
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
        time.sleep(2)


        if depth >= self.max_recursion_depth:
        #     print(f"\n⚠️ Warning: Max recursion depth ({self.max_recursion_depth}) reached.")
        #     stats_to_monitor = ["fullness", "hydration", "energy"]
        #     #  Decrease the stats
        #     # Decrease stats each function call set
        #     for stat_name in stats_to_monitor:
        # #         self.state_manager.adjust_stat(stat_name, -10)

            self.memory.save_to_memory(f"\n⚠️ Warning: Max recursion depth for actions ({self.max_recursion_depth})", "short_term", "user")
            #self.memory.save_to_memory(f"\n⚠️ Warning: Max recursion depth ({self.max_recursion_depth}) reached. Do not output any more functions.", "short_term", "system")
            return "Error: Max recursion depth reached while processing AI response chain."

        print(f"\n🤖 Thinking... (Call Depth: {depth})") # Added depth indicator

        try:


            # Call the AI with the current memory state and prompt
            # Ensure mem_structure is passed correctly (should be a dictionary)

            # This function is the main API call, it sends the information necesary, returns a stringed response for any tool calls if any were made
            # Returns a function_flag if any message was a tool call, for us to process here
            function_flag, response_content = await self.ai.ai_response(
                current_mem_structure if isinstance(current_mem_structure, dict) else {},
                depth, self.max_recursion_depth, developer_message=self.sys_prompt
            )


            if function_flag:
                print("*** Function call, decreasing wellness stats")
                stats_to_monitor = ["fullness", "hydration", "energy"]
                #  Decrease the stats
                # Decrease stats each function call set
                for stat_name in stats_to_monitor:
                    self.state_manager.adjust_stat(stat_name, -.1)
                    print(f"decreased stat: {stat_name} by: 1")

                print(f"⚙️ Function call detected (Depth: {depth}). Processing...")
                # self.text_capture.dump_text(f"Function Call (Depth {depth}):")
                # self.text_capture.dump_text(f"{response_content}") # response_content contains the function call payload
                # self.text_capture.dump_text(f"**************")


                # We have changed this to the tool tag
                if isinstance(response_content,list):
                    for result in response_content:
                        
                        self.memory.save_to_memory(result, "short_term", "tool")
                        print(f"✅ Saved function result to memory. Getting next AI response...")
                # else:
                #     self.memory.save_to_memory(str(response_content), "short_term", "tool")


                # Get the updated memory structure after saving the function result
                updated_mem_structure = self.memory.get_memory_structure()
                if updated_mem_structure is None:
                     print("Error: Could not load updated main memory structure after function call. Proceeding with potentially stale memory.")
                     updated_mem_structure = {} # Provide default empty fallback

                # Recursively call self to get the next response in the chain
                return await self._get_ai_response_sequence(current_mem_structure=updated_mem_structure, depth=depth + 1)

            else:

                # Not a function call - this is the final text response
                print(f"✅ No function call detected (Depth: {depth}). This is the final response.")
                print("Cleaning context...") # Added context cleaning step
   


                # Clean up tool context from memory after generating last response
                self.memory.process_short_term_system() # This system now changed to instead of using a lifespan for the entries, it uses tokens to decide if it is necesary to sumarize



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

    async def _check_wellness_and_consequences(self):
        """
        Monitors the AI agent's wellness stats (fullness, hydration, energy).
        Decreases stats, checks against predefined thresholds, applies specific
        messages to memory based on severity, and triggers a "pass out" state
        with subsequent recovery if any stat drops to a critical level.
        """
        print("Checking wellness and consequences...")
        stats_to_monitor = ["fullness", "hydration", "energy"]
        low_threshold_for_passout = 20  # The critical threshold below which passing out occurs
        recovery_amount = 40            # The amount stats are recovered after passing out

        # Define thresholds and messages for different severity levels for each stat.
        # Messages are ordered from highest threshold (least severe) to lowest (most severe).
        # This ensures that when iterating, the first matched threshold will be the
        # most severe applicable message for the current stat value.
        wellness_threshold_messages = {
            "fullness": [
                (120, "You begin to feel a bit hungry."),
                (60, "You feel really hungry, your stomach rumbles loudly."),
                (30, "Your hunger is unbearable, you can barely focus."),
                (low_threshold_for_passout, "You're about to collapse from hunger."),
            ],
            "hydration": [
                (120, "You feel a little thirsty."),
                (60, "Your mouth feels dry, you desperately need water."),
                (30, "You're severely dehydrated, your head throbs."),
                (low_threshold_for_passout, "You're about to collapse from dehydration."),
            ],
            "energy": [
                (120, "You feel a bit tired."),
                (60, "Your eyelids feel heavy, you're struggling to stay awake."),
                (30, "You're utterly exhausted, your body screams for rest."),
                (low_threshold_for_passout, "You're about to collapse from exhaustion."),
            ],
        }

        # 1. Decrease the monitored stats by 1 unit
        for stat_name in stats_to_monitor:
            self.state_manager.adjust_stat(stat_name, -1)

        # 2. Get the *updated* stats dictionary
        stats_data = self.state_manager.get_stats(True)

        low_stat_detected = False # Flag to determine if any stat has hit the critical pass-out threshold

        if stats_data is not None:
            for stat_name in stats_to_monitor:
                # Retrieve current value, defaulting to infinity if stat is missing to avoid false positives
                current_value = stats_data.get(stat_name, float('inf'))

                # Check for specific threshold messages and save them to memory
                if stat_name in wellness_threshold_messages:
                    # Iterate through the defined thresholds for the current stat
                    for threshold, message in wellness_threshold_messages[stat_name]:
                        if current_value <= threshold:
                            # If the current value is at or below this threshold, save the associated message
                            self.memory.save_to_memory(message, "short_term", "user")
                            
                            # If this specific threshold is the critical pass-out threshold,
                            # set the flag to trigger a pass-out event after checking all stats.
                            if current_value <= low_threshold_for_passout:
                                low_stat_detected = True
                                print("Low stat detected: " + stat_name + " is at or below threshold: " + str(threshold))
                            break # Stop after finding the most severe applicable message for this stat

        else:
            print("Warning: Could not retrieve valid stats data to check wellness thresholds.")

        # 3. If a critically low stat was detected, perform the consequences
        if low_stat_detected:
            print("Triggering pass-out consequences...")
            time_to_sleep = 900 # 15 minutes = 900 seconds
            # Send a signal to the system that the agent has passed out and needs to 'sleep'
            self._send_signal({"type": "start_sleep", "time_to_sleep": time_to_sleep})
            await asyncio.sleep(time_to_sleep)
            self._send_signal({"type": "end_sleep"})

            # Save pass-out specific messages to the agent's memory
            self.memory.save_to_memory("Internal message: You passed out! Be more careful with your basic necessities.", "short_term", "user")
            self.memory.save_to_memory("Internal message: After 15 minutes you wake up on the exact same spot you fainted, still feeling weak.", "short_term", "user")

            # 4. Increase the stats for recovery after passing out
            for stat_name in stats_to_monitor:
                self.state_manager.adjust_stat(stat_name, recovery_amount)

            print("AI agent passed out due to critically low wellness levels.")


    async def process_input(self, message, role="user"):
        """Process user input and generate AI response."""
        joined_random_entity = ""

        # Capture  input to logger
        self.text_capture.dump_text(f"##########")
        self.text_capture.dump_text(f"Input Message:")
        self.text_capture.dump_text(f"{role}:")
        self.text_capture.dump_text(f"{message}")
        self.text_capture.dump_text(f"##########")

        # 1. Save  input to short-term memory
        self.memory.save_to_memory(message, "short_term", f"{role}")

        # 3. Get current standard memory structure
        mem_structure = self.memory.get_memory_structure() # This structure should include the user input we just added
        if mem_structure is None:
             print("Error: Could not load main memory structure. Proceeding without it.")
             mem_structure = {"short_term": {}, "long_term": [], "base_memory": ""} # Provide default empty

        # 5. Get AI response (now handled recursively)
        final_ai_response = await self._get_ai_response_sequence(
            current_mem_structure=mem_structure if isinstance(mem_structure, dict) else {},
            depth=0
        )

        self.state_manager.add_steps(1) # add a step to the counter


# --- wellness stats check -----
        await self._check_wellness_and_consequences()
# --- extra part of the function -----
        # 6. Perform memory check (summarization, purging)
        print("Performing memory check...")
        self.last_response = final_ai_response # Store the last response for potential TTS

        # MODIFIED: Calling the new process_response_with_tts
        self.memory.check()

        self.process_response_with_tts(final_ai_response)

        return final_ai_response # Return the final text response

    
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
