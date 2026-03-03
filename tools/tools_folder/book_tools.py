# tools_folder/book_tools.py
# This is more of a tool than an item state service, but it was here before everything else.
# Now follows the same pattern as other tool classes: receives state_manager directly,
# accesses state only through the public facade, no private member access.
import copy

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager

from inventory_items.item_pydantic_models import validate_item_dict

class BookTools:
    def __init__(self, state_manager, signal_callback):
        self.state_manager: InventoryHouseManager = state_manager
        self._signal_callback = signal_callback

    # NOTE: set_inventory_service() has been removed.
    # BookService no longer holds a reference to inventory_service as a peer dependency.
    # All state access goes through state_manager (the public facade), same as every other tool.

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from BookService: {e}")

    # ------------------------------------------------------------------
    # Internal helpers — no private access, use find_item() result data
    # ------------------------------------------------------------------

    def _item_display(self, item_data: dict, item_id: int) -> str:
        """Inline display string for error messages. Replaces _format_item_for_display()."""
        name = item_data.get("name", "Unknown")
        return f"'{name}' (ID: {item_id})"

    def _fetch_book(self, book_item_id: int) -> tuple[dict | None, str | None]:
        """
        Fetches book item data via the public facade.
        Returns (item_data, error_message). Mirrors the old get_validated_item_data() pattern
        but goes through state_manager instead of touching inventory_service directly.
        """
        result = self.state_manager.find_item(
            book_item_id,
            required_type="book",
            required_location="inventory",
        )
        if not result.success:
            return None, result.error
        return result.item_data, None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_book_item(self, book_name: str, description: str) -> str:
        if not isinstance(book_name, str) or not book_name.strip():
            return "Error: Book name must be a non-empty string."
        if not isinstance(description, str) or not description.strip():
            return "Error: Book description must be a non-empty string."

        book_data = {
            "name": book_name.strip(),
            "descriptions": [description.strip()],
            "static": False,
            "type": ["book"],
            "chapters": [],
            "is_locked": False,
        }
        validated_book_data, error = validate_item_dict(book_data)
        if error:
            return f"Error validating book data: {error}"
        result = self.state_manager.create_item(target_location="inventory", target_location_id=None, item_creation_data=validated_book_data)
        self._send_signal({
            "type": "show_icon_popup",
            "icon_path": "style/images/action_icons/book_icon.png",
            "popup_type": 2,
        })
        if not result.success:
            return f"Error creating book: {result.error}"
        return f"{result.message}\nBook name: {book_name}"

    def list_book_chapters(self, book_item_id: int) -> str:
        book_data, error_msg = self._fetch_book(book_item_id)
        if error_msg:
            return f"Error: {error_msg}"

        chapters = book_data.get("chapters", [])
        if not chapters:
            return f"The book {self._item_display(book_data, book_item_id)} has no chapters."

        chapter_titles = [
            f"- '{chap.get('title', 'Untitled Chapter')}'"
            for chap in chapters
            if isinstance(chap, dict)
        ]
        return f"Chapters in {self._item_display(book_data, book_item_id)}:\n" + "\n".join(chapter_titles)

    def read_book_chapter(self, book_item_id: int, chapter_title: str) -> str:
        book_data, error_msg = self._fetch_book(book_item_id)
        if error_msg:
            return f"Error: {error_msg}"

        chapters = book_data.get("chapters", [])
        target_chapter = next(
            (c for c in chapters if c.get("title", "").lower() == chapter_title.lower()), None
        )
        if not target_chapter:
            return f"Chapter '{chapter_title}' not found in {self._item_display(book_data, book_item_id)}."

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png"})
        return f"--- Chapter: {target_chapter.get('title', 'Untitled')} ---\n{target_chapter.get('content', 'No content.')}"

    def add_book_chapter(self, book_item_id: int, chapter_title: str, content: str) -> str:
        book_data, error_msg = self._fetch_book(book_item_id)
        if error_msg:
            return f"Error: {error_msg}"

        if book_data.get("is_locked"):
            return f"{self._item_display(book_data, book_item_id)} is locked. Cannot add chapters."

        if not isinstance(chapter_title, str) or not chapter_title.strip():
            return "Error: Chapter title cannot be empty."
        if not isinstance(content, str) or not content.strip():
            return "Error: Chapter content cannot be empty."

        chapters = copy.deepcopy(book_data.get("chapters", []))
        if any(c.get("title", "").lower() == chapter_title.lower() for c in chapters):
            return (
                f"Error: Chapter '{chapter_title}' already exists in "
                f"{self._item_display(book_data, book_item_id)}."
            )

        chapters.append({"title": chapter_title.strip(), "content": content})
        attr_result = self.state_manager.set_item_attribute(book_item_id, "chapters", chapters)
        if not attr_result.success:
            return f"Error saving chapter: {attr_result.message}"

        self._send_signal({
            "type": "show_icon_popup",
            "icon_path": "style/images/action_icons/book_icon.png",
            "popup_type": 2,
        })
        return f"Chapter '{chapter_title}' successfully added to {self._item_display(book_data, book_item_id)}."

    def update_book_chapter(
        self, book_item_id: int, chapter_title: str, new_content: str, operation: str = "append"
    ) -> str:
        book_data, error_msg = self._fetch_book(book_item_id)
        if error_msg:
            return f"Error: {error_msg}"

        if book_data.get("is_locked"):
            return f"{self._item_display(book_data, book_item_id)} is locked. Cannot update chapters."

        if not isinstance(new_content, str) or not new_content.strip():
            return "Error: New chapter content cannot be empty."

        if operation not in ("append", "replace"):
            return f"Error: Unknown operation '{operation}'. Use 'append' or 'replace'."

        chapters_clone = copy.deepcopy(book_data.get("chapters", []))
        target_chapter = next(
            (c for c in chapters_clone if c.get("title", "").lower() == chapter_title.lower()), None
        )
        if not target_chapter:
            return f"Chapter '{chapter_title}' not found in {self._item_display(book_data, book_item_id)}."

        if operation == "append":
            target_chapter["content"] += "\n" + new_content.strip()
        else:
            target_chapter["content"] = new_content.strip()

        attr_result = self.state_manager.set_item_attribute(book_item_id, "chapters", chapters_clone)
        if not attr_result.success:
            return f"Error saving chapter update: {attr_result.message}"

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png"})
        return f"Chapter '{chapter_title}' in {self._item_display(book_data, book_item_id)} successfully updated."

    def delete_book_chapter(self, book_item_id: int, chapter_title: str) -> str:
        book_data, error_msg = self._fetch_book(book_item_id)
        if error_msg:
            return f"Error: {error_msg}"

        if book_data.get("is_locked"):
            return f"{self._item_display(book_data, book_item_id)} is locked. Cannot delete chapters."

        chapters = book_data.get("chapters", [])
        updated_chapters = [c for c in chapters if c.get("title", "").lower() != chapter_title.lower()]

        if len(updated_chapters) == len(chapters):
            return f"Chapter '{chapter_title}' not found in {self._item_display(book_data, book_item_id)}."

        attr_result = self.state_manager.set_item_attribute(book_item_id, "chapters", updated_chapters)
        if not attr_result.success:
            return f"Error deleting chapter: {attr_result.message}"

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/book_icon.png"})
        return f"Chapter '{chapter_title}' successfully deleted from {self._item_display(book_data, book_item_id)}."