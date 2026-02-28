from openai import OpenAI
from ai_managers.agents.agent_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.agents.agents_utils.llm_response_types import LLMResponse, FunctionCallDetails
from typing import List, Dict, Any, Optional
import json
from utils.pydantic_models import StructuredMemory


class OpenRouterClient(AbstractLLMClient):
    def __init__(self, api_key: str, http_referer: Optional[str] = None, x_title: Optional[str] = None):
        """
        Initialize the OpenRouter client.

        Args:
            api_key: Your OpenRouter API key.
            http_referer: Optional. Your site URL, for rankings on openrouter.ai.
            x_title: Optional. Your app name, for rankings on openrouter.ai.
        """
        default_headers = {}
        if http_referer:
            default_headers["HTTP-Referer"] = http_referer
        if x_title:
            default_headers["X-Title"] = x_title

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers=default_headers if default_headers else None,
        )

    def _transform_function_structure(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms a flat Responses API tool definition into the Chat Completions
        nested format expected by OpenRouter.

        Input:  {"type": "function", "name": ..., "description": ..., "parameters": ...}
        Output: {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
        """
        if "function" in input_dict:
            return input_dict  # Already in the correct format

        required_keys = ["type", "name", "description", "parameters"]
        if not all(key in input_dict for key in required_keys):
            raise ValueError(f"Tool definition is missing one or more required keys: {required_keys}")

        return {
            "type": input_dict["type"],
            "function": {
                "name": input_dict["name"],
                "description": input_dict["description"],
                "parameters": input_dict["parameters"],
            },
        }

    def _process_functions_list(self, functions_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize a list of tool definitions to Chat Completions format."""
        return [self._transform_function_structure(fn) for fn in functions_list]

    async def generate_response(
        self,
        messages: StructuredMemory,
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "google/gemini-2.0-flash-001",  # Default OpenRouter model
        tool_choice: str = "auto",
        **kwargs
    ) -> LLMResponse:

        messages_dict = messages.model_dump()
        l_messages = []

        # 1. System message
        if messages_dict.get("system_context"):
            l_messages.append({
                "role": "system",
                "content": messages_dict["system_context"]
            })

        # 2. Conversation history
        for entry in messages_dict.get("conversation_history", []):
            if entry["type"] == "user":
                l_messages.append({"role": "user", "content": entry["content"]})

            elif entry["type"] == "assistant":
                l_messages.append({"role": "assistant", "content": entry["content"]})

            elif entry["type"] == "tool_output":
                # In the chat completions format, a tool call round-trip is:
                #   1. assistant message with tool_calls array
                #   2. tool message with the result
                #
                # We inject the assistant stub only if the previous message isn't
                # already an assistant message that carries this call_id.
                call_id = entry.get("call_id")
                function_name = entry.get("function_name")
                arguments = entry.get("arguments", {})

                # Check if the last message already covers this tool call
                already_has_stub = (
                    l_messages
                    and l_messages[-1].get("role") == "assistant"
                    and any(
                        tc.get("id") == call_id
                        for tc in l_messages[-1].get("tool_calls", [])
                    )
                )

                if not already_has_stub:
                    l_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": json.dumps(arguments) if isinstance(arguments, dict) else str(arguments),
                                },
                            }
                        ],
                    })

                l_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": str(entry["content"]),
                })

        settings = {
            "model": model,
            "messages": l_messages,
            # "tools": self._process_functions_list(tools),
            # "tool_choice": tool_choice,
            #"tool_choice": "none"
        }
        if tools and tool_choice != "none":
            settings["tools"] = self._process_functions_list(tools)
            settings["tool_choice"] = tool_choice
        else:
            l_messages.append({
                "role": "system",
                "content": "Last turn for round, please do not use any tools and wait for the next autonomous action."
            })

        settings.update(kwargs)

        try:
            openrouter_response = self.client.chat.completions.create(**settings)
        except Exception as e:
            print(f"Error calling OpenRouter API: {e}")
            return LLMResponse(text_content=f"Error communicating with OpenRouter: {e}")

        # --- Normalize response into LLMResponse ---
        normalized_function_calls: List[FunctionCallDetails] = []
        normalized_text_content: Optional[str] = None

        choice = openrouter_response.choices[0]
        message = choice.message

        # Text content
        if message.content:
            normalized_text_content = message.content

        # Tool / function calls
        if message.tool_calls:
            for tool_call in message.tool_calls:
                try:
                    parsed_args = json.loads(tool_call.function.arguments)
                    normalized_function_calls.append(
                        FunctionCallDetails(
                            name=tool_call.function.name,
                            arguments=parsed_args,
                            call_id=tool_call.id,
                        )
                    )
                except json.JSONDecodeError as e:
                    print(f"Error parsing function arguments from OpenRouter response: {e}")
                except Exception as e:
                    print(f"Unexpected error processing OpenRouter tool call: {e}")

        return LLMResponse(
            function_calls=normalized_function_calls if normalized_function_calls else None,
            text_content=normalized_text_content if normalized_text_content else None,
        )