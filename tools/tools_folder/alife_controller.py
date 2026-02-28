import os
import json
from pathlib import Path
from utils.loc_datetime import datetime
import time

from tools.tools_folder.simulation import ALifeSimulation
from tools.tools_folder.tools_helpers.alife_manager import ALifeManager

class ALifeController:
    """
    The boundary layer for ALife simulation.
    Handles stat costs, signals, and file I/O using ALifeManager.
    """
    def __init__(self, state_manager, signal, base_path: str):
        self.state_manager = state_manager
        self._signal_callback = signal
        base_alife_path = Path(base_path) / "ALife_Data"
        self.archive_dir = base_alife_path / "simulations"
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        self.manager = ALifeManager(base_alife_path)
        self.simulation = ALifeSimulation()

        # Load last known state on startup
        pointer = self.manager.get_current_pointer()
        sim_id = pointer["current_simulation_id"]
        tick = pointer["current_tick"]

        if sim_id and sim_id in self.manager._state["simulations"]:
            self.load_previous_simulation(sim_id, tick)
        else:
            self.create_new_simulation()

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from ALifeController: {e}")

    def observe_ALIFE(self) -> str:
        self.state_manager.adjust_stat("energy", -3)
        result = self.simulation.observe_ALIFE()
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/alife_examine.png"})
        return result

    def forward_ALIFE(self) -> str:
        result = self.simulation.forward_ALIFE()
        if "Error" not in result:
            self.manager.set_current_pointer(tick=self.simulation.current_tick)
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/alife_scroll.png"})
        return result

    def backward_ALIFE(self) -> str:
        result = self.simulation.backward_ALIFE()
        if "Error" not in result:
            self.manager.set_current_pointer(tick=self.simulation.current_tick)
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/alife_scroll.png"})
        return result

    def set_current_tick_ALIFE(self, tick: int) -> str:
        result = self.simulation.set_current_tick_ALIFE(tick)
        if "Error" not in result:
            self.manager.set_current_pointer(tick=self.simulation.current_tick)
        return result

    def create_new_simulation(self, **kwargs) -> str:
        # Extract metadata-related kwargs
        new_name = kwargs.pop("new_name", None)
        internal = kwargs.pop("internal", False)

        # Run simulation
        result = self.simulation.create_new_simulation(**kwargs)

        # Create metadata entry
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        timestamp_time = int(time.time())
        run_filename_base = f"SIM_{timestamp_str}_{timestamp_time}"
        json_file_name = f"{run_filename_base}.json"
        txt_file_name = f"{run_filename_base}.txt"

        json_file_path = str(self.archive_dir / json_file_name)
        txt_file_path = str(self.archive_dir / txt_file_name)

        manager_entry = self.manager.create_entry(json_file_path)
        new_id = manager_entry["simulation_ID"]

        # Get archive data from simulation
        archive_data = self.simulation.archive_simulation_run(new_id)

        # Write files
        with open(json_file_path, 'w') as f:
            json.dump(archive_data["json_data"], f, indent=2)

        with open(txt_file_path, 'w') as f:
            f.write(archive_data["txt_data"])

        # Update pointer
        self.simulation.current_simulation_ID = new_id
        self.manager.set_current_pointer(simulation_id=new_id, tick=0)

        # Optional: update name if passed in kwargs
        if new_name:
            self.manager.update_simulation_name(new_id, new_name)

        if internal:
            return new_id

        return f"New simulation created and archived with ID: {new_id}. {result}"

    def load_previous_simulation(self, simulation_id: str, tick: int = 0) -> str:
        if simulation_id not in self.manager._state["simulations"]:
            return f"Error: Simulation {simulation_id} not found."

        entry = self.manager._state["simulations"][simulation_id]
        filepath = entry["simulation_file_path"]

        if not os.path.exists(filepath):
            return f"Error: Archive file not found at {filepath}"

        with open(filepath, 'r') as f:
            archived_data = json.load(f)

        result = self.simulation.load_simulation_data(archived_data, simulation_id, tick)
        if "Error" not in result:
            self.manager.set_current_pointer(simulation_id=simulation_id, tick=tick)

        return result

    def list_simulations(self) -> str:
        return self.manager.list_simulations()

    def details_of_simulation(self, sim_id: str) -> str:
        return self.manager.details_of_simulation(sim_id)

    def update_simulation_name(self, sim_id: str, name: str) -> str:
        return self.manager.update_simulation_name(sim_id, name)

    def add_simulation_detail(self, sim_id: str, detail: str) -> str:
        return self.manager.add_simulation_detail(sim_id, detail)

    def delete_simulation(self, sim_id: str) -> str:
        return self.manager.delete_simulation(sim_id)

    def display_information(self) -> str:
        # Re-implementation of display_information to use the manager and simulation data
        sim_id = self.simulation.current_simulation_ID
        metadata_str = self.details_of_simulation(sim_id)

        config_parts = []
        config_parts.append("\n--- Current Simulation Configuration ---")
        config_parts.append(f"  Grid Size: {self.simulation.config.get('grid_size', ['N/A', 'N/A'])[0]}x{self.simulation.config.get('grid_size', ['N/A', 'N/A'])[1]}")
        config_parts.append(f"  Configured Max Ticks: {self.simulation.config.get('max_ticks', 'N/A')}")

        visuals = self.simulation.get_visualization()

        return f"{metadata_str}\n" + "\n".join(config_parts) + f"\n\n--- ASCII Visualization (Current Tick: {self.simulation.current_tick}) ---\n{visuals}"
