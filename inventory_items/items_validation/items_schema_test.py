import json
import argparse
from inventory_items.items_validation.ai_schema_builder import build_llm_schema_for_types
from ai_managers.ai_utils.ai_loader import AIConfiguration
AVAILABLE_SIMPLE_AI=AIConfiguration.get_providers_by_mode("simple_ai")

def main():
    # 1. Setup Argument Parser
    parser = argparse.ArgumentParser(description="Test AI schema generation for inventory items.")
    
    parser.add_argument(
        "--types", 
        nargs="+", 
        default=["toggleable", "tamagotchi_device"],
        help="List of item types to include in the schema (space-separated)."
    )
    
    parser.add_argument(
        "--prompt", 
        type=str, 
        default="One example of this item. Portable Gadget. Tamagotchi.",
        help="The user prompt to send to the AI."
    )

    # New arguments for AI Configuration
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
        default="gpt-5.4-nano", # Set a standard default
        help="The specific model name."
    )

    args = parser.parse_args()

    # 2. Initialize AI Client
    # Now passing the provider and model from CLI arguments
    print(f"--- Initializing {args.provider} with model {args.model} ---")
    client = AIConfiguration(
        provider=args.provider, 
        model=args.model, 
        mode="simple_ai"
    ).get_client()

    # 3. Build Schema
    print(f"--- Building schema for types: {args.types} ---")
    test_base = build_llm_schema_for_types(args.types)
    
    # 4. Request Structured Output
    system_prompt = f"Please return structured responses using all the following types or type: #### {args.types} #### Always generate only 1 item."
    
    print(f"--- Sending Prompt: '{args.prompt}' ---")
    
    response = client.structured_output(
        system=system_prompt, 
        user=args.prompt, 
        structure=test_base
    )

    # 5. Output Result
    print("\n--- AI Response ---")
    print(response.model_dump_json(indent=2))

if __name__ == "__main__":
    main()



''' example, from project root:
python -m inventory_items.items_validation.items_schema_test \
  --provider openrouter \
  --model google/gemma-4-26b-a4b-it \
  --types discogs_endpoint toggleable \
  --prompt "iPod, broken speakers and no headphones."
'''