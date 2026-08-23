"""Build the independent ITS-1105 button FDM test coupon.

This module is deliberately self-contained.  It does not import, edit, or
export any OneGrip production geometry.  The only outputs are a standalone
print-layout STEP/STL and the coupon test document requested for this study.

Default units are millimetres.  Measured switch values can be changed either
in ``CouponConfig`` below or with the command-line overrides shown by
``python -m build123d_workbench.button_fdm_coupon --help``.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Iterable

from build123d import (
    Align,
    Axis,
    Box,
    Compound,
    Cylinder,
    Location,
    Shape,
    Vector,
    export_step,
    export_stl,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "button_fdm_coupon"
STEP_PATH = OUT_DIR / "BUTTON_FDM_TEST_COUPON.step"
STL_PATH = OUT_DIR / "BUTTON_FDM_TEST_COUPON.stl"
DOC_PATH = ROOT / "docs" / "button_fdm_coupon_test.md"


@dataclass(frozen=True)
class CouponConfig:
    """Editable hardware and test parameters.

    ``measured_body_x_mm`` and ``measured_body_y_mm`` are the physical-sample
    dimensions.  ``pocket_seed_mm`` and ``pocket_offsets_mm`` control the
    square pocket coupon independently, so a new measured lot does not require
    editing construction code.
    """

    measured_body_x_mm: float = 6.12
    measured_body_y_mm: float = 6.05
    housing_height_mm: float = 3.56
    actuator_diameter_mm: float = 3.35
    actuator_projection_mm: float = 2.44

    pocket_seed_mm: float = 6.40
    pocket_offsets_mm: tuple[float, ...] = (-0.10, -0.05, 0.0, 0.05, 0.10)

    cap_tail_diameter_mm: float = 4.50
    guide_seed_mm: float = 4.80
    guide_offsets_mm: tuple[float, ...] = (-0.10, -0.05, 0.0, 0.05, 0.10)
    contact_diameter_mm: float = 3.00
    hard_stop_travel_mm: float = 0.350

    minimum_structural_wall_mm: float = 1.20

    @property
    def pocket_variants_mm(self) -> tuple[float, ...]:
        return tuple(round(self.pocket_seed_mm + value, 2) for value in self.pocket_offsets_mm)

    @property
    def guide_variants_mm(self) -> tuple[float, ...]:
        return tuple(round(self.guide_seed_mm + value, 2) for value in self.guide_offsets_mm)


# Print-layout dimensions.  The coupon body is one connected base; caps and
# service gates are intentionally separate bodies in the same STL/STEP.
BASE_X_MM = 76.0
BASE_Y_MM = 52.0
BASE_Z_MM = 2.40
STATION_X_MM = (8.0, 23.0, 38.0, 53.0, 68.0)
POCKET_ROW_Y_MM = 14.0
GUIDE_ROW_Y_MM = 39.0
CAP_PRINT_ROW_Y_MM = 61.0
GATE_PRINT_ROW_Y_MM = 74.0

# Pocket-only fit cells.
FIT_CELL_OUTER_MM = 10.0
FIT_CELL_HEIGHT_MM = 5.20

# Complete mechanism cell.  The 6.80 mm shoulder cavity inside the 9.30 mm
# guide leaves a 1.25 mm structural wall, exceeding the 1.20 mm requirement.
GUIDE_OUTER_MM = 9.30
SHOULDER_CAVITY_MM = 6.80
SHOULDER_SIZE_MM = 6.50
SHOULDER_HEIGHT_MM = 1.20
FRONT_RETENTION_LIP_MM = 1.20
CAP_PAD_MM = 8.40
CAP_PAD_HEIGHT_MM = 2.00
CAP_TAIL_OVERLAP_MM = 0.10
CONTACT_HEIGHT_MM = 0.25
CONTACT_TAIL_GAP_MM = 0.15

# The cap coordinates below are relative to the free actuator top.  At rest,
# the shoulder touches the front retention lip.  Its lower face remains
# exactly 0.350 mm above the independent structural rear stop.
SHOULDER_BOTTOM_REL_MM = 1.25
SHOULDER_TOP_REL_MM = SHOULDER_BOTTOM_REL_MM + SHOULDER_HEIGHT_MM
FRONT_LIP_TOP_REL_MM = SHOULDER_TOP_REL_MM + FRONT_RETENTION_LIP_MM
TAIL_BOTTOM_REL_MM = CONTACT_TAIL_GAP_MM

# Terminal channel seed from the ITS drawing.  Long open slots permit lateral
# switch loading while leaving broad central/corner rear-support areas.
TERMINAL_PITCH_X_MM = 6.50
TERMINAL_PITCH_Y_MM = 4.50
TERMINAL_SLOT_WIDTH_MM = 1.10

# Removable lower side gate.  A central tongue avoids the two terminal rows;
# the external flange gives a tool-free pull surface.
GATE_TONGUE_Y_MM = 3.00
GATE_FLANGE_Y_MM = 8.50
GATE_FLANGE_X_MM = 1.20

# Raised, code-native labels avoid system-font and slicer-font dependencies.
LABEL_HEIGHT_MM = 0.45
LABEL_STROKE_MM = 0.42
LABEL_DIGIT_W_MM = 1.45
LABEL_DIGIT_H_MM = 2.45
LABEL_ADVANCE_MM = 1.82


SEGMENTS = {
    "0": "abcdef",
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
    # Block-style row prefixes, made from the same robust rectangular strokes.
    "G": "acdef",
    "P": "abefg",
}


def moved(shape: Shape, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Shape:
    return shape.moved(Location(Vector(float(x), float(y), float(z))))


def fuse_all(shapes: Iterable[Shape], label: str) -> Shape:
    rows = list(shapes)
    if not rows:
        raise ValueError(f"No shapes supplied for {label}")
    result = rows[0]
    for shape in rows[1:]:
        result = result.fuse(shape)
    result = result.clean()
    result.label = label
    return result


def subtract_all(shape: Shape, cutters: Iterable[Shape], label: str) -> Shape:
    result = shape
    for cutter in cutters:
        result = result - cutter
    result = result.clean()
    result.label = label
    return result


def raised_label(text: str, x_center: float, y_center: float, z_base: float) -> list[Shape]:
    """Return a raised seven-segment/block label as printable solids."""

    advances = [0.56 if char == "." else LABEL_ADVANCE_MM for char in text]
    total = sum(advances) - 0.18
    cursor = x_center - total / 2.0
    rows: list[Shape] = []
    for char, advance in zip(text, advances):
        if char == ".":
            rows.append(
                moved(
                    Box(
                        LABEL_STROKE_MM,
                        LABEL_STROKE_MM,
                        LABEL_HEIGHT_MM,
                        align=(Align.CENTER, Align.CENTER, Align.MIN),
                    ),
                    cursor + LABEL_STROKE_MM / 2.0,
                    y_center - LABEL_DIGIT_H_MM / 2.0 + LABEL_STROKE_MM / 2.0,
                    z_base,
                )
            )
            cursor += advance
            continue

        active = SEGMENTS[char]
        cx = cursor + LABEL_DIGIT_W_MM / 2.0
        cy = y_center
        horizontal = LABEL_DIGIT_W_MM - LABEL_STROKE_MM
        vertical = LABEL_DIGIT_H_MM / 2.0 - LABEL_STROKE_MM
        definitions = {
            "a": (horizontal, LABEL_STROKE_MM, cx, cy + LABEL_DIGIT_H_MM / 2.0 - LABEL_STROKE_MM / 2.0),
            "g": (horizontal, LABEL_STROKE_MM, cx, cy),
            "d": (horizontal, LABEL_STROKE_MM, cx, cy - LABEL_DIGIT_H_MM / 2.0 + LABEL_STROKE_MM / 2.0),
            "f": (LABEL_STROKE_MM, vertical, cursor + LABEL_STROKE_MM / 2.0, cy + LABEL_DIGIT_H_MM / 4.0),
            "b": (LABEL_STROKE_MM, vertical, cursor + LABEL_DIGIT_W_MM - LABEL_STROKE_MM / 2.0, cy + LABEL_DIGIT_H_MM / 4.0),
            "e": (LABEL_STROKE_MM, vertical, cursor + LABEL_STROKE_MM / 2.0, cy - LABEL_DIGIT_H_MM / 4.0),
            "c": (LABEL_STROKE_MM, vertical, cursor + LABEL_DIGIT_W_MM - LABEL_STROKE_MM / 2.0, cy - LABEL_DIGIT_H_MM / 4.0),
        }
        for segment in active:
            width, depth, sx, sy = definitions[segment]
            rows.append(
                moved(
                    Box(width, depth, LABEL_HEIGHT_MM, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                    sx,
                    sy,
                    z_base,
                )
            )
        cursor += advance
    return rows


def seed_label_frame(x_center: float, y_center: float, z_base: float) -> list[Shape]:
    width, depth, stroke = 10.6, 3.65, 0.35
    return [
        moved(Box(width, stroke, LABEL_HEIGHT_MM, align=(Align.CENTER, Align.CENTER, Align.MIN)), x_center, y_center + depth / 2.0, z_base),
        moved(Box(width, stroke, LABEL_HEIGHT_MM, align=(Align.CENTER, Align.CENTER, Align.MIN)), x_center, y_center - depth / 2.0, z_base),
        moved(Box(stroke, depth, LABEL_HEIGHT_MM, align=(Align.CENTER, Align.CENTER, Align.MIN)), x_center - width / 2.0, y_center, z_base),
        moved(Box(stroke, depth, LABEL_HEIGHT_MM, align=(Align.CENTER, Align.CENTER, Align.MIN)), x_center + width / 2.0, y_center, z_base),
    ]


def build_cap(config: CouponConfig) -> Shape:
    """Build one removable cap in coordinates relative to actuator free top."""

    # The pad clears the guide roof throughout the complete 0.350 mm motion.
    # Retention and the hard stop act on the internal shoulder, not the pad.
    pad_bottom = FRONT_LIP_TOP_REL_MM + config.hard_stop_travel_mm
    tail_top = pad_bottom + CAP_TAIL_OVERLAP_MM
    contact = Cylinder(
        config.contact_diameter_mm / 2.0,
        CONTACT_HEIGHT_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    tail = moved(
        Cylinder(
            config.cap_tail_diameter_mm / 2.0,
            tail_top - TAIL_BOTTOM_REL_MM,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        z=TAIL_BOTTOM_REL_MM,
    )
    shoulder = moved(
        Box(
            SHOULDER_SIZE_MM,
            SHOULDER_SIZE_MM,
            SHOULDER_HEIGHT_MM,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        z=SHOULDER_BOTTOM_REL_MM,
    )
    pad = moved(
        Box(CAP_PAD_MM, CAP_PAD_MM, CAP_PAD_HEIGHT_MM, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        z=pad_bottom,
    )
    cap = fuse_all((contact, tail, shoulder, pad), "BUTTON_FDM_REMOVABLE_CAP")
    if len(cap.solids()) != 1:
        raise RuntimeError(f"Cap must be one solid, got {len(cap.solids())}")
    return cap


def terminal_floor_cutters(x: float, y: float) -> list[Shape]:
    channel_min_x = x - TERMINAL_PITCH_X_MM / 2.0 - 0.55
    channel_max_x = x + GUIDE_OUTER_MM / 2.0 + 0.45
    length = channel_max_x - channel_min_x
    return [
        moved(
            Box(length, TERMINAL_SLOT_WIDTH_MM, BASE_Z_MM + 0.20, align=(Align.MIN, Align.CENTER, Align.MIN)),
            channel_min_x,
            y + sign * TERMINAL_PITCH_Y_MM / 2.0,
            -0.10,
        )
        for sign in (-1.0, 1.0)
    ]


def mechanism_levels(config: CouponConfig) -> dict[str, float]:
    switch_front = BASE_Z_MM + config.housing_height_mm
    actuator_top = switch_front + config.actuator_projection_mm
    return {
        "switchFront": switch_front,
        "actuatorTop": actuator_top,
        "rearStopTop": actuator_top + SHOULDER_BOTTOM_REL_MM - config.hard_stop_travel_mm,
        "shoulderBottom": actuator_top + SHOULDER_BOTTOM_REL_MM,
        "shoulderTop": actuator_top + SHOULDER_TOP_REL_MM,
        "frontLipTop": actuator_top + FRONT_LIP_TOP_REL_MM,
    }


def build_mechanism_station(config: CouponConfig, guide_diameter: float, x: float, y: float) -> Shape:
    levels = mechanism_levels(config)
    tower_bottom = BASE_Z_MM - 0.10
    tower_height = levels["frontLipTop"] - tower_bottom
    tower = moved(
        Box(GUIDE_OUTER_MM, GUIDE_OUTER_MM, tower_height, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        x,
        y,
        tower_bottom,
    )

    pocket = moved(
        Box(
            config.pocket_seed_mm,
            config.pocket_seed_mm,
            config.housing_height_mm + 0.20,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        x,
        y,
        BASE_Z_MM,
    )
    lower_service = moved(
        Box(
            GUIDE_OUTER_MM / 2.0 + 0.60,
            config.pocket_seed_mm,
            config.housing_height_mm + 0.20,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        ),
        x,
        y,
        BASE_Z_MM,
    )
    bore_bottom = levels["switchFront"] - 0.10
    bore = moved(
        Cylinder(
            guide_diameter / 2.0,
            levels["frontLipTop"] - bore_bottom + 0.20,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        x,
        y,
        bore_bottom,
    )
    cavity = moved(
        Box(
            SHOULDER_CAVITY_MM,
            SHOULDER_CAVITY_MM,
            levels["shoulderTop"] - levels["rearStopTop"],
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        x,
        y,
        levels["rearStopTop"],
    )
    upper_service = moved(
        Box(
            GUIDE_OUTER_MM / 2.0 + 0.60,
            SHOULDER_CAVITY_MM,
            levels["frontLipTop"] - bore_bottom + 0.20,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        ),
        x,
        y,
        bore_bottom,
    )
    station = subtract_all(
        tower,
        (pocket, lower_service, bore, cavity, upper_service),
        f"GUIDE_{guide_diameter:.2f}_MECHANISM_STATION",
    )
    return station


def build_service_gate(config: CouponConfig) -> Shape:
    """Build the removable lower gate in assembled local coordinates."""

    tongue_x = (GUIDE_OUTER_MM - config.pocket_seed_mm) / 2.0
    tongue = moved(
        Box(tongue_x, GATE_TONGUE_Y_MM, config.housing_height_mm, align=(Align.MIN, Align.CENTER, Align.MIN)),
        config.pocket_seed_mm / 2.0,
        z=BASE_Z_MM,
    )
    flange = moved(
        Box(GATE_FLANGE_X_MM, GATE_FLANGE_Y_MM, config.housing_height_mm, align=(Align.MIN, Align.CENTER, Align.MIN)),
        GUIDE_OUTER_MM / 2.0,
        z=BASE_Z_MM,
    )
    gate = fuse_all((tongue, flange), "BUTTON_FDM_SWITCH_SERVICE_GATE")
    if len(gate.solids()) != 1:
        raise RuntimeError(f"Gate must be one solid, got {len(gate.solids())}")
    return gate


def build_pocket_fit_cell(pocket: float, x: float, y: float) -> Shape:
    tower = moved(
        Box(FIT_CELL_OUTER_MM, FIT_CELL_OUTER_MM, FIT_CELL_HEIGHT_MM, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        x,
        y,
        BASE_Z_MM - 0.10,
    )
    through = moved(
        Box(pocket, pocket, BASE_Z_MM + FIT_CELL_HEIGHT_MM + 0.40, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        x,
        y,
        -0.10,
    )
    cell = (tower - through).clean()
    cell.label = f"POCKET_{pocket:.2f}_FIT_CELL"
    return cell


def place_on_bed(shape: Shape, x: float, y: float) -> Shape:
    # build123d locations can retain shared label metadata when the same source
    # shape is placed repeatedly.  Copy first so STEP child names stay unique.
    shape = copy.copy(shape)
    bbox = shape.bounding_box()
    return moved(
        shape,
        x - (float(bbox.min.X) + float(bbox.max.X)) / 2.0,
        y - (float(bbox.min.Y) + float(bbox.max.Y)) / 2.0,
        -float(bbox.min.Z),
    )


def build_coupon(config: CouponConfig) -> tuple[Compound, Shape, list[Shape], list[Shape]]:
    if len(config.guide_variants_mm) != len(STATION_X_MM):
        raise ValueError("Exactly five guide variants are required")
    if len(config.pocket_variants_mm) != len(STATION_X_MM):
        raise ValueError("Exactly five pocket variants are required")

    positives: list[Shape] = [Box(BASE_X_MM, BASE_Y_MM, BASE_Z_MM, align=(Align.MIN, Align.MIN, Align.MIN))]
    floor_cutters: list[Shape] = []
    label_z = BASE_Z_MM - 0.05

    for index, (x, guide) in enumerate(zip(STATION_X_MM, config.guide_variants_mm)):
        positives.append(build_mechanism_station(config, guide, x, GUIDE_ROW_Y_MM))
        floor_cutters.extend(terminal_floor_cutters(x, GUIDE_ROW_Y_MM))
        positives.extend(raised_label(f"G{guide:.2f}", x, 29.0, label_z))
        if index == 2:
            positives.extend(seed_label_frame(x, 29.0, label_z))

    for index, (x, pocket) in enumerate(zip(STATION_X_MM, config.pocket_variants_mm)):
        positives.append(build_pocket_fit_cell(pocket, x, POCKET_ROW_Y_MM))
        positives.extend(raised_label(f"P{pocket:.2f}", x, 4.0, label_z))
        if index == 2:
            positives.extend(seed_label_frame(x, 4.0, label_z))

    base = fuse_all(positives, "BUTTON_FDM_TEST_COUPON_BASE_POSITIVE")
    base = subtract_all(base, floor_cutters, "BUTTON_FDM_TEST_COUPON_BASE_AND_FIXTURES")
    if len(base.solids()) != 1:
        raise RuntimeError(f"Coupon base must remain connected, got {len(base.solids())} solids")

    caps: list[Shape] = []
    for index, x in enumerate(STATION_X_MM):
        # Rebuild each repeated part so STEP retains distinct child metadata.
        cap_print = build_cap(config).rotate(Axis.X, 180.0)
        cap = place_on_bed(cap_print, x, CAP_PRINT_ROW_Y_MM)
        cap.label = f"CAP_{index + 1}_TAIL_{config.cap_tail_diameter_mm:.2f}"
        caps.append(cap)

    gates: list[Shape] = []
    for index, x in enumerate(STATION_X_MM):
        gate_print = build_service_gate(config).rotate(Axis.Y, -90.0)
        gate = place_on_bed(gate_print, x, GATE_PRINT_ROW_Y_MM)
        gate.label = f"SWITCH_GATE_{index + 1}_POCKET_{config.pocket_seed_mm:.2f}"
        gates.append(gate)

    plate = Compound(children=[base, *caps, *gates], label="BUTTON_FDM_TEST_COUPON_PRINT_LAYOUT")
    return plate, base, caps, gates


def volume(shape: Shape | None) -> float:
    return float(shape.volume) if shape is not None and shape.solids() else 0.0


def validate_geometry(
    config: CouponConfig,
    plate: Compound,
    base: Shape,
    caps: list[Shape],
    gates: list[Shape],
) -> dict[str, object]:
    levels = mechanism_levels(config)
    cap_local = build_cap(config)
    station_rows: list[dict[str, object]] = []
    for x, guide in zip(STATION_X_MM, config.guide_variants_mm):
        station = build_mechanism_station(config, guide, 0.0, 0.0)
        rest_cap = moved(cap_local, z=levels["actuatorTop"])
        pressed_cap = moved(rest_cap, z=-config.hard_stop_travel_mm)
        switch_body = moved(
            Box(
                config.measured_body_x_mm,
                config.measured_body_y_mm,
                config.housing_height_mm,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            ),
            z=BASE_Z_MM,
        )
        actuator = moved(
            Cylinder(
                config.actuator_diameter_mm / 2.0,
                config.actuator_projection_mm,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            ),
            z=levels["switchFront"],
        )
        gate = build_service_gate(config)
        station_rows.append(
            {
                "guideDiameterMm": guide,
                "diametralClearanceMm": round(guide - config.cap_tail_diameter_mm, 3),
                "radialClearanceMm": round((guide - config.cap_tail_diameter_mm) / 2.0, 3),
                "restPenetrationMm3": volume(station & rest_cap),
                "fullPressPenetrationMm3": volume(station & pressed_cap),
                "switchPocketPenetrationMm3": volume(station & switch_body),
                "actuatorGuidePenetrationMm3": volume(station & actuator),
                "gateStationPenetrationMm3": volume(station & gate),
                "gateSwitchPenetrationMm3": volume(gate & switch_body),
                "hardStopGapMm": round(
                    levels["shoulderBottom"] - levels["rearStopTop"], 3
                ),
            }
        )

    guide_side_wall = (GUIDE_OUTER_MM - SHOULDER_CAVITY_MM) / 2.0
    minimum_wall = min(
        guide_side_wall,
        SHOULDER_HEIGHT_MM,
        FRONT_RETENTION_LIP_MM,
        GATE_FLANGE_X_MM,
    )
    bbox = plate.bounding_box()
    checks = {
        "plateValid": bool(plate.is_valid),
        "baseValid": bool(base.is_valid),
        "baseSolidCount": len(base.solids()),
        "capSolidCounts": [len(shape.solids()) for shape in caps],
        "gateSolidCounts": [len(shape.solids()) for shape in gates],
        "printLayoutSolidCount": len(plate.solids()),
        "printLayoutSizeMm": [
            round(float(bbox.size.X), 3),
            round(float(bbox.size.Y), 3),
            round(float(bbox.size.Z), 3),
        ],
        "minimumStructuralWallMm": round(minimum_wall, 3),
        "guideSideWallMm": round(guide_side_wall, 3),
        "minimumWallPass": minimum_wall + 1.0e-9 >= config.minimum_structural_wall_mm,
        "guideStations": station_rows,
    }
    if not checks["plateValid"] or not checks["baseValid"]:
        raise RuntimeError("Coupon contains invalid B-rep geometry")
    if checks["baseSolidCount"] != 1:
        raise RuntimeError("Coupon base is not one connected solid")
    if any(count != 1 for count in checks["capSolidCounts"]):
        raise RuntimeError("At least one cap is fragmented")
    if any(count != 1 for count in checks["gateSolidCounts"]):
        raise RuntimeError("At least one service gate is fragmented")
    if not checks["minimumWallPass"]:
        raise RuntimeError("Minimum structural wall requirement failed")
    if any(float(row["restPenetrationMm3"]) > 1.0e-6 for row in station_rows):
        raise RuntimeError("Cap intersects a guide station at rest")
    if any(float(row["fullPressPenetrationMm3"]) > 1.0e-6 for row in station_rows):
        raise RuntimeError("Cap penetrates the structural hard stop at full press")
    for key in (
        "switchPocketPenetrationMm3",
        "actuatorGuidePenetrationMm3",
        "gateStationPenetrationMm3",
        "gateSwitchPenetrationMm3",
    ):
        if any(float(row[key]) > 1.0e-6 for row in station_rows):
            raise RuntimeError(f"Mechanism interference gate failed: {key}")
    if any(abs(float(row["hardStopGapMm"]) - config.hard_stop_travel_mm) > 1.0e-9 for row in station_rows):
        raise RuntimeError("Hard-stop travel is not exact")
    return checks


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_test_document(config: CouponConfig, checks: dict[str, object]) -> str:
    pocket_rows = "\n".join(
        "| {pocket:.2f} | {x:.3f} | {y:.3f} |  |  |  |".format(
            pocket=pocket,
            x=(pocket - config.measured_body_x_mm) / 2.0,
            y=(pocket - config.measured_body_y_mm) / 2.0,
        )
        for pocket in config.pocket_variants_mm
    )
    guide_rows = "\n".join(
        "| {guide:.2f} | {diametral:.3f} | {radial:.3f} |  |  |  |  |  |".format(
            guide=float(row["guideDiameterMm"]),
            diametral=float(row["diametralClearanceMm"]),
            radial=float(row["radialClearanceMm"]),
        )
        for row in checks["guideStations"]
    )
    size = checks["printLayoutSizeMm"]
    return f"""# BUTTON FDM TEST COUPON — P1S / 0.4 mm nozzle

