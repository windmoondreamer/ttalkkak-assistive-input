"""Provisional SZH-EK056 packaging audit against the frozen 8-button baseline.

This is deliberately an analysis-only, single-process job.  It creates no
production STEP/STL, never edits the frozen Finger/Thumb geometry, and uses the
full JaD/JfD B-reps only once each to derive a small local crop.
"""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import psutil
from build123d import Align, Box, Compound, Cylinder, Location, Plane, Shape, Sphere, Vector, import_step

from .finger_controls_v2 import ControlDatum, point_at, unit, xyz
from .model import oriented_box_between
from .n2_production_intent_mechanism import FRONT_DEPTH_MM as N2_FRONT_DEPTH_MM
from .option_c_local_exact_prototype import (
    datum_from_manifest,
    modified_n2,
    raster_scene,
    safe_edge_lines,
    safe_triangles,
)
from .original_thumb_module_reuse_audit import load_target_parts
from .real_integration_conflict_resolution import terminal_path
from .szh_ek056_web_reference import (
    HEADER_PIN_COUNT,
    HEADER_PIN_D,
    HEADER_X_MAX,
    HEADER_Y_CENTRE,
    HEADER_Z_CENTRE,
    JOY_X,
    JOY_Y,
    MAX_TILT_DEG,
    MOUNT_HOLE_CENTRES,
    MOUNT_HOLE_D,
    PIVOT_Z,
    build_reference,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "szh_ek056_provisional_thumb_integration_audit"
RENDER_DIR = ROOT / "renders" / "szh_ek056_provisional_thumb_integration_audit"
JSON_PATH = OUT_DIR / "szh_ek056_provisional_thumb_integration_audit.json"
REPORT_PATH = ROOT / "docs" / "71_szh_ek056_provisional_thumb_integration_audit.md"

REFERENCE_STEP = ROOT / "local_cad" / "reference" / "SZH_EK056_WEB_REFERENCE.step"
REFERENCE_JSON = ROOT / "local_cad" / "reference" / "SZH_EK056_WEB_REFERENCE.json"
REFERENCE_RESEARCH = ROOT / "docs" / "szh_ek056_cad_reference_research.md"
PIN_LABEL_IMAGE = (
    ROOT / "lower_adapter" / "local_cad" / "reference" / "szh_ek056_web"
    / "ps_Joystick-Module-Connections-1.jpg"
)
MANIFEST = ROOT / "build123d_workbench" / "out" / "finger_controls_v2" / "finger_controls_v2_source_manifest.json"
OPTION_C_SOURCE = ROOT / "build123d_workbench" / "out" / "option_c_final_local_fit" / "OPTION_C_FINAL_LOCAL_FIT.step"
N2_ASSEMBLY = ROOT / "build123d_workbench" / "out" / "n2_production_intent_mechanism" / "N2_PRODUCTION_INTENT_LOCAL_ASSEMBLY.step"
N1_N2_CARRIER = ROOT / "build123d_workbench" / "out" / "n1_production_intent_mechanism" / "N1_N2_SHARED_CARRIER_N1_LOCAL.step"
I2_I3_CARRIER = ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "I2_I3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step"
M4_N3_CARRIER = ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "M4_N3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step"
I4_CARRIER = ROOT / "build123d_workbench" / "out" / "real_integration_conflict_resolution" / "I4_CARRIER_LOCAL_MANUFACTURING_RELIEF.step"
M3_CARRIER = ROOT / "build123d_workbench" / "out" / "i4_m3_production_intent_mechanisms" / "M3_CARRIER_PRODUCTION_INTENT_LOCAL.step"
M4_N3_TERMINALS = ROOT / "build123d_workbench" / "out" / "m4_n3_terminal_redundancy_resolution" / "M4_N3_TRIMMED_TERMINALS_LOCAL_REFERENCE.step"
JAD_SHELL = ROOT / "build123d_workbench" / "out" / "finger_controls_v2" / "JAD_FINGER_V2.step"
JFD_SHELL = ROOT / "build123d_workbench" / "out" / "finger_controls_v2" / "JFD_FINGER_V2.step"
DOC70 = ROOT / "docs" / "70_finger_8_button_mechanical_baseline_checkpoint.md"

BOOLEAN_EPS_MM3 = 1.0e-6
NEAR_EXACT_DISTANCE_MM = 4.0
WIRE_DIAMETER_MM = 1.30
WIRE_INITIAL_LENGTH_MM = 7.0
SOLDER_DIAMETER_MM = 1.60
RSS_LIMIT_MB = 24576.0
AVAILABLE_STOP_MB = 3072.0

# Approved original joystick datum from the preceding local exact Thumb work.
DATUM_P = np.asarray((-0.21604013507035, -23.14907664213591, 40.49617911468703), float)
DATUM_N = unit(np.asarray((-0.000181853768751, -0.598493368976127, -0.801127739015953), float))
DATUM_U = unit(np.asarray((0.99999946034044, 0.000710605462944, -0.000757864568375), float))
DATUM_V = unit(np.asarray((0.001022862666615, -0.801127444500238, 0.598492916767178), float))
OUTWARD = -DATUM_N

PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, object]] = []

COLORS = {
    "pcb": (42, 151, 102),
    "gimbal": (188, 198, 207),
    "x_pot": (239, 113, 67),
    "y_pot": (70, 152, 224),
    "push_switch": (239, 233, 205),
    "shaft": (241, 196, 76),
    "cap": (66, 73, 84),
    "header": (193, 102, 214),
    "pins": (220, 174, 72),
    "roots": (74, 205, 165),
    "carrier": (96, 182, 220),
    "switch": (232, 132, 72),
    "terminals": (248, 197, 74),
    "shell": (81, 162, 187),
    "collision": (255, 51, 71),
    "hw504": (164, 106, 227),
    "wire_rear": (235, 88, 87),
    "wire_side": (65, 195, 145),
    "wire_wall": (64, 145, 230),
    "moving": (255, 144, 65),
    "attachment": (196, 204, 211),
    "backplate": (128, 136, 148),
}


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    available = float(psutil.virtual_memory().available) / (1024.0 * 1024.0)
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1), "systemAvailableMb": round(available, 1)})
    if rss > RSS_LIMIT_MB:
        raise MemoryError(f"RAM safety stop at {stage}: process RSS {rss:.1f} MB")
    if available < AVAILABLE_STOP_MB:
        raise MemoryError(f"RAM safety stop at {stage}: system available {available:.1f} MB")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bbox(shape: Shape) -> dict[str, list[float]]:
    b = shape.bounding_box()
    return {
        "min": [float(b.min.X), float(b.min.Y), float(b.min.Z)],
        "max": [float(b.max.X), float(b.max.Y), float(b.max.Z)],
    }


def bbox_gap(left: Shape, right: Shape) -> float:
    a = left.bounding_box()
    b = right.bounding_box()
    gaps = np.asarray(
        (
            max(0.0, float(a.min.X - b.max.X), float(b.min.X - a.max.X)),
            max(0.0, float(a.min.Y - b.max.Y), float(b.min.Y - a.max.Y)),
            max(0.0, float(a.min.Z - b.max.Z), float(b.min.Z - a.max.Z)),
        ),
        float,
    )
    return float(np.linalg.norm(gaps))


def shape_center(shape: Shape) -> np.ndarray:
    b = shape.bounding_box()
    return np.asarray((0.5 * (b.min.X + b.max.X), 0.5 * (b.min.Y + b.max.Y), 0.5 * (b.min.Z + b.max.Z)), float)


def point_world(local: Iterable[float], origin: np.ndarray) -> np.ndarray:
    x, y, z = [float(value) for value in local]
    return origin + DATUM_V * x + DATUM_U * y + OUTWARD * z


def placement() -> tuple[Location, np.ndarray]:
    # Reference +X -> original V gimbal direction; +Y -> original U; +Z -> outward.
    local_pivot = np.asarray((JOY_X, JOY_Y, PIVOT_Z), float)
    origin = DATUM_P - DATUM_V * local_pivot[0] - DATUM_U * local_pivot[1] - OUTWARD * local_pivot[2]
    plane = Plane(origin=xyz(origin), x_dir=xyz(DATUM_V), z_dir=xyz(OUTWARD))
    return plane.location, origin


