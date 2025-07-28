
from abc import ABC, abstractmethod


class TokenizerProvider(ABC):
    """
    Abstract Base Class for tokenizer for token counting
    """


    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Abstract method to count tokens

        Args:
            text: str: A string to count the tokens from

        Returns:
                int: Lenght of string passed in tokens
        """
        pass
