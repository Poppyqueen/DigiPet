# pydantic_models.py
from typing import List
from pydantic import BaseModel

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class response_strucuture(BaseModel):
    thinking: str
    response: str

class entity_dict(BaseModel):
    Named_Entity: str
    excerpts: List[str]

class look_ner_structure(BaseModel):
    named_entities: List[str]

class save_ner_structure(BaseModel):
    entities: List[entity_dict]

class individual_item(BaseModel):
    name: str
    descriptions: List[str]

class edited_item(BaseModel):
    name: str
    description: str

class crafter_structure(BaseModel):
    names: List[individual_item]

class event_crafter(BaseModel):
    event: str
    edited_items: List[edited_item]
    created_items: List[individual_item]
    



### ///// New Classes


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

    type: List[str] = Field(description="A list of types for the item, e.g., ['consumable', 'seed'], from the possible, consumable, seed or misc. A misc item cannot be a consumable.")

    
# --- Structure that contains a list of these item definitions (Optional) ---
# This is if you needed a container holding a list of objects matching the above definition
class ItemDefinitionListContainer(BaseModel):
    """
    A container model holding a list of item definitions.
    """
    items: List[ItemDefinition] = Field(description="A list of item definition objects.")