## Scope and freeze

This is an independent print-test fixture for the completed OneGrip eight-button mechanism. It was built from new primitives only. No production STEP was imported, no production carrier/source parameter was changed, and the generated geometry must not be substituted into production without a separate decision.

## Generated artifacts

- `build123d_workbench/out/button_fdm_coupon/BUTTON_FDM_TEST_COUPON.step`
- `build123d_workbench/out/button_fdm_coupon/BUTTON_FDM_TEST_COUPON.stl`
- print layout: {size[0]:.3f} × {size[1]:.3f} × {size[2]:.3f} mm
- solids in the one-file print layout: {checks['printLayoutSolidCount']} = base/fixtures 1 + removable caps 5 + switch service gates 5

The labels beginning with `G` identify the complete guide/mechanism row. Labels beginning with `P` identify the through pocket-fit row. The framed `G4.80` and `P6.40` are the current seeds.

## Parametric hardware inputs

The defaults are grouped in `CouponConfig` at the top of `build123d_workbench/button_fdm_coupon.py`. They can also be overridden from the command line without editing construction code.

| Parameter | Default |
|---|---:|
| measured switch body X | {config.measured_body_x_mm:.2f} mm |
| measured switch body Y | {config.measured_body_y_mm:.2f} mm |
| housing height | {config.housing_height_mm:.2f} mm |
| actuator diameter | {config.actuator_diameter_mm:.2f} mm |
| actuator projection | {config.actuator_projection_mm:.2f} mm |
| fixed cap tail | Ø{config.cap_tail_diameter_mm:.2f} mm |
| central direct contact | Ø{config.contact_diameter_mm:.2f} mm |
| mechanical hard stop | {config.hard_stop_travel_mm:.3f} mm |
| minimum structural wall in fixture | {checks['minimumStructuralWallMm']:.2f} mm |

