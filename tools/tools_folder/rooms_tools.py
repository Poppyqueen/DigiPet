# State manager is being passed into this


# Here we cointain simple tools for each room, mostly based on
# flavor text

# Some use utils to interact with some simple APIs or data structures.

# the state manager has access to inventory and wellness stats access


from utils import open_meteo_handle, tv_handle, wiki_handle, random_object, simulation

from utils.ai_cook import cook

import random


def check_one_in(number: int):
  """
  Checks if a random event with a 1 in (the given argument) chance occurs.

  Returns:
      bool: True if the  event occurs, False otherwise.
  """
  # Generate a random integer between 1 and number (inclusive)
  random_number = random.randint(1, number)

  # The event occurs if the number is 1
  if random_number == 1:
    return True
  else:
    return False

# --- Helper method to be added to each room class ---
def _send_signal(self, signal_data):
    """Helper method to send signals using the registered callback."""
    if self._signal_callback:
        # print(f"{self.__class__.__name__} signaling: {signal_data}") # Optional: uncomment for debug
        try:
            self._signal_callback(signal_data)
        except Exception as e:
            print(f"Error sending signal from {self.__class__.__name__}: {e}")
    else:
        # print(f"{self.__class__.__name__} attempted to signal, but no callback registered: {signal_data}") # Optional: uncomment for debug
        pass # Silently fail if no callback is registered, or log loudly
# ------------------------------------------------------