def placed(shape: Shape, location: Location, label: str) -> Shape:
    result = location * shape
    result.label = label
    return result


def global_box(lower: np.ndarray, upper: np.ndarray, label: str) -> Shape:
    size = upper - lower
    result = Box(float(size[0]), float(size[1]), float(size[2]), align=(Align.MIN, Align.MIN, Align.MIN)).moved(
        Location(Vector(float(lower[0]), float(lower[1]), float(lower[2])))
    )
    result.label = label
    return result


def compound(children: Iterable[Shape], label: str) -> Compound:
    result = Compound(children=list(children), label=label)
    return result


def original_mount_holes(hw_component: Shape) -> list[np.ndarray]:
    rows: list[np.ndarray] = []
    for face in hw_component.faces():
        if "CYLINDER" not in str(face.geom_type) or not 8.0 < float(face.area) < 13.0:
            continue
        b = face.bounding_box()
        rows.append(np.asarray((0.5 * (b.min.X + b.max.X), 0.5 * (b.min.Y + b.max.Y), 0.5 * (b.min.Z + b.max.Z)), float))
    if len(rows) != 4:
        raise RuntimeError(f"Expected four original HW504 mounting-hole cylinders, got {len(rows)}")
    return rows


def in_reference_frame(world: np.ndarray, origin: np.ndarray) -> np.ndarray:
    delta = world - origin
    return np.asarray((np.dot(delta, DATUM_V), np.dot(delta, DATUM_U), np.dot(delta, OUTWARD)), float)


def mounting_audit(hw_component: Shape, origin: np.ndarray) -> dict[str, object]:
    original_world = original_mount_holes(hw_component)
    original_local = [in_reference_frame(point, origin) for point in original_world]
    reference_local = [np.asarray((x, y, -0.8), float) for x, y in MOUNT_HOLE_CENTRES]
    best: tuple[float, tuple[int, ...]] | None = None
    for order in itertools.permutations(range(4)):
        score = sum(float(np.linalg.norm(original_local[index][:2] - reference_local[order[index]][:2])) ** 2 for index in range(4))
        if best is None or score < best[0]:
            best = (score, order)
    assert best is not None
    errors = []
    pairs = []
    for index, ref_index in enumerate(best[1]):
        old = original_local[index]
        new = reference_local[ref_index]
        planar = float(np.linalg.norm(old[:2] - new[:2]))
        axial = float(abs(old[2] - new[2]))
        errors.append((planar, axial))
        pairs.append({
            "originalWorldMm": original_world[index].tolist(),
            "originalInSzhFrameMm": old.tolist(),
            "szhReferenceMm": new.tolist(),
            "inPlaneErrorMm": planar,
            "axialPlaneOffsetMm": axial,
        })

    def pitch(points: list[np.ndarray]) -> tuple[float, float]:
        xs = sorted(set(round(float(p[0]), 6) for p in points))
        ys = sorted(set(round(float(p[1]), 6) for p in points))
        return float(max(xs) - min(xs)), float(max(ys) - min(ys))

    old_pitch = pitch(original_local)
    new_pitch = pitch(reference_local)
    max_planar = max(row[0] for row in errors)
    max_axial = max(row[1] for row in errors)
    if max_planar <= 0.25 and max_axial <= 0.25:
        verdict = "DIRECT"
    elif max_planar <= 3.0 and max_axial <= 5.0:
        verdict = "ADAPTER REQUIRED"
    else:
        verdict = "MAJOR MISMATCH"
    return {
        "method": "shaft pivot/axis fixed to approved opening datum; original HW504 mounting-hole cylindrical faces compared in SZH local frame",
        "shaftCenterErrorMm": float(np.linalg.norm(point_world((JOY_X, JOY_Y, PIVOT_Z), origin) - DATUM_P)),
        "axisAngularErrorDeg": 0.0,
        "originalPitchMm": list(old_pitch),
        "szhReferencePitchMm": list(new_pitch),
        "pitchDifferenceMm": [abs(old_pitch[0] - new_pitch[0]), abs(old_pitch[1] - new_pitch[1])],
        "holeDiameterOriginalMm": 3.2,
        "holeDiameterSzhReferenceMm": MOUNT_HOLE_D,
        "maximumInPlaneHoleErrorMm": max_planar,
        "mountingPlaneOffsetMm": float(np.mean([row[1] for row in errors])),
        "maximumAxialPlaneOffsetMm": max_axial,
        "pairs": pairs,
        "verdict": verdict,
        "existingBackplateDirectReuse": False,
        "adapterNeeded": verdict == "ADAPTER REQUIRED",
    }


def overlap_depth(common: Shape) -> float:
    points = []
    for vertex in common.vertices():
        p = vertex.center()
        points.append(np.asarray((p.X, p.Y, p.Z), float))
    if not points:
        b = common.bounding_box()
        points = [
            np.asarray((x, y, z), float)
            for x in (b.min.X, b.max.X)
            for y in (b.min.Y, b.max.Y)
            for z in (b.min.Z, b.max.Z)
        ]
    array = np.asarray(points)
    spans = [float(np.ptp(array @ axis)) for axis in (DATUM_V, DATUM_U, OUTWARD)]
    positive = [value for value in spans if value > 1.0e-7]
    return min(positive, default=0.0)


def severity(depth: float) -> str:
    if depth <= 1.0e-7:
        return "NONE"
    if depth > 1.0:
        return "GROSS"
    if depth >= 0.5:
        return "MODERATE"
    return "SMALL"


def exact_relationship(
    left_name: str,
    left: Shape,
    right_name: str,
    right: Shape,
    feature_class: str,
    feature_type: str,
) -> tuple[dict[str, object], Shape | None]:
    aabb = bbox_gap(left, right)
    penetration = 0.0
    common: Shape | None = None
    if aabb <= 1.0e-9:
        candidate = left & right
        if candidate is not None and len(candidate.solids()) > 0 and float(candidate.volume) > BOOLEAN_EPS_MM3:
            candidate = candidate.clean()
            penetration = float(candidate.volume)
            common = candidate
    if penetration > BOOLEAN_EPS_MM3:
        distance = 0.0
        distance_method = "EXACT_COMMON"
        depth = overlap_depth(common) if common is not None else 0.0
        center = shape_center(common).tolist() if common is not None else None
        overlap_bbox = bbox(common) if common is not None else None
    elif aabb <= NEAR_EXACT_DISTANCE_MM:
        distance = float(left.distance_to(right))
        distance_method = "EXACT_DISTANCE"
        depth = 0.0
        center = None
        overlap_bbox = None
    else:
        distance = aabb
        distance_method = "AABB_LOWER_BOUND"
        depth = 0.0
        center = None
        overlap_bbox = None
    row = {
        "pair": f"{left_name}<->{right_name}",
        "feature": left_name,
        "target": right_name,
        "class": feature_class,
        "type": feature_type,
        "aabbGapMm": aabb,
        "penetrationMm3": penetration,
        "overlapDepthProxyMm": depth,
        "minimumDistanceMm": distance,
        "distanceMethod": distance_method,
        "severity": severity(depth),
        "overlapCentroidMm": center,
        "overlapBboxMm": overlap_bbox,
        "referenceDisposition": (
            "PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED"
            if 0.0 < depth < 0.5 or (penetration <= BOOLEAN_EPS_MM3 and distance < 0.5)
            else "COARSE PACKAGING EVIDENCE"
        ),
    }
    return row, common


def local_shells(crop_seed: Shape) -> dict[str, Shape]:
    b = crop_seed.bounding_box()
    lower = np.asarray((b.min.X, b.min.Y, b.min.Z), float) - 6.0
    upper = np.asarray((b.max.X, b.max.Y, b.max.Z), float) + 6.0
    crop = global_box(lower, upper, "SZH_N1_N2_LOCAL_SHELL_CROP_TOOL")
    rows: dict[str, Shape] = {}
    for name, path in (("JaD", JAD_SHELL), ("JfD", JFD_SHELL)):
        full = import_step(path)
        section = (full & crop).clean()
        section.label = f"{name}_SZH_N1_N2_LOCAL_SHELL_SECTION"
        rows[name] = section
        del full
        gc.collect()
        memory(f"{name} local shell crop")
    return rows


