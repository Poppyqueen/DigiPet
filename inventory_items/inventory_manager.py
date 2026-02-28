
# inventory_house_manager.py (UPDATED)

# Import the new StateStore
from inventory_items.services.state_store import StateStore

# Import the new service classes (will be created in subsequent steps)
from inventory_items.services.inventory_service import InventoryService
from inventory_items.services.room_manager import RoomManager
#from inventory_items.services.book_service import BookService # This has been moved to the tools folder
from inventory_items.services.stat_tracker import StatTracker # This will replace the old stats_component
from inventory_items.services.pet_state_manager import PetStateManager


from inventory_items.base_state_manager.base_state_config import InitialStateConst

from typing import Literal

class InventoryHouseManager: # NO LONGER INHERITS FROM GenericJsonTool
    MAX_INVENTORY_SLOTS = 30 # This constant can stay here or move to InventoryService

    def __init__(self, base_path, signal=None, config_manager=None):
        self.base_path = base_path
        self._signal_callback = signal
        self.config_manager = config_manager
        self.initial_state_manager=InitialStateConst()

        # 1. Determine the initial state to load

        selected_state_name = config_manager.get_config("game_settings", "initial_state")

        availiable_configs = self.initial_state_manager.states_configs

        available_states=[]
        for i in availiable_configs:
            available_states.append(i)

        for i in available_states:
            if i == selected_state_name:
                selected_state=self.initial_state_manager.create_state(i)


        #selected_state = available_states.get(selected_state_name, self.initial_state_manager.create_state("base_state")) # Fallback if name not found

        # 2. Initialize the central StateStore
        #print(f"DEBUG INVENTORY MANAGER INIT: Initializing StateStore with {selected_state_name}")
        self._state_store = StateStore(base_path, selected_state)

        # 3. Initialize all services, passing StateStore and signal_callback
        # Order services to minimize immediate circular dependency issues, resolve later
        self.inventory_service = InventoryService(self._state_store, self._signal_callback)
        self.room_manager = RoomManager(self._state_store, self._signal_callback)
        self.stat_tracker = StatTracker(self._state_store, self._signal_callback)
        self.pet_state_manager = PetStateManager(self._state_store, self._signal_callback)

        # 4. Resolve explicit circular dependencies or cross-service references
        self.inventory_service.set_room_manager(self.room_manager)
        self.room_manager.set_inventory_service(self.inventory_service) # TODO: Can we resolve this circular dependency?

        # self.stat_tracker.set_inventory_service(self.inventory_service) # StatTracker needs InventoryService for consume_item
        #self.book_service.set_inventory_service(self.inventory_service) # BookService needs InventoryService for create_book_item, etc.

        print(f"InventoryHouseManager initialized. Current room ID: {self._state_store.get_state_section('current_room_id')}")

    # --- Facade Methods (Public API of InventoryHouseManager) ---
    # These methods will now simply delegate to the appropriate service.
    # This makes InventoryHouseManager a thin orchestrator.

    def add_item_description(self, item_id: int, new_description: str) -> str: # this is a tool move to tools folder
        return self.inventory_service.add_item_description(item_id, new_description)

    def get_room_name(self, room_id: int) -> str:
        return self.room_manager.get_room_name(room_id)

    def get_current_room_id(self):
        return self.room_manager.get_current_room_id()

    def get_current_room_name(self):
        return self.room_manager.get_current_room_name()

    def set_current_room(self, room_id: int | float | str):
        room_id = int(room_id)
        return self.room_manager.set_current_room(room_id)

    def get_current_room_description(self):
        return self.room_manager.get_current_room_description()

    def list_items_in_current_room(self, internal=False): # TODO: Remove internal flag, and return standard object
        return self.inventory_service.list_items_in_current_room(internal)

    def get_inventory_items(self, internal=False): # TODO: Remove internal flag, and return standard object
        return self.inventory_service.get_inventory_items(internal)

    def pickup_item(self, item_id: int, quantity_to_pickup: int = 1):
        return self.inventory_service.pickup_item(item_id, quantity_to_pickup)

    def list_inventories(self, formatted=False): # TODO: Remove flag, and return standard object, change all interactions with it
        return self.inventory_service.list_inventories(formatted=formatted)

    def drop_item(self, item_id: int, quantity_to_drop: int = 1):
        return self.inventory_service.drop_item(item_id, quantity_to_drop)

    def trash_item(self, item_id: int, confirm: bool) -> str: # TODO: Move to a tooling system model, however, it is not used in game
        return self.inventory_service.trash_item(item_id, confirm)

    def get_all_rooms(self):
        return self.room_manager.get_all_rooms()

    def get_current_emote(self, internal: bool = False) -> str | dict:# TODO: None of the methods that call this use the internal flag
        return self.pet_state_manager.get_current_emote(internal)

    def get_possible_emotes(self, internal: bool = False) -> dict | str: # TODO: None of the methods that call this use the internal flag
        return self.pet_state_manager.get_possible_emotes(internal)

    def set_current_emote(self, emote_name: str, internal: bool = False) -> str | bool: # TODO: None of the methods that call this use the internal flag
        return self.pet_state_manager.set_current_emote(emote_name, internal)

    def get_stats(self, internal: bool = False) -> str | dict: # TODO: Remove flag, and return standard object, change all interactions with it
        return self.stat_tracker.get_stats(internal)

    def adjust_stat(self, stat_name: str, amount: int|float) -> str | int | float:
        return self.stat_tracker.adjust_stat(stat_name, amount)

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



    # Public Methods verified for tools and services use.

    def find_item(
        self,
        item_id: int,
        required_type: str | None = None,
        required_location: Literal["inventory", "room", "accessible"] | None = None,
    ):
        return self.inventory_service.find_item(item_id=item_id,required_type=required_type,required_location=required_location)

    def set_item_attribute(self,
    item_id: int, key: str, value, quantity: int = 1,
                           path: list[str] | None = None

    ):
        return self.inventory_service.set_item_attribute(item_id=item_id,key=key,value=value,quantity=quantity, path=path)
    ###

    def remove_item(self, item_id: int, quantity: int = 1):
        return self.inventory_service.remove_item(item_id, quantity)

    def create_item( 
        self,
        target_location: str,
        target_location_id: int | None,
        item_creation_data: dict | list[dict],
        quantity: int = 1,
        fallback_to_room: bool = True,
    ):
        return self.inventory_service.create_item(target_location, target_location_id, item_creation_data, quantity, fallback_to_room)