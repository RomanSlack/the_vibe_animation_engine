# AGENTS.md — working in this repo

Guide for AI agents (and humans) editing this repo. Read this first.

## What this is

An engine that turns a **wordmark + a config file** into animated GIFs. Each animation is a
**project** (`projects/<name>/`) whose `project.json` is the single editable source of truth.
The `engine/` builds any project deterministically, with input-hash caching.

The flagship project `belo_thinking` animates the "belo" wordmark as an "AI is thinking"
indicator: gravity draw-in → snake-taut line → bouncing dots.

## Mental model (important)

- **A project is a document.** Everything about an animation lives in `projects/<name>/project.json`.
  To change an animation, edit that file — **not** the engine.
- **The engine is generic.** `engine/` knows nothing about "belo". Change it only to change how
  *all* animations behave (new motion beat, new render backend, new clip type).
- **The animation model:** the word is reduced to medial-axis **discs in pen-stroke order**
  (centreline points; radius = glyph thickness; union = the filled wordmark). Every beat is a
  transform of those discs. The motion math is in `engine/anim.js` (`discState()`), shared by
  the renderer and the browser tuner so they always match.

## Repo map

```
engine/
  engine.js            orchestrator (build/clean, caching, manifest)   ← entry point
  extract_skeleton.py  stage 1: word+font -> build/skel.npy            (needs font)
  build_model.py       stage 2: skeleton -> build/model.json           (needs font)
  anim.js              the motion (defaults() = all knobs; discState() = the math)
  render.js            stage 3: model -> out/*.gif (+ montage)         (no font needed)
  glyphlib.py          shared glyph rasterizer
  SCHEMA.md            project.json field reference                    ← read for fields
projects/<name>/
  project.json         THE DOCUMENT you edit
  assets/<font>        the font (often git-ignored; see assets/README.md)
  build/               generated: skel.npy, model.json, glyph.json, cache.json
  out/                 generated: *.gif, _montage.png
  manifest.json        generated: what produced what
tune.html              browser tuner (sliders -> export project.json)
```

## Common tasks (copy/paste)

```bash
# build / rebuild a project (caches: only re-renders if you changed timeline/motion/render)
node engine/engine.js build projects/belo_thinking
node engine/engine.js build projects/belo_thinking --force     # ignore cache
node engine/engine.js clean projects/belo_thinking

# headless visual check (writes projects/<p>/out/_montage.png — open/Read it)
node engine/render.js projects/belo_thinking montage

# render one theme/clip only
node engine/render.js projects/belo_thinking white full
```

**To change the FEEL** (speed, dot size, bounce, line length): edit `project.json` →
`timeline` / `motion`, then `build`. See `engine/SCHEMA.md` for every field. This is cheap
(render-only). Verify with `montage`.

**To change the WORD or FONT:** you need the font in `assets/`. Edit `source.word` /
`source.font`, then `build --force`. This re-runs extraction (slower).

**To add a NEW animation:**
```bash
cp -r projects/belo_thinking projects/my_thing
# put a font in projects/my_thing/assets/, edit project.json: name, source.word, source.font, themes
node engine/engine.js build projects/my_thing
```

**To change the ANIMATION ITSELF** (a new beat / different motion): edit `engine/anim.js`
(`defaults()` for new knobs, `discState()` for the math, `timeline()`/`render.js clipRange()`
if you add phases). Keep it param-driven so projects stay in control. Add new knobs to
`SCHEMA.md` and `tune.html`'s `SPECS`.

## Show your work to the user (the viewer)

There is a minimal Flask viewer to show the user rendered GIFs and iterations in a browser.
**When the user ("master") wants to see results, start it and give them the URL:**

```bash
python3 viewer/app.py            # serves http://localhost:8015  (read-only)
# leave it running in the background; it auto-discovers projects/<name>/out/*.gif.
# after you re-build, the user just refreshes the page.
PORT=8020 python3 viewer/app.py  # if 8015 is taken
```

Tip: also run `node engine/render.js projects/<p> montage` first — the viewer shows the
montage (frame grid) under each project, which makes iterations easy to compare.

## Tune visually (vibe-code loop)

```bash
python3 -m http.server 8000      # serve the repo root
# open http://localhost:8000/tune.html?project=belo_thinking
```
Drag sliders → click **Export project.json** → paste the `timeline`/`motion` blocks into the
project's `project.json` → `build`.

## Conventions & gotchas

- **Never hand-edit generated files:** `build/*`, `out/*`, `manifest.json`. They are outputs.
- **Don't commit fonts** unless the license allows (default `.gitignore` excludes `*.otf/*.ttf`).
  Renders still work fontless via the committed `build/model.json`; only re-extraction needs the font.
- **Caching:** if a change "didn't take", you likely edited a generated file, or need `--force`.
  Cache keys: `source*` → re-extract; `timeline`/`motion`/`render` → re-render; nothing → no-op.
- **Deps:** Node (+ `npm install` for `@napi-rs/canvas`), `ffmpeg` on PATH, and `python3` with
  `pillow numpy scipy` (`pip install -r requirements.txt`).
- **GIF colour:** coloured fills make bigger GIFs (palette). 1-bit transparency is fine here
  because the shape is a single solid colour.
- The in-app endgame (out of scope) is a Flutter `CustomPainter` reading the same disc model —
  preferred over GIF/Lottie for the real indicator.

## Definition of done for a change

1. `node engine/engine.js build projects/<p>` succeeds.
2. `node engine/render.js projects/<p> montage` and the montage looks right.
3. If you added a knob: it's in `engine/anim.js` defaults, `engine/SCHEMA.md`, and `tune.html`.
