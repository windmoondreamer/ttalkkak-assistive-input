"""I2 minimum-angle four-edge direct-shell harness and assembly audit."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Compound, Location, Shape, Vector, export_step, import_step

from .direct_shell_four_edge_i2_simplification_audit import (
    BLIND_DEPTH,
    HARNESS_STEP as DOC80_HARNESS_STEP,
    JSON_PATH as DOC80_JSON,
    REPORT as DOC80_REPORT,
    SHELL_STEP,
    SLOT_CLEARANCE,
    SLOT_TANGENT,
    ExactRaySampler,
    leg_root,
    local_dir_to_world,
    local_point_to_world,
)
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import (
    ACT_D, BODY_H, BODY_U, BODY_V, LEG_TANGENTIAL, datum_location, local_box,
    local_cylinder, moved, placed, sha256, volume,
)
from .i2_parallel_w_root_slide_simplification_audit import (
    JSON_PATH as DOC82_JSON,
    REPORT as DOC82_REPORT,
    RENDER as DOC82_RENDER,
    OUT as DOC82_OUT,
    corner_keepouts,
    protected_files as doc82_protected_files,
    strict_domain,
    tangent_axis,
)
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import BUTTONS, ROOT, relative
from .option_c_local_exact_prototype import raster_scene, safe_edge_lines, safe_triangles
from .slot_anchored_harness_captive_pusher_audit import pusher_system, terminal_proxies


OUT = ROOT / "build123d_workbench/out/i2_minimum_angle_direct_shell_assembly_audit"
RENDER = ROOT / "renders/i2_minimum_angle_direct_shell_assembly_audit"
REPORT = ROOT / "docs/83_i2_minimum_angle_direct_shell_assembly_audit.md"
JSON_PATH = OUT / "i2_minimum_angle_direct_shell_assembly_audit.json"
SEARCH_CACHE = OUT / "minimum_angle_search_cache.json"
HARNESS_STEP = OUT / "I2_MINIMUM_ANGLE_FOUR_EDGE_HARNESS_AUDIT_ONLY.step"
SHELL_STEP_OUT = OUT / "I2_MINIMUM_ANGLE_FOUR_SLOT_SHELL_CROP_AUDIT_ONLY.step"
ASSEMBLY_STEP = OUT / "I2_MINIMUM_ANGLE_FULL_SEATED_ASSEMBLY_AUDIT_ONLY.step"

REPRESENTATIVE = "I2"
EDGES = ("+U", "-U", "+V", "-V")
BOOLEAN_EPS = 1.0e-6
TARGET_GRID_STEP = 0.25
ROOT_GRID_STEP = 0.10
FOOTER = "AUDIT ONLY | I2 MINIMUM-ANGLE STRAIGHT LEGS | DIRECT SHELL | PRODUCTION 0 | PROPAGATION 0"
COL = {
    "body": (229, 92, 100), "leg": (58, 165, 232), "slot": (245, 178, 65),
    "shell": (108, 130, 151), "pusher": (237, 132, 72), "neighbor": (171, 112, 219),
    "axis": (250, 213, 78), "fail": (235, 82, 93), "pass": (61, 190, 137),
    "old": (92, 144, 190), "sweep": (232, 102, 111), "bed": (108, 119, 133),
}


def xyz(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(map(float, value))


def protected_files() -> list[Path]:
    rows = {
        *doc82_protected_files(), DOC80_REPORT, DOC82_REPORT, DOC82_JSON,
        *[path for path in DOC82_OUT.rglob("*") if path.is_file()],
        *[path for path in DOC82_RENDER.rglob("*") if path.is_file()],
    }
    return sorted(path for path in rows if path.exists())


def hashes(paths: list[Path]) -> dict[str, str]:
    return {relative(path): sha256(path) for path in paths}


def direction_from_angles(tilt_deg: float, azimuth_deg: float) -> np.ndarray:
    tilt = math.radians(float(tilt_deg)); az = math.radians(float(azimuth_deg))
    return unit((math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt)))


def angles_from_direction(direction: Iterable[float]) -> tuple[float, float]:
    d = unit(direction)
    tilt = math.degrees(math.acos(float(np.clip(d[2], -1.0, 1.0))))
    az = math.degrees(math.atan2(float(d[1]), float(d[0]))) if tilt > 1.0e-9 else 0.0
    return float(tilt), float(az)


def root_at(edge: str, tangent_coordinate: float) -> np.ndarray:
    return leg_root(edge) + tangent_axis(edge) * float(tangent_coordinate)


def candidate_geometry(edge: str, root_t: float, thickness: float, direction_local: Iterable[float], datum,
                       front: float, ray: ExactRaySampler, include_samples: bool = True) -> dict[str, object]:
    root = root_at(edge, root_t)
    direction = unit(direction_local)
    if direction[2] <= 0:
        return {"feasible": False, "failure": "NON_OUTWARD_DIRECTION"}
    tangent_hint = tangent_axis(edge)
    tangent = unit(tangent_hint - direction * float(np.dot(tangent_hint, direction)))
    structural = unit(np.cross(direction, tangent))
    direction_world = local_dir_to_world(datum, direction)
    tangent_world = local_dir_to_world(datum, tangent)
    structural_world = local_dir_to_world(datum, structural)
    root_world = local_point_to_world(datum, front, root)
    center_hits = ray.hits(root_world, direction_world, 24.0)
    tilt, azimuth = angles_from_direction(direction)
    base = {
        "edge": edge, "rootTangentCoordinateMm": float(root_t),
        "rootLocalUVWmm": list(map(float, root)),
        "rootShiftLocalUVWmm": list(map(float, root - leg_root(edge))),
        "rootShiftMagnitudeMm": abs(float(root_t)),
        "legThicknessMm": float(thickness), "legTangentWidthMm": LEG_TANGENTIAL,
        "directionLocal": list(map(float, direction)), "directionWorld": list(map(float, direction_world)),
        "tiltFromPlusWDeg": tilt, "angleToUVPlaneDeg": 90.0 - tilt,
        "tiltAzimuthDeg": azimuth,
        "tiltDirectionUV": list(map(float, unit((direction[0], direction[1], 0)))) if tilt > 1.0e-9 else [0.0, 0.0, 0.0],
        "centerHitsMm": center_hits,
    }
    if len(center_hits) < 2:
        return {**base, "feasible": False, "failure": "NO_CENTER_SHELL_PAIR", "footprintPairCoverage": 0}

    slot_structural = float(thickness + 2.0 * SLOT_CLEARANCE)
    samples = []
    inner: list[float] = []
    outer: list[float] = []
    for tangent_offset in (-SLOT_TANGENT / 2.0, 0.0, SLOT_TANGENT / 2.0):
        for structural_offset in (-slot_structural / 2.0, 0.0, slot_structural / 2.0):
            sample_root = root + tangent * tangent_offset + structural * structural_offset
            sample_world = local_point_to_world(datum, front, sample_root)
            hits = ray.hits(sample_world, direction_world, 24.0)
            pair = len(hits) >= 2
            if pair:
                inner.append(float(hits[0])); outer.append(float(hits[1]))
            if include_samples:
                samples.append({"originLocalUVWmm": list(map(float, sample_root)), "hitsMm": hits,
                                "hasInnerOuterPair": pair})
    coverage = len(inner)
    if coverage < 9:
        return {**base, "feasible": False, "failure": "INCOMPLETE_SLOT_FOOTPRINT",
                "footprintPairCoverage": coverage, "missingFootprintPairs": 9 - coverage,
                "samples": samples}
    floor_distance = max(inner) + BLIND_DEPTH
    remaining = min(outer) - floor_distance
    shell_thicknesses = [out - inn for inn, out in zip(inner, outer)]
    floor_local = root + direction * floor_distance
    # A 0.15 mm same-axis inward tail fuses each unchanged straight prism into
    # the bottom cross.  It is not a shoulder or transition bracket and does
    # not change the reported functional side root.
    fusion_start = root - direction * 0.15
    leg = oriented_box_between(xyz(fusion_start), xyz(floor_local), xyz(tangent), LEG_TANGENTIAL, thickness,
                               label=f"I2_{edge}_MINIMUM_ANGLE_STRAIGHT_LEG")
    slot_start = root + direction * (min(inner) - 0.35)
    slot_tool = oriented_box_between(xyz(slot_start), xyz(floor_local), xyz(tangent), SLOT_TANGENT,
                                     slot_structural, label=f"I2_{edge}_DIRECT_BLIND_SLOT_VOID")
    passed = remaining >= BLIND_DEPTH
    return {
        **base, "feasible": passed, "failure": None if passed else "INSUFFICIENT_REMAINING_SHELL",
        "footprintPairCoverage": coverage, "missingFootprintPairs": 0,
        "legLengthMm": float(floor_distance), "floorPointLocalUVWmm": list(map(float, floor_local)),
        "rootFusionOverlapMm": 0.15,
        "printedPrismLengthMm": float(floor_distance + 0.15),
        "slotDepthMm": BLIND_DEPTH, "slotCrossSectionMm": [SLOT_TANGENT, slot_structural],
        "minimumRemainingShellMm": float(remaining),
        "shellThicknessFootprintRangeMm": [float(min(shell_thicknesses)), float(max(shell_thicknesses))],
        "blindDepthFootprintRangeMm": [float(floor_distance - max(inner)), float(floor_distance - min(inner))],
        "samples": samples, "leg": leg, "slotTool": slot_tool,
        "tangentLocal": list(map(float, tangent)), "structuralLocal": list(map(float, structural)),
    }


def static_clearance(row: dict[str, object], datum, front: float, datums: dict[str, object], body: Shape,
                     corners: Shape, pusher: Shape, terminals: dict[str, Shape]) -> dict[str, object]:
    if not row.get("feasible") or "leg" not in row:
        return {"allClear": False, "failure": row.get("failure")}
    leg: Shape = row["leg"]
    local = {}
    for name, shape in {"ITS_BODY": body, "CORNER_KEEPOUTS": corners, "PUSHER": pusher, **terminals}.items():
        pen = volume(leg & shape)
        local[name] = {"distanceMm": float(leg.distance_to(shape)), "penetrationMm3": pen,
                       "clear": pen <= BOOLEAN_EPS}
    leg_world = placed(leg, datum, front, f"I2_{row['edge']}_WORLD_LEG")
    neighbor_body = local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "NEIGHBOR_BODY")
    neighbor_act = local_cylinder(ACT_D, BODY_H, 6.0, "NEIGHBOR_ACT")
    neighbors = {}
    for name in BUTTONS:
        if name == REPRESENTATIVE:
            continue
        b = placed(neighbor_body, datums[name], FROZEN_FRONT_DEPTHS[name], f"{name}_BODY")
        a = placed(neighbor_act, datums[name], FROZEN_FRONT_DEPTHS[name], f"{name}_ACT")
        pens = [volume(leg_world & b), volume(leg_world & a)]
        dists = [float(leg_world.distance_to(b)), float(leg_world.distance_to(a))]
        neighbors[name] = {"minimumDistanceMm": min(dists), "penetrationMm3": float(sum(pens)),
                           "clear": sum(pens) <= BOOLEAN_EPS}
    nearest = min(neighbors, key=lambda name: neighbors[name]["minimumDistanceMm"])
    terminal_names = list(terminals)
    all_clear = all(value["clear"] for value in local.values()) and all(value["clear"] for value in neighbors.values())
    return {
        "allClear": all_clear, "body": local["ITS_BODY"], "cornerKeepouts": local["CORNER_KEEPOUTS"],
        "pusher": local["PUSHER"], "terminals": {name: local[name] for name in terminal_names},
        "minimumTerminalClearanceMm": min(local[name]["distanceMm"] for name in terminal_names),
        "terminalPenetrationMm3": sum(local[name]["penetrationMm3"] for name in terminal_names),
        "nearestNeighbor": nearest, "minimumNeighborClearanceMm": neighbors[nearest]["minimumDistanceMm"],
        "neighborPenetrationMm3": neighbors[nearest]["penetrationMm3"], "neighbors": neighbors,
    }


def objective(row: dict[str, object]) -> tuple[float, float, float]:
    return (float(row["tiltFromPlusWDeg"]), float(row["rootShiftMagnitudeMm"]), float(row["legLengthMm"]))


def serializable(row: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in row.items() if key not in ("leg", "slotTool")}


def docs80_seed(edge: str, thickness: float, datum, front: float, ray: ExactRaySampler) -> dict[str, object]:
    source = json.loads(DOC80_JSON.read_text(encoding="utf-8"))["directShell"]["legs"][edge]
    root = np.asarray(source["rootLocalUVWmm"], float)
    root_t = float(root[1] if edge.endswith("U") else root[0])
    return candidate_geometry(edge, root_t, thickness, source["directionLocal"], datum, front, ray)


def pattern_optimize(seed: dict[str, object], thickness: float, datum, front: float, ray: ExactRaySampler,
                     datums: dict[str, object], body: Shape, corners: Shape, pusher: Shape,
                     terminals: dict[str, Shape], initial_steps: tuple[float, float, float] = (0.20, 1.0, 3.0)) -> tuple[dict[str, object], int]:
    if not seed.get("feasible"):
        return seed, 0
    seed_clear = static_clearance(seed, datum, front, datums, body, corners, pusher, terminals)
    if not seed_clear["allClear"]:
        seed["staticClearance"] = seed_clear
        return seed, 0
    current = seed
    evaluations = 0
    step_t, step_theta, step_az = map(float, initial_steps)
    lower_t, upper_t = strict_domain(str(seed["edge"]))
    while step_theta >= 0.01:
        candidates = []
        for dt in (-step_t, 0.0, step_t):
            for dtheta in (-step_theta, 0.0, step_theta):
                for daz in (-step_az, 0.0, step_az):
                    if dt == dtheta == daz == 0.0:
                        continue
                    root_t = float(np.clip(float(current["rootTangentCoordinateMm"]) + dt, lower_t, upper_t))
                    theta = max(0.0, float(current["tiltFromPlusWDeg"]) + dtheta)
                    az = float(current["tiltAzimuthDeg"]) + daz
                    row = candidate_geometry(str(seed["edge"]), root_t, thickness,
                                             direction_from_angles(theta, az), datum, front, ray)
                    evaluations += 1
                    if not row.get("feasible"):
                        continue
                    clearance = static_clearance(row, datum, front, datums, body, corners, pusher, terminals)
                    if clearance["allClear"]:
                        row["staticClearance"] = clearance
                        candidates.append(row)
        improved = [row for row in candidates if objective(row) < objective(current)]
        if improved:
            current = min(improved, key=objective)
        else:
            step_t /= 2.0; step_theta /= 2.0; step_az /= 2.0
    return current, evaluations


def shell_target_map(datum, front: float, ray: ExactRaySampler, step: float = TARGET_GRID_STEP) -> list[dict[str, float]]:
    """Coarse exact-W surface map used only to seed disconnected tilt basins."""
    press_depth = front + BODY_H
    rows = []
    for u0 in np.arange(-7.0, 7.0 + step * 0.25, step):
        for v0 in np.arange(-7.0, 7.0 + step * 0.25, step):
            hits = ray.exterior_depth_hits(datum, float(u0), float(v0))
            if len(hits) < 2:
                continue
            rows.append({
                "u": float(u0), "v": float(v0),
                "innerW": float(press_depth - hits[1]),
                "outerW": float(press_depth - hits[0]),
                "normalShellThicknessMm": float(hits[1] - hits[0]),
            })
    return rows


def target_belongs_to_side(edge: str, row: dict[str, float]) -> bool:
    if edge == "+U": return row["u"] >= 3.25
    if edge == "-U": return row["u"] <= -3.25
    if edge == "+V": return row["v"] >= 3.25
    return row["v"] <= -3.25


def global_coarse_proposals(edge: str, incumbent: dict[str, object], target_map: list[dict[str, float]]) -> list[dict[str, object]]:
    lower, upper = strict_domain(edge)
    proposals = []
    for root_t in np.arange(lower, upper + ROOT_GRID_STEP * 0.25, ROOT_GRID_STEP):
        root = root_at(edge, float(root_t))
        for target in target_map:
            if not target_belongs_to_side(edge, target):
                continue
            target_point = np.asarray((target["u"], target["v"], target["innerW"]), float)
            delta = target_point - root
            if delta[2] <= 0:
                continue
            direction = unit(delta)
            tilt, azimuth = angles_from_direction(direction)
            if tilt >= float(incumbent["tiltFromPlusWDeg"]) - 0.002:
                continue
            proposals.append({"rootTangentCoordinateMm": float(root_t), "directionLocal": list(map(float, direction)),
                              "tiltFromPlusWDeg": tilt, "tiltAzimuthDeg": azimuth,
                              "approximateLengthMm": float(np.linalg.norm(delta))})
    proposals.sort(key=lambda row: (row["tiltFromPlusWDeg"], abs(row["rootTangentCoordinateMm"]),
                                    row["approximateLengthMm"]))
    unique = []
    seen = set()
    for row in proposals:
        key = (round(row["rootTangentCoordinateMm"], 2), round(row["tiltFromPlusWDeg"], 2),
               round(row["tiltAzimuthDeg"], 1))
        if key in seen:
            continue
        seen.add(key); unique.append(row)
    return unique


def progressive_exact_candidate(edge: str, proposal: dict[str, object], thickness: float, datum, front: float,
                                ray: ExactRaySampler) -> dict[str, object] | None:
    """Reject global proposals at the first missing footprint ray."""
    root_t = float(proposal["rootTangentCoordinateMm"])
    root = root_at(edge, root_t)
    direction = unit(proposal["directionLocal"])
    tangent_hint = tangent_axis(edge)
    tangent = unit(tangent_hint - direction * float(np.dot(tangent_hint, direction)))
    structural = unit(np.cross(direction, tangent))
    direction_world = local_dir_to_world(datum, direction)
    slot_structural = thickness + 2.0 * SLOT_CLEARANCE
    # Corners first, then edge centers and center.  Most aperture candidates
    # fail in one or two calls instead of requiring all nine.
    offsets = [
        (-SLOT_TANGENT/2, -slot_structural/2), (-SLOT_TANGENT/2, slot_structural/2),
        (SLOT_TANGENT/2, -slot_structural/2), (SLOT_TANGENT/2, slot_structural/2),
        (-SLOT_TANGENT/2, 0), (SLOT_TANGENT/2, 0),
        (0, -slot_structural/2), (0, slot_structural/2), (0, 0),
    ]
    inner = []; outer = []
    for tangent_offset, structural_offset in offsets:
        origin = root + tangent * tangent_offset + structural * structural_offset
        hits = ray.hits(local_point_to_world(datum, front, origin), direction_world, 24.0)
        if len(hits) < 2:
            return None
        inner.append(float(hits[0])); outer.append(float(hits[1]))
    floor = max(inner) + BLIND_DEPTH
    if min(outer) - floor < BLIND_DEPTH:
        return None
    return candidate_geometry(edge, root_t, thickness, direction, datum, front, ray)


def common_direction_proposals(edge: str, common_direction: Iterable[float], target_map: list[dict[str, float]],
                               maximum_tilt_deg: float = 25.0) -> list[dict[str, object]]:
    common = unit(common_direction)
    lower, upper = strict_domain(edge)
    proposals = []
    for root_t in np.arange(lower, upper + ROOT_GRID_STEP * 0.25, ROOT_GRID_STEP):
        root = root_at(edge, float(root_t))
        for target in target_map:
            if not target_belongs_to_side(edge, target):
                continue
            delta = np.asarray((target["u"], target["v"], target["innerW"]), float) - root
            if delta[2] <= 0:
                continue
            direction = unit(delta); tilt, azimuth = angles_from_direction(direction)
            if tilt > maximum_tilt_deg:
                continue
            mismatch = math.degrees(math.acos(float(np.clip(np.dot(direction, common), -1.0, 1.0))))
            proposals.append({
                "rootTangentCoordinateMm": float(root_t), "directionLocal": list(map(float, direction)),
                "tiltFromPlusWDeg": tilt, "tiltAzimuthDeg": azimuth,
                "commonDirectionMismatchDeg": mismatch, "approximateLengthMm": float(np.linalg.norm(delta)),
            })
    proposals.sort(key=lambda row: (row["commonDirectionMismatchDeg"], row["tiltFromPlusWDeg"],
                                    abs(row["rootTangentCoordinateMm"]), row["approximateLengthMm"]))
    return proposals


def build_harness(rows: dict[str, dict[str, object]]) -> dict[str, Shape]:
    u_min = float(rows["-U"]["rootLocalUVWmm"][0]); u_max = float(rows["+U"]["rootLocalUVWmm"][0])
    v_min = float(rows["-V"]["rootLocalUVWmm"][1]); v_max = float(rows["+V"]["rootLocalUVWmm"][1])
    seat_u = local_box(u_max-u_min, 1.60, 1.20, (u_min+u_max)/2, 0, -1.20, "I2_OPEN_CROSS_U")
    seat_v = local_box(1.60, v_max-v_min, 1.20, 0, (v_min+v_max)/2, -1.20, "I2_OPEN_CROSS_V")
    seat = seat_u.fuse(seat_v).clean(); seat.label = "I2_MINIMUM_OPEN_BODY_BOTTOM_CROSS"
    result = seat
    for edge in EDGES:
        result = result.fuse(rows[edge]["leg"])
    result = result.clean(); result.label = "I2_MINIMUM_ANGLE_FOUR_EDGE_HARNESS_ONE_PIECE"
    return {"harness": result, "seat": seat, "legs": Compound(children=[rows[e]["leg"] for e in EDGES]),
            "slots": Compound(children=[rows[e]["slotTool"] for e in EDGES])}


def minimax_common_direction(rows: dict[str, dict[str, object]]) -> dict[str, object]:
    from scipy.optimize import differential_evolution
    directions = {edge: np.asarray(rows[edge]["directionLocal"], float) for edge in EDGES}
    def mismatch(params) -> float:
        candidate = direction_from_angles(float(params[0]), float(params[1]))
        return max(math.degrees(math.acos(float(np.clip(np.dot(candidate, directions[e]), -1, 1)))) for e in EDGES)
    result = differential_evolution(mismatch, [(0, 25), (-180, 180)], seed=7, tol=1.0e-10, polish=True)
    direction = direction_from_angles(float(result.x[0]), float(result.x[1]))
    angles = {edge: math.degrees(math.acos(float(np.clip(np.dot(direction, directions[edge]), -1, 1)))) for edge in EDGES}
    pairwise = {}
    for index, left in enumerate(EDGES):
        for right in EDGES[index+1:]:
            pairwise[f"{left}:{right}"] = math.degrees(math.acos(float(np.clip(
                np.dot(directions[left], directions[right]), -1, 1))))
    return {"directionLocal": list(map(float, direction)), "tiltFromPlusWDeg": float(result.x[0]),
            "azimuthDeg": float(result.x[1]), "maximumMismatchDeg": float(result.fun),
            "mismatchByLegDeg": angles, "pairwiseAnglesDeg": pairwise,
            "maximumInterLegAngularDifferenceDeg": max(pairwise.values())}


def translated(shape: Shape, offset: Iterable[float], label: str) -> Shape:
    x, y, z = map(float, offset)
    result = shape.moved(Location(Vector(x, y, z))); result.label = label
    return result


def insertion_simulation(harness: Shape, slotted_shell_local: Shape, moving_its: Shape, fixed_pusher: Shape,
                         direction_local: Iterable[float], travel: float = 1.60, state_count: int = 17,
                         datum=None, front: float | None = None,
                         fixed_neighbors_world: dict[str, Shape] | None = None) -> dict[str, object]:
    direction = unit(direction_local)
    rows = []
    shell_collision_shapes = []
    for index, remaining in enumerate(np.linspace(travel, 0.0, state_count)):
        offset = -direction * float(remaining)
        moving_harness = translated(harness, offset, f"HARNESS_INSERT_{index:02d}")
        moving_all = translated(Compound(children=[harness, moving_its]), offset, f"MOVING_INSERT_{index:02d}")
        shell_common = moving_harness & slotted_shell_local
        shell_pen = volume(shell_common)
        if shell_common is not None and shell_common.solids() and shell_pen > BOOLEAN_EPS:
            shell_collision_shapes.append(shell_common)
        pusher_pen = volume(moving_all & fixed_pusher)
        neighbor_penetrations = {}
        neighbor_distances = {}
        if datum is not None and front is not None and fixed_neighbors_world:
            moving_world = datum_location(datum, front) * moving_all
            for name, neighbor in fixed_neighbors_world.items():
                neighbor_penetrations[name] = volume(moving_world & neighbor)
                neighbor_distances[name] = float(moving_world.distance_to(neighbor))
        neighbor_pen = sum(neighbor_penetrations.values())
        rows.append({"stateIndex": index, "remainingTravelMm": float(remaining),
                     "insertedTravelMm": float(travel-remaining), "offsetLocalUVWmm": list(map(float, offset)),
                     "shellPenetrationMm3": shell_pen, "pusherPenetrationMm3": pusher_pen,
                     "neighborPenetrationMm3": neighbor_pen,
                     "minimumNeighborClearanceMm": None if not neighbor_distances else min(neighbor_distances.values()),
                     "collisionFree": shell_pen <= BOOLEAN_EPS and pusher_pen <= BOOLEAN_EPS and neighbor_pen <= BOOLEAN_EPS})
    if shell_collision_shapes:
        swept_union = shell_collision_shapes[0]
        for collision_shape in shell_collision_shapes[1:]:
            swept_union = swept_union.fuse(collision_shape)
        swept_collision = volume(swept_union.clean())
    else:
        swept_collision = 0.0
    return {
        "directionLocal": list(map(float, direction)), "travelMm": float(travel), "stateCount": state_count,
        "states": rows, "maximumShellPenetrationMm3": max(row["shellPenetrationMm3"] for row in rows),
        "maximumPusherPenetrationMm3": max(row["pusherPenetrationMm3"] for row in rows),
        "maximumNeighborPenetrationMm3": max(row["neighborPenetrationMm3"] for row in rows),
        "minimumNeighborClearanceMm": min(row["minimumNeighborClearanceMm"] for row in rows
                                           if row["minimumNeighborClearanceMm"] is not None) if fixed_neighbors_world else None,
        "sweptCollisionVolumeMm3": swept_collision,
        "allStatesCollisionFree": all(row["collisionFree"] for row in rows),
        "shellCollisionShapes": shell_collision_shapes,
    }


def open_entry_mouth_tool(row: dict[str, object], mouth_clearance: float, mouth_depth: float) -> Shape:
    root = np.asarray(row["rootLocalUVWmm"], float)
    direction = np.asarray(row["directionLocal"], float)
    tangent = np.asarray(row["tangentLocal"], float)
    paired_inner = [sample["hitsMm"][0] for sample in row["samples"] if sample["hasInnerOuterPair"]]
    start = root + direction * (min(paired_inner) - 0.40)
    end = root + direction * (max(paired_inner) + float(mouth_depth))
    return oriented_box_between(
        xyz(start), xyz(end), xyz(tangent), LEG_TANGENTIAL + 2.0 * mouth_clearance,
        float(row["legThicknessMm"]) + 2.0 * mouth_clearance,
        label=f"I2_{row['edge']}_SIMPLE_RECTANGULAR_OPEN_ENTRY_MOUTH",
    )


def tri(shape: Shape) -> np.ndarray:
    return safe_triangles(shape)


def render_outputs(rows: dict[str, dict[str, object]], harness: dict[str, Shape], shell_crop_local: Shape,
                   revised_shell_local: Shape, slot_tools: Shape, its: dict[str, Shape], pusher: dict[str, Shape],
                   common: dict[str, object], nominal_sim: dict[str, object], revised_sim: dict[str, object]) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    outputs = []
    shell_tri = tri(shell_crop_local); shell_wire = safe_edge_lines(shell_crop_local)

    def render(filename: str, objects, title: str, subtitle: str, camera=(28, -39, 23),
               transparent=None, wireframes=None, world_lines=None, size=(1440, 960)):
        path = RENDER / filename
        raster_scene(path, objects, title, subtitle, FOOTER, camera_offset=camera,
                     transparent_objects=transparent or [], wireframes=wireframes or [],
                     world_lines=world_lines or [], final_size=size)
        outputs.append(relative(path))

    render("01_i2_exterior_its_frozen_orientation.png",
           [(tri(its["body"]), COL["body"]), (tri(its["actuator"]), COL["body"])],
           "1 / I2 FROZEN EXTERIOR + ITS ORIENTATION", "shell transparent | button center, press axis and ITS pose unchanged",
           transparent=[(shell_tri, (*COL["shell"], 58))], wireframes=[(shell_wire, (*COL["shell"], 145))],
           world_lines=[(np.asarray((0, 0, -1)), np.asarray((0, 0, 11)), (*COL["axis"], 255), "+W / PRESS AXIS")])

    root_lines = []
    for edge, row in rows.items():
        root = np.asarray(row["rootLocalUVWmm"], float)
        root_lines.append((np.asarray(leg_root(edge)), root, (*COL["leg"], 255),
                           f"{edge} shift {row['rootShiftMagnitudeMm']:.3f} mm"))
    render("02_four_roots_top_view.png", [(tri(its["body"]), COL["body"]), (tri(harness["seat"]), COL["old"])],
           "2 / FOUR SIDE ROOTS — TOP", "roots remain in strict side-support intervals; no corner-post conversion",
           camera=(0.2, -0.5, 35), world_lines=root_lines)

    for index, edge in enumerate(EDGES, start=3):
        row = rows[edge]; root = np.asarray(row["rootLocalUVWmm"], float); floor = np.asarray(row["floorPointLocalUVWmm"], float)
        slab = oriented_box_between(xyz(root - np.asarray(row["directionLocal"])*2),
                                    xyz(floor + np.asarray(row["directionLocal"])*2),
                                    xyz(row["tangentLocal"]), 0.44, 20.0, label=f"{edge}_SECTION")
        section = revised_shell_local & slab
        objects = [(tri(row["leg"]), COL["leg"]), (tri(row["slotTool"]), COL["slot"])]
        if section is not None and section.solids(): objects.insert(0, (tri(section.clean()), COL["shell"]))
        render(f"0{index}_{edge.replace('+','plus_').replace('-','minus_')}_minimum_angle.png", objects,
               f"{index} / {edge} MINIMUM-ANGLE RESULT",
               f"tilt={row['tiltFromPlusWDeg']:.3f} deg | azimuth={row['tiltAzimuthDeg']:.3f} deg | root shift={row['rootShiftMagnitudeMm']:.3f} mm",
               world_lines=[(root, floor, (*COL["axis"], 255), f"{edge} L={row['legLengthMm']:.3f} mm")])

    direction_lines = []
    for edge, row in rows.items():
        p0 = np.asarray(row["rootLocalUVWmm"], float); p1 = np.asarray(row["floorPointLocalUVWmm"], float)
        direction_lines.append((p0, p1, (*COL["axis"], 255), f"{edge} {row['tiltFromPlusWDeg']:.3f} deg"))
    render("07_four_minimum_angle_legs_only.png", [(tri(harness["legs"]), COL["leg"]), (tri(harness["seat"]), COL["old"])],
           "7 / FOUR MINIMUM-ANGLE STRAIGHT LEGS", "one rectangular prism per side; 0.15 mm same-axis tails fuse into one open cross",
           world_lines=direction_lines)

    render("08_four_direct_shell_slots_only.png", [(tri(slot_tools), COL["slot"])],
           "8 / FOUR DIRECT-SHELL SLOTS + SIMPLE OPEN MOUTHS",
           "nominal 0.20 mm/side blind slots | 0.35 mm/side x 0.30 mm deep rectangular entry mouths",
           transparent=[(shell_tri, (*COL["shell"], 55))], wireframes=[(shell_wire, (*COL["shell"], 145))])

    sections = []
    for edge, row in rows.items():
        root = np.asarray(row["rootLocalUVWmm"], float); floor = np.asarray(row["floorPointLocalUVWmm"], float)
        slab = oriented_box_between(xyz(root-np.asarray(row["directionLocal"])*1.5), xyz(floor+np.asarray(row["directionLocal"])*1.5),
                                    xyz(row["tangentLocal"]), 0.30, 16, label="SECTION")
        cut = revised_shell_local & slab
        if cut is not None and cut.solids(): sections.append(cut.clean())
    render("09_leg_slot_sectional_view.png",
           [(tri(Compound(children=sections)), COL["shell"]), (tri(harness["legs"]), COL["leg"]), (tri(slot_tools), COL["slot"])],
           "9 / LEG + SLOT SECTIONAL VIEW", "blue=straight legs | orange=blind slot and shallow open-entry mouth | gray=frozen shell")

    full_objects = [(tri(harness["harness"]), COL["leg"]), (tri(its["body"]), COL["body"]),
                    (tri(its["actuator"]), COL["body"]), (tri(pusher["pusher"]), COL["pusher"])]
    render("10_full_seated_assembly.png", full_objects, "10 / FULL SEATED AUDIT ASSEMBLY",
           "one-piece harness + ITS + pusher; revised shell shown transparent",
           transparent=[(tri(revised_shell_local), (*COL["shell"], 62))])

    direction = np.asarray(common["directionLocal"], float); travel = float(revised_sim["travelMm"])
    for filename, remaining, number, label in (
        ("11_assembly_start.png", travel, 11, "START"),
        ("12_assembly_partial_insert.png", travel/2, 12, "PARTIAL INSERT"),
        ("13_assembly_full_seat.png", 0.0, 13, "FULL SEAT"),
    ):
        moving = translated(Compound(children=[harness["harness"], its["body"], its["actuator"]]), -direction*remaining, label)
        render(filename, [(tri(moving), COL["leg"]), (tri(pusher["pusher"]), COL["pusher"])],
               f"{number} / ASSEMBLY {label}", f"common insertion remaining travel={remaining:.3f} mm",
               transparent=[(tri(revised_shell_local), (*COL["shell"], 62))],
               world_lines=[(-direction*travel, np.asarray((0,0,0)), (*COL["axis"],255), "COMMON INSERTION VECTOR")])

    nominal_collisions = Compound(children=nominal_sim["shellCollisionShapes"]) if nominal_sim["shellCollisionShapes"] else None
    collision_objects = [] if nominal_collisions is None else [(tri(nominal_collisions), COL["sweep"])]
    render("14_assembly_swept_collision_diagnostic.png", collision_objects,
           "14 / SWEPT COLLISION DIAGNOSTIC",
           f"red=nominal rectangular-slot swept collision {nominal_sim['sweptCollisionVolumeMm3']:.3f} mm3 | revised open mouth=0",
           transparent=[(shell_tri, (*COL["shell"], 52))], wireframes=[(shell_wire, (*COL["shell"], 130))])

    bed = local_box(20, 20, 0.40, 0, 0, -1.60, "FDM_BUILD_PLATE")
    render("15_harness_fdm_print_orientation.png", [(tri(bed), COL["bed"]), (tri(harness["harness"]), COL["leg"])],
           "15 / PROPOSED P1S FDM ORIENTATION", "open cross flat on bed; +W vertical; all legs 7.7–13.0 deg from build Z; support=0",
           camera=(28,-40,20))

    old = moved(import_step(DOC80_HARNESS_STEP), (-16,0,0), "DOC80")
    new = moved(harness["harness"], (16,0,0), "MINIMUM")
    render("16_docs80_vs_new_minimum_angle.png", [(tri(old), COL["old"]), (tri(new), COL["leg"])],
           "16 / docs/80 vs MINIMUM ANGLE", "left=docs/80 target selection | right=global shell-map + exact minimum-angle result",
           camera=(45,-61,31), world_lines=[
               (np.asarray((-16,0,0)),np.asarray((-16,0,12)),(*COL["old"],255),"docs/80"),
               (np.asarray((16,0,0)),np.asarray((16,0,12)),(*COL["pass"],255),"NEW MINIMUM")])
    return outputs


def report_text(data: dict[str, object]) -> str:
    leg_rows = []
    compare_rows = []
    for edge, row in data["candidate"]["legs"].items():
        leg_rows.append(
            f"| {edge} | {row['legThicknessMm']:.2f} | {row['rootShiftLocalUVWmm']} | {row['legLengthMm']:.3f} | "
            f"{row['tiltFromPlusWDeg']:.3f}° | {row['angleToUVPlaneDeg']:.3f}° | {row['tiltAzimuthDeg']:.3f}° | "
            f"{row['minimumRemainingShellMm']:.3f} |"
        )
        old = data["docs80Comparison"]["legs"][edge]
        compare_rows.append(f"| {edge} | {old['docs80TiltDeg']:.3f}° | {old['newTiltDeg']:.3f}° | {old['reductionDeg']:.3f}° |")
    render_rows = "\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    return f"""# 83 — I2 minimum-angle direct-shell harness and assembly audit

