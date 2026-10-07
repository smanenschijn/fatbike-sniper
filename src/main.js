import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { FOV, HEARTS, difficulty } from './config.js';
import { loadAssets } from './assets.js';
import { World } from './world.js';
import { Input } from './input.js';
import { Effects } from './effects.js';
import { Riders } from './riders.js';
import { Weapons } from './weapons.js';
import { Hud } from './hud.js';
import { Game } from './game.js';
import { sfx } from './audio.js';

const $ = (id) => document.getElementById(id);
const canvas = $('game');

// ---------------------------------------------------------------- renderer
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.85;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(FOV, innerWidth / innerHeight, 0.02, 1500);
camera.rotation.order = 'YXZ';
scene.add(camera);

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.3, 0.4, 3.0);
composer.addPass(bloom);
composer.addPass(new OutputPass());

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  composer.setSize(innerWidth, innerHeight);
});

// ---------------------------------------------------------------- highscores (per browser)
const HS_KEY = 'fatbike-sniper-highscores';
const loadScores = () => { try { return JSON.parse(localStorage.getItem(HS_KEY)) || []; } catch { return []; } };
const saveScores = (list) => { try { localStorage.setItem(HS_KEY, JSON.stringify(list)); } catch { /* private mode */ } };
function renderScores(el, highlight) {
  const list = loadScores();
  el.innerHTML = list.length
    ? list.map((s, i) => `<li class="${i === highlight ? 'me' : ''}">${escapeHtml(s.name)}<span class="s">${s.score}</span></li>`).join('')
    : '<li style="list-style:none;margin-left:-24px;color:#c8bfae">Nog geen scores. Wees de eerste!</li>';
}
const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function rankTitle(score) {
  if (score < 400) return 'Terrasganger';
  if (score < 1200) return 'Buurtwacht';
  if (score < 2500) return 'Fatbike Verdelger';
  if (score < 4500) return 'Schrik van het Plein';
  return "Legende van 't Pleintje";
}

// ---------------------------------------------------------------- boot
let world, effects, riders, weapons, hud, game, input;
let mode = 'loading'; // loading | title | playing | paused | ended
let lastScore = null;

async function boot() {
  const assets = await loadAssets((p) => { $('progress-bar').style.width = `${Math.round(p * 100)}%`; });
  $('loading-text').textContent = 'Fatbikers aan het oppompen...';
  await new Promise((r) => setTimeout(r, 30));

  world = new World(renderer, scene, assets);
  camera.position.copy(world.eye);
  hud = new Hud();
  effects = new Effects(scene, camera, hud.popups);
  riders = new Riders(scene, assets, effects, { playerEye: world.eye, onPlayerHit: () => {} });
  weapons = new Weapons(camera, assets, {});
  input = new Input(canvas);
  game = new Game({ scene, camera, world, riders, weapons, effects, hud });
  game.onEnd = showEnd;
  input.onLockChange = (locked) => { if (!locked && mode === 'playing') pause(); };
  input.onModeChange = (m) => {
    document.body.classList.toggle('cursor-mode', m === 'cursor');
    if (m === 'cursor' && mode === 'playing') effects.screenPopup('Richt met de cursor, ga naar de rand om te draaien', '', 0.5, 0.72, 3.5);
  };

  // warm up shaders so the first shot doesn't stutter
  renderer.compile(scene, camera);
  if (import.meta.env.DEV) window.__dbg = { renderer, composer, game, camera, input, riders, weapons, world, effects, startGame, scene, setMode: (m) => (mode = m) };
  $('loading').classList.add('hidden');
  showTitle();
  requestAnimationFrame(loop);
}

function showTitle() {
  mode = 'title';
  renderScores($('highscores-title'));
  $('title').classList.remove('hidden');
  hud.show(false);
}

function pause() {
  mode = 'paused';
  input.active = false;
  document.body.classList.remove('playing');
  $('pause').classList.remove('hidden');
}

function startGame() {
  sfx.init();
  $('title').classList.add('hidden');
  $('end').classList.add('hidden');
  hud.show(true);
  input.yaw = 0;
  input.pitch = -0.05;
  game.reset();
  mode = 'playing';
  input.active = true;
  document.body.classList.add('playing');
  input.lock();
}

