import os
import re
import sys
import time
import threading
from typing import Dict, Any, List
from enum import Enum
import json

from pygame_int.main_menu_int.utils.crafter_signal import CrafterSignal



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
        self.items_crafter = bundles_maker(select_model, select_provider)
        self.rooms_crafter = room_crafter(select_model, select_provider, signal_queue=signal_queue)
        self.InitialStateConst = initial_states_manager
        self.signal_queue = signal_queue
        self._shutdown_event = threading.Event()


    def request_shutdown(self):
        print("🛑 BaseCrafter shutdown requested...")
        self._shutdown_event.set()
        if hasattr(self.rooms_crafter, 'request_shutdown'):
            self.rooms_crafter.request_shutdown()

    def is_shutdown_requested(self):
        """Check if shutdown has been requested"""
        return self._shutdown_event.is_set()


    def _check_shutdown(self, operation_name=""):
        if self._shutdown_event.is_set():
            print(f"🛑 Shutdown detected during: {operation_name}")
            self._send_signal(CrafterSignal.SHUTDOWN_COMPLETE, {"interrupted_at": operation_name})
            return True
        return False





    def _send_signal(self, signal, data=None):
        if self.signal_queue:
            try:
                self.signal_queue.put((signal, data))
            except Exception as e:
                print(f"Warning: Failed to send signal {signal}: {e}")

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
        Complete orchestration of house + items generation from a single idea,
        instrumented with detailed signals for UI feedback.
        """
        try:
            print(f"\n{'='*80}")
            print(f"GENERATING COMPLETE BASE STATE")
            print(f"Concept: {initial_idea}")
            print(f"{'='*80}")

            # Reset shutdown state for the new generation run
            self._shutdown_event.clear()

            # --- STEP 1: FOUNDATION (House & Room Structure Generation) ---
            self._send_signal(CrafterSignal.FOUNDATION_START)
            self._send_signal(CrafterSignal.FLAVOR_TEXT, "Dreaming up a floor plan...")
            if self._check_shutdown("before_house_generation"): return None

            base_house = self.rooms_crafter.orchestrate_generation(
                initial_idea=initial_idea,
                output_dir=houses_output_dir
            )

            if self._check_shutdown("after_house_generation"): return None
            if not base_house:
                raise ValueError("Failed to generate the base house structure. The process returned None.")
            
            self._send_signal(CrafterSignal.FOUNDATION_COMPLETE)
            
            house_name = base_house["house_name"]
            house_file_path = base_house["file_path"]
            house_rooms_data = base_house["room_data"]
            print(f"✅ House '{house_name}' generated with {len(house_rooms_data)} rooms")

            # --- STEP 2: POPULATION (Item Generation for each Room) ---
            self._send_signal(CrafterSignal.POPULATION_START)
            self._send_signal(CrafterSignal.FLAVOR_TEXT, "Unpacking the moving boxes...")

            time.sleep(5)

            rooms_config = {}
            all_rooms_data = {}
            
            if house_rooms_data:
                initial_room_name = house_rooms_data[0]["name"]
                rooms_config["initial_room"] = initial_room_name
                print(f"🏠 Set initial room: '{initial_room_name}'")

            total_rooms = len(house_rooms_data)
            for index, room in enumerate(house_rooms_data):
                if self._check_shutdown("after_house_generation"): return None

                current_room_number = index + 1
                room_name = room["name"]

                if self._check_shutdown(f"room_{room_name}_generation"): return None

                print(f"\n--- Processing Room {current_room_number}/{total_rooms}: '{room_name}' ---")



                prompt_context = [desc for descs in room["descriptions"].values() for desc in descs]
                final_descriptions = "\n".join(prompt_context)
                final_prompt = (
                    f"You are a creative AI tasked with generating a small to medium bundle of items "
                    f"for the following room: {room_name}. The room has the following descriptions: "
                    f"{final_descriptions}. Based on this information, create a list of items that would "
                    f"logically fit in this room. 10 items max per room."
                )


                self._send_signal(CrafterSignal.POPULATION_PROGRESS, {
                    "room_name": room_name,
                    "current": current_room_number-1,
                    "total": total_rooms
                })

                self._send_signal(CrafterSignal.FLAVOR_TEXT, f"Organizing {room_name}") # sub-step populating individual room



                room_bundle = self.items_crafter.orchestrate_bundle_generation( # This is a lengthy process
                    initial_idea=final_prompt,
                    output_dir="inventory_items/items_provider/items_data/local_ai_gens"
                )

                self._send_signal(CrafterSignal.POPULATION_PROGRESS, {
                    "room_name": room_name,
                    "current": current_room_number,
                    "total": total_rooms
                })

                if self._check_shutdown(f"after_room_{room_name}_items"): return None

                if room_bundle and "item_data" in room_bundle:
                    all_rooms_data[room_name] = room_bundle["item_data"]
                    item_names = [item["name"] for item in room_bundle["item_data"] if "name" in item]
                    rooms_config[room_name] = item_names
                    print(f"✅ Generated {len(item_names)} items for '{room_name}'")
                else:
                    print(f"❌ Failed to generate items for room: '{room_name}'")
                    rooms_config[room_name] = []
                    all_rooms_data[room_name] = []

                if current_room_number < total_rooms:
                    print("⏳ Pausing 5 seconds before next room...")
                    for _ in range(5):
                        if self._check_shutdown(f"delay_after_room_{room_name}"): return None
                        time.sleep(1)

            self._send_signal(CrafterSignal.POPULATION_COMPLETE)

            # --- STEP 2.5: FILTERING (Applying Unique Types Filter) ---
            self._send_signal(CrafterSignal.FILTERING_START)
            #self._send_signal(CrafterSignal.FLAVOR_TEXT, "Ensuring no two snowflakes are alike...")
            if self._check_shutdown("before_filtering"): return None

            filtered_rooms_config = self._filter_unique_types(all_rooms_data, rooms_config)
            
            if self._check_shutdown("after_filtering"): return None
            self._send_signal(CrafterSignal.FILTERING_COMPLETE)

            # --- STEP 3: SAVING (Writing Config Files to Disk) ---
            self._send_signal(CrafterSignal.SAVING_START)
            if self._check_shutdown("before_saving_config"): return None

            os.makedirs(configs_output_dir, exist_ok=True)
            safe_house_name = re.sub(r'[^a-zA-Z0-9_-]', '_', house_name.lower())
            config_file_path = os.path.join(configs_output_dir, f"{safe_house_name}_config.json")
            
            with open(config_file_path, 'w') as f:
                json.dump(filtered_rooms_config, f, indent=4)
            print(f"✅ Filtered rooms configuration saved to: {config_file_path}")
            
            if self._check_shutdown("after_saving_config"): return None
            self._send_signal(CrafterSignal.SAVING_COMPLETE)
            
            # --- STEP 4: FINALIZING (Creating Final Data Structure) ---
            self._send_signal(CrafterSignal.FINALIZING)
            #sself._send_signal(CrafterSignal.FLAVOR_TEXT, "Tidying up and adding the final touches!")
            if self._check_shutdown("before_completion"): return None

            final_config = {
                safe_house_name: {
                    "b_house_path": house_file_path,
                    "items_config": config_file_path
                }
            }
            
            total_items_across_rooms = sum(len(items) for items in filtered_rooms_config.values() if isinstance(items, list))
            generation_summary = {
                "house_name": house_name, "total_rooms": len(house_rooms_data),
                "total_items_generated": total_items_across_rooms,
                "initial_room": filtered_rooms_config.get("initial_room", "unknown"),
                "house_file": house_file_path, "config_file": config_file_path
            }
            
            result = {
                "config": final_config,
                "generation_summary": generation_summary,
                "rooms_config": filtered_rooms_config
            }

            # --- STEP 5: COMPLETION ---
            print(f"\n{'='*80}")
            print(f"🎉 BASE STATE GENERATION COMPLETE!")
            print(f"   House: {house_name} ({len(house_rooms_data)} rooms, {total_items_across_rooms} items)")
            print(f"{'='*80}")

            self.InitialStateConst.add_state_configuration(final_config, "local_ai_gens")
            self._send_signal(CrafterSignal.OVERALL_COMPLETE)
            
            return result

        except Exception as e:
            # Catch any error during the process, log it, and send a signal to the UI
            print(f"❌ An unrecoverable error occurred during base state generation: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            self._send_signal(CrafterSignal.ERROR, str(e))
            return None


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