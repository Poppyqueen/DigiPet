# gui_clock.py

# The sleep duration clock is not currently implemented. It is a placeholder for future functionality.

import pygame

from .. import state
from .. import config
from . import gui_core
from ...utils.loc_datetime import datetime
from datetime import timedelta


# Threshold to decide if we are in "window shade" mode
COLLAPSE_HEIGHT_THRESHOLD = 20 

def handle_clock_click(mouse_pos):
    """
    Checks if the clock areas were clicked to toggle the 'clock_expanded' state.
    """
    if not hasattr(state, 'clock_expanded'):
        state.clock_expanded = True

    clicked = False

    if gui_core._current_time_clock_rect and gui_core._current_time_clock_rect.collidepoint(mouse_pos):
        clicked = True
        
    elif (state.agent_sleeping and 
          gui_core._sleep_duration_clock_rect and 
          gui_core._sleep_duration_clock_rect.collidepoint(mouse_pos)):
        clicked = True
        
    if clicked:
        state.clock_expanded = not state.clock_expanded
        
        # Force a GUI layout update immediately
        current_panel_w = gui_core._panel_rect.width if state.panel_visible else 0
        gui_core.update_gui_rects(current_panel_w)
        return True
        
    return False


def draw_current_time(screen):
    """
    Draws the current time. 
    Restores the dynamic width calculation so it doesn't overlap the Info button.
    """
    # 1. Access the Layout Container
    container_rect = gui_core._current_time_clock_rect
    if container_rect is None or gui_core._font is None: return

    try:
        # 2. Determine State
        is_collapsed = container_rect.height < COLLAPSE_HEIGHT_THRESHOLD
        
        # 3. Prepare Data
        now = datetime.now()
        time_str = now.strftime("%I:%M %p") 
        
        # Colors
        foreground_color = state.game_theme_colors.get("original_pet_color", (255, 255, 255))
        background_color = state.game_theme_colors.get("contrast_color", (0, 0, 0))


        text_surface = gui_core._font.render(time_str, True, foreground_color)
        padding_x = 20 
        
        button_width = text_surface.get_width() + padding_x
        
        button_rect = pygame.Rect(0, 0, button_width, container_rect.height)
        
        button_rect.right = container_rect.right
        button_rect.centery = container_rect.centery

        border_thickness = 2
        border_rect = button_rect.inflate(border_thickness * 2, border_thickness * 2)
        border_rect = border_rect.clip(screen.get_rect()) 
        
        pygame.draw.rect(screen, foreground_color, border_rect)

        pygame.draw.rect(screen, background_color, button_rect)

        if is_collapsed:
            # Draw "Grip" (Small bar)
            grip_rect = pygame.Rect(0, 0, 20, 2)
            grip_rect.center = button_rect.center
            pygame.draw.rect(screen, foreground_color, grip_rect)
        else:
            # Draw Text
            text_rect = text_surface.get_rect(center=button_rect.center)
            screen.blit(text_surface, text_rect)
        
    except pygame.error as e:
        print(f"Pygame error rendering current time: {e}")


def draw_sleep_duration(screen):
    """
    Draws the sleep duration using dynamic width.
    """
    if not state.agent_sleeping: return

    if state.time_to_sleep is None:
        print("No time_to_sleep found. Not drawing sleep duration.")
        return
    
    # Countdown logic
    current_time = pygame.time.get_ticks()
    
    # Initialize static variable for last tick if it doesn't exist
    if not hasattr(draw_sleep_duration, "last_tick"):
        draw_sleep_duration.last_tick = current_time
        
    # Check if a second has passed
    if current_time - draw_sleep_duration.last_tick >= 1000:
        state.time_to_sleep -= 1
        draw_sleep_duration.last_tick = current_time
        # print(f"Sleep countdown: {state.time_to_sleep}")


    container_rect = gui_core._sleep_duration_clock_rect
    if container_rect is None or gui_core._font is None: return

    try:
        is_collapsed = container_rect.height < COLLAPSE_HEIGHT_THRESHOLD

        sleep_str = f"Sleep: {str(timedelta(seconds=int(state.time_to_sleep)))}"        
        foreground_color = state.game_theme_colors.get("original_pet_color", (255, 255, 255))
        background_color = state.game_theme_colors.get("contrast_color", (0, 0, 0))

        # Calculate Width
        text_surface = gui_core._font.render(sleep_str, True, foreground_color)
        padding_x = 20
        button_width = text_surface.get_width() + padding_x
        
        # Content
        if not is_collapsed:
            # Visual Rect
            button_rect = pygame.Rect(0, 0, button_width, container_rect.height)
            button_rect.right = container_rect.right
            button_rect.centery = container_rect.centery

            # Border
            border_thickness = 2
            border_rect = button_rect.inflate(border_thickness * 2, border_thickness * 2)
            pygame.draw.rect(screen, foreground_color, border_rect)

            # Background
            pygame.draw.rect(screen, background_color, button_rect)

            text_rect = text_surface.get_rect(center=button_rect.center)
            screen.blit(text_surface, text_rect)

    except pygame.error as e:
        print(f"Pygame error rendering sleep duration: {e}")