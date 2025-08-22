import tiktoken



from abc import ABC

class OpenAITokenizer(ABC):

    def count_tokens(self, text: str) -> int:
        """
        Abstract method to count tokens

        Args:
            text: str: A string to count the tokens from

        Returns:
                int: Lenght of string passed in tokens
        """
        return self.num_tokens_from_string(string=text)
    
    
    def num_tokens_from_string(self, string: str, encoding_name: str = "o200k_base") -> int:
        """Returns the number of tokens in a text string."""
        #encoding_n = tiktoken.encoding_for_model(encoding_name).name  # returns str 
        #encoding = tiktoken.get_encoding(encoding_n)

        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens