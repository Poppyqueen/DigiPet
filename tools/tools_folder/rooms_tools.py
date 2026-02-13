# rooms_tools.py

# State manager is being passed into this


# Here we cointain simple tools for each room, mostly based on
# flavor text

# Some use utils to interact with some simple APIs or data structures.

# the state manager has access to inventory and wellness stats access

import asyncio
import math

from tools.tools_folder.tools_helpers import random_object, tv_handle

from tools.tools_folder.tools_helpers.ai_cook import cook

import random

from utils.loc_datetime import datetime

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
    def __init__(self, state_manager, signal=None, config_manager=None):
        self._signal_callback=signal

        # Store the state_manager reference
        self.state = state_manager
        self.cook = cook(config_manager)
        #print("Kitchen initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function (?)

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

    def _scale_stats(self, stats_edit, amount):
        if not stats_edit:
            return {}
        return {k: round(v * amount, 2) for k, v in stats_edit.items()}
    
    def prepare_food(self, process, items_list):
        """
        Prepares a food item using specified ingredients from the inventory.
        Validates that all required items exist in inventory, are of type 'consumable' or 'tool',
        and retrieves their detailed data for the AI process.

        Consumable items will have their consume_uses_left decremented by the specified amount;
        if consume_uses_left reaches 0, the item is removed from inventory via self.state.remove_item.
        Tool items are passed to the cook AI but are never consumed.

        Implements rollback logic for inventory changes on failure.

        Args:
            process (str): Description of the preparation process for the AI.
            items_list (list of [item_id, amount]): Each entry is [int item_id, int amount].

        Returns:
            str: An error message if validation or inventory management fails.
            str: A success message including details of created items.
        """

        # --- 1. Validate input is not empty ---
        if not items_list:
            return "Error: No items specified for preparation."

        valid_consumable_details = []  # (item_data, amount_to_use)  — will be consumed
        valid_tool_details = []        # item_data only              — passed to AI, not consumed
        validation_errors = []

        # --- 2. Validate every item before touching any state ---
        for entry in items_list:
            # Validate entry shape
            if not (isinstance(entry, dict) and "item_id" in entry and "amount" in entry):
                validation_errors.append(f"Invalid entry format: {entry!r}. Expected {{'item_id': id, 'amount': amount}}.")
                continue

            item_id_raw = entry["item_id"]
            amount = entry["amount"]

            # Validate item_id type
            if not isinstance(item_id_raw, int):
                try:
                    item_id = int(item_id_raw)
                except (ValueError, TypeError):
                    validation_errors.append(f"Invalid item ID format: {item_id_raw!r} is not an integer.")
                    continue
            else:
                item_id = item_id_raw

            # Validate amount
            if not isinstance(amount, (int, float)) or amount <= 0:
                validation_errors.append(f"Invalid amount {amount!r} for item ID {item_id}: must be a positive number.")
                continue

            # Look up item
            item_check_result = self.state.get_item_details(item_id, internal=True)
            status = item_check_result.get("status")

            if status == "not_found":
                validation_errors.append(f"Required item with ID {item_id} was not found.")
                continue

            if status == "error":
                msg = item_check_result.get("message", "Unknown error.")
                validation_errors.append(f"Error retrieving item ID {item_id}: {msg}")
                continue

            if status == "found":
                item_data = item_check_result["details"]
                item_location = item_check_result["location"]
                item_name = item_data.get("name", f"ID {item_id}")
                item_type_list = item_data.get("type", [])

                if item_location != "inventory":
                    validation_errors.append(
                        f"Item '{item_name}' (ID: {item_id}) is not in your inventory "
                        f"(found in '{item_location}')."
                    )
                    continue

                if "consumable" in item_type_list:
                    consume_uses_left = item_data.get("consume_consume_uses_left")
                    if consume_uses_left is not None and amount > consume_uses_left:
                        validation_errors.append(
                            f"Item '{item_name}' (ID: {item_id}) only has {consume_uses_left} use(s) left, "
                            f"but {amount} were requested."
                        )
                        continue
                    valid_consumable_details.append((item_data, amount))

                elif "tool" in item_type_list:
                    valid_tool_details.append(item_data)

                else:
                    validation_errors.append(
                        f"Item '{item_name}' (ID: {item_id}) has type {item_type_list!r}; "
                        f"only 'consumable' or 'tool' items can be used."
                    )

        if validation_errors:
            print("Preparation failed due to validation errors:")
            for error in validation_errors:
                print(f"  - {error}")
            return "Preparation failed: " + "; ".join(validation_errors)

        print(
            f"Validation passed: {len(valid_consumable_details)} consumable(s), "
            f"{len(valid_tool_details)} tool(s)."
        )

        # --- 3. Call cook AI (no state changes yet) ---
        COOK_AI_FIELDS = {"name", "descriptions", "effects", "stats_edit"}


        all_ingredient_details = [
            {**{k: v for k, v in d.items() if k in COOK_AI_FIELDS},
            "amount": amount,
            "stats_edit": self._scale_stats(d.get("stats_edit"), amount)}
            for d, amount in valid_consumable_details
        ] + [
            {**{k: v for k, v in d.items() if k in COOK_AI_FIELDS},
            "stats_edit": self._scale_stats(d.get("stats_edit"), 1)}
            for d in valid_tool_details
        ]

        print(f"Calling cook.prepare_food — process: '{process}', ingredients: {all_ingredient_details}")

        try:
            list_generated_items_data = self.cook.prepare_food(all_ingredient_details, process)
        except Exception as e:
            print(f"Error during cook process: {e}")
            return f"Preparation failed: Error during food generation process: {e}"

        if not list_generated_items_data:
            print("Cook process generated no output items.")
            return "Preparation process completed, but no food items were created by the cook."

        # --- 4. Create new items BEFORE consuming ingredients ---
        # If creation fails here, nothing has been consumed yet — no rollback needed.
        current_room_id = self.state.get_current_room_id()
        if self.state.is_inventory_full():
            creation_location_type = "room"
            creation_location_id = current_room_id
        else:
            creation_location_type = "inventory"
            creation_location_id = None

        successfully_created_items_info = []

        print(f"Creating {len(list_generated_items_data)} new item(s) in {creation_location_type}...")
        for generated_item_data in list_generated_items_data:
            item_name = generated_item_data.get("name", "Unnamed Item")
            new_item_ids = self.state.create_item(
                creation_location_type, creation_location_id, generated_item_data, internal=True
            )

            if new_item_ids and isinstance(new_item_ids, list):
                for new_item_id in new_item_ids:
                    print(f"  Created '{item_name}' → ID {new_item_id}.")
                    successfully_created_items_info.append({
                        "id": new_item_id,
                        "location_type": creation_location_type,
                        "location_id": creation_location_id,
                        "name": item_name,
                    })
            else:
                # Nothing was consumed yet, so just clean up any items created in this loop.
                print(f"  Failed to create '{item_name}'. Rolling back {len(successfully_created_items_info)} already-created item(s).")
                self._rollback_preparation([], successfully_created_items_info)
                return (
                    f"Preparation failed: Could not create generated item '{item_name}'. "
                    "No ingredients were consumed. Rolled back partial item creation."
                )

        print("All new items created successfully.")

        # --- 5. Consume ingredients (decrement consume_uses_left, remove at 0) ---
        # Rollback from here means removing the created items above.
        successfully_consumed = []  # track for rollback: (item_data, new_consume_uses_left)

        print("Consuming ingredients...")
        for item_data, amount in valid_consumable_details:
            item_id = int(item_data.get("id"))
            item_name = item_data.get("name", f"ID {item_id}")
            consume_uses_left = item_data.get("consume_consume_uses_left")

            if consume_uses_left is not None:
                new_consume_uses_left = consume_uses_left - amount

                if new_consume_uses_left <= 0:
                    # Remove the item entirely
                    if not self.state.remove_item(item_id, internal=True):
                        print(f"  Failed to remove depleted item '{item_name}' (ID: {item_id}).")
                        self._rollback_preparation(successfully_consumed, successfully_created_items_info)
                        return (
                            f"Preparation failed: Could not remove depleted ingredient '{item_name}' "
                            "(ID: {item_id}). Rolled back changes."
                        )
                    print(f"  Removed depleted item '{item_name}' (ID: {item_id}).")
                    successfully_consumed.append((item_data, 0))
                else:
                    # Decrement consume_uses_left
                    if not self.state.inventory_service.set_item_attribute(item_id, "consume_consume_uses_left", new_consume_uses_left):
                        print(f"  Failed to decrement consume_uses_left for '{item_name}' (ID: {item_id}).")
                        self._rollback_preparation(successfully_consumed, successfully_created_items_info)
                        return (
                            f"Preparation failed: Could not update consume_uses_left for ingredient '{item_name}' "
                            f"(ID: {item_id}). Rolled back changes."
                        )
                    print(f"  '{item_name}' (ID: {item_id}): consume_uses_left {consume_uses_left} → {new_consume_uses_left}.")
                    successfully_consumed.append((item_data, new_consume_uses_left))
            else:
                # Item has no consume_uses_left field — remove it entirely (legacy / uncounted consumable)
                if not self.state.remove_item(item_id, internal=True):
                    print(f"  Failed to remove ingredient '{item_name}' (ID: {item_id}).")
                    self._rollback_preparation(successfully_consumed, successfully_created_items_info)
                    return (
                        f"Preparation failed: Could not remove ingredient '{item_name}' "
                        f"(ID: {item_id}). Rolled back changes."
                    )
                print(f"  Removed ingredient '{item_name}' (ID: {item_id}) (no consume_uses_left field).")
                successfully_consumed.append((item_data, None))

        print("All ingredients consumed successfully.")

        # --- 6. Success ---
        item_names_and_ids = [
            f"{info.get('name', 'Unnamed')} (ID: {info.get('id', '?')})"
            for info in successfully_created_items_info
        ]
        self._send_signal({
            "type": "show_icon_popup",
            "icon_path": "style/images/action_icons/plate_icon.png",
            "popup_type": 2,
        })
        return (
            f"Preparation successful! "
            f"New item(s) created in {creation_location_type}: {', '.join(item_names_and_ids)}."
        )

    def _rollback_preparation(self, consumed_ingredients, created_items_info):
        """
        Reverses inventory changes from a failed preparation.

        Args:
            consumed_ingredients: list of (item_data, new_consume_uses_left) tuples.
                new_consume_uses_left == 0  → item was removed; re-create it in inventory.
                new_consume_uses_left > 0   → consume_uses_left was decremented; restore the old value.
                new_consume_uses_left None  → item had no consume_uses_left field and was removed; re-create it.
            created_items_info: list of {"id", "location_type", "location_id", "name"} dicts
                for items that were already created and must be removed.
        """
        print("Preparation failed — attempting rollback...")

        # 1. Undo ingredient consumption (reverse order for cleanliness)
        for item_data, new_consume_uses_left in reversed(consumed_ingredients):
            item_id = item_data.get("id", "?")
            item_name = item_data.get("name", "Unnamed")

            if new_consume_uses_left == 0 or new_consume_uses_left is None:
                # Item was fully removed — re-create it in inventory
                print(f"  Re-creating removed ingredient '{item_name}' (original ID: {item_id})...")
                new_ids = self.state.create_item("inventory", None, item_data, internal=True)
                if not new_ids:
                    print(f"  CRITICAL: Failed to re-create '{item_name}'. Item may be lost!")
                else:
                    print(f"  Re-created '{item_name}' → new ID: {new_ids[0]}.")
            else:
                # consume_uses_left was decremented — restore the previous value
                original_consume_uses_left = item_data.get("consume_consume_uses_left")
                print(
                    f"  Restoring consume_uses_left for '{item_name}' (ID: {item_id}): "
                    f"{new_consume_uses_left} → {original_consume_uses_left}..."
                )
                if not self.state.inventory_service.set_item_attribute(
                    int(item_id), "consume_consume_uses_left", original_consume_uses_left
                ):
                    print(f"  CRITICAL: Failed to restore consume_uses_left for '{item_name}' (ID: {item_id})!")
                else:
                    print(f"  Restored consume_uses_left for '{item_name}'.")

        # 2. Remove any items that were already created
        for item_info in reversed(created_items_info):
            item_id = item_info.get("id")
            item_name = item_info.get("name", "Unnamed")
            if item_id is None:
                print(f"  Internal error: created item info missing ID: {item_info}")
                continue
            print(f"  Removing created item '{item_name}' (ID: {item_id})...")
            if not self.state.remove_item(item_id, internal=True):
                print(f"  CRITICAL: Failed to remove created item '{item_name}' (ID: {item_id}). Duplicate may exist!")
            else:
                print(f"  Removed created item '{item_name}' (ID: {item_id}).")

        print("Rollback complete.")


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
    def __init__(self, state_manager, signal=None, memory=None):
        self.memory=memory
        self._signal_callback=signal
        # Store the state_manager reference
        self.state = state_manager
        #print("Bedroom initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function

    # Add instance methods here
    async def sleep(self, seconds):
        #print("Going to sleep in the bedroom...")
        #message=self.state.sleep(seconds)
        constant = 1
        # Using square root:
        energy_gain = constant * math.sqrt(seconds)
        # self.memory.save_to_memory("You beggin your sleep process.", "short_term", "user")
        self._send_signal({"type": "show_message_popup", "message": f"Entering sleep for {seconds} seconds!"})
        #int_gain=int(energy_gain)
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/pillow_icon.png"})
        self._send_signal({"type": "start_sleep", "time_to_sleep": seconds})
        await asyncio.sleep(seconds)
        self._send_signal({"type": "end_sleep"})
        self.state.adjust_stat("energy", energy_gain)

        # completely delegated to the state manager
        # --- Add signal call ---
        # ------------------------
        return f"You rested for {seconds} seconds, recovering {energy_gain} energy points. You feel refreshed."

    def hug_pillow(self):
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/pillow_icon.png"})
        # ------------------------
        return "You give the pillow a big hug, it is comfortable."

    def look_under_bed(self):
        message=f"You look uder the bed around and found nothing."
        # --- Add signal call for looking ---
        #self._send_signal({"type": "show_message", "message": "You look under the bed..."})
        # -----------------------------------
        if check_one_in(50):
            found_item=random_object.load_and_get_random_item("found_items/underbed_found_data.json")
            #found_item=random_object.load_and_get_random_item("food_n_drinks/")

            creation_message=self.state.create_item("inventory", None, found_item)
            message=f"You found something under the bed! It is a {found_item["name"]}, it is now in your inventory."
            # --- Add signal call for finding something ---
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/item_found_icon.png"}) # Example icon
            # -------------------------------------------

        return message


