"""A10 - exact inner-surface patch of the FROZEN Thumb shell + cap recess depth.

(1) Cap recess: along each control's own press axis, how far is the cap's outer
    face below the shell's OUTER surface, and below the shell's INNER surface.

(2) Exact inner-surface patch: BRep faces (not mesh) of the local frozen crop
    whose area lies in the Thumb window and whose outward normal points into the
    cavity.  Exported as a face compound for use as the conformal authority.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Compound, export_step, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from a07_conformity_map import combined_shell  # noqa: E402
from a09_cap_axis_exposure import NAME_MAP, leaf_parts, press_axis  # noqa: E402

OUT = L.LAB / "05_sections"
REFS = L.LAB / "02_reference_copies"

CROP_LO = (-32.0, -54.0, -60.0)
CROP_HI = (32.0, 24.0, 60.0)
# Thumb-facing window used to select inner faces
WIN_U = (-28.0, 28.0)
WIN_V = (-50.0, 16.0)
WIN_N = (-2.0, 30.0)


def axis_hits(T, origin, axis, tmin=-60.0, tmax=60.0):
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
    return h


def main() -> int:
    box = L.local_box(CROP_LO, CROP_HI, "CUR")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    export_step(frozen, str(REFS / "FROZEN_THUMB_LOCAL_CROP_SOLID.step"))
    T = L.triangles(frozen, tol=0.08, ang=0.15)
    L.memory("frozen crop tris %d" % len(T))

    # ---------------- (1) cap recess -------------------------------------
    root, parts = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    recess = {}
    print("\n=== cap recess along each control's own press axis ===")
    print("%-14s %10s %10s %10s %10s" % ("control", "capTop->", "wallInner", "wallOuter", "state"))
    for label, short in NAME_MAP.items():
        cap, _ = L.as_single_solid(parts[label], short)
        axis, cen, _, _ = press_axis(cap)
        pts = L.surf_points(cap, 40000, tol=0.06)
        proj = (pts - cen) @ axis
        top_pt = pts[np.argmax(proj)]
        h = axis_hits(T, top_pt, axis, tmin=-40.0, tmax=40.0)
        fwd = h[h > 0.02]
        row = {"axisWorld": axis.tolist(), "capTopWorld": top_pt.tolist(),
               "forwardShellCrossingsMm": [float(x) for x in fwd[:6]]}
        if fwd.size >= 2:
            row["wallInnerDistanceMm"] = float(fwd[0])
            row["wallOuterDistanceMm"] = float(fwd[1])
            row["wallThicknessMm"] = float(fwd[1] - fwd[0])
            state = "SEALED"
        elif fwd.size == 1:
            row["wallInnerDistanceMm"] = float(fwd[0])
            state = "PARTIAL/EDGE"
        else:
            state = "OPEN"
        row["state"] = state
        recess[short] = row
        print("%-14s %10s %10s %10s %10s"
              % (short,
                 "-",
                 ("%.3f" % row["wallInnerDistanceMm"]) if "wallInnerDistanceMm" in row else "-",
                 ("%.3f" % row["wallOuterDistanceMm"]) if "wallOuterDistanceMm" in row else "-",
                 state))
        del cap
    del root, parts
    L.memory("recess done")

    # ---------------- (2) exact inner-surface patch ----------------------
    faces = list(frozen.faces())
    picked, stats = [], []
    for idx, f in enumerate(faces):
        try:
            pts = L.surf_points(f, 400, tol=0.10)
        except Exception:
            continue
        loc = L.to_local(pts)
        inside = ((loc[:, 0] > WIN_U[0]) & (loc[:, 0] < WIN_U[1]) &
                  (loc[:, 1] > WIN_V[0]) & (loc[:, 1] < WIN_V[1]) &
                  (loc[:, 2] > WIN_N[0]) & (loc[:, 2] < WIN_N[1]))
        frac = float(inside.mean())
        if frac < 0.60:
            continue
        # face outward normal at its centre, via triangle normals (area weighted)
        Tf = L.triangles(f, tol=0.08, ang=0.15)
        n = np.cross(Tf[:, 1] - Tf[:, 0], Tf[:, 2] - Tf[:, 0])
        area = 0.5 * np.linalg.norm(n, axis=1)
        keep = area > 1e-9
        nrm = (n[keep] / (2 * area[keep])[:, None] * area[keep][:, None]).sum(axis=0)
        nrm = L.unit(nrm)
        dot_out = float(np.dot(nrm, -L.DATUM_N))
        row = {"faceIndex": idx, "areaMm2": float(f.area), "windowFraction": frac,
               "normalDotOutward": dot_out,
               "localBboxN": [float(loc[:, 2].min()), float(loc[:, 2].max())]}
        stats.append(row)
        # inner surface of the Thumb wall faces INTO the cavity -> dot < 0
        if dot_out < -0.20:
            picked.append(f)
            row["selected"] = True
    print("\ninner-surface face selection: %d candidate faces in window, %d selected"
          % (len(stats), len(picked)))
    for r in sorted(stats, key=lambda x: -x["areaMm2"])[:16]:
        print("  face %-4d area=%9.2f  win=%4.2f  n.out=%+6.3f  n=[%7.2f,%7.2f] %s"
              % (r["faceIndex"], r["areaMm2"], r["windowFraction"], r["normalDotOutward"],
                 r["localBboxN"][0], r["localBboxN"][1],
                 "SELECTED" if r.get("selected") else ""))
    if picked:
        patch = Compound(children=picked, label="FROZEN_THUMB_INNER_SURFACE_PATCH")
        export_step(patch, str(REFS / "FROZEN_THUMB_INNER_SURFACE_PATCH.step"))
        print("  patch total area = %.3f mm2" % sum(float(f.area) for f in picked))

    L.write_json(OUT / "a10_inner_surface_patch.json",
                 {"window": {"u": list(WIN_U), "v": list(WIN_V), "n": list(WIN_N)},
                  "capRecess": recess, "faceStats": stats,
                  "selectedFaceCount": len(picked), "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
