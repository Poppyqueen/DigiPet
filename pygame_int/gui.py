# gui.py

from pygame_int import config
from pygame_int import state
from pygame_int import animation
# from pygame_int.colors_config import _color_selection_options # Removed
# from pygame_int import gui_config # Removed
from pygame_int import gui_core
from pygame_int import gui_text_utils
from pygame_int import gui_inventory
from pygame_int import gui_popups
from pygame_int import gui_care_package

import pygame
# import pygame.gfxdraw # Removed
import colorsys
# import os # Removed
# import random # Removed
# import math # Removed

# Comments about moved global variables and functions from previous steps are kept for clarity.
# PopupMessage class and popup-related functions (show_popup_message, show_image_popup, 
# update_popups, draw_popups) have been moved to pygame_int.gui_popups.

# Global variable to track which input box is active
# active_input_box = None # Moved to gui_color_selector.py

# --- Input Box State ---
# rgb_input_values = ["", "", ""] # Moved to gui_color_selector.py

# run_color_selection_ui function has been moved to pygame_int.gui_color_selector.py
# prepare_inventory_item_data and draw_item_list functions have been moved to pygame_int.gui_inventory.py
# draw_package_buttons and get_package_button_click_regions have been moved to pygame_int.gui_care_package


# --- Helper function to get stat level string ---
def _get_stat_level(value):
    """Determines the icon level ('full', 'half', 'empty') for a given stat value (0-200)."""
    clamped_value = max(0.0, min(200.0, value)) 

    if clamped_value >= config.STAT_THRESHOLDS['full']:
        return 'full'
    elif clamped_value >= config.STAT_THRESHOLDS['half']:
        return 'half'
    else:
        return 'empty'


def draw_filter_overlay(screen):
    """
    Draws a filter overlay on the screen from the theme colors.
    This overlay is semi-transparent and covers the entire screen.

    The color of this is created in set_color_theme() and is stored in state.game_theme_colors.
    Args:
        screen (pygame.Surface): The main display surface.
    """
    
    # Clear the overlay surface before drawing to ensure previous drawings don't persist
    gui_core.overlay_surface.fill((0, 0, 0, 0)) # Fill with transparent black

    # Draw the full-screen rectangle onto the overlay_surface with the calculated color and alpha
    pygame.draw.rect(gui_core.overlay_surface, state.game_theme_colors["overlay_color_with_alpha"], (0, 0, config.WIDTH, config.HEIGHT), 0)

    # Blit the overlay_surface onto the whole screen
    screen.blit(gui_core.overlay_surface, (0, 0))


