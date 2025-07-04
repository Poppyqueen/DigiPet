# memory_ai_abc.py
from abc import ABC, abstractmethod


# Assuming these are defined in utils/pydantic_models.py
# from utils.pydantic_models import look_ner_structure, save_ner_structure, entity_dict


class MemoryAI(ABC):
    """
    Abstract Base Class for Memory AI operations.
    Defines the interface for various memory-related functionalities.
    """

    def __init__(self, text_capture=None, memory_model=None):
        self.memory_ai=memory_model
        self.text_capture = text_capture

    @abstractmethod
    def summarize_memories(self, to_summarize: str, memory_type: str) -> str | None:
        """
        Abstract method to summarize memories.
        :param to_summarize: The text content to summarize.
        :param memory_type: The type of memory to summarize ("short_term" or "long_term").
        :return: The summarized text or None if an error occurs.
        """
        pass
