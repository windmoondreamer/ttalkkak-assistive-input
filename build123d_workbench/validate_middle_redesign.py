"""Validate and export the build123d-first MIDDLE carrier redesign.

The script is deterministic, local-only and contains no Onshape mutation
code.  OCC B-reps are primary for the new parts; immutable cached meshes are
used only as obstacle references where the original source B-rep is not
available locally.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

import numpy as np
from build123d import Compound, Location, Shape, Vector, export_step, export_stl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scripts.analyze_middle_prewrite as geom  # noqa: E402
import scripts.audit_middle_its1105_design as legacy  # noqa: E402

from .middle_redesign import (  # noqa: E402
    ACTUATOR_PROJECTION,
    ACTUATOR_TRAVEL_MAX,
    BACKBONE_DEPTH,
    BACKBONE_SECTION,
    BACKBONE_SIDE_OFFSET,
    CAP_CONTACT_FREE_GAP,
    CAP_EXPOSURE,
    CAP_PAD_THICKNESS,
    CAP_SIZE,
    CAP_SKIRT_OUTER,
    CAP_SKIRT_REAR,
    CAP_TAB_INNER,
    CAP_TAB_OUTER,
    CAP_TAB_REAR,
    CAP_TAB_SPAN,
    CAP_TAB_FRONT,
    CARRIER_OUTER_X,
    CARRIER_OUTER_Y,
    CARRIER_WALL,
    COLUMN_REAR,
    FRONT_RING_FRONT,
    FRONT_RING_REAR,
    MIDDLE_DATUMS,
    MIN_DIVIDER,
    MIN_SCREW_CLEARANCE,
    MIN_SPLIT_OWNERSHIP,
    MIN_STRUCTURAL_WEB,
    MIN_SWITCH_SAT,
    OPENING_SIZE,
    OUT_DIR,
    PREFERRED_CARRIER_WALL,
    SHELL_WALL_NOMINAL,
    STOP_DEPTH,
    STOP_FRONT,
    STOP_REAR,
    STOP_WIDTH,
    SWITCH_BODY_H,
    SWITCH_BODY_X,
    SWITCH_BODY_Y,
    SWITCH_FRONT_DEPTH,
    SWITCH_POCKET_X,
    SWITCH_POCKET_Y,
    SWITCH_REAR_DEPTH,
    TERMINAL_CLEARANCE,
    TERMINAL_METAL_U,
    TERMINAL_METAL_V,
    TERMINAL_ROOT_DEPTH,
    TERMINAL_ROOT_OUTER,
    TERMINAL_ROOT_PITCH,
    WIRE_ENVELOPE_U,
    WIRE_ENVELOPE_V,
    WIRE_EXIT_DEPTH,
    MiddleDatum,
    backbone_node,
    build_middle_redesign,
    frame,
    oriented_box,
    point_at,
    scale,
    terminal_root_cutters,
)
from .source_of_truth import INDEX, MIDDLE as OLD_MIDDLE, ONSHAPE_URL, ONSHAPE_VERSION_ID  # noqa: E402


NAMES = tuple(datum.name for datum in MIDDLE_DATUMS)


def vector(row: Any) -> list[float]:
    return [float(row.X), float(row.Y), float(row.Z)]


def shape_metrics(shape: Shape) -> dict[str, Any]:
    bbox = shape.bounding_box()
    return {
        "valid": bool(shape.is_valid),
        "solidCount": len(shape.solids()),
        "faceCount": len(shape.faces()),
        "edgeCount": len(shape.edges()),
        "volumeMm3": float(shape.volume),
        "bboxMm": {"min": vector(bbox.min), "max": vector(bbox.max)},
    }


def obb_for(
    datum: MiddleDatum,
    width_u: float,
    width_v: float,
    front: float,
    rear: float,
    *,
    u_offset: float = 0.0,
    v_offset: float = 0.0,
):
    axes = legacy.rotated_axes(np.asarray(datum.axis), datum.roll_deg)
    point = np.asarray(datum.center) + axes[0] * u_offset + axes[1] * v_offset
    return legacy.obb_rect(point, axes, width_u, width_v, rear - front, front)


def projected_segment_box(p0, p1, x_hint, width_x, width_y):
    p0 = np.asarray(p0, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    direction = geom.unit(p1 - p0)
    hint = np.asarray(x_hint, dtype=float)
    local_x = hint - direction * float(np.dot(hint, direction))
    if np.linalg.norm(local_x) < 1e-9:
        local_x = geom.frame(direction)[0]
    local_x = geom.unit(local_x)
    local_y = geom.unit(np.cross(direction, local_x))
    return (
        (p0 + p1) / 2.0,
        np.asarray((local_x, local_y, direction)),
        np.asarray((width_x / 2.0, width_y / 2.0, np.linalg.norm(p1 - p0) / 2.0)),
    )


def carrier_proxy_boxes() -> dict[str, tuple]:
    """OBB decomposition matching every new carrier's positive material."""
    rows: dict[str, tuple] = {}
    corner_u = SWITCH_POCKET_X / 2.0 + CARRIER_WALL / 2.0
    corner_v = SWITCH_POCKET_Y / 2.0 + CARRIER_WALL / 2.0
    stop_v = CARRIER_OUTER_Y / 2.0 - STOP_DEPTH / 2.0 - 0.44
    for datum in MIDDLE_DATUMS:
        # Four exact bars replace the deliberately hollow front-ring B-rep.
        rows[f"{datum.name}_ring_pv"] = obb_for(
            datum, CARRIER_OUTER_X, CARRIER_WALL,
            FRONT_RING_FRONT, FRONT_RING_REAR, v_offset=corner_v,
        )
        rows[f"{datum.name}_ring_nv"] = obb_for(
            datum, CARRIER_OUTER_X, CARRIER_WALL,
            FRONT_RING_FRONT, FRONT_RING_REAR, v_offset=-corner_v,
        )
        rows[f"{datum.name}_ring_pu"] = obb_for(
            datum, CARRIER_WALL, SWITCH_POCKET_Y,
            FRONT_RING_FRONT, FRONT_RING_REAR, u_offset=corner_u,
        )
        rows[f"{datum.name}_ring_nu"] = obb_for(
            datum, CARRIER_WALL, SWITCH_POCKET_Y,
            FRONT_RING_FRONT, FRONT_RING_REAR, u_offset=-corner_u,
        )
        for sign_u in (-1.0, 1.0):
            for sign_v in (-1.0, 1.0):
                rows[
                    f"{datum.name}_column_{'p' if sign_u > 0 else 'n'}u_"
                    f"{'p' if sign_v > 0 else 'n'}v"
                ] = obb_for(
                    datum,
                    CARRIER_WALL,
                    CARRIER_WALL,
                    FRONT_RING_REAR - 0.20,
                    COLUMN_REAR,
                    u_offset=sign_u * corner_u,
                    v_offset=sign_v * corner_v,
                )
        for sign_v in (-1.0, 1.0):
            rows[f"{datum.name}_stop_{'p' if sign_v > 0 else 'n'}v"] = obb_for(
                datum,
                STOP_WIDTH,
                STOP_DEPTH,
                STOP_FRONT,
                STOP_REAR,
                v_offset=sign_v * stop_v,
            )

    for left, right in zip(MIDDLE_DATUMS[:2], MIDDLE_DATUMS[1:3]):
        p0 = np.asarray(backbone_node(left), dtype=float)
        p1 = np.asarray(backbone_node(right), dtype=float)
        direction = geom.unit(p1 - p0)
        extension = min(0.90, float(np.linalg.norm(p1 - p0)) * 0.08)
        p0 = p0 - direction * extension
        p1 = p1 + direction * extension
        rows[f"{left.name}_{right.name}_backbone"] = projected_segment_box(
            p0,
            p1,
            -geom.unit(np.asarray(left.axis) + np.asarray(right.axis)),
            BACKBONE_SECTION,
            BACKBONE_SECTION,
        )

    datum = MIDDLE_DATUMS[3]
    for sign_u in (-1.0, 1.0):
        rows[f"M4_keyed_stop_{'p' if sign_u > 0 else 'n'}u"] = obb_for(
            datum,
            3.20,
            CARRIER_WALL,
            9.80,
            12.20,
            u_offset=sign_u * 4.20,
            v_offset=BACKBONE_SIDE_OFFSET,
        )
    return rows


