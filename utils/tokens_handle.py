
from utils.token_providers.gemini_tokenizer import GeminiTokenizer
from utils.token_providers.openai_tokenizer import OpenAITokenizer
from utils.token_providers.opensource_tokenizer import OpenSourceTokenizer


import sys
import configparser

main_config = configparser.ConfigParser()
main_config.read('main_config.ini')
config_selected_provider = main_config['AI']['general_ai_provider']

print(f"DEBUG: Value of config_selected_provider from INI: '{config_selected_provider}'")


available_providers = {
    "gemini": {
        "client":GeminiTokenizer,
        },
    "openai": {
        "client":OpenAITokenizer,
        },
    "groq":{
        "client":OpenSourceTokenizer,
    },
    "ollama":{
        "client":OpenSourceTokenizer,
    }
}

# 4. Use the mapping dictionary to get the actual JSON structure
if config_selected_provider in available_providers:
    config_client = available_providers[config_selected_provider]["client"]
    #print(f"Loaded state: {config_selected_provider}")
    print(config_client)

else:
    print(f"Error: '{config_selected_provider}' is not a recognized provider.")
    sys.exit(0)


class token_manager():
    def __init__(self):
        self.tokenizer_selected=config_client()
    def num_tokens_from_string(self, string: str, encoding_name: str = "o200k_base") -> int:
        """Returns the number of tokens in a text string."""
        return self.tokenizer_selected.count_tokens(string)
    

