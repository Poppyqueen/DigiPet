import os
import shutil
from utils.generic_json_tool import GenericJsonTool

class ConfigManager(GenericJsonTool):
    def __init__(self, base_path):
        self.base_path = base_path            
        
        self.json_filename = "bots_configs_archive.json"

        self._default_state = {}
        
        super().__init__(self.base_path)
        
        self.archive = self._state
        self.active_config = {}  # This is now a simple dictionary

        
        print("ConfigManager initialized. Archive managed by GenericJsonTool.")

    def save_config_to_archive(self, config_name):
        self.archive[config_name] = self.active_config
        self._write_json(self.archive)
        print(f"Configuration '{config_name}' saved to archive.")

    def load_config_from_archive(self, config_name):
        if config_name in self.archive:
            self.active_config = self.archive[config_name]
            #print(f"Configuration '{config_name}' loaded from archive. Now the active config.")
        else:
            print(f"Error: Configuration '{config_name}' not found in the archive.")
            return None

    def get_config(self, section, option):
        return self.active_config.get(section, {}).get(option)

    def set_config(self, section, option, value):
        if section not in self.active_config:
            self.active_config[section] = {}
        self.active_config[section][option] = value
        
    def get_available_configs(self):
        return list(self.archive.keys())

    def get_config_info(self, config_name):
        return self.archive.get(config_name)


    def delete_pet_archive(self, config_name):
        """
        Deletes a configuration from the archive by its name.
        And removes the associated pet folder from the file system.
        """
        if config_name in self.archive:
            pet_folder=self.get_config_info(config_name).get("AI", {}).get("pets_folder")
            pet_folder_path=os.path.join(self.base_path, "bots", pet_folder)

            if not pet_folder:
                print(f"No pet folder specified for configuration '{config_name}', skipping folder deletion.")
            else:
                if os.path.exists(pet_folder_path) and os.path.isdir(pet_folder_path):
                    try:
                        shutil.rmtree(pet_folder_path)
                        print(f"Deleted pet folder '{pet_folder_path}'.")
                    except Exception as e:
                        print(f"Error deleting folder '{pet_folder_path}': {e}")
                else:
                    print(f"Pet folder '{pet_folder_path}' does not exist or is not a directory, skipping deletion.")
           

            del self.archive[config_name]
            self._write_json(self.archive)
            print(f"Configuration '{config_name}' successfully deleted from archive.")
        else:
            print(f"Error: Configuration '{config_name}' not found in the archive.")
