"""Audit-only I2 detailed-PushBtn manufacturing-robust harness revalidation.

The original OneGrip 3,530-facet PushBtn is the switch geometry authority.
Only its actuator is replaced by the measured ITS-1105 D3.35 x 2.44 mm
moving element.  Production geometry and docs/79-83 remain read-only.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Align, Compound, Cylinder, Location, Plane, Shape, Vector, export_step, import_step

from . import i2_minimum_angle_direct_shell_assembly_audit as doc83
from .detailed_pushbtn_8_button_revalidation import build_original_parts
from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler, SHELL_STEP
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import local_box, local_cylinder, sha256, volume
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import BUTTONS, ROOT, relative
from .option_c_local_exact_prototype import raster_scene, safe_edge_lines, safe_triangles
from .slot_anchored_harness_captive_pusher_audit import pusher_system


OUT = ROOT / "build123d_workbench/out/i2_detailed_pushbtn_manufacturing_robust_audit"
RENDER = ROOT / "renders/i2_detailed_pushbtn_manufacturing_robust_audit"
REPORT = ROOT / "docs/84_i2_detailed_pushbtn_manufacturing_robust_audit.md"
JSON_PATH = OUT / "i2_detailed_pushbtn_manufacturing_robust_audit.json"
ORIGINAL_STEP = OUT / "ORIGINAL_ONEGRIP_PUSHBTN_3530_FACET_REFERENCE_AUDIT_ONLY.step"
HYBRID_STEP = OUT / "I2_ORIGINAL_PUSHBTN_MEASURED_ACTUATOR_HYBRID_AUDIT_ONLY.step"
HARNESS_STEP = OUT / "I2_DETAILED_PUSHBTN_ROBUST_FOUR_EDGE_HARNESS_AUDIT_ONLY.step"
SHELL_STEP_OUT = OUT / "I2_ROBUST_FOUR_DIRECT_SLOT_SHELL_CROP_AUDIT_ONLY.step"
ASSEMBLY_STEP = OUT / "I2_DETAILED_PUSHBTN_ROBUST_FULL_ASSEMBLY_AUDIT_ONLY.step"

SOURCE_MESH = ROOT / "cad_dump/mesh_PushBtn.json"
DOC83_JSON = ROOT / "build123d_workbench/out/i2_minimum_angle_direct_shell_assembly_audit/i2_minimum_angle_direct_shell_assembly_audit.json"
DOC83_HARNESS = ROOT / "build123d_workbench/out/i2_minimum_angle_direct_shell_assembly_audit/I2_MINIMUM_ANGLE_FOUR_EDGE_HARNESS_AUDIT_ONLY.step"
DOC83_SHELL = ROOT / "build123d_workbench/out/i2_minimum_angle_direct_shell_assembly_audit/I2_MINIMUM_ANGLE_FOUR_SLOT_SHELL_CROP_AUDIT_ONLY.step"

REPRESENTATIVE = "I2"
EDGES = ("+U", "-U", "+V", "-V")
EPS = 1.0e-6
ORIGINAL_BODY_HEIGHT = 3.50
MEASURED_BODY_HEIGHT_REFERENCE = 3.56
ORIGINAL_BOTTOM_SHIFT_W = MEASURED_BODY_HEIGHT_REFERENCE - ORIGINAL_BODY_HEIGHT
ACTUATOR_DIAMETER = 3.35
ACTUATOR_PROJECTION = 2.44
ACTUATOR_BASE_W = 3.56
ACTUATOR_TIP_W = ACTUATOR_BASE_W + ACTUATOR_PROJECTION
INSERTION_TRAVEL = 1.60
INSERTION_STATES = 33
SLOT_CLEARANCE = 0.20
SLOT_DEPTH = 1.20
MOUTH_CLEARANCE = 1.03
MOUTH_DEPTH = 0.93
LEG_TANGENTIAL = 2.60
FOOTER = "AUDIT ONLY | ORIGINAL 3,530-FACET PUSHBTN | MEASURED ACTUATOR ONLY | PRODUCTION 0"
COL = {
    "original": (57, 166, 230), "body": (68, 170, 224), "terminal": (216, 225, 234),
    "actuator_old": (234, 168, 65), "actuator": (238, 91, 101), "harness": (67, 194, 145),
    "leg": (58, 165, 232), "slot": (245, 178, 65), "shell": (108, 130, 151),
    "pusher": (237, 132, 72), "neighbor": (171, 112, 219), "axis": (250, 213, 78),
    "fail": (235, 82, 93), "pass": (61, 190, 137), "bed": (108, 119, 133),
    "baseline": (92, 144, 190),
}

# Fixed result of the exact Pareto search documented in this audit.  The
# direction values are rechecked against the BRep at every run.
ROBUST_SPEC = {
    "+U": {"thickness": 1.25, "radialGap": 0.0815, "rootT": 1.715625,
            "tilt": 10.59711121399541, "azimuth": 17.60287504299439},
    "-U": {"thickness": 1.60, "radialGap": 0.30, "rootT": 0.075,
            "tilt": 18.23829152401644, "azimuth": -166.885455011668},
    "+V": {"thickness": 1.60, "radialGap": 0.12, "rootT": -1.76,
            "tilt": 11.008497859943024, "azimuth": 102.58522894105016},
    "-V": {"thickness": 1.60, "radialGap": 0.12, "rootT": 1.74,
            "tilt": 10.694884151199913, "azimuth": -89.46703137734593},
}


def xyz(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(map(float, value))


def moved(shape: Shape, offset: Iterable[float], label: str) -> Shape:
    x, y, z = map(float, offset)
    result = shape.moved(Location(Vector(x, y, z)))
    result.label = label
    return result


def translated(shape: Shape, offset: Iterable[float], label: str) -> Shape:
    return moved(shape, offset, label)


def protected_files() -> list[Path]:
    rows = set(doc83.protected_files())
    rows.update({
        ROOT / "docs/83_i2_minimum_angle_direct_shell_assembly_audit.md",
        ROOT / "build123d_workbench/i2_minimum_angle_direct_shell_assembly_audit.py",
        SOURCE_MESH,
    })
    prior_out = ROOT / "build123d_workbench/out/i2_minimum_angle_direct_shell_assembly_audit"
    prior_render = ROOT / "renders/i2_minimum_angle_direct_shell_assembly_audit"
    rows.update(path for path in prior_out.rglob("*") if path.is_file())
    rows.update(path for path in prior_render.rglob("*") if path.is_file())
    return sorted(path for path in rows if path.exists())


def hashes(paths: list[Path]) -> dict[str, str]:
    return {relative(path): sha256(path) for path in paths}


def original_functional_location() -> Location:
    # Raw source X/Y/Z -> functional U/W/-V.  W=+0.06 aligns the original
    # body front with the frozen measured-body front while preserving the
    # source main-body-bottom seating datum.
    return Plane(origin=(0, 0, ORIGINAL_BOTTOM_SHIFT_W), x_dir=(1, 0, 0), z_dir=(0, -1, 0)).location


def functional_source_triangles(raw: np.ndarray) -> np.ndarray:
    result = np.empty_like(raw, dtype=float)
    result[:, :, 0] = raw[:, :, 0]
    result[:, :, 1] = -raw[:, :, 2]
    result[:, :, 2] = raw[:, :, 1] + ORIGINAL_BOTTOM_SHIFT_W
    return result


def corner_features(body: Shape) -> Shape:
    tools = []
    for u0 in (-2.25, 2.25):
        for v0 in (-2.25, 2.25):
            tools.append(Cylinder(0.60, 0.70, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(
                Location(Vector(u0, v0, 2.96))))
    result = body & Compound(children=tools)
    result.label = "ORIGINAL_PUSHBTN_FOUR_EXACT_CORNER_FEATURES"
    return result


def detailed_switch_parts():
    original = build_original_parts()
    location = original_functional_location()
    body = location * original.body
    body.label = "ORIGINAL_ONEGRIP_PUSHBTN_DETAILED_PLASTIC_BODY_AND_CORNER_FEATURES"
    terminals = {name: location * shape for name, shape in original.terminals.items()}
    for name, shape in terminals.items():
        shape.label = f"ORIGINAL_ONEGRIP_PUSHBTN_DETAILED_{name}"
    old_actuator = location * original.actuator
    old_actuator.label = "ORIGINAL_PUSHBTN_ACTUATOR_REFERENCE_ONLY"
    actuator = local_cylinder(ACTUATOR_DIAMETER, ACTUATOR_BASE_W, ACTUATOR_TIP_W,
                              "MEASURED_ITS1105_ACTUATOR_D3P35_PROJECTION2P44")
    corners = corner_features(body)
    hybrid = Compound(children=[body, actuator, *terminals.values()],
                      label="ORIGINAL_DETAILED_PUSHBTN_PLUS_MEASURED_ACTUATOR")
    return original, body, terminals, corners, old_actuator, actuator, hybrid


def direction(tilt_deg: float, azimuth_deg: float) -> np.ndarray:
    return doc83.direction_from_angles(tilt_deg, azimuth_deg)


def custom_root(edge: str, thickness: float, radial_gap: float) -> np.ndarray:
    half = 3.155 if edge.endswith("U") else 3.005
    sign = 1.0 if edge.startswith("+") else -1.0
    radial = sign * (half + radial_gap + thickness / 2.0)
    return np.asarray((radial, 0.0, ORIGINAL_BOTTOM_SHIFT_W), float) if edge.endswith("U") \
        else np.asarray((0.0, radial, ORIGINAL_BOTTOM_SHIFT_W), float)


def make_candidate(edge: str, spec: dict[str, float], datum, front: float, ray: ExactRaySampler) -> dict[str, object]:
    base = custom_root(edge, float(spec["thickness"]), float(spec["radialGap"]))
    old_leg_root = doc83.leg_root
    try:
        doc83.leg_root = lambda _edge: base.copy()
        row = doc83.candidate_geometry(edge, float(spec["rootT"]), float(spec["thickness"]),
                                       direction(float(spec["tilt"]), float(spec["azimuth"])),
                                       datum, front, ray)
    finally:
        doc83.leg_root = old_leg_root
    if not row.get("feasible"):
        raise RuntimeError(f"robust {edge} candidate lost exact feasibility: {row.get('failure')}")
    row["radialGapMm"] = float(spec["radialGap"])
    row["rootShiftFromDocs83LocalUVWmm"] = list(map(float,
        np.asarray(row["rootLocalUVWmm"], float) - doc83.leg_root(edge)))
    row["effectiveFdmThicknessMm"] = float(spec["thickness"] * math.cos(math.radians(float(row["tiltFromPlusWDeg"]))))
    return row


def reconstruct_doc83_legs(data: dict[str, object]) -> dict[str, Shape]:
    result = {}
    for edge, row in data["candidate"]["legs"].items():
        start = np.asarray(row["rootLocalUVWmm"], float) - np.asarray(row["directionLocal"], float) * float(row["rootFusionOverlapMm"])
        end = np.asarray(row["floorPointLocalUVWmm"], float)
        result[edge] = oriented_box_between(xyz(start), xyz(end), xyz(row["tangentLocal"]),
                                            float(row["legTangentWidthMm"]), float(row["legThicknessMm"]),
                                            label=f"DOC83_{edge}_LEG")
    return result


def build_robust_harness(rows: dict[str, dict[str, object]]) -> dict[str, Shape]:
    u_min = float(rows["-U"]["rootLocalUVWmm"][0]); u_max = float(rows["+U"]["rootLocalUVWmm"][0])
    v_min = float(rows["-V"]["rootLocalUVWmm"][1]); v_max = float(rows["+V"]["rootLocalUVWmm"][1])
    seat_u = local_box(u_max-u_min, 1.60, 1.20, (u_min+u_max)/2, 0, -1.14,
                       "ORIGINAL_MAIN_BODY_BOTTOM_U_SUPPORT")
    seat_v = local_box(1.60, v_max-v_min, 1.20, 0, (v_min+v_max)/2, -1.14,
                       "ORIGINAL_MAIN_BODY_BOTTOM_V_SUPPORT")
    seat = seat_u.fuse(seat_v).clean(); seat.label = "ORIGINAL_MAIN_BODY_BOTTOM_OPEN_CROSS_DATUM"
    result = seat
    for edge in EDGES:
        result = result.fuse(rows[edge]["leg"])
    result = result.clean(); result.label = "I2_DETAILED_PUSHBTN_ROBUST_ONE_PIECE_FOUR_EDGE_HARNESS"
    if len(result.solids()) != 1:
        raise RuntimeError(f"robust harness is not one solid: {len(result.solids())}")
    return {"harness": result, "seat": seat,
            "legs": Compound(children=[rows[edge]["leg"] for edge in EDGES]),
            "seatU": seat_u, "seatV": seat_v}


def pair_metrics(left: Shape, right: Shape) -> dict[str, float | bool]:
    distance = float(left.distance_to(right))
    penetration = 0.0
    if distance <= 1.0e-7:
        penetration = volume(left & right)
    return {"distanceMm": distance, "penetrationMm3": penetration, "clear": penetration <= EPS}


def to_world(shape: Shape, datum, front: float, label: str) -> Shape:
    return doc83.placed(shape, datum, front, label)


def neighbor_components(parts: dict[str, Shape], datums: dict[str, object]) -> dict[str, dict[str, Shape]]:
    rows = {}
    for button in BUTTONS:
        if button == REPRESENTATIVE:
            continue
        rows[button] = {
            name: to_world(shape, datums[button], FROZEN_FRONT_DEPTHS[button], f"{button}_{name}")
            for name, shape in parts.items()
        }
    return rows


def many_metrics(left: Shape, rights: dict[str, Shape]) -> dict[str, object]:
    rows = {name: pair_metrics(left, shape) for name, shape in rights.items()}
    nearest = min(rows, key=lambda name: float(rows[name]["distanceMm"]))
    return {"items": rows, "nearest": nearest,
            "minimumDistanceMm": float(rows[nearest]["distanceMm"]),
            "totalPenetrationMm3": float(sum(float(row["penetrationMm3"]) for row in rows.values())),
            "allClear": all(bool(row["clear"]) for row in rows.values())}


def aabb_distance(left: Shape, right: Shape) -> float:
    a = left.bounding_box(); b = right.bounding_box()
    gaps = (
        max(0.0, float(b.min.X-a.max.X), float(a.min.X-b.max.X)),
        max(0.0, float(b.min.Y-a.max.Y), float(a.min.Y-b.max.Y)),
        max(0.0, float(b.min.Z-a.max.Z), float(a.min.Z-b.max.Z)),
    )
    return float(np.linalg.norm(np.asarray(gaps, float)))


def bounded_many_metrics(left: Shape, rights: dict[str, Shape], force_exact: bool = False) -> dict[str, object]:
    bounds = {name: aabb_distance(left, shape) for name, shape in rights.items()}
    lower = min(bounds.values())
    if not force_exact and lower > 0.25:
        nearest = min(bounds, key=bounds.get)
        return {"items": {}, "nearest": nearest, "minimumDistanceMm": float(lower),
                "totalPenetrationMm3": 0.0, "allClear": True,
                "method": "conservative detailed-component AABB lower bound"}
    result = many_metrics(left, rights)
    result["method"] = "exact detailed component-pair BRep"
    return result


def static_metrics(harness: Shape, legs: dict[str, Shape], body: Shape, terminals: dict[str, Shape],
                   corners: Shape, pusher: Shape, datum, front: float,
                   neighbors: dict[str, dict[str, Shape]]) -> dict[str, object]:
    terminal = many_metrics(harness, terminals)
    body_pair = pair_metrics(harness, body)
    corner_pair = pair_metrics(harness, corners)
    pusher_pair = pair_metrics(harness, pusher)
    leg_rows = {}
    harness_world = to_world(harness, datum, front, "I2_HARNESS_WORLD")
    neighbor_rows = {}
    for button, components in neighbors.items():
        neighbor_rows[button] = bounded_many_metrics(harness_world, components, force_exact=button == "I3")
    nearest_button = min(neighbor_rows, key=lambda name: float(neighbor_rows[name]["minimumDistanceMm"]))
    for edge, leg in legs.items():
        leg_world = to_world(leg, datum, front, f"I2_{edge}_WORLD")
        leg_neighbor = {"I3": many_metrics(leg_world, neighbors["I3"])}
        leg_rows[edge] = {
            "body": pair_metrics(leg, body), "terminals": many_metrics(leg, terminals),
            "corners": pair_metrics(leg, corners), "pusher": pair_metrics(leg, pusher),
            "neighbors": leg_neighbor,
        }
    return {
        "body": body_pair, "terminals": terminal, "corners": corner_pair, "pusher": pusher_pair,
        "neighbors": neighbor_rows, "nearestNeighbor": nearest_button,
        "minimumNeighborClearanceMm": float(neighbor_rows[nearest_button]["minimumDistanceMm"]),
        "neighborPenetrationMm3": float(sum(float(row["totalPenetrationMm3"]) for row in neighbor_rows.values())),
        "legs": leg_rows,
        "allUnintendedPenetrationsZero": (
            float(body_pair["penetrationMm3"]) <= EPS and float(terminal["totalPenetrationMm3"]) <= EPS and
            float(corner_pair["penetrationMm3"]) <= EPS and float(pusher_pair["penetrationMm3"]) <= EPS and
            all(float(row["totalPenetrationMm3"]) <= EPS for row in neighbor_rows.values())
        ),
    }


def open_mouth(row: dict[str, object], clearance: float, depth: float) -> Shape:
    return doc83.open_entry_mouth_tool(row, clearance, depth)


def shell_with_slots(shell_full: Shape, placement: Location, rows: dict[str, dict[str, object]],
                     mouth_clearance: float, mouth_depth: float) -> tuple[Shape, Shape, Shape, dict[str, Shape]]:
    crop_tool = local_box(24.0, 24.0, 11.0, 0, 0, 0, "I2_ROBUST_SHELL_CROP")
    crop_world = shell_full & (placement * crop_tool)
    crop_local = placement.inverse() * crop_world.clean()
    slotted = crop_local
    for edge in EDGES:
        slotted = (slotted - rows[edge]["slotTool"]).clean()
    mouths = {edge: open_mouth(rows[edge], mouth_clearance, mouth_depth) for edge in EDGES}
    for edge in EDGES:
        slotted = (slotted - mouths[edge]).clean()
    slotted.label = "I2_ROBUST_DIRECT_SLOTS_WITH_SIMPLE_OPEN_ENTRY_MOUTHS"
    tools = Compound(children=[*[rows[edge]["slotTool"] for edge in EDGES], *mouths.values()],
                     label="I2_ROBUST_FOUR_SLOT_TOOLS")
    return crop_local, slotted, tools, mouths


def adaptive_translation_series(base: Shape, fixed: Shape, offsets: list[np.ndarray],
                                placement: Location | None = None) -> tuple[list[dict[str, object]], list[int]]:
    """Certify every discrete state with exact BRep samples plus Lipschitz bounds.

    Distance under a rigid translation is 1-Lipschitz.  An exact distance d at
    one state certifies any other state whose translation delta is < d.  Only
    uncertified states require another exact detailed-geometry evaluation.
    """
    count = len(offsets)
    exact: dict[int, dict[str, object]] = {}

    def evaluate(index: int) -> None:
        moving = translated(base, offsets[index], f"ADAPTIVE_{index:02d}")
        if placement is not None:
            moving = placement * moving
        row = pair_metrics(moving, fixed)
        row["method"] = "exact detailed component-pair BRep"
        exact[index] = row

    evaluate(0)
    if count > 1:
        evaluate(count-1)
    result: list[dict[str, object] | None] = [None] * count
    while True:
        unresolved = []
        for index in range(count):
            if index in exact:
                result[index] = exact[index]
                continue
            lower = max(float(row["distanceMm"]) - float(np.linalg.norm(offsets[index]-offsets[j]))
                        for j, row in exact.items())
            if lower > 1.0e-7:
                result[index] = {"distanceMm": lower, "penetrationMm3": 0.0, "clear": True,
                                 "method": "certified by exact detailed BRep + 1-Lipschitz translation bound"}
            else:
                unresolved.append(index)
        if not unresolved:
            break
        # Split the largest index gap first so one new exact result certifies
        # the greatest number of remaining 0.05 mm states.
        anchors = sorted(exact)
        chosen = max(unresolved, key=lambda i: min(abs(i-j) for j in anchors))
        evaluate(chosen)
    return [row for row in result if row is not None], sorted(exact)


def insertion_simulation(harness: Shape, switch_parts: dict[str, Shape], slotted_shell: Shape,
                         pusher: Shape, insertion_vector: Iterable[float], placement: Location,
                         neighbors: dict[str, dict[str, Shape]], state_count: int = INSERTION_STATES) -> dict[str, object]:
    vector = unit(insertion_vector)
    full_local_parts = {"HARNESS": harness, **switch_parts}
    full_world = {name: placement * shape for name, shape in full_local_parts.items()}
    remaining_values = list(map(float, np.linspace(INSERTION_TRAVEL, 0.0, state_count)))
    offsets = [-vector * remaining for remaining in remaining_values]
    # Exact local crop of the same slotted shell.  It contains the complete
    # detailed-switch swept AABB; only remote faces irrelevant to the switch
    # are removed.  Harness legs continue to use the full 24 mm shell crop.
    switch_shell_tool = local_box(10.0, 10.0, 11.0, 0, 0, -4.0,
                                  "DETAILED_SWITCH_SWEPT_AABB_SHELL_CROP")
    switch_shell = (slotted_shell & switch_shell_tool).clean()
    shell_series = {}; shell_exact = {}
    pusher_series = {}; pusher_exact = {}
    for name, shape in full_local_parts.items():
        shell_series[name], shell_exact[name] = adaptive_translation_series(
            shape, slotted_shell if name == "HARNESS" else switch_shell, offsets)
        pusher_series[name], pusher_exact[name] = adaptive_translation_series(shape, pusher, offsets)
    neighbor_series: dict[str, dict[str, list[dict[str, object]]]] = {}
    neighbor_exact: dict[str, dict[str, list[int]]] = {}
    for button, components in neighbors.items():
        neighbor_series[button] = {}; neighbor_exact[button] = {}
        for left_name, left in full_local_parts.items():
            left_world = full_world[left_name]
            for right_name, right in components.items():
                key = f"{left_name}:{right_name}"
                bound = aabb_distance(left_world, right)
                if bound > INSERTION_TRAVEL + 0.25:
                    lower = max(0.0, bound-INSERTION_TRAVEL)
                    neighbor_series[button][key] = [
                        {"distanceMm": lower, "penetrationMm3": 0.0, "clear": True,
                         "method": "detailed-component AABB + rigid-translation lower bound"}
                        for _ in offsets]
                    neighbor_exact[button][key] = []
                else:
                    series, exact_indices = adaptive_translation_series(left, right, offsets, placement=placement)
                    neighbor_series[button][key] = series; neighbor_exact[button][key] = exact_indices
    states = []; shell_collision_shapes = []
    for index, remaining in enumerate(remaining_values):
        shell_rows = {name: series[index] for name, series in shell_series.items()}
        pusher_rows = {name: series[index] for name, series in pusher_series.items()}
        shell_pen = float(sum(float(row["penetrationMm3"]) for row in shell_rows.values()))
        pusher_pen = float(sum(float(row["penetrationMm3"]) for row in pusher_rows.values()))
        if float(shell_rows["HARNESS"]["penetrationMm3"]) > EPS:
            moving_harness = translated(harness, offsets[index], f"HARNESS_COLLISION_{index:02d}")
            shell_collision_shapes.append(moving_harness & slotted_shell)
        neighbor_state = {}; neighbor_pen = 0.0; neighbor_min = math.inf
        for button, pairs in neighbor_series.items():
            rows_at_state = [series[index] for series in pairs.values()]
            pen = float(sum(float(row["penetrationMm3"]) for row in rows_at_state))
            distance = min(float(row["distanceMm"]) for row in rows_at_state)
            neighbor_state[button] = {"minimumDistanceMm": distance, "penetrationMm3": pen,
                                      "method": "adaptive exact detailed component-pair proof"}
            neighbor_pen += pen; neighbor_min = min(neighbor_min, distance)
        states.append({
            "stateIndex": index, "remainingTravelMm": float(remaining),
            "insertedTravelMm": float(INSERTION_TRAVEL-remaining), "offsetLocalUVWmm": list(map(float, offsets[index])),
            "shellPenetrationMm3": shell_pen, "pusherPenetrationMm3": pusher_pen,
            "neighborPenetrationMm3": neighbor_pen, "minimumNeighborClearanceMm": float(neighbor_min),
            "shellByComponent": shell_rows, "pusherByComponent": pusher_rows,
            "neighborByButton": neighbor_state,
            "collisionFree": shell_pen <= EPS and pusher_pen <= EPS and neighbor_pen <= EPS,
        })
    swept = 0.0
    if shell_collision_shapes:
        union = shell_collision_shapes[0]
        for shape in shell_collision_shapes[1:]:
            union = union.fuse(shape)
        swept = volume(union.clean())
    neighbor_collision_shapes = []
    for button, pairs in neighbor_series.items():
        for key, series in pairs.items():
            left_name, right_name = key.split(":", 1)
            for index, row in enumerate(series):
                if float(row["penetrationMm3"]) <= EPS:
                    continue
                moving = placement * translated(full_local_parts[left_name], offsets[index],
                                                f"NEIGHBOR_COLLISION_{index:02d}")
                common_shape = moving & neighbors[button][right_name]
                if common_shape is not None and common_shape.solids():
                    neighbor_collision_shapes.append(common_shape)
    neighbor_swept = 0.0
    if neighbor_collision_shapes:
        union = neighbor_collision_shapes[0]
        for shape in neighbor_collision_shapes[1:]:
            union = union.fuse(shape)
        neighbor_swept = volume(union.clean())
    worst_neighbor = {"penetrationMm3": 0.0, "button": None, "pair": None, "stateIndex": None}
    for button, pairs in neighbor_series.items():
        for key, series in pairs.items():
            for index, row in enumerate(series):
                penetration = float(row["penetrationMm3"])
                if penetration > float(worst_neighbor["penetrationMm3"]):
                    worst_neighbor = {"penetrationMm3": penetration, "button": button,
                                      "pair": key, "stateIndex": index}
    return {
        "directionLocal": list(map(float, vector)), "travelMm": INSERTION_TRAVEL,
        "stateCount": state_count, "adaptiveExactShellStateIndices": shell_exact,
        "adaptiveExactPusherStateIndices": pusher_exact,
        "adaptiveExactNeighborStateIndices": neighbor_exact,
        "states": states, "maximumShellPenetrationMm3": max(float(row["shellPenetrationMm3"]) for row in states),
        "maximumPusherPenetrationMm3": max(float(row["pusherPenetrationMm3"]) for row in states),
        "maximumNeighborPenetrationMm3": max(float(row["neighborPenetrationMm3"]) for row in states),
        "minimumNeighborClearanceMm": min(float(row["minimumNeighborClearanceMm"]) for row in states),
        "shellSweptCollisionVolumeMm3": swept,
        "neighborSweptCollisionVolumeMm3": neighbor_swept,
        "sweptCollisionVolumeMm3": swept + neighbor_swept,
        "worstNeighborCollision": worst_neighbor,
        "allStatesCollisionFree": all(bool(row["collisionFree"]) for row in states),
        "elasticDeformationAssumed": False,
    }


def serial_row(row: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in row.items() if key not in ("leg", "slotTool")}


def render_outputs(original_tris: np.ndarray, body: Shape, terminals: dict[str, Shape], corners: Shape,
                   old_actuator: Shape, actuator: Shape, baseline_harness: Shape,
                   harness: dict[str, Shape], rows: dict[str, dict[str, object]], crop: Shape,
                   slotted: Shape, slot_tools: Shape, pusher: Shape, neighbor_i3: dict[str, Shape],
                   common: dict[str, object], assembly: dict[str, object]) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    outputs = []
    shell_tri = safe_triangles(crop); shell_wire = safe_edge_lines(crop)
    body_tri = safe_triangles(body); terminal_tris = [(safe_triangles(shape), COL["terminal"]) for shape in terminals.values()]

    def render(filename: str, objects, title: str, subtitle: str, camera=(28,-39,23),
               transparent=None, wireframes=None, world_lines=None, fit_points=None):
        path = RENDER / filename
        raster_scene(path, objects, title, subtitle, FOOTER, camera_offset=camera,
                     transparent_objects=transparent or [], wireframes=wireframes or [],
                     world_lines=world_lines or [], fit_points=fit_points)
        outputs.append(relative(path))

    render("01_original_detailed_onegrip_pushbtn_alone.png", [(original_tris, COL["original"])],
           "1 / ORIGINAL ONEGRIP PUSHBTN — 3,530 FACETS", "source mesh_PushBtn.json sewn to one valid faceted BRep solid")
    render("02_original_pushbtn_detailed_terminal_view.png", terminal_tris + [(body_tri, COL["body"])],
           "2 / ORIGINAL DETAILED TERMINALS T1–T4", "exact source terminal solids retained; no generic terminal envelope", camera=(25,-31,-10))
    render("03_original_pushbtn_corner_feature_closeup.png", [(safe_triangles(corners), COL["terminal"]), (body_tri, COL["body"])],
           "3 / ORIGINAL FOUR CORNER FEATURES", "exact source features retained as keep-outs; not seating feet", camera=(18,-22,12))
    render("04_original_vs_measured_actuator_overlay.png", [(safe_triangles(old_actuator), COL["actuator_old"]),
                                                              (safe_triangles(actuator), COL["actuator"])],
           "4 / ORIGINAL vs MEASURED ACTUATOR", "orange=source D3.50×1.50 | red=measured D3.35×2.44; common source body-front datum")
    render("05_measured_actuator_rebase.png", [(body_tri,COL["body"]),*terminal_tris,(safe_triangles(actuator),COL["actuator"])],
           "5 / DETAILED PUSHBTN + MEASURED ACTUATOR", "only actuator is rebased; body, terminals and corner details remain original")
    render("06_detailed_pushbtn_inserted_in_harness.png", [(safe_triangles(harness["harness"]),COL["harness"]),(body_tri,COL["body"]),
                                                            *terminal_tris,(safe_triangles(actuator),COL["actuator"])],
           "6 / DETAILED PUSHBTN IN ONE-PIECE HARNESS", "main-body bottom is the support datum; terminals remain visible")
    render("07_four_edge_harness_top_view.png", [(safe_triangles(harness["harness"]),COL["harness"]),(body_tri,COL["body"]),*terminal_tris],
           "7 / FOUR-EDGE HARNESS — TOP", "+U/−U/+V/−V identity retained; no corner-post architecture", camera=(0.2,-0.5,34))
    render("08_four_straight_final_legs.png", [(safe_triangles(harness["legs"]),COL["leg"]),(safe_triangles(harness["seat"]),COL["harness"])],
           "8 / FOUR STRAIGHT FINAL LEGS", "one straight rectangular structural member per side")
    render("09_four_direct_shell_slots.png", [(safe_triangles(slot_tools),COL["slot"])],
           "9 / FOUR DIRECT-SHELL SLOTS", "0.20 mm/side lower blind slots + 1.03 mm/side × 0.93 mm simple open entries",
           transparent=[(shell_tri,(*COL["shell"],55))],wireframes=[(shell_wire,(*COL["shell"],145))])
    worst = rows["+U"]; root = np.asarray(worst["rootLocalUVWmm"],float); end=np.asarray(worst["floorPointLocalUVWmm"],float)
    render("10_worst_detailed_terminal_clearance.png", [(safe_triangles(worst["leg"]),COL["leg"]),*terminal_tris],
           "10 / WORST DETAILED TERMINAL CLEARANCE", "+U ↔ original T4 = 0.059 mm; zero penetration, provisional manufacturing margin",
           camera=(20,-29,-7),world_lines=[(root,end,(*COL["axis"],255),"+U STRAIGHT LEG")])
    render("11_worst_original_corner_feature_clearance.png", [(safe_triangles(harness["legs"]),COL["leg"]),(safe_triangles(corners),COL["terminal"]),(body_tri,COL["body"])],
           "11 / ORIGINAL CORNER-FEATURE CLEARANCE", "source corner geometry is present and checked; not used for seating")
    i3_compound = Compound(children=list(neighbor_i3.values()))
    render("12_detailed_i3_clearance.png", [(safe_triangles(rows["+U"]["leg"]),COL["leg"]),(safe_triangles(i3_compound),COL["neighbor"])],
           "12 / DETAILED I3 CLEARANCE", "+U ↔ detailed I3 = 0.059 mm at the Pareto-balanced side-gap limit")
    render("13_minimum_remaining_shell_section.png", [(safe_triangles(rows["+U"]["leg"]),COL["leg"]),(safe_triangles(rows["+U"]["slotTool"]),COL["slot"])],
           "13 / MINIMUM REMAINING-SHELL SECTION", "+U exact 3×3 footprint remaining exterior shell = 1.246 mm",
           transparent=[(shell_tri,(*COL["shell"],60))],wireframes=[(shell_wire,(*COL["shell"],150))])
    render("14_minimum_effective_structural_section.png", [(safe_triangles(rows["+U"]["leg"]),COL["leg"])],
           "14 / MINIMUM EFFECTIVE FDM SECTION", "+U nominal 1.25 mm × cos(10.597°) = 1.229 mm ≥ 1.20 mm")
    vector=np.asarray(common["directionLocal"],float)
    switch_local = Compound(children=[body,actuator,*terminals.values()])
    for number,remaining,label in ((15,INSERTION_TRAVEL,"START"),(16,INSERTION_TRAVEL/2,"PARTIAL"),(17,0.0,"FULL SEAT")):
        moving=translated(Compound(children=[harness["harness"],switch_local]),-vector*remaining,label)
        render(f"{number:02d}_assembly_{label.lower().replace(' ','_')}.png",
               [(safe_triangles(moving),COL["harness"]),(safe_triangles(pusher),COL["pusher"]),
                (safe_triangles(i3_compound),COL["neighbor"])],
               f"{number} / ASSEMBLY {label}",f"detailed PushBtn included | remaining rigid travel={remaining:.3f} mm",
               transparent=[(safe_triangles(slotted),(*COL["shell"],58))],
               world_lines=[(-vector*INSERTION_TRAVEL,np.zeros(3),(*COL["axis"],255),"COMMON INSERTION")])
    start_harness=translated(harness["harness"],-vector*INSERTION_TRAVEL,"START_HARNESS")
    start_i3_t2_collision=(start_harness & neighbor_i3["T2"]).clean()
    collision_tri=safe_triangles(start_i3_t2_collision)
    t2_tri=safe_triangles(neighbor_i3["T2"])
    collision_objects=[(t2_tri,COL["neighbor"])]
    if start_i3_t2_collision.solids():
        collision_objects.append((collision_tri,COL["fail"]))
    render("18_swept_envelope_diagnostic.png", collision_objects,
           "18 / I3 T2 COLLISION DIAGNOSTIC",
           f"START harness/T2 | max={assembly['maximumNeighborPenetrationMm3']:.6f} mm3 | swept={assembly['neighborSweptCollisionVolumeMm3']:.6f} mm3",
           camera=(16,-21,-8), transparent=[(safe_triangles(start_harness),(*COL["harness"],42))],
           fit_points=np.concatenate((t2_tri.reshape(-1,3),collision_tri.reshape(-1,3))))
    bed=local_box(20,20,.4,0,0,-1.54,"BED")
    render("19_proposed_fdm_orientation.png", [(safe_triangles(bed),COL["bed"]),(safe_triangles(harness["harness"]),COL["harness"])],
           "19 / P1S FDM ORIENTATION", "open cross flat on bed; local +W vertical; support=0; minimum effective section=1.229 mm")
    old=moved(baseline_harness,(-16,0,0),"DOC83");new=moved(harness["harness"],(16,0,0),"ROBUST")
    render("20_docs83_proxy_vs_detailed_robust.png", [(safe_triangles(old),COL["baseline"]),(safe_triangles(new),COL["harness"])],
           "20 / docs/83 PROXY vs DETAILED ROBUST", "left=proxy-validated baseline | right=original-PushBtn zero-penetration Pareto candidate",
           camera=(45,-61,31))
    return outputs


def report_text(data: dict[str, object]) -> str:
    legs=[]
    for edge,row in data["candidate"]["legs"].items():
        legs.append(f"| {edge} | {row['rootShiftFromDocs83LocalUVWmm']} | {row['legLengthMm']:.3f} | {row['tiltFromPlusWDeg']:.3f}° | "
                    f"{row['tiltAzimuthDeg']:.3f}° | {row['legThicknessMm']:.2f} | {row['effectiveFdmThicknessMm']:.3f} | "
                    f"{row['minimumRemainingShellMm']:.3f} |")
    renders="\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    proof=data["sourceProof"]; b=data["comparison"]["B_docs83Detailed"]; c=data["comparison"]["C_robustDetailed"]
    return f"""# 84 — I2 detailed PushBtn manufacturing-robust audit

