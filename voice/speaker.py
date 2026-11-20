"""Text-to-speech via the built-in macOS `say` command."""
import re
import subprocess
import threading

import config


def clean_for_speech(text: str) -> str:
    """Strip markdown, URLs and emoji that sound bad when read aloud."""
    text = re.sub(r"https?://\S+", "link", text)
    text = re.sub(r"\s*[\u2013\u2014]\s*", ", ", text)  # dashes become a natural pause, not a dropped word
    text = re.sub(r"[`*_#>~\[\]]", "", text)
    text = re.sub(r"[^\x00-ɏ‘-”…]", "", text)  # drop emoji/symbols
    return re.sub(r"\s+", " ", text).strip()


class Speaker:
    def __init__(self, voice: str | None = config.SPEAK_VOICE, rate: int = config.SPEAK_RATE) -> None:
        self.voice = voice
        self.rate = rate
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()  # one voice at a time

    def _cmd(self, text: str, voice: str | None) -> list[str]:
        cmd = ["say", "-r", str(self.rate)]
        if voice:
            cmd += ["-v", voice]
        return cmd + ["--", text]

    def speak(self, text: str) -> bool:
        """Speak and block until finished. Returns False (never raises) if audio failed."""
        text = clean_for_speech(text)
        if not text:
            return True
        with self._lock:
            return self._speak(text)

    def _speak(self, text: str) -> bool:
        for voice in (self.voice, None):  # fall back to the system voice if ours is missing
            try:
                self._proc = subprocess.Popen(self._cmd(text, voice), stderr=subprocess.PIPE)
                _, err = self._proc.communicate()
                if self._proc.returncode == 0:
                    return True
                if self._proc.returncode < 0:  # stopped by stop()
                    return True
            except (OSError, subprocess.SubprocessError):
                return False
        return False

    def stop(self) -> None:
        """Interrupt speech in progress (e.g. from another thread or Ctrl+C)."""
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


def split_sentences(text: str) -> list[str]:
    """Sentence chunks so playback starts after the first one is synthesized."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    merged: list[str] = []
    for p in parts:
        if merged and len(merged[-1]) < 25:  # avoid tiny fragments like "Ok."
            merged[-1] += " " + p
        else:
            merged.append(p)
    return merged


class NaturalSpeaker:
    """Local neural TTS (Kokoro). Falls back to the macOS `say` voice if anything goes wrong."""

    def __init__(self, voice: str = config.KOKORO_VOICE, speed: float = config.KOKORO_SPEED) -> None:
        from kokoro_onnx import Kokoro

        self.voice, self.speed = voice, speed
        self.lang = "en-gb" if voice.startswith("b") else "en-us"
        self.engine = Kokoro(str(config.KOKORO_MODEL), str(config.KOKORO_VOICES))
        self.fallback = Speaker()
        self._lock = threading.Lock()
        self._stopped = threading.Event()

    def _synth(self, sentence: str):
        return self.engine.create(sentence, voice=self.voice, speed=self.speed, lang=self.lang)

    def speak(self, text: str) -> bool:
        text = clean_for_speech(text)
        if not text:
            return True
        with self._lock:
            self._stopped.clear()
            try:
                import numpy as np
                import sounddevice as sd

                from voice import audio

                # 1) Synthesize everything first so the CPU is idle during playback (no glitches).
                pieces, rate = [], 24000
                for sentence in split_sentences(text):
                    if self._stopped.is_set():
                        return True
                    chunk, rate = self._synth(sentence)
                    chunk = np.asarray(chunk, dtype=np.float32).copy()
                    fade = int(rate * 0.012)  # 12 ms fades remove clicks at sentence edges
                    chunk[:fade] *= np.linspace(0, 1, fade)
                    chunk[-fade:] *= np.linspace(1, 0, fade)
                    pieces += [chunk, np.zeros(int(rate * 0.18), dtype=np.float32)]  # natural pause
                wave = np.concatenate(pieces)
                # 2) Play one continuous buffer with a large, safe audio buffer.
                audio.OUTPUT_ACTIVE.set()
                try:
                    sd.play(wave, rate, latency="high")
                    sd.wait()
                finally:
                    audio.OUTPUT_ACTIVE.clear()
                return True
            except Exception:
                return self.fallback.speak(text)

    def stop(self) -> None:
        self._stopped.set()
        try:
            import sounddevice as sd

            sd.stop()
        except Exception:
            pass
        self.fallback.stop()


def make_speaker():
    """Best available voice: Kokoro neural voice if set up, otherwise the macOS voice."""
    if config.TTS_ENGINE != "say" and config.KOKORO_MODEL.exists() and config.KOKORO_VOICES.exists():
        try:
            return NaturalSpeaker()
        except Exception:
            if config.TTS_ENGINE == "kokoro":
                raise
    return Speaker()
