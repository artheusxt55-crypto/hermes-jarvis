---
name: codebase-comment-sweep
description: "Use when removing or auditing comments across a whole repo."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [comments, cleanup, ai-slop, codebase, repo-wide, agents-md]
    related_skills: [simplify-code, codebase-inspection]
---

# Codebase Comment Sweep

Repo-wide removal (or audit) of comments that only restate the code —
"increment the counter", "returns the history", section-banner noise. The
temptation is to count comment lines and delete them in one pass. **Do not.**
The same count is full of documentation that is load-bearing.

**Core principle: classify first, delete only the narration bucket.** A
comment sweep that runs before the user has seen the breakdown reads as
competence and destroys work.

## When to Use

- "remove the comments the AI writes" / "tira as explicação dos códigos"
- "clean the narration out of the repo" / "less comment noise"
- "those grey texts in the code" / "os textos cinzas" / "apagar os textos"
- "does my repo have AI-slop comments?"
- any ask to bulk-edit or bulk-delete comments across many files

This skill is repo-scoped. For comments inside an uncommitted diff, use
`simplify-code` instead — it already flags `// increment counter`-class slop
as a quality finding. Do not fan `simplify-code`'s four reviewers out for a
whole-repo sweep; the cost model is wrong.

## Phase 1 — Get the repo

```bash
git clone --depth 50 <url> <name>     # shallow is enough for a comment audit
git -C <name> ls-files | wc -l
```

**Never guess the repo URL from a project name.** A web search for a
handles-like project name returns unrelated repos (EC-CUBE, EDUCA, EDUCE…),
and cloning the wrong one wastes the whole pass. Ask for the URL or for
`user + repo name`.

Public repos clone with plain `git` — no token. Read and audit need no
credentials at all; only *writing* to the user's repo does.

## Getting write access (only when the user grants it)

Don't install or authenticate until the user explicitly authorizes a push —
but when they do, expect it to work and do it rather than handing the work back.
The path on Windows:

```bash
winget install --id GitHub.cli --exact --source winget \
  --accept-source-agreements --accept-package-agreements
"C:/Program Files/GitHub CLI/gh.exe" auth login --hostname github.com --git-protocol https --web
"C:/Program Files/GitHub CLI/gh.exe" auth setup-git     # required before push
```

`gh auth login --web` prints a one-time device code and blocks on the browser
confirmation — run it with `background=true, pty=true`, answer the
"Authenticate Git with your GitHub credentials? (Y/n)" prompt via
`process(action='submit')`, then `submit` an empty string for Enter to open
the browser. The user pastes the code; that page is a GitHub permission screen
you cannot click for them. A Windows Credential Manager window may pop up from
the credential-helper answer — it is optional and safe to dismiss.

**`gh auth setup-git` is the step people skip.** Without it `git push` fails
with `could not read Username for 'https://github.com'` because the token lives
in the OS keyring and plain git doesn't consult it. Also pass
`GIT_TERMINAL_PROMPT=0` so a missing credential fails fast instead of hanging
on a `/dev/tty` prompt that has no TTY in a tool session.

Confirm with `gh auth status` (check the `repo` scope is present) before relying
on it. If `git commit` stops on "Author identity unknown", the `gh` token often
lacks the `user:email` scope — do not invent an email. Set the GitHub-derived
noreply address locally, scoped to the repo with `git config` (not `--global`):

```
git config user.name  "<login>"
git config user.email "<numeric-user-id>+<login>@users.noreply.github.com"
```

Tell the user this was done and offer to amend with their real address.

Native Windows programs do not accept MSYS paths, so pass `C:/Users/...` style
paths to `git` and `gh` — `git commit -F /c/Users/.../msg.txt` fails with
"could not read log file", and a native path is what works.

## Phase 2 — Inventory, do not count

Run the classifier and read the buckets:

```bash
python scripts/comment_inventory.py <repo-path>
```

It reports per-file comment lines split into three buckets:

| bucket | what it is | default action |
|---|---|---|
| `banner` | `// ==== TITLE ====`, `// ---- TITLE ----` | **ask** — usually deliberate author style |
| `narration` | comment starts with the verb the next line performs ("retorna", "incrementa", "define") | **delete** |
| `other` | everything else | **keep, inspect on request** |

