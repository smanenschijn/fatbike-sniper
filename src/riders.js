import * as THREE from 'three';
import {
  ATTACK_Z, BIKE_COLORS, IS_TOUCH, BOSS_SHOUTS, ENTRIES, FOUNTAIN, GRAVITY, RING_RADIUS, SHOUTS, SUIT_COLORS, THROW_SHOUTS,
} from './config.js';
import { sfx } from './audio.js';

const RING_NODES = 12;
const LOD_DIST = IS_TOUCH ? 8 : 13;
const _v = new THREE.Vector3();
const _w = new THREE.Vector3();

// Hit spheres in model space (model faces +X). Passenger sits 0.36 m further back.
const DRIVER_SPHERES = [
  { c: new THREE.Vector3(0.075, 1.6, 0), r: 0.27, part: 'head', who: 'driver' },
  { c: new THREE.Vector3(-0.07, 1.17, 0), r: 0.3, part: 'body', who: 'driver' },
  { c: new THREE.Vector3(-0.12, 0.88, 0), r: 0.28, part: 'body', who: 'driver' },
  { c: new THREE.Vector3(0.42, 0.5, 0), r: 0.4, part: 'bike', who: 'driver' },
  { c: new THREE.Vector3(-0.45, 0.5, 0), r: 0.4, part: 'bike', who: 'driver' },
];
const PASSENGER_OFFSET = new THREE.Vector3(-0.36, 0.02, 0);
const PASSENGER_SPHERES = DRIVER_SPHERES.slice(0, 3).map((s) => ({ ...s, c: s.c.clone().add(PASSENGER_OFFSET), who: 'passenger' }));

const pick = (a) => a[Math.floor(Math.random() * a.length)];
const rand = (a, b) => a + Math.random() * (b - a);

function weightedEntry(exclude) {
  const list = ENTRIES.filter((e) => e !== exclude);
  let r = Math.random() * list.reduce((s, e) => s + e.weight, 0);
  for (const e of list) { if ((r -= e.weight) <= 0) return e; }
  return list[0];
}

export class Riders {
  constructor(scene, assets, effects, hooks) {
    this.scene = scene;
    this.effects = effects;
    this.hooks = hooks; // { onPlayerHit(knife), playerEye }
    this.hiTemplate = assets.fatbiker.scene;
    this.loTemplate = assets.fatbikerLod.scene;
    this.matCache = new Map();
    this.list = [];
    this.knives = [];
    this.spawnTimer = 1.0;
    this.retaliateCooldown = 0;
    this.settings = { accuracy: 0.6 };

    const knife = this.hiTemplate.getObjectByName('Rider_Knife').clone();
    knife.position.set(0, 0, 0);
    knife.rotation.set(0, 0, 0);
    knife.scale.setScalar(1.6); // cartoon-sized when flying at you
    this.knifeTemplate = knife;
    this.boomboxTemplate = makeBoombox();
  }

  // ------------------------------------------------------------ construction

  _variant(mat, color) {
    const key = mat.uuid + color;
    if (!this.matCache.has(key)) {
      const m = mat.clone();
      m.color.set(color);
      this.matCache.set(key, m);
    }
    return this.matCache.get(key);
  }

