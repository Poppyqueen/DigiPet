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
import os
import enum
from typing import Any, Optional, Callable

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
# Dependency Checkers
# ---------------------------------------------------------------------------
# Return (True, "") if ready, or (False, "Error message") to lock the card.

def _check_xeno_canto_ready() -> tuple[bool, str]:
    # Example environment secret check (Forcing False here to demonstrate the UI)
    if not os.getenv("XENO_CANTO_API_KEY"):
        print("xeno-canto API key missing! Locking module. Please register and obtain an xeno-canto API key. \nVisit 'https://xeno-canto.org' and 'https://xeno-canto.org/account' for more info.")
        return False, "missing .env secrets!"
    return True, ""

def _check_astro_views_ready() -> tuple[bool, str]:

        # Example library check
    try:
        import skyfield, opensimplex # Example required lib
    except ImportError:
        print("Required libraries for astro views skyfield, opensimplex are missing! Locking module. Run: pip install '.[skysim]'")
        return False, "missing libraries!"
    return True, ""


# ---------------------------------------------------------------------------
# Module definitions
# ---------------------------------------------------------------------------

_BORTLE_OPTIONS =[f"Class {i}" for i in range(1, 10)]
_BORTLE_PARSE   = {f"Class {i}": i for i in range(1, 10)}

# # Helpers for example modules (not part of the main function)
# _BEAUFORT_OPTIONS = [f"Force {i}" for i in range(0, 13)]
# _CLOUD_OPTIONS    = ["Clear", "Few", "Scattered", "Broken", "Overcast"]
# _SOIL_MOISTURE    = ["Dry", "Moist", "Wet", "Saturated"]
# _PH_SCALE         = [str(i) for i in range(0, 15)]

