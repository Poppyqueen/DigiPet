
# openai_memory_ai_provider.py
from openai import OpenAI
import time
import os
from memory.memory_providers.memory_ai_abc import MemoryAI

class OpenAIMemoryAI(MemoryAI):
    """
    OpenAI provider for the MemoryAI abstract base class.
    Implements memory operations using the OpenAI API.
    """

    def __init__(self, text_capture=None,memory_model=None):
        super().__init__(text_capture, memory_model)
        api_key = os.getenv("OPENAI_API_KEY")

        if api_key is None:
            raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=api_key)

    def _call_openai(self, role: str, system: str, input_content: str) -> str | None:
        """
        Internal method to make a call to the OpenAI chat completions API.
        :param role: The role of the message sender (e.g., "user", "system").
        :param system: The system prompt content.
        :param input_content: The user's input content.
        :return: The content of the AI's response or None if an error occurs.
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.memory_ai,
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
            print(f"Error calling OpenAI API: {e}")
            return None

    def summarize_memories(self, to_summarize: str, memory_type: str) -> str | None:
        """
        Summarizes the provided text content based on the memory type using OpenAI.
        """
        system_prompt = ""
        if memory_type == "short_term":
            system_prompt = """
            Create a concise summary from the provided information that captures the key points, including answering what, when, where, and why, from a first-person perspective. Remember to highlight important and useful behaviors, objectives or specific details for future reference to prevent repeated errors and guide planning.

            Focus on including:

            - **What**: Clearly state the main event or action or objects. Make sure to detail the key elements involved.
            - **When**: Specify the timing or context, include initial and ending time with date, hour and minute.
            - **Where**: Describe the location or environment.
            - **Why**: Explain the purpose or reason behind the action.
            - **Behaviors/Objectives**: Emphasize significant behaviors, objectives or details that should be noted for future reference, either to avoid mistakes or to enhance planning and beneficial actions.

            Make sure your output contains all the most relevant and important information to remember. Any updates, progress, failures or achievements should be documented.

            # Output Format

            A concise summary written in the first person perspective that addresses the key points as specified above.

            # Notes

            - Ensure the summary is clear and focused, avoiding unnecessary details.
            - Use past tense for completed actions and present tense for ongoing situations.
            - Highlight lessons learned or important guidelines for future actions.
            """
        elif memory_type == "long_term":
            system_prompt = """
            Summarize memories into 'nuclear memories' that preserve essential information, focusing on key events, individual details, overarching states, changes, and objectives. The summary should be detailed enough to maintain the essence of the memory and written in the first person perspective.

            # Steps

            1. **Identify Key Events**: Determine the major events that define the memory, make sure to note a granular archival of the time and date of them, organize in a chronological order.
            2. **Highlight Individual Details**: Note important details about people, places, and objects involved, specially when it relates to you.
            3. **Assess Overarching States**: Describe the general state or condition during the memory.
            4. **Detect Changes**: Recognize significant changes or developments that occurred.
            5. **Define Objectives**: Identify any goals or aims associated with the events.
            6. **Define positive and negative behaviors and actions you have learnt through your exploration.

            # Output Format

            - Detailed paragraph in the first person perspective.
            - Comprehensive enough to preserve the memory's essence.

            # Notes

            - Prioritize information relevance to ensure the essence of the memory is captured.
            - Use descriptive language that evokes imagery and emotions associated with the memory.
            - Keep the summary concise while ensuring no critical elements are omitted.
            - Use past tense for completed actions and present tense for ongoing situations.
            - Present the information from a first-person perspective, as if the memory is being recounted by the individual who experienced it.
            """
        else:
            print(f"Error: Invalid memory type '{memory_type}'. Must be 'short_term' or 'long_term'.")
            return None

        role = "user"
        response = self._call_openai(role, system_prompt, to_summarize)

        if self.text_capture and response:
            self.text_capture.dump_text(f"Memory archival:")
            current_time_unix = int(time.time())
            formatted_time = time.ctime(current_time_unix)
            self.text_capture.dump_text(f"{formatted_time}")
            self.text_capture.dump_text(f"Memory Type: {memory_type}")
            self.text_capture.dump_text(f"Summary: {response}")
            self.text_capture.dump_text(f"-------------")

        return response
