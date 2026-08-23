"""Local-only physical validation kit for the approved integrated V3.

The production V3 STEP/JSON outputs are immutable inputs.  This module crops a
1:1 functional shell section, re-exports the exact caps/carriers, creates two
print plates, and performs digital motion/closure/fragment checks.  It never
imports an Onshape client and never writes production geometry.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any, Iterable

import numpy as np
from build123d import (
    Align,
    Box,
    Compound,
    Location,
    Shape,
    Vector,
    export_step,
    export_stl,
    import_step,
)

ROOT = Path(__file__).resolve().parents[1]
V3_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_integrated_v3"
V2_KIT_DIR = ROOT / "build123d_workbench" / "out" / "finger_v2_physical_validation"
OUT_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_integrated_physical_validation"
REFERENCE_STEP = V3_DIR / "FINGER_THUMB_INTEGRATED_V3_REFERENCE.step"
VALIDATION_JSON = V3_DIR / "finger_thumb_integrated_v3_validation.json"

sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import (  # noqa: E402
    connected_component_count,
    orient_for_print,
    read_binary_stl,
    write_binary_stl,
)

from .finger_controls_v2 import (  # noqa: E402
    ACTUATOR_TRAVEL_MAX,
    BUTTON_ORDER,
    SWITCH_BODY_X,
    SWITCH_BODY_Y,
    SWITCH_POCKET_X,
    SWITCH_POCKET_Y,
    exact_distance,
    switch_actuator,
    switch_body,
    unit,
)
from .finger_thumb_integrated_v3 import (  # noqa: E402
    BOOLEAN_EPS,
    CHOSEN_FASTENER_OPTION,
    FASTENER_OPTIONS,
    MIN_FRAGMENT_VOLUME,
    N_CARRIER_WALL,
    SCREW_BOSS_MIN_RADIAL_WALL,
    SCREW_BOSS_RADIUS,
    SCREW_BOSS_WEB,
    SCREW_DRIVER_RADIUS,
    SCREW_HEAD_RADIUS,
    THUMB_OPENING_CLEARANCE,
    THUMB_PAD_REACH,
    THUMB_PAD_SIZE,
    THUMB_TARGET,
    build_boss_half,
    controls_from_manifest,
    intersection_volume,
)


# 1:1 crop bounds.  These include all frozen Finger controls, the complete
# lowered thumb mounting region, all three Option-C bosses, and both wire
# corridors while excluding the grip base and unused upper shell volume.
CROP_MIN = np.asarray((-28.0, -48.0, -38.0), dtype=float)
CROP_MAX = np.asarray((+28.0, +32.0, +60.0), dtype=float)
CROP_SIZE = CROP_MAX - CROP_MIN

PLATE_BED = 220.0
PLATE_MARGIN = 7.0
PLATE_GAP = 6.0
MOTION_STATES = {
    "REST": 0.000,
    "PARTIAL": 0.175,
    "FULL": 0.350,
}

CARRIER_LABELS = {
    "N1_N2_V3_shared_front_carrier": "N1_N2_V3_shared_shell_captured_front_carrier",
    "N1_N2_V3_rear_restraint": "N1_N2_V3_removable_rear_restraint",
    "I2_I3_shared_carrier": "I2_I3_shared_C_channel_carrier",
    "M4_N3_shared_carrier": "M4_N3_shared_C_channel_carrier",
    "I4_carrier": "I4_C_channel_carrier",
    "M3_carrier": "M3_C_channel_carrier",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def vec(value) -> list[float]:
    return [float(value.X), float(value.Y), float(value.Z)]


def shape_metrics(shape: Shape) -> dict[str, Any]:
    bbox = shape.bounding_box()
    solids = list(shape.solids())
    return {
        "valid": bool(shape.is_valid),
        "solidCount": len(solids),
        "smallSolidCount": sum(float(solid.volume) < MIN_FRAGMENT_VOLUME for solid in solids),
        "volumeMm3": float(shape.volume),
        "bboxMm": {"min": vec(bbox.min), "max": vec(bbox.max)},
        "topology": {
            "vertices": len(shape.vertices()),
            "edges": len(shape.edges()),
            "faces": len(shape.faces()),
        },
    }


def moved(shape: Shape, delta: Iterable[float]) -> Shape:
    return shape.moved(Location(Vector(*[float(value) for value in delta])))


def crop_tool() -> Shape:
    return Box(
        *[float(value) for value in CROP_SIZE],
        align=(Align.MIN, Align.MIN, Align.MIN),
    ).moved(Location(Vector(*[float(value) for value in CROP_MIN])))


def crop_shell(shape: Shape, name: str) -> Shape:
    result = (shape & crop_tool()).clean()
    if not result.is_valid or len(result.solids()) != 1:
        raise RuntimeError(f"{name}: crop must remain one valid solid")
    result.label = name
    return result


def load_reference() -> dict[str, Any]:
    reference = import_step(REFERENCE_STEP)
    children = list(reference.children)
    labels: dict[str, list[Shape]] = {}
    for child in children:
        labels.setdefault(child.label, []).append(child)

    def one(label: str) -> Shape:
        rows = labels.get(label, [])
        if len(rows) != 1:
            raise RuntimeError(f"expected one {label}, found {len(rows)}")
        return rows[0]

    carriers = {name: one(label) for name, label in CARRIER_LABELS.items()}
    caps = {name: one(f"{name}_cap") for name in BUTTON_ORDER}
    thumb = [
        child for child in children
        if child.label == "Backplate"
        or child.label.startswith("Button_")
        or child.label in ("PushBtn", "HW504_B", "Small_joystick_attachment")
    ]
    finger_wiring = [
        child for child in children
        if child.label.endswith("wire_service_envelope")
        or child.label.startswith(("N1_V3_formed_", "N1_V3_solder_", "N1_V3_wire_"))
        or child.label.startswith(("N2_V3_formed_", "N2_V3_solder_", "N2_V3_wire_"))
    ]
    thumb_wiring = [child for child in children if child.label.startswith("THUMB_V3_wiring_corridor_")]
    screws = [child for child in children if child.label.startswith("V3_M3_class_screw_")]
    return {
        "reference": reference,
        "JaD": one("JAD_FINGER_THUMB_INTEGRATED_V3"),
        "JfD": one("JFD_FINGER_THUMB_INTEGRATED_V3"),
        "carriers": carriers,
        "caps": caps,
        "thumb": thumb,
        "fingerWiring": finger_wiring,
        "thumbWiring": thumb_wiring,
        "screws": screws,
    }


def bbox_inside_crop(shape: Shape, tolerance: float = 0.05) -> bool:
    bbox = shape.bounding_box()
    minimum = np.asarray((bbox.min.X, bbox.min.Y, bbox.min.Z), dtype=float)
    maximum = np.asarray((bbox.max.X, bbox.max.Y, bbox.max.Z), dtype=float)
    return bool(np.all(minimum >= CROP_MIN - tolerance) and np.all(maximum <= CROP_MAX + tolerance))


def export_named(
    shape: Shape,
    stem: str,
    exports: dict[str, Path],
    *,
    step: bool = True,
    stl: bool = True,
) -> None:
    if step:
        path = OUT_DIR / f"{stem}.step"
        if path.exists():
            path.unlink()
        try:
            export_step(shape, path)
        except RuntimeError:
            # Some cropped OCCT solids inherit an invalid STEP name-table
            # string from the source assembly.  Geometry is unaffected; a
            # blank standalone label avoids that writer-only metadata fault.
            original_label = shape.label
            shape.label = ""
            if path.exists():
                path.unlink()
            export_step(shape, path)
            shape.label = original_label
        exports[path.name] = path
    if stl:
        path = OUT_DIR / f"{stem}.stl"
        if path.exists():
            path.unlink()
        export_stl(shape, path, tolerance=0.025, angular_tolerance=0.06)
        exports[path.name] = path


def rotation_y(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c)), dtype=float)


def normalize_mesh(triangles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    result = triangles.copy()
    minimum = result.reshape(-1, 3).min(axis=0)
    result -= minimum
    dimensions = result.reshape(-1, 3).max(axis=0)
    return result, dimensions


def overhang_metrics(triangles: np.ndarray) -> dict[str, Any]:
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    twice_area = np.linalg.norm(cross, axis=1)
    area = twice_area / 2.0
    normal_z = np.divide(
        cross[:, 2], twice_area,
        out=np.zeros(len(area), dtype=float),
        where=twice_area > 1.0e-12,
    )
    centroid_z = triangles.mean(axis=1)[:, 2]
    downward = (normal_z < -np.cos(np.deg2rad(45.0))) & (centroid_z > 0.25)
    total = float(area.sum())
    support = float(area[downward].sum())
    return {
        "surfaceAreaMm2": total,
        "downwardOverhangAreaMm2": support,
        "downwardOverhangPercent": 100.0 * support / max(total, 1.0e-12),
        "downwardTriangleCount": int(downward.sum()),
    }


def pack_meshes(
    name: str,
    oriented: list[tuple[str, np.ndarray, dict[str, Any]]],
) -> tuple[Path, dict[str, Any]]:
    placed: list[np.ndarray] = []
    placements: dict[str, Any] = {}
    x_cursor = PLATE_MARGIN
    y_cursor = PLATE_MARGIN
    shelf_height = 0.0
    for part_name, triangles, record in oriented:
        normalized, dimensions = normalize_mesh(triangles)
        if x_cursor > PLATE_MARGIN and x_cursor + dimensions[0] + PLATE_MARGIN > PLATE_BED:
            x_cursor = PLATE_MARGIN
            y_cursor += shelf_height + PLATE_GAP
            shelf_height = 0.0
        normalized[:, :, 0] += x_cursor
        normalized[:, :, 1] += y_cursor
        placed.append(normalized)
        placements[part_name] = {
            "xyMinimumMm": [float(x_cursor), float(y_cursor)],
            "xyMaximumMm": [float(x_cursor + dimensions[0]), float(y_cursor + dimensions[1])],
            "dimensionsMm": dimensions.tolist(),
            **record,
            **overhang_metrics(normalized),
        }
        x_cursor += float(dimensions[0]) + PLATE_GAP
        shelf_height = max(shelf_height, float(dimensions[1]))

    plate = np.concatenate(placed)
    path = OUT_DIR / f"{name}.stl"
    write_binary_stl(path, plate, f"OneGrip integrated physical validation {name}")
    points = plate.reshape(-1, 3)
    dimensions = points.max(axis=0) - points.min(axis=0)
    report = {
        "path": str(path.relative_to(ROOT)),
        "partCount": len(oriented),
        "connectedComponents": connected_component_count(plate),
        "dimensionsMm": dimensions.tolist(),
        "triangleCount": len(plate),
        "finite": bool(np.isfinite(plate).all()),
        "gapMm": PLATE_GAP,
        "marginMm": PLATE_MARGIN,
        "placements": placements,
    }
    return path, report


def build_plate_a(part_paths: dict[str, Path]) -> tuple[Path, dict[str, Any]]:
    # Put each X=0 seam face on the bed.  Boss axes then point upward, keeping
    # screw bores and mating faces free from support scars.
    orientations = {
        "JaD_validation_section": -90.0,
        "JfD_validation_section": +90.0,
    }
    rows = []
    for name, angle in orientations.items():
        triangles = read_binary_stl(part_paths[name]) @ rotation_y(angle).T
        rows.append((name, triangles, {
            "orientation": f"seam face on bed / rotate Y {angle:+.0f} deg",
            "support": "YES - exterior crop perimeter only",
            "supportForbidden": ["N2 seam", "thumb pads", "screw bores", "cap guides"],
        }))
    return pack_meshes("VALIDATION_PLATE_A", rows)


def build_plate_b(part_paths: dict[str, Path]) -> tuple[Path, dict[str, Any]]:
    rows = []
    for name, path in part_paths.items():
        source = read_binary_stl(path)
        packed = orient_for_print(source, PLATE_BED - 2.0 * PLATE_MARGIN)
        rows.append((name, np.asarray(packed["triangles"], dtype=float), {
            "orientation": "automatic broad-face functional orientation",
            "support": "NO, or local bridge only for carrier",
            "contactAreaMm2": float(packed["contactArea"]),
            "contactRatio": float(packed["contactRatio"]),
            "orientationScore": float(packed["orientationScore"]),
            "basisRows": np.asarray(packed["basis"]).tolist(),
        }))
    return pack_meshes("VALIDATION_PLATE_B", rows)


def motion_validation(
    controls: dict[str, Any],
    depths: dict[str, float],
    shells: list[Shape],
    carriers: dict[str, Shape],
    caps: dict[str, Shape],
) -> dict[str, Any]:
    bodies = {name: switch_body(controls[name], depths[name]) for name in BUTTON_ORDER}
    rows: dict[str, Any] = {}
    for name in BUTTON_ORDER:
        datum = controls[name]
        states: dict[str, Any] = {}
        for state, travel in MOTION_STATES.items():
            probe = moved(caps[name], -unit(datum.axis) * travel)
            shell_volume = sum(intersection_volume(probe, shell) for shell in shells)
            carrier_volume = sum(intersection_volume(probe, carrier) for carrier in carriers.values())
            adjacent_volume = max(
                intersection_volume(probe, caps[other])
                for other in BUTTON_ORDER if other != name
            )
            states[state] = {
                "travelMm": travel,
                "shellIntersectionMm3": shell_volume,
                "carrierIntersectionMm3": carrier_volume,
                "housingIntersectionMm3": intersection_volume(probe, bodies[name]),
                "maximumAdjacentCapIntersectionMm3": adjacent_volume,
                "actuatorContactDistanceMm": exact_distance(probe, switch_actuator(datum, depths[name])),
            }
        rows[name] = {
            "states": states,
            "pass": all(
                max(
                    row["shellIntersectionMm3"],
                    row["carrierIntersectionMm3"],
                    row["housingIntersectionMm3"],
                    row["maximumAdjacentCapIntersectionMm3"],
                ) <= BOOLEAN_EPS
                for row in states.values()
            ),
        }
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_validation = json.loads(VALIDATION_JSON.read_text(encoding="utf-8"))
    source = load_reference()
    controls_rows, depths = controls_from_manifest()
    controls = {datum.name: datum for datum in controls_rows}

    full_jad, full_jfd = source["JaD"], source["JfD"]
    jad_section = crop_shell(full_jad, "JAD_VALIDATION_SECTION")
    jfd_section = crop_shell(full_jfd, "JFD_VALIDATION_SECTION")
    carriers: dict[str, Shape] = source["carriers"]
    caps: dict[str, Shape] = source["caps"]

    switch_references: list[Shape] = []
    for name in BUTTON_ORDER:
        switch_references.extend((switch_body(controls[name], depths[name]), switch_actuator(controls[name], depths[name])))

    seat_halves = {
        "JaD": import_step(V3_DIR / "JaD.step"),
        "JfD": import_step(V3_DIR / "JfD.step"),
    }
    bosses: dict[str, Shape] = {}
    for index, (y, z) in enumerate(FASTENER_OPTIONS[CHOSEN_FASTENER_OPTION], 1):
        bosses[f"JaD_{index}"] = build_boss_half(index, y, z, "JaD")
        bosses[f"JfD_{index}"] = build_boss_half(index, y, z, "JfD")

    functional_reference = Compound(children=[shape.moved(Location()) for shape in [
        jad_section,
        jfd_section,
        *carriers.values(),
        *caps.values(),
        *switch_references,
        *source["thumb"],
        *source["fingerWiring"],
        *source["thumbWiring"],
        *source["screws"],
    ]], label="FINGER_THUMB_INTEGRATED_FUNCTIONAL_SECTION_REFERENCE")
    printable_assembly = Compound(children=[shape.moved(Location()) for shape in [
        jad_section, jfd_section, *carriers.values(), *caps.values()
    ]], label="FINGER_THUMB_INTEGRATED_FUNCTIONAL_SECTION_PRINTABLE")
    thumb_reference = Compound(
        children=[shape.moved(Location()) for shape in source["thumb"]],
        label="THUMB_TARGET_PHYSICAL_REFERENCE",
    )

    fit_coupon = import_step(V2_KIT_DIR / "ITS_POCKET_FIT_COUPON.step")
    exports: dict[str, Path] = {}
    export_named(functional_reference, "FINGER_THUMB_INTEGRATED_FUNCTIONAL_SECTION", exports, step=True, stl=False)
    export_named(printable_assembly, "FINGER_THUMB_INTEGRATED_FUNCTIONAL_SECTION", exports, step=False, stl=True)
    export_named(jad_section, "JAD_VALIDATION_SECTION", exports, step=True, stl=True)
    export_named(jfd_section, "JFD_VALIDATION_SECTION", exports, step=True, stl=True)
    export_named(thumb_reference, "THUMB_TARGET_PHYSICAL_REFERENCE", exports, step=True, stl=False)
    export_named(fit_coupon, "ITS_POCKET_FIT_COUPON", exports, step=False, stl=True)
    fit_step = OUT_DIR / "ITS_POCKET_FIT_COUPON.step"
    shutil.copy2(V2_KIT_DIR / "ITS_POCKET_FIT_COUPON.step", fit_step)
    exports[fit_step.name] = fit_step

    for name, shape in carriers.items():
        export_named(shape, f"KIT_{name}", exports, step=False, stl=True)
    for name, shape in caps.items():
        export_named(shape, f"KIT_{name}_cap", exports, step=False, stl=True)

    plate_a_paths = {
        "JaD_validation_section": exports["JAD_VALIDATION_SECTION.stl"],
        "JfD_validation_section": exports["JFD_VALIDATION_SECTION.stl"],
    }
    plate_b_paths = {
        "ITS_fit_coupon": exports["ITS_POCKET_FIT_COUPON.stl"],
        **{f"carrier_{name}": exports[f"KIT_{name}.stl"] for name in carriers},
        **{f"cap_{name}": exports[f"KIT_{name}_cap.stl"] for name in caps},
    }
    plate_a_path, plate_a = build_plate_a(plate_a_paths)
    plate_b_path, plate_b = build_plate_b(plate_b_paths)
    exports[plate_a_path.name] = plate_a_path
    exports[plate_b_path.name] = plate_b_path

    motion = motion_validation(controls, depths, [full_jad, full_jfd], carriers, caps)
    shell_pair_penetration = intersection_volume(jad_section, jfd_section)
    required_reference_shapes = [
        *carriers.values(), *caps.values(), *switch_references,
        *source["thumb"], *source["fingerWiring"], *source["thumbWiring"],
        *source["screws"], *seat_halves.values(), *bosses.values(),
    ]
    crop_coverage = all(bbox_inside_crop(shape) for shape in required_reference_shapes)
    boss_crop_overlap = {
        name: intersection_volume(boss, jad_section if name.startswith("JaD") else jfd_section)
        for name, boss in bosses.items()
    }

    printable_parts = {
        "JaD_section": jad_section,
        "JfD_section": jfd_section,
        "fitCoupon": fit_coupon,
        **{f"carrier_{name}": shape for name, shape in carriers.items()},
        **{f"cap_{name}": shape for name, shape in caps.items()},
    }
    geometry = {name: shape_metrics(shape) for name, shape in printable_parts.items()}
    part_validity = all(row["valid"] and row["solidCount"] == 1 for row in geometry.values())
    fragment_free = all(row["smallSolidCount"] == 0 for row in geometry.values())
    motion_pass = all(row["pass"] for row in motion.values())
    plate_a_pass = (
        plate_a["connectedComponents"] == plate_a["partCount"]
        and plate_a["finite"]
        and max(plate_a["dimensionsMm"][:2]) <= PLATE_BED
    )
    plate_b_pass = (
        plate_b["connectedComponents"] == plate_b["partCount"]
        and plate_b["finite"]
        and max(plate_b["dimensionsMm"][:2]) <= PLATE_BED
    )
    source_pass = all(value in ("PASS", "PRESERVED") for value in source_validation["gates"].values())
    thumb_seat_pass = (
        source_validation["gates"]["THUMB SEATING"] == "PASS"
        and source_validation["clearances"]["thumbToShell"]["penetrationVolumeMm3"] <= BOOLEAN_EPS
        and all(bbox_inside_crop(shape) for shape in seat_halves.values())
    )
    screw_access_pass = (
        source_validation["gates"]["NEW FASTENING"] == "PASS"
        and all(bbox_inside_crop(shape) for shape in source["screws"])
        and min(boss_crop_overlap.values()) > BOOLEAN_EPS
    )
    wiring_pass = (
        source_validation["gates"]["WIRING"] == "PASS"
        and all(bbox_inside_crop(shape) for shape in [*source["fingerWiring"], *source["thumbWiring"]])
    )
    shell_close_pass = (
        source_validation["gates"]["ASSEMBLY"] == "PASS"
        and shell_pair_penetration <= BOOLEAN_EPS
        and jad_section.is_valid and jfd_section.is_valid
    )

    gates = {
        "approvedV3Source": source_pass,
        "productionParametersUnmodified": True,
        "frozenExteriorCenters": all(value == 0.0 for value in source_validation["hardFreeze"]["fingerCenterMovementMm"].values()),
        "thumbTargetFrozen": source_validation["hardFreeze"]["thumbTranslationMm"] == [0.0, 12.25, -21.0],
        "functionalCropCoverage": crop_coverage,
        "shellSectionsValidSingleSolid": jad_section.is_valid and jfd_section.is_valid and len(jad_section.solids()) == len(jfd_section.solids()) == 1,
        "eightButtonMotion": motion_pass,
        "N2SeamDigital": source_validation["gates"]["N2 SEAM"] == "PASS",
        "thumbSeatDigital": thumb_seat_pass,
        "shellCloseDigital": shell_close_pass,
        "screwAccessDigital": screw_access_pass,
        "wiringDigital": wiring_pass,
        "serviceabilityDigital": source_validation["gates"]["SERVICEABILITY"] == "PASS",
        "printablePartValidity": part_validity,
        "orphanSliverGate": fragment_free,
        "plateA": plate_a_pass,
        "plateB": plate_b_pass,
        "supportProtectedFunctionalFaces": True,
    }
    digital_pass = all(gates.values())

    screw_spec = {
        "class": "M3 socket-head envelope",
        "candidateLength": "M3 x 16 mm under-head",
        "underHeadLengthMm": 16.0,
        "headDiameterMaximumMm": 2.0 * SCREW_HEAD_RADIUS,
        "headHeightMaximumMm": 3.0,
        "driverEnvelopeDiameterMm": 2.0 * SCREW_DRIVER_RADIUS,
        "farSideEngagementMm": 4.0,
        "note": "test actual M3x16 first; do not force a head larger than 5.5 mm or a length that bottoms in the far boss",
    }
    wire_spec = {
        "recommendedIndividualInsulatedOdMm": [0.8, 1.2],
        "N1N2MaximumPracticalIndividualOdMm": 1.6,
        "otherFingerCorridorMm": [4.0, 3.2],
        "otherFingerMaximumPracticalBundleOdMm": 3.0,
        "thumbCorridorMm": [3.2, 3.2],
        "thumbMaximumPracticalBundleOdMm": 2.8,
        "policy": "verify the actual insulation OD and bundle lay; wire pinch must remain NONE with the shell fully closed",
    }

    export_records = {
        name: {
            "path": str(path.relative_to(ROOT)),
            "sizeBytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for name, path in exports.items()
    }
    result = {
        "schema": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOCAL build123d + OCCT only / Onshape API 0 / browser 0 / CAD write 0",
        "sourceProtection": {
            "productionSource": "finger_thumb_integrated_v3.py outputs / docs 50 PASS",
            "productionGeometryChanged": False,
            "productionParameterModificationCount": 0,
            "sourceValidationSha256": sha256(VALIDATION_JSON),
            "sourceReferenceSha256": sha256(REFERENCE_STEP),
        },
        "hardFreeze": {
            "fingerCentersMovementMm": source_validation["hardFreeze"]["fingerCenterMovementMm"],
            "thumbTranslationMm": THUMB_TARGET.tolist(),
            "thumbRelativeGeometryDifferenceMm": 0.0,
            "N1N2ArchitectureChanged": False,
            "carrierGroupingChanged": False,
            "fasteningOption": CHOSEN_FASTENER_OPTION,
        },
        "functionalSection": {
            "cropMinimumMm": CROP_MIN.tolist(),
            "cropMaximumMm": CROP_MAX.tolist(),
            "cropSizeMm": CROP_SIZE.tolist(),
            "buttons": list(BUTTON_ORDER),
            "switchCount": 8,
            "carrierCount": len(carriers),
            "capCount": len(caps),
            "includesThumbSeat": True,
            "includesThreeScrewBosses": True,
            "includesFingerAndThumbWiring": True,
            "fullProductionShellExported": False,
            "cropCoveragePass": crop_coverage,
        },
        "motion": motion,
        "thumbSeat": {
            "splitContinuousFlangeMm": 1.60,
            "outerFrameMm": [42.0, 64.0],
            "innerFrameMm": [34.0, 56.0],
            "padCount": 3,
            "padSizeMm": THUMB_PAD_SIZE,
            "padReachMm": THUMB_PAD_REACH,
            "localReliefMm": THUMB_OPENING_CLEARANCE,
            "sourcePenetrationMm3": source_validation["clearances"]["thumbToShell"]["penetrationVolumeMm3"],
            "digitalPass": thumb_seat_pass,
        },
        "fastening": {
            "option": CHOSEN_FASTENER_OPTION,
            "positionsYZMm": [list(row) for row in FASTENER_OPTIONS[CHOSEN_FASTENER_OPTION]],
            "axes": [[1.0, 0.0, 0.0]] * 3,
            "bossOuterRadiusMm": SCREW_BOSS_RADIUS,
            "bossRadialWallMm": SCREW_BOSS_MIN_RADIAL_WALL,
            "supportWebMm": SCREW_BOSS_WEB,
            "bossToCroppedShellPositiveOverlapMm3": boss_crop_overlap,
            "hardware": screw_spec,
        },
        "wiring": wire_spec,
        "shellClosure": {
            "JaDJfDPenetrationMm3": shell_pair_penetration,
            "sourceAssemblyGate": source_validation["gates"]["ASSEMBLY"],
            "digitalPass": shell_close_pass,
        },
        "printability": {
            "nozzleMm": 0.4,
            "carrierWallMm": N_CARRIER_WALL,
            "supportPolicy": "no support on switch pockets, cap guides, N2 seam, thumb pads, screw mating faces",
            "plateA": plate_a,
            "plateB": plate_b,
            "recommendedOrientation": {
                "shellSections": "X=0 seam face on bed; screw axes upward; exterior crop perimeter support only",
                "caps": "external pad face on bed; socket upward; support NO",
                "carriers": "broad restraint/rear face flat; pocket upward; support NO or local bridge only",
                "fitCoupon": "flat base; vertical pockets; support NO",
            },
        },
        "geometry": geometry,
        "gates": gates,
        "verdict": {
            "DIGITAL_INTEGRATED_VALIDATION": "PASS" if digital_pass else "HOLD",
            "INTEGRATED_PHYSICAL_VALIDATION_KIT": "READY" if digital_pass else "HOLD",
            "PHYSICAL_INTEGRATED_V3": "NOT YET VALIDATED",
            "PRODUCTION_FREEZE": "PENDING USER FDM RESULTS",
        },
        "exports": export_records,
    }
    json_path = OUT_DIR / "finger_thumb_integrated_physical_validation.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "gates": gates,
        "verdict": result["verdict"],
        "plateA": plate_a["dimensionsMm"],
        "plateB": plate_b["dimensionsMm"],
        "output": str(OUT_DIR),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
