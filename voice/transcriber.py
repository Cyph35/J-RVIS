"""Local speech-to-text using faster-whisper (runs fully offline after first model download)."""
import numpy as np

import config


class Transcriber:
    def __init__(self, model_size: str = config.WHISPER_MODEL) -> None:
        from faster_whisper import WhisperModel

        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio: np.ndarray) -> str:
        """audio: float32 mono at 16 kHz."""
        segments, _ = self.model.transcribe(audio, language="en", beam_size=1, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()
