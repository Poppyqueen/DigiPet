from inventory_items.items_validation.ai_schema_builder import build_llm_schema_for_types, build_room_llm_schema_for_types

import json

from ai_managers.ai_utils.ai_loader import AIConfiguration


client=AIConfiguration(provider="openai",model="gpt-5-mini",mode="simple_ai").get_client()
test_base = build_llm_schema_for_types(["tv", "furniture"])

print(json.dumps(test_base.model_json_schema(), indent=2))


response = client.structured_output(system="Please return a single item definition", user="A retro-futuristic TV", structure=test_base)

print(response.model_dump_json(indent=2))