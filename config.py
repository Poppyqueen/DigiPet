# config.py (Modifications for Care Package GUI Button Configuration)

import pygame
import math
from care_packages import (
    care_package_1_general_survival, care_package_2_hydration_refreshment,
    care_package_3_hearty_meal_kit, care_package_4_quick_snacks_energy,
    care_package_friend_comfort_food, care_package_6_extreme_hydration, 
    care_package_7_hearty_survival_rations, care_package_8_utility_mix,
    care_package_9_basic_hygiene, care_package_2_cooking_kit
)



# --- Configuration ---
WIDTH, HEIGHT = 550, 550
PANEL_WIDTH = 225 # This is for the chat panel on the RIGHT
INPUT_HEIGHT = 40
PADDING = 5 # Space around elements within the panel
SCROLL_SPEED = 25 # Pixels to scroll per mouse wheel tick
MAX_MESSAGE_HISTORY = 10 # Keep it short
CURSOR_INTERVAL = 500 # Milliseconds for cursor blink

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (50, 50, 50) # Chat panel background
DARK_GREY = (30, 30, 30) # Input box background
LIGHT_GREY = (200, 200, 200) # Input text color
BLUE = (100, 150, 255) # User message color
GREEN = (100, 255, 100) # Bot message color
RED = (255, 100, 100) # Error color
YELLOW = (255, 255, 100) # System message color
ORANGE = (255, 165, 0) # Color for locked input indicator
# Add a color for the inventory toggle button if needed, or reuse one
INVENTORY_BUTTON_COLOR = (150, 100, 255) # Example purple/pinkish color
PURPLE = (150, 100, 255)
# Define care packages, using colors above
CARE_PACKAGES = [
    {"package": care_package_1_general_survival, "room_id": 200002, "color": RED}, # 
    {"package": care_package_2_hydration_refreshment, "room_id": 200002, "color": BLUE}, # 
    {"package": care_package_3_hearty_meal_kit, "room_id": 200002, "color": RED}, # 
    {"package": care_package_4_quick_snacks_energy, "room_id": 200001, "color": YELLOW}, # 
    {"package": care_package_friend_comfort_food, "room_id": 200001, "color": YELLOW}, # 
    {"package": care_package_6_extreme_hydration, "room_id": 200002, "color": BLUE}, # 
    {"package": care_package_7_hearty_survival_rations, "room_id": 200002, "color": RED}, #
    {"package": care_package_8_utility_mix, "room_id": 200001, "color": GREEN}, # 
    {"package": care_package_9_basic_hygiene, "room_id": 200004, "color": PURPLE}, # 
    {"package": care_package_2_cooking_kit, "room_id": 200002, "color": WHITE} # KITCHEN
]

# Background
fallback_bg_color = (50, 50, 70)

# Circle configuration
CIRCLE_RADIUS = 100
# Calculate the base center coordinates: middle horizontally (outside panel), middle vertically
BASE_CIRCLE_CENTER_X = (WIDTH - PANEL_WIDTH) // 2
BASE_CIRCLE_CENTER_Y = HEIGHT // 2

# --- Animation Configuration ---
# ... (existing animation configs) ...
SHAKE_INTENSITY = 7
SHAKE_DURATION_MS = 500
SHAKE_FREQUENCY_HZ = 25
SAD_DROP_AMOUNT = 100
SAD_DROP_DURATION_MS = 900
SAD_RISE_DURATION_MS = 800
SAD_SHAKE_INTENSITY = 1
SAD_SHAKE_DURATION_MS = 900
SAD_SHAKE_FREQUENCY_HZ = 2
BASE_BOB_AMPLITUDE = 5
BASE_BOB_FREQUENCY = 0.5
BASE_SWAY_AMPLITUDE = 3
BASE_SWAY_FREQUENCY = 0.3
BASE_PHASE_SHIFT = math.pi / 2


# Happy Animation Constants (New)
HAPPY_DIP_DURATION_MS = 300    # Shorter dip duration?
HAPPY_SHAKE_DURATION_MS = 200 # Shorter, faster shake?
HAPPY_RISE_DURATION_MS = 1000   # Quick bounce up?
HAPPY_DIP_AMOUNT = 25          # Smaller dip amount?
HAPPY_SHAKE_FREQUENCY_HZ = 12.0 # Faster shake frequency?
HAPPY_SHAKE_INTENSITY = 3      # Smaller shake intensity?


