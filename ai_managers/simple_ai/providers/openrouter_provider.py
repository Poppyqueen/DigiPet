from openai import OpenAI
import instructor
from instructor import Mode
import os
from typing import Any
from pydantic import BaseModel
from ai_managers.simple_ai.abstract_provider import SimpleAI


class OpenRouterProv(SimpleAI):
    """
    Simple OpenRouter provider.
    OpenRouter is OpenAI-compatible, so we use the OpenAI client
    pointed at the OpenRouter base URL.
    Structured output is handled via instructor (JSON mode),
    since not all OpenRouter models support the beta.parse() endpoint.
    """

    def __init__(self, selected_model=None):
        super().__init__(selected_model)
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key is None:
            raise ValueError("OPENROUTER_API_KEY not found. Please set the OPENROUTER_API_KEY environment variable.")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.structure_client = instructor.from_openai(self.client, mode=Mode.JSON)

    def response_output(self, system: str, message: str) -> str:
        """
        Simple string response from the model.
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": message},
                ]
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenRouter API: {e}")
            return None

    def structured_output(self, system: str, user: str, structure: BaseModel) -> BaseModel:
        """
        Structured response guided by a Pydantic model via instructor.
        """
        try:
            return self.structure_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_model=structure,
            )
        except Exception as e:
            print(f"Error calling OpenRouter API for structured output with structure {structure.__name__}: {e}")
            return None