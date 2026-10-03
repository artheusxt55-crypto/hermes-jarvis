---
name: always-on-agent-host
description: "Make a machine a persistent, phone-reachable agent host."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [hermes, gateway, always-on, power, wake-on-lan, messaging, telegram, remote-access]
    category: autonomous-ai-agents
    related_skills: [hermes-agent]
---

# Always-On Agent Host

Turning a machine into a host that stays reachable — from a phone, from
another room, for days — and being honest about which of those things the
hardware can actually do.

## When to Use

Trigger this skill when the user wants the agent reachable off the local
machine or kept alive, in any of these shapes:

- "acesso pelo celular", "access from my phone", "talk to you from Telegram"
- keep the machine awake / never sleep / stay online
- "ligar o computador pela remotely quando estiver desligado", wake a
  powered-off machine, Wake-on-LAN, smart plug
- a host that stopped responding and might be asleep or hibernated
- any remote-access request where the machine's power state is a dependency

Not for building the agent itself, channel feature questions with a
reachable host, or general Windows administration.

Three independent things get conflated in these requests. Separate them
before promising anything:

1. **Reachability** — can a message reach the agent while it runs?
2. **Liveness** — does the machine stay awake and online long enough to
   answer at all?
3. **Power-on from cold** — can a dead machine be booted remotely?

(1) and (2) are software and always solvable. (3) is hardware, often not
solvable, and must be verified before it is claimed.

## Order of operations

**Step 1 — Kill the sleep and hibernate timers FIRST.** This is the silent
killer and the most commonly missed step. A host that suspends or hibernates
loses the gateway, and the messaging channel looks configured but is dead.
Do this before touching any channel config.

```bash
# Windows (both AC and battery)
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change standby-timeout-dc 0
powercfg /change hibernate-timeout-dc 0
```

Verify by re-querying — the index must read `0x00000000`:

```bash
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE
powercfg /query SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLE
```

**Pitfall: setting sleep to 0 is not enough.** Hibernation has its own
independent timeout and is usually left at a few hours. A machine that
"never sleeps" can still hibernate at 3h and take the gateway with it. Zero
both.

**Pitfall: zeroing timers is a real power cost.** On a laptop it means the
battery drains while idle. Say so out loud and let the user choose between
always-on and battery life rather than silently picking for them.

**Step 2 — Confirm the gateway is installed to survive reboot.** A
host that is reachable right now but not after a reboot is not a host.

```bash
hermes gateway status
```

`Windows login item installed` / a systemd unit / a launchd plist is the
thing to look for. If absent: `hermes gateway install`.

**Step 3 — Check whether a channel is actually connected before claiming
phone access exists.** An installed gateway with zero platforms configured
is a host nobody can talk to.

```bash
cat "$HERMES_HOME/channel_directory.json"   # "platforms": {} means none
```

**Step 4 — Wire the messaging channel.** Prefer the QR / guided path over
hand-editing env files: the wizard writes the token AND the allowlist AND
restarts the gateway, which is three easy things to get half-right by hand.

**But do not route the user to a UI to get it.** If they asked you to connect
a channel, connect it: start the dashboard if it is not running, read the
session token it injects, call the pairing API yourself, render the QR, hand
over the deep link. Pointing a user at a dashboard button they have already
reported as missing is not a step, it is a stall.

**The pairing must be created through the dashboard process.** Created directly
against the upstream service, an approved pairing returns a *masked* token
(`"token":"8832153197:***"`) that can never be saved — only the dashboard's
in-memory record holds the real one. **Never call undocumented endpoints on the
pairing service to work around this:** `/ack` exists and silently retires a
ready pairing as `claimed`, stranding the user's confirmed bot with no undo.
Full recipe, the bearer-header `poll_token` placement, the session-token
extraction, QR rendering deps, and the @BotFather fallback that never expires:
`references/headless-channel-pairing.md`.

**Step 5 — Only then answer the power-on question**, using the feasibility
check below. Do not lead with it; do not promise it.

## Pitfalls

- **Produce the artifact; do not delegate the click.** If the user asks to be
  connected, generate the credential or QR yourself. Repeatedly telling a
  user to find a button — especially after they say it is not there — spends
  a turn and teaches nothing. Verify the surface exists, then take the action
  yourself, and hand over a concrete deliverable (absolute path, link,
  command) instead of a location to go look in.

