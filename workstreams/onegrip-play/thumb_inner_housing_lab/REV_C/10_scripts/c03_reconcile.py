"""C03 - build FROZEN_THUMB_EXTERIOR_RECONCILED_REFERENCE (REV_C section 5).

LAB ONLY.  Not production.

Construction
    start from the exact frozen STEP pair -- its outer skin is already the
    approved surface (REV_B: median deviation 0.019 mm vs LOWER15) -- and remove
    ONLY the material that the approved openings require.  Cutting can never
    change the surface outside the cut, so requirement 5A is satisfied by
    construction and then verified independently in C04.

Cutter, per control, derived analytically from EXACT inputs:
    cross-section = convex hull of the frozen CAP projected on its own axis
                    plane, parallel-offset by the original OneGrip button
                    tolerance
    direction     = the frozen TRUE press axis
    depth         = from just inboard of the cap face to beyond the outer skin
The LOWER15 mesh is used only to CHECK the resulting opening area, never as
geometry.

No control transform is touched.  No material is added anywhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Align, Location, Plane, Polyline, Vector, export_step, extrude, make_face
from scipy.spatial import ConvexHull

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, ray_intervals, true_axis  # noqa: E402
from c01_approved_openings import axis_frame  # noqa: E402

OUT = L.LAB / "03_reconciled"
BUTTON_TOLERANCE = 0.20        # original OneGrip #button_tolerance, per side
DEPTH_BELOW = 0.50             # start the sweep this far inboard of the cap face
DEPTH_ABOVE = 14.0             # and this far outboard of it


def hull_2d(points_xy):
    h = ConvexHull(points_xy)
    v = points_xy[h.vertices]
    # ensure counter-clockwise
    a = 0.5 * float(np.sum(v[:, 0] * np.roll(v[:, 1], -1) - np.roll(v[:, 0], -1) * v[:, 1]))
    if a < 0:
        v = v[::-1]
        a = -a
    return v, a


def offset_convex(poly, delta):
    """True parallel offset of a convex CCW polygon: intersect the offset
    half-planes.  A Minkowski square would overshoot on oblique edges and a
    Minkowski disc would round the corners the original openings have sharp."""
    n = len(poly)
    lines = []
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        e = q - p
        nrm = np.asarray([e[1], -e[0]], float)      # outward for CCW
        nrm /= np.linalg.norm(nrm)
        lines.append((nrm, float(nrm @ p) + delta))
    out = []
    for i in range(n):
        n0, d0 = lines[(i - 1) % n]
        n1, d1 = lines[i]
        A = np.stack([n0, n1])
        if abs(float(np.linalg.det(A))) < 1e-12:
            continue
        out.append(np.linalg.solve(A, np.asarray([d0, d1], float)))
    return np.asarray(out, float)


def poly_area(p):
    return 0.5 * abs(float(np.sum(p[:, 0] * np.roll(p[:, 1], -1)
                                  - np.roll(p[:, 0], -1) * p[:, 1])))


def user_face_outline(cap, w, cen, ex, ey):
    """Outline of the cap's USER-FACING face, projected on the axis plane.

    Hulling the whole cap silhouette (the first pass did) is wrong for wedged or
    tapered caps: the projection of the entire solid is larger than the face the
    opening has to surround, which inflated T1/T3 by 16 % and T4/T6/T7/T8 by
    7-9 %.  The opening is built around the top FACE.
    """
    best, best_a = None, -1.0
    for f in cap.faces():
        try:
            T = L.triangles(f, tol=0.03, ang=0.08)
        except Exception:
            continue
        nn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        a = 0.5 * np.linalg.norm(nn, axis=1)
        keep = a > 1e-10
        if not keep.any():
            continue
        nrm = L.unit((nn[keep] / (2 * a[keep])[:, None] * a[keep][:, None]).sum(axis=0))
        area = float(a[keep].sum())
        if float(np.dot(nrm, w)) > np.cos(np.radians(6.0)) and area > best_a:
            best, best_a = T, area
    if best is None:
        return None, None
    d = best.reshape(-1, 3) - cen
    return np.stack([d @ ex, d @ ey], axis=1), best_a


def solve_offset(hull, target_area, lo=0.0, hi=1.2):
    """Offset that reproduces the approved opening area."""
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if poly_area(offset_convex(hull, mid)) < target_area:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def circle_poly(radius, n=48):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([radius * np.cos(a), radius * np.sin(a)], axis=1)


def prism(poly_xy, origin, ex, ey, w, t0, t1, label):
    pl = Plane(origin=L.xyz(origin + w * t0), x_dir=L.xyz(ex), z_dir=L.xyz(w))
    pts = [(float(p[0]), float(p[1])) for p in poly_xy]
    face = make_face(Polyline(*pts, close=True))
    solid = extrude(pl * face, amount=float(t1 - t0))
    solid.label = label
    return solid


def main() -> int:
    approved = json.loads((L.LAB / "01_approved_openings" / "c01_approved_openings.json")
                          .read_text(encoding="utf-8"))["controls"]

    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    jad = L.load("JAD_LOWERED_THUMB")
    jad_c, _ = L.as_single_solid((jad & box).clean(), "JAD")
    del jad
    jfd = L.load("JFD_LOWERED_THUMB")
    jfd_c, _ = L.as_single_solid((jfd & box).clean(), "JFD")
    del jfd
    L.memory("shell crops")
    both = L.as_single_solid((jad_c + jfd_c).clean(), "FROZEN")[0]
    Tfz = L.triangles(both, tol=0.05, ang=0.10)

    _, cartL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")

    print("%-5s %10s %10s %10s %10s %10s %9s %s"
          % ("ctrl", "userFace", "cut area", "approved", "err mm2", "err %",
             "solved d", "sweep t"))
    cutters, rows = {}, {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cartL[label], short)
        w, _, tilt = true_axis(cap)
        pts = L.surf_points(cap, 60000, tol=0.04)
        cen = pts.mean(axis=0)
        ex, ey = axis_frame(w)
        d = pts - cen
        app_a = approved[short]["approvedOpeningAreaMm2"]
        if short == "JOY":
            # the knob is a cone + sphere; it has no planar user face, so the
            # joystick opening is taken as a circle of the APPROVED area.
            # SOURCE: LOWER15 mesh measurement -- marked NON-EXACT-DERIVED.
            r = float(np.sqrt(app_a / np.pi))
            hull, hull_a = circle_poly(r), app_a
            off = hull
            solved = float("nan")
            derivation = "circle fitted to the approved area [NON-EXACT-DERIVED from LOWER15 mesh]"
        else:
            face_xy, face_a = user_face_outline(cap, w, cen, ex, ey)
            hull, hull_a = hull_2d(face_xy)
            solved = solve_offset(hull, app_a)
            off = offset_convex(hull, BUTTON_TOLERANCE)
            derivation = "cap user-face hull + #button_tolerance [EXACT B-rep inputs]"
        cut_a = poly_area(off)
        t_cap = float((d @ w).max())
        t0, t1 = t_cap - DEPTH_BELOW, t_cap + DEPTH_ABOVE
        tool = prism(off, cen, ex, ey, w, t0, t1, "RECON_CUT_" + short)
        cutters[short] = tool
        rows[short] = {"tiltDeg": tilt, "capUserFaceAreaMm2": hull_a,
                       "derivation": derivation,
                       "offsetThatMatchesApprovedMm": solved,
                       "cutterCrossSectionAreaMm2": cut_a,
                       "approvedOpeningAreaMm2": app_a,
                       "areaErrorMm2": cut_a - app_a,
                       "areaErrorPct": 100.0 * (cut_a - app_a) / app_a if app_a else None,
                       "sweepAlongAxisMm": [t0, t1],
                       "buttonToleranceMm": BUTTON_TOLERANCE,
                       "cutterVolumeMm3": float(tool.volume),
                       "polygonVertices": off.tolist()}
        print("%-5s %10.3f %10.3f %10.3f %10.3f %9.2f%% %9s %s"
              % (short, hull_a, cut_a, app_a, cut_a - app_a,
                 100.0 * (cut_a - app_a) / app_a if app_a else float("nan"),
                 ("%.4f" % solved) if np.isfinite(solved) else "n/a",
                 "[%.2f, %.2f]" % (t0, t1)))
        del cap
    L.memory("cutters")

    # ---- apply, per half, so the split shells stay separate --------------
    print("\napplying reconciled cutters")
    res = {}
    for tag, shell in (("JAD", jad_c), ("JFD", jfd_c)):
        cur = shell
        v0 = L.vol(cur)
        per = {}
        for short in ORDER:
            iv = L.inter_vol(cur, cutters[short])
            if iv > 1.0e-9:
                cur = (cur - cutters[short]).clean()
                solids = list(cur.solids())
                if len(solids) != 1:
                    raise RuntimeError("%s: cutting %s fragmented the shell into %d solids"
                                       % (tag, short, len(solids)))
                cur, _ = L.as_single_solid(cur, tag)
            per[short] = iv
            print("   %s %-5s removed %9.4f mm3" % (tag, short, iv))
        res[tag] = {"volumeBeforeMm3": v0, "volumeAfterMm3": L.vol(cur),
                    "removedTotalMm3": v0 - L.vol(cur), "removedPerControlMm3": per,
                    "solids": len(list(cur.solids())), "faces": len(list(cur.faces()))}
        export_step(cur, str(OUT / ("%s_THUMB_EXTERIOR_RECONCILED_REFERENCE.step" % tag)))
        print("   %s: %.4f -> %.4f mm3  (removed %.4f)  solids=%d faces=%d"
              % (tag, v0, L.vol(cur), v0 - L.vol(cur), len(list(cur.solids())),
                 len(list(cur.faces()))))
        if tag == "JAD":
            jad_r = cur
        else:
            jfd_r = cur
        L.memory("cut " + tag)

    comb = L.as_single_solid((jad_r + jfd_r).clean(), "RECONCILED")[0]
    export_step(comb, str(OUT / "FROZEN_THUMB_EXTERIOR_RECONCILED_REFERENCE.step"))
    print("\ncombined reconciled reference: vol=%.4f faces=%d"
          % (L.vol(comb), len(list(comb.faces()))))

    L.write_json(OUT / "c03_reconcile.json",
                 {"note": "LAB ONLY - not production geometry",
                  "buttonToleranceMm": BUTTON_TOLERANCE,
                  "cutters": rows, "shells": res,
                  "combinedVolumeMm3": L.vol(comb),
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
