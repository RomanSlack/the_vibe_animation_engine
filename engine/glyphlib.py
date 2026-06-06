"""Shared glyph helpers for the animation engine.

Renders a project's word in its font to a filled bitmap. Used by both
extract_skeleton.py (needs the silhouette) and build_model.py (needs the
distance transform for disc radii). Keeping it here means the two stages
render the glyph identically.
"""
import json, os
import numpy as np
from PIL import Image, ImageFont, ImageDraw


def load_project(project_dir):
    cfg = json.load(open(os.path.join(project_dir, "project.json")))
    return cfg


def render_word(project_dir, cfg=None):
    """Return (bitmap np.uint8 LxW, meta dict). Glyph is white(255) on black(0)."""
    cfg = cfg or load_project(project_dir)
    s = cfg["source"]
    font_path = os.path.join(project_dir, s["font"])
    font = ImageFont.truetype(font_path, s["fontSize"])
    pad = s.get("pad", 60)
    word = s["word"]
    box = ImageDraw.Draw(Image.new("L", (10, 10))).textbbox((0, 0), word, font=font)
    w = box[2] - box[0] + 2 * pad
    h = box[3] - box[1] + 2 * pad
    img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(img).text((pad - box[0], pad - box[1]), word, fill=255, font=font)
    return np.array(img), {"w": w, "h": h}
