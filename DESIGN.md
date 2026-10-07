# Fatbike Sniper — Design

> Zit. Richt. Schiet. Hoeveel kun jij er neerhalen?

Je zit op een terras in een Hollandse winkelstraat met een ijsje, tot de fatbiker-invasie het plein komt verpesten. Je hebt 1 minuut om zoveel mogelijk fatbikers van hun fiets te schieten.

## Platform & tech
- Browsergame (Three.js / WebGL), gemaakt voor moderne Mac/PC: schaduwen, bloom, lens flares en post-processing mogen
- 3D-modellen worden met Python-scripts in **Blender 5.2** gebouwd, als losse onderdelen (lijf, hoofd, broccolikapsel, trainingspak, fatbike, wapens…), die worden samengevoegd en als `.glb` geëxporteerd
- Stijl: **stylized PBR** (Pixar/Fortnite-achtig), overdreven proporties, veel detail, zomerse terrassfeer
- Taal: Nederlands

## Speler
- Vaste plek op het terras, vrij rondkijken en richten met de muis (FPS-stijl, pointer lock)
- **3 hartjes**: een fatbiker die een mes gooit en raakt kost een hartje. Bij 0 hartjes ben je game over, ook als de minuut nog niet om is
- Je ijsje staat op het tafeltje in beeld en valt om bij een treffer

## Wapens (vrij wisselen met 1–4 / scrollwiel)
| Wapen | Rol | Schot |
|---|---|---|
| Katapult | Oneindige munitie, stil, de basis | Projectiel met boogbaan |
| Shotgun | Brede spreiding, sterk dichtbij, zwak op afstand | Hitscan-hagel |
| Sniper rifle | Rechtermuisknop = scope/zoom, schiet door meerdere fatbikers op een rij | Hitscan |
| Bazooka | Schaarse raketten, lang herladen, grote explosie | Projectiel |

Richten is arcade: directe treffers, behalve bij de katapult en de bazooka.

## Fatbikers
- Stereotiep en komisch: **zwart** broccolikapsel (krullen bovenop, fade aan de zijkanten), zwart trainingspak met witte strepen (geen logo's), mes op zak, soms een zonnebril
- Gedrag: rondjes racen over het plein langs routes, soms op je terras afrijden om een mes te gooien, toeteren en schelden (tekstwolkjes en audio)
- Missen ze hun kans, of mis jij, dan gooien ze een mes. Een mes kun je uit de lucht schieten (trickshot)
- Kleurvariatie: in-game per fatbiker een willekeurige kleur trainingspak (zwart, grijs, navy, wit, bordeaux) en fiets (materialen `TracksuitBlack` / `BikeFrame` / `BikeAccent` worden bij het spawnen gewisseld)
- Maximaal ~15–20 tegelijk; hun aantal neemt toe naarmate de minuut verstrijkt
- Specials:
  - **Duo op één fiets**: de achterste gooit messen; één schot kan beiden raken
  - **Speaker-baas**: boombox op de bagagedrager, heeft meerdere treffers nodig, levert veel punten op
  - **Wheelie-snelheidsduivel**: supersnel op één wiel, moeilijk te raken
- Treffer = slapstick zonder bloed: ze vliegen van hun fiets (ragdoll), het broccolikapsel vliegt eraf, er verschijnen sterretjes, en de bazooka geeft een cartoonexplosie met rondvliegende wielen

## Score
- Basispunten per treffer
- Extra punten voor headshots en trickshots (meerdere tegelijk raken, een mes uit de lucht schieten, doorboring met de sniper)
- Een voetganger of terrasgast raken levert strafpunten op

## Wereld
- Indeling (Blender-meters, +Y = noord, speler kijkt naar het noorden):
  - Plein x ∈ [-22, 22], y ∈ [-14, 16]; speler zit op het terras van Café 't Pleintje aan de zuidkant (~(0, -11.8), ooghoogte 1,15 m)
  - Hoofdstraat west (y -8…-1) en oost (y -8…-1), brede straat noord (x -5…5), steegje noordwest (x -14,5…-12), steegje oost (y 6…8,5)
  - Kerk met toren aan de noordoostkant, fontein in het midden
  - Markers in de GLB: `PlayerEye`, `Spawn_*`
- Verzonnen, generiek Hollands plein met kerktoren, trapgevels, klinkers, terrassen, parasols, bomen en fietsenrekken
- 4–5 toegangswegen: een hoofdstraat links en rechts, twee steegjes en een brede straat recht tegenover je
- Sfeer: warm zomers middaglicht, lange schaduwen, lens flares
- Terrasgasten die juichen als je een fatbiker raakt
- Duiven en meeuwen die opfladderen bij geschiet

## Audio
- Gratis CC0-geluidseffecten (schoten, explosies, fietsbellen, terrasgeroezemoes) en een opzwepend arcadedeuntje

## Flow
- Titelscherm → ronde van 60 s → eindscherm met statistieken (score, treffers, headshots, nauwkeurigheid, beste trickshot, grappige titel)
- Highscores voorlopig lokaal; de code is zo opgezet dat er later een online leaderboard (Supabase/Firebase) achter kan

## Werkwijze — stap voor stap met check-ins
1. Fatbiker + fatbike in Blender → renders ter goedkeuring
2. Plein en terras in Blender → renders
3. Wapens en ijsje in Blender → renders
4. Three.js-game: besturing, wapens, spawning/AI, score, HUD
5. Audio, effecten, titel- en eindscherm, polish
