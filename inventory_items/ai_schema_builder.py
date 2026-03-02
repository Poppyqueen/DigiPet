# ai_schema_builder.py
#
# Provides two public helpers:
#
#   build_llm_schema_for_types(types)
#       Constructs a strict item schema scoped to specific item types.
#
#   build_room_llm_schema_for_types(room_types)
#       Constructs a strict room schema scoped to specific room types.
#
# Both return a container model (items/rooms field) compatible with
# OpenAI structured output (extra="forbid" recursively applied).
#
# Usage examples:
#
#   from inventory_items.ai_schema_builder import build_llm_schema_for_types
#   CookSchema = build_llm_schema_for_types(["consumable"])
#
#   from inventory_items.ai_schema_builder import build_room_llm_schema_for_types
#   GardenRoomSchema = build_room_llm_schema_for_types(["planting_garden"])

from typing import List, Optional, Dict, Any, Type, get_args, get_origin
from pydantic import BaseModel, Field, ConfigDict, create_model

from inventory_items.item_pydantic_models import (
    BaseItem,
    TYPE_FIELD_CONTRACTS,
)
from inventory_items.room_pydantic_models import (
    BaseRoom,
    ROOM_TYPE_FIELD_CONTRACTS,
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
# ITEM SCHEMA BUILDER (unchanged from original)
# =============================================================================

def build_llm_schema_for_types(types: List[str]) -> Type[BaseModel]:
    """
    Builds a strict Pydantic container model for LLM structured output.
    
    If types are provided that exist in TYPE_FIELD_CONTRACTS, their specific 
    fields are added as Optional fields to the schema. If an empty list or 
    unrecognized types are provided, it returns a schema containing only 
    the fields defined in BaseItem.

    Args:
        types: List of item type strings, e.g. ["consumable"].
               Types absent from TYPE_FIELD_CONTRACTS are silently ignored 
               (they contribute no extra fields beyond BaseItem).

    Returns:
        A Pydantic model class with a single `items: List[ItemDefinition]` field,
        rebuilt with extra="forbid" for OpenAI strict mode compatibility.
    """
    strict_cache: Dict[type, type] = {}

    seen: set = set()
    fields: Dict[str, Any] = {}
    field_to_types: Dict[str, List[str]] = {}

    # Filter for contracts that actually exist
    relevant_contracts = {
        t: TYPE_FIELD_CONTRACTS[t] for t in types if t in TYPE_FIELD_CONTRACTS
    }

    # If relevant_contracts is empty, the following loops are simply skipped,
    # resulting in a schema that only uses BaseItem fields.

    for type_str, contract_class in relevant_contracts.items():
        for field_name in contract_class.model_fields:
            field_to_types.setdefault(field_name, []).append(type_str)

    for type_str, contract_class in relevant_contracts.items():
        for field_name, field_info in contract_class.model_fields.items():
            if field_name in seen:
                continue
            seen.add(field_name)

            strict_annotation = _make_strict(field_info.annotation, strict_cache)

            origin = get_origin(strict_annotation)
            args = get_args(strict_annotation)
            is_already_optional = origin is not None and type(None) in args
            optional_annotation = strict_annotation if is_already_optional else Optional[strict_annotation]

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

    # Use "base" label if no valid types were provided
    type_label = "_".join(sorted(types)) if types else "base"
    
    ItemDefinition = create_model(
        f"ItemDefinition_{type_label}",
        __base__=BaseItem,
        __config__=ConfigDict(extra="forbid"),
        **fields,
    )

    class _ItemContainer(BaseModel):
        model_config = ConfigDict(extra="forbid")
        items: List[ItemDefinition] = Field(
            description="List of item definitions generated by the AI."
        )

    _ItemContainer.__name__ = f"LLMSchema_{type_label}"
    _ItemContainer.__qualname__ = _ItemContainer.__name__
    return _ItemContainer


# =============================================================================
# ROOM SCHEMA BUILDER
# Parallel to build_llm_schema_for_types but for rooms.
# Uses BaseRoom + ROOM_TYPE_FIELD_CONTRACTS from pydantic_models.
#
# Unlike the item version, room_types can be empty — many room types (library,
# bedroom, etc.) have no registered contracts. In that case we still return a
# valid schema containing only BaseRoom fields, since that is legitimate
# (you want the LLM to generate a plain room with no type-specific extras).
# =============================================================================

def build_room_llm_schema_for_types(room_types: List[str]) -> Type[BaseModel]:
    """
    Builds a strict Pydantic container model for LLM structured room output,
    including only the fields relevant to the given room types.

    Args:
        room_types: List of room type strings, e.g. ["planting_garden"].
                    Types absent from ROOM_TYPE_FIELD_CONTRACTS are silently
                    ignored (they have no extra field requirements beyond BaseRoom).
                    Passing an empty list or only contract-free types is valid —
                    the resulting schema contains BaseRoom fields only.

    Returns:
        A Pydantic model class with a single `rooms: List[RoomDefinition]` field,
        where RoomDefinition contains BaseRoom fields + any requested type fields,
        all rebuilt with extra="forbid" for OpenAI strict mode compatibility.
    """
    strict_cache: Dict[type, type] = {}

    seen: set = set()
    fields: Dict[str, Any] = {}
    field_to_types: Dict[str, List[str]] = {}

    relevant_contracts = {
        t: ROOM_TYPE_FIELD_CONTRACTS[t]
        for t in room_types
        if t in ROOM_TYPE_FIELD_CONTRACTS
    }

    # Build field_to_types map for description annotation.
    for type_str, contract_class in relevant_contracts.items():
        for field_name in contract_class.model_fields:
            field_to_types.setdefault(field_name, []).append(type_str)

    for type_str, contract_class in relevant_contracts.items():
        for field_name, field_info in contract_class.model_fields.items():
            if field_name in seen:
                continue
            seen.add(field_name)

            strict_annotation = _make_strict(field_info.annotation, strict_cache)

            origin = get_origin(strict_annotation)
            args = get_args(strict_annotation)
            is_already_optional = origin is not None and type(None) in args
            optional_annotation = strict_annotation if is_already_optional else Optional[strict_annotation]

            required_types = field_to_types.get(field_name, [type_str])
            if len(required_types) == 1:
                requirement_note = f"Required when room_types includes '{required_types[0]}'."
            else:
                quoted = ", ".join(f"'{t}'" for t in required_types)
                requirement_note = f"Required when room_types includes any of: {quoted}."

            original_desc = field_info.description or ""
            full_description = f"{requirement_note} {original_desc}".strip()

            fields[field_name] = (
                optional_annotation,
                Field(default=None, description=full_description),
            )

    type_label = "_".join(sorted(room_types)) if room_types else "base"
    RoomDefinition = create_model(
        f"RoomDefinition_{type_label}",
        __base__=BaseRoom,
        __config__=ConfigDict(extra="forbid"),
        **fields,
    )

    class _RoomContainer(BaseModel):
        model_config = ConfigDict(extra="forbid")
        rooms: List[RoomDefinition] = Field(
            description="List of room definitions generated by the AI."
        )

    _RoomContainer.__name__ = f"RoomLLMSchema_{type_label}"
    _RoomContainer.__qualname__ = _RoomContainer.__name__
    return _RoomContainer