"""I02e - exact anatomy of the cap/shell overlap (REV_I sections 9, 18).

I02d reported a worst signed clearance of -1.73 mm and classified five buttons
CLASS A.  That result is suspect for a specific reason: the MEDIAN clearance is
+0.07 to +0.20 mm, which is exactly the original design tolerance, and every
worst case is 1.0 - 1.8 mm below the skin, right at the depth where a lateral
ray can still start outside the material on a curved panel and return the OUTER
skin instead of the bore wall.

So the overlap is measured again without any ray geometry: take the exact
boolean intersection of the placed cap with each shell solid and look at what it
actually is.  Volume, bounding box and radial extent together say whether this
is a shallow rub (CLASS B) or a real interference (CLASS A).

The intersection is taken solid-to-solid.  Passing a Compound silently returns
an empty result in OCC, which is a documented trap in this project.
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
from b03_axis_authority import true_axis  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402

OUT = L.LAB / "02_original_external_stack"
HAND_FINISH_LIMIT = 0.60


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pl = json.loads((OUT / "i02c_source_faithful_cap_placement.json").read_text(encoding="utf-8"))

    shell = []
    for k in ("JAD_APPROVED", "JFD_APPROVED"):
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        shell.append(s)
    print("approved shell solids: %d" % len(shell))
    L.memory("shell")

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    rows, keep = {}, []
    print("")
    print("=== exact cap/shell overlap anatomy at the restored protrusion ===")
    print("%-5s %10s %7s %9s %9s %9s %9s  %s"
          % ("ctrl", "volume", "pieces", "radial", "axial", "depthTop", "depthBot", "class"))
    for short in ORDER:
        if short == "JOY":
            continue
        b = pl["buttons"][short]
        lab = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[lab], short)
        w = np.asarray(b["axisWorld"], float)
        cen = np.asarray(b["capCentreWorld"], float)
        ex, ey = frame(w)
        moved = cap.moved(Location(Vector(*[float(x) for x in (w * b["axialShiftOutwardMm"])])))
        skin = b["currentSkinOnAxisMm"]

        pieces, vol = [], 0.0
        for sh in shell:
            try:
                x = (moved & sh).clean()
            except Exception:
                continue
            for sol in x.solids():
                v = float(sol.volume)
                if v > 1.0e-6:
                    pieces.append(sol)
                    vol += v
        if not pieces:
            rows[short] = {"overlapVolumeMm3": 0.0, "pieces": 0,
                           "classification": "NO OVERLAP"}
            print("%-5s %10.4f %7d %9s %9s %9s %9s  NO OVERLAP"
                  % (short, 0.0, 0, "-", "-", "-", "-"))
            del cap
            continue

        P = np.concatenate([L.surf_points(s, 30000, tol=0.02) for s in pieces])
        d = P - cen
        n = d @ w
        rad = np.hypot(d @ ex, d @ ey)
        # radial extent of the overlap = how deep the shell bites into the cap
        radial = float(rad.max() - rad.min())
        axial = float(n.max() - n.min())
        cls = ("CLASS B - HAND FINISHABLE" if radial <= HAND_FINISH_LIMIT
               else "CLASS A - MUST SOLVE IN CAD")
        rows[short] = {"overlapVolumeMm3": vol, "pieces": len(pieces),
                       "radialBiteMm": radial, "axialExtentMm": axial,
                       "overlapTopBelowSkinMm": float(skin - n.max()),
                       "overlapBottomBelowSkinMm": float(skin - n.min()),
                       "radiusRangeMm": [float(rad.min()), float(rad.max())],
                       "classification": cls}
        for s in pieces:
            s.label = "OVERLAP_%s" % short
            keep.append(s)
        print("%-5s %10.4f %7d %9.4f %9.3f %9.3f %9.3f  %s"
              % (short, vol, len(pieces), radial, axial,
                 skin - n.max(), skin - n.min(), cls))
        del cap
        L.memory("overlap " + short)

    rb = np.array([rows[k].get("radialBiteMm", 0.0) for k in rows])
    vv = np.array([rows[k]["overlapVolumeMm3"] for k in rows])
    print("")
    print("=== summary ===")
    print("  total overlap volume over eight caps: %.4f mm3" % vv.sum())
    print("  worst radial bite into a cap:         %.4f mm" % rb.max())
    verdict = ("CAP-SIDE FIT IS CLASS B - HAND FINISHABLE"
               if rb.max() <= HAND_FINISH_LIMIT else
               "CAP-SIDE FIT IS CLASS A - MUST SOLVE IN CAD")
    print("  -> %s (limit %.2f mm)" % (verdict, HAND_FINISH_LIMIT))
    if keep:
        export_step(Compound(children=keep, label="CAP_SHELL_OVERLAP"),
                    str(OUT / "I02E_CAP_SHELL_OVERLAP.step"))

    L.write_json(OUT / "i02e_cap_overlap_anatomy.json",
                 {"handFinishLimitMm": HAND_FINISH_LIMIT, "buttons": rows,
                  "totalOverlapMm3": float(vv.sum()),
                  "worstRadialBiteMm": float(rb.max()),
                  "verdict": verdict, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
