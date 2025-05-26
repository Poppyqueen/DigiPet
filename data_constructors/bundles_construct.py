# bundles_construct.py

import os
import re
from typing import List, Dict, Any, Optional # Import Optional or use | None for optional fields

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError # Import ValidationError
from dotenv import load_dotenv

load_dotenv()  # This loads variables from .env into os.environ

api_key = os.getenv("OPENAI_API_KEY")

if api_key is None:
    print("API key not found. Please set the OPENAI_API_KEY environment variable.")
    exit(1)


valid_plants = ['lettuce', 'carrot', 'cactus', 'tomato', 'potato', 'strawberry', 'rose', 'sunflower', 'mint', 'basil'] # Edit this to reflect the plants existing in the garden manager data structures. tools/tools_folder/tools_data/harvesting_data.py

strined_plant_types = ', '.join(f"'{plant}'" for plant in valid_plants)

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
    name: str = Field(description="A unique string identifier for the item type (e.g., 'bowl_of_nuts').")
    descriptions: List[str] = Field(description="A list of strings providing descriptions for the item.")
    static: bool = Field(description="Indicates if the item is static (cannot be picked up or moved like furniture).")
    # UPDATED: type is now List[str]
    type: List[str] = Field(description="A list of strings defining item categories (e.g., ['consumable'], ['misc', 'tool'], ['consumable', 'seed'], ['seed']). Primary categories: 'consumable', 'misc', 'furniture', 'seed'.")    

    # MAKE effects and stats_edit OPTIONAL
    # Use | None for Pydantic V2 syntax for optional fields
    # default=None allows the field to be missing in the input data without Pydantic error
    effects: List[str] |None= Field(default=None, description="A list of strings describing narrative effects upon use (only for 'consumable' items).")
    stats_edit: ItemStatsEdit |None = Field(default=None, description="A dictionary containing specific stat changes (fullness, hydration, energy) (only for 'consumable' items).")

    plant_type: str  |None =Field(default=None, description=f"A string for the seed type, it should define the plant of seed this is for, from the valid options: {strined_plant_types}")

# --- Structure that contains a list of these item definitions ---
class ItemDefinitionListContainer(BaseModel):
    """
    A container model holding a list of item definitions.
    """
    items: List[ItemDefinition] = Field(description="A list of item definition objects.")

