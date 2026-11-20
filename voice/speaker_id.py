"""Speaker verification: only act on the enrolled user's voice.

Uses a local speaker-embedding model (sherpa-onnx + 3D-Speaker CAM++). The voiceprint is one
averaged embedding in data/voiceprint.npy. This is a convenience filter, not strong security:
a good recording of your voice could still pass it.
"""
import numpy as np

import config

SAMPLE_RATE = 16000


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


class SpeakerVerifier:
    def __init__(self, threshold: float = config.SPEAKER_THRESHOLD, extractor=None) -> None:
        self.threshold = threshold
        self._extractor = extractor
        self.voiceprint: np.ndarray | None = None
        if config.VOICEPRINT_PATH.exists():
            self.voiceprint = np.load(config.VOICEPRINT_PATH)

    def enrolled(self) -> bool:
        return self.voiceprint is not None

    def _embed(self, audio: np.ndarray) -> np.ndarray:
        if self._extractor is None:
            import sherpa_onnx

            cfg = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(config.SPEAKER_MODEL), num_threads=1)
            self._extractor = sherpa_onnx.SpeakerEmbeddingExtractor(cfg)
        stream = self._extractor.create_stream()
        stream.accept_waveform(sample_rate=SAMPLE_RATE, waveform=audio.astype(np.float32))
        stream.input_finished()
        return np.array(self._extractor.compute(stream))

    def verify(self, audio: np.ndarray) -> tuple[bool, float | None]:
        """(accepted, score). With no voiceprint enrolled everything is accepted (score None)."""
        if self.voiceprint is None:
            return True, None
        score = cosine(self._embed(audio), self.voiceprint)
        return score >= self.threshold, score

    def enroll(self, samples: list[np.ndarray]) -> list[float]:
        """Average the embeddings of several utterances. Returns each sample's similarity to the average."""
        if len(samples) < 3:
            raise ValueError("Need at least 3 voice samples to enroll.")
        embs = [self._embed(s) for s in samples]
        embs = [e / (np.linalg.norm(e) + 1e-9) for e in embs]
        mean = np.mean(embs, axis=0)
        config.VOICEPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.save(config.VOICEPRINT_PATH, mean)
        self.voiceprint = mean
        return [cosine(e, mean) for e in embs]

    def clear(self) -> None:
        config.VOICEPRINT_PATH.unlink(missing_ok=True)
        self.voiceprint = None
