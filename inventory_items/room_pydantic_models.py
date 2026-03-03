# pydantic_models.py
from typing import List, Optional, Union, Dict, Any, Literal, Annotated, Type
from pydantic import BaseModel, Field, ConfigDict, PositiveInt, model_validator, create_model
from pydantic.functional_validators import AfterValidator

# =============================================================================
# CONSTANTS
# Lists used throughout the project for item/room type validation and prompting.
# =============================================================================

room_types = [
    "planting_garden", "library", "bedroom", "living_room", "bathroom",
    "garden", "white_room", "kitchen", "ALIFE_research", "computer_room", "outdoors_view"
]  # This is affecting room generator

lighthouse_room_types = ["lantern_room", "lighthouse_gallery", "accessible_light_viewing_room"]
room_types.extend(lighthouse_room_types)


# =============================================================================
# ROOM SHARED SUB-MODELS
# Parallel to the item SHARED SUB-MODELS section above.
# Named nested types used by room field contract mixins. Being explicit named
# BaseModel subclasses (rather than plain Dict/List annotations) means:
#   - The LLM receives a documented, named structure instead of an opaque dict.
#   - _make_strict() in ai_schema_builder.py rebuilds them correctly for
#     OpenAI strict mode when build_room_llm_schema_for_types() is called.
#   - Validation catches wrong shapes (e.g. {"morning": "not a list"}).
# =============================================================================

class RoomTimeDescriptions(BaseModel):
    """
    Time-of-day keyed description strings for a room.
    The runtime picks one string at random from the list for the current time.
    """
    model_config = ConfigDict(extra="allow")

    # Explicitly defined keys to guide the LLM and ensure validation
    early_morning: List[str] = Field(default_factory=list)
    morning: List[str] = Field(default_factory=list)
    noon: List[str] = Field(default_factory=list)
    afternoon: List[str] = Field(default_factory=list)
    late_afternoon: List[str] = Field(default_factory=list)
    night: List[str] = Field(default_factory=list)
    late_night: List[str] = Field(default_factory=list)

    # No explicit fields — all entries are captured by extra="allow".
    # The type annotation on BaseRoom.descriptions enforces Dict[str, List[str]]
    # at the BaseRoom level, which is where the shape contract lives.


# =============================================================================
# BASE ROOM
# Every room — regardless of room_type — must satisfy this contract.
# extra="allow" is required so that multi-type rooms carrying fields from
# multiple ROOM_TYPE_FIELD_CONTRACTS mixins don't fail on the extra keys.
#
# Mirrors BaseItem in philosophy:
#   - Required fields (name, descriptions, image, room_types) have no defaults.
#   - Optional fields (music) default to None.
#   - A model_validator enforces cross-field rules.
#
# Note on 'items': typed as List[Any] because item dicts are validated
# separately by validate_item_dict — Pydantic does not re-validate them here.
# =============================================================================

