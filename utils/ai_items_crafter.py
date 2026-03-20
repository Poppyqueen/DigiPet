from inventory_items.items_validation.ai_schema_builder import build_llm_schema_for_types
from ai_managers.ai_utils.ai_loader import AIConfiguration
# get_mcp_item_types already imported in item_pydantic_models, re-expose it:


# ItemsCrafter — replace base_path with valid_types
class ItemsCrafter:
    def __init__(self, provider, model, retries=4, valid_types: list[str] | None = None):
        self.client = AIConfiguration(provider=provider, model=model, mode="simple_ai").get_client()
        self.retries = retries
        self._valid_types = valid_types

    def craft_item(self, user_prompt: str, select_types: list[str]) -> list[dict] | None:
        # Validate that the requested types are actually known to this agent
        unknown = [t for t in select_types if t not in self._valid_types]
        if unknown:
            print(f"Warning: ItemsCrafter asked to craft unknown types {unknown} — skipping.")
            select_types = [t for t in select_types if t in self._valid_types]
        if not select_types:
            return None

        schema = build_llm_schema_for_types(select_types)

        for attempt in range(self.retries):
            try:
                response = self.client.structured_output(
                    system=f"Please return structured responses using all the following types or type: #### {select_types} ####.",
                    user=user_prompt,
                    structure=schema
                )
                if not response:
                    print(f"Empty response, retrying... ({attempt + 1}/{self.retries})")
                    continue
                return [item.model_dump() for item in response.items]
            except Exception as e:
                print(f"Error on attempt {attempt + 1}/{self.retries}: {e}")
        return None