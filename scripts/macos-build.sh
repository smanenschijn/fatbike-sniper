#!/usr/bin/env bash
# Build the universal macOS app (ad-hoc signed) and a zip to share.
set -euo pipefail
cd "$(dirname "$0")/.."
GODOT=/Applications/Godot.app/Contents/MacOS/Godot
scripts/sync-godot-assets.sh >/dev/null
OUT="godot/build/macos"
rm -rf "$OUT/Fatbike Sniper.app" "$OUT/FatbikeSniper-mac.zip" && mkdir -p "$OUT"
"$GODOT" --headless --path godot --export-release "macOS" "build/macos/Fatbike Sniper.app" >/dev/null 2>&1
(cd "$OUT" && ditto -c -k --keepParent "Fatbike Sniper.app" FatbikeSniper-mac.zip)
echo "Klaar: $OUT/Fatbike Sniper.app ($(du -sh "$OUT/Fatbike Sniper.app" | cut -f1)), zip: $(du -h "$OUT/FatbikeSniper-mac.zip" | cut -f1)"
