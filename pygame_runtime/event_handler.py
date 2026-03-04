"""
event_handler.py
----------------
Processes every Pygame event that enters the main loop.

Responsibility split
--------------------
- Custom events (signals from the agent)  → handle_custom_events()
- Standard input events (mouse, keyboard) → handle_input_events()

The main game loop calls both in order each frame.

Design notes
------------
- No drawing happens here.  All rendering stays in gui.draw_gui().
- State mutations happen via the ``state`` module (shared mutable state).
- Chatbot requests are started via the ``workers`` module.
- The music_player is passed in because it starts as None and may change.
"""

import pygame

from pygame_int import config, state
from pygame_int.main_digipet import animation, gui, gui_lore_panel

from pygame_runtime.workers import start_chatbot_request


# ---------------------------------------------------------------------------
# Custom (agent-posted) event handlers
# One function per event type keeps each case short and testable.
# ---------------------------------------------------------------------------

def _on_change_background(event) -> None:
    image_path = getattr(event, "image_path", None)
    if image_path:
        gui.gui_core.load_and_set_background(image_path)
    else:
        print("[event] CHANGE_BACKGROUND_EVENT — missing image_path.")


def _on_tts_sound(event, music_player) -> None:
    raw_audio = getattr(event, "raw_audio_data", None)
    if raw_audio and music_player:
        music_player.play_raw_sound_effect(raw_audio)
    elif not music_player:
        print("[event] TTS_PYGAME_SOUND_EVENT — music_player not ready.")


def _on_shake_circle(_event) -> None:
    animation.start_circle_shake()


def _on_chatbot_response(event, chatbot, current_time_ms: int) -> None:
    response_text = getattr(event, "text", None)
    message_type  = getattr(event, "msg_type", "bot")

    # Refresh the pet's displayed size whenever the bot responds.
    steps = chatbot.state_manager.get_steps()
    state.current_radius = _calculate_sized_by_steps(
        steps, config.CIRCLE_RADIUS, 100
    )

    if not response_text:
        return

    gui.gui_text_utils.add_message_to_history(response_text, message_type)
    animation.start_circle_shake()

    if message_type != "system":
        state.last_activity_time   = current_time_ms
        state.chatbot_is_processing = False

    print(
        f"[event] CHATBOT_RESPONSE ({message_type}). "
        f"Idle reset: {'yes' if message_type != 'system' else 'no'}."
    )


def _on_update_lore_display(event) -> None:
    room_data  = getattr(event, "room_data", {})
    lore_title = room_data.get("title", "Info Title Not Found")
    lore_body  = room_data.get("body",  "No content received.")

    print(f"[event] UPDATE_LORE_DISPLAY — title: {lore_title}")
    state.lore_panel_content = gui_lore_panel.prepare_lore_content_data(
        lore_title, lore_body
    )
    if state.lore_panel_visible:
        state.lore_panel_scroll_y = 0


def _on_room_inventory(event) -> None:
    item_list = getattr(event, "item_list", None)
    if isinstance(item_list, list):
        state.room_inventory_list = [
            gui.gui_inventory.prepare_inventory_item_data(item)
            for item in item_list
        ]
        state.room_inventory_scroll_y = 0
        print(f"[event] ROOM_INVENTORY — {len(state.room_inventory_list)} items.")
    else:
        print("[event] ROOM_INVENTORY — invalid item_list.")


def _on_player_inventory(event) -> None:
    item_list = getattr(event, "item_list", None)
    if isinstance(item_list, list):
        state.player_inventory_list = [
            gui.gui_inventory.prepare_inventory_item_data(item)
            for item in item_list
        ]
        state.player_inventory_scroll_y = 0
    else:
        print("[event] PLAYER_INVENTORY — invalid item_list.")


def _on_start_sleep(_event) -> None:
    state.agent_sleeping = True
    gui.gui_text_utils.add_message_to_history("Entering sleep state.", "system")


def _on_end_sleep(_event) -> None:
    state.agent_sleeping = False
    gui.gui_text_utils.add_message_to_history("Woke up from sleep.", "system")


