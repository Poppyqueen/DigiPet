# item_pydantic_models.py
#
# Defines the item contract system:
#   - BaseItem:              every item must satisfy this.
#   - ContractMixin subclasses: one per item type, declare required extra fields.
#   - TYPE_FIELD_CONTRACTS:  registry mapping type strings to their mixin.
#   - validate_item_dict:    single validation entry point.
#   - ItemDefinition / ItemDefinitionListContainer: LLM structured-output models,
#     built once at import time via ai_schema_builder.build_llm_schema().
#
# To add a new item type:
#   1. Write class MyTypeFields(ContractMixin) with its fields here.
#   2. Add an entry to TYPE_FIELD_CONTRACTS.
#   That's it — validate_item_dict and the LLM schema update automatically.

from typing import List, Optional, Union, Dict, Any, Literal, Annotated, Type
from pydantic import BaseModel, Field, ConfigDict, PositiveInt, model_validator, create_model
from pydantic.functional_validators import AfterValidator

from .contract_mixin import ContractMixin
from tools.tools_folder.tools_helpers.tv_utils.tv_channels_definitions import TV_TYPE_CHANNELS
from tools.tools_folder.tools_data.harvesting_data import plant_types


# =============================================================================
# CONSTANTS
# =============================================================================

toggable_items = ["tv", "bluesky_social", "iPod", "cellphone", "maze", "laptop", "desktop_computer"]

item_types = ["consumable", "misc", "furniture", "seed", "seat", "art_book", "bed", "pillow", "book", "dispenser", "candy_bag", "toggle_item_power"]
item_types.extend(toggable_items)

lighthouse_items = [
    "iov_pressure_system", "kerosene_container", "iov_spirit_pan", "hand_fire_source",
    "iov_lamp_top", "spirit_source", "iov_mantle", "clockwork_lens_apparatus",
    "sheet", "cleaning_rag", "fresnel_lens", "oiler_set"
]
item_types.extend(lighthouse_items)

ignore_fingerprint_keys = ["id", "quantity", "static"]


# =============================================================================
# TV REGISTRY
# =============================================================================

_tv_type_keys = tuple(TV_TYPE_CHANNELS.keys())
TVType = Literal[_tv_type_keys]  # type: ignore[valid-type]
tv_type_names = ", ".join(_tv_type_keys)


# =============================================================================
# PLANT REGISTRY
# =============================================================================

_plant_type_keys = tuple(plant_types.keys())
PlantType = Literal[_plant_type_keys]        # type: ignore[valid-type]
plant_type_names = ", ".join(_plant_type_keys)

# =============================================================================
# SHARED SUB-MODELS
# Named nested types used by mixins. Being explicit BaseModel subclasses means
# the LLM receives a documented, named structure rather than an opaque dict,
# and validation catches wrong shapes early.
# =============================================================================

class BookChapter(BaseModel):
    """A single chapter inside a book item."""
    title: str
    content: str
    is_locked: bool = Field(default=True, description="Whether the chapter is locked.")


class ItemStatsEdit(BaseModel):
    """Stat deltas applied when a consumable item is used."""
    fullness: float = Field(description="Change to fullness stat. Negative values allowed.")
    hydration: float = Field(description="Change to hydration stat. Negative values allowed.")
    energy: float = Field(description="Change to energy stat. Negative values allowed.")


class DispenserState(BaseModel):
    model_config = ConfigDict(extra="forbid")  # was extra="allow"
    contents: Dict[str, int] = Field(
        default_factory=dict,
        description="Maps existing item names to remaining quantities."
    )


class TVState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tv_type: TVType = Field(
        default=_tv_type_keys[0],
        description=f"The type of TV. One of: {tv_type_names}."
    )
    current_channel: Optional[str] = Field(
        default=None,
        description=f"Currently airing channel. Starts as None, managed by the TV tool."
    )



# =============================================================================
# BASE ITEM
# Every item must satisfy this contract.
# extra="allow" is intentional: a multi-type item carries fields from several
# mixins; validating each mixin individually against the full dict requires
# the base to not reject unknown keys.
# =============================================================================

class BaseItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(description="Human-readable item name, e.g. 'Bowl of Nuts'.")
    descriptions: List[str] = Field(description="One or more description strings shown to the player.")
    static: bool = Field(description="True if the item cannot be picked up or moved.")
    type: List[str] = Field(description=f"One or more type tags. Available types: {', '.join(item_types)}.")
    stackable: bool = Field(default=False, description="True for small non-unique items that can stack.")
    quantity: PositiveInt = Field(default=1, description="How many units are in this stack. Default to 1.")
    max_stack_size: Optional[PositiveInt] = Field(default=None, description="Maximum units per stack. None means unlimited.")

    @model_validator(mode="after")
    def check_stacking_consistency(self) -> "BaseItem":
        if not self.stackable:
            if self.quantity > 1:
                raise ValueError("Non-stackable item cannot have quantity > 1")
            if self.max_stack_size is not None and self.max_stack_size > 1:
                raise ValueError("Non-stackable item cannot have max_stack_size > 1")
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

