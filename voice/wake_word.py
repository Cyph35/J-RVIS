"""Wake-word detection. Only this runs while idle: no transcription, no audio is kept."""
import threading
import time

import numpy as np

import config

WAKE_CHUNK = 1280  # 80 ms at 16 kHz, what openWakeWord expects


class WakeWordDetector:
    def __init__(self, threshold: float = config.WAKE_THRESHOLD) -> None:
        from openwakeword.model import Model

        self.threshold = threshold
        self.model = Model(wakeword_models=[config.WAKE_WORD_MODEL], inference_framework="onnx")

    def score(self, chunk_int16: np.ndarray) -> float:
        return float(max(self.model.predict(chunk_int16).values()))

    def heard(self, chunk_int16: np.ndarray) -> bool:
        return self.score(chunk_int16) >= self.threshold

    def reset(self) -> None:
        self.model.reset()

    def wait_for_wake(self, stop: threading.Event, muted: threading.Event) -> bool:
        """Block until the wake word is heard (True) or `stop` is set (False).

        While `muted` is set the microphone stream is fully closed.
        """
        import sounddevice as sd

        self.reset()
        while not stop.is_set():
            if muted.is_set():
                time.sleep(0.2)
                continue
            with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=WAKE_CHUNK) as stream:
                while not stop.is_set() and not muted.is_set():
                    data, _ = stream.read(WAKE_CHUNK)
                    if self.heard(data[:, 0]):
                        return True
        return False
