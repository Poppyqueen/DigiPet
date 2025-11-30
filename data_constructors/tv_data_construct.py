# tv_data_construct.py



import os
import re
import sys

# --- TEMPORARY FIX FOR DIRECT EXECUTION ---
# This block allows the script to find the 'utils' package
# when run directly from its current location.
# Assuming 'utils' is in the parent directory of this script's location
# This adds the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
# -------------------------------------------

from pydantic import BaseModel, Field
from typing import List, Dict, Any
import json # Import the json module
import time


from ai_managers.ai_utils.ai_loader import AIConfiguration



class individual_tv_show(BaseModel):
    content: str = Field(description="An excerpt, quote or part of the program playing on TV. This has to be content of the TV media in display, not descriptions, but small excerpts or sections of it.")
    time_tag: str = Field(description="The slot of time for this TV show to air. Options: 'early morning', 'morning', 'noon', 'afternoon', 'late afternoon', 'night', 'late night'")

class programming(BaseModel):
    tv_show_name: str = Field(description="The name of the TV show in the main channel")
    tv_show_contents: List[individual_tv_show] = Field(description="A list of different TV shows at different times for the main channel")

class main_channel_container(BaseModel):
    channel_name: str
    programming_list: list[programming]= Field(description="A dict with the name of the main channel where collection of TV shows will be played")

# Pydantic models for the new two-step AI call process (Keep these)
class InitialChannelSetup(BaseModel):
    channel_name: str = Field(description="The generated name of the TV channel.")
    program_titles: List[str] = Field(
        description="A list of 3 to 5 distinct and creative titles for TV programs on this channel."
    )

class ProgramContent(BaseModel):
    tv_show_segments: List[individual_tv_show] = Field(
        description="A list of 2 to 4 detailed content segments for the TV program. Each segment must include actual broadcast-style content and a valid time_tag."
    )


