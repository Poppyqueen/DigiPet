# gui_core.py

import pygame
import os

from pygame_int import config # Needed for colors, padding, dimensions, max history
from pygame_int import state # Needed for accessing/modifying chat_history, input_text, etc.
from pygame_int.main_digipet import gui_construct_colors

from pygame_int.main_digipet import gui_stat_icons
# --- Internal Module State (Initialized by init_gui) ---
_font = None
_line_height = 0
_panel_rect = None # Rect for the main side panel
_history_rect = None # Rect for the chat history area within the panel
_input_rect = None # Rect for the text input area within the panel
_history_display_area = None # Rect for the actual text rendering area in history (takes padding into account)
_text_width_limit = 0 # Max width for a single line of text in history
_stat_icons = {} # Dictionary to hold loaded and scaled stat icon surfaces: {(stat_name, level): surface}
overlay_surface = None # Will be initialized in init_gui_elements

# --- NEW: Inventory GUI Rects (These are initialized in init_gui, so they belong here) ---
_inventory_toggle_button_rect = None
_inventory_panel_rect = None
_room_list_area_rect = None
_player_list_area_rect = None
_room_title_rect = None
_player_title_rect = None

# --- NEW: Inventory Item List Drawing Variables ---
_inventory_item_draw_width = 0
_inventory_item_start_x_offset = 0

# --- NEW: Care Package GUI Rects and State ---
_care_package_area_rect = None
_left_scroll_button_rect = None
_right_scroll_button_rect = None
_buttons_per_page = 0

# --- NEW: Mute Button Rect ---
_mute_button_rect = None # Declare the global variable for the mute button

# --- NEW: Panel Toggle Button Rect ---
_panel_toggle_button_rect = None


# --- NEW: Lore Panel GUI Rects ---
_lore_panel_rect = None
_lore_panel_title_rect = None
_lore_panel_body_area_rect = None
_lore_panel_close_button_rect = None
_lore_panel_text_draw_width = 0
_lore_panel_text_start_x_offset = 0

# --- NEW: Lore Panel Toggle Button Rect ---
_lore_toggle_button_rect = None

# --- NEW: Clock Rects ---
_current_time_clock_rect = None
_sleep_duration_clock_rect = None


