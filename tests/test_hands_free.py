import threading

from core import hands_free
from core.state import State, StateTracker


class FakeWake:
    def __init__(self, n):
        self.n = n

    def wait_for_wake(self, stop, muted):
        if self.n == 0:
            return False
        self.n -= 1
        return True


class FakeAssistant:
    confirm = None
    last_tool_calls = []

    def handle(self, text):
        return f"ok: {text}"


def run_loop(audio, transcript, wake_count=1):
    said, logs = [], []
    tr = StateTracker()
    hands_free.chime = lambda: None
    hands_free.run(FakeAssistant(), FakeWake(wake_count), lambda: audio, lambda a: transcript,
                   lambda t: said.append(t) or True, tr, threading.Event(), threading.Event(), logs.append)
    return said, logs, tr


def test_full_cycle_states_and_reply():
    said, _, tr = run_loop(audio=[1], transcript="what time is it")
    assert said == ["ok: what time is it"]
    assert tr.history[:5] == [State.IDLE, State.LISTENING, State.PROCESSING, State.SPEAKING, State.IDLE]


def test_no_speech_skips_assistant():
    said, logs, _ = run_loop(audio=None, transcript="")
    assert said == [] and any("didn't hear" in l for l in logs)


def test_error_does_not_kill_loop():
    def boom(_):
        raise RuntimeError("stt broke")
    logs = []
    hands_free.chime = lambda: None
    tr = StateTracker()
    hands_free.run(FakeAssistant(), FakeWake(2), lambda: [1], boom, lambda t: True, tr,
                   threading.Event(), threading.Event(), logs.append)
    assert sum("stt broke" in l for l in logs) == 2 and State.ERROR in tr.history


def test_spoken_confirmation_defaults_to_no():
    assert hands_free.is_yes("Yes.") and hands_free.is_yes("go ahead please")
    assert not hands_free.is_yes("") and not hands_free.is_yes("no") and not hands_free.is_yes("maybe")
