# gui_care_package.py

import pygame
from pygame_int import config
from pygame_int import state
from pygame_int.main_digipet import gui_core


def _get_btn_rect(i: int, visible_start: int, left_rect, area_rect) -> "pygame.Rect":
    """Return the pygame.Rect for care-package button at index *i*."""
    spacing_x = config.PACKAGE_BUTTON_SPACING_X
    start_x   = left_rect.right + spacing_x
    btn_x     = start_x + (i - visible_start) * (config.PACKAGE_BUTTON_WIDTH + spacing_x)
    return pygame.Rect(btn_x, area_rect.top, config.PACKAGE_BUTTON_WIDTH, config.PACKAGE_BUTTON_HEIGHT)


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def draw_package_buttons(screen: pygame.Surface, is_input_locked: bool) -> None:
    """Draw the care-package button row with scroll controls."""
    cp_rects = gui_core.get_care_package_rects()
    if not cp_rects:
        return

    left_rect  = cp_rects["left_scroll"]
    right_rect = cp_rects["right_scroll"]
    area_rect  = cp_rects["area"]
    font       = gui_core.get_font()

    # --- Backdrop ---
    backdrop_left  = left_rect.left
    backdrop_right = right_rect.right
    backdrop_h     = config.INPUT_HEIGHT + 3
    backdrop_rect  = pygame.Rect(
        backdrop_left - 3,
        config.HEIGHT - backdrop_h - config.PADDING,
        backdrop_right - backdrop_left + 10 - 3,
        backdrop_h,
    )
    pygame.draw.rect(screen, state.game_theme_colors["contrast_color"],      backdrop_rect)
    pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"],  backdrop_rect, 2)

    # --- Scroll state ---
    total_packages = len(config.CARE_PACKAGES)
    visible_start  = state.package_button_visible_start_index
    per_page       = max(1, gui_core.get_buttons_per_page())
    visible_end    = min(visible_start + per_page, total_packages)

    can_scroll_left  = visible_start > 0
    can_scroll_right = visible_end < total_packages

    left_color  = config.SCROLL_BUTTON_COLOR_DISABLED if not can_scroll_left  or is_input_locked else config.SCROLL_BUTTON_COLOR_ENABLED
    right_color = config.SCROLL_BUTTON_COLOR_DISABLED if not can_scroll_right or is_input_locked else config.SCROLL_BUTTON_COLOR_ENABLED

    # --- Scroll buttons ---
    pygame.draw.rect(screen, left_color,  left_rect)
    pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], left_rect,  2)
    pygame.draw.rect(screen, right_color, right_rect)
    pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], right_rect, 2)

    # --- Package buttons ---
    for i in range(int(visible_start), int(visible_end)):
        package_info = config.CARE_PACKAGES[i]
        color_name   = package_info["color"]
        base_color   = state.game_theme_colors["package_colors"][color_name]
        btn_color    = config.PACKAGE_BUTTON_COLOR_DISABLED(base_color) if is_input_locked else base_color
        btn_rect     = _get_btn_rect(i, visible_start, left_rect, area_rect)

        pygame.draw.rect(screen, btn_color, btn_rect)
        pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], btn_rect, 2)

        number_text = str(i + 1)

        if font is not None:
            # Outline (debossed look)
            outline_surf = font.render(number_text, True, state.game_theme_colors["contrast_color"])
            outline_rect = outline_surf.get_rect(center=btn_rect.center)
            for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                screen.blit(outline_surf, (outline_rect.x + dx, outline_rect.y + dy))

            # Main number
            text_surf = font.render(number_text, True, state.game_theme_colors["original_pet_color"])
            screen.blit(text_surf, text_surf.get_rect(center=btn_rect.center))

        # --- Hover info panel ---
        identifier = f"package_{i}"
        if identifier == state.hovered_package_identifier:
            pygame.draw.rect(screen, base_color, btn_rect, 2)

            info_w    = backdrop_rect.width - 3
            info_h    = backdrop_h * 2
            info_x    = backdrop_rect.left
            info_y    = backdrop_rect.top - info_h
            info_rect = pygame.Rect(info_x, info_y, info_w, info_h)

            pygame.draw.rect(screen, state.game_theme_colors["contrast_color"],     info_rect)
            pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], info_rect, 2)

            if font is not None and "package" in package_info and package_info["package"]:
                state.highlight_items_list = [
                    item['name'].title() for item in package_info["package"]
                ]

                text_x       = info_x + 8
                text_y       = info_y + 8
                line_h       = font.get_height() + 2
                avail_h      = info_h - 16
                max_visible  = avail_h // line_h
                total_items  = len(state.highlight_items_list)

                scroll_offset = int(state.package_scroll_y // 10)
                start_idx     = max(0, min(scroll_offset, total_items - max_visible))
                end_idx       = min(start_idx + max_visible, total_items)

                can_up   = start_idx > 0
                can_down = end_idx < total_items
                tri_size = 8
                tri_margin = 4
                tri_color  = state.game_theme_colors["original_pet_color"]
                tri_cx     = info_x + info_w - tri_size - tri_margin

                if can_up:
                    ty = info_y + tri_margin
                    pygame.draw.polygon(screen, tri_color, [
                        (tri_cx, ty), (tri_cx - tri_size//2, ty + tri_size),
                        (tri_cx + tri_size//2, ty + tri_size),
                    ])
                if can_down:
                    ty = info_y + info_h - tri_margin
                    pygame.draw.polygon(screen, tri_color, [
                        (tri_cx, ty), (tri_cx - tri_size//2, ty - tri_size),
                        (tri_cx + tri_size//2, ty - tri_size),
                    ])

                max_text_w = info_w - 32
                line_color = state.game_theme_colors["original_pet_color"]

                for idx in range(start_idx, end_idx):
                    item_name  = state.highlight_items_list[idx]
                    name_surf  = font.render(item_name, True, line_color)

                    if name_surf.get_width() > max_text_w:
                        for cut in range(len(item_name), 0, -1):
                            trunc = item_name[:cut] + "..."
                            test  = font.render(trunc, True, line_color)
                            if test.get_width() <= max_text_w:
                                name_surf = test
                                break

                    screen.blit(name_surf, (text_x, text_y))
                    pygame.draw.line(
                        screen, line_color,
                        (text_x, text_y + line_h - 1),
                        (info_x + info_w - 8, text_y + line_h - 1),
                    )
                    text_y += line_h

            # Re-draw number on top of hover panel (original did this twice)
            if font is not None:
                outline_surf = font.render(number_text, True, state.game_theme_colors["contrast_color"])
                outline_rect = outline_surf.get_rect(center=btn_rect.center)
                for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                    screen.blit(outline_surf, (outline_rect.x + dx, outline_rect.y + dy))
                text_surf = font.render(number_text, True, state.game_theme_colors["original_pet_color"])
                screen.blit(text_surf, text_surf.get_rect(center=btn_rect.center))


# ---------------------------------------------------------------------------
# Click regions
# ---------------------------------------------------------------------------

def get_package_button_click_regions() -> list:
    """
    Return a list of (identifier, rect) tuples for all clickable elements
    in the care-package row.  Input-lock checking is the caller's job.
    """
    cp_rects = gui_core.get_care_package_rects()
    if not cp_rects:
        return []

    left_rect = cp_rects["left_scroll"]
    area_rect = cp_rects["area"]
    regions   = [
        ("scroll_left",  left_rect),
        ("scroll_right", cp_rects["right_scroll"]),
    ]

    total_packages = len(config.CARE_PACKAGES)
    visible_start  = state.package_button_visible_start_index
    per_page       = max(1, gui_core.get_buttons_per_page())
    visible_end    = min(visible_start + per_page, total_packages)

    for i in range(int(visible_start), int(visible_end)):
        regions.append((f"package_{i}", _get_btn_rect(i, visible_start, left_rect, area_rect)))

    return regions


# ---------------------------------------------------------------------------
# Scroll info for hover panel
# ---------------------------------------------------------------------------

def get_package_scroll_info() -> dict:
    """
    Return scroll metadata for the currently hovered package hover panel.
    """
    font = gui_core.get_font()
    if (
        not state.hovered_package_identifier
        or not hasattr(state, 'highlight_items_list')
        or font is None
    ):
        return {'line_height': 0, 'max_scroll': 0, 'total_items': 0, 'max_visible_lines': 0}

    line_h       = font.get_height() + 2
    backdrop_h   = config.INPUT_HEIGHT + 3
    avail_h      = (backdrop_h * 2) - 16
    max_visible  = avail_h // line_h
    total_items  = len(state.highlight_items_list)
    max_scroll   = max(0, (total_items - max_visible) * line_h)

    return {
        'line_height':      line_h,
        'max_scroll':       max_scroll,
        'total_items':      total_items,
        'max_visible_lines': max_visible,
    }