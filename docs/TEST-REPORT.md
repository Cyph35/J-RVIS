# JARVIS: test report (Phase 4 and the roadmap that followed)

Date: 2026-11-22. Mac: M2, 16 GB. Everything runs locally. Nothing is committed (the folder is not a git repository). Backups are in `data/backups/`.

Legend: **Verified** = I ran it for real and saw the result. **Unit-tested** = automated tests only. **You confirmed** = you tested it in the app and said it works. **Not verified** = I could not test it, with the reason.

## Automated results (final run)

| Suite | Result |
|---|---|
| Frontend typecheck (`tsc -b`) | clean |
| Frontend tests (`npx vitest run`) | 306 passed, 49 files |
| Rust tests (`cargo test launcher`) | 4 passed |
| Voice-lab tests (memory, stretch, briefing, integrations incl. mail safety) | all passed |
| Live regression script (services and features) | 14 of 14 passed |

Live regression detail: Qwen3.5 4B model server answers (1.3 s); backend healthy; agent with web search answered a question correctly (16 s); voice spoke a new sentence; Whisper transcribed a test clip correctly; 2 memories intact; Calendar and Reminders read; Open-Meteo city lookup; Music, Notes and Mail read-only calls answered; `mail_send` does not exist; native app running.

## Roadmap tests A to J

