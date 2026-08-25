"""E01 - what does C01 actually have at the two ORIGINAL load-transfer zones?

Before designing anything, establish:
  * does the C01 plate reach the LEFT and RIGHT perimeter zones at all
  * how thick is it there
  * what is the gap there
  * how oblique is the shell wall there  (|m.n|, the cosine between the wall
    normal and the local n axis)

That last one decides the construction.  The conformal band is built by
translating the shell along n, so a plate built with skin depth t along n ends
up t*|m.n| thick measured along its own normal.  Wherever |m.n| falls the plate
tapers - that is the mechanism behind C01's knife edge, and it also tells us how
deep the band has to be to keep >= 1.60 mm at the perimeter.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from d02_housing_vs_exact import BP_LOW_STEP, C01_STEP, Field, approved_shell  # noqa: E402

OUT = L.LAB / "01_probe"
OUTWARD = -L.DATUM_N
PITCH = 0.25

ZONES = {
    "LEFT": {"u": (-20.0, -12.0), "v": (-49.0, -30.8), "targetMm2": 71.69},
    "RIGHT": {"u": (13.3, 19.5), "v": (-49.0, -40.3), "targetMm2": 23.38},
}


def wall_cos_map(shell, U, V):
    """|m . n| of the Thumb wall's inner surface, per column."""
    T = L.local_triangles(shell, tol=0.05, ang=0.10)
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    nrm = np.cross(b - a, c - a)
    ln = np.linalg.norm(nrm, axis=1)
    ok = ln > 1e-12
    nrm[ok] /= ln[ok][:, None]
    f = Field(T)
    cos = np.full((len(U), len(V)), np.nan)
    inner = np.full((len(U), len(V)), np.nan)
    # per column, find the wall inner face, then take the normal of the triangle
    # that produced it
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            cand = f.order[:np.searchsorted(f.tu0s, u, side="right")]
            cand = cand[f.tu1[cand] >= u]
            if cand.size == 0:
                continue
            sel = cand[(f.tv0[cand] <= v) & (f.tv1[cand] >= v)]
            if sel.size == 0:
                continue
            A, E1, E2 = f.a[sel], f.e1[sel], f.e2[sel]
            d, o = f.det[sel], f.ok[sel]
            du, dv = u - A[:, 0], v - A[:, 1]
            s = np.where(o, (du * E2[:, 1] - dv * E2[:, 0]) / np.where(o, d, 1.0), -1.0)
            t = np.where(o, (E1[:, 0] * dv - E1[:, 1] * du) / np.where(o, d, 1.0), -1.0)
            g = o & (s >= 0) & (t >= 0) & (s + t <= 1)
            if not g.any():
                continue
            hits = A[g, 2] + s[g] * E1[g, 2] + t[g] * E2[g, 2]
            tri = sel[g]
            order = np.argsort(hits)
            hits, tri = hits[order], tri[order]
            keep = np.ones(hits.size, bool)
            keep[1:] = np.diff(hits) > 1e-7
            hits, tri = hits[keep], tri[keep]
            if hits.size % 2:
                continue
            # the Thumb wall = the outermost slab; its inner face is hits[-2]
            if hits.size < 2:
                continue
            inner[i, j] = float(hits[-2])
            m = nrm[tri[-2]]
            # express in local frame
            mn = abs(float(m @ L.DATUM_U * 0 + 0))  # placeholder, replaced below
            mm = np.asarray([m @ L.DATUM_U, m @ L.DATUM_V, m @ OUTWARD], float) \
                if m.shape == (3,) else None
            cos[i, j] = abs(float(m[2]))  # T is already in local coords
    return cos, inner


