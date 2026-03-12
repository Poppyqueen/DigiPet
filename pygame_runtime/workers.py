"""
workers.py
----------
Background thread workers for the game.

Each worker runs in its own daemon thread so it never blocks the main
Pygame loop.  Results / side-effects are communicated back to the main
thread exclusively through pygame.event.post(), which is thread-safe.

Workers in this file
--------------------
- chatbot_worker        : runs one AI turn and posts CHATBOT_RESPONSE_EVENT
- garden_tick_worker    : advances garden / lighthouse / TV simulations
"""

import asyncio
import threading

import pygame

from pygame_int import config, state
from pygame_int.main_digipet import gui


# ---------------------------------------------------------------------------
# Chatbot worker
# ---------------------------------------------------------------------------

def chatbot_worker(user_input: str, input_role: str, chatbot_instance) -> None:
    """
    Runs ``chatbot_instance.process_input`` in a background thread.

    On success  → posts CHATBOT_RESPONSE_EVENT(text=..., msg_type='bot')
    On failure  → posts CHATBOT_RESPONSE_EVENT(text=error, msg_type='error')
    On no text  → returns silently (signals were already fired by the agent)
    """
    response_text = None
    message_type = "bot"

    try:
        response_text = asyncio.run(
            chatbot_instance.process_input(user_input, role=input_role)
        )

        # The agent may have communicated only through signals (no text body).
        if not response_text or not response_text.strip():
            return

        message_text = response_text.strip()

    except Exception as exc:
        message_text = f"Bot Error: {type(exc).__name__}: {exc}"
        message_type = "error"
        print(f"[chatbot_worker] {message_text}")

    if message_text:
        pygame.event.post(
            pygame.event.Event(
                config.CHATBOT_RESPONSE_EVENT,
                text=message_text,
                msg_type=message_type,
            )
        )


def start_chatbot_request(
    user_input: str,
    input_role: str = "user",
    *,
    chatbot,
    chatbot_available: bool,
    clean_hover_fn,
) -> bool:
    """
    Gate-check then spawn a chatbot_worker thread.

    Returns True if the thread was launched, False otherwise.
    ``clean_hover_fn`` should be game.clean_hover (passed in to avoid
    circular imports).
    """
    current_time_ms = pygame.time.get_ticks()
    clean_hover_fn()

    # Block user-initiated requests while the bot is resting.
    if input_role == "user" and current_time_ms < state.autonomous_action_paused_until_ms:
        reason = "bot is resting."
        print(f"[start_chatbot_request] Input locked — {reason}")
        gui.gui_text_utils.add_message_to_history(
            f"Cannot send input while {reason}", "system"
        )
        return False

    if not chatbot_available or not chatbot:
        print("[start_chatbot_request] Chatbot not available.")
        return False

    print(f"[start_chatbot_request] Spawning thread (role={input_role}): {user_input[:50]}…")
    state.chatbot_is_processing = True
    thread = threading.Thread(
        target=chatbot_worker,
        args=(user_input, input_role, chatbot),
        daemon=True,
    )
    thread.start()
    return True


# ---------------------------------------------------------------------------
# Garden / simulation tick worker
# ---------------------------------------------------------------------------

def garden_tick_worker(chatbot_instance) -> None:
    """
    Advances all time-based simulations (garden, lighthouse, TV) then
    posts UPDATE_LORE_DISPLAY_EVENT with fresh room data.

    Designed to run in a daemon thread; never touches Pygame directly
    except through event posting.
    """
    # Safety: bail out early if the registry isn't ready.
    registry = getattr(
        getattr(chatbot_instance, "functions_builder", None), "registry", None
    )
    garden_manager = getattr(registry, "garden_manager", None)
    if not callable(getattr(garden_manager, "tick", None)):
        print("[garden_tick_worker] Garden manager not ready — skipping tick.")
        return

    print("[garden_tick_worker] Tick started.")
    try:
        registry.garden_manager.tick()
        registry.lighthouse.lighthouse_tick()
        registry.tv_controller.tv_tick()
        registry.item_toggle.tick()
        print("[garden_tick_worker] Tick complete.")

        room_info = chatbot_instance.functions_builder.get_current_tools_info()
        if not isinstance(room_info, dict):
            room_info = {}

        pygame.event.post(
            pygame.event.Event(config.UPDATE_LORE_DISPLAY_EVENT, room_data=room_info)
        )

    except Exception as exc:
        print(f"[garden_tick_worker] Error: {type(exc).__name__}: {exc}")


def start_garden_tick_request(*, chatbot, chatbot_available: bool) -> bool:
    """
    Gate-check then spawn a garden_tick_worker thread.

    Returns True if the thread was launched.
    Skips silently if the chatbot is busy (except during sleep).
    """
    if not chatbot_available or not chatbot:
        return False

    if state.chatbot_is_processing and not state.agent_sleeping:
        return False  # Defer; the tick timer is NOT advanced so it retries next frame.

    thread = threading.Thread(
        target=garden_tick_worker,
        args=(chatbot,),
        daemon=True,
    )
    thread.start()
    return True


# ---------------------------------------------------------------------------
# Lore panel refresh worker
# ---------------------------------------------------------------------------

def _lore_refresh_worker(chatbot_instance) -> None:
    """
    Streams fresh tool info and posts UPDATE_LORE_DISPLAY_EVENT.

    Uses the streaming variant (get_current_tools_info_streaming) so the
    lore panel content arrives incrementally rather than waiting for a full
    round-trip.  Designed to run in a daemon thread.
    """
    def _post(room_data):
        pygame.event.post(
            pygame.event.Event(config.UPDATE_LORE_DISPLAY_EVENT, room_data=room_data)
        )

    try:
        chatbot_instance.functions_builder.get_current_tools_info_streaming(_post)
    except Exception as exc:
        print(f"[_lore_refresh_worker] Error: {type(exc).__name__}: {exc}")


def start_lore_panel_refresh(*, chatbot) -> None:
    """
    Spawn a background thread to refresh the lore panel content.

    Called when the user opens the lore panel so the content is always
    up to date.  Fire-and-forget: no gate checks needed since this is
    a read-only data fetch that doesn't affect the chatbot's state.
    """
    if not chatbot:
        return
    thread = threading.Thread(
        target=_lore_refresh_worker,
        args=(chatbot,),
        daemon=True,
    )
    thread.start()