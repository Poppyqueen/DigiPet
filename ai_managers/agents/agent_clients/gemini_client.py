# gemini_client.py

from google import genai
from google.genai import types
from ai_managers.agents.agent_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.agents.agents_utils.llm_response_types import LLMResponse, FunctionCallDetails
from typing import List, Dict, Any, Optional

from utils.pydantic_models import StructuredMemory

import uuid

import base64

class GeminiClient(AbstractLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Optional API key for authentication. If None, relies on default credentials.
        """
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()


    # # You must also adapt the _merge_consecutive_messages to be more careful.
    # # It should ONLY merge simple text messages.
    # def _merge_consecutive_messages(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    #     if not history:
    #         return []

    #     merged_history = [history[0]]

    #     for msg in history[1:]:
    #         last_msg = merged_history[-1]
            
    #         # This condition is now more strict and correct.
    #         # It only merges if BOTH are simple text content messages of the same type.
    #         if msg.get("type") == last_msg.get("type") and \
    #         msg["type"] in ["user", "assistant"] and \
    #         isinstance(msg.get("content"), str) and \
    #         isinstance(last_msg.get("content"), str) and \
    #         "function_name" not in msg and "function_name" not in last_msg: # Ensure they are not function calls/responses
                
    #             last_msg["content"] += "\n" + msg["content"]
    #         else:
    #             merged_history.append(msg)
                
    #     return merged_history

    def _convert_schema_dict_to_gemini(self, schema_dict: dict, context: str = "") -> types.Schema | None:
        """Recursively converts a JSON Schema dict to a types.Schema object."""
        kwargs = {}

        type_str = schema_dict.get("type")
        if type_str:
            if isinstance(type_str, list):
                type_str = next((t for t in type_str if t != "null"), None)
                kwargs["nullable"] = True
            try:
                kwargs["type"] = getattr(types.Type, type_str.upper())
            except AttributeError:
                print(f"Warning: Invalid type '{type_str}' in schema at {context}. Skipping.")
                return None

        if "description" in schema_dict:
            kwargs["description"] = schema_dict["description"]

        if "enum" in schema_dict:
            kwargs["enum"] = schema_dict["enum"]

        if "format" in schema_dict:
            kwargs["format"] = schema_dict["format"]

        # ✅ Recursively convert `items` (for ARRAY types)
        if "items" in schema_dict:
            nested = self._convert_schema_dict_to_gemini(schema_dict["items"], context=f"{context}.items")
            if nested:
                kwargs["items"] = nested

        # ✅ Recursively convert `properties` (for nested OBJECTs)
        if "properties" in schema_dict:
            props = {}
            for prop_name, prop_details in schema_dict["properties"].items():
                nested = self._convert_schema_dict_to_gemini(prop_details, context=f"{context}.{prop_name}")
                if nested:
                    props[prop_name] = nested
            kwargs["properties"] = props

        if "required" in schema_dict:
            kwargs["required"] = schema_dict["required"]

        return types.Schema(**kwargs)
        
    def _convert_tools_to_gemini_format(self, tools: List[Dict[str, Any]]) -> List[types.Tool]:
        if not tools:
            return []

        gemini_function_declarations = []
        for tool in tools:
            if not (tool.get("type") == "function" and
                    "name" in tool and "description" in tool and "parameters" in tool):
                print(f"Warning: Invalid tool format, skipping: {tool}")
                continue

            parameters_schema = self._convert_schema_dict_to_gemini(
                tool["parameters"], context=tool["name"]
            )
            if parameters_schema is None:
                print(f"Warning: Could not build parameters schema for tool '{tool['name']}', skipping.")
                continue

            gemini_function_declarations.append(types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=parameters_schema,
            ))

        return [types.Tool(function_declarations=gemini_function_declarations)] if gemini_function_declarations else []



    def _normalize_gemini_messages(self, messages: StructuredMemory, tools_state) -> List[Dict[str, Any]]:
        """
        Normalizes our memory format to Gemini's expected content format.
        
        This version is robust and handles two different 'tool_output' formats.
        
        CRITICAL FIX: It also checks if the conversation history begins with a model
        action (assistant or tool_output), which is invalid for the API. This can
        happen after summarization purges the original user prompt. If so, it
        prepends a placeholder user message to ensure the conversation is valid.
        """

        # Convert the StructuredMemory to a dictionary
        messages = messages.model_dump()

        gemini_contents = []

        system_context = messages.get("system_context")
        if tools_state == "NONE":
            system_context = (system_context or "") + "\nPlease output a textual and narrative message without any more function calls to close the latest round of actions. Make sure to not include any more function calls as they will be ignored."

        conversation_history = messages.get("conversation_history", [])
        
        # *** SAFETY CHECK: conversation must not start with a model-side turn ***
        # After memory summarization the oldest user message may have been pruned,
        # leaving a tool_batch or assistant message at the front.  Gemini rejects
        # conversations that don't start with a user turn.
        if conversation_history and conversation_history[0].get("type") in ["assistant", "tool_batch"]:
            print("Warning: Conversation history started with a model action due to summarization. Prepending a placeholder user message.")
            placeholder_message = {
                "type": "user",
                "content": "A summarization process has been applied reorganizing your memory. You can now continue."
            }
            conversation_history.insert(0, placeholder_message)

        i = 0
        while i < len(conversation_history):
            msg = conversation_history[i]
            original_type = msg.get("type")

            if original_type == "user":
                gemini_contents.append({
                    "role": "user",
                    "parts": [types.Part(text=str(msg.get("content")))]
                })
                i += 1

            elif original_type == "assistant":
                gemini_contents.append({
                    "role": "model",
                    "parts": [types.Part(text=str(msg.get("content")))]
                })
                i += 1


            elif original_type == "tool_batch":
                # Build exactly one model turn (all FunctionCall parts) and one user
                # turn (all FunctionResponse parts) from the batch.  This matches the
                # Gemini wire format requirement: calls and responses must be grouped
                # by inference turn, not listed individually.
                model_call_parts = []
                tool_response_parts = []

                for call in msg.get("calls", []):
                    call_id          = call.get("call_id") or str(uuid.uuid4())
                    function_name    = call.get("function_name")
                    arguments        = call.get("arguments", {})
                    result           = call.get("result", "")
                    thought_signature = call.get("thought_signature")

                    # ── FunctionCall part (goes into the model turn) ──────────
                    fc_kwargs = {"name": function_name, "args": arguments}
                    if call_id:
                        fc_kwargs["id"] = call_id
                    fn_call_obj = types.FunctionCall(**fc_kwargs)

                    part_kwargs = {"function_call": fn_call_obj}
                    if thought_signature:
                        try:
                            decoded_sig = base64.b64decode(thought_signature) \
                                          if isinstance(thought_signature, str) \
                                          else thought_signature
                            part_kwargs["thought_signature"] = decoded_sig
                        except Exception as e:
                            print(f"Warning: could not decode thought_signature: {e}")
                            part_kwargs["thought_signature"] = thought_signature
                    model_call_parts.append(types.Part(**part_kwargs))

                    # ── FunctionResponse part (goes into the user turn) ───────
                    fr_kwargs = {"name": function_name, "response": {"result": str(result)}}
                    if call_id:
                        fr_kwargs["id"] = call_id
                    tool_response_parts.append(
                        types.Part(function_response=types.FunctionResponse(**fr_kwargs))
                    )

                if model_call_parts:
                    gemini_contents.append({"role": "model", "parts": model_call_parts})
                    gemini_contents.append({"role": "user",  "parts": tool_response_parts})

                i += 1
            
            else:
                print(f"Warning: Skipping unknown message type '{original_type}'.")
                i += 1
            
        return gemini_contents, system_context

    def sanitize_function_name(self, name): # Gemini function responses sometimes have a "default_api:" prefix. Random behavior.
        if name.startswith("default_api:"):
            return name.replace("default_api:", "")
        return name

    # The rest of GeminiClient class is the same:

    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "gemini-2.5-flash",
        tool_choice: str = "auto",
        **kwargs
    ) -> LLMResponse:
        try:
            if tool_choice == "auto":
                tools_state = "AUTO"
            else:
                tools_state = "NONE"

            gemini_tools = self._convert_tools_to_gemini_format(tools) if tools else []
            gemini_contents, system_context = self._normalize_gemini_messages(messages, tools_state)

            tool_config = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=tools_state
                )
            )
            
            if tools_state == "AUTO":
                config = types.GenerateContentConfig(
                    tools=gemini_tools,
                    tool_config=tool_config,
                    system_instruction=system_context
                )
            else:
                config = types.GenerateContentConfig(
                    tool_config=tool_config,
                    system_instruction=system_context
                )

            response = self.client.models.generate_content(
                model=model,
                contents=gemini_contents,
                config=config            
            )
            
            normalized_function_calls: List[FunctionCallDetails] = []
            normalized_text_content: Optional[str] = None

            if response.candidates and response.candidates[0].content:
                candidate_content = response.candidates[0].content
                all_text_parts = []

                # ... inside the loop ...
                for part in candidate_content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_call = part.function_call
                        call_id = function_call.id if (hasattr(function_call, 'id') and function_call.id) else str(uuid.uuid4())
                        
                        # 1. Get the raw object (likely bytes)
                        raw_signature = getattr(part, 'thought_signature', None)
                        
                        # 2. Check if it is bytes and Convert to Base64 String
                        final_signature = None
                        if raw_signature:
                            if isinstance(raw_signature, bytes):
                                # Convert bytes -> Base64 Bytes -> UTF-8 String
                                final_signature = base64.b64encode(raw_signature).decode('utf-8')
                            else:
                                # It might already be a string (depending on SDK version), keep as is
                                final_signature = raw_signature

                        print(f"Function call name: {function_call.name}")
                        # print(f"Encoded Signature: {final_signature}") 

                        normalized_function_calls.append(
                            FunctionCallDetails(
                                name=self.sanitize_function_name(function_call.name),
                                arguments=dict(function_call.args),
                                call_id=call_id,
                                thought_signature=final_signature # Now safe for JSON
                            )
                        )
                    elif hasattr(part, 'text') and part.text:
                        all_text_parts.append(part.text)
                
                if all_text_parts:
                    normalized_text_content = "\n".join(all_text_parts).strip()

            return LLMResponse(
                function_calls=normalized_function_calls if normalized_function_calls else None,
                text_content=normalized_text_content if normalized_text_content else None
            )

        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return LLMResponse(text_content=f"Error communicating with Gemini API: {e}")