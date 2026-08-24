"""A06 - Thumb wall map on the COMBINED shell (JaD + JfD).

A05 probed single halves.  JaD spans u >= ~0 and JfD spans u <= ~0, so every
column at u = 0 grazes the split seam and returns nonsense.  Probing the union
removes that artefact.

For each Thumb control this reports the material slab the control axis passes
through, so cap flushness against the frozen exterior can be measured directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import export_step, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from a04_datum_probe import ray_hits  # noqa: E402

OUT = L.LAB / "04_current_thumb_analysis"
COPIES = L.LAB / "02_reference_copies"

CROP_LO = (-32.0, -54.0, -60.0)
CROP_HI = (32.0, 24.0, 60.0)

CENTRES = {
    "JOYSTICK": (0.0, 0.0),
    "T1_corner_1": (11.005, -41.44), "T2_middle_1": (0.010, -30.385),
    "T3_corner_2": (-10.995, -41.44), "T4_side_1": (11.010, -30.39),
    "T5_middle_2": (0.010, -41.355), "T6_side_2": (-10.99, -30.39),
    "T7_wide_1": (8.160, -18.12), "T8_wide_2": (-8.150, -18.12),
}
# cap outer n from A03 (LOWERED position)
CAP_OUTER_N = {"T1_corner_1": 6.66, "T2_middle_1": 7.35, "T3_corner_2": 6.67,
               "T4_side_1": 7.49, "T5_middle_2": 6.58, "T6_side_2": 7.49,
               "T7_wide_1": 7.77, "T8_wide_2": 7.77, "JOYSTICK": 14.40}
CAP_INNER_N = {"T1_corner_1": 1.30, "T2_middle_1": 2.06, "T3_corner_2": 1.29,
               "T4_side_1": 2.06, "T5_middle_2": 1.30, "T6_side_2": 2.06,
               "T7_wide_1": 2.96, "T8_wide_2": 2.96, "JOYSTICK": 3.40}


def slabs(hits: np.ndarray):
    if hits.size % 2:
        return None
    return [(float(hits[i]), float(hits[i + 1])) for i in range(0, hits.size, 2)]


def combined(jad_key: str, jfd_key: str, box, tag: str):
    a = L.load(jad_key)
    sa, _ = L.as_single_solid((a & box).clean(), "A")
    del a
    L.memory(tag + " JaD crop")
    b = L.load(jfd_key)
    sb, _ = L.as_single_solid((b & box).clean(), "B")
    del b
    L.memory(tag + " JfD crop")
    u = (sa + sb).clean()
    out, n = L.as_single_solid(u, tag)
    L.memory(tag + " union (%d solids in)" % n)
    return out


def main() -> int:
    L.assert_local_box(CROP_LO, CROP_HI)
    box = L.local_box(CROP_LO, CROP_HI, "TALL_CROP")
    report = {}
    for tag, ka, kb in (("FROZEN", "JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB"),
                        ("FINGER_V2", "JAD_FINGER_V2", "JFD_FINGER_V2"),
                        ("CLEAN", "JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER")):
        shell = combined(ka, kb, box, tag)
        export_step(shell, str(COPIES / ("COMBINED_%s_THUMB_CROP.step" % tag)))
        T = L.local_triangles(shell, tol=0.10, ang=0.18)
        rows = {}
        print("\n=== %s : material slabs along each control axis ===" % tag)
        for name, (u, v) in CENTRES.items():
            s = slabs(ray_hits(T, float(u), float(v)))
            rows[name] = {"columnUV": [u, v], "slabs": s}
            if s is None:
                print("  %-14s PARITY FAIL" % name)
                continue
            if not s:
                print("  %-14s NO MATERIAL in this column (fully open)" % name)
                continue
            # the Thumb wall = slab nearest the cap, on the outboard side
            target = CAP_OUTER_N[name]
            near = min(s, key=lambda p: min(abs(p[0] - target), abs(p[1] - target)))
            rows[name]["thumbWallSlab"] = list(near)
            rows[name]["wallThicknessMm"] = near[1] - near[0]
            rows[name]["capOuterN"] = CAP_OUTER_N[name]
            rows[name]["capInnerN"] = CAP_INNER_N[name]
            rows[name]["capOuterMinusWallInner"] = CAP_OUTER_N[name] - near[0]
            print("  %-14s slabs=%s" % (name, ["[%.3f,%.3f]" % p for p in s]))
            print("      thumb wall n=[%.3f,%.3f] t=%.3f | cap n=[%.2f,%.2f] "
                  "| capOuter - wallInner = %+.3f"
                  % (near[0], near[1], near[1] - near[0],
                     CAP_INNER_N[name], CAP_OUTER_N[name], CAP_OUTER_N[name] - near[0]))
        report[tag] = rows
        del shell, T
        L.memory("probed " + tag)

    L.write_json(OUT / "a06_combined_wall_map.json",
                 {"cropLocal": {"min": list(CROP_LO), "max": list(CROP_HI)},
                  "shells": report, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
