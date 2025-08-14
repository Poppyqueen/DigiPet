# configuration_module.py (or wherever LLMCONFIG is defined)
from typing import Type, TypeVar

# Assuming these imports are correct based on your snippet
from utils.utils_ai_providers.gemini_provider import GeminiProv
from utils.utils_ai_providers.openai_provider import OpenAIProv
from utils.utils_ai_providers.groq_provider import GroqProv
from utils.utils_ai_providers.ollama_provider import OllamaProv
from utils.utils_ai_providers.abstract_provider import SimpleAI
# Define a TypeVar bound to SimpleAI
# This isn't strictly necessary for the get_provider return, but good for more complex scenarios
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class LLMCONFIG:
    """
    Initializes the LLMCONFIG.

    Args:
        model (str): The specific model name to use (e.g., "gemini-pro", "gpt-4").
        provider (str): The name of the LLM provider to use.
                        Available providers are: 'gemini', 'openai', 'groq', 'ollama'.
    """
    def __init__(self, model: str, provider: str):
        self.model = model
        self.provider = provider

        # It's better to store the classes themselves, not instances, if you plan to instantiate them later
        self.available_providers: dict[str, Type[SimpleAI]] = {
            "gemini": GeminiProv,
            "openai": OpenAIProv,
            "groq": GroqProv,
            "ollama": OllamaProv
        }

    def get_provider(self) -> SimpleAI: 
        if self.provider in self.available_providers:
            print(f"Loaded state: {self.provider}")
            # Instantiate the provider here
            return self.available_providers[self.provider](selected_model=self.model)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}. Available providers are: {', '.join(self.available_providers.keys())}")