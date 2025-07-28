# embedding_operations.py

import numpy as np
from scipy.spatial.distance import cosine
from memory.deep_memory_db_managers.deep_memory_database import DatabaseManager
class EmbeddingOperations:
    """
    A class to handle operations related to embeddings, such as similarity calculation
    and searching.
    """

    def __init__(self, db_path):
        """
        Initializes the EmbeddingOperations with a DatabaseManager instance.

        Args:
            db_path (str): The file path for the SQLite database.
        """
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.create_tables() # Ensure tables exist for operations

    def calculate_cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculates the cosine similarity between two embedding vectors.
        Cosine similarity ranges from -1 (opposite) to 1 (identical).
        A higher value indicates greater similarity.

        Args:
            embedding1 (np.ndarray): The first embedding vector.
            embedding2 (np.ndarray): The second embedding vector.

        Returns:
            float: The cosine similarity between the two embeddings.
        """
        if embedding1 is None or embedding2 is None:
            raise ValueError("Embeddings cannot be None for similarity calculation.")
        if embedding1.shape != embedding2.shape:
            raise ValueError("Embeddings must have the same shape for similarity calculation.")
        
        # cosine from scipy.spatial.distance returns cosine distance, which is 1 - cosine similarity
        return 1 - cosine(embedding1, embedding2)

    def search_similar_characteristics(self, query_embedding: np.ndarray, top_n: int = 5) -> list:
        """
        Searches the database for characteristics most similar to a given query embedding.

        Args:
            query_embedding (np.ndarray): The embedding to use for the similarity search.
            top_n (int): The number of top similar characteristics to return.

        Returns:
            list: A list of dictionaries, each containing characteristic data and its 
                  similarity score to the query embedding, sorted by similarity (descending).
        """
        if query_embedding is None:
            print("Query embedding cannot be None.")
            return []

        all_characteristics = self.db_manager.get_all_characteristics()
        
        # Filter out characteristics without embeddings or with incompatible shapes
        searchable_characteristics = []
        for char in all_characteristics:
            if char.get("embeddings") is not None and char["embeddings"].shape == query_embedding.shape:
                searchable_characteristics.append(char)
            elif char.get("embeddings") is not None:
                print(f"Warning: Skipping characteristic ID {char['id']} due to embedding shape mismatch: {char['embeddings'].shape} vs {query_embedding.shape}")
            else:
                print(f"Warning: Skipping characteristic ID {char['id']} as it has no embedding.")


        if not searchable_characteristics:
            print("No characteristics with valid embeddings found for search.")
            return []

        similarities = []
        for char in searchable_characteristics:
            try:
                similarity = self.calculate_cosine_similarity(query_embedding, char["embeddings"])
                similarities.append({
                    "characteristic_id": char["id"],
                    "entity_id": char["entity_id"],
                    "raw_text": char["raw_text"],
                    "similarity_score": similarity
                })
            except ValueError as e:
                print(f"Error calculating similarity for characteristic ID {char['id']}: {e}")
                continue # Skip this characteristic if there's an issue

        # Sort by similarity score in descending order
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)

        return similarities[:top_n]

    def compare_two_characteristics(self, char_id1: int, char_id2: int) -> float:
        """
        Compares the embeddings of two specific characteristics by their IDs.

        Args:
            char_id1 (int): The ID of the first characteristic.
            char_id2 (int): The ID of the second characteristic.

        Returns:
            float: The cosine similarity between the two characteristics' embeddings,
                   or None if either characteristic or its embedding is not found.
        """
        char1 = self.db_manager.get_characteristic_by_id(char_id1)
        char2 = self.db_manager.get_characteristic_by_id(char_id2)

        if not char1 or not char1.get("embeddings"):
            print(f"Characteristic {char_id1} or its embedding not found.")
            return None
        if not char2 or not char2.get("embeddings"):
            print(f"Characteristic {char_id2} or its embedding not found.")
            return None
        
        try:
            return self.calculate_cosine_similarity(char1["embeddings"], char2["embeddings"])
        except ValueError as e:
            print(f"Error comparing characteristics {char_id1} and {char_id2}: {e}")
            return None

    def close(self):
        """Closes the database connection."""
        self.db_manager.close()

if __name__ == '__main__':
    db_file = "my_entity_database.db"
    embedding_ops = EmbeddingOperations(db_file)

    print("\n--- Demonstrating Embedding Operations ---")

    # First, ensure some data exists in the database by running DatabaseManager.py once
    # If you haven't run it, the following operations might not find data.

    # Example 1: Comparing two existing characteristics
    # Assuming char_v1_id and char_v2_id from DatabaseManager.py example exist
    # You might need to manually find these IDs if running this separately
    # For demonstration, let's assume we know some IDs or fetch them dynamically
    
    # Let's fetch all characteristics to get their IDs
    all_chars = embedding_ops.db_manager.get_all_characteristics()
    if len(all_chars) >= 2:
        char_id_1 = all_chars[0]["id"]
        char_id_2 = all_chars[1]["id"]
        print(f"\nComparing characteristic {char_id_1} and {char_id_2}:")
        similarity_score = embedding_ops.compare_two_characteristics(char_id_1, char_id_2)
        if similarity_score is not None:
            print(f"Cosine Similarity: {similarity_score:.4f}")
        else:
            print("Could not compare characteristics.")
    else:
        print("\nNot enough characteristics in the database to perform a comparison example.")


    # Example 2: Searching for similar characteristics
    print("\n--- Searching for Similar Characteristics ---")
    # Create a dummy query embedding (in a real scenario, this would come from an ML model)
    query_embedding_example = np.array([0.1, 0.2, 0.3, 0.4, 0.48], dtype=np.float32) 
    print(f"Query Embedding: {query_embedding_example}")

    similar_chars = embedding_ops.search_similar_characteristics(query_embedding_example, top_n=3)

    if similar_chars:
        print("\nTop 3 similar characteristics:")
        for char in similar_chars:
            print(f"  ID: {char['characteristic_id']}, Entity ID: {char['entity_id']}")
            print(f"  Raw Text: '{char['raw_text']}'")
            print(f"  Similarity Score: {char['similarity_score']:.4f}\n")
    else:
        print("No similar characteristics found.")

    # Close the database connection
    embedding_ops.close()
