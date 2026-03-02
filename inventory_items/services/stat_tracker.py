
# services/stat_tracker.py

class StatTracker:
    # Constants for stat ranges (or get from config/state_store if dynamic)
    MAX_STAT_VALUE = 200
    MIN_STAT_VALUE = 0

    def __init__(self, state_store, signal_callback):
        self._state_store = state_store
        self._signal_callback = signal_callback

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal: {e}")

    def get_stats(self, internal: bool = False) -> str | dict:
        stats_data = self._state_store.get_state_section("stats")
        if not isinstance(stats_data, dict):
            print("Warning: Stats data is corrupted in state_store.")
            if internal:
                return {"status": "error", "message": "Stats data is corrupted.", "stats_data_raw": stats_data}
            else:
                return "Error: Stats system is corrupted."

        # Ensure all required stats are present, clamp values
        cleaned_stats = {}
        needs_save = False
        required_stats_keys = ["fullness", "hydration", "energy"]
        for stat_key in required_stats_keys:
            value = stats_data.get(stat_key)
            if not isinstance(value, (int, float)):
                # Fallback to default, though _post_init_state_validation should fix
                default_val = self._state_store._default_state.get("stats", {}).get(stat_key, 200)
                cleaned_stats[stat_key] = default_val
                needs_save = True
                print(f"Warning: Stat '{stat_key}' invalid ({value}), resetting to default ({default_val}).")
            else:
                clamped_value = max(self.MIN_STAT_VALUE, min(self.MAX_STAT_VALUE, value))
                if clamped_value != value:
                    needs_save = True
                    print(f"Warning: Stat '{stat_key}' ({value}) out of range, clamped to {clamped_value}.")
                cleaned_stats[stat_key] = clamped_value

        if needs_save:
            self._state_store.update_state_section("stats", cleaned_stats) # Save corrected stats

        if internal:
            return cleaned_stats
        else:
            return (f"Current Stats: "
                    f"Fullness: {cleaned_stats.get('fullness', 'N/A'):.1f}/{self.MAX_STAT_VALUE}, "
                    f"Hydration: {cleaned_stats.get('hydration', 'N/A'):.1f}/{self.MAX_STAT_VALUE}, "
                    f"Energy: {cleaned_stats.get('energy', 'N/A'):.1f}/{self.MAX_STAT_VALUE}")

    def adjust_stat(self, stat_name: str, amount: int|float) -> str:
        """
        Adjusts a single stat by the given amount.

        Parameters
        ----------
        stat_name : str
            The name of the stat to adjust (e.g., "fullness", "hydration", "energy").
            Case-insensitive and whitespace-stripped.
        amount : int | float
            The amount to adjust the stat by. Positive values increase the stat,
            negative values decrease it.

        Returns
        -------
        str
            A message describing the result of the operation.
            Returns an error message if the stat does not exist, the amount is invalid,
            or the stats data is corrupted.
        """
        stat_name = stat_name.lower().strip()
        stats_data = self._state_store.get_state_section("stats")

        if not isinstance(stats_data, dict):
            return "Error: Stats data is corrupted, cannot adjust stat."

        if stat_name not in stats_data:
            return f"Error: Stat '{stat_name}' does not exist."
        if not isinstance(amount, (int, float)):
            return f"Error: Adjustment amount must be a number, received '{amount}' ({type(amount).__name__})."

        current_value = stats_data[stat_name]
        new_value = current_value + amount
        clamped_value = max(self.MIN_STAT_VALUE, min(self.MAX_STAT_VALUE, new_value))

        if clamped_value == current_value:
            return f"Stat '{stat_name}' remains at {int(clamped_value)}. No change needed or possible."

        stats_data[stat_name] = clamped_value
        self._state_store.update_state_section("stats", stats_data) # Save updated stats

        change_msg = "increased" if amount > 0 else "decreased"
        if amount == 0: change_msg = "changed by 0 (no effect)"

        self._send_signal({"type": "stat_changed", "stat_name": stat_name, "new_value": clamped_value, "change_amount": amount})

        return (f"Stat '{stat_name}' {change_msg} by {abs(amount):.1f} to {int(clamped_value)}.\n"
                f"{self.get_stats(internal=False).replace('Current Stats: ', '')}")
