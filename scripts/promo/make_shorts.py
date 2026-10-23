#!/usr/bin/env python3
"""Cut the Movie Maker recordings (scripts/promo/render.sh movie short|trailer ...) into social shorts and site videos.

    python3 scripts/promo/make_shorts.py [raw-dir]     (default: build/promo-raw)

The cuts and on-screen texts are in promo/shorts.json. Writes promo/shorts/*.mp4 (1080x1920, H.264 + AAC,
ready for TikTok, Reels and Shorts) and website/media/ (the hero trailer, the phone video and their posters).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

import brand

ROOT = brand.ROOT
RAW = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/promo-raw"
OUT = ROOT / "promo/shorts"
MEDIA = ROOT / "website/media"
COLORS = {"white": brand.WHITE, "yellow": brand.YELLOW, "ink": brand.INK}


def caption_png(lines, path, width=980):
    """Stacked lines of outlined Bangers text, centered, as a transparent PNG."""
    rows = []
    for text, color in lines:
        img = brand.text_layer([(text, COLORS[color])], 150, stroke=14)
        s = min(1.0, width / img.width)
        rows.append(img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS))
    gap = 6
    canvas = Image.new("RGBA", (max(r.width for r in rows), sum(r.height for r in rows) + gap * (len(rows) - 1)), (0, 0, 0, 0))
    y = 0
    for r in rows:
        canvas.alpha_composite(r, ((canvas.width - r.width) // 2, y))
        y += r.height + gap
    canvas = canvas.rotate(2, resample=Image.BICUBIC, expand=True)
    brand.drop_shadow(canvas, offset=(0, 10)).save(path)


def end_card(path, size, lines):
    """The last seconds: logo, icon and where to get it, on the yellow halftone."""
    W, H = size
    img = brand.halftone(size, step=36, r=5).convert("RGBA")
    lg = brand.drop_shadow(brand.logo(int(min(W * 0.62, H * 0.42))), offset=(0, 14))
    ic = brand.icon(int(min(W, H) * 0.2))
    texts = []
    for text, color, size_px in lines:
        t = brand.text_layer([(text, COLORS[color])], size_px, stroke=0 if color == "ink" else 10)
        s = min(1.0, W * 0.88 / t.width)
        texts.append(t.resize((int(t.width * s), int(t.height * s)), Image.LANCZOS))
    total = ic.height + 40 + lg.height + 40 + sum(t.height + 18 for t in texts)
    y = (H - total) // 2
    img.alpha_composite(brand.drop_shadow(ic, offset=(0, 8)), ((W - ic.width) // 2, y))
    y += ic.height + 40
    img.alpha_composite(lg, ((W - lg.width) // 2, y))
    y += lg.height + 40
    for t in texts:
        img.alpha_composite(t, ((W - t.width) // 2, y))
        y += t.height + 18
    img.convert("RGB").save(path)


def render(job, tmp):
    src = RAW / f"movie-{job['source']}"
    W, H = (1080, 1920) if job["source"].startswith("short") else (1920, 1080)
    start, dur = job["start"], job["duration"]
    inputs = ["-framerate", "30", "-i", str(src / "f%08d.png"), "-i", str(src / "f.wav")]
    chains = [f"[0:v]trim=start={start}:duration={dur},setpts=PTS-STARTPTS,scale={W}:{H},format=yuv420p[v0]"]
    last = "v0"
    for i, cap in enumerate(job.get("captions", [])):
        png = tmp / f"{job['name']}-cap{i}.png"
        caption_png(cap["lines"], png, width=int(W * 0.9))
        n = 2 + i
        t1 = min(cap["to"], dur)
        inputs += ["-loop", "1", "-t", str(dur), "-i", str(png)]
        y = int(H * cap.get("y", 0.16))
        chains.append(f"[{n}:v]format=rgba,fade=in:st={cap['from']}:d=0.15:alpha=1,fade=out:st={t1 - 0.15}:d=0.15:alpha=1[c{i}]")
        chains.append(f"[{last}][c{i}]overlay=(W-w)/2:{y}:enable='between(t,{cap['from']},{t1})'[v{i + 1}]")
        last = f"v{i + 1}"
    if job.get("end_card"):
        png = tmp / f"{job['name']}-end.png"
        end_card(png, (W, H), [tuple(x) for x in job["end_card"]])
        n = 2 + len(job.get("captions", []))
        t0 = dur - job.get("end_secs", 2.8)
        inputs += ["-loop", "1", "-t", str(dur), "-i", str(png)]
        chains.append(f"[{n}:v]format=rgba,fade=in:st={t0}:d=0.25:alpha=1[end]")
        chains.append(f"[{last}][end]overlay=0:0:enable='gte(t,{t0})'[vend]")
        last = "vend"
    if job.get("scale"):   # the site videos are smaller than the recordings
        chains.append(f"[{last}]scale={job['scale']}[vs]")
        last = "vs"
    chains.append(f"[1:a]atrim=start={start}:duration={dur},asetpts=PTS-STARTPTS,afade=in:d=0.3,afade=out:st={dur - 1.2}:d=1.2[a]")
    out = ROOT / job["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chains), "-map", f"[{last}]"]
    cmd += [] if job.get("mute") else ["-map", "[a]", "-c:a", "aac", "-b:a", "160k"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", str(job.get("crf", 20)), "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-r", "30", str(out)]
    subprocess.run(cmd, check=True)
    if job.get("poster"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(job.get("poster_at", 1.0)), "-i", str(out),
                        "-frames:v", "1", "-q:v", "4", str(ROOT / job["poster"])], check=True)
    print(f"{job['out']}  ({out.stat().st_size / 1e6:.1f} MB)")


def main():
    jobs = json.loads((ROOT / "promo/shorts.json").read_text())
    only = set(sys.argv[2:])
    with tempfile.TemporaryDirectory() as t:
        for job in jobs:
            if only and job["name"] not in only:
                continue
            if not (RAW / f"movie-{job['source']}").exists():
                print(f"skip {job['name']}: no recording movie-{job['source']}")
                continue
            render(job, Path(t))


if __name__ == "__main__":
    main()
