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


def set_color_theme():
    """
    Based on the initial pet color this function creates a color theme for the game.

    The theme includes:
        A dictionary of various colors:
            - Original pet color
            - Original color adjusted to target brightness (no alpha)
            - Overlay color with alpha (for drawing the filter)
            - New contrast color (desaturated with tint)
            - Inverted color (for system messages)
            - Black or white (for user messages)
            - Error color (red unless the pet color is red, if so, use green)
            - Dynamic package colors (hydration, fullness, misc, ingredient, combo, cheat)
    """

    # --- Configuration ---
    # Define this value as your desired absolute brightness level (0.0 to 1.0)
    
    # ---- Draw filter overlay above the background image ----
    # Define the alpha value for the overlay (0-255, where 255 is opaque)
    alpha_value = 80
    
    # Convert RGB to HSV for brightness adjustment
    # Normalize RGB to 0-1 range for colorsys
    #print(f"--- Original Pet Color: {state.pet_color} ---")
    r, g, b = [x / 255.0 for x in state.pet_color]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    #print(f"Original RGB (normalized): ({r:.2f}, {g:.2f}, {b:.2f})")
#print(f"Original HSV (normalized): H={h:.2f}, S={s:.2f}, V={v:.2f}")


    # Apply absolute brightness target for the overlay color
    # Set the brightness component directly to the target
    v_adjusted = config.TARGET_BRIGHTNESS 
    
    # Convert back to RGB and denormalize to 0-255 range for Pygame
    adjusted_r, adjusted_g, adjusted_b = [int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v_adjusted)]
    
    state.pets_theme_color = (adjusted_r, adjusted_g, adjusted_b)
    overlay_color_with_alpha = (adjusted_r, adjusted_g, adjusted_b, alpha_value)

    # --- Generate Better Contrast Color & Determine Dynamic Color Targets ---
    # These decisions will influence contrast_color, user_message_color, system_messages,
    # error_color, AND the new package colors.
    if v < 0.60: # If the original color is dark (low brightness)
        #print(f"Original color is dark (V={v:.2f} < 0.6). Aiming for LIGHT contrast elements.")
        contrast_v = 0.85  # Push brightness very high (close to white)
        contrast_s = 0.15  # Reduce saturation significantly (almost grayscale tint)
        user_message_color = (0, 0, 0) # Black for user messages
        
        # When original is dark, contrast_color is light.
        # System messages should be dark.
        inverted_target_v = 0.25 # Target brightness for system messages (dark)
        inverted_target_s = 0.50 # Moderate saturation for system messages

        # Error color: If contrast_color is LIGHT, error_color should be DARK.
        error_target_v = 0.35 # Darker error color
        error_target_s = 0.90 # High saturation

        # Package colors: If contrast_color is LIGHT, package colors should be DARK.
        package_target_v = 0.40 # Medium-dark brightness for package colors
        package_target_s = 0.85 # High saturation for package colors
        combo_target_v = 0.05 # Very dark for combo (closer to black)

    else: # If the original color is light (high brightness)
        #print(f"Original color is light (V={v:.2f} >= 0.6). Aiming for DARK contrast elements.")
        contrast_v = 0.15  # Push brightness very low (close to black)
        contrast_s = 0.45  # Reduce saturation significantly (almost grayscale tint)
        user_message_color = (255, 255, 255) # White for user messages

        # When original is light, contrast_color is dark.
        # System messages should be light.
        inverted_target_v = 0.75 # Target brightness for system messages (light)
        inverted_target_s = 0.50 # Moderate saturation for system messages

        # Error color: If contrast_color is DARK, error_color should be LIGHT.
        error_target_v = 0.85 # Lighter error color
        error_target_s = 0.90 # High saturation

        # Package colors: If contrast_color is DARK, package colors should be LIGHT.
        package_target_v = 0.60 # Medium-light brightness for package colors
        package_target_s = 0.85 # High saturation for package colors
        combo_target_v = 0.15 # Still dark for combo, but slightly lighter than pure black to stand out from background


    def invert_hsv_for_messages(h_in, inverted_target_s, inverted_target_v):
        """
        Calculates an 'inverted' HSV color where hue is inverted,
        and saturation/value are set based on desired contrast for messages.
        """
        # print(f"\n--- Inside invert_hsv_for_messages function ---")
        # print(f"  Input Hue: H={h_in:.2f}")
        # print(f"  Target Saturation: {inverted_target_s:.2f}")
        # print(f"  Target Value: {inverted_target_v:.2f}")

        inverted_h = (h_in + 0.5) % 1.0
        inverted_s = inverted_target_s
        inverted_v = inverted_target_v
        
        # print(f"  Final Inverted HSV for messages: H={inverted_h:.2f}, S={inverted_s:.2f}, V={inverted_v:.2f}")
        # print(f"--- End invert_hsv_for_messages function ---")
        
        return inverted_h, inverted_s, inverted_v
    
    # Calculate System Messages Color
    hsv_tuple_normalized = (h, s, v)
    i_h, i_s, i_v = invert_hsv_for_messages(h, inverted_target_s, inverted_target_v)
    inverted_r_norm, inverted_g_norm, inverted_b_norm = colorsys.hsv_to_rgb(i_h, i_s, i_v)
    inverted_color = (int(inverted_r_norm * 255), int(inverted_g_norm * 255), int(inverted_b_norm * 255))
    #print(f"  Calculated System Message Color: {inverted_color}")
    
    # Calculate Contrast Color
    contrast_r, contrast_g, contrast_b = [int(x * 255) for x in colorsys.hsv_to_rgb(h, contrast_s, contrast_v)]
    contrast_color = (contrast_r, contrast_g, contrast_b)
    #print(f"  Calculated Contrast Color: {contrast_color}")


    def is_red(h_norm, s_norm, v_norm):
        """
        Checks if a color (in normalized HSV) is predominantly red.
        Adjusted for 0.0-1.0 HSV range.
        """
        is_red_hue = (h_norm >= 350/360.0 or h_norm <= 10/360.0)
        is_saturated = s_norm > 0.15
        is_bright_enough = v_norm > 0.1

        return is_red_hue and is_saturated and is_bright_enough

    # --- Calculate Error Color ---
    #print("\n--- Calculating Error Color ---")
    if is_red(h, s, v):
        error_hue = 120 / 360.0 # Pure green hue
        #print(f"  Original pet is RED. Error hue set to GREEN (H={error_hue:.2f})")
    else:
        error_hue = 0 / 360.0 # Pure red hue
        #print(f"  Original pet is NOT RED. Error hue set to RED (H={error_hue:.2f})")

    error_r_norm, error_g_norm, error_b_norm = colorsys.hsv_to_rgb(error_hue, error_target_s, error_target_v)
    error_color = (int(error_r_norm * 255), int(error_g_norm * 255), int(error_b_norm * 255))
    #print(f"  Calculated Error Color: {error_color}")

    # --- Calculate Dynamic Package Colors ---
    #print("\n--- Calculating Dynamic Package Colors ---")
    dynamic_package_colors = {}
    
    # Define base hues for each package type
    package_hues = {
        "hydration": 220 / 360.0, # A standard blue
        "fullness": 0 / 360.0,    # Red
        "misc": 280 / 360.0,      # Purple (slightly more magenta than pure purple)
        "ingredient": 35 / 360.0, # Orange (closer to yellow-orange)
        "cheat": 120 / 360.0      # Green
    }

    # Generate colors for each package type
    for key, base_h in package_hues.items():
        # Use the dynamically determined target S and V
        r_norm, g_norm, b_norm = colorsys.hsv_to_rgb(base_h, package_target_s, package_target_v)
        dynamic_package_colors[key] = (int(r_norm * 255), int(g_norm * 255), int(b_norm * 255))
        #print(f"  {key.capitalize()} Color: {dynamic_package_colors[key]}")

    # Handle "combo" color (always dark, but with a slight variation based on theme)
    r_norm, g_norm, b_norm = colorsys.hsv_to_rgb(0, 0, combo_target_v) # Hue and Saturation don't matter for V=0.0-0.15
    dynamic_package_colors["combo"] = (int(r_norm * 255), int(g_norm * 255), int(b_norm * 255))
    #print(f"  Combo Color: {dynamic_package_colors['combo']}")


    # Store the generated theme colors in a dictionary
    state.game_theme_colors = {
        "original_pet_color": state.pet_color,
        "adjusted_brightness_color": (adjusted_r, adjusted_g, adjusted_b),
        "overlay_color_with_alpha": overlay_color_with_alpha,
        "contrast_color": contrast_color,
        "system_messages": inverted_color,
        "user_message_color": user_message_color, # This is still fixed black/white
        "error_color": error_color,
        "package_colors": dynamic_package_colors, # NEW: The dynamic package colors
    }


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
    set_color_theme()
    if gui_core._font is None or gui_core._line_height == 0 or not gui_core._gui_rects:
         print("Error: draw_gui called before gui_core components are initialized.")
         return

    if not state.is_initial_popup_phase:
        if state.background_image:
            screen.blit(state.background_image, (0, 0))
        else:
            screen.fill(config.fallback_bg_color)

        draw_filter_overlay(screen)

        # ------- draw pet ----------
        current_circle_center_x = config.BASE_CIRCLE_CENTER_X
        current_circle_center_y = config.BASE_CIRCLE_CENTER_Y
        animation.update_animation_state(current_time_ms) 
        animation_offset_x, animation_offset_y = animation.calculate_circle_offset(current_time_ms)

        current_circle_center_x += animation_offset_x
        current_circle_center_y += animation_offset_y

        pygame.draw.circle(screen, config.BLACK, (int(current_circle_center_x), int(current_circle_center_y)), state.current_radius)
        pygame.draw.circle(screen, state.pet_color, (int(current_circle_center_x), int(current_circle_center_y)), state.current_radius, 5)

        # ----------------------
        panel_rect = gui_core._gui_rects['panel_rect']
        input_rect = gui_core._gui_rects['input_rect']
        history_rect = gui_core._gui_rects['history_rect']
        history_display_area = gui_core._history_display_area
        
        # Draw the panel and history area backgrounds (always)
        pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], panel_rect)
        pygame.draw.rect(screen, state.game_theme_colors["contrast_color"], history_rect)

        # --- Draw Stat Icons ---
        stats_to_draw_order = ["fullness", "hydration", "energy"]
        icon_start_x = config.STAT_ICON_START_X_SCREEN
        icon_start_y = config.STAT_ICON_START_Y_SCREEN
        icon_height = config.STAT_ICON_SIZE[1]
        icon_spacing = config.STAT_ICON_SPACING_Y

        for i, stat_name in enumerate(stats_to_draw_order):
            stat_value = state.pet_stats.get(stat_name, 0)
            stat_level = _get_stat_level(stat_value) 
            icon_surface = gui_core._stat_icons.get((stat_name, stat_level))
            if icon_surface:
                icon_draw_y = icon_start_y + i * (icon_height + icon_spacing)
                screen.blit(icon_surface, (icon_start_x, icon_draw_y))

        # --- Draw Input Box Area Background and Border --- (always)
        pygame.draw.rect(screen, state.game_theme_colors["contrast_color"], input_rect)


        # --- Draw Wrapped & Scrollable Chat History ---
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
        input_text_draw_area = pygame.Rect(
            input_rect.left + config.PADDING,
            input_rect.top + config.PADDING,
            input_rect.width - 2 * config.PADDING,
            input_rect.height - 2 * config.PADDING
        )
        input_clip_rect = input_text_draw_area.copy()
        original_clip = screen.get_clip()
        screen.set_clip(input_clip_rect)

        text_color = state.game_theme_colors["user_message_color"] #  # Default text color for input
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
        pygame.draw.rect(screen, config.GREY, input_rect, 1) # Border for input_rect

        gui_care_package.draw_package_buttons(screen, is_input_locked)

    gui_popups.draw_image_popup_if_visible(screen)
    
    if not state.is_initial_popup_phase:
         gui_popups.draw_popups(screen) 

    if not state.is_initial_popup_phase and state.inventory_panel_visible:
        gui_inventory.draw_inventory_panel(screen)

    if not state.is_initial_popup_phase and gui_core._inventory_toggle_button_rect:
        pygame.draw.circle(screen, config.INVENTORY_BUTTON_COLOR, gui_core._inventory_toggle_button_rect.center, config.INVENTORY_TOGGLE_BUTTON_SIZE // 2)
        pygame.draw.circle(screen, state.game_theme_colors["contrast_color"], gui_core._inventory_toggle_button_rect.center, config.INVENTORY_TOGGLE_BUTTON_SIZE // 2, 1)

    if not state.is_initial_popup_phase:
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        border_rect = pygame.Rect(0, 0, screen_width, screen_height)
        pygame.draw.rect(screen, state.pet_color, border_rect, config.PADDING)
