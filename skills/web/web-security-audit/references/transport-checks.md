# Transport and TLS checks

## Why the naive version lies

`openssl s_client -tls1` (and `-tls1_1`) forces the client to that version floor.
Many OpenSSL builds either fail the handshake outright or silently negotiate
something higher — and still print a modern `Protocol:` line in the handshake
summary. A loop that greps for the literal string `TLSv1` therefore reports
"ACCEPTED" for every version, which is worse than not testing at all.

## What to do instead

Check the **negotiated** protocol and the certificate, not the flag you passed:

```bash
echo | openssl s_client -connect <domain>:443 -servername <domain> 2>/dev/null \
  | grep -E "Protocol *:|Cipher *:" | head -3
```

`Protocol: TLSv1.3` with `TLS_AES_128_GCM_SHA256` is the healthy result. Report
that, and state plainly that legacy-version support was **not determined** rather
than asserting it is disabled.

To actually determine it you need a client that will not negotiate up — a
`tlsscan` / `testssl.sh` run, or an external checker. If you did not run one, the
finding line is "legacy protocol support not verified", never "TLS 1.0 accepted".

## Cipher strength

```bash
echo | openssl s_client -connect <domain>:443 -servername <domain> 2>&1 \
  | grep -A5 "Cipher is"
```

Flag only genuinely weak suites (RC4, DES, export, non-forward-secret RSA key
exchange). `TLS_RSA_*` suites deserve a Low note — no forward secrecy — but
modern clients negotiate ECDHE anyway, so do not inflate it.

## Redirect chain

```bash
curl -sS -I --max-time 20 http://<domain>
```

Expect a 301/308 with a `Location: https://`. A 200 on the http:// origin means
there is no upgrade path — a real finding.

## CAA

```bash
dig +short CAA <domain>      # or: host -t CAA <domain>
```

Windows' bundled `nslookup` often does not know the `CAA` query type and prints
`unknown query type` — that is the resolver, not the domain. Do not report the
absence of a CAA record based on a failed query type.

## Notes on running these from Git-Bash/MSYS

`curl -o /dev/null` can abort with `client returned ERROR on write` in this
environment. Redirect to a real path under the scratch directory instead, or use
`-w` together with `-I`. The failure is about the write target, never about the
remote host.
