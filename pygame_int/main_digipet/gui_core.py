# gui_core.py
#
# Responsibilities
# ----------------
# 1. Store the font and layout geometry used by all gui_* submodules.
# 2. Calculate (and cache) every pygame.Rect the GUI needs.
# 3. Expose state through public getters — no private underscore access from outside.
#    Call mark_layout_dirty() whenever a structural change occurs (panel toggle, resize, etc.)

import pygame
import os

from pygame_int import config
from pygame_int import state
from pygame_int.main_digipet import gui_construct_colors
from pygame_int.main_digipet import gui_stat_icons


# ---------------------------------------------------------------------------
# Private module-level state
# (Use the public getters below — do not access these with _ from outside)
# ---------------------------------------------------------------------------

_font        = None
_line_height = 0

# Dirty flag — set to True whenever layout needs recalculating.
# update_gui_rects() resets it to False after recalculating.
_layout_dirty = True

_overlay_surface = None  # SRCALPHA surface for the time-of-day colour filter

# --- Panel rects ---
_panel_rect           = None
_history_rect         = None
_input_rect           = None
_history_display_area = None
_text_width_limit     = 0

# --- Inventory modal rects ---
_inventory_toggle_button_rect    = None
_inventory_panel_rect            = None
_room_list_area_rect             = None
_player_list_area_rect           = None
_room_title_rect                 = None
_player_title_rect               = None
_inventory_item_draw_width       = 0
_inventory_item_start_x_offset   = 0

# --- Care package rects ---
_care_package_area_rect   = None
_left_scroll_button_rect  = None
_right_scroll_button_rect = None
_buttons_per_page         = 0

# --- Utility buttons ---
_mute_button_rect         = None
_panel_toggle_button_rect = None

# --- Lore panel rects ---
_lore_panel_rect              = None
_lore_panel_title_rect        = None
_lore_panel_body_area_rect    = None
_lore_panel_close_button_rect = None
_lore_panel_text_draw_width   = 0
_lore_panel_text_start_x_offset = 0
_lore_toggle_button_rect      = None

# --- Clock rects ---
_current_time_clock_rect  = None
_sleep_duration_clock_rect = None

# --- Stat icons (loaded once at init) ---
_stat_icons = {}


# ---------------------------------------------------------------------------
# Public getters  (the only way outside modules should read internal state)
# ---------------------------------------------------------------------------

def get_font() -> pygame.font.Font:
    """Return the shared font used throughout the GUI."""
    return _font


def get_line_height() -> int:
    """Return the line height that matches the shared font."""
    return _line_height


def get_buttons_per_page() -> int:
    """Return how many care-package buttons fit in the current layout."""
    return _buttons_per_page


def get_button_rects() -> dict:
    """Return named rects for every clickable button."""
    rects = {}
    if _inventory_toggle_button_rect is not None:
        rects["inventory_toggle"]    = _inventory_toggle_button_rect
    if _mute_button_rect is not None:
        rects["mute_button"]         = _mute_button_rect
    if _panel_toggle_button_rect is not None:
        rects["panel_toggle"]        = _panel_toggle_button_rect
    if _lore_toggle_button_rect is not None:
        rects["lore_toggle"]         = _lore_toggle_button_rect
    if _current_time_clock_rect is not None:
        rects["current_time_clock"]  = _current_time_clock_rect
    if _sleep_duration_clock_rect is not None:
        rects["sleep_duration_clock"] = _sleep_duration_clock_rect
    return rects


def get_panel_rects() -> dict:
    """Return rects for the inventory modal panel and all its inner areas."""
    if _inventory_panel_rect is None:
        return {}
    return {
        "inventory_panel":  _inventory_panel_rect,
        "room_list_area":   _room_list_area_rect,
        "player_list_area": _player_list_area_rect,
        "room_title":       _room_title_rect,
        "player_title":     _player_title_rect,
    }


def get_care_package_rects() -> dict:
    """Return rects for the care-package button row."""
    if _left_scroll_button_rect is None:
        return {}
    return {
        "left_scroll":  _left_scroll_button_rect,
        "right_scroll": _right_scroll_button_rect,
        "area":         _care_package_area_rect,
    }


