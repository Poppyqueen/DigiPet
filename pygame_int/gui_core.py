import pygame
import pygame.gfxdraw
import os
import colorsys # Keep if load_and_set_background or other functions here use it directly

from pygame_int import config # Needed for colors, padding, dimensions, max history
from pygame_int import state # Needed for accessing/modifying chat_history, input_text, etc.
from pygame_int import animation # If init_gui uses it
from pygame_int import gui_config # For constants used in init_gui

# --- Internal Module State (Initialized by init_gui) ---
_font = None
_line_height = 0
_gui_rects = {} # Dictionary to hold the calculated Rects
_text_width_limit = 0 # <--- This will be updated to include padding
_history_display_area = None # Direct reference for convenience
_stat_icons = {} # Dictionary to hold loaded and scaled stat icon surfaces: {(stat_name, level): surface}
overlay_surface = None # Will be initialized in init_gui

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

# --- Initialization Function ---
def init_gui(font, line_height, gui_rects):
    """Initializes GUI module with necessary objects and dimensions."""
    global _font, _line_height, _gui_rects, _text_width_limit, _history_display_area
    global _inventory_toggle_button_rect, _inventory_panel_rect, \
           _room_list_area_rect, _player_list_area_rect, \
           _room_title_rect, _player_title_rect, \
           _inventory_item_draw_width, _inventory_item_start_x_offset # Add new globals
    # ADD NEW GLOBALS
    global _care_package_area_rect, _left_scroll_button_rect, _right_scroll_button_rect, _buttons_per_page
    global overlay_surface # Added for overlay_surface initialization
    # Removed globals for _image_popup_display_area and _image_popup_background_surface as they are managed in gui_popups


    _font = font
    _line_height = line_height
    _gui_rects = gui_rects # Pass in chat/input/history rects
    # --- MODIFIED: Calculate text_width_limit based on history_display_area and padding ---
    _history_display_area = gui_rects['history_display_area']
    # Use HISTORY_HORIZONTAL_PADDING for text width limit
    _text_width_limit = _history_display_area.width - 2 * config.HISTORY_HORIZONTAL_PADDING
    # Ensure the width limit is at least a small positive number
    _text_width_limit = max(1, _text_width_limit)
    # print(f"History display area width: {_history_display_area.width}, Text width limit (with padding): {_text_width_limit}")


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
    _inventory_panel_rect = config.INVENTORY_PANEL_RECT # Defined directly in config now

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
    _left_scroll_button_rect = config.LEFT_SCROLL_BUTTON_RECT
    _right_scroll_button_rect = config.RIGHT_SCROLL_BUTTON_RECT
    _care_package_area_rect = config.CARE_PACKAGE_AREA_RECT

    # Calculate how many buttons fit horizontally in the display area
    button_width_with_spacing = config.PACKAGE_BUTTON_SIZE + config.PACKAGE_BUTTON_SPACING_X
    if button_width_with_spacing > 0:
        _buttons_per_page = _care_package_area_rect.width // button_width_with_spacing
        # Ensure at least 1 button fits if the area is big enough for one button's width
        if _care_package_area_rect.width >= config.PACKAGE_BUTTON_SIZE:
             _buttons_per_page = max(1, _buttons_per_page)
        else:
            _buttons_per_page = 0 # Area too small for even one button
    else:
        _buttons_per_page = 0 # Avoid division by zero if spacing is weird

    # print(f"Initialized GUI. Buttons per page in Care Package area: {_buttons_per_page}")

    # Initialize overlay_surface
    screen_width = pygame.display.get_surface().get_width() if pygame.display.get_surface() else config.WIDTH
    screen_height = pygame.display.get_surface().get_height() if pygame.display.get_surface() else config.HEIGHT
    overlay_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)


    # --- Load stat icons ---
    _load_stat_icons() # This call is fine as _load_stat_icons is in this file.

    # Image popup display area and background surface initialization is now handled in gui_popups.show_image_popup

    # The following call to show_image_popup will be problematic if show_image_popup is not in gui_core.py
    # For now, I will leave it. It might need to be pygame_int.gui.show_image_popup if pygame_int.gui is the module.
    # Or, show_image_popup itself needs to be moved or refactored.
    # from pygame_int import gui # This would be a circular import if gui also imports gui_core
    # gui.show_image_popup("style/images/house_splash_v2.png", 5000, 1000, 3000, type=0)
    # For now, commenting out this problematic call as per instructions focusing on moving functions.
    # show_image_popup("style/images/house_splash_v2.png", 5000, 1000, 3000, type=0)

    if pygame.mixer.get_init(): 
        try:
            sound = pygame.mixer.Sound("style/sounds/intro.mp3") # Load your sound file
            sound.set_volume(0.5)
            sound.play()
            print("Playing sound from GUI Core init.") # Modified print statement
        except pygame.error as e:
            print(f"Could not play sound: {e}")
    else:
        print("Pygame mixer not initialized. Cannot play sound.")


    print("GUI Core module initialized.") # Modified print statement

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
    """Loads an image and sets it as the background."""
    # state.background_image is used here. 'state' is imported.
    print(f"Attempting to load background image: {image_path}")
    full_image_path = None
    try:
        if '.' not in image_path:
            base, _ = os.path.splitext(image_path)
            potential_paths = [f"style/images/{base}.jpg", f"style/images/{base}.png", f"style/images/{base}.jpeg"]
            found_path = None
            for p in potential_paths:
                if os.path.exists(p):
                    found_path = p
                    break
            if not found_path:
                 print(f"Error: Background image file not found with common extensions in 'images/' directory: {potential_paths}")
                 state.background_image = None 
                 return
            full_image_path = found_path
            print(f"Found image at: {full_image_path}")
        else:
             full_image_path = image_path if os.path.exists(image_path) else f"style/images/{image_path}"
             if not os.path.exists(full_image_path):
                  print(f"Error: Background image file not found at specified path: {full_image_path}")
                  state.background_image = None
                  return

        img_surface = pygame.image.load(full_image_path)
        state.background_image = pygame.transform.scale(img_surface, (config.WIDTH, config.HEIGHT))
        print(f"Successfully set background to {full_image_path}")
    except pygame.error as e:
        print(f"Pygame Error loading image '{full_image_path}': {e}")
        state.background_image = None 
    except Exception as e:
         print(f"An unexpected error occurred while loading background image '{full_image_path}': {e}")
         state.background_image = None

# --- Getter functions for rects ---
def get_button_rects():
     """Returns a dictionary of button rects."""
     global _inventory_toggle_button_rect # This is a global in gui_core.py
     if _inventory_toggle_button_rect is None:
         return {}
     return {
         'inventory_toggle': _inventory_toggle_button_rect
     }

def get_panel_rects():
     """Returns a dictionary of panel rects."""
     # These are globals in gui_core.py
     global _inventory_panel_rect, _room_list_area_rect, _player_list_area_rect
     if _inventory_panel_rect is None:
         return {}
     return {
         'inventory_panel': _inventory_panel_rect,
         'room_list_area': _room_list_area_rect, 
         'player_list_area': _player_list_area_rect 
     }
