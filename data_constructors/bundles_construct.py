# bundles_construct.py

# Updated, is now working as a general items creator

import os
import re
import sys

# --- TEMPORARY FIX FOR DIRECT EXECUTION ---
# This block allows the script to find the 'utils' package
# when run directly from its current location.
# Assuming 'utils' is in the parent directory of this script's location
# This adds the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
# -------------------------------------------

from typing import List, Dict, Any, Optional # Import Optional or use | None for optional fields
import json 
from pydantic import BaseModel, Field, ValidationError # Import ValidationError


from utils.utils_ai_providers.simple_ai_config import LLMCONFIG



valid_plants = ['lettuce', 'carrot', 'cactus', 'tomato', 'potato', 'strawberry', 'rose', 'sunflower', 'mint', 'basil'] # Edit this to reflect the plants existing in the garden manager data structures. tools/tools_folder/tools_data/harvesting_data.py

stringed_plant_types = ', '.join(f"'{plant}'" for plant in valid_plants)

# --- Structure for the fixed stats_edit dictionary ---
class ItemStatsEdit(BaseModel):
    """
    Defines the required structure for the stats_edit dictionary.
    Must contain exactly 'fullness', 'hydration', and 'energy' as floats.
    """
    fullness: float = Field(description="Float change to fullness stat. Can be negative for inflicting negative effects or punishments for consumption.")
    hydration: float = Field(description="Float change to hydration stat. Can be negative for inflicting negative effects or punishments for consumption.")
    energy: float = Field(description="Float change to energy stat. Can be negative for inflicting negative effects or punishments for consumption.")

# --- Structure for the individual item definition ---
class ItemDefinition(BaseModel):
    """
    Represents the data required to define a single item for creation.
    Excludes the ID as per requirements.
    Includes a strictly defined stats_edit structure, but fields are optional based on type.
    """
    name: str = Field(description="A unique string identifier for the item type (e.g., 'bowl of nuts').")
    descriptions: List[str] = Field(description="A list of strings providing descriptions for the item.")
    static: bool = Field(description="Indicates if the item is static (cannot be picked up or moved like furniture).")
    # UPDATED: type is now List[str]
    type: List[str] = Field(description="A list of strings defining item categories (e.g., ['consumable'], ['misc', 'tool'], ['consumable', 'seed'], ['seed']). Primary categories: 'consumable', 'misc', 'furniture', 'seed'.")    
    stackable: bool = Field(default=True, description="Bool for the stackablity property of this item, if defaults to true. Small non-unique items should be set to true so they are stackable. Large and unique items should be set to FALSE")
    # MAKE effects and stats_edit OPTIONAL
    # Use | None for Pydantic V2 syntax for optional fields
    # default=None allows the field to be missing in the input data without Pydantic error

    effects: List[str] |None= Field(default=None, description="A list of strings describing narrative effects upon use (only for 'consumable' items).")
    stats_edit: ItemStatsEdit |None = Field(default=None, description="A dictionary containing specific stat changes (fullness, hydration, energy) (only for 'consumable' items).")

    plant_type: str  |None =Field(default=None, description=f"A string for the seed type, it should define the plant of seed this is for, from the valid options: {stringed_plant_types}")

# --- Structure that contains a list of these item definitions ---
class ItemDefinitionListContainer(BaseModel):
    """
    A container model holding a list of item definitions.
    """
    items: List[ItemDefinition] = Field(description="A list of item definition objects.")

