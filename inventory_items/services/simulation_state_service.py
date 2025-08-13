class SimulationStateService:
    def __init__(self, state_store):
        self._state_store = state_store

    def get_sim_state(self):
        # Access state directly via state_store
        print(f"Retrieving simulation state: {self._state_store.get_state_section('id_value', '')}, {self._state_store.get_state_section('sim_current_step', 0)}")
        return {
            "id_value": self._state_store.get_state_section("id_value", ""),
            "sim_current_step": self._state_store.get_state_section("sim_current_step", 0)
        }

    def set_sim_state(self, id_value=None, sim_current_step=None):
        current_state = self._state_store.get_full_state() # Get full state to modify

        if isinstance(id_value, str):
            current_state["id_value"] = id_value
        if isinstance(sim_current_step, int):
            current_state["sim_current_step"] = sim_current_step

        self._state_store.save_state() # Save the modified full state
        print(f"Simulation state updated: id_value={id_value}, sim_current_step={sim_current_step}")
