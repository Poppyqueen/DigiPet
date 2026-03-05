from __future__ import annotations
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from tools.tools_folder.tools_helpers.tv_utils.tv_content import TVContent
from tools.tools_folder.tools_helpers.tv_utils.tv_models import TVProgram

if TYPE_CHECKING:
    from utils.config_manager import ConfigManager


# Range for rolling a random none_ticks cap when a channel resets
NONE_TICKS_CAP_MIN = 3
NONE_TICKS_CAP_MAX = 8


@dataclass
class ChannelState:
    """
    Runtime state for a single channel within a tv_type broadcast.

    sections:       AI-generated program sections, or None if exhausted/not yet generated.
    index:          Current section index being shown, or None if no content.
    none_ticks:     How many ticks this channel has spent with no content.
    none_ticks_cap: Randomly rolled cap for none_ticks. On reaching it, resets to 0 and rerolls.
    program_name:   Name of the current program, for display purposes.
    """
    name: str
    description: str
    ai_extra_prompt: str = ""
    sections: list[str] | None = None
    index: int | None = None
    none_ticks: int = 0
    none_ticks_cap: int = field(
        default_factory=lambda: random.randint(NONE_TICKS_CAP_MIN, NONE_TICKS_CAP_MAX)
    )
    program_name: str = ""

    def has_content(self) -> bool:
        return self.sections is not None

    def is_exhausted(self) -> bool:
        """True if index has advanced past the last section."""
        return self.sections is not None and self.index >= len(self.sections)

    def current_section(self) -> str | None:
        if not self.has_content() or self.is_exhausted():
            return None
        return self.sections[self.index]

    def exhaust(self) -> None:
        """Called when the program finishes. Clears content and resets none_ticks."""
        self.sections = None
        self.index = None
        self.program_name = ""
        self.none_ticks = 0
        self.none_ticks_cap = random.randint(NONE_TICKS_CAP_MIN, NONE_TICKS_CAP_MAX)

    def load_program(self, program: TVProgram, none_ticks: int) -> None:
        """
        Slot in a newly generated program and pick the starting index.
          none_ticks == 0  ->  fresh start, begin at index 0
          none_ticks  > 0  ->  mid-show feel, begin at a random index (avoiding last 2)
        """
        self.sections = program.sections
        self.program_name = program.name
        self.none_ticks = 0

        max_sections = len(program.sections)
        if none_ticks == 0:
            self.index = 0
        else:
            safe_max = max(0, max_sections - 2)
            self.index = random.randint(0, safe_max)


@dataclass
class TVTypeRegistry:
    """
    Shared broadcast state for one tv_type.
    All physical TVs of the same type show the same channel content.
    """
    channels: dict[str, ChannelState] = field(default_factory=dict)  # channel_name -> ChannelState