def _on_message_popup(event) -> None:
    message = getattr(event, "message", "")
    color   = getattr(event, "color", None)
    gui.gui_popups.show_popup_message(message, color)


def _on_stat_changed(event) -> None:
    stat_name = getattr(event, "stat_name", None)
    new_value  = getattr(event, "new_value", None)

    if stat_name not in state.pet_stats or not isinstance(new_value, (int, float)):
        print(f"[event] STAT_CHANGED — invalid data: {stat_name=}, {new_value=}")
        return

    old_value = state.pet_stats[stat_name]
    state.pet_stats[stat_name] = new_value
    change = new_value - old_value

    if abs(change) > 0.001:
        current_fmt = f"{new_value:.1f}"
        change_fmt  = f"{change:+.3f}"
        popup_text  = f"{stat_name.capitalize()}: {current_fmt} ({change_fmt})"
        color = (0, 255, 0) if change >= 0 else (255, 0, 0)
        gui.gui_popups.show_popup_message(popup_text, color)


def _on_show_icon_popup(event) -> None:
    icon_path   = getattr(event, "icon_path", None)
    duration_ms = getattr(event, "duration_ms", 2000)
    popup_type  = getattr(event, "popup_type", 1)

    if icon_path:
        gui.gui_popups.show_image_popup(icon_path, duration_ms, popup_type=popup_type)
    else:
        print("[event] SHOW_ICON_POPUP_EVENT — missing icon_path.")


# Dispatch table: event type → handler
# Handlers that need extra context receive it via the outer function signature.
_CUSTOM_EVENT_HANDLERS = {
    config.CHANGE_BACKGROUND_EVENT: _on_change_background,
    config.SHAKE_CIRCLE_EVENT:      _on_shake_circle,
    config.ROOM_INVENTORY_EVENT:    _on_room_inventory,
    config.PLAYER_INVENTORY_EVENT:  _on_player_inventory,
    config.START_SLEEP_EVENT:       _on_start_sleep,
    config.END_SLEEP_EVENT:         _on_end_sleep,
    config.MESSAGE_POPUP:           _on_message_popup,
    config.STAT_CHANGED_EVENT:      _on_stat_changed,
    config.SHOW_ICON_POPUP_EVENT:   _on_show_icon_popup,
    config.UPDATE_LORE_DISPLAY_EVENT: _on_update_lore_display,
}


def handle_custom_events(event, *, chatbot, music_player, current_time_ms: int) -> bool:
    """
    Dispatch one Pygame event to its custom-event handler.

    Returns True if the event was consumed (caller should ``continue``).
    """
    if event.type == config.TTS_PYGAME_SOUND_EVENT:
        _on_tts_sound(event, music_player)
        return True

    if event.type == config.CHATBOT_RESPONSE_EVENT:
        _on_chatbot_response(event, chatbot, current_time_ms)
        return True

    handler = _CUSTOM_EVENT_HANDLERS.get(event.type)
    if handler:
        handler(event)
        return True

    return False  # Not a custom event; let handle_input_events() see it.


# ---------------------------------------------------------------------------
# Input (mouse / keyboard) event handlers
# ---------------------------------------------------------------------------

def _handle_inventory_panel_events(
    event, *, inventory_toggle_button_rect, room_list_area_rect, player_list_area_rect
) -> bool:
    """
    When the inventory panel is open it behaves modally:
    only scroll + close interactions are accepted.

    Returns True if the event was consumed.
    """
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        if state.lore_panel_visible:
            state.lore_panel_visible = False
        else:
            state.inventory_panel_visible = False
        return True

    if event.type != pygame.MOUSEBUTTONDOWN:
        return False

    # Close button
    if (
        inventory_toggle_button_rect
        and inventory_toggle_button_rect.collidepoint(event.pos)
        and event.button == 1
    ):
        state.inventory_panel_visible = False
        return True

    # Scroll wheel inside list areas
    if event.button in (4, 5):
        scroll_delta = config.SCROLL_SPEED * (-1 if event.button == 4 else 1)

        if room_list_area_rect and room_list_area_rect.collidepoint(event.pos):
            room_h = gui.gui_inventory.calculate_list_height(state.room_inventory_list)
            max_scroll = max(0, room_h - room_list_area_rect.height)
            state.room_inventory_scroll_y = max(
                0, min(state.room_inventory_scroll_y + scroll_delta, max_scroll)
            )
            return True

        if player_list_area_rect and player_list_area_rect.collidepoint(event.pos):
            player_h = gui.gui_inventory.calculate_list_height(state.player_inventory_list)
            max_scroll = max(0, player_h - player_list_area_rect.height)
            state.player_inventory_scroll_y = max(
                0, min(state.player_inventory_scroll_y + scroll_delta, max_scroll)
            )
            return True

    return False


