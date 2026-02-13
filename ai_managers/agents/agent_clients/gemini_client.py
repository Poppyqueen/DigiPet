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
        
        # *** NEW SAFETY CHECK FOR INVALID CONVERSATION START ***
        if conversation_history and conversation_history[0].get("type") in ["assistant", "tool_output"]:
            print("Warning: Conversation history started with a model action due to summarization. Prepending a placeholder user message to ensure API compatibility.")
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


            elif original_type == "tool_output":
                model_call_parts = []
                tool_response_parts = []
                
                tool_msg_index = i
                while tool_msg_index < len(conversation_history) and \
                    conversation_history[tool_msg_index].get("type") == "tool_output":
                    
                    tool_msg = conversation_history[tool_msg_index]
                    content_data = tool_msg.get("content")

                    # 1. FIX: Initialize thought_signature to None
                    function_name, arguments, result, call_id, thought_signature = None, None, None, None, None

                    # Robustly parse both nested and flat tool_output formats
                    if isinstance(content_data, dict) and "function_name" in content_data:
                        function_name = content_data.get("function_name")
                        arguments = content_data.get("arguments", {})
                        result = content_data.get("result", "")
                        call_id = content_data.get("call_id")
                        # 2. FIX: Extract thought_signature from the content dictionary
                        thought_signature = content_data.get("thought_signature") 

                    elif "function_name" in tool_msg:
                        function_name = tool_msg.get("function_name")
                        arguments = tool_msg.get("arguments", {})
                        result = str(content_data)
                        call_id = tool_msg.get("call_id")
                        # 3. FIX: Extract thought_signature from the message level if it exists there
                        thought_signature = tool_msg.get("thought_signature")

                    if function_name is not None:
                        # Build FunctionCall (WITHOUT thought_signature)
                        fc_kwargs = {"name": function_name, "args": arguments or {}}
                        if call_id:
                            fc_kwargs["id"] = call_id
                        
                        fn_call_obj = types.FunctionCall(**fc_kwargs)

                        # Build Part (WITH thought_signature)
                        part_kwargs = {"function_call": fn_call_obj}
                        
                        # 4. FIX: Handle the extracted signature (Decode Base64 -> Bytes)
                        if thought_signature:
                            try:
                                # Check if it's a string (it should be, from JSON) and decode
                                if isinstance(thought_signature, str):
                                    decoded_sig = base64.b64decode(thought_signature)
                                    part_kwargs["thought_signature"] = decoded_sig
                                else:
                                    part_kwargs["thought_signature"] = thought_signature
                            except Exception as e:
                                print(f"Warning: Could not decode thought_signature, sending as is. Error: {e}")
                                part_kwargs["thought_signature"] = thought_signature
                        
                        model_call_parts.append(
                            types.Part(**part_kwargs)
                        )
                        
                        # Build FunctionResponse
                        fr_kwargs = {"name": function_name, "response": {"result": str(result)}}
                        if call_id:
                            fr_kwargs["id"] = call_id
                        
                        tool_response_parts.append(
                            types.Part(function_response=types.FunctionResponse(**fr_kwargs))
                        )
                    else:
                        print(f"Warning: Skipping malformed 'tool_output' message: {tool_msg}")

                    tool_msg_index += 1
                
                if model_call_parts:
                    gemini_contents.append({"role": "model", "parts": model_call_parts})
                    gemini_contents.append({"role": "user", "parts": tool_response_parts})

                i = tool_msg_index
            
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