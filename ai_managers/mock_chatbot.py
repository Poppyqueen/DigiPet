# mock_chatbot.py

# Util to mock the chatbot for UI testing without needing real AI APIs.

import time
import random
import pygame_int.config as config # Need access to event types, CARE_PACKAGES, etc.
import asyncio # ADDED THIS IMPORT IN PREVIOUS STEP
from inventory_items.inventory_manager import InventoryHouseManager
import os
from memory.memory_handle import memory_manager # Assuming this is the correct import for your memory class
from utils.capture_text import TextCapture # Import the text capture class


DEFAULT_INVENTORY_FOLDER = "inventory" 
DEFAULT_MEMORY_DB = "cli_memory.json"
DEFAULT_DEEP_MEMORY_DB = "cli_deep_memory.json"
DEFAULT_TEXT_CAPTURE_DB = "logs_capture.txt"

# --- Mock State Manager Class ---
# This class mocks the state_manager attribute of the real chatbot.
# It simulates holding the current room ID and providing methods to access state data.
class MockStateManager:
    def __init__(self, parent_chatbot):
        # Keep a reference to the parent MockChatbot to access shared mock data
        self._parent = parent_chatbot
        print("MockStateManager: Initializing...")

        # Mock the _state attribute as a dictionary, as accessed directly in game.py
        # This should hold the current room ID to mimic the access pattern.
        self._state = {"current_room_id": self._parent._current_location_id}
        print("MockStateManager: Initialized with _state.")

    def get_current_room_id(self):
        """Mock: Returns the current room ID from the mock state dictionary."""
        # Return from the _state dict to match how game.py accesses it indirectly
        room_id = self._state.get("current_room_id")
        print(f"MockStateManager: get_current_room_id() called, returning '{room_id}' (from _state)")
        return room_id

    # Note: _find_room_by_id is used internally by the real bot's state manager
    # to look up room details from its config/data. We mock this behavior here.
    def _find_room_by_id(self, room_id):
        """Mock: Finds mock room data by ID using parent chatbot's data."""
        # Use the mock room data stored in the parent MockChatbot
        room_data = self._parent._mock_room_data.get(room_id)
        print(f"MockStateManager: _find_room_by_id('{room_id}') called, returning {room_data}")
        return room_data # Returns the dictionary or None if not found

    # Need a way for the parent MockChatbot to update this state manager's
    # internal state (_state dict) when the room changes.
    def _update_current_room_id(self, new_room_id):
         print(f"MockStateManager: _update_current_room_id('{new_room_id}') called.")
         self._state["current_room_id"] = new_room_id
         print(f"MockStateManager: _state['current_room_id'] updated to '{new_room_id}'")


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
        # We can make this dynamic if needed, but for now, a static string is requested.
        # However, to be more robust for different rooms, let's use the parent's mock room data.
        current_room_id = self._parent.state_manager.get_current_room_id()
        room_data = self._parent._mock_room_data.get(current_room_id, {})
        room_name = room_data.get("name", "Unknown Room")

        # Static lore, but with a dynamic room name for context
        mock_lore = (
            f"Welcome to the {room_name}! This is a cozy space where your "
            "digital pet loves to spend time. Each room in the house has "
            "its own unique charm and potential interactions. Explore to "
            "discover new items, interact with your pet, and learn more "
            "about the world they inhabit. Keep an eye on your pet's stats "
            "to ensure they are happy, full, energetic, and clean!"
        )
        print(f"MockFunctionsBuilder: get_current_room_info() called for '{room_name}'.")
        return {"title": room_name,
                "body": mock_lore}


