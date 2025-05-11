# gui.py

from pygame_int import config # Needed for colors, padding, dimensions, max history
from pygame_int import state # Needed for accessing/modifying chat_history, input_text, scroll_y, cursor state, background_image, sleep state, AND chatbot_is_processing!
from pygame_int import animation
import pygame

import os
import random # Add this import

# --- Internal Module State (Initialized by init_gui) ---
# These will hold references to objects created in game.py
_font = None
_line_height = 0
_gui_rects = {} # Dictionary to hold the calculated Rects
_text_width_limit = 0 # <--- This will be updated to include padding
_history_display_area = None # Direct reference for convenience


# --- NEW: Stat Icon State ---
_stat_icons = {} # Dictionary to hold loaded and scaled stat icon surfaces: {(stat_name, level): surface}


# --- NEW: Popup Message Class ---
class PopupMessage:
    """Represents a single floating pop-up message."""
    def __init__(self, text_surface, initial_pos, start_time):
        self.text_surface = text_surface # Pygame surface of the rendered text
        self.initial_pos = initial_pos   # Starting (x, y) tuple for the message
        self.start_time = start_time     # Milliseconds since the message started
        self.current_pos = list(initial_pos)   # Use a list so we can update it in place


# --- NEW: Inventory GUI Rects ---
_inventory_toggle_button_rect = None
_inventory_panel_rect = None # The main rect covering the game area
_room_list_area_rect = None # Rect for drawing room items within the panel
_player_list_area_rect = None # Rect for drawing player items within the panel
_room_title_rect = None # Rect for drawing room title
_player_title_rect = None # Rect for drawing player title

# --- NEW: Inventory Item List Drawing Variables ---
_inventory_item_draw_width = 0 # Calculated usable width for items
_inventory_item_start_x_offset = 0 # Calculated start x position for drawing items


# --- NEW: Care Package GUI Rects and State ---
_care_package_area_rect = None
_left_scroll_button_rect = None
_right_scroll_button_rect = None
_buttons_per_page = 0 # How many package buttons fit horizontally in the display area




# State for the new image popup
_image_popup_visible = False
_image_popup_image = None # pygame.Surface
_image_popup_start_time = 0
_image_popup_duration = 0
_image_popup_background_surface = None # Surface for the dimming effect
_image_popup_display_area = None # The rect where the image popup draws (likely center of screen)

# --- NEW Global Variables for Fading ---
_image_popup_fade_in_duration = 0
_image_popup_fade_out_duration = 0


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



    # --- Load stat icons ---
    _load_stat_icons()


    # Image popup display area - centered on the screen *outside* the panel
    screen_width = pygame.display.get_surface().get_width()
    screen_height = pygame.display.get_surface().get_height()
    panel_width = _gui_rects.get('panel_rect', pygame.Rect(0,0,0,0)).width
    main_display_width = screen_width - panel_width
    main_display_height = screen_height # Image popup can span the whole height

    popup_size = (65, 65) # 
    # global _image_popup_display_area
    # _image_popup_display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
    # # Center within the main display area (left of the panel)
    # _image_popup_display_area.center = (main_display_width // 2, screen_height // 2)
    global _image_popup_display_area
    _image_popup_display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])

    # Set the top-right corner to the top-right of the non-panel area
    _image_popup_display_area.topright = (main_display_width, 0)

    # Create dimming background surface initially
    global _image_popup_background_surface
    try:
        _image_popup_background_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        _image_popup_background_surface.fill((0, 0, 0, 128)) # Semi-transparent black
    except pygame.error as e:
        print(f"Warning: Could not create dimming background surface: {e}")
        _image_popup_background_surface = None

    show_image_popup("style/images/stat_icons/fullness_empty.png", 5000, 1000, 3000, type=0)
    if pygame.mixer.get_init(): # 
        try:
            sound = pygame.mixer.Sound("style/sounds/intro.mp3") # Load your sound file
            sound.set_volume(0.5)
            sound.play()
            print("Playing sound from GUI.")
        except pygame.error as e:
            print(f"Could not play sound: {e}")
    else:
        print("Pygame mixer not initialized. Cannot play sound.")


    print("GUI module initialized.")

# --- Helper function to load stat icons ---
def _load_stat_icons():
    """Loads and scales stat icon images into _stat_icons dictionary."""
    global _stat_icons
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
                # Decide how to handle missing icons: maybe load a placeholder or skip
                _stat_icons[(stat_name, level)] = None # Store None or a default error icon
            except pygame.error as e:
                print(f" Warning: Pygame error loading icon {full_path}: {e}")
                _stat_icons[(stat_name, level)] = None
            except Exception as e:
                print(f" Warning: Unexpected error loading icon {full_path}: {e}")
                _stat_icons[(stat_name, level)] = None

    # print(f"Finished loading stat icons. Loaded {len([s for s in _stat_icons.values() if s is not None])} icons.") # Comment out for less spam

# --- Helper function to get stat level string ---
def _get_stat_level(value):
    """Determines the icon level ('full', 'half', 'empty') for a given stat value (0-200)."""
    # Values can exceed 200, but the levels here are based on a 0-200 scale implicitly
    # Let's clamp for the icon logic
    clamped_value = max(0.0, min(200.0, value)) # Clamp to 0-200 range for icon mapping

    if clamped_value >= config.STAT_THRESHOLDS['full']:
        return 'full'
    elif clamped_value >= config.STAT_THRESHOLDS['half']:
        return 'half'
    else:
        return 'empty'


