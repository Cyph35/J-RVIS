"""Screen understanding: capture a screenshot and ask the LOCAL vision model about it."""
import subprocess
import tempfile
from pathlib import Path


def analyze_screen(question: str, brain) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        shot = Path(tmp) / "screen.jpg"
        cap = subprocess.run(["screencapture", "-x", "-t", "jpg", str(shot)], capture_output=True, text=True)
        if cap.returncode != 0 or not shot.exists():
            raise RuntimeError("Screenshot failed. Allow Screen Recording for this app in System Settings > Privacy & Security.")
        subprocess.run(["sips", "-Z", "1280", str(shot)], capture_output=True)  # smaller = faster
        msg = brain.chat([{"role": "user", "content": question or "Describe what is on this screen.",
                           "images": [str(shot)]}])
    return (msg.content or "").strip() or "The vision model returned no description."
