"""D02 - ORIGINAL Backplate and C01 measured against the EXACT APPROVED shell.

REV_D sections 6, 7, 9.

Everything is re-measured; no REV_A/B/C number is assumed to carry over.

Three comparisons on one grid, in the lowered Thumb local frame:
  ORIGINAL   original Backplate  vs  original CLEAN shell   (design law reference)
  LOWERED    lowered  Backplate  vs  EXACT APPROVED shell   (does conformity hold?)
  C01        C01                 vs  EXACT APPROVED shell
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, true_axis  # noqa: E402


class Field:
    """Column ray-crossing accelerator.  Defined locally rather than imported
    from REV_C so that REV_D has no dependency on the reconciled-shell work."""

    def __init__(self, T):
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        self.a, self.e1, self.e2 = a, b - a, c - a
        self.tu0, self.tu1 = T[:, :, 0].min(axis=1), T[:, :, 0].max(axis=1)
        self.tv0, self.tv1 = T[:, :, 1].min(axis=1), T[:, :, 1].max(axis=1)
        self.det = self.e1[:, 0] * self.e2[:, 1] - self.e1[:, 1] * self.e2[:, 0]
        self.ok = np.abs(self.det) > 1.0e-14
        self.order = np.argsort(self.tu0)
        self.tu0s = self.tu0[self.order]

    def hits(self, u, v):
        cand = self.order[:np.searchsorted(self.tu0s, u, side="right")]
        cand = cand[self.tu1[cand] >= u]
        if cand.size == 0:
            return np.zeros(0)
        sel = cand[(self.tv0[cand] <= v) & (self.tv1[cand] >= v)]
        if sel.size == 0:
            return np.zeros(0)
        A, E1, E2 = self.a[sel], self.e1[sel], self.e2[sel]
        d, o = self.det[sel], self.ok[sel]
        du, dv = u - A[:, 0], v - A[:, 1]
        s = np.where(o, (du * E2[:, 1] - dv * E2[:, 0]) / np.where(o, d, 1.0), -1.0)
        t = np.where(o, (E1[:, 0] * dv - E1[:, 1] * du) / np.where(o, d, 1.0), -1.0)
        g = o & (s >= 0) & (t >= 0) & (s + t <= 1)
        if not g.any():
            return np.zeros(0)
        h = np.sort(A[g, 2] + s[g] * E1[g, 2] + t[g] * E2[g, 2])
        keep = np.ones(h.size, bool)
        keep[1:] = np.diff(h) > 1.0e-7
        return h[keep]


OUT2 = L.LAB / "02_original_housing"
OUT3 = L.LAB / "03_c01_recheck"
OUT4 = L.LAB / "04_loadpath"
OUTWARD = -L.DATUM_N
ORIG_P = L.DATUM_P - L.THUMB_DELTA
PITCH = 0.25
CONTACT = 0.30
C01_STEP = L.REV_A / "09_exports" / "C01_SOURCE_FAITHFUL_REBASE.step"
BP_STEP = L.REV_A / "02_reference_copies" / "ORIGINAL_THUMB_BACKPLATE.step"
BP_LOW_STEP = L.REV_A / "02_reference_copies" / "LOWERED_ORIGINAL_THUMB_BACKPLATE.step"


def approved_shell():
    a = import_step(L.SRC["JAD_APPROVED"])
    sa, _ = L.as_single_solid(a, "JAD")
    del a
    b = import_step(L.SRC["JFD_APPROVED"])
    sb, _ = L.as_single_solid(b, "JFD")
    del b
    out, _ = L.as_single_solid((sa + sb).clean(), "APPROVED")
    L.memory("approved shell")
    return out


def gap_map(part, shell, origin, U, V):
    """Thickness of the part and the gap to the first shell material outboard."""
    def loc_tris(s):
        T = L.triangles(s, tol=0.05, ang=0.10)
        d = T.reshape(-1, 3) - origin
        return np.stack([d @ L.DATUM_U, d @ L.DATUM_V, d @ OUTWARD], axis=1).reshape(-1, 3, 3)
    fp, fs = Field(loc_tris(part)), Field(loc_tris(shell))
    t = np.zeros((len(U), len(V)))
    g = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            hp = fp.hits(u, v)
            if hp.size == 0 or hp.size % 2:
                continue
            t[i, j] = float(sum(hp[k + 1] - hp[k] for k in range(0, hp.size, 2)))
            hs = fs.hits(u, v)
            if hs.size and hs.size % 2 == 0:
                cand = [hs[k] for k in range(0, hs.size, 2) if hs[k] > hp.max() - 1e-3]
                if cand:
                    g[i, j] = min(cand) - hp.max()
    return t, g


def summarise(tag, t, g, cell):
    plate = t > 1e-6
    valid = np.isfinite(g)
    gg = g[valid]
    row = {"plateColumns": int(plate.sum()), "planAreaMm2": plate.sum() * cell,
           "overlapColumns": int(valid.sum()),
           "gapPercentilesMm": {str(q): float(np.percentile(gg, q))
                                for q in (1, 5, 10, 25, 50, 75, 90, 99)},
           "gapMinMm": float(gg.min()), "gapMaxMm": float(gg.max()),
           "contactColumns": int((gg <= CONTACT).sum()),
           "contactAreaMm2": float((gg <= CONTACT).sum()) * cell,
           "contactFraction": float((gg <= CONTACT).mean()),
           "interferingColumns": int((gg < 0).sum()),
           "columnsBeyond3mm": int((gg > 3.0).sum()),
           "columnsBeyond6mm": int((gg > 6.0).sum()),
           "thicknessPercentilesMm": {str(q): float(np.percentile(t[plate], q))
                                      for q in (5, 25, 50, 75, 95)},
           "noShellAboveColumns": int(plate.sum() - valid.sum())}
    print("\n=== %s ===" % tag)
    print("  plan area %.2f mm2   overlap columns %d   no shell above %d"
          % (row["planAreaMm2"], row["overlapColumns"], row["noShellAboveColumns"]))
    print("  gap p10/p25/p50/p75/p90 = %+.3f / %+.3f / %+.3f / %+.3f / %+.3f mm"
          % tuple(row["gapPercentilesMm"][k] for k in ("10", "25", "50", "75", "90")))
    print("  gap min/max = %+.3f / %+.3f mm" % (row["gapMinMm"], row["gapMaxMm"]))
    print("  contact band (<= %.2f mm) = %d columns = %.2f mm2 = %.2f %% of overlap"
          % (CONTACT, row["contactColumns"], row["contactAreaMm2"],
             100 * row["contactFraction"]))
    print("  interfering %d   beyond 3 mm %d   beyond 6 mm %d"
          % (row["interferingColumns"], row["columnsBeyond3mm"], row["columnsBeyond6mm"]))
    print("  thickness p25/p50/p75 = %.3f / %.3f / %.3f mm"
          % tuple(row["thicknessPercentilesMm"][k] for k in ("25", "50", "75")))
    return row


def zones(tag, t, g, U, V, cell, ctr):
    plate = t > 1e-6
    band = np.isfinite(g) & (g <= CONTACT)
    lab, n = ndimage.label(band)
    out = []
    print("  contact zones:")
    for r in range(1, n + 1):
        m = lab == r
        a = float(m.sum()) * cell
        if a < 1.0:
            continue
        iu, iv = np.nonzero(m)
        cu, cv = float(U[iu].mean()), float(V[iv].mean())
        best = min(ctr, key=lambda s: np.hypot(cu - ctr[s][0], cv - ctr[s][1]))
        d = float(np.hypot(cu - ctr[best][0], cv - ctr[best][1]))
        # edge proximity: is the zone at the plate boundary or in the field?
        _pp = np.pad(plate, 1, mode="constant", constant_values=False)
        ed = ndimage.distance_transform_edt(_pp, sampling=PITCH)[1:-1, 1:-1]
        onedge = float((ed[m] <= 1.5).mean())
        out.append({"areaMm2": a, "centroidUV": [cu, cv],
                    "uRange": [float(U[iu.min()]), float(U[iu.max()])],
                    "vRange": [float(V[iv.min()]), float(V[iv.max()])],
                    "minGapMm": float(g[m].min()), "meanGapMm": float(g[m].mean()),
                    "nearestControl": best, "distanceToControlMm": d,
                    "fractionAtPlateEdge": onedge})
    out.sort(key=lambda r: -r["areaMm2"])
    for z in out[:10]:
        print("     %8.2f mm2  u[%7.2f,%7.2f] v[%7.2f,%7.2f]  min %6.3f  "
              "nearest %-4s d=%5.2f  atEdge %4.2f"
              % (z["areaMm2"], z["uRange"][0], z["uRange"][1], z["vRange"][0],
                 z["vRange"][1], z["minGapMm"], z["nearestControl"],
                 z["distanceToControlMm"], z["fractionAtPlateEdge"]))
    return out


def main() -> int:
    cell = PITCH * PITCH
    U = np.arange(-22.0, 22.0 + 1e-9, PITCH)
    V = np.arange(-52.0, 16.0 + 1e-9, PITCH)

    approved = approved_shell()
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    clean = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER", box, "CLEAN")

    bp = import_step(str(BP_STEP))
    bp, _ = L.as_single_solid(bp, "BACKPLATE")
    bpl = import_step(str(BP_LOW_STEP))
    bpl, _ = L.as_single_solid(bpl, "BACKPLATE_LOWERED")
    c01 = import_step(str(C01_STEP))
    c01, _ = L.as_single_solid(c01, "C01")
    print("Backplate %.4f mm3 | C01 %.4f mm3 | approved shell %.4f mm3"
          % (L.vol(bp), L.vol(c01), L.vol(approved)))
    L.memory("loaded")

    _, cartO = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    _, cartL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    ctrO, ctrL = {}, {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        c, _ = L.as_single_solid(cartO[label], short)
        p = L.surf_points(c, 20000, tol=0.06).mean(axis=0) - ORIG_P
        ctrO[short] = [float(p @ L.DATUM_U), float(p @ L.DATUM_V)]
        del c
        c, _ = L.as_single_solid(cartL[label], short)
        p = L.surf_points(c, 20000, tol=0.06).mean(axis=0) - L.DATUM_P
        ctrL[short] = [float(p @ L.DATUM_U), float(p @ L.DATUM_V)]
        del c

    res = {}
    t1, g1 = gap_map(bp, clean, ORIG_P, U, V)
    res["ORIGINAL_vs_CLEAN"] = summarise(
        "ORIGINAL Backplate  vs  ORIGINAL CLEAN shell   (design law reference)",
        t1, g1, cell)
    res["ORIGINAL_vs_CLEAN"]["contactZones"] = zones("orig", t1, g1, U, V, cell, ctrO)
    del clean
    L.memory("original pair")

    t2, g2 = gap_map(bpl, approved, L.DATUM_P, U, V)
    res["LOWERED_vs_APPROVED"] = summarise(
        "LOWERED Backplate  vs  EXACT APPROVED shell   (does conformity hold?)",
        t2, g2, cell)
    res["LOWERED_vs_APPROVED"]["contactZones"] = zones("low", t2, g2, U, V, cell, ctrL)
    L.memory("lowered pair")

    t3, g3 = gap_map(c01, approved, L.DATUM_P, U, V)
    res["C01_vs_APPROVED"] = summarise(
        "C01  vs  EXACT APPROVED shell", t3, g3, cell)
    res["C01_vs_APPROVED"]["contactZones"] = zones("c01", t3, g3, U, V, cell, ctrL)
    res["C01_vs_APPROVED"]["interferenceMm3"] = L.inter_vol(c01, approved)
    print("  C01 interference with the EXACT APPROVED shell = %.6f mm3"
          % res["C01_vs_APPROVED"]["interferenceMm3"])
    L.memory("c01 pair")

    np.savez_compressed(OUT2 / "d02_maps.npz", U=U, V=V,
                        t_orig=t1, g_orig=g1, t_low=t2, g_low=g2, t_c01=t3, g_c01=g3)
    L.write_json(OUT2 / "d02_housing_vs_exact.json",
                 {"authority": "exact Onshape THUMB_LOWER15_HOUSING_V1 export",
                  "gridPitchMm": PITCH, "contactThresholdMm": CONTACT,
                  "results": res, "controlCentresOriginalUV": ctrO,
                  "controlCentresLoweredUV": ctrL, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
