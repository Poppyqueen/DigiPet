"""
game.py
-------
Entry point and main game loop for DigiPet.

This file is intentionally thin.  All heavy logic lives in:

    initializer.py   — one-time startup (pygame, chatbot, state, splash)
    signal_handler.py — translates agent signals into Pygame events
    event_handler.py  — processes Pygame events each frame
    workers.py        — background threads (chatbot, garden tick)

The loop itself has four responsibilities:
    1. Advance timers and cursor state.
    2. Dispatch Pygame events (custom + input).
    3. Trigger autonomous actions and simulation ticks.
    4. Draw the frame.
"""

import sys

import pygame

from pygame_int import config, state
from pygame_int.main_digipet import gui
from pygame_int.juke_box import jukebox

from pygame_runtime.signal_handler import make_signal_handler
from pygame_runtime.initializer    import initialize
from pygame_runtime.event_handler  import handle_custom_events, handle_input_events
from pygame_runtime.workers        import start_chatbot_request, start_garden_tick_request


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GAME_MODE = "ai_player"
# Options: "ai_player"   — autonomous AI agent controls the pet
#          "user_player" — human types commands directly
#
# NOTE: The AI-powered environment crafter (Make Home) calls an LLM
#       even in "user_player" mode.


# ---------------------------------------------------------------------------
# Helpers shared across this file
# ---------------------------------------------------------------------------

def clean_hover() -> None:
    """Reset all hover-related state variables."""
    state.hover_stat               = None
    state.hovered_package_identifier = None


def add_items(items_list: list, room_id: str) -> None:
    """
    Place a list of items into the specified room via the state manager,
    then notify the agent's short-term memory.
    """
    current_time_ms = pygame.time.get_ticks()

    if current_time_ms < state.autonomous_action_paused_until_ms or state.inventory_panel_visible:
        reason = "bot is resting." if current_time_ms < state.autonomous_action_paused_until_ms else "inventory panel is open."
        gui.gui_text_utils.add_message_to_history(f"Cannot add items while {reason}", "system")
        return

    gui.gui_text_utils.add_message_to_history("Adding items to room…", "system")

    result = ctx.chatbot.state_manager.create_item(
        target_location="room", target_location_id=room_id, item_creation_data=items_list
    )
    if not result.success:
        gui.gui_text_utils.add_message_to_history(f"Error adding items: {result.error}", "system")
        return

    room_name = ctx.chatbot.state_manager.get_room_data(room_id).name
    ctx.chatbot.memory.save_to_memory(
        string_to_save=f"A package of helpful items has been delivered in {room_name}.",
        memory_type="short_term",
        tag="user",
    )
    gui.gui_text_utils.add_message_to_history("Items added successfully!", "system")


def _maybe_init_music_player() -> None:
    """
    Called once per frame until the splash popup clears.
    Initialises the jukebox and stores it in ctx.music_player_ref[0].
    """
    if ctx.music_player_ref[0] is not None:
        return  # Already initialised.
    if not gui.gui_popups.is_any_image_popup_currently_active():
        state.is_initial_popup_phase = False
        if pygame.mixer.get_init():
            try:
                room_data = ctx.chatbot.state_manager.get_current_room_data()
                ctx.music_player_ref[0] = jukebox(
                    f"style/sounds/music/rooms/{room_data.music}.mp3"
                )
                print("[game] Jukebox initialised.")
            except Exception as exc:
                print(f"[game] Jukebox init failed: {exc}")


def _trigger_autonomous_action(current_time_ms: int) -> None:
    """Fire an autonomous agent turn when the idle timeout elapses."""
    elapsed = current_time_ms - state.last_activity_time
    timeout = ctx.idle_time_mins * 60 * 1000

    if (
        ctx.chatbot_available
        and ctx.chatbot
        and elapsed >= timeout
        and current_time_ms >= state.autonomous_action_paused_until_ms
        and not state.chatbot_is_processing
        and ctx.game_mode in ("ai_player", "mock")
    ):
        print(f"[game] Idle timeout ({ctx.idle_time_mins} min) — triggering autonomous action.")
        gui.gui_text_utils.add_message_to_history(
            "Triggering autonomous action due to inactivity.", "system"
        )
        music_player = ctx.music_player_ref[0]
        if music_player:
            music_player.play_sound_effect(
                f"style/sounds/autonomous_action/{state.pet_sound}"
            )
        start_chatbot_request(
            "Automated internal message: The following should be an autonomous action.",
            "user",
            chatbot=ctx.chatbot,
            chatbot_available=ctx.chatbot_available,
            clean_hover_fn=clean_hover,
        )


