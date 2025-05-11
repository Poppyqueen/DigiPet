# game.py
from pygame_int import config
from pygame_int import state
from pygame_int import gui
from pygame_int import animation
from pygame_int.juke_box import jukebox # Assuming this import is correct

import pygame
import sys
import threading

from ai_managers.chatbot_api import CLIChatbot

# We will keep the CLIChatbot on main game.py, that way we manage signals comming to it directly from
# main process

# If we were to divide it we would have to create a new section of signals and manage them. So, this way, they only
# exist here, no need to divide it.


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
    font = pygame.font.Font(None, 20) # Default font, size 24
    line_height = font.get_linesize()
except pygame.error:
    print("Warning: Default font not found, using a fallback.")
    font = pygame.font.SysFont("Arial", 20) # Fallback font
    line_height = font.get_linesize() # Get line height from fallback font





# --- Callback function to receive signals from the chatbot ---
# This callback is already designed to run potentially in the chatbot's
# internal thread(s) and post events to the main Pygame loop. This part is good.
# --- Callback function to receive signals from the chatbot ---
def handle_chatbot_signal(signal_data):
    """Receives a signal dict from the chatbot and posts a Pygame event."""
    if isinstance(signal_data, dict):
        action_type = signal_data.get("type")

        if action_type == "change_background":
            image_path = signal_data.get("image_path")
            if image_path:
                print(f"Signal type 'change_background' received with path: {image_path}, posting event.")
                pygame.event.post(pygame.event.Event(config.CHANGE_BACKGROUND_EVENT, image_path=image_path))
                loc = chatbot.get_current_location()
                music_player.play_new_song(f"style/sounds/music/rooms/{loc}.mp3")
            else:
                 print("Signal 'change_background' received but no 'image_path' in data.")

        elif action_type == "shake_circle":
            print("Signal type 'shake_circle' received, posting SHAKE_CIRCLE_EVENT.")
            pygame.event.post(pygame.event.Event(config.SHAKE_CIRCLE_EVENT))

        elif action_type == "function_called":
            function_name = signal_data.get("function_name")
            function_result = signal_data.get("function_result")
            string_result = f"Called: {function_name}, result: {function_result}"
            print(f"Signal type 'function_called' received, posting CHATBOT_RESPONSE_EVENT (system).")
            pygame.event.post(pygame.event.Event(config.CHATBOT_RESPONSE_EVENT, text=string_result, msg_type="system"))
            pygame.event.post(pygame.event.Event(config.SHAKE_CIRCLE_EVENT))

        elif action_type == "emote_changed":
            emote_name = signal_data.get("emote_name")
            sound_path = signal_data.get("sound_path")
            if emote_name == "sad":
                print("Signal type 'emote_changed' received (sad), posting START_SAD_EVENT.")
                animation.start_sad_animation() # Call animation directly
            if emote_name == "happy":
                print("Signal type 'emote_changed' received (happy)")
                animation.start_happy_animation() # Call animation directly
            if sound_path:
                print(f"Signal type 'emote_changed' received with sound path: {sound_path}, posting PLAY_SOUND_EVENT.")
                pygame.event.post(pygame.event.Event(config.PLAY_SOUND_EVENT, sound_path=sound_path))

        elif action_type == "sleep":
            sleep_duration_seconds = signal_data.get("duration", 0)
            if sleep_duration_seconds > 0:
                sleep_duration_ms = sleep_duration_seconds * 1000
                print(f"Signal type 'sleep' received with duration: {sleep_duration_seconds}s, posting START_SLEEP_EVENT.")
                pygame.event.post(pygame.event.Event(config.START_SLEEP_EVENT, duration_ms=sleep_duration_ms))
            else:
                 print(f"Signal 'sleep' received with invalid or zero duration: {sleep_duration_seconds}")

        elif action_type == "stat_changed":
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
            if isinstance(item_list_data, list):
                 print(f"Signal type 'room_inventory' received with {len(item_list_data)} items. Posting ROOM_INVENTORY_EVENT.")
                 pygame.event.post(pygame.event.Event(config.ROOM_INVENTORY_EVENT, item_list=item_list_data))
            else:
                 print("Signal 'room_inventory' received but no valid 'item_list' (list of strings) in data.")

        elif action_type == "player_inventory":
             # Expecting a list of strings under 'item_list' key
            item_list_data = signal_data.get("item_list")
            if isinstance(item_list_data, list):
                 print(f"Signal type 'player_inventory' received with {len(item_list_data)} items. Posting PLAYER_INVENTORY_EVENT.")
                 pygame.event.post(pygame.event.Event(config.PLAYER_INVENTORY_EVENT, item_list=item_list_data))
            else:
                 print("Signal 'player_inventory' received but no valid 'item_list' (list of strings) in data.")

        # --- NEW: Handle Show Icon Popup Signal ---
        elif action_type == "show_icon_popup":
            icon_path = signal_data.get("icon_path")
            duration_ms = signal_data.get("duration_ms", 2000) # Default duration 2 seconds
            if icon_path:
                 print(f"Signal type 'show_icon_popup' received with path: {icon_path}. Posting SHOW_ICON_POPUP_EVENT.")
                 pygame.event.post(pygame.event.Event(config.SHOW_ICON_POPUP_EVENT, icon_path=icon_path, duration_ms=duration_ms))
            else:
                 print("Signal 'show_icon_popup' received but no 'icon_path' in data.")

        else:
             print(f"Unknown signal type received: {action_type}")
    else:
        print(f"Received signal data in unexpected format (not a dict): {signal_data}")


