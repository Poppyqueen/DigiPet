#gui_popups.py

import pygame
import random
import os
from pygame_int import config
from pygame_int import state
from pygame_int import gui_core # For _font, _gui_rects, etc.

# --- Popup Message Class (Text) ---
class PopupMessage:
    """Represents a single floating pop-up message."""
    def __init__(self, text_surface, initial_pos, start_time):
        self.text_surface = text_surface # Pygame surface of the rendered text
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
def show_popup_message(text, color=None):
    """
    Creates a new floating pop-up message and adds it to the active list.
    """
    if not color:
        color = state.pet_color

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

    base_x = config.get_base_circle_center_x(state.panel_width if state.panel_visible else 0) - text_surface.get_width() // 2
    base_y = config.BASE_CIRCLE_CENTER_Y + config.POPUP_INITIAL_OFFSET_Y

    rand_offset_x = random.uniform(-config.POPUP_RANDOM_SPREAD_X, config.POPUP_RANDOM_SPREAD_X)
    rand_offset_y = random.uniform(-config.POPUP_RANDOM_SPREAD_Y, config.POPUP_RANDOM_SPREAD_Y)

    initial_x = base_x + rand_offset_x
    initial_y = base_y + rand_offset_y

    start_time = pygame.time.get_ticks()
    new_popup = PopupMessage(text_surface, (initial_x, initial_y), start_time)
    state.active_popups.append(new_popup)

# Add this function to your popups module (gui_popups.py)

def is_any_image_popup_currently_active():
    """Checks if any image popup is currently active (visible and not expired)."""
    global _active_image_popups
    for popup in _active_image_popups.values():
        if popup.visible:
            # You might also want to check if it's actually drawing (alpha > 0)
            # For that, you'd need the current time to calculate alpha,
            # but popup.visible generally means it's "supposed to be shown or fading".
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
    # Iterate over a list of keys to allow modification of the dictionary
    for popup_type in list(_active_image_popups.keys()):
        image_popup = _active_image_popups[popup_type]
        if image_popup.visible:
            if current_time_ms >= image_popup.start_time + image_popup.duration:
                image_popup.visible = False # Mark as not visible
                # Optionally, remove from dictionary if no longer needed
                # print(f"Image popup type {image_popup.type} duration ended.")
        # If not visible and we want to clean up, we could remove it here:
        # if not image_popup.visible:
        #     del _active_image_popups[popup_type]
        # However, keeping it until replaced or explicitly cleared might be simpler for fade-out logic.
        # The current drawing function handles non-visible popups correctly by not drawing them.
        # If fade-out is entirely handled by alpha calculation during draw,
        # then just setting visible = False when duration is over is enough.
        # The drawing function will show 0 alpha if past duration + fade_out.

# --- Function to draw active pop-up messages (text popups) ---
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

    # Sort by type to control draw order if necessary (e.g., type 0 background first)
    # For now, dictionary iteration order is generally fine for a few items.
    # If specific layering is critical (e.g. type 0 always behind others),
    # you might draw type 0 first, then others.

    # Optional: Draw type 0 first if it has a background
    if 0 in _active_image_popups:
        popup = _active_image_popups[0]
        if popup.visible and popup.background_surface and state.is_initial_popup_phase:
            # Alpha for background dimming itself is not currently time-based, it's fixed.
            # If fade-in/out should apply to the dimming, that's an additional logic layer.
            # For now, assuming the background_surface has its own alpha set at creation.
            screen.blit(popup.background_surface, (0, 0))


    for popup_type, popup in _active_image_popups.items():
        if popup.visible and popup.image_surface and popup.display_area:
            elapsed_time = current_time - popup.start_time
            # remaining_time relative to this specific popup's life
            remaining_time = (popup.start_time + popup.duration) - current_time

            alpha = 255
            # Fade-in phase
            if popup.fade_in_duration > 0 and elapsed_time < popup.fade_in_duration:
                alpha = int((elapsed_time / popup.fade_in_duration) * 255)
            # Fade-out phase: only if fade_out_duration is set AND we are within that window before the *actual* end
            # The end of visibility is start_time + duration.
            # Fade out starts at (start_time + duration - fade_out_duration).
            elif popup.fade_out_duration > 0 and remaining_time <= popup.fade_out_duration and remaining_time > 0:
                alpha = int((remaining_time / popup.fade_out_duration) * 255)
            # If past the full duration (including any implicit fade-out time if fade_out_duration is 0)
            elif remaining_time <= 0:
                alpha = 0 # Should be invisible

            alpha = max(0, min(255, alpha)) # Clamp alpha

            if alpha > 0: # Only blit if it's going to be visible
                popup.image_surface.set_alpha(alpha)
                screen.blit(popup.image_surface, popup.display_area.topleft)
        elif not popup.visible and popup_type in _active_image_popups and (current_time > popup.start_time + popup.duration):
            # Optional: Clean up popups that have fully expired and are no longer visible
            # This check is a bit redundant if update_popups simply marks them not visible
            # and we don't need to reclaim memory aggressively.
            # If we were to clean up:
            # del _active_image_popups[popup_type] # This would need list(_active_image_popups.keys()) for iteration
            pass