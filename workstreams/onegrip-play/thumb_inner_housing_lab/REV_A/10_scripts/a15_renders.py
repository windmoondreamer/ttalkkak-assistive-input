"""A15 - comparison renders: ORIGINAL / CURRENT / CANDIDATE.

Identical camera and identical section plane in all three, so the images can be
placed side by side.  The ORIGINAL pair (clean shell + original Backplate) is
rigidly translated by +THUMB_DELTA so it lands in the same local Thumb frame;
that is a pure translation, so the shell-to-housing relationship is untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Compound, Location, Vector, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
import labrender as R  # noqa: E402
from a07_conformity_map import combined_shell, backplate  # noqa: E402

OUT = L.LAB / "08_renders"
CROP_LO = (-32.0, -54.0, -60.0)
CROP_HI = (32.0, 24.0, 60.0)

C_SHELL = (128, 152, 172)
C_ORIG_HOUSING = (232, 168, 74)
C_CUR_HOUSING = (226, 86, 86)
C_C01 = (86, 186, 132)
C_SZH = (150, 108, 214)
C_MOVING = (240, 168, 96)
C_CARRIER = (96, 176, 220)
C_CAPS = (60, 66, 76)

OUTWARD = -L.DATUM_N
CAM_ISO = tuple((L.DATUM_U * 0.55 + L.DATUM_V * -0.45 + OUTWARD * -0.70))
CAM_SECT = tuple(L.DATUM_U * -1.0)
CAM_FRONT = tuple(OUTWARD * -1.0)
CAM_ROW = tuple(L.DATUM_V * -1.0)


def tris(shape, tol=0.10):
    return L.triangles(shape, tol=tol, ang=0.18)


def sect(T, u=None, v=None):
    """Keep the half BEHIND the cut plane relative to the camera.

    clip_half keeps (p - p0).normal <= 0.  The camera looks along -DATUM_U, so
    the visible half must be u <= u_cut, which needs normal = +DATUM_U.  Using
    -DATUM_U keeps the near half instead and the image shows the outside of the
    shell rather than the cut face (that mistake produced the first render).
    """
    if u is not None:
        return R.clip_half(T, L.from_local([[u, 0, 0]])[0], L.DATUM_U)
    return R.clip_half(T, L.from_local([[0, v, 0]])[0], L.DATUM_V)


FIT_LOCAL = np.asarray([[a, b, c] for a in (-25.0, 25.0)
                        for b in (-52.0, 18.0) for c in (-18.0, 20.0)], float)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    dx = Location(Vector(*[float(x) for x in L.THUMB_DELTA]))

    box_cur = L.local_box(CROP_LO, CROP_HI, "CUR")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box_cur, "FROZEN")
    Tf = tris(frozen)
    L.memory("frozen tris")

    # original pair, translated into the current local frame
    lo_o, hi_o = np.asarray(CROP_LO, float), np.asarray(CROP_HI, float)
    origin = L.DATUM_P - L.THUMB_DELTA
    world = np.asarray([origin + p[0] * L.DATUM_U + p[1] * L.DATUM_V + p[2] * OUTWARD
                        for p in (lo_o, hi_o)])
    loc = L.to_local(world)
    clean = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER",
                           L.local_box(loc[0], loc[1], "ORIG"), "CLEAN")
    Tc = tris(clean.moved(dx))
    del clean
    L.memory("clean tris")

    bp_o = backplate("ORIGINAL_THUMB_CARTRIDGE").moved(dx)
    bp_l = backplate("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    Tbo, Tbl = tris(bp_o, 0.06), tris(bp_l, 0.06)

    c01 = import_step(str(L.LAB / "09_exports" / "C01_SOURCE_FAITHFUL_REBASE.step"))
    c01, _ = L.as_single_solid(c01, "C01")
    Tc01 = tris(c01, 0.06)
    L.memory("housings")

    keep = import_step(str(L.LAB / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    szh, mov, carr, caps = [], [], [], []
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if not ch.solids():
            continue
        t = tris(ch, 0.10)
        if lab.startswith("CAP_"):
            caps.append(t)
        elif "MOVING" in lab:
            mov.append(t)
        elif lab.startswith("SZH_"):
            szh.append(t)
        elif "CARRIER" in lab:
            carr.append(t)
    Tszh = np.concatenate(szh) if szh else np.zeros((0, 3, 3))
    Tmov = np.concatenate(mov) if mov else np.zeros((0, 3, 3))
    Tcar = np.concatenate(carr) if carr else np.zeros((0, 3, 3))
    Tcap = np.concatenate(caps) if caps else np.zeros((0, 3, 3))
    L.memory("keepout tris")

    FOOT = ("Thumb Inner Housing Lab REV_A | analysis only | no production geometry written | "
            "local frame: u=DATUM_U, v=DATUM_V, n=outward, origin = lowered joystick centre")
    fit = L.from_local(FIT_LOCAL)

    # ---- 1..3 : same section (u >= 0 removed), same camera --------------
    trio = [
        ("01_ORIGINAL_section.png", "ORIGINAL  —  original shell + original Backplate",
         sect(Tc, u=0.0), C_ORIG_HOUSING, sect(Tbo, u=0.0),
         "original inner housing (Backplate)",
         "conformal gap median +1.292 mm  |  contact band <=0.30 mm on 6.4 % of columns"),
        ("02_CURRENT_section.png", "CURRENT  —  frozen lowered shell + rigidly lowered Backplate",
         sect(Tf, u=0.0), C_CUR_HOUSING, sect(Tbl, u=0.0),
         "current inner housing (Backplate, translated (0,+12.25,-21))",
         "conformal gap median +9.027 mm  |  only 21 of 7293 columns within 0.5 mm"),
        ("03_CANDIDATE_C01_section.png", "CANDIDATE C01  —  frozen lowered shell + conformal rebase",
         sect(Tf, u=0.0), C_C01, sect(Tc01, u=0.0),
         "C01_SOURCE_FAITHFUL_REBASE",
         "conformal gap median +1.196 mm  |  shell intersection 0.000000 mm3"),
    ]
    for name, title, Ts, col, Th, hlabel, sub in trio:
        R.render(OUT / name, [(Ts, C_SHELL, 1.0, "shell (section at u = 0)"),
                              (Th, col, 1.0, hlabel)],
                 CAM_SECT, OUTWARD, title, sub, FOOT, fit=fit)

    # ---- 4..6 : same section through the button row (v <= -30) ----------
    trio2 = [
        ("04_ORIGINAL_button_row.png", "ORIGINAL  —  section through the button row (v = -30)",
         sect(Tc, v=-30.0), C_ORIG_HOUSING, sect(Tbo, v=-30.0), "original Backplate"),
        ("05_CURRENT_button_row.png", "CURRENT  —  section through the button row (v = -30)",
         sect(Tf, v=-30.0), C_CUR_HOUSING, sect(Tbl, v=-30.0), "lowered Backplate"),
        ("06_CANDIDATE_C01_button_row.png", "CANDIDATE C01  —  section through the button row (v = -30)",
         sect(Tf, v=-30.0), C_C01, sect(Tc01, v=-30.0), "C01 conformal plate"),
    ]
    for name, title, Ts, col, Th, hlabel in trio2:
        R.render(OUT / name, [(Ts, C_SHELL, 1.0, "shell"), (Th, col, 1.0, hlabel)],
                 CAM_ROW, OUTWARD, title,
                 "same camera and same section plane as images 01-03", FOOT, fit=fit)

    # ---- 7 : candidate with keep-outs ------------------------------------
    R.render(OUT / "07_C01_with_keepouts_section.png",
             [(sect(Tf, u=0.0), C_SHELL, 1.0, "frozen shell (section u = 0)"),
              (sect(Tc01, u=0.0), C_C01, 1.0, "C01 conformal plate"),
              (sect(Tszh, u=0.0), C_SZH, 1.0, "SZH-EK056 static (PROVISIONAL web reference)"),
              (sect(Tmov, u=0.0), C_MOVING, 0.40, "SZH 25 deg moving envelope (PROVISIONAL)"),
              (sect(Tcar, u=0.0), C_CARRIER, 1.0, "frozen N1/N2 shared carrier")],
             CAM_SECT, OUTWARD,
             "CANDIDATE C01 + keep-outs",
             "SZH PCB sits at n = -11.5 .. -13.1 while the Thumb wall inner surface is at n = +11 .. +14",
             FOOT, fit=fit)

    # ---- 8 : transparent shell, isometric --------------------------------
    R.render(OUT / "08_C01_transparent_shell_iso.png",
             [(Tf, C_SHELL, 0.30, "frozen shell"),
              (Tc01, C_C01, 1.0, "C01 conformal plate"),
              (Tcap, C_CAPS, 1.0, "frozen Thumb control caps"),
              (Tszh, C_SZH, 1.0, "SZH-EK056 static (PROVISIONAL)"),
              (Tcar, C_CARRIER, 1.0, "N1/N2 carrier")],
             CAM_ISO, OUTWARD, "CANDIDATE C01 inside the frozen shell",
             "transparent shell, isometric", FOOT, fit=fit)

    # ---- 9 : the exterior finding ----------------------------------------
    R.render(OUT / "09_frozen_exterior_sealed_buttons.png",
             [(Tf, C_SHELL, 1.0, "frozen lowered exterior"),
              (Tcap, C_CAPS, 1.0, "frozen Thumb caps (buried behind the wall)")],
             CAM_FRONT, L.DATUM_V,
             "FROZEN EXTERIOR  —  Thumb controls seen from outside",
             "A09: clear-path exposure T2 / T7 / T8 = 0.0 %, T4 = 1.2 %, T6 = 3.9 % "
             "(original exterior: 100 % for all nine)", FOOT,
             fit=fit)

    R.render(OUT / "10_original_exterior_reference.png",
             [(Tc, C_SHELL, 1.0, "original exterior (translated for comparison)"),
              (Tbo, C_ORIG_HOUSING, 1.0, "original Backplate")],
             CAM_FRONT, L.DATUM_V,
             "ORIGINAL EXTERIOR  —  same viewpoint as image 09",
             "every control had a 100 % clear path through its own opening", FOOT,
             fit=fit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
