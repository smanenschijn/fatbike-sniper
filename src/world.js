import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';
import { Lensflare, LensflareElement } from 'three/addons/objects/Lensflare.js';
import { computeBoundsTree, disposeBoundsTree, acceleratedRaycast } from 'three-mesh-bvh';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { B } from './config.js';

THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.BufferGeometry.prototype.disposeBoundsTree = disposeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;

// Late-afternoon summer sun, low in the west-north-west so it can flare when you look left.
export const SUN_DIR = new THREE.Vector3(-0.8, 0.5, -0.33).normalize();

function flareTexture(size, stops) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  stops.forEach(([o, col]) => grad.addColorStop(o, col));
  g.fillStyle = grad;
  g.fillRect(0, 0, size, size);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export class World {
  constructor(renderer, scene, assets) {
    this.scene = scene;
    this.colliders = [];
    this.markers = {};

    // --- the square: static, so merge everything per material (hundreds of draw calls -> ~70)
    const square = assets.square.scene;
    square.updateMatrixWorld(true);
    for (const name of ['PlayerEye', 'Player_Table', 'Player_Chair', 'Square_Center',
      'Spawn_West', 'Spawn_East', 'Spawn_North', 'Spawn_AlleyNW', 'Spawn_AlleyE']) {
      const o = square.getObjectByName(name);
      if (o) this.markers[name] = o;
    }
    this.eye = new THREE.Vector3();
    (this.markers.PlayerEye || square).getWorldPosition(this.eye);
    const byMat = new Map();
    square.traverse((o) => {
      if (!o.isMesh || isDescendant(o, this.markers.Player_Chair)) return; // the camera sits in the player's chair
      const list = byMat.get(o.material) || [];
      list.push(toWorldFloat(o.geometry, o.matrixWorld));
      byMat.set(o.material, list);
    });
    const merged = new THREE.Group();
    merged.name = 'SquareMerged';
    for (const [mat, geoms] of byMat) {
      const g = mergeGeometries(geoms, false);
      geoms.forEach((x) => x.dispose());
      if (!g) continue;
      g.computeBoundsTree();
      const m = new THREE.Mesh(g, mat);
      m.castShadow = true;
      m.receiveShadow = true;
      m.name = mat.name;
      if (mat.map) mat.map.anisotropy = renderer.capabilities.getMaxAnisotropy();
      merged.add(m);
      this.colliders.push(m);
    }
    scene.add(merged);

    // --- sky + image based lighting
    const sky = new Sky();
    sky.scale.setScalar(4000);
    const u = sky.material.uniforms;
    u.turbidity.value = 4.5;
    u.rayleigh.value = 1.4;
    u.mieCoefficient.value = 0.004;
    u.mieDirectionalG.value = 0.82;
    u.sunPosition.value.copy(SUN_DIR).multiplyScalar(1000);
    scene.add(sky);
    const pmrem = new THREE.PMREMGenerator(renderer);
    const envScene = new THREE.Scene();
    const skyClone = new Sky();
    skyClone.scale.setScalar(4000);
    skyClone.material.uniforms.sunPosition.value.copy(u.sunPosition.value);
    for (const k of ['turbidity', 'rayleigh', 'mieCoefficient', 'mieDirectionalG']) skyClone.material.uniforms[k].value = u[k].value;
    envScene.add(skyClone);
    scene.environment = pmrem.fromScene(envScene, 0.02).texture;
    scene.environmentIntensity = 0.55;
    scene.fog = new THREE.Fog(0xcfe0ee, 70, 260);

    // --- sun with soft shadows over the square
    const sun = new THREE.DirectionalLight(0xffe2b8, 3.4);
    sun.position.copy(SUN_DIR).multiplyScalar(80);
    sun.target.position.set(0, 0, 0);
    sun.castShadow = true;
    sun.shadow.mapSize.set(4096, 4096);
    const sc = sun.shadow.camera;
    sc.left = -45; sc.right = 45; sc.top = 45; sc.bottom = -45; sc.near = 10; sc.far = 220;
    sun.shadow.bias = -0.0003;
    sun.shadow.normalBias = 0.03;
    sun.shadow.radius = 3;
    scene.add(sun, sun.target);
    scene.add(new THREE.HemisphereLight(0xbfdcff, 0x8a5a3c, 0.45));

    // --- lens flare
    const flareLight = new THREE.PointLight(0xffffff, 0);
    flareLight.position.copy(SUN_DIR).multiplyScalar(900);
    const main = flareTexture(256, [[0, 'rgba(255,255,240,1)'], [0.2, 'rgba(255,230,170,0.8)'], [1, 'rgba(255,200,120,0)']]);
    const ring = flareTexture(128, [[0, 'rgba(255,255,255,0)'], [0.7, 'rgba(255,220,160,0)'], [0.85, 'rgba(255,220,160,0.35)'], [1, 'rgba(255,220,160,0)']]);
    const dot = flareTexture(64, [[0, 'rgba(255,240,200,0.6)'], [1, 'rgba(255,240,200,0)']]);
    const lf = new Lensflare();
    lf.addElement(new LensflareElement(main, 520, 0, new THREE.Color(1, 0.95, 0.85)));
    lf.addElement(new LensflareElement(ring, 160, 0.4));
    lf.addElement(new LensflareElement(dot, 60, 0.6, new THREE.Color(0.7, 1, 0.8)));
    lf.addElement(new LensflareElement(dot, 90, 0.75, new THREE.Color(1, 0.8, 0.6)));
    lf.addElement(new LensflareElement(ring, 220, 1.0, new THREE.Color(0.8, 0.9, 1)));
    flareLight.add(lf);
    scene.add(flareLight);

    // --- ice cream on the player's table
    this.ijsje = assets.ijsje.scene;
    // (mesh node transforms are altered by meshopt quantization, so use the known table spot)
    this.ijsje.position.copy(B(-0.38, -11.0, 0.755));
    this.ijsje.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    scene.add(this.ijsje);
    this.ijsjeFall = null;

    this.raycaster = new THREE.Raycaster();
    this.raycaster.firstHitOnly = true;
  }

  /** Nearest world hit along a ray (or null). */
  raycast(origin, dir, far = 400) {
    this.raycaster.set(origin, dir);
    this.raycaster.far = far;
    const hits = this.raycaster.intersectObjects(this.colliders, false);
    return hits.length ? hits[0] : null;
  }

  knockOverIjsje(fromDir) {
    if (this.ijsjeFall) return;
    const axis = new THREE.Vector3(fromDir.z, 0, -fromDir.x).normalize();
    this.ijsjeFall = { t: 0, axis, q0: this.ijsje.quaternion.clone() };
    // scoops tumble off separately
    const scoops = this.ijsje.getObjectByName('IJsje_Scoops');
    const top = this.ijsje.getObjectByName('IJsje_Topping');
    this.ijsjeBits = [scoops, top].filter(Boolean).map((o) => {
      const v = new THREE.Vector3(fromDir.x * 1.2 + (Math.random() - 0.5), 2 + Math.random(), fromDir.z * 1.2 + (Math.random() - 0.5));
      this.scene.attach(o);
      return { o, v, spin: new THREE.Vector3(Math.random() * 8, Math.random() * 8, Math.random() * 8) };
    });
  }

  update(dt) {
    if (this.ijsjeFall) {
      const f = this.ijsjeFall;
      f.t = Math.min(1, f.t + dt * 3);
      const q = new THREE.Quaternion().setFromAxisAngle(f.axis, (Math.PI / 2) * easeOutBounce(f.t));
      this.ijsje.quaternion.copy(f.q0).premultiply(q);
      for (const b of this.ijsjeBits) {
        if (b.o.position.y <= 0.02 && b.v.y <= 0) continue;
        b.v.y -= 9.8 * dt;
        b.o.position.addScaledVector(b.v, dt);
        b.o.rotation.x += b.spin.x * dt; b.o.rotation.y += b.spin.y * dt;
        if (b.o.position.y < 0.02) { b.o.position.y = 0.02; b.v.set(0, 0, 0); }
      }
    }
  }
}

