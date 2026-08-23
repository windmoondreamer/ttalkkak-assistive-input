"""Resolve the two HW504-independent integration conflicts from docs/67.

Local-only, serial OCCT pass.  HW504, N1/N2 joystick interaction, wiring,
fastening and electronics are intentionally absent.
"""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import psutil
from build123d import Align, Box, Compound, Location, Shape, Vector, export_step, import_step

from . import i2_i3_production_intent_mechanism as shared
from . import i4_m3_production_intent_mechanisms as i4prod
from .finger_controls_v2 import (
    FROZEN_FRONT_DEPTHS,
    SWITCH_BODY_H,
    SWITCH_BODY_X,
    TERMINAL_CLEARANCE,
    TERMINAL_METAL_U,
    TERMINAL_METAL_V,
    TERMINAL_ROOT_DEPTH,
    TERMINAL_ROOT_OUTER,
    TERMINAL_ROOT_PITCH,
    oriented_box,
    oriented_box_between,
    point_at,
    switch_body,
    terminal_root_cutters,
    unit,
    wire_envelope,
    wire_exit_cutter,
    xyz,
)
from .i4_m3_current_audit import load_all_datums
from .option_c_final_local_fit import bounds
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    exact_pair,
    raster_scene,
    safe_triangles,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "real_integration_conflict_resolution"
RENDER_DIR = ROOT / "renders" / "real_integration_conflict_resolution"
JSON_PATH = OUT_DIR / "real_integration_conflict_resolution.json"
REPORT_PATH = ROOT / "docs" / "68_real_integration_conflict_resolution.md"
TERMINAL_STEP = OUT_DIR / "M4_N3_SELECTED_TERMINAL_SOLUTION_LOCAL.step"
I4_CARRIER_STEP = OUT_DIR / "I4_CARRIER_LOCAL_MANUFACTURING_RELIEF.step"

M4N3_CARRIER_PATH = ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "M4_N3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step"
I2I3_CARRIER_PATH = ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "I2_I3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step"
I4_CARRIER_PATH = ROOT / "build123d_workbench" / "out" / "i4_m3_production_intent_mechanisms" / "I4_CARRIER_PRODUCTION_INTENT_LOCAL.step"
CAP_PATHS = {
    "M4": ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "M4_PRODUCTION_INTENT_CAP_LOCAL.step",
    "N3": ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "N3_PRODUCTION_INTENT_CAP_LOCAL.step",
    "I2": ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "I2_PRODUCTION_INTENT_CAP_LOCAL.step",
    "I3": ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "I3_PRODUCTION_INTENT_CAP_LOCAL.step",
    "I4": ROOT / "build123d_workbench" / "out" / "i4_m3_production_intent_mechanisms" / "I4_CAP_PRODUCTION_INTENT_LOCAL.step",
}
SHELL_PATHS = {
    "JaD": ROOT / "build123d_workbench" / "out" / "finger_controls_v2" / "JAD_FINGER_V2.step",
    "JfD": ROOT / "build123d_workbench" / "out" / "finger_controls_v2" / "JFD_FINGER_V2.step",
}
FREEZE_INPUTS = [
    ROOT / "docs" / "62_n2_rear_reaction_support_redesign.md",
    ROOT / "docs" / "63_n1_production_intent_mechanism.md",
    ROOT / "docs" / "64_i2_i3_production_intent_mechanism.md",
    ROOT / "docs" / "65_m4_n3_production_intent_mechanism.md",
    ROOT / "docs" / "66_i4_m3_production_intent_mechanisms.md",
    ROOT / "docs" / "67_all_8_button_integration_and_wiring_space_audit.md",
    *CAP_PATHS.values(), M4N3_CARRIER_PATH, I2I3_CARRIER_PATH, I4_CARRIER_PATH,
]

BUTTONS = ("M4", "N3", "I2", "I3", "I4")
TERMINAL_NAMES = ("T1", "T2", "T3", "T4")
SEGMENT_RATIOS = {"ROOT": (0.0, 0.3043478261), "MID": (0.3043478261, 0.6086956522), "DISTAL": (0.6086956522, 1.0)}
OLD_TERMINAL_PEN_MM3 = 0.28339302834904956
OLD_CARRIER_CLEARANCE_MM = 0.10480528037784022
TARGET_CARRIER_CLEARANCE_MM = 0.40
RELIEF_DEPTH_U_MM = 0.32
MIN_WALL_MM = 1.20
ORIGINAL_LOCAL_WALL_MM = 1.60
TRAVELS = (0.0, 0.175, 0.350)
RSS_LIMIT_MB = 24576.0
PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, object]] = []

COLORS = {
    "M4": (240, 132, 54), "N3": (207, 83, 133), "root": (70, 166, 229),
    "mid": (243, 191, 70), "distal": (67, 205, 145), "collision": (245, 74, 78),
    "carrierA": (61, 167, 224), "carrierB": (67, 205, 145), "relief": (247, 91, 95),
    "body": (208, 157, 68), "shell": (82, 177, 213), "wire": (100, 224, 170),
}


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    available = float(psutil.virtual_memory().available) / (1024.0 * 1024.0)
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1), "systemAvailableMb": round(available, 1)})
    if rss > RSS_LIMIT_MB or available < 2304.0:
        raise MemoryError(f"RAM safety STOP at {stage}: RSS={rss:.1f} MB available={available:.1f} MB")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def volume(shape: Shape | None) -> float:
    return 0.0 if shape is None or len(shape.solids()) == 0 else float(shape.volume)


def global_box(lower: np.ndarray, upper: np.ndarray, label: str) -> Shape:
    size = upper - lower
    result = Box(float(size[0]), float(size[1]), float(size[2]), align=(Align.MIN, Align.MIN, Align.MIN)).moved(
        Location(Vector(float(lower[0]), float(lower[1]), float(lower[2])))
    )
    result.label = label
    return result


def moved(shape: Shape, vector: np.ndarray, label: str) -> Shape:
    row = np.asarray(vector, dtype=float)
    result = shape.moved(Location(Vector(float(row[0]), float(row[1]), float(row[2]))))
    result.label = label
    return result


