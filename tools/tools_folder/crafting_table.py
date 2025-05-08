# OLD NEEDS REVAMP
# 
# 
# crafting_table.py

# This is a simple crafting table class that uses OpenAI's API to process items
# and create new items based on a given process.
# The current implementation is being used by an AI agent to manage crafting tasks.

from openai import OpenAI
# Assuming utils.pydantic_models now contains the new structures
#from utils.pydantic_models import crafter_structure, individual_item, event_crafter
from typing import List # Import List if not already in utils.pydantic_models

class crafter:
    client = OpenAI()  # client is correctly set up here at the class level

    def __init__(self, state_manager):
        self.state=state_manager


    def _call_openai(self, role, system, input_content): # Renamed 'input' to 'input_content' for clarity
        """
        Calls the OpenAI API for unstructured text generation.
        (This method is not used by process() but kept from the original code).
        """
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": role,
                        "content": input_content
                    }
                ]
            )

            response_content = completion.choices[0].message.content

            return response_content

        except Exception as e:
            print(f"Error calling OpenAI API (unstructured): {e}")
            return None

    def _calls_structured(self, system, input_content, structure):
        """
        Calls the OpenAI API with a structured response format (e.g., JSON guided by Pydantic).
        Assumes the API client method or library usage supports specifying a structure.
        Note: Standard OpenAI client uses `response_format={'type': 'json_object'}`
        and relies heavily on the system prompt + tool calls/function calling
        or prompt engineering to produce valid JSON matching a schema.
        This implementation uses a conceptual 'parse' method as in the original code.
        """
        try:

            # Keeping the original 'parse' method signature as per original code:
            completion = self.client.beta.chat.completions.parse( # Functional 'parse' method from the most recent API
                 # Note: gpt-4.1-nano is now a standard OpenAI model name.

                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": input_content
                    }
                ],
                response_format=structure # It assures the API to return structured data
            )
            # Access the parsed content which is expected to be an instance of 'structure'
            response_content = completion.choices[0].message.parsed
            return response_content
        except Exception as e:
            print(f"Error calling OpenAI API for structured output: {e}")
            return None