def get_clock_rects() -> dict:
    """Return rects for the clock widgets."""
    return {
        "current_time":   _current_time_clock_rect,
        "sleep_duration": _sleep_duration_clock_rect,
    }


def get_stat_icons() -> dict:
    """Return the loaded stat icon surfaces, keyed by (stat_name, level)."""
    return _stat_icons


def get_text_width_limit() -> int:
    """Return the max pixel width for a line of chat history text."""
    return _text_width_limit


def get_inventory_item_draw_width() -> int:
    """Return the pixel width available for one inventory item line."""
    return _inventory_item_draw_width


def get_inventory_item_start_x_offset() -> int:
    """Return the x offset from list-area left where item text begins."""
    return _inventory_item_start_x_offset


def get_lore_panel_text_draw_width() -> int:
    """Return the pixel width available for lore body text lines."""
    return _lore_panel_text_draw_width


def get_lore_panel_text_start_x_offset() -> int:
    """Return the x offset from body-area left where lore text begins."""
    return _lore_panel_text_start_x_offset


def get_gui_rects() -> dict:
    """Return rects for the main side panel (chat history, input box)."""
    return {
        "panel_rect":           _panel_rect,
        "history_rect":         _history_rect,
        "input_rect":           _input_rect,
        "history_display_area": _history_display_area,
    }


def get_lore_panel_rects() -> dict:
    """Return rects for the full-screen lore/info panel."""
    if _lore_panel_rect is None:
        return {}
    return {
        "lore_panel":       _lore_panel_rect,
        "lore_title_area":  _lore_panel_title_rect,
        "lore_body_area":   _lore_panel_body_area_rect,
        "lore_close_button": _lore_panel_close_button_rect,
    }


def get_overlay_surface() -> pygame.Surface:
    """Return the SRCALPHA overlay surface used for the time-of-day colour filter."""
    return _overlay_surface


# ---------------------------------------------------------------------------
# Dirty-flag helper
# Call this whenever a structural change makes layout recalculation necessary.
# ---------------------------------------------------------------------------

def mark_layout_dirty() -> None:
    """
    Signal that layout geometry must be recalculated on the next frame.

    Call this from anywhere that changes a value update_gui_rects() depends on:
      - panel_visible toggled
      - panel_width changed
      - window resized
    """
    global _layout_dirty
    _layout_dirty = True


# ---------------------------------------------------------------------------
# One-time initialisation
# ---------------------------------------------------------------------------

def init_gui_elements(font: pygame.font.Font, line_height: int, initial_panel_width: int) -> None:
    """
    Initialise the GUI module.  Call once at startup before the game loop.

    Sets up the font, overlay surface, and stat icons — things that only
    need to happen once.  All rect geometry is delegated to update_gui_rects()
    so there is a single source of truth for every rect formula.
    """
    global _font, _line_height, _overlay_surface, _layout_dirty

    _font        = font
    _line_height = line_height

    # Overlay surface for the time-of-day colour filter (needs display to exist).
    display = pygame.display.get_surface()
    sw = display.get_width()  if display else config.WIDTH
    sh = display.get_height() if display else config.HEIGHT
    _overlay_surface = pygame.Surface((sw, sh), pygame.SRCALPHA)

    # Load stat icon images — done once, stored in _stat_icons.
    _load_stat_icons()
    gui_stat_icons.update_stat_icon_rects()

    # Force a full layout calculation with the initial panel width.
    _layout_dirty = True
    update_gui_rects(initial_panel_width)

    print("GUI Core initialised.")


# ---------------------------------------------------------------------------
# Layout calculation  (single source of truth for every rect)
# ---------------------------------------------------------------------------

def update_gui_rects(current_panel_width: int) -> None:
    """
    Recalculate all layout rects for the given panel width.

    Guarded by _layout_dirty: if nothing structural has changed since the
    last call, this returns immediately without doing any work.

    Call mark_layout_dirty() before this whenever layout inputs change.
    draw_gui() calls this once per frame; the guard makes that free when
    nothing has changed.
    """
    global _layout_dirty
    if not _layout_dirty:
        return

    _recalculate_all_rects(current_panel_width)
    _layout_dirty = False


