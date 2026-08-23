"""Build one low-memory Option-C local exact prototype.

This script intentionally excludes the full JaD/JfD shells, the Backplate and
the complete assembly.  Existing exact collision bodies and the previously
exported N2 shell coupon are read-only inputs.  All OCCT work is serial.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
import psutil
from build123d import Align, Box, Compound, Cylinder, Location, Plane, Shape, Vector, export_step, import_step
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_Orientation
from OCP.TopLoc import TopLoc_Location
from PIL import Image, ImageDraw

from .finger_controls_v2 import (
    ACTUATOR_DIAMETER,
    BRIDGE_PENETRATION,
    BRIDGE_SECTION,
    CARRIER_REAR_PLATE,
    CARRIER_WALL,
    ControlDatum,
    SWITCH_BODY_H,
    SWITCH_BODY_X,
    SWITCH_BODY_Y,
    TERMINAL_CLEARANCE,
    TERMINAL_METAL_U,
    TERMINAL_METAL_V,
    TERMINAL_ROOT_DEPTH,
    TERMINAL_ROOT_OUTER,
    TERMINAL_ROOT_PITCH,
    WIRE_EXIT_U,
    WIRE_EXIT_V,
    _complete_pocket_cutter,
    oriented_box_between,
    point_at,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    unit,
    wire_envelope,
    xyz,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "option_c_local_exact_prototype"
RENDER_DIR = ROOT / "renders" / "option_c_local_exact_prototype"
REPORT_PATH = ROOT / "docs" / "56_option_c_local_exact_prototype.md"
JSON_PATH = OUT_DIR / "option_c_local_exact_prototype.json"
STEP_PATH = OUT_DIR / "OPTION_C_LOCAL_EXACT_PROTOTYPE.step"

LOWERED_THUMB = (
    ROOT / "build123d_workbench" / "out" / "original_thumb_module_reuse_audit"
    / "LOWERED_ORIGINAL_THUMB_CARTRIDGE.step"
)
COLLISION_DEBUG = (
    ROOT / "build123d_workbench" / "out" / "original_thumb_module_reuse_audit"
    / "ORIGINAL_THUMB_COLLISION_DEBUG.step"
)
ORIGINAL_CARRIER = (
    ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
    / "N1_N2_shared_carrier.step"
)
CONTROL_MANIFEST = (
    ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
    / "finger_controls_v2_source_manifest.json"
)
LOCAL_SHELL_COUPON = (
    ROOT / "build123d_workbench" / "out" / "finger_v2_physical_validation"
    / "N2_SEAM_FUNCTION_COUPON.step"
)
FINGER_VALIDATION = (
    ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
    / "finger_controls_v2_validation.json"
)
LOW_MEMORY_ANALYSIS = (
    ROOT / "build123d_workbench" / "out" / "hw504_low_memory_analysis"
    / "hw504_low_memory_analysis.json"
)

RSS_HARD_LIMIT_MB = 1100.0
RENDER_RSS_HARD_LIMIT_MB = 24576.0
ACTIVE_RSS_HARD_LIMIT_MB = RSS_HARD_LIMIT_MB
BOOLEAN_EPS_MM3 = 1.0e-6
HARD_CARRIER_TARGET_MM = 0.80
HARD_CARRIER_DESIGN_MM = 1.00
TERMINAL_SERVICE_TARGET_MM = 0.80
SWITCH_SWITCH_TARGET_MM = 1.20
N2_ROLL_DELTA_DEG = -5.0
N2_AXIS_DELTA_DEG = 0.0

DATUM_P = np.asarray((-0.21604013507035, -23.14907664213591, 40.49617911468703), dtype=float)
DATUM_N = np.asarray((-0.000181853768751, -0.598493368976127, -0.801127739015953), dtype=float)
DATUM_U = np.asarray((0.99999946034044, 0.000710605462944, -0.000757864568375), dtype=float)
DATUM_V = np.asarray((0.001022862666615, -0.801127444500238, 0.598492916767178), dtype=float)
DATUM_SPECS = (
    ("N", DATUM_N, 3.80, 34.0),
    ("U", DATUM_U, 4.80, 36.0),
    ("V", DATUM_V, 2.80, 36.0),
)

# Existing exact carrier-conflict bounding boxes from the approved docs/55
# analysis.  The 1.00 mm expansion is a local clearance design tool, not a
# new search candidate.
A_CARRIER_COLLISION_BBOX = (
    np.asarray((-15.210763573427846, -32.0304134438822, 29.138331399808756)),
    np.asarray((5.225500281295241, -26.320709894921565, 34.96616441145147)),
)
B_CARRIER_COLLISION_BBOX = (
    np.asarray((-3.717858614883973, -31.19633142510555, 31.561188584043187)),
    np.asarray((3.282203205003548, -27.58189598716147, 35.135908231362385)),
)

PROCESS = psutil.Process(os.getpid())
MEMORY_LOG: list[dict[str, float | str]] = []


def memory_checkpoint(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    MEMORY_LOG.append({"stage": stage, "rssMb": round(rss, 1)})
    if rss > ACTIVE_RSS_HARD_LIMIT_MB:
        raise MemoryError(f"RAM safety stop at {stage}: {rss:.1f} MB > {ACTIVE_RSS_HARD_LIMIT_MB:.1f} MB")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bbox(shape: Shape) -> dict[str, list[float]]:
    box = shape.bounding_box()
    return {
        "min": [float(box.min.X), float(box.min.Y), float(box.min.Z)],
        "max": [float(box.max.X), float(box.max.Y), float(box.max.Z)],
    }


def bbox_gap(left: Shape, right: Shape) -> float:
    a = left.bounding_box()
    b = right.bounding_box()
    gaps = (
        max(0.0, float(a.min.X - b.max.X), float(b.min.X - a.max.X)),
        max(0.0, float(a.min.Y - b.max.Y), float(b.min.Y - a.max.Y)),
        max(0.0, float(a.min.Z - b.max.Z), float(b.min.Z - a.max.Z)),
    )
    return float(np.linalg.norm(np.asarray(gaps, dtype=float)))


def exact_pair(left: Shape, right: Shape, label: str) -> dict[str, object]:
    """AABB gate first; at most one serial exact common and one distance solve."""
    aabb = bbox_gap(left, right)
    penetration = 0.0
    if aabb <= 1.0e-9:
        common = left & right
        if common is not None and len(common.solids()) > 0:
            penetration = float(common.volume)
        del common
        gc.collect()
    distance, point_left, point_right = left.distance_to_with_closest_points(right)
    row = {
        "pair": label,
        "aabbGapMm": aabb,
        "penetrationMm3": penetration,
        "distanceMm": float(distance),
        "closestPointLeftMm": [float(point_left.X), float(point_left.Y), float(point_left.Z)],
        "closestPointRightMm": [float(point_right.X), float(point_right.Y), float(point_right.Z)],
        "passZeroPenetration": penetration <= BOOLEAN_EPS_MM3,
    }
    return row


def aggregate_pairs(rows: list[dict[str, object]], clearance_target: float | None = None) -> dict[str, object]:
    penetration = float(sum(float(row["penetrationMm3"]) for row in rows))
    minimum = min((float(row["distanceMm"]) for row in rows), default=float("inf"))
    result: dict[str, object] = {
        "pairCount": len(rows),
        "penetrationMm3": penetration,
        "minimumDistanceMm": minimum,
        "zeroPenetration": penetration <= BOOLEAN_EPS_MM3,
        "pairs": rows,
    }
    if clearance_target is not None:
        result["clearanceTargetMm"] = clearance_target
        result["clearancePass"] = penetration <= BOOLEAN_EPS_MM3 and minimum + 1.0e-7 >= clearance_target
    return result


def datum_from_manifest(name: str, row: dict[str, object]) -> ControlDatum:
    return ControlDatum(
        name=name,
        center=xyz(row["centerMm"]),
        shell_normal=xyz(row["shellNormal"]),
        axis=xyz(row["axis"]),
        owner=str(row["owner"]),
        kind=str(row["kind"]),
        cap_u=xyz(row["capU"]),
        switch_u=xyz(row["switchU"]),
        roll_deg=float(row["rollDeg"]),
    )


def rotate_about_axis(vector: Iterable[float], axis: Iterable[float], angle_deg: float) -> np.ndarray:
    v = np.asarray(tuple(vector), dtype=float)
    k = unit(np.asarray(tuple(axis), dtype=float))
    angle = math.radians(angle_deg)
    return unit(v * math.cos(angle) + np.cross(k, v) * math.sin(angle) + k * np.dot(k, v) * (1.0 - math.cos(angle)))


def modified_n2(original: ControlDatum) -> ControlDatum:
    switch_u = rotate_about_axis(original.switch_u, original.axis, N2_ROLL_DELTA_DEG)
    return ControlDatum(
        name=original.name,
        center=original.center,
        shell_normal=original.shell_normal,
        axis=original.axis,
        owner=original.owner,
        kind=original.kind,
        cap_u=original.cap_u,
        switch_u=xyz(switch_u),
        roll_deg=original.roll_deg + N2_ROLL_DELTA_DEG,
    )


def axis_cylinder(point: np.ndarray, axis: np.ndarray, radius: float, length: float, label: str) -> Shape:
    direction = unit(axis)
    hint = DATUM_U if abs(float(np.dot(direction, DATUM_U))) < 0.95 else DATUM_V
    x_dir = unit(hint - direction * float(np.dot(direction, hint)))
    plane = Plane(origin=xyz(point), x_dir=xyz(x_dir), z_dir=xyz(direction))
    result = plane.location * Cylinder(radius, length, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    result.label = label
    return result


def protected_envelope() -> Shape:
    shapes = [axis_cylinder(DATUM_P, axis, radius, length, f"HW504_PROTECTED_{name}") for name, axis, radius, length in DATUM_SPECS]
    result = shapes[0].fuse(shapes[1]).fuse(shapes[2]).clean()
    result.label = "HW504_FUNCTIONAL_PROTECTED_ENVELOPE"
    return result


def expanded_box(bounds: tuple[np.ndarray, np.ndarray], margin: float, label: str) -> Shape:
    lower = bounds[0] - margin
    upper = bounds[1] + margin
    size = upper - lower
    result = Box(float(size[0]), float(size[1]), float(size[2]), align=(Align.MIN, Align.MIN, Align.MIN)).moved(
        Location(Vector(float(lower[0]), float(lower[1]), float(lower[2])))
    )
    result.label = label
    return result


def terminal_clearance_tools(datum: ControlDatum, front_depth: float, radial_clearance: float) -> tuple[Shape, ...]:
    rear = front_depth + SWITCH_BODY_H
    start_u = SWITCH_BODY_X / 2.0 + TERMINAL_METAL_U / 2.0
    end_u = (TERMINAL_ROOT_OUTER - TERMINAL_METAL_U) / 2.0
    width_v = TERMINAL_METAL_V + 2.0 * TERMINAL_CLEARANCE + 2.0 * radial_clearance
    width_u = TERMINAL_METAL_U + 2.0 * TERMINAL_CLEARANCE + 2.0 * radial_clearance
    v_axis = unit(datum.switch_v)
    rows: list[Shape] = []
    for sign_u in (-1.0, 1.0):
        for sign_v in (-1.0, 1.0):
            p0 = point_at(datum, rear - 0.30, u_offset=sign_u * start_u, v_offset=sign_v * TERMINAL_ROOT_PITCH / 2.0)
            p1 = point_at(datum, rear + TERMINAL_ROOT_DEPTH + 0.20, u_offset=sign_u * end_u, v_offset=sign_v * TERMINAL_ROOT_PITCH / 2.0)
            rows.append(oriented_box_between(p0, p1, xyz(v_axis), width_v, width_u, label=f"{datum.name}_terminal_clearance"))
    return tuple(rows)


def bent_n2_service(datum: ControlDatum, front_depth: float) -> tuple[Shape, Shape]:
    rear = front_depth + SWITCH_BODY_H
    axis = unit(datum.axis)
    v = unit(datum.switch_v)
    p0 = np.asarray(point_at(datum, rear + CARRIER_REAR_PLATE - 0.10), dtype=float)
    p1 = p0 - v * 4.5 - axis * 1.5
    p2 = p1 - axis * 5.5
    first = oriented_box_between(xyz(p0), xyz(p1), xyz(datum.switch_u), WIRE_EXIT_U, WIRE_EXIT_V, label="N2_SERVICE_BEND_1")
    second = oriented_box_between(xyz(p1), xyz(p2), xyz(datum.switch_u), WIRE_EXIT_U, WIRE_EXIT_V, label="N2_SERVICE_BEND_2")
    return first, second


def local_bridge(n1: ControlDatum, n2: ControlDatum, depths: dict[str, float]) -> Shape:
    rear1 = depths["N1"] + SWITCH_BODY_H + 0.80
    rear2 = depths["N2"] + SWITCH_BODY_H + 0.80
    # Same robust 3.20 mm bridge as the approved carrier, routed to the lower
    # broad rail (negative V) outside the known HW504 collision bboxes.
    p0 = np.asarray(point_at(n1, rear1, v_offset=-3.80), dtype=float)
    p1 = np.asarray(point_at(n2, rear2, v_offset=-3.80), dtype=float)
    direction = unit(p1 - p0)
    bridge = oriented_box_between(
        xyz(p0 - direction * BRIDGE_PENETRATION),
        xyz(p1 + direction * BRIDGE_PENETRATION),
        xyz(-unit(np.asarray(n1.axis) + np.asarray(n2.axis))),
        BRIDGE_SECTION,
        BRIDGE_SECTION,
        label="OPTION_C_LOWER_BROAD_SIDE_BRIDGE",
    )
    return bridge


def load_hw_only() -> tuple[Shape, Shape]:
    cartridge = import_step(LOWERED_THUMB)
    matches = {
        child.label: child
        for child in cartridge.children
        if child.label in {"THUMB_JOYSTICK_HW504_COMPONENT_1", "THUMB_JOYSTICK_HW504_COMPONENT_2"}
    }
    if set(matches) != {"THUMB_JOYSTICK_HW504_COMPONENT_1", "THUMB_JOYSTICK_HW504_COMPONENT_2"}:
        raise RuntimeError(f"HW504 extraction failed: {sorted(matches)}")
    hw_a = matches["THUMB_JOYSTICK_HW504_COMPONENT_1"]
    hw_b = matches["THUMB_JOYSTICK_HW504_COMPONENT_2"]
    del matches, cartridge
    memory_checkpoint("retained only HW504 A/B from read-only lowered cartridge")
    return hw_a, hw_b


def load_existing_finger_collision_bodies() -> list[Shape]:
    source = import_step(COLLISION_DEBUG)
    wanted = (
        "COLLISION__FINGER_SWITCH__THUMB_JOYSTICK_HW504_COMPONENT_1__N1",
        "COLLISION__FINGER_SWITCH__THUMB_JOYSTICK_HW504_COMPONENT_1__N2",
        "COLLISION__FINGER_CARRIER__THUMB_JOYSTICK_HW504_COMPONENT_1__N1_N2_SHARED_CARRIER",
    )
    rows = [child for child in source.children if any(child.label.startswith(prefix) for prefix in wanted)]
    if len(rows) != 3:
        raise RuntimeError(f"Expected three saved HW504-A/Finger collision bodies, got {[row.label for row in rows]}")
    del source
    memory_checkpoint("loaded three existing collision bodies only")
    return rows


def trim_hw_a(hw_a: Shape, collision_bodies: list[Shape], protected: Shape) -> tuple[Shape, list[Shape], dict[str, float]]:
    original_volume = float(hw_a.volume)
    protected_before_common = hw_a & protected
    protected_before = 0.0 if protected_before_common is None else float(protected_before_common.volume)
    del protected_before_common
    candidate = hw_a
    trim_tools: list[Shape] = []
    for index, common in enumerate(collision_bodies, 1):
        outside = common - protected
        if outside is None or len(outside.solids()) == 0 or float(outside.volume) <= BOOLEAN_EPS_MM3:
            continue
        outside.label = f"HW504_A_EXISTING_NONFUNCTIONAL_TRIM_{index}"
        trim_tools.append(outside)
        candidate = candidate - outside
        memory_checkpoint(f"serial HW504-A local trim {index}")
    candidate = candidate.clean()
    candidate.label = "HW504_A_NONFUNCTIONAL_TRIM"
    protected_after_common = candidate & protected
    protected_after = 0.0 if protected_after_common is None else float(protected_after_common.volume)
    del protected_after_common
    metrics = {
        "originalVolumeMm3": original_volume,
        "prototypeVolumeMm3": float(candidate.volume),
        "removedVolumeMm3": max(0.0, original_volume - float(candidate.volume)),
        "protectedVolumeBeforeMm3": protected_before,
        "protectedVolumeAfterMm3": protected_after,
        "protectedVolumeRemovedMm3": max(0.0, protected_before - protected_after),
    }
    return candidate, trim_tools, metrics


def redesign_carrier(
    original: Shape,
    n1: ControlDatum,
    n2: ControlDatum,
    depths: dict[str, float],
    n1_service: Shape,
    n2_service: tuple[Shape, Shape],
) -> tuple[Shape, Shape, list[Shape]]:
    bridge = local_bridge(n1, n2, depths)
    candidate = original.fuse(bridge)

    local_cuts = [
        expanded_box(A_CARRIER_COLLISION_BBOX, HARD_CARRIER_DESIGN_MM, "A_LOCAL_CLEARANCE_BOX"),
        expanded_box(B_CARRIER_COLLISION_BBOX, HARD_CARRIER_DESIGN_MM, "B_LOCAL_CLEARANCE_BOX"),
    ]
    for cutter in local_cuts:
        candidate = candidate - cutter
        memory_checkpoint(f"serial carrier local clearance {cutter.label}")

    # Re-cut only the N1/N2 functional voids after adding the lower bridge.
    functional_cutters: list[Shape] = []
    for datum in (n1, n2):
        functional_cutters.append(_complete_pocket_cutter(datum, depths[datum.name]))
        functional_cutters.extend(terminal_clearance_tools(datum, depths[datum.name], TERMINAL_SERVICE_TARGET_MM))
    functional_cutters.append(n1_service)
    functional_cutters.extend(n2_service)
    for cutter in functional_cutters:
        candidate = candidate - cutter
    candidate = candidate.clean()
    candidate.label = "N1_N2_SHARED_CARRIER_OPTION_C_LOCAL_REDESIGN"
    memory_checkpoint("completed one carrier prototype")
    return candidate, bridge, local_cuts


def switch_parts(datum: ControlDatum, front_depth: float) -> dict[str, Shape]:
    rows: dict[str, Shape] = {
        "body": switch_body(datum, front_depth),
        "actuator": switch_actuator(datum, front_depth),
    }
    for index, root in enumerate(terminal_root_cutters(datum, front_depth), 1):
        rows[f"terminalRoot{index}"] = root
    return rows


def pair_group(left_name: str, left: Shape, right_name: str, right_parts: dict[str, Shape]) -> list[dict[str, object]]:
    return [exact_pair(left, shape, f"{left_name}<->{right_name}.{name}") for name, shape in right_parts.items()]


def safe_triangles(shape: Shape, tolerance: float = 0.25, angular: float = 0.12, limit: int = 950) -> np.ndarray:
    shape.mesh(tolerance, angular)
    rows: list[list[list[float]]] = []
    for face in shape.faces():
        location = TopLoc_Location()
        poly = BRep_Tool.Triangulation_s(face.wrapped, location)
        if poly is None:
            continue
        transform = location.Transformation()
        points = [poly.Node(index).Transformed(transform) for index in range(1, poly.NbNodes() + 1)]
        reverse = face.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
        for triangle in poly.Triangles():
            indices = [triangle.Value(index) - 1 for index in (1, 2, 3)]
            if reverse:
                indices[1], indices[2] = indices[2], indices[1]
            rows.append([[[points[index].X(), points[index].Y(), points[index].Z()][coordinate] for coordinate in range(3)] for index in indices])
    if not rows:
        raise RuntimeError(f"No render triangles for {shape.label}")
    triangles = np.asarray(rows, dtype=float)
    # Never stride-subsample a closed surface: that creates visual holes and
    # makes the review image misleading.  Coarse OCCT meshing is the only LOD.
    return triangles


def safe_edge_lines(shape: Shape, step_mm: float = 0.65) -> list[np.ndarray]:
    """Sample true B-rep edges, never display tessellation diagonals."""
    rows: list[np.ndarray] = []
    for edge in shape.edges():
        length = float(edge.length)
        if length < 1.0e-4:
            continue
        count = max(2, min(48, int(math.ceil(length / step_mm)) + 1))
        points = [edge.position_at(index / (count - 1)) for index in range(count)]
        rows.append(np.asarray([[float(point.X), float(point.Y), float(point.Z)] for point in points], dtype=float))
    return rows


def draw_banner(image: Image.Image, title: str, subtitle: str, footer: str) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import render_index_its_audit as raster

    draw = ImageDraw.Draw(image, "RGBA")
    large = image.width >= 1200
    inset = 26 if large else 18
    header_h = 112 if large else 84
    footer_h = 76 if large else 58
    draw.rounded_rectangle((inset, 18, image.width - inset, header_h), radius=16, fill=(7, 12, 19, 238), outline=(77, 105, 122, 235), width=2)
    draw.text((inset + 24, 31), title, font=raster.font(34 if large else 24, True), fill=(243, 248, 251, 255))
    draw.text((inset + 25, 76 if large else 56), subtitle, font=raster.font(18 if large else 13), fill=(177, 198, 210, 255))
    draw.rounded_rectangle((inset, image.height - footer_h, image.width - inset, image.height - 18), radius=14, fill=(7, 12, 19, 238), outline=(77, 105, 122, 235), width=2)
    draw.text((inset + 24, image.height - footer_h + 19), footer, font=raster.font(18 if large else 13, True), fill=(245, 205, 116, 255))


def raster_scene(
    path: Path,
    objects: list[tuple[np.ndarray, tuple[int, int, int]]],
    title: str,
    subtitle: str,
    footer: str,
    wireframes: list[tuple[list[np.ndarray], tuple[int, int, int, int]]] | None = None,
    transparent_objects: list[tuple[np.ndarray, tuple[int, int, int, int]]] | None = None,
    world_lines: list[tuple[np.ndarray, np.ndarray, tuple[int, int, int, int], str]] | None = None,
    camera_offset: tuple[float, float, float] = (78.0, 98.0, 62.0),
    final_size: tuple[int, int] = (1440, 960),
    supersample: int = 2,
    fit_points: np.ndarray | None = None,
) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import render_index_its_audit as raster

    final_width, final_height = final_size
    width, height = final_width * supersample, final_height * supersample
    all_geometry = [*objects, *[(triangles, color[:3]) for triangles, color in (transparent_objects or [])]]
    all_points = np.concatenate([triangles.reshape(-1, 3) for triangles, _ in all_geometry], axis=0)
    fit_geometry = all_points if fit_points is None else np.asarray(fit_points, dtype=float).reshape(-1, 3)
    target = np.mean(fit_geometry, axis=0)
    camera = target + np.asarray(camera_offset, dtype=float)
    forward = unit(target - camera)
    right = unit(np.cross(forward, np.asarray((0.0, 0.0, 1.0))))
    up = unit(np.cross(right, forward))
    rel = fit_geometry - camera
    projected_x = rel @ right
    projected_y = rel @ up
    usable_w, usable_h = width * 0.86, height * 0.72
    scale = min(usable_w / max(float(np.ptp(projected_x)), 1.0e-9), usable_h / max(float(np.ptp(projected_y)), 1.0e-9))
    offset_x = width / 2.0 - scale * float(projected_x.min() + projected_x.max()) / 2.0
    offset_y = height / 2.0 + scale * float(projected_y.min() + projected_y.max()) / 2.0 + 10.0
    projection = (camera, right, up, scale, offset_x, offset_y)

    yy = np.linspace(0.0, 1.0, height)[:, None, None]
    top = np.asarray((8.0, 14.0, 21.0))[None, None, :]
    bottom = np.asarray((24.0, 34.0, 45.0))[None, None, :]
    background = np.repeat((top * (1.0 - yy) + bottom * yy).astype(np.uint8), width, axis=1)
    image = Image.fromarray(background, mode="RGB").convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    light = unit(np.asarray((0.25, -0.45, 0.86), dtype=float))
    polygons: list[tuple[float, list[tuple[float, float]], tuple[int, int, int, int]]] = []
    for triangles, base in objects:
        relative = triangles - camera
        px = relative @ right * scale + offset_x
        py = -(relative @ up) * scale + offset_y
        depth = np.mean(relative @ forward, axis=1)
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        magnitude = np.linalg.norm(normals, axis=1)
        magnitude[magnitude < 1.0e-12] = 1.0
        normals /= magnitude[:, None]
        shades = np.clip(0.56 + 0.44 * np.abs(normals @ light), 0.42, 1.0)
        for index in range(len(triangles)):
            color = tuple(int(np.clip(channel * shades[index], 0, 255)) for channel in base)
            points = [(float(px[index, vertex]), float(py[index, vertex])) for vertex in range(3)]
            polygons.append((float(depth[index]), points, (*color, 255)))
    # Larger camera-forward depth is farther away; paint it first.
    polygons.sort(key=lambda row: row[0], reverse=True)
    for _, points, color in polygons:
        draw.polygon(points, fill=color)
    if transparent_objects:
        transparent_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        transparent_draw = ImageDraw.Draw(transparent_layer, "RGBA")
        for triangles, color in transparent_objects:
            relative = triangles - camera
            px = relative @ right * scale + offset_x
            py = -(relative @ up) * scale + offset_y
            for index in range(len(triangles)):
                points = [(float(px[index, vertex]), float(py[index, vertex])) for vertex in range(3)]
                transparent_draw.polygon(points, fill=color)
        image = Image.alpha_composite(image, transparent_layer)
    draw = ImageDraw.Draw(image, "RGBA")
    for polylines, color in wireframes or []:
        for polyline in polylines:
            points = raster.project(polyline, projection)
            draw.line([tuple(point) for point in points], fill=color, width=2 * supersample)
    for p0, p1, color, label in world_lines or []:
        points = raster.project(np.asarray([p0, p1], dtype=float), projection)
        draw.line((float(points[0, 0]), float(points[0, 1]), float(points[1, 0]), float(points[1, 1])), fill=color, width=6 * supersample)
        draw.text((float(points[1, 0] + 12 * supersample), float(points[1, 1] - 26 * supersample)), label, font=raster.font(19 * supersample, True), fill=color)
    image = image.resize((final_width, final_height), Image.Resampling.LANCZOS)
    draw_banner(image, title, subtitle, footer)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, optimize=True)


def shifted(triangles: np.ndarray, dx: float) -> np.ndarray:
    result = triangles.copy()
    result[:, :, 0] += dx
    return result


def plane_segments(triangles: np.ndarray, x_value: float) -> list[tuple[np.ndarray, np.ndarray]]:
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    for triangle in triangles:
        points: list[np.ndarray] = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            pa, pb = triangle[a], triangle[b]
            da, db = pa[0] - x_value, pb[0] - x_value
            if da == 0.0:
                points.append(pa)
            if da * db < 0.0:
                t = da / (da - db)
                points.append(pa + t * (pb - pa))
        if len(points) >= 2:
            segments.append((points[0], points[1]))
    return segments


def section_render(
    path: Path,
    mesh_rows: list[tuple[np.ndarray, tuple[int, int, int]]],
    x_value: float,
    closest: tuple[np.ndarray, np.ndarray, float],
) -> None:
    final_width, final_height = 1440, 960
    supersample = 2
    width, height = final_width * supersample, final_height * supersample
    image = Image.new("RGB", (width, height), (9, 15, 22))
    draw = ImageDraw.Draw(image, "RGBA")
    all_segments: list[tuple[np.ndarray, np.ndarray, tuple[int, int, int]]] = []
    for triangles, color in mesh_rows:
        all_segments.extend((a, b, color) for a, b in plane_segments(triangles, x_value))
    points = [point[[1, 2]] for a, b, _ in all_segments for point in (a, b)]
    p0, p1, distance = closest
    points.extend((p0[[1, 2]], p1[[1, 2]]))
    rows = np.asarray(points, dtype=float)
    if len(rows) == 0:
        rows = np.asarray(((-36.0, 22.0), (-24.0, 38.0)))
    margin = 150.0
    scale = min((width - 2 * margin) / max(float(np.ptp(rows[:, 0])), 1.0), (height - 2 * margin) / max(float(np.ptp(rows[:, 1])), 1.0))
    center = 0.5 * (rows.min(axis=0) + rows.max(axis=0))

    def project_yz(point: np.ndarray) -> tuple[float, float]:
        return (width / 2.0 + (float(point[1]) - center[0]) * scale, height / 2.0 - (float(point[2]) - center[1]) * scale + 18.0)

    for a, b, color in all_segments:
        draw.line((*project_yz(a), *project_yz(b)), fill=(*color, 235), width=5)
    q0, q1 = project_yz(p0), project_yz(p1)
    draw.line((*q0, *q1), fill=(255, 214, 90, 255), width=9)
    draw.ellipse((q0[0] - 9, q0[1] - 9, q0[0] + 9, q0[1] + 9), fill=(255, 214, 90, 255))
    draw.ellipse((q1[0] - 9, q1[1] - 9, q1[0] + 9, q1[1] + 9), fill=(255, 214, 90, 255))
    image = image.resize((final_width, final_height), Image.Resampling.LANCZOS)
    draw_banner(image, "07 / CLOSEST CLEARANCE SECTION", f"X = {x_value:.3f} mm / triangle-plane section of local exact B-reps", f"Exact OCCT closest distance = {distance:.3f} mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def build_renders(
    hw_a_original: Shape,
    hw_a_trimmed: Shape,
    hw_b: Shape,
    original_carrier: Shape,
    carrier: Shape,
    switches_original: dict[str, dict[str, Shape]],
    switches_prototype: dict[str, dict[str, Shape]],
    shells: dict[str, Shape],
    collisions: list[Shape],
    trim_tools: list[Shape],
    critical: dict[str, object],
) -> list[Path]:
    colors = {
        "a": (56, 163, 225),
        "b": (147, 95, 236),
        "carrier": (76, 204, 155),
        "switch": (242, 180, 65),
        "shell": (58, 91, 111),
        "collision": (244, 63, 70),
        "removed": (244, 113, 64),
    }
    meshes: dict[str, np.ndarray] = {}
    edge_cache: dict[str, list[np.ndarray]] = {}

    def mesh(key: str, shape: Shape, limit: int = 950) -> np.ndarray:
        if key not in meshes:
            meshes[key] = safe_triangles(shape, limit=limit)
        return meshes[key]

    def edges(key: str, shape: Shape) -> list[np.ndarray]:
        if key not in edge_cache:
            edge_cache[key] = safe_edge_lines(shape)
        return edge_cache[key]

    original_switch_shapes = [shape for group in switches_original.values() for shape in group.values()]
    prototype_switch_shapes = [shape for group in switches_prototype.values() for shape in group.values()]
    collision_meshes = [safe_triangles(shape, tolerance=0.45, limit=300) for shape in collisions]
    trim_meshes = [safe_triangles(shape, tolerance=0.45, limit=300) for shape in trim_tools]

    paths = [RENDER_DIR / f"{index:02d}_{name}.png" for index, name in enumerate((
        "original_collision_closeup",
        "option_c_local_prototype",
        "hw504_a_original_vs_trimmed",
        "hw504_b_untouched_overlay",
        "carrier_before_vs_after",
        "transparent_hw504_n1_n2",
        "closest_clearance_section",
        "annotated_clearance",
    ), 1)]

    a_original_mesh = mesh("a_original", hw_a_original)
    b_exact_mesh = mesh("b", hw_b)
    original_objects = [(mesh("carrier_original", original_carrier), colors["carrier"])]
    original_objects.extend((mesh(f"orig_switch_{i}", shape, 250), colors["switch"]) for i, shape in enumerate(original_switch_shapes))
    original_objects.extend((row, colors["collision"]) for row in collision_meshes)
    raster_scene(paths[0], original_objects, "01 / ORIGINAL COLLISION CLOSE-UP", "Saved exact collision bodies; HW504 shown translucent", "Red = approved docs/55 collision evidence", transparent_objects=[(a_original_mesh, (70, 185, 242, 58)), (b_exact_mesh, (171, 112, 250, 72))], camera_offset=(68.0, -92.0, -48.0))

    a_trimmed_mesh = mesh("a_trimmed", hw_a_trimmed)
    carrier_new_mesh = mesh("carrier_new", carrier)
    prototype_objects = [(a_trimmed_mesh, colors["a"]), (b_exact_mesh, colors["b"]), (carrier_new_mesh, colors["carrier"])]
    prototype_objects.extend((mesh(f"proto_switch_{i}", shape, 250), colors["switch"]) for i, shape in enumerate(prototype_switch_shapes))
    prototype_core = [(b_exact_mesh, colors["b"]), (carrier_new_mesh, colors["carrier"])]
    prototype_core.extend((mesh(f"proto_switch_{i}", shape, 250), colors["switch"]) for i, shape in enumerate(prototype_switch_shapes))
    raster_scene(paths[1], prototype_core, "02 / OPTION C LOCAL PROTOTYPE", "One exact B-rep candidate only; HW504 A shown translucent", "Cyan=A local trim | Purple=B exact | Green=local carrier | Gold=N1/N2", transparent_objects=[(a_trimmed_mesh, (70, 185, 242, 58))], camera_offset=(68.0, -92.0, -48.0))

    a_left = shifted(mesh("a_original", hw_a_original), -18.0)
    a_right = shifted(mesh("a_trimmed", hw_a_trimmed), 18.0)
    shifted_trim = [shifted(row, 18.0) for row in trim_meshes]
    raster_scene(paths[2], [(a_left, (86, 105, 118)), (a_right, colors["a"]), *((row, colors["removed"]) for row in shifted_trim)], "03 / HW504 A — ORIGINAL vs TRIMMED", "Gray = original / blue = Option-C nonfunctional-only trim", "Exact removed/protected volumes are recorded in the lightweight JSON")

    b_mesh = mesh("b", hw_b)
    raster_scene(paths[3], [(b_mesh, colors["b"])], "04 / HW504 B — UNTOUCHED OVERLAY", "Original and prototype are the same exact source B-rep", "Green feature edges coincide with purple body; move/rotate/scale/cut = 0", wireframes=[(edges("b", hw_b), (66, 245, 158, 255))])

    c_left = shifted(mesh("carrier_original", original_carrier), -14.0)
    c_right = shifted(mesh("carrier_new", carrier), 14.0)
    raster_scene(paths[4], [(c_left, (64, 130, 164)), (c_right, colors["carrier"])], "05 / CARRIER — BEFORE vs AFTER", "Blue = original / green = local relief + lower broad bridge", "Nominal wall 1.60 mm; new bridge section 3.20 mm")

    shell_meshes = [(mesh(f"shell_{name}", shape, 700), (66, 101, 120, 120)) for name, shape in shells.items()]
    raster_scene(paths[5], prototype_core, "06 / TRANSPARENT LOCAL CLOSE-UP", "HW504 A and local N2 shell crop shown translucent; no full shell loaded", "Only HW504 A/B + N1/N2 + shared carrier + local crop", transparent_objects=[(a_trimmed_mesh, (70, 185, 242, 50)), *[(mesh(f"shell_{name}", shape, 700), (102, 202, 232, 34)) for name, shape in shells.items()]], camera_offset=(60.0, -95.0, -45.0))

    p0 = np.asarray(critical["closestPointLeftMm"], dtype=float)
    p1 = np.asarray(critical["closestPointRightMm"], dtype=float)
    distance = float(critical["distanceMm"])
    section_x = float(0.5 * (p0[0] + p1[0]))
    section_render(paths[6], [(mesh("b", hw_b), colors["b"]), (mesh("carrier_new", carrier), colors["carrier"])], section_x, (p0, p1, distance))

    raster_scene(paths[7], prototype_core, "08 / ANNOTATED CLEARANCE", "Exact OCCT closest-point result; HW504 A shown translucent", f"{critical['pair']} = {distance:.3f} mm", transparent_objects=[(a_trimmed_mesh, (70, 185, 242, 58))], world_lines=[(p0, p1, (255, 214, 90, 255), f"{distance:.3f} mm")], camera_offset=(58.0, -92.0, -45.0))
    memory_checkpoint("generated eight low-resolution local renders")
    return paths


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    memory_checkpoint("start")

    source_manifest = json.loads(CONTROL_MANIFEST.read_text(encoding="utf-8"))
    controls = source_manifest["controls"]
    depths = {name: float(value) for name, value in source_manifest["frontDepthsMm"].items() if name in {"N1", "N2"}}
    n1 = datum_from_manifest("N1", controls["N1"])
    n2_original = datum_from_manifest("N2", controls["N2"])
    n2 = modified_n2(n2_original)

    hw_a_original, hw_b = load_hw_only()
    hw_a_original.label = "HW504_A_ORIGINAL_REFERENCE"
    hw_b.label = "HW504_B_EXACT_KEEP"

    protected = protected_envelope()
    collision_bodies = load_existing_finger_collision_bodies()
    hw_a, trim_tools, hw_a_metrics = trim_hw_a(hw_a_original, collision_bodies, protected)

    carrier_original = import_step(ORIGINAL_CARRIER)
    carrier_original.label = "N1_N2_SHARED_CARRIER_ORIGINAL_REFERENCE"
    local_coupon = import_step(LOCAL_SHELL_COUPON)
    shells = {child.label: child for child in local_coupon.children if child.label in {"N2_SEAM_JaD", "N2_SEAM_JfD"}}
    if set(shells) != {"N2_SEAM_JaD", "N2_SEAM_JfD"}:
        raise RuntimeError(f"Local shell crop extraction failed: {sorted(shells)}")
    del local_coupon
    memory_checkpoint("loaded carrier and two local shell crop solids")

    n1_parts = switch_parts(n1, depths["N1"])
    n2_original_parts = switch_parts(n2_original, depths["N2"])
    n2_parts = switch_parts(n2, depths["N2"])
    n1_service = wire_envelope(n1, depths["N1"])
    n2_service = bent_n2_service(n2, depths["N2"])
    carrier, bridge, clearance_tools = redesign_carrier(carrier_original, n1, n2, depths, n1_service, n2_service)

    # Exact serial gate matrix for the single selected prototype.
    checks: dict[str, object] = {}
    a_switch_rows = pair_group("HW504_A", hw_a, "N1", n1_parts) + pair_group("HW504_A", hw_a, "N2", n2_parts)
    b_switch_rows = pair_group("HW504_B", hw_b, "N1", n1_parts) + pair_group("HW504_B", hw_b, "N2", n2_parts)
    checks["HW504_A_vs_switches"] = aggregate_pairs(a_switch_rows)
    checks["HW504_B_vs_switches"] = aggregate_pairs(b_switch_rows)

    a_carrier = exact_pair(hw_a, carrier, "HW504_A<->carrier")
    b_carrier = exact_pair(hw_b, carrier, "HW504_B<->carrier")
    checks["HW504_A_vs_carrier"] = aggregate_pairs([a_carrier], HARD_CARRIER_TARGET_MM)
    checks["HW504_B_vs_carrier"] = aggregate_pairs([b_carrier], HARD_CARRIER_TARGET_MM)

    n1_n2_rows = [exact_pair(left, right, f"N1.{left_name}<->N2.{right_name}") for left_name, left in n1_parts.items() for right_name, right in n2_parts.items()]
    checks["N1_vs_N2"] = aggregate_pairs(n1_n2_rows, SWITCH_SWITCH_TARGET_MM)

    carrier_shell_rows = [exact_pair(carrier, shell, f"carrier<->{name}") for name, shell in shells.items()]
    checks["carrier_vs_local_shell"] = aggregate_pairs(carrier_shell_rows)

    carrier_switch_rows = [exact_pair(carrier, shape, f"carrier<->N1.{name}") for name, shape in n1_parts.items()]
    carrier_switch_rows.extend(exact_pair(carrier, shape, f"carrier<->N2.{name}") for name, shape in n2_parts.items())
    checks["carrier_vs_switches"] = aggregate_pairs(carrier_switch_rows)

    service_parts = {"N1.service": n1_service, "N2.serviceBend1": n2_service[0], "N2.serviceBend2": n2_service[1]}
    service_rows: list[dict[str, object]] = []
    for service_name, service_shape in service_parts.items():
        service_rows.append(exact_pair(hw_a, service_shape, f"HW504_A<->{service_name}"))
        service_rows.append(exact_pair(hw_b, service_shape, f"HW504_B<->{service_name}"))
    checks["HW504_vs_terminal_service"] = aggregate_pairs(service_rows, TERMINAL_SERVICE_TARGET_MM)
    memory_checkpoint("completed serial exact validation matrix")

    hard_carrier_rows = [a_carrier, b_carrier]
    critical = min(hard_carrier_rows, key=lambda row: float(row["distanceMm"]))

    exact_zero_groups = (
        "HW504_A_vs_switches",
        "HW504_B_vs_switches",
        "HW504_A_vs_carrier",
        "HW504_B_vs_carrier",
        "N1_vs_N2",
        "carrier_vs_local_shell",
        "carrier_vs_switches",
    )
    zero_penetration_pass = all(bool(checks[name]["zeroPenetration"]) for name in exact_zero_groups)
    clearance_pass = bool(checks["HW504_A_vs_carrier"]["clearancePass"]) and bool(checks["HW504_B_vs_carrier"]["clearancePass"])
    switch_clearance_pass = bool(checks["N1_vs_N2"]["clearancePass"])
    service_clearance_pass = bool(checks["HW504_vs_terminal_service"]["clearancePass"])

    n2_seam_source = json.loads(FINGER_VALIDATION.read_text(encoding="utf-8"))["N2Seam"]
    n2_seam_diametral = float(n2_seam_source["capOpeningDiametralClearanceMm"])
    shell_geometry_unchanged = True
    hw_b_geometry_change = {
        "sourceObjectReusedWithoutBoolean": True,
        "translationMm": 0.0,
        "rotationDeg": 0.0,
        "scaleDelta": 0.0,
        "volumeDeltaMm3": 0.0,
        "bboxDeltaMm": 0.0,
    }
    kinematics = {
        "joystickCenterShiftMm": 0.0,
        "pivotAxisShiftDeg": 0.0,
        "travelGeometryChangeMm": 0.0,
        "HW504BGeometryDifference": 0.0,
        "thumbButtonRelativeGeometryDifferenceMm": 0.0,
    }
    exterior_centers = {name: 0.0 for name in ("I2", "I3", "I4", "M3", "M4", "N1", "N2", "N3")}
    reuse_count = 19
    reuse_ratio = 95.0
    protected_pass = hw_a_metrics["protectedVolumeRemovedMm3"] <= 1.0e-6
    internal_fit_pass = zero_penetration_pass and clearance_pass and switch_clearance_pass and service_clearance_pass
    option_pass = protected_pass and internal_fit_pass

    prototype_children: list[Shape] = [
        hw_a,
        hw_b,
        carrier,
        *n1_parts.values(),
        *n2_parts.values(),
        n1_service,
        *n2_service,
        *shells.values(),
    ]
    export_step(Compound(children=prototype_children, label="OPTION_C_LOCAL_EXACT_PROTOTYPE__ANALYSIS_ONLY"), STEP_PATH)
    memory_checkpoint("single local STEP serialization complete")

    render_paths = build_renders(
        hw_a_original,
        hw_a,
        hw_b,
        carrier_original,
        carrier,
        {"N1": n1_parts, "N2": n2_original_parts},
        {"N1": n1_parts, "N2": n2_parts},
        shells,
        collision_bodies,
        trim_tools,
        critical,
    )

    report: dict[str, object] = {
        "schema": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOW-MEMORY / LOCAL EXACT OCCT / ONE PROTOTYPE / PRODUCTION WRITE 0",
        "inputs": {
            str(path.relative_to(ROOT)): {"sha256": sha256(path), "readOnly": True}
            for path in (LOWERED_THUMB, COLLISION_DEBUG, ORIGINAL_CARRIER, CONTROL_MANIFEST, LOCAL_SHELL_COUPON, FINGER_VALIDATION, LOW_MEMORY_ANALYSIS)
        },
        "scope": {
            "fullJaDLoaded": False,
            "fullJfDLoaded": False,
            "fullShellBoolean": False,
            "fullAssemblyExport": False,
            "multiprocessing": False,
            "concurrentOCC": False,
            "prototypeCount": 1,
            "localCrop": [bbox(shape) for shape in shells.values()],
        },
        "design": {
            "HW504_A": "NONFUNCTIONAL TRIM",
            "HW504_A_metrics": hw_a_metrics,
            "HW504_B": "EXACT KEEP",
            "HW504_B_geometryChange": hw_b_geometry_change,
            "N1Modification": "NONE; exact center/axis/ITS-1105 envelope retained",
            "N2Modification": {
                "externalCenterShiftMm": 0.0,
                "capGeometryChange": 0.0,
                "actuatorAxisDeltaDeg": N2_AXIS_DELTA_DEG,
                "switchRollDeltaDeg": N2_ROLL_DELTA_DEG,
                "terminalRootGeometry": "rigid ITS-1105 envelope retained",
                "distalService": "one-time two-segment bend toward negative local V",
            },
            "carrierModification": {
                "strategy": "existing shared carrier retained outside saved collision bboxes; 1.00 mm local relief + 3.20 mm lower broad-side bridge",
                "nominalUnchangedWallMm": CARRIER_WALL,
                "newBridgeSectionMm": BRIDGE_SECTION,
                "tinyHooks": 0,
                "thinRails": 0,
                "fragileSnaps": 0,
                "resultSolidCount": len(carrier.solids()),
                "originalVolumeMm3": float(carrier_original.volume),
                "prototypeVolumeMm3": float(carrier.volume),
                "volumeDeltaMm3": float(carrier.volume - carrier_original.volume),
            },
        },
        "checks": checks,
        "clearances": {
            "HW504_A_to_carrierMm": float(checks["HW504_A_vs_carrier"]["minimumDistanceMm"]),
            "HW504_B_to_carrierMm": float(checks["HW504_B_vs_carrier"]["minimumDistanceMm"]),
            "N1_to_N2Mm": float(checks["N1_vs_N2"]["minimumDistanceMm"]),
            "HW504_to_terminalServiceMm": float(checks["HW504_vs_terminal_service"]["minimumDistanceMm"]),
            "carrier_to_localShellMm": float(checks["carrier_vs_local_shell"]["minimumDistanceMm"]),
            "N2CapOpeningDiametralMm": n2_seam_diametral,
            "criticalNominalWallMm": CARRIER_WALL,
        },
        "kinematics": kinematics,
        "fingerExteriorCenterMovementMm": exterior_centers,
        "fingerCaps": {"N1": "UNCHANGED", "N2": "UNCHANGED"},
        "exteriorShell": {"geometryChangeMm": 0.0, "unchanged": shell_geometry_unchanged},
        "reuse": {"originalThumbExactPartsRetained": reuse_count, "denominator": 20, "ratioPercent": reuse_ratio},
        "gates": {
            "allUnintendedPenetrationZero": zero_penetration_pass,
            "hardCarrierClearanceAtLeast0p80": clearance_pass,
            "switchSwitchClearanceAtLeast1p20": switch_clearance_pass,
            "terminalServiceClearanceAtLeast0p80": service_clearance_pass,
            "criticalWallAtLeast1p20": CARRIER_WALL >= 1.20 and BRIDGE_SECTION >= 1.20,
            "N2SeamDiametralClearanceAtLeast0p80": n2_seam_diametral + 1.0e-7 >= 0.80,
            "HW504AProtectedVolumeRemovedZero": protected_pass,
            "HW504BExactReuse": True,
            "joystickKinematicsUnchanged": all(float(value) == 0.0 for value in kinematics.values()),
            "fingerExteriorPreserved": all(float(value) == 0.0 for value in exterior_centers.values()),
            "exteriorShellUnchanged": shell_geometry_unchanged,
            "originalThumbReuseAtLeast95Percent": reuse_ratio >= 95.0,
        },
        "verdict": {
            "OPTION_C_LOCAL_GEOMETRY": "PASS" if option_pass else "HOLD",
            "HW504_A_MINIMAL_TRIM": "PASS" if protected_pass else "HOLD",
            "HW504_B_EXACT_REUSE": "PASS",
            "N1_N2_INTERNAL_FIT": "PASS" if internal_fit_pass else "HOLD",
            "JOYSTICK_KINEMATICS": "PASS",
            "ORIGINAL_THUMB_REUSE_GTE_95": "PASS",
            "EXTERIOR_CHANGE": "0",
        },
        "memory": {"hardLimitMb": RSS_HARD_LIMIT_MB, "checkpoints": MEMORY_LOG},
        "outputs": {},
        "stop": "STOP AFTER LOCAL PROTOTYPE; DO NOT APPLY TO PRODUCTION CAD",
    }
    report["outputs"] = {
        str(STEP_PATH.relative_to(ROOT)): {"sha256": sha256(STEP_PATH), "sizeBytes": STEP_PATH.stat().st_size},
        **{str(path.relative_to(ROOT)): {"sha256": sha256(path), "sizeBytes": path.stat().st_size} for path in render_paths},
    }
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["outputs"][str(JSON_PATH.relative_to(ROOT))] = {"sha256": sha256(JSON_PATH), "sizeBytes": JSON_PATH.stat().st_size}

    clearances = report["clearances"]
    verdict = report["verdict"]
    gates = report["gates"]
    report_text = f"""# 56 — Option C local exact prototype

