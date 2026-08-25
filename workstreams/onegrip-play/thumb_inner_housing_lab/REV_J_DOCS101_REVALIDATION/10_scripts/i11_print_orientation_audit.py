"""I11 - print-orientation audit (REV_I FDM cleanup).

Evaluates a candidate IN the intended print orientation, and compares
orientations, so the choice is made on measurements rather than on habit.

Conventions used throughout:
    a face's slope from the build plate is phi, and |n . up| = cos(phi)
    a DOWN-facing face needs support when phi < 45 deg, i.e. |n . up| > 0.7071
    a vertical wall has |n . up| = 0 and never needs support

Support accessibility is tested by firing horizontal rays from each support
region: if any of 16 bearings escapes the part, a tool can reach it.  Trapped
support is the one thing that cannot be fixed after printing.
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
from b01_true_axes import ORDER  # noqa: E402
from b03_axis_authority import ray_intervals  # noqa: E402
from h03_placement import seat_solids  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402

OUT = L.LAB / "09_hand_finish"
COS45 = 0.70710678
GRID = 0.5


def tri_geom(T):
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    a = 0.5 * np.linalg.norm(n, axis=1)
    keep = a > 1.0e-12
    T, n, a = T[keep], n[keep], a[keep]
    n = n / np.linalg.norm(n, axis=1)[:, None]
    return T, n, a, T.mean(axis=1)


def audit(T, up, tag, seats=None, Tfull=None):
    up = L.unit(np.asarray(up, float))
    Tt, n, a, c = tri_geom(T)
    z = c @ up
    vz = (Tt @ up)                      # per-vertex heights, (n, 3)
    z0 = float(vz.min())
    z1 = float(vz.max())
    dot = n @ up
    down = dot < 0.0
    need = down & (np.abs(dot) > COS45)
    # A face rests on the bed only if the WHOLE triangle is in the first-layer
    # band.  Using the centroid let a single low standoff pad drag z0 down and
    # then disqualify the real bed face, which reported 0.0 mm2 of bed contact
    # on a part with a flat 1100 mm2 underside.
    bed = need & (vz.max(axis=1) < z0 + 0.40)
    sup = need & ~bed

    ex, ey = frame(up)
    res = {"orientation": tag, "upWorld": up.tolist(),
           "heightMm": z1 - z0,
           "totalAreaMm2": float(a.sum()),
           "bedContactAreaMm2": float(a[bed].sum()),
           "supportedAreaMm2": float(a[sup].sum()),
           "supportedFraction": float(a[sup].sum() / a.sum()),
           "maxSupportHeightMm": float((z[sup] - z0).max()) if sup.any() else 0.0}

    regions = []
    if sup.any():
        # Rasterise the triangle AREA, not its centroid.  A flat slab underside
        # tessellates into two 40 mm2 triangles whose centroids land in one
        # cell, which reported every support region as span 0.00 mm.
        Ts, asup, zsup, cs = Tt[sup], a[sup], z[sup], c[sup]
        bary = np.array([[1 / 3, 1 / 3, 1 / 3], [.6, .2, .2], [.2, .6, .2], [.2, .2, .6],
                         [.8, .1, .1], [.1, .8, .1], [.1, .1, .8], [.4, .4, .2],
                         [.4, .2, .4], [.2, .4, .4]])
        S = np.einsum("kb,nbj->nkj", bary, Ts)          # (n, k, 3) samples
        owner = np.repeat(np.arange(len(Ts)), bary.shape[0])
        Q = S.reshape(-1, 3)
        x = (Q - Q.mean(axis=0)) @ ex
        y = (Q - Q.mean(axis=0)) @ ey
        gi = np.round((x - x.min()) / GRID).astype(int)
        gj = np.round((y - y.min()) / GRID).astype(int)
        m = np.zeros((gi.max() + 3, gj.max() + 3), bool)
        m[gi + 1, gj + 1] = True
        lab, k = ndimage.label(m, structure=np.ones((3, 3), bool))
        idx = lab[gi + 1, gj + 1]
        for r in range(1, k + 1):
            qsel = idx == r
            if not qsel.any():
                continue
            tsel = np.unique(owner[qsel])
            ar = float(asup[tsel].sum())
            if ar < 1.0:
                continue
            hh = float((zsup[tsel] - z0).mean())
            span = float(max(x[qsel].max() - x[qsel].min(), y[qsel].max() - y[qsel].min()))
            pt = cs[tsel].mean(axis=0)
            acc = "UNKNOWN"
            if Tfull is not None:
                free = 0
                for th in np.arange(0.0, 2 * np.pi - 1e-9, np.pi / 8.0):
                    d = ex * np.cos(th) + ey * np.sin(th)
                    h = ray_intervals(Tfull, pt - up * 1.0, d, 0.05, 90.0)
                    if not h or sum(b - aa for aa, b in h) < 0.5:
                        free += 1
                acc = ("ACCESSIBLE (%d/16 clear bearings)" % free) if free else "TRAPPED"
            regions.append({"areaMm2": ar, "heightAboveBedMm": hh, "planSpanMm": span,
                            "accessibility": acc})

    regions.sort(key=lambda r: -r["areaMm2"])
    res["supportRegions"] = regions
    res["trappedRegions"] = sum(1 for r in regions if r["accessibility"] == "TRAPPED")

    hits = 0
    if seats is not None and sup.any():
        for s, u in seats.items():
            d = c[sup] - u["top"]
            loc = np.stack([d @ u["ex"], d @ u["ey"], d @ u["w"]], axis=1)
            hits += int(((np.abs(loc[:, 0]) < 4.3) & (np.abs(loc[:, 1]) < 4.3)
                         & (loc[:, 2] > -0.6)).sum())
    res["supportOnCriticalInterfaces"] = hits

    zs = np.arange(z0 + 0.2, z1, 1.0)
    areas = []
    P = Tt.reshape(-1, 3)
    pz = P @ up
    px, py = P @ ex, P @ ey
    for zz in zs:
        band = np.abs(pz - zz) < 0.5
        if band.sum() < 3:
            areas.append(0.0)
            continue
        areas.append(float((px[band].max() - px[band].min())
                           * (py[band].max() - py[band].min())))
    res["minSliceBboxMm2"] = float(min(areas)) if areas else 0.0
    res["minSliceHeightMm"] = float(zs[int(np.argmin(areas))] - z0) if areas else 0.0
    return res


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core = json.loads((L.LAB / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joy = json.loads((L.LAB / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]
    seats = {}
    for s in names:
        r = core["seats"][s]
        w = np.asarray(r["axisWorld"], float)
        u = seat_solids(np.asarray(r["capUndersideWorld"], float), w, s)
        seats[s] = {"w": w, "top": u["plateTopPoint"], "ex": u["ex"], "ey": u["ey"]}
    jw = L.unit(np.asarray(joy["joyAxisWorld"], float))

    cands = {}
    for tag, fn in (("C06", "C06_SOURCE_FAITHFUL_THUMB_CORE.step"),
                    ("C07", "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step")):
        p = L.LAB / "07_prototype" / fn
        if p.exists():
            s, _ = L.as_single_solid(import_step(str(p)), tag)
            cands[tag] = L.triangles(s, tol=0.04, ang=0.09)
            del s
    L.memory("load")

    ors = {"JOY_AXIS_UP (chosen)": jw,
           "JOY_AXIS_DOWN (flipped)": -jw,
           "THUMB_NORMAL_UP": -L.DATUM_N,
           "IN_PLANE (on edge)": L.DATUM_V}
    out = {}
    for tag, T in cands.items():
        print("")
        print("=== %s ===" % tag)
        print("%-26s %8s %10s %10s %9s %8s %9s"
              % ("orientation", "height", "bed mm2", "support", "frac", "trapped", "critical"))
        rows = []
        for oname, up in ors.items():
            r = audit(T, up, oname, seats=seats, Tfull=T)
            rows.append(r)
            print("%-26s %8.2f %10.1f %10.1f %8.1f%% %8d %9d"
                  % (oname, r["heightMm"], r["bedContactAreaMm2"], r["supportedAreaMm2"],
                     100 * r["supportedFraction"], r["trappedRegions"],
                     r["supportOnCriticalInterfaces"]))
            L.memory("%s %s" % (tag, oname))
        out[tag] = rows

    print("")
    print("=== chosen orientation detail: JOY_AXIS_UP ===")
    for tag in cands:
        r = [x for x in out[tag] if x["orientation"].startswith("JOY_AXIS_UP")][0]
        print("  %s: height %.2f mm, bed contact %.1f mm2, support %.1f mm2 (%.1f%%), "
              "max support height %.2f mm"
              % (tag, r["heightMm"], r["bedContactAreaMm2"], r["supportedAreaMm2"],
                 100 * r["supportedFraction"], r["maxSupportHeightMm"]))
        print("     smallest slice bbox %.1f mm2 at %.1f mm above the bed"
              % (r["minSliceBboxMm2"], r["minSliceHeightMm"]))
        for x in r["supportRegions"][:6]:
            print("     region %8.2f mm2  h %6.2f  span %6.2f  %s"
                  % (x["areaMm2"], x["heightAboveBedMm"], x["planSpanMm"], x["accessibility"]))
        print("     support landing on a switch or joystick interface: %d faces"
              % r["supportOnCriticalInterfaces"])

    # press-load direction against the layer normal
    print("")
    print("=== button press load vs layer direction (chosen orientation) ===")
    ang = {}
    for s in names:
        a = float(np.degrees(np.arccos(abs(float(seats[s]["w"] @ jw)))))
        ang[s] = a
    print("  press axes sit %.2f-%.2f deg off PRINT_UP, so the press load is carried"
          % (min(ang.values()), max(ang.values())))
    print("  as compression THROUGH the layers, not as interlayer tension.")
    print("  The slab spans the layer plane, so its bending stress is in-plane.")

    L.write_json(OUT / "i11_print_orientation.json",
                 {"overhangThresholdDeg": 45.0, "candidates": out,
                  "chosen": "JOY_AXIS_UP", "pressAxisOffPrintUpDeg": ang,
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
