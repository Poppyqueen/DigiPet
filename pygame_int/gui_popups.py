import pygame
import random
import os
from pygame_int import config
from pygame_int import state
from pygame_int import gui_core # For _font, _gui_rects, etc.

# Global state variables related to image popups
_image_popup_visible = False
_image_popup_image = None
_image_popup_start_time = 0
_image_popup_duration = 0
_image_popup_background_surface = None # Initialized in show_image_popup
_image_popup_display_area = None # Initialized in show_image_popup
_image_popup_fade_in_duration = 0
_image_popup_fade_out_duration = 0

# --- Popup Message Class ---
class PopupMessage:
    """Represents a single floating pop-up message."""
    def __init__(self, text_surface, initial_pos, start_time):
        self.text_surface = text_surface # Pygame surface of the rendered text
        self.initial_pos = initial_pos   # Starting (x, y) tuple for the message
        self.start_time = start_time     # Milliseconds since the message started
        self.current_pos = list(initial_pos)   # Use a list so we can update it in place

# --- Function to trigger a floating pop-up message ---
def show_popup_message(text, color=None):
    """
    Creates a new floating pop-up message and adds it to the active list.
    The message appears centered horizontally above the character's base
    position with a slight random spread, moves up, and fades out.
    Uses gui_core._font. Accesses config and state.
    """
    if not color:
        color=state.pet_color

    # print(f"trying to show popup with color: {color}") # Debug
    if gui_core._font is None: 
         print("Error: show_popup_message called before gui_core._font is initialized.")
         return 

    if not text or not text.strip():
         return 

    try:
        text_surface = gui_core._font.render(text.strip(), True, color) 
    except pygame.error as e:
        print(f"Pygame error rendering popup text '{text}': {e}")
        return 

    base_x = config.BASE_CIRCLE_CENTER_X - text_surface.get_width() // 2
    base_y = config.BASE_CIRCLE_CENTER_Y + config.POPUP_INITIAL_OFFSET_Y

    rand_offset_x = random.uniform(-config.POPUP_RANDOM_SPREAD_X, config.POPUP_RANDOM_SPREAD_X)
    rand_offset_y = random.uniform(-config.POPUP_RANDOM_SPREAD_Y, config.POPUP_RANDOM_SPREAD_Y)

    initial_x = base_x + rand_offset_x
    initial_y = base_y + rand_offset_y

    start_time = pygame.time.get_ticks()
    new_popup = PopupMessage(text_surface, (initial_x, initial_y), start_time)
    state.active_popups.append(new_popup)

