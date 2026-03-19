"""
tick_registry.py
----------------
A modular, per-service tick scheduler.
"""

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Callable

import pygame

from pygame_int import config, state


@dataclass
class _ServiceEntry:
    name:           str
    fn:             Callable[[], None]
    interval_ms:    float
    next_tick_ms:   float = 0.0
    enabled:        bool  = True


class TickRegistry:

    def __init__(self, chatbot) -> None:
        self._services: dict[str, _ServiceEntry] = {}
        self._chatbot = chatbot

    def register(self, name, fn, interval_ms, *, start_delay_ms=0.0, enabled=True):
        now = pygame.time.get_ticks()
        self._services[name] = _ServiceEntry(
            name         = name,
            fn           = fn,
            interval_ms  = interval_ms,
            next_tick_ms = now + interval_ms + start_delay_ms,
            enabled      = enabled,
        )

    def unregister(self, name):  self._services.pop(name, None)
    def enable(self, name):
        if name in self._services: self._services[name].enabled = True
    def disable(self, name):
        if name in self._services: self._services[name].enabled = False
    def set_interval(self, name, interval_ms):
        if name in self._services: self._services[name].interval_ms = interval_ms

    # ------------------------------------------------------------------
    # Per-frame update — MUST stay cheap; never block here
    # ------------------------------------------------------------------

    def tick(self, current_time_ms, chatbot_is_processing, agent_sleeping) -> None:
        any_fired = False

        for entry in self._services.values():
            if not entry.enabled:
                continue
            if current_time_ms < entry.next_tick_ms:
                continue
            if chatbot_is_processing and not agent_sleeping:
                continue

            self._fire(entry, current_time_ms)
            any_fired = True

        if any_fired:
            self._post_lore_update()

    def _fire(self, entry: _ServiceEntry, current_time_ms: int) -> None:
        entry.next_tick_ms = current_time_ms + entry.interval_ms
        print(f"[TickRegistry] Firing '{entry.name}'")

        def _worker():
            try:
                entry.fn()
            except Exception as exc:
                print(f"[TickRegistry] {entry.name} error: {type(exc).__name__}: {exc}")

        threading.Thread(target=_worker, daemon=True, name=f"tick-{entry.name}").start()

    def _post_lore_update(self) -> None:
        """
        Fetch fresh tool info and post UPDATE_LORE_DISPLAY_EVENT.

        IMPORTANT: asyncio.run() must never be called on the main pygame thread
        because it blocks until the coroutine completes — including any MCP
        subprocess round-trips (GetPromptRequest etc.) that can take 100ms+.

        This mirrors the pattern used in signal_handler._trigger_lore_panel_update
        and workers._lore_refresh_worker: hand the async work to a daemon thread
        so the game loop keeps ticking at 60fps.
        """
        def _worker():
            try:
                room_info = asyncio.run(
                    self._chatbot.functions_builder.get_current_tools_info()
                )
                if not isinstance(room_info, dict):
                    room_info = {}
                pygame.event.post(
                    pygame.event.Event(config.UPDATE_LORE_DISPLAY_EVENT, room_data=room_info)
                )
            except Exception as exc:
                print(f"[TickRegistry] lore post error: {type(exc).__name__}: {exc}")

        threading.Thread(target=_worker, daemon=True, name="tick-lore-update").start()