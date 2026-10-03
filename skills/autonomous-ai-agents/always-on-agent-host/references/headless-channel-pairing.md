# Headless channel pairing (Telegram QR, without the dashboard)

Use this when the user asks to be connected to a phone channel and either
cannot or will not use the dashboard/desktop UI. The pairing flow is a plain
HTTP API; the dashboard is only a viewer for it.

## The rule

**When the user asks for a connection artifact, produce the artifact.** Sending
them to a button in a browser they may not be looking at — especially when
they have already said the button is not appearing — is a dead end. Call the
API, render the QR yourself, give them the deep link, and let them scan.

## Create the pairing THROUGH the dashboard, not upstream

**The pairing must be created by the dashboard process.** A pairing created
directly against the upstream service yields a **masked** token on approval —
`"token":"8832153197:***"` — and the real token is then unobtainable, because
only the dashboard's in-memory pairing record ever holds the unmasked value it
saves to `.env`. A masked token is indistinguishable from a dead end, and the
pairing expires, so the whole attempt has to be redone.

So call the dashboard's own endpoint. It 401s on a bare curl because the SPA
carries a session token the backend injects into the page HTML. **Use that
token; do not disable or weaken the auth gate.** Read it off the served page:

```bash
curl -s http://127.0.0.1:9119/ | grep -oE '__HERMES_(SESSION_TOKEN|AUTH_REQUIRED)__[^<]{0,120}'
# __HERMES_SESSION_TOKEN__="<token>";window.__HERMES_AUTH_REQUIRED__=false;

curl -s -X POST http://127.0.0.1:9119/api/messaging/telegram/onboarding/start \\
  -H "Content-Type: application/json" \\
  -H "X-Session-Token: <token>" -H "Authorization: Bearer <token>" \\
  -d '{"bot_name":"Hermes Agent"}' -w "\\nHTTP %{http_code}\\n"
```

`HTTP 200` plus a `pairing_id` confirms the pairing was born in the right
process. `401` means you forgot the token; re-read it, it is per-server-start.
Note `auth_required` is frequently `false` on a loopback bind — check it rather
than assuming a password prompt.

## Never probe the pairing service for undocumented endpoints

Endpoints like `/ack` exist on the service but are **destructive**. Calling
`/ack` flipped a ready pairing to `claimed`, which retires it permanently: the
real token is unrecoverable and the user's confirmed bot is stranded. There is
no undo, so nothing is backed up before you touch it.

**Rule: treat the documented create + poll pair as the entire API surface.**
`reveal` and `token` return `not_found`; `ack` returns `ok` and destroys the
work. Read the client code (`hermes_cli/web_routers/messaging.py`,
`web_server_messaging.py`) to learn the real contract instead of guessing
endpoint names — the router shows exactly which calls exist and what each
returns.

## Why the dashboard may still need starting

`hermes dashboard` gates its own API behind a session token, but the process is
not running by default and is **not** covered by `hermes gateway install`. If
the port refuses connections, start it first — a refused connection is a dead
surface, not an auth problem.

## The pairing API

Base: `https://setup.hermes-agent.nousresearch.com` (override with
`TELEGRAM_ONBOARDING_URL`).

Create a pairing — returns `pairing_id`, `poll_token`, `deep_link`,
`qr_payload`, `suggested_username`, `expires_at`:

```bash
curl -s -X POST https://setup.hermes-agent.nousresearch.com/v1/telegram/pairings \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "User-Agent: HermesDashboard/<version>" \
  -d '{"bot_name":"Hermes Agent"}'
```

Poll for approval:

```bash
curl -s "https://setup.hermes-agent.nousresearch.com/v1/telegram/pairings/<pairing_id>" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer <poll_token>" \
  --max-time 20
```

**Pitfall: `poll_token` is an `Authorization: Bearer` header, never a query
parameter.** Passing it as `?poll_token=` returns
`{"error":"missing_poll_token"}` with HTTP 401 — which reads like an auth
failure but is really a wrong-placement error. The deep link and the QR
payload are the same string.

Statuses: `waiting` → the user has not yet approved in Telegram. `ready` →
carries `token`, `bot_username`, `owner_user_id`. `expired` / `claimed` →
HTTP 410, generate a fresh pairing.

## The user must approve; you cannot

Opening the deep link is not approval. `NousHostedHermesBot` shows a
confirmation the user must tap. If polling stays `waiting`, that is the
server correctly reporting an unfinished user step — not a bug to debug.
Say which step is outstanding and give the manual fallback below rather than
re-polling indefinitely.

**The fallback that always works and never expires:** @BotFather → `/newbot`
→ pick a name and a username ending in `bot` → it returns a token shaped
`123456789:ABCdef...`. Write `TELEGRAM_BOT_TOKEN` to `.env`, add the user's
numeric ID to `TELEGRAM_ALLOWED_USERS`, restart the gateway. Offer this
whenever a pairing expires or stalls — it depends on no pairing service.

Never ask the user to paste a bot token into chat for the record. If they
offer it, use it in `.env` and move on; the gateway is the only reader.

## Rendering the QR

```bash
python -m pip install qrcode pillow --quiet
python -c "
import qrcode
qrcode.make('<deep_link>').save(r'C:\\path\\telegram_pairing.png')"
```

**Pitfall: `qrcode` alone raises `ModuleNotFoundError: No module named
'PIL'`.** The default backend is a PIL image; installing `qrcode` alone is
not enough. Install `pillow` in the same step.

Deliver as an absolute path and also give the raw deep link — the path is
for a camera, the link is the fallback when the desktop is not in view.

## Verify the QR by decoding it, not by looking at it

**Never use `vision_analyze` to validate a generated QR.** A VLM inspecting
modules reports structural defects that are not there — it called a
correctly-generated code unscannable, citing a malformed corner finder.
Decode it with a real decoder instead:

```bash
python -m pip install opencv-python-headless --quiet
python -c "
import cv2
img = cv2.imread(r'C:\\path\\telegram_pairing.png')
print(cv2.QRCodeDetector().detectAndDecode(img)[0])"
```

A decode that returns the exact deep link is proof. Apply this generally:
prefer a mechanical verifier over a perceptual one whenever a cheap
deterministic check exists.