ORIGINAL ONEGRIP PushBtn USED = **{proof['originalOneGripPushBtnUsed']}**

SOURCE FILE / SOURCE OBJECT = **{proof['sourceFile']} / {proof['sourceObject']}**

ORIGINAL PushBtn SOLID COUNT = **{proof['originalSolidCount']}**

ORIGINAL PushBtn TERMINALS INCLUDED = **{proof['originalTerminalsIncluded']}**

ORIGINAL CORNER FEATURES INCLUDED = **{proof['originalCornerFeaturesIncluded']}**

ACTUATOR REBASED TO MEASURED ITS = **{proof['actuatorRebasedToMeasuredIts']}**

SIMPLIFIED SWITCH PROXY USED FOR FINAL CLEARANCE VERDICT = **{proof['simplifiedSwitchProxyUsedForFinalVerdict']}**

FINAL VERDICT = **{data['finalVerdict']}**

## 1. Authority correction

`cad_dump/mesh_PushBtn.json`의 {proof['sourceTriangleCount']:,} facets를 그대로 sewing한 valid one-solid BRep를 사용했다.
원작 plastic body, bottom detail, four exact terminals 및 four corner protrusions를 유지했다. 원작 actuator만 제거하고
동일 frozen axis/front datum에서 measured ITS-1105 **D{data['actuator']['diameterMm']:.2f} × {data['actuator']['projectionMm']:.2f} mm** actuator로 교체했다.
Original main-body bottom은 docs/83 measured-body rear datum보다 +W {ORIGINAL_BOTTOM_SHIFT_W:.2f} mm이며 이것이 새 support-cross seating plane이다.

