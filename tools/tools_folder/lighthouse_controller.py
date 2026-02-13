from tools.tools_folder.tools_helpers.lighthouse.lighthouse_state_manager import LighthouseManager

from inventory_items.items_provider.item_store import ItemStore


import random

# TODO: Add popup signals to all methods

# --- Helper method to be added to each room class ---
def _send_signal(self, signal_data):
    """Helper method to send signals using the registered callback."""
    if self._signal_callback:
        # print(f"{self.__class__.__name__} signaling: {signal_data}") # Optional: uncomment for debug
        try:
            self._signal_callback(signal_data)
        except Exception as e:
            print(f"Error sending signal from {self.__class__.__name__}: {e}")
    else:
        # print(f"{self.__class__.__name__} attempted to signal, but no callback registered: {signal_data}") # Optional: uncomment for debug
        pass # Silently fail if no callback is registered, or log loudly
# ------------------------------------------------------

AIR_STROKE_COSTS = {
    "energy": -0.030,
    "hydration": -0.05,
    "fullness": -0.020
}

KEROSENE_REFILL_COSTS = {
    "energy": -0.25,
    "hydration": -0.25
}

MANTLE_INSTALL_COSTS = {
    "energy": -0.10,
    "hydration": -0.15
}

LIQUID_SPRAY_COSTS = {
    "energy": -0.45,
    "hydration": -0.40,
    "fullness": -0.40  # Kerosene exposure is bad!
}

WIND_UP_RATE = .005 # of max 1.0

WIND_UP_COSTS = {
    "energy": -0.025,
    "hydration": -0.015,
    "fullness": -0.010
}

CLEAN_LENS_COSTS = {
    "energy": -0.025,
    "hydration": -0.015,
    "fullness": -0.010
}

OIL_MECHANISM_COSTS = {
    "energy": -0.010,
    "hydration": -0.008,
    "fullness": -0.005
}

OIL_PUMP_RATE = .005 # of max 1.0

SPIRIT_CONSUME_RATE = .05

