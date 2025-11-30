from tokenizers import Tokenizer
from abc import ABC
import sys
import os

from .opensource_dict import mapped_models


class OpenSourceTokenizer(ABC):
    def __init__(self, select_model):

        self.HuggingFace_Key = os.getenv("HUGGING_ACCESS_TOKEN")

        general_model = select_model

        if general_model in mapped_models:
            self.hugging_ID = mapped_models[general_model]
        else:
            # This error now only appears if OpenSourceTokenizer is actually chosen AND its model isn't mapped.
            print(f"Model '{general_model}' not mapped to a HuggingFace repo ID in (utils.token_providers.opensource_dict.mapped_models). Please configure the model.")
            sys.exit(0) # Exit if the specific model isn't mapped for OpenSourceTokenizer

        self.tokenizer = Tokenizer.from_pretrained(self.hugging_ID, token=self.HuggingFace_Key)

    def count_tokens(self, text):
        output = self.tokenizer.encode(text)
        length = len(output.tokens)
        return length