Example for a newly measured lot:

```powershell
.\\.venv-build123d\\Scripts\\python.exe -m build123d_workbench.button_fdm_coupon --body-x 6.14 --body-y 6.08 --housing-height 3.58
```

## What is physically represented

Each `G` station has a 6.40 mm side-loading switch pocket, terminal floor channels, broad rear support, removable lower service gate, Ø4.50 solid cap tail, C-shaped guide bore, 6.50 mm retention shoulder, 6.80 mm shoulder cavity, Ø3.00 direct contact, ITS return, and an independent carrier hard stop. At full press the 1.20 mm cap shoulder transfers load to the printed guide at {config.hard_stop_travel_mm:.3f} mm; the switch housing is not the overtravel stop.

The smallest structural guide side wall is `(9.30 - 6.80) / 2 = {checks['guideSideWallMm']:.2f} mm`. The front lip, cap shoulder, and service-gate flange are each 1.20 mm, so the global minimum structural thickness is {checks['minimumStructuralWallMm']:.2f} mm. The cap tail is solid, avoiding an under-thickness cylindrical wall.

## Print setup

1. Import the STL as one object with multiple parts and keep the supplied orientation and 100% scale.
2. Bambu Lab P1S, 0.4 mm nozzle; start with 0.20 mm layer height and at least 3 wall loops.
3. Print without supports. The fixture plate is flat, caps are pad-face-down, and service gates are broad-face-down.
4. Keep XY/hole compensation at zero for the first run. Record filament, nozzle age, layer height, wall generator, line width, cooling, and build-plate type.
5. Do not drill, ream, sand, or lubricate before the as-printed comparison. If a second corrected trial is made, record the correction separately.

