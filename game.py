# game.py
from pygame_int import config
from pygame_int import state
from pygame_int import gui
from pygame_int import animation
from pygame_int import gui_lore_panel
from pygame_int import gui_color_selector
from pygame_int.juke_box import jukebox 
from pygame_int.config_gui import run_config_main_menu_ui
import pygame
import sys
import threading
import asyncio


from utils.config_manager import ConfigManager

# We will keep the CLIChatbot on main game.py, that way we manage signals comming to it directly from
# main process

mock_running = False # If set to True, the mock will run and simulate the chatbot behavior

if mock_running:
    from ai_managers.mock_chatbot import MockChatbot
else:
    from ai_managers.chatbot_api import CLIChatbot 

# --- Pygame Initialization ---
pygame.init()
screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
pygame.display.set_caption("Digital Pet")

# Initialize Pygame Mixer
try:
    pygame.mixer.init()
    print("Pygame Mixer initialized.")
except pygame.error as e:
    print(f"Warning: Could not initialize Pygame Mixer: {e}")

# Font
try:
    font = pygame.font.Font(None, 20) # Default font
    line_height = font.get_linesize()
except pygame.error:
    print("Warning: Default font not found, using a fallback.")
    font = pygame.font.SysFont("Arial", 20) # Fallback font
    line_height = font.get_linesize() # Get line height from fallback font

bots_archive_dir="data_archive"

if mock_running:
    config_manager = ConfigManager(bots_archive_dir, mock=True)
else:
    config_manager = ConfigManager(bots_archive_dir)

run_config_main_menu_ui(screen, font, config_manager)


def calculate_sized_by_steps(current_steps, start_size, end_size, step_limit=config.STEP_SIZE_LIMIT): # 250
  """
  Calculates a size based on steps, scaling linearly up to a step limit
  and then clamping at the maximum size.

  Args:
    current_steps: The current number of steps (integer).
    start_size: The size at step 0 (integer).
    end_size: The size at the step_limit (integer).
    step_limit: The step at which the size reaches the end_size and stops increasing (integer).

  Returns:
    The calculated and clamped size (integer).
  """

  # Ensure step_limit is not zero to avoid division by zero
  if step_limit == 0:
    # Handle this case based on your requirements.
    # For now, let's assume if step_limit is 0, the size is always the start_size.
    return start_size

  # Linear interpolation: Calculate a potential size based on the current steps
  # within the scaling range (0 to step_limit).
  # We use float division for accuracy before converting to int.
  scale_factor = min(current_steps, step_limit) / step_limit
  potential_size = start_size + (end_size - start_size) * scale_factor

  # Clamp the potential size between the start_size and end_size
  # This ensures the size doesn't go below start_size or above end_size
  # after the step_limit is reached.
  final_size = max(start_size, min(potential_size, end_size))

  # Convert to integer pixels
  return int(final_size)


# We'll need a helper function to trigger the lore update
def trigger_lore_panel_update():
    """Fetches current room info and posts an event to update the lore panel."""
    global chatbot_available, chatbot
    if chatbot_available and chatbot and hasattr(chatbot, 'functions_builder') and \
       hasattr(chatbot.functions_builder, 'get_current_room_info') and \
       callable(chatbot.functions_builder.get_current_room_info):
        
        current_room_info = chatbot.functions_builder.get_current_room_info()
        
        # Ensure room_data is a dictionary, even if functions_builder returns None or non-dict
        if not isinstance(current_room_info, dict):
            current_room_info = {} # Fallback to empty dict
            print("Warning: get_current_room_info did not return a dictionary. Lore panel may show default text.")

        print(f"Triggering lore panel update with room data: {current_room_info.get('name', 'N/A')}")
        pygame.event.post(pygame.event.Event(config.UPDATE_LORE_DISPLAY_EVENT, room_data=current_room_info))
    else:
        print("Chatbot or its functions_builder.get_current_room_info is not available for lore update.")
        # Post a default empty lore update if chatbot isn't ready
        pygame.event.post(pygame.event.Event(config.UPDATE_LORE_DISPLAY_EVENT, room_data={
            'name': 'System Lore',
            'description': 'The lore system is not yet initialized or the chatbot is unavailable.'
        }))



