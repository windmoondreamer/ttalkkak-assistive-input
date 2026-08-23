"""READ-ONLY ITS-1105-6mm project-source audit and channel optimization.

This file derives the project decision in docs/32 from the user-supplied
ITS-1105 drawing and the frozen INDEX_FINAL_VALIDATED local meshes.  It has no
network client and no CAD mutation path.
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
import audit_stock_6x6_switch as stock  # noqa: E402


NAMES = ("I1", "I2", "I3", "I4")
ANGLES = tuple(range(0, 180, 2))  # 180-degree pin-layout symmetry; mirrored to 0..360 in the report
WEB_GATE = 1.50
HOLDER_HALF = 6.20


def root_set(index: int, angle: int, worst: bool):
    return stock.root_boxes(
        geom.INDEX_CENTERS[index],
        geom.unit(geom.INDEX_AXES[index]),
        angle,
        stock.INDEX_FRONT,
        3.9 if worst else 3.6,
        worst,
    )


def local_external_web(index: int, boxes) -> float:
    frame = geom.frame(geom.unit(geom.INDEX_AXES[index]))
    corners = np.concatenate([geom.corners(box) for box in boxes], axis=0)
    local = (corners - geom.INDEX_CENTERS[index]) @ frame.T
    lateral_extent = max(float(np.abs(local[:, 0]).max()), float(np.abs(local[:, 1]).max()))
    return HOLDER_HALF - lateral_extent


def split_web(index: int, boxes) -> float:
    corners = np.concatenate([geom.corners(box) for box in boxes], axis=0)
    if index == 2:
        return -float(corners[:, 0].max())
    if index == 3:
        return float(corners[:, 0].min())
    return float("inf")


def obstacle_clear(index: int, boxes, bodies, rwid, rzkd) -> bool:
    if any(geom.mesh_box_intersects(rwid, box) or geom.mesh_box_intersects(rzkd, box) for box in boxes):
        return False
    if stock.screw_collisions(boxes):
        return False
    if any(
        geom.sat_signed(box, bodies[j]) <= 0.0
        for box in boxes for j in range(4) if j != index
    ):
        return False
    return True


def pair_gap(boxes_a, boxes_b) -> float:
    """Conservative separating-axis lower bound between root-channel envelopes."""
    return min(geom.sat_signed(a, b) for a in boxes_a for b in boxes_b)


def find_chain(individual, pair12, pair23, pair34, threshold):
    valid = [row >= threshold for row in individual]
    best = None
    for a2 in range(len(ANGLES)):
        if not valid[1][a2]:
            continue
        a1s = np.flatnonzero(valid[0] & (pair12[:, a2] >= threshold))
        if not len(a1s):
            continue
        for a3 in range(len(ANGLES)):
            if not valid[2][a3] or pair23[a2, a3] < threshold:
                continue
            a4s = np.flatnonzero(valid[3] & (pair34[a3, :] >= threshold))
            if not len(a4s):
                continue
            # Preserve existing edge-slot directions when structural margins
            # are tied.  0/180 has zero penalty.
            for a1 in a1s:
                for a4 in a4s:
                    indices = (int(a1), int(a2), int(a3), int(a4))
                    degrees = tuple(ANGLES[k] for k in indices)
                    penalty = sum(1.0 - abs(math.cos(math.radians(value))) for value in degrees)
                    key = (penalty, sum(min(value, 180 - value) for value in degrees), degrees)
                    if best is None or key < best[0]:
                        best = (key, indices)
    return None if best is None else best[1]


def optimize_channels(worst: bool):
    root_cache = [[root_set(i, angle, worst) for angle in ANGLES] for i in range(4)]
    width = 6.3 if worst else 6.0
    height = 3.9 if worst else 3.6
    bodies = [
        geom.obb(geom.INDEX_CENTERS[i], geom.unit(geom.INDEX_AXES[i]), width, height, stock.INDEX_FRONT)
        for i in range(4)
    ]
    rwid = geom.load_triangles("INDEX_FINAL_RWID")
    rzkd = geom.load_triangles("INDEX_FINAL_RZKD")
    individual = []
    details = []
    for i in range(4):
        margins, rows = [], []
        for angle_index, angle in enumerate(ANGLES):
            boxes = root_cache[i][angle_index]
            external = local_external_web(i, boxes)
            split = split_web(i, boxes)
            clear = obstacle_clear(i, boxes, bodies, rwid, rzkd)
            margin = min(external, split) if clear else -1.0
            margins.append(margin)
            rows.append({
                "rollDeg": angle,
                "externalWebMm": external,
                "splitWebMm": None if math.isinf(split) else split,
                "obstacleClearIgnoringHolderMaterial": clear,
                "individualMarginMm": margin,
            })
        individual.append(np.asarray(margins, dtype=float))
        details.append(rows)
    pair_matrices = []
    for i, j in ((0, 1), (1, 2), (2, 3)):
        matrix = np.empty((len(ANGLES), len(ANGLES)), dtype=float)
        for ai in range(len(ANGLES)):
            for aj in range(len(ANGLES)):
                matrix[ai, aj] = pair_gap(root_cache[i][ai], root_cache[j][aj])
        pair_matrices.append(matrix)
    low, high = 0.0, 5.0
    indices = None
    for _ in range(40):
        mid = (low + high) / 2.0
        found = find_chain(individual, *pair_matrices, mid)
        if found is None:
            high = mid
        else:
            low, indices = mid, found
    if indices is None:
        return {"feasible": False, "resolutionDeg": 2}
    angles = [ANGLES[indices[i]] for i in range(4)]
    ind_values = [float(individual[i][indices[i]]) for i in range(4)]
    pair_values = [
        float(pair_matrices[0][indices[0], indices[1]]),
        float(pair_matrices[1][indices[1], indices[2]]),
        float(pair_matrices[2][indices[2], indices[3]]),
    ]
    governing = min(*ind_values, *pair_values)
    return {
        "feasible": governing >= WEB_GATE - 1e-9,
        "resolutionDeg": 2,
        "periodicityDeg": 180,
        "rollsDeg": dict(zip(NAMES, angles)),
        "equivalentRolls0to360Deg": {
            NAMES[i]: [angles[i], angles[i] + 180] for i in range(4)
        },
        "individualMarginsMm": dict(zip(NAMES, ind_values)),
        "adjacentChannelWebLowerBoundMm": dict(zip(("I1-I2", "I2-I3", "I3-I4"), pair_values)),
        "governingZeroClearanceWebMm": governing,
        "webGateMm": WEB_GATE,
        "conservativeSymmetricClearanceAllowancePerChannelMm": max((governing - WEB_GATE) / 2.0, 0.0),
        "qualifier": "bounded 2-degree roll search; root OBB SAT lower bounds; final B-rep channel required before write",
    }


def main():
    prior = json.loads((ROOT / "cad_dump" / "stock_6x6x6_switch_actual_fit_audit.json").read_text(encoding="utf-8"))
    nominal_channels = optimize_channels(False)
    worst_channels = optimize_channels(True)
    payload = {
        "method": {
            "mode": "LOCAL READ-ONLY; Onshape CAD WRITE 0",
            "frozenVersion": "INDEX_FINAL_VALIDATED / 03ede76e83b5c865d9a69c35",
            "configuration": "default (frozen cache source)",
            "primarySwitch": "ITS-1105-6mm",
            "purchasedQuantity": 20,
            "drawing": "user-supplied ITS-1105 family drawing, L=6.0",
        },
        "drawingAudit": prior,
        "fixedRootFullRoll": {
            "periodicityExplanation": "four-pin rectangular layout repeats at 180 degrees; 0..179 exact results mirror into 180..359",
            "currentClearRanges0to360Deg": {name: [] for name in NAMES},
            "currentClearCountsPer360": {name: 0 for name in NAMES},
        },
        "coordinatedTerminalChannel": {
            "nominal": nominal_channels,
            "drawingWorst": worst_channels,
            "channelDepthNominalMm": [8.9, 12.5],
            "channelDepthDrawingWorstMm": [9.2, 12.5],
            "rootEnvelopeExtraBeyond6p4PerSideNominalMm": 0.75,
            "rootEnvelopeExtraBeyond6p4PerSideWorstMm": 0.90,
            "manufacturingClearance": "parameter c_channel; do not freeze until physical-lot root measurement and coupon",
        },
        "rearMinorSolution": {
            "preferred": "separate non-moving central rear spacer/shim; preserve RWID/RZKD pad and service paths",
            "nominalSpacerLengthMm": 2.4,
            "drawingStackSpacerLengthRangeMm": [2.1, 2.7],
            "contactDiameterCandidateMm": 3.6,
            "reason": "actual body rear 8.9 + spacer 2.4 reproduces legacy contact rear 11.3; current pad front 11.15 retains 0.15 nominal preload",
            "padExtensionRejectedAsMinimumPlan": "moving pad extension raises shared service demand to 4.84 mm and I4 to 4.25 mm",
        },
        "capMinorSolution": {
            "currentAvailableStrokeMm": 0.2,
            "minimumAdditionalStopRecessAtZeroFreeGapMm": {
                "I1": 0.134336757019875,
                "I2": 0.1343367156639476,
                "I3": 0.1343366816590796,
                "I4": 0.1496236853683653,
            },
            "bossLengthFormula": "measured free gap - chosen prototype free clearance",
            "stopRecessFormula": "chosen free clearance + 0.35*cos(axis-to-cap-normal) - 0.20",
            "status": "parameterized Grade-1 cap underside boss + local stop relief; actual lot measurement required",
        },
        "registryUpdatePlanOnly": {
            "part": "ITS-1105-6mm",
            "role": "INDEX + MIDDLE PRIMARY FINGER SWITCH",
            "status": "SELECTED / PHYSICAL LOT MEASUREMENT PENDING",
            "quantityPurchased": 20,
            "measure02Add": [
                "body X", "body Y", "housing height", "overall L", "actuator diameter",
                "actuator projection", "fixed-root position/profile", "pin spacing", "pin width", "pin thickness",
            ],
            "filesModified": False,
        },
        "decision": {
            "indexGrade": 1,
            "case": "B",
            "minimumPlan": [
                "coordinated local fixed-root channels",
                "separate non-moving rear spacer/shim",
                "parameterized cap underside contact boss and local stroke relief",
                "open rear wire/solder path using existing retainer slot directions",
            ],
            "centersAxesLayoutChange": False,
            "middleSameSwitch": True,
            "sameSkuIndexMiddle": True,
            "evqp0e07kFingerPrimary": False,
            "nextCadWrite": "HOLD pending physical-lot measurement and explicit approval",
        },
    }
    output = ROOT / "cad_dump" / "its1105_primary_switch_design_audit.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {output}")
    print("channel nominal", nominal_channels)
    print("channel worst", worst_channels)


if __name__ == "__main__":
    main()
