# JARVIS

A local, private AI assistant for macOS (Apple Silicon): a native app with a floating-panel workspace, one consistent voice, local speech
recognition, and control of your Mac that always asks before it changes anything. Built on [OpenJarvis](https://github.com/open-jarvis/OpenJarvis).
Everything runs on your Mac. No paid APIs and no cloud AI.

## What it does

- **Talk or type.** Local model (Qwen3.5 4B through Apple MLX), local voice (Qwen3-TTS), local speech recognition (Whisper small.en).
- **Mac tasks.** Open and quit apps and web pages, read Mail, search Notes, control Music, create Calendar events and Reminders, read the
  front app's screen and click or type in it, work with files and the terminal.
- **Safe by design.** Reads run at once; changes read themselves back and wait for your yes. Deleting only moves to the Trash, writes are
  limited to one workspace folder, and `sudo`, system folders, secrets and scripts that run other programs are never allowed
  (`OpenJarvis/src/openjarvis/security/jarvis_policy.py`, `config/jarvis-safety.json`).
- **Research.** Web search with a short spoken summary; the full answer stays on screen.
- **Daily briefing.** Time, weather for the city you choose, Calendar, Reminders and unfinished items.

## What is in this repo

| Path | What it is |
|---|---|
| `OpenJarvis/` | Upstream OpenJarvis plus our changes (see below) |
| `OpenJarvis/frontend/src/workspace/` | The JARVIS interface (React): routing, voice mode, approvals, panels |
| `OpenJarvis/frontend/src-tauri/` | The native macOS app and the Rust launcher that starts and stops the three services |
| `OpenJarvis/src/openjarvis/tools/jarvis_mac.py`, `mac_control.py` | Mac tools for the agent (apps, Mail, Calendar, Reminders, Notes, Music, screen) |
| `OpenJarvis/src/openjarvis/security/jarvis_policy.py`, `server/approvals.py` | Safety rules and the yes/no approval channel |
| `voice-lab/` | Voice server: speech, recognition, memory, briefing, Mac integrations |
| `config/jarvis-safety.json` | The folders JARVIS may read and write (edit to change them) |
| `docs/` | Test report, performance notes, repo research, setup notes |

## Setup (short)

1. Apple Silicon Mac, macOS 14+, about 16 GB of memory, an external or internal drive with roughly 25 GB free.
2. Set up OpenJarvis (`OpenJarvis/README.md`), then create the voice environment in `voice-lab/` (mlx-audio) and download the models
   (Qwen3.5-4B-MLX-4bit, Qwen3-TTS Base 4-bit, whisper-small.en-mlx) with the Hugging Face cache on your drive.
3. Paths such as `/Volumes/Acer/JARVIS` are hard-coded in a few files (`voice-lab/`, `jarvis_policy.py`, `launcher.rs`). Change them to your layout.
4. Build the app: `cd OpenJarvis/frontend && npx tauri build --bundles app`. The signing identity is set to ad-hoc (`-`); use your own
   certificate so macOS keeps the permissions you grant between builds.
5. Grant the permissions macOS asks for (Microphone, Automation, Calendar, Reminders, Accessibility). JARVIS can open the right Settings page
   for you, but only you can switch a permission on.

## Status

See `docs/TEST-REPORT.md` and `docs/AUTOMATED-STABILIZATION-REPORT.md`. Known gaps: double-clap wake is paused; some voice checks need a real
microphone; the 4B model is slower with many tools. This is a personal project, not a polished release.
