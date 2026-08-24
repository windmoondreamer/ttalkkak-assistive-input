"""C07 - (8) docs/71 shell-sensitive rerun on three shells
         (9) existing C01 re-evaluated against the reconciled shell.

docs/71 is NOT modified.  C01 is NOT modified.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Location, Plane, import_step
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, true_axis  # noqa: E402
from c04_validate import RECON  # noqa: E402

sys.path.insert(0, str(L.ROOT))
from build123d_workbench.szh_ek056_web_reference import (  # noqa: E402
    JOY_X, JOY_Y, PIVOT_Z, build_reference,
)

OUT8 = L.LAB / "05_docs71"
OUT9 = L.LAB / "06_c01_recheck"
OUTWARD = -L.DATUM_N
C01_STEP = L.REV_A / "09_exports" / "C01_SOURCE_FAITHFUL_REBASE.step"
KEEPOUTS = L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"


class Field:
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


def szh_location():
    pivot = np.asarray((JOY_X, JOY_Y, PIVOT_Z), float)
    origin = (L.DATUM_P - L.DATUM_V * pivot[0] - L.DATUM_U * pivot[1] - OUTWARD * pivot[2])
    return Location(Plane(origin=L.xyz(origin), x_dir=L.xyz(L.DATUM_V), z_dir=L.xyz(OUTWARD)))


def main() -> int:
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    shells = {}
    shells["FINGER_V2"] = combined_shell("JAD_FINGER_V2", "JFD_FINGER_V2", box, "FINGER_V2")
    shells["FROZEN_OLD"] = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    rec = import_step(str(RECON))
    shells["RECONCILED"] = L.as_single_solid(rec, "RECONCILED")[0]
    L.memory("shells")

    # ---------------- SECTION 8 -----------------------------------------
    loc = szh_location()
    _, parts, moving_world, _ = build_reference()
    items = list(parts.items()) + [("MOVING_ENVELOPE_25deg", moving_world)]
    want = ("pcb", "shaft", "cap", "header", "MOVING_ENVELOPE_25deg")
    print("=== SECTION 8 : SZH-EK056 vs three shells  [SZH = PROVISIONAL] ===")
    print("%-24s %14s %14s %14s %14s"
          % ("SZH feature", "FINGER_V2", "FROZEN_OLD", "RECONCILED", "REC - OLD"))
    rows = {}
    for name, shape in items:
        s = shape.moved(loc)
        try:
            solid, _ = L.as_single_solid(s, name)
        except RuntimeError:
            continue
        vals = {tag: L.inter_vol(solid, sh) for tag, sh in shells.items()}
        rows[name] = vals
        mark = "  <-" if name in want else ""
        print("%-24s %14.4f %14.4f %14.4f %14.4f%s"
              % (name[:24], vals["FINGER_V2"], vals["FROZEN_OLD"], vals["RECONCILED"],
                 vals["RECONCILED"] - vals["FROZEN_OLD"], mark))
        del solid
    L.memory("szh")

    # ---------------- SECTION 9 -----------------------------------------
    c01 = import_step(str(C01_STEP))
    c01, _ = L.as_single_solid(c01, "C01")
    print("\n=== SECTION 9 : existing C01 against the reconciled shell ===")
    print("C01 (read-only from REV_A): vol=%.3f faces=%d"
          % (L.vol(c01), len(list(c01.faces()))))
    inter = {tag: L.inter_vol(c01, sh) for tag, sh in shells.items()}
    for tag in ("FROZEN_OLD", "RECONCILED"):
        print("  C01 interference with %-12s = %.6f mm3" % (tag, inter[tag]))

    fp = Field(L.local_triangles(c01, tol=0.05, ang=0.10))
    U = np.arange(-21.0, 21.0 + 1e-9, 0.25)
    V = np.arange(-50.0, 15.0 + 1e-9, 0.25)
    res = {}
    for tag in ("FROZEN_OLD", "RECONCILED"):
        fs = Field(L.local_triangles(shells[tag], tol=0.06, ang=0.12))
        gap = np.full((len(U), len(V)), np.nan)
        plate = np.zeros((len(U), len(V)), bool)
        for i, u in enumerate(U):
            for j, v in enumerate(V):
                hp = fp.hits(u, v)
                if hp.size == 0 or hp.size % 2:
                    continue
                plate[i, j] = True
                hs = fs.hits(u, v)
                if hs.size and hs.size % 2 == 0:
                    cand = [hs[k] for k in range(0, hs.size, 2) if hs[k] > hp.max() - 1e-3]
                    if cand:
                        gap[i, j] = min(cand) - hp.max()
        g = gap[np.isfinite(gap)]
        res[tag] = {"plateColumns": int(plate.sum()),
                    "columnsWithShellAbove": int(np.isfinite(gap).sum()),
                    "columnsWithNoShellAbove": int(plate.sum() - np.isfinite(gap).sum()),
                    "gapMedianMm": float(np.median(g)), "gapMinMm": float(g.min()),
                    "gapMaxMm": float(g.max()),
                    "gapBelow0p40Mm2": float((g < 0.40).sum()) * 0.0625,
                    "gapBelow0p30Fraction": float((g < 0.30).mean())}
        print("  vs %-12s columns with shell above = %6d / %6d   median gap %+.3f  min %+.3f"
              % (tag, int(np.isfinite(gap).sum()), int(plate.sum()),
                 float(np.median(g)), float(g.min())))
        np.savez_compressed(OUT9 / ("c07_gap_%s.npz" % tag), U=U, V=V, gap=gap, plate=plate)
        del fs

    exposed = res["RECONCILED"]["columnsWithNoShellAbove"] - res["FROZEN_OLD"]["columnsWithNoShellAbove"]
    print("\n  columns where the reconciled openings newly expose C01: %d (%.2f mm2)"
          % (exposed, exposed * 0.0625))

    # aperture alignment: does C01's aperture cover each reconciled opening?
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    Trec = L.triangles(shells["RECONCILED"], tol=0.05, ang=0.10)
    print("\n  aperture alignment (C01 material standing inside a reconciled opening)")
    align = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, _ = true_axis(cap)
        pts = L.surf_points(cap, 30000, tol=0.05)
        cen = pts.mean(axis=0)
        ref = L.DATUM_U if abs(float(np.dot(w, L.DATUM_U))) < 0.9 else L.DATUM_V
        ex = L.unit(ref - w * float(np.dot(w, ref)))
        ey = np.cross(w, ex)
        blocked = 0
        total = 0
        for a in np.linspace(-4.0, 4.0, 17):
            for b in np.linspace(-4.0, 4.0, 17):
                o = cen + ex * a + ey * b
                total += 1
                Tc = L.triangles(c01, tol=0.05, ang=0.10) if False else None
                hp = None
                # ray through C01 along the control axis
                from b03_axis_authority import ray_intervals
                iv = ray_intervals(L.triangles(cap, tol=0.5, ang=0.5), o, w) if False else None
                blocked += 0
        align[short] = {"note": "measured below"}
        del cap
    # simpler and exact: volume of C01 inside each control's aperture prism
    from c03_reconcile import prism, offset_convex, hull_2d, user_face_outline, circle_poly
    import json as _json
    cutters = _json.loads((L.LAB / "03_reconciled" / "c03_reconcile.json")
                          .read_text(encoding="utf-8"))["cutters"]
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, _ = true_axis(cap)
        pts = L.surf_points(cap, 30000, tol=0.05)
        cen = pts.mean(axis=0)
        ref = L.DATUM_U if abs(float(np.dot(w, L.DATUM_U))) < 0.9 else L.DATUM_V
        ex = L.unit(ref - w * float(np.dot(w, ref)))
        ey = np.cross(w, ex)
        poly = np.asarray(cutters[short]["polygonVertices"], float)
        t0, t1 = cutters[short]["sweepAlongAxisMm"]
        tool = prism(poly, cen, ex, ey, w, t0, t1, "AP_" + short)
        v = L.inter_vol(c01, tool)
        align[short] = {"c01MaterialInsideOpeningPrismMm3": v}
        print("     %-5s C01 material inside the opening prism = %8.4f mm3" % (short, v))
        del cap, tool

    L.write_json(OUT8 / "c07_docs71_three_shells.json",
                 {"note": "docs/71 not modified; SZH remains PROVISIONAL / MEASURE ON ARRIVAL",
                  "szhVsShells": rows})
    L.write_json(OUT9 / "c07_c01_recheck.json",
                 {"c01VolumeMm3": L.vol(c01), "interference": inter,
                  "gap": res, "newlyExposedColumns": exposed,
                  "apertureAlignment": align, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