## Assembly

1. Remove only loose stringing; preserve the guide-bore surfaces for the first measurement.
2. For a `G` station, feed the ITS-1105 laterally from the open right side. Align the two terminal rows with the two floor slots and seat the housing on the rear support.
3. Slide one service gate into the lower opening until its flange meets the tower. The central tongue closes the 6.40 mm pocket without loading the terminal rows.
4. At the upper opening, slide a cap shoulder and tail laterally into the C-guide. The actuator return should lift the shoulder to the front retention lip.
5. Press only on the cap pad. Stop if the switch or printed wall visibly deforms.
6. The `P` row is a through gauge: insert the same switch squarely from above and push it back out from below. Use the same switch for all five pockets.

## Guide-clearance record

| G label / bore Ø mm | diametral clearance mm | radial clearance mm | wobble | binding | return | click feel | 100 cycles |
|---:|---:|---:|---|---|---|---|---|
{guide_rows}

Select the smallest guide that completes 100 presses without intermittent binding and returns positively on every cycle. Compare wobble only among the passing variants.

## Switch-pocket record

Clearance is calculated from the current measured body, before printer error.

| P label / square pocket mm | X side clearance mm | Y side clearance mm | insertion | retention | removal / damage |
|---:|---:|---:|---|---|---|
{pocket_rows}

