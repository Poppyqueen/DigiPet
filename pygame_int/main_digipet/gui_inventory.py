# gui_inventory.py

import pygame
from pygame_int import config
from pygame_int import state
from pygame_int.main_digipet import gui_core
from pygame_int.main_digipet import gui_text_utils


# ---------------------------------------------------------------------------
# Item data preparation
# ---------------------------------------------------------------------------

def prepare_inventory_item_data(item_string: str) -> dict:
    """
    Pre-calculate wrapped lines and pixel height for a single inventory item.

    Returns a dict: {'text', 'wrapped_lines', 'total_height'}
    """
    font        = gui_core.get_font()
    line_height = gui_core.get_line_height()
    draw_width  = gui_core.get_inventory_item_draw_width()

    if font is None or line_height == 0 or draw_width <= 0:
        print("[gui_inventory] gui_core not fully initialised when preparing item data.")
        return {
            'text':          item_string,
            'wrapped_lines': [item_string],
            'total_height':  (line_height or 20) + config.INVENTORY_PANEL_ITEM_SPACING,
        }

    try:
        wrapped     = gui_text_utils.wrap_text(item_string, draw_width, "")
        total_h     = len(wrapped) * line_height + config.INVENTORY_PANEL_ITEM_SPACING
        return {'text': item_string, 'wrapped_lines': wrapped, 'total_height': total_h}
    except pygame.error as e:
        print(f"[gui_inventory] Pygame error preparing item '{item_string}': {e}")
        return {
            'text':          item_string,
            'wrapped_lines': [item_string],
            'total_height':  line_height + config.INVENTORY_PANEL_ITEM_SPACING,
        }


# ---------------------------------------------------------------------------
# List height query
# ---------------------------------------------------------------------------

def calculate_list_height(item_list: list) -> int:
    """Return the total pixel height needed to display a list of prepared items."""
    line_height = gui_core.get_line_height()
    fallback    = (line_height or 20) + config.INVENTORY_PANEL_ITEM_SPACING
    return sum(item.get('total_height', fallback) for item in item_list)


# ---------------------------------------------------------------------------
# Item list drawing
# ---------------------------------------------------------------------------

def draw_item_list(
    surface: pygame.Surface,
    item_list: list,
    draw_rect: pygame.Rect,
    scroll_y: int,
    item_color,
) -> None:
    """
    Draw a scrollable list of prepared inventory items within draw_rect.
    """
    font        = gui_core.get_font()
    line_height = gui_core.get_line_height()
    x_offset    = gui_core.get_inventory_item_start_x_offset()

    if font is None or line_height == 0:
        return

    original_clip = surface.get_clip()
    surface.set_clip(draw_rect.copy())

    draw_y = draw_rect.top + config.INVENTORY_PANEL_ITEM_VERTICAL_PADDING - scroll_y

    for item in item_list:
        wrapped    = item.get('wrapped_lines', [item.get('text', 'Error')])
        item_h     = item.get('total_height', line_height + config.INVENTORY_PANEL_ITEM_SPACING)

        if draw_y + item_h < draw_rect.top:
            draw_y += item_h
            continue
        if draw_y > draw_rect.bottom:
            break

        for i, line in enumerate(wrapped):
            line_y = draw_y + i * line_height
            if line_y + line_height > draw_rect.top and line_y < draw_rect.bottom:
                try:
                    line_surf = font.render(line, True, item_color)
                    surface.blit(line_surf, (draw_rect.left + x_offset, line_y))
                except (pygame.error, Exception) as e:
                    print(f"[gui_inventory] Error rendering item line '{line}': {e}")

        draw_y += item_h
        if draw_y > draw_rect.bottom:
            break

    surface.set_clip(original_clip)


# ---------------------------------------------------------------------------
# Panel drawing
# ---------------------------------------------------------------------------

def draw_inventory_panel(screen: pygame.Surface) -> None:
    """
    Draw the full-screen modal inventory panel.
    Only call when state.inventory_panel_visible is True.
    """
    font        = gui_core.get_font()
    panel_rects = gui_core.get_panel_rects()

    if font is None or not panel_rects:
        print("[gui_inventory] draw_inventory_panel called before gui_core is initialised.")
        return

    panel_rect        = panel_rects["inventory_panel"]
    room_title_rect   = panel_rects["room_title"]
    player_title_rect = panel_rects["player_title"]
    room_list_rect    = panel_rects["room_list_area"]
    player_list_rect  = panel_rects["player_list_area"]

    # --- Background overlay ---
    overlay = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
    overlay.fill(config.INVENTORY_PANEL_BG_COLOR)
    screen.blit(overlay, (panel_rect.left, panel_rect.top))

    if config.INVENTORY_PANEL_BORDER_COLOR:
        pygame.draw.rect(screen, config.INVENTORY_PANEL_BORDER_COLOR, panel_rect, 1)

    # --- Column titles ---
    try:
        room_surf = font.render("Room Inventory", True, config.INVENTORY_PANEL_TITLE_COLOR)
        screen.blit(room_surf, room_surf.get_rect(center=room_title_rect.center))

        player_surf = font.render("Pet Inventory", True, config.INVENTORY_PANEL_TITLE_COLOR)
        screen.blit(player_surf, player_surf.get_rect(center=player_title_rect.center))
    except pygame.error as e:
        print(f"[gui_inventory] Error rendering titles: {e}")

    # --- Divider ---
    divider_x = panel_rect.left + panel_rect.width // 2
    pygame.draw.line(
        screen,
        config.INVENTORY_PANEL_DIVIDER_COLOR,
        (divider_x, panel_rect.top  + config.INVENTORY_PANEL_PADDING),
        (divider_x, panel_rect.bottom - config.INVENTORY_PANEL_PADDING),
        config.INVENTORY_PANEL_DIVIDER_WIDTH,
    )

    # --- Lists ---
    draw_item_list(
        screen, state.room_inventory_list,
        room_list_rect, state.room_inventory_scroll_y,
        config.INVENTORY_PANEL_ITEM_COLOR,
    )
    draw_item_list(
        screen, state.player_inventory_list,
        player_list_rect, state.player_inventory_scroll_y,
        config.INVENTORY_PANEL_ITEM_COLOR,
    )