# gui.py

# TODO: change drawing the order of the icon pop ups and any other pop ups under the inventory screen,
#       top right icon pop ups should consider the new clock UI we have, and change its position, the clock opens and closes. 
#       draw the clock under the inventory screen.
#       info screen should also be drawn over pop ups, and over the inventory screen.

from pygame_int import config
from pygame_int import state
from pygame_int.main_digipet import animation

from pygame_int.main_digipet import gui_core
from pygame_int.main_digipet import gui_text_utils
from pygame_int.main_digipet import gui_inventory
from pygame_int.main_digipet import gui_popups
from pygame_int.main_digipet import gui_care_package

from pygame_int.main_digipet import gui_lore_panel # NEW: Import the new lore panel module
from pygame_int.main_digipet import gui_stat_icons
from pygame_int.main_digipet import gui_clock

import pygame


from utils.time_manager import get_time_tag_from_now

ALPHA_MULTIPLIERS = {
    'late night': 1.2,
    'early morning': 1.1,
    'morning': 0.8,
    'noon': 0.6,            # Lightest (multiplied by 0.6)
    'afternoon': 0.8,
    'late afternoon': 1,
    'night': 1.1,
    None: 1.0               # Default: No change
}

def draw_filter_overlay(screen):
    """
    Draws a filter overlay on the screen from the theme colors.
    The alpha is dynamically adjusted by multiplying the theme's base alpha
    by a factor based on the time of day.

    Args:
        screen (pygame.Surface): The main display surface.
    """

    timetag = get_time_tag_from_now()

    #timetag = "night"

    # 1. Get the original color components from the theme
    original_color = state.game_theme_colors["overlay_color_with_alpha"]
    base_color_rgb = original_color[:3]
    base_alpha = original_color[3] # The original alpha from your theme

    # 2. Get the appropriate multiplier, defaulting to 1.0 (no change)
    multiplier = ALPHA_MULTIPLIERS.get(timetag, ALPHA_MULTIPLIERS[None])

    # 3. Calculate the new alpha value
    # We must ensure the final value is an integer between 0 and 255
    dynamic_alpha = int(base_alpha * multiplier)
    clamped_alpha = min(150, max(30, dynamic_alpha)) # Clamp value to the valid range

    # 4. Create the new color tuple with the calculated alpha
    dynamic_color = (*base_color_rgb, clamped_alpha)

    # --- The rest of your function remains the same ---

    # Clear the overlay surface
    gui_core.overlay_surface.fill((0, 0, 0, 0))

    # Draw the rectangle with the new dynamic color
    pygame.draw.rect(gui_core.overlay_surface, dynamic_color, (0, 0, config.WIDTH, config.HEIGHT), 0)

    # Blit the overlay_surface onto the whole screen
    screen.blit(gui_core.overlay_surface, (0, 0))


# --- NEW: Function to handle GUI-related events ---
# gui.py

# ... imports remain the same ...

