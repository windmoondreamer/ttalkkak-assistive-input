"""B06 - (2) docs/71 wrong-shell recheck   (4) cap position audit.

SECTION 2
    docs/71 measured every "local_shell" row against JAD/JFD_FINGER_V2.  Re-run
    the SZH-vs-shell intersections against BOTH FINGER_V2 and the frozen
    LOWERED_THUMB shell and compare.  If the numbers differ materially the
    claim is CONFIRMED; if they agree it is NOT PROVEN.

SECTION 4
    For every Thumb control, on its TRUE axis:
        cap reference point (world), axis, original reference point,
        outer-skin crossing, inner-skin crossing, cap outermost point,
        signed distance cap-outermost -> outer skin,
        signed distance cap-outermost -> inner skin.
    No cap motion is proposed.  The point is to establish whether the CAP is
    misplaced or the WALL around it is.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Location, Plane, Shape, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, ray_intervals, true_axis  # noqa: E402

sys.path.insert(0, str(L.ROOT))
from build123d_workbench.szh_ek056_web_reference import (  # noqa: E402
    JOY_X, JOY_Y, PIVOT_Z, build_reference,
)

OUT2 = L.LAB / "02_docs71_recheck"
OUT4 = L.LAB / "04_cap_position_audit"
OUTWARD = -L.DATUM_N


def szh_location():
    pivot = np.asarray((JOY_X, JOY_Y, PIVOT_Z), float)
    origin = (L.DATUM_P - L.DATUM_V * pivot[0] - L.DATUM_U * pivot[1] - OUTWARD * pivot[2])
    return Location(Plane(origin=L.xyz(origin), x_dir=L.xyz(L.DATUM_V), z_dir=L.xyz(OUTWARD)))


def main() -> int:
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    shells = {}
    for tag, ka, kb in (("FINGER_V2", "JAD_FINGER_V2", "JFD_FINGER_V2"),
                        ("FROZEN", "JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB")):
        shells[tag] = combined_shell(ka, kb, box, tag)

    # ---------------- SECTION 2 -----------------------------------------
    loc = szh_location()
    ref, parts, moving_world, _ = build_reference()
    print("=== SECTION 2 : SZH-EK056 vs local_shell, both shells ===")
    print("%-28s %14s %14s %14s" % ("SZH feature", "vs FINGER_V2", "vs FROZEN", "difference"))
    rows = {}
    for name, shape in list(parts.items()) + [("MOVING_ENVELOPE_25deg", moving_world)]:
        s = shape.moved(loc)
        try:
            solid, _ = L.as_single_solid(s, name)
        except RuntimeError:
            continue
        a = L.inter_vol(solid, shells["FINGER_V2"])
        b = L.inter_vol(solid, shells["FROZEN"])
        rows[name] = {"vsFingerV2Mm3": a, "vsFrozenMm3": b, "differenceMm3": b - a}
        print("%-28s %14.4f %14.4f %14.4f" % (name[:28], a, b, b - a))
        del solid
    L.memory("szh both shells")

    docs71 = {"PCB": 69.457418 + 111.677457, "SHAFT": 5.275598 + 6.548519,
              "REMOVABLE_KNOB": 205.622099 + 216.485863,
              "HEADER_PLASTIC": 18.139294 + 51.767565}
    print("\ndocs/71 reported totals (JaD+JfD) vs this Lab's FINGER_V2 recomputation:")
    keymap = {"PCB": "pcb", "SHAFT": "shaft", "REMOVABLE_KNOB": "cap", "HEADER_PLASTIC": "header"}
    recheck = {}
    for dk, lk in keymap.items():
        if lk not in rows:
            continue
        recheck[dk] = {"docs71Mm3": docs71[dk], "labFingerV2Mm3": rows[lk]["vsFingerV2Mm3"],
                       "labFrozenMm3": rows[lk]["vsFrozenMm3"]}
        print("  %-16s docs71 %10.4f | lab FINGER_V2 %10.4f | lab FROZEN %10.4f"
              % (dk, docs71[dk], rows[lk]["vsFingerV2Mm3"], rows[lk]["vsFrozenMm3"]))

    changed = [k for k, v in rows.items() if abs(v["differenceMm3"]) > 1.0]
    print("\nfeatures whose shell intersection changes by more than 1 mm3: %d of %d"
          % (len(changed), len(rows)))
    for k in changed:
        print("   %-28s %+12.4f mm3" % (k, rows[k]["differenceMm3"]))
    L.write_json(OUT2 / "b06_docs71_recheck.json",
                 {"szhVsBothShells": rows, "docs71Comparison": recheck,
                  "featuresChangedOver1mm3": changed})

    # ---------------- SECTION 4 -----------------------------------------
    _, cartL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    _, cartO = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    Tf = L.triangles(shells["FROZEN"], tol=0.06, ang=0.12)
    Tv = L.triangles(shells["FINGER_V2"], tol=0.06, ang=0.12)

    print("\n\n=== SECTION 4 : cap position audit on the TRUE axis ===")
    caps = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        capL, _ = L.as_single_solid(cartL[label], short)
        capO, _ = L.as_single_solid(cartO[label], short + "_o")
        ax, _, tilt = true_axis(capL)
        pts = L.surf_points(capL, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        proj = (pts - cen) @ ax
        top_t = float(proj.max())
        top_pt = pts[np.argmax(proj)]
        pO = L.surf_points(capO, 20000, tol=0.05).mean(axis=0)

        row = {"axisWorld": ax.tolist(), "tiltFromJoystickAxisDeg": tilt,
               "capCentroidWorld": cen.tolist(),
               "capOutermostPointWorld": top_pt.tolist(),
               "originalCapCentroidWorld": pO.tolist(),
               "capCentroidLocal": L.to_local(cen)[0].tolist(),
               "originalCapCentroidLocal": L.to_local(pO)[0].tolist()}
        for tag, T in (("FROZEN", Tf), ("FINGER_V2", Tv)):
            iv = ray_intervals(T, cen, ax)
            e = {"allIntervalsMm": [list(x) for x in iv] if iv else None}
            if iv:
                # the Thumb wall = the outermost interval on this ray
                outer = max(iv, key=lambda p: p[1])
                e["wallInnerT"] = outer[0]
                e["wallOuterT"] = outer[1]
                e["wallThicknessMm"] = outer[1] - outer[0]
                e["capOutermostToInnerSkinMm"] = outer[0] - top_t
                e["capOutermostToOuterSkinMm"] = outer[1] - top_t
            row[tag] = e
        caps[short] = row
        del capL, capO
    print("%-5s %8s | %-34s | %-30s" % ("ctrl", "tilt", "FROZEN wall on axis (t from centroid)",
                                        "cap outermost -> skins"))
    for short in ORDER:
        r = caps[short]
        f = r["FROZEN"]
        if "wallInnerT" in f:
            print("%-5s %7.3f | inner %7.3f  outer %7.3f  t=%5.3f | to inner %+7.3f  to outer %+7.3f"
                  % (short, r["tiltFromJoystickAxisDeg"], f["wallInnerT"], f["wallOuterT"],
                     f["wallThicknessMm"], f["capOutermostToInnerSkinMm"],
                     f["capOutermostToOuterSkinMm"]))
        else:
            print("%-5s %7.3f | no material on this ray at all" % (short, r["tiltFromJoystickAxisDeg"]))

    print("\nsame ray, but through FINGER_V2 (the un-lowered Thumb shell):")
    for short in ORDER:
        f = caps[short]["FINGER_V2"]
        if "wallInnerT" in f:
            print("%-5s inner %7.3f  outer %7.3f  t=%5.3f | to inner %+7.3f  to outer %+7.3f"
                  % (short, f["wallInnerT"], f["wallOuterT"], f["wallThicknessMm"],
                     f["capOutermostToInnerSkinMm"], f["capOutermostToOuterSkinMm"]))
        else:
            print("%-5s no material on this ray at all" % short)

    L.write_json(OUT4 / "b06_cap_position_audit.json", {"controls": caps,
                                                        "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
