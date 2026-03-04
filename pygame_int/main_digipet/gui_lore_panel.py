# gui_lore_panel.py

import pygame
from pygame_int import config
from pygame_int import state
from pygame_int.main_digipet import gui_core
from pygame_int.main_digipet import gui_text_utils


# ---------------------------------------------------------------------------
# Content data preparation
# ---------------------------------------------------------------------------

def prepare_lore_content_data(title_text: str, body_raw_text: str) -> dict:
    """
    Pre-calculate wrapped lines and total height for the lore panel body.

    Returns
    -------
    dict with keys: 'title', 'body_wrapped_lines', 'body_total_height'

    Handles explicit newlines (\\n) in body_raw_text by treating each
    newline-delimited segment as a separate paragraph.
    """
    font        = gui_core.get_font()
    line_height = gui_core.get_line_height()
    draw_width  = gui_core.get_lore_panel_text_draw_width()

    if font is None or line_height == 0 or draw_width <= 0:
        print("[gui_lore_panel] gui_core not fully initialised when preparing lore content.")
        fallback_lines  = [body_raw_text] if body_raw_text else [""]
        fallback_height = (line_height or 20) * len(fallback_lines) + config.LORE_PANEL_PADDING
        return {
            'title':             title_text,
            'body_wrapped_lines': fallback_lines,
            'body_total_height':  fallback_height,
        }

    all_wrapped_lines = []
    paragraphs = body_raw_text.split('\n')

    try:
        for para in paragraphs:
            if not para:
                all_wrapped_lines.append("")
            else:
                wrapped = gui_text_utils.wrap_text(para, draw_width, "")
                if not wrapped and para:
                    all_wrapped_lines.append(para)
                else:
                    all_wrapped_lines.extend(wrapped)

        if not all_wrapped_lines and not body_raw_text:
            all_wrapped_lines = [""]

        body_total_height = len(all_wrapped_lines) * line_height + config.LORE_PANEL_PADDING

        return {
            'title':             title_text.upper().replace("_", " "),
            'body_wrapped_lines': all_wrapped_lines,
            'body_total_height':  body_total_height,
        }

    except pygame.error as e:
        print(f"[gui_lore_panel] Pygame error preparing lore content: {e}")
        return {
            'title':             title_text,
            'body_wrapped_lines': [body_raw_text],
            'body_total_height':  line_height + config.LORE_PANEL_PADDING,
        }


# ---------------------------------------------------------------------------
# Height query
# ---------------------------------------------------------------------------

def calculate_lore_body_height(prepared_content_dict: dict) -> int:
    """Return the total pixel height needed to display the prepared body content."""
    return prepared_content_dict.get('body_total_height', 0)


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def draw_lore_panel(screen: pygame.Surface) -> None:
    """
    Draw the full-screen modal lore panel.
    Only call when state.lore_panel_visible is True.
    """
    font = gui_core.get_font()
    lore_rects = gui_core.get_lore_panel_rects()
    if font is None or not lore_rects:
        print("[gui_lore_panel] draw_lore_panel called before gui_core is initialised.")
        return

    panel_rect        = lore_rects['lore_panel']
    title_rect        = lore_rects['lore_title_area']
    body_area_rect    = lore_rects['lore_body_area']
    close_button_rect = lore_rects['lore_close_button']
    line_height       = gui_core.get_line_height()
    text_x_offset     = gui_core.get_lore_panel_text_start_x_offset()

    # --- Background overlay ---
    overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
    overlay.fill(config.LORE_PANEL_OVERLAY_COLOR)
    screen.blit(overlay, (0, 0))

    # --- Panel background ---
    pygame.draw.rect(screen, config.LORE_PANEL_BG_COLOR, panel_rect)
    if config.LORE_PANEL_BORDER_COLOR:
        pygame.draw.rect(
            screen, config.LORE_PANEL_BORDER_COLOR, panel_rect,
            config.LORE_PANEL_BORDER_WIDTH
        )

    # --- Title ---
    try:
        title_surf = font.render(
            state.lore_panel_content.get('title', ''), True, config.LORE_PANEL_TITLE_COLOR
        )
        screen.blit(title_surf, title_surf.get_rect(center=title_rect.center))
    except pygame.error as e:
        print(f"[gui_lore_panel] Error rendering title: {e}")

    # --- Close button ---
    pygame.draw.rect(screen, config.LORE_PANEL_CLOSE_BUTTON_COLOR, close_button_rect)
    try:
        close_surf = font.render("X", True, config.LORE_PANEL_CLOSE_BUTTON_TEXT_COLOR)
        screen.blit(close_surf, close_surf.get_rect(center=close_button_rect.center))
    except pygame.error as e:
        print(f"[gui_lore_panel] Error rendering close button: {e}")

    # --- Scrollable body ---
    body_wrapped_lines = state.lore_panel_content.get('body_wrapped_lines', [])
    body_total_height  = state.lore_panel_content.get('body_total_height', 0)

    max_scroll = max(0, body_total_height - body_area_rect.height)
    scroll_y   = max(0, min(state.lore_panel_scroll_y, max_scroll))

    draw_y = body_area_rect.top + config.LORE_PANEL_PADDING - scroll_y

    original_clip = screen.get_clip()
    screen.set_clip(body_area_rect)

    for line in body_wrapped_lines:
        if draw_y + line_height < body_area_rect.top:
            draw_y += line_height
            continue
        if draw_y > body_area_rect.bottom:
            break
        try:
            line_surf = font.render(line, True, config.LORE_PANEL_TEXT_COLOR)
            screen.blit(line_surf, (body_area_rect.left + text_x_offset, draw_y))
        except pygame.error as e:
            print(f"[gui_lore_panel] Error rendering body line '{line}': {e}")
        draw_y += line_height

    screen.set_clip(original_clip)