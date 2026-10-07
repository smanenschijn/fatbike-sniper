import * as THREE from 'three';
import { B, FOV, ZOOM_FOV } from './config.js';
import { sfx } from './audio.js';

/** Weapon stats. Muzzles are in the viewmodel's own (Blender) frame. */
const DEFS = [
  { key: 'katapult', name: 'KATAPULT', mag: Infinity, reserve: Infinity, fireDelay: 0.3, reload: 0, kind: 'projectile',
    projectile: { speed: 42, gravity: 6, radius: 0.12, damage: 1 }, muzzle: B(0, 0, 0.36), kick: 0.35,
    offset: new THREE.Vector3(0, -0.11, 0.13) },
  { key: 'shotgun', name: 'SHOTGUN', mag: 6, reserve: Infinity, fireDelay: 0.85, reload: 1.7, kind: 'hitscan',
    pellets: 10, spread: 0.075, range: 32, damage: 1, maxPerRider: 2, muzzle: B(0.8, 0, 0.06), kick: 1.0 },
  { key: 'sniper', name: 'SNIPER', mag: 5, reserve: Infinity, fireDelay: 1.05, reload: 2.1, kind: 'hitscan',
    pellets: 1, spread: 0, range: 400, damage: 3, pierce: 6, muzzle: B(1.07, 0, 0.03), kick: 1.2, zoom: true },
  { key: 'bazooka', name: 'BAZOOKA', mag: 1, reserve: 5, fireDelay: 0.6, reload: 2.4, kind: 'projectile',
    projectile: { speed: 30, gravity: 1.2, radius: 0.2, damage: 3, explode: 5 }, muzzle: B(0.95, 0, 0), kick: 1.6 },
];

export class Weapons {
  constructor(camera, assets, ctx) {
    this.camera = camera;
    this.ctx = ctx; // { fireHitscan(def, origin, dirs), fireProjectile(def, muzzle, dir), onEmpty() }
    this.root = new THREE.Group();
    this.root.rotation.y = Math.PI / 2; // viewmodel space (+X forward) -> camera space (-Z forward)
    camera.add(this.root);
    this.list = DEFS.map((d) => {
      const model = assets[d.key].scene;
      model.traverse((o) => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = true; o.frustumCulled = false; } });
      const vm = model.children[0] || model; // the VM_<Weapon> root, placed in camera space
      const holder = new THREE.Group();
      holder.add(model);
      holder.visible = false;
      this.root.add(holder);
      return {
        ...d, holder, vm, ammo: d.mag, reserveLeft: d.reserve, cooldown: 0, reloading: 0,
        parts: {
          pump: model.getObjectByName('Shotgun_Pump'), shell: model.getObjectByName('Shotgun_Shell'),
          bolt: model.getObjectByName('Sniper_Bolt'), rocket: model.getObjectByName('Bazooka_Rocket'),
          pouch: model.getObjectByName('Katapult_Pouch'), stone: model.getObjectByName('Katapult_Stone'),
          bands: model.getObjectByName('Katapult_Bands'),
        },
        anim: 0,
      };
    });
    for (const w of this.list) {
      w.base = {};
      for (const [k, p] of Object.entries(w.parts)) if (p) w.base[k] = p.position.clone();
      if (w.parts.shell) w.parts.shell.visible = false;
    }
    this.index = 0;
    this.switchT = 1; // 0 = lowered, 1 = raised
    this.pending = null;
    this.kick = 0;
    this.zoom = 0;
    this.time = 0;
    this.current.holder.visible = true;
  }

  get current() { return this.list[this.index]; }

  reset({ rockets = 5 } = {}) {
    for (const w of this.list) {
      w.ammo = w.mag; w.reserveLeft = w.key === 'bazooka' ? rockets : w.reserve; w.cooldown = 0; w.reloading = 0; w.anim = 0;
      if (w.parts.rocket) w.parts.rocket.visible = true;
    }
    this.select(0, true);
  }

  select(i, instant = false) {
    if (i === this.index && !instant) return;
    this.current.reloading = 0;
    if (instant) {
      this.list.forEach((w, k) => (w.holder.visible = k === i));
      this.index = i;
      this.switchT = 1;
      this.pending = null;
      return;
    }
    this.pending = i;
  }

  cycle(step) { this.select((this.index + step + this.list.length) % this.list.length); }

  startReload() {
    const w = this.current;
    if (w.reloading > 0 || w.ammo >= w.mag || w.reserveLeft <= 0 || w.mag === Infinity) return;
    w.reloading = w.reload;
    sfx.reload();
  }

  /** Muzzle position in world space for the current weapon. */
  muzzleWorld() {
    const w = this.current;
    return w.vm.localToWorld(w.muzzle.clone());
  }

  tryFire(input) {
    const w = this.current;
    if (this.switchT < 1 || this.pending !== null || w.cooldown > 0 || w.reloading > 0) return false;
    if (w.ammo <= 0) {
      if (input.firePressed) sfx.empty();
      if (w.reserveLeft > 0) this.startReload();
      else this.ctx.onEmpty?.(w);
      return false;
    }
    if (!input.firePressed && !input.fireDown) return false;
    if (!input.firePressed && w.key !== 'katapult') return false; // semi-auto except the slingshot
    w.ammo -= 1;
    w.cooldown = w.fireDelay;
    w.anim = 1;
    this.kick = Math.min(1.6, this.kick + w.kick);
    sfx.shot(w.key);

    const origin = this.camera.getWorldPosition(new THREE.Vector3());
    const fwd = input.aimDirection(this.camera);
    if (w.kind === 'hitscan') {
      const dirs = [];
      const spread = this.zoom > 0.5 ? 0 : w.spread;
      for (let i = 0; i < w.pellets; i++) dirs.push(i === 0 && w.pellets > 1 ? fwd.clone() : jitter(fwd, spread));
      this.ctx.fireHitscan(w, origin, dirs, this.zoom > 0.5 ? null : this.muzzleWorld());
    } else {
      this.ctx.fireProjectile(w, this.muzzleWorld(), origin, fwd);
      if (w.parts.rocket) w.parts.rocket.visible = false;
    }
    if (w.ammo <= 0 && w.reserveLeft > 0) setTimeout(() => this.startReload(), w.fireDelay * 600);
    return true;
  }

  update(dt, input) {
    this.time += dt;
    const w = this.current;
    // weapon selection
    for (let k = 0; k < this.list.length; k++) if (input.keysPressed.has(`Digit${k + 1}`)) this.select(k);
    if (input.wheel) this.cycle(input.wheel > 0 ? 1 : -1);
    if (input.keysPressed.has('KeyR')) this.startReload();

    if (this.pending !== null) {
      this.switchT = Math.max(0, this.switchT - dt * 6);
      if (this.switchT === 0) {
        w.holder.visible = false;
        this.index = this.pending;
        this.pending = null;
        this.current.holder.visible = true;
      }
    } else {
      this.switchT = Math.min(1, this.switchT + dt * 5);
    }

    for (const x of this.list) {
      x.cooldown = Math.max(0, x.cooldown - dt);
      x.anim = Math.max(0, x.anim - dt / Math.max(0.2, x.fireDelay));
    }
    if (w.reloading > 0) {
      w.reloading -= dt;
      if (w.reloading <= 0) {
        const need = w.mag - w.ammo;
        const take = Math.min(need, w.reserveLeft);
        w.ammo += take;
        if (w.reserveLeft !== Infinity) w.reserveLeft -= take;
        w.reloading = 0;
        if (w.parts.rocket) w.parts.rocket.visible = true;
        sfx.click();
      }
    }

    // sniper zoom
    const wantZoom = w.zoom && input.zoomHeld && this.switchT === 1 && w.reloading <= 0;
    this.zoom += ((wantZoom ? 1 : 0) - this.zoom) * Math.min(1, dt * 14);
    const fov = THREE.MathUtils.lerp(FOV, ZOOM_FOV, this.zoom);
    if (Math.abs(this.camera.fov - fov) > 0.01) { this.camera.fov = fov; this.camera.updateProjectionMatrix(); }
    input.sensScale = fov / FOV;
    this.root.visible = this.zoom < 0.6;

    // procedural animation: recoil, sway, lowering, reload dip
    this.kick = Math.max(0, this.kick - dt * 5);
    const k = this.kick;
    const lower = 1 - easeOut(this.switchT);
    const reloadDip = w.reloading > 0 ? Math.sin(Math.PI * (1 - w.reloading / w.reload)) : 0;
    const sway = Math.sin(this.time * 1.6) * 0.004;
    w.holder.position.set(-k * 0.07, -lower * 0.35 - reloadDip * 0.12 + sway + k * 0.015, Math.cos(this.time * 0.8) * 0.003);
    if (w.offset) w.holder.position.add(w.offset);
    w.holder.rotation.set(reloadDip * 0.5, 0, k * 0.12 - lower * 0.6 - reloadDip * 0.25);

    const a = w.anim;
    const p = w.parts;
    if (p.pump && w.base.pump) { // pump: back then forward
      const s = a > 0.5 ? (1 - a) * 2 : a * 2;
      p.pump.position.copy(w.base.pump).add(new THREE.Vector3(-0.08 * s, 0, 0));
      if (a > 0.45 && a < 0.5 && !w._ejected) { w._ejected = true; this.ctx.ejectShell?.(p.shell); }
      if (a < 0.1) w._ejected = false;
    }
    if (p.bolt && w.base.bolt) {
      const s = a > 0.5 ? (1 - a) * 2 : a * 2;
      p.bolt.position.copy(w.base.bolt).add(new THREE.Vector3(-0.07 * s, 0.02 * s, 0));
    }
    if (p.pouch && w.base.pouch) { // slingshot: snap forward, then pull back
      const snap = a > 0.75 ? 1 : a > 0.4 ? (a - 0.4) / 0.35 : 0;
      const fork = new THREE.Vector3(0.34, 0, 0);
      p.pouch.position.copy(w.base.pouch).addScaledVector(fork, snap);
      p.stone.position.copy(w.base.stone).addScaledVector(fork, snap);
      p.stone.visible = a < 0.4;
      p.bands.visible = snap < 0.5;
    }
  }

  hudState() {
    return {
      index: this.index,
      list: this.list.map((w) => ({ name: w.name, ammo: w.ammo, reserve: w.reserveLeft, mag: w.mag })),
      reload: this.current.reloading > 0 ? 1 - this.current.reloading / this.current.reload : null,
      zoom: this.zoom > 0.6,
      key: this.current.key,
    };
  }
}

function jitter(dir, spread) {
  if (!spread) return dir.clone();
  const up = Math.abs(dir.y) < 0.99 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
  const right = new THREE.Vector3().crossVectors(dir, up).normalize();
  const up2 = new THREE.Vector3().crossVectors(right, dir).normalize();
  const r = Math.sqrt(Math.random()) * spread;
  const a = Math.random() * Math.PI * 2;
  return dir.clone().addScaledVector(right, Math.cos(a) * r).addScaledVector(up2, Math.sin(a) * r).normalize();
}

const easeOut = (t) => 1 - (1 - t) * (1 - t);
