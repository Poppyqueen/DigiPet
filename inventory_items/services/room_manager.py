
# services/room_manager.py
from utils.time_manager import get_time_tag_from_now
from utils.loc_datetime import datetime

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

    # --- Public Room Management Methods ---
    def get_room_name(self, room_id: int) -> str:
        room = self._find_room_by_id(room_id)
        if room:
            return room.get("name", "Unknown Room")
        return "Unknown Room"

    def get_current_room_id(self):
        return self._state_store.get_state_section("current_room_id", -1)

    def get_current_room_name(self):
        current_room_id = self._state_store.get_state_section("current_room_id")
        current_room = self._find_room_by_id(current_room_id)
        if current_room:
            return current_room.get("name", "Unnamed Room")
        else:
            return f"Error: Current room ID '{current_room_id}' is invalid or room not found."

    def set_current_room(self, room_id: int):
        if not isinstance(room_id, int):
            return f"Failed to move: Room ID must be an integer, received '{room_id}' ({type(room_id).__name__})."
        now = datetime.now()
        time_tag = get_time_tag_from_now(now)
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

                room_descriptions_by_time = target_room.get("descriptions", {})
                descriptions = room_descriptions_by_time.get(time_tag, []) if time_tag else []
                if not isinstance(descriptions, list) or not all(isinstance(d, str) for d in descriptions):
                    descriptions = []
                desc_str = "(No description available.)"
                if descriptions:
                    desc_str = ", ".join(descriptions)
                if not desc_str:
                    desc_str = "(No description available.)"

                # Uses InventoryService for combined list
                if self._inventory_service:
                    list_room_items_names, _ = self._inventory_service.list_inventories(formatted=True)
                    self._send_signal({"type": "room_inventory", "item_list": list_room_items_names})
                else:
                    print("Warning: InventoryService not set in RoomManager, cannot send room_inventory signal.")

                self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/pointer_icon.png"})
                return f"You move to the {self._format_room_for_display(target_room)}. Tools pool has changed. {desc_str}"
        else:
            return f"There is no room with ID '{room_id}'. The existing rooms are: {self.get_all_rooms()}"

    def get_current_room_description(self):
        current_room_id = self._state_store.get_state_section("current_room_id")
        room_data = self._find_room_by_id(current_room_id)
        now = datetime.now()
        time_tag = get_time_tag_from_now(now)

        if room_data:
            room_display = self._format_room_for_display(room_data)
            room_descriptions_by_time = room_data.get("descriptions", {})
            descriptions = room_descriptions_by_time.get(time_tag, []) if time_tag else []

            if isinstance(descriptions, list) and all(isinstance(d, str) for d in descriptions):
                if descriptions:
                    return f"Description for {room_display} ({time_tag}):\n" + "\n".join(descriptions)
                else:
                    return f"The {room_display} has no specific description for '{time_tag}'."
            else:
                return f"Error: Descriptions for {room_display} are corrupted for time tag '{time_tag}'."
        else:
            return f"Error: Could not find description for current room (ID: {current_room_id}). State might be corrupted."

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