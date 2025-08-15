import os
import json
from inventory_items.items_provider.item_store import ItemStore

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
        
        item_names = package_info.get("items", [])
        detailed_items = self.list_items(item_names)
        
        return detailed_items

    def list_items(self, items_list=["Dry Pasta (500g)", "Granulated Sugar (500g)"]):
        print("Items list request for base state constructor:")
        list_items = self.items_store.get_item(items_list)
        list_of_item_dicts = list(list_items.values())
        return list_of_item_dicts
