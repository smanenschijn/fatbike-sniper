#!/usr/bin/env bash
# Export the Godot project for iOS, build it signed (free personal team) and install it on the connected iPhone.
# Usage: scripts/ios-deploy.sh [device-udid]
set -euo pipefail
cd "$(dirname "$0")/.."
GODOT=/Applications/Godot.app/Contents/MacOS/Godot
TEAM=4JPRJ9VXZ4
DEVICE="${1:-$(xcrun devicectl list devices 2>/dev/null | awk '/physical/ && /iPhone|iPad/ {for (i=1;i<=NF;i++) if ($i ~ /^[0-9A-F]{8}-[0-9A-F]{16}$/) print $i}' | head -1)}"
[ -n "$DEVICE" ] || { echo "Geen iPhone gevonden: sluit hem aan en ontgrendel hem."; exit 1; }

scripts/sync-godot-assets.sh
rm -rf godot/build/ios && mkdir -p godot/build/ios
"$GODOT" --headless --path godot --export-debug "iOS" build/ios/FatbikeSniper.xcodeproj >/dev/null 2>&1
cd godot/build/ios
xcodebuild -project FatbikeSniper.xcodeproj -scheme FatbikeSniper -configuration Debug \
  -destination 'generic/platform=iOS' -derivedDataPath DerivedData \
  -allowProvisioningUpdates -allowProvisioningDeviceRegistration DEVELOPMENT_TEAM=$TEAM build 2>&1 | grep -E "error:|BUILD"
xcrun devicectl device install app --device "$DEVICE" DerivedData/Build/Products/Debug-iphoneos/FatbikeSniper.app | grep -E "App installed|error"
xcrun devicectl device process launch --device "$DEVICE" nl.manenschijn.fatbikesniper >/dev/null 2>&1 && echo "Gestart op de iPhone" || echo "Geïnstalleerd; open de app op de iPhone"