# --- Callback function to receive signals from the chatbot ---
# This callback is already designed to run potentially in the chatbot's
# internal thread(s) and post events to the main Pygame loop. This part is good.
# --- Callback function to receive signals from the chatbot ---
def handle_chatbot_signal(signal_data):
    """Receives a signal dict from the chatbot and posts a Pygame event."""
    trigger_lore_panel_update() 

    if isinstance(signal_data, dict):
        action_type = signal_data.get("type")

        if action_type == "change_background":
            image_path = signal_data.get("image_path")
            if image_path:
                print(f"Signal type 'change_background' received with path: {image_path}, posting event.")
                pygame.event.post(pygame.event.Event(config.CHANGE_BACKGROUND_EVENT, image_path=image_path))

                current_room = chatbot.state_manager.room_manager._find_room_by_id(chatbot.state_manager.get_current_room_id())

                loc_music = current_room.get("music")

                music_player.play_new_song(f"style/sounds/music/rooms/{loc_music}.mp3")
            else:
                 print("Signal 'change_background' received but no 'image_path' in data.")

        elif action_type == "shake_circle":
            print("Signal type 'shake_circle' received, posting SHAKE_CIRCLE_EVENT.")
            pygame.event.post(pygame.event.Event(config.SHAKE_CIRCLE_EVENT))


        elif action_type == "TTS_AUDIO":
            raw_sound = signal_data.get("raw_audio_data")
            if raw_sound:
                print(f"Signal type 'TTS_AUDIO' received with raw audio data.")
                pygame.event.post(pygame.event.Event(config.TTS_PYGAME_SOUND_EVENT, raw_audio_data=raw_sound))
            else:
                print("Signal 'TTS_AUDIO' received but no 'raw_audio_data' in data.")

        elif action_type == "function_called":
            function_name = signal_data.get("function_name")
            function_result = signal_data.get("function_result")
            muted = signal_data.get("muted", False)
            string_result = f"Called: {function_name}, result: {function_result}"
            if muted:
                print("DEBUG DEBUG Mute recieved, trying to set display redacted response: ")
                max_length = 50
                shortened_function_string = function_result[:max_length] + "..."
                string_result = f"Called: {function_name}, result truncated: {shortened_function_string}"
            print(f"Signal type 'function_called' received, posting CHATBOT_RESPONSE_EVENT (system).")
            pygame.event.post(pygame.event.Event(config.CHATBOT_RESPONSE_EVENT, text=string_result, msg_type="system"))
            pygame.event.post(pygame.event.Event(config.SHAKE_CIRCLE_EVENT))

        elif action_type == "emote_changed":
            emote_name = signal_data.get("emote_name")
            sound_path = signal_data.get("sound_path")

            emote_animations = {
                "sad": animation.start_sad_animation,
                "happy": animation.start_happy_animation,
                "angry": animation.start_angry_animation,
                "excited": animation.start_excited_animation,
                "thinking": animation.start_thinking_animation,
                "curious": animation.start_curious_animation,
                "confused": animation.start_confused_animation,
            }

            # Look up the emote name in the dictionary and call the function if found
            if emote_name in emote_animations:
                print(f"Signal type 'emote_changed' received ({emote_name})")
                emote_animations[emote_name]() # Call the function associated with the emote
            elif emote_name is not None: # Handle cases where emote_name might be missing but sound_path is present
                 print(f"Signal type 'emote_changed' received with unhandled emote: {emote_name}")


            if sound_path:
                print(f"Signal type 'emote_changed' received with sound path: {sound_path}. Using Jukebox.")
                music_player.play_sound_effect(sound_path)
        elif action_type == "sleep":
            sleep_duration_seconds = signal_data.get("duration", 0)
            if sleep_duration_seconds > 0:
                sleep_duration_ms = sleep_duration_seconds * 1000
                print(f"Signal type 'sleep' received with duration: {sleep_duration_seconds}s, posting START_SLEEP_EVENT.")
                pygame.event.post(pygame.event.Event(config.START_SLEEP_EVENT, duration_ms=sleep_duration_ms))
            else:
                 print(f"Signal 'sleep' received with invalid or zero duration: {sleep_duration_seconds}")

        elif action_type == "stat_changed": # This signal does not change the stats for the backend, it is only signaling changes from it 
            stat_name = signal_data.get("stat_name")
            new_value = signal_data.get("new_value")
            if isinstance(stat_name, str) and isinstance(new_value, (int, float)):
                clamped_value = max(0.0, min(200.0, new_value))
                print(f"Signal type 'stat_changed' received for {stat_name} with value {new_value}, posting STAT_CHANGED_EVENT.")
                pygame.event.post(pygame.event.Event(config.STAT_CHANGED_EVENT, stat_name=stat_name.lower(), new_value=clamped_value))
            else:
                 print(f"Signal 'stat_changed' received with invalid data. stat_name: {stat_name}, new_value: {new_value}")

        # --- NEW: Handle Inventory Signals ---
        elif action_type == "room_inventory":
            # Expecting a list of strings under 'item_list' key
            item_list_data = signal_data.get("item_list")
            #print(f"Signal type 'room_inventory' received with {len(item_list_data)} items. Posting ROOM_INVENTORY_EVENT.")

            if isinstance(item_list_data, list):
                 pygame.event.post(pygame.event.Event(config.ROOM_INVENTORY_EVENT, item_list=item_list_data))
            else:
                 print("Signal 'room_inventory' received but no valid 'item_list' (list of strings) in data.")

        elif action_type == "player_inventory":
             # Expecting a list of strings under 'item_list' key
            item_list_data = signal_data.get("item_list")
            #print(f"Signal type 'player_inventory' received with {len(item_list_data)} items. Posting PLAYER_INVENTORY_EVENT.")
            if isinstance(item_list_data, list):
                 #print(f"Signal type 'player_inventory' received with {len(item_list_data)} items. Posting PLAYER_INVENTORY_EVENT.")
                 pygame.event.post(pygame.event.Event(config.PLAYER_INVENTORY_EVENT, item_list=item_list_data))
            else:
                 print("Signal 'player_inventory' received but no valid 'item_list' (list of strings) in data.")

        # --- NEW: Handle Show Icon Popup Signal ---
        elif action_type == "show_icon_popup":
            icon_path = signal_data.get("icon_path")
            duration_ms = signal_data.get("duration_ms", 2000) # Default duration 2 seconds
            popup_type = signal_data.get('popup_type', 1) # Default popup type

            if icon_path:
                 print(f"Signal type 'show_icon_popup' received with path: {icon_path}. Posting SHOW_ICON_POPUP_EVENT.")
                 pygame.event.post(pygame.event.Event(config.SHOW_ICON_POPUP_EVENT, icon_path=icon_path, duration_ms=duration_ms, popup_type=popup_type))
            else:
                 print("Signal 'show_icon_popup' received but no 'icon_path' in data.")

        # --- NEW: Handle Show Icon Popup Signal ---
        elif action_type == "show_message_popup":
            message = signal_data.get("message")
            color = signal_data.get("color", None) # Defaults to a set color if not given

            if message:
                 print(f"Signal type 'show_message_popup' received with path: {message}. Posting MESSAGE_POPUP.")
                 pygame.event.post(pygame.event.Event(config.MESSAGE_POPUP, message=message, color=color))
            else:
                 print("Signal 'show_message_popup' received but no 'message' in data.")

        else:
             print(f"Unknown signal type received: {action_type}")
    else:
        print(f"Received signal data in unexpected format (not a dict): {signal_data}")

if mock_running: # Mock configuration, leave as is
    # --- Mock Chatbot Initialization ---
    chatbot = None
    chatbot_available = False
    try:
        chatbot = MockChatbot( # Use the mock class
            signal_callback=handle_chatbot_signal,
            config_manager=config_manager
        )
        chatbot_available = True
        print(f"{type(chatbot).__name__} initialized successfully with signal callback.")
    except Exception as e:
        # Error handling is still useful in case the mock itself has an issue
        print(f"Error initializing Mock Chatbot: {type(e).__name__}: {e}")
        chatbot_available = False
        chatbot = None


else:
    # Actual chatbot initialization
    # --- Chatbot Initialization ---
    chatbot = None
    chatbot_available = False
    try:
        chatbot = CLIChatbot(
            signal_callback=handle_chatbot_signal,
            config_manager=config_manager,
            bots_archive_dir=bots_archive_dir
        )
        chatbot_available = True
        print(f"{type(chatbot).__name__} initialized successfully with signal callback.")
    except Exception as e:
        print(f"Error initializing Chatbot: {type(e).__name__}: {e}")
        chatbot_available = False
        chatbot = None # Ensure chatbot is None if initialization failed


steps=chatbot.state_manager.get_steps()
size=calculate_sized_by_steps(steps, config.CIRCLE_RADIUS, 100)
state.current_radius=size
print(f"setting up pets size as {size}")


# Ensure state.pet_color is initialized to the default before potential load/selection
state.pet_color = config.GREEN # Or use the default from state.py (which is already green)

if chatbot_available and chatbot and hasattr(chatbot.state_manager, 'is_color_configured') and callable(chatbot.state_manager.is_color_configured):
    if not chatbot.state_manager.is_color_configured():
        # --- Run Color Selection UI ---
        print("Color not configured. Starting color selection UI...")
        # Call the blocking UI function
        selected_color = gui_color_selector.run_color_selection_ui(screen, font) # Pass screen and font

        if selected_color is not None:
            # Color was selected, save it via the chatbot
            print(f"Color selected: {selected_color}. Saving configuration...")
            chatbot.state_manager.set_pet_color(selected_color)
            chatbot.state_manager.set_color_configured(True)
            # Update runtime state with the selected color
            state.pet_color = selected_color
            print("Color configuration saved and applied.")
        else:
            # User quit during color selection
            print("User quit during color selection. Exiting game.")
            running = False # Set main game loop flag to False

    else:
        # --- Load Configured Color ---
        print("Color already configured. Loading saved color...")
        # Load the saved color from the chatbot's state manager
        loaded_color = chatbot.state_manager.get_pet_color()
        if loaded_color: # Check if get_pet_color returned a valid color
            state.pet_color = loaded_color # Update runtime state
            print(f"Loaded pet color: {state.pet_color}")
        else:
             # This case should be rare if validation works, but good to handle
             print("Error loading pet color from config. Using default green.")
             state.pet_color = config.GREEN # Fallback to default green
else:
    # Chatbot unavailable, color configuration is skipped. Use default color.
    print("Chatbot not available. Skipping color configuration/load. Using default green.")
    state.pet_color = config.GREEN


# --- Initial Background Load ---
# Determine starting location based on chatbot if available, otherwise use default
starting_location_name = "bedroom" # Default
if chatbot_available and chatbot and hasattr(chatbot.state_manager, 'get_current_room_name'):
     try:
        # Call get_current_location only if the method exists and is callable
        if callable(getattr(chatbot.state_manager, 'get_current_room_name', None)):
             loc = chatbot.state_manager.get_current_room_name()
             if loc: # Use chatbot location if it returned something
                  starting_location_name = loc
                  print("found starting location!")
                  print(f"Getting initial location from chatbot: {starting_location_name}")
             else: # Fallback if chatbot returned None or empty string
                  print("Chatbot get_current_location returned empty. Using default 'bedroom'.")
                  starting_location_name = "bedroom"
        else:
             print("Chatbot instance does not have a callable 'get_current_location' method.")
             starting_location_name = "bedroom" # Fallback
     except Exception as e:
        print(f"Error getting initial location from chatbot: {e}")
        starting_location_name = "bedroom" # Fallback
