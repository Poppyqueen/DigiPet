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
            room_data = RoomDataResult.from_room_dict(target_room)
            return f"You are already in the {room_data.title_display}."

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
            f"You move to the {room_data.title_display}. "
            f"Tools pool has changed." # removed: {room_data.description}
        )

    # ------------------------------------------------------------------
    # Accessible rooms 
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
    

 

    def llm_get_accessible_rooms(self) -> str:
        """
        Returns a formatted string describing every room reachable from the
        current room, shaped for direct LLM consumption.
 
        Three cases:
 
        1. Current room is a connectoid — corridor template:
           "You are in a connecting area. You can travel to:
            * Garden (ID:000003) [blue_set]
            * Living Room (ID:000012) [red_set]"
 
        2. Current room is a regular room with exits:
           "You see the following areas around:
            * Outdoors Area A (ID:000007) [blue_set]
            * Garden (ID:000003) [blue_set] [Gateway — leads to: Hallway]
            * Hallway (ID:000001) [Connecting: Garden, Living Room, Bathroom]"
 
        3. No accessible rooms at all:
           "There are no accessible areas from here."
        """
        graph = self._state_store.get_connections_graph()
        current_room_id = self.get_current_room_id()
        accessible_ids = graph.get_accessible_ids(current_room_id)
 
        if not accessible_ids:
            return "There are no accessible areas from here."
 
        standing_in_connectoid = graph.is_connectoid(current_room_id)
 
        def _format_room_line(room_id: int) -> str:
            room = self._find_room_by_id(room_id)
            if not room:
                return f"* Unknown area (ID:{room_id})"
 
            name = room.get("name", "Unknown")
            parts = [f"* {name} (ID:{room_id:06d})"]
 
            if graph.is_connectoid(room_id):
                # Show where this connectoid leads by name — no group tag since
                # connectoids never have one, and destinations are more useful.
                dest_ids = graph.get_connectoid_destinations(room_id)
                dest_names = []
                for did in dest_ids:
                    dest_room = self._find_room_by_id(did)
                    if dest_room:
                        dest_names.append(dest_room.get("name", f"ID:{did}"))
                if dest_names:
                    parts.append(f"[Connecting: {', '.join(dest_names)}]")
            else:
                # Regular room — show group, then gateway annotation if applicable.
                group = room.get("movement_group")
                if isinstance(group, str) and group:
                    parts.append(f"[{group}]")
 
                if not standing_in_connectoid:
                    exit_ids = graph.get_connectoid_exits(room_id)
                    if exit_ids:
                        exit_names = []
                        for eid in exit_ids:
                            exit_room = self._find_room_by_id(eid)
                            if exit_room:
                                exit_names.append(exit_room.get("name", f"ID:{eid}"))
                        if exit_names:
                            parts.append(f"[Gateway — leads to: {', '.join(exit_names)}]")
 
            return " ".join(parts)
 
        lines = [_format_room_line(rid) for rid in accessible_ids]
 
        if standing_in_connectoid:
            return "You are in a connecting area. You can travel to:\n" + "\n".join(lines)
 
        return "You see the following areas around:\n" + "\n".join(lines)

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