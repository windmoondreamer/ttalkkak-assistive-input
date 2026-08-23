"""READ-ONLY EVQP0E07K physical-envelope audit.

This script performs local numerical checks against the frozen
INDEX_FINAL_VALIDATED tessellation caches.  It has no HTTP client and no CAD
mutation path.  Dimensions come from Panasonic ANCTB36E 202507, page 3.
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
import analyze_middle_low_profile as middle  # noqa: E402


OFFICIAL = {
    "bodyNominalMm": [6.2, 6.2],
    "bodyToleranceMm": [0.1, 0.1],
    "bodyHeightNominalMm": 6.7,
    "unqualifiedDrawingToleranceMm": 0.2,
    "overallFreePositionMaximumMm": 7.45,
    "operatingPositionMm": [7.0, 0.2],
    "actuatorDiameterNominalMm": 3.0,
    "terminalPitchMm": [5.08, 0.20],
    "terminalProjectionMm": [3.5, 0.2],
    "terminalSectionMm": [[0.8, 0.1], [0.3, 0.1]],
    "recommendedPwbHoleDiameterMm": [1.00, 0.05],
    "recommendedPwbHolePitchMm": [5.0, 0.1],
    "operatingForceMaximumN": 0.74,
    "preTravelMaximumMm": 0.5,
    "movementDifferentialMaximumMm": 0.12,
    "overTravelMinimumMm": 0.2,
    "returningForceMinimumN": 0.1,
}

INDEX_N0 = np.asarray(
    [
        (-0.9291, -0.2385, -0.2828),
        (-0.4724, -0.7368, -0.4838),
        (-0.0383, -0.9556, -0.2921),
        (0.0383, -0.9556, -0.2921),
    ],
    dtype=float,
)

# Best nominal candidate found in the recorded actual-SKU bounded search.
# Translation 1.25/5.25/-7.45; tangent scale 1.07; M2 z correction -2.8.
MIDDLE_POINTS = np.asarray(
    [
        (-19.76116250876274, 1.7722714031814117, -13.45),
        (-13.352299132411728, -6.89745778199315, -16.25),
        (-3.8248344011027333, -12.691743207612983, -13.45),
        (7.371679686458834, -11.851407527945067, -13.45),
    ]
)
MIDDLE_NORMALS = np.asarray(
    [
        (-0.9743061371072935, -0.12270102768045967, -0.1888703497143553),
        (-0.49799631203950667, -0.7039148937717189, -0.5064617414192312),
        (-0.10944589058152734, -0.8164249998796939, -0.5669848468929822),
        (0.26332467492461703, -0.7893349258020923, -0.5546264422878251),
    ]
)
MIDDLE_AXES = np.asarray(
    [
        (-0.8109996593761792, -0.5515103682829561, -0.19523285114990127),
        (-0.6425497169735713, -0.7520048436813596, -0.14703256883070978),
        (0.32764764973974503, -0.7021312150995384, -0.6321857119572278),
        (0.17853779715628357, -0.8116888025771647, -0.5561344646373128),
    ]
)


def rect_box(point, axis, u_size, v_size, length, front, u_offset=0.0, v_offset=0.0):
    axes = geom.frame(axis)
    center = (
        np.asarray(point)
        + axes[0] * u_offset
        + axes[1] * v_offset
        - axes[2] * (front + length / 2.0)
    )
    return center, axes, np.asarray((u_size / 2.0, v_size / 2.0, length / 2.0))


def index_sat(width: float, height: float):
    boxes = [
        geom.obb(geom.INDEX_CENTERS[i], geom.unit(geom.INDEX_AXES[i]), width, height, 5.3)
        for i in range(4)
    ]
    rows = {
        f"I{i + 1}-I{j + 1}": geom.sat_signed(boxes[i], boxes[j])
        for i, j in geom.KEY_PAIRS
    }
    return {"pairsMm": rows, "minimumMm": min(rows.values())}


def index_pocket(width: float):
    # Frozen holder passage is depth 5.3..12.5 after SEAT + REAR.
    boxes = [
        geom.obb(geom.INDEX_CENTERS[i], geom.unit(geom.INDEX_AXES[i]), width, 7.2, 5.3)
        for i in range(4)
    ]
    dividers = {
        f"I{i + 1}-I{j + 1}": geom.sat_signed(boxes[i], boxes[j])
        for i, j in geom.ADJ_PAIRS
    }
    xs = [geom.corners(box)[:, 0] for box in boxes]
    split = {"I3": -float(xs[2].max()), "I4": float(xs[3].min())}
    return {
        "nominalPerSideMm": (width - 6.2) / 2.0,
        "worstBody6p3PerSideMm": (width - 6.3) / 2.0,
        "dividerMm": dividers,
        "minimumDividerMm": min(dividers.values()),
        "splitWallMm": split,
        "minimumSplitWallMm": min(split.values()),
    }


def index_front_and_cap():
    rows = {}
    for i in range(4):
        axis = geom.unit(geom.INDEX_AXES[i])
        normal = geom.unit(INDEX_N0[i])
        cosine = float(np.dot(axis, normal))
        deviation = math.degrees(math.acos(np.clip(cosine, -1.0, 1.0)))
        u, v, z = geom.frame(axis)
        front_lip = min(
            -float(np.dot(-z * 5.3 + u * x + v * y, normal)) - 2.8
            for x in (-3.15, 3.15)
            for y in (-3.15, 3.15)
        )
        # The tallest allowed actuator gives the smallest possible free gap.
        min_free_gap = (5.3 - (7.45 - 6.7)) * cosine - 2.6
        rows[f"I{i + 1}"] = {
            "axisToCapNormalDeviationDeg": deviation,
            "minimumFrontLipAt6p3BodyMm": front_lip,
            "minimumFreeActuatorToFlatCapGapMm": min_free_gap,
            "capTravelBeforeHolderFrontStopMm": 0.2,
            "minimumShortfallToFirstContactMm": min_free_gap - 0.2,
            "travelToOperateAtPtMaxMm": min_free_gap + 0.5 / cosine,
            "travelThroughMinimumOtMm": min_free_gap + 0.7 / cosine,
            "actuatorCenterOffsetAtCapUndersidePlaneMm": 2.6 * math.tan(math.radians(deviation)),
        }
    return rows


def index_screw_clearance(width: float, height: float):
    rows = {}
    for i in range(4):
        box = geom.obb(
            geom.INDEX_CENTERS[i], geom.unit(geom.INDEX_AXES[i]), width, height, 5.3
        )
        rows[f"I{i + 1}"] = {
            name: geom.cylinder_gap_x(box, np.asarray(point), x_range, radius)
            for name, (point, x_range, radius) in geom.SCREWS.items()
        }
    return rows


def index_body_retainer_hits(width: float, height: float):
    rwid = geom.load_triangles("INDEX_FINAL_RWID")
    rzkd = geom.load_triangles("INDEX_FINAL_RZKD")
    rows = {}
    for i in range(4):
        box = geom.obb(
            geom.INDEX_CENTERS[i], geom.unit(geom.INDEX_AXES[i]), width, height, 5.3
        )
        rows[f"I{i + 1}"] = {
            "RWID": geom.mesh_box_intersects(rwid, box),
            "RZKD": geom.mesh_box_intersects(rzkd, box),
        }
    return rows


def terminal_boxes(point, axis, rotation_deg: int):
    base = geom.frame(axis)
    theta = math.radians(rotation_deg)
    u = math.cos(theta) * base[0] + math.sin(theta) * base[1]
    v = -math.sin(theta) * base[0] + math.cos(theta) * base[1]
    axes = np.asarray((u, v, base[2]))
    boxes = []
    for sign in (-1.0, 1.0):
        center = (
            np.asarray(point)
            + u * (sign * 2.64)  # (5.08 + 0.20) / 2
            - base[2] * (12.2 + 3.7 / 2.0)
        )
        boxes.append((center, axes, np.asarray((0.2, 0.45, 1.85))))
    return boxes


def index_terminal_rotation_sweep():
    meshes = {
        "JaD": geom.load_triangles("INDEX_FINAL_JaD"),
        "JfD": geom.load_triangles("INDEX_FINAL_JfD"),
        "RWID": geom.load_triangles("INDEX_FINAL_RWID"),
        "RZKD": geom.load_triangles("INDEX_FINAL_RZKD"),
    }
    rows = {}
    for i in range(4):
        components = ("JfD", "RWID") if i < 3 else ("JaD", "RWID", "RZKD")
        best = None
        pass_count = 0
        for rotation in range(180):
            boxes = terminal_boxes(
                geom.INDEX_CENTERS[i], geom.unit(geom.INDEX_AXES[i]), rotation
            )
            hits = sum(
                geom.mesh_box_intersects(meshes[name], box)
                for name in components
                for box in boxes
            )
            if hits == 0:
                pass_count += 1
            if best is None or (hits, rotation) < best:
                best = (hits, rotation)
        rows[f"I{i + 1}"] = {
            "testedRotations": 180,
            "collisionFreeRotationCount": pass_count,
            "minimumCollidingTerminalBoxes": best[0],
            "firstBestRotationDeg": best[1],
            "components": list(components),
        }
    return rows


def middle_components():
    return {
        "frozenShellIndexSurface": geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"),
        "RWID": geom.load_triangles("INDEX_FINAL_RWID"),
        "RZKD": geom.load_triangles("INDEX_FINAL_RZKD"),
    }


def middle_evaluation(footprint: float, height: float, pocket: float):
    middle.FOOTPRINT = footprint
    middle.POCKET = pocket
    middle.HOLDER_WIDTH = pocket + 6.0
    detail = middle.evaluate_candidate(
        MIDDLE_POINTS,
        MIDDLE_NORMALS,
        MIDDLE_AXES,
        height,
        2.3,
        middle_components(),
    )
    return {
        "footprintMm": footprint,
        "heightMm": height,
        "pocketMm": pocket,
        "holderWidthMm": pocket + 6.0,
        "holderRearMm": middle.holder_rear(height, 2.3),
        "switchSatMm": detail["switchSatMm"],
        "minimumSwitchSatMm": min(detail["switchSatMm"]),
        "dividerMm": detail["dividerMm"],
        "minimumDividerMm": min(detail["dividerMm"]),
        "splitWallMm": detail["splitWallMm"],
        "minimumSplitWallMm": min(detail["splitWallMm"]),
        "minimumScrewClearanceMm": min(detail["screwMm"]),
        "minimumActualFrontLipMm": min(detail["actualFrontLipMm"]),
        "maximumAxisDeviationDeg": detail["maxDeviationDeg"],
        "indexClearance": detail["indexClearance"]["globalMinimum"],
        "indexCollisionCount": detail["indexClearance"]["collisionCount"],
        "hardGatePass": detail["hardGatesWithoutRobustTarget"],
    }


def middle_terminal_zones():
    components = middle_components()
    # A 6.3 square bundle is conservative for both terminals at any in-plane
    # switch rotation.  It intentionally includes empty space between pins.
    zones = [
        geom.obb(MIDDLE_POINTS[i], MIDDLE_AXES[i], 6.3, 3.7, 12.2)
        for i in range(4)
    ]
    index_rows = {}
    for i, box in enumerate(zones):
        index_rows[f"M{i + 1}"] = {
            name: {
                "collision": geom.mesh_box_intersects(triangles, box),
                "clearanceMm": geom.mesh_box_distance(triangles, box),
            }
            for name, triangles in components.items()
        }
    neighbors = {
        f"M{i + 1}-M{j + 1}": geom.sat_signed(zones[i], zones[j])
        for i, j in geom.KEY_PAIRS
    }
    return {
        "method": "conservative 6.3 mm square all-rotation terminal bundle, depth 12.2..15.9",
        "toFrozenIndex": index_rows,
        "neighborSatMm": neighbors,
        "minimumNeighborSatMm": min(neighbors.values()),
    }


def main():
    pockets = {str(width): index_pocket(width) for width in (6.4, 6.5, 6.6, 6.7)}
    nominal_middle = middle_evaluation(6.2, 6.7, 6.7)
    worst_middle = middle_evaluation(6.3, 6.9, 6.7)
    middle_pockets = {
        str(width): middle_evaluation(6.2, 6.7, width)
        for width in (6.4, 6.5, 6.6, 6.7)
    }
    payload = {
        "method": {
            "mode": "LOCAL READ-ONLY; Onshape CAD WRITE 0",
            "frozenVersion": "INDEX_FINAL_VALIDATED / 03ede76e83b5c865d9a69c35",
            "configuration": "default (frozen cache source)",
            "drawing": "Panasonic ANCTB36E 202507 page 3",
            "middleBestQualifier": "best nominal candidate in recorded bounded search; not a global continuous proof",
        },
        "official": OFFICIAL,
        "pocketCandidates": pockets,
        "indexSat": {
            "legacyProxy6x6x6": index_sat(6.0, 6.0),
            "nominal6p2x6p2x6p7": index_sat(6.2, 6.7),
            "worst6p3x6p3x6p9": index_sat(6.3, 6.9),
        },
        "indexFrontCap": index_front_and_cap(),
        "indexRear": {
            "switchRearNominalMm": 12.0,
            "switchRearWorstMm": 12.2,
            "holderRearMm": 12.5,
            "rearLandNominalMm": 0.5,
            "rearLandWorstMm": 0.3,
            "currentPadFrontMm": 11.15,
            "bodyPadOverlapNominalMm": 0.85,
            "bodyPadOverlapWorstMm": 1.05,
            "correctedNominalPadFrontFor0p15MmPreload": 11.85,
            "correctedWorstPadFrontFor0p15MmPreload": 12.05,
            "bodyRetainerHitsNominal": index_body_retainer_hits(6.2, 6.7),
            "bodyRetainerHitsWorst": index_body_retainer_hits(6.3, 6.9),
            "screwClearanceWorstMm": index_screw_clearance(6.3, 6.9),
        },
        "indexTerminal": {
            "terminalTipRearNominalMm": 15.5,
            "terminalTipRearWorstMm": 15.9,
            "projectionBeyondHolderRearNominalMm": 3.0,
            "projectionBeyondHolderRearWorstMm": 3.4,
            "rotationSweep": index_terminal_rotation_sweep(),
        },
        "middle": {
            "translationMm": [1.25, 5.25, -7.45],
            "translationNormMm": float(np.linalg.norm((1.25, 5.25, -7.45))),
            "maximumIndividualDisplacementMm": 12.486442882827031,
            "centers": {middle.NAMES[i]: MIDDLE_POINTS[i].tolist() for i in range(4)},
            "axes": {middle.NAMES[i]: MIDDLE_AXES[i].tolist() for i in range(4)},
            "nominal": nominal_middle,
            "sameAxesWorstEnvelope": worst_middle,
            "pocketSensitivitySameAxes": middle_pockets,
            "nearestSmallerTestedFailureNormMm": 9.094360890134062,
            "terminalZones": middle_terminal_zones(),
        },
        "decision": {
            "recommendedPocketMm": 6.7,
            "recommendationBasis": "6.3 mm maximum body + 0.20 mm per side established service clearance",
            "indexModificationRequired": True,
            "indexAsIsUsable": False,
            "middleNominalGeometryCandidate": True,
            "middleToleranceRobustCandidateCertified": False,
            "differentMiddleSwitchRequired": False,
            "cadWrite": "HOLD",
        },
    }
    output = ROOT / "cad_dump" / "evqp0e07k_actual_hardware_audit.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {output}")
    print(
        "INDEX SAT nominal/worst",
        payload["indexSat"]["nominal6p2x6p2x6p7"]["minimumMm"],
        payload["indexSat"]["worst6p3x6p3x6p9"]["minimumMm"],
    )
    print(
        "MIDDLE nominal/worst hard",
        nominal_middle["hardGatePass"],
        worst_middle["hardGatePass"],
    )


if __name__ == "__main__":
    main()
