# juke_box.py audio player for pygame

import pygame
import os

class jukebox:
    def __init__(self, base_song_path):
        self.is_muted = False
        self.previous_volume = 0.1 # Default music volume when unmuted
        self.sfx_volume = 0.11      # Default sound effect volume (0.0 to 1.0)

        # Attribute to track the last SFX channel (still needed for stopping previous SFX)
        self.current_sfx_channel = None

        self.current_sfx_hash = None

        self.initialized = False # Start as not initialized

        # Check and initialize mixer
        if not pygame.mixer.get_init():
            print("Warning: Pygame mixer not initialized. Attempting to initialize.")
            try:
                # Ensure freq, size, channels are specified for robust init
                # Default values often work, but explicit can help diagnose issues
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            except pygame.error as e:
                print(f"Error initializing mixer: {e}")
                self.initialized = False # Keep as False on failure
                # Do NOT return here, continue to check get_init()

        # Check again if mixer is actually initialized after our attempt
        if pygame.mixer.get_init():
             print("Pygame mixer successfully initialized.")
             self.initialized = True
             # Now that we know it's *initialized*, we can attempt
             # to set the global channel volume.
             # However, to avoid the specific error seen, let's *not* call
             # pygame.mixer.set_volume here. We'll rely on the set_volume method
             # being called later or apply volume per sound.

             # Load and play the initial song *if* initialized
             self.init_jukebox(base_song_path)
        else:
             # Mixer initialization failed, handle this state
             print("Error: Pygame mixer failed to initialize. Audio will be disabled.")
             self.initialized = False


    def init_jukebox(self, base_song_path):
        """
        Initializes the music mixer and starts playing the base song on loop.
        This is called from __init__ after mixer check.

        Args:
            base_song_path (str): The file path to the initial song (e.g., .ogg, .mp3).
        """
        if not self.initialized:
            print("Jukebox not initialized, skipping init_jukebox.")
            return

        if not os.path.exists(base_song_path):
            print(f"Error: Base song file not found at '{base_song_path}'")
            # Should probably mark initialization as problematic here
            return
        try:
            pygame.mixer.music.load(base_song_path)

            if self.is_muted:
                 pygame.mixer.music.set_volume(0)
            else:
                 pygame.mixer.music.set_volume(self.previous_volume)

            pygame.mixer.music.play(loops=-1)
            print(f"Jukebox initialized. Playing base song: {base_song_path} (Music Muted: {self.is_muted})")

        except pygame.error as e:
            print(f"Error loading or playing base song '{base_song_path}': {e}")


    def play_new_song(self, new_song_path):
        """
        Stops the current song and starts playing a new one on loop.
        Respects the current mute state and volume.

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
            pygame.mixer.music.stop()
            pygame.mixer.music.load(new_song_path)

            if self.is_muted:
                 pygame.mixer.music.set_volume(0)
            else:
                 pygame.mixer.music.set_volume(self.previous_volume)

            pygame.mixer.music.play(loops=-1)
            print(f"Jukebox changed song to: {new_song_path} (Music Muted: {self.is_muted})")

        except pygame.error as e:
            print(f"Error loading or playing new song '{new_song_path}': {e}")


    def toggle_mute(self):
        """Toggles the mute state of the background music."""
        if not self.initialized:
            print("Error: Jukebox not initialized. Cannot toggle music mute.")
            return

        if self.is_muted:
            # Unmute music
            pygame.mixer.music.set_volume(self.previous_volume)
            self.is_muted = False
            print(f"Background music unmuted. Restored volume: {self.previous_volume:.2f}")
        else:
            # Mute music
            self.previous_volume = pygame.mixer.music.get_volume() # Store current volume before muting
            pygame.mixer.music.set_volume(0)
            self.is_muted = True
            print("Background music muted.")

    # --- Modified set_volume method ---
    def set_volume(self, song_volume=None, sfx_volume=None):
         """
         Sets the volume for background music and/or sound effects.
         Args:
             song_volume (float, optional): The desired volume for the background music (0.0 to 1.0).
                                            If None, background music volume is not changed.
             sfx_volume (float, optional): The desired volume for sound effects (0.0 to 1.0).
                                           If None, sound effect volume is not changed.
         """
         if not self.initialized:
             print("Error: Jukebox not initialized. Cannot set volume.")
             return

         # Handle song volume if provided
         if song_volume is not None:
             vol = max(0.0, min(1.0, song_volume)) # Clamp volume
             pygame.mixer.music.set_volume(vol)
             # Only update the stored previous_volume if music is currently NOT muted.
             if not self.is_muted:
                  self.previous_volume = vol
             print(f"Background music volume set to: {vol:.2f}")

         # Handle sfx volume if provided
         # We store the desired sfx_volume and apply it when playing sounds.
         # Optionally, you *can* still use pygame.mixer.set_volume(sfx_vol) here
         # IF you are confident it is available after init.
         # If the initial error suggests it's not always available,
         # relying purely on sfx_sound.set_volume in play_sound_effect is safer.
         # Let's keep the pygame.mixer.set_volume call here, as it's the standard way
         # to set global channel volume *after* initialization. The error in __init__
         # might be transient.
         if sfx_volume is not None:
             sfx_vol = max(0.0, min(1.0, sfx_volume)) # Clamp volume
             # --- Corrected: Check if the function exists before calling ---
             # This is a workaround if pygame.mixer.set_volume is truly missing
             if hasattr(pygame.mixer, 'set_volume'):
                 pygame.mixer.set_volume(sfx_vol) # Set the global channel volume
             else:
                 # Fallback: Print warning, volume will rely only on per-sound setting
                 print("Warning: pygame.mixer.set_volume not available. SFX volume relies on per-sound setting.")

             self.sfx_volume = sfx_vol       # Store the value internally
             print(f"Sound effect volume set to: {sfx_vol:.2f}")

         # Optional: Add a check if neither volume was provided
         if song_volume is None and sfx_volume is None:
             print("Warning: set_volume called with no volume parameters.")


    def get_is_muted(self):
         """Returns the current mute state of the background music."""
         return self.is_muted

    def get_previous_volume(self):
         """Returns the volume level the music will return to when unmuted."""
         return self.previous_volume

    def get_sfx_volume(self):
        """Returns the current global sound effect volume."""
        return self.sfx_volume # Return our stored value


    def stop(self):
        """Stops the background music."""
        if self.initialized:
            pygame.mixer.music.stop()
            print("Music stopped.")

    def play_sound_effect(self, sound_path):
        """
        Loads and plays a sound effect without stopping background music.
        If a sound effect was previously started by this method and is still playing,
        it will be stopped before the new sound effect is played.
        Applies the stored SFX volume to the sound.

        Args:
            sound_path (str): The file path to the sound effect (e.g., .wav, .ogg).
        """
        if not self.initialized:
            print("Error: Jukebox not initialized. Cannot play sound effect.")
            return

        if not os.path.exists(sound_path):
            print(f"Error: Sound effect file not found at '{sound_path}'")
            return

        try:
            # Stop the previously tracked sound effect channel if it's busy
            if self.current_sfx_channel and self.current_sfx_channel.get_busy():
                self.current_sfx_channel.stop()

            # Load the new sound effect
            sfx_sound = pygame.mixer.Sound(sound_path)

            # --- Apply the stored SFX volume directly to the Sound object ---
            sfx_sound.set_volume(self.sfx_volume)
            # This is the most reliable way to ensure the desired volume
            # for *this specific sound instance*. It complements the
            # global pygame.mixer.set_volume call in set_volume.

            # Play the sound effect and store the channel
            self.current_sfx_channel = sfx_sound.play()
            print(f"Playing sound effect: {sound_path} (Volume: {self.sfx_volume:.2f})")

        except pygame.error as e:
            print(f"Error loading or playing sound effect '{sound_path}': {e}")
        except Exception as e:
             print(f"An unexpected error occurred playing sound effect '{sound_path}': {e}")


    def play_raw_sound_effect(self, raw_audio_data, sample_rate: int = 44100, override: bool = True):
        if not self.initialized or not raw_audio_data:
            return

        # 1. Generate a unique hash for this specific audio data
        # Using hash() is fast for bytes/bytearrays in Python
        incoming_hash = hash(raw_audio_data)

        # 2. Check if this exact sound is already playing
        if self.current_sfx_channel and self.current_sfx_channel.get_busy():
            if incoming_hash == self.current_sfx_hash:
                # It's the same sound and it hasn't finished yet. 
                # We skip to prevent "stacking" the same audio.
                return 

        try:
            import miniaudio

            if not isinstance(raw_audio_data, (bytes, bytearray)):
                raw_audio_data = bytes(raw_audio_data)

            # Decode the audio
            decoded = miniaudio.decode(
                raw_audio_data,
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=2,
                sample_rate=sample_rate,
            )

            raw_pcm = bytes(decoded.samples)
            sound = pygame.mixer.Sound(buffer=raw_pcm)
            sound.set_volume(self.sfx_volume)

            # 3. Handle Playback Logic
            if override:
                # Stop whatever was playing (even if it was a different sound)
                if self.current_sfx_channel and self.current_sfx_channel.get_busy():
                    self.current_sfx_channel.stop()
                
                self.current_sfx_channel = sound.play()
                self.current_sfx_hash = incoming_hash # Update the hash
            else:
                # If override is False, we only play if it's a DIFFERENT sound 
                # (The duplicate check above already handled the "same sound" case)
                temp_channel = sound.play()
                
                # We still update these so the *next* call knows what is currently "active"
                self.current_sfx_channel = temp_channel
                self.current_sfx_hash = incoming_hash

        except Exception as e:
            print(f"[Jukebox] Failed to play raw sound: {e}")