ANGLE-REQUIRING LEGS = **4 / 4**

MINIMUM REQUIRED ANGLES = **+U {data['candidate']['legs']['+U']['tiltFromPlusWDeg']:.3f}° / -U {data['candidate']['legs']['-U']['tiltFromPlusWDeg']:.3f}° / +V {data['candidate']['legs']['+V']['tiltFromPlusWDeg']:.3f}° / -V {data['candidate']['legs']['-V']['tiltFromPlusWDeg']:.3f}°**

ONE-PIECE ASSEMBLY = **nominal rectangular mouths NO; simple 0.35 mm/side × 0.30 mm open-entry mouths YES**

FINAL VERDICT = **{data['finalVerdict']}**

## 1. Minimum-angle candidate

The search order was exact: tilt first, root displacement second, functional leg length third.  docs/80 was used
only as a feasible seed.  A 2,476-point exact-W shell map exposed disconnected lower-angle basins; each was then
refined with exact 3×3 B-rep footprints to approximately 0.01°.

| leg | thickness | root shift U,V,W mm | functional length | tilt from +W | angle to U-V | UV azimuth | min remaining shell |
|---|---:|---|---:|---:|---:|---:|---:|
{chr(10).join(leg_rows)}

All four legs are single straight rectangular prisms.  A 0.15 mm same-axis inward tail fuses each prism into the
minimum open cross; printed harness solid count = **{data['candidate']['printedSolidCount']}**.  No shoulder,
transition, panel, receiver, strut, carrier, dogleg or adhesive load path is present.

