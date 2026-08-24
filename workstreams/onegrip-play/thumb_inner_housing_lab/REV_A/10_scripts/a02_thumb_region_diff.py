"""A02 - what changed on the shell in the Thumb region, and where.

Compares, inside one local Thumb crop box only (never a full-shell boolean):
   CLEAN_PRE_FINGER   original exterior, original Thumb position
   FINGER_V2          clean + finger-8 openings, Thumb NOT lowered
   LOWERED_THUMB      frozen exterior: finger-8 + lowered Thumb openings

Volumes come from A & B (well conditioned).  A - B between near coincident
solids is NOT trusted: OCC returns A whole (verified in this Lab, see report).
Localisation comes from a ray-parity occupancy grid instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import export_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402

OUT = L.LAB / "04_current_thumb_analysis"
COPIES = L.LAB / "02_reference_copies"

CROP_LO = (-30.0, -36.0, -34.0)
CROP_HI = (30.0, 30.0, 14.0)
PITCH = 0.75


def crop(key: str, box, label: str):
    full = L.load(key)
    sec = (full & box).clean()
    if not sec.solids():
        raise RuntimeError("empty crop for " + key)
    out, _ = L.as_single_solid(sec, label)
    n = len(list(sec.solids()))
    del full, sec
    L.memory("cropped " + key)
    return out, n


def main() -> int:
    L.assert_local_box(CROP_LO, CROP_HI)
    COPIES.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    box = L.local_box(CROP_LO, CROP_HI, "THUMB_LOCAL_CROP")
    export_step(box, str(COPIES / "THUMB_LOCAL_CROP_BOX.step"))

    keys = [("JAD_CLEAN_PRE_FINGER", "JAD_CLEAN"), ("JFD_CLEAN_PRE_FINGER", "JFD_CLEAN"),
            ("JAD_FINGER_V2", "JAD_FV2"), ("JFD_FINGER_V2", "JFD_FV2"),
            ("JAD_LOWERED_THUMB", "JAD_FROZEN"), ("JFD_LOWERED_THUMB", "JFD_FROZEN")]
    crops, rows = {}, {}
    for key, tag in keys:
        solid, nsolids = crop(key, box, tag + "_THUMB_CROP")
        crops[tag] = solid
        rows[tag] = {"source": key, "cropVolumeMm3": L.vol(solid), "cropSolids": nsolids}
        export_step(solid, str(COPIES / (tag + "_THUMB_CROP.step")))
        print("%-12s crop vol = %12.4f mm3  (solids: %d)" % (tag, L.vol(solid), nsolids))

    # ---- exact volumes via intersection only ------------------------------
    pairs = [("JAD_CLEAN", "JAD_FV2"), ("JAD_FV2", "JAD_FROZEN"), ("JAD_CLEAN", "JAD_FROZEN"),
             ("JFD_CLEAN", "JFD_FV2"), ("JFD_FV2", "JFD_FROZEN"), ("JFD_CLEAN", "JFD_FROZEN")]
    diffs = {}
    print("\n--- exact volumes from intersection (A-B is NOT used) ---")
    for a, b in pairs:
        va, vb = L.vol(crops[a]), L.vol(crops[b])
        vc = L.inter_vol(crops[a], crops[b])
        diffs[a + "->" + b] = {"volA": va, "volB": vb, "commonMm3": vc,
                               "onlyAMm3": va - vc, "onlyBMm3": vb - vc,
                               "symDiffMm3": (va - vc) + (vb - vc)}
        print("%-26s common=%12.4f  onlyA=%10.4f  onlyB=%10.4f"
              % (a + "->" + b, vc, va - vc, vb - vc))
        L.memory("common " + a + "->" + b)

    # ---- localisation via occupancy grid ----------------------------------
    U, V, N = L.grid_axes(CROP_LO, CROP_HI, PITCH)
    cell = PITCH ** 3
    occ = {}
    for tag in crops:
        occ[tag] = L.Occupancy(crops[tag]).inside(U, V, N)
        print("occupancy %-12s cells=%8d  approx vol=%12.3f mm3"
              % (tag, int(occ[tag].sum()), float(occ[tag].sum()) * cell))
        L.memory("occupancy " + tag)

    loc = {}
    for a, b in pairs:
        A, B = occ[a], occ[b]
        onlyA = A & ~B
        onlyB = B & ~A
        entry = {"onlyACells": int(onlyA.sum()), "onlyBCells": int(onlyB.sum()),
                 "onlyAApproxMm3": float(onlyA.sum()) * cell,
                 "onlyBApproxMm3": float(onlyB.sum()) * cell}
        for name, mask in (("onlyA", onlyA), ("onlyB", onlyB)):
            if mask.any():
                iu, iv, inn = np.nonzero(mask)
                entry[name + "LocalBbox"] = {
                    "u": [float(U[iu.min()]), float(U[iu.max()])],
                    "v": [float(V[iv.min()]), float(V[iv.max()])],
                    "n": [float(N[inn.min()]), float(N[inn.max()])]}
        loc[a + "->" + b] = entry
        print("\n%-26s onlyA=%7d cells (%9.2f mm3)  onlyB=%7d cells (%9.2f mm3)"
              % (a + "->" + b, entry["onlyACells"], entry["onlyAApproxMm3"],
                 entry["onlyBCells"], entry["onlyBApproxMm3"]))
        for name in ("onlyA", "onlyB"):
            k = name + "LocalBbox"
            if k in entry:
                bb = entry[k]
                print("   %-6s u[%7.2f,%7.2f] v[%7.2f,%7.2f] n[%7.2f,%7.2f]"
                      % (name, bb["u"][0], bb["u"][1], bb["v"][0], bb["v"][1],
                         bb["n"][0], bb["n"][1]))

    np.savez_compressed(OUT / "a02_occupancy.npz", U=U, V=V, N=N, pitch=PITCH,
                        **{k: v for k, v in occ.items()})
    L.write_json(OUT / "a02_thumb_region_diff.json",
                 {"cropLocal": {"min": list(CROP_LO), "max": list(CROP_HI)},
                  "gridPitchMm": PITCH, "crops": rows,
                  "exactIntersectionVolumes": diffs, "occupancyLocalisation": loc,
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
