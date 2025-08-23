# embedding_operations.py

import numpy as np
from scipy.spatial.distance import cosine
from ai_managers.agents.memory.deep_memory_int.deep_memory_db.deep_memory_database import DatabaseManager
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



    # Add these methods to your EmbeddingOperations class

    def search_similar_characteristics_optimized(self, query_embedding: np.ndarray, top_n: int = 5, 
                                            min_threshold: float = 0.3, entity_ids: list = None) -> list:
        """
        Optimized version of similarity search with filtering options.
        
        Args:
            query_embedding (np.ndarray): The embedding to use for similarity search.
            top_n (int): The number of top similar characteristics to return.
            min_threshold (float): Minimum similarity threshold to include results.
            entity_ids (list, optional): If provided, only search within these entities.
            
        Returns:
            list: A list of dictionaries with similarity scores, filtered and optimized.
        """
        if query_embedding is None:
            print("Query embedding cannot be None.")
            return []

        # Use targeted search if entity_ids provided
        if entity_ids:
            all_characteristics = self.db_manager.get_characteristics_by_entity_ids(entity_ids)
        else:
            # For large databases, consider using get_characteristics_with_entity_names with a limit
            total_chars = self.db_manager.get_total_characteristics_count()
            if total_chars > 1000:  # Arbitrary threshold
                # Limit search to recent characteristics for performance
                all_characteristics = self.db_manager.get_characteristics_with_entity_names(limit=500)
            else:
                all_characteristics = self.db_manager.get_all_characteristics()
        
        # Filter out characteristics without embeddings or with incompatible shapes
        searchable_characteristics = []
        for char in all_characteristics:
            if char.get("embeddings") is not None and char["embeddings"].shape == query_embedding.shape:
                searchable_characteristics.append(char)

        if not searchable_characteristics:
            print("No characteristics with valid embeddings found for search.")
            return []

        # Use numpy operations for faster similarity calculation
        similarities = []
        query_norm = np.linalg.norm(query_embedding)
        
        for char in searchable_characteristics:
            try:
                char_embedding = char["embeddings"]
                char_norm = np.linalg.norm(char_embedding)
                
                # Skip if either vector is zero
                if query_norm == 0 or char_norm == 0:
                    continue
                    
                # Calculate cosine similarity using dot product
                similarity = np.dot(query_embedding, char_embedding) / (query_norm * char_norm)
                
                # Apply minimum threshold filter early
                if similarity >= min_threshold:
                    result = {
                        "characteristic_id": char["id"],
                        "entity_id": char["entity_id"],
                        "raw_text": char["raw_text"],
                        "similarity_score": float(similarity),
                        "extracted_at_timestamp": char.get("extracted_at_timestamp"),
                        "entity_name": char.get("entity_name")  # Available if using get_characteristics_with_entity_names
                    }
                    similarities.append(result)
                    
            except Exception as e:
                print(f"Error calculating similarity for characteristic ID {char['id']}: {e}")
                continue

        # Sort by similarity score in descending order
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)

        return similarities[:top_n]

    def batch_similarity_search(self, query_embeddings: list, top_n: int = 5, 
                            min_threshold: float = 0.3) -> list:
        """
        Perform similarity search for multiple query embeddings at once.
        More efficient than multiple individual searches.
        
        Args:
            query_embeddings (list): List of numpy arrays to search for.
            top_n (int): Number of top results per query.
            min_threshold (float): Minimum similarity threshold.
            
        Returns:
            list: List of lists, each containing results for one query embedding.
        """
        if not query_embeddings:
            return []
        
        # Get all characteristics once
        all_characteristics = self.db_manager.get_characteristics_with_entity_names()
        searchable_characteristics = [
            char for char in all_characteristics 
            if char.get("embeddings") is not None and 
            char["embeddings"].shape == query_embeddings[0].shape
        ]
        
        if not searchable_characteristics:
            return [[] for _ in query_embeddings]
        
        results = []
        for query_embedding in query_embeddings:
            similarities = []
            query_norm = np.linalg.norm(query_embedding)
            
            if query_norm == 0:
                results.append([])
                continue
                
            for char in searchable_characteristics:
                try:
                    char_embedding = char["embeddings"]
                    char_norm = np.linalg.norm(char_embedding)
                    
                    if char_norm == 0:
                        continue
                        
                    similarity = np.dot(query_embedding, char_embedding) / (query_norm * char_norm)
                    
                    if similarity >= min_threshold:
                        result = {
                            "characteristic_id": char["id"],
                            "entity_id": char["entity_id"],
                            "raw_text": char["raw_text"],
                            "similarity_score": float(similarity),
                            "entity_name": char.get("entity_name")
                        }
                        similarities.append(result)
                        
                except Exception as e:
                    print(f"Error in batch similarity for characteristic ID {char['id']}: {e}")
                    continue
            
            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
            results.append(similarities[:top_n])
        
        return results

    def find_entity_clusters(self, similarity_threshold: float = 0.8) -> dict:
        """
        Find clusters of similar entities based on their current characteristics.
        Useful for understanding entity relationships and avoiding redundant searches.
        
        Args:
            similarity_threshold (float): Minimum similarity to consider entities as related.
            
        Returns:
            dict: Dictionary where keys are entity IDs and values are lists of similar entity IDs.
        """
        # Get current characteristics for all entities
        all_characteristics = self.db_manager.get_characteristics_with_entity_names()
        
        # Filter to only current characteristics (you might need to add logic to identify current vs historical)
        current_characteristics = {}
        for char in all_characteristics:
            entity_id = char["entity_id"]
            if char.get("embeddings") is not None:
                # For simplicity, assume the most recent characteristic is current
                # You might want to use the entity's current_characteristics_id instead
                if (entity_id not in current_characteristics or 
                    char["extracted_at_timestamp"] > current_characteristics[entity_id]["extracted_at_timestamp"]):
                    current_characteristics[entity_id] = char
        
        entity_clusters = {}
        processed = set()
        
        for entity_id, char_data in current_characteristics.items():
            if entity_id in processed:
                continue
                
            cluster = [entity_id]
            char_embedding = char_data["embeddings"]
            char_norm = np.linalg.norm(char_embedding)
            
            if char_norm == 0:
                entity_clusters[entity_id] = cluster
                processed.add(entity_id)
                continue
            
            # Compare with all other entities
            for other_entity_id, other_char_data in current_characteristics.items():
                if other_entity_id == entity_id or other_entity_id in processed:
                    continue
                    
                other_embedding = other_char_data["embeddings"]
                other_norm = np.linalg.norm(other_embedding)
                
                if other_norm == 0:
                    continue
                    
                try:
                    similarity = np.dot(char_embedding, other_embedding) / (char_norm * other_norm)
                    if similarity >= similarity_threshold:
                        cluster.append(other_entity_id)
                        processed.add(other_entity_id)
                except Exception as e:
                    print(f"Error comparing entities {entity_id} and {other_entity_id}: {e}")
                    continue
            
            entity_clusters[entity_id] = cluster
            processed.add(entity_id)
        
        return entity_clusters  
    

    def close(self):
        """Closes the database connection."""
        self.db_manager.close()