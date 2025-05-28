# config.py - Organized Configuration Settings

import pygame
import math

# --- Data Imports ---
# Import specific care package data structures
from world_data.care_packages import (
    care_package_1_general_survival, care_package_2_hydration_refreshment,
    care_package_3_hearty_meal_kit, care_package_4_quick_snacks_energy,
    care_package_friend_comfort_food, care_package_6_extreme_hydration,
    care_package_7_hearty_survival_rations, care_package_8_utility_mix,
    care_package_9_basic_hygiene, care_package_2_cooking_kit, a_bundle_for_hydration_some_misc_items,
    the_most_epic_and_complete_bundle_for_cooking_raw_, a_bundle_for_energy_and_snacks,
    a_bundle_for_outdoor_survival, kitchen_pantry_bottled_goods_spices_etc_all_consum,
    salty_and_hardy_foods, fresh_vegetables, bread_package_all_kinds_of_food_implements_ingredi,
    raw_protein_package, more_raw_protein_package, cheat_bundles_items_that_replenish_stats_by_150_co,
    gardener_s_starter_kit
)


# --- General Configuration ---
# Window and Layout Dimensions
# slightly taller design?
WIDTH, HEIGHT = 450, 550
DEFAULT_PANEL_WIDTH = 200
INPUT_HEIGHT = 40
PADDING = 3 # Space around elements within the panel



TARGET_BRIGHTNESS = 0.3 # Transparent overlay brightness (0.0 to 1.0)

# # Window and Layout Dimensions
# # square window?
# WIDTH, HEIGHT = 550, 550
# DEFAULT_PANEL_WIDTH = 225
# INPUT_HEIGHT = 40
# PADDING = 2 # Space around elements within the panel


# # Window and Layout Dimensions 
# Smaller design?
# WIDTH, HEIGHT = 350, 550
# #PANEL_WIDTH = 160  # Width of the chat/info panel on the RIGHT
# INPUT_HEIGHT = 40  # Height of the input box at the bottom of the panel
# PADDING = 5  # General padding/space around elements

# Smaller design?
# WIDTH, HEIGHT = 350, 350
## PANEL_WIDTH = 130  # Width of the chat/info panel on the RIGHT
# INPUT_HEIGHT = 25  # Height of the input box at the bottom of the panel
# PADDING = 5  # General padding/space around elements


# Interaction & Timing
SCROLL_SPEED = 25  # Pixels to scroll per mouse wheel tick
MAX_MESSAGE_HISTORY = 50  # Max number of chat messages to display
CURSOR_INTERVAL = 500  # Milliseconds for text cursor blink rate
IDLE_TIMEOUT_MINUTES = 1 # Minutes until pet is considered idle
IDLE_TIMEOUT_MS = IDLE_TIMEOUT_MINUTES * 60 * 1000 # Calculated milliseconds
# Background
fallback_bg_color = (50, 50, 70) # Default background color


# --- Colors ---
# Base Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (50, 50, 50)
DARK_GREY = (30, 30, 30)
LIGHT_GREY = (200, 200, 200)

# Message/UI Specific Colors
BLUE = (100, 150, 255)  # User message color
GREEN = (100, 255, 100) # Bot message color
RED = (255, 100, 100)   # Error color / Alert color
YELLOW = (255, 255, 100) # System message color / Warning color
ORANGE = (255, 165, 0)  # Locked input indicator color
PURPLE = (150, 100, 255) # Example UI color / Package color

# Derived Colors
INVENTORY_BUTTON_COLOR = PURPLE # Reuse PURPLE for inventory toggle
# Function to calculate a muted color for disabled states
def get_disabled_color(color):
    """Blends a color with GREY for a disabled appearance."""
    r = (color[0] + GREY[0]) // 2
    g = (color[1] + GREY[1]) // 2
    b = (color[2] + GREY[2]) // 2
    return (r, g, b)

PACKAGE_BUTTON_COLOR_DISABLED = get_disabled_color # Store the function reference


