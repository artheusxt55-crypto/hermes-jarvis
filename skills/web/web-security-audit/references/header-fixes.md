# Ready-to-paste header fixes

Match the host. These are a strict-but-workable baseline; tighten
`script-src` / `connect-src` against the third-party hosts you actually observed
in Step 5 before shipping.

## Vercel — `vercel.json`

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "Content-Security-Policy", "value": "default-src 'self'; script-src 'self' https://www.googletagmanager.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://*.googleapis.com https://*.firebaseio.com wss://*.firebaseio.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests" },
        { "key": "Strict-Transport-Security", "value": "max-age=63072000; includeSubDomains" },
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" },
        { "key": "Cross-Origin-Opener-Policy", "value": "same-origin" },
        { "key": "X-Frame-Options", "value": "DENY" }
      ]
    },
    {
      "source": "/assets/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
      ]
    }
  ]
}
```

## Netlify — `netlify.toml`

```toml
[[headers]]
  for = "/*"
  [headers.values]
    Content-Security-Policy = "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; upgrade-insecure-requests"
    Strict-Transport-Security = "max-age=63072000; includeSubDomains"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
    Permissions-Policy = "camera=(), microphone=(), geolocation=()"
    X-Frame-Options = "DENY"

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
```

## Nginx

```nginx
add_header Content-Security-Policy "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; upgrade-insecure-requests" always;
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header X-Frame-Options "DENY" always;

location /assets/ {
    add_header Cache-Control "public, max-age=31536000, immutable" always;
}
```

`add_header` inside a `location` block REPLACES all inherited `add_header`
values — that is why the `location /assets/` block above sets only the cache
header and silently drops the security ones. Re-declare the full set inside it,
or serve assets from a separate host/CDN.

## Cloudflare — Transform Rules

Create a response-header-modification rule for all requests, and a second rule
matching `/assets/*` for the long cache TTL. Check whether an existing Edge Cache
rule is already short-circuiting the asset before adding it.

## `security.txt`

Must be a real static file at `/.well-known/security.txt`, not the SPA fallback:

```
Contact: mailto:security@example.com
Expires: 2027-01-01T00:00:00.000Z
Preferred-Languages: pt-BR, en
Canonical: https://<domain>/.well-known/security.txt
Policy: https://<domain>/security-policy
```

Exclude it from the SPA rewrite — Vercel: rewrite/cleanUrls ordering; Netlify: a
real static file in `public/`; Nginx: `location = /.well-known/security.txt`.
Verify afterwards with `curl -sS <url>/.well-known/security.txt | head -3` —
HTML coming back means the rewrite is still swallowing it.
