# abstract_chatbot.py
# Abstract base class for all chatbot implementations.
# Owns: TTS lifecycle, the chain-of-actions loop, wellness consequences, logging, shutdown.
# Subclasses own: memory persistence strategy, developer message construction.

import os
import time
import asyncio
from abc import ABC, abstractmethod
from typing import Optional

from utils.capture_text import TextCapture
from utils.open_meteo_handle import OpenMeteoLoc
from utils.loc_datetime import datetime as loc_datetime

from inventory_items.inventory_manager import InventoryHouseManager
from tools.tools_builder.construct_tools import FunctionBuilder
from ai_managers.agents.memory.memory_handle import memory_manager
from ai_managers.agents.ai_handle import ai_bot
from ai_managers.ai_utils.ai_loader import AIConfiguration

from tts_providers.base_tts_provider import BaseTTSProvider
from tts_providers.macos_say_provider import MacOSSaiProvider
from tts_providers.espeak_ng_provider import ESpeakNGProvider
from tts_providers.piper_provider import PiperTTSProvider

from dotenv import load_dotenv
load_dotenv()

# Default filenames inside each bot's archive subdirectory
DEFAULT_MEMORY_DB         = "memory.json"
DEFAULT_DEEP_MEMORY_DB    = "deep_memory.db"
DEFAULT_AI_LOG            = "ai_log.txt"
DEFAULT_INVENTORY_FOLDER  = "inventory"


