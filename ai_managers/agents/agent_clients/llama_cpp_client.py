# llama_cpp_client.py

from openai import OpenAI
from ai_managers.agents.agent_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.agents.agents_utils.llm_response_types import LLMResponse, FunctionCallDetails
from typing import List, Dict, Any, Optional
import json
from utils.pydantic_models import StructuredMemory


class LlamaCppClient(AbstractLLMClient):
    def __init__(self, api_key: str = "not-needed"):
        self.client = OpenAI(
            base_url="http://localhost:8080/v1", # TODO: Make this configurable?
            api_key=api_key,  # llama.cpp ignores this but the SDK requires it
        )

    @staticmethod
    def _normalize_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert flat tool format to OpenAI chat completions format."""
        normalized = []
        for tool in tools:
            if tool.get("type") == "function" and "function" not in tool:
                # Flat format — wrap it
                normalized.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })
            else:
                # Already in the right format, pass through
                normalized.append(tool)
        return normalized

    async def generate_response(
        self,
        messages: StructuredMemory,
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "local-model",  # llama.cpp ignores this too, but required by SDK
        tool_choice: str = "auto",
        **kwargs
    ) -> LLMResponse:

        data = messages.model_dump()
        l_messages = []

        # System message — llama.cpp supports "system" role fine
        if data.get("system_context"):
            l_messages.append({
                "role": "system",
                "content": data["system_context"]
            })

        # Conversation history
        for entry in data.get("conversation_history", []):
            if entry["type"] == "user":
                l_messages.append({"role": "user", "content": entry["content"]})

            elif entry["type"] == "assistant":
                l_messages.append({"role": "assistant", "content": entry["content"]})

            elif entry["type"] == "tool_output":
                # Chat completions tool call format:
                # 1. assistant message with tool_calls
                # 2. tool message with the result
                l_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": entry["call_id"],
                        "type": "function",
                        "function": {
                            "name": entry["function_name"],
                            "arguments": json.dumps(entry["arguments"])
                                if isinstance(entry["arguments"], dict)
                                else entry["arguments"]
                        }
                    }]
                })
                l_messages.append({
                    "role": "tool",
                    "tool_call_id": entry["call_id"],
                    "content": str(entry["content"])
                })

        settings = {
            "model": model,
            "messages": l_messages,
        }
        if tools and tool_choice != "none":
            settings["tools"] = self._normalize_tools(tools)
            settings["tool_choice"] = tool_choice

        if tool_choice == "none":
            l_messages.append({
                "role": "system",
                "content": "Last turn for round, please do not use any tools and wait for the next autonomous action. Output a natural language response without using any tools."
            })

        settings.update(kwargs)

        try:
            response = self.client.chat.completions.create(**settings)
        except Exception as e:
            print(f"Error calling llama.cpp API: {e}")
            return LLMResponse(text_content=f"Error communicating with llama.cpp: {e}")

        # Normalize response
        normalized_function_calls: List[FunctionCallDetails] = []
        normalized_text_content: Optional[str] = None

        choice = response.choices[0].message if response.choices else None
        if choice:
            if choice.content:
                normalized_text_content = choice.content

            if choice.tool_calls:
                for tc in choice.tool_calls:
                    try:
                        parsed_args = json.loads(tc.function.arguments)
                        normalized_function_calls.append(
                            FunctionCallDetails(
                                name=tc.function.name,
                                arguments=parsed_args,
                                call_id=tc.id
                            )
                        )
                    except json.JSONDecodeError as e:
                        print(f"Error parsing tool call arguments: {e}")

        return LLMResponse(
            function_calls=normalized_function_calls if normalized_function_calls else None,
            text_content=normalized_text_content if normalized_text_content else None
        )