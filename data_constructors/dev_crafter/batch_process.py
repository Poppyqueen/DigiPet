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

class RateLimiter:
    def __init__(self, requests_per_second=2, batch_size=100, idle_time=5):
        self.delay = 1.0 / requests_per_second
        self.batch_size = batch_size
        self.idle_time = idle_time
        self.request_count = 0
        self.last_request_time = 0

    def wait_if_needed(self):
        # 1. Handle Request-per-second limit
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

        # 2. Handle Batch Idle/Cool-down
        self.request_count += 1
        if self.request_count % self.batch_size == 0:
            print(f"   [RateLimit] Reached {self.batch_size} requests. Idling for {self.idle_time}s...")
            time.sleep(self.idle_time)
        
        self.last_request_time = time.time()

def save_incremental(output_path: Path, mode: str, data_list: list):
    file_path = output_path / f"{mode}s.json"
    with open(file_path, "w") as f:
        json.dump(data_list, f, indent=2)
    print(f"   [Disk] Updated {file_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data_constructors/dev_crafter/manifest.yaml")
    args = parser.parse_args()

    try:
        with open(args.manifest, "r") as f:
            manifest = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Error: Manifest file not found at {args.manifest}")
        return

    config = manifest.get("config", {})
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = config.get("export_dir", "./output").lstrip("/")
    output_path = Path.cwd() / raw_path / f"session_{timestamp}"
    output_path.mkdir(parents=True, exist_ok=True)

    results = {"item": [], "room": []}

    print(f"--- Initializing {config.get('provider')} client ---")
    client_manager = AIConfiguration(
        provider=config.get("provider"),
        model=config.get("model"),
        mode="simple_ai",
    )
    client = client_manager.get_client()

    # --- Initialize Rate Limiter ---
    limiter = RateLimiter(requests_per_second=2, batch_size=100, idle_time=5)

    for task in manifest.get("tasks", []):
        mode = task.get("mode", "item")
        types = task.get("types", [])
        prompts = task.get("prompts", [])
        context_raw = task.get("context", "")
        context = " ".join(context_raw) if isinstance(context_raw, list) else context_raw

        schema = build_room_llm_schema_for_types(types) if mode == "room" else build_llm_schema_for_types(types)

        # 2. Get the JSON schema dictionary from the class
        schema_dict = schema.model_json_schema()

        # 3. Print it beautifully with indentation
        print(json.dumps(schema_dict, indent=4))

        for prompt in prompts:
            # Apply Rate Limiting before the call
            limiter.wait_if_needed()

            full_prompt = f"{context} {prompt}".strip()
            type_list_str = ", ".join(types) if types else "empty"

            system_instruction = (
                f"Generate 1 {mode}. The 'type' field MUST contain ALL of these types exactly: {types}. "
                f"Do not omit any. Do not add others."
                if types else f"Generate 1 {mode}. Types empty."
            )

            try:
                print(f"Generating {mode} ({limiter.request_count}): '{prompt[:50]}...'")
                response = client.structured_output(
                    system=system_instruction,
                    user=full_prompt,
                    structure=schema,
                )

                raw_data = response.model_dump()
                key = f"{mode}s" 
                data_list = raw_data.get(key, [])

                if data_list and isinstance(data_list, list):
                    item = data_list[0]
                    # Force type field to always be the full list we requested
                    if isinstance(item.get("type"), str):
                        item["type"] = types
                    elif isinstance(item.get("type"), list) and set(item["type"]) != set(types):
                        item["type"] = types

                    results[mode].append(item)
                    save_incremental(output_path, mode, results[mode])
                else:
                    print(f"⚠️ Expected key '{key}' not found in LLM response.")

            except Exception as e:
                print(f"❌ Failed to generate '{prompt}': {e}")
                continue

    print(f"\n--- Batch Complete ---")
    print(f"Results saved in: {output_path}")

if __name__ == "__main__":
    main()