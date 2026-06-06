/*
 * Render the belo thinking animation to frames -> GIF (via ffmpeg),
 * sharing belo_anim.js with the browser tuning page.
 *
 *   node src/render.js montage           # one PNG grid of sampled frames (sanity)
 *   node src/render.js gifs [theme]      # render modular clip GIFs
 *
 * themes: black (default) | dark | light | all
 */
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { createCanvas } = require('@napi-rs/canvas');
const BeloAnim = require('./belo_anim.js');

const ROOT = path.join(__dirname, '..');
const OUT = path.join(ROOT, 'out');
const medial = JSON.parse(fs.readFileSync(path.join(OUT, 'medial.json'), 'utf8'));
const M = BeloAnim.prepare(medial);

const FPS = 30;
const SS = 2;                       // supersample factor for crisp edges
const FINAL_W = 600;                // output gif width (px)

const THEMES = {
  white: { color: '#FFFFFF' },
  black: { color: '#000000' },
  dark:  { color: '#F0F6FC' },      // off-white (dark UI)
  light: { color: '#5A1E5C' },      // deep plum (light UI)
};

function paramsFor(themeKey) {
  return Object.assign(BeloAnim.defaults(), THEMES[themeKey]);
}

function renderFrame(P, T) {
  const W = Math.round(M.w * SS), H = Math.round(M.h * SS);
  const canvas = createCanvas(W, H);
  const ctx = canvas.getContext('2d');
  BeloAnim.draw(ctx, M, P, T, { W, H, scale: SS, ox: 0, oy: 0 });
  return canvas;
}

// ---- montage: sample N frames across full timeline into a grid ----
function montage() {
  const P = paramsFor('dark');           // off-white on dark grid, easy to see
  const tl = BeloAnim.timeline(P);
  const total = tl.introEnd + P.dur.pulse;
  const N = 24, cols = 4, rows = Math.ceil(N / cols);
  const tw = Math.round(M.w * 0.5), th = Math.round(M.h * 0.5);
  const grid = createCanvas(cols * tw, rows * th);
  const g = grid.getContext('2d');
  g.fillStyle = '#15151c'; g.fillRect(0, 0, grid.width, grid.height);
  for (let i = 0; i < N; i++) {
    const T = (i / (N - 1)) * total * 0.999;
    const W = M.w, H = M.h;
    const c = createCanvas(W, H);
    const cx = c.getContext('2d');
    BeloAnim.draw(cx, M, P, T, { W, H, scale: 1 });
    const col = i % cols, row = Math.floor(i / cols);
    g.drawImage(c, col * tw, row * th, tw, th);
    g.fillStyle = '#ff5'; g.font = '16px sans'; g.fillText(`t=${T.toFixed(2)}s`, col * tw + 6, row * th + 18);
  }
  const f = path.join(OUT, 'preview_montage.png');
  fs.writeFileSync(f, grid.toBuffer('image/png'));
  console.log('wrote', f);
}

// ---- gif rendering ----
function renderClip(name, t0, t1, P, loop) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'belo_'));
  const nframes = Math.max(1, Math.round((t1 - t0) * FPS));
  for (let i = 0; i < nframes; i++) {
    const T = t0 + (i / nframes) * (t1 - t0);   // [t0,t1) so loop is seamless
    const canvas = renderFrame(P, T);
    fs.writeFileSync(path.join(tmp, `f_${String(i).padStart(4, '0')}.png`), canvas.toBuffer('image/png'));
  }
  const outFile = path.join(OUT, `${name}.gif`);
  const vf = `scale=${FINAL_W}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=reserve_transparent=1:stats_mode=full[p];[s1][p]paletteuse=alpha_threshold=128:dither=bayer:bayer_scale=3`;
  execFileSync('ffmpeg', [
    '-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', path.join(tmp, 'f_%04d.png'),
    '-vf', vf, '-loop', '0', outFile,
  ], { stdio: ['ignore', 'ignore', 'inherit'] });
  fs.rmSync(tmp, { recursive: true, force: true });
  const kb = (fs.statSync(outFile).size / 1024).toFixed(0);
  console.log(`  ${name}.gif  (${nframes} frames, ${kb} KB)`);
}

function gifs(themeKey) {
  const keys = themeKey === 'all' || !themeKey ? Object.keys(THEMES) : [themeKey];
  for (const tk of keys) {
    const P = paramsFor(tk);
    const tl = BeloAnim.timeline(P);
    console.log(`theme=${tk} color=${P.color}`);
    // modular clips tiling the timeline (seamless when concatenated)
    renderClip(`belo_${tk}_A_writeon`, 0, tl.hold1End, P, false);
    renderClip(`belo_${tk}_B_morph`, tl.hold1End, tl.hold2End, P, false);
    renderClip(`belo_${tk}_C_split`, tl.hold2End, tl.introEnd, P, false);
    renderClip(`belo_${tk}_D_pulse`, tl.introEnd, tl.introEnd + P.dur.pulse, P, true);
    // convenience: one-shot intro, and the WHOLE story + 3 thinking loops
    renderClip(`belo_${tk}_intro`, 0, tl.introEnd, P, false);
    renderClip(`belo_${tk}_full`, 0, tl.introEnd + P.dur.pulse * 3, P, true);
  }
}

function full(themeKey) {
  const tk = themeKey || 'white';
  const P = paramsFor(tk);
  const tl = BeloAnim.timeline(P);
  console.log(`theme=${tk} color=${P.color}`);
  renderClip(`belo_${tk}_full`, 0, tl.introEnd + P.dur.pulse * 3, P, true);
}

const cmd = process.argv[2] || 'montage';
if (cmd === 'montage') montage();
else if (cmd === 'gifs') gifs(process.argv[3]);
else if (cmd === 'full') full(process.argv[3]);
else { console.error('unknown cmd', cmd); process.exit(1); }
