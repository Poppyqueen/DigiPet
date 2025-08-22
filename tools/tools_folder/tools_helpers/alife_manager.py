from utils.generic_json_tool import GenericJsonTool

import string

import json


import random

class ALifeManager(GenericJsonTool):
    """
    A tool to manage multiple ALife simulation states using a single JSON archive file.
    Each simulation is stored as an entry in the main state dictionary, keyed by its ID.
    """

    # Define the expected structure for a single simulation entry for validation/template
    _simulation_entry_template = {
        "simulation_ID": "", # This will also be the key in the main state dict
        "simulation_file_path": "",
        "simulation_name": "",
        "simulation_details": [] # Changed to list of strings as default example
    }


    def __init__(self, base_path):
        # --- REQUIRED: Define json_filename and _default_state BEFORE super().__init__ ---

        # 1. Define the name of the JSON file for this specific tool
        self.json_filename = "simulations_archive.json"

        # 2. Define the initial/default state structure (a dictionary)
        # This will be the container for all simulations, keyed by ID.
        self._default_state = {} # Starts as an empty dictionary

        # --- Call the parent constructor AFTER setting filename and default state ---
        super().__init__(base_path)

        # Now self._state is initialized (either loaded from file or is a copy of _default_state)
        print(f"ALifeManager initialized. State contains {len(self._state)} simulations.")


    # --- Methods for managing individual simulations ---

    def add_simulation_detail(self, simulation_id: str, detail_string: str) -> str:
        """
        Adds a string detail to the list of simulation details for a given simulation ID.

        Args:
            simulation_id (str): The ID of the simulation to update.
            detail_string (str): The string to add to the 'simulation_details' list.

        Returns:
            str: A string indicating success or failure.
        """
        if simulation_id not in self._state:
            return f"Error: Simulation with ID '{simulation_id}' not found."

        if not isinstance(detail_string, str):
             return f"Error: The detail to add must be a string, received {type(detail_string).__name__}."

        sim_entry = self._state[simulation_id]

        # Ensure simulation_details exists and is a list, handle potential issues
        if "simulation_details" not in sim_entry or not isinstance(sim_entry["simulation_details"], list):
            print(f"Warning: 'simulation_details' field for ID '{simulation_id}' was missing or not a list. Re-initializing.")
            sim_entry["simulation_details"] = [] # Re-initialize if not found or wrong type

        try:
            # Add the detail to the list
            sim_entry["simulation_details"].append(detail_string)

            # --- Save the state after modification ---
            self._write_json(self._state)

            return f"Detail added to simulation '{simulation_id}'."
        except Exception as e:
            print(f"An unexpected error occurred adding detail to simulation {simulation_id}: {e}")
            return f"Error adding detail to simulation '{simulation_id}': An internal error occurred."


    def update_simulation_name(self, simulation_id: str, new_name: str) -> str:
        """
        Updates the 'simulation_name' for a specific simulation entry.

        Args:
            simulation_id (str): The ID of the simulation to update.
            new_name (str): The new name for the simulation.

        Returns:
            str: A string indicating success or failure.
        """
        if simulation_id not in self._state:
            return f"Error: Simulation with ID '{simulation_id}' not found."

        if not isinstance(new_name, str):
             return f"Error: New simulation name must be a string, received {type(new_name).__name__}."

        sim_entry = self._state[simulation_id]

        try:
            # Update the simulation_name field
            sim_entry["simulation_name"] = new_name

            # --- Save the state after modification ---
            self._write_json(self._state)

            return f"Simulation '{simulation_id}' name updated to '{new_name}'."
        except Exception as e:
            print(f"An unexpected error occurred updating simulation name for {simulation_id}: {e}")
            return f"Error updating simulation name for '{simulation_id}': An internal error occurred."


    def add_simulation(self, simulation_data: dict) -> str:
        """
        Adds a new simulation entry to the archive.

        Args:
            simulation_data (dict): A dictionary containing the simulation data,
                                    expected to have a 'simulation_ID' key.

        Returns:
            str: A string indicating success or failure.
        """
        # Basic validation
        sim_id = simulation_data.get("simulation_ID")
        if not sim_id:
            return "Error: 'simulation_ID' key is required to add a simulation."

        if not isinstance(simulation_data, dict):
             return f"Error: Input data must be a dictionary, received {type(simulation_data).__name__}."

        if sim_id in self._state:
            return f"Error: Simulation with ID '{sim_id}' already exists."

        try:
            # Add the new simulation dictionary to the main state dictionary
            self._state[sim_id] = simulation_data

            # --- Save the state after modification ---
            self._write_json(self._state)

            return f"Simulation '{sim_id}' added successfully."
        except TypeError as e:
             # Catch non-serializable data before write_json
             print(f"Error adding simulation {sim_id}: Data is not JSON serializable: {e}")
             # Optionally remove the invalid data from _state if it was added
             self._state.pop(sim_id, None)
             return f"Error: Could not add simulation '{sim_id}'. Data format issue: {e}"
        except Exception as e:
            print(f"An unexpected error occurred adding simulation {sim_id}: {e}")
            return f"Error adding simulation '{sim_id}': An internal error occurred."


    def details_of_simulation(self, simulation_id: str) -> str:
        """
        Retrieves a specific simulation's data by its ID.

        Args:
            simulation_id (str): The ID of the simulation to retrieve.

        Returns:
            str: A string containing the simulation data in JSON format, or an error message.
        """
        if simulation_id in self._state:
            # Return the data as a formatted JSON string for clarity
            sim_data_str = json.dumps(self._state[simulation_id], indent=2)
            return f"Data for simulation '{simulation_id}':\n```json\n{sim_data_str}\n```"
        else:
            return f"Error: Simulation with ID '{simulation_id}' not found."

    def delete_simulation(self, simulation_id: str) -> str:
        """
        Deletes a simulation entry by its ID.

        Args:
            simulation_id (str): The ID of the simulation to delete.

        Returns:
            str: A string indicating success or failure.
        """
        if simulation_id not in self._state:
            return f"Error: Simulation with ID '{simulation_id}' not found for deletion."

        try:
            # Remove the entry from the main state dictionary
            del self._state[simulation_id]

            # --- Save the state after modification ---
            self._write_json(self._state)

            return f"Simulation '{simulation_id}' deleted successfully."
        except Exception as e:
            print(f"An unexpected error occurred deleting simulation {simulation_id}: {e}")
            return f"Error deleting simulation '{simulation_id}': An internal error occurred."


    def list_simulations(self) -> str:
        """
        Lists all simulation IDs currently in the archive.

        Returns:
            str: A string listing the simulation IDs or indicating none exist.
        """
        sim_ids = list(self._state.keys())
        if not sim_ids:
            return "No simulations found in the archive."
        else:
            # Format the list nicely for AI/user
            # Optionally include simulation names if they exist
            sim_list = "\n".join([
                f"- ID: '{sim_id}', Name: '{self._state[sim_id].get('simulation_name', 'N/A')}'"
                for sim_id in sim_ids
            ])
            return f"Found {len(sim_ids)} simulation(s):\n{sim_list}"

    def get_all_simulations_data(self) -> str:
        """
        Retrieves data for all simulations.

        Returns:
            str: A string containing all simulation data in JSON format, or an error message.
        """
        if not self._state:
             return "No simulations found in the archive."

        try:
            all_data_str = json.dumps(self._state, indent=2)
            return f"All simulation data:\n```json\n{all_data_str}\n```"
        except Exception as e:
            print(f"Error retrieving all simulation data: {e}")
            return f"Error retrieving all simulation data: An internal error occurred."

    def create_entry(self, json_path: str): #
            """
            Creates a new simulation entry dictionary with a unique short UID
            and sets the simulation file path, then adds it to the manager.

            Args:
                json_path (str): The file path to the specific simulation's data.

            Returns:
                str: A string indicating success or failure of adding the entry,
                     or an error message if creation failed.
            """
            # --- 1. Generate a unique short UID ---
            def generate_short_uid(length=6):
                """Generates a random alphanumeric string of specified length."""
                characters = string.ascii_lowercase + string.digits
                return ''.join(random.choice(characters) for _ in range(length))

            sim_id = generate_short_uid()
            # Ensure the ID is unique among existing entries
            while sim_id in self._state:
                sim_id = generate_short_uid()

            # --- 2. Create the base structure for the entry ---
            # We use the template but populate the specific fields
            new_entry = self._simulation_entry_template.copy()
            new_entry["simulation_ID"] = sim_id # Set the generated ID
            new_entry["simulation_file_path"] = json_path
            new_entry["simulation_name"] = "" # As requested, leave empty
            new_entry["simulation_details"] = [] # As requested, leave as empty list

            # --- 3. Add the entry using the existing add_simulation method ---
            # This handles the validation and saving
            add_result = self.add_simulation(new_entry)

            # Return the result from add_simulation
            if "Error" in add_result:
                 return f"Error creating archive entry for {json_path}: {add_result}"
            else:
                 return new_entry
