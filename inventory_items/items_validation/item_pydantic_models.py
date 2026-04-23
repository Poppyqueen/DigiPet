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
from pydantic import BaseModel, Field, ConfigDict, PositiveInt, model_validator, create_model, PositiveFloat
from pydantic.functional_validators import AfterValidator
from typing import ClassVar

from .contract_mixin import ContractMixin

from tools.tools_folder.tools_helpers.outdoors_helpers.outdoors_type_definitions import OUTDOORS_TYPES
from tools.tools_folder.tools_helpers.tv_utils.tv_channels_definitions import TV_TYPE_CHANNELS
from tools.tools_folder.tools_data.harvesting_data import plant_types
from tools.tools_folder.tools_helpers.maze_sim.types import MazeState

from tools.tools_folder.tools_helpers.store_helpers.store_types import StoreEndpointData, StoreEntryData

import os
import json

narrative_prompt = "A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of,"

## Registry helpers

# 1. Load the MCP Config from root

def get_mcp_item_types(config_path: str | None = None) -> list[str]:
    """
    Load MCP item types from a specific config path, or the root
    mcp_config.json if config_path is None.
    """
    path = config_path
    print(f"[DEBUG] Target config path: {path}")

    if not os.path.exists(path):
        print(f"[DEBUG] File not found at: {path}")
        return []

    try:
        with open(path, 'r') as f:
            config = json.load(f)
            
        mcp_servers = config.get("mcpServers", {})
        print(f"[DEBUG] Found {len(mcp_servers)} server entries in 'mcpServers'")
        
        found_types = []
        for server_name, server_data in mcp_servers.items():
            affordance = server_data.get("affordance", {})
            types = affordance.get("item_types", [])
            
            if types:
                print(f"[DEBUG] Server '{server_name}' provided types: {types}")
            else:
                print(f"[DEBUG] Server '{server_name}' has no 'item_types' defined")
                
            found_types.extend(types)

        unique_types = list(set(found_types))
        print(f"[DEBUG] Final unique item types list: {unique_types}")
        return unique_types

    except json.JSONDecodeError as e:
        print(f"[DEBUG] ERROR: Failed to parse JSON in '{path}': {e}")
    except Exception as e:
        print(f"[DEBUG] ERROR: Unexpected error loading mcp_config: {e}")
        
    return []

# =============================================================================
# CONSTANTS
# =============================================================================
ignore_fingerprint_keys = ["id", "quantity", "static"]


toggable_items = ["tv", "maze_interface"] # This variable is a concept bag, does not affect the code, will be removed later

item_types = ["consumable", "seed", "book", "dispenser", "candy_bag"]
item_types.extend(toggable_items)

refactored_types = [
                    "fenestration_aperture", "bookmaking_implements", "meditation_aid", 
                    "sleepable_spot", "seatable", 
                    "cranny_host", "dust_bunnied_gleaning","comfort_object",
                    "water_point",  # If consumables change, this might want to change
                    "culinary_equipment", # If consumables change, this has to change
                    "ALIFE_interface", # Needs work on its methods
                    "planter_pot",
                    "toggleable",

                    "youtube_playlists_endpoint", "discogs_endpoint",
                    "musicbrainz_endpoint", "bluesky_social_endpoint", 
                    "wikipedia_endpoint", "searxng_endpoint",
                    "online_store",
                    "drawing_area",

                    "store_entry", "store_endpoint"
                    ] # In process of refactoring tools and affordances, making them more general and modular.
item_types.extend(refactored_types)



lighthouse_items = [
    "iov_pressure_system", "kerosene_container", "iov_spirit_pan", "hand_fire_source",
    "iov_lamp_top", "spirit_source", "iov_mantle", "clockwork_lens_apparatus",
    "sheet", "cleaning_rag", "fresnel_lens", "oiler_set"
]
item_types.extend(lighthouse_items)

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

# Go to TV_TYPE_CHANNELS and write new TV types! 


# =============================================================================
# PLANT TYPES REGISTRY
# =============================================================================