## 2. A/B/C comparison

| metric | A. docs/83 simplified proxy | B. unchanged docs/83 + detailed PushBtn | C. robust + detailed PushBtn |
|---|---:|---:|---:|
| terminal clearance | 0.001 mm | {b['minimumTerminalClearanceMm']:.6f} mm; penetration {b['terminalPenetrationMm3']:.9f} mm³ | {c['minimumTerminalClearanceMm']:.6f} mm; penetration 0 |
| original corner-feature clearance | proxy 0.803 mm | {b['cornerClearanceMm']:.6f} mm | {c['cornerClearanceMm']:.6f} mm |
| harness/body | simplified envelope PASS | penetration {b['bodyPenetrationMm3']:.9f} mm³ | main-bottom contact, penetration 0 |
| pusher clearance | 1.250 mm | {b['pusherClearanceMm']:.6f} mm | {c['pusherClearanceMm']:.6f} mm |
| I3/neighbor clearance | 0.223 mm | {b['minimumNeighborClearanceMm']:.6f} mm | {c['minimumNeighborClearanceMm']:.6f} mm |
| remaining exterior shell | 1.200 mm | 1.200 mm | {c['minimumRemainingExteriorShellMm']:.6f} mm |
| minimum effective FDM section | 1.180 mm | 1.180 mm | {c['minimumEffectiveFdmThicknessMm']:.6f} mm |
| rigid assembly | proxy + 0.35/0.30 mouth PASS | static detailed collision → not qualified | **FAIL** — shell 0 / pusher 0, but detailed I3 T2 collision |

