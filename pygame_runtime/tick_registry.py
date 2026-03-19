"""
tick_registry.py
----------------
A modular, per-service tick scheduler.

Usage
-----
    registry = TickRegistry()
    registry.register("garden",     garden_manager.tick,     interval_ms=180_000)
    registry.register("lighthouse", lighthouse.lighthouse_tick, interval_ms=300_000)
    registry.register("tv",         tv_controller.tv_tick,   interval_ms=600_000)
    registry.register("item_toggle",item_toggle.tick,         interval_ms=60_000)

    # In the game loop (replaces _trigger_garden_tick):
    registry.tick(current_time_ms, chatbot_is_processing, agent_sleeping)
"""

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

import pygame

from pygame_int import config, state

import asyncio


@dataclass
class _ServiceEntry:
    name:           str
    fn:             Callable[[], None]
    interval_ms:    float
    next_tick_ms:   float = 0.0          # set to now+interval on register()
    enabled:        bool  = True


class TickRegistry:
    """
    Maintains a set of ticked services, each with its own interval.
    Thread-safe for reading; mutation (register/enable/disable) is
    intended for the main thread only.
    """

    def __init__(self, chatbot) -> None:
        self._services: dict[str, _ServiceEntry] = {}
        self._chatbot = chatbot
    # ------------------------------------------------------------------
    # Registration API
    # ------------------------------------------------------------------

    def register(
        self,
        name:        str,
        fn:          Callable[[], None],
        interval_ms: float,
        *,
        start_delay_ms: float = 0.0,    # extra delay before the first tick
        enabled:     bool = True,
    ) -> None:
        """
        Add or replace a service.

        ``fn`` must be a zero-argument callable — wrap methods beforehand:
            registry.register("garden", garden_manager.tick, 180_000)
        """
        now = pygame.time.get_ticks()
        entry = _ServiceEntry(
            name         = name,
            fn           = fn,
            interval_ms  = interval_ms,
            next_tick_ms = now + interval_ms + start_delay_ms,
            enabled      = enabled,
        )
        self._services[name] = entry

    def unregister(self, name: str) -> None:
        self._services.pop(name, None)

    def enable(self, name: str) -> None:
        if name in self._services:
            self._services[name].enabled = True

    def disable(self, name: str) -> None:
        if name in self._services:
            self._services[name].enabled = False

    def set_interval(self, name: str, interval_ms: float) -> None:
        """Hotswap the interval for a service without deregistering it."""
        if name in self._services:
            self._services[name].interval_ms = interval_ms

    # ------------------------------------------------------------------
    # Per-frame update (called from the game loop)
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

        thread = threading.Thread(target=_worker, daemon=True, name=f"tick-{entry.name}")
        thread.start()

    def _post_lore_update(self) -> None:
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