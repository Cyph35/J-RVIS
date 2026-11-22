"""Look at and use any Mac app through the macOS Accessibility interface (text only, so a text model can use it).

screen_read lists what is on screen in the front app. screen_click, screen_type and screen_key act on it and ALWAYS ask the user first
(see ALWAYS_CONFIRM in tools/_stubs.py). When macOS has not given JARVIS the needed permission, the tool asks the user through the
approval channel to open the right Settings page, waits for them to switch it on, then tries again. Nothing here changes a setting."""

from __future__ import annotations

import re
import subprocess
from typing import Any, Callable, Optional, Tuple

from openjarvis.core.registry import ToolRegistry
from openjarvis.core.types import ToolResult
from openjarvis.tools._stubs import BaseTool, ToolSpec

PANES = {"accessibility": "Privacy_Accessibility", "automation": "Privacy_Automation", "screen": "Privacy_ScreenCapture"}
CLICKABLE = {"button", "checkbox", "radio button", "pop up button", "menu button", "menu item", "link", "tab", "toolbar button", "text field", "search field", "text area", "combo box", "disclosure triangle"}
KEYS = {"return": 36, "enter": 36, "tab": 48, "space": 49, "escape": 53, "esc": 53, "delete": 51, "backspace": 51, "left": 123, "right": 124, "down": 125, "up": 126}
MODS = {"cmd": "command down", "command": "command down", "shift": "shift down", "option": "option down", "alt": "option down", "ctrl": "control down", "control": "control down"}