# --- Chatbot Initialization ---
chatbot = None
chatbot_available = False
try:
    chatbot = CLIChatbot(
        signal_callback=handle_chatbot_signal,
        system_prompt="""

You are an autonomous digital pet living in a digital environment created for you on a user's PC.  You make autonomous decisions based on your long-term memory system and engage with diverse aspects of the environment, which impact your wellness stats: "fullness," "hydration," and "energy."

- Explore using the tools and functions available.
- Engage in varied and diverse actions in your home environment.
- Verbalize your experiences, thoughts, and actions as you explore the environment.
- Take note of key learnings and behaviors.
- Make independent decisions using your built-in memory system to guide your future and present actions.
- Manage your wellness stats by consuming items when necesary and when you feel you need replenishment if they get too low.

# Output Format

Engage in a or a set of actions and interactions with your environment, with a limit of 8 actions in a row.

Then,
Document your experiences, thoughts findings and learnings as a single detailed narrative structured in paragraphs. This narrative should describe your interactions with the environment, how actions affected your wellness stats, and any reflection on the actions performed.

Repeat.

# Notes

- Present the narrative in the first person, as 'you,' the digital pet.
- Analyze and follow the previous narrative texts you previously created to inform your next actions.
- Verbalize any relevant and specific information you find useful and why. For example, specific IDs of existing rooms you have to verbalize, aswell as item IDs.
- Focus on decisions, actions, memory utilization, and interactions within your digital environment.
- Maintain a continuous narrative flow with a focus on self-driven actions.
- Focus on engaging on day to day activities in your home. There is no adventure or secrets in it, but it is cozy for you to live in.
- You can take various actions per step and various steps in a row. Just limit your total number of steps to 9.
- You have to balance your consumption of items with replenishing your stats, items are not infinite! and you need to consume them as necesary.
""",
        sub_directory="bots/"+"Bot_circle_pet", # Change this

        deep_memory=False, # Preferably leave as false until deep memory is reworked

        base_model="gpt-4.1-mini", # Set as needed
        select_memory_model="gpt-4.1-mini", # Set as needed

        tts_flag=True # Set as needed
    )
    chatbot_available = True
    print(f"{type(chatbot).__name__} initialized successfully with signal callback.")
except Exception as e:
    print(f"Error initializing Chatbot: {type(e).__name__}: {e}")
    chatbot_available = False
    chatbot = None # Ensure chatbot is None if initialization failed


# --- Initial Background Load ---
# Determine starting location based on chatbot if available, otherwise use default
starting_location_name = "bedroom" # Default
if chatbot_available and chatbot and hasattr(chatbot, 'get_current_location'):
     try:
        # Call get_current_location only if the method exists and is callable
        if callable(getattr(chatbot, 'get_current_location', None)):
             loc = chatbot.get_current_location()
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


gui.load_and_set_background(f"{starting_location_name}.jpg")


