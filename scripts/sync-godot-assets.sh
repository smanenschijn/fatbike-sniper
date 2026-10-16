#!/usr/bin/env bash
# Copy the Blender exports + music into the Godot project (Godot needs them inside res://).
set -euo pipefail
cd "$(dirname "$0")/.."
G=godot/assets
cp assets/models/square.glb assets/models/dunant.glb assets/models/riders.glb assets/models/ijsje.glb assets/models/boss.glb assets/models/route.glb "$G/models/"
cp assets/models/weapons/*.glb "$G/models/weapons/"
cp public/audio/fatbike-flow.mp3 "$G/audio/"
# one shared copy of the brick/paving textures instead of one per model (see scripts/glb_shared_textures.py)
mkdir -p "$G/textures"
cp assets/textures/*.png "$G/textures/"
python3 scripts/glb_shared_textures.py assets/textures "$G/models/square.glb" "$G/models/dunant.glb" "$G/models/route.glb"
echo "synced $(ls $G/models | wc -l | tr -d ' ') models"