# --- Pet Configuration ---
# Core Appearance & Positioning
CIRCLE_RADIUS = 20 # Radius of the pet circle
# Calculate the base center coordinates: middle horizontally (outside panel), middle vertically
def get_base_circle_center_x(current_panel_width):
    return (WIDTH - current_panel_width) // 2
BASE_CIRCLE_CENTER_Y = HEIGHT // 2



STEP_SIZE_LIMIT = 250 # Determines how big the pet grows per step of interaction

# Stat Thresholds (for determining pet state based on stats)
STAT_THRESHOLDS = {
    'full': 120, # Value at or above this is 'full'
    'half': 60   # Value below 'full' but at or above this is 'half' (default/neutral)
    # Values below 'half' are 'low' etc.
}


# --- Animation Configuration ---
# General Base Animation (Applies when idle/neutral)
BASE_BOB_AMPLITUDE = 5    # Vertical bobbing distance
BASE_BOB_FREQUENCY = 0.5  # Vertical bobbing frequency (Hz)
BASE_SWAY_AMPLITUDE = 3   # Horizontal swaying distance
BASE_SWAY_FREQUENCY = 0.3 # Horizontal swaying frequency (Hz)
BASE_PHASE_SHIFT = math.pi / 2 # Phase shift for bobbing/swaying (often used for circular/elliptical motion)

# Shake Animation (e.g., for errors)
SHAKE_INTENSITY = 7       # Pixel displacement during shake
SHAKE_DURATION_MS = 500   # How long the shake lasts
SHAKE_FREQUENCY_HZ = 25   # How fast the shaking is (Hz)

# Sad Animation
SAD_DROP_AMOUNT = 100         # Pixels the pet drops
SAD_DROP_DURATION_MS = 900    # Time for the initial drop
SAD_RISE_DURATION_MS = 800    # Time to rise back up
SAD_SHAKE_INTENSITY = 1       # Subtle shake intensity while sad
SAD_SHAKE_DURATION_MS = 900   # How long the subtle shake lasts
SAD_SHAKE_FREQUENCY_HZ = 2    # Slow subtle shake frequency
SAD_SIZE_CHANGE_PERCENTAGE = -0.20 # e.g., 20% decrease (note the negative)

# Happy Animation
HAPPY_DIP_AMOUNT = 5          # Smaller initial dip amount
HAPPY_DIP_DURATION_MS = 300  # Initial dip duration
HAPPY_RISE_DURATION_MS = 600  # Quick bounce up duration
HAPPY_SHAKE_DURATION_MS = 1200 # Duration of the main happy shake phase
HAPPY_SHAKE_FREQUENCY_HZ = 12.0 # Faster shake frequency
HAPPY_SHAKE_INTENSITY = 3     # Smaller shake intensity
HAPPY_SIZE_CHANGE_PERCENTAGE = 0.40 # e.g., 40% increase

# Happy Animation Phase 2 (Shake with Orbit)
HAPPY_ORBIT_RADIUS = 50 # Radius of the orbital movement
HAPPY_ORBIT_FREQUENCY_HZ = 0.5 # Frequency of the orbital movement (Hz)
HAPPY_ORBIT_START_ANGLE = 0 # Starting phase angle of the orbit (radians)
HAPPY_ORBIT_FADE_IN_DURATION_MS = 500 # Duration for orbit to fade in
HAPPY_ORBIT_FADE_OUT_DURATION_MS = 500 # Duration for orbit to fade out

# Angry Animation
ANGRY_TENSE_DURATION_MS = 850 # Time for the initial tense/move down
ANGRY_TENSE_AMOUNT = 55 # Pixels moved down during tense phase
ANGRY_VIBRATE_DURATION_MS = 2000 # How long the intense vibration lasts
ANGRY_VIBRATE_FREQUENCY_HZ = 5 # Hz (very rapid vibration frequency)
ANGRY_VIBRATE_INTENSITY = 10 # Pixels (small, intense vibration amplitude)
ANGRY_SETTLE_DURATION_MS = 650 # Time to settle back up
ANGRY_SIZE_INCREASE_PERCENTAGE = 0.8 # Placeholder, adjust if needed

