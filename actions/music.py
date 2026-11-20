"""Music control through AppleScript. Controls the app only if it is already running."""
import subprocess

import config

ACTIONS = ["play", "pause", "next", "previous", "now_playing"]
_SCRIPTS = {"play": "play", "pause": "pause", "next": "next track", "previous": "previous track"}


def music_control(action: str) -> str:
    app = config.MUSIC_APP
    if action not in ACTIONS:
        raise ValueError(f"Unknown music action {action!r}. Use one of {ACTIONS}.")
    if subprocess.run(["pgrep", "-x", app], capture_output=True).returncode != 0:
        raise RuntimeError(f"{app} is not running. Open it first.")
    if action == "now_playing":
        script = f'tell application "{app}" to (name of current track) & " by " & (artist of current track)'
    else:
        script = f'tell application "{app}" to {_SCRIPTS[action]}'
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"{app} did not respond: {result.stderr.strip()}")
    return result.stdout.strip() or f"{action} sent to {app}"
