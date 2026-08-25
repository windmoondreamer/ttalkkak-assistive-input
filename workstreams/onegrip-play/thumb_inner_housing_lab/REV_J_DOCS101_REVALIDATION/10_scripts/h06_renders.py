"""H06 - REV_H user-review renders (section 17)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
import labrender as R  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import true_axis  # noqa: E402
from d02_housing_vs_exact import BP_STEP, approved_shell  # noqa: E402
from h01_seat_audit import axis_frame  # noqa: E402

OUT = L.LAB / "08_renders"
OUTWARD = -L.DATUM_N
C_SHELL = (146, 176, 128)
C_PLATE = (232, 168, 74)
C_BODY = (96, 150, 226)
C_ACT = (226, 96, 86)
C_TERM = (240, 200, 80)
C_CAP = (56, 62, 72)
C_CAR = (120, 200, 160)
C_SZH = (170, 120, 220)
C_N12 = (96, 182, 220)
FOOT = ("Thumb Inner Housing Lab REV_H | seat-first | shell authority = exact Onshape "
        "THUMB_LOWER15_HOUSING_V1 | audit only")
FIT = np.asarray([[a, b, c] for a in (-26.0, 26.0) for b in (-52.0, 18.0)
                  for c in (-22.0, 22.0)], float)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fit = L.from_local(FIT)
    approved = approved_shell()
    Tap = L.triangles(approved, tol=0.08, ang=0.15)
    dx = Location(Vector(*[float(x) for x in L.THUMB_DELTA]))

    # ---- A : the ORIGINAL mechanism, sectioned --------------------------
    _, cartO = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    bp = import_step(str(BP_STEP))
    bp, _ = L.as_single_solid(bp, "BP")
    lab8 = next(k for k, v in NAME_MAP.items() if v == "T8")
    cap8, _ = L.as_single_solid(cartO[lab8], "T8")
    pb, _ = L.as_single_solid([v for k, v in cartO.items() if "PUSHBTN" in k.upper()][0], "PB")
    w8, _, _ = true_axis(cap8)
    c8 = L.surf_points(cap8, 40000, tol=0.04).mean(axis=0)
    ex8, ey8 = axis_frame(w8)
    Tbp = L.triangles(bp, tol=0.05, ang=0.10)
    Tc8 = L.triangles(cap8, tol=0.04, ang=0.09)
    Tpb = L.triangles(pb, tol=0.04, ang=0.09)
    R.render(OUT / "A_ORIGINAL_MECHANISM_section.png",
             [(R.clip_half(Tbp, c8, ey8), C_PLATE, 1.0, "ORIGINAL Backplate (2.003 mm)"),
              (R.clip_half(Tpb, c8, ey8), C_BODY, 1.0, "ORIGINAL PushBtn: body / actuator / terminals"),
              (R.clip_half(Tc8, c8, ey8), C_CAP, 1.0, "button cap")],
             tuple(-ey8), tuple(w8),
             "A - the ORIGINAL Thumb button mechanism, sectioned at T8",
             "cap underside -4.759 | body sits +0.051 on the plate | terminals 1.651 below it "
             "| actuator projects 1.909", FOOT,
             fit=L.from_local(np.asarray([[a, b, c] for a in (-14.0, 14.0)
                                          for b in (14.0, 30.0) for c in (8.0, 26.0)], float)))
    L.memory("render A")

    # ---- placed seats ---------------------------------------------------
    pl = json.loads((L.LAB / "03_placement" / "h03_placement.json").read_text(encoding="utf-8"))
    names = [s for s in ORDER if s != "JOY"]
    _, cartL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    from h03_placement import seat_solids
    seats, Tcaps = {}, []
    for short in names:
        r = pl["buttons"][short]
        w = np.asarray(r["axisWorld"], float)
        cu = np.asarray(r["capUndersideWorld"], float)
        seats[short] = seat_solids(cu, w, short)
        lab = next(k for k, v in NAME_MAP.items() if v == short)
        cp, _ = L.as_single_solid(cartL[lab], short)
        Tcaps.append(L.triangles(cp, tol=0.05, ang=0.10))
        del cp
    Tcap_all = np.concatenate(Tcaps)
    T_body = np.concatenate([L.triangles(seats[s]["body"], 0.05, 0.10) for s in names])
    T_act = np.concatenate([L.triangles(seats[s]["actuator"], 0.05, 0.10) for s in names])
    T_term = np.concatenate([L.triangles(seats[s]["terminals"], 0.05, 0.10) for s in names])
    L.memory("seat tris")

    car = import_step(str(L.LAB / "04_carrier" / "C05_SEAT_FIRST_CARRIER.step"))
    car, _ = L.as_single_solid(car, "C05")
    Tcar = L.triangles(car, tol=0.05, ang=0.10)

    keep = import_step(str(L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    Tszh_m, Tn12 = [], []
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if not ch.solids():
            continue
        if "MOVING" in lab:
            Tszh_m.append(L.triangles(ch, 0.10, 0.18))
        elif "CARRIER" in lab.upper() or "N1_N2" in lab.upper():
            Tn12.append(L.triangles(ch, 0.08, 0.15))
    Tszh_m = np.concatenate(Tszh_m) if Tszh_m else np.zeros((0, 3, 3))
    Tn12 = np.concatenate(Tn12) if Tn12 else np.zeros((0, 3, 3))

    # ---- B : one central, one edge, and the tightest button -------------
    for tag, short, note in (("B1_central_T2", "T2", "central Thumb button - DIRECT reuse, 70.0 % bearing"),
                             ("B2_edge_T1", "T1", "edge Thumb button - DIRECT reuse, 70.0 % bearing"),
                             ("B3_tightest_T7", "T7", "tightest button - seat lies inside the PROVISIONAL "
                              "SZH 25 deg moving envelope")):
        r = pl["buttons"][short]
        w = np.asarray(r["axisWorld"], float)
        cu = np.asarray(r["capUndersideWorld"], float)
        ex, ey = axis_frame(w)
        s = seats[short]
        layers = [(R.clip_half(Tap, cu, ey), C_SHELL, 1.0, "exact approved shell"),
                  (R.clip_half(Tcar, cu, ey), C_CAR, 1.0, "seat-first carrier"),
                  (R.clip_half(L.triangles(s["body"], 0.04, 0.09), cu, ey), C_BODY, 1.0, "switch body"),
                  (R.clip_half(L.triangles(s["actuator"], 0.04, 0.09), cu, ey), C_ACT, 1.0, "actuator"),
                  (R.clip_half(L.triangles(s["terminals"], 0.04, 0.09), cu, ey), C_TERM, 1.0, "terminals"),
                  (R.clip_half(Tcap_all, cu, ey), C_CAP, 1.0, "frozen caps")]
        if short == "T7":
            layers.append((R.clip_half(Tszh_m, cu, ey), C_SZH, 0.35,
                           "SZH 25 deg moving envelope (PROVISIONAL)"))
        layers = [x for x in layers if len(x[0])]
        R.render(OUT / ("B_%s.png" % tag), layers, tuple(-ey), tuple(w),
                 "B - CURRENT frozen %s + ORIGINAL-style seat" % short, note, FOOT, fit=fit)
        L.memory("render " + tag)

    # ---- C : the full array ---------------------------------------------
    R.render(OUT / "C_FULL_SEAT_ARRAY.png",
             [(Tap, C_SHELL, 0.26, "exact approved shell"),
              (Tcar, C_CAR, 1.0, "seat-first common carrier"),
              (T_body, C_BODY, 1.0, "8 switch bodies"),
              (T_act, C_ACT, 1.0, "8 actuators"),
              (T_term, C_TERM, 1.0, "terminal escape"),
              (Tcap_all, C_CAP, 1.0, "frozen caps")],
             tuple((L.DATUM_U * 0.45 + L.DATUM_V * -0.35 + OUTWARD * -0.82)), OUTWARD,
             "C - full T1-T8 ORIGINAL-style seat array behind the frozen openings",
             "6 of 8 seats DIRECT; T7 / T8 lost to the PROVISIONAL SZH moving envelope; "
             "carrier sits 7.63-12.70 mm below the shell", FOOT, fit=fit)

    # ---- D : N1/N2 ------------------------------------------------------
    R.render(OUT / "D_N1_N2_adjacent.png",
             [(Tap, C_SHELL, 0.26, "exact approved shell"),
              (Tcar, C_CAR, 1.0, "seat-first carrier"),
              (Tn12, C_N12, 1.0, "N1/N2 carrier + rear harness keep-out"),
              (T_term, C_TERM, 1.0, "terminal escape")],
             tuple((L.DATUM_U * -0.5 + OUTWARD * -0.85)), OUTWARD,
             "D - N1 / N2 adjacency and the rear four-edge-harness corridor",
             "carrier vs N1/N2 keep-out = 0.000000 mm3; 15 mm rear insertion corridor = "
             "0.000000 mm3", FOOT, fit=fit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
