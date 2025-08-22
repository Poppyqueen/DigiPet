from ollama import chat
from ollama import ChatResponse


import os
from typing import Any
import time
from pydantic import BaseModel, ValidationError



from ai_managers.simple_ai.abstract_provider import SimpleAI

class OllamaProv(SimpleAI):
    """
    Simple Ollama provider
    """
    def __init__(self, selected_model=None):
        super().__init__(selected_model)

    def _call_openai(self, role: str, system: str, input_content: str) -> str | None:
        """
        Internal method to make a call to the Ollama chat completions API.
        :param role: The role of the message sender (e.g., "user", "system").
        :param system: The system prompt content.
        :param input_content: The user's input content.
        :return: The content of the AI's response or None if an error occurs.
        """
        try:
            response: ChatResponse = chat(model=self.ai_model, messages=[
            {
                'role': 'system',
                'content': system,
            },
            {
                'role': role,
                'content': input_content,
            },

            ],
            options={
                "num_ctx": 1024
            }
            )
            #print(response['message']['content'])
            # or access fields directly from the response object
            #print(response.message.content)
            return response.message.content
        except Exception as e:
            print(f"Error calling Ollama API: {e}")
            return None
        

    def _calls_structured(self, system: str, input_content: str, structure: Any):
        """
        Calls the Ollama API with a structured response format and retries on validation errors.
        """
        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = chat(
                    messages=[
                        {
                            'role': 'system',
                            'content': system,
                        },
                        {
                            'role': 'user',
                            'content': input_content,
                        }
                    ],
                    model=self.ai_model,
                    format=structure.model_json_schema(),
                    options={
                        "num_ctx": 1024
                    }
                )
                # This is where the ValidationError is raised
                model_structure = structure.model_validate_json(response.message.content)
                print(f"✅ Success on attempt {attempt + 1}")
                time.sleep(1)
                return model_structure
            except ValidationError as e:
                print(f"❌ Pydantic validation error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    time.sleep(2)  # Pause before retrying
                else:
                    print("❗ Max retries reached. Giving up.")
                    return None
            except Exception as e:
                print(f"Error calling Ollama API: {e}")
                return None
        return None # Return None if all retries fail

    def structured_output(self, system, user, structure: BaseModel) -> BaseModel:
        """
        Method to get a structured response from a given pydantic model                                                             
        Returns the requested structure as a pydantic object.                               
        """
        return self._calls_structured(system, user, structure)

    def response_output(self, system: str, message: str) -> str:
        """
        Method to get a simple string response from a model.
        Must be implemented by subclasses.
        """
        return self._call_openai("user", system, message)