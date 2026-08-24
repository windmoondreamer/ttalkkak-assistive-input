"""B03 - frozen-exterior authority, re-decided WITHOUT cap/shell intersection.

Two independent tests, neither of which infers an opening from cap collision.

TEST 1  TRUE-AXIS RAY CLASSIFICATION
    For every shell and every control, cast a ray along that control's TRUE
    press axis and classify the material intervals outboard of the cap:
        A  continuous shell wall   (an interval >= 2.0 mm)
        B  partial / not-through   (0.05 .. 2.0 mm)
        C  full through-opening    (no material outboard)
    Also a 5x5 bundle over the cap footprint, for an area fraction.

TEST 2  DIRECT OPENING LOCALISATION  (the decisive one)
    Find the holes in the Thumb wall of each shell WITHOUT using any cap, in a
    single common frame, cluster them, and compare each cluster centroid
    against the ORIGINAL and the LOWERED control positions.

TRUE AXIS = outward normal of the cap's user-facing face, i.e. the largest face
whose normal is within 45 deg of outward (B02).  REV_A used the largest face
overall, which is the cap's SEATING face for T1/T3/JOY and yields 4.00 deg for
every button; see b03 report.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, face_normals, leaf_parts, combined_shell  # noqa: E402

OUT = L.LAB / "01_axis_authority"
OUTWARD = -L.DATUM_N
ORIG_P = L.DATUM_P - L.THUMB_DELTA
DELTA_LOCAL = np.asarray([float(L.THUMB_DELTA @ L.DATUM_U),
                          float(L.THUMB_DELTA @ L.DATUM_V),
                          float(L.THUMB_DELTA @ OUTWARD)])

CROP_LO = (-32.0, -54.0, -60.0)
CROP_HI = (32.0, 24.0, 60.0)
WALL_BAND = (-2.0, 26.0)      # generous: covers CLEAN (n 5.7..12.7) and FROZEN (11..16)
PITCH = 0.30
FULL_WALL_MM = 2.00
OPEN_EPS_MM = 0.05


def true_axis(cap):
    """Outward normal of the cap's user-facing face."""
    cand = []
    for n, a in face_normals(cap):
        ang = float(np.degrees(np.arccos(np.clip(float(np.dot(n, OUTWARD)), -1, 1))))
        if ang < 45.0:
            cand.append((a, n, ang))
    if not cand:
        raise RuntimeError("no outward-facing face on cap")
    cand.sort(key=lambda r: -r[0])
    return L.unit(cand[0][1]), float(cand[0][0]), cand[0][2]


