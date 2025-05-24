import datetime
import random
import json # Need json for loading
import os   # Need os for checking file existence

from utils.time_manager import get_time_tag_from_now
# --- Data Structure Design (Conceptual - lives in tv_data.json) ---
# The data will be loaded from a JSON file with this structure:
# {
#     "Channel Name": {
#         "Program Name": [
#             {"content": "Excerpt Text", "time_tag": "early morning"},
#             # ... more excerpts for this program
#         ],
#         # ... more programs for this channel
#     },
#     # ... more channels
# }

FILE_PATH = "world_data/tv_data.json" # The name of our data file

def write_tv_data_to_file(data, filename=FILE_PATH):
    """Writes the TV data dictionary to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"Successfully wrote initial data to {filename}")
    except IOError as e:
        print(f"Error writing file {filename}: {e}")


# --- Modified load function to read from file ---
def load_tv_data(filename=FILE_PATH):
    """
    Loads the TV program structure from a JSON file.
    Returns an empty dictionary if the file is not found or is invalid.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            tv_data = json.load(f)
        return tv_data
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filename}. File might be corrupted or empty.")
        return {}
    except IOError as e:
        print(f"Error reading file {filename}: {e}")
        return {}



# --- Main function remains largely the same ---
def get_tv_program() -> str:
    """
    Gets the current time, finds the corresponding time tag,
    loads TV data from file, filters for excerpts matching the tag,
    and returns a random matching excerpt description.
    """
    # 1. Get the current time and corresponding tag
    now = datetime.datetime.now()
    current_hour = now.hour
    current_tag = get_time_tag_from_now()

    if current_tag is None:
        # With the current get_time_tag, this message indicates an issue
        # with the hour value (outside 0-23).
        return f"Internal Error: Invalid hour value ({current_hour}). Cannot find a program tag."

    print(f"Current time is {now.strftime('%H:%M')}. Looking for programs tagged '{current_tag}'.")

    # 2. Load TV data from file
    tv_data = load_tv_data()

    # Check if data loading failed (returned empty dict)
    if not tv_data:
        return "Could not load TV data. Please check the data file."


    # 3. Filter data for excerpts matching the current time tag
    matching_excerpts = []
    # Iterate through channels, then programs, then excerpts
    for channel_name, programs in tv_data.items():
        # Ensure programs value is a dictionary before iterating
        if isinstance(programs, dict):
            for program_name, excerpts in programs.items():
                # Ensure excerpts value is a list before iterating
                if isinstance(excerpts, list):
                    for excerpt in excerpts:
                         # Ensure excerpt is a dictionary and has 'time_tag' key
                         if isinstance(excerpt, dict) and excerpt.get("time_tag") == current_tag:
                            # Store the excerpt content along with its origin
                            matching_excerpts.append({
                                "channel": channel_name,
                                "program": program_name,
                                "content": excerpt.get("content", "No content provided"),
                                "tag": current_tag
                            })
                else:
                    print(f"Warning: Expected a list of excerpts for Program '{program_name}' on Channel '{channel_name}', but got {type(excerpts)}. Skipping.")
        else:
             print(f"Warning: Expected a dictionary of programs for Channel '{channel_name}', but got {type(programs)}. Skipping.")


    # 4. Select a random matching excerpt
    if not matching_excerpts:
        return f"No matching programs or excerpts found for the time tag '{current_tag}'. Please check your data file."

    chosen_excerpt_info = random.choice(matching_excerpts)

    # 5. Format and return the result
    return f"""From Channel: {chosen_excerpt_info['channel']}\n
        Program/Section: {chosen_excerpt_info['program']}\n
        Excerpt: {chosen_excerpt_info['content']}"""
    
