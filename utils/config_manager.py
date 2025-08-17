import os
from utils.generic_json_tool import GenericJsonTool

class ConfigManager(GenericJsonTool):
    def __init__(self, base_path, mock=False):
        self.base_path = base_path
        if mock:
            self.base_path = os.path.join(base_path,"mock_configs/")
        
        self.json_filename = "bots_configs_archive.json"

        self._default_state = {}
        
        super().__init__(self.base_path)
        
        self.archive = self._state
        self.active_config = {}  # This is now a simple dictionary

        mock_config = {
                    "AI_DeepMemory": {
                        "deep_memory_flag": True,
                        "deep_memory_ai_provider": "mock_provider",
                        "deep_memory_ai": "mock_bot",
                        "deep_memory_embeddings_provider": "ollama"
                    },
                    "AI": {
                        "general_ai_provider": "mock_provider",
                        "memory_ai_provider": "mock_provider",
                        "cook_provider": "mock_provider",
                        "pets_folder": "mock_bot_folder",
                        "general_model": "mock_bot",
                        "memory_model": "mock_bot",
                        "cook_model": "mock_bot",
                        "sys_prompt": "Mock sys prompt"
                    },
                    "Tools": {
                        "enable_youtube": False,
                        "enable_discogs": False,
                        "enable_musicbrainz": False,
                        "enable_bluesky": False
                    },
                    "game_settings": {
                        "initial_state": "base_state",
                        "tts_provider": "macos_say",
                        "selected_voice": ""
                    }
                }
                    
        if mock:
            self.active_config = mock_config
            self.save_config_to_archive("mock_bot_config")
        
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