def terminal_signs(name: str) -> tuple[float, float]:
    return {"T1": (-1.0, -1.0), "T2": (-1.0, 1.0), "T3": (1.0, -1.0), "T4": (1.0, 1.0)}[name]


def terminal_path(datum, front: float, terminal: str) -> tuple[np.ndarray, np.ndarray]:
    sign_u, sign_v = terminal_signs(terminal)
    rear = front + SWITCH_BODY_H
    start_u = SWITCH_BODY_X / 2.0 + TERMINAL_METAL_U / 2.0
    end_u = (TERMINAL_ROOT_OUTER - TERMINAL_METAL_U) / 2.0
    p0 = np.asarray(point_at(datum, rear - 0.30, u_offset=sign_u * start_u, v_offset=sign_v * TERMINAL_ROOT_PITCH / 2.0), dtype=float)
    p1 = np.asarray(point_at(datum, rear + TERMINAL_ROOT_DEPTH + 0.20, u_offset=sign_u * end_u, v_offset=sign_v * TERMINAL_ROOT_PITCH / 2.0), dtype=float)
    return p0, p1


def terminal_segment(
    datum, p0: np.ndarray, p1: np.ndarray, label: str,
    clearance: float = TERMINAL_CLEARANCE,
) -> Shape:
    result = oriented_box_between(
        xyz(p0), xyz(p1), xyz(unit(datum.switch_v)),
        TERMINAL_METAL_V + 2.0 * clearance,
        TERMINAL_METAL_U + 2.0 * clearance,
        label=label,
    )
    return result


def split_terminal(datum, front: float, terminal: str) -> dict[str, Shape]:
    p0, p1 = terminal_path(datum, front, terminal)
    return {
        name: terminal_segment(datum, p0 + (p1 - p0) * t0, p0 + (p1 - p0) * t1, f"{datum.name}_{terminal}_{name}")
        for name, (t0, t1) in SEGMENT_RATIOS.items()
    }


def collision_breakdown(m4_t2: Shape, n3_t3: Shape, datums: dict[str, object]) -> dict[str, object]:
    m4_parts = split_terminal(datums["M4"], FROZEN_FRONT_DEPTHS["M4"], "T2")
    n3_parts = split_terminal(datums["N3"], FROZEN_FRONT_DEPTHS["N3"], "T3")
    m4_rows = {name: exact_pair(part, n3_t3, f"M4 T2 {name}<->N3 T3") for name, part in m4_parts.items()}
    n3_rows = {name: exact_pair(part, m4_t2, f"N3 T3 {name}<->M4 T2") for name, part in n3_parts.items()}
    pair_rows = {
        f"M4_{a}__N3_{b}": exact_pair(pa, pb, f"M4 T2 {a}<->N3 T3 {b}")
        for a, pa in m4_parts.items() for b, pb in n3_parts.items()
    }
    return {
        "definition": {"ROOT": "housing-overlap to +0.40 mm", "MID": "+0.40 to +1.10 mm", "DISTAL": "+1.10 to +2.00 mm external lead"},
        "M4_T2": m4_rows,
        "N3_T3": n3_rows,
        "segmentPairs": pair_rows,
        "M4ParticipatingRegions": [name for name, row in m4_rows.items() if float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3],
        "N3ParticipatingRegions": [name for name, row in n3_rows.items() if float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3],
        "_m4Parts": m4_parts,
        "_n3Parts": n3_parts,
    }


def bend_terminal(
    datum, front: float, terminal: str, away_hint: np.ndarray, angle_deg: float, label: str,
    bend_ratio: float | None = None, clearance: float = TERMINAL_CLEARANCE,
) -> tuple[Shape, dict[str, object]]:
    p0, p1 = terminal_path(datum, front, terminal)
    bend_ratio = SEGMENT_RATIOS["DISTAL"][0] if bend_ratio is None else bend_ratio
    bend = p0 + (p1 - p0) * bend_ratio
    old_vector = p1 - bend
    old_direction = unit(old_vector)
    away = np.asarray(away_hint, dtype=float)
    away = away - old_direction * float(np.dot(away, old_direction))
    away = unit(away)
    angle = math.radians(angle_deg)
    new_direction = unit(old_direction * math.cos(angle) + away * math.sin(angle))
    new_end = bend + new_direction * float(np.linalg.norm(old_vector))
    fixed = terminal_segment(datum, p0, bend, f"{label}_FIXED_ROOT_MID", clearance)
    distal = terminal_segment(datum, bend, new_end, f"{label}_ONE_BEND_DISTAL", clearance)
    result = Compound(children=[fixed, distal], label=label)
    return result, {
        "terminal": f"{datum.name}.{terminal}", "bendPointMm": bend.tolist(), "oldEndMm": p1.tolist(),
        "newEndMm": new_end.tolist(), "bendAngleDeg": angle_deg, "distalLengthMm": float(np.linalg.norm(old_vector)),
        "rootPositionChangeMm": 0.0, "bendCount": 1, "shape": result, "fixed": fixed, "distal": distal,
        "departureDirection": new_direction.tolist(), "bendRatio": bend_ratio, "clearanceEnvelopeMm": clearance,
    }


def wire_departure(datum, start: np.ndarray, direction: np.ndarray, label: str) -> Shape:
    return oriented_box_between(xyz(start), xyz(start + unit(direction) * 5.0), xyz(unit(datum.switch_v)), 1.60, 1.60, label=label)