| Test | Result |
|---|---|
| A. One consistent voice | **You confirmed** ("one voice"). Every sentence now copies one reference clip (your 2_question.wav) with the Qwen3-TTS Base model. Measured pitch spread across sentences fell from 88 to 177 Hz to 99 to 131 Hz. The per-sentence style switching is removed (old settings kept, unused) |
| B. Search summaries | **Unit-tested + model checked**: the agent writes a short `SPOKEN:` line in the same turn; the screen shows the full answer without it; speech is that summary plus "The full research is in your workspace"; fallback is the opening of the real answer. "Read the full summary", "tell me more", "go through the details" read the full text. Not yet confirmed by you in the app |
| C. Time and date | **You confirmed.** Answered from the Mac clock, no model |
| D. Weather | **You confirmed** (your screenshot showed your city's weather). City is chosen in Settings; no IP geolocation anywhere in the code (`ip-api.com` was called twice during early testing, then removed) |
| E. Calendar | **Verified** reading; your calendar was empty, so reading real events and time zones is **unit-tested only** |
| F. Reminders | **Verified live**: create, find, complete, undated listed without error (old script error fixed). Overdue, due-today and upcoming sorting is **unit-tested** |
| G. Menu bar mode | **Verified**: closing the window hides it with services and microphone still running; reopening from the Dock works; Quit leaves no JARVIS process. **Not verified**: a real double clap reopening the hidden window (a clap played through the speaker is rejected by the detector). Double clap is **paused** now, so menu bar hiding is off too |
| H. Integrations | Open app: **unit-tested**, not run live (you asked me not to open apps). Music: only "what's playing" run live. Notes search: **verified** (read-only). Reminders create/complete: **verified live**. Calendar event create: **unit-tested** (date safety), not run live. Mail unread and read: **verified live** (read-only; no send, reply or delete exists) |
| I. Performance | See `PERF.md`, Stage 7. JARVIS uses about 6.5 GB; swap is old cold pages, not thrashing; two memory experiments gave no gain and were reverted |
| J. Regression | Model, MLX server, native app launch, memory, research path and existing tool paths pass (above). Clap activation was **not** re-tested because it is paused |

## Not done, and why

- Real double-clap tests (wake, hidden-window wake, false activations) and barge-in with your real voice: need a human in a quiet room. Clap is paused at your request.
- Tell me more about "the second result": needs the source cards wired to speech; not built.
- Editing or deleting calendar events; Spotify song search; Notes writing: not built (Spotify cannot be searched by name from here).
- Briefing items "previous project decisions" and "frequently used apps": not built (nothing records them).
- "Something new and important" mention on later wakes: replaced by "what did I miss".
- GPU and power measurements: need sudo.
- Unused 8-bit voice model (about 3 GB) and the VoiceDesign 4-bit model are still on disk; nothing was deleted without your approval.

## Files changed in this roadmap

Voice and data: `voice-lab/tts_server.py`, `voice-lab/briefing.py`, `voice-lab/integrations.py`, `voice-lab/test_briefing.py`, `voice-lab/test_integrations.py`, `voice-lab/measure.py`, `voice-lab/clone_test.py`, `voice-lab/clone_passage.py`, `voice-lab/stream_check.py`, `voice-lab/memprobe.py`, `data/voice/jarvis-voice.json`, `data/voice/reference/jarvis-ref.wav` (new), listening samples under `data/voice-samples/`.

Frontend (`OpenJarvis/frontend/src/workspace/`): new `norm.ts`, `clock.ts`, `briefing.ts`, `briefState.ts`, `when.ts`, `writes.ts`, `actions.ts`, `mail.ts`, `tasks.ts`, `native.ts` (each with tests where logic exists); changed `brain.ts`, `send.ts`, `settings.ts`, `clapWake.ts`, `WorkspacePage.tsx`, `panels/SettingsPanel.tsx`, `workspace.css`; `tsconfig.json`.

Desktop shell: `OpenJarvis/frontend/src-tauri/src/lib.rs` (hide on close, menu bar menu, show window, Dock reopen, launch-at-login start hidden). `launcher.rs` was changed for an experiment and reverted.

Docs: `PERF.md`, `TEST-REPORT.md`, `README-JARVIS.md`.

## External services contacted

| Service | When | What leaves the Mac |
|---|---|---|
| Open-Meteo (geocoding and forecast) | Only when you set a city or ask for weather or a briefing | The city name you typed, then its coordinates |
| Web search (You.com or DuckDuckGo, via the agent) | Only for research questions | The search query |
| Hugging Face | Once, to download the Qwen3-TTS Base 4-bit model (2.3 GB, saved on the Acer drive) | Standard download request |
| ip-api.com | Twice during early testing, now removed from the code | The Mac's public IP (as any web request does) |

Calendar, Reminders, Notes, Mail, Music and app launching are all local; the email summary is made by the local model.

## Computer access and permissions (2026-11-22, later)

| Item | Result |
|---|---|
| Stable signing with your Apple Development identity | Verified: the designated requirement is now identity-based, so permissions should survive rebuilds |
| Permission flow (name what is blocked, offer to open Settings, wait for "done", retry) | Error recognition and the page whitelist are unit-tested. Not yet seen against a real block |
| Approval channel for risky tools (`server/approvals.py`) | Verified through the live agent: approve ran `echo` and returned its output; deny stopped it; silence times out as no (120 s) |
| File tools (read) limited to Desktop, Documents, Downloads and the JARVIS folder; secrets such as .env and keys always refused by OpenJarvis's own policy | Read of README verified. Allowed folders set in `data/config.toml` |
| Terminal, file write, git commit always ask first | Verified for terminal; the others use the same gate |
| Browser control | Not available: needs Playwright and a Chromium download |
| App-side read-back and voice yes/no for approvals | Unit-tested (wording); not yet tried by voice |
| Files changed | `OpenJarvis/src/openjarvis/server/approvals.py` (new), `server/app.py`, `tools/_stubs.py`, `cli/serve.py` (backups in `data/backups/`), `voice-lab/perms.py` (new), `voice-lab/integrations.py`, `voice-lab/briefing.py`, `src/workspace/permissions.ts`, `approvals.ts`, `send.ts`, `brain.ts`, `actions.ts`, `tauri.conf.json`, `data/config.toml` |

## Browser and screen control (2026-11-22, later)

| Item | Result |
|---|---|
| Chromium (Playwright) on the Acer drive, `data/playwright` (about 600 MB) | Installed; the backend is pointed at it by `launcher.rs`. Verified: the agent opened example.com and read the heading (33 s). Browser click and type always ask first |
| `screen_read` (what is on screen, via macOS Accessibility, text only) | Verified live: the agent read the front app's window (26 s) |
| `screen_click`, `screen_type`, `screen_key` | Written and unit-tested (key mapping, quoting, permission retry logic); gated to always ask first. NOT run against your real screen, since a wrong click or keystroke would act on your apps |
| Missing-permission flow inside the tools | Unit-tested with a fake macOS: asks, opens the page, waits for "done", retries once; a "no" stops cleanly. Not seen against a real block (Accessibility was already allowed) |
| Limits | The 4B model is text-only, so it works from names of buttons and fields, not pictures; apps with poor accessibility info (games, video, some web views) are hard to read; each step takes tens of seconds |
| Files changed | `OpenJarvis/src/openjarvis/tools/mac_control.py` (new), `tools/__init__.py`, `tools/_stubs.py`, `frontend/src/workspace/approvals.ts`, `send.ts`, `brain.ts`, `data/config.toml` |

## Safety rules (2026-11-22, later)

Rules live in `OpenJarvis/src/openjarvis/security/jarvis_policy.py`, are checked in `tools/_stubs.py` before any tool runs, and the folders are in `data/jarvis-safety.json` (editable; anything not listed is refused).

| Tier | What it covers |
|---|---|
| Never, even if you say yes | sudo, rm and any delete, disk and system tools (diskutil, dd, defaults, launchctl, chmod, kill), curl/wget/ssh, scripts that run anything (python, node, sh, osascript), shell variables and substitutions, commands over 400 characters, any path in system folders or JARVIS's own install and data, secrets (.env, keys, passwords), `git push/reset/clean`, patches, `file://` addresses, typing into Terminal/Settings/Keychain/Disk Utility, password fields, and delete or quit shortcuts |
| Runs without asking | read-only commands (ls, cat, grep, find without delete, git status/log/diff, and similar) inside Desktop, Documents, Downloads and the JARVIS folder |
| Asks first, reads it back | writes inside `/Volumes/Acer/JARVIS/workspace` (an overwrite says so and keeps a backup in `data/backups/files`), mkdir/touch/cp/mv inside the workspace, moving something to the Trash (the only kind of delete), typing, clicking, key presses |

Checks: 40+ dangerous commands refused and the safe ones allowed (`tests/security/test_jarvis_policy.py`, all pass); 319 frontend tests pass. Live through the agent: `rm -rf` and `sudo` never ran, a write to the Desktop was refused without asking, a write inside the workspace asked first and ran only after approval. Not tested live: the Trash tool (needs Finder permission) and screen blocks on Terminal. Known gap: shell globs such as `cat ~/Documents/*` are checked by folder, not by every matching file name.

## Automated stabilization run (2026-11-22, evening)

See `AUTOMATED-STABILIZATION-REPORT.md` for the full run and `REPO-RESEARCH-REPORT.md` for the repository audit. Headline: 12/12 live approval, file-safety, browser and calendar checks; 12/12 live regression; 319 frontend, 4 Rust, voice-lab and safety tests pass; upstream's own tests (3,814 passing) show no regression from our changes. Fixed three real issues: intermittent browser thread errors, our confirm list breaking `POST /v1/agents`, and the missing capability entries for `file_trash` and `screen_*`. Still manual: voice approvals, speaking over JARVIS, old-panel closing, screen click and key press, Trash.

## Mac tasks by voice and text: root cause and fix (2026-11-23)

Reproduced with synthesized speech (two macOS voices) through the app's speech recognition: Whisper heard every command correctly, so recognition was not the problem. The failure was routing. Commands the quick patterns did not recognise ("Open Safari and go to YouTube", "What important emails do I have", "I want you to open Chrome", "Open the internet", "Open up Google Chrome") went to plain chat, which has no tools, and the model said it had no access.

Fix: (1) six agent tools, `mac_app` (open or quit apps, open web addresses and files), `mac_mail`, `mac_calendar`, `mac_reminders`, `mac_notes`, `mac_music`, as a thin adapter over the same code the quick commands use; (2) forgiving app-name matching against installed apps (aliases, partial and near matches); (3) requests that mention mail, calendar, reminders, music, apps, the internet or "open" now go to the agent; (4) "open X and do Y" opens X first, then handles Y; (5) calendar, reminder and quit actions read back and ask first; reads and opening run at once. Git tools and browser screenshots were dropped from the agent's list to keep its prompt small.

Verified live through the agent: open Chrome from a spoken-style phrase; open a web address in the default browser; list and read unread email; create a calendar event (one approval, event confirmed in Calendar, then removed); reminder creation asks once. Tests: 324 frontend, safety and tool tests, 182 upstream tests on the changed areas, app-name matching against the real installed apps. Not verified with your real voice. Known limit: the 4B model sometimes skips the second step of a two-step request, which is why the opening step is done by the app first.

## Voice, approvals, interrupt and noise fixes (2026-11-23)

Root causes found (from the traces and the code, not guessed):
- **"I'd like to add it... yes... nothing was added":** the voice handler called `stopPrompt()` before handing your "yes" to the app, which aborted the run, and the aborted run then answered its own open question with "no". The calendar event was never created, but the model still said it was. Fixed: a yes or no is handled first and aborts nothing.
- **Voice refuses, typing works:** old chat messages containing "I don't have access" were sent as history, and the small model copied them; also old topics (Spotify) steered new requests into "quit Spotify". Tool requests now start with no history and a note that it can act on this Mac and must not claim a refused action was done.
- **Card that never went away, and a stuck STOP button:** the card had a 2-minute timer and the command box was locked while waiting. Now the card has Yes and No buttons, disappears when answered or timed out, and the box accepts a typed yes or no.
- **Cannot interrupt while thinking:** the old request kept running in the backend. Added `POST /v1/approvals/interrupt`; agent loops stop after their current model call and open questions count as no. The model server cannot cancel a generation already in progress, so a new model request can still wait for it (for example 26 s before a long search ended); quick commands (open, quit, music, time) never wait for the model.
- **Slow open and close:** these now go straight to macOS with forgiving names: open about 0.2 to 1 s, quit about 1.8 s (was 25 s through the agent). Quit asks nothing, because macOS asks about unsaved work itself.
- **Noise:** after transcription, noise words ("thank you", "you", a stray word) are dropped without thinking; in a loud place (background level above 0.025) JARVIS answers only when it hears its name, or right after it spoke, or when it asked a question. Setting: Settings, "Listening in noise" (Smart, Only when I say Jarvis, Always).

Verified live in the real app by typing: a request that needs a calendar approval showed the card with Yes and No, "Type yes or no" in the box, my typed "yes" created exactly one event at the right time (checked in Calendar, then removed), and the card cleared. "open Spotify" opened it in about 1 s. 333 frontend tests and the safety and policy tests pass. Not tested here: the noise guard with real traffic noise, and speaking over JARVIS while it thinks (needs your voice).