_plant_type_keys = tuple(plant_types.keys())
PlantType = Literal[_plant_type_keys]        # type: ignore[valid-type]
plant_type_names = ", ".join(_plant_type_keys)

## Go to plant_types (imported variable) to see, edit and create new plant types.


# =============================================================================
# OUTDOORS TYPES REGISTRY
# =============================================================================

_outdoors_type_keys = tuple(OUTDOORS_TYPES)
OutdoorsType = Literal[_outdoors_type_keys]  # type: ignore[valid-type]
outdoors_type_names = ", ".join(_outdoors_type_keys)
# Go to OUTDOORS_TYPES and add new outdoors types! Provider based system with an Abstract Class.
# =============================================================================
# Note: Maze items own a maze type, these types determine props and flavor text when traversing a maze environment.
# Create and edit maze types here: tools/tools_folder/tools_helpers/maze_sim/maze_props.py
# =============================================================================

def get_base_item_types() -> list[str]:
    """
    Returns the full list of hardcoded item types known to this module.
    Use this to build per-agent valid type sets rather than importing
    item_types directly (which is a module-level list, not a copy).
    """
    return list(item_types)
# =============================================================================
# SHARED SUB-MODELS
# Named nested types used by mixins. Being explicit BaseModel subclasses means
# the LLM receives a documented, named structure rather than an opaque dict,
# and validation catches wrong shapes early.
# =============================================================================

class ToggleableStates(BaseModel):
    """Object containing the info for a toggleable state."""
    toggle_state: Literal["on", "off"] = Field(
        default="off",
        description="Current toggle state of the item.")
    toggle_uses_left: int | None = Field( # This could be 'consume_uses_left' from consumables, rip that key from it and make "digestable"s? ingestables? and make a general "consume_uses" type item that all other types and methods also use?
        default=None,
        description="Number of times the item can be toggled before it is disabled or fully consumed by its uses, i.e an incense stick could have 2 or 3 uses. None for infinite toggles like electronics.")

    on_description: str = Field(
        description="Short, single sentence description of the item as it is on, **present tense**")
    off_description: str = Field(
        description="Short, single sentence description of the item as it is off, **present tense**")

    on_sequence: str = Field(
        description="**second-person, present tense** evocative and grounded narration of the phenomenal experience of, the boot-up, cold start-up or toggle action experience of this item."
    )
    off_sequence: str = Field(
        description="**second-person, present tense** evocative and grounded narration of the phenomenal experience of, the turning off, cooldown or extinguishing of such item."
    )

    perishable: bool = Field(
        description="Is this item ephemeral? transitory? Will it be completely consumed when it has no more uses left? If so, set this to true."
    )
    ticks_lasting : int = Field(
        description="Represents how many in-game ticks a single use lasts. Ranging from 3 to 10. Only relevant for items that have toggle_uses_left."
    )
    ticks_elapsed : int = Field(
        default=0,
        description="Handled by runtime, always initialize as 0."
    )


class BookChapter(BaseModel):
    """A single chapter inside a book item."""
    title: str
    content: str