def q(s: str) -> str:
    """Escape for an AppleScript string literal."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def classify(err: str) -> Optional[Tuple[str, str]]:
    e = err or ""
    if "not allowed assistive access" in e.lower() or "-25211" in e or "-1719" in e and "assistive" in e.lower():
        return "accessibility", "control other apps"
    if "-1743" in e or "Not authorized to send Apple events" in e:
        return "automation", "control System Events"
    return None


def key_script(key: str) -> str:
    """'cmd+n', 'return', 'shift+tab' -> the System Events line. Anything unknown raises ValueError."""
    parts = [p.strip().lower() for p in key.split("+") if p.strip()]
    if not parts: raise ValueError("no key")
    mods = [MODS[p] for p in parts[:-1] if p in MODS]
    if len(mods) != len(parts) - 1: raise ValueError("unknown modifier")
    k = parts[-1]
    using = f" using {{{', '.join(mods)}}}" if mods else ""
    if k in KEYS: return f'tell application "System Events" to key code {KEYS[k]}{using}'
    if re.fullmatch(r"[a-z0-9]", k): return f'tell application "System Events" to keystroke {q(k)}{using}'
    raise ValueError("unknown key")


def _confirm(prompt: str) -> bool:
    from openjarvis.server.approvals import broker
    return broker.confirm(prompt)


def _open_pane(pane: str) -> None:
    subprocess.run(["open", f"x-apple.systempreferences:com.apple.preference.security?{PANES[pane]}"], capture_output=True, timeout=15)


def _osa(script: str, timeout: int = 30, ask: Callable[[str], bool] = _confirm) -> Tuple[bool, str]:
    """Run AppleScript. On a missing permission: ask, open the right pane, wait for 'done', retry once."""
    for attempt in range(2):
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0:
            return True, r.stdout.strip()
        need = classify(r.stderr)
        if not need or attempt == 1:
            return False, (r.stderr.strip() or "failed")[:300]
        pane, label = need
        if not ask(f"PERMISSION:{pane}|{label}"):
            return False, f"JARVIS does not have permission to {label}, and you chose not to open the settings page."
        _open_pane(pane)
        if not ask(f"PERMISSION_WAIT:{pane}|{label}"):
            return False, f"Permission to {label} was not switched on."
    return False, "failed"


BLOCKED_APPS = {"terminal", "iterm2", "iterm", "script editor", "automator", "keychain access", "disk utility", "system settings", "system preferences", "activity monitor", "console"}
BLOCKED_KEYS = {"cmd+delete", "cmd+backspace", "cmd+shift+delete", "cmd+option+delete", "cmd+alt+delete", "cmd+q", "cmd+option+esc", "cmd+alt+esc", "ctrl+cmd+q", "cmd+shift+q", "cmd+option+q", "cmd+alt+q"}


def front_app() -> Tuple[bool, str]:
    return _osa('tell application "System Events" to get name of first process whose frontmost is true')


def app_blocked(name: str) -> bool:
    return name.strip().lower() in BLOCKED_APPS


def key_blocked(key: str) -> bool:
    k = "+".join(sorted(p.strip().lower() for p in key.split("+"))) 
    return any("+".join(sorted(b.split("+"))) == k for b in BLOCKED_KEYS)


def _guard_front(app: str) -> Optional[str]:
    """Typing or clicking in a terminal, Settings, Keychain or Disk Utility could do anything, so those apps are off limits."""
    name = app or (front_app()[1] if app == "" else app)
    if app_blocked(name):
        return f"JARVIS may not click or type in {name}."
    return None


def _secure_field_focused(app: str) -> bool:
    ok, out = _osa(f'tell application "System Events" to tell ({_front_process(app)}) to get subrole of (value of attribute "AXFocusedUIElement")')
    return ok and "secure" in out.lower()


def _front_process(app: str) -> str:
    return f"first process whose name is {q(app)}" if app else "first process whose frontmost is true"


@ToolRegistry.register("screen_read")
class ScreenReadTool(BaseTool):
    tool_id = "screen_read"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="screen_read",
            description="List what is on screen in the front app (or a named app): its window title and its buttons, fields and menus by name.",
            parameters={"type": "object", "properties": {"app": {"type": "string", "description": "Optional app name; default is the front app."}}},
            category="computer", timeout_seconds=60.0,
        )

    def execute(self, **params: Any) -> ToolResult:
        app = str(params.get("app", "")).strip()[:60]
        script = f'''tell application "System Events"
set p to {_front_process(app)}
set out to "App: " & (name of p) & linefeed
try
set out to out & "Window: " & (name of window 1 of p) & linefeed
set n to 0
repeat with e in (entire contents of window 1 of p)
try
set r to role description of e
set nm to ""
try
set nm to name of e
end try
if nm is "" or nm is missing value then
try
set nm to description of e
end try
end if
if nm is not missing value and nm is not "" then
set out to out & r & ": " & nm & linefeed
set n to n + 1
end if
end try
if n >= 80 then exit repeat
end repeat
end try
return out
end tell'''
        ok, out = _osa(script, 60)
        return ToolResult(tool_name="screen_read", content=out if ok else f"Could not read the screen: {out}", success=ok)


@ToolRegistry.register("screen_click")
class ScreenClickTool(BaseTool):
    tool_id = "screen_click"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="screen_click",
            description="Click a button, checkbox, link or menu item by its exact name (as listed by screen_read). Asks the user first.",
            parameters={"type": "object", "properties": {"name": {"type": "string"}, "app": {"type": "string", "description": "Optional app name."}}, "required": ["name"]},
            category="computer", requires_confirmation=True, timeout_seconds=60.0,
        )

    def execute(self, **params: Any) -> ToolResult:
        name, app = str(params.get("name", "")).strip()[:120], str(params.get("app", "")).strip()[:60]
        if not name: return ToolResult(tool_name="screen_click", content="No name given.", success=False)
        blocked = _guard_front(app)
        if blocked: return ToolResult(tool_name="screen_click", content=blocked, success=False)
        clickable = ", ".join(q(c) for c in sorted(CLICKABLE))
        script = f'''tell application "System Events"
set p to {_front_process(app)}
repeat with e in (entire contents of window 1 of p)
try
set nm to ""
try
set nm to name of e
end try
if nm is "" or nm is missing value then
try
set nm to description of e
end try
end if
if nm is {q(name)} and (role description of e) is in {{{clickable}}} then
click e
return "clicked"
end if
end try
end repeat
return "not found"
end tell'''
        ok, out = _osa(script, 60)
        done = ok and out == "clicked"
        return ToolResult(tool_name="screen_click", content=f"Clicked {name}." if done else (f"I could not find a clickable item named {name}." if ok else f"Could not click: {out}"), success=done)


@ToolRegistry.register("screen_type")
class ScreenTypeTool(BaseTool):
    tool_id = "screen_type"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="screen_type",
            description="Type text into the front app, where the cursor is. Asks the user first.",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
            category="computer", requires_confirmation=True,
        )

    def execute(self, **params: Any) -> ToolResult:
        text = str(params.get("text", ""))[:500]
        if not text: return ToolResult(tool_name="screen_type", content="No text given.", success=False)
        blocked = _guard_front("")
        if blocked: return ToolResult(tool_name="screen_type", content=blocked, success=False)
        if _secure_field_focused(""): return ToolResult(tool_name="screen_type", content="That is a password field; JARVIS never types into those.", success=False)
        ok, out = _osa(f'tell application "System Events" to keystroke {q(text)}')
        return ToolResult(tool_name="screen_type", content="Typed it." if ok else f"Could not type: {out}", success=ok)


@ToolRegistry.register("screen_key")
class ScreenKeyTool(BaseTool):
    tool_id = "screen_key"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="screen_key",
            description="Press a key or shortcut in the front app, e.g. 'return', 'tab', 'cmd+n', 'cmd+shift+t'. Asks the user first.",
            parameters={"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
            category="computer", requires_confirmation=True,
        )

    def execute(self, **params: Any) -> ToolResult:
        keyname = str(params.get("key", ""))
        if key_blocked(keyname): return ToolResult(tool_name="screen_key", content="That shortcut can delete or quit things, so JARVIS does not press it.", success=False)
        blocked = _guard_front("")
        if blocked: return ToolResult(tool_name="screen_key", content=blocked, success=False)
        try:
            script = key_script(keyname)
        except ValueError as e:
            return ToolResult(tool_name="screen_key", content=f"I can't press that: {e}.", success=False)
        ok, out = _osa(script)
        return ToolResult(tool_name="screen_key", content="Pressed it." if ok else f"Could not press it: {out}", success=ok)


@ToolRegistry.register("file_trash")
class FileTrashTool(BaseTool):
    tool_id = "file_trash"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="file_trash",
            description="Move a file or folder to the Trash (it can be put back). This is the only way JARVIS deletes anything. Asks the user first.",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            category="computer", requires_confirmation=True, timeout_seconds=60.0,
        )

    def execute(self, **params: Any) -> ToolResult:
        import os
        path = os.path.realpath(os.path.expanduser(str(params.get("path", ""))))
        ok, out = _osa(f'tell application "Finder" to delete (POSIX file {q(path)} as alias)')
        return ToolResult(tool_name="file_trash", content="Moved it to the Trash." if ok else f"Could not move it to the Trash: {out}", success=ok)
