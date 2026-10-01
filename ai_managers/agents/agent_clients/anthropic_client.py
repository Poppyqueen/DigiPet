# anthropic_client.py
# Suggested location: ai_managers/agents/agent_clients/anthropic_client.py

import re
import uuid
from typing import List, Dict, Any, Optional, Tuple

from anthropic import Anthropic

from ai_managers.agents.agent_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.agents.agents_utils.llm_response_types import LLMResponse, FunctionCallDetails
from utils.pydantic_models import StructuredMemory

DEFAULT_MAX_TOKENS = 16000

PLACEHOLDER_OPENING = (
    "A summarization process has been applied reorganizing your memory. You can now continue."
)
PLACEHOLDER_CLOSING = "Please continue."


class AnthropicClient(AbstractLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Anthropic client.

        Args:
            api_key: Optional API key. If None, the SDK reads ANTHROPIC_API_KEY from the environment.
        """
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    def _convert_tools_to_anthropic_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        OpenAI-style flat definition:
            {"type": "function", "name", "description", "parameters"}
        becomes Anthropic's:
            {"name", "description", "input_schema"}
        """
        converted = []
        for tool in tools or []:
            if not (tool.get("type") == "function" and "name" in tool and "description" in tool):
                print(f"Warning: Invalid tool format, skipping: {tool}")
                continue

            schema = tool.get("parameters") or {"type": "object", "properties": {}}
            if "type" not in schema:
                schema = {"type": "object", **schema}

            converted.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": schema,
            })
        return converted

    @staticmethod
    def _convert_tool_choice(tool_choice: str) -> Dict[str, Any]:
        """
        "auto"             -> {"type": "auto"}
        "none"             -> {"type": "none"}
        "any"/"required"   -> {"type": "any"}   (must call some tool)
        anything else      -> treated as a specific tool name
        """
        if tool_choice in (None, "auto"):
            return {"type": "auto"}
        if tool_choice == "none":
            return {"type": "none"}
        if tool_choice in ("any", "required"):
            return {"type": "any"}
        return {"type": "tool", "name": tool_choice}

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_call_id(call_id: Optional[str]) -> str:
        """Anthropic tool ids must match ^[a-zA-Z0-9_-]{1,64}$."""
        if call_id:
            cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", str(call_id))[:64]
            if cleaned:
                return cleaned
        return f"toolu_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def _append(messages: List[Dict[str, Any]], role: str, blocks: List[Dict[str, Any]]) -> None:
        """Append blocks, merging into the previous message if it has the same role."""
        if not blocks:
            return
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"].extend(blocks)
        else:
            messages.append({"role": role, "content": list(blocks)})

    def _normalize_anthropic_messages(
        self, memory: StructuredMemory
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Converts StructuredMemory into (messages, system_context) for Anthropic.

        - system_context goes to the top-level `system` parameter.
        - Each tool_batch becomes ONE assistant message holding all tool_use blocks,
          followed by ONE user message holding all tool_result blocks (matched by id).
        - Consecutive same-role entries are merged into one message.
        - The conversation must start with a user turn (placeholder inserted otherwise,
          e.g. after summarization pruned the opening user message) and must not end
          on an assistant turn.
        """
        data = memory.model_dump()
        system_context = data.get("system_context") or None
        messages: List[Dict[str, Any]] = []

        for entry in data.get("conversation_history", []):
            entry_type = entry.get("type")

            if entry_type in ("user", "assistant"):
                text = str(entry.get("content") or "")
                if not text.strip():
                    continue  # Anthropic rejects empty text blocks
                self._append(messages, entry_type, [{"type": "text", "text": text}])

            elif entry_type == "tool_batch":
                tool_uses = []
                tool_results = []
                for call in entry.get("calls", []):
                    call_id = self._clean_call_id(call.get("call_id"))
                    arguments = call.get("arguments")
                    if not isinstance(arguments, dict):
                        arguments = {}
                    result = str(call.get("result", "")) or "(no output)"

                    tool_uses.append({
                        "type": "tool_use",
                        "id": call_id,
                        "name": call.get("function_name"),
                        "input": arguments,
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": call_id,
                        "content": result,
                    })

                if tool_uses:
                    self._append(messages, "assistant", tool_uses)
                    self._append(messages, "user", tool_results)

            else:
                print(f"Warning: Skipping unknown message type '{entry_type}'.")

        if not messages or messages[0]["role"] != "user":
            if messages:
                print("Warning: Conversation history started with a model turn. Prepending a placeholder user message.")
            messages.insert(0, {"role": "user", "content": [{"type": "text", "text": PLACEHOLDER_OPENING}]})

        if messages[-1]["role"] == "assistant":
            messages.append({"role": "user", "content": [{"type": "text", "text": PLACEHOLDER_CLOSING}]})

        return messages, system_context

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    async def generate_response(
        self,
        messages: StructuredMemory,
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "claude-sonnet-5-5",
        tool_choice: str = "auto",
        **kwargs,
    ) -> LLMResponse:
        try:
            anthropic_messages, system_context = self._normalize_anthropic_messages(messages)

            settings: Dict[str, Any] = {
                "model": model,
                "max_tokens": DEFAULT_MAX_TOKENS,
                "messages": anthropic_messages,
            }
            if system_context:
                settings["system"] = system_context

            anthropic_tools = self._convert_tools_to_anthropic_format(tools) if tools else []
            if anthropic_tools:
                settings["tools"] = anthropic_tools
                settings["tool_choice"] = self._convert_tool_choice(tool_choice)

            # kwargs can override anything above (e.g. max_tokens, temperature)
            settings.update(kwargs)

            response = self.client.messages.create(**settings)

            normalized_function_calls: List[FunctionCallDetails] = []
            text_parts: List[str] = []

            for block in response.content:
                if block.type == "text" and block.text:
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    print(f"Function call name: {block.name}")
                    normalized_function_calls.append(
                        FunctionCallDetails(
                            name=block.name,
                            arguments=dict(block.input) if block.input else {},
                            call_id=block.id,
                        )
                    )

            text_content = "\n".join(text_parts).strip()

            return LLMResponse(
                function_calls=normalized_function_calls if normalized_function_calls else None,
                text_content=text_content if text_content else None,
            )

        except Exception as e:
            print(f"Error calling Anthropic API: {e}")
            return LLMResponse(text_content=f"Error communicating with Anthropic API: {e}")