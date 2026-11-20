"""Central configuration. Secrets/settings come from .env (never committed)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b-mlx")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = (
    "You are JARVIS, a concise personal assistant running on the user's Mac. "
    "For greetings and small talk, just reply in words and call NO tool. "
    "Only when the user asks for something a tool does, call exactly the matching tool. "
    "Never invent tools. After a tool result, report it honestly in one or two "
    "short sentences; if the tool reports an error, say so and do not claim success."
)

# Speech-to-text (local). base.en is fast on an M2; try "small.en" for better accuracy.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small.en")

# Text-to-speech (macOS `say`). Daniel (UK) suits JARVIS; list voices with: say -v '?'
SPEAK_VOICE = os.getenv("SPEAK_VOICE", "Daniel")
SPEAK_RATE = int(os.getenv("SPEAK_RATE", "190"))  # words per minute

# Wake word (openWakeWord, fully local). Raise threshold if it triggers by accident.
WAKE_WORD_MODEL = "hey_jarvis"
WAKE_THRESHOLD = float(os.getenv("WAKE_THRESHOLD", "0.5"))

# Memory / music
DB_PATH = ROOT / "data" / "jarvis.db"
MUSIC_APP = os.getenv("MUSIC_APP", "Spotify")  # or "Music"
HISTORY_MESSAGES = 6
MAX_TOOL_CALLS_PER_REQUEST = 6

# Menu bar app + global hotkeys (pynput syntax). Needs Input Monitoring permission.
HOTKEY_WAKE = os.getenv("HOTKEY_WAKE", "<ctrl>+<alt>+j")
HOTKEY_MUTE = os.getenv("HOTKEY_MUTE", "<ctrl>+<alt>+m")

# Speaker verification ("only respond to my voice"). Voiceprint stays on this Mac in data/.
SPEAKER_MODEL = ROOT / "data" / "models" / "campplus.onnx"
VOICEPRINT_PATH = ROOT / "data" / "voiceprint.npy"
SPEAKER_THRESHOLD = float(os.getenv("SPEAKER_THRESHOLD", "0.5"))  # higher = stricter

# Microphone: "" (default) = automatically use whatever input macOS currently has selected, and follow
# changes (plug in a headset and it switches). Or set part of a device name to pin one, e.g. "MacBook".
MIC_DEVICE = os.getenv("MIC_DEVICE", "")