function easeOutBounce(x) {
  const n1 = 7.5625, d1 = 2.75;
  if (x < 1 / d1) return n1 * x * x;
  if (x < 2 / d1) return n1 * (x -= 1.5 / d1) * x + 0.75;
  if (x < 2.5 / d1) return n1 * (x -= 2.25 / d1) * x + 0.9375;
  return n1 * (x -= 2.625 / d1) * x + 0.984375;
}

/** Copy a (possibly quantized) geometry into plain float attributes, baked into world space. */
function toWorldFloat(src, matrix) {
  const pos = src.attributes.position;
  const n = pos.count;
  const g = new THREE.BufferGeometry();
  const p = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { p[i * 3] = pos.getX(i); p[i * 3 + 1] = pos.getY(i); p[i * 3 + 2] = pos.getZ(i); }
  g.setAttribute('position', new THREE.BufferAttribute(p, 3));
  const nor = src.attributes.normal;
  if (nor) {
    const a = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { a[i * 3] = nor.getX(i); a[i * 3 + 1] = nor.getY(i); a[i * 3 + 2] = nor.getZ(i); }
    g.setAttribute('normal', new THREE.BufferAttribute(a, 3));
  }
  const uv = src.attributes.uv;
  const u = new Float32Array(n * 2);
  if (uv) for (let i = 0; i < n; i++) { u[i * 2] = uv.getX(i); u[i * 2 + 1] = uv.getY(i); }
  g.setAttribute('uv', new THREE.BufferAttribute(u, 2));
  if (src.index) g.setIndex(Array.from(src.index.array));
  g.applyMatrix4(matrix);
  if (!nor) g.computeVertexNormals();
  return g;
}

function isDescendant(o, root) {
  if (!root) return false;
  for (let p = o; p; p = p.parent) if (p === root) return true;
  return false;
}
