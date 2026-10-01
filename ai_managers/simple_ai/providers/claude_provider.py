# claude_provider.py
# Suggested location: ai_managers/simple_ai/anthropic_provider.py

import os
from typing import Optional

from anthropic import Anthropic
from pydantic import BaseModel

from ai_managers.simple_ai.abstract_provider import SimpleAI

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 16000


class AnthropicProv(SimpleAI):
    """
    Simple Anthropic provider.
    Structured output uses the SDK's native messages.parse() with a Pydantic model.
    On failure both methods print the error and return None (same as OpenRouterProv).
    """

    def __init__(self, selected_model=None):
        super().__init__(selected_model or DEFAULT_MODEL)
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key is None:
            raise ValueError("ANTHROPIC_API_KEY not found. Please set the ANTHROPIC_API_KEY environment variable.")
        self.client = Anthropic(api_key=api_key)

    def structured_output(self, system, user, structure: BaseModel) -> Optional[BaseModel]:
        """
        Structured response guided by a Pydantic model, using native structured outputs.
        Returns an instance of `structure`, or None on failure.
        """
        try:
            response = self.client.messages.parse(
                model=self.ai_model,
                max_tokens=DEFAULT_MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=structure,
            )
            return response.parsed_output
        except Exception as e:
            print(f"Error calling Anthropic API for structured output with structure {structure.__name__}: {e}")
            return None

    def response_output(self, system: str, message: str) -> Optional[str]:
        """
        Simple string response from the model.
        """
        try:
            response = self.client.messages.create(
                model=self.ai_model,
                max_tokens=DEFAULT_MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": message}],
            )
            return "\n".join(b.text for b in response.content if b.type == "text").strip()
        except Exception as e:
            print(f"Error calling Anthropic API: {e}")
            return None