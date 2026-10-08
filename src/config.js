import * as THREE from 'three';

/** Blender (x, y, z) -> three.js (x, z, -y). The glTF exporter applies the same conversion. */
export const B = (x, y, z = 0) => new THREE.Vector3(x, z, -y);

/** Phones/tablets: touch controls + a lighter graphics profile. */
export const IS_TOUCH = typeof window !== 'undefined'
  && (new URLSearchParams(location.search).has('touch') || matchMedia('(pointer: coarse)').matches
    || (navigator.maxTouchPoints > 0 && !matchMedia('(pointer: fine)').matches));

export const ROUND_TIME = 60; // default
export const ROUND_OPTIONS = [60, 180, 300];

/** Difficulty presets: multipliers on the base curve + player/knife tuning. */
export const LEVELS = {
  easy: { label: 'Makkelijk', spawn: 1.35, alive: 0.7, attack: 0.5, speed: 0.88, accuracy: 0.35, retaliate: 0.4, hearts: 5, btFill: 1.35, score: 0.8 },
  normal: { label: 'Normaal', spawn: 1, alive: 1, attack: 1, speed: 1, accuracy: 0.6, retaliate: 0.7, hearts: 3, btFill: 1, score: 1 },
  hard: { label: 'Moeilijk', spawn: 0.72, alive: 1.3, attack: 1.5, speed: 1.15, accuracy: 0.8, retaliate: 0.9, hearts: 3, btFill: 0.8, score: 1.3 },
};

export const BULLET_TIME = {
  duration: 4.5,      // real seconds
  scale: 0.2,         // world speed while active
  fill: { kill: 0.2, head: 0.12, knife: 0.2 },
  bonus: 1.5,         // score multiplier for slow-mo kills
};
export const HEARTS = 3;
export const GRAVITY = 9.8;

export const FOV = 62;
export const ZOOM_FOV = 16;
export const MOUSE_SENS = 0.0022;
export const YAW_LIMIT = THREE.MathUtils.degToRad(115);
export const PITCH_MIN = THREE.MathUtils.degToRad(-40);
export const PITCH_MAX = THREE.MathUtils.degToRad(55);

/** Where riders come from / leave to (street ends) and where they join the square (street mouths). */
export const ENTRIES = [
  { name: 'west', spawn: B(-56, -4.5), mouth: B(-21, -4.5), weight: 3 },
  { name: 'east', spawn: B(56, -4.5), mouth: B(21, -4.5), weight: 3 },
  { name: 'north', spawn: B(0, 52), mouth: B(0, 15), weight: 3 },
  { name: 'alleyNW', spawn: B(-13.25, 38), mouth: B(-13.25, 15), weight: 1.5 },
  { name: 'alleyE', spawn: B(42, 7.25), mouth: B(21, 7.25), weight: 1.5 },
];

export const FOUNTAIN = B(0, 3);
export const RING_RADIUS = 9.5;
export const ATTACK_Z = B(0, -8.2).z; // how close riders dare to come to the terrace

export const SCORE = {
  kill: 100,
  headshot: 50,
  multi: 100,
  knife: 150,
  boss: 500,
  wheelieMul: 2,
};

/** Difficulty ramps over the round (t in 0..1) and is scaled by the chosen level. */
export const difficulty = (t, level = LEVELS.normal) => ({
  spawnInterval: THREE.MathUtils.lerp(1.9, 0.5, t) * level.spawn,
  maxAlive: Math.max(3, Math.round(THREE.MathUtils.lerp(5, 18, t) * level.alive * (IS_TOUCH ? 0.75 : 1))),
  attackChance: Math.min(0.85, THREE.MathUtils.lerp(0.12, 0.45, t) * level.attack),
  speedMul: THREE.MathUtils.lerp(1.0, 1.35, t) * level.speed,
});

/**
 * How intense the round is at `elapsed` seconds: ramps up over the first ~90 s, then (in longer rounds)
 * breathes in waves so 3–5 minute games have calmer moments between the rushes.
 */
export function roundIntensity(elapsed, roundTime) {
  const ramp = Math.min(1, elapsed / Math.min(roundTime, 90));
  if (roundTime <= 60 || elapsed < 90) return ramp;
  const wave = 0.5 + 0.5 * Math.sin(((elapsed - 90) / 50) * Math.PI * 2 - Math.PI / 2);
  return 0.7 + 0.3 * (1 - wave) + Math.min(0.15, (elapsed - 90) / 1200); // dips to ~0.7, peaks at 1
}

