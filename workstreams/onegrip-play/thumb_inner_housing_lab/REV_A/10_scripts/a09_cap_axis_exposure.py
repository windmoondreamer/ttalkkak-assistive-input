"""A09 - per-control exposure measured along each control's OWN press axis.

A08 projected cap footprints along the joystick n axis.  The Thumb buttons are
tilted relative to that axis, so this repeats the test along each cap's true
axis, derived from its dominant planar face normal.

Caution recorded in docs/73: do NOT use a PCA OBB on a square plate; it snaps
to the 45 deg diagonal.  The dominant planar face normal is used instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from a07_conformity_map import combined_shell, ORIG_P  # noqa: E402

OUT = L.LAB / "05_sections"
CROP_LO = (-32.0, -54.0, -60.0)
CROP_HI = (32.0, 24.0, 60.0)

NAME_MAP = {
    "THUMB_BUTTON_1_CAP__Button_corner_1": "T1_corner_1",
    "THUMB_BUTTON_2_CAP__Button_middle_1": "T2_middle_1",
    "THUMB_BUTTON_3_CAP__Button_corner_2": "T3_corner_2",
    "THUMB_BUTTON_4_CAP__Button_side_1": "T4_side_1",
    "THUMB_BUTTON_5_CAP__Button_middle_2": "T5_middle_2",
    "THUMB_BUTTON_6_CAP__Button_side_2": "T6_side_2",
    "THUMB_BUTTON_7_CAP__Button_wide_1": "T7_wide_1",
    "THUMB_BUTTON_8_CAP__Button_wide_2": "T8_wide_2",
    "THUMB_JOYSTICK_SMALL_ATTACHMENT": "JOYSTICK",
}


def leaf_parts(key: str):
    root = import_step(L.SRC[key])
    parts = {}

    def walk(shape):
        kids = list(getattr(shape, "children", []) or [])
        if kids:
            for k in kids:
                walk(k)
            return
        if shape.solids():
            parts[str(shape.label)] = shape
    walk(root)
    return root, parts


def press_axis(cap):
    """Outward normal of the cap's dominant planar face, oriented away from
    the cap centroid.  Square plates make PCA useless (docs/73)."""
    T = L.triangles(cap, tol=0.05, ang=0.10)
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    n = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(n, axis=1)
    keep = area > 1.0e-9
    n = n[keep] / (2.0 * area[keep])[:, None]
    area = area[keep]
    # cluster normals at 1 degree
    order = np.argsort(-area)
    groups = []
    for i in order:
        for g in groups:
            if float(np.dot(n[i], g["n"])) > np.cos(np.radians(2.0)):
                g["a"] += area[i]
                break
        else:
            groups.append({"n": n[i], "a": area[i]})
    groups.sort(key=lambda g: -g["a"])
    axis = L.unit(groups[0]["n"])
    bb = cap.bounding_box()
    cen = np.asarray([(bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2,
                      (bb.min.Z + bb.max.Z) / 2], float)
    # orient outward: away from the grip interior, i.e. +(-DATUM_N) side
    if float(np.dot(axis, -L.DATUM_N)) < 0.0:
        axis = -axis
    return axis, cen, float(groups[0]["a"]), float(np.degrees(
        np.arccos(np.clip(float(np.dot(axis, -L.DATUM_N)), -1.0, 1.0))))


def exposure(cap, axis, shell_tris, samples=900, reach=25.0):
    """Fraction of the cap top face that has a clear straight path outward."""
    pts = L.surf_points(cap, 60000, tol=0.06)
    d = pts - pts.mean(axis=0)
    proj = d @ axis
    top = pts[proj > proj.max() - 0.35]
    if len(top) > samples:
        idx = np.random.default_rng(7).choice(len(top), samples, replace=False)
        top = top[idx]
    a, b, c = shell_tris[:, 0], shell_tris[:, 1], shell_tris[:, 2]
    e1, e2 = b - a, c - a
    pv = np.cross(axis, e2)
    det = np.einsum("ij,ij->i", e1, pv)
    ok = np.abs(det) > 1.0e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    blocked = 0
    for p in top:
        tv = p - a
        u = np.einsum("ij,ij->i", tv, pv) * inv
        qv = np.cross(tv, e1)
        v = (qv @ axis) * inv
        t = np.einsum("ij,ij->i", e2, qv) * inv
        hit = ok & (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (t > 0.05) & (t < reach)
        if hit.any():
            blocked += 1
    return 1.0 - blocked / max(1, len(top)), len(top)


def main() -> int:
    box_cur = L.local_box(CROP_LO, CROP_HI, "CUR")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box_cur, "FROZEN")
    Tf = L.triangles(frozen, tol=0.10, ang=0.18)
    del frozen
    L.memory("frozen tris %d" % len(Tf))

    lo_o, hi_o = np.asarray(CROP_LO, float), np.asarray(CROP_HI, float)
    world = np.asarray([ORIG_P + p[0] * L.DATUM_U + p[1] * L.DATUM_V + p[2] * (-L.DATUM_N)
                        for p in (lo_o, hi_o)])
    loc = L.to_local(world)
    clean = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER",
                           L.local_box(loc[0], loc[1], "ORIG"), "CLEAN")
    Tc = L.triangles(clean, tol=0.10, ang=0.18)
    del clean
    L.memory("clean tris %d" % len(Tc))

    rows = {}
    for cart_key, tag, tris in (("LOWERED_ORIGINAL_THUMB_CARTRIDGE", "FROZEN", Tf),
                                ("ORIGINAL_THUMB_CARTRIDGE", "CLEAN", Tc)):
        root, parts = leaf_parts(cart_key)
        print("\n=== %s exterior : straight-path exposure along each control's own axis ==="
              % tag)
        for label, short in NAME_MAP.items():
            cap, _ = L.as_single_solid(parts[label], short)
            axis, cen, area, tilt = press_axis(cap)
            frac, ns = exposure(cap, axis, tris)
            rows.setdefault(short, {})[tag] = {
                "axisWorld": axis.tolist(), "tiltFromJoystickAxisDeg": tilt,
                "dominantFaceAreaMm2": area, "topSamples": ns, "clearPathFraction": frac}
            print("  %-14s tilt=%5.2f deg  clear path = %6.1f %%  (%d samples)"
                  % (short, tilt, 100.0 * frac, ns))
            del cap
        del root, parts
        L.memory("exposure " + tag)

    print("\n%-14s %10s %10s %10s" % ("control", "ORIGINAL", "FROZEN", "delta"))
    for short in NAME_MAP.values():
        o = rows[short]["CLEAN"]["clearPathFraction"]
        f = rows[short]["FROZEN"]["clearPathFraction"]
        print("%-14s %9.1f%% %9.1f%% %9.1f pp" % (short, 100 * o, 100 * f, 100 * (f - o)))

    L.write_json(OUT / "a09_cap_axis_exposure.json", {"controls": rows, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
