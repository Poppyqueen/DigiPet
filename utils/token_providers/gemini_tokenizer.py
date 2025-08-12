from google import genai

from abc import ABC

import os
from dotenv import load_dotenv

import configparser


class GeminiTokenizer(ABC):
    def __init__(self):

        load_dotenv()
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=gemini_api_key)


        main_config = configparser.ConfigParser()
        main_config.read('main_config.ini')
        self.general_model = main_config['AI']['general_model']

    
    def count_tokens(self, text: str) -> int:
        """Returns the number of tokens in a text string."""
        # Count tokens using the new client method.
        response_object = self.client.models.count_tokens(
            model=self.general_model, contents=text
        )
        total_tokens = response_object.total_tokens 

        #print("total_tokens: ", total_tokens)
        # ( e.g., total_tokens: 10 )
        return int(total_tokens)