def _trigger_garden_tick(current_time_ms: int) -> None:
    """Advance simulations when the tick timer fires."""
    if current_time_ms < state.next_garden_tick_time:
        return

    launched = start_garden_tick_request(
        chatbot=ctx.chatbot,
        chatbot_available=ctx.chatbot_available,
    )
    if launched:
        state.next_garden_tick_time = current_time_ms + ctx.garden_tick_interval_ms
    # If deferred (chatbot busy), next_garden_tick_time stays the same
    # so the tick retries on the very next free frame.


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    global ctx  # Accessible to add_items and helpers above.

    # Build the signal handler first so it can be passed into initialize().
    # Both refs start empty and are filled in after construction.
    chatbot_ref      = [None]
    music_player_ref = [None]
    signal_callback  = make_signal_handler(chatbot_ref, music_player_ref)

    ctx = initialize(GAME_MODE, signal_callback)

    # Wire the chatbot reference into the signal handler.
    chatbot_ref[0]      = ctx.chatbot
    # music_player_ref is ctx.music_player_ref (same list object).

    running_ref = [True]
    CURSOR_BLINK_MS = 500

    # -----------------------------------------------------------------------
    # Game loop
    # -----------------------------------------------------------------------
    while running_ref[0]:
        dt              = ctx.clock.tick(60)
        current_time_ms = pygame.time.get_ticks()

        # Cursor blink
        state.cursor_timer += dt
        if state.cursor_timer >= CURSOR_BLINK_MS and state.cursor_active:
            state.cursor_visible = not state.cursor_visible
            state.cursor_timer   = 0

        # Typing or active processing keeps the idle timer alive.
        if state.cursor_active or state.chatbot_is_processing:
            state.last_activity_time = current_time_ms

        is_input_locked = state.agent_sleeping or state.chatbot_is_processing

        # Update popup animations.
        gui.gui_popups.update_popups(current_time_ms)

        # --- Event loop ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running_ref[0] = False
                break

            # 1. Custom (agent-fired) events.
            if handle_custom_events(
                event,
                chatbot=ctx.chatbot,
                music_player=ctx.music_player_ref[0],
                current_time_ms=current_time_ms,
            ):
                continue

            # 2. Standard input events.
            handle_input_events(
                event,
                current_time_ms=current_time_ms,
                is_input_locked=is_input_locked,
                chatbot=ctx.chatbot,
                chatbot_available=ctx.chatbot_available,
                music_player=ctx.music_player_ref[0],
                clean_hover_fn=clean_hover,
                running_ref=running_ref,
                add_items_fn=add_items,
            )

        # --- Autonomous logic ---
        _trigger_autonomous_action(current_time_ms)
        _trigger_garden_tick(current_time_ms)

        # --- Draw ---
        is_input_locked = state.agent_sleeping or state.chatbot_is_processing
        gui.draw_gui(screen=ctx.screen, current_time_ms=current_time_ms, is_input_locked=is_input_locked)

        # --- Init jukebox once splash clears ---
        if state.is_initial_popup_phase:
            _maybe_init_music_player()

        pygame.display.flip()

    # -----------------------------------------------------------------------
    # Shutdown
    # -----------------------------------------------------------------------
    if ctx.chatbot and callable(getattr(ctx.chatbot, "shutdown", None)):
        try:
            ctx.chatbot.shutdown()
            print("[game] Chatbot shutdown complete.")
        except Exception as exc:
            print(f"[game] Chatbot shutdown error: {exc}")

    if pygame.mixer.get_init():
        pygame.mixer.quit()

    pygame.quit()
    print("[game] Goodbye!")
    sys.exit()


if __name__ == "__main__":
    main()