class bundles_maker:


    def __init__(self, select_model="gpt-5-mini", select_provider="openai"):
        self.llm_client=LLMCONFIG(select_model,select_provider).get_provider()


    def prepare_bundle(self, concept: str) -> List[Dict[str, Any]]:
        """
        Prepares a bundle of items based on a concept using the OpenAI API.
        Returns a list of item dictionaries.
        """
        # Use the ItemDefinitionListContainer structure for the response
        # Refined the system prompt to clearly state the conditional fields,
        # guiding the AI to provide data that matches the optional fields in the Pydantic model.
        system = """
You are a Common Sense AI Crafter. Your mission is to create logical and realistic items for care packages and bundles. Every item you define must be grounded in common sense.

Given an idea, you will generate a list of item definitions. Your response MUST be a JSON object with a single key 'items' containing a list of item dictionaries.

Each item dictionary MUST strictly follow these rules:
General Rules:
Include 'name' (string), 'descriptions' (List[str]), and 'static' (boolean).
Include a 'type' (List[str]) with at least one primary category: 'consumable', 'misc', 'furniture', or 'seed'.
Apply common sense when defining item properties. For example, furniture must be static: true and non-stackable. Simple items like seeds or ingredients should be stackable.
Some items can logically belong to multiple types (e.g., a "strawberry seed" is both a 'seed' and a 'consumable').
Consumables:
Stat effects values can be possitive and negative depending on the safety of consumption of the item created.
Stat effects values range from -100 to 100 in cases where meals or foods are really large (like eating a whole rotisserie chicken!), while smaller foods (like a sigle celery stem as a snack) can sit in smaller ranges of negative and possitive like, -10, +15. 
Make sure to only include negative values for those items that are truly unsafe. dangerous and unhealthy to consume on their current state (primarely animal based products, raw poultry, raw minced meat, raw egs, etc.)
If a consumable type is present, you MUST include 'effects' (List[str]) and 'stats_edit' (a dictionary with float values for 'fullness', 'hydration', and 'energy').
Important: Only apply negative stat effects to items that are actually dangerous to eat raw (e.g., uncooked meat). For these items, such as a raw chicken, use severe negative values like -10 for fullness, -30 for hydration, and -50 for energy. Naturally edible raw items, like fruits and vegetables, should always provide positive or neutral effects.
Seeds:
If a seed type is present, you MUST include 'plant_type' (string) with one of these exact values: 'lettuce', 'carrot', 'cactus', 'tomato', 'potato', 'strawberry'.
"""

        # Use the prompt format from your working example

        print("\n--- Calling AI ---")
        print(f"Prompt: {concept}")

        response: ItemDefinitionListContainer | None = self.llm_client.structured_output(
            system=system,
            user=concept,
            structure=ItemDefinitionListContainer # Pass the Pydantic model
        )

        # Check if the structured call was successful and returned data
        # The .parse method returns the parsed model directly if successful
        if response is None or not response.items:
             print("AI call failed or returned empty/invalid list. Returning empty list.")
             return []

        processed_items_list: List[Dict[str, Any]] = []

        for item_definition in response.items:
            # Convert the Pydantic ItemDefinition model instance to a dictionary
            item_dict = item_definition.model_dump(exclude_none=True) # exclude_unset=True is useful here
            processed_items_list.append(item_dict)

        print("--- AI Call Successful ---")
        return processed_items_list

    # --- Helper function to save the bundle data to a specified file ---
    def save_bundle_to_json_file(self, file_path: str, bundle_data: List[Dict[str, Any]]):
        """
        Saves a list of item dictionaries to a JSON file.

        Args:
            file_path: The path to the target JSON file.
            bundle_data: The list of dictionaries representing the item definitions.
        """
        try:
            # Check if the file exists to append or create it
            file_exists = os.path.exists(file_path)
            
            # Open the file in append mode ('a') or write mode ('w') for the first time
            # We'll read existing content if it's a valid JSON array, otherwise create a new one.
            
            existing_data = []
            if file_exists and os.path.getsize(file_path) > 0:
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        existing_data = json.load(f)
                        if not isinstance(existing_data, list):
                            print(f"Warning: File {file_path} is not a JSON array. Overwriting.")
                            existing_data = []
                    except json.JSONDecodeError:
                        print(f"Warning: Could not decode JSON from {file_path}. Overwriting.")
                        existing_data = []

            # Combine old and new data
            all_data = existing_data + bundle_data

            with open(file_path, 'w', encoding='utf-8') as f:
                # Use json.dump for proper JSON formatting.
                # 'indent=4' makes the file human-readable.
                json.dump(all_data, f, indent=4)
            
            print(f"Bundle data appended to {file_path}")

        except IOError as e:
            print(f"Error saving bundle data to {file_path}: {e}")


if __name__ == "__main__":

    crafter = bundles_maker()

    # Define the target file path with a .json extension
    target_output_file = "inventory_items/items_provider/items_data/healthy_food.json" # 

    bundle_concepts = [
    "Bundle of consumable items, fresh and healthy ready to eat simple consumables." # here we prompt directly for the plants we want, however, the AI agent already knows what the valid plants are. It might generate invalid seeds if you ask for it.
    ]
    #"Bundle of furniture, varied styles, eras and designs, vibes, artistic directions, simple and classics bundle of: TVs and entertainment systems" # here we prompt directly for the plants we want, however, the AI agent already knows what the valid plants are. It might generate invalid seeds if you ask for it.

    total_bundles = len(bundle_concepts)
    for index, concept in enumerate(bundle_concepts):
        current_bundle_number = index + 1
        print(f"\n--- Generating and Appending '{concept}' ({current_bundle_number} of {total_bundles}) ---")

        # Example call to prepare the bundle
        bundle_items_result = crafter.prepare_bundle(concept)

        # Check if the AI call was successful and returned data, then save it to the specified file
        if bundle_items_result:
            # Call the new JSON saving function
            crafter.save_bundle_to_json_file(target_output_file, bundle_items_result)
            print(f"Successfully processed '{concept}' ({current_bundle_number} of {total_bundles}).")
        else:
            print(f"Bundle generation failed for '{concept}', not saving.")

    print("\nAll bundles finalized!")