  _dress(model, look) {
    model.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = false; // riders use a cheap blob shadow instead
      const n = o.material.name;
      if (n === 'TracksuitBlack') o.material = this._variant(o.material, look.suit);
      else if (n === 'TracksuitStripe' && look.suit === '#e9e9ec') o.material = this._variant(o.material, '#1a1a20');
      else if (n === 'BikeFrame') o.material = this._variant(o.material, look.bike.frame);
      else if (n === 'BikeAccent') o.material = this._variant(o.material, look.bike.accent);
    });
    const shades = model.getObjectByName('Rider_Sunglasses');
    if (shades) shades.visible = look.shades;
  }

  _buildModel(type) {
    const look = { suit: pick(SUIT_COLORS), bike: pick(BIKE_COLORS), shades: Math.random() < 0.45 };
    const levels = [this.hiTemplate.clone(true), this.loTemplate.clone(true)];
    for (const lvl of levels) {
      this._dress(lvl, look);
      if (type === 'duo') {
        const driver = lvl.getObjectByName('Rider');
        const pas = driver.clone(true);
        pas.name = 'Passenger';
        pas.position.add(PASSENGER_OFFSET);
        const shades = pas.getObjectByName('Rider_Sunglasses');
        if (shades) shades.visible = !look.shades;
        driver.parent.add(pas);
      }
    }
    const lod = new THREE.LOD();
    lod.addLevel(levels[0], 0);
    lod.addLevel(levels[1], LOD_DIST);
    lod.position.set(0.58, 0, 0);
    const pivot = new THREE.Group(); // at the rear wheel contact, for wheelies + lean
    pivot.position.set(-0.58, 0, 0);
    pivot.rotation.order = 'XZY';
    pivot.add(lod);
    const root = new THREE.Group();
    root.add(pivot);
    const blob = new THREE.Mesh(BLOB_GEO, BLOB_MAT);
    blob.rotation.x = -Math.PI / 2;
    blob.position.y = 0.03;
    blob.scale.set(1.5, 0.6, 1);
    blob.renderOrder = 1;
    root.add(blob);
    let boombox = null;
    if (type === 'boss') {
      boombox = this.boomboxTemplate.clone(true);
      boombox.position.set(-0.52 + 0.58, 1.02, 0);
      pivot.add(boombox);
      root.scale.setScalar(1.25);
    }
    return { root, pivot, lod, levels, boombox, blob };
  }

  // ------------------------------------------------------------ routes

  _ringPoint(i, R) {
    const a = (((i % RING_NODES) + RING_NODES) % RING_NODES) / RING_NODES * Math.PI * 2;
    return new THREE.Vector3(FOUNTAIN.x + Math.cos(a) * R, 0, FOUNTAIN.z + Math.sin(a) * R);
  }

  _nearestRing(p, R) {
    let best = 0, bd = Infinity;
    for (let i = 0; i < RING_NODES; i++) {
      const d = this._ringPoint(i, R).distanceToSquared(p);
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  }

  _route(entry, exit, attack) {
    const R = RING_RADIUS + rand(-1.6, 1.6);
    const pts = [entry.spawn.clone(), entry.mouth.clone()];
    const dir = Math.random() < 0.5 ? 1 : -1;
    let i = this._nearestRing(entry.mouth, R);
    const mod = (k) => ((k % RING_NODES) + RING_NODES) % RING_NODES;
    const steps = 2 + Math.floor(Math.random() * 6);
    for (let s = 0; s < steps; s++) { pts.push(this._ringPoint(i, R)); i += dir; }
    let attackPoint = null;
    if (attack) {
      const front = RING_NODES / 4; // node closest to the player (+Z side)
      for (let g = 0; g < RING_NODES && mod(i) !== front; g++) { pts.push(this._ringPoint(i, R)); i += dir; }
      attackPoint = new THREE.Vector3(rand(-3.5, 3.5), 0, ATTACK_Z);
      pts.push(attackPoint.clone());
      i += dir;
    }
    const exitNode = this._nearestRing(exit.mouth, R);
    for (let g = 0; g < RING_NODES && mod(i) !== exitNode; g++) { pts.push(this._ringPoint(i, R)); i += dir; }
    pts.push(this._ringPoint(exitNode, R), exit.mouth.clone(), exit.spawn.clone());
    // jitter so riders don't all follow the exact same line
    for (let k = 2; k < pts.length - 2; k++) { pts[k].x += rand(-0.6, 0.6); pts[k].z += rand(-0.6, 0.6); }
    const curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal');
    return { curve, attackPoint };
  }

  // ------------------------------------------------------------ spawning

  spawn(type, diff) {
    const entry = weightedEntry(null);
    const exit = weightedEntry(entry);
    const attack = (type === 'normal' || type === 'duo') && Math.random() < diff.attackChance;
    const { curve, attackPoint } = this._route(entry, exit, attack);
    const m = this._buildModel(type);
    const base = { normal: rand(6.5, 8.8), duo: rand(5.8, 7), wheelie: rand(11, 13), boss: rand(4.8, 5.6) }[type];
    const r = {
      ...m, type, curve, len: curve.getLength(), dist: 0, speed: base * diff.speedMul,
      alive: true, attackPoint, thrown: false, knifeCooldown: rand(1, 3),
      hp: type === 'boss' ? 3 : 1, shoutTimer: rand(1.5, 4), bellTimer: rand(2, 6),
      yaw: 0, roll: 0, wheelie: type === 'wheelie' ? 0.42 : 0, bob: Math.random() * 10,
      spheres: type === 'duo' ? [...DRIVER_SPHERES, ...PASSENGER_SPHERES] : DRIVER_SPHERES,
      flash: 0,
    };
    if (type === 'boss') r.spheres = [...DRIVER_SPHERES, { c: new THREE.Vector3(-0.52, 1.02, 0), r: 0.32, part: 'body', who: 'driver' }];
    this._place(r, 0);
    this.scene.add(r.root);
    this.list.push(r);
    if (type === 'boss') this.effects.bubble(r.root, new THREE.Vector3(0, 2.9, 0), pick(BOSS_SHOUTS), false, 2.2);
    return r;
  }

  _place(r, dt) {
    const u = Math.min(1, r.dist / r.len);
    r.curve.getPointAt(u, _v);
    r.curve.getTangentAt(u, _w);
    r.root.position.copy(_v);
    const yaw = Math.atan2(-_w.z, _w.x);
    let dy = yaw - r.yaw;
    dy = Math.atan2(Math.sin(dy), Math.cos(dy));
    r.yaw = yaw;
    r.root.rotation.y = yaw;
    if (dt > 0) {
      const targetRoll = THREE.MathUtils.clamp((dy / dt) * r.speed * 0.045, -0.4, 0.4);
      r.roll += (targetRoll - r.roll) * Math.min(1, dt * 5);
    }
    r.bob += dt * (r.speed * 1.3);
    r.pivot.rotation.x = -r.roll;
    r.pivot.rotation.z = r.wheelie + (r.wheelie ? Math.sin(r.bob * 0.6) * 0.06 : 0);
    r.lod.position.y = Math.abs(Math.sin(r.bob)) * 0.02;
    if (r.boombox) r.boombox.scale.setScalar(1 + Math.max(0, Math.sin(performance.now() * 0.0126)) * 0.12);
    r.root.updateMatrixWorld(true);
  }

  // ------------------------------------------------------------ hit tests

  /** All rider hits along a ray, sorted by distance: [{ rider, t, point, part, who }]. */
  raycast(origin, dir, maxDist = 300, pad = 0) {
    const hits = [];
    for (const r of this.list) {
      if (!r.alive) continue;
      _v.copy(r.root.position).setY(1).sub(origin);
      const tc = _v.dot(dir);
      if (tc < -3 || tc > maxDist + 3) continue;
      if (_v.lengthSq() - tc * tc > 9) continue; // broad phase
      let best = null;
      const scale = r.root.scale.x;
      for (const s of r.spheres) {
        _w.copy(s.c).applyMatrix4(r.lod.matrixWorld).sub(origin);
        const rad = s.r * scale + pad;
        const tca = _w.dot(dir);
        const d2 = _w.lengthSq() - tca * tca;
        if (d2 > rad * rad) continue;
        const thc = Math.sqrt(rad * rad - d2);
        let t = tca - thc;
        if (t < 0) t = tca + thc;
        if (t < 0 || t > maxDist) continue;
        if (!best || t < best.t) best = { rider: r, t, part: s.part, who: s.who };
      }
      if (best) {
        best.point = origin.clone().addScaledVector(dir, best.t);
        hits.push(best);
      }
    }
    return hits.sort((a, b) => a.t - b.t);
  }

  inRadius(center, radius) {
    return this.list.filter((r) => r.alive && r.root.position.distanceTo(center) < radius + 0.6 * r.root.scale.x);
  }

  // ------------------------------------------------------------ damage / slapstick

  /** Returns true when the rider got knocked off. */
  damage(r, amount, info) {
    if (!r.alive) return false;
    r.hp -= amount;
    if (r.hp > 0) {
      r.flash = 0.15;
      this.effects.bubble(r.root, new THREE.Vector3(0, 2.9, 0), pick(['AUW!', 'HÉ!', 'Mijn speaker!', 'Wollah, dat doet pijn!']), false, 1.2);
      return false;
    }
    this.knockOff(r, info);
    return true;
  }

  knockOff(r, { dir, power = 6, explode = false }) {
    r.alive = false;
    const idx = Math.max(0, r.lod.getCurrentLevel());
    const lvl = r.levels[Math.min(idx, r.levels.length - 1)];
    for (const other of r.levels) if (other !== lvl) r.lod.remove(other);
    for (let i = r.lod.levels.length - 1; i >= 0; i--) if (r.lod.levels[i].object !== lvl) r.lod.levels.splice(i, 1);
    r.lod.autoUpdate = false;
    lvl.visible = true;

    const fwd = new THREE.Vector3(Math.cos(r.yaw), 0, -Math.sin(r.yaw));
    const carry = fwd.clone().multiplyScalar(r.speed * 0.5);
    const push = dir.clone().setY(0).normalize().multiplyScalar(power);
    const randAng = (s) => new THREE.Vector3(rand(-s, s), rand(-s, s), rand(-s, s));

    for (const name of ['Rider', 'Passenger']) {
      const body = lvl.getObjectByName(name);
      if (!body) continue;
      const hair = body.getObjectByName('Rider_Hair');
      const head = body.getObjectByName('Rider_Head');
      if (hair && head) {
        const hc = head.localToWorld(new THREE.Vector3(0.05, 0.25, 0));
        this.effects.addDebris(hair, hc, push.clone().multiplyScalar(0.6).add(new THREE.Vector3(rand(-1, 1), rand(6, 9), rand(-1, 1))),
          randAng(12), { radius: 0.18, life: 3.4, bounce: 0.5 });
      }
      const center = body.localToWorld(new THREE.Vector3(-0.1, 1.1, 0));
      const up = explode ? rand(9, 13) : rand(4.5, 6.5);
      this.effects.addDebris(body, center, push.clone().add(carry).add(new THREE.Vector3(0, up, 0)), randAng(explode ? 14 : 8),
        { radius: 0.42 * r.root.scale.x, life: 3.6, stars: true });
    }
    if (r.boombox) {
      const c = r.boombox.getWorldPosition(new THREE.Vector3());
      this.effects.addDebris(r.boombox, c, push.clone().add(new THREE.Vector3(0, 7, 0)), randAng(10), { radius: 0.25, life: 3.4 });
    }
    if (explode) {
      for (const name of ['Bike_WheelFront', 'Bike_WheelRear', 'Bike_Handlebar']) {
        const part = lvl.getObjectByName(name);
        if (!part) continue;
        const c = part.getWorldPosition(new THREE.Vector3());
        const out = c.clone().sub(r.root.position).setY(0).normalize().multiplyScalar(rand(5, 9));
        this.effects.addDebris(part, c, out.add(new THREE.Vector3(0, rand(7, 12), 0)), randAng(15), { radius: 0.32, life: 3.4, bounce: 0.55 });
      }
    }
    // the bike itself skids and tumbles on
    r.root.remove(r.blob);
    const bc = r.root.position.clone().add(new THREE.Vector3(0, 0.45, 0));
    const tumble = fwd.clone().multiplyScalar(rand(-7, 7)).add(new THREE.Vector3(0, rand(-2, 2), 0));
    this.scene.remove(r.root);
    this.effects.addDebris(r.root, bc, carry.clone().multiplyScalar(1.3).add(push.clone().multiplyScalar(0.3)).add(new THREE.Vector3(0, explode ? 8 : 2, 0)),
      tumble, { radius: 0.4, life: 3.6, bounce: 0.3 });
    sfx.knockOff();
    this.list = this.list.filter((x) => x !== r);
  }

  // ------------------------------------------------------------ knives

  throwKnife(r, accurate) {
    const eye = this.hooks.playerEye;
    const from = r.lod.localToWorld(new THREE.Vector3(0.25, 1.4, -0.25));
    const target = eye.clone();
    if (!accurate) target.add(new THREE.Vector3(rand(-1, 1), rand(0.2, 1.4), 0).normalize().multiplyScalar(rand(1.1, 1.9)));
    else target.add(new THREE.Vector3(rand(-0.15, 0.15), rand(-0.1, 0.1), 0));
    const T = THREE.MathUtils.clamp(from.distanceTo(target) / 15, 0.9, 1.9);
    const vel = target.clone().sub(from).divideScalar(T).add(new THREE.Vector3(0, 0.5 * GRAVITY * T, 0));
    const mesh = this.knifeTemplate.clone(true);
    mesh.position.copy(from);
    mesh.lookAt(target);
    mesh.rotateY(-Math.PI / 2);
    this.scene.add(mesh);
    this.knives.push({ mesh, vel, age: 0, accurate, spin: rand(14, 20) });
    r.thrown = true;
    r.knifeCooldown = rand(3, 5);
    this.effects.bubble(r.root, new THREE.Vector3(0, 2.6, 0), pick(THROW_SHOUTS), true, 1.3);
    sfx.whoosh();
  }

  /** A random visible rider throws a knife back at you (after you miss). */
  retaliate() {
    if (this.retaliateCooldown > 0) return;
    const eye = this.hooks.playerEye;
    const cands = this.list.filter((r) => r.alive && r.knifeCooldown <= 0 && r.type !== 'wheelie' && r.root.position.distanceTo(eye) < 42);
    if (!cands.length) return;
    this.throwKnife(pick(cands), Math.random() < this.settings.accuracy - 0.05);
    this.retaliateCooldown = 1.4;
  }

  /** Knives along a ray: [{ knife, t }]. */
  raycastKnives(origin, dir, maxDist = 300) {
    const out = [];
    for (const k of this.knives) {
      _w.copy(k.mesh.position).sub(origin);
      const tca = _w.dot(dir);
      if (tca < 0 || tca > maxDist) continue;
      const d2 = _w.lengthSq() - tca * tca;
      const rad = 0.45;
      if (d2 < rad * rad) out.push({ knife: k, t: tca });
    }
    return out.sort((a, b) => a.t - b.t);
  }

  destroyKnife(k, spark = true) {
    if (spark) this.effects.puff(k.mesh.position.clone(), 0xfff0c0, 4, 0.3);
    const vel = k.vel.clone().multiplyScalar(-0.3).add(new THREE.Vector3(rand(-2, 2), 5, rand(-2, 2)));
    this.effects.addDebris(k.mesh, k.mesh.position.clone(), vel, new THREE.Vector3(rand(-20, 20), rand(-20, 20), 0), { radius: 0.05, life: 2 });
    this.knives = this.knives.filter((x) => x !== k);
  }

  _updateKnives(dt) {
    const eye = this.hooks.playerEye;
    for (let i = this.knives.length - 1; i >= 0; i--) {
      const k = this.knives[i];
      k.age += dt;
      k.vel.y -= GRAVITY * dt;
      k.mesh.position.addScaledVector(k.vel, dt);
      k.mesh.rotateZ(-k.spin * dt);
      if (k.mesh.position.distanceTo(eye) < 0.6) {
        this.scene.remove(k.mesh);
        this.knives.splice(i, 1);
        this.hooks.onPlayerHit(k);
        continue;
      }
      if (k.mesh.position.y < 0.05 || k.age > 4 || k.mesh.position.z > eye.z + 3) {
        this.scene.remove(k.mesh);
        this.knives.splice(i, 1);
        if (k.mesh.position.z > eye.z - 1) sfx.clank();
      }
    }
  }

  // ------------------------------------------------------------ frame update

  update(dt, diff, elapsed) {
    this.retaliateCooldown -= dt;
    // spawning
    this.spawnTimer -= dt;
    if (this.spawnTimer <= 0 && this.list.length < diff.maxAlive) {
      this.spawnTimer = diff.spawnInterval * rand(0.7, 1.3);
      let type = 'normal';
      const roll = Math.random();
      const hasBoss = this.list.some((r) => r.type === 'boss');
      if (elapsed > 25 && !hasBoss && roll < 0.1) type = 'boss';
      else if (elapsed > 15 && roll < 0.24) type = 'wheelie';
      else if (elapsed > 8 && roll < 0.36) type = 'duo';
      this.spawn(type, diff);
      if (elapsed > 20 && Math.random() < 0.3) this.spawn('normal', diff); // groups later on
    }

    const eye = this.hooks.playerEye;
    for (let i = this.list.length - 1; i >= 0; i--) {
      const r = this.list[i];
      r.knifeCooldown -= dt;
      let speed = r.speed;
      if (r.attackPoint && !r.thrown) {
        const d = Math.hypot(r.root.position.x - r.attackPoint.x, r.root.position.z - r.attackPoint.z);
        if (d < 6) speed *= 0.65; // slow down to aim
        if (d < 2.5) this.throwKnife(r, Math.random() < this.settings.accuracy);
      }
      r.dist += speed * dt;
      if (r.dist >= r.len) { // escaped down a street
        this.scene.remove(r.root);
        this.list.splice(i, 1);
        continue;
      }
      this._place(r, dt);
      // wheels spin
      const w = (speed / 0.33) * dt;
      for (const lvl of r.levels) {
        const f = lvl.getObjectByName('Bike_WheelFront');
        const b = lvl.getObjectByName('Bike_WheelRear');
        if (f) f.rotation.z -= w;
        if (b) b.rotation.z -= w;
      }
      // chatter
      const dist = r.root.position.distanceTo(eye);
      r.shoutTimer -= dt;
      if (r.shoutTimer <= 0) {
        r.shoutTimer = rand(4, 8);
        if (dist < 40) this.effects.bubble(r.root, new THREE.Vector3(0, 2.5, 0), pick(r.type === 'boss' ? BOSS_SHOUTS : SHOUTS));
      }
      r.bellTimer -= dt;
      if (r.bellTimer <= 0) {
        r.bellTimer = rand(4, 9);
        if (dist < 35) sfx.bell(THREE.MathUtils.clamp((r.root.position.x - eye.x) / 20, -1, 1));
      }
    }
    this._updateKnives(dt);
  }

  clear() {
    for (const r of this.list) this.scene.remove(r.root);
    for (const k of this.knives) this.scene.remove(k.mesh);
    this.list = [];
    this.knives = [];
    this.spawnTimer = 1.0;
  }
}

