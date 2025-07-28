# pydantic_models.py
from typing import List
from pydantic import BaseModel

from pydantic import BaseModel, Field
from typing import List


### ///// Classes (Deep memory entities)


class characteristic_structure(BaseModel):
    characteristic: str = Field(description="The distinguishable intrinsic characteristic or propertie of this entity, I.E, colors, shapes, materials, sensations, interests, etc. You have to directly write the characteristics identified as an individual")
    messages_sources_ids: List[str] = Field(description="A list of IDs from the message where this specific characteristic for the entity is mentioned or extracted from.")

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
    Must contain exactly 'fullness', 'hydration', and 'energy' as integers.
    """
    fullness: float = Field(description="Integer change to fullness stat.")
    hydration: float = Field(description="Integer change to hydration stat.")
    energy: float = Field(description="Integer change to energy stat.")


# --- Structure for the individual item definition ---
class ItemDefinition(BaseModel):
    """
    Represents the data required to define a single item for creation.
    Excludes the ID and the 'type' field as per requirements.
    Includes a strictly defined stats_edit structure.
    """
    name: str = Field(description="A unique string identifier for the item type (e.g., 'bowl_of_nuts').")
    descriptions: List[str] = Field(description="A list of strings providing descriptions for the item.")
    static: bool = Field(description="Indicates if the item is static (cannot be picked up or moved).")

    # Use the specific ItemStatsEdit model to enforce the structure and keys
    stats_edit: ItemStatsEdit = Field(description="A dictionary containing specific stat changes (fullness, hydration, energy).")

    # 'effects' field from your example, assuming it's required for this definition structure
    effects: List[str] = Field(description="A list of strings describing narrative effects upon use.")

    type: List[str] = Field(description="A list of types for the item, e.g., ['consumable', 'seed'], from the possible, consumable, seed, furniture or misc. A misc item cannot be a consumable.")

    
# --- Structure that contains a list of these item definitions (Optional) ---
# This is if you needed a container holding a list of objects matching the above definition
class ItemDefinitionListContainer(BaseModel):
    """
    A container model holding a list of item definitions.
    """
    items: List[ItemDefinition] = Field(description="A list of item definition objects.")
