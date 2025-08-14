
# inventory_house_manager.py (UPDATED)
from inventory_items.items_init import base_state, dev_room

# Import the new StateStore
from inventory_items.services.state_store import StateStore

# Import the new service classes (will be created in subsequent steps)
from inventory_items.services.inventory_service import InventoryService
from inventory_items.services.room_manager import RoomManager
from inventory_items.services.book_service import BookService # This will replace the old book_component
from inventory_items.services.stat_tracker import StatTracker # This will replace the old stats_component
from inventory_items.services.pet_state_manager import PetStateManager
from inventory_items.services.simulation_state_service import SimulationStateService


class InventoryHouseManager: # NO LONGER INHERITS FROM GenericJsonTool
    MAX_INVENTORY_SLOTS = 30 # This constant can stay here or move to InventoryService

    def __init__(self, base_path, signal=None, memory=None, config_manager=None):
        self.base_path = base_path
        self._signal_callback = signal
        self.memory = memory
        self.config_manager = config_manager

        # 1. Determine the initial state to load
        available_states = {
            "base_state": base_state,
            "dev_room": dev_room,
        }
        selected_state_name = config_manager.get_config("game_settings", "initial_state")
        selected_state = available_states.get(selected_state_name, base_state) # Fallback if name not found

        # 2. Initialize the central StateStore
        print(f"DEBUG INVENTORY MANAGER INIT: Initializing StateStore with {selected_state_name}")
        self._state_store = StateStore(base_path, selected_state)

        # 3. Initialize all services, passing StateStore and signal_callback
        # Order services to minimize immediate circular dependency issues, resolve later
        self.inventory_service = InventoryService(self._state_store, self._signal_callback)
        self.room_manager = RoomManager(self._state_store, self._signal_callback)
        self.stat_tracker = StatTracker(self._state_store, self._signal_callback)
        self.book_service = BookService(self._state_store, self._signal_callback)
        self.pet_state_manager = PetStateManager(self._state_store, self._signal_callback)
        self.simulation_state_service = SimulationStateService(self._state_store)

        # 4. Resolve explicit circular dependencies or cross-service references
        self.inventory_service.set_room_manager(self.room_manager)
        self.room_manager.set_inventory_service(self.inventory_service)
        self.stat_tracker.set_inventory_service(self.inventory_service) # StatTracker needs InventoryService for consume_item
        self.book_service.set_inventory_service(self.inventory_service) # BookService needs InventoryService for create_book_item, etc.

        print(f"InventoryHouseManager initialized. Current room ID: {self._state_store.get_state_section('current_room_id')}")

    # --- Facade Methods (Public API of InventoryHouseManager) ---
    # These methods will now simply delegate to the appropriate service.
    # This makes InventoryHouseManager a thin orchestrator.

    def get_sim_state(self):
        return self.simulation_state_service.get_sim_state()

    def set_sim_state(self, id_value=None, sim_current_step=None):
        return self.simulation_state_service.set_sim_state(id_value, sim_current_step)

    def add_item_description(self, item_id: int, new_description: str) -> str:
        return self.inventory_service.add_item_description(item_id, new_description)

    def get_room_name(self, room_id: int) -> str:
        return self.room_manager.get_room_name(room_id)

    def get_current_room_id(self):
        return self.room_manager.get_current_room_id()

    def get_current_room_name(self):
        return self.room_manager.get_current_room_name()

    def set_current_room(self, room_id: int):
        return self.room_manager.set_current_room(room_id)

    def get_current_room_description(self):
        return self.room_manager.get_current_room_description()

    def list_items_in_current_room(self, internal=False):
        return self.inventory_service.list_items_in_current_room(internal)

    def get_inventory_items(self, internal=False):
        return self.inventory_service.get_inventory_items(internal)

    def get_item_details(self, item_id: int, internal=False):
        return self.inventory_service.get_item_details(item_id, internal)

    def is_inventory_full(self):
        return self.inventory_service.is_inventory_full()

    def pickup_item(self, item_id: int, quantity_to_pickup: int = 1):
        return self.inventory_service.pickup_item(item_id, quantity_to_pickup)

    def list_inventories(self, formatted=False):
        return self.inventory_service.list_inventories(formatted=formatted)

    def drop_item(self, item_id: int, quantity_to_drop: int = 1):
        return self.inventory_service.drop_item(item_id, quantity_to_drop)

    def create_item(self, target_location: str, target_location_id: int | None, item_creation_data: dict | list[dict], internal=False, quantity=1):
        return self.inventory_service.create_item(target_location, target_location_id, item_creation_data, internal, quantity)

    def trash_item(self, item_id: int, confirm: bool) -> str:
        return self.inventory_service.trash_item(item_id, confirm)

    def remove_item(self, item_id: int, internal=False):
        return self.inventory_service.remove_item(item_id, internal)

    def get_all_rooms(self):
        return self.room_manager.get_all_rooms()

    def get_current_emote(self, internal: bool = False) -> str | dict:
        return self.pet_state_manager.get_current_emote(internal)

    def get_possible_emotes(self, internal: bool = False) -> dict | str:
        return self.pet_state_manager.get_possible_emotes(internal)

    def set_current_emote(self, emote_name: str, internal: bool = False) -> str | bool:
        return self.pet_state_manager.set_current_emote(emote_name, internal)

    def create_book_item(self, book_name: str, description: str) -> str:
        return self.book_service.create_book_item(book_name, description)

    def list_inventory_books(self, internal=False) -> str | list[dict]:
        return self.book_service.list_inventory_books(internal)

    def list_book_chapters(self, book_item_id: int) -> str:
        return self.book_service.list_book_chapters(book_item_id)

    def read_book_chapter(self, book_item_id: int, chapter_title: str) -> str:
        return self.book_service.read_book_chapter(book_item_id, chapter_title)

    def add_book_chapter(self, book_item_id: int, chapter_title: str, content: str) -> str:
        return self.book_service.add_book_chapter(book_item_id, chapter_title, content)

    def update_book_chapter(self, book_item_id: int, chapter_title: str, new_content: str) -> str:
        return self.book_service.update_book_chapter(book_item_id, chapter_title, new_content)

    def delete_book_chapter(self, book_item_id: int, chapter_title: str) -> str:
        return self.book_service.delete_book_chapter(book_item_id, chapter_title)

    def get_stats(self, internal: bool = False) -> str | dict:
        return self.stat_tracker.get_stats(internal)

    def adjust_stat(self, stat_name: str, amount: int|float) -> str | int | float:
        return self.stat_tracker.adjust_stat(stat_name, amount)

    def consume_item(self, item_id: int) -> str:
        return self.stat_tracker.consume_item(item_id)

    def get_pet_color(self) -> tuple[int, int, int] | None:
        return self.pet_state_manager.get_pet_color()

    def set_pet_color(self, color: tuple[int, int, int]):
        return self.pet_state_manager.set_pet_color(color)

    def is_color_configured(self) -> bool:
        return self.pet_state_manager.is_color_configured()

    def set_color_configured(self, configured: bool):
        return self.pet_state_manager.set_color_configured(configured)

    def get_steps(self) -> int:
        return self.pet_state_manager.get_steps()

    def set_steps(self, count: int):
        return self.pet_state_manager.set_steps(count)

    def add_steps(self, amount: int):
        return self.pet_state_manager.add_steps(amount)

    def save_state(self) -> None:
        """Delegates to the StateStore to save the current state."""
        self._state_store.save_state()
        print("State saved successfully.")

