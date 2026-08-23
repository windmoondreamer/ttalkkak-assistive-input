"""Local sacrificial fit-test fixture for an actual SZH-EK056 joystick module.

The frozen OneGrip shell, lowered Thumb Backplate and approved N1/N2 carrier
are immutable inputs.  Only bounded local intersections and clearly labelled
test-fixture supports are exported.  The approximate web model is never fused
into the printable geometry; it is used only in review renders.
"""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import psutil
from build123d import (
    Align,
    Box,
    Compound,
    Location,
    Shape,
    Text,
    Vector,
    export_step,
    export_stl,
    extrude,
    import_step,
)

from .model import oriented_box_between
from .option_c_local_exact_prototype import raster_scene, safe_edge_lines, safe_triangles
from .original_thumb_module_reuse_audit import TARGET_SOURCE, load_target_parts
from .szh_ek056_provisional_thumb_integration_audit import (
    DATUM_P,
    DATUM_U,
    DATUM_V,
    JAD_SHELL,
    JFD_SHELL,
    N1_N2_CARRIER,
    OUTWARD,
    bbox,
    build_header_variants,
    build_reference,
    component_registry,
    in_reference_frame,
    load_button_targets,
    mounting_audit,
    placement,
    placed,
    sha256,
    xyz,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "szh_actual_fit_fixture"
RENDER_DIR = ROOT / "renders" / "szh_actual_fit_fixture"

FIXTURE_STEP = OUT_DIR / "SZH_EK056_ACTUAL_FIT_FIXTURE.step"
FIXTURE_STL = OUT_DIR / "SZH_EK056_ACTUAL_FIT_FIXTURE.stl"
BODY_STEP = OUT_DIR / "SZH_EK056_ACTUAL_FIT_FIXTURE_BODY.step"
BODY_STL = OUT_DIR / "SZH_EK056_ACTUAL_FIT_FIXTURE_BODY.stl"
CARRIER_STL = OUT_DIR / "SZH_EK056_ACTUAL_FIT_FIXTURE_N1_N2_CARRIER.stl"
JSON_PATH = OUT_DIR / "szh_ek056_actual_fit_fixture.json"

DOC70 = ROOT / "docs" / "70_finger_8_button_mechanical_baseline_checkpoint.md"
DOC71 = ROOT / "docs" / "71_szh_ek056_provisional_thumb_integration_audit.md"
KNOB_JSON = (
    ROOT / "build123d_workbench" / "out" / "szh_ek056_knob_interface_confirmation"
    / "szh_ek056_knob_interface_confirmation.json"
)
WEB_STEP = ROOT / "local_cad" / "reference" / "SZH_EK056_WEB_REFERENCE.step"
WEB_JSON = ROOT / "local_cad" / "reference" / "SZH_EK056_WEB_REFERENCE.json"

# Local frame is the approved joystick frame used by docs/71:
# X -> DATUM_V, Y -> DATUM_U, Z -> OUTWARD.
CROP_MIN = np.asarray((-27.5, -18.0, -9.0), float)
CROP_MAX = np.asarray((23.5, 18.0, 34.0), float)

# Sacrificial foundation is intentionally behind the module/body envelope.
FRAME_OUTER_X = 59.0
FRAME_OUTER_Y = 43.0
FRAME_INNER_X = 49.0
FRAME_INNER_Y = 33.0
FRAME_Z0 = -14.0
FRAME_THICKNESS = 3.0
LINK_SECTION = 3.2
LABEL_HEIGHT = 0.50

WEB_AXIAL_SENSITIVITY_MM = 1.8
RSS_LIMIT_MB = 24576.0
AVAILABLE_STOP_MB = 3072.0

PROCESS = psutil.Process(os.getpid())
MEMORY_LOG: list[dict[str, object]] = []


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    available = float(psutil.virtual_memory().available) / (1024.0 * 1024.0)
    MEMORY_LOG.append({"stage": stage, "rssMb": round(rss, 1), "systemAvailableMb": round(available, 1)})
    if rss > RSS_LIMIT_MB:
        raise MemoryError(f"RAM safety stop at {stage}: process RSS {rss:.1f} MB")
    if available < AVAILABLE_STOP_MB:
        raise MemoryError(f"RAM safety stop at {stage}: available RAM {available:.1f} MB")


def compound(children: Iterable[Shape], label: str) -> Compound:
    return Compound(children=list(children), label=label)


def local_box(lower: Iterable[float], upper: Iterable[float], label: str) -> Shape:
    lo = np.asarray(tuple(lower), float)
    hi = np.asarray(tuple(upper), float)
    size = hi - lo
    result = Box(
        float(size[0]), float(size[1]), float(size[2]),
        align=(Align.MIN, Align.MIN, Align.MIN),
    ).moved(Location(Vector(float(lo[0]), float(lo[1]), float(lo[2]))))
    result.label = label
    return result


def crop_source(path: Path, crop_world: Shape, label: str) -> Shape:
    full = import_step(path)
    section = (full & crop_world).clean()
    if not section.solids() or float(section.volume) <= 1.0e-6:
        raise RuntimeError(f"Empty local crop from {path}")
    section.label = label
    del full
    gc.collect()
    memory(f"crop {label}")
    return section


def local_bbox(shape: Shape, frame: Location) -> dict[str, list[float]]:
    local = frame.inverse() * shape
    result = bbox(local)
    del local
    return result


def text_solid(txt: str, size: float, x: float, y: float, z: float, rotation: float = 0.0) -> Shape:
    sketch = Text(txt, size, font="Arial", rotation=rotation)
    solid = extrude(sketch, LABEL_HEIGHT)
    solid = solid.moved(Location(Vector(x, y, z)))
    solid.label = f"EMBOSSED_{txt.replace(' ', '_')}"
    return solid


def foundation_frame() -> tuple[Shape, list[Shape]]:
    outer = Box(
        FRAME_OUTER_X, FRAME_OUTER_Y, FRAME_THICKNESS,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    ).moved(Location(Vector(0.0, 0.0, FRAME_Z0)))
    inner = Box(
        FRAME_INNER_X, FRAME_INNER_Y, FRAME_THICKNESS + 1.0,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    ).moved(Location(Vector(0.0, 0.0, FRAME_Z0 - 0.5)))
    ring = (outer - inner).clean()
    ring.label = "SACRIFICIAL_OPEN_FOUNDATION_FRAME"

    # Short inward ticks show the actual OneGrip frame directions without
    # placing any obstruction near the shaft/gimbal sweep.
    tick_z = FRAME_Z0 + FRAME_THICKNESS
    ticks = [
        local_box((20.5, 1.6, tick_z), (24.5, 2.4, tick_z + 0.55), "TILT_MARK_PLUS_X"),
        local_box((-24.5, 1.6, tick_z), (-20.5, 2.4, tick_z + 0.55), "TILT_MARK_MINUS_X"),
        local_box((0.0, 12.5, tick_z), (0.8, 16.5, tick_z + 0.55), "TILT_MARK_PLUS_Y"),
        local_box((0.0, -16.5, tick_z), (0.8, -12.5, tick_z + 0.55), "TILT_MARK_MINUS_Y"),
    ]

    labels = [
        text_solid("JOYSTICK AXIS", 2.05, 5.0, 19.0, tick_z),
        text_solid("PCB DATUM", 2.30, 5.0, -19.0, tick_z),
        text_solid("+Y", 2.25, -17.5, 19.0, tick_z),
        text_solid("-Y", 2.25, -17.5, -19.0, tick_z),
        text_solid("+X", 2.25, 27.0, 8.0, tick_z, 90.0),
        text_solid("-X", 2.25, -27.0, 8.0, tick_z, 90.0),
        text_solid("N2", 2.50, 27.0, 0.0, tick_z, 90.0),
        text_solid("N1", 2.50, 27.0, -9.0, tick_z, 90.0),
        text_solid("N1 T4 CHECK", 1.35, -27.0, -3.0, tick_z, 90.0),
        text_solid("TEST ONLY", 1.55, -5.0, 19.0, tick_z),
    ]
    return ring, [*ticks, *labels]


def local_vertices(shape: Shape, frame: Location) -> np.ndarray:
    local = frame.inverse() * shape
    points = np.asarray(
        [[float(vertex.center().X), float(vertex.center().Y), float(vertex.center().Z)] for vertex in local.vertices()],
        dtype=float,
    )
    del local
    if points.size == 0:
        raise RuntimeError(f"No vertices for support anchor: {shape.label}")
    return points


def support_link(shape: Shape, frame: Location, name: str, side: int) -> tuple[Shape, dict[str, object]]:
    points = local_vertices(shape, frame)
    z_threshold = float(np.quantile(points[:, 2], 0.40))
    candidates = points[points[:, 2] <= z_threshold]
    side_rows = candidates[candidates[:, 0] * float(side) >= 0.0]
    if len(side_rows) >= 2:
        candidates = side_rows
    radial = np.sqrt((candidates[:, 0] / (FRAME_INNER_X / 2.0)) ** 2 + (candidates[:, 1] / (FRAME_INNER_Y / 2.0)) ** 2)
    anchor = candidates[int(np.argmax(radial))]

    x, y, z = [float(value) for value in anchor]
    if abs(x) < 1.0e-6 and abs(y) < 1.0e-6:
        x = FRAME_INNER_X / 2.0
    tx = (FRAME_INNER_X / 2.0 + 1.2) / max(abs(x), 1.0e-6)
    ty = (FRAME_INNER_Y / 2.0 + 1.2) / max(abs(y), 1.0e-6)
    scale = min(tx, ty)
    edge = np.asarray((x * scale, y * scale, FRAME_Z0 + FRAME_THICKNESS * 0.55), float)
    foot = np.asarray((x, y, FRAME_Z0 + FRAME_THICKNESS * 0.55), float)

    horizontal = oriented_box_between(
        tuple(edge), tuple(foot), (0.0, 0.0, 1.0), LINK_SECTION, LINK_SECTION,
        label=f"{name}_FOUNDATION_LINK",
    )
    horizontal.label = f"{name}_FOUNDATION_LINK"
    top_z = max(z + 1.2, float(foot[2]) + 0.8)
    pillar = local_box(
        (x - LINK_SECTION / 2.0, y - LINK_SECTION / 2.0, float(foot[2]) - LINK_SECTION / 2.0),
        (x + LINK_SECTION / 2.0, y + LINK_SECTION / 2.0, top_z),
        f"{name}_ANCHOR_PILLAR",
    )
    link = compound([horizontal, pillar], f"{name}_SACRIFICIAL_SUPPORT")
    return link, {
        "target": name,
        "supportSideLocalX": "POSITIVE" if side > 0 else "NEGATIVE",
        "anchorLocalMm": [x, y, z],
        "foundationEdgeLocalMm": edge.tolist(),
        "sectionMm": LINK_SECTION,
        "fixtureOnly": True,
    }


def file_record(path: Path) -> dict[str, object]:
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def build_renders(
    body: Shape,
    carrier: Shape,
    frame_world: Shape,
    components: dict[str, dict[str, object]],
    targets: dict[str, dict[str, Shape]],
) -> list[Path]:
    paths = [
        RENDER_DIR / "01_actual_fit_fixture_assembled.png",
        RENDER_DIR / "02_access_windows_and_n1_t4.png",
        RENDER_DIR / "03_shaft_tilt_direction_reference.png",
    ]
    body_mesh = safe_triangles(body, tolerance=0.38, angular=0.16)
    carrier_mesh = safe_triangles(carrier, tolerance=0.28, angular=0.14)
    frame_edges = safe_edge_lines(frame_world, step_mm=0.55)

    static_names = ("PCB", "CENTER_GIMBAL", "X_POT", "Y_POT", "BOTTOM_SWITCH", "SHAFT", "HEADER_PLASTIC", "HEADER_DISTAL_PINS")
    module_meshes = {
        name: safe_triangles(components[name]["shape"], tolerance=0.35, angular=0.16)
        for name in static_names
    }
    colors = {
        "PCB": (45, 163, 106),
        "CENTER_GIMBAL": (189, 197, 204),
        "X_POT": (235, 109, 68),
        "Y_POT": (65, 146, 221),
        "BOTTOM_SWITCH": (228, 219, 194),
        "SHAFT": (245, 196, 74),
        "HEADER_PLASTIC": (190, 101, 215),
        "HEADER_DISTAL_PINS": (221, 174, 72),
    }
    module_objects = [(module_meshes[name], colors[name]) for name in static_names]
    axis_p0 = np.asarray(DATUM_P, float) - np.asarray(OUTWARD, float) * 12.0
    axis_p1 = np.asarray(DATUM_P, float) + np.asarray(OUTWARD, float) * 25.0
    direction_lines = [
        (np.asarray(DATUM_P, float), np.asarray(DATUM_P, float) + np.asarray(DATUM_V, float) * 16.0, (255, 93, 96, 255), "+X"),
        (np.asarray(DATUM_P, float), np.asarray(DATUM_P, float) - np.asarray(DATUM_V, float) * 16.0, (255, 93, 96, 255), "-X"),
        (np.asarray(DATUM_P, float), np.asarray(DATUM_P, float) + np.asarray(DATUM_U, float) * 16.0, (81, 204, 156, 255), "+Y"),
        (np.asarray(DATUM_P, float), np.asarray(DATUM_P, float) - np.asarray(DATUM_U, float) * 16.0, (81, 204, 156, 255), "-Y"),
    ]
    raster_scene(
        paths[0],
        [(body_mesh, (63, 111, 139)), (carrier_mesh, (71, 190, 160)), *module_objects],
        "SZH-EK056 ACTUAL-PART FIT FIXTURE",
        "local shell + lowered Backplate + frozen N1/N2 carrier | web module shown for position only",
        "Printable output excludes the web module; stock knob removed, stock header retained",
        wireframes=[(frame_edges, (244, 207, 111, 255))],
        camera_offset=(72.0, -92.0, -58.0),
    )

    switch_shapes = [
        targets["N1"]["switch_body"], targets["N1"]["T1"], targets["N1"]["T2"], targets["N1"]["T3"], targets["N1"]["T4"],
        targets["N2"]["switch_body"], targets["N2"]["T1"], targets["N2"]["T2"], targets["N2"]["T3"], targets["N2"]["T4"],
    ]
    switch_meshes = [safe_triangles(shape, tolerance=0.25, angular=0.14) for shape in switch_shapes]
    raster_scene(
        paths[1],
        [(carrier_mesh, (67, 191, 157)), *[(mesh, (240, 175, 69)) for mesh in switch_meshes]],
        "OPEN ACCESS / N1 T4 DIRECT INSPECTION",
        "rear, side and shell-wall wire departures remain physically reachable",
        "N1 T4 geometry is frozen; mark contact on the sacrificial fixture only",
        transparent_objects=[(body_mesh, (68, 128, 156, 72)), (module_meshes["PCB"], (45, 163, 106, 115))],
        wireframes=[(safe_edge_lines(targets["N1"]["T4"], step_mm=0.35), (255, 77, 82, 255))],
        camera_offset=(58.0, -72.0, -42.0),
    )

    raster_scene(
        paths[2],
        [(body_mesh, (62, 104, 128)), (module_meshes["CENTER_GIMBAL"], colors["CENTER_GIMBAL"]), (module_meshes["SHAFT"], colors["SHAFT"])],
        "CENTER / ±X / ±Y SHAFT TILT REFERENCE",
        "simple fixture marks identify directions; actual mechanical angle is measured on the real part",
        "Record FREE / TOUCH / BLOCKED with the stock knob removed",
        transparent_objects=[(carrier_mesh, (74, 193, 160, 72))],
        world_lines=[(axis_p0, axis_p1, (255, 214, 90, 255), "JOYSTICK AXIS"), *direction_lines],
        camera_offset=(70.0, -88.0, -45.0),
    )
    return paths


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    guard_paths = [DOC70, DOC71, KNOB_JSON, WEB_STEP, WEB_JSON, TARGET_SOURCE, JAD_SHELL, JFD_SHELL, N1_N2_CARRIER]
    for path in guard_paths:
        if not path.exists():
            raise FileNotFoundError(path)
    guard_before = {str(path.relative_to(ROOT)): sha256(path) for path in guard_paths}
    memory("start/hash guard")

    frame, origin = placement()
    crop_local = local_box(CROP_MIN, CROP_MAX, "SZH_ACTUAL_FIT_LOCAL_CROP_TOOL")
    crop_world = frame * crop_local
    crop_world.label = "SZH_ACTUAL_FIT_LOCAL_CROP_TOOL_WORLD"

    jad = crop_source(JAD_SHELL, crop_world, "JAD_CURRENT_SHELL_LOCAL_FIT_SECTION")
    jfd = crop_source(JFD_SHELL, crop_world, "JFD_CURRENT_SHELL_LOCAL_FIT_SECTION")
    thumb_parts = load_target_parts()
    backplate_full = next(part.shape for part in thumb_parts if part.name == "THUMB_BACKPLATE")
    backplate = (backplate_full & crop_world).clean()
    backplate.label = "LOWERED_THUMB_BACKPLATE_LOCAL_MOUNT_REFERENCE"
    del backplate_full, thumb_parts
    memory("lowered Backplate local crop")

    carrier = import_step(N1_N2_CARRIER)
    carrier.label = "N1_N2_APPROVED_CARRIER_EXACT_COPY"
    _, targets = load_button_targets(carrier)
    memory("frozen carrier and terminal references")

    foundation_local, marks_local = foundation_frame()
    links_local: list[Shape] = []
    link_records: list[dict[str, object]] = []
    for name, section in (("JAD", jad), ("JFD", jfd), ("BACKPLATE", backplate)):
        for side, suffix in ((-1, "NEG_X"), (1, "POS_X")):
            link, record = support_link(section, frame, f"{name}_{suffix}", side)
            links_local.append(link)
            link_records.append(record)
    fixture_only_local = compound(
        [foundation_local, *marks_local, *links_local],
        "SACRIFICIAL_FRAME_LABELS_AND_SUPPORTS",
    )
    fixture_only_world = frame * fixture_only_local
    fixture_only_world.label = "SACRIFICIAL_FRAME_LABELS_AND_SUPPORTS_WORLD"

    body = compound(
        [jad, jfd, backplate, fixture_only_world],
        "SZH_EK056_ACTUAL_FIT_FIXTURE_BODY__TEST_ONLY",
    )
    assembly = compound(
        [body, carrier],
        "SZH_EK056_ACTUAL_FIT_FIXTURE__SACRIFICIAL_PROTOTYPE",
    )
    memory("fixture assembly built")

    # docs/71's bounded axial sensitivity is used only to place the translucent
    # web reference in renders.  The printable fixture contains no web solids.
    _, web_parts, _, _ = build_reference()
    web_shift = Location(Vector(0.0, 0.0, WEB_AXIAL_SENSITIVITY_MM))
    shifted_parts = {name: shape.moved(web_shift) for name, shape in web_parts.items()}
    stock_header, direct_header = build_header_variants(shifted_parts, frame)
    components = component_registry(shifted_parts, frame, stock_header, direct_header)

    # Confirm the exact source mount plane in the same local frame.
    original_hw = [part.shape for part in load_target_parts() if part.category == "joystickMechanism"]
    hw_primary = max(original_hw, key=lambda shape: float(shape.volume))
    mounting = mounting_audit(hw_primary, origin)
    old_mount_z = [float(row["originalInSzhFrameMm"][2]) for row in mounting["pairs"]]

    export_step(assembly, FIXTURE_STEP)
    export_stl(assembly, FIXTURE_STL, tolerance=0.05, angular_tolerance=0.08)
    # OCCT's STEP writer can retain assembly ownership on a previously written
    # nested Compound.  Fresh identity copies of its leaf solids keep the
    # optional print split independent without changing any coordinates.
    body_split = compound(
        [solid.moved(Location()) for solid in body.solids()],
        "SZH_EK056_ACTUAL_FIT_FIXTURE_BODY_PRINT_SPLIT",
    )
    carrier_split = carrier.moved(Location())
    carrier_split.label = "N1_N2_APPROVED_CARRIER_EXACT_COPY_PRINT_SPLIT"
    export_step(body_split, BODY_STEP)
    export_stl(body_split, BODY_STL, tolerance=0.05, angular_tolerance=0.08)
    export_stl(carrier_split, CARRIER_STL, tolerance=0.04, angular_tolerance=0.07)
    memory("STEP/STL exports")

    render_paths = build_renders(body, carrier, fixture_only_world, components, targets)
    memory("review renders")

    guard_after = {str(path.relative_to(ROOT)): sha256(path) for path in guard_paths}
    if guard_before != guard_after:
        raise RuntimeError("Frozen/source hash guard changed while creating the test fixture")

    # Re-import mandatory deliverables for a bounded serialization check.
    step_check = import_step(FIXTURE_STEP)
    step_leaf_solids = list(step_check.solids())
    step_solids = len(step_leaf_solids)
    step_root_volume = float(step_check.volume)
    step_volume = float(sum(float(solid.volume) for solid in step_leaf_solids))
    step_bbox = bbox(step_check)
    step_labels: list[str] = []

    def collect_labels(shape: Shape) -> None:
        step_labels.append(str(shape.label))
        for child in shape.children:
            collect_labels(child)

    collect_labels(step_check)
    exported_carrier = next(child for child in step_check.children if "CARRIER" in str(child.label))
    source_carrier_check = import_step(N1_N2_CARRIER)
    carrier_common = source_carrier_check & exported_carrier
    carrier_check = {
        "sourceVolumeMm3": float(source_carrier_check.volume),
        "exportedVolumeMm3": float(exported_carrier.volume),
        "commonVolumeMm3": float(carrier_common.volume),
        "minimumDistanceMm": float(source_carrier_check.distance_to(exported_carrier)),
        "exactCopy": abs(float(carrier_common.volume) - float(source_carrier_check.volume)) <= 1.0e-6,
    }
    web_labels_in_fixture = [
        label for label in step_labels
        if any(token in label for token in ("SZH_HEADER", "CENTRAL_GIMBAL", "PCB_34P5", "JOYSTICK_SHAFT_INFERRED"))
    ]
    del step_check
    memory("serialized STEP re-import")

    outputs = [FIXTURE_STEP, FIXTURE_STL, BODY_STEP, BODY_STL, CARRIER_STL]
    data: dict[str, object] = {
        "schema": "onegrip.szh_ek056.actual_fit_fixture.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "classification": "TEST FIXTURE / SACRIFICIAL PROTOTYPE / NOT PRODUCTION GEOMETRY",
        "mode": "LOCAL ONLY / SINGLE PROCESS / SERIAL OCCT / WEB REFERENCE FOR RENDER ONLY",
        "productionGeometryModificationCount": 0,
        "sourceHashesBeforeAfterIdentical": True,
        "sourceSha256": guard_after,
        "realCoordinateFrame": {
            "localOriginWorldMm": [float(value) for value in origin],
            "joystickPivotDatumWorldMm": [float(value) for value in DATUM_P],
            "joystickAxisWorld": [float(value) for value in OUTWARD],
            "localXWorld": [float(value) for value in DATUM_V],
            "localYWorld": [float(value) for value in DATUM_U],
            "localZWorld": [float(value) for value in OUTWARD],
            "sourceGeometryTranslationMm": 0.0,
            "sourceGeometryRotationDeg": 0.0,
        },
        "crop": {
            "localMinMm": CROP_MIN.tolist(),
            "localMaxMm": CROP_MAX.tolist(),
            "sizeMm": (CROP_MAX - CROP_MIN).tolist(),
            "fullShellExported": False,
            "fullShellTessellated": False,
            "serialFullShellToLocalCropOperations": 2,
        },
        "fixtureArchitecture": {
            "mandatoryAssembly": "body + separately removable exact-copy N1/N2 carrier",
            "bodyContents": [
                "current JaD local shell section",
                "current JfD local shell section",
                "lowered original Thumb Backplate local mount section",
                "sacrificial open foundation/labels/support links",
            ],
            "carrierContents": "approved carrier exact copy; no terminal/switch body is printed",
            "assemblyCoordinates": "original OneGrip world coordinates",
            "splitPrintAllowed": True,
            "stockKnobInPrintable": False,
            "customKnobAdapterInPrintable": False,
            "webJoystickInPrintable": False,
        },
        "access": {
            "moduleInsertion": "open central rear aperture; insert by hand with stock knob removed",
            "stockHeader": "present during actual test; open side/rear observation",
            "windows": [
                "central rear module insertion window",
                "open PCB/header side crop boundary",
                "open N1/N1-T4 inspection side",
                "open N2 inspection side",
                "open shaft/gimbal exterior opening",
                "rear/side/shell-wall wire probe access",
            ],
            "wireProbeDiameterMm": [1.0, 1.3],
        },
        "labels": ["N1", "N2", "PCB DATUM", "JOYSTICK AXIS", "+X", "-X", "+Y", "-Y", "N1 T4 CHECK", "TEST ONLY"],
        "supportLinks": link_records,
        "referenceOnlyWebPlacement": {
            "quality": "LOW / APPROXIMATE",
            "axialSensitivityMm": WEB_AXIAL_SENSITIVITY_MM,
            "webReferenceExportedIntoFixture": False,
            "stockKnobExcluded": True,
            "stockHeaderIncludedInRenders": True,
        },
        "mountReference": {
            "originalMountHoleCenterPlaneLocalZMm": float(np.mean(old_mount_z)),
            "originalMountHoleCenterPlaneSpreadMm": float(np.ptp(old_mount_z)),
            "webReferenceMountPlaneOffsetMm": float(mounting["mountingPlaneOffsetMm"]),
            "webPatternVerdict": mounting["verdict"],
            "hardLocatorFromWebDimensions": False,
            "instruction": "hold/locate the actual module against the preserved Backplate/opening; measure actual position before designing an adapter",
        },
        "localGeometryBbox": {
            "JaD": local_bbox(jad, frame),
            "JfD": local_bbox(jfd, frame),
            "Backplate": local_bbox(backplate, frame),
            "N1N2Carrier": local_bbox(carrier, frame),
            "fixtureAssemblyWorld": bbox(assembly),
        },
        "serializationCheck": {
            "stepSolidCount": step_solids,
            "stepVolumeMm3": step_volume,
            "stepRootCompoundMassPropertyMm3": step_root_volume,
            "stepBboxWorldMm": step_bbox,
            "stepNonEmpty": step_solids > 0 and step_volume > 0.0,
            "carrier": carrier_check,
            "webReferenceLabelsInFixture": web_labels_in_fixture,
            "webReferenceSolidsAbsent": len(web_labels_in_fixture) == 0,
        },
        "outputs": {path.name: file_record(path) for path in outputs},
        "renders": [file_record(path) for path in render_paths],
        "memoryLog": MEMORY_LOG,
        "stop": "STOP AFTER FIXTURE AND TEST SHEET; actual measurements required before N1/N2/Thumb redesign",
    }
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "fixtureStep": str(FIXTURE_STEP),
        "fixtureStl": str(FIXTURE_STL),
        "solidCount": step_solids,
        "volumeMm3": step_volume,
        "productionGeometryModificationCount": 0,
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY_LOG),
    }, indent=2))


if __name__ == "__main__":
    main()
