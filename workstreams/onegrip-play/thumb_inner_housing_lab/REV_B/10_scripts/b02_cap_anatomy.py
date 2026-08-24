"""B02 - what shape are the Thumb caps actually?

B01's three axis methods disagreed (T1/T3 came out at 87 deg tilt from M1),
so the axis rule cannot be chosen before the cap geometry is known.
Dumps every B-rep face of every cap: area, unit normal, and the normal's angle
to the joystick outward axis.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, face_normals, leaf_parts  # noqa: E402

OUT = L.LAB / "01_axis_authority"
OUTWARD = -L.DATUM_N


def main() -> int:
    root, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    rows = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        fn = face_normals(cap)
        bb = cap.bounding_box()
        cen = np.asarray([(bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2,
                          (bb.min.Z + bb.max.Z) / 2], float)
        print("\n=== %s : vol=%.3f mm3  faces=%d  planarFaceGroups=%d ==="
              % (short, L.vol(cap), len(list(cap.faces())), len(fn)))
        entries = []
        for n, a in sorted(fn, key=lambda r: -r[1]):
            ang = float(np.degrees(np.arccos(np.clip(float(np.dot(n, OUTWARD)), -1, 1))))
            # is the face centred outboard or inboard?
            entries.append({"normal": n.tolist(), "areaMm2": a, "angleToOutwardDeg": ang})
            print("   area=%8.3f  n=%-40s  angle to outward = %7.2f deg"
                  % (a, np.array2string(np.round(n, 5)), ang))
        rows[short] = {"volumeMm3": L.vol(cap), "faceCount": len(list(cap.faces())),
                       "centreWorld": cen.tolist(), "faces": entries}
        del cap
    L.write_json(OUT / "b02_cap_anatomy.json", {"caps": rows, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
