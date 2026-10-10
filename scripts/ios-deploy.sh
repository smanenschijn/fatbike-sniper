#!/usr/bin/env bash
# Export the Godot project for iOS, build it signed (free personal team) and install it on the connected iPhone.
# Usage: scripts/ios-deploy.sh [device-udid ...]   (default: every connected iPhone/iPad)
set -euo pipefail
cd "$(dirname "$0")/.."
GODOT=/Applications/Godot.app/Contents/MacOS/Godot
TEAM=4JPRJ9VXZ4
if [ $# -gt 0 ]; then DEVICES="$*"; else
  DEVICES=$(xcrun devicectl list devices 2>/dev/null | awk '/physical/ && /iPhone|iPad/ {for (i=1;i<=NF;i++) if ($i ~ /^[0-9A-F]{8}-[0-9A-F]{16}$/) print $i}')
fi
[ -n "$DEVICES" ] || { echo "Geen iPhone/iPad gevonden: sluit hem aan en ontgrendel hem."; exit 1; }

scripts/sync-godot-assets.sh
mkdir -p godot/build && touch godot/build/.gdignore
rm -rf godot/build/ios && mkdir -p godot/build/ios
"$GODOT" --headless --path godot --export-debug "iOS" build/ios/FatbikeSniper.xcodeproj >/dev/null 2>&1
cd godot/build/ios
xcodebuild -project FatbikeSniper.xcodeproj -scheme FatbikeSniper -configuration Debug \
  -destination 'generic/platform=iOS' -derivedDataPath DerivedData \
  -allowProvisioningUpdates -allowProvisioningDeviceRegistration DEVELOPMENT_TEAM=$TEAM build 2>&1 | grep -E "error:|BUILD"
for DEVICE in $DEVICES; do
  echo "== $DEVICE"
  xcrun devicectl device install app --device "$DEVICE" DerivedData/Build/Products/Debug-iphoneos/FatbikeSniper.app | grep -E "App installed|error" || true
  xcrun devicectl device process launch --device "$DEVICE" nl.manenschijn.fatbikesniper >/dev/null 2>&1 && echo "Gestart" || echo "Geïnstalleerd; open de app op het apparaat"
done
