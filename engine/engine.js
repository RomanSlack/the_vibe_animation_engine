#!/usr/bin/env node
/*
 * Animation GIF engine — project orchestrator.
 *
 *   node engine/engine.js build <project_dir> [--force]
 *   node engine/engine.js clean <project_dir>
 *
 * Runs the pipeline for a project (a folder with project.json):
 *   1. extract_skeleton.py   word+font -> build/skel.npy
 *   2. build_model.py        skeleton  -> build/model.json   (ordered discs)
 *   3. render.js             model     -> out/*.gif          (per theme x clip)
 *
 * Each stage is cached by a hash of its inputs (build/cache.json), so editing
 * only `motion` re-renders without re-extracting — which is what makes this
 * cheap to drive from an AI editor. A manifest.json records what produced what.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const render = require('./render.js');

const ENGINE_DIR = __dirname;
const sha = (s) => crypto.createHash('sha256').update(s).digest('hex').slice(0, 16);

function loadCfg(dir) { return JSON.parse(fs.readFileSync(path.join(dir, 'project.json'), 'utf8')); }
function readCache(dir) {
  const f = path.join(dir, 'build', 'cache.json');
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : {};
}
function writeCache(dir, c) {
  fs.mkdirSync(path.join(dir, 'build'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'build', 'cache.json'), JSON.stringify(c, null, 2));
}
function py(script, dir) {
  execFileSync('python3', [path.join(ENGINE_DIR, script), dir],
    { cwd: ENGINE_DIR, stdio: 'inherit' });
}

function build(dir, force) {
  dir = path.resolve(dir);
  const cfg = loadCfg(dir);
  const cache = force ? {} : readCache(dir);
  const manifest = { name: cfg.name, version: cfg.version, builtAt: new Date().toISOString(),
                     stages: {}, outputs: [] };

  // ---- stages 1+2: extract skeleton -> build model (need the font) ----
  // The font may be absent (e.g. a trial font kept out of git). Rendering only
  // needs build/model.json, so we skip extraction when the font is missing but
  // a model already exists — and only hard-fail if neither is available.
  const fontPath = path.join(dir, cfg.source.font);
  const modelPath = path.join(dir, 'build', 'model.json');
  const haveFont = fs.existsSync(fontPath);
  const modelOk = fs.existsSync(modelPath);

  if (haveFont) {
    const fontBytes = fs.readFileSync(fontPath);
    const hExtract = sha(JSON.stringify({ ...cfg.source, font: undefined }) + ':' + sha(fontBytes));
    const skelOk = fs.existsSync(path.join(dir, 'build', 'skel.npy'));
    if (cache.extract === hExtract && skelOk) console.log('[extract] cached');
    else { py('extract_skeleton.py', dir); cache.extract = hExtract; }

    const hModel = sha(hExtract + ':' + (cfg.source.discSpacing || 7));
    if (cache.model === hModel && modelOk) console.log('[model] cached');
    else { py('build_model.py', dir); cache.model = hModel; }
  } else if (modelOk) {
    console.log(`[extract/model] skipped — font ${cfg.source.font} not present; using committed build/model.json`);
  } else {
    throw new Error(
      `Cannot build "${cfg.name}": font not found at ${cfg.source.font} and no build/model.json to fall back on.\n` +
      `  Add the font (see ${path.relative(process.cwd(), path.join(dir, 'assets'))}/) ` +
      `or commit a prebuilt build/model.json.`);
  }

  // render depends on the model's actual content (works with or without font)
  const hModelContent = sha(fs.readFileSync(modelPath));
  manifest.stages.model = hModelContent;

  // ---- stage 3: render (per theme x clip) ----
  cache.renders = cache.renders || {};
  for (const [themeName, color] of Object.entries(cfg.render.themes)) {
    for (const clip of cfg.render.clips) {
      const key = `${themeName}:${clip}`;
      const hRender = sha([hModelContent, color, clip,
        JSON.stringify(cfg.timeline), JSON.stringify(cfg.motion),
        cfg.render.fps, cfg.render.width, cfg.render.supersample, cfg.render.background].join('|'));
      const outFile = path.join(dir, 'out', `${cfg.name}_${themeName}_${clip}.gif`);
      let rec;
      if (cache.renders[key] && cache.renders[key].hash === hRender && fs.existsSync(outFile)) {
        console.log(`[render] ${themeName}:${clip} cached`);
        rec = cache.renders[key].rec;
      } else {
        rec = render.renderClip(dir, cfg, themeName, color, clip);
        cache.renders[key] = { hash: hRender, rec };
      }
      manifest.outputs.push({ theme: themeName, clip, ...rec });
    }
  }

  writeCache(dir, cache);
  fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2));
  console.log(`\n✔ built ${cfg.name}: ${manifest.outputs.length} output(s) -> ${path.join(dir, 'out')}`);
  console.log(`  manifest: ${path.join(dir, 'manifest.json')}`);
}

function clean(dir) {
  dir = path.resolve(dir);
  for (const sub of ['build', 'out']) fs.rmSync(path.join(dir, sub), { recursive: true, force: true });
  fs.rmSync(path.join(dir, 'manifest.json'), { force: true });
  console.log('cleaned', dir);
}

const [cmd, dir, flag] = process.argv.slice(2);
if (cmd === 'build' && dir) build(dir, flag === '--force');
else if (cmd === 'clean' && dir) clean(dir);
else { console.error('usage: node engine/engine.js build|clean <project_dir> [--force]'); process.exit(1); }
