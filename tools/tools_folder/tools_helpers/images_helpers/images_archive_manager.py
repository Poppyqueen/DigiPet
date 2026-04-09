"""
images_archive_manager.py
─────────────────────────
Pure-logic layer for the per-item SVG image archive.

No reference to ``state_manager`` or any framework object lives here.
All filesystem I/O, UID registration, metadata management, and SVG
validation is handled in this file.  The controller (``images_lab.py``)
is the only caller.

Directory layout
────────────────
<base_path>/
└── images_archive/
    ├── registry.json          ← uid → subdir_name mapping (the "database")
    ├── <uid-a>/
    │   ├── metadata.json
    │   ├── my_image.svg
    │   └── …
    └── <uid-b>/
        ├── metadata.json
        └── …
"""

import os
import json
import re
import uuid
import logging
import io

from utils.loc_datetime import datetime
from tools.tools_folder.tools_helpers.svg_validator import SVGValidator

# ---------------------------------------------------------------------------
# Module-level configuration
# ---------------------------------------------------------------------------

TOTAL_IMAGES_LIMIT: int = 10000  # Max images per item. TODO: make configurable.
_REGISTRY_FILENAME: str = "registry.json"
_METADATA_FILENAME: str = "metadata.json"


# ---------------------------------------------------------------------------
# String / UID helpers
# ---------------------------------------------------------------------------



def _convert_svg_to_png(svg_path: str):
    """Convert an SVG file to PNG bytes, resizing if over 1200×1200."""
    try:
        from PIL import Image
        import cairosvg

        png_data = cairosvg.svg2png(url=svg_path)

        with Image.open(io.BytesIO(png_data)) as img:
            max_size = (1200, 1200)
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', optimize=True)
            return img_bytes.getvalue()

    except ImportError:
        logging.error("cairosvg not available. Install with: pip install cairosvg")
        return None
    except Exception as e:
        logging.error(f"Failed to convert SVG to PNG: {e}")
        return None

def make_string_file_safe(input_string: str) -> str:
    """
    Sanitize *input_string* so it is safe to use as a file name.

    Replaces characters that are unsafe on common operating systems with ``_``.
    Spaces are also replaced with ``_``.

    Args:
        input_string: The raw string to sanitize.

    Returns:
        A filesystem-safe version of the string.
    """
    unsafe_chars_pattern = re.compile(r'[^\w\s\.-]')
    safe = unsafe_chars_pattern.sub('_', input_string)
    safe = safe.replace(' ', '_')
    return safe.strip()


def generate_uid() -> str:
    """
    Return a new, globally unique identifier string (UUID4).

    Call this exactly once when an item is first created and persist the
    result via ``state_manager.set_item_attribute(item_id, "images_lab_uid", uid)``.
    Because item IDs can change, the UID is the stable tracking key — never
    use the item ID as the archive key.

    Returns:
        A UUID4 string such as ``"3f2504e0-4f89-11d3-9a0c-0305e82c3301"``.
    """
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Registry helpers  (uid ↔ subdirectory mapping)
# ---------------------------------------------------------------------------

def _load_registry(archive_root: str) -> dict:
    """Return the uid→subdir_name mapping dict, or ``{}`` on any error."""
    path = os.path.join(archive_root, _REGISTRY_FILENAME)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_registry(archive_root: str, registry: dict) -> None:
    """Persist *registry* to ``registry.json``, printing a warning on failure."""
    path = os.path.join(archive_root, _REGISTRY_FILENAME)
    try:
        with open(path, 'w') as f:
            json.dump(registry, f, indent=4)
    except OSError as e:
        print(f"[ImagesArchiveManager] Warning: could not write registry: {e}")


def get_or_create_item_dir(archive_root: str, uid: str) -> str:
    """
    Return the absolute path to the per-item subdirectory for *uid*.

    Creates the directory and registers the UID on first call.

    Args:
        archive_root: Absolute path to the shared ``images_archive`` directory.
        uid:          Stable item UID from ``generate_uid()``.

    Returns:
        Absolute path to the per-item directory (guaranteed to exist on disk).
    """
    registry = _load_registry(archive_root)

    if uid not in registry:
        registry[uid] = uid          # subdir name == uid (already fs-safe)
        _save_registry(archive_root, registry)

    item_dir = os.path.join(archive_root, registry[uid])
    os.makedirs(item_dir, exist_ok=True)
    return item_dir


