# book_component.py
# Contains book-specific item logic, designed to be used by InventoryHouseManager.


class BookComponent:
    """
    Handles operations specific to items of type 'book'.
    Designed to be composed within an InventoryHouseManager instance.
    """
    def __init__(self, manager_instance):
        """
        Initializes the BookComponent with a reference to the main manager.

        Args:
            manager_instance: An instance of InventoryHouseManager. This component
                              requires access to manager's state and helper methods.
        """
        # Store a reference to the main manager instance
        # This allows the component to access the state and core methods
        self._manager = manager_instance

        # Optional: Perform checks to ensure manager_instance has expected methods/attributes
        if not hasattr(self._manager, '_find_item_info_by_id') or not callable(self._manager._find_item_info_by_id):
             raise TypeError("Manager instance does not have required '_find_item_info_by_id' method.")
        if not hasattr(self._manager, '_is_valid_item_data') or not callable(self._manager._is_valid_item_data):
             raise TypeError("Manager instance does not have required '_is_valid_item_data' method.")
        if not hasattr(self._manager, '_write_json') or not callable(self._manager._write_json):
             raise TypeError("Manager instance does not have required '_write_json' method.")
        if not hasattr(self._manager, '_format_item_for_display') or not callable(self._manager._format_item_for_display):
             raise TypeError("Manager instance does not have required '_format_item_for_display' method.")
        # Check for _state attribute (accessing state directly)
        if not hasattr(self._manager, '_state') or not isinstance(self._manager._state, dict):
             # This check is less about type safety and more about expected structure
             print("Warning: Manager instance does not have expected '_state' dictionary attribute.")
             # Depending on how critical direct state access is in the component, might raise error


    def _get_book_item_internal(self, book_item_id: int):
        """
        Internal helper to find an item by ID and verify it is a book,
        using the main manager's methods.
        """
        # Use the manager's method to find the item
        item_info = self._manager._find_item_info_by_id(book_item_id)
        if not item_info:
             return None, f"Item with ID '{book_item_id}' not found anywhere."

        item_data = item_info["item_data"]
        # Use the manager's validation method, which knows about book type
        is_valid, msg = self._manager._is_valid_item_data(item_data, check_id=True)

        if not is_valid:
             # Item found, but its data structure is invalid according to the manager's rules
             print(f"Warning: Item ID {book_item_id} found but data is invalid ({msg}). Treated as non-book or corrupted.")
             return None, f"Item with ID '{book_item_id}' ({item_data.get('name', 'Unnamed Item')}) data is corrupted: {msg}"

        # After validation, check if the validated item is actually a book type
        if item_data.get("type") != "book":
             return None, f"Item with ID '{book_item_id}' ({item_data.get('name', 'Unnamed Item')}) is not a book (type is '{item_data.get('type')}')."


        # Return the item data dictionary itself (a reference from the main state)
        return item_data, None


    def list_chapters(self, book_item_id: int) -> str:
        """
        Lists all chapter titles of a book item using its ID.
        Called by the main InventoryHouseManager.
        """
        # Use the internal helper
        book_item, error_msg = self._get_book_item_internal(book_item_id)

        if error_msg:
             return f"Failed to list chapters: {error_msg}"

        # Book item is valid and is a book, access chapters list
        # Use .get with default [] for safety, though validation should catch missing key
        chapters_list = book_item.get("chapters", [])

        # Ensure chapters_list is actually a list (should be true if _get_book_item_internal validated)
        if not isinstance(chapters_list, list):
             # This indicates a validation gap or deeper corruption
             print(f"Error: Chapters key for book ID {book_item_id} is not a list in list_chapters after validation.")
             return f"Error: Chapter data for book {self._manager._format_item_for_display(book_item)} is corrupted."


        # Get chapter titles, robustly checking each entry is a dict and has a title key
        chapter_titles = [
             chapter.get('title', 'Untitled Chapter') for chapter in chapters_list
             if isinstance(chapter, dict) and isinstance(chapter.get('title'), str) # Robust check
        ]

        # Use manager's formatter for consistent display
        book_display = self._manager._format_item_for_display(book_item)

        if not chapter_titles:
            return f"No chapters found in {book_display}."

        joined_chapters = ", ".join(chapter_titles)
        message = f"Chapters available in {book_display}: {joined_chapters}"
        return message


    def read_chapter(self, book_item_id: int, chapter_title: str) -> str:
        """
        Reads the content of a specific chapter from a book item using its ID.
        Called by the main InventoryHouseManager.
        """
        if not isinstance(book_item_id, int):
             return f"Failed to read chapter: Book item ID must be an integer, received '{book_item_id}' ({type(book_item_id).__name__})."

        # Use the internal helper
        book_item, error_msg = self._get_book_item_internal(book_item_id)

        if error_msg:
             return f"Failed to read chapter: {error_msg}"

        # Book item is valid and is a book, access chapters list
        chapters_list = book_item.get("chapters", [])
        if not isinstance(chapters_list, list):
             print(f"Error: Chapters key for book ID {book_item_id} is not a list in read_chapter after validation.")
             return f"Error: Chapter data for book {self._manager._format_item_for_display(book_item)} is corrupted."


        chapter_title_lower = str(chapter_title).strip().lower()
        book_display = self._manager._format_item_for_display(book_item)

        # Find the chapter (case-insensitive title match), robustly checking each entry
        for chapter in chapters_list:
             if isinstance(chapter, dict) and isinstance(chapter.get('title'), str) and chapter['title'].strip().lower() == chapter_title_lower:
                  content = chapter.get('content', 'No content available.') # Get content, default if missing
                  if not isinstance(content, str): # Ensure content is a string
                      print(f"Warning: Content for chapter '{chapter_title}' in book ID {book_item_id} is not a string ({type(content).__name__}).")
                      content = 'Content data corrupted.' # Provide a fallback string
                  return f"Content of '{chapter.get('title', 'Untitled Chapter')}' in {book_display}:\n{content}" # Return stored title case
        chapters=self.list_chapters(book_item_id)
        return f"Chapter '{chapter_title}' not found in {book_display}. {chapters} "


    def add_chapter(self, book_item_id: int, chapter_title: str, content: str) -> str:
        """
        Adds a new chapter to a book item using its ID.
        Called by the main InventoryHouseManager.
        Modifies state via the manager's _write_json method.
        """
        if not isinstance(book_item_id, int):
             return f"Failed to add chapter: Book item ID must be an integer, received '{book_item_id}' ({type(book_item_id).__name__})."

        book_item, error_msg = self._get_book_item_internal(book_item_id)

        if error_msg:
             return f"Failed to add chapter: {error_msg}"

        # Book item is valid and is a book, access chapters list
        chapters_list = book_item.get("chapters", [])
        if not isinstance(chapters_list, list):
             print(f"Error: Chapters key for book ID {book_item_id} is not a list in add_chapter after validation. Attempting to fix.")
             book_item["chapters"] = [] # Attempt to fix state by resetting chapter list
             chapters_list = book_item["chapters"]
             # Note: A save will happen later, so this correction is persisted if the add succeeds.

        chapter_title_clean = str(chapter_title).strip() # Keep original case for storage
        chapter_title_lower = chapter_title_clean.lower()
        content_str = str(content) # Ensure content is string

        book_display = self._manager._format_item_for_display(book_item)

        # Check if the chapter already exists (case-insensitive title check)
        if any(isinstance(chapter, dict) and isinstance(chapter.get('title'), str) and chapter['title'].strip().lower() == chapter_title_lower for chapter in chapters_list):
            return f"Chapter '{chapter_title_clean}' already exists in {book_display}."

        # Add the new chapter
        new_chapter = {
            "title": chapter_title_clean, # Store cleaned title
            "content": content_str # Store content as string
        }

        chapters_list.append(new_chapter) # Append to the list reference within the state

        # Use the manager's method to save the modified state
        self._manager._write_json(self._manager._state) # Pass the manager's state to its writer

        return f"Chapter '{chapter_title_clean}' added to {book_display} successfully."


    def update_chapter(self, book_item_id: int, chapter_title: str, new_content: str) -> str:
        """
        Updates the content of a chapter in a book item using its ID.
        Called by the main InventoryHouseManager.
        Modifies state via the manager's _write_json method.
        """
        if not isinstance(book_item_id, int):
             return f"Failed to update chapter: Book item ID must be an integer, received '{book_item_id}' ({type(book_item_id).__name__})."

        book_item, error_msg = self._get_book_item_internal(book_item_id)

        if error_msg:
             return f"Failed to update chapter: {error_msg}"

        # Book item is valid and is a book, access chapters list
        chapters_list = book_item.get("chapters", [])
        if not isinstance(chapters_list, list):
             print(f"Error: Chapters key for book ID {book_item_id} is not a list in update_chapter after validation. Attempting to fix.")
             book_item["chapters"] = [] # Attempt to fix state
             chapters_list = book_item["chapters"]
             # Note: A save will happen later.


        chapter_title_lower = str(chapter_title).strip().lower()
        new_content_str = str(new_content) # Ensure content is string
        book_display = self._manager._format_item_for_display(book_item)


        # Find the chapter to update (case-insensitive title match), robustly checking each entry
        for chapter in chapters_list:
             if isinstance(chapter, dict) and isinstance(chapter.get('title'), str) and chapter['title'].strip().lower() == chapter_title_lower:
                  chapter['content'] = new_content_str # Update content
                  # Use the manager's method to save the modified state
                  self._manager._write_json(self._manager._state) # Pass the manager's state
                  # Return the stored title case
                  return f"Chapter '{chapter.get('title', 'Untitled Chapter')}' in {book_display} updated successfully."

        return f"Chapter '{chapter_title}' not found in {book_display}."


    def delete_chapter(self, book_item_id: int, chapter_title: str) -> str:
        """
        Deletes a chapter from a book item using its ID.
        Called by the main InventoryHouseManager.
        Modifies state via the manager's _write_json method.
        """
        if not isinstance(book_item_id, int):
             return f"Failed to delete chapter: Book item ID must be an integer, received '{book_item_id}' ({type(book_item_id).__name__})."

        book_item, error_msg = self._get_book_item_internal(book_item_id)

        if error_msg:
             return f"Failed to delete chapter: {error_msg}"

        # Book item is valid and is a book, access chapters list
        chapters_list = book_item.get("chapters", [])
        if not isinstance(chapters_list, list):
             print(f"Error: Chapters key for book ID {book_item_id} is not a list in delete_chapter after validation. Attempting to fix.")
             book_item["chapters"] = [] # Attempt to fix state
             chapters_list = book_item["chapters"]
             needs_save = True # Need to save correction if successful later


        chapter_title_lower = str(chapter_title).strip().lower()
        book_display = self._manager._format_item_for_display(book_item)

        # Find the chapter to delete (case-insensitive title match)
        original_chapter_count = len(chapters_list)

        # Create a new list excluding the chapter to delete
        # Ensure chapter entry is a dict and has a title key for safety during filtering.
        # Modify the list directly in the book_item dictionary
        book_item["chapters"] = [
             chapter for chapter in chapters_list
             if not (isinstance(chapter, dict) and isinstance(chapter.get('title'), str) and chapter['title'].strip().lower() == chapter_title_lower)
        ]

        if len(book_item["chapters"]) < original_chapter_count:
            # Use the manager's method to save the modified state
            self._manager._write_json(self._manager._state) # Pass the manager's state
            return f"Chapter '{chapter_title}' deleted from {book_display} successfully."
        else:
            return f"Chapter '{chapter_title}' not found in {book_display}."

    def list_inventory_books(self, internal=False) -> str:
        """
        Lists all book items currently in the player's inventory by name and ID.
        Called by the main InventoryHouseManager.
        Requires direct access to the inventory list.
        """
        # Access the inventory list directly from the manager's state
        inventory_list = self._manager._state.get("inventory")

        if not isinstance(inventory_list, list):
             # This should ideally be caught by manager validation, but handle defensively
             print(f"Error: Inventory list in manager state is not a list ({type(inventory_list).__name__}) in list_inventory_books.")
             return "Error: Could not access inventory to list books. State might be corrupted."

        # Filter inventory items to find those of type "book"
        # Robust checks for dict type, 'type' key, and 'id' key
        book_items_in_inventory = [
            item for item in inventory_list
            if isinstance(item, dict) and item.get("type") == "book" and item.get("id") is not None and isinstance(item.get("id"), int)
        ]

        # Use manager's formatter for display
        book_display_list = [self._manager._format_item_for_display(item) for item in book_items_in_inventory]

        if book_display_list:
            if internal:
                 return True
            return f"Books in your inventory: {', '.join(book_display_list)}"
        else:
            # Check if inventory has other items, if so, specify no *books*
            if len(inventory_list) > 0:
                 if internal:
                      return False
                 return "You have items in your inventory, but no books."
            else:
                 return "Your inventory is empty."