
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

# Results
from inventory_items.services.return_objects import (
    RoomDataResult,
    ItemLookupResult,
    ItemCreationResult,
    ItemRemovalResult,
    SetItemAttributeResult,
    InventoryStateResult,
)

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


    def get_stats(self, internal: bool = False) -> str | dict: # TODO: Remove flag, and return standard object, change all interactions with it
        return self.stat_tracker.get_stats(internal)

    def get_steps(self) -> int:
        return self.pet_state_manager.get_steps()

    def set_steps(self, count: int):
        return self.pet_state_manager.set_steps(count)

    def add_steps(self, amount: int):
        return self.pet_state_manager.add_steps(amount)

    def save_state(self) -> None:
        """Delegates to the StateStore to save the current state.""" # Only used for shutdown
        self._state_store.save_state()
        print("State saved successfully.")


    # Needs changes:
    # Remove internal flag
    # TODO: Return a standard object instead of a string? 
    def get_current_emote(self) -> str:
        return self.pet_state_manager.get_current_emote()

    def get_possible_emotes(self) -> str: 
        return self.pet_state_manager.get_possible_emotes()

    # Moved to base tools
    # def set_current_emote(self, emote_name: str) -> str: 
    #     return self.pet_state_manager.set_current_emote(emote_name)


    # AI agent using these methods as tools, maybe move them? or something they are sending signals to the room manager
    # Not used as API methods but moved to base tools with direct access...

    # Moved to base tools, not supposed to be state API methods
    # def drop_item(self, item_id: int, quantity_to_drop: int = 1):
    #     return self.inventory_service.drop_item(item_id, quantity_to_drop)

    # def pickup_item(self, item_id: int, quantity_to_pickup: int = 1):
    #     return self.inventory_service.pickup_item(item_id, quantity_to_pickup)

    # def get_all_rooms(self): # not sending signals, that's fine, just documenting
    #     return self.room_manager.get_all_rooms()

    # Moved methods above to base tools, however, the ones bellow I decided to keep here, someone might want to use them in the API for their own tools? It hasn't happened yet.
    def add_item_description(self, item_id: int, new_description: str) -> str: 
        return self.inventory_service.add_item_description(item_id, new_description)

    def set_current_room(self, room_id: int | float | str):
        room_id = int(room_id)
        return self.room_manager.set_current_room(room_id)



    # Public Methods verified for tools and services use.
    def adjust_stat(self,
        stat_name: str, 
        amount: int|float
    ) -> str: # Maybe create return model for this?
        """
        Adjusts a single stat by the given amount.

        Parameters
        ----------
        stat_name : str
            The name of the stat to adjust (e.g., "fullness", "hydration", "energy").
            Case-insensitive and whitespace-stripped.
        amount : int | float
            The amount to adjust the stat by. Positive values increase the stat,
            negative values decrease it.

        Returns
        -------
        str
            A message describing the result of the operation.
            Returns an error message if the stat does not exist, the amount is invalid,
            or the stats data is corrupted. Needs a return model.
        """
        return self.stat_tracker.adjust_stat(stat_name, amount)

    ### 
    def find_item(self,
        item_id: int,
        required_type: str | None = None,
        required_location: Literal["inventory", "room", "accessible"] | None = None,
    )-> ItemLookupResult:
        """
        Unified item lookup with optional filters.

        Parameters
        ----------
        item_id           : The integer ID of the item to find.
        required_type     : If given, the item's type list must include this string.
        required_location : Controls where the item is allowed to be:
                            None           → anywhere in the whole state
                            "inventory"    → must be in the player's inventory
                            "room"         → must be in any room
                            "accessible"   → must be in inventory OR the current room

        Returns
        -------
        ItemLookupResult
            Always returns this model.
            Check result.success before using result.item_data.
        """
        return self.inventory_service.find_item(item_id=item_id,required_type=required_type,required_location=required_location)

    def set_item_attribute(self,
        item_id: int, 
        key: str, 
        value,
        quantity: int = 1,
        path: list[str] | None = None

    )-> SetItemAttributeResult: # Fix this object
        """
        Modifies a single attribute (key/value) on one or more units of an item
        stack, then recalculates stacking state.

        If *path* is provided the write is applied at a nested location inside
        the item dict.  For example::

            set_item_attribute(id, "contents", new_dict, path=["dispenser_state"])

        writes ``item_data["dispenser_state"]["contents"] = new_dict`` instead
        of touching the top-level key directly.

        The stacking-fingerprint logic only considers the *top-level* key when
        path is None; when path is provided the fingerprint comparison uses the
        top-level segment (path[0]) so that nested writes on non-stacking keys
        remain fast-pathed correctly.

        Args:
            item_id:  The ID of the item (or stack) to modify.
            key:      The attribute key to set (at the leaf of *path*).
            value:    The new value for that attribute.
            quantity: How many units of the stack to affect.  Defaults to 1.
                      Pass 0 or a value >= available quantity to affect the whole stack.
            path:     Optional list of dict keys to traverse before setting *key*.
                      Intermediate dicts are created automatically if absent.

        Returns:
            A SetItemAttributeResult object.
        """
        return self.inventory_service.set_item_attribute(item_id=item_id,key=key,value=value,quantity=quantity, path=path)

    def remove_item(self, 
        item_id: int, 
        quantity: int = 1
    )-> ItemRemovalResult:
        """
        Removes one or more units of an item from wherever it currently is.

        Parameters
        ----------
        item_id  : The integer ID of the item to remove.
        quantity : How many units to remove. Pass 0 to remove the entire stack.
                Defaults to 1.

        Returns
        -------
        ItemRemovalResult
            Always returns this model — never a raw string or tuple.
            Check result.success before acting on failure.
            result.message is always safe to append to a parts list.
        """
        return self.inventory_service.remove_item(item_id, quantity)

    def create_item( self,
        target_location: str,
        target_location_id: int | None,
        item_creation_data: dict | list[dict],
        quantity: int = 1,
        fallback_to_room: bool = True,
    )-> ItemCreationResult:
        """
        Creates one or more items in the specified location.

        Parameters
        ----------
        target_location     : "inventory" or "room"
        target_location_id  : Room ID when target_location="room", else None
        item_creation_data  : A single item dict or a list of item dicts (templates)
        quantity            : How many of each template to create. Defaults to 1.
        fallback_to_room    : If True and inventory is full, place in current room instead.

        Returns
        -------
        ItemCreationResult
            Always returns this model — never a raw string or list.
            Check result.success before using result.created_ids.
            result.message is always safe to append to a parts list.
        """
        return self.inventory_service.create_item(target_location, target_location_id, item_creation_data, quantity, fallback_to_room)

    ### 
    def get_room_data(self, room_id: int) -> RoomDataResult:
        """
        Returns a RoomDataResult for any room by ID.
        Raises ValueError if the room is not found.
        """
        return self.room_manager.get_room_data(room_id)

    def get_current_room_data(self) -> RoomDataResult:
        """
        Returns a RoomDataResult for every room in state.
        Callers that need to filter by room_types, plot_number, etc.
        should do so on the returned list.
        """
        return self.room_manager.get_current_room_data()

    def get_all_rooms_data(self) -> list[RoomDataResult]:
        """
        Returns a RoomDataResult for every room in state.
        Callers that need to filter by room_types, plot_number, etc.
        should do so on the returned list.
        """
        return self.room_manager.get_all_rooms_data()

    # New method

    def get_inventory_state(self) -> InventoryStateResult:
        """
        Returns a fully-typed snapshot of the player inventory and current
        room items.
        """
        return self.inventory_service.get_inventory_state()
