"""B07 - (3) lineage of the approved exterior, and the visual-vs-exact check.

docs/53 says the exterior the user reviewed was a VISUAL COMPOSITE: the Thumb
region of the tessellation was replaced by a patch taken from a different
Onshape model (THUMB_LOWER15_HOUSING_V1), while the exact STEP pair was built
by a different route (fill the old openings, translate the old opening VOIDS,
re-cut, then cut 9 AABB service boxes).

If those two disagree in the Thumb region, then the file this Lab has been
calling "the frozen exterior" is not the geometric state that was approved.
That is one of the three possibilities the audit has to decide between, so it
is measured rather than assumed.

Reads STL with a local parser; no production module is executed.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import combined_shell  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, PITCH, WALL_BAND, clusters, wall_map  # noqa: E402

OUT = L.LAB / "03_lineage"
OUTWARD = -L.DATUM_N

VISUAL_STL = (L.ROOT / "build123d_workbench/out/integrated_exterior_lowered_thumb_v1"
              / "EXTERIOR_FIRST_LOWERED_THUMB_VISUAL_REFERENCE.stl")
LOWER15_JAD = (L.ROOT / "exports/thumb_lower15_housing_mockup"
               / "OneGrip_lower15_housing_Joystick_1_JaD.stl")
LOWER15_JFD = (L.ROOT / "exports/thumb_lower15_housing_mockup"
               / "OneGrip_lower15_housing_Joystick_2_JfD.stl")


def read_stl(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if data[:5] == b"solid" and b"facet" in data[:2048]:
        verts = []
        for line in data.decode("utf-8", "replace").splitlines():
            t = line.strip().split()
            if len(t) == 4 and t[0] == "vertex":
                verts.append([float(t[1]), float(t[2]), float(t[3])])
        return np.asarray(verts, float).reshape(-1, 3, 3)
    n = struct.unpack("<I", data[80:84])[0]
    arr = np.frombuffer(data, dtype=np.uint8, count=n * 50, offset=84).reshape(n, 50)
    f = arr[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(float)
    return f


def local_tris(T: np.ndarray) -> np.ndarray:
    return L.to_local(T.reshape(-1, 3)).reshape(-1, 3, 3)


def main() -> int:
    U = np.arange(-26.0, 26.0 + 1e-9, PITCH)
    V = np.arange(-52.0, 16.0 + 1e-9, PITCH)

    maps = {}

    # ---- exact frozen STEP ---------------------------------------------
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    Tf = L.local_triangles(frozen, tol=0.06, ang=0.12)
    maps["EXACT_FROZEN_STEP"] = wall_map(Tf, U, V, WALL_BAND)
    del frozen, Tf
    L.memory("exact frozen map")

    # ---- approved visual composite STL ---------------------------------
    for tag, paths in (("APPROVED_VISUAL_STL", [VISUAL_STL]),
                       ("LOWER15_HOUSING_STL", [LOWER15_JAD, LOWER15_JFD])):
        tris = []
        for p in paths:
            if not p.exists():
                print("  MISSING %s" % p)
                continue
            t = read_stl(p)
            print("  %-24s %-58s %8d triangles" % (tag, p.name[:58], len(t)))
            tris.append(t)
        if not tris:
            continue
        T = local_tris(np.concatenate(tris))
        maps[tag] = wall_map(T, U, V, WALL_BAND)
        del T
        L.memory("map " + tag)

    # ---- compare -------------------------------------------------------
    print("\n=== Thumb wall: holes found in each representation ===")
    rows = {}
    for tag, (thick, any_mat) in maps.items():
        holes = any_mat & (thick < 0.05)
        cl = clusters(holes, U, V)
        big = [c for c in cl if c["areaMm2"] >= 8.0]
        rows[tag] = {"clusterCount": len(cl), "significantClusters": len(big),
                     "clusters": cl[:14],
                     "mappedColumns": int(any_mat.sum()),
                     "meanWallMm": float(thick[any_mat].mean())}
        print("\n%-22s columns=%6d  meanWall=%6.3f  holes>=8mm2 = %d"
              % (tag, int(any_mat.sum()), float(thick[any_mat].mean()), len(big)))
        for k, c in enumerate(big[:10]):
            print("     #%-2d area=%7.2f  centroid (u,v)=(%7.2f,%7.2f)"
                  % (k, c["areaMm2"], c["centroidUV"][0], c["centroidUV"][1]))

    # direct per-column agreement between exact STEP and approved visual
    if "APPROVED_VISUAL_STL" in maps:
        te, ae = maps["EXACT_FROZEN_STEP"]
        tv, av = maps["APPROVED_VISUAL_STL"]
        both = ae & av
        oe = te < 0.05
        ov = tv < 0.05
        agree = float((oe[both] == ov[both]).mean())
        only_exact = int((oe & ~ov & both).sum())
        only_vis = int((ov & ~oe & both).sum())
        print("\n=== EXACT STEP vs APPROVED VISUAL, per column ===")
        print("  columns mapped in both              : %d" % int(both.sum()))
        print("  open/closed agreement               : %.2f %%" % (100 * agree))
        print("  open ONLY in the exact STEP         : %d columns (%.2f mm2)"
              % (only_exact, only_exact * PITCH * PITCH))
        print("  open ONLY in the approved visual    : %d columns (%.2f mm2)"
              % (only_vis, only_vis * PITCH * PITCH))
        print("  mean wall  exact %.3f mm | visual %.3f mm"
              % (float(te[both].mean()), float(tv[both].mean())))
        rows["exactVsVisual"] = {"columnsBoth": int(both.sum()), "agreementFraction": agree,
                                 "openOnlyInExactColumns": only_exact,
                                 "openOnlyInVisualColumns": only_vis,
                                 "openOnlyInExactMm2": only_exact * PITCH * PITCH,
                                 "openOnlyInVisualMm2": only_vis * PITCH * PITCH,
                                 "meanWallExactMm": float(te[both].mean()),
                                 "meanWallVisualMm": float(tv[both].mean())}
        np.savez_compressed(OUT / "b07_maps.npz", U=U, V=V,
                            exact_thick=te, exact_mat=ae,
                            visual_thick=tv, visual_mat=av)

    L.write_json(OUT / "b07_lineage_and_visual.json", {"maps": rows, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