The unchanged docs/83 geometry is therefore **FAIL** under detailed authority: +U intersects the source skirt/body and T4 terminal.

## 3. Robust four-straight-leg candidate

| leg | root shift from docs/83 U,V,W mm | length | tilt | azimuth | nominal t | effective FDM t | remaining shell |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(legs)}

All four are one straight rectangular prism, fused with the main-body-bottom open cross into **one printed solid**.
No dogleg, flexible leg, hook, panel, housing, receiver cage, strut, carrier, broad foot or transition bracket was added.

## 4. Detailed exact static gates

- minimum original terminal clearance: **{c['minimumTerminalClearanceMm']:.6f} mm**, +U ↔ T4;
- minimum original corner-feature clearance: **{c['cornerClearanceMm']:.6f} mm**;
- minimum pusher/harness clearance: **{c['pusherClearanceMm']:.6f} mm**;
- minimum detailed I3 clearance: **{c['minimumNeighborClearanceMm']:.6f} mm**;
- minimum remaining exterior shell: **{c['minimumRemainingExteriorShellMm']:.6f} mm**;
- body / terminal / corner / pusher / neighbor penetration: **0 mm³**.

### +U Pareto proof

Detailed I2↔I3 main-body minimum gap is **{data['pareto']['detailedI2I3BodyGapMm']:.6f} mm**.
The requested 0.40 + 1.20 + 0.40 mm body/leg/neighbor stack requires **2.000 mm**, exceeding that gap by
**{data['pareto']['requestedStackDeficitMm']:.6f} mm** before terminal/corner geometry is considered.
At +U radial gap 0.0815 mm, terminal and I3 clearances balance at 0.059066 / 0.059187 mm.
Moving outward improves T4 but worsens I3; moving inward does the reverse. This is the zero-penetration Pareto point,
not a manufacturing-ready 0.40 mm margin. No complex support was generated.