class ItemStatsEdit(BaseModel):
    """Stat deltas applied when a consumable item is used."""
    fullness: float = Field(description="A positive or negative float representing an effect on the metabolic system of a character. Dangerous meals or drinks use negative floats as they are harmful to the character.")
    hydration: float = Field(description="A positive or negative float representing an effect on the hydration of a character. Meals and drinks affect the dryness on the mouth, use floats logically. i.e. A meaty and salty broth would make the character feel thirstier, so a negative float is appropriate. A glass of water would be a positive float. Eating a raw meat would dehydrate the character, so a negative float is appropriate.")
    energy: float = Field(description="A positive or negative float representing an effect on the energy system of a character. Raw, spoiled, or otherwise dangerous meals or tainted drinks when consumed cause digestive issues and risk sickness so negative values need to be applied respectively.")

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
    type: Optional[List[str]] = Field(default=[], description=f"Empty, one or more type tags from valid literals. Empty list if none of the existing types fits. Used to define, control and determine specific behaviors and required keys for the item. Standard items with no interaction do not require a types.")
    stackable: bool = Field(default=False, description="Stackability is primarily driven by item size and weight, then by uniqueness. Most items are stackable except for furniture, objects larger than a human, or items that are too heavy to lift. Some truly unique items are not stackable, a specific meal is not stackable, but a red apple is stackable.")
    quantity: PositiveInt = Field(default=1, description="How many units are in this stack. Always 1.")
    max_stack_size: Optional[PositiveInt] = Field(default=None, description="Maximum units per stack. None means unlimited.")

    # @model_validator(mode="after") # Runtime handles this.
    # def check_stacking_consistency(self) -> "BaseItem":
    #     if not self.stackable:
    #         if self.quantity > 1:
    #             raise ValueError("Non-stackable item cannot have quantity > 1")
    #         if self.max_stack_size is not None and self.max_stack_size > 1:
    #             raise ValueError("Non-stackable item cannot have max_stack_size > 1")
    #     return self


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
        description="A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, having a bite or consuming a portion of this item, based on consume_uses_left. Each entry on the list is an individual singular bite and narration of the experience from different angles and dimensions."
    )

    examine_fields: ClassVar[list[str]] = ["consume_uses_left"] # Examine fields are not used during validation nor LLM structured generation, they define the behavior of each type for the 'examine_item' tool, whatever is listed here or returned by a 'render_examine_section' classmethod will be appended into any examine action for an item that matches this type. 



class SeedFields(ContractMixin):
    model_description: ClassVar[str] = "A seed item, most of them are also consumables, they have a direct tie to a plant through its plant type, it must be always set as any of the valid literals. This seed growth and behavior are directly tied to its plant type."

    plant_type: PlantType = Field(
        description=f"The plant this type of seed grows. From valid literals. Always required for seed type." 
    )


class BookFields(ContractMixin):
    model_description: ClassVar[str] = "A book item, it can be a notebook for personal use or a publication with content, it can be empty or contain chapters. Its locked quality is determined by its use case. It varies wildly in presentation, from size, to cover art, to the color and format of the pages inside."
    chapters: List[BookChapter] = Field(
        default=[],
        description="Ordered list of chapters in this book. Empty list means the book is empty."
    )
    is_locked: bool = Field(
        default=True,
        description="True if the book cannot be written to or edited after creation."
    )

    @classmethod
    def render_examine_section(cls, item_data: dict) -> str | None:
        """Return a formatted Table of Contents for the book."""
        chapters = item_data.get("chapters", [])
        
        if not chapters:
            return "The pages are blank."

        # Header for the section
        lines = ["--- CONTENTS ---"]
        
        # Enumerate provides the index (starting at 1) and the chapter data
        for i, chapter in enumerate(chapters, 1):
            title = chapter.get("title", "Untitled Chapter")
            lines.append(f"{i}. {title}")
            
        return "\n".join(lines)


class DispenserFields(ContractMixin):
    dispenser_state: DispenserState = Field(
        default={},
        description="Always set dispenser_state.contents to empty dict. Runtime manages contents."
    )

    @classmethod
    def render_examine_section(cls, item_data: dict) -> str | None:
        contents = (item_data.get("dispenser_state") or {}).get("contents") or {}
        total = sum(contents.values())
        if total <= 0:
            return "The dispenser is empty. You need to refill it."
        return f"The dispenser has {total} candies left."

class CandyBagFields(ContractMixin):
    contents: List[CandyBagEntry] = Field(
        description="List of candy items and their quantities in the bag."
    )


class ToggableFields(ContractMixin):
    model_description : ClassVar[str] = "This type modifies any item so its affordances are toggleable, these items are utilities one can change their state, ranging from incense sticks to electronic devices like computers, to windows or other systems."
    toggle_state : ToggleableStates = Field(
        description="The initial state of a toggable item, detailing its total uses capacity, and description on either state."
    )

    @classmethod
    def render_examine_section(cls, item_data: dict) -> str | None:
        ts = item_data.get("toggle_state")
        if not ts:
            return None
        state = ts.get("toggle_state", "off")
        desc = ts.get("on_description") if state == "on" else ts.get("off_description")
        lines = [f"State: {state}", desc] if desc else [f"State: {state}"]
        uses = ts.get("toggle_uses_left")
        if uses is not None:
            lines.append(f"Uses remaining: {uses}")
        return "\n".join(lines)


