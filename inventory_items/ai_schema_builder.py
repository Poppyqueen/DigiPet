# ai_schema_builder.py
#
# Provides build_llm_schema_for_types(), a helper that constructs a strict
# Pydantic model suitable for OpenAI structured output, scoped to only the
# item types you actually need.
#
# Usage example (in ai_cook.py):
#
#   from inventory_items.ai_schema_builder import build_llm_schema_for_types
#
#   CookSchema = build_llm_schema_for_types(["consumable"])
#   response = self.client.structured_output(system=..., user=..., structure=CookSchema)
#
# The returned model is a container with a single `items` field, mirroring
# ItemDefinitionListContainer, so existing response-handling code needs no changes.

from typing import List, Optional, Dict, Any, Type, get_args, get_origin
from pydantic import BaseModel, Field, ConfigDict, create_model

from inventory_items.item_pydantic_models import (
    BaseItem,
    TYPE_FIELD_CONTRACTS,
)


# =============================================================================
# STRICT SUB-MODEL REBUILDER
# Recursively rebuilds a BaseModel class with extra="forbid" so that nested
# models satisfy OpenAI's additionalProperties: false requirement.
# Non-BaseModel annotations are returned unchanged.
# Results are cached so the same class isn't rebuilt more than once per call.
# =============================================================================

def _make_strict(annotation: Any, cache: Dict[type, type]) -> Any:
    """
    Given a type annotation, return a version safe for OpenAI strict mode:
    - BaseModel subclasses are rebuilt with extra="forbid" (recursively).
    - Generic aliases (List[X], Optional[X], etc.) have their args processed.
    - Everything else is returned as-is.
    """
    origin = get_origin(annotation)

    # Handle generics: List[X], Optional[X], Union[X, None], Dict[K, V], etc.
    if origin is not None:
        args = get_args(annotation)
        new_args = tuple(_make_strict(a, cache) for a in args)
        # Reconstruct the generic with the new args if anything changed.
        if new_args != args:
            try:
                return origin[new_args] if len(new_args) > 1 else origin[new_args[0]]
            except Exception:
                return annotation  # fallback: leave unchanged if reconstruction fails
        return annotation

    # Handle BaseModel subclasses.
    if isinstance(annotation, type) and issubclass(annotation, BaseModel) and annotation is not BaseModel:
        if annotation in cache:
            return cache[annotation]

        strict_fields: Dict[str, Any] = {}
        for field_name, field_info in annotation.model_fields.items():
            strict_annotation = _make_strict(field_info.annotation, cache)
            # Preserve the original field's default and description.
            if field_info.default is not field_info.default:  # always False, just a pattern
                pass
            new_field = Field(
                default=field_info.default,
                description=field_info.description or "",
            )
            strict_fields[field_name] = (strict_annotation, new_field)

        strict_model = create_model(
            f"Strict_{annotation.__name__}",
            __config__=ConfigDict(extra="forbid"),
            **strict_fields,
        )
        cache[annotation] = strict_model
        return strict_model

    return annotation


# =============================================================================
# PUBLIC HELPER
# =============================================================================

def build_llm_schema_for_types(types: List[str]) -> Type[BaseModel]:
    """
    Builds a strict Pydantic container model for LLM structured output,
    including only the fields relevant to the given item types.

    Args:
        types: List of item type strings, e.g. ["consumable"] or ["seed", "consumable"].
               Only contracts registered in TYPE_FIELD_CONTRACTS are considered;
               unknown or contract-free types (misc, furniture, etc.) are silently ignored.

    Returns:
        A Pydantic model class with a single `items: List[ItemDefinition]` field,
        where ItemDefinition contains BaseItem fields + the requested type fields,
        all rebuilt with extra="forbid" for OpenAI strict mode compatibility.

    Raises:
        ValueError: If none of the requested types have registered contracts
                    (i.e. the resulting schema would have no type-specific fields
                    beyond BaseItem — likely a mistake on the caller's side).
    """
    strict_cache: Dict[type, type] = {}

    # Collect fields from the relevant contracts only.
    seen: set = set()
    fields: Dict[str, Any] = {}
    field_to_types: Dict[str, List[str]] = {}

    relevant_contracts = {
        t: TYPE_FIELD_CONTRACTS[t] for t in types if t in TYPE_FIELD_CONTRACTS
    }

    if not relevant_contracts:
        raise ValueError(
            f"None of the requested types {types} have registered field contracts. "
            f"Registered types: {list(TYPE_FIELD_CONTRACTS.keys())}"
        )

    # Build field_to_types map for description annotation.
    for type_str, contract_class in relevant_contracts.items():
        for field_name in contract_class.model_fields:
            field_to_types.setdefault(field_name, []).append(type_str)

    for type_str, contract_class in relevant_contracts.items():
        for field_name, field_info in contract_class.model_fields.items():
            if field_name in seen:
                continue
            seen.add(field_name)

            # Rebuild nested models as strict variants.
            strict_annotation = _make_strict(field_info.annotation, strict_cache)

            # Wrap in Optional so the LLM can omit fields for irrelevant types.
            origin = get_origin(strict_annotation)
            args = get_args(strict_annotation)
            is_already_optional = origin is not None and type(None) in args
            if not is_already_optional:
                optional_annotation = Optional[strict_annotation]
            else:
                optional_annotation = strict_annotation

            # Annotate description with which types require this field.
            required_types = field_to_types.get(field_name, [type_str])
            if len(required_types) == 1:
                requirement_note = f"Required when type includes '{required_types[0]}'."
            else:
                quoted = ", ".join(f"'{t}'" for t in required_types)
                requirement_note = f"Required when type includes any of: {quoted}."

            original_desc = field_info.description or ""
            full_description = f"{requirement_note} {original_desc}".strip()

            fields[field_name] = (
                optional_annotation,
                Field(default=None, description=full_description),
            )

    type_label = "_".join(sorted(types))
    ItemDefinition = create_model(
        f"ItemDefinition_{type_label}",
        __base__=BaseItem,
        __config__=ConfigDict(extra="forbid"),
        **fields,
    )

    class _Container(BaseModel):
        model_config = ConfigDict(extra="forbid")
        items: List[ItemDefinition] = Field(
            description="List of item definitions generated by the AI."
        )

    _Container.__name__ = f"LLMSchema_{type_label}"
    _Container.__qualname__ = _Container.__name__

    return _Container