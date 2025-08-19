import os
import json

import re

from datetime import datetime

TOTAL_IMAGES_LIMIT=100

def make_string_file_safe(input_string):
    """
    Sanitizes a string to be used as a file name.
    
    This function replaces characters that are not safe for file names on most
    operating systems with an underscore '_'.
    
    Args:
        input_string (str): The string to sanitize.
        
    Returns:
        str: The sanitized string.
    """
    # Define a pattern of characters that are generally unsafe for file names.
    # The pattern matches any character that is NOT a letter (a-z, A-Z),
    # a number (0-9), an underscore (_), a hyphen (-), or a period (.).
    # The `re.IGNORECASE` flag makes the regex case-insensitive.
    unsafe_chars_pattern = re.compile(r'[^\w\s\.-]')
    
    # Replace unsafe characters with an underscore.
    safe_string = unsafe_chars_pattern.sub('_', input_string)
    
    # Also, replace spaces with underscores for better cross-platform compatibility.
    safe_string = safe_string.replace(' ', '_')
    
    # Trim leading/trailing whitespace, which could be an issue.
    safe_string = safe_string.strip()
    
    return safe_string


class ImagesLab:
    def __init__(self, base_path):
        self.base_path = os.path.join(base_path, "images_archive")
        os.makedirs(self.base_path, exist_ok=True)


    def _int_get_arch(self)->list:
        """
        Will return a list of dictionaries. Each dictionary within the list represents an archived image's metadata.
        """
        metadata_file = os.path.join(self.base_path, "metadata.json")
        if not os.path.exists(metadata_file):
            return []

        with open(metadata_file, 'r') as f:
            data = json.load(f)
            return data


    def _update_metadata_archive(self, metadata_object):
        metadata_file = os.path.join(self.base_path, "metadata.json")
        if not os.path.exists(metadata_file):
            with open(metadata_file, 'w') as f:
                f.write("[]")
        
        with open(metadata_file, 'r+') as f:
            data = json.load(f)
            data.append(metadata_object)
            f.seek(0)
            json.dump(data, f, indent=4)

    def _clean_up_entries(self):
        """
        Checks if the length of the metadata archive reached a limit. If so, remove both the relevant SVG file and its
        entry for the oldest entries until we are below the configured TOTAL_IMAGES_LIMIT.
        """
        metadata_file = os.path.join(self.base_path, "metadata.json")
        if not os.path.exists(metadata_file):
            return

        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return

        if not isinstance(data, list):
            return

        # Ensure there's room for a new image: reduce until len < TOTAL_IMAGES_LIMIT
        while len(data) >= TOTAL_IMAGES_LIMIT:
            # Prefer removing the oldest by time_stamp if available and parseable
            oldest_index = None
            oldest_dt = None
            for i, entry in enumerate(data):
                ts = entry.get("time_stamp")
                if not ts:
                    continue
                try:
                    dt = datetime.strptime(ts, "%Y-%m-%d_%H-%M-%S")
                except Exception:
                    continue
                if oldest_dt is None or dt < oldest_dt:
                    oldest_dt = dt
                    oldest_index = i

            # Fallback to FIFO (first entry) if no valid time_stamp found
            if oldest_index is None:
                oldest_index = 0

            # Remove the file on disk if it exists
            entry = data.pop(oldest_index)
            path = entry.get("path")
            if path:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    # Ignore file removal errors; continue cleaning metadata
                    pass

        # Persist updated metadata
        try:
            with open(metadata_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception:
            # If writing fails, we silently ignore to avoid crashing the caller
            pass

            #### ----- AT TOOLS ----- ### 

    def create_svg_image(self, image_name, concept, content):
        final_name = make_string_file_safe(image_name)
        svg_path = os.path.join(self.base_path, f"{final_name}.svg")

        try:
            # Clean up old entries first to ensure room for the new one.
            self._clean_up_entries()

            # Try to create the image file.
            try:
                with open(svg_path, 'w') as svg_file:
                    svg_file.write(content)
            except IOError as e:
                # Handle file creation/writing errors specifically.
                print(f"An IOError occurred while creating the image file: {e}")
                return f"Failed to create the image file for concept {concept}. Error: {e}"

            current_datetime = datetime.now()
            safe_filename_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")

            # Now try to update the metadata.
            try:
                metadata_object = {
                    "image_name": final_name,
                    "concept": concept,
                    "path": svg_path,
                    "time_stamp": safe_filename_datetime
                }
                self._update_metadata_archive(metadata_object)
                return f"Image for concept {concept} created successfully with name {final_name} on path {svg_path}! Metadata archived for later usage."
            except Exception as e:
                # Handle metadata-related errors.
                # Remove the created image file to avoid orphaned files.
                if os.path.exists(svg_path):
                    os.remove(svg_path)
                print(f"An error occurred while updating metadata: {e}")
                return f"Image file for concept {concept} was created, but failed to update metadata. The file has been removed to prevent orphaned data. Error: {e}"

        except Exception as e:
            # This is a general catch-all for any other unexpected errors.
            print(f"An unexpected error occurred: {e}")
            return f"An unexpected error occurred during the image creation process. Error: {e}"
            

    def read_archive(self)->list:
        """
        Reads the metadata and returns an structured string for each of the entries.
        """
        metadata_file = os.path.join(self.base_path, "metadata.json")
        if not os.path.exists(metadata_file):
            return []

        with open(metadata_file, 'r') as f:
            data = json.load(f)
            return [f"Image Name: {entry['image_name']}, Concept: {entry['concept']}, Path: {entry['path']}" for entry in data]
