#!/usr/bin/env bash
# Deploy the unified site. certs/latest.json is a repo symlink (./dev
# certify maintains it) which won't resolve on Vercel's static hosting, so
# the deploy ships the dereferenced file and restores the symlink after.
set -euo pipefail
cd "$(dirname "$0")"
LINK=certs/latest.json
TARGET=""
if [ -L "$LINK" ]; then
  TARGET=$(readlink "$LINK")
  cp "$LINK" "$LINK.real" && rm "$LINK" && mv "$LINK.real" "$LINK"
fi
restore() { if [ -n "$TARGET" ]; then rm -f "$LINK"; ln -s "$TARGET" "$LINK"; fi; }
trap restore EXIT
vercel deploy --prod --yes ${VERCEL_TOKEN:+--token "$VERCEL_TOKEN"}
