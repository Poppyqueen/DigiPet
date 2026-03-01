# user_interface_api.py
# User-controlled game mode.
# Inherits all shared infrastructure (chain loop, TTS, wellness) from BaseChatbot.
# Owns: ephemeral memory strategy (short-term wiped after every chain).
#
# CommandTranslator is no longer needed — the shared chain loop in BaseChatbot
# handles function calling and response generation identically to CLIChatbot.
# The only meaningful differences from CLIChatbot are:
#   1. short-term memory is wiped after each chain  (_post_chain_memory_hook)
#   2. available_rooms is injected into the developer message (_build_developer_message)
#   3. deep_memory is always disabled (ephemeral sessions have no long-term identity)

from ai_managers.agents.abstract_agent import BaseChatbot


# System prompt for the user-controlled mode.
# Intentionally lighter than the full AI pet persona — the user IS the agent here,
# and the LLM's job is purely to interpret intent and execute functions faithfully.
_USER_INTERFACE_SYS_PROMPT = """You are a command interpreter for a text adventure / life-sim game.

Your job is to faithfully execute the player's intent using the available tools, then
respond with a short, immersive, second-person narrative (1-3 sentences, Zork-style). 
Narrate from the initial state to the final result.

Rules:
- Prefer function calls over explanations. Act first, narrate after.
- If the player's request maps to multiple actions, chain them in the same turn.
- If a requested action has no matching tool, respond naturally without making up functions.
- Do NOT reference internal function names or arguments in your narrative.
- Even if an action seems impossible, attempt it — the system will surface the error.

Current game context and available rooms are appended below.
"""


class UserController(BaseChatbot):
    """
    User-controlled interface mode.

    The player's natural language is sent through the exact same chain-of-actions
    loop as the AI agent (CLIChatbot), but memory is wiped after every chain so
    there is no persistent identity or long-term memory accumulation.
    """

    def __init__(self, config_manager, signal_callback=None, bots_archive_dir="data_archive"):
        print("Initializing User Controller Interface...")

        super().__init__(
            config_manager       = config_manager,
            signal_callback      = signal_callback,
            bots_archive_dir     = bots_archive_dir,
            deep_memory_override = False,  # ephemeral mode — never accumulate deep memory
        )

        print("UserInterfaceChatbot initialized successfully (mode: user_player).")

    # ------------------------------------------------------------------
    # Developer message  — base prompt + live available_rooms injection
    # ------------------------------------------------------------------

    def _build_developer_message(self) -> str:
        """
        Appends the current list of available rooms to the developer message.
        This is called fresh on every recursive step of the chain so the room
        list is always up to date.
        """
        available_rooms = self.state_manager.get_all_rooms()
        return f"{_USER_INTERFACE_SYS_PROMPT}\nAvailable rooms: {available_rooms}"

    # ------------------------------------------------------------------
    # Post-chain memory hook — wipe short-term (ephemeral session)
    # ------------------------------------------------------------------

    def _post_chain_memory_hook(self) -> None:
        """
        Wipe short-term memory after every completed chain.
        Long-term and base_memory are untouched (not written to in this mode).
        """
        self.memory.wipe_short_term()
        print("UserInterfaceChatbot: short-term memory wiped (ephemeral mode).")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def process_input(self, message: str, role: str = "user") -> str:
        """Process a player command and return the narrated response."""

        print(f"\nUserInterface: Processing → {message[:100]}...")

        # Log input (same pattern as CLIChatbot)
        self.text_capture.dump_text("##########")
        self.text_capture.dump_text("Input Message:")
        self.text_capture.dump_text(f"{role}:")
        self.text_capture.dump_text(message)
        self.text_capture.dump_text("##########")

        # Save to short-term memory — present for the duration of this chain only
        self.memory.save_to_memory(message, "short_term", role)

        # Build memory structure (will be wiped after chain completes)
        mem_structure = self.memory.get_memory_structure()
        if mem_structure is None:
            print("Error: Could not load memory structure. Using empty fallback.")
            mem_structure = {"short_term": {}, "long_term": [], "base_memory": ""}

        # Run the shared chain-of-actions loop
        final_response = await self._get_ai_response_sequence(
            current_mem_structure = mem_structure if isinstance(mem_structure, dict) else {},
            depth                 = 0,
        )

        # Bookkeeping
        self.state_manager.add_steps(1)
        await self._check_wellness_and_consequences()

        # Wipe ephemeral memory
        self._post_chain_memory_hook()

        # TTS
        self.last_response = final_response
        self.process_response_with_tts(final_response)

        return final_response