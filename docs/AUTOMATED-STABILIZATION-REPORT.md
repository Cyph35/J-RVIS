# AUTOMATED-STABILIZATION-REPORT

Date: 2026-11-22 (evening run). No spoken input, claps or microphone were used, the paused clap feature was not enabled, and nothing was committed. You granted full approval for the run; I used it only inside the safety rules (every test write stayed in `/Volumes/Acer/JARVIS/workspace`, test approvals were given by the test script only for the exact test file, and nothing destructive or security-related was attempted).

Companion files: `REPO-RESEARCH-REPORT.md` (Phase 0), `TEST-REPORT.md`, `PERF.md`.

## Summary

| Phase | Result |
|---|---|
| 0. Repository research | Done. `REPO-RESEARCH-REPORT.md` written. Local copy is essentially current upstream (1 commit behind, a statistics chore). Most capabilities are reused already; custom code remains only where OpenJarvis has a genuine gap |
| 1. Approvals, files, browser, calendar | 12 of 12 live checks pass (after one real bug was fixed, see below) |
| 2. Lifecycle, menu bar, memory, swap | Pass. Quit leaves 0 processes (1 to 2 s); launch is ready in 6 to 8 s; tray icon present; swap and memory measured |
| 3. Regression | All suites pass; 12 of 12 live regression checks; upstream's own tests show no regression from our changes |
| 4. Reports | This file, updated `TEST-REPORT.md` and `PERF.md`, and the checklist below |

## What was found and fixed tonight

| # | Problem | Cause | Fix | Files (backups in `data/backups/`) |
|---|---|---|---|---|
| 1 | Browser tasks failed intermittently ("greenlet / thread switching") | Upstream Playwright sync API is thread-bound, tools run on a thread pool | All browser tools pinned to one thread. 3 of 3 multi-step runs clean afterwards | `tools/browser.py`, `tools/browser_axtree.py` |
| 2 | Upstream test `test_create_agent` returned 400 | Our always-confirm list included `agent_spawn` and `agent_kill`, which `POST /v1/agents` calls without a confirmation channel | Removed those two from the list; our enabled tools still always ask | `tools/_stubs.py` |
| 3 | Upstream test: every built-in tool must be in the capability inventory | Our `file_trash` and `screen_*` tools were missing | Added the entries | `security/capabilities.py` |
| 4 | My first Phase 1 file-write check "failed" | The 4B model mis-copied a 10-digit file name, so the exact-match approval correctly denied it (a safety feature working) | Test now uses a short name | test script only |
| 5 | My first lifecycle timing said "42 s to quit" | A bug in my test (padded line count). Re-measured: 1 to 2 s | none needed | test script only |

## Phase 1 detail (live, against the running app)

| Check | Result |
|---|---|
| `file_write` in the workspace asks once, then writes | Pass |
| Read-only `ls` runs with no question | Pass |
| Overwrite is approved, applied, and the old text is saved to `data/backups/files` | Pass |
| `rm`, `sudo`, write to Desktop, write into JARVIS data: refused, nothing asked, victim file survives | 4 of 4 pass |
| Browser opens a page and reads it | Pass (after fix #1) |
| Web search answers | Pass |
| Calendar tool answers; Calendar and Reminders read through the briefing; undated-safe Reminders search | 3 of 3 pass |
| Approval broker edge cases (silence = no, explicit yes, explicit no, double answer rejected, unknown id rejected) | All pass |
| Voice interruption, research workspace | Unit tests only (53 tests across speaker, capture, VAD, cleanup, store, layout, approvals, send, all pass). Real microphone and speech: manual, see checklist |

## Phase 2 detail

| Check | Result |
|---|---|
| Quit then relaunch, 3 cycles | Quit: 0 JARVIS processes left after 1 to 2 s (app, model, voice, backend, headless browser). Launch: three services ready in 6 to 8 s |
| Close the window with clap paused | App quits cleanly, 0 processes left, ports freed. (Hide-to-menu-bar only applies when clap wake is on; it is paused) |
| Menu bar icon | Present (one status item) |
| Memory and swap | See `PERF.md`. Model 2.8 to 4.1 GB, voice 2.5 to 3.7 GB with speech recognition, backend 0.1 GB. Swap used 5.1 to 5.7 of 6.1 GB, with swap-ins during research of about 150 MB; no sustained thrashing, but headroom is thin |

## Phase 3 detail

| Suite | Result |
|---|---|
| Frontend typecheck | Clean |
| Frontend tests | 319 passed, 52 files |
| Rust tests | 4 passed |
| Voice-lab tests (memory, stretch, briefing, integrations, permissions) | All passed |
| Safety policy tests (40+ dangerous commands) | All passed |
| Live regression (model, voice, recognition, memory, city lookup, Music, Notes, Mail read-only, no send/delete, settings whitelist, approvals) | 12 of 12 |
| Upstream OpenJarvis tests (tools, security, server, agents, core, mcp, scheduler, memory) | 3,814 pass. 42 fail, all also failing on pristine upstream (41 need the missing `openjarvis_rust` extension, 1 loop-guard test). None fail only because of our changes |

## Open risks and recommendations (smallest changes first)

1. **Research is slower than it was** (median 24 s, up from about 18 s) because 21 tools add about 2,150 tokens to every agent request. Recommend giving each route its own tool subset. Not done: behaviour change, needs your choice.
2. **Swap is near full** (5.7 of 6.1 GB after a research run). Closing Chrome and the Claude app gives the most headroom.
3. **OpenJarvis document memory is unavailable** (missing `openjarvis_rust`). Our JSON memory is unaffected. Building the extension is optional and large.
4. **Notes connector** still stores nothing; likely tied to the same environment gap. `knowledge_search` and `deep_research` stay off until it works.
5. **Upstream watch list:** PRs #1289, #1352 (voice), #1334 (filesystem allowlists), #1295 (skill injection scanning), #1317 (calendar).
6. **Housekeeping:** all our changes are uncommitted on upstream `main`. A local `jarvis` branch would make future upstream updates reviewable. Not done without your request.

## Short manual checklist for tomorrow (needs you)

1. Approvals by voice: say "type hello into the front app" with a TextEdit document open, listen to the read-back, say yes.
2. Stopping by voice: while JARVIS is speaking a long answer, speak over it. It should stop at once.
3. Old panels: ask two unrelated questions in a row; the first panel should close when the second starts.
4. Screen click and key press: try "click Save" or "press cmd+n" in a harmless app (not run tonight).
5. Trash: ask it to move a throwaway file from the workspace to the Trash (needs Finder permission; not run tonight).
6. Briefing by voice: "brief me", then add a Calendar event for later today and ask again.
7. Clap (still paused): only if you want it back, flip `CLAP_AVAILABLE` in `src/workspace/clapWake.ts`.
8. Decide: tool subsets for faster research (item 1), and whether to delete the unused 8-bit voice model (about 3 GB).
