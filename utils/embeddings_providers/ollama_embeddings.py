import numpy as np

import ollama


from utils.embeddings_providers.embeddings_abc import EmbeddingProvider



class OllamaEmbeddingProvider(EmbeddingProvider):
    """
    Implementation for a Ollama embeddings provider.
    """

    def __init__(self, selected_model="nomic-embed-text:latest", target_embedding_dimension: int = 768):
        # Pass both arguments to the parent class's __init__
        super().__init__(embedding_model=selected_model, target_embedding_dimension=target_embedding_dimension)

    def ollama_embeddings(self, text)->np.ndarray:
        response = ollama.embed(
        model=self.selected_model,
        input=text
        )

        embeddings = response["embeddings"]
        # Convert to a NumPy array
        embeddings_array = np.array(embeddings)

        return embeddings_array


    def make_embeddings(self, text: str) -> np.ndarray:
        #print(f"Calling Ollama API to make embeddings for {text}")
        embeddings = self.ollama_embeddings(text)
        #print(f"Ollama raw embeddings shape: {embeddings.shape}")
        return embeddings

# --- Example Usage ---
if __name__ == "__main__":
    sample_text = "The quick brown fox jumps over the lazy dog."

    print("--- Using Ollama Embedding Provider ---")
    ollama_provider = OllamaEmbeddingProvider(target_embedding_dimension=768)
    ollama_reduced_embeddings = ollama_provider.get_reduced_embeddings(sample_text)
    print(f"Ollama reduced embeddings shape: {ollama_reduced_embeddings.shape}\n")