# --- Idle Timer Configuration ---
IDLE_TIMEOUT_MINUTES = 3
IDLE_TIMEOUT_MS = IDLE_TIMEOUT_MINUTES * 60 * 1000

# --- Custom Events ---
# Use pygame.event.custom_type() for unique event IDs
CHANGE_BACKGROUND_EVENT = pygame.event.custom_type()
SHAKE_CIRCLE_EVENT = pygame.event.custom_type()
START_SAD_EVENT = pygame.event.custom_type()
PLAY_SOUND_EVENT = pygame.event.custom_type()
ADD_ITEMS_EVENT = pygame.event.custom_type() # Assuming this was needed for the Ctrl+key logic
CHATBOT_RESPONSE_EVENT = pygame.event.custom_type()
START_SLEEP_EVENT = pygame.event.custom_type()
STAT_CHANGED_EVENT = pygame.event.custom_type()

START_HAPPY_EVENT = pygame.event.custom_type()

# --- NEW: Inventory Events ---
ROOM_INVENTORY_EVENT = pygame.event.custom_type() # Signal with room inventory LIST of strings
PLAYER_INVENTORY_EVENT = pygame.event.custom_type() # Signal with player inventory LIST of strings


# --- NEW: Inventory Toggle Button Config ---
INVENTORY_TOGGLE_BUTTON_SIZE = 12 # Diameter of the dot
# Position relative to the bottom-left corner of the main *game* area (left of the panel)
# Offset from the bottom-left of the entire screen
INVENTORY_TOGGLE_BUTTON_POS_X = PADDING + INVENTORY_TOGGLE_BUTTON_SIZE // 2 # Centered horizontally with padding
INVENTORY_TOGGLE_BUTTON_POS_Y = HEIGHT - PADDING - INVENTORY_TOGGLE_BUTTON_SIZE // 2 # Centered vertically with padding


# --- NEW: Inventory Panel Config (Full-Screen Modal Overlay) ---
# The panel will cover the main game area, NOT the chat panel
INVENTORY_PANEL_RECT = pygame.Rect(0, 0, WIDTH - PANEL_WIDTH, HEIGHT)

# Panel Visuals
INVENTORY_PANEL_BG_COLOR = (20, 20, 20, 200) # Very dark grey with some transparency
INVENTORY_PANEL_BORDER_COLOR = WHITE # Optional border around the panel
INVENTORY_PANEL_PADDING = 20 # Padding inside the panel

# Layout within the panel
INVENTORY_PANEL_DIVIDER_WIDTH = 2 # Width of the line dividing room and player inventory
INVENTORY_PANEL_DIVIDER_COLOR = WHITE

# Text within the panel
INVENTORY_PANEL_TITLE_COLOR = WHITE
INVENTORY_PANEL_ITEM_COLOR = LIGHT_GREY
INVENTORY_PANEL_TITLE_HEIGHT = 30 # Space reserved for title at the top of each section
INVENTORY_PANEL_ITEM_SPACING = 2 # Vertical space between item lines (in addition to line_height)


# --- NEW: Pet Stat Configuration ---
# ... (existing stat configs) ...
STAT_ICON_DIR = "style/images/stat_icons/"
STAT_ICON_SIZE = (40, 40)
STAT_ICON_SPACING_Y = 5
STAT_ICON_START_X_SCREEN = PADDING # Keep as screen relative
STAT_ICON_START_Y_SCREEN = PADDING # Keep as screen relative

STAT_THRESHOLDS = {
    'full': 120,
    'half': 60
}

# --- Pop-up Message Configuration ---
# ... (existing popup configs) ...
POPUP_DURATION_MS = 6000
POPUP_MOVE_DISTANCE_Y = 50
POPUP_INITIAL_OFFSET_Y = -CIRCLE_RADIUS - 20
POPUP_COLOR = (100, 255, 100)
POPUP_RANDOM_SPREAD_X = 100
POPUP_RANDOM_SPREAD_Y = 60



