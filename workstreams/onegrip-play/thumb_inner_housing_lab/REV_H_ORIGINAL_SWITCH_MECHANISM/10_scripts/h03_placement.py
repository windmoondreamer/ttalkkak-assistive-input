"""H03 - place the ORIGINAL seat mechanism behind each CURRENT frozen opening.

REV_H sections 7 and 8.  No carrier is built; this produces the per-button table
that section 8 requires before any common plate may be generated.

Seat unit, in seat-local coordinates with n = 0 at the plate TOP face
(all values measured in H02 from exact B-rep):

    terminal tip      -3.654
    plate bottom      -2.003
    plate top          0.000
    switch body       +0.051 .. +3.195   6.04 x 6.04 mm
    actuator          +3.195 .. +5.104   3.51 mm
    cap underside     +4.759

Placement rule: the plate top plane sits 4.759 mm below the CURRENT cap
underside, on the CURRENT true press axis.  Nothing about the controls moves.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import (Align, Box, Compound, Cylinder, Location, Plane, Vector,
                       export_step, import_step)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from d02_housing_vs_exact import approved_shell  # noqa: E402
from h01_seat_audit import axis_frame  # noqa: E402

OUT = L.LAB / "03_placement"
OUTWARD = -L.DATUM_N
KEEPOUTS = L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"

CAP_TO_PLATE = 4.759          # cap underside -> plate top face
PLATE_T = 2.003
BODY_LO, BODY_HI = 0.051, 3.195
BODY_XY = 6.04
POCKET_XY = 6.40              # original #button_module_width + 2 x tolerance
ACT_HI = 5.104
ACT_D = 3.51
TERM_LO = -3.654
TERM_XY = (7.568, 4.632)
SEAT_PATCH = 11.0             # local plate island the seat needs
HARNESS_MM = 15.0


def seat_solids(cen_cap, w, tag):
    """Build the seat unit on a control's axis.  cen_cap = cap underside point."""
    ex, ey = axis_frame(w)
    top = cen_cap - w * CAP_TO_PLATE          # plate top face point
    def at(n_lo, n_hi, sx, sy, label):
        pl = Plane(origin=L.xyz(top + w * n_lo), x_dir=L.xyz(ex), z_dir=L.xyz(w))
        s = pl * Box(sx, sy, n_hi - n_lo, align=(Align.CENTER, Align.CENTER, Align.MIN))
        s.label = label
        return s
    body = at(BODY_LO, BODY_HI, BODY_XY, BODY_XY, tag + "_BODY")
    pocket = at(BODY_LO - 0.10, BODY_HI + 0.10, POCKET_XY, POCKET_XY, tag + "_POCKET")
    term = at(TERM_LO, BODY_LO, TERM_XY[0], TERM_XY[1], tag + "_TERMINALS")
    plate = at(-PLATE_T, 0.0, SEAT_PATCH, SEAT_PATCH, tag + "_PLATE_ISLAND")
    pl = Plane(origin=L.xyz(top + w * BODY_HI), x_dir=L.xyz(ex), z_dir=L.xyz(w))
    act = pl * Cylinder(ACT_D / 2.0, ACT_HI - BODY_HI, align=(Align.CENTER, Align.CENTER, Align.MIN))
    act.label = tag + "_ACTUATOR"
    return {"body": body, "pocket": pocket, "terminals": term, "plate": plate,
            "actuator": act, "plateTopPoint": top, "ex": ex, "ey": ey}


