"""Mac tasks for the agent: open or quit apps, open web addresses and files, read Mail, search Notes, control Music, and create or complete
Calendar events and Reminders. Thin adapter over voice-lab/integrations.py (the same code the voice server's quick commands use), so there is
one implementation. Reads and opening run at once; changes (calendar, reminders, quit) always ask the user first (see ALWAYS_CONFIRM and
security/jarvis_policy.py). When macOS blocks something, the tool asks the user to open the right Settings page and retries once."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from openjarvis.core.registry import ToolRegistry
from openjarvis.core.types import ToolResult
from openjarvis.tools._stubs import BaseTool, ToolSpec

_VOICE_LAB = "/Volumes/Acer/JARVIS/voice-lab"
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _mods():
    if _VOICE_LAB not in sys.path:
        sys.path.insert(0, _VOICE_LAB)
    import integrations
    import perms
    return integrations, perms


def _confirm(prompt: str) -> bool:
    from openjarvis.server.approvals import broker
    return broker.confirm(prompt)


def _call(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    I, P = _mods()
    r = I.run(name, args)
    need = r.get("needs")
    if need and not r.get("ok"):                    # a missing macOS permission: ask, open the page, wait for "done", retry once
        if _confirm(f"PERMISSION:{need['pane']}|{need['label']}"):
            P.open_pane(need["pane"])
            if _confirm(f"PERMISSION_WAIT:{need['pane']}|{need['label']}"):
                r = I.run(name, args)
    return r


def parse_when(date: str, time_: str = "", now: Optional[datetime] = None) -> Optional[str]:
    """'tomorrow' / 'friday' / '2026-11-27' and '3pm' / '15:30' -> 'YYYY-MM-DD HH:MM' (local). None if the date cannot be read."""
    now = now or datetime.now()
    d = (date or "").strip().lower()
    day = None
    if d in ("", "today", "tonight"): day = now.date()
    elif d == "tomorrow": day = (now + timedelta(days=1)).date()
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        try: day = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError: return None
    else:
        w = re.sub(r"^(?:next|this|on)\s+", "", d)
        if w in DAYS:
            add = (DAYS.index(w) - now.weekday()) % 7 or 7
            day = (now + timedelta(days=add)).date()
    if day is None: return None
    t = (time_ or "").strip().lower().replace(".", "").replace(" ", "")
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)?", t)
    if not t: return day.strftime("%Y-%m-%d") + " 00:00"
    if not m: return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap == "pm" and h < 12: h += 12
    if ap == "am" and h == 12: h = 0
    if h > 23 or mi > 59: return None
    return f"{day.strftime('%Y-%m-%d')} {h:02d}:{mi:02d}"


def _done(tool: str, r: Dict[str, Any], extra: str = "") -> ToolResult:
    msg = str(r.get("message", "")) + extra
    return ToolResult(tool_name=tool, content=msg or ("Done." if r.get("ok") else "That did not work."), success=bool(r.get("ok")))


def _spec(name: str, desc: str, props: Dict[str, Any], required: list) -> ToolSpec:
    return ToolSpec(name=name, description=desc, parameters={"type": "object", "properties": props, "required": required}, category="computer", timeout_seconds=90.0)


@ToolRegistry.register("mac_app")
class MacAppTool(BaseTool):
    tool_id = "mac_app"

    @property
    def spec(self) -> ToolSpec:
        return _spec("mac_app", "Open or quit a Mac app by name (Chrome, Safari, Spotify, Mail, Notes...) and SHOW a web address or a file to the user. Use it whenever the user says open, launch or start something, even if they also ask something else; the browser_* tools only read pages invisibly.",
                     {"action": {"type": "string", "enum": ["open", "quit"]}, "name": {"type": "string", "description": "App name. For a web address, leave empty unless the user named a browser"}, "target": {"type": "string", "description": "Web address or file path to open"}}, ["action"])

    def execute(self, **p: Any) -> ToolResult:
        a = str(p.get("action", "open")).lower()
        if a == "quit": return _done("mac_app", _call("quit_app", {"name": str(p.get("name", ""))}))
        if p.get("target"): return _done("mac_app", _call("open_target", {"target": str(p["target"]), "browser": str(p.get("name", ""))}))
        return _done("mac_app", _call("open_app", {"name": str(p.get("name", ""))}))


@ToolRegistry.register("mac_mail")
class MacMailTool(BaseTool):
    tool_id = "mac_mail"

    @property
    def spec(self) -> ToolSpec:
        return _spec("mac_mail", "Read the user's Apple Mail (read-only): list unread messages, search by sender or subject, or read one message by id.",
                     {"action": {"type": "string", "enum": ["unread", "search", "read"]}, "query": {"type": "string"}, "id": {"type": "string", "description": "Message id from unread or search"}}, ["action"])

    def execute(self, **p: Any) -> ToolResult:
        a = str(p.get("action", "unread")).lower()
        if a == "read":
            r = _call("mail_read", {"id": str(p.get("id", ""))})
            return ToolResult(tool_name="mac_mail", content=(f"Subject: {r.get('subject', '')}\n{r.get('body', '')}" if r.get("ok") else str(r.get("message", ""))), success=bool(r.get("ok")))
        r = _call("mail_search", {"query": str(p.get("query", ""))}) if a == "search" else _call("mail_unread", {})
        ids = "; ".join(f"id {m['id']}: {m['sender']} - {m['subject']}" for m in r.get("messages", []))
        return _done("mac_mail", r, f"\nMessages: {ids}" if ids else "")


@ToolRegistry.register("mac_calendar")
class MacCalendarTool(BaseTool):
    tool_id = "mac_calendar"

    @property
    def spec(self) -> ToolSpec:
        return _spec("mac_calendar", "Create an event in the user's Apple Calendar. date: today, tomorrow, a weekday name or YYYY-MM-DD. time: like 3pm or 15:30.",
                     {"title": {"type": "string"}, "date": {"type": "string"}, "time": {"type": "string"}, "minutes": {"type": "integer", "description": "Length, default 60"}}, ["title", "date", "time"])

    def execute(self, **p: Any) -> ToolResult:
        start = parse_when(str(p.get("date", "")), str(p.get("time", "")))
        if not start or not str(p.get("time", "")).strip():
            return ToolResult(tool_name="mac_calendar", content="I need a clear date and time, for example tomorrow at 3pm.", success=False)
        return _done("mac_calendar", _call("event_create", {"title": str(p.get("title", "")), "start": start, "minutes": int(p.get("minutes") or 60)}))


@ToolRegistry.register("mac_reminders")
class MacRemindersTool(BaseTool):
    tool_id = "mac_reminders"

    @property
    def spec(self) -> ToolSpec:
        return _spec("mac_reminders", "Apple Reminders: find open reminders, create one (optional date and time), or mark one complete by its exact name.",
                     {"action": {"type": "string", "enum": ["find", "create", "complete"]}, "title": {"type": "string"}, "date": {"type": "string"}, "time": {"type": "string"}}, ["action", "title"])

    def execute(self, **p: Any) -> ToolResult:
        a, title = str(p.get("action", "find")).lower(), str(p.get("title", ""))
        if a == "find":
            r = _call("reminder_find", {"name": title}); m = r.get("matches", [])
            return ToolResult(tool_name="mac_reminders", content="Open reminders: " + "; ".join(m) if m else "No open reminders match.", success=bool(r.get("ok")))
        if a == "complete": return _done("mac_reminders", _call("reminder_complete", {"name": title}))
        due = parse_when(str(p.get("date", "")), str(p.get("time", ""))) if p.get("date") else ""
        if p.get("date") and not due: return ToolResult(tool_name="mac_reminders", content="I could not read that date.", success=False)
        return _done("mac_reminders", _call("reminder_create", {"title": title, "due": due or ""}))


@ToolRegistry.register("mac_notes")
class MacNotesTool(BaseTool):
    tool_id = "mac_notes"

    @property
    def spec(self) -> ToolSpec:
        return _spec("mac_notes", "Apple Notes (read-only): search notes by words, or read one note by its title.",
                     {"action": {"type": "string", "enum": ["search", "read"]}, "query": {"type": "string"}, "title": {"type": "string"}}, ["action"])

    def execute(self, **p: Any) -> ToolResult:
        if str(p.get("action", "search")).lower() == "read": return _done("mac_notes", _call("notes_read", {"title": str(p.get("title", ""))}))
        return _done("mac_notes", _call("notes_search", {"query": str(p.get("query", ""))}))


@ToolRegistry.register("mac_music")
class MacMusicTool(BaseTool):
    tool_id = "mac_music"

    @property
    def spec(self) -> ToolSpec:
        return _spec("mac_music", "Control Apple Music or Spotify (open the app first with mac_app if it is not running): play, pause, next, previous, volume 0-100, find a song by name (Apple Music library), or say what is playing.",
                     {"action": {"type": "string", "enum": ["play", "pause", "next", "previous", "volume", "find", "now"]}, "value": {"type": "string", "description": "Volume number or song name"}}, ["action"])

    def execute(self, **p: Any) -> ToolResult:
        return _done("mac_music", _call("music", {"action": str(p.get("action", "now")), "value": str(p.get("value", ""))}))