def exact_intersection_volume(a: Shape, b: Shape) -> float:
    intersection = a & b
    return 0.0 if intersection is None else float(intersection.volume)


def minimum_mesh_clearance(mesh: np.ndarray, boxes: dict[str, tuple]) -> dict[str, Any]:
    best = (float("inf"), "")
    collisions: list[str] = []
    for name, box in boxes.items():
        if geom.mesh_box_intersects(mesh, box):
            collisions.append(name)
            distance = 0.0
        else:
            distance = float(geom.mesh_box_distance(mesh, box))
        if distance < best[0]:
            best = (distance, name)
    return {
        "collisionCount": len(collisions),
        "collidingProxies": collisions,
        "minimumClearanceMm": best[0],
        "nearestProxy": best[1],
    }


def mesh_collision_only(mesh: np.ndarray, boxes: dict[str, tuple]) -> dict[str, Any]:
    collisions = [name for name, box in boxes.items() if geom.mesh_box_intersects(mesh, box)]
    return {"collisionCount": len(collisions), "collidingProxies": collisions}


def export_models(design) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    exports: dict[str, Any] = {}
    named_shapes = {
        "M1_M2_M3_shared_carrier": design.shared_carrier.solid,
        "M4_single_carrier": design.m4_carrier.solid,
        **{f"{datum.name}_cap": cap for datum, cap in zip(MIDDLE_DATUMS, design.caps)},
        **{
            f"{datum.name}_ITS1105_reference": switch
            for datum, switch in zip(MIDDLE_DATUMS, design.switches)
        },
    }
    for name, shape in named_shapes.items():
        step_path = OUT_DIR / f"{name}.step"
        stl_path = OUT_DIR / f"{name}.stl"
        export_step(shape, step_path)
        export_stl(shape, stl_path, tolerance=0.025, angular_tolerance=0.06)
        exports[name] = {"step": str(step_path), "stl": str(stl_path)}

    printable = Compound(children=list(design.printable_parts), label="MIDDLE_printable_parts_6")
    reference = design.assembly_reference
    for name, shape in (
        ("MIDDLE_printable_parts_6", printable),
        ("MIDDLE_reference_with_ITS1105", reference),
    ):
        step_path = OUT_DIR / f"{name}.step"
        stl_path = OUT_DIR / f"{name}.stl"
        export_step(shape, step_path)
        export_stl(shape, stl_path, tolerance=0.025, angular_tolerance=0.06)
        exports[name] = {"step": str(step_path), "stl": str(stl_path)}
    return exports


