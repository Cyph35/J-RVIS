import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from interface.dashboard import JarvisWindow


class FakeAssistant:
    last_tool_calls = [("get_current_time", {}, {"ok": True, "result": "noon"})]

    def handle(self, text, confirm=None):
        return f"echo: {text}"


class FakeSpeaker:
    def __init__(self):
        self.said = []

    def speak(self, t):
        self.said.append(t)
        return True

    def stop(self):
        pass


def pump(app, seconds=1.0):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def test_typed_request_shows_both_sides_and_speaks():
    app = QApplication.instance() or QApplication([])
    spk = FakeSpeaker()
    w = JarvisWindow(FakeAssistant(), spk)
    w.input.setText("what time is it")
    w.submit()
    pump(app)
    text = w.transcript.toPlainText()
    assert "You: what time is it" in text and "JARVIS: echo: what time is it" in text
    assert "get_current_time" in text
    assert spk.said == ["echo: what time is it"]
    w.tray.hide()


def test_mute_changes_status_color():
    app = QApplication.instance() or QApplication([])
    w = JarvisWindow(FakeAssistant())
    w.voice_ready = True
    w.toggle_mute()
    w.refresh()
    assert "Muted" in w.status_label.text() and "Unmute" in w.mute_btn.text()
    w.tray.hide()
