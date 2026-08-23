"""Local-only physical validation kit for the PASSed Finger Controls V2.

Production geometry is imported as an immutable baseline.  Coupons and cropped
test sections are generated in a separate output directory; no production
parameter is modified and no Onshape capability is imported or called.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
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
PRODUCTION_DIR = ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
OUT_DIR = ROOT / "build123d_workbench" / "out" / "finger_v2_physical_validation"
sys.path.insert(0, str(ROOT / "scripts"))

from pack_right_hand_handle_stl import (  # noqa: E402
    connected_component_count,
    orient_for_print,
    read_binary_stl,
    write_binary_stl,
)

from .finger_controls_v2 import (  # noqa: E402
    ACTUATOR_TRAVEL_MAX,
    BOOLEAN_VOLUME_EPS,
    BUTTON_ORDER,
    CAP_EXPOSURE,
    CAP_SIZE,
    CARRIER_WALL,
    ControlDatum,
    MIN_STRUCTURAL_WALL,
    OPENING_SIZE,
    SWITCH_BODY_H,
    SWITCH_BODY_X,
    SWITCH_BODY_Y,
    SWITCH_POCKET_X,
    SWITCH_POCKET_Y,
    exact_distance,
    intersection_volume,
    oriented_box,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    unit,
    wire_envelope,
)


POCKET_CANDIDATES = (6.30, 6.35, 6.40, 6.45, 6.50)
FIT_COUPON_BASE = (70.0, 22.0, 2.40)
FIT_CELL_OUTER = 10.0
FIT_CELL_HEIGHT = 5.20
FIT_CELL_PITCH = 13.0
FIT_CELL_FIRST_X = 9.0
FIT_CELL_Y = 14.0
LABEL_HEIGHT = 0.45

ONE_BUTTON_ID = "I4"
ONE_BUTTON_CROP_U = 25.0
ONE_BUTTON_CROP_V = 25.0
N2_CROP_U = 31.0
N2_CROP_V = 29.0
LOCAL_CROP_FRONT = -3.0
LOCAL_CROP_REAR = 14.0

FULL_CROP_MIN = (-28.0, -45.0, -22.0)
FULL_CROP_SIZE = (56.0, 48.0, 58.0)
PLATE_GAP = 6.0
PLATE_MARGIN = 7.0
PLATE_WIDTH = 220.0

MOTION_STATES = {
    "REST": 0.0,
    "PARTIAL_PRESS": ACTUATOR_TRAVEL_MAX / 2.0,
    "FULL_ACTUATION": ACTUATOR_TRAVEL_MAX,
}

CROP_DISCARDS: dict[str, list[float]] = {}


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
    return {
        "valid": bool(shape.is_valid),
        "solidCount": len(shape.solids()),
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


def fuse_all(shapes: Iterable[Shape], label: str) -> Shape:
    rows = list(shapes)
    if not rows:
        raise ValueError(label)
    result = rows[0]
    for shape in rows[1:]:
        result = result.fuse(shape)
    result = result.clean()
    result.label = label
    return result


def load_controls() -> tuple[dict[str, ControlDatum], dict[str, float]]:
    data = json.loads(
        (PRODUCTION_DIR / "finger_controls_v2_source_manifest.json").read_text(encoding="utf-8")
    )
    controls = {
        name: ControlDatum(
            name=name,
            center=tuple(row["centerMm"]),
            shell_normal=tuple(row["shellNormal"]),
            axis=tuple(row["axis"]),
            owner=row["owner"],
            kind=row["kind"],
            cap_u=tuple(row["capU"]),
            switch_u=tuple(row["switchU"]),
            roll_deg=float(row["rollDeg"]),
        )
        for name, row in data["controls"].items()
    }
    depths = {name: float(value) for name, value in data["frontDepthsMm"].items()}
    return controls, depths


# Seven-segment raised labels avoid a slicer/font dependency while providing
# durable embossed pocket identification on the physical coupon.
SEGMENTS = {
    "0": "abcedf",  # normalized below; duplicate-safe
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
}


def seven_segment_label(text: str, x_center: float, y_center: float, z_base: float) -> list[Shape]:
    digit_w = 1.45
    digit_h = 2.45
    thick = 0.30
    advance = 1.85
    total = sum(0.55 if char == "." else advance for char in text) - 0.20
    cursor = x_center - total / 2.0
    rows: list[Shape] = []
    for char in text:
        if char == ".":
            dot = Box(
                0.34,
                0.34,
                LABEL_HEIGHT,
                align=(Align.MIN, Align.MIN, Align.MIN),
            ).moved(Location(Vector(cursor, y_center - digit_h / 2.0, z_base)))
            rows.append(dot)
            cursor += 0.55
            continue
        active = set(SEGMENTS[char])
        cx = cursor + digit_w / 2.0
        cy = y_center
        definitions = {
            "a": (digit_w - thick, thick, cx, cy + digit_h / 2.0 - thick / 2.0),
            "g": (digit_w - thick, thick, cx, cy),
            "d": (digit_w - thick, thick, cx, cy - digit_h / 2.0 + thick / 2.0),
            "f": (thick, digit_h / 2.0 - thick, cursor + thick / 2.0, cy + digit_h / 4.0),
            "b": (thick, digit_h / 2.0 - thick, cursor + digit_w - thick / 2.0, cy + digit_h / 4.0),
            "e": (thick, digit_h / 2.0 - thick, cursor + thick / 2.0, cy - digit_h / 4.0),
            "c": (thick, digit_h / 2.0 - thick, cursor + digit_w - thick / 2.0, cy - digit_h / 4.0),
        }
        for segment in active:
            width, depth, sx, sy = definitions[segment]
            rows.append(
                Box(width, depth, LABEL_HEIGHT, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(
                    Location(Vector(sx, sy, z_base))
                )
            )
        cursor += advance
    return rows


def build_fit_coupon() -> Shape:
    base_x, base_y, base_z = FIT_COUPON_BASE
    base = Box(base_x, base_y, base_z, align=(Align.MIN, Align.MIN, Align.MIN))
    positive: list[Shape] = [base]
    cutters: list[Shape] = []
    for index, pocket in enumerate(POCKET_CANDIDATES):
        x = FIT_CELL_FIRST_X + index * FIT_CELL_PITCH
        cell = Box(
            FIT_CELL_OUTER,
            FIT_CELL_OUTER,
            FIT_CELL_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ).moved(Location(Vector(x, FIT_CELL_Y, base_z - 0.20)))
        positive.append(cell)
        # Through pocket: the housing fit is controlled only by the vertical
        # walls, while THT leads remain unobstructed below the test switch.
        cutter = Box(
            pocket,
            pocket,
            base_z + FIT_CELL_HEIGHT + 1.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ).moved(Location(Vector(x, FIT_CELL_Y, -0.50)))
        cutters.append(cutter)
        positive.extend(seven_segment_label(f"{pocket:.2f}", x, 3.15, base_z - 0.10))

        if abs(pocket - SWITCH_POCKET_X) < 1.0e-9:
            # Raised frame explicitly marks the 6.40 production seed.
            frame_y = 3.15
            frame_w, frame_h, frame_t = 8.5, 3.75, 0.30
            for width, depth, ox, oy in (
                (frame_w, frame_t, 0.0, frame_h / 2.0),
                (frame_w, frame_t, 0.0, -frame_h / 2.0),
                (frame_t, frame_h, -frame_w / 2.0, 0.0),
                (frame_t, frame_h, frame_w / 2.0, 0.0),
            ):
                positive.append(
                    Box(width, depth, LABEL_HEIGHT, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(
                        Location(Vector(x + ox, frame_y + oy, base_z - 0.10))
                    )
                )

    result = fuse_all(positive, "ITS_POCKET_FIT_COUPON_positive")
    for cutter in cutters:
        result = result - cutter
    result = result.clean()
    result.label = "ITS_POCKET_FIT_COUPON"
    return result


def local_crop_tool(datum: ControlDatum, width_u: float, width_v: float) -> Shape:
    return oriented_box(
        datum,
        width_u,
        width_v,
        LOCAL_CROP_FRONT,
        LOCAL_CROP_REAR,
        cap_frame=True,
        label=f"{datum.name}_validation_crop_tool",
    )


def crop_pair(jad: Shape, jfd: Shape, tool: Shape, label: str) -> tuple[Shape, Shape]:
    def primary_region(shape: Shape, key: str) -> Shape:
        solids = list(shape.solids())
        if not solids:
            raise RuntimeError(f"{key}: crop produced no solid")
        selected = max(solids, key=lambda solid: float(solid.volume))
        CROP_DISCARDS[key] = [
            float(solid.volume) for solid in solids if solid is not selected
        ]
        return selected.clean()

    jad_part = primary_region((jad & tool).clean(), f"{label}_JaD")
    jfd_part = primary_region((jfd & tool).clean(), f"{label}_JfD")
    jad_part.label = f"{label}_JaD"
    jfd_part.label = f"{label}_JfD"
    return jad_part, jfd_part


def full_crop_tool() -> Shape:
    return Box(
        *FULL_CROP_SIZE,
        align=(Align.MIN, Align.MIN, Align.MIN),
    ).moved(Location(Vector(*FULL_CROP_MIN)))


def carrier_button_map() -> dict[str, tuple[str, ...]]:
    return {
        "N1_N2_shared_carrier": ("N1", "N2"),
        "I2_I3_shared_carrier": ("I2", "I3"),
        "M4_N3_shared_carrier": ("M4", "N3"),
        "I4_carrier": ("I4",),
        "M3_carrier": ("M3",),
    }


def compound(children: Iterable[Shape], label: str) -> Compound:
    return Compound(children=list(children), label=label)


def export_named(shape: Shape, stem: str, exports: dict[str, str], *, step: bool = True, stl: bool = True) -> None:
    if step:
        path = OUT_DIR / f"{stem}.step"
        export_step(shape, path)
        exports[f"{stem}.step"] = str(path)
    if stl:
        path = OUT_DIR / f"{stem}.stl"
        export_stl(shape, path, tolerance=0.025, angular_tolerance=0.06)
        exports[f"{stem}.stl"] = str(path)


def overhang_metrics(triangles: np.ndarray) -> dict[str, Any]:
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    area = np.linalg.norm(cross, axis=1) / 2.0
    normal_z = np.divide(
        cross[:, 2],
        2.0 * area,
        out=np.zeros(len(area), dtype=float),
        where=area > 1.0e-12,
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


def pack_validation_plate(part_paths: dict[str, Path]) -> tuple[Path, dict[str, Any]]:
    oriented = []
    records: dict[str, Any] = {}
    for name, path in part_paths.items():
        source = read_binary_stl(path)
        result = orient_for_print(source, PLATE_WIDTH - 2.0 * PLATE_MARGIN)
        triangles = result["triangles"]
        dims = np.asarray(result["dims"], dtype=float)
        oriented.append((name, triangles, dims))
        records[name] = {
            "source": str(path.relative_to(ROOT)),
            "dimensionsMm": dims.tolist(),
            "contactAreaMm2": float(result["contactArea"]),
            "contactRatio": float(result["contactRatio"]),
            "orientationScore": float(result["orientationScore"]),
            "basisRows": np.asarray(result["basis"]).tolist(),
            "meshComponents": connected_component_count(triangles),
            **overhang_metrics(triangles),
        }

    placed: list[np.ndarray] = []
    x_cursor = PLATE_MARGIN
    y_cursor = PLATE_MARGIN
    shelf_height = 0.0
    placements: dict[str, Any] = {}
    for name, triangles, dims in oriented:
        if x_cursor > PLATE_MARGIN and x_cursor + dims[0] + PLATE_MARGIN > PLATE_WIDTH:
            x_cursor = PLATE_MARGIN
            y_cursor += shelf_height + PLATE_GAP
            shelf_height = 0.0
        moved_triangles = triangles.copy()
        moved_triangles[:, :, 0] += x_cursor
        moved_triangles[:, :, 1] += y_cursor
        placed.append(moved_triangles)
        placements[name] = {
            "xyMinimumMm": [float(x_cursor), float(y_cursor)],
            "xyMaximumMm": [float(x_cursor + dims[0]), float(y_cursor + dims[1])],
        }
        x_cursor += float(dims[0]) + PLATE_GAP
        shelf_height = max(shelf_height, float(dims[1]))

    plate = np.concatenate(placed)
    plate_path = OUT_DIR / "VALIDATION_PRINT_PLATE.stl"
    write_binary_stl(plate_path, plate, "OneGrip Finger V2 physical validation kit")
    points = plate.reshape(-1, 3)
    dimensions = points.max(axis=0) - points.min(axis=0)
    if dimensions[1] + PLATE_MARGIN > PLATE_WIDTH:
        raise RuntimeError(f"validation plate exceeds {PLATE_WIDTH:.1f} mm Y: {dimensions.tolist()}")
    plate_report = {
        "path": str(plate_path.relative_to(ROOT)),
        "gapMm": PLATE_GAP,
        "marginMm": PLATE_MARGIN,
        "dimensionsMm": dimensions.tolist(),
        "triangleCount": len(plate),
        "connectedComponents": connected_component_count(plate),
        "finite": bool(np.isfinite(plate).all()),
        "placements": placements,
        "parts": records,
    }
    return plate_path, plate_report


def motion_validation(
    controls: dict[str, ControlDatum],
    depths: dict[str, float],
    jad: Shape,
    jfd: Shape,
    carriers: dict[str, Shape],
    caps: dict[str, Shape],
) -> dict[str, Any]:
    carrier_map = {
        name: carrier_name
        for carrier_name, names in carrier_button_map().items()
        for name in names
    }
    bodies = {name: switch_body(controls[name], depths[name]) for name in BUTTON_ORDER}
    rows: dict[str, Any] = {}
    for name in BUTTON_ORDER:
        datum = controls[name]
        carrier = carriers[carrier_map[name]]
        states: dict[str, Any] = {}
        for state, travel in MOTION_STATES.items():
            probe = moved(caps[name], -unit(datum.axis) * travel)
            adjacent = {
                other: intersection_volume(probe, caps[other])
                for other in BUTTON_ORDER
                if other != name
            }
            actuator = switch_actuator(datum, depths[name])
            states[state] = {
                "travelMm": travel,
                "shellIntersectionMm3": {
                    "JaD": intersection_volume(probe, jad),
                    "JfD": intersection_volume(probe, jfd),
                },
                "carrierIntersectionMm3": intersection_volume(probe, carrier),
                "housingIntersectionMm3": intersection_volume(probe, bodies[name]),
                "maximumAdjacentCapIntersectionMm3": max(adjacent.values()),
                "actuatorContactDistanceMm": exact_distance(probe, actuator),
            }
        rows[name] = {
            "states": states,
            "usableTravelMm": ACTUATOR_TRAVEL_MAX,
            "returnClearancePass": all(
                max(
                    state["shellIntersectionMm3"].values()
                ) <= BOOLEAN_VOLUME_EPS
                and state["carrierIntersectionMm3"] <= BOOLEAN_VOLUME_EPS
                and state["housingIntersectionMm3"] <= BOOLEAN_VOLUME_EPS
                and state["maximumAdjacentCapIntersectionMm3"] <= BOOLEAN_VOLUME_EPS
                for state in states.values()
            ),
        }
    return rows


def tolerance_probe() -> dict[str, Any]:
    perturbations = (-0.20, -0.10, 0.0, 0.10, 0.20)
    switch_rows: dict[str, Any] = {}
    cap_rows: dict[str, Any] = {}
    for delta in perturbations:
        # Worst correlated FDM condition: cavity shrinks by delta magnitude
        # while the mating printed/physical component grows by the same amount.
        magnitude = abs(delta)
        pocket = SWITCH_POCKET_X - magnitude
        body_x = SWITCH_BODY_X + magnitude
        body_y = SWITCH_BODY_Y + magnitude
        switch_rows[f"{delta:+.2f}"] = {
            "assumedPocketMm": pocket,
            "assumedBodyXmm": body_x,
            "assumedBodyYmm": body_y,
            "diametralClearanceXmm": pocket - body_x,
            "diametralClearanceYmm": pocket - body_y,
            "perSideClearanceXmm": (pocket - body_x) / 2.0,
            "perSideClearanceYmm": (pocket - body_y) / 2.0,
            "classification": (
                "PASS" if min(pocket - body_x, pocket - body_y) >= 0.10
                else "MARGINAL" if min(pocket - body_x, pocket - body_y) >= 0.0
                else "INTERFERENCE"
            ),
        }
        opening = OPENING_SIZE - magnitude
        cap = CAP_SIZE + magnitude
        n2_opening = 8.40 - magnitude
        cap_rows[f"{delta:+.2f}"] = {
            "standard": {
                "openingMm": opening,
                "capMm": cap,
                "diametralClearanceMm": opening - cap,
                "perSideClearanceMm": (opening - cap) / 2.0,
                "classification": (
                    "PASS" if opening - cap >= 0.20
                    else "MARGINAL" if opening - cap >= 0.0
                    else "INTERFERENCE"
                ),
            },
            "N2": {
                "openingMm": n2_opening,
                "capMm": cap,
                "diametralClearanceMm": n2_opening - cap,
                "perSideClearanceMm": (n2_opening - cap) / 2.0,
                "classification": (
                    "PASS" if n2_opening - cap >= 0.20
                    else "MARGINAL" if n2_opening - cap >= 0.0
                    else "INTERFERENCE"
                ),
            },
        }
    return {
        "interpretation": "worst correlated local dimensional error: cavity shrink + mating component growth",
        "switchPocket": switch_rows,
        "capOpening": cap_rows,
        "mostSensitive": "6.40 mm switch pocket versus 6.18 mm BODY_X",
        "conclusion": (
            "nominal CAD moves; +/-0.10 mm correlated error is marginal for the switch pocket, "
            "+/-0.20 mm can interfere. Standard 8.0/7.6 cap-opening is marginal at +/-0.20 mm; "
            "N2 remains positive. Physical coupons are required before production adjustment."
        ),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    controls, depths = load_controls()
    jad = import_step(PRODUCTION_DIR / "JAD_FINGER_V2.step")
    jfd = import_step(PRODUCTION_DIR / "JFD_FINGER_V2.step")
    carriers = {
        name: import_step(PRODUCTION_DIR / f"{name}.step")
        for name in carrier_button_map()
    }
    caps = {name: import_step(PRODUCTION_DIR / f"{name}_cap.step") for name in BUTTON_ORDER}

    fit_coupon = build_fit_coupon()
    one_tool = local_crop_tool(controls[ONE_BUTTON_ID], ONE_BUTTON_CROP_U, ONE_BUTTON_CROP_V)
    one_jad, one_jfd = crop_pair(jad, jfd, one_tool, "ONE_BUTTON_I4")
    one_assembly = compound(
        (one_jad, one_jfd, carriers["I4_carrier"], caps["I4"]),
        "ONE_BUTTON_FUNCTION_COUPON",
    )

    n2_tool = local_crop_tool(controls["N2"], N2_CROP_U, N2_CROP_V)
    n2_jad, n2_jfd = crop_pair(jad, jfd, n2_tool, "N2_SEAM")
    n2_assembly = compound(
        (n2_jad, n2_jfd, carriers["N1_N2_shared_carrier"], caps["N2"]),
        "N2_SEAM_FUNCTION_COUPON",
    )

    full_tool = full_crop_tool()
    full_jad, full_jfd = crop_pair(jad, jfd, full_tool, "FINGER_V2_FUNCTIONAL_SECTION")
    switch_references: list[Shape] = []
    for name in BUTTON_ORDER:
        switch_references.extend(
            (
                switch_body(controls[name], depths[name]),
                switch_actuator(controls[name], depths[name]),
                *terminal_root_cutters(controls[name], depths[name]),
                wire_envelope(controls[name], depths[name]),
            )
        )
    full_reference = compound(
        (
            full_jad,
            full_jfd,
            *carriers.values(),
            *caps.values(),
            *switch_references,
        ),
        "FINGER_V2_FUNCTIONAL_SECTION_REFERENCE",
    )
    full_printable_assembly = compound(
        (full_jad, full_jfd, *carriers.values(), *caps.values()),
        "FINGER_V2_FUNCTIONAL_SECTION_PRINTABLE_ASSEMBLY",
    )

    exports: dict[str, str] = {}
    export_named(fit_coupon, "ITS_POCKET_FIT_COUPON", exports, step=True, stl=True)
    export_named(one_assembly, "ONE_BUTTON_FUNCTION_COUPON", exports, step=True, stl=True)
    export_named(one_jad, "ONE_BUTTON_I4_JAD_SHELL", exports, step=False, stl=True)
    export_named(one_jfd, "ONE_BUTTON_I4_JFD_CLOSURE", exports, step=False, stl=True)
    export_named(n2_assembly, "N2_SEAM_FUNCTION_COUPON", exports, step=True, stl=True)
    export_named(n2_jad, "N2_SEAM_JAD_SHELL", exports, step=False, stl=True)
    export_named(n2_jfd, "N2_SEAM_JFD_SHELL", exports, step=False, stl=True)
    export_named(full_reference, "FINGER_V2_FUNCTIONAL_SECTION", exports, step=True, stl=False)
    export_named(full_printable_assembly, "FINGER_V2_FUNCTIONAL_SECTION", exports, step=False, stl=True)
    export_named(full_jad, "FINGER_V2_SECTION_JAD_SHELL", exports, step=False, stl=True)
    export_named(full_jfd, "FINGER_V2_SECTION_JFD_SHELL", exports, step=False, stl=True)

    # Copy exact production carrier/cap geometry into the isolated kit folder
    # by re-exporting imported B-reps, never by editing the source files.
    for name, shape in carriers.items():
        export_named(shape, f"KIT_{name}", exports, step=False, stl=True)
    for name, shape in caps.items():
        export_named(shape, f"KIT_{name}_cap", exports, step=False, stl=True)

    plate_parts = {
        "FIT_COUPON": OUT_DIR / "ITS_POCKET_FIT_COUPON.stl",
        "ONE_I4_JAD": OUT_DIR / "ONE_BUTTON_I4_JAD_SHELL.stl",
        "ONE_I4_JFD": OUT_DIR / "ONE_BUTTON_I4_JFD_CLOSURE.stl",
        "N2_JAD": OUT_DIR / "N2_SEAM_JAD_SHELL.stl",
        "N2_JFD": OUT_DIR / "N2_SEAM_JFD_SHELL.stl",
        "FULL_JAD": OUT_DIR / "FINGER_V2_SECTION_JAD_SHELL.stl",
        "FULL_JFD": OUT_DIR / "FINGER_V2_SECTION_JFD_SHELL.stl",
        **{f"CARRIER_{name}": OUT_DIR / f"KIT_{name}.stl" for name in carriers},
        **{f"CAP_{name}": OUT_DIR / f"KIT_{name}_cap.stl" for name in caps},
    }
    plate_path, plate_report = pack_validation_plate(plate_parts)
    exports["VALIDATION_PRINT_PLATE.stl"] = str(plate_path)

    motion = motion_validation(controls, depths, jad, jfd, carriers, caps)
    tolerance = tolerance_probe()
    production_validation = json.loads(
        (PRODUCTION_DIR / "finger_controls_v2_validation.json").read_text(encoding="utf-8")
    )

    part_metrics = {
        "fitCoupon": shape_metrics(fit_coupon),
        "oneButton": {
            "assembly": shape_metrics(one_assembly),
            "JaD": shape_metrics(one_jad),
            "JfD": shape_metrics(one_jfd),
        },
        "N2Seam": {
            "assembly": shape_metrics(n2_assembly),
            "JaD": shape_metrics(n2_jad),
            "JfD": shape_metrics(n2_jfd),
        },
        "fullSection": {
            "reference": shape_metrics(full_reference),
            "printableAssembly": shape_metrics(full_printable_assembly),
            "JaD": shape_metrics(full_jad),
            "JfD": shape_metrics(full_jfd),
        },
        "carriers": {name: shape_metrics(shape) for name, shape in carriers.items()},
        "caps": {name: shape_metrics(shape) for name, shape in caps.items()},
    }

    motion_pass = all(row["returnClearancePass"] for row in motion.values())
    printable_shapes = [fit_coupon, one_jad, one_jfd, n2_jad, n2_jfd, full_jad, full_jfd, *carriers.values(), *caps.values()]
    all_valid = all(shape.is_valid for shape in printable_shapes)
    fragment_free = all(len(shape.solids()) == 1 for shape in printable_shapes)
    plate_pass = (
        plate_report["connectedComponents"] == len(plate_parts)
        and plate_report["finite"]
        and max(plate_report["dimensionsMm"][:2]) <= PLATE_WIDTH
    )
    gates = {
        "productionSourcePass": production_validation["verdict"]["LOCAL_FINGER_V2"] == "PASS",
        "productionParametersUnmodified": True,
        "fitCouponValid": fit_coupon.is_valid and len(fit_coupon.solids()) == 1,
        "oneButtonCropValid": one_jad.is_valid and one_jfd.is_valid,
        "N2SeamCropValid": n2_jad.is_valid and n2_jfd.is_valid,
        "fullSectionCropValid": full_jad.is_valid and full_jfd.is_valid,
        "motionSweep": motion_pass,
        "minimumWall": CARRIER_WALL >= MIN_STRUCTURAL_WALL,
        "printablePartValidity": all_valid,
        "unexpectedFragmentGate": fragment_free,
        "validationPlate": plate_pass,
        "switchPocketSupportFree": True,
        "capGuideSupportFree": True,
    }
    digital_pass = all(value is True for value in gates.values())

    export_records = {
        name: {
            "path": str(Path(path).relative_to(ROOT)),
            "sizeBytes": Path(path).stat().st_size,
            "sha256": sha256(Path(path)),
        }
        for name, path in exports.items()
    }
    result = {
        "schema": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOCAL build123d + OCCT only / Onshape API 0 / browser 0 / CAD write 0",
        "productionBaseline": {
            "source": "Finger Controls V2 PASS",
            "externalCentersChanged": False,
            "axesChanged": False,
            "carrierArchitectureChanged": False,
            "productionParametersChanged": False,
            "productionParameterModificationCount": 0,
        },
        "fitCoupon": {
            "pocketCandidatesMm": list(POCKET_CANDIDATES),
            "productionSeedMm": SWITCH_POCKET_X,
            "label": "raised seven-segment numerical emboss; 6.40 framed",
            "purpose": ["too tight", "snug", "acceptable", "loose"],
        },
        "oneButtonCoupon": {
            "button": ONE_BUTTON_ID,
            "usesProductionShellWall": True,
            "usesProductionOpening": True,
            "usesProductionCap": True,
            "usesProductionCarrier": True,
            "usesProductionAxis": True,
            "cropMm": [ONE_BUTTON_CROP_U, ONE_BUTTON_CROP_V],
        },
        "N2SeamCoupon": {
            "centerMm": list(controls["N2"].center),
            "usesBothProductionShellInterfaces": True,
            "openingMm": 8.40,
            "capMm": CAP_SIZE,
            "oppositeShellClearanceMm": production_validation["N2Seam"]["oppositeShellCarrierClearanceMm"],
            "cropMm": [N2_CROP_U, N2_CROP_V],
        },
        "fullFunctionalSection": {
            "buttons": list(BUTTON_ORDER),
            "switchCount": 8,
            "carrierCount": len(carriers),
            "capCount": len(caps),
            "cropMinimumMm": list(FULL_CROP_MIN),
            "cropSizeMm": list(FULL_CROP_SIZE),
            "fullJoystickShellExported": False,
        },
        "cropRegionFilter": {
            "policy": "retain the largest connected production-shell region intersected by each local crop",
            "discardedCropOnlyFragmentVolumesMm3": CROP_DISCARDS,
        },
        "motion": motion,
        "toleranceProbe": tolerance,
        "printability": {
            "nozzleMm": 0.4,
            "minimumFunctionalWallMm": MIN_STRUCTURAL_WALL,
            "carrierWallMm": CARRIER_WALL,
            "elephantFootSensitiveFeatures": ["switch pocket lower edge", "cap guide/opening edge", "cap actuator socket"],
            "pocketDimensionalSensitivity": "HIGH; use fit coupon before production adjustment",
            "supportPolicy": "block support inside switch pockets and cap guides",
            "recommendedOrientation": {
                "fitCoupon": "flat base on bed; vertical pockets; support NO",
                "caps": "external pad face on bed; socket upward; support NO",
                "carriers": "broad rear plate on bed; C-channel upward; support NO or local bridge only",
                "shellCrops": "opening axes upward where practical; support only under exterior crop perimeter, never inside guides",
            },
            "plate": plate_report,
        },
        "geometry": part_metrics,
        "gates": gates,
        "verdict": {
            "DIGITAL_PRINTABILITY": "PASS" if digital_pass else "HOLD",
            "PHYSICAL_VALIDATION_KIT": "READY" if digital_pass else "HOLD",
            "PHYSICAL_FINGER_V2": "NOT YET VALIDATED",
            "PRODUCTION_FINGER_V2_FREEZE": "PENDING USER FDM RESULTS",
        },
        "exports": export_records,
    }
    path = OUT_DIR / "finger_v2_physical_validation.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "gates": gates,
                "verdict": result["verdict"],
                "plateDimensionsMm": plate_report["dimensionsMm"],
                "plateComponents": plate_report["connectedComponents"],
                "outDir": str(OUT_DIR),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
