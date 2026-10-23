#!/usr/bin/env python3
"""Zip the press kit the website links to: logo, icon, screenshots, feature graphic, a short and a fact sheet.

    python3 scripts/promo/presskit.py <out.zip>
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "promo"

FACTS = """Fatbike Sniper - factsheet

Zit. Richt. Schiet. Hoeveel kun jij er neerhalen?

Je zit op een terrasje in een Hollandse winkelstraat met een ijsje, tot de fatbiker-invasie het plein komt
verpesten. Schiet ze van hun fiets met een katapult, shotgun, sniper, bazooka of de IJSMACHINE, een
machinegeweer dat ijsbolletjes vuurt. Slapstick zonder bloed: fatbikers vliegen met een backflip van hun fiets.

- Klassiek: rondes van 1, 3 of 5 minuten, niveaus Makkelijk, Normaal, Moeilijk en Chill
- Campagne: met je ijsje van 't Pleintje door de stad naar het Henri Donutplein
- Twaalf soorten fatbikers, specials (duo, speaker-baas, wheelie-gozer) en eindbaas FATBIKETRON
- Bullet time, headshots, trickshots en een Hall of Fame per modus
- Eigen soundtrack "Fatbike Flow"

Platforms: web (gratis), iOS en Android (binnenkort)
Taal: Nederlands
Engine: Godot 4; alle 3D-modellen zijn met Python-scripts in Blender gebouwd
Gemaakt in Nederland door een solo-ontwikkelaar
"""


def main():
    out = Path(sys.argv[1])
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("fatbike-sniper/factsheet.txt", FACTS)
        z.write(ROOT / "godot/icon.png", "fatbike-sniper/icon-1024.png")
        for f in [P / "brand/logo.png", P / "store/google-play-feature-graphic.png", *sorted((P / "store/google-play-phone").glob("*.jpg")),
                  *sorted((P / "shorts").glob("*.mp4"))[:1]]:
            if f.exists():
                sub = "screenshots/" if f.suffix == ".jpg" else "video/" if f.suffix == ".mp4" else ""
                z.write(f, f"fatbike-sniper/{sub}{f.name}")
    print(f"{out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
