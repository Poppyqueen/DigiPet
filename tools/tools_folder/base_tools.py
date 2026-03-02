# Base tools,
# Unique case for tools, some are bypassing the facade, do not do this in general tools
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager

class BaseTools:
    def __init__(self, state_manager: InventoryHouseManager): # No quotes needed now
        self.state_manager = state_manager

    def list_items_in_current_room(self):
        items_state = self.state_manager.get_inventory_state()
        agent_response = items_state.room_summary
        return agent_response

    def list_items_in_inventory(self):
        items_state = self.state_manager.get_inventory_state()
        agent_response = items_state.inventory_summary
        return agent_response
        
    def get_all_rooms(self):
        rooms = self.state_manager.get_all_rooms_data()
        summary = f"Available rooms: {', '.join(f'{r.name} (ID:{r.id:06d})' for r in rooms)}"
        return summary

    def drop_item(self, item_id: int, quantity_to_drop: int = 1):
        return self.state_manager.inventory_service.drop_item(item_id, quantity_to_drop) # Bypassing facade, not sure what to do about it

    def pick_up_item(self, item_id: int, quantity_to_pickup: int = 1):
        return self.state_manager.inventory_service.pickup_item(item_id, quantity_to_pickup) # Bypassing facade, not sure what to do about it

    def set_current_emote(self, emote_name: str) -> str:
        return self.state_manager.pet_state_manager.set_current_emote(emote_name)
