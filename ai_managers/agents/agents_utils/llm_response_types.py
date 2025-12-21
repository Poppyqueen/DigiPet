# llm_response_types.py
from typing import List, Dict, Union, Optional, Any
from dataclasses import dataclass

@dataclass
class FunctionCallDetails:
    name: str
    arguments: Dict[str, Any] # Parsed arguments as a dictionary
    call_id: Optional[str] = None # Optional, as not all providers might have this
    thought_signature: Optional[str] = None # Optional, as not all providers might have this

@dataclass
class TextMessageDetails:
    text: str

@dataclass
class LLMResponse:
    """
    A simplified and normalized structure for AI model responses.
    This is what all concrete LLM clients will return.
    """
    function_calls: Optional[List[FunctionCallDetails]] = None
    text_content: Optional[str] = None

    # Helper properties for easy checking
    @property
    def has_function_calls(self) -> bool:
        return bool(self.function_calls)

    @property
    def has_text_content(self) -> bool:
        return bool(self.text_content)