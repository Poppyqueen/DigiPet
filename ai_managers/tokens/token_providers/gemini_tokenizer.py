from google import genai
from abc import ABC



class GeminiTokenizer(ABC):
    def __init__(self, select_model):
        self.general_model =select_model

        self.client=genai.Client()
    
    def count_tokens(self, text: str) -> int:
        """Returns the number of tokens in a text string."""
        # Count tokens using the new client method.
        response_object = self.client.models.count_tokens(
            model=self.general_model, contents=text
        )
        total_tokens = response_object.total_tokens 
        return int(total_tokens)