class room_kitchen:
    def __init__(self, state_manager, signal=None):
        self._signal_callback=signal

        # Store the state_manager reference
        self.state = state_manager
        self.cook = cook()
        #print("Kitchen initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function

    def drink_water(self):
        print("Drinking water...")
        # You can now access the state_manager if needed
        edit=10
        self.state.adjust_stat("hydration", edit)
        message=f"Drank some water from the kitchen faucet! Got {edit} hydration points."
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/water_icon.png"})
        # ------------------------
        return message

    def prepare_food(self, process, items_list: str):
        """
        Prepares a food item using specified ingredients from the inventory.
        Validates that all required items exist in inventory, are of type 'consumable',
        and retrieves their detailed data for the AI process.
        Implements rollback logic for inventory changes on failure.

        Args:
            process (str): Description of the preparation process for the AI.
            items_list (str): A string of item IDs separated by '#'.

        Returns:
            str: An error message if validation or inventory management fails.
            str: A success message including details of created items.
        """
        # 1. Parse the input items_list
        required_item_id_strings = items_list.split("#")
        # Filter out empty strings that might result from split("#") like "id1##id2"
        required_item_id_strings = [item_id for item_id in required_item_id_strings if item_id]

        if not required_item_id_strings:
             return "Error: No items specified for preparation." # Handle empty input

        # Lists to store validated items and any errors encountered
        valid_ingredient_details = []
        validation_errors = []

        # 2. Iterate through required items and validate each one using get_item_details
        for item_id_str in required_item_id_strings:
            try:
                # Attempt to convert ID to integer
                item_id = int(item_id_str)
            except ValueError:
                # Handle cases where the ID string is not a valid integer
                validation_errors.append(f"Invalid item ID format: '{item_id_str}' is not an integer.")
                continue # Move to the next item in the list

            # Use get_item_details with internal=True
            # This gives us a dictionary result regardless of accessibility or status
            item_check_result = self.state.get_item_details(item_id, internal=True)

            # 3. Check the status and location of the item based on the returned dictionary
            if item_check_result["status"] == "found":
                # Item was found, now check its location and type
                item_data = item_check_result["details"] # Get the actual item data dict
                item_location = item_check_result["location"]
                item_type = item_data.get("type")
                item_name = item_data.get('name', f'ID {item_id}') # Get name for clearer errors

                if item_location == "inventory":
                    # Item is in inventory, now check if it's consumable
                    if item_type == "consumable":
                        # Item is found, in inventory, and consumable - looks good!
                        valid_ingredient_details.append(item_data)
                    else:
                        # Item is not consumable
                        validation_errors.append(f"Item '{item_name}' (ID: {item_id}) is of type '{item_type}', but only 'consumable' items can be used as ingredients.")
                else:
                    # Item is found but not in inventory (e.g., in a room)
                    validation_errors.append(f"Item '{item_name}' (ID: {item_id}) is required but is not in your inventory. It is located in '{item_location}'.")

            elif item_check_result["status"] == "not_found":
                 # Item was not found anywhere
                 validation_errors.append(f"Required item with ID '{item_id}' was not found.")

            # elif item_check_result["status"] == "not_accessible":
                 # Item exists but is not in the current room or inventory.
                 # This status implies it's *somewhere*, but the location check above already covers
                 # if it's not "inventory". So this check is redundant for the *must be in inventory* rule.
                 # pass

            elif item_check_result["status"] == "error":
                 # An error occurred during lookup
                 error_message = item_check_result.get("message", "An unknown error occurred.")
                 validation_errors.append(f"Error retrieving details for item ID '{item_id}': {error_message}")

        # 4. Check if any validation errors occurred
        if validation_errors:
            print("Preparation failed due to validation errors:")
            for error in validation_errors:
                print(f"- {error}")
            return "Preparation failed: " + "; ".join(validation_errors)

        # If we reached here, all initial validation passed!
        print(f"All {len(valid_ingredient_details)} required items found in inventory and are consumable.")

        # --- Proceed with the rest of the preparation logic ---

        # 6. Call cook/AI API with `process` description and `valid_ingredient_details`
        print(f"Calling cook.prepare_food with process: '{process}' and ingredients: {valid_ingredient_details}")
        try:
            # Assume cook.prepare_food returns a list of item data dictionaries or None/empty list on certain conditions
            list_generated_items_data = self.cook.prepare_food(valid_ingredient_details, process)

            if not list_generated_items_data:
                 print("Cook process generated no output items.")
                 # If no items are generated, the process is "complete" in that ingredients weren't used,
                 # and nothing was created. No rollback of ingredients needed as they weren't removed.
                 # --- Add signal call for process completion without output ---
                 self._send_signal({"type": "show_message", "message": "Preparation process completed, but no food items were created by the cook."})
                 # -----------------------------------------------------------
                 return "Preparation process completed, but no food items were created by the cook."
        except Exception as e:
            print(f"Error during cook process: {e}")
            # If the cook process itself fails, ingredients haven't been removed yet. No rollback needed.
            # --- Add signal call for cook process failure ---
            self._send_signal({"type": "show_message", "message": f"Preparation failed: Error during food generation process: {e}"})
            # ------------------------------------------------
            return f"Preparation failed: Error during food generation process: {e}"


        # Lists to track state changes for potential rollback
        successfully_removed_ingredients_data = [] # Store full data to add back
        successfully_created_items_info = []     # Store id, location_type, location_id, name for removal

        # 7. Manage state: Remove used items first
        print(f"Attempting to remove ingredients...")
        # Iterate through the validated ingredient data list to get IDs and data for removal
        for original_ingredient_data in valid_ingredient_details:
            item_id_str = original_ingredient_data.get('id')
            item_name = original_ingredient_data.get('name', f'ID {item_id_str}')

            # Safety check for data integrity, though validation should cover ID format
            if item_id_str is None:
                 print(f"Internal Error: Ingredient data missing ID during removal attempt: {original_ingredient_data}")
                 # Rollback what we *could* have removed (should be empty at this point if first item fails)
                 self._rollback_preparation(successfully_removed_ingredients_data, successfully_created_items_info)
                 return "Preparation failed: Internal error processing ingredient data (missing ID)."

            try:
                inted_id = int(item_id_str)
            except ValueError:
                 # Safety check for ID format, though validation should cover this
                 print(f"Internal Error: Ingredient ID '{item_id_str}' is not a valid integer during removal attempt.")
                 self._rollback_preparation(successfully_removed_ingredients_data, successfully_created_items_info)
                 return "Preparation failed: Internal error with ingredient ID format."


            # Attempt to remove the item from inventory
            # Assuming self.state.remove_item(item_id, internal=True) removes the item by ID
            # This assumption is based on the original code's usage. If location matters for removal,
            # the state manager needs a different method signature or logic.
            if self.state.remove_item(inted_id, internal=True):
                print(f"Successfully removed ingredient '{item_name}' (ID: {inted_id}).")
                # Store the original item data for potential rollback (adding back to inventory)
                successfully_removed_ingredients_data.append(original_ingredient_data)
            else:
                # Removal failed for this ingredient
                print(f"Error: Failed to remove ingredient '{item_name}' (ID: {inted_id}) from inventory. Check state manager logs.")
                # Attempt to add back any ingredients that were successfully removed before this failure
                self._rollback_preparation(successfully_removed_ingredients_data, successfully_created_items_info)
                # --- Add signal call for ingredient removal failure ---
                self._send_signal({"type": "show_message", "message": f"Preparation failed: Could not remove ingredient '{item_name}' (ID: {inted_id}) from inventory. Rolled back partial changes."})
                # ------------------------------------------------------
                return f"Preparation failed: Could not remove ingredient '{item_name}' (ID: {inted_id}) from inventory. Rolled back partial changes."

        # All ingredients successfully removed
        print("All ingredients successfully removed from inventory.")

        # Now add the new items generated by the cook process
        print(f"Attempting to create {len(list_generated_items_data)} generated items...")

        # Location for created items, hardcoded 200002 as in original code snippet
        # Here it is hardcoded with the ID for the initial kitchen, in practice, this function will only be ever active
        # if the user is in the kitchen already, so placing the items directly into it is fine

        # add to the kitchen if inventory is full, else, add to inventory
        if self.state.is_inventory_full():
            creation_location_type = "room"
            creation_location_id = 200002
        else:
            creation_location_type = "inventory"
            creation_location_id = None # Inventory doesn't have a room ID


        for generated_item_data in list_generated_items_data:
            item_name = generated_item_data.get('name', 'Unnamed Item')

            # Attempt to create the item at the specified location
            # Assuming create_item returns the new item_id (e.g., an integer) on success, and False/None on failure
            new_item_id = self.state.create_item(creation_location_type, creation_location_id, generated_item_data, internal=True)

            # Check for successful ID return (an integer ID is truthy, None/False are falsy)
            if new_item_id is not None and new_item_id is not False: # Be explicit about checking for non-None and non-False
                 print(f"Successfully created item '{item_name}' with ID {new_item_id} in {creation_location_type} {creation_location_id}.")
                 # Store info for potential rollback (removing the newly created item)
                 successfully_created_items_info.append({
                     "id": new_item_id,
                     "location_type": creation_location_type,
                     "location_id": creation_location_id,
                     "name": item_name # Store name for reporting/logging in rollback
                 })
            else:
                # Creation failed for this item
                print(f"Error: Failed to create item '{item_name}' in {creation_location_type} {creation_location_id}. Check state manager logs.")
                # Attempt rollback: add ingredients back, remove any successfully created items
                self._rollback_preparation(successfully_removed_ingredients_data, successfully_created_items_info)
                # --- Add signal call for item creation failure ---
                self._send_signal({"type": "show_message", "message": f"Preparation failed: Could not create generated item '{item_name}'. Rolled back inventory changes."})
                # -------------------------------------------------
                return f"Preparation failed: Could not create generated item '{item_name}'. Rolled back inventory changes."

        # All new items successfully created
        print(f"Successfully created {len(successfully_created_items_info)} new items.")

        # 8. Return success result
        created_item_names = [item_info.get('name', f"ID {item_info.get('id', '?')}") for item_info in successfully_created_items_info]
        # --- Add signal call for successful preparation ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/plate_icon.png"})
        # --------------------------------------------------
        return f"Preparation successful! Items created and placed in {creation_location_type}: {', '.join(created_item_names)}."


    def _rollback_preparation(self, removed_ingredients_data, created_items_info):
        """
        Helper method to attempt reversing inventory changes made during a failed preparation.
        Adds back ingredients removed and removes new items created before the failure point.
        """
        print("Preparation failed, attempting rollback...")
        # --- Add signal call for rollback attempt ---
        self._send_signal({"type": "show_message", "message": "Preparation failed, attempting rollback...", "urgent": True})
        # --------------------------------------------

        # 1. Add back ingredients that were successfully removed
        print(f"Attempting to add back {len(removed_ingredients_data)} ingredients...")
        # Ingredients were originally validated as being in "inventory". Add them back there.
        rollback_add_location_type = "inventory"
        rollback_add_location_id = None # Inventory typically doesn't have a room ID

        for item_data in removed_ingredients_data:
            item_id = item_data.get('id', '?') # Get original ID for logging
            item_name = item_data.get('name', 'Unnamed')
            print(f"Attempting to add back ingredient: '{item_name}' (Original ID: {item_id}) to inventory.")
            # Assuming create_item can add to "inventory" with location_id=None
            # And assuming create_item returns the new item's ID on success, False/None on failure
            new_item_id_after_rollback_add = self.state.create_item(rollback_add_location_type, rollback_add_location_id, item_data, internal=True)

            if new_item_id_after_rollback_add is None or new_item_id_after_rollback_add is False:
                 # This is a critical error: an ingredient was removed and could not be put back.
                 print(f"CRITICAL ERROR: Failed to add back ingredient '{item_name}' (Original ID: {item_id}) during rollback. Item may be lost from inventory! Manual restoration needed.")
                 # --- Add signal call for critical rollback failure (ingredient lost) ---
                 self._send_signal({"type": "show_message", "message": f"CRITICAL ERROR: Failed to add back ingredient '{item_name}' during rollback. Item may be lost!", "urgent": True})
                 # ---------------------------------------------------------------------
            else:
                 # Note: The ID might change when re-added depending on state manager implementation
                 print(f"Successfully added back ingredient '{item_name}'. New ID: {new_item_id_after_rollback_add}")
                 # --- Add signal call for successful ingredient rollback ---
                 self._send_signal({"type": "show_message", "message": f"Successfully added back ingredient '{item_name}'."})
                 # --------------------------------------------------------


        # 2. Remove items that were successfully created
        print(f"Attempting to remove {len(created_items_info)} created items...")
        for item_info in created_items_info:
             item_id = item_info.get('id')
             item_name = item_info.get('name', 'Unnamed')
             item_location_type = item_info.get('location_type')
             item_location_id = item_info.get('location_id')

             if item_id is not None:
                 print(f"Attempting to remove created item '{item_name}' (ID: {item_id}) from {item_location_type} {item_location_id} for rollback...")
                 # Items were created at item_info['location_type'], item_info['location_id'].
                 # The original code used `remove_item(id, internal=True)`. This signature
                 # might not be sufficient to reliably remove an item from a specific location
                 # if there are multiple items with the same ID or the state manager
                 # requires location context for removal outside of inventory.
                 # Using the original signature but highlighting potential issue.
                 if not self.state.remove_item(item_id, internal=True):
                      # If rollback of a created item fails, it means a duplicate item is left at the creation location.
                     print(f"CRITICAL ERROR: Failed to remove created item '{item_name}' (ID: {item_id}) from {item_location_type} {item_location_id} during rollback. Duplicate item created! Manual cleanup needed.")
                     # --- Add signal call for critical rollback failure (item not removed) ---
                     self._send_signal({"type": "show_message", "message": f"CRITICAL ERROR: Failed to remove created item '{item_name}' during rollback. Duplicate item created!", "urgent": True})
                     # --------------------------------------------------------------------
                 else:
                     print(f"Successfully removed created item ID {item_id} during rollback.")
                     # --- Add signal call for successful item rollback ---
                     self._send_signal({"type": "show_message", "message": f"Successfully removed created item '{item_name}'."})
                     # --------------------------------------------------
             else:
                  print(f"Internal Error: Created item info missing ID for rollback: {item_info}")

        print("Rollback attempt finished.")
        # --- Add signal call for rollback completion ---
        self._send_signal({"type": "show_message", "message": "Rollback attempt finished."})
        # -----------------------------------------------