class BaseRoom(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(
        description="Human-readable room name, e.g. 'Garden'."
    )
    descriptions: Dict[str, List[str]] = Field(
        description=(
            "Time-of-day keyed description strings. Keys are time tags "
            "(e.g. 'morning', 'noon', 'late night'). Values are lists of "
            "strings the runtime selects from. "
            "See RoomTimeDescriptions for the expected key vocabulary."
        )
    )
    image: str = Field(
        description="Background image filename without extension, e.g. 'garden'."
    )
    music: Optional[str] = Field(
        default=None,
        description="Background music filename without extension, or None for silence."
    )
    room_types: List[str] = Field(
        description=(
            f"One or more room type tags. "
            f"Available types: {', '.join(room_types)}."
        )
    )
    items: List[Any] = Field(
        default_factory=list,
        description=(
            "Items currently present in this room. "
            "Each entry must independently pass validate_item_dict."
        )
    )

    @model_validator(mode="after")
    def check_room_types_are_known(self) -> "BaseRoom":
        unknown = [t for t in self.room_types if t not in room_types]
        if unknown:
            raise ValueError(
                f"Unknown room_type(s): {unknown}. "
                f"Known types: {room_types}."
            )
        return self


# =============================================================================
# ROOM FIELD CONTRACT MIXINS
# One class per room_type that introduces required or type-specific fields.
# Rules — identical to item mixin rules:
#   - Always set model_config = ConfigDict(extra="allow").
#   - Required fields have no default; optional fields default to None.
#   - Write clear Field(description=...) strings.
#
# To add a new room type with specific fields:
#   1. Write class MyRoomTypeFields(BaseModel) here.
#   2. Add an entry to ROOM_TYPE_FIELD_CONTRACTS below.
#   validate_room_dict and build_room_llm_schema automatically pick it up.
# =============================================================================

class PlantingGardenFields(BaseModel):
    model_config = ConfigDict(extra="allow")
    plot_number: int = Field(
        description="Number of planting plots available in this garden room."
    )


# =============================================================================
# ROOM_TYPE_FIELD_CONTRACTS REGISTRY
# Maps room_type strings to the mixin that defines their required fields.
# Room types absent from this dict (library, bedroom, living_room, etc.)
# have no extra field requirements beyond BaseRoom — they pass through
# validate_room_dict without a per-type check, same as misc/furniture items.
# =============================================================================

ROOM_TYPE_FIELD_CONTRACTS: Dict[str, Type[BaseModel]] = {
    "planting_garden": PlantingGardenFields,
}


# =============================================================================
# ROOM VALIDATION FUNCTION
# Single entry point for all room validation — parallel to validate_item_dict.
# Replaces the ~60-line manual imperative loop in StateStore._post_init_state_validation.
#
# Returns (data, None) on success, (None, error_string) on failure.
# Never mutates the input dict.
# Base contract failures are fatal and short-circuit per-type checks.
# All per-type errors are collected before returning.
# =============================================================================

def validate_room_dict(data: dict, check_id: bool = False) -> tuple[dict | None, str | None]:
    """
    Validates a room dictionary against BaseRoom and all registered type contracts.

    Args:
        data:     The raw room dict to validate.
        check_id: If True, also verifies that data["id"] is an integer.
                  Pass True for rooms already in saved state; False for templates.

    Returns:
        (data, None)         — valid room, original dict returned unchanged.
        (None, error_string) — invalid room, human-readable reason.
    """
    errors = []

    # --- Optional ID check (for existing rooms, not templates) ---
    if check_id:
        if not isinstance(data.get("id"), int):
            return None, f"Missing or invalid 'id' (must be int), got: {data.get('id')!r}"

    # --- Base contract (fatal if it fails) ---
    try:
        BaseRoom.model_validate(data)
    except Exception as e:
        return None, f"Base room contract failed: {e}"

    # --- Per-type contracts (all collected before returning) ---
    for type_str in data.get("room_types", []):
        contract = ROOM_TYPE_FIELD_CONTRACTS.get(type_str)
        if contract is None:
            continue  # no extra fields required for this room type
        try:
            contract.model_validate(data)
        except Exception as e:
            errors.append(f'"{type_str}" room contract failed: {e}')

    if errors:
        return None, "; ".join(errors)

    return data, None


# =============================================================================
# ROOM LLM SCHEMA BUILDER
# Parallel to build_llm_schema() for items.
# Dynamically constructs a flat Pydantic model for LLM structured output,
# scoped to only the room types you actually need.
#
# Intended to be called from ai_schema_builder.py via
# build_room_llm_schema_for_types(). Called once and cached there.
# =============================================================================

def build_room_llm_schema(room_type_filter: List[str] | None = None) -> Type[BaseModel]:
    """
    Builds and returns a RoomDefinition model for LLM structured output.

    BaseRoom fields remain required. All type-specific fields from
    ROOM_TYPE_FIELD_CONTRACTS are made Optional with None defaults.
    Field descriptions are auto-enriched with "Required when room_types
    includes 'X'" notes.

    Args:
        room_type_filter: If provided, only include contracts for these room
                          types. If None, include all registered contracts.
                          Unknown type strings are silently ignored.

    Returns:
        A Pydantic model class (RoomDefinition or RoomDefinition_<types>).
    """
    fields: Dict[str, Any] = {}
    seen: set = set()

    contracts_to_include = (
        {t: ROOM_TYPE_FIELD_CONTRACTS[t]
         for t in room_type_filter
         if t in ROOM_TYPE_FIELD_CONTRACTS}
        if room_type_filter is not None
        else ROOM_TYPE_FIELD_CONTRACTS
    )

    field_to_types: Dict[str, List[str]] = {}
    for type_str, contract_class in contracts_to_include.items():
        for field_name in contract_class.model_fields:
            field_to_types.setdefault(field_name, []).append(type_str)

    for type_str, contract_class in contracts_to_include.items():
        for field_name, field_info in contract_class.model_fields.items():
            if field_name in seen:
                continue
            seen.add(field_name)

            annotation = field_info.annotation

            # Wrap in Optional if not already
            is_already_optional = (
                hasattr(annotation, "__origin__")
                and type(None) in getattr(annotation, "__args__", ())
            )
            optional_annotation = annotation if is_already_optional else Optional[annotation]

            required_types = field_to_types.get(field_name, [type_str])
            if len(required_types) == 1:
                requirement_note = f"Required when room_types includes '{required_types[0]}'."
            else:
                quoted = ', '.join(f"'{t}'" for t in required_types)
                requirement_note = f"Required when room_types includes any of: {quoted}."

            original_desc = field_info.description or ""
            full_description = f"{requirement_note} {original_desc}".strip()

            fields[field_name] = (
                optional_annotation,
                Field(default=None, description=full_description)
            )

    model_name = (
        "RoomDefinition_" + "_".join(sorted(room_type_filter))
        if room_type_filter
        else "RoomDefinition"
    )

    return create_model(
        model_name,
        __base__=BaseRoom,
        **fields
    )


# Generated once at import time — the all-types variant for general use.
RoomDefinition = build_room_llm_schema()


class RoomDefinitionListContainer(BaseModel):
    """Container for LLM structured output for room generation.
    Pass this as the `structure` argument to your AI client's structured_output method."""
    rooms: List[RoomDefinition] = Field(
        description="List of room definitions generated by the AI."
    )