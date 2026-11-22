# JARVIS speed ledger

Measured on this Mac (M2, 16 GB) with Qwen3.5 4B 4-bit (MLX) and the JARVIS voice (Qwen3-TTS 1.7B 4-bit).
Every interaction logs its own stage timings to `data/logs/perf.jsonl` (milliseconds since you pressed Enter or stopped speaking).
Marks: `route_*`, `first_token`, `tts_request`, `tts_ready`, `audio_start`, `llm_done`, `audio_end`.

## Where it started

A plain "Hey Jarvis!" took 16 s to the first sound (cold) and a normal question about 39 s. Causes found by measuring:

| Cause | Evidence |
|---|---|
| Every message went through the agent loop and arrived all at once (no streaming) | explain-photosynthesis: ~30 s of text before any speech could start |
| Old, very long messages were re-sent as history | a greeting ran one 47 s model call after a huge paste was in the history |
| Memory was sent as a system message, which the agent path ignores | answers stayed ~340 words (no effect); as a note in the message they became ~60 words and 4x faster |
| Up to 1,024 tokens allowed per reply | the model rambled |
| Voice model loaded on first use | 6 to 9 s cold |
| A whole sentence was generated before any of it played | 4.8 s for an 8.5 s sentence |
| New input while busy was silently ignored | later messages looked dead |
| My own background experiment queued ahead of real requests on the single model server | a 57 s wait |

## Kept

| Change | Before | After |
|---|---|---|
| Brain: route greetings to a local reflex | 16 s | 0.03 s (cached phrase) |
| Brain: chat streams straight from the model, short spoken-style persona, 320 token cap | ~30 s to finish text | ~5 s, speech starts after the first sentence |
| Memory as a note in the user message | 340 words / 30 s | 60 words / 7 s |
| History cut to 4 short messages | one stray paste could stall everything | bounded |
| Disk cache of spoken sentences (LRU, 300) | 6.2 s per repeat | 0.00 s |
| Voice warmed when you send, and at app start; kept loaded 4 min | 7 to 9 s cold | first request after launch: first sound at 3.8 s |
| Streaming speech (audio sent as it is produced, played gaplessly) | first audio 4.8 s | 0.78 s |
| First spoken piece kept short (breaks at a comma) | long first piece | shorter wait to speak |
| Research answers: voice reads the first 4 sentences, the rest stays on screen | 100 s of speech | about 15 s |
| A new message interrupts the old one | ignored | stops the old speech, answers the new |

End to end now (first sound): greeting 0.03 s; short chat 3 to 4 s; longer chat 4 to 5 s; research about 30 s (agent plus web search).

## Tried and not kept

| Idea | Why not |
|---|---|
| System message for memory | the agent path ignores it |
| Speculative decoding with a draft model | reported ~1.05x for small 4-bit models; not worth the memory |
| 8-bit voice model | same speed and memory, no clear quality gain (3 GB unused on disk) |
| Pacing cues / seeds / punctuation to fix rushed short voice lines | no effect on very short lines |

## Guard

Re-measure after any change to the model, voice, prompt or send path: send the same three requests and compare `perf.jsonl`.
Budgets: greeting under 0.2 s, warm chat first sound under 5 s, first request after launch under 6 s.

## Still slow, and why

- Research (about 30 s): the agent needs a model call to decide to search, a web search, then a second call to write.
- The model, voice and speech recognition share one 16 GB memory pool. If other apps push the Mac into swap, everything slows; close heavy apps for the best response.

## Stage 7: memory and swap (2026-11-22)

Measured with `voice-lab/memprobe.py` (vm_stat swap counters plus `footprint` per process; no sudo). Footprints include the GPU buffers MLX uses, which plain RSS hides.

| Piece | Footprint |
|---|---|
| Qwen3.5 4B model server | 2.7 GB at start, about 3.3 GB after use (settles; ten different 500-token prompts did not grow it further) |
| Voice server, voice loaded | 2.5 GB |
| Voice server, plus speech recognition loaded | 3.2 GB (Whisper adds about 0.65 GB; first call 1.8 s, then 0.33 s; unloaded after 180 s idle) |
| OpenJarvis backend | 0.11 to 0.14 GB |
| JARVIS app window | 0.03 GB (plus WebKit about 0.2 GB) |
| JARVIS total, everything loaded | about 6.5 GB of 16 GB |

Other apps at the time: Chrome 2.3 GB across its processes, Claude desktop and CLI 1.3 GB.

What the swap number means: 5 to 5.5 GB of the 6 to 7 GB swap file is in use, but swap-ins during idle were tiny (52 to 600 pages, about 1 to 10 MB per 10 s) and `memory_pressure` reported 41 to 59 % free. That is old, cold pages from other apps, not JARVIS thrashing. Speaking caused one burst of swap-outs (about 1 GB) the first time the voice ran after a quiet spell; it did not repeat.

| Idea | Result | Verdict |
|---|---|---|
| Cap MLX cache in the voice server to 256 MB | footprint 2518 MB vs 2521 MB; first audio 1.0 s both | reverted: no change |
| Cap the model's prompt cache (2 entries, 300 MB) | after chat plus research: 3417 MB vs 3717 MB (-300 MB); research 18.7 s vs 17.9 s. But the uncapped server settles at about 3.3 GB anyway under ten different prompts, so there is no runaway to guard against | reverted: not needed |
| Smaller 0.6B voice model | would change the approved voice | not tried |

Timings on this build: first audio of an uncached sentence 1.0 s (warm); speech recognition 0.33 s warm; research 18 to 20 s in these runs.

Conclusion: nothing in JARVIS needed changing. Its footprint is bounded and the biggest items are the two models. To get more headroom, close Chrome (and the Claude desktop app) while using JARVIS heavily. GPU and power draw were not measured (`powermetrics` needs sudo).

## Stabilization run (2026-11-22, evening)

| Measure | Result |
|---|---|
| Quit (app, model, voice, backend, headless browser) | 1 to 2 s, 0 processes left, 3 of 3 cycles |
| Launch to all three services ready (warm) | 6 to 8 s |
| Footprints | model 2.8 GB (4.1 GB after a research run), voice 2.5 GB (3.7 GB with speech recognition loaded, 3.1 GB after it unloads), backend 0.11 to 0.14 GB |
| Swap | 5.1 GB used before and 5.7 of 6.1 GB after the test run; swap-ins during research about 150 MB; memory free 48 to 57 % |
| Agent requests | 7,100 to 7,700 prompt tokens each; the 21 enabled tools are about 2,150 of those (the original 4 were about 330) |
| Web research (3 runs) | 17.6, 24.0, 41.4 s (median 24 s; earlier with fewer tools about 18 s) |
| Voice, uncached sentence (non-streaming) | 4.9 s; speech recognition 1.8 s first call, 0.3 s warm |
| Browser task (open and read a page) | 10 to 33 s |

Recommendation (not applied): per-route tool subsets to bring research back toward 18 s and cut the model's memory growth. Swap headroom is thin: close Chrome and the Claude app for the best speed.