class room_bathroom:
    def __init__(self, state_manager, signal=None):
        self._signal_callback=signal
        # Store the state_manager reference
        self.state = state_manager
        #print("Bathroom initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function


    # Make methods instance methods by adding 'self'
    def drink_water(self):
        print("Drinking water...")
        # You can now access the state_manager if needed
        edit=10
        self.state.adjust_stat("hydration", edit)
        message=f"Drank some water from the faucet! Got {edit} hydration points."
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/water_icon.png"})
        # ------------------------
        return message

    # Make methods instance methods by adding 'self'
    def wash_hands(self):
        edit=2
        print("Washing hands...")
        self.state.adjust_stat("hydration", edit) # Washing hands might not give hydration, maybe hygiene or something else?
        message=f"You wash your hands, you feel refreshed."
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/water_icon.png"}) # Or a soap icon?
        # ------------------------
        return message


# Define Bedroom Class - similarly, accept state_manager
class room_bedroom:
    def __init__(self, state_manager, signal=None):
        self._signal_callback=signal
        # Store the state_manager reference
        self.state = state_manager
        #print("Bedroom initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function

    # Add instance methods here
    def sleep(self, seconds):
        #print("Going to sleep in the bedroom...")
        message=self.state.sleep(seconds)
        # completely delegated to the state manager
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/pillow_icon.png"})
        # ------------------------
        return message

    def hug_pillow(self):
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/pillow_icon.png"})
        # ------------------------
        return "You give the pillow a big hug, it is comfortable."

    def look_under_bed(self):
        message=f"You look uder the bed around and found nothing."
        # --- Add signal call for looking ---
        self._send_signal({"type": "show_message", "message": "You look under the bed..."})
        # -----------------------------------
        if check_one_in(50):
            found_item=random_object.load_and_get_random_item("world_data/underbed_found_data.json")
            creation_message=self.state.create_item("inventory", None, found_item)
            message=f"You found something under the bed! {creation_message}."
            # --- Add signal call for finding something ---
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/item_found_icon.png"}) # Example icon
            # -------------------------------------------

        return message


