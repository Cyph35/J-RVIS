"""Text-to-speech via the built-in macOS `say` command."""
import re
import subprocess

import config


def clean_for_speech(text: str) -> str:
    """Strip markdown, URLs and emoji that sound bad when read aloud."""
    text = re.sub(r"https?://\S+", "link", text)
    text = re.sub(r"[`*_#>~\[\]]", "", text)
    text = re.sub(r"[^\x00-ɏ‘-”…]", "", text)  # drop emoji/symbols
    return re.sub(r"\s+", " ", text).strip()


class Speaker:
    def __init__(self, voice: str | None = config.SPEAK_VOICE, rate: int = config.SPEAK_RATE) -> None:
        self.voice = voice
        self.rate = rate
        self._proc: subprocess.Popen | None = None

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
