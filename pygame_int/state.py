# state.py

# This file contains all global state variables for the game.
# By keeping state in one place, it's easier to manage and understand
# the current status of the application.

# --- Core Game State & Flow ---
# Variables controlling the overall game flow, timing, and activity.

last_activity_time = 0 # Initialize timer at start - will be set after pygame.init()
autonomous_action_paused_until_ms = 0 # Time in milliseconds until the autonomous action/input lock is paused.
chatbot_is_processing = False # Indicates if the chatbot is currently generating a response.
is_initial_popup_phase = True # Flag for displaying initial game information popups.

agent_sleeping = False

# --- Chat and Input State ---
# Variables managing the chat interface, input box, and history.

input_text = "" # Text currently in the input box.
chat_history = [] # Stores tuples: (text, type) for display.
scroll_y = 0 # Pixels scrolled from the bottom of chat history. 0 means scrolled to the very bottom.

# Cursor State (tied to input)
cursor_visible = False # Controls the blinking visibility of the input cursor.
cursor_timer = 0 # Timer for cursor blinking animation.
cursor_active = False

# --- Pet Core Properties ---
# Fundamental attributes of the pet itself.

# Dictionary to hold the current wellness levels (0-100, but can exceed initially)
pet_stats = {
    "fullness": 200.0,
    "hydration": 200.0,
    "energy": 200.0
}

pet_color = (100, 255, 100) # Default RGB tuple for drawing the pet.
game_theme_colors = {} # Dictionary to hold theme colors for the game.
# This value will be updated by game.py based on loaded config or user selection.
pet_sound = "mellow_friend.mp3" # Default sound for the pet.

pet_radius = 0 # The current drawing radius of the pet.
current_radius = 0 # Appears potentially redundant with pet_radius, but kept as provided.


# --- Pet Animation State ---
# Variables controlling various pet animations and their timings.

# General Animation State
is_shaking = False # General shake state (e.g., for incorrect input).
shake_start_time = 0 # Time in milliseconds when the general shake started.

# Sleep Animation State
sleep_state = 0 # 0: Idle, 1: Falling Asleep, 2: Deep Sleep, 3: Waking Up.
sleep_phase_start_time = 0 # Time when the current sleep phase began.
original_radius_before_sleep = None # Stores pet_radius at start.

# New variables for the "Dreaming/Twitch" mechanic
sleep_twitch_active = False       # Is it currently twitching?
sleep_twitch_start_time = 0       # When did the current twitch start?
next_twitch_time = 0              # Timestamp for when the next twitch should happen

# Sad Animation State
sad_state = 0 # 0: Idle, 1: Dropping, 2: Shaking Down, 3: Rising (Sad animation state).
sad_phase_start_time = 0 # Time when the current sad phase began.
original_radius_before_sad = None # Stores pet_radius at the start of the sad animation for size change.
target_sad_radius = None # Target radius for the sad animation size change.

# Happy Animation State
happy_state = 0 # 0: Idle, 1: Dipping, 2: Shaking Happy, 3: Bouncing Up (Happy animation state).
happy_phase_start_time = 0 # ms timestamp when the current happy phase began.
original_radius_before_happy = None # Stores pet_radius at the start of happy animation.
target_happy_radius = None # Target radius for happy animation size change.

# Angry Animation State
angry_state = 0  # 0: Idle, 1: Phase 1 (e.g., tense), 2: Phase 2 (e.g., vibrate), 3: Phase 3 (e.g., settle).
angry_phase_start_time = 0 # Timestamp (ms) when the current angry phase started.
original_radius_before_angry = 0 # Stores pet_radius at the start of angry animation.
max_angry_radius = 0 # Max radius to reach during the angry animation size change.

# Excited Animation State
excited_state = 0 # 0: Idle, 1: Phase 1 (e.g., bounce up), 2: Phase 2 (e.g., jiggle), 3: Phase 3 (e.g., settle).
excited_phase_start_time = 0 # ms timestamp when the current excited phase started.

# Confused Animation State (Multiple related variables exist)
is_confused = False # Boolean, True if the confused animation is active (simpler flag).
confused_start_time = 0 # Timestamp (ms) when the confused animation started (simpler timer).
confused_state = 0  # 0: Idle, 1-8: Phases of X movement (more detailed state).
confused_phase_start_time = 0 # pygame.time.get_ticks() when the current detailed phase started.
confused_corner_index = 0 # 0:TL, 1:TR, 2:BL, 3:BR - tracks the target corner for the current Ctr->Corner phase.
original_radius_before_confused = None # Stores pet_radius at the start of the animation for potential size change.

# Curious Animation State
is_curious = False # Boolean, True if the curious animation is active.
curious_start_time = 0 # Timestamp (ms) when the curious animation started.

# Thinking Animation State
is_thinking = False # Boolean, True if the thinking animation is active.
thinking_start_time = 0 # Timestamp (ms) when the thinking animation started.


# --- UI and Overlay States ---
# Variables controlling visibility and state of UI elements like popups and modals.

panel_width = 0 # Width of the side panel in pixels.
panel_visible = False # Boolean to control the visibility of the side panel.

active_popups = [] # List to hold active PopupMessage objects currently displayed.

# Inventory Modal Panel State
inventory_panel_visible = False # Single flag: True if the modal inventory panel is open.
room_inventory_list = [] # List of strings representing items in the room inventory. E.g., ["Item Name", "Item B x2", ...].
player_inventory_list = [] # List of strings representing items in the player's inventory. E.g., ["Item C x5", ...].
room_inventory_scroll_y = 0 # Scroll position for the room inventory list (0 is top).
player_inventory_scroll_y = 0 # Scroll position for the player inventory list (0 is top).

# Care Package Button State
# Index of the first package button shown in the current page (0-based index of CARE_PACKAGES list).
package_button_visible_start_index = 0


# --- Background State ---
# Variable holding the current background image.

background_image = None # Variable to hold the currently loaded background image surface.


# --- Conceptual References (Not actual state instances) ---
# These are placeholders or reminders for objects managed elsewhere.
# chatbot = None # Not defining the instance here, reference only.


is_muted = False # Boolean flag for muting/unmuting sounds.



# --- Garden Tick State ---
next_garden_tick_time = 0 # Stores the time (ms) when the next garden tick is due



# --- NEW: Lore Panel State ---
lore_panel_visible = False # True if the lore panel is currently displayed
lore_panel_content = {'title': '', 'body_wrapped_lines': [], 'body_total_height': 0} # Stores processed lore content
lore_panel_scroll_y = 0 # Current vertical scroll offset for the lore body


# For care package buttons hover implementation
hovered_package_identifier = None

package_scroll_y = 0

highlight_items_list = []

hover_stat=None