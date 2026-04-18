"""
images_lab.py
─────────────
Controller layer for the per-item SVG image archive.

Owns the ``state_manager`` reference, resolves item access, retrieves / mints
stable UIDs, and exposes agent-facing tool methods that return plain ``str``.

All archive logic (filesystem I/O, metadata, validation) lives in
``images_archive_manager.py``.  This file is a thin shell that follows the
controller pattern defined in the framework skill.

"""

# TODO: Add int field for drawing area which limits how many images can be stored in the archive.

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.tools_folder.tools_helpers.images_helpers.images_archive_manager import (
    ImagesArchiveManager,
    generate_uid,
)

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager

# Item type this controller operates on.
IMAGES_LAB_ITEM_TYPE = "drawing_area"

# The key used to store the stable UID inside item state.
_UID_KEY = "images_lab_uid"


class ImagesLab:
    """
    Thin controller that exposes SVG-archive tools to the agent.

    Responsibilities
    ────────────────
    - Locate items via ``state_manager.find_item``.
    - Ensure every item has a stable UID (mint one and persist it on first use).
    - Instantiate ``ImagesArchiveManager`` with the item's UID and delegate all
      archive work to it.
    - Return plain ``str`` results to the agent.

    No filesystem logic lives here — this class only orchestrates.
    """

    def __init__(self, state_manager, signal_callback) -> None:
        self.state_manager: InventoryHouseManager = state_manager
        self._signal_callback = signal_callback

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_manager(self, item_id: int) -> tuple[ImagesArchiveManager | None, str]:
        """
        Locate *item_id*, ensure it has a UID, and return an ``ImagesArchiveManager``.

        Mints and persists a new UID via ``set_item_attribute`` the first time
        an item is encountered.

        Args:
            item_id: The agent-provided item ID.

        Returns:
            ``(manager, "")`` on success.
            ``(None, error_message)`` on any failure.
        """
        found = self.state_manager.find_item(
            item_id,
            required_type=IMAGES_LAB_ITEM_TYPE,
            required_location="accessible",
        )
        if not found.success:
            return None, found.error
        
        if found.toggle_state is False:
            return None, f"Item {self.state_manager.format_item_for_display(item_id,False)}, is 'off' can't use it like that."



        item_data = found.item_data
        uid = item_data.get(_UID_KEY)

        # Mint a UID if this item does not have one yet.
        if not uid:
            uid = generate_uid()
            result = self.state_manager.set_item_attribute(item_id, key=_UID_KEY, value=uid)
            if not result.success:
                return None, f"Failed to assign a stable UID to item {item_id}: {result.error}"

        manager = ImagesArchiveManager(self.state_manager.base_path, uid)
        return manager, ""


    def get_image_data(self, item_id: int, image_name: str) -> tuple[bytes | None, str]:
        """
        Resolve item, then return PNG bytes and alt text for *image_name*.

        Returns:
            ``(png_bytes, alt_text)`` on success.
            ``(None, error_message)`` on any failure.
        """
        manager, error = self._get_manager(item_id)
        if manager is None:
            return None, f"Could not access images lab: {error}"

        return manager.get_image_data(image_name)
    
    
    # ------------------------------------------------------------------
    # Agent-facing tool methods  (all return plain str)
    # ------------------------------------------------------------------

    def create_svg_image(self, item_id: int, image_name: str, concept: str, content: str) -> str:
        """
        Save an SVG image to the archive owned by *item_id*.

        Creation is **blocked** if the archive is at its limit.  No existing
        images are ever deleted automatically — use ``delete_image`` to free space.

        Args:
            item_id:    ID of the images-lab item in the player's inventory or room.
            image_name: Human-readable label for the image (used as the filename).
            concept:    Short description of what the image represents.
            content:    Raw SVG markup.

        Returns:
            A status string for the agent describing success or the reason for failure.
        """
        manager, error = self._get_manager(item_id)
        if manager is None:
            return f"Could not access images lab: {error}"

        success, message = manager.create_svg_image(image_name, concept, content)
        return message

    def delete_image(self, item_id: int, image_name: str) -> str:
        """
        Delete a specific image from the archive owned by *item_id*.

        The agent controls which images to remove — this is how space is freed
        when the archive is full.

        Args:
            item_id:    ID of the images-lab item.
            image_name: The exact ``image_name`` as shown in ``read_image_archive``.

        Returns:
            A status string confirming deletion or explaining why it failed.
        """
        manager, error = self._get_manager(item_id)
        if manager is None:
            return f"Could not access images lab: {error}"

        success, message = manager.delete_image(image_name)
        return message

    def read_image_archive(self, item_id: int) -> str:
        """
        List all archived images for *item_id*, plus current usage.

        Args:
            item_id: ID of the images-lab item.

        Returns:
            A formatted string listing every archived image and archive usage,
            or a message indicating the archive is empty.
        """
        manager, error = self._get_manager(item_id)
        if manager is None:
            return f"Could not access images lab: {error}"

        parts = []
        entries = manager.read_archive()

        if not entries:
            parts.append("The image archive is empty.")
        else:
            parts.extend(entries)

        parts.append(manager.get_archive_status())
        return "\n".join(p for p in parts if p)