"""
observation_settings_ui.py

Blocking GUI screen for selecting optional observation module settings.
Returns a dict of enabled modules and their configured values, or None on quit.

Return structure:
    {
        "xeno_canto": { "enabled": True,  "fauna_abundance": 7    },
        "astro_views": { "enabled": True,  "bortle_class":    3    },
    }

Usage:
    result = run_observation_settings_ui(screen, font)
"""

from __future__ import annotations

import sys
import enum
from typing import Any, Optional

import pygame

from pygame_int import gui_config, state, config
from pygame_int.main_menu_int.main_menu_modules.button import Button
from pygame_int.main_menu_int.main_menu_modules.checkbox import Checkbox
from pygame_int.main_menu_int.main_menu_modules.text_input_box import TextInputBox
from pygame_int.main_menu_int.main_menu_modules.dropdown_menu import DropdownMenu
from pygame_int.main_menu_int.main_menu_modules.pulsing_text import PulsingText


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationResult(enum.Enum):
    OK           = "ok"
    EMPTY        = "empty"        # blank — ok when module is disabled
    INVALID      = "invalid"
    OUT_OF_RANGE = "out_of_range"


def _validate_int_range(raw: str, lo: int, hi: int) -> tuple[ValidationResult, Optional[int]]:
    raw = raw.strip()
    if not raw:
        return ValidationResult.EMPTY, None
    try:
        v = int(raw)
    except (ValueError, TypeError):
        return ValidationResult.INVALID, None
    if lo <= v <= hi:
        return ValidationResult.OK, v
    return ValidationResult.OUT_OF_RANGE, None


def _validate_dropdown(selected: Optional[str], options: list[str]) -> tuple[ValidationResult, Optional[str]]:
    if selected is None:
        return ValidationResult.EMPTY, None
    if selected in options:
        return ValidationResult.OK, selected
    return ValidationResult.INVALID, None


# ---------------------------------------------------------------------------
# Module definitions
# ---------------------------------------------------------------------------
# To add a new module: append one dict to OBSERVATION_MODULES — nothing else changes.
# Field types: "text_int" | "dropdown"

_BORTLE_OPTIONS = [f"Class {i}" for i in range(1, 10)]
_BORTLE_PARSE   = {f"Class {i}": i for i in range(1, 10)}


OBSERVATION_MODULES: list[dict] = [
    {
        "id":    "xeno_canto",
        "title": "xeno-canto",
        "fields": [
            {
                "type":     "text_int",
                "key":      "fauna_abundance",
                "label":    "Fauna Abundance",
                "hint":     "1 ... 10",
                "validate": lambda raw: _validate_int_range(raw, 1, 10),
            },
        ],
    },
    {
        "id":    "astro_views",
        "title": "astro-views",
        "fields": [
            {
                "type":     "dropdown",
                "key":      "bortle_class",
                "label":    "Bortle Scale",
                "hint":     "Class 1 (darkest)... ",
                "options":  _BORTLE_OPTIONS,
                "validate": lambda sel: _validate_dropdown(sel, _BORTLE_OPTIONS),
            },
        ],
    },

]

_N_MODULES = len(OBSERVATION_MODULES)

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

_NEUTRAL = (160, 160, 170)
_MUTED   = (80,  80,  95)
_RED     = (255,  60,  60)

# Card layout constants — proportions, not absolutes
_CARD_INNER_PAD  = 20   # px inside the card on each side
_CARD_HEADER_H   = 50   # height of the title+checkbox band
_FIELD_LABEL_H   = 20   # px for the field label text above each widget
_FIELD_HINT_H    = 20   # px for the hint text below each widget
_FIELD_GAP       = 14   # gap between hint bottom and next label top
_CARD_BOTTOM_PAD = 16   # breathing room below the last field


# ---------------------------------------------------------------------------
# Per-module card
# ---------------------------------------------------------------------------

