# JARVIS: running and rebuilding

Everything runs locally on this Mac. Nothing here uses a paid API or a cloud model.

## Use it

Open **JARVIS** from Applications, Launchpad or Spotlight. It starts its own services:

| Service | Port | What it is |
|---|---|---|
| Model server | 8080 | Qwen3.5 4B through Apple MLX (`mlx_lm`) |
| JARVIS backend | 8000 | OpenJarvis API, orchestrator agent, web search |
| Voice server | 8090 | JARVIS voice (Qwen3-TTS), speech recognition (Whisper small.en), personal memory |

Anything already running (for example started from Terminal) is reused, not duplicated. Quitting the app stops only the services it started, even after a crash.
The drive `/Volumes/Acer` must be mounted. If it is not, the app says so and offers Retry. It never creates data folders elsewhere or downloads models on its own.

## Where things live (all on the Acer drive)

| What | Where |
|---|---|
| Project | `/Volumes/Acer/JARVIS` |
| App source | `/Volumes/Acer/JARVIS/OpenJarvis/frontend` (React + Tauri 2) |
| Rust launcher | `.../frontend/src-tauri/src/launcher.rs` |
| Workspace UI | `.../frontend/src/workspace/` |
| Models and caches | `/Volumes/Acer/JARVIS/data/hf` |
| Settings and voice | `/Volumes/Acer/JARVIS/data/voice/jarvis-voice.json` |
| Personal memory | `/Volumes/Acer/JARVIS/data/memory/jarvis-memory.json` (plain JSON, yours to read or delete) |
| Logs | `/Volumes/Acer/JARVIS/data/logs/` |
| Voice engine | `/Volumes/Acer/JARVIS/voice-lab` (own Python environment) |
| Rust toolchain | `/Volumes/Acer/JARVIS/toolchain` |
| Config backups | `data/config.toml.bak-*`, `env.sh.bak*` |

## Rebuild the app after changing the interface

```bash
cd /Volumes/Acer/JARVIS/OpenJarvis/frontend
export RUSTUP_HOME=/Volumes/Acer/JARVIS/toolchain/rustup CARGO_HOME=/Volumes/Acer/JARVIS/toolchain/cargo
export PATH=$CARGO_HOME/bin:$PATH
npx tauri build --bundles app
rm -rf /Applications/JARVIS.app
ditto src-tauri/target/release/bundle/macos/JARVIS.app /Applications/JARVIS.app
```

Quit JARVIS first (⌘Q). Add `,dmg` to `--bundles` for a disk image. Frontend tests: `npx vitest run`. Rust tests: `cargo test launcher` inside `src-tauri`.
npm 12 is too new for this repo; use `npx --yes npm@11.19.0 ci --ignore-scripts` if dependencies need reinstalling.

## What you can say or type

| Ask | What happens |
|---|---|
| "What time is it", "what's the date" | Answered from the Mac clock |
| "Brief me", "what's my day like", "what did I miss" | Time, weather (city set in Settings), Calendar, Reminders, saved unfinished items |
| "Remind me to call mom tomorrow at 5 PM", "add dentist to my calendar on Friday at 10 AM" | JARVIS reads back what it will do; saves only after you say yes |
| "Mark that reminder complete" | Asks first if more than one reminder could match |
| "Check my email", "search my email for invoice", "summarize my latest email" | Read-only; JARVIS never sends, replies or deletes |
| "Search my notes for X", "open Calculator", "pause the music", "set volume to 40" | Done on this Mac and reported as macOS answered |
| "Research X" | Full answer on screen; JARVIS speaks only a short summary. "Read the full summary" reads it all |

Double-clap wake is paused (switch `CLAP_AVAILABLE` in `src/workspace/clapWake.ts` to bring it back).

## Keys

| Key | Does |
|---|---|
| ⌘⇧M | Voice mode on or off (listens through the microphone) |
| `/` | Focus the command box |

## Privacy

Voice mode and double-clap wake use the microphone only while switched on, and the macOS microphone indicator shows when. Audio is processed in memory; it is never saved. Searches go out to You.com or DuckDuckGo (that is what web search is); nothing else leaves the Mac.
