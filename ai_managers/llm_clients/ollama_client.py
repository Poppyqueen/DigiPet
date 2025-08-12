# ollama client

import ollama
from ai_managers.llm_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.llm_clients.llm_response_types import LLMResponse, FunctionCallDetails
from typing import List, Dict, Any, Optional
import json # For parsing arguments from OpenAI's string format (retained as per original code, though not used here now)


class OllamaClient(AbstractLLMClient):
    """
    Client for interacting with Ollama models.
    Inherits from AbstractLLMClient to provide a standardized interface for LLM operations.
    """
    def __init__(self, selected_key=None): # Make sure to pass api_key here
        """
        Initializes the OllamaClient.
        'selected_key' is included for potential future API key requirements,
        though Ollama typically runs locally without one.
        """
        # DEBUG: Confirming OllamaClient initialization.
        # print("DEBUG: OllamaClient initialized.")
        pass

    @staticmethod
    def transform_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transforms a list of tool definitions from a generic format
        to the specific nested 'function' format required by Ollama for tool calling.

        Input format for each tool:
        {
          "type": "function",
          "name": "sleep",
          "description": "Sleep for a given amount of seconds.",
          "parameters": { ... }
        }

        Output format for each tool:
        {
          "type": "function",
          "function": {
            "name": "sleep",
            "description": "Sleep for a given amount of seconds.",
            "parameters": { ... }
          }
        }

        Args:
            tools (List[Dict[str, Any]]): A list of tool definitions in the input format.

        Returns:
            List[Dict[str, Any]]: A list of tool definitions transformed into Ollama's expected format.
        """
        transformed_tools = []
        # DEBUG: Starting tool transformation process. Incoming tools count: {len(tools)}
        # print(f"DEBUG: transform_tools: Starting transformation for {len(tools)} tools.")
        for tool in tools:
            # DEBUG: Processing tool: {json.dumps(tool, indent=2)}
            # print(f"DEBUG: transform_tools: Processing tool named '{tool.get('name', 'UNKNOWN')}'.")
            if tool.get("type") == "function":
                # Construct the nested 'function' dictionary as required by Ollama.
                transformed_tool = {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""), # description might be optional
                        "parameters": tool["parameters"]
                    }
                }
                transformed_tools.append(transformed_tool)
                # print(f"DEBUG: transform_tools: Successfully transformed tool '{tool['name']}'.")
        #     else:
        #         # DEBUG: Log if an unsupported tool type is encountered.
        #         # print(f"WARNING: transform_tools: Tool type '{tool.get('type')}' not supported for transformation and will be skipped: {tool.get('name', 'N/A')}.")
        # # DEBUG: Completed tool transformation. Transformed tools count: {len(transformed_tools)}
        # # print(f"DEBUG: transform_tools: Completed transformation. Transformed {len(transformed_tools)} tools.")
        return transformed_tools

    async def generate_response(
        self,
        messages: Dict[str, Any], # Now expects the structured memory from construct_data
        tools: Optional[List[Dict[str, Any]]] = None, # Corresponds to functions_builder.construct_tools
        model: str = "qwen3:4b", # Default Ollama model
        tool_choice: str = "auto", # 'auto' lets the model decide; 'none' disables tools; {'type': 'function', 'function': {'name': 'my_tool'}} for specific tool
        **kwargs # For any additional provider-specific settings
    ) -> LLMResponse:
        """
        Generates a response from the Ollama model based on the provided messages and tools.

        Args:
            messages (Dict[str, Any]): Structured memory containing system context and conversation history.
                                        Expected keys: "system_context", "conversation_history".
            tools (Optional[List[Dict[str, Any]]]): List of tool definitions for the model to use.
                                                     These should be in functions_builder.construct_tools format.
            model (str): The name of the Ollama model to use (e.g., "gemma3:4b-it-qat").
            tool_choice (str): Strategy for tool usage (e.g., "auto", "none").
            **kwargs: Additional keyword arguments to pass directly to the ollama.chat call.

        Returns:
            LLMResponse: A standardized response object containing text content or function call details.
        """

        l_messages = []
        # DEBUG: Log the incoming raw messages and tools for initial inspection.
        # print(f"DEBUG: Incoming 'messages' for LLM generation: {json.dumps(messages, indent=2)}")
        # print(f"DEBUG: Incoming 'tools' for LLM generation: {json.dumps(tools, indent=2) if tools else 'None'}")

        # 1. Add the main system message from the structured_memory's system_context
        if messages.get("system_context"):
            l_messages.append({
                "role": "system", 
                "content": messages["system_context"]
            })
            # print(f"DEBUG: Added 'system' (system) message: '{messages['system_context'][:100]}...'")

        # 2. Process conversation history from the structured memory
        for entry in messages.get("conversation_history", []):
            # DEBUG: Processing conversation history entry: type and content/name.
            print(f"DEBUG: Processing conversation history entry: Type='{entry['type']}', Content/Name='{entry.get('content', entry.get('name'))[:100]}...'")
            if entry["type"] == "user":
                l_messages.append({"role": "user", "content": entry["content"]})
            elif entry["type"] == "assistant":
                l_messages.append({"role": "assistant", "content": entry["content"]})
            elif entry["type"] == "tool_output":


                l_messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": entry["call_id"],
                        "type": "function",
                        "function": {
                            "name": entry["function_name"],
                            "arguments": entry["arguments"]
                        }
                    }]
                })

                l_messages.append({
                    "role": "tool", # Using 'tool' role for tool output.
                    "content": str(entry["content"]),
                    "tool_name": entry["function_name"],
                    "tool_call_id": entry["call_id"]

                })
        
        # DEBUG: Log the final constructed 'l_messages' list that will be sent to the LLM.
        # print(f"DEBUG: Constructed 'messages' list for LLM API call: {json.dumps(l_messages, indent=2)}")

        settings = {
            "model": model,
            "messages": l_messages, # This will be the 'messages' array in the Ollama API call.
            "think": False
        }
        
        # --- FIX: Transform tools to Ollama's expected format before passing them ---
        if tools and tool_choice=="auto":
            # DEBUG: Tools detected. Calling transform_tools to convert format.
            # print("DEBUG: Tools provided. Transforming them to Ollama's required format.")
            transformed_tools = self.transform_tools(tools)
            settings["tools"] = transformed_tools
            #settings["tool_choice"] = tool_choice

            # The 'tool_choice' parameter is commented out in your original code.
            # If you intend to use it, uncomment this line.
            # settings["tool_choice"] = tool_choice
        # else:
        #     # print("DEBUG: No tools provided for the LLM call.")
        
        # Merge any additional kwargs provided. These will be passed directly to ollama.chat.
        settings.update(kwargs)
        # DEBUG: Log the final 'settings' dictionary before making the API call.
        # print(f"DEBUG: Final 'settings' for LLM API call: {json.dumps(settings, indent=2)}")

        llm_response = None # Initialize response variable to None
        try:
            # DEBUG: Making the actual ollama.chat API call.
            # print("DEBUG: Calling ollama.chat with specified settings...")
            llm_response = ollama.chat(**settings)
            # DEBUG: Raw response received from Ollama.
            # print(f"DEBUG: Raw LLM response received. Type: {type(llm_response)}")
            # print(f"DEBUG: Raw LLM response content: {llm_response}")

        except Exception as e:
            # DEBUG: Detailed error logging for any exceptions during the API call.
            print(f"ERROR: Exception calling LLM API (ollama.chat): {type(e).__name__} - {e}")
            return LLMResponse(text_content=f"Error communicating with LLM: {e}")

        # --- Normalize LLM's 'response' into our LLMResponse structure ---
        # This section processes the raw response from Ollama into a standardized format.
        # It correctly accesses attributes of the `ollama._types.ChatResponse` and `ollama._types.Message` objects.
        
        normalized_function_calls: List[FunctionCallDetails] = []
        normalized_text_content: Optional[str] = None

        if llm_response:
            # print(f"DEBUG: LLM response received, attempting to parse.")

            # Access the 'message' attribute directly from the ChatResponse object.
            # This 'message' itself is an 'ollama._types.Message' object.
            message_obj = llm_response.message
            # print(f"DEBUG: Accessed message object from ChatResponse. Type: {type(message_obj)}")

            if message_obj:
                # 1. Check for tool calls first
                # Access the 'tool_calls' attribute from the message object.
                # This will be None if no tools were called, or a list of tool call objects.
                tool_calls_list = message_obj.tool_calls
                # print(f"DEBUG: Tool calls attribute from message: {tool_calls_list}. Type: {type(tool_calls_list)}")

                if tool_calls_list: # If tool_calls_list is not None and not empty
                    # print(f"DEBUG: Processing {len(tool_calls_list)} tool call(s).")
                    for tool_call in tool_calls_list:
                        # DEBUG: Processing individual tool call: {tool_call}. Type: {type(tool_call)}"
                        try:
                            # Each `tool_call` object has a `function` attribute.
                            # `function` itself has `name` and `arguments` attributes.
                            function_name = tool_call.function.name
                            
                            # --- FIX: Removed json.loads() here ---
                            # As per debug, tool_call.function.arguments is already a dictionary ({}), not a JSON string.
                            parsed_args = tool_call.function.arguments
                            # print(f"DEBUG: Arguments directly from tool_call.function.arguments: {parsed_args}. Type: {type(parsed_args)}")
                            
                            # Ollama's tool calls often have an 'id', retrieve it safely.
                            call_id = getattr(tool_call, 'id', None) 

                            normalized_function_calls.append(
                                FunctionCallDetails(
                                    name=function_name,
                                    arguments=parsed_args, # Pass as is, now it's a dict
                                    call_id=call_id # Retain call_id if available
                                )
                            )
                            # print(f"DEBUG: Parsed FunctionCall: Name='{function_name}', Arguments='{parsed_args}', Call ID='{call_id}'")
                        except AttributeError as ae:
                            print(f"ERROR: AttributeError accessing tool call details (e.g., missing .function or .name/.arguments): {ae}. Tool call object: {tool_call}")
                        except Exception as e:
                            # This catch is now less likely to hit a JSONDecodeError, but keeps general error handling.
                            print(f"ERROR: Unexpected error processing individual tool call: {e}. Tool call object: {tool_call}")

                # 2. Get the text content if no tool calls were made or if content is present alongside.
                # Access the 'content' attribute directly from the message object. This will be a string or None.
                text_content = message_obj.content
                # print(f"DEBUG: Text content from message object: '{text_content[:100] if text_content else 'None'}'. Type: {type(text_content)}")

                if text_content is not None and not normalized_function_calls: # Only set text content if no function calls detected and content exists
                    normalized_text_content = text_content.strip() # Strip any leading/trailing whitespace
                #     # print(f"DEBUG: Normalized text content: '{normalized_text_content}'")
                # elif text_content is not None and normalized_function_calls:
                #     # print(f"DEBUG: Text content present but function calls also detected. Text content might be a thinking process or brief instruction: '{text_content[:100]}...'")

            else:
                print("WARNING: 'message' attribute not found in LLM ChatResponse object or was None. Cannot parse message content.")
        else:
            print("WARNING: LLM response object was None. No content to parse.")


        # Return our standardized LLMResponse
        final_llm_response = LLMResponse(
            function_calls=normalized_function_calls if normalized_function_calls else None,
            text_content=normalized_text_content if normalized_text_content else None
        )
        # DEBUG: Log the final standardized LLMResponse object that will be returned.
        # print(f"DEBUG: Final standardized LLMResponse object: Function Calls={final_llm_response.function_calls}, Text Content='{final_llm_response.text_content}'")
        return final_llm_response