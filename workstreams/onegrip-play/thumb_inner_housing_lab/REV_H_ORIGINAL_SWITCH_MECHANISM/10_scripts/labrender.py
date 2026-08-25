"""Minimal self-contained rasteriser for the Thumb Lab.

Deliberately not importing any production render module.

Two rules taken from earlier repo mistakes:
  * every triangle of every part is depth-sorted TOGETHER.  Drawing part by part
    lets a later part paint over an earlier one and invents features that are
    not there.
  * section clipping keeps a triangle only when all three vertices are on the
    keep side.  Clipping by centroid leaves spikes across the cut plane.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _font(size):
    for name in ("consola.ttf", "arial.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def clip_half(T: np.ndarray, point, normal) -> np.ndarray:
    """Keep triangles entirely on the -normal side of the plane."""
    p = np.asarray(point, float)
    n = np.asarray(normal, float)
    d = (T.reshape(-1, 3) - p) @ n
    keep = (d.reshape(-1, 3) <= 0.0).all(axis=1)
    return T[keep]


def render(path: Path, layers, camera_dir, up_hint, title, subtitle, footer,
           size=(1500, 1000), ss=2, fit=None, bg=(250, 250, 250),
           world_lines=None, world_labels=None):
    """layers: list of (triangles(n,3,3), rgb, alpha, label).

    world_lines : list of (p0, p1, rgba, width, label) drawn after the solids
    world_labels: list of (point3, text, rgb) drawn as leader-free callouts
    """
    W, H = size[0] * ss, size[1] * ss
    tris, cols, alphas = [], [], []
    for T, rgb, alpha, _ in layers:
        if len(T) == 0:
            continue
        tris.append(T)
        cols.append(np.repeat(np.asarray([rgb], float), len(T), axis=0))
        alphas.append(np.full(len(T), float(alpha)))
    if not tris:
        raise RuntimeError("nothing to render")
    T = np.concatenate(tris)
    C = np.concatenate(cols)
    A = np.concatenate(alphas)

    fwd = np.asarray(camera_dir, float)
    fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, np.asarray(up_hint, float))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)

    pts = T.reshape(-1, 3) if fit is None else np.asarray(fit, float).reshape(-1, 3)
    centre = pts.mean(axis=0)
    px = (pts - centre) @ right
    py = (pts - centre) @ up
    span_x = max(px.max() - px.min(), 1e-6)
    span_y = max(py.max() - py.min(), 1e-6)
    scale = min(W * 0.84 / span_x, H * 0.74 / span_y)

    P = T.reshape(-1, 3) - centre
    sx = W * 0.5 + (P @ right) * scale
    sy = H * 0.52 - (P @ up) * scale
    depth = (P @ fwd).reshape(-1, 3).mean(axis=1)
    sx = sx.reshape(-1, 3)
    sy = sy.reshape(-1, 3)

    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(nrm, axis=1)
    ok = ln > 1e-12
    nrm[ok] /= ln[ok][:, None]
    shade = 0.34 + 0.66 * np.abs(nrm @ fwd)

    # Painter's algorithm into a numpy RGB buffer.
    #
    # The previous version created a full W x H PIL image, drew ONE polygon into
    # it, built a full-size mask and composited the whole canvas -- once per
    # triangle.  With three transparent shells overlaid that is tens of
    # thousands of full-canvas composites and a single section took ~15 minutes.
    # Rasterising each triangle into its own bounding box and blending only
    # those pixels does the same thing in seconds.
    buf = np.empty((H, W, 3), np.float64)
    buf[:] = np.asarray(bg, float)
    order = np.argsort(-depth)
    xs, ys = sx[order], sy[order]
    cols = C[order] * shade[order][:, None]
    als = A[order]
    for k in range(len(order)):
        x0 = int(max(0, np.floor(xs[k].min())))
        x1 = int(min(W - 1, np.ceil(xs[k].max())))
        y0 = int(max(0, np.floor(ys[k].min())))
        y1 = int(min(H - 1, np.ceil(ys[k].max())))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5,
                             np.arange(y0, y1 + 1) + 0.5)
        ax_, ay_ = xs[k, 0], ys[k, 0]
        bx_, by_ = xs[k, 1], ys[k, 1]
        cx_, cy_ = xs[k, 2], ys[k, 2]
        den = (by_ - cy_) * (ax_ - cx_) + (cx_ - bx_) * (ay_ - cy_)
        if abs(den) < 1e-12:
            continue
        w0 = ((by_ - cy_) * (gx - cx_) + (cx_ - bx_) * (gy - cy_)) / den
        w1 = ((cy_ - ay_) * (gx - cx_) + (ax_ - cx_) * (gy - cy_)) / den
        w2 = 1.0 - w0 - w1
        m = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if not m.any():
            continue
        tile = buf[y0:y1 + 1, x0:x1 + 1]
        al = float(als[k])
        tile[m] = tile[m] * (1.0 - al) + cols[k] * al
    img = Image.fromarray(np.clip(buf, 0, 255).astype(np.uint8), "RGB")

    img = img.resize(size, Image.LANCZOS)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, size[0], 74], fill=(24, 28, 34))
    d.text((18, 12), title, font=_font(26), fill=(255, 255, 255))
    d.text((18, 46), subtitle, font=_font(16), fill=(178, 190, 205))
    d.rectangle([0, size[1] - 58, size[0], size[1]], fill=(24, 28, 34))
    d.text((18, size[1] - 50), footer, font=_font(14), fill=(178, 190, 205))
    y = 92
    for _, rgb, alpha, label in layers:
        if not label:
            continue
        d.rectangle([18, y, 44, y + 16], fill=tuple(int(v) for v in rgb),
                    outline=(40, 40, 40))
        d.text((54, y), "%s%s" % (label, "" if alpha >= 0.999 else "  (transparent)"),
               font=_font(15), fill=(28, 32, 38))
        y += 24
    # ---- 3-D overlays, projected with the SAME camera ------------------
    def proj(p):
        q = np.asarray(p, float) - centre
        return (size[0] * 0.5 + float(q @ right) * scale / ss,
                size[1] * 0.52 - float(q @ up) * scale / ss)

    for p0, p1, rgba, wdt, lbl in (world_lines or []):
        a0, a1 = proj(p0), proj(p1)
        d.line([a0, a1], fill=tuple(int(x) for x in rgba[:3]), width=int(wdt))
        if lbl:
            d.text((a1[0] + 6, a1[1] - 8), lbl, font=_font(14),
                   fill=tuple(int(x) for x in rgba[:3]))
    for pt, text, rgb in (world_labels or []):
        x, y = proj(pt)
        col = tuple(int(v) for v in rgb)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=col, outline=(255, 255, 255))
        d.rectangle([x + 8, y - 11, x + 12 + 7 * len(text), y + 8], fill=(255, 255, 255))
        d.text((x + 11, y - 9), text, font=_font(14), fill=col)

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print("  render -> %s" % path.name)
