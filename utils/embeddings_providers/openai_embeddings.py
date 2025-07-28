import numpy as np
import os
from utils.embeddings_providers.embeddings_abc import EmbeddingProvider
from openai import OpenAI

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Concrete implementation for an OpenAI embedding provider.
    """

    def __init__(self, selected_model="text-embedding-3-small", target_embedding_dimension: int = 768):
        super().__init__(embedding_model=selected_model, target_embedding_dimension=target_embedding_dimension)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client = OpenAI(api_key=api_key)

    def openai_embeddings(self, text):
        response = self.client.embeddings.create(
            input=text,
            model=self.selected_model
        )

        # Extract all embeddings. If 'text' was a list, response.data would have multiple items.
        # If 'text' was a single string, response.data will have one item.
        # We want to create a list of embedding arrays, then stack them.
        embeddings_list_of_lists = [data.embedding for data in response.data]
        embeddings_array = np.array(embeddings_list_of_lists) # This will naturally be 2D: (num_texts, embedding_dim)

        return embeddings_array

    def make_embeddings(self, text: str) -> np.ndarray: # Added list[str] to type hint
        #print(f"Calling OpenAI API to make embeddings for {text}")
        embeddings = self.openai_embeddings(text)
        return embeddings

# --- Example Usage ---
if __name__ == "__main__":
    # To properly demonstrate, let's pass a list of strings, even if it's just one,
    # as the current design of openai_embeddings is now more geared for batching.
    # If you always intend to pass a single string, you can keep it as is,
    # but the corrected openai_embeddings will still produce a (1, original_dim) array.
    sample_texts = "The quick brown fox jumps over the lazy dog." # This is still a single string.

    print("--- Using OpenAI Embedding Provider ---")
    openai_provider = OpenAIEmbeddingProvider(selected_model="text-embedding-3-small", target_embedding_dimension=768)
    openai_mbeddings = openai_provider.make_embeddings(sample_texts)
    print(f"OpenAI reduced embeddings shape: {openai_mbeddings.shape}\n")