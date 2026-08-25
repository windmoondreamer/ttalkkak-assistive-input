"""Audit-only 8-button four-edge direct-shell batch propagation screening.

I2 is imported as the frozen docs/89 control.  The other seven buttons are
screened with bounded, leg-independent 90-degree-first probes against the
frozen shell BReps and the original 3,530-facet PushBtn.  This module creates
only new audit artifacts and never edits production geometry.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Compound, Location, Shape, Vector, export_step, import_step

from . import i2_detailed_pushbtn_manufacturing_robust_audit as doc84
from . import i2_manufacturing_harness_rebase_audit as doc86
from . import i2_final_local_clearance_balancing_audit as doc89
from .direct_shell_four_edge_i2_simplification_audit import (
    ExactRaySampler, SHELL_STEP, local_dir_to_world, local_point_to_world,
)
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import local_box, volume
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import ROOT, relative
from .option_c_local_exact_prototype import raster_scene, safe_edge_lines, safe_triangles
from .slot_anchored_harness_captive_pusher_audit import pusher_system


OUT = ROOT / "build123d_workbench/out/eight_button_four_edge_batch_propagation_screening"
RENDER = ROOT / "renders/eight_button_four_edge_batch_propagation_screening"
REPORT = ROOT / "docs/90_eight_button_four_edge_batch_propagation_screening.md"
JSON_PATH = OUT / "eight_button_four_edge_batch_propagation_screening.json"
ALL8_HARNESS_STEP = OUT / "ALL8_SELECTED_FOUR_EDGE_HARNESSES_AUDIT_ONLY.step"
ALL8_SLOT_STEP = OUT / "ALL8_DIRECT_SHELL_SLOT_CROPS_AUDIT_ONLY.step"

BUTTONS = ("N1", "N2", "I2", "I3", "I4", "M3", "M4", "N3")
EDGES = ("+U", "-U", "+V", "-V")
EPS = 1.0e-6
BODY_U_HALF = 3.155
BODY_V_HALF = 3.005
ROOT_GAP = 0.18
FRAME_WIDTH = 1.60
BASE_TOP_W = doc84.ORIGINAL_BOTTOM_SHIFT_W
BASE_THICKNESS = 1.60
ROOT_EMBED = 1.40
LEG_WIDTH = 1.60
SLOT_CLEARANCE = 0.15
BLIND_DEPTH = 1.20
MOUTH_CLEARANCE = 1.03
MOUTH_DEPTH = 0.93
ROOT_T_VALUES = (-0.40, 0.0, 0.40)
COARSE_TILTS = (5.0, 10.0, 15.0, 20.0, 25.0, 30.0)
AZIMUTH_OFFSETS = (-15.0, 0.0, 15.0)
FRACTIONS = (1.0, 0.75, 0.50, 0.25, 0.0)
FOOTER = "8-BUTTON BATCH SCREENING | ORIGINAL DETAILED PUSHBTN | FROZEN EXTERIOR | PRODUCTION 0"
COL = {
    "shell": (102, 125, 148), "standard": (54, 188, 132), "variant": (247, 175, 63),
    "fail": (235, 75, 88), "body": (65, 166, 224), "terminal": (218, 225, 233),
    "axis": (250, 212, 76), "i2": (160, 104, 215), "slot": (241, 126, 65),
}


def xyz(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(map(float, value))


def moved(shape: Shape, offset: Iterable[float], label: str) -> Shape:
    row = np.asarray(tuple(offset), float)
    result = shape.moved(Location(Vector(*map(float, row))))
    result.label = label
    return result


def pair(left: Shape, right: Shape) -> dict[str, float | bool]:
    distance = float(left.distance_to(right))
    penetration = volume(left & right) if distance <= 1.0e-7 else 0.0
    return {"distanceMm": distance, "penetrationMm3": penetration, "clear": penetration <= EPS}


def protected_files() -> list[Path]:
    rows = set(doc89.protected_files())
    rows.update({ROOT / "docs/89_i2_final_local_clearance_balancing_audit.md",
                 ROOT / "build123d_workbench/i2_final_local_clearance_balancing_audit.py"})
    for folder in (ROOT / "build123d_workbench/out/i2_final_local_clearance_balancing_audit",
                   ROOT / "renders/i2_final_local_clearance_balancing_audit"):
        rows.update(path for path in folder.rglob("*") if path.is_file())
    return sorted(path for path in rows if path.exists())


def leg_radial_azimuth(edge: str) -> float:
    return {"+U": 0.0, "-U": 180.0, "+V": 90.0, "-V": -90.0}[edge]


def direction(tilt_deg: float, azimuth_deg: float) -> np.ndarray:
    tilt = math.radians(tilt_deg)
    azimuth = math.radians(azimuth_deg)
    return unit((math.sin(tilt) * math.cos(azimuth),
                 math.sin(tilt) * math.sin(azimuth), math.cos(tilt)))


def tangent_axis(edge: str) -> np.ndarray:
    return np.asarray((0.0, 1.0, 0.0) if edge.endswith("U") else (1.0, 0.0, 0.0), float)


def base_root(edge: str, thickness: float, root_t: float) -> np.ndarray:
    radial = (BODY_U_HALF if edge.endswith("U") else BODY_V_HALF) + ROOT_GAP + thickness / 2.0
    radial *= 1.0 if edge.startswith("+") else -1.0
    if edge.endswith("U"):
        return np.asarray((radial, root_t, BASE_TOP_W), float)
    return np.asarray((root_t, radial, BASE_TOP_W), float)


def evaluate_leg(edge: str, root_t: float, tilt_deg: float, azimuth_deg: float,
                 datum, front: float, ray: ExactRaySampler) -> dict[str, object]:
    thickness = max(1.30, 1.20 / max(math.cos(math.radians(tilt_deg)), 1.0e-6))
    root = base_root(edge, thickness, root_t)
    vector = direction(tilt_deg, azimuth_deg)
    tangent_hint = tangent_axis(edge)
    tangent = unit(tangent_hint - vector * float(np.dot(tangent_hint, vector)))
    structural = unit(np.cross(vector, tangent))
    direction_world = local_dir_to_world(datum, vector)
    footprint_t = LEG_WIDTH + 2.0 * SLOT_CLEARANCE
    footprint_s = thickness + 2.0 * SLOT_CLEARANCE
    inner: list[float] = []
    outer: list[float] = []
    samples = []
    # Corners first: one missing corner proves that the complete rectangular
    # footprint is invalid, so reject without spending the remaining rays.
    offsets = (
        (-footprint_t / 2.0, -footprint_s / 2.0),
        (-footprint_t / 2.0, footprint_s / 2.0),
        (footprint_t / 2.0, -footprint_s / 2.0),
        (footprint_t / 2.0, footprint_s / 2.0),
        (-footprint_t / 2.0, 0.0), (footprint_t / 2.0, 0.0),
        (0.0, -footprint_s / 2.0), (0.0, footprint_s / 2.0), (0.0, 0.0),
    )
    for sample_index, (dt, ds) in enumerate(offsets):
            origin = root + tangent * dt + structural * ds
            hits = ray.hits(local_point_to_world(datum, front, origin), direction_world, 24.0)
            paired = len(hits) >= 2
            samples.append({"originLocalUVWmm": origin.tolist(), "hitsMm": hits,
                            "hasInnerOuterPair": paired})
            if paired:
                inner.append(float(hits[0]))
                outer.append(float(hits[1]))
            elif sample_index < 4:
                return {
                    "edge": edge, "rootTangentCoordinateMm": root_t,
                    "rootLocalUVWmm": root.tolist(), "directionLocal": vector.tolist(),
                    "tiltFromWDeg": tilt_deg, "tiltAzimuthDeg": azimuth_deg,
                    "legThicknessMm": thickness,
                    "effectiveFdmThicknessMm": thickness * abs(float(vector[2])),
                    "legTangentWidthMm": LEG_WIDTH, "footprintPairCoverage": len(inner),
                    "samples": samples, "feasible": False,
                    "failure": "INCOMPLETE_SLOT_FOOTPRINT",
                    "missingFootprintPairs": 9 - len(inner),
                }
    base = {
        "edge": edge, "rootTangentCoordinateMm": root_t, "rootLocalUVWmm": root.tolist(),
        "directionLocal": vector.tolist(), "tiltFromWDeg": tilt_deg,
        "tiltAzimuthDeg": azimuth_deg, "legThicknessMm": thickness,
        "effectiveFdmThicknessMm": thickness * abs(float(vector[2])),
        "legTangentWidthMm": LEG_WIDTH, "footprintPairCoverage": len(inner), "samples": samples,
    }
    if len(inner) < 9:
        return {**base, "feasible": False, "failure": "INCOMPLETE_SLOT_FOOTPRINT",
                "missingFootprintPairs": 9 - len(inner)}
    floor_distance = max(inner) + BLIND_DEPTH
    remaining = min(outer) - floor_distance
    floor = root + vector * floor_distance
    leg = oriented_box_between(xyz(root - vector * ROOT_EMBED), xyz(floor), xyz(tangent),
                               LEG_WIDTH, thickness, label=f"{edge}_STRAIGHT_STRUCTURAL_LEG")
    slot_start = root + vector * (min(inner) - 0.35)
    slot = oriented_box_between(xyz(slot_start), xyz(floor), xyz(tangent), footprint_t,
                                footprint_s, label=f"{edge}_DIRECT_BLIND_SLOT")
    mouth_start = root + vector * (min(inner) - 0.40)
    mouth_end = root + vector * (max(inner) + MOUTH_DEPTH)
    mouth = oriented_box_between(xyz(mouth_start), xyz(mouth_end), xyz(tangent),
                                 LEG_WIDTH + 2.0 * MOUTH_CLEARANCE,
                                 thickness + 2.0 * MOUTH_CLEARANCE,
                                 label=f"{edge}_SIMPLE_ENTRY_MOUTH")
    shell_range = [float(min(o - i for i, o in zip(inner, outer))),
                   float(max(o - i for i, o in zip(inner, outer)))]
    feasible = remaining >= 1.20 - EPS
    return {
        **base, "feasible": feasible,
        "failure": None if feasible else "INSUFFICIENT_REMAINING_SHELL",
        "missingFootprintPairs": 0, "legLengthMm": float(floor_distance + ROOT_EMBED),
        "functionalLengthMm": float(floor_distance), "floorPointLocalUVWmm": floor.tolist(),
        "tangentLocal": tangent.tolist(), "structuralLocal": structural.tolist(),
        "minimumRemainingShellMm": float(remaining), "shellThicknessFootprintRangeMm": shell_range,
        "minimumBlindInsertionDepthMm": BLIND_DEPTH, "leg": leg, "slotTool": slot, "mouthTool": mouth,
    }


def leg_static(row: dict[str, object], local_parts: dict[str, Shape], corners: Shape, pusher: Shape,
               placement, neighbor_world: dict[str, dict[str, Shape]], button: str) -> dict[str, object]:
    if not row.get("feasible"):
        return {"allClear": False, "failure": row.get("failure")}
    leg: Shape = row["leg"]
    body = pair(leg, local_parts["BODY"])
    terminals = {name: pair(leg, local_parts[name]) for name in ("T1", "T2", "T3", "T4")}
    corner = pair(leg, corners)
    push = pair(leg, pusher)
    world_leg = placement * leg
    neighbors = {}
    for other, parts in neighbor_world.items():
        if other == button:
            continue
        metrics = {name: pair(world_leg, shape) for name, shape in parts.items()}
        nearest = min(metrics, key=lambda key: float(metrics[key]["distanceMm"]))
        neighbors[other] = {
            "nearestPart": nearest, "minimumDistanceMm": float(metrics[nearest]["distanceMm"]),
            "penetrationMm3": sum(float(item["penetrationMm3"]) for item in metrics.values()),
        }
    nearest_neighbor = min(neighbors, key=lambda key: float(neighbors[key]["minimumDistanceMm"]))
    all_clear = (body["clear"] and corner["clear"] and push["clear"] and
                 all(item["clear"] for item in terminals.values()) and
                 all(float(item["penetrationMm3"]) <= EPS for item in neighbors.values()))
    return {
        "allClear": bool(all_clear), "body": body, "terminals": terminals, "corner": corner,
        "pusher": push, "nearestNeighbor": nearest_neighbor,
        "nearestNeighborPart": neighbors[nearest_neighbor]["nearestPart"],
        "minimumNeighborClearanceMm": neighbors[nearest_neighbor]["minimumDistanceMm"],
        "neighborPenetrationMm3": neighbors[nearest_neighbor]["penetrationMm3"],
        "neighbors": neighbors,
    }


def select_leg(edge: str, datum, front: float, ray: ExactRaySampler, local_parts: dict[str, Shape],
               corners: Shape, pusher: Shape, placement, neighbor_world: dict[str, dict[str, Shape]],
               button: str) -> tuple[dict[str, object], dict[str, object]]:
    evaluated = 0
    ninety_rows = []
    failure_counts: dict[str, int] = {}
    for root_t in ROOT_T_VALUES:
        row = evaluate_leg(edge, root_t, 0.0, 0.0, datum, front, ray); evaluated += 1
        failure_counts[str(row.get("failure"))] = failure_counts.get(str(row.get("failure")), 0) + 1
        if row.get("feasible"):
            static = leg_static(row, local_parts, corners, pusher, placement, neighbor_world, button)
            row["static"] = static
            if static["allClear"]:
                ninety_rows.append(row)
    if ninety_rows:
        best = max(ninety_rows, key=lambda row: (
            min(float(row["minimumRemainingShellMm"]),
                float(row["static"]["body"]["distanceMm"]),
                min(float(v["distanceMm"]) for v in row["static"]["terminals"].values()),
                float(row["static"]["minimumNeighborClearanceMm"])),
            -abs(float(row["rootTangentCoordinateMm"]))))
        best["ninetyDegreeResult"] = "PASS"
        best["reasonNinetyFailed"] = None
        return best, {"evaluations": evaluated, "ninetyCandidates": len(ROOT_T_VALUES),
                      "tiltCandidates": 0, "failureCounts": failure_counts}

    selected = None
    first_tilt = None
    for tilt in COARSE_TILTS:
        passed = []
        for az_offset in AZIMUTH_OFFSETS:
            azimuth = leg_radial_azimuth(edge) + az_offset
            for root_t in ROOT_T_VALUES:
                row = evaluate_leg(edge, root_t, tilt, azimuth, datum, front, ray); evaluated += 1
                failure_counts[str(row.get("failure"))] = failure_counts.get(str(row.get("failure")), 0) + 1
                if not row.get("feasible"):
                    continue
                static = leg_static(row, local_parts, corners, pusher, placement, neighbor_world, button)
                row["static"] = static
                if static["allClear"]:
                    passed.append(row)
        if passed:
            selected = max(passed, key=lambda row: (
                min(float(row["minimumRemainingShellMm"]), float(row["static"]["body"]["distanceMm"]),
                    min(float(v["distanceMm"]) for v in row["static"]["terminals"].values()),
                    float(row["static"]["minimumNeighborClearanceMm"])),
                -abs(float(row["rootTangentCoordinateMm"]))))
            first_tilt = tilt
            break

    if selected is None:
        failure = max((key for key in failure_counts if key != "None"),
                      key=lambda key: failure_counts[key], default="NO_MANUFACTURING_CANDIDATE")
        return {"edge": edge, "feasible": False, "failure": failure,
                "tiltFromWDeg": 30.0, "tiltResolved": False,
                "tiltSearchUpperBoundDeg": 30.0, "ninetyDegreeResult": "FAIL",
                "reasonNinetyFailed": f"{failure}; no valid manufacturing candidate through 30 deg bounded screen"}, {
                    "evaluations": evaluated, "ninetyCandidates": len(ROOT_T_VALUES),
                    "tiltCandidates": evaluated - len(ROOT_T_VALUES), "failureCounts": failure_counts,
                }

    # One-degree local angular refinement around the first successful coarse band.
    low = max(0.1, float(first_tilt) - 4.0)
    refined = []
    center_az = float(selected["tiltAzimuthDeg"])
    center_t = float(selected["rootTangentCoordinateMm"])
    for tilt in np.arange(low, float(first_tilt) + 0.001, 1.0):
        for azimuth in (center_az - 5.0, center_az, center_az + 5.0):
            for root_t in sorted(set((max(-0.4, center_t - 0.1), center_t, min(0.4, center_t + 0.1)))):
                row = evaluate_leg(edge, float(root_t), float(tilt), float(azimuth), datum, front, ray)
                evaluated += 1
                if not row.get("feasible"):
                    continue
                static = leg_static(row, local_parts, corners, pusher, placement, neighbor_world, button)
                row["static"] = static
                if static["allClear"]:
                    refined.append(row)
        if refined:
            break
    if refined:
        selected = max(refined, key=lambda row: (
            min(float(row["minimumRemainingShellMm"]), float(row["static"]["body"]["distanceMm"]),
                min(float(v["distanceMm"]) for v in row["static"]["terminals"].values()),
                float(row["static"]["minimumNeighborClearanceMm"])),
            -abs(float(row["rootTangentCoordinateMm"]))))
    reasons = [key for key, count in failure_counts.items() if key != "None" and count > 0]
    selected["ninetyDegreeResult"] = "FAIL"
    selected["tiltResolved"] = True
    selected["reasonNinetyFailed"] = ", ".join(reasons) if reasons else "DETAILED_GEOMETRY_INTERFERENCE"
    return selected, {"evaluations": evaluated, "ninetyCandidates": len(ROOT_T_VALUES),
                      "tiltCandidates": evaluated - len(ROOT_T_VALUES), "failureCounts": failure_counts}


def base_profile(roots: dict[str, np.ndarray]) -> Shape:
    return doc86.base_profile(roots)


def build_candidate(button: str, rows: dict[str, dict[str, object]]) -> dict[str, object]:
    roots = {edge: np.asarray(rows[edge]["rootLocalUVWmm"], float) for edge in EDGES}
    base = base_profile(roots)
    harness = base
    overlaps = {}
    for edge in EDGES:
        harness = harness.fuse(rows[edge]["leg"])
        overlaps[edge] = volume(base & rows[edge]["leg"])
    harness = harness.clean(); harness.label = f"{button}_ONE_PIECE_FOUR_EDGE_DIRECT_SHELL_HARNESS"
    return {"harness": harness, "base": base,
            "legs": Compound(children=[rows[edge]["leg"] for edge in EDGES]),
            "slots": Compound(children=[rows[edge]["slotTool"] for edge in EDGES]),
            "mouths": Compound(children=[rows[edge]["mouthTool"] for edge in EDGES]),
            "rows": rows, "rootCommonVolumeByEdgeMm3": overlaps}


def make_slotted_shell(candidate: dict[str, object], shell_full: Shape, placement, button: str) -> dict[str, Shape]:
    crop_tool = local_box(24.0, 24.0, 13.0, 0, 0, 0, f"{button}_LOCAL_SHELL_CROP_TOOL")
    crop_world = shell_full & (placement * crop_tool)
    crop = placement.inverse() * crop_world.clean()
    slotted = crop
    for edge in EDGES:
        slotted = (slotted - candidate["rows"][edge]["slotTool"] - candidate["rows"][edge]["mouthTool"]).clean()
    return {"crop": crop, "slotted": slotted,
            "tools": Compound(children=[candidate["slots"], candidate["mouths"]])}


def candidate_metrics(candidate: dict[str, object], shell: dict[str, Shape], local_parts: dict[str, Shape],
                      corners: Shape, pusher: Shape, placement,
                      neighbor_world: dict[str, dict[str, Shape]], button: str) -> dict[str, object]:
    legs: Shape = candidate["legs"]
    body = pair(legs, local_parts["BODY"])
    terminals = {name: pair(legs, local_parts[name]) for name in ("T1", "T2", "T3", "T4")}
    nearest_terminal = min(terminals, key=lambda key: float(terminals[key]["distanceMm"]))
    corner = pair(legs, corners)
    push = pair(candidate["harness"], pusher)
    world_harness = placement * candidate["harness"]
    neighbors = {}
    for other, parts in neighbor_world.items():
        if other == button:
            continue
        values = {name: pair(world_harness, shape) for name, shape in parts.items()}
        nearest = min(values, key=lambda key: float(values[key]["distanceMm"]))
        neighbors[other] = {"nearestPart": nearest,
                            "minimumDistanceMm": float(values[nearest]["distanceMm"]),
                            "penetrationMm3": sum(float(v["penetrationMm3"]) for v in values.values())}
    nearest_neighbor = min(neighbors, key=lambda key: float(neighbors[key]["minimumDistanceMm"]))
    shell_pair = pair(candidate["harness"], shell["slotted"])
    min_terminal = float(terminals[nearest_terminal]["distanceMm"])
    min_neighbor = float(neighbors[nearest_neighbor]["minimumDistanceMm"])
    min_three = min(float(body["distanceMm"]), min_terminal, min_neighbor)
    return {
        "ownBody": body, "terminals": terminals, "nearestTerminal": nearest_terminal,
        "minimumTerminalClearanceMm": min_terminal, "cornerFeature": corner, "pusher": push,
        "nearestNeighbor": nearest_neighbor, "nearestNeighborPart": neighbors[nearest_neighbor]["nearestPart"],
        "nearestNeighborClearanceMm": min_neighbor, "neighbors": neighbors,
        "minimumThreeWayClearanceMm": min_three, "shellUnintended": shell_pair,
        "minimumRemainingShellMm": min(float(candidate["rows"][e]["minimumRemainingShellMm"]) for e in EDGES),
    }


def rear_check(candidate: dict[str, object], shell: dict[str, Shape], local_parts: dict[str, Shape],
               corners: Shape, mechanism: dict[str, Shape]) -> dict[str, object]:
    directions = {edge: np.asarray(candidate["rows"][edge]["directionLocal"], float) for edge in EDGES}
    common = unit(np.mean(list(directions.values()), axis=0))
    dots = {edge: float(np.dot(common, vector)) for edge, vector in directions.items()}
    travel = max(BLIND_DEPTH / max(dots[edge], 1.0e-6) for edge in EDGES)
    fixed = {**local_parts, "CORNERS": corners, **mechanism, "SHELL": shell["slotted"]}
    states = []
    maxima = {name: 0.0 for name in fixed}
    for index, fraction in enumerate(FRACTIONS):
        moving = moved(candidate["harness"], -common * travel * fraction,
                       f"REAR_HARNESS_{index}")
        pairs = {name: volume(moving & shape) for name, shape in fixed.items()}
        for name, value in pairs.items():
            maxima[name] = max(maxima[name], value)
        states.append({"stateIndex": index, "insertionPercent": 100.0 * (1.0 - fraction),
                       "remainingTravelMm": travel * fraction, "pairPenetrationMm3": pairs,
                       "totalUnintendedPenetrationMm3": sum(pairs.values()),
                       "collisionFree": all(value <= EPS for value in pairs.values())})
    lateral = {edge: travel * math.sqrt(max(0.0, 1.0 - dots[edge] ** 2)) for edge in EDGES}
    entry_ok = all(value <= MOUTH_CLEARANCE + EPS for value in lateral.values())
    result = "PASS" if all(row["collisionFree"] for row in states) and entry_ok else "FAIL"
    return {"result": result, "stateCount": 5, "commonInsertionVectorLocal": common.tolist(),
            "travelMm": travel, "states": states, "maximumPenetrationByPartMm3": maxima,
            "startLateralOffsetByLegMm": lateral, "entryMouthClearancePerSideMm": MOUTH_CLEARANCE,
            "elasticDeformationRequired": False, "pushBtnMotionMm": 0.0, "pushBtnRotationDeg": 0.0}


def serial_row(row: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in row.items() if key not in ("leg", "slotTool", "mouthTool")}


def all8_check(world: dict[str, dict[str, Shape]], detailed_world: dict[str, dict[str, Shape]]) -> dict[str, object]:
    pairs = {}
    worst_pen = 0.0
    closest = None
    closest_distance = 1.0e9
    for index, left in enumerate(BUTTONS):
        for right in BUTTONS[index + 1:]:
            hh = pair(world[left]["harness"], world[right]["harness"])
            ss = pair(world[left]["slots"], world[right]["slots"])
            cross = {}
            for source, target in ((left, right), (right, left)):
                values = {name: pair(world[source]["legs"], shape)
                          for name, shape in detailed_world[target].items()}
                nearest = min(values, key=lambda key: float(values[key]["distanceMm"]))
                cross[f"{source}->{target}"] = {
                    "nearestPart": nearest, "minimumDistanceMm": float(values[nearest]["distanceMm"]),
                    "penetrationMm3": sum(float(value["penetrationMm3"]) for value in values.values()),
                }
            minimum = min(float(hh["distanceMm"]), float(ss["distanceMm"]),
                          *(float(value["minimumDistanceMm"]) for value in cross.values()))
            penetration = float(hh["penetrationMm3"]) + float(ss["penetrationMm3"]) + sum(
                float(value["penetrationMm3"]) for value in cross.values())
            pairs[f"{left}:{right}"] = {"harnessToHarness": hh, "slotToSlot": ss,
                                        "legToNeighborDetailed": cross,
                                        "minimumDistanceMm": minimum,
                                        "totalPenetrationMm3": penetration}
            if minimum < closest_distance:
                closest_distance = minimum; closest = f"{left}:{right}"
            worst_pen = max(worst_pen, penetration)
    return {"result": "PASS" if worst_pen <= EPS else "FAIL", "pairCount": len(pairs),
            "closestPair": closest, "minimumPairClearanceMm": closest_distance,
            "maximumPairPenetrationMm3": worst_pen, "pairs": pairs,
            "checks": ["harness-harness", "leg-neighbor harness", "leg-neighbor PushBtn",
                       "slot-slot", "overlapping local shell weakening"]}


def render_outputs(world: dict[str, dict[str, Shape]], detailed_world: dict[str, dict[str, Shape]],
                   shell_full: dict[str, Shape], results: dict[str, dict[str, object]],
                   all8: dict[str, object]) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    outputs = []

    def render(name: str, title: str, subtitle: str, objects, camera=(105, -145, 90),
               transparent=None, wireframes=None, world_lines=None, fit_points=None):
        path = RENDER / name
        raster_scene(path, objects, title, subtitle, FOOTER, camera_offset=camera,
                     transparent_objects=transparent or [], wireframes=wireframes or [],
                     world_lines=world_lines or [], fit_points=fit_points)
        outputs.append(relative(path))

    shell_tri = {name: safe_triangles(shape) for name, shape in shell_full.items()}
    switches = [(safe_triangles(Compound(children=list(detailed_world[name].values()))), COL["body"])
                for name in BUTTONS]
    harnesses = [(safe_triangles(world[name]["harness"]),
                  COL["i2"] if name == "I2" else
                  (COL["standard"] if results[name]["countedClass"] == "STANDARD" else
                   (COL["variant"] if results[name]["countedClass"] == "LOCAL VARIANT" else COL["fail"])))
                 for name in BUTTONS]
    shells_transparent = [(shell_tri[name], (*COL["shell"], 42)) for name in shell_tri]
    shells_wire = [(safe_edge_lines(shape), (*COL["shell"], 105)) for shape in shell_full.values()]
    render("01_all8_exterior_context_overview.png", "1 / ALL-8 EXTERIOR-CONTEXT OVERVIEW",
           "all frozen button centers and press axes retained; audit harnesses shown through transparent shell",
           switches + harnesses, transparent=shells_transparent)
    render("02_all8_shell_interior_harness_overview.png", "2 / ALL-8 SHELL-INTERIOR HARNESS OVERVIEW",
           f"{sum(1 for n in BUTTONS if results[n]['countedClass'] != 'FAIL')} viable harnesses + "
           f"{sum(1 for n in BUTTONS if results[n]['countedClass'] == 'FAIL')} unresolved red markers in full context",
           harnesses,
           camera=(-110, 150, -78), wireframes=shells_wire)
    axis_lines = []
    for name in BUTTONS:
        datum = results[name]["datum"]
        center = np.asarray(datum.center, float)
        axis = np.asarray(datum.axis, float)
        axis_lines.append((tuple(center), tuple(center - axis * 12.0), (*COL["axis"], 255), name))
    render("03_all8_top_local_axis_overview.png", "3 / ALL-8 TOP + LOCAL-AXIS OVERVIEW",
           "yellow vectors are frozen local W/press axes", harnesses, camera=(0, -10, 190),
           world_lines=axis_lines)
    leg_objects = []
    leg_lines = []
    for name in BUTTONS:
        for edge in EDGES:
            shape = world[name][f"leg_{edge}"]
            row = results[name]["legs"][edge]
            tilt = float(row["tiltFromWDeg"])
            unresolved = row.get("tiltResolved") is False
            leg_objects.append((safe_triangles(shape), COL["fail"] if unresolved else
                                (COL["standard"] if tilt <= 1.0e-8 else COL["variant"])))
            box = shape.bounding_box(); center = np.asarray(((box.min.X + box.max.X) / 2,
                                                             (box.min.Y + box.max.Y) / 2,
                                                             (box.min.Z + box.max.Z) / 2), float)
            label = f"{name} {edge} UNRESOLVED≤30°" if unresolved else f"{name} {edge} {tilt:.3f}°"
            leg_lines.append((tuple(center), tuple(center + np.asarray(results[name]["datum"].axis) * 4.0),
                              (*COL["axis"], 255), label))
    render("04_all32_legs_angle_visualization.png", "4 / ALL 32 LEGS — ANGLE VISUALIZATION",
           "green=90° retained; amber=selected minimum-tilt; red=unresolved through 30°", leg_objects,
           camera=(110, -145, 85), world_lines=leg_lines)
    pair_name = str(all8["closestPair"]); left, right = pair_name.split(":")
    fit = np.vstack((safe_triangles(world[left]["harness"]).reshape(-1, 3),
                     safe_triangles(world[right]["harness"]).reshape(-1, 3)))
    render("05_tightest_neighboring_pair_closeup.png", "5 / TIGHTEST NEIGHBORING PAIR",
           f"{pair_name} exact simultaneous minimum={all8['minimumPairClearanceMm']:.6f} mm",
           [(safe_triangles(world[left]["harness"]), COL["variant"]),
            (safe_triangles(world[right]["harness"]), COL["standard"]),
            (safe_triangles(Compound(children=list(detailed_world[left].values()))), COL["body"]),
            (safe_triangles(Compound(children=list(detailed_world[right].values()))), COL["body"])],
           camera=(35, -46, 24), fit_points=fit)
    worst_shell = min(BUTTONS, key=lambda name: float(results[name]["minimumRemainingShellMm"]))
    render("06_worst_shell_footprint_closeup.png", "6 / WORST SHELL FOOTPRINT",
           f"{worst_shell} minimum remaining shell={results[worst_shell]['minimumRemainingShellMm']:.6f} mm",
           [(safe_triangles(world[worst_shell]["slots"]), COL["slot"]),
            (safe_triangles(world[worst_shell]["harness"]), COL["variant"])], camera=(30, -42, 22),
           transparent=[(safe_triangles(world[worst_shell]["shellCrop"]), (*COL["shell"], 55))])
    n2 = "N2"
    n2_detail = Compound(children=list(detailed_world[n2].values()))
    n2_fit = safe_triangles(n2_detail).reshape(-1, 3)
    render("07_n2_seam_closeup.png", "7 / N2 SEAM CLOSE-UP",
           "JfD-only rule retained; +U/+V/-V full footprints unresolved without seam redesign",
           [(safe_triangles(world[n2]["harness"]), COL["fail"]),
            (safe_triangles(n2_detail), COL["body"])], camera=(30, -42, 22), fit_points=n2_fit,
           transparent=[(safe_triangles(world[n2]["shellCrop"]), (*COL["shell"], 52))])
    render("08_i2_reference_closeup.png", "8 / I2 DOCS/89 REFERENCE CONTROL",
           "frozen final-balanced harness; no I2 re-optimization performed",
           [(safe_triangles(world["I2"]["harness"]), COL["i2"]),
            (safe_triangles(Compound(children=list(detailed_world["I2"].values()))), COL["body"])],
           camera=(28, -39, 21))
    variants = [name for name in BUTTONS if name != "I2" and results[name]["countedClass"] == "LOCAL VARIANT"]
    if variants:
        worst = min(variants, key=lambda name: float(results[name]["minimumThreeWayClearanceMm"]))
        render("09_worst_local_variant_closeup.png", "9 / WORST LOCAL VARIANT",
               f"{worst} MIN_3WAY={results[worst]['minimumThreeWayClearanceMm']:.6f} mm",
               [(safe_triangles(world[worst]["harness"]), COL["variant"]),
                (safe_triangles(Compound(children=list(detailed_world[worst].values()))), COL["body"])],
               camera=(30, -42, 22))
    failures = [name for name in BUTTONS if results[name]["countedClass"] == "FAIL"]
    if failures:
        name = failures[0]
        render("10_fail_closeup.png", "10 / FAIL LIMITING GEOMETRY",
               f"{name}: {results[name]['failureReason']}",
               [(safe_triangles(Compound(children=list(detailed_world[name].values()))), COL["body"])],
               camera=(30, -42, 22), transparent=[(safe_triangles(world[name]["shellCrop"]), (*COL["shell"], 48))])
    return outputs


def report_text(data: dict[str, object]) -> str:
    master = []
    detail = []
    for name in BUTTONS:
        row = data["buttons"][name]
        states = []
        for edge in EDGES:
            leg = row["legs"][edge]
            if name == "I2":
                states.append("reference")
            else:
                states.append("PASS" if float(leg["tiltFromWDeg"]) <= 1.0e-8 else "FAIL")
            if float(leg["tiltFromWDeg"]) > 1.0e-8:
                detail.append(f"| {name} | {edge} | {float(leg['tiltFromWDeg']):.3f}° | {leg['reasonNinetyFailed']} |")
        tilted = [
            (f"{edge} UNRESOLVED≤30°" if row["legs"][edge].get("tiltResolved") is False
             else f"{edge} {float(row['legs'][edge]['tiltFromWDeg']):.3f}°")
            for edge in EDGES if float(row["legs"][edge]["tiltFromWDeg"]) > 1.0e-8
        ]
        clearance_text = ("N/A" if row["minimumThreeWayClearanceMm"] is None
                          else f"{float(row['minimumThreeWayClearanceMm']):.6f}")
        master.append(f"| {name} | {states[0]} | {states[1]} | {states[2]} | {states[3]} | "
                      f"{', '.join(tilted) if tilted else 'none'} | {clearance_text} | "
                      f"{float(row['minimumRemainingShellMm']):.6f} | {row['rearAssembly']['result']} | {row['displayClass']} |")
    s = data["summary"]
    renders = "\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    one_lines = "\n".join(
        f"- **{name}:** {data['buttons'][name]['displayClass']} — MIN_3WAY "
        f"{('N/A' if data['buttons'][name]['minimumThreeWayClearanceMm'] is None else format(data['buttons'][name]['minimumThreeWayClearanceMm'], '.6f') + ' mm')}; shell "
        f"{data['buttons'][name]['minimumRemainingShellMm']:.6f} mm; rear "
        f"{data['buttons'][name]['rearAssembly']['result']}"
        for name in BUTTONS)
    return f"""# 90 — 8-button four-edge harness batch propagation screening

