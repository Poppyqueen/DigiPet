import os
from utils.generic_json_tool import GenericJsonTool

class ConfigManager(GenericJsonTool):
    def __init__(self, base_path):
        self.base_path = base_path
        
        self.json_filename = "bots_configs_archive.json"
        self._default_state = {}
        
        super().__init__(base_path)
        
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
            print(f"Configuration '{config_name}' loaded from archive. Now the active config.")
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


    def delete_config_from_archive(self, config_name):
        """
        Deletes a configuration from the archive by its name.
        """
        if config_name in self.archive:
            del self.archive[config_name]
            self._write_json(self.archive)
            print(f"Configuration '{config_name}' successfully deleted from archive.")
        else:
            print(f"Error: Configuration '{config_name}' not found in the archive.")
