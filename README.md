# animation_gif_engine

A small **project-based engine** that turns a wordmark + a config file into animated GIFs.

Each animation is a **project**: a folder with one editable document (`project.json`) plus
its font. The engine reads that document and builds the GIFs deterministically. Because the
document *is* the animation, this is the layer an **AI editor** (or a GUI) can drive later —
edit `project.json`, run `build`, get new GIFs.

```
animation_gif_engine/
├── engine/                     # the reusable, word/font-agnostic engine
│   ├── engine.js               #   orchestrator: build/clean, input-hash caching, manifest
│   ├── extract_skeleton.py     #   stage 1: word+font -> centerline skeleton
│   ├── build_model.py          #   stage 2: skeleton -> ordered medial-disc model
│   ├── anim.js                 #   the motion (param-driven; shared with browser tuning)
│   ├── render.js               #   stage 3: model -> GIF (frames -> ffmpeg)
│   └── glyphlib.py             #   shared glyph rasterizer
├── projects/
│   └── belo_thinking/
│       ├── project.json        # ← THE DOCUMENT (the editable source of truth)
│       ├── assets/Bumbbled.otf
│       ├── build/              # generated: skel.npy, model.json, cache.json
│       ├── out/                # generated: *.gif
│       └── manifest.json       # generated: what was produced from what
└── experiments/belo_thinking_anim/   # original standalone prototype + tuning page (kept)
```

## Quickstart

```bash
npm install                       # pulls @napi-rs/canvas
pip install -r requirements.txt   # pillow numpy scipy (+ flask for the viewer)
# ffmpeg must be on PATH

node engine/engine.js build projects/belo_thinking   # -> projects/belo_thinking/out/*.gif
python3 viewer/app.py                                 # browse results: http://localhost:8015
```

```bash
node engine/engine.js build projects/belo_thinking --force   # ignore cache
node engine/engine.js clean projects/belo_thinking
node engine/render.js projects/belo_thinking montage         # headless frame-grid sanity check
```

Prereqs: `node` (>=18), `ffmpeg`, `python3` with `pillow numpy scipy`.

**New here / an agent?** Read [`AGENTS.md`](AGENTS.md) for the working model and common tasks,
and [`engine/SCHEMA.md`](engine/SCHEMA.md) for every `project.json` field.

## View & tune

- **Viewer** (`python3 viewer/app.py`, port **8015**): a minimal read-only page showing every
  project's rendered GIFs + montage. Re-run a build and refresh.
- **Tuner** (`python3 -m http.server 8000`, then open `tune.html?project=belo_thinking`): live
  sliders over the real motion; click **Export project.json** and paste the result back.

## How it builds (and why it's cheap to re-drive)

Three stages, each **cached by a hash of its inputs** (`build/cache.json`):

| stage | inputs (hash) | artifact |
|-------|---------------|----------|
| extract | font bytes + word + fontSize + pad | `build/skel.npy` |
| model   | extract-hash + discSpacing | `build/model.json` |
| render  | model-hash + timeline + motion + render opts | `out/<name>_<theme>_<clip>.gif` |

So editing only `motion` or `timeline` **re-renders without re-extracting the skeleton**
(the slow part). A no-op rebuild is ~0.4s; a motion tweak skips straight to render. This is
exactly what makes an AI editing loop (change config → rebuild → look) practical.

## The document: `project.json`

The whole animation is described by this one file — see `engine/SCHEMA.md` for the field
reference. In short:

- `source` — word, font, size, disc spacing (what gets traced)
- `timeline` — seconds per beat: writeon, hold1, morph, hold2, split, pulse
- `motion` — the feel: drop-in gravity, taut-snap, dot size/gap, bounce
- `render` — fps, width, supersample, background, `themes` (name→color), `clips`

## The animation model (what the engine actually animates)

"belo" is reduced to a cloud of **medial-axis discs in pen-stroke order** (each disc = a
point on the centreline with radius = the glyph's thickness there; the union reconstructs the
filled wordmark). Every beat is just a transform of those discs — gravity drop-in, snake-taut
straighten, gather-into-3, bounce. No font-outline animation, no shape-morph point matching.
This generalizes to any word/font, which is why it lives in the engine, not the project.

## Adding a new animation

1. `cp -r projects/belo_thinking projects/my_thing` (or make a fresh folder)
2. drop a font in `assets/`, edit `project.json` (`name`, `source.word`, `source.font`, colors)
3. `node engine/engine.js build projects/my_thing`

## Output notes

- GIF transparency is 1-bit; since the shape is a single solid colour the alpha edge is
  effectively invisible even on mid-grey. Put a white/theme layer behind as needed.
- Colored fills produce larger GIFs (anti-aliased edges → bigger palette). For tiny header
  use, a `.webp`/`.mp4` export would be ~10× smaller — easy to add as another render backend.
- **In-app endgame (out of scope):** the disc model ports directly to a Flutter `CustomPainter`
  for dynamic theme color and crisp edges — preferred over GIF/Lottie for the real indicator.
