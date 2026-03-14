# ai_cook.py

# This is a simple crafting table class that uses a "Simple AI" provider to process
# and create new items based on a given preparation.
# The current implementation is being used by an AI agent to manage cooking tasks.

from typing import List, Dict, Any
from inventory_items.items_validation.item_pydantic_models import validate_item_dict
from inventory_items.items_validation.ai_schema_builder import build_llm_schema_for_types
from ai_managers.ai_utils.ai_loader import AIConfiguration

# Build once at import time — the cook only ever produces consumables.
_COOK_SCHEMA = build_llm_schema_for_types(["consumable"])
MAX_RETRIES = 4 # 4!!!

# TODO: Update this to use utils/ai_items_crafter.py and help the AI calculate the resulting stats for an item instead of letting it decide.

class cook:

    def __init__(self, config_manager):

        config_model = config_manager.get_config("AI","cook_model")
        selected_config_client = config_manager.get_config("AI","cook_provider")

        self.client=AIConfiguration(provider=selected_config_client,model=config_model,mode="simple_ai").get_client()

    def prepare_food(self, items: List[str], process: str) -> List[Dict[str, Any]]: # TODO: improve this prompt
 
        system=f"""You are a cooking AI, given a set of items and a cooking related process, you will return a single
        food item definition that would result from applying such cooking process into the given items. 
        You should identify the main resulting item which are 'consumable' directly from the preparation process. 
        Return the response as a JSON object matching the LLMSchema_consumable structure. While staying grounded in the items given to you, 
        make detailed and evocative descriptions and effects for the item, and in effects, write text directed to whomever just consumed this item, 
        i.e 'Consuming the water of glass makes you feel refreshed.', 'Calm washes over your body as you drink the fresh glass of water.', 'The candy gives you an overpowering taste in the mouth, you feel energized, and somewhat sticky.', 
        you can make 2 to 3 effects for the item. 
        The stats for the item you create should be based and calculated from the exact stats of the items given to you.
        i.e. 
        potatoes:
        stats_edit: fullness: 15.0, hydration: -5.0, energy: 5.0, amount: 20
        carrots:
        stats_edit: fullness: 5.0, hydration: 10.0, energy: 3.0, amount: 20

        The total count of stats to return for these items would be:
        fullness: 20.0, hydration: 5.0, energy: 8.0
        Note how the values are not affected by the amount of each of the items. These calculations should be flat, instead, the amount should be used to determine the size of a portion.

        The final plate should have a key 'consume_uses_left' with a value of 1 as a default. If you set a value higher than 1, you should divide the stats_edit by that value.
        So, in our previous example
        fullness: 20.0, hydration: 5.0, energy: 8.0, consume_uses_left: 2
        should be
        fullness: 10.0, hydration: 2.5, energy: 4.0, consume_uses_left: 2

        Some items could have negative stats, these is in cases where items are in a raw state or are consumed by themeselves. If these stats are negative because the item needs a preparation before consumption,
        i.e. raw poultry, raw coffee beans, raw potatoes, etc., consuder the negative stats as possitive for your calculation as your cooking process will make it safe to consume.
        Some other cases for negative stats are items that are salty, sour, bitter, spicy, etc., usually condiments, seasonings, for these, keep the negative stats as negative for your calculation.
        """

        process_prompt = f"""Using the items: {items}, and applying the process: {process}, design a single item that would result from it. 
        Do not return any tools or utensils, only food items, consumables. Create only the main plate or product that would result from such recipe."""


        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            retry_note = f"\nYour previous attempt was invalid: {last_error}. Please fix it." if last_error else ""

            response = self.client.structured_output(
                system=system,
                user=process_prompt + retry_note,
                structure=_COOK_SCHEMA
            )

            if response is None:
                print(f"Attempt {attempt}: AI call failed.")
                continue

            for item_definition in response.items:
                item_dict = item_definition.model_dump(exclude_none=True)
                result, error = validate_item_dict(item_dict)
                if error:
                    print(f"Attempt {attempt}: Invalid item '{item_dict.get('name')}': {error}")
                    last_error = error
                    break
                return [item_dict]

        print(f"All {MAX_RETRIES} attempts failed. Last error: {last_error}")
        return []