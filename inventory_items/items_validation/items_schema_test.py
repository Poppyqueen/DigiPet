import json
import argparse
from inventory_items.items_validation.ai_schema_builder import (
    build_llm_schema_for_types, 
    build_room_llm_schema_for_types # Imported the new builder
)
from ai_managers.ai_utils.ai_loader import AIConfiguration

AVAILABLE_SIMPLE_AI = AIConfiguration.get_providers_by_mode("simple_ai")

def main():
    # 1. Setup Argument Parser
    parser = argparse.ArgumentParser(description="Test AI schema generation for inventory items or rooms.")
    
    parser.add_argument(
        "--types", 
        nargs="*", # Changed from "+" to "*" to allow zero items
        default=[],
        help="List of types to include in the schema (space-separated or empty)."
    )
    
    parser.add_argument(
        "--prompt", 
        type=str, 
        default="One example of this item. Portable Gadget. Tamagotchi.",
        help="The user prompt to send to the AI."
    )

    # Logic switch for Item vs Room generation
    parser.add_argument(
        "--mode",
        type=str,
        choices=["item", "room"],
        default="item",
        help="Decide whether to generate a single 'item' or a 'room' layout."
    )

    # AI Configuration arguments
    parser.add_argument(
        "--provider", 
        type=str, 
        default="openai",
        choices=AVAILABLE_SIMPLE_AI,
        help="The AI provider to use."
    )

    parser.add_argument(
        "--model", 
        type=str, 
        default="gpt-5.4-nano",
        help="The specific model name."
    )

    args = parser.parse_args()

    # 2. Initialize AI Client
    print(f"--- Initializing {args.provider} with model {args.model} ---")
    client = AIConfiguration(
        provider=args.provider, 
        model=args.model, 
        mode="simple_ai"
    ).get_client()

    # 3. Build Schema based on Mode
    print(f"--- Building {args.mode} schema for types: {args.types} ---")
    
    if args.mode == "room":
        test_base = build_room_llm_schema_for_types(args.types)
    else:
        test_base = build_llm_schema_for_types(args.types)
    
    # 4. Request Structured Output
    # Tweaked system prompt slightly to reflect the mode
    system_prompt = (
        f"Please return structured responses for a {args.mode} using all the following types (If no type given, leave types as an empty list.): "
        f"#### {args.types} #### Always generate only 1 {args.mode}."
    )
    
    print(f"--- Sending Prompt: '{args.prompt}' ---")
    
    response = client.structured_output(
        system=system_prompt, 
        user=args.prompt, 
        structure=test_base
    )

    # 5. Output Result
    print(f"\n--- AI {args.mode.capitalize()} Response ---")
    print(response.model_dump_json(indent=2))

if __name__ == "__main__":
    main()


''' example item (no mode defaults to item), from project root:
python -m inventory_items.items_validation.items_schema_test \
  --provider openrouter \
  --model google/gemma-4-26b-a4b-it \
  --types drawing_area toggleable \
  --prompt "Drawing tablet, completely portable, with a screen and stylus."
'''

''' example item (no mode defaults to item), from project root:
python -m inventory_items.items_validation.items_schema_test \
  --provider openrouter \
  --model google/gemma-4-26b-a4b-it \
  --prompt "Single Ball Pit Plastic Ball, blue"
'''

''' example item (no mode defaults to item), from project root:
python -m inventory_items.items_validation.items_schema_test \
  --provider openrouter \
  --model google/gemma-4-26b-a4b-it \
  --prompt "Single Ball Pit Plastic Ball, purple"
'''

''' example room, from project root:
python -m inventory_items.items_validation.items_schema_test \
  --provider openrouter \
  --model google/gemma-4-26b-a4b-it \
  --mode room \
  --types outdoors_area open_soil_zone \
  --prompt "Astro-punk cabin garden"
'''

''' example room, from project root:
python -m inventory_items.items_validation.items_schema_test \
  --provider openrouter \
  --model google/gemma-4-26b-a4b-it \
  --mode room \
  --prompt "Giant ball pit room"
'''

''' example item (no mode defaults to item), from project root (not sure if a toggleable consumable is a good idea):
python -m inventory_items.items_validation.items_schema_test \
  --provider openrouter \
  --model google/gemma-4-26b-a4b-it \
  --types consumable toggleable \
  --prompt "Potato chips bag"
'''