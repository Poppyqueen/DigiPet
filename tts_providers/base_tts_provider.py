# tts_providers/base_tts_provider.py
import abc # Abstract Base Classes

class BaseTTSProvider(abc.ABC):
    """
    Abstract Base Class (ABC) for Text-to-Speech (TTS) providers.
    All concrete TTS providers must inherit from this class and implement
    its abstract methods.
    """

    def __init__(self, signal_callback=None):
        """
        Initializes the TTS provider.

        Args:
            signal_callback: A callable function (e.g., method from CLIChatbot)
                             that the provider can use to send signals back
                             to the main application (e.g., speech started, error).
        """
        self._signal_callback = signal_callback
        # Internal flag to indicate if the provider is properly set up and available
        # (e.g., if the underlying command/library is found).
        self._is_available = False

    @abc.abstractmethod
    def synthesize(self, text: str) -> bool:
        """
        Converts the given text to speech.

        Args:
            text: The string to be spoken.

        Returns:
            True if speech synthesis was successfully initiated, False otherwise.
        """
        pass

    @abc.abstractmethod
    def stop(self) -> None:
        """
        Stops any currently playing speech immediately.
        """
        pass

    @abc.abstractmethod
    def is_playing(self) -> bool:
        """
        Checks if speech is currently being synthesized or played.

        Returns:
            True if speech is active, False otherwise.
        """
        pass

    @abc.abstractmethod
    def get_provider_name(self) -> str:
        """
        Returns a unique string identifier for this TTS provider (e.g., "macos_say", "espeak_ng").
        """
        pass

    def is_available(self) -> bool:
        """
        Returns whether the TTS provider is correctly configured and its
        underlying system/command is found.
        """
        return self._is_available

    def _send_signal(self, signal_data):
        """Helper to send signals via the callback if available."""
        if self._signal_callback:
            self._signal_callback(signal_data)
        else:
            # print(f"TTS Provider attempted to signal, but no callback registered: {signal_data}")
            pass # Suppress this print for cleaner output if no callback is critical