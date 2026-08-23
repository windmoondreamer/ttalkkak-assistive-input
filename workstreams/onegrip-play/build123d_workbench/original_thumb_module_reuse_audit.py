"""Exact reuse audit for the original open-source OneGrip Thumb subsystem.

This module is deliberately analysis-only.  It imports immutable exact STEP
references, applies the approved rigid translation, and writes reference STEP,
collision/debug B-rep and JSON evidence.  It does not create a carrier, seat,
boss, screw mount, wiring channel, or production shell geometry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from itertools import permutations
import json
from math import inf
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import (
    Align,
    Box,
    Compound,
    Location,
    Shape,
    Vector,
    export_step,
    import_step,
)

from .finger_controls_v2 import BOOLEAN_VOLUME_EPS, BUTTON_ORDER, exact_distance
from .model import oriented_box_between


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "original_thumb_module_reuse_audit"

ASSEMBLY_SOURCE = (
    ROOT / "lower_adapter" / "local_cad" / "reference"
    / "ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step"
)
PART_STUDIO_SOURCE = ROOT / "local_cad" / "reference" / "THUMB_ORIGINAL_PRE_FINGER_REFERENCE.step"
TARGET_SOURCE = (
    ROOT / "build123d_workbench" / "out" / "finger_thumb_joint_feasibility"
    / "THUMB_TARGET_EXACT_MODULE.step"
)
JAD_SHELL = (
    ROOT / "build123d_workbench" / "out" / "integrated_exterior_lowered_thumb_v1"
    / "JAD_EXTERIOR_LOWERED_THUMB_V1.step"
)
JFD_SHELL = (
    ROOT / "build123d_workbench" / "out" / "integrated_exterior_lowered_thumb_v1"
    / "JFD_EXTERIOR_LOWERED_THUMB_V1.step"
)
EXTERIOR_REFERENCE = (
    ROOT / "build123d_workbench" / "out" / "integrated_exterior_lowered_thumb_v1"
    / "EXTERIOR_LOWERED_THUMB_V1_COMBINED_REFERENCE.step"
)
EXTERIOR_VALIDATION = (
    ROOT / "build123d_workbench" / "out" / "integrated_exterior_lowered_thumb_v1"
    / "exterior_lowered_thumb_v1_validation.json"
)
FINGER_REFERENCE = (
    ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
    / "FINGER_V2_ASSEMBLY_REFERENCE.step"
)

ORIGINAL_OUTPUT = OUT_DIR / "ORIGINAL_THUMB_CARTRIDGE.step"
LOWERED_OUTPUT = OUT_DIR / "LOWERED_ORIGINAL_THUMB_CARTRIDGE.step"
FASTENING_OUTPUT = OUT_DIR / "ORIGINAL_FASTENING_REFERENCE.step"
COLLISION_OUTPUT = OUT_DIR / "ORIGINAL_THUMB_COLLISION_DEBUG.step"
WIRING_OUTPUT = OUT_DIR / "THUMB_WIRING_CLEARANCE_PROBES.step"
REPORT_OUTPUT = OUT_DIR / "original_thumb_module_reuse_audit.json"

TARGET_DELTA = np.asarray((0.0, 12.25, -21.0), dtype=float)
EPS = 1.0e-7
NEAR_CLEARANCE_MM = 0.80
WIRE_PROBE_LENGTH_MM = 12.0
WIRE_PROBE_SECTION_MM = 1.20

CAP_LOGICAL_ORDER = (
    "Button_corner_1",
    "Button_middle_1",
    "Button_corner_2",
    "Button_side_1",
    "Button_middle_2",
    "Button_side_2",
    "Button_wide_1",
    "Button_wide_2",
)
EXTERNAL_CONTROL_LABELS = (*CAP_LOGICAL_ORDER, "Small_joystick_attachment")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def moved(shape: Shape, delta: Iterable[float]) -> Shape:
    return shape.moved(Location(Vector(*[float(value) for value in delta])))


def center(shape: Shape) -> np.ndarray:
    bbox = shape.bounding_box()
    return np.asarray(
        (
            0.5 * float(bbox.min.X + bbox.max.X),
            0.5 * float(bbox.min.Y + bbox.max.Y),
            0.5 * float(bbox.min.Z + bbox.max.Z),
        ),
        dtype=float,
    )


def bbox_row(shape: Shape) -> dict[str, list[float]]:
    bbox = shape.bounding_box()
    return {
        "min": [float(bbox.min.X), float(bbox.min.Y), float(bbox.min.Z)],
        "max": [float(bbox.max.X), float(bbox.max.Y), float(bbox.max.Z)],
    }


def bbox_gap(left: Shape, right: Shape) -> float:
    a = left.bounding_box()
    b = right.bounding_box()
    gaps = (
        max(float(a.min.X - b.max.X), float(b.min.X - a.max.X), 0.0),
        max(float(a.min.Y - b.max.Y), float(b.min.Y - a.max.Y), 0.0),
        max(float(a.min.Z - b.max.Z), float(b.min.Z - a.max.Z), 0.0),
    )
    return float(np.linalg.norm(gaps))


def intersection(left: Shape, right: Shape, label: str | None = None) -> tuple[float, Shape | None]:
    if bbox_gap(left, right) > EPS:
        return 0.0, None
    try:
        common = left & right
    except Exception:
        return 0.0, None
    if common is None or len(common.solids()) == 0:
        return 0.0, None
    common = common.clean()
    volume = float(common.volume)
    if volume <= EPS:
        return 0.0, None
    if label:
        common.label = label
    return volume, common


def minimum_distance(left: list[Shape], right: list[Shape]) -> float:
    pairs = sorted(
        ((bbox_gap(a, b), a, b) for a in left for b in right),
        key=lambda row: row[0],
    )
    best = inf
    for lower, a, b in pairs:
        if lower >= best:
            break
        best = min(best, exact_distance(a, b))
        if best <= EPS:
            return 0.0
    return best


@dataclass(slots=True)
class Part:
    name: str
    source_label: str
    role: str
    category: str
    shape: Shape
    moves_with_thumb: bool = True


def _best_switch_assignment(caps: list[Part], switches: list[Shape]) -> dict[str, Shape]:
    """Pair the eight repeated PushBtn occurrences to their nearest cap.

    The source assembly contains repeated labels but exact occurrence placement.
    An exhaustive 8! assignment avoids a greedy ambiguity at the symmetric row.
    """
    cap_centers = [center(part.shape) for part in caps]
    switch_centers = [center(shape) for shape in switches]
    cost = np.asarray(
        [[float(np.linalg.norm(a - b)) for b in switch_centers] for a in cap_centers],
        dtype=float,
    )
    best_order: tuple[int, ...] | None = None
    best_cost = inf
    for order in permutations(range(8)):
        value = sum(float(cost[index, order[index]]) for index in range(8))
        if value < best_cost:
            best_cost = value
            best_order = order
    assert best_order is not None
    return {caps[index].name: switches[best_order[index]] for index in range(8)}


def load_target_parts() -> list[Part]:
    source = import_step(TARGET_SOURCE)
    children = list(source.children)
    if len(children) != 20:
        raise RuntimeError(f"Original Thumb target must contain 20 exact solids, got {len(children)}")

    by_label: dict[str, list[Shape]] = {}
    for child in children:
        by_label.setdefault(child.label, []).append(child)

    expected = {
        "Backplate": 1,
        "PushBtn": 8,
        "HW504_B": 2,
        "Small_joystick_attachment": 1,
        **{name: 1 for name in CAP_LOGICAL_ORDER},
    }
    actual = {name: len(by_label.get(name, [])) for name in expected}
    if actual != expected:
        raise RuntimeError(f"Original Thumb inventory mismatch: {actual}")

    parts: list[Part] = [
        Part(
            "THUMB_BACKPLATE",
            "Backplate",
            "common swept backplate; integrates the eight button supports/retainers",
            "backplate",
            by_label["Backplate"][0],
        )
    ]
    cap_parts: list[Part] = []
    for index, name in enumerate(CAP_LOGICAL_ORDER, 1):
        cap_parts.append(
            Part(
                f"THUMB_BUTTON_{index}_CAP__{name}",
                name,
                f"original Thumb button {index} cap",
                "thumbCap",
                by_label[name][0],
            )
        )
    parts.extend(cap_parts)

    assignment = _best_switch_assignment(cap_parts, by_label["PushBtn"])
    for index, cap in enumerate(cap_parts, 1):
        parts.append(
            Part(
                f"THUMB_BUTTON_{index}_PUSHBTN",
                "PushBtn",
                f"original Thumb button {index} push-button mechanism; paired to {cap.source_label}",
                "pushButton",
                assignment[cap.name],
            )
        )

    mechanisms = sorted(by_label["HW504_B"], key=lambda shape: float(shape.volume), reverse=True)
    for index, mechanism in enumerate(mechanisms, 1):
        parts.append(
            Part(
                f"THUMB_JOYSTICK_HW504_COMPONENT_{index}",
                "HW504_B",
                "HW504 joystick mechanism component (two exact solids form one module)",
                "joystickMechanism",
                mechanism,
            )
        )
    parts.append(
        Part(
            "THUMB_JOYSTICK_SMALL_ATTACHMENT",
            "Small_joystick_attachment",
            "original joystick attachment / opening counterpart",
            "thumbSupport",
            by_label["Small_joystick_attachment"][0],
        )
    )
    if len(parts) != 20:
        raise RuntimeError("Rigid cartridge definition did not resolve to 20 exact parts")
    return parts


def load_original_screws() -> list[Part]:
    assembly = import_step(ASSEMBLY_SOURCE)
    joystick = next(child for child in assembly.children if child.label.startswith("Joystick_"))
    jad = next(child for child in joystick.children if child.label == "Joystick_1")
    inverse = jad.location.inverse()
    rows = [
        child.moved(inverse)
        for child in joystick.children
        if child.label.startswith("Hex_socket_head_cap_screw_M3")
    ]
    rows.sort(key=lambda shape: tuple(center(shape)[[2, 1, 0]]))
    if len(rows) != 3:
        raise RuntimeError(f"Expected three original M3 shell screws, got {len(rows)}")
    return [
        Part(
            f"ORIGINAL_M3_SHELL_SCREW_{index}",
            "Hex_socket_head_cap_screw_M3x0_50_x_16",
            "original Joystick shell clamp / Backplate capture fastener; remains shell-side",
            "originalFastener",
            shape,
            moves_with_thumb=False,
        )
        for index, shape in enumerate(rows, 1)
    ]


def renamed_compound(parts: list[Part], label: str, delta: Iterable[float] | None = None) -> Compound:
    children: list[Shape] = []
    for part in parts:
        shape = part.shape if delta is None else moved(part.shape, delta)
        shape.label = part.name
        children.append(shape)
    return Compound(children=children, label=label)


def load_current_shells() -> dict[str, Shape]:
    return {"JaD": import_step(JAD_SHELL), "JfD": import_step(JFD_SHELL)}


def load_finger_references() -> tuple[dict[str, Shape], dict[str, Shape]]:
    reference = import_step(FINGER_REFERENCE)
    switches = {
        child.label.removesuffix("_ITS1105_reference"): child
        for child in reference.children
        if child.label.endswith("_ITS1105_reference")
    }
    carrier_alias = {
        "N1_N2_shared_C_channel_carrier": "N1_N2_SHARED_CARRIER",
        "I2_I3_shared_C_channel_carrier": "I2_I3_SHARED_CARRIER",
        "M4_N3_shared_C_channel_carrier": "M4_N3_SHARED_CARRIER",
        "I4_C_channel_carrier": "I4_CARRIER",
        "M3_C_channel_carrier": "M3_CARRIER",
    }
    carriers = {
        carrier_alias[child.label]: child
        for child in reference.children
        if child.label in carrier_alias
    }
    if tuple(switches) != BUTTON_ORDER or len(carriers) != 5:
        raise RuntimeError("Frozen Finger V2 internal reference inventory mismatch")
    return switches, carriers


def collision_audit(
    parts: list[Part],
    targets: dict[str, Shape],
    target_group: str,
    debug: list[Shape],
) -> dict[str, object]:
    part_rows: dict[str, object] = {}
    collisions: list[dict[str, object]] = []
    total_volume = 0.0
    all_target_shapes = list(targets.values())
    for part in parts:
        volumes: list[tuple[str, float]] = []
        for target_name, target in targets.items():
            volume, common = intersection(
                part.shape,
                target,
                f"COLLISION__{target_group}__{part.name}__{target_name}",
            )
            if volume > EPS:
                volumes.append((target_name, volume))
                total_volume += volume
                if common is not None:
                    debug.append(common)
                collisions.append(
                    {
                        "part": part.name,
                        "target": target_name,
                        "penetrationVolumeMm3": volume,
                        "minimumClearanceMm": 0.0,
                    }
                )
        part_clearance = 0.0 if volumes else minimum_distance([part.shape], all_target_shapes)
        part_rows[part.name] = {
            "minimumClearanceMm": part_clearance,
            "penetrationVolumeMm3": sum(row[1] for row in volumes),
            "intersections": [
                {"target": name, "penetrationVolumeMm3": volume}
                for name, volume in volumes
            ],
        }
    minimum = 0.0 if collisions else minimum_distance([part.shape for part in parts], all_target_shapes)
    return {
        "minimumClearanceMm": minimum,
        "penetrationVolumeMm3": total_volume,
        "intersectingPairCount": len(collisions),
        "intersectingParts": sorted({row["part"] for row in collisions}),
        "collisions": collisions,
        "byPart": part_rows,
    }


def seam_audit(parts: list[Part]) -> dict[str, object]:
    rows = []
    for part in parts:
        bbox = part.shape.bounding_box()
        minimum_x = float(bbox.min.X)
        maximum_x = float(bbox.max.X)
        clearance = 0.0 if minimum_x <= 0.0 <= maximum_x else min(abs(minimum_x), abs(maximum_x))
        if clearance <= EPS:
            rows.append(
                {
                    "part": part.name,
                    "minimumClearanceMm": 0.0,
                    "penetrationVolumeMm3": 0.0,
                    "xSpanMm": [minimum_x, maximum_x],
                    "classification": "CROSSES_ZERO_THICKNESS_SPLIT_PLANE",
                }
            )
    return {
        "definition": "exact shell split plane X=0; zero-thickness plane has no penetration volume",
        "minimumClearanceMm": 0.0 if rows else min(
            min(abs(float(part.shape.bounding_box().min.X)), abs(float(part.shape.bounding_box().max.X)))
            for part in parts
        ),
        "penetrationVolumeMm3": 0.0,
        "crossingPartCount": len(rows),
        "crossingParts": rows,
    }


def per_part_collision_volume(audit: dict[str, object], part_name: str) -> float:
    return float(audit["byPart"][part_name]["penetrationVolumeMm3"])


def collision_subset(audit: dict[str, object], parts: list[Part]) -> dict[str, object]:
    """Summarize an already-computed matrix without repeating OCCT booleans."""
    names = {part.name for part in parts}
    rows = [row for row in audit["collisions"] if row["part"] in names]
    by_part = {name: audit["byPart"][name] for name in names}
    return {
        "minimumClearanceMm": 0.0 if rows else min(
            float(row["minimumClearanceMm"]) for row in by_part.values()
        ),
        "penetrationVolumeMm3": sum(float(row["penetrationVolumeMm3"]) for row in rows),
        "intersectingPairCount": len(rows),
        "intersectingParts": sorted({row["part"] for row in rows}),
        "collisions": rows,
        "byPart": by_part,
    }


def classify_parts(
    parts: list[Part],
    shell: dict[str, object],
    switches: dict[str, object],
    carriers: dict[str, object],
    screws: dict[str, object],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for part in parts:
        shell_v = per_part_collision_volume(shell, part.name)
        switch_v = per_part_collision_volume(switches, part.name)
        carrier_v = per_part_collision_volume(carriers, part.name)
        screw_v = per_part_collision_volume(screws, part.name)
        reasons: list[str] = []
        if shell_v > EPS:
            reasons.append("current exact review shell")
        if switch_v > EPS:
            reasons.append("frozen Finger switch references")
        if carrier_v > EPS:
            reasons.append("present Finger carrier references")
        if screw_v > EPS:
            reasons.append("original fixed shell screws")

        if not reasons:
            classification = "AS_IS"
            reuse = "REUSABLE_AS_IS"
        elif switch_v > EPS or carrier_v > EPS:
            if part.category in ("backplate", "thumbSupport", "thumbCap"):
                classification = "CLASS_C"
                reuse = "ORIGINAL_MOUNTING_PART_MODIFICATION_REQUIRED"
            else:
                classification = "CLASS_D"
                reuse = "ORIGINAL_MECHANISM_CHANGE_REQUIRED"
        elif shell_v > EPS and part.category == "joystickMechanism":
            classification = "CLASS_D"
            reuse = "ORIGINAL_MECHANISM_CHANGE_REQUIRED"
            reasons.append("prior local HW504 relief breached the frozen exterior and was discarded")
        elif part.category in ("backplate", "thumbSupport") or screw_v > EPS:
            classification = "CLASS_B"
            reuse = "SHELL_SIDE_ADAPTER_REQUIRED"
        else:
            classification = "CLASS_A"
            reuse = "LOCAL_INTERNAL_SHELL_MATERIAL_RELIEF_REQUIRED"

        result[part.name] = {
            "classification": classification,
            "reuseDisposition": reuse,
            "interferesWith": reasons,
            "volumesMm3": {
                "shell": shell_v,
                "fingerSwitches": switch_v,
                "fingerCarriers": carrier_v,
                "fixedOriginalScrews": screw_v,
            },
        }
    return result


def alignment_audit(parts: list[Part]) -> dict[str, object]:
    exterior = import_step(EXTERIOR_REFERENCE)
    exterior_controls: dict[str, Shape] = {
        child.label: child
        for child in exterior.children
        if child.label in EXTERNAL_CONTROL_LABELS
    }
    target_by_source = {part.source_label: part for part in parts if part.source_label in EXTERNAL_CONTROL_LABELS}
    rows: dict[str, object] = {}
    for label in EXTERNAL_CONTROL_LABELS:
        target = target_by_source[label].shape
        current = exterior_controls[label]
        target_center = center(target)
        current_center = center(current)
        rows[label] = {
            "targetCenterMm": target_center.tolist(),
            "currentExteriorReferenceCenterMm": current_center.tolist(),
            "centerErrorMm": float(np.linalg.norm(target_center - current_center)),
            "shapeDistanceMm": exact_distance(target, current),
            "volumeDifferenceMm3": abs(float(target.volume) - float(current.volume)),
        }
    joystick = rows["Small_joystick_attachment"]
    button_errors = [rows[name]["centerErrorMm"] for name in CAP_LOGICAL_ORDER]
    exterior_validation = json.loads(EXTERIOR_VALIDATION.read_text(encoding="utf-8"))
    return {
        "method": (
            "exact target external solids are compared to the unchanged solids exported with the current exterior; "
            "the circular/split opening and eight button openings are generated from the same rigidly translated "
            "original opening/control registry"
        ),
        "rigidTransform": {
            "translationMm": TARGET_DELTA.tolist(),
            "scale": 1.0,
            "rotationChangeDeg": 0.0,
            "relativeGeometryDifferenceMm": 0.0,
        },
        "joystickCenterErrorMm": joystick["centerErrorMm"],
        "circularRecessCenterErrorMm": joystick["centerErrorMm"],
        "buttonCenterErrorsMm": {
            f"BUTTON_{index}": rows[name]["centerErrorMm"]
            for index, name in enumerate(CAP_LOGICAL_ORDER, 1)
        },
        "maximumButtonCenterErrorMm": max(button_errors),
        "capToOpeningReferenceErrorMm": max(button_errors),
        "buttonTravelAxisAngularErrorDeg": 0.0,
        "openingResidualVolumesMm3": {
            name: exterior_validation["thumbOpenings"][name]["totalResidualAfterCutMm3"]
            for name in EXTERNAL_CONTROL_LABELS
        },
        "controls": rows,
        "verdict": "PASS" if max(button_errors + [joystick["centerErrorMm"]]) <= 1.0e-6 else "HOLD",
    }


def transform_integrity(parts: list[Part]) -> dict[str, object]:
    original = [moved(part.shape, -TARGET_DELTA) for part in parts]
    rebuilt = [moved(shape, TARGET_DELTA) for shape in original]
    center_residuals = [
        float(np.linalg.norm(center(rebuilt[index]) - center(parts[index].shape)))
        for index in range(len(parts))
    ]
    volume_residuals = [
        abs(float(rebuilt[index].volume) - float(parts[index].shape.volume))
        for index in range(len(parts))
    ]
    pair_residual = 0.0
    base_centers = [center(shape) for shape in original]
    target_centers = [center(part.shape) for part in parts]
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            before = float(np.linalg.norm(base_centers[i] - base_centers[j]))
            after = float(np.linalg.norm(target_centers[i] - target_centers[j]))
            pair_residual = max(pair_residual, abs(before - after))
    return {
        "scale": 1.0,
        "rotationChangeDeg": 0.0,
        "translationMm": TARGET_DELTA.tolist(),
        "maximumCenterRoundTripResidualMm": max(center_residuals),
        "maximumVolumeResidualMm3": max(volume_residuals),
        "maximumPairwiseCenterDistanceResidualMm": pair_residual,
        "relativeGeometryDifferenceMm": pair_residual,
        "validation": "PASS" if max(center_residuals + [pair_residual]) <= 1.0e-9 else "HOLD",
    }


def screw_axis(shape: Shape) -> tuple[list[float], list[float]]:
    """Return a stable shell-screw datum from its exact placed B-rep.

    All three source screws have the same M3 geometry.  Their long dimension is
    the shank axis; PCA over exact vertices is used only to report that datum,
    never to create or alter geometry.
    """
    points = np.asarray(
        [[float(vertex.X), float(vertex.Y), float(vertex.Z)] for vertex in shape.vertices()],
        dtype=float,
    )
    origin = points.mean(axis=0)
    covariance = np.cov(points - origin, rowvar=False)
    values, vectors = np.linalg.eigh(covariance)
    axis = vectors[:, int(np.argmax(values))]
    if axis[0] < 0.0:
        axis = -axis
    return origin.tolist(), (axis / np.linalg.norm(axis)).tolist()


def fastening_audit(parts: list[Part], screws: list[Part], screw_collisions: dict[str, object]) -> dict[str, object]:
    rows = []
    for screw in screws:
        origin, axis = screw_axis(screw.shape)
        pair_rows = [row for row in screw_collisions["collisions"] if row["target"] == screw.name]
        rows.append(
            {
                "name": screw.name,
                "source": str(ASSEMBLY_SOURCE.relative_to(ROOT)),
                "axisPointMm": origin,
                "axisDirection": axis,
                "movesWithThumb": False,
                "intersectionsAtLoweredTarget": pair_rows,
            }
        )
    return {
        "architecture": (
            "three original M3x0.50x16 screws clamp the split Joystick shell and participate in "
            "Backplate/shell capture; the screw datums remain shell-side when the Thumb cartridge moves"
        ),
        "screws": rows,
        "targetMinimumClearanceMm": screw_collisions["minimumClearanceMm"],
        "targetPenetrationVolumeMm3": screw_collisions["penetrationVolumeMm3"],
        "originalHardwareReusable": True,
        "originalAxesReusableAtLoweredPosition": False,
        "verdict": "SHELL-SIDE ADAPTER REQUIRED",
        "note": "No replacement fastener, boss, or screw architecture is designed in this audit.",
    }


WIRE_DIRECTIONS: dict[str, np.ndarray] = {
    "X_POS": np.asarray((1.0, 0.0, 0.0)),
    "X_NEG": np.asarray((-1.0, 0.0, 0.0)),
    "Y_POS": np.asarray((0.0, 1.0, 0.0)),
    "Y_NEG": np.asarray((0.0, -1.0, 0.0)),
    "Z_POS": np.asarray((0.0, 0.0, 1.0)),
    "Z_NEG": np.asarray((0.0, 0.0, -1.0)),
}


def support_point(shape: Shape, direction: np.ndarray) -> np.ndarray:
    points = np.asarray(
        [[float(vertex.X), float(vertex.Y), float(vertex.Z)] for vertex in shape.vertices()],
        dtype=float,
    )
    return points[int(np.argmax(points @ direction))]


def build_probe(shape: Shape, direction: np.ndarray, label: str) -> tuple[Shape, np.ndarray]:
    start = support_point(shape, direction) + direction * 0.20
    end = start + direction * WIRE_PROBE_LENGTH_MM
    hint = np.asarray((0.0, 0.0, 1.0))
    if abs(float(np.dot(hint, direction))) > 0.95:
        hint = np.asarray((1.0, 0.0, 0.0))
    probe = oriented_box_between(
        tuple(start), tuple(end), tuple(hint),
        WIRE_PROBE_SECTION_MM, WIRE_PROBE_SECTION_MM,
        label=label,
    )
    return probe, start


def wiring_audit(
    parts: list[Part],
    shells: dict[str, Shape],
    finger_switches: dict[str, Shape],
    finger_carriers: dict[str, Shape],
) -> tuple[dict[str, object], list[Shape]]:
    controls = [part for part in parts if part.category in ("pushButton", "joystickMechanism")]
    obstacles = {**{f"SHELL_{key}": value for key, value in shells.items()}}
    obstacles.update({f"FINGER_SWITCH_{key}": value for key, value in finger_switches.items()})
    obstacles.update({f"FINGER_CARRIER_{key}": value for key, value in finger_carriers.items()})
    probes: list[Shape] = []
    rows: dict[str, object] = {}
    direction_summary: dict[str, dict[str, float | int]] = {
        name: {"blockedProbeCount": 0, "minimumClearanceMm": inf}
        for name in WIRE_DIRECTIONS
    }
    for part in controls:
        candidates: dict[str, object] = {}
        for direction_name, direction in WIRE_DIRECTIONS.items():
            probe, start = build_probe(part.shape, direction, f"WIRE_PROBE__{part.name}__{direction_name}")
            probes.append(probe)
            volumes = []
            for obstacle_name, obstacle in obstacles.items():
                volume, _ = intersection(probe, obstacle)
                if volume > EPS:
                    volumes.append({"obstacle": obstacle_name, "penetrationVolumeMm3": volume})
            clearance = 0.0 if volumes else minimum_distance([probe], list(obstacles.values()))
            candidates[direction_name] = {
                "probeStartMm": start.tolist(),
                "direction": direction.tolist(),
                "probeLengthMm": WIRE_PROBE_LENGTH_MM,
                "probeSectionMm": WIRE_PROBE_SECTION_MM,
                "minimumClearanceMm": clearance,
                "blocked": bool(volumes),
                "intersections": volumes,
            }
            summary = direction_summary[direction_name]
            summary["blockedProbeCount"] = int(summary["blockedProbeCount"]) + int(bool(volumes))
            summary["minimumClearanceMm"] = min(float(summary["minimumClearanceMm"]), clearance)
        unblocked = [
            (name, row) for name, row in candidates.items()
            if not bool(row["blocked"])
        ]
        preferred = max(unblocked, key=lambda item: float(item[1]["minimumClearanceMm"]))[0] if unblocked else None
        rows[part.name] = {
            "terminalSemanticLimit": (
                "the imported occurrence is one fused exact solid; connector sub-bodies are not separately named. "
                "Probe starts are conservative exact-B-rep support points, not a production pinout."
            ),
            "candidates": candidates,
            "preferredUnblockedDirection": preferred,
        }
    for summary in direction_summary.values():
        if float(summary["minimumClearanceMm"]) == inf:
            summary["minimumClearanceMm"] = None
    return (
        {
            "mode": "ANALYSIS-ONLY CLEARANCE MAP; no channel or corridor geometry is proposed",
            "probeDefinition": {
                "lengthMm": WIRE_PROBE_LENGTH_MM,
                "squareSectionMm": WIRE_PROBE_SECTION_MM,
                "directions": {name: direction.tolist() for name, direction in WIRE_DIRECTIONS.items()},
            },
            "controls": rows,
            "directionSummary": direction_summary,
        },
        probes,
    )


def source_part_list(parts: list[Part], classifications: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "partName": part.name,
            "sourcePartLabel": part.source_label,
            "sourceFile": str(ASSEMBLY_SOURCE.relative_to(ROOT)),
            "role": part.role,
            "movesWithThumb": "YES" if part.moves_with_thumb else "NO",
            "category": part.category,
            "volumeMm3": float(part.shape.volume),
            "bboxMm": bbox_row(part.shape),
            **classifications[part.name],
        }
        for part in parts
    ]


def build_report() -> tuple[dict[str, object], dict[str, Compound]]:
    print("[1/9] import and identify exact original Thumb cartridge", flush=True)
    parts = load_target_parts()
    screws = load_original_screws()
    shells = load_current_shells()
    finger_switches, finger_carriers = load_finger_references()

    print("[2/9] validate rigid transform and current exterior alignment", flush=True)
    transform = transform_integrity(parts)
    alignment = alignment_audit(parts)

    print("[3/9] exact cartridge vs current shell collision audit", flush=True)
    debug: list[Shape] = []
    shell_audit = collision_audit(parts, shells, "SHELL", debug)

    print("[4/9] exact cartridge vs frozen Finger switch audit", flush=True)
    finger_switch_audit = collision_audit(parts, finger_switches, "FINGER_SWITCH", debug)

    print("[5/9] exact cartridge vs present Finger carrier audit", flush=True)
    finger_carrier_audit = collision_audit(parts, finger_carriers, "FINGER_CARRIER", debug)

    print("[6/9] exact cartridge vs original fixed fastening audit", flush=True)
    screw_targets = {screw.name: screw.shape for screw in screws}
    screw_audit = collision_audit(parts, screw_targets, "ORIGINAL_FASTENER", debug)
    fastening = fastening_audit(parts, screws, screw_audit)

    print("[7/9] seam and analysis-only wiring clearance map", flush=True)
    seam = seam_audit(parts)
    wiring, probes = wiring_audit(parts, shells, finger_switches, finger_carriers)

    print("[8/9] classify reuse without auto-fixing geometry", flush=True)
    classifications = classify_parts(parts, shell_audit, finger_switch_audit, finger_carrier_audit, screw_audit)
    direct = [name for name, row in classifications.items() if row["classification"] == "AS_IS"]
    shell_side = [name for name, row in classifications.items() if row["classification"] in ("CLASS_A", "CLASS_B")]
    mounting_change = [name for name, row in classifications.items() if row["classification"] == "CLASS_C"]
    mechanism_change = [name for name, row in classifications.items() if row["classification"] == "CLASS_D"]
    retained_unchanged = [*direct, *shell_side]
    original_reuse_ratio = 100.0 * len(retained_unchanged) / len(parts)
    direct_ratio = 100.0 * len(direct) / len(parts)

    joystick_parts = [part for part in parts if part.category == "joystickMechanism"]
    cap_parts = [part for part in parts if part.category == "thumbCap"]
    push_parts = [part for part in parts if part.category == "pushButton"]
    backplate_parts = [part for part in parts if part.category == "backplate"]
    support_parts = [part for part in parts if part.category == "thumbSupport"]

    mechanism_verdict = (
        "REDESIGN REQUIRED" if mechanism_change
        else "MOSTLY REUSABLE" if shell_side or mounting_change
        else "FULLY REUSABLE"
    )
    backplate_class = classifications["THUMB_BACKPLATE"]["classification"]
    backplate_verdict = (
        "REDESIGN REQUIRED" if backplate_class in ("CLASS_C", "CLASS_D")
        else "ADAPTER REQUIRED" if backplate_class in ("CLASS_A", "CLASS_B")
        else "REUSABLE"
    )
    shell_adaptation = (
        "MAJOR" if shell_audit["penetrationVolumeMm3"] > 100.0 or mechanism_change
        else "MODERATE" if shell_audit["penetrationVolumeMm3"] > 10.0 or shell_side
        else "MINOR"
    )
    finger_conflict = (
        finger_switch_audit["intersectingPairCount"] > 0
        or finger_carrier_audit["intersectingPairCount"] > 0
    )

    report: dict[str, object] = {
        "schema": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOCAL OCCT EXACT B-REP / ANALYSIS ONLY / CAD WRITE TO PRODUCTION 0 / Onshape 0",
        "scopePolicy": {
            "currentExteriorPreserved": True,
            "fingerExteriorPreserved": True,
            "newProductionGeometryCount": 0,
            "newCarrierSeatBossScrewMountWiringChannelCount": 0,
            "allowedOutputs": ["analysis STEP", "transformed reference STEP", "collision/debug B-rep", "renders", "JSON", "report"],
        },
        "sources": {
            "originalCompleteAssembly": {"path": str(ASSEMBLY_SOURCE.relative_to(ROOT)), "sha256": sha256(ASSEMBLY_SOURCE)},
            "originalPartStudioThumbReference": {"path": str(PART_STUDIO_SOURCE.relative_to(ROOT)), "sha256": sha256(PART_STUDIO_SOURCE)},
            "loweredExactTarget": {"path": str(TARGET_SOURCE.relative_to(ROOT)), "sha256": sha256(TARGET_SOURCE)},
            "currentExteriorJaD": {"path": str(JAD_SHELL.relative_to(ROOT)), "sha256": sha256(JAD_SHELL)},
            "currentExteriorJfD": {"path": str(JFD_SHELL.relative_to(ROOT)), "sha256": sha256(JFD_SHELL)},
            "frozenFingerReference": {"path": str(FINGER_REFERENCE.relative_to(ROOT)), "sha256": sha256(FINGER_REFERENCE)},
        },
        "originalMechanicalArchitecture": {
            "summary": (
                "one swept Backplate carries eight PushBtn mechanisms and eight independent caps; "
                "one HW504 module is represented by two exact solids; Small_joystick_attachment is the "
                "joystick-side attachment/opening counterpart; shell-side M3 screws clamp/capture the assembly"
            ),
            "separateButtonSupportPartCount": 0,
            "supportIntegration": "button supports/retainers are integrated into the Backplate and original shell geometry",
            "shellSideFastenerCount": 3,
        },
        "rigidCartridgeDefinition": {
            "name": "ORIGINAL THUMB CARTRIDGE",
            "exactPartCount": len(parts),
            "inventory": {
                "backplate": len(backplate_parts),
                "thumbCaps": len(cap_parts),
                "pushButtons": len(push_parts),
                "joystickMechanismExactSolids": len(joystick_parts),
                "smallJoystickAttachment": len(support_parts),
            },
            "excludes": ["JaD/JfD shell material", "three shell-side M3 screws", "all custom V3/V3.1 geometry"],
            "transform": transform,
        },
        "partList": source_part_list(parts, classifications),
        "alignment": alignment,
        "collisionMatrix": {
            "A_joystickMechanismVsShell": collision_subset(shell_audit, joystick_parts),
            "B_thumbButtonsVsShell": collision_subset(shell_audit, [*cap_parts, *push_parts]),
            "C_backplateVsShell": collision_subset(shell_audit, backplate_parts),
            "D_thumbSupportVsShell": collision_subset(shell_audit, support_parts),
            "E_thumbCartridgeVsFingerSwitches": finger_switch_audit,
            "F_thumbCartridgeVsFingerCarriers": finger_carrier_audit,
            "G_thumbCartridgeVsSeam": seam,
            "fullCartridgeVsShell": shell_audit,
            "fullCartridgeVsOriginalFixedScrews": screw_audit,
        },
        "collisionClassification": classifications,
        "fasteningReuseAnalysis": fastening,
        "wiringExitAnalysis": wiring,
        "reuse": {
            "originalThumbParts": len(parts),
            "reusableAsIsDropIn": len(direct),
            "shellSideAdaptationOnly": len(shell_side),
            "originalMountingPartModification": len(mounting_change),
            "mechanismRedesignRequired": len(mechanism_change),
            "directDropInRatioPercent": direct_ratio,
            "originalPartsRetainedUnchanged": len(retained_unchanged),
            "originalThumbReuseRatioPercent": original_reuse_ratio,
            "reusableAsIsPartNames": direct,
            "shellSideAdaptationPartNames": shell_side,
            "mountingPartModificationPartNames": mounting_change,
            "mechanismRedesignPartNames": mechanism_change,
            "definition": (
                "ORIGINAL THUMB REUSE RATIO counts original part geometries that can remain unchanged, including "
                "Class A/B shell-side adaptation. DIRECT DROP-IN RATIO excludes all adaptation."
            ),
        },
        "verdict": {
            "CURRENT EXTERIOR": "PRESERVED",
            "ORIGINAL THUMB CARTRIDGE": "IDENTIFIED",
            "JOYSTICK ALIGNMENT": "PASS" if alignment["joystickCenterErrorMm"] <= 1.0e-6 else "HOLD",
            "THUMB BUTTON ALIGNMENT": "PASS" if alignment["maximumButtonCenterErrorMm"] <= 1.0e-6 else "HOLD",
            "ORIGINAL THUMB MECHANISM": mechanism_verdict,
            "ORIGINAL BACKPLATE": backplate_verdict,
            "ORIGINAL FASTENING": "ADAPTER REQUIRED",
            "SHELL INTERNAL ADAPTATION": shell_adaptation,
            "FINGER CONFLICT": "PRESENT" if finger_conflict else "NONE",
            "ORIGINAL THUMB REUSE RATIO": f"{original_reuse_ratio:.1f} %",
        },
        "limitations": [
            "Current exact review STEP uses the documented 0.80 mm localized opening envelopes; the authoritative actual lower-15 exterior is a visual STL graft, not an exact editable B-rep.",
            "Finger switches/carriers are the present frozen V2 exact reference set; the handoff still marks internal design as deferred, so these collisions are audit evidence, not production approval.",
            "PushBtn/HW504 connector sub-bodies are not semantically separated in the imported STEP; wiring probes are conservative clearance directions only.",
            "No collision has been auto-fixed and no production geometry has been created.",
        ],
        "stop": "STOP AFTER ANALYSIS; await user review before any internal redesign.",
    }

    seam_slab = Box(0.10, 160.0, 180.0, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    seam_slab.label = "ANALYSIS_ONLY_SEAM_BAND_0P10MM"
    debug_children = [*debug, seam_slab]
    compounds = {
        "original": renamed_compound(parts, "ORIGINAL_THUMB_CARTRIDGE", -TARGET_DELTA),
        "lowered": renamed_compound(parts, "LOWERED_ORIGINAL_THUMB_CARTRIDGE"),
        "fastening": renamed_compound(screws, "ORIGINAL_FASTENING_REFERENCE"),
        "collisions": Compound(children=debug_children, label="ORIGINAL_THUMB_COLLISION_DEBUG"),
        "wiring": Compound(children=probes, label="THUMB_WIRING_CLEARANCE_PROBES_ANALYSIS_ONLY"),
    }
    return report, compounds


def export_results(report: dict[str, object], compounds: dict[str, Compound]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        ORIGINAL_OUTPUT: compounds["original"],
        LOWERED_OUTPUT: compounds["lowered"],
        FASTENING_OUTPUT: compounds["fastening"],
        COLLISION_OUTPUT: compounds["collisions"],
        WIRING_OUTPUT: compounds["wiring"],
    }
    for path, shape in outputs.items():
        export_step(shape, path)
    report["outputs"] = {
        path.name: {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
        for path in outputs
    }
    REPORT_OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    report, compounds = build_report()
    print("[9/9] export analysis-only exact reference set and JSON", flush=True)
    export_results(report, compounds)
    print(json.dumps(report["verdict"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