# Excited Animation
EXCITED_BOUNCE_DURATION_MS = 150 # Time for the initial quick bounce up
EXCITED_BOUNCE_AMOUNT = 22 # Pixels bounced up (will result in negative y offset)
EXCITED_JIGGLE_DURATION_MS = 1800 # How long the rapid jiggle lasts
EXCITED_JIGGLE_FREQUENCY_HZ = 30 # Hz (super fast jiggle frequency)
EXCITED_JIGGLE_INTENSITY = 20 # Pixels (medium jiggle amplitude)
EXCITED_SETTLE_DURATION_MS = 400 # Time to settle back down
EXCITED_ORBIT_FREQUENCY_HZ = 2 * 1000.0 / EXCITED_JIGGLE_DURATION_MS # Calculated based on jiggle duration
EXCITED_ORBIT_RADIUS = 100 # Radius of orbital movement
EXCITED_ORBIT_START_ANGLE = 0 # Starting phase angle
EXCITED_ORBIT_FADE_IN_DURATION_MS = 1000 # Duration for orbit to fade in
EXCITED_JIGGLE_FADE_IN_DURATION_MS= 1000 # Duration for jiggle intensity to fade in

# Thinking U-Shape Animation Configuration (Movement path)
THINKING_U_CYCLES = 2 # Number of full back-and-forth U traversals
THINKING_SEGMENT_DURATION_MS = 550 # Duration in milliseconds for each straight segment of the U path
# Points defining the U-shape relative to the pet's center (origin 0,0)
THINKING_POINT_P1_Y = 20 # Y-offset for the intermediate point (downwards)
THINKING_POINT_P2_X = -25 # X-offset for the bottom-left point
THINKING_POINT_P2_Y = 30 # Y-offset for the bottom-left point (downwards)
THINKING_POINT_P3_X = 25 # X-offset for the bottom-right point
THINKING_POINT_P3_Y = 30 # Y-offset for the bottom-right point (downwards)

# Curious Animation (Sustained state with a peek movement)
CURIOUS_SWAY_AMPLITUDE_X = 55 # Maximum horizontal pixel displacement
CURIOUS_SWAY_FREQUENCY_HZ = 3 / 14.0 # Frequency adjusted for a specific duration cycle
CURIOUS_SWAY_AMPLITUDE_Y = 10 # Optional subtle vertical sway amplitude (set to 0 for none)
CURIOUS_SWAY_PHASE_SHIFT_Y = 0 # Phase shift for vertical sway
CURIOUS_SIZE_CHANGE_PERCENTAGE = 0.10 # Max percentage size change during pulsing
CURIOUS_SIZE_PULSE_FREQUENCY_HZ = 3 # Frequency of size pulse (Hz)
CURIOUS_DURATION_MS = 7000 # Total duration of the curious animation state


# Confused X-Shape Animation Configuration (Movement path)
CONFUSED_PHASE_DURATION_MS = 2200 # Duration for each segment of the X path
CONFUSED_X_OFFSET_AMOUNT = 70 # Max horizontal offset for the X points
CONFUSED_Y_OFFSET_AMOUNT = 70 # Max vertical offset for the X points
CONFUSED_SIZE_PULSE_AMPLITUDE_PERCENTAGE = 0.15 # Max percentage size change during pulse
CONFUSED_SIZE_PULSE_FREQUENCY_HZ = .5 # Frequency of the size pulsing (Hz)


# --- UI Configuration ---

# Panel Toggle Button
PANEL_TOGGLE_BUTTON_SIZE = (20, 40) # width, height
PANEL_TOGGLE_BUTTON_COLOR = (100, 100, 200) # A distinct color