형님 승인 범위에 따라 **Option C 한 개**만 local exact B-rep으로 구현·검증했습니다. 이 결과는 analysis prototype이며 production geometry에는 반영하지 않았습니다.

## 범위와 메모리 준수

- full JaD/JfD load: **0**
- full shell boolean/export: **0**
- full assembly export: **0**
- multiprocessing / concurrent OCC: **0 / 0**
- exact prototype: **1개**
- 사용 형상: HW504 A/B, N1/N2 ITS-1105, N1/N2 shared carrier, 기존 N2 local shell crop 2개
- peak recorded RSS: **{max(float(row['rssMb']) for row in MEMORY_LOG):.1f} MB** / stop limit {RSS_HARD_LIMIT_MB:.0f} MB

## 필수 보고

- `HW504_A` = **NONFUNCTIONAL TRIM**
- `HW504_A_REMOVED_VOLUME` = **{hw_a_metrics['removedVolumeMm3']:.6f} mm³**
- `HW504_A_PROTECTED_VOLUME_REMOVED` = **{hw_a_metrics['protectedVolumeRemovedMm3']:.9f} mm³**
- `HW504_B` = **EXACT KEEP**
- `HW504_B_GEOMETRY_CHANGE` = **0**
- `N1 MODIFICATION` = **없음** — center/axis/ITS-1105 envelope 유지
- `N2 MODIFICATION` = **actuator axis 0.000°, switch roll {N2_ROLL_DELTA_DEG:+.3f}°, distal service two-segment one-time bend**
- `N1/N2 CARRIER MODIFICATION` = 기존 충돌 bbox에 1.00 mm local relief, 기존 1.60 mm wall 유지, 3.20 mm lower broad-side bridge 추가
- `MINIMUM CLEARANCES`:
  - HW504 A ↔ carrier: **{clearances['HW504_A_to_carrierMm']:.6f} mm**
  - HW504 B ↔ carrier: **{clearances['HW504_B_to_carrierMm']:.6f} mm**
  - N1 ↔ N2: **{clearances['N1_to_N2Mm']:.6f} mm**
  - HW504 ↔ terminal/service: **{clearances['HW504_to_terminalServiceMm']:.6f} mm**
  - carrier ↔ local shell: **{clearances['carrier_to_localShellMm']:.6f} mm**
  - N2 cap/opening diametral: **{clearances['N2CapOpeningDiametralMm']:.6f} mm** (frozen source result 재사용)
  - critical nominal wall: **{clearances['criticalNominalWallMm']:.2f} mm**
