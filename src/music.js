/**
 * "Fatbike Flow" — a procedurally synthesized hip-hop track with an auto-tuned robot vocal.
 * Everything is generated live with Web Audio: drums, 808, Rhodes chords, bike bells, "skrrt" ad-libs and a
 * formant-synth singer whose pitch snaps hard to the scale (the classic auto-tune warble).
 * In bullet time the whole track goes "slowed + reverb": half tempo, lower pitch, muffled.
 */

const BPM = 92;
const STEPS_PER_LOOP = 64; // 4 bars of 16ths
const SWING = 0.16;

// A minor: Am7 – Fmaj7 – Dm7 – E7
const CHORDS = [
  [57, 60, 64, 67], // Am7
  [53, 57, 60, 64], // Fmaj7
  [50, 53, 57, 60], // Dm7
  [52, 56, 59, 62], // E7
];
const BASS = [33, 29, 26, 28];

// Vowel formants (F1, F2, F3) in Hz.
const VOWELS = {
  a: [800, 1250, 2600], e: [480, 1900, 2600], i: [300, 2300, 3000], o: [470, 820, 2600],
  u: [330, 750, 2400], ui: [450, 1600, 2500], ei: [500, 1800, 2700],
};

// Syllables: [pre-consonant, vowel, end vowel (glide) | null, post-consonant]
const S = (pre, v, glide = null, post = null) => ({ pre, v, glide, post });

// Hook A: "Fat-bike fat-bike, op het plein / ik zit met m'n ijs-je / jij komt hier niet langs / (skrrt) yeah!"
const HOOK_A = [
  [0, 76, 2, S('f', 'a', null, 't')], [2, 76, 2, S('b', 'a', 'i', 'k')], [4, 79, 2, S('f', 'a', null, 't')], [6, 76, 2, S('b', 'a', 'i', 'k')],
  [8, 74, 2, S(null, 'o', null, 'p')], [10, 72, 2, S('h', 'e', null, 't')], [12, 69, 4, S('p', 'ei', null, 'n')],
  [16, 72, 2, S(null, 'i', null, 'k')], [18, 72, 2, S('z', 'i', null, 't')], [20, 74, 2, S('m', 'e', null, 't')], [22, 76, 2, S('m', 'u', null, 'n')],
  [24, 76, 4, S(null, 'ei', null, 's')], [28, 74, 4, S('j', 'e')],
  [32, 69, 2, S('j', 'ei')], [34, 72, 2, S('k', 'o', null, 'm')], [36, 74, 2, S('h', 'i', null, 'r')], [38, 74, 2, S('n', 'i', null, 't')],
  [40, 76, 6, S('l', 'a', null, 'ng')],
  [52, 68, 3, S('j', 'e', 'a')], [56, 64, 6, S('j', 'e', 'a')],
];
// Hook B: "Tring tring, broc-co-li / trai-nings-pak, mes op zak / ik schiet je van je fiets af / yeah!"
const HOOK_B = [
  [0, 79, 2, S('t', 'i', null, 'ng')], [2, 79, 2, S('t', 'i', null, 'ng')], [4, 76, 2, S('b', 'o', null, 'k')], [6, 74, 2, S('k', 'o')], [8, 72, 4, S('l', 'i')],
  [16, 72, 2, S('t', 'ei')], [18, 72, 2, S('n', 'i', null, 's')], [20, 74, 2, S('p', 'a', null, 'k')], [22, 76, 2, S('m', 'e', null, 's')],
  [24, 76, 2, S(null, 'o', null, 'p')], [26, 74, 4, S('z', 'a', null, 'k')],
  [32, 69, 2, S(null, 'i', null, 'k')], [34, 72, 2, S('s', 'i', null, 't')], [36, 74, 2, S('j', 'e')], [38, 74, 2, S('f', 'a', null, 'n')],
  [40, 76, 2, S('j', 'e')], [42, 79, 4, S('f', 'i', null, 'ts')], [46, 76, 2, S(null, 'a', null, 'f')],
  [52, 68, 3, S('j', 'e', 'a')], [56, 64, 6, S('j', 'e', 'a')],
];

