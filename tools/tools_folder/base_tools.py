# Add other base tools here

class BaseTools:
    def __init__(self, state_manager):
        self.state_manager = state_manager

    def list_items_in_current_room(self):
        items_state = self.state_manager.get_inventory_state()
        agent_response = items_state.room_summary
        return agent_response

    def list_items_in_inventory(self):
        items_state = self.state_manager.get_inventory_state()
        agent_response = items_state.inventory_summary
        return agent_response
        