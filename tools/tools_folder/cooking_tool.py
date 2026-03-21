from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager # just for typing

from tools.tools_folder.tools_helpers.ai_cook import cook
import random


CULINARY_EQUIPMENT_TYPE = "culinary_equipment"
COOKING_APPARATUS_PHENOM = "narrative_prepare" # Add this, no longer only heating source, but preparation space or area or implement in general, For future reference: also add a process tag to the keys, not strict, just to guide AI cook with it
EQUIPMENT_AFFORDANCE = "equipment_affordances" # Not yet implemented

COOKING_COSTS = {
    "hydration": -3.5,
    "fullness": -1,
    "energy": -1.5,
}

class CookingApparatus:
    def __init__(self, state_manager, signal=None, config_manager=None):
        self._signal_callback=signal

        # Store the state_manager reference
        self.state_manager : InventoryHouseManager = state_manager
        self.cook = cook(config_manager)
        #print("Kitchen initialized.")

    @staticmethod
    def _get_item_text(item_deets, source:str):
        item_texts = item_deets.get(source, []) 
        return random.choice(item_texts)


    def _scale_stats(self, stats_edit, amount):
        if not stats_edit:
            return {}
        return {k: round(v * amount, 2) for k, v in stats_edit.items()}
            

    def prepare_food(self, cooking_apparatus_id, process, items_list):
        if not items_list:
            return "Error: No items specified for preparation."

        cooking_apparatus = self.state_manager.find_item(cooking_apparatus_id, required_type=CULINARY_EQUIPMENT_TYPE, required_location="accessible")
        if not cooking_apparatus.success:
            return cooking_apparatus.error

        cooking_apparatus = cooking_apparatus.item_data

        capp_name = cooking_apparatus['name']
        capp_desc = self._get_item_text(cooking_apparatus, "descriptions")
        capp_phenom = self._get_item_text(cooking_apparatus, COOKING_APPARATUS_PHENOM)



        consumables, tools, errors = [], [], []

        for entry in items_list:
            item_id = entry.get("item_id")
            amount = entry.get("amount", 1)

            result = self.state_manager.find_item(item_id, required_location="inventory")
            if not result.success:
                errors.append(result.error)
                continue

            item = result.item_data
            types = item.get("type", [])

            if "consumable" in types:
                uses = item.get("consume_uses_left")
                if uses is not None and amount > uses:
                    errors.append(f"'{item['name']}' only has {uses} use(s) left, {amount} requested.")
                    continue
                consumables.append((item, amount))

            elif "tool" in types:
                tools.append(item)

            else:
                errors.append(f"'{item.get('name')}' is not a consumable or tool.")

        if errors:
            return "Preparation failed: " + "; ".join(errors)

        ingredients = [
            {**{k: item[k] for k in ("name", "descriptions", "effects", "stats_edit") if k in item},
            "amount": amount,
            "stats_edit": self._scale_stats(item.get("stats_edit"), amount)}
            for item, amount in consumables
        ] + [
            {**{k: item[k] for k in ("name", "descriptions", "effects", "stats_edit") if k in item},
            "stats_edit": self._scale_stats(item.get("stats_edit"), 1)}
            for item in tools
        ]

        pass_process = f"Using the following main equipment: {capp_name}, {capp_desc},  and the following ingredients: {ingredients}, try to prepare the following process: {process}."

        generated = self.cook.prepare_food(ingredients, pass_process)
        if not generated:
            return "You mime and begin preparing food, your plan was perfect, however when you start, you trip up the sequence of actions!... You just trace back your steps and start right from the beginning."

        for item_data in generated:
            self.state_manager.create_item("inventory", None, item_data)

        for item, amount in consumables:
            item_id = int(item["id"])
            uses = item.get("consume_uses_left")
            if uses is None or uses - amount <= 0:
                self.state_manager.remove_item(item_id)
            else:
                self.state_manager.set_item_attribute(item_id, "consume_uses_left", uses - amount)

        created_objects = {} # item name and description
        for item_data in generated:
            created_objects[item_data.get("name", "")] = self._get_item_text(item_data, "descriptions")

        self._signal_callback({
            "type": "show_icon_popup",
            "icon_path": "style/images/action_icons/plate_icon.png",
            "popup_type": 2,
        })

        for stat, amount in COOKING_COSTS.items():
            self.state_manager.adjust_stat(stat, amount)

        item_details = [f"{name}: {desc}" for name, desc in created_objects.items()]

        return (
            f"You interact with the {capp_name}, {capp_desc}\n"
            f"{capp_phenom}\n"
            f"Preparation successful! Created:\n" + "\n".join(item_details)
        )
