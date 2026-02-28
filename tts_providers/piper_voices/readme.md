# TTS Piper Voices

https://rhasspy.github.io/piper-samples/ [Piper Voices Examples]

https://huggingface.co/rhasspy/piper-voices/tree/main [Piper Voices Hugging Face]

https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md [Piper API Python]

Listen to the voices in the Piper Voices Examples Web Page, look for their information on Hugging Face, specially their licensing, and name. 

To download voices run:

python -m piper.download_voices en_US-libritts_r-medium --data-dir tts_providers/piper_voices/

voices_map={
    "aru_medium": "en_GB-aru-medium.onnx",
    "libritts-r-medium": "en_US-libritts_r-medium.onnx",
    "ryan_high": "en_US-ryan-high.onnx"
}


To download standard voices on MacOS or Linux:
printf "%s\n" en_GB-aru-medium en_US-libritts_r-medium en_US-ryan-high | xargs -I {} python -m piper.download_voices {} --data-dir tts_providers/piper_voices/