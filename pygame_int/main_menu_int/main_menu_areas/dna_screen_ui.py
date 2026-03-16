from __future__ import annotations

import sys
import pygame

from pygame_int import gui_config, state
from pygame_int.main_menu_int.main_menu_modules.button import Button
from pygame_int.main_menu_int.main_menu_modules.text_input_box import TextInputBox
from pygame_int.main_menu_int.main_menu_modules.pulsing_text import PulsingText

from pygame_int.main_digipet.pet_dna import PetDNA



# Field order matches PetDNA field order exactly.
# (letter, field_key, hint)
_FIELD_KEYS = [
    ("F", "wave_freq"),
    ("A", "amplitude"),
    ("D", "droop"),
    ("B", "blend_ms"),
    ("S", "speed_base"),
    ("N", "noise_ceiling"),
    ("W", "stroke_width"),
]
 
def _build_fields():
    """Build (letter, field_key, hint) tuples from PetDNA.RANGES."""
    result = []
    for letter, fk in _FIELD_KEYS:
        lo, hi, typ = PetDNA.RANGES[fk]
        hint = f"{lo} ... {hi}"
        result.append((letter, fk, hint))
    return result
 
_FIELDS  = _build_fields()

_N       = len(_FIELDS)
_NEUTRAL = (160, 160, 170)
_MUTED   = (80,  80,  95)
_BG      = (8,   8,   12)


def _try_parse(field_key: str, raw: str):
    """
    Parse and range-validate a raw string using PetDNA as source of truth.
    Returns the typed value if valid, None otherwise.
    """
    from pygame_int.main_digipet.pet_dna import PetDNA
    raw = raw.strip()
    if not raw:
        return None
    ranges = PetDNA.RANGES
    if field_key not in ranges:
        return None
    lo, hi, typ = ranges[field_key]
    try:
        v = typ(raw)
        return v if lo <= v <= hi else None
    except (TypeError, ValueError):
        return None


def _fill_missing(values: dict) -> dict:
    from pygame_int.main_digipet.pet_dna import PetDNA
    pool     = PetDNA.generate_random()
    pool_map = {
        "wave_freq":     pool.wave_freq,
        "amplitude":     pool.amplitude,
        "droop":         pool.droop,
        "blend_ms":      pool.blend_ms,
        "speed_base":    pool.speed_base,
        "noise_ceiling": pool.noise_ceiling,
        "stroke_width":  pool.stroke_width,
    }
    return {k: (v if v is not None else pool_map[k]) for k, v in values.items()}


def _build_dna(filled: dict):
    from pygame_int.main_digipet.pet_dna import PetDNA
    return PetDNA(
        wave_freq     = int(filled["wave_freq"]),
        amplitude     = float(filled["amplitude"]),
        droop         = float(filled["droop"]),
        blend_ms      = int(filled["blend_ms"]),
        speed_base    = float(filled["speed_base"]),
        noise_ceiling = float(filled["noise_ceiling"]),
        stroke_width  = int(filled["stroke_width"]),
    )


