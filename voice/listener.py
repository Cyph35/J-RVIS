"""Microphone capture with simple energy-based end-of-speech detection."""
import numpy as np

SAMPLE_RATE = 16000
CHUNK_SEC = 0.1


class EndpointDetector:
    """Feed one RMS value per chunk; tells when the speaker has finished."""

    def __init__(self, threshold: float, silence_sec: float = 1.0,
                 no_speech_timeout: float = 8.0, max_sec: float = 20.0) -> None:
        self.threshold = threshold
        self.silence_chunks = int(silence_sec / CHUNK_SEC)
        self.no_speech_chunks = int(no_speech_timeout / CHUNK_SEC)
        self.max_chunks = int(max_sec / CHUNK_SEC)
        self.n = 0
        self.quiet = 0
        self.heard_speech = False

    def feed(self, rms: float) -> str:
        """Return 'continue', 'done' (speech then silence/limit) or 'timeout' (never spoke)."""
        self.n += 1
        if rms >= self.threshold:
            self.heard_speech = True
            self.quiet = 0
        else:
            self.quiet += 1
        if self.heard_speech and (self.quiet >= self.silence_chunks or self.n >= self.max_chunks):
            return "done"
        if not self.heard_speech and self.n >= self.no_speech_chunks:
            return "timeout"
        return "continue"


def record_utterance(on_status=print) -> np.ndarray | None:
    """Record one spoken request. Returns float32 mono audio, or None if nobody spoke."""
    import sounddevice as sd  # imported lazily so tests don't need a mic

    chunk = int(SAMPLE_RATE * CHUNK_SEC)
    frames: list[np.ndarray] = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=chunk) as stream:
        # Calibrate against ambient noise for ~0.5s.
        ambient = [float(np.sqrt(np.mean(stream.read(chunk)[0] ** 2))) for _ in range(5)]
        threshold = max(0.015, 3 * float(np.mean(ambient)))
        detector = EndpointDetector(threshold)
        on_status("[listening...]")
        while True:
            data, _ = stream.read(chunk)
            frames.append(data[:, 0].copy())
            state = detector.feed(float(np.sqrt(np.mean(data ** 2))))
            if state == "timeout":
                return None
            if state == "done":
                break
    return np.concatenate(frames)
