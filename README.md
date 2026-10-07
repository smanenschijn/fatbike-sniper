# Fatbike Sniper

Je zit op een terrasje in een Hollandse winkelstraat met een ijsje, tot de fatbiker-invasie het plein komt verpesten. Schiet in één minuut zoveel mogelijk fatbikers van hun fiets.

Een komische 3D first-person browsergame (Three.js). Alle modellen worden met Python-scripts in Blender gebouwd.

## Spelen

Kies op het titelscherm de speeltijd (1, 3 of 5 minuten) en het niveau (makkelijk, normaal of moeilijk). De Hall of Fame houdt per combinatie een eigen top 10 bij.

```bash
npm install
npm run dev
```

Besturing: muis/trackpad richten (op mobiel: slepen om te kijken, tikken om te schieten), klik om te schieten, rechtermuisknop of Shift om in te zoomen (sniper), 1–4 of scrollen om van wapen te wisselen, R om te herladen, Esc voor pauze, B of spatie voor bullet time, M voor muziek aan/uit. Lukt pointer lock niet, dan richt je met de cursor en draait de camera mee als je naar de rand van het scherm gaat.

## Modellen opnieuw bouwen

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_fatbiker.py
/Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_square.py
/Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_weapons.py
npm run assets   # comprimeert assets/models -> public/models (WebP + meshopt, LOD)
```

Zie [DESIGN.md](DESIGN.md) voor het ontwerp.

De soundtrack staat in `public/audio/fatbike-flow.mp3` (gemaakt met Mureka, zie [docs/mureka-soundtrack.md](docs/mureka-soundtrack.md)). Ontbreekt het bestand, dan valt de game terug op een live gesynthetiseerde versie in Web Audio.
