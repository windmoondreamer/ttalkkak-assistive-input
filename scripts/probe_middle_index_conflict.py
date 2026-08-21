"""Lower-bound probe for the frozen INDEX/MIDDLE spatial conflict.

Local-only diagnostic.  It asks whether each MIDDLE pocket or full holder can
individually avoid the frozen INDEX holders/RWID/RZKD at the fixed Z=-6 centre,
before pairwise MIDDLE SAT constraints are even imposed.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_middle_prewrite as geom  # noqa: E402


def main() -> None:
    audit = json.loads((ROOT / "cad_dump" / "middle_prewrite_axis_optimization.json").read_text(encoding="utf-8"))
    points = np.asarray([audit["centers"][name] for name in geom.NAMES])
    normals = np.asarray([audit["normals"][name] for name in geom.NAMES])
    rwid = geom.load_triangles("INDEX_FINAL_RWID")
    rzkd = geom.load_triangles("INDEX_FINAL_RZKD")
    index_holders = [
        geom.obb(
            geom.INDEX_CENTERS[i], geom.unit(geom.INDEX_AXES[i]), geom.HOLDER_WIDTH,
            geom.HOLDER_TO - geom.HOLDER_FROM, geom.HOLDER_FROM,
        )
        for i in range(4)
    ]
    front = 5.3
    rng = np.random.default_rng(271828)
    results = {}

    samples = 5_000
    for i, name in enumerate(geom.NAMES):
        local = geom.frame(normals[i])
        best_pocket = None
        best_holder = None
        safe_pocket_count = 0
        safe_holder_count = 0
        for _ in range(samples):
            angle = math.radians(rng.uniform(0.0, 70.0))
            phi = rng.uniform(0.0, 2.0 * math.pi)
            axis = geom.unit(
                local[2]
                + math.tan(angle) * math.cos(phi) * local[0]
                + math.tan(angle) * math.sin(phi) * local[1]
            )
            pocket = geom.obb(points[i], axis, geom.POCKET, geom.SWITCH + 0.2, front)
            holder = geom.obb(
                points[i], axis, geom.HOLDER_WIDTH,
                geom.HOLDER_TO - geom.HOLDER_FROM, geom.HOLDER_FROM,
            )
            px = geom.corners(pocket)[:, 0]
            split_ok = True
            if i == 2:
                split_ok = -float(px.max()) >= 1.5
            elif i == 3:
                split_ok = float(px.min()) >= 1.5
            lip_ok = geom.lip_min(points[i], normals[i], axis, front) >= 0.5
            if not (split_ok and lip_ok):
                continue
            pocket_safe = (
                not geom.mesh_box_intersects(rwid, pocket)
                and not geom.mesh_box_intersects(rzkd, pocket)
                and all(geom.sat_signed(pocket, other) > 0.0 for other in index_holders)
            )
            if pocket_safe:
                safe_pocket_count += 1
                if best_pocket is None or angle < best_pocket[0]:
                    best_pocket = (angle, axis.copy())
            holder_safe = (
                pocket_safe
                and not geom.mesh_box_intersects(rwid, holder)
                and not geom.mesh_box_intersects(rzkd, holder)
                and all(geom.sat_signed(holder, other) > 0.0 for other in index_holders)
            )
            if holder_safe:
                safe_holder_count += 1
                if best_holder is None or angle < best_holder[0]:
                    best_holder = (angle, axis.copy())
        results[name] = {
            "samples": samples,
            "safePocketSamples": safe_pocket_count,
            "minimumIndividualPocketDeviationDeg": (
                math.degrees(best_pocket[0]) if best_pocket else None
            ),
            "minimumIndividualPocketAxis": best_pocket[1].tolist() if best_pocket else None,
            "safeHolderSamples": safe_holder_count,
            "minimumIndividualHolderDeviationDeg": (
                math.degrees(best_holder[0]) if best_holder else None
            ),
            "minimumIndividualHolderAxis": best_holder[1].tolist() if best_holder else None,
        }
        print(name, results[name], flush=True)

    selected_axes = np.asarray([audit["optimizedAxes"][name] for name in geom.NAMES])
    selected = {}
    for i, name in enumerate(geom.NAMES):
        switch = geom.obb(points[i], selected_axes[i], geom.SWITCH, geom.SWITCH, front)
        pocket = geom.obb(points[i], selected_axes[i], geom.POCKET, geom.SWITCH + 0.2, front)
        holder = geom.obb(
            points[i], selected_axes[i], geom.HOLDER_WIDTH,
            geom.HOLDER_TO - geom.HOLDER_FROM, geom.HOLDER_FROM,
        )
        selected[name] = {
            "switchToRWIDmm": geom.mesh_box_distance(rwid, switch),
            "pocketToRWIDmm": geom.mesh_box_distance(rwid, pocket),
            "holderToRWIDmm": geom.mesh_box_distance(rwid, holder),
            "switchToRZKDmm": geom.mesh_box_distance(rzkd, switch),
            "pocketToRZKDmm": geom.mesh_box_distance(rzkd, pocket),
            "holderToRZKDmm": geom.mesh_box_distance(rzkd, holder),
            "switchToIndexHolderMm": min(geom.box_distance(switch, other) for other in index_holders),
            "pocketToIndexHolderMm": min(geom.box_distance(pocket, other) for other in index_holders),
            "holderToIndexHolderMm": min(geom.box_distance(holder, other) for other in index_holders),
        }

    vertical_shift = {}
    for shift in range(0, -11, -1):
        holder_rwid = []
        holder_index = []
        for i in range(4):
            holder = geom.obb(
                points[i] + np.asarray((0.0, 0.0, float(shift))), selected_axes[i],
                geom.HOLDER_WIDTH, geom.HOLDER_TO - geom.HOLDER_FROM, geom.HOLDER_FROM,
            )
            holder_rwid.append(geom.mesh_box_distance(rwid, holder))
            holder_index.append(min(geom.box_distance(holder, other) for other in index_holders))
        vertical_shift[str(shift)] = {
            "holderToRWIDmm": holder_rwid,
            "holderToIndexHolderMm": holder_index,
        }

    payload = {
        "method": "local exact triangle/OBB SAT; no network; no CAD write",
        "individualAxisProbe": results,
        "selectedCandidateClearance": selected,
        "uniformNegativeZShiftProbe": vertical_shift,
    }
    output = ROOT / "cad_dump" / "middle_index_conflict_probe.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