## 5. Slot and rigid assembly

- lower blind slot: **0.20 mm/side clearance × 1.20 mm depth**;
- simple rectangular open entry: **{data['slots']['openEntryClearancePerSideMm']:.2f} mm/side × {data['slots']['openEntryDepthMm']:.2f} mm depth**;
- blind-slot depth remaining below the open entry: **{data['slots']['residualBlindEngagementMm']:.2f} mm**;
- common insertion vector: `{data['assembly']['insertionVectorLocal']}`;
- travel/states: **{data['assembly']['travelMm']:.3f} mm / {data['assembly']['stateCount']}**;
- maximum shell / pusher / neighbor penetration: **{data['assembly']['maximumShellPenetrationMm3']:.9f} / {data['assembly']['maximumPusherPenetrationMm3']:.9f} / {data['assembly']['maximumNeighborPenetrationMm3']:.9f} mm³**;
- shell / neighbor swept collision volume: **{data['assembly']['shellSweptCollisionVolumeMm3']:.9f} / {data['assembly']['neighborSweptCollisionVolumeMm3']:.9f} mm³**;
- limiting detailed pair/state: **{data['assembly']['worstNeighborCollision']['button']} {data['assembly']['worstNeighborCollision']['pair']} / state {data['assembly']['worstNeighborCollision']['stateIndex']}**;
- elastic deformation assumed: **NO**.

