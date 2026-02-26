import tiktoken



from abc import ABC

class OpenAITokenizer(ABC):
    def __init__(self, encoding_name="o200k_base"):
        self.encoding_name = encoding_name

    def count_tokens(self, text: str) -> int:
        """
        Abstract method to count tokens

        Args:
            text: str: A string to count the tokens from

        Returns:
                int: Lenght of string passed in tokens
        """
        return self.num_tokens_from_string(string=text)
    
    
    def num_tokens_from_string(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        encoding = tiktoken.get_encoding(self.encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens