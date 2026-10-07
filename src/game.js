import * as THREE from 'three';
import { HEARTS, ROUND_TIME, SCORE, difficulty } from './config.js';
import { sfx } from './audio.js';

const MULTI_NAMES = { 2: 'DUBBEL!', 3: 'TRIPLE!', 4: 'QUADRA!', 5: 'MEGA!' };

export class Game {
  constructor({ scene, camera, world, riders, weapons, effects, hud }) {
    Object.assign(this, { scene, camera, world, riders, weapons, effects, hud });
    this.state = 'idle';
    this.projectiles = [];
    this.tracers = [];
    this.onEnd = null;
    this.stoneGeo = new THREE.IcosahedronGeometry(0.06, 1);
    this.stoneMat = new THREE.MeshStandardMaterial({ color: 0x8c8a83, roughness: 0.85 });
    weapons.ctx = {
      fireHitscan: (w, origin, dirs, muzzle) => this.fireHitscan(w, origin, dirs, muzzle),
      fireProjectile: (w, muzzle, origin, fwd) => this.fireProjectile(w, muzzle, origin, fwd),
      ejectShell: (shell) => this.ejectShell(shell),
      onEmpty: () => this.hud.message('LEEG!', 500),
    };
    riders.hooks.onPlayerHit = (k) => this.onPlayerHit(k);
  }

  reset() {
    this.riders.clear();
    this.effects.clear();
    for (const p of this.projectiles) this.scene.remove(p.mesh);
    this.projectiles = [];
    this.weapons.reset();
    this.score = 0;
    this.time = ROUND_TIME;
    this.hearts = HEARTS;
    this.stats = { shots: 0, hits: 0, kills: 0, headshots: 0, knives: 0, bestMulti: 1, bosses: 0 };
    this.countdown = 3.6;
    this.lastCount = null;
    this.state = 'countdown';
    this.hud.setHearts(this.hearts, HEARTS);
    this.hud.setScore(0);
    this.hud.setTime(this.time);
  }

  get elapsed() { return ROUND_TIME - this.time; }

  // ------------------------------------------------------------ shooting

  fireHitscan(w, origin, dirs, muzzle) {
    this.stats.shots++;
    const perRider = new Map();
    let anyHit = false;
    let firstEnd = null;
    for (const dir of dirs) {
      const wh = this.world.raycast(origin, dir, w.range);
      const limit = wh ? wh.distance : w.range;
      const rh = this.riders.raycast(origin, dir, limit);
      const kh = this.riders.raycastKnives(origin, dir, limit);
      if (kh.length && (!rh.length || kh[0].t < rh[0].t)) {
        this.knifeShot(kh[0].knife);
        anyHit = true;
        continue;
      }
      const hits = w.pierce ? dedupe(rh).slice(0, w.pierce) : rh.slice(0, 1);
      for (const h of hits) {
        const e = perRider.get(h.rider) || { dmg: 0, head: false, point: h.point, dir };
        e.dmg = Math.min(e.dmg + w.damage, w.maxPerRider || Infinity);
        e.head = e.head || h.part === 'head';
        perRider.set(h.rider, e);
      }
      const end = hits.length && !w.pierce ? hits[0].point : (wh ? wh.point : origin.clone().addScaledVector(dir, limit));
      if (!firstEnd) firstEnd = end;
      if (!hits.length && wh) this.effects.puff(wh.point, 0xd8cbb5, w.pellets > 1 ? 1 : 4, w.pellets > 1 ? 0.25 : 0.5);
    }
    if (muzzle) {
      this.effects.muzzleFlash(muzzle, w.key === 'shotgun' ? 0.7 : 0.55);
      if (w.key === 'sniper' && firstEnd) this.tracer(muzzle, firstEnd);
    }
    const kills = [];
    for (const [r, e] of perRider) {
      anyHit = true;
      this.hud.hit(e.head);
      sfx.hit(e.head);
      const power = w.key === 'shotgun' ? 9 : w.key === 'sniper' ? 8 : 5;
      if (this.riders.damage(r, e.dmg, { dir: e.dir, power })) kills.push({ rider: r, head: e.head, point: e.point });
    }
    if (kills.length) this.scoreKills(kills);
    this.afterShot(anyHit);
  }

