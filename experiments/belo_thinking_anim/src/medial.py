#!/usr/bin/env python3
"""
Medial-axis ("disc") representation of the filled Bumbbled "belo".

A disc of radius = distance-transform value, stamped at every skeleton
pixel, reconstructs the filled glyph (medial axis transform). We subsample
the skeleton to an even spacing so a manageable number of overlapping discs
still tile the strokes. Output feeds the canvas animation: every beat is
just moving / resizing these discs.

Outputs:
  out/medial.json          {w,h,y_mid,x0,x1, discs:[[x,y,r],...]} normalised-ish (px)
  out/preview_recon.png    discs stamped back -> should look like "belo"
"""
import json, numpy as np
from scipy import ndimage
from PIL import Image, ImageFont, ImageDraw

FONT = "../assets/Bumbbled.otf"
WORD = "belo"
FONT_PX = 380
PAD = 60
OUT = "../out"
SPACING = 7.0          # target disc spacing (px) along the stroke


def render_word():
    font = ImageFont.truetype(FONT, FONT_PX)
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    box = tmp.textbbox((0, 0), WORD, font=font)
    w = box[2]-box[0] + 2*PAD
    h = box[3]-box[1] + 2*PAD
    img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(img).text((PAD-box[0], PAD-box[1]), WORD, fill=255, font=font)
    return np.array(img)


def subsample(pts, spacing):
    """Greedy spatial subsample: keep a point only if it's >= spacing from
    all already-kept points (grid-hashed for speed)."""
    cell = spacing
    grid = {}
    kept = []
    for x, y in pts:
        gx, gy = int(x//cell), int(y//cell)
        ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for (px, py) in grid.get((gx+dx, gy+dy), ()):
                    if (px-x)**2 + (py-y)**2 < spacing*spacing:
                        ok = False; break
                if not ok: break
            if not ok: break
        if ok:
            kept.append((x, y))
            grid.setdefault((gx, gy), []).append((x, y))
    return kept


def main():
    arr = render_word()
    binary = arr > 110
    h, w = binary.shape

    dist = ndimage.distance_transform_edt(binary)   # radius map

    skel = np.load(f"{OUT}/skel_pts.npy")            # (N,2) x,y  (from extract_centerline)
    pts = [(int(x), int(y)) for x, y in skel]
    kept = subsample(pts, SPACING)
    print(f"skeleton {len(pts)} -> {len(kept)} discs")

    discs = []
    for x, y in kept:
        r = float(dist[y, x])
        if r < 2:
            continue
        discs.append([float(x), float(y), r])

    xs = [d[0] for d in discs]; ys = [d[1] for d in discs]
    x0, x1 = min(xs), max(xs)
    y_mid = float(np.mean(ys))
    meta = {"w": w, "h": h, "y_mid": y_mid, "x0": x0, "x1": x1,
            "n": len(discs), "discs": discs}
    json.dump(meta, open(f"{OUT}/medial.json", "w"))
    print(f"wrote {OUT}/medial.json ({len(discs)} discs)  r:[{min(d[2] for d in discs):.1f},{max(d[2] for d in discs):.1f}]")

    # reconstruction preview: stamp discs
    canvas = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(canvas)
    for x, y, r in discs:
        d.ellipse([x-r, y-r, x+r, y+r], fill=255)
    # side by side: original (top) vs reconstruction (bottom)
    comp = Image.new("RGB", (w, h*2+10), (20, 20, 25))
    comp.paste(Image.fromarray(arr).convert("RGB"), (0, 0))
    comp.paste(canvas.convert("RGB"), (0, h+10))
    comp.save(f"{OUT}/preview_recon.png")
    print(f"wrote {OUT}/preview_recon.png")


if __name__ == "__main__":
    main()
