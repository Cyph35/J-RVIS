# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
A single owner using JARVIS daily on their own Apple Silicon Mac (M2, 16 GB unified memory) for voice and text commands, web research and system control. Local-first and offline-preferred; no paid cloud inference.

## Product Purpose
JARVIS is a personal desktop AI assistant built on the OpenJarvis framework (Stanford Hazy Research, Apache-2.0), running a local Qwen3.5 4B model (MLX) through the existing OpenJarvis backend, memory and tool infrastructure. The interface should feel like a living AI command center, not a chatbot.

## Positioning
A desktop AI environment: a live orb that shows what the assistant is doing, surrounded by a workspace where results (search, research, summaries, charts, media, system info) appear as separate floating panels while the assistant works. Own identity, inspired by the ROSE assistant demo by Huw Prosser, not a copy of its code, branding or assets.

## Operating Context
- Frontend: React 19, TypeScript, Vite, Tauri 2, existing OpenJarvis frontend at `/Volumes/Acer/JARVIS/OpenJarvis/frontend`.
- Backend: existing OpenJarvis server and agents (orchestrator with tools such as web_search, shell_exec); model served by `mlx_lm.server` on port 8080 via `/Volumes/Acer/JARVIS/start-mlx.sh`, with thinking disabled.
- Data lives on the external drive under `/Volumes/Acer/JARVIS/data` (`source /Volumes/Acer/JARVIS/env.sh`).
- Hardware budget: animations must stay light so local inference remains responsive.

## Capabilities and Constraints
- Scope confirmed: the orb workspace becomes the default home screen; existing pages (Settings, Agents, Logs and others) stay reachable from a small control cluster.
- Orb states required: idle, listening, thinking, searching, speaking, error.
- Panels: search results, research articles, text summaries, images, charts, video previews, browser previews, file info, system info, task progress; movable and resizable; several at once.
- Research panels use real backend data only. Never fabricate sources, links, dates, statistics, images or videos. Source citations stay clickable.
- Voice mode and camera are future functionality; controls may exist as placeholders and must be labelled as such.
- Do not rebuild the agent or run a separate inference server. Avoid new dependencies unless needed.

## Brand Commitments
Name: JARVIS. Reference (primary visual inspiration, binding): the ROSE demo video supplied by the user. Binding direction stated by the user: almost-black background, pink/magenta glowing orb, cyan and white technical accents, thin illuminated panel borders, HUD feel, minimal application chrome. The earlier blue dashboard direction is dropped.

## Evidence on Hand
- Real search/research data exists only as the backend returns it; there are no sample sources, statistics or media to reuse.

## Product Principles
1. The workspace is the product: information appears, develops and gets organised as the assistant works.
2. Everything shown is real: no invented sources, numbers or media.
3. The orb communicates state truthfully; it never animates "thinking" when nothing is happening.
4. Light on the machine: efficient rendering that pauses when hidden, leaving the GPU to the model.
5. Original identity: inspired by the reference, not a copy.

## Accessibility & Inclusion
Respect reduced-motion preferences, keep text legible on the dark background, and keep all controls keyboard reachable.
