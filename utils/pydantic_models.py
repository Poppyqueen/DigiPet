# pydantic_models.py
from typing import List
from pydantic import BaseModel

from pydantic import BaseModel, Field
from typing import List


valid_plants = ['lettuce', 'carrot', 'cactus', 'tomato', 'potato', 'strawberry', 'rose', 'sunflower', 'mint', 'basil'] # Edit this to reflect the plants existing in the garden manager data structures. tools/tools_folder/tools_data/harvesting_data.py

stringed_plant_types = ', '.join(f"'{plant}'" for plant in valid_plants)

item_types= ["consumable", "misc", "furniture", "seed", "seat", "art_book", "bed", "tv", "pillow", "laptop", "iPod", "cellphone", "book", "bluesky_social", "dispenser", "candy_bag"]

room_types = ["planting_garden","library","bedroom","living_room","bathroom","garden","white_room","kitchen","ALIFE_research", "computer_room"]

### ///// Classes (Deep memory entities)


class characteristic_structure(BaseModel):
    messages_sources_ids: List[str] = Field(description="A list of IDs from the message where this specific characteristic for the entity is mentioned or extracted from.")
    characteristic: str = Field(description="The distinguishable intrinsic characteristic or propertie of this entity, I.E, colors, shapes, materials, sensations, interests, etc. You have to directly write the characteristics identified as an individual")

class entity_dict(BaseModel):
    named_entity: str = Field(description="The entity identified in the memory structure")
    characteristics: List[characteristic_structure] = Field(description="A list of  distinguishable intrinsic characteristics or properties of this entity")

class save_ner_structure(BaseModel):
    entities: List[entity_dict] = Field(description="A collection of important identified entities in memory, accompanied by their intrinsic characteristics and specific information recognized and the messages ID sources for the origins of these qualities and details extracted.")


### ///// Classes (Items)


# --- Structure for the fixed stats_edit dictionary ---
class ItemStatsEdit(BaseModel):
    """
    Defines the required structure for the stats_edit dictionary.
    Must contain exactly 'fullness', 'hydration', and 'energy' as floats.
    """
    fullness: float = Field(description="Float change to fullness stat. Can be negative for inflicting negative effects or punishments for consumption.")
    hydration: float = Field(description="Float change to hydration stat. Can be negative for inflicting negative effects or punishments for consumption.")
    energy: float = Field(description="Float change to energy stat. Can be negative for inflicting negative effects or punishments for consumption.")

# --- Structure for the individual item definition ---
class ItemDefinition(BaseModel):
    """
    Represents the data required to define a single item for creation.
    Excludes the ID as per requirements.
    Includes a strictly defined stats_edit structure, but fields are optional based on type.
    """
    name: str = Field(description="A unique string identifier for the item type (e.g., 'bowl of nuts').")
    descriptions: List[str] = Field(description="A list of strings providing descriptions for the item.")
    static: bool = Field(description="Indicates if the item is static (cannot be picked up or moved like furniture).")
    # UPDATED: type is now List[str]
    type: List[str] = Field(description=f"A list of strings defining item categories (e.g., ['consumable'], ['misc', 'tool'], ['consumable', 'seed'], ['seed']). Available categories: {", ".join(item_types)}.")    
    stackable: bool = Field(default=True, description="Bool for the stackablity property of this item, if defaults to true. Small non-unique items should be set to true so they are stackable. Large and unique items should be set to FALSE")
    # MAKE effects and stats_edit OPTIONAL
    # Use | None for Pydantic V2 syntax for optional fields
    # default=None allows the field to be missing in the input data without Pydantic error

    effects: List[str] |None= Field(default=None, description="A list of strings describing narrative and evocative effects upon use (only for 'consumable' items). i.e 'You feel refreshed after eating the apple', 'The apple gives a delicious juicy and sweet crunch'. Or, 'You eat the salt by itself, an overpowering slightly disgusting metalic flavor takes over you', 'You eat the raw eags, the slimy texture and the lack of taste make you gag', 'Eating the raw egss makes your stomach churn'")
    stats_edit: ItemStatsEdit |None = Field(default=None, description="A dictionary containing specific stat changes (fullness, hydration, energy) (only for 'consumable' items) Can be possitive or negative, i.e 'hydration' -10 for a salty snack. -50 hydration for dry rice, -50 energy for raw meat, +4 hydration for a fresh apple, etc.")
    
    contents: dict[str, int] | None = Field(default=None, description="A dictionary mapping item names to quantities, used for container items like 'candy_bag'.")

    plant_type: str  |None =Field(default=None, description=f"A string for the seed type, it should define the plant of seed this is for, from the valid options: {stringed_plant_types}")

# --- Structure that contains a list of these item definitions ---
class ItemDefinitionListContainer(BaseModel):
    """
    A container model holding a list of item definitions.
    """
    items: List[ItemDefinition] = Field(description="A list of item definition objects.")