class TVFields(ContractMixin):
    tv_state: TVState = Field(description="Runtime state of the TV, managed by the TV tool.")

    @classmethod
    def render_examine_section(cls, item_data: dict) -> str | None:
        tv = item_data.get("tv_state")
        if not tv:
            return None
        state = item_data.get("toggle_state", {})
        if state:
            if state.get("toggle_state") != "on":
                return None
        channel = tv.get("current_channel")
        if not channel:
            return None
        return f"Current channel: {channel}"

# Lighthouse mixins

class LighthouseSpiritSourceFields(ContractMixin):
    model_description: ClassVar[str] = "A large container for spirit fuel, they come in various sizes, materials and shapes, depending on era. From wooden barrels, metal tins, to plastic containers. Usually stackable."

    spirit_quantity: float = Field(
        default=1.0,
        description="Amount of spirit remaining. 1.0 is full, 0.0 is empty."
    )

    @classmethod
    def render_examine_section(cls, item_data: dict) -> str | None:
        return f"Spirit Percentage: {item_data.get('spirit_quantity', 0):.1%}"



class LighthouseSpiritPanFields(ContractMixin):
    model_description: ClassVar[str] = "Made of different metals and in varying conditions and ages, they are used to hold spirit fuel to host a small flame. Usually stackable."

    filled: bool = Field(
        default=False,
        description="Whether the spirit pan currently contains spirit."
    )
    examine_fields: ClassVar[list[str]] = ["filled"]

###

class ArtBookFields(ContractMixin): # Does not define any fields, but injects a model_description for the LLM to use.
    model_description: ClassVar[str] = "These are varieties of notebooks, from E-ink drawing tablets to physical sketchbooks. They are used for drawing, sketching, and other forms of art. Covers can be made of various materials, such as paper, leather, plastic, etc."


class FenetreApertureFields(ContractMixin):
    model_description: ClassVar[str] = "These are architectural designs, ornamental, functional, furniture and static fixtures of a room, ranging from windows, skylights, light wells, clerestories to sun tubes, portholes and any others designed as apertures of a room to peer through to the outside world."

    accessible: bool = Field(
        default=True,
        description="This true or false flag represents the accessibility, and reachability for the opening fixture. It asks if it is possible to stand no more than 1 feet besides it, if so, it should be set to true. Features like raised windows or skylights and other inaccessible apertures should be set as false."
    )

    outdoors_type: List[OutdoorsType] = Field(
        default=[_outdoors_type_keys[0]],
        description=f"A list of outdoors types that can be seen from this aperture. From valid literals."
    )

class BookMakingImplementsFields(ContractMixin): # No required fields, just adding model description
    model_description: ClassVar[str] = "This type of item holds and provides the ability to create books, from DIY carry kits for simple books, simple areas for home-made binding in workbenches, DIY enthusiasts spaces, semi-profesional apparatuses, to large machinery, or any other."

class MeditationAidFields(ContractMixin):
    model_description: ClassVar[str] = "These items are meditation aid, sensory decor, ambience decorations, meaningful, unique, or personal trinkets, furniture, and other sources of relaxation, inspiration for deep thought, meditation, or other forms of mindfulness practices. From small objects like incense, cushions, windchimes, emotionally charged trinkets, to larger items like yoga mats, particularly beautiful benches, fountains, and others."

    meditation_aid_ambience: List[str] = Field(
        description="**Present tense** evocative descriptions of what ambience effect this specific item brings, examples range from the description of humidifiers and their soft LED illumination, to personal objects like jewerly emitting powerful courage for whoever is near it, or the entrancing soft rythm of a water fountain."
    )
    
class SleepableSpotFields(ContractMixin):
    model_description: ClassVar[str] = "These items range from beds, couches, hammocks and some chairs to tents, sleeping bags, some rugs, or any reasonable place where one could sleep on."

    narrative_sleeping: List[str] = Field(
        description="A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, laying down and sleeping on this item."
    )


