"""READ-ONLY reevaluation of the user-measured ITS-1105-6mm sample.

The script combines the physical sample body/actuator stack with the frozen
INDEX_FINAL_VALIDATED local meshes.  Terminal metal remains drawing-derived
because the supplied sample record specifies bend policy but not pin/root
dimensions.  There is no network client and no CAD mutation path.
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
import analyze_middle_low_profile as middle  # noqa: E402
import analyze_middle_prewrite as geom  # noqa: E402
import audit_its1105_primary_switch as prior  # noqa: E402
import audit_stock_6x6_switch as stock  # noqa: E402


BODY_X = 6.12
BODY_Y = 6.05
HOUSING_H = 3.56
TOTAL_H = 6.00
ACTUATOR_D = 3.35
ACTUATOR_PROJECTION = 2.44
TRAVEL = {"nominal": 0.25, "lower": 0.15, "upper": 0.35}
POCKET = 6.40
BORE = 4.50
WEB_GATE = 1.50
BODY_SAT_GATE = 1.20
CARDINAL_ANGLES = (0, 90)
KEY_PAIRS = tuple(geom.KEY_PAIRS)
ADJACENT_PAIRS = ((0, 1), (1, 2), (2, 3))


def physical_body_box(index: int, roll_deg: float, body_x: float, body_y: float):
    axes = stock.rotation_frame(geom.unit(geom.INDEX_AXES[index]), roll_deg)
    center = np.asarray(geom.INDEX_CENTERS[index]) - axes[2] * (
        stock.INDEX_FRONT + HOUSING_H / 2.0
    )
    return center, axes, np.asarray((body_x / 2.0, body_y / 2.0, HOUSING_H / 2.0))


def pocket_projection(roll_deg: float, body_x: float, body_y: float):
    theta = math.radians(roll_deg)
    c, s = abs(math.cos(theta)), abs(math.sin(theta))
    return body_x * c + body_y * s, body_x * s + body_y * c


def pocket_fit(roll_deg: int, body_x: float, body_y: float):
    projected = pocket_projection(roll_deg, body_x, body_y)
    clearances = tuple((POCKET - value) / 2.0 for value in projected)
    return {
        "projectedEnvelopeMm": list(projected),
        "sideClearanceMm": list(clearances),
        "minimumSideClearanceMm": min(clearances),
        "fitsExactGeometry": min(clearances) >= -1e-10,
    }


def physical_root_boxes(index: int, roll_deg: int, body_x: float):
    """Drawing-nominal fixed roots placed at the measured housing rear."""
    point = np.asarray(geom.INDEX_CENTERS[index])
    u, v, z = stock.rotation_frame(geom.unit(geom.INDEX_AXES[index]), roll_deg)
    rear = stock.INDEX_FRONT + HOUSING_H
    metal_u, metal_v = 0.3, 0.7
    pitch_v, outer_width, formed_depth = 4.5, 7.9, 1.8
    start_u = body_x / 2.0 + metal_u / 2.0
    knee_u = (outer_width - metal_u) / 2.0
    boxes = []
    for sign_u in (-1.0, 1.0):
        for sign_v in (-1.0, 1.0):
            p0 = point + u * (sign_u * start_u) + v * (sign_v * pitch_v / 2.0) - z * rear
            p1 = point + u * (sign_u * knee_u) + v * (sign_v * pitch_v / 2.0) - z * (rear + formed_depth)
            direction = geom.unit(p1 - p0)
            cross_v = v
            cross_t = geom.unit(np.cross(direction, cross_v))
            boxes.append(
                (
                    (p0 + p1) / 2.0,
                    np.asarray((cross_v, cross_t, direction)),
                    np.asarray((metal_v / 2.0, metal_u / 2.0, np.linalg.norm(p1 - p0) / 2.0)),
                )
            )
    return boxes


def static_root_margin(index: int, boxes, rwid, rzkd):
    mesh_clear = not any(
        geom.mesh_box_intersects(rwid, box) or geom.mesh_box_intersects(rzkd, box)
        for box in boxes
    )
    screw_clear = stock.screw_collisions(boxes) == 0
    external = prior.local_external_web(index, boxes)
    split = prior.split_web(index, boxes)
    margin = min(external, split) if mesh_clear and screw_clear else -1.0
    return {
        "marginMm": float(margin),
        "externalWebMm": float(external),
        "splitWebMm": None if math.isinf(split) else float(split),
        "retainerAndScrewClear": bool(mesh_clear and screw_clear),
    }


def evaluate_roll_space(body_x: float, body_y: float, cardinal_only: bool):
    allowed = [
        angle for angle in range(180)
        if pocket_fit(angle, body_x, body_y)["fitsExactGeometry"]
        and (not cardinal_only or angle in CARDINAL_ANGLES)
    ]
    rwid = geom.load_triangles("INDEX_FINAL_RWID")
    rzkd = geom.load_triangles("INDEX_FINAL_RZKD")
    roots = {
        (i, angle): physical_root_boxes(i, angle, body_x)
        for i in range(4) for angle in allowed
    }
    bodies = {
        (i, angle): physical_body_box(i, angle, body_x, body_y)
        for i in range(4) for angle in allowed
    }
    static = {
        (i, angle): static_root_margin(i, roots[i, angle], rwid, rzkd)
        for i in range(4) for angle in allowed
    }
    pair_gap = {
        (i, a, b): prior.pair_gap(roots[i, a], roots[i + 1, b])
        for i in range(3) for a in allowed for b in allowed
    }
    body_gap = {
        (i, j, a, b): float(geom.sat_signed(bodies[i, a], bodies[j, b]))
        for i, j in KEY_PAIRS for a in allowed for b in allowed
    }
    root_body_clear = {
        (i, j, a, b): all(
            geom.sat_signed(root_box, bodies[j, b]) > 0.0
            for root_box in roots[i, a]
        )
        for i in range(4) for j in range(4) if j != i
        for a in allowed for b in allowed
    }
    pocket_clear = {
        angle: pocket_fit(angle, body_x, body_y)["minimumSideClearanceMm"]
        for angle in allowed
    }

    best = None
    feasible_count = 0
    for rolls in itertools.product(allowed, repeat=4):
        body_rows = {
            f"I{i + 1}-I{j + 1}": body_gap[i, j, rolls[i], rolls[j]]
            for i, j in KEY_PAIRS
        }
        body_min = min(body_rows.values())
        if body_min < BODY_SAT_GATE - 1e-10:
            continue
        roots_clear = all(
            root_body_clear[i, j, rolls[i], rolls[j]]
            for i in range(4) for j in range(4) if j != i
        )
        if not roots_clear:
            continue
        individual = [static[i, rolls[i]]["marginMm"] for i in range(4)]
        pairs = [pair_gap[i, rolls[i], rolls[i + 1]] for i in range(3)]
        governing = min(*individual, *pairs)
        pocket_min = min(pocket_clear[rolls[i]] for i in range(4))
        if governing >= WEB_GATE - 1e-10:
            feasible_count += 1
        key = (governing, pocket_min, body_min, tuple(-value for value in rolls))
        if best is None or key > best[0]:
            best = (
                key,
                {
                    "rollsDeg": dict(zip(prior.NAMES, rolls)),
                    "equivalentRolls0to360Deg": {
                        prior.NAMES[i]: [rolls[i], rolls[i] + 180] for i in range(4)
                    },
                    "bodySatMm": body_rows,
                    "minimumBodySatMm": body_min,
                    "individualRootMarginsMm": dict(zip(prior.NAMES, individual)),
                    "adjacentChannelWebLowerBoundMm": dict(
                        zip(("I1-I2", "I2-I3", "I3-I4"), pairs)
                    ),
                    "governingZeroClearanceWebMm": governing,
                    "minimumPocketSideClearanceMm": pocket_min,
                    "conservativeSymmetricChannelClearanceMm": max((governing - WEB_GATE) / 2.0, 0.0),
                    "passesBodySat1p20": body_min >= BODY_SAT_GATE - 1e-10,
                    "passesChannelWeb1p50": governing >= WEB_GATE - 1e-10,
                    "fixedRootsRigid": True,
                    "distalPinsOneTimeFormable": True,
                },
            )
    return {
        "bodyAxisMappingMm": {"localU_terminalExit": body_x, "localV_pinRow": body_y},
        "cardinalOnly": cardinal_only,
        "allowedRolls0to179DegAt1DegResolution": allowed,
        "allowedRollCountPer180": len(allowed),
        "allowedRollCountPer360": len(allowed) * 2,
        "feasibleCombinationCount": feasible_count,
        "best": None if best is None else best[1],
    }


def cap_rows():
    rows = {}
    top_axis = stock.INDEX_FRONT - ACTUATOR_PROJECTION
    for i in range(4):
        axis = geom.unit(geom.INDEX_AXES[i])
        normal = geom.unit(stock.INDEX_NORMALS[i])
        cosine = float(np.dot(axis, normal))
        free_gap = top_axis * cosine - stock.CAP_UNDERSIDE_NORMAL_DEPTH
        prototype_free = 0.05
        rows[f"I{i + 1}"] = {
            "axisNormalCosine": cosine,
            "actuatorTopAxisDepthMm": top_axis,
            "measuredFreeGapAlongCapNormalMm": free_gap,
            "bossFor0p05FreeClearanceMm": max(free_gap - prototype_free, 0.0),
            "capDisplacementForTravelMm": {
                name: prototype_free + value * cosine for name, value in TRAVEL.items()
            },
            "localStopRecessFor0p35TravelAt0p05FreeMm": max(
                prototype_free + TRAVEL["upper"] * cosine
                - (stock.HOLDER_TRIM_NORMAL_DEPTH - stock.CAP_UNDERSIDE_NORMAL_DEPTH),
                0.0,
            ),
        }
    return rows


def middle_actual():
    source = json.loads((ROOT / "cad_dump" / "h3p1_w1.json").read_text(encoding="utf-8"))
    names = middle.NAMES
    points = np.asarray([source["centers"][name] for name in names], dtype=float)
    normals = np.asarray([source["surfaceNormals"][name] for name in names], dtype=float)
    axes = np.asarray([source["axisSolution"]["axes"][name] for name in names], dtype=float)
    components = {
        "frozenShellIndexSurface": geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"),
        "RWID": geom.load_triangles("INDEX_FINAL_RWID"),
        "RZKD": geom.load_triangles("INDEX_FINAL_RZKD"),
    }
    middle.POCKET = POCKET
    middle.HOLDER_WIDTH = 12.4
    middle.FOOTPRINT = 6.0
    frozen_lip = max(middle.required_front_lip(normals[i], axes[i]) for i in range(4))
    middle.FOOTPRINT = max(BODY_X, BODY_Y)  # rotation-independent conservative square
    adjusted_lip = max(middle.required_front_lip(normals[i], axes[i]) for i in range(4))

    def run(front_lip: float):
        detail = middle.evaluate_candidate(points, normals, axes, HOUSING_H, front_lip, components)
        return {
            "conservativeFootprintMm": middle.FOOTPRINT,
            "housingHeightMm": HOUSING_H,
            "frontLipMm": front_lip,
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
            "holderRearDatumMm": middle.holder_rear(HOUSING_H, front_lip),
        }

    return {
        "sourceCandidate": "h3p1_w1",
        "fixedOriginalNominalFrontLip": run(frozen_lip),
        "adjustedFrontLipForMeasuredBody": run(adjusted_lip),
        "frontLipIncreaseRequiredMm": adjusted_lip - frozen_lip,
        "qualifier": "6.12 square is conservative over the measured 6.12x6.05 body for unknown MIDDLE roll",
    }


def main():
    direct = evaluate_roll_space(BODY_X, BODY_Y, cardinal_only=True)
    exact = evaluate_roll_space(BODY_X, BODY_Y, cardinal_only=False)
    swapped = evaluate_roll_space(BODY_Y, BODY_X, cardinal_only=True)
    cap = cap_rows()
    body_rear = stock.INDEX_FRONT + HOUSING_H
    spacer = TOTAL_H - HOUSING_H
    payload = {
        "method": {
            "mode": "LOCAL READ-ONLY; Onshape CAD WRITE 0; registry WRITE 0",
            "frozenVersion": "INDEX_FINAL_VALIDATED / 03ede76e83b5c865d9a69c35",
            "configuration": "default frozen local mesh cache",
            "measurementAuthority": "user-supplied owned physical sample, 2026-08-20",
            "terminalGeometryQualifier": "drawing nominal; physical pin/root dimensions not supplied",
        },
        "physicalSample": {
            "part": "ITS-1105-6mm",
            "bodyXmm": BODY_X,
            "bodyYmm": BODY_Y,
            "housingHmm": HOUSING_H,
            "totalHmm": TOTAL_H,
            "actuatorDiameterMm": ACTUATOR_D,
            "actuatorProjectionMm": ACTUATOR_PROJECTION,
            "travelMm": TRAVEL,
            "terminalCount": 4,
            "terminalType": "THT; two pins per opposite side",
            "terminalPolicy": {
                "fixedRoot": "rigid; do not bend",
                "distalPin": "one-time pre-form before assembly allowed",
                "directWiring": True,
                "preSolder": True,
            },
            "consistencyChecksMm": {
                "totalMinusHousing": TOTAL_H - HOUSING_H,
                "reportedActuatorProjection": ACTUATOR_PROJECTION,
                "difference": (TOTAL_H - HOUSING_H) - ACTUATOR_PROJECTION,
            },
        },
        "indexPocket": {
            "axisAligned": {
                "bodyProjectionMm": [BODY_X, BODY_Y],
                "sideClearanceMm": [(POCKET - BODY_X) / 2.0, (POCKET - BODY_Y) / 2.0],
            },
            "exactFitAllowedRolls": exact["allowedRolls0to179DegAt1DegResolution"],
            "warning": "near-square body cannot use arbitrary terminal roll inside a 6.4 square seat",
        },
        "indexActuator": {
            "boreDiameterMm": BORE,
            "actuatorDiameterMm": ACTUATOR_D,
            "radialClearanceMm": (BORE - ACTUATOR_D) / 2.0,
            "coaxial": True,
        },
        "indexRollAndChannel": {
            "physicalAxisMappingCardinal": direct,
            "physicalAxisMappingExactFit": exact,
            "bodyXYMappingSwappedCardinalCheck": swapped,
            "terminalChannelDepthMm": [body_rear, stock.INDEX_HOLDER_REAR],
            "qualifier": "fixed-root boxes retain drawing nominal 4.5 pitch, 7.9 outer width, 0.3x0.7 metal and 1.8 formed depth",
        },
        "indexRear": {
            "measuredBodyRearDepthMm": body_rear,
            "currentPadFrontMm": 11.15,
            "gapWithoutSpacerMm": 11.15 - body_rear,
            "measuredProjectionDerivedSpacerMm": spacer,
            "contactRearWithSpacerMm": body_rear + spacer,
            "preloadAgainstCurrentPadMm": body_rear + spacer - 11.15,
            "preferred": "separate non-moving central spacer; do not extend moving retainer pad",
        },
        "indexCap": {
            "availableStrokeBeforeCurrentHolderStopMm": stock.HOLDER_TRIM_NORMAL_DEPTH - stock.CAP_UNDERSIDE_NORMAL_DEPTH,
            "prototypeFreeClearanceSeedMm": 0.05,
            "perButton": cap,
            "status": "measured stack resolves boss seed; prototype free clearance and printed tolerance still require physical validation",
        },
        "middle": middle_actual(),
        "remainingMeasurementAndPrototypeGates": [
            "fixed-root position/profile and maximum envelope",
            "pin spacing, width and thickness",
            "multi-sample min/max rather than one sample",
            "6.4/6.5/6.6/6.7 pocket coupon",
            "terminal-channel coupon at selected cardinal roll",
            "wire gauge, insulation OD and solder-fillet envelope",
            "explicit user CAD WRITE approval",
        ],
        "decision": {
            "physicalBodyAndActuatorMeasurementAccepted": True,
            "indexGrade": 1,
            "case": "B",
            "sameSkuIndexMiddle": True,
            "middleGeometry": "conditional GO with measured-body front-lip adjustment",
            "cadWrite": "HOLD",
            "reason": "sample dimensions remove body/actuator uncertainty, but root/pin envelope, coupons, wiring envelope and explicit write approval remain",
        },
    }
    output = ROOT / "cad_dump" / "its1105_physical_sample_reaudit.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {output}")
    print("cardinal", direct["best"])
    print("exact", exact["best"])
    print("middle", payload["middle"])


if __name__ == "__main__":
    main()
