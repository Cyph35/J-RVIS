"""Assistant states, so every interface can show what JARVIS is doing."""
from enum import Enum
from typing import Callable


class State(str, Enum):
    IDLE = "idle"              # waiting for the wake word (only the wake model hears audio)
    LISTENING = "listening"    # recording your request
    PROCESSING = "processing"  # transcribing / thinking / running a tool
    SPEAKING = "speaking"
    MUTED = "muted"            # microphone closed
    ERROR = "error"


class StateTracker:
    def __init__(self, on_change: Callable[[State], None] | None = None) -> None:
        self.state = State.IDLE
        self.history: list[State] = [State.IDLE]
        self._on_change = on_change

    def set(self, state: State) -> None:
        if state != self.state:
            self.state = state
            self.history.append(state)
            if self._on_change:
                self._on_change(state)


def status_color(state: State, muted: bool, busy: bool = False) -> str:
    """green = running/idle, orange = active, black = muted, red = error."""
    if muted:
        return "black"
    if state == State.ERROR:
        return "red"
    if busy or state in (State.LISTENING, State.PROCESSING, State.SPEAKING):
        return "orange"
    return "green"
