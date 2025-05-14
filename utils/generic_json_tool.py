# generic_json_tool.py 
# Base module to create state management tools using JSON files. Used inside "emoter" tool in the "tools_folder".

import os
import json

class GenericJsonTool:
    """
    Boilerplate class for a modular tool that manages its state using a JSON file.

    Follows the pattern of initializing with a base path, loading state from
    a JSON file if it exists, using a default state if not, persisting state
    to the file after modifications, and exposing public methods that return
    string results for AI integration.
    """

    def __init__(self, base_path):
        """
        Initializes the tool, ensuring the directory and JSON file exist
        and loading the state.

        Args:
            base_path (str): The base directory path where the JSON file will be stored.

        IMPORTANT: Inheriting classes MUST set self.json_filename and self._default_state
                   BEFORE calling super().__init__(base_path).
        """
        self.base_path = base_path

        # Inheriting class MUST set self.json_filename before this point
        if not hasattr(self, 'json_filename') or not isinstance(self.json_filename, str) or not self.json_filename:
             raise NotImplementedError("Inheriting classes must set self.json_filename (a non-empty string) before calling super().__init__")
        self.json_path = os.path.join(base_path, self.json_filename)

        # Inheriting class MUST set self._default_state before this point
        if not hasattr(self, '_default_state') or not isinstance(self._default_state, dict):
             raise NotImplementedError("Inheriting classes must set self._default_state (a dictionary) before calling super().__init__")


        self._ensure_base_path_exists()

        # Attempt to load state from the file
        loaded_state = self._read_json()

        # Check if loaded_state is valid (is a dictionary and contains *all* top-level keys from the specific default state)
        # This check ensures the basic structure matches what the inheriting class expects.
        # If loading fails or the file was empty/corrupted or doesn't contain the required keys, use the default state.
        if isinstance(loaded_state, dict) and all(key in loaded_state for key in self._default_state):
            self._state = loaded_state
            print(f"Loaded state for {self.__class__.__name__} from {self.json_path}")
        else:
            # Use a copy of the default state defined by the inheriting class
            self._state = self._default_state.copy()
            print(f"JSON file for {self.__class__.__name__} not found, invalid format, or missing expected keys. Using default state.")
            # Ensure the base directory exists before writing the default state
            self._ensure_base_path_exists() # Redundant if already called, but safe
            # Write the default state immediately if file was missing or invalid
            self._write_json(self._state)

        #print(f"{self.__class__.__name__} initialized with state: {self._state}")


    def _ensure_base_path_exists(self):
        """Ensures the base directory for the JSON file exists."""
        if not os.path.exists(self.base_path):
            try:
                os.makedirs(self.base_path)
                # print(f"Base directory created at {self.base_path}") # Use print only if verbose logging is on
            except OSError as e:
                 print(f"Error creating base directory {self.base_path}: {e}")
                 # Depending on severity, you might want to raise the exception
                 # raise e


    def _read_json(self):
        """Reads the JSON data from the file. Returns None if file doesn't exist, is empty, or decode fails."""
        try:
            if not os.path.exists(self.json_path):
                # print(f"JSON file not found at {self.json_path} for reading.") # Too verbose during normal startup
                return None # File doesn't exist yet, return None

            with open(self.json_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    # print(f"JSON file at {self.json_path} is empty.") # Use print only if verbose logging is on
                    return None # File is empty

                # Attempt to parse JSON
                data = json.loads(content)
                # A simple check: is it a dictionary? Most states will be.
                if not isinstance(data, dict):
                     print(f"Warning: JSON file at {self.json_path} content is not a dictionary ({type(data).__name__}). Expected dict.")
                     return None # Content exists but isn't the expected format
                return data

        except FileNotFoundError:
             # This should ideally be caught by the os.path.exists check, but good to have
            print(f"Error: JSON file not found at {self.json_path} during read attempt (should not happen if os.path.exists was true).")
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {self.json_path}: {e}")
            return None
        except IOError as e:
            print(f"Error reading JSON file at {self.json_path}: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during JSON read: {e}")
            return None


    def _write_json(self, data):
        """Writes data to the JSON file with indentation."""
        try:
            # Ensure the base directory exists before writing (redundant if done in init, but safe)
            self._ensure_base_path_exists()

            # Ensure data is a dictionary before attempting to write
            if not isinstance(data, dict):
                 print(f"Error: Data to write is not a dictionary ({type(data).__name__}). Cannot save state.")
                 return # Don't attempt to dump non-dict data

            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            # print(f"State written to {self.json_path}") # Use print only if verbose logging is on
        except TypeError as e:
             print(f"Serialization error: Cannot write state to JSON. Data is not JSON serializable: {e}. Data to write type: {type(data).__name__}")
        except IOError as e:
            print(f"Error writing to JSON file at {self.json_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during JSON write: {e}")

# --- End of Corrected GenericJsonTool ---
