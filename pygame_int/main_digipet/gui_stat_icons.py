# gui_stat_icons.py

import pygame
from pygame_int import config
from pygame_int import state
from pygame_int.main_digipet import gui_core


# Module-level dict of icon rects for collision detection.
_stat_icon_rects = {}


def get_stat_icon_rects() -> dict:
    """Return a copy of the current stat icon rects for hit-testing."""
    return _stat_icon_rects.copy()


def _get_stat_level(value) -> str:
    """Map a stat value (0–200) to 'full', 'half', or 'empty'."""
    clamped = max(0.0, min(200.0, value))
    if clamped >= config.STAT_THRESHOLDS['full']:
        return 'full'
    elif clamped >= config.STAT_THRESHOLDS['half']:
        return 'half'
    else:
        return 'empty'


def update_stat_icon_rects() -> None:
    """
    Recalculate icon rects from config positions.
    Called by gui_core.init_gui_elements and whenever layout changes.
    """
    global _stat_icon_rects

    stats_order    = ["fullness", "hydration", "energy"]
    icon_w, icon_h = config.STAT_ICON_SIZE
    spacing        = config.STAT_ICON_SPACING_Y

    _stat_icon_rects.clear()
    for i, stat_name in enumerate(stats_order):
        y = config.STAT_ICON_START_Y_SCREEN + i * (icon_h + spacing)
        _stat_icon_rects[stat_name] = pygame.Rect(
            config.STAT_ICON_START_X_SCREEN, y, icon_w, icon_h
        )


def draw_stat_icons(screen: pygame.Surface) -> None:
    """
    Draw all stat icons.  If a stat is hovered (state.hover_stat) draw its
    current value beside the icon.
    Call update_stat_icon_rects() at init and on layout changes — not here.
    """

    font      = gui_core.get_font()
    icons     = gui_core.get_stat_icons()
    stats_order = ["fullness", "hydration", "energy"]

    for stat_name in stats_order:
        stat_value = state.pet_stats.get(stat_name, 0)
        stat_level = _get_stat_level(stat_value)
        icon_surface = icons.get((stat_name, stat_level))

        if icon_surface and stat_name in _stat_icon_rects:
            rect = _stat_icon_rects[stat_name]
            screen.blit(icon_surface, (rect.x, rect.y))

            if hasattr(state, 'hover_stat') and state.hover_stat == stat_name and font is not None:
                try:
                    value_text  = f"{stat_value:.1f}"
                    text_color  = state.game_theme_colors.get('contrast_color', config.WHITE)
                    text_surface = font.render(value_text, True, text_color)

                    text_x = rect.right + 10
                    text_y = rect.centery - text_surface.get_height() // 2

                    bg_color   = state.game_theme_colors.get('original_pet_color', config.BLACK)
                    bg_rect    = pygame.Rect(
                        text_x - 2, text_y - 2,
                        text_surface.get_width() + 4,
                        text_surface.get_height() + 4,
                    )
                    bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
                    bg_surface.set_alpha(128)
                    bg_surface.fill(bg_color)
                    screen.blit(bg_surface,  (bg_rect.x, bg_rect.y))
                    screen.blit(text_surface, (text_x, text_y))

                except pygame.error as e:
                    print(f"[gui_stat_icons] Pygame error rendering hover text: {e}")