def handle_gui_event(event):
    """
    Handles Pygame events related to the GUI.
    """
    if event.type == pygame.MOUSEBUTTONDOWN:
        mouse_pos = event.pos

        # Retrieve rects
        current_gui_rects = gui_core.get_gui_rects()
        input_rect = current_gui_rects.get('input_rect')

        # --- 1. PRIORITY: Lore Panel (Modal) ---
        if state.lore_panel_visible:
            lore_panel_rects = gui_core.get_lore_panel_rects()
            lore_body_area_rect = lore_panel_rects.get('lore_body_area')
            lore_close_button_rect = lore_panel_rects.get('lore_close_button')

            # Handle Mouse Wheel Scrolling
            if event.button in (4, 5) and lore_body_area_rect and lore_body_area_rect.collidepoint(event.pos):
                scroll_speed = config.LORE_PANEL_SCROLL_SPEED * (-1 if event.button == 4 else 1)
                state.lore_panel_scroll_y += scroll_speed
                lore_content_height = gui_lore_panel.calculate_lore_body_height(state.lore_panel_content)
                max_lore_scroll = max(0, lore_content_height - lore_body_area_rect.height)
                state.lore_panel_scroll_y = max(0, min(state.lore_panel_scroll_y, max_lore_scroll))
                return 

            # Handle Lore Close Button
            if event.button == 1 and lore_close_button_rect and lore_close_button_rect.collidepoint(event.pos):
                print("Lore panel close button clicked. Closing panel.")
                state.lore_panel_visible = False 
                return 

            # If Lore Panel is open, we consume ALL clicks so you can't click things behind it
            return 


        # --- 2. PRIORITY: Clock Toggles ---
        # We check this BEFORE the main panel logic.
        # We use the function from gui_clock to handle the logic and state change.
        if event.button == 1:
            if gui_clock.handle_clock_click(mouse_pos):
                return # Click handled by clock, stop processing


        # --- 3. PRIORITY: Main GUI (Panel, Input, etc.) ---
        # Check if the panel is visible and valid
        if event.button == 1 and not state.chatbot_is_processing: 

            if state.panel_visible and input_rect and not state.agent_sleeping and not state.chatbot_is_processing:
                if not input_rect.collidepoint(mouse_pos):
                    # Clicked outside input box -> Unfocus
                    if state.cursor_active:
                        gui_text_utils.add_message_to_history("Input box inactive...", "system")
                    state.cursor_active = False
                    state.cursor_visible = False
                else:
                    # Clicked inside input box -> Focus
                    if not state.cursor_active:
                        gui_text_utils.add_message_to_history("Input box active...", "system")
                    state.cursor_active = True
            else:
                # Panel hidden -> Ensure cursor inactive
                state.cursor_active = False
                state.cursor_visible = False

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
                    if state.agent_sleeping:
                        display_text = "The bot is currently sleeping."
                    else:
                        display_text = "Waiting for bot..."
                    try:
                        text_surface = gui_core._font.render(display_text, True, state.game_theme_colors["original_pet_color"])
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
                                pygame.draw.line(screen, state.game_theme_colors["user_message_color"], (cursor_x, cursor_y_start), (cursor_x, cursor_y_end), 1)
                    except pygame.error as e:
                        print(f"Pygame error rendering user input or cursor: {e}")
                screen.set_clip(original_clip)
                pygame.draw.rect(screen, config.GREY, input_rect, 1) # Border for input box

        # Moved draw stat icons to its own spot
        gui_stat_icons.draw_stat_icons(screen)
        # Changed the order of drawing, now we draw these buttons before we draw the chat window
        gui_care_package.draw_package_buttons(screen, is_input_locked)

        gui_popups.draw_popups(screen)


        if state.inventory_panel_visible:
            gui_inventory.draw_inventory_panel(screen)



        if gui_core._inventory_toggle_button_rect:
            inv_but_border_color=state.game_theme_colors["original_pet_color"]
            pygame.draw.circle(screen, state.game_theme_colors["contrast_color"], gui_core._inventory_toggle_button_rect.center, config.INVENTORY_TOGGLE_BUTTON_SIZE // 2)
            pygame.draw.circle(screen, inv_but_border_color, gui_core._inventory_toggle_button_rect.center, config.INVENTORY_TOGGLE_BUTTON_SIZE // 2, 2)





            # --- Draw Panel Toggle Button ---
            if gui_core._panel_toggle_button_rect:
                button_rect = gui_core._panel_toggle_button_rect
                pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], button_rect)

                arrow_char = ">" if state.panel_visible else "<"
                try:
                    arrow_surface = gui_core._font.render(arrow_char, True, state.game_theme_colors["contrast_color"])
                    arrow_rect = arrow_surface.get_rect(center=button_rect.center)
                    screen.blit(arrow_surface, arrow_rect)
                except pygame.error as e:
                    print(f"Pygame error rendering panel toggle arrow: {e}")



        # --- Draw Lore Panel Toggle Button (always visible) ---
        if gui_core._lore_toggle_button_rect:
            button_rect = gui_core._lore_toggle_button_rect


            # Make border rect
            border_thickness = 2
            border_color = state.game_theme_colors["original_pet_color"]
            border_rect = button_rect.inflate(border_thickness * 2, border_thickness * 2)

            # Draw border
            pygame.draw.rect(screen, border_color, border_rect)


            pygame.draw.rect(screen, state.game_theme_colors["contrast_color"], button_rect)
            try:
                # Text for the toggle button
                button_text = "Info"
                text_surface = gui_core._font.render(button_text, True, border_color)
                text_rect = text_surface.get_rect(center=button_rect.center)
                screen.blit(text_surface, text_rect)
            except pygame.error as e:
                print(f"Pygame error rendering lore toggle button text: {e}")



        # --- NEW: Draw Mute Button --- Moved above inventory menu
        if gui_core._mute_button_rect:
            button_rect = gui_core._mute_button_rect
            button_color = state.game_theme_colors["system_messages"] if state.is_muted else state.game_theme_colors["original_pet_color"]
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

        gui_clock.draw_current_time(screen)
        gui_clock.draw_sleep_duration(screen) # TODO: Implement sleep duration clock

        # NEW: Draw Lore Panel if visible (highest layer, after other modals)
        if state.lore_panel_visible:
            gui_lore_panel.draw_lore_panel(screen) # No current_time_ms needed as it snaps



    # Draw whole screen border
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        border_rect = pygame.Rect(0, 0, screen_width, screen_height)
        pygame.draw.rect(screen, state.pet_color, border_rect, config.PADDING)




    gui_popups.draw_active_image_popups(screen)
    gui_popups.draw_popups(screen)
