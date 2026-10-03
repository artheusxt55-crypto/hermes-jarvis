# Where residue hides, by app class

Checklist to walk per class. Order the report by recovered size.

## Model runners (Ollama, LM Studio, llama.cpp)

| Location | Typical content |
|---|---|
| `%USERPROFILE%\.ollama\models\blobs` | the bulk — multi-GB, one blob per layer |
| `%USERPROFILE%\.ollama\models\manifests\registry.ollama.ai/library\<model>` | model names; read this to tell the user WHICH models die |
| `%USERPROFILE%\.ollama\` root | `config.json`, `id_ed25519` + `.pub` (auth keys), `launch/`, `onboarding-*.completed` |
| `%APPDATA%\<app> app.exe\` | tray app WebView2 profile, tens of MB |
| `%LOCALAPPDATA%\Temp\scoped_dir*\*Setup.exe` | installer copies; glob them — they are GB-scale and hard-linked (`nlink 2`), so `du` undercounts the second copy |
| `HKCU\Environment` Path | stale `...\Programs\<app>` entry pointing at a deleted dir |

The binary in `%LOCALAPPDATA%\Programs\` may already be gone while all of the above remains — check that dir early and report it as "uninstalled but residue present", which is the actual state.

## Git clones / dev projects

- The clone directory itself, plus its launcher scripts in `$HOME` (`*start.sh`, `*stop.sh`) and log dirs (`*logs/`).
- If the clone sat under `%TEMP%`, Windows cleanup may have already removed it. **Always `ls -la` before claiming it is there** — an 8 KB empty directory means the files are already gone.
- Package managers keep state outside the project: `uv cache` / `AppData\Local\uv\cache\archive-v0\*` still holds every wheel ever installed into a project venv (spacy models, whisper, onnx runtimes). It is legitimately that project's residue and reclaimable via `uv cache prune`.
- `AppData\Local\Programs\` and `AppData\Local\Temp/` are the two highest-yield roots; `ProgramData/` is the third.

## Python projects

- `.venv\` inside the project, or a tool dir under `AppData\Local\hermes\installs\<hash>\environments\<hash>\venv\`
- `uv tool list` (tools) and `npm ls -g --depth=0` (global packages) — cheap, conclusive, and worth quoting as evidence in the report
- Wheel/sdist caches: `%LOCALAPPDATA%\uv\cache`, `%LOCALAPPDATA%\pip\Cache`, `%USERPROFILE%\.cache\`

## Never touch without asking

- `AppData\Local\hermes\` — `logs\process-results\*.json`, `cache\delegation\live\`, `memories\`, `pastes\`, `hermes-agent\` source. These match any project name you are searching for and are session records, not the app's residue.
- `AppData\Roaming\` browser profiles, `%LOCALAPPDATA%\Packages\*` (Store apps), `$Recycle.Bin\`.