"""Wake-word detection. Only this runs while idle: no transcription, no audio is kept."""
import threading
import time

import numpy as np

import config

WAKE_CHUNK = 1280  # 80 ms at 16 kHz, what openWakeWord expects
RECHECK_SEC = 20  # re-scan for a changed default microphone this often


class WakeWordDetector:
    def __init__(self, threshold: float = config.WAKE_THRESHOLD) -> None:
        from openwakeword.model import Model

        self.threshold = threshold
        self.mic_name = ""
        self.on_mic_change = None  # optional callback(name) when the microphone in use changes
        self.model = Model(wakeword_models=[config.WAKE_WORD_MODEL], inference_framework="onnx")

    def score(self, chunk_int16: np.ndarray) -> float:
        return float(max(self.model.predict(chunk_int16).values()))

    def heard(self, chunk_int16: np.ndarray) -> bool:
        return self.score(chunk_int16) >= self.threshold

    def reset(self) -> None:
        self.model.reset()

    def wait_for_wake(self, stop: threading.Event, muted: threading.Event,
                      manual: threading.Event | None = None) -> bool:
        """Block until the wake word is heard OR `manual` (hotkey/menu) is set (True), or `stop` is set (False).

        While `muted` is set the microphone stream is fully closed.
        """
        import sounddevice as sd

        from voice.audio import input_device, input_name, refresh_devices

        self.reset()
        while not stop.is_set():
            if muted.is_set():
                if manual is not None:
                    manual.clear()  # a hotkey press while muted is ignored
                time.sleep(0.2)
                continue
            refresh_devices()  # no stream is open here, so a re-scan is safe
            try:
                name = input_name()
                if name != self.mic_name:
                    self.mic_name = name
                    if self.on_mic_change:
                        self.on_mic_change(name)
                opened = time.time()
                with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=WAKE_CHUNK,
                                    device=input_device()) as stream:
                    while not stop.is_set() and not muted.is_set() and time.time() - opened < RECHECK_SEC:
                        if manual is not None and manual.is_set():
                            manual.clear()
                            return True
                        data, _ = stream.read(WAKE_CHUNK)
                        if self.heard(data[:, 0]):
                            return True
            except sd.PortAudioError:
                time.sleep(1.0)  # mic unplugged or busy: wait and look again
        return False
