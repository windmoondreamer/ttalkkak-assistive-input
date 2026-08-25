"""H01 - dissect the ORIGINAL OneGrip Thumb button seat from exact B-rep.

REV_H section 4.  Nothing is generated; this is measurement only.

Per original button (measured on that button's own TRUE press axis):
  * plate material intervals along the axis  -> seat plane, local thickness,
    any recess / boss / shoulder
  * holes in the plate near the button       -> terminal escape slots, pitch,
    width, length, web between them
  * PushBtn body and actuator                -> stack heights
  * cap underside                            -> actuator-to-cap relationship
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from d02_housing_vs_exact import BP_STEP, Field  # noqa: E402

OUT = L.LAB / "01_seat_audit"
OUTWARD = -L.DATUM_N
ORIG_P = L.DATUM_P - L.THUMB_DELTA
PITCH = 0.10
PATCH = 9.0


def axis_frame(w):
    ref = L.DATUM_U if abs(float(np.dot(w, L.DATUM_U))) < 0.9 else L.DATUM_V
    ex = L.unit(ref - w * float(np.dot(w, ref)))
    return ex, np.cross(w, ex)


def local_tris(shape, origin, ex, ey, w, tol=0.04):
    T = L.triangles(shape, tol=tol, ang=0.09)
    d = T.reshape(-1, 3) - origin
    return np.stack([d @ ex, d @ ey, d @ w], axis=1).reshape(-1, 3, 3)


def main() -> int:
    bp = import_step(str(BP_STEP))
    bp, _ = L.as_single_solid(bp, "BACKPLATE")
    print("ORIGINAL Backplate: vol=%.4f mm3  faces=%d  shells=%d"
          % (L.vol(bp), len(list(bp.faces())), len(list(bp.shells()))))

    root, cart = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    push = [v for k, v in cart.items() if "PUSHBTN" in k.upper()]
    print("PushBtn solids present in the exact cartridge STEP: %d" % len(push))
    pb = None
    if push:
        pb, _ = L.as_single_solid(push[0], "PUSHBTN")
        print("  PushBtn vol=%.4f mm3  faces=%d" % (L.vol(pb), len(list(pb.faces()))))

    X = np.arange(-PATCH, PATCH + 1e-9, PITCH)
    Y = np.arange(-PATCH, PATCH + 1e-9, PITCH)
    cell = PITCH * PITCH
    rows = {}

    print("\n=== per-button seat dissection (original frame, own press axis) ===")
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, tilt = true_axis(cap)
        cpts = L.surf_points(cap, 40000, tol=0.04)
        cen = cpts.mean(axis=0)
        ex, ey = axis_frame(w)
        proj = (cpts - cen) @ w
        cap_top = float(proj.max())
        cap_bot = float(proj.min())

        Tb = local_tris(bp, cen, ex, ey, w)
        f = Field(Tb)

        # material along the exact button axis
        h = f.hits(0.0, 0.0)
        iv = [(float(h[k]), float(h[k + 1])) for k in range(0, h.size, 2)] if h.size % 2 == 0 else None

        # plate map over the patch: thickness and hole detection
        t = np.zeros((len(X), len(Y)))
        top = np.full((len(X), len(Y)), np.nan)
        bot = np.full((len(X), len(Y)), np.nan)
        for i, x in enumerate(X):
            for j, y in enumerate(Y):
                hh = f.hits(x, y)
                if hh.size and hh.size % 2 == 0:
                    t[i, j] = float(sum(hh[k + 1] - hh[k] for k in range(0, hh.size, 2)))
                    top[i, j] = float(hh.max())
                    bot[i, j] = float(hh.min())
        mat = t > 1e-6
        # a hole is a no-material island surrounded by plate
        holes = (~mat) & ndimage.binary_dilation(mat, np.ones((11, 11), bool))
        holes = holes & ndimage.binary_fill_holes(mat)
        lab, n = ndimage.label(holes)
        hl = []
        for r in range(1, n + 1):
            m = lab == r
            a = float(m.sum()) * cell
            if a < 0.20:
                continue
            ix, iy = np.nonzero(m)
            hl.append({"areaMm2": a,
                       "centreXY": [float(X[ix].mean()), float(Y[iy].mean())],
                       "sizeXMm": float(X[ix].max() - X[ix].min() + PITCH),
                       "sizeYMm": float(Y[iy].max() - Y[iy].min() + PITCH),
                       "distanceFromAxisMm": float(np.hypot(X[ix].mean(), Y[iy].mean()))})
        hl.sort(key=lambda r: r["distanceFromAxisMm"])

        seat = None
        if iv:
            # the seat = the outermost plate slab the actuator would sit on
            seat = max(iv, key=lambda p: p[1])
        rows[short] = {
            "tiltFromJoystickAxisDeg": tilt,
            "capTopAlongAxisMm": cap_top, "capBottomAlongAxisMm": cap_bot,
            "capThicknessMm": cap_top - cap_bot,
            "plateIntervalsOnAxisMm": iv,
            "seatSlabMm": list(seat) if seat else None,
            "plateThicknessOnAxisMm": (seat[1] - seat[0]) if seat else None,
            "capBottomToPlateTopMm": (cap_bot - seat[1]) if seat else None,
            "plateThicknessP50Mm": float(np.median(t[mat])) if mat.any() else None,
            "plateAreaInPatchMm2": float(mat.sum()) * cell,
            "holeCount": len(hl), "holes": hl,
        }
        r = rows[short]
        print("\n  %-4s tilt %.3f deg   cap thickness %.3f   plate on axis %s"
              % (short, tilt, r["capThicknessMm"],
                 ("[%.3f, %.3f] t=%.3f" % (seat[0], seat[1], seat[1] - seat[0]))
                 if seat else "NO PLATE ON AXIS"))
        if seat:
            print("       cap underside is %+.3f mm from the plate top face"
                  % r["capBottomToPlateTopMm"])
        print("       plate thickness p50 in patch = %s   holes found = %d"
              % (("%.3f" % r["plateThicknessP50Mm"]) if r["plateThicknessP50Mm"] else "-",
                 len(hl)))
        for k, hh in enumerate(hl[:6]):
            print("         hole %d  %6.2f mm2  %5.2f x %5.2f mm  at (%+6.2f,%+6.2f)  d=%5.2f"
                  % (k, hh["areaMm2"], hh["sizeXMm"], hh["sizeYMm"],
                     hh["centreXY"][0], hh["centreXY"][1], hh["distanceFromAxisMm"]))
        del cap
        L.memory("seat " + short)

    # ---- the PushBtn itself ----------------------------------------------
    pbrow = None
    if pb is not None:
        # align to its own dominant axis
        Tp = L.triangles(pb, tol=0.03, ang=0.08)
        nrm = np.cross(Tp[:, 1] - Tp[:, 0], Tp[:, 2] - Tp[:, 0])
        ln = np.linalg.norm(nrm, axis=1)
        okn = ln > 1e-12
        nrm[okn] /= ln[okn][:, None]
        ar = 0.5 * ln
        # the PushBtn travels with the cartridge, so use T8's axis (its own button)
        lab8 = next(k for k, v in NAME_MAP.items() if v == "T8")
        cap8, _ = L.as_single_solid(cart[lab8], "T8")
        w8, _, _ = true_axis(cap8)
        ex, ey = axis_frame(w8)
        p = L.surf_points(pb, 60000, tol=0.03)
        c = p.mean(axis=0)
        d = p - c
        a_, b_, n_ = d @ ex, d @ ey, d @ w8
        print("\n=== ORIGINAL PushBtn (single exact solid in the cartridge STEP) ===")
        print("  extent along its button axis : %.3f mm  [%.3f, %.3f]"
              % (n_.max() - n_.min(), n_.min(), n_.max()))
        print("  lateral extent               : %.3f x %.3f mm"
              % (a_.max() - a_.min(), b_.max() - b_.min()))
        # actuator = the narrow part near the outward end
        bins = np.linspace(n_.min(), n_.max(), 25)
        print("  cross-section along the axis (outward is +):")
        prof = []
        for k in range(len(bins) - 1):
            m = (n_ >= bins[k]) & (n_ < bins[k + 1])
            if m.sum() < 20:
                continue
            sx = float(a_[m].max() - a_[m].min())
            sy = float(b_[m].max() - b_[m].min())
            prof.append({"nMid": float(0.5 * (bins[k] + bins[k + 1])), "sizeX": sx, "sizeY": sy})
            print("     n=%+7.3f   %6.3f x %6.3f mm" % (0.5 * (bins[k] + bins[k + 1]), sx, sy))
        pbrow = {"volumeMm3": L.vol(pb), "axisExtentMm": [float(n_.min()), float(n_.max())],
                 "lateralMm": [float(a_.max() - a_.min()), float(b_.max() - b_.min())],
                 "profile": prof}
        del cap8

    L.write_json(OUT / "h01_seat_audit.json",
                 {"backplate": {"volumeMm3": L.vol(bp), "faces": len(list(bp.faces()))},
                  "pushBtnSolidsInStep": len(push), "pushBtn": pbrow,
                  "buttons": rows, "patchHalfWidthMm": PATCH, "pitchMm": PITCH,
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