def _handle_mouse_motion(event) -> None:
    """Update hover state for care packages and stat icons."""
    if state.inventory_panel_visible or state.lore_panel_visible:
        return

    package_regions = gui.gui_care_package.get_package_button_click_regions()
    stats_rects     = gui.gui_stat_icons.get_stat_icon_rects()

    # Care package hover
    new_hover = None
    for identifier, rect in package_regions:
        if rect.collidepoint(event.pos):
            new_hover = identifier
            break

    if state.hovered_package_identifier != new_hover:
        state.hovered_package_identifier = new_hover
        state.package_scroll_y = 0

    # Stat icon hover
    state.hover_stat = None
    for name, rect in stats_rects.items():
        if rect.collidepoint(event.pos):
            state.hover_stat = name
            break


def _handle_mouse_button(
    event,
    *,
    current_time_ms: int,
    is_input_locked: bool,
    chatbot,
    chatbot_available: bool,
    music_player,
    clean_hover_fn,
    lore_toggle_button_rect,
    inventory_toggle_button_rect,
    mute_button_rect,
    history_display_area,
    add_items_fn,
) -> bool:
    """
    Handle MOUSEBUTTONDOWN events when the inventory panel is NOT open.

    Returns True if the event was consumed.
    """
    # Lore panel toggle
    if (
        lore_toggle_button_rect
        and lore_toggle_button_rect.collidepoint(event.pos)
        and event.button == 1
    ):
        if not state.lore_panel_visible:
            state.lore_panel_visible  = True
            state.lore_panel_scroll_y = 0
        return True

    if state.lore_panel_visible:
        return False  # Lore panel is open; don't handle other clicks.

    # Inventory toggle (open)
    if (
        inventory_toggle_button_rect
        and inventory_toggle_button_rect.collidepoint(event.pos)
        and event.button == 1
    ):
        state.inventory_panel_visible   = True
        state.room_inventory_scroll_y   = 0
        state.player_inventory_scroll_y = 0
        return True

    # Mute button
    if (
        mute_button_rect
        and mute_button_rect.collidepoint(event.pos)
        and event.button == 1
        and music_player
    ):
        music_player.toggle_mute()
        state.is_muted = music_player.get_is_muted()
        status = "muted" if state.is_muted else "unmuted"
        gui.gui_text_utils.add_message_to_history(f"Music toggled {status}.", "system")
        return True

    # Panel toggle
    all_buttons     = gui.gui_core.get_button_rects()
    panel_toggle    = all_buttons.get("panel_toggle")
    if panel_toggle and panel_toggle.collidepoint(event.pos) and event.button == 1:
        state.panel_visible = not state.panel_visible
        if state.panel_visible:
            state.panel_width = config.DEFAULT_PANEL_WIDTH
        gui.gui_core.update_gui_rects(state.panel_width)
        return True

    # Chat history scroll
    if history_display_area and history_display_area.collidepoint(event.pos):
        if event.button == 4:
            state.scroll_y -= config.SCROLL_SPEED
        elif event.button == 5:
            state.scroll_y += config.SCROLL_SPEED
        total_h   = gui.gui_text_utils.calculate_total_history_height(state.chat_history)
        max_scroll = max(0, total_h - history_display_area.height)
        state.scroll_y = max(0, min(state.scroll_y, max_scroll))
        return True

    # Care package scroll wheel
    if state.hovered_package_identifier:
        scroll_info = gui.gui_care_package.get_package_scroll_info()
        if event.button == 4:
            state.package_scroll_y = max(0, state.package_scroll_y - scroll_info["line_height"])
        elif event.button == 5:
            state.package_scroll_y = min(scroll_info["max_scroll"], state.package_scroll_y + scroll_info["line_height"])

    # Care package buttons (left-click only, not locked)
    if not is_input_locked and not state.inventory_panel_visible and event.button == 1:
        return _handle_care_package_click(
            event,
            chatbot=chatbot,
            add_items_fn=add_items_fn,
        )

    return False


