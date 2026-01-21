# user_interface_chatbot.py

# this "adaptor" turns the pygame interface into a user driven controller instead of an AI agent driven one

# TODO: This needs the TTS providers to be added just like in the real bot

import os
import asyncio
import random
from inventory_items.inventory_manager import InventoryHouseManager
from tools.tools_builder.construct_tools import FunctionBuilder
from utils.capture_text import TextCapture
from utils.open_meteo_handle import OpenMeteoLoc
from utils.loc_datetime import datetime

from ai_managers.agents.memory.memory_handle import memory_manager # Assuming this is the correct import for your memory class


# Import the lightweight LLM translator
from ai_managers.agents.agents_utils.command_translator import CommandTranslator


# NEW: Import TTS Providers
from tts_providers.base_tts_provider import BaseTTSProvider
from tts_providers.macos_say_provider import MacOSSaiProvider
from tts_providers.espeak_ng_provider import ESpeakNGProvider
from tts_providers.piper_provider import PiperTTSProvider

# Default filepaths 
DEFAULT_MEMORY_DB = "memory.json"
DEFAULT_DEEP_MEMORY_DB = "deep_memory.db"
DEFAULT_AI_LOG = "ai_log.txt"
DEFAULT_INVENTORY_FOLDER = "inventory" 
DEFAULT_TEXT_CAPTURE_DB = "logs_capture.txt"

my_latitude = os.getenv("LATITUDE")
my_longitude = os.getenv("LONGITUDE")


