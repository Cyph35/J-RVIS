"""JARVIS desktop app: chat window (type or speak, see both sides) + menu bar status icon.

Status dot: green = running/idle, orange = active, black = muted, red = error.
"""
import html
import threading

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox,
                               QPushButton, QSystemTrayIcon, QTextBrowser, QVBoxLayout, QWidget)

import config
from core import hands_free
from core.state import State, StateTracker, status_color

COLORS = {"green": "#34c759", "orange": "#ff9500", "black": "#3a3a3c", "red": "#ff3b30"}
LINE_STYLE = {"you": ("You", "#7aa2f7"), "voice": ("You (voice)", "#7aa2f7"), "jarvis": ("JARVIS", "#ff9e64"),
              "tool": ("", "#8e8e93"), "info": ("", "#8e8e93"), "error": ("Error", "#ff3b30")}


def dot_icon(color: str) -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(COLORS[color]))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(8, 8, 48, 48)
    p.end()
    return QIcon(pm)


class Bridge(QObject):
    """Thread-safe channel from worker threads to the UI thread."""
    line = Signal(str, str)        # kind, text
    status = Signal(str)
    confirm = Signal(str, object)  # summary, holder


class JarvisWindow(QWidget):
    def __init__(self, assistant, speaker=None) -> None:
        super().__init__()
        self.assistant, self.speaker = assistant, speaker
        self.stop, self.muted, self.manual = threading.Event(), threading.Event(), threading.Event()
        self.tracker = StateTracker()
        self.bridge = Bridge()
        self.busy = 0
        self.voice_ready = False
        self.verifier = None
        self.record = None
        self.enrolling = False

        self.setWindowTitle("JARVIS")
        self.resize(560, 680)
        self.setStyleSheet("QWidget{background:#1c1c1e;color:#f2f2f7;font-size:14px}"
                           "QTextBrowser,QLineEdit{background:#2c2c2e;border:1px solid #3a3a3c;border-radius:8px;padding:8px}"
                           "QPushButton{background:#3a3a3c;border:none;border-radius:8px;padding:8px 12px}"
                           "QPushButton:hover{background:#48484a}"
                           "QCheckBox::indicator{width:18px;height:18px;border-radius:4px;border:1px solid #8e8e93;background:#2c2c2e}"
                           "QCheckBox::indicator:checked{background:#ff9500;border-color:#ff9500}")
        self.dot = QLabel("●")
        self.status_label = QLabel("Starting...")
        self.wake_btn = QPushButton("Wake (⌃⌥J)")
        self.mute_btn = QPushButton("Mute (⌃⌥M)")
        self.enroll_btn = QPushButton("Enroll my voice")
        self.forget_btn = QPushButton("Forget my voice")
        top = QHBoxLayout()
        for w in (self.dot, self.status_label):
            top.addWidget(w)
        top.addStretch()
        for b in (self.wake_btn, self.mute_btn):
            top.addWidget(b)
        voice_row = QHBoxLayout()
        self.voice_label = QLabel("")
        voice_row.addWidget(self.voice_label)
        voice_row.addStretch()
        voice_row.addWidget(self.enroll_btn)
        voice_row.addWidget(self.forget_btn)

        self.transcript = QTextBrowser()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a request and press Enter...")
        self.send_btn = QPushButton("Send")
        self.speak_box = QCheckBox("Speak replies aloud")
        self.speak_box.setChecked(speaker is not None)
        self.speak_box.setEnabled(speaker is not None)
        bottom = QHBoxLayout()
        bottom.addWidget(self.input)
        bottom.addWidget(self.send_btn)
        layout = QVBoxLayout(self)
        for item in (top, voice_row):
            layout.addLayout(item)
        layout.addWidget(self.transcript, 1)
        layout.addLayout(bottom)
        layout.addWidget(self.speak_box)

        self.bridge.line.connect(self.add_line)
        self.bridge.status.connect(self.status_label.setText)
        self.bridge.confirm.connect(self._ask_confirm)
        self.input.returnPressed.connect(self.submit)
        self.send_btn.clicked.connect(self.submit)
        self.wake_btn.clicked.connect(self.wake_now)
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.enroll_btn.clicked.connect(self.start_enrollment)
        self.forget_btn.clicked.connect(self.forget_voice)

        self.tray = QSystemTrayIcon(dot_icon("green"), self)
        menu = QMenu()
        for text, fn in (("Show JARVIS", self.show_window), ("Wake now", self.wake_now),
                         ("Mute / unmute microphone", self.toggle_mute), ("Quit JARVIS", self.quit)):
            act = QAction(text, self)
            act.triggered.connect(fn)
            menu.addAction(act)
        self._menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_window()
                                    if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(200)
        self.refresh()
        self.add_line("info", f"Typing works right away. Voice models load in the background "
                              f"(say 'Hey Jarvis' or press {config.HOTKEY_WAKE}).")

    # ------------------------------------------------------------------ transcript / status
    def add_line(self, kind: str, text: str) -> None:
        label, color = LINE_STYLE[kind]
        prefix = f"<b style='color:{color}'>{label}:</b> " if label else ""
        body = html.escape(text).replace("\n", "<br>")
        self.transcript.append(f"<div style='margin:4px 0;color:{color if not label else '#f2f2f7'}'>{prefix}{body}</div>")

    def refresh(self) -> None:
        muted = self.muted.is_set()
        color = status_color(self.tracker.state, muted, self.busy > 0)
        self.dot.setStyleSheet(f"color:{COLORS[color]};font-size:18px")
        self.tray.setIcon(dot_icon(color))
        self.mute_btn.setText("Unmute (⌃⌥M)" if muted else "Mute (⌃⌥M)")
        if self.voice_ready:
            text = "Muted" if muted else (f"Thinking..." if self.busy else f"Voice: {self.tracker.state.value}")
            self.status_label.setText(text)
        enrolled = self.verifier is not None and self.verifier.enrolled()
        self.voice_label.setText("Only your enrolled voice is accepted" if enrolled
                                 else "Voice check off: any voice is accepted")
        self.enroll_btn.setEnabled(self.voice_ready and not self.enrolling)

    # ------------------------------------------------------------------ typed requests
    def submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.add_line("you", text)
        threading.Thread(target=self._run_typed, args=(text,), daemon=True).start()

    def _run_typed(self, text: str) -> None:
        self.busy += 1
        try:
            reply = self.assistant.handle(text, confirm=self._gui_confirm)
            self.show_result(reply, self.assistant.last_tool_calls)
            if self.speaker and self.speak_box.isChecked():
                self.speaker.speak(reply)
        except Exception as exc:
            self.bridge.line.emit("error", f"{type(exc).__name__}: {exc}")
        finally:
            self.busy -= 1

    def show_result(self, reply: str, tool_calls) -> None:
        for name, args, outcome in tool_calls:
            self.bridge.line.emit("tool", f"[tool] {name}({args}) -> {'ok' if outcome['ok'] else 'FAILED'}")
        self.bridge.line.emit("jarvis", reply)

    def _gui_confirm(self, summary: str) -> bool:
        holder = {"event": threading.Event(), "ok": False}
        self.bridge.confirm.emit(summary, holder)
        holder["event"].wait(120)
        return holder["ok"]

    def _ask_confirm(self, summary: str, holder: dict) -> None:
        self.show_window()
        answer = QMessageBox.question(self, "JARVIS needs your approval", f"Allow JARVIS to run:\n\n{summary}")
        holder["ok"] = answer == QMessageBox.StandardButton.Yes
        holder["event"].set()

    # ------------------------------------------------------------------ voice
    def start_voice(self) -> None:
        threading.Thread(target=self._voice_worker, daemon=True).start()

    def _voice_worker(self) -> None:
        try:
            from voice.listener import record_utterance
            from voice.speaker import make_speaker
            from voice.speaker_id import SpeakerVerifier
            from voice.transcriber import Transcriber
            from voice.wake_word import WakeWordDetector

            self.bridge.status.emit("Loading voice models...")
            wake, transcriber = WakeWordDetector(), Transcriber()
            wake.on_mic_change = lambda n: self.bridge.line.emit("info", f"Microphone: {n}")
            self.speaker = self.speaker or make_speaker()
            self.verifier = SpeakerVerifier()
            self.record = lambda: record_utterance(on_status=lambda m: None)
            self.voice_ready = True
            self.bridge.line.emit("info", "Voice ready." + ("" if self.verifier.enrolled()
                                  else " Tip: click 'Enroll my voice' so JARVIS only obeys you."))

            def on_turn(user_text, reply, calls):
                self.bridge.line.emit("voice", user_text)
                self.show_result(reply, calls)

            hands_free.run(self.assistant, wake, self.record, transcriber.transcribe, self.speaker.speak,
                           self.tracker, self.stop, self.muted, log=lambda m: self.bridge.line.emit("info", m),
                           manual=self.manual, verify=self.verifier.verify, on_turn=on_turn)
        except Exception as exc:
            self.tracker.set(State.ERROR)
            self.bridge.line.emit("error", f"Voice stopped: {type(exc).__name__}: {exc}")
            self.bridge.status.emit("Voice error (typing still works)")

    def wake_now(self, *_) -> None:
        if self.voice_ready and not self.muted.is_set():
            self.manual.set()

    def toggle_mute(self, *_) -> None:
        self.muted.clear() if self.muted.is_set() else self.muted.set()

    def start_enrollment(self) -> None:
        if not self.voice_ready or self.enrolling:
            return
        self.enrolling = True
        self.enroll_btn.setEnabled(False)
        threading.Thread(target=self._enroll_worker, daemon=True).start()

    def _enroll_worker(self) -> None:
        import time

        from voice.enroll import run_enrollment

        was_muted = self.muted.is_set()
        self.muted.set()  # closes the wake-word microphone stream while we record
        time.sleep(0.6)
        try:
            from voice.listener import describe_last

            msg = run_enrollment(self.verifier, self.record, lambda t: self.bridge.line.emit("info", t),
                                 hands_free.chime, describe_last)
        except Exception as exc:
            msg = f"Enrollment error: {type(exc).__name__}: {exc}"
        finally:
            self.enrolling = False
            if not was_muted:
                self.muted.clear()
        self.bridge.line.emit("info", msg)

    def forget_voice(self) -> None:
        if self.verifier is not None:
            self.verifier.clear()
            self.add_line("info", "Voiceprint deleted. Any voice is accepted again.")

    # ------------------------------------------------------------------ window / app
    def show_window(self, *_) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:  # closing the window keeps JARVIS running in the menu bar
        event.ignore()
        self.hide()

    def quit(self, *_) -> None:
        self.stop.set()
        if self.speaker:
            self.speaker.stop()
        self.tray.hide()
        QApplication.quit()


def start_hotkeys(window: JarvisWindow) -> None:
    try:
        from pynput import keyboard

        listener = keyboard.GlobalHotKeys({config.HOTKEY_WAKE: window.wake_now, config.HOTKEY_MUTE: window.toggle_mute})
        listener.daemon = True
        listener.start()
    except Exception as exc:
        window.add_line("info", f"Global hotkeys unavailable ({type(exc).__name__}); use the buttons instead.")


def run(assistant, speaker=None, with_voice: bool = True) -> None:
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    window = JarvisWindow(assistant, speaker)
    window.show()
    if with_voice:
        window.start_voice()
        start_hotkeys(window)
    app.exec()
