# ai_managers/llm_clients/abstract_llm_client.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# Assuming llm_response_types.py is available
from ai_managers.agents.agents_utils.llm_response_types import LLMResponse

from utils.pydantic_models import StructuredMemory

class AbstractLLMClient(ABC):
    """
    Abstract Base Class for all Large Language Model (LLM) clients.
    Concrete implementations will provide specific API interactions
    and normalize responses to the LLMResponse structure.
    """

    @abstractmethod
    async def generate_response(
        self,
        messages: StructuredMemory, # Corresponds to StructuredMemory
        tools: Optional[List[Dict[str, Any]]] = None, # Corresponds to an OpenAI tools format
        model: str = "default-model",
        tool_choice: str = "auto", # Or a more specific enum if needed
        **kwargs # For any additional provider-specific settings
    ) -> LLMResponse:
        """
        Generates a response from the LLM, normalizing it into a
        standardized LLMResponse format.

        Args:
            messages: The conversation history/prompt for the LLM.
            tools: List of available tools (functions) for the LLM to call.
            model: The name of the LLM model to use.
            tool_choice: Strategy for tool usage (e.g., "auto", "none").
            **kwargs: Additional provider-specific parameters.

        Returns:
            An LLMResponse object containing normalized function call details
            or text content.
        """
        pass