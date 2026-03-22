"""
signal_handler.py
-----------------
Translates structured signal dicts fired by the AI agent into Pygame
events and/or direct side-effects (animations, music).

The agent never touches Pygame directly; it calls the signal_callback
that was passed to it at construction time.  That callback is
``handle_chatbot_signal`` below.

Signal types (``signal_data["type"]``)
---------------------------------------
change_background   → load new room image + start matching music track
shake_circle        → trigger the circle-shake animation
TTS_AUDIO           → play raw audio bytes through the jukebox
function_called     → display tool-call result in the chat history
emote_changed       → play an emotion animation + optional sound effect
start_sleep         → enter sleep state
end_sleep           → leave sleep state
stat_changed        → push a stat update to the main loop
room_inventory      → refresh the room inventory panel
player_inventory    → refresh the player inventory panel
show_icon_popup     → show a timed icon popup
show_message_popup  → show a timed text popup
play_sound          → play a one-shot sound effect
"""

import asyncio
import threading

import pygame

from pygame_int import config, state
from pygame_int.main_digipet import animation, gui

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_lore_update_in_flight = False

def _trigger_lore_panel_update(chatbot) -> None:
    global _lore_update_in_flight
    if _lore_update_in_flight:
        return
    _lore_update_in_flight = True

    def _post(room_data):
        pygame.event.post(
            pygame.event.Event(config.UPDATE_LORE_DISPLAY_EVENT, room_data=room_data)
        )

    def _stream():
        global _lore_update_in_flight
        try:
            asyncio.run(
                chatbot.functions_builder.get_current_tools_info_streaming(_post)
            )
        except Exception as exc:
            print(f"[signal] lore update error: {type(exc).__name__}: {exc}")
        finally:
            _lore_update_in_flight = False

    threading.Thread(target=_stream, daemon=True).start()


# ---------------------------------------------------------------------------
# Individual signal handlers  (one function per signal type)
# ---------------------------------------------------------------------------

def _on_change_background(signal_data: dict, chatbot, music_player) -> None:
    image_path = signal_data.get("image_path")
    if not image_path:
        print("[signal] 'change_background' missing image_path.")
        return

    print(f"[signal] change_background → {image_path}")
    pygame.event.post(
        pygame.event.Event(config.CHANGE_BACKGROUND_EVENT, image_path=image_path)
    )

    current_room = chatbot.state_manager.get_current_room_data()
    if music_player:
        music_player.play_new_song(
            f"style/sounds/music/rooms/{current_room.music}.mp3"
        )


def _on_shake_circle(_signal_data: dict, **_kwargs) -> None:
    print("[signal] shake_circle")
    pygame.event.post(pygame.event.Event(config.SHAKE_CIRCLE_EVENT))


def _on_tts_audio(signal_data: dict, **_kwargs) -> None:
    raw_sound = signal_data.get("raw_audio_data")
    if raw_sound:
        print("[signal] TTS_AUDIO — raw audio received.")
        pygame.event.post(
            pygame.event.Event(config.TTS_PYGAME_SOUND_EVENT, raw_audio_data=raw_sound)
        )
    else:
        print("[signal] TTS_AUDIO — missing raw_audio_data.")


def _on_function_called(signal_data: dict, **_kwargs) -> None:
    function_name   = signal_data.get("function_name")
    function_result = signal_data.get("function_result")
    muted           = signal_data.get("muted", False)

    if muted:
        shortened = (function_result or "")[:50] + "..."
        display_result = f"Called: {function_name}, result truncated: {shortened}"
    else:
        display_result = f"Called: {function_name}, result: {function_result}"

    print(f"[signal] function_called → posting system message.")
    pygame.event.post(
        pygame.event.Event(
            config.CHATBOT_RESPONSE_EVENT, text=display_result, msg_type="system"
        )
    )
    pygame.event.post(pygame.event.Event(config.SHAKE_CIRCLE_EVENT))


def _on_emote_changed(signal_data: dict, music_player, **_kwargs) -> None:
    emote_name = signal_data.get("emote_name")
    sound_path = signal_data.get("sound_path")

    print("DEBUG EMOTE SIGNAL RECEIVED")
    print("DEBUG EMOTE SIGNAL: ", signal_data)
    print("DEBUG EMOTE SOUND PATH: ", sound_path)
    print("DEBUG EMOTE MUSIC PLAYER: ", music_player)

    emote_map = {
        "sad":      animation.start_sad_animation,
        "happy":    animation.start_happy_animation,
        "angry":    animation.start_angry_animation,
        "excited":  animation.start_excited_animation,
        "thinking": animation.start_thinking_animation,
        "curious":  animation.start_curious_animation,
        "confused": animation.start_confused_animation,
        "neutral": animation.start_neutral_animation,
    }

    if emote_name in emote_map:
        print(f"[signal] emote_changed → {emote_name}")
        emote_map[emote_name]()
        state.current_emote = emote_name
    elif emote_name:
        print(f"[signal] emote_changed — unhandled emote: {emote_name}")

    if sound_path and music_player:
        print("ATTEMPTING TO PLAY SOUND WITH play_sound_effect")
        print("DEBUG EMOTE SOUND PATH: ", sound_path)
        music_player.play_sound_effect(sound_path)


def _on_start_sleep(signal_data: dict, **_kwargs) -> None:
    state.time_to_sleep = signal_data.get("time_to_sleep")
    animation.start_sleep_animation()
    print("[signal] start_sleep")
    pygame.event.post(pygame.event.Event(config.START_SLEEP_EVENT))


