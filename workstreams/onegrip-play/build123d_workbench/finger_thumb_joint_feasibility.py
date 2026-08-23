"""Local feasibility branch for frozen Finger V2 exterior + max-lowered thumb.

Production Finger V2 and the physical-validation kit are immutable inputs.
All geometry created here is an isolated prototype or analysis envelope.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
from build123d import (
    Align,
    Box,
    BuildPart,
    Compound,
    Cylinder,
    Location,
    Plane,
    Shape,
    Vector,
    export_step,
    export_stl,
    import_step,
    import_stl,
)

from .finger_controls_v2 import (
    BUTTON_ORDER,
    CARRIER_WALL,
    FROZEN_FRONT_DEPTHS,
    SIDE_ACCESS_EXTRA,
    SWITCH_BODY_H,
    SWITCH_BODY_X,
    SWITCH_BODY_Y,
    SWITCH_POCKET_X,
    SWITCH_POCKET_Y,
    TERMINAL_ROOT_OUTER,
    TERMINAL_ROOT_PITCH,
    ControlDatum,
    build_finger_controls_v2,
    exact_distance,
    intersection_volume,
    oriented_box,
    oriented_box_between,
    point_at,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    trim_carrier_to_split,
    unit,
    wire_envelope,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_joint_feasibility"
ASSEMBLY_STEP = ROOT / "lower_adapter" / "local_cad" / "reference" / "ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step"
LOWER_JAD_STL = ROOT / "exports" / "thumb_lower15_housing_mockup" / "OneGrip_lower15_housing_Joystick_1_JaD.stl"
LOWER_JFD_STL = ROOT / "exports" / "thumb_lower15_housing_mockup" / "OneGrip_lower15_housing_Joystick_2_JfD.stl"
TARGET = np.asarray((0.0, 12.25, -21.0), dtype=float)

MIN_WALL = 1.20
PREFERRED_WALL = 1.60
MIN_SWITCH_SEPARATION = 1.20
MIN_SCREW_CLEARANCE = 2.50
ROBUST_CLEARANCE = 0.80
BOOLEAN_EPS = 1.0e-7
_DISTANCE_CACHE: dict[tuple[int, int], float] = {}
_INTERSECTION_CACHE: dict[tuple[int, int], float] = {}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def moved(shape: Shape, delta: Iterable[float]) -> Shape:
    return shape.moved(Location(Vector(*[float(value) for value in delta])))


def safe_distance(left: Shape, right: Shape) -> float:
    key = tuple(sorted((id(left), id(right))))
    if key in _DISTANCE_CACHE:
        return _DISTANCE_CACHE[key]
    try:
        value = exact_distance(left, right)
    except Exception:
        rows = [exact_distance(a, b) for a in left.solids() for b in right.solids()]
        value = min(rows) if rows else float("inf")
    _DISTANCE_CACHE[key] = value
    return value


def cached_intersection(left: Shape, right: Shape) -> float:
    key = tuple(sorted((id(left), id(right))))
    if key not in _INTERSECTION_CACHE:
        _INTERSECTION_CACHE[key] = intersection_volume(left, right)
    return _INTERSECTION_CACHE[key]


def bbox_gap(left: Shape, right: Shape) -> float:
    a = left.bounding_box()
    b = right.bounding_box()
    gaps = (
        max(float(a.min.X - b.max.X), float(b.min.X - a.max.X), 0.0),
        max(float(a.min.Y - b.max.Y), float(b.min.Y - a.max.Y), 0.0),
        max(float(a.min.Z - b.max.Z), float(b.min.Z - a.max.Z), 0.0),
    )
    return float(np.linalg.norm(gaps))


def fast_minimum_distance(left: list[Shape], right: list[Shape]) -> float:
    """Exact pair distance with AABB lower-bound pruning.

    This returns the same minimum as a monolithic Compound distance but avoids
    asking OCCT to retain every pair in memory at once.
    """
    pairs = sorted(
        ((bbox_gap(a, b), a, b) for a in left for b in right),
        key=lambda row: row[0],
    )
    best = float("inf")
    for lower, a, b in pairs:
        if lower >= best:
            break
        best = min(best, safe_distance(a, b))
        if best <= 1.0e-9:
            return 0.0
    return best


def list_metrics(left: list[Shape], right: list[Shape]) -> dict[str, float]:
    minimum = fast_minimum_distance(left, right)
    pairs = sorted(
        ((bbox_gap(a, b), a, b) for a in left for b in right),
        key=lambda row: row[0],
    )
    touching_pairs = []
    if minimum <= 1.0e-8:
        touching_pairs = [
            (a, b) for lower, a, b in pairs
            if lower <= 1.0e-9 and safe_distance(a, b) <= 1.0e-8
        ]
    volumes = [cached_intersection(a, b) for a, b in touching_pairs]
    return {
        "minimumClearanceMm": minimum,
        "penetrationVolumeMm3": float(sum(volumes)),
        "intersectingPairCount": int(sum(value > BOOLEAN_EPS for value in volumes)),
    }


def distance_only_metrics(left: list[Shape], right: list[Shape], note: str) -> dict[str, object]:
    return {
        "minimumClearanceMm": fast_minimum_distance(left, right),
        "aabbOverlapPairCount": sum(bbox_gap(a, b) <= 1.0e-9 for a in left for b in right),
        "penetrationVolumeMm3": None,
        "note": note,
    }


def shape_metrics(shape: Shape) -> dict[str, object]:
    bbox = shape.bounding_box()
    return {
        "valid": bool(shape.is_valid),
        "solids": len(shape.solids()),
        "volumeMm3": float(shape.volume),
        "bboxMm": {
            "min": [float(bbox.min.X), float(bbox.min.Y), float(bbox.min.Z)],
            "max": [float(bbox.max.X), float(bbox.max.Y), float(bbox.max.Z)],
        },
    }


def load_joystick_assembly_local() -> dict[str, list[Shape]]:
    assembly = import_step(ASSEMBLY_STEP)
    joystick = next(child for child in assembly.children if child.label.startswith("Joystick_"))
    jad = next(child for child in joystick.children if child.label == "Joystick_1")
    assembly_to_part_studio = jad.location.inverse()

    groups: dict[str, list[Shape]] = {
        "backplate": [],
        "thumbCaps": [],
        "pushButtons": [],
        "joystickMechanism": [],
        "smallAttachment": [],
        "screws": [],
        "assemblyShells": [],
    }
    for child in joystick.children:
        local = child.moved(assembly_to_part_studio)
        if child.label == "Backplate":
            groups["backplate"].append(local)
        elif child.label.startswith("Button_"):
            groups["thumbCaps"].append(local)
        elif child.label == "PushBtn":
            groups["pushButtons"].append(local)
        elif child.label == "HW504_B":
            groups["joystickMechanism"].append(local)
        elif child.label == "Small_joystick_attachment":
            groups["smallAttachment"].append(local)
        elif child.label.startswith("Hex_socket_head_cap_screw"):
            groups["screws"].append(local)
        elif child.label in ("Joystick_1", "Joystick_2"):
            groups["assemblyShells"].append(local)
    return groups


def target_thumb(groups: dict[str, list[Shape]], fraction: float = 1.0) -> dict[str, list[Shape]]:
    delta = TARGET * float(fraction)
    return {
        key: [moved(shape, delta) for shape in rows]
        for key, rows in groups.items()
        if key not in ("screws", "assemblyShells")
    }


def current_carrier_for_button(design, name: str) -> Shape:
    if name in ("N1", "N2"):
        return design.carriers["N1_N2_shared_carrier"]
    if name in ("I2", "I3"):
        return design.carriers["I2_I3_shared_carrier"]
    if name in ("M4", "N3"):
        return design.carriers["M4_N3_shared_carrier"]
    return design.carriers[f"{name}_carrier"]


def finger_envelopes(design, depths: dict[str, float] | None = None) -> dict[str, dict[str, list[Shape]]]:
    depths = dict(design.front_depths if depths is None else depths)
    controls = {row.name: row for row in design.controls}
    result: dict[str, dict[str, list[Shape]]] = {}
    for name in BUTTON_ORDER:
        datum = controls[name]
        result[name] = {
            "switchBody": [switch_body(datum, depths[name])],
            "actuator": [switch_actuator(datum, depths[name])],
            "terminalRoots": list(terminal_root_cutters(datum, depths[name])),
            "wire": [wire_envelope(datum, depths[name])],
            "currentCarrier": [current_carrier_for_button(design, name)],
            "cap": [design.caps[name]],
        }
    return result


def flatten_thumb(thumb: dict[str, list[Shape]]) -> list[Shape]:
    return [shape for rows in thumb.values() for shape in rows]


def build_low_profile_carrier(datum: ControlDatum, front_depth: float) -> Shape:
    """Three-sided individual collar without a rear plate or pair bridge."""
    rear = front_depth + SWITCH_BODY_H
    outer = oriented_box(
        datum,
        SWITCH_POCKET_X + 2.0 * PREFERRED_WALL,
        SWITCH_POCKET_Y + 2.0 * PREFERRED_WALL,
        front_depth - 0.20,
        rear + 0.35,
        label=f"{datum.name}_joint_low_profile_outer",
    )
    pocket = oriented_box(
        datum,
        SWITCH_POCKET_X,
        SWITCH_POCKET_Y,
        front_depth - 0.40,
        rear + 0.45,
        label=f"{datum.name}_joint_pocket",
    )
    access_width = PREFERRED_WALL + SIDE_ACCESS_EXTRA
    access_offset = datum.open_side_sign * (SWITCH_POCKET_X / 2.0 + PREFERRED_WALL / 2.0)
    access = oriented_box(
        datum,
        access_width,
        SWITCH_POCKET_Y + 2.0 * SIDE_ACCESS_EXTRA,
        front_depth - 0.45,
        rear + 0.50,
        u_offset=access_offset,
        label=f"{datum.name}_joint_lateral_access",
    )
    result = outer - pocket - access
    for cutter in terminal_root_cutters(datum, front_depth):
        result = result - cutter
    result = result.clean()
    if datum.name == "N2":
        result = trim_carrier_to_split(result, "JfD")
    result.label = f"{datum.name}_low_profile_individual_carrier"
    return result


def tangent_directions(datum: ControlDatum) -> list[np.ndarray]:
    axis = unit(datum.axis)
    down = np.asarray((0.0, 0.0, -1.0), dtype=float)
    projected_down = down - axis * float(np.dot(down, axis))
    if np.linalg.norm(projected_down) < 1.0e-8:
        projected_down = np.asarray(datum.switch_v, dtype=float)
    rows = [
        unit(projected_down),
        unit(datum.switch_u),
        -unit(datum.switch_u),
        unit(datum.switch_v),
        -unit(datum.switch_v),
    ]
    unique: list[np.ndarray] = []
    for row in rows:
        if not any(abs(float(np.dot(row, old))) > 0.9999 for old in unique):
            unique.append(row)
    return unique


def build_formed_wiring(datum: ControlDatum, front_depth: float, direction: np.ndarray) -> list[Shape]:
    """Four one-bend leads, local solder envelopes and insulated tangent wires."""
    rear = front_depth + SWITCH_BODY_H
    direction = unit(direction)
    up_hint = unit(datum.switch_v)
    rows: list[Shape] = []
    for sign_u in (-1.0, 1.0):
        for sign_v in (-1.0, 1.0):
            root = np.asarray(point_at(
                datum,
                rear + 0.25,
                u_offset=sign_u * (TERMINAL_ROOT_OUTER / 2.0 - 0.35),
                v_offset=sign_v * TERMINAL_ROOT_PITCH / 2.0,
            ))
            bend = root + direction * 2.80
            wire_end = bend + direction * 10.0
            formed = oriented_box_between(
                tuple(root - direction * 0.30), tuple(bend + direction * 0.30),
                tuple(up_hint), 1.20, 1.20,
                label=f"{datum.name}_formed_lead_{sign_u:+.0f}_{sign_v:+.0f}",
            )
            solder = oriented_box_between(
                tuple(bend - direction * 0.65), tuple(bend + direction * 0.90),
                tuple(up_hint), 2.20, 2.20,
                label=f"{datum.name}_solder_{sign_u:+.0f}_{sign_v:+.0f}",
            )
            wire = oriented_box_between(
                tuple(bend + direction * 0.45), tuple(wire_end),
                tuple(up_hint), 1.60, 1.60,
                label=f"{datum.name}_insulated_wire_{sign_u:+.0f}_{sign_v:+.0f}",
            )
            rows.extend((formed, solder, wire))
    return rows


def redesign_candidate(
    design,
    thumb_all: list[Shape],
    name: str,
    front_depth: float,
    *,
    exact_boolean: bool = False,
) -> dict[str, object]:
    datum = next(row for row in design.controls if row.name == name)
    carrier = build_low_profile_carrier(datum, front_depth)
    body = switch_body(datum, front_depth)
    actuator = switch_actuator(datum, front_depth)
    roots = list(terminal_root_cutters(datum, front_depth))

    wire_options = []
    for direction in tangent_directions(datum):
        shapes = build_formed_wiring(datum, front_depth, direction)
        # Direction selection only needs exact OCC distance.  Computing boolean
        # penetration for every deliberately rejected direction is extremely
        # expensive and cannot change which direction has the largest gap.
        minimum = fast_minimum_distance(thumb_all, shapes)
        wire_options.append((minimum, direction, shapes))
    _clearance, wire_direction, wiring = max(wire_options, key=lambda row: row[0])
    metric = list_metrics if exact_boolean else (
        lambda left, right: distance_only_metrics(
            left, right, "depth sweep uses exact OCC distance; selected depth receives exact boolean audit"
        )
    )
    # Run the expensive intersection-volume check only on the selected depth.
    wiring_metrics = metric(thumb_all, wiring)

    return {
        "name": name,
        "frontDepthMm": front_depth,
        "axisAdjustmentDeg": 0.0,
        "carrier": carrier,
        "switchBody": body,
        "actuator": actuator,
        "terminalRoots": roots,
        "wiring": wiring,
        "wireDirection": wire_direction.tolist(),
        "metrics": {
            "switch": metric(thumb_all, [body]),
            "actuator": metric(thumb_all, [actuator]),
            "terminalRoots": metric(thumb_all, roots),
            "carrier": metric(thumb_all, [carrier]),
            "wiring": wiring_metrics,
        },
    }


def choose_redesign(design, thumb_all: list[Shape], name: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    rows = []
    # The feasibility gate uses the shallowest manufacturable collar.  A
    # deeper-part optimisation would only reduce thumb clearance and is left
    # for production refinement after the fixed-screw blocker is resolved.
    for depth in (3.20,):
        candidate = redesign_candidate(design, thumb_all, name, float(round(depth, 3)))
        metrics = candidate["metrics"]
        candidate["minimumThumbClearanceMm"] = min(
            metrics[key]["minimumClearanceMm"]
            for key in ("switch", "actuator", "terminalRoots", "carrier", "wiring")
        )
        candidate["penetrationVolumeMm3"] = None
        rows.append(candidate)
    feasible = [
        row for row in rows
        if row["minimumThumbClearanceMm"] >= ROBUST_CLEARANCE
        and row["carrier"].is_valid
        and len(row["carrier"].solids()) == 1
    ]
    if not feasible:
        selected = max(rows, key=lambda row: row["minimumThumbClearanceMm"])
    else:
        selected = max(feasible, key=lambda row: row["frontDepthMm"])
    # Rebuild and audit only the chosen depth with exact boolean intersections.
    selected_exact = redesign_candidate(
        design, thumb_all, name, selected["frontDepthMm"], exact_boolean=True
    )
    selected_metrics = selected_exact["metrics"]
    selected_exact["minimumThumbClearanceMm"] = min(
        selected_metrics[key]["minimumClearanceMm"]
        for key in ("switch", "actuator", "terminalRoots", "carrier", "wiring")
    )
    selected_exact["penetrationVolumeMm3"] = sum(
        selected_metrics[key]["penetrationVolumeMm3"]
        for key in ("switch", "actuator", "terminalRoots", "carrier", "wiring")
    )
    return selected_exact, rows


def screw_sweep(assembly: dict[str, list[Shape]]) -> dict[str, object]:
    screws = assembly["screws"]
    base_groups = {
        key: rows for key, rows in assembly.items()
        if key not in ("screws", "assemblyShells")
    }
    original_thumb = flatten_thumb(base_groups)

    def clearance(fraction: float) -> float:
        # Relative geometry is identical if the small fixed screws are moved by
        # the inverse transform.  This avoids cloning the large exact thumb
        # module for every sweep sample.
        inverse_delta = -TARGET * float(fraction)
        relative_screws = [moved(screw, inverse_delta) for screw in screws]
        return fast_minimum_distance(original_thumb, relative_screws)

    samples = []
    for fraction in np.linspace(0.0, 1.0, 5):
        samples.append({"t": float(fraction), "clearanceMm": clearance(float(fraction))})
    passing = [row for row in samples if row["clearanceMm"] >= MIN_SCREW_CLEARANCE]
    coarse = max((row["t"] for row in passing), default=0.0)
    upper = min(1.0, coarse + 0.25)
    low, high = coarse, upper
    for _ in range(8):
        middle = 0.5 * (low + high)
        if clearance(middle) >= MIN_SCREW_CLEARANCE:
            low = middle
        else:
            high = middle
    robust_t = low
    return {
        "samples": samples,
        "robustFraction": robust_t,
        "maxRobustTranslationMm": (TARGET * robust_t).tolist(),
        "clearanceAtRobustMm": clearance(robust_t),
        "targetClearanceMm": clearance(1.0),
    }


def collision_matrix(thumb: dict[str, list[Shape]], fingers: dict[str, dict[str, list[Shape]]]) -> dict[str, object]:
    thumb_all = flatten_thumb(thumb)
    result = {}
    for name in BUTTON_ORDER:
        row = fingers[name]
        functional = [
            *row["switchBody"], *row["actuator"], *row["terminalRoots"], *row["wire"],
        ]
        result[name] = {
            "jointEnvelope": list_metrics(thumb_all, functional),
            "switchBody": list_metrics(thumb_all, row["switchBody"]),
            "actuator": list_metrics(thumb_all, row["actuator"]),
            "terminalRoots": list_metrics(thumb_all, row["terminalRoots"]),
            "wire": list_metrics(thumb_all, row["wire"]),
            "currentCarrier": list_metrics(thumb_all, row["currentCarrier"]),
            "cap": list_metrics(thumb_all, row["cap"]),
        }
    return result


def audit_current() -> dict[str, object]:
    print("[1/7] build Finger V2", flush=True)
    design = build_finger_controls_v2()
    print("[2/7] import exact assembly", flush=True)
    assembly = load_joystick_assembly_local()
    thumb = target_thumb(assembly)
    fingers = finger_envelopes(design)
    thumb_all = flatten_thumb(thumb)

    print("[3/7] prepare shell-interface evidence", flush=True)

    current_carriers = list({id(shape): shape for shape in design.carriers.values()}.values())
    print("[4/7] finger collision matrix", flush=True)
    matrix = collision_matrix(thumb, fingers)
    print("[5/7] carrier and screw clearance", flush=True)
    carrier_row = list_metrics(thumb_all, current_carriers)
    exact_screw_row = list_metrics(thumb_all, assembly["screws"])
    keepout_row = list_metrics(thumb_all, list(design.screw_keep_outs.values()))
    print("[6/7] shell-interface evidence", flush=True)
    clean_shell_row = {
        "minimumClearanceMm": 0.0,
        "penetrationVolumeMm3": None,
        "classification": "INCOMPATIBLE_OLD_OPENINGS",
        "note": "clean historical shell has original thumb openings; target transform is not represented",
    }
    cut_shell_row = {
        "minimumClearanceMm": 0.0,
        "penetrationVolumeMm3": None,
        "classification": "INCOMPATIBLE_OLD_THUMB_INTERFACE",
        "note": "Finger V2 shell freezes the original thumb interface",
    }
    print("[7/7] lower-15 housing evidence", flush=True)
    lower_shell_row = {
        "minimumClearanceMm": 0.2524557555295586,
        "penetrationVolumeMm3": 0.0,
        "classification": "SEATED_BUT_NOT_ROBUST",
        "note": "documented sampled moved-Backplate-to-shell gap from exact lower-15 housing study",
    }
    return {
        "targetMm": TARGET.tolist(),
        "sourceCounts": {key: len(value) for key, value in assembly.items()},
        "matrix": matrix,
        "thumbVsCurrentCarriers": carrier_row,
        "thumbVsExactAssemblyScrews": exact_screw_row,
        "thumbVsAnalyticalScrewKeepouts": keepout_row,
        "thumbVsCleanShell": clean_shell_row,
        "thumbVsFingerV2CutShell": cut_shell_row,
        "thumbVsLower15MeshShell": lower_shell_row,
        "design": design,
        "assembly": assembly,
        "thumb": thumb,
        "fingers": fingers,
    }


def summary_only(audit: dict[str, object]) -> dict[str, object]:
    matrix = audit["matrix"]
    return {
        "targetMm": audit["targetMm"],
        "sourceCounts": audit["sourceCounts"],
        "matrix": matrix,
        "thumbVsCurrentCarriers": audit["thumbVsCurrentCarriers"],
        "thumbVsExactAssemblyScrews": audit["thumbVsExactAssemblyScrews"],
        "thumbVsAnalyticalScrewKeepouts": audit["thumbVsAnalyticalScrewKeepouts"],
        "thumbVsCleanShell": audit["thumbVsCleanShell"],
        "thumbVsFingerV2CutShell": audit["thumbVsFingerV2CutShell"],
        "thumbVsLower15MeshShell": audit["thumbVsLower15MeshShell"],
    }


def candidate_report(row: dict[str, object]) -> dict[str, object]:
    return {
        "name": row["name"],
        "frontDepthMm": row["frontDepthMm"],
        "axisAdjustmentDeg": row["axisAdjustmentDeg"],
        "wireDirection": row["wireDirection"],
        "minimumThumbClearanceMm": row["minimumThumbClearanceMm"],
        "penetrationVolumeMm3": row["penetrationVolumeMm3"],
        "carrierValid": bool(row["carrier"].is_valid),
        "carrierSolidCount": len(row["carrier"].solids()),
        "metrics": row["metrics"],
    }


def full_study() -> dict[str, object]:
    current_path = OUT_DIR / "current_collision_audit.json"
    if not current_path.exists():
        current = audit_current()
        current_summary = summary_only(current)
        current_path.write_text(json.dumps(current_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        design = current["design"]
        assembly = current["assembly"]
        thumb = current["thumb"]
    else:
        print("[cache] current collision audit", flush=True)
        current_summary = json.loads(current_path.read_text(encoding="utf-8"))
        print("[study 1/6] build immutable Finger V2 reference", flush=True)
        design = build_finger_controls_v2()
        print("[study 2/6] import exact assembly reference", flush=True)
        assembly = load_joystick_assembly_local()
        thumb = target_thumb(assembly)

    thumb_all = flatten_thumb(thumb)
    print("[study 3/6] optimize N1 low-profile carrier/wiring", flush=True)
    n1, n1_rows = choose_redesign(design, thumb_all, "N1")
    print("[study 4/6] optimize N2 low-profile carrier/wiring", flush=True)
    n2, n2_rows = choose_redesign(design, thumb_all, "N2")

    carrier_pair = list_metrics([n1["carrier"]], [n2["carrier"]])
    proposed_bodies = [n1["switchBody"], n2["switchBody"]]
    switch_pair = list_metrics([proposed_bodies[0]], [proposed_bodies[1]])
    n2_opposite_shell = list_metrics([n2["carrier"]], [design.jad_shell])

    other_carrier_names = (
        "I2_I3_shared_carrier", "M4_N3_shared_carrier", "I4_carrier", "M3_carrier",
    )
    proposed_carriers = {
        "N1_low_profile_carrier": n1["carrier"],
        "N2_low_profile_carrier": n2["carrier"],
        **{name: design.carriers[name] for name in other_carrier_names},
    }
    proposed_carrier_clearance = list_metrics(thumb_all, list(proposed_carriers.values()))
    proposed_wiring_clearance = list_metrics(thumb_all, [*n1["wiring"], *n2["wiring"]])

    print("[study 5/6] fixed-screw lowering sweep", flush=True)
    sweep = screw_sweep(assembly)
    target_screw_by_group = {
        key: list_metrics(rows, assembly["screws"])
        for key, rows in thumb.items()
    }
    target_screw_by_index = {
        f"screw_{index + 1}": list_metrics(thumb_all, [screw])
        for index, screw in enumerate(assembly["screws"])
    }

    print("[study 6/6] export isolated prototype geometry", flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    exports: dict[str, str] = {}
    for name, candidate in (("N1", n1), ("N2", n2)):
        for suffix, exporter in (("step", export_step), ("stl", export_stl)):
            path = OUT_DIR / f"{name}_LOW_PROFILE_CARRIER_PROPOSAL.{suffix}"
            exporter(candidate["carrier"], path)
            exports[path.name] = str(path.relative_to(ROOT))
        wiring_path = OUT_DIR / f"{name}_FORMED_WIRING_ENVELOPE.step"
        export_step(Compound(children=list(candidate["wiring"]), label=f"{name}_formed_wiring"), wiring_path)
        exports[wiring_path.name] = str(wiring_path.relative_to(ROOT))

    target_thumb_path = OUT_DIR / "THUMB_TARGET_EXACT_MODULE.step"
    export_step(Compound(children=thumb_all, label="THUMB_TARGET_RIGID_MODULE"), target_thumb_path)
    exports[target_thumb_path.name] = str(target_thumb_path.relative_to(ROOT))

    controls = {row.name: row for row in design.controls}
    prototype_children: list[Shape] = [
        design.jad_shell,
        design.jfd_shell,
        *thumb_all,
        *design.caps.values(),
        *proposed_carriers.values(),
        *assembly["screws"],
    ]
    for name in BUTTON_ORDER:
        if name == "N1":
            prototype_children.extend((n1["switchBody"], n1["actuator"], *n1["terminalRoots"], *n1["wiring"]))
        elif name == "N2":
            prototype_children.extend((n2["switchBody"], n2["actuator"], *n2["terminalRoots"], *n2["wiring"]))
        else:
            depth = design.front_depths[name]
            prototype_children.extend((
                switch_body(controls[name], depth),
                switch_actuator(controls[name], depth),
                *terminal_root_cutters(controls[name], depth),
                wire_envelope(controls[name], depth),
            ))
    prototype_path = OUT_DIR / "FINGER_THUMB_JOINT_FEASIBILITY_REFERENCE.step"
    export_step(Compound(children=prototype_children, label="JOINT_FEASIBILITY_REFERENCE"), prototype_path)
    exports[prototype_path.name] = str(prototype_path.relative_to(ROOT))

    min_redesigned = min(
        float(n1["minimumThumbClearanceMm"]),
        float(n2["minimumThumbClearanceMm"]),
        float(proposed_carrier_clearance["minimumClearanceMm"]),
    )
    max_axis_adjust = max(float(n1["axisAdjustmentDeg"]), float(n2["axisAdjustmentDeg"]))
    redesign_pass = (
        min_redesigned >= ROBUST_CLEARANCE
        and n1["penetrationVolumeMm3"] <= BOOLEAN_EPS
        and n2["penetrationVolumeMm3"] <= BOOLEAN_EPS
        and carrier_pair["minimumClearanceMm"] >= MIN_SWITCH_SEPARATION
        and switch_pair["minimumClearanceMm"] >= MIN_SWITCH_SEPARATION
        and max_axis_adjust <= 5.0
    )
    wiring_pass = proposed_wiring_clearance["minimumClearanceMm"] >= ROBUST_CLEARANCE
    target_screw_pass = current_summary["thumbVsExactAssemblyScrews"]["minimumClearanceMm"] >= MIN_SCREW_CLEARANCE

    report = {
        "schema": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOCAL build123d/OCCT feasibility branch; Onshape 0; production write 0",
        "hardFreeze": {
            "fingerButtons": list(BUTTON_ORDER),
            "fingerCenterMovementMm": {name: 0.0 for name in BUTTON_ORDER},
            "thumbTranslationMm": TARGET.tolist(),
            "thumbRigidShapeChanged": False,
        },
        "sources": {
            "assemblyStep": {"path": str(ASSEMBLY_STEP.relative_to(ROOT)), "sha256": sha256(ASSEMBLY_STEP)},
            "productionFingerV2": "immutable imported build_finger_controls_v2() result",
            "currentCollisionAudit": str(current_path.relative_to(ROOT)),
        },
        "currentInternals": current_summary,
        "redesign": {
            "architecture": "replace N1/N2 shared rear-plate carrier with two shell-captured low-profile C-collars; retain other four carriers",
            "newCarrierCount": len(proposed_carriers),
            "minimumWallMm": PREFERRED_WALL,
            "axisAdjustmentMaximumDeg": max_axis_adjust,
            "N1Selected": candidate_report(n1),
            "N2Selected": candidate_report(n2),
            "N1DepthSweep": [candidate_report(row) for row in n1_rows],
            "N2DepthSweep": [candidate_report(row) for row in n2_rows],
            "carrierPair": carrier_pair,
            "switchPair": switch_pair,
            "minimumThumbToProposedCarrierMm": proposed_carrier_clearance["minimumClearanceMm"],
            "minimumThumbToProposedWiringMm": proposed_wiring_clearance["minimumClearanceMm"],
            "N2OppositeShellSeam": n2_opposite_shell,
            "thumbInterfaceProposal": {
                "type": "relieved lower-15 opening with three seating pads and continuous 1.60 mm local flange",
                "nonSeatingServiceClearanceMm": 0.80,
                "existingSampledGapMm": 0.2524557555295586,
                "productionImplementation": "NOT WRITTEN",
            },
        },
        "fixedScrews": {
            "requiredClearanceMm": MIN_SCREW_CLEARANCE,
            "targetByThumbGroup": target_screw_by_group,
            "targetByScrew": target_screw_by_index,
            "loweringSweep": sweep,
        },
        "assemblySequence": [
            "preload I2/I3, I4, M3 and M4/N3 modules and route their wires downward",
            "load N1 and N2 from the seam into separate low-profile collars",
            "form each N1/N2 distal lead once into the selected tangent route and pre-solder",
            "install the rigid thumb module at the relocated flange",
            "close JaD/JfD and capture the N2 collar from the opposite shell",
            "install unchanged screws only if the 2.50 mm keep-out is met",
        ],
        "exports": exports,
        "gates": {
            "fingerExteriorLayout": "PRESERVED",
            "thumbTarget": "FEASIBLE" if target_screw_pass and redesign_pass else "HOLD",
            "currentFingerInternals": "COMPATIBLE" if current_summary["thumbVsCurrentCarriers"]["penetrationVolumeMm3"] <= BOOLEAN_EPS else "REDESIGN REQUIRED",
            "redesignedInternals": "FEASIBLE" if redesign_pass else "HOLD",
            "wiring": "FEASIBLE" if wiring_pass else "HOLD",
            "assembly": "FEASIBLE" if target_screw_pass and redesign_pass and wiring_pass else "HOLD",
            "fdm": "FEASIBLE" if redesign_pass and PREFERRED_WALL >= MIN_WALL else "HOLD",
            "maxRobustThumbLoweringMm": sweep["maxRobustTranslationMm"],
            "answerYesNo": "YES" if target_screw_pass and redesign_pass and wiring_pass else "NO",
        },
        "limitations": [
            "The exact clean/Finger V2 shells still contain the original thumb interface; no production shell boolean was written.",
            "The lower-15 housing is a watertight STL plus its prior exact sampled seating audit, not a local analytic STEP body.",
            "Prototype geometry proves packaging directions but cannot override an unchanged screw collision.",
        ],
    }
    return report


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = full_study()
    path = OUT_DIR / "finger_thumb_joint_feasibility.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "target": report["hardFreeze"]["thumbTranslationMm"],
        "gates": report["gates"],
        "N1": report["redesign"]["N1Selected"],
        "N2": report["redesign"]["N2Selected"],
        "fixedScrewSweep": report["fixedScrews"]["loweringSweep"],
        "report": str(path),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
