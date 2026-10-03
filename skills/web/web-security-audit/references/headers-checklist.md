# Security header checklist

The sweep order. Each entry: what it buys, and what a weak value looks like.

## Transport

| Header | Buys | Notes |
|---|---|---|
| `Strict-Transport-Security` | Blocks SSL-strip downgrade | A `max-age` below ~31536000 is weak. Only meaningful once you are confident you are HTTPS-only everywhere including subdomains — `includeSubDomains` is an irreversible commitment. |

## Script execution

| Header | Buys | Notes |
|---|---|---|
| `Content-Security-Policy` | The single highest-value header. Restricts where scripts/styles/frames may load from. | A CSP that omits `script-src`, or sets `unsafe-inline` / `*`, buys far less than it appears to. `frame-ancestors` inside CSP supersedes `X-Frame-Options`. |
| `Content-Security-Policy-Report-Only` | Deploy a policy without breaking prod. | Ship alongside the enforcing header during rollout, then remove. |

## Framing

| Header | Buys | Notes |
|---|---|---|
| `X-Frame-Options` | Clickjacking defense. | `DENY` or `SAMEORIGIN`. Modern CSP `frame-ancestors` is preferred; treat this header as the fallback for old browsers, not the primary. |

## Content type & sniffing

| Header | Buys | Notes |
|---|---|---|
| `X-Content-Type-Options: nosniff` | Stops the browser re-interpreting a response as a different type. | Always `nosniff`. One line, no downside. |

## Referrer & data leakage

| Header | Buys | Notes |
|---|---|---|
| `Referrer-Policy` | Stops full URLs (with query strings) leaking to third parties. | `strict-origin-when-cross-origin` is the sane modern default. |
| `Permissions-Policy` | Disables camera/mic/geolocation/USB you do not use. | Only worth listing features you actually serve. |

## Cross-origin isolation

| Header | Buys | Notes |
|---|---|---|
| `Cross-Origin-Opener-Policy` | Isolates the browsing context group. | `same-origin` is the common choice. |
| `Cross-Origin-Embedder-Policy` | Requires cross-origin resources to opt in via CORP. | `require-corp` breaks any third-party resource lacking CORP — audit embed/image hosts before enabling. |
| `Cross-Origin-Resource-Policy` | Blocks cross-origin reads of your assets. | `same-origin` or `same-site`. |

## Not in the list, still worth checking

- **`Server` / `X-Powered-By`** — version disclosure. Low severity; usually not
  worth reporting on managed hosts where you cannot remove it.
- **`Access-Control-Allow-Origin`** — see the CORS step; severity depends on
  whether the response is static content or an API.
- **`Cache-Control` on hashed assets** — a correctness/perf finding, not
  security, but report it alongside the rest.
