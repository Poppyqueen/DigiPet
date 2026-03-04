# gui_clock.py

import pygame
from pygame_int import state
from pygame_int import config
from pygame_int.main_digipet import gui_core
from utils.loc_datetime import datetime
from datetime import timedelta


COLLAPSE_HEIGHT_THRESHOLD = 20


# ---------------------------------------------------------------------------
# Sleep countdown update  (call from the game loop's update phase, not draw)
# ---------------------------------------------------------------------------

def update_sleep_countdown() -> None:
    """
    Decrement state.time_to_sleep by 1 each second.
    Call once per frame from the update phase, not from a draw function.
    """
    if not state.agent_sleeping or state.time_to_sleep is None:
        return

    current_time = pygame.time.get_ticks()
    if not hasattr(state, 'sleep_countdown_last_tick'):
        state.sleep_countdown_last_tick = current_time

    if current_time - state.sleep_countdown_last_tick >= 1000:
        state.time_to_sleep             -= 1
        state.sleep_countdown_last_tick  = current_time


# ---------------------------------------------------------------------------
# Click handling
# ---------------------------------------------------------------------------

def handle_clock_click(mouse_pos) -> bool:
    """
    Toggle state.clock_expanded when either clock rect is clicked.
    Marks layout dirty and triggers an immediate recalculation.
    Returns True if a clock was clicked.
    """
    clock_rects = gui_core.get_clock_rects()
    ct_rect     = clock_rects.get("current_time")
    sd_rect     = clock_rects.get("sleep_duration")

    clicked = (
        (ct_rect and ct_rect.collidepoint(mouse_pos))
        or (state.agent_sleeping and sd_rect and sd_rect.collidepoint(mouse_pos))
    )

    if clicked:
        state.clock_expanded = not state.clock_expanded
        gui_core.mark_layout_dirty()
        gui_core.update_gui_rects(state.panel_width)
        return True

    return False


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def draw_current_time(screen: pygame.Surface) -> None:
    """Draw the current time clock widget."""
    font        = gui_core.get_font()
    clock_rects = gui_core.get_clock_rects()
    container   = clock_rects.get("current_time")

    if container is None or font is None:
        return

    try:
        is_collapsed = container.height < COLLAPSE_HEIGHT_THRESHOLD

        now      = datetime.now()
        time_str = now.strftime("%I:%M %p")

        fg = state.game_theme_colors.get("original_pet_color", (255, 255, 255))
        bg = state.game_theme_colors.get("contrast_color",     (0,   0,   0))

        text_surf = font.render(time_str, True, fg)
        btn_width = text_surf.get_width() + 20
        btn_rect  = pygame.Rect(0, 0, btn_width, container.height)
        btn_rect.right   = container.right
        btn_rect.centery = container.centery

        border_rect = btn_rect.inflate(4, 4).clip(screen.get_rect())
        pygame.draw.rect(screen, fg, border_rect)
        pygame.draw.rect(screen, bg, btn_rect)

        if is_collapsed:
            grip = pygame.Rect(0, 0, 20, 2)
            grip.center = btn_rect.center
            pygame.draw.rect(screen, fg, grip)
        else:
            screen.blit(text_surf, text_surf.get_rect(center=btn_rect.center))

    except pygame.error as e:
        print(f"[gui_clock] Error rendering current time: {e}")


def draw_sleep_duration(screen: pygame.Surface) -> None:
    """Draw the sleep-countdown clock widget (only while agent is sleeping)."""
    if not state.agent_sleeping:
        return
    if state.time_to_sleep is None:
        print("[gui_clock] No time_to_sleep set — skipping sleep duration draw.")
        return

    font        = gui_core.get_font()
    clock_rects = gui_core.get_clock_rects()
    container   = clock_rects.get("sleep_duration")

    if container is None or font is None:
        return

    try:
        if container.height < COLLAPSE_HEIGHT_THRESHOLD:
            return

        sleep_str = f"Sleep: {str(timedelta(seconds=int(state.time_to_sleep)))}"
        fg = state.game_theme_colors.get("original_pet_color", (255, 255, 255))
        bg = state.game_theme_colors.get("contrast_color",     (0,   0,   0))

        text_surf = font.render(sleep_str, True, fg)
        btn_width = text_surf.get_width() + 20
        btn_rect  = pygame.Rect(0, 0, btn_width, container.height)
        btn_rect.right   = container.right
        btn_rect.centery = container.centery

        border_rect = btn_rect.inflate(4, 4)
        pygame.draw.rect(screen, fg, border_rect)
        pygame.draw.rect(screen, bg, btn_rect)
        screen.blit(text_surf, text_surf.get_rect(center=btn_rect.center))

    except pygame.error as e:
        print(f"[gui_clock] Error rendering sleep duration: {e}")