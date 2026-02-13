
# services/book_service.py
# This is more of a tool than an item state service, but it was here before everything else
import copy

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

    def _validate_book_location(self, book_item_id: int, level="inventory")->bool:
        "2 levels, inventory and dual (room and inventory)"
        current_room_id = self._state_store.get_state_section("current_room_id")
        item_info = self._inventory_service._find_item_info_by_id(book_item_id)
        if not item_info:
            return False
        item_loc_id=item_info["location_id"]
        item_location = item_info["location"]
        if level == "inventory":
            return item_location == "inventory"
        elif level == "dual":
            return item_location == "inventory" or (item_location == "room" and item_loc_id == current_room_id)
        return False

    def _validate_book_locked(self, book_item_id: int)->bool:
        item_info = self._inventory_service._find_item_info_by_id(book_item_id)
        print(f"Book item {book_item_id} info: {item_info}")
        if not item_info:
            print(f"Error: Book item {book_item_id} not found.")
            return False
            
        # The 'is_locked' key is inside the 'item_data' dictionary
        item_data = item_info.get("item_data", {}) 
        
        # Check if item_data exists and has the 'is_locked' key
        if 'is_locked' not in item_data:
            print(f"Error: 'is_locked' key not found in item_data for book {book_item_id}")
            return False # Or raise an appropriate error
            
        is_locked_status = item_data["is_locked"]
        
        print(f"Book item {book_item_id} is locked: {is_locked_status}")
        return is_locked_status

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
            'chapters': [],
            'is_locked': False
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
        book_data, error_msg = self._inventory_service.get_validated_item_data(book_item_id, required_type="book")
        if error_msg: return f"Error: {error_msg}"

        # Check accessibility (moved from InventoryHouseManager)
        is_accessible = self._validate_book_location(book_item_id, "inventory")
        if not is_accessible:
            item_display = self._inventory_service._format_item_for_display(book_data)
            return f"You can only examine items in your inventory. Item {item_display} is not here."

        chapters = book_data.get("chapters", [])
        if not chapters:
            return f"The book '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id}) has no chapters."
        chapter_titles = [f"- '{chap.get('title', 'Untitled Chapter')}'" for chap in chapters if isinstance(chap, dict)]
        return f"Chapters in '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id}):\n" + "\n".join(chapter_titles)

    def read_book_chapter(self, book_item_id: int, chapter_title: str) -> str:
        book_data, error_msg = self._inventory_service.get_validated_item_data(book_item_id, required_type="book")
        if error_msg: return f"Error: {error_msg}"

        # Check accessibility
        is_accessible = self._validate_book_location(book_item_id, "inventory")
        if not is_accessible:
            item_display = self._inventory_service._format_item_for_display(book_data)
            return f"You can only read books in your inventory. Item {item_display} is not here."

        chapters = book_data.get("chapters", [])
        target_chapter = next((c for c in chapters if c.get("title", "").lower() == chapter_title.lower()), None)

        if target_chapter:
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png"})
            return f"--- Chapter: {target_chapter.get('title', 'Untitled')} ---\n{target_chapter.get('content', 'No content.')}"
        else:
            return f"Chapter '{chapter_title}' not found in '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id})."

    def add_book_chapter(self, book_item_id: int, chapter_title: str, content: str) -> str:

        book_data, error_msg = self._inventory_service.get_validated_item_data(book_item_id, required_type="book")
        if error_msg: return f"Error: {error_msg}"

        # Check accessibility
        is_accessible = self._validate_book_location(book_item_id, "inventory")
        if not is_accessible:
            item_display = self._inventory_service._format_item_for_display(book_data)
            return f"You can only add chapters to books in your inventory. Item {item_display} is not here."

        is_locked = self._validate_book_locked(book_item_id)
        if is_locked:
            item_display = self._inventory_service._format_item_for_display(book_data)
            return f"Item {item_display} is locked. Cannot add chapters."

        if not isinstance(chapter_title, str) or not chapter_title.strip():
            return "Error: Chapter title cannot be empty."
        if not isinstance(content, str) or not content.strip():
            return "Error: Chapter content cannot be empty."


        chapters = copy.deepcopy(book_data.get("chapters", []))  # not the live reference
        if any(c.get("title", "").lower() == chapter_title.lower() for c in chapters):
            return f"Error: Chapter with title '{chapter_title}' already exists in '{book_data.get('name', 'Unnamed Book')}'."

        chapters.append({"title": chapter_title.strip(), "content": content})
        # book_data["chapters"] = chapters # Ensure the list is updated in the dict # TODO: DIRECT MODIFICATION OF STATE

        # # Now, you need to persist this change to the overall state
        # persist_error = self._inventory_service.persist_item_changes(book_item_id)
        # if persist_error:
        #     return persist_error

        self._inventory_service.set_item_attribute(book_item_id, "chapters", chapters)

        

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png", "popup_type": 2})
        return f"Chapter '{chapter_title}' successfully added to '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id})."


    def update_book_chapter(self, book_item_id: int, chapter_title: str, new_content: str, operation: str = "append") -> str:
        # Check accessibility
        book_data, error_msg = self._inventory_service.get_validated_item_data(book_item_id, required_type="book")
        if error_msg: return f"Error: {error_msg}"

        is_accessible = self._validate_book_location(book_item_id, "inventory")
        if not is_accessible:
            item_display = self._inventory_service._format_item_for_display(book_data)
            return f"You can only update chapters of books in your inventory. Item {item_display} is not here."

        is_locked = self._validate_book_locked(book_item_id)
        if is_locked:
            item_display = self._inventory_service._format_item_for_display(book_data)
            return f"Item {item_display} is locked. Cannot update chapters."

        if not isinstance(new_content, str) or not new_content.strip():
            return "Error: New chapter content cannot be empty."

        chapters_clone = copy.deepcopy(book_data.get("chapters", []))
        target_chapter = next((c for c in chapters_clone if c.get("title", "").lower() == chapter_title.lower()), None)

        if target_chapter:
            if operation == "append":
                target_chapter["content"] += "\n" + new_content.strip()
            elif operation == "replace":
             target_chapter["content"] = new_content.strip()

            self._inventory_service.set_item_attribute(book_item_id, "chapters", chapters_clone)

            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png"})
            return f"Chapter '{chapter_title}' in '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id}) successfully updated."
        else:
            return f"Chapter '{chapter_title}' not found in '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id})."

    def delete_book_chapter(self, book_item_id: int, chapter_title: str) -> str:

        book_data, error_msg = self._inventory_service.get_validated_item_data(book_item_id, required_type="book")
        if error_msg: return f"Error: {error_msg}"

        # Check accessibility
        is_accessible = self._validate_book_location(book_item_id, "inventory")
        if not is_accessible:
            item_display = self._inventory_service._format_item_for_display(book_data)
            return f"You can only delete chapters of books in your inventory. Item {item_display} is not here."

        is_locked = self._validate_book_locked(book_item_id)
        if is_locked:
            item_display = self._inventory_service._format_item_for_display(book_data)
            return f"Item {item_display} is locked. Cannot delete chapters."

        chapters = book_data.get("chapters", [])
        original_chapter_count = len(chapters)
        updated_chapters = [c for c in chapters if c.get("title", "").lower() != chapter_title.lower()]

        if len(updated_chapters) < original_chapter_count:
            # book_data["chapters"] = updated_chapters
            self._inventory_service.set_item_attribute(book_item_id, "chapters", updated_chapters)

            # persist_error = self._inventory_service.persist_item_changes(book_item_id)
            # if persist_error:
            #     return persist_error

            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png"})
            return f"Chapter '{chapter_title}' successfully deleted from '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id})."
        else:
            return f"Chapter '{chapter_title}' not found in '{book_data.get('name', 'Unnamed Book')}' (ID:{book_item_id})."

