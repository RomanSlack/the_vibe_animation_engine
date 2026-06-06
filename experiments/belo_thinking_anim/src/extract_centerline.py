#!/usr/bin/env python3
"""
Extract a single continuous centerline ("pen stroke") from the filled
Bumbbled rendering of the word "belo".

Pipeline:
  1. Render "belo" filled (black on white) at high resolution via PIL.
  2. Binarize.
  3. Skeletonize via Zhang-Suen thinning (numpy, no skimage dependency).
  4. Save a preview overlay (glyph in grey, skeleton in red) for eyeballing.

Ordering the skeleton into one continuous path is a separate step
(order_path.py) once we're happy with skeleton quality.
"""
import sys, json
import numpy as np
from PIL import Image, ImageFont, ImageDraw

FONT = "../assets/Bumbbled.otf"
WORD = "belo"
FONT_PX = 380          # render size for the glyph (big = cleaner skeleton)
PAD = 60               # padding around the word
OUT_DIR = "../out"


def render_word():
    font = ImageFont.truetype(FONT, FONT_PX)
    # measure
    tmp = Image.new("L", (10, 10), 0)
    d = ImageDraw.Draw(tmp)
    box = d.textbbox((0, 0), WORD, font=font)
    w = box[2] - box[0] + 2 * PAD
    h = box[3] - box[1] + 2 * PAD
    img = Image.new("L", (w, h), 0)            # black bg
    d = ImageDraw.Draw(img)
    d.text((PAD - box[0], PAD - box[1]), WORD, fill=255, font=font)  # white glyph
    return img


def zhang_suen(binary):
    """Zhang-Suen thinning. Input: bool array (True = foreground)."""
    img = binary.astype(np.uint8).copy()
    changed = True
    def neighbours(y, x, im):
        return [im[y-1, x], im[y-1, x+1], im[y, x+1], im[y+1, x+1],
                im[y+1, x], im[y+1, x-1], im[y, x-1], im[y-1, x-1]]
    def transitions(n):
        n2 = n + n[:1]
        return sum((a, b) == (0, 1) for a, b in zip(n2, n2[1:]))
    while changed:
        changed = False
        for step in (0, 1):
            to_del = []
            ys, xs = np.nonzero(img[1:-1, 1:-1])
            ys += 1; xs += 1
            for y, x in zip(ys, xs):
                P = neighbours(y, x, img)
                p2, p3, p4, p5, p6, p7, p8, p9 = P
                B = sum(P)
                if not (2 <= B <= 6):
                    continue
                if transitions(P) != 1:
                    continue
                if step == 0:
                    if p2 * p4 * p6 != 0: continue
                    if p4 * p6 * p8 != 0: continue
                else:
                    if p2 * p4 * p8 != 0: continue
                    if p2 * p6 * p8 != 0: continue
                to_del.append((y, x))
            if to_del:
                changed = True
                for y, x in to_del:
                    img[y, x] = 0
    return img.astype(bool)


def main():
    img = render_word()
    arr = np.array(img)
    binary = arr > 110
    print(f"glyph bitmap: {binary.shape}, fg px: {binary.sum()}")

    skel = zhang_suen(binary)
    print(f"skeleton px: {skel.sum()}")

    # preview overlay: glyph dark grey, skeleton red
    h, w = binary.shape
    prev = np.zeros((h, w, 3), np.uint8)
    prev[binary] = (70, 70, 80)
    prev[skel] = (255, 40, 40)
    Image.fromarray(prev).save(f"{OUT_DIR}/preview_skeleton.png")
    print(f"wrote {OUT_DIR}/preview_skeleton.png")

    # stash raw skeleton coords for the ordering step
    ys, xs = np.nonzero(skel)
    np.save(f"{OUT_DIR}/skel_pts.npy", np.stack([xs, ys], 1))
    json.dump({"w": w, "h": h}, open(f"{OUT_DIR}/skel_meta.json", "w"))


if __name__ == "__main__":
    main()
