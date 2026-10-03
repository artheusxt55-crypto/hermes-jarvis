---
name: adopting-external-agent-frameworks
description: Adopt an external agent framework without forking it.
version: 1.0.0
author: user
license: MIT
metadata:
  hermes:
    tags: [agents, frameworks, adoption, config, research]
    related_skills: [hermes-agent]
---

# Adopting an external agent framework

The class of task: the user points at someone else's agent framework/repo and
asks to run it, extend it, or build "mine" on top of it. The job is to make it
theirs with the least code, not to reimplement it.

## When to Use

- "leia esse repo e me construa um X seguindo isso"
- "quero rodar esse framework aqui"
- "instala e adapta pra mim" pointing at a GitHub URL
- Comparing a framework against Hermes for a stated goal

Not for: ordinary library usage where no adaptation is wanted.

Per-framework notes: `references/openjarvis.md` (config schema, the cloud
engine, the Python upper bound, the `/v1/models` picker filter, speech config)
and `references/serving-ui-and-voice.md` (HTTP API, browser UI, local TTS — each
verified on its own), plus `references/residue-sweep-windows.md` for
decommissioning an install on Windows. `references/hands-free-voice.md` covers the wake-word
loop: openwakeword/VAD/whisper setup, and the gain-sweep probe that separates a
mic problem from a pipeline fault (the detector wants audio ~10x hotter than a
normal mic delivers — sweep decades, not single steps).

## The default answer is configure, not port

A finished framework is a finished framework. Copying N files out of it
produces something worse and costs a merge conflict on every upstream update.
The escalation ladder, cheapest first — stop as soon as it meets the need:

1. **Config** — parameters, model, tool list, identity. No code.
2. **Skill** — procedure as markdown. No code.
3. **Plugin** — new tool outside the repo. No fork, no maintenance.
4. **Surface extension** — the framework's own UI/plugin API.
5. **Fork** — only for a hook the extension system cannot reach, or a change to
   the agent loop itself.

State which rung you are on and why, then stop. Recommending rung 5 when rung 1
would do is the single most expensive error in this class of work.

## Procedure

1. **Shallow clone** into scratch, then map before reading. `git clone
   --depth 1 <url>` — depth 1 keeps a 2000-file repo fast. Do not read files
   one at a time to "understand" it; you will exhaust context and still not know
   where the entry point is.

2. **Fan out parallel readers with disjoint scopes.** Delegate one task per
   subsystem (agent loop, tools, memory/skills/scheduler, install
   feasibility) plus one for docs/roadmap/maturity. Give each child the
   absolute repo path, read-only instruction, and demand quoted real code —
   "do not speculate, say if unclear" is what keeps the output usable.
   Reconcile the reports yourself; children do not see each other.

3. **Verify the config schema against the loader, not the example config.**
   Shipped example configs and presets are routinely stale relative to the
   dataclass that parses them. Read the config module and confirm each field's
   actual type before writing a config file. This is where silent breakage
   lives: a value that parses without error and is then ignored at runtime.

4. **Check host feasibility in parallel with the reading**, not after. Python
   version range, binary availability, native-wheel gaps, and which platforms
   CI actually tests. A framework that declares a Python upper bound below the
   user's interpreter is a real blocker, and finding it late wastes the whole
   analysis.

5. **Write the config, and say plainly what is still not done.** A config file
   that exists while the package is uninstalled is not a working system. State
   the remaining install step rather than letting the artifact imply success.

6. **Get it actually answering before calling the task done.** Run the
   framework's own entry point with a trivial prompt ("reply with OK and
   nothing else"). Load success, `doctor` green and a real completion are three
   different claims; only the third means it works. Read the error text to
   localize which layer failed — engine selection, transport/auth, or model id
   produce distinguishable messages, so the error is the diagnosis, not just a
   failure.

## Decommissioning: removing the install and sweeping residue

The class includes undoing it. When the user asks to delete the code, the code
is often already gone — a `%TEMP%`-hosted clone gets reaped by the OS temp
cleaner — so **verify before deleting anything**. An empty leftover directory
and a missing config are the normal end state, not a failure to report as one.

Sweep in this order, and report findings as a list of what was already clean
versus what you removed:

1. Install tree and config dir (e.g. `~/.<project>/`).
2. Running processes and bound ports (`tasklist`, `netstat -ano | grep :port`).
3. Persistence: `HKCU\...\Run`, `HKLM\...\Run`, env vars, `schtasks /query`,
   Start Menu + Startup folder.