class room_garden:
    def __init__(self, state_manager, signal=None):
        self._signal_callback=signal
        # Store the state_manager reference
        self.state = state_manager
        #print("Garden initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function

    def lay_down(self):
        edit=5
        self.state.adjust_stat("energy", edit)
        message=f"You lay down in the middle of the garden. The fresh ambience makes you feel revilatized, you recover {edit} energy points."
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/lying_icon.png"}) # Example icon
        # ------------------------
        return message

    def dig_hole(self):
        edit=-15
        self.state.adjust_stat("energy", edit)
        self.state.adjust_stat("hydration", edit)
        self.state.adjust_stat("fullness", edit)
        message=f"You dig around and found nothing, all your stats have been lowered by {abs(edit)}. It at least was a good excercise." # Use abs for positive display
        # --- Add signal call for digging ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/dig_icon.png"})
        # -----------------------------------
        if check_one_in(200):
            found_item=random_object.load_and_get_random_item("world_data/garden_found_items_data.json")
            creation_message=self.state.create_item("inventory", None, found_item)
            message=f"While digging on the garden you found something! {creation_message}. All your stats have been lowered by {abs(edit)} for digging around."
             # --- Add signal call for finding something while digging ---
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/item_found_icon.png"}) # Example icon
            # ---------------------------------------------------------

        return message


