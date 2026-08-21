"""Local READ-ONLY audit for the user-owned 6x6, L=6 tactile switch.

The script reads only frozen local tessellation caches for
INDEX_FINAL_VALIDATED.  It has no HTTP client and no Onshape mutation path.
The mechanical dimensions are transcribed from the drawing image supplied by
the user on 2026-08-20.  Unqualified dimensions use the drawing's +/-0.3 mm
general tolerance only in the separately labelled worst-case envelope.
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_middle_prewrite as geom  # noqa: E402
import analyze_middle_low_profile as middle  # noqa: E402


DRAWING = {
    "selectedOverallHeightLmm": 6.0,
    "bodyFootprintMm": [6.0, 6.0],
    "bodyHeightMm": 3.6,
    "actuatorProjectionAboveBodyMm": 2.4,
    "actuatorDiameterMm": 3.5,
    "travelMm": {"nominal": 0.25, "lower": 0.15, "upper": 0.35},
    "terminalCount": 4,
    "terminalCenterPatternMm": [6.5, 4.5],
    "terminalCenterPatternToleranceMm": [0.2, 0.2],
    "terminalSectionMm": [0.3, 0.7],
    "terminalMaximumOuterWidthMm": 7.9,
    "terminalMaximumOuterWidthToleranceMm": [0.3, 0.3],
    "terminalProjectionBehindBodyMm": 3.5,
    "factoryFormedRootDepthMm": 1.8,
    "pcbHoleCountAndDiameterMm": [4, 1.0],
    "generalToleranceMm": 0.3,
    "circuit": "pins 1-2 internally common; pins 3-4 internally common; press bridges the two groups",
}

INDEX_NORMALS = np.asarray(
    [
        (-0.9291, -0.2385, -0.2828),
        (-0.4724, -0.7368, -0.4838),
        (-0.0383, -0.9556, -0.2921),
        (0.0383, -0.9556, -0.2921),
    ],
    dtype=float,
)

INDEX_FRONT = 5.3
INDEX_HOLDER_REAR = 12.5
CAP_UNDERSIDE_NORMAL_DEPTH = 2.6
HOLDER_TRIM_NORMAL_DEPTH = 2.8
BORE_DIAMETER = 4.5
POCKET_WIDTH = 6.4
SHARED_PAD_REAR = 13.5
I4_PAD_REAR = 13.2
SHARED_SERVICE_DIRECTION = geom.unit(np.asarray((0.4734, 0.8350, 0.2805)))
SLOT_SIGNS = (-1, 1, -1, -1)


def rotation_frame(axis: np.ndarray, rotation_deg: float) -> np.ndarray:
    base = geom.frame(axis)
    theta = math.radians(rotation_deg)
    u = math.cos(theta) * base[0] + math.sin(theta) * base[1]
    v = -math.sin(theta) * base[0] + math.cos(theta) * base[1]
    return np.asarray((u, v, base[2]))


def segment_box(p0: np.ndarray, p1: np.ndarray, width_v: float, thickness: float):
    direction = geom.unit(p1 - p0)
    # All terminal centerlines are in the local u/depth plane; local v is
    # therefore a stable first cross-section direction.
    nominal_axis = geom.unit(np.cross(direction, np.asarray((0.0, 0.0, 1.0))))
    if np.linalg.norm(nominal_axis) < 1e-8:
        nominal_axis = np.asarray((1.0, 0.0, 0.0))
    # The caller replaces this orientation; this branch is retained only as a
    # safe fallback and is not used by root_boxes().
    other = geom.unit(np.cross(direction, nominal_axis))
    axes = np.asarray((nominal_axis, other, direction))
    return (p0 + p1) / 2.0, axes, np.asarray((width_v / 2.0, thickness / 2.0, np.linalg.norm(p1 - p0) / 2.0))


def root_boxes(
    point: np.ndarray,
    axis: np.ndarray,
    rotation_deg: float,
    front: float,
    body_height: float,
    worst: bool = False,
):
    """Four conservative boxes around the factory-formed, no-bend root zone."""
    u, v, z = rotation_frame(axis, rotation_deg)
    if worst:
        footprint = 6.3
        metal_u = 0.6
        metal_v = 1.0
        pitch_v = 4.7
        outer_width = 8.2
        formed_depth = 2.1
    else:
        footprint = 6.0
        metal_u = 0.3
        metal_v = 0.7
        pitch_v = 4.5
        outer_width = 7.9
        formed_depth = 1.8
    rear = front + body_height
    start_u = footprint / 2.0 + metal_u / 2.0
    knee_u = (outer_width - metal_u) / 2.0
    boxes = []
    for sign_u in (-1.0, 1.0):
        for sign_v in (-1.0, 1.0):
            p0 = np.asarray(point) + u * (sign_u * start_u) + v * (sign_v * pitch_v / 2.0) - z * rear
            p1 = np.asarray(point) + u * (sign_u * knee_u) + v * (sign_v * pitch_v / 2.0) - z * (rear + formed_depth)
            direction = geom.unit(p1 - p0)
            cross_v = v
            cross_t = geom.unit(np.cross(direction, cross_v))
            axes = np.asarray((cross_v, cross_t, direction))
            boxes.append(
                (
                    (p0 + p1) / 2.0,
                    axes,
                    np.asarray((metal_v / 2.0, metal_u / 2.0, np.linalg.norm(p1 - p0) / 2.0)),
                )
            )
    return boxes


def box_collision_count(mesh: np.ndarray, boxes) -> int:
    return sum(int(geom.mesh_box_intersects(mesh, box)) for box in boxes)


def crop_mesh_for_roots(mesh: np.ndarray, point: np.ndarray, axis: np.ndarray, front: float, body_height: float, worst: bool):
    """Conservative AABB broad phase around every possible in-plane rotation."""
    formed = 2.1 if worst else 1.8
    rear = front + body_height
    center = np.asarray(point) - geom.unit(axis) * (rear + formed / 2.0)
    margin = 6.0
    lower, upper = center - margin, center + margin
    tmin, tmax = mesh.min(axis=1), mesh.max(axis=1)
    keep = np.all(tmax >= lower, axis=1) & np.all(tmin <= upper, axis=1)
    return mesh[keep]


def index_sat(width: float, height: float):
    boxes = [
        geom.obb(geom.INDEX_CENTERS[i], geom.unit(geom.INDEX_AXES[i]), width, height, INDEX_FRONT)
        for i in range(4)
    ]
    pairs = {
        f"I{i + 1}-I{j + 1}": geom.sat_signed(boxes[i], boxes[j])
        for i, j in geom.KEY_PAIRS
    }
    return {"pairsMm": pairs, "minimumMm": min(pairs.values())}


def cap_audit():
    rows = {}
    for i in range(4):
        axis = geom.unit(geom.INDEX_AXES[i])
        normal = geom.unit(INDEX_NORMALS[i])
        cosine = float(np.dot(axis, normal))
        deviation = math.degrees(math.acos(np.clip(cosine, -1.0, 1.0)))
        top_axis_nominal = INDEX_FRONT - (6.0 - 3.6)
        nominal_gap = top_axis_nominal * cosine - CAP_UNDERSIDE_NORMAL_DEPTH
        travel_rows = {
            name: nominal_gap + travel * cosine
            for name, travel in (("lower", 0.15), ("nominal", 0.25), ("upper", 0.35))
        }
        # Independent drawing stack: L max/body-height min gives the most
        # protruding actuator; the opposite stack gives the deepest actuator.
        top_axis_min = INDEX_FRONT - ((6.0 + 0.3) - (3.6 - 0.3))
        top_axis_max = INDEX_FRONT - ((6.0 - 0.3) - (3.6 + 0.3))
        rows[f"I{i + 1}"] = {
            "axisToCapNormalDeviationDeg": deviation,
            "axisNormalCosine": cosine,
            "actuatorTopAxisDepthNominalMm": top_axis_nominal,
            "freeGapAlongCapNormalNominalMm": nominal_gap,
            "freeGapDrawingStackRangeMm": [
                top_axis_min * cosine - CAP_UNDERSIDE_NORMAL_DEPTH,
                top_axis_max * cosine - CAP_UNDERSIDE_NORMAL_DEPTH,
            ],
            "capTravelAvailableBeforeHolderTrimMm": HOLDER_TRIM_NORMAL_DEPTH - CAP_UNDERSIDE_NORMAL_DEPTH,
            "capDisplacementToActuatorTravelMm": travel_rows,
            "minimumTravelShortfallMm": travel_rows["lower"] - 0.2,
            "nominalTravelShortfallMm": travel_rows["nominal"] - 0.2,
            "maximumTravelShortfallMm": travel_rows["upper"] - 0.2,
            "actuatorAxisOffsetAtCapUndersideMm": CAP_UNDERSIDE_NORMAL_DEPTH * math.tan(math.radians(deviation)),
        }
    return rows


def pad_disengagement(front: float, rear: float, direction: np.ndarray, button_index: int, step: float = 0.01):
    point = geom.INDEX_CENTERS[button_index]
    axis = geom.unit(geom.INDEX_AXES[button_index])
    bore = geom.obb(point, axis, POCKET_WIDTH, INDEX_HOLDER_REAR - INDEX_FRONT, INDEX_FRONT)
    pad = geom.obb(point, axis, 3.6, rear - front, front)
    t = 0.0
    while t <= 12.0:
        moved = (pad[0] + direction * t, pad[1], pad[2])
        if geom.sat_signed(moved, bore) > 0.0:
            return round(t, 2)
        t += step
    return None


def index_rear_audit():
    nominal_rear = INDEX_FRONT + 3.6
    rear_range = [INDEX_FRONT + 3.3, INDEX_FRONT + 3.9]
    corrected_front = nominal_rear - 0.15
    current_shared = [pad_disengagement(11.15, SHARED_PAD_REAR, SHARED_SERVICE_DIRECTION, i) for i in range(3)]
    corrected_shared = [pad_disengagement(corrected_front, SHARED_PAD_REAR, SHARED_SERVICE_DIRECTION, i) for i in range(3)]
    return {
        "bodyRearNominalMm": nominal_rear,
        "bodyRearDrawingStackRangeMm": rear_range,
        "currentPadFrontMm": 11.15,
        "nominalPadGapMm": 11.15 - nominal_rear,
        "minimumPadGapAtBodyHeightMaxMm": 11.15 - rear_range[1],
        "padFrontForNominal0p15PreloadMm": corrected_front,
        "sharedCurrentBoreDisengagementMm": current_shared,
        "sharedCorrectedBoreDisengagementMm": corrected_shared,
        "sharedCorrectedServiceWith0p50MarginMm": max(corrected_shared) + 0.5,
        "sharedFinalVerifiedServiceTravelMm": 2.09,
        "i4CurrentRequiredMm": INDEX_HOLDER_REAR - 11.15,
        "i4CurrentServiceMm": INDEX_HOLDER_REAR - 11.15 + 0.5,
        "i4CorrectedRequiredMm": INDEX_HOLDER_REAR - corrected_front,
        "i4CorrectedServiceMm": INDEX_HOLDER_REAR - corrected_front + 0.5,
    }


def split_clear(name: str, boxes) -> bool:
    points = np.concatenate([geom.corners(box) for box in boxes], axis=0)
    if name.endswith("3"):
        return float(points[:, 0].max()) < 0.0
    if name.endswith("4"):
        return float(points[:, 0].min()) > 0.0
    return True


def screw_collisions(boxes) -> int:
    return sum(
        int(geom.cylinder_gap_x(box, np.asarray(point), x_range, radius) <= 1e-10)
        for box in boxes
        for point, x_range, radius in geom.SCREWS.values()
    )


def root_pair_sat(boxes_a, boxes_b) -> float:
    return min(geom.sat_signed(a, b) for a in boxes_a for b in boxes_b)


def inside_pocket(box, point: np.ndarray, axis: np.ndarray) -> bool:
    """True only when the complete root OBB lies in the existing 6.4 passage."""
    frame = geom.frame(axis)
    local = (geom.corners(box) - np.asarray(point)) @ frame.T
    depths = -local[:, 2]
    return bool(
        np.all(np.abs(local[:, 0]) <= POCKET_WIDTH / 2.0 + 1e-9)
        and np.all(np.abs(local[:, 1]) <= POCKET_WIDTH / 2.0 + 1e-9)
        and np.all(depths >= INDEX_FRONT - 1e-9)
        and np.all(depths <= INDEX_HOLDER_REAR + 1e-9)
    )


def holder_solid_collision(box, holder, pocket_point: np.ndarray, pocket_axis: np.ndarray) -> bool:
    """Analytic holder OBB minus its 6.4 through-passage."""
    if geom.sat_signed(box, holder) > 0.0:
        return False
    return not inside_pocket(box, pocket_point, pocket_axis)


def rotation_sweep(points, axes, fronts, heights, names, current_index: bool, worst: bool = False):
    meshes = {
        "JaD": geom.load_triangles("INDEX_FINAL_JaD"),
        "JfD": geom.load_triangles("INDEX_FINAL_JfD"),
        "RWID": geom.load_triangles("INDEX_FINAL_RWID"),
        "RZKD": geom.load_triangles("INDEX_FINAL_RZKD"),
    }
    body_width = 6.3 if worst else 6.0
    bodies = [geom.obb(points[i], axes[i], body_width, heights[i], fronts[i]) for i in range(4)]
    holders = [geom.obb(points[i], axes[i], 12.4, 9.7, 2.8) for i in range(4)] if current_index else []
    rows = {}
    root_cache = {}
    for i, name in enumerate(names):
        local_meshes = {
            label: crop_mesh_for_roots(mesh, points[i], axes[i], fronts[i], heights[i], worst)
            for label, mesh in meshes.items()
        }
        scored = []
        for rotation in range(180):
            boxes = root_boxes(points[i], axes[i], rotation, fronts[i], heights[i], worst)
            root_cache[(i, rotation)] = boxes
            component_hits = {label: box_collision_count(mesh, boxes) for label, mesh in local_meshes.items()}
            neighbor_body_hits = sum(
                int(geom.sat_signed(box, bodies[j]) <= 0.0)
                for box in boxes for j in range(4) if j != i
            )
            own_holder_hits = 0
            neighbor_holder_hits = 0
            if current_index:
                own_holder_hits = sum(
                    int(holder_solid_collision(box, holders[i], points[i], axes[i]))
                    for box in boxes
                )
                neighbor_holder_hits = sum(
                    int(holder_solid_collision(box, holders[j], points[j], axes[j]))
                    for box in boxes for j in range(4) if j != i
                )
            split_ok = split_clear(name, boxes)
            screw_hits = screw_collisions(boxes)
            total_mesh = sum(component_hits.values())
            hard_current = total_mesh + own_holder_hits + neighbor_holder_hits + neighbor_body_hits + screw_hits + int(not split_ok)
            conditional = (
                component_hits["RWID"] + component_hits["RZKD"]
                + neighbor_holder_hits + neighbor_body_hits + screw_hits + int(not split_ok)
            )
            alignment = 0.0
            if current_index:
                base_v = geom.frame(axes[i])[1] * SLOT_SIGNS[i]
                rotated_v = rotation_frame(axes[i], rotation)[1]
                alignment = 1.0 - abs(float(np.dot(base_v, rotated_v)))
            scored.append(
                {
                    "rotationDeg": rotation,
                    "componentRootSegmentHits": component_hits,
                    "meshRootSegmentHits": total_mesh,
                    "ownHolderSolidRootSegmentHits": own_holder_hits,
                    "neighborBodyHits": neighbor_body_hits,
                    "neighborHolderObbHits": neighbor_holder_hits,
                    "screwHits": screw_hits,
                    "splitOwnershipClear": split_ok,
                    "hardCurrentScore": hard_current,
                    "conditionalAfterOwnReliefScore": conditional,
                    "wireExitAlignmentPenalty": alignment,
                }
            )
        current_pass = [row for row in scored if row["hardCurrentScore"] == 0]
        conditional = [row for row in scored if row["conditionalAfterOwnReliefScore"] == 0]
        best_current = min(scored, key=lambda row: (row["hardCurrentScore"], row["neighborHolderObbHits"], row["wireExitAlignmentPenalty"], row["rotationDeg"]))
        best_conditional = min(
            conditional or scored,
            key=lambda row: (
                row["conditionalAfterOwnReliefScore"],
                row["neighborHolderObbHits"],
                row["wireExitAlignmentPenalty"],
                row["rotationDeg"],
            ),
        )
        rows[name] = {
            "testedRotations": 180,
            "currentCollisionFreeRotationCount": len(current_pass),
            "conditionalRotationCountAfterOwnRootRelief": len(conditional),
            "bestCurrent": best_current,
            "conditionalSeed": best_conditional,
        }
    # Report the simple conditional seeds as a joint sanity check.  A full
    # holder subtraction has not been authored, so these are seeds, not CAD
    # approvals.
    seeds = [rows[name]["conditionalSeed"]["rotationDeg"] for name in names]
    pair_rows = {}
    for i, j in geom.KEY_PAIRS:
        pair_rows[f"{names[i]}-{names[j]}"] = root_pair_sat(root_cache[(i, seeds[i])], root_cache[(j, seeds[j])])
    return {
        "perButton": rows,
        "conditionalSeedRotationsDeg": dict(zip(names, seeds)),
        "conditionalSeedRootPairSatMm": pair_rows,
        "conditionalSeedMinimumRootPairSatMm": min(pair_rows.values()),
    }


def middle_source():
    source = json.loads((ROOT / "cad_dump" / "h3p1_w1.json").read_text(encoding="utf-8"))
    names = middle.NAMES
    points = np.asarray([source["centers"][name] for name in names], dtype=float)
    normals = np.asarray([source["surfaceNormals"][name] for name in names], dtype=float)
    axes = np.asarray([source["axisSolution"]["axes"][name] for name in names], dtype=float)
    required_lip = max(middle.required_front_lip(normals[i], axes[i]) for i in range(4))
    components = {
        "frozenShellIndexSurface": geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"),
        "RWID": geom.load_triangles("INDEX_FINAL_RWID"),
        "RZKD": geom.load_triangles("INDEX_FINAL_RZKD"),
    }

    def evaluate(width: float, height: float):
        middle.FOOTPRINT = width
        middle.POCKET = 6.4
        middle.HOLDER_WIDTH = 12.4
        detail = middle.evaluate_candidate(points, normals, axes, height, required_lip, components)
        return {
            "footprintMm": width,
            "bodyHeightMm": height,
            "frontLipMm": required_lip,
            "bodyFrontDepthMm": middle.front_depth(required_lip),
            "bodyRearDepthMm": middle.front_depth(required_lip) + height,
            "holderRearDatumMm": middle.holder_rear(height, required_lip),
            "minimumBodySatMm": min(detail["switchSatMm"]),
            "minimumPocketDividerMm": min(detail["dividerMm"]),
            "minimumSplitWallMm": min(detail["splitWallMm"]),
            "minimumScrewClearanceMm": min(detail["screwMm"]),
            "minimumActualFrontLipMm": min(detail["actualFrontLipMm"]),
            "minimumFrozenIndexClearance": detail["indexClearance"]["globalMinimum"],
            "frozenIndexCollisionCount": detail["indexClearance"]["collisionCount"],
            "hardGatePass": detail["hardGatesWithoutRobustTarget"],
            "robust0p50Pass": bool(
                detail["hardGatesWithoutRobustTarget"]
                and detail["indexClearance"]["globalMinimum"]["clearanceMm"] >= 0.5
            ),
        }

    nominal = evaluate(6.0, 3.6)
    worst = evaluate(6.3, 3.9)
    nominal_front = nominal["bodyFrontDepthMm"]
    roots_nominal = rotation_sweep(
        points,
        axes,
        [nominal_front] * 4,
        [3.6] * 4,
        list(names),
        current_index=False,
        worst=False,
    )
    roots_worst = rotation_sweep(
        points,
        axes,
        [nominal_front] * 4,
        [3.9] * 4,
        list(names),
        current_index=False,
        worst=True,
    )
    return {
        "sourceCandidate": "h3p1_w1.json (docs/29 H3.5 branch reevaluated at actual 3.6/3.9 body height)",
        "translationMm": source["translationMm"],
        "translationNormMm": source["translationNormMm"],
        "perButtonDisplacementMm": source["perButtonDisplacementMm"],
        "maximumIndividualDisplacementMm": max(source["perButtonDisplacementMm"]),
        "centers": source["centers"],
        "axes": source["axisSolution"]["axes"],
        "nominal": nominal,
        "drawingWorst": worst,
        "terminalRootNominal": roots_nominal,
        "terminalRootDrawingWorst": roots_worst,
    }


def main():
    index_points = np.asarray(geom.INDEX_CENTERS, dtype=float)
    index_axes = np.asarray([geom.unit(axis) for axis in geom.INDEX_AXES], dtype=float)
    index_roots_nominal = rotation_sweep(
        index_points,
        index_axes,
        [INDEX_FRONT] * 4,
        [3.6] * 4,
        ["I1", "I2", "I3", "I4"],
        current_index=True,
        worst=False,
    )
    index_roots_worst = rotation_sweep(
        index_points,
        index_axes,
        [INDEX_FRONT] * 4,
        [3.9] * 4,
        ["I1", "I2", "I3", "I4"],
        current_index=True,
        worst=True,
    )
    payload = {
        "method": {
            "mode": "LOCAL READ-ONLY; Onshape CAD WRITE 0",
            "frozenVersion": "INDEX_FINAL_VALIDATED / 03ede76e83b5c865d9a69c35",
            "configuration": "default (frozen cache source)",
            "drawingSource": "user-supplied image; L=6.0 variant",
            "rootModel": "factory-formed 1.8 mm zone as four sloped OBB segments; distal 1.7 mm excluded from rigid hard gate",
            "rotationResolutionDeg": 1,
        },
        "drawing": DRAWING,
        "proxyDifference": {
            "legacy": "one 6x6x6 cuboid from depth 5.3 to 11.3",
            "actual": "6x6x3.6 body from 5.3 to 8.9; actuator top at 2.9; four formed roots 8.9..10.7; bendable distal terminals to 12.4",
        },
        "pocket": {
            "widthMm": 6.4,
            "nominalBodyMm": 6.0,
            "nominalPerSideClearanceMm": 0.2,
            "drawingWorstBodyMm": 6.3,
            "drawingWorstPerSideClearanceMm": 0.05,
            "couponWidthsMm": [6.4, 6.5, 6.6, 6.7],
        },
        "index": {
            "bodySat": {
                "legacyProxy6x6x6": index_sat(6.0, 6.0),
                "actualNominal6x6x3p6": index_sat(6.0, 3.6),
                "drawingWorst6p3x6p3x3p9": index_sat(6.3, 3.9),
            },
            "actuatorBore": {
                "actuatorDiameterNominalMm": 3.5,
                "boreDiameterMm": 4.5,
                "nominalRadialClearanceMm": 0.5,
                "drawingWorstActuatorDiameterMm": 3.8,
                "drawingWorstRadialClearanceMm": 0.35,
            },
            "cap": cap_audit(),
            "rear": index_rear_audit(),
            "terminalRootNominal": index_roots_nominal,
            "terminalRootDrawingWorst": index_roots_worst,
        },
        "middle": middle_source(),
        "electrical": {
            "sameGroupInvalidPairs": [[1, 2], [3, 4]],
            "validTwoTerminalExamples": [[1, 3], [1, 4], [2, 3], [2, 4]],
            "defaultMechanicalPolicy": "retain all four terminals; one-time form distal zone only; do not approve cutting",
        },
        "decision": {
            "indexAsIs": False,
            "indexModificationGrade": 2,
            "indexCadModificationRequired": True,
            "middleSameSwitchGeometryFeasible": True,
            "middleDifferentHardwareRequired": False,
            "unifyIndexAndMiddleSkuAfterRedesignAndPrototype": True,
            "evqp0e07kMechanicalSource": "EXCLUDED; do not redesign INDEX for EVQP0E07K",
            "nextCadWrite": "HOLD",
        },
    }
    output = ROOT / "cad_dump" / "stock_6x6x6_switch_actual_fit_audit.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {output}")
    print("INDEX SAT nominal/worst", payload["index"]["bodySat"]["actualNominal6x6x3p6"]["minimumMm"], payload["index"]["bodySat"]["drawingWorst6p3x6p3x3p9"]["minimumMm"])
    print("INDEX root pass nominal", [payload["index"]["terminalRootNominal"]["perButton"][f"I{i}"]["currentCollisionFreeRotationCount"] for i in range(1, 5)])
    print("MIDDLE robust nominal/worst", payload["middle"]["nominal"]["robust0p50Pass"], payload["middle"]["drawingWorst"]["robust0p50Pass"])


if __name__ == "__main__":
    main()