4. Launcher scripts and log dirs the agent shipped for the user.
5. Package managers that may hold it (`npm ls -g`, `uv tool list`).
6. **Your own persistent memory.** An entry describing the install path, ports
   and config location becomes a lie the moment it is deleted; the next session
   reads it and chases a path that does not exist. Delete or rewrite those
   entries in the same pass.

Two rules on scope:

- **Artifacts that merely mention the name are not residue.** Other tooling's
  transcripts, pastes and logs containing the string are history, not residue.
  Name them, offer them, and let the user decide — do not sweep them silently.
- **Report per-item, not a summary.** "Nothing to delete, X was already gone,
  here is the list I checked" is a real result and satisfies the ask.

See `references/residue-sweep-windows.md` for the command set and the search
scope that avoids a full-tree grep.

## Bridging a missing provider credential

Frameworks commonly ship one cloud path per vendor and no generic fallback, so
"switch to the cloud" stalls when the required key belongs to a vendor the
user has no account with. Before reporting a credential blocker, check whether
the project also exposes a **generic OpenAI-compatible client** — it is usually
registered under a surprising engine key (`vllm`, `lmstudio`, `openai_compat`)
because those names predate the generic need, and selecting one does **not**
require that server to be running. Repointing that engine at any
OpenAI-compatible base URL — a local proxy, a gateway, an aggregator — is
usually a one-line config change and needs no code.

Corollary: when a model id is rejected with "engine unavailable for model
X", read the vendor-detection predicate before assuming a missing key. Those
predicates are defined narrowly and positively on purpose, so a typo and an
absent credential produce the same message, and a vendor-prefixed id is
routinely filtered out. Enumerate what the endpoint actually serves instead of
guessing an id.

## Pitfalls

- **The example config lies about field types.** Read the dataclass that parses
  it. Preset TOMLs in the wild routinely show a list where the field is declared
  a comma-separated string; the file loads fine and the setting never applies.

- **Check whether the framework's default identity prompt is now false.** A
  local-first project's stock prompt asserts "you are not X" — swap in a cloud
  backend and that instruction makes the assistant lie about its own backend.
  Rewrite it to state the real one.

- **Deliver the runnable artifact, and run diagnostics yourself.** This user
  asks "what code do I run", "where is the code", "the code in python" — that is
  a request for the literal command, not a description of one. Reply with the
  exact copy-pasteable line in a fenced block and nothing above it. Equally: if
  the blocker is a measurement the machine can take (mic levels, port state,
  model scores), run the probe yourself and read the numbers. Asking the user
  to run a diagnostic and report back costs a full round trip and reads as
  having delegated your own diagnosis; this drew repeated correction.

- **Check shell idioms against the host, not against habit.** Two Windows/git-bash
  idioms that look right and fail: `curl -o /dev/null` returns exit 23 (write
  error) on a large body even with HTTP 200, so a readiness loop built on curl's
  exit status declares a healthy service dead — branch on `-w "%{http_code}"`
  instead. And `taskkill //PID` is rejected with `Argumento invalido - '//PID'`
  because the MSYS `//` prefix does not convert for this native command — use
  `/PID`.

- **Stop proposing architecture when the user asked for a build.** Describing
  the plan, the layers, and the options while producing no artifact reads as
  confidence without evidence, and the user will say so. Build one real thing
  per turn — a file, a skill, a verified config — and let the next turn follow
  from that.

- **State uncertainty instead of hardening it.** "I don't know whether I'm good
  at this yet" is a real answer. Recommending an OS migration or a large fork
  with no task run yet is a guess dressed as a plan.

- **When a sub-goal stops paying, hand back a working path instead of
  grinding.** The user asked for wake-word control; STT, TTS, tool execution
  and VAD were all verified working, and the detector was not. Say plainly
  which parts are proven, that the last one is not, and offer the verified
  turn-based route as a real option — not a consolation prize. Keep pursuing a
  diagnosis for as long as each step tests a NEW hypothesis; when the last
  measurement re-ran the previous one and changed nothing, stop and report
  rather than spending more turns in the same place. Over-claiming a fix you
  have not demonstrated is the worse failure.

- **Don't present an architectural reading as a decision the user already made.**
  "I'm raising this on rung 5" invites agreement rather than scrutiny. Give the
  recommendation and let it stand or fall — overclaiming read as tone-deaf and
  drew a direct correction.

