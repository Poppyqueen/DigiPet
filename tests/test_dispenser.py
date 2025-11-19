# tests/test_dispenser.py
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.tools_folder.dispenser_tools import DispenserTools

# Mock Classes
class MockStateStore:
    def __init__(self, items):
        self.items = items # Dict of ID -> Item Data
        self.inventory = []
        self.rooms = [{"id": 1, "name": "Living Room", "items": []}]

    def get_state_section(self, section, default=None):
        if section == "inventory":
            return self.inventory
        if section == "rooms":
            return self.rooms
        return default

    def update_state_section(self, section, data):
        if section == "inventory":
            self.inventory = data
        elif section == "rooms":
            self.rooms = data
        print(f"State updated for section: {section}")

class MockInventoryService:
    def __init__(self, state_store):
        self._state_store = state_store

    def _find_item_info_by_id(self, item_id):
        # Search inventory
        for item in self._state_store.inventory:
            if item["id"] == item_id:
                return {"location": "inventory", "item_data": item}
        
        # Search rooms
        for room in self._state_store.rooms:
            for item in room["items"]:
                if item["id"] == item_id:
                    return {"location": "room", "item_data": item}
        return None

class MockInventoryHouseManager:
    def __init__(self):
        # Initial Data
        self.dispenser_data = {
            "id": 1,
            "name": "Candy Dispenser",
            "type": ["furniture", "dispenser"],
            "descriptions": ["A retro dispenser.", "Status: 0 candies left"],
            "candy_count": 0,
            "static": True
        }
        self.refill_bag_data = {
            "id": 2,
            "name": "Candy Refill Bag",
            "type": ["consumable", "misc"],
            "static": False
        }
        
        self._state_store = MockStateStore({})
        # Place dispenser in room
        self._state_store.rooms[0]["items"].append(self.dispenser_data)
        # Place refill bag in inventory
        self._state_store.inventory.append(self.refill_bag_data)
        
        self.inventory_service = MockInventoryService(self._state_store)

    def get_inventory_items(self, internal=False):
        return self._state_store.inventory

    def remove_item(self, item_id, internal=False):
        print(f"Removing item ID: {item_id}")
        self._state_store.inventory = [i for i in self._state_store.inventory if i["id"] != item_id]
        return True

    def create_item(self, location, location_id, item_data, internal=False):
        print(f"Creating item: {item_data.get('name')}")
        # Mock creation
        new_item = item_data.copy()
        new_item["id"] = 99
        self._state_store.inventory.append(new_item)
        return [new_item]

def test_dispenser():
    manager = MockInventoryHouseManager()
    # Mock ItemStore in DispenserTools to avoid file loading
    tools = DispenserTools(manager)
    
    # Mock the item_store.get_item method
    class MockItemStore:
        def get_item(self, name):
            if name == "Single Candy":
                return {"name": "Single Candy", "type": ["consumable"]}
            return None
    tools.item_store = MockItemStore()

    print("--- Test 1: Dispense from empty ---")
    result = tools.dispense_candy(1)
    print(result)
    assert "empty" in result

    print("\n--- Test 2: Refill ---")
    result = tools.refill_dispenser(1)
    print(result)
    assert "pour the bag" in result
    
    # Verify state update
    dispenser = manager._state_store.rooms[0]["items"][0]
    print(f"Candy count after refill: {dispenser['candy_count']}")
    assert dispenser['candy_count'] == 10
    assert "Status: 10 candies left" in dispenser['descriptions']

    print("\n--- Test 3: Dispense from full ---")
    result = tools.dispense_candy(1)
    print(result)
    assert "candy falls out" in result
    
    # Verify state update
    dispenser = manager._state_store.rooms[0]["items"][0]
    print(f"Candy count after dispense: {dispenser['candy_count']}")
    assert dispenser['candy_count'] == 9
    assert "Status: 9 candies left" in dispenser['descriptions']

if __name__ == "__main__":
    test_dispenser()
