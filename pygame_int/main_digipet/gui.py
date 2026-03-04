# gui.py
#
# Responsibilities
# ----------------
# Facade and orchestrator for all rendering.
#
# Two public functions for the game loop
# ---------------------------------------
#   draw_gui(screen, current_time_ms, is_input_locked)
#       Draws the complete frame.  Reads state; does not mutate it.
#       (Two legacy state mutations remain inside the input-box render
#        block — state.scroll_y clamp and state.cursor_visible = False.
#        These are low-priority and tracked in ARCHITECTURE.md.)
#
#   handle_gui_event(event)
#       Pre-processes input events for GUI-internal concerns:
#         1. Lore panel scroll + close  (modal, highest priority)
#         2. Clock click  (gui_clock.handle_clock_click — real side effect)
#         3. Input box focus / unfocus  (cursor_active state)
#       This is NOT a passive observer — it mutates state.
#
# What changed from the original
# --------------------------------
# - All gui_core._font / _line_height / _*_button_rect private accesses
#   replaced with public getter calls:
#     gui_core.get_font()          instead of gui_core._font
#     gui_core.get_line_height()   instead of gui_core._line_height
#     button_rects["..."]          instead of gui_core._*_button_rect
#
# - update_gui_rects() is still called at the top of draw_gui() to ensure
#   layout is always fresh before rendering.  With the dirty flag added in
#   gui_core.py this call is free when nothing has changed.

from pygame_int import config
from pygame_int import state
from pygame_int.main_digipet import animation

from pygame_int.main_digipet import gui_core
from pygame_int.main_digipet import gui_text_utils
from pygame_int.main_digipet import gui_inventory
from pygame_int.main_digipet import gui_popups
from pygame_int.main_digipet import gui_care_package

from pygame_int.main_digipet import gui_lore_panel
from pygame_int.main_digipet import gui_stat_icons
from pygame_int.main_digipet import gui_clock

import pygame

from utils.time_manager import get_time_tag_from_now


# ---------------------------------------------------------------------------
# Time-of-day overlay
# ---------------------------------------------------------------------------

ALPHA_MULTIPLIERS = {
    'late night':    1.2,
    'early morning': 1.1,
    'morning':       0.8,
    'noon':          0.6,
    'afternoon':     0.8,
    'late afternoon': 1.0,
    'night':         1.1,
    None:            1.0,
}


def draw_filter_overlay(screen: pygame.Surface) -> None:
    """
    Draw a translucent colour tint whose opacity scales with time of day.
    Reads the theme's overlay colour and multiplies its alpha by a time factor.
    """
    timetag = get_time_tag_from_now()

    original_color = state.game_theme_colors["overlay_color_with_alpha"]
    base_rgb   = original_color[:3]
    base_alpha = original_color[3]

    multiplier    = ALPHA_MULTIPLIERS.get(timetag, ALPHA_MULTIPLIERS[None])
    dynamic_alpha = int(base_alpha * multiplier)
    clamped_alpha = min(150, max(30, dynamic_alpha))

    gui_core.overlay_surface.fill((0, 0, 0, 0))
    pygame.draw.rect(
        gui_core.overlay_surface,
        (*base_rgb, clamped_alpha),
        (0, 0, config.WIDTH, config.HEIGHT),
    )
    screen.blit(gui_core.overlay_surface, (0, 0))


# ---------------------------------------------------------------------------
# GUI event pre-processor  (called by handle_input_events before hit-testing)
# ---------------------------------------------------------------------------