const midiHz = (m) => 440 * Math.pow(2, (m - 69) / 12);

export class Music {
  constructor(sfx) {
    this.sfx = sfx;
    this.ctx = null;
    this.running = false;
    this.intensity = 'title'; // title | game | final
    this.slow = 0;            // 0..1 (bullet time)
    this.muted = (() => { try { return localStorage.getItem('fatbike-music') === 'off'; } catch { return false; } })();
  }

  _setup() {
    if (this.ctx) return;
    this.sfx.init();
    const ctx = (this.ctx = this.sfx.ctx);
    this.out = ctx.createGain();
    this.out.gain.value = this.muted ? 0 : 0.42;
    this.lowpass = ctx.createBiquadFilter();
    this.lowpass.type = 'lowpass';
    this.lowpass.frequency.value = 20000;
    this.out.connect(this.lowpass).connect(this.sfx.comp);
    // shared reverb
    this.reverb = ctx.createConvolver();
    this.reverb.buffer = this._impulse(2.4);
    this.reverbSend = ctx.createGain();
    this.reverbSend.gain.value = 0.35;
    this.reverbSend.connect(this.reverb).connect(this.out);
    // slapback delay for the vocal
    this.delay = ctx.createDelay(1);
    this.delay.delayTime.value = (60 / BPM) * 0.75;
    const fb = ctx.createGain();
    fb.gain.value = 0.28;
    this.delay.connect(fb).connect(this.delay);
    this.delaySend = ctx.createGain();
    this.delaySend.gain.value = 0.22;
    this.delaySend.connect(this.delay);
    this.delay.connect(this.out);
    // gentle saturation for the 808
    this.shaper = ctx.createWaveShaper();
    const curve = new Float32Array(1024);
    for (let i = 0; i < 1024; i++) { const x = (i / 1023) * 2 - 1; curve[i] = Math.tanh(x * 2.2); }
    this.shaper.curve = curve;
    this.shaper.connect(this.out);
    this.noise = this.sfx.noise;
    this.lastVoiceHz = midiHz(69);
  }