def _recalculate_all_rects(current_panel_width: int) -> None:
    """
    Internal: perform the actual rect calculations.
    Broken out from update_gui_rects() so the dirty-flag logic stays clean.
    """
    global _panel_rect, _history_rect, _input_rect, _history_display_area, _text_width_limit
    global _inventory_toggle_button_rect, _mute_button_rect, _panel_toggle_button_rect
    global _inventory_panel_rect, _room_title_rect, _player_title_rect
    global _room_list_area_rect, _player_list_area_rect
    global _inventory_item_draw_width, _inventory_item_start_x_offset
    global _care_package_area_rect, _left_scroll_button_rect, _right_scroll_button_rect, _buttons_per_page
    global _lore_panel_rect, _lore_panel_title_rect, _lore_panel_body_area_rect
    global _lore_panel_close_button_rect, _lore_panel_text_draw_width, _lore_panel_text_start_x_offset
    global _lore_toggle_button_rect
    global _current_time_clock_rect, _sleep_duration_clock_rect

    # ------------------------------------------------------------------
    # Side panel (chat history + input box)
    # ------------------------------------------------------------------
    _panel_rect = pygame.Rect(
        config.WIDTH - current_panel_width, 0,
        current_panel_width, config.HEIGHT
    )
    _input_rect = pygame.Rect(
        config.WIDTH - current_panel_width + config.PADDING,
        config.HEIGHT - config.INPUT_HEIGHT - config.PADDING,
        current_panel_width - 2 * config.PADDING,
        config.INPUT_HEIGHT,
    )
    _history_rect = pygame.Rect(
        config.WIDTH - current_panel_width + config.PADDING,
        config.PADDING,
        current_panel_width - 2 * config.PADDING,
        config.HEIGHT - config.INPUT_HEIGHT - 3 * config.PADDING,
    )
    _history_display_area = pygame.Rect(
        _history_rect.left  + config.HISTORY_HORIZONTAL_PADDING,
        _history_rect.top   + config.PADDING,
        _history_rect.width - 2 * config.HISTORY_HORIZONTAL_PADDING,
        _history_rect.height - 2 * config.PADDING,
    )
    _text_width_limit = max(1, _history_display_area.width)

    # ------------------------------------------------------------------
    # Mute button
    # ------------------------------------------------------------------
    sz = config.MUTE_BUTTON_SIZE
    _mute_button_rect = pygame.Rect(
        config.MUTE_BUTTON_POS_X - sz // 2,
        config.MUTE_BUTTON_POS_Y - sz // 2,
        sz, sz,
    )

    # ------------------------------------------------------------------
    # Inventory toggle button (small dot, bottom-left)
    # ------------------------------------------------------------------
    bsz = config.INVENTORY_TOGGLE_BUTTON_SIZE
    _inventory_toggle_button_rect = pygame.Rect(
        config.INVENTORY_TOGGLE_BUTTON_POS_X - bsz // 2,
        config.INVENTORY_TOGGLE_BUTTON_POS_Y - bsz // 2,
        bsz, bsz,
    )

    # ------------------------------------------------------------------
    # Inventory modal panel + inner rects
    # ------------------------------------------------------------------
    visible_panel_width = current_panel_width if state.panel_visible else 0
    _inventory_panel_rect = config.get_inventory_panel_rect(visible_panel_width)

    ip_x = _inventory_panel_rect.left  + config.INVENTORY_PANEL_PADDING
    ip_y = _inventory_panel_rect.top   + config.INVENTORY_PANEL_PADDING
    ip_w = _inventory_panel_rect.width  - 2 * config.INVENTORY_PANEL_PADDING
    ip_h = _inventory_panel_rect.height - 2 * config.INVENTORY_PANEL_PADDING

    title_h    = config.INVENTORY_PANEL_TITLE_HEIGHT
    half_w     = (ip_w - config.INVENTORY_PANEL_DIVIDER_WIDTH) // 2
    list_area_y = ip_y + title_h
    list_area_h = ip_h - title_h

    _room_title_rect = pygame.Rect(ip_x,                                        ip_y, half_w, title_h)
    _player_title_rect = pygame.Rect(ip_x + half_w + config.INVENTORY_PANEL_DIVIDER_WIDTH, ip_y, half_w, title_h)
    _room_list_area_rect   = pygame.Rect(ip_x,                                        list_area_y, half_w, list_area_h)
    _player_list_area_rect = pygame.Rect(ip_x + half_w + config.INVENTORY_PANEL_DIVIDER_WIDTH, list_area_y, half_w, list_area_h)

    _inventory_item_draw_width     = max(1, _room_list_area_rect.width - 2 * config.INVENTORY_PANEL_ITEM_HORIZONTAL_PADDING)
    _inventory_item_start_x_offset = config.INVENTORY_PANEL_ITEM_HORIZONTAL_PADDING

    # ------------------------------------------------------------------
    # Care package buttons row
    # ------------------------------------------------------------------
    game_area_width = config.WIDTH - (current_panel_width if state.panel_visible else 0)
    btn_row_top     = config.HEIGHT - config.PADDING - config.INPUT_HEIGHT
    max_btn_area_w  = (
        game_area_width
        - config.SCROLL_BUTTON_WIDTH * 2
        - config.PADDING * 3
        - config.INVENTORY_TOGGLE_BUTTON_SIZE
    )

    btn_step = config.PACKAGE_BUTTON_WIDTH + config.PACKAGE_BUTTON_SPACING_X
    _buttons_per_page = max(1, int(max_btn_area_w // btn_step) if btn_step > 0 else 1)

    actual_btn_area_w = max(
        0,
        _buttons_per_page * config.PACKAGE_BUTTON_WIDTH
        + max(0, _buttons_per_page - 1) * config.PACKAGE_BUTTON_SPACING_X,
    )

    _left_scroll_button_rect = pygame.Rect(
        config.PADDING + config.INVENTORY_TOGGLE_BUTTON_SIZE + config.PADDING,
        btn_row_top,
        config.SCROLL_BUTTON_WIDTH,
        config.SCROLL_BUTTON_HEIGHT,
    )
    _care_package_area_rect = pygame.Rect(
        _left_scroll_button_rect.right + config.PACKAGE_BUTTON_SPACING_X,
        btn_row_top,
        actual_btn_area_w,
        config.PACKAGE_BUTTON_HEIGHT,
    )
    _right_scroll_button_rect = pygame.Rect(
        _care_package_area_rect.right + config.PACKAGE_BUTTON_SPACING_X,
        btn_row_top,
        config.SCROLL_BUTTON_WIDTH,
        config.SCROLL_BUTTON_HEIGHT,
    )

    # ------------------------------------------------------------------
    # Panel toggle button (arrow on the panel edge)
    # ------------------------------------------------------------------
    tw, th = config.PANEL_TOGGLE_BUTTON_SIZE
    if state.panel_visible:
        toggle_x = config.WIDTH - current_panel_width - tw
    else:
        toggle_x = config.WIDTH - tw - config.PADDING
    _panel_toggle_button_rect = pygame.Rect(
        toggle_x,
        config.HEIGHT // 2 - th // 2,
        tw, th,
    )

    # ------------------------------------------------------------------
    # Lore panel (full-screen overlay)
    # ------------------------------------------------------------------
    _lore_panel_rect = pygame.Rect(0, 0, config.WIDTH, config.HEIGHT)

    lp_x = _lore_panel_rect.left  + config.LORE_PANEL_PADDING
    lp_y = _lore_panel_rect.top   + config.LORE_PANEL_PADDING
    lp_w = _lore_panel_rect.width  - 2 * config.LORE_PANEL_PADDING
    lp_h = _lore_panel_rect.height - 2 * config.LORE_PANEL_PADDING

    _lore_panel_title_rect = pygame.Rect(lp_x, lp_y, lp_w, config.LORE_PANEL_TITLE_HEIGHT)
    _lore_panel_close_button_rect = pygame.Rect(
        _lore_panel_rect.right - config.LORE_PANEL_PADDING - config.LORE_PANEL_CLOSE_BUTTON_SIZE,
        _lore_panel_rect.top   + config.LORE_PANEL_PADDING,
        config.LORE_PANEL_CLOSE_BUTTON_SIZE,
        config.LORE_PANEL_CLOSE_BUTTON_SIZE,
    )
    _lore_panel_body_area_rect = pygame.Rect(
        lp_x,
        lp_y + config.LORE_PANEL_TITLE_HEIGHT,
        lp_w,
        lp_h - config.LORE_PANEL_TITLE_HEIGHT,
    )
    _lore_panel_text_draw_width     = max(1, _lore_panel_body_area_rect.width - 2 * config.LORE_PANEL_PADDING)
    _lore_panel_text_start_x_offset = config.LORE_PANEL_PADDING

    # ------------------------------------------------------------------
    # Lore toggle button (centred at top, shifts left when panel is open)
    # ------------------------------------------------------------------
    lore_btn_x = config.WIDTH // 2 - config.LORE_PANEL_TOGGLE_BUTTON_WIDTH // 2
    if state.panel_visible:
        lore_btn_x -= current_panel_width // 2
    _lore_toggle_button_rect = pygame.Rect(
        lore_btn_x,
        config.PADDING,
        config.LORE_PANEL_TOGGLE_BUTTON_WIDTH,
        config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT,
    )

    # ------------------------------------------------------------------
    # Clock rects (stacked, flush against panel or screen edge)
    # ------------------------------------------------------------------
    if getattr(state, "clock_expanded", True):
        clock_h       = config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT
        sleep_clock_h = config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT
    else:
        clock_h       = config.LORE_PANEL_TOGGLE_BUTTON_HEIGHT // 2
        sleep_clock_h = 0

    if state.panel_visible:
        clock_x = config.WIDTH - current_panel_width - config.CLOCK_WIDTH
    else:
        clock_x = config.WIDTH - config.CLOCK_WIDTH - (config.PADDING * 2) - (config.MUTE_BUTTON_SIZE + config.MUTE_BUTTON_SIZE // 2)

    _current_time_clock_rect = pygame.Rect(clock_x, config.PADDING, config.CLOCK_WIDTH, clock_h)
    _sleep_duration_clock_rect = pygame.Rect(clock_x, config.PADDING + clock_h, config.CLOCK_WIDTH, sleep_clock_h)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_stat_icons() -> None:
    """Load and scale all stat icon images into _stat_icons."""
    global _stat_icons
    _stat_icons = {}

    stats  = ["fullness", "hydration", "energy"]
    levels = ["full", "half", "empty"]

    for stat_name in stats:
        for level in levels:
            file_name  = f"{stat_name}_{level}.png"
            full_path  = os.path.join(config.STAT_ICON_DIR, file_name)
            try:
                img    = pygame.image.load(full_path).convert_alpha()
                scaled = pygame.transform.scale(img, config.STAT_ICON_SIZE)
                _stat_icons[(stat_name, level)] = scaled
            except FileNotFoundError:
                print(f"[gui_core] Stat icon not found: {full_path}")
                _stat_icons[(stat_name, level)] = None
            except (pygame.error, Exception) as exc:
                print(f"[gui_core] Could not load icon {full_path}: {exc}")
                _stat_icons[(stat_name, level)] = None


def load_and_set_background(image_path: str) -> None:
    """
    Load an image and store it in state.background_image.

    Searches several directories in order, with and without extension.
    """
    image_dirs = [ # Move these out of here? asset files, asset paths
        "style/images/local_rooms_images",
        "style/images/rooms_images",
        "style/images/local_rooms_images/local_ai_gens",
        "style/images/lighthouse_rooms_images",
    ]

    full_path = None

    if "." not in image_path:
        # No extension supplied — try .jpg in each directory.
        for directory in image_dirs:
            candidate = os.path.join(directory, f"{image_path}.jpg")
            if os.path.exists(candidate):
                full_path = candidate
                break
    else:
        for directory in image_dirs:
            candidate = os.path.join(directory, image_path)
            if os.path.exists(candidate):
                full_path = candidate
                break

    if full_path:
        try:
            img = pygame.image.load(full_path)
            state.background_image = pygame.transform.scale(img, (config.WIDTH, config.HEIGHT))
            print(f"[gui_core] Background set: {full_path}")
        except Exception as exc:
            print(f"[gui_core] Failed to load background '{full_path}': {exc}")
            state.background_image = None
    else:
        print(f"[gui_core] Background not found in any directory: {image_path}")
        state.background_image = None