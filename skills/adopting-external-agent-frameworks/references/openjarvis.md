# OpenJarvis

Stanford project, Apache 2.0, `github.com/open-jarvis/OpenJarvis`. Python, ~30
modules under `src/openjarvis/`, ~2169 files. Local-first thesis: run on-device
by default, call the cloud only when needed. Installers for macOS/Linux/WSL2
(`install.sh`) and native Windows (`install.ps1`); desktop GUI builds ship in
GitHub releases. `jarvis` starts a chat, `jarvis gui` the browser interface,
`jarvis init --preset <name>` writes a starter config, `jarvis doctor` reports
status. `jarvis gui` needs Node 22+.

## Hard blocker on a modern interpreter

`pyproject.toml` declares `requires-python = ">=3.10,<3.14"`. The in-repo
comment explains why: numpy 2.2.x ships no cp314 Windows wheel, so under 3.14
uv compiles numpy from source with Meson and fails without a C toolchain. On
Python 3.14 the user needs `uv` to provision a supported interpreter, or an
older one — do not attempt a bare `pip install`.

## Config lives at `~/.openjarvis/config.toml`

Verify every field against `src/openjarvis/core/config.py` before writing.
Confirmed from source:

| Section | Field | Actual type |
|---|---|---|
| `[engine]` | `default` | str — `"ollama"` default, `"cloud"` for API |
| `[intelligence]` | `provider` | str — `local`/`openai`/`anthropic`/`google` |
| `[intelligence]` | `default_model` | str |
| `[intelligence]` | `preferred_engine` | str — pins engine, blocks silent local fallback |
| `[agent]` | `default_agent` | str — `"simple"` default, `"orchestrator"` for tool selection |
| `[agent]` | `tools` | **str, comma-separated** (replaced the old `default_tools`) |
| `[tools]` | `enabled` | **str, comma-separated** |
| `[agent]` | `system_prompt` | inline str, takes precedence over the default |

The shipped example presets render `enabled` as a TOML **list**, which does not
match the declared `str`. Loading succeeds and the tool set silently does not
apply. Use CSV.

## Cloud instead of local

No fork needed. `src/openjarvis/engine/cloud.py` reads `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`,
`DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`, `OPENAI_CODEX_API_KEY`,
`ATLASCLOUD_API_KEY` and picks the client by model-id prefix
(`_is_anthropic_model` and siblings). Set `[engine] default = "cloud"` plus
`[intelligence] provider` and a matching model id. `engine/_discovery.py`
handles engine selection and has explicit local/cloud boundary logic; set
`preferred_engine = "cloud"` so a cloud outage does not silently fall back to a
local engine.

**The `cloud` engine is NOT a generic OpenAI client.** The prefix predicates are
narrow and a mismatch fails closed with
`Requested engine 'cloud' is unavailable for model '<id>'; no substitute was
selected`. Confirmed behaviour:

- `_is_openai_model` is defined **positively** — only `gpt-*`, `chatgpt-*`,
  `o1/o3/o4` series. A bare `claude-sonnet-4-6` routes to the Anthropic client,
  which then needs `ANTHROPIC_API_KEY`.
- `anthropic/claude-sonnet-5.5` is also rejected: the vendor-prefixed form is
  filtered out by the openrouter/atlascloud guards.
- Any unrecognized id deliberately falls through to "not available" rather than
  to a generic client, so a typo and a missing credential look identical in the
  log. Read the predicate, do not guess the id shape.

## Verified route to an OpenAI-compatible endpoint

`_OpenAICompatibleEngine` (`engine/_openai_compat.py`) is registered under the
registry keys `vllm`, `sglang`, `llamacpp`, `mlx`, `lmstudio`, `exo`, `nexa`,
`uzu`, `apple_fm`, `lemonade` — all in the `_ENGINES` dict in
`engine/openai_compat_engines.py`. **These keys are just names**: selecting
`vllm` does not require vLLM running. Point any of them at an arbitrary
OpenAI-compatible base URL:

```bash
jarvis config set engine.vllm.host http://127.0.0.1:8645   # prints "Reachable"
jarvis config set engine.default vllm
jarvis config set intelligence.preferred_engine vllm
jarvis config set intelligence.default_model <id-that-endpoint-serves>
```

This is the working path for pointing OpenJarvis at a subscription-backed local
proxy instead of buying a separate provider key. A token of `local` suffices
when the proxy attaches real credentials itself.

Paid-vs-free is a real split on subscription-backed endpoints: a paid model id
resolves and then returns `404 requires available credits ... pick a free
model`, while a free id completes. Enumerate what the endpoint actually serves
before choosing, rather than copying an id from a blog post.

## `/v1/models` is filtered, and that decides which engine key to use

The chat endpoint can work while the model list comes back
`{"object":"list","data":[]}` — an empty picker looks like "no models
available" and blocks the browser UI from selecting anything, even though
`jarvis ask` completes fine. Different layers, different symptoms.

Cause is in `server/routes.py::list_models`: it drops every id where
`is_cloud_model(m)` is true, keeping it only when
`_engine_key_for_model(engine, m) == "litellm"`. `is_cloud_model` delegates to
`get_provider`, which classifies **any `vendor/model` shape as openrouter**. So
every id an OpenAI-compatible aggregator serves gets classified as cloud — and
because the OpenAI-compat route above uses key `vllm`, all of them are
filtered out.

