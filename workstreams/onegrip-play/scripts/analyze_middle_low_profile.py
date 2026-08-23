"""READ-ONLY low-profile MIDDLE switch envelope feasibility analysis.

This script performs local geometry computation only.  It has no Onshape
client, no HTTP mutation path, and consumes the frozen tessellation caches
already audited for INDEX_FINAL_VALIDATED.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_middle_prewrite as geom  # noqa: E402
import search_middle_joint as prior_search  # noqa: E402


FOOTPRINT = 6.0
POCKET = 6.4
SHELL_WALL = 3.0
TRIM_DEPTH = 2.8
REAR_RETENTION = 1.2
HOLDER_WIDTH = 12.4
HEIGHTS = (6.0, 5.0, 4.3, 3.5, 3.1)
TARGETS = (0.5, 0.8, 1.0)
NAMES = geom.NAMES


def load_json(name: str):
    return json.loads((ROOT / "cad_dump" / name).read_text(encoding="utf-8"))


def front_depth(front_lip: float) -> float:
    return SHELL_WALL + front_lip


def holder_rear(height: float, front_lip: float) -> float:
    """Minimum rear datum retaining the audited 1.2 mm rear land."""
    return front_depth(front_lip) + height + REAR_RETENTION


def make_boxes(point, axis, height: float, front_lip: float):
    front = front_depth(front_lip)
    rear = holder_rear(height, front_lip)
    return {
        "switch": geom.obb(point, axis, FOOTPRINT, height, front),
        "pocket": geom.obb(point, axis, POCKET, height + 0.2, front),
        "holder": geom.obb(point, axis, HOLDER_WIDTH, rear - TRIM_DEPTH, TRIM_DEPTH),
    }


def expanded_holder(point, axis, height: float, front_lip: float, margin: float):
    rear = holder_rear(height, front_lip)
    return geom.obb(
        point,
        axis,
        HOLDER_WIDTH + 2.0 * margin,
        rear - TRIM_DEPTH + 2.0 * margin,
        TRIM_DEPTH - margin,
    )


def lip_min(point, normal, axis, front_lip: float) -> float:
    front = front_depth(front_lip)
    u, v, z = geom.frame(axis)
    return min(
        -float(np.dot(point - z * front + u * x + v * y - point, normal)) - TRIM_DEPTH
        for x in (-FOOTPRINT / 2.0, FOOTPRINT / 2.0)
        for y in (-FOOTPRINT / 2.0, FOOTPRINT / 2.0)
    )


def required_front_lip(normal, axis, minimum_actual: float = 0.5) -> float:
    """Solve the affine front-lip inequality exactly for a fixed axis."""
    u, v, z = geom.frame(axis)
    cosine = float(np.dot(z, normal))
    corner_loss = FOOTPRINT / 2.0 * (
        abs(float(np.dot(u, normal))) + abs(float(np.dot(v, normal)))
    )
    required_front = (TRIM_DEPTH + minimum_actual + corner_loss) / cosine
    return required_front - SHELL_WALL


def split_walls(pocket_boxes):
    p3x = geom.corners(pocket_boxes[2])[:, 0]
    p4x = geom.corners(pocket_boxes[3])[:, 0]
    return (-float(p3x.max()), float(p4x.min()))


def screw_clearances(holder_boxes):
    return [
        min(
            geom.cylinder_gap_x(box, np.asarray(point), x_range, radius)
            for point, x_range, radius in geom.SCREWS.values()
        )
        for box in holder_boxes
    ]


def exact_component_clearance(points, axes, height: float, front_lip: float, components):
    per_button = {}
    global_min = (float("inf"), None, None, None)
    collision_count = 0
    for i, name in enumerate(NAMES):
        rows = {}
        for envelope, box in make_boxes(points[i], axes[i], height, front_lip).items():
            rows[envelope] = {}
            for component, triangles in components.items():
                hit = geom.mesh_box_intersects(triangles, box)
                distance = 0.0 if hit else geom.mesh_box_distance(triangles, box)
                collision_count += int(hit)
                rows[envelope][component] = {
                    "collision": bool(hit),
                    "clearanceMm": float(distance),
                }
                if distance < global_min[0]:
                    global_min = (distance, name, envelope, component)
        per_button[name] = rows
    return {
        "perButton": per_button,
        "collisionCount": collision_count,
        "globalMinimum": {
            "clearanceMm": float(global_min[0]),
            "button": global_min[1],
            "envelope": global_min[2],
            "component": global_min[3],
        },
    }


def cap_pair_clearance(points, normals):
    caps = [geom.obb(points[i], normals[i], 8.0, 0.2, -0.1) for i in range(4)]
    return [geom.sat_signed(caps[i], caps[i + 1]) for i in range(3)]


def evaluate_candidate(points, normals, axes, height: float, front_lip: float, components):
    all_boxes = [make_boxes(points[i], axes[i], height, front_lip) for i in range(4)]
    switches = [row["switch"] for row in all_boxes]
    pockets = [row["pocket"] for row in all_boxes]
    holders = [row["holder"] for row in all_boxes]
    switch_sat = [geom.sat_signed(switches[i], switches[j]) for i, j in geom.KEY_PAIRS]
    dividers = [geom.sat_signed(pockets[i], pockets[j]) for i, j in geom.ADJ_PAIRS]
    split = split_walls(pockets)
    screws = screw_clearances(holders)
    lips = [lip_min(points[i], normals[i], axes[i], front_lip) for i in range(4)]
    pitch = [float(np.linalg.norm(points[i + 1] - points[i])) for i in range(3)]
    cap_gap = cap_pair_clearance(points, normals)
    clearance = exact_component_clearance(points, axes, height, front_lip, components)
    deviations = [
        math.degrees(math.acos(np.clip(float(np.dot(normals[i], axes[i])), -1.0, 1.0)))
        for i in range(4)
    ]
    hard = bool(
        min(switch_sat) >= 1.2 - 1e-8
        and min(dividers) >= 0.8 - 1e-8
        and min(split) >= 1.5 - 1e-8
        and min(screws) >= 2.5 - 1e-8
        and min(lips) >= 0.5 - 1e-8
        and min(pitch) >= 10.5 - 1e-8
        and max(pitch) <= 11.5 + 1e-8
        and min(cap_gap) > 0.0
        and clearance["collisionCount"] == 0
    )
    return {
        "switchSatMm": [float(v) for v in switch_sat],
        "dividerMm": [float(v) for v in dividers],
        "splitWallMm": [float(v) for v in split],
        "screwMm": [float(v) for v in screws],
        "actualFrontLipMm": [float(v) for v in lips],
        "pitchMm": pitch,
        "capPairClearanceMm": [float(v) for v in cap_gap],
        "deviationsDeg": deviations,
        "maxDeviationDeg": max(deviations),
        "indexClearance": clearance,
        "hardGatesWithoutRobustTarget": hard,
    }


def robust_axis_pool(
    button_index,
    point,
    normal,
    height: float,
    front_lip: float,
    target: float,
    forbidden,
    transferred,
    seed_axes,
    seed: int,
    sample_count: int,
    pool_limit: int,
):
    """Build axes safe against a conservative target-expanded full holder."""
    rng = np.random.default_rng(seed)
    local = geom.frame(normal)
    raw = [geom.unit(normal), geom.unit(transferred)]
    raw.extend(geom.unit(axis) for axis in seed_axes)
    # Low-angle bias plus a uniform tail.  A deterministic local cloud around
    # prior solutions makes the rerun reproducible without assuming those axes
    # remain optimal for a new height.
    for axis in list(raw):
        params = prior_search.tangent_parameters(normal, axis)
        for _ in range(max(20, sample_count // max(1, 8 * len(raw)))):
            raw.append(geom.axis_from_tangent(normal, params + rng.normal(0.0, 0.09, 2)))
    while len(raw) < sample_count:
        fraction = rng.random()
        angle_deg = 58.0 * (fraction ** 2 if len(raw) < sample_count * 0.8 else fraction)
        angle = math.radians(angle_deg)
        phi = rng.uniform(0.0, 2.0 * math.pi)
        raw.append(
            geom.unit(
                local[2]
                + math.tan(angle) * math.cos(phi) * local[0]
                + math.tan(angle) * math.sin(phi) * local[1]
            )
        )

    accepted = []
    for axis in raw[:sample_count]:
        deviation = math.degrees(
            math.acos(np.clip(float(np.dot(normal, axis)), -1.0, 1.0))
        )
        boxes = make_boxes(point, axis, height, front_lip)
        px = geom.corners(boxes["pocket"])[:, 0]
        if button_index == 2 and -float(px.max()) < 1.5 - 1e-9:
            continue
        if button_index == 3 and float(px.min()) < 1.5 - 1e-9:
            continue
        if lip_min(point, normal, axis, front_lip) < 0.5 - 1e-9:
            continue
        screw = min(
            geom.cylinder_gap_x(boxes["holder"], np.asarray(screw_point), x_range, radius)
            for screw_point, x_range, radius in geom.SCREWS.values()
        )
        if screw < 2.5 - 1e-9:
            continue
        # A half-target local expansion is a conservative broad-phase relative
        # to raw non-intersection.  The exact triangle-to-OBB Euclidean target
        # is authoritative after the four-axis combination is selected.
        if geom.mesh_box_intersects(
            forbidden,
            expanded_holder(point, axis, height, front_lip, target * 0.5),
        ):
            continue
        accepted.append((deviation, axis, screw))

    accepted.sort(key=lambda row: row[0])
    if len(accepted) <= pool_limit:
        selected = accepted
    else:
        low_count = int(pool_limit * 0.75)
        low = accepted[:low_count]
        tail_indices = np.linspace(
            low_count, len(accepted) - 1, pool_limit - low_count, dtype=int
        )
        selected = low + [accepted[i] for i in tail_indices]
        selected.sort(key=lambda row: row[0])
    return {
        "sampleCount": sample_count,
        "safeCount": len(accepted),
        "axes": np.asarray([row[1] for row in selected]),
        "deviations": np.asarray([row[0] for row in selected]),
        "screws": np.asarray([row[2] for row in selected]),
    }


def pair_compatibility(pool_a, pool_b, point_a, point_b, height, front_lip, divider):
    axes_a, axes_b = pool_a["axes"], pool_b["axes"]
    matrix = np.zeros((len(axes_a), len(axes_b)), dtype=bool)
    switch_a = [make_boxes(point_a, axis, height, front_lip)["switch"] for axis in axes_a]
    pocket_a = [make_boxes(point_a, axis, height, front_lip)["pocket"] for axis in axes_a]
    switch_b = [make_boxes(point_b, axis, height, front_lip)["switch"] for axis in axes_b]
    pocket_b = [make_boxes(point_b, axis, height, front_lip)["pocket"] for axis in axes_b]
    for i in range(len(axes_a)):
        for j in range(len(axes_b)):
            if geom.sat_signed(switch_a[i], switch_b[j]) < 1.2 - 1e-9:
                continue
            if divider and geom.sat_signed(pocket_a[i], pocket_b[j]) < 0.8 - 1e-9:
                continue
            matrix[i, j] = True
    return matrix


def choose_axis_combination(points, pools, height, front_lip):
    if any(len(pool["axes"]) == 0 for pool in pools):
        return None, {"reason": "one or more buttons have no robust-safe axis"}
    c12 = pair_compatibility(pools[0], pools[1], points[0], points[1], height, front_lip, True)
    c23 = pair_compatibility(pools[1], pools[2], points[1], points[2], height, front_lip, True)
    c13 = pair_compatibility(pools[0], pools[2], points[0], points[2], height, front_lip, False)
    c34 = pair_compatibility(pools[2], pools[3], points[2], points[3], height, front_lip, True)
    best = None
    for i2, i3 in np.argwhere(c23):
        valid1 = np.flatnonzero(c12[:, i2] & c13[:, i3])
        valid4 = np.flatnonzero(c34[i3, :])
        if not len(valid1) or not len(valid4):
            continue
        # Pools are sorted by local deviation, so the first valid endpoint is
        # the minimax-optimal endpoint for this central pair.
        indices = (int(valid1[0]), int(i2), int(i3), int(valid4[0]))
        deviations = [float(pools[i]["deviations"][indices[i]]) for i in range(4)]
        key = (max(deviations), sum(deviations))
        if best is None or key < best[0]:
            best = (key, indices, deviations)
    stats = {
        "compatible12": int(c12.sum()),
        "compatible23": int(c23.sum()),
        "compatible13": int(c13.sum()),
        "compatible34": int(c34.sum()),
    }
    if best is None:
        return None, {**stats, "reason": "no four-axis compatible combination"}
    axes = np.asarray([pools[i]["axes"][best[1][i]] for i in range(4)])
    return {"axes": axes, "deviationsDeg": best[2], "indices": best[1]}, stats


def corrected_row(projector, nominal_points, translation, tangent_correction, z_correction):
    translation = np.asarray(translation, float)
    derived = [projector.project(nominal_points[i] + translation) for i in range(4)]
    points = np.asarray([row[0] for row in derived])
    normals = np.asarray([row[1] for row in derived])
    corrected = []
    for i in range(4):
        tangent_direction = geom.unit(np.asarray((-normals[i, 1], normals[i, 0], 0.0)))
        target = (
            points[i]
            + tangent_direction * tangent_correction[i]
            + np.asarray((0.0, 0.0, z_correction[i]))
        )
        corrected.append(projector.project(target))
    return (
        np.asarray([row[0] for row in corrected]),
        np.asarray([row[1] for row in corrected]),
    )


def solve_case(
    height,
    front_lip,
    target,
    translation,
    tangent_correction,
    z_correction,
    sample_count=1000,
    pool_limit=100,
    extra_seed_files=(),
):
    prior = load_json("middle_prewrite_axis_optimization.json")
    options = load_json("middle_center_axis_joint_optimization.json")["options"]
    nominal_points = np.asarray([prior["centers"][name] for name in NAMES])
    nominal_normals = np.asarray([prior["normals"][name] for name in NAMES])
    prior_axes = np.asarray([prior["optimizedAxes"][name] for name in NAMES])
    tangent = np.asarray(
        [prior_search.tangent_parameters(nominal_normals[i], prior_axes[i]) for i in range(4)]
    )
    seed_axes_by_button = [
        [np.asarray(options[label]["axes"][NAMES[i]], float) for label in ("A", "B", "C")]
        + [prior_axes[i]]
        for i in range(4)
    ]
    for seed_file in extra_seed_files:
        seed_payload = json.loads(Path(seed_file).read_text(encoding="utf-8"))
        if not seed_payload.get("axisSolution"):
            continue
        for i, name in enumerate(NAMES):
            seed_axes_by_button[i].append(
                np.asarray(seed_payload["axisSolution"]["axes"][name], float)
            )
    projector = prior_search.SurfaceProjector()
    points, normals = corrected_row(
        projector,
        nominal_points,
        np.asarray(translation, float),
        np.asarray(tangent_correction, float),
        np.asarray(z_correction, float),
    )
    transferred = np.asarray(
        [prior_search.transferred_axis(normals[i], tangent[i]) for i in range(4)]
    )
    components = {
        "frozenShellIndexSurface": geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"),
        "RWID": geom.load_triangles("INDEX_FINAL_RWID"),
        "RZKD": geom.load_triangles("INDEX_FINAL_RZKD"),
    }
    forbidden = np.concatenate(list(components.values()), axis=0)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(
                robust_axis_pool,
                i,
                points[i],
                normals[i],
                height,
                front_lip,
                target,
                forbidden,
                transferred[i],
                seed_axes_by_button[i],
                290003 + i * 1009 + int(height * 100) + int(target * 1000)
                + int((translation[0] + 5) * 31 + (translation[1] + 7) * 47 + (translation[2] + 9) * 59),
                sample_count,
                pool_limit,
            )
            for i in range(4)
        ]
        pools = [future.result() for future in futures]
    solution, compatibility = choose_axis_combination(points, pools, height, front_lip)
    pitch = [float(np.linalg.norm(points[i + 1] - points[i])) for i in range(3)]
    result = {
        "heightMm": height,
        "frontLipSearchMm": front_lip,
        "robustTargetMm": target,
        "translationMm": list(translation),
        "translationNormMm": float(np.linalg.norm(translation)),
        "tangentialCorrectionMm": list(tangent_correction),
        "longitudinalCorrectionMm": list(z_correction),
        "centers": {NAMES[i]: points[i].tolist() for i in range(4)},
        "surfaceNormals": {NAMES[i]: normals[i].tolist() for i in range(4)},
        "perButtonDisplacementMm": [
            float(np.linalg.norm(points[i] - nominal_points[i])) for i in range(4)
        ],
        "pitchMm": pitch,
        "poolStats": [
            {
                "sampleCount": pool["sampleCount"],
                "safeCount": pool["safeCount"],
                "retainedCount": len(pool["axes"]),
                "minimumDeviationDeg": (
                    float(pool["deviations"][0]) if len(pool["deviations"]) else None
                ),
            }
            for pool in pools
        ],
        "compatibility": compatibility,
        "axisSolution": None,
        "feasible": False,
    }
    if solution is None:
        return result
    axes = solution["axes"]
    detail = evaluate_candidate(points, normals, axes, height, front_lip, components)
    exact_clearance = detail["indexClearance"]["globalMinimum"]["clearanceMm"]
    result.update(
        {
            "axisSolution": {
                "axes": {NAMES[i]: axes[i].tolist() for i in range(4)},
                "deviationsDeg": {
                    NAMES[i]: solution["deviationsDeg"][i] for i in range(4)
                },
            },
            "detail": detail,
            "feasible": bool(
                detail["hardGatesWithoutRobustTarget"]
                and exact_clearance >= target - 1e-8
            ),
        }
    )
    return result


def probe_prior_options():
    data = load_json("middle_center_axis_joint_optimization.json")
    components = {
        "frozenShellIndexSurface": geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"),
        "RWID": geom.load_triangles("INDEX_FINAL_RWID"),
        "RZKD": geom.load_triangles("INDEX_FINAL_RZKD"),
    }
    output = {}
    for label, option in data["options"].items():
        points = np.asarray([option["centers"][name] for name in NAMES], float)
        normals = np.asarray([option["normals"][name] for name in NAMES], float)
        axes = np.asarray([option["axes"][name] for name in NAMES], float)
        lip_required = max(required_front_lip(normals[i], axes[i]) for i in range(4))
        rows = {}
        for height in HEIGHTS:
            rows[str(height)] = evaluate_candidate(
                points, normals, axes, height, lip_required, components
            )
        output[label] = {
            "minimumNominalFrontLipMm": lip_required,
            "holderRearByHeightMm": {
                str(h): holder_rear(h, lip_required) for h in HEIGHTS
            },
            "heights": rows,
        }
    path = ROOT / "cad_dump" / "middle_low_profile_prior_option_probe.json"
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"wrote {path}")
    for label, row in output.items():
        print(label, "lip", round(row["minimumNominalFrontLipMm"], 4))
        for height, result in row["heights"].items():
            g = result["indexClearance"]["globalMinimum"]
            print(" ", height, round(g["clearanceMm"], 4), g["button"], g["envelope"],
                  "hard", result["hardGatesWithoutRobustTarget"])


def reevaluate_source(source_file: str, height: float, front_lip: float | None = None):
    source = json.loads(Path(source_file).read_text(encoding="utf-8"))
    points = np.asarray([source["centers"][name] for name in NAMES], float)
    normals = np.asarray([source["surfaceNormals"][name] for name in NAMES], float)
    axes = np.asarray([source["axisSolution"]["axes"][name] for name in NAMES], float)
    required = max(required_front_lip(normals[i], axes[i]) for i in range(4))
    chosen_lip = required if front_lip is None else front_lip
    components = {
        "frozenShellIndexSurface": geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"),
        "RWID": geom.load_triangles("INDEX_FINAL_RWID"),
        "RZKD": geom.load_triangles("INDEX_FINAL_RZKD"),
    }
    detail = evaluate_candidate(points, normals, axes, height, chosen_lip, components)
    return {
        "source": str(source_file),
        "heightMm": height,
        "minimumNominalFrontLipMm": required,
        "evaluatedFrontLipMm": chosen_lip,
        "seatDepthMm": front_depth(chosen_lip),
        "holderRearDatumMm": holder_rear(height, chosen_lip),
        "holderDepthBehindTrimMm": holder_rear(height, chosen_lip) - TRIM_DEPTH,
        "detail": detail,
    }


def final_payload():
    selected = [
        {
            "height": 6.0,
            "source": ROOT / "cad_dump" / "h6_y1.json",
            "lipCertifiedUpper": 2.40,
            "lipFirstFailed": 2.45,
            "selection": "height-specific free-axis search",
        },
        {
            "height": 5.0,
            "source": ROOT / "cad_dump" / "h6_y1.json",
            "lipCertifiedUpper": 3.375,
            "lipFirstFailed": 3.4375,
            "selection": "H=5 rerun plus nested-envelope transfer from H=6 winner",
        },
        {
            "height": 4.3,
            "source": ROOT / "cad_dump" / "h6_y1.json",
            "lipCertifiedUpper": 4.00,
            "lipFirstFailed": 4.125,
            "selection": "H=4.3 rerun plus nested-envelope transfer from H=6 winner",
        },
        {
            "height": 3.5,
            "source": ROOT / "cad_dump" / "h3p1_w1.json",
            "lipCertifiedUpper": 2.40,
            "lipFirstFailed": 2.45,
            "selection": "H=3.5 rerun plus nested-envelope transfer from H=3.1 winner",
        },
        {
            "height": 3.1,
            "source": ROOT / "cad_dump" / "h3p1_w1.json",
            "lipCertifiedUpper": 2.80,
            "lipFirstFailed": 2.85,
            "selection": "height-specific free-axis search",
        },
    ]
    index_centers = np.asarray(geom.INDEX_CENTERS, float)
    option_c = load_json("middle_center_axis_joint_optimization.json")["options"]["C"]
    rows = {}
    for spec in selected:
        source = json.loads(spec["source"].read_text(encoding="utf-8"))
        height = spec["height"]
        reevaluated = reevaluate_source(str(spec["source"]), height, None)
        detail = reevaluated["detail"]
        points = np.asarray([source["centers"][name] for name in NAMES], float)
        normals = np.asarray([source["surfaceNormals"][name] for name in NAMES], float)
        axes = np.asarray([source["axisSolution"]["axes"][name] for name in NAMES], float)
        lip_minimum = reevaluated["minimumNominalFrontLipMm"]
        lip_upper = spec["lipCertifiedUpper"]
        spacing = {
            NAMES[i]: {
                "indexButton": f"I{i + 1}",
                "centerDistance3dMm": float(np.linalg.norm(points[i] - index_centers[i])),
                "vectorMm": (points[i] - index_centers[i]).tolist(),
            }
            for i in range(4)
        }
        row = {
            "heightMm": height,
            "sourceCandidate": spec["source"].name,
            "selectionMethod": spec["selection"],
            "translationMm": source["translationMm"],
            "translationNormMm": source["translationNormMm"],
            "tangentialCorrectionMm": source["tangentialCorrectionMm"],
            "longitudinalCorrectionMm": source["longitudinalCorrectionMm"],
            "perButtonDisplacementMm": source["perButtonDisplacementMm"],
            "maximumIndividualDisplacementMm": max(source["perButtonDisplacementMm"]),
            "centers": source["centers"],
            "surfaceNormals": source["surfaceNormals"],
            "axes": source["axisSolution"]["axes"],
            "deviationsDeg": source["axisSolution"]["deviationsDeg"],
            "maximumNormalDeviationDeg": detail["maxDeviationDeg"],
            "pitchMm": detail["pitchMm"],
            "minimumSwitchSatMm": min(detail["switchSatMm"]),
            "minimumPocketDividerMm": min(detail["dividerMm"]),
            "minimumSplitWallMm": min(detail["splitWallMm"]),
            "minimumScrewClearanceMm": min(detail["screwMm"]),
            "minimumIndexClearance": detail["indexClearance"]["globalMinimum"],
            "indexIntersectionCount": detail["indexClearance"]["collisionCount"],
            "minimumCapPairClearanceMm": min(detail["capPairClearanceMm"]),
            "frontLipCertifiedRangeMm": [lip_minimum, lip_upper],
            "frontLipFirstTestedFailureMm": spec["lipFirstFailed"],
            "seatDepthCertifiedRangeMm": [
                front_depth(lip_minimum),
                front_depth(lip_upper),
            ],
            "effectiveStemReachCorridorMm": [
                front_depth(lip_minimum),
                front_depth(lip_upper),
            ],
            "actualMovingStemTravel": "not derivable without a switch/stem SKU",
            "minimumHolderRearDatumMm": holder_rear(height, lip_minimum),
            "minimumHolderDepthBehindTrimMm": holder_rear(height, lip_minimum) - TRIM_DEPTH,
            "indexSpacing": spacing,
            "optionCImprovement": {
                "rowTranslationReductionMm": option_c["translationNormMm"] - source["translationNormMm"],
                "rowTranslationReductionPercent": 100.0 * (
                    option_c["translationNormMm"] - source["translationNormMm"]
                ) / option_c["translationNormMm"],
                "M2DisplacementReductionMm": option_c["perButtonDisplacementMm"][1]
                - source["perButtonDisplacementMm"][1],
            },
            "robust050Pass": bool(
                detail["hardGatesWithoutRobustTarget"]
                and detail["indexClearance"]["globalMinimum"]["clearanceMm"] >= 0.5
            ),
        }
        rows[f"H{height:g}"] = row

    height_limits = {
        "clearance0.50": {
            "sweepConfirmedAtLeastMm": 6.0,
            "fixedBranchCertifiedMaximumMm": 6.10,
            "nextTestedFailureMm": 6.20,
            "sourceCandidate": "h6_y1.json",
            "rowTranslationNormMm": 6.773108592907527,
        },
        "clearance0.80": {
            "sweepConfirmedAtLeastMm": 6.0,
            "fixedBranchCertifiedMaximumMm": 6.20,
            "nextTestedFailureMm": 6.30,
            "sourceCandidate": "h6_c08_1.json",
            "rowTranslationNormMm": 8.04673846971554,
        },
        "clearance1.00": {
            "sweepConfirmedAtLeastMm": 6.0,
            "fixedBranchCertifiedMaximumMm": 6.30,
            "nextTestedFailureMm": 6.40,
            "sourceCandidate": "h6_c10_m2p6.json",
            "rowTranslationNormMm": 8.73212459828649,
            "evaluatedFrontLipMm": 2.30,
        },
    }
    return {
        "method": {
            "mode": "READ-ONLY / Onshape CAD WRITE 0",
            "frozenVersion": "03ede76e83b5c865d9a69c35",
            "configuration": "default",
            "footprintMm": [6.0, 6.0],
            "pocketFootprintMm": [6.4, 6.4],
            "holderWidthMm": 12.4,
            "holderTrimDatumMm": TRIM_DEPTH,
            "rearRetentionMm": REAR_RETENTION,
            "holderRearFormula": "3.0 + frontLip + H + 1.2",
            "clearance": "exact triangle-soup to OBB Euclidean distance after expanded broad-phase",
            "bestQualifier": "best certified candidate in the recorded center/free-axis search; not a global continuous proof",
        },
        "optionCReference": {
            "translationMm": option_c["translationMm"],
            "translationNormMm": option_c["translationNormMm"],
            "M2DisplacementMm": option_c["perButtonDisplacementMm"][1],
            "indexClearanceMm": option_c["indexClearance"]["globalMinimum"]["clearanceMm"],
        },
        "heightResults": rows,
        "maximumHeightReverseCalculation": height_limits,
        "decision": {
            "hardwareFallback": "A-family: retain 6x6x6; new robust reoptimized row supersedes literal Option C",
            "lowProfileClearlyAdvantageous": False,
            "lowProfileSpecificSkuSearchNeeded": False,
            "actualSkuGeometryValidationNeededBeforeWrite": True,
            "cadWrite": "HOLD",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--case", action="store_true")
    parser.add_argument("--height", type=float, default=6.0)
    parser.add_argument("--lip", type=float, default=2.3)
    parser.add_argument("--auto-lip", action="store_true")
    parser.add_argument("--target", type=float, default=0.5)
    parser.add_argument("--translation", nargs=3, type=float, default=(1.0, 5.5, -8.0))
    parser.add_argument("--template", choices=("none", "A", "B"), default="B")
    parser.add_argument("--tangent-scale", type=float)
    parser.add_argument("--m2-z", type=float)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--pool", type=int, default=100)
    parser.add_argument("--output", type=str, default="middle_low_profile_case.json")
    parser.add_argument("--seed-file", action="append", default=[])
    parser.add_argument("--reevaluate", type=str)
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    if args.finalize:
        result = final_payload()
        output = ROOT / "cad_dump" / "middle_low_profile_switch_feasibility.json"
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {output}")
        for name, row in result["heightResults"].items():
            print(
                name,
                "D", round(row["translationNormMm"], 3),
                "max", round(row["maximumIndividualDisplacementMm"], 3),
                "dev", round(row["maximumNormalDeviationDeg"], 3),
                "clear", round(row["minimumIndexClearance"]["clearanceMm"], 4),
                "lip", [round(v, 3) for v in row["frontLipCertifiedRangeMm"]],
            )
        return
    if args.reevaluate:
        result = reevaluate_source(
            args.reevaluate, args.height, None if args.auto_lip else args.lip
        )
        output = ROOT / "cad_dump" / args.output
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        g = result["detail"]["indexClearance"]["globalMinimum"]
        print(f"wrote {output}")
        print(
            "height", args.height,
            "lip", round(result["evaluatedFrontLipMm"], 4),
            "clearance", round(g["clearanceMm"], 6),
            "hard", result["detail"]["hardGatesWithoutRobustTarget"],
        )
        return
    if args.probe:
        probe_prior_options()
        return
    if args.case:
        templates = {
            "none": ((0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0)),
            "A": ((-0.9, -0.3, 0.3, 0.9), (0.0, -3.0, -0.75, -0.75)),
            "B": ((-0.9, -0.3, 0.3, 0.9), (0.0, -3.0, 0.0, 0.0)),
        }
        tangent_correction, z_correction = templates[args.template]
        if args.tangent_scale is not None:
            tangent_correction = tuple(
                args.tangent_scale * value for value in (-0.9, -0.3, 0.3, 0.9)
            )
        if args.m2_z is not None:
            z_correction = (z_correction[0], args.m2_z, z_correction[2], z_correction[3])
        result = solve_case(
            args.height,
            args.lip,
            args.target,
            args.translation,
            tangent_correction,
            z_correction,
            args.samples,
            args.pool,
            args.seed_file,
        )
        output = ROOT / "cad_dump" / args.output
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {output}")
        print("feasible", result["feasible"], "pool", [p["safeCount"] for p in result["poolStats"]])
        if result["axisSolution"]:
            g = result["detail"]["indexClearance"]["globalMinimum"]
            print(
                "clearance", round(g["clearanceMm"], 6), g["button"], g["envelope"], g["component"],
                "maxDev", round(result["detail"]["maxDeviationDeg"], 3),
                "SAT", round(min(result["detail"]["switchSatMm"]), 3),
                "divider", round(min(result["detail"]["dividerMm"]), 3),
                "split", round(min(result["detail"]["splitWallMm"]), 3),
                "screw", round(min(result["detail"]["screwMm"]), 3),
            )
        return
    probe_prior_options()


if __name__ == "__main__":
    main()