else:
    print("Chatbot instance not available or does not have 'get_current_location'. Using default 'bedroom'.")




# --- NEW: Initial Wellness State Load ---
if chatbot_available and chatbot and hasattr(chatbot.state_manager, 'get_stats'):
    try:
        # Call get_wellness_states only if the method exists and is callable
        if callable(getattr(chatbot.state_manager, 'get_stats', None)):
             stats_data = chatbot.state_manager.get_stats(True)
             if isinstance(stats_data, dict):
                  # Check if the expected keys are present and values are numbers
                  all_keys_present = all(key in stats_data for key in state.pet_stats.keys())
                  all_values_numeric = all(isinstance(value, (int, float)) for value in stats_data.values())

                  if all_keys_present and all_values_numeric:
                       # Update state.pet_stats with loaded values, clamping defensively
                       for stat_name, value in stats_data.items():
                           state.pet_stats[stat_name.lower()] = max(0.0, min(200.0, value))
                       print(f"Getting initial wellness states from chatbot: {state.pet_stats}")
                  else:
                       print(f"Chatbot get_stats returned unexpected data format: {stats_data}. Using default state.")
             elif stats_data is None:
                  print("Chatbot get_stats returned None. Using default state.")
             else:
                  print(f"Chatbot get_stats returned non-dict data: {stats_data}. Using default state.")
        else:
             print("Chatbot instance does not have a callable 'get_stats' method. Using default state.")
    except Exception as e:
        print(f"Error getting initial wellness states from chatbot: {e}. Using default state.")
else:
    print("Chatbot instance not available or does not have 'get_stats'. Using default state.")


def add_items(items_list, room):
    """Adds items to the room with a chatbot function connected to its environment with add_items_room"""
    current_time_ms = pygame.time.get_ticks()
    # Check if input is generally locked (by sleep or panel)
    # This check is done *before* calling add_items now via mouse handler
    # but keeping a check here is a safeguard if this function is called directly elsewhere
    if current_time_ms < state.autonomous_action_paused_until_ms or state.inventory_panel_visible:
        block_reason = "bot is resting." if current_time_ms < state.autonomous_action_paused_until_ms else "inventory panel is open."
        print(f"Input locked - {block_reason}. Ignoring add items command.")
        gui.gui_text_utils.add_message_to_history(f"Cannot add items while {block_reason}", 'system')
        return

    gui.gui_text_utils.add_message_to_history(f"Adding items to room...", "system")
    try:
        if chatbot_available and chatbot and hasattr(chatbot.state_manager, 'create_item') and callable(chatbot.state_manager.create_item):
            chatbot.state_manager.create_item(target_location="room", target_location_id=room, item_creation_data=items_list) # Adds items to the specified room and triggers signals to update the GUI
            room_name=chatbot.state_manager.get_room_name(room)
            # add message to AI memory chain, does not call the AI yet, but it adds informatio to its memory
            chatbot.memory.save_to_memory(string_to_save=f"A package of helpful items has been delivered for you in the room {room_name}.", memory_type="short_term", tag="user")

            # Append the text into GUI chat window
            gui.gui_text_utils.add_message_to_history(f"Items added successfully!", "system")

        else:
            error_message = "Chatbot not available or does not support adding items."
            print(error_message)
            gui.gui_text_utils.add_message_to_history(error_message, 'error')

    except Exception as e:
        error_message = f"System Error preparing add items instruction: {type(e).__name__}: {e}"
        print(error_message)
        gui.gui_text_utils.add_message_to_history(error_message, 'error')


# Initialize the GUI module. This also calculates and stores button/panel rects internally in gui.py.
gui.gui_core.init_gui_elements(font, line_height, 200)

def get_current_room_image():
    """Retrieves the list of types for the current room."""
    current_id = chatbot.state_manager.get_current_room_id()
    room = chatbot.state_manager.room_manager._find_room_by_id(current_id) # Assuming _find_room_by_id is accessible or use a public getter
    if room and "image" in room:
        print(f"DEBUG: Current room image: {room['image']}")
        return room["image"]
    print("DEBUG: No room types found or room not found.")
    return "" # Return empty list if no types found
current_image=get_current_room_image()

gui.gui_core.load_and_set_background(f"{current_image}.jpg")

# Initial popup, splash screen.
gui.gui_popups.show_image_popup("style/images/house_splash_v2.png", 5000, 1000, 3000, popup_type=0) # Main screen image popup type

current_gui_rects=gui.gui_core.get_gui_rects()


history_display_area = current_gui_rects['history_display_area']

# --- Initial Inventory Load ---
try:
    if chatbot_available and chatbot and hasattr(chatbot.state_manager, 'list_inventories') and callable(getattr(chatbot.state_manager, 'list_inventories', None)):
         print("Attempting to get initial inventories from chatbot...")
         list_room_items_names_raw, list_inventory_item_names_raw = chatbot.state_manager.list_inventories(formatted=True)

         # MODIFIED: Check and pre-calculate initial data
         if isinstance(list_room_items_names_raw, list) and isinstance(list_inventory_item_names_raw, list):
             # Ensure gui is initialized before preparing data
             # Assuming gui.init_gui is called earlier in setup
             if gui.gui_core._font is None: # Check if gui initialization was successful
                  print("GUI font not initialized. Cannot prepare inventory data. Initial inventories will be empty.")
                  state.room_inventory_list = []
                  state.player_inventory_list = []
             else:
                 state.room_inventory_list = [gui.gui_inventory.prepare_inventory_item_data(item) for item in list_room_items_names_raw]
                 state.player_inventory_list = [gui.gui_inventory.prepare_inventory_item_data(item) for item in list_inventory_item_names_raw]
                 print(f"Loaded and prepared initial inventories. Room: {len(state.room_inventory_list)} items, Player: {len(state.player_inventory_list)} items.")
         else:
             print("Chatbot get_inventories returned non-list data. Initial inventories will be empty.")
             state.room_inventory_list = []
             state.player_inventory_list = []

    else:
        print("Chatbot not available or does not have get_inventories method. Initial inventories will be empty.")
        state.room_inventory_list = [] # Ensure lists are initialized even if chatbot fails
        state.player_inventory_list = [] # Ensure lists are initialized even if chatbot fails


except Exception as e:
    print(f"Error getting initial inventories from chatbot: {e}. Initial inventories will be empty.")
    state.room_inventory_list = [] # Ensure lists are initialized on error
    state.player_inventory_list = [] # Ensure lists are initialized on error


# Get the calculated rects from gui.py after initialization if needed in game.py
# Note: We *can* get them here, but we don't strictly *need* them for click detection
# if we use gui.get_package_button_click_regions() and gui.get_button_rects().
# Let's continue using the gui functions to access rects where possible for cleaner separation.
inventory_button_rects = gui.gui_core.get_button_rects()
inventory_panel_rects = gui.gui_core.get_panel_rects()
inventory_toggle_button_rect = inventory_button_rects.get('inventory_toggle')
inventory_panel_main_rect = inventory_panel_rects.get('inventory_panel') # The big panel rect
room_list_area_rect = inventory_panel_rects.get('room_list_area') # Area for room list items
player_list_area_rect = inventory_panel_rects.get('player_list_area') # Area for player list items

mute_button_rect = inventory_button_rects.get('mute_button')