Two ways out, in order of preference:

1. **Switch the engine key to `litellm`.** It is the one key the filter admits.
   Install `inference-litellm`, set `engine.default = "litellm"` and
   `preferred_engine = "litellm"`. Note `LiteLLMEngine` advertises only
   `config.intelligence.default_model` from `list_models()` — one entry is
   enough for the picker, and it does not need to enumerate the aggregator.
   **The model id then needs an explicit provider prefix** (`openai/<id>`);
   bare `vendor/model` fails with `LLM Provider NOT provided`.
2. Patch the route's filter. Only if the first conflicts with something else —
   it means editing project source and carrying merge cost.

Confirm directly: `curl -s localhost:8000/v1/models` should contain the
configured id.

## Speech: STT and TTS are separate config keys with separate backends

`SpeechConfig` splits them and they fail independently:

- `backend` — STT: `auto` / `faster-whisper` / `openai` / `deepgram`.
- `tts_backend` — `kokoro` / `openai_tts` / `cartesia`, plus `voice_id`,
  `voice_speed`.

`GET /v1/speech/health` reports **STT only**; TTS health is
`/v1/speech/tts/health`. A green STT check says nothing about whether the agent
can speak, so check both.

**Set `compute_type` to `int8` on CPU.** The default is `float16`, invalid for a
CPU inference device; `device = "cpu"` alone still fails. Set `language`
explicitly (e.g. `pt`) — the default is auto-detect, which mis-transcribes
short clips into English.

Kokoro voices include `af_heart`, `af_bella`, `af_nicole`, `af_sarah`,
`af_sky`, `am_adam`, `am_michael`, `bf_emma`, plus `bm_*`/`am_*` variants. It is
~82M params, runs offline, needs no API key; output is ~24 kHz mono PCM. Its
small phoneme inventory mangles accented vowels, so synthesized `"lê"` coming
back as `"Lough"` is expected and is not a STT defect.

Endpoints: `POST /v1/speech/transcribe` (multipart `file`) and
`POST /v1/speech/synthesize` (JSON `{"text": ..., "voice_id": ...}`) returning
a WAV. A TTS→STT round trip proves both at once.

## Verify end-to-end, and read which layer failed

Config that loads is not a working system. The confirming command is
`jarvis ask "..."` — and the error text localizes the failure:

- `No inference engine available` + engine list → engine selection rejected the
  id; check the prefix predicate.
- `returned 404 for /v1/chat/completions` with an upstream JSON body → transport
  and auth are fine, the **model** is the problem (wrong id, or credits).
- Bare connection failure → the endpoint is not listening or the host is wrong.

Absence of `openjarvis_rust` (no Rust toolchain) prints a rate-limiter warning
and is **degraded, not broken** — chat, agents, tools, scheduler and speech all
run. The Rust extension disables the rate limiter and the ColBERT memory
backend only.

## `uv sync` prunes extras you omit

`uv sync` resolves to the requested extras only and **uninstalls** anything not
listed. Syncing `--extra inference-litellm` alone silently removes the server and
voice extras. Pass the full set every time:

```bash
uv sync --extra server --extra desktop --extra voice --extra inference-litellm --python 3.13
```

`desktop` is where `faster-whisper` lives — not `server`. Omitting it makes
`ModuleNotFoundError: No module named 'faster_whisper'` while the config claims
the backend is configured, which reads as a config bug rather than a missing
extra.

## Identity lives in `SOUL.md`, not in the config

`AgentConfig.default_system_prompt` reads "You are OpenJarvis... You are not
Claude, ChatGPT, Gemini, or any other branded assistant." Point the backend at a
different vendor and that instruction makes the agent misreport itself.

**`[agent] system_prompt` does not fix this.** It parses fine and is silently
inert: `cli/ask.py` wires the `SystemPromptBuilder` from
`config.agent.default_system_prompt` and the persona file set, and that builder
is only passed to agents whose `__init__` names a `prompt_builder` kwarg. An
agent configured otherwise never sees the configured string. Symptom is the
agent still answering with the framework's own name.

The working path is `~/.openjarvis/SOUL.md` (path from
`MemoryFilesConfig.soul_path`). Write identity, response language, and the
priorities you want obeyed there; confirm with a question whose answer differs
between the two.

## Tool modules present

`src/openjarvis/tools/`: `shell_exec`, `docker_shell_exec`, `file_read`,
`file_write`, `apply_patch`, `git_tool`, `code_interpreter`,
`code_interpreter_docker`, `browser`, `browser_axtree`, `http_request`,
`web_search`, `think`, `calculator`, `repl`, `memory_manage`,
`user_profile_manage`, `skill_manage`, `knowledge_search`, `knowledge_sql`,
`db_query`, `retrieval`, `mcp_adapter`, `text_to_speech`, `audio_tool`,
`image_tool`, `pdf_tool`, `storage_tools`, `weather`, `llm_tool`,
`proactive_tools`, `channel_tools`, `digest_collect`, `scan_chunks`.

Other subsystems worth mapping before extending: `agents/` (incl. `hybrid/`),
`core/`, `engine/`, `memory/`, `skills/`, `scheduler/`, `sessions/`, `mcp/`,
`sandbox/`, `security/` (`_SECURITY_PROFILES` + `apply_security_profile`),
`channels/`, `server/`, `recipes/`, `prompt/personas/`, plus a `rust/`
extension and a `frontend/`.
