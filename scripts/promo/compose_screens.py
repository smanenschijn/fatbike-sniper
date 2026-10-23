#!/usr/bin/env python3
"""Turn raw gameplay captures (scripts/promo/render.sh shots ...) into store screenshots and site images.

    python3 scripts/promo/compose_screens.py [raw-dir]     (default: build/promo-raw)

Which frame goes where, and its caption, is in promo/selection.json. Writes:
    promo/store/app-store-iphone-6.9/  2868x1320  (App Store, iPhone 6.9")
    promo/store/app-store-ipad-13/     2752x2064  (App Store, iPad 13")
    promo/store/google-play-phone/     1920x1080  (Google Play, phone and 7"/10" tablet)
    promo/store/google-play-feature-graphic.png  1024x500
    promo/store/google-play-icon-512.png, promo/brand/logo.png
    website/img/shot-*.jpg, website/img/og.jpg
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageEnhance

import brand

ROOT = brand.ROOT
RAW = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/promo-raw"
STORE = ROOT / "promo/store"
SITE_IMG = ROOT / "website/img"
BRAND = ROOT / "promo/brand"

# canvas, height of the caption band, margin around the gameplay (= the raw size in render.sh)
FORMATS = {
    "iphone": {"dir": "app-store-iphone-6.9", "size": (2868, 1320), "band": 250, "pad": 56},
    "ipad": {"dir": "app-store-ipad-13", "size": (2752, 2064), "band": 400, "pad": 56},
    "play": {"dir": "google-play-phone", "size": (1920, 1080), "band": 180, "pad": 40},
}
COLORS = {"ink": brand.INK, "white": brand.WHITE, "red": brand.RED}


def caption(parts, max_w, max_h):
    img = brand.text_layer([(t, COLORS[c]) for t, c in parts], 220, stroke=12, spacing=0.12)
    s = min(max_w / img.width, max_h / img.height)
    return img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)


def store_shot(fmt, raw, parts):
    W, H = fmt["size"]
    band, pad = fmt["band"], fmt["pad"]
    canvas = brand.halftone((W, H), step=max(20, band // 9), r=max(3, band // 60)).convert("RGBA")
    shot = Image.open(raw).convert("RGB")
    want = (W - 2 * pad, H - band - pad)
    if shot.size != want:
        shot = shot.resize(want, Image.LANCZOS)
    framed = brand.drop_shadow(brand.rounded(shot, band // 7, border=max(6, band // 32)), offset=(0, band // 22))
    canvas.alpha_composite(framed, (pad, band))
    ic = brand.icon(int(band * 0.64))
    canvas.alpha_composite(brand.drop_shadow(ic, offset=(0, band // 40)), (W - pad - ic.width, (band - ic.height) // 2))
    cap = caption(parts, W - 3 * pad - ic.width - pad, band * 0.6)
    canvas.alpha_composite(cap, (pad, (band - cap.height) // 2 + band // 40))
    return canvas.convert("RGB")


def hero(raw, size, logo_h):
    """Full-bleed gameplay, darkened towards the left, with the logo: the feature graphic and the share image."""
    W, H = size
    img = Image.open(raw).convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * s) + 1, int(img.height * s) + 1), Image.LANCZOS)
    img = img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width - W) // 2 + W, (img.height - H) // 2 + H))
    img = ImageEnhance.Color(img).enhance(1.15).convert("RGBA")
    shade = Image.linear_gradient("L").rotate(-90).resize((W, H))  # 255 on the left, 0 on the right
    dark = Image.new("RGBA", (W, H), brand.INK + (0,))
    dark.putalpha(shade.point(lambda v: int(v * 0.85)))
    img.alpha_composite(dark)
    lg = brand.drop_shadow(brand.logo(logo_h), offset=(0, logo_h // 40))
    img.alpha_composite(lg, (int(W * 0.05), (H - lg.height) // 2))
    return img.convert("RGB")


def main():
    sel = json.loads((ROOT / "promo/selection.json").read_text())
    for key, fmt in FORMATS.items():
        out = STORE / fmt["dir"]
        out.mkdir(parents=True, exist_ok=True)
        for old in out.glob("*.jpg"):
            old.unlink()
        for i, slot in enumerate(sel["store"], 1):
            raw = RAW / key / slot["frames"][key]
            store_shot(fmt, raw, slot["caption"]).save(out / f"{i:02d}-{slot['name']}.jpg", quality=92, optimize=True)
        print(f"{fmt['dir']}: {len(sel['store'])} screenshots")

    hero(RAW / "play" / sel["feature"], (1024, 500), 330).save(STORE / "google-play-feature-graphic.png", optimize=True)
    hero(RAW / "play" / sel["feature"], (1200, 630), 400).save(SITE_IMG / "og.jpg", quality=88, optimize=True)
    for i, name in enumerate(sel["site"], 1):
        img = Image.open(RAW / "play" / name).convert("RGB")
        img.resize((1600, round(1600 * img.height / img.width)), Image.LANCZOS).save(SITE_IMG / f"shot-{i}.jpg", quality=84, optimize=True)
    print("feature graphic, og.jpg and", len(sel["site"]), "site screenshots")

    BRAND.mkdir(parents=True, exist_ok=True)
    brand.logo(1200).save(BRAND / "logo.png", optimize=True)
    Image.open(brand.ICON).convert("RGB").resize((512, 512), Image.LANCZOS).save(STORE / "google-play-icon-512.png", optimize=True)
    print("logo and 512 px store icon")


if __name__ == "__main__":
    main()
