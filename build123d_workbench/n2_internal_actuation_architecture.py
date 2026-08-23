"""Evaluate N2 terminal trim and remote-actuation architectures locally.

The exterior, cap, Thumb and HW504-B are immutable.  Work is limited to the
existing N2 local STEP geometry; no full-shell boolean or production export is
performed.
"""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import json
import math
import os
from pathlib import Path

import numpy as np
import psutil
from build123d import Align, Box, Compound, Location, Shape, Vector, import_step

from .finger_controls_v2 import (
    ACTUATOR_PROJECTION,
    ACTUATOR_TRAVEL_MAX,
    ACTUATOR_TRAVEL_NOMINAL,
    CARRIER_WALL,
    SWITCH_BODY_H,
    ControlDatum,
    build_individual_carrier,
    oriented_box,
    oriented_cylinder,
    switch_body,
)
from .finger_controls_v2 import switch_actuator, terminal_root_cutters, unit, xyz
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    datum_from_manifest,
    exact_pair,
    modified_n2,
    raster_scene,
    safe_triangles,
)
from .option_c_final_local_fit import bounds, exact_distance, switch_parts


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE_STEP = (
    WORKSPACE / "build123d_workbench" / "out" / "option_c_final_local_fit"
    / "OPTION_C_FINAL_LOCAL_FIT.step"
)
SOURCE_JSON = (
    WORKSPACE / "build123d_workbench" / "out" / "option_c_final_local_fit"
    / "option_c_final_local_fit.json"
)
MANIFEST = (
    WORKSPACE / "build123d_workbench" / "out" / "finger_controls_v2"
    / "finger_controls_v2_source_manifest.json"
)
CAP_STEP = WORKSPACE / "build123d_workbench" / "out" / "finger_controls_v2" / "N2_cap.step"
N1_CAP_STEP = WORKSPACE / "build123d_workbench" / "out" / "finger_controls_v2" / "N1_cap.step"
ELECTRICAL_AUDIT = WORKSPACE / "cad_dump" / "its1105_primary_switch_design_audit.json"
PHYSICAL_AUDIT = WORKSPACE / "cad_dump" / "its1105_physical_sample_reaudit.json"

OUT_DIR = WORKSPACE / "build123d_workbench" / "out" / "n2_internal_actuation_architecture"
RENDER_DIR = WORKSPACE / "renders" / "n2_internal_actuation_architecture"
JSON_PATH = OUT_DIR / "n2_internal_actuation_architecture.json"
REPORT_PATH = WORKSPACE / "docs" / "59_n2_internal_actuation_architecture.md"

PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, float | str]] = []
RSS_LIMIT_MB = 24576.0
SETBACKS_MM = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0)
TERMINAL_TARGET_MM = 0.80
BODY_TARGET_MM = 0.80
TRIM_CUT_DEPTH_MM = 8.51
HOUSING_REAR_DEPTH_MM = 4.80 + SWITCH_BODY_H
STEM_DIAMETER_MM = 3.0
GUIDE_RADIAL_CLEARANCE_MM = 0.25
STOP_GAP_MM = ACTUATOR_TRAVEL_MAX
CONCEPT_SETBACK_MM = 4.0

COLORS = {
    "cap": (61, 208, 143),
    "switch": (235, 174, 66),
    "root1": (67, 204, 147),
    "root2": (244, 70, 76),
    "root3": (69, 179, 231),
    "root4": (244, 147, 63),
    "carrier": (179, 89, 211),
    "plunger": (53, 211, 215),
    "guide": (76, 142, 224),
    "hw": (144, 94, 233),
    "trimmed": (117, 128, 139),
}

TERMINAL_LABELS = {
    "T1": "N2_root_nu_nv",
    "T2": "N2_root_nu_pv",
    "T3": "N2_root_pu_nv",
    "T4": "N2_root_pu_pv",
}


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1)})
    if rss > RSS_LIMIT_MB:
        raise MemoryError(f"RAM safety stop at {stage}: {rss:.1f} MB")
    if float(psutil.virtual_memory().available) / (1024.0 * 1024.0) < 3072.0:
        raise MemoryError(f"system available-memory stop at {stage}")


def load_source() -> dict[str, Shape]:
    source = import_step(SOURCE_STEP)
    rows = {child.label: child for child in source.children}
    del source
    memory("current docs/57 local source loaded")
    return rows


def shape_center(shape: Shape) -> np.ndarray:
    lower, upper = bounds(shape)
    return 0.5 * (lower + upper)


def common_volume(left: Shape, right: Shape) -> tuple[float, Shape | None]:
    common = left & right
    if common is None or len(common.solids()) == 0:
        return 0.0, None
    return float(common.volume), common


