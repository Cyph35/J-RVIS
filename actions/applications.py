import subprocess

# Allowlist: lowercase name -> real macOS app name.
APPROVED_APPS = {
    "calculator": "Calculator",
    "safari": "Safari",
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "spotify": "Spotify",
    "notes": "Notes",
    "finder": "Finder",
    "terminal": "Terminal",
    "vs code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
}


def open_application(name: str) -> str:
    app = APPROVED_APPS.get(name.strip().lower())
    if app is None:
        raise ValueError(
            f"{name!r} is not an approved app. Approved: {sorted(set(APPROVED_APPS.values()))}"
        )
    result = subprocess.run(["open", "-a", app], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Could not open {app}: {result.stderr.strip()}")
    return f"Opened {app}"


def close_application(name: str) -> str:
    app = APPROVED_APPS.get(name.strip().lower())
    if app is None:
        raise ValueError(f"{name!r} is not an approved app.")
    result = subprocess.run(
        ["osascript", "-e", f'tell application "{app}" to quit'],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Could not close {app}: {result.stderr.strip()}")
    return f"Closed {app}"