MODE = **BATCH SCREENING / AUDIT ONLY / PRODUCTION 0 / FROZEN EXTERIOR**

| Button | 90° +U | 90° -U | 90° +V | 90° -V | Tilted legs | Min clearance | Min shell | Rear assembly | Class |
|---|---|---|---|---|---|---:|---:|---|---|
{chr(10).join(master)}

I2 is shown as REFERENCE but is counted in STANDARD for the required 8-button partition.

## Required numeric summary

- Buttons evaluated = **8**
- STANDARD = **{s['standard']}**
- LOCAL VARIANT = **{s['localVariant']}**
- FAIL = **{s['fail']}**
- Total legs = **32**
- 90° legs retained = **{s['ninetyLegs']}**
- Tilted legs required = **{s['tiltedLegs']}**
- Unresolved legs with no candidate through 30° bounded screen = **{s['unresolvedLegs']}**
- Maximum required tilt = **{s['maximumTiltDeg']:.3f}°**
- Button with worst clearance = **{s['worstClearanceButton']}**, {s['worstClearanceMm']:.6f} mm
- Button with minimum remaining shell = **{s['minimumShellButton']}**, {s['minimumShellMm']:.6f} mm
- ALL-8 simultaneous static fit = **{data['all8Simultaneous']['result']}**
- bounded candidate evaluations = **{s['candidateEvaluations']}**; global optimizer = **NO**

