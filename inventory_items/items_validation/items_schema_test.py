# python -m inventory_items.items_validation.items_schema_test
from inventory_items.items_validation.ai_schema_builder import build_llm_schema_for_types, build_room_llm_schema_for_types

import json

from ai_managers.ai_utils.ai_loader import AIConfiguration


client=AIConfiguration(provider="openrouter",model="openai/gpt-oss-20b",mode="simple_ai").get_client()
select_types = ["dispenser", "furniture"]
test_base = build_llm_schema_for_types(select_types)

# print(json.dumps(test_base.model_json_schema(), indent=2))


response = client.structured_output(system=f"Please return a single item definition using all the following types or type: #### {select_types} ####", user="Early 20th century candy dispenser", structure=test_base)

print(response.model_dump_json(indent=2))