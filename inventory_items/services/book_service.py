
# services/book_service.py

class BookService:
    def __init__(self, state_store, signal_callback):
        self._state_store = state_store
        self._signal_callback = signal_callback
        self._inventory_service = None # Dependency for creating/finding items

    def set_inventory_service(self, inventory_service_instance):
        """Sets the InventoryService dependency."""
        self._inventory_service = inventory_service_instance

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal: {e}")

    # Helper method to find a book item's actual data from state
    # This assumes find_item_info_by_id from InventoryService is reliable
    def _get_book_data_from_id(self, book_item_id):
        if not self._inventory_service:
            print("Error: InventoryService not set in BookService.")
            return None, "InventoryService not available."

        item_info = self._inventory_service._find_item_info_by_id(book_item_id)
        if not item_info:
            return None, f"No item found with ID '{book_item_id}'."

        item_data = item_info["item_data"]
        is_valid_book, validation_msg = self._inventory_service._is_valid_item_data(item_data, check_id=True)

        if not is_valid_book or "book" not in item_data.get("type", []):
            if "book" not in item_data.get("type", []):
                return None, f"Item with ID '{book_item_id}' ('{item_data.get('name', 'Unnamed')}') is not a book. Found types: {item_data.get('type', [])}."
            else:
                return None, f"Item with ID '{book_item_id}' found but data is corrupted: {validation_msg}"
        return item_data, None # Return data and no error message

    def create_book_item(self, book_name: str, description: str) -> str:
        if not isinstance(book_name, str) or not book_name.strip():
            return "Error: Book name must be a non-empty string."
        if not isinstance(description, str) or not description.strip():
            return "Error: Book description must be a non-empty string."
        if not self._inventory_service:
            return "Error: InventoryService not available to create book items."

        book_data = {
            'name': book_name.strip(),
            'descriptions': [description.strip()],
            'static': False,
            'type': ['book'],
            'chapters': []
        }
        message = self._inventory_service.create_item("inventory", None, book_data)
        message += "\nBook name: " + book_name
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png", "popup_type": 2})
        return message

    def list_inventory_books(self, internal=False) -> str | list[dict]:
        if not self._inventory_service:
            return "Error: InventoryService not available."

        inventory_items = self._inventory_service.get_inventory_items(internal=True)
        if not isinstance(inventory_items, list):
            return "Error: Could not retrieve inventory items."

        books = [
            item for item in inventory_items
            if isinstance(item, dict) and "book" in item.get("type", []) and self._inventory_service._is_valid_item_data(item, check_id=True)[0]
        ]

        if internal:
            return books
        else:
            if not books:
                return "You do not have any books in your inventory."
            book_lines = []
            for book in books:
                book_lines.append(self._inventory_service._format_item_for_display(book))
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png"})
            return "Your books:\n" + "\n".join(book_lines)

    def list_book_chapters(self, book_item_id: int) -> str:
        book_data, error_msg = self._get_book_data_from_id(book_item_id)
        if error_msg: return f"Error: {error_msg}"

        # Check accessibility (moved from InventoryHouseManager)
        item_info = self._inventory_service._find_item_info_by_id(book_item_id)
        current_room_id = self._state_store.get_state_section("current_room_id")
        is_accessible = (item_info["location"] == "inventory") or (item_info["location"] == "room" and item_info["location_id"] == current_room_id)
        if not is_accessible:
            item_display = self._inventory_service._format_item_for_display(book_data)
            return f"You can only examine items in your current location or inventory. Item {item_display} is not here."

        chapters = book_data.get("chapters", [])
        if not chapters:
            return f"The book '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id}) has no chapters."
        chapter_titles = [f"- '{chap.get('title', 'Untitled Chapter')}'" for chap in chapters if isinstance(chap, dict)]
        return f"Chapters in '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id}):\n" + "\n".join(chapter_titles)

    def read_book_chapter(self, book_item_id: int, chapter_title: str) -> str:
        book_data, error_msg = self._get_book_data_from_id(book_item_id)
        if error_msg: return f"Error: {error_msg}"

        # Check accessibility
        item_info = self._inventory_service._find_item_info_by_id(book_item_id)
        current_room_id = self._state_store.get_state_section("current_room_id")
        is_accessible = (item_info["location"] == "inventory") or (item_info["location"] == "room" and item_info["location_id"] == current_room_id)
        if not is_accessible:
            item_display = self._inventory_service._format_item_for_display(book_data)
            return f"You can only read books in your current location or inventory. Item {item_display} is not here."

        chapters = book_data.get("chapters", [])
        target_chapter = next((c for c in chapters if c.get("title", "").lower() == chapter_title.lower()), None)

        if target_chapter:
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png"})
            return f"--- Chapter: {target_chapter.get('title', 'Untitled')} ---\n{target_chapter.get('content', 'No content.')}"
        else:
            return f"Chapter '{chapter_title}' not found in '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id})."

    def add_book_chapter(self, book_item_id: int, chapter_title: str, content: str) -> str:
        if not isinstance(chapter_title, str) or not chapter_title.strip():
            return "Error: Chapter title cannot be empty."
        if not isinstance(content, str) or not content.strip():
            return "Error: Chapter content cannot be empty."

        book_data, error_msg = self._get_book_data_from_id(book_item_id)
        if error_msg: return f"Error: {error_msg}"

        chapters = book_data.get("chapters", [])
        if any(c.get("title", "").lower() == chapter_title.lower() for c in chapters):
            return f"Error: Chapter with title '{chapter_title}' already exists in '{book_data.get('name', 'Unnamed Book')}'."

        chapters.append({"title": chapter_title.strip(), "content": content})
        book_data["chapters"] = chapters # Ensure the list is updated in the dict

        # Now, you need to persist this change to the overall state
        # Find the item in its original location and update it
        item_info = self._inventory_service._find_item_info_by_id(book_item_id)
        if item_info and item_info["location"] == "inventory":
            inventory_list = self._state_store.get_state_section("inventory", [])
            # Update the item directly in the list (since book_data is a reference)
            self._state_store.update_state_section("inventory", inventory_list)
        elif item_info and item_info["location"] == "room":
            rooms_list = self._state_store.get_state_section("rooms", [])
            # The direct modification of book_data (which is inside rooms_list) should reflect
            self._state_store.update_state_section("rooms", rooms_list)
        else:
            return f"Error: Book with ID {book_item_id} moved or is in an unmanageable location after lookup."

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png", "popup_type": 2})
        return f"Chapter '{chapter_title}' successfully added to '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id})."


    def update_book_chapter(self, book_item_id: int, chapter_title: str, new_content: str, operation: str = "append") -> str:
        if not isinstance(new_content, str) or not new_content.strip():
            return "Error: New chapter content cannot be empty."

        book_data, error_msg = self._get_book_data_from_id(book_item_id)
        if error_msg: return f"Error: {error_msg}"

        chapters = book_data.get("chapters", [])
        target_chapter = next((c for c in chapters if c.get("title", "").lower() == chapter_title.lower()), None)

        if target_chapter:
            if operation == "append":
                target_chapter["content"] += "\n" + new_content.strip()
            elif operation == "replace":
             target_chapter["content"] = new_content.strip()

            item_info = self._inventory_service._find_item_info_by_id(book_item_id)
            if item_info and item_info["location"] == "inventory":
                inventory_list = self._state_store.get_state_section("inventory", [])
                self._state_store.update_state_section("inventory", inventory_list)
            elif item_info and item_info["location"] == "room":
                rooms_list = self._state_store.get_state_section("rooms", [])
                self._state_store.update_state_section("rooms", rooms_list)
            else:
                return f"Error: Book with ID {book_item_id} moved or is in an unmanageable location after lookup."

            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png"})
            return f"Chapter '{chapter_title}' in '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id}) successfully updated."
        else:
            return f"Chapter '{chapter_title}' not found in '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id})."

    def delete_book_chapter(self, book_item_id: int, chapter_title: str) -> str:
        book_data, error_msg = self._get_book_data_from_id(book_item_id)
        if error_msg: return f"Error: {error_msg}"

        chapters = book_data.get("chapters", [])
        original_chapter_count = len(chapters)
        updated_chapters = [c for c in chapters if c.get("title", "").lower() != chapter_title.lower()]

        if len(updated_chapters) < original_chapter_count:
            book_data["chapters"] = updated_chapters

            item_info = self._inventory_service._find_item_info_by_id(book_item_id)
            if item_info and item_info["location"] == "inventory":
                inventory_list = self._state_store.get_state_section("inventory", [])
                self._state_store.update_state_section("inventory", inventory_list)
            elif item_info and item_info["location"] == "room":
                rooms_list = self._state_store.get_state_section("rooms", [])
                self._state_store.update_state_section("rooms", rooms_list)
            else:
                return f"Error: Book with ID {book_item_id} moved or is in an unmanageable location after lookup."

            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png"})
            return f"Chapter '{chapter_title}' successfully deleted from '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id})."
        else:
            return f"Chapter '{chapter_title}' not found in '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id})."

