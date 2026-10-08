import * as THREE from 'three';
import { GRAVITY } from './config.js';

function spriteTexture(draw, size = 128) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  draw(c.getContext('2d'), size);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

const TEX = {
  puff: () => spriteTexture((g, s) => {
    const grad = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
    grad.addColorStop(0, 'rgba(255,255,255,0.9)');
    grad.addColorStop(0.5, 'rgba(255,255,255,0.5)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grad; g.fillRect(0, 0, s, s);
  }),
  flash: () => spriteTexture((g, s) => {
    g.translate(s / 2, s / 2);
    g.fillStyle = 'rgba(255,240,170,1)';
    g.beginPath();
    for (let i = 0; i < 16; i++) {
      const r = i % 2 ? s * 0.18 : s * 0.5;
      const a = (i / 16) * Math.PI * 2;
      g.lineTo(Math.cos(a) * r, Math.sin(a) * r);
    }
    g.fill();
    const grad = g.createRadialGradient(0, 0, 0, 0, 0, s * 0.3);
    grad.addColorStop(0, 'rgba(255,255,255,1)'); grad.addColorStop(1, 'rgba(255,200,80,0)');
    g.fillStyle = grad; g.beginPath(); g.arc(0, 0, s * 0.3, 0, Math.PI * 2); g.fill();
  }),
  star: () => spriteTexture((g, s) => {
    g.translate(s / 2, s / 2);
    g.fillStyle = '#ffd23f'; g.strokeStyle = '#121216'; g.lineWidth = s * 0.06;
    g.beginPath();
    for (let i = 0; i < 10; i++) {
      const r = i % 2 ? s * 0.2 : s * 0.45;
      const a = (i / 10) * Math.PI * 2 - Math.PI / 2;
      g.lineTo(Math.cos(a) * r, Math.sin(a) * r);
    }
    g.closePath(); g.fill(); g.stroke();
  }, 64),
};

export class Effects {
  constructor(scene, camera, hudPopups) {
    this.scene = scene;
    this.camera = camera;
    this.popupLayer = hudPopups;
    this.tex = Object.fromEntries(Object.entries(TEX).map(([k, f]) => [k, f()]));
    this.debris = [];
    this.particles = [];
    this.lights = [];
    this.popups = [];
    this.shake = 0;
    this._v = new THREE.Vector3();
  }

  // ------------------------------------------------------------ debris (slapstick physics)

  /** Turn `obj` into a tumbling rigid body around `center` (world space). */
  addDebris(obj, center, vel, angVel, { radius = 0.3, life = 3.2, bounce = 0.38, stars = false, onLand = null } = {}) {
    const g = new THREE.Group();
    g.position.copy(center);
    this.scene.add(g);
    g.attach(obj);
    obj.traverse((o) => { if (o.isMesh) o.castShadow = false; });
    this.debris.push({ g, vel: vel.clone(), ang: angVel.clone(), radius, life, age: 0, bounce, stars, landed: false, onLand });
    return g;
  }

  _updateDebris(dt) {
    const q = new THREE.Quaternion();
    for (let i = this.debris.length - 1; i >= 0; i--) {
      const d = this.debris[i];
      d.age += dt;
      d.vel.y -= GRAVITY * 1.5 * dt;
      d.g.position.addScaledVector(d.vel, dt);
      const w = d.ang.length();
      if (w > 1e-4) {
        q.setFromAxisAngle(this._v.copy(d.ang).divideScalar(w), w * dt);
        d.g.quaternion.premultiply(q);
      }
      if (d.g.position.y < d.radius) {
        d.g.position.y = d.radius;
        if (d.vel.y < -1.5 && !d.landed) {
          d.landed = true;
          this.puff(d.g.position.clone().setY(0.1), 0x8a7a6a, 4, 0.5);
          if (d.stars) this.stars(d.g.position.clone().add(new THREE.Vector3(0, d.radius + 0.4, 0)));
          d.onLand?.();
        }
        d.vel.y = Math.abs(d.vel.y) * d.bounce;
        d.vel.x *= 0.72; d.vel.z *= 0.72;
        d.ang.multiplyScalar(0.7);
      }
      if (d.age > d.life - 0.8) d.g.position.y -= dt * 0.8; // sink away
      if (d.age > d.life) {
        this.scene.remove(d.g);
        this.debris.splice(i, 1);
      }
    }
  }

  // ------------------------------------------------------------ particles

  _sprite(tex, color, size, additive = false, opacity = 1) {
    const m = new THREE.SpriteMaterial({ map: tex, color, transparent: true, depthWrite: false, opacity,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending, fog: true });
    const s = new THREE.Sprite(m);
    s.scale.setScalar(size);
    this.scene.add(s);
    return s;
  }

  _particle(sprite, { vel = new THREE.Vector3(), grow = 1, life = 1, gravity = 0, fade = true, drag = 1 }) {
    this.particles.push({ s: sprite, vel, grow, life, age: 0, gravity, fade, drag, base: sprite.scale.x, op: sprite.material.opacity });
  }

  puff(pos, color = 0xd8d0c0, n = 5, size = 0.6) {
    for (let i = 0; i < n; i++) {
      const s = this._sprite(this.tex.puff, color, size * (0.6 + Math.random() * 0.6), false, 0.8);
      s.position.copy(pos).add(new THREE.Vector3((Math.random() - 0.5) * 0.4, Math.random() * 0.3, (Math.random() - 0.5) * 0.4));
      this._particle(s, { vel: new THREE.Vector3((Math.random() - 0.5) * 1.5, 0.5 + Math.random(), (Math.random() - 0.5) * 1.5),
        grow: 2.2, life: 0.6 + Math.random() * 0.5, drag: 0.92 });
    }
  }

  muzzleFlash(pos, size = 0.5) {
    const s = this._sprite(this.tex.flash, 0xffffff, size, true);
    s.material.rotation = Math.random() * Math.PI;
    s.position.copy(pos);
    this._particle(s, { life: 0.06, grow: 1.4 });
    this.flashLight(pos, 0xffcc66, 6, 0.07);
  }

  flashLight(pos, color, intensity, life, distance = 12) {
    const l = new THREE.PointLight(color, intensity, distance, 1.5);
    l.position.copy(pos);
    this.scene.add(l);
    this.lights.push({ l, life, age: 0, i0: intensity });
  }

  smokeTrail(pos) {
    const s = this._sprite(this.tex.puff, 0xbbbbbb, 0.35, false, 0.6);
    s.position.copy(pos);
    this._particle(s, { vel: new THREE.Vector3(0, 0.4, 0), grow: 3, life: 0.9 });
  }

  explosion(pos) {
    // fireballs
    for (let i = 0; i < 14; i++) {
      const s = this._sprite(this.tex.puff, i % 3 ? 0xffa030 : 0xfff0a0, 1.2 + Math.random(), true);
      s.position.copy(pos).add(new THREE.Vector3((Math.random() - 0.5) * 1.2, Math.random() * 1.2, (Math.random() - 0.5) * 1.2));
      this._particle(s, { vel: new THREE.Vector3((Math.random() - 0.5) * 7, Math.random() * 6, (Math.random() - 0.5) * 7),
        grow: 3, life: 0.45 + Math.random() * 0.3, drag: 0.85 });
    }
    // smoke
    for (let i = 0; i < 16; i++) {
      const s = this._sprite(this.tex.puff, 0x4a4440, 1.5 + Math.random(), false, 0.85);
      s.position.copy(pos).add(new THREE.Vector3((Math.random() - 0.5) * 2, Math.random() * 1.5, (Math.random() - 0.5) * 2));
      this._particle(s, { vel: new THREE.Vector3((Math.random() - 0.5) * 3, 1.5 + Math.random() * 2.5, (Math.random() - 0.5) * 3),
        grow: 2.8, life: 1.6 + Math.random(), drag: 0.95 });
    }
    // sparks
    for (let i = 0; i < 20; i++) {
      const s = this._sprite(this.tex.puff, 0xffd060, 0.15, true);
      s.position.copy(pos);
      this._particle(s, { vel: new THREE.Vector3((Math.random() - 0.5) * 18, 4 + Math.random() * 10, (Math.random() - 0.5) * 18),
        grow: 0.5, life: 0.9, gravity: GRAVITY });
    }
    this.flashLight(pos.clone().add(new THREE.Vector3(0, 1, 0)), 0xff9a40, 60, 0.35, 30);
    this.popup(pos.clone().add(new THREE.Vector3(0, 2, 0)), 'BOEM!', 'boem', 0.9);
    this.addShake(0.8);
  }

  stars(pos) {
    const group = [];
    for (let i = 0; i < 5; i++) {
      const s = this._sprite(this.tex.star, 0xffffff, 0.28);
      group.push(s);
    }
    this.particles.push({ starRing: group, center: pos, age: 0, life: 1.6 });
  }

  _updateParticles(dt) {
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.age += dt;
      const k = p.age / p.life;
      if (p.starRing) {
        p.starRing.forEach((s, j) => {
          const a = p.age * 5 + (j / p.starRing.length) * Math.PI * 2;
          s.position.set(p.center.x + Math.cos(a) * 0.45, p.center.y + Math.sin(p.age * 6 + j) * 0.06, p.center.z + Math.sin(a) * 0.45);
          s.material.opacity = 1 - Math.max(0, k - 0.7) / 0.3;
        });
        if (k >= 1) { p.starRing.forEach((s) => { this.scene.remove(s); s.material.dispose(); }); this.particles.splice(i, 1); }
        continue;
      }
      p.vel.y -= p.gravity * dt;
      p.vel.multiplyScalar(Math.pow(p.drag, dt * 60));
      p.s.position.addScaledVector(p.vel, dt);
      p.s.scale.setScalar(p.base * (1 + (p.grow - 1) * k));
      if (p.fade) p.s.material.opacity = p.op * (1 - k);
      if (k >= 1) {
        this.scene.remove(p.s);
        p.s.material.dispose();
        this.particles.splice(i, 1);
      }
    }
    for (let i = this.lights.length - 1; i >= 0; i--) {
      const l = this.lights[i];
      l.age += dt;
      l.l.intensity = l.i0 * Math.max(0, 1 - l.age / l.life);
      if (l.age >= l.life) { this.scene.remove(l.l); l.l.dispose(); this.lights.splice(i, 1); }
    }
  }

  // ------------------------------------------------------------ DOM popups / bubbles

  popup(worldPos, text, cls = '', life = 1.0, rise = 1.2) {
    const el = document.createElement('div');
    el.className = 'popup ' + cls;
    el.textContent = text;
    this.popupLayer.appendChild(el);
    this.popups.push({ el, pos: worldPos.clone(), age: 0, life, rise, follow: null });
  }

  /** Screen-anchored popup (fractions of the viewport). */
  screenPopup(text, cls = '', x = 0.5, y = 0.42, life = 1.0) {
    const el = document.createElement('div');
    el.className = 'popup ' + cls;
    el.textContent = text;
    this.popupLayer.appendChild(el);
    this.popups.push({ el, screen: [x, y], age: 0, life, rise: 0.04 });
  }

  bubble(target, offset, text, warn = false, life = 1.8) {
    const el = document.createElement('div');
    el.className = 'bubble' + (warn ? ' warn' : '');
    el.textContent = text;
    this.popupLayer.appendChild(el);
    this.popups.push({ el, follow: target, offset: offset.clone(), age: 0, life, rise: 0, isBubble: true });
  }

  _updatePopups(dt) {
    const w = innerWidth, h = innerHeight;
    for (let i = this.popups.length - 1; i >= 0; i--) {
      const p = this.popups[i];
      p.age += dt;
      const k = p.age / p.life;
      if (p.screen) {
        p.el.style.left = `${p.screen[0] * w}px`;
        p.el.style.top = `${(p.screen[1] - p.rise * k) * h}px`;
      } else {
        if (p.follow) {
          if (!p.follow.parent) p.age = p.life;
          p.follow.getWorldPosition(this._v).add(p.offset);
        } else {
          this._v.copy(p.pos).add(new THREE.Vector3(0, p.rise * k, 0));
        }
        const dist = this._v.distanceTo(this.camera.position);
        this._v.project(this.camera);
        const visible = this._v.z < 1 && Math.abs(this._v.x) < 1.2 && Math.abs(this._v.y) < 1.2;
        p.el.style.display = visible ? '' : 'none';
        p.el.style.left = `${(this._v.x * 0.5 + 0.5) * w}px`;
        p.el.style.top = `${(-this._v.y * 0.5 + 0.5) * h}px`;
        if (p.isBubble) p.el.style.transform = `translate(-50%, -100%) scale(${THREE.MathUtils.clamp(14 / dist, 0.55, 1.2)})`;
      }
      const pop = Math.min(1, p.age / 0.1);
      p.el.style.opacity = k > 0.75 ? String(1 - (k - 0.75) / 0.25) : '1';
      if (!p.isBubble && !p.el.classList.contains('boem')) p.el.style.scale = String(0.6 + 0.4 * pop);
      if (k >= 1) { p.el.remove(); this.popups.splice(i, 1); }
    }
  }

  addShake(a) { this.shake = Math.min(1.2, this.shake + a); }

  clear() {
    for (const d of this.debris) this.scene.remove(d.g);
    for (const p of this.particles) {
      if (p.starRing) p.starRing.forEach((s) => this.scene.remove(s));
      else this.scene.remove(p.s);
    }
    for (const l of this.lights) this.scene.remove(l.l);
    for (const p of this.popups) p.el.remove();
    this.debris = []; this.particles = []; this.lights = []; this.popups = [];
    this.shake = 0;
  }

  update(dt) {
    this._updateDebris(dt);
    this._updateParticles(dt);
    this._updatePopups(dt);
    this.shake = Math.max(0, this.shake - dt * 2.5);
  }
}
