
from pygame_int import gui_config


def calculate_total_content_height(elements):
    """
    Calculates the total height of all UI elements in a list by finding the lowest element's bottom edge.
    """
    max_bottom = 0
    for element in elements:
        # We only care about UI objects that have a rect attribute
        if hasattr(element, 'rect'):
            max_bottom = max(max_bottom, element.rect.bottom)
    # Return the lowest point plus the standard spacing for a clean look
    return max_bottom + gui_config.INPUT_BOX_SPACING


def draw_section_title(font, title, y, screen_width):
    """Helper function to draw a section title and return the surface and rect."""
    text_surface = font.render(f"[{title}]", True, gui_config.SECTION_TITLE_COLOR)
    text_rect = text_surface.get_rect(centerx=screen_width // 2, top=y + gui_config.SECTION_TITLE_SPACING_TOP)
    return text_surface, text_rect