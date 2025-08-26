# To run this code you need to install the following dependencies:
# pip install google-genai


import os
from google import genai
from google.genai import types

from ai_managers.images_ai.images_ai_abc import ImagesAI


class GeminiImages(ImagesAI):
    """
    Gemini Images provider
    """
    def __init__(self, model="gemini-2.5-flash-image-preview"):
        super().__init__(model)
        self.selected_model=model
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key is None:
            raise ValueError("GEMINI_API_KEY API key not found. Please set the GEMINI_API_KEY environment variable.")
        self.client = genai.Client(api_key=api_key)


    def generate_image(self, prompt: str) -> bytes:
        model = self.selected_model
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            response_modalities=[
                "IMAGE"
            ],
            
        )
        full_image_data = b""  # Initialize an empty byte array to store the full image data

        for chunk in self.client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue
            if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                full_image_data += inline_data.data  # Append data from the current chunk

        return full_image_data  # Return the complete byte array after the loop finishes