# --- Function to draw the entire GUI panel ---
def draw_gui(screen, current_time_ms, is_input_locked):
    """
    Draws the background, panel, chat history, input box, stats,
    care package buttons, and conditionally the inventory panel.
    """
    # Update GUI rects based on the current panel_width from state
    gui_core.update_gui_rects(state.panel_width)

    # Retrieve potentially updated rects
    # _gui_rects in gui_core now holds the dynamic panel rects via get_gui_rects()
    current_gui_rects = gui_core.get_gui_rects() 

    if gui_core._font is None or gui_core._line_height == 0: # Removed check for gui_core._gui_rects as it's always populated now
         print("Error: draw_gui called before gui_core font/line_height are initialized.")
         return

    if not state.is_initial_popup_phase:
        if state.background_image:
            screen.blit(state.background_image, (0, 0)) # Background covers full screen
        else:
            screen.fill(config.fallback_bg_color)

        draw_filter_overlay(screen) # Assuming draw_filter_overlay is defined or imported

        # ------- draw pet ----------
        # Pet is centered in the game area (full width if panel hidden, game area if panel visible)
        current_circle_center_x = config.get_base_circle_center_x(state.panel_width if state.panel_visible else 0)
        current_circle_center_y = config.BASE_CIRCLE_CENTER_Y # Y position doesn't change with panel
        animation.update_animation_state(current_time_ms)
        animation_offset_x, animation_offset_y = animation.calculate_circle_offset(current_time_ms)

        current_circle_center_x += animation_offset_x
        current_circle_center_y += animation_offset_y

        pygame.draw.circle(screen, config.BLACK, (int(current_circle_center_x), int(current_circle_center_y)), state.current_radius)
        pygame.draw.circle(screen, state.pet_color, (int(current_circle_center_x), int(current_circle_center_y)), state.current_radius, 5)

        # --- Draw Stat Icons (always visible in the game area) ---
        stats_to_draw_order = ["fullness", "hydration", "energy"]
        icon_start_x = config.STAT_ICON_START_X_SCREEN
        icon_start_y = config.STAT_ICON_START_Y_SCREEN
        icon_height = config.STAT_ICON_SIZE[1]
        icon_spacing = config.STAT_ICON_SPACING_Y

        for i, stat_name in enumerate(stats_to_draw_order):
            stat_value = state.pet_stats.get(stat_name, 0)
            stat_level = _get_stat_level(stat_value) # Assuming _get_stat_level is defined or imported
            icon_surface = gui_core._stat_icons.get((stat_name, stat_level))
            if icon_surface:
                icon_draw_y = icon_start_y + i * (icon_height + icon_spacing)
                screen.blit(icon_surface, (icon_start_x, icon_draw_y))

        # --- Draw Panel related elements only if panel is visible ---
        if state.panel_visible:
            panel_rect = current_gui_rects['panel_rect']
            input_rect = current_gui_rects['input_rect']
            history_rect = current_gui_rects['history_rect']
            history_display_area = current_gui_rects['history_display_area']

            # Draw the panel and history area backgrounds
            pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], panel_rect)
            pygame.draw.rect(screen, state.game_theme_colors["contrast_color"], history_rect)

            # --- Draw Input Box Area Background and Border ---
            pygame.draw.rect(screen, state.game_theme_colors["contrast_color"], input_rect)

            # --- Draw Wrapped & Scrollable Chat History ---
            if history_display_area and history_display_area.height > 0: # Check if history_display_area is valid
                total_history_height = gui_text_utils.calculate_total_history_height(state.chat_history)
                max_scroll = max(0, total_history_height - history_display_area.height)
                state.scroll_y = max(0, min(state.scroll_y, max_scroll))
                current_content_top_y = history_display_area.bottom - total_history_height + state.scroll_y - config.PADDING

                history_clip_rect = history_display_area.copy()
                original_clip = screen.get_clip()
                screen.set_clip(history_clip_rect)

                message_draw_y = current_content_top_y
                for message_dict in state.chat_history:
                    msg_total_height = message_dict.get('total_height', 0)
                    rendered_surfaces = message_dict.get('rendered_surfaces', [])
                    msg_bottom_y = message_draw_y + msg_total_height
                    if msg_bottom_y < history_display_area.top or message_draw_y > history_display_area.bottom:
                        message_draw_y += msg_total_height
                        continue

                    line_draw_y = message_draw_y
                    for line_surface in rendered_surfaces:
                        if line_surface is None:
                            line_draw_y += gui_core._line_height
                            continue
                        line_bottom_y = line_draw_y + gui_core._line_height
                        if not (line_bottom_y < history_display_area.top or line_draw_y > history_display_area.bottom):
                            blit_x = history_display_area.left + config.HISTORY_HORIZONTAL_PADDING
                            screen.blit(line_surface, (blit_x, line_draw_y))
                        line_draw_y += gui_core._line_height
                    message_draw_y += msg_total_height
                screen.set_clip(original_clip)

            # --- Draw Input Box Content ---
            if input_rect: # Check if input_rect is valid
                input_text_draw_area = pygame.Rect(
                    input_rect.left + config.PADDING,
                    input_rect.top + config.PADDING,
                    input_rect.width - 2 * config.PADDING,
                    input_rect.height - 2 * config.PADDING
                )
                input_clip_rect = input_text_draw_area.copy()
                original_clip = screen.get_clip()
                screen.set_clip(input_clip_rect)

                text_color = state.game_theme_colors["user_message_color"]
                if is_input_locked:
                    display_text = "Waiting for bot..."
                    try:
                        text_surface = gui_core._font.render(display_text, True, config.GREY)
                        text_x = input_text_draw_area.left + (input_text_draw_area.width - text_surface.get_width()) // 2
                        text_y = input_text_draw_area.top + (input_text_draw_area.height - text_surface.get_height()) // 2
                        screen.blit(text_surface, (text_x, text_y))
                    except pygame.error as e:
                        print(f"Pygame error rendering locked input text: {e}")
                    state.cursor_visible = False
                else:
                    display_text = state.input_text
                    input_text_width_limit = input_text_draw_area.width
                    clipped_display_text = display_text
                    try:
                        text_width = gui_core._font.size(clipped_display_text)[0]
                        while text_width > input_text_width_limit and len(clipped_display_text) > 0:
                            clipped_display_text = clipped_display_text[1:]
                            text_width = gui_core._font.size(clipped_display_text)[0]
                        text_surface = gui_core._font.render(clipped_display_text, True, text_color)
                        text_x = input_text_draw_area.left
                        text_y = input_text_draw_area.top + (input_text_draw_area.height - text_surface.get_height()) // 2
                        screen.blit(text_surface, (text_x, text_y))

                        if state.cursor_visible:
                                cursor_pos_in_input_clipped = gui_core._font.size(clipped_display_text)[0]
                                cursor_x = text_x + cursor_pos_in_input_clipped
                                cursor_y_start = text_y
                                cursor_y_end = text_y + text_surface.get_height()
                                cursor_x = max(input_text_draw_area.left, min(cursor_x, input_text_draw_area.right - 1))
                                pygame.draw.line(screen, config.WHITE, (cursor_x, cursor_y_start), (cursor_x, cursor_y_end), 1)
                    except pygame.error as e:
                        print(f"Pygame error rendering user input or cursor: {e}")
                screen.set_clip(original_clip)
                pygame.draw.rect(screen, config.GREY, input_rect, 1) # Border for input box

        # --- Care Package buttons are drawn outside the panel visibility check for now ---
        # Their positioning might need to be adjusted based on panel visibility in gui_care_package.py
        gui_care_package.draw_package_buttons(screen, is_input_locked)

    # Popups and inventory are drawn on top of everything, managed by their own visibility flags
    gui_popups.draw_active_image_popups(screen)

    if not state.is_initial_popup_phase:
         gui_popups.draw_popups(screen)

    if not state.is_initial_popup_phase and state.inventory_panel_visible:
        gui_inventory.draw_inventory_panel(screen)

    if not state.is_initial_popup_phase and gui_core._inventory_toggle_button_rect:
        pygame.draw.circle(screen, config.INVENTORY_BUTTON_COLOR, gui_core._inventory_toggle_button_rect.center, config.INVENTORY_TOGGLE_BUTTON_SIZE // 2)
        pygame.draw.circle(screen, state.game_theme_colors["contrast_color"], gui_core._inventory_toggle_button_rect.center, config.INVENTORY_TOGGLE_BUTTON_SIZE // 2, 1)


    # --- NEW: Draw Mute Button ---
    if not state.is_initial_popup_phase and gui_core._mute_button_rect:
        button_rect = gui_core._mute_button_rect
        button_color = state.game_theme_colors["original_pet_color"] if state.is_muted else config.MUTE_BUTTON_UNMUTED_COLOR
        border_color = config.MUTE_BUTTON_BORDER_COLOR

        pygame.draw.circle(screen, button_color, button_rect.center, button_rect.width // 2)
        pygame.draw.circle(screen, border_color, button_rect.center, button_rect.width // 2, 1)

        # Draw a simple speaker icon (or speaker with a cross if muted)
        icon_color = config.WHITE if state.is_muted else config.BLACK # Icon color changes based on mute state

        # Speaker body
        speaker_width = button_rect.width // 4
        speaker_height = button_rect.height // 3
        speaker_x = button_rect.centerx - speaker_width // 2 - button_rect.width // 8
        speaker_y = button_rect.centery - speaker_height // 2
        pygame.draw.rect(screen, icon_color, (speaker_x, speaker_y, speaker_width, speaker_height))

        # Speaker "horn" (triangle)
        horn_points = [
            (speaker_x + speaker_width, speaker_y),
            (speaker_x + speaker_width + speaker_width // 2, button_rect.centery),
            (speaker_x + speaker_width, speaker_y + speaker_height)
        ]
        pygame.draw.polygon(screen, icon_color, horn_points)

        if state.is_muted:
            # Draw a diagonal line through the speaker
            line_start = (button_rect.left + button_rect.width // 4, button_rect.top + button_rect.height // 4)
            line_end = (button_rect.right - button_rect.width // 4, button_rect.bottom - button_rect.height // 4)
            pygame.draw.line(screen, icon_color, line_start, line_end, 2)


    if not state.is_initial_popup_phase:
        # --- Draw Panel Toggle Button ---
        if not state.is_initial_popup_phase and gui_core._panel_toggle_button_rect:
            button_rect = gui_core._panel_toggle_button_rect
            pygame.draw.rect(screen, config.PANEL_TOGGLE_BUTTON_COLOR, button_rect)

            arrow_char = ">" if state.panel_visible else "<"
            try:
                arrow_surface = gui_core._font.render(arrow_char, True, config.WHITE)
                arrow_rect = arrow_surface.get_rect(center=button_rect.center)
                screen.blit(arrow_surface, arrow_rect)
            except pygame.error as e:
                print(f"Pygame error rendering panel toggle arrow: {e}")


        screen_width = screen.get_width()
        screen_height = screen.get_height()
        border_rect = pygame.Rect(0, 0, screen_width, screen_height)
        pygame.draw.rect(screen, state.pet_color, border_rect, config.PADDING)
