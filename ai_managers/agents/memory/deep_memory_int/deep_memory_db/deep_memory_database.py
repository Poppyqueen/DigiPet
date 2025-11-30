
# deep_memory_database.py

import sqlite3
import json
import pickle  # For serializing/deserializing numpy arrays
import numpy as np  # For handling embeddings as numerical arrays
import threading # Import the threading module

from ......utils.loc_datetime import datetime


class DatabaseManager:
    """
    A class to manage an SQLite database for storing entities,
    their characteristics, and related messages in a thread-safe manner.
    """

    def __init__(self, db_path):
        """
        Initializes the DatabaseManager.
        Connection objects will be created on a per-thread basis.

        Args:
            db_path (str): The file path for the SQLite database.
        """
        self.db_path = db_path
        # Use threading.local() to store connection objects. Each thread will have its own.
        self.thread_local = threading.local()
        print(f"DatabaseManager initialized for database at {self.db_path}. Connections will be thread-local.")

    def _get_connection(self):
        """
        Gets a database connection specific to the current thread.
        If a connection does not exist for the thread, it creates one.
        """
        # Check if a connection is already stored for this thread
        if not hasattr(self.thread_local, 'conn'):
            try:
                # No connection for this thread, so create one
                # check_same_thread=False is used here because we *explicitly* manage
                # connections per-thread using threading.local(). This flag
                # prevents SQLite from raising an error when it *thinks* a connection
                # is being used across threads, even though our pattern ensures
                # each thread has its *own* connection object. The safety comes
                # from threading.local, not from this flag.
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.execute("PRAGMA foreign_keys = ON;")
                self.thread_local.conn = conn
                # print(f"Created new SQLite connection for thread {threading.get_ident()}") # Optional: uncomment for debugging
            except sqlite3.Error as e:
                print(f"Error connecting to database in thread {threading.get_ident()}: {e}")
                raise
        return self.thread_local.conn
        

    def are_tables_created(self):
        """
        Checks if the application-specific tables have been created in the database.
        This is useful for determining if the initial setup/schema migration is needed.
        It specifically ignores the internal 'sqlite_sequence' table.

        Returns:
            True if tables like 'Entity', 'Characteristics', etc., exist, False otherwise.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # Check for the existence of one of our key tables.
            # This is more direct than getting a list of all tables.
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Entity';")
            # fetchone() will return a result if the table exists, None otherwise.
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"An error occurred while checking if tables are created: {e}")
            return False

    def has_data(self):
        """
        Checks if there is any data in the core 'Entity' table. This is the correct
        way to check if the database "is empty" in terms of application data.

        Returns:
            True if at least one entity exists, False otherwise.
        """
        # If the tables don't even exist, there's definitely no data.
        if not self.are_tables_created():
            return False
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # This is a very efficient query to check for the existence of any row.
            # It stops and returns as soon as it finds one row.
            cursor.execute("SELECT 1 FROM Entity LIMIT 1;")
            result = cursor.fetchone()
            # fetchone() returns a tuple (e.g., (1,)) if a row is found, and None if the table is empty.
            # bool(result) will be True for a tuple and False for None.
            return bool(result)
        except sqlite3.Error as e:
            print(f"An error occurred while checking for data in the Entity table: {e}")
            return False
            

    def create_tables(self):
        """
        Creates all necessary tables based on the ER diagram.
        This method is idempotent; it won't recreate tables that already exist.
        Safe to call from any thread.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Table for Entities
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Entity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT(65535) NOT NULL,
                    current_characteristics_id INTEGER,
                    creation_time TEXT NOT NULL,
                    edit_time TEXT NOT NULL,
                    last_access TEXT NOT NULL,
                    FOREIGN KEY (current_characteristics_id) REFERENCES Characteristics(id) ON DELETE SET NULL
                );
            ''')

            # Table for Characteristics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Characteristics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER NOT NULL,
                    embeddings_blob BLOB,
                    raw_text TEXT(65535),
                    extracted_at_timestamp TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    FOREIGN KEY (entity_id) REFERENCES Entity(id) ON DELETE CASCADE
                );
            ''')

            # Table for Messages
            # Renamed 'unique_id' to 'source_unique_id' to store the ID from the source system
            # The 'id' column remains the database's internal unique ID (primary key)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_unique_id TEXT(255) UNIQUE NOT NULL, -- The unique ID from the source system
                    timestamp TEXT NOT NULL,
                    source_tag TEXT(65535),
                    type TEXT(65535),
                    raw_json TEXT(65535)
                );
            ''')

            # Junction table for Characteristics and Messages
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Characteristics_Messages (
                    characteristic_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    contribution_timestamp TEXT NOT NULL,
                    contribution_score REAL,
                    PRIMARY KEY (characteristic_id, message_id),
                    FOREIGN KEY (characteristic_id) REFERENCES Characteristics(id) ON DELETE CASCADE,
                    FOREIGN KEY (message_id) REFERENCES message(id) ON DELETE CASCADE
                );
            ''')

            conn.commit()
            print("Tables created successfully (if they didn't already exist).")
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
            conn.rollback()


    def add_entity(self, name, current_characteristics_id=None):
        """
        Adds a new entity to the Entity table. Safe to call from any thread.

        Args:
            name (str): The name of the entity.
            current_characteristics_id (int, optional): The ID of the current characteristics. Defaults to None.

        Returns:
            int: The ID of the newly created entity, or None if an error occurred.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        try:
            sql = '''
                INSERT INTO Entity (name, current_characteristics_id, creation_time, edit_time, last_access)
                VALUES (?, ?, ?, ?, ?)
            '''
            cursor.execute(sql, (name, current_characteristics_id, now, now, now))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding entity: {e}")
            conn.rollback()
            return None


    def add_characteristics(self, entity_id, raw_text, version, embeddings_array=None):
        """
        Adds a new characteristics record. Safe to call from any thread.

        Args:
            entity_id (int): The ID of the parent entity.
            raw_text (str): The raw text associated with the characteristics.
            version (int): The version number of these characteristics.
            embeddings_array (np.ndarray, optional): The numpy array data for embeddings.
                                                     Will be pickled before storage. Defaults to None.

        Returns:
            int: The ID of the new characteristics record, or None on error.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        embeddings_blob = None
        if embeddings_array is not None:
            # Serialize the numpy array into a bytes object using pickle
            embeddings_blob = pickle.dumps(embeddings_array)

        try:
            sql = '''
                INSERT INTO Characteristics (entity_id, embeddings_blob, raw_text, extracted_at_timestamp, version)
                VALUES (?, ?, ?, ?, ?)
            '''
            cursor.execute(sql, (entity_id, embeddings_blob, raw_text, now, version))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding characteristics: {e}")
            conn.rollback()
            return None

    def update_entity_current_characteristics(self, entity_id, characteristic_id):
        """
        Updates an entity's current_characteristics_id field. Safe to call from any thread.

        Args:
            entity_id (int): The ID of the entity to update.
            characteristic_id (int): The ID of the new current characteristic.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        try:
            sql = '''
                UPDATE Entity
                SET current_characteristics_id = ?, edit_time = ?
                WHERE id = ?
            '''
            cursor.execute(sql, (characteristic_id, now, entity_id))
            conn.commit()
            # print(f"Entity {entity_id} updated with characteristic {characteristic_id}.") # Optional: uncomment for logging
        except sqlite3.Error as e:
            print(f"Error updating entity: {e}")
            conn.rollback()


    def add_message(self, source_unique_id: str, source_tag: str, msg_type: str, raw_data_dict: dict):
        """
        Adds a new message to the message table.
        Stores the source system's unique ID in 'source_unique_id' column.
        The database's auto-incremented primary key 'id' is the internal unique ID.
        Safe to call from any thread.

        Args:
            source_unique_id (str): The unique identifier for the message from the source system.
            source_tag (str): A tag indicating the source of the message.
            msg_type (str): The type of the message.
            raw_data_dict (dict): A dictionary to be stored as a JSON string.

        Returns:
            int: The database's primary key (ID) of the new message,
                 or the existing ID if source_unique_id already exists, or None on error.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        raw_json = json.dumps(raw_data_dict)
        try:
            sql = '''
                INSERT INTO message (source_unique_id, timestamp, source_tag, type, raw_json)
                VALUES (?, ?, ?, ?, ?)
            '''
            # Insert the source_unique_id into the correct column
            cursor.execute(sql, (source_unique_id, now, source_tag, msg_type, raw_json))
            conn.commit()
            # Return the database's primary key (internal ID)
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # This will happen if you try to add a message with a source_unique_id that already exists.
            # We handle this by fetching the existing message's internal ID.
            print(f"Warning: Message with source_unique_id '{source_unique_id}' already exists. Fetching existing internal ID.")
            conn.rollback() # Rollback the failed insert
            cursor.execute("SELECT id FROM message WHERE source_unique_id = ?", (source_unique_id,))
            result = cursor.fetchone()
            # Return the existing database's primary key (internal ID)
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Error adding message: {e}")
            conn.rollback()
            return None


    def link_characteristic_to_message(self, characteristic_id, message_id, score):
        """
        Links a characteristic to a message in the junction table. Safe to call from any thread.

        Args:
            characteristic_id (int): The ID of the characteristic.
            message_id (int): The ID of the message (this should be the database's internal ID).
            score (float): The contribution score.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        try:
            sql = '''
                INSERT INTO Characteristics_Messages (characteristic_id, message_id, contribution_timestamp, contribution_score)
                VALUES (?, ?, ?, ?)
            '''
            cursor.execute(sql, (characteristic_id, message_id, now, score))
            conn.commit()
        except sqlite3.IntegrityError:
            # print(f"Link between characteristic {characteristic_id} and message {message_id} already exists.") # Optional: uncomment for logging
             pass # Suppress message if link already exists, as it's not an error
        except sqlite3.Error as e:
            print(f"Error linking characteristic to message: {e}")
            conn.rollback()

    def get_latest_characteristic_version(self, entity_id):
        """
        Gets the latest version number for a given entity's characteristics.
        Safe to call from any thread.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT MAX(version) FROM Characteristics WHERE entity_id = ?", (entity_id,))
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else 0
        except sqlite3.Error as e:
            print(f"Error getting latest characteristic version for entity {entity_id}: {e}")
            return 0

    def get_characteristic_by_id(self, characteristic_id):
        """
        Retrieves a single characteristic record by its ID. Safe to call from any thread.

        Args:
            characteristic_id (int): The ID of the characteristic to retrieve.

        Returns:
            dict: A dictionary containing characteristic data, with embeddings_blob
                  deserialized to a numpy array, or None if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, entity_id, embeddings_blob, raw_text, extracted_at_timestamp, version FROM Characteristics WHERE id = ?", (characteristic_id,))
            row = cursor.fetchone()
            if row:
                char_data = {
                    "id": row[0],
                    "entity_id": row[1],
                    "embeddings": pickle.loads(row[2]) if row[2] else None, # Deserialize blob
                    "raw_text": row[3],
                    "extracted_at_timestamp": row[4],
                    "version": row[5]
                }
                return char_data
            return None
        except sqlite3.Error as e:
            print(f"Error retrieving characteristic by ID {characteristic_id}: {e}")
            return None
        except Exception as e:
            # Catch errors during deserialization (e.g., corrupted data)
            print(f"Error deserializing embedding for characteristic {characteristic_id}: {e}")
            return None


    def get_all_characteristics(self):
        """
        Retrieves all characteristic records. Safe to call from any thread.

        Returns:
            list: A list of dictionaries, each containing characteristic data,
                  with embeddings_blob deserialized to numpy arrays.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, entity_id, embeddings_blob, raw_text, extracted_at_timestamp, version FROM Characteristics")
            rows = cursor.fetchall()
            all_characteristics = []
            for row in rows:
                try:
                    char_data = {
                        "id": row[0],
                        "entity_id": row[1],
                        "embeddings": pickle.loads(row[2]) if row[2] else None, # Deserialize blob
                        "raw_text": row[3],
                        "extracted_at_timestamp": row[4],
                        "version": row[5]
                    }
                    all_characteristics.append(char_data)
                except Exception as e:
                    # Handle potential deserialization errors for individual rows
                    print(f"Warning: Could not deserialize embedding for characteristic ID {row[0]}: {e}. Skipping embeddings for this entry.")
                    char_data = {
                        "id": row[0],
                        "entity_id": row[1],
                        "embeddings": None, # Store as None if deserialization fails
                        "raw_text": row[3],
                        "extracted_at_timestamp": row[4],
                        "version": row[5]
                    }
                    all_characteristics.append(char_data)
            return all_characteristics
        except sqlite3.Error as e:
            print(f"Error retrieving all characteristics: {e}")
            return []


    def get_messages_for_characteristic(self, characteristic_id):
        """
        Retrieves all messages related to a specific characteristic. Safe to call from any thread.

        Args:
            characteristic_id (int): The ID of the characteristic.

        Returns:
            list: A list of dictionaries, each representing a message,
                  or an empty list if no messages are found or an error occurs.
                  Each dictionary includes message details and the contribution score.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            sql = '''
                SELECT
                    m.id,
                    m.source_unique_id,
                    m.timestamp,
                    m.source_tag,
                    m.type,
                    m.raw_json,
                    cm.contribution_score,
                    cm.contribution_timestamp
                FROM
                    message m
                JOIN
                    Characteristics_Messages cm ON m.id = cm.message_id
                WHERE
                    cm.characteristic_id = ?
                ORDER BY
                    m.timestamp ASC;
            '''
            cursor.execute(sql, (characteristic_id,))
            rows = cursor.fetchall()
            messages = []
            for row in rows:
                try:
                    message_data = {
                        "id": row[0],
                        "source_unique_id": row[1],
                        "timestamp": row[2],
                        "source_tag": row[3],
                        "type": row[4],
                        "raw_json": json.loads(row[5]) if row[5] else {}, # Parse raw_json back to dict
                        "contribution_score": row[6],
                        "contribution_timestamp": row[7]
                    }
                    messages.append(message_data)
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not decode raw_json for message ID {row[0]}: {e}. Storing raw_json as string.")
                    # If JSON decoding fails, store raw_json as is (string)
                    message_data = {
                        "id": row[0],
                        "source_unique_id": row[1],
                        "timestamp": row[2],
                        "source_tag": row[3],
                        "type": row[4],
                        "raw_json": row[5], # Keep as string if parsing fails
                        "contribution_score": row[6],
                        "contribution_timestamp": row[7]
                    }
                    messages.append(message_data)
            return messages
        except sqlite3.Error as e:
            print(f"Error retrieving messages for characteristic {characteristic_id}: {e}")
            return []

    def get_messages_for_entity_current_characteristic(self, entity_id: int):
        """
        Retrieves all messages related to the current characteristic of a given entity.
        Safe to call from any thread.

        Args:
            entity_id (int): The ID of the entity.

        Returns:
            list: A list of dictionaries, each representing a message,
                  or an empty list if no current characteristic is set for the entity,
                  no messages are found, or an error occurs.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # 1. Get the current_characteristics_id for the entity
            cursor.execute("SELECT current_characteristics_id FROM Entity WHERE id = ?", (entity_id,))
            result = cursor.fetchone()

            if result and result[0] is not None:
                current_characteristic_id = result[0]
                # 2. Use the retrieved characteristic_id to get messages
                return self.get_messages_for_characteristic(current_characteristic_id)
            else:
                print(f"No current characteristic found for entity ID {entity_id}.")
                return []
        except sqlite3.Error as e:
            print(f"Error retrieving current characteristic for entity {entity_id}: {e}")
            return []



    def get_entity_by_id(self, entity_id: int):
        """
        Retrieves an entity record by its ID. Safe to call from any thread.

        Args:
            entity_id (int): The ID of the entity to retrieve.

        Returns:
            dict: A dictionary containing entity data, or None if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            sql = '''
                SELECT id, name, current_characteristics_id, creation_time, edit_time, last_access
                FROM Entity
                WHERE id = ?
            '''
            cursor.execute(sql, (entity_id,))
            row = cursor.fetchone()
            if row:
                entity_data = {
                    "id": row[0],
                    "name": row[1],
                    "current_characteristics_id": row[2],
                    "creation_time": row[3],
                    "edit_time": row[4],
                    "last_access": row[5]
                }
                return entity_data
            return None
        except sqlite3.Error as e:
            print(f"Error retrieving entity by ID {entity_id}: {e}")
            return None
        
    def close(self):
        """
        Closes the connection for the current thread.
        This should be called when a thread is finished with the database.
        Note: Connections are thread-local, so closing in one thread
        does not affect connections in other threads.
        """
        if hasattr(self.thread_local, 'conn'):
            try:
                self.thread_local.conn.commit() # Commit any pending changes for this thread
                self.thread_local.conn.close()
                del self.thread_local.conn
                # print(f"Closed SQLite connection for thread {threading.get_ident()}") # Optional: uncomment for debugging
            except sqlite3.Error as e:
                 print(f"Error closing database connection for thread {threading.get_ident()}: {e}")


    # Add these methods to your DatabaseManager class

    def get_total_characteristics_count(self):
        """
        Gets the total count of characteristics in the database.
        Used for adaptive threshold calculations.
        Safe to call from any thread.
        
        Returns:
            int: Total number of characteristics, or 0 if error occurs.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM Characteristics")
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            print(f"Error getting total characteristics count: {e}")
            return 0

    def get_total_entities_count(self):
        """
        Gets the total count of entities in the database.
        Safe to call from any thread.
        
        Returns:
            int: Total number of entities, or 0 if error occurs.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM Entity")
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            print(f"Error getting total entities count: {e}")
            return 0

    def get_recent_characteristics(self, limit=50):
        """
        Gets the most recently created characteristics, useful for prioritizing
        recent memories in search results.
        Safe to call from any thread.
        
        Args:
            limit (int): Maximum number of characteristics to return.
            
        Returns:
            list: List of characteristic IDs, ordered by most recent first.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id FROM Characteristics 
                ORDER BY extracted_at_timestamp DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        except sqlite3.Error as e:
            print(f"Error getting recent characteristics: {e}")
            return []

    def get_characteristics_by_entity_ids(self, entity_ids):
        """
        Gets characteristics for specific entities, useful for targeted searches.
        Safe to call from any thread.
        
        Args:
            entity_ids (list): List of entity IDs to get characteristics for.
            
        Returns:
            list: List of dictionaries containing characteristic data.
        """
        if not entity_ids:
            return []
            
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ','.join('?' * len(entity_ids))
            query = f"""
                SELECT id, entity_id, embeddings_blob, raw_text, extracted_at_timestamp, version 
                FROM Characteristics 
                WHERE entity_id IN ({placeholders})
                ORDER BY extracted_at_timestamp DESC
            """
            cursor.execute(query, entity_ids)
            rows = cursor.fetchall()
            
            characteristics = []
            for row in rows:
                try:
                    char_data = {
                        "id": row[0],
                        "entity_id": row[1],
                        "embeddings": pickle.loads(row[2]) if row[2] else None,
                        "raw_text": row[3],
                        "extracted_at_timestamp": row[4],
                        "version": row[5]
                    }
                    characteristics.append(char_data)
                except Exception as e:
                    print(f"Warning: Could not deserialize embedding for characteristic ID {row[0]}: {e}")
                    char_data = {
                        "id": row[0],
                        "entity_id": row[1],
                        "embeddings": None,
                        "raw_text": row[3],
                        "extracted_at_timestamp": row[4],
                        "version": row[5]
                    }
                    characteristics.append(char_data)
            return characteristics
        except sqlite3.Error as e:
            print(f"Error getting characteristics by entity IDs: {e}")
            return []

    def get_entity_names_batch(self, entity_ids):
        """
        Gets entity names for multiple entity IDs in a single query.
        Safe to call from any thread.
        
        Args:
            entity_ids (list): List of entity IDs.
            
        Returns:
            dict: Dictionary mapping entity_id to entity name.
        """
        if not entity_ids:
            return {}
            
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ','.join('?' * len(entity_ids))
            query = f"SELECT id, name FROM Entity WHERE id IN ({placeholders})"
            cursor.execute(query, entity_ids)
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}
        except sqlite3.Error as e:
            print(f"Error getting entity names batch: {e}")
            return {}

    def update_entity_last_access(self, entity_id):
        """
        Updates the last_access timestamp for an entity.
        This can be used to track which entities are being accessed frequently.
        Safe to call from any thread.
        
        Args:
            entity_id (int): The ID of the entity to update.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        try:
            cursor.execute("UPDATE Entity SET last_access = ? WHERE id = ?", (now, entity_id))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error updating entity last access for ID {entity_id}: {e}")
            conn.rollback()

    def get_characteristics_with_entity_names(self, limit=None):
        """
        Gets characteristics along with their entity names in a single query.
        More efficient than separate queries when you need both.
        Safe to call from any thread.
        
        Args:
            limit (int, optional): Maximum number of results to return.
            
        Returns:
            list: List of dictionaries containing characteristic and entity data.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT c.id, c.entity_id, c.embeddings_blob, c.raw_text, 
                    c.extracted_at_timestamp, c.version, e.name as entity_name
                FROM Characteristics c
                JOIN Entity e ON c.entity_id = e.id
                ORDER BY c.extracted_at_timestamp DESC
            """
            if limit:
                query += f" LIMIT {limit}"
                
            cursor.execute(query)
            rows = cursor.fetchall()
            
            characteristics = []
            for row in rows:
                try:
                    char_data = {
                        "id": row[0],
                        "entity_id": row[1],
                        "embeddings": pickle.loads(row[2]) if row[2] else None,
                        "raw_text": row[3],
                        "extracted_at_timestamp": row[4],
                        "version": row[5],
                        "entity_name": row[6]
                    }
                    characteristics.append(char_data)
                except Exception as e:
                    print(f"Warning: Could not deserialize embedding for characteristic ID {row[0]}: {e}")
                    char_data = {
                        "id": row[0],
                        "entity_id": row[1],
                        "embeddings": None,
                        "raw_text": row[3],
                        "extracted_at_timestamp": row[4],
                        "version": row[5],
                        "entity_name": row[6]
                    }
                    characteristics.append(char_data)
            return characteristics
        except sqlite3.Error as e:
            print(f"Error getting characteristics with entity names: {e}")
            return []