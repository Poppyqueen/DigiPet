# ai_schema_builder.py
#
# Single source of truth for LLM structured-output schema construction.
#
# Public API:
#
#   build_llm_schema(base, contracts, types, model_name)
#       Builds a flat Pydantic model from a base class + a subset of contract
#       mixins. Used for both items and rooms. Returns the definition model
#       (not a container — callers wrap it themselves if needed).
#
#   build_llm_schema_for_types(types)
#       Convenience wrapper for items. Returns a container model with an
#       `items` field, scoped to the given item types.
#
#   build_room_llm_schema_for_types(room_types)
#       Convenience wrapper for rooms. Returns a container model with a
#       `rooms` field, scoped to the given room types.
#
# OpenAI structured output compatibility:
#   All mixin fields are required (no defaults, no Optional wrapping).
#   The generated definition model uses extra="forbid" throughout.
#   This satisfies the additionalProperties: false + fully-populated
#   required array constraints imposed by OpenAI structured output.

from typing import List, Dict, Any, Type
from pydantic import BaseModel, Field, ConfigDict, create_model

from .contract_mixin import ContractMixin
from pydantic_core import PydanticUndefined


# =============================================================================
# CORE BUILDER
# =============================================================================

def build_llm_schema(
    base: Type[BaseModel],
    contracts: Dict[str, Type[ContractMixin]],
    types: List[str],
    model_name: str,
    type_field_name: str = "type",

) -> Type[BaseModel]:
    """
    Builds a flat Pydantic model for LLM structured output.

    Takes the required fields from `base` unchanged. For each type in `types`
    that has an entry in `contracts`, its mixin fields are added as required
    with their original descriptions.

    Args:
        base:       The base model class (BaseItem or BaseRoom).
        contracts:  The full registry dict (TYPE_FIELD_CONTRACTS or ROOM_TYPE_FIELD_CONTRACTS).
        types:      The subset of type strings to include fields for.
        model_name: The __name__ of the generated model class.

    Returns:
        A Pydantic model class inheriting from `base`, with extra="forbid",
        suitable for passing directly to OpenAI structured output.
    """
    relevant_contracts = {t: contracts[t] for t in types if t in contracts}

    # Collect model_description from each contract mixin that defines one.
    # Injected into the model's __doc__, giving the LLM semantic context
    # about what each type means.
    type_context_lines = []
    for type_str, contract_class in relevant_contracts.items():
        desc = getattr(contract_class, "model_description", None)
        if desc:
            type_context_lines.append(f"'{type_str}': {desc}")

    seen: set = set()
    fields: Dict[str, Any] = {}

    for type_str, contract_class in relevant_contracts.items():
        for field_name, field_info in contract_class.model_fields.items():
            if field_name in seen:
                continue
            seen.add(field_name)

            # Preserve default or default_factory so OpenAI doesn't demand these fields
            kwargs = {"description": field_info.description}
            if field_info.default is not PydanticUndefined:
                kwargs["default"] = field_info.default
            elif field_info.default_factory is not None:
                kwargs["default_factory"] = field_info.default_factory

            fields[field_name] = (
                field_info.annotation,
                Field(**kwargs),
            )

    # Narrow the 'type' field to only the requested types.
    if types:
        from typing import Literal
        NarrowedType = Literal[tuple(types)]  # type: ignore[valid-type]
        fields[type_field_name] = (
            List[NarrowedType],
            Field(description="One or more type tags. From valid literals.")
        )

    model = create_model(
        model_name,
        __base__=base,
        __config__=ConfigDict(extra="forbid"),
        **fields,
    )

    if type_context_lines:
        model.__doc__ = "Type context:\n" + "\n".join(type_context_lines)

    return model


# =============================================================================
# ITEM CONVENIENCE WRAPPER
# =============================================================================

def build_llm_schema_for_types(types: List[str]) -> Type[BaseModel]:
    """
    Builds a strict item container model scoped to the given item types.

    The returned model has a single `items: List[ItemDefinition]` field.
    Only fields relevant to the requested types are included, so the LLM
    is not distracted by irrelevant field definitions.

    Args:
        types: Item type strings, e.g. ["consumable"]. Types absent from
               TYPE_FIELD_CONTRACTS are silently ignored.

    Returns:
        A container model class with extra="forbid", ready for OpenAI structured output.
    """
    from .item_pydantic_models import BaseItem, TYPE_FIELD_CONTRACTS  # local import avoids circular

    type_label = "_".join(sorted(types)) if types else "base"
    ItemDefinition = build_llm_schema(
        base=BaseItem,
        contracts=TYPE_FIELD_CONTRACTS,
        types=types,
        model_name=f"ItemDefinition_{type_label}"

    )

    class _Container(BaseModel):
        model_config = ConfigDict(extra="forbid")
        items: List[ItemDefinition] = Field(  # type: ignore[valid-type]
            description="List of item definitions generated by the AI."
        )

    _Container.__name__ = f"LLMSchema_{type_label}"
    _Container.__qualname__ = _Container.__name__
    return _Container


# =============================================================================
# ROOM CONVENIENCE WRAPPER
# =============================================================================

def build_room_llm_schema_for_types(room_types: List[str]) -> Type[BaseModel]:
    """
    Builds a strict room container model scoped to the given room types.

    The returned model has a single `rooms: List[RoomDefinition]` field.
    Passing an empty list or only contract-free types is valid — the schema
    will contain BaseRoom fields only.

    Args:
        room_types: Room type strings, e.g. ["planting_garden"]. Types absent
                    from ROOM_TYPE_FIELD_CONTRACTS are silently ignored.

    Returns:
        A container model class with extra="forbid", ready for OpenAI structured output.
    """
    from .room_pydantic_models import BaseRoom, ROOM_TYPE_FIELD_CONTRACTS  # local import avoids circular

    type_label = "_".join(sorted(room_types)) if room_types else "base"
    RoomDefinition = build_llm_schema(
        base=BaseRoom,
        contracts=ROOM_TYPE_FIELD_CONTRACTS,
        types=room_types,
        model_name=f"RoomDefinition_{type_label}",
        type_field_name="room_types",

    )

    class _Container(BaseModel):
        model_config = ConfigDict(extra="forbid")
        rooms: List[RoomDefinition] = Field(  # type: ignore[valid-type]
            description="List of room definitions generated by the AI."
        )

    _Container.__name__ = f"RoomLLMSchema_{type_label}"
    _Container.__qualname__ = _Container.__name__
    return _Container