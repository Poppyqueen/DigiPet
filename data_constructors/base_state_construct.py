import os
import re
import sys

import time
# # --- TEMPORARY FIX FOR DIRECT EXECUTION ---
# # This block allows the script to find the 'utils' package
# # when run directly from its current location.
# # Assuming 'utils' is in the parent directory of this script's location
# # This adds the parent directory to the Python path
# script_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(script_dir)
# sys.path.append(parent_dir)
# # -------------------------------------------

from data_constructors.bundles_construct import bundles_maker
from data_constructors.room_generator import room_crafter
import os
import re
import json
import time
from typing import Dict, Any, List

from enum import Enum

from pygame_int.main_menu_areas.crafter_signal import CrafterSignal

# Define unique types - only one item of these types can exist across the entire house
UNIQUE_TYPES = [
    "art_book",
    "bluesky_social"
]

class BaseCrafter:
    def __init__(self, select_model="gpt-5-mini", select_provider="openai", initial_states_manager=None, signal_queue=None):

        print("Initializing BaseCrafter...")

        print("Initializing Items Crafter...")
        self.items_crafter = bundles_maker(select_model, select_provider)

        print("Initializing Rooms Crafter...")
        self.rooms_crafter = room_crafter(select_model, select_provider)

        self.signal_queue = signal_queue  # Optional signal queue

        self.InitialStateConst=initial_states_manager # added for testing, it is here now, maybe it can stay?
    

    def _send_signal(self, signal, data=None):
        """Send a signal if queue is available"""
        if self.signal_queue:
            try:
                self.signal_queue.put((signal, data))
            except:
                pass  # Don't let signal issues break the main process

    def _filter_unique_types(self, all_rooms_data: Dict[str, List[Dict]], rooms_config: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Filter out duplicate unique types across all rooms, keeping only the first occurrence.
        
        Args:
            all_rooms_data: Dictionary mapping room names to their item data
            rooms_config: Dictionary mapping room names to item names
        
        Returns:
            Filtered rooms_config with unique types enforced
        """
        print(f"\n--- FILTERING UNIQUE TYPES ---")
        print(f"Unique types to enforce: {UNIQUE_TYPES}")
        
        unique_types_found = {}  # Maps type -> (room_name, item_name)
        filtered_rooms_config = {}
        
        # First pass: identify all unique types and their first occurrence
        for room_name, item_names in rooms_config.items():
            if room_name == "initial_room":
                filtered_rooms_config[room_name] = item_names
                continue
                
            if room_name not in all_rooms_data:
                filtered_rooms_config[room_name] = item_names
                continue
            
            room_items_data = all_rooms_data[room_name]
            
            # Create a mapping of item names to their data for this room
            item_name_to_data = {}
            for item_data in room_items_data:
                if "name" in item_data:
                    item_name_to_data[item_data["name"]] = item_data
            
            # Check each item in this room
            for item_name in item_names:
                if item_name in item_name_to_data:
                    item_data = item_name_to_data[item_name]
                    
                    # Check if this item has any unique types
                    if "type" in item_data and isinstance(item_data["type"], list):
                        item_types = item_data["type"]
                        
                        # Check for unique types
                        for item_type in item_types:
                            if item_type in UNIQUE_TYPES:
                                if item_type not in unique_types_found:
                                    # First occurrence - keep it
                                    unique_types_found[item_type] = (room_name, item_name)
                                    print(f"✅ Found unique type '{item_type}' in '{room_name}' - '{item_name}' (KEEPING)")
                                else:
                                    # Duplicate - will be filtered out
                                    existing_room, existing_item = unique_types_found[item_type]
                                    print(f"🔍 Found duplicate unique type '{item_type}' in '{room_name}' - '{item_name}' (already in '{existing_room}' - '{existing_item}' - WILL REMOVE)")
        
        # Second pass: build filtered config, removing duplicates
        items_removed = 0
        for room_name, item_names in rooms_config.items():
            if room_name == "initial_room":
                filtered_rooms_config[room_name] = item_names
                continue
                
            if room_name not in all_rooms_data:
                filtered_rooms_config[room_name] = item_names
                continue
            
            room_items_data = all_rooms_data[room_name]
            
            # Create a mapping of item names to their data for this room
            item_name_to_data = {}
            for item_data in room_items_data:
                if "name" in item_data:
                    item_name_to_data[item_data["name"]] = item_data
            
            filtered_item_names = []
            
            for item_name in item_names:
                should_keep_item = True
                
                if item_name in item_name_to_data:
                    item_data = item_name_to_data[item_name]
                    
                    # Check if this item has any unique types
                    if "type" in item_data and isinstance(item_data["type"], list):
                        item_types = item_data["type"]
                        
                        # Check for unique types
                        for item_type in item_types:
                            if item_type in UNIQUE_TYPES:
                                # Check if this is the designated keeper for this unique type
                                if item_type in unique_types_found:
                                    keeper_room, keeper_item = unique_types_found[item_type]
                                    if not (room_name == keeper_room and item_name == keeper_item):
                                        # This is a duplicate, remove it
                                        should_keep_item = False
                                        items_removed += 1
                                        print(f"❌ Removing duplicate '{item_name}' (type: {item_type}) from '{room_name}'")
                                        break
                
                if should_keep_item:
                    filtered_item_names.append(item_name)
            
            filtered_rooms_config[room_name] = filtered_item_names
        
        print(f"🧹 Filtering complete: {items_removed} duplicate unique-type items removed")
        return filtered_rooms_config
                
    def generate_base_state(self, initial_idea: str, 
                           houses_output_dir: str = "inventory_items/base_state_manager/houses_data/local_ai_gens",
                           configs_output_dir: str = "inventory_items/base_state_manager/houses_configs/local_ai_gens") -> Dict[str, Any] | None:
        """
        Complete orchestration of house + items generation from a single idea.
        
        Args:
            initial_idea: The concept for the entire base state
            houses_output_dir: Directory for house JSON files
            configs_output_dir: Directory for config JSON files
        
        Returns:
            Dictionary with house configuration structure or None if failed
        """
        print(f"\n{'='*80}")
        print(f"🏠 GENERATING COMPLETE BASE STATE")
        print(f"💡 Concept: {initial_idea}")
        print(f"{'='*80}")

        self.signal_queue.put((CrafterSignal.ANALYZING_PROMPT, None))
        
        # Step 1: Generate the house with rooms
        print(f"\n--- STEP 1: Generating House Structure ---")
        base_house = self.rooms_crafter.orchestrate_generation(
            initial_idea=initial_idea,
            output_dir=houses_output_dir
        )

        self.signal_queue.put((CrafterSignal.GENERATING_STATE, None))
        
        if not base_house:
            print("❌ Failed to generate house structure. Aborting.")
            return None
        
        house_name = base_house["house_name"]
        house_file_path = base_house["file_path"]
        house_rooms_data = base_house["room_data"]
        
        print(f"✅ House '{house_name}' generated with {len(house_rooms_data)} rooms")
        
        # Step 2: Generate items for each room
        print(f"\n--- STEP 2: Generating Items for Each Room ---")
        
        # Create the rooms configuration dictionary
        rooms_config = {}
        all_rooms_data = {}  # Store raw item data for filtering
        
        # Choose the first room as the initial room
        if house_rooms_data:
            initial_room_name = house_rooms_data[0]["name"]
            rooms_config["initial_room"] = initial_room_name
            print(f"🏠 Set initial room: '{initial_room_name}'")
        
        # Generate items for each room
        total_rooms = len(house_rooms_data)
        for index, room in enumerate(house_rooms_data):
            current_room_number = index + 1
            room_name = room["name"]

            print(f"\n--- Processing Room {current_room_number}/{total_rooms}: '{room_name}' ---")

            process_value = (current_room_number / total_rooms) * 100

            self.signal_queue.put((CrafterSignal.PROGRESS_UPDATE, process_value))

            # Extract all descriptions from all time periods
            prompt_context = []
            for time_period, descriptions in room["descriptions"].items():
                if isinstance(descriptions, list):
                    prompt_context.extend(descriptions)
                else:
                    prompt_context.append(descriptions)
            
            final_descriptions = "\n".join(prompt_context)
            
            # Create the prompt for item generation
            final_prompt = (
                f"You are a creative AI tasked with generating a small to medium bundle of items "
                f"for the following room: {room_name}. The room has the following descriptions: "
                f"{final_descriptions}. Based on this information, create a list of items that would "
                f"logically fit in this room, considering the room's atmosphere, purpose, and described elements."
                f"10 items max per room."
            )
            
            print(f"Generating items for room: '{room_name}'")
            print(f"Using context: {final_descriptions[:100]}...")
            
            # Generate the bundle for this room
            room_bundle = self.items_crafter.orchestrate_bundle_generation(
                initial_idea=final_prompt,
                output_dir="inventory_items/items_provider/items_data/local_ai_gens"  #
            )
            
            if room_bundle and "item_data" in room_bundle:
                # Store raw item data for filtering later
                all_rooms_data[room_name] = room_bundle["item_data"]
                
                # Extract item names from the bundle
                item_names = []
                for item in room_bundle["item_data"]:
                    if "name" in item:
                        item_names.append(item["name"])
                
                rooms_config[room_name] = item_names
                print(f"✅ Generated {len(item_names)} items for '{room_name}'")
                
                # Show some example items
                if item_names:
                    example_items = item_names[:3]  # Show first 3 items
                    print(f"   Examples: {', '.join(example_items)}")
                    if len(item_names) > 3:
                        print(f"   ... and {len(item_names) - 3} more")
            else:
                print(f"❌ Failed to generate items for room: '{room_name}'")
                rooms_config[room_name] = []  # Empty list as fallback
                all_rooms_data[room_name] = []  # Empty data as fallback
            
            # Add delay between rooms (except for the last one)
            if current_room_number < total_rooms:
                print("⏳ Pausing 5 seconds before next room...")
                time.sleep(5)
        
        # Step 2.5: Apply unique types filter
        print(f"\n--- STEP 2.5: Applying Unique Types Filter ---")
        filtered_rooms_config = self._filter_unique_types(all_rooms_data, rooms_config)
        
        # Step 3: Save the rooms configuration (now filtered)
        print(f"\n--- STEP 3: Saving Filtered Rooms Configuration ---")
        
        # Create configs output directory
        os.makedirs(configs_output_dir, exist_ok=True)
        
        # Create safe config filename
        safe_house_name = re.sub(r'[^a-zA-Z0-9_-]', '_', house_name.lower())
        config_file_path = os.path.join(configs_output_dir, f"{safe_house_name}_config.json")
        
        try:
            with open(config_file_path, 'w') as f:
                json.dump(filtered_rooms_config, f, indent=4)
            print(f"✅ Filtered rooms configuration saved to: {config_file_path}")
        except Exception as e:
            print(f"❌ Error saving rooms configuration: {e}")
            return None
        
        # Step 4: Create final return structure
        print(f"\n--- STEP 4: Creating Final Configuration Structure ---")
        
        # Create the final configuration dictionary
        final_config = {
            safe_house_name: {
                "b_house_path": house_file_path,
                "items_config": config_file_path
            }
        }
        
        # Step 5: Create comprehensive summary
        total_items_across_rooms = sum(len(items) for items in filtered_rooms_config.values() if isinstance(items, list))
        
        generation_summary = {
            "house_name": house_name,
            "total_rooms": len(house_rooms_data),
            "total_items_generated": total_items_across_rooms,
            "initial_room": filtered_rooms_config.get("initial_room", "unknown"),
            "room_names": list(filtered_rooms_config.keys()),
            "house_file": house_file_path,
            "config_file": config_file_path,
            "rooms_with_items": {k: len(v) for k, v in filtered_rooms_config.items() if isinstance(v, list)}
        }
        
        # Final result
        result = {
            "config": final_config,
            "generation_summary": generation_summary,
            "rooms_config": filtered_rooms_config  # Now using filtered version
        }
        
        # Print final summary
        print(f"\n{'='*80}")
        print(f"🎉 BASE STATE GENERATION COMPLETE!")
        print(f"{'='*80}")
        print(f"🏠 House: {house_name}")
        print(f"🚪 Rooms: {len(house_rooms_data)}")
        print(f"📦 Total Items: {total_items_across_rooms}")
        print(f"🏠 House File: {house_file_path}")
        print(f"⚙️  Config File: {config_file_path}")
        print(f"🚪 Initial Room: {filtered_rooms_config.get('initial_room', 'unknown')}")
        print(f"\n📋 Rooms Summary:")
        for room_name, items in filtered_rooms_config.items():
            if isinstance(items, list):
                print(f"   • {room_name}: {len(items)} items")
        print(f"{'='*80}")

        self.InitialStateConst.add_state_configuration(final_config, "local_ai_gens")
        self.signal_queue.put((CrafterSignal.COMPLETED, None))  # 50% done

        return result

# Example usage
if __name__ == "__main__":
    crafter = BaseCrafter()

    concept="A tiny home inside the crack on a wall inside a NY apartment."

    print(f"\n🚀 TESTING CONCEPT: {concept}")
    
    result = crafter.generate_base_state(
        initial_idea=concept
    )
    
    if result:
        print(f"\n✅ SUCCESS! Generated complete base state.")
        print(f"📁 Config Structure: {result['config']}")
        
        # Show the rooms config structure as an example
        print(f"\n📋 Rooms Config Preview:")
        rooms_config = result['rooms_config']
        for room_name, items in list(rooms_config.items())[:3]:  # Show first 3 rooms
            if isinstance(items, list):
                item_preview = items[:2] if items else []  # Show first 2 items
                print(f"   '{room_name}': {item_preview}{'...' if len(items) > 2 else ''}")
            else:
                print(f"   '{room_name}': '{items}'")  # This would be initial_room
        
        if len(rooms_config) > 4:  # 3 rooms + initial_room key
            print(f"   ... and {len(rooms_config) - 4} more rooms")
            
    else:
        print(f"❌ Failed to generate base state for: {concept}")
    
    print(f"\n{'-'*60}\n")