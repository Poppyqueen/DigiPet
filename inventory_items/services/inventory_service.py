
# services/inventory_service.py
from __future__ import annotations

from utils.loc_datetime import datetime

import json


from inventory_items.item_pydantic_models import validate_item_dict, ignore_fingerprint_keys

import copy

from typing import Literal


from inventory_items.services.return_objects import (
    ItemLookupResult,
    ItemCreationResult,
    ItemRemovalResult,
    SetItemAttributeResult,
    InventoryItemEntry,
    InventoryStateResult,
)



class InventoryService:
    MAX_INVENTORY_SLOTS = 30

    def __init__(self, state_store, signal_callback):
        self._state_store = state_store
        self._signal_callback = signal_callback
        self._room_manager = None # Dependency to be set later

    def _get_item_stacking_key(self, item_data: dict):
        """
        Generates a key for comparing stackable items.
        Attributes that should NOT affect stacking (like ID, quantity, descriptions) are excluded.
        """
        if not item_data.get("stackable", False):
            return None # Only stackable items have a stacking key

        # Create a deep copy to avoid modifying the original item_data if it's a mutable dict
        # then filter out non-stacking attributes.
        stacking_attrs = {}
        for k, v in item_data.items():
            if k not in ignore_fingerprint_keys: # We need to decide what we will ignore
                # last_modified and location_history are examples of other attributes
                # that shouldn't affect stacking. Add or remove as needed.
                stacking_attrs[k] = v
        
        # Use json.dumps with sort_keys=True for a consistent, comparable string
        # for complex nested structures like lists or dictionaries within stacking_attrs.
        return json.dumps(stacking_attrs, sort_keys=True)

    def _find_matching_stack_in_list(self, item_list: list, item_to_match: dict):
        """
        Finds an existing stack in a given list (inventory or room items) that matches
        the item_to_match's stacking key and has space.
        Returns the matching item dictionary (mutable reference) or None.
        """
        if not item_to_match.get("stackable", False):
            return None # Only stackable items can match stacks

        item_stacking_key = self._get_item_stacking_key(item_to_match)
        if item_stacking_key is None:
            return None

        for existing_item in item_list:
            if isinstance(existing_item, dict) and existing_item.get("stackable", False):
                if self._get_item_stacking_key(existing_item) == item_stacking_key:
                    # Check if there's space in the stack
                    current_quantity = existing_item.get("quantity", 0)
                    max_size = existing_item.get("max_stack_size", float('inf')) # Use infinity if no max_stack_size
                    if current_quantity < max_size:
                        return existing_item
        return None

    def set_room_manager(self, room_manager_instance):
        """Sets the RoomManager dependency to resolve circular dependency."""
        self._room_manager = room_manager_instance

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal: {e}")


    def _emit_inventory_signals(self) -> None:
        """
        Fires room_inventory and player_inventory signals with current
        display strings. Call this after any mutation to keep the GUI in sync.

        Replaces the repeated list_inventories(formatted=True) + two signal
        pattern that previously appeared in every mutating method.
        """
        state = self.get_inventory_state()
        self._send_signal({"type": "room_inventory",   "item_list": state.room_display_strings})
        self._send_signal({"type": "player_inventory", "item_list": state.inventory_display_strings})

    # --- Helper Methods (Internal to InventoryService) ---
    def _find_item_info_by_id(self, item_id):
        if not isinstance(item_id, int):
            return None

        inventory_list = self._state_store.get_state_section("inventory")
        if isinstance(inventory_list, list):
            for item in inventory_list:
                if isinstance(item, dict) and item.get("id") == item_id and isinstance(item.get("id"), int):
                    return {
                        "location": "inventory",
                        "location_name": None,
                        "location_id": None,
                        "item_data": item
                    }

        rooms = self._state_store.get_state_section("rooms")
        if isinstance(rooms, list) and self._room_manager: # Ensure room_manager is set
            for room in rooms:
                if isinstance(room, dict) and isinstance(room.get("id"), int) and isinstance(room.get("items"), list):
                    for item in room["items"]:
                        if isinstance(item, dict) and item.get("id") == item_id and isinstance(item.get("id"), int):
                            return {
                                "location": "room",
                                "location_name": room.get("name"),
                                "location_id": room.get("id"),
                                "item_data": item
                            }
        return None

    def _is_valid_item_data(self, item_data: dict, check_id: bool = False) -> tuple[bool, str]:
        _, error = validate_item_dict(item_data, check_id=check_id)
        if error:
            return False, error
        return True, ""


    def _format_item_for_display(self, item_dict, show_quantity=True):
        if not isinstance(item_dict, dict):
            return "Invalid Item Data"
        item_id = item_dict.get('id', -1)
        item_name = item_dict.get('name', 'Unnamed Item')
        if not isinstance(item_id, int):
            return f"{item_name} (ID:INVALID)"
        
        # Only show quantity if requested and conditions are met
        quantity = item_dict.get('quantity', 1)
        if show_quantity and item_dict.get('stackable', False) and quantity > 1:
            return f"{item_name} (ID:{item_id:06d}) x{quantity}"
        
        return f"{item_name} (ID:{item_id:06d})"

    # --- Public Inventory Methods ---

    def add_item_description(self, item_id: int, new_description: str) -> str:
        if not isinstance(item_id, int):
            return f"Failed to add description: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."
        if not isinstance(new_description, str) or not new_description.strip():
            return "Failed to add description: New description must be a non-empty string."

        item_object : ItemLookupResult = self.find_item(item_id=item_id, required_type=None, required_location="inventory")

        if item_object.success:
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            timed_description = f"{timestamp} {new_description.strip()}"

            descriptions_list_copy = copy.deepcopy(item_object.item_data.get("descriptions"))
            if not isinstance(descriptions_list_copy, list):
                descriptions_list_copy = []
            descriptions_list_copy.append(timed_description)

            # Don't touch found_item here — let set_item_attribute handle the write
            attribute_result : SetItemAttributeResult = self.set_item_attribute(item_id, "descriptions", descriptions_list_copy)

            item_name = item_object.item_data.get("name", "Unnamed Item")
            return f"Added description for '{item_name}' (ID: {item_id}) in inventory. {attribute_result.message}"
        else:
            return f"Failed to add description: Item with ID {item_id} not found in your inventory."

    def _inventory_can_accept(self, item_data: dict, current_list: list | None = None) -> bool:
        """
        Returns True if this item can be placed in inventory —
        either because it will merge into an existing stack,
        or because there is a free slot available.
        """
        inventory_list = current_list if current_list is not None else self._state_store.get_state_section("inventory", [])

        if item_data.get("stackable", False):
            existing_stack = self._find_matching_stack_in_list(inventory_list, item_data)
            if existing_stack:
                space = existing_stack.get("max_stack_size", float("inf")) - existing_stack.get("quantity", 0)
                if space > 0:
                    return True  # Will merge, no slot needed

        # No merge possible — needs a free slot
        return len(inventory_list) < self.MAX_INVENTORY_SLOTS


    def pickup_item(self, item_id: int, quantity_to_pickup: int = 1):
        if not isinstance(item_id, int):
            return f"Failed to pick up: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        item_info = self._find_item_info_by_id(item_id)
        if item_info is None:
            return "Item not found anywhere."

        item_data_in_source = item_info.get("item_data")
        if not item_data_in_source:
            print(f"Warning: item_info for ID {item_id} found but missing 'item_data'. item_info: {item_info}")
            return f"Error: Found item info for ID {item_id} but item data is missing."

        item_display = self._format_item_for_display(item_data_in_source)

        if item_info["location"] == "inventory":
            return f"You already have the {item_display} in your inventory!"

        if item_data_in_source.get("static", False):
            return f"You cannot pick up the {item_display}. It is too big!"

        current_room_id = self._state_store.get_state_section("current_room_id")
        current_room = None
        if self._room_manager:
            current_room = self._room_manager._find_room_by_id(current_room_id)
        else:
            print("Warning: RoomManager not set in InventoryService, cannot pickup from room.")
            return "Error: Room information not available for pickup."

        if not (item_info["location"] == "room" and item_info["location_id"] == current_room_id):
            return f"Failed to pick up {item_display}: It is not here."

        available_in_source = item_data_in_source.get("quantity", 1)
        if quantity_to_pickup <= 0:
            actual_quantity_to_pickup = available_in_source
        else:
            actual_quantity_to_pickup = min(quantity_to_pickup, available_in_source)

        item_to_move = None
        if actual_quantity_to_pickup < available_in_source:
            item_data_in_source["quantity"] = available_in_source - actual_quantity_to_pickup
            item_to_move = item_data_in_source.copy()
            item_to_move["id"] = self._state_store.get_next_item_id()
            item_to_move["quantity"] = actual_quantity_to_pickup
        else:
            item_to_move = item_data_in_source
            current_room["items"][:] = [item for item in current_room["items"] if item.get("id") != item_id]

        inventory_list = self._state_store.get_state_section("inventory", [])

        transfer_successful = False
        remaining_to_pickup = item_to_move.get("quantity", 1)
        messages = []

        if item_to_move.get("stackable", False):
            target_stack = self._find_matching_stack_in_list(inventory_list, item_to_move)
            if target_stack:
                space_in_target = target_stack.get("max_stack_size", float('inf')) - target_stack.get("quantity", 0)
                amount_to_transfer = min(remaining_to_pickup, space_in_target)

                if amount_to_transfer > 0:
                    target_stack["quantity"] += amount_to_transfer
                    remaining_to_pickup -= amount_to_transfer
                    messages.append(f"Added {amount_to_transfer} to an existing stack of {self._format_item_for_display(target_stack)}.")
                    transfer_successful = True

            if remaining_to_pickup > 0:
                if not self._inventory_can_accept(item_to_move, current_list=inventory_list):
                    messages.append(f"Your inventory is full! Could not pick up the remaining {remaining_to_pickup} items.")
                    current_room["items"].append(item_to_move)
                else:
                    inventory_list.append(item_to_move)
                    messages.append(f"Picked up a new stack of {self._format_item_for_display(item_to_move)}.")
                    remaining_to_pickup = 0
                    transfer_successful = True
        else:
            if not self._inventory_can_accept(item_to_move, current_list=inventory_list):
                messages.append(f"Your inventory is full! You cannot pick up the item.")
                current_room["items"].append(item_to_move)
            else:
                inventory_list.append(item_to_move)
                transfer_successful = True
                messages.append(f"Picked up the {self._format_item_for_display(item_to_move)}.")

        if transfer_successful:
            rooms_list = self._state_store.get_state_section("rooms", [])
            self._state_store.update_state_section("rooms", rooms_list)
            self._state_store.update_state_section("inventory", inventory_list)

            self._emit_inventory_signals()
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/hand_up_icon.png"})
            return " ".join(messages)
        else:
            return f"Failed to pick up {item_display}. " + " ".join(messages)