class room_living_room:
    def __init__(self, state_manager, signal=None):
        self._signal_callback=signal
        # Store the state_manager reference
        self.state = state_manager
        #print("Living room initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function

    def watch_tv(self):
        """
        Returns an excerpt of a random TV show based on the current time
        delegated to a TV manager
        """
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/tv_icon.png"})
        # ------------------------
        return tv_handle.get_tv_program()

    def sit_on_couch(self):
        edit=1
        message=f"You sit down on the couch for a while, you feel like you are sinking into it. Gained {edit} energy points."
        if check_one_in(10):
            edit=5
            message=f"You sit down, the world seems to pass really slowly for now. You rested for {edit} energy points"

        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/sofa_icon.png"})
        # ------------------------
        self.state.adjust_stat("energy", edit)
        return message

    def look_at_window(self):
        """
        Returns a string with the current weather information
        delegated to Open Meteo handle
        """
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/window_icon.png"})
        # ------------------------
        return open_meteo_handle.get_full_weather()



class room_computer:
    def __init__(self, state_manager, signal=None):
        self._signal_callback=signal
        # Store the state_manager reference
        self.state = state_manager
        #print("Computer room initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function


    def write_blog_post(self, post):
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/writing_icon.png"}) # Example icon
        # ------------------------
        # Implement blog writing logic... maybe adjust a stat or create an item?
        return f"You wrote a blog post about: {post}. It feels good to express yourself."


    def random_wikipedia(self):
        "Delegated, returns a structured string with title and body for a random wikipedia article"
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/computer_icon.png"})
        # ------------------------
        return wiki_handle.fetch_random_wiki_article()



