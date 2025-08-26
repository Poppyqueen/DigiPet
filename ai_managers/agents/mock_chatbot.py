# mock_chatbot.py

# Util to mock the chatbot for UI testing without needing real AI APIs.

import random
import asyncio # ADDED THIS IMPORT IN PREVIOUS STEP
from inventory_items.inventory_manager import InventoryHouseManager
import os
from utils.capture_text import TextCapture # Import the text capture class

from utils.open_meteo_handle import OpenMeteoLoc

from utils.loc_datetime import datetime


DEFAULT_INVENTORY_FOLDER = "inventory" 
DEFAULT_MEMORY_DB = "cli_memory.json"
DEFAULT_DEEP_MEMORY_DB = "cli_deep_memory.json"
DEFAULT_TEXT_CAPTURE_DB = "logs_capture.txt"

my_latitude = os.getenv("LATITUDE")
my_longitude = os.getenv("LONGITUDE")


# --- NEW: Mock Functions Builder Class ---
# This class mocks the functions_builder attribute of the real chatbot,
# specifically to provide the get_current_room_info method.
class MockFunctionsBuilder:
    def __init__(self, parent_chatbot):
        self._parent = parent_chatbot # To access parent's state if needed

    def get_current_room_info(self):
        """
        Mock: Returns a dictionary containing mock lore for the current room.
        This provides the structured data expected by the UI for the lore panel.
        """
        # Get the current room name directly from the state manager.
        room_name = self._parent.state_manager.get_current_room_name()

        # Static lore, but with a dynamic room name for context
        mock_lore = (
            f"Welcome to the {room_name}! This is a cozy space where your "
            "digital pet loves to spend time. Each room in the house has "
            "its own unique charm and potential interactions. Explore to "
            "discover new items, interact with your pet, and learn more "
            "about the world they inhabit. Keep an eye on your pet's stats "
            "to ensure they are happy, full, energetic, and clean!"
        )
        print(f"MockFunctionsBuilder: get_current_room_info() called.")
        return {"title": room_name,
                "body": mock_lore}