class room_garden:
    def __init__(self, state_manager, signal=None, open_meteo=None):
        self._signal_callback=signal
        # Store the state_manager reference
        self.state = state_manager
        self.open_meteo = open_meteo
        #print("Garden initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function

    def display_information(self):
        return self.open_meteo.get_full_weather()
        

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
        if check_one_in(50):
            found_item=random_object.load_and_get_random_item("found_items/garden_found_items_data.json")
            creation_message=self.state.create_item("inventory", None, found_item)
            message=f"While digging on the garden you found something! It is a {found_item["name"]}! It's been added to your inventory. All your stats have been lowered by {abs(edit)} for digging around."
             # --- Add signal call for finding something while digging ---
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/dig_icon.png", "popup_type": 2}) # Example icon
            # ---------------------------------------------------------

        return message


class room_living_room:
    def __init__(self, state_manager, signal=None, open_meteo=None):
        self._signal_callback=signal
        # Store the state_manager reference
        self.state = state_manager

        self.open_meteo = open_meteo

        self.last_show_watched=""
        #print("Living room initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function

    def display_information(self):
        message=f"The last TV show watched was:\n {self.last_show_watched}"
        return message
    
    def take_a_seat(self, item_id:int):
        item_details=self.state.get_item_details(item_id,internal=True)
        if item_details["status"] == "found":
            if "seat" in item_details["details"]["type"]:
                print(f"Ok to sit on!")
                edit=1
                message=f"You sit down for a while, you feel like you are sinking as you relax. Gained {edit} energy points."
                if check_one_in(10):
                    edit=5
                    message=f"You sit down, the world seems to pass really slowly for now. You rested for {edit} energy points"
                string_desc= "\n".join(item_details["details"]["descriptions"])
                self.state.adjust_stat("energy", edit)
                return f"You take a sit on the {item_details["details"]["name"]}\n {string_desc} \n {message}"
            return f"Item {item_id} {item_details["details"]["name"]} would not be a good place to sit on!"
        return f"Item {item_id} not found."
        

    def watch_tv(self):
        """
        Returns an excerpt of a random TV show based on the current time
        delegated to a TV manager
        """
        tv_show=tv_handle.get_tv_program()
        self.last_show_watched=tv_show
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/tv_icon.png"})
        # ------------------------
        return tv_show

    def sit_on_couch(self):
        edit=1
        message=f"You sit down for a while, you feel like you are sinking as you relax. Gained {edit} energy points."
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
        return self.open_meteo.get_full_weather()



