"""Independent-axis pool optimization for re-seated MIDDLE row candidates.

For each fixed row translation, every retained axis already satisfies the
frozen INDEX switch/pocket/full-holder keep-out, split, lip and screw gates.
The pool combination solver then enforces the exact MIDDLE pair SAT/divider
constraints and minimizes maximum local-normal deviation.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_middle_prewrite as geom  # noqa: E402
import search_middle_joint as rigid  # noqa: E402


FRONT = 5.3
SAMPLES = 3_000
POOL_LIMIT = 320


def safe_axis_pool(index, point, normal, forbidden, transferred, seed):
    rng = np.random.default_rng(seed)
    local = geom.frame(normal)
    raw = [(transferred, math.degrees(math.acos(np.clip(float(np.dot(normal, transferred)), -1, 1))))]
    # Low-angle-biased global cap, plus a uniform tail to avoid missing narrow high-angle windows.
    for sample in range(SAMPLES):
        fraction = rng.random()
        angle_deg = 70.0 * (fraction ** 2 if sample < SAMPLES * 0.75 else fraction)
        angle = math.radians(angle_deg)
        phi = rng.uniform(0.0, 2.0 * math.pi)
        axis = geom.unit(
            local[2]
            + math.tan(angle) * math.cos(phi) * local[0]
            + math.tan(angle) * math.sin(phi) * local[1]
        )
        raw.append((axis, angle_deg))

    accepted = []
    for axis, deviation in raw:
        pocket = geom.obb(point, axis, geom.POCKET, geom.SWITCH + 0.2, FRONT)
        px = geom.corners(pocket)[:, 0]
        if index == 2 and -float(px.max()) < 1.5 - 1e-9:
            continue
        if index == 3 and float(px.min()) < 1.5 - 1e-9:
            continue
        if geom.lip_min(point, normal, axis, FRONT) < 0.5 - 1e-9:
            continue
        holder = geom.obb(
            point, axis, geom.HOLDER_WIDTH,
            geom.HOLDER_TO - geom.HOLDER_FROM, geom.HOLDER_FROM,
        )
        screw = min(
            geom.cylinder_gap_x(holder, np.asarray(screw_point), x_range, radius)
            for screw_point, x_range, radius in geom.SCREWS.values()
        )
        if screw < 2.5 - 1e-9:
            continue
        if geom.mesh_box_intersects(forbidden, holder):
            continue
        accepted.append((deviation, axis, screw))

    accepted.sort(key=lambda row: row[0])
    if len(accepted) <= POOL_LIMIT:
        selected = accepted
    else:
        # Keep low-deviation solutions plus coverage of the tail for pair compatibility.
        low = accepted[: int(POOL_LIMIT * 0.75)]
        tail_indices = np.linspace(int(POOL_LIMIT * 0.75), len(accepted) - 1, POOL_LIMIT - len(low), dtype=int)
        selected = low + [accepted[i] for i in tail_indices]
        selected.sort(key=lambda row: row[0])
    return {
        "sampleCount": len(raw),
        "safeCount": len(accepted),
        "axes": np.asarray([row[1] for row in selected]),
        "deviations": np.asarray([row[0] for row in selected]),
        "screws": np.asarray([row[2] for row in selected]),
    }


def compatibility(pool_a, pool_b, point_a, point_b, need_divider=True):
    axes_a, axes_b = pool_a["axes"], pool_b["axes"]
    matrix = np.zeros((len(axes_a), len(axes_b)), dtype=bool)
    switch_a = [geom.obb(point_a, axis, geom.SWITCH, geom.SWITCH, FRONT) for axis in axes_a]
    pocket_a = [geom.obb(point_a, axis, geom.POCKET, geom.SWITCH + 0.2, FRONT) for axis in axes_a]
    switch_b = [geom.obb(point_b, axis, geom.SWITCH, geom.SWITCH, FRONT) for axis in axes_b]
    pocket_b = [geom.obb(point_b, axis, geom.POCKET, geom.SWITCH + 0.2, FRONT) for axis in axes_b]
    for i in range(len(axes_a)):
        for j in range(len(axes_b)):
            if geom.sat_signed(switch_a[i], switch_b[j]) < 1.2 - 1e-9:
                continue
            if need_divider and geom.sat_signed(pocket_a[i], pocket_b[j]) < 0.8 - 1e-9:
                continue
            matrix[i, j] = True
    return matrix


def solve_combination(points, pools):
    if any(len(pool["axes"]) == 0 for pool in pools):
        return None, {"reason": "one or more buttons have no individually INDEX-safe full-holder axis"}
    c12 = compatibility(pools[0], pools[1], points[0], points[1], True)
    c23 = compatibility(pools[1], pools[2], points[1], points[2], True)
    c13 = compatibility(pools[0], pools[2], points[0], points[2], False)
    c34 = compatibility(pools[2], pools[3], points[2], points[3], True)
    best = None
    for i2, i3 in np.argwhere(c23):
        valid1 = np.flatnonzero(c12[:, i2] & c13[:, i3])
        valid4 = np.flatnonzero(c34[i3, :])
        if len(valid1) == 0 or len(valid4) == 0:
            continue
        i1, i4 = int(valid1[0]), int(valid4[0])
        indices = (i1, int(i2), int(i3), i4)
        deviations = [float(pools[i]["deviations"][indices[i]]) for i in range(4)]
        key = (max(deviations), sum(deviations))
        if best is None or key < best[0]:
            axes = np.asarray([pools[i]["axes"][indices[i]] for i in range(4)])
            best = (key, indices, axes, deviations)
    stats = {
        "compatible12": int(c12.sum()),
        "compatible23": int(c23.sum()),
        "compatible13": int(c13.sum()),
        "compatible34": int(c34.sum()),
    }
    if best is None:
        return None, {**stats, "reason": "no compatible four-axis combination in safe pools"}
    return {"indices": best[1], "axes": best[2], "deviationsDeg": best[3]}, stats


def solve_translation(
    translation, nominal_points, nominal_normals, tangent, projector, forbidden,
    tangential_correction=None, longitudinal_correction=None,
):
    translation = np.asarray(translation, float)
    derived = [projector.project(nominal_points[i] + translation) for i in range(4)]
    points = np.asarray([row[0] for row in derived])
    normals = np.asarray([row[1] for row in derived])
    tangential_correction = np.zeros(4) if tangential_correction is None else np.asarray(tangential_correction, float)
    longitudinal_correction = np.zeros(4) if longitudinal_correction is None else np.asarray(longitudinal_correction, float)
    if np.any(tangential_correction) or np.any(longitudinal_correction):
        corrected = []
        for i in range(4):
            tangent_direction = geom.unit(np.asarray((-normals[i, 1], normals[i, 0], 0.0)))
            target = (
                points[i]
                + tangent_direction * tangential_correction[i]
                + np.asarray((0.0, 0.0, longitudinal_correction[i]))
            )
            corrected.append(projector.project(target))
        points = np.asarray([row[0] for row in corrected])
        normals = np.asarray([row[1] for row in corrected])
    transferred = np.asarray([rigid.transferred_axis(normals[i], tangent[i]) for i in range(4)])
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(
                safe_axis_pool, i, points[i], normals[i], forbidden, transferred[i],
                91001 + i * 1009 + int((translation[0] + 5) * 31 + (translation[1] + 7) * 47 + (translation[2] + 9) * 59),
            )
            for i in range(4)
        ]
        pools = [future.result() for future in futures]
    solution, compatibility_stats = solve_combination(points, pools)
    pitch = [float(np.linalg.norm(points[i + 1] - points[i])) for i in range(3)]
    row = {
        "translationMm": translation.tolist(),
        "translationNormMm": float(np.linalg.norm(translation)),
        "tangentialCorrectionMm": tangential_correction.tolist(),
        "longitudinalCorrectionMm": longitudinal_correction.tolist(),
        "perButtonDisplacementMm": [
            float(np.linalg.norm(points[i] - nominal_points[i])) for i in range(4)
        ],
        "points": points.tolist(),
        "normals": normals.tolist(),
        "pitchMm": pitch,
        "poolStats": [
            {
                "sampleCount": pool["sampleCount"],
                "safeCount": pool["safeCount"],
                "retainedCount": len(pool["axes"]),
                "minimumSafeDeviationDeg": float(pool["deviations"][0]) if len(pool["deviations"]) else None,
            }
            for pool in pools
        ],
        "compatibility": compatibility_stats,
        "pitchGate": all(10.5 - 1e-9 <= value <= 11.5 + 1e-9 for value in pitch),
    }
    if solution is None:
        return {**row, "axisSolution": None, "feasible": False}
    axes = solution["axes"]
    forbidden_parts = [
        geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"),
        geom.load_triangles("INDEX_FINAL_RWID"),
        geom.load_triangles("INDEX_FINAL_RZKD"),
    ]
    detail = rigid.evaluate(points, normals, axes, forbidden_parts, exact_clearance=True)
    return {
        **row,
        "axisSolution": {
            "axes": axes.tolist(),
            "deviationsDeg": solution["deviationsDeg"],
        },
        "detail": detail,
        "feasible": row["pitchGate"] and detail["feasible"],
    }


def main() -> None:
    prior = json.loads((ROOT / "cad_dump" / "middle_prewrite_axis_optimization.json").read_text(encoding="utf-8"))
    nominal_points = np.asarray([prior["centers"][name] for name in geom.NAMES])
    nominal_normals = np.asarray([prior["normals"][name] for name in geom.NAMES])
    prior_axes = np.asarray([prior["optimizedAxes"][name] for name in geom.NAMES])
    tangent = np.asarray([rigid.tangent_parameters(nominal_normals[i], prior_axes[i]) for i in range(4)])
    projector = rigid.SurfaceProjector()
    forbidden = np.concatenate(
        [
            geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"),
            geom.load_triangles("INDEX_FINAL_RWID"),
            geom.load_triangles("INDEX_FINAL_RZKD"),
        ],
        axis=0,
    )
    cases = [
        ((0.5, 4.25, -6.25), (-0.9, -0.3, 0.3, 0.9), (0, -3.0, 0, 0)),
        ((0.5, 4.5, -6.5), (-0.9, -0.3, 0.3, 0.9), (0, -3.0, 0, 0)),
        ((0.5, 4.75, -6.75), (-0.9, -0.3, 0.3, 0.9), (0, -3.0, 0, 0)),
    ]
    results = []
    for translation, tangent_correction, z_correction in cases:
        print("solve", translation, "tc", tangent_correction, flush=True)
        result = solve_translation(
            translation, nominal_points, nominal_normals, tangent, projector, forbidden,
            tangent_correction, z_correction,
        )
        results.append(result)
        print(
            " ->", "feasible", result["feasible"], "pitch", [round(v, 3) for v in result["pitchMm"]],
            "safe", [row["safeCount"] for row in result["poolStats"]],
            "minDev", [None if row["minimumSafeDeviationDeg"] is None else round(row["minimumSafeDeviationDeg"], 2) for row in result["poolStats"]],
            "combo", result["axisSolution"] is not None,
            flush=True,
        )
    path = ROOT / "cad_dump" / "middle_joint_axis_rows.json"
    path.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
