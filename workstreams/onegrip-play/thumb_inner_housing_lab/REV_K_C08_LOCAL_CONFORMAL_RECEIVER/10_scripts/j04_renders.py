"""J04 - docs/101 x C07 revalidation renders (section 20).

Ten views, all measurement-driven: no decorative angles.
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
from h03_placement import seat_solids  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402
from j02_collision import switch_groups  # noqa: E402

OUT = L.LAB / "08_renders"
CAND = L.REV_I / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step"
C_JAD = (150, 178, 132)
C_JFD = (126, 158, 176)
C_CORE = (120, 200, 160)
C_SW = (226, 110, 90)
C_ACT = (250, 180, 60)
C_TERM = (240, 210, 100)
C_POCK = (200, 120, 220)
C_CAP = (56, 62, 72)
C_SZH = (170, 120, 220)
C_BODY = (96, 150, 226)
FOOT = ("Thumb Inner Housing Lab REV_J | docs/101 x C07 revalidation | "
        "transform = IDENTITY | measurement only, no geometry changed")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core_j = json.loads((L.REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    plc = json.loads((L.REV_I / "02_original_external_stack" /
                      "i02c_source_faithful_cap_placement.json").read_text(encoding="utf-8"))
    c07j = json.loads((L.REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    col = json.loads((L.LAB / "03_collision" / "j02_collision.json").read_text(encoding="utf-8"))
    dat = json.loads((L.ROOT / "build123d_workbench/out/lower15_true_bare_finger_base"
                      / "finger_button_frozen_datums.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    core, _ = L.as_single_solid(import_step(str(CAND)), "C07")
    Tcore = L.triangles(core, tol=0.04, ang=0.09)
    Tjad, _ = L.as_single_solid(import_step(L.SRC["D101_JAD"]), "JaD")
    Tjfd, _ = L.as_single_solid(import_step(L.SRC["D101_JFD"]), "JfD")
    TA = L.triangles(Tjad, tol=0.07, ang=0.14)
    TB = L.triangles(Tjfd, tol=0.07, ang=0.14)
    del Tjad, Tjfd
    L.memory("shells")

    groups = switch_groups()
    Tsw, Tac, Ttm = [], [], []
    for b, g in groups.items():
        Tsw.append(L.triangles(g["BODY"][0], 0.04, 0.09))
        Tac.append(L.triangles(g["ACTUATOR"][0], 0.03, 0.08))
        for t in g["TERMINAL"]:
            Ttm.append(L.triangles(t, 0.03, 0.08))
    Tsw, Tac, Ttm = np.concatenate(Tsw), np.concatenate(Tac), np.concatenate(Ttm)
    pockets, _ = L.as_single_solid(import_step(
        str(L.LAB / "03_collision" / "J02_FINGER_POCKET_ENVELOPES.step")), "POCK") \
        if (L.LAB / "03_collision" / "J02_FINGER_POCKET_ENVELOPES.step").exists() else (None, None)
    Tpk = L.triangles(pockets, 0.05, 0.10) if pockets is not None else np.zeros((0, 3, 3))
    L.memory("switches")

    seats = {}
    for s in names:
        r = core_j["seats"][s]
        seats[s] = seat_solids(np.asarray(r["capUndersideWorld"], float),
                               np.asarray(r["axisWorld"], float), s)
    Tbody = np.concatenate([L.triangles(seats[s]["body"], 0.05, 0.10) for s in names])
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

    jw = L.unit(np.asarray(joyj["joyAxisWorld"], float))
    jc = np.asarray(joyj["knobCentreWorld"], float)
    jex, jey = frame(jw)
    keep = import_step(str(L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    rz = Location(Vector(*[float(x) for x in (jw * c07j["szhRaiseMm"])]))
    Tszh = []
    for ch in list(getattr(keep, "children", []) or []):
        lb = str(ch.label)
        if ch.solids() and lb.startswith("SZH") and "MOVING" not in lb and lb not in (
                "SZH_cap", "SZH_header"):
            Tszh.append(L.triangles(ch.moved(rz), 0.09, 0.16))
    Tszh = np.concatenate(Tszh) if Tszh else np.zeros((0, 3, 3))
    L.memory("thumb parts")

    fit = L.from_local(np.asarray([[a, b, c] for a in (-34.0, 34.0)
                                   for b in (-58.0, 24.0) for c in (-34.0, 30.0)], float))
    iso = tuple(L.DATUM_U * 0.45 + L.DATUM_V * -0.35 + jw * -0.82)
    mn = col["minFingerClearanceMm"]

    R.render(OUT / "01_docs101_shell_with_C07.png",
             [(TA, C_JAD, 0.22, "docs/101 JaD"), (TB, C_JFD, 0.22, "docs/101 JfD"),
              (Tcore, C_CORE, 1.0, "C07 Thumb core"), (Tcaps, C_CAP, 1.0, "Thumb caps")],
             iso, tuple(jw),
             "1 - docs/101 frozen Finger shell with the C07 Thumb core in place",
             "transform IDENTITY | shell interference 0.000000 mm3 both halves | "
             "min gap 0.111 mm", FOOT, fit=fit)
    R.render(OUT / "02_interior_overview.png",
             [(TA, C_JAD, 0.10, "JaD"), (TB, C_JFD, 0.10, "JfD"),
              (Tcore, C_CORE, 1.0, "C07 core"), (Tsw, C_SW, 1.0, "8 Finger switches"),
              (Tszh, C_SZH, 0.8, "SZH static (PROVISIONAL)")],
             tuple(-L.DATUM_V), tuple(jw),
             "2 - interior overview, both subsystems together",
             "Finger switches direct-embedded per docs/101; Thumb core per REV_I/C07",
             FOOT, fit=fit)
    R.render(OUT / "03_core_and_pockets.png",
             [(TA, C_JAD, 0.08, "JaD"), (TB, C_JFD, 0.08, "JfD"),
              (Tcore, C_CORE, 1.0, "C07 core"),
              (Tpk, C_POCK, 0.55, "8 docs/101 pocket envelopes (body + 0.2 mm/side)")],
             iso, tuple(jw),
             "3 - C07 core against all 8 docs/101 Finger pocket envelopes",
             "core n pocket = 0.0000 mm3 on every button", FOOT, fit=fit)
    R.render(OUT / "04_core_and_actual_switches.png",
             [(Tcore, C_CORE, 1.0, "C07 core"), (Tsw, C_SW, 1.0, "switch bodies"),
              (Tac, C_ACT, 1.0, "actuators"), (Ttm, C_TERM, 1.0, "terminals")],
             iso, tuple(jw),
             "4 - C07 core against the actual detailed Finger switches",
             "body / actuator / terminals all 0.0000 mm3; minimum clearance %.4f mm" % mn,
             FOOT, fit=fit)
    L.memory("r1-4")

    # closest interface: N1
    n1c = np.asarray(dat["controls"]["N1"]["centerMm"], float)
    n1a = L.unit(np.asarray(dat["controls"]["N1"]["pressAxis"], float))
    ex1, ey1 = frame(n1a)
    fitN = np.asarray([n1c + ex1 * a + ey1 * b + n1a * c
                       for a in (-18.0, 18.0) for b in (-18.0, 18.0)
                       for c in (-20.0, 12.0)])
    R.render(OUT / "05_closest_interface_N1.png",
             [(R.clip_half(TA, n1c, ey1), C_JAD, 0.9, "JaD"),
              (R.clip_half(TB, n1c, ey1), C_JFD, 0.9, "JfD"),
              (R.clip_half(Tcore, n1c, ey1), C_CORE, 1.0, "C07 core"),
              (R.clip_half(Tsw, n1c, ey1), C_SW, 1.0, "switch bodies"),
              (R.clip_half(Ttm, n1c, ey1), C_TERM, 1.0, "terminals")],
             tuple(-ey1), tuple(n1a),
             "5 - tightest Finger/Thumb interface: N1, sectioned on its press axis",
             "minimum clearance %.4f mm, no contact | the 12 mm withdrawal corridor "
             "behind N1 is what the core occupies" % mn, FOOT, fit=fitN)
    n2c = np.asarray(dat["controls"]["N2"]["centerMm"], float)
    R.render(OUT / "06_N1_N2_region.png",
             [(TA, C_JAD, 0.12, "JaD"), (TB, C_JFD, 0.12, "JfD"),
              (Tcore, C_CORE, 1.0, "C07 core"), (Tsw, C_SW, 1.0, "switch bodies"),
              (Ttm, C_TERM, 1.0, "terminals")],
             tuple(L.unit(n1c - 0.5 * (n1c + n2c) + jw * -1.2)), tuple(jw),
             "6 - N1 / N2 region, the only two buttons with any flag",
             "N1 clearance %.4f mm, N2 %.4f mm | both static values are POSITIVE; "
             "the flag is the service corridor" % (col["fingers"]["N1"]["minClearanceMm"],
                                                   col["fingers"]["N2"]["minClearanceMm"]),
             FOOT, fit=np.asarray([n1c + jex * a + jey * b + jw * c
                                   for a in (-26.0, 26.0) for b in (-26.0, 26.0)
                                   for c in (-26.0, 16.0)]))
    L.memory("r5-6")

    R.render(OUT / "07_JOY_deck.png",
             [(TA, C_JAD, 0.14, "JaD"), (TB, C_JFD, 0.14, "JfD"),
              (Tcore, C_CORE, 1.0, "C07 core and deck"),
              (Tszh, C_SZH, 0.85, "SZH static (PROVISIONAL)")],
             tuple(-jey), tuple(jw),
             "7 - joystick holder / deck against docs/101",
             "deck %.1f mm below the skin, cavity-shaped r %.1f-%.1f mm | "
             "JOY column open through docs/101"
             % (-c07j["deckTopAboveSkinMm"], c07j["deckCavityRadiusMm"]["min"],
                c07j["deckCavityRadiusMm"]["max"]), FOOT,
             fit=np.asarray([jc + jex * a + jey * b + jw * c
                             for a in (-30.0, 30.0) for b in (-30.0, 30.0)
                             for c in (-30.0, 14.0)]))
    R.render(OUT / "08_T1_T8_carrier.png",
             [(TA, C_JAD, 0.10, "JaD"), (TB, C_JFD, 0.10, "JfD"),
              (Tcore, C_CORE, 0.92, "C07 carrier"),
              (Tbody, C_BODY, 1.0, "8 Thumb switch bodies"),
              (Tterm, C_TERM, 1.0, "Thumb terminal escape"),
              (Tcaps, C_CAP, 1.0, "caps at the restored protrusion")],
             tuple(-L.DATUM_V), tuple(jw),
             "8 - Thumb T1-T8 carrier inside the docs/101 shell",
             "8/8 seats bearing, 16/16 terminal slots open, protrusion law preserved",
             FOOT, fit=fit)
    R.render(OUT / "09_JaD_JfD_closure.png",
             [(TA, C_JAD, 0.85, "docs/101 JaD"), (TB, C_JFD, 0.45, "docs/101 JfD"),
              (Tcore, C_CORE, 1.0, "C07 core"), (Tsw, C_SW, 0.9, "Finger switches")],
             tuple(L.DATUM_U), tuple(jw),
             "9 - JaD / JfD closure with both subsystems installed",
             "core n JaD = 0.000000 | core n JfD = 0.000000 mm3", FOOT, fit=fit)
    R.render(OUT / "10_N1_service_corridor.png",
             [(R.clip_half(TA, n1c, ey1), C_JAD, 0.35, "JaD"),
              (R.clip_half(Tcore, n1c, ey1), C_CORE, 1.0, "C07 core"),
              (R.clip_half(Tsw, n1c, ey1), C_SW, 1.0, "switch body"),
              (R.clip_half(Ttm, n1c, ey1), C_TERM, 1.0, "terminals")],
             tuple(-ey1), tuple(n1a),
             "10 - the only finding: N1 / N2 withdrawal corridor",
             "static clearance is positive everywhere; the core occupies the space a "
             "switch would need to be pulled BACK into, so Finger switches go in first",
             FOOT, fit=fitN)
    print("renders written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