# ---------------------------------------------------------------------------
# ImagesArchiveManager
# ---------------------------------------------------------------------------

class ImagesArchiveManager:
    """
    Manages the SVG image archive for a single item, identified by *uid*.

    All files for this item live under::

        <archive_root>/<uid>/

    This class has no knowledge of ``state_manager`` or any framework object.
    It is instantiated and used exclusively by ``ImagesLab`` (the controller).

    Limit policy
    ────────────
    When the per-item archive reaches ``TOTAL_IMAGES_LIMIT``, **creation is
    blocked** and a descriptive message is returned.  Old images are never
    deleted automatically.  Use ``delete_image`` to remove specific entries
    and free up space — that decision belongs to the agent, not the system.
    """

    def __init__(self, base_path: str, uid: str) -> None:
        """
        Args:
            base_path:  Filesystem root (``state_manager.base_path``).
            uid:        Stable item UID from ``generate_uid()``.
        """
        self._archive_root = os.path.join(base_path, "images_archive")
        os.makedirs(self._archive_root, exist_ok=True)

        self._uid = uid
        self._item_dir = get_or_create_item_dir(self._archive_root, uid)
        self._svg_validator = SVGValidator()

    # ------------------------------------------------------------------
    # Internal metadata helpers
    # ------------------------------------------------------------------

    @property
    def _metadata_path(self) -> str:
        return os.path.join(self._item_dir, _METADATA_FILENAME)

    def _read_metadata(self) -> list:
        """Return the metadata list for this item, or ``[]`` on any error."""
        if not os.path.exists(self._metadata_path):
            return []
        try:
            with open(self._metadata_path, 'r') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _write_metadata(self, data: list) -> None:
        """Overwrite the metadata file with *data*."""
        try:
            with open(self._metadata_path, 'w') as f:
                json.dump(data, f, indent=4)
        except OSError as e:
            print(f"[ImagesArchiveManager uid={self._uid}] Warning: could not write metadata: {e}")

    def _append_metadata(self, entry: dict) -> None:
        """Append *entry* to the metadata list and persist."""
        data = self._read_metadata()
        data.append(entry)
        self._write_metadata(data)

    # ------------------------------------------------------------------
    # Public API (called by the controller)
    # ------------------------------------------------------------------
    def get_image_data(self, image_name: str) -> tuple[bytes | None, str]:
        """
        Retrieve PNG bytes and alt text for a named image.

        Looks up *image_name* in the metadata, resolves its path,
        and converts the SVG to PNG.

        Returns:
            ``(png_bytes, alt_text)`` on success.
            ``(None, error_message)`` on any failure.
        """
        metadata = self._read_metadata()
        target = next((e for e in metadata if e.get("image_name") == image_name), None)

        if not target:
            return None, f"Image '{image_name}' not found in archive."

        path = target.get("path")
        if not path or not os.path.exists(path):
            return None, f"Image file not found at '{path}'."

        alt = f"{target['image_name']}: {target['concept']}"

        img_bytes = _convert_svg_to_png(path)
        if img_bytes is None:
            return None, "Failed to convert SVG to PNG."

        return img_bytes, alt
    
    def is_at_limit(self) -> bool:
        """Return ``True`` if this item's archive has reached ``TOTAL_IMAGES_LIMIT``."""
        return len(self._read_metadata()) >= TOTAL_IMAGES_LIMIT

    def get_image_count(self) -> int:
        """Return the number of images currently archived for this item."""
        return len(self._read_metadata())

    def create_svg_image(self, image_name: str, concept: str, content: str) -> tuple[bool, str]:
        """
        Validate and save an SVG image, updating the metadata archive.

        Blocks creation (without deleting anything) if the limit is reached.

        Args:
            image_name: Human-readable label used as the file name.
            concept:    Short description of what the image represents.
            content:    Raw SVG markup to write to disk.

        Returns:
            ``(True, success_message)`` on success.
            ``(False, error_message)`` on any failure, including limit reached.
        """
        # Enforce limit — block, never silently delete.
        if self.is_at_limit():
            count = self.get_image_count()
            return (
                False,
                f"Image limit reached ({count}/{TOTAL_IMAGES_LIMIT}). "
                f"Delete one or more existing images before creating new ones."
            )

        # Validate SVG content before touching disk.
        validation_result = self._svg_validator.validate_string(content)
        if not validation_result['valid']:
            return False, f"SVG validation failed: {validation_result['error']}"

        final_name = make_string_file_safe(image_name)
        svg_path = os.path.join(self._item_dir, f"{final_name}.svg")

        # Write the SVG file.
        try:
            with open(svg_path, 'w') as f:
                f.write(content)
        except IOError as e:
            print(f"[ImagesArchiveManager uid={self._uid}] IOError writing SVG: {e}")
            return False, f"Failed to write image file for concept '{concept}'. Error: {e}"

        # Persist metadata.
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            entry = {
                "image_name": image_name,   # original name for readability
                "concept": concept,
                "path": svg_path,
                "time_stamp": timestamp,
                "uid": self._uid,
            }
            self._append_metadata(entry)
        except Exception as e:
            # Roll back the SVG file to keep disk and metadata in sync.
            if os.path.exists(svg_path):
                os.remove(svg_path)
            print(f"[ImagesArchiveManager uid={self._uid}] Error writing metadata: {e}")
            return False, (
                f"Image file was created but metadata update failed. "
                f"The file has been removed to prevent orphaned data. Error: {e}"
            )

        count_after = self.get_image_count()
        return True, (
            f"Image '{final_name}' for concept '{concept}' saved successfully. "
            f"Archive: {count_after}/{TOTAL_IMAGES_LIMIT}."
        )

    def delete_image(self, image_name: str) -> tuple[bool, str]:
        """
        Delete an archived image by its *image_name* and remove its SVG file.

        Args:
            image_name: The exact ``image_name`` value as shown in the archive
                        listing (case-sensitive).

        Returns:
            ``(True, success_message)`` if the entry was found and removed.
            ``(False, error_message)`` if the name was not found.
        """
        data = self._read_metadata()
        target_index = next(
            (i for i, e in enumerate(data) if e.get("image_name") == image_name),
            None
        )

        if target_index is None:
            return False, (
                f"No image named '{image_name}' found in the archive. "
                f"Use read_image_archive to see the current listing."
            )

        entry = data.pop(target_index)
        svg_path = entry.get("path")

        # Remove the SVG file; warn but don't fail if it is already gone.
        file_removed = False
        if svg_path:
            try:
                if os.path.exists(svg_path):
                    os.remove(svg_path)
                    file_removed = True
            except OSError as e:
                print(f"[ImagesArchiveManager uid={self._uid}] Warning: could not remove '{svg_path}': {e}")

        self._write_metadata(data)
        count_after = len(data)

        note = "" if file_removed else " (SVG file was already missing from disk)"
        return True, (
            f"Image '{image_name}' deleted.{note} "
            f"Archive: {count_after}/{TOTAL_IMAGES_LIMIT}."
        )

    def read_archive(self) -> list[str]:
        """
        Return a human-readable summary string for each archived image.

        Returns:
            A list of strings, one per image, suitable for agent display.
            Empty list when the archive is empty.
        """
        data = self._read_metadata()
        if not data:
            return []
        return [
            f"Image Name: {e['image_name']}, Concept: {e['concept']}, Path: {e['path']}"
            for e in data
        ]

    def get_archive_status(self) -> str:
        """
        Return a one-line status string describing the current archive usage.

        Example: ``"Archive: 42/10000 images stored."``
        """
        count = self.get_image_count()
        return f"Archive: {count}/{TOTAL_IMAGES_LIMIT} images stored."