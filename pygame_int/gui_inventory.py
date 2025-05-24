import pygame
from pygame_int import config
from pygame_int import state
from pygame_int import gui_core # For _font, _line_height, rects, etc.
from pygame_int import gui_text_utils # For wrap_text

# --- Inventory Item Data Preparation ---
def prepare_inventory_item_data(item_string):
    """
    Pre-calculates wrapped lines and total height for a single inventory item string.
    Returns a dictionary: {'text': original, 'wrapped_lines': [...], 'total_height': H}
    Uses gui_core._font, gui_core._line_height, gui_core._inventory_item_draw_width.
    Calls gui_text_utils.wrap_text.
    Uses config.INVENTORY_PANEL_ITEM_SPACING.
    """
    if gui_core._font is None or gui_core._line_height == 0 or gui_core._inventory_item_draw_width <= 0:
        print("Warning: gui_core not fully initialized when preparing inventory item data.")
        return {'text': item_string, 'wrapped_lines': [item_string], 'total_height': (gui_core._line_height or 20) + config.INVENTORY_PANEL_ITEM_SPACING}

    try:
        wrapped_lines = gui_text_utils.wrap_text(item_string, gui_core._inventory_item_draw_width, "")
        item_total_height = len(wrapped_lines) * gui_core._line_height + config.INVENTORY_PANEL_ITEM_SPACING
        return {
            'text': item_string,
            'wrapped_lines': wrapped_lines,
            'total_height': item_total_height
        }
    except pygame.error as e:
        print(f"Pygame error during inventory item data preparation for '{item_string}': {e}")
        return {'text': item_string, 'wrapped_lines': [item_string], 'total_height': gui_core._line_height + config.INVENTORY_PANEL_ITEM_SPACING}

# --- List Height Calculation ---
def calculate_list_height(item_list):
    """
    Calculates the total pixel height needed to display a list of inventory item data.
    Sums the pre-calculated total_height for each item.
    Uses gui_core._line_height.
    Uses config.INVENTORY_PANEL_ITEM_SPACING.
    """
    if gui_core._line_height == 0:
         return sum(item_dict.get('total_height', 20 + config.INVENTORY_PANEL_ITEM_SPACING) for item_dict in item_list) # Fallback with estimated line height

    total_height = 0
    for item_dict in item_list:
         total_height += item_dict.get('total_height', gui_core._line_height + config.INVENTORY_PANEL_ITEM_SPACING)
    return total_height

# --- Item List Drawing ---
def draw_item_list(surface, item_list, draw_rect, scroll_y, item_color):
    """
    Draws a list of inventory item data (pre-calculated wrapped lines/heights)
    onto a surface within the specified rectangle. Handles vertical scrolling.
    Uses gui_core._font, gui_core._line_height, gui_core._inventory_item_start_x_offset.
    Uses config.INVENTORY_PANEL_ITEM_VERTICAL_PADDING.
    """
    if gui_core._font is None or gui_core._line_height == 0:
         return

    clip_rect = draw_rect.copy()
    original_clip = surface.get_clip() 
    surface.set_clip(clip_rect)

    current_draw_y_absolute = draw_rect.top + config.INVENTORY_PANEL_ITEM_VERTICAL_PADDING - scroll_y

    for item_dict in item_list:
        wrapped_lines = item_dict.get('wrapped_lines', [item_dict.get('text', 'Error')]) 
        item_total_height = item_dict.get('total_height', gui_core._line_height + config.INVENTORY_PANEL_ITEM_SPACING)

        if current_draw_y_absolute + item_total_height < clip_rect.top:
             current_draw_y_absolute += item_total_height
             continue 

        if current_draw_y_absolute > clip_rect.bottom:
             break 

        for i, line in enumerate(wrapped_lines):
            line_draw_y_absolute = current_draw_y_absolute + i * gui_core._line_height
            if line_draw_y_absolute + gui_core._line_height > clip_rect.top and line_draw_y_absolute < clip_rect.bottom:
                 try:
                     line_surface = gui_core._font.render(line, True, item_color)
                     surface.blit(line_surface,
                                  (draw_rect.left + gui_core._inventory_item_start_x_offset, line_draw_y_absolute))
                 except pygame.error as e:
                      print(f"Pygame error rendering inventory item line '{line}': {e}")
                 except Exception as e:
                      print(f"Unexpected error rendering inventory item line '{line}': {e}")
        current_draw_y_absolute += item_total_height
        if current_draw_y_absolute > clip_rect.bottom:
             break
    surface.set_clip(original_clip)

# --- Inventory Panel Drawing ---
def draw_inventory_panel(screen):
    """
    Draws the full-screen modal inventory panel with room and player lists.
    This should only be called when state.inventory_panel_visible is True.
    Uses gui_core variables for font and rects.
    Uses config for colors and padding.
    Calls local draw_item_list.
    Accesses state for inventory lists and scroll positions.
    """
    if gui_core._font is None or gui_core._inventory_panel_rect is None:
        print("Error: draw_inventory_panel called before gui_core components are initialized.")
        return

    
    inventory_overlay_surface = pygame.Surface((gui_core._inventory_panel_rect.width, gui_core._inventory_panel_rect.height), pygame.SRCALPHA)
    inventory_overlay_surface.fill(config.INVENTORY_PANEL_BG_COLOR)
    screen.blit(inventory_overlay_surface, (gui_core._inventory_panel_rect.left, gui_core._inventory_panel_rect.top))

    if config.INVENTORY_PANEL_BORDER_COLOR:
         pygame.draw.rect(screen, config.INVENTORY_PANEL_BORDER_COLOR, gui_core._inventory_panel_rect, 1)

    try:
        room_title_surface = gui_core._font.render("Room Inventory", True, config.INVENTORY_PANEL_TITLE_COLOR)
        room_title_x = gui_core._room_title_rect.left + (gui_core._room_title_rect.width - room_title_surface.get_width()) // 2
        room_title_y = gui_core._room_title_rect.top + (gui_core._room_title_rect.height - room_title_surface.get_height()) // 2
        screen.blit(room_title_surface, (room_title_x, room_title_y))

        player_title_surface = gui_core._font.render("Pet Inventory", True, config.INVENTORY_PANEL_TITLE_COLOR)
        player_title_x = gui_core._player_title_rect.left + (gui_core._player_title_rect.width - player_title_surface.get_width()) // 2
        player_title_y = gui_core._player_title_rect.top + (gui_core._player_title_rect.height - player_title_surface.get_height()) // 2
        screen.blit(player_title_surface, (player_title_x, player_title_y))
    except pygame.error as e:
        print(f"Pygame error rendering inventory titles: {e}")

    divider_x = gui_core._inventory_panel_rect.left + gui_core._inventory_panel_rect.width // 2
    pygame.draw.line(
        screen,
        config.INVENTORY_PANEL_DIVIDER_COLOR,
        (divider_x, gui_core._inventory_panel_rect.top + config.INVENTORY_PANEL_PADDING),
        (divider_x, gui_core._inventory_panel_rect.bottom - config.INVENTORY_PANEL_PADDING),
        config.INVENTORY_PANEL_DIVIDER_WIDTH
    )

    draw_item_list(screen, state.room_inventory_list, gui_core._room_list_area_rect, state.room_inventory_scroll_y, config.INVENTORY_PANEL_ITEM_COLOR)
    draw_item_list(screen, state.player_inventory_list, gui_core._player_list_area_rect, state.player_inventory_scroll_y, config.INVENTORY_PANEL_ITEM_COLOR)
