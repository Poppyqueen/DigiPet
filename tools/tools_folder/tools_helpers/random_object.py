import json
import random
import os # Used only for creating the dummy file for demonstration

from ....inventory_items.items_provider.item_store import ItemStore

item_s=ItemStore("inventory_items/items_provider/items_data")


def load_and_get_random_item(items_file="underbed_found_data.json"):
    """
    Loads item data from a JSON file and returns a random item structure.

    Args:
        json_filename (str): The path to the JSON file containing the list of items.

    Returns:
        dict: A randomly selected item structure (dictionary), or None if loading fails
              or the list is empty.
    """
    try:
        filers={
            '__source_path__':items_file
        }
        item_list=item_s.find_items(filers)

        # Check if the loaded data is actually a list
        if not isinstance(item_list, list):
            print(f"Error: The JSON file '{items_file}' does not contain a list at the top level.")
            return None

        # Check if the list is empty
        if not item_list:
            print(f"Error: The list of items in '{items_file}' is empty.")
            return None

        # Select a random item from the list
        random_item = random.choice(item_list)

        return random_item

    except FileNotFoundError:
        print(f"Error: The file '{items_file}' was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from the file '{items_file}'. Check for syntax errors.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading or selecting an item: {e}")
        return None