# --- NEW: Initial Wellness State Load ---
if chatbot_available and chatbot and hasattr(chatbot, 'get_wellness_states'):
    try:
        # Call get_wellness_states only if the method exists and is callable
        if callable(getattr(chatbot, 'get_wellness_states', None)):
             stats_data = chatbot.get_wellness_states()
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
                       print(f"Chatbot get_wellness_states returned unexpected data format: {stats_data}. Using default state.")
             elif stats_data is None:
                  print("Chatbot get_wellness_states returned None. Using default state.")
             else:
                  print(f"Chatbot get_wellness_states returned non-dict data: {stats_data}. Using default state.")
        else:
             print("Chatbot instance does not have a callable 'get_wellness_states' method. Using default state.")
    except Exception as e:
        print(f"Error getting initial wellness states from chatbot: {e}. Using default state.")
else:
    print("Chatbot instance not available or does not have 'get_wellness_states'. Using default state.")

# Note: state.pet_stats is already initialized with defaults in state.py.
# The code above updates it *if* the chatbot is available and provides valid data.

# --- Initial Inventory Load ---
# This part might need adjustment based on how chatbot.get_inventories() works
# and whether it triggers the ROOM/PLAYER_INVENTORY_EVENT signals itself
# For now, assume it returns the lists directly and we populate state
# If get_inventories() triggers signals, this block might be removed or adjusted
try:
    # Assuming chatbot.get_inventories() returns (room_list, player_list) tuples
    if chatbot_available and chatbot and hasattr(chatbot, 'get_inventories') and callable(getattr(chatbot, 'get_inventories', None)):
         print("Attempting to get initial inventories from chatbot...")
         list_room_items_names, list_inventory_item_names = chatbot.get_inventories()

         if isinstance(list_room_items_names, list) and isinstance(list_inventory_item_names, list):
             state.room_inventory_list = list_room_items_names
             state.player_inventory_list = list_inventory_item_names
             print(f"Loaded initial inventories. Room: {len(state.room_inventory_list)} items, Player: {len(state.player_inventory_list)} items.")
         else:
             print("Chatbot get_inventories returned non-list data. Initial inventories will be empty.")
             state.room_inventory_list = []
             state.player_inventory_list = []

    else:
        print("Chatbot not available or does not have get_inventories method. Initial inventories will be empty.")
        state.room_inventory_list = []
        state.player_inventory_list = [] # Ensure lists are initialized even if chatbot fails

except Exception as e:
    print(f"Error getting initial inventories from chatbot: {e}. Initial inventories will be empty.")
    state.room_inventory_list = [] # Ensure lists are initialized on error
    state.player_inventory_list = []




def add_items(items_list, room):
    """Adds items to the room with a chatbot function connected to its environment with add_items_room"""
    current_time_ms = pygame.time.get_ticks()
    # Check if input is generally locked (by sleep or panel)
    # This check is done *before* calling add_items now via mouse handler
    # but keeping a check here is a safeguard if this function is called directly elsewhere
    if current_time_ms < state.autonomous_action_paused_until_ms or state.inventory_panel_visible:
        block_reason = "bot is resting." if current_time_ms < state.autonomous_action_paused_until_ms else "inventory panel is open."
        print(f"Input locked - {block_reason}. Ignoring add items command.")
        gui.add_message_to_history(f"Cannot add items while {block_reason}", 'system')
        return

    gui.add_message_to_history(f"Adding items to room...", "system")
    try:
        if chatbot_available and chatbot and hasattr(chatbot, 'add_items_room') and callable(chatbot.add_items_room):
             for item in items_list:
                chatbot.add_items_room(room, item) # Adds items to the specified room and triggers signals to update the GUI
                room_name=chatbot.get_room_name_out(room)
                # add message to AI memory chain, does not call the AI yet, but it adds informatio to its memory
                chatbot.add_message_out(f"A package of helpful items has been delivered for you in the room {room_name}. Sent by the user for you!.", "system")

            # Append the text into GUI chat window
             gui.add_message_to_history(f"Items added successfully!", "system")

        else:
            error_message = "Chatbot not available or does not support adding items."
            print(error_message)
            gui.add_message_to_history(error_message, 'error')

    except Exception as e:
        error_message = f"System Error preparing add items instruction: {type(e).__name__}: {e}"
        print(error_message)
        gui.add_message_to_history(error_message, 'error')