def _handle_care_package_click(event, *, chatbot, add_items_fn) -> bool:
    """Process clicks on care-package and scroll buttons."""
    for identifier, rect in gui.gui_care_package.get_package_button_click_regions():
        if not rect.collidepoint(event.pos):
            continue

        if identifier == "scroll_left":
            if state.package_button_visible_start_index > 0:
                state.package_button_visible_start_index -= 1
            return True

        if identifier == "scroll_right":
            total    = len(config.CARE_PACKAGES)
            per_page = gui.gui_core._buttons_per_page
            if state.package_button_visible_start_index + per_page < total:
                state.package_button_visible_start_index += 1
            return True

        if identifier.startswith("package_"):
            try:
                idx = int(identifier.split("_")[1])
            except (ValueError, IndexError):
                print(f"[event] Could not parse package index from: {identifier}")
                return True

            if 0 <= idx < len(config.CARE_PACKAGES):
                package_info = config.CARE_PACKAGES[idx]
                room_data    = chatbot.state_manager.get_current_room_data()
                add_items_fn(package_info["package"], room_data.id)

                item_names = ", ".join(i["name"] for i in package_info["package"])
                message    = f"Items placed in: {room_data.name}"
                gui.gui_popups.show_popup_message(message)
                gui.gui_text_utils.add_message_to_history(
                    f"{message}. Items: {item_names}", "system"
                )
            return True

    return False


