import * as THREE from 'three';

/** Blender (x, y, z) -> three.js (x, z, -y). The glTF exporter applies the same conversion. */
export const B = (x, y, z = 0) => new THREE.Vector3(x, z, -y);

/** Phones/tablets: touch controls + a lighter graphics profile. */
export const IS_TOUCH = typeof window !== 'undefined'
  && (new URLSearchParams(location.search).has('touch') || matchMedia('(pointer: coarse)').matches
    || (navigator.maxTouchPoints > 0 && !matchMedia('(pointer: fine)').matches));

export const ROUND_TIME = 60;

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

/** Difficulty ramps over the round (t in 0..1). */
export const difficulty = (t) => ({
  spawnInterval: THREE.MathUtils.lerp(1.9, 0.5, t),
  maxAlive: Math.round(THREE.MathUtils.lerp(5, 18, t) * (IS_TOUCH ? 0.75 : 1)),
  attackChance: THREE.MathUtils.lerp(0.12, 0.45, t),
  speedMul: THREE.MathUtils.lerp(1.0, 1.35, t),
});

export const SUIT_COLORS = ['#1a1a20', '#1a1a20', '#5d6066', '#1e2a4a', '#e9e9ec', '#6b1d2a'];
export const BIKE_COLORS = [
  { frame: '#2a2c30', accent: '#ff7a1a' },
  { frame: '#2a2c30', accent: '#35c2ff' },
  { frame: '#d8d8dc', accent: '#ff3b6b' },
  { frame: '#264d32', accent: '#ffd23f' },
  { frame: '#8a1c22', accent: '#f2f2f2' },
  { frame: '#1d2f55', accent: '#7cff6b' },
];

export const SHOUTS = [
  'Wollah!', 'Kijk uit, man!', 'Sahbi, rustig!', 'Haha, mis!', 'Fakka!', 'Wat kijk je nou?',
  'Opzij, opa!', 'Brrrrrrr!', 'Ewa!', 'Rot op met je ijsje!', 'Ik ben de snelste!', 'Check deze wheelie!',
  'Tring tring!', 'Mattie, gas erop!', 'Dit is mijn plein!', 'Jij raakt niks!',
];
export const THROW_SHOUTS = ['Pak aan!', 'Vang dan!', 'Hier, voor jou!', 'Mes erin!'];
export const BOSS_SHOUTS = ['VOLUME OMHOOG!', 'BASSSSS!', 'Hoor je dat?!', 'Plein is van mij!'];