class UserInterfaceChatbot:
    """
    A user-controlled interface that uses a small LLM (Function Gemma) 
    to translate natural language commands into function calls.
    
    Replaces the AI agent - user is now in control, but with natural language flexibility.
    """
    
    def __init__(self, signal_callback, config_manager, bots_archive_dir="data_archive"):
        print("UserInterfaceChatbot: Initializing...")

        pet_name = config_manager.get_config('AI', 'pets_folder')
        sub_directory = os.path.join(bots_archive_dir, "bots", pet_name)
        os.makedirs(sub_directory, exist_ok=True)

        self._signal_callback = signal_callback

        # Setup location (same as real bot)
        lat = config_manager.get_config('location', 'latitude')
        long = config_manager.get_config('location', 'longitude')
        
        if not lat or not long:
            lat = my_latitude
            long = my_longitude
            
        self.open_meteo = OpenMeteoLoc(long=long, lat=lat)
        datetime.set_coordinates(lat, long)

        print(f"User Interface initialized with location: {lat}, {long}")

        # Initialize core systems
        memory_filepath = os.path.join(sub_directory, DEFAULT_MEMORY_DB)
        deep_memory_filepath = os.path.join(sub_directory, DEFAULT_DEEP_MEMORY_DB)
        ai_data_filepath = os.path.join(sub_directory, DEFAULT_AI_LOG)
        inventory_filepath = os.path.join(sub_directory, DEFAULT_INVENTORY_FOLDER) # Assuming you have an inventory subdirectory
        inventory_filepath = os.path.join(sub_directory, DEFAULT_INVENTORY_FOLDER)
        text_capture_path = os.path.join(sub_directory, DEFAULT_TEXT_CAPTURE_DB)

        self.text_capture = TextCapture(filepath=text_capture_path)
        self.state_manager = InventoryHouseManager(inventory_filepath, self._signal_callback, config_manager)

        self.memory = memory_manager(
                filepath=memory_filepath,
                deep_memory_filepath=deep_memory_filepath,
                deep_memory= False, # Pass the deep memory flag
                text_capture=self.text_capture,
                sub_directory=sub_directory,
                config_manager=config_manager

            )
        self.functions_builder = FunctionBuilder(
            state_manager=self.state_manager, 
            signal=self._signal_callback, 
            subdirectory=sub_directory, 
            memory_manager=self.memory,  # Just pass the memory manager 
            config_manager=config_manager, 
            open_meteo=self.open_meteo
        )

        # Initialize the command translator (small LLM)
        self.command_translator = CommandTranslator(
            functions_builder=self.functions_builder,
            text_capture=self.text_capture,
            config_manager=config_manager
        )

        tts_provider_id = config_manager.get_config('game_settings','tts_provider')
        voice = config_manager.get_config('game_settings','selected_voice')

        self.tts_provider: BaseTTSProvider | None = None
        if tts_provider_id:
            if tts_provider_id == "macos_say":
                self.tts_provider = MacOSSaiProvider(signal_callback=self._signal_callback)
            elif tts_provider_id == "espeak_ng":
                self.tts_provider = ESpeakNGProvider(signal_callback=self._signal_callback, voice_name=voice)
            elif tts_provider_id == "piper":
                self.tts_provider = PiperTTSProvider(signal_callback=self._signal_callback, voice_name=voice)

            # Add more elifs here for other providers as they are created
            else:
                print(f"Warning: Unknown TTS provider ID '{tts_provider_id}'. TTS will be disabled.")
                self.tts_provider = None
        
        if self.tts_provider and not self.tts_provider.is_available():
            print(f"Warning: Selected TTS provider '{tts_provider_id}' is not available on this system. TTS will be disabled.")
            self.tts_provider = None


        print("UserInterfaceChatbot: Initialized.")

    # --- API Methods (same as CLIChatbot/MockChatbot) ---
    
    def get_steps(self):
        return self.state_manager.get_steps()

    def is_color_configured(self):
        return self.state_manager.is_color_configured()

    def set_pet_color(self, color):
        self.state_manager.set_pet_color(color)

    def set_color_configured(self, flag):
        self.state_manager.set_color_configured(flag)

    def get_pet_color(self):
        return self.state_manager.get_pet_color()

    def get_current_location(self):
        return self.state_manager.get_current_room_id()

    def get_wellness_states(self):
        return self.state_manager.get_stats(internal=True)

    def add_items_room(self, room_id, items_list):
        for item_info in items_list:
            if isinstance(item_info, dict) and 'name' in item_info:
                self.state_manager.create_item(
                    target_location="room", 
                    target_location_id=room_id,
                    item_creation_data=item_info
                )
        
        self._signal_callback({
            "type": "room_inventory",
            "item_list": self.state_manager.list_inventories(formatted=True)
        })

    def get_room_name_out(self, room_id):
        return self.state_manager.get_room_name(room_id)

    def add_message_out(self, message, role):
        # No memory, but log it
        self.text_capture.dump_text(f"[{role}] {message}")

    def get_inventories(self):
        inventories = self.state_manager.list_inventories(formatted=True)
        room_items = inventories.get('room', [])
        player_items = inventories.get('player', [])

        self._signal_callback({"type": "room_inventory", "item_list": room_items})
        self._signal_callback({"type": "player_inventory", "item_list": player_items})

        return room_items, player_items

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


    async def process_input(self, user_input, role='user'):
        """
        Main processing method - translates natural language to function calls.
        
        Flow:
        1. User types: "go to kitchen and eat an apple"
        2. Command Translator (Function Gemma) → function calls
        3. Execute functions
        4. Generate natural language response
        5. Return response to UI
        """
        print(f"\nUserInterface: Processing input: {user_input[:100]}...")
        
        # Log input


        # Small delay for realism
        await asyncio.sleep(random.uniform(0.3, 1.0))

        try:
            # --- CORE: Translate natural language → function calls ---
            function_calls = await self.command_translator.translate_to_functions(
                user_input=user_input,
                current_context=self._get_current_context()
            )

            # --- Execute function calls ---
            execution_results = []
            for fc in function_calls:
                result = await self._execute_function_call(fc)
                execution_results.append({
                    "function": fc['name'],
                    "args": fc['args'],
                    "result": result
                })

            # --- Generate natural language response ---
            response = await self.command_translator.generate_response(
                user_input=user_input,
                execution_results=execution_results,
                current_context=self._get_current_context()
            )

            self.text_capture.dump_text(f"Translation: User Input: '{user_input}' → {str(function_calls)}")
            self.text_capture.dump_text(f"AI Response: {response}")

            # Update step counter
            self.state_manager.add_steps(1)

            # Check wellness consequences (optional - keeps game mechanics)
            await self._check_wellness_consequences()

            self.process_response_with_tts(response)

            return response

        except Exception as e:
            print(f"Error processing input: {e}")
            import traceback
            traceback.print_exc()
            return f"I couldn't understand that command. ({str(e)})"

    async def _execute_function_call(self, function_call):
        """Execute a single function call and return result."""
        try:
            name = function_call['name']
            args = function_call['args']
            
            print(f"  Executing: {name}({args})")
            
            result = await self.functions_builder.call_function(name, args)
            
            # Send signal for UI feedback
            self._signal_callback({
                "type": "function_called",
                "function_name": name,
                "function_result": str(result)
            })
            
            return result
            
        except Exception as e:
            print(f"Error executing {function_call.get('name')}: {e}")
            return f"Error: {str(e)}"

    def _get_current_context(self):
        """Get current game state context for the translator."""
        current_room = self.state_manager.get_current_room_name()
        room_items, player_items = self.state_manager.list_inventories(formatted=True)
        stats = self.state_manager.get_stats(internal=True)

        available_rooms = self.state_manager.get_all_rooms()
        
        return {
            "current_room": current_room,
            "room_items": room_items,
            "player_items": player_items,
            "stats": stats,
            "available_rooms": available_rooms,
            "tools_info": self.functions_builder.get_current_tools_info()
        }

    async def _check_wellness_consequences(self):
        """
        Optional: Keep the wellness system from the original bot.
        Stats decrease with actions, pass out if too low.
        """
        stats_to_monitor = ["fullness", "hydration", "energy"]
        low_threshold = 20
        
        # Decrease stats slightly per action
        for stat_name in stats_to_monitor:
            self.state_manager.adjust_stat(stat_name, -0.5)
        
        stats_data = self.state_manager.get_stats(True)
        low_stat = False
        
        for stat_name in stats_to_monitor:
            if stats_data.get(stat_name, 100) <= low_threshold:
                low_stat = True
                break
        
        if low_stat:
            print("Warning: Low wellness! Triggering rest...")
            time_to_sleep = 60  # 1 minute for demo
            self._signal_callback({"type": "start_sleep", "time_to_sleep": time_to_sleep})
            await asyncio.sleep(time_to_sleep)
            self._signal_callback({"type": "end_sleep"})
            
            # Recovery
            for stat_name in stats_to_monitor:
                self.state_manager.adjust_stat(stat_name, 40)

    def shutdown(self):
        """Clean shutdown."""
        print("UserInterfaceChatbot: Shutting down...")
        if self.state_manager:
            self.state_manager.save_state()
            
        if self.tts_provider:
            self.tts_provider.stop()

        print("UserInterfaceChatbot: Shutdown complete.")