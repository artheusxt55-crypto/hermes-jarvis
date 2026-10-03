# Residue sweep on Windows (git-bash shell)

Command set for decommissioning an installed tool/agent framework. Run each
independently and keep the output — the report is a per-item list, not a
conclusion.

## Finding leftovers

```bash
find "$HOME" -maxdepth 5 -iname "*<name>*" 2>/dev/null
find "$LOCALAPPDATA/Temp" -maxdepth 2 -iname "*<name>*" 2>/dev/null
ls -la "$HOME" | grep -iE "<name>|\.sh$|\.log$"
```

`ls -la` on a `find` hit distinguishes a real payload from an empty husk: a
directory showing only `.` and `..` at a few KB is residue of residue — remove
with `rmdir`, not `rm -rf`, and do not report it as deleted code.

## Live state

```bash
tasklist | grep -iE "<name>|node|vite|uvicorn"
netstat -ano | grep -E ":(8645|8000|5173)"
```

Attribute every surviving PID before assuming it belongs to the project — the
agent's own process usually matches a broad grep.

## Persistence and launch points

```bash
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" | grep -i <name>
reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" | grep -i <name>
env | grep -i <name>
schtasks /query /fo csv | grep -i <name>
find "$APPDATA/Microsoft/Windows/Start Menu" "/c/ProgramData/Microsoft/Windows/Start Menu" -iname "*<name>*"
ls "$APPDATA/Microsoft/Windows/Start Menu/Programs/Startup"
grep -i <name> "$APPDATA/.../Startup/"*.vbs "$APPDATA/.../Startup/"*.lnk
```

`schtasks /query /fo csv` over a busy machine is slow; grep it or bound it with
a timeout rather than letting it run unbounded.

## Package managers

```bash
npm ls -g --depth=0 | grep -i <name>
uv tool list
```

Empty output from `uv tool list` ("No tools installed") is a valid clean result.

## Pitfall: do not grep the whole agent install tree

A recursive `grep -ril "<name>" "$LOCALAPPDATA/hermes"` walks logs, caches, the
agent's own source and its vendored site-packages — it times out at the default
terminal budget and returns nothing. Use the `search_files` tool for that, which
is ripgrep-backed and bounded, and scope it to the subdirectories you actually
care about (`logs/process-results`, `cache/delegation`, `pastes`).

## Removing

```bash
rm -rf "$HOME/<name>-logs"
```

Agent-owned transient state is safe to clear (`logs/process-results/*.json`,
delegation caches): it is output, not the user's work. User-authored material
(pastes, notes) is not — offer it.

## Close the loop in memory

Persistent-memory entries holding the deleted install path, port map and config
location must be removed in the same pass as the deletion, or the next session
starts from a false environment map.