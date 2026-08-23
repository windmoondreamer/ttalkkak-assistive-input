"""Mechanical design review for the approved Finger + lowered Thumb V3.

This is a review-only LOCAL build123d/OCCT consumer.  It does not export STL,
print plates, mockups, or production geometry.  The approved exterior control
centres and the rigid thumb target remain immutable.  One narrowly scoped
candidate correction is evaluated in memory: final through-bore/counterbore
tools are applied *after* the screw bosses have been fused into the shells.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Align, Box, Face, Location, Plane, Shape, Vector, import_step

from .finger_controls_v2 import oriented_box_between
from .finger_thumb_integrated_v3 import (
    CHOSEN_FASTENER_OPTION,
    FASTENER_OPTIONS,
    SCREW_BOSS_RADIUS,
    SCREW_HEAD_RADIUS,
    SCREW_INSERT_RADIUS,
    N_CARRIER_WALL,
    N_CARRIER_OUTER_X,
    N_CARRIER_OUTER_Y,
    N_PAIR_BRIDGE,
    N_RING_FRONT_DEPTH,
    N_RESTRAINT_STRAP_V,
    N_RESTRAINT_THICKNESS,
    SWITCH_BODY_H,
    SWITCH_BODY_X,
    SWITCH_POCKET_X,
    SWITCH_POCKET_Y,
    build_fastener_screw,
    controls_from_manifest,
    exact_metrics,
    oriented_box,
    point_at,
    terminal_root_cutters,
    unit,
    x_cylinder,
    xyz,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_integrated_v3"
OUT_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_integrated_v3_internal_review"
REFERENCE_STEP = SOURCE_DIR / "FINGER_THUMB_INTEGRATED_V3_REFERENCE.step"
JAD_STEP = SOURCE_DIR / "JAD_FINGER_THUMB_INTEGRATED_V3.step"
JFD_STEP = SOURCE_DIR / "JFD_FINGER_THUMB_INTEGRATED_V3.step"
SOURCE_VALIDATION = SOURCE_DIR / "finger_thumb_integrated_v3_validation.json"

EPS = 1.0e-7
SCREW_CLEARANCE_RADIUS = 1.70
HEAD_COUNTERBORE_RADIUS = 2.90
HEAD_COUNTERBORE_SHOULDER_X = -5.75
INSERT_POCKET_START_X = 5.80


def intersection_volume(left: Shape, right: Shape) -> float:
    common = left & right
    if common is None or not common.solids():
        return 0.0
    return float(common.volume)


def center_box(size: tuple[float, float, float], center: tuple[float, float, float], label: str) -> Shape:
    shape = Box(*size, align=(Align.CENTER, Align.CENTER, Align.CENTER)).moved(
        Location(Vector(*center))
    )
    shape.label = label
    return shape


def select_children(reference: Shape, predicate) -> list[Shape]:
    return [child for child in reference.children if predicate(child.label)]


def apply_final_fastener_bores(jad: Shape, jfd: Shape) -> tuple[Shape, Shape, dict[str, object]]:
    """Evaluate a correct head shoulder, through clearance, and insert pocket.

    V3 pre-bored each boss before union.  Any pre-existing shell wall crossing
    the axis can therefore refill the nominal hole during fuse.  These cutters
    are deliberately applied to the final shell solids, which is the correct
    boolean order for an actual fastener path.
    """
    jad_candidate = jad
    jfd_candidate = jfd
    removed: dict[str, dict[str, float]] = {}
    for index, (y, z) in enumerate(FASTENER_OPTIONS[CHOSEN_FASTENER_OPTION], 1):
        jfd_before = float(jfd_candidate.volume)
        jad_before = float(jad_candidate.volume)

        jfd_clearance = x_cylinder(
            y, z, SCREW_CLEARANCE_RADIUS, -11.50, 0.80,
            f"REVIEW_screw_{index}_JfD_clearance",
        )
        jfd_counterbore = x_cylinder(
            y, z, HEAD_COUNTERBORE_RADIUS, -11.50, HEAD_COUNTERBORE_SHOULDER_X,
            f"REVIEW_screw_{index}_head_counterbore",
        )
        jad_clearance = x_cylinder(
            y, z, SCREW_CLEARANCE_RADIUS, -0.80, INSERT_POCKET_START_X + 0.60,
            f"REVIEW_screw_{index}_JaD_clearance",
        )
        jad_insert = x_cylinder(
            y, z, SCREW_INSERT_RADIUS, INSERT_POCKET_START_X, 11.50,
            f"REVIEW_screw_{index}_heat_set_insert_pocket",
        )

        jfd_candidate = (jfd_candidate - jfd_clearance - jfd_counterbore).clean()
        jad_candidate = (jad_candidate - jad_clearance - jad_insert).clean()
        removed[f"screw_{index}"] = {
            "JfDMaterialRemovedMm3": jfd_before - float(jfd_candidate.volume),
            "JaDMaterialRemovedMm3": jad_before - float(jad_candidate.volume),
        }

    return jad_candidate, jfd_candidate, {
        "clearanceDiameterMm": 2.0 * SCREW_CLEARANCE_RADIUS,
        "headCounterboreDiameterMm": 2.0 * HEAD_COUNTERBORE_RADIUS,
        "headRadialClearanceMm": HEAD_COUNTERBORE_RADIUS - SCREW_HEAD_RADIUS,
        "headBearingShoulderRadialMm": SCREW_BOSS_RADIUS - HEAD_COUNTERBORE_RADIUS,
        "insertPocketDiameterMm": 2.0 * SCREW_INSERT_RADIUS,
        "insertPocketRadialWallMm": SCREW_BOSS_RADIUS - SCREW_INSERT_RADIUS,
        "materialRemoved": removed,
    }


def build_noninterfering_n_pair_candidate() -> tuple[Shape, Shape]:
    """Shorten the front support and move the rear bridge behind the switch.

    V3 intentionally moves the N1/N2 switch bodies to 1.20 mm internal depth.
    The failure is geometric overlap: the current front ring ends 0.71 mm
    behind the switch body while the outer-width rear straps start there, and
    the 2.40 mm rear bridge extends back toward the switch.  This review-only
    candidate keeps every frozen control transform but separates those zones.
    """
    controls, depths = controls_from_manifest()
    by_name = {datum.name: datum for datum in controls}
    review_front_support_depth = 2.45

    rings: list[Shape] = []
    for name in ("N1", "N2"):
        datum = by_name[name]
        outer = oriented_box(
            datum,
            N_CARRIER_OUTER_X,
            N_CARRIER_OUTER_Y,
            N_RING_FRONT_DEPTH,
            N_RING_FRONT_DEPTH + review_front_support_depth,
            label=f"{name}_REVIEW_short_front_outer",
        )
        pocket = oriented_box(
            datum,
            SWITCH_POCKET_X,
            SWITCH_POCKET_Y,
            N_RING_FRONT_DEPTH - 0.30,
            N_RING_FRONT_DEPTH + review_front_support_depth + 0.30,
            label=f"{name}_REVIEW_front_pocket",
        )
        rings.append((outer - pocket).clean())
    p0 = np.asarray(point_at(by_name["N1"], N_RING_FRONT_DEPTH + 0.75, v_offset=4.50))
    p1 = np.asarray(point_at(by_name["N2"], N_RING_FRONT_DEPTH + 0.75, v_offset=4.50))
    direction = unit(p1 - p0)
    front_bridge = oriented_box_between(
        xyz(p0 - direction * 1.10),
        xyz(p1 + direction * 1.10),
        xyz(-unit(np.asarray(by_name["N1"].axis) + np.asarray(by_name["N2"].axis))),
        N_PAIR_BRIDGE,
        N_PAIR_BRIDGE,
        label="N1_N2_REVIEW_front_bridge",
    )
    front = rings[0].fuse(rings[1]).fuse(front_bridge)
    for name in ("N1", "N2"):
        front = front - oriented_box(
            by_name[name],
            SWITCH_POCKET_X,
            SWITCH_POCKET_Y,
            N_RING_FRONT_DEPTH - 0.35,
            N_RING_FRONT_DEPTH + review_front_support_depth + 0.35,
            label=f"{name}_REVIEW_front_recut",
        )
    front = front.clean()
    front.label = "N1_N2_REVIEW_noninterfering_front_carrier"

    straps: list[Shape] = []
    rear_depths: dict[str, float] = {}
    for name in ("N1", "N2"):
        datum = by_name[name]
        rear_depth = depths[name] + SWITCH_BODY_H
        rear_depths[name] = rear_depth
        straps.append(oriented_box(
            datum,
            SWITCH_BODY_X + 2.0 * N_CARRIER_WALL,
            N_RESTRAINT_STRAP_V,
            rear_depth + 0.14,
            rear_depth + N_RESTRAINT_THICKNESS,
            label=f"{name}_REVIEW_noninterfering_rear_stop",
        ))
    bridge_offset = N_PAIR_BRIDGE / 2.0 + 0.35
    p0 = np.asarray(point_at(by_name["N1"], rear_depths["N1"] + bridge_offset, v_offset=0.0))
    p1 = np.asarray(point_at(by_name["N2"], rear_depths["N2"] + bridge_offset, v_offset=0.0))
    direction = unit(p1 - p0)
    bridge = oriented_box_between(
        xyz(p0 - direction * 1.15),
        xyz(p1 + direction * 1.15),
        xyz(-unit(np.asarray(by_name["N1"].axis) + np.asarray(by_name["N2"].axis))),
        N_PAIR_BRIDGE,
        N_PAIR_BRIDGE,
        label="N1_N2_REVIEW_noninterfering_rear_bridge",
    )
    result = straps[0].fuse(straps[1]).fuse(bridge)
    for name in ("N1", "N2"):
        for root in terminal_root_cutters(by_name[name], depths[name]):
            result = result - root
    result = result.clean()
    result.label = "N1_N2_REVIEW_noninterfering_rear_restraint"
    return front, result


def screw_shell_rows(screws: dict[str, Shape], jad: Shape, jfd: Shape) -> dict[str, object]:
    rows: dict[str, object] = {}
    for name, screw in screws.items():
        jad_volume = intersection_volume(screw, jad)
        jfd_volume = intersection_volume(screw, jfd)
        rows[name] = {
            "JaDIntersectionMm3": jad_volume,
            "JfDIntersectionMm3": jfd_volume,
            "totalIntersectionMm3": jad_volume + jfd_volume,
        }
    return rows


def yz_triangle_area(points: Iterable[tuple[float, float]]) -> float:
    p0, p1, p2 = [np.asarray(row, dtype=float) for row in points]
    first = p1 - p0
    second = p2 - p0
    return 0.5 * abs(float(first[0] * second[1] - first[1] * second[0]))


def point_in_triangle(point: tuple[float, float], triangle: tuple[tuple[float, float], ...]) -> bool:
    p = np.asarray(point, dtype=float)
    a, b, c = [np.asarray(row, dtype=float) for row in triangle]
    v0, v1, v2 = c - a, b - a, p - a
    dot00 = float(np.dot(v0, v0))
    dot01 = float(np.dot(v0, v1))
    dot02 = float(np.dot(v0, v2))
    dot11 = float(np.dot(v1, v1))
    dot12 = float(np.dot(v1, v2))
    denom = dot00 * dot11 - dot01 * dot01
    if abs(denom) <= EPS:
        return False
    u = (dot11 * dot02 - dot01 * dot12) / denom
    v = (dot00 * dot12 - dot01 * dot02) / denom
    return u >= 0.0 and v >= 0.0 and u + v <= 1.0


def cavity_section(jad: Shape, jfd: Shape, z: float) -> dict[str, object]:
    rows = [*jad.intersect(Plane.XY.offset(z)), *jfd.intersect(Plane.XY.offset(z))]
    if len(rows) < 2:
        return {"zMm": z, "valid": False}
    merged = rows[0].fuse(rows[1]).clean()
    wires = merged.wires()
    if len(wires) < 2:
        return {"zMm": z, "valid": False, "wireCount": len(wires)}
    wire_faces = [(wire, abs(float(Face(wire).area))) for wire in wires]
    inner_wire, inner_area = min(wire_faces, key=lambda row: row[1])
    bbox = inner_wire.bounding_box()
    return {
        "zMm": z,
        "valid": True,
        "innerAreaMm2": inner_area,
        "innerBoundingBoxMm": {
            "x": [float(bbox.min.X), float(bbox.max.X)],
            "y": [float(bbox.min.Y), float(bbox.max.Y)],
        },
        "innerBoundingSizeMm": [float(bbox.size.X), float(bbox.size.Y)],
    }


def reserve_metrics(shape: Shape, shells: list[Shape], obstacles: list[Shape]) -> dict[str, object]:
    return {
        "label": shape.label,
        "volumeMm3": float(shape.volume),
        "shellIntersectionMm3": sum(intersection_volume(shape, shell) for shell in shells),
        "mechanicalIntersectionMm3": sum(intersection_volume(shape, row) for row in obstacles),
        "bboxMm": {
            "min": [float(shape.bounding_box().min.X), float(shape.bounding_box().min.Y), float(shape.bounding_box().min.Z)],
            "max": [float(shape.bounding_box().max.X), float(shape.bounding_box().max.Y), float(shape.bounding_box().max.Z)],
        },
    }


def route_from_points(points: tuple[tuple[float, float, float], ...], width: float, label: str) -> list[Shape]:
    rows = []
    for index, (start, end) in enumerate(zip(points[:-1], points[1:]), 1):
        rows.append(oriented_box_between(
            start, end, (1.0, 0.0, 0.0), width, width,
            label=f"{label}_{index}",
        ))
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_validation = json.loads(SOURCE_VALIDATION.read_text(encoding="utf-8"))
    reference = import_step(REFERENCE_STEP)
    jad = import_step(JAD_STEP)
    jfd = import_step(JFD_STEP)

    screws = {
        f"screw_{index}": build_fastener_screw(index, y, z)
        for index, (y, z) in enumerate(FASTENER_OPTIONS[CHOSEN_FASTENER_OPTION], 1)
    }
    before_screw_shell = screw_shell_rows(screws, jad, jfd)
    jad_bored, jfd_bored, bore_design = apply_final_fastener_bores(jad, jfd)
    after_screw_shell = screw_shell_rows(screws, jad_bored, jfd_bored)

    carrier_labels = {
        "N1_N2_V3_shared_front_carrier": "N1_N2_V3_shared_shell_captured_front_carrier",
        "N1_N2_V3_rear_restraint": "N1_N2_V3_removable_rear_restraint",
        "I2_I3_shared_carrier": "I2_I3_shared_C_channel_carrier",
        "M4_N3_shared_carrier": "M4_N3_shared_C_channel_carrier",
        "I4_carrier": "I4_C_channel_carrier",
        "M3_carrier": "M3_C_channel_carrier",
    }
    carriers = {
        name: select_children(reference, lambda label, expected=label: label == expected)[0]
        for name, label in carrier_labels.items()
    }
    switches = select_children(reference, lambda label: "ITS1105_body" in label)
    roots = select_children(reference, lambda label: "_root_" in label)
    finger_wires = select_children(reference, lambda label: "wire_service_envelope" in label or "_V3_formed_" in label or "_V3_solder_" in label or "_V3_wire_" in label)
    thumb_wires = select_children(reference, lambda label: label.startswith("THUMB_V3_wiring_corridor"))
    thumb_hardware = select_children(reference, lambda label: label in ("Backplate", "HW504_B", "Small_joystick_attachment") or label.startswith("Button_") or label == "PushBtn")
    caps = select_children(reference, lambda label: label.endswith("_cap"))

    n_rear = carriers["N1_N2_V3_rear_restraint"]
    n_front = carriers["N1_N2_V3_shared_front_carrier"]
    n_switches = select_children(reference, lambda label: label.startswith(("N1_ITS1105_body", "N2_ITS1105_body")))
    n_roots = select_children(reference, lambda label: label.startswith(("N1_root_", "N2_root_")))
    corrected_n_front, corrected_n_rear = build_noninterfering_n_pair_candidate()
    current_front_rear = exact_metrics([n_front], [n_rear])
    current_front_switch = exact_metrics([n_front], n_switches)
    current_rear_switch = exact_metrics([n_rear], n_switches)
    corrected_front_rear = exact_metrics([corrected_n_front], [corrected_n_rear])
    corrected_front_switch = exact_metrics([corrected_n_front], n_switches)
    corrected_rear_switch = exact_metrics([corrected_n_rear], n_switches)
    corrected_front_shell = exact_metrics([corrected_n_front], [jad, jfd])
    corrected_rear_shell = exact_metrics([corrected_n_rear], [jad, jfd])
    corrected_pair_thumb = exact_metrics([corrected_n_front, corrected_n_rear], thumb_hardware)

    current_thumb_to_shell = exact_metrics(thumb_wires, [jad, jfd])
    current_finger_to_shell = exact_metrics(finger_wires, [jad, jfd])
    thumb_lower_bbox = thumb_wires[-1].bounding_box()
    section_minus_35 = cavity_section(jad, jfd, -35.0)
    outer_x_at_minus_35 = 19.17

    finger_candidate = route_from_points(
        ((0.0, 4.0, -16.0), (0.0, 4.0, -24.0), (0.0, 9.0, -40.0)),
        4.0,
        "REVIEW_finger_shared_trunk",
    )
    thumb_candidate = route_from_points(
        ((9.0, 12.0, 4.0), (8.0, 7.0, -12.0), (6.0, 10.0, -32.0), (6.0, 18.0, -45.0)),
        3.2,
        "REVIEW_thumb_inboard_trunk",
    )
    hard_obstacles = [*carriers.values(), *switches, *roots, *thumb_hardware, *screws.values()]

    electronics_reserves = [
        center_box((27.0, 17.0, 6.0), (0.0, 20.0, -40.0), "MCU_IO_CONNECTOR_RESERVE"),
        center_box((16.0, 18.0, 7.0), (0.0, 27.0, -51.0), "COMPACT_BATTERY_RESERVE"),
    ]
    cavity_sections = [cavity_section(jad, jfd, z) for z in (-65.0, -55.0, -45.0, -35.0)]
    estimated_cavity_volume = sum(
        0.5 * (left["innerAreaMm2"] + right["innerAreaMm2"]) * (right["zMm"] - left["zMm"])
        for left, right in zip(cavity_sections[:-1], cavity_sections[1:])
        if left.get("valid") and right.get("valid")
    )

    fastener_triangle = FASTENER_OPTIONS[CHOSEN_FASTENER_OPTION]
    control_centers = source_validation["hardFreeze"]["fingerExternalCaps"]
    manifest = json.loads((ROOT / "build123d_workbench" / "out" / "finger_controls_v2" / "finger_controls_v2_source_manifest.json").read_text(encoding="utf-8"))
    finger_yz = {name: (row["centerMm"][1], row["centerMm"][2]) for name, row in manifest["controls"].items()}
    backplate = select_children(reference, lambda label: label == "Backplate")[0]
    back_bbox = backplate.bounding_box()
    thumb_yz = (0.5 * (float(back_bbox.min.Y) + float(back_bbox.max.Y)), 0.5 * (float(back_bbox.min.Z) + float(back_bbox.max.Z)))

    carrier_map = {
        "I2_I3_shared_carrier": {"role": "I2/I3 switch pocket, rear plate and terminal exits", "shell": "JfD", "removable": True, "location": "two frozen switch axes + JfD wall capture", "fixing": "shell closure; broad C-channel", "assembly": "pre-wire/load from opposite open ends, insert from seam", "classification": "KEEP AS-IS"},
        "I4_carrier": {"role": "independent I4 switch cradle", "shell": "JaD", "removable": True, "location": "I4 axis + JaD local wall", "fixing": "shell closure; broad C-channel", "assembly": "pre-wire, insert from seam", "classification": "KEEP AS-IS"},
        "M3_carrier": {"role": "independent M3 switch cradle", "shell": "JfD", "removable": True, "location": "M3 axis + JfD local wall", "fixing": "shell closure; broad C-channel", "assembly": "pre-wire, insert from seam", "classification": "KEEP AS-IS"},
        "M4_N3_shared_carrier": {"role": "two-switch JaD cradle with opposite-end loading", "shell": "JaD", "removable": True, "location": "M4/N3 axes + split-trim datum", "fixing": "shell closure; broad shared carrier", "assembly": "pre-wire/load from opposite ends, insert from seam", "classification": "KEEP AS-IS"},
        "N1_N2_V3_shared_front_carrier": {"role": "front locating rings for N1/N2", "shell": "JfD locating / JaD clearance", "removable": True, "location": "N1/N2 axes and JfD locating relief", "fixing": "shell closure", "assembly": "insert wired switches axially before shell close", "classification": "REDESIGN RECOMMENDED with broad rear-restraint key"},
        "N1_N2_V3_rear_restraint": {"role": "rear axial stop while clearing four terminal roots", "shell": "floating between halves", "removable": True, "location": "switch rear faces only", "fixing": "claimed shell capture, but 0.925 mm shell gap and no positive key", "assembly": "loose piece placed after soldering", "classification": "REDESIGN RECOMMENDED"},
    }

    report = {
        "schema": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOCAL build123d + OCCT review only; STL 0 / print plate 0 / Onshape 0 / production overwrite 0",
        "hardFreeze": {
            "fingerCentersMovementMm": {name: 0.0 for name in control_centers},
            "thumbTranslationMm": [0.0, 12.25, -21.0],
            "externalGeometryChanged": False,
        },
        "carrierMap": carrier_map,
        "carrierCountReview": {
            "currentCount": 6,
            "keepIndependentOrShared": ["I2_I3_shared_carrier", "I4_carrier", "M3_carrier", "M4_N3_shared_carrier"],
            "doNotMerge": "different owner shells, axes, insertion directions and service paths make a larger monolithic carrier worse",
            "NPairRecommendation": "keep a two-stage front/rear concept, but add a broad non-snap keyed guide and reduce rear float; do not use hooks/rails/tiny snaps",
        },
        "N1N2": {
            "actualV3SwitchFrontDepthMm": {"N1": 1.2, "N2": 1.2},
            "currentFrontRingRearExtensionPastSwitchMm": 0.71,
            "currentRearBridgeSectionMm": 2.4,
            "currentFrontToRear": current_front_rear,
            "currentFrontToSwitchBodies": current_front_switch,
            "currentRearToSwitchBodies": current_rear_switch,
            "rearToCompleteShellClearanceMm": source_validation["clearances"]["NRearRestraintToShell"]["minimumClearanceMm"],
            "frontToOppositeJaDClearanceMm": source_validation["clearances"]["N2CarrierToOppositeJaD"]["minimumClearanceMm"],
            "rearToSwitch": exact_metrics([n_rear], n_switches),
            "rearToTerminalRoots": exact_metrics([n_rear], n_roots),
            "positiveRearKeyCount": 0,
            "loosePartDuringOpenShellAssembly": True,
            "finding": "the current front ring extends behind the switch while the outer-width rear straps enter the same zone; the 2.40 mm rear bridge also extends toward the switch. The current front/rear and rear/switch solids positively overlap, and the rear part is not keyed",
            "noninterferingReviewCandidate": {
                "frontValid": bool(corrected_n_front.is_valid),
                "rearValid": bool(corrected_n_rear.is_valid),
                "frontSolidCount": len(corrected_n_front.solids()),
                "rearSolidCount": len(corrected_n_rear.solids()),
                "frontVolumeMm3": float(corrected_n_front.volume),
                "rearVolumeMm3": float(corrected_n_rear.volume),
                "frontToRear": corrected_front_rear,
                "frontToSwitchBodies": corrected_front_switch,
                "rearToSwitchBodies": corrected_rear_switch,
                "frontToShell": corrected_front_shell,
                "rearToShell": corrected_rear_shell,
                "pairToThumb": corrected_pair_thumb,
            },
            "recommendedChange": "shorten the front support so it does not pass the switch rear, move the rear bridge fully behind the switch, recut terminal roots, then add two broad keyed cheeks/T-guide >=1.60 mm wall and >=3.0 mm engagement with 0.25-0.40 mm closed-shell float",
        },
        "N2Seam": {
            "JfD": "locating shell",
            "JaD": "clearance/capture only",
            "frontCarrierToOppositeJaDMm": 1.0541709029625572,
            "rearRestraintToCompleteShellMm": 0.9246960915587177,
            "jamMarginAboveGateMm": 1.0541709029625572 - 0.80,
            "classification": "KEEP AS-IS for cap/front locator; rear restraint handled separately",
        },
        "thumbSeat": {
            "frameMm": {"outer": [42.0, 64.0], "inner": [34.0, 56.0], "wall": 1.60},
            "padCount": 3,
            "padSizeMm": 5.0,
            "padReachMm": 4.8,
            "seatVolumeMm3": source_validation["fragments"]["JaD"]["volumeMm3"] + source_validation["fragments"]["JfD"]["volumeMm3"],
            "threePointPlaneDefinition": True,
            "modeledContactClearanceMm": 0.0,
            "definedOpposingPreloadFeature": False,
            "finding": "non-collinear three-point support is good, but exact conformal contact plus undefined opposite preload is tolerance-sensitive",
            "recommendedChange": "retain frame/pads; parameterize 0.15-0.25 mm assembly clearance and one broad compliant preload/shim zone",
        },
        "fastening": {
            "option": CHOSEN_FASTENER_OPTION,
            "positionsYZMm": [list(row) for row in fastener_triangle],
            "triangleAreaMm2": yz_triangle_area(fastener_triangle),
            "allFingerCentersInsideClampTriangle": all(point_in_triangle(point, fastener_triangle) for point in finger_yz.values()),
            "thumbBackplateCenterInsideClampTriangle": point_in_triangle(thumb_yz, fastener_triangle),
            "maximumFingerCenterToNearestScrewMm": max(min(math.dist(point, screw) for screw in fastener_triangle) for point in finger_yz.values()),
            "beforeFinalBoreScrewShellIntersections": before_screw_shell,
            "candidateFinalBore": bore_design,
            "afterFinalBoreScrewShellIntersections": after_screw_shell,
            "candidateShellValidity": {"JaD": bool(jad_bored.is_valid), "JfD": bool(jfd_bored.is_valid)},
            "candidateShellSolidCount": {"JaD": len(jad_bored.solids()), "JfD": len(jfd_bored.solids())},
            "hardwareComparison": {
                "A_heatSetInsert": {"repeatDisassembly": "BEST", "FDMStrength": "BEST if installed across layers with 2.3 mm radial wall", "space": "moderate", "assembly": "controlled iron installation", "availability": "high", "rank": 1},
                "B_capturedNut": {"repeatDisassembly": "GOOD", "FDMStrength": "GOOD", "space": "largest trap and access", "assembly": "nut handling can be blind", "availability": "high", "rank": 2},
                "C_selfTapping": {"repeatDisassembly": "POOR", "FDMStrength": "material/layer dependent", "space": "small", "assembly": "easy first build", "availability": "high", "rank": 3},
            },
            "recommendedHardware": "M3 heat-set insert + M3 machine screw; keep insert OD/length and screw length parameterized until actual SKU measurement",
            "finding": "boss spacing avoids controls, but current final shells refill parts of the pre-bored axes and the clamp triangle does not surround the control load region",
        },
        "wiring": {
            "currentFingerToShell": current_finger_to_shell,
            "currentThumbToShell": current_thumb_to_shell,
            "fingerModelEndsAtLocalCarrierServiceEnvelopes": True,
            "fingerSharedTrunkToElectronicsModeled": False,
            "currentN1ShellPenetratingSegments": {
                "N1_V3_solder_-1_-1": 2.991088,
                "N1_V3_wire_-1_-1": 22.972703,
                "N1_V3_solder_-1_+1": 2.556758,
                "N1_V3_wire_-1_+1": 19.516099,
            },
            "thumbLowerCorridorBBoxXmm": [float(thumb_lower_bbox.min.X), float(thumb_lower_bbox.max.X)],
            "shellOuterXAtZMinus35ApproxMm": [-outer_x_at_minus_35, outer_x_at_minus_35],
            "thumbCorridorOutsideShellByAtLeastMm": float(thumb_lower_bbox.min.X) - outer_x_at_minus_35,
            "candidateFingerTrunk": exact_metrics(finger_candidate, [jad, jfd, *hard_obstacles]),
            "candidateThumbInboardTrunk": exact_metrics(thumb_candidate, [jad, jfd, *hard_obstacles]),
            "candidateThumbTrunkStart": "3.2 mm harness envelope from an internal service-loop handoff; exact thumb PCB/terminal branch remains hardware-dependent",
            "recommendation": "replace the present envelopes with open shell channels: >=6 x 4 mm finger channel around the 4 mm trunk envelope and >=4 x 4 mm thumb channel around the 3.2 mm harness envelope, bend radius >=4 mm, no tiny clips; validate actual conductor count and OD",
        },
        "electronicsSpace": {
            "cavitySections": cavity_sections,
            "estimatedCavityVolumeZMinus65ToMinus35Mm3": estimated_cavity_volume,
            "reserves": [reserve_metrics(shape, [jad, jfd], hard_obstacles) for shape in electronics_reserves],
            "finding": "a lower-handle bay remains and accepts collision-free 27x17x6 mm board plus 16x18x7 mm compact-battery reserves; battery capacity, mounting datum and connector access remain undefined",
        },
        "loadPaths": {
            "finger": "cap -> ITS actuator/body -> carrier rear plate/walls -> owner shell",
            "thumb": "thumb module/backplate -> three datum pads/flange -> both shell halves -> shell screws",
            "shellClamp": "screw head shoulder -> JfD boss/web -> seam -> JaD boss -> heat-set insert",
            "risks": ["unkeyed N rear restraint", "pre-bore boolean order", "one-sided clamp triangle", "undefined thumb preload", "unmodeled complete wire trunks"],
        },
        "assembly": {
            "recommendedOrder": [
                "install heat-set inserts into open JaD with a depth stop and inspect all bores",
                "pre-wire and load I2/I3, I4, M3 and M4/N3 carrier modules",
                "pre-wire N1/N2, insert into front carrier, then install the revised broad-key rear restraint",
                "route all Finger branches into the broad open shared trunk and apply temporary removable tape at two broad zones",
                "pre-wire and seat the thumb module against three datum pads; install the broad preload shim if used",
                "route the thumb cable into the inboard posterior channel",
                "place electronics/battery into reserved lower bay and connect before final close",
                "close JfD onto JaD while visually monitoring both broad channels",
                "install three M3 screws only after all seams are fully seated",
            ],
            "currentBlindOperations": ["holding the loose N rear restraint", "keeping uncontained wire bundles out of the seam", "confirming thumb preload during closure"],
        },
        "service": {
            "fingerSwitch": "possible after shell opening; four established carriers are practical",
            "N1N2Switch": "CAD-removable but loose rear part makes actual handling awkward",
            "thumbModule": "removable after shell opening; exact-contact seat may stick",
            "wiringRepair": "local solder joints visible, but complete trunk and service loop are not defined",
        },
        "classification": {
            "I2_I3_carrier": "KEEP AS-IS",
            "I4_carrier": "KEEP AS-IS",
            "M3_carrier": "KEEP AS-IS",
            "M4_N3_carrier": "KEEP AS-IS",
            "N1_N2_carrier": "REDESIGN RECOMMENDED",
            "N2_seam": "KEEP AS-IS",
            "thumb_seat": "MINOR IMPROVEMENT",
            "screw_fastening": "REDESIGN RECOMMENDED",
            "Finger_wiring": "REDESIGN RECOMMENDED",
            "Thumb_wiring": "REDESIGN RECOMMENDED",
            "shell_integration": "MINOR IMPROVEMENT",
        },
        "changesActuallyMade": {
            "productionV3Changed": False,
            "reviewOnlyCandidate": "final screw clearance/counterbore/insert cutters applied after boss-shell union",
            "STLGenerated": False,
            "printPlateGenerated": False,
            "reasonOtherChangesNotApplied": "N rear key, clamp redistribution, thumb preload and full wiring channels interact with assembly and hardware choices; changing all at once would violate the staged-review policy",
        },
        "finalVerdict": {
            "INTERNAL ARCHITECTURE": "REVISE",
            "N1/N2": "REVISE",
            "N2 SEAM": "ACCEPT",
            "THUMB SEATING": "REVISE",
            "FASTENING": "REVISE",
            "WIRING": "REVISE",
            "ASSEMBLY": "REVISE",
            "SERVICEABILITY": "REVISE",
            "STRUCTURE": "REVISE",
            "FDM REALISM": "REVISE",
            "ELECTRONICS SPACE": "ACCEPT",
            "BASELINE": "NO",
        },
    }

    output = OUT_DIR / "integrated_v3_internal_design_review.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "screwShellBeforeMm3": {name: row["totalIntersectionMm3"] for name, row in before_screw_shell.items()},
        "screwShellAfterMm3": {name: row["totalIntersectionMm3"] for name, row in after_screw_shell.items()},
        "candidateShellValidity": report["fastening"]["candidateShellValidity"],
        "candidateWiring": {
            "finger": report["wiring"]["candidateFingerTrunk"],
            "thumb": report["wiring"]["candidateThumbInboardTrunk"],
        },
        "electronics": report["electronicsSpace"]["reserves"],
        "verdict": report["finalVerdict"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