OBSERVATION_MODULES: list[dict] =[
    {
        "id":    "xeno_canto",
        "title": "xeno-canto",
        "check_ready": _check_xeno_canto_ready,  # Optional check
        "fields":[
            {
                "type":     "text_int",
                "key":      "fauna_abundance",
                "label":    "Fauna Abundance",
                "hint":     "1 ... 9",
                "validate": lambda raw: _validate_int_range(raw, 1, 9),
            },
        ],
    },
    {
        "id":    "astro_views",
        "title": "astro-views",
        "check_ready": _check_astro_views_ready, # Optional check
        "fields":[
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


    # Examples to verify scroll and layout #

# {
#         "id":    "wind_speed",
#         "title": "Beaufort Wind Scale",
#         "fields": [
#             {
#                 "type":     "dropdown",
#                 "key":      "wind_force",
#                 "label":    "Wind Force",
#                 "hint":     "Force 0 (Calm) ... Force 12 (Hurricane)",
#                 "options":  _BEAUFORT_OPTIONS,
#                 "validate": lambda sel: _validate_dropdown(sel, _BEAUFORT_OPTIONS),
#             },
#         ],
#     },
#     {
#         "id":    "cloud_density",
#         "title": "Cloud Cover",
#         "fields": [
#             {
#                 "type":     "dropdown",
#                 "key":      "cover_type",
#                 "label":    "Sky Condition",
#                 "hint":     "Select current coverage",
#                 "options":  _CLOUD_OPTIONS,
#                 "validate": lambda sel: _validate_dropdown(sel, _CLOUD_OPTIONS),
#             },
#         ],
#     },
#     {
#         "id":    "soil_analysis",
#         "title": "Soil Moisture",
#         "fields": [
#             {
#                 "type":     "dropdown",
#                 "key":      "moisture_level",
#                 "label":    "Moisture State",
#                 "hint":     "Tactile soil assessment",
#                 "options":  _SOIL_MOISTURE,
#                 "validate": lambda sel: _validate_dropdown(sel, _SOIL_MOISTURE),
#             },
#         ],
#     },
#     {
#         "id":    "noise_pollution",
#         "title": "Ambient Noise Level",
#         "fields": [
#             {
#                 "type":     "text_int",
#                 "key":      "decibel_estimate",
#                 "label":    "Estimated Decibels (dB)",
#                 "hint":     "Range: 30 (Quiet) ... 120 (Loud)",
#                 "validate": lambda raw: _validate_int_range(raw, 30, 120),
#             },
#         ],
#     },
#     {
#         "id":    "botany_health",
#         "title": "Plant Health Index",
#         "fields": [
#             {
#                 "type":     "text_int",
#                 "key":      "vitality_score",
#                 "label":    "Vitality Score",
#                 "hint":     "1 (Near Death) ... 5 (Thriving)",
#                 "validate": lambda raw: _validate_int_range(raw, 1, 5),
#             },
#         ],
#     },
#     {
#         "id":    "water_chemistry",
#         "title": "Water pH",
#         "fields": [
#             {
#                 "type":     "dropdown",
#                 "key":      "ph_level",
#                 "label":    "pH Value",
#                 "hint":     "0 (Acidic) ... 14 (Alkaline)",
#                 "options":  _PH_SCALE,
#                 "validate": lambda sel: _validate_dropdown(sel, _PH_SCALE),
#             },
#         ],
#     },
]

_N_MODULES = len(OBSERVATION_MODULES)

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

_NEUTRAL = (160, 160, 170)
_MUTED   = (80,  80,  95)
_RED     = (255,  60,  60)

# Card layout constants
_CARD_INNER_PAD  = 20
_CARD_HEADER_H   = 50
_FIELD_LABEL_H   = 20
_FIELD_HINT_H    = 20
_FIELD_GAP       = 14
_CARD_BOTTOM_PAD = 16


# ---------------------------------------------------------------------------
# Per-module card
# ---------------------------------------------------------------------------

class _ModuleState:
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
        bold_font:   pygame.font.Font,
        text_inputs: dict,
        dropdowns:   dict,
    ):
        self.defn       = module_def
        self.font       = font
        self.small_font = small_font
        self.hint_font  = hint_font
        self.bold_font  = bold_font

        # Check dependencies
        self.is_ready, self.error_msg = module_def.get("check_ready", lambda: (True, ""))()

        # Checkbox geometry (used whether drawn natively or rendered as locked dummy)
        cb_size = 20
        self.cb_x = card_x + card_w - cb_size - 12
        self.cb_y = card_y + (_CARD_HEADER_H - cb_size) // 2
        self.checkbox = Checkbox(self.cb_x, self.cb_y, "", font)

        self.field_widgets: list[dict] =[]
        self.field_results: dict[str, tuple[ValidationResult, Any]] = {}

        if self.is_ready:
            # Build normal field widgets
            n_fields = len(module_def.get("fields",[]))
            content_h = n_fields * (_FIELD_LABEL_H + field_h + _FIELD_HINT_H + _FIELD_GAP)
            card_h = _CARD_HEADER_H + content_h + _CARD_BOTTOM_PAD

            fw_x = card_x + _CARD_INNER_PAD
            fw_w = card_w - 2 * _CARD_INNER_PAD
            fy   = card_y + _CARD_HEADER_H + _FIELD_LABEL_H

            for fdef in module_def.get("fields", []):
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

        else:
            # Force uncheck and lock height to a compact error box
            self.checkbox.checked = False
            card_h = _CARD_HEADER_H + 60

        self.card_rect = pygame.Rect(card_x, card_y, card_w, card_h)

    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self.is_ready and self.checkbox.checked

    @property
    def card_h(self) -> int:
        return self.card_rect.height

    def validate_all(self) -> bool:
        if not self.is_ready:
            return True  # A locked module shouldn't block main confirmation
            
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
        if not self.is_ready:
            return out
            
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
        if not self.is_ready:
            return
            
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
        if not self.is_ready:
            return  # Completely block interaction if dependencies are missing
            
        self.checkbox.handle_event(event, adjusted_pos)
        if self.enabled:
            for fw in self.field_widgets:
                fw["widget"].handle_event(event, adjusted_pos)

    def draw(self, surface: pygame.Surface, hover_pos: tuple, offset_y: int, accent: tuple) -> None:
        border_col = accent if self.enabled else _MUTED
        title_col  = config.WHITE if self.enabled else _MUTED

        # Card background
        draw_card = self.card_rect.move(0, -offset_y)
        pygame.draw.rect(surface, config.BLACK, draw_card)
        pygame.draw.rect(surface, border_col, draw_card, 3, border_radius=15)

        # Title
        title_surf = self.font.render(self.defn["title"], True, title_col)
        surface.blit(title_surf, (draw_card.x + 14, draw_card.y + 14))

        # Checkbox & State Logic
        if self.is_ready:
            state_text = "ON" if self.enabled else "OFF"
            st_col     = border_col
        else:
            state_text = "LOCKED"
            st_col     = _MUTED
            
        st_surf = self.small_font.render(state_text, True, st_col)

        if self.is_ready:
            # Active checkbox
            surface.blit(st_surf, (
                self.checkbox.rect.x - st_surf.get_width() - 6,
                self.checkbox.rect.y - offset_y + 2,
            ))
            self.checkbox.draw(surface, hover_pos, offset_y)
        else:
            # Blocked dummy checkbox (muted, crossed out)
            fake_cb_rect = self.checkbox.rect.move(0, -offset_y)
            pygame.draw.rect(surface, _MUTED, fake_cb_rect, 2, border_radius=3)
            # Cross lines
            pygame.draw.line(surface, _MUTED, fake_cb_rect.topleft, fake_cb_rect.bottomright, 2)
            pygame.draw.line(surface, _MUTED, fake_cb_rect.bottomleft, fake_cb_rect.topright, 2)
            
            surface.blit(st_surf, (
                fake_cb_rect.x - st_surf.get_width() - 6,
                fake_cb_rect.y + 2,
            ))

        # Separator
        sep_y = draw_card.y + _CARD_HEADER_H
        pygame.draw.line(surface, border_col,
                         (draw_card.x + 10, sep_y),
                         (draw_card.right - 10, sep_y), 1)

        # Body Rendering
        if self.is_ready:
            # Standard Fields
            for fw in self.field_widgets:
                fdef     = fw["def"]
                widget   = fw["widget"]
                error_pt = fw["error_pt"]

                lbl_col  = config.WHITE if self.enabled else _MUTED
                lbl_surf = self.small_font.render(fdef["label"], True, lbl_col)
                surface.blit(lbl_surf, (widget.rect.x, widget.rect.y - offset_y - _FIELD_LABEL_H))

                hint_surf = self.hint_font.render(fdef["hint"], True, config.WHITE if self.enabled else _MUTED)
                surface.blit(hint_surf, (widget.rect.x, widget.rect.bottom - offset_y + 4))

                if self.enabled:
                    widget.draw(surface, offset_y)
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
        else:
            # Alert replacement text (Centered bold red error message)
            err_surf = self.bold_font.render(self.error_msg, True, _RED)
            err_rect = err_surf.get_rect(
                centerx=draw_card.centerx,
                centery=draw_card.y + _CARD_HEADER_H + (draw_card.height - _CARD_HEADER_H) // 2
            )
            surface.blit(err_surf, err_rect)


# ---------------------------------------------------------------------------
# Main blocking function
# ---------------------------------------------------------------------------

def run_observation_settings_ui(
    screen: pygame.Surface,
    font:   pygame.font.Font,
) -> Optional[dict]:
    sw, sh = screen.get_width(), screen.get_height()
    clock  = pygame.time.Clock()

    try:
        accent = state.pet_color if hasattr(state, "pet_color") and state.pet_color else (100, 255, 180)
    except Exception:
        accent = (100, 255, 180)

    try:
        small_font = pygame.font.SysFont("Courier New", 15)
        hint_font  = pygame.font.SysFont("Courier New", 12)
        bold_font  = pygame.font.SysFont("Courier New", 14, bold=True)
    except Exception:
        small_font = font
        hint_font  = font
        bold_font  = font

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

    def _build_module_states() -> tuple[list[_ModuleState], dict, dict, int]:
        t_inputs:  dict = {}
        dd_inputs: dict = {}
        states:    list[_ModuleState] =[]

        num_columns = min(_N_MODULES, 2)
        field_h     = max(30, sh // 20)
        col_spacing = 20
        row_spacing = 20
        card_w      = (viewport_rect.width - (num_columns - 1) * col_spacing) // num_columns
        start_y     = 10

        def _card_h_for(mdef: dict) -> int:
            # Mirrors the card height calculation in _ModuleState to correctly size rows
            is_ready, _ = mdef.get("check_ready", lambda: (True, ""))()
            if not is_ready:
                return _CARD_HEADER_H + 60
            n = len(mdef.get("fields",[]))
            return _CARD_HEADER_H + n * (_FIELD_LABEL_H + field_h + _FIELD_HINT_H + _FIELD_GAP) + _CARD_BOTTOM_PAD

        n_rows = (_N_MODULES + num_columns - 1) // num_columns
        row_tops: list[int] =[]
        current_y = start_y
        for row in range(n_rows):
            row_tops.append(current_y)
            row_cards =[OBSERVATION_MODULES[row * num_columns + c]
                         for c in range(num_columns)
                         if row * num_columns + c < _N_MODULES]
            tallest = max(_card_h_for(m) for m in row_cards)
            current_y += tallest + row_spacing

        total_content_height = current_y

        for i, mdef in enumerate(OBSERVATION_MODULES):
            row = i // num_columns
            col = i % num_columns
            cx  = col * (card_w + col_spacing)
            cy  = row_tops[row]
            ms  = _ModuleState(
                mdef, cx, cy, card_w, field_h,
                font, small_font, hint_font, bold_font,
                t_inputs, dd_inputs,
            )
            states.append(ms)

        return states, t_inputs, dd_inputs, total_content_height

    module_states, text_inputs, dropdowns, total_content_height = _build_module_states()

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
                    continue

                elif viewport_rect.collidepoint(mouse_pos):
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

        for ms in module_states:
            ms.validate_all()
            ms.sync_errors()

        can_confirm = all(ms.validate_all() for ms in module_states)
        cont_btn.text_color = accent if can_confirm else _NEUTRAL

        screen.fill(config.BLACK)

        is_mouse_in_viewport = viewport_rect.collidepoint(mouse_pos)
        mouse_in_vp          = (mouse_pos[0] - viewport_rect.x,
                                 mouse_pos[1] - viewport_rect.y)
        hover_check_pos = mouse_in_vp if is_mouse_in_viewport else (-1, -1)

        scroll_surface.fill(config.BLACK)

        for ms in module_states:
            ms.draw(scroll_surface, hover_check_pos, scroll_offset_y, accent)

        for dd in dropdowns.values():
            if dd.is_open:
                dd.draw(scroll_surface, scroll_offset_y)

        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)
        screen.blit(scroll_surface, viewport_rect.topleft)
        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)

        screen.blit(title_surface, title_rect)
        cont_btn.draw(screen, mouse_pos, 0)

        pygame.display.flip()

    return result