# --- Initialization Function ---
def init_gui_elements(font, line_height, current_panel_width):
    """Initializes GUI module with necessary objects and dimensions."""
    global _font, _line_height, _text_width_limit, _history_display_area
    # Panel rects are now global within this module, not passed in _gui_rects dict
    global _panel_rect, _history_rect, _input_rect
    global _inventory_toggle_button_rect, _inventory_panel_rect, \
           _room_list_area_rect, _player_list_area_rect, \
           _room_title_rect, _player_title_rect, \
           _inventory_item_draw_width, _inventory_item_start_x_offset # Add new globals
    # ADD NEW GLOBALS
    global _care_package_area_rect, _left_scroll_button_rect, _right_scroll_button_rect, _buttons_per_page
    global overlay_surface # Added for overlay_surface initialization
    global _mute_button_rect # Add the new global for the mute button
    global _panel_toggle_button_rect # Add new global for panel toggle button

    # Removed globals for _image_popup_display_area and _image_popup_background_surface as they are managed in gui_popups

    global _lore_panel_rect, _lore_panel_title_rect, _lore_panel_body_area_rect, \
           _lore_panel_close_button_rect, _lore_panel_text_draw_width, \
           _lore_panel_text_start_x_offset # Add new globals
    global _lore_toggle_button_rect # Add new global for lore toggle button

    global _current_time_clock_rect, _sleep_duration_clock_rect # Add new global for clock rects


    _font = font
    _line_height = line_height #

    # Calculate panel-related rects using current_panel_width
    _panel_rect = pygame.Rect(config.WIDTH - current_panel_width, 0, current_panel_width, config.HEIGHT)
    _input_rect = pygame.Rect(
        config.WIDTH - current_panel_width + config.PADDING,
        config.HEIGHT - config.INPUT_HEIGHT - config.PADDING,
        current_panel_width - 2 * config.PADDING,
        config.INPUT_HEIGHT
    )
    _history_rect = pygame.Rect(
        config.WIDTH - current_panel_width + config.PADDING,
        config.PADDING,
        current_panel_width - 2 * config.PADDING,
        config.HEIGHT - config.INPUT_HEIGHT - 3 * config.PADDING
    )
    # _history_display_area is the inner part of _history_rect for actual text.
    _history_display_area = pygame.Rect(
        _history_rect.left + config.HISTORY_HORIZONTAL_PADDING,
        _history_rect.top + config.PADDING, # Assuming PADDING is used vertically inside history_rect
        _history_rect.width - 2 * config.HISTORY_HORIZONTAL_PADDING,
        _history_rect.height - 2 * config.PADDING # Assuming PADDING is used vertically
    )

    # --- MODIFIED: Calculate text_width_limit based on history_display_area and padding ---
    # Use HISTORY_HORIZONTAL_PADDING for text width limit
    _text_width_limit = _history_display_area.width # Already accounts for horizontal padding
    # Ensure the width limit is at least a small positive number
    _text_width_limit = max(1, _text_width_limit)
    # print(f"History display area width: {_history_display_area.width}, Text width limit (with padding): {_text_width_limit}")


    # --- NEW: Calculate Mute Button Rect ---
    mute_button_size = config.MUTE_BUTTON_SIZE
    _mute_button_rect = pygame.Rect(
        config.MUTE_BUTTON_POS_X - mute_button_size // 2,
        config.MUTE_BUTTON_POS_Y - mute_button_size // 2,
        mute_button_size,
        mute_button_size
    )

    # --- Calculate Inventory Button Rect ---
    button_size = config.INVENTORY_TOGGLE_BUTTON_SIZE
    # Button is centered at its position (using config values defined as centers)
    _inventory_toggle_button_rect = pygame.Rect(
        config.INVENTORY_TOGGLE_BUTTON_POS_X - button_size // 2,
        config.INVENTORY_TOGGLE_BUTTON_POS_Y - button_size // 2,
        button_size,
        button_size
    )

    # --- Calculate Inventory Panel and Internal Rects ---
    # _inventory_panel_rect is now a function call using state.panel_width,
    # but it's for the *modal* inventory, not the side panel.
    # For now, it's using the config function which depends on a panel_width argument.
    # This might need to be state.panel_width if the modal should also adjust, or 0 if it's always full game area.
    # The subtask implies INVENTORY_PANEL_RECT in config.py was made into a function.
    # Let's assume it refers to the main game area (WIDTH - panel_width_when_inventory_is_shown)
    # However, the inventory panel is a modal, typically covering the game area,
    # so it should use the panel_width that was active when it was opened, or a fixed portion.
    # The config function get_inventory_panel_rect(current_panel_width) implies it's dynamic.
    # For now, let's pass 0, assuming the inventory modal covers the *entire* game area,
    # irrespective of the chat panel's current width. This might need refinement.
    _inventory_panel_rect = config.get_inventory_panel_rect(0) # Default to full game area if panel is hidden

    # Calculate the inner area after panel padding
    inner_panel_x = _inventory_panel_rect.left + config.INVENTORY_PANEL_PADDING
    inner_panel_y = _inventory_panel_rect.top + config.INVENTORY_PANEL_PADDING
    inner_panel_width = _inventory_panel_rect.width - 2 * config.INVENTORY_PANEL_PADDING
    inner_panel_height = _inventory_panel_rect.height - 2 * config.INVENTORY_PANEL_PADDING

    # Calculate rects for titles
    title_height = config.INVENTORY_PANEL_TITLE_HEIGHT
    half_inner_width = (inner_panel_width - config.INVENTORY_PANEL_DIVIDER_WIDTH) // 2

    _room_title_rect = pygame.Rect(
        inner_panel_x,
        inner_panel_y,
        half_inner_width,
        title_height
    )
    _player_title_rect = pygame.Rect(
        inner_panel_x + half_inner_width + config.INVENTORY_PANEL_DIVIDER_WIDTH,
        inner_panel_y,
        half_inner_width,
        title_height
    )

    # Calculate rects for item lists (below titles)
    list_area_y = inner_panel_y + title_height
    list_area_height = inner_panel_height - title_height # Remaining height for the list

    _room_list_area_rect = pygame.Rect(
        inner_panel_x,
        list_area_y,
        half_inner_width,
        list_area_height
    )
    _player_list_area_rect = pygame.Rect(
        inner_panel_x + half_inner_width + config.INVENTORY_PANEL_DIVIDER_WIDTH,
        list_area_y,
        half_inner_width,
        list_area_height
    )

    # --- NEW: Calculate Inventory Item Drawing Properties (with padding) ---
    # These are used by draw_item_list
    _inventory_item_draw_width = _room_list_area_rect.width - 2 * config.INVENTORY_PANEL_ITEM_HORIZONTAL_PADDING
    _inventory_item_draw_width = max(1, _inventory_item_draw_width) # Ensure positive width
    _inventory_item_start_x_offset = config.INVENTORY_PANEL_ITEM_HORIZONTAL_PADDING


    # --- NEW: Store Care Package GUI Rects and Calculate Buttons Per Page ---
    game_area_width = config.WIDTH - (current_panel_width if state.panel_visible else 0)
    
    BUTTON_RECT_TOP_Y = config.HEIGHT - config.PADDING - config.INPUT_HEIGHT

    max_buttons_area_width = game_area_width - (config.SCROLL_BUTTON_WIDTH * 2) - (config.PADDING * 3) - config.INVENTORY_TOGGLE_BUTTON_SIZE # Added more padding and inv toggle size
    
    if config.PACKAGE_BUTTON_WIDTH + config.PACKAGE_BUTTON_SPACING_X > 0:
        _buttons_per_page = max_buttons_area_width // (config.PACKAGE_BUTTON_WIDTH + config.PACKAGE_BUTTON_SPACING_X)
    else:
        _buttons_per_page = 0
    _buttons_per_page = max(1, _buttons_per_page) # Ensure at least 1 button if possible, or it becomes 0 if area is too small

    actual_button_area_display_width = (_buttons_per_page * config.PACKAGE_BUTTON_WIDTH) + (max(0, _buttons_per_page - 1) * config.PACKAGE_BUTTON_SPACING_X)
    
    # Ensure actual_button_area_display_width is not negative if _buttons_per_page becomes 0
    actual_button_area_display_width = max(0, actual_button_area_display_width)


    _left_scroll_button_rect = pygame.Rect(
        config.PADDING + config.INVENTORY_TOGGLE_BUTTON_SIZE + config.PADDING,
        BUTTON_RECT_TOP_Y,
        config.SCROLL_BUTTON_WIDTH,
        config.SCROLL_BUTTON_HEIGHT
    )

    _care_package_area_rect = pygame.Rect(
        _left_scroll_button_rect.right + config.PACKAGE_BUTTON_SPACING_X,
        BUTTON_RECT_TOP_Y,
        actual_button_area_display_width,
        config.PACKAGE_BUTTON_HEIGHT
    )

    _right_scroll_button_rect = pygame.Rect(
        _care_package_area_rect.right + config.PACKAGE_BUTTON_SPACING_X,
        BUTTON_RECT_TOP_Y,
        config.SCROLL_BUTTON_WIDTH,
        config.SCROLL_BUTTON_HEIGHT
    )
    # print(f"Initialized GUI. Buttons per page in Care Package area: {_buttons_per_page}")

    # --- Panel Toggle Button Calculation ---
    toggle_btn_width, toggle_btn_height = config.PANEL_TOGGLE_BUTTON_SIZE
    if state.panel_visible:
        toggle_x = config.WIDTH - current_panel_width - toggle_btn_width
    else:
        toggle_x = config.WIDTH - toggle_btn_width - config.PADDING
    toggle_y = config.HEIGHT // 2 - toggle_btn_height // 2
    _panel_toggle_button_rect = pygame.Rect(toggle_x, toggle_y, toggle_btn_width, toggle_btn_height)



    # --- NEW: Calculate Lore Panel Rects (full screen) ---
    _lore_panel_rect = pygame.Rect(0, 0, config.WIDTH, config.HEIGHT)

    # Calculate inner content area (panel_rect minus padding)
    lore_inner_x = _lore_panel_rect.left + config.LORE_PANEL_PADDING
    lore_inner_y = _lore_panel_rect.top + config.LORE_PANEL_PADDING
    lore_inner_width = _lore_panel_rect.width - 2 * config.LORE_PANEL_PADDING
    lore_inner_height = _lore_panel_rect.height - 2 * config.LORE_PANEL_PADDING

    _lore_panel_title_rect = pygame.Rect(
        lore_inner_x,
        lore_inner_y,
        lore_inner_width,
        config.LORE_PANEL_TITLE_HEIGHT
    )

    # Lore Panel Close Button (top right within the panel's padding)
    _lore_panel_close_button_rect = pygame.Rect(
        _lore_panel_rect.right - config.LORE_PANEL_PADDING - config.LORE_PANEL_CLOSE_BUTTON_SIZE,
        _lore_panel_rect.top + config.LORE_PANEL_PADDING,
        config.LORE_PANEL_CLOSE_BUTTON_SIZE,
        config.LORE_PANEL_CLOSE_BUTTON_SIZE
    )

    # Body area starts below the title and extends to the bottom padding
    _lore_panel_body_area_rect = pygame.Rect(
        lore_inner_x,
        lore_inner_y + config.LORE_PANEL_TITLE_HEIGHT,
        lore_inner_width,
        lore_inner_height - config.LORE_PANEL_TITLE_HEIGHT # Use inner_height - title_height
    )

    _lore_panel_text_draw_width = _lore_panel_body_area_rect.width - 2 * config.LORE_PANEL_PADDING # Padding for text
    _lore_panel_text_draw_width = max(1, _lore_panel_text_draw_width)
    _lore_panel_text_start_x_offset = config.LORE_PANEL_PADDING

    # --- NEW: Calculate Lore Panel Toggle Button Rect ---
    # Initial position (when panel is closed)
    _lore_toggle_button_rect = pygame.Rect(
        config.WIDTH // 2 - config.LORE_PANEL_TOGGLE_BUTTON_WIDTH // 2, # Centered horizontally
        config.PADDING, # Top padding
        config.LORE_PANEL_TOGGLE_BUTTON_WIDTH,
        config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT
    )

    # --- NEW: Initialize Clock Rects ---
    _current_time_clock_rect = pygame.Rect(
        config.WIDTH - config.CLOCK_WIDTH -  current_panel_width,
        config.PADDING,
        config.CLOCK_WIDTH,
        config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT
    )
    _sleep_duration_clock_rect = pygame.Rect(
        config.WIDTH - config.CLOCK_WIDTH - current_panel_width,
        config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT + config.PADDING,
        config.CLOCK_WIDTH,
        config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT
    )






    # Initialize overlay_surface
    screen_width = pygame.display.get_surface().get_width() if pygame.display.get_surface() else config.WIDTH
    screen_height = pygame.display.get_surface().get_height() if pygame.display.get_surface() else config.HEIGHT
    overlay_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)


    # --- Load stat icons ---
    _load_stat_icons() # This call is fine as _load_stat_icons is in this file.
    gui_stat_icons.update_stat_icon_rects()

    # Image popup display area and background surface initialization is now handled in gui_popups.show_image_popup

    # The following call to show_image_popup will be problematic if show_image_popup is not in gui_core.py
    # For now, I will leave it. It might need to be pygame_int.gui.show_image_popup if pygame_int.gui is the module.
    # Or, show_image_popup itself needs to be moved or refactored.
    # from pygame_int import gui # This would be a circular import if gui also imports gui_core
    # gui.show_image_popup("style/images/house_splash_v2.png", 5000, 1000, 3000, type=0)
    # For now, commenting out this problematic call as per instructions focusing on moving functions.
    # show_image_popup("style/images/house_splash_v2.png", 5000, 1000, 3000, type=0)

    # This was moved to game.py

    # if pygame.mixer.get_init(): 
    #     try:
    #         sound = pygame.mixer.Sound("style/sounds/intro.mp3") # Load your sound file
    #         sound.set_volume(0.5)
    #         sound.play()
    #         print("Playing sound from GUI Core init.") # Modified print statement
    #     except pygame.error as e:
    #         print(f"Could not play sound: {e}")
    # else:
    #     print("Pygame mixer not initialized. Cannot play sound.")

    print("GUI Core module initialized.") # Modified print statement


