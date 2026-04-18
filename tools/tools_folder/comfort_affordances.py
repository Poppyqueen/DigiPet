from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager # just for typing
    from inventory_items.services.return_objects import InventoryStateResult, InventoryItemEntry



from utils.misc import check_one_in, front_weighted_pick
import random
import math
import asyncio


NOOK_TYPE = "cranny_host"

SEAT_TYPE = "seatable"
SEAT_NARRATIVE = "narrative_sitting"

SLEEP_ITEM = "sleepable_spot"
SLEEP_NARRATIVE = "narrative_sleeping"

HUGGABLE_ITEM = "comfort_object"
NARRATIVE_HUG = "narrative_hug"

MEDITATION_AID_ITEM = "meditation_aid"
MEDITATION_AID_NARRATIVE = "meditation_aid_ambience"



# Turned into ComfortAffordances, maybe move later, maybe don't, or even rename, decide another time
class ComfortAffordances:
    def __init__(self, state_manager, signal=None, memory=None, items_crafter=None, item_store=None):
        self.memory=memory
        self._signal_callback = signal
        # Store the state_manager reference
        self.state_manager : InventoryHouseManager = state_manager
        #print("Bedroom initialized.")
        self.item_store = item_store
        self.items_crafter = items_crafter

        

    @staticmethod
    def _get_item_text(item_deets, source:str):
        item_texts = item_deets.get(source, []) 
        return random.choice(item_texts)

    def _filter_meditative_items(self, item_data: list[InventoryItemEntry]):
        return [item for item in item_data if "meditation_aid" in item.item_data.get("type", "")]


    def meditate(self, thoughts):
        current_steps = self.state_manager.get_steps()
        edit=random.uniform(.1, .50) # magic numbers
        self.state_manager.adjust_stat("energy", edit)
        # self.state_manager.get_steps
        # --- Add signal call ---
        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/meditate_icon.png"})
        # ------------------------
        return f"You feel inspired by the ambience, you try to quiet your mind, however, thoughts rush over you... {thoughts}.\n As you keep going your mind begins letting go...\n...\n..."

    def _get_medit_item_state(self, item_id: int) -> tuple[bool, dict | str]:
        found_response = self.state_manager.find_item(
            item_id=item_id, required_type=MEDITATION_AID_ITEM, required_location="accessible"
        )
        if found_response.error:
            return False, found_response.error

        item_data = found_response.item_data
        ambience = item_data.get(MEDITATION_AID_NARRATIVE)
        item_name = item_data.get("name", "")

        ts = found_response.item_data.get("toggle_state", {})
        if isinstance(ts, dict) and ts.get("toggle_state") == "off":
            return False, ""

        return True, {
            "name": item_name,
            "description": self._get_item_text(item_data, "descriptions"),
            "ambience": ambience,
        }

    def get_accessible_meditative_elements(self):
        inventory: InventoryStateResult = self.state_manager.get_inventory_state()

        check_all = inventory.inventory_items + inventory.room_items
        meditative_items = self._filter_meditative_items(check_all)

        if not meditative_items:
            return "A an odd sensation that something is missing overcomes you..."

        info_string = "The area is provided with a beautiful ambience, at a quick glance, you can notice:\n"

        for item in meditative_items:
            item_id = item.item_id

            flag, state = self._get_medit_item_state(item_id)
            if not flag:
                info_string += f"{state}\n"
                continue

            info_string += f"  {state['name']} ID: {item_id}\n  {state['description']}\n    {self._get_item_text(state, 'ambience')}\n"
            info_string += "=" * 30 + "\n"

        return info_string
        
        

    def take_a_seat(self, item_id: int):
        item_object = self.state_manager.find_item(item_id=item_id, required_type=SEAT_TYPE, required_location="room")
        if not item_object.success:
            return item_object.error

        # Safe to access item_data only after success check
        item_details = item_object.item_data
        display_item_name = self.state_manager.format_item_for_display(item_details, False)
        item_desc = self._get_item_text(item_details, "descriptions")
        item_phenom = self._get_item_text(item_details, SEAT_NARRATIVE)
        edit = 1

        self._signal_callback({"type": "show_message_popup", "message": f"Sat on {display_item_name}!"})

        message = f"You sit down for a while, you feel like you are sinking as you relax. Gained {edit} energy points."
        if check_one_in(10): # magic number
            edit = 5
            message = f"You sit down, the world seems to pass really slowly for now. You rested for {edit} energy points."

        self.state_manager.adjust_stat("energy", edit)

        
        # TODO: Add icon pop-up signal and image to assets
        return f"You take a seat on the {display_item_name}\n{item_desc}\n{item_phenom}\n{message}"

    def reach_into_item_crevice(self, item_id):
        lookup = self.state_manager.find_item(
            item_id,
            required_type=NOOK_TYPE,
            required_location="room"
        )
        if lookup.error:
            return lookup.error

        item_data = lookup.item_data
        item_name = self.state_manager.format_item_for_display(item_data, False)
        
        search_chance = item_data.get("chance", 0.05) 
        reward_options = item_data.get("reward_options", []) 
        narrative_lines = item_data.get("narrative_search", [f"You reach under the {item_name}."])


        self._signal_callback({"type": "show_message_popup", "message": "Looking for something hidden..."})

        search_action_desc = random.choice(narrative_lines)

        if random.random() >= search_chance:
            return f"{search_action_desc} However, you find nothing but dust bunnies."

        found_item_types = None
        if reward_options:
            try:
                found_item_types = front_weighted_pick(items=reward_options, none_chance=0.30)
                print(f"DEBUG: front_weighted_pick returned: {found_item_types}")
            except Exception as e:
                print(f"DEBUG ERROR: front_weighted_pick crashed: {e}")
                # Don't crash the whole thing, just proceed with None
                found_item_types = None

        item_descs_text = "\n".join(item_data.get("descriptions", []))

        items_to_create = self.items_crafter.craft_item(
            user_prompt=(
                f"Create an item found under: {item_name}. {item_descs_text}. "
                f"Inconsequential, evocative, and fits the source item's qualities."
            ),
            select_types=found_item_types
        )
        
        print(f"DEBUG: items_to_create type={type(items_to_create)}, value={items_to_create}")

        if not items_to_create:
            return f"{search_action_desc} You feel something, but it turns out to be a mirage."

        result = self.state_manager.create_item(
            target_location="inventory",
            target_location_id=None,
            item_creation_data=items_to_create
        )

        print(f"DEBUG: create_item result success={result.success}, error={result.error}")

        if not result.success:
            return f"{search_action_desc} You feel something, but it slips back into the shadows."

        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/trumpet.png"})
        
        return f"{search_action_desc} You found:\n{result.message}"

    # Add instance methods here
    async def sleep_on_item(self, lay_item_id, seconds):
        #print("Going to sleep in the bedroom...")
        #message=self.state_manager.sleep(seconds)
        lookup = self.state_manager.find_item(
            lay_item_id,
            required_type=SLEEP_ITEM,
            required_location="room"
        )
        if lookup.error:
            return lookup.error

        item_data = lookup.item_data

        item_name = self.state_manager.format_item_for_display(item_data, False)
        item_desc = self._get_item_text(item_data, "descriptions")
        item_phenom = self._get_item_text(item_data, SLEEP_NARRATIVE)# **second-person, present tense** narrative of the experience of laying down and sleeping on this item.


        constant = 1
        # Using square root:
        energy_gain = constant * math.sqrt(seconds)
        # self.memory.save_to_memory("You beggin your sleep process.", "short_term", "user")
        self._signal_callback({"type": "show_message_popup", "message": f"Entering sleep for {seconds} seconds!"})
        #int_gain=int(energy_gain)
        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/pillow_icon.png"})
        self._signal_callback({"type": "start_sleep", "time_to_sleep": seconds})

        # Sleep!
        await asyncio.sleep(seconds)
        self._signal_callback({"type": "end_sleep"})

        # Gain energy
        self.state_manager.adjust_stat("energy", energy_gain)


        return f"{item_phenom}\n, after {seconds} seconds, you wake up on the {item_name}.\n{item_desc}\n, recovering {energy_gain} energy points. You feel refreshed."

    def hug_comfort_object(self, item_id):
        lookup = self.state_manager.find_item(
            item_id,
            required_type=HUGGABLE_ITEM,
            required_location="accessible" # both inventory and room
        )
        if lookup.error:
            return lookup.error

        item_data = lookup.item_data

        item_name = self.state_manager.format_item_for_display(item_data, False)
        item_desc = self._get_item_text(item_data, "descriptions")

        item_phenom = self._get_item_text(item_data, NARRATIVE_HUG)

        self._signal_callback({"type": "show_message_popup", "message": f"Hugging {item_name}!"})

        edit=random.uniform(.1, .50) # magic numbers
        self.state_manager.adjust_stat("energy", edit)
        message = f"You hug the {item_name}, {item_phenom} Gained {edit} energy points."

        # --- Add signal call ---
        # self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/pillow_icon.png"}) # TODO: Need a new icon for this now that changed name
        # ------------------------       
        return f"{item_desc}\n{message}"
 