# --- Mock Chatbot Class ---
# This class mocks the behavior of CLIChatbot for UI testing purposes.
# It does not use any real AI APIs.
class MockChatbot:
    def __init__(self, signal_callback, config_manager, bots_archive_dir="data_archive"):
        print("MockChatbot: Initializing...")

        pet_name = config_manager.get_config('AI','pets_folder') # This will create a folder for the pet backend making a unique agent with its own memory and inventory and state

        sub_directory=os.path.join(bots_archive_dir,"bots",pet_name)

        os.makedirs(sub_directory, exist_ok=True) # Ensure the target directory is created

        self._signal_callback = signal_callback


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
    

        # --- Mock Internal State (Simulating what the real bot holds) ---
        # self._is_color_configured = False
        # self._pet_color = None # Will store a mock color value (e.g., 'red', 'blue')
        # self._steps = 150 # Initial mock step count
        # self._current_location_id = "bedroom" # Mock initial location ID

        # self._pet_stats = {
        #     "fullness": 150.0, # Mock initial stats
        #     "happiness": 180.0,
        #     "energy": 120.0,
        #     "hygiene": 100.0
        # }

        # Mock room data for name lookups, music, and inventory keys
        # self._mock_room_data = {
        #     "bedroom": {"name": "Bedroom", "music": "bedroom", "image": "bedroom"},
        #     "living_room": {"name": "Living Room", "music": "living_room", "image": "living_room"},
        #     "kitchen": {"name": "Kitchen", "music": "kitchen", "image": "kitchen"},
        #     "garden": {"name": "Garden", "music": "garden", "image": "garden"},
        #     "bathroom": {"name": "Bathroom", "music": "bathroom", "image": "bathroom"},
        # }
        # Mock inventory data - mapping location_id to list of item names
        # self._mock_inventories = {
        #     "bedroom": ["bed", "wardrobe", "toy box"],
        #     "living_room": ["sofa", "tv", "rug"],
        #     "kitchen": ["fridge", "stove", "table", "apple", "banana"],
        #     "garden": ["tree", "flowers", "bench"],
        #     "bathroom": ["sink", "toilet", "shower", "soap"],
        # }
        # self._player_inventory = ["wallet", "phone"] # Mock player inventory
        inventory_filepath = os.path.join(sub_directory, DEFAULT_INVENTORY_FOLDER) # Assuming you have an inventory subdirectory
        text_capture_path = os.path.join(sub_directory, DEFAULT_TEXT_CAPTURE_DB)



        self.text_capture = TextCapture(filepath=text_capture_path)  # Initialize text capture

        # --- Instantiate the Mock State Manager ---
        self.config_manager = config_manager
        self.state_manager=InventoryHouseManager(inventory_filepath, self._signal_callback, config_manager)


        # --- NEW: Instantiate the Mock Functions Builder ---
        self.functions_builder = MockFunctionsBuilder(self) # Pass self

        print("MockChatbot: Initialized.")

    # --- Methods used by game.py ---

    def get_steps(self):
        """Mock: Returns a mock step count."""
        print(f"MockChatbot: get_steps() called")
        return self.state_manager.get_steps()

    def is_color_configured(self):
        """Mock: Returns the mock color configured state."""
        print(f"MockChatbot: is_color_configured() called")
        return self.state_manager.is_color_configured()

    def set_pet_color(self, color):
        """Mock: Stores the mock pet color."""
        print(f"MockChatbot: set_pet_color({color}) called.")
        self.state_manager.set_pet_color(color)

    def set_color_configured(self, flag):
        """Mock: Sets the mock color configured state."""
        print(f"MockChatbot: set_color_configured({flag}) called.")
        self.state_manager.set_color_configured(flag)

    def get_pet_color(self):
        """Mock: Returns the stored mock pet color."""
        print(f"MockChatbot: get_pet_color() called")
        return self.state_manager.get_pet_color()

    # This method is used for the *initial* background load in game.py,
    # NOT subsequent ones triggered by signals.
    def get_current_location(self):
        """Mock: Returns the mock current location ID (from the MockChatbot's state)."""
        print(f"MockChatbot: get_current_location() called")
        return self.state_manager.get_current_room_id()

    def get_wellness_states(self):
        """Mock: Returns a copy of the mock pet stats."""
        print(f"MockChatbot: get_wellness_states() called")
        # Return a copy to prevent external modification of internal state
        return self.state_manager.get_stats(internal=True)

    def add_items_room(self, room_id, items_list):
        """Mock: Adds items to the specified mock room inventory and signals."""
        print(f"MockChatbot: add_items_room() called for room '{room_id}' with items: {items_list}")
            # Add item names from the list of dictionaries
        for item_info in items_list:
                if isinstance(item_info, dict) and 'name' in item_info:
                    item_name = item_info['name']
                    self.state_manager.create_item(target_location="room", target_location_id=room_id,item_creation_data=item_info)
                    print(f"MockChatbot: Added '{item_name}' to room '{room_id}'.")
        # Trigger an inventory update signal for the CURRENT room
        # Note: This might be slightly different from how the real bot works
        # (which might only update the inventory when you *enter* the room),
        # but it simulates the items appearing after adding.
        self._signal_callback({
                "type": "room_inventory",
                "item_list": self.state_manager.list_inventories(formatted=True) # Signal for current room
        })
        print("MockChatbot: Signaled room_inventory update.")
    

    def get_room_name_out(self, room_id):
        """Mock: Returns the name for a given mock room ID using internal mock data."""
        # Access the mock room data directly from the MockChatbot
        name=self.state_manager.get_room_name(room_id)
        print(f"MockChatbot: get_room_name_out('{room_id}') called, returning '{name}'")
        return name

    def add_message_out(self, message, role):
        """Mock: Simulates adding a message to the bot's internal memory (prints it)."""
        # The mock doesn't have memory, but it confirms it received the message
        print(f"MockChatbot: add_message_out() called (received message for internal memory): [Role: {role}] {message[:100]}...") # Print first 100 chars


    def get_inventories(self):
        """Mock: Returns the current mock room and player inventory lists."""
        inventories = self.state_manager.list_inventories(formatted=True)
        room_items = inventories.get('room', [])
        player_items = inventories.get('player', [])


        print(f"MockChatbot: get_inventories() called. Room: {len(room_items)} items, Player: {len(player_items)} items.")

        # Also send signals to ensure GUI is updated if this is called *after* init
        # (The game.py init calls this before the main loop, which is fine)
        self._signal_callback({"type": "room_inventory", "item_list": room_items})
        self._signal_callback({"type": "player_inventory", "item_list": player_items})

        return room_items, player_items


    async def process_input(self, user_input, role='user'):
        """
        Mock: Simulates processing input and triggering signals/responses.
        Adds a small delay. Responds based on simple keywords.
        """
        print(f"\nMockChatbot: process_input() called [Role: {role}]: {user_input[:100]}...")

        # Simulate processing time
        await asyncio.sleep(random.uniform(.3, 3))

        response_text = ""
        signal_sent = False # Flag to track if a signal was sent

        # --- Logic based on Input/Role ---

        if role == 'system':
            # Simulate an autonomous action trigger
            print("MockChatbot: Processing autonomous system input.")
            response_text = random.choice([
                "I feel a bit lonely...",
                "What should we do now?",
                "My stats are feeling a bit... unbalanced.",
                "I think I need something.",
                "It's a quiet moment."
            ])
            # Simulate a random stat change and possibly an emote
            all_stats = self.state_manager.get_stats(internal=True)
            stat_to_change = random.choice(list(all_stats.keys()))
            change_amount = random.uniform(-20.0, 20.0) # Random change
            new_value = self.state_manager.adjust_stat(stat_to_change, change_amount)
            print(f"MockChatbot: Simulating stat change: {stat_to_change} by {change_amount:.2f} to {new_value:.2f}")
            signal_sent = True # adjust_stat handles the signal

            if change_amount < -10: # If stat dropped significantly
                 emote = random.choice(["sad", "confused", "thinking"])
                 self.state_manager.set_current_emote(emote) # This will signal
                 print(f"MockChatbot: Simulating negative emote: {emote}")
            elif change_amount > 10: # If stat increased significantly
                 emote = random.choice(["happy", "excited", "curious"])
                 self.state_manager.set_current_emote(emote) # This will signal
                 print(f"MockChatbot: Simulating positive emote: {emote}")


        elif role == 'user':
            lower_input = user_input.lower()
            print("MockChatbot: Processing user input.")

            # --- Simple Keyword Matching ---
            if "feed" in lower_input or "eat" in lower_input or "food" in lower_input:
                response_text = "Yummy! Thank you for the food!"
                # Simulate stat changes - signals are handled by adjust_stat
                self.state_manager.adjust_stat("fullness", random.uniform(20, 50))
                self.state_manager.adjust_stat("happiness", random.uniform(5, 15))
                # Signal emote and popup
                self.state_manager.set_current_emote(random.choice(["happy", "excited"]))
                self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/stat_icons/fullness_full.png", "duration_ms": 2000})
                signal_sent = True

            elif "play" in lower_input or "toy" in lower_input or "fun" in lower_input:
                response_text = "Let's play! What game?"
                # Simulate stat changes - signals are handled by adjust_stat
                self.state_manager.adjust_stat("happiness", random.uniform(20, 50))
                self.state_manager.adjust_stat("energy", -random.uniform(5, 15))
                # Signal emote and shake
                self.state_manager.set_current_emote(random.choice(["excited", "happy"]))
                self._signal_callback({"type": "shake_circle"})
                signal_sent = True

            elif "sleep" in lower_input or "bed" in lower_input or "rest" in lower_input:
                response_text = "Okay, I'm feeling sleepy. Good night!"
                # Simulate stat changes - signals are handled by adjust_stat
                self.state_manager.adjust_stat("energy", random.uniform(40, 80))
                self.state_manager.adjust_stat("happiness", -random.uniform(5, 10))
                # Signal sleep event (mock duration: 10-30 seconds)
                sleep_duration = random.randint(10, 30)
                self._signal_callback({"type": "sleep", "duration": sleep_duration})
                signal_sent = True

            elif "clean" in lower_input or "bathe" in lower_input or "wash" in lower_input:
                response_text = "Ah, a bath sounds refreshing!"
                # Simulate stat changes - signals are handled by adjust_stat
                self.state_manager.adjust_stat("hygiene", random.uniform(50, 100))
                self.state_manager.adjust_stat("happiness", random.uniform(5, 15))
                # Signal emote and popup
                self.state_manager.set_current_emote(random.choice(["happy", "content"]))
                self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/stat_icons/hygiene_clean.png", "duration_ms": 2000})
                signal_sent = True
            # CORRECTED CODE
            elif "change room" in lower_input or "move to" in lower_input or "go to" in lower_input:
                try:
                    # Get all room IDs and sort them numerically for a predictable cycle
                    rooms = self.state_manager._state_store.get_state_section("rooms")
                    room_ids = []

                    for room in rooms:
                        room_ids.append(room["id"])
                    # print(f"DEBUG MOCK CHATBOT ROOM IDS")
                    # print(room_ids)
                    # Ensure the room IDs are integers to allow for numerical sorting
                    room_ids_int = sorted([int(r) for r in room_ids]) 

                    if not room_ids_int:
                        raise ValueError("No rooms available to move to.")

                    current_room_id_int = self.state_manager.get_current_room_id()
                    
                    # Find the index of the current room in the numerically sorted list
                    current_index = room_ids_int.index(current_room_id_int)
                    
                    # Calculate the index of the next room
                    next_index = (current_index + 1) % len(room_ids_int)
                    new_room_id_int = room_ids_int[next_index]

                    # This call triggers all necessary signals (background, inventory, etc.)
                    self.state_manager.set_current_room(new_room_id_int)
                    
                    new_room_name = self.state_manager.get_room_name(new_room_id_int)
                    response_text = f"Okay, let's go to the {new_room_name}!"
                    signal_sent = True
                except (ValueError, IndexError):
                    response_text = "Hmm, I'm having trouble moving to another room."


            elif "inventory" in lower_input or "items" in lower_input or "what do we have" in lower_input:
                 response_text = "Let me check our inventories!"
                 # This service method sends signals for both room and player inventories.
                 self.state_manager.list_inventories(formatted=True)
                 signal_sent = True

            elif "care package" in lower_input or "deliver" in lower_input:
                 response_text = "Looks like a care package arrived!"
                 # The game handles adding items from care packages. This mock just acknowledges.
                 pass

            else:
                # Default response for unhandled input
                response_text = random.choice([
                    "Hmm, that's interesting.",
                    "Tell me more.",
                    "I'm not sure I understand.",
                    "Okay.",
                    "What do you mean?",
                    "Could you rephrase that?"
                ])

        print(f"MockChatbot: Finished process_input. Returning text response (length {len(response_text)}). Signals sent: {signal_sent}")

        # Return the text response. The game loop will decide whether to post it.
        return response_text.strip() if response_text else None


    def shutdown(self):
        """Mock: Simulates chatbot shutdown."""
        print("MockChatbot: Shutting down...")
        # No actual resources to clean up for the mock
        print("MockChatbot: Shutdown complete.")

    # Mock helper method that is accessed via state_manager in game.py
    # def _find_room_by_id(self, room_id):
    #     """Mock: Helper to simulate finding room data by ID."""
    #     # This method is now in MockStateManager, accessed via self.state_manager._find_room_by_id
    #      print(f"MockChatbot: _find_room_by_id('{room_id}') called. This should be called via state_manager.")
    #      return self._mock_room_data.get(room_id)