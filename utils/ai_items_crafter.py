from inventory_items.items_validation.ai_schema_builder import build_llm_schema_for_types
from inventory_items.items_validation.item_pydantic_models import ItemType
from ai_managers.ai_utils.ai_loader import AIConfiguration

class ItemsCrafter:
    def __init__(self, provider, model, retries=4):
        self.client = AIConfiguration(provider=provider, model=model, mode="simple_ai").get_client()
        self.retries = retries

    def craft_item(self, user_prompt: str, select_types: list[ItemType]) -> list[dict] | None:
        test_base = build_llm_schema_for_types(select_types)
        for attempt in range(self.retries):
            try:
                response = self.client.structured_output(
                    system=f"Please return structured responses using all the following types or type: #### {select_types} ####.",
                    user=user_prompt,
                    structure=test_base
                )
                if not response:
                    print(f"Empty response, retrying... ({attempt + 1}/{self.retries})")
                    continue
                return [item.model_dump() for item in response.items]
            except Exception as e:
                print(f"Error on attempt {attempt + 1}/{self.retries}: {e}")
        return None