# --- NEW: Care Package GUI Button Configuration ---
PACKAGE_BUTTON_SIZE = 12 # Diameter of the circular buttons
PACKAGE_BUTTON_SPACING_X = 5 # Horizontal space between buttons
SCROLL_BUTTON_SIZE = 12 # Size (width/height) of the scroll control buttons
SCROLL_BUTTON_COLOR_ENABLED = WHITE
SCROLL_BUTTON_COLOR_DISABLED = GREY # Or similar muted color
PACKAGE_BUTTON_BORDER_COLOR = WHITE # Border color for package buttons

# Define the list of packages including their button color and target room
# The 'package' value should be the actual Python variable/data structure
# imported from care_packages.py


# Calculate dimensions and positions for the button area
# Position them horizontally starting near the inventory toggle button, extending right
# Vertical position will match the inventory toggle button's vertical center
# BUTTON_ROW_Y is the Y coordinate for the *center* of the buttons/scroll controls
BUTTON_ROW_Y = HEIGHT - PADDING - INVENTORY_TOGGLE_BUTTON_SIZE // 2 # Vertical center alignment

# Let's assume a fixed width for the button area that can comfortably fit a few buttons.
# A width for 4 buttons is a reasonable starting point as per the plan.
# Width = (ButtonSize + Spacing) * N - Spacing
BUTTON_AREA_DISPLAY_WIDTH = (PACKAGE_BUTTON_SIZE + PACKAGE_BUTTON_SPACING_X) * 4 - PACKAGE_BUTTON_SPACING_X
# Ensure minimal width for at least one button if possible
BUTTON_AREA_DISPLAY_WIDTH = max(BUTTON_AREA_DISPLAY_WIDTH, PACKAGE_BUTTON_SIZE)


# Define the rects for the scroll buttons and the package button display area
# *** MODIFIED CALCULATION START ***
# They are placed to the right of the game area, before the chat panel.
# We'll calculate positions working backwards from the right edge of the game area.

# Y position for the *top* edge of the rects (centered around BUTTON_ROW_Y)
BUTTON_RECT_TOP_Y = BUTTON_ROW_Y - PACKAGE_BUTTON_SIZE // 2 # Assuming button size is same as scroll size

# Calculate the rect for the RIGHT scroll button
# Its right edge should be PADDING pixels from the right edge of the game area (WIDTH - PANEL_WIDTH)
RIGHT_SCROLL_BUTTON_X = (WIDTH - PANEL_WIDTH) - PADDING - SCROLL_BUTTON_SIZE
RIGHT_SCROLL_BUTTON_RECT = pygame.Rect(
    RIGHT_SCROLL_BUTTON_X,
    BUTTON_RECT_TOP_Y,
    SCROLL_BUTTON_SIZE,
    SCROLL_BUTTON_SIZE
)

# Calculate the rect for the button display area
# Its right edge should be PADDING pixels to the left of the RIGHT scroll button's left edge
CARE_PACKAGE_AREA_X = RIGHT_SCROLL_BUTTON_RECT.left - PADDING - BUTTON_AREA_DISPLAY_WIDTH
CARE_PACKAGE_AREA_RECT = pygame.Rect(
    CARE_PACKAGE_AREA_X,
    BUTTON_RECT_TOP_Y,
    BUTTON_AREA_DISPLAY_WIDTH,
    PACKAGE_BUTTON_SIZE
)

# Calculate the rect for the LEFT scroll button
# Its right edge should be PADDING pixels to the left of the button display area's left edge
LEFT_SCROLL_BUTTON_X = CARE_PACKAGE_AREA_RECT.left - PADDING - SCROLL_BUTTON_SIZE
LEFT_SCROLL_BUTTON_RECT = pygame.Rect(
    LEFT_SCROLL_BUTTON_X,
    BUTTON_RECT_TOP_Y,
    SCROLL_BUTTON_SIZE,
    SCROLL_BUTTON_SIZE
)
# *** MODIFIED CALCULATION END ***


# Add a slightly muted color for disabled package buttons
# Function to calculate disabled color
def get_disabled_color(color):
    """Blends a color with GREY for a disabled appearance."""
    r = (color[0] + GREY[0]) // 2
    g = (color[1] + GREY[1]) // 2
    b = (color[2] + GREY[2]) // 2
    return (r, g, b)

PACKAGE_BUTTON_COLOR_DISABLED = get_disabled_color # Store the function reference