class bundles_maker:

    client=OpenAI(api_key=api_key) 

    def __init__(self):
        pass


    def _calls_structured(self, system: str, input_content: str, structure: type[BaseModel]) -> BaseModel | None:
        """
        Calls the OpenAI API with a structured response format using the .parse method
        as shown in the user's working example.
        """
        try:
            # Using the .parse method signature from the user's example
            # Ensure your OpenAI library version and setup supports client.beta.chat.completions.parse
            completion = self.client.beta.chat.completions.parse(
                 model="gpt-4.1-mini", # Use your desired model name
                 messages=[
                     {"role": "system", "content": system},
                     {"role": "user", "content": input_content}
                 ],
                 response_format=structure # Pass the Pydantic structure directly here
            )
            # Access the parsed content which is expected to be an instance of 'structure'
            parsed_response = completion.choices[0].message.parsed
            return parsed_response
        except AttributeError:
             print("Error: client.beta.chat.completions.parse not found. Ensure you have a compatible library version or use the standard `create` method.")
             return None
        except ValidationError as e: # Catch specific Pydantic validation errors from the parse step
             print(f"Pydantic Validation Error during OpenAI parse: {e}")
             # Note: With parse, the raw JSON might not be easily available here if parsing failed early.
             return None
        except Exception as e:
            print(f"Error calling OpenAI API for structured output: {e}")
            return None


    def prepare_bundle(self, concept: str) -> List[Dict[str, Any]]:
        """
        Prepares a bundle of items based on a concept using the OpenAI API.
        Returns a list of item dictionaries.
        """
        # Use the ItemDefinitionListContainer structure for the response
        # Refined the system prompt to clearly state the conditional fields,
        # guiding the AI to provide data that matches the optional fields in the Pydantic model.
        system = (
            "You are a bundle crafter AI. Given an idea, you will generate a list of item definitions "
            "for a care package or bundle. Your response MUST be a JSON object with a single key 'items' "
            "containing a list of item dictionaries. Each item dictionary MUST strictly follow these rules:\n"
            "- Include 'name' (string), 'descriptions' (List[str]), 'static' (bool), and 'type' (List[str]). "
            "The 'type' list MUST contain at least one primary category: 'consumable', 'misc', 'furniture', or 'seed'. "
            "It can also include other descriptive types (e.g., 'tool', 'weapon', 'wearable', 'container').\n"
            "- IF the 'type' list contains 'consumable', you MUST include 'effects' (List[str]) and 'stats_edit' (a dictionary with keys 'fullness', 'hydration', 'energy' as floats).\n"
            "- IF the 'type' list does NOT contain 'consumable', you MUST NOT include the 'effects' or 'stats_edit' keys.\n"
            "- IF the 'type' list contains 'seed', you MUST include 'plant_type' (string) with one of the following exact values: 'lettuce', 'carrot', 'cactus', 'tomato', 'potato', 'strawberry'.\n"
            "- IF the 'type' list does NOT contain 'seed', you MUST NOT include the 'plant_type' key.\n"
            "Ensure all values match the specified types (e.g., floats for stats_edit values, not integers)."
            "You can create raw items, if you do, these need to have 'consumable' in their type list."
            "In the stats floats you can use negative values to cause negative effects or punishments for consumption of raw items or other similar effects."
            "The stats effect ranges are from -50 to 50."
            "Be punishing for the consumption of raw items in all stats, from fullness, hydration and energy, specially raw protein will cause sickness, loss of energy, stomach ache, dehydration, and hunger. Eating a whole raw chicken should give something like -10, -30, -50."
        )

        # Use the prompt format from your working example
        process_prompt = f"{concept} Bundle"

        print("\n--- Calling AI ---")
        print(f"Prompt: {process_prompt}")

        response: ItemDefinitionListContainer | None = self._calls_structured(
            system=system,
            input_content=process_prompt,
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
            item_dict = item_definition.model_dump(exclude_unset=True) # exclude_unset=True is useful here

            item_types = item_dict.get("type", []) # Get the list of types, default to empty list

            # --- Post-processing: Safeguard for 'consumable' related fields ---
            if "consumable" not in item_types:
                if item_dict.pop("effects", None) is not None:
                     print(f"Processing non-consumable item '{item_dict.get('name')}': Removed 'effects' (AI incorrectly included).")
                if item_dict.pop("stats_edit", None) is not None:
                     print(f"Processing non-consumable item '{item_dict.get('name')}': Removed 'stats_edit' (AI incorrectly included).")
            else: # "consumable" IS in item_types, so effects and stats_edit should be present
                 if item_dict.get("effects") is None:
                      print(f"Warning: Consumable item '{item_dict.get('name')}' is missing 'effects'. Adding empty list.")
                      item_dict["effects"] = []
                 if item_dict.get("stats_edit") is None:
                      print(f"Warning: Consumable item '{item_dict.get('name')}' is missing 'stats_edit'. Adding default zero stats.")
                      item_dict["stats_edit"] = ItemStatsEdit(fullness=0.0, hydration=0.0, energy=0.0).model_dump()

            # --- Post-processing: Safeguard for 'seed' related fields (NEW) ---
            valid_plant_types = ['lettuce', 'carrot', 'cactus', 'tomato', 'potato', 'strawberry']
            if "seed" not in item_types:
                if item_dict.pop("plant_type", None) is not None:
                    print(f"Processing non-seed item '{item_dict.get('name')}': Removed 'plant_type' (AI incorrectly included).")
            else: # "seed" IS in item_types, so plant_type should be present and valid
                current_plant_type = item_dict.get("plant_type")
                if current_plant_type is None or current_plant_type not in valid_plant_types:
                    # If missing or invalid, remove it and log a warning.
                    # Depending on game logic, you might want to default to a specific type
                    # or mark the item as invalid for planting. Here, we remove it.
                    item_dict.pop("plant_type", None) # Ensure it's removed if invalid/missing
                    print(f"Warning: Seed item '{item_dict.get('name')}' has missing or invalid 'plant_type' ('{current_plant_type}'). Expected one of {valid_plant_types}. Removed 'plant_type'.")

            processed_items_list.append(item_dict)

        print("--- AI Call Successful ---")
        return processed_items_list

# --- Helper function to create a valid Python variable name ---

def _concept_to_variable_name(concept: str, max_length: int = 50) -> str:
    """
    Converts a concept string into a valid Python variable name,
    with an optional length cutoff.

    Args:
        concept: The input concept string.
        max_length: The maximum length for the returned variable name.
                    Defaults to 64. Set to 0 or None for no length limit.

    Returns:
        A valid Python variable name.
    """
    # Convert to lowercase
    name = concept.lower()

    # Replace spaces, hyphens, commas, and other non-alphanumeric characters with underscores
    # Keep only a-z, 0-9, and replace everything else with underscore
    name = re.sub(r'[^a-z0-9]+', '_', name)

    # Remove leading/trailing underscores
    name = name.strip('_')

    # Ensure the name is not empty after cleaning
    # This handles inputs like "!", " @ ", "__" etc.
    if not name:
        # Use a default name that itself is valid and short
        name = "unnamed_bundle"

    # Ensure it starts with a letter or underscore (add underscore if starts with digit)
    if name[0].isdigit():
        name = '_' + name

    # Apply length cutoff *after* cleaning and initial checks
    # Check if max_length is positive, otherwise no limit
    if max_length is not None and max_length > 0:
        name = name[:max_length]

        # Re-check for emptiness *after* slicing
        # Slicing could potentially result in an empty string if max_length is small
        if not name:
             # If truncation resulted in an empty string, use the default again
             name = "unnamed_bundle"

    return name

# --- Helper function to save the bundle data to a specified file ---
def save_bundle_to_file(file_path: str, concept: str, bundle_data: List[Dict[str, Any]]):
    """
    Generates a Python variable definition string from bundle data based on the concept
    and appends it to the end of the specified script file.

    Args:
        file_path: The path to the target Python file where the bundle list will be saved.
        concept: The string concept used to create the bundle.
        bundle_data: The list of dictionaries representing the item definitions.
    """
    filename = file_path # Use the provided file path

    # Generate the variable name from the concept
    variable_name = _concept_to_variable_name(concept)

    # Format the bundle data list into a Python string representation
    # Using repr() is suitable for basic Python literals.
    # Add indentation for readability in the output file
    data_string = repr(bundle_data)
    # Optional: Using json.dumps for potentially nicer formatting, requires json.loads when loading
    # data_string = json.dumps(bundle_data, indent=4)

    # Format the full variable definition string
    # Add newlines for separation from existing code
    definition_string = f"\n\n{variable_name} = {data_string}\n"

    try:
        # Open the file in append mode ('a')
        # Create the file if it doesn't exist
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(definition_string)
        print(f"Bundle '{concept}' saved successfully as variable '{variable_name}' in {filename}")
    except IOError as e:
        print(f"Error saving bundle data to {filename}: {e}")

# --- Example Usage ---
if __name__ == "__main__":

    crafter = bundles_maker()

    # Define the target file path where you want to save the bundle data
    # Make sure this file exists or the script has permissions to create it.
    target_output_file = "care_packages.py" # Using a distinct name for generated file

    bundle_concepts = [
"Seeds and more seeds! many seeds, for 'rose', 'basil', 'mint', 'sunflower', 'strawberry'" # here we prompt directly for the plants we want, however, the AI agent already knows what the valid plants are. It might generate invalid seeds if you ask for it.

        # Add more concepts as needed
    ]
    total_bundles = len(bundle_concepts)
    for index, concept in enumerate(bundle_concepts):
        current_bundle_number = index + 1
        print(f"\n--- Generating and Appending '{concept}' ({current_bundle_number} of {total_bundles}) ---")

        # Example call to prepare the bundle
        bundle_items_result = crafter.prepare_bundle(concept)

        # Check if the AI call was successful and returned data, then save it to the specified file
        if bundle_items_result:
            # Use the original concept string for variable name generation
            save_bundle_to_file(target_output_file, concept, bundle_items_result)
            print(f"Successfully processed '{concept}' ({current_bundle_number} of {total_bundles}).")
        else:
            print(f"Bundle generation failed for '{concept}', not saving.")

    print("\nAll bundles finalized!")