# tts_providers/macos_say_provider.py
import sys
import subprocess
from .base_tts_provider import BaseTTSProvider

class MacOSSaiProvider(BaseTTSProvider):
    """
    TTS provider for macOS using the 'say' command.
    Manages the 'say' subprocess directly.
    """
    _PROVIDER_NAME = "macos_say"

    def __init__(self, signal_callback=None):
        # Fix: Only pass signal_callback to the BaseTTSProvider's __init__.
        # The BaseTTSProvider does not have a 'sub_directory' parameter.
        super().__init__(signal_callback)

        # If sub_directory was intended for use by MacOSSaiProvider,
        # it would be stored here, e.g., self._sub_directory = sub_directory
        # However, in the provided code, it's not used, so this line isn't strictly needed unless it's used elsewhere.

        self._current_process = None  # To hold the Popen object for 'say'
        self._check_availability()

    def _check_availability(self):
        """Checks if the 'say' command is available on macOS."""
        if sys.platform == 'darwin':
            # Check if 'say' command exists and is executable
            try:
                # Use subprocess.run with shell=True for 'which' or 'command -v'
                # and capture output to check if it's found.
                # 'say' is usually always present on macOS, so a direct check isn't strictly necessary,
                # but it's good practice for robustness.
                subprocess.run(['command', '-v', 'say'], check=True, capture_output=True)
                self._is_available = True
                print(f"TTS Provider '{self._PROVIDER_NAME}' is available.")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"Warning: '{self._PROVIDER_NAME}' provider selected, but 'say' command not found or not executable. TTS will be disabled for this provider.")
                self._is_available = False
        else:
            print(f"Warning: '{self._PROVIDER_NAME}' provider selected, but not on macOS. TTS will be disabled for this provider.")
            self._is_available = False

    def synthesize(self, text: str) -> bool:
        """
        Initiates speech synthesis using the 'say' command.
        """
        if not self._is_available:
            print(f"Error: '{self._PROVIDER_NAME}' provider is not available.")
            return False

        # Ensure any previous speech is stopped before starting new one
        self.stop()

        try:
            # Use subprocess.Popen to run the command in the background.
            self._current_process = subprocess.Popen(
                ['say', text],
                stdout=subprocess.DEVNULL, # Discard stdout
                stderr=subprocess.DEVNULL  # Discard stderr
            )
            self._send_signal({"type": "TTS_STARTED", "provider": self.get_provider_name()})
            return True
        except FileNotFoundError:
            print(f"Error: 'say' command not found when trying to synthesize with '{self._PROVIDER_NAME}'.")
            self._is_available = False # Mark as unavailable if it fails
            self._current_process = None
            return False
        except Exception as e:
            print(f"An error occurred during '{self._PROVIDER_NAME}' synthesis: {e}")
            self._current_process = None
            return False

    def stop(self) -> None:
        """
        Stops any currently playing speech by terminating the 'say' process.
        """
        if self._current_process and self._current_process.poll() is None:
            # Process is still running
            print(f"Stopping '{self._PROVIDER_NAME}' process...")
            try:
                self._current_process.kill() # Forceful stop
                self._current_process.wait(timeout=1) # Give it a moment to terminate
                self._send_signal({"type": "TTS_STOPPED", "provider": self.get_provider_name()})
            except ProcessLookupError:
                # Process already terminated between poll() and kill()
                pass
            except Exception as e:
                print(f"Error stopping '{self._PROVIDER_NAME}' process: {e}")
        self._current_process = None # Clear the reference

    def is_playing(self) -> bool:
        """
        Checks if the 'say' command process is currently active.
        """
        if self._current_process:
            return self._current_process.poll() is None # Returns None if still running
        return False

    def get_provider_name(self) -> str:
        """
        Returns the unique identifier for this provider.
        """
        return self._PROVIDER_NAME