# belo "thinking" animation

Animated GIF of the **belo** wordmark as an "AI is thinking" indicator. Motion (v2):

1. **draw-in** — discs fall in under gravity, sweeping left→right **in pen-stroke order**
2. **snake-taut** — the cursive straightens like a string pulled taut into one clean line
3. **split + pulse** — the line gathers into three dots that bounce on a staggered gravity arc, looping

See `../../BELO_THINKING_ANIMATION_SPEC.md` for the original brief.
Current deliverable going forward: **`out/belo_white_full.gif`** (white fill, transparent bg, whole story + thinking loop). Earlier v1 motion + all themes are archived in `out/v1_backup/`.

## How it works (the trick)

Bumbbled glyphs are *filled* letterforms, so you can't animate the font outline directly
(it would trace the borders). Instead we reduce "belo" to its **medial axis**: a disc is
stamped at every centreline point with radius = the glyph's local thickness there. The
union of those discs reconstructs the exact filled wordmark — and then **every beat is just
a transform of those discs**:

The discs are stored **in pen-stroke order** (arc-length param `s` per disc, from `order_discs.py`),
which is what makes the stroke-order draw and the snake-taut straighten possible:

| beat   | disc transform                                              |
|--------|------------------------------------------------------------|
| draw-in  | reveal by `s`; each disc falls in from above with a gravity bounce |
| morph    | move disc to `x = x0 + s·width` on the mid-line (easeOutBack snap) → unrolls taut |
| split    | gather discs into 3 clusters by `s`-third (easeOutBack bounce) |
| pulse    | 3 dot clusters bounce on a gravity arc `4·ph·(1-ph)`, staggered |

This needs no font-outline animation, no shape-morph point-matching, and uses the real
font's thickness. The same `belo_anim.js` runs in the browser (tuning) and in Node (GIF render).

## Files

```
index.html              # live tuning page (sliders) — open in a browser
src/belo_anim.js        # shared animation module (browser + node) — SINGLE SOURCE OF TRUTH
src/render.js           # node renderer: frames -> ffmpeg -> GIF
src/extract_centerline.py  # render "belo" in Bumbbled -> skeleton (Zhang-Suen)
src/order_discs.py      # skeleton -> ORDERED medial discs -> out/medial.json  (v2 source)
src/medial.py           # (v1) unordered discs — kept for reference
assets/Bumbbled.otf     # the font (TRIAL — see licensing note below)
out/medial.json         # ORDERED disc data consumed by belo_anim.js
out/belo_white_full.gif # current deliverable
out/v1_backup/          # archived v1 gifs (all themes) + medial_v1.json
```

## Re-rendering

Prereqs: `python3` (PIL, numpy, scipy, fontTools), `node`, `ffmpeg`, and `npm i` (pulls `@napi-rs/canvas`).

```bash
# 1. (only if the font/word changes) rebuild the ordered disc data:
cd src
python3 extract_centerline.py     # -> out/skel_pts.npy  (~8s)
python3 order_discs.py            # -> out/medial.json (ordered) + out/preview_order2.png
cd ..

# 2. sanity-check the motion as a single grid of frames:
node src/render.js montage        # -> out/preview_montage.png

# 3. render GIFs:
node src/render.js full white     # the current deliverable (white, full sequence)
node src/render.js gifs all       # (v1-style) all themes + modular clips
```

## Output

- **fps:** 30 · **width:** 600 px (rendered at 2× then downscaled with lanczos for crisp edges)
- **background:** transparent (1-bit). Solid single-colour shape, so the binary alpha edge is
  effectively invisible even on mid-grey — verified. Put a white/theme layer behind it as needed.
- **themes / colors** (match in-app `logoColor`):
  - `black` `#000000` (neutral / "make them black first")
  - `dark`  `#F0F6FC` off-white (dark UI)
  - `light` `#5A1E5C` deep plum (light UI)

### Modular clips (tile the timeline — seamless when concatenated)

| file | beat |
|------|------|
| `belo_<theme>_A_writeon.gif` | write-on + hold |
| `belo_<theme>_B_morph.gif`   | belo → line |
| `belo_<theme>_C_split.gif`   | line → 3 dots |
| `belo_<theme>_D_pulse.gif`   | **seamless** thinking loop |
| `belo_<theme>_intro.gif`     | A+B+C combined (one-shot intro) |

Recommended consumption: play `intro` once, then loop `D_pulse` forever.

## Tunable knobs

All in `BeloAnim.defaults()` (`src/belo_anim.js`) and live in `index.html`:

- **timing (s):** `dur.writeon` `dur.hold1` `dur.morph` `dur.hold2` `dur.split` `dur.pulse`
- **draw-in:** `revealWindow` (how much of the stroke is mid-drop at once), `dropHeight` (gravity fall distance)
- **line/dots:** `lineR` (line thickness), `dotR`, `dotGap`, `morphBack` / `splitBack` (overshoot/bounce strength)
- **pulse:** `bounceAmp`, `dotPulse` (radius squash), `bounceStagger`
- `color`, `bg`

Render constants (`src/render.js`): `FPS`, `SS` (supersample), `FINAL_W`.

## Notes

- **Licensing:** `Bumbbled.otf` is a **trial** font. These GIFs bake an *inspired-by traced
  stroke* (a medial skeleton) rather than embedding the glyph outlines, but confirm with the
  team before shipping. The `.otf` is copied here only to regenerate `medial.json`.
- **In-app later (out of scope):** the disc model ports directly to a Flutter `CustomPainter`
  reading `context.colors.logoColor` — no per-theme files, clean edges, dynamic color.
  Preferred over GIF/Lottie for the real in-app indicator.
```