class BaseChatbot(ABC):
    """
    Shared foundation for all chatbot modes (AI agent, user-interface, mock…).

    Concrete subclasses must implement:
        - process_input(message, role)   — public entry point called by game.py
        - _post_chain_memory_hook()      — what to do with memory after a full chain ends
        - _build_developer_message()     — compose the sys/developer prompt sent to ai_bot
                                           (override to inject subclass-specific context)

    Everything else — TTS, the recursive chain loop, wellness, logging, shutdown — lives here.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        config_manager,
        signal_callback=None,
        bots_archive_dir: str = "data_archive",
        deep_memory_override: bool | None = None,
    ):
        print(f"[{type(self).__name__}] Initializing base systems...")

        self._signal_callback = signal_callback
        self._config_manager  = config_manager  # kept so subclasses can query it

        # ── Identity & paths ──────────────────────────────────────────
        pet_name      = config_manager.get_config("AI", "pets_folder")
        sub_directory = os.path.join(bots_archive_dir, "bots", pet_name)
        os.makedirs(sub_directory, exist_ok=True)
        self._sub_directory = sub_directory

        memory_filepath      = os.path.join(sub_directory, DEFAULT_MEMORY_DB)
        deep_memory_filepath = os.path.join(sub_directory, DEFAULT_DEEP_MEMORY_DB)
        ai_data_filepath     = os.path.join(sub_directory, DEFAULT_AI_LOG)
        inventory_filepath   = os.path.join(sub_directory, DEFAULT_INVENTORY_FOLDER)
        self._ai_data_filepath = ai_data_filepath   # subclasses may need it

        # ── Logging (centralised) ─────────────────────────────────────
        # Single TextCapture instance shared by memory_manager, ai_bot, etc.
        self.text_capture = TextCapture(filepath=ai_data_filepath)

        # ── Location ─────────────────────────────────────────────────
        lat  = config_manager.get_config("location", "latitude")
        long = config_manager.get_config("location", "longitude")
        _env_lat  = os.getenv("LATITUDE")
        _env_long = os.getenv("LONGITUDE")

        location_source = "config"
        if not lat or not long:
            lat, long  = _env_lat, _env_long
            location_source = "environment variables"

        self.open_meteo = OpenMeteoLoc(long=long, lat=lat)
        loc_datetime.set_coordinates(lat, long)

        print(f"[{type(self).__name__}] Location ({location_source}): {lat}, {long}")
        print(f"  Timezone: {self.open_meteo.get_timezone()}")
        print(f"  Weather : {self.open_meteo.get_full_weather()}")

        # ── Core game systems ─────────────────────────────────────────
        deep_memory_flag = config_manager.get_config("AI_DeepMemory", "deep_memory_flag")
        if deep_memory_override is not None:
            deep_memory_flag = deep_memory_override

        self.memory = memory_manager(
            filepath             = memory_filepath,
            deep_memory_filepath = deep_memory_filepath,
            deep_memory          = deep_memory_flag,
            text_capture         = self.text_capture,   # shared instance
            sub_directory        = sub_directory,
            config_manager       = config_manager,
        )

        self.state_manager = InventoryHouseManager(
            inventory_filepath, self._signal_callback, config_manager
        )

        self.functions_builder = FunctionBuilder(
            state_manager  = self.state_manager,
            signal         = self._signal_callback,
            subdirectory   = sub_directory,
            memory_manager = self.memory,
            config_manager = config_manager,
            open_meteo     = self.open_meteo,
        )

        # ── AI client + ai_bot ────────────────────────────────────────
        provider    = config_manager.get_config("AI", "general_ai_provider")
        model_name  = config_manager.get_config("AI", "general_model")

        llm_client = AIConfiguration(
            provider = provider,
            model    = model_name,
            mode     = "agent",
        ).get_client()

        self.ai = ai_bot(
            data_filepath     = ai_data_filepath,
            act_model         = model_name,
            functions_builder = self.functions_builder,
            state_manager     = self.state_manager,
            signal            = self._signal_callback,
            memory_manager    = self.memory,
            llm_client        = llm_client,
        )

        # ── Chain-depth guard ─────────────────────────────────────────
        self.max_recursion_depth: int = 8 # TODO: make this configurable

        # ── TTS ───────────────────────────────────────────────────────
        self.tts_provider: Optional[BaseTTSProvider] = self._init_tts(config_manager)

        # ── Misc ──────────────────────────────────────────────────────
        self.last_response: Optional[str] = None
        self.running: bool = True

        print(f"[{type(self).__name__}] Base initialisation complete.")

    # ------------------------------------------------------------------
    # TTS  (private helper, called once from __init__)
    # ------------------------------------------------------------------

    def _init_tts(self, config_manager) -> Optional[BaseTTSProvider]:
        """Construct and validate the configured TTS provider, or return None."""
        tts_provider_id = config_manager.get_config("game_settings", "tts_provider")
        voice           = config_manager.get_config("game_settings", "selected_voice")

        if not tts_provider_id:
            return None

        provider_map = {
            "macos_say" : lambda: MacOSSaiProvider(signal_callback=self._signal_callback),
            "espeak_ng" : lambda: ESpeakNGProvider(signal_callback=self._signal_callback, voice_name=voice),
            "piper"     : lambda: PiperTTSProvider(signal_callback=self._signal_callback, voice_name=voice),
        }

        factory = provider_map.get(tts_provider_id)
        if factory is None:
            print(f"[TTS] Warning: Unknown provider '{tts_provider_id}'. TTS disabled.")
            return None

        provider = factory()
        if not provider.is_available():
            print(f"[TTS] Warning: '{tts_provider_id}' is not available on this system. TTS disabled.")
            return None

        return provider

    def process_response_with_tts(self, text: str) -> None:
        """Stop any current speech, then synthesize *text* with the active TTS provider."""
        if self.tts_provider:
            self.tts_provider.stop()
            if self.tts_provider.is_available():
                self.tts_provider.synthesize(text)

    # ------------------------------------------------------------------
    # Signal helper
    # ------------------------------------------------------------------

    def _send_signal(self, signal_data: dict) -> None:
        if self._signal_callback:
            print(f"[{type(self).__name__}] Signal: {signal_data}")
            self._signal_callback(signal_data)
        else:
            print(f"[{type(self).__name__}] No callback registered for signal: {signal_data}")

    # ------------------------------------------------------------------
    # Developer / system message  (override in subclasses to augment)
    # ------------------------------------------------------------------

    def _build_developer_message(self) -> str:
        """
        Return the developer/system message injected into every ai_bot call.

        The default implementation returns the sys_prompt from config.
        Subclasses that need to append extra context (e.g. available_rooms
        for UserInterfaceChatbot) should call super() and extend the string.
        """
        return self._config_manager.get_config("AI", "sys_prompt") or ""

    # ------------------------------------------------------------------
    # Core chain-of-actions loop  (shared, do not override)
    # ------------------------------------------------------------------

    async def _get_ai_response_sequence(
        self,
        current_mem_structure: dict,
        depth: int = 0,
    ) -> str:
        """
        Recursively drive the AI until it produces a plain-text response.

        Handles function calls by saving their results to short-term memory
        and recursing.  The only thing subclasses influence here is
        _build_developer_message(), which is evaluated fresh on every call
        so that dynamic context (e.g. available_rooms) stays current.
        """
        time.sleep(2)

        if depth >= self.max_recursion_depth:
            self.memory.save_to_memory(
                f"\n⚠️ Max recursion depth ({self.max_recursion_depth}) reached.",
                "short_term", "user",
            )
            return "Error: Max recursion depth reached while processing AI response chain."

        print(f"\n🤖 Thinking… (depth {depth})")

        try:
            function_flag, response_content = await self.ai.ai_response(
                current_mem_structure if isinstance(current_mem_structure, dict) else {},
                depth,
                self.max_recursion_depth,
                developer_message=self._build_developer_message(),
            )

            # ── Function call branch ───────────────────────────────────
            if function_flag:
                print(f"⚙️  Function call(s) at depth {depth} — adjusting wellness stats.")
                for stat in ("fullness", "hydration", "energy"):
                    self.state_manager.adjust_stat(stat, -0.1)

                if isinstance(response_content, list):
                    for result in response_content:
                        self.memory.save_to_memory(result, "short_term", "tool")
                        print("✅ Saved function result to short-term memory.")

                updated_mem = self.memory.get_memory_structure()
                if updated_mem is None:
                    print("Warning: Could not reload memory after function call; using empty fallback.")
                    updated_mem = {}

                return await self._get_ai_response_sequence(
                    current_mem_structure=updated_mem,
                    depth=depth + 1,
                )

            # ── Text response branch ───────────────────────────────────
            else:
                print(f"✅ Final text response at depth {depth}.")
                print("Cleaning tool context from short-term memory…")
                self.memory.process_short_term_system()

                self.memory.save_to_memory(response_content, "short_term", "assistant")
                return response_content

        except Exception as e:
            self.text_capture.dump_text(f"Error during chain (depth {depth}): {e}")
            print(f"\n❌ Error at depth {depth}: {e}")
            return f"Error generating response: {e}"

    # ------------------------------------------------------------------
    # Wellness consequences  (shared, same logic for all modes)
    # ------------------------------------------------------------------

    async def _check_wellness_and_consequences(self) -> None:
        """
        Decrease wellness stats by 1, apply threshold messages to memory,
        and trigger a pass-out sleep if any stat hits the critical floor.
        """
        print("Checking wellness and consequences…")

        LOW_PASSOUT   = 20
        RECOVERY      = 40
        TIME_TO_SLEEP = 900  # 15 minutes

        thresholds = {
            "fullness": [
                (120, "You begin to feel a bit hungry."),
                (60,  "You feel really hungry, your stomach rumbles loudly."),
                (30,  "Your hunger is unbearable, you can barely focus."),
                (LOW_PASSOUT, "You're about to collapse from hunger."),
            ],
            "hydration": [
                (120, "You feel a little thirsty."),
                (60,  "Your mouth feels dry, you desperately need water."),
                (30,  "You're severely dehydrated, your head throbs."),
                (LOW_PASSOUT, "You're about to collapse from dehydration."),
            ],
            "energy": [
                (120, "You feel a bit tired."),
                (60,  "Your eyelids feel heavy, you're struggling to stay awake."),
                (30,  "You're utterly exhausted, your body screams for rest."),
                (LOW_PASSOUT, "You're about to collapse from exhaustion."),
            ],
        }

        stats_to_monitor = list(thresholds.keys())

        # Decrease stats
        for stat in stats_to_monitor:
            self.state_manager.adjust_stat(stat, -1)

        stats_response = self.state_manager.get_stats()
        stats_data = stats_response.stats
        if stats_response.error:
            print(f"Error????: {stats_response.error}")
            return
        low_stat_detected = False

        if stats_data is not None:
            for stat in stats_to_monitor:
                value = stats_data.get(stat, float("inf"))
                for threshold, message in thresholds[stat]:
                    if value <= threshold:
                        self.memory.save_to_memory(message, "short_term", "user")
                        if value <= LOW_PASSOUT:
                            low_stat_detected = True
                            print(f"Low stat: {stat} = {value} (≤ {LOW_PASSOUT})")
                        break
        else:
            print("Warning: Could not retrieve stats for wellness check.")

        if low_stat_detected:
            print("Triggering pass-out consequences…")
            self._send_signal({"type": "start_sleep", "time_to_sleep": TIME_TO_SLEEP})
            await asyncio.sleep(TIME_TO_SLEEP)
            self._send_signal({"type": "end_sleep"})

            self.memory.save_to_memory(
                "Internal message: You passed out! Be more careful with your basic necessities.",
                "short_term", "user",
            )
            self.memory.save_to_memory(
                "Internal message: After 15 minutes you wake up on the exact same spot you fainted, still feeling weak.",
                "short_term", "user",
            )

            for stat in stats_to_monitor:
                self.state_manager.adjust_stat(stat, RECOVERY)

            print("Agent passed out due to critically low wellness.")

    # ------------------------------------------------------------------
    # Post-chain memory hook  (MUST be implemented by subclasses)
    # ------------------------------------------------------------------

    @abstractmethod
    def _post_chain_memory_hook(self) -> None:
        """
        Called by process_input after the chain completes and before TTS.

        CLIChatbot      → run memory.check(), persist everything.
        UserInterface   → wipe short-term memory (ephemeral session).
        MockChatbot     → no-op.
        """
        ...

    # ------------------------------------------------------------------
    # Public entry point  (MUST be implemented by subclasses)
    # ------------------------------------------------------------------

    @abstractmethod
    async def process_input(self, message: str, role: str = "user") -> str:
        """
        Called by game.py for every user or system message.

        Typical implementation:
            1. Save message to memory (or not, for ephemeral mode)
            2. Build mem_structure
            3. Await _get_ai_response_sequence(...)
            4. state_manager.add_steps(1)
            5. Await _check_wellness_and_consequences()
            6. _post_chain_memory_hook()
            7. process_response_with_tts(response)
            8. return response
        """
        ...

    # ------------------------------------------------------------------
    # Shutdown  (shared, subclasses may call super().shutdown())
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Stop TTS and persist inventory/state."""
        print(f"[{type(self).__name__}] Shutting down…")
        if self.tts_provider:
            self.tts_provider.stop()
        if self.state_manager:
            self.state_manager.save_state()
        print(f"[{type(self).__name__}] Shutdown complete.")