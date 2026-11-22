# REPO-RESEARCH-REPORT: what OpenJarvis already gives JARVIS

Date: 2026-11-22. Method: read the installed source (`/Volumes/Acer/JARVIS/OpenJarvis`), queried its live registries, read the official docs pages, and checked the public upstream repository (releases, commits, open pull requests) over the GitHub API. Nothing was merged, installed or changed for this report except that `jarvis skill discover --dry-run` and the registry listings were run read-only.

Rule followed: reuse, then configure, then extend, then adapt, and build only real gaps. Our safety rules (`data/jarvis-safety.json`, `security/jarvis_policy.py`, the approval step) stay authoritative.

## A. Repository findings (what is installed)

| Item | Finding |
|---|---|
| Git | Working copy of upstream `main` at `5a9b5268` (2026-11-21), version `1.0.5.dev239`. Remote `origin` is the official repo. Upstream is only one commit ahead (`c05ebe99`, a traffic-statistics chore), so we are effectively current |
| Our changes on top | 20 modified files and 8 new paths, all uncommitted: Tauri shell (`lib.rs`, `tauri.conf.json`, `Info.plist`, `Entitlements.plist`, capabilities, icons), `frontend/src/App.tsx`, `Sidebar.tsx`, `tsconfig.json`, new `frontend/src/workspace/`, `frontend/src-tauri/src/launcher.rs`; backend `cli/serve.py`, `server/app.py`, `tools/__init__.py`, `tools/_stubs.py`; new `server/approvals.py`, `security/jarvis_policy.py`, `tools/mac_control.py`, `tests/security/test_jarvis_policy.py` |
| Agents (22 registered) | advisors, archon, baseline_cloud, baseline_local, claude_code, conductor, **deep_research**, mini_swe_agent, minions, **monitor_operative**, **morning_digest**, native_openhands, **native_react**, opencode, openhands, **operative**, **orchestrator** (we use this), react, rlm, **simple**, skillorchestra, toolorchestra |
| Tools (61 registered) | web_search, file_read/write, shell_exec, git_*, browser_* (6), calculator, calendar_upcoming/search, get_weather, memory_* (5), kg_* (4), knowledge_search/sql, text_to_speech, audio_transcribe, http_request, pdf_extract, image_generate, code_interpreter (+docker), repl, queue_action / execute_pending_actions / check_permission / record_decision, skill_manage, think, llm, and more. Ours: `screen_read/click/type/key`, `file_trash` |
| Scheduler | `scheduler/` plus tools `schedule_task`, `list_scheduled_tasks`, `pause_scheduled_task`, `resume_scheduled_task`. Present but **not enabled** in our tool list |
| Memory | Four search backends (`sqlite`, `hybrid`, `dense`, `knowledge`), a `FactStore` ("local"), a background `MemoryService` that extracts long-term facts, tools `memory_*` and `user_profile_manage`, and persona files `SOUL.md / MEMORY.md / USER.md` wired into the operative and monitor agents |
| Connectors (27) | apple_calendar, apple_contacts, apple_health, apple_music, apple_notes, imessage, gmail, gmail_imap, imap, outlook, gcalendar, gcontacts, gdrive, google_tasks, notion, obsidian, slack, spotify, dropbox, whatsapp, weather, hackernews, news_rss, github_notifications, granola, oura, strava. **No Apple Reminders and no Apple Mail connector** |
| Skills | 20 bundled skill definitions (`skills/data/*.toml`, e.g. daily-digest, calendar-prep, file-organizer, meeting-notes). **None installed** (`jarvis skill list` is empty). Skill discovery from traces and DSPy/GEPA optimisation exist |
| MCP | Client, server, loader and transports (`mcp/`). No MCP servers configured here |
| Learning and traces | `traces.db` holds 94 traces and 283 steps from our use; telemetry 18 rows. `jarvis skill discover --dry-run` found no recurring tool sequence yet. Router, optimiser and spec-search code exists; nothing retrains the model unless enabled |
| Speech | STT: faster_whisper, openai_whisper, deepgram. TTS: **kokoro (default voice `bm_george`, British male, local)**, openai, cartesia, elevenlabs. We use neither: our voice server runs MLX Whisper and Qwen3-TTS |
| API | About 40 route groups under `/v1/...` (agents, managed-agents, connectors, memory, skills, speech, traces, learning, approvals [ours], and others), a chat WebSocket `/v1/chat/stream`, and an event bus with 50 event types |
| Desktop | `frontend/` (React and Tauri 2) and `desktop/src-tauri/`; both are upstream. Ours is a customised `frontend/` |

