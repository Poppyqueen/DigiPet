import pygame
from .. import config
from .. import state
from . import gui_core # For _font, _left_scroll_button_rect, etc.

#buttons_per_page = 5 #  Placeholder number of buttons to show per page

def draw_package_buttons(screen, is_input_locked):
    """
    Draws the care package buttons (as rectangles) and their scroll controls.
    Visually disables them if input is locked.
    """

    if gui_core._left_scroll_button_rect is None or \
       gui_core._right_scroll_button_rect is None or \
       gui_core._care_package_area_rect is None:
         # gui_core.init_gui_elements or update_gui_rects hasn't properly initialized these.
         # print("Error: draw_package_buttons called before critical gui_core rects are initialized.")
         return

    # Calculate backdrop width to span from the start of the left scroll button
    # to the end of the right scroll button.
    backdrop_left = gui_core._left_scroll_button_rect.left
    backdrop_right = gui_core._right_scroll_button_rect.right
    backdrop_width = backdrop_right - backdrop_left + 10
    backdrop_height = config.INPUT_HEIGHT + 3 # Same as before

    # Define the backdrop rect
    _backdrop_area_rect = pygame.Rect(
        backdrop_left- 3,
        config.HEIGHT - backdrop_height - config.PADDING, # Bottom position
        backdrop_width-3,
        backdrop_height
    )

    # Draw the backdrop area
    pygame.draw.rect(screen, state.game_theme_colors["contrast_color"], _backdrop_area_rect)
    # Draw border for the backdrop area
    pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], _backdrop_area_rect, 2) # Border width of 2 pixels


    total_packages = len(config.CARE_PACKAGES)
    visible_start = state.package_button_visible_start_index
    buttons_per_page = max(1, gui_core._buttons_per_page) # Ensure we don't divide by zero or less than 1
    visible_end = min(visible_start + buttons_per_page, total_packages)

    # Determine if scrolling is possible in each direction *before* considering input lock
    can_scroll_left = visible_start > 0
    can_scroll_right = visible_end < total_packages

    # Determine scroll button colors based on scroll possibility and lock state
    # Button is colored DISABLED if scrolling is not possible OR if input is locked
    left_scroll_color = config.SCROLL_BUTTON_COLOR_DISABLED if not can_scroll_left or is_input_locked else config.SCROLL_BUTTON_COLOR_ENABLED
    right_scroll_color = config.SCROLL_BUTTON_COLOR_DISABLED if not can_scroll_right or is_input_locked else config.SCROLL_BUTTON_COLOR_ENABLED

    # Draw Left Scroll Button (as a filled rectangle)
    pygame.draw.rect(screen, left_scroll_color, gui_core._left_scroll_button_rect)
    pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], gui_core._left_scroll_button_rect, 2) # Border

    # Draw Right Scroll Button
    pygame.draw.rect(screen, right_scroll_color, gui_core._right_scroll_button_rect)
    pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], gui_core._right_scroll_button_rect, 2) # Border

    # Draw Package Buttons within the display area
    button_width = config.PACKAGE_BUTTON_WIDTH #/ 2 # Renamed for clarity, but still using config.PACKAGE_BUTTON_SIZE
    button_height = config.PACKAGE_BUTTON_HEIGHT #*2   #INPUT_HEIGHT # Make buttons fill the height of the area
    button_spacing_x = config.PACKAGE_BUTTON_SPACING_X

    # The starting X position for the first button, after the left scroll button
    start_x = gui_core._left_scroll_button_rect.right + button_spacing_x
    # The top Y position for all buttons (aligned with the top of the package area)
    button_y_top = gui_core._care_package_area_rect.top #- button_height // 2 # Centered vertically in the area

    # Draw a background rect for the button area (optional, helps visualize)
    # This rectangle will be in the middle, between scroll buttons
    # pygame.draw.rect(screen, config.DARK_GREY, _care_package_area_rect, 2) # Draw border of the whole area

    for i in range(int(visible_start), int(visible_end)):
        package_info = config.CARE_PACKAGES[i]
        color_name = package_info["color"]
        base_color = state.game_theme_colors["package_colors"][color_name]
        button_color = config.PACKAGE_BUTTON_COLOR_DISABLED(base_color) if is_input_locked else base_color

        # Calculate the button's rectangle
        button_x = start_x + (i - visible_start) * (button_width + button_spacing_x)
        button_rect = pygame.Rect(button_x, button_y_top, button_width, button_height)

        pygame.draw.rect(screen, button_color, button_rect)
        # Draw the border
        pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], button_rect, 2) # Border width of 1 pixels

        # Draw the number with outline
        number_text = str(i + 1)

        # Render the outline text slightly offset (using button_color for outline as before)
        # This creates a 'debossed' or 'cutout' look
        outline_surface = gui_core._font.render(number_text, True, state.game_theme_colors["contrast_color"])
        outline_rect = outline_surface.get_rect(center=button_rect.center)

        offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dx, dy in offsets:
            outline_pos = (outline_rect.x + dx, outline_rect.y + dy)
            screen.blit(outline_surface, outline_pos)

        # # Render the main text on top
        text_surface =gui_core._font.render(number_text, True, state.game_theme_colors["original_pet_color"])
        text_rect = text_surface.get_rect(center=button_rect.center) # Center text on the button's center
        screen.blit(text_surface, text_rect)


        # New border for hovering package button
        identifier = f"package_{i}"
        if identifier == state.hovered_package_identifier:
            #pygame.draw.rect(screen, (255, 255, 255), button_rect, 2)  # Draw a white border
            #pygame.draw.rect(screen, state.game_theme_colors["contrast_color"], button_rect, 2)  # Draw a border
            pygame.draw.rect(screen, base_color, button_rect, 2)  # Draw a border

            
            # Create hover information panel
            info_panel_width = backdrop_width - 3
            info_panel_height = backdrop_height * 2
            info_panel_x = _backdrop_area_rect.left
            info_panel_y = _backdrop_area_rect.top - info_panel_height #- 5  # Position above backdrop with small gap
            info_panel_rect = pygame.Rect(info_panel_x, info_panel_y, info_panel_width, info_panel_height)
            
            # # Draw the info panel background
            # # Draw the filled rectangle
            # #pygame.draw.rect(screen, state.game_theme_colors["contrast_color"], info_panel_rect)
            pygame.draw.rect(screen, state.game_theme_colors["contrast_color"], info_panel_rect)


            # # Create a surface with per-pixel alpha for transparency
            # info_surface = pygame.Surface((info_panel_width, info_panel_height), pygame.SRCALPHA)

            # # Fill the surface with a transparent color (RGBA)
            # transparent_background = state.game_theme_colors["overlay_color_with_alpha"]
            # info_surface.fill(transparent_background)

            # # Draw the transparent background to the screen
            # screen.blit(info_surface, (info_panel_x, info_panel_y))

            # Draw border for the info panel
            pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], info_panel_rect, 2)
            
            # Display package information
            if "package" in package_info and len(package_info["package"]) > 0:
                # Collect all item names
                #print(package_info)
                state.highlight_items_list = []
                for item in package_info["package"]:
                    state.highlight_items_list.append(item['name'].title())
                
                # Text positioning variables
                text_x = info_panel_x + 8  # Left padding
                text_y = info_panel_y + 8  # Top padding
                line_height = gui_core._font.get_height() + 2
                
                # Calculate scrollable area
                available_height = info_panel_height - 16  # Account for top/bottom padding
                max_visible_lines = available_height // line_height
                total_items = len(state.highlight_items_list)
                
                # Apply scroll offset
                scroll_offset = int(state.package_scroll_y // 10)  # Adjust scroll sensitivity
                start_index = max(0, min(scroll_offset, total_items - max_visible_lines))
                end_index = min(start_index + max_visible_lines, total_items)
                
                # Determine if we can scroll up or down
                can_scroll_up = start_index > 0
                can_scroll_down = end_index < total_items
                
                # Draw scroll indicators (triangles)
                triangle_size = 8
                triangle_margin = 4
                triangle_color = state.game_theme_colors["original_pet_color"]
                
                # Up triangle (when can scroll up)
                if can_scroll_up:
                    triangle_center_x = info_panel_x + info_panel_width - triangle_size - triangle_margin
                    triangle_top_y = info_panel_y + triangle_margin
                    triangle_points = [
                        (triangle_center_x, triangle_top_y),  # Top point
                        (triangle_center_x - triangle_size//2, triangle_top_y + triangle_size),  # Bottom left
                        (triangle_center_x + triangle_size//2, triangle_top_y + triangle_size)   # Bottom right
                    ]
                    pygame.draw.polygon(screen, triangle_color, triangle_points)
                
                # Down triangle (when can scroll down)
                if can_scroll_down:
                    triangle_center_x = info_panel_x + info_panel_width - triangle_size - triangle_margin
                    triangle_bottom_y = info_panel_y + info_panel_height - triangle_margin
                    triangle_points = [
                        (triangle_center_x, triangle_bottom_y),  # Bottom point
                        (triangle_center_x - triangle_size//2, triangle_bottom_y - triangle_size),  # Top left
                        (triangle_center_x + triangle_size//2, triangle_bottom_y - triangle_size)   # Top right
                    ]
                    pygame.draw.polygon(screen, triangle_color, triangle_points)
                                
                # Display visible item names (truncated if too long)
                for idx in range(start_index, end_index):
                    item_name = state.highlight_items_list[idx]
                    # Reserve space for scroll indicators on the right
                    max_width = info_panel_width - 32  # Reduced to account for triangle space
                    
                    # Truncate if too long
                    name_surface = gui_core._font.render(item_name, True, state.game_theme_colors["original_pet_color"])
                    if name_surface.get_width() > max_width:
                        # Find how much text fits
                        for i in range(len(item_name), 0, -1):
                            truncated = item_name[:i] + "..."
                            test_surface = gui_core._font.render(truncated, True, state.game_theme_colors["original_pet_color"])
                            if test_surface.get_width() <= max_width:
                                name_surface = test_surface
                                break
                    
                    screen.blit(name_surface, (text_x, text_y))


                    # Draw lines 
                    # line_color = state.game_theme_colors["package_colors"][package_info["color"]]
                    line_color = state.game_theme_colors["original_pet_color"]
                    # line_color = state.game_theme_colors["overlay_color_with_alpha"]


                    pygame.draw.line(screen, line_color,
                                        (text_x, text_y + line_height - 1),
                                        (info_panel_x + info_panel_width - 8, text_y + line_height - 1))
                
                    text_y += line_height



        # Render the outline text slightly offset (using button_color for outline as before)
        # This creates a 'debossed' or 'cutout' look
        outline_surface = gui_core._font.render(number_text, True, state.game_theme_colors["contrast_color"])
        outline_rect = outline_surface.get_rect(center=button_rect.center)

        offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dx, dy in offsets:
            outline_pos = (outline_rect.x + dx, outline_rect.y + dy)
            screen.blit(outline_surface, outline_pos)

        # # Render the main text on top
        text_surface =gui_core._font.render(number_text, True, state.game_theme_colors["original_pet_color"])
        text_rect = text_surface.get_rect(center=button_rect.center) # Center text on the button's center
        screen.blit(text_surface, text_rect)


def get_package_button_click_regions():
    """
    Returns a list of tuples (identifier, rect) for clickable package buttons and scroll controls.
    Only includes buttons that are currently visible.
    This function does NOT check if input is locked; that's handled in game.py.
    """
    click_regions = []
    if gui_core._left_scroll_button_rect is None:
         # gui.init_gui hasn't been called, return empty list
         # print("Error: get_package_button_click_regions called before gui.init_gui") # Avoid excessive logging
         return click_regions

    # Add scroll button regions (always potentially clickable if initialized)
    click_regions.append(("scroll_left", gui_core._left_scroll_button_rect))
    click_regions.append(("scroll_right", gui_core._right_scroll_button_rect))

    total_packages = len(config.CARE_PACKAGES)
    visible_start = state.package_button_visible_start_index
    buttons_per_page = max(1, gui_core._buttons_per_page)
    visible_end = min(visible_start + buttons_per_page, total_packages)

    # Calculate the button positions again to create the click rects
    button_width = config.PACKAGE_BUTTON_WIDTH #/ 2
    button_height = config.PACKAGE_BUTTON_HEIGHT#*2 # Match height from draw function
    button_spacing_x = config.PACKAGE_BUTTON_SPACING_X

    # The starting X position for the first button, after the left scroll button
    start_x = gui_core._left_scroll_button_rect.right + button_spacing_x
    # The top Y position for all buttons (aligned with the top of the package area)
    button_y_top = gui_core._care_package_area_rect.top #- button_height // 2

    # Add regions for the visible package buttons
    for i in range(int(visible_start), int(visible_end)):
        # Calculate the button's rectangle position
        button_x = start_x + (i - visible_start) * (button_width + button_spacing_x)
        button_rect = pygame.Rect(button_x, button_y_top, button_width, button_height)

        # Add the region identifier and rect to the list
        click_regions.append((f"package_{i}", button_rect))

    return click_regions



def get_package_scroll_info():
    """
    Returns scroll information for the currently hovered package.
    Used by main game to handle scroll bounds properly.
    Returns: dict with 'line_height', 'max_scroll', 'total_items', 'max_visible_lines'
    """
    if not state.hovered_package_identifier or not hasattr(state, 'highlight_items_list'):
        return {'line_height': 0, 'max_scroll': 0, 'total_items': 0, 'max_visible_lines': 0}
    
    line_height = gui_core._font.get_height() + 2
    backdrop_height = config.INPUT_HEIGHT + 3
    available_height = (backdrop_height * 2) - 16  # Panel height minus padding
    max_visible_lines = available_height // line_height
    total_items = len(state.highlight_items_list)
    
    # Calculate maximum scroll (how far down we can scroll)
    max_scroll = max(0, (total_items - max_visible_lines) * line_height)
    
    return {
        'line_height': line_height,
        'max_scroll': max_scroll, 
        'total_items': total_items,
        'max_visible_lines': max_visible_lines
    }