# --- Mute Button Settings ---
MUTE_BUTTON_SIZE = 15  # Diameter for a circular button
MUTE_BUTTON_POS_X = WIDTH - MUTE_BUTTON_SIZE # X-coordinate (e.g., near top-right)
MUTE_BUTTON_POS_Y = MUTE_BUTTON_SIZE  # Y-coordinate (e.g., near top-right)
MUTE_BUTTON_COLOR = (100, 100, 100) # Dark grey when active (muted)
MUTE_BUTTON_UNMUTED_COLOR = (50, 200, 50) # Green when unmuted
MUTE_BUTTON_BORDER_COLOR = (200, 200, 200) # Light grey border

MAX_ACTIVE_POPUPS = 5

# Chat Panel Display
HISTORY_HORIZONTAL_PADDING = 1 # Padding inside history display area (left and right)


# Inventory Toggle Button
INVENTORY_TOGGLE_BUTTON_SIZE = 12 # Diameter of the inventory toggle button (dot)
# Position relative to the bottom-left corner of the main *game* area
# Offset from the bottom-left of the entire screen
INVENTORY_TOGGLE_BUTTON_POS_X = PADDING + INVENTORY_TOGGLE_BUTTON_SIZE // 2 # Centered horizontally with padding
INVENTORY_TOGGLE_BUTTON_POS_Y = HEIGHT - PADDING - INVENTORY_TOGGLE_BUTTON_SIZE // 2 # Centered vertically with padding


# Inventory Panel (Full-Screen Modal Overlay)
# Rect covers the main game area, NOT the chat panel
def get_inventory_panel_rect(current_panel_width):
    return pygame.Rect(0, 0, WIDTH - current_panel_width, HEIGHT)
# Panel Visuals
INVENTORY_PANEL_BG_COLOR = (20, 20, 20, 200) # Very dark grey with some transparency
INVENTORY_PANEL_BORDER_COLOR = WHITE # Optional border
INVENTORY_PANEL_PADDING = 20 # Padding inside the panel
# Layout within the panel
INVENTORY_PANEL_DIVIDER_WIDTH = 2 # Width of divider line
INVENTORY_PANEL_DIVIDER_COLOR = WHITE
# Text within the panel
INVENTORY_PANEL_TITLE_COLOR = WHITE
INVENTORY_PANEL_ITEM_COLOR = LIGHT_GREY
INVENTORY_PANEL_TITLE_HEIGHT = 30 # Space reserved for title at the top of each section
INVENTORY_PANEL_ITEM_SPACING = 2 # Vertical space between item lines
INVENTORY_PANEL_ITEM_HORIZONTAL_PADDING = 2 # Horizontal padding for item text
INVENTORY_PANEL_ITEM_VERTICAL_PADDING = 10 # Vertical padding for item text


# Care Package GUI Buttons
PACKAGE_BUTTON_HEIGHT = (INPUT_HEIGHT)#-PADDING # Same as width for circular buttons
PACKAGE_BUTTON_WIDTH = int(PACKAGE_BUTTON_HEIGHT/2)# Diameter of the circular package buttons
PACKAGE_BUTTON_SPACING_X = 1 # Horizontal space between package buttons
PACKAGE_BUTTON_BORDER_COLOR = WHITE # Border color for package buttons

SCROLL_BUTTON_HEIGHT = (INPUT_HEIGHT)#-PADDING # Height of the scroll control buttons
SCROLL_BUTTON_WIDTH = SCROLL_BUTTON_HEIGHT/2 # Size (width/height) of the scroll control buttons
SCROLL_BUTTON_COLOR_ENABLED = WHITE
SCROLL_BUTTON_COLOR_DISABLED = GREY # Muted color for disabled scroll buttons

# Calculate dimensions and positions for the button area
# Position them horizontally starting near the inventory toggle button, extending right
# Vertical position will match the inventory toggle button's vertical center
# BUTTON_ROW_Y is the Y coordinate for the *center* of the buttons/scroll controls
BUTTON_ROW_Y = HEIGHT - PADDING - PACKAGE_BUTTON_HEIGHT // 2 # Vertical center alignment (assuming same size as toggle)


