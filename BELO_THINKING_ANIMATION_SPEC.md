# belo "Thinking" Animation — Build Spec / Handoff

**Status:** Not started — handoff to implementing agent
**Owner:** TBD (next agent)
**Output format:** **Animated GIF** (frame sequence rendered to GIF)
**Date:** 2026-06-06

---

## 1. What we're building

An animation of the **"belo" wordmark** that signals an "AI is thinking" state. The visual story, in three beats:

1. **Unfold / write-on** — the cursive "belo" logo draws itself in, stroke by stroke, like a pen writing smoothly (left → right).
2. **Collapse to a line** — the finished cursive script straightens / morphs into a single clean horizontal line.
3. **Split into three thinking-bubbles** — the line breaks apart into **three dots/bubbles** that pulse/bounce in a loop, the universal "thinking…" indicator.

The intended use is a toggleable indicator (on while the AI is thinking, resolves when done). **For this deliverable, the output is a GIF** — the in-app/toggle integration is a later, separate task. Build the animation as a clean, self-contained, tunable artifact and render it to GIF.

### Reference (current static logo)
Today "belo" is rendered as plain text in the home-screen header:
- File: `frontend/messaging_app/lib/features/home/screens/home_screen.dart` (~line 3750), `Text('belo', style: AppTheme.logoStyle(context))`
- Style: `AppTheme.logoStyle` in `frontend/messaging_app/lib/core/constants/app_theme.dart:57`

---

## 2. The font

- **Font family:** `Bumbbled` (cursive / script display face)
- **File:** `frontend/messaging_app/assets/fonts/Bumbbled.otf` (235 KB)
- **As used in-app today:** size `28`, weight `500` (`FontWeight.w500`), `letterSpacing: -0.5`
- **Word:** lowercase `belo`

### ⚠️ Important: do NOT animate the raw font outline
Bumbbled glyphs are **filled letterforms** (they have thickness — outlined shapes, not a thin centerline). If you animate the font's actual outline, the "write-on" traces the *borders* of the letters and looks broken.

**What to do instead:** trace a **single thin continuous stroke down the centerline of "belo"** and animate *that*. The font outline is the *reference/silhouette*; the animation source is your traced skeleton stroke.

Suggested process:
1. Set "belo" in Bumbbled in Figma / Illustrator, convert to outlines, export SVG (this gives the exact brand silhouette to trace against).
2. Hand-trace a single continuous pen stroke through the middle of the word as the animatable path.

### ⚠️ Licensing note
`Bumbbled.otf` is a **trial font** (the in-repo file is the trial). Converting/embedding its glyph outlines into a shipped asset is a licensing question. Tracing your *own* inspired-by stroke (rather than baking the actual glyph outlines) is the safer route. Flag to the team before shipping if in doubt.

---

## 3. Recommended approach (vibecodable → GIF)

**Build it as pure code, not in a GUI tool.** Rive/Lottie are GUI-authored (binary `.riv` / machine-generated JSON) and can't be iterated on in code. A hand-rolled code animation can be tuned in plain English and exports to GIF trivially.

**Recommended pipeline:**
1. **Prototype in a single self-contained HTML file** using `<canvas>` (or SVG). Fastest iteration (browser refresh, no build), and canvas → capture frames → GIF is straightforward.
2. Add a few **tuning controls** (sliders) so the feel can be dialed in: unfold speed, morph speed, bubble bounce amount, bubble size, loop speed, colors.
3. Once the feel is locked, **render to GIF** (capture frames at a fixed fps, encode — e.g. via `gif.js` in-browser, or dump PNG frames + `ffmpeg`/`gifski`).

### The animation, mechanically
- **Beat 1 (write-on):** reveal the traced path from 0%→100% of its length. (Canvas: `setLineDash` + `lineDashOffset`, or `getPointAtLength` sampling. Flutter equivalent later: `PathMetric.extractPath`.)
- **Beat 2 (collapse to line):** **shape morph** — the only genuinely tricky 20%. Both shapes must have the **same number of sample points** so you can `lerp` point-to-point. Sample N evenly-spaced points along the cursive stroke and N along a straight line, then interpolate.
- **Beat 3 (split → bubbles):** line shrinks, gaps open between three segments, segments round into dots, dots pulse/bounce on a continuous loop.

---

## 4. Deliverables

1. **The animation source** — the self-contained HTML/canvas (or SVG) prototype with tuning controls, checked into the repo (suggest `experiments/belo_thinking_anim/`).
2. **The rendered GIF(s)** — the final output. Provide:
   - A version on **transparent background** if achievable (GIF transparency is binary/1-bit; if it looks bad, provide solid-background variants for both themes instead).
   - At minimum: one for **dark theme** and one for **light theme** (see colors below).
3. **Short README** in the experiment folder: how to re-render the GIF, fps/dimensions chosen, and any knobs.

---

## 5. Output specs (proposed — confirm with team)

- **Colors (match in-app `logoColor`):**
  - Dark theme: `#F0F6FC` (off-white)
  - Light theme: `#5A1E5C` (deep warm plum)
  - (Other themes exist — `#ECEEF5`, `#F5F0E8` — but dark + light are the two that matter for v1.)
- **Frame rate:** 30 fps target (60 if size allows; GIF gets heavy fast).
- **Dimensions:** size for a header logo — propose ~`tight crop around the wordmark`, exact px TBD. Keep it crisp; render at 2–3× and downscale.
- **Loop:** the "thinking" bubbles loop should be seamless. Decide whether the GIF loops the *whole* sequence (write-on → line → bubbles → repeat) or just the bubble-pulse tail. Recommend: a one-shot intro (beats 1–2) + a seamless looping bubble tail — possibly delivered as **two GIFs** (intro + loop) so the consumer can play intro-once-then-loop.

---

## 6. Open questions for whoever picks this up

- Single full-loop GIF, or split intro + looping-tail GIFs?
- Transparent background achievable at acceptable quality, or solid per-theme?
- Final dimensions / where exactly it sits in the header (affects crop + size).
- Is the trial-font licensing resolved, or are we tracing an inspired-by stroke?

---

## 7. Context / history

- This came out of a discussion about making the cursive "belo" logo "unfold into a line then split into three bubbles" as an AI-thinking indicator.
- Considered and rejected for *this* deliverable: **Rive** (GUI-only authoring, not vibecodable) and **Lottie** (machine-generated JSON, color-baking pain). Both could be revisited if a human designer drives them.
- The eventual in-app version (post-GIF) would likely be a Flutter `CustomPainter` reading `context.colors.logoColor`, driven by a Riverpod `thinkingProvider` for toggle on/off — **out of scope here**, GIF is the output for this task.
