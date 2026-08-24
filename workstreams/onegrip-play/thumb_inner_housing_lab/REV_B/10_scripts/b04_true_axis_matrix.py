"""B04 - the full TRUE-axis classification matrix.

Fixes two things in b03's TEST 1:
  * all three shells are cropped with the SAME world box.  b03 cropped CLEAN
    with a box shifted by THUMB_DELTA, which made CLEAN and FINGER_V2 disagree
    in the Thumb region even though they are the same shell there.  The
    difference was the crop, not the geometry.
  * each shell is probed on BOTH the LOWERED control axes and the ORIGINAL
    control axes, so "which openings does this shell contain" is answered
    directly rather than inferred.

Classification along the exact axis, outboard of the cap's user-facing face:
    A  continuous shell wall   material interval >= 2.00 mm
    B  partial / not through   0.05 .. 2.00 mm
    C  full through-opening    no material outboard
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts, combined_shell  # noqa: E402
from b03_axis_authority import (  # noqa: E402
    CROP_LO, CROP_HI, classify, ray_intervals, true_axis,
)

OUT = L.LAB / "01_axis_authority"
OUTWARD = -L.DATUM_N


def control_frames(cart_key: str):
    root, cart = leaf_parts(cart_key)
    ax, cen, top, foot, meta = {}, {}, {}, {}, {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        a, area, tilt = true_axis(cap)
        pts = L.surf_points(cap, 40000, tol=0.05)
        c = pts.mean(axis=0)
        proj = (pts - c) @ a
        ax[short], cen[short], top[short] = a, c, float(proj.max())
        foot[short] = pts[proj > proj.max() - 0.30]
        meta[short] = {"axisWorld": a.tolist(), "capCentroidWorld": c.tolist(),
                       "capTopAlongAxisMm": float(proj.max()),
                       "userFaceAreaMm2": area, "tiltFromJoystickAxisDeg": tilt,
                       "capCentroidLocal": L.to_local(c)[0].tolist()}
        del cap
    del root, cart
    return ax, cen, top, foot, meta


def probe(T, AX, CEN, TOP, FOOT):
    rows = {}
    for short in ORDER:
        a, c, t0 = AX[short], CEN[short], TOP[short]
        iv = ray_intervals(T, c, a)
        cls, slab, th = classify(iv, t0)
        fp = FOOT[short]
        idx = np.linspace(0, len(fp) - 1, min(49, len(fp))).astype(int)
        n_open = 0
        for p in fp[idx]:
            iv2 = ray_intervals(T, p, a)
            c2, _, _ = classify(iv2, 0.0)
            if c2 == "C_THROUGH_OPENING":
                n_open += 1
        rows[short] = {"class": cls,
                       "materialIntervalMm": list(slab) if slab else None,
                       "wallThicknessMm": th,
                       "allIntervalsMm": [list(x) for x in iv] if iv else None,
                       "footprintOpenFraction": n_open / max(1, len(idx)),
                       "footprintSamples": int(len(idx))}
    return rows


def show(tag, title, rows):
    print("\n=== %s | %s ===" % (tag, title))
    print("%-5s %-24s %-26s %9s %10s" % ("ctrl", "class", "material interval (mm)",
                                         "thickness", "footprint"))
    for short in ORDER:
        r = rows[short]
        print("%-5s %-24s %-26s %9.3f %9.0f%%"
              % (short, r["class"],
                 ("[%.3f, %.3f]" % tuple(r["materialIntervalMm"]))
                 if r["materialIntervalMm"] else "-",
                 r["wallThicknessMm"], 100 * r["footprintOpenFraction"]))


def main() -> int:
    axL, cenL, topL, footL, metaL = control_frames("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    axO, cenO, topO, footO, metaO = control_frames("ORIGINAL_THUMB_CARTRIDGE")
    L.memory("control frames")

    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    shells = [("CLEAN", "JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER"),
              ("FINGER_V2", "JAD_FINGER_V2", "JFD_FINGER_V2"),
              ("FROZEN", "JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB")]

    out = {}
    for tag, ka, kb in shells:
        shell = combined_shell(ka, kb, box, tag)
        T = L.triangles(shell, tol=0.06, ang=0.12)
        rl = probe(T, axL, cenL, topL, footL)
        ro = probe(T, axO, cenO, topO, footO)
        out[tag] = {"loweredControlAxes": rl, "originalControlAxes": ro}
        show(tag, "rays on the LOWERED control axes", rl)
        show(tag, "rays on the ORIGINAL control axes", ro)
        del shell, T
        L.memory("probed " + tag)

    print("\n\n=== SUMMARY : which openings does each shell contain? ===")
    print("%-11s | %-34s | %-34s" % ("shell", "on LOWERED axes", "on ORIGINAL axes"))
    print("%-11s | %-10s %-10s %-10s | %-10s %-10s %-10s"
          % ("", "A wall", "B partial", "C through", "A wall", "B partial", "C through"))
    summary = {}
    for tag, _, _ in shells:
        cnt = {}
        for which in ("loweredControlAxes", "originalControlAxes"):
            r = out[tag][which]
            cnt[which] = {
                "A": sum(1 for s in ORDER if r[s]["class"] == "A_CONTINUOUS_WALL"),
                "B": sum(1 for s in ORDER if r[s]["class"] == "B_PARTIAL_NOT_THROUGH"),
                "C": sum(1 for s in ORDER if r[s]["class"] == "C_THROUGH_OPENING"),
                "meanFootprintOpen": float(np.mean([r[s]["footprintOpenFraction"]
                                                    for s in ORDER])),
            }
        summary[tag] = cnt
        a, b = cnt["loweredControlAxes"], cnt["originalControlAxes"]
        print("%-11s | %-10d %-10d %-10d | %-10d %-10d %-10d"
              % (tag, a["A"], a["B"], a["C"], b["A"], b["B"], b["C"]))
    print("\nmean footprint open fraction:")
    for tag, _, _ in shells:
        print("  %-11s LOWERED axes %5.1f %%   ORIGINAL axes %5.1f %%"
              % (tag, 100 * summary[tag]["loweredControlAxes"]["meanFootprintOpen"],
                 100 * summary[tag]["originalControlAxes"]["meanFootprintOpen"]))

    L.write_json(OUT / "b04_true_axis_matrix.json",
                 {"loweredControlFrames": metaL, "originalControlFrames": metaO,
                  "matrix": out, "summary": summary,
                  "classThresholds": {"fullWallMm": 2.0, "openEpsMm": 0.05},
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
