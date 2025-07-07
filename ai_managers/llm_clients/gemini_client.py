# gemini_client.py

from google import genai
from google.genai import types
from ai_managers.llm_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.llm_clients.llm_response_types import LLMResponse, FunctionCallDetails
from typing import List, Dict, Any, Optional

class GeminiClient(AbstractLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Optional API key for authentication. If None, relies on default credentials.
        """
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

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
        Normalizes our structured memory format (from construct_data) to Gemini's expected content format.
        This method is now more of a 'final stage conversion' from our structured internal format.
        """
        gemini_contents = []

        

        # Handle the system_context as an initial 'user' message
        system_context = messages.get("system_context")

        if tools_state == "NONE":
            system_context  = system_context + "Please output a textual and narrative message without any more function calls to close the latest round of actions. Make sure to not include any more function calls as they will be ignored."
        # if system_context:
        #     gemini_contents.append({
        #         "role": "user",
        #         "parts": [types.Part(text=system_context)]
        #     })

        # Process conversation_history
        conversation_history = messages.get("conversation_history", [])
        for msg in conversation_history:
            original_type = msg.get("type")
            content = msg.get("content")

            gemini_role = "user"  # Default for unknown or user messages
            gemini_parts = []
            gemini_requests = []

            if original_type == "user":
                gemini_role = "user"
                gemini_parts.append(types.Part(text=str(content)))
            elif original_type == "assistant":
                gemini_role = "model"
                # Filter out internal error messages if they are present in assistant content
                if isinstance(content, str) and "Error communicating with" in content:
                    print(f"DEBUG: Filtering out internal error message from history: {content[:100]}...")
                    continue # Skip this message entirely if it's an error
                gemini_parts.append(types.Part(text=str(content)))
            elif original_type == "tool_output":
                gemini_role = "user" # Tool responses are sent from the 'user' role

                # --- FIX STARTS HERE ---
                # Retrieve function_name, arguments, and the result (which is in 'content')
                # directly from the 'msg' dictionary, as populated by construct_data.
                function_name = msg.get("function_name")
                function_args = msg.get("arguments", {})
                function_id = msg.get("call_id")
                function_result_content = msg.get("content") # This is the result string from construct_data

                if function_name:
                    # This is a tool output representing a function call result.
                    # Gemini expects the original function_call to be reiterated by the user
                    # along with the function_response in the same turn.
                    gemini_requests.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                name=function_name,
                                args=function_args, # These are the arguments used in the original call
                                id=function_id
                                       
                            )
                        )
                    )

                    gemini_contents.append({
                    "role": "model",
                    "parts": gemini_requests
                })

                    # Ensure function_result_content is structured as a dictionary for types.FunctionResponse.
                    # Gemini's `response` field expects a dictionary.
                    # We wrap the string content from construct_data into a dictionary.
                    if not isinstance(function_result_content, dict):
                        function_result_content = {"result": str(function_result_content)}

                    gemini_parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=function_name,
                                response=function_result_content,
                                id=function_id
                            )
                        )
                    )
                else:
                    # This is a 'tool_output' that is not associated with a specific function_name,
                    # likely a plain string system message from construct_data.
                    # Gemini doesn't have a direct 'system' role for intermediate messages.
                    # The most appropriate fallback is to treat it as a user text message.
                    if function_result_content: # Ensure there's actual content to add
                        gemini_parts.append(types.Part(text=str(function_result_content)))
                    else:
                        print(f"Warning: Tool output message of type 'plain string' had no content. Skipping.")
                        continue # Skip if no content and not a function call response
                # --- FIX ENDS HERE ---

            else:
                print(f"Warning: Unrecognized message type in conversation history: {original_type}. Skipping message.")
                continue

            if gemini_parts:  # Only add if there are actual parts to avoid empty content blocks
                gemini_contents.append({
                    "role": gemini_role,
                    "parts": gemini_parts
                })

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

            print(f"DEBUG: Gemini contents sent: {gemini_contents}")
            print(f"DEBUG: Gemini tools sent: {gemini_tools}")


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
                    print(f"📮📮📮📮📮📮Normalized Text Content: {normalized_text_content}")

            return LLMResponse(
                function_calls=normalized_function_calls if normalized_function_calls else None,
                text_content=normalized_text_content if normalized_text_content else None
            )

        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return LLMResponse(text_content=f"Error communicating with Gemini API: {e}")