def ray_intervals(T, origin, axis, tmin=-45.0, tmax=45.0):
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    e1, e2 = b - a, c - a
    pv = np.cross(axis, e2)
    det = np.einsum("ij,ij->i", e1, pv)
    ok = np.abs(det) > 1.0e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    tv = origin - a
    u = np.einsum("ij,ij->i", tv, pv) * inv
    qv = np.cross(tv, e1)
    v = (qv @ axis) * inv
    t = np.einsum("ij,ij->i", e2, qv) * inv
    good = ok & (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (t > tmin) & (t < tmax)
    h = np.sort(t[good])
    if h.size:
        keep = np.ones(h.size, bool)
        keep[1:] = np.diff(h) > 1.0e-7
        h = h[keep]
    if h.size % 2:
        return None
    return [(float(h[i]), float(h[i + 1])) for i in range(0, h.size, 2)]


def classify(intervals, cap_top_t):
    """Material outboard of the cap top along the ray."""
    if intervals is None:
        return "PARITY_FAIL", None, 0.0
    out = [(lo, hi) for lo, hi in intervals if hi > cap_top_t + 1.0e-6]
    out = [(max(lo, cap_top_t), hi) for lo, hi in out]
    out = [(lo, hi) for lo, hi in out if hi - lo > OPEN_EPS_MM]
    if not out:
        return "C_THROUGH_OPENING", None, 0.0
    thickest = max(out, key=lambda p: p[1] - p[0])
    t = thickest[1] - thickest[0]
    return ("A_CONTINUOUS_WALL" if t >= FULL_WALL_MM else "B_PARTIAL_NOT_THROUGH"), thickest, t


def wall_map(T, U, V, band):
    """Total material thickness inside the wall band, per (u, v) column."""
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    e1, e2 = b - a, c - a
    tu0, tu1 = T[:, :, 0].min(axis=1), T[:, :, 0].max(axis=1)
    tv0, tv1 = T[:, :, 1].min(axis=1), T[:, :, 1].max(axis=1)
    det = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
    ok = np.abs(det) > 1.0e-14
    thick = np.zeros((len(U), len(V)))
    any_mat = np.zeros((len(U), len(V)), bool)
    order = np.argsort(tu0)
    tu0s = tu0[order]
    for i, u in enumerate(U):
        cand = order[:np.searchsorted(tu0s, u, side="right")]
        cand = cand[tu1[cand] >= u]
        if cand.size == 0:
            continue
        for j, v in enumerate(V):
            sel = cand[(tv0[cand] <= v) & (tv1[cand] >= v)]
            if sel.size == 0:
                continue
            A, E1, E2 = a[sel], e1[sel], e2[sel]
            d, o = det[sel], ok[sel]
            du, dv = u - A[:, 0], v - A[:, 1]
            s = np.where(o, (du * E2[:, 1] - dv * E2[:, 0]) / np.where(o, d, 1.0), -1.0)
            t = np.where(o, (E1[:, 0] * dv - E1[:, 1] * du) / np.where(o, d, 1.0), -1.0)
            g = o & (s >= 0) & (t >= 0) & (s + t <= 1)
            if not g.any():
                continue
            h = np.sort(A[g, 2] + s[g] * E1[g, 2] + t[g] * E2[g, 2])
            keep = np.ones(h.size, bool)
            keep[1:] = np.diff(h) > 1.0e-7
            h = h[keep]
            if h.size % 2:
                continue
            any_mat[i, j] = True
            tot = 0.0
            for k in range(0, h.size, 2):
                lo, hi = max(h[k], band[0]), min(h[k + 1], band[1])
                if hi > lo:
                    tot += hi - lo
            thick[i, j] = tot
    return thick, any_mat


def clusters(mask, U, V, min_cells=40):
    lab = -np.ones(mask.shape, int)
    out = []
    for i in range(mask.shape[0]):
        for j in range(mask.shape[1]):
            if not mask[i, j] or lab[i, j] >= 0:
                continue
            cid = len(out)
            stack = [(i, j)]
            lab[i, j] = cid
            cells = []
            while stack:
                x, y = stack.pop()
                cells.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < mask.shape[0] and 0 <= ny < mask.shape[1] \
                            and mask[nx, ny] and lab[nx, ny] < 0:
                        lab[nx, ny] = cid
                        stack.append((nx, ny))
            if len(cells) < min_cells:
                continue
            arr = np.asarray(cells)
            out.append({"cells": len(cells),
                        "areaMm2": len(cells) * PITCH * PITCH,
                        "centroidUV": [float(U[arr[:, 0]].mean()), float(V[arr[:, 1]].mean())],
                        "uRange": [float(U[arr[:, 0]].min()), float(U[arr[:, 0]].max())],
                        "vRange": [float(V[arr[:, 1]].min()), float(V[arr[:, 1]].max())]})
    out.sort(key=lambda r: -r["areaMm2"])
    return out


def main() -> int:
    print("THUMB_DELTA in local (u, v, n) = %s" % np.round(DELTA_LOCAL, 4))
    root, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")

    axes, centres, tops, foot = {}, {}, {}, {}
    print("\nTRUE press axes (user-facing face) vs REV_A's axis")
    print("%-5s %-42s %9s %9s %10s" % ("ctrl", "true axis (world)", "tilt", "REV_A", "err"))
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        ax, area, tilt = true_axis(cap)
        pts = L.surf_points(cap, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        proj = (pts - cen) @ ax
        axes[short] = ax
        centres[short] = cen
        tops[short] = float(proj.max())
        # footprint sample points on the user-facing face
        face_pts = pts[proj > proj.max() - 0.30]
        foot[short] = face_pts
        axes[short + "_meta"] = {"userFaceAreaMm2": area, "tiltDeg": tilt,
                                 "capCentreWorld": cen.tolist(),
                                 "capTopAlongAxisMm": float(proj.max())}
        print("%-5s %-42s %9.4f %9.4f %10.4f"
              % (short, np.array2string(np.round(ax, 6)), tilt, 4.0 if short != "JOY" else 0.0,
                 abs(tilt - (4.0 if short != "JOY" else 0.0))))
        del cap
    L.memory("axes")

    # ---------------- TEST 1 -------------------------------------------
    box_cur = L.local_box(CROP_LO, CROP_HI, "CUR")
    lo, hi = np.asarray(CROP_LO), np.asarray(CROP_HI)
    world = np.asarray([ORIG_P + p[0] * L.DATUM_U + p[1] * L.DATUM_V + p[2] * OUTWARD
                        for p in (lo, hi)])
    box_orig = L.local_box(L.to_local(world)[0], L.to_local(world)[1], "ORIG")

    shells = {}
    shells["FROZEN"] = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box_cur, "FROZEN")
    shells["FINGER_V2"] = combined_shell("JAD_FINGER_V2", "JFD_FINGER_V2", box_cur, "FINGER_V2")
    shells["CLEAN"] = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER",
                                     box_orig, "CLEAN")

    test1 = {}
    for tag, shell in shells.items():
        T = L.triangles(shell, tol=0.06, ang=0.12)
        rows = {}
        print("\n=== TEST 1 : %s  (ray along each control's TRUE axis) ===" % tag)
        print("%-5s %-22s %-28s %8s %10s" % ("ctrl", "class", "material interval (mm)",
                                             "thick", "footprint"))
        for short in ORDER:
            ax, cen, top = axes[short], centres[short], tops[short]
            iv = ray_intervals(T, cen, ax)
            cls, slab, th = classify(iv, top)
            # 5x5 bundle over the user-facing face
            fp = foot[short]
            idx = np.linspace(0, len(fp) - 1, min(25, len(fp))).astype(int)
            n_open = 0
            for p in fp[idx]:
                iv2 = ray_intervals(T, p, ax)
                c2, _, _ = classify(iv2, 0.0)
                if c2 == "C_THROUGH_OPENING":
                    n_open += 1
            frac = n_open / max(1, len(idx))
            rows[short] = {"class": cls, "materialIntervalMm": list(slab) if slab else None,
                           "wallThicknessMm": th,
                           "allIntervalsMm": [list(x) for x in iv] if iv else None,
                           "footprintOpenFraction": frac,
                           "capTopAlongAxisMm": top}
            print("%-5s %-22s %-28s %8.3f %9.0f%%"
                  % (short, cls,
                     ("[%.3f, %.3f]" % slab) if slab else "-", th, 100 * frac))
        test1[tag] = rows
        del T
        L.memory("test1 " + tag)

    # ---------------- TEST 2 -------------------------------------------
    U = np.arange(-26.0, 26.0 + 1e-9, PITCH)
    V = np.arange(-52.0, 16.0 + 1e-9, PITCH)
    test2 = {}
    lowered_pos = {s: L.to_local(centres[s])[0][:2].tolist() for s in ORDER}
    original_pos = {s: [lowered_pos[s][0] - DELTA_LOCAL[0],
                        lowered_pos[s][1] - DELTA_LOCAL[1]] for s in ORDER}

    for tag, shell in shells.items():
        # CLEAN lives in the original frame; express it in the LOWERED frame by
        # translating the shell, not by changing the grid - a pure translation.
        s = shell
        if tag == "CLEAN":
            from build123d import Location, Vector
            s = shell.moved(Location(Vector(*[float(x) for x in L.THUMB_DELTA])))
        T = L.local_triangles(s, tol=0.06, ang=0.12)
        thick, any_mat = wall_map(T, U, V, WALL_BAND)
        holes = any_mat & (thick < OPEN_EPS_MM)
        cl = clusters(holes, U, V)
        test2[tag] = {"clusters": cl}
        print("\n=== TEST 2 : %s  -- holes in the Thumb wall, no caps used ===" % tag)
        print("   %d clusters >= 3.6 mm2" % len(cl))
        for k, cdat in enumerate(cl[:12]):
            cu, cv = cdat["centroidUV"]
            # nearest control in each hypothesis
            dl = min(((np.hypot(cu - lowered_pos[s2][0], cv - lowered_pos[s2][1]), s2)
                      for s2 in ORDER))
            do = min(((np.hypot(cu - original_pos[s2][0], cv - original_pos[s2][1]), s2)
                      for s2 in ORDER))
            cdat["nearestLowered"] = {"control": dl[1], "distanceMm": float(dl[0])}
            cdat["nearestOriginal"] = {"control": do[1], "distanceMm": float(do[0])}
            print("   #%-2d area=%7.2f mm2  centroid (u,v)=(%7.2f,%7.2f) | "
                  "LOWERED %-4s d=%6.2f | ORIGINAL %-4s d=%6.2f  -> %s"
                  % (k, cdat["areaMm2"], cu, cv, dl[1], dl[0], do[1], do[0],
                     "LOWERED" if dl[0] < do[0] else "ORIGINAL"))
        np.savez_compressed(OUT / ("b03_wallmap_%s.npz" % tag), U=U, V=V,
                            thick=thick, any_mat=any_mat, holes=holes)
        del T
        L.memory("test2 " + tag)

    # verdict from TEST 2
    verdict = {}
    for tag in shells:
        cl = test2[tag]["clusters"]
        big = [c for c in cl if c["areaMm2"] >= 8.0]
        low = sum(1 for c in big if c["nearestLowered"]["distanceMm"]
                  < c["nearestOriginal"]["distanceMm"])
        verdict[tag] = {"bigClusters": len(big), "matchingLowered": low,
                        "matchingOriginal": len(big) - low}
        print("\n%s : %d significant holes -> %d match LOWERED, %d match ORIGINAL"
              % (tag, len(big), low, len(big) - low))

    L.write_json(OUT / "b03_axis_authority.json", {
        "deltaLocal": DELTA_LOCAL.tolist(),
        "trueAxes": {k: v for k, v in axes.items() if k.endswith("_meta")},
        "loweredControlUV": lowered_pos, "originalControlUV": original_pos,
        "test1_rayAlongTrueAxis": test1, "test2_openingLocalisation": test2,
        "test2_verdict": verdict, "wallBand": list(WALL_BAND), "gridPitchMm": PITCH,
        "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