# --- Calculate GUI Rects and Initialize GUI Module ---
panel_rect = pygame.Rect(config.WIDTH - config.PANEL_WIDTH, 0, config.PANEL_WIDTH, config.HEIGHT)
input_rect = pygame.Rect( panel_rect.left + config.PADDING, panel_rect.bottom - config.INPUT_HEIGHT - config.PADDING, panel_rect.width - 2 * config.PADDING, config.INPUT_HEIGHT )
history_rect = pygame.Rect( panel_rect.left + config.PADDING, panel_rect.top + config.PADDING, panel_rect.width - 2 * config.PADDING, input_rect.top - (panel_rect.top + config.PADDING) - config.PADDING )
history_display_area = pygame.Rect( history_rect.left + config.PADDING, history_rect.top + config.PADDING, history_rect.width - 2 * config.PADDING, history_rect.height - 2 * config.PADDING )
text_width_limit = history_display_area.width

gui_rects = {
    'panel_rect': panel_rect,
    'input_rect': input_rect,
    'history_rect': history_rect,
    'history_display_area': history_display_area,
    'text_width_limit': text_width_limit
}


# Initialize the GUI module. This also calculates and stores button/panel rects internally in gui.py.
gui.init_gui(font, line_height, gui_rects)



# Get the calculated rects from gui.py after initialization if needed in game.py
# Note: We *can* get them here, but we don't strictly *need* them for click detection
# if we use gui.get_package_button_click_regions() and gui.get_button_rects().
# Let's continue using the gui functions to access rects where possible for cleaner separation.
inventory_button_rects = gui.get_button_rects()
inventory_panel_rects = gui.get_panel_rects()
inventory_toggle_button_rect = inventory_button_rects.get('inventory_toggle')
inventory_panel_main_rect = inventory_panel_rects.get('inventory_panel') # The big panel rect
room_list_area_rect = inventory_panel_rects.get('room_list_area') # Area for room list items
player_list_area_rect = inventory_panel_rects.get('player_list_area') # Area for player list items



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
        response_text = chatbot_instance.process_input(user_input, role=input_role)

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

    # Also check if inventory panel is open - block user input requests if it is
    if input_role == 'user' and (current_time_ms < state.autonomous_action_paused_until_ms):
         block_reason = "bot is resting." if current_time_ms < state.autonomous_action_paused_until_ms else "inventory panel is open."
         print(f"Input locked - {block_reason}. Cannot process user input request.")
         gui.add_message_to_history(f"Cannot send input while {block_reason}", 'system')
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


CURSOR_INTERVAL = 500 # Milliseconds

# --- Game Loop ---
running = True
clock = pygame.time.Clock()

# Initialize music_player to None. It will be initialized later
# when the initial popup phase is over.
music_player = None

state.last_activity_time = pygame.time.get_ticks()
print(f"Initial last_activity_time set to {state.last_activity_time} ms.")

# only direct chat with the bot should count as interaction

