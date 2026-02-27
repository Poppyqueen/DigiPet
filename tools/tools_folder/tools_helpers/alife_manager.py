import json
import os
from pathlib import Path
import string
import random

class ALifeManager:
    """
    Manages ALife simulation metadata and the current state pointer.
    Replaces both the old ALifeManager(GenericJsonTool) and SimulationStateService.
    """
    def __init__(self, base_path: str):
        self.filepath = Path(base_path) / "alife_data.json"
        self._state = self._load()

    def _load(self) -> dict:
        if not self.filepath.exists():
            default = {"current_simulation_id": "", "current_tick": 0, "simulations": {}}
            self._save(default)
            return default
        try:
            with open(self.filepath) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            default = {"current_simulation_id": "", "current_tick": 0, "simulations": {}}
            self._save(default)
            return default

    def _save(self, state: dict = None):
        data = state if state is not None else self._state
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2)

    def get_current_pointer(self) -> dict:
        """Returns the last known simulation ID and tick."""
        return {
            "current_simulation_id": self._state.get("current_simulation_id", ""),
            "current_tick": self._state.get("current_tick", 0),
        }

    def set_current_pointer(self, simulation_id: str = None, tick: int = None):
        """Updates the global simulation pointer."""
        if simulation_id is not None:
            self._state["current_simulation_id"] = simulation_id
        if tick is not None:
            self._state["current_tick"] = tick
        self._save()

    def create_entry(self, json_path: str) -> dict:
        """Creates a new simulation entry in the registry."""
        def generate_short_uid(length=6):
            characters = string.ascii_lowercase + string.digits
            return ''.join(random.choice(characters) for _ in range(length))

        sim_id = generate_short_uid()
        while sim_id in self._state["simulations"]:
            sim_id = generate_short_uid()

        new_entry = {
            "simulation_ID": sim_id,
            "simulation_file_path": json_path,
            "simulation_name": "",
            "simulation_details": []
        }
        self._state["simulations"][sim_id] = new_entry
        self._save()
        return new_entry

    def list_simulations(self) -> str:
        """Lists all registered simulations."""
        sims = self._state.get("simulations", {})
        if not sims:
            return "No simulations found in the archive."

        sim_list = "\n".join([
            f"- ID: '{sim_id}', Name: '{data.get('simulation_name', 'N/A')}'"
            for sim_id, data in sims.items()
        ])
        return f"Found {len(sims)} simulation(s):\n{sim_list}"

    def update_simulation_name(self, sim_id: str, name: str) -> str:
        """Updates the name of a specific simulation."""
        if sim_id not in self._state["simulations"]:
            return f"Error: Simulation with ID '{sim_id}' not found."
        self._state["simulations"][sim_id]["simulation_name"] = name
        self._save()
        return f"Simulation '{sim_id}' name updated to '{name}'."

    def add_simulation_detail(self, sim_id: str, detail: str) -> str:
        """Adds a descriptive detail to a specific simulation."""
        if sim_id not in self._state["simulations"]:
            return f"Error: Simulation with ID '{sim_id}' not found."
        self._state["simulations"][sim_id]["simulation_details"].append(detail)
        self._save()
        return f"Detail added to simulation '{sim_id}'."

    def details_of_simulation(self, sim_id: str) -> str:
        """Returns JSON metadata for a specific simulation."""
        if sim_id not in self._state["simulations"]:
            return f"Error: Simulation with ID '{sim_id}' not found."
        sim_data_str = json.dumps(self._state["simulations"][sim_id], indent=2)
        return f"Data for simulation '{sim_id}':\n```json\n{sim_data_str}\n```"

    def delete_simulation(self, sim_id: str) -> str:
        """Removes a simulation from the registry."""
        if sim_id not in self._state["simulations"]:
            return f"Error: Simulation with ID '{sim_id}' not found."

        del self._state["simulations"][sim_id]

        # If we deleted the current active simulation, clear the pointer
        if self._state["current_simulation_id"] == sim_id:
            self._state["current_simulation_id"] = ""
            self._state["current_tick"] = 0

        self._save()
        return f"Simulation '{sim_id}' deleted successfully."