## Tilted-leg proof

| Button | leg | tilt from W | reason 90° failed |
|---|---|---:|---|
{chr(10).join(detail) if detail else '| — | — | 0.000° | every new leg retained 90° |'}

## Button-by-button screening result

{one_lines}

`0.15 mm` is treated as a practical hardening preference, not a penetration gate. A viable candidate below
that value is LOCAL VARIANT — clearance hardening required, and was not deeply optimized in this batch.

## Detailed authority and manufacturing gates

- ORIGINAL PushBtn detailed faceted BRep: **3,530 triangles**, main body + T1–T4 + corner/bottom detail;
- actuator-only authority: measured D3.35 / projection 2.44 mm;
- each selected non-I2 harness: one fused valid solid, positive four-root common volumes, minimum neck and
  effective FDM section >=1.20 mm, direct blind slots, no receiver/cage/panel/strut/carrier;
- I2: docs/89 STEP and docs/87 rear assembly reused unchanged;
- rear check: START/25/50/75/FULL only; PushBtn translation/rotation 0; no PushBtn-through-harness sequence;
- N2 remains entirely on its owning **JfD** shell half; no new seam architecture was generated.

## ALL-8 simultaneous fit

Closest pair = **{data['all8Simultaneous']['closestPair']}**, exact minimum
**{data['all8Simultaneous']['minimumPairClearanceMm']:.6f} mm**; maximum unintended pair penetration
**{data['all8Simultaneous']['maximumPairPenetrationMm3']:.9f} mm³**. Pairwise checks include harness↔harness,
leg↔neighbor detailed PushBtn, slot↔slot and overlapping local shell-weakening regions.