def main() -> int:
    approved = approved_shell()
    c01 = import_step(str(C01_STEP))
    c01, _ = L.as_single_solid(c01, "C01")
    bp = import_step(str(BP_LOW_STEP))
    bp, _ = L.as_single_solid(bp, "BACKPLATE_LOWERED")
    L.memory("loaded")

    U = np.arange(-22.0, 22.0 + 1e-9, PITCH)
    V = np.arange(-52.0, 16.0 + 1e-9, PITCH)
    cell = PITCH * PITCH

    fp = Field(L.local_triangles(c01, tol=0.05, ang=0.10))
    fb = Field(L.local_triangles(bp, tol=0.05, ang=0.10))
    fs = Field(L.local_triangles(approved, tol=0.06, ang=0.12))
    tc = np.zeros((len(U), len(V)))
    gc = np.full((len(U), len(V)), np.nan)
    tb = np.zeros((len(U), len(V)))
    gb = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            hs = fs.hits(u, v)
            for (f, tt, gg) in ((fp, tc, gc), (fb, tb, gb)):
                h = f.hits(u, v)
                if h.size == 0 or h.size % 2:
                    continue
                tt[i, j] = float(sum(h[k + 1] - h[k] for k in range(0, h.size, 2)))
                if hs.size and hs.size % 2 == 0:
                    cand = [hs[k] for k in range(0, hs.size, 2) if hs[k] > h.max() - 1e-3]
                    if cand:
                        gg[i, j] = min(cand) - h.max()
    L.memory("maps")

    cos, inner = wall_cos_map(approved, U, V)
    L.memory("wall normals")

    print("=== coverage at the ORIGINAL load-transfer zones ===")
    print("%-6s %10s %10s %10s %10s %10s %10s"
          % ("zone", "cells", "C01 area", "C01 t p50", "C01 gap p50", "BP area", "BP gap p50"))
    rows = {}
    for name, z in ZONES.items():
        m = ((U[:, None] >= z["u"][0]) & (U[:, None] <= z["u"][1]) &
             (V[None, :] >= z["v"][0]) & (V[None, :] <= z["v"][1]))
        cm = m & (tc > 1e-6)
        bm = m & (tb > 1e-6)
        gcm = m & np.isfinite(gc)
        gbm = m & np.isfinite(gb)
        rows[name] = {
            "footprintCells": int(m.sum()), "footprintAreaMm2": m.sum() * cell,
            "c01MaterialAreaMm2": cm.sum() * cell,
            "c01CoverageFraction": float(cm.sum() / max(1, m.sum())),
            "c01ThicknessP50": float(np.median(tc[cm])) if cm.any() else None,
            "c01GapP50": float(np.median(gc[gcm])) if gcm.any() else None,
            "c01GapMin": float(np.min(gc[gcm])) if gcm.any() else None,
            "backplateAreaMm2": bm.sum() * cell,
            "backplateGapP50": float(np.median(gb[gbm])) if gbm.any() else None,
            "wallCosP05": float(np.nanpercentile(cos[m], 5)) if np.isfinite(cos[m]).any() else None,
            "wallCosP50": float(np.nanmedian(cos[m])) if np.isfinite(cos[m]).any() else None,
            "targetContactMm2": z["targetMm2"],
        }
        r = rows[name]
        print("%-6s %10d %10.2f %10s %10s %10.2f %10s"
              % (name, r["footprintCells"], r["c01MaterialAreaMm2"],
                 ("%.3f" % r["c01ThicknessP50"]) if r["c01ThicknessP50"] else "-",
                 ("%+.3f" % r["c01GapP50"]) if r["c01GapP50"] else "-",
                 r["backplateAreaMm2"],
                 ("%+.3f" % r["backplateGapP50"]) if r["backplateGapP50"] else "-"))
        print("        C01 coverage %.1f %%   wall |m.n| p05/p50 = %s / %s   gap min %s"
              % (100 * r["c01CoverageFraction"],
                 ("%.3f" % r["wallCosP05"]) if r["wallCosP05"] else "-",
                 ("%.3f" % r["wallCosP50"]) if r["wallCosP50"] else "-",
                 ("%+.3f" % r["c01GapMin"]) if r["c01GapMin"] else "-"))

    # where does C01 taper, and what is |m.n| there?
    plate = tc > 1e-6
    thin = plate & (tc < 1.60)
    print("\n=== C01 taper vs wall obliquity ===")
    if thin.any():
        print("  cells below 1.60 mm : %d = %.2f mm2" % (int(thin.sum()), thin.sum() * cell))
        print("  |m.n| there  p05/p50/p95 = %.3f / %.3f / %.3f"
              % (float(np.nanpercentile(cos[thin], 5)), float(np.nanmedian(cos[thin])),
                 float(np.nanpercentile(cos[thin], 95))))
    good = plate & (tc >= 2.30)
    print("  |m.n| where the plate is full thickness p05/p50 = %.3f / %.3f"
          % (float(np.nanpercentile(cos[good], 5)), float(np.nanmedian(cos[good]))))
    print("\n  skin depth along n needed for 1.60 mm normal thickness:")
    for c in (1.00, 0.90, 0.80, 0.70, 0.60, 0.50):
        print("     |m.n| = %.2f  ->  %.2f mm" % (c, 1.60 / c))

    np.savez_compressed(OUT / "e01_maps.npz", U=U, V=V, tc=tc, gc=gc, tb=tb, gb=gb,
                        cos=cos, inner=inner)
    L.write_json(OUT / "e01_probe.json", {"zones": rows, "pitchMm": PITCH,
                                          "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