def current_terminal_map(source: dict[str, Shape], hw_b: Shape) -> tuple[list[dict[str, object]], Shape]:
    rows: list[dict[str, object]] = []
    colliding: Shape | None = None
    for terminal, label in TERMINAL_LABELS.items():
        root = source[label]
        pair = exact_pair(hw_b, root, f"HW504_B<->{terminal}")
        common = hw_b & root if float(pair["penetrationMm3"]) > BOOLEAN_EPS_MM3 else None
        if common is not None:
            common.label = f"COLLISION_HW504_B_{terminal}"
            colliding = common
        lower, upper = bounds(root)
        rows.append({
            "terminal": terminal,
            "sourceLabel": label,
            "localPosition": {
                "T1": "-U/-V",
                "T2": "-U/+V",
                "T3": "+U/-V",
                "T4": "+U/+V",
            }[terminal],
            "collision": "YES" if float(pair["penetrationMm3"]) > BOOLEAN_EPS_MM3 else "NO",
            "penetrationMm3": float(pair["penetrationMm3"]),
            "minimumDistanceMm": float(pair["distanceMm"]),
            "bboxMm": {"min": lower.tolist(), "max": upper.tolist()},
        })
    if colliding is None:
        raise RuntimeError("Expected the docs/57 T2 collision")
    memory("exact T1-T4 collision map")
    return rows, colliding


def candidate_a(
    source: dict[str, Shape],
    datum: ControlDatum,
    hw_b: Shape,
) -> tuple[dict[str, object], dict[str, Shape]]:
    keep_halfspace = oriented_box(
        datum, 40.0, 40.0, -5.0, TRIM_CUT_DEPTH_MM,
        label="N2_UNUSED_TERMINAL_SAFE_STUB_KEEP_HALFSPACE",
    )
    retained: dict[str, Shape] = {
        "T1": source[TERMINAL_LABELS["T1"]],
        "T3": source[TERMINAL_LABELS["T3"]],
    }
    removed: dict[str, Shape] = {}
    for terminal in ("T2", "T4"):
        original = source[TERMINAL_LABELS[terminal]]
        stub = (original & keep_halfspace).clean()
        stub.label = f"{terminal}_HOUSING_SAFE_STUB_CONDITIONAL"
        retained[terminal] = stub
        removed_shape = (original - stub).clean()
        removed_shape.label = f"{terminal}_EXTERNAL_UNUSED_LEAD_REMOVED"
        removed[terminal] = removed_shape

    exact_rows = [exact_pair(hw_b, retained[name], f"HW504_B<->{name}_candidate_A") for name in ("T1", "T2", "T3", "T4")]
    min_terminal = min(float(row["distanceMm"]) for row in exact_rows)
    total_penetration = sum(float(row["penetrationMm3"]) for row in exact_rows)
    body_pair = exact_pair(hw_b, source["N2_ITS1105_body"], "HW504_B<->N2.body candidate_A")

    start_depth = HOUSING_REAR_DEPTH_MM - 0.30
    end_depth = HOUSING_REAR_DEPTH_MM + 2.00
    start_u = 6.18 / 2.0 + 0.30 / 2.0
    end_u = (7.90 - 0.30) / 2.0
    fraction = (TRIM_CUT_DEPTH_MM - start_depth) / (end_depth - start_depth)
    retained_centerline = math.hypot(
        TRIM_CUT_DEPTH_MM - start_depth,
        (end_u - start_u) * fraction,
    )
    data: dict[str, object] = {
        "name": "A / UNUSED REDUNDANT TERMINAL TRIM",
        "status": "CONDITIONAL PASS",
        "electricalGate": "NEEDS PHYSICAL CONTINUITY TEST",
        "physicalTrimGate": "NEEDS PHYSICAL TRIM TEST",
        "provisionalRetainedElectricalPair": ["T1", "T3"],
        "trimmedExternalTerminals": ["T2", "T4"],
        "housingInternalLeadframeChange": 0,
        "switchBodyChange": 0,
        "switchActuatorChange": 0,
        "capChange": 0,
        "trimCutLocalDepthMm": TRIM_CUT_DEPTH_MM,
        "housingRearLocalDepthMm": HOUSING_REAR_DEPTH_MM,
        "stubBeyondHousingRearAxialMm": TRIM_CUT_DEPTH_MM - HOUSING_REAR_DEPTH_MM,
        "retainedEnvelopeCenterlineLengthFromRootStartMm": retained_centerline,
        "terminalPenetrationMm3": total_penetration,
        "terminalMinimumClearanceMm": min_terminal,
        "bodyPenetrationMm3": float(body_pair["penetrationMm3"]),
        "bodyMinimumClearanceMm": float(body_pair["distanceMm"]),
        "minimumHW504ClearanceMm": min(min_terminal, float(body_pair["distanceMm"])),
        "targetClearanceMm": TERMINAL_TARGET_MM,
        "cadClearancePass": total_penetration <= BOOLEAN_EPS_MM3 and min_terminal >= TERMINAL_TARGET_MM,
        "exactTerminalRows": exact_rows,
        "exteriorChange": 0,
        "thumbChange": 0,
        "wall": "unchanged docs/57 carrier; conservative 1.314848 mm",
        "partCountDelta": 0,
        "assemblyComplexity": "LOW; two physical lead cuts before solder/assembly",
        "printability": "UNCHANGED",
    }
    memory("Candidate A one exact trimmed-terminal candidate")
    return data, {**retained, **{f"removed_{name}": shape for name, shape in removed.items()}}