class LighthouseController:
    def __init__(self, state_manager, signal, open_meteo_handle):
        self.state_manager = state_manager
        self._signal_callback = signal

        self.item_store = ItemStore()

        self.lighthouse_manager = LighthouseManager(state_manager, open_meteo_handle)
        self._send_signal = _send_signal # Assign the common helper function

    def _adjust_stats(self, cost_dict, mult=1):  
        responses = []
        for stat in cost_dict:
            cost_calc = cost_dict[stat] * mult  
            self.state_manager.adjust_stat(stat, cost_calc)  
            stats_effect = f"{stat.capitalize()} decreased by {abs(round(cost_calc, 2))}."
            responses.append(stats_effect)
        return "\n".join(responses)

    ## Service Room Actions

    def IOV_pump_air(self, strokes) -> str:
        text_results = []
        response, events, success = self.lighthouse_manager.pump_air(strokes, internal=True)
        # NO NEGATIVE STROKES ALLOWED
        if strokes < 0:
            return "Not how air pumps work, you lovely thing."

        # print(f"DEBUG: response type: {type(response)}, value: {repr(response)}")
        # print(f"DEBUG: events type: {type(events)}, value: {repr(events)}")

        text_results.append(response)
        event_messages = [e.message for e in events]
        text_results.append(", ".join(event_messages))

        if success:
            stats_res = self._adjust_stats(AIR_STROKE_COSTS, strokes)
            text_results.append(stats_res)
        # TODO: add signal for icon popups

        return "\n".join(text_results)

    def IOV_kerosene_refill(self, kerosene_id): # adjust add_fuel to return a dict with message and 'solution' key for knowing if the action was successful or not
        item_check_result = self.state_manager.validate_item_data(kerosene_id, "kerosene_container", "inventory")  

        if item_check_result == False:
            return "You don't have any Kerosene container in your inventory."

        result_messages = []
        fuel_message, events = self.lighthouse_manager.add_fuel(0.5)

        result_messages.append(fuel_message)
        event_messages = [e.message for e in events]
        result_messages.append(", ".join(event_messages))
        self.state_manager.remove_item(kerosene_id)
        stat_res = self._adjust_stats(KEROSENE_REFILL_COSTS)
        result_messages.append(stat_res)
        # TODO: add signal for icon popups

        return "\n".join(result_messages)


    ## Lantern Room Actions

    def clean_outside_panes(self, rag_id, strokes=10):

        # check for cleaning rag
        item_check_result = self.state_manager.validate_item_data(rag_id, "cleaning_rag", "inventory")  

        if item_check_result == False:
            return "You don't have any cleaning rag in your inventory."

        
        min_range = 0.001
        max_range = 0.005
        amount = float(random.uniform(min_range, max_range))
        response = self.lighthouse_manager.clean_wp(amount*strokes)
        stats_res = self._adjust_stats(CLEAN_LENS_COSTS, strokes)
        return "\n".join([response, stats_res])

    def clean_condensation(self, rag_id, strokes=10):

        # check for cleaning rag
        item_check_result = self.state_manager.validate_item_data(rag_id, "cleaning_rag", "inventory")  

        if item_check_result == False:
            return "You don't have any cleaning rag in your inventory."

        min_range = 0.001
        max_range = 0.005
        amount = float(random.uniform(min_range, max_range))

        response = self.lighthouse_manager.clean_condensation(amount*strokes)
        stats_res = self._adjust_stats(CLEAN_LENS_COSTS, strokes)
        return "\n".join([response, stats_res])

    def place_sheet(self, sheet_id):
        item_check_result = self.state_manager.validate_item_data(sheet_id, "sheet", "inventory")  

        if item_check_result == False:
            return "You don't have any sheet in your inventory."

        sheet_message, events, success = self.lighthouse_manager.place_sheet(internal=True)
        if success:
            # remove sheet from inventory
            report = self.state_manager.remove_item(sheet_id)
        return "\n".join([sheet_message, report])

    def remove_sheet(self):
        # return sheet item
        sheet_message, events, success = self.lighthouse_manager.remove_sheet(internal=True)
        if success:
            item_data = self.item_store.get_item("Window curtains") # This is not tracking the item, and returns a transmuted item instead of the original item
            report = self.state_manager.create_item("inventory", None, item_data)

        return "\n".join([sheet_message, report])

    # Lantern Clockwork Actions

    def windup_clockwork(self, turns: int = 10):
        if turns < 0:
            return "Nope, can't do that. The handle won't give that way."

        results = []

        results.append(f"You spin the handle of the clockwork {turns} times.")

        value = float(turns * WIND_UP_RATE)
        stats_res = self._adjust_stats(WIND_UP_COSTS, turns)
        response = self.lighthouse_manager.windup_clockwork(value)
        results.append(response)
        results.append(stats_res)
        return "\n".join(results)


    ## IOV Lamp Actions

    ### Spirit Pan 
    
    def lamp_place_spirit_pan(self, spirit_pan_id): # adjust place_spirit_pan to return a dict with message and 'solution' key for knowing if the action was successful or not
        text_results = []
        item_check_result = self.state_manager.validate_item_data(spirit_pan_id, "iov_spirit_pan", "inventory")  

        if item_check_result == False:
            return "You don't have any Spirit Pan in your inventory."

        spirit_pan_details, error_message = self.state_manager.inventory_service.get_validated_item_data(spirit_pan_id, "iov_spirit_pan")

        if error_message:
            return error_message

        if spirit_pan_details.get("filled") == False:
            return "Please re-fill the spirit pan with spirit before placing it in the IOV lamp."

        response, events, success = self.lighthouse_manager.place_spirit_pan(internal=True)
            
        text_results.append(response)
        event_messages = [e.message for e in events]
        text_results.append(", ".join(event_messages))

        if success:
            report = self.state_manager.remove_item(spirit_pan_id)
            text_results.append(f"Placed spirit pan! Spirit pan consumed.")
            text_results.append(report)
        # TODO: add signal for icon popups

        return "\n".join(text_results)

    def lamp_refill_spirit_pan(self, spirit_pan_id, spirit_source_id): 
        text_results = []
        item_check_result = self.state_manager.validate_item_data(spirit_pan_id, "iov_spirit_pan", "inventory")  

        spirit_source_inventory_result = self.state_manager.validate_item_data(spirit_source_id, "spirit_source", "inventory")
        spirit_source_room_result = self.state_manager.validate_item_data(spirit_source_id, "spirit_source", "room")

        if spirit_source_inventory_result == False and spirit_source_room_result == False:
            return "You don't have any Spirit Source in your inventory or room."


        if item_check_result == False:
            return "You don't have any Spirit Pan in your inventory."

        spirit_pan_details, error_message = self.state_manager.inventory_service.get_validated_item_data(spirit_pan_id, "iov_spirit_pan")

        denatured_alcohol_details, error_message = self.state_manager.inventory_service.get_validated_item_data(spirit_source_id, "spirit_source")

        if denatured_alcohol_details["spirit_quantity"] == 0:
            return "The denatured alcohol container is empty."
        

        denatured_alcohol_details["spirit_quantity"] -= SPIRIT_CONSUME_RATE
        text_results.append(f"Spirit source consumed {SPIRIT_CONSUME_RATE} units of spirit. {denatured_alcohol_details['spirit_quantity']:.0%} units remaining.")
        
        if denatured_alcohol_details["spirit_quantity"] < 0:
            denatured_alcohol_details["spirit_quantity"] = 0
            flag, message = self.state_manager.remove_item(spirit_source_id, internal=True)
            text_results.append("Spirit source has been consumed entirely!")
            text_results.append(message)
            

        error_message = self.state_manager.inventory_service.persist_item_changes(spirit_source_id)

        if error_message:
            return error_message

        if spirit_pan_details.get("filled") == True:
            return "This spirit pan is already filled with spirit."

        spirit_pan_details["filled"] = True

        error_message = self.state_manager.inventory_service.persist_item_changes(spirit_pan_id)

        if error_message:
            return error_message
        # TODO: add signal for icon popups

        return "Spirit pan refilled." + "\n".join(text_results)

    def lamp_remove_spirit_pan(self):
        text_results = []
        response, pan_state, events, success = self.lighthouse_manager.remove_spirit_pan(internal=True)
        text_results.append(response)

        if success:
            item_data = self.item_store.get_item("IOV Spirit Pan")
            item_data["filled"] = True if pan_state == "full" else False
            report = self.state_manager.create_item("inventory", None, item_data)
            text_results.append(report)
    
        # TODO: add signal for icon popups

        return "\n".join(text_results)
        
    ### Mantle Actions

    def lamp_light_install_mantle(self, mantle_id): # adjust install_mantle to return a dict with message and 'solution' key for knowing if the action was successful or not
        text_results = []
        item_check_result = self.state_manager.validate_item_data(mantle_id, "iov_mantle", "inventory")

        if item_check_result == False:
            return "You don't have any IOV Mantle in your inventory."

        response, events, success = self.lighthouse_manager.install_mantle(internal=True) 
        text_results.append(response)

        if success:
            report = self.state_manager.remove_item(mantle_id)
            text_results.append(report)
            stats_res = self._adjust_stats(MANTLE_INSTALL_COSTS)
            text_results.append(stats_res)
        # TODO: add signal for icon popups

        return "\n".join(text_results)

    def remove_mantle(self):
        messages = []
        response, was_fabric, events, success = self.lighthouse_manager.remove_mantle(internal=True)
        messages.append(response)
        if success:
            if was_fabric:
                report = self.state_manager.create_item("inventory", None, self.item_store.get_item("IOV Mantle"))
                if report:
                    messages.append(report)
            else:
                report = "No item returned."
                messages.append(report)
        # TODO: add signal for icon popups

        return "\n".join(messages)

    ### 

    def open_valve(self, amount: float = 0.5) -> str:
        responses=[]
        result = self.lighthouse_manager.open_valve(amount)
        if result:
            responses.append(result)

        hazards = self.lighthouse_manager.get_all_hazards()

        lamp_hazard = hazards["lamp"]

        if lamp_hazard["is_hazardous"]:
            # Apply immediate penalty
            hazard = lamp_hazard["hazard_level"]
            stats_res = self._adjust_stats(LIQUID_SPRAY_COSTS, hazard)
            
            responses.append(stats_res)

    
    
        return "\n".join(responses)

    def lamp_ignite_vapor(self, light_source_id):
        text_results = []
        item_check_result = self.state_manager.validate_item_data(light_source_id, "hand_fire_source", "inventory")

        if item_check_result == False:
            return "You don't have any Hand Fire Source in your inventory."

        response = self.lighthouse_manager.ignite_vapor()

        if response:
            text_results.append(response)
        # TODO: add signal for icon popups

        return "\n".join(text_results)
        
    def lamp_light_spirit_pan(self, fire_source_id):
        text_results = []
        item_check_result = self.state_manager.validate_item_data(fire_source_id, "hand_fire_source", "inventory")

        if item_check_result == False:
            return "You don't have any Hand Fire Source in your inventory."

        response = self.lighthouse_manager.light_spirit_pan()
        if response:
            text_results.append(response)
        # TODO: add signal for icon popups

        return "\n".join(text_results)


    # Oil Mechanism
    def controller_oil_mechanism(self, pumps: int = 1, oiler_id: str = None):
        text_results = []
        # check for "oiler set" in inventory
        item_check_result = self.state_manager.validate_item_data(oiler_id, "oiler_set", "inventory")
        if item_check_result == False:
            return "You don't have any Oiler Set in your inventory."

        amount = pumps * OIL_PUMP_RATE

        response, events, success = self.lighthouse_manager.oil_mechanism(amount, internal=True)
        text_results.append(response)

        if success:
            text_results.append(f"You oil the clockwork mechanism {pumps} time{'s' if pumps != 1 else ''}.")
            stats_res = self._adjust_stats(OIL_MECHANISM_COSTS, pumps)
            text_results.append(stats_res)
            # TODO: add signal for icon popups

        return "\n".join(text_results)

    def examine_spirit_source(self, spirit_source_id):
        inventory_item_check_result = self.state_manager.validate_item_data(spirit_source_id, "spirit_source", "inventory")
        room_item_check_result = self.state_manager.validate_item_data(spirit_source_id, "spirit_source", "room")

        if inventory_item_check_result == False and room_item_check_result == False:
            return "Could not find the item in your inventory or room."

        item_data, error = self.state_manager.inventory_service.get_validated_item_data(spirit_source_id, "spirit_source")


        return f"You examine the {item_data['name']} ID {item_data['id']}. {item_data['descriptions']} Spirit Contents: {item_data['spirit_quantity']:.0%}"
        

    def service_room_light_check(self):
        # If we are inside the service room, we should be able to see the light state.
        light_state = self.lighthouse_manager.lamp.get_light_state()

        return light_state


    def get_lantern_room_interior_status(self):
        lines = []
        lines.append(self.lighthouse_manager.lantern.get_interior_status())
        lines.append(self.lighthouse_manager.lamp.get_light_state())
        return "\n".join(lines)
    
    ## Tick!
   
    
    def lighthouse_tick(self):
        """Handle lighthouse tick and return any player-facing messages."""
        responses = []
        
        # Get tick messages from lighthouse manager
        tick_messages = self.lighthouse_manager.tick()

        hazards = self.lighthouse_manager.get_all_hazards()

        lamp_hazard = hazards["lamp"]

        if lamp_hazard["is_hazardous"]:
            # Apply immediate penalty
            hazard = lamp_hazard["hazard_level"]
            stats_res = self._adjust_stats(LIQUID_SPRAY_COSTS, hazard)
            
            responses.append(stats_res)

        

        
        return "\n".join(responses)