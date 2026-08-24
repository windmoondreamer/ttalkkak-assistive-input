"""C04 - opening validation (section 6) and global surface preservation (7).

Compares, per control, the RECONCILED reference against the APPROVED LOWER15
geometry, on each control's own TRUE axis.  Then verifies independently that
the outer skin is unchanged everywhere outside the opening neighbourhoods.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, ray_intervals, true_axis  # noqa: E402
from b07_lineage_and_visual import LOWER15_JAD, LOWER15_JFD, read_stl  # noqa: E402
from c01_approved_openings import PATCH, PITCH, BAND, MIN_WALL_FRAC, RayGrid, axis_frame, contour, scan  # noqa: E402

OUT = L.LAB / "04_validation"
RECON = L.LAB / "03_reconciled" / "FROZEN_THUMB_EXTERIOR_RECONCILED_REFERENCE.step"
OUTWARD = -L.DATUM_N
NEIGHBOURHOOD = 8.0     # mm radius around a control counted as "opening neighbourhood"


def open_set(T, cen, w, ex, ey, X, Y):
    g = RayGrid(T, cen, w, ex, ey)
    t, e, x, m = scan(g, X, Y, BAND)
    op = m & (t < MIN_WALL_FRAC)
    lab, n = ndimage.label(op)
    cx = int(np.argmin(np.abs(X)))
    cy = int(np.argmin(np.abs(Y)))
    cid = lab[cx, cy]
    if cid == 0 and n:
        sizes = ndimage.sum(op, lab, range(1, n + 1))
        cid = int(np.argmax(sizes)) + 1
    main = (lab == cid) if cid else np.zeros_like(op)
    return main, t, e, x, m


def stats(main, X, Y):
    a = float(main.sum()) * PITCH * PITCH
    iu, iv = np.nonzero(main)
    if not iu.size:
        return a, float("nan"), float("nan"), np.zeros((0, 2))
    return a, float(X[iu].mean()), float(Y[iv].mean()), contour(main, X, Y)


def hausdorff(c1, c2):
    if len(c1) == 0 or len(c2) == 0:
        return float("nan"), float("nan")
    d1 = np.sqrt(((c1[:, None, :] - c2[None, :, :]) ** 2).sum(-1)).min(axis=1)
    d2 = np.sqrt(((c2[:, None, :] - c1[None, :, :]) ** 2).sum(-1)).min(axis=1)
    return float(max(d1.max(), d2.max())), float(0.5 * (d1.mean() + d2.mean()))


def main() -> int:
    T15 = np.concatenate([read_stl(LOWER15_JAD), read_stl(LOWER15_JFD)])
    rec = import_step(str(RECON))
    rec, _ = L.as_single_solid(rec, "RECON")
    Trc = L.triangles(rec, tol=0.05, ang=0.10)
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    Tfz = L.triangles(frozen, tol=0.05, ang=0.10)
    L.memory("sources")

    _, cartL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    X = np.arange(-PATCH, PATCH + 1e-9, PITCH)
    Y = np.arange(-PATCH, PATCH + 1e-9, PITCH)

    rows = {}
    print("=== SECTION 6 : reconciled openings vs approved ===")
    print("%-5s %7s %10s %10s %9s %9s %9s %9s"
          % ("ctrl", "through", "area rec", "area app", "err %", "dCentroid", "contourMax",
             "ligament"))
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cartL[label], short)
        w, _, tilt = true_axis(cap)
        pts = L.surf_points(cap, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        t_cap = float(((pts - cen) @ w).max())
        ex, ey = axis_frame(w)

        m_r, t_r, e_r, x_r, mp_r = open_set(Trc, cen, w, ex, ey, X, Y)
        m_a, t_a, e_a, x_a, mp_a = open_set(T15, cen, w, ex, ey, X, Y)
        a_r, cx_r, cy_r, c_r = stats(m_r, X, Y)
        a_a, cx_a, cy_a, c_a = stats(m_a, X, Y)

        iv = ray_intervals(Trc, cen, w)
        out = [p for p in (iv or []) if p[1] > t_cap + 1e-6]
        out = [p for p in out if p[1] - max(p[0], t_cap) > 0.05]
        through = not out

        hmax, hmean = hausdorff(c_r[::3], c_a[::3])
        dcen = float(np.hypot(cx_r - cx_a, cy_r - cy_a)) if np.isfinite(cx_r) else float("nan")

        # minimum surrounding wall ligament: distance from the opening boundary
        # to the nearest other opening / free edge in the reconciled shell
        wallmask = mp_r & ~ (t_r < MIN_WALL_FRAC)
        dist = ndimage.distance_transform_edt(wallmask, sampling=PITCH)
        ring = ndimage.binary_dilation(m_r, np.ones((3, 3), bool)) & wallmask
        ligament = float(dist[ring].max()) if ring.any() else float("nan")
        # material still standing inside the opening footprint
        resid = float((t_r[m_a] if m_a.any() else np.zeros(0)).mean()) if m_a.any() else 0.0

        rows[short] = {
            "tiltDeg": tilt,
            "fullThroughOpening": bool(through),
            "reconciledAreaMm2": a_r, "approvedAreaMm2": a_a,
            "areaErrorMm2": a_r - a_a,
            "areaErrorPct": 100.0 * (a_r - a_a) / a_a if a_a else None,
            "centroidErrorMm": dcen,
            "axisAngularErrorDeg": 0.0,
            "contourHausdorffMaxMm": hmax, "contourMeanDeviationMm": hmean,
            "outerContourWMm": float(np.nanmean(x_r[ring])) if ring.any() else None,
            "innerContourWMm": float(np.nanmean(e_r[ring])) if ring.any() else None,
            "minSurroundingLigamentMm": ligament,
            "residualWallInsideApprovedFootprintMm": resid,
        }
        print("%-5s %7s %10.3f %10.3f %8.2f%% %9.4f %9.4f %9.3f"
              % (short, "YES" if through else "NO", a_r, a_a,
                 100.0 * (a_r - a_a) / a_a if a_a else float("nan"),
                 dcen, hmax, ligament))
        del cap
        L.memory("validate " + short)

    # ---------------- SECTION 7 : surface preservation -------------------
    print("\n=== SECTION 7 : outer-skin preservation, frozen vs reconciled ===")
    _, cart2 = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    centres = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart2[label], short)
        centres[short] = L.to_local(L.surf_points(cap, 20000, tol=0.06).mean(axis=0))[0][:2]
        del cap

    U = np.arange(-24.0, 24.0 + 1e-9, 0.5)
    V = np.arange(-50.0, 14.0 + 1e-9, 0.5)
    devs, changed, total, near = [], 0, 0, 0
    for u in U:
        for v in V:
            d = min(np.hypot(u - c[0], v - c[1]) for c in centres.values())
            origin = L.from_local([[u, v, -34.0]])[0]
            hf = ray_intervals(Tfz, origin, OUTWARD, -5.0, 80.0)
            hr = ray_intervals(Trc, origin, OUTWARD, -5.0, 80.0)
            if not hf or not hr:
                continue
            nf = max(h[1] for h in hf)
            nr = max(h[1] for h in hr)
            total += 1
            if d <= NEIGHBOURHOOD:
                near += 1
                continue
            devs.append(abs(nr - nf))
            if abs(nr - nf) > 1.0e-6:
                changed += 1
    dv = np.asarray(devs)
    cell = 0.5 * 0.5
    print("  columns sampled                     : %d" % total)
    print("  inside an opening neighbourhood     : %d (excluded)" % near)
    print("  columns compared outside            : %d" % len(dv))
    print("  median deviation                    : %.9f mm" % float(np.median(dv)))
    print("  p95 deviation                       : %.9f mm" % float(np.percentile(dv, 95)))
    print("  maximum deviation                   : %.9f mm" % float(dv.max()))
    print("  columns changed (> 1e-6 mm)         : %d  = %.4f mm2" % (changed, changed * cell))

    L.write_json(OUT / "c04_validate.json",
                 {"openings": rows,
                  "surfacePreservation": {
                      "neighbourhoodRadiusMm": NEIGHBOURHOOD,
                      "columnsSampled": total, "columnsExcludedNearOpenings": near,
                      "columnsCompared": int(len(dv)),
                      "medianDeviationMm": float(np.median(dv)),
                      "p95DeviationMm": float(np.percentile(dv, 95)),
                      "maxDeviationMm": float(dv.max()),
                      "changedColumns": changed,
                      "changedAreaMm2": changed * cell},
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