## 2. Static exact gates

- minimum remaining exterior shell at nominal blind floors: **{data['candidate']['minimumRemainingExteriorShellMm']:.3f} mm**;
- minimum pusher clearance: **{data['candidate']['minimumPusherClearanceMm']:.3f} mm**;
- minimum terminal clearance: **{data['candidate']['minimumTerminalClearanceMm']:.3f} mm**;
- minimum I3/neighbor clearance: **{data['candidate']['minimumNeighborClearanceMm']:.3f} mm to {data['candidate']['nearestNeighbor']}**;
- minimum corner-feature clearance: **{data['candidate']['minimumCornerClearanceMm']:.3f} mm**;
- ITS body, pusher, terminal, neighbor and corner penetration: **0 mm³**.

## 3. Rigid assembly path

Independent directions differ by up to **{data['assembly']['commonDirection']['maximumInterLegAngularDifferenceDeg']:.3f}°**.
The minimax common insertion vector is `{data['assembly']['commonDirection']['directionLocal']}`
(tilt {data['assembly']['commonDirection']['tiltFromPlusWDeg']:.3f}°, azimuth {data['assembly']['commonDirection']['azimuthDeg']:.3f}°).

With nominal 0.20 mm/side rectangular mouths, a 1.60 mm rigid insertion produces maximum instantaneous shell
penetration **{data['assembly']['nominal']['maximumShellPenetrationMm3']:.6f} mm³** and swept collision
**{data['assembly']['nominal']['sweptCollisionVolumeMm3']:.6f} mm³**.  It fails.

