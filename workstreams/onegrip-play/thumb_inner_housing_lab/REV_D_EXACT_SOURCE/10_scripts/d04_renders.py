"""D04 - matched sections against the EXACT APPROVED shell (REV_D section 12).

Three configurations on five identical section planes:
  A  ORIGINAL shell        + ORIGINAL Backplate   (translated into the lowered
                                                   frame; pure translation)
  B  EXACT APPROVED shell  + lowered Backplate
  C  EXACT APPROVED shell  + C01
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
import labrender as R  # noqa: E402
from b01_true_axes import combined_shell  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI  # noqa: E402
from d02_housing_vs_exact import BP_LOW_STEP, BP_STEP, C01_STEP, approved_shell  # noqa: E402

OUT = L.LAB / "08_renders"
OUTWARD = -L.DATUM_N
C_ORIG_SHELL = (150, 160, 172)
C_APPROVED = (146, 176, 128)
C_BP = (232, 168, 74)
C_C01 = (86, 186, 132)
FOOT = ("Thumb Inner Housing Lab REV_D | authority = exact Onshape "
        "THUMB_LOWER15_HOUSING_V1 export | audit only")
FIT_LOCAL = np.asarray([[a, b, c] for a in (-26.0, 26.0)
                        for b in (-52.0, 18.0) for c in (-24.0, 22.0)], float)

SECTIONS = [
    ("S1_JOY", "v", 0.0, "through the joystick centre"),
    ("S2_BUTTON_ROW", "v", -30.4, "through the T2 / T4 / T6 button row"),
    ("S3_T1_T3", "v", -40.8, "through the T1 / T3 / T5 row"),
    ("S4_N1_ADJACENT", "u", -10.0, "N1-adjacent, through the N1/N2 carrier region"),
    ("S5_N2_ADJACENT", "u", 2.0, "N2-adjacent"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fit = L.from_local(FIT_LOCAL)
    dx = Location(Vector(*[float(x) for x in L.THUMB_DELTA]))

    approved = approved_shell()
    Tap = L.triangles(approved, tol=0.08, ang=0.15)
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    clean = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER", box, "CLEAN")
    Tcl = L.triangles(clean.moved(dx), tol=0.08, ang=0.15)
    del clean

    bp = import_step(str(BP_STEP))
    Tbp = L.triangles(L.as_single_solid(bp, "BP")[0].moved(dx), tol=0.06, ang=0.12)
    bpl = import_step(str(BP_LOW_STEP))
    Tbpl = L.triangles(L.as_single_solid(bpl, "BPL")[0], tol=0.06, ang=0.12)
    c01 = import_step(str(C01_STEP))
    Tc01 = L.triangles(L.as_single_solid(c01, "C01")[0], tol=0.06, ang=0.12)
    L.memory("loaded")

    configs = [
        ("A", Tcl, C_ORIG_SHELL, "ORIGINAL shell", Tbp, C_BP, "ORIGINAL Backplate",
         "gap p50 +1.230 mm | contact band 7.48 % | two perimeter zones 71.7 + 23.4 mm2"),
        ("B", Tap, C_APPROVED, "EXACT APPROVED shell", Tbpl, C_BP, "lowered Backplate",
         "gap p50 +8.948 mm | contact band 0.18 % | no contact zone >= 1 mm2"),
        ("C", Tap, C_APPROVED, "EXACT APPROVED shell", Tc01, C_C01, "C01",
         "gap p25/p50/p75 +1.177/+1.192/+1.201 mm | interference 0.002603 mm3"),
    ]

    for sname, axis, val, sdesc in SECTIONS:
        if axis == "v":
            nrm = L.DATUM_V
            pt = L.from_local([[0.0, val, 0.0]])[0]
            cam = tuple(-L.DATUM_V)
        else:
            nrm = L.DATUM_U
            pt = L.from_local([[val, 0.0, 0.0]])[0]
            cam = tuple(-L.DATUM_U)
        for tag, Ts, cs, ls, Th, ch, lh, sub in configs:
            layers = [(R.clip_half(Ts, pt, nrm), cs, 1.0, ls),
                      (R.clip_half(Th, pt, nrm), ch, 1.0, lh)]
            layers = [x for x in layers if len(x[0])]
            if not layers:
                continue
            R.render(OUT / ("%s_%s.png" % (sname, tag)), layers, cam, OUTWARD,
                     "%s  %s = %+.1f mm  --  %s" % (sname, axis, val, sdesc),
                     "%s + %s   |   %s" % (ls, lh, sub), FOOT, fit=fit)
        L.memory("section " + sname)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