####


    def drop_item(self, item_id: int, quantity_to_drop: int = 1):
            if not isinstance(item_id, int):
                return f"Failed to drop: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

            # 1. Get the Master Lists (The actual lists we will save back to the store)
            inventory_list = self._state_store.get_state_section("inventory", [])
            rooms_list = self._state_store.get_state_section("rooms", [])
            current_room_id = self._state_store.get_state_section("current_room_id")

            # 2. Find the Source Item DIRECTLY in the inventory_list
            # This prevents "reference disconnects" where we modify a copy but save the original
            source_item = next((item for item in inventory_list if item.get("id") == item_id), None)

            if not source_item:
                # Fallback: check if it's in the room just to give a better error
                return f"Failed to drop: Item with ID '{item_id}' not found in your inventory."

            # 3. Find the Target Room DIRECTLY in the rooms_list
            target_room = next((r for r in rooms_list if r.get("id") == current_room_id), None)
            if not target_room:
                return f"Error: Could not access current room (ID: {current_room_id})."
            
            target_room_name = target_room.get("name", "Unknown Room")
            item_display = self._format_item_for_display(source_item)

            # 4. Calculate Quantities
            available_quantity = source_item.get("quantity", 1)
            if quantity_to_drop <= 0:
                actual_quantity_to_drop = available_quantity
            else:
                actual_quantity_to_drop = min(quantity_to_drop, available_quantity)

            # 5. Handle Splitting / Moving
            item_to_drop = None

            if actual_quantity_to_drop < available_quantity:
                # PARTIAL DROP:
                # A. Modify the item in the inventory IN PLACE (keeping the original ID there)
                source_item["quantity"] -= actual_quantity_to_drop
                
                # B. Create a COPY for the room (giving it a new ID)
                item_to_drop = source_item.copy()
                item_to_drop["id"] = self._state_store.get_next_item_id()
                item_to_drop["quantity"] = actual_quantity_to_drop
            else:
                # FULL DROP:
                # A. Use the original item
                item_to_drop = source_item
                # B. Remove it strictly from the list we are holding
                inventory_list.remove(source_item)

            # 6. Add to Room (Stacking Logic)
            transfer_successful = False
            remaining_to_drop = item_to_drop.get("quantity", 1)
            messages = []

            if item_to_drop.get("stackable", False):
                # Pass target_room["items"] directly so we modify the list inside rooms_list
                target_stack = self._find_matching_stack_in_list(target_room["items"], item_to_drop)
                
                if target_stack:
                    space_in_target = target_stack.get("max_stack_size", float('inf')) - target_stack.get("quantity", 0)
                    amount_to_transfer = min(remaining_to_drop, space_in_target)

                    if amount_to_transfer > 0:
                        target_stack["quantity"] += amount_to_transfer
                        remaining_to_drop -= amount_to_transfer
                        # We don't really need to update item_to_drop['quantity'] here as it merges, 
                        # but it helps for debugging logic if needed.
                        messages.append(f"Added {amount_to_transfer} to an existing stack of {self._format_item_for_display(target_stack)} in {target_room_name}.")
                        transfer_successful = True

                if remaining_to_drop > 0:
                    # Update the quantity if some was merged but not all
                    item_to_drop["quantity"] = remaining_to_drop
                    target_room["items"].append(item_to_drop)
                    messages.append(f"Dropped a new stack of {self._format_item_for_display(item_to_drop)} in {target_room_name}.")
                    transfer_successful = True
            else:
                target_room["items"].append(item_to_drop)
                messages.append(f"Dropped the {self._format_item_for_display(item_to_drop)} in {target_room_name}.")
                transfer_successful = True

            # 7. Persist Changes
            if transfer_successful:
                self._state_store.update_state_section("inventory", inventory_list)
                self._state_store.update_state_section("rooms", rooms_list)

                self._emit_inventory_signals()
                self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/hand_down_icon.png"})
                return f"You dropped items. " + " ".join(messages)
            else:
                # Recovery: If logic failed (unlikely), restore inventory
                if actual_quantity_to_drop >= available_quantity:
                    inventory_list.append(item_to_drop)
                else:
                    source_item["quantity"] += actual_quantity_to_drop
                return f"Failed to drop {item_display}."
        
    def create_item(
        self,
        target_location: str,
        target_location_id: int | None,
        item_creation_data: dict | list[dict],
        quantity: int = 1,
        fallback_to_room: bool = True,
    ) -> ItemCreationResult:
        """
        Creates one or more items in the specified location.

        Parameters
        ----------
        target_location     : "inventory" or "room"
        target_location_id  : Room ID when target_location="room", else None
        item_creation_data  : A single item dict or a list of item dicts (templates)
        quantity            : How many of each template to create. Defaults to 1.
        fallback_to_room    : If True and inventory is full, place in current room instead.

        Returns
        -------
        ItemCreationResult
            Always returns this model — never a raw string or list.
            Check result.success before using result.created_ids.
            result.message is always safe to append to a parts list.
        """
        print(f"DEBUG: Starting create_item. target_location: '{target_location}', "
            f"target_location_id: '{target_location_id}', quantity: {quantity}")

        failed_items_info = []
        messages = []
        overall_successful_creation_count = 0

        # --- Validate quantity ---
        if not isinstance(quantity, int) or quantity <= 0:
            return ItemCreationResult.fail(
                f"Failed to create item(s): 'quantity' must be a positive integer, "
                f"received '{quantity}' ({type(quantity).__name__})."
            )

        # --- Normalise item_creation_data to a list of templates ---
        if isinstance(item_creation_data, dict):
            item_templates_to_create = [item_creation_data]
        elif isinstance(item_creation_data, list):
            item_templates_to_create = item_creation_data
        else:
            return ItemCreationResult.fail(
                f"Failed to create item(s): item_creation_data must be a dict or list of dicts, "
                f"received {type(item_creation_data).__name__}."
            )

        if not item_templates_to_create:
            return ItemCreationResult.fail("No valid item data provided.")

        # --- Fetch state lists ---
        inventory_list = self._state_store.get_state_section("inventory", [])
        rooms_list     = self._state_store.get_state_section("rooms", [])

        target_location_lower = target_location.strip().lower()
        target_room = None

        if target_location_lower == "room":
            if not isinstance(target_location_id, int) or not self._room_manager:
                return ItemCreationResult.fail(
                    f"Target room ID must be an integer when creating item(s) in a room, "
                    f"received '{target_location_id}' ({type(target_location_id).__name__})."
                )
            target_room = self._room_manager._find_room_by_id(target_location_id)
            if not target_room or not isinstance(target_room.get("items"), list):
                return ItemCreationResult.fail(
                    f"Target room with ID '{target_location_id}' not found or room data corrupted."
                )

        elif target_location_lower == "inventory":
            if not isinstance(inventory_list, list):
                return ItemCreationResult.fail("Inventory state corrupted. Cannot create items.")

        else:
            return ItemCreationResult.fail(
                f"Invalid target location '{target_location}'. Must be 'room' or 'inventory'."
            )

        # --- Resolve fallback room upfront ---
        fallback_room = None
        if fallback_to_room and target_location_lower == "inventory" and self._room_manager:
            fallback_room_id = self._room_manager.get_current_room_id()
            fallback_room = self._room_manager._find_room_by_id(fallback_room_id)

        # --- Main creation loop ---
        successfully_created_ids = []

        for original_item_template in item_templates_to_create:
            item_data_template = original_item_template.copy()
            item_data_template.setdefault("stackable", False)
            item_data_template.setdefault("quantity", 1)

            is_valid, error_msg = self._is_valid_item_data(item_data_template, check_id=False)
            if not is_valid:
                display_name = item_data_template.get("name", "Unnamed Item") if isinstance(item_data_template, dict) else "Invalid Data"
                failed_items_info.append((display_name, f"Template validation failed: {error_msg}"))
                continue

            current_quantity_to_add = quantity

            while current_quantity_to_add > 0:
                created_this_iteration = False

                if item_data_template.get("stackable", False):
                    target_list = inventory_list if target_location_lower == "inventory" else (target_room["items"] if target_room else [])
                    existing_stack = self._find_matching_stack_in_list(target_list, item_data_template)

                    if existing_stack:
                        space_in_target = existing_stack.get("max_stack_size", float("inf")) - existing_stack.get("quantity", 0)
                        amount_to_transfer = min(current_quantity_to_add, space_in_target)

                        if amount_to_transfer > 0:
                            existing_stack["quantity"] = existing_stack.get("quantity", 0) + amount_to_transfer
                            current_quantity_to_add -= amount_to_transfer
                            overall_successful_creation_count += amount_to_transfer
                            successfully_created_ids.append(existing_stack["id"])
                            created_this_iteration = True
                            messages.append(f"Added {amount_to_transfer} units to existing stack {self._format_item_for_display(existing_stack)}.")

                    if current_quantity_to_add > 0:
                        if target_location_lower == "inventory" and not self._inventory_can_accept(item_data_template, current_list=inventory_list):
                            if fallback_room:
                                target_location_lower = "room"
                                target_room = fallback_room
                                messages.append("Inventory full, placing in room instead.")
                                continue
                            else:
                                failed_items_info.append((
                                    self._format_item_for_display(item_data_template),
                                    f"Inventory full, could not create new stack for {current_quantity_to_add} units."
                                ))
                                current_quantity_to_add = 0
                                break

                        new_item_id    = self._state_store.get_next_item_id()
                        new_stack_item = item_data_template.copy()
                        new_stack_item["id"]       = new_item_id
                        new_stack_item["quantity"] = current_quantity_to_add

                        max_size = new_stack_item.get("max_stack_size", float("inf"))
                        if new_stack_item["quantity"] > max_size:
                            original_qty = new_stack_item["quantity"]
                            new_stack_item["quantity"] = max_size
                            failed_items_info.append((
                                self._format_item_for_display(new_stack_item),
                                f"Quantity ({original_qty}) exceeded max_stack_size ({max_size}); clamped. Remaining units lost."
                            ))

                        if target_location_lower == "inventory":
                            inventory_list.append(new_stack_item)
                        elif target_room:
                            target_room["items"].append(new_stack_item)

                        overall_successful_creation_count += new_stack_item["quantity"]
                        successfully_created_ids.append(new_stack_item["id"])
                        messages.append(f"Created a new stack of {self._format_item_for_display(new_stack_item)}.")
                        current_quantity_to_add = 0
                        created_this_iteration = True

                else:  # Non-stackable
                    if target_location_lower == "inventory" and len(inventory_list) >= self.MAX_INVENTORY_SLOTS:
                        if fallback_room:
                            target_location_lower = "room"
                            target_room = fallback_room
                            messages.append("Inventory full, placing in room instead.")
                            continue
                        else:
                            failed_items_info.append((
                                self._format_item_for_display(item_data_template),
                                "Inventory full, could not create new non-stackable item."
                            ))
                            current_quantity_to_add = 0
                            break

                    new_item_id     = self._state_store.get_next_item_id()
                    new_single_item = item_data_template.copy()
                    new_single_item["id"]       = new_item_id
                    new_single_item["quantity"] = 1

                    if target_location_lower == "inventory":
                        inventory_list.append(new_single_item)
                    elif target_room:
                        target_room["items"].append(new_single_item)

                    overall_successful_creation_count += 1
                    successfully_created_ids.append(new_single_item["id"])
                    messages.append(f"Created {self._format_item_for_display(new_single_item)}.")
                    current_quantity_to_add -= 1
                    created_this_iteration = True

                if not created_this_iteration and current_quantity_to_add > 0:
                    failed_items_info.append((
                        self._format_item_for_display(item_data_template),
                        f"Failed to place remaining {current_quantity_to_add} units (unknown reason)."
                    ))
                    current_quantity_to_add = 0

        # --- Persist ---
        if target_location_lower == "inventory":
            self._state_store.update_state_section("inventory", inventory_list)
        else:
            self._state_store.update_state_section("rooms", rooms_list)

        if overall_successful_creation_count > 0:
            self._emit_inventory_signals()

        # --- Build result ---
        if overall_successful_creation_count == 0:
            all_reasons = "; ".join(f"{name}: {reason}" for name, reason in failed_items_info)
            return ItemCreationResult.fail(
                f"Failed to create item(s): {all_reasons or 'Unknown reason.'}"
            )

        item_plural = "item" if overall_successful_creation_count == 1 else "items"
        summary_parts = [f"Successfully created {overall_successful_creation_count} {item_plural}."]
        summary_parts.extend(messages)

        if failed_items_info:
            grouped = {}
            for name, reason in failed_items_info:
                grouped[(name, reason)] = grouped.get((name, reason), 0) + 1
            failure_lines = [
                f"- {count}x {name}: {reason}" if count > 1 else f"- {name}: {reason}"
                for (name, reason), count in grouped.items()
            ]
            summary_parts.append("Some items failed:\n" + "\n".join(failure_lines))

        return ItemCreationResult.ok(
            created_ids=successfully_created_ids,
            location=target_location_lower,
            message="\n".join(summary_parts),
        )

    def remove_item(
        self,
        item_id: int,
        quantity: int = 1,
    ) -> ItemRemovalResult:
        """
        Removes one or more units of an item from wherever it currently is.

        Parameters
        ----------
        item_id  : The integer ID of the item to remove.
        quantity : How many units to remove. Pass 0 to remove the entire stack.
                Defaults to 1.

        Returns
        -------
        ItemRemovalResult
            Always returns this model — never a raw string or tuple.
            Check result.success before acting on failure.
            result.message is always safe to append to a parts list.
        """
        if not isinstance(item_id, int):
            return ItemRemovalResult.fail(
                f"Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."
            )

        item_info = self._find_item_info_by_id(item_id)
        if not item_info:
            return ItemRemovalResult.fail(
                f"Item with ID '{item_id}' not found anywhere."
            )

        item_data_to_remove = item_info["item_data"]
        item_display        = self._format_item_for_display(item_data_to_remove)
        location            = item_info["location"]
        location_id         = item_info["location_id"]

        available_quantity = item_data_to_remove.get("quantity", 1)
        if quantity <= 0 or quantity > available_quantity:
            actual_quantity_to_remove = available_quantity
        else:
            actual_quantity_to_remove = quantity

        # --- Inventory removal ---
        if location == "inventory":
            inventory_list = self._state_store.get_state_section("inventory")
            if not isinstance(inventory_list, list):
                return ItemRemovalResult.fail(
                    "Cannot remove item from inventory — inventory state corrupted."
                )

            if item_data_to_remove.get("stackable", False) and item_data_to_remove["quantity"] > actual_quantity_to_remove:
                item_data_to_remove["quantity"] -= actual_quantity_to_remove
                message = (
                    f"Removed {actual_quantity_to_remove} unit(s) from {item_display} in your inventory. "
                    f"Remaining: {item_data_to_remove['quantity']}."
                )
            else:
                inventory_list[:] = [item for item in inventory_list if item.get("id") != item_id]
                message = f"Removed {item_display} from your inventory."

            self._state_store.update_state_section("inventory", inventory_list)

        # --- Room removal ---
        elif location == "room":
            rooms_list = self._state_store.get_state_section("rooms")
            if not self._room_manager:
                return ItemRemovalResult.fail(
                    "RoomManager not set — cannot remove item from room."
                )

            room_data = self._room_manager._find_room_by_id(location_id)
            if not room_data or not isinstance(room_data.get("items"), list):
                return ItemRemovalResult.fail(
                    f"Cannot remove item from room '{location_id}' — room data corrupted."
                )

            room_display = self._room_manager._format_room_for_display(room_data)

            if item_data_to_remove.get("stackable", False) and item_data_to_remove["quantity"] > actual_quantity_to_remove:
                item_data_to_remove["quantity"] -= actual_quantity_to_remove
                message = (
                    f"Removed {actual_quantity_to_remove} unit(s) from {item_display} "
                    f"in {room_display}. Remaining: {item_data_to_remove['quantity']}."
                )
            else:
                room_data["items"][:] = [
                    item for item in room_data["items"]
                    if isinstance(item, dict) and item.get("id") != item_id
                ]
                message = f"Removed {item_display} from {room_display}."

            self._state_store.update_state_section("rooms", rooms_list)

        else:
            return ItemRemovalResult.fail(
                f"Failed to remove {item_display}: unknown location type '{location}'."
            )

        # --- Signals ---
        self._emit_inventory_signals()

        return ItemRemovalResult.ok(message)

    def persist_item_changes(self, item_id: int) -> str | None:
        """
        Persists changes made to an item's data to the central state store.
        Finds the item by ID, determines its location, and updates the appropriate state section.
        Returns None on success, or an error message string on failure.
        """
        item_id = int(item_id)
        item_info = self._find_item_info_by_id(item_id)
        if not item_info:
            return f"Error: Item {item_id} moved or lost during operation."

        location = item_info["location"]
        
        if location == "inventory":
            inventory_list = self._state_store.get_state_section("inventory", [])
            # The item data in inventory_list is a reference, so it might already be updated if modified in place.
            # We trigger the update on the store to ensure persistence (e.g. writing to file).
            self._state_store.update_state_section("inventory", inventory_list)
        elif location == "room":
            rooms_list = self._state_store.get_state_section("rooms", [])
            self._state_store.update_state_section("rooms", rooms_list)
        else:
            return f"Error: Item in unmanageable location: {location}"
            
        return None


    # ============================================================================
    # NEW PUBLIC METHOD — add inside InventoryService class
    # ============================================================================

    def find_item(
        self,
        item_id: int,
        required_type: str | None = None,
        required_location: Literal["inventory", "room", "accessible"] | None = None,
    ) -> ItemLookupResult:
        """
        Unified item lookup with optional filters.

        Parameters
        ----------
        item_id           : The integer ID of the item to find.
        required_type     : If given, the item's type list must include this string.
        required_location : Controls where the item is allowed to be:
                            None           → anywhere in the whole state
                            "inventory"    → must be in the player's inventory
                            "room"         → must be in any room
                            "accessible"   → must be in inventory OR the current room

        Returns
        -------
        ItemLookupResult
            Always returns this model.
            Check result.success before using result.item_data.
        """
        # 1. Coerce and validate the ID
        if not isinstance(item_id, int):
            try:
                item_id = int(item_id)
            except (ValueError, TypeError):
                return ItemLookupResult.fail(
                    f"Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."
                )

        # 2. Find the item anywhere in state (inventory + all rooms)
        raw = copy.deepcopy(self._find_item_info_by_id(item_id))
        if raw is None:
            return ItemLookupResult.fail(f"Item {item_id} not found.")

        item_data    = raw["item_data"]
        location     = raw["location"]        # "inventory" or "room"
        location_id  = raw["location_id"]     # int or None
        location_name = raw["location_name"]  # str or None

        # 3. Type filter
        if required_type is not None:
            if required_type not in item_data.get("type", []):
                return ItemLookupResult.fail(
                    f"Item {item_id} ('{item_data.get('name', '?')}') "
                    f"is not of type '{required_type}' "
                    f"(found types: {item_data.get('type', [])})."
                )

        # 4. Location filter
        if required_location is not None:
            if required_location == "inventory":
                if location != "inventory":
                    return ItemLookupResult.fail(
                        f"Item {item_id} ('{item_data.get('name', '?')}') "
                        f"is not in your inventory (found in {location!r}"
                        + (f", room '{location_name}'" if location_name else "")
                        + ")."
                    )

            elif required_location == "room":
                current_room_id = self._state_store.get_state_section("current_room_id")
                in_current_room = location == "room" and location_id == current_room_id
                if not in_current_room:
                    where = (
                        f"room '{location_name}' (ID {location_id})"
                        if location == "room"
                        else "your inventory"
                    )
                    return ItemLookupResult.fail(
                        f"Item {item_id} ('{item_data.get('name', '?')}') "
                        f"is not in your current room "
                        f"(it is in {where})."
                    )

            elif required_location == "accessible":
                current_room_id = self._state_store.get_state_section("current_room_id")
                in_inventory    = location == "inventory"
                in_current_room = location == "room" and location_id == current_room_id
                if not (in_inventory or in_current_room):
                    where = (
                        f"room '{location_name}' (ID {location_id})"
                        if location == "room"
                        else "an unknown location"
                    )
                    return ItemLookupResult.fail(
                        f"Item {item_id} ('{item_data.get('name', '?')}') "
                        f"is not accessible from your current location "
                        f"(it is in {where})."
                    )

        # 5. All filters passed
        return ItemLookupResult.ok(
            item_data=item_data,
            location=location,
            location_id=location_id,
            location_name=location_name,
        )


