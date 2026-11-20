# Project JARVIS - Replanned Build Plan (local AI via Ollama)

Replaces the original cloud (OpenAI) plan in `Project_JARVIS_Build_Plan.pdf`.
Last updated: 2026-11-20.

## Decisions
- **Location:** `/Volumes/Acer/JARVIS` (APFS external drive). Code, `.venv`, Git all live here.
- **Hardware:** MacBook Air, Apple M2, 16 GB RAM.
- **AI brain:** local model through Ollama (`ollama` Python package). No API keys, no cloud, no recurring cost.
- **Primary model:** `qwen3.5:4b-mlx` (about 4 GB). Fallback: `qwen3:8b`. Switch via `OLLAMA_MODEL` in `.env`.
  Choice is from specs, not yet benchmarked: Phase 1 includes a benchmark (`tests/benchmark_models.py`) to confirm.
- **Models stay on the internal disk** (`~/.ollama`) so JARVIS model loading is fast.
- **Python:** 3.12 in `.venv` (system 3.14 is too new for many audio/ML wheels).
- **Wake word:** openWakeWord only (fully local). **STT:** local Whisper (whisper.cpp / mlx-whisper / faster-whisper, test on M2). **TTS:** macOS `say`, Piper later.
- **Skipped for now:** specialized decision models (tev1, d1), anything over ~10 GB (27B+, gemma4 26B/31B).

## Memory budget (16 GB)
Brain ~4 GB + Whisper + wake word + your apps. Avoid running two large models at once.
A vision model (Phase 6) loads on demand.

## Safety rules (unchanged)
- Allowlist of tools only; never run model-generated shell commands or code.
- Validate every tool argument. Confirm before deleting/overwriting files, sending messages, purchases, important settings.
- A tool call counts as success only from its real result, never from the model's claim.
- Log tool name + outcome; do not record private audio.
- Mute/stop control and a clear mic-active indicator.

## Local-model risks and mitigations
- Weaker tool calling: small tool list (~6), strict JSON schemas, validate, retry once on a bad call.
- Latency: keep model loaded (`keep_alive`), stream output, fast path for trivial commands.

## Phases
| Phase | Work | Done when |
|---|---|---|
| 0 | Python 3.12 venv, Ollama, model, scaffold, Git | DONE: `python main.py` runs, first commit made |
| 1 | `core/brain.py`, tool registry, validation, retry, text chat loop | DONE |
| 2 | Actions: time, apps (open/close), URLs, web search, system info, confirmation gate | DONE (v0.1) |
| 3 | Mic capture + local Whisper (`python main.py --voice`) | BUILT, mic live test pending |
| 4 | TTS via macOS `say` (Daniel voice, `--speak` / `--voice`) | BUILT (v0.2), audible check by user pending |
| 5 | openWakeWord "hey_jarvis", state machine, mute (`python main.py --wake`) | BUILT, live mic test pending |
| 6 | Memory (SQLite), file search, music, local vision, bounded workflows | BUILT; screen capture needs Screen Recording permission |
| 7 | PySide6 chat window + tray status icon + hotkeys (`--gui`); settings page still to do | PARTIAL |

## Operating notes
- Start Ollama after a reboot: `ollama serve` (not set to start at login).
- Run: `source .venv/bin/activate && python main.py`
- Tests: `.venv/bin/python -m pytest`
