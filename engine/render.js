/*
 * Stage 3: render a project's clips to GIF (frames -> ffmpeg).
 * Driven entirely by project.json (timeline, motion, render). Shares anim.js
 * with the browser tuning page, so renders match the live preview exactly.
 *
 * Exposed as functions so engine.js can call render per (theme, clip) with
 * input-hash caching. Can also run standalone:
 *   node engine/render.js <project_dir> [theme] [clip]
 */
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { createCanvas } = require('@napi-rs/canvas');
const Anim = require('./anim.js');

// build the flat param object anim.js expects from a project config
function paramsFor(cfg, color) {
  return Object.assign(Anim.defaults(), cfg.motion, {
    dur: Object.assign({}, Anim.defaults().dur, cfg.timeline),
    color,
    bg: cfg.render.background || 'transparent',
  });
}

// clip name -> [t0, t1, loop] given the timeline
function clipRange(P) {
  const tl = Anim.timeline(P);
  const pulse = P.dur.pulse;
  return {
    writeon: [0, tl.hold1End, false],
    morph: [tl.hold1End, tl.hold2End, false],
    split: [tl.hold2End, tl.introEnd, false],
    pulse: [tl.introEnd, tl.introEnd + pulse, true],
    intro: [0, tl.introEnd, false],
    full: [0, tl.introEnd + pulse * 3, true],
  };
}

function loadModel(projectDir) {
  const model = JSON.parse(fs.readFileSync(path.join(projectDir, 'build', 'model.json'), 'utf8'));
  return Anim.prepare(model);
}

function renderClip(projectDir, cfg, themeName, color, clipName) {
  const M = loadModel(projectDir);
  const P = paramsFor(cfg, color);
  const range = clipRange(P)[clipName];
  if (!range) throw new Error(`unknown clip: ${clipName}`);
  const [t0, t1, loop] = range;
  const SS = cfg.render.supersample || 2;
  const FPS = cfg.render.fps || 30;
  const W = Math.round(M.w * SS), H = Math.round(M.h * SS);

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'eng_'));
  const nframes = Math.max(1, Math.round((t1 - t0) * FPS));
  for (let i = 0; i < nframes; i++) {
    const T = t0 + (i / nframes) * (t1 - t0);  // [t0,t1) for seamless loop
    const canvas = createCanvas(W, H);
    Anim.draw(canvas.getContext('2d'), M, P, T, { W, H, scale: SS });
    fs.writeFileSync(path.join(tmp, `f_${String(i).padStart(4, '0')}.png`), canvas.toBuffer('image/png'));
  }
  const outDir = path.join(projectDir, 'out');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, `${cfg.name}_${themeName}_${clipName}.gif`);
  const vf = `scale=${cfg.render.width}:-1:flags=lanczos,split[s0][s1];` +
             `[s0]palettegen=reserve_transparent=1:stats_mode=full[p];` +
             `[s1][p]paletteuse=alpha_threshold=128:dither=bayer:bayer_scale=3`;
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS),
    '-i', path.join(tmp, 'f_%04d.png'), '-vf', vf, '-loop', '0', outFile],
    { stdio: ['ignore', 'ignore', 'inherit'] });
  fs.rmSync(tmp, { recursive: true, force: true });
  const size = fs.statSync(outFile).size;
  console.log(`[render] ${path.basename(outFile)}  ${nframes}f  ${(size / 1024).toFixed(0)}KB`);
  return { file: path.relative(projectDir, outFile), frames: nframes, bytes: size };
}

// headless sanity grid: N frames sampled across the whole timeline -> out/_montage.png
function montage(projectDir, cfg, color, n = 20) {
  const M = loadModel(projectDir);
  const P = paramsFor(cfg, color);
  const tl = Anim.timeline(P), total = tl.introEnd + P.dur.pulse;
  const cols = 5, rows = Math.ceil(n / cols);
  const tw = Math.round(M.w * 0.5), th = Math.round(M.h * 0.5);
  const grid = createCanvas(cols * tw, rows * th);
  const g = grid.getContext('2d');
  g.fillStyle = '#15151c'; g.fillRect(0, 0, grid.width, grid.height);
  for (let i = 0; i < n; i++) {
    const T = (i / (n - 1)) * total * 0.999;
    const c = createCanvas(M.w, M.h);
    Anim.draw(c.getContext('2d'), M, Object.assign({}, P, { bg: '#15151c' }), T, { W: M.w, H: M.h, scale: 1 });
    g.drawImage(c, (i % cols) * tw, Math.floor(i / cols) * th, tw, th);
    g.fillStyle = '#ff5'; g.font = '16px sans';
    g.fillText(T.toFixed(2) + 's', (i % cols) * tw + 6, Math.floor(i / cols) * th + 18);
  }
  const out = path.join(projectDir, 'out', '_montage.png');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, grid.toBuffer('image/png'));
  console.log('[montage]', path.relative(projectDir, out));
  return out;
}

module.exports = { renderClip, montage, paramsFor, clipRange, loadModel };

if (require.main === module) {
  const dir = process.argv[2];
  const cfg = JSON.parse(fs.readFileSync(path.join(dir, 'project.json'), 'utf8'));
  const firstColor = Object.values(cfg.render.themes)[0];
  if (process.argv[3] === 'montage') { montage(dir, cfg, firstColor); }
  else {
    const themes = process.argv[3] ? { [process.argv[3]]: cfg.render.themes[process.argv[3]] } : cfg.render.themes;
    const clips = process.argv[4] ? [process.argv[4]] : cfg.render.clips;
    for (const [tn, col] of Object.entries(themes))
      for (const cl of clips) renderClip(dir, cfg, tn, col, cl);
  }
}