Use one insertion direction and keep the switch orientation fixed. Mark any whitening, layer split, gouging, or corner damage after removal.

## Required test items

For the selected guide/pocket combination, record:

- cap wobble: none / slight / objectionable, plus measured lateral play if available
- cap binding: none, intermittent, or continuous; note press direction and temperature
- return: 10/10 slow releases and 10/10 off-axis releases before cycling
- click feel: clean / damped / double-feel / hard-stop masks click
- 0.350 mm hard stop: measured rest-to-stop displacement and measuring method
- switch retention: gate installed, including pull direction and subjective force
- switch removal: tool used, removal force if available, and whether the same switch is reusable
- wall damage: cracks, whitening, delamination, crushed lip, or terminal-slot damage
- repeated press: 100 cycles; inspect again at cycles 25, 50, and 100

### Run sheet

| Field | Result |
|---|---|
| printer / nozzle | Bambu Lab P1S / 0.4 mm |
| filament / lot / dry state |  |
| layer / wall generator / wall count |  |
| slicer XY or hole compensation | 0 for baseline |
| selected G variant |  |
| selected P variant |  |
| rest-to-hard-stop displacement |  |
| cap wobble / binding |  |
| return / click feel |  |
| switch retention / removal |  |
| wall damage after removal |  |
| 25-cycle inspection |  |
| 50-cycle inspection |  |
| 100-cycle result |  |
| decision / next compensation |  |