  fireProjectile(w, muzzle, origin, fwd) {
    this.stats.shots++;
    const wh = this.world.raycast(origin, fwd, 250);
    const rh = this.riders.raycast(origin, fwd, wh ? wh.distance : 250);
    const aimDist = rh.length ? rh[0].t : wh ? wh.distance : 120;
    const aim = origin.clone().addScaledVector(fwd, aimDist);
    const p = w.projectile;
    if (rh.length && rh[0].rider.alive) { // arcade lead: aim where the rider will be
      const r = rh[0].rider;
      const rv = new THREE.Vector3(Math.cos(r.yaw), 0, -Math.sin(r.yaw)).multiplyScalar(r.speed);
      const base = aim.clone();
      for (let i = 0; i < 2; i++) aim.copy(base).addScaledVector(rv, aim.distanceTo(muzzle) / p.speed);
    }
    const dir = aim.clone().sub(muzzle).normalize();
    const T = aim.distanceTo(muzzle) / p.speed;
    const vel = dir.multiplyScalar(p.speed).add(new THREE.Vector3(0, 0.5 * p.gravity * T, 0)); // arc lands on the crosshair
    let mesh;
    if (w.key === 'bazooka') {
      mesh = w.parts.rocket.clone(true);
      mesh.visible = true;
      const holder = new THREE.Group();
      holder.add(mesh);
      // rocket part sits ~0.75 m forward in its own frame; recentre it
      mesh.position.set(-0.78, 0, 0);
      mesh = holder;
      this.effects.puff(muzzle.clone().addScaledVector(fwd, -1.2), 0xcccccc, 6, 0.8); // back blast
      this.effects.flashLight(muzzle, 0xffaa55, 8, 0.1);
    } else {
      mesh = new THREE.Mesh(this.stoneGeo, this.stoneMat);
      mesh.castShadow = true;
    }
    mesh.position.copy(muzzle);
    this.scene.add(mesh);
    this.projectiles.push({ mesh, vel, w, age: 0, trail: 0, hitAny: false });
  }

