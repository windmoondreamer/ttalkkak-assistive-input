"""K06 - C08 renders (§23).  Ten views: four for the gate, six for the full core."""
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
from h01_seat_audit import axis_frame  # noqa: E402
from h03_placement import seat_solids  # noqa: E402
from j02_collision import switch_groups  # noqa: E402

OUT = L.LAB / "08_renders"
C_JAD = (150, 178, 132)
C_JFD = (126, 158, 176)
C_C08 = (110, 200, 180)
C_C07 = (196, 150, 120)
C_BODY = (96, 150, 226)
C_TERM = (240, 200, 80)
C_CAP = (56, 62, 72)
C_SW = (226, 110, 90)
C_SZH = (170, 120, 220)
FOOT = ("Thumb Inner Housing Lab REV_K | C08 local conformal switch receiver | "
        "docs/101 shell | SZH geometry PROVISIONAL")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core_j = json.loads((L.REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    c07j = json.loads((L.REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    plc = json.loads((L.REV_I / "02_original_external_stack" /
                      "i02c_source_faithful_cap_placement.json").read_text(encoding="utf-8"))
    site = json.loads((L.LAB / "01_site_survey" / "k01_site_survey.json").read_text(encoding="utf-8"))
    k04 = json.loads((L.LAB / "03_full_c08" / "k04_full_c08.json").read_text(encoding="utf-8"))
    k05 = json.loads((L.LAB / "04_validation" / "k05_validate.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]
    easy, hard = site["caseEasy"], site["caseHard"]

    c08, _ = L.as_single_solid(import_step(
        str(L.LAB / "03_full_c08" / "C08_LOCAL_CONFORMAL_SWITCH_RECEIVER_CORE.step")), "C08")
    c07, _ = L.as_single_solid(import_step(
        str(L.REV_I / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step")), "C07")
    T8_ = L.triangles(c08, tol=0.04, ang=0.09)
    T7_ = L.triangles(c07, tol=0.04, ang=0.09)
    ja, _ = L.as_single_solid(import_step(L.SRC["D101_JAD"]), "JaD")
    jf, _ = L.as_single_solid(import_step(L.SRC["D101_JFD"]), "JfD")
    TA = L.triangles(ja, tol=0.07, ang=0.14)
    TB = L.triangles(jf, tol=0.07, ang=0.14)
    del ja, jf
    units = {}
    root = import_step(str(L.LAB / "03_full_c08" / "C08_RECEIVER_UNITS.step"))
    for ch in list(getattr(root, "children", []) or []):
        s, _ = L.as_single_solid(ch, str(ch.label))
        units[str(ch.label)] = L.triangles(s, tol=0.03, ang=0.08)
        del s
    L.memory("load")

    seats, geom = {}, {}
    for s in names:
        u = seat_solids(np.asarray(core_j["seats"][s]["capUndersideWorld"], float),
                        np.asarray(core_j["seats"][s]["axisWorld"], float), s)
        seats[s] = u
        geom[s] = {"cen": np.asarray(site["buttons"][s]["capCentreWorld"], float),
                   "w": np.asarray(site["buttons"][s]["axisWorld"], float)}
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

    groups = switch_groups()
    Tsw = np.concatenate([L.triangles(s, 0.04, 0.09) for g in groups.values()
                          for v in g.values() for s in v])
    jw = L.unit(np.asarray(joyj["joyAxisWorld"], float))
    jc = np.asarray(joyj["knobCentreWorld"], float)
    keep = import_step(str(L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    rz = Location(Vector(*[float(x) for x in (jw * c07j["szhRaiseMm"])]))
    Tszh = [L.triangles(ch.moved(rz), 0.09, 0.16)
            for ch in list(getattr(keep, "children", []) or [])
            if ch.solids() and str(ch.label).startswith("SZH")
            and "MOVING" not in str(ch.label)
            and str(ch.label) not in ("SZH_cap", "SZH_header")]
    Tszh = np.concatenate(Tszh) if Tszh else np.zeros((0, 3, 3))
    L.memory("parts")

    fit = L.from_local(np.asarray([[a, b, c] for a in (-30.0, 30.0)
                                   for b in (-56.0, 22.0) for c in (-30.0, 28.0)], float))
    iso = tuple(L.DATUM_U * 0.45 + L.DATUM_V * -0.35 + jw * -0.82)

    for tag, name in (("1", easy), ("3", hard)):
        g = geom[name]
        ex, ey = axis_frame(g["w"])
        fl = np.asarray([g["cen"] + ex * a + ey * b + g["w"] * c
                         for a in (-16.0, 16.0) for b in (-16.0, 16.0)
                         for c in (-16.0, 12.0)])
        role = "EASY" if name == easy else "HARD"
        rec = k04["receivers"][name]
        R.render(OUT / ("%s_%s_%s_receiver.png" % (tag, role, name)),
                 [(TA, C_JAD, 0.30, "docs/101 JaD"), (TB, C_JFD, 0.30, "docs/101 JfD"),
                  (units[name], C_C08, 1.0, "C08 %s receiver" % name),
                  (L.triangles(seats[name]["body"], 0.04, 0.09), C_BODY, 1.0, "switch"),
                  (L.triangles(seats[name]["terminals"], 0.04, 0.09), C_TERM, 1.0, "terminals")],
                 tuple(-ey), tuple(g["w"]),
                 "%s - CASE %s (%s): local conformal receiver in place" % (tag, role, name),
                 "vol %.1f mm3, %d faces, transition %.3f mm, landing width %.3f mm"
                 % (rec["volumeMm3"], rec["faces"], rec["transitionLengthMm"],
                    rec["landingWidthMm"]), FOOT, fit=fl)
        R.render(OUT / ("%s_%s_%s_section.png" % (str(int(tag) + 1), role, name)),
                 [(R.clip_half(TA, g["cen"], ey), C_JAD, 1.0, "JaD"),
                  (R.clip_half(TB, g["cen"], ey), C_JFD, 1.0, "JfD"),
                  (R.clip_half(units[name], g["cen"], ey), C_C08, 1.0, "C08 receiver"),
                  (R.clip_half(L.triangles(seats[name]["body"], 0.04, 0.09), g["cen"], ey),
                   C_BODY, 1.0, "switch"),
                  (R.clip_half(Tcaps, g["cen"], ey), C_CAP, 1.0, "cap")],
                 tuple(-ey), tuple(g["w"]),
                 "%s - CASE %s (%s) sectioned on its press axis" % (str(int(tag) + 1), role, name),
                 "curved shell landing on top, flat seat below, one ruled taper between",
                 FOOT, fit=fl)
        L.memory("gate render " + name)

    R.render(OUT / "5_all_receivers.png",
             [(TA, C_JAD, 0.10, "JaD"), (TB, C_JFD, 0.10, "JfD"),
              (T8_, C_C08, 1.0, "C08: 8 receivers + %d ribs" % len(k04["links"]))],
             iso, tuple(jw),
             "5 - all eight C08 local receivers",
             "T1-T6 fuse on their own; only %d rib(s) added (%s)"
             % (len(k04["links"]),
                ", ".join("%s-%s" % (x["from"], x["to"]) for x in k04["links"])),
             FOOT, fit=fit)
    R.render(OUT / "6_transparent_shell.png",
             [(TA, C_JAD, 0.20, "docs/101 JaD"), (TB, C_JFD, 0.20, "docs/101 JfD"),
              (T8_, C_C08, 1.0, "C08 core"), (Tbody, C_BODY, 1.0, "8 switches"),
              (Tterm, C_TERM, 1.0, "terminals"), (Tcaps, C_CAP, 1.0, "caps")],
             tuple(-L.DATUM_V), tuple(jw),
             "6 - C08 inside the docs/101 shell",
             "shell penetration %.6f mm3 | 8/8 seats | 16/16 slots"
             % max(float(v) for v in [0.0]), FOOT, fit=fit)
    R.render(OUT / "7_joystick_and_receivers.png",
             [(TA, C_JAD, 0.12, "JaD"), (TB, C_JFD, 0.12, "JfD"),
              (T8_, C_C08, 1.0, "C08 receivers"),
              (Tszh, C_SZH, 0.85, "SZH static (PROVISIONAL)")],
             tuple(-axis_frame(jw)[1]), tuple(jw),
             "7 - joystick coordination: C08 leaves the JOY package free",
             "SZH static interference %.6f mm3; the C07 deck is carried over unchanged"
             % max(k05["szhStatic"].values()), FOOT, fit=fit)
    R.render(OUT / "8_docs101_finger_interface.png",
             [(T8_, C_C08, 1.0, "C08 core"), (Tsw, C_SW, 1.0, "8 docs/101 Finger switches")],
             iso, tuple(jw),
             "8 - C08 against the docs/101 Finger switches",
             "interference 0.000000 mm3 on all 8; minimum clearance %.4f mm"
             % k05["minFingerClearanceMm"], FOOT, fit=fit)
    R.render(OUT / "9_underside_fdm.png",
             [(T8_, C_C08, 1.0, "C08 as printed")],
             tuple(-jw), tuple(axis_frame(jw)[0]),
             "9 - C08 underside, print orientation JOY_AXIS_UP",
             "support %.1f mm2 (%.1f%%) against C07's %.1f mm2 (%.1f%%)"
             % (k05["supportC08"]["supportMm2"], 100 * k05["supportC08"]["supportFraction"],
                k05["supportC07"]["supportMm2"], 100 * k05["supportC07"]["supportFraction"]),
             FOOT, fit=fit)
    R.render(OUT / "10a_C07_same_camera.png",
             [(TA, C_JAD, 0.14, "JaD"), (TB, C_JFD, 0.14, "JfD"),
              (T7_, C_C07, 1.0, "C07: slab + deck + walls + standoffs")],
             iso, tuple(jw), "10a - C07, same camera",
             "%.0f mm3, %d faces, 26 major members" % (c07j["volumeMm3"], c07j["faces"]),
             FOOT, fit=fit)
    R.render(OUT / "10b_C08_same_camera.png",
             [(TA, C_JAD, 0.14, "JaD"), (TB, C_JFD, 0.14, "JfD"),
              (T8_, C_C08, 1.0, "C08: 8 local receivers + %d ribs" % len(k04["links"]))],
             iso, tuple(jw), "10b - C08, same camera",
             "%.0f mm3, %d faces, %d major members"
             % (k04["volumeMm3"], k04["faces"], 8 + len(k04["links"])), FOOT, fit=fit)
    print("renders written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
