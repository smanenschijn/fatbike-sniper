# Fatbike Sniper (Godot 4)

Native port of the web game (tag `v1.0-web`). Same Blender models, same gameplay.

```bash
scripts/sync-godot-assets.sh   # copy Blender exports + music into godot/assets
python3 scripts/gen_sfx.py     # render the synth sound effects to WAV
/Applications/Godot.app/Contents/MacOS/Godot --path godot            # play on the Mac
/Applications/Godot.app/Contents/MacOS/Godot --headless --path godot --export-debug "Android" build/android/fatbike-sniper.apk
```

Automated screenshot / smoke test: `Godot --path godot -- --autoshot=/tmp/shot.png [--autoplay] [--wait=8]`

Op je iPhone zetten (gratis Apple ID, verloopt na 7 dagen): `scripts/ios-deploy.sh`
Mac-app bouwen (universeel, met zip): `scripts/macos-build.sh`