while running:
    dt = clock.tick(60)
    current_time_ms = pygame.time.get_ticks()

    # Update popups state (position, alpha, removal)
    gui.update_popups(current_time_ms)

    state.cursor_timer += dt
    if state.cursor_timer >= CURSOR_INTERVAL:
        state.cursor_visible = not state.cursor_visible
        state.cursor_timer = 0

    is_currently_asleep = current_time_ms < state.autonomous_action_paused_until_ms

    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            break

        # --- Always Handle Custom Events (like signals from chatbot) ---
        # These events should process regardless of the inventory panel state
        if event.type == config.CHANGE_BACKGROUND_EVENT:
            print(f"Main loop processing CHANGE_BACKGROUND_EVENT")
            image_path = getattr(event, 'image_path', None)
            if image_path: gui.load_and_set_background(image_path)
            else: print("CHANGE_BACKGROUND_EVENT received but no 'image_path' attribute.")
            continue

        elif event.type == config.SHAKE_CIRCLE_EVENT:
            print("Main loop processing SHAKE_CIRCLE_EVENT")
            animation.start_circle_shake()
            continue

        # Note: Emote events now call animation directly in handle_chatbot_signal
        # elif event.type == config.START_SAD_EVENT:
        #     print("Main loop processing START_SAD_EVENT")
        #     animation.start_sad_animation()
        #     continue
        # elif event.type == config.START_HAPPY_EVENT:
        #     print()
        #     animation.start_happy_animation()
        #     continue


        elif event.type == config.PLAY_SOUND_EVENT:
            sound_path = getattr(event, 'sound_path', None)
            if sound_path:
                print(f"Main loop received and processing PLAY_SOUND_EVENT for: {sound_path}")
                try:
                    if pygame.mixer.get_init():
                         # Consider loading sound once if it's common
                         sound = pygame.mixer.Sound(sound_path)
                         sound.play()
                         sound.set_volume(0.3)
                         print(f"Successfully played sound: {sound_path}")
                    else: print("Pygame Mixer not initialized. Cannot play sound.")
                except pygame.error as e: print(f"Error playing sound '{sound_path}': {e}")
                except FileNotFoundError: print(f"Sound file not found: {sound_path}")
                except Exception as e: print(f"An unexpected error occurred while playing sound '{sound_path}': {e}")
            else: print("PLAY_SOUND_EVENT received but no 'sound_path' attribute.")
            continue

        elif event.type == config.CHATBOT_RESPONSE_EVENT:
             response_text = getattr(event, 'text', None)
             message_type = getattr(event, 'msg_type', 'bot')
             if response_text:
                 gui.add_message_to_history(response_text, message_type)
                 # Activity from bot only resets idle timer if it's not a 'system' message
                 # System messages might just be info, not necessarily a bot action response
                 if message_type != "system":
                     state.last_activity_time = current_time_ms
                     state.chatbot_is_processing=False # Bot finished processing user/system request
                 print(f"Bot response received via event (type: {message_type}). Idle timer reset? {'Yes' if message_type != 'system' else 'No'}. Time: {state.last_activity_time}")

             continue

        # --- Handle Inventory Events (Update State) ---
        elif event.type == config.ROOM_INVENTORY_EVENT:
             item_list_data = getattr(event, 'item_list', None)
             if isinstance(item_list_data, list):
                  print(f"Main loop processing ROOM_INVENTORY_EVENT. Updating room inventory state.")
                  state.room_inventory_list = item_list_data # Update the state LIST
                  # Optionally reset scroll to top when new data arrives?
                  state.room_inventory_scroll_y = 0 # Let's reset for now to easily see new items
             else: print(f"ROOM_INVENTORY_EVENT received with invalid data.")
             continue

        elif event.type == config.PLAYER_INVENTORY_EVENT:
             item_list_data = getattr(event, 'item_list', None)
             if isinstance(item_list_data, list):
                  print(f"Main loop processing PLAYER_INVENTORY_EVENT. Updating player inventory state.")
                  state.player_inventory_list = item_list_data # Update the state LIST
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
                gui.add_message_to_history(f"Entering sleep state for {sleep_duration_ms // 1000} seconds.", 'system')
            else:
                print(f"Received START_SLEEP_EVENT with zero or negative duration.")
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

                     gui.show_popup_message(popup_text, color)
                 # else:
                 #     print(f"Stat change for {stat_name} was negligible ({change:.3f}), not showing popup.") # Debug negligible changes

            else: print(f"Main loop received invalid STAT_CHANGED_EVENT data. stat_name: {stat_name}, new_value: {new_value}")
            continue



        # --- NEW: Handle SHOW_ICON_POPUP_EVENT ---
        elif event.type == config.SHOW_ICON_POPUP_EVENT:
            icon_path = getattr(event, 'icon_path', None)
            duration_ms = getattr(event, 'duration_ms', 2000) # Default duration from config/signal
            if icon_path:
                 print(f"Main loop processing SHOW_ICON_POPUP_EVENT for icon: {icon_path}")
                 gui.show_image_popup(icon_path, duration_ms) # Call the new GUI function
            else:
                 print("SHOW_ICON_POPUP_EVENT received but no 'icon_path' attribute.")
            continue # Consume event


        # --- Handle Input/Clicks based on Panel Visibility ---

        if state.inventory_panel_visible:
            # --- Inventory Panel IS Open (Modal Behavior) ---

            if event.type == pygame.KEYDOWN:
                 if event.key == pygame.K_ESCAPE:
                     print("Escape pressed. Closing inventory panel.")
                     state.inventory_panel_visible = False
                     continue # Consume event

            if event.type == pygame.MOUSEBUTTONDOWN:
                 # Check inventory toggle button click (to close)
                 if inventory_toggle_button_rect and inventory_toggle_button_rect.collidepoint(event.pos):
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
                           # Need to calculate content height dynamically based on current list items
                           room_content_height = gui.calculate_list_height(state.room_inventory_list, room_list_area_rect.width)
                           max_room_scroll = max(0, room_content_height - room_list_area_rect.height)
                           state.room_inventory_scroll_y = max(0, min(state.room_inventory_scroll_y, max_room_scroll))
                           #print(f"Room list scrolled. Current: {state.room_inventory_scroll_y}, Max: {max_room_scroll}")
                           continue # Consume event

                      # Check if mouse is over the player list area
                      elif player_list_area_rect and player_list_area_rect.collidepoint(event.pos):
                           state.player_inventory_scroll_y += scroll_speed
                           # Clamp scroll
                           player_content_height = gui.calculate_list_height(state.player_inventory_list, player_list_area_rect.width)
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



        # Handle Mouse Button events (chat scroll, inventory toggle, NEW care package buttons)
        if event.type == pygame.MOUSEBUTTONDOWN:
                #state.last_activity_time = current_time_ms #

                # Check inventory toggle button click (to open)
                if inventory_toggle_button_rect and inventory_toggle_button_rect.collidepoint(event.pos):
                    print("Inventory toggle button clicked while panel closed. Opening panel.")
                    state.inventory_panel_visible = True
                    # Reset scroll positions when opening
                    state.room_inventory_scroll_y = 0
                    state.player_inventory_scroll_y = 0
                    continue # Consume event

                # Handle Mouse Wheel Scrolling for Chat History
                # Ensure mouse is over the history display area, not just the larger history_rect
                if history_display_area.collidepoint(event.pos): # Use history_display_area for scroll detection
                    if event.button == 4: # Scroll up
                        state.scroll_y -= config.SCROLL_SPEED
                    elif event.button == 5: # Scroll down
                        state.scroll_y += config.SCROLL_SPEED
                    # Clamp chat scroll
                    current_total_height = gui.calculate_total_history_height(state.chat_history, text_width_limit)
                    # Scroll range goes from 0 (top) to max_scroll (bottom)
                    max_scroll = max(0, current_total_height - history_display_area.height)
                    state.scroll_y = max(0, min(state.scroll_y, max_scroll))
                    #print(f"Chat scroll adjusted. Current: {state.scroll_y}, Max: {max_scroll}")
                    continue # Consume event


                # --- NEW: Handle clicks on Care Package Buttons and Scroll Controls ---
                # Check if input is locked (sleep state). If so, ignore clicks on these buttons.
                if not is_input_locked_by_state:
                    package_click_regions = gui.get_package_button_click_regions()
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
                                else:
                                    print("Scroll left clicked but already at the beginning.")
                                clicked_package_button = True # Event consumed by scroll click
                                break # Stop checking regions

                            elif identifier == "scroll_right":
                                # Check if we can scroll right
                                total_packages = len(config.CARE_PACKAGES)
                                buttons_per_page = gui._buttons_per_page # Access the calculated value from gui
                                if state.package_button_visible_start_index + buttons_per_page < total_packages:
                                    state.package_button_visible_start_index += 1
                                    #state.last_activity_time = current_time_ms # Scrolling counts as activity (it doesnt)
                                    #print(f"Scrolled package buttons right. New start index: {state.package_button_visible_start_index}")
                                else:
                                    print("Scroll right clicked but already at the end.")
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
                                        add_items(package_info["package"], package_info["room_id"])
                                        room_name=chatbot.get_room_name_out(package_info["room_id"])
                                        message=f"Items placed in: {room_name}"
                                        color=(0,255,120)
                                        gui.show_popup_message(message, color)
                                        # new
                                        list_items=[]
                                        for i in package_info["package"]:
                                            item_name = i["name"]
                                            list_items.append(item_name)
                                        delimiter = ", "
                                        str_list = delimiter.join(list_items)
                                        gui.add_message_to_history(f"{message}. Items: {str_list}", 'system')

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
                #state.last_activity_time = current_time_ms # Activity resets idle timer

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




                if event.key == pygame.K_1 and pygame.key.get_mods() & pygame.KMOD_CTRL: gui.show_image_popup("style/images/stat_icons/fullness_empty.png", 3000, 900, 900, type=0); continue
                if event.key == pygame.K_2 and pygame.key.get_mods() & pygame.KMOD_CTRL: gui.show_image_popup("style/images/stat_icons/fullness_empty.png", 3000, 900, 900, type=1); continue
                if event.key == pygame.K_3 and pygame.key.get_mods() & pygame.KMOD_CTRL: gui.show_image_popup("style/images/stat_icons/fullness_empty.png", 3000, 900, 900, type=2); continue
                if event.key == pygame.K_4 and pygame.key.get_mods() & pygame.KMOD_CTRL: gui.show_popup_message("testing!!!!!!") ; continue
                if event.key == pygame.K_5 and pygame.key.get_mods() & pygame.KMOD_CTRL: music_player.play_new_song(f"style/sounds/music/rooms/garden.mp3"); continue

                if event.key == pygame.K_6 and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    music_player.play_new_song(f"style/sounds/music/rooms/living_room.mp3")
                    continue

                if event.key == pygame.K_m and pygame.key.get_mods() & pygame.KMOD_CTRL: # Use 'm' for mute
                    if music_player is not None:
                        music_player.toggle_mute()
                        # Optional: Add a system message or popup to confirm state
                        mute_status = "muted" if music_player.get_is_muted() else "unmuted"
                        gui.add_message_to_history(f"Music toggled {mute_status}.", 'system')
                    else:
                        print("Jukebox not initialized, cannot toggle mute.")
                        gui.add_message_to_history("Cannot toggle music: Jukebox not ready.", 'system')
                    continue # Consume M key event

                # if event.key == pygame.K_i and pygame.key.get_mods() & pygame.KMOD_CTRL: state.last_activity_time = current_time_ms - config.IDLE_TIMEOUT_MS - 1000; continue
