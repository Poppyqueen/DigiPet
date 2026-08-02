import json
import copy
from pathlib import Path


class RoomStore:
    """
    A shared catalogue of room definitions loaded from a directory tree of JSON files.

    Each JSON file may contain a single room dict or a list of room dicts.
    Rooms are indexed by their "name" field and are shared across any number of
    house states — designers pick from the full collection when assembling a layout.

    Mirrors ItemStore's interface as closely as the room domain allows.
    """

    def __init__(
        self,
        root_dir_path: str = "inventory_items/rooms_provider/rooms_data",
        valid_types: list[str] | None = None,
    ):
        self._rooms: dict[str, dict] = {}
        self._room_to_file_map: dict[str, str] = {}
        self._root_dir = Path(root_dir_path)
        # None means "accept everything" — mirrors ItemStore behaviour
        self._valid_types: set[str] | None = set(valid_types) if valid_types is not None else None
        self._load_rooms()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _room_passes_type_filter(self, room_data: dict) -> bool:
        """
        Returns True if this room's room_types are all within the valid set,
        or if no filter is active (valid_types was None).
        Rooms with no room_types tag always pass.
        """
        if self._valid_types is None:
            return True
        room_types = room_data.get("room_types", [])
        if not room_types:
            return True
        return all(t in self._valid_types for t in room_types)

    def _load_rooms(self):
        if not self._root_dir.is_dir():
            print(f"Warning: '{self._root_dir}' is not a valid directory.")
            return

        for path in self._root_dir.rglob("*.json"):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = [data]
                    for room_data in data:
                        room_name = room_data.get("name")
                        if room_name and self._room_passes_type_filter(room_data):
                            self._rooms[room_name] = room_data
                            self._room_to_file_map[room_name] = str(path)
            except (IOError, json.JSONDecodeError) as e:
                print(f"Error loading from '{path}': {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_room(self, name: str | list[str]) -> dict | None | dict[str, dict]:
        """
        Retrieve a deep copy of a room by name, or a batch dict keyed by name.

        Single name  → returns the room dict, or None if not found.
        List of names → returns a dict mapping each found name to its room dict
                        (missing names are silently omitted, mirroring ItemStore).
        """
        def get_single(n: str) -> dict | None:
            room = self._rooms.get(n)
            return copy.deepcopy(room) if room is not None else None

        if isinstance(name, (list, tuple, set)):
            return {n: get_single(n) for n in name if get_single(n) is not None}

        return get_single(name)

    def get_rooms_by_type(self, room_type: str) -> list[dict]:
        """
        Return deep copies of all rooms that include the specified room_type tag.
        """
        return [
            copy.deepcopy(r)
            for r in self._rooms.values()
            if room_type in r.get("room_types", [])
        ]

    def find_rooms(self, filters: dict | None = None) -> list[dict]:
        """
        Return all rooms that match every provided filter.

        Supports a special '__source_path__' key (mirrors ItemStore.find_items):
            filters={'__source_path__': 'walled_garden/'}
            filters={'__source_path__': 'walled_garden/hallway.json'}

        The path is interpreted relative to the store's root directory — a prefix
        match on the absolute path, so both files and subdirectories work.

        All other keys are matched against the room dict directly.
        The 'room_types' key supports list-vs-list "all provided types present" logic.
        """
        if filters is None:
            return [copy.deepcopy(r) for r in self._rooms.values()]

        found = []
        for room_name, room_data in self._rooms.items():
            match = True

            if "__source_path__" in filters:
                expected_segment = filters["__source_path__"]
                expected_path = str(self._root_dir / expected_segment)
                actual_path = self._room_to_file_map.get(room_name)
                if not actual_path or not actual_path.startswith(expected_path):
                    match = False

            if match:
                for key, value in filters.items():
                    if key == "__source_path__":
                        continue

                    if key not in room_data:
                        match = False
                        break

                    if (
                        key == "room_types"
                        and isinstance(value, list)
                        and isinstance(room_data.get("room_types"), list)
                    ):
                        if not all(t in room_data.get("room_types", []) for t in value):
                            match = False
                            break
                    elif room_data[key] != value:
                        match = False
                        break

            if match:
                found.append(copy.deepcopy(room_data))

        return found

    def get_all_rooms(self) -> list[dict]:
        """Return deep copies of every room currently in the store."""
        return [copy.deepcopy(r) for r in self._rooms.values()]

    def list_room_names(self) -> list[str]:
        """Return all known room names — useful for manifest validation."""
        return list(self._rooms.keys())

    def add_room_definition(self, room_data: dict) -> tuple[bool, str]:
        """
        Register a room definition in memory without touching the filesystem.
        Returns (True, success_message) or (False, error_message).
        """
        room_name = room_data.get("name")
        if not room_name:
            return False, "Failed to add room: 'name' key is missing."
        if room_name in self._rooms:
            return False, f"Failed to add room: a room named '{room_name}' already exists."

        self._rooms[room_name] = copy.deepcopy(room_data)
        self._room_to_file_map[room_name] = None
        return True, f"Room '{room_name}' added successfully."

    def save_room_to_file(self, room_name: str, file_path: str | None = None) -> tuple[bool, str]:
        """
        Persist a single room to disk.

        file_path is relative to the store root. When omitted, falls back to the
        room's original source file, or a generated filename in the root directory.
        """
        room_data = self._rooms.get(room_name)
        if not room_data:
            return False, f"Error: room '{room_name}' not found in store."

        if file_path:
            save_path = self._root_dir / file_path
        else:
            original = self._room_to_file_map.get(room_name)
            if original:
                save_path = Path(original)
            else:
                slug = room_name.replace(" ", "_").lower()
                save_path = self._root_dir / f"{slug}.json"

        try:
            existing = []
            if save_path.exists():
                with open(save_path, "r") as f:
                    try:
                        existing = json.load(f)
                        if not isinstance(existing, list):
                            existing = [existing]
                    except json.JSONDecodeError:
                        print(f"Warning: '{save_path}' is not valid JSON. Overwriting.")
                        existing = []

            replaced = False
            for i, entry in enumerate(existing):
                if entry.get("name") == room_name:
                    existing[i] = room_data
                    replaced = True
                    break
            if not replaced:
                existing.append(room_data)

            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w") as f:
                json.dump(existing, f, indent=4)

            self._room_to_file_map[room_name] = str(save_path)
            return True, f"Successfully saved room '{room_name}' to '{save_path}'."

        except IOError as e:
            return False, f"Error saving room '{room_name}': {e}"

    # ------------------------------------------------------------------
    # Reload
    # ------------------------------------------------------------------

    def reload(self):
        """Re-scan the root directory. Useful if files change on disk at runtime."""
        self._rooms.clear()
        self._room_to_file_map.clear()
        self._load_rooms()
        print(f"RoomStore reloaded — {len(self._rooms)} rooms available.")