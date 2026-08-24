"""A07 - why conformity broke: same-grid gap map, ORIGINAL vs CURRENT.

Frames
------
CURRENT  : origin = DATUM_P              (lowered joystick centre)
ORIGINAL : origin = DATUM_P - THUMB_DELTA (original joystick centre)
Both use the same axes (U, V, -N).  Because the Thumb cartridge moved by a pure
translation, a given (u, v) addresses the SAME cartridge feature in both frames.
Any change in the gap map is therefore caused by the shell, not by the part.

Per column (u, v):
    nWallInner   = inner surface of the Thumb wall
    nPartOuter   = outermost cartridge material in that column
    gap          = nWallInner - nPartOuter     ( >0 clearance, <0 interference )
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402

OUT = L.LAB / "03_original_thumb_analysis"
OUT2 = L.LAB / "04_current_thumb_analysis"

ORIG_P = L.DATUM_P - L.THUMB_DELTA
CROP_LO = (-32.0, -54.0, -60.0)
CROP_HI = (32.0, 24.0, 60.0)
PITCH = 0.5
GRID_LO = (-26.0, -50.0)
GRID_HI = (26.0, 14.0)


def to_frame(points, origin):
    d = np.atleast_2d(np.asarray(points, float)) - origin
    return np.stack([d @ L.DATUM_U, d @ L.DATUM_V, d @ (-L.DATUM_N)], axis=1)


def tri_frame(shape, origin, tol=0.10, ang=0.18):
    T = L.triangles(shape, tol=tol, ang=ang)
    return to_frame(T.reshape(-1, 3), origin).reshape(-1, 3, 3)


class ColumnField:
    """All ray/column crossings of a triangle soup, for a whole (u, v) grid."""

    def __init__(self, T: np.ndarray):
        self.a, b, c = T[:, 0], T[:, 1], T[:, 2]
        self.e1 = b - self.a
        self.e2 = c - self.a
        self.tu0 = T[:, :, 0].min(axis=1)
        self.tu1 = T[:, :, 0].max(axis=1)
        self.tv0 = T[:, :, 1].min(axis=1)
        self.tv1 = T[:, :, 1].max(axis=1)
        self.det = self.e1[:, 0] * self.e2[:, 1] - self.e1[:, 1] * self.e2[:, 0]
        self.ok = np.abs(self.det) > 1.0e-14

    def hits(self, u: float, v: float, cand: np.ndarray) -> np.ndarray:
        if cand.size == 0:
            return np.zeros(0)
        a, e1, e2 = self.a[cand], self.e1[cand], self.e2[cand]
        det, ok = self.det[cand], self.ok[cand]
        du = u - a[:, 0]
        dv = v - a[:, 1]
        s = np.where(ok, (du * e2[:, 1] - dv * e2[:, 0]) / np.where(ok, det, 1.0), -1.0)
        t = np.where(ok, (e1[:, 0] * dv - e1[:, 1] * du) / np.where(ok, det, 1.0), -1.0)
        good = ok & (s >= 0.0) & (t >= 0.0) & (s + t <= 1.0)
        if not good.any():
            return np.zeros(0)
        h = np.sort(a[good, 2] + s[good] * e1[good, 2] + t[good] * e2[good, 2])
        keep = np.ones(h.size, bool)
        keep[1:] = np.diff(h) > 1.0e-7
        return h[keep]

    def candidates(self, u: float, v: float) -> np.ndarray:
        return np.nonzero((self.tu0 <= u) & (self.tu1 >= u) &
                          (self.tv0 <= v) & (self.tv1 >= v))[0]


def combined_shell(ka: str, kb: str, box, tag: str):
    a = L.load(ka)
    sa, _ = L.as_single_solid((a & box).clean(), "A")
    del a
    b = L.load(kb)
    sb, _ = L.as_single_solid((b & box).clean(), "B")
    del b
    out, _ = L.as_single_solid((sa + sb).clean(), tag)
    L.memory("combined " + tag)
    return out


def backplate(key: str):
    root = import_step(L.SRC[key])
    hit = None

    def walk(shape):
        nonlocal hit
        kids = list(getattr(shape, "children", []) or [])
        if kids:
            for k in kids:
                walk(k)
            return
        if "BACKPLATE" in str(shape.label).upper() and shape.solids():
            hit = shape
    walk(root)
    if hit is None:
        raise RuntimeError("no backplate in " + key)
    out, _ = L.as_single_solid(hit, "BACKPLATE")
    return out


def analyse(tag, shell, part, origin, wall_seed):
    Ts = tri_frame(shell, origin)
    Tp = tri_frame(part, origin, tol=0.08, ang=0.15)
    fs, fp = ColumnField(Ts), ColumnField(Tp)
    U = np.arange(GRID_LO[0], GRID_HI[0] + 1e-9, PITCH)
    V = np.arange(GRID_LO[1], GRID_HI[1] + 1e-9, PITCH)
    wall_inner = np.full((len(U), len(V)), np.nan)
    wall_outer = np.full((len(U), len(V)), np.nan)
    part_outer = np.full((len(U), len(V)), np.nan)
    part_inner = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        cs = fs.candidates(u, 0.0) if False else None
        for j, v in enumerate(V):
            hs = fs.hits(u, v, fs.candidates(u, v))
            if hs.size and hs.size % 2 == 0:
                # Thumb wall = the slab whose inner face is nearest wall_seed
                slab = [(hs[k], hs[k + 1]) for k in range(0, hs.size, 2)]
                cand = [p for p in slab if p[1] > wall_seed - 12.0]
                if cand:
                    p = min(cand, key=lambda q: abs(q[0] - wall_seed))
                    wall_inner[i, j], wall_outer[i, j] = p[0], p[1]
            hp = fp.hits(u, v, fp.candidates(u, v))
            if hp.size:
                part_outer[i, j] = hp.max()
                part_inner[i, j] = hp.min()
    gap = wall_inner - part_outer
    ok = np.isfinite(gap)
    stats = {
        "columnsWithBothMaterial": int(ok.sum()),
        "gapMinMm": float(np.nanmin(gap)) if ok.any() else None,
        "gapMaxMm": float(np.nanmax(gap)) if ok.any() else None,
        "gapMeanMm": float(np.nanmean(gap)) if ok.any() else None,
        "gapMedianMm": float(np.nanmedian(gap)) if ok.any() else None,
        "columnsInterfering": int((gap < 0).sum()),
        "columnsWithin0p5mm": int(((gap >= 0) & (gap <= 0.5)).sum()),
        "columnsWithin1p0mm": int(((gap >= 0) & (gap <= 1.0)).sum()),
        "columnsGapOver3mm": int((gap > 3.0).sum()),
        "columnsGapOver6mm": int((gap > 6.0).sum()),
        "wallInnerRange": [float(np.nanmin(wall_inner)), float(np.nanmax(wall_inner))],
        "partOuterRange": [float(np.nanmin(part_outer)), float(np.nanmax(part_outer))],
    }
    print("\n=== %s ===" % tag)
    print("  columns with both shell wall and part material : %d" % stats["columnsWithBothMaterial"])
    print("  gap  min/median/mean/max = %+.3f / %+.3f / %+.3f / %+.3f mm"
          % (stats["gapMinMm"], stats["gapMedianMm"], stats["gapMeanMm"], stats["gapMaxMm"]))
    print("  interfering columns      = %d" % stats["columnsInterfering"])
    print("  columns gap <= 0.5 mm    = %d   (conformal contact band)" % stats["columnsWithin0p5mm"])
    print("  columns gap <= 1.0 mm    = %d" % stats["columnsWithin1p0mm"])
    print("  columns gap  > 3.0 mm    = %d" % stats["columnsGapOver3mm"])
    print("  columns gap  > 6.0 mm    = %d" % stats["columnsGapOver6mm"])
    print("  shell wall inner n range = [%.3f, %.3f]" % tuple(stats["wallInnerRange"]))
    print("  part outer      n range  = [%.3f, %.3f]" % tuple(stats["partOuterRange"]))
    return stats, U, V, wall_inner, wall_outer, part_outer, part_inner, gap


def main() -> int:
    box_cur = L.local_box(CROP_LO, CROP_HI, "CUR")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box_cur, "FROZEN")

    # original-frame crop box, built by shifting the same local window
    lo_o = np.asarray(CROP_LO, float)
    hi_o = np.asarray(CROP_HI, float)
    pts = np.stack([lo_o, hi_o])
    world = np.asarray([ORIG_P + p[0] * L.DATUM_U + p[1] * L.DATUM_V + p[2] * (-L.DATUM_N)
                        for p in pts])
    loc = L.to_local(world)
    box_orig = L.local_box(loc[0], loc[1], "ORIG")
    clean = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER", box_orig, "CLEAN")

    bp_orig = backplate("ORIGINAL_THUMB_CARTRIDGE")
    bp_low = backplate("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    print("backplate volume original=%.4f lowered=%.4f mm3" % (L.vol(bp_orig), L.vol(bp_low)))
    L.memory("loaded backplates")

    res = {}
    s1 = analyse("ORIGINAL  (original Backplate vs CLEAN shell, original frame)",
                 clean, bp_orig, ORIG_P, wall_seed=9.0)
    res["ORIGINAL"] = s1[0]
    np.savez_compressed(OUT / "a07_original_gap.npz", U=s1[1], V=s1[2],
                        wall_inner=s1[3], wall_outer=s1[4], part_outer=s1[5],
                        part_inner=s1[6], gap=s1[7])
    del clean, bp_orig
    L.memory("original analysed")

    s2 = analyse("CURRENT   (lowered Backplate vs FROZEN shell, lowered frame)",
                 frozen, bp_low, L.DATUM_P, wall_seed=12.0)
    res["CURRENT"] = s2[0]
    np.savez_compressed(OUT2 / "a07_current_gap.npz", U=s2[1], V=s2[2],
                        wall_inner=s2[3], wall_outer=s2[4], part_outer=s2[5],
                        part_inner=s2[6], gap=s2[7])
    L.memory("current analysed")

    L.write_json(OUT2 / "a07_conformity_map.json",
                 {"originFrames": {"CURRENT": L.DATUM_P.tolist(), "ORIGINAL": ORIG_P.tolist()},
                  "gridPitchMm": PITCH, "gridLocal": {"min": list(GRID_LO), "max": list(GRID_HI)},
                  "stats": res, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
