# agent_api.py
# Main endpoint for an AI agent.
# Inherits all shared infrastructure from BaseChatbot.
# Owns: persistent memory strategy (check + summarise after each chain).

import sys
import traceback

from ai_managers.agents.abstract_agent import BaseChatbot


class AgentChatbot(BaseChatbot):
    """
    Full AI agent mode.

    Memory behaviour: short-term is persisted across turns; memory.check()
    is called after every chain to summarise/purge when thresholds are hit.
    """

    def __init__(self, config_manager, signal_callback=None, bots_archive_dir="data_archive"):
        print("Initializing Agent Chatbot...")
        try:
            super().__init__(
                config_manager    = config_manager,
                signal_callback   = signal_callback,
                bots_archive_dir  = bots_archive_dir,
            )
        except ImportError as e:
            print(f"FATAL: Could not import dependencies ({e}). Ensure all modules exist.")
            sys.exit(1)
        except Exception as e:
            traceback.print_exc()
            print(f"FATAL: Could not initialize AI or Memory systems ({e}). Exiting.")
            sys.exit(1)

        # sys_prompt is read inside _build_developer_message() via config_manager,
        # but we cache it here too for clarity / potential override in tests.
        self._sys_prompt = config_manager.get_config("AI", "sys_prompt")

        print(f"CLIChatbot initialized successfully (mode: ai_player).")



    @classmethod
    async def create(cls, config_manager, signal_callback=None, bots_archive_dir="data_archive") -> "AgentChatbot":
        """
        Async factory for AgentChatbot. Always use this instead of
        AgentChatbot(...) directly.
        """
        instance = await super().create(
            config_manager   = config_manager,
            signal_callback  = signal_callback,
            bots_archive_dir = bots_archive_dir,
        )
        # Cache sys_prompt (was set in __init__ but __init__ still runs, so this
        # is already set — just keeping it explicit for clarity).
        instance._sys_prompt = config_manager.get_config("AI", "sys_prompt")
        return instance
 
    # ------------------------------------------------------------------
    # Developer message  (base already returns sys_prompt — no override needed,
    # but kept explicit so the intent is obvious)
    # ------------------------------------------------------------------

    def _build_developer_message(self) -> str:
        return self._sys_prompt or super()._build_developer_message()

    # ------------------------------------------------------------------
    # Post-chain memory hook
    # ------------------------------------------------------------------

    def _post_chain_memory_hook(self) -> None:
        """Persist and summarise/purge memory after every completed chain."""
        print("Performing memory check...")
        self.memory.check()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def process_input(self, message: str, role: str = "user") -> str:
        """Process a user (or system) message and return the AI's final response."""

        # 1. Log input
        self.text_capture.dump_text("##########")
        self.text_capture.dump_text("Input Message:")
        self.text_capture.dump_text(f"{role}:")
        self.text_capture.dump_text(message)
        self.text_capture.dump_text("##########")

        # 2. Save to short-term memory
        self.memory.save_to_memory(message, "short_term", role)

        # 3. Build memory structure
        mem_structure = self.memory.get_memory_structure()
        if mem_structure is None:
            print("Error: Could not load memory structure. Using empty fallback.")
            mem_structure = {"short_term": {}, "long_term": [], "base_memory": ""}

        # 4. Run the chain-of-actions loop (defined in BaseChatbot)
        final_response = await self._get_ai_response_sequence(
            current_mem_structure = mem_structure if isinstance(mem_structure, dict) else {},
            depth                 = 0,
        )

        # 5. Bookkeeping
        self.state_manager.add_steps(1)
        await self._check_wellness_and_consequences()

        # 6. Memory persistence (subclass-specific)
        self._post_chain_memory_hook()

        # 7. TTS
        self.last_response = final_response
        self.process_response_with_tts(final_response)

        return final_response

    # ------------------------------------------------------------------
    # CLI convenience runner  (not used by game.py / pygame)
    # ------------------------------------------------------------------

    def run(self):
        """Blocking CLI loop — only useful when running chatbot_api.py directly."""
        import asyncio
        try:
            while self.running:
                user_input = input("\n💬 You: ").strip()
                if not user_input:
                    continue
                response = asyncio.run(self.process_input(user_input))
                print(f"\n🤖 AI: {response}")
                print("-" * 60)
        except KeyboardInterrupt:
            print("\n\nInterrupted. Exiting gracefully...")
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            traceback.print_exc()
        finally:
            self.shutdown()