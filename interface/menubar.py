"""Menu bar app: a status icon that shows what JARVIS is doing, plus global hotkeys.

Icon: green = running and idle, orange = active (listening / thinking / speaking),
black = muted (microphone closed), red = error.
"""
import threading

import rumps

import config
from core import hands_free
from core.state import State, StateTracker

ICONS = {State.IDLE: "🟢", State.LISTENING: "🟠", State.PROCESSING: "🟠",
         State.SPEAKING: "🟠", State.MUTED: "⚫", State.ERROR: "🔴"}
LOADING_ICON = "⏳"


def icon_for(state: State, muted: bool) -> str:
    return ICONS[State.MUTED] if muted else ICONS[state]


class JarvisMenuBar(rumps.App):
    def __init__(self, assistant) -> None:
        super().__init__("JARVIS", title=LOADING_ICON, quit_button=None)
        self.assistant = assistant
        self.stop, self.muted, self.manual = threading.Event(), threading.Event(), threading.Event()
        self.tracker = StateTracker()
        self.loaded = False
        self.status_item = rumps.MenuItem("Loading models...")
        self.mute_item = rumps.MenuItem(f"Mute microphone", callback=self.toggle_mute)
        self.menu = [self.status_item,
                     rumps.MenuItem("Wake now", callback=self.wake_now),
                     self.mute_item, None,
                     rumps.MenuItem("Quit JARVIS", callback=self.quit)]
        self._timer = rumps.Timer(self._refresh, 0.2)  # UI updates happen on the main thread
        self._timer.start()
        threading.Thread(target=self._worker, daemon=True).start()
        self._start_hotkeys()

    # --- worker: the hands-free loop runs off the UI thread
    def _worker(self) -> None:
        try:
            from voice.listener import record_utterance
            from voice.speaker import Speaker
            from voice.transcriber import Transcriber
            from voice.wake_word import WakeWordDetector

            wake, transcriber, speaker = WakeWordDetector(), Transcriber(), Speaker()
            self.loaded = True
            hands_free.run(self.assistant, wake, lambda: record_utterance(on_status=lambda m: None),
                           transcriber.transcribe, speaker.speak, self.tracker, self.stop, self.muted,
                           manual=self.manual)
        except Exception as exc:
            self.tracker.set(State.ERROR)
            self.status_item.title = f"Error: {type(exc).__name__}"

    # --- controls
    def wake_now(self, _=None) -> None:
        if self.loaded and not self.muted.is_set():
            self.manual.set()

    def toggle_mute(self, _=None) -> None:
        self.muted.clear() if self.muted.is_set() else self.muted.set()

    def quit(self, _=None) -> None:
        self.stop.set()
        rumps.quit_application()

    def _start_hotkeys(self) -> None:
        try:
            from pynput import keyboard

            self._hotkeys = keyboard.GlobalHotKeys({config.HOTKEY_WAKE: self.wake_now,
                                                    config.HOTKEY_MUTE: self.toggle_mute})
            self._hotkeys.daemon = True
            self._hotkeys.start()
        except Exception as exc:
            print(f"Global hotkeys unavailable ({type(exc).__name__}); use the menu instead.")

    def _refresh(self, _) -> None:
        if not self.loaded and self.tracker.state != State.ERROR:
            return
        muted = self.muted.is_set()
        state = self.tracker.state
        self.title = icon_for(state, muted)
        self.status_item.title = "Muted" if muted else f"Status: {state.value}"
        self.mute_item.title = "Unmute microphone" if muted else "Mute microphone"