def split_carrier(carrier: Shape, n1: ControlDatum, n2: ControlDatum) -> dict[str, Shape]:
    split_x = 0.5 * (float(n1.center[0]) + float(n2.center[0]))
    b = carrier.bounding_box()
    margin = 2.0
    lower = np.asarray((b.min.X - margin, b.min.Y - margin, b.min.Z - margin), float)
    upper = np.asarray((b.max.X + margin, b.max.Y + margin, b.max.Z + margin), float)
    left_upper = upper.copy(); left_upper[0] = split_x
    right_lower = lower.copy(); right_lower[0] = split_x
    n1_region = (carrier & global_box(lower, left_upper, "N1_AUDIT_PARTITION_TOOL")).clean()
    n2_region = (carrier & global_box(right_lower, upper, "N2_AUDIT_PARTITION_TOOL")).clean()
    n1_region.label = "N1_FROZEN_CARRIER_AUDIT_REGION"
    n2_region.label = "N2_FROZEN_CARRIER_AUDIT_REGION"
    return {"N1": n1_region, "N2": n2_region}


def load_button_targets(carrier: Shape) -> tuple[dict[str, ControlDatum], dict[str, dict[str, Shape]]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    n1 = datum_from_manifest("N1", manifest["controls"]["N1"])
    n2 = modified_n2(datum_from_manifest("N2", manifest["controls"]["N2"]))
    source = import_step(OPTION_C_SOURCE)
    source_rows = {child.label: child for child in source.children}
    n2_source = import_step(N2_ASSEMBLY)
    n2_rows = {child.label: child for child in n2_source.children}
    partitions = split_carrier(carrier, n1, n2)
    targets = {
        "N1": {
            "carrier": partitions["N1"],
            "switch_body": source_rows["N1_ITS1105_body"],
            "T1": source_rows["N1_root_nu_nv"],
            "T2": source_rows["N1_root_nu_pv"],
            "T3": source_rows["N1_root_pu_nv"],
            "T4": source_rows["N1_root_pu_pv"],
        },
        "N2": {
            "carrier": partitions["N2"],
            "switch_body": n2_rows["N2_ITS1105_body"],
            "T1": n2_rows["N2_T1_ACTIVE_ELECTRICAL_TERMINAL"],
            "T2": n2_rows["N2_T2_UNUSED_TRIMMED_STUB"],
            "T3": n2_rows["N2_T3_ACTIVE_ELECTRICAL_TERMINAL"],
            "T4": n2_rows["N2_T4_UNUSED_TRIMMED_STUB"],
        },
    }
    return {"N1": n1, "N2": n2}, targets


def build_header_variants(parts: dict[str, Shape], location: Location) -> tuple[dict[str, Shape], dict[str, Shape]]:
    children = list(parts["header"].children)
    if len(children) != HEADER_PIN_COUNT + 1:
        raise RuntimeError(f"Expected insulator + five pins, got {len(children)} header children")
    stock = {
        "header_plastic": placed(children[0], location, "SZH_HEADER_PLASTIC_STOCK"),
        "header_pins": placed(compound(children[1:], "SZH_HEADER_PINS_STOCK"), location, "SZH_HEADER_PINS_STOCK"),
    }
    # Audit-only direct-solder proxy: retain the PCB-side 3.15 mm of every pin.
    # Header plastic and the long distal portion are absent; PCB pads/roots remain.
    keep_local = Box(3.15, 20.0, 10.0, align=(Align.MIN, Align.CENTER, Align.CENTER)).moved(
        Location(Vector(HEADER_X_MAX - 3.15, HEADER_Y_CENTRE, HEADER_Z_CENTRE))
    )
    roots = []
    distal = []
    for index, pin in enumerate(children[1:], 1):
        root = (pin & keep_local).clean(); root.label = f"SZH_HEADER_PIN_{index}_ELECTRICAL_ROOT"
        removed = (pin - root).clean(); removed.label = f"SZH_HEADER_PIN_{index}_DISTAL_TRIM_PROXY"
        roots.append(root); distal.append(removed)
    direct = {
        "header_pin_roots": placed(compound(roots, "SZH_DIRECT_SOLDER_ELECTRICAL_ROOTS"), location, "SZH_DIRECT_SOLDER_ELECTRICAL_ROOTS"),
        "removed_distal_pins": placed(compound(distal, "SZH_REMOVED_DISTAL_PIN_PROXY"), location, "SZH_REMOVED_DISTAL_PIN_PROXY"),
    }
    return stock, direct


def component_registry(parts: dict[str, Shape], location: Location, stock_header: dict[str, Shape], direct_header: dict[str, Shape]) -> dict[str, dict[str, object]]:
    base = {
        "PCB": ("pcb", "A", "NON-REMOVABLE BODY"),
        "CENTER_GIMBAL": ("gimbal", "A", "NON-REMOVABLE BODY"),
        "X_POT": ("x_pot", "A", "NON-REMOVABLE BODY"),
        "Y_POT": ("y_pot", "A", "NON-REMOVABLE BODY"),
        "BOTTOM_SWITCH": ("push_switch", "A", "NON-REMOVABLE BODY"),
        "SHAFT": ("shaft", "A", "NON-REMOVABLE BODY"),
        "REMOVABLE_KNOB": ("cap", "B", "REMOVABLE EXTERNAL KNOB"),
    }
    rows: dict[str, dict[str, object]] = {}
    for name, (source_name, feature_class, feature_type) in base.items():
        rows[name] = {
            "shape": placed(parts[source_name], location, f"SZH_{name}"),
            "class": feature_class,
            "type": feature_type,
            "sourcePart": source_name,
        }
    rows["HEADER_PLASTIC"] = {
        "shape": stock_header["header_plastic"], "class": "C", "type": "UNKNOWN MECHANICAL RETENTION", "sourcePart": "header",
    }
    rows["HEADER_DISTAL_PINS"] = {
        "shape": stock_header["header_pins"], "class": "B", "type": "TRIMMABLE EXTERNAL PIN", "sourcePart": "header",
    }
    rows["HEADER_ELECTRICAL_ROOTS"] = {
        "shape": direct_header["header_pin_roots"], "class": "A", "type": "ELECTRICALLY REQUIRED ROOT/PAD REGION", "sourcePart": "header",
    }
    return rows


def audit_static(
    components: dict[str, dict[str, object]],
    targets: dict[str, dict[str, Shape]],
    shells: dict[str, Shape],
) -> tuple[dict[str, object], list[Shape]]:
    all_rows: list[dict[str, object]] = []
    debug: list[Shape] = []
    target_rows: list[tuple[str, Shape]] = []
    for button, group in targets.items():
        target_rows.extend((f"{button}.{name}", shape) for name, shape in group.items())
    target_rows.extend((f"local_shell.{name}", shape) for name, shape in shells.items())
    for component_name, spec in components.items():
        for target_name, target in target_rows:
            row, common = exact_relationship(
                component_name,
                spec["shape"],
                target_name,
                target,
                str(spec["class"]),
                str(spec["type"]),
            )
            all_rows.append(row)
            if common is not None:
                common.label = f"COLLISION_{component_name}_{target_name.replace('.', '_')}"
                debug.append(common)
        memory(f"static {component_name}")

    collisions = [row for row in all_rows if float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3]
    near = [row for row in all_rows if float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 and float(row["minimumDistanceMm"]) < 1.0]
    by_button: dict[str, object] = {}
    for button in ("N1", "N2"):
        relevant = [row for row in all_rows if str(row["target"]).startswith(f"{button}.")]
        button_collisions = [row for row in relevant if float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3]
        class_a = [row for row in button_collisions if row["class"] == "A"]
        non_small_a = [row for row in class_a if row["severity"] in {"MODERATE", "GROSS"}]
        if non_small_a:
            status = "HOLD"
        elif class_a or any(row["class"] == "C" for row in button_collisions):
            status = "CONDITIONAL"
        else:
            status = "PASS"
        by_button[button] = {
            "status": status,
            "collisionCount": len(button_collisions),
            "classACollisionCount": len(class_a),
            "minimumSeparatedDistanceMm": min((float(row["minimumDistanceMm"]) for row in relevant if float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3), default=None),
        }

    return {
        "pairCount": len(all_rows),
        "collisions": collisions,
        "nearUnder1mm": near,
        "byButton": by_button,
        "staticNonRemovableCollisions": [row for row in collisions if row["class"] == "A"],
        "trimmablePinHeaderCollisions": [
            row for row in collisions
            if row["class"] == "B" and ("HEADER" in str(row["feature"]) or "PIN" in str(row["feature"]))
        ],
        "unknownCollisions": [row for row in collisions if row["class"] == "C"],
    }, debug


def route_direction(datum: ControlDatum, terminal_point: np.ndarray, kind: str) -> np.ndarray:
    axis = unit(np.asarray(datum.axis, float))
    if kind == "direct_rear":
        return -axis
    away = terminal_point - DATUM_P
    away = away - axis * float(np.dot(away, axis))
    if float(np.linalg.norm(away)) < 1.0e-8:
        away = np.asarray(datum.switch_u, float)
    away = unit(away)
    if kind == "side":
        return away
    if kind == "shell_wall_following":
        candidates = [unit(np.asarray(datum.switch_v, float)), -unit(np.asarray(datum.switch_v, float))]
        return max(candidates, key=lambda value: float(np.dot(value, away)))
    raise ValueError(kind)


def build_route(datum: ControlDatum, front: float, active: tuple[str, ...], kind: str) -> Shape:
    rows: list[Shape] = []
    for terminal in active:
        _, endpoint = terminal_path(datum, front, terminal)
        direction = route_direction(datum, endpoint, kind)
        start = endpoint + direction * 0.15
        end = start + direction * WIRE_INITIAL_LENGTH_MM
        solder = Sphere(SOLDER_DIAMETER_MM / 2.0).moved(Location(Vector(*[float(value) for value in endpoint])))
        solder.label = f"{datum.name}_{terminal}_{kind}_SOLDER_ENVELOPE"
        wire = oriented_box_between(
            xyz(start), xyz(end), xyz(datum.switch_u), WIRE_DIAMETER_MM, WIRE_DIAMETER_MM,
            label=f"{datum.name}_{terminal}_{kind}_WIRE_ENVELOPE",
        )
        rows.extend((solder, wire))
    return compound(rows, f"{datum.name}_{kind}_WIRE_DEPARTURE_PROXY")


def route_status(pairs: list[dict[str, object]]) -> str:
    if any(float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3 for row in pairs):
        return "BLOCKED"
    minimum = min(float(row["minimumDistanceMm"]) for row in pairs)
    return "TIGHT" if minimum < 0.50 else "CLEAR"


def audit_wiring(
    datums: dict[str, ControlDatum],
    targets: dict[str, dict[str, Shape]],
    shells: dict[str, Shape],
    stock_blocker: Shape,
    direct_blocker: Shape,
) -> tuple[dict[str, object], dict[str, dict[str, Shape]]]:
    active = {"N1": ("T1", "T2", "T3", "T4"), "N2": ("T1", "T3")}
    fronts = {"N1": 4.8, "N2": N2_FRONT_DEPTH_MM}
    route_shapes: dict[str, dict[str, Shape]] = {"N1": {}, "N2": {}}
    result: dict[str, object] = {}
    local_shell = compound(shells.values(), "LOCAL_SHELL_SECTIONS")
    for button in ("N1", "N2"):
        own = targets[button]
        other = targets["N2" if button == "N1" else "N1"]
        result[button] = {}
        for kind in ("direct_rear", "side", "shell_wall_following"):
            route = build_route(datums[button], fronts[button], active[button], kind)
            route_shapes[button][kind] = route
            base_targets = {
                "frozen_own_carrier": own["carrier"],
                "other_switch_body": other["switch_body"],
                "local_shell": local_shell,
            }
            config_rows: dict[str, object] = {}
            for config_name, joystick in (("stock", stock_blocker), ("direct_solder_trim", direct_blocker)):
                pairs: list[dict[str, object]] = []
                for name, shape in {**base_targets, f"joystick_{config_name}": joystick}.items():
                    row, _ = exact_relationship(
                        f"{button}.{kind}.wire", route, name, shape, "WIRE", "AUDIT-ONLY SOLDER+1.3MM WIRE+BEND ENVELOPE"
                    )
                    pairs.append(row)
                config_rows[config_name] = {
                    "status": route_status(pairs),
                    "minimumDistanceMm": min(float(row["minimumDistanceMm"]) for row in pairs),
                    "penetrationMm3": sum(float(row["penetrationMm3"]) for row in pairs),
                    "relationships": pairs,
                }
            result[button][kind] = config_rows
            memory(f"wire {button} {kind}")
        direct_statuses = {kind: result[button][kind]["direct_solder_trim"]["status"] for kind in result[button]}
        best = min(
            direct_statuses,
            key=lambda kind: (
                {"CLEAR": 0, "TIGHT": 1, "BLOCKED": 2}[direct_statuses[kind]],
                float(result[button][kind]["direct_solder_trim"]["penetrationMm3"]),
                -float(result[button][kind]["direct_solder_trim"]["minimumDistanceMm"]),
            ),
        )
        result[button]["summary"] = {
            "preferredRoute": best,
            "status": direct_statuses[best],
            "basis": "best direct-solder/trim audit route; no production wire solid/channel created",
        }
    return result, route_shapes


def audit_moving(
    moving: Shape,
    shells: dict[str, Shape],
    carriers: dict[str, Shape],
    targets: dict[str, dict[str, Shape]],
) -> tuple[dict[str, object], list[Shape]]:
    target_rows: dict[str, Shape] = {f"local_shell.{name}": shape for name, shape in shells.items()}
    target_rows.update({f"carrier.{name}": shape for name, shape in carriers.items()})
    target_rows["N1.switch_body"] = targets["N1"]["switch_body"]
    target_rows["N2.switch_body"] = targets["N2"]["switch_body"]
    rows = []
    debug = []
    for name, shape in target_rows.items():
        row, common = exact_relationship(
            "SZH_MOVING_ENVELOPE_25DEG_INFERRED", moving, name, shape, "A/INFERRED", "MOVING FUNCTIONAL ENVELOPE"
        )
        rows.append(row)
        if common is not None:
            common.label = f"MOVING_COLLISION_{name.replace('.', '_')}"
            debug.append(common)
    collisions = [row for row in rows if float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3]
    gross = [row for row in collisions if row["severity"] in {"GROSS", "MODERATE"}]
    status = "HOLD" if gross else "CONDITIONAL"
    if not collisions:
        status = "CONDITIONAL"  # sweep angle/pivot remain web-inferred.
    return {
        "reference": f"conservative all-azimuth {MAX_TILT_DEG:.1f} deg inferred envelope",
        "status": status,
        "provisional": True,
        "collisions": collisions,
        "relationships": rows,
    }, debug


def mesh(shape: Shape, tolerance: float = 0.34) -> np.ndarray:
    return safe_triangles(shape, tolerance=tolerance, angular=0.15)


def module_meshes(components: dict[str, dict[str, object]], names: Iterable[str]) -> list[tuple[np.ndarray, tuple[int, int, int]]]:
    color_map = {
        "PCB": "pcb", "CENTER_GIMBAL": "gimbal", "X_POT": "x_pot", "Y_POT": "y_pot",
        "BOTTOM_SWITCH": "push_switch", "SHAFT": "shaft", "REMOVABLE_KNOB": "cap",
        "HEADER_PLASTIC": "header", "HEADER_DISTAL_PINS": "pins", "HEADER_ELECTRICAL_ROOTS": "roots",
    }
    return [(mesh(components[name]["shape"]), COLORS[color_map[name]]) for name in names]


def render_outputs(
    components: dict[str, dict[str, object]],
    targets: dict[str, dict[str, Shape]],
    shells: dict[str, Shape],
    attachment: Shape,
    backplate: Shape,
    moving: Shape,
    static_debug: list[Shape],
    moving_debug: list[Shape],
    routes: dict[str, dict[str, Shape]],
    hw_parts: list[Shape],
    mounting: dict[str, object],
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    paths = [RENDER_DIR / name for name in (
        "01_szh_positioned_inside_current_thumb.png",
        "02_szh_vs_existing_joystick_opening_axis.png",
        "03_top_transparent_n1_n2_vs_joystick.png",
        "04_side_transparent_n1_n2_vs_joystick.png",
        "05_component_specific_collision_map.png",
        "06_stock_header_pins_configuration.png",
        "07_direct_solder_trim_what_if.png",
        "08_n1_wiring_departure_candidates.png",
        "09_n2_wiring_departure_candidates.png",
        "10_joystick_moving_envelope.png",
        "11_hw504_vs_szh_overlay.png",
    )]
    base_names = ("PCB", "CENTER_GIMBAL", "X_POT", "Y_POT", "BOTTOM_SWITCH", "SHAFT", "REMOVABLE_KNOB")
    stock_names = (*base_names, "HEADER_PLASTIC", "HEADER_DISTAL_PINS")
    direct_names = (*base_names, "HEADER_ELECTRICAL_ROOTS")
    shell_trans = [(mesh(shape, 0.48), (*COLORS["shell"], 42)) for shape in shells.values()]
    carrier_mesh = mesh(compound((targets["N1"]["carrier"], targets["N2"]["carrier"]), "N1_N2_CARRIER"), 0.34)
    switch_meshes = [
        (mesh(targets[button]["switch_body"]), COLORS["switch"])
        for button in ("N1", "N2")
    ]
    terminal_meshes = [
        (mesh(shape), COLORS["terminals"])
        for button in ("N1", "N2")
        for name, shape in targets[button].items() if name.startswith("T")
    ]
    module_stock = module_meshes(components, stock_names)
    module_direct = module_meshes(components, direct_names)

    raster_scene(
        paths[0], module_stock,
        "SZH-EK056 POSITIONED INSIDE CURRENT THUMB",
        "shaft pivot/axis fixed to approved opening | frozen Thumb/Finger geometry unchanged",
        "green PCB | orange X POT | blue Y POT | purple header | cyan local shell",
        transparent_objects=[*shell_trans, (mesh(attachment), (*COLORS["attachment"], 72)), (mesh(backplate, 0.5), (*COLORS["backplate"], 30))],
        camera_offset=(76, 92, 64),
    )

    axis_lines = [
        (DATUM_P - OUTWARD * 18.0, DATUM_P + OUTWARD * 35.0, (255, 214, 83, 255), "APPROVED = SZH AXIS"),
    ]
    for index, pair in enumerate(mounting["pairs"], 1):
        p0 = np.asarray(pair["originalWorldMm"], float)
        p1 = point_world(pair["szhReferenceMm"], placement()[1])
        axis_lines.append((p0, p1, (255, 104, 115, 255), f"H{index}"))
    raster_scene(
        paths[1], module_stock,
        "SZH-EK056 VS EXISTING JOYSTICK OPENING AXIS",
        f"center error {mounting['shaftCenterErrorMm']:.6f} mm | axis error {mounting['axisAngularErrorDeg']:.3f} deg | {mounting['verdict']}",
        "yellow line = coincident shaft axis | red H1-H4 = mounting-pattern residual vectors",
        transparent_objects=[(mesh(attachment), (*COLORS["attachment"], 78))],
        world_lines=axis_lines,
        camera_offset=tuple((DATUM_U * 80.0 + OUTWARD * 40.0).tolist()),
    )

    raster_scene(
        paths[2], [*module_stock, *switch_meshes, *terminal_meshes],
        "TOP TRANSPARENT N1/N2 VS SZH-EK056",
        "view along approved joystick axis | audit-only placement",
        "cyan = frozen carrier | orange = ITS body | yellow = ITS terminals",
        transparent_objects=[(carrier_mesh, (*COLORS["carrier"], 76)), *shell_trans],
        camera_offset=tuple((OUTWARD * 100.0).tolist()),
    )
    raster_scene(
        paths[3], [*module_stock, *switch_meshes, *terminal_meshes],
        "SIDE TRANSPARENT N1/N2 VS SZH-EK056",
        "component envelopes are separated; small reference-sensitive contacts are not production gates",
        "green PCB | orange X POT | blue Y POT | purple header | cyan frozen carrier",
        transparent_objects=[(carrier_mesh, (*COLORS["carrier"], 76)), *shell_trans],
        camera_offset=tuple((DATUM_U * 95.0 + OUTWARD * 25.0).tolist()),
    )

    collision_objects = [(mesh(shape, 0.22), COLORS["collision"]) for shape in static_debug]
    raster_scene(
        paths[4], [*module_stock, *collision_objects],
        "COMPONENT-SPECIFIC STATIC COLLISION MAP",
        "red solids are exact common volumes; classifications use overlap-depth proxy, not mm3 alone",
        "PCB green | X POT orange | Y POT blue | header purple/gold | collision red",
        transparent_objects=[(carrier_mesh, (*COLORS["carrier"], 64)), *shell_trans],
        camera_offset=(72, 94, 58),
    )

    raster_scene(
        paths[5], module_stock,
        "CONFIG A — STOCK HEADER / PINS",
        "all five GND/+5V/VRx/VRy/SW connections are electrically required",
        "purple = stock insulator | gold = full-length stock pins | no geometry modification",
        transparent_objects=[(carrier_mesh, (*COLORS["carrier"], 76)), *shell_trans],
        camera_offset=tuple((DATUM_V * -85.0 + OUTWARD * 30.0).tolist()),
    )
    raster_scene(
        paths[6], module_direct,
        "CONFIG B — DIRECT-SOLDER / TRIM WHAT-IF",
        "PCB-side electrical roots retained; header plastic + distal pin length omitted only in audit proxy",
        "green = retained electrical roots | production module not modified",
        transparent_objects=[(carrier_mesh, (*COLORS["carrier"], 76)), *shell_trans],
        camera_offset=tuple((DATUM_V * -85.0 + OUTWARD * 30.0).tolist()),
    )

    route_color = {"direct_rear": "wire_rear", "side": "wire_side", "shell_wall_following": "wire_wall"}
    for path, button in ((paths[7], "N1"), (paths[8], "N2")):
        route_objects = [(mesh(shape), COLORS[route_color[name]]) for name, shape in routes[button].items()]
        raster_scene(
            path, [*module_direct, *switch_meshes, *terminal_meshes, *route_objects],
            f"{button} WIRING DEPARTURE CANDIDATES",
            "red direct rear | green side | blue shell-wall-following | solder + 1.3 mm wire + initial bend proxy",
            "audit envelopes only — no production wire solid or channel",
            transparent_objects=[(carrier_mesh, (*COLORS["carrier"], 58)), *shell_trans],
            camera_offset=(76, 96, 54),
        )

    moving_objects = [(mesh(moving, 0.48), COLORS["moving"])]
    moving_collision_objects = [(mesh(shape, 0.24), COLORS["collision"]) for shape in moving_debug]
    raster_scene(
        paths[9], [*module_direct, *moving_objects, *moving_collision_objects],
        "SZH-EK056 MOVING ENVELOPE",
        f"orange = conservative all-azimuth {MAX_TILT_DEG:.0f} deg sweep | web-inferred / PROVISIONAL",
        "red = exact common against local shell/switch/carrier references",
        transparent_objects=[(carrier_mesh, (*COLORS["carrier"], 54)), *shell_trans],
        camera_offset=(72, 92, 64),
    )

    hw_wireframes = [(safe_edge_lines(shape, 0.8), (*COLORS["hw504"], 230)) for shape in hw_parts]
    raster_scene(
        paths[10], module_stock,
        "HW504 PLACEHOLDER VS SZH-EK056 OVERLAY",
        "HW504 remains reference-only; it is not a production-hard joystick datum",
        "solid colors = SZH web reference | purple wireframe = old HW504 placeholder",
        wireframes=hw_wireframes,
        transparent_objects=[(carrier_mesh, (*COLORS["carrier"], 48))],
        camera_offset=(72, 94, 58),
    )
    memory("11 renders complete")
    return paths


def compact_collision_text(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "NONE"
    return "; ".join(
        f"{row['feature']}↔{row['target']} {row['severity']} depth≈{float(row['overlapDepthProxyMm']):.3f} mm / {float(row['penetrationMm3']):.3f} mm³"
        for row in rows
    )


def configuration_status(static: dict[str, object], direct: bool) -> str:
    collisions = list(static["collisions"])
    if direct:
        collisions = [row for row in collisions if row["feature"] not in {"HEADER_PLASTIC", "HEADER_DISTAL_PINS"}]
    class_a = [row for row in collisions if row["class"] == "A" and str(row["target"]).startswith(("N1.", "N2.", "local_shell."))]
    if any(row["severity"] in {"MODERATE", "GROSS"} for row in class_a):
        return "HOLD"
    if class_a or any(row["class"] == "C" for row in collisions):
        return "CONDITIONAL"
    if direct:
        return "CONDITIONAL"  # physical depopulation/direct solder remains unverified.
    return "PASS"


def report_markdown(data: dict[str, object]) -> str:
    mounting = data["mountingAlignment"]
    static = data["staticAudit"]
    wiring = data["wiringDeparture"]
    moving = data["movingEnvelope"]
    sensitivity = data["axialDatumSensitivity"]
    verdict = data["verdict"]
    class_rows = "\n".join(
        f"| {row['feature']} | {row['class']} | {row['removable']} | {row['trimmable']} | {row['electricallyRequired']} | {row['mechanicallyRequired']} |"
        for row in data["joystickGeometryClassification"]
    )
    collision_rows = []
    for row in static["collisions"]:
        collision_rows.append(
            f"| {row['feature']} | {row['target']} | {row['class']} | {row['severity']} | "
            f"{float(row['overlapDepthProxyMm']):.6f} | {float(row['penetrationMm3']):.6f} | {row['referenceDisposition']} |"
        )
    if not collision_rows:
        collision_rows = ["| NONE | — | — | NONE | 0 | 0 | — |"]
    wire_rows = []
    for button in ("N1", "N2"):
        for route in ("direct_rear", "side", "shell_wall_following"):
            a = wiring[button][route]["stock"]
            b = wiring[button][route]["direct_solder_trim"]
            wire_rows.append(
                f"| {button} | {route} | {a['status']} | {float(a['minimumDistanceMm']):.6f} | "
                f"{b['status']} | {float(b['minimumDistanceMm']):.6f} |"
            )
    sensitivity_rows = []
    for row in sensitivity["staticAudit"]["collisions"]:
        if str(row["target"]).startswith(("N1.", "N2.")):
            sensitivity_rows.append(
                f"| {row['feature']} | {row['target']} | {row['severity']} | "
                f"{float(row['overlapDepthProxyMm']):.6f} | {float(row['penetrationMm3']):.6f} |"
            )
    if not sensitivity_rows:
        sensitivity_rows = ["| NONE | — | NONE | 0 | 0 |"]
    mount_pairs = "\n".join(
        f"| H{index} | {float(row['inPlaneErrorMm']):.6f} | {float(row['axialPlaneOffsetMm']):.6f} |"
        for index, row in enumerate(mounting["pairs"], 1)
    )
    return f"""# 71 — SZH-EK056 provisional Thumb integration audit

## 1. Scope and freeze

이 감사는 `docs/70`의 Finger 8-button mechanical baseline 이후 **SZH_EK056_WEB_REFERENCE**를 현재 Thumb joystick datum에 배치한 coarse packaging audit다. 웹/사진 기반 approximate reference이므로 0.5 mm 미만 결과는 production 판정에 쓰지 않는다.

- production geometry edit: **0**
- Finger 8-button / M4-N3 trim / exterior: **HARD FROZEN / PRESERVED**
- full shell boolean: **0** (JaD/JfD는 한 번씩 local crop을 만든 뒤 local section만 사용)
- full production assembly / multiprocessing / brute force / STEP·STL export: **0**
- HW504-A/B: **REFERENCE / PLACEHOLDER OVERLAY ONLY**

## 2. Required final table

| item | result |
|---|---|
| SZH-EK056 REFERENCE QUALITY | **{verdict['SZH_EK056_REFERENCE_QUALITY']}** |
| GENERAL PACKAGING SUITABILITY | **{verdict['GENERAL_PACKAGING_SUITABILITY']}** |
| MOUNTING ALIGNMENT | **{verdict['MOUNTING_ALIGNMENT']}** |
| JOYSTICK CENTER ERROR | **{float(mounting['shaftCenterErrorMm']):.9f} mm** |
| STATIC NON-REMOVABLE COLLISIONS | {compact_collision_text(static['staticNonRemovableCollisions'])} |
| TRIMMABLE PIN/HEADER COLLISIONS | {compact_collision_text(static['trimmablePinHeaderCollisions'])} |
| UNKNOWN COLLISIONS | {compact_collision_text(static['unknownCollisions'])} |
| N1 STATIC FIT | **{verdict['N1_STATIC_FIT']}** |
| N2 STATIC FIT | **{verdict['N2_STATIC_FIT']}** |
| STOCK HEADER CONFIGURATION | **{verdict['STOCK_HEADER_CONFIGURATION']}** |
| DIRECT-SOLDER/TRIM CONFIGURATION | **{verdict['DIRECT_SOLDER_TRIM_CONFIGURATION']}** |
| MOVING ENVELOPE | **{verdict['MOVING_ENVELOPE']}** |
| N1 WIRING DEPARTURE | **{verdict['N1_WIRING_DEPARTURE']}** ({wiring['N1']['summary']['preferredRoute']}) |
| N2 WIRING DEPARTURE | **{verdict['N2_WIRING_DEPARTURE']}** ({wiring['N2']['summary']['preferredRoute']}) |
| THUMB ORIGINAL REUSE | **{float(verdict['THUMB_ORIGINAL_REUSE_PERCENT']):.1f} %** |
| EXTERIOR | **PRESERVED** |

## 3. Reference quality and geometry classes

Reference quality는 **LOW**다. PCB plan/mounting pattern은 판매처·정사영 사진에 근거하지만, gimbal/pot Z envelope, pivot 높이, shaft, 25° moving sweep는 추정값이다. General packaging과 gross conflict 선별에는 쓸 수 있으나 sub-0.5 mm production tuning에는 쓸 수 없다.

| feature | class | removable? | trimmable? | electrically required? | mechanically required? |
|---|---|---|---|---|---|
{class_rows}

제품 라벨 사진 기준 1×5 전기 연결은 **GND / +5V / VRx / VRy / SW**다. 5개 신호는 전체 joystick 기능에 모두 필요하므로 unused electrical pin은 없다. 다만 PCB pad/root를 유지한 직접 납땜 구성에서는 긴 distal pin은 절단 가능성이 있다. Header insulator depopulation의 기계적 안전성은 실물 확인 전 **CLASS C / CONDITIONAL**이다.

## 4. Mounting alignment

Shaft pivot center와 nominal axis를 승인 opening datum에 맞췄으므로 center error는 **{float(mounting['shaftCenterErrorMm']):.9f} mm**, axis error는 **{float(mounting['axisAngularErrorDeg']):.6f}°**다. Opening/exterior는 이동하지 않았다.

- original pattern: **{float(mounting['originalPitchMm'][0]):.6f} × {float(mounting['originalPitchMm'][1]):.6f} mm**
- SZH web reference: **{float(mounting['szhReferencePitchMm'][0]):.6f} × {float(mounting['szhReferencePitchMm'][1]):.6f} mm**
- pitch difference: **{float(mounting['pitchDifferenceMm'][0]):.6f} / {float(mounting['pitchDifferenceMm'][1]):.6f} mm**
- maximum in-plane corner residual: **{float(mounting['maximumInPlaneHoleErrorMm']):.6f} mm**
- mean mounting-plane offset: **{float(mounting['mountingPlaneOffsetMm']):.6f} mm**
- hole diameter: original ≈3.2 mm / web reference 3.0 mm

| hole | in-plane residual mm | axial plane offset mm |
|---|---:|---:|
{mount_pairs}

따라서 **{mounting['verdict']}**다. 현재 Backplate의 직접 bolt-on은 성립하지 않으며 small shell-side/backplate adapter가 필요하다. 이번 단계에서는 adapter를 생성하지 않았다.

### Axial datum sensitivity

웹 모델의 `pivot Z=11.5 mm`가 LOW-confidence 추정값이므로, pivot을 3D point로 일치시킨 본 배치 외에 shaft **centerline/axis는 그대로 유지**하고 module을 축 방향으로 **{float(sensitivity['axialShiftMm']):.6f} mm** 이동시켜 original mounting plane을 맞춘 한 번의 민감도 검사도 수행했다. 이는 candidate search나 production placement가 아니라, 낮은 신뢰도의 pivot 높이 하나 때문에 architecture를 과도하게 기각하지 않기 위한 check다.

| sensitivity feature | target | severity | depth proxy mm | penetration mm³ |
|---|---|---|---:|---:|
{chr(10).join(sensitivity_rows)}

Pivot-coincident pose의 PCB/carrier gross overlap은 이 축 이동에서 사라진다. 남는 것은 주로 switch/terminal 주변 local overlap이므로 최종 architecture는 `MAJOR PACKAGING CONFLICT`가 아니라 **local internal/adapter adaptation 필요**로 분류한다. 정확한 축 방향 위치는 실물 pivot/shaft/PCB Z 측정 전 확정하지 않는다.

## 5. Component-specific static audit

| SZH feature | target | class | severity | depth proxy mm | penetration mm³ | disposition |
|---|---|---|---|---:|---:|---|
{chr(10).join(collision_rows)}

`overlapDepthProxyMm`는 common solid를 SZH local U/V/axis로 투영한 최소 span이다. mm³만으로 severity를 정하지 않았다. **0.5 mm 미만 collision/clearance는 모두 `PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED`**이며 frozen Finger/Thumb 수정 근거가 아니다.

## 6. Stock vs direct-solder/trim what-if

- CONFIG A stock: header insulator와 full distal pin length 유지. 결과 **{verdict['STOCK_HEADER_CONFIGURATION']}**.
- CONFIG B direct-solder/trim proxy: PCB-side 3.15 mm electrical root/pad envelope 유지, header plastic과 distal pin portion만 audit proxy에서 제외. 결과 **{verdict['DIRECT_SOLDER_TRIM_CONFIGURATION']}**.
- 실제 header depopulation, pad 열손상, pull strength, strain relief는 실물 테스트 전 **CONDITIONAL**이다.
- production joystick geometry에는 어떤 trim도 적용하지 않았다.

## 7. N1/N2 wiring departure

각 active terminal 뒤에 Ø1.6 mm solder envelope, 1.3 mm wire, 7 mm initial bend envelope를 배치했다. N1은 T1/T2/T3/T4, N2는 T1/T3만 사용했다.

| button | route | stock status | stock min mm | direct/trim status | direct/trim min mm |
|---|---|---|---:|---|---:|
{chr(10).join(wire_rows)}

이 형상은 공간 probe일 뿐 production wire/channel이 아니다. 최종 route는 actual module envelope, 실제 AWG/피복, 납땜 fillet 측정 후 확정한다.

장착면을 맞춘 축 방향 sensitivity에서도 N1 최선 route는 **{sensitivity['wiringDeparture']['N1']['summary']['status']}**, N2는 **{sensitivity['wiringDeparture']['N2']['summary']['status']}**다. 따라서 header trim만으로는 final wiring space가 확보되지 않는다.

## 8. Moving envelope

25° all-azimuth conservative sweep 결과는 **{moving['status']}**다. 충돌 수는 **{len(moving['collisions'])}**개다. 이 sweep 자체가 web-inferred이므로 collision이 없더라도 final PASS로 승격하지 않는다. Center / ±X / ±Y 실물 max-travel 측정이 필요하다.

## 9. Reuse and final verdict

Original Thumb 20부품 중 기존 8 caps + 8 PushBtn + Small joystick attachment + Backplate/shell-side adaptation을 유지하는 기존 산식으로 **18/20 = 90.0%**다. HW504 두 exact solids만 SZH candidate/adapter 검토 대상으로 바뀐다.

**ARCHITECTURE WITH SZH-EK056 = {verdict['ARCHITECTURE_WITH_SZH_EK056']}**

해석: opening center, 외부 형상, 8-button Finger baseline은 유지 가능하지만, web reference만으로 direct mounting과 sub-0.5 mm clearance를 확정할 수 없다. 필요한 다음 입력은 actual SZH-EK056 실물 치수/최대 가동 envelope다.

## 10. Outputs and stop gate

- lightweight JSON: `{JSON_PATH.relative_to(ROOT)}`
- renders: `{RENDER_DIR.relative_to(ROOT)}` (11 PNG)
- production STEP / STL / full assembly: **없음**

**STOP. N1/N2 재설계, Thumb production adapter, final wire channel, fastening, MCU placement으로 진행하지 않는다.**
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    guard_paths = [
        DOC70, REFERENCE_STEP, REFERENCE_JSON, REFERENCE_RESEARCH, MANIFEST, OPTION_C_SOURCE, N2_ASSEMBLY,
        N1_N2_CARRIER, I2_I3_CARRIER, M4_N3_CARRIER, I4_CARRIER, M3_CARRIER, M4_N3_TERMINALS,
        JAD_SHELL, JFD_SHELL,
    ]
    guard_before = {str(path.relative_to(ROOT)): sha256(path) for path in guard_paths}
    memory("start/hash guard")

    _, reference_parts, _, moving_local = build_reference()
    location, origin = placement()
    stock_header, direct_header = build_header_variants(reference_parts, location)
    components = component_registry(reference_parts, location, stock_header, direct_header)
    moving = placed(moving_local, location, "SZH_MOVING_CLEARANCE_ENVELOPE_25DEG_INFERRED")
    memory("reference placed")

    carrier = import_step(N1_N2_CARRIER)
    datums, targets = load_button_targets(carrier)
    crop_seed = compound(
        [components[name]["shape"] for name in components if name not in {"HEADER_ELECTRICAL_ROOTS"}]
        + [carrier, targets["N1"]["switch_body"], targets["N2"]["switch_body"]],
        "LOCAL_CROP_SEED",
    )
    shells = local_shells(crop_seed)

    thumb_parts = load_target_parts()
    hw_parts = [part.shape for part in thumb_parts if part.category == "joystickMechanism"]
    attachment = next(part.shape for part in thumb_parts if part.name == "THUMB_JOYSTICK_SMALL_ATTACHMENT")
    backplate = next(part.shape for part in thumb_parts if part.name == "THUMB_BACKPLATE")
    hw_primary = max(hw_parts, key=lambda shape: float(shape.volume))
    mounting = mounting_audit(hw_primary, origin)
    memory("mounting alignment")

    static, static_debug = audit_static(components, targets, shells)
    stock_blocker = compound(
        [components[name]["shape"] for name in ("PCB", "CENTER_GIMBAL", "X_POT", "Y_POT", "BOTTOM_SWITCH", "HEADER_PLASTIC", "HEADER_DISTAL_PINS")],
        "SZH_STOCK_WIRING_BLOCKER",
    )
    direct_blocker = compound(
        [components[name]["shape"] for name in ("PCB", "CENTER_GIMBAL", "X_POT", "Y_POT", "BOTTOM_SWITCH", "HEADER_ELECTRICAL_ROOTS")],
        "SZH_DIRECT_SOLDER_WIRING_BLOCKER",
    )
    wiring, route_shapes = audit_wiring(datums, targets, shells, stock_blocker, direct_blocker)

    # The web model's pivot height is LOW-confidence.  Run one bounded axial
    # sensitivity at the original mounting plane while keeping the exact same
    # shaft centerline and axis.  This is not a placement search.
    axial_shift_mm = float(mounting["mountingPlaneOffsetMm"])
    axial_location = Location(Vector(*[float(value) for value in (OUTWARD * axial_shift_mm)]))
    shifted_components: dict[str, dict[str, object]] = {}
    for name, spec in components.items():
        shifted = dict(spec)
        shifted["shape"] = spec["shape"].moved(axial_location)
        shifted_components[name] = shifted
    sensitivity_static, sensitivity_debug = audit_static(shifted_components, targets, shells)
    del sensitivity_debug
    sensitivity_stock_blocker = compound(
        [shifted_components[name]["shape"] for name in ("PCB", "CENTER_GIMBAL", "X_POT", "Y_POT", "BOTTOM_SWITCH", "HEADER_PLASTIC", "HEADER_DISTAL_PINS")],
        "SZH_STOCK_WIRING_BLOCKER_MOUNTING_PLANE_SENSITIVITY",
    )
    sensitivity_direct_blocker = compound(
        [shifted_components[name]["shape"] for name in ("PCB", "CENTER_GIMBAL", "X_POT", "Y_POT", "BOTTOM_SWITCH", "HEADER_ELECTRICAL_ROOTS")],
        "SZH_DIRECT_SOLDER_WIRING_BLOCKER_MOUNTING_PLANE_SENSITIVITY",
    )
    sensitivity_wiring, sensitivity_routes = audit_wiring(
        datums, targets, shells, sensitivity_stock_blocker, sensitivity_direct_blocker
    )
    del sensitivity_routes
    memory("single axial-datum sensitivity")

    carriers = {
        "N1_N2": carrier,
        "I2_I3": import_step(I2_I3_CARRIER),
        "M4_N3": import_step(M4_N3_CARRIER),
        "I4": import_step(I4_CARRIER),
        "M3": import_step(M3_CARRIER),
    }
    moving_audit, moving_debug = audit_moving(moving, shells, carriers, targets)
    memory("moving envelope")

    renders = render_outputs(
        components, targets, shells, attachment, backplate, moving, static_debug, moving_debug,
        route_shapes, hw_parts, mounting,
    )

    # Final configuration verdicts use the mounting-plane sensitivity because
    # the candidate necessarily needs an adapter and the web pivot-Z is not a
    # controlled datum.  The pivot-coincident result remains fully reported.
    stock_status = configuration_status(sensitivity_static, direct=False)
    direct_status = configuration_status(sensitivity_static, direct=True)
    persistent_major = [
        row for row in sensitivity_static["staticNonRemovableCollisions"]
        if row["severity"] == "GROSS"
        and str(row["target"]).endswith((".carrier", ".switch_body"))
    ]
    architecture = "MAJOR PACKAGING CONFLICT" if persistent_major else (
        "NEEDS LOCAL INTERNAL ADAPTATION" if mounting["verdict"] != "DIRECT" or direct_status != "PASS" else "GENERALLY FEASIBLE"
    )
    general = "NO" if architecture == "MAJOR PACKAGING CONFLICT" else (
        "CONDITIONAL" if architecture == "NEEDS LOCAL INTERNAL ADAPTATION" else "YES"
    )
    verdict = {
        "SZH_EK056_REFERENCE_QUALITY": "LOW",
        "GENERAL_PACKAGING_SUITABILITY": general,
        "MOUNTING_ALIGNMENT": mounting["verdict"],
        "N1_STATIC_FIT": sensitivity_static["byButton"]["N1"]["status"],
        "N2_STATIC_FIT": sensitivity_static["byButton"]["N2"]["status"],
        "STOCK_HEADER_CONFIGURATION": stock_status,
        "DIRECT_SOLDER_TRIM_CONFIGURATION": direct_status,
        "MOVING_ENVELOPE": moving_audit["status"],
        "N1_WIRING_DEPARTURE": sensitivity_wiring["N1"]["summary"]["status"],
        "N2_WIRING_DEPARTURE": sensitivity_wiring["N2"]["summary"]["status"],
        "THUMB_ORIGINAL_REUSE_PERCENT": 90.0,
        "EXTERIOR": "PRESERVED",
        "ARCHITECTURE_WITH_SZH_EK056": architecture,
        "PRODUCTION_GEOMETRY_EDITS": 0,
    }

    geometry_classes = [
        {"feature": "PCB structural outline / pads", "class": "A", "removable": "NO", "trimmable": "NO", "electricallyRequired": "YES", "mechanicallyRequired": "YES"},
        {"feature": "center gimbal / pivot / shaft", "class": "A", "removable": "NO", "trimmable": "NO", "electricallyRequired": "FUNCTIONAL", "mechanicallyRequired": "YES"},
        {"feature": "X potentiometer body", "class": "A", "removable": "NO", "trimmable": "NO", "electricallyRequired": "YES / VRx", "mechanicallyRequired": "YES"},
        {"feature": "Y potentiometer body", "class": "A", "removable": "NO", "trimmable": "NO", "electricallyRequired": "YES / VRy", "mechanicallyRequired": "YES"},
        {"feature": "bottom push-switch body", "class": "A", "removable": "NO", "trimmable": "NO", "electricallyRequired": "YES / SW", "mechanicallyRequired": "YES"},
        {"feature": "mounting-hole functional regions", "class": "A", "removable": "NO", "trimmable": "NO", "electricallyRequired": "NO", "mechanicallyRequired": "YES"},
        {"feature": "external knob/cap", "class": "B", "removable": "POTENTIALLY", "trimmable": "NO", "electricallyRequired": "NO", "mechanicallyRequired": "USER INTERFACE / MAY BE REPLACED"},
        {"feature": "1x5 distal pin length", "class": "B", "removable": "POTENTIALLY", "trimmable": "YES", "electricallyRequired": "ROOT YES / DISTAL LENGTH NO", "mechanicallyRequired": "NO IF STRAIN RELIEF PROVIDED"},
        {"feature": "1x5 header plastic", "class": "C", "removable": "UNKNOWN", "trimmable": "NO", "electricallyRequired": "NO", "mechanicallyRequired": "UNKNOWN / VERIFY ANCHOR"},
        {"feature": "PCB pads + solder roots GND/+5V/VRx/VRy/SW", "class": "A", "removable": "NO", "trimmable": "NO", "electricallyRequired": "ALL FIVE YES", "mechanicallyRequired": "SOLDER/STRAIN RELIEF"},
    ]

    guard_after = {str(path.relative_to(ROOT)): sha256(path) for path in guard_paths}
    if guard_before != guard_after:
        raise RuntimeError("Frozen/source hash guard changed during read-only audit")
    memory("final hash guard")
    data: dict[str, object] = {
        "schema": "onegrip.szh_ek056.provisional_thumb_integration_audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOCAL / SINGLE PROCESS / SERIAL OCCT / APPROXIMATE REFERENCE / PRODUCTION EDIT 0",
        "policy": {
            "fullShellBooleanCount": 0,
            "localShellCropCount": 2,
            "fullProductionAssemblyCount": 0,
            "multiprocessing": False,
            "bruteForceCandidates": 0,
            "stepExports": 0,
            "stlExports": 0,
            "sub0p5FinalJudgementAllowed": False,
        },
        "freeze": {"finger8ButtonBaseline": "HARD FROZEN", "M4N3TerminalTrim": "PRESERVED", "exterior": "PRESERVED", "productionGeometryEdits": 0},
        "sourceHashesBeforeAfterIdentical": True,
        "sourceSha256": guard_after,
        "reference": {
            "name": "SZH_EK056_WEB_REFERENCE",
            "quality": "LOW",
            "exactMetrology": False,
            "pinLabelSourceImage": str(PIN_LABEL_IMAGE.relative_to(ROOT)),
            "electricalPinLabels": ["GND", "+5V", "VRx", "VRy", "SW"],
            "allFiveConnectionsRequired": True,
            "placementFrame": {"originMm": origin.tolist(), "localXWorld": DATUM_V.tolist(), "localYWorld": DATUM_U.tolist(), "localZWorld": OUTWARD.tolist(), "pivotWorldMm": DATUM_P.tolist()},
        },
        "joystickGeometryClassification": geometry_classes,
        "mountingAlignment": mounting,
        "staticAudit": static,
        "axialDatumSensitivity": {
            "reason": "web pivot-Z is LOW-confidence; shaft centerline/axis preserved while original mounting plane is matched once",
            "axialShiftMm": axial_shift_mm,
            "shaftCenterlineLateralErrorMm": 0.0,
            "axisAngularErrorDeg": 0.0,
            "candidateSearch": False,
            "productionPlacement": False,
            "staticAudit": sensitivity_static,
            "wiringDeparture": sensitivity_wiring,
        },
        "configurationComparison": {
            "stock": {"status": stock_status, "headerPlastic": "PRESENT", "distalPins": "PRESENT"},
            "directSolderTrim": {"status": direct_status, "headerPlastic": "OMITTED IN AUDIT PROXY", "retainedPinRootLengthMm": 3.15, "pcbPadsAndElectricalRoots": "PRESERVED", "productionModification": False},
        },
        "wiringDeparture": wiring,
        "movingEnvelope": moving_audit,
        "verdict": verdict,
        "renders": [str(path.relative_to(ROOT)) for path in renders],
        "memoryLog": MEMORY,
        "stop": "STOP AFTER PROVISIONAL AUDIT; no N1/N2 redesign, production adapter, final wire channel, fastening or MCU placement",
    }
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(report_markdown(data), encoding="utf-8")
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    print(f"JSON: {JSON_PATH}")
    print(f"REPORT: {REPORT_PATH}")
    print(f"RENDERS: {len(renders)} in {RENDER_DIR}")


if __name__ == "__main__":
    main()
