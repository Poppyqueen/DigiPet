import os
import json

import re

from datetime import datetime

TOTAL_IMAGES_LIMIT=100

def make_filename_safe(filename_string, replacement_char='_'):
    """
    Converts a string into a file-system safe filename by replacing invalid characters.

    Args:
        filename_string (str): The original string to sanitize.
        replacement_char (str): The character to replace invalid characters with.
                                Defaults to an underscore '_'.

    Returns:
        str: The sanitized filename string.
    """
    # Define a regular expression pattern for invalid filename characters.
    # This pattern covers common invalid characters across Windows, macOS, and Linux.
    # It excludes characters like '/', '\', ':', '*', '?', '"', '<', '>', '|'
    # and also control characters and leading/trailing spaces/dots.
    invalid_chars_pattern = r'[<>:"/\\|?*\x00-\x1F]'

    # Replace invalid characters with the specified replacement_char
    safe_filename = re.sub(invalid_chars_pattern, replacement_char, filename_string)

    # Handle reserved names (case-insensitive for Windows)
    reserved_names = ['con', 'prn', 'aux', 'nul', 'com0', 'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9', 'lpt0', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9']
    if safe_filename.lower() in reserved_names:
        safe_filename = replacement_char + safe_filename

    # Remove leading/trailing spaces and dots
    safe_filename = safe_filename.strip(' .')

    # Collapse multiple replacement characters into a single one
    safe_filename = re.sub(f'{re.escape(replacement_char)}+', replacement_char, safe_filename)

    return safe_filename


class ImagesLab:
    def __init__(self, base_path):
        self.base_path = os.path.join(base_path, "images_archive")
        os.makedirs(self.base_path, exist_ok=True)

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
            final_name=make_filename_safe(image_name)
            svg_path = os.path.join(self.base_path, f"{final_name}.svg")
            
            try:
                # 1. Clean up old entries first to ensure room for the new one.
                self._clean_up_entries()


                # 2. Create the image file.
                with open(svg_path, 'w') as svg_file:
                    svg_file.write(content)
                            
                current_datetime = datetime.now()
                safe_filename_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")

                # 3. Update the metadata.
                metadata_object = {
                    "image_name": final_name,
                    "concept": concept,
                    "path": svg_path,
                    "time_stamp": safe_filename_datetime
                }
                self._update_metadata_archive(metadata_object)
                return f"Image for concept {concept} created successfully with name {final_name} on path {svg_path}! Metadata archived for later usage."

            except Exception as e:
                if os.path.exists(svg_path):
                    os.remove(svg_path)
                
                print(f"An error occurred: {e}")
                return f"Failed to create image and/or update metadata."
            

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
