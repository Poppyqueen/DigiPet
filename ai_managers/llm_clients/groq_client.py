# groq_client.py

from groq import Groq
import json
from ai_managers.llm_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.llm_clients.llm_response_types import LLMResponse, FunctionCallDetails
from typing import List, Dict, Any, Optional


class GroqClient(AbstractLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Groq client.
        
        Args:
            api_key: Optional API key for authentication. If None, relies on default credentials.
        """
        
        self.client = Groq(api_key=api_key)

    def _transform_function_structure(self, input_dict):
        """
        Transforms a function definition dictionary into a new structure.

        Args:
            input_dict (dict): The original dictionary representing a function.

        Returns:
            dict: The transformed dictionary.
        """
        if not isinstance(input_dict, dict):
            raise TypeError("Input must be a dictionary.")
        
        # Ensure the input has the expected keys for a function definition
        required_keys = ["type", "name", "description", "parameters"]
        if not all(key in input_dict for key in required_keys):
            raise ValueError(f"Input dictionary is missing one or more required keys: {required_keys}")

        transformed_dict = {
            "type": input_dict["type"],  # Keep the top-level type
            "function": {
                "name": input_dict["name"],
                "description": input_dict["description"],
                "parameters": input_dict["parameters"]
            }
        }
        return transformed_dict
    
    def _process_functions_list(self, functions_list):
        """
        
        """
        transformed_functions=[]
        for function in functions_list:
            transformed_function=self._transform_function_structure(function)
            transformed_functions.append(transformed_function)
        return transformed_functions
    
    async def generate_response(
        self,
        messages: List[Dict[str, Any]], # Corresponds to memory_manager.construct_data
        tools: Optional[List[Dict[str, Any]]] = None, # Corresponds to functions_builder.construct_tools
        model: str = "llama-3.1-8b-instant",
        tool_choice: str = "auto", # Or a more specific enum if needed
        **kwargs # For any additional provider-specific settings
    ) -> LLMResponse:
        """
        Generates a response from the LLM, normalizing it into a
        standardized LLMResponse format.

        Args:
            messages: The conversation history/prompt for the LLM.
            tools: List of available tools (functions) for the LLM to call.
            model: The name of the LLM model to use.
            tool_choice: Strategy for tool usage (e.g., "auto", "none").
            **kwargs: Additional provider-specific parameters.

        Returns:
            An LLMResponse object containing normalized function call details
            or text content.
        """
        l_messages = []

        functions_list=self._process_functions_list(tools)


        # 1. Add the main system message from the structured_memory's system_context
        # This becomes your original 'developer' message.
        if messages.get("system_context"):
            l_messages.append({
                "role": "system", # Using 'system' role 
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
                    "role": "tool",
                    "content": entry["content"],
                    "tool_call_id": entry["call_id"]
                })
        

        settings = {
            "model": model,
            "messages": l_messages, # 
        }
        if functions_list:
            settings["tools"] = functions_list
            settings["tool_choice"] = tool_choice
        
        # Merge any additional kwargs
        settings.update(kwargs)

        response = self.client.chat.completions.create(**settings)

        # Extract the response and any tool call responses
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        output_text=None
        normalized_function_calls: List[FunctionCallDetails] = []
        if tool_calls:
            # Process each tool call

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                normalized_function_calls.append(
                    FunctionCallDetails(
                        name=function_name,
                        arguments=function_args,
                        call_id=tool_call.id # Retain call_id if available
                    )
                )

        else:
            output_text=response_message.content

        return LLMResponse(
            function_calls=normalized_function_calls if normalized_function_calls else None,
            text_content=output_text if output_text else None
        )
        
