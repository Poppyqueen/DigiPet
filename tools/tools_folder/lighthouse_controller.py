# lighthouse_controller.py
#*   **Lighthouse** A detailed IOV lamp and lantern room simulation. The agent acts as a lighthouse keeper, managing an incandescent oil vapor lamp system with physical pressure, fuel, temperature, and optics simulation. Features ambient perception — the agent passively receives state information (pressure levels, lamp status, lens condition) based on which room it occupies, without needing explicit observation actions.

from tools.tools_folder.tools_helpers.lighthouse.lighthouse_state_manager import LighthouseManager

from inventory_items.items_provider.item_store import ItemStore

from tools.tools_folder.tools_helpers.lighthouse.models import ActionInternalResponse


import random

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager # just for typing
    from inventory_items.services.return_objects import ItemLookupResult

# TODO: Add popup signals to all methods
# TODO: Add keys more in depth for items like the oiler, kerosene containers, hand_fire_source, etc.

# --- Helper method to be added to each room class ---
def _send_signal(self, signal_data):
    """Helper method to send signals using the registered callback."""
    if self._signal_callback:
        try:
            self._signal_callback(signal_data)
        except Exception as e:
            print(f"Error sending signal from {self.__class__.__name__}: {e}")
    else:
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

CLEAN_JET_COSTS = {
    "energy": -0.010,
    "hydration": -0.008,
    "fullness": -0.005
}

OIL_PUMP_RATE = .005 # of max 1.0

SPIRIT_CONSUME_RATE = .05