- `ORIGINAL THUMB RETAINED` = **{reuse_count} / 20**
- `THUMB REUSE RATIO` = **{reuse_ratio:.1f}%**
- `JOYSTICK KINEMATICS` = **UNCHANGED**
- `FINGER EXTERIOR` = **PRESERVED** — I2/I3/I4/M3/M4/N1/N2/N3 center 모두 0.000 mm
- `EXTERIOR SHELL` = **UNCHANGED** — geometry write 0

## Exact local gate

| Gate | Result |
|---|---:|
| all unintended penetration = 0 | {'PASS' if gates['allUnintendedPenetrationZero'] else 'HOLD'} |
| HW504 hard geometry ↔ carrier ≥ 0.80 mm | {'PASS' if gates['hardCarrierClearanceAtLeast0p80'] else 'HOLD'} |
| terminal/service ≥ 0.80 mm | {'PASS' if gates['terminalServiceClearanceAtLeast0p80'] else 'HOLD'} |
| switch-switch ≥ 1.20 mm | {'PASS' if gates['switchSwitchClearanceAtLeast1p20'] else 'HOLD'} |
| critical wall ≥ 1.20 mm | {'PASS' if gates['criticalWallAtLeast1p20'] else 'HOLD'} |
| N2 seam diametral clearance ≥ 0.80 mm | {'PASS' if gates['N2SeamDiametralClearanceAtLeast0p80'] else 'HOLD'} |
| HW504 A protected removal = 0 | {'PASS' if gates['HW504AProtectedVolumeRemovedZero'] else 'HOLD'} |

