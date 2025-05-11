# Assuming this is your jukebox.py file content

import pygame
import os # Useful for checking if files exist

# Assume pygame.init() has been called, which includes pygame.mixer.init()

class jukebox:
    def __init__(self, base_song_path):
        self.is_muted = False
        self.previous_volume = 0.1 # Default volume, will be updated after load

        # Check if mixer is initialized (usually handled by pygame.init())
        if not pygame.mixer.get_init():
            print("Warning: Pygame mixer not initialized. Attempting to initialize.")
            try:
                pygame.mixer.init()
            except pygame.error as e:
                print(f"Error initializing mixer: {e}")
                self.initialized = False
                return # Cannot proceed without mixer
        self.initialized = True # Mixer is ready

        # Load and play the initial song
        if self.initialized:
            self.init_jukebox(base_song_path)

    def init_jukebox(self, base_song_path):
        """
        Initializes the music mixer and starts playing the base song on loop.
        This is called from __init__ after mixer check.

        Args:
            base_song_path (str): The file path to the initial song (e.g., .ogg, .mp3).
        """
        if not self.initialized: return

        if not os.path.exists(base_song_path):
            print(f"Error: Base song file not found at '{base_song_path}'")
            # Optionally, set initialized = False or handle this error
            return
        try:
            # Load the music file
            pygame.mixer.music.load(base_song_path)

            # Set volume based on mute state and previous volume
            if self.is_muted:
                 pygame.mixer.music.set_volume(0)
            else:
                 pygame.mixer.music.set_volume(self.previous_volume) # Use default or previously stored

            # Play the music on loop (-1 means loop indefinitely)
            pygame.mixer.music.play(loops=-1)
            print(f"Jukebox initialized. Playing base song: {base_song_path} (Muted: {self.is_muted})")

        except pygame.error as e:
            print(f"Error loading or playing base song '{base_song_path}': {e}")
            # Handle error - maybe stop attempts to play music?
            # self.initialized = False # Or some other state management

    def play_new_song(self, new_song_path):
        """
        Stops the current song and starts playing a new one on loop.
        Respects the current mute state.

        Args:
            new_song_path (str): The file path to the new song.
        """
        if not self.initialized:
            print("Error: Jukebox not initialized. Cannot change song.")
            return

        if not os.path.exists(new_song_path):
            print(f"Error: New song file not found at '{new_song_path}'")
            return

        try:
            # Stop the currently playing music
            pygame.mixer.music.stop()
            # Load the new music file
            pygame.mixer.music.load(new_song_path)

            # Set volume based on mute state
            if self.is_muted:
                 pygame.mixer.music.set_volume(0) # Keep muted
            else:
                 pygame.mixer.music.set_volume(self.previous_volume) # Use last active volume (0.1 initially)

            # Play the new music on loop (-1 means loop indefinitely)
            pygame.mixer.music.play(loops=-1)
            print(f"Jukebox changed song to: {new_song_path} (Muted: {self.is_muted})")

        except pygame.error as e:
            print(f"Error loading or playing new song '{new_song_path}': {e}")
            # You might want to add fallback logic here,
            # like trying to resume the previous song or play silence.

    def toggle_mute(self):
        """Toggles the mute state of the background music."""
        if not self.initialized:
            print("Error: Jukebox not initialized. Cannot toggle mute.")
            return

        if self.is_muted:
            # Unmute: Restore the previous volume
            pygame.mixer.music.set_volume(self.previous_volume)
            self.is_muted = False
            print(f"Music unmuted. Restored volume: {self.previous_volume:.2f}")
        else:
            # Mute: Store current volume and set to 0
            # Get current volume before setting to 0, just in case it changed somehow
            self.previous_volume = pygame.mixer.music.get_volume()
            pygame.mixer.music.set_volume(0)
            self.is_muted = True
            print("Music muted.")

    # Optional: Method to explicitly set volume (could update previous_volume)
    def set_volume(self, volume):
         if not self.initialized: return
         vol = max(0.0, min(1.0, volume)) # Clamp volume between 0 and 1
         pygame.mixer.music.set_volume(vol)
         if not self.is_muted:
              self.previous_volume = vol # Only update previous if not currently muted
         print(f"Music volume set to: {vol:.2f}")

    # Optional: Method to get current mute state
    def get_is_muted(self):
         return self.is_muted

    # Optional: Method to get previous volume
    def get_previous_volume(self):
         return self.previous_volume

    # You might want a stop method as well, though play(-1) is usually enough
    def stop(self):
        if self.initialized:
            pygame.mixer.music.stop()
            print("Music stopped.")