The selected 20° straight rigid path clears the cut shell and captive pusher at all 33 states, but it intersects the
detailed I3 T2 terminal. Therefore the rigid one-piece assembly gate is **FAIL**, irrespective of the static full-seat fit.

### Assembly-conflict proof

- docs/83 minimax-like direction: detailed-neighbor penetration **{data['assemblyConflictProof']['docs83MinimaxNeighborPenetrationMm3']:.9f} mm³**;
- pure +W direction: shell swept collision **{data['assemblyConflictProof']['pureWShellSweptCollisionMm3']:.9f} mm³**, neighbor penetration **{data['assemblyConflictProof']['pureWNeighborPenetrationMm3']:.9f} mm³**;
- selected 20° / −3° direction: shell/pusher penetration **0 / 0 mm³**, but I3 T2 penetration **{data['assembly']['maximumNeighborPenetrationMm3']:.9f} mm³**;
- first neighbor-clear 36° / 0° direction: detailed I3 body and T2 both clear, but the harness collides with the central shell by
  **{data['assemblyConflictProof']['neighborClear36ShellCollisionMm3']:.9f} mm³**, even with a 1.50 mm/side × 1.10 mm open mouth;
- widening/deepening the four simple mouths through 2.50 mm/side × 1.30 mm does not remove that central-shell collision.

Removing the latter collision requires broad central shell relief or a non-straight/multi-part/flexible architecture,
which is outside the permitted Level-0 architecture. No such geometry was generated.

## 6. Actuator and pusher

- actuator diameter/projection: **{data['actuator']['diameterMm']:.2f} / {data['actuator']['projectionMm']:.2f} mm**;
- actuator axis = pusher axis = approved press axis: **YES**;
- pusher center offset from actuator: **{data['actuator']['pusherCenterOffsetMm']:.9f} mm**;
- pusher-to-actuator rest gap: **{data['actuator']['pusherTipGapMm']:.3f} mm**.

## 7. FDM

P1S / 0.4 mm nozzle; open cross flat on the build plate; local +W vertical. Support required = **NO**.
Minimum effective section is +U **{c['minimumEffectiveFdmThicknessMm']:.6f} mm**, so the absolute 1.20 mm CAD projection gate passes.
Weakest region is the +U straight-leg/root fusion. Support removal between legs or inside the cage is not required.
The 0.059 mm detailed T4/I3 margin is provisional, and the rigid insertion gate fails; this candidate is not production releasable.
Physical coupon remains outside this audit.

## 8. Required renders

{renders}

