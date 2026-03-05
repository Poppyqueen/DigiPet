# item_pydantic_models.py
from typing import List, Optional, Union, Dict, Any, Literal, Annotated, Type, get_args
from pydantic import BaseModel, Field, ConfigDict, PositiveInt, model_validator, create_model
from pydantic.functional_validators import AfterValidator

from tools.tools_folder.tools_helpers.tv_utils.tv_channels_definitions import TV_TYPE_CHANNELS


# TODO: Register lighthouse items that require mixins
# =============================================================================
# CONSTANTS
# Lists used throughout the project for item/room type validation and prompting.
# =============================================================================

valid_plants = [
    'lettuce', 'carrot', 'cactus', 'tomato', 'potato',
    'strawberry', 'rose', 'sunflower', 'mint', 'basil'
]  # Edit this to reflect the plants existing in the garden manager data structures.
   # tools/tools_folder/tools_data/harvesting_data.py

stringed_plant_types = ', '.join(f"'{p}'" for p in valid_plants)

toggable_items = ["tv", "bluesky_social", "iPod", "cellphone", "maze", "laptop", "desktop_computer"]

item_types = ["consumable", "misc", "furniture", "seed", "seat", "art_book", "bed", "pillow", "book", "dispenser", "candy_bag", "toggle_item_power"]
item_types.extend(toggable_items)

lighthouse_items = [
    "iov_pressure_system", "kerosene_container", "iov_spirit_pan", "hand_fire_source",
    "iov_lamp_top", "spirit_source", "iov_mantle", "clockwork_lens_apparatus",
    "sheet", "cleaning_rag", "fresnel_lens", "oiler_set"
]
item_types.extend(lighthouse_items)


#ignore_fingerprint_keys = ["id", "quantity", "static", "stats_edit", "effects"] # This is what I had before
ignore_fingerprint_keys = ["id", "quantity", "static"]


# TODO: Check if any of the item types have particular keys that need mixins definitions, I think not, but I'm not sure.

# Build a Literal type from the dict keys at import time
_tv_type_keys = tuple(TV_TYPE_CHANNELS.keys())
TVType = Literal[_tv_type_keys]  # type: ignore[valid-type]

tv_type_names = ", ".join(_tv_type_keys)
# =============================================================================
# PLANT VALIDATOR
# ValidPlantType is an Annotated str that raises a clear error for unknown plants.
# Derive from valid_plants so there's only one place to maintain the list.
# =============================================================================

def _check_plant(v: str) -> str:
    if v not in valid_plants:
        raise ValueError(f"plant_type must be one of {valid_plants}, got '{v}'")
    return v

ValidPlantType = Annotated[str, AfterValidator(_check_plant)]


# =============================================================================
# SHARED SUB-MODELS
# Small reusable models referenced by field contract mixins.
# =============================================================================

class BookChapter(BaseModel):
    """A single chapter inside a book item."""
    title: str
    content: str
    is_locked: bool = Field(default=True, description="Whether the chapter is locked.")


class ItemStatsEdit(BaseModel):
    """Stat deltas applied when a consumable item is used."""
    fullness: float = Field(description="Change to fullness stat. Negative values allowed for harmful or other hunger causing items.")
    hydration: float = Field(description="Change to hydration stat. Negative values allowed for harmful or other thrist causing items.")
    energy: float = Field(description="Change to energy stat. Negative values allowed for harmful or other energy reducing items.")

class DispenserState(BaseModel):
    model_config = ConfigDict(extra="allow")  # keep allow for runtime
    contents: Dict[str, int] = Field(default_factory=dict, description="Maps existing item names to remaining quantities.")

# =============================================================================
# BASE ITEM
# Every item — regardless of type — must satisfy this contract.
# extra="allow" is required so that multi-type items carrying fields from
# multiple contracts don't fail base validation on the extra keys.
# =============================================================================

class BaseItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(description="Human-readable item name, e.g. 'Bowl of Nuts'.")
    descriptions: List[str] = Field(description="One or more description strings shown to the player.")
    static: bool = Field(description="True if the item cannot be picked up or moved (e.g. furniture).")
    type: List[str] = Field(description=f"One or more type tags. Available types: {', '.join(item_types)}.")
    stackable: bool = Field(default=False, description="True for small non-unique items that can stack (seeds, coins). False for large/unique items.")
    quantity: PositiveInt = Field(default=1, description="How many units are in this stack. Must be 1 for non-stackable items.")
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
# One class per item type that introduces required or type-specific fields.
# Rules:
#   - Always set model_config = ConfigDict(extra="allow") so that a multi-type
#     item's full dict doesn't fail when validated against a single contract.
#   - Required fields have no default; optional fields default to None.
#   - Write clear Field(description=...) strings — build_llm_schema() appends
#     "Required when type includes 'X'" automatically, so keep these concise.
#
# To add a new type:
#   1. Write class MyNewTypeFields(BaseModel) with its fields here.
#   2. Add an entry to TYPE_FIELD_CONTRACTS below.
#   That's it. validate_item_dict and the LLM schema update automatically.
# =============================================================================

class ConsumableFields(BaseModel):
    model_config = ConfigDict(extra="allow")
    stats_edit: ItemStatsEdit = Field(description="Stat changes applied on consumption. Can be negative or possitive for realistic effects.")
    effects: Optional[List[str]] = Field(default=None, description="Narrative effect strings shown to the player on consumption.")
    consume_uses_left: Optional[PositiveInt] = Field(default=None, description="Remaining uses for multi-use consumables (jars, bags, large bowls, meals, packages, some fruits, etc). Single-use items omit this.")


class SeedFields(BaseModel):
    model_config = ConfigDict(extra="allow")
    plant_type: ValidPlantType = Field(description=f"The plant this seed grows. One of: {stringed_plant_types}.")


class BookFields(BaseModel):
    model_config = ConfigDict(extra="allow")
    chapters: List[BookChapter] = Field(default_factory=list, description="Ordered list of chapters in this book.")
    is_locked: bool = Field(default=False, description="True if the book cannot be written to.")


class DispenserFields(BaseModel):
    model_config = ConfigDict(extra="allow")
    dispenser_state: DispenserState = Field(description="Internal state of the dispenser.")


class CandyBagFields(BaseModel):
    model_config = ConfigDict(extra="allow")
    contents: Dict[str, PositiveInt] = Field(description="Maps contained item names to their quantities.")


class ToggableFields(BaseModel):
    model_config = ConfigDict(extra="allow")
    power_toggle: Optional[bool] = Field(default=None, description="Current power state. True = on, False = off.")



class TVFields(BaseModel):
    model_config = ConfigDict(extra="allow")
    tv_type: Optional[TVType] = Field(default=None, description=f"The type of TV, any from: {tv_type_names}. Default is null.")
    current_channel: Optional[str] = Field(default=None, description=f"The currently airing channel, any from: {tv_type_names}. Initialize to null and let the tool handle it.")
# Lighthouse items

class LighthouseSpiritPanFields(BaseModel):
    model_config = ConfigDict(extra="allow")
    filled: bool = Field(description="Whether the spirit pan is filled with spirit.")

class LighthouseSpiritSourceFields(BaseModel):
    model_config = ConfigDict(extra="allow")
    spirit_quantity: float = Field(description="The amount of spirit in the source. Float from 0.0 to 1.0.")

# =============================================================================
# TYPE_FIELD_CONTRACTS REGISTRY
# Maps each type string to the mixin that defines its required fields.
# Types absent from this dict (misc, furniture, seat, bed, pillow, art_book,
# and all lighthouse items for now) have no extra field requirements beyond
# BaseItem — they simply pass through validate_item_dict without a per-type check.
#
# Lighthouse items with specific fields: add a new mixin above, then register it here.
# =============================================================================

TYPE_FIELD_CONTRACTS: Dict[str, Type[BaseModel]] = {
    "consumable": ConsumableFields,
    "seed":        SeedFields,
    "book":        BookFields,
    "dispenser":   DispenserFields,
    "candy_bag":   CandyBagFields,
    "iov_spirit_pan":  LighthouseSpiritPanFields,
    "spirit_source": LighthouseSpiritSourceFields,
    "toggle_item_power": ToggableFields,
    "tv":          TVFields,
}


