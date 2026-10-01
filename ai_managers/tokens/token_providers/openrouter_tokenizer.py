# openrouter_tokenizer.py
from ai_managers.tokens.token_providers.tokenizer_abc import TokenizerProvider

class OpenRouterTokenizer(TokenizerProvider):
    """
    Delegates to the appropriate tokenizer based on the underlying model provider.
    OpenRouter model strings follow the format: 'provider/model-name'
    e.g. 'anthropic/claude-sonnet-4-5', 'openai/gpt-4o', 'google/gemini-2.0-flash-001'
    """

    PROVIDER_PREFIXES = {
        "openai":    "_load_tiktoken", # this works, 
        # "anthropic": "_load_opensource", # needs a tokenizer, not implemented, yet
        "google":    "_load_google", # this works
        "meta-llama":"_load_opensource", # this works
        # "mistralai": "_load_opensource", # TODO: implement Mistral-common tokenizer
        "~deepseek":"_load_opensource", # works! 
        "anthropic":"_load_anthropic" # You need an anthropic account with credits to use their tokenizer (tokenizer is free)

        # Add more providers as needed, see https://openrouter.ai/models 
        # use _load_opensource for... open source models...
        # if using _load_opensource, make sure to define model mapping in ai_managers/tokens/token_providers/opensource_dict.py
        # the mapping is model ID and the HuggingFace ID
    }

    def __init__(self, model: str):
        self.model = model
        self._tokenizer = self._resolve_tokenizer(model)

    @staticmethod
    def _strip_provider_prefix(model: str) -> str:
        """Strips the 'provider/' prefix from an OpenRouter model string."""
        return model.split("/", 1)[-1]
    
    def _resolve_tokenizer(self, model: str):
        prefix = model.split("/")[0].lower() if "/" in model else ""
        loader = self.PROVIDER_PREFIXES.get(prefix)

        if loader is None:
            raise ValueError(
                f"No tokenizer mapping for OpenRouter model prefix '{prefix}' "
                f"(model: '{model}'). Add it to PROVIDER_PREFIXES or register "
                f"the model in opensource_dict.py."
            )

        return getattr(self, loader)(model)

    def _load_anthropic(self, model: str):
        from ai_managers.tokens.token_providers.claude_tokenizer import AnthropicTokenizer
        return AnthropicTokenizer(self._strip_provider_prefix(model))

    def _load_google(self, model: str):
        from ai_managers.tokens.token_providers.gemini_tokenizer import GeminiTokenizer
        return GeminiTokenizer(self._strip_provider_prefix(model))

    def _load_tiktoken(self, model: str):
        from ai_managers.tokens.token_providers.openai_tokenizer import OpenAITokenizer
        model_name = self._strip_provider_prefix(model)
        if "oss" in model_name:
            return OpenAITokenizer("o200k_harmony")
        return OpenAITokenizer()

    def _load_opensource(self, model: str):
        from ai_managers.tokens.token_providers.opensource_tokenizer import OpenSourceTokenizer
        return OpenSourceTokenizer(self._strip_provider_prefix(model))

    def count_tokens(self, text: str) -> int:
        # OpenSourceTokenizer already implements count_tokens
        return self._tokenizer.count_tokens(text)