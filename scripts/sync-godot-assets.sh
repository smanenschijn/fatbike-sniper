#!/usr/bin/env bash
# Copy the Blender exports + music into the Godot project (Godot needs them inside res://).
set -euo pipefail
cd "$(dirname "$0")/.."
G=godot/assets
cp assets/models/square.glb assets/models/riders.glb assets/models/ijsje.glb "$G/models/"
cp assets/models/weapons/*.glb "$G/models/weapons/"
cp public/audio/fatbike-flow.mp3 "$G/audio/"
echo "synced $(ls $G/models | wc -l | tr -d ' ') models"