def handle_gui_event(event) -> None:
    """
    Handle GUI-internal input concerns in priority order.

    Priority chain
    --------------
    1. Lore panel  — modal: consumes all clicks when open
    2. Clock        — gui_clock.handle_clock_click() mutates clock state
    3. Input box    — focus / unfocus (cursor_active)
    """
    if event.type != pygame.MOUSEBUTTONDOWN:
        return

    mouse_pos     = event.pos
    current_rects = gui_core.get_gui_rects()
    input_rect    = current_rects.get("input_rect")

    # --- Priority 1: Lore panel (modal) ---
    if state.lore_panel_visible:
        lore_rects         = gui_core.get_lore_panel_rects()
        lore_body_area     = lore_rects.get("lore_body_area")
        lore_close_button  = lore_rects.get("lore_close_button")

        if event.button in (4, 5) and lore_body_area and lore_body_area.collidepoint(mouse_pos):
            scroll_delta = config.LORE_PANEL_SCROLL_SPEED * (-1 if event.button == 4 else 1)
            state.lore_panel_scroll_y += scroll_delta
            content_h     = gui_lore_panel.calculate_lore_body_height(state.lore_panel_content)
            max_scroll    = max(0, content_h - lore_body_area.height)
            state.lore_panel_scroll_y = max(0, min(state.lore_panel_scroll_y, max_scroll))
            return

        if event.button == 1 and lore_close_button and lore_close_button.collidepoint(mouse_pos):
            print("[gui] Lore panel closed.")
            state.lore_panel_visible = False
            return

        return  # Consume all other clicks while lore panel is open.

    # --- Priority 2: Clock ---
    if event.button == 1 and not state.inventory_panel_visible:
        if gui_clock.handle_clock_click(mouse_pos):
            return

    # --- Priority 3: Input box focus ---
    if event.button == 1 and not state.chatbot_is_processing:
        if state.panel_visible and input_rect and not state.agent_sleeping:
            if not input_rect.collidepoint(mouse_pos):
                if state.cursor_active:
                    gui_text_utils.add_message_to_history("Input box inactive...", "system")
                state.cursor_active  = False
                state.cursor_visible = False
            else:
                if not state.cursor_active:
                    gui_text_utils.add_message_to_history("Input box active...", "system")
                state.cursor_active = True
        else:
            state.cursor_active  = False
            state.cursor_visible = False


# ---------------------------------------------------------------------------
# Main draw function
# ---------------------------------------------------------------------------