## B. Upstream findings (not installed here)

Releases: `v1.0.0` (2026-05-16) and `desktop-v1.0.5` (2026-11-11). Recent commits are security patches (#1306, #1259, #1325) and small fixes (#1314, #1315, #1316). We already contain these.

Open pull requests that touch our areas (none verified or merged; recommendations only):

| PR | What | Relevance |
|---|---|---|
| #1289 | JARVIS voice architecture: wake gating, streaming TTS, barge-in, audio wake word | Overlaps our voice stack; watch |
| #1352 | Desktop hands-free voice mode with a wake word | Overlaps our (paused) clap and voice mode; watch |
| #1320 | Voice-first JARVIS HUD at `/hud` | Overlaps our interface; ignore |
| #1334 | Enforce filesystem allowlists in tools | Overlaps our `jarvis_policy`; compare when released |
| #1295 (draft) | Scan inbound skills for prompt injection | Useful before we ever import a skill |
| #1317, #1313 | apple_calendar: keep upcoming events; map apple_calendar to digest sections | Relevant to our Calendar and briefing |
| #1365 | Rapid-MLX local engine | Alternative to `mlx_lm`; not needed |
| #1351 | Hotwords for transcription | We have our own STT; not needed |
| #1236-#1238, #1234 (drafts) | MCP management and OAuth, agent teams | Future only |

## C. Feature reuse matrix

| Feature | OpenJarvis capability (where / interface / enabled here) | JARVIS implementation today | Recommended action |
|---|---|---|---|
| Web search and research | `web_search` tool, orchestrator agent (`agents/orchestrator.py`, tool calling). **Enabled and used** | Same, plus our spoken-summary line in the user message | **Reuse (already)**. Keep our summary wrapper |
| Deep research | `deep_research` agent (`agents/deep_research.py`): multi-hop retrieval over indexed personal data with citations. Needs data in `knowledge.db`; ours has 0 chunks | Not used; our "research" is web search through the orchestrator | **Leave.** Revisit once notes or calendar data are indexed |
| Morning briefing | `morning_digest` agent + `digest_collect` tool (sources: messages, calendar, health, world, music; can speak via TTS); depends on connectors | Own composer (`briefing.ts`, `voice-lab/briefing.py`): clock, Open-Meteo, AppleScript Calendar/Reminders, saved tasks | **Keep custom, evaluate later.** Our version works and is local; the digest agent could replace the narrative once connectors hold data |
| Calendar read | `calendar_upcoming`, `calendar_search` tools and `apple_calendar` connector (reads Calendar's database; needs Full Disk Access, now granted) | AppleScript read in `briefing.py` | **Reuse already for agent questions** (enabled). Keep AppleScript for the fast briefing path |
| Calendar write | None found (tools are read-only) | `event_create` in `integrations.py`, confirmed first | **Keep custom** (genuine gap) |
| Reminders | None (no tool or connector) | AppleScript create, complete, find | **Keep custom** (genuine gap) |
| Notes | `apple_notes` connector (database read, now permitted; stores 0 items, cause not found) | AppleScript search and read | **Keep custom; investigate the connector** |
| Mail | No Apple Mail connector. `gmail`, `gmail_imap`, `imap`, `outlook` need accounts or app passwords | Read-only AppleScript Mail | **Keep custom** (genuine gap for local Mail.app) |
| Music | `apple_music` connector reads the library; `spotify` needs OAuth. No playback control tool | Play, pause, skip, volume via AppleScript | **Keep custom** (genuine gap: control) |
| Personal memory | `FactStore`, `MemoryService`, `memory_*` and `user_profile_manage` tools, 4 search backends, persona files | JSON memory with explicit save, confirmed preferences, sensitive-data refusal, editable UI | **Complement, do not merge.** Possible later: use `user_profile_manage` for the agent's view of preferences |
| Persona and prompt | `system_prompt.md` override per agent at `$OPENJARVIS_HOME/agents/<name>/` (`agents/prompt_loader.py`), persona files | Persona and style are added in `brain.ts` and `send.ts` as user-message notes | **Candidate to migrate**: moving the spoken-style and tool guidance into the orchestrator's `system_prompt.md` would remove prompt code from the app. Test first |
| File operations | `file_read`, `file_write` with `allowed_dirs`; sensitive-file policy (`security/file_policy.py`) | `jarvis_policy` (workspace-only writes, backups, Trash) layered over them | **Preserve our wrapper**; reuse the tools |
| Terminal | `shell_exec` (confirmation required) | Whitelisted read-only commands, workspace-only changes, never sudo or rm | **Preserve our wrapper**; reuse the tool |
| Approvals | `confirm_callback` in `ToolExecutor`; `approval_store` and proactive tools (queue/approve actions); upstream bell UI | `server/approvals.py` broker and voice read-back | **Keep custom** (the callback hook is reused; upstream has no voice-ready channel) |
| Browser | `browser_*` tools (Playwright). **Enabled and used** | Only config and a Chromium on the Acer drive | **Reuse (already)** |
| Screen control | Only `browser_axtree`; no desktop control | `screen_read/click/type/key` through Accessibility, guarded | **Keep custom** (genuine gap) |
| Speech to text | `faster_whisper` (CTranslate2) and cloud backends | MLX Whisper small.en in the voice server | **Preserve ours** (runs on the Apple GPU, already tuned) |
| Text to speech | Kokoro (local), cloud TTS; PR #1289 for streaming voice | Qwen3-TTS Base, cloned from your chosen clip, streaming and cached | **Preserve selected voice**. Kokoro `bm_george` is a free local alternative only if you ever want one |
| Scheduling | `scheduler` plus `schedule_task` tools; cron, interval, once | First-wake-of-day logic in the app (tied to the paused clap) | **Evaluate**: scheduler tools could trigger the daily briefing without a clap. Not enabled yet |
| Learning | Trace store, analyser, skill discovery, router, DSPy/GEPA skill optimisation | Preference memory only | **Explore safely**: keep collecting traces; run discovery later. No model retraining |
| Skills | 20 bundled TOML skills; importer; MCP | None installed | **Do not install now.** Inspect each before use; wait for #1295 style injection scanning |
| Desktop UI | Tauri and React `frontend/` | Our workspace, launcher, tray, signed app | **Preserve and extend** |
| Services lifecycle | `jarvis serve`, daemon, `doctor` | Rust launcher starts, watches and stops three services | **Keep custom** (needed for the native app) |

## D. Duplicate implementation analysis

| Custom JARVIS code | Overlaps with | Decision |
|---|---|---|
| `voice-lab/briefing.py` + `src/workspace/briefing.ts` | `morning_digest` agent, `digest_collect`, `apple_calendar` connector | **Retain.** Revisit when connectors are indexed; adapter possible |
| `voice-lab/integrations.py` Calendar/Notes/Mail/Music reads | `calendar_*` tools, `apple_notes`, `apple_music` connectors | **Retain** for speed and for writes; the agent already uses the built-in calendar tools for open questions |
| JSON memory (`memory_store.py`, `memory-policy.ts`) | `FactStore`, `MemoryService`, `user_profile_manage` | **Retain as is.** Complement later, never auto-merge |
| Spoken-style prompt handling (`brain.ts`, `send.ts`) | `system_prompt.md` override, persona files | **Gradual migration candidate** after tests |
| `server/approvals.py` | `ToolExecutor` confirm callback and `approval_store` | **Retain**; it plugs into the upstream hook, not beside it |
| `security/jarvis_policy.py` | `file_policy.py`, `allowed_dirs`, upstream PR #1334 | **Retain** (stricter); compare to #1334 once merged upstream |
| Tauri launcher, tray, signing | Upstream desktop sidecar start | **Retain** (different design: three services, external drive) |
| Voice stack (MLX Whisper, Qwen3-TTS, barge-in, wake) | `speech/`, PRs #1289, #1352 | **Retain**; do not mix |

## E. Security assessment

- Imported capabilities respect our gate: `ALWAYS_CONFIRM` and `check_tool()` run inside `ToolExecutor.execute`, before every tool, including any added later.
- Risks to watch: `http_request` (can send data out), `code_interpreter` and `repl` (run code), `channel_send` (sends messages), `agent_spawn`. They are **not** in our enabled tool list. Keep it that way unless reviewed.
- Skills and MCP servers: none installed. An imported skill or MCP tool would still pass through `ToolExecutor`, but a skill can change the agent's instructions, so each one needs source and permission review first. Upstream PR #1295 (prompt-injection scanning) is the right feature to wait for.
- Connectors store personal data in `knowledge.db` on the Acer drive. The Notes and Calendar connectors have Full Disk Access via the signed JARVIS app. Keep them off unless you want indexing.
- Network: web search (You.com or DuckDuckGo), Open-Meteo (city only), Hugging Face (one-time model downloads), GitHub API (this report: no personal data sent).
- Never overwritten: the local modifications. Upstream code was not copied in.

## F. Performance assessment (16 GB)

- JARVIS resident today: model about 3.3 GB, voice server 2.5 GB (3.2 GB with speech recognition loaded), backend about 0.14 GB, headless browser about 0.24 GB while used. Total about 6.5 GB.
- Adding Kokoro or faster-whisper would add a second speech stack for no gain. Skills, scheduler and MCP clients cost almost nothing at idle. Deep research and connector indexing add CPU and disk work only while running; embeddings are optional (Ollama only; the code falls back to text search).
- Agent latency with the extra tools: web search 12 to 23 s, calendar and maths 3 to 10 s, browser about 33 s, on the 4B model.

## G. Recommendations (smallest changes first)

1. **Nothing to rebuild right now.** Everything else in the table is already reused or is a genuine gap.
2. **Trial: persona via `system_prompt.md`** for the orchestrator, to retire prompt-building code in `send.ts`. Why: removes custom code and keeps the persona in one place. Test with the 4B model before switching.
3. **Trial: scheduler tools** (`schedule_task`) to trigger the daily briefing without a clap. Why: the clap is paused, and the scheduler is the built-in answer. Enable only after a test run.
4. **Find why the Notes connector stores 0 notes** (missing embedder is ruled out; text extraction on this macOS version is the likely cause). Why: it would let `knowledge_search` and `deep_research` work on your notes.
5. **Keep collecting traces**; rerun `jarvis skill discover --dry-run` after more use. No retraining.
6. **Watch upstream PRs** #1289, #1352, #1334, #1295, #1317. Adopt only after they are merged and tested against our changes.
7. **Housekeeping:** our changes are uncommitted on `main`. A local branch (for example `jarvis`) would make future upstream updates reviewable. Not done, because nothing is committed without your request.

## H. Findings from the stabilization tests (they change some recommendations)

1. **The native Rust extension `openjarvis_rust` is not installed in our environment.** 41 upstream memory and storage tests fail for exactly this reason, and the same tests fail on a pristine upstream copy (they are not caused by our changes). Consequence: OpenJarvis's own document-memory backends (`sqlite`, `hybrid`, `dense`) raise `MemoryBackendUnavailable` here, so the `memory_*` tools cannot be used today. This supports keeping our JSON memory. Building the extension (the `rust/` crate, with the Rust toolchain already on the Acer drive) is the way to unlock them, and it may also explain why the Apple Notes connector stored nothing. Not done tonight: it is a large build and would add a compiled component.
2. **Upstream bug found and fixed (small adapter):** the browser tools use Playwright's sync API, which only works on the thread that started it, while the tool executor runs tools on a pool of threads. Result: intermittent "greenlet / thread switching" failures (one failed live run, then 3 of 3 clean after the fix). Fix: `tools/browser.py` and `tools/browser_axtree.py` now run every browser call on one dedicated thread (`pin_to_browser_thread`). Worth reporting upstream.
3. **We were missing a registration upstream expects:** every built-in tool needs an entry in `security/capabilities.py` (`DEFAULT_TOOL_CAPABILITIES`), otherwise it is treated as `system:admin`, and an upstream test fails. Added `file_trash` and `screen_*`. This is reuse of upstream's capability system, not a new one.
4. **Our confirmation list broke an upstream endpoint:** `ALWAYS_CONFIRM` included `agent_spawn` and `agent_kill`, and upstream's `POST /v1/agents` calls those without a confirmation channel (it returned 400). Removed those two. Our enabled mutating tools (`file_write`, `shell_exec`, `git_commit`, `browser_click/type`, `screen_*`, `file_trash`) are unaffected and still always ask.
5. **Upstream test comparison:** 3,814 upstream tests pass with our changes in `tests/tools`, `security`, `server`, `agents`, `core`, `mcp`, `scheduler`, `memory`. 42 fail, and every one of those also fails on a pristine upstream copy (41 are the missing Rust extension, one is a loop-guard test). Nothing fails only because of our modifications.
6. **Tool descriptions are costly on a 4B model:** the 21 enabled tools add about 2,150 tokens to every agent request (4 tools were about 330). Agent requests now carry about 7,100 to 7,700 prompt tokens in total, and web research has a median of 24 s (17.6, 24.0, 41.4 s), up from roughly 18 s. Smallest fix, when you want it: give each route its own tool subset (research: search, calendar, calculator; computer access only when asked). Not done tonight, because it changes behaviour.
