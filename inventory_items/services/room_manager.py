
# services/room_manager.py
#from utils.time_manager import get_time_tag_from_now

from inventory_items.services.return_objects import (
    RoomDataResult
)

class RoomManager:
    def __init__(self, state_store, signal_callback):
        self._state_store = state_store
        self._signal_callback = signal_callback
        self._inventory_service = None # Dependency to be set later

    def set_inventory_service(self, inventory_service_instance):
        """Sets the InventoryService dependency to resolve circular dependency."""
        self._inventory_service = inventory_service_instance

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal: {e}")

    # --- Helper Methods (Internal to RoomManager) ---
    def _find_room_by_id(self, room_id):
        """Internal helper to find a room dictionary by its ID, returning None if not found."""
        if not isinstance(room_id, int):
            return None
        rooms = self._state_store.get_state_section("rooms")
        if isinstance(rooms, list):
            for room in rooms:
                if isinstance(room, dict) and room.get("id") == room_id and isinstance(room.get("id"), int):
                    return room
        return None

    def _find_room_id_by_name(self, room_name):
        """Internal helper to find a room ID by its name (case-insensitive), returning None if not found."""
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
        """Formats a room dictionary into a readable string including name and ID."""
        if not isinstance(room_dict, dict):
            return "Invalid Room Data"
        room_id = room_dict.get('id', -1)
        room_name = room_dict.get('name', 'Unnamed Room')
        if not isinstance(room_id, int):
            return f"{room_name} (ID:INVALID)"
        return f"{room_name} (ID:{room_id:06d})"




    def get_current_room_id(self):
        return self._state_store.get_state_section("current_room_id", -1)

    def set_current_room(self, room_id: int):
        if not isinstance(room_id, int):
            return f"Failed to move: Room ID must be an integer, received '{room_id}' ({type(room_id).__name__})."
        #time_tag = get_time_tag_from_now()
        target_room = self._find_room_by_id(room_id)

        if target_room:
            current_room_id = self._state_store.get_state_section("current_room_id")
            if current_room_id == room_id:
                return f"You are already in the {self._format_room_for_display(target_room)}."
            else:
                self._state_store.update_state_section("current_room_id", room_id)

                current_room_data = self._find_room_by_id(self._state_store.get_state_section("current_room_id"))
                if current_room_data:
                    c_name = current_room_data.get("image", "unnamed_image")
                    self._send_signal({"type": "change_background", "image_path": f"{c_name}"})

                room_data = RoomDataResult.from_room_dict(target_room)
                room_descriptions_by_time = room_data.description

                # Uses InventoryService for combined list
                if self._inventory_service:
                    list_room_items_names, _ = self._inventory_service.list_inventories(formatted=True)
                    self._send_signal({"type": "room_inventory", "item_list": list_room_items_names})
                else:
                    print("Warning: InventoryService not set in RoomManager, cannot send room_inventory signal.")

                self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/pointer_icon.png"})
                return f"You move to the {self._format_room_for_display(target_room)}. Tools pool has changed. {room_descriptions_by_time}"
        else:
            return f"There is no room with ID '{room_id}'."

    def get_all_rooms(self):
        rooms_list = self._state_store.get_state_section("rooms")
        if isinstance(rooms_list, list):
            valid_rooms = [
                room for room in rooms_list
                if isinstance(room, dict) and isinstance(room.get('id'), int) and isinstance(room.get('name'), str)
            ]
            room_display = [self._format_room_for_display(room) for room in valid_rooms]
            if room_display:
                return f"Available rooms: {', '.join(room_display)}"
            else:
                return "No rooms are currently defined."
        else:
            return "Error: Could not access room list. State might be corrupted."

    def get_room_data(self, room_id: int) -> RoomDataResult:
        """
        Returns a RoomDataResult for any room by ID.
        Raises ValueError if the room is not found.
        """
        room = self._find_room_by_id(room_id)
        if room is None:
            raise ValueError(f"Room id={room_id} not found. State may be corrupted.")
        return RoomDataResult.from_room_dict(room)

    def get_current_room_data(self) -> RoomDataResult:
        """Returns a RoomDataResult for the current room."""
        return self.get_room_data(self.get_current_room_id())

    def get_all_rooms_data(self) -> list[RoomDataResult]:
        """
        Returns a RoomDataResult for every room in state.
        Callers that need to filter by room_types, plot_number, etc.
        should do so on the returned list.
        """
        rooms = self._state_store.get_state_section("rooms", [])
        return [
            RoomDataResult.from_room_dict(room)
            for room in rooms
            if isinstance(room, dict)
        ]