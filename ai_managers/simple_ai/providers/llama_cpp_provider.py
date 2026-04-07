from openai import OpenAI
import instructor
import time
from pydantic import BaseModel
from typing import Any

from ai_managers.simple_ai.abstract_provider import SimpleAI


class LlamaCppProv(SimpleAI):
    """
    Llama.cpp provider using the `instructor` library for robust structured outputs.

    instructor wraps the OpenAI-compatible client and adds:
      - Pydantic-schema-guided generation (JSON_SCHEMA mode)
      - Automatic validation + retry if the model returns an incomplete/invalid response
    """

    def __init__(self, selected_model=None, max_retries: int = 3, base_url: str = "http://localhost:8080/v1"): # TODO: Make this configurable?
        super().__init__(selected_model)

        raw_client = OpenAI(base_url=base_url, api_key="not-needed")

        # Patch with instructor in JSON_SCHEMA mode — best fit for llama.cpp
        self.client = instructor.from_openai(
            raw_client,
            mode=instructor.Mode.JSON_SCHEMA,
        )

        # Plain (un-patched) client for simple string responses
        self._plain_client = raw_client
        self.max_retries = max_retries

    # ------------------------------------------------------------------
    # Structured output — instructor handles validation + retries
    # ------------------------------------------------------------------
    def structured_output(self, system: str, user: str, structure: type[BaseModel]) -> BaseModel | None:
        """
        Returns a fully-validated instance of `structure`, or None on failure.
        instructor will retry up to `self.max_retries` times if the model
        returns an incomplete or invalid response.
        """
        try:
            result = self.client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                response_model=structure,
                max_retries=self.max_retries,
            )
            time.sleep(1)  # Respect local server rate limits
            return result
        except Exception as e:
            print(f"[LlamaCppInstructorProv] structured_output error ({structure.__name__}): {e}")
            return None

    # ------------------------------------------------------------------
    # Plain string response — bypass instructor, use raw client
    # ------------------------------------------------------------------
    def response_output(self, system: str, message: str) -> str | None:
        """
        Returns a plain string response, or None on failure.
        """
        try:
            completion = self._plain_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": message},
                ],
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"[LlamaCppInstructorProv] response_output error: {e}")
            return None