import json
import copy
from pathlib import Path
import re

class ItemStore:
    def __init__(self, root_dir_path: str= "inventory_items/items_provider/items_data"):
        self._items = {}
        self._item_to_file_map = {}
        self._root_dir = Path(root_dir_path) # Store the root directory as a Path object
        self._load_items()

    def _load_items(self):
        """Recursively loads items from all JSON files in a given directory."""
        if not self._root_dir.is_dir():
            print(f"Warning: '{self._root_dir}' is not a valid directory.")
            return

        json_files = self._root_dir.rglob('*.json')
        
        for path in json_files:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = [data]

                    for item_data in data:
                        item_name = item_data.get('name')
                        if item_name:
                            self._items[item_name] = item_data
                            self._item_to_file_map[item_name] = str(path)
            except (IOError, json.JSONDecodeError) as e:
                print(f"Error loading from '{path}': {e}")

    def get_item(self, name: str | list[str]) -> dict | None | dict[str, dict]:
        """Retrieves a deep copy of a single item dictionary by its name,
        or accepts a list/tuple/set of names and returns a dict mapping each found
        name to its item dict (missing names are omitted)."""
        
        def parse_name(name: str):
            """Returns (clean_name, quantity) where quantity defaults to 1."""
            match = re.match(r'^(.*)\[x(\d+)\]$', name)
            if match:
                return match.group(1), int(match.group(2))
            return name, 1
        
        def get_single_item(name: str):
            """Get item(s) by name (with optional [xN] syntax)."""
            clean_name, quantity = parse_name(name)
            item = self._items.get(clean_name)
            
            if item is None:
                return None
            
            # Stackable: return one item with adjusted quantity
            if item.get("stackable"):
                item_copy = copy.deepcopy(item)
                item_copy["quantity"] = item_copy.get("quantity", 1) * quantity
                return {name: item_copy}
            
            # Non-stackable: return multiple separate copies with unique keys
            result = {}
            for i in range(quantity):
                key =  f"{name}_{i}" if quantity > 1 else name
                result[key] = copy.deepcopy(item)
            return result
        
        # Batch request
        if isinstance(name, (list, tuple, set)):
            result = {}
            for n in name:
                items = get_single_item(n)
                if items is not None:
                    result.update(items)  # Merge the dict(s)
            return result
        
        # Single request
        items = get_single_item(name)
        if items is None:
            return None
        
        # For single requests, if there's only one item, return it directly
        if len(items) == 1:
            return list(items.values())[0]
        
        # Multiple non-stackable items requested: return the dict
        return items

    def get_items_by_type(self, item_type: str) -> list[dict]:
        """Retrieves a list of all items that include the specified type."""
        return [copy.deepcopy(item) for item in self._items.values() if item_type in item.get('type', [])]
    
    def find_items(self, filters: dict = None) -> list[dict]:
        """
        Finds items that match all provided filters.
        A special filter key, '__source_path__', can be used to filter by the
        item's original file path relative to the root directory. This can be a
        direct path to a file or a path to a directory.
        Example: find_items(filters={'__source_path__': 'weapons/'})
        Example: find_items(filters={'__source_path__': 'weapons/purple_magic_sword.json'})
        """
        if filters is None:
            return [copy.deepcopy(item) for item in self._items.values()]

        found_items = []
        for item_name, item_data in self._items.items():
            match = True
            
            # Check for the special '__source_path__' filter
            if '__source_path__' in filters:
                expected_path_segment = filters['__source_path__']
                expected_path = str(self._root_dir / expected_path_segment)
                actual_path = self._item_to_file_map.get(item_name)
                
                # If the actual path doesn't start with the expected path, it's not a match.
                # This works for both directory and file paths.
                if not actual_path or not actual_path.startswith(expected_path):
                    match = False
            
            # Check for all other filters
            if match:
                for key, value in filters.items():
                    if key == '__source_path__':
                        continue
                    
                    if key not in item_data:
                        match = False
                        break
                    
                    # Special handling for 'type' lists
                    if key == 'type' and isinstance(value, list) and isinstance(item_data.get('type'), list):
                        if not all(t in item_data.get('type', []) for t in value):
                            match = False
                            break
                    elif item_data[key] != value:
                        match = False
                        break
            
            if match:
                found_items.append(copy.deepcopy(item_data))
        
        return found_items

    def get_all_items(self) -> list[dict]:
        """Retrieves a deep copy of all items currently in the store."""
        return [copy.deepcopy(item) for item in self._items.values()]

    def add_item_definition(self, item_data: dict) -> tuple[bool, str]:
        item_name = item_data.get("name")
        if not item_name:
            return False, "Failed to add item: 'name' key is missing."
        
        if item_name in self._items:
            return False, f"Failed to add item: An item with the name '{item_name}' already exists."

        self._items[item_name] = copy.deepcopy(item_data)
        self._item_to_file_map[item_name] = None
        return True, f"Item '{item_name}' added successfully."
    

    def save_item_to_file(self, item_name: str, file_path: str = None) -> tuple[bool, str]:
        """
        Saves a single item to a specified file path relative to the root directory.
        If no file_path is provided, it saves to the item's original source file
        or to a default file in the root directory for new items.
        """
        item_data = self._items.get(item_name)
        if not item_data:
            return False, f"Error: Item '{item_name}' not found in store."

        # Determine the file path to save to.
        # New Logic: Construct the save path relative to the root directory.
        if file_path:
            save_path = self._root_dir / file_path
        else:
            # Fallback to the original file path or a default for new items.
            original_path_str = self._item_to_file_map.get(item_name)
            if original_path_str:
                save_path = Path(original_path_str)
            else:
                item_name_slug = item_name.replace(" ", "_").lower()
                save_path = self._root_dir / f"{item_name_slug}.json"
        
        try:
            existing_items = []
            if save_path.exists():
                with open(save_path, 'r') as f:
                    try:
                        existing_items = json.load(f)
                        if not isinstance(existing_items, list):
                            existing_items = [existing_items]
                    except json.JSONDecodeError:
                        print(f"Warning: File '{save_path}' is not a valid JSON list. Overwriting.")
                        existing_items = []

            item_exists_in_file = False
            for i, item in enumerate(existing_items):
                if item.get('name') == item_name:
                    existing_items[i] = item_data
                    item_exists_in_file = True
                    break
            
            if not item_exists_in_file:
                existing_items.append(item_data)
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w') as f:
                json.dump(existing_items, f, indent=4)
            
            # Update the internal mapping for the newly saved item.
            self._item_to_file_map[item_name] = str(save_path)
            
            return True, f"Successfully saved item '{item_name}' to '{save_path}'."
        except IOError as e:
            return False, f"Error saving item '{item_name}': {e}"