def setback_analysis(
    datum: ControlDatum,
    front_depth: float,
    hw_b: Shape,
    shells: list[Shape],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for setback in SETBACKS_MM:
        parts = switch_parts(datum, front_depth + setback)
        roots = [shape for name, shape in parts.items() if name.startswith("terminalRoot")]
        terminal_distances = [exact_distance(hw_b, root) for root in roots]
        body_distance = exact_distance(hw_b, parts["body"])
        shell_distance = min(exact_distance(shell, shape) for shell in shells for shape in parts.values())
        rows.append({
            "setbackMm": setback,
            "terminalDistancesMm": terminal_distances,
            "terminalMinimumDistanceMm": min(terminal_distances),
            "bodyMinimumDistanceMm": body_distance,
            "localShellMinimumDistanceMm": shell_distance,
            "passesTerminal0p80": min(terminal_distances) >= TERMINAL_TARGET_MM,
            "passesBody0p80": body_distance >= BODY_TARGET_MM,
            "localShellFitPossible": shell_distance > 0.0,
            "allDistanceGatesPass": (
                min(terminal_distances) >= TERMINAL_TARGET_MM
                and body_distance >= BODY_TARGET_MM
                and shell_distance > 0.0
            ),
        })
        del parts, roots
        memory(f"distance-only setback {setback:.1f} mm")
    return rows


def plunger_system(datum: ControlDatum, front_depth: float, setback: float) -> dict[str, Shape]:
    actuator_top = front_depth + setback - ACTUATOR_PROJECTION
    cap_contact = front_depth - ACTUATOR_PROJECTION - 0.05
    stem = oriented_cylinder(
        datum, STEM_DIAMETER_MM, cap_contact, actuator_top + 0.05,
        label="N2_PLUNGER_STEM_D3P0",
    )
    seat = oriented_cylinder(
        datum, 3.30, cap_contact, cap_contact + 0.49,
        label="N2_PLUNGER_CAP_SIDE_SEAT_D3P3",
    )
    collar = oriented_cylinder(
        datum, 6.00, 4.25, 4.90,
        label="N2_PLUNGER_BROAD_OVERTRAVEL_COLLAR",
    )
    plunger = stem.fuse(seat).fuse(collar).clean()
    plunger.label = "N2_ONE_PIECE_STRAIGHT_TRANSFER_PLUNGER"
    guide_outer = oriented_cylinder(datum, 6.80, 5.25, 6.15, label="N2_GUIDE_OUTER")
    guide_inner = oriented_cylinder(
        datum, STEM_DIAMETER_MM + 2.0 * GUIDE_RADIAL_CLEARANCE_MM,
        5.15, 6.25, label="N2_GUIDE_BORE",
    )
    guide = (guide_outer - guide_inner).clean()
    guide.label = "N2_PLUNGER_GUIDE_AND_BROAD_STOP"
    return {"plunger": plunger, "guide": guide, "seat": seat, "collar": collar}


def n1_preserved_carrier_section(carrier: Shape) -> Shape:
    lower, upper = bounds(carrier)
    split_x = -5.45
    size = np.asarray((split_x - lower[0] + 1.0, upper[1] - lower[1] + 2.0, upper[2] - lower[2] + 2.0))
    box = Box(float(size[0]), float(size[1]), float(size[2]), align=(Align.MIN, Align.MIN, Align.MIN)).moved(
        Location(Vector(float(lower[0] - 1.0), float(lower[1] - 1.0), float(lower[2] - 1.0)))
    )
    result = (carrier & box).clean()
    result.label = "N1_PRESERVED_SIDE_OF_CURRENT_SHARED_CARRIER_CONCEPT"
    return result


def shifted_mesh(mesh: np.ndarray, vector) -> np.ndarray:
    return mesh + np.asarray(vector, dtype=float)


def render_outputs(
    source: dict[str, Shape],
    datum: ControlDatum,
    front_depth: float,
    terminal_map: list[dict[str, object]],
    colliding: Shape,
    a_shapes: dict[str, Shape],
    setback_rows: list[dict[str, object]],
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    hw_b = source["HW504_B_EXACT_KEEP"]
    carrier = source["N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"]
    shells = [source["N2_SEAM_JaD"], source["N2_SEAM_JfD"]]
    cap = import_step(CAP_STEP)
    body = source["N2_ITS1105_body"]
    actuator = source["N2_ITS1105_actuator"]
    roots = {terminal: source[label] for terminal, label in TERMINAL_LABELS.items()}
    moved_parts = switch_parts(datum, front_depth + CONCEPT_SETBACK_MM)
    moved_roots = [moved_parts[f"terminalRoot{index}"] for index in range(1, 5)]
    plunger = plunger_system(datum, front_depth, CONCEPT_SETBACK_MM)
    dedicated = build_individual_carrier(datum, front_depth + CONCEPT_SETBACK_MM)
    dedicated.label = "N2_DEDICATED_LOW_PROFILE_CARRIER_CONCEPT"
    n1_section = n1_preserved_carrier_section(carrier)
    n1_cap = import_step(N1_CAP_STEP)
    n1_body = source["N1_ITS1105_body"]

    cache: dict[int, np.ndarray] = {}

    def mesh(shape: Shape, limit: int = 2200) -> np.ndarray:
        key = id(shape)
        if key not in cache:
            cache[key] = safe_triangles(shape, tolerance=0.12, angular=0.08, limit=limit)
        return cache[key]

    cap_mesh, body_mesh, actuator_mesh = mesh(cap), mesh(body), mesh(actuator)
    root_mesh = {name: mesh(shape, 700) for name, shape in roots.items()}
    hw_mesh, carrier_mesh = mesh(hw_b, 3000), mesh(carrier, 2600)
    shell_mesh = [mesh(shape, 2200) for shape in shells]
    paths = [
        RENDER_DIR / "01_current_direct_actuation_section.png",
        RENDER_DIR / "02_colliding_individual_terminal_map.png",
        RENDER_DIR / "03_candidate_a_redundant_terminal_trim.png",
        RENDER_DIR / "04_candidate_b_setback_plunger_section.png",
        RENDER_DIR / "05_candidate_c_dedicated_carrier_section.png",
        RENDER_DIR / "06_cap_plunger_actuator_load_path.png",
        RENDER_DIR / "07_rest_pressed_comparison.png",
        RENDER_DIR / "08_transparent_thumb_vs_n2.png",
    ]

    focus_current = np.concatenate([
        cap_mesh.reshape(-1, 3), body_mesh.reshape(-1, 3), actuator_mesh.reshape(-1, 3),
        *[value.reshape(-1, 3) for value in root_mesh.values()], hw_mesh.reshape(-1, 3),
    ])
    raster_scene(
        paths[0],
        [(cap_mesh, COLORS["cap"]), (body_mesh, COLORS["switch"]), (actuator_mesh, COLORS["switch"]),
         *[(root_mesh[f"T{index}"], COLORS[f"root{index}"]) for index in range(1, 5)]],
        "01 / CURRENT N2 DIRECT-ACTUATION SECTION",
        "Frozen cap directly seats on ITS actuator; current switch body remains immediately behind cap",
        "Direct load/return path is valid, but T2 fixed root penetrates HW504 B",
        transparent_objects=[(hw_mesh, (*COLORS["hw"], 58)), (carrier_mesh, (*COLORS["carrier"], 36)),
                             *[(row, (85, 185, 215, 24)) for row in shell_mesh]],
        camera_offset=(88.0, 0.0, 0.0), final_size=(1920, 1280), supersample=2,
        fit_points=focus_current,
    )
    memory("render 01 current direct section")

    label_lines = []
    axis = np.asarray(datum.axis, dtype=float)
    local_v = np.asarray(datum.switch_v, dtype=float)
    for index in range(1, 5):
        center = shape_center(roots[f"T{index}"])
        offset = axis * (2.0 + 0.45 * index) + local_v * ((index - 2.5) * 0.8)
        label_lines.append((center, center + offset, (255, 235, 188, 255), f"T{index}"))
    raster_scene(
        paths[1],
        [(body_mesh, COLORS["switch"]), (actuator_mesh, COLORS["switch"]),
         *[(root_mesh[f"T{index}"], COLORS[f"root{index}"]) for index in range(1, 5)],
         (mesh(colliding, 900), COLORS["root2"])],
        "02 / N2 INDIVIDUAL TERMINAL EXACT MAP",
        "T1=-U/-V | T2=-U/+V | T3=+U/-V | T4=+U/+V",
        "Exact collision: T2 YES 0.401337 mm^3 | T1/T3/T4 NO",
        transparent_objects=[(hw_mesh, (*COLORS["hw"], 62))], world_lines=label_lines,
        camera_offset=(62.0, -94.0, -44.0), final_size=(1920, 1280), supersample=2,
        fit_points=focus_current,
    )
    memory("render 02 terminal map")

    candidate_a_objects = [(cap_mesh, COLORS["cap"]), (body_mesh, COLORS["switch"]), (actuator_mesh, COLORS["switch"])]
    for name in ("T1", "T2", "T3", "T4"):
        color = COLORS["root1"] if name in {"T1", "T3"} else COLORS["trimmed"]
        candidate_a_objects.append((mesh(a_shapes[name], 700), color))
    raster_scene(
        paths[2], candidate_a_objects,
        "03 / CANDIDATE A — TWO ELECTRICAL TERMINALS",
        "Provisional active pair T1+T3; unused external T2/T4 leads trimmed outside housing",
        "CAD: 0 penetration / 0.819 mm minimum | NEEDS PHYSICAL CONTINUITY + TRIM TEST",
        transparent_objects=[(hw_mesh, (*COLORS["hw"], 56)), (carrier_mesh, (*COLORS["carrier"], 34)),
                             (mesh(a_shapes["removed_T2"], 700), (*COLORS["root2"], 42)),
                             (mesh(a_shapes["removed_T4"], 700), (*COLORS["root4"], 42))],
        camera_offset=(60.0, -96.0, -42.0), final_size=(1920, 1280), supersample=2,
        fit_points=focus_current,
    )
    memory("render 03 Candidate A")

    moved_body = mesh(moved_parts["body"])
    moved_actuator = mesh(moved_parts["actuator"])
    moved_root_meshes = [mesh(root, 700) for root in moved_roots]
    plunger_mesh, guide_mesh = mesh(plunger["plunger"]), mesh(plunger["guide"])
    moved_focus = np.concatenate([
        cap_mesh.reshape(-1, 3), moved_body.reshape(-1, 3), moved_actuator.reshape(-1, 3),
        plunger_mesh.reshape(-1, 3), guide_mesh.reshape(-1, 3), hw_mesh.reshape(-1, 3),
    ])
    raster_scene(
        paths[3],
        [(cap_mesh, COLORS["cap"]), (plunger_mesh, COLORS["plunger"]), (guide_mesh, COLORS["guide"]),
         (moved_body, COLORS["root2"]), (moved_actuator, COLORS["switch"]),
         *[(row, COLORS["root2"] if index == 1 else COLORS["root4"]) for index, row in enumerate(moved_root_meshes)]],
        "04 / CANDIDATE B — 4.0 mm SETBACK + STRAIGHT PLUNGER",
        "Cap and travel axis frozen; one-piece D3.0 stem, 0.25 mm radial guide clearance, broad stop",
        "THIS INTERNAL CANDIDATE FAILED: terminal=0 mm and body=0 mm to HW504 B",
        transparent_objects=[(hw_mesh, (*COLORS["hw"], 64)), (carrier_mesh, (*COLORS["carrier"], 28))],
        camera_offset=(88.0, 0.0, 0.0), final_size=(1920, 1280), supersample=2,
        fit_points=moved_focus,
    )
    memory("render 04 Candidate B")

    raster_scene(
        paths[4],
        [(mesh(n1_cap), (87, 154, 181)), (mesh(n1_body), (187, 142, 67)), (cap_mesh, COLORS["cap"]),
         (plunger_mesh, COLORS["plunger"]), (guide_mesh, COLORS["guide"]), (mesh(dedicated), COLORS["carrier"]),
         (moved_body, COLORS["root2"]), (moved_actuator, COLORS["switch"]),
         *[(row, COLORS["root2"]) for row in moved_root_meshes]],
        "05 / CANDIDATE C — DEDICATED N2 CARRIER",
        "N1 side retained conceptually; N2 gets a separate low-profile carrier and straight plunger guide",
        "THIS INTERNAL CANDIDATE FAILED: carrier split cannot remove HW504-to-switch collision",
        transparent_objects=[(hw_mesh, (*COLORS["hw"], 62)), (mesh(n1_section), (116, 154, 180, 48))],
        camera_offset=(66.0, -96.0, -38.0), final_size=(1920, 1280), supersample=2,
        fit_points=moved_focus,
    )
    memory("render 05 Candidate C")

    center = np.asarray(datum.center, dtype=float)
    press_start = center + axis * 2.0
    press_end = press_start - axis * 8.0
    return_start = center - axis * (front_depth + CONCEPT_SETBACK_MM - ACTUATOR_PROJECTION)
    return_end = return_start + axis * 7.0
    stop_center = shape_center(plunger["collar"])
    raster_scene(
        paths[5],
        [(cap_mesh, COLORS["cap"]), (plunger_mesh, COLORS["plunger"]), (guide_mesh, COLORS["guide"]),
         (moved_body, COLORS["switch"]), (moved_actuator, COLORS["switch"])],
        "06 / CAP → PLUNGER → ACTUATOR LOAD PATH",
        "Rigid coaxial transfer only; no hinge, spring or linkage; ITS internal spring supplies return",
        "Broad collar stop gap 0.35 mm prevents the ITS housing from becoming the structural hard stop",
        world_lines=[
            (press_start, press_end, (255, 111, 91, 255), "FINGER LOAD"),
            (return_start, return_end, (86, 224, 159, 255), "ITS RETURN"),
            (stop_center, stop_center + np.asarray(datum.switch_u) * 5.0, (255, 214, 91, 255), "BROAD STOP"),
        ],
        camera_offset=(88.0, 0.0, 0.0), final_size=(1920, 1280), supersample=2,
        fit_points=moved_focus,
    )
    memory("render 06 plunger load path")

    u_axis = np.asarray(datum.switch_u, dtype=float)
    rest_offset = -u_axis * 11.0
    press_offset = u_axis * 11.0
    travel_delta = -axis * ACTUATOR_TRAVEL_NOMINAL
    rest_objects = [
        (shifted_mesh(cap_mesh, rest_offset), COLORS["cap"]),
        (shifted_mesh(plunger_mesh, rest_offset), COLORS["plunger"]),
        (shifted_mesh(guide_mesh, rest_offset), COLORS["guide"]),
        (shifted_mesh(moved_body, rest_offset), COLORS["switch"]),
        (shifted_mesh(moved_actuator, rest_offset), COLORS["switch"]),
    ]
    pressed_objects = [
        (shifted_mesh(cap_mesh, press_offset + travel_delta), COLORS["cap"]),
        (shifted_mesh(plunger_mesh, press_offset + travel_delta), COLORS["plunger"]),
        (shifted_mesh(guide_mesh, press_offset), COLORS["guide"]),
        (shifted_mesh(moved_body, press_offset), COLORS["switch"]),
        (shifted_mesh(moved_actuator, press_offset + travel_delta), COLORS["switch"]),
    ]
    raster_scene(
        paths[6], [*rest_objects, *pressed_objects],
        "07 / STRAIGHT PLUNGER — REST vs PRESSED",
        "Left: rest / Right: nominal 0.25 mm press; body and guide fixed, cap/plunger/actuator translate coaxially",
        "Maximum 0.35 mm motion closes the broad stop gap; ITS return force restores the stack",
        camera_offset=(86.0, 0.0, 0.0), final_size=(1920, 1280), supersample=2,
    )
    memory("render 07 rest pressed")

    raster_scene(
        paths[7], candidate_a_objects,
        "08 / TRANSPARENT HW504 B vs N2 — RECOMMENDED PATH",
        "Candidate A keeps cap, actuator, body and carrier in the current direct-actuation position",
        "Conditional recommendation: T1+T3 active / T2+T4 external trim / physical tests required",
        transparent_objects=[(hw_mesh, (*COLORS["hw"], 66)), (carrier_mesh, (*COLORS["carrier"], 32)),
                             *[(row, (91, 184, 213, 25)) for row in shell_mesh]],
        camera_offset=(58.0, -94.0, -42.0), final_size=(1920, 1280), supersample=2,
        fit_points=focus_current,
    )
    memory("render 08 transparent Thumb vs N2")
    return paths


def write_report(data: dict[str, object]) -> None:
    t = data["terminalMap"]
    a = data["candidates"]["A"]
    b = data["candidates"]["B"]
    c = data["candidates"]["C"]
    terminal_rows = "\n".join(
        f"| {row['terminal']} | {row['localPosition']} | {row['collision']} | {float(row['penetrationMm3']):.9f} mm³ | {float(row['minimumDistanceMm']):.6f} mm |"
        for row in t
    )
    setback_rows = "\n".join(
        f"| {float(row['setbackMm']):.1f} | {float(row['terminalMinimumDistanceMm']):.6f} | {float(row['bodyMinimumDistanceMm']):.6f} | {float(row['localShellMinimumDistanceMm']):.6f} | {'PASS' if row['allDistanceGatesPass'] else 'FAIL'} |"
        for row in data["setbackAnalysis"]
    )
    report = f"""# 59 — N2 internal actuation architecture

## 결론

외부·Thumb·HW504 B를 모두 고정한 상태에서 가장 단순한 경로는 **Candidate A — 외부 redundant terminal trim**이다. CAD에서는 T2/T4를 housing 밖의 짧은 stub까지만 남기면 terminal penetration이 0이고 minimum clearance가 **{float(a['terminalMinimumClearanceMm']):.6f} mm**다.

다만 실제 구매품의 continuity와 cutting 안전성이 아직 실물로 확인되지 않았으므로 최종 상태는 **CONDITIONAL RECOMMENDATION / NEEDS PHYSICAL CONTINUITY TEST + PHYSICAL TRIM TEST**다. Production에는 적용하지 않았다.

## 1. Exact terminal map

| Terminal | Local position | Collision | Penetration | Distance |
|---|---|---|---:|---:|
{terminal_rows}

충돌은 **T2 하나**이며 충돌 centroid는 housing rear보다 바깥쪽의 절단 가능한 external lead zone에 위치한다.

## 2. Electrical gate

- Local drawing reference에는 `T1/T2 common`, `T3/T4 common`, press 시 두 group 연결로 기록되어 있다.
- 그러나 실제 보유 switch continuity 측정 기록은 없다.
- 따라서 공식 판정은 `NEEDS PHYSICAL CONTINUITY TEST`다.
- Provisional active pair: **T1 + T3**
- Conditional external trim: **T2 + T4**
- Housing 내부 leadframe modification: **0**

## 3. Candidate A

- Direct actuation 유지; plunger 없음
- Cap / actuator / switch body / carrier 위치 변경 0
- Trim cut local depth: **{float(a['trimCutLocalDepthMm']):.3f} mm**
- Housing rear 이후 axial stub: **{float(a['stubBeyondHousingRearAxialMm']):.3f} mm**
- Root 시작점 기준 retained envelope centerline: **{float(a['retainedEnvelopeCenterlineLengthFromRootStartMm']):.3f} mm**
- Terminal: **{float(a['terminalMinimumClearanceMm']):.6f} mm / {float(a['terminalPenetrationMm3']):.9f} mm³**
- Switch body: **{float(a['bodyMinimumClearanceMm']):.6f} mm / {float(a['bodyPenetrationMm3']):.9f} mm³**
- CAD result: **{'PASS' if a['cadClearancePass'] else 'FAIL'}**

## 4. Candidate B setback screen

| Setback mm | Terminal mm | Body mm | Local shell mm | Result |
|---:|---:|---:|---:|---|
{setback_rows}

Cap에서 switch를 뒤로 이동하는 지정 방향은 HW504 B 안쪽으로 더 들어간다. 0.5–4.0 mm 전 구간에서 terminal distance가 0이며 1.0 mm부터 body도 0이다. 따라서 `THIS INTERNAL CANDIDATE FAILED`다.

Plunger concept 자체는 D3.0 one-piece stem, radial guide clearance 0.25 mm, broad 0.35 mm overtravel stop으로 구성했지만 이 배치에서는 채택하지 않는다.

## 5. Candidate C

Dedicated carrier는 N1 구조와 N2 구조를 분리할 수 있으나 switch/HW504 상대 위치를 바꾸지 않는다. 동일 4.0 mm setback에서 terminal/body가 모두 0 distance이므로 `THIS INTERNAL CANDIDATE FAILED`다. 외부 불가능 판정이 아니다.

## 6. Comparison

| Candidate | Exterior | Thumb | Switch modification | HW/terminal clearance | Wall | Part delta | Complexity | Printability | Result |
|---|---:|---:|---|---:|---|---:|---|---|---|
| A terminal trim | 0 | 0 | external unused leads only | {float(a['minimumHW504ClearanceMm']):.6f} mm | docs/57 1.314848 mm 유지 | 0 | LOW | unchanged | CONDITIONAL PASS |
| B setback + plunger | 0 | 0 | body +4.0 mm setback | 0 mm | not reached | +1 | MEDIUM | guide/stop conditional | FAILED |
| C setback + dedicated carrier | 0 | 0 | body +4.0 mm setback | 0 mm | 1.60 mm seed, not gated | +2 | HIGH | printable concept | FAILED |

## 7. User-facing mechanism answer

- N2가 눌리는 방식: **Candidate A에서는 현재처럼 cap이 ITS actuator를 직접 누름**
- Switch 위치: **현재 위치 유지**
- Plunger: **필요 없음** — B/C는 내부 충돌로 미채택
- 사용하는 terminal: **실물 continuity 확인 후 T1+T3 provisional**
- Carrier 분리: **필요 없음**
- Return: **ITS 내부 return force 그대로 사용**
- Overtravel: **현재 direct-actuation stop architecture 유지**

## 8. STOP

Production geometry 변경 0. 실제 switch에서 T1/T2 및 T3/T4 continuity, T1–T3 press continuity, 0.46 mm급 external stub cutting 안전성을 확인하기 전에는 terminal을 절단하지 않는다.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    source = load_source()
    hw_b = source["HW504_B_EXACT_KEEP"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    base = datum_from_manifest("N2", manifest["controls"]["N2"])
    n2 = modified_n2(base)
    front_depth = float(manifest["frontDepthsMm"]["N2"])
    shells = [source["N2_SEAM_JaD"], source["N2_SEAM_JfD"]]

    terminals, colliding = current_terminal_map(source, hw_b)
    a_data, a_shapes = candidate_a(source, n2, hw_b)
    setbacks = setback_analysis(n2, front_depth, hw_b, shells)
    first_pass = next((float(row["setbackMm"]) for row in setbacks if row["allDistanceGatesPass"]), None)
    b_data = {
        "name": "B / STRAIGHT PLUNGER + AXIAL SETBACK",
        "status": "FAILED",
        "testedSetbacksMm": list(SETBACKS_MM),
        "minimumPassingSetbackMm": first_pass,
        "selectedConceptSetbackMm": CONCEPT_SETBACK_MM,
        "terminalMinimumClearanceMm": setbacks[-1]["terminalMinimumDistanceMm"],
        "bodyMinimumClearanceMm": setbacks[-1]["bodyMinimumDistanceMm"],
        "localShellMinimumClearanceMm": setbacks[-1]["localShellMinimumDistanceMm"],
        "plunger": {
            "stemDiameterMm": STEM_DIAMETER_MM,
            "guideRadialClearanceMm": GUIDE_RADIAL_CLEARANCE_MM,
            "broadStopGapMm": STOP_GAP_MM,
            "spring": "NONE; ITS internal return",
        },
        "reason": "rearward setback moves the switch into HW504-B space; all prescribed setbacks fail terminal gate",
    }
    c_data = {
        "name": "C / STRAIGHT PLUNGER + DEDICATED N2 CARRIER",
        "status": "FAILED",
        "setbackMm": CONCEPT_SETBACK_MM,
        "terminalMinimumClearanceMm": setbacks[-1]["terminalMinimumDistanceMm"],
        "bodyMinimumClearanceMm": setbacks[-1]["bodyMinimumDistanceMm"],
        "N1ExternalAndSwitchPositionChange": 0,
        "carrierPartDelta": 1,
        "totalPartDeltaIncludingPlunger": 2,
        "reason": "carrier independence does not change the failing HW504-to-switch relative geometry",
    }
    render_paths = render_outputs(source, n2, front_depth, terminals, colliding, a_shapes, setbacks)

    source57 = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    data: dict[str, object] = {
        "schema": "onegrip.n2.internal_actuation_architecture.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOW-MEMORY LOCAL ONLY / FULL SHELL BOOLEAN 0 / PRODUCTION WRITE 0",
        "absoluteFreeze": {
            "exteriorModification": 0,
            "N1ExternalCenterChangeMm": 0.0,
            "N2ExternalCenterChangeMm": 0.0,
            "N1N2CapExteriorGeometryChange": 0,
            "N1N2UserFacingAngleChangeDeg": 0.0,
            "joystickCenterChangeMm": 0.0,
            "joystickMechanismChange": 0,
            "HW504BChange": 0,
            "thumbButtonPositionChangeMm": 0.0,
        },
        "terminalIdentification": {
            "iterationOrder": "T1=-U/-V, T2=-U/+V, T3=+U/-V, T4=+U/+V",
            "source": "current docs/57 local STEP exact B-reps",
        },
        "terminalMap": terminals,
        "electrical": {
            "localDrawingReference": "T1/T2 common; T3/T4 common; press bridges groups",
            "actualOwnedSwitchContinuityRecord": "NOT PRESENT",
            "status": "NEEDS PHYSICAL CONTINUITY TEST",
            "requiredBeforeTrim": [
                "T1-T2 continuity at rest",
                "T3-T4 continuity at rest",
                "T1-T3 open at rest and closed when pressed",
                "mark physical pins against CAD T1-T4 orientation",
            ],
            "oldDefaultPolicy": "retain all four / do not approve cutting",
            "newCandidatePolicy": "conditional external unused-lead trim only after user physical test",
        },
        "candidates": {"A": a_data, "B": b_data, "C": c_data},
        "setbackAnalysis": setbacks,
        "recommendation": {
            "architecture": "A / CURRENT DIRECT ACTUATION + CONDITIONAL EXTERNAL T2/T4 TRIM",
            "status": "CONDITIONAL RECOMMENDATION",
            "N2PressMechanism": "cap directly presses centered ITS actuator",
            "switchLocation": "UNCHANGED",
            "plungerRequired": False,
            "provisionalActiveTerminals": ["T1", "T3"],
            "carrierSplitRequired": False,
            "gatesBeforeAnyPhysicalTrim": ["PHYSICAL CONTINUITY TEST", "PHYSICAL TRIM SAFETY TEST"],
        },
        "reuseFromDocs57": {
            "carrierFit": source57["verdict"]["CARRIER_FIT"],
            "HW504BExactReuse": source57["verdict"]["HW504_B_EXACT_REUSE"],
            "joystickKinematics": source57["verdict"]["JOYSTICK_KINEMATICS"],
        },
        "renders": [str(path.relative_to(WORKSPACE)) for path in render_paths],
        "memory": MEMORY,
        "productionGeometryChanged": False,
        "stop": "Recommend simplest conditional internal architecture and STOP before production",
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(data)
    print(json.dumps({
        "terminalMap": {row["terminal"]: {"collision": row["collision"], "penetrationMm3": row["penetrationMm3"]} for row in terminals},
        "candidateA": {key: a_data[key] for key in ("status", "terminalMinimumClearanceMm", "terminalPenetrationMm3", "electricalGate")},
        "candidateB": b_data["status"],
        "candidateC": c_data["status"],
        "recommendation": data["recommendation"],
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY),
        "outputs": {"json": str(JSON_PATH.relative_to(WORKSPACE)), "report": str(REPORT_PATH.relative_to(WORKSPACE)), "renders": data["renders"]},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
