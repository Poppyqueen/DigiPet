import os
import re
import sys
import time
import threading
from typing import Dict, Any, List
from enum import Enum
import json

from pygame_int.main_menu_areas.crafter_signal import CrafterSignal



from data_constructors.bundles_construct import bundles_maker
from data_constructors.room_generator import room_crafter
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
        self.rooms_crafter = room_crafter(select_model, select_provider, signal_queue=signal_queue)

        self.InitialStateConst = initial_states_manager

        self.signal_queue = signal_queue
               
        # Shutdown mechanism
        self._shutdown_event = threading.Event()
        self._current_operation = None


    def request_shutdown(self):
        """Request shutdown from external thread/process"""
        print("🛑 BaseCrafter shutdown requested...")
        self._shutdown_event.set()
        
        # Also request shutdown for room crafter
        if hasattr(self.rooms_crafter, 'request_shutdown'):
            self.rooms_crafter.request_shutdown()
        
        # Also request shutdown for items crafter if it supports it
        if hasattr(self.items_crafter, 'request_shutdown'):
            self.items_crafter.request_shutdown()
        
        self._send_signal(CrafterSignal.SHUTDOWN_REQUESTED, None)

    def is_shutdown_requested(self):
        """Check if shutdown has been requested"""
        return self._shutdown_event.is_set()

    def _check_shutdown(self, operation_name=""):
        """Check for shutdown request and handle if needed"""
        if self.is_shutdown_requested():
            print(f"🛑 BaseCrafter shutdown detected during: {operation_name}")
            self._send_signal(CrafterSignal.SHUTDOWN_COMPLETE, {"interrupted_at": operation_name})
            return True
        return False




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
        """
        # Check for shutdown at the start of filtering
        if self._check_shutdown("unique_types_filtering"):
            return rooms_config  # Return unfiltered config
            
        print(f"\n--- FILTERING UNIQUE TYPES ---")
        print(f"Unique types to enforce: {UNIQUE_TYPES}")
        
        unique_types_found = {}
        filtered_rooms_config = {}
        
        # First pass: identify all unique types and their first occurrence
        for room_name, item_names in rooms_config.items():
            # Check for shutdown periodically
            if self._check_shutdown(f"filtering_room_{room_name}"):
                return rooms_config
                
            if room_name == "initial_room":
                filtered_rooms_config[room_name] = item_names
                continue
                
            if room_name not in all_rooms_data:
                filtered_rooms_config[room_name] = item_names
                continue
            
            room_items_data = all_rooms_data[room_name]
            item_name_to_data = {}
            
            for item_data in room_items_data:
                if "name" in item_data:
                    item_name_to_data[item_data["name"]] = item_data
            
            for item_name in item_names:
                if item_name in item_name_to_data:
                    item_data = item_name_to_data[item_name]
                    
                    if "type" in item_data and isinstance(item_data["type"], list):
                        item_types = item_data["type"]
                        
                        for item_type in item_types:
                            if item_type in UNIQUE_TYPES:
                                if item_type not in unique_types_found:
                                    unique_types_found[item_type] = (room_name, item_name)
                                    print(f"✅ Found unique type '{item_type}' in '{room_name}' - '{item_name}' (KEEPING)")
                                else:
                                    existing_room, existing_item = unique_types_found[item_type]
                                    print(f"🔍 Found duplicate unique type '{item_type}' in '{room_name}' - '{item_name}' (already in '{existing_room}' - '{existing_item}' - WILL REMOVE)")

        # Second pass: build filtered config, removing duplicates
        items_removed = 0
        for room_name, item_names in rooms_config.items():
            # Check for shutdown
            if self._check_shutdown(f"filtering_final_{room_name}"):
                return filtered_rooms_config  # Return what we have so far
                
            if room_name == "initial_room":
                filtered_rooms_config[room_name] = item_names
                continue
                
            if room_name not in all_rooms_data:
                filtered_rooms_config[room_name] = item_names
                continue
            
            room_items_data = all_rooms_data[room_name]
            item_name_to_data = {}
            
            for item_data in room_items_data:
                if "name" in item_data:
                    item_name_to_data[item_data["name"]] = item_data
            
            filtered_item_names = []
            
            for item_name in item_names:
                should_keep_item = True
                
                if item_name in item_name_to_data:
                    item_data = item_name_to_data[item_name]
                    
                    if "type" in item_data and isinstance(item_data["type"], list):
                        item_types = item_data["type"]
                        
                        for item_type in item_types:
                            if item_type in UNIQUE_TYPES:
                                if item_type in unique_types_found:
                                    keeper_room, keeper_item = unique_types_found[item_type]
                                    if not (room_name == keeper_room and item_name == keeper_item):
                                        should_keep_item = False
                                        items_removed += 1
                                        print(f"❌ Removing duplicate '{item_name}' (type: {item_type}) from '{room_name}'")
                                        break
                
                if should_keep_item:
                    filtered_item_names.append(item_name)
            
            filtered_rooms_config[room_name] = filtered_item_names
        
        print(f"Filtering complete: {items_removed} duplicate unique-type items removed")
        return filtered_rooms_config
                
    def generate_base_state(self, initial_idea: str, 
                           houses_output_dir: str = "inventory_items/base_state_manager/houses_data/local_ai_gens",
                           configs_output_dir: str = "inventory_items/base_state_manager/houses_configs/local_ai_gens") -> Dict[str, Any] | None:
        """
        Complete orchestration of house + items generation from a single idea.
        Now with shutdown support.
        """
        print(f"\n{'='*80}")
        print(f"GENERATING COMPLETE BASE STATE")
        print(f"Concept: {initial_idea}")
        print(f"{'='*80}")

        # Reset shutdown state and partial data for new generation
        self._shutdown_event.clear()
        self._current_operation = "base_state_generation"

        # Check for early shutdown
        if self._check_shutdown("initialization"):
            return None

        self._send_signal(CrafterSignal.ANALYZING_PROMPT, None)
        
        # Step 1: Generate the house with rooms
        print(f"\n--- STEP 1: Generating House Structure ---")
        self._current_operation = "house_generation"
        
        # Check shutdown before expensive operation
        if self._check_shutdown("before_house_generation"):
            return None
            
        base_house = self.rooms_crafter.orchestrate_generation(
            initial_idea=initial_idea,
            output_dir=houses_output_dir
        )

        # Check shutdown after house generation
        if self._check_shutdown("after_house_generation"):
            # Save partial house data
            return None

        self._send_signal(CrafterSignal.GENERATING_STATE, None)
        
        if not base_house:
            print("❌ Failed to generate house structure. Aborting.")
            return None
        
        house_name = base_house["house_name"]
        house_file_path = base_house["file_path"]
        house_rooms_data = base_house["room_data"]
        
        
        print(f"✅ House '{house_name}' generated with {len(house_rooms_data)} rooms")
        
        # Step 2: Generate items for each room
        print(f"\n--- STEP 2: Generating Items for Each Room ---")
        self._current_operation = "items_generation"
        
        rooms_config = {}
        all_rooms_data = {}
        
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

            # Check for shutdown before processing each room
            if self._check_shutdown(f"room_{room_name}_generation"):
                # Save what we have so far
                return None

            print(f"\n--- Processing Room {current_room_number}/{total_rooms}: '{room_name}' ---")
            process_value = (current_room_number / total_rooms) * 100
            self._send_signal(CrafterSignal.PROGRESS_UPDATE, process_value)

            # Extract descriptions
            prompt_context = []
            for time_period, descriptions in room["descriptions"].items():
                if isinstance(descriptions, list):
                    prompt_context.extend(descriptions)
                else:
                    prompt_context.append(descriptions)
            
            final_descriptions = "\n".join(prompt_context)
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
                output_dir="inventory_items/items_provider/items_data/local_ai_gens"
            )
            
            # Check shutdown after item generation
            if self._check_shutdown(f"after_room_{room_name}_items"):
                return None
            
            if room_bundle and "item_data" in room_bundle:
                all_rooms_data[room_name] = room_bundle["item_data"]
                
                item_names = []
                for item in room_bundle["item_data"]:
                    if "name" in item:
                        item_names.append(item["name"])
                
                rooms_config[room_name] = item_names
                print(f"✅ Generated {len(item_names)} items for '{room_name}'")
                
                if item_names:
                    example_items = item_names[:3]
                    print(f"   Examples: {', '.join(example_items)}")
                    if len(item_names) > 3:
                        print(f"   ... and {len(item_names) - 3} more")
            else:
                print(f"❌ Failed to generate items for room: '{room_name}'")
                rooms_config[room_name] = []
                all_rooms_data[room_name] = []
            
            
            # Add delay between rooms (except for the last one) with shutdown checks
            if current_room_number < total_rooms:
                print("⏳ Pausing 5 seconds before next room...")
                for i in range(5):  # Check shutdown every second during delay
                    if self._check_shutdown(f"delay_after_room_{room_name}"):
                        return None
                    time.sleep(1)
        
        # Step 2.5: Apply unique types filter
        print(f"\n--- STEP 2.5: Applying Unique Types Filter ---")
        if self._check_shutdown("before_filtering"):
            return None
            
        filtered_rooms_config = self._filter_unique_types(all_rooms_data, rooms_config)
        
        # Check shutdown after filtering
        if self._check_shutdown("after_filtering"):
            return None
        
        # Step 3: Save the rooms configuration
        print(f"\n--- STEP 3: Saving Filtered Rooms Configuration ---")
        if self._check_shutdown("before_saving_config"):
            return None
        
        os.makedirs(configs_output_dir, exist_ok=True)
        safe_house_name = re.sub(r'[^a-zA-Z0-9_-]', '_', house_name.lower())
        config_file_path = os.path.join(configs_output_dir, f"{safe_house_name}_config.json")
        
        try:
            with open(config_file_path, 'w') as f:
                json.dump(filtered_rooms_config, f, indent=4)
            print(f"✅ Filtered rooms configuration saved to: {config_file_path}")
        except Exception as e:
            print(f"❌ Error saving rooms configuration: {e}")
            return None
        
        # Check shutdown after saving
        if self._check_shutdown("after_saving_config"):
            return None
        
        # Step 4: Create final return structure
        print(f"\n--- STEP 4: Creating Final Configuration Structure ---")
        
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
        
        result = {
            "config": final_config,
            "generation_summary": generation_summary,
            "rooms_config": filtered_rooms_config
        }
        
        # Final check before completion
        if self._check_shutdown("before_completion"):
            return None
        
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
        self._send_signal(CrafterSignal.COMPLETED, None)
        
        return result


# Example usage with thread management
if __name__ == "__main__":
    import queue
    import threading
    
    # Create signal queue
    signal_queue = queue.Queue()
    
    # Create crafter
    crafter = BaseCrafter(signal_queue=signal_queue)
    
    
    # Function to run in thread
    def run_generation():
        concept = "A tiny home inside the crack on a wall inside a NY apartment."
        print(f"\n🚀 TESTING CONCEPT: {concept}")
        
        result = crafter.generate_base_state(initial_idea=concept)
        
        if result:
            print(f"\n✅ SUCCESS! Generated complete base state.")
        else:
            print(f"❌ Generation failed or was interrupted.")
    
    # Start generation in thread
    generation_thread = threading.Thread(target=run_generation)
    generation_thread.start()
    
    # Simulate shutdown request after 10 seconds (for testing)
    def request_shutdown_after_delay():
        time.sleep(10)
        print("\n🛑 Requesting shutdown from main thread...")
        crafter.request_shutdown()
    
    shutdown_thread = threading.Thread(target=request_shutdown_after_delay)
    shutdown_thread.start()
    
    # Monitor signals
    while generation_thread.is_alive():
        try:
            signal, data = signal_queue.get(timeout=1)
            print(f"📡 Received signal: {signal} - Data: {data}")
            
            if signal == CrafterSignal.SHUTDOWN_COMPLETE:
                print("🛑 Shutdown completed!")
                break
                
        except queue.Empty:
            continue
    
    # Wait for threads to complete
    generation_thread.join()
    shutdown_thread.join()
    
    print("\n🏁 All threads completed.")