from __future__ import annotations
import threading
from typing import TYPE_CHECKING

from ai_managers.ai_utils.ai_loader import AIConfiguration
from utils.time_manager import get_time_tag_from_now
from tools.tools_folder.tools_helpers.tv_utils.tv_models import TVProgram
from tools.tools_folder.tools_helpers.tv_utils.tv_channels_definitions import TV_TYPE_CHANNELS

if TYPE_CHECKING:
    from utils.config_manager import ConfigManager
    from ai_managers.simple_ai.abstract_provider import SimpleAI

import time


class TVContent:
    """
    Handles all AI generation for TV programs.

    Generates one program at a time, per channel, on demand.
    The time tag is passed to the AI as context only — it does not
    control any structural logic.

    Thread safety — single-flight / request coalescing pattern:
        Each (tv_type, channel_name) pair has its own lock and an
        "is_generating" flag. When a second caller arrives while
        generation is in flight:

          blocking=True:  waits for the lock, then returns None.
                          TVManager re-checks has_content() after this —
                          the first caller already saved the result, so
                          the second caller gets it for free without
                          triggering a second generation.

          blocking=False: returns None immediately without waiting.
                          Used by fire-and-forget callers like
                          get_current_accessible_tv.
        generate_program() only returns a TVProgram when THIS call
        is the one that actually ran the AI. In all other cases it
        returns None — the caller must re-check channel state.
    """


    def __init__(self, config_manager: ConfigManager):
        config_model = config_manager.get_config("AI", "cook_model")
        selected_config_client = config_manager.get_config("AI", "cook_provider")
        self.client: SimpleAI = AIConfiguration(
            provider=selected_config_client, model=config_model, mode="simple_ai"
        ).get_client()

        # (tv_type, channel_name) -> Lock
        self._generation_locks: dict[tuple[str, str], threading.Lock] = {}
        # (tv_type, channel_name) -> bool — True while generation is actively running
        self._is_generating: dict[tuple[str, str], bool] = {}
        self._locks_mutex = threading.Lock()  # Protects both dicts above

    def get_channel_blueprints(self, tv_type: str) -> list[dict]:
        return TV_TYPE_CHANNELS.get(tv_type) or next(iter(TV_TYPE_CHANNELS.values()), [])

    def _get_lock(self, tv_type: str, channel_name: str) -> threading.Lock:
        """Get or create the lock for a specific (tv_type, channel_name) pair."""
        key = (tv_type, channel_name)
        with self._locks_mutex:
            if key not in self._generation_locks:
                self._generation_locks[key] = threading.Lock()
                self._is_generating[key] = False
            return self._generation_locks[key]

    def is_generating(self, tv_type: str, channel_name: str) -> bool:
        """Return True if a generation is currently in flight for this channel."""
        key = (tv_type, channel_name)
        with self._locks_mutex:
            return self._is_generating.get(key, False)

    def generate_program(
        self,
        tv_type: str,
        channel_name: str,
        channel_description: str,
        channel_ai_extra_prompt: str,
        blocking: bool = True,
    ) -> TVProgram | None:
        """
        Generate a single program for the given channel.

        Returns a TVProgram only when THIS call is the one that ran the AI.
        Returns None in all other cases — the caller (TVManager) must
        re-check channel state after getting None, because the first caller
        may have already saved the result while this one was waiting.

        blocking=True  (default):
            Waits if another thread is generating. After the wait, returns
            None — TVManager will re-check has_content() and serve the
            cached result without generating again. This is the coalescing
            hook: all waiters piggyback on the first caller's result.

        blocking=False:
            Returns None immediately if generation is in flight.
            Used by fire-and-forget callers (e.g. get_current_accessible_tv).
        """
        key = (tv_type, channel_name)
        lock = self._get_lock(tv_type, channel_name)

        # Check if currently generating before attempting to acquire
        currently_generating = self.is_generating(tv_type, channel_name)

        acquired = lock.acquire(blocking=blocking)

        if not acquired:
            # Non-blocking and lock was taken — walk away
            print(f"[TVContent] '{channel_name}' generating — skipping (non-blocking).")
            return None

        if currently_generating:
            # We waited (blocking=True) and the lock was just released by the
            # generator — the result is already saved. Signal caller to re-check.
            print(f"[TVContent] '{channel_name}' — coalesced onto completed generation, re-check channel state.")
            lock.release()
            return None

        # We acquired the lock and nothing was generating — we are the generator
        with self._locks_mutex:
            self._is_generating[key] = True

        try:
            time_tag = get_time_tag_from_now()

            system_prompt = (
                "You are a Lead Screenwriter for an immersive game world. "
                "Your task is to write the ACTUAL SCRIPT for a TV broadcast, not a description of it. "
                "Use a screenplay format: \n"
                "- Use [brackets] for visual actions, camera cuts, and sound effects.\n"
                "- Use 'Character Name: Dialogue' for spoken lines.\n"
                "- Include on-screen graphics or tickers in quotes.\n"
                "Write in the present tense. Ensure the content feels 'in-the-moment' and "
                "specific to the channel's theme. Avoid meta-commentary like 'the scene shows'."
            )
            user_prompt = (
                f"CHANNEL CONTEXT:\n"
                f"- Type: {tv_type}\n"
                f"- Name: {channel_name}\n"
                f"- Description: {channel_description}\n"
                f"- Extra Prompt: {channel_ai_extra_prompt}\n"
                f"- Current World Time: {time_tag}\n\n"
                f"TASK:\n"
                f"Write a script for the program currently airing. It must have 3-6 sections. "
                f"Each section should represent a continuous flow of the broadcast.\n\n"
                f"Generate the script for {channel_name} now:"
            )


            print(f"DEBUG TV CONTENT")
            print(f"[TVContent] Generating '{channel_name}'...")
            print(f"System Prompt: {system_prompt}")
            print(f"User Prompt: {user_prompt}")

            program: TVProgram = self.client.structured_output(
                system=system_prompt,
                user=user_prompt,
                structure=TVProgram,
            )

            # # --- SIMULATION ---
            # sleep_time = 5
            # print(f"[TVContent] Generating '{channel_name}'... sleeping {sleep_time}s")
            # time.sleep(sleep_time)
            # print(f"[TVContent] Done generating '{channel_name}'")
            # program = TVProgram(
            #     name="Test Program",
            #     sections=["Test Section", "Test Section 1", "Test Section 2", "Test Section 3"],
            #     section_index=0,
            # )
            return program

        finally:
            with self._locks_mutex:
                self._is_generating[key] = False
            lock.release()