def run_dna_selector_ui(screen: pygame.Surface, font: pygame.font.Font):
    from pygame_int.main_digipet.pet_dna import PetDNA

    sw, sh = screen.get_width(), screen.get_height()
    clock  = pygame.time.Clock()

    try:
        accent = state.pet_color if hasattr(state, "pet_color") and state.pet_color else (100, 255, 180)
    except Exception:
        accent = (100, 255, 180)

    try:
        mono      = pygame.font.SysFont("Courier New", 15)
        hint_font = pygame.font.SysFont("Courier New", 12)
    except Exception:
        mono      = font
        hint_font = font

    # ------------------------------------------------------------------
    # Layout — fully responsive
    # ------------------------------------------------------------------
    h_padding    = 40
    usable_w     = sw - 2 * h_padding
    slot_spacing = max(8, usable_w // 40)
    slot_size    = min(72, (usable_w - (_N - 1) * slot_spacing) // _N)
    total_w      = _N * slot_size + (_N - 1) * slot_spacing
    start_x      = (sw - total_w) // 2

    slots_y  = sh // 2 - slot_size # // 2
    label_y  = slots_y - 26
    hint_y   = slots_y + slot_size + 14

    # Buttons stacked vertically, centred
    btn_w       = min(180, sw - 80)
    btn_h       = 38
    btn_spacing = 12
    rand_y      = hint_y + 30
    cont_y      = rand_y + btn_h + btn_spacing
    btn_x       = (sw - btn_w) // 2

    # ------------------------------------------------------------------
    # TextInputBox instances
    # ------------------------------------------------------------------
    text_inputs = {}
    boxes = []
    for i, (_, field_key, _) in enumerate(_FIELDS):
        x = start_x + i * (slot_size + slot_spacing)
        box = TextInputBox(
            x, slots_y, slot_size, slot_size,
            mono, field_key,
            text_inputs=text_inputs,
            active_element=None,
        )
        boxes.append(box)

    # ------------------------------------------------------------------
    # PulsingText letter labels
    # ------------------------------------------------------------------
    labels = []
    for i, (letter, _, _) in enumerate(_FIELDS):
        cx = start_x + i * (slot_size + slot_spacing) + slot_size // 2
        pt = PulsingText(
            letter, font, (cx, label_y),
            color=_NEUTRAL,
            ang_velocity=0.003 + i * 0.0003,
        )
        pt.show()
        labels.append(pt)

    # ------------------------------------------------------------------
    # Buttons — stacked vertically, centred
    # ------------------------------------------------------------------
    rand_btn = Button(
        btn_x, rand_y, btn_w, btn_h,
        "FILL MISSING...", font,
        action=lambda: "randomize",
        button_color=(30, 30, 40),
        hover_color=(50, 50, 65),
        text_color=_NEUTRAL,
    )

    cont_btn = Button(
        btn_x, cont_y, btn_w, btn_h,
        "ENTER", font,
        action=lambda: "continue",
        button_color=(30, 30, 40),
        hover_color=(50, 50, 65),
        text_color=_NEUTRAL,
    )
    cont_btn.hidden = True

    # ------------------------------------------------------------------
    # Sync helpers
    # ------------------------------------------------------------------

    def _all_valid() -> bool:
        return all(
            _try_parse(fk, text_inputs[fk].text) is not None
            for _, fk, _ in _FIELDS
        )

    def _sync():
        all_done = _all_valid()
        for i, (_, fk, _) in enumerate(_FIELDS):
            val = _try_parse(fk, text_inputs[fk].text)
            raw = text_inputs[fk].text.strip()
            if val is not None:
                labels[i].hide()
                boxes[i].validation_error = False
            elif raw and val is None:
                # Something typed but invalid — show error immediately
                boxes[i].validation_error = True
                labels[i].show()
                labels[i].update_color(_NEUTRAL)
            else:
                boxes[i].validation_error = False
                labels[i].show()
                labels[i].update_color(_NEUTRAL)

        cont_btn.hidden     = not all_done
        cont_btn.text_color = accent if all_done else _NEUTRAL

    def _do_randomize():
        values = {fk: _try_parse(fk, text_inputs[fk].text) for _, fk, _ in _FIELDS}
        filled = _fill_missing(values)
        for _, fk, _ in _FIELDS:
            if _try_parse(fk, text_inputs[fk].text) is None:
                text_inputs[fk].text = str(filled[fk])
                text_inputs[fk]._render_text()
        _sync()

    def _do_continue():
        if _all_valid():
            values = {fk: _try_parse(fk, text_inputs[fk].text) for _, fk, _ in _FIELDS}
            return _build_dna(values)
        return None

    _sync()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    result_dna = None
    running    = True

    while running:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                _do_randomize()
                result_dna = _do_continue()
                if result_dna:
                    running = False

            for box in boxes:
                box.handle_event(event, mouse_pos)
            _sync()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if rand_btn.handle_event(event, mouse_pos) == "randomize":
                    _do_randomize()
                if not cont_btn.hidden:
                    if cont_btn.handle_event(event, mouse_pos) == "continue":
                        result_dna = _do_continue()
                        if result_dna:
                            running = False

        # ------------------------------------------------------------------
        # Draw
        # ------------------------------------------------------------------
        screen.fill(_BG)

        all_done  = _all_valid()

        # Labels
        for lbl in labels:
            lbl.draw(screen)

        # Boxes
        for box in boxes:
            box.draw(screen, 0)

        # Buttons
        rand_btn.draw(screen, mouse_pos, 0)
        cont_btn.draw(screen, mouse_pos, 0)

        # Seed preview at bottom
        parts    = [str(_try_parse(fk, text_inputs[fk].text)) if _try_parse(fk, text_inputs[fk].text) is not None else "?" for _, fk, _ in _FIELDS]
        prev_col = accent if all_done else _MUTED
        p_surf   = hint_font.render("  .  ".join(parts), True, prev_col)
        screen.blit(p_surf, p_surf.get_rect(centerx=sw // 2, bottom=sh - 16))

        pygame.display.flip()

    return result_dna or PetDNA.generate_random()