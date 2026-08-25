"""K01 - per-button site survey, to choose the EASY and HARD gate cases (C08 §8).

C08 attaches each switch receiver to the shell locally, so what matters per
button is not the global cavity but the room immediately around its own opening:

    how far inward the shell's inner surface sits, at several radii -- this is
    the length of the transition from a curved landing to a flat seat
    how much lateral room exists before the receiver would hit a neighbour,
    a docs/101 Finger switch, the JOY package or the shell itself

Measured on the docs/101 shell, on each button's FROZEN press axis, using the
REV_I C07 seat planes so the two architectures are compared at the same depth.
Nothing is built here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from i02_original_external_stack import frame, skin_reference  # noqa: E402
from j02_collision import switch_groups  # noqa: E402

OUT = L.LAB / "01_site_survey"
RADII = (4.6, 5.6, 6.6, 7.6, 9.0)
NDIR = 36


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core_j = json.loads((L.REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    plc = json.loads((L.REV_I / "02_original_external_stack" /
                      "i02c_source_faithful_cap_placement.json").read_text(encoding="utf-8"))
    c07j = json.loads((L.REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    shells = {}
    for tag, key in (("JaD", "D101_JAD"), ("JfD", "D101_JFD")):
        shells[tag], _ = L.as_single_solid(import_step(L.SRC[key]), tag)
    T101 = np.concatenate([L.triangles(s, tol=0.05, ang=0.10) for s in shells.values()])
    Psh = np.concatenate([L.surf_points(s, 900000, tol=0.06) for s in shells.values()])
    Psh = Psh[np.linalg.norm(Psh - L.DATUM_P, axis=1) < 55.0]
    tree_sh = cKDTree(Psh)
    print("docs/101 shell: %d triangles, %d surface samples" % (len(T101), len(Psh)))
    L.memory("shell")

    groups = switch_groups()
    Pfing, owner = [], []
    for b, g in groups.items():
        for v in g.values():
            for s in v:
                q = L.surf_points(s, 20000, tol=0.03)
                Pfing.append(q)
                owner += [b] * len(q)
    Pfing = np.concatenate(Pfing)
    owner = np.asarray(owner)
    tree_f = cKDTree(Pfing)

    jw = L.unit(np.asarray(joyj["joyAxisWorld"], float))
    jc = np.asarray(joyj["knobCentreWorld"], float)
    keep = import_step(str(L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    from build123d import Location, Vector
    rz = Location(Vector(*[float(x) for x in (jw * c07j["szhRaiseMm"])]))
    Pszh_static, Pszh_prov = [], []
    for ch in list(getattr(keep, "children", []) or []):
        lb = str(ch.label)
        if not ch.solids() or not lb.startswith("SZH"):
            continue
        q = L.surf_points(ch.moved(rz), 40000, tol=0.05)
        (Pszh_prov if "MOVING" in lb else Pszh_static).append(q)
    tree_szh = cKDTree(np.concatenate(Pszh_static))
    tree_prov = cKDTree(np.concatenate(Pszh_prov)) if Pszh_prov else None
    L.memory("keepouts")

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    rows, cen_w = {}, {}
    print("")
    print("=== per-button site survey on the docs/101 shell ===")
    print("%-4s %8s %8s %9s %9s %9s %9s %9s %9s"
          % ("btn", "skin", "seat", "innerR46", "innerR66", "transit", "nearFing", "nearSZH", "nearT"))
    for s in names:
        lab = next(k for k, v in NAME_MAP.items() if v == s)
        cap, _ = L.as_single_solid(cart[lab], s)
        w, _, _ = true_axis(cap)
        P = L.surf_points(cap, 40000, tol=0.05)
        cen = P.mean(axis=0)
        cen_w[s] = cen
        ex, ey = frame(w)
        r_cap = float(np.hypot((P - cen) @ ex, (P - cen) @ ey).max())
        skin = skin_reference(T101, cen, w, ex, ey, r_cap)["referenceMm"]
        seat = float((np.asarray(core_j["seats"][s]["plateTopWorld"], float) - cen) @ w)

        # inner surface of the shell at each radius: cast outward from deep
        # inside along +w and take the FIRST material boundary
        inner = {}
        for r in RADII:
            vals = []
            for a in np.arange(0.0, 2 * np.pi - 1e-9, 2 * np.pi / NDIR):
                o = cen + ex * (r * np.cos(a)) + ey * (r * np.sin(a)) + w * (seat - 14.0)
                h = ray_intervals(T101, o, w, 0.0, 40.0)
                if h:
                    vals.append(seat - 14.0 + float(h[0][0]))
            inner[r] = ({"medianMm": float(np.median(vals)),
                         "p10Mm": float(np.percentile(vals, 10)),
                         "p90Mm": float(np.percentile(vals, 90)),
                         "samples": len(vals)} if vals else None)
        land = inner[5.6] or inner[6.6] or inner[4.6]
        transit = (land["medianMm"] - seat) if land else float("nan")

        d_f = tree_f.query(cen)[0]
        i_f = tree_f.query(cen)[1]
        d_szh = float(tree_szh.query(cen)[0])
        d_prov = float(tree_prov.query(cen)[0]) if tree_prov is not None else float("nan")
        rows[s] = {"skinOnAxisMm": skin, "seatOnAxisMm": seat,
                   "seatBelowSkinMm": skin - seat,
                   "shellInnerByRadius": inner,
                   "transitionLengthMm": transit,
                   "nearestFingerMm": float(d_f), "nearestFingerButton": str(owner[i_f]),
                   "nearestSzhStaticMm": d_szh, "nearestSzhProvisionalMm": d_prov,
                   "capCentreWorld": cen.tolist(), "axisWorld": w.tolist()}
        print("%-4s %8.3f %8.3f %9.3f %9.3f %9.3f %9.3f %9.3f"
              % (s, skin, seat,
                 inner[4.6]["medianMm"] if inner[4.6] else float("nan"),
                 inner[6.6]["medianMm"] if inner[6.6] else float("nan"),
                 transit, d_f, d_szh), end="")
        del cap
        L.memory("survey " + s)
    print("")

    # neighbour spacing between Thumb seats
    for s in names:
        d = sorted((float(np.linalg.norm(cen_w[s] - cen_w[o])), o) for o in names if o != s)
        rows[s]["nearestThumbMm"] = d[0][0]
        rows[s]["nearestThumbButton"] = d[0][1]

    print("")
    print("%-4s %10s %10s %10s %10s %10s %10s"
          % ("btn", "transit", "nearFing", "nearT", "nearSZH", "nearProv", "score"))
    for s in names:
        r = rows[s]
        # room score: the binding constraint is the smallest of the lateral
        # clearances, and a longer transition is harder to make printable
        room = min(r["nearestFingerMm"], r["nearestThumbMm"], r["nearestSzhStaticMm"])
        r["roomScoreMm"] = room
        print("%-4s %10.3f %10.3f %10.3f %10.3f %10.3f %10.3f"
              % (s, r["transitionLengthMm"], r["nearestFingerMm"], r["nearestThumbMm"],
                 r["nearestSzhStaticMm"], r["nearestSzhProvisionalMm"], room))

    easy = max(names, key=lambda s: rows[s]["roomScoreMm"])
    hard = min(names, key=lambda s: rows[s]["roomScoreMm"])
    print("")
    print("  CASE EASY = %s  (room %.3f mm; nearest Finger %s at %.3f, nearest Thumb %s at %.3f)"
          % (easy, rows[easy]["roomScoreMm"], rows[easy]["nearestFingerButton"],
             rows[easy]["nearestFingerMm"], rows[easy]["nearestThumbButton"],
             rows[easy]["nearestThumbMm"]))
    print("  CASE HARD = %s  (room %.3f mm; nearest Finger %s at %.3f, nearest Thumb %s at %.3f,"
          " SZH static %.3f)"
          % (hard, rows[hard]["roomScoreMm"], rows[hard]["nearestFingerButton"],
             rows[hard]["nearestFingerMm"], rows[hard]["nearestThumbButton"],
             rows[hard]["nearestThumbMm"], rows[hard]["nearestSzhStaticMm"]))

    tr = np.array([rows[s]["transitionLengthMm"] for s in names])
    print("")
    print("  transition length (shell inner surface at r=5.6 -> flat seat):"
          " %.3f to %.3f mm, mean %.3f" % (tr.min(), tr.max(), tr.mean()))
    print("  -> this is the whole C08 load path; C07 spans the same load "
          "through a remote slab")

    L.write_json(OUT / "k01_site_survey.json",
                 {"radiiMm": list(RADII), "buttons": rows,
                  "caseEasy": easy, "caseHard": hard,
                  "transitionStats": {"minMm": float(tr.min()), "maxMm": float(tr.max()),
                                      "meanMm": float(tr.mean())},
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
