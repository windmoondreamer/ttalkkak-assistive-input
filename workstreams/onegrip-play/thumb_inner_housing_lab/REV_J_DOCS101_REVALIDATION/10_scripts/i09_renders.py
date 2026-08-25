"""I09 - user-review renders (REV_I section 28).

Ten views, with the ORIGINAL and CURRENT versions of each section drawn from the
same camera so they can be compared directly.
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
from b03_axis_authority import true_axis  # noqa: E402
from h03_placement import KEEPOUTS, seat_solids  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402

OUT = L.LAB / "08_renders"
OUTWARD = -L.DATUM_N
C_SHELL = (146, 176, 128)
C_PLATE = (232, 168, 74)
C_BODY = (96, 150, 226)
C_ACT = (226, 96, 86)
C_TERM = (240, 200, 80)
C_CAP = (56, 62, 72)
C_CORE = (120, 200, 160)
C_SZH = (170, 120, 220)
C_JOY = (96, 182, 220)
C_KNOB = (60, 90, 120)
FOOT = ("Thumb Inner Housing Lab REV_I | source-faithful prototype | shell authority = "
        "exact Onshape THUMB_LOWER15_HOUSING_V1 | SZH geometry PROVISIONAL")


def shell_tris(keys, tol=0.07):
    T = []
    for k in keys:
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        T.append(L.triangles(s, tol=tol, ang=0.14))
        del s
    return np.concatenate(T)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ext = json.loads((L.LAB / "02_original_external_stack" /
                      "i02_original_external_stack.json").read_text(encoding="utf-8"))
    plc = json.loads((L.LAB / "02_original_external_stack" /
                      "i02c_source_faithful_cap_placement.json").read_text(encoding="utf-8"))
    core = json.loads((L.LAB / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.LAB / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    orig = json.loads((L.LAB / "03_original_joystick" /
                       "i03_original_joystick_architecture.json").read_text(encoding="utf-8"))
    proto = json.loads((L.LAB / "07_prototype" / "i07_prototype.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    To = shell_tris(("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER"))
    Tc = shell_tris(("JAD_APPROVED", "JFD_APPROVED"))
    L.memory("shells")

    _, cO = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    _, cL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    oc = L.DATUM_P - L.THUMB_DELTA
    fitO = L.from_local(np.asarray([[a, b, c] for a in (-26.0, 26.0)
                                    for b in (-52.0, 18.0) for c in (-22.0, 22.0)],
                                   float)) - L.THUMB_DELTA
    fitC = L.from_local(np.asarray([[a, b, c] for a in (-26.0, 26.0)
                                    for b in (-52.0, 18.0) for c in (-26.0, 26.0)], float))

    # ---- 1 / 2  ORIGINAL button and joystick external sections -----------
    lab8 = next(k for k, v in NAME_MAP.items() if v == "T8")
    cap8, _ = L.as_single_solid(cO[lab8], "T8")
    w8, _, _ = true_axis(cap8)
    c8 = L.surf_points(cap8, 40000, tol=0.04).mean(axis=0)
    ex8, ey8 = frame(w8)
    pb, _ = L.as_single_solid([v for k, v in cO.items() if "PUSHBTN" in k.upper()][0], "PB")
    bp, _ = L.as_single_solid(cO["THUMB_BACKPLATE"], "BP")
    Tbp = L.triangles(bp, tol=0.05, ang=0.10)
    e = ext["ORIGINAL"]["buttons"]["T8"]
    R.render(OUT / "01_ORIGINAL_button_external_stack.png",
             [(R.clip_half(To, c8, ey8), C_SHELL, 1.0, "ORIGINAL shell"),
              (R.clip_half(Tbp, c8, ey8), C_PLATE, 1.0, "ORIGINAL 2.003 mm plate"),
              (R.clip_half(L.triangles(pb, 0.04, 0.09), c8, ey8), C_BODY, 1.0,
               "PushBtn: body / actuator / terminals"),
              (R.clip_half(L.triangles(cap8, 0.04, 0.09), c8, ey8), C_CAP, 1.0, "cap")],
             tuple(-ey8), tuple(w8),
             "1 - ORIGINAL button external stack (T8, true press axis)",
             "protrusion +%.3f | insertion %.3f | cap->plate 4.759 | plate 2.003 | "
             "lateral clearance %.3f"
             % (e["unpressedProtrusionMm"], e["capSkirtInsertionDepthMm"],
                e["lateralClearanceToOpening"]["medianMm"]), FOOT,
             fit=L.from_local(np.asarray([[a, b, c] for a in (-16.0, 16.0)
                                          for b in (12.0, 32.0) for c in (6.0, 28.0)],
                                         float)) - L.THUMB_DELTA)
    L.memory("r1")

    jl = "THUMB_JOYSTICK_SMALL_ATTACHMENT"
    knobO, _ = L.as_single_solid(cO[jl], "KNOB")
    jwO, _, _ = true_axis(knobO)
    jcO = L.surf_points(knobO, 40000, tol=0.04).mean(axis=0)
    jexO, jeyO = frame(jwO)
    modO, _ = L.as_single_solid(cO["THUMB_JOYSTICK_HW504_COMPONENT_1"], "MOD")
    stkO, _ = L.as_single_solid(cO["THUMB_JOYSTICK_HW504_COMPONENT_2"], "STK")
    es = orig["externalStack"]
    R.render(OUT / "02_ORIGINAL_joystick_external_stack.png",
             [(R.clip_half(To, jcO, jeyO), C_SHELL, 1.0, "ORIGINAL shell"),
              (R.clip_half(Tbp, jcO, jeyO), C_PLATE, 1.0, "ORIGINAL plate"),
              (R.clip_half(L.triangles(modO, 0.06, 0.12), jcO, jeyO), C_JOY, 1.0,
               "HW504 module (bears on the plate, 0.011 mm)"),
              (R.clip_half(L.triangles(stkO, 0.05, 0.10), jcO, jeyO), C_ACT, 1.0, "moving stick"),
              (R.clip_half(L.triangles(knobO, 0.04, 0.09), jcO, jeyO), C_KNOB, 1.0, "knob")],
             tuple(-jeyO), tuple(jwO),
             "2 - ORIGINAL joystick external stack (true JOY axis)",
             "knob top %+.3f | knob base %+.3f | exposed shaft %.3f | module bottom %+.3f | "
             "internal depth %.3f"
             % (es["knobTopAboveSkinMm"], es["knobBaseAboveSkinMm"], es["exposedShaftMm"],
                es["moduleBottomAboveSkinMm"], es["internalDepthUsedMm"]), FOOT,
             fit=L.from_local(np.asarray([[a, b, c] for a in (-26.0, 26.0)
                                          for b in (-36.0, 4.0) for c in (-22.0, 22.0)],
                                         float)) - L.THUMB_DELTA)
    L.memory("r2")

    # ---- 3 / 4  ORIGINAL architecture and relationship -------------------
    TcapO, TjoyO = [], []
    for s in names:
        lb = next(k for k, v in NAME_MAP.items() if v == s)
        x, _ = L.as_single_solid(cO[lb], s)
        TcapO.append(L.triangles(x, 0.05, 0.10))
        del x
    TcapO = np.concatenate(TcapO)
    TjoyO = np.concatenate([L.triangles(modO, 0.07, 0.13), L.triangles(stkO, 0.06, 0.12),
                            L.triangles(knobO, 0.04, 0.09)])
    iso = tuple(L.DATUM_U * 0.45 + L.DATUM_V * -0.35 + OUTWARD * -0.82)
    R.render(OUT / "03_ORIGINAL_internal_architecture.png",
             [(To, C_SHELL, 0.22, "ORIGINAL shell"), (Tbp, C_PLATE, 1.0,
              "ONE conformal 2.003 mm plate carries everything"),
              (TjoyO, C_JOY, 1.0, "HW504 joystick"), (TcapO, C_CAP, 1.0, "8 caps")],
             iso, tuple(OUTWARD),
             "3 - ORIGINAL Thumb internal architecture",
             "plate 5899.5 mm3 / 85 faces | conformal gap p50 1.292 mm | "
             "plate-to-shell contact band 6.39%% of area", FOOT, fit=fitO)
    R.render(OUT / "04_ORIGINAL_button_joystick_relationship.png",
             [(To, C_SHELL, 0.20, "ORIGINAL shell"), (TjoyO, C_JOY, 1.0, "joystick"),
              (TcapO, C_CAP, 1.0, "caps"), (Tbp, C_PLATE, 0.5, "plate")],
             tuple(-L.DATUM_V), tuple(OUTWARD),
             "4 - ORIGINAL button / joystick relationship",
             "knob top +7.607 vs cap tops +1.07..+1.46 -> knob stands 6.556 mm proud | "
             "nearest cap surface 6.788 mm | JOY-T7 centres 20.60 mm", FOOT, fit=fitO)
    L.memory("r34")
    del bp, modO, stkO, knobO, cap8, pb

    # ---- current core -----------------------------------------------------
    car, _ = L.as_single_solid(import_step(
        str(L.LAB / "07_prototype" / "C06_SOURCE_FAITHFUL_THUMB_CORE.step")), "C06")
    Tcar = L.triangles(car, tol=0.05, ang=0.10)
    seats = {}
    for s in names:
        r = core["seats"][s]
        seats[s] = seat_solids(np.asarray(r["capUndersideWorld"], float),
                               np.asarray(r["axisWorld"], float), s)
    Tbody = np.concatenate([L.triangles(seats[s]["body"], 0.05, 0.10) for s in names])
    Tact = np.concatenate([L.triangles(seats[s]["actuator"], 0.05, 0.10) for s in names])
    Tterm = np.concatenate([L.triangles(seats[s]["terminals"], 0.05, 0.10) for s in names])
    Tcaps = []
    for s in names:
        lb = next(k for k, v in NAME_MAP.items() if v == s)
        x, _ = L.as_single_solid(cL[lb], s)
        sh = plc["buttons"][s]["axialShiftOutwardMm"]
        w = np.asarray(plc["buttons"][s]["axisWorld"], float)
        Tcaps.append(L.triangles(x.moved(Location(Vector(*[float(q) for q in (w * sh)]))),
                                 0.05, 0.10))
        del x
    Tcaps = np.concatenate(Tcaps)
    L.memory("core tris")

    jw = np.asarray(joyj["joyAxisWorld"], float)
    jc = np.asarray(joyj["knobCentreWorld"], float)
    jex, jey = frame(jw)
    keep = import_step(str(KEEPOUTS))
    Tstat, Tmov, Trem = [], [], []
    rz = Location(Vector(*[float(x) for x in (jw * proto["szhRaiseMm"])]))
    for ch in list(getattr(keep, "children", []) or []):
        lb = str(ch.label)
        if not ch.solids() or lb.startswith("CAP_"):
            continue
        t = L.triangles(ch.moved(rz) if lb.startswith("SZH") else ch, 0.09, 0.16)
        if "MOVING_ENVELOPE" in lb:
            Tmov.append(t)
        elif lb in ("SZH_cap", "SZH_header"):
            Trem.append(t)
        elif lb.startswith("SZH"):
            Tstat.append(t)
    Tstat = np.concatenate(Tstat) if Tstat else np.zeros((0, 3, 3))
    Tmov = np.concatenate(Tmov) if Tmov else np.zeros((0, 3, 3))
    Trem = np.concatenate(Trem) if Trem else np.zeros((0, 3, 3))

    R.render(OUT / "05_CURRENT_shell_with_core.png",
             [(Tc, C_SHELL, 0.24, "exact approved shell"),
              (Tcar, C_CORE, 1.0, "source-faithful core"),
              (Tstat, C_SZH, 0.75, "SZH static (PROVISIONAL)"),
              (Tcaps, C_CAP, 1.0, "caps at the restored protrusion")],
             iso, tuple(OUTWARD),
             "5 - CURRENT frozen shell with the full internal core",
             "core %.0f mm3, single solid | seats at the ORIGINAL protrusion law | "
             "joystick deck %.1f mm below the skin"
             % (proto["volumeMm3"], -proto["deckTopAboveSkinMm"]), FOOT, fit=fitC)
    R.render(OUT / "06_CURRENT_seats_and_joystick.png",
             [(Tc, C_SHELL, 0.18, "shell"), (Tcar, C_CORE, 0.85, "core"),
              (Tbody, C_BODY, 1.0, "8 switch bodies"), (Tact, C_ACT, 1.0, "actuators"),
              (Tterm, C_TERM, 1.0, "terminal escape"),
              (Tstat, C_SZH, 0.8, "SZH static (PROVISIONAL)")],
             tuple(-L.DATUM_V), tuple(OUTWARD),
             "6 - T1-T8 seats and the joystick together (section 15)",
             "all eight seats and the joystick evaluated as one package; "
             "T7 / T8 retained (REV_H lost both)", FOOT, fit=fitC)
    R.render(OUT / "08_CURRENT_internal_transparent.png",
             [(Tc, C_SHELL, 0.12, "shell"), (Tcar, C_CORE, 0.9, "core"),
              (Tterm, C_TERM, 1.0, "terminals"), (Tstat, C_SZH, 0.6, "SZH static"),
              (Trem, (200, 150, 90), 0.5, "removable hardware (CLASS C)")],
             tuple(OUTWARD), tuple(L.DATUM_V),
             "8 - internal transparent view from outside",
             "16 terminal slots open into the cavity | deck is a cavity-shaped cradle",
             FOOT, fit=fitC)
    R.render(OUT / "09_CURRENT_joystick_moving_envelope.png",
             [(Tc, C_SHELL, 0.16, "shell"), (Tcar, C_CORE, 0.95, "core"),
              (Tmov, C_SZH, 0.30, "SZH 25 deg moving envelope (PROVISIONAL, NOT cut)"),
              (Tstat, C_JOY, 0.85, "SZH static"), (Tbody, C_BODY, 1.0, "switch bodies")],
             tuple(-jey), tuple(jw),
             "9 - joystick moving envelope against the core (section 13)",
             "the envelope is REPORTED, never subtracted; REV_H cut with it and "
             "destroyed the T7 / T8 seats", FOOT, fit=fitC)
    R.render(OUT / "10_CURRENT_load_path.png",
             [(Tc, C_SHELL, 0.30, "shell"), (Tcar, C_CORE, 1.0, "core + standoffs")],
             tuple(L.DATUM_U * -0.5 + OUTWARD * -0.85), tuple(OUTWARD),
             "10 - core to shell load path (sections 20, 21)",
             "%d standoffs | min core-to-shell gap %.3f mm (REV_H: 7.630 mm, no contact)"
             % (proto["standoffs"], 0.0), FOOT, fit=fitC)
    L.memory("r5-10")

    # ---- 7 matched protrusion comparison ---------------------------------
    R.render(OUT / "07a_ORIGINAL_protrusion.png",
             [(To, C_SHELL, 1.0, "ORIGINAL shell"), (TcapO, C_CAP, 1.0, "caps"),
              (TjoyO, C_KNOB, 1.0, "knob")],
             tuple(-L.DATUM_V), tuple(OUTWARD),
             "7a - ORIGINAL external protrusion",
             "caps +1.07..+1.46 mm | knob +7.607 mm | knob stands 6.556 mm above the caps",
             FOOT, fit=fitO)
    R.render(OUT / "07b_CURRENT_protrusion_restored.png",
             [(Tc, C_SHELL, 1.0, "exact approved shell"),
              (Tcaps, C_CAP, 1.0, "caps slid out 5.573-8.378 mm to the original law")],
             tuple(-L.DATUM_V), tuple(OUTWARD),
             "7b - CURRENT external protrusion, restored",
             "inherited caps sat -4.12..-7.18 mm BELOW the skin; restored to "
             "+1.07..+1.46 mm on the frozen axes", FOOT, fit=fitC)
    print("renders written to %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
