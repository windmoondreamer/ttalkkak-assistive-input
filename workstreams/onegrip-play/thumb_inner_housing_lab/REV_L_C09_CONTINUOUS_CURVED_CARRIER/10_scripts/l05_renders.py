"""L05 - C09 renders."""
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
from h01_seat_audit import axis_frame  # noqa: E402
from h03_placement import seat_solids  # noqa: E402
from j02_collision import switch_groups  # noqa: E402

OUT = L.LAB / "08_renders"
C_JAD = (150, 178, 132)
C_JFD = (126, 158, 176)
C_C09 = (110, 195, 200)
C_C071 = (196, 150, 120)
C_C08 = (170, 190, 130)
C_BODY = (96, 150, 226)
C_TERM = (240, 200, 80)
C_CAP = (56, 62, 72)
C_SW = (226, 110, 90)
C_SZH = (170, 120, 220)
FOOT = ("Thumb Inner Housing Lab REV_L | C09 continuous curved carrier | "
        "docs/101 shell | SZH geometry PROVISIONAL")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core_j = json.loads((L.REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    c07j = json.loads((L.REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    plc = json.loads((L.REV_I / "02_original_external_stack" /
                      "i02c_source_faithful_cap_placement.json").read_text(encoding="utf-8"))
    val = json.loads((L.LAB / "04_validation" / "l04_validate.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    c09, _ = L.as_single_solid(import_step(
        str(L.LAB / "03_full_c09" / "C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE.step")), "C09")
    c71, _ = L.as_single_solid(import_step(L.SRC["C07_1"]), "C07_1")
    c08, _ = L.as_single_solid(import_step(
        str(L.REV_K / "03_full_c08" / "C08_LOCAL_CONFORMAL_SWITCH_RECEIVER_CORE.step")), "C08")
    T9 = L.triangles(c09, tol=0.04, ang=0.09)
    T71 = L.triangles(c71, tol=0.04, ang=0.09)
    T08 = L.triangles(c08, tol=0.04, ang=0.09)
    ja, _ = L.as_single_solid(import_step(L.SRC["D101_JAD"]), "JaD")
    jf, _ = L.as_single_solid(import_step(L.SRC["D101_JFD"]), "JfD")
    TA = L.triangles(ja, tol=0.07, ang=0.14)
    TB = L.triangles(jf, tol=0.07, ang=0.14)
    del ja, jf
    L.memory("load")

    seats = {s: seat_solids(np.asarray(core_j["seats"][s]["capUndersideWorld"], float),
                            np.asarray(core_j["seats"][s]["axisWorld"], float), s)
             for s in names}
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
    v = val["viablePaths"][0] if val["viablePaths"] else "none"

    R.render(OUT / "1_C09_in_docs101_shell.png",
             [(TA, C_JAD, 0.22, "docs/101 JaD"), (TB, C_JFD, 0.22, "docs/101 JfD"),
              (T9, C_C09, 1.0, "C09 continuous curved carrier"),
              (Tcaps, C_CAP, 1.0, "caps at the preserved protrusion")],
             iso, tuple(jw),
             "1 - C09 in the docs/101 shell",
             "one carrier band + 8 inward blocks | shell interference %.6f mm3 | "
             "insertable %s" % (max(val["shell"].values()), v), FOOT, fit=fit)

    s = "T2"
    g = {"cen": np.asarray(core_j["seats"][s]["plateTopWorld"], float),
         "w": np.asarray(core_j["seats"][s]["axisWorld"], float)}
    ex, ey = axis_frame(g["w"])
    fl = np.asarray([g["cen"] + ex * a + ey * b + g["w"] * c
                     for a in (-20.0, 20.0) for b in (-20.0, 20.0)
                     for c in (-14.0, 14.0)])
    R.render(OUT / "2_section_carrier_block_seat.png",
             [(R.clip_half(TA, g["cen"], ey), C_JAD, 1.0, "JaD"),
              (R.clip_half(TB, g["cen"], ey), C_JFD, 1.0, "JfD"),
              (R.clip_half(T9, g["cen"], ey), C_C09, 1.0, "C09 carrier + block"),
              (R.clip_half(L.triangles(seats[s]["body"], 0.04, 0.09), g["cen"], ey),
               C_BODY, 1.0, "switch"),
              (R.clip_half(Tcaps, g["cen"], ey), C_CAP, 1.0, "cap")],
             tuple(-ey), tuple(g["w"]),
             "2 - the C09 stack, sectioned at T2",
             "curved carrier %.2f mm off the fitted shell interior -> short block "
             "hanging inward -> flat seat normal to the frozen press axis"
             % val["carrierGapMm"], FOOT, fit=fl)

    R.render(OUT / "3_carrier_and_blocks.png",
             [(TA, C_JAD, 0.08, "JaD"), (TB, C_JFD, 0.08, "JfD"),
              (T9, C_C09, 1.0, "C09"), (Tbody, C_BODY, 1.0, "8 switches"),
              (Tterm, C_TERM, 1.0, "terminals")],
             tuple(-L.DATUM_V), tuple(jw),
             "3 - one continuous band carrying all eight seats",
             "8/8 seats bearing, %d/16 slots open, terminals escape below"
             % sum(p["openSlots"] for p in val["buttons"].values()), FOOT, fit=fit)

    R.render(OUT / "4_docs101_finger_interface.png",
             [(T9, C_C09, 1.0, "C09"), (Tsw, C_SW, 1.0, "8 docs/101 Finger switches")],
             iso, tuple(jw),
             "4 - C09 against the docs/101 Finger switches",
             "collision %.6f mm3 on all 8; minimum clearance %.4f mm"
             % (max(val["fingerCollision"].values()), min(val["fingerClearance"].values())),
             FOOT, fit=fit)

    R.render(OUT / "5_joystick_region.png",
             [(TA, C_JAD, 0.12, "JaD"), (TB, C_JFD, 0.12, "JfD"),
              (T9, C_C09, 1.0, "C09"), (Tszh, C_SZH, 0.85, "SZH static (PROVISIONAL)")],
             tuple(-axis_frame(jw)[1]), tuple(jw),
             "5 - joystick coordination",
             "SZH static %.6f mm3; JOY column carries %.4f mm of C09"
             % (max(val["szhStatic"].values()), val["joyAxisMaterialMm"]), FOOT, fit=fit)

    R.render(OUT / "6_underside_fdm.png",
             [(T9, C_C09, 1.0, "C09 as printed")],
             tuple(-jw), tuple(axis_frame(jw)[0]),
             "6 - C09 underside, JOY_AXIS_UP",
             "support %.1f mm2 (%.1f%%) vs C07.1 %.1f mm2 (%.1f%%)"
             % (val["support"]["C09"]["supportMm2"],
                100 * val["support"]["C09"]["supportFraction"],
                val["support"]["C07_1"]["supportMm2"],
                100 * val["support"]["C07_1"]["supportFraction"]), FOOT, fit=fit)

    for tag, T, col, note in (("7a_C07_1", T71, C_C071, "C07.1: slab + 10 bridges + deck + chord wall"),
                              ("7b_C08", T08, C_C08, "C08: 8 conformal collars + 2 ribs"),
                              ("7c_C09", T9, C_C09, "C09: 1 curved band + 8 blocks")):
        R.render(OUT / ("%s_same_camera.png" % tag),
                 [(TA, C_JAD, 0.14, "JaD"), (TB, C_JFD, 0.14, "JfD"), (T, col, 1.0, note)],
                 iso, tuple(jw), "7 - %s, same camera" % tag.split("_", 1)[1], note,
                 FOOT, fit=fit)
    print("renders written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
