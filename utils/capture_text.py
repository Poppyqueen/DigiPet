# class to capture text and save for archival.

import os

class TextCapture:
    def __init__(self, filepath="captured_text.txt"):
        """
        Initializes the text capture manager with the path to the txt  file.
        """
        self.filepath = filepath  # Now filepath is configurable
        self._check_and_create_db()


    def _check_and_create_db(self):
        """
        internal function to check for and create a TXT fike if it does not exist
        """
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                f.write("Captured Text:\n")
            print(f"Text file created at: {self.filepath}")
        else:
            print(f"Text file already exists at: {self.filepath}")

    def dump_text(self, text):
        """
        Saves the captured text to the specified file.
        """
        try:
            with open(self.filepath, 'a') as f:
                f.write(text + "\n")
        except Exception as e:
            print(f"Error saving to text file: {e}")

