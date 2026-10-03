#!/usr/bin/env bash
# Sweep security headers for a URL and print explicit MISSING lines.
# Usage: bash sweep-headers.sh https://example.com
#
# Explicit MISSING output is the whole point: a header you did not check and a
# header that is genuinely absent must never look the same in your report.
#
# Note: avoid `-o /dev/null` — MSYS/Git-Bash curl can fail there with
# "client returned ERROR on write". Use a real temp file or -w with -I.

set -uo pipefail
URL="${1:?usage: sweep-headers.sh <url>}"
TMP="${TMPDIR:-/tmp}/sweep-headers.$$"

if ! curl -sS -I -L --max-time 25 "$URL" -o "$TMP" 2>/dev/null; then
  # Some servers reject HEAD; retry with a ranged GET.
  curl -sS -L --max-time 25 -r 0-2048 "$URL" -o "$TMP" 2>/dev/null || {
    echo "FATAL: could not fetch headers for $URL" >&2; exit 1; }
fi

hdrval() { grep -i "^$1:" "$TMP" 2>/dev/null | head -1 | tr -d '\r' | cut -d' ' -f2-; }

echo "== $URL =="
echo

echo "-- status / redirect --"
HTTP_URL="${URL/https:\/\//http:\/\/}"
echo "http:// -> $(curl -sS -o "$TMP.r" -w '%{http_code} %{redirect_url}' --max-time 20 "$HTTP_URL" 2>/dev/null)"
rm -f "$TMP.r"
echo

echo "-- security headers --"
FOUND=0
for h in \
  content-security-policy \
  content-security-policy-report-only \
  strict-transport-security \
  x-frame-options \
  x-content-type-options \
  referrer-policy \
  permissions-policy \
  cross-origin-opener-policy \
  cross-origin-embedder-policy \
  cross-origin-resource-policy
do
  v="$(hdrval "$h")"
  if [ -n "$v" ]; then
    echo "  OK       $h: $v"
    FOUND=$((FOUND+1))
  else
    echo "  MISSING  $h"
  fi
done
echo
echo "  present: $FOUND / 10"

echo
echo "-- other --"
for h in server x-powered-by access-control-allow-origin \
         access-control-allow-credentials cache-control
do
  v="$(hdrval "$h")"
  [ -n "$v" ] && echo "  $h: $v"
done
echo

echo "-- certificate --"
host="$(printf '%s' "$URL" | sed -E 's#^https?://([^/:]+).*#\1#')"
if echo | openssl s_client -connect "$host:443" -servername "$host" 2>/dev/null \
   | openssl x509 -noout -subject -issuer -dates 2>/dev/null; then
  echo
  echo "  negotiated:"
  echo | openssl s_client -connect "$host:443" -servername "$host" 2>/dev/null \
    | grep -E "Protocol *:|Cipher *:" | head -2
  echo "  (legacy TLS version support NOT determined by this script)"
else
  echo "  (could not read certificate - openssl unavailable?)" >&2
fi

rm -f "$TMP"
