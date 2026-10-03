---
name: windows-app-removal
description: Use when purging an app or project from this Windows PC.
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [windows, cleanup, uninstall, registry, disk-space]
    related_skills: [hermes-agent]
---

# Windows app removal (residue-first)

## When to Use

- "apague o X", "limpa o X", "tira o X do PC" — any removal request for an app, tool, CLI, or cloned project.
- "o X ainda ta no PC?" — an existence/reality check that needs a residue sweep before answering yes or no.
- Reclaiming disk space after an uninstall: quantify and remove what the uninstaller left.
- After deleting something, sweep persistent memory for entries pointing at the now-dead paths.

Do not use for: uninstalling a Hermes profile (see the bundled `hermes-agent` skill), or removing a single stray file with a known path (just delete it).

Removing software here means the *residue*, not the uninstaller. Apps here get uninstalled by their own GUI while leaving GBs behind, and the leftovers are spread over eight distinct layers that a single file-name search never covers.

## Always-on rules

- **Enumerate every layer before touching anything.** Report what exists with sizes, then delete only after the user confirms. The user asks for removals to be *complete*, so an unexamined layer is a failed job.
- **Size before deleting.** `du -sh` on each candidate. A `models/` dir at 18 GB is a decision the user should see, not a surprise in the report.
- **Distinguish app residue from Hermes' own history.** Hermes' `logs/`, `cache/delegation/`, `memories/` and `pastes/` contain the word you are searching for and are *not* the app's residue — deleting them destroys session records and the user's own content. List them separately and ask.
- **Sweep your own memory.** When the removed thing was tracked in persistent memory, delete those entries in the same session — stale paths pointing at deleted directories are worse than no entry, because a future session will report them as facts.
- **Report what was already gone as explicitly as what you deleted.** "O código já tinha sumido, eu só removi a pasta vazia" is the finding; a silent `rm` hides it.
- **Admit an error in the same message you fix it**, with the exact restore command and the reconstructed value. Do not bury it under the success report.

## Procedure

1. **Name-layer scan, scoped.** Use `search_files(pattern="*<name>*", target="files", path="<root>")` per root — `/c/Users`, `/c/ProgramData`, `/c/Program Files`, `/c/Program Files (x86)` — or one `find <roots> -maxdepth 4 -iname "*<name>*"` via terminal when you need many roots in a single pass. A whole-`/c` `find` is slow and its redirected output can vanish from scratch; if a full-disk pass is truly needed, background it with `notify=true`, write to an explicit absolute path, and verify the file exists before reading it.
2. **Content-layer scan** with `search_files(pattern="<name>", output_mode="files_only")`, or ripgrep via terminal (`rg` ships with Hermes under `AppData/Local/hermes/tools/ripgrep-*/rg`) when you must exclude large subtrees: `rg -il --hidden -g '!<hermes-dir>/**' -e '<name>' <root>`. Cap it with `| head -40` and a foreground timeout — a bare scan of a home dir with browser caches will exceed any timeout.
3. **State-layer checks** (one batched call): `tasklist | grep`, `netstat -ano` for known ports, `reg query "HKCU\...\Run"`, `env | grep`, `ls "$APPDATA/.../Startup"`, `schtasks /query /fo csv | grep`, `sc query <name>`.
4. **Report**, grouped: already-clean / residue found (with sizes) / Hermes-internal (ask first).
5. **Delete**, then **verify** with a re-run of the name-layer scan showing empty.

## Pitfalls

- **`reg delete "HKCU\Environment" /v Path /f` deletes the whole Path variable**, not the one offending entry — that is what happened here. To remove one entry: `reg query "HKCU\Environment" /v Path` → filter the entry out → `reg add "HKCU\Environment" /v Path /t REG_EXPAND_SZ /d "<joined-with-semicolons>" /f`. Preserve `REG_EXPAND_SZ`, not `REG_SZ`, or `%USERPROFILE%`-style paths stop expanding.
- **Snapshot `$PATH` and `reg query "HKLM\...\Session Manager\Environment" /v Path` before any registry edit to the user environment.** The live process PATH is your only in-memory record of the effective user Path; the HKLM value supplies the machine half. Tools Hermes injects (`AppData/Local/hermes/...`) reappear every session and do not belong in the registry.
- **Uninstallers leave `scoped_dir*` folders in `%TEMP%`** holding multi-GB `*Setup.exe` copies — routinely the largest single item after a clean uninstall. Glob them, don't hunt for one name.
- **Substring hits in binary caches are noise.** `ollama app.exe`, `Clone Hero/icons.json`, geosite.dat and Adobe `ZxcvbnData` all matched "jarvis"/"ollama" as unrelated words. Confirm a hit is real (check the path and a few content lines) before reporting it as residue.
- **A model/data dir under `%USERPROFILE%` is user data even when the app is gone** — treat it as high-stakes and show the model names from `models/manifests/` in the report so the user can decide.
- **Path quoting:** MSYS bash here needs POSIX paths for builtins (`rm -rf "$HOME/.ollama"`) and native forward-slash or Windows paths for `reg.exe`. Spaces are common (`"ollama app.exe"`), so always quote.

## Related

- `references/residue-locations.md` — per-app-class table of where residue hides (model runners, git clones, node/python projects, installer temp dirs, auth keys).
- Hermes' own directory layout and profile rules live in the bundled `hermes-agent` skill; do not duplicate them here.