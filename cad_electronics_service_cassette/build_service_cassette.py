"""OneGrip Play RP2040 + power-board side-by-side service cassette.

This replaces the inaccessible tray buried behind the stock gimbal.  Both
boards are top-loaded independently and remain serviceable after assembly.
The exact stock spring-base integration is handled separately by
``integrate_stock_spring_base_cassette.py``,
which imports the current open-source Option-C carrier.  This file generates
only the cassette, lid, fit coupons and board surrogates.
All dimensions are millimetres.
"""

from __future__ import annotations

import json
from pathlib import Path

from build123d import (
    Align,
    Box,
    Cylinder,
    Pos,
    export_step,
    export_stl,
)


HERE = Path(__file__).resolve().parent
OUT = HERE / "export"

# User measurements.
RP_X, RP_Y, RP_T = 17.92, 23.15, 1.60
RP_USB_W, RP_USB_H = 8.90, 3.00
RP_USB_BOTTOM = 2.50
RP_USB_PROTRUSION = 1.28

POWER_X_NATIVE, POWER_Y_NATIVE = 15.35, 23.24
POWER_UNDERSIDE = 2.10
POWER_PCB_T = 1.60  # provisional until the physical board thickness is measured

# The power board is rotated 90 degrees in plan, beside the RP2040 short edge.
POWER_X, POWER_Y = POWER_Y_NATIVE, POWER_X_NATIVE

# Human-assembly-first enclosure.
OUTER_X, OUTER_Y = 36.0, 45.0
BODY_H = 12.0
BASE_T = 1.60
WALL = 1.60
LID_T = 1.80
LID_GAP = 0.20

# Physical fit feedback, 2026-08-24:
# - the 17.92 mm RP2040 width fitted correctly, so its X clearance is retained;
# - the 23.15 mm insertion direction was too tight, so its Y clearance is
#   increased to 0.60 mm per end (1.20 mm total).
# The power board pocket already fitted and is intentionally unchanged.
RP_CLEARANCE_X = 0.25
RP_CLEARANCE_Y = 0.60
POWER_CLEARANCE_X = 0.25
POWER_CLEARANCE_Y = 0.25

# One-file print layout: the cassette body and lid remain independent here.
PRINT_PART_GAP = 5.0

# Board seating levels.
RP_SUPPORT_H = 1.20
RP_PCB_BOTTOM = BASE_T + RP_SUPPORT_H
POWER_SUPPORT_H = POWER_UNDERSIDE + 0.30
POWER_PCB_BOTTOM = BASE_T + POWER_SUPPORT_H

# Pocket layout along Y.
INNER_Y = OUTER_Y - 2 * WALL
RP_POCKET_X = RP_X + 2 * RP_CLEARANCE_X
RP_POCKET_Y = RP_Y + 2 * RP_CLEARANCE_Y
POWER_POCKET_X = POWER_X + 2 * POWER_CLEARANCE_X
POWER_POCKET_Y = POWER_Y + 2 * POWER_CLEARANCE_Y
DIVIDER_T = 1.20
RP_CENTER_Y = -INNER_Y / 2 + RP_POCKET_Y / 2
DIVIDER_Y = -INNER_Y / 2 + RP_POCKET_Y + DIVIDER_T / 2
POWER_CENTER_Y = DIVIDER_Y + DIVIDER_T / 2 + POWER_POCKET_Y / 2

# Common hardware.  M3 self-tapping screws match the rest of the project.
PILOT_D = 2.50
LID_CLEAR_D = 3.40
COUNTERBORE_D = 6.20
BOSS_D = 6.00
BOSS_CENTERS = (
    (-15.0, RP_CENTER_Y),
    (+15.0, RP_CENTER_Y),
    (-15.0, POWER_CENTER_Y),
    (+15.0, POWER_CENTER_Y),
)


def one(shape):
    solids = shape.solids()
    return solids[0] if len(solids) == 1 else shape