  _orientRocket(p) {
    const d = p.vel.clone().normalize();
    p.mesh.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), d);
  }

  updateProjectiles(dt) {
    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      const p = this.projectiles[i];
      const def = p.w.projectile;
      p.age += dt;
      const prev = p.mesh.position.clone();
      p.vel.y -= def.gravity * dt;
      const next = prev.clone().addScaledVector(p.vel, dt);
      const seg = next.clone().sub(prev);
      const len = seg.length();
      const dir = seg.divideScalar(len || 1);
      if (p.w.key === 'bazooka') {
        this._orientRocket(p);
        p.trail -= dt;
        if (p.trail <= 0) { p.trail = 0.025; this.effects.smokeTrail(prev); }
      } else {
        p.mesh.rotation.x += dt * 15;
      }
      const wh = this.world.raycast(prev, dir, len + def.radius);
      const rh = this.riders.raycast(prev, dir, wh ? wh.distance : len + def.radius, 0.2);
      const kh = this.riders.raycastKnives(prev, dir, len + 0.2);
      let done = false;
      if (kh.length) { this.knifeShot(kh[0].knife); p.hitAny = true; }
      if (rh.length) {
        const h = rh[0];
        if (def.explode) { this.explode(h.point, p); done = true; }
        else {
          p.hitAny = true;
          this.hud.hit(h.part === 'head');
          sfx.hit(h.part === 'head');
          if (this.riders.damage(h.rider, def.damage, { dir, power: 6 })) this.scoreKills([{ rider: h.rider, head: h.part === 'head', point: h.point }]);
          done = true;
        }
      } else if (wh || next.y < 0 || p.age > 4) {
        const at = wh ? wh.point : next;
        if (def.explode) this.explode(at, p);
        else this.effects.puff(at, 0xd8cbb5, 3, 0.35);
        done = true;
      }
      if (done) {
        this.scene.remove(p.mesh);
        this.projectiles.splice(i, 1);
        if (!def.explode) this.afterShot(p.hitAny, true);
      } else {
        p.mesh.position.copy(next);
      }
    }
  }

  explode(point, p) {
    this.effects.explosion(point);
    sfx.explosion(point.distanceTo(this.camera.position));
    const R = p.w.projectile.explode;
    const kills = [];
    for (const r of this.riders.inRadius(point, R)) {
      const dir = r.root.position.clone().sub(point).setY(0);
      if (dir.lengthSq() < 0.01) dir.set(Math.random() - 0.5, 0, Math.random() - 0.5);
      dir.normalize();
      r.hp = 0;
      this.riders.knockOff(r, { dir, power: 10, explode: true });
      kills.push({ rider: r, head: false, point: r.root.position.clone().setY(1.2) });
    }
    for (const k of [...this.riders.knives]) if (k.mesh.position.distanceTo(point) < R) this.knifeShot(k);
    if (kills.length) { this.hud.hit(false); this.scoreKills(kills); }
    this.afterShot(kills.length > 0, true);
  }

  afterShot(hit, projectile = false) {
    if (hit) this.stats.hits++;
    else if (this.state === 'playing' && Math.random() < 0.7) this.riders.retaliate();
  }

  knifeShot(k) {
    this.riders.destroyKnife(k);
    this.stats.knives++;
    this.addScore(SCORE.knife, k.mesh.position, 'MES GERAAKT! +' + SCORE.knife, 'bonus');
    sfx.clank();
    this.hud.hit(false);
  }

  ejectShell(shell) {
    if (!shell) return;
    const c = shell.clone(true);
    c.visible = true;
    const pos = shell.getWorldPosition(new THREE.Vector3());
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(this.camera.quaternion);
    this.effects.addDebris(c, pos, right.multiplyScalar(2.5).add(new THREE.Vector3(0, 2.5, 0)),
      new THREE.Vector3(Math.random() * 20, Math.random() * 20, 0), { radius: 0.02, life: 1.5, bounce: 0.5 });
  }

  tracer(from, to) {
    const g = new THREE.BufferGeometry().setFromPoints([from, to]);
    const m = new THREE.LineBasicMaterial({ color: 0xfff2b0, transparent: true, opacity: 0.9 });
    const line = new THREE.Line(g, m);
    this.scene.add(line);
    this.tracers.push({ line, age: 0 });
  }

  // ------------------------------------------------------------ scoring

  addScore(n, pos, text, cls = '') {
    this.score = Math.max(0, this.score + n);
    if (text) this.effects.popup(pos.clone().add(new THREE.Vector3(0, 0.6, 0)), text, cls, 1.1);
  }

  scoreKills(kills) {
    let bodies = 0;
    for (const k of kills) {
      const r = k.rider;
      const n = r.type === 'duo' ? 2 : 1;
      bodies += n;
      let pts = r.type === 'boss' ? SCORE.boss : SCORE.kill * n * (r.type === 'wheelie' ? SCORE.wheelieMul : 1);
      if (k.head) pts += SCORE.headshot;
      this.stats.kills += n;
      if (k.head) this.stats.headshots++;
      if (r.type === 'boss') this.stats.bosses++;
      const label = r.type === 'boss' ? `SPEAKER-BAAS! +${pts}` : k.head ? `HEADSHOT! +${pts}` : `+${pts}`;
      this.addScore(pts, k.point, label, k.head || r.type === 'boss' ? 'bonus' : '');
    }
    if (bodies >= 2) {
      const bonus = SCORE.multi * (bodies - 1);
      this.score += bonus;
      this.stats.bestMulti = Math.max(this.stats.bestMulti, bodies);
      this.effects.screenPopup(`${MULTI_NAMES[Math.min(bodies, 5)]} +${bonus}`, 'big', 0.5, 0.3, 1.3);
      sfx.cheer();
    }
  }

  onPlayerHit(knife) {
    if (this.state !== 'playing') return;
    this.hearts--;
    this.hud.setHearts(this.hearts, HEARTS);
    this.hud.hurt();
    this.effects.addShake(1.0);
    sfx.hurt();
    this.effects.screenPopup(['AU!', 'AUWW!', 'NEE, MIJN IJSJE!'][HEARTS - 1 - this.hearts] || 'AU!', 'bad', 0.5, 0.55, 1.0);
    if (this.hearts === HEARTS - 1) this.world.knockOverIjsje(knife.vel.clone().setY(0).normalize());
    if (this.hearts <= 0) this.end('NEERGESTOKEN!');
  }

  // ------------------------------------------------------------ loop

  update(dt, input) {
    for (let i = this.tracers.length - 1; i >= 0; i--) {
      const t = this.tracers[i];
      t.age += dt;
      t.line.material.opacity = 0.9 * (1 - t.age / 0.18);
      if (t.age > 0.18) { this.scene.remove(t.line); t.line.geometry.dispose(); this.tracers.splice(i, 1); }
    }
    if (this.state === 'countdown') {
      this.countdown -= dt;
      const c = Math.ceil(this.countdown - 0.6);
      if (c !== this.lastCount) {
        this.lastCount = c;
        if (c > 0) { this.hud.message(String(c), 800); sfx.tick(); } else { this.hud.message('SCHIETEN!', 900); sfx.go(); }
      }
      if (this.countdown <= 0.6) this.state = 'playing';
      this.weapons.update(dt, input);
      return;
    }
    if (this.state !== 'playing') return;
    const prevSec = Math.ceil(this.time);
    this.time -= dt;
    if (Math.ceil(this.time) !== prevSec && this.time <= 5 && this.time > 0) sfx.tick();
    const diff = difficulty(Math.min(1, this.elapsed / ROUND_TIME));
    this.riders.update(dt, diff, this.elapsed);
    this.weapons.update(dt, input);
    this.weapons.tryFire(input);
    this.updateProjectiles(dt);
    this.hud.setScore(this.score);
    this.hud.setTime(this.time);
    if (this.time <= 0) this.end('TIJD OP!');
  }

  end(reason) {
    if (this.state === 'ended') return;
    this.state = 'ended';
    sfx.end();
    this.onEnd?.(reason, this.score, this.stats);
  }
}

function dedupe(hits) {
  const seen = new Set();
  return hits.filter((h) => (seen.has(h.rider) ? false : (seen.add(h.rider), true)));
}
