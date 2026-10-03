# Serving, UI and voice layers

The adoption path (config → install → CLI reply) proves the *agent* works. A
framework usually ships three more surfaces that fail independently: an HTTP
API, a browser/desktop UI, and speech. Verify each by its own command; a green
CLI is not evidence for any of them.

OpenJarvis specifics below. The checklist generalizes.

## Verify the API before the UI

The UI is a client of the server. If `POST /v1/chat/completions` answers, the
agent path is proven and every UI failure is front-end or route shape — a much
smaller search space than "the whole thing is broken". Confirm with a trivial
completion before touching the browser.

```
curl -s http://localhost:8000/health
curl -s http://localhost:8000/v1/models | tr ',' '\n' | grep -c '"id"'
curl -s -m 90 http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"<id>","messages":[{"role":"user","content":"reply only: OK"}]}'
```

## Restart the server after changing dependencies

`uv sync` rewrites `.venv` in place. A server process started before the sync
keeps running against the old venv, so a newly installed backend keeps
reporting itself absent and newly populated endpoints keep returning empty.
Symptom is a fix that appears to have no effect. Kill and restart before
concluding the fix was wrong.

## `/v1/models` can be empty while chat works — verified cause

`server/routes.py::list_models` filters engine-advertised ids: it keeps a model
only if `is_cloud_model(m)` is false, or the engine key resolving that model is
`litellm`. `cloud_router.get_provider()` classifies any `vendor/model` id as
`openrouter`, so an aggregator's entire catalogue is treated as direct-cloud.
Served through an OpenAI-compat engine (`vllm`), every id is filtered out, the
response is `{"object":"list","data":[]}`, and the model picker cannot select.
Chat is unaffected because it does not go through this filter.

The design assumption is that cloud ids arrive via the `cloud` engine, not
through a compat engine fronting an aggregator.

**Verified fix: switch the engine key to `litellm`** — it is the one key the
filter lets cloud ids through, and no source patch is needed. `litellm`'s
`list_models` advertises only the configured default model, which is enough to
unblock the picker.

```bash
uv sync --extra inference-litellm --python 3.13
jarvis config set engine.default litellm
jarvis config set intelligence.preferred_engine litellm
jarvis config set intelligence.default_model openai/<id>
export OPENAI_API_KEY=local OPENAI_BASE_URL=http://127.0.0.1:<proxy-port>
```

Two things this costs. The model id **must** carry a provider prefix: litellm
raises `LLM Provider NOT provided` on a bare `vendor/model`, so `openai/`
prefixes it even when the upstream is an aggregator. And the environment must be
exported for the server process itself, not only for one-off CLI runs — a
server started without them comes up healthy and then fails every completion.

Keep the secrets in the environment. `OPENAI_API_KEY=local` is a placeholder,
valid only because that proxy attaches real credentials per request.

## Browser UI

`frontend/` is React + Tailwind (Vite). Pages include Chat, Dashboard, Data
Sources, Agents, Logs, Settings, plus power/cost telemetry and a cost
comparison panel. Setup is `npm install` then `npm run dev`.

- **Vite on Windows binds IPv6 only** by default: it listens on `[::1]:5173`, so
  `http://127.0.0.1:5173` refuses while `http://localhost:5173` returns 200.
  When a port looks dead but the process is healthy, check `netstat` for `[::1]`
  before assuming the dev server failed to start.
- Proxy target is `OPENJARVIS_VITE_PROXY_TARGET`, else `VITE_API_URL`, else
  `http://localhost:8000`. `/v1`, `/health` and `/api` are proxied; the `/v1`
  entry needs `ws: true` or the agents-events WebSocket silently never opens.
- Tauri desktop build needs Rust + Node. Without a Rust toolchain the browser
  UI is the only route — say so rather than promising a native window.
- The chat composer stays disabled with a "pick a model first" placeholder when
  `/v1/models` is empty. That is the empty-list bug above surfacing in the UI,
  not a separate front-end defect.

## Local voice (Kokoro) — verified working

Extra: `uv sync --extra voice` (kokoro, soundfile, sounddevice). 82M model,
offline, no API key. Voice ids are backend-specific and not portable —
`bm_george`/`bm_lewis` (British male), `bf_emma`/`bf_isabella` (British
female), `af_*`/`am_*` (American). `SpeechConfig.voice_id` is interpreted by
`tts_backend` only.

- **STT and TTS are separate config axes.** `SpeechConfig.backend` (`"auto"`,
  whisper) governs transcription; `tts_backend` (`kokoro`, `openai_tts`,
  `cartesia`) governs synthesis. `/v1/speech/health` reflects the STT backend
  only, so it can report `No speech backend configured` while TTS is perfectly
  usable. Do not read that endpoint as a verdict on speech output.
- Kokoro pulls spaCy/misaki for G2P, and **spaCy downloads models at runtime by
  shelling out to pip or uv**. With no pip on PATH it fails with
  `No package installer found`. Put uv on PATH for the run
  (`PATH="<uv-dir>:$PATH"`), not a pip shim.
- espeak-ng is expected on PATH for out-of-dictionary words. Absent on Windows;
  in-dictionary text synthesizes fine, so absence is not a blocker worth
  pre-emptively fixing.
- `get_tts_backend(preferred: str, *, attempted=None)` takes a **backend id
  string**, not a config object. Passing the config raises
  `TypeError: unhashable type` — check the signature before constructing the
  call.
- Confirm output as a real artifact, not a log line: synthesize to a `.wav`,
  then probe it (`ffprobe -show_entries format=duration`).

A verified synthesis is a 24 kHz mono PCM WAV of a few seconds for a
short sentence, tens to hundreds of KB.

## Turn-based voice chat (`jarvis chat --voice`)

`cli/_voice_chat.py` provides the interactive loop: an empty submission starts
recording, `record_until_silence` stops on VAD silence, STT transcribes, and the
answer is spoken through TTS. Requires `sounddevice` and a real input device —
verify with `sounddevice.query_devices()` before promising the flag works.

**This is turn-based, not hands-free.** The user still triggers each turn. There
is no wake word, no hotword, and no clap/sound-trigger path anywhere in the
repo — grep for them before repeating a project's framing of "voice assistant".
Genuine hands-free (say "Jarvis", it answers) is a build: continuous capture +
wake-word detection + VAD loop wrapped around the agent. Say that plainly rather
than implying a flag delivers it. Build notes, including the openwakeword/onnx
install and the mic-level probes that decide whether the wake word can fire at
all: `references/hands-free-voice.md`.

Speech-to-text defaults to auto language detection, which mis-labels short
clips. Set the language explicitly (`speech.language`) once the user's locale is
known.

## STT backend (faster-whisper) — verified working

`--extra desktop` provides `faster-whisper`; `compute_type` must be `int8` on
CPU (`float16` is the config default and is not a valid CPU compute type), and
`device` `cpu`. Check `GET /v1/speech/health` reports
`{"available":true,"backend":"faster-whisper"}` — that endpoint is STT only and
says nothing about TTS.

Round-trip proof beats two separate green checks: synthesize a WAV through
`POST /v1/speech/synthesize`, resample to 16 kHz mono with ffmpeg, then POST it
back to `POST /v1/speech/transcribe`. The returned `text` plus `confidence` is
the only evidence both directions work over HTTP.

## Frontend and TTS are not gated on the model choice

The speech extra and the UI are independent of whether inference is local or
cloud. On a host that cannot run a useful local model (integrated GPU, no CUDA,
~10 GB RAM), local voice plus a subscription-backed cloud model is a coherent
combination — do not treat "the local-first thesis is unserved" as a reason to
skip voice.