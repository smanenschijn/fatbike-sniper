#!/usr/bin/env bash
# Render raw promo material with the game's own autoplay (see _parse_auto_args in godot/scripts/main.gd).
#   scripts/promo/render.sh shots <size> <scene> [out-dir]   screenshot burst: <out>/<size>/<scene>_<t*10>.png
#   scripts/promo/render.sh movie <size> <scene> [out-dir]   30 fps PNG frames + WAV (Movie Maker): <out>/movie-<size>-<scene>/
# Sizes: iphone, ipad and play are the gameplay windows inside the captioned store screenshots
# (2868x1320, 2752x2064, 1920x1080, see compose_screens.py); short is 1080x1920, trailer 1920x1080.
# Afterwards: scripts/promo/compose_screens.py and scripts/promo/make_shorts.py turn these into store/social assets.
set -euo pipefail
cd "$(dirname "$0")/../.."
GODOT=${GODOT:-$( [ -x /Applications/Godot.app/Contents/MacOS/Godot ] && echo /Applications/Godot.app/Contents/MacOS/Godot || echo godot )}
KIND=$1 SIZE=$2 SCENE=$3 OUT=${4:-build/promo-raw}

case $SIZE in
  iphone) RES=2756x1014 ;; ipad) RES=2640x1608 ;; play) RES=1840x860 ;; trailer) RES=1920x1080 ;; short) RES=1080x1920 ;;
  *) echo "unknown size $SIZE"; exit 1 ;;
esac

# what happens in each scene (all with the touch HUD of the phone version and smooth, human-looking aim)
case $SCENE in
  sniper)    ARGS="--autoplay --weapon=3" ; WAIT=36 ;;
  shotgun)   ARGS="--autoplay --weapon=2" ; WAIT=36 ;;
  ijsmachine) ARGS="--autoplay --weapon=5" ; WAIT=36 ;;
  bazooka)   ARGS="--autoplay --weapon=4" ; WAIT=36 ;;
  bullet)    ARGS="--autoplay --weapon=3 --bullet" ; WAIT=30 ;;
  donut)     ARGS="--autoplay --weapon=2 --map=donut" ; WAIT=36 ;;
  boss)      ARGS="--bossfight --autoplay --weapon=3" ; WAIT=32 ;;
  rockets)   ARGS="--bossfight --autoplay --weapon=3 --nolegs" ; WAIT=32 ;;
  route)     ARGS="--phase=route --routeat=30 --autoplay --weapon=2" ; WAIT=24 ;;
  title)     ARGS="" ; WAIT=10 ;;
  *) echo "unknown scene $SCENE"; exit 1 ;;
esac
TOUCH=--touch; [ "$SIZE" = short ] || [ "$SIZE" = trailer ] && TOUCH=""

mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
if [ "$KIND" = shots ]; then
  mkdir -p "$OUT/$SIZE"
  # a screenshot every second from 6 s until the end; low-res 3D in between keeps software rendering fast
  SHOTS=$(seq -s, 6 1 $((WAIT - 1)))
  [ "$SCENE" = bullet ] && SHOTS="$SHOTS,28.2,28.5,28.8,29.1,29.4,29.7"
  "$GODOT" --path godot --resolution $RES --fixed-fps 15 -- --autoshot="$OUT/$SIZE/${SCENE}.png" \
    $ARGS $TOUCH --smooth=5 --god --fast --shots=$SHOTS --wait=$WAIT
else
  D="$OUT/movie-$SIZE-$SCENE"
  rm -rf "$D" && mkdir -p "$D"
  "$GODOT" --path godot --resolution $RES --write-movie "$D/f.png" --fixed-fps 30 -- --autoshot="$D/end.png" \
    $ARGS $TOUCH --smooth=5 --god --wait=$WAIT
fi