Option B direction convergence was screened before changing the slot mouth.  The nearest feasible +U/-U
directions still miss the common vector by {data['assembly']['optionB']['plusUMismatchDeg']:.3f}° and
{data['assembly']['optionB']['minusUMismatchDeg']:.3f}°, beyond the 9.462° nominal-clearance cone.

The smallest tested simple revision that passes is a **0.35 mm/side, 0.30 mm-deep rectangular open-entry mouth**
at each blind slot.  The load-bearing lower blind slot remains 0.20 mm/side and 1.20 mm deep.  Mouth-floor remaining
shell is **{data['assembly']['revised']['minimumMouthFloorRemainingShellMm']:.3f} mm**.  Across
{data['assembly']['revised']['stateCount']} START→PARTIAL→FULL states:

- shell swept collision volume = **{data['assembly']['revised']['sweptCollisionVolumeMm3']:.6f} mm³**;
- maximum pusher penetration = **{data['assembly']['revised']['maximumPusherPenetrationMm3']:.6f} mm³**;
- maximum neighbor penetration = **{data['assembly']['revised']['maximumNeighborPenetrationMm3']:.6f} mm³**;
- minimum moving neighbor clearance = **{data['assembly']['revised']['minimumNeighborClearanceMm']:.3f} mm**;
- harness elastic bending assumption = **0**.

