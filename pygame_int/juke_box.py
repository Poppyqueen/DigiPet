import pygame
import os # Useful for checking if files exist

# Assume pygame.init() has been called, which includes pygame.mixer.init()
# If you initialized pygame with specific modules, make sure mixer is included:
# pygame.init() # or pygame.mixer.init() after pygame.base.init()

class jukebox:
    def __init__(self, base_song_path):
        self.init_jukebox(base_song_path)


    def init_jukebox(self, base_song_path):
        """
        Initializes the music mixer and starts playing the base song on loop.

        Args:
            base_song_path (str): The file path to the initial song (e.g., .ogg, .mp3).
        """
        # Check if mixer is initialized (usually handled by pygame.init())
        if not pygame.mixer.get_init():
            print("Warning: Pygame mixer not initialized. Attempting to initialize.")
            try:
                pygame.mixer.init()
            except pygame.error as e:
                print(f"Error initializing mixer: {e}")
                return # Cannot proceed without mixer

        if not os.path.exists(base_song_path):
            print(f"Error: Base song file not found at '{base_song_path}'")
            return
        try:
            # Load the music file
            pygame.mixer.music.load(base_song_path)
            pygame.mixer.music.set_volume(0.1)

            # Play the music on loop (-1 means loop indefinitely)
            pygame.mixer.music.play(loops=-1)
            print(f"Jukebox initialized. Playing base song: {base_song_path}")
        except pygame.error as e:
            print(f"Error loading or playing base song '{base_song_path}': {e}")

    # Example of where you might call this (e.g., in your main game setup function)
    # In your main setup, after screen setup but before the main loop:
    # init_jukebox("path/to/your/default_music.ogg")


    def play_new_song(self, new_song_path):
        """
        Stops the current song and starts playing a new one on loop.

        Args:
            new_song_path (str): The file path to the new song.
        """
        if not pygame.mixer.get_init():
            print("Error: Pygame mixer not initialized. Cannot change song.")
            return # Cannot change song

        if not os.path.exists(new_song_path):
            print(f"Error: New song file not found at '{new_song_path}'")
            return

        try:
            # Stop the currently playing music
            pygame.mixer.music.stop()
            # Load the new music file
            pygame.mixer.music.load(new_song_path)
            # Play the new music on loop (-1 means loop indefinitely)
            pygame.mixer.music.play(loops=-1)
            print(f"Jukebox changed song to: {new_song_path}")
        except pygame.error as e:
            print(f"Error loading or playing new song '{new_song_path}': {e}")
            # You might want to add fallback logic here,
            # like trying to resume the previous song or play silence.