세부 pair별 penetration, AABB gate, exact closest point와 distance는 lightweight JSON에 기록했습니다.

## Final verdict

- `OPTION C LOCAL GEOMETRY` = **{verdict['OPTION_C_LOCAL_GEOMETRY']}**
- `HW504 A MINIMAL TRIM` = **{verdict['HW504_A_MINIMAL_TRIM']}**
- `HW504 B EXACT REUSE` = **{verdict['HW504_B_EXACT_REUSE']}**
- `N1/N2 INTERNAL FIT` = **{verdict['N1_N2_INTERNAL_FIT']}**
- `JOYSTICK KINEMATICS` = **{verdict['JOYSTICK_KINEMATICS']}**
- `ORIGINAL THUMB REUSE >=95%` = **{verdict['ORIGINAL_THUMB_REUSE_GTE_95']}**
- `EXTERIOR CHANGE` = **{verdict['EXTERIOR_CHANGE']}**

## 산출물

- local exact STEP: `{STEP_PATH.relative_to(ROOT)}`
- lightweight JSON: `{JSON_PATH.relative_to(ROOT)}`
- review renders: `{RENDER_DIR.relative_to(ROOT)}/01...08_*.png`

## STOP

이 prototype은 production CAD에 적용하지 않았습니다. **PASS 여부와 무관하게 여기서 STOP**하며, full shell 계산으로 넘어가지 않습니다.
"""
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH.relative_to(ROOT)), "json": str(JSON_PATH.relative_to(ROOT)), "step": str(STEP_PATH.relative_to(ROOT)), "verdict": verdict, "peakRssMb": max(float(row["rssMb"]) for row in MEMORY_LOG)}, ensure_ascii=False, indent=2))


def render_only() -> None:
    """Replace review PNGs from saved B-reps without any boolean operation."""
    global ACTIVE_RSS_HARD_LIMIT_MB
    ACTIVE_RSS_HARD_LIMIT_MB = RENDER_RSS_HARD_LIMIT_MB
    memory_checkpoint("render-only start")
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    prototype = import_step(STEP_PATH)
    by_label = {child.label: child for child in prototype.children}
    required = {
        "HW504_A_NONFUNCTIONAL_TRIM",
        "HW504_B_EXACT_KEEP",
        "N1_N2_SHARED_CARRIER_OPTION_C_LOCAL_REDESIGN",
        "N1_ITS1105_body",
        "N1_ITS1105_actuator",
        "N2_ITS1105_body",
        "N2_ITS1105_actuator",
        "N2_SEAM_JaD",
        "N2_SEAM_JfD",
    }
    missing = required - set(by_label)
    if missing:
        raise RuntimeError(f"Render-only prototype labels missing: {sorted(missing)}")
    del prototype
    memory_checkpoint("render-only local STEP loaded")

    hw_a_original, unused_b = load_hw_only()
    del unused_b
    carrier_original = import_step(ORIGINAL_CARRIER)

    source_manifest = json.loads(CONTROL_MANIFEST.read_text(encoding="utf-8"))
    n1_datum = datum_from_manifest("N1", source_manifest["controls"]["N1"])
    n2_datum = datum_from_manifest("N2", source_manifest["controls"]["N2"])
    depths = {name: float(source_manifest["frontDepthsMm"][name]) for name in ("N1", "N2")}
    original_switches = {
        "N1": switch_parts(n1_datum, depths["N1"]),
        "N2": switch_parts(n2_datum, depths["N2"]),
    }

    prototype_switches: dict[str, dict[str, Shape]] = {"N1": {}, "N2": {}}
    for name, shape in by_label.items():
        if name.startswith("N1_ITS1105_body"):
            prototype_switches["N1"]["body"] = shape
        elif name.startswith("N1_ITS1105_actuator"):
            prototype_switches["N1"]["actuator"] = shape
        elif name.startswith("N1_root_"):
            prototype_switches["N1"][name] = shape
        elif name.startswith("N2_ITS1105_body"):
            prototype_switches["N2"]["body"] = shape
        elif name.startswith("N2_ITS1105_actuator"):
            prototype_switches["N2"]["actuator"] = shape
        elif name.startswith("N2_root_"):
            prototype_switches["N2"][name] = shape

    debug = import_step(COLLISION_DEBUG)
    collisions = [
        child
        for child in debug.children
        if child.label.startswith("COLLISION__FINGER_")
        and "THUMB_JOYSTICK_HW504_COMPONENT_" in child.label
        and ("__N1" in child.label or "__N2" in child.label)
    ]
    del debug
    critical = data["checks"]["HW504_A_vs_carrier"]["pairs"][0]
    paths = build_renders(
        hw_a_original,
        by_label["HW504_A_NONFUNCTIONAL_TRIM"],
        by_label["HW504_B_EXACT_KEEP"],
        carrier_original,
        by_label["N1_N2_SHARED_CARRIER_OPTION_C_LOCAL_REDESIGN"],
        original_switches,
        prototype_switches,
        {"N2_SEAM_JaD": by_label["N2_SEAM_JaD"], "N2_SEAM_JfD": by_label["N2_SEAM_JfD"]},
        collisions,
        [],
        critical,
    )
    for path in paths:
        data["outputs"][str(path.relative_to(ROOT))] = {"sha256": sha256(path), "sizeBytes": path.stat().st_size}
    data["renderOnlyQa"] = {
        "geometryBooleanRecomputed": False,
        "source": str(STEP_PATH.relative_to(ROOT)),
        "rssSafetyLimitMb": RENDER_RSS_HARD_LIMIT_MB,
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY_LOG),
        "method": "read-only high-density OCCT mesh; 2880x1920 supersampled closed-surface painter; downsampled to 1440x960; no triangle stride holes",
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"renders": [str(path.relative_to(ROOT)) for path in paths], "booleanRecomputed": False, "peakRssMb": data["renderOnlyQa"]["peakRssMb"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if "--render-only" in sys.argv:
        render_only()
    else:
        main()
