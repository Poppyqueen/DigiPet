# pydantic_models.py
from typing import List
from pydantic import BaseModel

from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any, Literal, Annotated

# TODO: Memory structures, probably move them to the memory manager at some point

class characteristic_structure(BaseModel):
    messages_sources_ids: List[str] = Field(description="A list of IDs from the message where this specific characteristic for the entity is mentioned or extracted from.")
    characteristic: str = Field(description="The distinguishable intrinsic characteristic or propertie of this entity, I.E, colors, shapes, materials, sensations, interests, etc. You have to directly write the characteristics identified as an individual")

class entity_dict(BaseModel):
    named_entity: str = Field(description="The entity identified in the memory structure")
    characteristics: List[characteristic_structure] = Field(description="A list of  distinguishable intrinsic characteristics or properties of this entity")

class save_ner_structure(BaseModel):
    entities: List[entity_dict] = Field(description="A collection of important identified entities in memory, accompanied by their intrinsic characteristics and specific information recognized and the messages ID sources for the origins of these qualities and details extracted.")



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