# ── New helper ──────────────────────────────────────────────────────────

    def _apply_nested_set(self, data: dict, path: list[str] | None, key: str, value) -> None:
        """
        Traverse *path* into *data* (creating intermediate dicts as needed),
        then set data[key] = value at that level.

        Examples
        --------
        _apply_nested_set(item, None,                    "name",     "Bob")
          → item["name"] = "Bob"

        _apply_nested_set(item, ["dispenser_state"],     "contents", {...})
          → item["dispenser_state"]["contents"] = {...}

        _apply_nested_set(item, ["a", "b"],              "c",        42)
          → item["a"]["b"]["c"] = 42
        """
        target = data
        for segment in (path or []):
            if not isinstance(target.get(segment), dict):
                target[segment] = {}
            target = target[segment]
        target[key] = value

    # ── Modified method signature ────────────────────────────────────────────

    def set_item_attribute(self, item_id: int, key: str, value, quantity: int = 1,
                           path: list[str] | None = None) -> SetItemAttributeResult:
        """
        Modifies a single attribute (key/value) on one or more units of an item
        stack, then recalculates stacking state.

        If *path* is provided the write is applied at a nested location inside
        the item dict.  For example::

            set_item_attribute(id, "contents", new_dict, path=["dispenser_state"])

        writes ``item_data["dispenser_state"]["contents"] = new_dict`` instead
        of touching the top-level key directly.

        The stacking-fingerprint logic only considers the *top-level* key when
        path is None; when path is provided the fingerprint comparison uses the
        top-level segment (path[0]) so that nested writes on non-stacking keys
        remain fast-pathed correctly.

        Args:
            item_id:  The ID of the item (or stack) to modify.
            key:      The attribute key to set (at the leaf of *path*).
            value:    The new value for that attribute.
            quantity: How many units of the stack to affect.  Defaults to 1.
                      Pass 0 or a value >= available quantity to affect the whole stack.
            path:     Optional list of dict keys to traverse before setting *key*.
                      Intermediate dicts are created automatically if absent.

        Returns:
            A SetItemAttributeResult object.
        """
        if not isinstance(item_id, int):
            return SetItemAttributeResult(success=False, message=f"Failed to set attribute: item_id must be an integer, got '{item_id}'.")

        # --- 1. Locate the item ---
        item_info = self._find_item_info_by_id(item_id)
        if not item_info:
            return SetItemAttributeResult(success=False, message=f"Failed to set attribute: item with ID {item_id} not found.")

        item_data     = item_info["item_data"]
        location      = item_info["location"]
        location_id   = item_info["location_id"]

        item_display  = self._format_item_for_display(item_data)
        is_stackable  = item_data.get("stackable", False)

        # The "effective top-level key" for fingerprint purposes:
        # when a path is given the stacking key is path[0], not key.
        fingerprint_key = path[0] if path else key

        # --- 2. Resolve how many units are affected ---
        available = item_data.get("quantity", 1)
        if quantity <= 0 or quantity >= available:
            actual_qty = available
        else:
            actual_qty = quantity

        # --- 3. Resolve the target list ---
        if location == "inventory":
            target_list = self._state_store.get_state_section("inventory", [])
        elif location == "room":
            if not self._room_manager:
                return SetItemAttributeResult(success=False, message="Error: RoomManager not set; cannot modify room item.")
            room_data = self._room_manager._find_room_by_id(location_id)
            if not room_data or not isinstance(room_data.get("items"), list):
                return SetItemAttributeResult(success=False, message=f"Error: Room {location_id} not found or corrupted.")
            target_list = room_data["items"]
        else:
            return SetItemAttributeResult(success=False, message=f"Error: Unknown item location '{location}'.")

        # --- 4. Non-stackable: just mutate and persist ---
        if not is_stackable:
            self._apply_nested_set(item_data, path, key, value)
            err = self.persist_item_changes(item_id)
            if err:
                return SetItemAttributeResult(success=False, message=f"Set '{key}' on {item_display}, but failed to persist: {err}")
            path_str = ".".join(path + [key]) if path else key
            return SetItemAttributeResult(success=True, message=f"Set '{path_str}' = {value!r} on {item_display}.")

        # --- Stackable path ---
        stacking_key_before = self._get_item_stacking_key(item_data)

        modified_preview = item_data.copy()
        self._apply_nested_set(modified_preview, path, key, value)
        stacking_key_after = self._get_item_stacking_key(modified_preview)

        fingerprint_unchanged = (stacking_key_before == stacking_key_after)

        if fingerprint_unchanged:
            self._apply_nested_set(item_data, path, key, value)
            err = self.persist_item_changes(item_id)
            if err:
                return SetItemAttributeResult(success=False, message=f"Set '{key}' on {item_display}, but failed to persist: {err}")
            path_str = ".".join(path + [key]) if path else key
            return SetItemAttributeResult(success=True, message=f"Set '{path_str}' = {value!r} on all {available} unit(s) of {item_display}.")

        # --- Fingerprint changes: split logic ---
        remaining_in_source = available - actual_qty

        detached_preview = {**item_data, **({path[0]: modified_preview[path[0]]} if path else {key: value}), "quantity": actual_qty}
        existing_target = next(
            (i for i in target_list
            if i.get("id") != item_id
            and i.get("stackable", False)
            and self._get_item_stacking_key(i) == self._get_item_stacking_key(detached_preview)
            and i.get("quantity", 0) < i.get("max_stack_size", float("inf"))),
            None
        )

        if remaining_in_source == 0 and existing_target is None:
            self._apply_nested_set(item_data, path, key, value)
            err = self.persist_item_changes(item_id)
            if err:
                return SetItemAttributeResult(success=False, message=f"Set '{key}' on {item_display}, but failed to persist: {err}")
            path_str = ".".join(path + [key]) if path else key
            return SetItemAttributeResult(success=True, message=f"Set '{path_str}' = {value!r} on {item_display} (ID kept, stack updated in place).")

        # --- Reduce or remove source stack ---
        if remaining_in_source > 0:
            item_data["quantity"] = remaining_in_source
        else:
            target_list[:] = [i for i in target_list if i.get("id") != item_id]

        detached = {**item_data}
        self._apply_nested_set(detached, path, key, value)
        detached["quantity"] = actual_qty

        existing_target = self._find_matching_stack_in_list(target_list, detached)

        messages = []
        if existing_target:
            space = existing_target.get("max_stack_size", float("inf")) - existing_target.get("quantity", 0)
            can_merge = min(actual_qty, space)
            existing_target["quantity"] += can_merge
            leftover = actual_qty - can_merge
            messages.append(
                f"Merged {can_merge} unit(s) into existing stack {self._format_item_for_display(existing_target)}."
            )
            if leftover > 0:
                new_id = self._state_store.get_next_item_id()
                overflow_stack = {**detached, "id": new_id, "quantity": leftover}
                target_list.append(overflow_stack)
                messages.append(f"Created new stack (ID:{new_id:06d}) for remaining {leftover} unit(s).")
        else:
            new_id = self._state_store.get_next_item_id()
            new_stack = {**detached, "id": new_id, "quantity": actual_qty}
            target_list.append(new_stack)
            messages.append(f"Created new stack {self._format_item_for_display(new_stack)} with {actual_qty} unit(s).")

        if location == "inventory":
            self._state_store.update_state_section("inventory", target_list)
        else:
            rooms_list = self._state_store.get_state_section("rooms", [])
            self._state_store.update_state_section("rooms", rooms_list)

        self._emit_inventory_signals()

        split_msg = (
            f"Modified '{key}' on {actual_qty} unit(s) of {item_display} "
            f"(source stack {'reduced to ' + str(remaining_in_source) + ' unit(s)' if remaining_in_source > 0 else 'fully consumed'}). "
        )
        return SetItemAttributeResult(success=True, message=split_msg + " ".join(messages))



    def get_inventory_state(self) -> InventoryStateResult:
        """
        Returns a fully-typed snapshot of the current inventory and room items.

        Replaces the combined behaviour of:
          - list_inventories(formatted=True / False)
          - get_inventory_items(internal=True / False)
          - list_items_in_current_room(internal=True / False)

        All items are validated before inclusion — invalid raw dicts are
        silently dropped. Every caller gets one consistent object with
        pre-computed views for their specific need:

          GUI / signals      → result.inventory_display_strings
                               result.room_display_strings
          AI agent strings   → result.inventory_summary
                               result.room_summary
          Tool / logic use   → result.inventory_items  (list[InventoryItemEntry])
                               result.room_items        (list[InventoryItemEntry])
          Raw dict access    → entry.item_data on any entry

        Returns
        -------
        InventoryStateResult
            Always returns this model — never raises. If the room cannot be
            found, room_items will be empty and room_name will be "Unknown Room".
        """
        # --- 1. Resolve current room ---
        current_room_id: int = self._state_store.get_state_section("current_room_id", -1)

        room_data = None
        if self._room_manager:
            room_data = self._room_manager._find_room_by_id(current_room_id)

        room_name: str = room_data.get("name", "Unknown Room") if room_data else "Unknown Room"
        room_display: str = (
            self._room_manager._format_room_for_display(room_data)
            if (self._room_manager and room_data)
            else f"{room_name} (ID:{current_room_id:06d})"
        )

        # --- 2. Build room item entries ---
        room_item_entries: list[InventoryItemEntry] = []

        if room_data and isinstance(room_data.get("items"), list):
            for raw_item in room_data["items"]:
                is_valid, _ = self._is_valid_item_data(raw_item, check_id=True)
                if not is_valid:
                    continue
                room_item_entries.append(
                    InventoryItemEntry(
                        item_id=raw_item["id"],
                        name=raw_item.get("name", "Unnamed Item"),
                        display_string=self._format_item_for_display(raw_item),
                        item_data=raw_item,
                        location="room",
                        location_id=current_room_id,
                        location_name=room_name,
                    )
                )

        # --- 3. Build inventory item entries ---
        inventory_raw: list = self._state_store.get_state_section("inventory", [])
        inventory_item_entries: list[InventoryItemEntry] = []

        if isinstance(inventory_raw, list):
            for raw_item in inventory_raw:
                is_valid, _ = self._is_valid_item_data(raw_item, check_id=True)
                if not is_valid:
                    continue
                inventory_item_entries.append(
                    InventoryItemEntry(
                        item_id=raw_item["id"],
                        name=raw_item.get("name", "Unnamed Item"),
                        display_string=self._format_item_for_display(raw_item),
                        item_data=raw_item,
                        location="inventory",
                        location_id=None,
                        location_name=None,
                    )
                )

        # --- 4. Construct and return ---
        return InventoryStateResult.build(
            inventory_items=inventory_item_entries,
            room_items=room_item_entries,
            room_id=current_room_id,
            room_name=room_name,
            room_display=room_display,
        )