class _ModuleState:
    """One observation module: checkbox toggle + its field widgets."""

    def __init__(
        self,
        module_def:  dict,
        card_x:      int,
        card_y:      int,
        card_w:      int,
        field_h:     int,
        font:        pygame.font.Font,
        small_font:  pygame.font.Font,
        hint_font:   pygame.font.Font,
        text_inputs: dict,
        dropdowns:   dict,
    ):
        self.defn       = module_def
        self.font       = font
        self.small_font = small_font
        self.hint_font  = hint_font

        # Compute card height from content
        n_fields = len(module_def["fields"])
        content_h = n_fields * (_FIELD_LABEL_H + field_h + _FIELD_HINT_H + _FIELD_GAP)
        card_h = _CARD_HEADER_H + content_h + _CARD_BOTTOM_PAD

        self.card_rect = pygame.Rect(card_x, card_y, card_w, card_h)

        # Checkbox — top-right of header; text="" because we draw ON/OFF ourselves
        cb_size = 20
        cb_x = card_x + card_w - cb_size - 12
        cb_y = card_y + (_CARD_HEADER_H - cb_size) // 2
        self.checkbox = Checkbox(cb_x, cb_y, "", font)

        # Field widgets
        self.field_widgets: list[dict] = []
        fw_x = card_x + _CARD_INNER_PAD
        fw_w = card_w - 2 * _CARD_INNER_PAD
        fy   = card_y + _CARD_HEADER_H + _FIELD_LABEL_H

        for fdef in module_def["fields"]:
            if fdef["type"] == "text_int":
                widget = TextInputBox(
                    fw_x, fy, fw_w, field_h,
                    small_font, fdef["key"],
                    text_inputs=text_inputs,
                    active_element=None,
                )
            elif fdef["type"] == "dropdown":
                widget = DropdownMenu(
                    fw_x, fy, fw_w, field_h,
                    small_font, fdef["key"],
                    options=fdef["options"],
                    default_text="Select...",
                    dropdowns=dropdowns,
                )
            else:
                raise ValueError(f"Unknown field type: {fdef['type']}")

            error_pt = PulsingText(
                "!", font,
                (fw_x + fw_w // 2, fy - 14),
                color=_RED,
                ang_velocity=0.006,
            )

            self.field_widgets.append({
                "def":      fdef,
                "widget":   widget,
                "error_pt": error_pt,
            })
            fy += field_h + _FIELD_HINT_H + _FIELD_GAP + _FIELD_LABEL_H

        self.field_results: dict[str, tuple[ValidationResult, Any]] = {}

    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self.checkbox.checked

    @property
    def card_h(self) -> int:
        return self.card_rect.height

    def validate_all(self) -> bool:
        all_ok = True
        for fw in self.field_widgets:
            fdef   = fw["def"]
            widget = fw["widget"]
            key    = fdef["key"]
            if fdef["type"] == "text_int":
                result, value = fdef["validate"](widget.text)
            else:
                result, value = fdef["validate"](widget.selected_option)
            self.field_results[key] = (result, value)
            if self.enabled and result != ValidationResult.OK:
                all_ok = False
        return all_ok

    def collect(self) -> dict:
        out = {"enabled": self.enabled}
        for fw in self.field_widgets:
            key       = fw["def"]["key"]
            result, v = self.field_results.get(key, (ValidationResult.EMPTY, None))
            if self.enabled and result == ValidationResult.OK:
                if fw["def"]["type"] == "dropdown" and key == "bortle_class":
                    v = _BORTLE_PARSE.get(v, v)
                out[key] = v
            else:
                out[key] = None
        return out

    def sync_errors(self) -> None:
        for fw in self.field_widgets:
            key      = fw["def"]["key"]
            result, _ = self.field_results.get(key, (ValidationResult.EMPTY, None))
            bad = self.enabled and result not in (ValidationResult.OK, ValidationResult.EMPTY)
            fw["widget"].validation_error = bad
            if bad:
                fw["error_pt"].show()
            else:
                fw["error_pt"].hide()

    def handle_event(self, event: pygame.event.Event, adjusted_pos: tuple) -> None:
        """adjusted_pos is already offset-corrected for the scroll surface."""
        self.checkbox.handle_event(event, adjusted_pos)
        if self.enabled:
            for fw in self.field_widgets:
                fw["widget"].handle_event(event, adjusted_pos)

    def draw(self, surface: pygame.Surface, hover_pos: tuple, offset_y: int, accent: tuple) -> None:
        """
        Draw onto the scroll surface.
        All rects live in scroll-surface absolute coords; offset_y shifts them
        upward visually, exactly as the widget draw methods do internally.
        """
        border_col = accent if self.enabled else _MUTED
        title_col  = config.WHITE if self.enabled else _MUTED

        # Card background — shift by offset_y, same as every other widget
        draw_card = self.card_rect.move(0, -offset_y)
        pygame.draw.rect(surface, config.BLACK, draw_card)
        pygame.draw.rect(surface, border_col, draw_card, 3, border_radius=15)

        # Title
        title_surf = self.font.render(self.defn["title"], True, title_col)
        surface.blit(title_surf, (draw_card.x + 14, draw_card.y + 14))

        # ON / OFF label — position relative to the shifted checkbox rect
        state_text = "ON" if self.enabled else "OFF"
        st_surf    = self.small_font.render(state_text, True, border_col)
        surface.blit(st_surf, (
            self.checkbox.rect.x - st_surf.get_width() - 6,
            self.checkbox.rect.y - offset_y + 2,
        ))

        # Checkbox — passes offset_y so it draws itself shifted correctly
        self.checkbox.draw(surface, hover_pos, offset_y)

        # Separator
        sep_y = draw_card.y + _CARD_HEADER_H
        pygame.draw.line(surface, border_col,
                         (draw_card.x + 10, sep_y),
                         (draw_card.right - 10, sep_y), 1)

        # Fields
        for fw in self.field_widgets:
            fdef     = fw["def"]
            widget   = fw["widget"]
            error_pt = fw["error_pt"]

            lbl_col  = config.WHITE if self.enabled else _MUTED
            lbl_surf = self.small_font.render(fdef["label"], True, lbl_col)
            # label sits _FIELD_LABEL_H px above the widget rect, shifted by offset_y
            surface.blit(lbl_surf, (widget.rect.x, widget.rect.y - offset_y - _FIELD_LABEL_H))

            hint_surf = self.hint_font.render(fdef["hint"], True, config.WHITE if self.enabled else _MUTED)
            surface.blit(hint_surf, (widget.rect.x, widget.rect.bottom - offset_y + 4))

            if self.enabled:
                # widget.draw handles offset_y internally via self.rect.move(0, -offset_y)
                widget.draw(surface, offset_y)
                # PulsingText has no offset_y awareness — temporarily move its rect,
                # draw, then restore so its logical position stays correct
                if error_pt.visible:
                    original_y = error_pt.rect.y
                    error_pt.rect.y -= offset_y
                    error_pt.draw(surface)
                    error_pt.rect.y = original_y
            else:
                draw_widget = widget.rect.move(0, -offset_y)
                pygame.draw.rect(surface, (20, 20, 20), draw_widget, border_radius=4)
                pygame.draw.rect(surface, _MUTED, draw_widget, 1, border_radius=4)
                error_pt.hide()


# ---------------------------------------------------------------------------
# Main blocking function
# ---------------------------------------------------------------------------

def run_observation_settings_ui(
    screen: pygame.Surface,
    font:   pygame.font.Font,
) -> Optional[dict]:
    """
    Blocking GUI. Returns result dict on confirm, None if window is closed.
    """
    sw, sh = screen.get_width(), screen.get_height()
    clock  = pygame.time.Clock()

    # Accent — same guard as the DNA screen
    try:
        accent = state.pet_color if hasattr(state, "pet_color") and state.pet_color else (100, 255, 180)
    except Exception:
        accent = (100, 255, 180)

    # Fonts — same pattern as DNA screen
    try:
        small_font = pygame.font.SysFont("Courier New", 15)
        hint_font  = pygame.font.SysFont("Courier New", 12)
    except Exception:
        small_font = font
        hint_font  = font

    # ------------------------------------------------------------------
    # Static elements — title + confirm button, drawn directly on screen
    # ------------------------------------------------------------------
    title_text    = "Outdoors Perception Settings"
    title_surface = font.render(title_text, True, config.WHITE)
    title_rect    = title_surface.get_rect(centerx=sw // 2, top=20)

    btn_w = min(gui_config.ENTER_BUTTON_WIDTH, sw - 80)
    btn_h = gui_config.ENTER_BUTTON_HEIGHT
    btn_x = sw - gui_config.HORIZONTAL_PADDING - btn_w
    btn_y = title_rect.bottom + 15

    cont_btn = Button(
        btn_x, btn_y, btn_w, btn_h,
        "CONFIRM", font,
        action=lambda: "confirm",
    )

    # ------------------------------------------------------------------
    # Scrollable viewport — mirrors main menu exactly
    # ------------------------------------------------------------------
    viewport_y      = cont_btn.rect.bottom + 20
    viewport_height = sh - viewport_y - 20
    viewport_rect   = pygame.Rect(
        gui_config.HORIZONTAL_PADDING,
        viewport_y,
        sw - 2 * gui_config.HORIZONTAL_PADDING,
        viewport_height,
    )
    scroll_surface = pygame.Surface((viewport_rect.width, viewport_rect.height))
    scroll_offset_y = 0
    scroll_speed    = 30

    # ------------------------------------------------------------------
    # Build module cards inside the scroll surface coordinate space
    # ------------------------------------------------------------------
    def _build_module_states() -> tuple[list[_ModuleState], dict, dict, int]:
        """
        Lay out module cards in a grid inside the scroll surface coordinate space.
        Returns (module_states, text_inputs, dropdowns, total_content_height).
        """
        t_inputs:  dict = {}
        dd_inputs: dict = {}
        states:    list[_ModuleState] = []

        num_columns = min(_N_MODULES, 2)
        field_h     = max(30, sh // 20)
        col_spacing = 20
        row_spacing = 20
        card_w      = (viewport_rect.width - (num_columns - 1) * col_spacing) // num_columns
        start_y     = 10

        # Pre-compute the card height for each module (depends only on field count)
        def _card_h_for(mdef: dict) -> int:
            n = len(mdef["fields"])
            return _CARD_HEADER_H + n * (_FIELD_LABEL_H + field_h + _FIELD_HINT_H + _FIELD_GAP) + _CARD_BOTTOM_PAD

        # Compute row top-y values — must know tallest card per row
        n_rows = (_N_MODULES + num_columns - 1) // num_columns
        row_tops: list[int] = []
        current_y = start_y
        for row in range(n_rows):
            row_tops.append(current_y)
            row_cards = [OBSERVATION_MODULES[row * num_columns + c]
                         for c in range(num_columns)
                         if row * num_columns + c < _N_MODULES]
            tallest = max(_card_h_for(m) for m in row_cards)
            current_y += tallest + row_spacing

        total_content_height = current_y

        # Now build every _ModuleState with the correct final y position
        for i, mdef in enumerate(OBSERVATION_MODULES):
            row = i // num_columns
            col = i % num_columns
            cx  = col * (card_w + col_spacing)
            cy  = row_tops[row]
            ms  = _ModuleState(
                mdef,
                cx, cy,
                card_w, field_h,
                font, small_font, hint_font,
                t_inputs, dd_inputs,
            )
            states.append(ms)

        return states, t_inputs, dd_inputs, total_content_height

    module_states, text_inputs, dropdowns, total_content_height = _build_module_states()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    result  = None
    running = True

    while running:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
                break

            # --- Static confirm button (always on screen, not scrolled) ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if cont_btn.rect.collidepoint(mouse_pos):
                    action = cont_btn.handle_event(event, mouse_pos)
                    if action == "confirm":
                        all_valid = all(ms.validate_all() for ms in module_states)
                        for ms in module_states:
                            ms.sync_errors()
                        if all_valid:
                            result  = {ms.defn["id"]: ms.collect() for ms in module_states}
                            running = False
                    continue  # consumed

                # --- Scrollable viewport clicks ---
                elif viewport_rect.collidepoint(mouse_pos):
                    adjusted_pos = (
                        mouse_pos[0] - viewport_rect.x,
                        mouse_pos[1] - viewport_rect.y + scroll_offset_y,
                    )
                    # Open dropdown gets priority
                    active_dd = next((dd for dd in dropdowns.values() if dd.is_open), None)
                    if active_dd:
                        active_dd.handle_event(event, adjusted_pos)
                    else:
                        for ms in module_states:
                            ms.handle_event(event, adjusted_pos)

            # Mousewheel — open dropdown gets priority; otherwise scroll the viewport
            if event.type == pygame.MOUSEWHEEL and viewport_rect.collidepoint(mouse_pos):
                adjusted_pos = (
                    mouse_pos[0] - viewport_rect.x,
                    mouse_pos[1] - viewport_rect.y + scroll_offset_y,
                )
                active_dd = next((dd for dd in dropdowns.values() if dd.is_open), None)
                if active_dd:
                    active_dd.handle_event(event, adjusted_pos)
                else:
                    scroll_offset_y -= event.y * scroll_speed
                    max_scroll = max(0, total_content_height - viewport_rect.height)
                    scroll_offset_y = max(0, min(scroll_offset_y, max_scroll))

            # Non-click events (keyboard) — route to all module states
            if event.type not in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL):
                adjusted_pos = (
                    mouse_pos[0] - viewport_rect.x,
                    mouse_pos[1] - viewport_rect.y + scroll_offset_y,
                )
                active_dd = next((dd for dd in dropdowns.values() if dd.is_open), None)
                if active_dd:
                    active_dd.handle_event(event, adjusted_pos)
                else:
                    for ms in module_states:
                        ms.handle_event(event, adjusted_pos)

        # Live validation every frame
        for ms in module_states:
            ms.validate_all()
            ms.sync_errors()

        can_confirm = all(ms.validate_all() for ms in module_states)
        cont_btn.text_color = accent if can_confirm else _NEUTRAL

        # ------------------------------------------------------------------
        # Draw — mirrors main menu draw block
        # ------------------------------------------------------------------
        screen.fill(config.BLACK)

        # --- Scroll surface ---
        is_mouse_in_viewport = viewport_rect.collidepoint(mouse_pos)
        mouse_in_vp          = (mouse_pos[0] - viewport_rect.x,
                                 mouse_pos[1] - viewport_rect.y)
        # Safe hover pos: impossible coord when outside viewport (main menu pattern)
        hover_check_pos = mouse_in_vp if is_mouse_in_viewport else (-1, -1)

        scroll_surface.fill(config.BLACK)

        for ms in module_states:
            ms.draw(scroll_surface, hover_check_pos, scroll_offset_y, accent)

        # Open dropdowns drawn last so they float above cards
        for dd in dropdowns.values():
            if dd.is_open:
                dd.draw(scroll_surface, scroll_offset_y)

        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)
        screen.blit(scroll_surface, viewport_rect.topleft)
        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)

        # --- Static elements on top ---
        screen.blit(title_surface, title_rect)
        cont_btn.draw(screen, mouse_pos, 0)

        pygame.display.flip()

    return result