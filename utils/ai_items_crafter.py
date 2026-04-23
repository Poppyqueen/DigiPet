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
        # 1. Normalize valid_types to an empty list if it's None to avoid iteration errors
        available_types = self._valid_types or []
        select_types = select_types or []
        
        # 2. Filter requested types against what is available
        # Only perform filtering if available_types isn't empty; 
        # otherwise, we assume we're passing everything through to the builder.
        if available_types:
            unknown = [t for t in select_types if t not in available_types]
            if unknown:
                print(f"Warning: ItemsCrafter asked to craft unknown types {unknown} — skipping.")
                select_types = [t for t in select_types if t in available_types]

        # 3. Build the schema (now handles empty select_types gracefully)
        schema = build_llm_schema_for_types(select_types)

        for attempt in range(self.retries):
            try:
                response = self.client.structured_output(
                    system=f"Please return structured responses using all the following types or type: #### {select_types} ####.",
                    user=user_prompt,
                    structure=schema
                )
                
                # If the LLM returns nothing but the schema was valid, 
                # we should still handle the response safely.
                if response is None:
                    print(f"Empty response, retrying... ({attempt + 1}/{self.retries})")
                    continue
                
                return [item.model_dump() for item in response.items]
            except Exception as e:
                print(f"Error on attempt {attempt + 1}/{self.retries}: {e}")
                
        return None