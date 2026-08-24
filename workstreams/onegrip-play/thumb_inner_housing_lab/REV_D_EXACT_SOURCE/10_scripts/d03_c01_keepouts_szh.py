"""D03 - C01 aperture alignment, keep-outs, thin regions, and SZH vs the exact shell.

REV_D sections 7, 10, 11.  C01 is READ ONLY.  No SZH carrier is designed.
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
from b03_axis_authority import CROP_LO, CROP_HI, ray_intervals, true_axis  # noqa: E402
from d02_housing_vs_exact import C01_STEP, Field, approved_shell  # noqa: E402

sys.path.insert(0, str(L.ROOT))
from build123d_workbench.szh_ek056_web_reference import (  # noqa: E402
    JOY_X, JOY_Y, PIVOT_Z, build_reference,
)

OUT3 = L.LAB / "03_c01_recheck"
OUT5 = L.LAB / "05_szh"
OUTWARD = -L.DATUM_N
PITCH = 0.25
MIN_WALL = 1.20
KEEPOUTS = L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"


def szh_location():
    pivot = np.asarray((JOY_X, JOY_Y, PIVOT_Z), float)
    origin = (L.DATUM_P - L.DATUM_V * pivot[0] - L.DATUM_U * pivot[1] - OUTWARD * pivot[2])
    return Location(Plane(origin=L.xyz(origin), x_dir=L.xyz(L.DATUM_V), z_dir=L.xyz(OUTWARD)))


def main() -> int:
    approved = approved_shell()
    c01 = import_step(str(C01_STEP))
    c01, _ = L.as_single_solid(c01, "C01")
    Tap = L.triangles(approved, tol=0.05, ang=0.10)
    Tc = L.triangles(c01, tol=0.05, ang=0.10)
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    L.memory("loaded")

    # ---- aperture alignment against the APPROVED openings ---------------
    print("=== C01 aperture alignment vs the EXACT APPROVED openings ===")
    print("%-5s %-10s %-14s %-14s %s" % ("ctrl", "clearPath", "C01 blocks?", "minRadialClr",
                                         "note"))
    align = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, _ = true_axis(cap)
        pts = L.surf_points(cap, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        proj = (pts - cen) @ w
        face = pts[proj > proj.max() - 0.30]
        idx = np.linspace(0, len(face) - 1, min(81, len(face))).astype(int)
        blocked_shell = 0
        blocked_c01 = 0
        for p in face[idx]:
            for T, which in ((Tap, "s"), (Tc, "c")):
                iv = ray_intervals(T, p, w)
                hit = [q for q in (iv or []) if q[1] > 0.0 and q[1] - max(q[0], 0.0) > 0.05]
                if hit:
                    if which == "s":
                        blocked_shell += 1
                    else:
                        blocked_c01 += 1
        n = len(idx)
        # radial clearance from the cap edge to C01 material, in the axis plane
        ref = L.DATUM_U if abs(float(np.dot(w, L.DATUM_U))) < 0.9 else L.DATUM_V
        ex = L.unit(ref - w * float(np.dot(w, ref)))
        ey = np.cross(w, ex)
        d = face - cen
        rmax = float(np.hypot(d @ ex, d @ ey).max())
        clr = None
        for extra in np.arange(0.0, 4.01, 0.05):
            hit = False
            for a in np.linspace(0, 2 * np.pi, 24, endpoint=False):
                p = cen + ex * ((rmax + extra) * np.cos(a)) + ey * ((rmax + extra) * np.sin(a))
                iv = ray_intervals(Tc, p, w)
                if iv:
                    hit = True
                    break
            if hit:
                clr = float(extra)
                break
        align[short] = {"shellBlockedFraction": blocked_shell / n,
                        "c01BlockedFraction": blocked_c01 / n,
                        "capOuterRadiusMm": rmax,
                        "c01RadialClearanceMm": clr}
        print("%-5s %-10.0f%% %-14.0f%% %-14s %s"
              % (short, 100 * (1 - blocked_shell / n), 100 * (blocked_c01 / n),
                 ("%.2f mm" % clr) if clr is not None else "> 4 mm",
                 "C01 clear of the opening" if blocked_c01 == 0 else "C01 INTRUDES"))
        del cap
    L.memory("apertures")

    # ---- thin regions of C01 (intrinsic) --------------------------------
    U = np.arange(-21.0, 21.0 + 1e-9, PITCH)
    V = np.arange(-50.0, 15.0 + 1e-9, PITCH)
    Tloc = L.local_triangles(c01, tol=0.05, ang=0.10)
    fp = Field(Tloc)
    t = np.zeros((len(U), len(V)))
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            h = fp.hits(u, v)
            if h.size and h.size % 2 == 0:
                t[i, j] = float(sum(h[k + 1] - h[k] for k in range(0, h.size, 2)))
    plate = t > 1e-6
    cell = PITCH * PITCH
    _pd = np.pad(plate, 1, mode="constant", constant_values=False)
    edge = ndimage.distance_transform_edt(_pd, sampling=PITCH)[1:-1, 1:-1]
    thin = plate & (t < MIN_WALL)
    interior = thin & (edge > 1.0)
    print("\n=== C01 thin regions (intrinsic to C01, shell-independent) ===")
    print("  plan area                    %8.2f mm2" % (plate.sum() * cell))
    print("  area below %.2f mm            %8.2f mm2" % (MIN_WALL, thin.sum() * cell))
    print("  interior (non-edge) thin     %8.2f mm2" % (interior.sum() * cell))
    print("  minimum thickness            %8.4f mm" % float(t[plate].min()))

    # ---- keep-outs ------------------------------------------------------
    print("\n=== C01 vs keep-outs (N1/N2 harness, SZH provisional, screws) ===")
    keep = import_step(str(KEEPOUTS))
    ko = {}
    for child in list(getattr(keep, "children", []) or []):
        lab = str(child.label)
        if not child.solids() or lab.startswith("CAP_"):
            continue
        s, _ = L.as_single_solid(child, lab)
        iv = L.inter_vol(c01, s)
        ko[lab] = iv
        if iv > 1.0e-6 or "CARRIER" in lab or "SZH" in lab or "SCREW" in lab:
            print("  %-38s %12.6f mm3" % (lab[:38], iv))
        del s
    L.memory("keepouts")

    # ---- SZH vs the exact approved shell --------------------------------
    print("\n=== SZH-EK056 vs the EXACT APPROVED shell  [PROVISIONAL] ===")
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    legacy = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "LEGACY")
    loc = szh_location()
    _, parts, moving_world, _ = build_reference()
    print("%-24s %14s %14s %14s" % ("SZH feature", "legacy(defect)", "EXACT APPROVED", "delta"))
    szh = {}
    for name, shape in list(parts.items()) + [("MOVING_ENVELOPE_25deg", moving_world)]:
        try:
            solid, _ = L.as_single_solid(shape.moved(loc), name)
        except RuntimeError:
            continue
        a = L.inter_vol(solid, legacy)
        b = L.inter_vol(solid, approved)
        szh[name] = {"vsLegacyMm3": a, "vsApprovedMm3": b, "deltaMm3": b - a}
        print("%-24s %14.4f %14.4f %14.4f" % (name[:24], a, b, b - a))
        del solid

    # available depth along the joystick axis inside the approved shell
    iv = ray_intervals(Tap, L.DATUM_P, OUTWARD, -60.0, 60.0)
    print("\n  approved-shell material along the joystick axis (n from DATUM_P):")
    print("    %s" % (["[%.3f, %.3f]" % x for x in iv] if iv else "none"))
    inner = [x for x in (iv or []) if x[1] < 0]
    depth = None
    if inner:
        depth = float(max(x[1] for x in inner))
        print("    deepest cavity floor below the pivot : n = %.3f mm" % depth)

    L.write_json(OUT3 / "d03_c01_vs_exact.json",
                 {"apertureAlignment": align,
                  "thin": {"planAreaMm2": plate.sum() * cell,
                           "belowMinWallMm2": thin.sum() * cell,
                           "interiorThinMm2": interior.sum() * cell,
                           "minThicknessMm": float(t[plate].min())},
                  "keepOutInterferenceMm3": ko, "memory": L.MEMORY_LOG})
    L.write_json(OUT5 / "d03_szh_vs_exact.json",
                 {"status": "PROVISIONAL / MEASURE ON ARRIVAL - no carrier designed",
                  "szh": szh,
                  "joystickAxisMaterialIntervals": [list(x) for x in iv] if iv else None,
                  "cavityFloorBelowPivotMm": depth})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