- **Never report success you have not verified end to end.** A `waiting` poll,
  a masked token, or a generated-but-unapplied artifact is *not* a connected
  channel. State the exact outstanding step and what remains unverified, and
  correct yourself plainly the moment a later check contradicts an earlier
  "that worked". Overclaiming here costs the user a whole manual redo, because
  they stop looking for the missing piece.

- **Prefer a mechanical verifier over a perceptual one.** A VLM asked whether
  a generated QR is scannable will confidently invent a structural defect and
  call a valid code broken. Decode with a real decoder and compare against
  the expected string. The same rule holds for any artifact a cheap
  deterministic check can validate.

- **A missing UI button usually means the UI is not running, not that
  config is broken.** The dashboard and the gateway are separate processes.
  Before debugging any dashboard/desktop surface, confirm the process
  exists and the port answers.

  ```bash
  hermes dashboard --port 9119          # background it
  powershell.exe -NoProfile -Command "Get-NetTCPConnection -State Listen | Where-Object {\$_.LocalPort -eq 9119}"
  curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:9119/
  ```

  An HTTP 200 with the dashboard title means the surface is fine and the
  problem is inside it; connection refused means it simply was never started.
  Note `hermes dashboard` is NOT covered by `hermes gateway install` — one
  does not start the other.

- **Never hand-edit `config.yaml`** for the user — use `hermes config set`.
  A stray indent corrupts the file and takes the live gateway down. Secrets
  go in `.env`, settings go in `config.yaml`; do not mix.

- **Do not recommend hardware the user may not own.** If the only working
  approach needs a smart plug, an Ethernet adapter, or a vPro-capable
  machine, say that the hardware is required and offer the zero-cost path
  first. Recommending a purchase as if it were the only move wastes the
  user's time when they may not have the device — and the free alternative
  (never sleep) usually covers the real use case anyway.

- **"With the PC off, the agent is also off."** State this plainly when a
  user asks to control a powered-down machine. No agent runs to receive the
  message or emit the wake signal, so the wake must originate outside the
  machine (the phone, the router, a smart plug). This reframing is usually
  the most useful thing in the whole answer.

## Feasibility: can this box be booted remotely?

Never assume. Probe, then report what the probe found. On Windows:

```bash
# 1. Which NICs exist, really (include hidden/virtual)? Is there Ethernet?
powershell.exe -NoProfile -Command "Get-NetAdapter -IncludeHidden | Select-Object Name,InterfaceDescription,Status,MediaType | Format-Table -AutoSize"

# 2. Is any NIC armed to wake the system? (expect keyboard/mouse only)
powercfg /devicequery wake_armed

# 3. Does the adapter expose Wake-on-Magic-Packet / PME?
powershell.exe -NoProfile -Command "foreach(\$a in (Get-NetAdapter)){ \$p = Get-NetAdapterPowerManagement -Name \$a.Name -ErrorAction SilentlyContinue; if(\$p){ Write-Output \"\$(\$a.Name): WOL=\$(\$p.WakeOnMagicPacket)\" } else { Write-Output \"\$(\$a.Name): power mgmt not available\" } }"
```

Reading the result:

| Finding | Verdict |
|---|---|
| An Ethernet NIC armed in `wake_armed` | Wake-on-LAN viable — route the magic packet from the phone/VPN to that MAC |
| `wake_armed` lists only keyboard/mouse | **No NIC armed — not viable.** Usually a Wi-Fi-only machine |
| `power mgmt not available` for the only adapter | Adapter has no WOL support at all |
| Intel vPro/AMT machine | Out-of-band power-on works, independent of the OS |

Wake-on-LAN needs a wired NIC with PME armed. Wake-over-Wi-Fi (WoWLAN) is
rarely supported by consumer adapters. If no NIC is armed, the honest answer
is: this cannot be booted remotely, and here is what would make it possible.

Rank the remedies by cost and say which one actually fixes it:

1. **Free — never shut down, only suspend.** Solves the real use case
   without hardware. Pair it with step 1.
2. **Cheap — a Wi-Fi relay/smart plug.** Cutting and restoring power boots
   the machine, provided it is set to power on when AC returns (default on
   most laptops). Verify that setting exists before recommending.
3. **Expensive — Intel AMT/vPro.** Out-of-band power-on independent of the
   OS. Corporate hardware only; check the model before suggesting it.

Full probe output, the MSYS `$`-escaping trap, and macOS/Linux equivalents:
`references/power-and-wake-feasibility.md`.
