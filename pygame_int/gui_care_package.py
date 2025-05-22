import pygame
from pygame_int import config
from pygame_int import state
from pygame_int import gui_core # For _font, _left_scroll_button_rect, etc.

def draw_package_buttons(screen, is_input_locked):
    """
    Draws the care package buttons (as rectangles) and their scroll controls.
    Visually disables them if input is locked.
    Uses gui_core for font and rects. Accesses config and state.
    """
    if gui_core._left_scroll_button_rect is None: 
         return

    total_packages = len(config.CARE_PACKAGES)
    visible_start = state.package_button_visible_start_index
    buttons_per_page = max(1, gui_core._buttons_per_page) 
    visible_end = min(visible_start + buttons_per_page, total_packages)

    can_scroll_left = visible_start > 0
    can_scroll_right = visible_end < total_packages

    left_scroll_color = config.SCROLL_BUTTON_COLOR_DISABLED if not can_scroll_left or is_input_locked else config.SCROLL_BUTTON_COLOR_ENABLED
    right_scroll_color = config.SCROLL_BUTTON_COLOR_DISABLED if not can_scroll_right or is_input_locked else config.SCROLL_BUTTON_COLOR_ENABLED

    pygame.draw.rect(screen, left_scroll_color, gui_core._left_scroll_button_rect) 
    pygame.draw.rect(screen, state.pet_color, gui_core._left_scroll_button_rect, 1) 

    pygame.draw.rect(screen, right_scroll_color, gui_core._right_scroll_button_rect) 
    pygame.draw.rect(screen, state.pet_color, gui_core._right_scroll_button_rect, 1) 

    button_width = config.PACKAGE_BUTTON_SIZE 
    button_height = config.PACKAGE_BUTTON_SIZE   
    button_spacing_x = config.PACKAGE_BUTTON_SPACING_X

    start_x = gui_core._left_scroll_button_rect.right 
    button_y_top = gui_core._care_package_area_rect.top 

    for i in range(visible_start, visible_end):
        package_info = config.CARE_PACKAGES[i]
        base_color = package_info["color"]
        button_color = config.PACKAGE_BUTTON_COLOR_DISABLED(base_color) if is_input_locked else base_color

        button_x = start_x + (i - visible_start) * (button_width + button_spacing_x)
        button_rect = pygame.Rect(button_x, button_y_top, button_width, button_height)

        pygame.draw.rect(screen, button_color, button_rect)
        pygame.draw.rect(screen, state.pet_color, button_rect, 1) 

        number_text = str(i + 1)
        if gui_core._font: # Ensure font is initialized
            outline_surface = gui_core._font.render(number_text, True, button_color) 
            outline_rect = outline_surface.get_rect(center=button_rect.center)

            offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dx, dy in offsets:
                outline_pos = (outline_rect.x + dx, outline_rect.y + dy)
                screen.blit(outline_surface, outline_pos)

            text_color = (0, 0, 0) 
            if button_color == (0, 0, 0) or sum(button_color) < 150: 
                text_color = (255, 255, 255)

            text_surface = gui_core._font.render(number_text, True, text_color) 
            text_rect = text_surface.get_rect(center=button_rect.center) 
            screen.blit(text_surface, text_rect)

def get_package_button_click_regions():
    """
    Returns a list of tuples (identifier, rect) for clickable package buttons and scroll controls.
    Only includes buttons that are currently visible.
    Uses gui_core for rects and button count. Accesses config and state.
    """
    click_regions = []
    if gui_core._left_scroll_button_rect is None: 
         return click_regions

    click_regions.append(("scroll_left", gui_core._left_scroll_button_rect)) 
    click_regions.append(("scroll_right", gui_core._right_scroll_button_rect)) 

    total_packages = len(config.CARE_PACKAGES)
    visible_start = state.package_button_visible_start_index
    buttons_per_page = max(1, gui_core._buttons_per_page) 
    visible_end = min(visible_start + buttons_per_page, total_packages)

    button_width = config.PACKAGE_BUTTON_SIZE
    button_height = config.PACKAGE_BUTTON_SIZE 
    button_spacing_x = config.PACKAGE_BUTTON_SPACING_X

    start_x = gui_core._left_scroll_button_rect.right + button_spacing_x 
    button_y_top = gui_core._care_package_area_rect.top 

    for i in range(visible_start, visible_end):
        button_x = start_x + (i - visible_start) * (button_width + button_spacing_x)
        button_rect = pygame.Rect(button_x, button_y_top, button_width, button_height)
        click_regions.append((f"package_{i}", button_rect))

    return click_regions
