#!/usr/bin/env python3
"""
Ordered medial discs: like medial.py, but the discs come out in pen-stroke
order (with an even arc-length spacing) so the animation can:
  - draw "belo" on in the order it's written, and
  - straighten it like a snake pulled taut (arc-length -> position on a line).

Ordering = greedy stroke-follower over the skeleton: walk pixel-to-pixel
choosing the neighbour that best continues recent direction (edges consumed,
so loop crossings are traced by "going straight"); when it dead-ends with
edges still unused, resume from the nearest pixel that still has an unused
edge (a short, mostly-invisible hop between letters). Contiguous runs are
resampled separately so no discs land in the hop gaps.

Outputs:
  out/medial.json          {w,h,y_mid,x0,x1,n, discs:[[x,y,r],...]}  IN ORDER
  out/preview_order2.png   gradient blue->red showing the stroke order
"""
import json, numpy as np
from scipy import ndimage
from PIL import Image, ImageFont, ImageDraw

FONT = "../assets/Bumbbled.otf"
WORD = "belo"
FONT_PX = 380
PAD = 60
OUT = "../out"
SPACING = 7.0

N8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
RING = [(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1)]


def render_word():
    font = ImageFont.truetype(FONT, FONT_PX)
    box = ImageDraw.Draw(Image.new("L", (10,10))).textbbox((0,0), WORD, font=font)
    w = box[2]-box[0]+2*PAD; h = box[3]-box[1]+2*PAD
    img = Image.new("L", (w,h), 0)
    ImageDraw.Draw(img).text((PAD-box[0], PAD-box[1]), WORD, fill=255, font=font)
    return np.array(img)


def neighbours(grid, y, x):
    H, W = grid.shape
    return [(y+dy, x+dx) for dy, dx in N8
            if 0 <= y+dy < H and 0 <= x+dx < W and grid[y+dy, x+dx]]


def branch_count(grid, y, x):
    H, W = grid.shape
    vals = [0 <= y+dy < H and 0 <= x+dx < W and grid[y+dy, x+dx] for dy, dx in RING]
    return sum(1 for i in range(8) if vals[i] and not vals[i-1])


def greedy_order(grid):
    ys, xs = np.nonzero(grid)
    px = list(zip(ys.tolist(), xs.tolist()))
    start = min(px, key=lambda p: (p[1], p[0]))   # leftmost pixel -> draw L->R

    # adjacency, then drop redundant diagonal edges (the hypotenuse of each
    # 8-connectivity triangle) so staircases become clean degree-2 paths
    unused = {p: set(neighbours(grid, *p)) for p in px}
    for p in px:
        for q in list(unused[p]):
            if p[0] != q[0] and p[1] != q[1] and (unused[p] & unused[q]):
                unused[p].discard(q); unused[q].discard(p)

    runs = [[start]]
    cur = start
    dirv = np.array([1.0, 0.0])

    def consume(a, b):
        unused[a].discard(b); unused[b].discard(a)

    while True:
        cand = list(unused[cur])
        if cand:
            best, bs = None, -2.0
            for p in cand:
                v = np.array([p[1]-cur[1], p[0]-cur[0]], float); v /= (np.linalg.norm(v) or 1)
                sc = float(np.dot(v, dirv))
                if sc > bs: bs, best = sc, p
            consume(cur, best)
            runs[-1].append(best)
            k = min(6, len(runs[-1]) - 1)
            a = np.array(runs[-1][-1]); b = np.array(runs[-1][-1-k])
            v = np.array([a[1]-b[1], a[0]-b[0]], float); n = np.linalg.norm(v)
            if n: dirv = v/n
            cur = best
        else:
            # resume from nearest pixel that still has an unused edge
            live = [p for p in px if unused[p]]
            if not live:
                break
            cur = min(live, key=lambda p: (p[0]-runs[-1][-1][0])**2 + (p[1]-runs[-1][-1][1])**2)
            runs.append([cur])
            dirv = np.array([1.0, 0.0])
    total = sum(len(r) for r in runs)
    print(f"  runs: {len(runs)}  ordered px: {total} of ~{int(grid.sum())}")
    return runs


def resample_run(run, spacing):
    pts = np.array(run, float)[:, ::-1]      # (x,y)
    if len(pts) < 2:
        return pts
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    if d[-1] < spacing:
        return pts[:1]
    u = np.arange(0, d[-1], spacing)
    x = np.interp(u, d, pts[:, 0]); y = np.interp(u, d, pts[:, 1])
    return np.stack([x, y], 1)


def main():
    arr = render_word()
    binary = arr > 110
    h, w = binary.shape
    dist = ndimage.distance_transform_edt(binary)
    skel = np.load(f"{OUT}/skel_pts.npy")
    grid = np.zeros((h, w), bool); grid[skel[:,1], skel[:,0]] = True

    runs = greedy_order(grid)
    ordered = []
    for run in runs:
        for x, y in resample_run(run, SPACING):
            r = float(dist[int(round(y)), int(round(x))])
            if r >= 2:
                ordered.append((float(x), float(y), r))
    print(f"  ordered discs: {len(ordered)}")

    xs = [d[0] for d in ordered]; ys = [d[1] for d in ordered]
    meta = {"w": w, "h": h, "y_mid": float(np.mean(ys)),
            "x0": min(xs), "x1": max(xs), "n": len(ordered),
            "discs": [[x, y, r] for x, y, r in ordered]}
    json.dump(meta, open(f"{OUT}/medial.json", "w"))
    print(f"  wrote {OUT}/medial.json (ordered)")

    # gradient preview of stroke order
    prev = np.zeros((h, w, 3), np.uint8)
    prev[grid] = (40, 40, 50)
    M = len(ordered)
    for idx, (x, y, r) in enumerate(ordered):
        f = idx/(M-1)
        col = (int(40+215*(1-f)), int(40+50*abs(0.5-f)*2), int(40+215*f))
        xi, yi = int(round(x)), int(round(y))
        for dy in range(-3,4):
            for dx in range(-3,4):
                if 0<=yi+dy<h and 0<=xi+dx<w and dx*dx+dy*dy<=9:
                    prev[yi+dy, xi+dx] = col
    Image.fromarray(prev).save(f"{OUT}/preview_order2.png")
    print(f"  wrote {OUT}/preview_order2.png")


if __name__ == "__main__":
    main()
