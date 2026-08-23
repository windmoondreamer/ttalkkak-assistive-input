"""Read-only confirmation of the original OneGrip knob and SZH reference stack.

No production geometry is exported or modified.  The only new geometry is an
audit-only shaft sweep and an exploded/target-position render proxy.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from build123d import Align, Box, Compound, Cone, Location, Plane, Shape, Vector, import_step

from .finger_controls_v2 import xyz
from .option_c_local_exact_prototype import raster_scene, safe_triangles
from .original_thumb_module_reuse_audit import load_target_parts
from .szh_ek056_provisional_thumb_integration_audit import (
    DATUM_P,
    DATUM_V,
    OUTWARD,
    N1_N2_CARRIER,
    bbox,
    exact_relationship,
    local_shells,
    placement,
    placed,
)
from .szh_ek056_web_reference import (
    GIMBAL_H,
    JOY_X,
    JOY_Y,
    MAX_TILT_DEG,
    PIVOT_Z,
    SHAFT_D,
    SHAFT_TOP_Z,
    build_reference,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "szh_ek056_knob_interface_confirmation"
RENDER_DIR = ROOT / "renders" / "szh_ek056_knob_interface_confirmation"
JSON_PATH = OUT_DIR / "szh_ek056_knob_interface_confirmation.json"
RENDER_PATH = RENDER_DIR / "01_stock_vs_original_knob_final_intended_stack.png"

DOCS70 = ROOT / "docs" / "70_finger_8_button_mechanical_baseline_checkpoint.md"
DOCS71 = ROOT / "docs" / "71_szh_ek056_provisional_thumb_integration_audit.md"
DOCS71_JSON = ROOT / "build123d_workbench" / "out" / "szh_ek056_provisional_thumb_integration_audit" / "szh_ek056_provisional_thumb_integration_audit.json"
ORIGINAL_SOURCE = ROOT / "lower_adapter" / "local_cad" / "reference" / "ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step"
ORIGINAL_TARGET = ROOT / "build123d_workbench" / "out" / "finger_thumb_joint_feasibility" / "THUMB_TARGET_EXACT_MODULE.step"
ORIGINAL_PRINTABLE_STL = ROOT / "exports" / "right_hand_handle_parts" / "individual_stl" / "Joystick - Small_joystick_attachment.stl"
FEATURE_DUMP = ROOT / "cad_dump" / "features_Joystick.json"
ASSEMBLY_DUMP = ROOT / "cad_dump" / "asmdef_Joystick.json"
REFERENCE_STEP = ROOT / "local_cad" / "reference" / "SZH_EK056_WEB_REFERENCE.step"
REFERENCE_JSON = ROOT / "local_cad" / "reference" / "SZH_EK056_WEB_REFERENCE.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_original_shapes() -> tuple[Shape, Shape]:
    parts = load_target_parts()
    knob = next(part.shape for part in parts if part.name == "THUMB_JOYSTICK_SMALL_ATTACHMENT")
    moving = min((part.shape for part in parts if part.category == "joystickMechanism"), key=lambda shape: float(shape.volume))
    plane = Plane(origin=xyz(DATUM_P), x_dir=xyz(DATUM_V), z_dir=xyz(OUTWARD))
    knob_local = plane.to_local_coords(knob)
    knob_local.label = "ORIGINAL_ONEGRIP_SMALL_JOYSTICK_ATTACHMENT_KNOB"
    moving_local = plane.to_local_coords(moving)
    moving_local.label = "ORIGINAL_HW504_MOVING_SHAFT_GIMBAL"
    return knob_local, moving_local


def interface_measurements(knob: Shape, original_moving: Shape) -> dict[str, object]:
    candidates: list[Shape] = []
    for face in knob.faces():
        b = face.bounding_box()
        span_z = float(b.max.Z - b.min.Z)
        span_x = float(b.max.X - b.min.X)
        span_y = float(b.max.Y - b.min.Y)
        if span_z > 8.9 and span_x < 4.3 and span_y < 3.3:
            candidates.append(face)
    if len(candidates) != 4:
        raise RuntimeError(f"Expected four blind keyed-bore side faces, got {len(candidates)}")
    bounds = [face.bounding_box() for face in candidates]
    bore_min = np.asarray((min(b.min.X for b in bounds), min(b.min.Y for b in bounds), min(b.min.Z for b in bounds)), float)
    bore_max = np.asarray((max(b.max.X for b in bounds), max(b.max.Y for b in bounds), max(b.max.Z for b in bounds)), float)

    slice_z = 5.0
    slab = Box(20.0, 20.0, 0.10, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0.0, 0.0, slice_z)))
    section = (original_moving & slab).clean()
    sb = section.bounding_box()
    shaft_xy = [float(sb.max.X - sb.min.X), float(sb.max.Y - sb.min.Y)]
    moving_bbox = original_moving.bounding_box()
    insertion = max(0.0, min(float(bore_max[2]), float(moving_bbox.max.Z)) - max(float(bore_min[2]), slice_z - 1.6))
    # Physical assembled overlap is opening Z=3.4 to original shaft top Z=9.0.
    insertion = max(0.0, min(float(bore_max[2]), float(moving_bbox.max.Z)) - float(bore_min[2]))
    return {
        "knobBlindBoreBboxMm": {"min": bore_min.tolist(), "max": bore_max.tolist()},
        "knobBoreCrossSectionMm": [float(bore_max[0] - bore_min[0]), float(bore_max[1] - bore_min[1])],
        "knobBoreDepthMm": float(bore_max[2] - bore_min[2]),
        "originalHw504ShaftCrossSectionAtZ5Mm": shaft_xy,
        "originalAssembledInsertionLengthMm": insertion,
        "interfaceShape": "KEYED ROUNDED-RECTANGULAR BLIND BORE",
        "retentionEvidence": "geometry/variables imply friction or press/transition fit; Onshape assembly uses FASTENED mate; no screw feature found",
        "sourceVariablesMm": {
            "small_joystick_pin_width": 3.0,
            "small_joystick_pin_depth": 4.0,
            "small_joystick_pin_height": 8.0,
            "small_joystick_top_diameter": 14.0,
            "small_joystick_tolerance": 0.075,
        },
    }


def shaft_only_sweep() -> Shape:
    length = SHAFT_TOP_Z - PIVOT_Z
    top_radius = SHAFT_D / 2.0 + length * math.sin(math.radians(MAX_TILT_DEG))
    sweep = Cone(
        SHAFT_D / 2.0,
        top_radius,
        length,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    ).moved(Location(Vector(JOY_X, JOY_Y, PIVOT_Z)))
    sweep.label = "SZH_SHAFT_ONLY_25DEG_INFERRED_SWEEP_NO_STOCK_KNOB"
    return sweep


def shell_rerate(reference_parts: dict[str, Shape], shaft_sweep_local: Shape) -> dict[str, object]:
    location, _ = placement()
    placed_rows = {name: placed(shape, location, f"SZH_{name.upper()}") for name, shape in reference_parts.items()}
    carrier = import_step(N1_N2_CARRIER)
    crop_seed = Compound(children=[*placed_rows.values(), carrier], label="KNOB_CHECK_LOCAL_CROP_SEED")
    shells = local_shells(crop_seed)
    sweep = placed(shaft_sweep_local, location, "SZH_SHAFT_ONLY_MOVING_SWEEP")
    gimbal = placed_rows["gimbal"]
    shaft = placed_rows["shaft"]
    rows = {"shaftOnlySweep": [], "neutralShaft": [], "gimbalHousing": []}
    for shell_name, shell in shells.items():
        for key, feature, shape in (
            ("shaftOnlySweep", "SHAFT_ONLY_SWEEP", sweep),
            ("neutralShaft", "NEUTRAL_SHAFT", shaft),
            ("gimbalHousing", "GIMBAL_HOUSING", gimbal),
        ):
            row, _ = exact_relationship(
                feature,
                shape,
                f"local_shell.{shell_name}",
                shell,
                "A",
                "FUNCTIONAL / KNOB EXCLUDED",
            )
            rows[key].append(row)
    return rows


def target_original_knob(knob_local: Shape) -> tuple[Shape, float]:
    # Align the blind-bore bottom (original local Z=12.4) to the nominal SZH
    # shaft tip Z=25.0.  This is an audit-only maximum-insertion concept.
    shift_z = SHAFT_TOP_Z - 12.4
    result = knob_local.moved(Location(Vector(JOY_X, JOY_Y, shift_z)))
    result.label = "ORIGINAL_ONEGRIP_KNOB_TARGET_MAX_INSERTION_CONCEPT"
    return result, shift_z


def triangles(shape: Shape, tolerance: float = 0.24) -> np.ndarray:
    return safe_triangles(shape, tolerance=tolerance, angular=0.12)


def render_stack(reference_parts: dict[str, Shape], knob_target: Shape, mismatch: Shape | None) -> None:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    left_dx = -24.0
    right_dx = 24.0

    def moved(shape: Shape, dx: float) -> Shape:
        return shape.moved(Location(Vector(dx, 0.0, 0.0)))

    stock_cap_left = moved(reference_parts["cap"], left_dx)
    shaft_left = moved(reference_parts["shaft"], left_dx)
    gimbal_left = moved(reference_parts["gimbal"], left_dx)
    housing_left = moved(Compound(children=[reference_parts["x_pot"], reference_parts["y_pot"], reference_parts["push_switch"]]), left_dx)
    knob_right = moved(knob_target, right_dx)
    shaft_right = moved(reference_parts["shaft"], right_dx)
    gimbal_right = moved(reference_parts["gimbal"], right_dx)
    housing_right = moved(Compound(children=[reference_parts["x_pot"], reference_parts["y_pot"], reference_parts["push_switch"]]), right_dx)

    colors = {
        "stock": (177, 98, 226),
        "shaft": (247, 190, 63),
        "gimbal": (69, 156, 226),
        "housing": (154, 164, 174),
        "original": (55, 205, 139),
        "mismatch": (255, 68, 82),
    }
    objects = [
        (triangles(stock_cap_left), colors["stock"]),
        (triangles(shaft_left), colors["shaft"]),
        (triangles(gimbal_left), colors["gimbal"]),
        (triangles(housing_left), colors["housing"]),
        (triangles(knob_right), colors["original"]),
        (triangles(shaft_right), colors["shaft"]),
        (triangles(gimbal_right), colors["gimbal"]),
        (triangles(housing_right), colors["housing"]),
    ]
    if mismatch is not None:
        objects.append((triangles(moved(mismatch, right_dx), 0.16), colors["mismatch"]))
    world_lines = [
        (np.asarray((-24.0 + JOY_X, JOY_Y, 36.0)), np.asarray((-35.0, JOY_Y, 40.0)), (211, 151, 244, 255), "STOCK KNOB / DOCS71"),
        (np.asarray((-24.0 + JOY_X, JOY_Y, 19.0)), np.asarray((-36.0, JOY_Y, 22.0)), (255, 209, 88, 255), "SHAFT Ø4.8 INFERRED"),
        (np.asarray((-24.0 + JOY_X, JOY_Y, 7.0)), np.asarray((-36.0, JOY_Y, 8.0)), (92, 178, 242, 255), "GIMBAL"),
        (np.asarray((24.0 + JOY_X, JOY_Y, 25.5)), np.asarray((34.0, JOY_Y, 34.0)), (84, 226, 164, 255), "ORIGINAL PRINTED KNOB"),
        (np.asarray((24.0 + JOY_X, JOY_Y, 21.0)), np.asarray((36.0, JOY_Y, 18.0)), (255, 95, 105, 255), "BORE / ADAPTER REQUIRED"),
    ]
    raster_scene(
        RENDER_PATH,
        objects,
        "SZH-EK056 KNOB TREATMENT / FINAL INTENDED STACK",
        "LEFT current docs/71 stock-cap envelope | RIGHT original OneGrip printed knob target concept",
        "purple stock knob REMOVED | yellow shaft + blue gimbal PRESERVED | green original knob | red nominal interface mismatch",
        world_lines=world_lines,
        camera_offset=(74.0, -105.0, 60.0),
        final_size=(1760, 1080),
        supersample=2,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    guard_paths = [DOCS70, DOCS71, DOCS71_JSON, ORIGINAL_SOURCE, ORIGINAL_TARGET, ORIGINAL_PRINTABLE_STL, FEATURE_DUMP, ASSEMBLY_DUMP, REFERENCE_STEP, REFERENCE_JSON]
    before = {str(path.relative_to(ROOT)): sha256(path) for path in guard_paths}

    knob_local, original_moving = local_original_shapes()
    interface = interface_measurements(knob_local, original_moving)
    _, parts, _, _ = build_reference()
    knob_target, target_shift_z = target_original_knob(knob_local)
    mismatch = knob_target & parts["shaft"]
    mismatch_volume = float(mismatch.volume) if mismatch is not None and len(mismatch.solids()) else 0.0
    if mismatch_volume <= 1.0e-7:
        mismatch = None
    shell_rows = shell_rerate(parts, shaft_only_sweep())
    render_stack(parts, knob_target, mismatch)

    docs71 = json.loads(DOCS71_JSON.read_text(encoding="utf-8"))
    stock_knob_rows = [row for row in docs71["staticAudit"]["collisions"] if row["feature"] == "REMOVABLE_KNOB"]
    pcb_terminal_1108 = [
        row for row in docs71["axialDatumSensitivity"]["staticAudit"]["collisions"]
        if row["feature"] == "PCB" and row["target"] == "N1.T4"
    ][0]
    knob_free_sweep_collisions = [row for row in shell_rows["shaftOnlySweep"] if float(row["penetrationMm3"]) > 1.0e-6]
    after = {str(path.relative_to(ROOT)): sha256(path) for path in guard_paths}
    if before != after:
        raise RuntimeError("Read-only source hash guard changed")

    data = {
        "schema": "onegrip.szh_ek056.knob_interface_confirmation.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ ONLY / LOCAL / PRODUCTION GEOMETRY EDIT 0",
        "originalOneGripKnob": {
            "partName": "Small_joystick_attachment",
            "partId": "RHED",
            "sourceFile": str(ORIGINAL_SOURCE.relative_to(ROOT)),
            "exactTargetOccurrence": str(ORIGINAL_TARGET.relative_to(ROOT)),
            "printableStl": str(ORIGINAL_PRINTABLE_STL.relative_to(ROOT)),
            "separatePart": True,
            "sourceFeature": "Extrude 25 / FTcXnBBgATAer7g_13",
            "assemblyMate": "FASTENED to HW504_B <2> moving part",
            "volumeMm3": float(knob_local.volume),
            "bboxInOriginalJoystickFrameMm": bbox(knob_local),
            "interface": interface,
        },
        "szhWebReferenceTopGeometry": {
            "stockKnob": {"label": parts["cap"].label, "class": "B / REMOVABLE NOMINAL ENVELOPE", "exactPhysicalInterfaceKnown": False},
            "shaft": {"label": parts["shaft"].label, "class": "A / MUST PRESERVE", "diameterMm": SHAFT_D, "shape": "CYLINDER INFERRED", "modeledLengthMm": SHAFT_TOP_Z - GIMBAL_H, "pivotToTipMm": SHAFT_TOP_Z - PIVOT_Z, "confidence": "LOW"},
            "gimbal": {"label": parts["gimbal"].label, "class": "A / MUST PRESERVE"},
            "nonRemovableHousing": [parts[name].label for name in ("pcb", "x_pot", "y_pot", "push_switch")],
            "docs71MovingEnvelopeIncludesStockKnob": True,
            "movingEnvelopeMethod": "independent conservative cone using full handle/cap profile through overall top Z=38; not shaft/gimbal-only",
        },
        "compatibility": {
            "szhShaftDiameterMm": SHAFT_D,
            "szhShaftShape": "ROUND CYLINDER — WEB INFERENCE, ACTUAL UNKNOWN",
            "szhModeledShaftLengthAboveGimbalMm": SHAFT_TOP_Z - GIMBAL_H,
            "szhStockExposedLengthBeforeCapEnvelopeMm": 17.0 - GIMBAL_H,
            "szhMaximumModeledInsertionLengthIfStockCapRemovedMm": SHAFT_TOP_Z - GIMBAL_H,
            "originalKnobBoreCrossSectionMm": interface["knobBoreCrossSectionMm"],
            "originalKnobBoreDepthMm": interface["knobBoreDepthMm"],
            "nominalTargetKnobTopZMm": 14.4 + target_shift_z,
            "stockReferenceOverallTopZMm": 38.0,
            "nominalTargetTopReductionMm": 38.0 - (14.4 + target_shift_z),
            "nominalShaftKnobInterferenceMm3": mismatch_volume,
            "verdict": "ADAPTER OR BORE CHANGE REQUIRED",
            "physicalMeasurementRequired": True,
        },
        "docs71Rerate": {
            "stockKnobStaticShellCollisionRows": stock_knob_rows,
            "staticFit": "STOCK-KNOB-TO-SHELL ROWS REMOVED; N1/N2 HOLD UNCHANGED",
            "movingEnvelope": "DOCS71 HOLD IS OVERCONSERVATIVE FOR FINAL INTENT; RECLASSIFY CONDITIONAL UNTIL ACTUAL SHAFT/GIMBAL + INTENDED KNOB SWEEP",
            "shellClearance": "STOCK KNOB GROSS SHELL COLLISIONS ARE NOT FINAL HARD CONSTRAINTS",
            "shaftOnlyInferredSweepShellRelationships": shell_rows["shaftOnlySweep"],
            "shaftOnlyInferredSweepCollisionCount": len(knob_free_sweep_collisions),
            "neutralShaftShellRelationships": shell_rows["neutralShaft"],
            "gimbalHousingShellRelationships": shell_rows["gimbalHousing"],
            "pcbToN1T4AxialSensitivityDepthMm": float(pcb_terminal_1108["overlapDepthProxyMm"]),
            "pcbToN1T4EffectOfKnobRemoval": "UNCHANGED",
        },
        "render": str(RENDER_PATH.relative_to(ROOT)),
        "sourceHashesBeforeAfterIdentical": True,
        "sourceSha256": after,
        "productionGeometryEdits": 0,
        "stepExports": 0,
        "stlExports": 0,
        "stop": "STOP AFTER CONFIRMATION",
    }
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "separatePart": True,
        "interface": interface["interfaceShape"],
        "compatibility": data["compatibility"]["verdict"],
        "docs71MovingIncludedStockKnob": True,
        "shaftOnlySweepShellCollisionCount": len(knob_free_sweep_collisions),
        "productionGeometryEdits": 0,
    }, indent=2, ensure_ascii=False))
    print(f"JSON: {JSON_PATH}")
    print(f"RENDER: {RENDER_PATH}")


if __name__ == "__main__":
    main()