def make_body():
    outer = Box(
        OUTER_X, OUTER_Y, BODY_H,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    cavity = Pos(0, 0, BASE_T) * Box(
        OUTER_X - 2 * WALL,
        OUTER_Y - 2 * WALL,
        BODY_H - BASE_T + 0.5,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    body = outer - cavity

    # Four lid bosses, drilled vertically.  The board pockets remain open and
    # no fastener is hidden beneath either board.
    for x, y in BOSS_CENTERS:
        boss = Pos(x, y, BASE_T) * Cylinder(
            BOSS_D / 2, BODY_H - BASE_T,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        body = body + boss
        pilot = Pos(x, y, BODY_H - 7.0) * Cylinder(
            PILOT_D / 2, 7.5,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        body = body - pilot

    # RP2040 support pads.  The -Y connector end remains completely open.
    for x in (-RP_X / 2 + 1.8, RP_X / 2 - 1.8):
        for y in (RP_CENTER_Y - RP_Y / 2 + 2.2, RP_CENTER_Y + RP_Y / 2 - 2.2):
            pad = Pos(x, y, BASE_T) * Box(
                2.4, 2.4, RP_SUPPORT_H,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            body = body + pad

    # Power-board support pads are tall enough for its measured 2.1 mm lower
    # protrusion.  Only corner areas are touched; the underside centre is open.
    for x in (-POWER_X / 2 + 2.0, POWER_X / 2 - 2.0):
        for y in (POWER_CENTER_Y - POWER_Y / 2 + 2.0,
                  POWER_CENTER_Y + POWER_Y / 2 - 2.0):
            pad = Pos(x, y, BASE_T) * Box(
                2.6, 2.6, POWER_SUPPORT_H,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            body = body + pad

    # Low guide blocks centre each board but stop below the component side.
    guide_t = 1.00
    guide_h_rp = RP_SUPPORT_H + RP_T + 0.8
    rp_guide_x = RP_X / 2 + RP_CLEARANCE_X + guide_t / 2
    for x in (-rp_guide_x, rp_guide_x):
        for y in (RP_CENTER_Y - 6.0, RP_CENTER_Y + 6.0):
            body = body + Pos(x, y, BASE_T) * Box(
                guide_t, 3.5, guide_h_rp,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )

    guide_h_power = POWER_SUPPORT_H + POWER_PCB_T + 0.8
    power_guide_x = POWER_X / 2 + POWER_CLEARANCE_X + guide_t / 2
    for x in (-power_guide_x, power_guide_x):
        for y in (POWER_CENTER_Y - 4.3, POWER_CENTER_Y + 4.3):
            body = body + Pos(x, y, BASE_T) * Box(
                guide_t, 3.0, guide_h_power,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )

    # Low divider keeps the two boards independent and includes a wiring gate.
    divider_h = 5.8
    divider = Pos(0, DIVIDER_Y, BASE_T) * Box(
        OUTER_X - 2 * WALL,
        DIVIDER_T,
        divider_h,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    wire_gate = Pos(0, DIVIDER_Y, BASE_T + 2.0) * Box(
        10.0, DIVIDER_T + 1.0, 3.2,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    body = body + (divider - wire_gate)

    # Actual RP2040 USB opening, enlarged by 0.4 mm per side for FDM assembly.
    usb_cut = Pos(0, -OUTER_Y / 2, RP_USB_BOTTOM - 0.4) * Box(
        RP_USB_W + 0.8,
        WALL + 2.0,
        RP_USB_H + 0.8,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    body = body - usb_cut

    # Physical fit feedback: the power board needs no external connector
    # opening.  Its +Y wall therefore remains continuous.  Wiring between the
    # two boards still uses the protected divider gate above.

    body = one(body)
    body.label = "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_BODY_V4"
    return body


def make_lid():
    lid = Box(
        OUTER_X, OUTER_Y, LID_T,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    for x, y in BOSS_CENTERS:
        through = Pos(x, y, -0.1) * Cylinder(
            LID_CLEAR_D / 2, LID_T + 0.2,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        counterbore = Pos(x, y, LID_T - 1.0) * Cylinder(
            COUNTERBORE_D / 2, 1.1,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        lid = lid - through - counterbore

    # Vent and inspection opening.  A removable dust film can be added without
    # blocking screws or board removal.
    vent = Pos(0, 2.0, -0.1) * Box(
        16.0, 20.0, LID_T + 0.2,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    lid = lid - vent
    lid = one(lid)
    lid.label = "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_LID_V4"
    return lid


def make_usb_port_coupon():
    coupon = Box(
        20.0, 8.0, 6.0,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    opening = Pos(0, 0, 1.1) * Box(
        RP_USB_W + 0.8, 9.0, RP_USB_H + 0.8,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    coupon = one(coupon - opening)
    coupon.label = "RP2040_USB_PORT_FDM_COUPON"
    return coupon


def make_rp_length_fit_coupon():
    """Three quick-fit cells for the RP2040 23.15 mm insertion direction.

    The centre cell is the V4 production value (0.60 mm per end).  The flanking
    cells allow a team member to choose 0.50 or 0.70 mm after one short print,
    without reprinting the complete cassette.
    """
    cells = []
    cell_gap = 3.0
    outer_x = RP_X + 2 * RP_CLEARANCE_X + 2 * WALL
    x_cursor = 0.0
    for clearance_y in (0.50, 0.60, 0.70):
        pocket_y = RP_Y + 2 * clearance_y
        outer_y = pocket_y + 2 * WALL
        cell = Box(
            outer_x, outer_y, 4.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        cavity = Pos(0, 0, 1.20) * Box(
            RP_X + 2 * RP_CLEARANCE_X,
            pocket_y,
            3.2,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        cell = one(cell - cavity).translate((x_cursor, 0, 0))
        cells.append(cell)
        x_cursor += outer_x + cell_gap

    coupon = cells[0] + cells[1] + cells[2]
    # Thin breakaway bars make the coupon a single printable solid.
    for index in (0, 1):
        left_right = index * (outer_x + cell_gap) + outer_x / 2
        right_left = (index + 1) * (outer_x + cell_gap) - outer_x / 2
        low, high = sorted((left_right, right_left))
        coupon = coupon + Pos((low + high) / 2, 0, 0) * Box(
            high - low + 0.4,
            3.0,
            0.8,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    coupon = one(coupon)
    coupon.label = "RP2040_LENGTH_CLEARANCE_COUPON_050_060_070"
    return coupon


def make_print_together(body, lid):
    """Place body and lid in one print file as two disconnected solids."""
    lid_shift_x = OUTER_X + PRINT_PART_GAP
    lid_on_plate = lid.translate((lid_shift_x, 0, 0))
    print_part = body + lid_on_plate
    print_part.label = "ONEGRIP_ELECTRONICS_CASSETTE_PRINT_LAYOUT_V5"
    return print_part


def make_rp_surrogate():
    pcb = Pos(0, RP_CENTER_Y, RP_PCB_BOTTOM) * Box(
        RP_X, RP_Y, RP_T,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    usb = Pos(0, RP_CENTER_Y - RP_Y / 2 - RP_USB_PROTRUSION / 2,
              RP_USB_BOTTOM) * Box(
        RP_USB_W, RP_USB_PROTRUSION, RP_USB_H,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    surrogate = one(pcb + usb)
    surrogate.label = "RP2040_ZERO_USER_MEASURED_SURROGATE"
    return surrogate


def make_power_surrogate():
    surrogate = Pos(0, POWER_CENTER_Y, POWER_PCB_BOTTOM) * Box(
        POWER_X, POWER_Y, POWER_PCB_T,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    surrogate = one(surrogate)
    surrogate.label = "POWER_BOARD_PCB_SURROGATE"
    return surrogate


def make_power_underside_envelope():
    # Full-footprint worst case.  It is exported separately because the user
    # has supplied depth but not the XY location of the underside components.
    envelope = Pos(0, POWER_CENTER_Y, POWER_PCB_BOTTOM - POWER_UNDERSIDE) * Box(
        POWER_X, POWER_Y, POWER_UNDERSIDE,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    envelope = one(envelope)
    envelope.label = "POWER_BOARD_UNDERSIDE_FULL_FOOTPRINT_ENVELOPE"
    return envelope


def inter_volume(a, b):
    result = a.intersect(b)
    if result is None:
        return 0.0
    solids = result.solids() if hasattr(result, "solids") else [result]
    return float(sum(s.volume for s in solids))


def export_all():
    OUT.mkdir(parents=True, exist_ok=True)
    body = make_body()
    lid = make_lid()
    rp = make_rp_surrogate()
    power = make_power_surrogate()
    power_under = make_power_underside_envelope()
    coupon = make_usb_port_coupon()
    rp_length_coupon = make_rp_length_fit_coupon()
    print_together = make_print_together(body, lid)

    # STEP masters and print STLs.
    parts = {
        "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_BODY_V4": body,
        "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_LID_V4": lid,
    }
    for name, part in parts.items():
        export_step(part, str(OUT / f"{name}.step"))
        export_stl(part, str(OUT / f"{name}.stl"), tolerance=0.05,
                   angular_tolerance=0.2)

    export_step(coupon, str(OUT / "RP2040_USB_PORT_FDM_COUPON.step"))
    export_stl(coupon, str(OUT / "RP2040_USB_PORT_FDM_COUPON.stl"),
               tolerance=0.05, angular_tolerance=0.2)
    export_step(
        rp_length_coupon,
        str(OUT / "RP2040_LENGTH_CLEARANCE_COUPON_050_060_070.step"),
    )
    export_stl(
        rp_length_coupon,
        str(OUT / "RP2040_LENGTH_CLEARANCE_COUPON_050_060_070.stl"),
        tolerance=0.05,
        angular_tolerance=0.2,
    )
    export_step(print_together, str(OUT / "ONEGRIP_ELECTRONICS_CASSETTE_PRINT_LAYOUT_V5.step"))
    export_stl(print_together, str(OUT / "ONEGRIP_ELECTRONICS_CASSETTE_PRINT_LAYOUT_V5.stl"),
               tolerance=0.05, angular_tolerance=0.2)
    export_step(rp, str(OUT / "RP2040_ZERO_USER_MEASURED_SURROGATE.step"))
    export_step(power, str(OUT / "POWER_BOARD_PCB_SURROGATE.step"))
    export_step(power_under, str(OUT / "POWER_BOARD_UNDERSIDE_FULL_FOOTPRINT_ENVELOPE.step"))
    export_stl(rp, str(OUT / "RP2040_ZERO_USER_MEASURED_SURROGATE.stl"),
               tolerance=0.05, angular_tolerance=0.2)
    export_stl(power, str(OUT / "POWER_BOARD_PCB_SURROGATE.stl"),
               tolerance=0.05, angular_tolerance=0.2)

    # The lid is shown in assembled position with a small non-interference gap.
    lid_assembled = lid.translate((0, 0, BODY_H + LID_GAP))
    assembly = body + lid_assembled + rp + power
    export_step(assembly, str(OUT / "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_ASSEMBLY_V4.step"))

    report = {
        "decision": "side-by-side fixed-base service cassette; old buried tray rejected",
        "outer_dimensions_mm": [OUTER_X, OUTER_Y, BODY_H + LID_GAP + LID_T],
        "board_layout": {
            "rp2040_center_y_mm": round(RP_CENTER_Y, 3),
            "power_board_center_y_mm": round(POWER_CENTER_Y, 3),
            "power_rotation_deg": 90,
            "rp2040_pocket_mm": [RP_POCKET_X, RP_POCKET_Y],
            "rp2040_clearance_each_side_mm": {
                "width_x": RP_CLEARANCE_X,
                "insertion_y": RP_CLEARANCE_Y,
            },
            "power_external_connector_opening": "removed per physical fit feedback",
        },
        "body": {
            "valid": bool(body.is_valid),
            "solid_count": len(body.solids()),
            "bbox_mm": [round(body.bounding_box().size.X, 3),
                        round(body.bounding_box().size.Y, 3),
                        round(body.bounding_box().size.Z, 3)],
        },
        "lid": {
            "valid": bool(lid.is_valid),
            "solid_count": len(lid.solids()),
            "bbox_mm": [round(lid.bounding_box().size.X, 3),
                        round(lid.bounding_box().size.Y, 3),
                        round(lid.bounding_box().size.Z, 3)],
            "matches_current_body_footprint": bool(
                abs(lid.bounding_box().size.X - body.bounding_box().size.X) < 1.0e-6
                and abs(lid.bounding_box().size.Y - body.bounding_box().size.Y) < 1.0e-6
            ),
            "shared_screw_centers_mm": [[x, round(y, 3)] for x, y in BOSS_CENTERS],
            "lid_clear_hole_diameter_mm": LID_CLEAR_D,
            "body_pilot_diameter_mm": PILOT_D,
        },
        "print_together": {
            "valid": bool(print_together.is_valid),
            "solid_count": len(print_together.solids()),
            "bbox_mm": [round(print_together.bounding_box().size.X, 3),
                        round(print_together.bounding_box().size.Y, 3),
                        round(print_together.bounding_box().size.Z, 3)],
            "part_count": 2,
            "physical_connections": 0,
            "instruction": "Import once; body and lid remain separate after printing.",
        },
        "rp2040_length_fit_coupon": {
            "clearance_each_end_mm": [0.50, 0.60, 0.70],
            "production_choice_mm": 0.60,
            "purpose": "verify hand insertion before reprinting the full cassette",
        },
        "hard_interference_mm3": {
            "rp2040_vs_body": round(inter_volume(rp, body), 6),
            "power_pcb_vs_body": round(inter_volume(power, body), 6),
            "lid_vs_body_assembled": round(inter_volume(lid_assembled, body), 6),
        },
        "unresolved_component_map": {
            "power_underside_full_footprint_envelope_vs_body_mm3":
                round(inter_volume(power_under, body), 6),
            "meaning": "Not a hard failure: support pads intentionally occupy corner zones. "
                       "Measure the real underside component XY footprint before freezing pads.",
        },
        "assembly_access": {
            "board_insertion": "top-down, boards independent",
            "screw_access": "four vertical M3 screws; none beneath a board",
            "rp_usb": "open -Y wall, 0.4 mm FDM clearance each side",
            "power_wiring": "closed +Y wall; protected 10 x 3.2 mm divider gate only",
        },
        "print_orientation": {
            "body": "flat base on build plate; no support required",
            "lid": "outer face on build plate; no support required",
        },
        "stop_gate": [
            "Measure power-board PCB thickness and tallest top component before freezing lid clearance.",
            "Confirm a 9.7 x 3.8 mm test coupon accepts the actual RP2040 USB connector/cable.",
        ],
    }
    (OUT / "service_cassette_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    export_all()