  _impulse(seconds) {
    const rate = this.ctx.sampleRate;
    const len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    for (let c = 0; c < 2; c++) {
      const d = buf.getChannelData(c);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3.2);
    }
    return buf;
  }

  start() {
    this._setup();
    if (this.running) return;
    this.running = true;
    this.step = 0;
    this.loop = 0;
    this.nextTime = this.ctx.currentTime + 0.1;
    this.timer = setInterval(() => this._schedule(), 25);
  }

  stop() { clearInterval(this.timer); this.running = false; }

  setIntensity(level) { this.intensity = level; }

  toggleMute() {
    this.muted = !this.muted;
    try { localStorage.setItem('fatbike-music', this.muted ? 'off' : 'on'); } catch { /* ignore */ }
    if (this.out) this.out.gain.setTargetAtTime(this.muted ? 0 : 0.42, this.ctx.currentTime, 0.05);
    return this.muted;
  }

  /** Bullet time: slowed + reverb. */
  setSlow(on) {
    this.slow = on ? 1 : 0;
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.lowpass.frequency.setTargetAtTime(on ? 1100 : 20000, t, 0.15);
    this.reverbSend.gain.setTargetAtTime(on ? 0.75 : 0.35, t, 0.2);
  }

  get _tempo() { return this.slow ? 0.55 : 1; }
  get _pitch() { return this.slow ? 0.74 : 1; }

  _schedule() {
    const stepDur = 60 / BPM / 4 / this._tempo;
    while (this.nextTime < this.ctx.currentTime + 0.15) {
      const swing = this.step % 2 === 1 ? SWING * stepDur : 0;
      this._playStep(this.step, this.nextTime + swing, stepDur);
      this.nextTime += stepDur;
      this.step = (this.step + 1) % STEPS_PER_LOOP;
      if (this.step === 0) this.loop++;
    }
  }

  // ------------------------------------------------------------ arrangement

  _playStep(step, t, sd) {
    const bar = Math.floor(step / 16);
    const s = step % 16;
    const lvl = this.intensity;
    const drums = lvl !== 'title' || this.loop % 4 >= 2;

    // chords: on the 1 and a stab on the "and" of 3
    if (s === 0) this._chord(CHORDS[bar], t, sd * 14, 0.11);
    if (s === 10 && lvl !== 'title') this._chord(CHORDS[bar], t, sd * 3, 0.06);

    // 808 bass
    const bassHits = { 0: 6, 7: 2, 10: 4, 14: 2 };
    if (bassHits[s] !== undefined && (drums || s === 0)) {
      const note = BASS[bar] + (s === 14 ? 7 : 0);
      this._bass(note, t, sd * bassHits[s], s === 7 ? BASS[(bar + 1) % 4] : null);
    }

    if (drums) {
      const kick = [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0];
      if (kick[s] || (bar === 3 && s === 13)) this._kick(t);
      if (s === 4 || s === 12) this._snare(t);
      // hats: 8ths, 16ths later in the round, trap rolls at the end of each loop
      const sixteenths = lvl === 'final' || (lvl === 'game' && this.loop % 2 === 1);
      if (s % 2 === 0 || sixteenths) this._hat(t, s % 4 === 2 ? 0.16 : 0.09, s === 6 && bar % 2 === 1);
      if (bar === 3 && s >= 12) { this._hat(t + sd / 3, 0.07); this._hat(t + (2 * sd) / 3, 0.07); }
    } else if (s % 4 === 2) {
      this._hat(t, 0.05);
    }

    // funny bits: bike bell, skrrt, slide whistle at the turnaround
    if (bar === 1 && s === 14 && this.loop % 2 === 0) this._bell(t);
    if (bar === 3 && s === 8) this._skrrt(t);
    if (bar === 3 && s === 15 && this.loop % 4 === 3) this._whistle(t, sd * 4);

    // the auto-tuned singer
    const sing = lvl === 'title' ? this.loop % 2 === 1 : this.loop % 4 !== 0;
    if (sing) {
      const hook = this.loop % 4 === 3 ? HOOK_B : HOOK_A;
      for (const [st, midi, len, syl] of hook) if (st === step) this._voice(midi, t, len * sd, syl, lvl === 'title' ? 0.6 : 1);
    }
  }

  // ------------------------------------------------------------ instruments

  _env(g, t, peak, attack, dur, release = 0.05) {
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + attack);
    g.gain.setTargetAtTime(0.0001, t + Math.max(attack, dur - release), release / 3);
  }

  _noiseSrc(t, dur) {
    const n = this.ctx.createBufferSource();
    n.buffer = this.noise;
    n.start(t, Math.random() * 1.5);
    n.stop(t + dur + 0.1);
    return n;
  }

  _kick(t) {
    const c = this.ctx;
    const o = c.createOscillator();
    const g = c.createGain();
    o.frequency.setValueAtTime(155 * this._pitch, t);
    o.frequency.exponentialRampToValueAtTime(42 * this._pitch, t + 0.16);
    g.gain.setValueAtTime(1.0, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + 0.45 / this._tempo);
    o.connect(g).connect(this.out);
    o.start(t); o.stop(t + 0.6 / this._tempo);
  }

  _snare(t) {
    const c = this.ctx;
    for (let k = 0; k < 3; k++) { // clap layers
      const n = this._noiseSrc(t + k * 0.011, 0.2);
      const f = c.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 1500 * this._pitch; f.Q.value = 0.9;
      const g = c.createGain();
      this._env(g, t + k * 0.011, k === 2 ? 0.55 : 0.3, 0.002, k === 2 ? 0.2 : 0.03, 0.12);
      n.connect(f).connect(g);
      g.connect(this.out);
      if (k === 2) g.connect(this.reverbSend);
    }
    const o = c.createOscillator(); const og = c.createGain();
    o.frequency.setValueAtTime(220 * this._pitch, t); o.frequency.exponentialRampToValueAtTime(150 * this._pitch, t + 0.08);
    this._env(og, t, 0.25, 0.002, 0.08);
    o.connect(og).connect(this.out); o.start(t); o.stop(t + 0.2);
  }

  _hat(t, vol, open = false) {
    const c = this.ctx;
    const n = this._noiseSrc(t, open ? 0.3 : 0.06);
    const f = c.createBiquadFilter(); f.type = 'highpass'; f.frequency.value = 7500 * this._pitch;
    const g = c.createGain();
    this._env(g, t, vol, 0.001, open ? 0.25 : 0.035, open ? 0.15 : 0.03);
    n.connect(f).connect(g).connect(this.out);
  }

  _bass(midi, t, dur, glideTo) {
    const c = this.ctx;
    const o = c.createOscillator();
    o.type = 'sine';
    const f = midiHz(midi) * this._pitch;
    o.frequency.setValueAtTime(f, t);
    if (glideTo !== null) o.frequency.exponentialRampToValueAtTime(midiHz(glideTo) * this._pitch, t + dur);
    const g = c.createGain();
    this._env(g, t, 0.55, 0.005, dur, 0.08);
    o.connect(g).connect(this.shaper);
    o.start(t); o.stop(t + dur + 0.2);
  }

  _chord(notes, t, dur, vol) {
    const c = this.ctx;
    const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2200;
    const trem = c.createGain(); trem.gain.value = 1;
    const lfo = c.createOscillator(); lfo.frequency.value = 4.5;
    const lfoG = c.createGain(); lfoG.gain.value = 0.25;
    lfo.connect(lfoG).connect(trem.gain);
    lfo.start(t); lfo.stop(t + dur + 0.5);
    lp.connect(trem);
    trem.connect(this.out);
    trem.connect(this.reverbSend);
    notes.forEach((m, i) => {
      for (const [type, mul, v] of [['triangle', 1, 1], ['sine', 2, 0.35]]) {
        const o = c.createOscillator();
        o.type = type;
        o.frequency.value = midiHz(m + 12) * mul * this._pitch;
        o.detune.value = (i - 1.5) * 4;
        const g = c.createGain();
        this._env(g, t + i * 0.008, vol * v, 0.01, dur, 0.4);
        o.connect(g).connect(lp);
        o.start(t); o.stop(t + dur + 0.6);
      }
    });
  }

  _bell(t) {
    const c = this.ctx;
    for (const dt of [0, 0.14]) {
      for (const [f, v] of [[2093, 0.12], [2637, 0.07], [4186, 0.03]]) {
        const o = c.createOscillator(); o.frequency.value = f * this._pitch;
        const g = c.createGain();
        this._env(g, t + dt, v, 0.002, 0.5, 0.4);
        o.connect(g); g.connect(this.out); g.connect(this.reverbSend);
        o.start(t + dt); o.stop(t + dt + 0.8);
      }
    }
  }

  _skrrt(t) {
    const c = this.ctx;
    const o = c.createOscillator(); o.type = 'sawtooth';
    o.frequency.setValueAtTime(520 * this._pitch, t);
    o.frequency.exponentialRampToValueAtTime(140 * this._pitch, t + 0.32);
    const am = c.createOscillator(); am.frequency.value = 38; // the rolled "rrr"
    const amG = c.createGain(); amG.gain.value = 0.5;
    const g = c.createGain(); g.gain.value = 0;
    am.connect(amG).connect(g.gain);
    const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = 3;
    bp.frequency.setValueAtTime(2400, t); bp.frequency.exponentialRampToValueAtTime(700, t + 0.32);
    const env = c.createGain();
    this._env(env, t, 0.22, 0.01, 0.34, 0.06);
    const n = this._noiseSrc(t, 0.05);
    const ng = c.createGain(); this._env(ng, t, 0.25, 0.002, 0.05);
    const nf = c.createBiquadFilter(); nf.type = 'highpass'; nf.frequency.value = 3500;
    n.connect(nf).connect(ng).connect(this.out); // the "sk"
    o.connect(bp).connect(g).connect(env).connect(this.out);
    env.connect(this.delaySend);
    o.start(t); am.start(t); o.stop(t + 0.45); am.stop(t + 0.45);
  }

  _whistle(t, dur) {
    const c = this.ctx;
    const o = c.createOscillator(); o.type = 'sine';
    o.frequency.setValueAtTime(700 * this._pitch, t);
    o.frequency.exponentialRampToValueAtTime(2100 * this._pitch, t + dur);
    const g = c.createGain();
    this._env(g, t, 0.08, 0.05, dur, 0.05);
    o.connect(g).connect(this.out);
    o.start(t); o.stop(t + dur + 0.1);
  }

  /** Formant-synth singer with hard pitch snapping (auto-tune). */
  _voice(midi, t, dur, syl, vol = 1) {
    const c = this.ctx;
    const target = midiHz(midi) * this._pitch;
    const pre = syl.pre ? 0.05 : 0;
    const vt = t + pre;
    const bus = c.createGain();
    bus.connect(this.out);
    bus.connect(this.reverbSend);
    bus.connect(this.delaySend);
    const env = c.createGain();
    this._env(env, vt, 0.33 * vol, 0.015, dur - pre, 0.06);
    env.connect(bus);

    // source: two detuned saws + a sub octave, snapping from the previous note (that warble!)
    const formantIn = c.createGain();
    for (const [type, mul, det, v] of [['sawtooth', 1, -6, 0.5], ['sawtooth', 1, 7, 0.5], ['square', 0.5, 0, 0.18]]) {
      const o = c.createOscillator();
      o.type = type;
      o.detune.value = det;
      o.frequency.setValueAtTime(this.lastVoiceHz * mul, vt);
      o.frequency.setTargetAtTime(target * mul, vt, 0.012);
      const g = c.createGain(); g.gain.value = v;
      o.connect(g).connect(formantIn);
      o.start(vt); o.stop(vt + dur + 0.2);
    }
    this.lastVoiceHz = target;

    // vowel formants (optionally gliding, e.g. "bike" = a -> i, "yeah" = e -> a)
    const v0 = VOWELS[syl.v] || VOWELS.a;
    const v1 = syl.glide ? VOWELS[syl.glide] : syl.v === 'ei' ? VOWELS.i : null;
    [1, 0.55, 0.28].forEach((gain, k) => {
      const f = c.createBiquadFilter();
      f.type = 'bandpass';
      f.Q.value = k === 0 ? 6 : 9;
      f.frequency.setValueAtTime(v0[k], vt);
      if (v1) f.frequency.linearRampToValueAtTime(v1[k], vt + dur * 0.75);
      const g = c.createGain(); g.gain.value = gain * 2.2;
      formantIn.connect(f).connect(g).connect(env);
    });

    // consonants
    if (syl.pre) this._consonant(syl.pre, t, vol);
    if (syl.post) this._consonant(syl.post, vt + dur * 0.8, vol * 0.7);
  }

  _consonant(ch, t, vol) {
    const c = this.ctx;
    const spec = {
      f: ['highpass', 3500, 0.05, 0.2], s: ['highpass', 5000, 0.07, 0.22], z: ['bandpass', 4500, 0.06, 0.2], h: ['highpass', 1800, 0.04, 0.1],
      t: ['bandpass', 3500, 0.015, 0.35], k: ['bandpass', 1800, 0.02, 0.35], p: ['bandpass', 900, 0.015, 0.35], b: ['lowpass', 500, 0.02, 0.35],
      ts: ['highpass', 4500, 0.06, 0.25], j: ['bandpass', 2600, 0.03, 0.12], l: ['lowpass', 900, 0.03, 0.1], m: ['lowpass', 400, 0.04, 0.15],
      n: ['lowpass', 500, 0.04, 0.12], ng: ['lowpass', 400, 0.05, 0.12], r: ['bandpass', 1200, 0.04, 0.12],
    }[ch];
    if (!spec) return;
    const [type, freq, dur, v] = spec;
    const n = this._noiseSrc(t, dur);
    const f = c.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = 1.5;
    const g = c.createGain();
    this._env(g, t, v * vol, 0.003, dur, dur * 0.6);
    n.connect(f).connect(g).connect(this.out);
  }
}
