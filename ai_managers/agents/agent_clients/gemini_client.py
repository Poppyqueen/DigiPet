# gemini_client.py

from google import genai
from google.genai import types
from ai_managers.agents.agent_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.agents.agents_utils.llm_response_types import LLMResponse, FunctionCallDetails
from typing import List, Dict, Any, Optional

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

    def _convert_tools_to_gemini_format(self, tools: List[Dict[str, Any]]) -> List[types.Tool]:
        """
        Converts tools from our format to Gemini's expected format by explicitly
        constructing types.Tool, types.FunctionDeclaration, and types.Schema objects.
        """
        if not tools:
            return []
        
        gemini_function_declarations = []
        for tool in tools:
            if tool.get("type") == "function" and \
               "name" in tool and \
               "description" in tool and \
               "parameters" in tool:
                
                tool_parameters_dict = tool["parameters"].copy()
                schema_kwargs = {}

                param_type_str = tool_parameters_dict.get("type", "object")
                try:
                    schema_kwargs["type"] = getattr(types.Type, param_type_str.upper())
                except AttributeError:
                    print(f"Warning: Invalid 'type' '{param_type_str}' for tool '{tool['name']}' parameters. Defaulting to OBJECT.")
                    schema_kwargs["type"] = types.Type.OBJECT

                if "properties" in tool_parameters_dict:
                    properties_for_schema = {}
                    for prop_name, prop_details in tool_parameters_dict["properties"].items():
                        prop_schema_kwargs = {}
                        prop_type_str = prop_details.get("type")
                        if prop_type_str:
                            try:
                                prop_schema_kwargs["type"] = getattr(types.Type, prop_type_str.upper())
                            except AttributeError:
                                print(f"Warning: Invalid 'type' '{prop_type_str}' for property '{prop_name}' in tool '{tool['name']}'. Skipping property.")
                                continue
                        if "description" in prop_details:
                            prop_schema_kwargs["description"] = prop_details["description"]
                        
                        # Add other simple JSON Schema properties like enum, format, etc.
                        for key_prop in ['enum', 'format', 'items', 'minimum', 'maximum', 'min_length', 'max_length', 'pattern', 'default', 'title', 'example']:
                            if key_prop in prop_details:
                                prop_schema_kwargs[key_prop] = prop_details[key_prop]

                        properties_for_schema[prop_name] = types.Schema(**prop_schema_kwargs)
                    schema_kwargs["properties"] = properties_for_schema

                if "required" in tool_parameters_dict:
                    schema_kwargs["required"] = tool_parameters_dict["required"]

                try:
                    gemini_parameters_schema = types.Schema(**schema_kwargs)
                except Exception as e:
                    print(f"Error creating Gemini Schema for tool {tool['name']}: {e}. Schema arguments tried: {schema_kwargs}")
                    continue
                
                gemini_function_declaration = types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=gemini_parameters_schema
                )
                gemini_function_declarations.append(gemini_function_declaration)
            else:
                print(f"Warning: Invalid tool format, skipping: {tool}")
        
        return [types.Tool(function_declarations=gemini_function_declarations)] if gemini_function_declarations else []



    def _normalize_gemini_messages(self, messages: Dict[str, Any], tools_state) -> List[Dict[str, Any]]:
        """
        Normalizes our memory format to Gemini's expected content format.
        
        This version is robust and handles two different 'tool_output' formats.
        
        CRITICAL FIX: It also checks if the conversation history begins with a model
        action (assistant or tool_output), which is invalid for the API. This can
        happen after summarization purges the original user prompt. If so, it
        prepends a placeholder user message to ensure the conversation is valid.
        """
        gemini_contents = []

        system_context = messages.get("system_context")
        if tools_state == "NONE":
            system_context = (system_context or "") + "\nPlease output a textual and narrative message without any more function calls to close the latest round of actions. Make sure to not include any more function calls as they will be ignored."

        conversation_history = messages.get("conversation_history", [])
        
        #conversation_history = self._merge_consecutive_messages(conversation_history)

        # *** NEW SAFETY CHECK FOR INVALID CONVERSATION START ***
        if conversation_history and conversation_history[0].get("type") in ["assistant", "tool_output"]:
            # This is an invalid start for the Gemini API. Prepend a placeholder user message.
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

                    function_name, arguments, result = None, None, None

                    # Robustly parse both nested and flat tool_output formats
                    if isinstance(content_data, dict) and "function_name" in content_data:
                        function_name = content_data.get("function_name")
                        arguments = content_data.get("arguments", {})
                        result = content_data.get("result", "")
                    elif "function_name" in tool_msg:
                        function_name = tool_msg.get("function_name")
                        arguments = tool_msg.get("arguments", {})
                        result = str(content_data)

                    if function_name is not None:
                        model_call_parts.append(
                            types.Part(function_call=types.FunctionCall(name=function_name, args=arguments or {}))
                        )
                        tool_response_parts.append(
                            types.Part(function_response=types.FunctionResponse(name=function_name, response={"result": str(result)}))
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
                tools_state="AUTO"
            else:
                tools_state="NONE"

            gemini_tools = self._convert_tools_to_gemini_format(tools) if tools else []
            gemini_contents, system_context = self._normalize_gemini_messages(messages, tools_state)

            # print(f"DEBUG: Gemini contents sent: {gemini_contents}")
            # print(f"DEBUG: Gemini tools sent: {gemini_tools}")


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
                    system_instruction=system_context

                )

            response = self.client.models.generate_content(
                model=model,
                contents=gemini_contents,
                config=config            
                )
            
            #print(f"📮📮📮📮📮📮Raw Gemini response: {response}")

            normalized_function_calls: List[FunctionCallDetails] = []
            normalized_text_content: Optional[str] = None

            if response.candidates and response.candidates[0].content:
                candidate_content = response.candidates[0].content
                all_text_parts = []
                for part in candidate_content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_call = part.function_call
                        # print(f"📮📮📮📮📮📮Function full: {function_call}")

                        # print(f"📮📮📮📮📮📮Function call name: {function_call.name}")

                        # print(f"📮📮📮📮📮📮Function call ID: {function_call.id}")
                        normalized_function_calls.append(
                            FunctionCallDetails(
                                name=function_call.name,
                                arguments=dict(function_call.args),
                                call_id=function_call.id
                            )
                        )
                    elif hasattr(part, 'text') and part.text:
                        all_text_parts.append(part.text)
                
                if all_text_parts:
                    normalized_text_content = "\n".join(all_text_parts).strip()
                    #print(f"📮📮📮📮📮📮Normalized Text Content: {normalized_text_content}")

            return LLMResponse(
                function_calls=normalized_function_calls if normalized_function_calls else None,
                text_content=normalized_text_content if normalized_text_content else None
            )

        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return LLMResponse(text_content=f"Error communicating with Gemini API: {e}")