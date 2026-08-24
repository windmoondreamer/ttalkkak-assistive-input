"""B08 - is the SURFACE the same and only the OPENINGS different?

B07 found that THUMB_LOWER15_HOUSING (the Onshape model whose Thumb patch was
grafted into the exterior the user reviewed) has full openings at all nine
LOWERED control positions, while the exact STEP pair does not.

This script separates two questions:
  Q1  do the two agree on the OUTER SKIN position?  (is the visible surface the
      same shape, i.e. is the approved silhouette actually preserved?)
  Q2  where do the frozen caps sit relative to the LOWER15 skins, on the TRUE
      axis?  If they sit correctly there, the caps are not misplaced and only
      the exact STEP's cuts are defective.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, ray_intervals, true_axis  # noqa: E402
from b07_lineage_and_visual import LOWER15_JAD, LOWER15_JFD, read_stl  # noqa: E402

OUT = L.LAB / "03_lineage"
OUT4 = L.LAB / "04_cap_position_audit"
OUTWARD = -L.DATUM_N


def main() -> int:
    T15 = np.concatenate([read_stl(LOWER15_JAD), read_stl(LOWER15_JFD)])
    print("LOWER15 housing STL: %d triangles" % len(T15))

    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    Tex = L.triangles(frozen, tol=0.06, ang=0.12)
    clean = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER", box, "CLEAN")
    Tcl = L.triangles(clean, tol=0.06, ang=0.12)
    del frozen, clean
    L.memory("shells")

    # ---- Q1 : outer skin agreement on a fan of columns ------------------
    print("\n=== Q1 : outer skin position, exact STEP vs LOWER15 housing ===")
    print("%9s %9s | %10s %10s %10s" % ("u", "v", "exact n", "lower15 n", "delta"))
    deltas = []
    rows_q1 = []
    for u in (-18.0, -12.0, -6.0, 0.0, 6.0, 12.0, 18.0):
        for v in (8.0, 0.0, -10.0, -20.0, -26.0, -36.0, -46.0):
            origin = L.from_local([[u, v, -30.0]])[0]
            hits_e = ray_intervals(Tex, origin, OUTWARD, -5.0, 80.0)
            hits_l = ray_intervals(T15, origin, OUTWARD, -5.0, 80.0)
            if not hits_e or not hits_l:
                continue
            ne = max(h[1] for h in hits_e) - 30.0
            nl = max(h[1] for h in hits_l) - 30.0
            deltas.append(nl - ne)
            rows_q1.append({"u": u, "v": v, "exactOuterN": ne, "lower15OuterN": nl,
                            "deltaMm": nl - ne})
            print("%9.1f %9.1f | %10.4f %10.4f %10.4f" % (u, v, ne, nl, nl - ne))
    d = np.asarray(deltas)
    print("\nouter-skin delta over %d columns: mean %+.4f  median %+.4f  "
          "max|d| %.4f  p95|d| %.4f mm"
          % (len(d), d.mean(), np.median(d), np.abs(d).max(), np.percentile(np.abs(d), 95)))

    # ---- Q2 : caps against the LOWER15 skins ---------------------------
    _, cartL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    _, cartO = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    print("\n=== Q2 : frozen cap vs LOWER15 housing skins, on the TRUE axis ===")
    print("%-5s | %-34s | %-34s" % ("ctrl", "vs LOWER15 (the approved surface)",
                                    "vs exact STEP"))
    print("%-5s | %-11s %-11s %-10s | %-11s %-11s %-10s"
          % ("", "wall t", "capTop->in", "capTop->out", "wall t", "capTop->in", "capTop->out"))
    rows = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cartL[label], short)
        ax, _, tilt = true_axis(cap)
        pts = L.surf_points(cap, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        top_t = float(((pts - cen) @ ax).max())
        row = {"tiltDeg": tilt, "capTopAlongAxisMm": top_t}
        cells = []
        for tag, T in (("LOWER15", T15), ("EXACT", Tex)):
            iv = ray_intervals(T, cen, ax)
            if iv:
                out = [p for p in iv if p[1] > top_t]
                if out:
                    w = max(out, key=lambda p: p[1] - p[0])
                    row[tag] = {"wallThicknessMm": w[1] - w[0],
                                "capTopToInnerSkinMm": w[0] - top_t,
                                "capTopToOuterSkinMm": w[1] - top_t}
                    cells.append("%-11.3f %-11.3f %-10.3f"
                                 % (w[1] - w[0], w[0] - top_t, w[1] - top_t))
                    continue
            row[tag] = {"wallThicknessMm": 0.0, "note": "no material outboard of the cap"}
            cells.append("%-34s" % "no material outboard (open)")
        rows[short] = row
        print("%-5s | %s | %s" % (short, cells[0], cells[1]))
        del cap

    # original cap vs CLEAN, as the design-intent reference
    print("\n=== reference : ORIGINAL cap vs CLEAN shell, on the TRUE axis ===")
    ref = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cartO[label], short)
        ax, _, _ = true_axis(cap)
        pts = L.surf_points(cap, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        top_t = float(((pts - cen) @ ax).max())
        iv = ray_intervals(Tcl, cen, ax)
        out = [p for p in iv if p[1] > top_t] if iv else []
        if out:
            w = max(out, key=lambda p: p[1] - p[0])
            ref[short] = {"wallThicknessMm": w[1] - w[0], "capTopToInnerSkinMm": w[0] - top_t,
                          "capTopToOuterSkinMm": w[1] - top_t}
            print("  %-5s wall %6.3f  capTop->inner %+7.3f  capTop->outer %+7.3f"
                  % (short, w[1] - w[0], w[0] - top_t, w[1] - top_t))
        else:
            ref[short] = {"note": "no material outboard of the cap (open, as designed)"}
            print("  %-5s no material outboard of the cap -- open, as designed" % short)
        del cap

    L.write_json(OUT / "b08_lower15_vs_exact.json",
                 {"outerSkinColumns": rows_q1,
                  "outerSkinDeltaStatsMm": {"mean": float(d.mean()),
                                            "median": float(np.median(d)),
                                            "maxAbs": float(np.abs(d).max()),
                                            "p95Abs": float(np.percentile(np.abs(d), 95))},
                  "capVsSkins": rows, "originalCapVsCleanReference": ref,
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