# --- Image Popup Function ---
def show_image_popup(image_path, duration_ms=2000, fade_in_ms=500, fade_out_ms=500, type=1):
    """
    Shows a temporary image popup. Manages its own state variables.
    Accesses gui_core._gui_rects. Initializes _image_popup_display_area and _image_popup_background_surface.
    """
    global _image_popup_visible, _image_popup_image, _image_popup_start_time, _image_popup_duration
    global _image_popup_fade_in_duration, _image_popup_fade_out_duration
    global _image_popup_background_surface, _image_popup_display_area

    if pygame.display.get_surface() is None:
         print("Error: Pygame display not initialized. Cannot show image popup.")
         return

    screen_width = pygame.display.get_surface().get_width()
    screen_height = pygame.display.get_surface().get_height()
    panel_width = gui_core._gui_rects.get('panel_rect', pygame.Rect(0,0,0,0)).width
    main_display_width = screen_width - panel_width

    if type == 0: # Main screen splash
        popup_size = (200, 200)
        _image_popup_display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
        _image_popup_display_area.center = (screen_width // 2, screen_height // 2)
        # Initialize background dimming surface for splash
        if _image_popup_background_surface is None :
            try:
                _image_popup_background_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                _image_popup_background_surface.fill((0, 0, 0, 128)) # Semi-transparent black
            except pygame.error as e:
                print(f"Warning: Could not create dimming background surface: {e}")
                _image_popup_background_surface = None # Ensure it's None if creation fails
    elif type == 1: # Top right icon
        popup_size = (60, 60)
        _image_popup_display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
        _image_popup_display_area.topright = (main_display_width, 0)
    elif type == 2: # Icon on front of character
        popup_size = (150, 150)
        _image_popup_display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
        _image_popup_display_area.center = (main_display_width // 2, screen_height // 2)
    else: # Default
        popup_size = (200, 200) 
        _image_popup_display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
        _image_popup_display_area.center = (screen_width // 2, screen_height // 2)

    if duration_ms <= 0:
        print("Warning: duration_ms must be positive for image popup.")
        return
    _image_popup_fade_in_duration = max(0, fade_in_ms)
    _image_popup_fade_out_duration = max(0, fade_out_ms)

    try:
        raw_image = pygame.image.load(image_path)
        _image_popup_image = pygame.transform.scale(raw_image, _image_popup_display_area.size).convert_alpha()
        _image_popup_visible = True
        _image_popup_start_time = pygame.time.get_ticks()
        _image_popup_duration = duration_ms
        print(f"Attempting to show image popup: {image_path} (Total: {duration_ms}ms, FadeIn: {_image_popup_fade_in_duration}ms, FadeOut: {_image_popup_fade_out_duration}ms)") # Debug
    except FileNotFoundError:
        print(f"Error loading image for popup: File not found at '{image_path}'")
        _image_popup_visible = False
        _image_popup_image = None
    except pygame.error as e:
        print(f"Error loading or processing image for popup '{image_path}': {e}")
        _image_popup_visible = False
        _image_popup_image = None
    except Exception as e:
        print(f"An unexpected error occurred while preparing image popup '{image_path}': {e}")
        _image_popup_visible = False
        _image_popup_image = None

# --- Function to update the state of active pop-up messages ---
def update_popups(current_time_ms):
    """
    Updates active pop-up messages (text and image).
    Accesses state and config. Manages global image popup state.
    """
    global _image_popup_visible # This is needed as we are modifying it

    # Iterate backwards for text popups
    for i in range(len(state.active_popups) - 1, -1, -1):
        popup = state.active_popups[i]
        elapsed_time = current_time_ms - popup.start_time
        progress = min(1.0, elapsed_time / config.POPUP_DURATION_MS) 

        if progress >= 1.0:
            state.active_popups.pop(i) 
            continue 

        popup.current_pos[1] = popup.initial_pos[1] - progress * config.POPUP_MOVE_DISTANCE_Y
        alpha = 255 * (1.0 - progress)
        popup.text_surface.set_alpha(int(alpha))

    # Update image popup visibility
    if _image_popup_visible:
        if current_time_ms >= _image_popup_start_time + _image_popup_duration:
            _image_popup_visible = False
            # print("Image popup duration ended.") # Debug

# --- Function to draw active pop-up messages (text popups) ---
def draw_popups(screen):
    """
    Draws all active text pop-up messages. Accesses state.
    """
    for popup in state.active_popups:
        if popup.text_surface.get_alpha() > 0:
            screen.blit(popup.text_surface, popup.current_pos)

# --- Function to draw the image popup if visible (background and image) ---
def draw_image_popup_if_visible(screen):
    """
    Draws the image popup (background dimming and image) if it's currently visible.
    Manages its own alpha based on fade durations.
    """
    global _image_popup_visible, _image_popup_image, _image_popup_start_time, _image_popup_duration
    global _image_popup_fade_in_duration, _image_popup_fade_out_duration, _image_popup_display_area
    global _image_popup_background_surface

    if _image_popup_visible:
        # Draw dimming background first, only if it exists (it might not for non-type 0 popups if not explicitly created)
        if _image_popup_background_surface and state.is_initial_popup_phase: 
            screen.blit(_image_popup_background_surface, (0, 0))
        
        if _image_popup_image and _image_popup_display_area:
            current_time = pygame.time.get_ticks()
            elapsed_time = current_time - _image_popup_start_time
            # Calculate remaining time based on the popup's own duration, not total game time
            remaining_time = (_image_popup_start_time + _image_popup_duration) - current_time


            alpha = 255
            if _image_popup_fade_in_duration > 0 and elapsed_time < _image_popup_fade_in_duration:
                alpha = int((elapsed_time / _image_popup_fade_in_duration) * 255)
            # Check fade-out condition based on remaining time relative to the popup's own lifecycle
            elif _image_popup_fade_out_duration > 0 and remaining_time <= _image_popup_fade_out_duration and remaining_time > 0 : # ensure remaining_time is positive
                alpha = int((remaining_time / _image_popup_fade_out_duration) * 255)
            elif remaining_time <=0: # If time is up and not covered by fade out (e.g. fade_out_duration is 0)
                alpha = 0 # Should be invisible
            
            alpha = max(0, min(255, alpha))
            _image_popup_image.set_alpha(alpha)
            screen.blit(_image_popup_image, _image_popup_display_area.topleft)
