/** Tiny Web Audio synth for arcade sound effects (no external files needed). */
class Sfx {
  constructor() {
    this.ctx = null;
    this.master = null;
  }

  init() {
    if (this.ctx) { if (this.ctx.state === 'suspended') this.ctx.resume(); return; }
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.master = this.ctx.createGain();
    this.master.gain.value = 0.55;
    const comp = this.ctx.createDynamicsCompressor();
    this.master.connect(comp).connect(this.ctx.destination);
    const len = this.ctx.sampleRate * 2;
    this.noise = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
    const d = this.noise.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
  }

  get t() { return this.ctx.currentTime; }

  _noise(dur, { type = 'lowpass', freq = 1000, freqEnd = null, q = 0.7, gain = 1, attack = 0.002, delay = 0, pan = 0 } = {}) {
    if (!this.ctx) return;
    const t = this.t + delay;
    const src = this.ctx.createBufferSource();
    src.buffer = this.noise;
    const f = this.ctx.createBiquadFilter();
    f.type = type; f.frequency.setValueAtTime(freq, t); f.Q.value = q;
    if (freqEnd) f.frequency.exponentialRampToValueAtTime(freqEnd, t + dur);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(gain, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    const p = this.ctx.createStereoPanner(); p.pan.value = pan;
    src.connect(f).connect(g).connect(p).connect(this.master);
    src.start(t, Math.random()); src.stop(t + dur + 0.05);
  }

  _tone(freq, dur, { type = 'sine', freqEnd = null, gain = 0.5, attack = 0.005, delay = 0, pan = 0 } = {}) {
    if (!this.ctx) return;
    const t = this.t + delay;
    const o = this.ctx.createOscillator();
    o.type = type; o.frequency.setValueAtTime(freq, t);
    if (freqEnd) o.frequency.exponentialRampToValueAtTime(freqEnd, t + dur);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(gain, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    const p = this.ctx.createStereoPanner(); p.pan.value = pan;
    o.connect(g).connect(p).connect(this.master);
    o.start(t); o.stop(t + dur + 0.05);
  }

  shot(kind) {
    switch (kind) {
      case 'katapult':
        this._noise(0.12, { type: 'bandpass', freq: 2500, freqEnd: 600, q: 2, gain: 0.5 });
        this._tone(500, 0.12, { type: 'triangle', freqEnd: 120, gain: 0.35 });
        break;
      case 'shotgun':
        this._noise(0.45, { freq: 2200, freqEnd: 300, gain: 1.0 });
        this._tone(120, 0.25, { type: 'sine', freqEnd: 40, gain: 0.9 });
        this._noise(0.05, { type: 'highpass', freq: 3000, gain: 0.4, delay: 0.35 });
        this._noise(0.05, { type: 'highpass', freq: 2500, gain: 0.4, delay: 0.5 });
        break;
      case 'sniper':
        this._noise(0.08, { type: 'highpass', freq: 1500, gain: 1.0 });
        this._noise(0.9, { freq: 1200, freqEnd: 200, gain: 0.6, attack: 0.01 });
        this._tone(90, 0.3, { freqEnd: 35, gain: 0.8 });
        this._noise(0.04, { type: 'highpass', freq: 4000, gain: 0.3, delay: 0.55 });
        break;
      case 'bazooka':
        this._noise(0.9, { type: 'bandpass', freq: 400, freqEnd: 2500, q: 1.2, gain: 0.9, attack: 0.02 });
        this._tone(70, 0.4, { freqEnd: 30, gain: 0.8 });
        break;
    }
  }

  explosion(dist = 10) {
    const g = Math.max(0.25, 1.2 - dist / 50);
    this._noise(1.6, { freq: 900, freqEnd: 60, gain: g, attack: 0.005 });
    this._tone(65, 1.0, { freqEnd: 25, gain: g });
    this._noise(0.3, { type: 'highpass', freq: 2000, gain: g * 0.4 });
  }

  hit(head = false) {
    this._tone(320, 0.14, { type: 'square', freqEnd: 90, gain: 0.18 });
    this._noise(0.06, { type: 'bandpass', freq: 1200, gain: 0.4 });
    if (head) this._tone(1760, 0.25, { type: 'triangle', gain: 0.25, delay: 0.03 });
  }

  knockOff() {
    this._tone(200, 0.35, { type: 'sawtooth', freqEnd: 60, gain: 0.15, delay: 0.05 });
    this._noise(0.25, { freq: 800, freqEnd: 150, gain: 0.5, delay: 0.25 });
  }

  bell(pan = 0) {
    this._tone(2100, 0.5, { type: 'sine', gain: 0.18, pan });
    this._tone(2650, 0.4, { type: 'sine', gain: 0.1, pan });
    this._tone(2100, 0.5, { type: 'sine', gain: 0.16, delay: 0.14, pan });
    this._tone(2650, 0.4, { type: 'sine', gain: 0.08, delay: 0.14, pan });
  }

  whoosh() { this._noise(0.4, { type: 'bandpass', freq: 600, freqEnd: 2600, q: 3, gain: 0.35, attack: 0.15 }); }
  clank() { this._tone(900, 0.15, { type: 'square', freqEnd: 500, gain: 0.12 }); this._noise(0.08, { type: 'highpass', freq: 3000, gain: 0.3 }); }

  hurt() {
    this._tone(220, 0.35, { type: 'sawtooth', freqEnd: 70, gain: 0.3 });
    this._noise(0.2, { freq: 600, gain: 0.5 });
  }

  click() { this._noise(0.03, { type: 'highpass', freq: 3000, gain: 0.3 }); }
  reload() { this.click(); this._noise(0.05, { type: 'highpass', freq: 2200, gain: 0.3, delay: 0.25 }); }
  empty() { this._tone(1500, 0.05, { type: 'square', gain: 0.08 }); }

  cheer() {
    for (let i = 0; i < 4; i++) this._noise(1.1, { type: 'bandpass', freq: 900 + i * 350, q: 4, gain: 0.12, attack: 0.25, delay: i * 0.05 });
  }

  tick() { this._tone(1000, 0.06, { type: 'square', gain: 0.1 }); }
  go() { this._tone(660, 0.15, { type: 'square', gain: 0.15 }); this._tone(990, 0.4, { type: 'square', gain: 0.15, delay: 0.15 }); }
  end() { [523, 440, 349, 262].forEach((f, i) => this._tone(f, 0.3, { type: 'square', gain: 0.12, delay: i * 0.18 })); }
}

export const sfx = new Sfx();