function showEnd(reason, score, stats) {
  mode = 'ended';
  input.active = false;
  document.body.classList.remove('playing');
  input.unlock();
  lastScore = { score, stats };
  setTimeout(() => {
    hud.show(false);
    $('end-reason').textContent = reason;
    $('end-title').textContent = rankTitle(score);
    $('end-score').textContent = score;
    const acc = stats.shots ? Math.round((stats.hits / stats.shots) * 100) : 0;
    $('end-stats').innerHTML = [
      ['Van de fiets', stats.kills], ['Headshots', stats.headshots], ['Nauwkeurigheid', `${acc}%`],
      ['Messen geraakt', stats.knives], ['Beste combo', `${stats.bestMulti}x`], ['Speaker-bazen', stats.bosses],
    ].map(([k, v]) => `<div>${k}<b>${v}</b></div>`).join('');
    const list = loadScores();
    const qualifies = score > 0 && (list.length < 10 || score > list[list.length - 1].score);
    $('name-entry').classList.toggle('hidden', !qualifies);
    renderScores($('highscores-end'));
    $('end').classList.remove('hidden');
    if (qualifies) setTimeout(() => $('name-input').focus(), 50);
  }, 1300);
}

$('save-btn').addEventListener('click', () => {
  if (!lastScore) return;
  const name = $('name-input').value.trim() || 'Anoniem';
  const list = loadScores();
  list.push({ name, score: lastScore.score, date: Date.now() });
  list.sort((a, b) => b.score - a.score);
  const top = list.slice(0, 10);
  saveScores(top);
  renderScores($('highscores-end'), top.findIndex((s) => s.name === name && s.score === lastScore.score));
  $('name-entry').classList.add('hidden');
  lastScore = null;
});
$('name-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('save-btn').click(); });
$('start-btn').addEventListener('click', startGame);
$('again-btn').addEventListener('click', startGame);
$('pause').addEventListener('click', () => {
  $('pause').classList.add('hidden');
  mode = 'playing';
  input.active = true;
  document.body.classList.add('playing');
  input.lock();
});

// ---------------------------------------------------------------- loop
const timer = new THREE.Timer();
const DEMO_DIFF = { ...difficulty(0.35), attackChance: 0, maxAlive: 8 };
let demoT = 0;

function loop() {
  requestAnimationFrame(loop);
  timer.update();
  const dt = Math.min(timer.getDelta(), 0.05);

  if (mode === 'title' || mode === 'ended') {
    // attract mode: riders cruise the square while the camera looks around
    demoT += dt;
    riders.update(dt, DEMO_DIFF, 30);
    camera.rotation.set(-0.08 + Math.sin(demoT * 0.15) * 0.05, Math.sin(demoT * 0.12) * 0.6, 0);
    weapons.root.visible = false;
  } else if (mode === 'playing') {
    if (input.mode === 'cursor' && input.keysPressed.has('Escape')) pause();
    input.update(dt);
    game.update(dt, input);
    camera.rotation.set(input.pitch, input.yaw, 0);
    if (input.mode === 'cursor') hud.setAim((input.cursor.x * 0.5 + 0.5) * innerWidth, (-input.cursor.y * 0.5 + 0.5) * innerHeight);
    else hud.setAim(null);
  }
  if (mode === 'playing' || mode === 'paused') {
    hud.setWeapons(weapons.hudState());
    hud.setHearts(game.hearts, HEARTS);
  }

  // camera shake
  camera.position.copy(world.eye);
  if (effects.shake > 0) {
    const s = effects.shake * effects.shake * 0.06;
    camera.position.x += (Math.random() - 0.5) * s;
    camera.position.y += (Math.random() - 0.5) * s;
    camera.rotation.z = (Math.random() - 0.5) * s * 0.5;
  }

  if (mode !== 'paused') {
    effects.update(dt);
    world.update(dt);
  }
  input.endFrame();
  composer.render();
}

boot().catch((e) => {
  console.error(e);
  $('loading-text').textContent = 'Er ging iets mis bij het laden: ' + e.message;
});
