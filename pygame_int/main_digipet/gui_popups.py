# gui_popups.py

import pygame
import random
from pygame_int import config
from pygame_int import state
from pygame_int.main_digipet import gui_core


# ---------------------------------------------------------------------------
# Text popup
# ---------------------------------------------------------------------------

class PopupMessage:
    """A single floating text pop-up."""
    def __init__(self, text_surface, initial_pos, start_time):
        self.text_surface = text_surface
        self.initial_pos  = initial_pos
        self.start_time   = start_time
        self.current_pos  = list(initial_pos)


# ---------------------------------------------------------------------------
# Image popup
# ---------------------------------------------------------------------------

class ImagePopup:
    """
    A timed image overlay.

    Parameters
    ----------
    clock_height_offset : int
        Pre-calculated pixel offset below the top of the screen where a
        type-1 (top-right icon) popup should appear.  Computed by the
        caller from gui_core.get_clock_rects() so this class stays
        free of gui_core coupling.
    """

    def __init__(
        self,
        image_path: str,
        duration_ms: int,
        fade_in_ms: int,
        fade_out_ms: int,
        popup_type: int,
        screen_width: int,
        screen_height: int,
        panel_width: int,
        clock_height_offset: int = 0,
    ):
        self.image_path         = image_path
        self.duration           = duration_ms
        self.fade_in_duration   = max(0, fade_in_ms)
        self.fade_out_duration  = max(0, fade_out_ms)
        self.type               = popup_type
        self.visible            = False
        self.image_surface      = None
        self.display_area       = None
        self.start_time         = 0
        self.background_surface = None

        main_display_width = screen_width - panel_width

        if popup_type == 0:
            popup_size = (200, 200)
            self.display_area = pygame.Rect(0, 0, *popup_size)
            self.display_area.center = (screen_width // 2, screen_height // 2)
            try:
                self.background_surface = pygame.Surface(
                    (screen_width, screen_height), pygame.SRCALPHA
                )
                self.background_surface.fill((0, 0, 0, 128))
            except pygame.error as e:
                print(f"[gui_popups] Could not create splash background: {e}")
                self.background_surface = None

        elif popup_type == 1:
            popup_size = (60, 60)
            self.display_area = pygame.Rect(0, 0, *popup_size)
            self.display_area.topright = (main_display_width, clock_height_offset)

        elif popup_type == 2:
            popup_size = (150, 150)
            self.display_area = pygame.Rect(0, 0, *popup_size)
            self.display_area.center = (main_display_width // 2, screen_height // 2)

        else:
            popup_size = (200, 200)
            self.display_area = pygame.Rect(0, 0, *popup_size)
            self.display_area.center = (screen_width // 2, screen_height // 2)

        if self.duration <= 0:
            print(f"[gui_popups] duration_ms must be positive for '{image_path}'. Skipping.")
            return

        try:
            raw   = pygame.image.load(image_path)
            self.image_surface = pygame.transform.scale(
                raw, self.display_area.size
            ).convert_alpha()
            self.visible    = True
            self.start_time = pygame.time.get_ticks()
            print(
                f"[gui_popups] Image popup '{image_path}' (type {popup_type}) created. "
                f"Duration: {duration_ms}ms, FadeIn: {fade_in_ms}ms, FadeOut: {fade_out_ms}ms"
            )
        except FileNotFoundError:
            print(f"[gui_popups] Image not found: '{image_path}'")
        except (pygame.error, Exception) as e:
            print(f"[gui_popups] Error loading '{image_path}': {e}")


# Active image popups keyed by type int.
_active_image_popups: dict = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def show_popup_message(text, color=None, raw=False) -> None:
    """Create a floating text pop-up and add it to state.active_popups."""
    font = gui_core.get_font()
    if font is None:
        print("[gui_popups] show_popup_message called before font is initialised.")
        return
    if not text or not text.strip():
        return

    border_color = (0, 0, 0)
    if not raw:
        if not color:
            color = state.game_theme_colors["contrast_color"]
        border_color = state.game_theme_colors.get("original_pet_color", (255, 255, 255))

    border_px = 1

    try:
        main_surf   = font.render(text.strip(), True, color)
        border_surf = font.render(text.strip(), True, border_color)

        w = main_surf.get_width()  + 2 * border_px
        h = main_surf.get_height() + 2 * border_px
        combined = pygame.Surface((w, h), pygame.SRCALPHA)

        for dx, dy in [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]:
            combined.blit(border_surf, (border_px + dx, border_px + dy))
        combined.blit(main_surf, (border_px, border_px))

    except (pygame.error, Exception) as e:
        print(f"[gui_popups] Error rendering popup '{text}': {e}")
        return

    cx = config.get_base_circle_center_x(state.panel_width if state.panel_visible else 0)
    pos_x = cx - combined.get_width() // 2
    pos_y = config.BASE_CIRCLE_CENTER_Y + config.POPUP_INITIAL_OFFSET_Y - border_px

    pos_x += random.uniform(-config.POPUP_RANDOM_SPREAD_X, config.POPUP_RANDOM_SPREAD_X)
    pos_y += random.uniform(-config.POPUP_RANDOM_SPREAD_Y, config.POPUP_RANDOM_SPREAD_Y)

    state.active_popups.append(
        PopupMessage(combined, (pos_x, pos_y), pygame.time.get_ticks())
    )


def show_image_popup(
    image_path: str,
    duration_ms: int = 2000,
    fade_in_ms: int = 500,
    fade_out_ms: int = 500,
    popup_type: int = 1,
) -> None:
    """
    Create a timed image popup.

    Calculates the clock-height offset here (from gui_core.get_clock_rects())
    and passes it to ImagePopup as a plain value so the constructor stays
    free of gui_core coupling.
    """
    surface = pygame.display.get_surface()
    if surface is None:
        print("[gui_popups] Pygame display not initialised. Cannot show image popup.")
        return

    screen_w   = surface.get_width()
    screen_h   = surface.get_height()
    panel_w    = state.panel_width if state.panel_visible else 0

    # Compute how far below the top the type-1 popup should sit.
    clock_height_offset = config.PADDING
    if popup_type == 1:
        clock_rects = gui_core.get_clock_rects()
        ct_rect     = clock_rects.get("current_time")
        sd_rect     = clock_rects.get("sleep_duration")
        if ct_rect is not None:
            clock_height_offset += ct_rect.height
        if sd_rect is not None:
            clock_height_offset += sd_rect.height

    popup = ImagePopup(
        image_path, duration_ms, fade_in_ms, fade_out_ms, popup_type,
        screen_w, screen_h, panel_w,
        clock_height_offset=clock_height_offset,
    )
    if popup.visible:
        _active_image_popups[popup_type] = popup
    else:
        print(f"[gui_popups] Failed to create image popup: '{image_path}', type {popup_type}")


def is_any_image_popup_currently_active() -> bool:
    """Return True if at least one image popup is still visible."""
    current_time = pygame.time.get_ticks()
    for popup in _active_image_popups.values():
        if not popup.visible:
            continue
        elapsed    = current_time - popup.start_time
        remaining  = (popup.start_time + popup.duration) - current_time

        alpha = 255
        if popup.fade_in_duration > 0 and elapsed < popup.fade_in_duration:
            alpha = int(elapsed / popup.fade_in_duration * 255)
        elif popup.fade_out_duration > 0 and 0 < remaining <= popup.fade_out_duration:
            alpha = int(remaining / popup.fade_out_duration * 255)
        elif remaining <= 0:
            alpha = 0

        if alpha > 0:
            return True
    return False


def update_popups(current_time_ms: int) -> None:
    """Advance all active text and image popups; remove expired ones."""
    # Text popups
    for i in range(len(state.active_popups) - 1, -1, -1):
        popup    = state.active_popups[i]
        elapsed  = current_time_ms - popup.start_time
        progress = min(1.0, elapsed / config.POPUP_DURATION_MS)

        if progress >= 1.0:
            state.active_popups.pop(i)
            continue

        popup.current_pos[1] = popup.initial_pos[1] - progress * config.POPUP_MOVE_DISTANCE_Y
        popup.text_surface.set_alpha(int(255 * (1.0 - progress)))

    # Image popups
    for popup_type in list(_active_image_popups):
        popup = _active_image_popups[popup_type]
        if popup.visible and current_time_ms >= popup.start_time + popup.duration:
            popup.visible = False


def clear_all_popups() -> None:
    """Remove all active text and image popups."""
    state.active_popups.clear()
    _active_image_popups.clear()


def draw_popups(screen: pygame.Surface) -> None:
    """Draw all active floating text popups."""
    for popup in state.active_popups:
        if popup.text_surface.get_alpha() > 0:
            screen.blit(popup.text_surface, popup.current_pos)


def draw_active_image_popups(screen: pygame.Surface) -> None:
    """Draw all active image popups with fade-in/out."""
    current_time = pygame.time.get_ticks()

    # Draw type-0 splash background first.
    if 0 in _active_image_popups:
        p = _active_image_popups[0]
        if p.visible and p.background_surface and state.is_initial_popup_phase:
            screen.blit(p.background_surface, (0, 0))

    for popup in _active_image_popups.values():
        if not (popup.visible and popup.image_surface and popup.display_area):
            continue

        elapsed   = current_time - popup.start_time
        remaining = (popup.start_time + popup.duration) - current_time

        alpha = 255
        if popup.fade_in_duration > 0 and elapsed < popup.fade_in_duration:
            alpha = int(elapsed / popup.fade_in_duration * 255)
        elif popup.fade_out_duration > 0 and 0 < remaining <= popup.fade_out_duration:
            alpha = int(remaining / popup.fade_out_duration * 255)
        elif remaining <= 0:
            alpha = 0

        alpha = max(0, min(255, alpha))
        if alpha > 0:
            popup.image_surface.set_alpha(alpha)
            screen.blit(popup.image_surface, popup.display_area.topleft)