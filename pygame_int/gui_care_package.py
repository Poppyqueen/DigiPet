import pygame
from pygame_int import config
from pygame_int import state
from pygame_int import gui_core # For _font, _left_scroll_button_rect, etc.

buttons_per_page = 5 #  Placeholder number of buttons to show per page

def draw_package_buttons(screen, is_input_locked):
    """
    Draws the care package buttons (as rectangles) and their scroll controls.
    Visually disables them if input is locked.
    """

    if gui_core._left_scroll_button_rect is None:
         # gui.init_gui hasn't been called, return empty list
         # print("Error: draw_package_buttons called before gui.init_gui") # Avoid excessive logging
         return
    
    backdrop_width=config.WIDTH - config.PANEL_WIDTH
    #print(f"width {config.PANEL_WIDTH} height {config.HEIGHT}")
    backdrop_height=config.INPUT_HEIGHT

    inner_padding = 3 # Padding for the inner area

    # Make rect for the care package area
    _backdrop_area_rect = pygame.Rect(
        config.PADDING, # Left position
        config.HEIGHT-backdrop_height-config.PADDING-inner_padding, # Bottom position
        backdrop_width, # Width
        backdrop_height+inner_padding # Height
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
    button_width = config.PACKAGE_BUTTON_SIZE # Renamed for clarity, but still using config.PACKAGE_BUTTON_SIZE
    button_height = config.PACKAGE_BUTTON_SIZE *2   #INPUT_HEIGHT # Make buttons fill the height of the area
    button_spacing_x = config.PACKAGE_BUTTON_SPACING_X

    # The starting X position for the first button, after the left scroll button
    start_x = gui_core._left_scroll_button_rect.right + button_spacing_x
    # The top Y position for all buttons (aligned with the top of the package area)
    button_y_top = gui_core._care_package_area_rect.top #- button_height // 2 # Centered vertically in the area

    # Draw a background rect for the button area (optional, helps visualize)
    # This rectangle will be in the middle, between scroll buttons
    # pygame.draw.rect(screen, config.DARK_GREY, _care_package_area_rect, 2) # Draw border of the whole area

    for i in range(visible_start, visible_end):
        package_info = config.CARE_PACKAGES[i]
        base_color = package_info["color"]
        button_color = config.PACKAGE_BUTTON_COLOR_DISABLED(base_color) if is_input_locked else base_color

        # Calculate the button's rectangle
        button_x = start_x + (i - visible_start) * (button_width + button_spacing_x)
        button_rect = pygame.Rect(button_x, button_y_top, button_width, button_height)

        # Draw the filled rectangle
        pygame.draw.rect(screen, button_color, button_rect)
        # Draw the border
        pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], button_rect, 2) # Border width of 1 pixels

        # Draw the number with outline
        number_text = str(i + 1)

        # Render the outline text slightly offset (using button_color for outline as before)
        # This creates a 'debossed' or 'cutout' look
        outline_surface = gui_core._font.render(number_text, True, button_color)
        outline_rect = outline_surface.get_rect(center=button_rect.center)

        offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dx, dy in offsets:
            outline_pos = (outline_rect.x + dx, outline_rect.y + dy)
            screen.blit(outline_surface, outline_pos)

        # Determine text color based on button color for contrast
        text_color = (0, 0, 0) # Default to black
        if button_color == (0, 0, 0) or sum(button_color) < 150: # If button is dark, use white text
            text_color = (255, 255, 255)

        # Render the main text on top
        text_surface =gui_core._font.render(number_text, True, text_color)
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
    button_width = config.PACKAGE_BUTTON_SIZE
    button_height = config.PACKAGE_BUTTON_SIZE*2 # Match height from draw function
    button_spacing_x = config.PACKAGE_BUTTON_SPACING_X

    # The starting X position for the first button, after the left scroll button
    start_x = gui_core._left_scroll_button_rect.right + button_spacing_x
    # The top Y position for all buttons (aligned with the top of the package area)
    button_y_top = gui_core._care_package_area_rect.top #- button_height // 2

    # Add regions for the visible package buttons
    for i in range(visible_start, visible_end):
        # Calculate the button's rectangle position
        button_x = start_x + (i - visible_start) * (button_width + button_spacing_x)
        button_rect = pygame.Rect(button_x, button_y_top, button_width, button_height)

        # Add the region identifier and rect to the list
        click_regions.append((f"package_{i}", button_rect))

    return click_regions