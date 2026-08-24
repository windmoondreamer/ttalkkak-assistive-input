"""Independent fit audit for the Claude RP2040 tray.

This does not modify production CAD.  It rechecks the current tray placement
against the user's measured RP2040-Zero and power-board envelopes.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from build123d import Align, Box, Location, import_step


ROOT = Path(
    r"C:\Users\guest2\Desktop\ttalkkak-assistive-input-add-onegrip-play-cad-workspace"
    r"\workstreams\onegrip-play"
)
HOUSING_STEP = ROOT / "lower_adapter/local_cad/reference/CONFORMAL_CORE_REFERENCE.step"
ASSEMBLY_STEP = ROOT / "lower_adapter/local_cad/reference/ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step"
TRAY_STEP = ROOT / "lower_adapter/local_cad/export/step/RP2040_ZERO_TRAY.step"

# Claude tray placement and geometry.
TRAY_ORIGIN = np.array([0.5, -44.0, -137.0])
PLATE_T = 1.5
STANDOFF_H = 1.2

# User measurements (mm).
RP_X, RP_Y, RP_T = 17.92, 23.15, 1.60
USB_W, USB_H, USB_PROTRUSION = 8.90, 3.00, 1.28
USB_BOTTOM_FROM_TRAY = 2.50
POWER_SHORT, POWER_LONG = 15.35, 23.24
POWER_UNDERSIDE_PROTRUSION = 2.10

T_ASSEMBLY_TO_GRIP = (
    (0.5760063798429542, 18.785985876151216, -149.95651399999994),
    (0, 0, 180),
)


def one_solid(box):
    solids = box.solids()
    return solids[0] if solids else box


def centered_box(x, y, z, center):
    return one_solid(
        Box(x, y, z, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    ).translate(center)


def bottom_box(x, y, z, center_x, center_y, bottom_z):
    return one_solid(
        Box(x, y, z, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ).translate((center_x, center_y, bottom_z))


def inter_vol(a, b):
    result = a.intersect(b)
    if result is None:
        return 0.0
    solids = result.solids() if hasattr(result, "solids") else [result]
    return float(sum(s.volume for s in solids))


def bbox_may_overlap(a, b):
    aa = a.bounding_box()
    bb = b.bounding_box()
    return not (
        aa.max.X < bb.min.X
        or aa.min.X > bb.max.X
        or aa.max.Y < bb.min.Y
        or aa.min.Y > bb.max.Y
        or aa.max.Z < bb.min.Z
        or aa.min.Z > bb.max.Z
    )


def audit(shape, housing_shell, gimbal_solids):
    return {
        "housing_overlap_mm3": round(inter_vol(shape, housing_shell), 6),
        "gimbal_overlap_mm3": round(
            sum(
                inter_vol(shape, part)
                for part in gimbal_solids
                if bbox_may_overlap(shape, part)
            ),
            6,
        ),
    }


def main():
    housing = import_step(str(HOUSING_STEP))
    housing_shell = max(housing.solids(), key=lambda s: s.volume)
    tray_local = import_step(str(TRAY_STEP))
    tray_shape = max(tray_local.solids(), key=lambda s: s.volume).translate(TRAY_ORIGIN)

    assembly = import_step(str(ASSEMBLY_STEP))
    loc = Location(T_ASSEMBLY_TO_GRIP[0], T_ASSEMBLY_TO_GRIP[1])
    gimbal_solids = None
    for child in assembly.children:
        if child.label.startswith("Base_"):
            gimbal_solids = [s.moved(loc) for s in child.solids()]
            break
    if gimbal_solids is None:
        raise RuntimeError("Base_<1> not found")

    pcb_bottom_z = float(TRAY_ORIGIN[2] + PLATE_T + STANDOFF_H)
    rp_board = bottom_box(
        RP_X, RP_Y, RP_T, float(TRAY_ORIGIN[0]), float(TRAY_ORIGIN[1]), pcb_bottom_z
    )

    # USB opening envelope from the user's measured tray-bottom datum.
    rp_neg_y_edge = float(TRAY_ORIGIN[1] - RP_Y / 2)
    usb_bottom_z = float(TRAY_ORIGIN[2] + USB_BOTTOM_FROM_TRAY)
    usb_external = bottom_box(
        USB_W,
        USB_PROTRUSION,
        USB_H,
        float(TRAY_ORIGIN[0]),
        rp_neg_y_edge - USB_PROTRUSION / 2,
        usb_bottom_z,
    )
    # Straight insertion keepout for a plug/cable.  12 mm is the same provisional
    # length used by Claude, but it is now at the measured opening height.
    usb_insertion = bottom_box(
        USB_W,
        12.0,
        USB_H,
        float(TRAY_ORIGIN[0]),
        rp_neg_y_edge - 6.0,
        usb_bottom_z,
    )

    result = {
        "input_dimensions_mm": {
            "rp2040": [RP_X, RP_Y, RP_T],
            "usb_opening": {
                "bottom_from_tray": USB_BOTTOM_FROM_TRAY,
                "width": USB_W,
                "height": USB_H,
                "external_protrusion": USB_PROTRUSION,
            },
            "power_board": [POWER_SHORT, POWER_LONG],
            "power_board_underside_protrusion": POWER_UNDERSIDE_PROTRUSION,
        },
        "claude_tray_origin_grip_frame": TRAY_ORIGIN.tolist(),
        "derived": {
            "rp_pcb_bottom_z": pcb_bottom_z,
            "rp_actual_margin_in_19x27_5_tray": {
                "x_each_side": round((19.0 - RP_X) / 2, 3),
                "y_each_side": round((27.5 - RP_Y) / 2, 3),
            },
            "usb_opening_bbox": [
                [float(TRAY_ORIGIN[0] - USB_W / 2), rp_neg_y_edge - USB_PROTRUSION, usb_bottom_z],
                [float(TRAY_ORIGIN[0] + USB_W / 2), rp_neg_y_edge, usb_bottom_z + USB_H],
            ],
        },
        "current_position": {
            "rp_board": audit(rp_board, housing_shell, gimbal_solids),
            "rp_board_vs_printed_tray_overlap_mm3": round(
                inter_vol(rp_board, tray_shape), 6
            ),
            "usb_external_1_28mm": audit(usb_external, housing_shell, gimbal_solids),
            "usb_external_vs_printed_tray_overlap_mm3": round(
                inter_vol(usb_external, tray_shape), 6
            ),
            "usb_straight_insertion_12mm": audit(usb_insertion, housing_shell, gimbal_solids),
        },
        "power_board_short_edge_behind_candidates": [],
        "power_board_alternative_orientations": [],
    }

    # Interpret "behind the short edge" as coplanar, on the +Y edge opposite USB.
    # Include a small assembly gap sweep.  Keepout height includes 2.1 mm below the
    # PCB plane plus a provisional 1.6 mm PCB thickness above it.
    power_keepout_h = POWER_UNDERSIDE_PROTRUSION + RP_T
    power_bottom_z = pcb_bottom_z - POWER_UNDERSIDE_PROTRUSION
    for gap in (0.5, 1.0, 2.0):
        center_y = float(
            TRAY_ORIGIN[1] + RP_Y / 2 + gap + POWER_LONG / 2
        )
        board = bottom_box(
            POWER_SHORT,
            POWER_LONG,
            power_keepout_h,
            float(TRAY_ORIGIN[0]),
            center_y,
            power_bottom_z,
        )
        entry = {
            "gap_mm": gap,
            "center": [float(TRAY_ORIGIN[0]), center_y, power_bottom_z],
            "orientation": f"X={POWER_SHORT}, Y={POWER_LONG}",
        }
        entry.update(audit(board, housing_shell, gimbal_solids))
        result["power_board_short_edge_behind_candidates"].append(entry)

    # A small set of practical alternatives, so the audit points to a next move
    # rather than only rejecting the team's coplanar +Y proposal.
    alternatives = []

    # Flat, rotated 90 degrees, still behind the RP board's +Y short edge.
    gap = 1.0
    rotated_center_y = float(TRAY_ORIGIN[1] + RP_Y / 2 + gap + POWER_SHORT / 2)
    alternatives.append((
        "flat_rotated_90_behind_plus_Y",
        bottom_box(POWER_LONG, POWER_SHORT, power_keepout_h,
                   float(TRAY_ORIGIN[0]), rotated_center_y, power_bottom_z),
        [float(TRAY_ORIGIN[0]), rotated_center_y, power_bottom_z],
        [POWER_LONG, POWER_SHORT, power_keepout_h],
    ))

    # Flat on the USB side.  This is mechanically useful to measure even though
    # it competes with the connector/cable route.
    minus_y_center = float(TRAY_ORIGIN[1] - RP_Y / 2 - gap - POWER_LONG / 2)
    alternatives.append((
        "flat_behind_minus_Y_USB_side",
        bottom_box(POWER_SHORT, POWER_LONG, power_keepout_h,
                   float(TRAY_ORIGIN[0]), minus_y_center, power_bottom_z),
        [float(TRAY_ORIGIN[0]), minus_y_center, power_bottom_z],
        [POWER_SHORT, POWER_LONG, power_keepout_h],
    ))

    # Stack above RP2040.  Sweep the free air gap because the RP board's tallest
    # top-side component height was not provided.
    for stack_gap in (1.0, 2.0, 3.0, 4.0):
        stacked_bottom = float(pcb_bottom_z + RP_T + stack_gap)
        alternatives.append((
            f"stacked_above_rp2040_gap_{stack_gap:.0f}mm",
            bottom_box(POWER_SHORT, POWER_LONG, power_keepout_h,
                       float(TRAY_ORIGIN[0]), float(TRAY_ORIGIN[1]), stacked_bottom),
            [float(TRAY_ORIGIN[0]), float(TRAY_ORIGIN[1]), stacked_bottom],
            [POWER_SHORT, POWER_LONG, power_keepout_h],
        ))

    # Edge-on immediately beyond the RP board's +Y and -Y ends.
    edge_y_plus = float(TRAY_ORIGIN[1] + RP_Y / 2 + gap + power_keepout_h / 2)
    edge_y_minus = float(TRAY_ORIGIN[1] - RP_Y / 2 - gap - power_keepout_h / 2)
    edge_center_z = float(pcb_bottom_z + POWER_SHORT / 2)
    for name, cy in (("edge_on_XZ_plus_Y", edge_y_plus),
                     ("edge_on_XZ_minus_Y", edge_y_minus)):
        alternatives.append((
            name,
            centered_box(POWER_LONG, power_keepout_h, POWER_SHORT,
                         (float(TRAY_ORIGIN[0]), cy, edge_center_z)),
            [float(TRAY_ORIGIN[0]), cy, edge_center_z],
            [POWER_LONG, power_keepout_h, POWER_SHORT],
        ))

    # Edge-on to either X side of the RP board.
    edge_x_plus = float(TRAY_ORIGIN[0] + RP_X / 2 + gap + power_keepout_h / 2)
    edge_x_minus = float(TRAY_ORIGIN[0] - RP_X / 2 - gap - power_keepout_h / 2)
    edge_center_z_2 = float(pcb_bottom_z + POWER_SHORT / 2)
    for name, cx in (("edge_on_YZ_plus_X", edge_x_plus),
                     ("edge_on_YZ_minus_X", edge_x_minus)):
        alternatives.append((
            name,
            centered_box(power_keepout_h, POWER_LONG, POWER_SHORT,
                         (cx, float(TRAY_ORIGIN[1]), edge_center_z_2)),
            [cx, float(TRAY_ORIGIN[1]), edge_center_z_2],
            [power_keepout_h, POWER_LONG, POWER_SHORT],
        ))

    for name, shape, center, envelope in alternatives:
        entry = {"name": name, "center_or_xy_bottom_z": center,
                 "envelope_mm": envelope}
        entry.update(audit(shape, housing_shell, gimbal_solids))
        result["power_board_alternative_orientations"].append(entry)

    output = Path(__file__).with_name("rp2040_power_board_fit_review.json")
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nREPORT={output}")


if __name__ == "__main__":
    main()
