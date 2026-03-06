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

from inventory_items.items_provider.item_store import ItemStore

from typing import ClassVar

# =============================================================================
# CONSTANTS
# =============================================================================

item_store = ItemStore()

toggable_items = ["tv", "bluesky_social", "iPod", "cellphone", "maze", "laptop", "desktop_computer"]

item_types = ["consumable", "misc", "furniture", "seed", "seat", "art_book", "bed", "pillow", "book", "dispenser", "candy_bag", "toggle_item_power"]
item_types.extend(toggable_items)

refactored_types = ["fenestration_aperture", "bookmaking_implements", "meditation_aids"] # In process of refactoring tools and affordances, making them more general and modular.
item_types.extend(refactored_types)
item_types.extend(toggable_items)


lighthouse_items = [
    "iov_pressure_system", "kerosene_container", "iov_spirit_pan", "hand_fire_source",
    "iov_lamp_top", "spirit_source", "iov_mantle", "clockwork_lens_apparatus",
    "sheet", "cleaning_rag", "fresnel_lens", "oiler_set"
]
item_types.extend(lighthouse_items)

ignore_fingerprint_keys = ["id", "quantity", "static"]

# # Register consumables # 
# # 1. Get the list of dictionaries
# consumable_items_data = item_store.get_items_by_type("consumable")
# # 2. Extract just the names into a tuple
# _consumable_names = tuple(item['name'] for item in consumable_items_data)
# # 3. Create the Literal Type
# ConsumableItemType = Literal[_consumable_names] # type: ignore[valid-type]
# # 4. (Optional) For display or debugging
# print(f"Registered consumables: {', '.join(_consumable_names)}")
# print(ConsumableItemType)

# =============================================================================
# ITEM TYPES REGISTRY
# =============================================================================

ItemType = Literal[tuple(item_types)]

# =============================================================================
# TV TYPES REGISTRY
# =============================================================================

_tv_type_keys = tuple(TV_TYPE_CHANNELS.keys())
TVType = Literal[_tv_type_keys]  # type: ignore[valid-type]
tv_type_names = ", ".join(_tv_type_keys)


# =============================================================================
# PLANT TYPES REGISTRY
# =============================================================================

_plant_type_keys = tuple(plant_types.keys())
PlantType = Literal[_plant_type_keys]        # type: ignore[valid-type]
plant_type_names = ", ".join(_plant_type_keys)

## Go to plant_types (imported variable) to see, edit and create new plant types.

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

class ItemStatsEdit(BaseModel):
    """Stat deltas applied when a consumable item is used."""
    fullness: float = Field(description="A positive or negative float representing an effect on the metabolic system of a character. Dangerous meals use negative floats as they are harmful to the character.")
    hydration: float = Field(description="A positive or negative float representing an effect on the hydration of a character. Meals affect the dryness on the mouth, use floats logically. i.e. A meaty and salty broth would make the character feel thirstier, so a negative float is appropriate. A glass of water would be a positive float. Eating a raw meat would dehydrate the character, so a negative float is appropriate.")
    energy: float = Field(description="A positive or negative float representing an effect on the energy system of a character. Raw, spoiled, or otherwise dangerous meals when consumed cause digestive issues and risk sickness so negative values need to be applied respectively.")

class CandyBagEntry(BaseModel):
    item_name: str
    quantity: int


class DispenserState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contents: Optional[Dict[str, int]] = Field(
        default={},
        description="Always set to empty dict. Contents are managed at runtime, never by generation."
    )