# --- Text Wrapping Function (Moved) ---
# --- CHANGE 2: Improve text wrapping to handle prefixes correctly ---
def wrap_text(text, max_width, prefix=""):
    """
    Wraps text based on maximum pixel width using the initialized font.
    Takes into account the prefix length for the first line if provided.
    """
    if _font is None:
        return [str(text)]  # Avoid crash, return text as single line

    lines = []
    if not text: return [""]

    words = text.split(' ')
    if not words: return [""]

    # Handle the first line with prefix differently
    first_line_max_width = max_width
    if prefix:
        try:
            prefix_width = _font.size(prefix)[0]
            first_line_max_width = max(1, max_width - prefix_width)
        except pygame.error as e:
            print(f"Pygame error calculating prefix width for '{prefix}': {e}")
            first_line_max_width = max_width # Fallback if size calculation fails


    current_line_words = []
    is_first_line = True
    current_max_width = first_line_max_width

    for word in words:
        # Handle long words that exceed max_width
        # Calculate width safely
        try:
             word_width = _font.size(word)[0]
        except pygame.error as e:
             print(f"Pygame error calculating word width for '{word}': {e}")
             word_width = current_max_width + 1 # Assume it's too wide if calculation fails


        if current_max_width > 0 and word_width > current_max_width:
            # Add the current line if not empty before adding the long word
            if current_line_words:
                lines.append(' '.join(current_line_words))
                current_line_words = []
                if is_first_line:
                    is_first_line = False
                    current_max_width = max_width  # Subsequent lines use full width
            lines.append(word)  # Add the long word on its own line
            continue

        # Check if adding the word exceeds the max width
        test_line = ' '.join(current_line_words + [word])
        # Calculate width safely
        try:
            test_line_width = _font.size(test_line)[0]
        except pygame.error as e:
            print(f"Pygame error calculating test line width for '{test_line}': {e}")
            test_line_width = current_max_width + 1 # Assume it's too wide


        if current_max_width <= 0 or test_line_width <= current_max_width:
            current_line_words.append(word)
        else:
            # Current line + word is too wide, add the current line and start a new one
            lines.append(' '.join(current_line_words))
            current_line_words = [word]
            if is_first_line:
                is_first_line = False
                current_max_width = max_width  # Subsequent lines use full width

    # Add the last line if it's not empty
    if current_line_words:
        lines.append(' '.join(current_line_words))

    return lines


# --- Helper to calculate the total wrapped height of all messages (Moved) ---
# --- CHANGE 4: Update the calculate_total_history_height function to use the improved wrap_text ---
def calculate_total_history_height(history_tuples, max_width):
    """Calculates the total pixel height needed to display all wrapped messages."""
    if _font is None or _line_height == 0:
        return len(history_tuples) * 20  # Rough estimate

    total_height = 0
    for text, msg_type in history_tuples:
        # Determine prefix for proper text wrapping calculation
        display_prefix = ""
        if msg_type == 'user':
            display_prefix = "You: "
        elif msg_type == 'bot':
            display_prefix = "Bot: "
        elif msg_type == 'error':
            display_prefix = "Error: "
        elif msg_type == 'system':
            display_prefix = "System: "
        elif msg_type == 'system_instruction':
            display_prefix = "Instruction: "

        # Use the prefix-aware wrapping function
        wrapped_lines = wrap_text(text, max_width, display_prefix)
        total_height += len(wrapped_lines) * _line_height
    return total_height

# --- Helper to add message and auto-scroll (Moved) ---
def add_message_to_history(text, msg_type):
    """Adds a message tuple (text, type) to history and auto-scrolls to bottom."""
    # Need global to modify module-level state variables imported from state.py

    # Prevent adding empty messages if they somehow get here
    if not text or not text.strip():
        # print(f"Attempted to add empty message of type {msg_type}. Ignoring.") # Debug
        return

    state.chat_history.append((text.strip(), msg_type)) # Add stripped text

    # Limit history size
    while len(state.chat_history) > config.MAX_MESSAGE_HISTORY:
         state.chat_history.pop(0) # Remove oldest

    # Automatically scroll to the bottom after adding messages (scroll_y = 0)
    # This shows the most recent message.
    state.scroll_y = 0 # Simply set scroll_y to 0 to show the latest message

    # print(f"Added message to history ({msg_type}): {text[:50]}...") # Debugging log


# --- NEW: Helper to calculate the total wrapped height of a list of strings ---
def calculate_list_height(item_list, draw_width):
    """Calculates the total pixel height needed to display a list of strings."""
    if _font is None or _line_height == 0:
         # print("Error: calculate_list_height called before gui.init_gui") # Avoid excessive logging
         return len(item_list) * (20 + config.INVENTORY_PANEL_ITEM_SPACING) # Rough estimate

    total_height = 0
    # Use the pre-calculated usable width for inventory items
    usable_width = _inventory_item_draw_width

    for item_string in item_list:
        # No prefix needed for inventory items
        wrapped_lines = wrap_text(item_string, usable_width, "")
        # Add line height for each line PLUS spacing AFTER the item
        total_height += len(wrapped_lines) * _line_height + config.INVENTORY_PANEL_ITEM_SPACING
    # Add padding at the bottom if needed (handled by the start/end draw checks?)
    # Let's just add the top padding to the initial Y in the drawing function.
    return total_height