# --- Function to update GUI rects based on panel width ---
def update_gui_rects(current_panel_width):
    """Recalculates panel-related GUI rects based on the current panel width."""
    global _panel_rect, _history_rect, _input_rect, _history_display_area, _text_width_limit
    global _left_scroll_button_rect, _care_package_area_rect, _right_scroll_button_rect, _buttons_per_page
    global _panel_toggle_button_rect # Add panel toggle button rect
    global _lore_panel_rect, _lore_panel_title_rect, _lore_panel_body_area_rect, \
           _lore_panel_close_button_rect, _lore_panel_text_draw_width, \
           _lore_panel_text_start_x_offset # Add new globals
    global _lore_toggle_button_rect # Add new global for lore toggle button
    global _current_time_clock_rect, _sleep_duration_clock_rect # Add new global for clock rects


    _panel_rect = pygame.Rect(config.WIDTH - current_panel_width, 0, current_panel_width, config.HEIGHT)
    _input_rect = pygame.Rect(
        config.WIDTH - current_panel_width + config.PADDING,
        config.HEIGHT - config.INPUT_HEIGHT - config.PADDING,
        current_panel_width - 2 * config.PADDING,
        config.INPUT_HEIGHT
    )
    _history_rect = pygame.Rect(
        config.WIDTH - current_panel_width + config.PADDING,
        config.PADDING,
        current_panel_width - 2 * config.PADDING,
        config.HEIGHT - config.INPUT_HEIGHT - 3 * config.PADDING
    )
    _history_display_area = pygame.Rect(
        _history_rect.left + config.HISTORY_HORIZONTAL_PADDING,
        _history_rect.top + config.PADDING,
        _history_rect.width - 2 * config.HISTORY_HORIZONTAL_PADDING,
        _history_rect.height - 2 * config.PADDING
    )
    _text_width_limit = _history_display_area.width
    _text_width_limit = max(1, _text_width_limit)

    # Recalculate Care Package related rects
    game_area_width = config.WIDTH - (current_panel_width if state.panel_visible else 0)

    BUTTON_RECT_TOP_Y = config.HEIGHT - config.PADDING - config.INPUT_HEIGHT

    max_buttons_area_width = game_area_width - (config.SCROLL_BUTTON_WIDTH * 2) - (config.PADDING * 3) - config.INVENTORY_TOGGLE_BUTTON_SIZE
    
    if config.PACKAGE_BUTTON_WIDTH + config.PACKAGE_BUTTON_SPACING_X > 0:
        _buttons_per_page = max_buttons_area_width // (config.PACKAGE_BUTTON_WIDTH + config.PACKAGE_BUTTON_SPACING_X)
    else:
        _buttons_per_page = 0
    _buttons_per_page = max(1, _buttons_per_page)
    
    actual_button_area_display_width = (_buttons_per_page * config.PACKAGE_BUTTON_WIDTH) + (max(0, _buttons_per_page - 1) * config.PACKAGE_BUTTON_SPACING_X)
    actual_button_area_display_width = max(0, actual_button_area_display_width)

    _left_scroll_button_rect = pygame.Rect(
        config.PADDING + config.INVENTORY_TOGGLE_BUTTON_SIZE + config.PADDING,
        BUTTON_RECT_TOP_Y,
        config.SCROLL_BUTTON_WIDTH,
        config.SCROLL_BUTTON_HEIGHT
    )

    _care_package_area_rect = pygame.Rect(
        _left_scroll_button_rect.right + config.PACKAGE_BUTTON_SPACING_X,
        BUTTON_RECT_TOP_Y,
        actual_button_area_display_width,
        config.PACKAGE_BUTTON_HEIGHT
    )

    _right_scroll_button_rect = pygame.Rect(
        _care_package_area_rect.right + config.PACKAGE_BUTTON_SPACING_X,
        BUTTON_RECT_TOP_Y,
        config.SCROLL_BUTTON_WIDTH,
        config.SCROLL_BUTTON_HEIGHT
    )

    # --- Panel Toggle Button Calculation ---
    toggle_btn_width, toggle_btn_height = config.PANEL_TOGGLE_BUTTON_SIZE
    if state.panel_visible:
        # If panel is visible, button is to its left
        toggle_x = config.WIDTH - current_panel_width - toggle_btn_width
    else:
        # If panel is hidden, button is on the far right of the screen
        toggle_x = config.WIDTH - toggle_btn_width - config.PADDING
    toggle_y = config.HEIGHT // 2 - toggle_btn_height // 2
    _panel_toggle_button_rect = pygame.Rect(toggle_x, toggle_y, toggle_btn_width, toggle_btn_height)

    # Update inventory panel rects as it is meant to be dinamic

    global _inventory_panel_rect, _room_title_rect, _player_title_rect, _room_list_area_rect, _player_list_area_rect
    _inventory_panel_rect = config.get_inventory_panel_rect(current_panel_width if state.panel_visible else 0)


    # Calculate the inner area after panel padding
    inner_panel_x = _inventory_panel_rect.left + config.INVENTORY_PANEL_PADDING
    inner_panel_y = _inventory_panel_rect.top + config.INVENTORY_PANEL_PADDING
    inner_panel_width = _inventory_panel_rect.width - 2 * config.INVENTORY_PANEL_PADDING
    inner_panel_height = _inventory_panel_rect.height - 2 * config.INVENTORY_PANEL_PADDING

    # Calculate rects for titles
    title_height = config.INVENTORY_PANEL_TITLE_HEIGHT
    half_inner_width = (inner_panel_width - config.INVENTORY_PANEL_DIVIDER_WIDTH) // 2

    _room_title_rect = pygame.Rect(
        inner_panel_x,
        inner_panel_y,
        half_inner_width,
        title_height
    )
    _player_title_rect = pygame.Rect(
        inner_panel_x + half_inner_width + config.INVENTORY_PANEL_DIVIDER_WIDTH,
        inner_panel_y,
        half_inner_width,
        title_height
    )


    # Calculate rects for item lists (below titles)
    list_area_y = inner_panel_y + title_height
    list_area_height = inner_panel_height - title_height # Remaining height for the list

    _room_list_area_rect = pygame.Rect(
        inner_panel_x,
        list_area_y,
        half_inner_width,
        list_area_height
    )
    _player_list_area_rect = pygame.Rect(
        inner_panel_x + half_inner_width + config.INVENTORY_PANEL_DIVIDER_WIDTH,
        list_area_y,
        half_inner_width,
        list_area_height
    )



    # --- NEW: Recalculate Lore Panel Rects (full screen, static) ---
    _lore_panel_rect = pygame.Rect(0, 0, config.WIDTH, config.HEIGHT) # Always full screen

    lore_inner_x = _lore_panel_rect.left + config.LORE_PANEL_PADDING
    lore_inner_y = _lore_panel_rect.top + config.LORE_PANEL_PADDING
    lore_inner_width = _lore_panel_rect.width - 2 * config.LORE_PANEL_PADDING
    lore_inner_height = _lore_panel_rect.height - 2 * config.LORE_PANEL_PADDING

    _lore_panel_title_rect = pygame.Rect(
        lore_inner_x,
        lore_inner_y,
        lore_inner_width,
        config.LORE_PANEL_TITLE_HEIGHT
    )

    _lore_panel_close_button_rect = pygame.Rect(
        _lore_panel_rect.right - config.LORE_PANEL_PADDING - config.LORE_PANEL_CLOSE_BUTTON_SIZE,
        _lore_panel_rect.top + config.LORE_PANEL_PADDING,
        config.LORE_PANEL_CLOSE_BUTTON_SIZE,
        config.LORE_PANEL_CLOSE_BUTTON_SIZE
    )

    _lore_panel_body_area_rect = pygame.Rect(
        lore_inner_x,
        lore_inner_y + config.LORE_PANEL_TITLE_HEIGHT,
        lore_inner_width,
        lore_inner_height - config.LORE_PANEL_TITLE_HEIGHT
    )

    _lore_panel_text_draw_width = _lore_panel_body_area_rect.width - 2 * config.LORE_PANEL_PADDING
    _lore_panel_text_draw_width = max(1, _lore_panel_text_draw_width)
    _lore_panel_text_start_x_offset = config.LORE_PANEL_PADDING


    # --- NEW: Recalculate Lore Panel Toggle Button Rect ---
    if state.panel_visible:
        # If right panel is visible, move button to account for it
        _lore_toggle_button_rect = pygame.Rect(
            config.WIDTH // 2 - config.LORE_PANEL_TOGGLE_BUTTON_WIDTH // 2 -current_panel_width //2,
            config.PADDING, # Top padding
            config.LORE_PANEL_TOGGLE_BUTTON_WIDTH,
            config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT
        )

    else:
        # If  panel is not visible, keep button at the center
        _lore_toggle_button_rect = pygame.Rect(
            config.WIDTH // 2 - config.LORE_PANEL_TOGGLE_BUTTON_WIDTH // 2,
            config.PADDING, # Top padding
            config.LORE_PANEL_TOGGLE_BUTTON_WIDTH,
            config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT
        )
 

    # 1. Determine Height based on state
    # If expanded: Use the standard button height.
    # If collapsed: Use a thin "window shade" height (e.g., 10px).
    if getattr(state, 'clock_expanded', True):
        current_clock_height = config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT
        sleep_duration_height = config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT
    else:
        current_clock_height = config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT // 2  # Thin strip height
        sleep_duration_height = 0



    # 2. Determine X Position (Flush against the panel or screen edge)
    if state.panel_visible:
        clock_x = config.WIDTH - current_panel_width - config.CLOCK_WIDTH
    else:
        clock_x = config.WIDTH - config.CLOCK_WIDTH - (config.PADDING*2) -(config.MUTE_BUTTON_SIZE + (config.MUTE_BUTTON_SIZE // 2))

    # Current Time (Top)
    _current_time_clock_rect = pygame.Rect(
        clock_x,
        config.PADDING, # Top of screen
        config.CLOCK_WIDTH,
        current_clock_height
    )

    # Sleep Duration (Stacked immediately below Time)
    _sleep_duration_clock_rect = pygame.Rect(
        clock_x,
        config.PADDING + current_clock_height, # Starts where Time ends
        config.CLOCK_WIDTH,
        sleep_duration_height
    )

# --- Helper function to load stat icons ---
def _load_stat_icons():
    """Loads and scales stat icon images into _stat_icons dictionary."""
    global _stat_icons # This is a global in gui_core.py
    _stat_icons = {} # Clear existing icons

    stats = ["fullness", "hydration", "energy"]
    levels = ["full", "half", "empty"]
    icon_size = config.STAT_ICON_SIZE
    icon_dir = config.STAT_ICON_DIR

    # print(f"Loading stat icons from {icon_dir}..."): # Comment out for less spam

    for stat_name in stats:
        for level in levels:
            # Construct the expected file name based on convention
            file_name = f"{stat_name}_{level}.png"
            full_path = os.path.join(icon_dir, file_name)

            try:
                img_surface = pygame.image.load(full_path).convert_alpha() # Use convert_alpha for potential transparency
                scaled_surface = pygame.transform.scale(img_surface, icon_size)
                _stat_icons[(stat_name, level)] = scaled_surface
                # print(f" Successfully loaded {file_name}"): # Comment out for less spam
            except FileNotFoundError:
                print(f" Warning: Stat icon not found: {full_path}")
                _stat_icons[(stat_name, level)] = None 
            except pygame.error as e:
                print(f" Warning: Pygame error loading icon {full_path}: {e}")
                _stat_icons[(stat_name, level)] = None
            except Exception as e:
                print(f" Warning: Unexpected error loading icon {full_path}: {e}")
                _stat_icons[(stat_name, level)] = None

    # print(f"Finished loading stat icons. Loaded {len([s for s in _stat_icons.values() if s is not None])} icons.")

# --- Helper function to load and set background image ---

def load_and_set_background(image_path):
    """
    Loads an image and sets it as the background, checking a local directory first.
    """
    print(f"Attempting to load background image: {image_path}")
    image_dirs = ["style/images/local_rooms_images", "style/images/rooms_images", "style/images/local_rooms_images/local_ai_gens"]
    full_image_path = None
    
    # Check if the image_path has an extension
    if '.' not in image_path:
        base_name = image_path
        # Define common extensions to check for
        extensions = ['.jpg']
        
        # Iterate through directories and extensions to find the file
        for directory in image_dirs:
            for ext in extensions:
                potential_path = os.path.join(directory, f"{base_name}{ext}")
                if os.path.exists(potential_path):
                    full_image_path = potential_path
                    break
            if full_image_path:
                break
    else:
        # If image_path has an extension, check the specified directories directly
        for directory in image_dirs:
            potential_path = os.path.join(directory, image_path)
            if os.path.exists(potential_path):
                full_image_path = potential_path
                break

    # If the image was found, load and set it. Otherwise, handle the error.
    if full_image_path:
        try:
            img_surface = pygame.image.load(full_image_path)
            state.background_image = pygame.transform.scale(img_surface, (config.WIDTH, config.HEIGHT))
            print(f"Successfully set background to {full_image_path}")
        except pygame.error as e:
            print(f"Pygame Error loading image '{full_image_path}': {e}")
            state.background_image = None
        except Exception as e:
            print(f"An unexpected error occurred while loading background image '{full_image_path}': {e}")
            state.background_image = None
    else:
        print(f"Error: Background image file '{image_path}' not found in any specified directory: {image_dirs}")
        state.background_image = None


# --- Getter functions for rects ---
def get_button_rects():
     """Returns a dictionary of button rects."""
     global _inventory_toggle_button_rect, _mute_button_rect, _panel_toggle_button_rect # Add panel_toggle_button_rect
     global _lore_toggle_button_rect # Add new global
     global _current_time_clock_rect, _sleep_duration_clock_rect # NEW: Add clock rects
     rects = {}
     if _inventory_toggle_button_rect is not None:
         rects['inventory_toggle'] = _inventory_toggle_button_rect
     if _mute_button_rect is not None:
         rects['mute_button'] = _mute_button_rect
     if _panel_toggle_button_rect is not None:
         rects['panel_toggle'] = _panel_toggle_button_rect
     if _lore_toggle_button_rect is not None: # NEW: Add lore toggle button
         rects['lore_toggle'] = _lore_toggle_button_rect
     if _current_time_clock_rect is not None: # NEW: Add current time clock rect
         rects['current_time_clock'] = _current_time_clock_rect
     if _sleep_duration_clock_rect is not None: # NEW: Add sleep duration clock rect
         rects['sleep_duration_clock'] = _sleep_duration_clock_rect
     return rects


def get_panel_rects():
     """Returns a dictionary of panel rects. Now returns directly managed rects."""
     # These are globals in gui_core.py
     global _inventory_panel_rect, _room_list_area_rect, _player_list_area_rect
     # The main panel rects are now _panel_rect, _history_rect, _input_rect
     # This function was originally for the MODAL inventory panel.
     # Keeping its original purpose for now.
     if _inventory_panel_rect is None: # This is the modal inventory panel rect
         return {}
     return {
         'inventory_panel': _inventory_panel_rect, # Modal inventory
         'room_list_area': _room_list_area_rect, 
         'player_list_area': _player_list_area_rect 
     }

# --- NEW: Getter for the main UI panel rects ---
def get_gui_rects():
    """Returns a dictionary of the main GUI panel rects."""
    return {
        'panel_rect': _panel_rect,
        'history_rect': _history_rect,
        'input_rect': _input_rect,
        'history_display_area': _history_display_area
    }


# --- NEW: Getter for Lore Panel rects ---
def get_lore_panel_rects():
    """Returns a dictionary of Lore Panel rects."""
    global _lore_panel_rect, _lore_panel_title_rect, _lore_panel_body_area_rect, _lore_panel_close_button_rect
    if _lore_panel_rect is None:
        return {}
    return {
        'lore_panel': _lore_panel_rect,
        'lore_title_area': _lore_panel_title_rect,
        'lore_body_area': _lore_panel_body_area_rect,
        'lore_close_button': _lore_panel_close_button_rect
    }


