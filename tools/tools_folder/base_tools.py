# Base tools, agent tooling for its own state.
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


    def add_item_description(self, item_id: int, new_description: str) -> str: 
        item_search = self.state_manager.find_item(item_id)
        if not item_search.success:
            return item_search.error_message
        item_data_copy = item_search.item_data # This is a deep copy, so we can modify it directly without corrupting state
        new_descs = item_data_copy["descriptions"] + [new_description]

        item_edit = self.state_manager.set_item_attribute(item_id, "descriptions", new_descs)
        
        if not item_edit.success:
            return item_edit.error_message
        message = f"Added description to item {item_id}: {new_description}, {item_edit.message}"
        return message


    def drop_item(self, item_id: int, quantity_to_drop: int = 1):
        return self.state_manager.inventory_service.drop_item(item_id, quantity_to_drop) # Bypassing facade, not sure what to do about it

    def pick_up_item(self, item_id: int, quantity_to_pickup: int = 1):
        return self.state_manager.inventory_service.pickup_item(item_id, quantity_to_pickup) # Bypassing facade, not sure what to do about it

    def set_current_emote(self, emote_name: str) -> str:
        return self.state_manager.pet_state_manager.set_current_emote(emote_name)

    def emit_inner_thought(self, context, thought):
        """
        Emits a quick, ephemeral reflection or thought about the current or upcoming action.
        Used for internal reasoning, questioning, or subtle judgment.

        Args:
            thought (str): A brief, freeform inner thought.
            context (str): Short description of what this thought refers to.
        """
        # Returning it to the AI is the main purpose of this function.
        return f"Inner Thought - Context: {context}, Thought: {thought}"