# --- NEW: Helper to draw a list of strings within a rect with scrolling ---
def draw_item_list(surface, item_list, draw_rect, scroll_y, item_color):
    """
    Draws a list of strings onto a surface within the specified rectangle.
    Handles text wrapping and vertical scrolling.
    Uses pre-calculated item drawing width and horizontal offset.
    """
    if _font is None or _line_height == 0 or _inventory_item_draw_width <= 0:
        print("Error: draw_item_list called before gui.init_gui or with invalid width.")
        return

    # Use the draw_rect as the clipping area for drawing directly onto the surface
    clip_rect = draw_rect.copy()
    original_clip = surface.get_clip() # Save original clipping area
    surface.set_clip(clip_rect) # Set the clipping area


    # Calculate current Y position to start drawing the *first* item based on scroll
    # Start drawing from the top of the draw_rect, offset by:
    # - scroll_y (subtract, positive scrolls down)
    # - config.INVENTORY_PANEL_ITEM_VERTICAL_PADDING (add, for padding at the top)
    current_draw_y_absolute = draw_rect.top + config.INVENTORY_PANEL_ITEM_VERTICAL_PADDING - scroll_y


    # Draw each item string
    for item_string in item_list:
        # Use the pre-calculated usable width for wrapping
        # No prefix needed for inventory items
        wrapped_lines = wrap_text(item_string, _inventory_item_draw_width, "")
        item_total_line_height = len(wrapped_lines) * _line_height + config.INVENTORY_PANEL_ITEM_SPACING

        # Draw each line of the wrapped item string
        for i, line in enumerate(wrapped_lines):
            line_draw_y_absolute = current_draw_y_absolute + i * _line_height

            # Blit relative to the surface passed in. The clip_rect ensures only the correct part is drawn.
            # Use the pre-calculated horizontal start offset
            try:
                line_surface = _font.render(line, True, item_color)
                surface.blit(line_surface,
                             (draw_rect.left + _inventory_item_start_x_offset, line_draw_y_absolute))
            except pygame.error as e:
                 print(f"Pygame error rendering inventory item line '{line}': {e}")


        # After drawing all lines for the current item, move down the absolute drawing position
        current_draw_y_absolute += item_total_line_height

        # Optimization: If we're drawing below the visible area, stop
        # If the top of the *next* item would be below the bottom of the clipping rectangle, stop.
        # Consider vertical padding at the bottom of the list area
        if current_draw_y_absolute > clip_rect.bottom - config.INVENTORY_PANEL_ITEM_VERTICAL_PADDING:
             break # Stop drawing remaining items


    # Restore original clipping area
    surface.set_clip(original_clip)


# --- NEW: Function to draw the Inventory Panel ---
def draw_inventory_panel(screen):
    """
    Draws the full-screen modal inventory panel with room and player lists.
    This should only be called when state.inventory_panel_visible is True.
    """
    if _font is None or _inventory_panel_rect is None:
        print("Error: draw_inventory_panel called before gui.init_gui")
        return

    # Draw semi-transparent background over the game area
    # Create a surface with alpha
    overlay_surface = pygame.Surface((_inventory_panel_rect.width, _inventory_panel_rect.height), pygame.SRCALPHA)
    # Fill with the background color including alpha
    overlay_surface.fill(config.INVENTORY_PANEL_BG_COLOR)
    # Draw the overlay onto the main screen
    screen.blit(overlay_surface, (_inventory_panel_rect.left, _inventory_panel_rect.top))


    # Draw the main panel border if configured
    if config.INVENTORY_PANEL_BORDER_COLOR:
         pygame.draw.rect(screen, config.INVENTORY_PANEL_BORDER_COLOR, _inventory_panel_rect, 1)


    # Draw titles
    try:
        room_title_surface = _font.render("Room Inventory", True, config.INVENTORY_PANEL_TITLE_COLOR)
        # Center titles horizontally within their rects
        room_title_x = _room_title_rect.left + (_room_title_rect.width - room_title_surface.get_width()) // 2
        room_title_y = _room_title_rect.top + (_room_title_rect.height - room_title_surface.get_height()) // 2
        screen.blit(room_title_surface, (room_title_x, room_title_y))

        player_title_surface = _font.render("Pet Inventory", True, config.INVENTORY_PANEL_TITLE_COLOR)
        # Center titles horizontally within their rects
        player_title_x = _player_title_rect.left + (_player_title_rect.width - player_title_surface.get_width()) // 2
        player_title_y = _player_title_rect.top + (_player_title_rect.height - player_title_surface.get_height()) // 2
        screen.blit(player_title_surface, (player_title_x, player_title_y))
    except pygame.error as e:
        print(f"Pygame error rendering inventory titles: {e}")


    # Draw the central divider line
    divider_x = _inventory_panel_rect.left + _inventory_panel_rect.width // 2
    pygame.draw.line(
        screen,
        config.INVENTORY_PANEL_DIVIDER_COLOR,
        (divider_x, _inventory_panel_rect.top + config.INVENTORY_PANEL_PADDING), # Start below top padding
        (divider_x, _inventory_panel_rect.bottom - config.INVENTORY_PANEL_PADDING), # End above bottom padding
        config.INVENTORY_PANEL_DIVIDER_WIDTH
    )

    # Draw the item lists using the helper function
    # Need to pass the correct scroll value for each list
    draw_item_list(screen, state.room_inventory_list, _room_list_area_rect, state.room_inventory_scroll_y, config.INVENTORY_PANEL_ITEM_COLOR)
    draw_item_list(screen, state.player_inventory_list, _player_list_area_rect, state.player_inventory_scroll_y, config.INVENTORY_PANEL_ITEM_COLOR)


