# memory_ai_helper.py
from openai import OpenAI
import time
from utils.pydantic_models import look_ner_structure, save_ner_structure, entity_dict  # Import from pydantic_models.py


class memory_ai():
    client=OpenAI()

    def __init__(self, text_capture=None):
        self.text_capture=text_capture
        self.memory_model = "gpt-4.1-mini"

    def _call_openai(self, role, system, input_content): # Renamed 'input' to 'input_content' for clarity

        try:
            completion = self.client.chat.completions.create(
                model=self.memory_model,
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": role,
                        "content": input_content # Use input_content here
                    }
                ]
            )

            # Access the content of the message, not 'response' - this was the main issue
            response_content = completion.choices[0].message.content

            return response_content

        except Exception as e: # It's good practice to have a try-except block for API calls
            print(f"Error calling OpenAI API: {e}")
            return None  # Or handle the error in a way that suits your application


    def summarize_memories(self, to_summarize, memory_type): # Renamed 'type' to 'memory_type' for clarity

        if memory_type == "short_term":
            system_prompt =  """

            Create a concise summary from the provided information that captures the key points, including answering what, when, where, and why, from a first-person perspective. Remember to highlight important and useful behaviors or objectives for future reference to prevent repeated errors and guide planning.

Focus on including:

- **What**: Clearly state the main event or action or objects.
- **When**: Specify the timing or context, include initial and ending time with date, hour and minute.
- **Where**: Describe the location or environment.
- **Why**: Explain the purpose or reason behind the action.
- **Behaviors/Objectives**: Emphasize significant behaviors or objectives that should be noted for future reference, either to avoid mistakes or to enhance planning and beneficial actions.

Make sure your output contains all the most relevant and important information to remember. Any updates, progress, failures or achievements should be documented.

# Output Format

A concise summary written in the first person perspective that addresses the key points as specified above.

# Notes

- Ensure the summary is clear and focused, avoiding unnecessary details.
- Use past tense for completed actions and present tense for ongoing situations.
- Highlight lessons learned or important guidelines for future actions.


            """
            role = "user" # User role is appropriate for input to be summarized
            response = self._call_openai(role, system_prompt, to_summarize) # Correct argument order: role, system, input






        elif memory_type == "long_term": # Use elif for clarity and to avoid unnecessary checks if short_term is already true
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
            role = "user" # User role is appropriate for input to be summarized
            response = self._call_openai(role, system_prompt, to_summarize) # Correct argument order: role, system, input

        else:
            print(f"Error: Invalid memory type '{memory_type}'. Must be 'short_term' or 'long_term'.")
            return None # Handle invalid input gracefully
        

        self.text_capture.dump_text(f"Memory archival:")
        current_time_unix = int(time.time())
        formatted_time = time.ctime(current_time_unix)
        self.text_capture.dump_text(f"{formatted_time}")
        self.text_capture.dump_text(f"Memory Type: {memory_type}")
        self.text_capture.dump_text(f"Summary: {response}")

        self.text_capture.dump_text(f"-------------")

        return response
    
    def save_ner_process(self, mem_structure):
        """
        """
        system_prompt = "From the whole collection of memories provided, extract the named entities and their corresponding excerpts. The output should be a list of dictionaries, each containing a named entity and its associated excerpts. Preface your excerpts with the provenance of the information, what, who said it, when, where. Extract the entities from the conversation itself, names, places, objects, ideas, etc."
        try:
            short_term_memories = mem_structure.get("short_term", {})
            short_term_memories_str = ""
            for key, value in short_term_memories.items():
                short_term_memories_str += f"{key}: {value}\n"


            completion = self.client.beta.chat.completions.parse(
                model=self.memory_model, # Consider making this configurable, or using a more robust model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": short_term_memories_str # Use input_content here
                    }
                ],
                response_format=save_ner_structure

            )
            response_content = completion.choices[0].message.parsed
            #print(response_content)

        except Exception as e: # It's good practice to have a try-except block for API calls
            print(f"Error calling OpenAI API: {e}")
            return None  # Or handle the error in a way that suits your application
        
        self.text_capture.dump_text(f"Memory archival:")
        current_time_unix = int(time.time())
        formatted_time = time.ctime(current_time_unix)
        self.text_capture.dump_text(f"{formatted_time}")
        self.text_capture.dump_text(f"Memory Type: {response_content}")


        self.text_capture.dump_text(f"-------------")

        
        return response_content  # Correct argument order: role, system, input


    def summarize_excerpts(self, excerpts, entity_name):
        """
        Summarizes excerpts into a 'schema' for the entity mentioned,
         It gets a list of entries and name of the entity and returns a list of new summarized entries strings.
         entity_dict is a dictionary that maps entity names to their respective schemas.
        """
        joined_excerpts = "\n".join(excerpts)  # Join the excerpts into a single string
        completion = self.client.beta.chat.completions.parse(
            model=self.memory_model, # Consider making this configurable, or using a more robust model
            messages=[
                {"role": "system", "content": f"Summarize the following excerpts into a collection of descriptive and comprehensive yet sumarized points for the entity {entity_name}. You can merge points and remove duplicates, mention the source of the information, make sure to include the exact time and date of the excerpts."},
                {                        "role": "user",
                       "content": joined_excerpts # 
                }
            ],
            response_format=entity_dict
        )
        response_content = completion.choices[0].message.parsed
        print(f"DEBUG: Type of response_content: {type(response_content)}")
        print(f"DEBUG: Value of response_content: {response_content}")

        summarized_excerpts_list = []

        if response_content: # Check if response_content is not None
            # Directly access the 'excerpts' attribute from the Pydantic model
            if hasattr(response_content, 'excerpts') and isinstance(response_content.excerpts, list):
                summarized_excerpts_list = response_content.excerpts
            else:
                print(f"Warning: 'response_content' does not have 'excerpts' attribute or it's not a list.")
        else:
            print("Warning: response_content is None.")
        #print(summarized_excerpts_list)

        updated_joined_excerpts= "\n".join(summarized_excerpts_list)  # Join the excerpts into a single string

        
        self.text_capture.dump_text(f"Memory archival:")
        current_time_unix = int(time.time())
        formatted_time = time.ctime(current_time_unix)
        self.text_capture.dump_text(f"{formatted_time}")
        self.text_capture.dump_text(f"Entity: {entity_name}")
        self.text_capture.dump_text(f"Summarized Excerpts: \n {updated_joined_excerpts}")

        self.text_capture.dump_text(f"-------------")
        return summarized_excerpts_list


    def look_ner_process(self, mem_structure):
            """
            Extracts named entities from the last one or two short-term memories and queries the AI.
            Uses the last two instances of short-term memory information if available, otherwise uses the last one.
            """
            system_prompt = "Extract a list of named entities, objects or ideas that would be relevant for you to querry, directed or associative concepts. Always include the exact time in year, month, day, hour and minute of the excerpts."
            try:
                short_term_memories = mem_structure.get("short_term", {})

                most_recent_memories_content = []  # List to store the content of the last 1 or 2 memories
                most_recent_keys = [] # List to store the keys of the last 1 or 2 memories

                if short_term_memories:
                    items_list = list(short_term_memories.items())
                    num_memories = len(items_list)

                    if num_memories >= 2:
                        # Get the last two items
                        last_item = items_list[-1]
                        second_last_item = items_list[-2]

                        most_recent_keys.append(second_last_item[0]) # key of the second last
                        most_recent_memories_content.append(second_last_item[1]) # content of second last

                        most_recent_keys.append(last_item[0]) # key of the last
                        most_recent_memories_content.append(last_item[1]) # content of last


                        #print("Most Recent Short-Term Memory Keys (Last Two):", most_recent_keys)
                        #print("Most Recent Short-Term Memory Content (Last Two):", most_recent_memories_content)


                    elif num_memories == 1:
                        # Only one memory available, use that
                        last_item = items_list[-1]
                        most_recent_keys.append(last_item[0]) # key of the last
                        most_recent_memories_content.append(last_item[1]) # content of last

                        #print("Most Recent Short-Term Memory Key (Last One):", most_recent_keys)
                        #print("Most Recent Short-Term Memory Content (Last One):", most_recent_memories_content)

                    else: # This case shouldn't ideally be reached if `if short_term_memories:` is working correctly, but for robustness
                        print("No short-term memories available (even after initial check).")
                        return None # Exit or handle as needed

                    # Construct the prompt content by joining the last 1 or 2 memories with newlines for clarity
                    prompt_content = "\n".join(most_recent_memories_content)

                    completion = self.client.beta.chat.completions.parse(
                        model=self.memory_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": prompt_content  # Use combined content for prompt
                            }
                        ],
                        response_format=look_ner_structure
                    )

                    response_content = completion.choices[0].message.parsed
                    #print(response_content)
                    return response_content # Return the parsed response for further use

                else:
                    print("No short-term memories available.")
                    return None # Indicate no processing was done due to lack of memories

            except Exception as e:
                print(f"Error calling OpenAI API: {e}")
                return None


