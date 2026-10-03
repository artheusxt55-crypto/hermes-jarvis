# Power & Wake Feasibility

Depth for the cold-power-on question in `SKILL.md`. Read when a user wants
to boot a machine that is off, or when a host stops responding and sleep /
hibernate is suspected.

## Why the agent cannot wake its own machine

The agent is a process on the machine. If the machine is powered off there
is no process, so nothing can receive the "wake up" message or emit a magic
packet. Any cold-boot scheme must originate outside the machine:

- the phone (an app sending a WOL packet / a vendor app for a smart plug)
- the router (WOL relay, port-forward to a relay daemon)
- the power itself (a smart plug restoring AC)

This is why "just send it a magic packet from Hermes" can never work, and
why the packaging of a WOL feature inside the agent is beside the point.

## Windows probes (full set)

```bash
# Chassis / form factor — a laptop has a battery, and often only Wi-Fi
powershell.exe -NoProfile -Command "Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory | Format-List"
powershell.exe -NoProfile -Command "(Get-CimInstance Win32_Battery | Measure-Object).Count"

# Every adapter, including hidden and virtual — looking for real Ethernet
powershell.exe -NoProfile -Command "Get-NetAdapter -IncludeHidden | Select-Object Name,InterfaceDescription,Status,MediaType | Format-Table -AutoSize"

# Who is allowed to wake the system
powercfg /devicequery wake_armed
powercfg /lastwake

# Per-adapter WOL capability
powershell.exe -NoProfile -Command "foreach(\$a in (Get-NetAdapter)){ \$p = Get-NetAdapterPowerManagement -Name \$a.Name -ErrorAction SilentlyContinue; if(\$p){ Write-Output \"\$(\$a.Name): WOL=\$(\$p.WakeOnMagicPacket)\" } else { Write-Output \"\$(\$a.Name): power mgmt not available\" } }"

# Driver-level WOL / PME properties, when the above is ambiguous
powershell.exe -NoProfile -Command "Get-NetAdapterAdvancedProperty -Name 'Wi-Fi' -ErrorAction SilentlyContinue | Where-Object {\$_.DisplayName -match 'Wake|Magic|WOL|PME|Shutdown'} | Select-Object DisplayName,DisplayValue | Format-Table -AutoSize"
```

### The MSYS `$`-escaping trap

Under the Git-Bash/MSYS shell, `$` inside a
`powershell.exe -NoProfile -Command "..."` string is consumed by bash first.
Escape it as `\$`, or the variable expands to empty and the probe returns
nothing — which reads as "this adapter has no support" rather than "my
quoting was wrong." A blank result from a `foreach` loop is a quoting bug
until proven otherwise.

## Interpreting `wake_armed`

This is the decisive output. A healthy desktop that can be woken remotely
lists its network adapter. A list containing only HID devices (keyboard,
mouse) means **no network adapter is armed**, and no WOL packet will ever be
honoured. That single line is the whole verdict — do not keep probing
adapters afterwards.

## Sleep / hibernate, the always-on prerequisite

Independent timers. Both must be zeroed, on AC and on battery.

```bash
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change standby-timeout-dc 0
powercfg /change hibernate-timeout-dc 0

# verify: both must print 0x00000000
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE
powercfg /query SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLE
```

`0` means never. Symptom to recognise: a host reachable for a few hours
then silently unreachable, with the gateway "still installed" — that is
hibernation firing, not a config regression.

Also worth checking when a host sleeps anyway: lid-close action, and any
vendor "battery saver" / "intelligent standby" that can override the timer.

```bash
# Lid close action
powercfg /query SCHEME_CURRENT SUB_BUTTONS LIDACTION
```

## macOS / Linux equivalents

```bash
# macOS: prevent sleep on AC (0 = never), and list what can wake it
pmset -g custom
pmset -g womp

# Linux: never suspend, and what is armed to wake
sudo systemctl mask sleep.target suspend.target hibernate.target
cat /proc/acpi/wakeup
```

On macOS, `pmset` sleep=0 still allows the display to sleep; use
`sudo pmset -a displaysleep 0` if the host should look awake too. `womp`
(wake on network access) must be 1 for a wired magic packet to work.

## What to tell the user

Report the probe result, not a capability guess. If a NIC is armed, give
the MAC and the subnet; if not, say plainly that the hardware cannot do it
and rank the remedies by cost. Include the free option (never shut down)
first — it covers the common case and requires nothing.
