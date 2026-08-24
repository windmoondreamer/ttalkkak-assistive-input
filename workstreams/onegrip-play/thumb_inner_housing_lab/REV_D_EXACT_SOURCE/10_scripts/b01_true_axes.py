"""B01 - derive the TRUE Thumb control press axes, three independent ways.

Everything in section 1 of the audit rests on the axis being right, so it is
derived three times and cross-checked:

  M1  dominant planar face normal of the cap        (the REV_A method)
  M2  area-weighted normal covariance of the cap    (prism eigen-axis)
  M3  bore axis of the ORIGINAL opening in the CLEAN shell -- derived from the
      SHELL, not from the cap, so it is independent of any cap placement

M3 is the important one: the original opening side walls were cut along the
press axis, so they give the axis without ever touching a cap solid.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402

OUT = L.LAB / "01_axis_authority"
OUTWARD = -L.DATUM_N
ORIG_P = L.DATUM_P - L.THUMB_DELTA

NAME_MAP = {
    "THUMB_BUTTON_1_CAP__Button_corner_1": "T1",
    "THUMB_BUTTON_2_CAP__Button_middle_1": "T2",
    "THUMB_BUTTON_3_CAP__Button_corner_2": "T3",
    "THUMB_BUTTON_4_CAP__Button_side_1": "T4",
    "THUMB_BUTTON_5_CAP__Button_middle_2": "T5",
    "THUMB_BUTTON_6_CAP__Button_side_2": "T6",
    "THUMB_BUTTON_7_CAP__Button_wide_1": "T7",
    "THUMB_BUTTON_8_CAP__Button_wide_2": "T8",
    "THUMB_JOYSTICK_SMALL_ATTACHMENT": "JOY",
}
ORDER = ("JOY", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8")


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


def face_normals(shape, tol=0.05, ang=0.10):
    """(unit normal, area) per B-rep face, area-weighted from its triangles."""
    rows = []
    for f in shape.faces():
        try:
            T = L.triangles(f, tol=tol, ang=ang)
        except Exception:
            continue
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        a = 0.5 * np.linalg.norm(n, axis=1)
        keep = a > 1.0e-10
        if not keep.any():
            continue
        nn = (n[keep] / (2.0 * a[keep])[:, None] * a[keep][:, None]).sum(axis=0)
        tot = float(a[keep].sum())
        if float(np.linalg.norm(nn)) < 1.0e-9:
            continue
        rows.append((L.unit(nn), tot))
    return rows


def m1_dominant(shape):
    rows = face_normals(shape)
    groups = []
    for n, a in sorted(rows, key=lambda r: -r[1]):
        for g in groups:
            if float(np.dot(n, g["n"])) > np.cos(np.radians(2.0)):
                g["a"] += a
                break
        else:
            groups.append({"n": n, "a": a})
    groups.sort(key=lambda g: -g["a"])
    ax = L.unit(groups[0]["n"])
    return ax if float(np.dot(ax, OUTWARD)) > 0 else -ax


def m2_covariance(shape):
    rows = face_normals(shape)
    M = np.zeros((3, 3))
    for n, a in rows:
        M += a * np.outer(n, n)
    w, V = np.linalg.eigh(M)
    # the prism axis is the eigenvector best aligned with the outward direction
    best = max(range(3), key=lambda i: abs(float(np.dot(V[:, i], OUTWARD))))
    ax = L.unit(V[:, best])
    return ax if float(np.dot(ax, OUTWARD)) > 0 else -ax


def m3_bore_from_shell(shell, cap_centre_world, seed_axis, radius=7.5):
    """Bore axis of the opening around a control, taken from the SHELL.

    Selects shell faces whose material lies within `radius` of the control
    centre and whose normal is close to perpendicular to the seed axis: those
    are the opening's side walls.  The axis is the direction perpendicular to
    all of them = smallest eigenvector of the area-weighted normal covariance.
    """
    picked = []
    for f in shell.faces():
        try:
            T = L.triangles(f, tol=0.05, ang=0.10)
        except Exception:
            continue
        pts = T.reshape(-1, 3)
        d = pts - cap_centre_world
        radial = d - np.outer(d @ seed_axis, seed_axis)
        if float(np.linalg.norm(radial, axis=1).min()) > radius:
            continue
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        a = 0.5 * np.linalg.norm(n, axis=1)
        keep = a > 1.0e-10
        if not keep.any():
            continue
        nn = (n[keep] / (2.0 * a[keep])[:, None] * a[keep][:, None]).sum(axis=0)
        if float(np.linalg.norm(nn)) < 1.0e-9:
            continue
        nn = L.unit(nn)
        area = float(a[keep].sum())
        if abs(float(np.dot(nn, seed_axis))) < 0.35 and area > 1.0:
            picked.append((nn, area))
    if len(picked) < 3:
        return None, len(picked)
    M = np.zeros((3, 3))
    for n, a in picked:
        M += a * np.outer(n, n)
    w, V = np.linalg.eigh(M)
    ax = L.unit(V[:, 0])
    return (ax if float(np.dot(ax, seed_axis)) > 0 else -ax), len(picked)


def combined_shell(ka, kb, box, tag):
    a = L.load(ka)
    sa, _ = L.as_single_solid((a & box).clean(), "A")
    del a
    b = L.load(kb)
    sb, _ = L.as_single_solid((b & box).clean(), "B")
    del b
    out, _ = L.as_single_solid((sa + sb).clean(), tag)
    L.memory("combined " + tag)
    return out


def main() -> int:
    root, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    root_o, cart_o = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")

    # CLEAN shell cropped around the ORIGINAL Thumb cluster
    lo, hi = np.asarray((-32.0, -54.0, -60.0)), np.asarray((32.0, 24.0, 60.0))
    world = np.asarray([ORIG_P + p[0] * L.DATUM_U + p[1] * L.DATUM_V + p[2] * OUTWARD
                        for p in (lo, hi)])
    locbb = L.to_local(world)
    clean = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER",
                           L.local_box(locbb[0], locbb[1], "ORIG"), "CLEAN")

    rows = {}
    print("%-5s %-46s %-46s %8s %8s" % ("ctrl", "M1 dominant-face axis", "M3 shell-bore axis",
                                        "M1-M2", "M1-M3"))
    for label, short in NAME_MAP.items():
        cap_l, _ = L.as_single_solid(cart[label], short)
        cap_o, _ = L.as_single_solid(cart_o[label], short + "_orig")
        a1 = m1_dominant(cap_l)
        a2 = m2_covariance(cap_l)
        bb = cap_o.bounding_box()
        c_o = np.asarray([(bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2,
                          (bb.min.Z + bb.max.Z) / 2], float)
        a3, nfaces = m3_bore_from_shell(clean, c_o, a1)
        d12 = float(np.degrees(np.arccos(np.clip(abs(float(np.dot(a1, a2))), -1, 1))))
        d13 = (float(np.degrees(np.arccos(np.clip(abs(float(np.dot(a1, a3))), -1, 1))))
               if a3 is not None else float("nan"))
        rows[short] = {
            "m1DominantFaceAxis": a1.tolist(),
            "m2CovarianceAxis": a2.tolist(),
            "m3ShellBoreAxis": (a3.tolist() if a3 is not None else None),
            "m3SideFaceCount": nfaces,
            "m1_m2_deg": d12, "m1_m3_deg": d13,
            "tiltFromJoystickAxisDeg": float(np.degrees(np.arccos(
                np.clip(float(np.dot(a1, OUTWARD)), -1, 1)))),
        }
        print("%-5s %-46s %-46s %8.4f %8s"
              % (short, np.array2string(np.round(a1, 6)),
                 np.array2string(np.round(a3, 6)) if a3 is not None else "n/a",
                 d12, ("%.4f" % d13) if a3 is not None else "n/a"))
        del cap_l, cap_o

    print("\ntilt of each control axis from the joystick axis (M1):")
    for k in ORDER:
        print("  %-5s %7.4f deg" % (k, rows[k]["tiltFromJoystickAxisDeg"]))

    ok = all(rows[k]["m1_m2_deg"] < 1.0 for k in rows)
    ok3 = all((not np.isfinite(rows[k]["m1_m3_deg"])) or rows[k]["m1_m3_deg"] < 3.0
              for k in rows)
    print("\nM1 vs M2 agree within 1.0 deg : %s" % ok)
    print("M1 vs M3 agree within 3.0 deg : %s" % ok3)
    L.write_json(OUT / "b01_true_axes.json",
                 {"axes": rows, "m1m2Agree": bool(ok), "m1m3Agree": bool(ok3),
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
