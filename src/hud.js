const HEART = `<svg viewBox="0 0 32 30"><path d="M16 29 C16 29 1 19 1 9.5 C1 4.5 5 1 9.5 1 C12.5 1 14.8 2.7 16 5 C17.2 2.7 19.5 1 22.5 1 C27 1 31 4.5 31 9.5 C31 19 16 29 16 29Z" fill="#e63946" stroke="#121216" stroke-width="2.5"/><ellipse cx="9" cy="8" rx="3" ry="2" fill="#fff" opacity=".6"/></svg>`;

const $ = (id) => document.getElementById(id);

export class Hud {
  constructor() {
    this.el = $('hud');
    this.score = $('score');
    this.timer = $('timer');
    this.hearts = $('hearts');
    this.crosshair = $('crosshair');
    this.hitmarker = $('hitmarker');
    this.scope = $('scope');
    this.weapons = $('weapons');
    this.reload = $('reload');
    this.reloadBar = $('reload-bar');
    this.damage = $('damage');
    this.center = $('center-msg');
    this.popups = $('popups');
    this._last = {};
  }

  show(on) { this.el.classList.toggle('hidden', !on); }

  setHearts(n, max) {
    if (this._last.hearts === n) return;
    this._last.hearts = n;
    this.hearts.innerHTML = Array.from({ length: max }, (_, i) => HEART.replace('<svg', `<svg class="${i < n ? '' : 'lost'}"`)).join('');
  }

  setScore(s) {
    if (this._last.score === s) return;
    this._last.score = s;
    this.score.textContent = s;
    this.score.animate([{ transform: 'scale(1.25)' }, { transform: 'scale(1)' }], { duration: 180 });
  }

  setTime(t) {
    const s = Math.max(0, Math.ceil(t));
    if (this._last.time === s) return;
    this._last.time = s;
    this.timer.textContent = s;
    this.timer.classList.toggle('urgent', s <= 10);
  }

  setWeapons(st) {
    const key = JSON.stringify(st.list) + st.index;
    if (this._last.weapons !== key) {
      this._last.weapons = key;
      this.weapons.innerHTML = st.list.map((w, i) => {
        const ammo = w.mag === Infinity ? '∞' : `${w.ammo}<small>/${w.reserve === Infinity ? '∞' : w.reserve}</small>`;
        return `<div class="wslot ${i === st.index ? 'active' : ''}"><div class="key">${i + 1}</div><div class="name">${w.name}</div><div class="ammo">${ammo}</div></div>`;
      }).join('');
    }
    this.crosshair.className = st.key;
    this.crosshair.style.display = st.zoom ? 'none' : '';
    this.scope.classList.toggle('on', st.zoom);
    this.reload.classList.toggle('on', st.reload !== null);
    if (st.reload !== null) this.reloadBar.style.width = `${st.reload * 100}%`;
  }

  /** Cursor mode: crosshair + scope follow the cursor (pixels), or recentre with null. */
  setAim(x, y) {
    const key = x === null ? 'c' : `${Math.round(x)},${Math.round(y)}`;
    if (this._last.aim === key) return;
    this._last.aim = key;
    const left = x === null ? '50%' : `${x}px`;
    const top = x === null ? '50%' : `${y}px`;
    for (const el of [this.crosshair, this.hitmarker]) { el.style.left = left; el.style.top = top; }
    this.scope.style.setProperty('--x', left);
    this.scope.style.setProperty('--y', top);
  }

  hit(head) {
    this.hitmarker.className = '';
    void this.hitmarker.offsetWidth;
    this.hitmarker.className = head ? 'show head' : 'show';
  }

  hurt() {
    this.damage.classList.add('on');
    setTimeout(() => this.damage.classList.remove('on'), 80);
  }

  message(text, ms = 900) {
    this.center.textContent = text;
    this.center.animate([{ transform: 'translate(-50%,-50%) scale(1.6)', opacity: 0 }, { transform: 'translate(-50%,-50%) scale(1)', opacity: 1 }],
      { duration: 200, easing: 'ease-out' });
    clearTimeout(this._msgT);
    if (ms) this._msgT = setTimeout(() => { this.center.textContent = ''; }, ms);
  }
}