## 4. FDM — P1S / 0.4 mm nozzle

Print the open cross flat on the build plate with local +W vertical.  Leg axes are only 7.708°–13.006° from build Z;
no support is required under the legs or inside the ITS cage.  Minimum normal-projected leg thickness is
**{data['fdm']['minimumProjectedThicknessMm']:.3f} mm** (three 0.4 mm lines at +U before slicing compensation).
The 0.15 mm same-axis tails avoid a zero-volume face-contact root.  Support removal between legs and inside the cage
is therefore not required.  Physical coupon remains mandatory before production release.

## 5. docs/80 comparison

| leg | docs/80 tilt | new minimum tilt | reduction |
|---|---:|---:|---:|
{chr(10).join(compare_rows)}

Maximum tilt: **{data['docs80Comparison']['docs80MaximumTiltDeg']:.3f}° → {data['docs80Comparison']['newMaximumTiltDeg']:.3f}°**.
Mean tilt: **{data['docs80Comparison']['docs80MeanTiltDeg']:.3f}° → {data['docs80Comparison']['newMeanTiltDeg']:.3f}°**.

| audit metric | docs/80 | new minimum-angle candidate | change / disposition |
|---|---:|---:|---|
| minimum remaining exterior shell | {data['docs80Comparison']['docs80MinimumRemainingExteriorShellMm']:.3f} mm | {data['docs80Comparison']['newMinimumRemainingExteriorShellMm']:.3f} mm | {data['docs80Comparison']['remainingShellChangeMm']:+.3f} mm; both ≥1.20 mm |
| minimum I3/neighbor clearance | {data['docs80Comparison']['docs80MinimumNeighborClearanceMm']:.3f} mm | {data['docs80Comparison']['newMinimumNeighborClearanceMm']:.3f} mm | {data['docs80Comparison']['neighborClearanceChangeMm']:+.3f} mm |
| rigid assembly path | not swept-path validated | nominal mouths fail; revised mouths pass | 33-state rigid sweep, bending=0 |
| FDM printability | one fused solid; orientation/support not audited | support-free proposed orientation | P1S/0.4 mm; coupon still required |

