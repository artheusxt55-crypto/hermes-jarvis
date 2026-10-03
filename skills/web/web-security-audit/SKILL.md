---
name: web-security-audit
description: "Use when asked to security-scan a deployed site."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [security, headers, tls, cors, audit, web, hardening]
    category: web
---

# Web Security Audit (black-box, deployed site)

Audit a LIVE site the user owns, from the outside. No source access assumed.
Covers transport, response headers, CORS, caching, shipped assets, and what the
page actually loads at runtime.

**This skill is not source review** — that is `requesting-code-review`. **It is not
functional/bug QA** — that is `dogfood`. Use all three for a full pass.

## When to Use

- "Faz uma verificação de segurança no meu site" / "audita meu site"
- "Scan this site" / "is my site secure" / "check my headers"
- Before or after a launch, as a hardening pass
- When a deploy target is named and the user wants the config written for it

**Skip when** the user has the source and wants a code-level review
(`requesting-code-review`) or is hunting functional bugs (`dogfood`).

## Inputs

1. Target URL (default scheme; probe both http and https)
2. Whether the user wants findings only, or also a fix (config file) written
3. Platform, if you will suggest a fix (Vercel/Netlify/Nginx/Cloudflare)

## Workflow

### Step 1 — Transport and certificate

```bash
nslookup <domain> 2>&1 | tail -20
echo | openssl s_client -connect <domain>:443 -servername <domain> 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
curl -sS -I --max-time 20 http://<domain>   # must 301/308 -> https
```

Report the certificate expiry date explicitly. Legacy-protocol checks are in
`references/transport-checks.md` — read it before claiming anything about
TLS 1.0/1.1 support.

### Step 2 — Security headers sweep

Run `scripts/sweep-headers.sh <url>`. It prints explicit `MISSING:` lines for
every absent header, which is the form you want: a header you did not check and
a header that is absent must never look the same in your report.

What each header buys, and what a weak value looks like:
`references/headers-checklist.md`.

### Step 3 — CORS

`Access-Control-Allow-Origin: *` on a **static HTML** response is inert noise.
The same header on an **API route** means any origin can call it. Check both and
say which one you saw. Never report a static-asset CORS wildcard as a finding.

### Step 4 — Shipped assets

```bash
curl -sS -L <url> -o page.html
grep -oE 'src="/assets/[^"]+\.js' page.html      # find the entry bundle
curl -sS <asset-url> -o bundle.js
curl -sS -I <asset-url>                          # cache-control on the asset
# external hosts referenced in the bundle
grep -oE 'https?://[a-zA-Z0-9._-]+\.[a-z]{2,}' bundle.js \
  | sed -E 's#(https?://[^/]+).*#\1#' | sort | uniq -c | sort -rn
for p in 'eval(' 'new Function' 'document.write' 'innerHTML' \
         'dangerouslySetInnerHTML' 'localStorage'; do
  echo "$p : $(grep -oF "$p" bundle.js | wc -l)"
done
grep -oE 'AIza[0-9A-Za-z_-]{35}' bundle.js       # Google/Firebase key
```

Hashed filenames (`index-BOIaKGcY.js`) are immutable by construction — if their
`Cache-Control` is not `max-age=31536000, immutable`, that is a real finding.

Third-party hosts in a bundle are mostly noise: `w3.org` XML namespaces,
`apache.org` license strings and `reactjs.org` error-message URLs are expected.
Say so rather than listing them as suspicious.

### Step 5 — Runtime, in a real browser

Open the site, then read what actually loaded:

```python
new_tab("<url>"); wait_for_load()
# performance.getEntriesByType('resource') -> group by host, count each
# entries whose name startsWith 'http://'  -> mixed content
js("document.cookie"); js("JSON.stringify(Object.keys(localStorage))")
document.querySelectorAll('iframe') -> src list
```

What matters here: a third-party host you did not expect, mixed content,
cookies/localStorage set before any user action, a hidden iframe.

### Step 6 — Route behavior

```bash
curl -sS -o <scratchfile> -w "%{http_code} %{content_type}\n" <url>/nao-existe-xyz-123
```

An SPA catch-all returns `200 text/html` for every path. That is a soft-404
(SEO noise, confusing for broken links) — a Low finding, not a security one.

### Step 7 — Report

Two sections in this order: **what is solid** (so the user knows it was checked,
not skipped), then **what to fix**, ordered by severity, each with the concrete
config that fixes it.

- Never state an untested property as fine. "Firebase rules not tested" is a
  line item, not an omission.
- Distinguish *absent* from *weak*. No CSP and a permissive CSP are different bugs.
- A missing `X-Frame-Options` is only mitigated by `frame-ancestors` inside a
  real CSP — check both before calling clickjacking covered.
- Offer the fix file. If the user says yes, write it (Step 8).

### Step 8 — Fix (only when asked)

The fix lands in the host's config, not the app. Match the user's platform.
`references/header-fixes.md` has copy-ready blocks for Vercel, Netlify, Nginx and
Cloudflare, plus a `security.txt`. `security.txt` must be a real static file — an
SPA fallback serving HTML for that path is not one.

## Pitfalls

- **SPA catch-all makes every status check lie.** `200 OK` on
  `/.well-known/security.txt` may just be `index.html`. Confirm `content_type`
  and eyeball the first bytes before reporting a file as present.
- **`openssl s_client -tls1` does not test TLS 1.0.** The client forces its own
  floor and still prints a modern `Protocol:` line, so a naive grep reports
  "ACCEPTED" for every version. See `references/transport-checks.md`.
- **MSYS/Git-Bash curl aborts with `client returned ERROR on write` when the
  output path is `/dev/null`.** Write to a real file under the scratch dir, or
  use `-w` with `-I`. The error is about the write, not the site — never report
  it as a site problem.
- **Header presence ≠ header configured correctly.** Read the value; a CSP of
  `default-src *` buys far less than it appears to.
- **Do not paste a generic scanner's output.** Name the missing header, why it
  matters here, and the line that fixes it.
