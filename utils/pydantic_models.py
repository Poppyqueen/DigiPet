# pydantic_models.py
from __future__ import annotations

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


class ToolBatchCall(BaseModel):
    """
    A single tool call and its result within a batch.
    Mirrors the function_array dict produced by ai_handle.ai_response().
    """
    function_name: str
    arguments: Dict[str, Any]
    result: str
    call_id: Optional[str] = None
    thought_signature: Optional[str] = None  # Gemini extended-thinking only


class ToolBatch(BaseModel):
    """
    Represents all tool calls issued by the LLM in a single inference step.

    A single tool call is represented as a batch of one.  This uniform
    structure means every client has exactly one branch to handle tool
    history — no ToolOutput vs ToolBatch split.

    The shared timestamp on the parent memory entry guarantees all calls
    in a batch are emitted consecutively by construct_data, so clients
    receive them in the exact order and grouping the LLM produced them.
    """
    type: Literal["tool_batch"]
    calls: List[ToolBatchCall]


ConversationEntry = Annotated[
    Union[UserMessage, AssistantMessage, ToolBatch],
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