def main() -> int:
    approved = approved_shell()
    Tap = L.triangles(approved, tol=0.05, ang=0.10)
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    keep = import_step(str(KEEPOUTS))
    ko = {}
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if ch.solids() and not lab.startswith("CAP_"):
            ko[lab] = L.as_single_solid(ch, lab)[0]
    print("keep-outs loaded: %d" % len(ko))

    seats, rows = {}, {}
    print("\n=== per-button seat placement against the exact approved shell ===")
    print("%-5s %10s %10s %10s %10s %10s %10s"
          % ("ctrl", "body^shell", "term^shell", "act^shell", "termDepth", "capErr", "axErr"))
    for short in ORDER:
        if short == "JOY":
            continue
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, tilt = true_axis(cap)
        p = L.surf_points(cap, 40000, tol=0.04)
        c = p.mean(axis=0)
        proj = (p - c) @ w
        cap_under = c + w * float(proj.min())
        s = seat_solids(cap_under, w, short)
        seats[short] = s

        i_body = L.inter_vol(s["body"], approved)
        i_term = L.inter_vol(s["terminals"], approved)
        i_act = L.inter_vol(s["actuator"], approved)
        # how far can a terminal descend before hitting shell material?
        tip = s["plateTopPoint"] + w * TERM_LO
        iv = ray_intervals(Tap, s["plateTopPoint"], -w, 0.0, 60.0)
        depth = float(min([q[0] for q in (iv or []) if q[0] > 0.0], default=60.0))
        rows[short] = {
            "tiltDeg": tilt,
            "capUndersideWorld": cap_under.tolist(),
            "axisWorld": w.tolist(),
            "plateTopWorld": s["plateTopPoint"].tolist(),
            "actuatorCentreErrorMm": 0.0,      # built on the frozen axis by construction
            "axisAngularErrorDeg": 0.0,
            "bodyShellInterferenceMm3": i_body,
            "terminalShellInterferenceMm3": i_term,
            "actuatorShellInterferenceMm3": i_act,
            "terminalFreeDepthBelowPlateTopMm": depth,
            "terminalNeedMm": -TERM_LO,
        }
        print("%-5s %10.4f %10.4f %10.4f %10.3f %10.4f %10.4f"
              % (short, i_body, i_term, i_act, depth, 0.0, 0.0))
        del cap
        L.memory("seat " + short)

    # neighbouring-seat interference
    print("\n=== neighbouring-seat interference (body + terminals + plate island) ===")
    names = [s for s in ORDER if s != "JOY"]
    pair = {}
    worst = 0.0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            v = 0.0
            for ka in ("body", "terminals"):
                for kb in ("body", "terminals"):
                    v += L.inter_vol(seats[a][ka], seats[b][kb])
            vp = L.inter_vol(seats[a]["plate"], seats[b]["plate"])
            if v > 1e-6 or vp > 1e-6:
                pair["%s-%s" % (a, b)] = {"mechanismMm3": v, "plateIslandMm3": vp}
                worst = max(worst, v)
                print("  %-8s mechanism %9.4f mm3   plate islands overlap %9.4f mm3"
                      % ("%s-%s" % (a, b), v, vp))
    if not pair:
        print("  none")
    print("  worst mechanism-to-mechanism overlap = %.4f mm3" % worst)

    # keep-outs
    print("\n=== seat mechanism vs keep-outs ===")
    kres = {}
    for short in names:
        for kname, ksolid in ko.items():
            v = sum(L.inter_vol(seats[short][k], ksolid) for k in ("body", "terminals", "actuator"))
            if v > 1e-6:
                kres["%s / %s" % (short, kname)] = v
                print("  %-5s vs %-32s %10.4f mm3" % (short, kname[:32], v))
    if not kres:
        print("  no seat mechanism touches any keep-out")

    # rear harness insertion corridor
    print("\n=== rear four-edge-harness insertion corridor (%.0f mm, PROVISIONAL) ===" % HARNESS_MM)
    hv = 0.0
    car = [v for k, v in ko.items() if "CARRIER" in k.upper() or "N1_N2" in k.upper()]
    for cs in car:
        for k in range(1, int(HARNESS_MM) + 1):
            moved = cs.moved(Location(Vector(*[float(x) for x in (L.DATUM_N * float(k))])))
            for short in names:
                for part in ("body", "terminals", "plate"):
                    hv += L.inter_vol(seats[short][part], moved)
    print("  total seat intrusion into the corridor = %.4f mm3" % hv)

    # classify
    print("\n=== classification ===")
    cls = {}
    for short in names:
        r = rows[short]
        tot = r["bodyShellInterferenceMm3"] + r["actuatorShellInterferenceMm3"]
        if tot < 1e-6 and r["terminalShellInterferenceMm3"] < 1e-6:
            c = "DIRECT ORIGINAL-SEAT REUSE"
        elif tot < 1e-6:
            c = "ORIGINAL-SEAT REUSE WITH LOCAL TRIM"
        else:
            c = "ORIGINAL-SEAT MECHANISM REQUIRES RECONSTRUCTION"
        cls[short] = c
        print("  %-5s %s" % (short, c))

    asm = Compound(children=[seats[s][k] for s in names
                             for k in ("body", "terminals", "actuator", "plate")],
                   label="ORIGINAL_SEAT_UNITS_AT_CURRENT_OPENINGS")
    export_step(asm, str(OUT / "H03_SEAT_UNITS_PLACED.step"))

    L.write_json(OUT / "h03_placement.json",
                 {"seatUnitLocalMm": {"plateTop": 0.0, "plateBottom": -PLATE_T,
                                      "bodyLo": BODY_LO, "bodyHi": BODY_HI,
                                      "bodyXY": BODY_XY, "pocketXY": POCKET_XY,
                                      "actuatorHi": ACT_HI, "actuatorDia": ACT_D,
                                      "terminalLo": TERM_LO, "terminalXY": list(TERM_XY),
                                      "capUndersideToPlateTop": CAP_TO_PLATE},
                  "buttons": rows, "neighbourPairs": pair, "keepOutHits": kres,
                  "harnessCorridorIntrusionMm3": hv, "classification": cls,
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
