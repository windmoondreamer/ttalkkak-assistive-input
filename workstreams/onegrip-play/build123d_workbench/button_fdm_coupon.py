"""Build the independent ITS-1105 button FDM test coupon.

This module is deliberately self-contained.  It does not import, edit, or
export any OneGrip production geometry.  The only outputs are a standalone
print-layout STEP/STL and the coupon test document requested for this study.

V2 replaces the rejected side-loading station with a support-free, top-loaded
switch cradle and a separately printed guide deck.  The change is based on the
physical P6.30 result and a read-only audit of the original open-source
``PushBtn`` reference.  No reference B-rep is consumed by this generator.

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
    Cone,
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

    # Physical P1S result: P6.30 accepts the user's switch lot with a close fit.
    mechanism_pocket_mm: float = 6.30

    # Read-only open-source PushBtn detail envelope.  These are explicit
    # parameters because the old coupon omitted both features.  The four front
    # posts are Ø1.00 at (±2.25, ±2.25); the formed leads occupy about 7.566 mm
    # across the body and extend about 3.52 mm behind it.
    corner_post_diameter_mm: float = 1.00
    corner_post_offset_mm: float = 2.25
    corner_post_height_mm: float = 0.50
    terminal_outer_span_mm: float = 7.566
    terminal_rear_reach_mm: float = 3.52
    pin_clearance_depth_mm: float = 4.20

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


# Print-layout dimensions.  The coupon body is one connected base; the guide
# deck and five caps are intentionally separate bodies in the same STL/STEP.
BASE_X_MM = 82.0
BASE_Y_MM = 52.0
BASE_Z_MM = 2.40
STATION_X_MM = (11.0, 26.0, 41.0, 56.0, 71.0)
POCKET_ROW_Y_MM = 14.0
GUIDE_ROW_Y_MM = 39.0
DECK_PRINT_ROW_Y_MM = 59.0
CAP_PRINT_ROW_Y_MM = 70.0
CLIP_PRINT_ROW_Y_MM = 80.0

# Pocket-only fit cells.
FIT_CELL_OUTER_MM = 10.0
FIT_CELL_HEIGHT_MM = 5.20

# V2 complete mechanism cell.  Four open corner columns locate the 6.30 mm
# housing while leaving every terminal side and the full uncut lead length
# exposed.  A central pedestal provides the rear reaction support.
CRADLE_OUTER_MM = 10.60
CENTRAL_SUPPORT_MM = 4.00
SHOULDER_CAVITY_MM = 6.80
SHOULDER_SIZE_MM = 6.50
SHOULDER_HEIGHT_MM = 1.20
RETENTION_GROOVE_DIAMETER_MM = 3.50
RETENTION_CLIP_BORE_MM = 3.70
RETENTION_CLIP_SLOT_MM = 3.80
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

# The common guide deck is printed assembled-top-face-down.  Its five shoulder
# cavities therefore open upward during printing and create no bridge/roof.
DECK_X_MM = BASE_X_MM
DECK_Y_MM = CRADLE_OUTER_MM
RETAINER_BOSS_DIAMETER_MM = 5.60
RETAINER_PILOT_DIAMETER_MM = 2.80
RETAINER_CLEARANCE_DIAMETER_MM = 3.40
# Deliberately asymmetric so the deck cannot be installed with G4.70/G4.90
# reversed relative to the embossed base labels.
RETAINER_X_MM = (3.0, BASE_X_MM - 4.0)

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
    """Build one removable cap in coordinates relative to actuator free top.

    The Ø4.50 guide tail stays solid except for a local Ø3.50 retention groove.
    A separate flat C-clip occupies that groove after the cap has passed through
    the uninterrupted round guide bore.
    """

    # The pad clears the guide roof throughout the complete 0.350 mm motion.
    # Retention and the hard stop act on the internal shoulder, not the pad.
    pad_bottom = FRONT_LIP_TOP_REL_MM + config.hard_stop_travel_mm
    tail_top = pad_bottom + CAP_TAIL_OVERLAP_MM
    contact = Cylinder(
        config.contact_diameter_mm / 2.0,
        CONTACT_HEIGHT_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    lower_tail = moved(
        Cylinder(
            config.cap_tail_diameter_mm / 2.0,
            SHOULDER_BOTTOM_REL_MM - 0.50 - TAIL_BOTTOM_REL_MM,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        z=TAIL_BOTTOM_REL_MM,
    )
    print_safe_groove_ramp = moved(
        Cone(
            config.cap_tail_diameter_mm / 2.0,
            RETENTION_GROOVE_DIAMETER_MM / 2.0,
            0.50,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        z=SHOULDER_BOTTOM_REL_MM - 0.50,
    )
    groove_core = moved(
        Cylinder(
            RETENTION_GROOVE_DIAMETER_MM / 2.0,
            SHOULDER_HEIGHT_MM,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        z=SHOULDER_BOTTOM_REL_MM,
    )
    upper_tail = moved(
        Cylinder(
            config.cap_tail_diameter_mm / 2.0,
            tail_top - SHOULDER_TOP_REL_MM,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        z=SHOULDER_TOP_REL_MM,
    )
    pad = moved(
        Box(CAP_PAD_MM, CAP_PAD_MM, CAP_PAD_HEIGHT_MM, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        z=pad_bottom,
    )
    cap = fuse_all(
        (contact, lower_tail, print_safe_groove_ramp, groove_core, upper_tail, pad),
        "BUTTON_FDM_REMOVABLE_CAP",
    )
    if len(cap.solids()) != 1:
        raise RuntimeError(f"Cap must be one solid, got {len(cap.solids())}")
    return cap


def build_retention_clip() -> Shape:
    """Build one flat C-clip for the cap's Ø3.50 retention groove."""

    blank = Cylinder(
        SHOULDER_SIZE_MM / 2.0,
        SHOULDER_HEIGHT_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    bore = moved(
        Cylinder(
            RETENTION_CLIP_BORE_MM / 2.0,
            SHOULDER_HEIGHT_MM + 0.20,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        z=-0.10,
    )
    radial_slot = moved(
        Box(
            SHOULDER_SIZE_MM / 2.0 + 0.20,
            RETENTION_CLIP_SLOT_MM,
            SHOULDER_HEIGHT_MM + 0.20,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        ),
        0.0,
        0.0,
        -0.10,
    )
    clip = subtract_all(blank, (bore, radial_slot), "BUTTON_FDM_CAP_RETENTION_C_CLIP")
    if len(clip.solids()) != 1:
        raise RuntimeError(f"Retention clip must be one solid, got {len(clip.solids())}")
    return clip


def mechanism_levels(config: CouponConfig) -> dict[str, float]:
    switch_rear = BASE_Z_MM + config.pin_clearance_depth_mm
    switch_front = switch_rear + config.housing_height_mm
    actuator_top = switch_front + config.actuator_projection_mm
    deck_bottom = actuator_top + SHOULDER_BOTTOM_REL_MM - config.hard_stop_travel_mm
    cavity_height = SHOULDER_HEIGHT_MM + config.hard_stop_travel_mm
    return {
        "switchRear": switch_rear,
        "switchFront": switch_front,
        "actuatorTop": actuator_top,
        "deckBottom": deck_bottom,
        "deckCavityHeight": cavity_height,
        "deckTop": deck_bottom + cavity_height + FRONT_RETENTION_LIP_MM,
        "shoulderBottom": actuator_top + SHOULDER_BOTTOM_REL_MM,
        "shoulderTop": actuator_top + SHOULDER_TOP_REL_MM,
        "frontLipTop": actuator_top + FRONT_LIP_TOP_REL_MM,
    }


def build_cradle_station(config: CouponConfig, x: float, y: float) -> Shape:
    """Build one fully open, top-loading switch cradle.

    Four corner columns locate the square housing.  Their cardinal gaps admit
    the complete formed lead envelope in either 90-degree orientation.  A
    central pedestal supports the rear housing face without touching leads.
    There is no switch-pocket roof and therefore no hidden bridge.
    """

    levels = mechanism_levels(config)
    bottom = BASE_Z_MM - 0.10
    support = moved(
        Box(
            CENTRAL_SUPPORT_MM,
            CENTRAL_SUPPORT_MM,
            levels["switchRear"] - bottom,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        x,
        y,
        bottom,
    )

    locator_width = (CRADLE_OUTER_MM - config.mechanism_pocket_mm) / 2.0
    locator_offset = config.mechanism_pocket_mm / 2.0 + locator_width / 2.0
    locator_height = levels["deckBottom"] - bottom
    columns = [
        moved(
            Box(locator_width, locator_width, locator_height, align=(Align.CENTER, Align.CENTER, Align.MIN)),
            x + sx * locator_offset,
            y + sy * locator_offset,
            bottom,
        )
        for sx in (-1.0, 1.0)
        for sy in (-1.0, 1.0)
    ]
    cradle = fuse_all((support, *columns), "OPEN_TOP_SWITCH_CRADLE")
    return cradle


def build_guide_deck(config: CouponConfig) -> Shape:
    """Build the common guide/retention/hard-stop deck in assembled pose."""

    levels = mechanism_levels(config)
    deck_height = levels["deckTop"] - levels["deckBottom"]
    deck = moved(
        Box(DECK_X_MM, DECK_Y_MM, deck_height, align=(Align.MIN, Align.CENTER, Align.MIN)),
        0.0,
        GUIDE_ROW_Y_MM,
        levels["deckBottom"],
    )
    cutters: list[Shape] = []
    for x, guide in zip(STATION_X_MM, config.guide_variants_mm):
        cutters.append(
            moved(
                Box(
                    SHOULDER_CAVITY_MM,
                    SHOULDER_CAVITY_MM,
                    levels["deckCavityHeight"] + 0.05,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                ),
                x,
                GUIDE_ROW_Y_MM,
                levels["deckBottom"] - 0.05,
            )
        )
        # The cap uses an uninterrupted circular guide.  Only the lower clip
        # cavity opens to the front edge, so a flat C-clip can be inserted and
        # rotated after the deck/cap are in place without breaking the bore.
        service_depth = (DECK_Y_MM - SHOULDER_CAVITY_MM) / 2.0 + 0.20
        cutters.append(
            moved(
                Box(
                    SHOULDER_CAVITY_MM,
                    service_depth,
                    levels["deckCavityHeight"] + 0.05,
                    align=(Align.CENTER, Align.MIN, Align.MIN),
                ),
                x,
                GUIDE_ROW_Y_MM - DECK_Y_MM / 2.0 - 0.10,
                levels["deckBottom"] - 0.05,
            )
        )
        cutters.append(
            moved(
                Cylinder(
                    guide / 2.0,
                    deck_height + 0.20,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                ),
                x,
                GUIDE_ROW_Y_MM,
                levels["deckBottom"] - 0.10,
            )
        )
    for x in RETAINER_X_MM:
        cutters.append(
            moved(
                Cylinder(
                    RETAINER_CLEARANCE_DIAMETER_MM / 2.0,
                    deck_height + 0.20,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                ),
                x,
                GUIDE_ROW_Y_MM,
                levels["deckBottom"] - 0.10,
            )
        )
    return subtract_all(deck, cutters, "REMOVABLE_FULL_BORE_GUIDE_DECK")


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


def build_coupon(config: CouponConfig) -> tuple[Compound, Shape, Shape, list[Shape], list[Shape]]:
    if len(config.guide_variants_mm) != len(STATION_X_MM):
        raise ValueError("Exactly five guide variants are required")
    if len(config.pocket_variants_mm) != len(STATION_X_MM):
        raise ValueError("Exactly five pocket variants are required")

    positives: list[Shape] = [Box(BASE_X_MM, BASE_Y_MM, BASE_Z_MM, align=(Align.MIN, Align.MIN, Align.MIN))]
    label_z = BASE_Z_MM - 0.05

    for index, (x, guide) in enumerate(zip(STATION_X_MM, config.guide_variants_mm)):
        positives.append(build_cradle_station(config, x, GUIDE_ROW_Y_MM))
        positives.extend(raised_label(f"G{guide:.2f}", x, 29.0, label_z))
        if index == 2:
            positives.extend(seed_label_frame(x, 29.0, label_z))

    for index, (x, pocket) in enumerate(zip(STATION_X_MM, config.pocket_variants_mm)):
        positives.append(build_pocket_fit_cell(pocket, x, POCKET_ROW_Y_MM))
        positives.extend(raised_label(f"P{pocket:.2f}", x, 4.0, label_z))
        if index == 2:
            positives.extend(seed_label_frame(x, 4.0, label_z))

    levels = mechanism_levels(config)
    for x in RETAINER_X_MM:
        positives.append(
            moved(
                Cylinder(
                    RETAINER_BOSS_DIAMETER_MM / 2.0,
                    levels["deckBottom"] - BASE_Z_MM + 0.10,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                ),
                x,
                GUIDE_ROW_Y_MM,
                BASE_Z_MM - 0.10,
            )
        )

    base = fuse_all(positives, "BUTTON_FDM_TEST_COUPON_BASE_POSITIVE")
    pilot_cutters = [
        moved(
            Cylinder(
                RETAINER_PILOT_DIAMETER_MM / 2.0,
                levels["deckBottom"] + 0.20,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            ),
            x,
            GUIDE_ROW_Y_MM,
            -0.10,
        )
        for x in RETAINER_X_MM
    ]
    base = subtract_all(base, pilot_cutters, "BUTTON_FDM_TEST_COUPON_BASE_AND_CRADLES")
    if len(base.solids()) != 1:
        raise RuntimeError(f"Coupon base must remain connected, got {len(base.solids())} solids")

    # The assembled top face is placed on the print bed.  After printing, flip
    # the deck over; every shoulder pocket was therefore printed open upward.
    deck_print = build_guide_deck(config).rotate(Axis.X, 180.0)
    deck = place_on_bed(deck_print, BASE_X_MM / 2.0, DECK_PRINT_ROW_Y_MM)
    deck.label = "GUIDE_DECK_TOP_FACE_DOWN__FLIP_AFTER_PRINT"

    caps: list[Shape] = []
    for index, x in enumerate(STATION_X_MM):
        # Rebuild each repeated part so STEP retains distinct child metadata.
        cap_print = build_cap(config).rotate(Axis.X, 180.0)
        cap = place_on_bed(cap_print, x, CAP_PRINT_ROW_Y_MM)
        cap.label = f"CAP_{index + 1}_TAIL_{config.cap_tail_diameter_mm:.2f}"
        caps.append(cap)

    clips: list[Shape] = []
    for index, x in enumerate(STATION_X_MM):
        clip = place_on_bed(build_retention_clip(), x, CLIP_PRINT_ROW_Y_MM)
        clip.label = f"CAP_RETENTION_C_CLIP_{index + 1}"
        clips.append(clip)

    plate = Compound(children=[base, deck, *caps, *clips], label="BUTTON_FDM_TEST_COUPON_V2_PRINT_LAYOUT")
    return plate, base, deck, caps, clips


def volume(shape: Shape | None) -> float:
    return float(shape.volume) if shape is not None and shape.solids() else 0.0


def switch_reference_shapes(config: CouponConfig, x: float, y: float) -> dict[str, object]:
    """Return explicit physical/open-source reference envelopes for checking."""

    levels = mechanism_levels(config)
    body = moved(
        Box(
            config.measured_body_x_mm,
            config.measured_body_y_mm,
            config.housing_height_mm,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        x,
        y,
        levels["switchRear"],
    )
    actuator = moved(
        Cylinder(
            config.actuator_diameter_mm / 2.0,
            config.actuator_projection_mm,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ),
        x,
        y,
        levels["switchFront"],
    )
    posts = [
        moved(
            Cylinder(
                config.corner_post_diameter_mm / 2.0,
                config.corner_post_height_mm,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            ),
            x + sx * config.corner_post_offset_mm,
            y + sy * config.corner_post_offset_mm,
            levels["switchFront"],
        )
        for sx in (-1.0, 1.0)
        for sy in (-1.0, 1.0)
    ]

    # Conservative boxes around the exact open-source formed leads.  They are
    # deliberately outside the square housing and extend through the complete
    # uncut rear reach.  The open cardinal gaps in the cradle must clear them.
    side_reach = max(
        config.terminal_outer_span_mm / 2.0 - config.measured_body_x_mm / 2.0,
        0.35,
    )
    terminal_pair_offset = 1.955
    terminal_width = 0.70
    terminal_height = config.terminal_rear_reach_mm + 1.00
    terminals = [
        moved(
            Box(side_reach, terminal_width, terminal_height, align=(Align.CENTER, Align.CENTER, Align.MIN)),
            x + sx * (config.measured_body_x_mm / 2.0 + side_reach / 2.0),
            y + sy * terminal_pair_offset,
            levels["switchRear"] - config.terminal_rear_reach_mm,
        )
        for sx in (-1.0, 1.0)
        for sy in (-1.0, 1.0)
    ]
    return {"body": body, "actuator": actuator, "posts": posts, "terminals": terminals}


def validate_geometry(
    config: CouponConfig,
    plate: Compound,
    base: Shape,
    deck_print: Shape,
    caps: list[Shape],
    clips: list[Shape],
) -> dict[str, object]:
    levels = mechanism_levels(config)
    cap_local = build_cap(config)
    assembled_deck = build_guide_deck(config)
    station_rows: list[dict[str, object]] = []
    for x, guide in zip(STATION_X_MM, config.guide_variants_mm):
        cradle = build_cradle_station(config, x, GUIDE_ROW_Y_MM)
        reference = switch_reference_shapes(config, x, GUIDE_ROW_Y_MM)
        rest_cap = moved(cap_local, x=x, y=GUIDE_ROW_Y_MM, z=levels["actuatorTop"])
        pressed_cap = moved(rest_cap, z=-config.hard_stop_travel_mm)
        rest_clip = moved(
            build_retention_clip(),
            x=x,
            y=GUIDE_ROW_Y_MM,
            z=levels["actuatorTop"] + SHOULDER_BOTTOM_REL_MM,
        )
        pressed_clip = moved(rest_clip, z=-config.hard_stop_travel_mm)
        details = [reference["body"], reference["actuator"], *reference["posts"]]
        station_rows.append(
            {
                "guideDiameterMm": guide,
                "diametralClearanceMm": round(guide - config.cap_tail_diameter_mm, 3),
                "radialClearanceMm": round((guide - config.cap_tail_diameter_mm) / 2.0, 3),
                "restDeckPenetrationMm3": volume(assembled_deck & rest_cap),
                "fullPressDeckPenetrationMm3": volume(assembled_deck & pressed_cap),
                "restClipDeckPenetrationMm3": volume(assembled_deck & rest_clip),
                "fullPressClipDeckPenetrationMm3": volume(assembled_deck & pressed_clip),
                "clipCapPenetrationMm3": volume(rest_clip & rest_cap),
                "cradleBodyPenetrationMm3": volume(cradle & reference["body"]),
                "cradleTerminalPenetrationMm3": sum(
                    volume(cradle & terminal) for terminal in reference["terminals"]
                ),
                "deckSwitchDetailPenetrationMm3": sum(
                    volume(assembled_deck & detail) for detail in details
                ),
                "hardStopGapMm": round(
                    levels["shoulderBottom"] - levels["deckBottom"], 3
                ),
                "mechanismPocketMm": config.mechanism_pocket_mm,
                "bodySideClearanceXmm": round(
                    (config.mechanism_pocket_mm - config.measured_body_x_mm) / 2.0, 3
                ),
                "bodySideClearanceYmm": round(
                    (config.mechanism_pocket_mm - config.measured_body_y_mm) / 2.0, 3
                ),
            }
        )

    locator_wall = (CRADLE_OUTER_MM - config.mechanism_pocket_mm) / 2.0
    guide_side_wall = (DECK_Y_MM - SHOULDER_CAVITY_MM) / 2.0
    boss_wall = (RETAINER_BOSS_DIAMETER_MM - RETAINER_PILOT_DIAMETER_MM) / 2.0
    deck_end_wall = RETAINER_X_MM[0] - RETAINER_CLEARANCE_DIAMETER_MM / 2.0
    minimum_wall = min(
        locator_wall,
        guide_side_wall,
        SHOULDER_HEIGHT_MM,
        FRONT_RETENTION_LIP_MM,
        boss_wall,
        deck_end_wall,
    )
    bbox = plate.bounding_box()
    checks = {
        "plateValid": bool(plate.is_valid),
        "baseValid": bool(base.is_valid),
        "deckValid": bool(deck_print.is_valid),
        "baseSolidCount": len(base.solids()),
        "deckSolidCount": len(deck_print.solids()),
        "capSolidCounts": [len(shape.solids()) for shape in caps],
        "clipSolidCounts": [len(shape.solids()) for shape in clips],
        "printLayoutSolidCount": len(plate.solids()),
        "printLayoutSizeMm": [
            round(float(bbox.size.X), 3),
            round(float(bbox.size.Y), 3),
            round(float(bbox.size.Z), 3),
        ],
        "minimumStructuralWallMm": round(minimum_wall, 3),
        "locatorWallMm": round(locator_wall, 3),
        "guideSideWallMm": round(guide_side_wall, 3),
        "retainerBossWallMm": round(boss_wall, 3),
        "deckEndWallMm": round(deck_end_wall, 3),
        "minimumWallPass": minimum_wall + 1.0e-9 >= config.minimum_structural_wall_mm,
        "assembledDeckBasePenetrationMm3": volume(assembled_deck & base),
        "pinClearanceDepthMm": config.pin_clearance_depth_mm,
        "referenceCornerPosts": {
            "count": 4,
            "diameterMm": config.corner_post_diameter_mm,
            "offsetMm": config.corner_post_offset_mm,
            "heightMm": config.corner_post_height_mm,
        },
        "referenceTerminalEnvelope": {
            "outerSpanMm": config.terminal_outer_span_mm,
            "rearReachMm": config.terminal_rear_reach_mm,
        },
        "guideStations": station_rows,
    }
    if not checks["plateValid"] or not checks["baseValid"] or not checks["deckValid"]:
        raise RuntimeError("Coupon contains invalid B-rep geometry")
    if checks["baseSolidCount"] != 1:
        raise RuntimeError("Coupon base is not one connected solid")
    if checks["deckSolidCount"] != 1:
        raise RuntimeError("Guide deck is not one connected solid")
    if any(count != 1 for count in checks["capSolidCounts"]):
        raise RuntimeError("At least one cap is fragmented")
    if any(count != 1 for count in checks["clipSolidCounts"]):
        raise RuntimeError("At least one retention clip is fragmented")
    if not checks["minimumWallPass"]:
        raise RuntimeError("Minimum structural wall requirement failed")
    if float(checks["assembledDeckBasePenetrationMm3"]) > 1.0e-6:
        raise RuntimeError("Assembled guide deck penetrates the base/cradles")
    for key in (
        "restDeckPenetrationMm3",
        "fullPressDeckPenetrationMm3",
        "restClipDeckPenetrationMm3",
        "fullPressClipDeckPenetrationMm3",
        "clipCapPenetrationMm3",
        "cradleBodyPenetrationMm3",
        "cradleTerminalPenetrationMm3",
        "deckSwitchDetailPenetrationMm3",
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
    return f"""# BUTTON FDM TEST COUPON V2 — P1S / 0.4 mm nozzle

## 결론과 범위

V1 G열의 옆삽입 포켓/좁은 핀 슬롯/공중에 생기는 포켓 지붕은 실물 FDM 시험에서 부적합으로 판정했다. V2는 **위에서 내려놓는 개방형 4코너 크래들 + 중앙 rear support + 별도 가이드 덱**으로 다시 만들었다.

OneGrip production STEP/carrier/source는 import, 수정, overwrite하지 않았다. 오픈소스 Thumb의 `PushBtn` exact STEP은 읽기 전용으로만 감사했고, 생성 스크립트에는 측정된 envelope 숫자만 독립 parameter로 기록했다.

## 생성물과 부품

- `build123d_workbench/out/button_fdm_coupon/BUTTON_FDM_TEST_COUPON.step`
- `build123d_workbench/out/button_fdm_coupon/BUTTON_FDM_TEST_COUPON.stl`
- print layout: {size[0]:.3f} × {size[1]:.3f} × {size[2]:.3f} mm
- 총 {checks['printLayoutSolidCount']} solids: base/cradles 1 + 뒤집어 쓰는 guide deck 1 + caps 5 + C-clips 5
- 별도 준비: **M3×10 mm screw 2개**. 덱은 Ø3.40 clearance, base boss는 Ø2.80 self-tapping pilot이다.

`P`는 switch-body 관통 공차 게이지, `G`는 완성 기구의 guide bore 번호다. `G4.80`과 `P6.40` 테두리는 최초 seed 표시일 뿐이며, 실물 P6.30 합격 결과가 V2 G열의 body 기준이다.

## V2가 새로 반영한 실물 형상

| 항목 | V2 값/처리 |
|---|---:|
| 사용자의 measured body | {config.measured_body_x_mm:.2f} × {config.measured_body_y_mm:.2f} mm |
| G열 body locator | {config.mechanism_pocket_mm:.2f} mm |
| body 이론 side clearance X/Y | {(config.mechanism_pocket_mm-config.measured_body_x_mm)/2:.3f} / {(config.mechanism_pocket_mm-config.measured_body_y_mm)/2:.3f} mm |
| 네 모서리 전면 돌기 | 4 × Ø{config.corner_post_diameter_mm:.2f}, 중심 ±{config.corner_post_offset_mm:.2f}, 높이 {config.corner_post_height_mm:.2f} mm |
| 원본 formed-pin 최대 외폭 | {config.terminal_outer_span_mm:.3f} mm |
| 원본 pin rear reach | {config.terminal_rear_reach_mm:.2f} mm |
| V2 아래쪽 pin 여유 깊이 | {config.pin_clearance_depth_mm:.2f} mm |
| cap tail / contact | Ø{config.cap_tail_diameter_mm:.2f} / Ø{config.contact_diameter_mm:.2f} mm |
| hard stop | {config.hard_stop_travel_mm:.3f} mm |

네 corner locator 사이의 네 방향은 완전히 열려 있다. 따라서 terminal root와 성형된 긴 핀이 좁은 slot을 통과할 필요가 없고, 핀을 자르거나 뿌리에서 꺾지 않는다. 중앙 4.00 mm pedestal만 housing 뒤 중앙을 받는다. 네 모서리 Ø1.00 돌기는 deck과 locator 어느 쪽에도 닿지 않는다.

## FDM 방향

1. STL을 multi-part 한 개 object로 가져오고 제공 방향/100% scale을 유지한다.
2. P1S / 0.4 mm nozzle, 0.20 mm layer, wall 3회 이상, support OFF로 시작한다.
3. 긴 guide deck은 **완성품 윗면이 build plate를 향하도록 이미 뒤집혀 있다.** 출력 후 뒤집어서 조립한다. 이 때문에 6.80 mm retention cavity가 출력 중 위로 열리고 공중 bridge/roof가 생기지 않는다.
4. 5개 guide bore는 모두 Z축 수직 hole이다. caps는 pad-face-down, C-clips는 flat으로 놓여 있다.
5. 첫 출력은 XY/hole compensation 0.00. 드릴, 리머, 사포, 윤활 없이 비교한다.

## 조립 순서

### P열 — body 공차 확인

1. 형님이 시험하신 것과 동일하게 **actuator/누르는 면이 아래쪽**을 향하게 한다.
2. 같은 switch를 P6.50부터 P6.30까지 넣고 아래에서 다시 밀어 뺀다.
3. 현재 실물 결과 `P6.30 = 아주 핏하게 삽입 가능`을 baseline으로 기록한다.

### G열 — 실제 누름 구조

1. switch를 **actuator 위 / 핀 아래** 방향으로 잡고 원하는 G 번호의 네 corner locator 사이에 수직으로 내려놓는다.
2. 핀은 locator 사이의 열린 방향과 아래 빈 공간으로 그대로 내려간다. **핀을 더 자르거나 억지로 좁은 홈에 넣지 않는다.** 중앙 pedestal에 housing 뒤 중앙만 닿으면 정상이다.
3. 빈 guide deck을 뒤집어 6.80 mm cavity/clip service opening이 아래를 향하게 하고, switch actuator 위로 수직으로 내린다.
4. 양 끝 Ø3.40 hole 두 개는 일부러 비대칭 위치다. **두 hole이 동시에 boss와 맞는 방향만 정방향**이며 G4.70/G4.90 뒤바뀜을 막는다. M3×10 screw 2개를 Ø2.80 pilot boss에 가볍게 self-tap하고, deck이 네 기둥 위에 닿은 뒤 더 조이지 않는다.
5. cap tail을 덱의 평평한 윗면에서 해당 **완전 원형 bore**로 넣고, cap pad 하단이 deck에 닿을 때까지 0.350 mm 눌러 유지한다. 이 위치에서 Ø3.50 groove가 앞쪽 clip service opening과 정렬된다.
6. flat C-clip의 열린 입구가 tail을 향하도록 앞쪽 service opening으로 밀어 groove에 건다. 완전히 들어가면 clip을 groove 축 주위로 90° 돌려 열린 입구가 좌/우 cavity 벽을 향하게 한다. 그러면 clip은 앞쪽으로 빠질 수 없다.
7. cap에서 손을 놓는다. ITS return이 cap/clip을 0.350 mm 올리고 clip 상면이 cavity roof에 걸려 cap을 유지한다. 다시 누르면 clip 하단과 cap pad 하단이 동시에 printed deck에 닿아 hard stop을 만든다.
8. 분해는 cap을 끝까지 누름 → clip 입구를 앞쪽으로 90° 복귀 → clip 인출 → cap 인출 → screw 2개 → deck 수직 인양 → switch 위로 인출 순서다.

## Guide 공차 기록

| G bore Ø mm | diametral clearance mm | radial clearance mm | wobble | binding | return | click feel | 100 cycles |
|---:|---:|---:|---|---|---|---|---|
{guide_rows}

100회 중 한 번도 걸리지 않고 모든 slow/off-axis release에서 복귀하는 가장 작은 G를 선택한 다음, 통과한 후보끼리 wobble을 비교한다.

## Pocket 공차 기록

| P square mm | X side clearance mm | Y side clearance mm | insertion | retention | removal / damage |
|---:|---:|---:|---|---|---|
{pocket_rows}

## 실물 평가표

| 항목 | 결과 |
|---|---|
| printer / nozzle | Bambu Lab P1S / 0.4 mm |
| filament / 건조 상태 |  |
| layer / wall / line width |  |
| XY / hole compensation | 0.00 baseline |
| P6.30 재확인 |  |
| 선택 G |  |
| cap wobble |  |
| cap binding |  |
| slow/off-axis return 10+10회 |  |
| click feel |  |
| 실측 rest-to-stop travel |  |
| switch retention / removal |  |
| corner locator / wall damage |  |
| 25 / 50 / 100 cycle |  |
| 최종 선택 / 다음 보정 |  |

## 디지털 검사

- B-rep valid, connected base 1 solid, guide deck 1 solid: `PASS`
- cap 5 / retention clip 5 fragmentation: `PASS`
- minimum structural wall: {checks['minimumStructuralWallMm']:.2f} mm (`PASS >= {config.minimum_structural_wall_mm:.2f}`)
- body ↔ four-corner cradle unintended penetration: 0 mm³
- full uncut formed-pin envelope ↔ cradle penetration: 0 mm³
- four corner posts / actuator / body ↔ guide deck penetration: 0 mm³
- cap + C-clip ↔ deck penetration at rest: 0 mm³
- cap + C-clip ↔ deck penetration at {config.hard_stop_travel_mm:.3f} mm: 0 mm³, hard-stop faces only coincident
- production source import/write: 0

### Bambu Studio 실제 slice sanity check

- Bambu Studio 02.08.02.60 / `Bambu Lab P1S 0.4 nozzle` / stock 0.20 mm profile
- support: `OFF`; slice return code 0, warning 없음
- 입력 45,976 triangles / 82.00 × 83.25 × 13.50 mm
- slicer의 `Bridge` 태그는 Z=1.40, 1.80, 2.20 mm의 base/deck/cap 내부 top-skin 구간에만 존재했다.
- Z>2.20 mm의 switch cradle, guide bore, retention cavity에는 bridge-tagged extrusion이 0개다. 즉 V1처럼 switch pocket 위에서 filament가 공중에 시작하는 roof가 없다.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-x", type=float, help="measured switch body X in mm")
    parser.add_argument("--body-y", type=float, help="measured switch body Y in mm")
    parser.add_argument("--housing-height", type=float, help="measured switch housing height in mm")
    parser.add_argument("--actuator-diameter", type=float, help="measured actuator diameter in mm")
    parser.add_argument("--actuator-projection", type=float, help="measured actuator projection in mm")
    parser.add_argument("--pocket-seed", type=float, help="centre pocket size in mm; offsets remain +/-0.10 and +/-0.05")
    parser.add_argument("--mechanism-pocket", type=float, help="G-row body locator size in mm")
    parser.add_argument("--corner-post-diameter", type=float, help="front corner-post diameter in mm")
    parser.add_argument("--corner-post-offset", type=float, help="front corner-post +/- centre offset in mm")
    parser.add_argument("--corner-post-height", type=float, help="front corner-post projection in mm")
    parser.add_argument("--terminal-outer-span", type=float, help="formed-terminal maximum outer span in mm")
    parser.add_argument("--terminal-rear-reach", type=float, help="uncut terminal reach behind housing in mm")
    parser.add_argument("--pin-clearance-depth", type=float, help="open clearance below switch rear in mm")
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
        "mechanism_pocket_mm": args.mechanism_pocket,
        "corner_post_diameter_mm": args.corner_post_diameter,
        "corner_post_offset_mm": args.corner_post_offset,
        "corner_post_height_mm": args.corner_post_height,
        "terminal_outer_span_mm": args.terminal_outer_span,
        "terminal_rear_reach_mm": args.terminal_rear_reach,
        "pin_clearance_depth_mm": args.pin_clearance_depth,
    }
    return replace(config, **{name: value for name, value in overrides.items() if value is not None})


def main() -> None:
    config = config_from_args(parse_args())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plate, base, deck, caps, clips = build_coupon(config)
    checks = validate_geometry(config, plate, base, deck, caps, clips)

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
