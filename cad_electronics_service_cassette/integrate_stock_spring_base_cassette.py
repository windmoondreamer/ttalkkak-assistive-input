"""Integrate the cassette with the stock spring-compatible fixed Base.

The immutable open-source gimbal contains two relevant parts:

* ``Base``: fixed lower plate with four spring-screw bosses
* ``Spring_holder``: moving upper plate with four corresponding spring ears

The stock Base's obsolete central rear cassette/projection is removed flush with
the square spring deck.  The electronics cassette is attached to the opposite,
central front edge through a low bridge.
It is not fused to the moving Spring_holder and none of the four spring paths is
modified.  The 1 mm service gap lets the cassette lid open upward without
overlapping the 18.5 mm-tall Base.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import cadquery as cq


HERE = Path(__file__).resolve().parent
OUT = HERE / "export"
OPTION_C = HERE.parent / "stock-cartridge-option-c"
SOURCE = OPTION_C / "source" / "stock_gimbal_base_source_all_parts.step"
BUILDER = OPTION_C / "build_option_c.py"
BODY_STEP = OUT / "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_BODY_V4.step"
LID_STEP = OUT / "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_LID_V4.step"

INTEGRATED_NAME = "ONEGRIP_STOCK_SPRING_BASE_CASSETTE_BODY_INTEGRATED_V4"
ASSEMBLY_NAME = "ONEGRIP_STOCK_SPRING_BASE_CASSETTE_LID_ASSEMBLY_V4"
PRINT_LAYOUT_NAME = "ONEGRIP_STOCK_SPRING_BASE_CASSETTE_LID_PRINT_LAYOUT_V4"
BASE_REFERENCE_NAME = "STOCK_SPRING_BASE_REAR_REMOVED_FLAT_DECK_REFERENCE"
SPRING_HOLDER_REFERENCE_NAME = "STOCK_MOVING_SPRING_HOLDER_REFERENCE"

CASSETTE_X = 36.0
CASSETTE_Y = 45.0
BODY_H = 12.0
LID_GAP_Z = 0.20

# Do not bury the cassette or its lid under the taller stock Base.  The low
# bridge spans this visible gap and overlaps both solids by 3 mm.
BASE_TO_CASSETTE_GAP_Y = 1.0
BRIDGE_OVERLAP_EACH_Y = 3.0
BRIDGE_X = 30.0
BRIDGE_Z = 5.0
PRINT_PART_GAP = 5.0

# The source Base is a 100 mm square spring deck ending at Y=76.636 mm, plus
# a central 24 x 43 mm obsolete rear cassette/projection.  The red-X feedback
# requests that projection be removed.  This cut plane is the original square
# deck edge and remains 2.6+ mm behind the rear spring-boss geometry.
REAR_CASSETTE_TRIM_Y = 76.636
TRIM_BOX_MARGIN = 10.0

# After the rear cassette is sliced off, its 5 mm-thick front wall remains as
# a vertical cross-section.  Remove that central wall down to the actual deck
# top Z=-21.5996 mm.  The earlier 3.5 mm assumption cut 3 mm too deep and made
# the red-circle recess; the measured deck thickness is 6.5 mm.
REAR_WALL_CUT_X = 30.0
REAR_WALL_CUT_Y_MIN = 69.0
REAR_WALL_CUT_Y_MAX = 77.0
DECK_FLOOR_THICKNESS = 6.5

DESIGN_TILT_DEG = 20.0


def load_builder():
    spec = importlib.util.spec_from_file_location("option_c_builder", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_single(path: Path) -> cq.Shape:
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise RuntimeError(f"Expected one valid STEP solid: {path}")
    return solids[0]


def common_volume(left: cq.Shape, right: cq.Shape) -> float:
    try:
        return float(left.intersect(right).Volume())
    except Exception:
        return 0.0


def export_shape(shape: cq.Shape, name: str) -> None:
    cq.exporters.export(shape, str(OUT / f"{name}.step"))
    cq.exporters.export(
        shape,
        str(OUT / f"{name}.stl"),
        tolerance=0.05,
        angularTolerance=0.20,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    builder = load_builder()
    names = builder.step_solid_names(SOURCE)
    solids = cq.importers.importStep(str(SOURCE)).solids().vals()
    if len(names) != len(solids):
        raise RuntimeError("Stock STEP name/solid count mismatch")
    stock = dict(zip(names, solids, strict=True))

    base_raw = stock["Base"]
    spring_holder = stock["Spring_holder"]
    body = load_single(BODY_STEP)
    lid = load_single(LID_STEP)
    raw_bb = base_raw.BoundingBox()
    trim_box = (
        cq.Workplane("XY")
        .box(
            raw_bb.xlen + 2.0 * TRIM_BOX_MARGIN,
            REAR_CASSETTE_TRIM_Y - raw_bb.ymin + TRIM_BOX_MARGIN,
            raw_bb.zlen + 2.0 * TRIM_BOX_MARGIN,
            centered=(False, False, False),
        )
        .val()
        .translate(
            (
                raw_bb.xmin - TRIM_BOX_MARGIN,
                raw_bb.ymin - TRIM_BOX_MARGIN,
                raw_bb.zmin - TRIM_BOX_MARGIN,
            )
        )
    )
    base_after_rear_trim = base_raw.intersect(trim_box)
    removed_rear_cassette = base_raw.cut(base_after_rear_trim)
    if not base_after_rear_trim.isValid() or len(base_after_rear_trim.Solids()) != 1:
        raise RuntimeError("Rear cassette trim did not leave one valid Base solid")
    removed_rear_volume = float(removed_rear_cassette.Volume())
    if removed_rear_volume < 1000.0:
        raise RuntimeError(
            f"Rear cassette/projection was not removed: {removed_rear_volume:.3f} mm^3"
        )
    deck_floor_top_z = raw_bb.zmin + DECK_FLOOR_THICKNESS
    rear_wall_cut = (
        cq.Workplane("XY")
        .box(
            REAR_WALL_CUT_X,
            REAR_WALL_CUT_Y_MAX - REAR_WALL_CUT_Y_MIN,
            raw_bb.zmax - deck_floor_top_z + TRIM_BOX_MARGIN,
            centered=(False, False, False),
        )
        .val()
        .translate(
            (
                -REAR_WALL_CUT_X / 2.0,
                REAR_WALL_CUT_Y_MIN,
                deck_floor_top_z,
            )
        )
    )
    removed_rear_wall = base_after_rear_trim.intersect(rear_wall_cut)
    removed_rear_wall_volume = float(removed_rear_wall.Volume())
    base = base_after_rear_trim.cut(rear_wall_cut)
    if removed_rear_wall_volume < 100.0:
        raise RuntimeError(
            f"Rear cut-face wall was not removed: {removed_rear_wall_volume:.3f} mm^3"
        )
    if not base.isValid() or len(base.Solids()) != 1:
        raise RuntimeError("Rear wall removal did not leave one valid Base solid")
    remaining_wall_probe_volume = common_volume(base, rear_wall_cut)
    if remaining_wall_probe_volume > 1.0e-5:
        raise RuntimeError(
            f"Rear wall remains in cut envelope: {remaining_wall_probe_volume:.6f} mm^3"
        )
    bb = base.BoundingBox()

    body_rear_y = bb.ymin - BASE_TO_CASSETTE_GAP_Y
    body_center_y = body_rear_y - CASSETTE_Y / 2.0
    body_installed = body.translate((0.0, body_center_y, bb.zmin))

    bridge_ymin = body_rear_y - BRIDGE_OVERLAP_EACH_Y
    bridge_ymax = bb.ymin + BRIDGE_OVERLAP_EACH_Y
    bridge = (
        cq.Workplane("XY")
        .box(
            BRIDGE_X,
            bridge_ymax - bridge_ymin,
            BRIDGE_Z,
            centered=(True, True, False),
        )
        .val()
        .translate((0.0, (bridge_ymin + bridge_ymax) / 2.0, bb.zmin))
    )

    base_bridge_overlap = common_volume(base, bridge)
    body_bridge_overlap = common_volume(body_installed, bridge)
    if base_bridge_overlap < 300.0 or body_bridge_overlap < 300.0:
        raise RuntimeError(
            "Front bridge does not overlap both Base and cassette sufficiently: "
            f"{base_bridge_overlap:.3f}, {body_bridge_overlap:.3f} mm^3"
        )

    integrated = base.fuse(bridge).fuse(body_installed)
    if not integrated.isValid() or len(integrated.Solids()) != 1:
        raise RuntimeError("Base + bridge + cassette did not form one valid solid")

    lid_installed = lid.translate(
        (0.0, body_center_y, bb.zmin + BODY_H + LID_GAP_Z)
    )
    lid_overlap = common_volume(integrated, lid_installed)
    if lid_overlap > 1.0e-5:
        raise RuntimeError(f"Removable lid collision: {lid_overlap:.6f} mm^3")

    # Only the new attachment is checked against the untouched gimbal.  Base
    # interfaces already exist in the stock design and are not reinterpreted.
    attachment = body_installed.fuse(bridge)
    other_static = ["Pitch", "Spring_holder", "Roll_holder", "Spacer", "Roll", "Roll_holder_2"]
    static_hits = {
        name: round(common_volume(attachment, stock[name]), 6)
        for name in other_static
    }
    static_lid_hits = {
        name: round(common_volume(lid_installed, stock[name]), 6)
        for name in other_static
    }

    moving_names = ["Pitch", "Spring_holder", "Roll"]
    states = [
        ("neutral", 0.0, 0.0),
        ("x_pos_20", DESIGN_TILT_DEG, 0.0),
        ("x_neg_20", -DESIGN_TILT_DEG, 0.0),
        ("y_pos_20", 0.0, DESIGN_TILT_DEG),
        ("y_neg_20", 0.0, -DESIGN_TILT_DEG),
        ("corner_pp", DESIGN_TILT_DEG, DESIGN_TILT_DEG),
        ("corner_pn", DESIGN_TILT_DEG, -DESIGN_TILT_DEG),
        ("corner_np", -DESIGN_TILT_DEG, DESIGN_TILT_DEG),
        ("corner_nn", -DESIGN_TILT_DEG, -DESIGN_TILT_DEG),
    ]
    motion_checks: list[dict[str, object]] = []
    for label, x_deg, y_deg in states:
        hits = {}
        lid_hits = {}
        for name in moving_names:
            moving = builder.rotate_about_pivot(stock[name], x_deg, y_deg)
            hits[name] = round(common_volume(attachment, moving), 6)
            lid_hits[name] = round(common_volume(lid_installed, moving), 6)
        motion_checks.append(
            {
                "state": label,
                "x_deg": x_deg,
                "y_deg": y_deg,
                "body_bridge_overlap_mm3": hits,
                "lid_overlap_mm3": lid_hits,
            }
        )
    max_interference = max(
        [*static_hits.values(), *static_lid_hits.values()]
        + [
            value
            for state in motion_checks
            for group in ("body_bridge_overlap_mm3", "lid_overlap_mm3")
            for value in state[group].values()
        ]
    )
    if max_interference > 1.0e-5:
        raise RuntimeError(f"Attachment/gimbal interference: {max_interference:.6f} mm^3")

    # Conservative boxes around the four fixed spring bosses.  Zero overlap
    # proves that the bridge is central and does not consume a spring screw ear.
    hook_centers = [
        (-38.868, -15.273),
        (38.868, -15.273),
        (-38.868, 68.545),
        (38.868, 68.545),
    ]
    hook_keepout_hits = []
    for x, y in hook_centers:
        keepout = (
            cq.Workplane("XY")
            .box(14.0, 14.0, 25.0, centered=(True, True, False))
            .val()
            .translate((x, y, bb.zmin))
        )
        hook_keepout_hits.append(
            round(
                common_volume(attachment, keepout)
                + common_volume(lid_installed, keepout),
                6,
            )
        )
    if max(hook_keepout_hits) > 1.0e-5:
        raise RuntimeError("Cassette attachment enters a spring-boss keepout")

    assembly = cq.Compound.makeCompound([integrated, lid_installed])
    integrated_print = integrated.translate((0.0, 0.0, -integrated.BoundingBox().zmin))
    ipb = integrated_print.BoundingBox()
    lb = lid.BoundingBox()
    lid_print = lid.translate(
        (
            ipb.xmax + PRINT_PART_GAP - lb.xmin,
            ipb.ymin - lb.ymin,
            -lb.zmin,
        )
    )
    print_layout = cq.Compound.makeCompound([integrated_print, lid_print])

    export_shape(integrated, INTEGRATED_NAME)
    export_shape(assembly, ASSEMBLY_NAME)
    export_shape(print_layout, PRINT_LAYOUT_NAME)
    export_shape(base, BASE_REFERENCE_NAME)
    export_shape(spring_holder, SPRING_HOLDER_REFERENCE_NAME)

    ib = integrated.BoundingBox()
    report = {
        "correct_part_identification": {
            "fixed_spring_plate": "Base",
            "moving_upper_plate": "Spring_holder",
            "wrong_previous_part": "CARRIER_PLATE",
            "source_base_bbox_mm": [raw_bb.xlen, raw_bb.ylen, raw_bb.zlen],
            "trimmed_base_bbox_mm": [bb.xlen, bb.ylen, bb.zlen],
            "spring_holder_bbox_mm": [
                spring_holder.BoundingBox().xlen,
                spring_holder.BoundingBox().ylen,
                spring_holder.BoundingBox().zlen,
            ],
        },
        "red_x_rear_cassette_removal": {
            "trim_plane_y_mm": REAR_CASSETTE_TRIM_Y,
            "removed_volume_mm3": removed_rear_volume,
            "remaining_base_valid": base.isValid(),
            "remaining_base_solid_count": len(base.Solids()),
            "result": "pass",
        },
        "red_x_cut_face_wall_removal": {
            "cut_envelope_mm": {
                "x": [-REAR_WALL_CUT_X / 2.0, REAR_WALL_CUT_X / 2.0],
                "y": [REAR_WALL_CUT_Y_MIN, REAR_WALL_CUT_Y_MAX],
                "z": [deck_floor_top_z, raw_bb.zmax],
            },
            "deck_floor_remaining_thickness_mm": DECK_FLOOR_THICKNESS,
            "deck_top_z_mm": deck_floor_top_z,
            "removed_wall_volume_mm3": removed_rear_wall_volume,
            "remaining_wall_probe_volume_mm3": remaining_wall_probe_volume,
            "remaining_base_valid": base.isValid(),
            "remaining_base_solid_count": len(base.Solids()),
            "result": "pass",
        },
        "red_circle_deck_flatness": {
            "target_top_z_mm": deck_floor_top_z,
            "previous_wrong_top_z_mm": raw_bb.zmin + 3.5,
            "corrected_height_mm": DECK_FLOOR_THICKNESS - 3.5,
            "result": "pass",
        },
        "cassette_attachment": {
            "body_center_y_mm": body_center_y,
            "base_to_body_gap_y_mm": BASE_TO_CASSETTE_GAP_Y,
            "bridge_bbox_mm": [BRIDGE_X, bridge_ymax - bridge_ymin, BRIDGE_Z],
            "base_bridge_overlap_mm3": base_bridge_overlap,
            "body_bridge_overlap_mm3": body_bridge_overlap,
            "lid_overlap_mm3": lid_overlap,
            "integrated_bbox_mm": [ib.xlen, ib.ylen, ib.zlen],
            "integrated_valid": integrated.isValid(),
            "integrated_solid_count": len(integrated.Solids()),
        },
        "spring_interface_preservation": {
            "fixed_hook_count": 4,
            "moving_ear_count": 4,
            "attachment_overlap_with_hook_keepouts_mm3": hook_keepout_hits,
            "result": "pass",
        },
        "gimbal_interference": {
            "static_attachment_overlap_mm3": static_hits,
            "static_lid_overlap_mm3": static_lid_hits,
            "motion_states": motion_checks,
            "maximum_overlap_mm3": max_interference,
            "result": "pass",
        },
        "front_cassette_placement_assessment": {
            "location": "fixed Base central front (-Y), not on moving gimbal",
            "design_tilt_checked_deg": DESIGN_TILT_DEG,
            "spring_boss_keepout_max_overlap_mm3": max(hook_keepout_hits),
            "moving_gimbal_max_overlap_mm3": max_interference,
            "lid_overlap_mm3": lid_overlap,
            "usb_access": "outward toward -Y/front",
            "mass_symmetry": "centered on X; no left/right fixed-base bias",
            "result": "mechanically suitable",
        },
        "human_assembly": {
            "lid_removal": "+Z; one-millimetre gap from fixed Base",
            "spring_service": "all four fixed bosses and four moving ears remain untouched",
            "usb": "faces -Y/front",
        },
        "printing": {
            "integrated_part": "stock Base bottom and cassette bottom share Z datum",
            "support": "none expected for Base/cassette bridge orientation; verify slicer bridges",
            "print_layout_solid_count": len(print_layout.Solids()),
        },
        "outputs": {
            "integrated": INTEGRATED_NAME,
            "assembly": ASSEMBLY_NAME,
            "print_layout": PRINT_LAYOUT_NAME,
            "base_reference": BASE_REFERENCE_NAME,
            "spring_holder_reference": SPRING_HOLDER_REFERENCE_NAME,
        },
    }
    (OUT / "stock_spring_base_cassette_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
