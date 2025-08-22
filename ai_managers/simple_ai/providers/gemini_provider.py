from google import genai
from google.genai import types

import os
from typing import Any
import time
from pydantic import BaseModel

from ai_managers.simple_ai.abstract_provider import SimpleAI


class GeminiProv(SimpleAI):
    """
    Simple Gemini provider
    """
    def __init__(self, selected_model=None):
        super().__init__(selected_model)
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key is None:
            raise ValueError("GEMINI_API_KEY API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client = genai.Client(api_key=api_key)

    def structured_output(self, system, user, structure: BaseModel) -> BaseModel:

        chat_config = types.GenerateContentConfig(
        system_instruction=system,
        response_schema=structure,
        response_mime_type="application/json"
        )
        response = self.client.models.generate_content(
            model=self.ai_model,
            contents=user,
            config=chat_config
        )

        # Use instantiated objects.
        my_response: BaseModel = response.parsed

        return my_response
    
    def response_output(self, system: str, message: str) -> str:
        """
        Method to get a simple string response from a model.
        Must be implemented by subclasses.
        """
        chat_config = types.GenerateContentConfig(
        system_instruction=system
        )

        response = self.client.models.generate_content(
            model=self.ai_model, contents=message,config=chat_config
        )
        #print(response.text)
        return response.text