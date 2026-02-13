
from groq import Groq
import instructor
from instructor import Mode

import os
from pydantic import BaseModel

from ai_managers.simple_ai.abstract_provider import SimpleAI


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
        self.structure_client = instructor.from_groq(self.client, mode=Mode.JSON)



    def structured_output(self, system, user, structure: BaseModel) -> BaseModel:
        """
        Method to get a structured response from a given pydantic model                                                             
        Returns the requested structure as a pydantic object.                               
        """


        # Create structured output
        response_model = self.structure_client.chat.completions.create(
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