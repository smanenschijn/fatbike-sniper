import * as THREE from 'three';
import { MOUSE_SENS, PITCH_MAX, PITCH_MIN, YAW_LIMIT } from './config.js';

const EDGE = 0.55;        // cursor mode: start turning when the cursor is this far from the centre (0..1)
const EDGE_SPEED = 1.9;   // rad/s at the very edge

/**
 * Mouse / trackpad look.
 * - 'locked': pointer lock, relative movement turns the camera (classic FPS).
 * - 'cursor': fallback when pointer lock is unavailable (embedded browsers, blocked by the user):
 *   aim with the visible cursor; pushing it to the screen edge turns the camera.
 * Yaw 0 = looking north (-Z) over the square.
 */
export class Input {
  constructor(canvas) {
    this.canvas = canvas;
    this.yaw = 0;
    this.pitch = -0.05;
    this.sensScale = 1;
    this.fireDown = false;
    this.aimDown = false;
    this.firePressed = false;
    this.keysPressed = new Set();
    this.keysDown = new Set();
    this.wheel = 0;
    this._wheelAcc = 0;
    this._wheelBlock = 0;
    this.locked = false;
    this.mode = 'locked';
    this.active = false; // true while a round is running
    this.cursor = new THREE.Vector2(0, 0); // NDC, -1..1
    this.onLockChange = null;
    this.onModeChange = null;

    document.addEventListener('pointerlockchange', () => {
      this.locked = document.pointerLockElement === canvas;
      if (this.locked) this._setMode('locked');
      if (!this.locked) { this.fireDown = false; this.aimDown = false; }
      if (this.mode === 'locked') this.onLockChange?.(this.locked);
    });
    document.addEventListener('pointerlockerror', () => this._setMode('cursor'));

    document.addEventListener('mousemove', (e) => {
      if (this.mode === 'locked' && this.locked) {
        const s = MOUSE_SENS * this.sensScale;
        this.yaw = THREE.MathUtils.clamp(this.yaw - e.movementX * s, -YAW_LIMIT, YAW_LIMIT);
        this.pitch = THREE.MathUtils.clamp(this.pitch - e.movementY * s, PITCH_MIN, PITCH_MAX);
      }
      this.cursor.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
    });
    document.addEventListener('mousedown', (e) => {
      if (!this._accepting()) return;
      if (e.button === 0) { this.fireDown = true; this.firePressed = true; }
      if (e.button === 2) this.aimDown = true;
    });
    document.addEventListener('mouseup', (e) => {
      if (e.button === 0) this.fireDown = false;
      if (e.button === 2) this.aimDown = false;
    });
    document.addEventListener('contextmenu', (e) => e.preventDefault());
    // trackpads send a stream of small wheel deltas: accumulate and rate-limit weapon switching
    document.addEventListener('wheel', (e) => {
      if (!this._accepting()) return;
      const now = performance.now();
      if (now < this._wheelBlock) return;
      this._wheelAcc += e.deltaY;
      if (Math.abs(this._wheelAcc) > 40) {
        this.wheel += Math.sign(this._wheelAcc);
        this._wheelAcc = 0;
        this._wheelBlock = now + 260;
      }
    }, { passive: true });
    document.addEventListener('keydown', (e) => {
      if (!e.repeat) this.keysPressed.add(e.code);
      this.keysDown.add(e.code);
    });
    document.addEventListener('keyup', (e) => this.keysDown.delete(e.code));
    addEventListener('blur', () => { this.keysDown.clear(); this.fireDown = false; this.aimDown = false; });
  }

  _accepting() { return this.active && (this.mode === 'cursor' || this.locked); }

  _setMode(m) {
    if (this.mode === m) return;
    this.mode = m;
    this.onModeChange?.(m);
  }

  /** Try pointer lock; fall back to cursor aiming if it doesn't engage. */
  lock() {
    if (this.mode === 'cursor') return;
    try {
      const p = this.canvas.requestPointerLock?.();
      if (p && p.catch) p.catch(() => this._setMode('cursor'));
      if (!this.canvas.requestPointerLock) this._setMode('cursor');
    } catch { this._setMode('cursor'); }
    setTimeout(() => { if (!this.locked && this.active) this._setMode('cursor'); }, 600);
  }

  unlock() { if (document.pointerLockElement) document.exitPointerLock(); }

  /** Zoom: right button or holding Shift (handy on a trackpad). */
  get zoomHeld() { return this.aimDown || this.keysDown.has('ShiftLeft') || this.keysDown.has('ShiftRight'); }

  /** Per-frame: edge-turning in cursor mode. */
  update(dt) {
    if (this.mode !== 'cursor' || !this.active) return;
    const turn = (v) => (Math.abs(v) < EDGE ? 0 : Math.sign(v) * ((Math.abs(v) - EDGE) / (1 - EDGE)) ** 1.5);
    const s = EDGE_SPEED * this.sensScale * dt;
    this.yaw = THREE.MathUtils.clamp(this.yaw - turn(this.cursor.x) * s, -YAW_LIMIT, YAW_LIMIT);
    this.pitch = THREE.MathUtils.clamp(this.pitch + turn(this.cursor.y) * s * 0.7, PITCH_MIN, PITCH_MAX);
  }

  /** World-space aim direction (screen centre when locked, the cursor otherwise). */
  aimDirection(camera, out = new THREE.Vector3()) {
    if (this.mode !== 'cursor') return camera.getWorldDirection(out);
    out.set(this.cursor.x, this.cursor.y, 0.5).unproject(camera);
    return out.sub(camera.getWorldPosition(new THREE.Vector3())).normalize();
  }

  endFrame() {
    this.firePressed = false;
    this.keysPressed.clear();
    this.wheel = 0;
  }
}