def draw_gui(screen: pygame.Surface, current_time_ms: int, is_input_locked: bool) -> None:
    """
    Draw the complete frame.

    Call order
    ----------
    background → overlay → pet → panel → stat icons → care packages →
    popups → clock → inventory modal → buttons → lore panel → border
    """
    # Ensure layout geometry is up to date.
    # With the dirty flag in gui_core, this is free when nothing changed.
    gui_core.update_gui_rects(state.panel_width)

    current_rects = gui_core.get_gui_rects()
    font          = gui_core.get_font()
    line_height   = gui_core.get_line_height()
    button_rects  = gui_core.get_button_rects()

    if font is None or line_height == 0:
        print("[gui] draw_gui called before font is initialised.")
        return

    # ---- Splash phase: only draw image popups ----
    if state.is_initial_popup_phase:
        gui_popups.draw_active_image_popups(screen)
        gui_popups.draw_popups(screen)
        return

    # ---- Background ----
    if state.background_image:
        screen.blit(state.background_image, (0, 0))
    else:
        screen.fill(config.fallback_bg_color)

    draw_filter_overlay(screen)

    # ---- Pet circle ----
    cx = config.get_base_circle_center_x(state.panel_width if state.panel_visible else 0)
    cy = config.BASE_CIRCLE_CENTER_Y
    animation.update_animation_state(current_time_ms)
    ox, oy = animation.calculate_circle_offset(current_time_ms)
    cx += ox
    cy += oy
    pygame.draw.circle(screen, config.BLACK,     (int(cx), int(cy)), state.current_radius)
    pygame.draw.circle(screen, state.pet_color,  (int(cx), int(cy)), state.current_radius, 5)

    # ---- Side panel ----
    if state.panel_visible:
        panel_rect          = current_rects["panel_rect"]
        input_rect          = current_rects["input_rect"]
        history_rect        = current_rects["history_rect"]
        history_display_area = current_rects["history_display_area"]

        pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], panel_rect)
        pygame.draw.rect(screen, state.game_theme_colors["contrast_color"],     history_rect)
        pygame.draw.rect(screen, state.game_theme_colors["contrast_color"],     input_rect)

        # -- Chat history --
        if history_display_area and history_display_area.height > 0:
            total_h    = gui_text_utils.calculate_total_history_height(state.chat_history)
            max_scroll = max(0, total_h - history_display_area.height)
            state.scroll_y = max(0, min(state.scroll_y, max_scroll))  # clamp (legacy; also done in update phase)

            content_top_y  = history_display_area.bottom - total_h + state.scroll_y - config.PADDING
            original_clip  = screen.get_clip()
            screen.set_clip(history_display_area.copy())

            msg_y = content_top_y
            for msg in state.chat_history:
                msg_h      = msg.get("total_height", 0)
                msg_bottom = msg_y + msg_h
                if msg_bottom < history_display_area.top or msg_y > history_display_area.bottom:
                    msg_y += msg_h
                    continue
                line_y = msg_y
                for line_surface in msg.get("rendered_surfaces", []):
                    if line_surface is None:
                        line_y += line_height
                        continue
                    line_bottom = line_y + line_height
                    if not (line_bottom < history_display_area.top or line_y > history_display_area.bottom):
                        screen.blit(line_surface, (history_display_area.left + config.HISTORY_HORIZONTAL_PADDING, line_y))
                    line_y += line_height
                msg_y += msg_h

            screen.set_clip(original_clip)

        # -- Input box --
        if input_rect:
            draw_area = pygame.Rect(
                input_rect.left   + config.PADDING,
                input_rect.top    + config.PADDING,
                input_rect.width  - 2 * config.PADDING,
                input_rect.height - 2 * config.PADDING,
            )
            original_clip = screen.get_clip()
            screen.set_clip(draw_area.copy())

            if is_input_locked:
                display_text = "The bot is currently sleeping." if state.agent_sleeping else "Waiting for bot..."
                try:
                    surf = font.render(display_text, True, state.game_theme_colors["original_pet_color"])
                    screen.blit(surf, (
                        draw_area.left + (draw_area.width  - surf.get_width())  // 2,
                        draw_area.top  + (draw_area.height - surf.get_height()) // 2,
                    ))
                except pygame.error as exc:
                    print(f"[gui] Error rendering locked input text: {exc}")
                state.cursor_visible = False  # legacy mutation; also handled in update phase
            else:
                text_color = state.game_theme_colors["user_message_color"]
                display_text = state.input_text
                width_limit  = draw_area.width

                # Clip text from left if it overflows
                clipped = display_text
                try:
                    while font.size(clipped)[0] > width_limit and len(clipped) > 0:
                        clipped = clipped[1:]
                    surf = font.render(clipped, True, text_color)
                    text_x = draw_area.left
                    text_y = draw_area.top + (draw_area.height - surf.get_height()) // 2
                    screen.blit(surf, (text_x, text_y))

                    if state.cursor_visible:
                        cursor_x = text_x + font.size(clipped)[0]
                        cursor_x = max(draw_area.left, min(cursor_x, draw_area.right - 1))
                        pygame.draw.line(
                            screen, state.game_theme_colors["user_message_color"],
                            (cursor_x, text_y),
                            (cursor_x, text_y + surf.get_height()),
                            1,
                        )
                except pygame.error as exc:
                    print(f"[gui] Error rendering input text: {exc}")

            screen.set_clip(original_clip)
            pygame.draw.rect(screen, config.GREY, input_rect, 1)

    # ---- Stat icons, care packages, popups, clock ----
    gui_stat_icons.draw_stat_icons(screen)
    gui_care_package.draw_package_buttons(screen, is_input_locked)
    gui_popups.draw_popups(screen)
    gui_popups.draw_active_image_popups(screen)
    gui_clock.draw_current_time(screen)
    gui_clock.draw_sleep_duration(screen)

    # ---- Inventory modal ----
    if state.inventory_panel_visible:
        gui_inventory.draw_inventory_panel(screen)

    # ---- Inventory toggle button ----
    inv_toggle = button_rects.get("inventory_toggle")
    if inv_toggle:
        border_color = state.game_theme_colors["original_pet_color"]
        pygame.draw.circle(screen, state.game_theme_colors["contrast_color"], inv_toggle.center, config.INVENTORY_TOGGLE_BUTTON_SIZE // 2)
        pygame.draw.circle(screen, border_color,                               inv_toggle.center, config.INVENTORY_TOGGLE_BUTTON_SIZE // 2, 2)

        # ---- Panel toggle button (drawn here, inside the inv_toggle block in original) ----
        panel_toggle = button_rects.get("panel_toggle")
        if panel_toggle:
            pygame.draw.rect(screen, state.game_theme_colors["original_pet_color"], panel_toggle)
            arrow = ">" if state.panel_visible else "<"
            try:
                arrow_surf = font.render(arrow, True, state.game_theme_colors["contrast_color"])
                screen.blit(arrow_surf, arrow_surf.get_rect(center=panel_toggle.center))
            except pygame.error as exc:
                print(f"[gui] Error rendering panel toggle arrow: {exc}")

    # ---- Lore toggle button ----
    lore_toggle = button_rects.get("lore_toggle")
    if lore_toggle:
        border_color = state.game_theme_colors["original_pet_color"]
        border_rect  = lore_toggle.inflate(4, 4)
        pygame.draw.rect(screen, border_color,                              border_rect)
        pygame.draw.rect(screen, state.game_theme_colors["contrast_color"], lore_toggle)
        try:
            text_surf = font.render("Info", True, border_color)
            screen.blit(text_surf, text_surf.get_rect(center=lore_toggle.center))
        except pygame.error as exc:
            print(f"[gui] Error rendering lore toggle text: {exc}")

    # ---- Mute button ----
    mute_btn = button_rects.get("mute_button")
    if mute_btn:
        btn_color    = state.game_theme_colors["system_messages"] if state.is_muted else state.game_theme_colors["original_pet_color"]
        border_color = config.MUTE_BUTTON_BORDER_COLOR
        icon_color   = config.WHITE if state.is_muted else config.BLACK

        pygame.draw.circle(screen, btn_color,    mute_btn.center, mute_btn.width // 2)
        pygame.draw.circle(screen, border_color, mute_btn.center, mute_btn.width // 2, 1)

        # Speaker body
        sw = mute_btn.width  // 4
        sh = mute_btn.height // 3
        sx = mute_btn.centerx - sw // 2 - mute_btn.width // 8
        sy = mute_btn.centery - sh // 2
        pygame.draw.rect(screen, icon_color, (sx, sy, sw, sh))

        # Speaker horn
        pygame.draw.polygon(screen, icon_color, [
            (sx + sw,          sy),
            (sx + sw + sw // 2, mute_btn.centery),
            (sx + sw,          sy + sh),
        ])

        if state.is_muted:
            pygame.draw.line(
                screen, icon_color,
                (mute_btn.left  + mute_btn.width  // 4, mute_btn.top    + mute_btn.height // 4),
                (mute_btn.right - mute_btn.width  // 4, mute_btn.bottom - mute_btn.height // 4),
                2,
            )

    # ---- Lore panel (topmost layer) ----
    if state.lore_panel_visible:
        gui_lore_panel.draw_lore_panel(screen)

    # ---- Screen border ----
    pygame.draw.rect(screen, state.pet_color, pygame.Rect(0, 0, screen.get_width(), screen.get_height()), config.PADDING)