class room_computer:
    def __init__(self, state_manager, signal=None, wiki=None):
        self._signal_callback=signal
        self.wiki=wiki
        # Store the state_manager reference
        self.state = state_manager

        self.last_accessed_wiki=""
        self.last_wiki_query=""
        #print("Computer room initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function

    def display_information(self):
        message=f"""The last query made into the wiki was:\n{self.last_wiki_query}\n
                    The last accessed article was: \n{self.last_accessed_wiki}\n 
                """
        return message

    def write_blog_post(self, post):        
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/writing_icon.png"}) # Example icon
        # ------------------------
        # Implement blog writing logic... maybe adjust a stat or create an item?
        return f"You wrote a blog post about: {post}. It feels good to express yourself."


    def random_wikipedia(self):
        "Delegated, returns a structured string with title and body for a random wikipedia article"
        # --- Add signal call ---
        edit=-2
        self.state.adjust_stat("energy", edit)

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/computer_icon.png"})
        # ------------------------
        article=self.wiki.fetch_random_wiki_article()
        self.last_accessed_wiki=article
        return article
    
    def search_wikipedia_articles(self, query):
        "Delegated, returns a structured string with title and body for a random wikipedia article"
        edit=-2
        self.state.adjust_stat("energy", edit)
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/computer_icon.png"})
        # ------------------------
        query_result=self.wiki.search_wikipedia(query)
        self.last_wiki_query=query_result
        return query_result

    def get_wikipedia_article_content(self, title):
        "Delegated, returns a structured string with title and body for a random wikipedia article"
        edit=-5
        self.state.adjust_stat("energy", edit)
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/computer_icon.png"})
        # ------------------------
        article=self.wiki.get_wikipedia_content_by_title(title)
        self.last_accessed_wiki=article
        return article
    
    
    



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
    def __init__(self, state_manager, signal=None, memory_manager=None, config_manager=None, open_meteo=None):
        self.memory=memory_manager

        wikipedia_enabled = config_manager.get_config('Tools', "enable_wikipedia")


        print(f"DEBUG: WIKPEDIA enabled (config): {wikipedia_enabled}")

        self.wiki=None
        if wikipedia_enabled:
            try: 
                from tools.tools_folder.tools_helpers.services.wiki_handle import Wikipedia_handle
                self.wiki=Wikipedia_handle(self.memory)
            except Exception as e:
                print(f"Error initializing Wikipedia_handle: {e}")

        print("Main tools handler initialized.")
        self._signal_callback=signal # Store the main signal callback here
        # Store the state_manager reference
        self.state = state_manager

        self.open_meteo = open_meteo

        # Instantiate the room classes and store them as attributes
        # Pass the state_manager AND the signal callback to the room instances
        self.bathroom = room_bathroom(self.state, self._signal_callback)
        self.bedroom = room_bedroom(self.state, self._signal_callback, self.memory)
        self.living_room= room_living_room(self.state, self._signal_callback, self.open_meteo)
        self.computer = room_computer(self.state, self._signal_callback, self.wiki)
        self.garden = room_garden(self.state, self._signal_callback, self.open_meteo)
        # --- Fix: Removed the extra 'self' argument here ---
        self.white_room = room_white(self.state, self._signal_callback)
        # ---------------------------------------------------
        self.kitchen = room_kitchen(self.state, self._signal_callback, config_manager)

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