# =============================================================================
# CORE VALIDATION FUNCTION
# Single entry point for all item validation — replaces _is_valid_item_data
# in InventoryService and the inline stub in StateStore.
#
# Returns (data, None) on success, (None, error_string) on failure.
# Never mutates the input dict.
# Base contract failures are fatal and short-circuit per-type checks.
# All per-type errors are collected before returning so multi-type items
# (e.g. ["seed", "consumable"]) report all problems at once.
# =============================================================================

def validate_item_dict(data: dict, check_id: bool = False) -> tuple[dict | None, str | None]:
    """
    Validates an item dictionary against BaseItem and all registered type contracts.

    Args:
        data:     The raw item dict to validate.
        check_id: If True, also verifies that data["id"] is an integer.

    Returns:
        (data, None)         — valid item, original dict returned unchanged.
        (None, error_string) — invalid item, human-readable reason.
    """
    errors = []

    # --- Optional ID check (for existing items, not templates) ---
    if check_id:
        if not isinstance(data.get("id"), int):
            return None, f"Missing or invalid 'id' (must be int), got: {data.get('id')!r}"

    # --- Base contract (fatal if it fails) ---
    try:
        BaseItem.model_validate(data)
    except Exception as e:
        return None, f"Base contract failed: {e}"

    # --- Per-type contracts (all collected before returning) ---
    type_list = data.get("type", [])
    for type_str in type_list:
        contract = TYPE_FIELD_CONTRACTS.get(type_str)
        if contract is None:
            continue  # no extra fields required for this type
        try:
            contract.model_validate(data)
        except Exception as e:
            errors.append(f'"{type_str}" contract failed: {e}')

    if errors:
        return None, "; ".join(errors)

    return data, None


# =============================================================================
# LLM SCHEMA BUILDER
# Dynamically constructs a flat Pydantic model suitable for LLM structured
# output by collecting fields from BaseItem (required) and every registered
# mixin (made Optional).
#
# Field descriptions are auto-enriched with "Required when type includes 'X'"
# so the LLM understands conditionality without manual maintenance.
#
# Called once at module level to produce ItemDefinition and
# ItemDefinitionListContainer. When you add a new mixin + registry entry,
# the LLM schema updates automatically — no manual changes needed here.
# =============================================================================

def build_llm_schema() -> Type[BaseModel]:
    """
    Builds and returns an ItemDefinition model for LLM structured output.
    All type-specific fields are Optional with None defaults.
    Base fields (name, descriptions, static, type, stackable, quantity) remain required.
    """
    fields: Dict[str, Any] = {}

    seen: set = set()

    field_to_types: Dict[str, List[str]] = {}
    for type_str, contract_class in TYPE_FIELD_CONTRACTS.items():
        for field_name in contract_class.model_fields:
            field_to_types.setdefault(field_name, []).append(type_str)

    for type_str, contract_class in TYPE_FIELD_CONTRACTS.items():
        for field_name, field_info in contract_class.model_fields.items():
            if field_name in seen:
                continue
            seen.add(field_name)

            annotation = field_info.annotation

            if not (hasattr(annotation, "__origin__") and type(None) in getattr(annotation, "__args__", ())):
                optional_annotation = Optional[annotation]
            else:
                optional_annotation = annotation

            required_types = field_to_types.get(field_name, [type_str])
            if len(required_types) == 1:
                requirement_note = f"Required when type includes '{required_types[0]}'."
            else:
                quoted = ', '.join(f"'{t}'" for t in required_types)
                requirement_note = f"Required when type includes any of: {quoted}."

            original_desc = field_info.description or ""
            full_description = f"{requirement_note} {original_desc}".strip()

            fields[field_name] = (
                optional_annotation,
                Field(default=None, description=full_description)
            )

    return create_model(
        "ItemDefinition",
        __base__=BaseItem,
        **fields
    )


# Generated once at import time. Import ItemDefinition or ItemDefinitionListContainer
# from this module wherever LLM structured output is needed.
ItemDefinition = build_llm_schema()


class ItemDefinitionListContainer(BaseModel):
    """Container for LLM structured output. Pass this as the `structure` argument
    to your AI client's structured_output method."""
    items: List[ItemDefinition] = Field(description="List of item definitions generated by the AI.")