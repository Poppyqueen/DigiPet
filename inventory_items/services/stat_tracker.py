
# services/stat_tracker.py
from inventory_items.services.return_objects import StatsResult

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

    def get_stats(self) -> StatsResult:
        stats_data = self._state_store.get_state_section("stats")
        
        # Handle corrupted state store
        if not isinstance(stats_data, dict):
            error_msg = "Stats data is corrupted in state_store."
            print(f"Warning: {error_msg}")
            return StatsResult.fail(error=error_msg, stats={})

        # Ensure all required stats are present and clamped
        cleaned_stats = {}
        needs_save = False
        required_stats_keys = ["fullness", "hydration", "energy"]

        for stat_key in required_stats_keys:
            value = stats_data.get(stat_key)
            
            if not isinstance(value, (int, float)):
                # Fallback to default
                default_val = self._state_store._default_state.get("stats", {}).get(stat_key, 200)
                cleaned_stats[stat_key] = default_val
                needs_save = True
                print(f"Warning: Stat '{stat_key}' invalid ({value}), resetting to default ({default_val}).")
            else:
                # Clamp values between MIN and MAX
                clamped_value = max(self.MIN_STAT_VALUE, min(self.MAX_STAT_VALUE, value))
                if clamped_value != value:
                    needs_save = True
                    print(f"Warning: Stat '{stat_key}' ({value}) out of range, clamped to {clamped_value}.")
                cleaned_stats[stat_key] = clamped_value

        # Persist corrected stats if changes were made
        if needs_save:
            self._state_store.update_state_section("stats", cleaned_stats)

        # Construct the descriptive message
        display_message = (
            f"Fullness: {cleaned_stats['fullness']:.1f}/{self.MAX_STAT_VALUE}, "
            f"Hydration: {cleaned_stats['hydration']:.1f}/{self.MAX_STAT_VALUE}, "
            f"Energy: {cleaned_stats['energy']:.1f}/{self.MAX_STAT_VALUE}"
        )

        return StatsResult.ok(message=display_message, stats=cleaned_stats)
        
    def adjust_stat(self, stat_name: str, amount: int | float) -> StatsResult:
        """
        Adjusts a single stat by the given amount and returns a StatsResult.
        """
        stat_name = stat_name.lower().strip()
        stats_data = self._state_store.get_state_section("stats")

        # 1. Validation Checks
        if not isinstance(stats_data, dict):
            return StatsResult.fail(error="Stats data is corrupted, cannot adjust stat.", stats={})

        if stat_name not in stats_data:
            return StatsResult.fail(error=f"Stat '{stat_name}' does not exist.", stats=stats_data)
        
        if not isinstance(amount, (int, float)):
            return StatsResult.fail(
                error=f"Adjustment amount must be a number, received '{type(amount).__name__}'.", 
                stats=stats_data
            )

        # 2. Calculation & Clamping
        current_value = stats_data[stat_name]
        new_value = current_value + amount
        clamped_value = max(self.MIN_STAT_VALUE, min(self.MAX_STAT_VALUE, new_value))

        # 3. Apply changes if necessary
        if clamped_value != current_value:
            stats_data[stat_name] = clamped_value
            self._state_store.update_state_section("stats", stats_data)
            
            # Signal the change
            self._send_signal({
                "type": "stat_changed", 
                "stat_name": stat_name, 
                "new_value": clamped_value, 
                "change_amount": amount
            })

        # 4. Generate result using the refactored get_stats()
        # This ensures the message includes ALL current stats and handles formatting.
        full_stats_result = self.get_stats()
        
        change_verb = "increased" if amount > 0 else "decreased"
        if amount == 0:
            change_verb = "unchanged"

        # Prefix the overall stats message with the specific change that occurred
        summary_message = (
            f"Stat '{stat_name}' {change_verb} by {abs(amount):.1f} to {int(clamped_value)}.\n"
            f"Total: {full_stats_result.message}"
        )

        return StatsResult.ok(message=summary_message, stats=full_stats_result.stats)