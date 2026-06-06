#!/usr/bin/env python3
"""Stage 1: render the project word -> centerline skeleton (Zhang-Suen thinning).

  python3 engine/extract_skeleton.py <project_dir>

Writes <project_dir>/build/skel.npy (Nx2 x,y) and build/glyph.json (w,h).
"""
import sys, os, json
import numpy as np
from glyphlib import load_project, render_word


def zhang_suen(binary):
    img = binary.astype(np.uint8).copy()
    def nb(y, x, im):
        return [im[y-1, x], im[y-1, x+1], im[y, x+1], im[y+1, x+1],
                im[y+1, x], im[y+1, x-1], im[y, x-1], im[y-1, x-1]]
    def trans(n):
        n2 = n + n[:1]
        return sum((a, b) == (0, 1) for a, b in zip(n2, n2[1:]))
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            dele = []
            ys, xs = np.nonzero(img[1:-1, 1:-1]); ys += 1; xs += 1
            for y, x in zip(ys, xs):
                P = nb(y, x, img)
                p2, p3, p4, p5, p6, p7, p8, p9 = P
                if not (2 <= sum(P) <= 6): continue
                if trans(P) != 1: continue
                if step == 0:
                    if p2*p4*p6 != 0 or p4*p6*p8 != 0: continue
                else:
                    if p2*p4*p8 != 0 or p2*p6*p8 != 0: continue
                dele.append((y, x))
            if dele:
                changed = True
                for y, x in dele: img[y, x] = 0
    return img.astype(bool)


def main(project_dir):
    cfg = load_project(project_dir)
    arr, meta = render_word(project_dir, cfg)
    binary = arr > 110
    skel = zhang_suen(binary)
    ys, xs = np.nonzero(skel)
    build = os.path.join(project_dir, "build")
    os.makedirs(build, exist_ok=True)
    np.save(os.path.join(build, "skel.npy"), np.stack([xs, ys], 1))
    json.dump(meta, open(os.path.join(build, "glyph.json"), "w"))
    print(f"[extract] {cfg['source']['word']!r}: glyph {binary.shape} fg={binary.sum()} skel={skel.sum()}")


if __name__ == "__main__":
    main(sys.argv[1])
