# stats_component.py
# Contains stat-specific logic for fullness, hydration, and energy.
# Designed to be used by InventoryHouseManager.


class StatsComponent:
    """
    Handles operations specific to the player/AI's stats (fullness, hydration, energy).
    Designed to be composed within an InventoryHouseManager instance.
    Stats are stored and managed as floats between 0.0 and 200.0.
    """

    STAT_MIN_VALUE = 0.0
    STAT_MAX_VALUE = 200.0

    def __init__(self, manager_instance):
        """
        Initializes the StatsComponent with a reference to the main manager.

        Args:
            manager_instance: An instance of InventoryHouseManager. This component
                              requires access to manager's state and helper methods
                              like _write_json and _send_signal.
        """
        self._manager = manager_instance # Store a reference to the main manager instance

        # Optional: Perform checks to ensure manager_instance has expected methods/attributes
        # Check for _state - essential
        if not hasattr(self._manager, '_state') or not isinstance(self._manager._state, dict):
             raise TypeError("Manager instance does not have expected '_state' dictionary attribute.")

        # Check for _write_json - essential for persistence
        if not hasattr(self._manager, '_write_json') or not callable(self._manager._write_json):
             # This is actually critical for the component to ensure saves happen *after*
             # state is modified via the manager reference.
             raise TypeError("Manager instance does not have required '_write_json' method.")

        # Check for _send_signal - essential for UI updates
        if not hasattr(self._manager, '_send_signal') or not callable(self._manager._send_signal):
             raise TypeError("Manager instance does not have required '_send_signal' method.")

        # --- Initial validation and potential conversion to float ---
        # This happens within the manager's __init__ via _post_init_state_validation,
        # which validates the 'stats' structure and ensures values are (int, float)
        # and within range, potentially clamping them. The manager *should* handle
        # converting ints to floats during this validation if that's the desired migration path.
        # We'll rely on the manager's validation. _get_stats_data will then access
        # the validated state.

    def _get_stats_data(self) -> dict | None:
        """
        Internal helper to safely access the 'stats' dictionary from the manager's state.
        Returns the stats dictionary reference if valid, otherwise None.
        Validates keys and checks values are instances of int or float.
        """
        # Use .get() for safety
        stats_data = self._manager._state.get("stats")

        # Validate that it's a dictionary
        if not isinstance(stats_data, dict):
            print(f"Warning: Stats data in manager state is not a dictionary ({type(stats_data).__name__}) in _get_stats_data.")
            return None # Indicate corruption

        # Validate that it contains the expected keys and that values are numbers (int or float)
        required_keys = ["fullness", "hydration", "energy"]
        if not all(key in stats_data and isinstance(stats_data[key], (int, float)) for key in required_keys):
             # Log which specific checks failed for better debugging
             missing_keys = [key for key in required_keys if key not in stats_data]
             invalid_types = {key: type(stats_data[key]).__name__ for key in required_keys if key in stats_data and not isinstance(stats_data[key], (int, float))}
             print(f"Warning: Stats data in manager state validation failed in _get_stats_data. Missing keys: {missing_keys}. Keys with invalid types: {invalid_types}. Data: {stats_data}.")
             return None # Indicate corruption

        return stats_data # Return the mutable dictionary reference


    def get_stats(self, internal: bool = False) -> str | dict:
        """
        Retrieves the current stats (fullness, hydration, or energy).
        Called by the main InventoryHouseManager.

        Args:
            internal (bool): If True, returns the raw stats dictionary (values as floats).
                             If False (default), returns a human-readable string with percentages.

        Returns:
            str or dict: The current stats dictionary (internal=True) or a formatted message (internal=False).
                         Returns an error message string if stats data is corrupted.
        """
        stats_data = self._get_stats_data()

        if stats_data is None:
             # Error message already printed in _get_stats_data warning
             return "Error: Could not access stats data. State might be corrupted."

        # Ensure values are floats for internal representation, convert if needed
        # (This *should* be handled by manager validation on load, but defensive)
        # However, _get_stats_data already validated they are int or float.
        # For internal=True, return the dictionary AS IS from state.
        if internal:
            return stats_data # Return the reference to the state dictionary portion

        else:
            # Construct a human-readable string with percentages
            # Safely get values, defaulting to 0.0 if needed (though validation should prevent this)
            fullness = float(stats_data.get("fullness", self.STAT_MIN_VALUE))
            hydration = float(stats_data.get("hydration", self.STAT_MIN_VALUE))
            energy = float(stats_data.get("energy", self.STAT_MIN_VALUE))

            # Ensure values are within the expected range for display, just in case internal state is bad
            # Use float bounds for consistency
            fullness = max(self.STAT_MIN_VALUE, min(self.STAT_MAX_VALUE, fullness))
            hydration = max(self.STAT_MIN_VALUE, min(self.STAT_MAX_VALUE, hydration))
            energy = max(self.STAT_MIN_VALUE, min(self.STAT_MAX_VALUE, energy))

            # Turn into percentages of 0 - 200, for 100% for display
            # Avoid division by zero if STAT_MAX_VALUE were ever 0 (not the case here, but good practice)
            fullness_percentage = (fullness / self.STAT_MAX_VALUE) * 100 if self.STAT_MAX_VALUE > 0 else 0
            hydration_percentage = (hydration / self.STAT_MAX_VALUE) * 100 if self.STAT_MAX_VALUE > 0 else 0
            energy_percentage = (energy / self.STAT_MAX_VALUE) * 100 if self.STAT_MAX_VALUE > 0 else 0

            # Format percentages to one decimal place
            return (
                f"Current Stats: "
                f"fullness: {fullness_percentage:.1f}%, "
                f"hydration: {hydration_percentage:.1f}%, "
                f"energy: {energy_percentage:.1f}%"
            )


    def adjust_stat(self, stat_name: str, amount: int | float) -> str | dict | None:
        """
        Adjusts a specific stat (fullness, hydration, or energy) by a given amount.
        Positive amount increases, negative decreases. Caps at STAT_MIN_VALUE and STAT_MAX_VALUE.
        Called by the main InventoryHouseManager or internally.
        Modifies state directly via the manager's state reference and calls the manager's signal method.
        Calls the manager's _write_json to persist the state change immediately.

        Args:
            stat_name (str): The name of the stat ('fullness', 'hydration', 'energy'). Case-insensitive.
            amount (int | float): The amount to add (positive) or subtract (negative) from the stat value.
                                  Can be an integer or a float.

        Returns:
            str | dict | None: Returns None if no actual change occurred (amount was 0 or already capped).
                               Returns a dictionary {stat_name: actual_change} on successful adjustment.
                               Returns a string error message on failure (invalid stat name, invalid amount type, corrupted state).
        """
        # Basic validation before accessing state
        valid_stats = ["fullness", "hydration", "energy"]
        stat_name_lower = stat_name.strip().lower()

        if stat_name_lower not in valid_stats:
             return f"Error: Invalid stat name '{stat_name}'. Must be one of: {', '.join(valid_stats)}."

        # Allow int or float amounts for adjustment
        if not isinstance(amount, (int, float)):
             return f"Error: Adjustment amount must be a number (integer or float), received '{amount}' ({type(amount).__name__})."

        # Get the current stats data dictionary
        stats_data = self._get_stats_data()

        if stats_data is None:
             return f"Error: Cannot adjust stat '{stat_name_lower}'. Stats data is corrupted."

        # Get the current value of the specific stat
        # _get_stats_data ensures the key exists and is int/float
        current_value = float(stats_data.get(stat_name_lower)) # Ensure we're working with a float


        # Calculate the potential new value
        new_value = current_value + amount

        # Clamp the new value using float bounds
        clamped_value = max(self.STAT_MIN_VALUE, min(self.STAT_MAX_VALUE, new_value))

        # Calculate the actual change that will occur after clamping
        actual_change = clamped_value - current_value

        # Check if the value actually changes significantly (account for floating point errors)
        # Use a small tolerance or check if the difference is exactly 0.0
        # Checking if difference is exactly 0.0 is often sufficient for values manipulated by whole numbers/simple fractions,
        # but tolerance is safer. abs(actual_change) < 1e-9 is a common tolerance check.
        # Let's check if the clamped value is *effectively* the same as the current value.
        # We can cast to a precision and compare, or use abs(difference).
        # Comparing the clamped value with the original value from the state is the most direct check for 'no change saved'.
        # Note: _get_stats_data might return an int if loaded from an old state, so ensure state comparison is float.
        current_value_in_state = float(stats_data.get(stat_name_lower)) # Ensure float comparison

        # Check if the clamped value is the same as the current state value within a tolerance
        if abs(clamped_value - current_value_in_state) < 1e-9:
             # Value didn't change or change was negligible.
             # Return None to indicate no change occurred.
             return None

        # Update the state via the reference with the new clamped float value
        stats_data[stat_name_lower] = float(clamped_value) # Ensure value is stored as float

        # Save the state immediately after modification
        self._manager._write_json(self._manager._state)

        # Send a signal using the manager's method
        # Send the clamped_value and the actual_change (both should be floats)
        self._manager._send_signal({
            "type": "stat_changed",
            "stat_name": stat_name_lower,
            "new_value": float(clamped_value), # Ensure float
            "change_amount": float(actual_change) # Ensure float
        })

        # Return information about the change for the caller (manager) to use
        # Return a dictionary {stat_name: actual_change}
        return {stat_name_lower: float(actual_change)} # Ensure float change is returned


    def apply_consumable_effects(self, stat_effects_dict: dict) -> dict | None:
        """
        Applies a dictionary of stat changes (like from a consumable's 'stats_edit')
        to the player's stats. Uses adjust_stat which handles clamping and signaling.
        Does NOT save state itself; adjust_stat handles saving.

        Args:
            stat_effects_dict (dict): Dictionary where keys are stat names ('fullness',
                                    'hydration', 'energy') and values are integer or float
                                    amounts to add/subtract.

        Returns:
            dict | None: A dictionary summarizing the *actual* changes made (key: stat_name,
                         value: actual_change_amount, which may be less than requested
                         due to clamping). Returns None if stats data is corrupted.
                         Returns an empty dict {} if no stats were changed (e.g. all amounts 0 or invalid).
        """
        if not isinstance(stat_effects_dict, dict):
             print(f"Warning: apply_consumable_effects received non-dict effects: {stat_effects_dict}")
             return {} # Treat as no effects if input is invalid type

        stats_data = self._get_stats_data()

        if stats_data is None:
             # Error message already printed in _get_stats_data warning
             return None # Indicate stats data is corrupted

        changes_summary = {}
        valid_stats = {"fullness", "hydration", "energy"}
        needs_save = False # Track if any adjustment caused a save

        # Iterate through the effects requested by the consumable
        for stat_name, amount in stat_effects_dict.items():
             # Validate the key and value type from the input dict defensively
             if stat_name.strip().lower() in valid_stats and isinstance(amount, (int, float)):
                  stat_name_lower = stat_name.strip().lower()

                  # Call the internal adjust_stat method, which handles clamping and signalling.
                  # Importantly, adjust_stat now also handles calling _write_json for *each* successful adjustment.
                  change_result = self.adjust_stat(stat_name_lower, amount)

                  if change_result is not None and isinstance(change_result, dict):
                       # adjust_stat returned a dictionary indicating a change occurred
                       # Merge the results into our summary dictionary
                       changes_summary.update(change_result)
                       # adjust_stat already saved state and signaled, so we don't need a flag here
                  # else: adjust_stat returned None (no change) or an error string (shouldn't happen with checks), ignore

             else:
                  # Log a warning about an invalid entry in the consumable's stats_edit
                  # Use get() defensively for the log message
                  print(f"Warning: Consumable effects dict had invalid entry: '{stat_name}': {amount} (type: {type(amount).__name__}). Expected valid stat name and number.")

        # We don't need to call _write_json here at the end of apply_consumable_effects
        # because adjust_stat now calls _write_json for every stat that actually changes.
        # If multiple stats change, the state is saved multiple times, but for simplicity
        # this is acceptable. An alternative design would be for adjust_stat to *not* save,
        # and for apply_consumable_effects to save *once* at the end if any changes occurred.
        # Sticking to adjust_stat saving keeps adjust_stat self-contained for persistence.


        # Return the summary of changes that actually occurred
        # Return an empty dict if no stats were changed, as adjust_stat returns None in that case
        return changes_summary if changes_summary else {}


# You could add more specific methods here if needed, e.g.,
# def increment_fullness(self, amount): return self.adjust_stat("fullness", amount)
# def decrement_hydration(self, amount): return self.adjust_stat("hydration", -amount)
# But adjust_stat is general enough for now.