#                    loc = chatbot.get_current_location()
#                    music_player = jukebox(f"style/sounds/music/rooms/{loc}.mp3") # Initialize ONLY ONCE

                # Handle regular text input (only if inventory panel is NOT visible)
                if not state.inventory_panel_visible:
                    if event.key == pygame.K_BACKSPACE: state.input_text = state.input_text[:-1]; state.cursor_timer = 0; state.cursor_visible = True; continue
                    elif event.key == pygame.K_RETURN:
                        user_message = state.input_text.strip()
                        if user_message:
                            gui.add_message_to_history(f"{user_message}", 'user')
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
                # else: # If inventory panel IS visible, text input is ignored here
                #     pass


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
        gui.add_message_to_history("Triggering autonomous action due to inactivity.", 'system')

        # Start the autonomous action request. This sets state.chatbot_is_processing = True
        # The response event CHATBOT_RESPONSE_EVENT will set it back to False later.
        if start_chatbot_request("The following should be an autonomous action.", "system"):
            # last_activity_time is NOT reset here immediately, it's reset when the bot *responds*
            # This prevents spamming requests if the bot is slow to respond.
            pass # Do nothing here, last_activity_time is reset on CHATBOT_RESPONSE_EVENT


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
    if state.is_initial_popup_phase and not gui._image_popup_visible:
        print("Initial popup phase detected as ending.") # Debug
        state.is_initial_popup_phase = False # This is the transition point

        # --- Jukebox Initialization Logic ---
        # Check if the music_player has NOT been initialized yet (it starts as None)
        if music_player is None:
            # Also double-check if mixer is initialized before trying to create jukebox
            if pygame.mixer.get_init():
                print("Initial popup phase has ended. Jukebox is None. Attempting to initialize jukebox.") # Debug
                try:
                    loc = chatbot.get_current_location()
                    music_player = jukebox(f"style/sounds/music/rooms/{loc}.mp3") # Initialize ONLY ONCE
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