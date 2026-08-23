"""
SZH-EK056 / KY-023 photo measurement helper.

READ-ONLY with respect to OneGrip production geometry.
This script only loads reference photographs and produces annotated
crops + a homography solver so that pixel picks can be converted to
millimetres on the PCB plane.

Usage:
  python szh_photo_measure.py grid   <img> <out> [step] [scale]
  python szh_photo_measure.py crop   <img> <out> x0 y0 x1 y1 [zoom] [step]
"""

from __future__ import annotations

import sys
from PIL import Image, ImageDraw

# ------------------------------------------------------------------ grid


def _draw_grid(im: Image.Image, step: int, off_x: float = 0.0,
               off_y: float = 0.0, zoom: float = 1.0) -> Image.Image:
    """Overlay a labelled pixel grid.  Labels are in ORIGINAL image pixels."""
    im = im.convert("RGB")
    d = ImageDraw.Draw(im)
    w, h = im.size

    # minor + major lines
    x = 0
    while x < w:
        orig = off_x + x / zoom
        major = (round(orig) % (step * 5)) < (1.0 / zoom)
        col = (255, 60, 60) if major else (0, 200, 255)
        d.line([(x, 0), (x, h)], fill=col, width=1)
        if major:
            d.text((x + 2, 2), f"{orig:.0f}", fill=(255, 255, 0))
        x += int(round(step * zoom))

    y = 0
    while y < h:
        orig = off_y + y / zoom
        major = (round(orig) % (step * 5)) < (1.0 / zoom)
        col = (255, 60, 60) if major else (0, 200, 255)
        d.line([(0, y), (w, y)], fill=col, width=1)
        if major:
            d.text((2, y + 2), f"{orig:.0f}", fill=(255, 255, 0))
        y += int(round(step * zoom))
    return im


def cmd_grid(argv):
    src, out = argv[0], argv[1]
    step = int(argv[2]) if len(argv) > 2 else 25
    scale = float(argv[3]) if len(argv) > 3 else 1.0
    im = Image.open(src)
    if scale != 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)),
                       Image.LANCZOS)
    _draw_grid(im, step, 0.0, 0.0, scale).save(out)
    print(f"{out}  {im.size}  step={step}px  scale={scale}")


def cmd_crop(argv):
    src, out = argv[0], argv[1]
    x0, y0, x1, y1 = (int(v) for v in argv[2:6])
    zoom = float(argv[6]) if len(argv) > 6 else 3.0
    step = int(argv[7]) if len(argv) > 7 else 10
    im = Image.open(src).crop((x0, y0, x1, y1))
    im = im.resize((int(im.width * zoom), int(im.height * zoom)),
                   Image.LANCZOS)
    # brighten: these boards are near-black on near-black
    if len(argv) <= 8 or argv[8] != "raw":
        im = _autolevel(im)
    _draw_grid(im, step, x0, y0, zoom).save(out)
    print(f"{out}  crop=({x0},{y0})-({x1},{y1})  zoom={zoom}  step={step}px")


def _autolevel(im: Image.Image) -> Image.Image:
    import numpy as np
    a = np.asarray(im.convert("RGB")).astype(float)
    lo, hi = np.percentile(a, 1.0), np.percentile(a, 99.0)
    if hi - lo < 1e-6:
        return im
    a = (a - lo) / (hi - lo) * 255.0
    return Image.fromarray(a.clip(0, 255).astype("uint8"))


# ------------------------------------------------------- homography (mm)


def homography(src_pts, dst_pts):
    """Solve H so that H @ [x,y,1] ~ [X,Y,1].  4+ correspondences."""
    import numpy as np
    A = []
    for (x, y), (X, Y) in zip(src_pts, dst_pts):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y, -X])
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y, -Y])
    A = np.asarray(A, float)
    _, _, vt = np.linalg.svd(A)
    H = vt[-1].reshape(3, 3)
    return H / H[2, 2]


def apply_h(H, pts):
    import numpy as np
    p = np.asarray(pts, float)
    p = np.hstack([p, np.ones((len(p), 1))])
    q = (H @ p.T).T
    return q[:, :2] / q[:, 2:3]


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"grid": cmd_grid, "crop": cmd_crop}[cmd](sys.argv[2:])