## Digital geometry checks

- B-rep validity: `PASS`
- connected fixture base: `PASS` (1 solid)
- cap/gate fragmentation: `PASS`
- minimum structural wall: `{checks['minimumStructuralWallMm']:.2f} mm` (`PASS >= {config.minimum_structural_wall_mm:.2f} mm`)
- guide/cap penetration at rest: `0 mm³` for all five variants
- guide/cap penetration at full {config.hard_stop_travel_mm:.3f} mm press: `0 mm³` for all five variants; coincident hard-stop faces only
- switch body/pocket, actuator/guide, gate/fixture, and gate/switch unintended penetration: `0 mm³`
- production source import/write: `0`
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-x", type=float, help="measured switch body X in mm")
    parser.add_argument("--body-y", type=float, help="measured switch body Y in mm")
    parser.add_argument("--housing-height", type=float, help="measured switch housing height in mm")
    parser.add_argument("--actuator-diameter", type=float, help="measured actuator diameter in mm")
    parser.add_argument("--actuator-projection", type=float, help="measured actuator projection in mm")
    parser.add_argument("--pocket-seed", type=float, help="centre pocket size in mm; offsets remain +/-0.10 and +/-0.05")
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> CouponConfig:
    config = CouponConfig()
    overrides = {
        "measured_body_x_mm": args.body_x,
        "measured_body_y_mm": args.body_y,
        "housing_height_mm": args.housing_height,
        "actuator_diameter_mm": args.actuator_diameter,
        "actuator_projection_mm": args.actuator_projection,
        "pocket_seed_mm": args.pocket_seed,
    }
    return replace(config, **{name: value for name, value in overrides.items() if value is not None})


def main() -> None:
    config = config_from_args(parse_args())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plate, base, caps, gates = build_coupon(config)
    checks = validate_geometry(config, plate, base, caps, gates)

    export_step(plate, STEP_PATH)
    export_stl(plate, STL_PATH, tolerance=0.02, angular_tolerance=0.05)
    DOC_PATH.write_text(render_test_document(config, checks), encoding="utf-8")

    print(f"STEP {STEP_PATH.relative_to(ROOT)} {STEP_PATH.stat().st_size} bytes sha256={sha256(STEP_PATH)}")
    print(f"STL  {STL_PATH.relative_to(ROOT)} {STL_PATH.stat().st_size} bytes sha256={sha256(STL_PATH)}")
    print(f"DOC  {DOC_PATH.relative_to(ROOT)} {DOC_PATH.stat().st_size} bytes sha256={sha256(DOC_PATH)}")
    print(f"SOLIDS {checks['printLayoutSolidCount']} SIZE_MM {checks['printLayoutSizeMm']}")
    print("BUTTON_FDM_TEST_COUPON PASS")


if __name__ == "__main__":
    main()