// ---- the crowd: colours are rolled per rider, independent of shape, so everyone gets mixed
export const PALETTES = {
  skin: ['#f6d7c3', '#efc3a4', '#e6b18f', '#d9a07a', '#c98d62', '#b77a52', '#a06640', '#8a5536', '#6f4330', '#5a3526', '#46291d'],
  hair: {
    young: ['#1d1714', '#1d1714', '#3b2a20', '#5a3d2b', '#7a5236', '#a5774c', '#d8b276', '#e8d3a0', '#9c3b22', '#c25a2c', '#ff6fb5', '#5ec8ff'],
    grey: ['#d8d8d8', '#e8e8e8', '#bdbdbd', '#f2efe8', '#a8a8a8'],
  },
  top: ['#1a1a20', '#e9e9ec', '#c8302a', '#2b5a8c', '#2d6a45', '#f4cf3a', '#f08a24', '#ff6fb5', '#7a5cff', '#5d6066', '#6b1d2a', '#35c2c2'],
  cardigan: ['#d98aa8', '#8aa8d9', '#c9b48a', '#9c6b8a', '#7a9a6a'],
  bottom: {
    trackpants: ['#1a1a20', '#5d6066', '#1e2a4a', '#6b1d2a', '#e9e9ec', '#2d6a45'],
    jeans: ['#2b4a7a', '#3b5f94', '#1f2f4f', '#6f8fb8', '#2a2a2e'],
    leggings: ['#1a1a20', '#2a2a3a', '#5d6066', '#6b1d2a', '#2b4a7a'],
    shorts: ['#c9b48a', '#2b4a7a', '#1a1a20', '#6b7b4a', '#d6d0c4', '#c8302a', '#3b5f94'],
    skirt: ['#6b1d2a', '#2b4a7a', '#4a5a3a', '#5a3a5a', '#7a6a5a'],
  },
  cap: ['#c8302a', '#1a1a20', '#2b5a8c', '#f4cf3a', '#e9e9ec', '#2d6a45', '#f08a24'],
  flatcap: ['#6b5a48', '#4a4a4a', '#7a6a5a', '#3a4a5a'],
  shoe: ['#f7f7f5', '#f7f7f5', '#f7f7f5', '#1a1a20', '#c8302a', '#35c2ff', '#ffd23f'],
};
export const BIKE_COLORS = [
  { frame: '#2a2c30', accent: '#ff7a1a' },
  { frame: '#2a2c30', accent: '#35c2ff' },
  { frame: '#d8d8dc', accent: '#ff3b6b' },
  { frame: '#264d32', accent: '#ffd23f' },
  { frame: '#8a1c22', accent: '#f2f2f2' },
  { frame: '#1d2f55', accent: '#7cff6b' },
  { frame: '#f2e6d0', accent: '#2b5a8c' },
  { frame: '#ff8fb8', accent: '#ffffff' },
];

export const SHOUTS = {
  any: ['Opzij!', 'Tring tring!', 'Kijk uit, ik heb haast!', 'Fietspad? Nooit van gehoord!', 'Ik ga 40, hoor!', 'Haha, mis!',
    'Jij raakt niks!', 'Dit is mijn plein!', 'Rot op met je ijsje!', 'Gas erop!', 'Brrrrrr!', 'Ik heb voorrang!', 'Aan de kant!'],
  teen: ['Bro, rustig!', 'Skrrrt!', 'Dit gaat op TikTok!', 'Mam, kijk!', 'Wacht, ik film dit!', 'Check deze wheelie!', 'Ik heb geen rijbewijs nodig!'],
  adult: ['Ik moet naar m\'n werk!', 'Ik heb nog een call!', 'Even de kids ophalen!', 'Zo, dat scheelt fietsen!'],
  senior: ['Aan de kant, jongeman!', 'Vroeger reden we gewoon op de fiets!', 'Mijn kleinzoon heeft hem afgesteld!',
    'Ik ben op weg naar de bingo!', 'Ik heb voorrang, ik ben 78!', 'Hoe rem je met dit ding?!', 'Waar zit de bel?!'],
};
export const PAIN_SHOUTS = ['AUW!', 'HÉ!', 'Mijn fiets!', 'Dat doet pijn, zeg!', 'Au, m\'n heup!'];
export const THROW_SHOUTS = ['Pak aan!', 'Vang dan!', 'Hier, voor jou!', 'Opgepast!'];
export const BOSS_SHOUTS = ['VOLUME OMHOOG!', 'BASSSSS!', 'Hoor je dat?!', 'Plein is van mij!'];
