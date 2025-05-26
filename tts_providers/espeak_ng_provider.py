# tts_providers/espeak_ng_provider.py 
import subprocess
from .base_tts_provider import BaseTTSProvider

class ESpeakNGProvider(BaseTTSProvider):
    """
    TTS provider using the 'espeak-ng' command-line tool.
    Manages the 'espeak-ng' subprocess directly.
    """
    _PROVIDER_NAME = "espeak_ng"
    _DEFAULT_VOICE = "en-us" # Keep this as a general default, or remove if you always pass a voice

    def __init__(self, signal_callback=None, voice_name: str = None):
        super().__init__(signal_callback)

        self._current_process = None
        # This line correctly prioritizes the passed 'voice' argument
        self._voice = voice_name if voice_name else self._DEFAULT_VOICE
        self._check_availability()

    def _check_availability(self):
        """Checks if the 'espeak-ng' command is available."""
        try:
            subprocess.run(['command', '-v', 'espeak-ng'], check=True, capture_output=True)
            self._is_available = True
            print(f"TTS Provider '{self._PROVIDER_NAME}' is available with voice '{self._voice}'.")
            
            # Optional: Add a more specific check for MBROLA voices
            # This is harder to do programmatically as espeak-ng doesn't have a direct "check voice" flag.
            # If the synthesize call fails, that's usually the indicator.
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"Warning: '{self._PROVIDER_NAME}' provider selected, but 'espeak-ng' command not found or not executable. Please install it (e.g., 'sudo apt-get install espeak-ng' or 'brew install espeak-ng'). TTS will be disabled for this provider.")
            self._is_available = False

    def synthesize(self, text: str) -> bool:
        if not self._is_available:
            print(f"Error: '{self._PROVIDER_NAME}' provider is not available.")
            return False

        self.stop()

        try:
            command = ['espeak-ng', '-v', self._voice, text]
            print(f"Executing espeak-ng command: {' '.join(command)}") # For debugging
            self._current_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self._send_signal({"type": "TTS_STARTED", "provider": self.get_provider_name()})
            return True
        except FileNotFoundError:
            print(f"Error: 'espeak-ng' command not found when trying to synthesize with '{self._PROVIDER_NAME}'.")
            self._is_available = False
            self._current_process = None
            return False
        except Exception as e:
            print(f"An error occurred during '{self._PROVIDER_NAME}' synthesis: {e}")
            self._current_process = None
            return False

    def stop(self) -> None:
        if self._current_process and self._current_process.poll() is None:
            print(f"Stopping '{self._PROVIDER_NAME}' process...")
            try:
                self._current_process.kill()
                self._current_process.wait(timeout=1)
                self._send_signal({"type": "TTS_STOPPED", "provider": self.get_provider_name()})
            except ProcessLookupError:
                pass
            except Exception as e:
                print(f"Error stopping '{self._PROVIDER_NAME}' process: {e}")
        self._current_process = None

    def is_playing(self) -> bool:
        if self._current_process:
            return self._current_process.poll() is None
        return False

    def get_provider_name(self) -> str:
        return self._PROVIDER_NAME

# --- How you would use it elsewhere ---
if __name__ == "__main__":
    # Dummy signal handler for testing
    def my_signal_handler(signal):
        print(f"Signal received: {signal}")

    # Test with the default voice (en-us)
    print("\n--- Testing with default voice (en-us) ---")
    espeak_default = ESpeakNGProvider(signal_callback=my_signal_handler)
    if espeak_default._is_available:
        espeak_default.synthesize("Hello, this is the default voice.")
        import time
        time.sleep(2) # Give it time to play
        espeak_default.stop()

    # Test with us-mbrola-1 voice
    print("\n--- Testing with en-us+us-mbrola-1 voice ---")
    # Make sure you have the MBROLA voice data and MBROLA binary installed for this to work!
    # e.g., sudo apt-get install mbrola mbrola-us1
    espeak_mbrola = ESpeakNGProvider(signal_callback=my_signal_handler, voice="en-us+us-mbrola-1")
    if espeak_mbrola._is_available:
        espeak_mbrola.synthesize("Hello, this is the MBROLA voice. I hope it works.")
        import time
        time.sleep(3)
        espeak_mbrola.stop()

    print("\n--- Testing with a different espeak-ng internal voice (e.g., en-gb) ---")
    espeak_gb = ESpeakNGProvider(signal_callback=my_signal_handler, voice="en-gb")
    if espeak_gb._is_available:
        espeak_gb.synthesize("Hello, this is the British English voice.")
        import time
        time.sleep(2)
        espeak_gb.stop()