# --- Mock Chatbot Class ---
# This class mocks the behavior of CLIChatbot for UI testing purposes.
# It does not use any real AI APIs.
class MockChatbot:
    def __init__(self, signal_callback, system_prompt, sub_directory, deep_memory, base_model, select_memory_model, tts_flag):
        print("MockChatbot: Initializing...")
        os.makedirs(sub_directory, exist_ok=True) # Ensure the target directory is created

        self._signal_callback = signal_callback
        self._system_prompt = system_prompt # Stored, but not used by mock logic
        self._sub_directory = sub_directory # Stored, but not used by mock logic
        self._deep_memory = deep_memory     # Stored, but not used by mock logic
        self._base_model = base_model       # Stored, but not used by mock logic
        self._select_memory_model = select_memory_model # Stored, but not used by mock logic
        self._tts_flag = tts_flag         # Stored, but not used by mock logic

        # --- Mock Internal State (Simulating what the real bot holds) ---
        self._is_color_configured = False
        self._pet_color = None # Will store a mock color value (e.g., 'red', 'blue')
        self._steps = 150 # Initial mock step count
        self._current_location_id = "bedroom" # Mock initial location ID

        self._pet_stats = {
            "fullness": 150.0, # Mock initial stats
            "happiness": 180.0,
            "energy": 120.0,
            "hygiene": 100.0
        }

        # Mock room data for name lookups, music, and inventory keys
        self._mock_room_data = {
            "bedroom": {"name": "Bedroom", "music": "bedroom", "image": "bedroom"},
            "living_room": {"name": "Living Room", "music": "living_room", "image": "living_room"},
            "kitchen": {"name": "Kitchen", "music": "kitchen", "image": "kitchen"},
            "garden": {"name": "Garden", "music": "garden", "image": "garden"},
            "bathroom": {"name": "Bathroom", "music": "bathroom", "image": "bathroom"},
        }
        # Mock inventory data - mapping location_id to list of item names
        self._mock_inventories = {
            "bedroom": ["bed", "wardrobe", "toy box"],
            "living_room": ["sofa", "tv", "rug"],
            "kitchen": ["fridge", "stove", "table", "apple", "banana"],
            "garden": ["tree", "flowers", "bench"],
            "bathroom": ["sink", "toilet", "shower", "soap"],
        }
        self._player_inventory = ["wallet", "phone"] # Mock player inventory
        inventory_filepath = os.path.join(sub_directory, DEFAULT_INVENTORY_FOLDER) # Assuming you have an inventory subdirectory
        memory_filepath = os.path.join(sub_directory, DEFAULT_MEMORY_DB)
        deep_memory_filepath = os.path.join(sub_directory, DEFAULT_DEEP_MEMORY_DB)
        text_capture_path = os.path.join(sub_directory, DEFAULT_TEXT_CAPTURE_DB)



        self.text_capture = TextCapture(filepath=text_capture_path)  # Initialize text capture

        self.memory = memory_manager(
            filepath=memory_filepath,
            deep_memory_filepath=deep_memory_filepath,
            deep_memory=deep_memory, # Pass the deep memory flag
            text_capture=self.text_capture,
            sub_directory=sub_directory
        )
        # --- Instantiate the Mock State Manager ---
        self.state_manager=InventoryHouseManager(inventory_filepath, self._signal_callback, self.memory)


        # --- NEW: Instantiate the Mock Functions Builder ---
        self.functions_builder = MockFunctionsBuilder(self) # Pass self

        print("MockChatbot: Initialized.")

    # --- Methods used by game.py ---

    def get_steps(self):
        """Mock: Returns a mock step count."""
        print(f"MockChatbot: get_steps() called, returning {self._steps}")
        return self._steps

    def is_color_configured(self):
        """Mock: Returns the mock color configured state."""
        print(f"MockChatbot: is_color_configured() called, returning {self._is_color_configured}")
        return self._is_color_configured

    def set_pet_color(self, color):
        """Mock: Stores the mock pet color."""
        print(f"MockChatbot: set_pet_color({color}) called.")
        self._pet_color = color

    def set_color_configured(self, flag):
        """Mock: Sets the mock color configured state."""
        print(f"MockChatbot: set_color_configured({flag}) called.")
        self._is_color_configured = flag

    def get_pet_color(self):
        """Mock: Returns the stored mock pet color."""
        print(f"MockChatbot: get_pet_color() called, returning {self._pet_color}")
        return self._pet_color

    # This method is used for the *initial* background load in game.py,
    # NOT subsequent ones triggered by signals.
    def get_current_location(self):
        """Mock: Returns the mock current location ID (from the MockChatbot's state)."""
        print(f"MockChatbot: get_current_location() called, returning {self._current_location_id}")
        return self.state_manager.get_current_room_id()

    def get_wellness_states(self):
        """Mock: Returns a copy of the mock pet stats."""
        print(f"MockChatbot: get_wellness_states() called, returning {self._pet_stats}")
        # Return a copy to prevent external modification of internal state
        return self._pet_stats.copy()

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
                "item_list": self.state_manager.list_inventories() # Signal for current room
        })
        print("MockChatbot: Signaled room_inventory update.")
    

    def get_room_name_out(self, room_id):
        """Mock: Returns the name for a given mock room ID using internal mock data."""
        # Access the mock room data directly from the MockChatbot
        name=self.state_manager.get_current_room_name()
        print(f"MockChatbot: get_room_name_out('{room_id}') called, returning '{name}'")
        return name

    def add_message_out(self, message, role):
        """Mock: Simulates adding a message to the bot's internal memory (prints it)."""
        # The mock doesn't have memory, but it confirms it received the message
        print(f"MockChatbot: add_message_out() called (received message for internal memory): [Role: {role}] {message[:100]}...") # Print first 100 chars


    def get_inventories(self):
        """Mock: Returns the current mock room and player inventory lists."""
        room_items = self._mock_inventories.get(self._current_location_id, [])
        player_items = self._player_inventory

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
        await asyncio.sleep(random.uniform(0.5, 2.0))

        response_text = ""
        signal_sent = False # Flag to track if any signal was sent

        # --- Mock Logic based on Input/Role ---

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
            stat_to_change = random.choice(list(self._pet_stats.keys()))
            change_amount = random.uniform(-20.0, 20.0) # Random change
            self._pet_stats[stat_to_change] += change_amount
            # Clamp stats between 0 and 200
            self._pet_stats[stat_to_change] = max(0.0, min(200.0, self._pet_stats[stat_to_change]))
            print(f"MockChatbot: Simulating stat change: {stat_to_change} by {change_amount:.2f} to {self._pet_stats[stat_to_change]:.2f}")
            self._signal_callback({
                 "type": "stat_changed",
                 "stat_name": stat_to_change,
                 "new_value": self._pet_stats[stat_to_change]
            })
            signal_sent = True

            if change_amount < -10: # If stat dropped significantly
                 emote = random.choice(["sad", "confused", "thinking"])
                 print(f"MockChatbot: Simulating negative emote: {emote}")
                 self._signal_callback({"type": "emote_changed", "emote_name": emote, "sound_path": f"style/sounds/emotes/{emote}.mp3"})
                 signal_sent = True
            elif change_amount > 10: # If stat increased significantly
                 emote = random.choice(["happy", "excited", "curious"])
                 print(f"MockChatbot: Simulating positive emote: {emote}")
                 self._signal_callback({"type": "emote_changed", "emote_name": emote, "sound_path": f"style/sounds/emotes/{emote}.mp3"})
                 signal_sent = True


        elif role == 'user':
            lower_input = user_input.lower()
            print("MockChatbot: Processing user input.")

            # --- Simple Keyword Matching ---
            if "feed" in lower_input or "eat" in lower_input or "food" in lower_input:
                response_text = "Yummy! Thank you for the food!"
                # Simulate stat changes
                self._pet_stats["fullness"] += random.uniform(20, 50)
                self._pet_stats["happiness"] += random.uniform(5, 15)
                # Clamp stats
                self._pet_stats["fullness"] = max(0.0, min(200.0, self._pet_stats["fullness"]))
                self._pet_stats["happiness"] = max(0.0, min(200.0, self._pet_stats["happiness"]))
                # Signal stat changes
                self._signal_callback({"type": "stat_changed", "stat_name": "fullness", "new_value": self._pet_stats["fullness"]})
                self._signal_callback({"type": "stat_changed", "stat_name": "happiness", "new_value": self._pet_stats["happiness"]})
                # Signal emote and popup
                emote = random.choice(["happy", "excited"])
                self._signal_callback({"type": "emote_changed", "emote_name": emote, "sound_path": f"style/sounds/emotes/{emote}.mp3"})
                self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/stat_icons/fullness_full.png", "duration_ms": 2000})
                signal_sent = True

            elif "play" in lower_input or "toy" in lower_input or "fun" in lower_input:
                response_text = "Let's play! What game?"
                # Simulate stat changes
                self._pet_stats["happiness"] += random.uniform(20, 50)
                self._pet_stats["energy"] -= random.uniform(5, 15) # Playing costs energy
                 # Clamp stats
                self._pet_stats["happiness"] = max(0.0, min(200.0, self._pet_stats["happiness"]))
                self._pet_stats["energy"] = max(0.0, min(200.0, self._pet_stats["energy"]))
                # Signal stat changes
                self._signal_callback({"type": "stat_changed", "stat_name": "happiness", "new_value": self._pet_stats["happiness"]})
                self._signal_callback({"type": "stat_changed", "stat_name": "energy", "new_value": self._pet_stats["energy"]})
                # Signal emote and shake
                emote = random.choice(["excited", "happy"])
                self._signal_callback({"type": "emote_changed", "emote_name": emote, "sound_path": f"style/sounds/emotes/{emote}.mp3"})
                self._signal_callback({"type": "shake_circle"})
                signal_sent = True

            elif "sleep" in lower_input or "bed" in lower_input or "rest" in lower_input:
                response_text = "Okay, I'm feeling sleepy. Good night!"
                # Simulate stat changes
                self._pet_stats["energy"] += random.uniform(40, 80) # Gain energy
                self._pet_stats["happiness"] -= random.uniform(5, 10) # Maybe slightly less happy while sleeping?
                 # Clamp stats
                self._pet_stats["energy"] = max(0.0, min(200.0, self._pet_stats["energy"]))
                self._pet_stats["happiness"] = max(0.0, min(200.0, self._pet_stats["happiness"]))
                # Signal stat changes
                self._signal_callback({"type": "stat_changed", "stat_name": "energy", "new_value": self._pet_stats["energy"]})
                self._signal_callback({"type": "stat_changed", "stat_name": "happiness", "new_value": self._pet_stats["happiness"]})
                # Signal sleep event (mock duration: 5-10 seconds)
                sleep_duration = random.randint(5, 10)
                self._signal_callback({"type": "sleep", "duration": sleep_duration})
                signal_sent = True


            elif "clean" in lower_input or "bathe" in lower_input or "wash" in lower_input:
                response_text = "Ah, a bath sounds refreshing!"
                # Simulate stat changes
                self._pet_stats["hygiene"] += random.uniform(50, 100) # Gain hygiene
                self._pet_stats["happiness"] += random.uniform(5, 15) # Feel clean, feel good
                 # Clamp stats
                self._pet_stats["hygiene"] = max(0.0, min(200.0, self._pet_stats["hygiene"]))
                self._pet_stats["happiness"] = max(0.0, min(200.0, self._pet_stats["happiness"]))
                # Signal stat changes
                self._signal_callback({"type": "stat_changed", "stat_name": "hygiene", "new_value": self._pet_stats["hygiene"]})
                self._signal_callback({"type": "stat_changed", "stat_name": "happiness", "new_value": self._pet_stats["happiness"]})
                # Signal emote and popup
                emote = random.choice(["happy", "content"]) # Maybe add a 'clean' emote/sound?
                self._signal_callback({"type": "emote_changed", "emote_name": emote, "sound_path": f"style/sounds/emotes/{emote}.mp3"})
                self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/stat_icons/hygiene_clean.png", "duration_ms": 2000})
                signal_sent = True


            elif "change room" in lower_input or "move to" in lower_input or "go to" in lower_input:
                # Simple mock room changing - cycles through rooms
                room_ids = list(self._mock_room_data.keys())
                try:
                    current_index = room_ids.index(self._current_location_id)
                    next_index = (current_index + 1) % len(room_ids)
                    self._current_location_id = room_ids[next_index]

                    # --- Update the mock state manager's internal state ---
                    self.state_manager._update_current_room_id(self._current_location_id)

                    new_room_name = self._mock_room_data[self._current_location_id]["name"]
                    response_text = f"Okay, let's go to the {new_room_name}!"
                    # Signal background change (corrected path to match typical Pygame image loading)
                    self._signal_callback({"type": "change_background", "image_path": f"{self._current_location_id}.jpg"})
                    # Signal inventory update for the new room
                    self._signal_callback({"type": "room_inventory", "item_list": self._mock_inventories.get(self._current_location_id, [])})
                    signal_sent = True
                except ValueError:
                    response_text = "Hmm, I don't know which room you mean."


            elif "inventory" in lower_input or "items" in lower_input or "what do we have" in lower_input:
                 response_text = "Let me check our inventories!"
                 # Signal inventory updates
                 self._signal_callback({"type": "room_inventory", "item_list": self._mock_inventories.get(self._current_location_id, [])})
                 self._signal_callback({"type": "player_inventory", "item_list": self._player_inventory})
                 signal_sent = True


            elif "care package" in lower_input or "deliver" in lower_input:
                 response_text = "Looks like a care package arrived!"
                 # Note: The game handles *adding* items based on button clicks
                 # This response simply acknowledges the command if typed directly.
                 # The actual item addition and inventory signal happen via the game's add_items function.
                 pass # No signals sent directly by this command, just the text response


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
        # Return None if empty to match the potential behavior of the real bot.
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