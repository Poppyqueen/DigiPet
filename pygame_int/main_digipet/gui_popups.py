#gui_popups.py

import pygame
import random

from .. import config
from .. import state
from . import gui_core # For _font, _gui_rects, etc.

# --- Popup Message Class (Text) ---
class PopupMessage:
    """Represents a single floating pop-up message."""
    def __init__(self, text_surface, initial_pos, start_time):
        # text_surface now includes the pre-rendered border
        self.text_surface = text_surface
        self.initial_pos = initial_pos   # Starting (x, y) tuple for the message
        self.start_time = start_time     # Milliseconds since the message started
        self.current_pos = list(initial_pos)   # Use a list so we can update it in place

# --- Image Popup Class ---
class ImagePopup:
    """Represents a single image popup."""
    def __init__(self, image_path, duration_ms, fade_in_ms, fade_out_ms, popup_type, screen_width, screen_height, panel_width):
        self.image_path = image_path
        self.duration = duration_ms
        self.fade_in_duration = max(0, fade_in_ms)
        self.fade_out_duration = max(0, fade_out_ms)
        self.type = popup_type
        self.visible = False
        self.image_surface = None
        self.display_area = None
        self.start_time = 0
        self.background_surface = None # Specific to this instance if type 0

        main_display_width = screen_width - panel_width

        if self.type == 0: # Main screen splash
            popup_size = (200, 200)
            self.display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
            self.display_area.center = (screen_width // 2, screen_height // 2)
            try:
                self.background_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                self.background_surface.fill((0, 0, 0, 128)) # Semi-transparent black
            except pygame.error as e:
                print(f"Warning: Could not create dimming background surface for popup type 0: {e}")
                self.background_surface = None
        elif self.type == 1: # Top right icon
            popup_size = (60, 60)
            self.display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
            self.display_area.topright = (main_display_width, 0)
        elif self.type == 2: # Icon on front of character
            popup_size = (150, 150)
            self.display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
            self.display_area.center = (main_display_width // 2, screen_height // 2)
        else: # Default (same as type 0 for positioning, but no default background)
            popup_size = (200, 200)
            self.display_area = pygame.Rect(0, 0, popup_size[0], popup_size[1])
            self.display_area.center = (screen_width // 2, screen_height // 2)

        if self.duration <= 0:
            print(f"Warning: duration_ms must be positive for image popup '{image_path}'. Not creating.")
            return # Will not be loaded or made visible

        try:
            raw_image = pygame.image.load(image_path)
            self.image_surface = pygame.transform.scale(raw_image, self.display_area.size).convert_alpha()
            self.visible = True
            self.start_time = pygame.time.get_ticks()
            print(f"Image popup '{image_path}' (Type: {self.type}) created. Duration: {self.duration}ms, FadeIn: {self.fade_in_duration}ms, FadeOut: {self.fade_out_duration}ms")
        except FileNotFoundError:
            print(f"Error loading image for popup: File not found at '{image_path}'")
        except pygame.error as e:
            print(f"Error loading or processing image for popup '{image_path}': {e}")
        except Exception as e:
            print(f"An unexpected error occurred while preparing image popup '{image_path}': {e}")


# Global dictionary to store active image popups, keyed by type
_active_image_popups = {} # Key: int (type), Value: ImagePopup instance


# --- Function to trigger a floating pop-up message ---
def show_popup_message(text, color=None, raw=False):
    """
    Creates a new floating pop-up message with a border and adds it to the active list.
    """
    border_color=(0,0,0)
    if not raw:
        if not color:
            color = state.game_theme_colors["contrast_color"]
        
        # Define border color and offset
        # Choose border color based on main text color for better contrast
        #border_color =  state.game_theme_colors["original_pet_color"] # Default black border
        border_color =  state.game_theme_colors.get("original_pet_color", (255,255,255)) 

    border_offset_px = 1 # 1 pixel offset for the border outline

    if gui_core._font is None:
         print("Error: show_popup_message called before gui_core._font is initialized.")
         return

    if not text or not text.strip():
         return

    try:
        # Render main text surface
        text_surface_main = gui_core._font.render(text.strip(), True, color)
        
        # Render border text surface
        text_surface_border = gui_core._font.render(text.strip(), True, border_color)

        # Calculate the size of the combined surface, adding space for the border
        combined_width = text_surface_main.get_width() + 2 * border_offset_px
        combined_height = text_surface_main.get_height() + 2 * border_offset_px
        
        # Create a new surface with SRCALPHA for transparency
        combined_text_surface = pygame.Surface((combined_width, combined_height), pygame.SRCALPHA)
        
        # Blit the border text at offset positions (8 directions for a full outline)
        offsets = [
            (-border_offset_px, -border_offset_px), (0, -border_offset_px), (border_offset_px, -border_offset_px),
            (-border_offset_px, 0),                                         (border_offset_px, 0),
            (-border_offset_px, border_offset_px), (0, border_offset_px), (border_offset_px, border_offset_px)
        ]
        
        for dx, dy in offsets:
            combined_text_surface.blit(text_surface_border, (border_offset_px + dx, border_offset_px + dy))
        
        # Blit the main text on top, centered within the border space
        combined_text_surface.blit(text_surface_main, (border_offset_px, border_offset_px))

    except pygame.error as e:
        print(f"Pygame error rendering popup text '{text}': {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred while preparing popup text '{text}': {e}")
        return

    # Calculate the initial position for the *combined* text surface.
    # We want the visual center/top of the *original* text to align as before.
    # The `combined_text_surface` is `2 * border_offset_px` wider and taller.
    
    # Horizontal centering: Center the entire combined surface.
    final_pos_x = config.get_base_circle_center_x(state.panel_width if state.panel_visible else 0) - combined_text_surface.get_width() // 2
    
    # Vertical positioning: Adjust so the top of the *main text* (after border) is at the original `POPUP_INITIAL_OFFSET_Y`.
    # This means the top of the `combined_text_surface` must be `border_offset_px` higher.
    final_pos_y = config.BASE_CIRCLE_CENTER_Y + config.POPUP_INITIAL_OFFSET_Y - border_offset_px

    # Apply random spread as before
    rand_offset_x = random.uniform(-config.POPUP_RANDOM_SPREAD_X, config.POPUP_RANDOM_SPREAD_X)
    rand_offset_y = random.uniform(-config.POPUP_RANDOM_SPREAD_Y, config.POPUP_RANDOM_SPREAD_Y)

    initial_x = final_pos_x + rand_offset_x
    initial_y = final_pos_y + rand_offset_y

    start_time = pygame.time.get_ticks()
    new_popup = PopupMessage(combined_text_surface, (initial_x, initial_y), start_time)
    state.active_popups.append(new_popup)

def is_any_image_popup_currently_active():
    """Checks if any image popup is currently active (visible and not expired)."""
    global _active_image_popups
    for popup in _active_image_popups.values():
        if popup.visible:
            current_time = pygame.time.get_ticks()
            elapsed_time = current_time - popup.start_time
            remaining_time = (popup.start_time + popup.duration) - current_time

            alpha = 255
            if popup.fade_in_duration > 0 and elapsed_time < popup.fade_in_duration:
                alpha = int((elapsed_time / popup.fade_in_duration) * 255)
            elif popup.fade_out_duration > 0 and remaining_time <= popup.fade_out_duration and remaining_time > 0:
                alpha = int((remaining_time / popup.fade_out_duration) * 255)
            elif remaining_time <= 0:
                alpha = 0

            if alpha > 0 : # Check if it would actually be drawn
                return True
    return False

# --- Image Popup Function ---
def show_image_popup(image_path, duration_ms=2000, fade_in_ms=500, fade_out_ms=500, popup_type=1): # Changed 'type' to 'popup_type'
    """
    Shows a temporary image popup. Manages its own state variables.
    Accesses gui_core._gui_rects.
    """
    global _active_image_popups

    current_surface = pygame.display.get_surface()
    if current_surface is None:
         print("Error: Pygame display not initialized. Cannot show image popup.")
         return

    screen_width = current_surface.get_width()
    screen_height = current_surface.get_height()
    
    panel_width = state.panel_width if state.panel_visible else 0


    new_image_popup = ImagePopup(
        image_path, duration_ms, fade_in_ms, fade_out_ms, popup_type,
        screen_width, screen_height, panel_width
    )

    if new_image_popup.visible: # Only add if successfully created and loaded
        _active_image_popups[popup_type] = new_image_popup
    else:
        print(f"Failed to create or load image popup for path: {image_path}, type: {popup_type}")


# --- Function to update the state of active pop-up messages ---
def update_popups(current_time_ms):
    """
    Updates active pop-up messages (text and image).
    Accesses state and config. Manages global image popup state.
    """
    global _active_image_popups

    # Iterate backwards for text popups for safe removal
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

    # Update image popups
    for popup_type in list(_active_image_popups.keys()):
        image_popup = _active_image_popups[popup_type]
        # Only set visible to False once the full duration has passed
        if image_popup.visible:
            if current_time_ms >= image_popup.start_time + image_popup.duration:
                image_popup.visible = False

# --- Function to draw active pop-up messages (text popups) ---

def clear_all_popups():
    """
    Clears all active pop-up messages (text and image).
    """
    state.active_popups.clear()
    global _active_image_popups
    _active_image_popups.clear()

def draw_popups(screen):
    """
    Draws all active text pop-up messages. Accesses state.
    """
    for popup in state.active_popups:
        if popup.text_surface.get_alpha() > 0: # Only draw if alpha is positive
            screen.blit(popup.text_surface, popup.current_pos)

# --- Function to draw the image popups if visible ---
def draw_active_image_popups(screen): # Renamed function
    """
    Draws all active and visible image popups.
    Manages their alpha based on fade durations.
    """
    global _active_image_popups
    current_time = pygame.time.get_ticks()

    # Draw type 0 (full screen splash) background first, if applicable
    if 0 in _active_image_popups:
        popup = _active_image_popups[0]
        # Ensure the background is only drawn when the type 0 popup is visible
        # AND when the initial popup phase flag is active, to prevent persistent dimming.
        if popup.visible and popup.background_surface and state.is_initial_popup_phase:
            screen.blit(popup.background_surface, (0, 0))


    for popup_type, popup in list(_active_image_popups.items()): # Iterate over copy to allow deletion if needed (though not currently implemented here)
        if popup.visible and popup.image_surface and popup.display_area:
            elapsed_time = current_time - popup.start_time
            remaining_time = (popup.start_time + popup.duration) - current_time

            alpha = 255
            # Fade-in phase
            if popup.fade_in_duration > 0 and elapsed_time < popup.fade_in_duration:
                alpha = int((elapsed_time / popup.fade_in_duration) * 255)
            # Fade-out phase: starts `fade_out_duration` before the end of the total duration
            elif popup.fade_out_duration > 0 and remaining_time <= popup.fade_out_duration and remaining_time > 0:
                alpha = int((remaining_time / popup.fade_out_duration) * 255)
            # If past the full duration, should be invisible
            elif remaining_time <= 0:
                alpha = 0 

            alpha = max(0, min(255, alpha)) # Clamp alpha between 0 and 255

            if alpha > 0: # Only blit if it's going to be visible
                popup.image_surface.set_alpha(alpha)
                screen.blit(popup.image_surface, popup.display_area.topleft)