---
name: agent-self-hosting
description: "Use when the user wants to own the agent itself."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, skills, personality, profile, self-hosting, config]
    related_skills: [hermes-agent, adopting-external-agent-frameworks, hermes-agent-skill-authoring]
---

# Agent self-hosting

The class of task: the user wants the agent to be *theirs* — their skills under
version control, their personality, their own isolated profile — rather than a
default install they can only consume. The job is to move control down the
cheapest rung that actually delivers it, and to be honest about which rung
they landed on.

## When to Use

- "quero total controle de voce" / "criar voce pra mim"
- "meu github de skills", "personalidade propria", "minhas skills"
- "crie um repositorio com as skills"
- "nao preciso fazer fork?" / "da pra alterar voce?"
- "quero rodar [framework] aqui" → see `adopting-external-agent-frameworks`
- a bulk sweep whose deliverable includes an `AGENTS.md` rule →
  `codebase-comment-sweep`

Not for: ordinary skill authoring for one task (`hermes-agent-skill-authoring`),
or adopting someone else's framework wholesale.

## The ladder — cheapest rung that works, then stop

State which rung the user is on and why. Recommending a fork when a config key
would do is the most expensive error in this class.

1. **Prompt file** — `SOUL.md` in the Hermes home. One file, injected into every
   session's system prompt, zero code. This is personality, full stop.
2. **Skills** — markdown procedures in a versioned repo. No code.
3. **Config keys** — `config.yaml` via `hermes config set`. Never hand-edit the
   file; the file tools refuse it by design.
4. **Profile** — `hermes --profile <name>`, giving isolated skills, memory and
   config so a personal agent never mixes with work.
5. **Source** — only for a hook the plugin/tool system cannot reach.

Ask which rung before rung 3 if the user's stated goal is satisfied by rung 1.
Most "I want control over you" asks are a `SOUL.md` request.

## Is the source already here?

Before answering "you need to clone the repo", check. A git-installed Hermes
keeps its source on disk next to the launcher. Prove it resolves to the source,
not to a compiled binary, because that is the fact the whole answer turns on:

```bash
python -c "import hermes_cli; print(hermes_cli.__file__)"
```

A path under the source tree means editing `.py` there changes behaviour. A path
into `site-packages` means it does not.

## Do not offer to "self-modify"

When asked to change the agent's own code, the honest framing is: the user
edits, the agent helps write and review. Applying an untested change to the
runtime executing it is the failure mode, not the shortcut. Personality and
skills achieve the same goal with no such risk — lead with those.

## Wiring a versioned skills repo

The repo is the **source of truth**; the installed skills dir is a cache. Two
keys, both under `skills:`:

```bash
hermes config set skills.create_dir   "C:/Users/<you>/<repo>/skills"
hermes config set skills.external_dirs '["C:/Users/<you>/<repo>/skills"]'
```

- `create_dir` — where `skill_manage` writes new skills. Point it at the repo so
  skills the user asks for are born versionable.
- `external_dirs` — a **list**. `hermes config set` rejects a bare string for a
  list-valued key and prints the expected shape; pass a JSON array in quotes.
- `external_dirs` **adds** to the bundled skills. It does not replace them.
- Re-read the config after every `config set` — the writer has misfiled nested
  keys under a sibling section before, and `hermes config unset <key>` removes it.

Verify with `hermes skills list`: bundled rows plus `local` rows, no errors.

## Making the repo canonical (and the trap)

Once the repo holds copies of the bundled skills, **both** sets resolve and
same-named skills collide. Hermes refuses to load an ambiguous name rather than
guessing, and refuses again on every later load. Fix it by removing one copy:

```bash
rm -rf ~/.hermes/skills/<category>      # keep the repo as the only source
```

**There is no config-only fix.** `skills.disabled` filters by skill *name*, not
by path, so disabling the name kills the repo copy too. Do not spend a turn
discovering this twice.

Then confirm the repo copy loaded: `hermes skills list` shows the count, and an
`Ambiguous skill name` error is gone.

**Tell the user this can regress.** An upgrade of the agent may repopulate the
local skills dir, which restores the collision. The durable options are to
accept a re-check after upgrades, or to keep only user-authored skills in the
repo and leave the bundled set installed.

## Gitignore the runtime state

A skills directory carries machine-specific runtime state that a naive
`git add -A` will version: `.locks/`, `.usage.json`, `.usage.json.lock`,
`.curator_ledger.jsonl`, `.curator_state`, `.bundled_manifest`, `__pycache__/`.
Exclude them at the start, not after they land in a pushed commit.

## Reading a file the user created in the web UI

A file committed through GitHub's web editor never reaches the local clone —
`git status` stays clean and a filesystem search finds nothing. `git fetch`, then
read from the fetched ref:

```bash
git fetch origin
git show origin/main:<path> > /tmp/x
```

If it is not on the default branch, `git ls-tree --name-only origin/main` reveals
what is actually there. A skill in the repo **root** rather than under `skills/`
is never loaded — `external_dirs` points at the skills directory, so a misplaced
file is invisible to the loader and looks like a search failure.

## Pitfalls

- **Versioning the install directory as if it were the user's content.** If every
  skill present is bundled, committing that folder gives the user a copy of
  someone else's work and nothing of their own. Say so and ask whether the repo
  holds the imported base or only their own skills before copying anything.
- **Mistaking a search miss for absence, then searching again.** Checked four
  locations for a filename, found nothing, and asked again. Once a name-based
  and a content-based search over the obvious roots both come up empty, the file
  is elsewhere — ask for the path or the URL instead of widening the search.
- **Promising persistence that a file read does not provide.** Reading a skill
  once puts it in context for this session only. Durable retention is the
  `SOUL.md`, the skill files themselves, or a written memory entry — say which,
  rather than implying the agent "learned" it.
- **Treating a skipped question as permission.** If the user answers a question
  with a different subject, that is not consent to the pending action. Re-ask
  the real one.
- **Answering "can you change yourself?" with the fork branch first.** Find the
  source on disk and present the ladder; most users stop at rung 1 or 2.

## Verification

- `hermes config get` shows both keys under `skills:`, in the right section.
- `hermes skills list` resolves with no ambiguity error and a plausible count.
- The repo is a git repo with the user's own commits, and no runtime state
  tracked.
- The user can name which rung they are on and what it costs them.