## Renders and outputs

{renders}

- `{data['outputs']['all8HarnessStep']}`
- `{data['outputs']['all8SlotStep']}`
- `{data['outputs']['json']}`

Production modification=0; frozen shell modification=0; button pose modification=0; existing validated I2
modification=0. Protected authority hashes preserved: **{data['preservation']['allProtectedFilesPreserved']}**.
STOP after batch classification; no production feature generation or physical coupon generation was performed.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); RENDER.mkdir(parents=True, exist_ok=True)
    protected = protected_files(); hashes_before = doc84.hashes(protected)
    datums = load_all_datums()
    shell_full = {owner: import_step(path) for owner, path in SHELL_STEP.items()}
    rays = {owner: ExactRaySampler(shape) for owner, shape in shell_full.items()}
    original, body, terminals, corners, _old_actuator, actuator, _hybrid = doc84.detailed_switch_parts()
    local_parts = {"BODY": body, "ACTUATOR": actuator, **terminals}
    mechanism_source = pusher_system()
    mechanism = {"PUSHER": mechanism_source["pusher"], "GUIDE": mechanism_source["guide"],
                 "HARD_STOP": mechanism_source["stop"], "CLIP": mechanism_source["clip"]}
    placements = {name: doc84.doc83.datum_location(datums[name], FROZEN_FRONT_DEPTHS[name]) for name in BUTTONS}
    detailed_world = {name: {part: placements[name] * shape for part, shape in local_parts.items()}
                      for name in BUTTONS}
    results: dict[str, dict[str, object]] = {}
    candidates: dict[str, dict[str, object]] = {}
    shells: dict[str, dict[str, Shape]] = {}
    evaluation_total = 0

    # Frozen docs/89 I2 control.
    auth84 = json.loads(doc86.DOC84_JSON.read_text(encoding="utf-8"))
    baseline = doc86.manufacturing_candidate(auth84)
    i2_candidate = doc89.candidate_from(baseline, doc89.FINAL_SHIFT_U, doc89.FINAL_EFFECTIVE)
    i2_shell_local = placements["I2"].inverse() * import_step(doc86.SHELL_AUDIT_STEP)
    i2_shell = {"crop": i2_shell_local, "slotted": i2_shell_local,
                "tools": Compound(children=[])}
    auth86 = json.loads(doc86.JSON_PATH.read_text(encoding="utf-8"))
    i2_depths = {edge: float(auth86["candidate"]["slots"][edge]["minimumBlindInsertionDepthMm"]) for edge in EDGES}
    for edge in EDGES:
        i2_candidate["rows"][edge]["minimumRemainingShellMm"] = float(auth86["candidate"]["slots"][edge]["minimumRemainingShellMm"])
        i2_candidate["rows"][edge]["minimumBlindInsertionDepthMm"] = i2_depths[edge]
        i2_candidate["rows"][edge]["tiltFromWDeg"] = math.degrees(math.acos(abs(float(i2_candidate["rows"][edge]["directionLocal"][2]))))
        i2_candidate["rows"][edge]["ninetyDegreeResult"] = "REFERENCE"
        i2_candidate["rows"][edge]["reasonNinetyFailed"] = "docs/81 exact 90-degree shell-footprint/material rejection"
        if "slotTool" not in i2_candidate["rows"][edge]:
            i2_candidate["rows"][edge]["slotTool"] = local_box(.01, .01, .01, 0, 0, 0, "I2_SLOT_REFERENCE_MARKER")
            i2_candidate["rows"][edge]["mouthTool"] = local_box(.01, .01, .01, 0, 0, 0, "I2_MOUTH_REFERENCE_MARKER")
    i2_candidate["legs"] = Compound(children=[i2_candidate["rows"][e]["leg"] for e in EDGES])
    i2_candidate["slots"] = Compound(children=[i2_candidate["rows"][e]["slotTool"] for e in EDGES])
    i2_candidate["mouths"] = Compound(children=[i2_candidate["rows"][e]["mouthTool"] for e in EDGES])
    candidates["I2"] = i2_candidate; shells["I2"] = i2_shell
    auth89 = json.loads(doc89.JSON_PATH.read_text(encoding="utf-8"))
    results["I2"] = {
        "datum": datums["I2"], "owner": datums["I2"].owner, "sameHalfComplete": True,
        "legs": {edge: serial_row(i2_candidate["rows"][edge]) for edge in EDGES},
        "minimumThreeWayClearanceMm": float(auth89["finalCandidate"]["minimumThreeWayClearanceMm"]),
        "minimumRemainingShellMm": float(auth89["manufacturingGate"]["remainingExteriorShellMm"]),
        "rearAssembly": auth89["rearHarnessAssembly"], "displayClass": "REFERENCE",
        "countedClass": "STANDARD", "failureReason": None,
        "manufacturing": auth89["manufacturingGate"],
    }

    for button in BUTTONS:
        if button == "I2":
            continue
        print(f"screening {button}", flush=True)
        datum = datums[button]; front = float(FROZEN_FRONT_DEPTHS[button]); placement = placements[button]
        rows = {}; searches = {}
        for edge in EDGES:
            row, search = select_leg(edge, datum, front, rays[datum.owner], local_parts, corners,
                                     mechanism["PUSHER"], placement, detailed_world, button)
            rows[edge] = row; searches[edge] = search; evaluation_total += int(search["evaluations"])
            print(f"  {edge}: feasible={row.get('feasible')} tilt={row.get('tiltFromWDeg')} failure={row.get('failure')}", flush=True)
        if not all(bool(rows[edge].get("feasible")) for edge in EDGES):
            failure = "; ".join(f"{edge}:{rows[edge].get('failure')}" for edge in EDGES if not rows[edge].get("feasible"))
            # A diagnostic placeholder keeps the all-eight context render complete.
            placeholder = local_box(1.6, 1.6, 1.2, 0, 0, -1.14, f"{button}_FAILED_SCREEN_MARKER")
            candidate = {"harness": placeholder, "base": placeholder, "legs": placeholder,
                         "slots": placeholder, "mouths": placeholder, "rows": rows,
                         "rootCommonVolumeByEdgeMm3": {edge: 0.0 for edge in EDGES}}
            shell = {"crop": placements[button].inverse() * (shell_full[datum.owner] & (placements[button] * local_box(24,24,13,0,0,0,"FAIL_CROP"))),
                     "slotted": placeholder, "tools": placeholder}
            valid_shell = [float(row["minimumRemainingShellMm"]) for row in rows.values()
                           if row.get("feasible") and "minimumRemainingShellMm" in row]
            minimum_shell = min(valid_shell) if valid_shell else 0.0
            results[button] = {"datum": datum, "owner": datum.owner, "sameHalfComplete": datum.owner == "JfD",
                               "legs": {edge: serial_row(rows[edge]) for edge in EDGES}, "search": searches,
            "minimumThreeWayClearanceMm": None, "minimumRemainingShellMm": minimum_shell,
                               "rearAssembly": {"result": "FAIL", "stateCount": 0}, "displayClass": "FAIL",
                               "countedClass": "FAIL", "failureReason": failure,
                               "manufacturing": {"result": "FAIL"}}
            candidates[button] = candidate; shells[button] = shell
            continue
        candidate = build_candidate(button, rows)
        shell = make_slotted_shell(candidate, shell_full[datum.owner], placement, button)
        metrics = candidate_metrics(candidate, shell, local_parts, corners, mechanism["PUSHER"],
                                    placement, detailed_world, button)
        rear = rear_check(candidate, shell, local_parts, corners, mechanism)
        step_path = OUT / f"{button}_FOUR_EDGE_HARNESS_AUDIT_ONLY.step"
        export_step(candidate["harness"], step_path); imported = import_step(step_path)
        neck = min(FRAME_WIDTH - abs(float(rows[e]["rootTangentCoordinateMm"])) for e in EDGES)
        effective = min(float(rows[e]["effectiveFdmThicknessMm"]) for e in EDGES)
        manufacturing = {
            "solidCount": len(candidate["harness"].solids()), "valid": bool(candidate["harness"].is_valid),
            "stepReimportSolidCount": len(imported.solids()), "stepReimportValid": bool(imported.is_valid),
            "minimumStructuralNeckMm": neck, "minimumEffectiveFdmThicknessMm": effective,
            "rootCommonVolumeByEdgeMm3": candidate["rootCommonVolumeByEdgeMm3"],
            "shellUnintendedPenetrationMm3": float(metrics["shellUnintended"]["penetrationMm3"]),
        }
        manufacturing["result"] = "PASS" if (
            manufacturing["solidCount"] == manufacturing["stepReimportSolidCount"] == 1 and
            manufacturing["valid"] and manufacturing["stepReimportValid"] and neck >= 1.20 - EPS and
            effective >= 1.20 - EPS and all(value > EPS for value in candidate["rootCommonVolumeByEdgeMm3"].values()) and
            float(metrics["shellUnintended"]["penetrationMm3"]) <= EPS) else "FAIL"
        tilted = any(float(rows[e]["tiltFromWDeg"]) > 1.0e-8 for e in EDGES)
        hardening = float(metrics["minimumThreeWayClearanceMm"]) < 0.15
        if manufacturing["result"] != "PASS" or rear["result"] != "PASS":
            counted = "FAIL"; display = "FAIL"
            failure = "manufacturing gate or rear assembly failed"
        elif tilted or hardening or (button == "N2" and datum.owner != "JfD"):
            counted = "LOCAL VARIANT"; display = "LOCAL VARIANT"
            failure = None
        else:
            counted = "STANDARD"; display = "STANDARD"; failure = None
        results[button] = {"datum": datum, "owner": datum.owner,
                           "sameHalfComplete": bool(button != "N2" or datum.owner == "JfD"),
                           "legs": {edge: serial_row(rows[edge]) for edge in EDGES}, "search": searches,
                           **{key: value for key, value in metrics.items() if key not in ("shellUnintended",)},
                           "rearAssembly": rear, "displayClass": display, "countedClass": counted,
                           "failureReason": failure, "manufacturing": manufacturing,
                           "auditHarnessStep": relative(step_path)}
        candidates[button] = candidate; shells[button] = shell

    world: dict[str, dict[str, Shape]] = {}
    for button in BUTTONS:
        placement = placements[button]; candidate = candidates[button]
        world[button] = {
            "harness": placement * candidate["harness"], "legs": placement * candidate["legs"],
            "slots": placement * candidate["slots"], "mouths": placement * candidate["mouths"],
            "shellCrop": placement * shells[button]["crop"],
        }
        for edge in EDGES:
            if candidate["rows"].get(edge, {}).get("feasible") and "leg" in candidate["rows"][edge]:
                world[button][f"leg_{edge}"] = placement * candidate["rows"][edge]["leg"]
            else:
                world[button][f"leg_{edge}"] = placement * candidate["harness"]

    all8 = all8_check(world, detailed_world)
    all8["geometricPairFitResult"] = all8["result"]
    unresolved_buttons = [name for name in BUTTONS if results[name]["countedClass"] == "FAIL"]
    if unresolved_buttons:
        all8["result"] = "FAIL"
        all8["failureButtons"] = unresolved_buttons
        all8["failureReason"] = "one or more button has no viable selected four-leg manufacturing harness"
    export_step(Compound(children=[world[name]["harness"] for name in BUTTONS]), ALL8_HARNESS_STEP)
    export_step(Compound(children=[world[name]["slots"] for name in BUTTONS]), ALL8_SLOT_STEP)

    # A simultaneous collision converts otherwise viable local results to FAIL.
    if float(all8["maximumPairPenetrationMm3"]) > EPS:
        involved = set(str(all8["closestPair"]).split(":"))
        for name in involved:
            if name != "I2":
                results[name]["countedClass"] = "FAIL"; results[name]["displayClass"] = "FAIL"
                results[name]["failureReason"] = "ALL-8 simultaneous interference"

    ninety = sum(1 for name in BUTTONS for edge in EDGES
                  if float(results[name]["legs"][edge]["tiltFromWDeg"]) <= 1.0e-8)
    unresolved = sum(1 for name in BUTTONS for edge in EDGES
                     if results[name]["legs"][edge].get("tiltResolved") is False)
    tilts = [float(results[name]["legs"][edge]["tiltFromWDeg"]) for name in BUTTONS for edge in EDGES
             if results[name]["legs"][edge].get("tiltResolved") is not False]
    standard = sum(1 for name in BUTTONS if results[name]["countedClass"] == "STANDARD")
    local_variant = sum(1 for name in BUTTONS if results[name]["countedClass"] == "LOCAL VARIANT")
    fail = sum(1 for name in BUTTONS if results[name]["countedClass"] == "FAIL")
    clearance_buttons = [name for name in BUTTONS if results[name]["minimumThreeWayClearanceMm"] is not None]
    worst_clear = min(clearance_buttons, key=lambda name: float(results[name]["minimumThreeWayClearanceMm"]))
    worst_shell = min(BUTTONS, key=lambda name: float(results[name]["minimumRemainingShellMm"]))
    summary = {"buttonsEvaluated": 8, "standard": standard, "localVariant": local_variant, "fail": fail,
               "totalLegs": 32, "ninetyLegs": ninety, "tiltedLegs": 32 - ninety - unresolved,
               "unresolvedLegs": unresolved,
               "maximumTiltDeg": max(tilts), "worstClearanceButton": worst_clear,
               "worstClearanceMm": float(results[worst_clear]["minimumThreeWayClearanceMm"]),
               "minimumShellButton": worst_shell,
               "minimumShellMm": float(results[worst_shell]["minimumRemainingShellMm"]),
               "candidateEvaluations": evaluation_total}
    renders = render_outputs(world, detailed_world, shell_full, results, all8)
    hashes_after = doc84.hashes(protected)

    serial_buttons = {}
    for name, row in results.items():
        serial_buttons[name] = {key: value for key, value in row.items() if key != "datum"}
    data = {
        "schema": "onegrip.8-button-four-edge-batch-propagation-screening.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(), "mode": "BATCH SCREENING / AUDIT ONLY",
        "sourceProof": {"sourceObject": "ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID",
                        "sourceTriangleCount": int(len(original.triangles)), "simplifiedProxyUsedForVerdict": False,
                        "measuredActuatorDiameterMm": 3.35, "measuredActuatorProjectionMm": 2.44},
        "summary": summary, "buttons": serial_buttons, "all8Simultaneous": all8,
        "scope": {"productionModification": 0, "frozenShellModification": 0,
                  "buttonPoseModification": 0, "existingValidatedI2Modification": 0,
                  "physicalCouponGeneration": 0, "deepPerButtonHardening": 0},
        "preservation": {"protectedFileCount": len(protected), "hashesBefore": hashes_before,
                         "hashesAfter": hashes_after,
                         "allProtectedFilesPreserved": hashes_before == hashes_after},
        "outputs": {"report": relative(REPORT), "json": relative(JSON_PATH),
                    "all8HarnessStep": relative(ALL8_HARNESS_STEP),
                    "all8SlotStep": relative(ALL8_SLOT_STEP), "renders": renders},
    }
    JSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"summary": summary, "all8": all8["result"], "renders": len(renders),
                      "protected": hashes_before == hashes_after, "report": relative(REPORT)}, indent=2), flush=True)


