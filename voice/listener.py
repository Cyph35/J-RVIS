"""Microphone capture. Uses Silero VAD (neural speech detector) instead of loudness,
so steady noise (fans, traffic, music) is not mistaken for speech."""
import numpy as np

SAMPLE_RATE = 16000
CHUNK = 1920                      # 120 ms = 4 x 480-sample VAD frames
CHUNK_SEC = CHUNK / SAMPLE_RATE
SPEECH_PROB = 0.5
last_stats = {"max_prob": 0.0, "peak": 0.0}  # why the last recording failed


def describe_last() -> str:
    return f"mic level {last_stats['peak']:.2f}, speech confidence {last_stats['max_prob']:.2f}"


class EndpointDetector:
    """Feed one speech probability per chunk; tells when the speaker has finished."""

    def __init__(self, threshold: float = SPEECH_PROB, silence_sec: float = 0.9,
                 no_speech_timeout: float = 8.0, max_sec: float = 20.0, min_speech_chunks: int = 2) -> None:
        self.threshold = threshold
        self.silence_chunks = round(silence_sec / CHUNK_SEC)
        self.no_speech_chunks = round(no_speech_timeout / CHUNK_SEC)
        self.max_chunks = round(max_sec / CHUNK_SEC)
        self.min_speech_chunks = min_speech_chunks  # consecutive speech chunks before we call it speech
        self.n = self.quiet = self.run = 0
        self.heard_speech = False

    def feed(self, prob: float) -> str:
        """Return 'continue', 'done' (speech then silence/limit) or 'timeout' (never spoke)."""
        self.n += 1
        if prob >= self.threshold:
            self.run += 1
            self.quiet = 0
            if self.run >= self.min_speech_chunks:
                self.heard_speech = True
        else:
            self.run = 0
            self.quiet += 1
        if self.heard_speech and (self.quiet >= self.silence_chunks or self.n >= self.max_chunks):
            return "done"
        if not self.heard_speech and self.n >= self.no_speech_chunks:
            return "timeout"
        return "continue"


def record_utterance(on_status=print) -> np.ndarray | None:
    """Record one spoken request. Returns float32 mono audio, or None if nobody spoke."""
    import sounddevice as sd
    from openwakeword.vad import VAD

    from voice.audio import input_device

    vad = VAD()
    detector = EndpointDetector()
    frames: list[np.ndarray] = []
    last_stats.update(max_prob=0.0, peak=0.0)
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=CHUNK,
                        device=input_device()) as stream:
        on_status("[listening...]")
        while True:
            data, _ = stream.read(CHUNK)
            chunk = data[:, 0].copy()
            frames.append(chunk)
            prob = float(vad.predict(chunk, frame_size=480))
            last_stats["max_prob"] = max(last_stats["max_prob"], prob)
            last_stats["peak"] = max(last_stats["peak"], float(np.abs(chunk).max()) / 32768)
            state = detector.feed(prob)
            if state == "timeout":
                return None
            if state == "done":
                break
    return np.concatenate(frames).astype(np.float32) / 32768.0