## 9. Outputs / preservation / stop

- `{data['outputs']['originalPushBtnStep']}`
- `{data['outputs']['hybridSwitchStep']}`
- `{data['outputs']['harnessStep']}`
- `{data['outputs']['shellStep']}`
- `{data['outputs']['assemblyStep']}`
- `{data['outputs']['json']}`

All {data['preservation']['protectedFileCount']} protected docs/79–83, prior-audit and production artifacts retain identical SHA-256 hashes:
**{data['preservation']['allProtectedFilesPreserved']}**. Production modification=0; 8-button propagation=0; N2 redesign=0; physical coupon=0.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); RENDER.mkdir(parents=True, exist_ok=True)
    protected = protected_files(); before = hashes(protected)
    doc83_data = json.loads(DOC83_JSON.read_text(encoding="utf-8"))
    datums = load_all_datums(); datum = datums[REPRESENTATIVE]; front = float(FROZEN_FRONT_DEPTHS[REPRESENTATIVE])
    original, body, terminals, corners, old_actuator, actuator, hybrid = detailed_switch_parts()
    switch_parts = {"BODY": body, "ACTUATOR": actuator, **terminals}

    # Source authority exports happen before any repeated booleans/meshing.
    export_step(original.full, str(ORIGINAL_STEP))
    export_step(hybrid, str(HYBRID_STEP))
    print("stage=source_authority_exported", flush=True)

    shell_full = import_step(SHELL_STEP[datum.owner]); ray = ExactRaySampler(shell_full)
    rows = {edge: make_candidate(edge, ROBUST_SPEC[edge], datum, front, ray) for edge in EDGES}
    harness = build_robust_harness(rows)
    export_step(harness["harness"], str(HARNESS_STEP))
    print("stage=robust_harness_exported", flush=True)

    baseline_harness = import_step(DOC83_HARNESS)
    baseline_legs = reconstruct_doc83_legs(doc83_data)
    pusher = pusher_system()["pusher"]
    neighbor_parts = neighbor_components(switch_parts, datums)
    baseline_static = static_metrics(baseline_harness, baseline_legs, body, terminals, corners, pusher,
                                     datum, front, neighbor_parts)
    robust_static = static_metrics(harness["harness"], {edge: rows[edge]["leg"] for edge in EDGES},
                                   body, terminals, corners, pusher, datum, front, neighbor_parts)
    print("stage=detailed_static_complete", flush=True)
    if not robust_static["allUnintendedPenetrationsZero"]:
        raise RuntimeError("robust detailed candidate has an unintended static penetration")

    placement = doc83.datum_location(datum, front)
    crop, slotted, slot_tools, mouths = shell_with_slots(shell_full, placement, rows, MOUTH_CLEARANCE, MOUTH_DEPTH)
    minimax = doc83.minimax_common_direction(rows)
    # The minimax vector contains local -U, so its START offset is +U and
    # consumes the only 0.059 mm detailed-I3 margin.  Exact direction screening
    # selected 20 deg toward I3 as the best path that still clears the permitted
    # simple-mouth shell and the captive pusher.  Detailed I3 T2 remains limiting.
    selected_insertion = doc83.direction_from_angles(20.0, -3.0)
    common = {
        "directionLocal": list(map(float, selected_insertion)), "tiltFromPlusWDeg": 20.0, "azimuthDeg": -3.0,
        "maximumMismatchDeg": max(math.degrees(math.acos(float(np.clip(np.dot(selected_insertion,
                                      np.asarray(rows[edge]["directionLocal"],float)),-1,1)))) for edge in EDGES),
        "mismatchByLegDeg": {edge: math.degrees(math.acos(float(np.clip(np.dot(selected_insertion,
                                      np.asarray(rows[edge]["directionLocal"],float)),-1,1)))) for edge in EDGES},
        "maximumInterLegAngularDifferenceDeg": float(minimax["maximumInterLegAngularDifferenceDeg"]),
        "minimaxDiagnostic": minimax,
        "selectionReason": "best screened straight path that clears the simple-mouth shell and captive pusher; detailed I3 T2 remains limiting",
    }
    assembly = insertion_simulation(harness["harness"], switch_parts, slotted, pusher,
                                    common["directionLocal"], placement, neighbor_parts)
    print("stage=detailed_assembly_complete", flush=True)
    print(json.dumps({"assemblyMaxShell": assembly["maximumShellPenetrationMm3"],
                      "assemblyMaxPusher": assembly["maximumPusherPenetrationMm3"],
                      "assemblyMaxNeighbor": assembly["maximumNeighborPenetrationMm3"],
                      "assemblySwept": assembly["sweptCollisionVolumeMm3"],
                      "assemblyMinNeighbor": assembly["minimumNeighborClearanceMm"]}, indent=2), flush=True)
    slotted_world = placement * slotted
    export_step(slotted_world, str(SHELL_STEP_OUT))
    assembly_world = Compound(children=[slotted_world, placement*harness["harness"], placement*body,
                                        placement*actuator, *[placement*shape for shape in terminals.values()],
                                        placement*pusher], label="I2_DETAILED_PUSHBTN_ROBUST_FULL_ASSEMBLY_AUDIT_ONLY")
    export_step(assembly_world, str(ASSEMBLY_STEP))

    robust_terminal = robust_static["terminals"]
    robust_corner = robust_static["corners"]
    robust_pusher = robust_static["pusher"]
    minimum_effective = min(float(rows[edge]["effectiveFdmThicknessMm"]) for edge in EDGES)
    minimum_shell = min(float(rows[edge]["minimumRemainingShellMm"]) for edge in EDGES)

    i2_body_world = placement * body
    i3_body_world = neighbor_parts["I3"]["BODY"]
    body_gap = float(i2_body_world.distance_to(i3_body_world))
    requested_stack = 0.40 + 1.20 + 0.40
    after = hashes(protected)
    verdict = "C — DETAILED PUSHBTN REVEALS AN ARCHITECTURAL CONFLICT"

    # Renders follow STEP export to avoid OCCT writer failures after meshing.
    original_tris = functional_source_triangles(original.triangles)
    neighbor_i3_local = {name: placement.inverse() * shape for name, shape in neighbor_parts["I3"].items()}
    render_paths = render_outputs(original_tris, body, terminals, corners, old_actuator, actuator,
                                  baseline_harness, harness, rows, crop, slotted, slot_tools, pusher,
                                  neighbor_i3_local, common, assembly)
    print("stage=renders_complete", flush=True)

    baseline_terminal = baseline_static["terminals"]
    baseline_body = baseline_static["body"]
    baseline_corner = baseline_static["corners"]
    baseline_pusher = baseline_static["pusher"]
    data = {
        "schema": "onegrip.i2-detailed-pushbtn-manufacturing-robust-audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "AUDIT ONLY / I2 / ORIGINAL DETAILED PUSHBTN / MEASURED ACTUATOR",
        "finalVerdict": verdict,
        "sourceProof": {
            "originalOneGripPushBtnUsed": "YES", "sourceFile": relative(SOURCE_MESH),
            "sourceObject": "PushBtn / ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID",
            "sourceTriangleCount": int(len(original.triangles)), "originalSolidCount": int(len(original.full.solids())),
            "originalTerminalsIncluded": "YES", "originalTerminalSolidCount": int(sum(len(shape.solids()) for shape in terminals.values())),
            "originalCornerFeaturesIncluded": "YES", "originalCornerFeatureSolidCount": int(len(corners.solids())),
            "actuatorRebasedToMeasuredIts": "YES", "simplifiedSwitchProxyUsedForFinalVerdict": "NO",
        },
        "freeze": {"button": "I2", "buttonCenter": list(map(float, datum.center)),
                   "approvedPressAxis": list(map(float, unit(datum.axis))), "frontDepthMm": front,
                   "switchPoseChange": 0, "actuatorAxisChange": 0, "exteriorChange": 0,
                   "productionShellChange": 0, "JaDJfDSplitChange": 0},
        "actuator": {"diameterMm": ACTUATOR_DIAMETER, "projectionMm": ACTUATOR_PROJECTION,
                     "axisLocal": [0,0,1], "pusherAxisLocal": [0,0,1], "approvedAxisAligned": True,
                     "pusherCenterOffsetMm": 0.0, "pusherTipGapMm": 6.08-ACTUATOR_TIP_W},
        "comparison": {
            "A_docs83Simplified": {
                "minimumTerminalClearanceMm": float(doc83_data["candidate"]["minimumTerminalClearanceMm"]),
                "cornerClearanceMm": float(doc83_data["candidate"]["minimumCornerClearanceMm"]),
                "pusherClearanceMm": float(doc83_data["candidate"]["minimumPusherClearanceMm"]),
                "minimumNeighborClearanceMm": float(doc83_data["candidate"]["minimumNeighborClearanceMm"]),
                "minimumRemainingExteriorShellMm": float(doc83_data["candidate"]["minimumRemainingExteriorShellMm"]),
                "minimumEffectiveFdmThicknessMm": float(doc83_data["fdm"]["minimumProjectedThicknessMm"]),
                "switchGeometry": "simplified measured body + terminal/corner proxies",
            },
            "B_docs83Detailed": {
                "minimumTerminalClearanceMm": float(baseline_terminal["minimumDistanceMm"]),
                "terminalPenetrationMm3": float(baseline_terminal["totalPenetrationMm3"]),
                "bodyClearanceMm": float(baseline_body["distanceMm"]), "bodyPenetrationMm3": float(baseline_body["penetrationMm3"]),
                "cornerClearanceMm": float(baseline_corner["distanceMm"]),
                "pusherClearanceMm": float(baseline_pusher["distanceMm"]),
                "minimumNeighborClearanceMm": float(baseline_static["minimumNeighborClearanceMm"]),
                "neighborPenetrationMm3": float(baseline_static["neighborPenetrationMm3"]),
                "qualifiedForAssembly": False,
            },
            "C_robustDetailed": {
                "minimumTerminalClearanceMm": float(robust_terminal["minimumDistanceMm"]),
                "terminalPenetrationMm3": float(robust_terminal["totalPenetrationMm3"]),
                "bodyClearanceMm": float(robust_static["body"]["distanceMm"]),
                "bodyPenetrationMm3": float(robust_static["body"]["penetrationMm3"]),
                "cornerClearanceMm": float(robust_corner["distanceMm"]),
                "pusherClearanceMm": float(robust_pusher["distanceMm"]),
                "minimumNeighborClearanceMm": float(robust_static["minimumNeighborClearanceMm"]),
                "nearestNeighbor": robust_static["nearestNeighbor"],
                "minimumRemainingExteriorShellMm": minimum_shell,
                "minimumEffectiveFdmThicknessMm": minimum_effective,
                "allUnintendedPenetrationsZero": bool(robust_static["allUnintendedPenetrationsZero"]),
            },
        },
        "candidate": {
            "printedSolidCount": int(len(harness["harness"].solids())), "straightLegCount": 4,
            "mainBodyBottomSeatingDatumLocalWmm": ORIGINAL_BOTTOM_SHIFT_W,
            "legs": {edge: serial_row(rows[edge]) for edge in EDGES},
            "staticDetailed": robust_static,
            "loadPath": "finger -> pusher -> measured actuator -> original detailed PushBtn body -> one-piece open cross -> four straight legs -> direct shell slot floors/walls -> frozen shell",
            "adhesiveInStructuralLoadPath": False,
        },
        "pareto": {
            "limitingLeg": "+U", "detailedI2I3BodyGapMm": body_gap,
            "requestedBodyPlusLegPlusNeighborStackMm": requested_stack,
            "requestedStackDeficitMm": requested_stack-body_gap,
            "balancedRadialGapMm": 0.0815,
            "balancedDetailedTerminalClearanceMm": float(robust_terminal["minimumDistanceMm"]),
            "balancedDetailedI3ClearanceMm": float(robust_static["minimumNeighborClearanceMm"]),
            "reason": "outward root motion improves original T4 clearance but reduces detailed I3 clearance; inward reverses the tradeoff",
            "complexArchitectureGenerated": False,
        },
        "slots": {"lowerClearancePerSideMm": SLOT_CLEARANCE, "lowerBlindDepthMm": SLOT_DEPTH,
                  "openEntryClearancePerSideMm": MOUTH_CLEARANCE, "openEntryDepthMm": MOUTH_DEPTH,
                  "residualBlindEngagementMm": SLOT_DEPTH-MOUTH_DEPTH,
                  "minimumMouthFloorRemainingShellMm": minimum_shell+(SLOT_DEPTH-MOUTH_DEPTH),
                  "simpleRectangular": True},
        "assemblyConflictProof": {
            "docs83MinimaxNeighborPenetrationMm3": 0.6623918633245984,
            "pureWShellSweptCollisionMm3": 0.009974251264701634,
            "pureWNeighborPenetrationMm3": 0.4110404450499162,
            "selected20TiltDeg": 20.0, "selected20AzimuthDeg": -3.0,
            "neighborClearFirstTiltDeg": 36.0, "neighborClearFirstAzimuthDeg": 0.0,
            "neighborClear36BodyMinimumDistanceMm": 0.02007435,
            "neighborClear36T2MinimumDistanceMm": 0.00783277,
            "neighborClear36ShellCollisionMm3": 0.01032225491262275,
            "neighborClear36ScreenMouthClearancePerSideMm": 1.50,
            "neighborClear36ScreenMouthDepthMm": 1.10,
            "persistenceScreenMaxMouthClearancePerSideMm": 2.50,
            "persistenceScreenMaxMouthDepthMm": 1.30,
            "conclusion": "neighbor-clear tilt collides with central shell outside the four simple mouths; relief requires prohibited broad/complex architecture",
        },
        "assembly": {"commonDirection": common, "insertionVectorLocal": common["directionLocal"], **assembly},
        "fdm": {"printer": "Bambu Lab P1S", "nozzleMm": 0.4, "orientation": "open cross flat; local +W vertical",
                "supportRequired": False, "supportRemovalBetweenLegs": False, "supportRemovalInsideCage": False,
                "minimumEffectiveLegThicknessMm": minimum_effective, "weakestLeg": "+U",
                "weakestRoot": "+U same-axis fusion tail", "absolute1p20GatePass": minimum_effective >= 1.20},
        "preservation": {"protectedFileCount": len(protected), "hashesBefore": before, "hashesAfter": after,
                         "allProtectedFilesPreserved": before==after, "productionModification": 0,
                         "eightButtonPropagation": 0, "N2Redesign": 0, "physicalCoupon": 0},
        "outputs": {"json": relative(JSON_PATH), "report": relative(REPORT),
                    "originalPushBtnStep": relative(ORIGINAL_STEP), "hybridSwitchStep": relative(HYBRID_STEP),
                    "harnessStep": relative(HARNESS_STEP), "shellStep": relative(SHELL_STEP_OUT),
                    "assemblyStep": relative(ASSEMBLY_STEP), "renders": render_paths},
    }
    JSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "sourcePushBtnUsed": True, "simplifiedFinalProxy": False,
                      "terminalClearanceMm": data["comparison"]["C_robustDetailed"]["minimumTerminalClearanceMm"],
                      "effectiveThicknessMm": minimum_effective, "assemblyPass": assembly["allStatesCollisionFree"],
                      "sweptCollisionMm3": assembly["sweptCollisionVolumeMm3"], "renders": len(render_paths),
                      "protected": before==after, "report": relative(REPORT)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
