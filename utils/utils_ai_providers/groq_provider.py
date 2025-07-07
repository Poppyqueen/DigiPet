
from groq import Groq

import os
from pydantic import BaseModel

from utils.utils_ai_providers.abstract_provider import SimpleAI



class GroqProv(SimpleAI):
    """
    Simple Groq provider
    """
    def __init__(self, selected_model=None):
        super().__init__(selected_model)
        api_key = os.getenv("GROQ_API_KEY")
        if api_key is None:
            raise ValueError("GROQ_API_KEY API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client =Groq(api_key=api_key)



    def structured_output(self, system, user, structure: BaseModel) -> BaseModel:
        """
        Method to get a structured response from a given pydantic model                                                             
        Returns the requested structure as a pydantic object.                               
        """


        # Create structured output
        response_model = self.client.chat.completions.create(
            model=self.ai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_model=structure
        )

        return response_model

    def response_output(self, system: str, message: str) -> str:
        """
        Method to get a simple string response from a model.
        Must be implemented by subclasses.
        """
        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": message,
                }
            ],
            model=self.ai_model,
        )

        return chat_completion.choices[0].message.content