class tv_exec:

    def __init__(self, select_model="gpt-5-mini", select_provider="openai"):
        self.llm_client=AIConfiguration(provider=select_provider,model=select_model,mode="simple_ai").get_client()




    # --- Existing methods for two-step generation (Keep these) ---

    def _generate_channel_outline(self, channel_concept: str) -> InitialChannelSetup | None:
        """
        First AI call: Generates the channel name and a list of program titles.
        """
        system_prompt = (
            "You are an AI assistant helping to brainstorm TV channel concepts. "
            "Given a channel concept, generate a creative and fitting channel name. "
            "Also, create a list of 3 to 5 distinct and engaging program titles appropriate for that channel. "
            "Ensure program titles are diverse and sound like real TV shows."
        )
        user_prompt = f"Develop a channel outline based on the concept: '{channel_concept}'."

        print(f"  Calling AI (Step 1: Channel Outline) for concept: '{channel_concept}'")
        response = self.llm_client.structured_output(
            system=system_prompt,
            user=user_prompt,
            structure=InitialChannelSetup
        )

        if response:
            print(f"  [AI Response] Channel Name: '{response.channel_name}', Program Titles: {response.program_titles}")
        else:
            print(f"  [AI Response] Failed to generate channel outline for '{channel_concept}'.")
        return response

    def _generate_program_segments(self, channel_name: str, program_title: str) -> ProgramContent | None:
        """
        Second AI call (repeated for each program): Generates content segments for a specific program.
        """
        system_prompt = """

You are an AI assistant creating detailed content segments for TV programs on various channels. 

For the given TV channel and program title, generate 2 to 4 distinct content segments. Each segment must include: 

- A 'content' field: An actual excerpt of the program (e.g., dialogue, news report, narration, action description) as if it is being broadcast. The content should be engaging, realistic, and at least a paragraph long. You may include various parts of the segment in the same content, divided by ellipses '...', to show different scenes or parts. You can create sections without context, non-sequitur or from the middle section, as if we missed parts of it.

- A 'time_tag' field: Must be one of the following: 'early morning', 'morning', 'noon', 'afternoon', 'late afternoon', 'night', 'late night'. Aim to create varied content across these time tags. Make sure that your time tag is coherent and related to the content created if necesary.

# Steps

1. Identify the TV channel and program title provided.
2. Generate 2-4 content segments that reflect the tone and style typical of the program.
3. Ensure each segment includes a vivid 'content' excerpt, reflecting realistic broadcast material.
4. Assign an appropriate 'time_tag' to each segment, ensuring a spread across different times of the day and alligning with the content generated for it.
5. Ensure the content is varied and appropriate to the assigned time tag.

# Output Format

Provide the output as a JSON array of segment objects:

```json
[
    {
        "content": "Volunteers on the California coast are painstakingly restoring native dune grasses, a vital step in preventing erosion and rebuilding habitat for endangered shorebirds like the Western Snowy Plover. ... Across the globe, scientists are racing to develop new methods for tracking illegal fishing vessels using satellite imagery and AI, helping to protect vulnerable marine populations from overexploitation",
        "time_tag": "early morning"
    },
    ...
]
```

Each object in the array represents a separate content segment for the TV program.

# Examples

**Example 1**

Given TV channel: [TV Channel Name]
Program Title: [Program Title]

```json
[
    {
        "content": "Did you know that a group of flamingos is called a 'flamboyance'? These elegant birds often stand on one leg, but scientists still aren't completely sure why \u2013 perhaps to save energy or regulate body temperature! ... And here's another amazing fact: some species of octopuses can change the texture of their skin to perfectly blend in with surrounding rocks or coral, disappearing in an instant!",
        "time_tag": "morning"
    },
    {
        "content": "Reporter: 'New data suggests a significant increase in food insecurity among elderly populations in urban areas, often linked to rising costs and limited access to transportation.' (Visual: Chart showing data trends) ... Panelist 1: 'This isn't just about economics; it's a dignity issue. We need comprehensive solutions that involve not only food banks but also community support networks and policy changes.",
        "time_tag": "night"
    }
]
```


"""
        user_prompt = (
            f"Generate content segments for the program titled '{program_title}' "
            f"which airs on the channel '{channel_name}'. "
            "Provide rich, broadcast-style content for each segment."
        )

        print(f"  Calling AI (Step 2: Program Segments) for Program: '{program_title}' on Channel: '{channel_name}'")
        response = self.llm_client.structured_output(
            system=system_prompt,
            user=user_prompt,
            structure=ProgramContent
        )

        if response and hasattr(response, 'tv_show_segments') and response.tv_show_segments:
             print(f"  [AI Response] Generated {len(response.tv_show_segments)} segments for '{program_title}'.")
        elif response:
             print(f"  [AI Response] Received response for '{program_title}', but no valid segments found or segments list is empty.")
        else:
             print(f"  [AI Response] Failed to generate segments for '{program_title}'.")
        return response

    def create_full_tv_schedule(self, channel_concept: str) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        """
        Orchestrates the two-step generation process to create the full TV schedule
        for a single channel in the desired dictionary format.
        """
        print(f"\n--- Initiating TV Schedule Generation for Concept: '{channel_concept}' ---")

        # Step 1: Generate channel name and program titles
        channel_outline = self._generate_channel_outline(channel_concept)

        if not channel_outline or not channel_outline.channel_name or not channel_outline.program_titles:
            print("Critical failure: Could not generate channel outline (name or program titles missing). Aborting schedule creation.")
            return {}

        # Prepare the structure for the single channel's data
        single_channel_data: Dict[str, Dict[str, List[Dict[str, str]]]] = {channel_outline.channel_name: {}}
        channel_programs_data = single_channel_data[channel_outline.channel_name]


        # Step 2: For each program title, generate its content segments
        for program_title in channel_outline.program_titles:
            program_content_response = self._generate_program_segments(channel_outline.channel_name, program_title)

            if program_content_response and hasattr(program_content_response, 'tv_show_segments') and program_content_response.tv_show_segments:
                # Convert List[individual_tv_show] to List[Dict[str, str]] for the final structure
                segments_as_dicts = [segment.model_dump() for segment in program_content_response.tv_show_segments]
                channel_programs_data[program_title] = segments_as_dicts
            else:
                print(f"Warning: No segments generated or retrieved for program '{program_title}'. It will be listed with empty content.")
                channel_programs_data[program_title] = [] # Add with empty list if generation failed

        print(f"--- TV Schedule Generation Complete for Channel: '{channel_outline.channel_name}' ---")
        return single_channel_data # Return the dictionary containing just the newly created channel


    def append_tv_channel_to_file(self, file_path: str, new_channel_data: Dict[str, Dict[str, List[Dict[str, str]]]]) -> bool:
        """
        Loads existing TV schedule from a JSON file, appends a new channel's data,
        and saves the combined schedule back to the same file.

        Args:
            file_path: The path to the JSON file containing the TV schedule.
            new_channel_data: A dictionary containing the data for one new channel
                              (format: {"Channel Name": { "Program Name": [ {...}, ... ] }}).

        Returns:
            True if the append and save operation was successful, False otherwise.
        """
        combined_schedule: Dict[str, Dict[str, List[Dict[str, str]]]] = {}

        # 1. Load existing data from the file
        try:
            with open(file_path, 'r') as f:
                # Handle empty file or invalid JSON
                try:
                    combined_schedule = json.load(f)
                    if not isinstance(combined_schedule, dict):
                         print(f"Warning: File '{file_path}' contains data that is not a dictionary. Starting fresh.")
                         combined_schedule = {}
                except json.JSONDecodeError:
                    print(f"Warning: File '{file_path}' contains invalid JSON. Starting fresh.")
                    combined_schedule = {}
                except Exception as e:
                     print(f"An unexpected error occurred while reading '{file_path}': {e}")
                     combined_schedule = {} # Fallback to empty dictionary on other read errors

        except FileNotFoundError:
            print(f"Info: File '{file_path}' not found. Creating a new file.")
            combined_schedule = {} # Start with an empty dict if the file doesn't exist

        # 2. Append the new channel data
        # new_channel_data is expected to be a dictionary with a single key (the channel name)
        if new_channel_data:
            combined_schedule.update(new_channel_data)
            print(f"Appended data for channel(s): {list(new_channel_data.keys())}")
        else:
            print("Warning: No new channel data provided to append.")
            return False # Indicate failure if there's nothing to append

        # 3. Save the combined data back to the file
        try:
            with open(file_path, 'w') as f:
                json.dump(combined_schedule, f, indent=4)
            print(f"Successfully saved combined schedule to '{file_path}'.")
            return True
        except Exception as e:
            print(f"Error writing schedule to file '{file_path}': {e}")
            return False


# Example Usage:
if __name__ == "__main__":
    creative = tv_exec()
    schedule_file = "tv_data.json" # Define the path to your schedule file

    channel_ideas=["Comedy Channel", "Futurism channel", "Politics channel"]
    total_channels = len(channel_ideas) # Get the total number of channels

    # Use enumerate to get both the index and the channel name
    for index, channel in enumerate(channel_ideas):
        # index is 0-based, so add 1 for a 1-based count display
        current_channel_number = index + 1

        # Print the generation message with the current number and total
        print(f"\n--- Generating and Appending {channel} ({current_channel_number} of {total_channels}) ---")

        run_data = creative.create_full_tv_schedule(channel)

        if run_data:
            success = creative.append_tv_channel_to_file(schedule_file, run_data)
            if success:
                print(f"'{channel}' added to file.")
                if current_channel_number < total_channels:
                      print(f"Successfully processed '{channel}' ({current_channel_number} of {total_channels}).")
                      print("Sleeping for 10 seconds!")
                      time.sleep(10)


            else:
                print(f"Failed to add '{channel}' to file.")
        else:
            print(f"'{channel}' generation failed.")

    print("\nAll channels finalized!")