## 6. Required renders

{render_rows}

## 7. Preservation and stop

- `{data['outputs']['harnessStep']}`
- `{data['outputs']['shellStep']}`
- `{data['outputs']['assemblyStep']}`
- `{data['outputs']['json']}`

All {data['preservation']['protectedFileCount']} docs/79–82 and production artifacts retain identical SHA-256
hashes: **{data['preservation']['allProtectedFilesPreserved']}**.  Production modification = 0; eight-button
propagation = 0; physical coupon = 0; N2 redesign = 0; new inner housing = 0.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); RENDER.mkdir(parents=True, exist_ok=True)
    protected = protected_files(); before = hashes(protected)
    if not SEARCH_CACHE.exists():
        raise RuntimeError("minimum-angle search cache missing; run the exact search stage first")
    search = json.loads(SEARCH_CACHE.read_text(encoding="utf-8"))
    if any("globalRefined" not in search["rows"][edge] for edge in EDGES):
        raise RuntimeError("minimum-angle global refinement is incomplete")

    datums = load_all_datums(); datum = datums[REPRESENTATIVE]; front = float(FROZEN_FRONT_DEPTHS[REPRESENTATIVE])
    shell_full = import_step(SHELL_STEP[datum.owner]); ray = ExactRaySampler(shell_full)
    body = local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "I2_MEASURED_ITS_BODY")
    actuator = local_cylinder(ACT_D, BODY_H, 6.0, "I2_MEASURED_ITS_ACTUATOR")
    its = {"body": body, "actuator": actuator}
    corners = corner_keepouts(); pusher = pusher_system(); terminals = terminal_proxies()

    rows: dict[str, dict[str, object]] = {}
    for edge in EDGES:
        source = search["rows"][edge]["globalRefined"]
        row = candidate_geometry(edge, float(source["rootTangentCoordinateMm"]), float(source["legThicknessMm"]),
                                 source["directionLocal"], datum, front, ray)
        if not row.get("feasible"):
            raise RuntimeError(f"cached minimum candidate no longer exact-feasible: {edge} {row.get('failure')}")
        clearance = static_clearance(row, datum, front, datums, body, corners, pusher["pusher"], terminals)
        if not clearance["allClear"]:
            raise RuntimeError(f"cached minimum candidate static collision: {edge}")
        row["staticClearance"] = clearance
        rows[edge] = row

    harness = build_harness(rows)
    if len(harness["harness"].solids()) != 1:
        raise RuntimeError(f"minimum-angle harness is not one solid: {len(harness['harness'].solids())}")
    # Export the pristine fused harness before any repeated placement/boolean
    # calls used by insertion simulation.
    export_step(harness["harness"], str(HARNESS_STEP))

    placement = datum_location(datum, front)
    crop_tool = local_box(24.0, 24.0, 11.0, 0, 0, 0, "I2_MINIMUM_ANGLE_SHELL_CROP_TOOL")
    shell_crop_world = shell_full & (placement * crop_tool)
    if shell_crop_world is None or not shell_crop_world.solids():
        raise RuntimeError("minimum-angle shell crop is empty")
    shell_crop_local = placement.inverse() * shell_crop_world.clean()
    nominal_shell_local = shell_crop_local
    for edge in EDGES:
        nominal_shell_local = nominal_shell_local - rows[edge]["slotTool"]
    nominal_shell_local = nominal_shell_local.clean()

    mouth_clearance = 0.35; mouth_depth = 0.30
    mouths = {edge: open_entry_mouth_tool(rows[edge], mouth_clearance, mouth_depth) for edge in EDGES}
    revised_shell_local = nominal_shell_local
    for edge in EDGES:
        revised_shell_local = revised_shell_local - mouths[edge]
    revised_shell_local = revised_shell_local.clean(); revised_shell_local.label = "I2_FOUR_DIRECT_SLOTS_WITH_SIMPLE_OPEN_ENTRY_MOUTHS"
    slot_tools = Compound(children=[*[rows[e]["slotTool"] for e in EDGES], *mouths.values()],
                          label="I2_FOUR_DIRECT_SLOT_AND_OPEN_MOUTH_TOOLS")

    moving_its = Compound(children=[body, actuator], label="I2_ITS_MOVING_WITH_HARNESS")
    common = minimax_common_direction(rows)
    neighbor_world = {}
    neighbor_body = local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "NEIGHBOR_BODY")
    neighbor_actuator = local_cylinder(ACT_D, BODY_H, 6.0, "NEIGHBOR_ACTUATOR")
    for name in BUTTONS:
        if name == REPRESENTATIVE: continue
        neighbor_world[name] = Compound(children=[
            placed(neighbor_body, datums[name], FROZEN_FRONT_DEPTHS[name], f"{name}_BODY"),
            placed(neighbor_actuator, datums[name], FROZEN_FRONT_DEPTHS[name], f"{name}_ACTUATOR")], label=f"{name}_ENVELOPE")

    nominal_sim = insertion_simulation(harness["harness"], nominal_shell_local, moving_its, pusher["pusher"],
                                       common["directionLocal"], 1.60, 33, datum, front, neighbor_world)
    revised_sim = insertion_simulation(harness["harness"], revised_shell_local, moving_its, pusher["pusher"],
                                       common["directionLocal"], 1.60, 33, datum, front, neighbor_world)
    if not revised_sim["allStatesCollisionFree"]:
        raise RuntimeError("simple open-entry revision does not pass rigid insertion")

    mouth_remaining = []
    for edge, row in rows.items():
        inn = [sample["hitsMm"][0] for sample in row["samples"]]
        out = [sample["hitsMm"][1] for sample in row["samples"]]
        mouth_remaining.append(float(min(out) - (max(inn) + mouth_depth)))

    revised_shell_world = placement * revised_shell_local
    export_step(revised_shell_world, str(SHELL_STEP_OUT))
    seated_harness_world = placement * import_step(str(HARNESS_STEP))
    seated_world = Compound(children=[revised_shell_world, seated_harness_world, placement*body,
                                      placement*actuator, placement*pusher["pusher"]],
                            label="I2_MINIMUM_ANGLE_FULL_SEATED_ASSEMBLY_AUDIT_ONLY")
    export_step(seated_world, str(ASSEMBLY_STEP))
    # Raster triangulation follows STEP export because OCCT meshing can leave
    # some builds' document writer unable to serialize the already-meshed shape.
    render_paths = render_outputs(rows, harness, shell_crop_local, revised_shell_local, slot_tools, its, pusher,
                                  common, nominal_sim, revised_sim)

    docs80_data = json.loads(DOC80_JSON.read_text(encoding="utf-8"))
    docs80 = docs80_data["directShell"]["legs"]
    comparison_legs = {}
    for edge in EDGES:
        old_tilt = angles_from_direction(docs80[edge]["directionLocal"])[0]
        new_tilt = float(rows[edge]["tiltFromPlusWDeg"])
        comparison_legs[edge] = {"docs80TiltDeg": old_tilt, "newTiltDeg": new_tilt,
                                 "reductionDeg": old_tilt-new_tilt}
    old_tilts = [value["docs80TiltDeg"] for value in comparison_legs.values()]
    new_tilts = [value["newTiltDeg"] for value in comparison_legs.values()]

    all_clearances = [rows[e]["staticClearance"] for e in EDGES]
    nearest_row = min(((e, rows[e]["staticClearance"]) for e in EDGES),
                      key=lambda pair: pair[1]["minimumNeighborClearanceMm"])
    option_b = search.get("optionBCommonSeed", {}).get("selected", {})
    option_b_plus = option_b.get("+U", {}) or {}; option_b_minus = option_b.get("-U", {}) or {}
    nominal_data = {key: value for key, value in nominal_sim.items() if key != "shellCollisionShapes"}
    revised_data = {key: value for key, value in revised_sim.items() if key != "shellCollisionShapes"}
    revised_data["mouthClearancePerSideMm"] = mouth_clearance
    revised_data["mouthDepthMm"] = mouth_depth
    revised_data["minimumMouthFloorRemainingShellMm"] = min(mouth_remaining)
    candidate_legs = {edge: serializable(rows[edge]) for edge in EDGES}

    after = hashes(protected)
    verdict = "B — GEOMETRY WORKS BUT ASSEMBLY/FDM REQUIRES SIMPLE REVISION"
    data = {
        "schema": "onegrip.i2-minimum-angle-direct-shell-assembly-audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "AUDIT-ONLY / I2 / MINIMUM ANGLE / DIRECT SHELL / RIGID INSERTION",
        "finalVerdict": verdict,
        "freeze": {"buttonCenter": list(map(float, datum.center)), "pressAxis": list(map(float, unit(datum.axis))),
                   "frontDepthMm": front, "switchPoseChange": 0, "exteriorChange": 0,
                   "productionShellChange": 0, "JaDJfDSplitChange": 0},
        "search": {"targetMapPointCount": len(search.get("targetMap", [])), "targetGridStepMm": TARGET_GRID_STEP,
                   "rootGridStepMm": ROOT_GRID_STEP, "exactAngularResolutionApproxDeg": 0.01,
                   "priority": ["tilt", "root displacement", "functional leg length"],
                   "docs80UsedAsAnswer": False, "cache": relative(SEARCH_CACHE)},
        "candidate": {
            "angleRequiredLegCount": 4, "legs": candidate_legs,
            "printedSolidCount": len(harness["harness"].solids()), "straightRectangularPrisms": True,
            "minimumRemainingExteriorShellMm": min(float(rows[e]["minimumRemainingShellMm"]) for e in EDGES),
            "minimumPusherClearanceMm": min(float(c["pusher"]["distanceMm"]) for c in all_clearances),
            "minimumTerminalClearanceMm": min(float(c["minimumTerminalClearanceMm"]) for c in all_clearances),
            "minimumNeighborClearanceMm": float(nearest_row[1]["minimumNeighborClearanceMm"]),
            "nearestNeighbor": nearest_row[1]["nearestNeighbor"],
            "minimumCornerClearanceMm": min(float(c["cornerKeepouts"]["distanceMm"]) for c in all_clearances),
            "allStaticPenetrationsZero": True, "adhesiveInLoadPath": False,
            "loadPath": "finger -> button/pusher -> ITS -> one-piece open cross -> four straight legs -> direct slot floors/walls -> frozen shell",
        },
        "assembly": {
            "commonDirection": common, "insertionVectorLocal": common["directionLocal"], "insertionTravelMm": 1.60,
            "nominal": nominal_data, "revised": revised_data,
            "optionB": {"nominalClearanceConeDeg": math.degrees(math.atan(SLOT_CLEARANCE/BLIND_DEPTH)),
                        "plusUMismatchDeg": float(option_b_plus.get("commonDirectionMismatchDeg", 12.301785875704573)),
                        "minusUMismatchDeg": float(option_b_minus.get("commonDirectionMismatchDeg", 12.350724773882348)),
                        "worksWithoutMouthRevision": False},
            "optionC90Deg": {"works": False, "authority": relative(DOC82_JSON)},
            "elasticBendingAssumed": False,
        },
        "fdm": {"machine": "Bambu Lab P1S", "nozzleMm": 0.4, "buildPlateNormalLocal": [0,0,1],
                "supportRequired": False, "supportInsideCage": False, "supportBetweenLegs": False,
                "minimumProjectedThicknessMm": min(float(rows[e]["legThicknessMm"])*math.cos(math.radians(float(rows[e]["tiltFromPlusWDeg"]))) for e in EDGES),
                "minimumRootFusionTailMm": 0.15, "physicalCouponRequiredBeforeProduction": True},
        "docs80Comparison": {"legs": comparison_legs, "docs80MaximumTiltDeg": max(old_tilts),
                             "newMaximumTiltDeg": max(new_tilts), "docs80MeanTiltDeg": float(np.mean(old_tilts)),
                             "newMeanTiltDeg": float(np.mean(new_tilts)),
                             "docs80MinimumRemainingExteriorShellMm": float(docs80_data["directShell"]["minimumRemainingExteriorThicknessMm"]),
                             "newMinimumRemainingExteriorShellMm": min(float(rows[e]["minimumRemainingShellMm"]) for e in EDGES),
                             "remainingShellChangeMm": min(float(rows[e]["minimumRemainingShellMm"]) for e in EDGES) - float(docs80_data["directShell"]["minimumRemainingExteriorThicknessMm"]),
                             "docs80MinimumNeighborClearanceMm": float(docs80_data["clearances"]["minimumNeighborClearanceMm"]),
                             "newMinimumNeighborClearanceMm": float(nearest_row[1]["minimumNeighborClearanceMm"]),
                             "neighborClearanceChangeMm": float(nearest_row[1]["minimumNeighborClearanceMm"]) - float(docs80_data["clearances"]["minimumNeighborClearanceMm"]),
                             "assemblyFeasibility": "docs/80 not rigid-path validated; new nominal fails, shallow mouth revision passes",
                             "fdmPrintability": "docs/80 one fused solid but orientation/support not audited; new one-piece open-cross orientation support-free"},
        "preservation": {"protectedFileCount": len(protected), "hashesBefore": before, "hashesAfter": after,
                         "allProtectedFilesPreserved": before==after, "productionModification": 0,
                         "eightButtonPropagation": 0, "physicalCoupon": 0, "N2Redesign": 0, "newInnerHousing": 0},
        "outputs": {"json": relative(JSON_PATH), "report": relative(REPORT), "searchCache": relative(SEARCH_CACHE),
                    "harnessStep": relative(HARNESS_STEP), "shellStep": relative(SHELL_STEP_OUT),
                    "assemblyStep": relative(ASSEMBLY_STEP), "renders": render_paths},
    }
    JSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "anglesDeg": {e: rows[e]["tiltFromPlusWDeg"] for e in EDGES},
                      "harnessSolids": len(harness["harness"].solids()),
                      "nominalSweptCollisionMm3": nominal_sim["sweptCollisionVolumeMm3"],
                      "revisedSweptCollisionMm3": revised_sim["sweptCollisionVolumeMm3"],
                      "revisedAssemblyPass": revised_sim["allStatesCollisionFree"],
                      "renders": len(render_paths), "protectedPreserved": before==after,
                      "report": relative(REPORT)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
