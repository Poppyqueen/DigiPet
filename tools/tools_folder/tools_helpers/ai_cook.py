# 
# 
# ai_cook.py

# This is a simple crafting table class that uses OpenAI's API to process items
# and create new items based on a given process.
# The current implementation is being used by an AI agent to manage crafting tasks.


# Update this, creating a food item should inform of the ID it has 
from typing import List, Dict, Any
from utils.pydantic_models import ItemDefinitionListContainer
from ai_managers.ai_utils.ai_loader import AIConfiguration


class cook:

    def __init__(self, config_manager):

        config_model = config_manager.get_config("AI","cook_model")
        selected_config_client = config_manager.get_config("AI","cook_provider")


        self.client=AIConfiguration(provider=selected_config_client,model=config_model,mode="simple_ai").get_client()

    def prepare_food(self, items: List[str], process: str) -> List[Dict[str, Any]]:
        """
        Calls the cooking AI, retrieves structured item definitions,
        and processes them into a list of dictionaries, removing
        'effects' and 'stats_edit' for 'misc' type items.

        Args:
            items: List of input item names.
            process: Description of the process applied.

        Returns:
            A list of dictionaries, where each dictionary represents a resulting item,
            with 'effects' and 'stats_edit' removed for 'misc' type items.
            Returns an empty list if the AI call fails.
        """
        system=f"You are a cooking AI, given a set of items and a cooking related process, you will return a list of consumable, food item definition or definitions that would result from applying such cooking process into the given items. You should identify the main resulting item(s) which are likely 'consumable' and any byproducts or scraps which should be 'misc'. Return the response as a JSON object matching the ItemDefinitionListContainer structure. While staying grounded in the items given to you, make detailed and evocative descriptions and effects for the items, deescribe then, and in effects, write text directed to whomever just consumed this item, i.e 'Consuming the water of glass makes you feel refreshed.', 'Calm washes over your body as you drink the fresh glass of water.', 'The candy gives you an overpowering taste in the mouth, you feel energized, and somewhat sticky.', you can make 2 to 3 effects for each item. The stats for the items you create should be high, minimum 20 points of replenishment for small items, up to 80 points for big food items."
        process_prompt=f"Using the items: {items}, and applying the process: {process}, design a set of items that would result from it."

        print("\n--- Calling AI ---")
        print(f"Prompt: {process_prompt}")

        response: ItemDefinitionListContainer | None = self.client.structured_output(
            system=system,
            user=process_prompt,
            structure=ItemDefinitionListContainer
        )

        if response is None:
             print("AI call failed. Returning empty list.")
             return []

        processed_items_list: List[Dict[str, Any]] = []

        for item_definition in response.items:
            # Convert the Pydantic ItemDefinition model instance to a dictionary
            item_dict = item_definition.model_dump(exclude_none=True) # Or .dict() for Pydantic V1

            # --- Post-processing: Remove keys for 'misc' items ---
            if item_dict.get("type") == "misc":
                print(f"Processing misc item '{item_dict.get('name')}': Removing effects and stats_edit.")
                # Use .pop() which removes the key and returns its value (or None if key not found)
                # This is slightly cleaner than checking 'in dict' then 'del dict[key]'
                item_dict.pop("effects", None)
                item_dict.pop("stats_edit", None)
            # --- End Post-processing ---

            # Append the (potentially modified) dictionary to our new list
            processed_items_list.append(item_dict)

        print("--- AI Call Successful ---")
        return processed_items_list