The `other` bucket is where the value is. Security rules ("the UID comes from
Firebase, never from the frontend"), rate-limit semantics, protocol and DB-key
formats, and bug workarounds all live there — and in a student or client
project those comments are often the deliverable.

**Pitfall — a naive line-prefix count is a ceiling, not a number.** Counting
lines that `strip().startswith("//")` also matches comment markers inside
template literals, GLSL shader source, JSX strings, and CSS `content`. Always
say "upper bound" when reporting a raw count, and open a handful of real
samples before you characterize anything.

**Pitfall — `git ls-files` paths need existence checks.** Submodules, sparse
checkouts, and case-mismatched paths list files that are not on disk; opening
them unguarded throws `FileNotFoundError` mid-scan. The script guards this.

## Phase 3 — Report once, then honour the decision

Lead with the breakdown table and the surprising number. Explicitly name
what a blanket delete destroys ("this would delete your rate-limit
documentation"). **Then do the non-destructive half immediately:**

**Write the standing rule.** Put it in `AGENTS.md` at the repo root — it
travels with the code and is read by every agent and IDE. Extend an existing
`AGENTS.md`; only create one if absent. Ship it in two parts:

1. the comment rule — no restating the code; comment only the non-obvious
   reason, a workaround, a protocol/format constraint, or a security
   "never do it this way"
2. the repo's own invariants worth protecting, so a future agent doesn't
   "simplify" a security check away

Stage it (`git add`), do not push, and report the absolute path.

Global alternative — `agent.coding_instructions` in `config.yaml` — is
inferior for this purpose: it only applies when the agent is in a code
workspace, and `hermes config set` has misfiled nested keys under a sibling
section. **Re-read the config with `search_files` after every `config set`**;
if the key landed in the wrong section, `hermes config unset <key>` to remove
it. Never edit `config.yaml` with the file tools — they refuse the file by
design.

## Phase 4 — Bulk edits

Only after the user opts in.

**Delegate to parallel subagents, one per disjoint file group.** A mechanical
sweep is the canonical fan-out job: each subagent holds a small, exclusive
file list, edits only those, and runs the project's build itself. See
`references/parallel-sweep.md` for the grouping recipe and the per-group
prompt.

- **Give every subagent the same explicit list of what a comment is NOT.**
  Regex-blind scanners and LLM editors both eat `catch (e)`, template-literal
  contents, and `/// <reference>` directives. The prompt is the only guardrail.
- **Hand each child the file paths as a file to read**, not a glob to
  re-derive — a child that re-globs will silently miss or duplicate files.
- **Verify coverage arithmetically before spawning**: partition the full list,
  confirm `sum(len(group)) == len(all files)` and that no path appears twice.
  A grouping bug that drops 70 of 76 files looks identical to success.
- **Surgical removal, never an LLM rewrite of whole files.** Rewrite-per-file
  reformats code, renames identifiers, and produces diffs nobody can review.
- **One risk tier, one commit.** No opportunistic refactors in the same diff.
- **Large sweep → branch + PR, never direct push to `main`.** The user reviews
  the diff; that review is the entire safety mechanism. Tag the pre-sweep commit
  (`git tag backup-pre-comments <base>`) before committing — the base branch on
  the remote is itself the undo, and an explicit tag survives branch deletion.
- **Parallel children share one working tree.** A child that runs
  `git checkout -- .` to undo its own bad pass silently reverts every sibling's
  finished work. Forbid `checkout`/`restore`/`stash`/`clean` by name in every
  child prompt and verify each group's diff is non-empty; see
  `references/parallel-sweep.md`.
- **Run the project's real build after the sweep** (`npm run build`,
  `tsc -b`, test suite) and report the actual result. A comment deletion that
  eats a `#` inside a shell heredoc or a `//` inside a string breaks the build
  — the count changing is not evidence it worked.

## Pitfalls

- **Answering "is it touching my GitHub yet?" in the abstract.** Users ask this
  repeatedly mid-sweep, and repeat it when the answer was vague. Give the
  concrete state every time — the working directory, the branch name, whether a
  commit exists yet, whether `git push` has run. "All under control" guarantees
  a second question.
- **Handing back work the user has to do by hand.** Copy-paste command lists,
  "run this for each group", or per-file edit instructions are a failed
  delivery, not a shortcut — they asked for the sweep, not a recipe. Delegate
  the mechanical work out and return a result. The only commands worth handing
  over are ones that genuinely require their credentials or their judgement
  (a `git push` on a machine with no token, a merge decision).
- **Asking twice.** Present the buckets once, with counts, and accept the
  answer. A user who said "remove them all" and then watched the agent
  re-argue about the security comments has been told no twice. One pushback
  on a false premise is respect; a second is an obstacle. Once the scope is
  stated, it is their repo and their call.
- **Misreading a vague scope description.** "those grey texts in the code"
  means *all* comments (editor comment colour), not the narration subset.
  Confirm the bucket before a destructive sweep, and when the user answers
  "all", delete all — including banners and documentation they were keeping
  for their own reasons.
- **Writing a comment stripper by hand.** Every hand-rolled version of this
  corrupts code; see `references/parallel-sweep.md` for the four concrete
  failure modes and why the language-native tooling is still not enough on
  its own. Delegate instead of iterating on a regex.
- **Deleting before showing the buckets.** Bulk delete is unrecoverable in the
  user's eyes even when git can revert it; the lost thing is trust, not bytes.
- **Treating `banner` comments as slop.** Section banners in a long file are
  navigation aids and often the author's own convention. Ask.
- **Assuming the user's diagnosis.** "Those comments the AI writes" can point
  at a repo that is mostly hand-authored documentation. Measure, then say so
  plainly when the premise is wrong — the user would rather know.
- **Re-deriving state instead of reading the plan.** Mid-sweep the parent's
  own memory of what is staged goes stale, and so do the children's reports.
  Settle every "is it done / did it land / did I break it" question with
  `git diff --numstat`, `git status`, and a fresh `tsc` — never with recall.
  A count that contradicts the plan is a signal to re-verify, not to explain
  the discrepancy away: an unexpectedly long diff can be a child that staged
  scratch files, and an unexpectedly short one a group that got reverted.
- **Not every comment is slop.** `/// <reference types="vite/client" />` is a
  compiler directive; deleting it breaks `import.meta.env` typing across the
  project with an error message that names a different file entirely. Likewise
  `<!-- -->` inside a template literal that generates an email body or runtime
  HTML is content, not commentary — removing it means rewriting the string and
  changing what a customer receives. Keep both, and say in the report why.
- **Pushing or opening a PR unasked.** Ask before writing to the user's repo
  even when credentials are sitting right there. Once they grant it, finish the
  job (commit, push, open the PR) instead of stopping to ask again.
- **Staging scratch directories.** Children often leave backup folders or
  driver scripts inside the clone. `git add -A` will happily stage them. Use
  explicit pathspec excludes (`git add -A -- . ':!node_modules' ':!dist'`) and
  read `git status --porcelain | grep '^??'` before committing.
- **Committing without verifying the build.** Re-run it after the sweep.

## Recovering from a botched sweep

A corrupted sweep is normal, not a failure state — `git` makes it one command:

```bash
git checkout -- .          # discard working-tree edits, back to HEAD
```

Re-apply from scratch rather than patching the damage in place; layered
half-fixes on a broken file are how `catch (e)` disappears. Re-establish a
clean build baseline (`tsc -b --force`) before the next attempt, so the next
run's errors are attributable.

## Related

- `simplify-code` — comment/slop detection scoped to an uncommitted diff.
- `codebase-inspection` — LOC and code-vs-comment ratios via pygount.
- `scripts/comment_inventory.py` — the bucketing classifier used in Phase 2.
- `references/parallel-sweep.md` — subagent grouping recipe, per-group prompt
  template, the shared-working-tree hazard, the code-identity proof, the
  hand-rolled-stripper failure catalogue, and the branch-vs-`main` delivery
  and verification recipe.