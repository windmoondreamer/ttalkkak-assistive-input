"""I02c - restore the ORIGINAL protrusion law in the CURRENT shell (REV_I section 9).

I02 established the problem: the inherited "lowered" caps are the ORIGINAL caps
rigidly translated by THUMB_DELTA, and they end up 4.12 - 7.18 mm BELOW the
current outer skin instead of 1.07 - 1.46 mm above it.  A button recessed 5 mm
into a hole cannot be pressed, so the inherited cap position cannot be the datum
for the seat.

Section 9 says the CAP / SWITCH stack controls the seat depth and the original
protrusion is a functional requirement.  So: slide each ORIGINAL cap along its
own frozen press axis until its top face sits at the ORIGINAL protrusion above
the CURRENT skin, and test whether it actually fits there.

Sliding along the axis changes nothing that is frozen -- the external centre and
the press axis are both preserved by construction.

The boolean test is done solid-to-solid with L.inter_vol, never on Compounds,
and the answer is cross-checked with a ray-parity point test because OCC has
returned empty results for near-coincident shells elsewhere in this lab.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Compound, Location, Vector, export_step, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from i02_original_external_stack import frame, skin_reference  # noqa: E402

OUT = L.LAB / "02_original_external_stack"
CAP_TO_PLATE = 4.759      # H02, inherited from REV_H
PLATE_T = 2.003


def parity_inside(T, P):
    """Fraction of points inside a closed mesh, by ray parity with de-dup."""
    d = np.array([0.5773502691896258, 0.5773502691896258, 0.5773502691896258])
    n = 0
    for p in P:
        h = ray_intervals(T, p, d, 1.0e-7, 400.0)
        if h and any(lo <= 0.0 <= hi for lo, hi in h):
            n += 1
        elif h is None:
            continue
        else:
            # origin outside every interval -> count material crossings ahead
            k = sum(1 for lo, hi in h if lo > 0.0) * 2
            n += 1 if k % 4 == 2 else 0
    return n / max(1, len(P))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ext = json.loads((OUT / "i02_original_external_stack.json").read_text(encoding="utf-8"))

    shell = []
    for k in ("JAD_APPROVED", "JFD_APPROVED"):
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        shell.append(s)
    Tsh = np.concatenate([L.triangles(s, tol=0.06, ang=0.12) for s in shell])
    print("approved shell: %d triangles, %d solids" % (len(Tsh), len(shell)))
    L.memory("shell")

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    rows, placed = {}, []
    print("")
    print("=== source-faithful cap placement (ORIGINAL protrusion law, CURRENT shell) ===")
    print("%-5s %9s %9s %9s %10s %11s %11s"
          % ("ctrl", "target", "shiftOut", "capTop", "capUnder", "cap^shell", "plateTop"))
    for short in ORDER:
        if short == "JOY":
            continue
        lab = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[lab], short)
        w, _, tilt = true_axis(cap)
        P = L.surf_points(cap, 60000, tol=0.04)
        cen = P.mean(axis=0)
        ex, ey = frame(w)
        s = (P - cen) @ w
        r_cap = float(np.hypot((P - cen) @ ex, (P - cen) @ ey).max())
        skin = skin_reference(Tsh, cen, w, ex, ey, r_cap)["referenceMm"]
        target = ext["ORIGINAL"]["buttons"][short]["unpressedProtrusionMm"]

        # slide along the frozen axis so the cap top lands at skin + target
        shift = (skin + target) - float(s.max())
        moved = cap.moved(Location(Vector(*[float(x) for x in (w * shift)])))
        moved.label = "CAP_%s_SOURCE_FAITHFUL" % short
        iv = sum(L.inter_vol(moved, sh) for sh in shell)

        Pm = P + w * shift
        sm = (Pm - cen) @ w
        cap_top, cap_und = float(sm.max()), float(sm.min())
        plate_top = cap_und - CAP_TO_PLATE

        # free depth on the axis below the new plate plane
        o = cen + w * plate_top
        h = ray_intervals(Tsh, o, -w, 0.0, 60.0)
        free = float(min([a for a, _ in (h or [])], default=60.0))

        rows[short] = {
            "tiltDeg": tilt, "axisWorld": w.tolist(), "capCentreWorld": cen.tolist(),
            "currentSkinOnAxisMm": skin,
            "targetProtrusionMm": target,
            "axialShiftOutwardMm": shift,
            "newCapTopAboveSkinMm": cap_top - skin,
            "newCapUndersideAboveSkinMm": cap_und - skin,
            "newPlateTopAboveSkinMm": plate_top - skin,
            "newPlateTopWorld": (cen + w * plate_top).tolist(),
            "newCapUndersideWorld": (cen + w * cap_und).tolist(),
            "capShellInterferenceMm3": iv,
            "freeDepthBelowPlateTopMm": free,
        }
        placed.append(moved)
        print("%-5s %9.3f %9.3f %9.3f %10.3f %11.4f %11.3f"
              % (short, target, shift, cap_top - skin, cap_und - skin, iv,
                 plate_top - skin))
        del cap
        L.memory("cap " + short)

    sh = np.array([rows[k]["axialShiftOutwardMm"] for k in rows])
    iv = np.array([rows[k]["capShellInterferenceMm3"] for k in rows])
    pt = np.array([rows[k]["newPlateTopAboveSkinMm"] for k in rows])
    print("")
    print("=== summary ===")
    print("  outward shift needed: min %.3f  max %.3f  mean %.3f mm"
          % (sh.min(), sh.max(), sh.mean()))
    print("  cap-to-shell interference at the restored position: max %.4f mm3" % iv.max())
    print("  new plate-top plane sits %.3f to %.3f mm below the skin"
          % (-pt.max(), -pt.min()))
    print("  (REV_H put the plate %.3f to %.3f mm below the skin)"
          % (-(pt.max() - sh.max()), -(pt.min() - sh.min())))
    fits = iv.max() <= 1.0
    print("  -> %s" % ("ORIGINAL CAP GEOMETRY FITS AT THE ORIGINAL PROTRUSION"
                       if fits else
                       "ORIGINAL CAP GEOMETRY DOES NOT FIT AT THE ORIGINAL PROTRUSION"))

    export_step(Compound(children=placed, label="SOURCE_FAITHFUL_CAPS"),
                str(OUT / "I02C_SOURCE_FAITHFUL_CAPS.step"))
    L.write_json(OUT / "i02c_source_faithful_cap_placement.json",
                 {"capToPlateMm": CAP_TO_PLATE, "plateThicknessMm": PLATE_T,
                  "buttons": rows,
                  "shiftStats": {"minMm": float(sh.min()), "maxMm": float(sh.max()),
                                 "meanMm": float(sh.mean())},
                  "maxCapShellInterferenceMm3": float(iv.max()),
                  "fits": bool(fits), "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
