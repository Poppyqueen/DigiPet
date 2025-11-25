
# services/pet_state_manager.py
class PetStateManager:
    def __init__(self, state_store, signal_callback):
        self._state_store = state_store
        self._signal_callback = signal_callback

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal: {e}")

    # --- Pet Theme Color Getters and Setters ---
    def get_pet_color(self) -> tuple[int, int, int] | None:
        color_list = self._state_store.get_state_section("pet_theme_color")
        if isinstance(color_list, (list, tuple)) and len(color_list) == 3:
            return tuple(max(0, min(255, int(c))) for c in color_list)
        print("Warning: get_pet_color returning default due to unexpected state format.")
        return (100, 255, 100)

    def set_pet_color(self, color: tuple[int, int, int]):
        if not (isinstance(color, (list, tuple)) and len(color) == 3 and
                all(isinstance(c, (int, float)) and 0 <= c <= 255 for c in color)):
            print(f"Error: Attempted to set invalid pet color format: {color}. Ignoring.")
            return

        self._state_store.update_state_section("pet_theme_color", [int(c) for c in color])

    def is_color_configured(self) -> bool:
        return self._state_store.get_state_section("is_color_configured", False)

    def set_color_configured(self, configured: bool):
        if not isinstance(configured, bool):
            print(f"Error: Attempted to set 'is_color_configured' with non-boolean value: {configured}. Ignoring.")
            return
        self._state_store.update_state_section("is_color_configured", configured)

    # --- Pet Sound Getters and Setters ---
    def get_pet_sound(self) -> str | None:
        return self._state_store.get_state_section("pet_sound", "")

    def set_pet_sound(self, sound: str):
        if not isinstance(sound, str):
            print(f"Error: Attempted to set invalid pet sound format: {sound}. Ignoring.")
            return
        self._state_store.update_state_section("pet_sound", sound)

    def is_sound_configured(self) -> bool:
        return self._state_store.get_state_section("is_sound_configured", False)

    def set_sound_configured(self, configured: bool):
        if not isinstance(configured, bool):
            print(f"Error: Attempted to set 'is_sound_configured' with non-boolean value: {configured}. Ignoring.")
            return
        print(f"Setting 'is_sound_configured' to {configured}")
        self._state_store.update_state_section("is_sound_configured", configured)

    # --- Emote Management ---
    def get_current_emote(self, internal: bool = False) -> str | dict:
        current_emote = self._state_store.get_state_section("current_emote", "unknown")
        possible_emotes = self._state_store.get_state_section("possible_emotes", {})
        if not isinstance(possible_emotes, dict):
            possible_emotes = {}

        if internal:
            return {
                "current_emote": current_emote,
                "possible_emotes": possible_emotes
            }
        else:
            description = possible_emotes.get(current_emote, "no description available")
            if description == "no description available" and current_emote != "unknown":
                return f"The current emote is '{current_emote}', but its description is missing."
            elif current_emote == "unknown":
                return "The current emote is unknown or not set."
            else:
                return f"The current emote is '{current_emote}'. Description: {description}"

    def get_possible_emotes(self, internal: bool = False) -> dict | str:
        possible_emotes = self._state_store.get_state_section("possible_emotes", {})
        if not isinstance(possible_emotes, dict):
            possible_emotes = {}

        if internal:
            return possible_emotes
        else:
            if not possible_emotes:
                return "There are no possible emotes defined."
            message_lines = ["Here are the possible emotes:"]
            for emote_name in sorted(possible_emotes.keys()):
                description = possible_emotes.get(emote_name, "no description available")
                message_lines.append(f"- '{emote_name}': {description}")
            return "\n".join(message_lines)

    def set_current_emote(self, emote_name: str, internal: bool = False) -> str | bool:
        if not isinstance(emote_name, str) or not emote_name.strip():
            message = "Error: Emote name must be a non-empty string."
            print(message)
            return False if internal else message

        possible_emotes = self._state_store.get_state_section("possible_emotes", {})
        if not isinstance(possible_emotes, dict):
            message = f"Error setting emote: 'possible_emotes' in state is not a dict ({type(possible_emotes).__name__}). Cannot set emote."
            print(message)
            return False if internal else message

        if emote_name in possible_emotes:
            current_emote = self._state_store.get_state_section("current_emote")
            if current_emote == emote_name:
                message = f"The current emote is already '{emote_name}'."
                return True if internal else message

            self._state_store.update_state_section("current_emote", emote_name)

            emote_description = possible_emotes.get(emote_name, "No description available.")
            self._send_signal({
                "type": "emote_changed",
                "emote_name": emote_name,
                "sound_path": f"style/sounds/{emote_name.lower()}.mp3"
            })
            if internal:
                return True
            else:
                return f"Current emote successfully set to '{emote_name}' - {emote_description}"
        else:
            message = f"Error: Emote '{emote_name}' is not a possible emote. Available emotes: {', '.join(sorted(possible_emotes.keys()) if possible_emotes else ['none'])}"
            print(message)
            return False if internal else message

    # --- Steps Getters and Setters ---
    def get_steps(self) -> int:
        steps_value = self._state_store.get_state_section("steps")
        if not isinstance(steps_value, int) or steps_value < 0:
            print(f"Warning: get_steps found invalid state value ({steps_value}). Returning default 0.")
            return 0
        return steps_value

    def set_steps(self, count: int):
        if not isinstance(count, int):
            print(f"Error: Attempted to set 'steps' with non-integer value: {count}. Ignoring.")
            return
        if count < 0:
            print(f"Error: Attempted to set 'steps' with negative value: {count}. Clamping to 0.")
            count = 0
        self._state_store.update_state_section("steps", count)

    def add_steps(self, amount: int):
        if not isinstance(amount, int):
            print(f"Error: Attempted to add non-integer amount to 'steps': {amount}. Ignoring.")
            return
        if amount < 0:
            print(f"Error: Attempted to add negative amount ({amount}) to 'steps'. Please use set_steps if reducing. Ignoring.")
            return
        current_steps = self.get_steps()
        self._state_store.update_state_section("steps", current_steps + amount)


    # --- Currency Getters and Setters ---
    def get_currency(self) -> int:
        currency_value = self._state_store.get_state_section("currency")
        if not isinstance(currency_value, int) or currency_value < 0:
            print(f"Warning: get_currency found invalid state value ({currency_value}). Returning default 0.")
            return 0
        return currency_value

    def set_currency(self, amount: int):
        if not isinstance(amount, int):
            print(f"Error: Attempted to set 'currency' with non-integer value: {amount}. Ignoring.")
            return
        if amount < 0:
            print(f"Error: Attempted to set 'currency' with negative value: {amount}. Clamping to 0.")
            amount = 0
        self._state_store.update_state_section("currency", amount)

    def adjust_currency(self, amount: int):
        """
        Adjusts the current currency possiteviley or negatively
        """
        if not isinstance(amount, int):
            print(f"Error: Attempted to adjust 'currency' with non-integer amount: {amount}. Ignoring.")
            return
        current_currency = self.get_currency()
        new_currency = current_currency + amount
        if new_currency < 0:
            print(f"Warning: Adjustment would set 'currency' below 0. Clamping to 0.")
            new_currency = 0
        self._state_store.update_state_section("currency", new_currency)
