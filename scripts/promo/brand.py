"""Shared look for the promo images: the game's HUD palette and fonts (godot/scripts/hud.gd)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONT_TITLE = ROOT / "godot/assets/fonts/Bangers-Regular.ttf"
FONT_UI = ROOT / "godot/assets/fonts/Nunito.ttf"
ICON = ROOT / "godot/icon.png"

INK = (18, 18, 22)
YELLOW = (255, 210, 63)
ORANGE = (255, 138, 31)
RED = (230, 57, 70)
CREAM = (255, 248, 234)
WHITE = (255, 255, 255)


def font(size, ui=False, weight=800):
    f = ImageFont.truetype(str(FONT_UI if ui else FONT_TITLE), size)
    if ui:
        try:
            f.set_variation_by_axes([weight])
        except OSError:
            pass
    return f


def text_layer(parts, size, stroke=0, spacing=0.0):
    """Render [(text, fill), ...] on one line into a transparent image (Bangers, optional ink outline)."""
    f = font(size)
    pad = stroke + size // 4
    widths = [f.getlength(t) for t, _ in parts]
    gap = size * spacing
    w = int(sum(widths) + gap * (len(parts) - 1) + pad * 2)
    asc, desc = f.getmetrics()
    h = asc + desc + pad * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for (t, fill), tw in zip(parts, widths):
        # ink words stay plain: an ink outline would only make them blobby
        d.text((x, pad), t, font=f, fill=fill, stroke_width=0 if fill == INK else stroke, stroke_fill=INK)
        x += tw + gap
    return img.crop(img.getbbox())


def logo(height, tilt=-4):
    """FATBIKE (white) over SNIPER (yellow), ink outline, tilted like the title screen."""
    l1 = text_layer([("FATBIKE", WHITE)], 300, stroke=26)
    l2 = text_layer([("SNIPER", YELLOW)], 375, stroke=30)
    w = max(l1.width, l2.width)
    overlap = 40
    img = Image.new("RGBA", (w, l1.height + l2.height - overlap), (0, 0, 0, 0))
    img.alpha_composite(l1, ((w - l1.width) // 2, 0))
    img.alpha_composite(l2, ((w - l2.width) // 2, l1.height - overlap))
    img = img.rotate(-tilt, resample=Image.BICUBIC, expand=True)
    img = img.crop(img.getbbox())
    return img.resize((int(img.width * height / img.height), height), Image.LANCZOS)


def drop_shadow(img, offset=(0, 10), blur=0, color=INK):
    """img with a solid (or blurred) shadow underneath, in a canvas grown by the offset."""
    ox, oy = offset
    out = Image.new("RGBA", (img.width + abs(ox) + blur * 2, img.height + abs(oy) + blur * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, color + (255,))
    sh.putalpha(img.getchannel("A"))
    if blur:
        sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sh, (blur + max(ox, 0), blur + max(oy, 0)))
    out.alpha_composite(img, (blur + max(-ox, 0), blur + max(-oy, 0)))
    return out


def rounded(img, radius, border=0, border_color=INK):
    """img with rounded corners and an optional ink border drawn inside the edge."""
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius, fill=255)
    if border:
        ImageDraw.Draw(img).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius, outline=border_color, width=border)
    img.putalpha(mask)
    return img


def halftone(size, base=YELLOW, dot=(245, 192, 40), step=28, r=4):
    """A flat comic-book background: base color with a soft dot grid."""
    img = Image.new("RGB", size, base)
    d = ImageDraw.Draw(img)
    for y in range(0, size[1] + step, step):
        for x in range((y // step % 2) * step // 2, size[0] + step, step):
            d.ellipse((x - r, y - r, x + r, y + r), fill=dot)
    return img


def icon(size):
    return rounded(Image.open(ICON).convert("RGBA").resize((size, size), Image.LANCZOS), int(size * 0.22))
