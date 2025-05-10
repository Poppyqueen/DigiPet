# state.py (Additions and Modifications)

# --- Game State Variables ---

# Chat/Input State
input_text = ""
chat_history = [] # Stores tuples: (text, type)
scroll_y = 0 # Pixels scrolled from the bottom of chat history. 0 means scrolled to the very bottom.

# Cursor State (tied to input)
cursor_visible = True
cursor_timer = 0

# Animation State
is_shaking = False # General shake state
shake_start_time = 0 # Time in milliseconds when the general shake started

sad_state = 0 # 0: Idle, 1: Dropping, 2: Shaking Down, 3: Rising (Sad animation state)
sad_phase_start_time = 0 # Time when the current sad phase began
happy_state = 0 # 0: Idle, 1: Dipping, 2: Shaking Happy, 3: Bouncing Up
happy_phase_start_time = 0 # ms timestamp

# Background State
background_image = None # Variable to hold the currently loaded background image surface

# Timer/Activity State
last_activity_time = 0 # Initialize timer at start - will be set after pygame.init()
autonomous_action_paused_until_ms = 0 # Time in milliseconds until the autonomous action/input lock is paused.

# Chatbot Instance (Conceptual reference)
# chatbot = None # Not defining the instance here


# --- Pet Wellness Stats ---
# Dictionary to hold the current wellness levels (0-100)
pet_stats = {
    "fullness": 200.0,
    "hydration": 200.0,
    "energy": 200.0
}


# --- Pop-up Messages State ---
active_popups = [] # List to hold active PopupMessage objects


# --- NEW: Inventory State (for the Modal Panel) ---
room_inventory_list = [] # List of strings: ["Item Name", "Item B x2", ...]
player_inventory_list = [] # List of strings: ["Item C x5", ...]

inventory_panel_visible = False # Single flag: True if the modal inventory panel is open

room_inventory_scroll_y = 0 # Scroll position for the room list (0 is top)
player_inventory_scroll_y = 0 # Scroll position for the player list (0 is top)



# --- NEW: Care Package Button State ---
# Index of the first package button shown in the current page (0-based index of CARE_PACKAGES list)
package_button_visible_start_index = 0


# NEW, IS PROCESSING?

chatbot_is_processing=False

is_initial_popup_phase = True