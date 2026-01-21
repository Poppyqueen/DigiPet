# pydantic_models.py
from typing import List
from pydantic import BaseModel

from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any, Literal, Annotated


valid_plants = ['lettuce', 'carrot', 'cactus', 'tomato', 'potato', 'strawberry', 'rose', 'sunflower', 'mint', 'basil'] # Edit this to reflect the plants existing in the garden manager data structures. tools/tools_folder/tools_data/harvesting_data.py

stringed_plant_types = ', '.join(f"'{plant}'" for plant in valid_plants)

toggable_items = ["tv", "bluesky_social", "iPod", "cellphone", "maze", "laptop", "desktop_computer"]

item_types= ["consumable", "misc", "furniture", "seed", "seat", "art_book", "bed", "pillow", "book", "dispenser", "candy_bag"]
# Might want to add validation for the dispenser and candy_bag items

item_types.extend(toggable_items)

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
    
    contents: dict[str, int] | None = Field(default=None, description="A dictionary mapping item names to quantities, Only used for container items 'candy_bag' No other items should use this. To use this correctly, the string should be the item name and the int should be the quantity, crucially, a separate item should be created for each item in the container with the unique names referenced in the dictionary of the container item. I.E, if the container item is a 'candy_bag' and it contains 5 candies, then the dictionary should be {'candy': 5}, and a separate blueprint should be created for that 'candy' definition.")

    plant_type: str  |None =Field(default=None, description=f"Seeds Key: A string for the seed type, it should define the plant of seed this is for, from the valid options: {stringed_plant_types}")

    power_toggle: bool | None = Field(default=None, description=f"Optional Key: A boolean for the power toggle property of this item. List of the only item types that accept and require this key: {", ".join(toggable_items)}")

# --- Structure that contains a list of these item definitions ---
class ItemDefinitionListContainer(BaseModel):
    """
    A container model holding a list of item definitions.
    """
    items: List[ItemDefinition] = Field(description="A list of item definition objects.")


# --- Structure for memory package --- 

class UserMessage(BaseModel):
    """Represents a user message in the conversation."""
    type: Literal["user"]
    content: str


class AssistantMessage(BaseModel):
    """Represents an assistant message in the conversation."""
    type: Literal["assistant"]
    content: str


class ToolOutput(BaseModel):
    """Represents a tool execution output in the conversation."""
    type: Literal["tool_output"]
    call_id: Optional[str] = None
    content: str
    function_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None,
    thought_signature: Optional[str] = None



ConversationEntry = Annotated[
    Union[UserMessage, AssistantMessage, ToolOutput],
    Field(discriminator="type")
]


class StructuredMemory(BaseModel):
    """
    The structured memory representation output by construct_data().
    
    This format is agnostic and can be consumed by any LLM client.
    Contains system context (time, prompts, base memory, long-term memory)
    and chronologically ordered conversation history (user/assistant turns and tool outputs).
    """
    system_context: str = Field(
        ...,
        description="Combined system message containing timestamp, system prompt, base memory, and long-term memory entries"
    )
    
    conversation_history: List[ConversationEntry] = Field(
        default_factory=list,
        description="Chronologically ordered list of conversation turns and tool outputs"
    )