class ConsumableFields(ContractMixin):
    stats_edit: ItemStatsEdit = Field(
        description="Stat changes applied on consumption. Negative values allowed for harmful items."
    )
    effects: List[str] = Field(
        description="Narrative effect strings shown to the player on consumption."
    )
    consume_uses_left: PositiveInt = Field(
        description=(
            "Remaining uses for multi-use consumables (jars, bags, large bowls, etc). "
            "Set to 1 for single-use items."
        )
    )


class SeedFields(ContractMixin):
    plant_type: PlantType = Field(
        description=f"The plant this seed grows. One of: {plant_type_names}."
    )


class BookFields(ContractMixin):
    chapters: List[BookChapter] = Field(
        description="Ordered list of chapters in this book."
    )
    is_locked: bool = Field(
        description="True if the book cannot be written to."
    )


class DispenserFields(ContractMixin):
    dispenser_state: DispenserState = Field(
        description="Internal state of the dispenser, including remaining contents."
    )


class CandyBagFields(ContractMixin):
    contents: Dict[str, PositiveInt] = Field(
        description="Maps contained item names to their quantities."
    )


class ToggableFields(ContractMixin):
    power_toggle: bool = Field(
        description="Current power state. True = on, False = off."
    )



class TVFields(ContractMixin):
    tv_state: TVState = Field(description="Runtime state of the TV, managed by the TV tool.")


# Lighthouse mixins

class LighthouseSpiritPanFields(ContractMixin):
    filled: bool = Field(
        description="Whether the spirit pan is filled with spirit."
    )


class LighthouseSpiritSourceFields(ContractMixin):
    spirit_quantity: float = Field(
        description="Amount of spirit in the source. Float from 0.0 to 1.0."
    )


# =============================================================================
# TYPE_FIELD_CONTRACTS REGISTRY
#
# Maps each type string to its ContractMixin subclass.
# Types absent from this dict (misc, furniture, seat, bed, pillow, art_book,
# and lighthouse items without specific fields) require no extra fields beyond
# BaseItem and pass through validate_item_dict without a per-type check.
# =============================================================================

TYPE_FIELD_CONTRACTS: Dict[str, Type[ContractMixin]] = {
    "consumable":        ConsumableFields,
    "seed":              SeedFields,
    "book":              BookFields,
    "dispenser":         DispenserFields,
    "candy_bag":         CandyBagFields,
    "toggle_item_power": ToggableFields,
    "tv":                TVFields,
    "iov_spirit_pan":    LighthouseSpiritPanFields,
    "spirit_source":     LighthouseSpiritSourceFields,
}


# =============================================================================
# VALIDATION
# =============================================================================

def validate_item_dict(data: dict, check_id: bool = False) -> tuple[dict | None, str | None]:
    """
    Validates an item dictionary against BaseItem and all registered type contracts.

    Args:
        data:     The raw item dict to validate.
        check_id: If True, also verifies that data["id"] is an integer.
                  Pass True for items already in saved state; False for templates.

    Returns:
        (data, None)         — valid item, original dict returned unchanged.
        (None, error_string) — invalid item, human-readable reason.
    """
    if check_id:
        if not isinstance(data.get("id"), int):
            return None, f"Missing or invalid 'id' (must be int), got: {data.get('id')!r}"

    try:
        BaseItem.model_validate(data)
    except Exception as e:
        return None, f"Base contract failed: {e}"

    errors = []
    for type_str in data.get("type", []):
        contract = TYPE_FIELD_CONTRACTS.get(type_str)
        if contract is None:
            continue
        try:
            contract.model_validate(
                {k: data[k] for k in contract.model_fields if k in data}
            )
        except Exception as e:
            errors.append(f'"{type_str}" contract failed: {e}')

    if errors:
        return None, "; ".join(errors)

    return data, None


# =============================================================================
# LLM SCHEMA — built once at import time via the shared builder in
# ai_schema_builder.py, which owns all schema construction logic.
# =============================================================================

from inventory_items.items_validation.ai_schema_builder import build_llm_schema  # noqa: E402 (import after contracts defined)

ItemDefinition = build_llm_schema(
    base=BaseItem,
    contracts=TYPE_FIELD_CONTRACTS,
    types=list(TYPE_FIELD_CONTRACTS.keys()),
    model_name="ItemDefinition",
)


class ItemDefinitionListContainer(BaseModel):
    """Container for LLM structured output. Pass as the `structure` argument
    to your AI client's structured_output method."""
    items: List[ItemDefinition] = Field(  # type: ignore[valid-type]
        description="List of item definitions generated by the AI."
    )