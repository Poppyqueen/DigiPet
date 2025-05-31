# pygame_int/gui_lore_panel.py

import pygame
from pygame_int import config
from pygame_int import state
from pygame_int import gui_core # For _font, _line_height, rects, etc.
from pygame_int import gui_text_utils # For wrap_text


# --- Content Data Preparation ---
def prepare_lore_content_data(title_text, body_raw_text):
    """
    Pre-calculates wrapped lines and total height for the lore panel's body text.
    Returns a dictionary: {'title': original_title, 'body_wrapped_lines': [...], 'body_total_height': H}
    Uses gui_core._font, gui_core._line_height, gui_core._lore_panel_text_draw_width.
    Calls gui_text_utils.wrap_text.
    **MODIFIED to correctly handle explicit newlines (`\n`) in body_raw_text.**
    """
    if gui_core._font is None or gui_core._line_height == 0 or gui_core._lore_panel_text_draw_width <= 0:
        print("Warning: gui_core not fully initialized when preparing lore panel content.")
        # Fallback in case of initialization issue
        body_wrapped_lines = [body_raw_text] if body_raw_text else [""]
        body_total_height = (gui_core._line_height or 20) * len(body_wrapped_lines) + config.LORE_PANEL_PADDING
        return {
            'title': title_text,
            'body_wrapped_lines': body_wrapped_lines,
            'body_total_height': body_total_height
        }

    all_wrapped_lines = []
    # Split the raw text by explicit newline characters.
    # This will create a list of strings, where each string is a natural "paragraph"
    # or segment separated by a newline. Empty strings in this list represent blank lines.
    paragraphs = body_raw_text.split('\n')

    try:
        for para in paragraphs:
            if not para:
                # If a paragraph segment is empty (e.g., from `\n\n` or a trailing `\n`),
                # add an empty string to the wrapped lines to represent a blank line.
                all_wrapped_lines.append("")
            else:
                # For non-empty segments, apply the existing word-wrapping logic.
                # The third argument `""` implies `gui_text_utils.wrap_text` handles font internally.
                wrapped_segment = gui_text_utils.wrap_text(para, gui_core._lore_panel_text_draw_width, "")
                
                # Extend the main list with lines from the current segment.
                # Ensure that if wrap_text somehow returns an empty list for a non-empty `para`,
                # we still add the original text to prevent data loss.
                if not wrapped_segment and para:
                    all_wrapped_lines.append(para)
                else:
                    all_wrapped_lines.extend(wrapped_segment)

        # Handle the edge case where the original body_raw_text was completely empty.
        # Ensure there's at least one empty line for consistent behavior.
        if not all_wrapped_lines and not body_raw_text:
            all_wrapped_lines = [""]

        body_total_height = len(all_wrapped_lines) * gui_core._line_height + config.LORE_PANEL_PADDING
        
        return {
            'title': title_text.upper().replace("_", " "),
            'body_wrapped_lines': all_wrapped_lines,
            'body_total_height': body_total_height
        }
    except pygame.error as e:
        print(f"Pygame error during lore content data preparation for '{body_raw_text[:50]}...': {e}")
        # Fallback: if an error occurs during processing, return a simplified version.
        return {'title': title_text, 'body_wrapped_lines': [body_raw_text], 'body_total_height': gui_core._line_height + config.LORE_PANEL_PADDING}
    

# --- List Height Calculation ---
def calculate_lore_body_height(prepared_content_dict):
    """
    Calculates the total pixel height needed to display the prepared lore body content.
    """
    return prepared_content_dict.get('body_total_height', 0)

# --- Lore Panel Drawing ---
def draw_lore_panel(screen):
    """
    Draws the full-screen modal Lore Panel with its title and scrollable body.
    This should only be called when state.lore_panel_visible is True.
    """
    if gui_core._font is None or gui_core._lore_panel_rect is None:
        print("Error: draw_lore_panel called before gui_core components are initialized.")
        return

    lore_rects = gui_core.get_lore_panel_rects()
    panel_rect = lore_rects['lore_panel']
    title_rect = lore_rects['lore_title_area']
    body_area_rect = lore_rects['lore_body_area']
    close_button_rect = lore_rects['lore_close_button']

    # --- Draw Background Overlay (Covers entire screen) ---
    # Create a temporary surface for the overlay
    overlay_surface = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
    overlay_surface.fill(config.LORE_PANEL_OVERLAY_COLOR)
    screen.blit(overlay_surface, (0, 0))

    # --- Draw Lore Panel Background (Full screen, always at 0,0 when visible) ---
    # Since it snaps, panel_rect is already at (0,0) in gui_core when visible.
    pygame.draw.rect(screen, config.LORE_PANEL_BG_COLOR, panel_rect)
    if config.LORE_PANEL_BORDER_COLOR:
        pygame.draw.rect(screen, config.LORE_PANEL_BORDER_COLOR, panel_rect, config.LORE_PANEL_BORDER_WIDTH)

    # --- Draw Title ---
    try:
        title_surface = gui_core._font.render(state.lore_panel_content.get('title', ''), True, config.LORE_PANEL_TITLE_COLOR)
        title_x = title_rect.left + (title_rect.width - title_surface.get_width()) // 2
        title_y = title_rect.top + (title_rect.height - title_surface.get_height()) // 2
        screen.blit(title_surface, (title_x, title_y))
    except pygame.error as e:
        print(f"Pygame error rendering lore title: {e}")

    # --- Draw Close Button ---
    pygame.draw.rect(screen, config.LORE_PANEL_CLOSE_BUTTON_COLOR, close_button_rect)
    try:
        close_text_surface = gui_core._font.render("X", True, config.LORE_PANEL_CLOSE_BUTTON_TEXT_COLOR)
        close_text_rect = close_text_surface.get_rect(center=close_button_rect.center)
        screen.blit(close_text_surface, close_text_rect)
    except pygame.error as e:
        print(f"Pygame error rendering lore close button text: {e}")


    # --- Draw Scrollable Body ---
    body_wrapped_lines = state.lore_panel_content.get('body_wrapped_lines', [])
    body_total_height = state.lore_panel_content.get('body_total_height', 0)

    # Clamp scroll
    max_scroll = max(0, body_total_height - body_area_rect.height)
    state.lore_panel_scroll_y = max(0, min(state.lore_panel_scroll_y, max_scroll))

    current_draw_y_absolute = body_area_rect.top + config.LORE_PANEL_PADDING - state.lore_panel_scroll_y

    # Set clip area for the body text
    original_clip = screen.get_clip()
    screen.set_clip(body_area_rect)

    for line in body_wrapped_lines:
        line_draw_y_absolute = current_draw_y_absolute
        if line_draw_y_absolute + gui_core._line_height < body_area_rect.top:
            current_draw_y_absolute += gui_core._line_height
            continue
        if line_draw_y_absolute > body_area_rect.bottom:
            break

        try:
            line_surface = gui_core._font.render(line, True, config.LORE_PANEL_TEXT_COLOR)
            screen.blit(line_surface,
                        (body_area_rect.left + gui_core._lore_panel_text_start_x_offset, line_draw_y_absolute))
        except pygame.error as e:
            print(f"Pygame error rendering lore body line '{line}': {e}")
        current_draw_y_absolute += gui_core._line_height

    screen.set_clip(original_clip)