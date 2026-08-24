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

    img = Image.new("RGB", (W, H), bg)
    base = img.copy()
    order = np.argsort(-depth)
    draw = ImageDraw.Draw(img)
    for k in order:
        c = tuple(int(np.clip(v * shade[k], 0, 255)) for v in C[k])
        poly = [(sx[k, 0], sy[k, 0]), (sx[k, 1], sy[k, 1]), (sx[k, 2], sy[k, 2])]
        if A[k] >= 0.999:
            draw.polygon(poly, fill=c)
        else:
            ov = Image.new("RGB", (W, H))
            od = ImageDraw.Draw(ov)
            od.polygon(poly, fill=c)
            mask = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mask).polygon(poly, fill=int(255 * A[k]))
            img = Image.composite(Image.blend(img, ov, 1.0), img, mask)
            draw = ImageDraw.Draw(img)
    del base

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
