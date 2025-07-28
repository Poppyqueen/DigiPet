from tokenizers import Tokenizer
from abc import ABC
from utils.token_providers.opensource_dict import mapped_models
import sys
import configparser

import os
from dotenv import load_dotenv


class OpenSourceTokenizer(ABC):
    def __init__(self):

        load_dotenv()
        self.HuggingFace_Key = os.getenv("HUGGING_ACCESS_TOKEN")

        # Move the config reading and model mapping logic into __init__
        # This code will ONLY execute when an OpenSourceTokenizer object is created.
        main_config = configparser.ConfigParser()
        main_config.read('main_config.ini')

        # Check for 'general_model' existence in config
        general_model = None # Initialize to None
        if 'AI' in main_config and 'general_model' in main_config['AI']:
            general_model = main_config['AI']['general_model']
        else:
            # Handle the case where general_model is missing in config
            print("Error: 'general_model' key missing in [AI] section of main_config.ini. This is required for OpenSourceTokenizer.")
            sys.exit(1) # Exit with an error code

        if general_model in mapped_models:
            self.hugging_ID = mapped_models[general_model]
        else:
            # This error now only appears if OpenSourceTokenizer is actually chosen AND its model isn't mapped.
            print(f"Model '{general_model}' not mapped to a HuggingFace repo ID in (utils.token_providers.opensource_dict.mapped_models). Please configure the model.")
            sys.exit(0) # Exit if the specific model isn't mapped for OpenSourceTokenizer

        self.tokenizer = Tokenizer.from_pretrained(self.hugging_ID, token=self.HuggingFace_Key)

    def count_tokens(self, text):
        output = self.tokenizer.encode(text)
        length = len(output.tokens)
        return length