# --- Paste into item_pydantic_models.py alongside the other ContractMixin definitions ---
# Then add "cranny_host": CrannyHostFields to TYPE_FIELD_CONTRACTS.

class CrannyHostFields(ContractMixin):
    model_description: ClassVar[str] = (
        "A nook, cranny, crevice, or hidden hollow within a piece of furniture or room feature "
        "that may conceal small forgotten or lost objects. The yield_pool depletes as items are "
        "pulled from it and replenishes over time via the tick system."
    )

    chance: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "Base probability (0.0–1.0) that a search action finds anything at all. "
            "0.05 is a tight crevice that rarely gives up its secrets; 0.3 is an obvious cubby."
        )
    )
    yield_pool: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Current resource level of this nook (0.0–1.0). Always initialise at 1.0. "
            "Managed by the tool at runtime — decreases on a successful pull, "
            "replenishes each tick by refresh_rate up to 1.0."
        )
    )
    yield_cost: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description=(
            "How much yield_pool is consumed by a single successful pull. "
            "0.25 means the nook can be harvested ~4 times before running dry. "
            "A rare, singular hiding spot might use 1.0."
        )
    )
    refresh_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description=(
            "How much yield_pool is restored each tick. "
            "0.1 means a fully drained nook refills over ~10 ticks. "
            "Set very low (0.01–0.05) for spots that should stay sparse for a long time."
        )
    )
    reward_options: List[List[ItemType]] = Field(
        default_factory=list,
        description=(
            "A list of lists. Each nested list represents a collection of types for the possible "
            "rewarded item extracted from this cranny host. Use 'dust_bunnied_gleaning' if no "
            "logical item types fit. A front-weighted random pick selects one inner list, which "
            "is then passed to the crafter as the item type constraint. "
            "Example for a cranny behind a bookshelf: "
            "[['dust_bunnied_gleaning'], ['trinket'], ['consumable'], ['trinket', 'readable']]."
        )
    )
    narrative_search: List[str] = Field(
        default_factory=list,
        description=(
            "A list of **second-person, present tense** narration lines describing the physical "
            "act of reaching into or searching this nook. Each line should feel distinct — "
            "different angles of the same gesture. One is chosen at random per search."
        )
    )

    examine_fields: ClassVar[list[str]] = ["yield_pool", "yield_cost", "refresh_rate"]


class DustBunniedGleaningFields(ContractMixin):
    model_description: ClassVar[str] = "Inconsequential flotsam of all sorts, the rewards of reaching into the forgotten corners and crevices of a room, such as lost buttons, discontinued coins, antique kitchen utensils, former held-close trinkets, and other defunct minutiae."

class SeatableFields(ContractMixin):
    model_description: ClassVar[str] = "Items like chairs, seats, stools, benches, couches, hammocks, beds, some desks, a variety of rugs, or any reasonable place where one could sit on."

    narrative_sitting: List[str] = Field(
        description="A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, sitting on this item."
    )

class ComfortObjectFields(ContractMixin):
    model_description: ClassVar[str] = "These items usually are soft goods, tactile comfort objects or other emotionally charged objects; plushies, blankets, pillows, dolls, or any other item that can be hugged."

    narrative_hug: List[str] = Field(
        description="A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, hugging this item."
    )

class WaterPointFields(ContractMixin):
    model_description: ClassVar[str] = "This type is never combined with 'consumable' type; Water points are currently functional or active, environmental features, water fixtures, water bodies, aqueous outlets, all sorts of water sources and water points, like rivers, ponds, kitchen faucets, outdoors faucets and others, ranging in safety from tainted rivers, to fresh water ponds and saline shoars, sewage outlets and kitchen fauces and more, exclusive to fixtures and large features of the environment, NEVER individual carry water sources like water bottles or glasses of water."

    narrative_drinking: List[str] = Field(
        description="A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, taking a sip directly out of this water source."
    )
    narrative_wash_self: List[str] = Field(
        description="A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, different ways to wash and rinse oneself with such water source."
    )
    stats_edit: ItemStatsEdit = Field(
    description="You should first think 'Is this a Potentially Hazardous Water Source?' (badly tainted rivers, sewage outlets, a saline water body, etc.). If it is, all the stat edits should be negative floats ranging from -15.0 to -0.5 depending on severity. If it is instead a fresh drinkable water source, all the stat edits should be positive floats ranging from 0.1 to 0.5. They represent a sip."
    )

