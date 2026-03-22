"""
tick_registry.py
----------------
A modular, per-service tick scheduler.
"""

import threading
from dataclasses import dataclass, field
from typing import Callable

import pygame
from pygame_int import config, state


@dataclass
class _ServiceEntry:
    name:        str
    callback:    Callable
    interval_ms: float
    next_tick_ms: float = 0
    enabled:     bool   = True


class TickRegistry:

    def __init__(self):
        self._services: dict[str, _ServiceEntry] = {}

    def register(self, name: str, callback: Callable, interval_ms: float, enabled: bool = True):
        self._services[name] = _ServiceEntry(
            name         = name,
            callback     = callback,
            interval_ms  = interval_ms,
            enabled      = enabled,
        )

    def unregister(self, name):
        self._services.pop(name, None)

    def enable(self, name):
        if name in self._services:
            self._services[name].enabled = True

    def disable(self, name):
        if name in self._services:
            self._services[name].enabled = False

    def set_interval(self, name, interval_ms):
        if name in self._services:
            self._services[name].interval_ms = interval_ms

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
            pygame.event.post(pygame.event.Event(config.UPDATE_LORE_DISPLAY_EVENT))

    def _fire(self, entry: _ServiceEntry, current_time_ms: int) -> None:
        entry.next_tick_ms = current_time_ms + entry.interval_ms

        def _worker():
            try:
                print(f"[TickRegistry] Firing '{entry.name}'")
                entry.callback()
            except Exception as exc:
                print(f"[TickRegistry] {entry.name} error: {type(exc).__name__}: {exc}")

        threading.Thread(target=_worker, daemon=True, name=f"tick-{entry.name}").start()