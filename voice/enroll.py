"""Guided voice enrollment shared by the CLI and the GUI."""
from typing import Callable

import numpy as np

PHRASES = [
    "Hey Jarvis, what time is it?",
    "Open Calculator and search the web for Python tutorials.",
    "Play some music and tell me how much battery I have left.",
    "Jarvis, find my files and remind me what is on my screen.",
    "This is my voice, and I am the only one Jarvis should listen to.",
]


def run_enrollment(verifier, record: Callable[[], np.ndarray | None], say: Callable[[str], None],
                   chime: Callable[[], None] = lambda: None) -> str:
    samples = []
    for i, phrase in enumerate(PHRASES, 1):
        for attempt in range(2):
            say(f"[{i}/{len(PHRASES)}] Say: \"{phrase}\"")
            chime()
            audio = record()
            if audio is not None and len(audio) >= 16000:  # at least 1 second of speech
                samples.append(audio)
                break
            say("   didn't catch that, trying once more...")
    if len(samples) < 3:
        return "Enrollment failed: not enough clear voice samples. Try again in a quieter spot."
    scores = verifier.enroll(samples)
    return ("Voice enrolled. Consistency scores: " + ", ".join(f"{s:.2f}" for s in scores)
            + f". JARVIS now ignores voices below {verifier.threshold:.2f} similarity.")