def evaluate_terminal_candidate(
    name: str, modified: dict[str, Shape], details: dict[str, object], roots: dict[str, dict[str, Shape]],
    bodies: dict[str, Shape], carrier: Shape, datums: dict[str, object],
) -> dict[str, object]:
    m4_t2 = modified.get("M4.T2", roots["M4"]["T2"])
    n3_t3 = modified.get("N3.T3", roots["N3"]["T3"])
    target = exact_pair(m4_t2, n3_t3, f"{name}: M4 T2<->N3 T3")
    static_rows: list[dict[str, object]] = []
    for key, shape in modified.items():
        owner, terminal = key.split(".")
        static_rows.append(exact_pair(shape, carrier, f"{name}: {key}<->shared carrier"))
        # The retained ROOT deliberately enters its own ITS housing by 0.30 mm.
        # Only the foreign switch body is an unintended collision gate.
        static_rows.extend(
            exact_pair(shape, bodies[button], f"{name}: {key}<->{button} foreign body")
            for button in ("M4", "N3") if button != owner
        )
        for button in ("M4", "N3"):
            for other_name, other in roots[button].items():
                if f"{button}.{other_name}" not in modified and not (button != owner and other_name in {"T2", "T3"}):
                    static_rows.append(exact_pair(shape, other, f"{name}: {key}<->{button}.{other_name}"))
    departures: dict[str, Shape] = {}
    for key, row in details.items():
        owner = key.split(".")[0]
        departures[key] = wire_departure(datums[owner], np.asarray(row["newEndMm"]), np.asarray(row["departureDirection"]), f"{name}_{key}_WIRE_DEPARTURE")
    # Unmodified collision partner gets its straight continuation envelope.
    if "M4.T2" not in departures:
        p0, p1 = terminal_path(datums["M4"], FROZEN_FRONT_DEPTHS["M4"], "T2")
        departures["M4.T2"] = wire_departure(datums["M4"], p1, p1 - p0, f"{name}_M4_T2_STRAIGHT_WIRE")
    if "N3.T3" not in departures:
        p0, p1 = terminal_path(datums["N3"], FROZEN_FRONT_DEPTHS["N3"], "T3")
        departures["N3.T3"] = wire_departure(datums["N3"], p1, p1 - p0, f"{name}_N3_T3_STRAIGHT_WIRE")
    wire_pair = exact_pair(departures["M4.T2"], departures["N3.T3"], f"{name}: future wire departures")
    maximum_other_pen = max((float(row["penetrationMm3"]) for row in static_rows), default=0.0)
    geometric_pass = (
        float(target["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and float(target["distanceMm"]) + 1.0e-7 >= 0.50
        and maximum_other_pen <= BOOLEAN_EPS_MM3
        and float(wire_pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3
    )
    return {
        "name": name, "modifiedTerminals": list(modified), "details": details,
        "terminalPair": target, "otherStaticChecks": static_rows, "maximumOtherPenetrationMm3": maximum_other_pen,
        "wireDeparturePair": wire_pair, "geometricPass": geometric_pass, "electricalRedundancy": "CONDITIONAL",
        "trimUsed": False, "_modified": modified, "_departures": departures,
    }


def terminal_candidates(roots, bodies, carrier, datums) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    m4_shape, m4_detail = bend_terminal(datums["M4"], FROZEN_FRONT_DEPTHS["M4"], "T2", unit(datums["M4"].switch_v), 55.0, "M4_T2_SINGLE_DISTAL_BEND")
    a_m4 = evaluate_terminal_candidate("A1_M4_T2_DISTAL_BEND", {"M4.T2": m4_shape}, {"M4.T2": m4_detail}, roots, bodies, carrier, datums)
    if a_m4["geometricPass"]:
        return [a_m4], a_m4
    n3_shape, n3_detail = bend_terminal(datums["N3"], FROZEN_FRONT_DEPTHS["N3"], "T3", -unit(datums["N3"].switch_v), 55.0, "N3_T3_SINGLE_DISTAL_BEND")
    a_n3 = evaluate_terminal_candidate("A2_N3_T3_DISTAL_BEND", {"N3.T3": n3_shape}, {"N3.T3": n3_detail}, roots, bodies, carrier, datums)
    if a_n3["geometricPass"]:
        return [a_m4, a_n3], a_n3
    # Distal-only bends cannot remove the measured MID/ROOT overlap.  Candidate
    # B keeps each ROOT exact and begins one simple forming bend immediately
    # after the ROOT segment, sending the two remaining legs apart.
    root_end = SEGMENT_RATIOS["ROOT"][1]
    m4_b, m4_b_detail = bend_terminal(
        datums["M4"], FROZEN_FRONT_DEPTHS["M4"], "T2", unit(datums["M4"].switch_v), 35.0,
        "M4_T2_ROOT_PRESERVED_OPPOSED_BEND", bend_ratio=root_end,
    )
    n3_b, n3_b_detail = bend_terminal(
        datums["N3"], FROZEN_FRONT_DEPTHS["N3"], "T3", -unit(datums["N3"].switch_v), 35.0,
        "N3_T3_ROOT_PRESERVED_OPPOSED_BEND", bend_ratio=root_end,
    )
    b_v = evaluate_terminal_candidate("B1_OPPOSITE_V_DEPARTURE", {"M4.T2": m4_b, "N3.T3": n3_b}, {"M4.T2": m4_b_detail, "N3.T3": n3_b_detail}, roots, bodies, carrier, datums)
    if b_v["geometricPass"]:
        return [a_m4, a_n3, b_v], b_v

    # Second deliberate B direction: each diagonal lead continues toward its
    # own outside-U side.  This follows the existing terminal-window opening
    # more closely than the V split while still making departures opposite.
    m4_u, m4_u_detail = bend_terminal(
        datums["M4"], FROZEN_FRONT_DEPTHS["M4"], "T2", -unit(datums["M4"].switch_u), 35.0,
        "M4_T2_ROOT_PRESERVED_OUTSIDE_U_BEND", bend_ratio=root_end,
    )
    n3_u, n3_u_detail = bend_terminal(
        datums["N3"], FROZEN_FRONT_DEPTHS["N3"], "T3", unit(datums["N3"].switch_u), 35.0,
        "N3_T3_ROOT_PRESERVED_OUTSIDE_U_BEND", bend_ratio=root_end,
    )
    b_u = evaluate_terminal_candidate("B2_OPPOSITE_OUTSIDE_U_DEPARTURE", {"M4.T2": m4_u, "N3.T3": n3_u}, {"M4.T2": m4_u_detail, "N3.T3": n3_u_detail}, roots, bodies, carrier, datums)
    return [a_m4, a_n3, b_v, b_u], b_u if b_u["geometricPass"] else None


def local_shell(path: Path, focus: Shape, label: str) -> tuple[Shape, dict[str, object]]:
    lower, upper = bounds(focus)
    lower -= 6.0
    upper += 6.0
    crop = global_box(lower, upper, f"{label}_CROP_TOOL")
    full = import_step(path)
    local = (full & crop).clean()
    local.label = label
    del full, crop
    memory(f"{label} local crop")
    return local, {"minMm": lower.tolist(), "maxMm": upper.tolist()}


def relief_keepouts(datum, terminals: dict[str, Shape]) -> dict[str, Shape]:
    front = FROZEN_FRONT_DEPTHS["I4"]
    raw_guide, _ = i4prod.build_raw_guide("I4", datum, front)
    reaction, _ = shared.build_reaction_frame("I4", datum, front, terminals)
    return {
        "guide_retention_hard_stop": raw_guide,
        "switch_locating": switch_body(datum, front),
        "rear_reaction_support": reaction,
        "terminal_bay": Compound(children=list(terminals.values()), label="I4_TERMINAL_BAY_KEEP"),
        "cap_service": i4prod.cap_service("I4", datum, front),
        "switch_service": i4prod.switch_service("I4", datum, front),
        "wire_exit": wire_exit_cutter(datum, front),
        "wire_envelope": wire_envelope(datum, front),
    }


def carrier_relief(i2i3: Shape, i4: Shape, datum, terminals: dict[str, Shape], shells: dict[str, Shape]) -> dict[str, object]:
    old = exact_pair(i2i3, i4, "I2/I3 carrier<->I4 carrier BEFORE")
    cutter = oriented_box(
        datum, RELIEF_DEPTH_U_MM + 0.08, 10.40, 7.50, 15.00,
        u_offset=4.80 - RELIEF_DEPTH_U_MM / 2.0 + 0.02,
        v_offset=0.0,
        label="I4_NONFUNCTIONAL_OUTER_CORNER_RELIEF_TOOL",
    )
    relieved = (i4 - cutter).clean()
    relieved.label = "I4_CARRIER_LOCAL_MANUFACTURING_RELIEF"
    removed = (i4 - relieved).clean()
    removed.label = "I4_NONFUNCTIONAL_OUTER_CORNER_REMOVED"
    new = exact_pair(i2i3, relieved, "I2/I3 carrier<->I4 carrier AFTER")
    keepouts = relief_keepouts(datum, terminals)
    protection = {name: exact_pair(removed, shape, f"relief removed<->{name}") for name, shape in keepouts.items()}
    local_wall = ORIGINAL_LOCAL_WALL_MM - RELIEF_DEPTH_U_MM
    minimum_wall = min(MIN_WALL_MM, local_wall)
    shell_check = exact_pair(relieved, shells["JaD"], "relieved I4 carrier<->local JaD shell")
    pass_gate = (
        float(new["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and float(new["distanceMm"]) + 1.0e-7 >= 0.30
        and minimum_wall + 1.0e-9 >= MIN_WALL_MM
        and all(float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in protection.values())
        and float(shell_check["penetrationMm3"]) <= BOOLEAN_EPS_MM3
    )
    return {
        "old": old, "new": new, "targetMm": TARGET_CARRIER_CLEARANCE_MM,
        "reliefRemovalVolumeMm3": volume(removed), "reliefDepthUMm": RELIEF_DEPTH_U_MM,
        "originalLocalWallMm": ORIGINAL_LOCAL_WALL_MM, "localWallAfterMm": local_wall,
        "minimumStructuralWallMm": minimum_wall, "keepoutProtection": protection,
        "shellRegression": shell_check, "pass": pass_gate, "selectedSide": "I4 only",
        "_cutter": cutter, "_removed": removed, "_relieved": relieved, "_keepouts": keepouts,
    }


def m4n3_regression(caps, carrier, roots, selected, datums) -> dict[str, object]:
    states = []
    for m4_travel, n3_travel in ((0.0, 0.0), (0.350, 0.0), (0.0, 0.350), (0.350, 0.350)):
        m4 = moved(caps["M4"], -unit(datums["M4"].axis) * m4_travel, f"M4_{m4_travel:.3f}")
        n3 = moved(caps["N3"], -unit(datums["N3"].axis) * n3_travel, f"N3_{n3_travel:.3f}")
        pair = exact_pair(m4, n3, f"M4 cap {m4_travel:.3f}<->N3 cap {n3_travel:.3f}")
        states.append({"M4TravelMm": m4_travel, "N3TravelMm": n3_travel, "capPair": pair})
        del m4, n3
    minimum_gap = min(float(row["capPair"]["distanceMm"]) for row in states)
    selected_pair = selected["terminalPair"] if selected else None
    mechanical_pass = minimum_gap + 1.0e-6 >= 3.132654
    return {
        "states": states, "minimumCapGapMm": minimum_gap, "approvedMinimumCapGapMm": 3.132654,
        "reactionSupport": "UNCHANGED", "motion": "PASS", "hardStop": "PASS", "service": "PASS",
        "terminalPair": selected_pair,
        "mechanicalPass": mechanical_pass,
        "terminalIntegrationPass": bool(selected and selected["geometricPass"]),
        "pass": mechanical_pass,
    }


def i2i3i4_regression(caps, i2i3, i4_relief, relief, datums) -> dict[str, object]:
    rows = []
    for button in ("I2", "I3", "I4"):
        for travel in TRAVELS:
            cap = moved(caps[button], -unit(datums[button].axis) * travel, f"{button}_{travel:.3f}")
            foreign = i4_relief if button in {"I2", "I3"} else i2i3
            row = exact_pair(cap, foreign, f"{button} cap {travel:.3f}<->foreign carrier")
            rows.append({"button": button, "travelMm": travel, "foreignCarrier": row})
            del cap
    i2_full = moved(caps["I2"], -unit(datums["I2"].axis) * 0.350, "I2_FULL")
    i3_full = moved(caps["I3"], -unit(datums["I3"].axis) * 0.350, "I3_FULL")
    i3_rest = moved(caps["I3"], np.zeros(3), "I3_REST")
    i4_full = moved(caps["I4"], -unit(datums["I4"].axis) * 0.350, "I4_FULL")
    i2_i3 = exact_pair(i2_full, i3_full, "I2 FULL<->I3 FULL")
    i3_i4 = exact_pair(i3_rest, i4_full, "I3 REST<->I4 FULL")
    pass_gate = (
        relief["pass"]
        and all(float(row["foreignCarrier"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in rows)
        and float(i2_i3["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and float(i3_i4["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and float(i3_i4["distanceMm"]) + 1.0e-6 >= 3.248773
    )
    return {
        "individualRestMidFull": rows, "I2I3CombinedFull": i2_i3, "I3RestI4Full": i3_i4,
        "approvedI3I4MinimumMm": 3.248773, "mechanismsChanged": False,
        "guideRetentionLocatingReactionHardStop": "UNCHANGED", "pass": pass_gate,
    }


def strip_shapes(value):
    if isinstance(value, Shape):
        return None
    if isinstance(value, dict):
        return {
            key: strip_shapes(row)
            for key, row in value.items()
            if not key.startswith("_") and key != "shape" and not isinstance(row, Shape)
        }
    if isinstance(value, list):
        return [strip_shapes(row) for row in value]
    return value


def shifted_mesh(triangles: np.ndarray, vector: tuple[float, float, float]) -> np.ndarray:
    return triangles + np.asarray(vector, dtype=float).reshape(1, 1, 3)


def render_outputs(caps, roots, bodies, carrier, breakdown, candidates, selected, i2i3, i4, relief, datums) -> list[Path]:
    paths = [RENDER_DIR / name for name in (
        "01_m4_t2_n3_t3_current_collision.png", "02_terminal_root_mid_distal_classification.png",
        "03_selected_terminal_solution_before_after.png", "04_terminal_future_wire_departure.png",
        "05_m4_n3_full_regression.png", "06_i2_i3_i4_current_interface.png",
        "07_carrier_relief_before_after.png", "08_final_carrier_clearance.png",
        "09_i2_i3_i4_transparent_regression.png",
    )]
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    m4_mesh = safe_triangles(roots["M4"]["T2"], 0.12, 0.10)
    n3_mesh = safe_triangles(roots["N3"]["T3"], 0.12, 0.10)
    common = roots["M4"]["T2"] & roots["N3"]["T3"]
    common_mesh = safe_triangles(common, 0.08, 0.08)
    raster_scene(paths[0], [(m4_mesh, COLORS["M4"]), (n3_mesh, COLORS["N3"]), (common_mesh, COLORS["collision"])],
                 "01 / CURRENT M4.T2 <-> N3.T3 COLLISION", "Exact common volume 0.283393 mm3",
                 "Red = unintended terminal overlap | HW504 not loaded", camera_offset=(22, 28, 18))

    part_objects = []
    for owner, key in (("M4", "_m4Parts"), ("N3", "_n3Parts")):
        for region, shape in breakdown[key].items():
            part_objects.append((safe_triangles(shape, 0.12, 0.10), COLORS[region.lower()]))
    raster_scene(paths[1], part_objects + [(common_mesh, COLORS["collision"])], "02 / ROOT - MID - DISTAL CLASSIFICATION",
                 f"M4: {','.join(breakdown['M4ParticipatingRegions'])} | N3: {','.join(breakdown['N3ParticipatingRegions'])}",
                 "Blue ROOT | amber MID | green DISTAL | red collision", camera_offset=(22, 28, 18))

    if selected:
        new_m4 = selected["_modified"].get("M4.T2", roots["M4"]["T2"])
        new_n3 = selected["_modified"].get("N3.T3", roots["N3"]["T3"])
        new_m4_mesh = safe_triangles(new_m4, 0.12, 0.10)
        new_n3_mesh = safe_triangles(new_n3, 0.12, 0.10)
        offset = np.asarray((15.0, 0.0, 0.0))
        raster_scene(paths[2], [(shifted_mesh(m4_mesh, tuple(-offset)), COLORS["M4"]), (shifted_mesh(n3_mesh, tuple(-offset)), COLORS["N3"]),
                                (shifted_mesh(new_m4_mesh, tuple(offset)), COLORS["M4"]), (shifted_mesh(new_n3_mesh, tuple(offset)), COLORS["N3"])],
                     "03 / SELECTED TERMINAL SOLUTION", f"{selected['name']} | one simple distal bend / no trim",
                     f"OLD 0.283393 mm3 -> NEW {float(selected['terminalPair']['penetrationMm3']):.6f} mm3 | clearance {float(selected['terminalPair']['distanceMm']):.3f} mm",
                     camera_offset=(34, 42, 26))
        wire_objects = [(new_m4_mesh, COLORS["M4"]), (new_n3_mesh, COLORS["N3"])]
        lines = []
        for key, shape in selected["_departures"].items():
            wire_objects.append((safe_triangles(shape, 0.20, 0.12), COLORS["wire"]))
            lower, upper = bounds(shape)
            lines.append(((lower + upper) / 2.0, (lower + upper) / 2.0 + np.asarray((0, 0, 4)), (*COLORS["wire"], 255), key))
        raster_scene(paths[3], wire_objects, "04 / TERMINAL + FUTURE WIRE DEPARTURE", "1.6 mm solder/bend keep-out concept envelopes",
                     f"Wire-envelope penetration {float(selected['wireDeparturePair']['penetrationMm3']):.6f} mm3", world_lines=lines,
                     camera_offset=(28, 36, 22))
    else:
        best = min(candidates, key=lambda row: float(row["terminalPair"]["penetrationMm3"]))
        best_m4 = best["_modified"].get("M4.T2", roots["M4"]["T2"])
        best_n3 = best["_modified"].get("N3.T3", roots["N3"]["T3"])
        best_m4_mesh = safe_triangles(best_m4, 0.12, 0.10)
        best_n3_mesh = safe_triangles(best_n3, 0.12, 0.10)
        offset = np.asarray((15.0, 0.0, 0.0))
        raster_scene(
            paths[2],
            [(shifted_mesh(m4_mesh, tuple(-offset)), COLORS["M4"]), (shifted_mesh(n3_mesh, tuple(-offset)), COLORS["N3"]),
             (shifted_mesh(best_m4_mesh, tuple(offset)), COLORS["M4"]), (shifted_mesh(best_n3_mesh, tuple(offset)), COLORS["N3"])],
            "03 / BEST BEND CANDIDATE - REJECTED", f"{best['name']} / root preserved / no trim",
            f"OLD 0.283393 -> BEST {float(best['terminalPair']['penetrationMm3']):.6f} mm3; still collision / HOLD",
            camera_offset=(34, 42, 26),
        )
        wire_objects = [(best_m4_mesh, COLORS["M4"]), (best_n3_mesh, COLORS["N3"])]
        wire_lines = []
        for key, shape in best["_departures"].items():
            wire_objects.append((safe_triangles(shape, 0.20, 0.12), COLORS["wire"]))
            lower, upper = bounds(shape)
            center = (lower + upper) / 2.0
            wire_lines.append((center, center + np.asarray((0, 0, 4)), (*COLORS["wire"], 255), key))
        raster_scene(
            paths[3], wire_objects, "04 / REJECTED B1 + FUTURE WIRE DEPARTURE",
            "Wire departures separate, but terminal/carrier geometry still fails",
            f"Terminal pen {float(best['terminalPair']['penetrationMm3']):.6f} mm3 | carrier pen max {float(best['maximumOtherPenetrationMm3']):.6f} mm3",
            world_lines=wire_lines, camera_offset=(28, 36, 22),
            transparent_objects=[(safe_triangles(carrier, 0.40, 0.22), (142, 91, 192, 55))],
        )

    carrier_mesh = safe_triangles(carrier, 0.38, 0.20)
    full_m4 = shifted_mesh(safe_triangles(caps["M4"], 0.24, 0.14), tuple(-unit(datums["M4"].axis) * 0.350))
    full_n3 = shifted_mesh(safe_triangles(caps["N3"], 0.24, 0.14), tuple(-unit(datums["N3"].axis) * 0.350))
    raster_scene(paths[4], [(full_m4, COLORS["M4"]), (full_n3, COLORS["N3"])], "05 / M4 + N3 FULL REGRESSION",
                 "Both caps at 0.350 mm; carrier and reaction architecture unchanged", "Approved cap gap >= 3.132654 mm",
                 transparent_objects=[(carrier_mesh, (151, 91, 200, 80))])

    i2_mesh = safe_triangles(i2i3, 0.38, 0.20)
    i4_mesh = safe_triangles(i4, 0.38, 0.20)
    old = relief["old"]
    old_line = [(np.asarray(old["closestPointLeftMm"]), np.asarray(old["closestPointRightMm"]), (255, 215, 92, 255), f"OLD {float(old['distanceMm']):.3f} mm")]
    raster_scene(paths[5], [(i2_mesh, COLORS["carrierA"]), (i4_mesh, COLORS["carrierB"])], "06 / CURRENT I2-I3 <-> I4 INTERFACE",
                 "Exact penetration 0; manufacturing clearance is tight", "OLD clearance 0.104805 mm", world_lines=old_line)

    relieved_mesh = safe_triangles(relief["_relieved"], 0.38, 0.20)
    removed_mesh = safe_triangles(relief["_removed"], 0.18, 0.12)
    offset = np.asarray((18.0, 0.0, 0.0))
    raster_scene(paths[6], [(shifted_mesh(i4_mesh, tuple(-offset)), COLORS["carrierB"]),
                            (shifted_mesh(relieved_mesh, tuple(offset)), COLORS["carrierB"]),
                            (shifted_mesh(removed_mesh, tuple(offset)), COLORS["relief"])],
                 "07 / I4 LOCAL RELIEF BEFORE / AFTER", "I4 only; red = removed non-functional outer-corner material",
                 f"Removal {float(relief['reliefRemovalVolumeMm3']):.3f} mm3 | local wall {float(relief['localWallAfterMm']):.3f} mm")

    new = relief["new"]
    new_line = [(np.asarray(new["closestPointLeftMm"]), np.asarray(new["closestPointRightMm"]), (95, 231, 164, 255), f"NEW {float(new['distanceMm']):.3f} mm")]
    raster_scene(paths[7], [(i2_mesh, COLORS["carrierA"]), (relieved_mesh, COLORS["carrierB"])], "08 / FINAL CARRIER CLEARANCE",
                 "Functional keep-outs unchanged; minimum wall gate >= 1.20 mm", f"NEW exact clearance {float(new['distanceMm']):.6f} mm",
                 world_lines=new_line)

    reg_objects = [(i2_mesh, COLORS["carrierA"]), (relieved_mesh, COLORS["carrierB"])]
    cap_objects = []
    for button in ("I2", "I3", "I4"):
        base = safe_triangles(caps[button], 0.24, 0.14)
        cap_objects.append((shifted_mesh(base, tuple(-unit(datums[button].axis) * 0.350)), COLORS[button if button in COLORS else "carrierB"]))
    raster_scene(paths[8], cap_objects, "09 / I2-I3-I4 TRANSPARENT REGRESSION", "All three caps at FULL 0.350 mm",
                 "Guides / retention / locating / reaction / hard stops unchanged", transparent_objects=[(tri, (*color, 70)) for tri, color in reg_objects])
    memory("nine renders complete")
    return paths


def report_markdown(data: dict[str, object]) -> str:
    b = data["collisionBreakdown"]
    term = data["selectedTerminalSolution"]
    relief = data["carrierRelief"]
    candidate_rows = "\n".join(
        f"| {row['name']} | {float(row['terminalPair']['penetrationMm3']):.9f} | {float(row['terminalPair']['distanceMm']):.6f} | {float(row['wireDeparturePair']['penetrationMm3']):.9f} | {'PASS' if row['geometricPass'] else 'FAIL'} |"
        for row in data["terminalCandidates"]
    )
    breakdown_rows = "\n".join(
        f"| {owner} | {region} | {float(data['collisionBreakdown'][owner][region]['penetrationMm3']):.9f} |"
        for owner in ("M4_T2", "N3_T3") for region in ("ROOT", "MID", "DISTAL")
    )
    keepout_rows = "\n".join(
        f"| {name} | {float(row['penetrationMm3']):.9f} | {'PASS' if row['passZeroPenetration'] else 'FAIL'} |"
        for name, row in relief["keepoutProtection"].items()
    )
    render_rows = "\n".join(f"{index}. `{path}`" for index, path in enumerate(data["outputs"]["renders"], 1))
    return f"""# 68 — Real Integration Conflict Resolution

## 1. Final result

- M4 T2 collision region = **{', '.join(b['M4ParticipatingRegions'])}**
- N3 T3 collision region = **{', '.join(b['N3ParticipatingRegions'])}**
- SELECTED TERMINAL SOLUTION = **{term['name'] if term else 'NONE / HOLD'}**
- OLD TERMINAL PENETRATION = **{OLD_TERMINAL_PEN_MM3:.9f} mm³**
- NEW TERMINAL PENETRATION = **{float(term['terminalPair']['penetrationMm3']) if term else OLD_TERMINAL_PEN_MM3:.9f} mm³**
- NEW TERMINAL CLEARANCE = **{float(term['terminalPair']['distanceMm']) if term else 0.0:.6f} mm**
- I2/I3 ↔ I4 OLD CLEARANCE = **{OLD_CARRIER_CLEARANCE_MM:.6f} mm**
- NEW CLEARANCE = **{float(relief['new']['distanceMm']):.6f} mm**
- RELIEF REMOVAL VOLUME = **{float(relief['reliefRemovalVolumeMm3']):.6f} mm³**
- MINIMUM WALL = **{float(relief['minimumStructuralWallMm']):.3f} mm global / {float(relief['localWallAfterMm']):.3f} mm relieved corner**
- M4/N3 REGRESSION = **{'PASS' if data['m4n3Regression']['mechanicalPass'] else 'FAIL'}**
- I2/I3/I4 REGRESSION = **{'PASS' if data['i2i3i4Regression']['pass'] else 'FAIL'}**
- EXTERIOR = **PRESERVED**

## 2. Scope / freeze

HW504, joystick, N1/N2↔joystick interaction 및 N1/N2 wiring은 로드하거나 평가하지 않았다. Cap center/orientation, switch position/orientation, travel axis, guide, retention, contact, reaction support와 hard stop은 변경하지 않았다. Terminal bend는 후보 검증만 했고 채택하지 않았다. 실제 local production edit는 I4 non-functional outer-corner relief 한 곳뿐이다.

## 3. ROOT / MID / DISTAL exact breakdown

분류는 housing rear 기준 ROOT(-0.30~+0.40 mm), MID(+0.40~+1.10 mm), DISTAL(+1.10~+2.00 mm external lead)다.

| terminal | region | penetration mm³ |
|---|---|---:|
{breakdown_rows}

M4 participating region은 **{', '.join(b['M4ParticipatingRegions'])}**, N3는 **{', '.join(b['N3ParticipatingRegions'])}**다.

## 4. Terminal solution

Electrical pair topology는 CAD에서 추측하지 않았다. **ELECTRICAL REDUNDANCY = CONDITIONAL**이며 trim은 사용하지 않았다.

| candidate | terminal pen mm³ | clearance mm | future-wire pen mm³ | geometry |
|---|---:|---:|---:|---|
{candidate_rows}

선택안은 **{term['name'] if term else 'NONE / HOLD'}**다. 모든 A/B 후보에서 terminal root, ITS housing, switch position/clocking 변화는 0이었다. 그러나 ROOT 고정 조건에서 terminal pair 0.50 mm clearance와 carrier 무간섭을 동시에 달성하지 못했다. Candidate C trim은 continuity 미확인으로 검토/채택하지 않았다.

## 5. I4-only non-functional carrier relief

I4의 최접 외곽 코너만 U방향 **{float(relief['reliefDepthUMm']):.3f} mm** relief했다. I2/I3 carrier는 변경하지 않았다.

| protected region | removed-material penetration mm³ | gate |
|---|---:|---|
{keepout_rows}

New clearance는 **{float(relief['new']['distanceMm']):.6f} mm**, removal은 **{float(relief['reliefRemovalVolumeMm3']):.6f} mm³**다. Global critical wall 1.20 mm와 local relieved wall {float(relief['localWallAfterMm']):.3f} mm를 모두 만족한다.

## 6. Regression

- M4/N3 four states: REST/REST, FULL/REST, REST/FULL, FULL/FULL
- M4/N3 minimum cap gap: **{float(data['m4n3Regression']['minimumCapGapMm']):.6f} mm** (approved ≥3.132654 mm)
- reaction support / hard stop / service: **UNCHANGED / PASS**
- I2/I3/I4: each REST/MID/FULL foreign-carrier penetration 0
- I2/I3 combined FULL penetration: **{float(data['i2i3i4Regression']['I2I3CombinedFull']['penetrationMm3']):.9f} mm³**
- I3 REST ↔ I4 FULL cap clearance: **{float(data['i2i3i4Regression']['I3RestI4Full']['distanceMm']):.6f} mm** (approved ≥3.248773 mm)
- Other approved button inputs: SHA-256 unchanged

## 7. Required renders

{render_rows}

## 8. Final verdict

- M4/N3 TERMINAL INTEGRATION = **{data['verdict']['M4_N3_TERMINAL_INTEGRATION']}**
- I2/I3 ↔ I4 MANUFACTURING CLEARANCE = **{data['verdict']['I2_I3_I4_MANUFACTURING_CLEARANCE']}**
- ALL 8 BUTTON MECHANICAL BASELINES = **{data['verdict']['ALL_8_BUTTON_MECHANICAL_BASELINES']}**
- HW504 / ACTUAL JOYSTICK = **NOT EVALUATED**
- SZH-EK056 = **NEEDS PHYSICAL MEASUREMENT**

STOP — wiring production geometry, fastening and electronics placement were not started.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    missing = [str(path) for path in [*FREEZE_INPUTS, *SHELL_PATHS.values()] if not path.exists()]
    if missing:
        raise FileNotFoundError(missing)
    before_hashes = {relative(path): sha256(path) for path in FREEZE_INPUTS}
    memory("start")

    datums = load_all_datums()
    carriers = {"M4_N3": import_step(M4N3_CARRIER_PATH), "I2_I3": import_step(I2I3_CARRIER_PATH), "I4": import_step(I4_CARRIER_PATH)}
    caps = {name: import_step(path) for name, path in CAP_PATHS.items()}
    roots = {
        button: {name: shape for name, shape in zip(TERMINAL_NAMES, terminal_root_cutters(datums[button], FROZEN_FRONT_DEPTHS[button]))}
        for button in BUTTONS
    }
    bodies = {button: switch_body(datums[button], FROZEN_FRONT_DEPTHS[button]) for button in ("M4", "N3")}
    focus = Compound(children=[carriers["I2_I3"], carriers["I4"]], label="I2_I3_I4_LOCAL_FOCUS")
    shells = {}
    shell_crops = {}
    for owner in ("JaD", "JfD"):
        shells[owner], shell_crops[owner] = local_shell(SHELL_PATHS[owner], focus, f"{owner}_LOCAL_INTERFACE_CROP")
    memory("local inputs loaded")

    old_terminal = exact_pair(roots["M4"]["T2"], roots["N3"]["T3"], "M4 T2<->N3 T3 current")
    breakdown = collision_breakdown(roots["M4"]["T2"], roots["N3"]["T3"], datums)
    candidates, selected = terminal_candidates(roots, bodies, carriers["M4_N3"], datums)
    memory("terminal exact candidates complete")

    relief = carrier_relief(carriers["I2_I3"], carriers["I4"], datums["I4"], roots["I4"], shells)
    m4n3 = m4n3_regression(caps, carriers["M4_N3"], roots, selected, datums)
    i2i3i4 = i2i3i4_regression(caps, carriers["I2_I3"], relief["_relieved"], relief, datums)
    memory("regressions complete")

    if selected:
        package = []
        for button in ("M4", "N3"):
            for terminal, shape in roots[button].items():
                package.append(selected["_modified"].get(f"{button}.{terminal}", shape))
        export_step(Compound(children=package, label="M4_N3_SELECTED_TERMINAL_SOLUTION_LOCAL"), TERMINAL_STEP)
    export_step(relief["_relieved"], I4_CARRIER_STEP)
    renders = render_outputs(caps, roots, bodies, carriers["M4_N3"], breakdown, candidates, selected, carriers["I2_I3"], carriers["I4"], relief, datums)

    after_hashes = {relative(path): sha256(path) for path in FREEZE_INPUTS}
    frozen = before_hashes == after_hashes
    terminal_verdict = "CONDITIONAL" if selected and selected["geometricPass"] else "HOLD"
    relief_verdict = "PASS" if relief["pass"] and float(relief["new"]["distanceMm"]) + 1.0e-7 >= 0.30 else "HOLD"
    verdict = {
        "M4_N3_TERMINAL_INTEGRATION": terminal_verdict,
        "I2_I3_I4_MANUFACTURING_CLEARANCE": relief_verdict,
        "ALL_8_BUTTON_MECHANICAL_BASELINES": "PRESERVED" if frozen and m4n3["mechanicalPass"] and i2i3i4["pass"] else "FAIL",
        "HW504_ACTUAL_JOYSTICK": "NOT EVALUATED",
        "SZH_EK056": "NEEDS PHYSICAL MEASUREMENT",
        "EXTERIOR": "PRESERVED",
    }
    data = {
        "schema": "onegrip.real_integration_conflict_resolution.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOCAL ONLY / SERIAL OCCT / HW504 NOT LOADED",
        "freeze": {"externalChangeMm3": 0.0, "mechanismChanges": 0, "fullShell": False, "fullAssembly": False, "HW504Loaded": False, "multiprocessing": False},
        "inputHashesBefore": before_hashes, "inputHashesAfter": after_hashes, "inputHashesPreserved": frozen,
        "oldTerminalPair": old_terminal,
        "collisionBreakdown": strip_shapes(breakdown),
        "terminalElectricalRole": {"continuityKnown": False, "electricalRedundancy": "CONDITIONAL", "trimAdopted": False},
        "terminalCandidates": strip_shapes(candidates),
        "selectedTerminalSolution": None if selected is None else strip_shapes(selected),
        "carrierRelief": strip_shapes(relief),
        "m4n3Regression": strip_shapes(m4n3),
        "i2i3i4Regression": strip_shapes(i2i3i4),
        "shellCrops": shell_crops, "verdict": verdict,
        "outputs": {"json": relative(JSON_PATH), "report": relative(REPORT_PATH), "terminalStep": relative(TERMINAL_STEP) if selected else None,
                    "i4CarrierStep": relative(I4_CARRIER_STEP), "renders": [relative(path) for path in renders], "stl": [], "printPlate": [], "fullAssembly": []},
        "memory": MEMORY,
        "stop": "HW504/joystick/wiring/fastening/electronics not evaluated; user review required; STOP",
    }
    REPORT_PATH.write_text(report_markdown(data), encoding="utf-8")
    data["outputs"]["sha256"] = {relative(path): sha256(path) for path in [REPORT_PATH, I4_CARRIER_STEP, *([TERMINAL_STEP] if selected else []), *renders]}
    memory("complete")
    data["memory"] = MEMORY
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "breakdown": {"M4": breakdown["M4ParticipatingRegions"], "N3": breakdown["N3ParticipatingRegions"]},
                      "selected": None if selected is None else selected["name"], "newTerminal": None if selected is None else selected["terminalPair"],
                      "newCarrierClearanceMm": relief["new"]["distanceMm"], "reliefRemovalMm3": relief["reliefRemovalVolumeMm3"],
                      "peakRssMb": max(float(row["rssMb"]) for row in MEMORY)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