# --- NEW: Function to trigger a floating pop-up message ---
def show_popup_message(text, color=config.POPUP_COLOR):
    """
    Creates a new floating pop-up message and adds it to the active list.
    The message appears centered horizontally above the character's base
    position with a slight random spread, moves up, and fades out.

    Requires:
         String to display
    Optional:
         Color RGB tuple (100, 255, 100) to display the text in
    """
    if _font is None:
         print("Error: show_popup_message called before gui.init_gui")
         return # Cannot create message without font

    if not text or not text.strip():
         # print("Attempted to show empty popup message. Ignoring.") # Debug
         return # Don't show empty messages

    # Render the text message
    try:
        text_surface = _font.render(text.strip(), True, color)
    except pygame.error as e:
        print(f"Pygame error rendering popup text '{text}': {e}")
        return # Cannot create message if rendering fails

    # Calculate the base starting position (centered horizontally above character)
    # Character's base center is BASE_CIRCLE_CENTER_X, BASE_CIRCLE_CENTER_Y
    base_x = config.BASE_CIRCLE_CENTER_X - text_surface.get_width() // 2
    # Initial Y is above the character's center, adjusted by POPUP_INITIAL_OFFSET_Y
    base_y = config.BASE_CIRCLE_CENTER_Y + config.POPUP_INITIAL_OFFSET_Y

    # Add random spread to the initial position
    rand_offset_x = random.uniform(-config.POPUP_RANDOM_SPREAD_X, config.POPUP_RANDOM_SPREAD_X)
    rand_offset_y = random.uniform(-config.POPUP_RANDOM_SPREAD_Y, config.POPUP_RANDOM_SPREAD_Y)

    initial_x = base_x + rand_offset_x
    initial_y = base_y + rand_offset_y

    # Get the current time
    start_time = pygame.time.get_ticks()

    # Create the popup message object
    new_popup = PopupMessage(text_surface, (initial_x, initial_y), start_time)

    # Add the new popup to the list of active popups in state.py
    state.active_popups.append(new_popup)




