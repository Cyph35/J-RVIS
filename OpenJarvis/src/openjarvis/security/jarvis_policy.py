"""JARVIS safety rules: get the job done without being able to wreck the Mac.

Three tiers, applied before any tool runs:

  1. NEVER   - refused even if the user says yes (a mistaken yes must not be able to cause damage that cannot be undone):
               sudo, rm, disk tools, system settings, killing processes, network downloads/uploads from the shell, scripts that can
               run anything (python, node, sh), anything touching system folders or JARVIS's own install, and writes outside the
               workspace.
  2. EASY    - read-only commands inside the readable folders run without asking.
  3. ASK     - everything else that is allowed (writes in the workspace, moving things to the Trash, typing, clicking) is read back
               and needs a yes.

Deleting never happens: "delete" means "move to the Trash", which can be undone. Overwriting a file keeps a backup copy first.
The folders are in data/jarvis-safety.json; anything not listed there is refused. This module only decides; it changes nothing."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

DEFAULTS: Dict[str, Any] = {
    "read_dirs": ["/Volumes/Acer/JARVIS", "~/Desktop", "~/Documents", "~/Downloads"],
    "write_dirs": ["/Volumes/Acer/JARVIS/workspace"],
    "protected_dirs": ["/Volumes/Acer/JARVIS/data", "/Volumes/Acer/JARVIS/OpenJarvis", "/Volumes/Acer/JARVIS/voice-lab",
                       "/Volumes/Acer/JARVIS/toolchain", "/System", "/usr", "/bin", "/sbin", "/etc", "/private", "/Library",
                       "/Applications", "~/Library", "~/.ssh", "~/.config", "~/.zshrc", "~/.zprofile"],
    "backup_dir": "/Volumes/Acer/JARVIS/data/backups/files",
}
CONFIG_PATH = os.environ.get("JARVIS_SAFETY_FILE", "/Volumes/Acer/JARVIS/data/jarvis-safety.json")
MAX_WRITE_BYTES = 200_000
MAX_COMMAND_CHARS = 400

READ_ONLY = {"ls", "cat", "head", "tail", "wc", "grep", "egrep", "fgrep", "pwd", "echo", "date", "whoami", "uname", "df", "du", "file",
             "stat", "sort", "uniq", "cut", "tr", "diff", "cmp", "basename", "dirname", "realpath", "tree", "which", "printf", "true", "test"}
WRITE_ZONE_ONLY = {"mkdir", "touch", "cp", "mv"}
GIT_READ = {"status", "log", "diff", "show", "branch", "rev-parse", "remote", "ls-files", "blame"}
FIND_FORBIDDEN = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprintf", "-fls"}
NEVER_WORDS = {"sudo", "su", "doas", "rm", "rmdir", "unlink", "shred", "dd", "mkfs", "diskutil", "fdisk", "newfs", "mount", "umount",
               "csrutil", "nvram", "launchctl", "systemsetup", "defaults", "chmod", "chown", "chgrp", "chflags", "xattr", "kill", "killall",
               "pkill", "shutdown", "reboot", "halt", "curl", "wget", "ssh", "scp", "sftp", "rsync", "nc", "ncat", "telnet", "eval", "exec",
               "source", "sh", "bash", "zsh", "python", "python3", "node", "ruby", "perl", "osascript", "open", "tee", "install", "ln",
               "crontab", "at", "networksetup", "scutil", "pmset", "tmutil", "hdiutil", "security", "sed", "awk", "xargs", "env", "nohup"}
OPERATORS = {"|", "&&", "||", ";", "&", ">", ">>", "<", "<<", "2>", "2>>", "&>", ">&"}


@dataclass
class Verdict:
    allow: bool = True
    reason: str = ""                       # why it was refused
    auto: bool = False                     # safe enough to run without asking
    notes: List[str] = field(default_factory=list)   # extra words for the read-back
    params: Optional[Dict[str, Any]] = None          # parameters to use instead of the ones given
    before_run: Optional[Callable[[], None]] = None  # e.g. make a backup, called only after the user said yes


def _cfg() -> Dict[str, Any]:
    c = dict(DEFAULTS)
    try:
        c.update({k: v for k, v in json.load(open(CONFIG_PATH)).items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return c


def _real(p: str | Path, base: Optional[str] = None) -> Path:
    q = Path(os.path.expanduser(str(p)))
    if not q.is_absolute():
        q = Path(base or os.getcwd()) / q
    return Path(os.path.realpath(q))


def _inside(path: Path, roots: List[str]) -> bool:
    for r in roots:
        root = _real(r)
        if path == root or root in path.parents:
            return True
    return False


def in_read_zone(path: Path, c: Dict[str, Any]) -> bool:
    return _inside(path, c["read_dirs"]) and not _inside(path, c["protected_dirs"] if not _inside(path, c["write_dirs"]) else [])


def in_write_zone(path: Path, c: Dict[str, Any]) -> bool:
    return _inside(path, c["write_dirs"]) and not _inside(path, [p for p in c["protected_dirs"] if not _inside(_real(p), c["write_dirs"])])


def _no(reason: str) -> Verdict:
    return Verdict(allow=False, reason=reason)


def _looks_like_path(tok: str) -> bool:
    return "/" in tok or tok.startswith(("~", "."))


def check_shell(params: Dict[str, Any], c: Dict[str, Any]) -> Verdict:
    cmd = str(params.get("command", ""))
    if not cmd.strip():
        return _no("no command given")
    if len(cmd) > MAX_COMMAND_CHARS:
        return _no(f"the command is longer than {MAX_COMMAND_CHARS} characters; split it into smaller steps")
    if any(x in cmd for x in ("`", "$(", "${", "$", "\n", "\r")):
        return _no("commands with variables, backticks, substitutions or several lines are not allowed")
    wd = params.get("working_dir")
    cwd = _real(wd) if wd else _real(c["write_dirs"][0])
    if not (in_read_zone(cwd, c) or in_write_zone(cwd, c)):
        return _no("the working folder is not one JARVIS may use")
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        return _no("I could not read that command safely")
    segments: List[List[str]] = [[]]
    redirects: List[str] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in OPERATORS or set(t) <= set("|&;<>"):
            if t in ("|", "&&", "||", ";"):
                segments.append([])
            elif t in (">", ">>", "2>", "2>>", "&>", ">&"):
                if i + 1 < len(toks):
                    redirects.append(toks[i + 1]); i += 1
            elif t in ("<",):
                i += 1
            else:
                return _no("that kind of shell operator is not allowed")
        else:
            segments[-1].append(t)
        i += 1
    if any(not s for s in segments):
        return _no("that command has an empty step")
    for r in redirects:
        if r == "/dev/null":
            continue
        if not in_write_zone(_real(r, str(cwd)), c):
            return _no("output can only be written inside JARVIS's workspace folder")
    writes_something = bool(redirects) and any(r != "/dev/null" for r in redirects)
    for seg in segments:
        prog = os.path.basename(seg[0])
        args = seg[1:]
        if prog in NEVER_WORDS:
            return _no(f"'{prog}' is never run by JARVIS (it can delete, change the system, run other programs or send data away)")
        if prog == "git":
            sub = next((a for a in args if not a.startswith("-")), "")
            if sub not in GIT_READ:
                return _no("only read-only git commands (status, log, diff, show, branch) are allowed in the terminal")
        elif prog == "find":
            if any(a in FIND_FORBIDDEN for a in args):
                return _no("find cannot delete or run commands")
        elif prog in READ_ONLY:
            pass
        elif prog in WRITE_ZONE_ONLY:
            writes_something = True
        else:
            return _no(f"'{prog}' is not on the list of commands JARVIS may run")
        paths = [a for a in args if not a.startswith("-") and _looks_like_path(a)]
        from openjarvis.security.file_policy import is_sensitive_file

        if any(is_sensitive_file(_real(a.split("*")[0] or ".", str(cwd))) for a in args if not a.startswith("-") and (_looks_like_path(a) or "." in a)):
            return _no("that looks like a secret or credentials file (.env, keys, passwords), which JARVIS never opens")
        if prog in WRITE_ZONE_ONLY:
            plain = [a for a in args if not a.startswith("-")]
            targets = plain[-1:] if prog == "cp" else plain       # cp may read from readable folders; everything else must stay in the workspace
            for a in targets:
                if not in_write_zone(_real(a, str(cwd)), c):
                    return _no(f"'{prog}' may only change things inside JARVIS's workspace folder")
            for a in (plain[:-1] if prog == "cp" else []):
                if not (in_read_zone(_real(a, str(cwd)), c) or in_write_zone(_real(a, str(cwd)), c)):
                    return _no("that source is not in a folder JARVIS may read")
        else:
            for a in paths:
                p = _real(a.split("*")[0].rstrip("/") or ".", str(cwd))
                if not (in_read_zone(p, c) or in_write_zone(p, c)):
                    return _no("that path is not in a folder JARVIS may read")
    out = Verdict(params={**params, "working_dir": str(cwd)})
    out.auto = not writes_something                       # read-only: no need to ask
    if writes_something:
        out.notes.append("this changes files inside the JARVIS workspace folder only")
    return out


def check_file_write(params: Dict[str, Any], c: Dict[str, Any]) -> Verdict:
    path = params.get("path", "")
    if not path:
        return _no("no file path given")
    p = _real(path)
    if not in_write_zone(p, c):
        return _no("files can only be written inside JARVIS's workspace folder")
    if len(str(params.get("content", "")).encode()) > MAX_WRITE_BYTES:
        return _no("that file is too large to write in one go")
    v = Verdict()
    if p.exists():
        if p.is_dir():
            return _no("that path is a folder")
        mode = str(params.get("mode", "write")).lower()
        if mode != "append":
            v.notes.append("this OVERWRITES an existing file; a backup copy is kept first")

        def backup(p: Path = p) -> None:
            d = Path(os.path.expanduser(c["backup_dir"])); d.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, d / f"{time.strftime('%Y%m%d-%H%M%S')}-{p.name}")
        v.before_run = backup
    return v


def check_file_trash(params: Dict[str, Any], c: Dict[str, Any]) -> Verdict:
    path = params.get("path", "")
    if not path:
        return _no("no path given")
    p = _real(path)
    if not p.exists():
        return _no("that file does not exist")
    roots = [_real(r) for r in c["read_dirs"] + c["write_dirs"]]
    if p in roots or not (in_read_zone(p, c) or in_write_zone(p, c)):
        return _no("that item is not one JARVIS may move to the Trash (whole folders like Documents and JARVIS's own files are protected)")
    v = Verdict(); v.notes.append("it goes to the Trash, so it can be put back")
    return v


def check_mac(name: str, params: Dict[str, Any], c: Dict[str, Any]) -> Verdict:
    """Mac tasks: reading, opening and playing music are safe to do at once; changes ask first."""
    a = str(params.get("action", "")).lower()
    if name in ("mac_mail", "mac_notes", "mac_music"):
        return Verdict(auto=True)
    if name == "mac_reminders":
        return Verdict(auto=(a == "find"))
    if name == "mac_calendar":
        return Verdict(notes=["this adds an event to your calendar"])
    if name == "mac_app":
        if a == "quit":
            app = str(params.get("name", "")).strip().lower()
            if app in ("jarvis", "finder", "system settings"):
                return _no("JARVIS never quits that app")
            return Verdict(auto=True)                       # macOS itself asks about unsaved work, so quitting needs no extra question
        target = str(params.get("target", "")).strip()
        if target and not target.lower().startswith(("http://", "https://")) and "." not in target.split("/")[0] or (target and target.startswith(("/", "~", "."))):
            p = _real(target)
            if not (in_read_zone(p, c) or in_write_zone(p, c)):
                return _no("that file or folder is not one JARVIS may open")
        return Verdict(auto=True)
    return Verdict()


def check_tool(name: str, params: Dict[str, Any]) -> Verdict:
    """The one entry point used by the tool executor."""
    c = _cfg()
    if name.startswith("mac_"):
        return check_mac(name, params or {}, c)
    if name == "shell_exec":
        return check_shell(params or {}, c)
    if name == "file_write":
        return check_file_write(params or {}, c)
    if name == "file_trash":
        return check_file_trash(params or {}, c)
    if name == "apply_patch":
        return _no("patches are not allowed; use a file write inside the workspace instead")
    if name == "browser_navigate":
        url = str((params or {}).get("url", "")).strip().lower()
        if url and not url.startswith(("http://", "https://")):
            return _no("only normal web addresses (http or https) can be opened")
    return Verdict()