class CulinaryImplementsFields(ContractMixin):
    model_description: ClassVar[str] = "These are culinary fixtures, furniture, appliances, workstations or vessels that transform food, from salad mixers, blenders, toasters, ovens to open fires and grills, cookeries or hearths, from appliances or work areas. It strictly excludes utensils and items that are not completely self-contained for their full functional use."

    narrative_prepare: List[str] = Field(
        description="A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, the starting interaction, first actions and first contact with this specific item. Do not mention specific ingredients, processes or outcomes, only descriptions and narratives of encountering and preparing to use such item."
    )
    # equipment_affordances: str = Field( # For future reference, possible update, make this utensils and equipment, and use affordances propmt for AI cook, validate a list of all equipments and consumables separately, validate accessibility for equipments, validate power toggle or default to true. Do not overthink contianers, but maybe do.
    #     description="A string listing the range of affordances, verbs or actions this item provides."
    # )


class PlanterPotFields(ContractMixin):
    model_description: ClassVar[str] = (...)

    capacity: int = Field(
        default=1,
        description="How many plant slots this pot has. A small terracotta pot has 1, a rooftop planting bed might have 3 or 4."
    )
    size_multiplier: float = Field(
        default=1.0,
        le=2.5,
        ge=0.25,
        description="Harvest yield multiplier at harvest time. Above 1.0 increases yield, below 1.0 reduces it."
    )
    examine_fields: ClassVar[list[str]] = ["capacity"]


# Following fields do not contain any required keys, but they inject model descriptions for the LLM to use, and they are registered in the TYPE_FIELD_CONTRACTS registry to be recognized as valid types and have their descriptions injected into the LLM schema.
base_endpoints_description = "These items, usually toggleable electronic devices, are gateways to different information sources, databases, APIs, or other digital repositories of information. They affort detailed interactions, control and manipulation on the information they provide access to, and they are meant to be used as tools for information retrieval, research, or entertainment. They can be mixed and matched with other types, from handhelds to interactive furniture."
class YoutubeEndpointFields(ContractMixin):
    model_description: ClassVar[str] = f"{base_endpoints_description} This specific endpoint provides access to a Youtube account, with the ability to search for videos, create and manage playlists."
class DiscogsEndpointFields(ContractMixin):
    model_description: ClassVar[str] = f"{base_endpoints_description} This specific endpoint provides access to a Discogs account, with the ability to search for records, create and manage collections, and view artist information."
class MusicBrainzEndpointFields(ContractMixin):
    model_description: ClassVar[str] = f"{base_endpoints_description} This specific endpoint provides access to a MusicBrainz, with a stateless implementation, it is direct access to a large music database without any accounts tied to it. It provides the ability to search for artists, albums, tracks, and view detailed information about them."
class BlueskySocialEndpointFields(ContractMixin):
    model_description: ClassVar[str] = f"{base_endpoints_description} This specific endpoint provides access to a Bluesky Social account, with the ability to view and post content, with the platform's AT Protocol."
class WikipediaEndpointFields(ContractMixin):
    model_description: ClassVar[str] = f"{base_endpoints_description} This specific endpoint provides access to Wikipedia, with a stateless implementation, it is direct access to the Wikipedia database without any accounts tied to it. It provides the ability to search and retrieve Wikipedia articles."
class SearxngEndpointFields(ContractMixin):
    model_description: ClassVar[str] = f"{base_endpoints_description} This specific endpoint provides access to a Searxng instance with direct access to a meta-search engine and the ability to query found results for full website content retrieval."

class ColabEndpointFields(ContractMixin):
    model_description: ClassVar[str] = f"{base_endpoints_description} This specific endpoint provides access to a Colab notebook, with the ability to execute code cells, retrieve outputs, and manage the notebook's content. It is meant to be used as a powerful tool for running custom code, data analysis, or any other task that can be accomplished within a Colab environment."