# --- Worker Function for Chatbot API Call ---
def chatbot_worker(user_input, input_role, chatbot_instance):
    """
    This function runs in a separate thread.
    It calls the chatbot's process_input and posts a Pygame event
    with the result (text response) or signals.
    """
    # print(f"Chatbot worker thread started for role: {input_role} with input: {user_input[:50]}...") # Debug

    response_text = None
    message_type = 'bot' # Default type for a bot response

    try:
        # This is the blocking call that now runs in this separate thread
        response_text = asyncio.run(chatbot_instance.process_input(user_input, role=input_role))

        # process_input might return None or empty if it only triggered signals
        # In this case, we don't need to post a text response event.
        if response_text is None or not response_text.strip():
             # print("Chatbot process_input returned no text, likely only signals were triggered.") # Debug
             return # No text response to post

        message_text = response_text.strip()
        # Determine the type based on role or content if needed, default is 'bot'
        # If using a 'system_instruction' role, perhaps the response is still 'bot' narrative?
        # Let's stick to 'bot' for the *response text* itself, unless process_input
        # explicitly indicates otherwise (which our current signal handling does separately).
        message_type = 'bot'

    except Exception as e:
        message_text = f"Bot Error: {type(e).__name__}: {e}"
        message_type = 'error' # Errors are 'error' type
        print(f"Error in chatbot worker thread: {message_text}")

    # Post a custom event to the Pygame event queue
    # This is a thread-safe way to communicate back to the main loop
    # Ensure the message text is not empty before posting
    if message_text:
         # print(f"Posting CHATBOT_RESPONSE_EVENT (type: {message_type}) for text: {message_text[:50]}...") # Debug
         new_response_event = pygame.event.Event(config.CHATBOT_RESPONSE_EVENT, text=message_text, msg_type=message_type)
         pygame.event.post(new_response_event)
    # else: print("Chatbot worker had no text response to post.") # Debug


# --- Function to Start the Chatbot Request Asynchronously ---
def start_chatbot_request(user_input, input_role='user'):
    """Starts a new thread to process the chatbot request."""
    global chatbot_available, chatbot
    current_time_ms = pygame.time.get_ticks()

    clean_hover() # Clean hover state on any kind of bot action

    # Also check if inventory panel is open - block user input requests if it is
    if input_role == 'user' and (current_time_ms < state.autonomous_action_paused_until_ms):
         block_reason = "bot is resting." if current_time_ms < state.autonomous_action_paused_until_ms else "inventory panel is open."
         print(f"Input locked - {block_reason}. Cannot process user input request.")
         gui.gui_text_utils.add_message_to_history(f"Cannot send input while {block_reason}", 'system')
         return False

    if chatbot_available and chatbot:
        print(f"Starting chatbot request thread (role: {input_role}) for input: {user_input[:50]}...")
        state.chatbot_is_processing=True
        thread = threading.Thread(target=chatbot_worker, args=(user_input, input_role, chatbot))
        thread.start()
        return True
    else:
        print("Chatbot not available, cannot start request thread.")
        return False
    


# --- Worker Function for Garden Tick ---
def garden_tick_worker(chatbot_instance):
    """
    This function runs in a separate thread to call the garden manager's tick.
    It posts a system message on completion or error.
    """
    if not chatbot_instance or \
    not hasattr(chatbot_instance, 'ai') or \
    not hasattr(chatbot_instance.ai, 'functions_builder') or \
    not hasattr(chatbot_instance.ai.functions_builder, 'garden_manager') or \
    not callable(getattr(chatbot_instance.ai.functions_builder.garden_manager, 'tick', None)):
        print("Chatbot or garden manager not fully available for tick. Skipping.")
        return

    print("Garden tick worker thread started.")
    try:
        chatbot_instance.ai.functions_builder.garden_manager.tick()
        print("Garden tick processed successfully.")


        current_room_info = chatbot_instance.functions_builder.get_current_room_info()

        if not isinstance(current_room_info, dict):
            current_room_info = {} # Fallback to empty dict

        # Post the event to the main Pygame thread with the fresh data
        pygame.event.post(pygame.event.Event(config.UPDATE_LORE_DISPLAY_EVENT, room_data=current_room_info))

    except Exception as e:
        error_message = f"Error in garden tick worker thread: {type(e).__name__}: {e}"
        print(error_message)

        
# --- Function to Start the Garden Tick Asynchronously ---
def start_garden_tick_request():
    """
    Starts a new thread to process the garden tick.
    Checks if the main chatbot processing is currently active to avoid conflicts.
    """
    global chatbot_available, chatbot
    if not chatbot_available or not chatbot:
        #print("Chatbot not available, cannot start garden tick.")
        return False

    # Only proceed if the chatbot is NOT currently processing a user request
    if state.chatbot_is_processing: # <--- UNCOMMENT THIS LINE
        #print("Chatbot is currently busy processing, deferring garden tick.") # Keep this line for debugging if needed
        return False # And this line

    #print("Starting garden tick request thread.")

    thread = threading.Thread(target=garden_tick_worker, args=(chatbot,))
    thread.start()
    return True

def clean_hover():
    """
    To clean up hover state variables if necessary.
    """
    state.hover_stat=None
    state.hovered_package_identifier=None

CURSOR_INTERVAL = 500 # Milliseconds

# --- Game Loop ---
running = True
clock = pygame.time.Clock()

# Initialize music_player to None. It will be initialized later
# when the initial popup phase is over.
music_player = None

state.last_activity_time = pygame.time.get_ticks()
print(f"Initial last_activity_time set to {state.last_activity_time} ms.")

# NEW: Garden Tick Timer Initialization
state.next_garden_tick_time = pygame.time.get_ticks() + config.GARDEN_TICK_INTERVAL_MS
print(f"Next garden tick scheduled for {state.next_garden_tick_time} ms.")

# only direct chat with the bot should count as interaction
state.hovered_package_identifier = None # Initialize a variable to track hover state

is_input_locked_by_state=False