# --- NEW Image Popup Function ---
def show_image_popup(image_path, duration_ms=2000, fade_in_ms=500, fade_out_ms=500, type=1):
    """
    Shows a temporary image popup centered on the screen (outside the panel)
    with optional fade-in and fade-out effects.

    Args:
        image_path (str): Path to the image file.
        duration_ms (int): Total duration in milliseconds the popup should be visible
                           (including fade-in and fade-out).
        fade_in_ms (int): Duration in milliseconds for the fade-in effect.
        fade_out_ms (int): Duration in milliseconds for the fade-out effect.
                           Note: The solid display time is duration_ms - fade_in_ms - fade_out_ms.
                                 If fade_in_ms + fade_out_ms >= duration_ms, there is no solid phase,
                                 just fading or instant display/hide.
    """
    global _image_popup_visible, _image_popup_image, _image_popup_start_time, _image_popup_duration
    global _image_popup_fade_in_duration, _image_popup_fade_out_duration
    global _image_popup_background_surface, _image_popup_display_area # Assuming _image_popup_display_area is defined elsewhere

    # Image popup display area - centered on the screen *outside* the panel
    screen_width = pygame.display.get_surface().get_width()
    screen_height = pygame.display.get_surface().get_height()
    panel_width = _gui_rects.get('panel_rect', pygame.Rect(0,0,0,0)).width
    main_display_width = screen_width - panel_width
    main_display_height = screen_height # Image popup can span the whole height

    # Check if Pygame display is initialized
    if pygame.display.get_surface() is None:
         print("Error: Pygame display not initialized. Cannot show image popup.")
         return

    if type == 0:
        popup_size = (200, 200)
        _image_popup_display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
        _image_popup_display_area.center = (screen_width // 2, screen_height // 2)
    elif type == 1:
        popup_size = (60, 60)
        _image_popup_display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
        # Set the top-right corner to the top-right of the non-panel area
        _image_popup_display_area.topright = (main_display_width, 0)

    elif type == 2: # --- ADD THIS NEW CASE ---
        # Centered within the NON-PANEL area
        popup_size = (150, 150) # Choose a size for this type
        _image_popup_display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
        _image_popup_display_area.center = (main_display_width // 2, screen_height // 2)

    else:
        # Default or handle unknown type
        popup_size = (200, 200) # Default size
        _image_popup_display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
        _image_popup_display_area.center = (screen_width // 2, screen_height // 2) # Default to center of whole screen


    # Basic validation for durations
    if duration_ms <= 0:
        print("Warning: duration_ms must be positive for image popup.")
        return
    fade_in_ms = max(0, fade_in_ms)
    fade_out_ms = max(0, fade_out_ms)
    if fade_in_ms + fade_out_ms > duration_ms:
         # If fade times are longer than total duration, adjust them proportionally
         # or just let the alpha calculation handle it (it will become 0 rapidly after max alpha reached)
         # Let's just ensure they don't exceed total if it simplifies calculation later
         # Or more simply, just ensure they are capped individually by the total duration
         # Let's keep it simple and just store the values. The drawing loop handles the rest.
         pass # The alpha calculation handles this case implicitly

    try:
        # Load and scale the image
        # It's crucial that the loaded image has an alpha channel for set_alpha() to work correctly.
        # .convert_alpha() is needed.
        raw_image = pygame.image.load(image_path)
        # Scale to the predefined display area size
        _image_popup_image = pygame.transform.scale(raw_image, _image_popup_display_area.size).convert_alpha()

        _image_popup_visible = True
        _image_popup_start_time = pygame.time.get_ticks()
        _image_popup_duration = duration_ms
        _image_popup_fade_in_duration = fade_in_ms
        _image_popup_fade_out_duration = fade_out_ms


        print(f"Attempting to show image popup: {image_path} (Total: {duration_ms}ms, FadeIn: {fade_in_ms}ms, FadeOut: {fade_out_ms}ms)") # Debug
    except FileNotFoundError:
        print(f"Error loading image for popup: File not found at '{image_path}'")
        _image_popup_visible = False
        _image_popup_image = None # Clean up state
    except pygame.error as e:
        print(f"Error loading or processing image for popup '{image_path}': {e}")
        _image_popup_visible = False
        _image_popup_image = None # Clean up state
    except Exception as e:
        print(f"An unexpected error occurred while preparing image popup '{image_path}': {e}")
        _image_popup_visible = False
        _image_popup_image = None # Clean up state


# --- NEW: Function to update the state of active pop-up messages ---
def update_popups(current_time_ms):
    """
    Updates the position and transparency of all active pop-up messages.
    Removes messages that have exceeded their duration.
    Should be called once per frame in the game loop.
    """
    global _image_popup_visible
    # Iterate backwards so removing items doesn't mess up the loop index
    for i in range(len(state.active_popups) - 1, -1, -1):
        popup = state.active_popups[i]

        elapsed_time = current_time_ms - popup.start_time
        progress = min(1.0, elapsed_time / config.POPUP_DURATION_MS) # Progress from 0 to 1

        # Check if message duration is over
        if progress >= 1.0:
            # print(f"Removing popup: '{popup.text_surface.get_rect().width}x{popup.text_surface.get_rect().height}'") # Debug
            state.active_popups.pop(i) # Remove the message
            continue # Move to the next message in the list

        # Calculate current Y position (moving upwards)
        popup.current_pos[1] = popup.initial_pos[1] - progress * config.POPUP_MOVE_DISTANCE_Y
        # X position remains constant
        # popup.current_pos[0] = popup.initial_pos[0] # No change to X

        # Calculate current alpha (fading out)
        # Alpha goes from 255 to 0 as progress goes from 0 to 1
        alpha = 255 * (1.0 - progress)

        # Update the surface's alpha
        popup.text_surface.set_alpha(int(alpha))



    # Update image popup
    if _image_popup_visible:
        if current_time_ms >= _image_popup_start_time + _image_popup_duration:
            _image_popup_visible = False
            # Optional: Explicitly clear the image surface if memory is a concern
            # _image_popup_image = None
            print("Image popup duration ended.") # Debug

# --- NEW: Function to draw active pop-up messages ---
def draw_popups(screen):
    """
    Draws all active pop-up messages onto the screen.
    Should be called during the drawing phase of the game loop.
    """
    # Iterate through active popups and draw them
    for popup in state.active_popups:
        # Only draw if alpha is > 0 (not fully faded)
        if popup.text_surface.get_alpha() > 0:
            screen.blit(popup.text_surface, popup.current_pos)


# --- NEW: Function to draw Care Package Buttons and Scroll Controls ---
# MODIFIED: Renamed parameter from is_currently_asleep to is_input_locked
def draw_package_buttons(screen, is_input_locked):
    """
    Draws the care package buttons and their scroll controls.
    Visually disables them if input is locked.
    """
    # Assuming these global variables are defined elsewhere (e.g., in gui.py init)
    global _left_scroll_button_rect, _right_scroll_button_rect, _care_package_area_rect, _buttons_per_page

    if _left_scroll_button_rect is None:
         # gui.init_gui hasn't been called, return empty list
         # print("Error: draw_package_buttons called before gui.init_gui") # Avoid excessive logging
         return

    total_packages = len(config.CARE_PACKAGES)
    visible_start = state.package_button_visible_start_index
    buttons_per_page = max(1, _buttons_per_page) # Ensure we don't divide by zero or less than 1
    visible_end = min(visible_start + buttons_per_page, total_packages)


    # Determine if scrolling is possible in each direction *before* considering input lock
    can_scroll_left = visible_start > 0
    can_scroll_right = visible_end < total_packages


    # Determine scroll button colors based on scroll possibility and lock state
    # Button is colored DISABLED if scrolling is not possible OR if input is locked
    left_scroll_color = config.SCROLL_BUTTON_COLOR_DISABLED if not can_scroll_left or is_input_locked else config.SCROLL_BUTTON_COLOR_ENABLED
    right_scroll_color = config.SCROLL_BUTTON_COLOR_DISABLED if not can_scroll_right or is_input_locked else config.SCROLL_BUTTON_COLOR_ENABLED


    # Draw Left Scroll Button (as a filled rectangle or triangle)
    pygame.draw.rect(screen, left_scroll_color, _left_scroll_button_rect)
    pygame.draw.rect(screen, config.WHITE, _left_scroll_button_rect, 1) # Border

    # Optional: Draw a triangle shape inside the scroll button rect
    if _left_scroll_button_rect.width > 4 and _left_scroll_button_rect.height > 4: # Only draw triangle if big enough
        # Check if the button is in the enabled state (can scroll AND not locked)
        if not is_input_locked and can_scroll_left:
            tri_pad_x = _left_scroll_button_rect.width // 4 # Use relative padding
            tri_pad_y = _left_scroll_button_rect.height // 4
            # Triangle points left
            points_left = [
                 (_left_scroll_button_rect.right - tri_pad_x, _left_scroll_button_rect.centery), # Right point
                 (_left_scroll_button_rect.left + tri_pad_x, _left_scroll_button_rect.top + tri_pad_y), # Top-left
                 (_left_scroll_button_rect.left + tri_pad_x, _left_scroll_button_rect.bottom - tri_pad_y) # Bottom-left
            ]
            pygame.draw.polygon(screen, config.WHITE, points_left) # Draw white arrow shape


    # Draw Right Scroll Button
    pygame.draw.rect(screen, right_scroll_color, _right_scroll_button_rect)
    pygame.draw.rect(screen, config.WHITE, _right_scroll_button_rect, 1) # Border

    # Optional: Draw a triangle shape inside the scroll button rect
    if _right_scroll_button_rect.width > 4 and _right_scroll_button_rect.height > 4:
         # Check if the button is in the enabled state (can scroll AND not locked)
         if not is_input_locked and can_scroll_right:
             tri_pad_x = _right_scroll_button_rect.width // 4
             tri_pad_y = _right_scroll_button_rect.height // 4
             # Triangle points right
             points_right = [
                 (_right_scroll_button_rect.left + tri_pad_x, _right_scroll_button_rect.centery), # Left point
                 (_right_scroll_button_rect.right - tri_pad_x, _right_scroll_button_rect.top + tri_pad_y), # Top-right
                 (_right_scroll_button_rect.right - tri_pad_x, _right_scroll_button_rect.bottom - tri_pad_y) # Bottom-right
             ]
             pygame.draw.polygon(screen, config.WHITE, points_right) # Draw white arrow shape


    # Draw Package Buttons within the display area
    button_size = config.PACKAGE_BUTTON_SIZE
    button_spacing = config.PACKAGE_BUTTON_SPACING_X
    # Center of the first button position within the care package area
    start_x_offset = _care_package_area_rect.left + button_size // 2
    button_y_center = _care_package_area_rect.centery # Vertical center of all buttons

    # Draw a background rect for the button area (optional, helps visualize)
    # pygame.draw.rect(screen, config.DARK_GREY, _care_package_area_rect)

    for i in range(visible_start, visible_end):
        package_info = config.CARE_PACKAGES[i]
        base_color = package_info["color"]
        # Button color is DISABLED color if input is locked, otherwise use the package's base color
        button_color = config.PACKAGE_BUTTON_COLOR_DISABLED(base_color) if is_input_locked else base_color

        # Calculate the button's center position relative to the screen
        # Position is based on its index within the *visible* page (i - visible_start)
        button_center_x = start_x_offset + (i - visible_start) * (button_size + button_spacing)

        # Draw the filled circle
        pygame.draw.circle(screen, button_color, (button_center_x, button_y_center), button_size // 2)
        # Draw the border
        pygame.draw.circle(screen, config.PACKAGE_BUTTON_BORDER_COLOR, (button_center_x, button_y_center), button_size // 2, 1)
# --- NEW: Function to get clickable regions for Care Package Buttons and Scroll Controls ---
def get_package_button_click_regions():
    """
    Returns a list of tuples (identifier, rect) for clickable package buttons and scroll controls.
    Only includes buttons that are currently visible.
    This function does NOT check if input is locked; that's handled in game.py.
    """
    click_regions = []
    if _left_scroll_button_rect is None:
         # gui.init_gui hasn't been called, return empty list
         # print("Error: get_package_button_click_regions called before gui.init_gui") # Avoid excessive logging
         return click_regions

    # Add scroll button regions (always potentially clickable if initialized)
    click_regions.append(("scroll_left", _left_scroll_button_rect))
    click_regions.append(("scroll_right", _right_scroll_button_rect))

    total_packages = len(config.CARE_PACKAGES)
    visible_start = state.package_button_visible_start_index
    buttons_per_page = max(1, _buttons_per_page) # Ensure correct calculation
    visible_end = min(visible_start + buttons_per_page, total_packages)


    # Calculate the button positions again to create the click rects
    button_size = config.PACKAGE_BUTTON_SIZE
    button_spacing = config.PACKAGE_BUTTON_SPACING_X
    start_x_offset = _care_package_area_rect.left + button_size // 2 # Center of the first button position
    button_y_center = _care_package_area_rect.centery # Vertical center of all buttons


    # Add regions for the visible package buttons
    for i in range(visible_start, visible_end):
        # Calculate the button's center position
        button_center_x = start_x_offset + (i - visible_start) * (button_size + button_spacing)
        # Create the rect for the button (centered around the calculated position)
        button_rect = pygame.Rect(
            button_center_x - button_size // 2,
            button_y_center - button_size // 2,
            button_size,
            button_size
        )
        # Add the region identifier and rect to the list
        click_regions.append((f"package_{i}", button_rect))

    return click_regions


# --- Function to draw the entire GUI panel ---
# MODIFIED: Changed parameter name to is_input_locked
def draw_gui(screen, current_time_ms, is_input_locked):
    global _image_popup_visible, _image_popup_image, _image_popup_background_surface, _image_popup_display_area

    """
    Draws the background, panel, chat history, input box, stats,
    care package buttons, and conditionally the inventory panel.
    """
    if _font is None or _line_height == 0 or not _gui_rects:
         print("Error: draw_gui called before gui.init_gui")
         return # Cannot draw without initialization

    # --- Always Draw Base Game UI Elements ---



        # Draw background image or fallback color



    # --- Draw the Dimming Background Surface (if visible) ---
    # Draw this *before* the popup image, *after* the background
    if _image_popup_visible and _image_popup_background_surface:
         screen.blit(_image_popup_background_surface, (0, 0))


    if not state.is_initial_popup_phase:

        if state.background_image:
            screen.blit(state.background_image, (0, 0))
        else:
            screen.fill(config.fallback_bg_color)

        # Unpack rects for easier access (always needed)
        panel_rect = _gui_rects['panel_rect']
        input_rect = _gui_rects['input_rect']
        history_rect = _gui_rects['history_rect']
        # Use the stored _history_display_area rect from init
        history_display_area = _history_display_area
        # Use the stored _text_width_limit from init
        text_width_limit = _text_width_limit


        # Draw the panel and history area backgrounds (always)
        pygame.draw.rect(screen, config.GREY, panel_rect)
        pygame.draw.rect(screen, config.DARK_GREY, history_rect)


        # --- Draw Stat Icons --- (always)
        stats_to_draw_order = ["fullness", "hydration", "energy"]
        icon_start_x = config.STAT_ICON_START_X_SCREEN
        icon_start_y = config.STAT_ICON_START_Y_SCREEN
        icon_height = config.STAT_ICON_SIZE[1]
        icon_spacing = config.STAT_ICON_SPACING_Y

        for i, stat_name in enumerate(stats_to_draw_order):
            stat_value = state.pet_stats.get(stat_name, 0)
            stat_level = _get_stat_level(stat_value)
            icon_surface = _stat_icons.get((stat_name, stat_level))
            if icon_surface:
                icon_draw_y = icon_start_y + i * (icon_height + icon_spacing)
                screen.blit(icon_surface, (icon_start_x, icon_draw_y))


        # --- Draw Input Box Area Background and Border --- (always)
        pygame.draw.rect(screen, config.DARK_GREY, input_rect)


        # --- Draw Wrapped & Scrollable Chat History --- (always)
        # --- CHANGE 3: Update the chat history drawing code to use the improved wrap_text function ---
        # Calculate total height using the text_width_limit (with padding)
        total_history_height = calculate_total_history_height(state.chat_history, text_width_limit)
        max_scroll = max(0, total_history_height - history_display_area.height)
        state.scroll_y = max(0, min(state.scroll_y, max_scroll))  # Clamp state scroll_y

        # Current draw Y calculation with bottom-up drawing relative to history area's bottom
        # Adjusted by config.PADDING at the bottom of the history area itself
        current_draw_y = history_display_area.bottom - total_history_height + state.scroll_y - config.PADDING

        # Set clipping area for history display - make sure it's the right size
        history_clip_rect = history_display_area.copy()
        original_clip = screen.get_clip()
        screen.set_clip(history_clip_rect)

        for text, msg_type in state.chat_history:
            # Determine the prefix based on message type
            display_prefix = ""
            if msg_type == 'user':
                display_prefix = "You: "
                text_color = config.BLUE
            elif msg_type == 'bot':
                display_prefix = "Bot: "
                text_color = config.GREEN
            elif msg_type == 'error':
                display_prefix = "Error: "
                text_color = config.RED
            elif msg_type == 'system':
                display_prefix = "System: "
                text_color = config.YELLOW
            elif msg_type == 'system_instruction':
                display_prefix = "Instruction: "
                text_color = config.ORANGE
            else:
                text_color = config.BLUE  # Default

            # Wrap text considering the prefix for the first line
            # Use the global _text_width_limit which includes padding
            wrapped_lines = wrap_text(text, _text_width_limit, display_prefix)
            message_total_line_height = len(wrapped_lines) * _line_height

            # Draw each line of the current message
            for i, line in enumerate(wrapped_lines):
                line_draw_y = current_draw_y + i * _line_height

                # Only add prefix string to the first line.
                # Subsequent lines are just the wrapped content.
                # The wrapping function ensures the first line has room for the prefix,
                # and the drawing position handles the overall left padding.
                rendered_line_text = display_prefix + line if i == 0 else line

                # Apply proper left padding.
                # The x position starts at the history_display_area's left edge,
                # and we add the horizontal padding.
                left_pad = config.HISTORY_HORIZONTAL_PADDING
                try:
                    line_surface = _font.render(rendered_line_text, True, text_color)
                    screen.blit(line_surface, (history_display_area.left + left_pad, line_draw_y))
                except pygame.error as e:
                    print(f"Pygame error rendering history line '{rendered_line_text}': {e}")


            # Move the drawing position DOWN for the next message
            current_draw_y += message_total_line_height

        # Restore original clipping area after drawing history
        screen.set_clip(original_clip)


        # --- Draw Input Box Content (Handles Locked State) --- (always)
        input_border_color = config.ORANGE if is_input_locked else config.WHITE
        pygame.draw.rect(screen, input_border_color, input_rect, 1) # Draw border


        # Calculate the drawing area for the input text within the input_rect
        # This already includes padding thanks to how input_rect was defined in game.py based on panel_rect
        input_text_draw_area = pygame.Rect(
            input_rect.left + config.PADDING,
            input_rect.top + config.PADDING,
            input_rect.width - 2 * config.PADDING,
            input_rect.height - 2 * config.PADDING
        )

        # Set clipping for the input box text
        input_clip_rect = input_text_draw_area.copy()
        original_clip = screen.get_clip()
        screen.set_clip(input_clip_rect)

        display_text = ""
        text_color = config.LIGHT_GREY # Default text color for input

        # Use is_input_locked here to determine what to draw in the input box
        if is_input_locked:
            # Input is locked (either asleep or bot processing)
            display_text = "Waiting for bot..."
            # Use a greyed-out color
            try:
                text_surface = _font.render(display_text, True, config.GREY)
                # Center the "Waiting..." text in the input box
                text_x = input_text_draw_area.left + (input_text_draw_area.width - text_surface.get_width()) // 2
                text_y = input_text_draw_area.top + (input_text_draw_area.height - text_surface.get_height()) // 2
                screen.blit(text_surface, (text_x, text_y))
            except pygame.error as e:
                print(f"Pygame error rendering locked input text: {e}")

            state.cursor_visible = False # Ensure cursor is off when locked

        else:
            # Input is NOT locked, draw the user's text and cursor
            display_text = state.input_text
            input_text_width_limit = input_text_draw_area.width # Use the calculated inner width

            # Clip text if it's too long to fit (from the front)
            clipped_display_text = display_text
            try:
                text_width = _font.size(clipped_display_text)[0]
                while text_width > input_text_width_limit and len(clipped_display_text) > 0:
                    clipped_display_text = clipped_display_text[1:] # Remove character from the front
                    text_width = _font.size(clipped_display_text)[0]

                text_surface = _font.render(clipped_display_text, True, text_color)
                # Draw text aligned to the left within the padded area
                text_x = input_text_draw_area.left
                text_y = input_text_draw_area.top + (input_text_draw_area.height - text_surface.get_height()) // 2
                screen.blit(text_surface, (text_x, text_y))

                # Draw cursor only if visible and input is not locked
                if state.cursor_visible: # The check for is_input_locked is implicitly handled by the outer else block
                        cursor_pos_in_input_clipped = _font.size(clipped_display_text)[0]
                        # Cursor position is relative to the start of the drawn text
                        cursor_x = text_x + cursor_pos_in_input_clipped
                        cursor_y_start = text_y
                        cursor_y_end = text_y + text_surface.get_height()
                        # Clamp cursor x position just in case it goes slightly out
                        cursor_x = max(input_text_draw_area.left, min(cursor_x, input_text_draw_area.right - 1))
                        pygame.draw.line(screen, config.WHITE, (cursor_x, cursor_y_start), (cursor_x, cursor_y_end), 1)

            except pygame.error as e:
                print(f"Pygame error rendering user input or cursor: {e}")


        # Restore original clipping area after drawing input box content
        screen.set_clip(original_clip)


        # --- NEW: Draw Care Package Buttons and Scroll Controls --- (always)
        # Pass the is_input_locked flag
        draw_package_buttons(screen, is_input_locked)

        if not state.inventory_panel_visible:
            # Calculate current circle position
            current_circle_center_x = config.BASE_CIRCLE_CENTER_X
            current_circle_center_y = config.BASE_CIRCLE_CENTER_Y
            time_in_seconds = current_time_ms / 1000.0
            animation.update_animation_state(current_time_ms) # Update animation state variables
            animation_offset_x, animation_offset_y = animation.calculate_circle_offset(current_time_ms) # Calculate position based on state

            current_circle_center_x = config.BASE_CIRCLE_CENTER_X + animation_offset_x
            current_circle_center_y = config.BASE_CIRCLE_CENTER_Y + animation_offset_y

            # Draw the Circle (Ensure positions are integers)
            pygame.draw.circle(screen, config.BLACK, (int(current_circle_center_x), int(current_circle_center_y)), config.CIRCLE_RADIUS)
            # Example: Draw a border around the circle
            pygame.draw.circle(screen, config.GREEN, (int(current_circle_center_x), int(current_circle_center_y)), config.CIRCLE_RADIUS, 5)


    # --- Draw NEW Image Popup (This is OUTSIDE the conditional block) ---
    # Draw this on top of the background/dimming, regardless of initial phase
    if _image_popup_visible and _image_popup_image:
        current_time = pygame.time.get_ticks()
        elapsed_time = current_time - _image_popup_start_time
        remaining_time = (_image_popup_start_time + _image_popup_duration) - current_time

        alpha = 255
        if elapsed_time < _image_popup_fade_in_duration:
            if _image_popup_fade_in_duration > 0:
                 alpha = int((elapsed_time / _image_popup_fade_in_duration) * 255)
            else: alpha = 255
        elif remaining_time <= _image_popup_fade_out_duration:
            if _image_popup_fade_out_duration > 0:
                 alpha = int((remaining_time / _image_popup_fade_out_duration) * 255)
            else: alpha = 0
        alpha = max(0, min(255, alpha))

        _image_popup_image.set_alpha(alpha) # Apply alpha
        screen.blit(_image_popup_image, _image_popup_display_area.topleft) # Blit

        # Check if popup duration is over *in this frame*
        if elapsed_time >= _image_popup_duration:
            _image_popup_visible = False
            #print("Image popup duration ended.") # Debug


    # --- Draw Pop-up Messages --- (Draw these regardless of initial phase, or maybe only after?)
    # You'll need to decide if ephemeral popups should appear during the initial phase.
    # For now, let's assume they wait until the main GUI is visible.
    if not state.is_initial_popup_phase:
         draw_popups(screen)


    # --- Draw Inventory Panel (Conditional - Draws on top) ---
    # This should also be inside the conditional block, UNLESS you want the inventory
    # panel to be instantly available even during the initial popup phase.
    # Assuming you want it to appear *after* the initial phase:
    if not state.is_initial_popup_phase and state.inventory_panel_visible:
        draw_inventory_panel(screen)


    # --- Draw Inventory Toggle Button --- (Conditional?)
    # Do you want this button visible during the initial popup phase?
    # Probably not, unless it's the *only* thing besides the popup.
    # Let's put it inside the conditional block too.
    if not state.is_initial_popup_phase and _inventory_toggle_button_rect:
        pygame.draw.circle(screen, config.INVENTORY_BUTTON_COLOR, _inventory_toggle_button_rect.center, config.INVENTORY_TOGGLE_BUTTON_SIZE // 2)
        pygame.draw.circle(screen, config.WHITE, _inventory_toggle_button_rect.center, config.INVENTORY_TOGGLE_BUTTON_SIZE // 2, 1)


# --- Helper function to load and set background image (Moved) ---
# Kept this function here as it directly affects the GUI (drawing the background)
def load_and_set_background(image_path):
    """Loads an image and sets it as the background."""
    # Modifies state.background_image, which was already handled correctly with state. prefix
    # No 'global state.background_image' needed, just access/assign via state.

    print(f"Attempting to load background image: {image_path}")
    full_image_path = None
    try:
        # Add common image extensions if none provided
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
                 state.background_image = None # Fallback to solid color
                 return
            full_image_path = found_path
            print(f"Found image at: {full_image_path}")
        else:
             # Assume path includes directory and extension
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
        state.background_image = None # Fallback to solid color
    except Exception as e:
         print(f"An unexpected error occurred while loading background image '{full_image_path}': {e}")
         state.background_image = None


# Add a function to get button rects for game.py (Optional, but cleaner than global access)
def get_button_rects():
     """Returns a dictionary of button rects."""
     # Ensure gui.init_gui has been called
     if _inventory_toggle_button_rect is None:
         # print("Warning: get_button_rects called before gui.init_gui") # Avoid excessive logging
         return {}

     return {
         'inventory_toggle': _inventory_toggle_button_rect
         # Add other button rects here if you create more
     }

# Add a function to get panel rects for game.py (Needed for mouse wheel scroll area check)
def get_panel_rects():
     """Returns a dictionary of panel rects."""
     # Ensure gui.init_gui has been called
     if _inventory_panel_rect is None:
         # print("Warning: get_panel_rects called before gui.init_gui") # Avoid excessive logging
         return {}

     return {
         'inventory_panel': _inventory_panel_rect,
         'room_list_area': _room_list_area_rect, # Needed to check if mouse is over room list
         'player_list_area': _player_list_area_rect # Needed to check if mouse is over player list
     }