def _handle_keyboard(
    event,
    *,
    current_time_ms: int,
    is_input_locked: bool,
    chatbot,
    chatbot_available: bool,
    music_player,
    clean_hover_fn,
    running_ref: list,
) -> bool:
    """
    Handle KEYDOWN events.

    ``running_ref`` is a single-element list [True] so we can signal
    the main loop to quit without a global variable.

    Returns True if the event was consumed.
    """
    key = event.key

    # Escape: close panels or quit.
    if key == pygame.K_ESCAPE:
        if state.inventory_panel_visible:
            state.inventory_panel_visible = False
        else:
            running_ref[0] = False
        return True

    # Developer shortcut: manually trigger autonomous action.
    if key == pygame.K_5 and pygame.key.get_mods() & pygame.KMOD_CTRL:
        start_chatbot_request(
            "Automated internal message: The following should be an autonomous action.",
            "user",
            chatbot=chatbot,
            chatbot_available=chatbot_available,
            clean_hover_fn=clean_hover_fn,
        )
        return True

    if is_input_locked:
        return True  # Swallow all other keys while locked.

    # Active text input (cursor is on and bot is idle).
    if state.cursor_active and not state.chatbot_is_processing:
        state.last_activity_time = current_time_ms

        if key == pygame.K_BACKSPACE:
            state.input_text   = state.input_text[:-1]
            state.cursor_timer = 0
            state.cursor_visible = True
            return True

        if key == pygame.K_RETURN:
            user_message = state.input_text.strip()
            state.input_text   = ""
            state.cursor_timer = 0
            state.cursor_visible = True
            if user_message:
                gui.gui_text_utils.add_message_to_history(user_message, "user")
                start_chatbot_request(
                    user_message,
                    "user",
                    chatbot=chatbot,
                    chatbot_available=chatbot_available,
                    clean_hover_fn=clean_hover_fn,
                )
            return True

        if event.unicode and event.unicode.isprintable():
            state.input_text    += event.unicode
            state.cursor_timer   = 0
            state.cursor_visible = True
            return True

    else:
        # Hotkeys available when cursor is inactive.
        if key == pygame.K_i:
            clean_hover_fn()
            state.inventory_panel_visible = not state.inventory_panel_visible
            return True

        if key == pygame.K_c:
            state.panel_visible = not state.panel_visible
            return True

        if key == pygame.K_m and music_player:
            music_player.toggle_mute()
            state.is_muted = music_player.get_is_muted()
            status = "muted" if state.is_muted else "unmuted"
            gui.gui_text_utils.add_message_to_history(
                f"Music toggled {status}.", "system"
            )
            return True

    return False


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def handle_input_events(
    event,
    *,
    current_time_ms: int,
    is_input_locked: bool,
    chatbot,
    chatbot_available: bool,
    music_player,
    clean_hover_fn,
    running_ref: list,
    add_items_fn,
) -> bool:
    """
    Process one standard input event (mouse / keyboard).

    Fetches button rects fresh on each call so they reflect the latest
    GUI layout recalculation.

    Returns True if the event was consumed.
    """
    # Always let the GUI module pre-process the event (tooltips etc.).
    gui.handle_gui_event(event)

    # Fetch latest button/panel rects.
    button_rects = gui.gui_core.get_button_rects()
    gui_rects    = gui.gui_core.get_gui_rects()

    inventory_toggle  = button_rects.get("inventory_toggle")
    mute_button       = button_rects.get("mute_button")
    lore_toggle       = button_rects.get("lore_toggle")
    history_area      = gui_rects.get("history_display_area")

    room_list_area   = None
    player_list_area = None
    if state.inventory_panel_visible:
        panel_rects      = gui.gui_core.get_panel_rects()
        room_list_area   = panel_rects.get("room_list_area")
        player_list_area = panel_rects.get("player_list_area")

    # ------- Modal inventory panel -------
    if state.inventory_panel_visible:
        return _handle_inventory_panel_events(
            event,
            inventory_toggle_button_rect=inventory_toggle,
            room_list_area_rect=room_list_area,
            player_list_area_rect=player_list_area,
        )

    # ------- Mouse motion (hover) -------
    if event.type == pygame.MOUSEMOTION:
        _handle_mouse_motion(event)
        return True

    # ------- Mouse button -------
    if event.type == pygame.MOUSEBUTTONDOWN:
        return _handle_mouse_button(
            event,
            current_time_ms=current_time_ms,
            is_input_locked=is_input_locked,
            chatbot=chatbot,
            chatbot_available=chatbot_available,
            music_player=music_player,
            clean_hover_fn=clean_hover_fn,
            lore_toggle_button_rect=lore_toggle,
            inventory_toggle_button_rect=inventory_toggle,
            mute_button_rect=mute_button,
            history_display_area=history_area,
            add_items_fn=add_items_fn,
        )

    # ------- Keyboard -------
    if event.type == pygame.KEYDOWN:
        return _handle_keyboard(
            event,
            current_time_ms=current_time_ms,
            is_input_locked=is_input_locked,
            chatbot=chatbot,
            chatbot_available=chatbot_available,
            music_player=music_player,
            clean_hover_fn=clean_hover_fn,
            running_ref=running_ref,
        )

    return False


# ---------------------------------------------------------------------------
# Utility (used here and potentially by game.py)
# ---------------------------------------------------------------------------

def _calculate_sized_by_steps(
    current_steps: int,
    start_size: int,
    end_size: int,
    step_limit: int = None,
) -> int:
    """
    Linearly interpolate size between start_size and end_size over step_limit steps.
    Clamps at end_size once the limit is reached.
    """
    if step_limit is None:
        from pygame_int import config as _config
        step_limit = _config.STEP_SIZE_LIMIT

    if step_limit == 0:
        return start_size

    scale  = min(current_steps, step_limit) / step_limit
    result = start_size + (end_size - start_size) * scale
    return int(max(start_size, min(result, end_size)))