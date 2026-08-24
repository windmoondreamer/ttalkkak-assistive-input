"""A05 - map the actual Thumb wall of the FROZEN shell.

A02/A04 used n in [-34, +14]; the Thumb wall is partly above +14, so those
crops truncated it.  Here the crop is tall in n and narrow in u/v, and the
ray family is placed at the real control centres.

Reported per column: every material slab [n_in, n_out], so the wall the Thumb
controls pass through can be identified unambiguously.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from a04_datum_probe import ray_hits  # noqa: E402

OUT = L.LAB / "04_current_thumb_analysis"

CROP_LO = (-30.0, -52.0, -60.0)
CROP_HI = (30.0, 22.0, 60.0)

# lowered control centres in local (u, v), from A03
LOWERED_CENTRES = {
    "JOYSTICK": (0.0, 0.0),
    "T1_corner_1": (11.005, -41.44), "T2_middle_1": (0.010, -30.385),
    "T3_corner_2": (-10.995, -41.44), "T4_side_1": (11.010, -30.39),
    "T5_middle_2": (0.010, -41.355), "T6_side_2": (-10.99, -30.39),
    "T7_wide_1": (8.160, -18.12), "T8_wide_2": (-8.150, -18.12),
}
RING = [("ring_r%02d_a%03d" % (r, a),
         (r * np.cos(np.radians(a)), r * np.sin(np.radians(a))))
        for r in (9, 12, 16) for a in range(0, 360, 45)]


def slabs(hits: np.ndarray) -> list:
    if hits.size % 2:
        return []
    return [[round(float(hits[i]), 4), round(float(hits[i + 1]), 4)]
            for i in range(0, hits.size, 2)]


def main() -> int:
    L.assert_local_box(CROP_LO, CROP_HI)
    box = L.local_box(CROP_LO, CROP_HI, "TALL_CROP")
    out = {}
    for tag, key in (("JAD_FROZEN", "JAD_LOWERED_THUMB"), ("JFD_FROZEN", "JFD_LOWERED_THUMB"),
                     ("JAD_FV2", "JAD_FINGER_V2"), ("JFD_FV2", "JFD_FINGER_V2")):
        full = L.load(key)
        sec, _ = L.as_single_solid((full & box).clean(), tag)
        T = L.local_triangles(sec, tol=0.12, ang=0.20)
        col = {}
        for name, (u, v) in list(LOWERED_CENTRES.items()) + RING:
            col[name] = slabs(ray_hits(T, float(u), float(v)))
        out[tag] = col
        print("\n=== %s ===" % tag)
        for name in LOWERED_CENTRES:
            print("  %-14s (u=%7.3f v=%8.3f)  %s"
                  % (name, LOWERED_CENTRES[name][0], LOWERED_CENTRES[name][1], col[name]))
        del full, sec, T
        L.memory("wall map " + tag)

    print("\n=== joystick ring, FROZEN JFD / JAD (opening boundary) ===")
    for name, (u, v) in RING:
        print("  %-16s u=%7.3f v=%7.3f | JAD %s | JFD %s"
              % (name, u, v, out["JAD_FROZEN"][name], out["JFD_FROZEN"][name]))

    L.write_json(OUT / "a05_thumb_wall_map.json",
                 {"cropLocal": {"min": list(CROP_LO), "max": list(CROP_HI)},
                  "columns": out, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