class TVManager:
    """
    Central registry for all active tv_types.

    Responsibilities:
        - Register new tv_types on first access, populating channel stubs from blueprints
        - Lazily generate channel content on demand (only when a channel is actually watched)
        - Advance all channel indexes on each tick
        - Exhaust and reset channels when their program ends
        - Track none_ticks per channel to determine fresh-start vs mid-show index on generation
        - Persist full registry to JSON on every mutation and reload on startup

    Does NOT own per-TV state — current_channel lives on the inventory item itself,
    read and written by TVController via state_manager.

    JSON structure:
        {
            "bar": {
                "Channel 1 - Sports Live": {
                    "name": "...", "description": "...", "ai_extra_prompt": "...",
                    "sections": [...] | null,
                    "index": int | null,
                    "none_ticks": int,
                    "none_ticks_cap": int,
                    "program_name": "..."
                },
                ...
            },
            ...
        }
    """

    def __init__(self, base_path: str, config_manager: ConfigManager):
        self.filepath = Path(base_path) / "tv_data.json"
        self.content = TVContent(config_manager)
        # tv_type -> TVTypeRegistry
        self._registry: dict[str, TVTypeRegistry] = {}
        self._load_state()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_state(self) -> None:
        """Serialize the full registry to JSON."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for tv_type, registry in self._registry.items():
            data[tv_type] = {
                channel_name: {
                    "name": ch.name,
                    "description": ch.description,
                    "ai_extra_prompt": ch.ai_extra_prompt,
                    "sections": ch.sections,
                    "index": ch.index,
                    "none_ticks": ch.none_ticks,
                    "none_ticks_cap": ch.none_ticks_cap,
                    "program_name": ch.program_name,
                }
                for channel_name, ch in registry.channels.items()
            }
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2)

    def _load_state(self) -> None:
        """Reload the registry from JSON if it exists."""
        if not self.filepath.exists():
            return
        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
            for tv_type, channels_data in data.items():
                registry = TVTypeRegistry()
                for channel_name, ch in channels_data.items():
                    registry.channels[channel_name] = ChannelState(
                        name=ch["name"],
                        description=ch["description"],
                        ai_extra_prompt=ch["ai_extra_prompt"],
                        sections=ch["sections"],
                        index=ch["index"],
                        none_ticks=ch["none_ticks"],
                        none_ticks_cap=ch["none_ticks_cap"],
                        program_name=ch["program_name"],
                    )
                self._registry[tv_type] = registry
        except (json.JSONDecodeError, KeyError):
            self._registry = {}  # Corrupt state — start fresh

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_type_registered(self, tv_type: str) -> TVTypeRegistry:
        """Register a tv_type if not already known. Populates channel stubs from blueprints."""
        if tv_type not in self._registry:
            blueprints = self.content.get_channel_blueprints(tv_type)
            registry = TVTypeRegistry()
            for bp in blueprints:
                registry.channels[bp["name"]] = ChannelState(
                    name=bp["name"],
                    description=bp["description"],
                    ai_extra_prompt=bp.get("extra_prompt", ""),  
                )
            self._registry[tv_type] = registry
        return self._registry[tv_type]

    def _ensure_channel_has_content(self, tv_type: str, channel: ChannelState, blocking: bool = True) -> bool:
        """
        Ensure a channel has content, generating it if needed.

        blocking=True  (default): waits if generation is in flight, then re-checks
                                  channel state — the first caller's result is reused
                                  (single-flight coalescing). Always returns True.
        blocking=False: returns False immediately if generation is in flight.
                        Used by fire-and-forget callers like get_current_accessible_tv.

        Returns True if content is ready, False if non-blocking and generation is in flight.
        """
        if not channel.has_content():
            none_ticks = channel.none_ticks
            program = self.content.generate_program(tv_type, channel.name, channel.description, channel.ai_extra_prompt, blocking=blocking)

            if program is None:
                # Two cases:
                # 1. blocking=False and lock was taken — bail out, content not ready
                # 2. blocking=True and we waited — first caller already saved content,
                #    re-check has_content() to serve the coalesced result
                if channel.has_content():
                    # Case 2: coalesced — content arrived while we waited, we're good
                    return True
                # Case 1: non-blocking miss — content not ready
                return False

            # We were the generator — load and save
            channel.load_program(program, none_ticks)
            self._save_state()
        return True

    # ------------------------------------------------------------------
    # Public API (called by TVController)
    # ------------------------------------------------------------------

    def get_first_channel_name(self, tv_type: str) -> str | None:
        """Return the name of the first channel for a tv_type. Used to default current_channel."""
        registry = self._ensure_type_registered(tv_type)
        names = list(registry.channels.keys())
        return names[0] if names else None

    def get_current_section(self, tv_type: str, channel_name: str, blocking: bool = True) -> tuple[str, str] | None:
        """
        Return (program_name, section_text) for the given tv_type + channel.
        blocking=True  (default): waits for generation — use for direct agent calls.
        blocking=False: returns None immediately if generation is in flight.
        """
        registry = self._ensure_type_registered(tv_type)
        channel = registry.channels[channel_name]
        ready = self._ensure_channel_has_content(tv_type, channel, blocking=blocking)
        if not ready:
            return None
        return channel.program_name, channel.current_section()

    def get_all_channels(self, tv_type: str) -> list[ChannelState]:
        """Return all channel states for a tv_type."""
        registry = self._ensure_type_registered(tv_type)
        return list(registry.channels.values())

    def is_valid_channel(self, tv_type: str, channel_name: str) -> bool:
        """Check if a channel name exists for a tv_type."""
        registry = self._ensure_type_registered(tv_type)
        return channel_name in registry.channels

    def tick(self) -> None:
        """
        Advance all channels across all registered tv_types by one tick.

        For channels WITH content:
            - Advance index by 1
            - If now exhausted -> exhaust(), clearing content and resetting none_ticks

        For channels WITHOUT content:
            - Increment none_ticks
            - If none_ticks >= cap -> reset to 0 and roll a new random cap

        Saves state once after all channels have been advanced.
        """
        for registry in self._registry.values():
            for channel in registry.channels.values():
                if channel.has_content():
                    channel.index += 1
                    if channel.is_exhausted():
                        channel.exhaust()
                else:
                    channel.none_ticks += 1
                    if channel.none_ticks >= channel.none_ticks_cap:
                        channel.none_ticks = 0
                        channel.none_ticks_cap = random.randint(NONE_TICKS_CAP_MIN, NONE_TICKS_CAP_MAX)
        self._save_state()