- **Keep claims to what was executed.** An agent's self-report ("it installed
  and ran it") is not verification — a child claiming an install succeeded may
  have read the docs instead of running anything. Reproduce the load-bearing
  claim yourself before reporting it. Same rule for a project's own docs: quote
  a CHANGELOG admission verbatim rather than paraphrasing it as a mild caveat,
  since paraphrasing a serious finding as a soft one is the failure mode.

- **One blast radius per turn.** When a repo offers an install that pulls
  gigabytes and provisions toolchains, scope the verification before running
  it. A read-only analysis answers "can this run here" as well as "does it
  install", without leaving a half-installed multi-hundred-MB environment
  behind.

- **When `write_file` refuses an overwrite with a stale-read guard, stop
  re-sending the same call.** A file you created earlier in the session can get
  stuck behind the read-before-write state. Switch to `patch` for targeted
  edits — it succeeds where rewriting does not.

- **Ask for scope on offensive tooling before running it.** When a framework
  exposes scanners and exploit tooling, confirm the target is the user's or
  authorized. Build the procedure so the scope check is step one, not a caveat
  appended at the end.

- **"It works" is per-surface.** A framework typically exposes an API, a UI and
  speech on top of the agent. They fail independently, so verify each with its
  own command and never let a green CLI stand in for them. Prove the HTTP API
  with a trivial completion before debugging the browser UI — it collapses the
  search space to front-end/route shape.

- **Restart a long-running server after a dependency install.** A process
  started before `uv sync` keeps the old venv, so the new backend stays
  "absent" and fixed endpoints keep returning empty. A fix that appears inert
  is this before it is a wrong fix.

- **A multi-process stack needs a start script, not a hand-typed command
  list.** When the framework needs an upstream proxy plus a server plus a UI,
  ship `start.sh` and `stop.sh` that bring the chain up in dependency order,
  poll each until it answers, and tear the ports down. State the ordering
  constraint in the script's header comment — "the proxy is the inference
  upstream, so the server boots but does not answer without it" is the fact
  that makes the script correct rather than a convenience.

- **Offer a `.bat`/`.sh` launcher when the user keeps asking where the code
  is.** Repeated "what code do I run", "where is it", "send the python" means
  the command did not land as a runnable unit. A double-clickable file removes
  the copy-paste and the path entirely — prefer it over re-sending the same
  command in a different shape. Do this on the **second** request: the first
  miss is a formatting accident, the second is proof that neither the prose
  description, the fenced block, nor a two-line paste landed. Note that
  reformatting the same command a fourth time is not a fix — change the delivery
  mechanism or the session stalls.

- **Run the diagnostic yourself when you have the machine, even mid-task.** If a
  probe needs only your own tool access, running it costs one turn and yields
  the answer; handing it to the user for them to run and paste back costs the
  same turn and returns nothing. Only delegate a probe the user must physically
  perform (say a word aloud, wear headphones) — and when you do, make it one
  double-clickable launcher rather than a command they must retype.

- **Confirm a suspicion with a control before acting on it.** Suspecting a
  corrupted model file, then re-downloading it the supported way and re-
  measuring an identical score, **clears** the suspicion and redirects the
  search. Label the first hypothesis as provisional until a control rules it
  in or out; re-running the same measurement under a new filename proves
  nothing.

- **Reach for the exaggerated control before blaming the weakest link.** When a
  detector/gauge/threshold reads low, the instinct is to suspect the weakest
  component — the user's mic, the room, the shipped file. Instead push the input
  far outside the plausible range first (synthesize a perfect signal, sweep
  amplification across orders of magnitude). An exaggerated control that still
  reads low implicates the pipeline; one that reads high proves the suspect was
  innocent and you have just located the real fix. Skipping this costs multiple
  wrong diagnoses in a row, each stated to the user with growing confidence.

- **Distinguish a verified diagnosis from a verified fix.** Reading the source
  to prove why an endpoint returns empty is a result. A candidate change that
  has not yet produced the correct output is a hypothesis — label it and keep
  going, or the next session inherits it as settled.

## Verification

- The config's every field type was confirmed against the parser source.
- The host-feasibility blockers are named, with the fix for each.
- Whatever was written is a path the user can open.
- The framework's own entry point returned a real completion on a trivial
  prompt — not just a successful load.
- Each shipped surface (API, UI, voice) was exercised with its own check, and
  the ones left unexercised are named as such rather than implied working.
- What remains uninstalled/unverified is stated as such.
