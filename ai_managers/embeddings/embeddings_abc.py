import numpy as np
from sklearn.decomposition import PCA
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """
    Abstract Base Class for AI embedding providers.

    This class defines the common interface for generating and optionally
    reducing the dimensionality of embeddings.
    """

    def __init__(self, embedding_model=None, target_embedding_dimension: int = 768):
        """
        Initializes the EmbeddingProvider.

        Args:
            target_embedding_dimension (int): The desired output dimension for embeddings
                                              after reduction, if applicable.
        """
        self.target_embedding_dimension = target_embedding_dimension
        self.selected_model=embedding_model

    @abstractmethod
    def make_embeddings(self, text: str) -> np.ndarray:
        """
        Abstract method to generate embeddings from a string.
        Each concrete provider must implement this method to call its specific AI API.

        Args:
            text: str: A list of text strings to generate embeddings for.

        Returns:
            np.ndarray: A 2D NumPy array of embeddings.
                        Shape: (num_texts, original_embedding_dimension).
        """
        pass
