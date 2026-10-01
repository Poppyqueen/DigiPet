# anthropic_tokenizer.py
# Suggested location: ai_managers/tokens/token_providers/anthropic_tokenizer.py

from abc import ABC

from anthropic import Anthropic


class AnthropicTokenizer(ABC):
    """
    Token counter backed by Anthropic's token-counting endpoint.

    Claude has no local tokenizer, so this is a network call (free, but rate-limited).
    Counts are an estimate and include a few tokens of message-framing overhead.
    Reads ANTHROPIC_API_KEY from the environment.
    """

    def __init__(self, select_model):
        self.general_model = select_model
        self.client = Anthropic()

    def count_tokens(self, text: str) -> int:
        """Returns the number of tokens in a text string."""
        if not text or not text.strip():
            return 0  # the API rejects empty content

        response_object = self.client.messages.count_tokens(
            model=self.general_model,
            messages=[{"role": "user", "content": text}],
        )
        return int(response_object.input_tokens)
    
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    tokenizer = AnthropicTokenizer("claude-haiku-4-5-20251001")
    print(tokenizer.count_tokens("This is a tokenizer test!"))