class room_white:
    def __init__(self, state_manager, signal=None): # <-- Removed the extra 'main_handler' argument
        self._signal_callback=signal
        # Store the state_manager reference
        self.state = state_manager
        #print("White room initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function

    def meditate(self, thoughts):
        edit=10
        self.state.adjust_stat("energy", edit)
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/meditate_icon.png"})
        # ------------------------
        return f"You begin to meditate, your mind is filled with thoughts at first, {thoughts}.\n As you keep going your mind begins to quiet down...\n...\n..."


# Define the main handler class
class main_tools_handle:
    def __init__(self, state_manager, signal=None):
        print("Main tools handler initialized.")
        self._signal_callback=signal # Store the main signal callback here
        # Store the state_manager reference
        self.state = state_manager

        # Instantiate the room classes and store them as attributes
        # Pass the state_manager AND the signal callback to the room instances
        self.bathroom = room_bathroom(self.state, self._signal_callback)
        self.bedroom = room_bedroom(self.state, self._signal_callback)
        self.living_room= room_living_room(self.state, self._signal_callback)
        self.computer = room_computer(self.state, self._signal_callback)
        self.garden = room_garden(self.state, self._signal_callback)
        # --- Fix: Removed the extra 'self' argument here ---
        self.white_room = room_white(self.state, self._signal_callback)
        # ---------------------------------------------------
        self.kitchen = room_kitchen(self.state, self._signal_callback)

    # You already have _send_signal in main_tools_handle, but it's not currently used
    # by the room methods. The approach above adds it *to* the room instances.
    # If you wanted main_tools_handle itself to send signals, you'd use this method.
    # For signals originating *from* room actions, adding the helper to the rooms is better.
    # You can keep this one if main_tools_handle might signal independently later.
    # def _send_signal(self, signal_data):
    #     """Helper method to send signals using the registered callback."""
    #     if self._signal_callback:
    #         print(f"main_tools_handle signaling: {signal_data}") # Optional: uncomment for debug
    #         try:
    #             self._signal_callback(signal_data)
    #         except Exception as e:
    #             print(f"Error sending signal from main_tools_handle: {e}")
    #     else:
    #         print(f"main_tools_handle attempted to signal, but no callback registered: {signal_data}") # Optional: uncomment for debug
    #         pass # Silently fail if no callback is registered, or log loudly