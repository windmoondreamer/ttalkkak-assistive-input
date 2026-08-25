"""I02 - Thumb button EXTERNAL stack audit, ORIGINAL vs CURRENT (REV_I sections 5, 9).

REV_H measured only what happens inside the shell.  Section 9 makes cap
protrusion a functional requirement, so the ORIGINAL ergonomic stack has to be
measured before any seat depth can be called correct, and the CURRENT frozen
stack has to be compared against it.

Everything is measured on each button's TRUE press axis (b03), never world Z:
the Thumb panel is inclined and the eight caps sit at 0.00 - 9.38 deg to each
other, so a global Z reading is meaningless.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402

OUT = L.LAB / "02_original_external_stack"
OUTWARD = -L.DATUM_N
RING_IN, RING_OUT = 0.35, 1.60  # skin-reference ring outboard of THIS cap
CAST = 40.0                     # ray start distance outboard of the cap centre
ACT_ENGAGE = 0.345              # H02: actuator tip sits this far inside the cap
SW_TRAVEL = 0.25                # datasheet-class tact travel, PROVISIONAL
PROT_TOL = 0.30                 # protrusion deviation the prototype may carry


def frame(w):
    a = np.array([1.0, 0.0, 0.0]) if abs(w[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    ex = L.unit(np.cross(a, w))
    return ex, np.cross(w, ex)


def skin_reference(T, cen, w, ex, ey, r_cap):
    """Outer skin height on the axis, by ray-casting inward from outside.

    Two corrections were needed to make this measure the right surface:

    1. Binning surface samples and keeping the outermost per bin is wrong on a
       curved grip -- points on the far side of the body project high along w
       and win the bin.  Casting from outside and taking the FIRST hit cannot
       pick a far-side surface.
    2. A fixed 5.6-9.5 mm annulus straddles the NEIGHBOURING openings (adjacent
       cap centres are only 10.3 mm apart and the caps are 7.6 mm wide, so the
       free ring is about 1.4 mm), and rays falling through a neighbouring hole
       return a surface several mm deeper.  The ring is therefore sized from
       this cap, and the statistic is a high percentile: a ray can return a
       surface DEEPER than the local skin but never one further out.
    """
    tops = []
    for r in np.arange(r_cap + RING_IN, r_cap + RING_OUT + 1e-9, 0.25):
        for a in np.arange(0.0, 2.0 * np.pi - 1e-9, np.pi / 60.0):
            o = cen + ex * (r * np.cos(a)) + ey * (r * np.sin(a)) + w * CAST
            h = ray_intervals(T, o, -w, 0.0, 2.0 * CAST)
            if h:
                tops.append(CAST - float(h[0][0]))
    if len(tops) < 30:
        return None
    tops = np.asarray(tops)
    return {"referenceMm": float(np.percentile(tops, 90)),
            "p90Mm": float(np.percentile(tops, 90)),
            "medianMm": float(np.median(tops)), "maxMm": float(tops.max()),
            "p10Mm": float(np.percentile(tops, 10)),
            "throughHoleFraction": float((tops < np.percentile(tops, 90) - 1.5).mean()),
            "ringMm": [float(r_cap + RING_IN), float(r_cap + RING_OUT)],
            "samples": int(tops.size)}


def lateral_clearance(Psh, Pcap, cen, w, ex, ey, cap_und, r0):
    """Side gap between cap and opening wall, in the plane of the panel.

    Two rejected methods, both worth keeping:

    * Ray casting: ray_intervals pairs crossings and returns None on an odd
      count, so a radial probe that STARTS inside the cap is discarded -- four
      of the eight buttons produced no samples at all.
    * Sector statistics: inside one 15 deg sector the closest shell point and
      the furthest cap point are at DIFFERENT angles, and a square cap's radius
      swings from 3.80 mm on an axis to 5.37 mm at a corner, so the difference
      is not a gap.  Every button came out negative.

    A nearest-neighbour query restricted to the same depth band compares
    matched locations and makes no parity assumption.
    """
    lo, hi = cap_und + 0.30, r0 - 0.30
    if hi <= lo:
        return {"minMm": float("nan"), "medianMm": float("nan"), "samples": 0}

    def band(P):
        d = P - cen
        s = d @ w
        m = (s >= lo) & (s <= hi)
        return m, np.hypot(d[m] @ ex, d[m] @ ey)

    msh, rs = band(Psh)
    mcap, _ = band(Pcap)
    Ps = Psh[msh][rs < 14.0]
    Pc = Pcap[mcap]
    if len(Ps) < 100 or len(Pc) < 100:
        return {"minMm": float("nan"), "medianMm": float("nan"), "samples": 0}
    d = cKDTree(Ps).query(Pc)[0]
    return {"minMm": float(d.min()), "p10Mm": float(np.percentile(d, 10)),
            "medianMm": float(np.median(d)), "samples": int(d.size)}


def load_shell(keys, centre, tag):
    T, P = [], []
    for k in keys:
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        T.append(L.triangles(s, tol=0.08, ang=0.15))
        P.append(L.surf_points(s, 700000, tol=0.08))
        del s
    T = np.concatenate(T)
    P = np.concatenate(P)
    P = P[np.linalg.norm(P - centre, axis=1) < 60.0]
    print("%-14s shell: %d triangles, %d surface samples near the Thumb"
          % (tag, len(T), len(P)))
    L.memory(tag + " shell")
    return T, P


def audit(Tsh, Psh, cart_key, tag):
    _, cart = leaf_parts(cart_key)
    rows, cen_w = {}, {}
    print("")
    print("=== %s Thumb button external stack (TRUE press axis) ===" % tag)
    print("%-5s %6s %9s %9s %9s %9s %8s %8s"
          % ("ctrl", "tilt", "skinRef", "capTop", "capUnder", "actTip", "insert", "latClr"))
    for short in ORDER:
        if short == "JOY":
            continue
        lab = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[lab], short)
        w, _, tilt = true_axis(cap)
        P = L.surf_points(cap, 60000, tol=0.04)
        cen = P.mean(axis=0)
        ex, ey = frame(w)
        s = (P - cen) @ w
        cap_top, cap_und = float(s.max()), float(s.min())
        r_cap = float(np.hypot((P - cen) @ ex, (P - cen) @ ey).max())
        ref = skin_reference(Tsh, cen, w, ex, ey, r_cap)
        if ref is None:
            print("%-5s  no ring samples" % short)
            del cap
            continue
        r0 = ref["referenceMm"]
        lat = lateral_clearance(Psh, P, cen, w, ex, ey, cap_und, r0)
        rows[short] = {
            "tiltDeg": tilt, "axisWorld": w.tolist(), "capCentreWorld": cen.tolist(),
            "capOuterRadiusMm": r_cap, "outerSkinReference": ref,
            "shellToCapTopMm": cap_top - r0,
            "shellToCapUndersideMm": cap_und - r0,
            "shellToActuatorTipMm": cap_und + ACT_ENGAGE - r0,
            "unpressedProtrusionMm": cap_top - r0,
            "pressedProtrusionMm": cap_top - r0 - SW_TRAVEL,
            "assumedSwitchTravelMm": SW_TRAVEL,
            # A plain block cap has no flange, so it can sink until its top face
            # reaches the skin.  That equals the protrusion and is an order of
            # magnitude more than tact travel, so it never binds.
            "capTopReachesSkinAtMm": cap_top - r0,
            "capSkirtInsertionDepthMm": r0 - cap_und,
            "capHeightMm": cap_top - cap_und,
            "lateralClearanceToOpening": lat,
        }
        cen_w[short] = cen
        print("%-5s %6.2f %9.3f %9.3f %9.3f %9.3f %8.3f %8.3f"
              % (short, tilt, r0, cap_top - r0, cap_und - r0,
                 cap_und + ACT_ENGAGE - r0, r0 - cap_und, lat["medianMm"]))
        del cap
        L.memory("%s cap %s" % (tag, short))
    return rows, cen_w


def summarise(rows, cen_w, tag):
    pr = np.array([rows[k]["unpressedProtrusionMm"] for k in rows])
    ins = np.array([rows[k]["capSkirtInsertionDepthMm"] for k in rows])
    tl = np.array([rows[k]["tiltDeg"] for k in rows])
    lc = np.array([rows[k]["lateralClearanceToOpening"]["medianMm"] for k in rows])
    print("")
    print("=== %s protrusion law ===" % tag)
    print("  unpressed protrusion  min %.3f  max %.3f  spread %.3f  mean %.3f  sd %.3f"
          % (pr.min(), pr.max(), pr.max() - pr.min(), pr.mean(), pr.std()))
    print("  skirt insertion depth min %.3f  max %.3f  spread %.3f  mean %.3f"
          % (ins.min(), ins.max(), ins.max() - ins.min(), ins.mean()))
    print("  lateral clearance to opening  median %.3f  min %.3f"
          % (float(np.median(lc)), float(np.nanmin(lc))))
    r = float(np.corrcoef(tl, pr)[0, 1])
    print("  correlation(tilt, protrusion) = %+.3f" % r)
    law = ("ONE COMMON PROTRUSION LAW" if pr.max() - pr.min() <= 0.50 else
           "TWO OR MORE PROTRUSION VARIANTS")
    print("  -> %s  (spread %.3f mm against a 0.50 mm threshold)"
          % (law, pr.max() - pr.min()))

    names = [k for k in ORDER if k != "JOY" and k in cen_w]
    sp = {}
    for i in range(len(names)):
        for k in range(i + 1, len(names)):
            a, b = names[i], names[k]
            dd = float(np.linalg.norm(cen_w[a] - cen_w[b]))
            if dd < 20.0:
                sp["%s-%s" % (a, b)] = dd
    return {"buttons": rows, "protrusionLaw": law,
            "protrusionStats": {"minMm": float(pr.min()), "maxMm": float(pr.max()),
                                "spreadMm": float(pr.max() - pr.min()),
                                "meanMm": float(pr.mean()), "sdMm": float(pr.std())},
            "insertionStats": {"minMm": float(ins.min()), "maxMm": float(ins.max()),
                               "spreadMm": float(ins.max() - ins.min()),
                               "meanMm": float(ins.mean())},
            "tiltProtrusionCorrelation": r,
            "lateralClearanceMedianMm": float(np.median(lc)),
            "neighbourSpacingMm": sp}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # ORIGINAL shell = clean pre-finger pair, which still carries the ORIGINAL
    # (un-lowered) Thumb openings.  CURRENT = the exact approved lowered export.
    To, Po = load_shell(("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER"),
                        L.DATUM_P - L.THUMB_DELTA, "ORIGINAL")
    ro, co = audit(To, Po, "ORIGINAL_THUMB_CARTRIDGE", "ORIGINAL")
    so = summarise(ro, co, "ORIGINAL")
    del To, Po
    L.memory("original done")

    Tc, Pc = load_shell(("JAD_APPROVED", "JFD_APPROVED"), L.DATUM_P, "CURRENT")
    rc, cc = audit(Tc, Pc, "LOWERED_ORIGINAL_THUMB_CARTRIDGE", "CURRENT FROZEN")
    sc = summarise(rc, cc, "CURRENT FROZEN")
    del Tc, Pc

    print("")
    print("=== ORIGINAL vs CURRENT FROZEN cap protrusion (section 9) ===")
    print("%-5s %12s %12s %10s %12s %12s"
          % ("ctrl", "orig prot", "curr prot", "delta", "orig inset", "curr inset"))
    dev = {}
    for k in [x for x in ORDER if x != "JOY"]:
        if k not in ro or k not in rc:
            continue
        a = ro[k]["unpressedProtrusionMm"]
        b = rc[k]["unpressedProtrusionMm"]
        dev[k] = {"originalMm": a, "currentMm": b, "deltaMm": b - a,
                  "originalInsertionMm": ro[k]["capSkirtInsertionDepthMm"],
                  "currentInsertionMm": rc[k]["capSkirtInsertionDepthMm"]}
        print("%-5s %12.3f %12.3f %+10.3f %12.3f %12.3f"
              % (k, a, b, b - a, ro[k]["capSkirtInsertionDepthMm"],
                 rc[k]["capSkirtInsertionDepthMm"]))
    d = np.array([v["deltaMm"] for v in dev.values()])
    print("  protrusion deviation: min %+.3f  max %+.3f  mean %+.3f  max|d| %.3f"
          % (d.min(), d.max(), d.mean(), np.abs(d).max()))
    verdict = ("CURRENT PROTRUSION MATCHES THE ORIGINAL LAW"
               if np.abs(d).max() <= PROT_TOL else
               "CURRENT PROTRUSION DEVIATES FROM THE ORIGINAL LAW")
    print("  -> %s (%.2f mm tolerance)" % (verdict, PROT_TOL))

    L.write_json(OUT / "i02_original_external_stack.json",
                 {"ringOffsetMm": [RING_IN, RING_OUT], "actuatorEngagementMm": ACT_ENGAGE,
                  "assumedSwitchTravelMm": SW_TRAVEL,
                  "assumedSwitchTravelQuality": "PROVISIONAL - datasheet class, not measured",
                  "ORIGINAL": so, "CURRENT_FROZEN": sc, "protrusionDeviation": dev,
                  "protrusionDeviationStats": {"minMm": float(d.min()), "maxMm": float(d.max()),
                                               "meanMm": float(d.mean()),
                                               "maxAbsMm": float(np.abs(d).max())},
                  "protrusionVerdict": verdict, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
