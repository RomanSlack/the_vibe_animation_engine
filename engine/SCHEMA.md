# `project.json` schema

The single editable document for an animation project. All fields below are required
unless noted. Paths are relative to the project folder.

```jsonc
{
  "name": "belo_thinking",     // output files are named <name>_<theme>_<clip>.gif
  "version": 2,                // free-form integer for your own tracking
  "description": "...",        // optional, human note

  "source": {                  // WHAT GETS TRACED  (changing any of these re-extracts)
    "word": "belo",            // the text to animate
    "font": "assets/Bumbbled.otf",
    "fontSize": 380,           // px the glyph is rasterized at (bigger = cleaner skeleton)
    "pad": 60,                 // px padding around the word in the work bitmap
    "discSpacing": 7           // px between medial discs (smaller = smoother + more discs)
  },

  "timeline": {                // SECONDS PER BEAT  (changing these re-renders only)
    "writeon": 1.55,           // gravity draw-in
    "hold1": 0.35,             // hold full wordmark
    "morph": 1.0,              // snake-taut straighten
    "hold2": 0.25,             // hold the line
    "split": 0.85,             // line -> 3 dots
    "pulse": 1.1               // length of ONE seamless thinking-dot loop
  },

  "motion": {                  // THE FEEL  (changing these re-renders only)
    "revealWindow": 0.12,      // fraction of the stroke mid-drop at once (draw-in wave width)
    "dropHeight": 44,          // px each disc falls in from (gravity)
    "lineR": 16,               // half-thickness of the taut line (px)
    "dotR": 23,                // dot radius (px)
    "dotGap": 84,              // spacing between the 3 dot centres (px)
    "morphBack": 1.6,          // taut-pull overshoot strength (0 = no bounce)
    "splitBack": 2.1,          // split-gather overshoot strength
    "bounceAmp": 30,           // dot bounce height (px)
    "dotPulse": 0.14,          // dot radius squash on bounce (fraction)
    "bounceStagger": 0.16      // phase offset between the 3 dots (turns)
  },

  "render": {                  // OUTPUT
    "fps": 30,
    "width": 600,              // output px width (rendered at width*supersample, downscaled)
    "supersample": 2,          // render scale for crisp edges
    "background": "transparent", // "transparent" or a hex like "#0d1117"
    "themes": { "white": "#FFFFFF" },  // name -> fill color; one gif per theme
    "clips": ["full"]          // which clips to render (see below)
  }
}
```

## Clips

A clip is a time-range of the timeline. Available names:

| clip | range | loops? |
|------|-------|--------|
| `writeon` | draw-in + hold | no |
| `morph`   | belo → line | no |
| `split`   | line → 3 dots | no |
| `pulse`   | one seamless thinking loop | yes |
| `intro`   | writeon→morph→split (one-shot) | no |
| `full`    | whole sequence + 3 thinking loops | yes |

`writeon`/`morph`/`split`/`pulse` tile the timeline, so they concatenate seamlessly if you
want to assemble them downstream.

## Cache keys (what triggers a rebuild)

- edit `source` → re-extracts skeleton, rebuilds model, re-renders
- edit `source.discSpacing` only → rebuilds model + re-renders (skips extract)
- edit `timeline` / `motion` / `render` → **re-renders only**
- no change → nothing runs

`--force` ignores the cache entirely.
