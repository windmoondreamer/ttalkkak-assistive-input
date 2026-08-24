"""C05 - corrected validation.

Three defects in C04 are fixed here.

1. LIGAMENT was degenerate (0.141 mm for every control = the grid pitch).  It
   took the distance transform on a 3x3 ring, which measures the pitch, not a
   ligament.  Replaced with a global wall map of the reconciled shell: find the
   holes, then measure the true material gap between neighbouring holes.

2. SURFACE PRESERVATION was measured by comparing two independent
   tessellations, so its 0.183 mm maximum is chord error, not geometry change.
   Replaced with an exact containment proof: cutting can only remove material,
   so RECONCILED must be a subset of FROZEN, i.e.
       vol(RECONCILED & FROZEN) == vol(RECONCILED)
   Any added material anywhere would break that equality.

3. AREA ERROR alone is misleading where the frozen STEP had already made a
   mis-shaped partial cut (T1/T3/JOY).  Reported as EXCESS (open in reconciled,
   solid in approved) and DEFICIT (open in approved, solid in reconciled).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, WALL_BAND, clusters, true_axis, wall_map  # noqa: E402
from b07_lineage_and_visual import LOWER15_JAD, LOWER15_JFD, read_stl  # noqa: E402
from c01_approved_openings import PATCH, PITCH, BAND, MIN_WALL_FRAC, RayGrid, axis_frame, scan  # noqa: E402
from c04_validate import RECON, open_set  # noqa: E402

OUT = L.LAB / "04_validation"
OUTWARD = -L.DATUM_N
GPITCH = 0.20


def main() -> int:
    T15 = np.concatenate([read_stl(LOWER15_JAD), read_stl(LOWER15_JFD)])
    rec = import_step(str(RECON))
    rec, _ = L.as_single_solid(rec, "RECON")
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    L.memory("sources")

    # ---- 1. exact containment proof -------------------------------------
    v_rec = L.vol(rec)
    v_fz = L.vol(frozen)
    v_common = L.inter_vol(rec, frozen)
    print("=== exact containment proof (no material added anywhere) ===")
    print("  vol(FROZEN)              = %14.6f mm3" % v_fz)
    print("  vol(RECONCILED)          = %14.6f mm3" % v_rec)
    print("  vol(RECONCILED & FROZEN) = %14.6f mm3" % v_common)
    print("  vol(REC) - vol(REC & FZ) = %14.9f mm3   <- material added outside FROZEN"
          % (v_rec - v_common))
    print("  vol(FZ)  - vol(REC & FZ) = %14.6f mm3   <- material removed" % (v_fz - v_common))
    added = v_rec - v_common
    contained = abs(added) < 1.0e-4
    print("  RECONCILED is a subset of FROZEN : %s" % contained)

    Trc = L.triangles(rec, tol=0.05, ang=0.10)
    L.memory("recon tris")

    # ---- 2. global wall map -> real ligaments ---------------------------
    U = np.arange(-26.0, 26.0 + 1e-9, GPITCH)
    V = np.arange(-52.0, 16.0 + 1e-9, GPITCH)
    thick, mat = wall_map(L.local_triangles(rec, tol=0.06, ang=0.12), U, V, WALL_BAND)
    holes = mat & (thick < 0.05)
    lab, nlab = ndimage.label(holes)
    wall = mat & ~holes
    print("\n=== reconciled Thumb wall: %d hole clusters ===" % nlab)

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    ctr = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        ctr[short] = L.to_local(L.surf_points(cap, 20000, tol=0.06).mean(axis=0))[0][:2]
        del cap

    assign, sizes = {}, {}
    for r in range(1, nlab + 1):
        m = lab == r
        a = float(m.sum()) * GPITCH * GPITCH
        if a < 4.0:
            continue
        iu, iv = np.nonzero(m)
        cu, cv = float(U[iu].mean()), float(V[iv].mean())
        best = min(ORDER, key=lambda s: np.hypot(cu - ctr[s][0], cv - ctr[s][1]))
        d = float(np.hypot(cu - ctr[best][0], cv - ctr[best][1]))
        if d < 6.0:
            assign[best] = r
            sizes[best] = a
        print("   cluster %-3d area=%8.2f mm2  centroid (%7.2f,%7.2f)  -> %-4s d=%5.2f"
              % (r, a, cu, cv, best, d))

    ligament = {}
    for s, r in assign.items():
        others = holes & (lab != r) & (lab > 0)
        if not others.any():
            ligament[s] = None
            continue
        d_other = ndimage.distance_transform_edt(~others, sampling=GPITCH)
        edge = (lab == r) & ~ndimage.binary_erosion(lab == r, np.ones((3, 3), bool))
        ligament[s] = float(d_other[edge].min())

    # ---- 3. excess / deficit per opening --------------------------------
    X = np.arange(-PATCH, PATCH + 1e-9, PITCH)
    Y = np.arange(-PATCH, PATCH + 1e-9, PITCH)
    cellA = PITCH * PITCH
    rows = {}
    print("\n=== opening agreement with the approved geometry ===")
    print("%-5s %8s %10s %10s %10s %10s %10s %10s"
          % ("ctrl", "through", "recArea", "appArea", "EXCESS", "DEFICIT", "overlap%", "ligament"))
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, tilt = true_axis(cap)
        pts = L.surf_points(cap, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        ex, ey = axis_frame(w)
        m_r, t_r, _, _, _ = open_set(Trc, cen, w, ex, ey, X, Y)
        m_a, t_a, _, _, _ = open_set(T15, cen, w, ex, ey, X, Y)
        a_r = float(m_r.sum()) * cellA
        a_a = float(m_a.sum()) * cellA
        exc = float((m_r & ~m_a).sum()) * cellA
        dfc = float((m_a & ~m_r).sum()) * cellA
        ovl = 100.0 * float((m_r & m_a).sum()) / max(1, m_a.sum())
        lig = ligament.get(short)
        rows[short] = {"tiltDeg": tilt, "fullThroughOpening": bool(a_r > 0),
                       "reconciledAreaMm2": a_r, "approvedAreaMm2": a_a,
                       "excessMm2": exc, "deficitMm2": dfc,
                       "approvedCoveragePct": ovl,
                       "minSurroundingLigamentMm": lig,
                       "wallMapClusterAreaMm2": sizes.get(short)}
        print("%-5s %8s %10.3f %10.3f %10.3f %10.3f %9.1f%% %10s"
              % (short, "YES" if a_r > 0 else "NO", a_r, a_a, exc, dfc, ovl,
                 ("%.3f" % lig) if lig else "n/a"))
        del cap
        L.memory("agree " + short)

    tot_exc = sum(r["excessMm2"] for r in rows.values())
    tot_dfc = sum(r["deficitMm2"] for r in rows.values())
    print("\n  total EXCESS  (open here, solid in approved) = %8.3f mm2" % tot_exc)
    print("  total DEFICIT (open in approved, solid here) = %8.3f mm2" % tot_dfc)
    print("  minimum ligament over all controls           = %8.3f mm"
          % min(v for v in ligament.values() if v))

    L.write_json(OUT / "c05_validate2.json",
                 {"containment": {"frozenVolumeMm3": v_fz, "reconciledVolumeMm3": v_rec,
                                  "commonVolumeMm3": v_common,
                                  "materialAddedMm3": added,
                                  "materialRemovedMm3": v_fz - v_common,
                                  "reconciledIsSubsetOfFrozen": bool(contained)},
                  "openings": rows,
                  "totalExcessMm2": tot_exc, "totalDeficitMm2": tot_dfc,
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
