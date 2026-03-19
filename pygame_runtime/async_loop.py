"""
async_loop.py
-------------
A single persistent asyncio event loop running in a background daemon thread.

All MCP async work (connections, tool calls, prompt fetches, session cleanup)
runs on this loop. This solves two problems:

1. anyio cancel scopes must be entered and exited in the same event loop.
   HTTP sessions created here stay here for their entire lifetime.

2. asyncio.run() — which creates a NEW event loop each time — can no longer
   be used for anything that touches an MCP session. Everything goes through
   mcp_loop instead.

Usage
-----
    from pygame_runtime.async_loop import mcp_loop

    # Fire and forget (non-blocking)
    mcp_loop.run(some_coroutine())

    # Block until done (use from sync code only — never from inside the loop)
    result = mcp_loop.run_sync(some_coroutine(), timeout=30)

    # At shutdown
    mcp_loop.stop()

Thread safety
-------------
run() and run_sync() are safe to call from any thread.
Never call run_sync() from a coroutine running on mcp_loop itself — deadlock.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


class AsyncLoopThread:
    """
    A background daemon thread running a persistent asyncio event loop.
    Instantiated once at module level as the mcp_loop singleton.
    """

    def __init__(self) -> None:
        self._loop   = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="mcp-async-loop",
        )
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, coro: Coroutine) -> concurrent.futures.Future:
        """
        Schedule a coroutine on the persistent loop.
        Returns immediately with a Future — does not block the caller.
        Errors are stored in the Future; call .result() to surface them.
        """
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def run_sync(self, coro: Coroutine, timeout: float = 30) -> Any:
        """
        Schedule a coroutine and block the calling thread until it completes.

        Never call this from inside a coroutine running on mcp_loop — deadlock.
        Safe to call from the pygame main thread, daemon threads, or anywhere
        outside the loop.
        """
        return self.run(coro).result(timeout=timeout)

    def stop(self) -> None:
        """Stop the loop if still running, then join the thread."""
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
        print("[AsyncLoopThread] Stopped.")
# ---------------------------------------------------------------------------
# Singleton — import this everywhere
# ---------------------------------------------------------------------------

mcp_loop = AsyncLoopThread()