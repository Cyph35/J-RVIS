"""Local speech-to-text using faster-whisper (offline after the first model download)."""
import numpy as np

import config

# Biases recognition toward the words JARVIS actually needs.
PROMPT = "JARVIS assistant commands: open, close, search, Spotify, Safari, Chrome, Calculator, music, time, weather."


class Transcriber:
    def __init__(self, model_size: str = config.WHISPER_MODEL) -> None:
        from faster_whisper import WhisperModel

        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio: np.ndarray) -> str:
        """audio: float32 mono at 16 kHz. Drops segments Whisper itself thinks are not speech."""
        segments, _ = self.model.transcribe(
            audio, language="en", beam_size=5, vad_filter=True, initial_prompt=PROMPT,
            condition_on_previous_text=False, no_speech_threshold=0.6, log_prob_threshold=-1.0)
        kept = [s.text.strip() for s in segments if s.no_speech_prob < 0.6 and s.avg_logprob > -1.0]
        return " ".join(kept).strip()