class LighthouseController:
    def __init__(self, state_manager, signal, open_meteo_handle, is_toolset_available, base_path: str = None):
        self.state_manager : InventoryHouseManager = state_manager
        self._signal_callback = signal

        self.item_store = ItemStore()
        self.is_toolset_available = is_toolset_available # New, method to check if a string matches a toolset or affordance block currently active based on the game state. 

        self.lighthouse_manager = LighthouseManager(open_meteo_handle, self.is_toolset_available, base_path)
        self._send_signal = _send_signal

    # --- Private Helpers ---

    def _adjust_stats(self, cost_dict, mult=1):
        responses = []
        for stat in cost_dict:
            cost_calc = cost_dict[stat] * mult
            self.state_manager.adjust_stat(stat, cost_calc)
            stats_effect = f"{stat.capitalize()} decreased by {abs(round(cost_calc, 2))}."
            responses.append(stats_effect)
        return "\n".join(responses)

    def _validate_inventory_item(self, item_id, item_type, friendly_name) -> str | None:
        result : ItemLookupResult = self.state_manager.find_item(item_id, required_type=item_type, required_location="inventory")
        if not result.success:
            return result.error

        return None

    def _collect_response(self, response_object: ActionInternalResponse, extra_lines: list = None) -> list:
        """Assembles a standard message list from an ActionInternalResponse."""
        parts = [response_object.message, response_object.formatted_events]
        if extra_lines:
            parts.extend(extra_lines)
        return [p for p in parts if p]  # filter empty strings/None

    def _apply_lamp_hazard(self) -> str:
        """Checks lamp hazard and applies stat costs if hazardous. Returns stat result string."""
        lamp_hazard = self.lighthouse_manager.get_all_hazards()["lamp"]
        if lamp_hazard["is_hazardous"]:
            return self._adjust_stats(LIQUID_SPRAY_COSTS, lamp_hazard["hazard_level"])
        return ""

    # --- Service Room Actions ---

    def open_air_service_valve(self) -> str:
        response_object: ActionInternalResponse = self.lighthouse_manager.open_air_service_valve()
        parts = self._collect_response(response_object)
        return "\n".join(parts)

    def close_air_service_valve(self) -> str:
        response_object: ActionInternalResponse = self.lighthouse_manager.close_air_service_valve()
        parts = self._collect_response(response_object)
        return "\n".join(parts)

    def open_main_valve(self) -> str:
        response_object: ActionInternalResponse = self.lighthouse_manager.open_main_valve()
        parts = self._collect_response(response_object)
        return "\n".join(parts)

    def close_main_valve(self) -> str:
        response_object: ActionInternalResponse = self.lighthouse_manager.close_main_valve()
        parts = self._collect_response(response_object)
        return "\n".join(parts)

    def IOV_pump_air(self, strokes) -> str:
        if strokes < 0:
            return "Not how air pumps work, you lovely thing."

        response_object: ActionInternalResponse = self.lighthouse_manager.pump_air(strokes)
        parts = self._collect_response(response_object)

        if response_object.success:
            parts.append(self._adjust_stats(AIR_STROKE_COSTS, strokes))
        # TODO: add signal for icon popups

        return "\n".join(parts)

    def IOV_kerosene_refill(self, kerosene_id) -> str:
        if err := self._validate_inventory_item(kerosene_id, "kerosene_container", "Kerosene container"):
            return err

        response_object: ActionInternalResponse = self.lighthouse_manager.add_fuel(0.5)
        parts = self._collect_response(response_object)

        if response_object.success:
            self.state_manager.remove_item(kerosene_id)
            parts.append(self._adjust_stats(KEROSENE_REFILL_COSTS))
        # TODO: add signal for icon popups

        return "\n".join(parts)

    # --- Lantern Room Actions ---

    def clean_outside_panes(self, rag_id, strokes=10) -> str:
        if err := self._validate_inventory_item(rag_id, "cleaning_rag", "cleaning rag"):
            return err

        amount = float(random.uniform(0.001, 0.005))
        response_object: ActionInternalResponse = self.lighthouse_manager.clean_wp(amount * strokes)
        parts = self._collect_response(response_object)

        if response_object.success:
            parts.append(self._adjust_stats(CLEAN_LENS_COSTS, strokes))

        return "\n".join(parts)

    def clean_condensation(self, rag_id, strokes=10) -> str:
        if err := self._validate_inventory_item(rag_id, "cleaning_rag", "cleaning rag"):
            return err

        amount = float(random.uniform(0.001, 0.005))
        response_object: ActionInternalResponse = self.lighthouse_manager.clean_condensation(amount * strokes)
        parts = self._collect_response(response_object)

        if response_object.success:
            parts.append(self._adjust_stats(CLEAN_LENS_COSTS, strokes))

        return "\n".join(parts)

    def place_sheet(self, sheet_id) -> str:
        if err := self._validate_inventory_item(sheet_id, "sheet", "sheet"):
            return err

        response_object: ActionInternalResponse = self.lighthouse_manager.place_sheet()
        parts = self._collect_response(response_object)

        if response_object.success:
            parts.append(self.state_manager.remove_item(sheet_id).message)

        return "\n".join(parts)

    def remove_sheet(self) -> str:
        response_object: ActionInternalResponse = self.lighthouse_manager.remove_sheet()
        parts = self._collect_response(response_object)

        if response_object.success:
            item_data = self.item_store.get_item("Window curtains")
            parts.append(self.state_manager.create_item("inventory", None, item_data).message)

        return "\n".join(parts)

    # --- Lantern Clockwork Actions ---

    def windup_clockwork(self, turns: int = 10) -> str:
        if turns < 0:
            return "Nope, can't do that. The handle won't give that way."

        response_object: ActionInternalResponse = self.lighthouse_manager.windup_clockwork(float(turns * WIND_UP_RATE))
        parts = self._collect_response(response_object)

        if response_object.success:
            parts.insert(0, f"You spin the handle of the clockwork {turns} times.")
            parts.append(self._adjust_stats(WIND_UP_COSTS, turns))

        return "\n".join(parts)

    # --- IOV Lamp Actions ---

    ### Spirit Pan

    def close_valve(self, amount: float = 0.5) -> str:
        response_object: ActionInternalResponse = self.lighthouse_manager.close_valve(amount)
        parts = self._collect_response(response_object)
        return "\n".join(parts)

        

    def lamp_place_spirit_pan(self, spirit_pan_id) -> str:
        result : ItemLookupResult = self.state_manager.find_item(spirit_pan_id, required_type="iov_spirit_pan", required_location="inventory")
        if not result.success:
            return result.error

        if not result.item_data.get("filled"):
            return "Please re-fill the spirit pan with spirit before placing it in the IOV lamp."

        response_object: ActionInternalResponse = self.lighthouse_manager.place_spirit_pan()
        parts = self._collect_response(response_object)

        if response_object.success:
            parts.append(self.state_manager.remove_item(spirit_pan_id).message)
            parts.append("Placed spirit pan! Spirit pan consumed.")

        return "\n".join(parts)

    def lamp_refill_spirit_pan(self, spirit_pan_id, spirit_source_id) -> str:
        source_result : ItemLookupResult = self.state_manager.find_item(spirit_source_id, required_type="spirit_source", required_location="accessible")
        if not source_result.success:
            return source_result.error

        pan_result : ItemLookupResult = self.state_manager.find_item(spirit_pan_id, required_type="iov_spirit_pan", required_location="inventory")
        if not pan_result.success:
            return pan_result.error

        spirit_pan_details = pan_result.item_data
        denatured_alcohol_details = source_result.item_data


        if spirit_pan_details.get("filled"):
            return "This spirit pan is already filled with spirit."

        if denatured_alcohol_details["spirit_quantity"] == 0:
            return "The denatured alcohol container is empty."

        parts = []
        new_spirit_content = denatured_alcohol_details["spirit_quantity"] - SPIRIT_CONSUME_RATE
        parts.append(self.state_manager.set_item_attribute(spirit_source_id, "spirit_quantity", new_spirit_content).message)
        parts.append(f"Spirit source consumed {SPIRIT_CONSUME_RATE} units of spirit. {new_spirit_content:.0%} units remaining.")

        if new_spirit_content < 0:
            parts.append(self.state_manager.set_item_attribute(spirit_source_id, "spirit_quantity", 0).message)
            removal_result = self.state_manager.remove_item(spirit_source_id, internal=True)
            parts.append("Spirit source has been consumed entirely!")
            parts.append(removal_result.message)

        parts.append(self.state_manager.set_item_attribute(spirit_pan_id, "filled", True).message)

        return "Spirit pan refilled.\n" + "\n".join(p for p in parts if p)

    ### Mantle Actions

    def lamp_light_install_mantle(self, mantle_id) -> str:
        if err := self._validate_inventory_item(mantle_id, "iov_mantle", "IOV Mantle"):
            return err

        response_object: ActionInternalResponse = self.lighthouse_manager.install_mantle()
        parts = self._collect_response(response_object)

        if response_object.success:
            parts.append(self.state_manager.remove_item(mantle_id).message)
            parts.append(self._adjust_stats(MANTLE_INSTALL_COSTS))
        # TODO: add signal for icon popups

        return "\n".join(parts)


    ###

    def open_valve(self, amount: float = 0.5) -> str:
        result: ActionInternalResponse = self.lighthouse_manager.open_valve(amount)


        if result.success:
            extra_messages = []
            extra_messages.append(self._apply_lamp_hazard())
        else:
            extra_messages = None
            
        response_request = {
            "response_object": result,
            "extra_lines": extra_messages
        }
        parts = self._collect_response(**response_request)

        return "\n".join(parts)

    def lamp_ignite_vapor(self, light_source_id) -> str:
        if err := self._validate_inventory_item(light_source_id, "hand_fire_source", "Hand Fire Source"):
            return err

        response_object: ActionInternalResponse = self.lighthouse_manager.ignite_vapor()
        parts = self._collect_response(response_object)
        # TODO: add signal for icon popups

        return "\n".join(parts)

    def lamp_light_spirit_pan(self, fire_source_id) -> str:
        if err := self._validate_inventory_item(fire_source_id, "hand_fire_source", "Hand Fire Source"):
            return err

        response_object: ActionInternalResponse = self.lighthouse_manager.light_spirit_pan()
        parts = self._collect_response(response_object)
        # TODO: add signal for icon popups

        return "\n".join(parts)

    def clean_jet_soot(self):
        response_object = ActionInternalResponse = self.lighthouse_manager.clean_jet(float(random.uniform(-0.8, -0.25)))
        parts = self._collect_response(response_object)
        if response_object.success:
            stats_res = self._adjust_stats(CLEAN_JET_COSTS)
            parts.append(stats_res)
        # TODO: add signal for icon popups

        return "\n".join(parts)

    # --- Oil Mechanism ---

    def controller_oil_mechanism(self, pumps: int = 1, oiler_id: str = None) -> str:
        if err := self._validate_inventory_item(oiler_id, "oiler_set", "Oiler Set"):
            return err

        response_object: ActionInternalResponse = self.lighthouse_manager.oil_mechanism(pumps * OIL_PUMP_RATE)
        parts = self._collect_response(response_object)

        if response_object.success:
            parts.append(f"You oil the clockwork mechanism {pumps} time{'s' if pumps != 1 else ''}.")
            parts.append(self._adjust_stats(OIL_MECHANISM_COSTS, pumps))
        # TODO: add signal for icon popups

        return "\n".join(parts)

    # data returning actions


    def lamp_remove_spirit_pan(self) -> str:
        response_object: ActionInternalResponse = self.lighthouse_manager.remove_spirit_pan()
        parts = self._collect_response(response_object)

        if response_object.success:
            item_data = self.item_store.get_item("IOV Spirit Pan")
            item_data["filled"] = response_object.data.get("pan_state") == "full"
            parts.append(self.state_manager.create_item("inventory", None, item_data).message)
        # TODO: add signal for icon popups

        return "\n".join(parts)


    def remove_mantle(self) -> str:
        response_object: ActionInternalResponse = self.lighthouse_manager.remove_mantle()
        parts = self._collect_response(response_object)

        if response_object.success:
            if response_object.data.get("was_fabric"):
                parts.append(self.state_manager.create_item("inventory", None, self.item_store.get_item("IOV Mantle")).message)
            else:
                parts.append("No item returned.")
        # TODO: add signal for icon popups

        return "\n".join(parts)

    # --- State Inspection / Examination ---

    def examine_spirit_source(self, spirit_source_id) -> str:
        result : ItemLookupResult = self.state_manager.find_item(spirit_source_id, required_type="spirit_source", required_location="accessible")
        if not result.success:
            return result.error
        item_data = result.item_data

        return f"You examine the {item_data['name']} ID {item_data['id']}. {item_data['descriptions']} Spirit Contents: {item_data['spirit_quantity']:.0%}"

    def accessible_room_light_check(self) -> str:
        # TODO: Change name and descriptive texts, register along with other rooms where it would be applicable.
        try:
            current_room_data = self.state_manager.get_current_room_data()
        except ValueError:
            return "You are not in a room. o.O"

        messages = [
            f"You are in the {current_room_data.name}. From here you catch a glimpse of the lamp's light output state.\n",
            self.lighthouse_manager.lamp.get_light_state()
        ]
        return "\n".join(messages)

    def get_lantern_room_interior_status(self) -> str:
        return "\n".join([
            self.lighthouse_manager.lantern.get_interior_status(),
            self.lighthouse_manager.lamp.get_light_state()
        ])

    # --- Tick ---

    def lighthouse_tick(self) -> str: # TODO: Change how this works.
        self.lighthouse_manager.tick()

        parts = []
        hazard_result = self._apply_lamp_hazard()
        if hazard_result:
            parts.append(hazard_result)

        return "\n".join(parts)