# python -m data_constructors.dev_crafter.batch_process
import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

import yaml

# Internal imports
from ai_managers.ai_utils.ai_loader import AIConfiguration
from inventory_items.items_validation.ai_schema_builder import (
    build_llm_schema_for_types,
    build_room_llm_schema_for_types,
)


def save_incremental(output_path: Path, mode: str, data_list: list):
    """
    Overwrites the specific mode's JSON file with the current list of objects.
    """
    file_path = output_path / f"{mode}s.json"
    with open(file_path, "w") as f:
        json.dump(data_list, f, indent=2)
    print(f"   [Disk] Updated {file_path}")


def main():
    # --- Setup & Manifest Loading ---
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", 
        default="data_constructors/dev_crafter/manifest.yaml"
    )
    args = parser.parse_args()

    try:
        with open(args.manifest, "r") as f:
            manifest = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Error: Manifest file not found at {args.manifest}")
        return

    config = manifest.get("config", {})
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Corrected path logic to avoid the "Read-only" root error
    raw_path = config.get("export_dir", "./output").lstrip("/")
    output_path = Path.cwd() / raw_path / f"session_{timestamp}"
    output_path.mkdir(parents=True, exist_ok=True)

    # Storage for the runtime session
    results = {"item": [], "room": []}

    print(f"--- Initializing {config.get('provider')} client ---")
    client_manager = AIConfiguration(
        provider=config.get("provider"),
        model=config.get("model"),
        mode="simple_ai",
    )
    client = client_manager.get_client()

# --- Processing Tasks ---
    for task in manifest.get("tasks", []):
        mode = task.get("mode", "item")
        types = task.get("types", [])
        prompts = task.get("prompts", [])
        
        context_raw = task.get("context", "")
        context = " ".join(context_raw) if isinstance(context_raw, list) else context_raw

        if mode == "room":
            schema = build_room_llm_schema_for_types(types)
        else:
            schema = build_llm_schema_for_types(types)

        for prompt in prompts:
            full_prompt = f"{context} {prompt}".strip()
            
            type_list_str = ", ".join(types) if types else "empty"
            system_instruction = (
                f"Generate 1 {mode} using types ONLY THE GIVEN TYPES: {type_list_str}."
                if types else f"Generate 1 {mode}. Types empty."
            )

            try:
                print(f"Generating {mode}: '{prompt[:50]}...'")
                response = client.structured_output(
                    system=system_instruction,
                    user=full_prompt,
                    structure=schema,
                )

                # Convert response to dictionary
                raw_data = response.model_dump()
                
                # Use the key we discovered (items or rooms)
                # We use .get() and fallback to an empty list to avoid crashes
                key = f"{mode}s" 
                data_list = raw_data.get(key, [])

                if data_list and isinstance(data_list, list):
                    # Take the first object from the LLM's list and 
                    # add it to our session's flat list
                    results[mode].append(data_list[0])
                    
                    # Save the flattened list to disk
                    save_incremental(output_path, mode, results[mode])
                else:
                    print(f"⚠️ Expected key '{key}' not found in LLM response.")

                time.sleep(1)

            except Exception as e:
                print(f"❌ Failed to generate '{prompt}': {e}")
                continue

    print(f"\n--- Batch Complete ---")
    print(f"Results saved in: {output_path}")


if __name__ == "__main__":
    main()