import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const FILES = {
  square: 'models/square.glb',
  riders: 'models/riders.glb',
  ridersLod: 'models/riders_lod.glb',
  ijsje: 'models/ijsje.glb',
  katapult: 'models/weapons/katapult.glb',
  shotgun: 'models/weapons/shotgun.glb',
  sniper: 'models/weapons/sniper.glb',
  bazooka: 'models/weapons/bazooka.glb',
};

export async function loadAssets(onProgress) {
  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  const keys = Object.keys(FILES);
  const progress = Object.fromEntries(keys.map((k) => [k, 0]));
  const report = () => onProgress?.(keys.reduce((s, k) => s + progress[k], 0) / keys.length);
  const results = await Promise.all(keys.map((k) => new Promise((resolve, reject) => {
    loader.load(FILES[k], (g) => { progress[k] = 1; report(); resolve([k, g]); },
      (e) => { if (e.total) { progress[k] = e.loaded / e.total; report(); } }, reject);
  })));
  const out = Object.fromEntries(results);
  // Blender's fabric sheen comes out far too strong in three.js (everything looks frosted)
  const done = new Set();
  for (const g of Object.values(out)) {
    g.scene.traverse((o) => {
      if (!o.isMesh) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        if (done.has(m)) continue;
        done.add(m);
        if (m.sheen !== undefined) m.sheen = 0;
        if (m.clearcoat) m.clearcoat *= 0.5;
      }
    });
  }
  return out;
}
