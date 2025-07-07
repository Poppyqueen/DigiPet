from openai import OpenAI
from ai_managers.llm_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.llm_clients.llm_response_types import LLMResponse, FunctionCallDetails, TextMessageDetails
from typing import List, Dict, Any, Optional
import json # For parsing arguments from OpenAI's string format


class OpenAIClient(AbstractLLMClient):
    def __init__(self, selected_key=None): # Make sure to pass api_key here
        if selected_key is not None:
            self.client = OpenAI(api_key=selected_key) # Initialize the OpenAI client with the argument api_key
        else:
            self.client = OpenAI() # Try setting up the client with system wide api keys


    async def generate_response(
        self,
        messages: Dict[str, Any], # Now expects the structured memory from construct_data
        tools: Optional[List[Dict[str, Any]]] = None, # Corresponds to functions_builder.construct_tools
        model: str = "gpt-4.1-mini", # Default OpenAI model
        tool_choice: str = "auto",
        **kwargs # For any additional provider-specific settings
    ) -> LLMResponse:
        

        l_messages = []

        # 1. Add the main system message from the structured_memory's system_context
        # This becomes your original 'developer' message.
        if messages.get("system_context"):
            l_messages.append({
                "role": "developer", # Using 'developer' role as per your original message structure
                "content": messages["system_context"]
            })

        # 2. Process conversation history from the structured memory
        for entry in messages.get("conversation_history", []):
            if entry["type"] == "user":
                l_messages.append({"role": "user", "content": entry["content"]})
            elif entry["type"] == "assistant":
                l_messages.append({"role": "assistant", "content": entry["content"]})
            elif entry["type"] == "tool_output":
                # As per your requirement: "for the system messages you want to apply them as tool messages"
                # This directly implements: messages.append({"role": "system" "content": str(result)})
                l_messages.append({
                    "role": "system",
                    "content": entry["content"]
                })
        

        settings = {
            "model": model,
            "input": l_messages, # 
        }
        if tools:
            settings["tools"] = tools
            settings["tool_choice"] = tool_choice
        
        # Merge any additional kwargs
        settings.update(kwargs)

        try:
            # Call the ACTUAL OpenAI API method you were using: client.responses.create
            openai_response = self.client.responses.create(**settings)
        except Exception as e:
            print(f"Error calling OpenAI API (client.responses.create): {e}")
            return LLMResponse(text_content=f"Error communicating with OpenAI: {e}")

        # --- Normalize OpenAI's 'response.output' into our LLMResponse structure ---
        # This section remains EXACTLY as you provided it, as it parses YOUR API's response.
        normalized_function_calls: List[FunctionCallDetails] = []
        normalized_text_content: Optional[str] = None

        if openai_response.output: # <--- CRITICAL: Access 'output' attribute
            for item in openai_response.output:
                if item.type == "function_call":
                    try:
                        parsed_args = json.loads(item.arguments) # Arguments are already a JSON string
                        normalized_function_calls.append(
                            FunctionCallDetails(
                                name=item.name,
                                arguments=parsed_args,
                                call_id=item.id # Retain call_id if available
                            )
                        )
                    except json.JSONDecodeError as e:
                        print(f"Error parsing function arguments from OpenAI 'responses' API: {e}")
                        pass
                    except Exception as e:
                        print(f"Unexpected error processing OpenAI function call item: {e}")
                        pass

                elif item.type == "message":
                    if hasattr(item, 'content') and isinstance(item.content, list):
                        for content_item in item.content:
                            if hasattr(content_item, 'type') and content_item.type == 'output_text':
                                if normalized_text_content is None:
                                    normalized_text_content = ""
                                normalized_text_content += content_item.text + "\n"
            
            if normalized_text_content and normalized_text_content.endswith("\n"):
                normalized_text_content = normalized_text_content.strip()

        elif hasattr(openai_response, 'output_text') and openai_response.output_text:
            normalized_text_content = openai_response.output_text


        # Return our standardized LLMResponse
        return LLMResponse(
            function_calls=normalized_function_calls if normalized_function_calls else None,
            text_content=normalized_text_content if normalized_text_content else None
        )