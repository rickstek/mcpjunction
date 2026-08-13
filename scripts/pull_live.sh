#!/usr/bin/env bash
#
# Pull the currently-live mcpjunction.ai files into public/ so this repo is a
# byte-exact mirror of production before the first automated deploy.
#
# Run this ONCE, from the repo root, before your first `git push`:
#     bash scripts/pull_live.sh
#
# Why: the Worker serves ONLY what's in public/. If a file is live today but
# missing from public/, the first automated deploy deletes it from the site.
#
# robots.txt is deliberately NOT overwritten, and the repo copy is the one
# that must win. Cloudflare's "managed robots.txt" feature is documented as
# prepending to your file, but in practice it REPLACED it — dropping the
# Sitemap: and License: directives entirely. The feature is therefore disabled
# for this zone and public/robots.txt carries the Content Signals policy
# itself. The live copy is fetched to a reference file for comparison only.

set -euo pipefail

BASE="https://mcpjunction.ai"
cd "$(dirname "$0")/.."
mkdir -p public/data

fetch() {
  local path="$1" dest="$2"
  local code
  code=$(curl -sS -w "%{http_code}" -o "$dest.tmp" "$BASE$path" || echo 000)
  if [ "$code" = "200" ] && [ -s "$dest.tmp" ]; then
    mv "$dest.tmp" "$dest"
    printf '  %-28s -> %s\n' "$path" "$dest"
  else
    rm -f "$dest.tmp"
    printf '  %-28s -> SKIPPED (HTTP %s)\n' "$path" "$code"
  fi
}

echo "Mirroring live site into public/ ..."
fetch "/"                        public/index.html
fetch "/licensing.html"          public/licensing.html
fetch "/license.xml"             public/license.xml
fetch "/llms.txt"                public/llms.txt
fetch "/data/mcp_servers.json"   public/data/mcp_servers.json
fetch "/robots.txt"              public/robots.txt.live-reference

echo
echo "Done. Two things to check by hand:"
echo "  1. diff public/robots.txt public/robots.txt.live-reference"
echo "     — the live copy MUST contain the Sitemap: and License: lines."
echo "       If it ends at '# END Cloudflare Managed Content' with nothing"
echo "       after, managed robots.txt is replacing your file: turn it OFF"
echo "       at AI Crawl Control -> robots.txt, then re-run this script."
echo "  2. Confirm public/index.html and public/licensing.html look right;"
echo "     they were captured as served, so any edge injection is baked in."