# Calculate how many buttons can fit in the available width
# TODO: Recalculate these in GUI modules
# BUTTONS_MAX_COUNT = (WIDTH - PANEL_WIDTH - (SCROLL_BUTTON_WIDTH) * 2) // (PACKAGE_BUTTON_WIDTH + PACKAGE_BUTTON_SPACING_X)

# Width = (ButtonSize + Spacing) * N - Spacing
# BUTTON_AREA_DISPLAY_WIDTH = (PACKAGE_BUTTON_WIDTH + PACKAGE_BUTTON_SPACING_X) * BUTTONS_MAX_COUNT - PACKAGE_BUTTON_SPACING_X


#BUTTON_AREA_DISPLAY_WIDTH = max(BUTTON_AREA_DISPLAY_WIDTH, PACKAGE_BUTTON_WIDTH) # Ensure minimal width for at least one button

# Define the rects for the scroll buttons and the package button display area
# They are placed to the right of the game area, before the chat panel.
# Calculated working backwards from the right edge of the game area (WIDTH - PANEL_WIDTH).

# Y position for the *top* edge of the rects (centered around BUTTON_ROW_Y)
#BUTTON_RECT_TOP_Y = BUTTON_ROW_Y - SCROLL_BUTTON_SIZE // 2 # Assuming button size is same as scroll size
BUTTON_RECT_TOP_Y = HEIGHT - PADDING - INPUT_HEIGHT

# Calculate the rect for the RIGHT scroll button
# Its right edge should be PADDING pixels from the right edge of the game area
# RIGHT_SCROLL_BUTTON_X = BUTTON_AREA_DISPLAY_WIDTH + (SCROLL_BUTTON_WIDTH)
# RIGHT_SCROLL_BUTTON_RECT = pygame.Rect(
#     RIGHT_SCROLL_BUTTON_X,
#     BUTTON_RECT_TOP_Y,
#     SCROLL_BUTTON_WIDTH,
#     SCROLL_BUTTON_HEIGHT
# )

# Calculate the rect for the button display area (where package buttons are drawn)
# Its right edge should be PADDING pixels to the left of the RIGHT scroll button's left edge
# CARE_PACKAGE_AREA_X = PADDING - BUTTON_AREA_DISPLAY_WIDTH
# CARE_PACKAGE_AREA_RECT = pygame.Rect(
#     CARE_PACKAGE_AREA_X,
#     BUTTON_RECT_TOP_Y,
#     BUTTON_AREA_DISPLAY_WIDTH,
#     PACKAGE_BUTTON_HEIGHT
# )

# Calculate the rect for the LEFT scroll button
# Its right edge should be PADDING pixels to the left of the button display area's left edge
# LEFT_SCROLL_BUTTON_X =  INVENTORY_TOGGLE_BUTTON_SIZE + INVENTORY_TOGGLE_BUTTON_SIZE // 2 + PADDING
# LEFT_SCROLL_BUTTON_RECT = pygame.Rect(
#     LEFT_SCROLL_BUTTON_X,
#     BUTTON_RECT_TOP_Y,
#     SCROLL_BUTTON_WIDTH,
#     SCROLL_BUTTON_HEIGHT
# )


# Stat Icons Display
STAT_ICON_DIR = "style/images/stat_icons/" # Directory containing stat icon images
STAT_ICON_SIZE = (40, 40) # Size to render stat icons
STAT_ICON_SPACING_Y = 5 # Vertical space between stat icons
STAT_ICON_START_X_SCREEN = PADDING # X position (screen relative) for the left edge of the icons
STAT_ICON_START_Y_SCREEN = PADDING # Y position (screen relative) for the top edge of the first icon


# Pop-up Message Configuration (for stat changes, etc.)
POPUP_DURATION_MS = 6000 # How long a pop-up message stays visible
POPUP_MOVE_DISTANCE_Y = 50 # How far the pop-up moves upwards
POPUP_INITIAL_OFFSET_Y = -CIRCLE_RADIUS - 20 # Starting Y offset relative to the pet's center
POPUP_COLOR = (100, 255, 100) # Default color for pop-up text (e.g., positive changes)
POPUP_RANDOM_SPREAD_X = 100 # Max horizontal random displacement from pet center
POPUP_RANDOM_SPREAD_Y = 60 # Max vertical random displacement from pet center


