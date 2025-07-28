import numpy as np
from utils.embeddings_providers.embeddings_abc import EmbeddingProvider
import os

from google import genai

class GoogleEmbeddingProvider(EmbeddingProvider):
    """
    Concrete implementation for a Google embedding provider.
    """

    def __init__(self, selected_model="gemini-embedding-exp-03-07", target_embedding_dimension: int = 768):
        # Pass both arguments to the parent class's __init__
        super().__init__(embedding_model=selected_model, target_embedding_dimension=target_embedding_dimension)
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key is None:
            raise ValueError("GEMINI_API_KEY API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client = genai.Client(api_key=api_key)

    def google_embeddings(self, text):
 
        result = self.client.models.embed_content(
                model=self.selected_model,
                contents=text
            
        )


        embeddings_list = [emb.values for emb in result.embeddings]
        embeddings_array = np.array(embeddings_list)

        return embeddings_array

    def make_embeddings(self, text: str) -> np.ndarray:
        #print(f"Calling Google API to make embeddings for {text}")
        embeddings = self.google_embeddings(text)
        return embeddings