while running:
    dt = clock.tick(60)
    current_time_ms = pygame.time.get_ticks()



    # Update popups state (position, alpha, removal)
    gui.gui_popups.update_popups(current_time_ms)

    state.cursor_timer += dt
    if state.cursor_timer >= CURSOR_INTERVAL and state.cursor_active:
        state.cursor_visible = not state.cursor_visible
        state.cursor_timer = 0

    if state.cursor_active:
        state.last_activity_time = current_time_ms # Cursor activity resets the autonomous action timer

    if state.chatbot_is_processing:
        state.last_activity_time = current_time_ms

    is_currently_asleep = current_time_ms < state.autonomous_action_paused_until_ms

    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            break

        gui.handle_gui_event(event)


        # --- NEW: Fetch the LATEST GUI rects for event detection ---
        # Do this at the start of each event loop iteration
        # so collision checks use the most current dimensions.
        current_button_rects = gui.gui_core.get_button_rects()
        inventory_toggle_button_rect = current_button_rects.get('inventory_toggle')
        mute_button_rect = current_button_rects.get('mute_button') # Also fetch mute button
        panel_toggle_button_rect = current_button_rects.get('panel_toggle') # And panel toggle button
        lore_toggle_button_rect = current_button_rects.get('lore_toggle') # NEW: Fetch lore toggle button rect

        # For inventory panel specific areas, fetch them only if the panel is visible
        # to avoid unnecessary lookups when it's closed.
        room_list_area_rect = None
        player_list_area_rect = None
        history_display_area = gui.gui_core.get_gui_rects().get('history_display_area') # Always get chat history area, it's always relevant if panel is visible

        if state.inventory_panel_visible:
            current_panel_rects = gui.gui_core.get_panel_rects()
            room_list_area_rect = current_panel_rects.get('room_list_area')
            player_list_area_rect = current_panel_rects.get('player_list_area')



        # --- Always Handle Custom Events (like signals from chatbot) ---
        # These events should process regardless of the inventory panel state
        if event.type == config.CHANGE_BACKGROUND_EVENT:
            print(f"Main loop processing CHANGE_BACKGROUND_EVENT")
            image_path = getattr(event, 'image_path', None)
            if image_path: gui.gui_core.load_and_set_background(image_path)
            else: print("CHANGE_BACKGROUND_EVENT received but no 'image_path' attribute.")
            continue
        
        elif event.type == config.TTS_PYGAME_SOUND_EVENT:
            raw_audio_data = getattr(event, 'raw_audio_data', None)
            if raw_audio_data:
                print("Main loop processing TTS_PYGAME_SOUND_EVENT")
                # Play the raw audio data using music_player
                if music_player:
                    music_player.play_raw_sound_effect(raw_audio_data)
                else:
                    print("Music player not initialized. Cannot play TTS audio.")
            else:
                print("TTS_PYGAME_SOUND_EVENT received but no 'raw_audio_data' attribute.")
            continue

        elif event.type == config.SHAKE_CIRCLE_EVENT:
            print("Main loop processing SHAKE_CIRCLE_EVENT")
            animation.start_circle_shake()
            continue

        elif event.type == config.CHATBOT_RESPONSE_EVENT:
             response_text = getattr(event, 'text', None)
             message_type = getattr(event, 'msg_type', 'bot')
             steps=chatbot.state_manager.get_steps()
             size=calculate_sized_by_steps(steps, config.CIRCLE_RADIUS, 100)
             state.current_radius=size
             if response_text:
                 gui.gui_text_utils.add_message_to_history(response_text, message_type)
                 # Activity from bot only resets idle timer if it's not a 'system' message
                 # System messages might just be info, not necessarily a bot action response
                 animation.start_circle_shake() # Shake the circle on bot activity

                 if message_type != "system":
                     state.last_activity_time = current_time_ms
                     state.chatbot_is_processing=False # Bot finished processing user/system request

                 print(f"Bot response received via event (type: {message_type}). Idle timer reset? {'Yes' if message_type != 'system' else 'No'}. Time: {state.last_activity_time}")

             continue


        elif event.type == config.UPDATE_LORE_DISPLAY_EVENT: # NEW EVENT TYPE
            # 1. Get the dictionary passed as 'room_data' from the event
            room_data = getattr(event, 'room_data', {}) # Default to empty dict if not present

            # 2. Extract 'title' and 'body' SAFELY from the room_data dictionary
            #    using .get() to provide default values if keys are missing
            lore_title = room_data.get('title', 'Info Title Not Found')
            lore_body = room_data.get('body', 'No content received for this info entry.')

            print(f"Main loop processing UPDATE_LORE_DISPLAY_EVENT. Title: {lore_title}")
            
            # 3. Prepare and store the content data in state
            state.lore_panel_content = gui_lore_panel.prepare_lore_content_data(lore_title, lore_body)
            
            # 4. Reset scroll to top ONLY IF the panel is visible.
            #    This prevents constant scroll resets if the room changes while the panel is closed.
            if state.lore_panel_visible:
                state.lore_panel_scroll_y = 0
            continue # Event consumed


        elif event.type == config.ROOM_INVENTORY_EVENT:
            item_list_raw = getattr(event, 'item_list', None) # Get the raw list of strings
            if isinstance(item_list_raw, list):
                print(f"Main loop processing ROOM_INVENTORY_EVENT. Updating room inventory state.")
                # MODIFIED: Pre-calculate data for each item
                state.room_inventory_list = [gui.gui_inventory.prepare_inventory_item_data(item) for item in item_list_raw]
                print(f"Prepared room inventory data for {len(state.room_inventory_list)} items.")
                # Reset scroll to top when new data arrives
                state.room_inventory_scroll_y = 0
            else: print(f"ROOM_INVENTORY_EVENT received with invalid data.")
            continue

        elif event.type == config.PLAYER_INVENTORY_EVENT:
            item_list_raw = getattr(event, 'item_list', None) # Get the raw list of strings
            if isinstance(item_list_raw, list):
                print(f"Main loop processing PLAYER_INVENTORY_EVENT. Updating player inventory state.")
                # MODIFIED: Pre-calculate data for each item
                state.player_inventory_list = [gui.gui_inventory.prepare_inventory_item_data(item) for item in item_list_raw]
                #print(f"Prepared player inventory data for {len(state.player_inventory_list)} items.")
                state.player_inventory_scroll_y = 0 # Reset scroll
            else: print(f"PLAYER_INVENTORY_EVENT received with invalid data.")
            continue


        # --- 1. Fix the START_SLEEP_EVENT handler to properly calculate end time ---
        elif event.type == config.START_SLEEP_EVENT:
            sleep_duration_ms = getattr(event, 'duration_ms', 0)
            if sleep_duration_ms > 0:
                # Calculate sleep end time
                sleep_end_time_ms = current_time_ms + sleep_duration_ms

                # Update the autonomous_action_paused_until_ms to be AFTER the sleep ends
                # This ensures no autonomous action triggers during sleep
                state.autonomous_action_paused_until_ms = sleep_end_time_ms

                # Also reset the last_activity_time to the end of sleep
                # This prevents autonomous action from triggering immediately after sleep
                state.last_activity_time = sleep_end_time_ms

                print(f"Sleep signal processed in main loop. Locking input until {state.autonomous_action_paused_until_ms} ms (for {sleep_duration_ms} ms).")
                gui.gui_text_utils.add_message_to_history(f"Entering sleep state for {sleep_duration_ms // 1000} seconds.", 'system')
            else:
                print(f"Received START_SLEEP_EVENT with zero or negative duration.")
            continue

        elif event.type == config.MESSAGE_POPUP:
            message = getattr(event, 'message', "")
            color = getattr(event, 'color', None)
            gui.gui_popups.show_popup_message(message, color)
            continue

        elif event.type == config.STAT_CHANGED_EVENT:
            stat_name = getattr(event, 'stat_name', None)
            new_value = getattr(event, 'new_value', None)
            if stat_name in state.pet_stats and isinstance(new_value, (int, float)):
                 old_value = state.pet_stats[stat_name]
                 state.pet_stats[stat_name] = new_value
                 print(f"Main loop processed STAT_CHANGED_EVENT: Updated {stat_name} to {state.pet_stats[stat_name]:.3f}")
                 change = new_value - old_value
                 formatted_change = f"{change:+.3f}" if abs(change) > 0.001 else "" # Add + for positive changes, only show if change is significant
                 formatted_current_value = f"{state.pet_stats[stat_name]:.1f}" # Maybe format current value differently?
                 # Show popup only if there was a significant change
                 if abs(change) > 0.001: # Threshold for showing popup
                     # Adjust popup text based on whether there was a visible change value
                     popup_text = f"{stat_name.capitalize()}: {formatted_current_value}"
                     if formatted_change: # Only add change if it's shown
                         popup_text += f" ({formatted_change})"

                     # Choose red or green depending on positive or negative change
                     if change >= 0.0:
                         color=(0, 255, 0) # Green for positive/no change
                     else:
                         color=(255, 0, 0) # Red for negative

                     gui.gui_popups.show_popup_message(popup_text, color)
                 # else:
                 #     print(f"Stat change for {stat_name} was negligible ({change:.3f}), not showing popup.") # Debug negligible changes

            else: print(f"Main loop received invalid STAT_CHANGED_EVENT data. stat_name: {stat_name}, new_value: {new_value}")
            continue



        # --- NEW: Handle SHOW_ICON_POPUP_EVENT ---
        elif event.type == config.SHOW_ICON_POPUP_EVENT:
            icon_path = getattr(event, 'icon_path', None)
            duration_ms = getattr(event, 'duration_ms', 2000) # Default duration from config/signal
            popup_type = getattr(event, 'popup_type', 1) # Default popup type

            print(f"🔺🔺🔺🔺🔺 Main loop processing SHOW_ICON_POPUP_EVENT for icon: {icon_path}, duration: {duration_ms} ms, type: {popup_type}")
            if icon_path:
                 print(f"Main loop processing SHOW_ICON_POPUP_EVENT for icon: {icon_path}")
                 gui.gui_popups.show_image_popup(icon_path, duration_ms, popup_type=popup_type) # Call the new GUI function
            else:
                 print("SHOW_ICON_POPUP_EVENT received but no 'icon_path' attribute.")
            continue # Consume event


        # --- Handle Input/Clicks based on Panel Visibility ---

        if state.inventory_panel_visible:
            # --- Inventory Panel IS Open (Modal Behavior) ---

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state.lore_panel_visible: # NEW: Prioritize closing lore panel
                        print("Escape pressed. Closing lore panel.")
                        state.lore_panel_visible = False # Snap closed
                        continue # Consume the event
                    elif state.inventory_panel_visible:
                        print("Escape pressed. Closing inventory panel.")
                        state.inventory_panel_visible = False
                        continue
                    else:
                        running = False # Exit the game
                        continue

            if event.type == pygame.MOUSEBUTTONDOWN:
                
                # Check inventory toggle button click (to close)
                if inventory_toggle_button_rect and inventory_toggle_button_rect.collidepoint(event.pos) and event.button == 1:
                    print("Inventory toggle button clicked while panel open. Closing panel.")
                    state.inventory_panel_visible = False
                    continue

                # Handle Mouse Wheel Scrolling over the panel list areas
                if event.button in (4, 5): # 4: up, 5: down
                    scroll_speed = config.SCROLL_SPEED * (-1 if event.button == 4 else 1) # Negative for up, positive for down
                    # Check if mouse is over the room list area
                    if room_list_area_rect and room_list_area_rect.collidepoint(event.pos):
                        state.room_inventory_scroll_y += scroll_speed
                        # Clamp scroll
                        # MODIFIED: Removed draw_width argument
                        room_content_height = gui.gui_inventory.calculate_list_height(state.room_inventory_list)
                        max_room_scroll = max(0, room_content_height - room_list_area_rect.height)
                        state.room_inventory_scroll_y = max(0, min(state.room_inventory_scroll_y, max_room_scroll))
                        #print(f"Room list scrolled. Current: {state.room_inventory_scroll_y}, Max: {max_room_scroll}")
                        continue # Consume event

                    # Check if mouse is over the player list area
                    elif player_list_area_rect and player_list_area_rect.collidepoint(event.pos):
                        state.player_inventory_scroll_y += scroll_speed
                        # Clamp scroll
                        # MODIFIED: Removed draw_width argument
                        player_content_height = gui.gui_inventory.calculate_list_height(state.player_inventory_list)
                        max_player_scroll = max(0, player_content_height - player_list_area_rect.height)
                        state.player_inventory_scroll_y = max(0, min(state.player_inventory_scroll_y, max_player_scroll))
                        #print(f"Player list scrolled. Current: {state.player_inventory_scroll_y}, Max: {max_player_scroll}")
                        continue # Consume event

                # If the click wasn't on the toggle button or handled by scrolling, ignore it
                #continue # Simply do nothing for other events inside the panel

        #else:
        # --- Inventory Panel IS NOT Open (Normal Game Behavior) ---
            # Check the combined input lock state FIRST for user input events

        # # --- 2. Improve the is_currently_asleep check to use absolute time comparison ---
        # # Before the drawing section, update the is_currently_asleep calculation:
        # is_currently_asleep = current_time_ms < state.autonomous_action_paused_until_ms
        # is_input_locked_by_state = is_currently_asleep or state.chatbot_is_processing



        # --- NEW: Handle MOUSEMOTION for hover effect ---
        if event.type == pygame.MOUSEMOTION:
            # state.inventory_b_hover=False
            # if not is_input_locked_by_state and inventory_toggle_button_rect.collidepoint(event.pos) and not state.lore_panel_visible:
            #     #print("over inventory button")
            #     state.inventory_b_hover=True
            #     continue

            if not is_input_locked_by_state and not state.inventory_panel_visible and not state.lore_panel_visible:
                package_hover_regions = gui.gui_care_package.get_package_button_click_regions()
                current_hovered_identifier = None  # Local variable to find the new hovered item
                stats_rects = gui.gui_stat_icons.get_stat_icon_rects()

                for identifier, rect in package_hover_regions:
                    if rect.collidepoint(event.pos):
                        current_hovered_identifier = identifier
                        break  # Found a hover, no need to check others

                # Update the global hover state variable only if it has changed
                if state.hovered_package_identifier != current_hovered_identifier:
                    state.hovered_package_identifier = current_hovered_identifier
                    state.package_scroll_y = 0
                    # You can print for debugging here if needed
                    #print(f"Hovering over: {state.hovered_package_identifier}")
                
                state.hover_stat=None
                for name, rect in stats_rects.items():
                    if rect.collidepoint(event.pos):
                        state.hover_stat = name
                        #print(name)
                        break
            continue


        # Handle Mouse Button events (chat scroll, inventory toggle, NEW care package buttons)
        if event.type == pygame.MOUSEBUTTONDOWN:
                #state.last_activity_time = current_time_ms #

                # NEW: Handle Lore Panel Toggle Button click
                if lore_toggle_button_rect and lore_toggle_button_rect.collidepoint(event.pos) and event.button == 1:
                    if not state.lore_panel_visible: # Only open if not already open
                        print("Lore toggle button clicked. Opening panel.")
                        state.lore_panel_visible = True
                        state.lore_panel_scroll_y = 0 # Reset scroll
                        trigger_lore_panel_update()
                    continue # Consume event

                if not state.lore_panel_visible:
                    # Check inventory toggle button click (to open)
                    if inventory_toggle_button_rect and inventory_toggle_button_rect.collidepoint(event.pos) and event.button == 1:
                        print("Inventory toggle button clicked while panel closed. Opening panel.")
                        state.inventory_panel_visible = True
                        # Reset scroll positions when opening
                        state.room_inventory_scroll_y = 0
                        state.player_inventory_scroll_y = 0
                        continue # Consume event

                    # Check if the click is within the history display area
                    if mute_button_rect and mute_button_rect.collidepoint(event.pos) and event.button == 1:
                        if music_player is not None:
                            music_player.toggle_mute()
                            mute_status = "muted" if music_player.get_is_muted() else "unmuted"
                            state.is_muted=music_player.get_is_muted()
                            gui.gui_text_utils.add_message_to_history(f"Music toggled {mute_status}.", 'system')

                            continue

                    # Handle Mouse Wheel Scrolling for Chat History
                    # Ensure mouse is over the history display area, not just the larger history_rect
                    
                    # --- Panel Toggle Button Click Check ---
                    all_button_rects = gui.gui_core.get_button_rects()
                    panel_toggle_rect = all_button_rects.get('panel_toggle')

                    if panel_toggle_rect and panel_toggle_rect.collidepoint(event.pos) and event.button == 1:
                        state.panel_visible = not state.panel_visible
                        if state.panel_visible:
                            state.panel_width = config.DEFAULT_PANEL_WIDTH
                        # If panel is hidden, its width is effectively 0 for layout purposes,
                        # but we don't change state.panel_width to 0 here.
                        # update_gui_rects will use state.panel_width if visible, or handle appropriately if hidden.
                        # The actual drawing of the panel is skipped in gui.py if state.panel_visible is False.
                        # The pet's centering logic in gui.py already uses `state.panel_width if state.panel_visible else 0`.
                        gui.gui_core.update_gui_rects(state.panel_width)
                        continue # Consume event, no further MOUSEBUTTONDOWN processing for this click

                    if history_display_area.collidepoint(event.pos): # Use history_display_area for scroll detection
                        if event.button == 4: # Scroll up
                            state.scroll_y -= config.SCROLL_SPEED
                        elif event.button == 5: # Scroll down
                            state.scroll_y += config.SCROLL_SPEED
                        # Clamp chat scroll
                        current_total_height = gui.gui_text_utils.calculate_total_history_height(state.chat_history)
                        # Scroll range goes from 0 (top) to max_scroll (bottom)
                        max_scroll = max(0, current_total_height - history_display_area.height)
                        state.scroll_y = max(0, min(state.scroll_y, max_scroll))
                        #print(f"Chat scroll adjusted. Current: {state.scroll_y}, Max: {max_scroll}")
                        continue # Consume event

                    if state.hovered_package_identifier and not state.inventory_panel_visible:
                        scroll_info = gui.gui_care_package.get_package_scroll_info()
                        if event.button == 4:  # Scroll up
                            state.package_scroll_y = max(0, state.package_scroll_y - scroll_info['line_height'])
                        elif event.button == 5:  # Scroll down
                            state.package_scroll_y = min(scroll_info['max_scroll'], state.package_scroll_y + scroll_info['line_height'])
                        #print(state.package_scroll_y)


                    # --- NEW: Handle clicks on Care Package Buttons and Scroll Controls ---
                    # Check if input is locked (sleep state). If so, ignore clicks on these buttons.
                    if not is_input_locked_by_state and not state.inventory_panel_visible and event.button == 1 :
                        package_click_regions = gui.gui_care_package.get_package_button_click_regions()
                        clicked_package_button = False # Flag to consume event

                        for identifier, rect in package_click_regions:
                            if rect.collidepoint(event.pos):
                                #print(f"Clicked on Care Package button region: {identifier}") # Debug click detection
                                if identifier == "scroll_left":
                                    # Check if we can scroll left
                                    if state.package_button_visible_start_index > 0:
                                        state.package_button_visible_start_index -= 1
                                        #state.last_activity_time = current_time_ms # Scrolling counts as activity (it shouldt...)
                                        #print(f"Scrolled package buttons left. New start index: {state.package_button_visible_start_index}")
                                    #else:
                                        #print("Scroll left clicked but already at the beginning.")
                                    clicked_package_button = True # Event consumed by scroll click
                                    break # Stop checking regions

                                elif identifier == "scroll_right":
                                    # Check if we can scroll right
                                    total_packages = len(config.CARE_PACKAGES)
                                    buttons_per_page = gui.gui_core._buttons_per_page # Access the calculated value from gui
                                    if state.package_button_visible_start_index + buttons_per_page < total_packages:
                                        state.package_button_visible_start_index += 1
                                        #state.last_activity_time = current_time_ms # Scrolling counts as activity (it doesnt)
                                        #print(f"Scrolled package buttons right. New start index: {state.package_button_visible_start_index}")
                                    #else:
                                        #print("Scroll right clicked but already at the end.")
                                    clicked_package_button = True # Event consumed by scroll click
                                    break # Stop checking regions

                                elif identifier.startswith("package_"):
                                    # Extract package index from the identifier string "package_N"
                                    try:
                                        package_index = int(identifier.split('_')[1])
                                        if 0 <= package_index < len(config.CARE_PACKAGES):
                                            package_info = config.CARE_PACKAGES[package_index]
                                            #print(f"Clicked on package button {package_index}. Calling add_items.")
                                            # Call the add_items function with the package data
                                            # The add_items function has its own lock check,
                                            # but we already checked is_currently_asleep above.
                                            current_room_id=chatbot.state_manager.get_current_room_id()
                                            #print(f"Debug calling add items with {package_info["package"]}")
                                            add_items(package_info["package"], current_room_id )
                                            
                                            room_name=chatbot.state_manager.get_room_name(current_room_id)
                                            message=f"Items placed in: {room_name}"
                                            color=(0,255,120)
                                            gui.gui_popups.show_popup_message(message)
                                            # new
                                            list_items=[]
                                            for i in package_info["package"]:
                                                item_name = i["name"]
                                                list_items.append(item_name)
                                            delimiter = ", "
                                            str_list = delimiter.join(list_items)
                                            gui.gui_text_utils.add_message_to_history(f"{message}. Items: {str_list}", 'system')

                                        else:
                                            print(f"Error: Clicked package button with invalid index: {package_index}")
                                    except (ValueError, IndexError):
                                        print(f"Error: Could not parse package index from identifier: {identifier}")

                                    clicked_package_button = True # Event consumed by package button click
                                    break # Stop checking regions

                        if clicked_package_button:
                            continue # Consume the mouse event if it was handled by a package/scroll button

                    # If the click wasn't handled by buttons or scrolling, it's ignored or could activate input
                    pass # Continue to next event processing if not handled


        # Handle Keyboard events (typing, Ctrl+keys, Escape)
        if event.type == pygame.KEYDOWN:
                #clean_hover()
