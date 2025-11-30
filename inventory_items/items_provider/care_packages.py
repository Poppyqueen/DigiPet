import os
import json
from .item_store import ItemStore

# "hydration": BLUE, # "fullness": RED, # "misc": PURPLE, # "ingredient": ORANGE, # "combo": BLACK, # "cheat": GREEN
class CareConstructor():
    def __init__(self, care_directory: str):
        self.items_store = ItemStore("inventory_items/items_provider/items_data")
        self.care_dict = self.load_care_packages(care_directory)

    def load_care_packages(self, care_directory: str) -> dict:
        care_dict = {}
        # Iterate over the files in the provided directory
        for filename in os.listdir(care_directory):
            file_path = os.path.join(care_directory, filename)
            
            # Process only JSON files
            if os.path.isfile(file_path) and filename.endswith('.json'):
                with open(file_path, 'r') as file:
                    try:
                        data = json.load(file)
                        # Expecting the file to contain a dictionary with care package data
                        if isinstance(data, dict):
                            care_dict.update(data)
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON in file: {filename}")
        return care_dict

    def create_full_data(self) -> list:
        # Our final output list.
        final_list = []
        # Loop through each package name and its data in the care_dict.
        for package_name, package_info in self.care_dict.items():
            # Get the list of detailed item dictionaries for the package.
            # list_items will handle if "items" is a list or a path string.
            items = self.list_items(package_info["items"])
            
            # Create a dictionary in the exact format you requested.
            package_dict = {
                "package": items,  # The list of item structures
                "color": package_info["package_color"]
            }
            final_list.append(package_dict)
            
        return final_list

    def make_package(self, package_name: str) -> list:
        # This method's purpose is now to just get the items for a specific package.
        package_info = self.care_dict.get(package_name)

        if not package_info:
            print(f"Warning: Package '{package_name}' not found.")
            return []
        
        item_source = package_info.get("items", [])
        detailed_items = self.list_items(item_source)
        
        return detailed_items

    def list_items(self, item_source):
        """
        Retrieves a list of item dictionaries from either a list of item names
        or a source path string.
        """
        #print("Items list request for base state constructor:")

        if isinstance(item_source, str):  # Handle path string
            filters = {'__source_path__': item_source}
            return self.items_store.find_items(filters)

        elif isinstance(item_source, list):  # Handle list of item names
            if not item_source:
                return []
            list_items_dict = self.items_store.get_item(item_source)
            return list(list_items_dict.values())
            
        else:
            print(f"Warning: Invalid item source type: {type(item_source)}. Returning empty list.")
            return []