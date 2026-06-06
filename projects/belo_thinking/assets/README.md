# Fonts for this project

This folder holds the font(s) referenced by `../project.json` (`source.font`).

## ⚠️ Bumbbled.otf is a TRIAL font — not committed to git

`Bumbbled.otf` is git-ignored (see repo `.gitignore`) because it is a **trial**
font and embedding it in a public repo is a licensing risk.

You do **not** need the font to render or tune this project: the build falls back
to the committed `../build/model.json` (the traced disc model). You only need the
font to **re-extract** the geometry — i.e. if you change `source.word`,
`source.font`, `source.fontSize`, or `source.pad`.

To regenerate geometry, drop the font here as `Bumbbled.otf`, then:

```bash
node engine/engine.js build projects/belo_thinking --force
```

If you ship anything derived from this font, clear the licensing first (the
project's GIFs trace a centreline skeleton rather than embedding glyph outlines,
which is safer, but confirm with whoever owns the font license).