#                state.last_activity_time = current_time_ms # Activity resets idle timer

                if event.key == pygame.K_ESCAPE:
                    # If inventory is open, close it. If closed, exit.
                    if state.inventory_panel_visible:
                        print("Escape pressed. Closing inventory panel.")
                        state.inventory_panel_visible = False
                    else:
                        running = False # Exit the game
                    continue

                # Check if input is locked due to sleep state (Applies only when panel is NOT visible)
                if is_input_locked_by_state:
                    # Allow Escape key to exit/close panel even when locked
                    if event.key == pygame.K_ESCAPE:
                         pass # Already handled above
                    else:
                         print("Input locked by state. Ignoring key press.")
                         continue # Skip rest of KEYDOWN handling if locked and not Escape


                            ## Testing 
                # if event.key == pygame.K_1 and pygame.key.get_mods() & pygame.KMOD_CTRL: value="error"; gui.gui_text_utils.add_message_to_history(f"testing {value}!!!", value); continue
                # if event.key == pygame.K_2 and pygame.key.get_mods() & pygame.KMOD_CTRL: value="system";gui.gui_text_utils.add_message_to_history(f"testing {value}!!!", value); continue
                # if event.key == pygame.K_3 and pygame.key.get_mods() & pygame.KMOD_CTRL: value="bot";gui.gui_text_utils.add_message_to_history(f"testing {value}!!!", value); continue
                # if event.key == pygame.K_4 and pygame.key.get_mods() & pygame.KMOD_CTRL: value="user";gui.gui_text_utils.add_message_to_history(f"testing {value}!!!", value); continue
                # if event.key == pygame.K_5 and pygame.key.get_mods() & pygame.KMOD_CTRL: value="system_instruction";gui.gui_text_utils.add_message_to_history(f"testing {value}!!!", value); continue


                # if event.key == pygame.K_2 and pygame.key.get_mods() & pygame.KMOD_CTRL: animation.start_excited_animation(); continue
                # if event.key == pygame.K_3 and pygame.key.get_mods() & pygame.KMOD_CTRL: animation.start_thinking_animation(); continue
                # if event.key == pygame.K_4 and pygame.key.get_mods() & pygame.KMOD_CTRL: animation.start_curious_animation(); continue
                # if event.key == pygame.K_5 and pygame.key.get_mods() & pygame.KMOD_CTRL: animation.start_confused_animation(); continue
                # if event.key == pygame.K_8 and pygame.key.get_mods() & pygame.KMOD_CTRL: animation.start_happy_animation(); continue
                # if event.key == pygame.K_9 and pygame.key.get_mods() & pygame.KMOD_CTRL: animation.start_sad_animation(); continue

                # if event.key == pygame.K_7 and pygame.key.get_mods() & pygame.KMOD_CTRL: chatbot.state_manager.add_steps(20); continue

                # if event.key == pygame.K_5 and pygame.key.get_mods() & pygame.KMOD_CTRL: animation.start_; continue


                # We might want a more user friendly way to call this, while using it as a dev command I realize how nice is it to be able to call the autonomous action whenever one wants.
                if event.key == pygame.K_5 and pygame.key.get_mods() & pygame.KMOD_CTRL:start_chatbot_request("Automated internal message: The following should be an autonomous action.", "user"); continue




                # if event.key == pygame.K_1 and pygame.key.get_mods() & pygame.KMOD_CTRL: gui.gui_popups.show_image_popup("style/images/stat_icons/fullness_empty.png", 3000, 900, 900, popup_type=0); continue
                # if event.key == pygame.K_2 and pygame.key.get_mods() & pygame.KMOD_CTRL: gui.gui_popups.show_image_popup("style/images/stat_icons/fullness_empty.png", 3000, 900, 900, popup_type=1); continue
                # if event.key == pygame.K_3 and pygame.key.get_mods() & pygame.KMOD_CTRL: gui.gui_popups.show_image_popup("style/images/stat_icons/fullness_empty.png", 3000, 900, 900, popup_type=2); continue
                # if event.key == pygame.K_4 and pygame.key.get_mods() & pygame.KMOD_CTRL: gui.gui_popups.show_popup_message("testing!!!!!!") ; continue
                # if event.key == pygame.K_5 and pygame.key.get_mods() & pygame.KMOD_CTRL: music_player.play_new_song(f"style/sounds/music/rooms/garden.mp3"); continue

                # if event.key == pygame.K_6 and pygame.key.get_mods() & pygame.KMOD_CTRL:
                #     music_player.play_new_song(f"style/sounds/music/rooms/living_room.mp3")
                #     continue


                # Handle regular text input (only if cursor is active)
                if state.cursor_active and not state.chatbot_is_processing:
                    state.last_activity_time = current_time_ms # User typing resets idle timer

                    if event.key == pygame.K_BACKSPACE: state.input_text = state.input_text[:-1]; state.cursor_timer = 0; state.cursor_visible = True; continue
                    elif event.key == pygame.K_RETURN:
                        user_message = state.input_text.strip()
                        if user_message:
                            gui.gui_text_utils.add_message_to_history(f"{user_message}", 'user')
                            state.input_text = ""
                            state.cursor_timer = 0
                            state.cursor_visible = True
                            # This call includes its own lock check
                            start_chatbot_request(user_message, 'user')
                        else: # Empty message
                            state.input_text = ""
                            state.cursor_timer = 0
                            state.cursor_visible = True
                        continue
                    else: # Other key press
                        if event.unicode and event.unicode.isprintable():
                            state.input_text += event.unicode
                            state.cursor_timer = 0
                            state.cursor_visible = True
                            continue

                else: # If cursor is inactive, text input is ignored here
                    if event.key == pygame.K_i:
                        clean_hover() # Reset hover state if we enter a menu or other window 
                        if state.inventory_panel_visible:
                            state.inventory_panel_visible = False
                        else:
                            state.inventory_panel_visible = True
                        continue
                    if event.key == pygame.K_c:
                        # clean_hover() no need to clear hover state here
                        if state.panel_visible:
                            state.panel_visible = False
                        else:
                            state.panel_visible = True
                        continue
                #     pass
                    if event.key == pygame.K_m: # Use 'm' for mute
                        # clean_hover() no need to clear hover state here
                        if music_player is not None:
                            music_player.toggle_mute()
                            # Optional: Add a system message or popup to confirm state
                            mute_status = "muted" if music_player.get_is_muted() else "unmuted"
                            state.is_muted=music_player.get_is_muted()
                            gui.gui_text_utils.add_message_to_history(f"Music toggled {mute_status}.", 'system')
                        else:
                            print("Jukebox not initialized, cannot toggle mute.")
                            gui.gui_text_utils.add_message_to_history("Cannot toggle music: Jukebox not ready.", 'system')
                        continue # Consume M key event


        # If event wasn't handled by specific checks above, continue to next event
        pass # Or continue

    # --- Autonomous Action / Idle Logic ---
    # Check if enough time has passed, bot is not currently locked (sleeping)
    # it can act even if the inventory is open
    elapsed_time_ms = current_time_ms - state.last_activity_time

    # --- 3. Update the is_currently_asleep check to use absolute time comparison ---
    # Before the drawing section, update the is_currently_asleep calculation:
    is_currently_asleep = current_time_ms < state.autonomous_action_paused_until_ms
    is_input_locked_by_state = is_currently_asleep or state.chatbot_is_processing


    # In the autonomous action trigger section:
    # Check if idle timeout is reached, bot is not asleep/paused, and bot is not currently processing
    if chatbot_available and chatbot and \
       elapsed_time_ms >= config.IDLE_TIMEOUT_MS and \
       current_time_ms >= state.autonomous_action_paused_until_ms and \
       not state.chatbot_is_processing:

        print(f"Idle timeout ({config.IDLE_TIMEOUT_MINUTES} mins) reached, sleep ended, and no processing in progress. Triggering autonomous action.")
        gui.gui_text_utils.add_message_to_history("Triggering autonomous action due to inactivity.", 'system')

        # Start the autonomous action request. This sets state.chatbot_is_processing = True
        # The response event CHATBOT_RESPONSE_EVENT will set it back to False later.
        if start_chatbot_request("Automated internal message: The following should be an autonomous action.", "user"):
            # last_activity_time is NOT reset here immediately, it's reset when the bot *responds*
            # This prevents spamming requests if the bot is slow to respond.
            pass # Do nothing here, last_activity_time is reset on CHATBOT_RESPONSE_EVENT



    # NEW: Garden Tick Logic
    if current_time_ms >= state.next_garden_tick_time:
        #print(f"Attempting garden tick. (Scheduled at {state.next_garden_tick_time}, current: {current_time_ms})")
        if start_garden_tick_request(): # This will now return False if chatbot is busy
            # If the tick was successfully launched, schedule the next one.
            state.next_garden_tick_time = current_time_ms + config.GARDEN_TICK_INTERVAL_MS
            #print(f"Garden tick launched. Next scheduled for {state.next_garden_tick_time} ms.")
        else:
            # If the tick was deferred (because chatbot was busy),
            # `state.next_garden_tick_time` is NOT updated.
            # This means on the very next frame, if the chatbot is free,
            # it will immediately try to run this "due" tick again.
            pass # Keep state.next_garden_tick_time as is, for re-attempt

    # --- Drawing ---
    # Inside the game loop, before drawing:

    # --- 2. Improve the is_currently_asleep check to use absolute time comparison ---
    # Before the drawing section, update the is_currently_asleep calculation:
    is_currently_asleep = current_time_ms < state.autonomous_action_paused_until_ms
    is_input_locked_by_state = is_currently_asleep or state.chatbot_is_processing


    # --- Drawing ---
    # MODIFIED: Pass the combined lock state

    gui.draw_gui(screen, current_time_ms, is_input_locked_by_state)

    # --- Check for the end of the initial popup phase and initialize jukebox ---
    # This needs to happen *after* update_popups in gui.update_popups
    # which is where _image_popup_visible state is managed.
    # The initial popup phase is true, and no image popups are currently visible.
    if state.is_initial_popup_phase and not gui.gui_popups.is_any_image_popup_currently_active():
        print("Initial popup phase detected as ending.") # Debug
        state.is_initial_popup_phase = False # This is the transition point

        # --- Jukebox Initialization Logic ---
        # Check if the music_player has NOT been initialized yet (it starts as None)
        if music_player is None:
            # Also double-check if mixer is initialized before trying to create jukebox
            if pygame.mixer.get_init():
                print("Initial popup phase has ended. Jukebox is None. Attempting to initialize jukebox.") # Debug
                try:
                    current_room = chatbot.state_manager.room_manager._find_room_by_id(chatbot.state_manager.get_current_room_id())
                    loc_music = current_room.get("music")
                    music_player = jukebox(f"style/sounds/music/rooms/{loc_music}.mp3") # Initialize ONLY ONCE
                except Exception as e:
                    print(f"Error initializing jukebox: {e}")
                    music_player = None # Ensure it stays None if initialization fails unexpectedly
            else:
                 print("Pygame Mixer not initialized. Cannot initialize Jukebox.")


    # --- Update Display ---
    pygame.display.flip()


# --- Quit Pygame ---
# Ensure chatbot shutdown is called on exit
if chatbot and hasattr(chatbot, 'shutdown') and callable(chatbot.shutdown):
    print("Attempting to shut down chatbot...")
    try:
        chatbot.shutdown()
        print("Chatbot shutdown complete.")
    except Exception as e:
        print(f"Error during chatbot shutdown: {e}")

# Clean up mixer before quitting pygame
if pygame.mixer.get_init():
    print("Quitting Pygame Mixer.")
    pygame.mixer.quit()

pygame.quit()
sys.exit()