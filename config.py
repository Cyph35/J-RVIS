"""Central configuration. Secrets/settings come from .env (never committed)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b-mlx")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MAX_TOOL_ROUNDS = 3

SYSTEM_PROMPT = (
    "You are JARVIS, a concise personal assistant running on the user's Mac. "
    "When the user asks for an action, call exactly the matching tool. "
    "Never invent tools. After a tool result, report it honestly in one or two "
    "short sentences; if the tool reports an error, say so and do not claim success."
)

# Speech-to-text (local). base.en is fast on an M2; try "small.en" for better accuracy.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base.en")
