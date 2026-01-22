import threading
import sounddevice as sd
from piper import PiperVoice
from tts_providers.base_tts_provider import BaseTTSProvider
import os

VOICES_PATH = "tts_providers/piper_voices/"

# Update this dictionary with your downloaded Piper voices and choose an alias for each voice to use on the application configuration screen.
voices_map={
    "aru_medium": "en_GB-aru-medium.onnx",
    "libritts-r-medium": "en_US-libritts_r-medium.onnx",
    "ryan_high": "en_US-ryan-high.onnx"
}


class PiperTTSProvider(BaseTTSProvider):
    def __init__(self, voice_name="libritts-r-medium", signal_callback=None):
        use_cuda = False # TODO: Figure out how to change this on the fly preferably without torch?
        super().__init__(signal_callback)
        if voice_name == "":
            voice_name = "libritts-r-medium"
        if voice_name not in voices_map:
            raise ValueError(f"Invalid voice name: {voice_name}, please register your voice or select a valid voice name in tts_providers/piper_provider.py")
        full_path = os.path.join(VOICES_PATH, voices_map[voice_name])
        if not os.path.exists(full_path):
            raise ValueError(f"Voice file not found: {full_path}, for voice selected: {voice_name}. Make sure the voice onnx file is downloaded and placed in the correct directory. {VOICES_PATH}")
        self.model_path = full_path
        self.use_cuda = use_cuda
        
        # Threading and State management
        self._stop_event = threading.Event()
        self._is_playing = False
        self._thread = None
        
        try:
            self.voice = PiperVoice.load(self.model_path, use_cuda=self.use_cuda)
            self._is_available = True
        except Exception as e:
            print(f"Failed to load Piper voice: {e}")
            self._is_available = False

    def get_provider_name(self) -> str:
        return "piper_tts"

    def is_playing(self) -> bool:
        return self._is_playing

    def stop(self) -> None:
        """Sets the stop event and waits for the thread to clean up."""
        if self._is_playing:
            self._stop_event.set()
            if self._thread:
                self._thread.join()
            self._is_playing = False

    def synthesize(self, text: str) -> bool:
        if not self._is_available:
            return False
        
        # If already speaking, stop the old one first
        if self._is_playing:
            self.stop()

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._speech_worker, args=(text,))
        self._thread.start()
        return True

    def _speech_worker(self, text: str):
        """The background worker that streams audio to the speakers."""
        self._is_playing = True
        # self._send_signal({"status": "started", "text": text}) # these signals are not real

        try:
            # Initialize the audio stream
            # Piper default: 22050Hz, 16-bit Mono
            with sd.RawOutputStream(
                samplerate=22050, 
                blocksize=1024, 
                channels=1, 
                dtype='int16'
            ) as stream:
                for chunk in self.voice.synthesize(text):
                    # Check if we were told to stop mid-sentence
                    if self._stop_event.is_set():
                        break
                    
                    stream.write(chunk.audio_int16_bytes)
        
        except Exception as e:
            print(f"Error during speech synthesis: {e}")
            # self._send_signal({"status": "error", "message": str(e)}) # these signals are not real
        finally:
            self._is_playing = False
            # self._send_signal({"status": "finished"}) # these signals are not real