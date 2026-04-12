# services/room_manager.py

from inventory_items.services.return_objects import RoomDataResult


class RoomManager:
    def __init__(self, state_store, signal_callback):
        self._state_store = state_store
        self._signal_callback = signal_callback
        self._inventory_service = None  # Set later to resolve circular dependency

    def set_inventory_service(self, inventory_service_instance):
        """Sets the InventoryService dependency to resolve circular dependency."""
        self._inventory_service = inventory_service_instance

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal: {e}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_room_by_id(self, room_id):
        """Returns the raw room dict for room_id, or None."""
        if not isinstance(room_id, int):
            return None
        rooms = self._state_store.get_state_section("rooms")
        if isinstance(rooms, list):
            for room in rooms:
                if isinstance(room, dict) and room.get("id") == room_id and isinstance(room.get("id"), int):
                    return room
        return None

    def _find_room_id_by_name(self, room_name):
        """Returns the room ID for room_name (case-insensitive), or None."""
        if not isinstance(room_name, str) or not room_name.strip():
            return None
        name_lower = room_name.strip().lower()
        rooms = self._state_store.get_state_section("rooms")
        if isinstance(rooms, list):
            for room in rooms:
                if isinstance(room, dict) and isinstance(room.get("name"), str) and room["name"].lower() == name_lower:
                    return room.get("id")
        return None

    def _format_room_for_display(self, room_dict):
        """Formats a room dict as 'Name (ID:000001)'."""
        if not isinstance(room_dict, dict):
            return "Invalid Room Data"
        room_id = room_dict.get("id", -1)
        room_name = room_dict.get("name", "Unnamed Room")
        if not isinstance(room_id, int):
            return f"{room_name} (ID:INVALID)"
        return f"{room_name} (ID:{room_id:06d})"

    # ------------------------------------------------------------------
    # Room ID / current room
    # ------------------------------------------------------------------

    def get_current_room_id(self) -> int:
        return self._state_store.get_state_section("current_room_id", -1)

    # ------------------------------------------------------------------
    # Movement — access-gated
    # ------------------------------------------------------------------

    def set_current_room(self, room_id: int) -> str:
        if not isinstance(room_id, int):
            return (
                f"Failed to move: Room ID must be an integer, "
                f"received '{room_id}' ({type(room_id).__name__})."
            )

        target_room = self._find_room_by_id(room_id)
        if not target_room:
            return f"There is no room with ID '{room_id}'."

        current_room_id = self._state_store.get_state_section("current_room_id")

        if current_room_id == room_id:
            return f"You are already in the {self._format_room_for_display(target_room)}."

        # ── Access check ──────────────────────────────────────────────
        graph = self._state_store.get_connections_graph()
        if not graph.is_accessible(current_room_id, room_id):
            return "You don't see that area around you."
        # ─────────────────────────────────────────────────────────────

        self._state_store.update_state_section("current_room_id", room_id)

        # Background signal
        current_room_data = self._find_room_by_id(
            self._state_store.get_state_section("current_room_id")
        )
        if current_room_data:
            image_name = current_room_data.get("image", "unnamed_image")
            self._send_signal({"type": "change_background", "image_name": image_name})

        # Room inventory signal
        if self._inventory_service:
            state = self._inventory_service.get_inventory_state()
            self._send_signal({"type": "room_inventory", "item_list": state.room_display_strings})
        else:
            print("Warning: InventoryService not set in RoomManager, cannot send room_inventory signal.")

        self._send_signal({
            "type": "show_icon_popup",
            "icon_path": "style/images/action_icons/pointer_icon.png",
        })

        room_data = RoomDataResult.from_room_dict(target_room)
        return (
            f"You move to the {self._format_room_for_display(target_room)}. "
            f"Tools pool has changed. {room_data.description}"
        )

    # ------------------------------------------------------------------
    # Accessible rooms (LLM-facing)
    # ------------------------------------------------------------------

    def get_accessible_rooms(self) -> list[RoomDataResult]:
        """
        Returns RoomDataResult for every room reachable from the current room.

        Rules (enforced by ConnectionsGraph):
          - Same movement_group  → freely reachable
          - Connectoid listing current room in connections → reachable
          - From a connectoid → only its declared connections
          - Everything else → not included
        """
        graph = self._state_store.get_connections_graph()
        current_room_id = self.get_current_room_id()
        accessible_ids = graph.get_accessible_ids(current_room_id)

        results = []
        for room_id in accessible_ids:
            room = self._find_room_by_id(room_id)
            if room:
                results.append(RoomDataResult.from_room_dict(room))
        return results

    # ------------------------------------------------------------------
    # Data accessors (unchanged, get_all_rooms_data returns everything)
    # ------------------------------------------------------------------

    def get_room_data(self, room_id: int) -> RoomDataResult:
        """Returns a RoomDataResult for any room by ID. Raises ValueError if not found."""
        room = self._find_room_by_id(room_id)
        if room is None:
            raise ValueError(f"Room id={room_id} not found. State may be corrupted.")
        return RoomDataResult.from_room_dict(room)

    def get_current_room_data(self) -> RoomDataResult:
        """Returns a RoomDataResult for the current room."""
        return self.get_room_data(self.get_current_room_id())

    def get_all_rooms_data(self) -> list[RoomDataResult]:
        """
        Returns a RoomDataResult for EVERY room in state — no filtering.
        This is a logic/system endpoint. For LLM movement use get_accessible_rooms().
        """
        rooms = self._state_store.get_state_section("rooms", [])
        return [
            RoomDataResult.from_room_dict(room)
            for room in rooms
            if isinstance(room, dict)
        ]