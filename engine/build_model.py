#!/usr/bin/env python3
"""Stage 2: skeleton -> ordered medial-disc model.

  python3 engine/build_model.py <project_dir>

Walks the skeleton as one continuous pen stroke (redundant diagonal edges
removed so staircases stay degree-2; greedy direction-continuity; resume from
nearest unused edge when stuck) and resamples to evenly spaced discs IN ORDER,
each with radius = the glyph's distance-transform there. Writes build/model.json
consumed by anim.js (every animation beat is a transform of these discs).
"""
import sys, os, json
import numpy as np
from scipy import ndimage
from glyphlib import load_project, render_word

N8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]


def neighbours(grid, y, x):
    H, W = grid.shape
    return [(y+dy, x+dx) for dy, dx in N8
            if 0 <= y+dy < H and 0 <= x+dx < W and grid[y+dy, x+dx]]


def greedy_order(grid):
    ys, xs = np.nonzero(grid)
    px = list(zip(ys.tolist(), xs.tolist()))
    start = min(px, key=lambda p: (p[1], p[0]))          # leftmost -> draw L->R
    unused = {p: set(neighbours(grid, *p)) for p in px}
    # drop redundant diagonal edges (hypotenuse of each 8-conn triangle)
    for p in px:
        for q in list(unused[p]):
            if p[0] != q[0] and p[1] != q[1] and (unused[p] & unused[q]):
                unused[p].discard(q); unused[q].discard(p)

    runs = [[start]]; cur = start; dirv = np.array([1.0, 0.0])
    while True:
        cand = list(unused[cur])
        if cand:
            best, bs = None, -2.0
            for p in cand:
                v = np.array([p[1]-cur[1], p[0]-cur[0]], float); v /= (np.linalg.norm(v) or 1)
                sc = float(np.dot(v, dirv))
                if sc > bs: bs, best = sc, p
            unused[cur].discard(best); unused[best].discard(cur)
            runs[-1].append(best)
            k = min(6, len(runs[-1]) - 1)
            a = np.array(runs[-1][-1]); b = np.array(runs[-1][-1-k])
            v = np.array([a[1]-b[1], a[0]-b[0]], float); n = np.linalg.norm(v)
            if n: dirv = v/n
            cur = best
        else:
            live = [p for p in px if unused[p]]
            if not live: break
            last = runs[-1][-1]
            cur = min(live, key=lambda p: (p[0]-last[0])**2 + (p[1]-last[1])**2)
            runs.append([cur]); dirv = np.array([1.0, 0.0])
    return runs


def resample_run(run, spacing):
    pts = np.array(run, float)[:, ::-1]
    if len(pts) < 2: return pts
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    if d[-1] < spacing: return pts[:1]
    u = np.arange(0, d[-1], spacing)
    return np.stack([np.interp(u, d, pts[:, 0]), np.interp(u, d, pts[:, 1])], 1)


def main(project_dir):
    cfg = load_project(project_dir)
    spacing = cfg["source"].get("discSpacing", 7)
    arr, meta = render_word(project_dir, cfg)
    h, w = arr.shape
    dist = ndimage.distance_transform_edt(arr > 110)
    skel = np.load(os.path.join(project_dir, "build", "skel.npy"))
    grid = np.zeros((h, w), bool); grid[skel[:, 1], skel[:, 0]] = True

    runs = greedy_order(grid)
    discs = []
    for run in runs:
        for x, y in resample_run(run, spacing):
            r = float(dist[int(round(y)), int(round(x))])
            if r >= 2: discs.append([float(x), float(y), r])

    xs = [d[0] for d in discs]; ys = [d[1] for d in discs]
    model = {"w": w, "h": h, "y_mid": float(np.mean(ys)),
             "x0": min(xs), "x1": max(xs), "n": len(discs), "discs": discs}
    json.dump(model, open(os.path.join(project_dir, "build", "model.json"), "w"))
    rs = [d[2] for d in discs]
    print(f"[model] runs={len(runs)} discs={len(discs)} r=[{min(rs):.1f}..{max(rs):.1f}]")


if __name__ == "__main__":
    main(sys.argv[1])