class MazeInterface(ContractMixin):
    model_description: ClassVar[str] = f"Maze device or toy, it can be a physical maze box with a small ball inside, or a virtual maze on a screen. The item provides an interactive maze experience, where the user can navigate through the maze by tilting the box or using controls for the virtual version. It can be used for entertainment, stress relief, or as a cognitive exercise."

    stackable : bool = False # Overrides and forces base key
    maze_state : MazeState = Field(
        description="The state of the maze, including the seed for generation, size, current position, goal position, and steps taken. Managed by the maze tool."
    )


class ImagesLabFields(ContractMixin):
    model_description: ClassVar[str] = "Digital or physical sketchbooks, drawing notebooks or paginated archives that contain images and where someone can create new entries by adding new images to it. They can be physical or digital."
    images_lab_uid: str = Field(
        default="",
        description="Stable archive UID. Always initialise as empty string — assigned automatically by the tool on first use."
    )

class StoreEntryFields(ContractMixin):
    model_description: ClassVar[str] = "A store entry item represents a purchasable offering in an online or physical store. It contains details about the product, such as its name, description, price, and any other relevant information that a customer would need to know before making a purchase. This type is meant to be used in conjunction with the StoreEndpointFields type, which provides access to a store's inventory and purchasing system."
    store_entry_data: StoreEntryData = Field(
        description="Data specific to a store entry, including price, availability, and other relevant details. Managed by the store endpoint tool."
    )
class StoreEndpointFields(ContractMixin):
    model_description: ClassVar[str] = "This specific endpoint provides access to an online or physical store, with the ability to browse products, view details, and make purchases. It is meant to be used as a tool for shopping and managing online purchases, and it can be mixed with other types for enhanced functionality, such as toggleable for electronics or dispensers for vending machines."
    store_endpoint_data: StoreEndpointData = Field(
        description="Data specific to a store endpoint, including available categories and item listings. Managed by the store endpoint tool."
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
    "tv":                TVFields,
    "iov_spirit_pan":    LighthouseSpiritPanFields,
    "spirit_source":     LighthouseSpiritSourceFields,
    "art_book":          ArtBookFields, # no fields — model_description only

    "fenestration_aperture": FenetreApertureFields, # windows, doors, skylights, clerestories, light wells, portholes, sun tubes, etc.
    "bookmaking_implements": BookMakingImplementsFields, 
    "meditation_aid": MeditationAidFields, 
    "sleepable_spot": SleepableSpotFields, # Spaces to sleep, holes, tents, hammocks, beds, couches.
    "cranny_host": CrannyHostFields, # Any furniture where small inconsequential items can fall under. # TODO: Update with dust_bunnied_gleaning type
    "dust_bunnied_gleaning": DustBunniedGleaningFields, # Rewards of digging into crannies. # TODO: Add specific typing for this, like the plants or the TV registry with literals, tie the "dust_bunnied_gleaning" with a new cranny_host type.
    "seatable": SeatableFields, # Places you can sit on
    "comfort_object": ComfortObjectFields, # You would want to hug these
    "water_point": WaterPointFields, # 
    "culinary_equipment": CulinaryImplementsFields, # Needs an update alongside consumables.
    "planter_pot": PlanterPotFields,
    "toggleable": ToggableFields,

    "youtube_playlists_endpoint": YoutubeEndpointFields,
    "discogs_endpoint": DiscogsEndpointFields,
    "musicbrainz_endpoint": MusicBrainzEndpointFields,
    "bluesky_social_endpoint": BlueskySocialEndpointFields,
    "wikipedia_endpoint": WikipediaEndpointFields,
    "searxng_endpoint": SearxngEndpointFields,
    "colab_endpoint": ColabEndpointFields,

    "maze_interface": MazeInterface, # You can add more maze types and props for these: tools/tools_folder/tools_helpers/maze_sim/maze_props.py

    "drawing_area": ImagesLabFields,

    "store_entry": StoreEntryFields,
    "store_endpoint": StoreEndpointFields,

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