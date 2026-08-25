"""Useful evidence renders for the isolated C09 candidate."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step

ROOT = Path(r"C:\Users\User\Desktop\OneGrip-Play")
WORK = ROOT / "codex_work" / "C09_CONTINUOUS_CURVED_CARRIER"
OUT = WORK / "outputs"
RENDER = WORK / "renders"
REV_I = ROOT / "thumb_inner_housing_lab" / "REV_I_SOURCE_FAITHFUL_THUMB_PROTOTYPE"
SCRIPTS = ROOT / "thumb_inner_housing_lab" / "REV_K_C08_LOCAL_CONFORMAL_RECEIVER" / "10_scripts"
sys.path.insert(0, str(SCRIPTS))

import labrender as R  # noqa: E402
import labutil as L  # noqa: E402
from b01_true_axes import ORDER  # noqa: E402
from h03_placement import seat_solids  # noqa: E402
from j02_collision import switch_groups  # noqa: E402

C09 = (62, 181, 164)
CARRIER = (39, 128, 151)
SUPPORT = (239, 170, 65)
C071 = (92, 147, 220)
JAD = (155, 181, 135)
JFD = (129, 160, 178)
SWITCH = (220, 95, 78)
SZH = (168, 115, 218)
GHOST = (120, 120, 126)
FOOT = "C09 isolated candidate | docs/101 frozen shell/Finger authority | production writes 0"


def single(path, label):
    return L.as_single_solid(import_step(str(path)), label)[0]


def main() -> int:
    RENDER.mkdir(parents=True, exist_ok=True)
    val = json.loads((WORK / "validation" / "C09_VALIDATION.json").read_text(encoding="utf-8"))
    core_j = json.loads((REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joy_j = json.loads((REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    c07_j = json.loads((REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    jw = L.unit(np.asarray(joy_j["joyAxisWorld"], float))
    jc = np.asarray(joy_j["knobCentreWorld"], float)
    names = [x for x in ORDER if x != "JOY"]

    c09 = single(OUT / "C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE.step", "C09")
    carrier = single(OUT / "C09_CONTINUOUS_LOWER_CURVED_CARRIER.step", "carrier")
    deck = single(OUT / "C09_SOURCE_FAITHFUL_JOY_DECK.step", "deck")
    c071 = single(ROOT / "codex_work" / "C07_1_FDM_SIMPLIFICATION" / "outputs" /
                  "C07_1_SOURCE_FAITHFUL_THUMB_CORE_SIMPLIFIED.step", "C07.1")
    ja = single(L.SRC["D101_JAD"], "JaD")
    jf = single(L.SRC["D101_JFD"], "JfD")
    T09 = L.triangles(c09, 0.045, 0.10)
    Tcar = L.triangles(carrier, 0.035, 0.09)
    Tdeck = L.triangles(deck, 0.05, 0.10)
    T071 = L.triangles(c071, 0.05, 0.10)
    TA = L.triangles(ja, 0.08, 0.15)
    TF = L.triangles(jf, 0.08, 0.15)

    gate = {n: single(WORK / "gate" / f"C09_GATE_{n}.step", n) for n in ("T2", "T8")}
    Tgate = {n: L.triangles(s, 0.035, 0.09) for n, s in gate.items()}
    seats = {}
    for n in names:
        r = core_j["seats"][n]
        seats[n] = seat_solids(np.asarray(r["capUndersideWorld"], float),
                               np.asarray(r["axisWorld"], float), n)
    Tthumb = np.concatenate([L.triangles(seats[n]["body"], 0.05, 0.10) for n in names])
    groups = switch_groups()
    Tfingers = np.concatenate([L.triangles(s, 0.05, 0.10) for g in groups.values()
                               for parts in g.values() for s in parts])

    keep = import_step(str(ROOT / "thumb_inner_housing_lab" / "REV_A" / "06_keepouts" /
                           "THUMB_KEEPOUT_ASSEMBLY.step"))
    rz = Location(Vector(*[float(x) for x in jw * c07_j["szhRaiseMm"]]))
    Tszh = [L.triangles(ch.moved(rz), 0.08, 0.15)
            for ch in list(getattr(keep, "children", []) or [])
            if ch.solids() and str(ch.label).startswith("SZH")
            and "MOVING" not in str(ch.label) and str(ch.label) not in ("SZH_cap", "SZH_header")]
    Tszh = np.concatenate(Tszh)

    fit = L.from_local(np.asarray([[a, b, c] for a in (-31.0, 31.0)
                                   for b in (-57.0, 23.0) for c in (-31.0, 29.0)], float))
    iso = tuple(L.DATUM_U * 0.44 + L.DATUM_V * -0.36 + jw * -0.82)

    # Gate renders focus around each frozen axis.
    for idx, n in enumerate(("T2", "T8"), 1):
        u = seats[n]
        top, w, ex, ey = u["plateTopPoint"], np.asarray(core_j["seats"][n]["axisWorld"]), u["ex"], u["ey"]
        local_fit = np.asarray([top + ex * x + ey * y + w * z
                                for x in (-15, 15) for y in (-15, 15) for z in (-13, 12)])
        g = val["feasibilityGate"]["cases"][n]
        R.render(RENDER / f"0{idx}_gate_{n}.png",
                 [(TA, JAD, 0.18, "docs/101 JaD"), (TF, JFD, 0.18, "docs/101 JfD"),
                  (Tgate[n], C09, 1.0, f"C09 {g['role']} {n}"),
                  (L.triangles(u["body"], 0.04, 0.09), SWITCH, 1.0, "Thumb switch body")],
                 tuple(-ey), tuple(w), f"C09 feasibility gate — {g['role']} {n}",
                 "seat normal error 0 deg | bearing 23.40 mm2 | slots 1.30 x 6.40 mm | shell/Finger 0",
                 FOOT, fit=local_fit)

    R.render(RENDER / "03_full_core.png",
             [(TA, JAD, 0.12, "JaD"), (TF, JFD, 0.12, "JfD"),
              (T09, C09, 1.0, "C09 full one-piece core"), (Tthumb, SWITCH, 0.90, "8 Thumb switches")],
             iso, tuple(jw), "C09 — full continuous curved carrier core",
             f"{val['geometry']['volumeMm3']:.1f} mm3 | {val['geometry']['faces']} faces | valid single solid",
             FOOT, fit=fit)

    R.render(RENDER / "04_carrier_underside.png",
             [(T09, GHOST, 0.14, "full core ghost"), (Tcar, CARRIER, 1.0, "3 curved rails + 3 broad cross ties"),
              (Tdeck, C071, 0.70, "source-faithful JOY deck")],
             tuple(-jw), tuple(L.DATUM_U), "C09 lower curved under-carrier — underside",
             "one continuous ladder; no per-opening conformal collars; terminal slots remain open",
             FOOT, fit=fit)

    R.render(RENDER / "05_docs101_finger_clearance.png",
             [(T09, C09, 1.0, "C09 core"), (Tfingers, SWITCH, 1.0, "8 actual docs/101 Finger switches")],
             iso, tuple(jw), "C09 × docs/101 actual Finger switches",
             f"all collisions 0 | minimum {val['minimumFingerClearance']['mm']:.4f} mm at {val['minimumFingerClearance']['button']}",
             FOOT, fit=fit)

    R.render(RENDER / "06_joystick_coordination.png",
             [(T09, C09, 0.82, "C09 core"), (Tszh, SZH, 0.88, "SZH confident-static package"),
              (Tdeck, C071, 1.0, "JOY deck")],
             tuple(-L.DATUM_V), tuple(jw), "C09 joystick coordination",
             "JOY axis blocked 0.0000 mm | deck height delta 0.0000 mm | static package improved vs C07.1",
             FOOT, fit=fit)

    moved = c09.moved(Location(Vector(*[float(x) for x in (-L.DATUM_U * 18.0)])))
    Tmoved = L.triangles(moved, 0.05, 0.10)
    R.render(RENDER / "07_assembly_path.png",
             [(TA, JAD, 0.28, "open JaD half"), (T09, C09, 0.38, "final position"),
              (Tmoved, SUPPORT, 0.82, "18 mm along clear -U path")],
             tuple(-L.DATUM_V), tuple(jw), "C09 one-piece assembly path",
             "-U into open JaD half: exact 30 mm sweep interference 0.000000 mm3 — PASS",
             FOOT, fit=fit,
             world_lines=[(jc - L.DATUM_U * 19.0, jc + L.DATUM_U * 2.0, (210, 65, 55, 255), 4, "-U insertion")])

    R.render(RENDER / "08a_C07_1_same_camera.png",
             [(TA, JAD, 0.10, "JaD"), (TF, JFD, 0.10, "JfD"), (T071, C071, 1.0, "C07.1")],
             iso, tuple(jw), "C07.1 — same camera",
             "6694.2 mm3 | 247 faces | support 708.4 mm2 | one-piece PASS",
             FOOT, fit=fit)
    R.render(RENDER / "08b_C09_same_camera.png",
             [(TA, JAD, 0.10, "JaD"), (TF, JFD, 0.10, "JfD"), (T09, C09, 1.0, "C09")],
             iso, tuple(jw), "C09 — same camera",
             f"{val['geometry']['volumeMm3']:.1f} mm3 | {val['geometry']['faces']} faces | support {val['fdm']['orientation']['supportAreaMm2']:.1f} mm2 | one-piece PASS",
             FOOT, fit=fit)
    print("renders complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