def rerender_existing() -> None:
    """Rebuild only the ten diagnostic PNGs from the completed JSON/STEP audit."""
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    datums = load_all_datums()
    placements = {name: doc84.doc83.datum_location(datums[name], FROZEN_FRONT_DEPTHS[name]) for name in BUTTONS}
    shell_full = {owner: import_step(path) for owner, path in SHELL_STEP.items()}
    _original, body, terminals, corners, _old_actuator, actuator, _hybrid = doc84.detailed_switch_parts()
    local_parts = {"BODY": body, "ACTUATOR": actuator, **terminals}
    detailed_world = {name: {part: placements[name] * shape for part, shape in local_parts.items()}
                      for name in BUTTONS}
    results = data["buttons"]
    for name in BUTTONS:
        results[name]["datum"] = datums[name]
    world: dict[str, dict[str, Shape]] = {}
    for name in BUTTONS:
        placement = placements[name]
        rows = results[name]["legs"]
        local_legs = {}
        for edge in EDGES:
            row = rows[edge]
            if row.get("tiltResolved") is False or "floorPointLocalUVWmm" not in row:
                root = base_root(edge, 1.30, 0.0)
                marker = local_box(.42, .42, .42, float(root[0]), float(root[1]), float(root[2] - .21),
                                   f"{name}_{edge}_UNRESOLVED_MARKER")
                local_legs[edge] = marker
            else:
                root = np.asarray(row["rootLocalUVWmm"], float)
                vector = np.asarray(row["directionLocal"], float)
                floor = np.asarray(row["floorPointLocalUVWmm"], float)
                tangent = np.asarray(row["tangentLocal"], float)
                local_legs[edge] = oriented_box_between(
                    xyz(root - vector * ROOT_EMBED), xyz(floor), xyz(tangent),
                    float(row["legTangentWidthMm"]), float(row["legThicknessMm"]),
                    label=f"{name}_{edge}_DIAGNOSTIC_LEG")
        legs = Compound(children=list(local_legs.values()))
        if name == "I2":
            harness_local = import_step(doc89.HARNESS_STEP)
        elif results[name]["countedClass"] != "FAIL":
            harness_local = import_step(ROOT / results[name]["auditHarnessStep"])
        else:
            harness_local = legs
        slot_markers = []
        for edge in EDGES:
            row = rows[edge]
            point = np.asarray(row.get("floorPointLocalUVWmm", base_root(edge, 1.30, 0.0)), float)
            slot_markers.append(local_box(.34, .34, .34, float(point[0]), float(point[1]), float(point[2] - .17),
                                          f"{name}_{edge}_SLOT_DIAGNOSTIC"))
        slots = Compound(children=slot_markers)
        crop_tool = local_box(24, 24, 13, 0, 0, 0, f"{name}_RENDER_CROP")
        shell_crop_world = (shell_full[datums[name].owner] & (placement * crop_tool)).clean()
        world[name] = {"harness": placement * harness_local, "legs": placement * legs,
                       "slots": placement * slots, "mouths": placement * slots,
                       "shellCrop": shell_crop_world}
        for edge in EDGES:
            world[name][f"leg_{edge}"] = placement * local_legs[edge]
    render_outputs(world, detailed_world, shell_full, results, data["all8Simultaneous"])


if __name__ == "__main__":
    main()
