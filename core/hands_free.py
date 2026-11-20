"""Hands-free loop: wake word -> record -> transcribe -> assistant -> speak."""
import subprocess
import threading
from typing import Callable

from core.state import State, StateTracker

YES = {"yes", "yeah", "yep", "sure", "confirm", "do it", "go ahead", "okay", "ok", "proceed"}


def chime() -> None:
    try:
        subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], timeout=3)
    except Exception:
        pass


def is_yes(text: str) -> bool:
    t = text.lower().strip(" .!?,")
    return t in YES or t.startswith(("yes", "yeah", "go ahead"))


def run(assistant, wake, record: Callable, transcribe: Callable[[object], str], say: Callable[[str], bool],
        tracker: StateTracker, stop: threading.Event, muted: threading.Event, log=print) -> None:
    def confirm(summary: str) -> bool:
        """Spoken confirmation. Silence or anything but a clear yes means NO."""
        tracker.set(State.SPEAKING)
        say(f"Should I run {summary.split('(')[0].replace('_', ' ')}? Say yes or no.")
        tracker.set(State.LISTENING)
        chime()
        audio = record()
        tracker.set(State.PROCESSING)
        return audio is not None and is_yes(transcribe(audio))

    assistant.confirm = confirm
    while not stop.is_set():
        tracker.set(State.MUTED if muted.is_set() else State.IDLE)
        if not wake.wait_for_wake(stop, muted):
            break
        try:
            tracker.set(State.LISTENING)
            chime()
            audio = record()
            if audio is None:
                log("(didn't hear a request)")
                continue
            tracker.set(State.PROCESSING)
            text = transcribe(audio)
            if not text:
                log("(couldn't make out any words)")
                continue
            log(f"you said> {text}")
            reply = assistant.handle(text)
            log(f"jarvis> {reply}")
            for name, args, outcome in assistant.last_tool_calls:
                log(f"  [tool] {name}({args}) -> {'ok' if outcome['ok'] else 'FAILED'}")
            tracker.set(State.SPEAKING)
            if not say(reply):
                log("  (audio playback failed - reply shown as text only)")
        except Exception as exc:  # keep the loop alive; report honestly
            tracker.set(State.ERROR)
            log(f"error: {type(exc).__name__}: {exc}")
