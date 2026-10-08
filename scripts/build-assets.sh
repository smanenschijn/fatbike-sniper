#!/usr/bin/env bash
# Compress the Blender exports (assets/models) into web-ready GLBs (public/models):
# textures -> WebP, geometry -> meshopt. Also builds a low-poly LOD of the fatbiker.
set -euo pipefail
cd "$(dirname "$0")/.."
GT=node_modules/.bin/gltf-transform
OUT=public/models
TMP=$(mktemp -d)
mkdir -p "$OUT/weapons"

compress() {  # in out
  $GT webp "$1" "$TMP/a.glb" --quality 85 >/dev/null
  $GT meshopt "$TMP/a.glb" "$2" >/dev/null
  echo "  $(basename "$2"): $(du -h "$2" | cut -f1)"
}

echo "Compressing models..."
compress assets/models/square.glb "$OUT/square.glb"
compress assets/models/riders.glb "$OUT/riders.glb"
compress assets/models/ijsje.glb "$OUT/ijsje.glb"
for w in assets/models/weapons/*.glb; do compress "$w" "$OUT/weapons/$(basename "$w")"; done

echo "Riders LOD..."
$GT weld assets/models/riders.glb "$TMP/w.glb" >/dev/null
$GT simplify "$TMP/w.glb" "$TMP/s.glb" --ratio 0.12 --error 0.005 >/dev/null
compress "$TMP/s.glb" "$OUT/riders_lod.glb"
rm -f "$OUT/fatbiker.glb" "$OUT/fatbiker_lod.glb"
rm -rf "$TMP"