def _on_end_sleep(_signal_data: dict, **_kwargs) -> None:
    animation.wake_up_pet()
    state.time_to_sleep = None
    print("[signal] end_sleep")
    pygame.event.post(pygame.event.Event(config.END_SLEEP_EVENT))


def _on_stat_changed(signal_data: dict, **_kwargs) -> None:
    stat_name = signal_data.get("stat_name")
    new_value  = signal_data.get("new_value")

    if not isinstance(stat_name, str) or not isinstance(new_value, (int, float)):
        print(f"[signal] stat_changed — invalid data: {stat_name=}, {new_value=}")
        return

    clamped = max(0.0, min(200.0, new_value))
    print(f"[signal] stat_changed → {stat_name} = {clamped}")
    pygame.event.post(
        pygame.event.Event(
            config.STAT_CHANGED_EVENT,
            stat_name=stat_name.lower(),
            new_value=clamped,
        )
    )


def _on_room_inventory(signal_data: dict, **_kwargs) -> None:
    item_list = signal_data.get("item_list")
    if isinstance(item_list, list):
        pygame.event.post(
            pygame.event.Event(config.ROOM_INVENTORY_EVENT, item_list=item_list)
        )
    else:
        print("[signal] room_inventory — missing or invalid item_list.")


def _on_player_inventory(signal_data: dict, **_kwargs) -> None:
    item_list = signal_data.get("item_list")
    if isinstance(item_list, list):
        pygame.event.post(
            pygame.event.Event(config.PLAYER_INVENTORY_EVENT, item_list=item_list)
        )
    else:
        print("[signal] player_inventory — missing or invalid item_list.")


def _on_show_icon_popup(signal_data: dict, **_kwargs) -> None:
    icon_path   = signal_data.get("icon_path")
    duration_ms = signal_data.get("duration_ms", 2000)
    popup_type  = signal_data.get("popup_type", 1)

    if icon_path:
        print(f"[signal] show_icon_popup → {icon_path}")
        pygame.event.post(
            pygame.event.Event(
                config.SHOW_ICON_POPUP_EVENT,
                icon_path=icon_path,
                duration_ms=duration_ms,
                popup_type=popup_type,
            )
        )
    else:
        print("[signal] show_icon_popup — missing icon_path.")


def _on_show_message_popup(signal_data: dict, **_kwargs) -> None:
    message = signal_data.get("message")
    color   = signal_data.get("color", None)

    if message:
        print(f"[signal] show_message_popup → {message}")
        pygame.event.post(
            pygame.event.Event(config.MESSAGE_POPUP, message=message, color=color)
        )
    else:
        print("[signal] show_message_popup — missing message.")


def _on_play_sound(signal_data: dict, music_player, **_kwargs) -> None:
    sound_path  = signal_data.get("sound_path")
    raw_audio   = signal_data.get("raw_audio_data")

    if not music_player:
        print("[signal] play_sound — music_player not ready.")
        return

    if sound_path:
        print(f"[signal] play_sound → {sound_path}")
        music_player.play_sound_effect(sound_path)
    elif raw_audio:
        sample_rate = signal_data.get("sample_rate", 44100)
        music_player.play_raw_sound_effect(raw_audio, sample_rate=sample_rate)
    else:
        print("[signal] play_sound — missing both sound_path and raw_audio_data.")


# ---------------------------------------------------------------------------
# Dispatch table  (signal type → handler function)
# ---------------------------------------------------------------------------

_SIGNAL_HANDLERS = {
    "change_background":  _on_change_background,
    "shake_circle":       _on_shake_circle,
    "TTS_AUDIO":          _on_tts_audio,
    "function_called":    _on_function_called,
    "emote_changed":      _on_emote_changed,
    "start_sleep":        _on_start_sleep,
    "end_sleep":          _on_end_sleep,
    "stat_changed":       _on_stat_changed,
    "room_inventory":     _on_room_inventory,
    "player_inventory":   _on_player_inventory,
    "show_icon_popup":    _on_show_icon_popup,
    "show_message_popup": _on_show_message_popup,
    "play_sound":         _on_play_sound,
}


# ---------------------------------------------------------------------------
# Public entry point  (pass this as signal_callback to the agent)
# ---------------------------------------------------------------------------

def make_signal_handler(chatbot_ref: list, music_player_ref: list):
    """
    Returns a ``handle_chatbot_signal(signal_data)`` closure.

    Both ``chatbot_ref`` and ``music_player_ref`` are single-element lists
    so the closure always reads the *current* object even if it is replaced
    after construction (e.g. music_player starts as None).

    Usage
    -----
    ::

        chatbot_ref    = [None]
        music_player_ref = [None]
        callback = make_signal_handler(chatbot_ref, music_player_ref)

        chatbot_ref[0]      = AgentChatbot(signal_callback=callback, …)
        music_player_ref[0] = jukebox(…)
    """

    def handle_chatbot_signal(signal_data) -> None:
        chatbot      = chatbot_ref[0]
        music_player = music_player_ref[0]

        if not isinstance(signal_data, dict):
            print(f"[signal_handler] Unexpected format: {signal_data}")
            return

        # Every signal triggers a lore panel refresh.
        _trigger_lore_panel_update(chatbot)

        action_type = signal_data.get("type")
        handler     = _SIGNAL_HANDLERS.get(action_type)

        if handler:
            handler(
                signal_data,
                chatbot=chatbot,
                music_player=music_player,
            )
        else:
            print(f"[signal_handler] Unknown signal type: {action_type!r}")

    return handle_chatbot_signal