color_code={
    "hydration": BLUE,
    "fullness": RED,
    "misc": PURPLE,
    "ingredient": ORANGE,
    "combo": BLACK,
    "cheat": GREEN

}


# Reordered list based on the 'color' key
CARE_PACKAGES =   [
        {"package": care_package_1_general_survival,"color": "combo"},
        {"package": care_package_8_utility_mix, "color": "combo"},

        {"package": care_package_3_hearty_meal_kit,"color": "fullness"},
        {"package": care_package_4_quick_snacks_energy, "color": "fullness"},
        {"package": care_package_friend_comfort_food, "color": "fullness"},
        {"package": care_package_7_hearty_survival_rations,"color": "fullness"},
        {"package": a_bundle_for_energy_and_snacks,"color": "fullness"},
        {"package": a_bundle_for_outdoor_survival, "color": "fullness"},
        {"package": salty_and_hardy_foods,"color": "fullness"},
        {"package": fresh_vegetables,"color": "fullness"},

        {"package": care_package_2_hydration_refreshment,"color": "hydration"},
        {"package": care_package_6_extreme_hydration,"color": "hydration"},
        {"package": a_bundle_for_hydration_some_misc_items,"color": "hydration"},

        {"package": kitchen_pantry_bottled_goods_spices_etc_all_consum,"color": "ingredient"},
        {"package": care_package_2_cooking_kit,"color": "ingredient"},
        {"package": the_most_epic_and_complete_bundle_for_cooking_raw_,"color": "ingredient"},
        {"package": bread_package_all_kinds_of_food_implements_ingredi,"color": "ingredient"},
        {"package": raw_protein_package,"color": "ingredient"},
        {"package": more_raw_protein_package,"color": "ingredient"},

        {"package": cheat_bundles_items_that_replenish_stats_by_150_co, "color": "cheat"},
        {"package": gardener_s_starter_kit, "color": "cheat"}
    ]

# --- Event Configuration ---
# Use pygame.event.custom_type() for unique event IDs

CHANGE_BACKGROUND_EVENT = pygame.event.custom_type() # Trigger background change
SHAKE_CIRCLE_EVENT = pygame.event.custom_type() # Trigger shake animation
START_SAD_EVENT = pygame.event.custom_type() # Trigger sad animation
START_HAPPY_EVENT = pygame.event.custom_type() # Trigger happy animation
START_SLEEP_EVENT = pygame.event.custom_type() # Trigger sleep state/animation

PLAY_SOUND_EVENT = pygame.event.custom_type() # Request sound playback
ADD_ITEMS_EVENT = pygame.event.custom_type() # Request item addition to inventory (e.g. from command)
CHATBOT_RESPONSE_EVENT = pygame.event.custom_type() # Signal new chatbot response

STAT_CHANGED_EVENT = pygame.event.custom_type() # Signal that a pet stat has changed


TTS_PYGAME_SOUND_EVENT = pygame.event.custom_type() # Signal to play TTS audio via pygame jukebox


# Inventory & UI Related Events
ROOM_INVENTORY_EVENT = pygame.event.custom_type() # Signal with current room inventory LIST
PLAYER_INVENTORY_EVENT = pygame.event.custom_type() # Signal with current player inventory LIST
SHOW_ICON_POPUP_EVENT = pygame.event.custom_type() # Signal to show a stat/item change pop-up

MESSAGE_POPUP = pygame.event.custom_type()

MESSAGE_PADDING = 3 # Example: 10 pixels of padding between messages


# --- Garden Tick Configuration ---
GARDEN_TICK_INTERVAL_MINUTES = 1 # Tick every 1 minute
GARDEN_TICK_INTERVAL_MS = GARDEN_TICK_INTERVAL_MINUTES * 60 * 1000