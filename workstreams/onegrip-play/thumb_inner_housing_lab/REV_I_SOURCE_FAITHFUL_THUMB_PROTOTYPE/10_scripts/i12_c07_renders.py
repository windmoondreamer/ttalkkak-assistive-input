"""I12 - C07 manufacturability renders (REV_I FDM cleanup).

Four views aimed at print review rather than at geometry review:
    11  C06 and C07 from the same camera, to show what the rebuild removed
    12  C07 in the print orientation, looking along the bed
    13  C07 sectioned through the seat row, showing slab thickness
    14  C07 with the switches, caps and joystick in place
"""
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
from h03_placement import KEEPOUTS, seat_solids  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402

OUT = L.LAB / "08_renders"
C_SHELL = (146, 176, 128)
C_C06 = (196, 150, 120)
C_C07 = (120, 200, 160)
C_BODY = (96, 150, 226)
C_ACT = (226, 96, 86)
C_TERM = (240, 200, 80)
C_CAP = (56, 62, 72)
C_SZH = (170, 120, 220)
FOOT = ("Thumb Inner Housing Lab REV_I | C07 FDM refine | PRINT_UP = JOY axis outward | "
        "SZH geometry PROVISIONAL")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core = json.loads((L.LAB / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joy = json.loads((L.LAB / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    plc = json.loads((L.LAB / "02_original_external_stack" /
                      "i02c_source_faithful_cap_placement.json").read_text(encoding="utf-8"))
    c07 = json.loads((L.LAB / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    Tsh = []
    for k in ("JAD_APPROVED", "JFD_APPROVED"):
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        Tsh.append(L.triangles(s, tol=0.07, ang=0.14))
        del s
    Tsh = np.concatenate(Tsh)

    T = {}
    for tag, fn in (("C06", "C06_SOURCE_FAITHFUL_THUMB_CORE.step"),
                    ("C07", "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step")):
        s, _ = L.as_single_solid(import_step(str(L.LAB / "07_prototype" / fn)), tag)
        T[tag] = L.triangles(s, tol=0.04, ang=0.09)
        del s
    L.memory("load")

    jw = L.unit(np.asarray(joy["joyAxisWorld"], float))
    jc = np.asarray(joy["knobCentreWorld"], float)
    jex, jey = frame(jw)
    fit = L.from_local(np.asarray([[a, b, c] for a in (-26.0, 26.0)
                                   for b in (-52.0, 18.0) for c in (-30.0, 26.0)], float))
    iso = tuple(L.DATUM_U * 0.45 + L.DATUM_V * -0.35 + jw * -0.82)

    R.render(OUT / "11a_C06_before.png",
             [(Tsh, C_SHELL, 0.18, "exact approved shell"),
              (T["C06"], C_C06, 1.0, "C06: 8 tilted tiles, 20 tilted webs, 5 inclined links")],
             iso, tuple(jw),
             "11a - C06 before the FDM rebuild",
             "542 faces | 27.36 mm2 below 1.20 mm | thickness p50 2.500 mm | "
             "support on 12 critical-interface faces", FOOT, fit=fit)
    R.render(OUT / "11b_C07_after.png",
             [(Tsh, C_SHELL, 0.18, "exact approved shell"),
              (T["C07"], C_C07, 1.0, "C07: one slab, vertical walls, cavity deck")],
             iso, tuple(jw),
             "11b - C07 after the FDM rebuild",
             "%d faces | 0.00 mm2 below 1.20 mm | thickness p50 3.000 mm | "
             "support on 0 critical-interface faces" % c07["faces"], FOOT, fit=fit)
    L.memory("r11")

    # 12: print orientation, viewed along the bed
    bed = c07["bedHeightZ"]
    R.render(OUT / "12_C07_print_orientation.png",
             [(T["C07"], C_C07, 1.0, "C07 as printed")],
             tuple(jex), tuple(jw),
             "12 - C07 in the print orientation, PRINT_UP = JOY axis outward",
             "bed at the joystick deck underside | every side wall is parallel to "
             "PRINT_UP | seat faces point up", FOOT, fit=fit,
             world_lines=[(jc + jw * bed + jex * -40 + jey * -40,
                           jc + jw * bed + jex * 40 + jey * -40,
                           (40, 40, 40, 255), 3, "BED"),
                          (jc + jw * bed + jex * -40 + jey * 40,
                           jc + jw * bed + jex * 40 + jey * 40,
                           (40, 40, 40, 255), 3, None)])
    L.memory("r12")

    # 13: section through the seat row
    seats = {}
    for s in names:
        r = core["seats"][s]
        seats[s] = seat_solids(np.asarray(r["capUndersideWorld"], float),
                               np.asarray(r["axisWorld"], float), s)
    cut_pt = np.asarray(core["seats"]["T2"]["plateTopWorld"], float)
    nrm = L.unit(np.cross(jw, np.asarray(core["seats"]["T7"]["plateTopWorld"], float)
                          - np.asarray(core["seats"]["T2"]["plateTopWorld"], float)))
    R.render(OUT / "13_C07_section_slab.png",
             [(R.clip_half(Tsh, cut_pt, nrm), C_SHELL, 1.0, "shell"),
              (R.clip_half(T["C07"], cut_pt, nrm), C_C07, 1.0, "C07 slab and deck")],
             tuple(-nrm), tuple(jw),
             "13 - C07 sectioned along the seat row",
             "flat slab bottom, faceted top on the eight seat planes; "
             "thickness %.2f-%.2f mm" % tuple(c07["slabThicknessMm"]), FOOT, fit=fit)
    L.memory("r13")

    # 14: everything installed
    Tbody = np.concatenate([L.triangles(seats[s]["body"], 0.05, 0.10) for s in names])
    Tact = np.concatenate([L.triangles(seats[s]["actuator"], 0.05, 0.10) for s in names])
    Tterm = np.concatenate([L.triangles(seats[s]["terminals"], 0.05, 0.10) for s in names])
    _, cL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    Tcaps = []
    for s in names:
        lb = next(k for k, v in NAME_MAP.items() if v == s)
        x, _ = L.as_single_solid(cL[lb], s)
        b = plc["buttons"][s]
        Tcaps.append(L.triangles(x.moved(Location(Vector(
            *[float(q) for q in (np.asarray(b["axisWorld"], float)
                                 * b["axialShiftOutwardMm"])]))), 0.05, 0.10))
        del x
    Tcaps = np.concatenate(Tcaps)
    keep = import_step(str(KEEPOUTS))
    rz = Location(Vector(*[float(x) for x in (jw * c07["szhRaiseMm"])]))
    Tstat = []
    for ch in list(getattr(keep, "children", []) or []):
        lb = str(ch.label)
        if ch.solids() and lb.startswith("SZH") and "MOVING" not in lb and lb not in (
                "SZH_cap", "SZH_header"):
            Tstat.append(L.triangles(ch.moved(rz), 0.09, 0.16))
    Tstat = np.concatenate(Tstat) if Tstat else np.zeros((0, 3, 3))
    R.render(OUT / "14_C07_assembled.png",
             [(Tsh, C_SHELL, 0.16, "shell"), (T["C07"], C_C07, 0.95, "C07 core"),
              (Tbody, C_BODY, 1.0, "8 switch bodies"), (Tact, C_ACT, 1.0, "actuators"),
              (Tterm, C_TERM, 1.0, "terminal escape"),
              (Tstat, C_SZH, 0.8, "SZH static (PROVISIONAL)"),
              (Tcaps, C_CAP, 1.0, "caps at the restored protrusion")],
             tuple(-L.DATUM_V), tuple(jw),
             "14 - C07 with switches, caps and joystick installed",
             "all eight seats bearing, 16 of 16 terminal slots open, "
             "joystick deck %.1f mm below the skin" % -c07["deckTopAboveSkinMm"],
             FOOT, fit=fit)
    print("C07 renders written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
