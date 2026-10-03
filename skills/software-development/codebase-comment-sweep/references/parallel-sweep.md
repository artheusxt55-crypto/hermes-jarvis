# Parallel Comment Sweep

How to fan a repo-wide comment removal out to subagents, and why you should
not try to script it yourself.

## Parallel children share ONE working tree

The single most destructive mistake in this workflow: fanning children out over
a shared clone and letting any of them run a whole-tree restore. A child that
runs `git checkout -- .` to undo its own bad pass **reverts every sibling's
completed work**, because there is one working tree, not one per child. The
damage looks like a child that silently did nothing — its report claims success
while `git diff` against the base shows the file untouched.

Consequences that follow, all of them observed:

- Whole groups revert at once, and the parent's arithmetic coverage check
  still passes (the file list partition was correct; only the edits vanished).
- "Pushing or opening a PR" becomes impossible to verify because the staged
  diff is short by exactly the lost groups.
- A child that restores from its *own* backup is following the prompt
  faithfully — "restore and re-run" is the correct instinct in isolation, and
  catastrophic in a fan-out.

Rules:

1. **Put `git checkout`, `git restore`, `git stash`, `git clean` in the
   forbidden list explicitly in every child prompt**, by name. "Don't run git"
   is too weak — a child restoring its own backup thinks it is being careful.
2. Tell each child other children are working in the same directory and that
   touching anything outside its list destroys their work.
3. Allow read-only git: `git show <ref>:<path>` and `git status` are the child's
   only tools for seeing the original.
4. If a child does need to revert, it reverts **its own files by explicit
   path**, never the tree.
5. **Verify per-group completion by counting comments per group**, not by
   `git diff --shortstat` alone. A short diff is the signature of a reverted
   group; per-group comment counts are the signature of work that survived.
   `git diff main --stat -- <group paths>` must be non-empty for every group.
6. On re-dispatch after a loss, say in the prompt that the work was done before
   and reverted, so children re-verify from the current on-disk state instead of
   assuming their output landed.

## Why delegation beats scripting

A comment sweep is mechanical, high-volume, and low-judgment — exactly the
fan-out shape. Handled serially it is many tool calls and several chances to
corrupt a file; handled by children it is one dispatch plus one verification.

But the naive automation is a trap. Every hand-rolled stripper tried on a
real TypeScript/React repo produced syntax errors. Delegation is not laziness
here; it is the correct tool, because each child can *read the surrounding
code* and see that a `//` sits inside a template literal or that a comment
documents a security rule.

## Why the language-native tooling still is not enough

Do not assume "use the compiler's lexer" solves it. Each of these was tried
and each failed in a distinct way — useful because the failure modes recur
across repos:

| attempt | failure |
|---|---|
| Regex over line prefixes | eats `//` inside strings, GLSL in template literals, `content:` in CSS. Produced `Unterminated template literal`. |
| Char-scan tracking quotes/backticks | consumed `catch (e)` and `video.play().catch(() => {})`; nested template interpolation confused the nesting stack. |
| `ts.createScanner` with `skipTrivia: false` | scanner is regex-blind: after `=` a `/` starts a regex, so it swallowed later `//` comments as regex body. Silently left most of one file untouched. |
| `getLeadingCommentRanges` walking the AST | correct on strings, but misses comments attached before `else if`, and cannot see inside template literals (GLSL `//` needs its own pass). |

The invariant every attempt violated: **a comment is not a line prefix.** It
is a lexical construct whose extent depends on tokenizer state. Only a real
parser gets it right, and even the parser needs extra passes for the two
constructs it deliberately skips (template-literal bodies, `///` directives).

## Grouping recipe

Partition by directory depth so no two children share a file, then verify the
partition is complete before spawning:

```bash
cd <repo>
git ls-files | grep -E '\.(js|ts|tsx|css|html)$' > all.txt
grep -E '^api/'                  all.txt > g_api.txt
grep -E '^src/components/[^/]+$' all.txt > g_comproot.txt
grep -E '^src/components/.+/'    all.txt > g_compsub.txt
grep -E '^src/(pages|hooks|lib|styles)/' all.txt > g_srcdirs.txt
grep -E '^src/[^/]+$'            all.txt > g_srcroot.txt
grep -E '\.html$|^vite\.config\.ts$' all.txt > g_html.txt
cat g_*.txt | sort | uniq | wc -l     # must equal wc -l < all.txt
```

Write each list to its own file. Children read the list; they never re-glob.
Note that grouping by `count("/")` inside a shell loop is a common source of
a silently empty group — verify the count per group, not just the total.

## Per-group prompt template

Give every child the same guardrails. These are the failure modes above,
restated as instructions:

```
Remover TODOS os comentários dos N arquivos em <dir> do repo em <path>.
Os caminhos exatos estão em <list.txt>.

Regras obrigatórias:
1. NÃO pode quebrar código. Preserve o número de linhas de cada arquivo:
   substitua cada bloco de comentário por linhas em branco, para que stack
   traces continuem alinhados.
2. `/// <reference ... />` é DIRETIVA DO COMPILADOR — nunca remover.
3. NÃO toque em nada dentro de template literals (${...}) nem em strings.
   Verifique se o que parece comentário está na verdade dentro de uma string.
4. `* {` em CSS é seletor universal, NÃO é comentário.
5. Não rode git. Não edite arquivos fora da sua lista.

Validação: rode o build/tsc do projeto e reporte a saída.
```

Include the **build command in the child's own prompt**. A child that verifies
its own group catches its own corruption immediately, instead of the parent
discovering four broken files after all six children return.

## What the parent verifies

Never trust a child's self-report that it removed N comments. Verify yourself.

1. **Clean baseline first** — was the repo green before the sweep? Run
   `tsc -b --force` on the untouched tree and record the exit code. Without
   it you cannot tell your errors from pre-existing ones. A child that ran
   `npm install` mid-run will leave `node_modules` inconsistent; if the build
   breaks on a missing transitive dep, re-run the install before blaming the sweep.
2. **Per-group diff non-empty** — see the shared-working-tree section above.
3. **Coverage** — grep for surviving comment patterns across the tree.
   Expect false positives: `* {` (CSS universal selector), `///` lines
   correctly kept, and binary files ("Binary file X matches" — pass
   `--text` off / restrict to text globs).
4. **Diff shape** — `git diff --shortstat`. A pure comment removal with
   comments replaced by blanks shows **equal** insertions and deletions. If
   deletions exceed insertions, whole comment lines were dropped — fine. If
   **insertions exceed deletions, something was added**: usually a stray
   scratch directory the children created inside the repo and staged.
   Check `git status --porcelain | grep '^??'` for untracked junk and
   `git diff --cached --name-only` for anything that is not the sweep.
5. **Code-identity proof** — the check that actually proves nothing was eaten.
   For each changed file, compare `git show <base>:<path>` against the file on
   disk with comments and whitespace stripped; they must be byte-identical.
   Strongest available variant: parse both with the project's own parser
   (`@babel/parser` ships with most React projects, `typescript` is a devDep)
   and compare the serialized AST with `loc`/`start`/`end`/comment fields
   removed — any eaten code changes the AST. For HTML, use an *independent*
   oracle (minify both inline `<script>`/`<style>` blocks and compare) —
   validating with the same tool that stripped the file is circular and
   passes on a defective stripper.
   False-positive to expect: JSX `{/* ... */}` looks like a code divergence
   because the parser counts the braces as tokens. Confirm by grepping the
   diff's added lines for non-whitespace; if empty, the file is clean.
6. **Full build** — `npm run build`, report actual output.

Then commit locally, and see the delivery section below before pushing.

## Delivery

The user will ask, possibly several times, whether the sweep is touching their
real repo yet. Answer concretely every time — name the directory, the branch,
whether a commit exists, and whether a push has run. Vague reassurance ("all
under control") is what makes them ask again.

Local state is the default and stays that way until they grant write access.
`git commit` is local and needs no credentials; `git push` is the first act that
needs a token, so it is the line to draw explicitly.

**Branch vs `main` is their call, not yours.** Present the trade-off once:

- branch + PR — `main` stays untouched, the diff is reviewable in the GitHub UI,
  closing the PR discards everything
- direct to `main` — appears immediately, no review gate

For "land it on `main` but keep the commits", **merge the PR; do not force-push
the branch over `main`.** Merging preserves history and is recoverable with a
revert, while a force-push rewrites it:

```bash
gh pr view <n> --json mergeable,mergeStateStatus --jq '"mergeable=\(.mergeable)"'
gh pr merge <n> --merge --delete-branch=false     # --merge keeps the commits
gh pr view <n> --json state,mergedAt,mergeCommit
gh api repos/<owner>/<repo>/commits/main --jq '"\(.sha[0:7]) \(.commit.message | split("\n")[0])"'
```

Read the diff shape back before merging: `+N / -M` where `N` should be at or
below `M` for a comment removal. Confirm on the **remote**, not just locally —
fetch the merged file through the API and grep it for the pattern you removed:

```bash
gh api repos/<owner>/<repo>/contents/<path> --jq '.content' | base64 -d | grep -cE '^\s*(//|/\*)'
```

Report the surviving exceptions with the reason each was kept. A sweep that
leaves a handful of deliberate keeps reads as thorough; one that silently drops
them reads as sloppy.

## Beware the recovery loop

If a sweep corrupts files, `git checkout -- .` and start over. Do not layer
patches on a damaged file — that is how a `catch` block silently vanishes.
Re-run the baseline build after the reset so the next attempt is attributable.

**In a fan-out, the reset belongs to the parent, not the children.** A child's
own `git checkout` is the failure mode above. If a group is already verified
and staged, prefer re-dispatching only the affected groups over resetting
everything.