const BLOB_GEO = new THREE.CircleGeometry(0.85, 24);
const BLOB_MAT = (() => {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, 'rgba(0,0,0,0.55)');
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  return new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false });
})();

function makeBoombox() {
  const g = new THREE.Group();
  const body = new THREE.MeshStandardMaterial({ color: 0x2b2d33, roughness: 0.4, metalness: 0.3 });
  const chrome = new THREE.MeshStandardMaterial({ color: 0xd8d8d8, roughness: 0.15, metalness: 1 });
  const cone = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.7 });
  const neon = new THREE.MeshStandardMaterial({ color: 0xff2bd0, emissive: 0xff2bd0, emissiveIntensity: 2 });
  const box = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.3, 0.6), body);
  g.add(box);
  for (const s of [-1, 1]) {
    for (const z of [-0.16, 0.16]) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.015, 8, 24), chrome);
      ring.position.set(0, 0, z);
      ring.position.x = 0;
      ring.rotation.y = Math.PI / 2;
      ring.position.set(s * 0.172, 0, z);
      const c = new THREE.Mesh(new THREE.CircleGeometry(0.095, 24), cone);
      c.position.set(s * 0.171, 0, z);
      c.rotation.y = (s * Math.PI) / 2;
      g.add(ring, c);
    }
  }
  const handle = new THREE.Mesh(new THREE.TorusGeometry(0.16, 0.018, 8, 24, Math.PI), chrome);
  handle.position.y = 0.15;
  handle.rotation.y = Math.PI / 2;
  g.add(handle);
  const strip = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.03, 0.5), neon);
  strip.position.y = -0.1;
  g.add(strip);
  return g;
}
