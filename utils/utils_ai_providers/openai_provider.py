from openai import OpenAI

import os
from typing import Any
import time
from pydantic import BaseModel



from utils.utils_ai_providers.abstract_provider import SimpleAI

class OpenAIProv(SimpleAI):
    """
    Simple OpenAI provider
    """
    def __init__(self, selected_model=None):
        super().__init__(selected_model)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client = OpenAI(api_key=api_key)

    def _call_openai(self, role: str, system: str, input_content: str) -> str | None:
        """
        Internal method to make a call to the OpenAI chat completions API.
        :param role: The role of the message sender (e.g., "user", "system").
        :param system: The system prompt content.
        :param input_content: The user's input content.
        :return: The content of the AI's response or None if an error occurs.
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": role,
                        "content": input_content
                    }
                ]
            )
            response_content = completion.choices[0].message.content
            return response_content
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return None
        

    def _calls_structured(self, system: str, input_content: str, structure: Any):
        """
        Calls the OpenAI API with a structured response format (e.g., JSON guided by Pydantic).
        This method is kept EXACTLY as provided in the original example.
        """
        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.ai_model, #
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": input_content}
                ],
                response_format=structure
            )
            response_content = completion.choices[0].message.parsed
            time.sleep(1) # Pause to respect API rate limits
            return response_content
        except Exception as e:
            print(f"Error calling OpenAI API for structured output with structure {structure.__name__}: {e}")
            # print(f"System: {system}\nInput: {input_content}") # Optional: uncomment for debugging failed prompts
            return None

    def structured_output(self, system, user, structure: BaseModel) -> BaseModel:
        """
        Method to get a structured response from a given pydantic model                                                             
        Returns the requested structure as a pydantic object.                               
        """
        return self._calls_structured(system, user, structure)

    def response_output(self, system: str, message: str) -> str:
        """
        Method to get a simple string response from a model.
        Must be implemented by subclasses.
        """
        return self._call_openai("user", system, message)