class TVState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tv_type: TVType = Field(
        default=_tv_type_keys[0],
        description=f"The type of TV. From valid literals." # 
    )
    current_channel: Optional[str] = Field(
        default="",
        description=f"Currently airing channel. Always set to empty string. Managed by the TV tool."
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
    static: bool = Field(description="True if the item cannot be logically picked up or moved by a single human, like furniture, machinery, permanent fixtures or installed work equipment.")
    type: List[ItemType] = Field(description=f"One or more type tags. From valid literals.")
    stackable: bool = Field(default=False, description="Stackability is primarily driven by item size and weight, then by uniqueness. Most items are stackable except for furniture, objects larger than a human, or items that are too heavy to lift. Some truly unique items are not stackable, a specific meal is not stackable, but a red apple is stackable.")
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
    consume_uses_left: PositiveInt = Field(
        default=1,
        description=(
            "Logical bites or portions for consumables, dishes, bags, jars, bowls, etc. A single piece of bread has 5 bites, a full meal has 15, a milk carton has 25, etc."
            "Set to 1 for single-bite items like single pieces of candy, chocolates, or other single-bite items."
        )
    )
    stats_edit: ItemStatsEdit = Field(
        description="You should first think 'Is this a Potentially Hazardous Food?' (raw meats, spoiled foods, etc.). If it is, all the stat edits should be negative floats ranging from -10.0 to -0.5 depending on severity. If it is not, all the stat edits should be positive floats ranging from 0.5 to 10.0. "
    )
    effects: List[str] = Field(
        description="Narrative, evocative, grounded descriptions of the effects of consuming the item, **second-person, present tense** narration of the phenomenal experience of having a bite or consuming a portion of this item, based on consume_uses_left. Each entry on the list is an individual singular bite and narration of the experience from different angles and dimensions."
    )


class SeedFields(ContractMixin):
    model_description: ClassVar[str] = "A seed item, most of them are also consumables, they have a direct tie to a plant through its plant type, it must be always set as any of the valid literals. This seed growth and behavior are directly tied to its plant type."

    plant_type: PlantType = Field(
        description=f"The plant this type of seed grows. From valid literals. Always required for seed type." 
    )


class BookFields(ContractMixin):
    model_description: ClassVar[str] = "A book item, it can be a notebook for personal use or a publication with content, it can be empty or contain chapters. Its locked quality is determined by its use case. It varies wildly in presentation, from size, to cover art, to the color and format of the pages inside."
    chapters: Optional[List[BookChapter]] = Field(
        default=None,
        description="Ordered list of chapters in this book. If None, the book is empty."
    )
    is_locked: bool = Field(
        default=True,
        description="True if the book cannot be written to or edited after creation."
    )


class DispenserFields(ContractMixin):
    dispenser_state: DispenserState = Field(
        default={},
        description="Always set dispenser_state.contents to empty dict. Runtime manages contents."
    )



class CandyBagFields(ContractMixin):
    contents: List[CandyBagEntry] = Field(
        description="List of candy items and their quantities in the bag."
    )


class ToggableFields(ContractMixin):
    power_toggle: bool = Field(
        default=False,
        description="Current power state for electronic devices. True = on, False = off. Always set to False. Runtime manages state."
    )


class TVFields(ContractMixin):
    tv_state: TVState = Field(description="Runtime state of the TV, managed by the TV tool.")


# Lighthouse mixins

class LighthouseSpiritSourceFields(ContractMixin):
    model_description: ClassVar[str] = "A large container for spirit fuel, they come in various sizes, materials and shapes, depending on era. From wooden barrels, metal tins, to plastic containers. Usually stackable."

    spirit_quantity: float = Field(
        default=1.0,
        description="Amount of spirit remaining. 1.0 is full, 0.0 is empty."
    )


class LighthouseSpiritPanFields(ContractMixin):
    model_description: ClassVar[str] = "Made of different metals and in varying conditions and ages, they are used to hold spirit fuel to host a small flame. Usually stackable."

    filled: bool = Field(
        default=False,
        description="Whether the spirit pan currently contains spirit."
    )

###

class ArtBookFields(ContractMixin): # Does not define any fields, but injects a model_description for the LLM to use.
    model_description: ClassVar[str] = "These are varieties of notebooks, from E-ink drawing tablets to physical sketchbooks. They are used for drawing, sketching, and other forms of art. Covers can be made of various materials, such as paper, leather, plastic, etc."


class FenetreApertureFields(ContractMixin):
    model_description: ClassVar[str] = "These are architectural designs, ornamental, functional, furniture and static fixtures of a room, ranging from windows, skylights, light wells, clerestories to sun tubes, portholes and any others designed as apertures of a room to peer through to the outside world."

    accessible: bool = Field(
        default=True,
        description="This true or false flag represents the accessibility, and reachability for the opening fixture. It asks if it is possible to stand no more than 1 feet besides it, if so, it should be set to true. Features like raised windows or skylights and other inaccessible apertures should be set as false."
    )

class BookMakingImplementsFields(ContractMixin): # No required fields, just adding model description
    model_description: ClassVar[str] = "This type of item holds and provides the ability to create books, from DIY carry kits for simple books, simple areas for home-made binding in workbenches, DIY enthusiasts spaces, semi-profesional apparatuses, to large machinery, or any other."

class MeditationAidsFields(ContractMixin):
    model_description: ClassVar[str] = "These items are meditation aids, sensory decor, ambience decorations, meaningful, unique, or personal trinkets, furniture, and other sources of relaxation, inspiration for deep thought, meditation, or other forms of mindfulness practices. From small objects like incense, cushions, windchimes, emotionally charged trinkets, to larger items like yoga mats, particularly beautiful benches, fountains, and others."
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
    "art_book":          ArtBookFields, # no fields — model_description only

    "fenestration_aperture": FenetreApertureFields,
    "bookmaking_implements": BookMakingImplementsFields,
    "meditation_aids": MeditationAidsFields,
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