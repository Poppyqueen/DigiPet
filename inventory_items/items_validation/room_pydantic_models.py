# room_pydantic_models.py
#
# Defines the room contract system:
#   - BaseRoom:              every room must satisfy this.
#   - ContractMixin subclasses: one per room type, declare required extra fields.
#   - ROOM_TYPE_FIELD_CONTRACTS: registry mapping type strings to their mixin.
#   - validate_room_dict:    single validation entry point.
#   - RoomDefinition / RoomDefinitionListContainer: LLM structured-output models,
#     built once at import time via ai_schema_builder.build_llm_schema().
#
# To add a new room type:
#   1. Write class MyRoomTypeFields(ContractMixin) with its fields here.
#   2. Add an entry to ROOM_TYPE_FIELD_CONTRACTS.
#   That's it — validate_room_dict and the LLM schema update automatically.

from typing import List, Optional, Dict, Any, Type
from pydantic import BaseModel, Field, ConfigDict, model_validator

from .contract_mixin import ContractMixin


# =============================================================================
# CONSTANTS
# =============================================================================

room_types = [
    "planting_garden", "library", "bedroom", "living_room", "bathroom",
    "garden", "white_room", "kitchen", "ALIFE_research", "computer_room", "outdoors_view"
]

lighthouse_room_types = ["lantern_room", "lighthouse_gallery", "accessible_light_viewing_room"]
room_types.extend(lighthouse_room_types)


# =============================================================================
# SHARED SUB-MODELS
# =============================================================================


class RoomTimeDescriptions(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    early_morning: List[str] = Field(alias="early morning", description="Descriptions shown during early morning.")
    morning: List[str] = Field(description="Descriptions shown during morning.")
    noon: List[str] = Field(description="Descriptions shown at noon.")
    afternoon: List[str] = Field(description="Descriptions shown during afternoon.")
    late_afternoon: List[str] = Field(alias="late afternoon", description="Descriptions shown during late afternoon.")
    night: List[str] = Field(description="Descriptions shown at night.")
    late_night: List[str] = Field(alias="late night", description="Descriptions shown during late night.")


# =============================================================================
# BASE ROOM
# Every room must satisfy this contract.
# extra="allow" is intentional: a multi-type room carries fields from several
# mixins; validating each mixin individually against the full dict requires
# the base to not reject unknown keys.
# =============================================================================

class BaseRoom(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(
        description="Human-readable room name, e.g. 'Garden'."
    )
    descriptions: RoomTimeDescriptions = Field(
        description="Time-of-day description strings. All 7 slots required, each with at least one string."
    )
    image: str = Field(
        description="Background image filename without extension, e.g. 'garden'."
    )
    music: Optional[str] = Field(
        default=None,
        description="Background music filename without extension, or None for silence."
    )
    room_types: List[str] = Field(
        description=f"One or more room type tags. Available types: {', '.join(room_types)}."
    )
    items: List[Any] = Field(
        default_factory=list,
        description="Items currently present in this room. Each entry must independently pass validate_item_dict."
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
# FIELD CONTRACT MIXINS
#
# Rules (enforced automatically by ContractMixin — violations = import error):
#   - Inherit from ContractMixin, not BaseModel.
#   - Do NOT set model_config. ContractMixin sets extra="forbid" for you.
#   - Every field must have Field(description=...).
#   - No field may be typed Any, object, or Optional.
#     Optional fields belong on the base model, not on mixins.
# =============================================================================

class PlantingGardenFields(ContractMixin):
    plot_number: int = Field(
        description="Number of planting plots available in this garden room."
    )


# =============================================================================
# ROOM_TYPE_FIELD_CONTRACTS REGISTRY
#
# Maps each room type string to its ContractMixin subclass.
# Room types absent from this dict (library, bedroom, living_room, etc.)
# require no extra fields beyond BaseRoom and pass through validate_room_dict
# without a per-type check.
# =============================================================================

ROOM_TYPE_FIELD_CONTRACTS: Dict[str, Type[ContractMixin]] = {
    "planting_garden": PlantingGardenFields,
}


# =============================================================================
# VALIDATION
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
    if check_id:
        if not isinstance(data.get("id"), int):
            return None, f"Missing or invalid 'id' (must be int), got: {data.get('id')!r}"

    try:
        BaseRoom.model_validate(data)
    except Exception as e:
        return None, f"Base room contract failed: {e}"

    errors = []
    for type_str in data.get("room_types", []):
        contract = ROOM_TYPE_FIELD_CONTRACTS.get(type_str)
        if contract is None:
            continue
        try:
            contract.model_validate(
                {k: data[k] for k in contract.model_fields if k in data}
            )
        except Exception as e:
            errors.append(f'"{type_str}" room contract failed: {e}')

    if errors:
        return None, "; ".join(errors)

    return data, None


# =============================================================================
# LLM SCHEMA — built once at import time via the shared builder in
# ai_schema_builder.py, which owns all schema construction logic.
# =============================================================================

from .ai_schema_builder import build_llm_schema  # noqa: E402 (import after contracts defined)

RoomDefinition = build_llm_schema(
    base=BaseRoom,
    contracts=ROOM_TYPE_FIELD_CONTRACTS,
    types=list(ROOM_TYPE_FIELD_CONTRACTS.keys()),
    model_name="RoomDefinition",
)


class RoomDefinitionListContainer(BaseModel):
    """Container for LLM structured output. Pass as the `structure` argument
    to your AI client's structured_output method."""
    rooms: List[RoomDefinition] = Field(  # type: ignore[valid-type]
        description="List of room definitions generated by the AI."
    )