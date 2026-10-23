# Promotiemateriaal

Alles wat je nodig hebt voor de stores, de website en social media. De beelden komen rechtstreeks uit de game: de autoplay van de game speelt een ronde en de scripts in `scripts/promo/` maken er screenshots en video's van.

| Map / bestand | Wat | Formaat |
|---|---|---|
| `store/app-store-iphone-6.9/` | App Store-screenshots iPhone (6,9"-scherm; Apple schaalt ze zelf naar kleinere iPhones) | 2868×1320 JPG |
| `store/app-store-ipad-13/` | App Store-screenshots iPad (13") | 2752×2064 JPG |
| `store/google-play-phone/` | Google Play-screenshots (telefoon, ook bruikbaar voor tablets) | 1920×1080 JPG |
| `store/google-play-feature-graphic.png` | Google Play-banner ("feature graphic") | 1024×500 |
| `store/google-play-icon-512.png` | Google Play-icoon | 512×512 |
| `brand/logo.png` | Logo met transparante achtergrond | PNG |
| `shorts/` | Shorts voor TikTok, Reels en YouTube Shorts, met geluid | 1080×1920 MP4 |
| `social-posts.md` | Teksten en hashtags bij de shorts, plus een postschema | |
| `store-listing.md` | Teksten voor de store-pagina's (naam, ondertitel, beschrijving, zoekwoorden) | |
| `selection.json`, `shorts.json` | Welke frames en fragmenten er gebruikt zijn, met de kopteksten | |

De website staat in `website/` en draait op https://fatbike-sniper.manenschijn.eu/. De Docker-build zet de site op `/` en de browserversie van de game op `/speel/` (zie `Dockerfile`); een push naar `main` deployt automatisch.

## Opnieuw maken

Bijvoorbeeld na een update met nieuwe pleinen of wapens:

```bash
scripts/sync-godot-assets.sh
scripts/promo/render.sh shots iphone sniper     # screenshotreeks: build/promo-raw/iphone/sniper_<t>.png
scripts/promo/render.sh movie short rockets     # 30 fps-opname met geluid: build/promo-raw/movie-short-rockets/
# kies frames en kopteksten in promo/selection.json en fragmenten in promo/shorts.json, en dan:
python3 scripts/promo/compose_screens.py
python3 scripts/promo/make_shorts.py
```

Formaten: `iphone`, `ipad`, `play`, `short`, `trailer`. Scènes: `sniper`, `shotgun`, `ijsmachine`, `bazooka`, `bullet`, `donut`, `boss`, `rockets`, `route`, `title`. Op een Mac met GPU gaat het renderen veel sneller dan in de cloud, waar alles via software-rendering liep.

## Nog in te vullen

- **Contactadressen** in `website/index.html` (pers) en `website/privacy.html`. Daar staan nu `@example.com`-adressen.
- **Store-knoppen:** zodra de apps live staan, vervang je de "Binnenkort"-knoppen door de officiële badges van Apple en Google, met de echte links.
