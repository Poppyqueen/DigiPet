# services/pet_state_manager.py
from inventory_items.services.return_objects import GetCurrencyResult, AdjustCurrencyResult, EmotesResult

# TODO: kick out the currency stuff, move to the tools folder... maybe not?
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
    # --- Emote Management ---
    def get_current_emote(self) -> str:
        current_emote = self._state_store.get_state_section("current_emote", "unknown")
        possible_emotes = self._state_store.get_state_section("possible_emotes", {})
        if not isinstance(possible_emotes, dict):
            possible_emotes = {}

        description = possible_emotes.get(current_emote, "no description available")
        if description == "no description available" and current_emote != "unknown":
            return f"The current emote is '{current_emote}', but its description is missing."
        elif current_emote == "unknown":
            return "The current emote is unknown or not set."
        else:
            return f"The current emote is '{current_emote}'. Description: {description}"

    def get_possible_emotes(self) -> str:
        possible_emotes = self._state_store.get_state_section("possible_emotes", {})
        if not isinstance(possible_emotes, dict):
            possible_emotes = {}

        if not possible_emotes:
            return "There are no possible emotes defined."
        message_lines = ["Here are the possible emotes:"]
        for emote_name in sorted(possible_emotes.keys()):
            description = possible_emotes.get(emote_name, "no description available")
            message_lines.append(f"- '{emote_name}': {description}")
        return "\n".join(message_lines)

    def set_current_emote(self, emote_name: str) -> str:
        if not isinstance(emote_name, str) or not emote_name.strip():
            message = "Error: Emote name must be a non-empty string."
            print(message)
            return message

        possible_emotes = self._state_store.get_state_section("possible_emotes", {})
        if not isinstance(possible_emotes, dict):
            message = f"Error setting emote: 'possible_emotes' in state is not a dict ({type(possible_emotes).__name__}). Cannot set emote."
            print(message)
            return message
        print(f"DEBUG: emote_name={emote_name!r}, type={type(emote_name)}")
        print(f"DEBUG: possible_emotes keys={list(possible_emotes.keys())!r}")
        print(f"DEBUG: in check={emote_name in possible_emotes}")
        if emote_name not in possible_emotes:
            message = f"Error: Emote '{emote_name}' is not a possible emote. ..."
            print(message)
            return message

        self._state_store.update_state_section("current_emote", emote_name)
        emote_description = possible_emotes.get(emote_name, "No description available.")
        self._send_signal({
            "type": "emote_changed",
            "emote_name": emote_name,
            "sound_path": f"style/sounds/{emote_name.lower()}.mp3"
        })
        return f"You are feeling '{emote_name}'! {emote_description}"

        #     self._send_signal({
        #         "type": "emote_changed",
        #         "emote_name": emote_name,
        #         "sound_path": f"style/sounds/{emote_name.lower()}.mp3"
        #     })
        #     return f"You are feeling '{emote_name}'! {emote_description}"
        # else:
        #     message = f"Error: Emote '{emote_name}' is not a possible emote. Available emotes: {', '.join(sorted(possible_emotes.keys()) if possible_emotes else ['none'])}"
        #     print(message)
        #     return message

    # --- Steps Getters and Setters ---
    def get_steps(self) -> int:
        steps_value = self._state_store.get_state_section("steps")
        if not isinstance(steps_value, int) or steps_value < 0:
            print(f"Warning: get_steps found invalid state value ({steps_value}). Returning default 0.")
            return 0
        return steps_value

    def add_steps(self, amount: int):
        if not isinstance(amount, int):
            print(f"Error: Attempted to add non-integer amount to 'steps': {amount}. Ignoring.")
            return
        if amount < 0:
            print(f"Error: Attempted to add negative amount ({amount}) to 'steps'. Ignoring.")
            return
        current_steps = self.get_steps()
        self._state_store.update_state_section("steps", current_steps + amount)


    # --- Currency Getters and Setters ---
    def get_currency(self) -> GetCurrencyResult:
        currency_value = self._state_store.get_state_section("currency")
        if not isinstance(currency_value, int) or currency_value < 0:
            print(f"Warning: get_currency found invalid state value ({currency_value}). Returning default 0.")
            return GetCurrencyResult.fail(error="Invalid currency value found in state.", currency=0)
        return GetCurrencyResult.ok(currency=currency_value, message="Currency retrieved successfully.")

    def set_currency(self, amount: int):
        if not isinstance(amount, int):
            print(f"Error: Attempted to set 'currency' with non-integer value: {amount}. Ignoring.")
            return
        if amount < 0:
            print(f"Error: Attempted to set 'currency' with negative value: {amount}. Clamping to 0.")
            amount = 0
        self._state_store.update_state_section("currency", amount)

    def adjust_currency(self, amount: int) -> AdjustCurrencyResult:
        """
        Adjusts the current currency positively or negatively
        """
        if not isinstance(amount, int):
            error = f"Error: Attempted to adjust 'currency' with non-integer amount: {amount}. Ignoring."
            print(error)
            return AdjustCurrencyResult.fail(error=error, currency=self.get_currency().currency)
        current_currency = self.get_currency().currency
        new_currency = current_currency + amount
        if new_currency < 0:
            print(f"Warning: Adjustment would set 'currency' below 0. Clamping to 0.")
            new_currency = 0
            self._state_store.update_state_section("currency", new_currency)
            return AdjustCurrencyResult.ok(currency=new_currency, message="Currency adjusted and reached 0.")
        self._state_store.update_state_section("currency", new_currency)
        return AdjustCurrencyResult.ok(currency=new_currency, message=f"Currency adjusted, new balance: {new_currency}")

    def get_emotes_data(self) -> EmotesResult:
        current_emote = self._state_store.get_state_section("current_emote", "unknown")
        possible_emotes = self._state_store.get_state_section("possible_emotes", {})
        if not isinstance(possible_emotes, dict):
            possible_emotes = {}
            return EmotesResult.fail(error="Invalid possible_emotes value found in state.", current_emote=current_emote, possible_emotes=list(possible_emotes.keys()))
        if not isinstance(current_emote, str):
            current_emote = "unknown"
            return EmotesResult.fail(error="Invalid current_emote value found in state.", current_emote=current_emote, possible_emotes=list(possible_emotes.keys()))
        return EmotesResult.ok(message=f"Your current emote is {current_emote}", current_emote=current_emote, possible_emotes=list(possible_emotes.keys()))