"""G03 - old vs Backplate-driven layout, matched cameras (REV_G section 16)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Compound, Location, Vector, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
import labrender as R  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from d02_housing_vs_exact import BP_STEP, approved_shell  # noqa: E402
from f01_rigid_fit import rot  # noqa: E402

OUT = L.LAB / "08_renders"
OUTWARD = -L.DATUM_N
C_SHELL = (146, 176, 128)
C_OLD = (56, 62, 72)
C_NEW = (226, 96, 86)
C_BP_OLD = (232, 168, 74)
C_BP_NEW = (96, 150, 226)
FOOT = ("Thumb Inner Housing Lab REV_G | audit only | shell authority = exact Onshape "
        "THUMB_LOWER15_HOUSING_V1 | no production apply")
FIT = np.asarray([[a, b, c] for a in (-28.0, 28.0) for b in (-56.0, 34.0)
                  for c in (-24.0, 26.0)], float)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fit = L.from_local(FIT)
    d = json.loads((L.LAB / "01_pose" / "g01_solve_pose.json").read_text(encoding="utf-8"))
    M = np.asarray(d["worldTransform4x4"], float)
    Rm, off = M[:3, :3], M[:3, 3]

    approved = approved_shell()
    Tap = L.triangles(approved, tol=0.08, ang=0.15)

    bp = import_step(str(BP_STEP))
    bp, _ = L.as_single_solid(bp, "BP")
    Tbp0 = L.triangles(bp, tol=0.06, ang=0.12)
    Tbp_old = (Tbp0.reshape(-1, 3) + L.THUMB_DELTA).reshape(-1, 3, 3)
    Tbp_new = ((Tbp0.reshape(-1, 3) @ Rm.T) + off).reshape(-1, 3, 3)

    _, cartO = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    _, cartL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    old_caps, new_caps = [], []
    for short in ORDER:
        lab = next(k for k, v in NAME_MAP.items() if v == short)
        cL, _ = L.as_single_solid(cartL[lab], short)
        old_caps.append(L.triangles(cL, tol=0.05, ang=0.10))
        cO, _ = L.as_single_solid(cartO[lab], short)
        t = L.triangles(cO, tol=0.05, ang=0.10)
        new_caps.append(((t.reshape(-1, 3) @ Rm.T) + off).reshape(-1, 3, 3))
        del cL, cO
    Told = np.concatenate(old_caps)
    Tnew = np.concatenate(new_caps)
    L.memory("geometry")

    cam_ext = tuple(OUTWARD * -1.0)
    sub_old = "OLD approved layout - the maximum-lowered Thumb (24.31 mm of lowering)"
    sub_new = ("NEW Backplate-driven layout - controls land 1.109 mm from the ORIGINAL "
               "pre-lowering position (95.0 % of the lowering undone)")

    R.render(OUT / "01_EXTERNAL_OLD_layout.png",
             [(Tap, C_SHELL, 1.0, "exact approved shell"),
              (Told, C_OLD, 1.0, "OLD control layout")],
             cam_ext, L.DATUM_V, "EXTERNAL - OLD approved Thumb layout", sub_old,
             FOOT, fit=fit)
    R.render(OUT / "02_EXTERNAL_NEW_layout.png",
             [(Tap, C_SHELL, 1.0, "exact approved shell"),
              (Tnew, C_NEW, 1.0, "NEW Backplate-driven layout")],
             cam_ext, L.DATUM_V, "EXTERNAL - NEW Backplate-driven Thumb layout", sub_new,
             FOOT, fit=fit)
    R.render(OUT / "03_EXTERNAL_OVERLAY.png",
             [(Tap, C_SHELL, 0.35, "exact approved shell"),
              (Told, C_OLD, 1.0, "OLD layout"),
              (Tnew, C_NEW, 1.0, "NEW Backplate-driven layout")],
             cam_ext, L.DATUM_V, "EXTERNAL OVERLAY - old vs Backplate-driven",
             "every control moves about 25.1 mm; mean distance from the ORIGINAL "
             "pre-lowering layout is 1.109 mm", FOOT, fit=fit)
    L.memory("external")

    # sections through the joystick, both poses
    for name, Tb, col, lbl, sub in (
        ("04_SECTION_backplate_OLD_pose.png", Tbp_old, C_BP_OLD,
         "Backplate at the approved lowered pose",
         "gap p25/p50/p75 = 6.572 / 8.349 / 10.742 mm - no contact, no load path"),
        ("05_SECTION_backplate_NEW_pose.png", Tbp_new, C_BP_NEW,
         "Backplate at the solved Backplate-driven pose",
         "gap p25/p50/p75 = 0.178 / 0.316 / 0.654 mm - but 213.97 mm2 interferes"),
    ):
        pt = L.from_local([[0.0, 0.0, 0.0]])[0]
        R.render(OUT / name,
                 [(R.clip_half(Tap, pt, L.DATUM_U), C_SHELL, 1.0, "exact approved shell"),
                  (R.clip_half(Tb, pt, L.DATUM_U), col, 1.0, lbl)],
                 tuple(-L.DATUM_U), OUTWARD,
                 "SECTION at u = 0 - %s" % lbl, sub, FOOT, fit=fit)

    R.render(OUT / "06_INTERNAL_transparent_both_poses.png",
             [(Tap, C_SHELL, 0.28, "exact approved shell"),
              (Tbp_old, C_BP_OLD, 1.0, "Backplate at the approved lowered pose"),
              (Tbp_new, C_BP_NEW, 1.0, "Backplate at the Backplate-driven pose")],
             tuple((L.DATUM_U * 0.5 + L.DATUM_V * -0.4 + OUTWARD * -0.75)), OUTWARD,
             "INTERNAL - both Backplate poses inside the approved shell",
             "the Backplate-driven pose sits about 25 mm higher up the grip", FOOT,
             fit=fit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