def validate() -> dict[str, Any]:
    design = build_middle_redesign()
    axes = np.asarray([datum.axis for datum in MIDDLE_DATUMS], dtype=float)
    points = np.asarray([datum.center for datum in MIDDLE_DATUMS], dtype=float)
    body_boxes = [
        legacy.obb_rect(
            points[i],
            legacy.rotated_axes(axes[i], MIDDLE_DATUMS[i].roll_deg),
            SWITCH_BODY_X,
            SWITCH_BODY_Y,
            SWITCH_BODY_H,
            SWITCH_FRONT_DEPTH,
        )
        for i in range(4)
    ]
    pocket_boxes = [
        obb_for(
            datum,
            SWITCH_POCKET_X,
            SWITCH_POCKET_Y,
            SWITCH_FRONT_DEPTH,
            SWITCH_REAR_DEPTH,
        )
        for datum in MIDDLE_DATUMS
    ]
    cap_boxes = [
        obb_for(
            datum,
            CAP_SIZE,
            CAP_SIZE,
            -CAP_EXPOSURE,
            -CAP_EXPOSURE + CAP_PAD_THICKNESS,
        )
        for datum in MIDDLE_DATUMS
    ]

    adjacent = ((0, 1), (1, 2), (2, 3))
    body_sat = {
        f"{NAMES[i]}-{NAMES[j]}": float(geom.sat_signed(body_boxes[i], body_boxes[j]))
        for i, j in adjacent
    }
    divider = {
        f"{NAMES[i]}-{NAMES[j]}": float(geom.sat_signed(pocket_boxes[i], pocket_boxes[j]))
        for i, j in adjacent
    }
    cap_gap = {
        f"{NAMES[i]}-{NAMES[j]}": float(geom.sat_signed(cap_boxes[i], cap_boxes[j]))
        for i, j in adjacent
    }
    split = {
        "M3_JfD": -float(geom.corners(pocket_boxes[2])[:, 0].max()),
        "M4_JaD": float(geom.corners(pocket_boxes[3])[:, 0].min()),
    }

    mismatch = {
        datum.name: math.degrees(
            math.acos(float(np.clip(np.dot(datum.axis, datum.shell_normal), -1.0, 1.0)))
        )
        for datum in MIDDLE_DATUMS
    }

    carrier_shapes = [design.shared_carrier.solid, design.m4_carrier.solid]
    exact_switch_collision = {
        datum.name: {
            "sharedCarrierMm3": exact_intersection_volume(design.shared_carrier.solid, switch),
            "m4CarrierMm3": exact_intersection_volume(design.m4_carrier.solid, switch),
        }
        for datum, switch in zip(MIDDLE_DATUMS, design.switches)
    }

    # Straight switch insertion from the exterior through the complete pocket.
    insertion_rows: dict[str, Any] = {}
    for index, datum in enumerate(MIDDLE_DATUMS):
        carrier = carrier_shapes[0] if index < 3 else carrier_shapes[1]
        samples = []
        for front in np.linspace(0.20, SWITCH_FRONT_DEPTH, 10):
            moving_body = oriented_box(
                datum,
                SWITCH_BODY_X,
                SWITCH_BODY_Y,
                float(front),
                float(front + SWITCH_BODY_H),
                label=f"{datum.name}_insertion_probe",
            )
            samples.append(
                {
                    "frontDepthMm": float(front),
                    "intersectionVolumeMm3": exact_intersection_volume(carrier, moving_body),
                }
            )
        insertion_rows[datum.name] = {
            "maximumInterferenceMm3": max(row["intersectionVolumeMm3"] for row in samples),
            "samples": samples,
        }

    cap_motion = {}
    for index, (datum, cap) in enumerate(zip(MIDDLE_DATUMS, design.caps)):
        inward = scale(datum.axis, -ACTUATOR_TRAVEL_MAX)
        pressed = cap.moved(Location(Vector(*inward)))
        carrier = carrier_shapes[0] if index < 3 else carrier_shapes[1]
        # The cap contact intentionally overlaps the actuator during a press;
        # the hard collision checks therefore use the carrier and housing body.
        body_only = oriented_box(
            datum,
            SWITCH_BODY_X,
            SWITCH_BODY_Y,
            SWITCH_FRONT_DEPTH,
            SWITCH_REAR_DEPTH,
            label=f"{datum.name}_housing_only",
        )
        cap_motion[datum.name] = {
            "maximumTravelMm": ACTUATOR_TRAVEL_MAX,
            "carrierInterferenceMm3": exact_intersection_volume(carrier, pressed),
            "switchHousingInterferenceMm3": exact_intersection_volume(body_only, pressed),
            "skirtToHousingAxialClearanceAtMaxTravelMm": (
                SWITCH_FRONT_DEPTH - CAP_SKIRT_REAR - ACTUATOR_TRAVEL_MAX
            ),
            "tabToCarrierAxialClearanceAtMaxTravelMm": (
                FRONT_RING_FRONT - CAP_TAB_REAR - ACTUATOR_TRAVEL_MAX
            ),
            "tabToHousingRadialClearanceMm": (
                CAP_TAB_INNER / 2.0 - max(SWITCH_BODY_X, SWITCH_BODY_Y) / 2.0
            ),
        }

    proxies = carrier_proxy_boxes()
    index_holder_boxes = [
        geom.obb(
            np.asarray(button.center),
            geom.unit(np.asarray(button.axis)),
            12.40,
            9.70,
            2.80,
        )
        for button in INDEX
    ]
    index_switch_boxes = [
        geom.obb(
            np.asarray(button.center),
            geom.unit(np.asarray(button.axis)),
            6.18,
            3.56,
            4.40,
        )
        for button in INDEX
    ]
    index_clearance = {}
    for name, box in proxies.items():
        holder = min(geom.box_distance(box, target) for target in index_holder_boxes)
        switch = min(geom.box_distance(box, target) for target in index_switch_boxes)
        index_clearance[name] = {
            "holderMm": float(holder),
            "switchMm": float(switch),
        }

    screw_rows = {
        name: min(
            geom.cylinder_gap_x(box, np.asarray(point), x_range, radius)
            for point, x_range, radius in geom.SCREWS.values()
        )
        for name, box in proxies.items()
    }

    frozen_mesh_results = {
        "INDEX_shell_keepout": minimum_mesh_clearance(
            geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"), proxies
        ),
        "RWID": minimum_mesh_clearance(geom.load_triangles("INDEX_FINAL_RWID"), proxies),
        "RZKD": minimum_mesh_clearance(geom.load_triangles("INDEX_FINAL_RZKD"), proxies),
    }
    thumb_names = (
        "Backplate",
        "Small_joystick_attachment",
        "Button_corner_1",
        "Button_side_1",
        "Button_wide_1",
        "Button_middle_1",
        "Button_corner_2",
        "Button_side_2",
        "Button_wide_2",
        "Button_middle_2",
    )
    thumb_collision = {
        name: mesh_collision_only(geom.load_triangles(name), proxies)
        for name in thumb_names
    }

    root_clearance = {}
    for datum in MIDDLE_DATUMS:
        carrier = carrier_shapes[0] if datum.shell_owner == "JfD" else carrier_shapes[1]
        root_clearance[datum.name] = [
            exact_intersection_volume(carrier, cutter)
            for cutter in terminal_root_cutters(datum)
        ]

    part_metrics = {
        "M1_M2_M3_shared_carrier": shape_metrics(design.shared_carrier.solid),
        "M4_single_carrier": shape_metrics(design.m4_carrier.solid),
        **{
            f"{datum.name}_cap": shape_metrics(cap)
            for datum, cap in zip(MIDDLE_DATUMS, design.caps)
        },
    }
    fragment_count = sum(max(0, row["solidCount"] - 1) for row in part_metrics.values())

    min_index_holder = min(row["holderMm"] for row in index_clearance.values())
    min_index_switch = min(row["switchMm"] for row in index_clearance.values())
    min_screw = min(screw_rows.values())
    frozen_collision_count = sum(
        row["collisionCount"] for row in frozen_mesh_results.values()
    )
    thumb_collision_count = sum(row["collisionCount"] for row in thumb_collision.values())
    exact_internal_collision = max(
        value
        for row in exact_switch_collision.values()
        for value in row.values()
    )
    insertion_interference = max(
        row["maximumInterferenceMm3"] for row in insertion_rows.values()
    )
    cap_hard_interference = max(
        max(row["carrierInterferenceMm3"], row["switchHousingInterferenceMm3"])
        for row in cap_motion.values()
    )
    root_interference = max(max(rows) for rows in root_clearance.values())

    local_gates = {
        "occPartValidity": all(row["valid"] for row in part_metrics.values()),
        "oneSolidPerPrintablePart": all(row["solidCount"] == 1 for row in part_metrics.values()),
        "switchSat": min(body_sat.values()) >= MIN_SWITCH_SAT - 1e-8,
        "divider": min(divider.values()) >= MIN_DIVIDER - 1e-8,
        "splitOwnership": min(split.values()) >= MIN_SPLIT_OWNERSHIP - 1e-8,
        "axisMismatch": max(mismatch.values()) <= 5.0 + 1e-8,
        "capSpacing": min(cap_gap.values()) > 0.0,
        "indexHolderCollision": min_index_holder > 0.0,
        "indexSwitchCollision": min_index_switch > 0.0,
        "screwClearance": min_screw >= MIN_SCREW_CLEARANCE - 1e-8,
        "frozenObstacleCollision": frozen_collision_count == 0,
        "thumbCollision": thumb_collision_count == 0,
        "switchCarrierInterference": exact_internal_collision <= 1e-7,
        "terminalRootInterference": root_interference <= 1e-7,
        "straightSwitchInsertion": insertion_interference <= 1e-7,
        "capTravel": cap_hard_interference <= 1e-7,
        "minimumStructuralWeb": MIN_STRUCTURAL_WEB <= CARRIER_WALL,
        "fragmentCheck": fragment_count == 0,
    }
    local_pass = all(local_gates.values())

    exports = export_models(design)
    old_centers = {button.name: button.center for button in OLD_MIDDLE}
    result = {
        "schema": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "build123d FIRST / local exact geometry / Onshape CAD WRITE 0",
        "onshapeReference": {
            "url": ONSHAPE_URL,
            "versionId": ONSHAPE_VERSION_ID,
            "currentBrepRecheck": "BLOCKED: API HTTP 402 and browser session at sign-in",
        },
        "parametersMm": {
            "switchBody": [SWITCH_BODY_X, SWITCH_BODY_Y, SWITCH_BODY_H],
            "switchPocket": [SWITCH_POCKET_X, SWITCH_POCKET_Y],
            "pocketPerSideClearance": [
                (SWITCH_POCKET_X - SWITCH_BODY_X) / 2.0,
                (SWITCH_POCKET_Y - SWITCH_BODY_Y) / 2.0,
            ],
            "cap": CAP_SIZE,
            "opening": OPENING_SIZE,
            "capExposure": CAP_EXPOSURE,
            "switchFrontDepth": SWITCH_FRONT_DEPTH,
            "switchRearDepth": SWITCH_REAR_DEPTH,
            "carrierWall": CARRIER_WALL,
            "backboneSection": BACKBONE_SECTION,
            "terminalClearance": TERMINAL_CLEARANCE,
            "wireEnvelope": [WIRE_ENVELOPE_U, WIRE_ENVELOPE_V, WIRE_EXIT_DEPTH],
        },
        "datums": {
            datum.name: {
                "centerMm": list(datum.center),
                "oldCenterMm": list(old_centers[datum.name]),
                "centerChangeMm": float(
                    np.linalg.norm(np.asarray(datum.center) - np.asarray(old_centers[datum.name]))
                ),
                "axis": list(datum.axis),
                "shellNormal": list(datum.shell_normal),
                "axisMismatchDeg": mismatch[datum.name],
                "rollDeg": datum.roll_deg,
                "shellOwner": datum.shell_owner,
                "arcStationMm": datum.arc_station,
            }
            for datum in MIDDLE_DATUMS
        },
        "spacing": {
            "switchSatMm": body_sat,
            "minimumSwitchSatMm": min(body_sat.values()),
            "dividerMm": divider,
            "minimumDividerMm": min(divider.values()),
            "splitOwnershipMm": split,
            "minimumSplitOwnershipMm": min(split.values()),
            "capGapMm": cap_gap,
            "minimumCapGapMm": min(cap_gap.values()),
        },
        "clearance": {
            "indexPerProxy": index_clearance,
            "minimumIndexHolderMm": min_index_holder,
            "minimumIndexSwitchMm": min_index_switch,
            "screwPerProxyMm": screw_rows,
            "minimumScrewMm": min_screw,
            "frozenMeshes": frozen_mesh_results,
            "thumbCollision": thumb_collision,
        },
        "exactOccChecks": {
            "partMetrics": part_metrics,
            "switchCarrierIntersectionMm3": exact_switch_collision,
            "terminalRootIntersectionMm3": root_clearance,
            "switchInsertion": insertion_rows,
            "capMotion": cap_motion,
            "unexpectedFragmentCount": fragment_count,
        },
        "architecture": {
            "independentMiddleParts": 6,
            "tinyServiceParts": 0,
            "parts": ["4 caps", "1 shared M1-M3 carrier", "1 M4 carrier"],
            "retention": "shell-captive cap tabs + robust continuous carrier; no hooks/rails",
            "terminalPolicy": "all fixed roots cleared; distal leads pre-formable; open rear wire exit",
            "recommendedPrintOrientation": {
                "sharedCarrier": "non-wiring backbone side on build plate; pockets open sideways/up",
                "M4Carrier": "keyed-stop/backbone side on build plate; pocket open sideways/up",
                "caps": "external pad face on build plate; retention tabs upward",
            },
            "supportRequirement": "carriers: minimal/local bridge support only; caps: none expected",
            "assemblySequence": [
                "insert each cap from shell interior and push the 7.6 mm pad through the 8.0 mm opening",
                "pre-form and optionally pre-solder the selected ITS-1105 leads",
                "insert M1-M3 switches straight into the shared carrier until the broad rear stops",
                "route wires through the open rear side opposite the backbone",
                "mount the shared carrier into JfD and capture it with the shell interface",
                "repeat with the independent M4 carrier in JaD",
                "close the existing shell assembly; verify 0.25 mm actuation and return",
            ],
        },
        "structural": {
            "minimumStructuralWebMm": MIN_STRUCTURAL_WEB,
            "minimumActualCarrierWallMm": CARRIER_WALL,
            "preferredCarrierWallMm": PREFERRED_CARRIER_WALL,
            "minimumCapRetentionFeatureMm": min(
                (CAP_TAB_OUTER - CAP_TAB_INNER) / 2.0,
                CAP_TAB_REAR - CAP_TAB_FRONT,
                (CAP_SKIRT_OUTER - 4.40) / 2.0,
            ),
        },
        "localGates": local_gates,
        "build123dLocalPass": local_pass,
        "onshapePhaseGate": {
            "status": "HOLD",
            "reason": (
                "current Onshape B-rep/feature-tree and exact shell docking interface could not be "
                "re-read; no production write is permitted until that read-only gate is restored"
            ),
            "cadWriteCount": 0,
        },
        "exports": exports,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUT_DIR / "middle_redesign_validation.json"
    report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    result = validate()
    print(json.dumps({
        "build123dLocalPass": result["build123dLocalPass"],
        "localGates": result["localGates"],
        "minimumSwitchSatMm": result["spacing"]["minimumSwitchSatMm"],
        "minimumDividerMm": result["spacing"]["minimumDividerMm"],
        "minimumIndexHolderMm": result["clearance"]["minimumIndexHolderMm"],
        "minimumScrewMm": result["clearance"]["minimumScrewMm"],
        "unexpectedFragmentCount": result["exactOccChecks"]["unexpectedFragmentCount"],
        "onshapePhaseGate": result["onshapePhaseGate"],
        "outDir": str(OUT_DIR),
    }, indent=2, ensure_ascii=False))
    if not result["build123dLocalPass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
