# Hands-free voice: building the wake-word loop

Turn-based `--voice` proves STT and TTS work but leaves the user pressing a key
every turn. Hands-free (say the wake word, it acts and answers aloud) is a
wrapper you build around the already-running agent server — the agent's tools
(`shell_exec`, `file_read`) are reached over HTTP, so the loop never needs its
own tool layer.

Loop shape: continuous mic → wake-word score → on hit, record until VAD silence
→ transcribe → POST to the chat endpoint → speak the reply.

Every component below was executed and verified individually. The wake-word
detector fires once the input gain is corrected (see the sweep section) — but a
hit against the user's own live voice at the corrected default was still
pending, so treat the assembled end-to-end cycle as unconfirmed until you watch
one real command travel mic → transcript → tool call → spoken reply.

## Wake word (openwakeword) — verified setup

Install into the framework's venv: `uv pip install openwakeword webrtcvad-wheels`.

- **Default backend tflite needs `tflite-runtime`, which has no cp313 wheel.**
  Resolution fails outright on a Python 3.13 venv. Force the onnx path instead:
  `Model(wakeword_models=[<path>.onnx], inference_framework="onnx")`.
- **The package ships no models.** Nothing is bundled in `resources/models`, and
  constructing a `Model` without paths fails. Fetch the three files from the
  openWakeWord release:
  - `hey_jarvis.onnx` → your own writable path, passed in `wakeword_models`
  - `melspectrogram.onnx` → `site-packages/openwakeword/resources/models/`
  - `embedding_model.onnx` → same directory

  The last two are feature-extractor internals resolved by path; each surfaces as
  its own `NO_SUCHFILE` when missing, so install them together rather than
  discovering them one round trip at a time.

Sanity check before wiring a mic: score must be ~0.0 for both a zero array and
low-amplitude noise. A model that fires on noise is a threshold problem, not a
code problem.

Prefer the library's own downloader — `from openwakeword.utils import
download_models; download_models(["hey_jarvis"])` fetches the wake model plus
the feature extractors pinned to the installed version, into
`site-packages/openwakeword/resources/models/`, and you can then construct with
`Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")`.
Hand-fetching from a guessed GitHub release URL risks version skew with the
installed lib, and `Model` will happily load a mismatched file instead of
failing. Only hand-place `melspectrogram.onnx` / `embedding_model.onnx` when you
cannot reach the network path.

Note the model key: loading via `wakeword_models=["hey_jarvis"]` keys the
result `hey_jarvis`, while passing a raw `.onnx` path keys it by filename
(`hey_jarvis_v0.1`). Index the dict by the key your construction actually
produces or the test raises `KeyError` on a healthy model.

## VAD (webrtcvad) — verified

`webrtcvad.Vad(2)`, and `is_speech()` accepts only 10/20/30 ms frames —
a one-second buffer raises `Error while processing frame`. At 16 kHz, 30 ms is
480 samples.

Silence returns False, a 300 Hz tone returns True. Always wrap the call: on
exception assume speech so a VAD glitch cannot end a recording early.

Record-until-silence needs a hangover, not an immediate cut — require speech to
have been seen first, then ~900 ms of continuous silence. Cutting on the first
silent frame truncates the first syllable.

## STT: faster-whisper wants a numpy array, not a WAV wrapper

Passing a `BytesIO` containing a `wave`-written buffer fails with
`ValueError: File object has no read() method` — faster-whisper uses PyAV
underneath, which requires a real object with `read()`, and rejects the stream.

Convert and pass the array directly instead:

```python
audio_for_lib = pcm_int16.astype(np.float32) / 32768.0
segments, _ = whisper.transcribe(audio_for_lib, language="pt")
```

Verify transcription by synthesizing known speech with the local TTS and
transcribing it back. Expect small losses on accented vowels from a small TTS
model — `"lê"` coming back as `"Lough"` is a synthesis G2P limit, not a
recognition failure, and does not indicate a STT bug.

## Measuring whether the user's voice is loud enough

Wake-word models are trained on normal-level audio; a quiet room delivers a
low-amplitude signal and the model never fires, which looks identical to "the
loop is broken". Write two probes and read the numbers before changing code.

Signal probe — open the mic for a few seconds, report peak/RMS and how many
frames exceed a floor. Peak near zero means the stream opened but delivered
silence (wrong device, or the selected input is a stereo mix rather than a mic).
A peak around 0.1 with a median two orders lower is a working but quiet mic.

Wake-word probe — record real speech once, then replay it through the detector
at gains spanning **four decades** (1, 10, 100, 1000 — not 1/1.6/2.5/4/6) and
print the best score per gain. `--sensitivity` multiplies the frame before
scoring and clips to [-1, 1] afterwards. Run this probe **before** touching the
loop code — it is the step that distinguishes a mic problem from a detector
problem. A narrow sweep reads as "no effect" when the real answer sits at the
next decade up.

**Sweep the gain over orders of magnitude, and read the curve's SHAPE, not its
endpoint.** A sweep of 1.0/1.6/2.5/4.0/6.0 is not enough to conclude anything:
observed scores were 0.0001 at 1.0, 0.0001 at 1.6, 0.0001 at 2.5, 0.0003 at
4.0, 0.0032 at 6.0 — rising, but the last point is still ~150x below threshold
and reads as "flat" if you stop there. Extending the same sweep to 10/100/1000
gave 0.909 / 0.997 / 0.996. The detector was fine the whole time; the probe
range was too narrow.

The transition is **sharp and exponential, not gradual** — the score sits near
zero and then crosses 0.5 within roughly a decade of gain. So the signature of
"wrong gain" is a low score that is still climbing, and the signature of a real
pipeline fault is a score that is *bit-identical* across every gain.

Use at least four decades (1, 10, 100, 1000) before ruling gain out. Rule of
thumb for the probe: if any two gains give the same score to three decimals,
that is a strong signal the input is not reaching the model at all.

**Use synthetic speech as the control.** To separate "the model is broken" from
"this room is too quiet", synthesize the wake phrase with the project's own TTS
(peak ~0.7, far above any real voice), resample to 16 kHz, and score it. Result
interpretation:

| Real voice | Synthetic control (each at wide gain range) | Meaning |
|---|---|---|
| low | high | gain/room issue — raise `--sensitivity` |
| low | low across all gains | real pipeline fault, not the mic |

Run the control at the **same gain values** as the real-voice sweep. A control
that scores low at 1.0 but high at 10 is the decisive result: the wake model
expects audio roughly an order of magnitude hotter than a normal microphone
delivers, so a low control score says nothing about the pipeline. Recording
the control only at gain 1.0 will send you down the wrong branch.

A genuinely flat control — bit-identical near-zero at 1.0, 10, 100 and 1000 —
does mean the input is not reaching the model. Then compare the model's declared
input shape against what the feature extractor emits, since a mismatched
`melspectrogram.onnx`/`embedding_model.onnx` yields a stable near-zero score
indistinguishable from "no speech detected". That is a research task, not a
calibration task — say so and offer the verified turn-based path rather than
burning turns on it.

Do not conclude the model is corrupt from one test. Fetching a model file by
hand from an old release while the installed lib is a newer version is a real
version-skew risk — but re-downloading via the library's own
`download_models([...])` and re-scoring reproduced the same score, which
**cleared** the file as the cause. Prefer the library's downloader over a guessed
release URL, and let the negative result redirect the investigation.

## Known unresolved behaviour

An open speaker lets the loop transcribe and answer its own TTS output, then
loop. Needs headphones, or a cooldown between cycles. Flag it when handing the
loop over rather than letting the user discover the feedback loop.