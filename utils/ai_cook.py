# 
# 
# ai_cook.py

# This is a simple crafting table class that uses OpenAI's API to process items
# and create new items based on a given process.
# The current implementation is being used by an AI agent to manage crafting tasks.

from typing import List, Dict, Any
from utils.pydantic_models import ItemDefinitionListContainer
from utils.ai_loader import AIConfiguration




# # --- Structure for the fixed stats_edit dictionary ---
# class ItemStatsEdit(BaseModel):
#     """
#     Defines the required structure for the stats_edit dictionary.
#     Must contain exactly 'fullness', 'hydration', and 'energy' as integers.
#     """
#     fullness: float = Field(description="Integer change to fullness stat.")
#     hydration: float = Field(description="Integer change to hydration stat.")
#     energy: float = Field(description="Integer change to energy stat.")


# # --- Structure for the individual item definition ---
# class ItemDefinition(BaseModel):
#     """
#     Represents the data required to define a single item for creation.
#     Excludes the ID and the 'type' field as per requirements.
#     Includes a strictly defined stats_edit structure.
#     """
#     name: str = Field(description="A unique string identifier for the item type (e.g., 'bowl_of_nuts').")
#     descriptions: List[str] = Field(description="A list of strings providing descriptions for the item.")
#     static: bool = Field(description="Indicates if the item is static (cannot be picked up or moved).")

#     # Use the specific ItemStatsEdit model to enforce the structure and keys
#     stats_edit: ItemStatsEdit = Field(description="A dictionary containing specific stat changes (fullness, hydration, energy).")

#     # 'effects' field from your example, assuming it's required for this definition structure
#     effects: List[str] = Field(description="A list of strings describing narrative effects upon use.")

#     type: str = Field(description="Options: 'consumable' or 'misc' for items that are no longer consumable")

    
# # --- Structure that contains a list of these item definitions (Optional) ---
# # This is if you needed a container holding a list of objects matching the above definition
# class ItemDefinitionListContainer(BaseModel):
#     """
#     A container model holding a list of item definitions.
#     """
#     items: List[ItemDefinition] = Field(description="A list of item definition objects.")


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
        system=f"You are a cooking AI, given a set of items and a process, you will return a list of food item definitions that would result from applying such process into these items. You should identify the main resulting item(s) which are likely 'consumable' and any byproducts or scraps which should be 'misc'. Return the response as a JSON object matching the ItemDefinitionListContainer structure. While staying grounded in the items given to you, make detailed and evocative descriptions and effects for the items, deescribe then, and in effects, write text directed to whomever just consumed this item, i.e 'Consuming the water of glass makes you feel refreshed.', 'Calm washes over your body as you drink the fresh glass of water.', 'The candy gives you an overpowering taste in the mouth, you feel energized, and somewhat sticky.', you can make 2 to 3 effects for each item. The stats for the items you create should be high, minimum 20 points of replenishment for small items, up to 80 points for big food items."
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
            item_dict = item_definition.model_dump() # Or .dict() for Pydantic V1

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



# # --- Example Usage ---
# processor = cook()
# input_items = ["raw_nuts", "ceramic_bowl"]
# processing_action = "shell and place in bowl"

# resulting_items = processor.prepare_food(input_items, processing_action)

# print("\n--- Resulting Items (List of Dictionaries) ---")
# import json
# print(json.dumps(resulting_items, indent=4))

# # Verification
# print("\n--- Verification ---")
# if resulting_items:
#     # Check the first item (consumable in mock)
#     print("First item (expected consumable):", resulting_items[0].get("name"))
#     print("Has 'type'?", "type" in resulting_items[0])
#     print("Has 'stats_edit'?", "stats_edit" in resulting_items[0])
#     print("Has 'effects'?", "effects" in resulting_items[0])

#     # Check the second item (misc in mock)
#     if len(resulting_items) > 1:
#         print("\nSecond item (expected misc):", resulting_items[1].get("name"))
#         print("Has 'type'?", "type" in resulting_items[1])
#         print("Has 'stats_edit'?", "stats_edit" in resulting_items[1]) # Should be False
#         print("Has 'effects'?", "effects" in resulting_items[1])     # Should be False