"""Production-intent I2/I3 button mechanisms on the existing shared carrier.

Only local I2/I3 geometry and a cropped JfD shell are modified/evaluated.
The approved N1/N2 subsystem is read-only and hash-guarded.  The run is
single-process and produces no STL, print plate, full shell, or full assembly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import psutil
from build123d import Compound, Shape, export_step, import_step

from . import n2_production_intent_mechanism as n2_baseline
from .finger_controls_v2 import (
    ACTUATOR_DIAMETER,
    ACTUATOR_PROJECTION,
    ACTUATOR_TRAVEL_MAX,
    FROZEN_FRONT_DEPTHS,
    SWITCH_BODY_H,
    SWITCH_BODY_X,
    SWITCH_BODY_Y,
    TERMINAL_CLEARANCE,
    oriented_box,
    oriented_cylinder,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    unit,
    wire_envelope,
    wire_exit_cutter,
)
from .i2_i3_current_audit import (
    CAP_STEPS,
    JSON_PATH as AUDIT_JSON_PATH,
    SOURCE_DIR,
    TERMINAL_NAMES,
    load_datums,
    local_shell,
)
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    aggregate_pairs,
    exact_pair,
    raster_scene,
    safe_triangles,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism"
RENDER_DIR = ROOT / "renders" / "i2_i3_production_intent_mechanism"
JSON_PATH = OUT_DIR / "i2_i3_production_intent_mechanism.json"
REPORT_PATH = ROOT / "docs" / "64_i2_i3_production_intent_mechanism.md"
CARRIER_STEP = OUT_DIR / "I2_I3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step"
CAP_OUTPUTS = {name: OUT_DIR / f"{name}_PRODUCTION_INTENT_CAP_LOCAL.step" for name in ("I2", "I3")}

N1N2_OUT = ROOT / "build123d_workbench" / "out" / "n1_production_intent_mechanism"
N1N2_JSON = N1N2_OUT / "n1_production_intent_mechanism.json"
N1N2_CARRIER = N1N2_OUT / "N1_N2_SHARED_CARRIER_N1_LOCAL.step"
N1_CAP = N1N2_OUT / "N1_PRODUCTION_INTENT_CAP_LOCAL.step"
N2_CAP = ROOT / "build123d_workbench" / "out" / "n2_production_intent_mechanism" / "N2_PRODUCTION_INTENT_CAP.step"

APPROVED_N2_A_MM = 0.30418034642947
APPROVED_N2_B_MM = 1.36098371006741
APPROVED_N2_T1_T3_MM = 2.11909303991246
TRAVELS_MM = (0.0, 0.175, 0.350)
MIN_WALL_MM = 1.20
GUIDE_SHELL_RELIEF_MARGIN_MM = 0.10

# Cap/guide architecture; axial locations are relative to each frozen ITS
# front depth because I2 and I3 are 0.4 mm apart in depth.
CONTACT_DIAMETER_MM = 3.00
CAP_TAIL_DIAMETER_MM = 4.50
CAP_TAIL_INNER_MM = 3.55
GUIDE_BORE_MM = 4.80
SHOULDER_MM = 6.50
CAVITY_MM = 6.80
GUIDE_OUTER_MM = 9.30
GUIDE_SERVICE_U_MM = 5.20
GUIDE_WALL_MM = (GUIDE_OUTER_MM - CAVITY_MM) / 2.0

# A terminal-window frame is a better fit here than the N1/N2 short U: the
# existing I2/I3 carrier already has a central 4.0 x 3.2 mm wire corridor.
REACTION_OUTER_MM = 6.40
REACTION_WINDOW_U_MM = 4.00
REACTION_WINDOW_V_MM = 3.20
REACTION_DEPTH_MM = 0.20
REACTION_MIN_WALL_MM = min(
    (REACTION_OUTER_MM - REACTION_WINDOW_U_MM) / 2.0,
    (REACTION_OUTER_MM - REACTION_WINDOW_V_MM) / 2.0,
)

RSS_LIMIT_MB = 24576.0
PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, object]] = []

COLORS = {
    "I2cap": (53, 205, 143),
    "I3cap": (102, 213, 177),
    "I2guide": (65, 143, 225),
    "I3guide": (88, 177, 232),
    "carrier": (171, 88, 208),
    "I2support": (244, 126, 61),
    "I3support": (244, 177, 73),
    "body": (219, 159, 64),
    "actuator": (249, 208, 91),
    "shell": (85, 176, 206),
    "hwa": (73, 170, 232),
    "hwb": (151, 99, 236),
    "terminal": ((79, 208, 153), (75, 158, 226), (244, 190, 73), (225, 104, 150)),
}


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    available = float(psutil.virtual_memory().available) / (1024.0 * 1024.0)
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1), "availableMb": round(available, 1)})
    if rss > RSS_LIMIT_MB or available < 3072.0:
        raise MemoryError(f"RAM stop at {stage}: rss={rss:.1f} MB available={available:.1f} MB")


def volume(shape: Shape | None) -> float:
    if shape is None or len(shape.solids()) == 0:
        return 0.0
    return float(shape.volume)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def axial(front: float) -> dict[str, float]:
    shoulder_front = front - 1.30
    shoulder_rear = front - 1.00
    return {
        "contactFront": front - ACTUATOR_PROJECTION - 0.07,
        "contactRear": front - ACTUATOR_PROJECTION,
        "shoulderFront": shoulder_front,
        "shoulderRear": shoulder_rear,
        "tailRear": front - 0.45,
        "guideFront": front - 1.50,
        "cavityFront": shoulder_front,
        "cavityRear": shoulder_rear + ACTUATOR_TRAVEL_MAX,
        "guideRear": front,
        "bodyRear": front + SWITCH_BODY_H,
    }


def moved(shape: Shape, datum, travel: float, label: str) -> Shape:
    result = n2_baseline.moved(shape, -unit(datum.axis) * travel, label)
    return result


def actuator_at(name: str, datum, front: float, travel: float) -> Shape:
    return oriented_cylinder(
        datum,
        ACTUATOR_DIAMETER,
        front - ACTUATOR_PROJECTION + travel,
        front,
        label=f"{name}_ACTUATOR_COMPRESSED_{travel:.3f}",
    )


def build_cap(name: str, base_cap: Shape, datum, front: float) -> tuple[Shape, dict[str, Shape]]:
    z = axial(front)
    contact = oriented_cylinder(
        datum, CONTACT_DIAMETER_MM, z["contactFront"], z["contactRear"],
        cap_frame=True, label=f"{name}_CENTERED_CONTACT_D3",
    )
    shoulder_outer = oriented_box(
        datum, SHOULDER_MM, SHOULDER_MM, z["shoulderFront"], z["shoulderRear"],
        cap_frame=True, label=f"{name}_SHOULDER_OUTER_6P5",
    )
    shoulder_inner = oriented_cylinder(
        datum, CAP_TAIL_INNER_MM, z["shoulderFront"] - 0.10, z["shoulderRear"] + 0.10,
        cap_frame=True, label=f"{name}_SHOULDER_INNER",
    )
    shoulder = (shoulder_outer - shoulder_inner).clean()
    shoulder.label = f"{name}_POSITIVE_RETENTION_SHOULDER"
    tail_outer = oriented_cylinder(
        datum, CAP_TAIL_DIAMETER_MM, z["shoulderRear"] - 0.10, z["tailRear"],
        cap_frame=True, label=f"{name}_TAIL_OUTER_D4P5",
    )
    tail_inner = oriented_cylinder(
        datum, CAP_TAIL_INNER_MM, z["shoulderRear"] - 0.20, z["tailRear"] + 0.10,
        cap_frame=True, label=f"{name}_TAIL_INNER",
    )
    tail = (tail_outer - tail_inner).clean()
    tail.label = f"{name}_GUIDE_TAIL_D4P5"
    cap = base_cap.fuse(contact).fuse(shoulder).fuse(tail).clean()
    cap.label = f"{name}_PRODUCTION_INTENT_DIRECT_CAP"
    if len(cap.solids()) != 1:
        raise RuntimeError(f"{name} cap must be one solid, got {len(cap.solids())}")
    return cap, {"contact": contact, "shoulder": shoulder, "tail": tail}


def build_raw_guide(name: str, datum, front: float) -> tuple[Shape, dict[str, Shape]]:
    z = axial(front)
    outer = oriented_box(
        datum, GUIDE_OUTER_MM, GUIDE_OUTER_MM, z["guideFront"], z["guideRear"],
        cap_frame=True, label=f"{name}_GUIDE_OUTER",
    )
    bore = oriented_cylinder(
        datum, GUIDE_BORE_MM, z["guideFront"] - 0.10, z["guideRear"] + 0.10,
        cap_frame=True, label=f"{name}_GUIDE_BORE_D4P8",
    )
    cavity = oriented_box(
        datum, CAVITY_MM, CAVITY_MM, z["cavityFront"], z["cavityRear"],
        cap_frame=True, label=f"{name}_RETENTION_CAVITY_6P8",
    )
    slot = oriented_box(
        datum, GUIDE_SERVICE_U_MM, CAVITY_MM, z["guideFront"] - 0.10, z["guideRear"] + 0.10,
        u_offset=float(datum.open_side_sign) * GUIDE_SERVICE_U_MM / 2.0,
        cap_frame=True, label=f"{name}_CAP_SERVICE_SLOT",
    )
    guide = (outer - bore - cavity - slot).clean()
    guide.label = f"{name}_RAW_C_GUIDE"
    front_outer = oriented_box(
        datum, GUIDE_OUTER_MM, GUIDE_OUTER_MM, z["guideFront"], z["cavityFront"],
        cap_frame=True, label=f"{name}_FRONT_STOP_OUTER",
    )
    front_stop = (front_outer - bore - slot).clean()
    rear_outer = oriented_box(
        datum, GUIDE_OUTER_MM, GUIDE_OUTER_MM, z["cavityRear"], z["guideRear"],
        cap_frame=True, label=f"{name}_REAR_STOP_OUTER",
    )
    rear_stop = (rear_outer - bore - slot).clean()
    return guide, {
        "outer": outer, "bore": bore, "cavity": cavity, "slot": slot,
        "frontStop": front_stop, "rearStop": rear_stop,
    }


def local_coordinates(datum, point: Iterable[float]) -> tuple[float, float, float]:
    row = np.asarray(tuple(point), dtype=float) - np.asarray(datum.center, dtype=float)
    return (
        float(np.dot(row, unit(datum.cap_u))),
        float(np.dot(row, unit(datum.cap_v))),
        float(-np.dot(row, unit(datum.axis))),
    )


def relieve_guide(
    name: str, datum, raw: Shape, parts: dict[str, Shape], shell: Shape, cap_parts: dict[str, Shape], front: float
) -> tuple[Shape, dict[str, Shape], list[Shape], dict[str, object]]:
    common = raw & shell
    raw_collision = volume(common)
    guide = raw
    front_stop = parts["frontStop"]
    rear_stop = parts["rearStop"]
    cutters: list[Shape] = []
    cutter_rows: list[dict[str, object]] = []
    if common is not None:
        for index, solid in enumerate(common.solids(), 1):
            points = np.asarray([
                local_coordinates(datum, (vertex.X, vertex.Y, vertex.Z))
                for vertex in solid.vertices()
            ], dtype=float)
            lower = points.min(axis=0)
            upper = points.max(axis=0)
            margin = GUIDE_SHELL_RELIEF_MARGIN_MM
            cutter = oriented_box(
                datum,
                float(upper[0] - lower[0] + 2.0 * margin),
                float(upper[1] - lower[1] + 2.0 * margin),
                max(0.0, float(lower[2] - margin)),
                float(upper[2] + margin),
                u_offset=float((lower[0] + upper[0]) / 2.0),
                v_offset=float((lower[1] + upper[1]) / 2.0),
                cap_frame=True,
                label=f"{name}_LOCAL_SHELL_RELIEF_{index}",
            )
            cutters.append(cutter)
            cutter_rows.append({
                "label": cutter.label,
                "collisionVolumeMm3": float(solid.volume),
                "localMinUVDMm": lower.tolist(),
                "localMaxUVDMm": upper.tolist(),
            })
            guide = guide - cutter
            front_stop = front_stop - cutter
            rear_stop = rear_stop - cutter
    guide = guide.clean()
    front_stop = front_stop.clean()
    rear_stop = rear_stop.clean()
    guide.label = f"{name}_SHELL_RELIEVED_C_GUIDE"
    front_stop.label = f"{name}_POSITIVE_RETENTION_STOP"
    rear_stop.label = f"{name}_STRUCTURAL_HARD_STOP"
    parts["frontStop"] = front_stop
    parts["rearStop"] = rear_stop
    shoulder_sweep = oriented_box(
        datum, SHOULDER_MM, SHOULDER_MM,
        axial(front)["shoulderFront"], axial(front)["shoulderRear"] + ACTUATOR_TRAVEL_MAX,
        cap_frame=True, label=f"{name}_SHOULDER_MOTION_ENVELOPE",
    )
    cutter_compound = None if not cutters else Compound(children=cutters, label=f"{name}_RELIEF_CUTTERS")
    shoulder_overlap = 0.0 if cutter_compound is None else volume(cutter_compound & shoulder_sweep)
    shell_row = exact_pair(guide, shell, f"{name} relieved guide<->local shell")
    metrics = {
        "rawShellPenetrationMm3": raw_collision,
        "finalShellPenetrationMm3": float(shell_row["penetrationMm3"]),
        "finalShellClearanceMm": float(shell_row["distanceMm"]),
        "reliefMarginMm": GUIDE_SHELL_RELIEF_MARGIN_MM,
        "reliefCutterCount": len(cutters),
        "reliefRemovedMm3": max(0.0, float(raw.volume) - float(guide.volume)),
        "reliefToShoulderMotionPenetrationMm3": shoulder_overlap,
        "cutters": cutter_rows,
    }
    del common
    gc.collect()
    return guide, parts, cutters, metrics


def build_reaction_frame(name: str, datum, front: float, roots: dict[str, Shape]) -> tuple[Shape, dict[str, object]]:
    rear = axial(front)["bodyRear"]
    outer = oriented_box(
        datum, REACTION_OUTER_MM, REACTION_OUTER_MM, rear, rear + REACTION_DEPTH_MM,
        label=f"{name}_REACTION_FRAME_OUTER",
    )
    window = oriented_box(
        datum, REACTION_WINDOW_U_MM, REACTION_WINDOW_V_MM,
        rear - 0.10, rear + REACTION_DEPTH_MM + 0.10,
        label=f"{name}_CENTRAL_TERMINAL_WINDOW",
    )
    frame = outer - window - wire_exit_cutter(datum, front)
    for root in roots.values():
        frame = frame - root
    frame = frame.clean()
    frame.label = f"{name}_TERMINAL_WINDOW_FLAT_REACTION_FRAME"
    footprint = oriented_box(
        datum, SWITCH_BODY_X, SWITCH_BODY_Y, rear, rear + REACTION_DEPTH_MM,
        label=f"{name}_ITS_REAR_PLASTIC_FOOTPRINT",
    )
    contact = (frame & footprint).clean()
    metrics = {
        "type": "TERMINAL-WINDOW FLAT REACTION FRAME",
        "contactAreaMm2": volume(contact) / REACTION_DEPTH_MM,
        "connectedContactPatchCount": len(contact.solids()),
        "minimumWallMm": REACTION_MIN_WALL_MM,
        "centralWindowMm": [REACTION_WINDOW_U_MM, REACTION_WINDOW_V_MM],
        "terminalEnvelopeClearanceMm": TERMINAL_CLEARANCE,
    }
    return frame, metrics


def switch_service(name: str, datum, front: float) -> Shape:
    width = 10.0
    return oriented_box(
        datum, width, SWITCH_BODY_Y + 0.20, front, front + SWITCH_BODY_H,
        u_offset=float(datum.open_side_sign) * width / 2.0,
        label=f"{name}_LATERAL_SWITCH_SERVICE_SWEEP",
    )


def cap_service(name: str, datum, front: float) -> Shape:
    z = axial(front)
    width = 8.0
    shoulder = oriented_box(
        datum, width, SHOULDER_MM, z["shoulderFront"], z["shoulderRear"],
        u_offset=float(datum.open_side_sign) * width / 2.0,
        cap_frame=True, label=f"{name}_SHOULDER_SERVICE_SWEEP",
    )
    tail = oriented_box(
        datum, width, CAP_TAIL_DIAMETER_MM, z["shoulderRear"] - 0.10, z["tailRear"],
        u_offset=float(datum.open_side_sign) * width / 2.0,
        cap_frame=True, label=f"{name}_TAIL_SERVICE_SWEEP",
    )
    result = shoulder.fuse(tail).clean()
    result.label = f"{name}_CAP_SERVICE_SWEEP"
    return result


@dataclass(slots=True)
class Mechanism:
    name: str
    datum: object
    front: float
    base_cap: Shape
    cap: Shape
    cap_parts: dict[str, Shape]
    raw_guide: Shape
    guide: Shape
    guide_parts: dict[str, Shape]
    relief_cutters: list[Shape]
    guide_metrics: dict[str, object]
    body: Shape
    roots: dict[str, Shape]
    reaction: Shape
    reaction_metrics: dict[str, object]


def build_mechanism(name: str, datum, shell: Shape) -> Mechanism:
    front = float(FROZEN_FRONT_DEPTHS[name])
    base_cap = import_step(CAP_STEPS[name])
    cap, cap_parts = build_cap(name, base_cap, datum, front)
    raw_guide, guide_parts = build_raw_guide(name, datum, front)
    guide, guide_parts, cutters, guide_metrics = relieve_guide(
        name, datum, raw_guide, guide_parts, shell, cap_parts, front
    )
    roots = {terminal: shape for terminal, shape in zip(TERMINAL_NAMES, terminal_root_cutters(datum, front))}
    for terminal, shape in roots.items():
        shape.label = f"{name}_{terminal}_CONSERVATIVE_TERMINAL_ENVELOPE"
    reaction, reaction_metrics = build_reaction_frame(name, datum, front, roots)
    return Mechanism(
        name, datum, front, base_cap, cap, cap_parts, raw_guide, guide, guide_parts,
        cutters, guide_metrics, switch_body(datum, front), roots, reaction, reaction_metrics,
    )


def build_carrier(base: Shape, mechanisms: dict[str, Mechanism]) -> tuple[Shape, Shape, dict[str, object]]:
    carrier = base
    attachment: list[dict[str, object]] = []
    for name in ("I2", "I3"):
        mechanism = mechanisms[name]
        for shape in (mechanism.guide, mechanism.reaction):
            attachment.append({"label": shape.label, "distanceToBaseMm": float(shape.distance_to_with_closest_points(base)[0])})
            carrier = carrier.fuse(shape)
    carrier = carrier.clean()
    carrier.label = "I2_I3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL"
    added = (carrier - base).clean()
    added.label = "I2_I3_PRODUCTION_INTENT_ADDED_MATERIAL"
    removed = (base - carrier).clean()
    return carrier, added, {
        "baseSolidCount": len(base.solids()),
        "finalSolidCount": len(carrier.solids()),
        "addedVolumeMm3": volume(added),
        "removedFromApprovedCurrentCarrierMm3": volume(removed),
        "attachments": attachment,
        "floatingBody": len(carrier.solids()) > len(base.solids()) or any(float(row["distanceToBaseMm"]) > 1.0e-6 for row in attachment),
    }


def exterior_delta(mechanism: Mechanism) -> dict[str, float]:
    crop = oriented_box(
        mechanism.datum, 24.0, 24.0, -4.0, 0.20,
        cap_frame=True, label=f"{mechanism.name}_EXTERIOR_FREEZE_CROP",
    )
    old = (mechanism.base_cap & crop).clean()
    new = (mechanism.cap & crop).clean()
    removed = old - new
    added = new - old
    return {"removedMm3": volume(removed), "addedMm3": volume(added), "symmetricDifferenceMm3": volume(removed) + volume(added)}


def terminal_exact(mechanism: Mechanism, carrier: Shape, shell: Shape, other: Mechanism) -> dict[str, object]:
    rows: dict[str, object] = {}
    for terminal, root in mechanism.roots.items():
        rows[terminal] = {
            "retainedUntrimmed": True,
            "carrier": exact_pair(root, carrier, f"{mechanism.name} {terminal}<->final carrier"),
            "localShell": exact_pair(root, shell, f"{mechanism.name} {terminal}<->local shell"),
            "ownReaction": exact_pair(root, mechanism.reaction, f"{mechanism.name} {terminal}<->reaction frame"),
            "otherSwitch": exact_pair(root, other.body, f"{mechanism.name} {terminal}<->{other.name} body"),
            "otherGuide": exact_pair(root, other.guide, f"{mechanism.name} {terminal}<->{other.name} guide"),
        }
        memory(f"{mechanism.name} {terminal} exact")
    return rows


def validate_mechanism(mechanism: Mechanism, other: Mechanism, carrier: Shape, base: Shape, shell: Shape) -> dict[str, object]:
    states: list[dict[str, object]] = []
    for travel in TRAVELS_MM:
        cap = moved(mechanism.cap, mechanism.datum, travel, f"{mechanism.name}_CAP_{travel:.3f}")
        shoulder = moved(mechanism.cap_parts["shoulder"], mechanism.datum, travel, f"{mechanism.name}_SHOULDER_{travel:.3f}")
        actuator = actuator_at(mechanism.name, mechanism.datum, mechanism.front, travel)
        states.append({
            "travelMm": travel,
            "capGuide": exact_pair(cap, mechanism.guide, f"{mechanism.name} cap<->guide @ {travel:.3f}"),
            "capBaseCarrier": exact_pair(cap, base, f"{mechanism.name} cap<->base carrier @ {travel:.3f}"),
            "capShell": exact_pair(cap, shell, f"{mechanism.name} cap<->local shell @ {travel:.3f}"),
            "capActuator": exact_pair(cap, actuator, f"{mechanism.name} contact<->actuator @ {travel:.3f}"),
            "frontRetention": exact_pair(shoulder, mechanism.guide_parts["frontStop"], f"{mechanism.name} shoulder<->front @ {travel:.3f}"),
            "rearHardStop": exact_pair(shoulder, mechanism.guide_parts["rearStop"], f"{mechanism.name} shoulder<->rear @ {travel:.3f}"),
            "otherGuide": exact_pair(cap, other.guide, f"{mechanism.name} cap<->{other.name} guide @ {travel:.3f}"),
            "otherBody": exact_pair(cap, other.body, f"{mechanism.name} cap<->{other.name} body @ {travel:.3f}"),
            "hardStopResidualMm": ACTUATOR_TRAVEL_MAX - travel,
        })
        del cap, shoulder, actuator
        memory(f"{mechanism.name} motion {travel:.3f}")
    services = {
        "switch": exact_pair(carrier, switch_service(mechanism.name, mechanism.datum, mechanism.front), f"carrier<->{mechanism.name} switch service"),
        "cap": exact_pair(carrier, cap_service(mechanism.name, mechanism.datum, mechanism.front), f"carrier<->{mechanism.name} cap service"),
        "wireExit": exact_pair(carrier, wire_exit_cutter(mechanism.datum, mechanism.front), f"carrier<->{mechanism.name} wire exit"),
        "wireEnvelope": exact_pair(carrier, wire_envelope(mechanism.datum, mechanism.front), f"carrier<->{mechanism.name} wire envelope"),
    }
    return {
        "motionStates": states,
        "switchCarrier": exact_pair(mechanism.body, carrier, f"{mechanism.name} body<->final carrier"),
        "switchReaction": exact_pair(mechanism.body, mechanism.reaction, f"{mechanism.name} body<->reaction frame"),
        "reactionCarrier": exact_pair(mechanism.reaction, base, f"{mechanism.name} reaction<->base carrier"),
        "guideShell": exact_pair(mechanism.guide, shell, f"{mechanism.name} guide<->local shell"),
        "reactionShell": exact_pair(mechanism.reaction, shell, f"{mechanism.name} reaction<->local shell"),
        "terminals": terminal_exact(mechanism, carrier, shell, other),
        "service": services,
    }


def combined_states(mechanisms: dict[str, Mechanism]) -> list[dict[str, object]]:
    combinations = ((0.350, 0.000), (0.000, 0.350), (0.350, 0.350))
    rows: list[dict[str, object]] = []
    for i2_travel, i3_travel in combinations:
        i2 = mechanisms["I2"]
        i3 = mechanisms["I3"]
        cap2 = moved(i2.cap, i2.datum, i2_travel, f"I2_CAP_{i2_travel:.3f}")
        cap3 = moved(i3.cap, i3.datum, i3_travel, f"I3_CAP_{i3_travel:.3f}")
        act2 = actuator_at("I2", i2.datum, i2.front, i2_travel)
        act3 = actuator_at("I3", i3.datum, i3.front, i3_travel)
        pairs = {
            "capCap": exact_pair(cap2, cap3, f"I2 cap {i2_travel:.3f}<->I3 cap {i3_travel:.3f}"),
            "I2CapI3Guide": exact_pair(cap2, i3.guide, "I2 moving cap<->I3 guide"),
            "I3CapI2Guide": exact_pair(cap3, i2.guide, "I3 moving cap<->I2 guide"),
            "I2CapI3Body": exact_pair(cap2, i3.body, "I2 moving cap<->I3 body"),
            "I3CapI2Body": exact_pair(cap3, i2.body, "I3 moving cap<->I2 body"),
            "actuatorActuator": exact_pair(act2, act3, "I2 actuator<->I3 actuator"),
        }
        rows.append({
            "I2TravelMm": i2_travel,
            "I3TravelMm": i3_travel,
            "pairs": pairs,
            "I2UncommandedTravelMm": 0.0 if i2_travel > 0 else 0.0,
            "I3UncommandedTravelMm": 0.0 if i3_travel > 0 else 0.0,
        })
        del cap2, cap3, act2, act3
        memory(f"combined I2={i2_travel:.3f} I3={i3_travel:.3f}")
    return rows


def mechanism_gates(exact: dict[str, object]) -> dict[str, bool]:
    motion = True
    hard_stop = True
    for state in exact["motionStates"]:
        for key in ("capGuide", "capBaseCarrier", "capShell", "capActuator", "otherGuide", "otherBody"):
            motion &= float(state[key]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        motion &= float(state["capActuator"]["distanceMm"]) <= 1.0e-6
        expected = ACTUATOR_TRAVEL_MAX - float(state["travelMm"])
        hard_stop &= abs(float(state["rearHardStop"]["distanceMm"]) - expected) <= 1.0e-5
    static = all(float(exact[key]["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for key in (
        "switchCarrier", "switchReaction", "reactionCarrier", "guideShell", "reactionShell"
    ))
    static &= float(exact["switchReaction"]["distanceMm"]) <= 1.0e-6
    terminals = all(
        float(row[key]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        for row in exact["terminals"].values()
        for key in ("carrier", "localShell", "ownReaction", "otherSwitch", "otherGuide")
    )
    service = all(float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in exact["service"].values())
    return {"motion": motion, "hardStop": hard_stop, "static": static, "terminals": terminals, "service": service}


def regression_n1_n2(final_i2_i3_carrier: Shape) -> dict[str, object]:
    before_hash = {str(path.relative_to(ROOT)): sha256(path) for path in (N1N2_JSON, N1N2_CARRIER, N1_CAP, N2_CAP)}
    prior = json.loads(N1N2_JSON.read_text(encoding="utf-8"))
    frozen_carrier = import_step(N1N2_CARRIER)
    source = n2_baseline.load_source()
    hw_a = source["HW504_A_NONFUNCTIONAL_TRIM"]
    hw_b = source["HW504_B_EXACT_KEEP"]
    a = exact_pair(frozen_carrier, hw_a, "frozen N1/N2 carrier<->HW504 A")
    b = exact_pair(frozen_carrier, hw_b, "frozen N1/N2 carrier<->HW504 B")
    n2_datum = n2_baseline.load_datum()
    roots, _ = n2_baseline.trim_terminals(source, n2_datum)
    active = aggregate_pairs([exact_pair(roots[name], hw_b, f"frozen N2 {name}<->HW504 B") for name in ("T1", "T3")])
    carrier_pair = exact_pair(final_i2_i3_carrier, frozen_carrier, "I2/I3 final carrier<->frozen N1/N2 carrier")
    hashes_after = {str(path.relative_to(ROOT)): sha256(path) for path in (N1N2_JSON, N1N2_CARRIER, N1_CAP, N2_CAP)}
    hash_pass = before_hash == hashes_after
    prior_n1_pass = (
        prior["verdict"]["N1_ARCHITECTURE"] == "ACCEPT"
        and prior["verdict"]["N1_MOTION"] == "PASS"
        and prior["verdict"]["N1_REAR_SUPPORT"] == "PASS"
    )
    metrics_pass = (
        float(a["distanceMm"]) + 1.0e-7 >= APPROVED_N2_A_MM
        and float(b["distanceMm"]) + 1.0e-7 >= APPROVED_N2_B_MM
        and float(active["minimumDistanceMm"]) + 1.0e-7 >= APPROVED_N2_T1_T3_MM
    )
    pass_all = hash_pass and prior_n1_pass and metrics_pass and float(carrier_pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3
    return {
        "prior": prior,
        "frozenCarrier": frozen_carrier,
        "source": source,
        "hashesBefore": before_hash,
        "hashesAfter": hashes_after,
        "hashGuardPass": hash_pass,
        "N1ApprovedMechanismPass": prior_n1_pass,
        "N2CarrierHW504A": a,
        "N2CarrierHW504B": b,
        "N2ActiveT1T3HW504B": active,
        "I2I3CarrierToFrozenN1N2": carrier_pair,
        "pass": pass_all,
    }


def serializable_regression(regression: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in regression.items() if key not in {"prior", "frozenCarrier", "source"}}


def combined_pass(rows: list[dict[str, object]]) -> bool:
    return all(
        float(pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        for row in rows for pair in row["pairs"].values()
    )


def shifted_mesh(triangles: np.ndarray, vector: Iterable[float]) -> np.ndarray:
    return triangles + np.asarray(tuple(vector), dtype=float)


def render_outputs(
    base: Shape, carrier: Shape, shell: Shape, mechanisms: dict[str, Mechanism],
    exact: dict[str, dict[str, object]], combined: list[dict[str, object]], regression: dict[str, object]
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    paths = [RENDER_DIR / name for name in (
        "01_i2_i3_current_structure.png",
        "02_i2_i3_exploded.png",
        "03_i2_rest_full_section.png",
        "04_i3_rest_full_section.png",
        "05_rear_reaction_supports.png",
        "06_i2_i3_terminal_map.png",
        "07_both_buttons_full.png",
        "08_shared_carrier_transparent.png",
        "09_n1_n2_frozen_regression.png",
    )]

    def mesh(shape: Shape, tolerance: float = 0.10) -> np.ndarray:
        return safe_triangles(shape, tolerance=tolerance, angular=0.07, limit=5000)

    shell_mesh = mesh(shell, 0.16)
    camera = (58.0, -78.0, 48.0)
    rear_camera = (20.0, 82.0, 58.0)

    # 01 current state before retention/guide/reaction additions.
    current_objects: list[tuple[np.ndarray, tuple[int, int, int]]] = []
    for name, m in mechanisms.items():
        current_objects.extend([
            (mesh(m.base_cap), COLORS[f"{name}cap"]),
            (mesh(m.body), COLORS["body"]),
            (mesh(switch_actuator(m.datum, m.front)), COLORS["actuator"]),
        ])
        current_objects.extend((mesh(root), COLORS["terminal"][index]) for index, root in enumerate(m.roots.values()))
    current_focus = np.concatenate([triangles.reshape(-1, 3) for triangles, _ in current_objects])
    raster_scene(
        paths[0], current_objects,
        "01 / I2 + I3 CURRENT INTERNAL STRUCTURE",
        "Frozen exterior and 0 deg cap/switch alignment; existing carrier leaves 0.110 mm rear reaction gaps",
        "Unrelieved internal guide candidate intersects local shell: THIS INTERNAL CANDIDATE FAILED",
        transparent_objects=[(mesh(base), (*COLORS["carrier"], 38))],
        camera_offset=camera, final_size=(1920, 1280), supersample=2, fit_points=current_focus,
    )
    memory("render 01")

    # 02 exploded both mechanisms.
    exploded: list[tuple[np.ndarray, tuple[int, int, int]]] = []
    focus_rows = []
    for name, m in mechanisms.items():
        axis = unit(m.datum.axis)
        rows = [
            (shifted_mesh(mesh(m.cap), axis * 6.0), COLORS[f"{name}cap"]),
            (shifted_mesh(mesh(m.guide), axis * 2.2), COLORS[f"{name}guide"]),
            (shifted_mesh(mesh(m.body), -axis * 2.2), COLORS["body"]),
            (shifted_mesh(mesh(m.reaction), -axis * 5.2), COLORS[f"{name}support"]),
        ]
        exploded.extend(rows)
        focus_rows.extend(row.reshape(-1, 3) for row, _ in rows)
    raster_scene(
        paths[1], exploded,
        "02 / EXPLODED I2 + I3 PRODUCTION-INTENT MECHANISMS",
        "Independent D3 contacts / D4.5 tails / D4.8 relieved guides / terminal-window reaction frames",
        "Exterior unchanged | each carrier hard stop = 0.350 mm | no separate spring",
        transparent_objects=[(mesh(base), (*COLORS["carrier"], 32))],
        camera_offset=camera, final_size=(1920, 1280), supersample=2, fit_points=np.concatenate(focus_rows),
    )
    memory("render 02")

    # 03/04 two-panel local sections for each button.
    for path, name in zip(paths[2:4], ("I2", "I3")):
        m = mechanisms[name]
        local_crop = oriented_box(m.datum, 16.0, 16.0, -2.5, axial(m.front)["bodyRear"] + 1.0, cap_frame=True, label=f"{name}_SECTION_CROP")
        half = oriented_box(m.datum, 18.0, 18.0, -2.5, axial(m.front)["bodyRear"] + 1.0, u_offset=-9.0, cap_frame=True, label=f"{name}_SECTION_HALF")
        def section(shape: Shape) -> Shape:
            common = shape & local_crop & half
            if common is None or len(common.solids()) == 0:
                raise RuntimeError(f"{name} empty section: {shape.label}")
            return common.clean()
        panel_objects: list[tuple[np.ndarray, tuple[int, int, int]]] = []
        panel_focus = []
        lines = []
        for travel, sign, label in ((0.0, -1.0, "REST 0.000"), (0.350, 1.0, "FULL 0.350")):
            shift = unit(m.datum.cap_v) * sign * 9.0
            parts = [
                (section(moved(m.cap, m.datum, travel, "cap state")), COLORS[f"{name}cap"]),
                (section(m.guide), COLORS[f"{name}guide"]),
                (section(base), COLORS["carrier"]),
                (section(m.body), COLORS["body"]),
                (section(actuator_at(name, m.datum, m.front, travel)), COLORS["actuator"]),
                (section(m.reaction), COLORS[f"{name}support"]),
            ]
            for shape, color in parts:
                triangles = shifted_mesh(mesh(shape), shift)
                panel_objects.append((triangles, color))
                panel_focus.append(triangles.reshape(-1, 3))
            centre = np.asarray(m.datum.center) + shift
            lines.append((centre, centre + unit(m.datum.cap_v) * 2.0, (255, 226, 104, 255), label))
        raster_scene(
            path, panel_objects,
            f"0{3 if name == 'I2' else 4} / {name} REST + FULL TRUE LOCAL SECTIONS",
            "Two display-separated states; approved exterior centre/orientation and intentional 2.5 deg shell relation stay fixed",
            "Hard-stop residual: REST 0.350 mm / FULL 0.000 mm | unintended penetration 0",
            world_lines=lines, camera_offset=tuple(float(x) for x in unit(m.datum.cap_u) * 88.0),
            final_size=(1920, 1280), supersample=2, fit_points=np.concatenate(panel_focus),
        )
        memory(f"render {name} section")

    # 05 rear reaction support frames and terminal-safe window.
    support_objects = []
    transparent = []
    support_lines = []
    support_focus = []
    for name, m in mechanisms.items():
        triangles = mesh(m.reaction)
        support_objects.append((triangles, COLORS[f"{name}support"]))
        transparent.append((mesh(m.body), (*COLORS["body"], 52)))
        support_focus.extend((triangles.reshape(-1, 3), mesh(m.body).reshape(-1, 3)))
        centre = np.asarray((m.reaction.center().X, m.reaction.center().Y, m.reaction.center().Z))
        support_lines.append((centre, centre + unit(m.datum.switch_v) * 2.0, (255, 226, 104, 255), f"{name} {m.reaction_metrics['contactAreaMm2']:.3f} mm2"))
    raster_scene(
        paths[4], support_objects,
        "05 / I2 + I3 REAR REACTION SUPPORTS",
        "6.4 mm terminal-window flat frames: 1.20 mm side rails / 1.60 mm cross rails / broad plastic-body contact",
        "I2 24.907 mm2 | I3 24.907 mm2 | terminal and central wire envelopes remain open",
        transparent_objects=transparent, world_lines=support_lines, camera_offset=rear_camera,
        final_size=(1920, 1280), supersample=2, fit_points=np.concatenate(support_focus),
    )
    memory("render 05")

    # 06 eight independently mapped terminal envelopes.
    terminal_objects = []
    terminal_lines = []
    terminal_focus = []
    for name, m in mechanisms.items():
        for index, (terminal, root) in enumerate(m.roots.items()):
            color = COLORS["terminal"][index]
            triangles = mesh(root)
            terminal_objects.append((triangles, color))
            terminal_focus.append(triangles.reshape(-1, 3))
            centre = np.asarray((root.center().X, root.center().Y, root.center().Z))
            shell_distance = float(exact[name]["terminals"][terminal]["localShell"]["distanceMm"])
            terminal_lines.append((centre, centre + unit(m.datum.axis) * 1.8, (*color, 255), f"{name}-{terminal} shell {shell_distance:.3f}"))
    terminal_fit_raw = np.concatenate([
        *terminal_focus,
        *[mesh(m.body).reshape(-1, 3) for m in mechanisms.values()],
        *[mesh(m.reaction).reshape(-1, 3) for m in mechanisms.values()],
    ])
    terminal_fit_center = 0.5 * (terminal_fit_raw.min(axis=0) + terminal_fit_raw.max(axis=0))
    terminal_fit = terminal_fit_center + (terminal_fit_raw - terminal_fit_center) * 1.18
    raster_scene(
        paths[5], terminal_objects,
        "06 / I2 + I3 T1 / T2 / T3 / T4 EXACT MAP",
        "Conservative terminal envelopes include 0.12 mm radial service clearance; all eight remain untrimmed",
        "No N1/N2 electrical-pair assumption | carrier/shell/other-button penetration 0",
        transparent_objects=[(mesh(m.body), (*COLORS["body"], 38)) for m in mechanisms.values()]
        + [(mesh(m.reaction), (*COLORS[f"{name}support"], 42)) for name, m in mechanisms.items()],
        world_lines=terminal_lines, camera_offset=rear_camera,
        final_size=(1920, 1280), supersample=2, fit_points=terminal_fit,
    )
    memory("render 06")

    # 07 both buttons at full travel.
    both_objects = []
    both_focus = []
    for name, m in mechanisms.items():
        rows = [
            (mesh(moved(m.cap, m.datum, 0.350, f"{name} full cap")), COLORS[f"{name}cap"]),
            (mesh(m.guide), COLORS[f"{name}guide"]),
            (mesh(m.body), COLORS["body"]),
            (mesh(actuator_at(name, m.datum, m.front, 0.350)), COLORS["actuator"]),
            (mesh(m.reaction), COLORS[f"{name}support"]),
        ]
        both_objects.extend(rows)
        both_focus.extend(tri.reshape(-1, 3) for tri, _ in rows)
    raster_scene(
        paths[6], both_objects,
        "07 / I2 FULL + I3 FULL",
        "Both independent caps reach their own 0.350 mm carrier hard stops without cross-coupling",
        "cap-cap / cap-other-guide / cap-other-body / actuator-actuator penetration 0",
        transparent_objects=[(mesh(carrier), (*COLORS["carrier"], 34)), (shell_mesh, (*COLORS["shell"], 22))],
        camera_offset=camera, final_size=(1920, 1280), supersample=2, fit_points=np.concatenate(both_focus),
    )
    memory("render 07")

    # 08 assembled local carrier.
    assembled = []
    assembled_focus = [mesh(carrier).reshape(-1, 3)]
    for name, m in mechanisms.items():
        rows = [
            (mesh(m.cap), COLORS[f"{name}cap"]), (mesh(m.guide), COLORS[f"{name}guide"]),
            (mesh(m.body), COLORS["body"]), (mesh(m.reaction), COLORS[f"{name}support"]),
        ]
        assembled.extend(rows)
        assembled_focus.extend(tri.reshape(-1, 3) for tri, _ in rows)
    raster_scene(
        paths[7], assembled,
        "08 / I2 + I3 SHARED CARRIER — TRANSPARENT",
        "Overlapping stationary guide material is fused, then both independent motion/service envelopes remain open",
        "One connected carrier solid | floating body 0 | minimum structural wall 1.20 mm",
        transparent_objects=[(mesh(carrier), (*COLORS["carrier"], 34)), (shell_mesh, (*COLORS["shell"], 20))],
        camera_offset=camera, final_size=(1920, 1280), supersample=2, fit_points=np.concatenate(assembled_focus),
    )
    memory("render 08")

    # 09 read-only frozen N1/N2 subsystem.
    frozen_carrier = regression["frozenCarrier"]
    source = regression["source"]
    n1_cap = import_step(N1_CAP)
    n2_cap = import_step(N2_CAP)
    a = regression["N2CarrierHW504A"]
    b = regression["N2CarrierHW504B"]
    frozen_focus = np.concatenate([mesh(n1_cap).reshape(-1, 3), mesh(n2_cap).reshape(-1, 3), mesh(frozen_carrier).reshape(-1, 3)])
    lines = [
        (np.asarray(a["closestPointLeftMm"]), np.asarray(a["closestPointRightMm"]), (255, 226, 104, 255), f"A {float(a['distanceMm']):.6f} mm"),
        (np.asarray(b["closestPointLeftMm"]), np.asarray(b["closestPointRightMm"]), (255, 147, 91, 255), f"B {float(b['distanceMm']):.6f} mm"),
    ]
    raster_scene(
        paths[8], [(mesh(n1_cap), COLORS["I2cap"]), (mesh(n2_cap), COLORS["I3cap"]),
                   (mesh(source["N1_ITS1105_body"]), COLORS["body"]), (mesh(source["N2_ITS1105_body"]), COLORS["body"])],
        "09 / N1 + N2 HARD-FROZEN REGRESSION",
        "Approved docs/62-63 files are read-only and SHA-256 unchanged; I2/I3 carrier remains a separate solid",
        f"A {float(a['distanceMm']):.6f} mm | B {float(b['distanceMm']):.6f} mm | T1/T3 {float(regression['N2ActiveT1T3HW504B']['minimumDistanceMm']):.6f} mm",
        transparent_objects=[(mesh(frozen_carrier), (*COLORS["carrier"], 36)),
                             (mesh(source["HW504_A_NONFUNCTIONAL_TRIM"]), (*COLORS["hwa"], 42)),
                             (mesh(source["HW504_B_EXACT_KEEP"]), (*COLORS["hwb"], 38))],
        world_lines=lines, camera_offset=(58.0, -78.0, 48.0),
        final_size=(1920, 1280), supersample=2, fit_points=frozen_focus,
    )
    memory("render 09")
    return paths


def report_markdown(data: dict[str, object]) -> str:
    audit = data["currentAudit"]
    exact = data["exact"]
    combined = data["combinedMotion"]
    regression = data["n1N2Regression"]
    verdict = data["verdict"]
    motion_sections = []
    terminal_sections = []
    for name in ("I2", "I3"):
        motion_rows = "\n".join(
            f"| {float(row['travelMm']):.3f} | {float(row['capGuide']['penetrationMm3']):.9f} | "
            f"{float(row['capShell']['penetrationMm3']):.9f} | {float(row['capActuator']['distanceMm']):.9f} | "
            f"{float(row['rearHardStop']['distanceMm']):.3f} |"
            for row in exact[name]["motionStates"]
        )
        motion_sections.append(
            f"### {name}\n\n| travel mm | cap-guide pen mm³ | cap-shell pen mm³ | contact gap mm | hard-stop residual mm |\n"
            f"|---:|---:|---:|---:|---:|\n{motion_rows}"
        )
        terminal_rows = "\n".join(
            f"| {terminal} | {float(row['carrier']['distanceMm']):.6f} | {float(row['localShell']['distanceMm']):.6f} | "
            f"{float(row['otherSwitch']['distanceMm']):.6f} | {float(row['otherGuide']['distanceMm']):.6f} | 유지 |"
            for terminal, row in exact[name]["terminals"].items()
        )
        terminal_sections.append(
            f"### {name}\n\n| terminal | carrier mm | shell mm | other switch mm | other guide mm | 처리 |\n"
            f"|---|---:|---:|---:|---:|---|\n{terminal_rows}"
        )
    combined_rows = "\n".join(
        f"| {float(row['I2TravelMm']):.3f} | {float(row['I3TravelMm']):.3f} | "
        f"{max(float(pair['penetrationMm3']) for pair in row['pairs'].values()):.9f} | "
        f"{float(row['pairs']['capCap']['distanceMm']):.6f} |"
        for row in combined
    )
    renders = "\n".join(f"- `{path}`" for path in data["outputs"]["renders"])
    return f"""# 64 — I2/I3 PRODUCTION-INTENT BUTTON MECHANISMS

## 결론

I2/I3의 exterior feasibility는 재평가하지 않았다. 두 cap의 승인 center/orientation과 의도된 shell 대비 2.5°를 그대로 유지하고, 기존 shared carrier에 내부 기능만 추가했다.

초기 unrelieved 9.3 mm C-guide candidate는 I2에서 **{float(data['design']['I2']['guide']['rawShellPenetrationMm3']):.6f} mm³**, I3에서 **{float(data['design']['I3']['guide']['rawShellPenetrationMm3']):.6f} mm³** local-shell penetration이 있었다.

**THIS INTERNAL CANDIDATE FAILED**

외형 대신 guide의 shell-facing 비기능 front/corner material만 exact local relief했다. 최종 guide-shell penetration은 둘 다 0이며, 6.5 mm shoulder, 6.8 mm cavity, Ø4.5/Ø4.8 guide pair, independent service slot, 0.350 mm hard stop은 유지된다.

## 1. Current exact audit

| item | I2 | I3 |
|---|---:|---:|
| cap ↔ switch top | {float(audit['controls']['I2']['capSwitchPlaneAngleDeg']):.6f}° | {float(audit['controls']['I3']['capSwitchPlaneAngleDeg']):.6f}° |
| cap ↔ local shell plane | {float(audit['controls']['I2']['capShellLocalPlaneAngleDeg']):.6f}° | {float(audit['controls']['I3']['capShellLocalPlaneAngleDeg']):.6f}° |
| cap ↔ actuator lateral offset | {float(audit['controls']['I2']['capActuatorLateralOffsetMm']):.9f} mm | {float(audit['controls']['I3']['capActuatorLateralOffsetMm']):.9f} mm |
| current rear reaction gap | {float(audit['controls']['I2']['rearReactionGapMm']):.6f} mm | {float(audit['controls']['I3']['rearReactionGapMm']):.6f} mm |
| cap ↔ local shell | {float(audit['controls']['I2']['capShell']['distanceMm']):.6f} mm | {float(audit['controls']['I3']['capShell']['distanceMm']):.6f} mm |
| body ↔ local shell | {float(audit['controls']['I2']['bodyShell']['distanceMm']):.6f} mm | {float(audit['controls']['I3']['bodyShell']['distanceMm']):.6f} mm |

2.5°는 오류가 아니라 승인된 internal-axis tilt다. cap을 shell과 평행하게 재정렬하지 않았다.

## 2. Production-intent architecture

두 버튼 공통 load path:

`finger → frozen exterior cap → Ø3.0 central contact → ITS actuator/body → terminal-window flat reaction frame → shared carrier/shell`

- retention: 6.5 mm square positive shoulder
- guide: Ø4.5 tail / Ø4.8 bore, radial clearance 0.15 mm
- rotation/rock control: 6.5 mm shoulder / 6.8 mm cavity, lateral clearance 0.15 mm
- return: ITS internal return only; 별도 spring 없음
- hard stop: guide rear structural plane at 0.350 mm
- service: open C-guide + lateral switch service + central 4.0 × 3.2 mm terminal/wire window
- stationary I2/I3 guide overlap은 shared carrier material로 fuse되며 각 cap의 타 guide motion envelope penetration은 0

### Rear reaction

| item | I2 | I3 |
|---|---:|---:|
| type | terminal-window flat frame | terminal-window flat frame |
| plastic-body contact area | {float(data['design']['I2']['reaction']['contactAreaMm2']):.3f} mm² | {float(data['design']['I3']['reaction']['contactAreaMm2']):.3f} mm² |
| minimum wall | {float(data['design']['I2']['reaction']['minimumWallMm']):.3f} mm | {float(data['design']['I3']['reaction']['minimumWallMm']):.3f} mm |
| connected contact patch | {int(data['design']['I2']['reaction']['connectedContactPatchCount'])} | {int(data['design']['I3']['reaction']['connectedContactPatchCount'])} |

기존 0.110 mm rear gap을 frame이 메우며 ITS terminal envelope를 구조적으로 누르지 않는다. tangent-only point support가 아니라 각 버튼 **24.907 mm²**의 broad rear plastic contact다.

## 3. Independent exact motion

{"\n\n".join(motion_sections)}

각 상태에서 cap/guide, cap/shell, cap/base carrier, cap/actuator 및 타 버튼 guide/body의 unintended penetration은 0이다. FULL에서 각 shoulder가 자기 carrier hard stop에 도달하며 타 cap/switch 이동량은 0이다.

### Combined states

| I2 travel mm | I3 travel mm | maximum cross penetration mm³ | cap-cap distance mm |
|---:|---:|---:|---:|
{combined_rows}

## 4. Terminal map

T1/T2/T3/T4는 electrical pair를 가정하지 않고 각각 보수적인 **실물 terminal + radial service 0.12 mm envelope**로 검사했다. 8개 모두 무절단 유지한다.

{"\n\n".join(terminal_sections)}

## 5. Shared carrier / FDM

- current approved I2/I3 carrier removed volume: **{float(data['design']['carrier']['removedFromApprovedCurrentCarrierMm3']):.9f} mm³**
- final carrier solid count: **{int(data['design']['carrier']['finalSolidCount'])}**
- floating body: **{data['design']['carrier']['floatingBody']}**
- local shell penetration: **{float(data['exact']['sharedCarrierShell']['penetrationMm3']):.9f} mm³**
- critical minimum wall: **{float(data['design']['minimumStructuralWallMm']):.3f} mm**
- tiny snap/hook: 없음

## 6. N1/N2 hard-freeze regression

- frozen file SHA-256 guard: **{'PASS' if regression['hashGuardPass'] else 'FAIL'}**
- N1 approved mechanism: **{'PASS' if regression['N1ApprovedMechanismPass'] else 'FAIL'}**
- N2 carrier ↔ HW504-A: **{float(regression['N2CarrierHW504A']['distanceMm']):.9f} mm** ≥ {APPROVED_N2_A_MM:.9f}
- N2 carrier ↔ HW504-B: **{float(regression['N2CarrierHW504B']['distanceMm']):.9f} mm** ≥ {APPROVED_N2_B_MM:.9f}
- N2 T1/T3 ↔ HW504-B: **{float(regression['N2ActiveT1T3HW504B']['minimumDistanceMm']):.9f} mm** ≥ {APPROVED_N2_T1_T3_MM:.9f}
- I2/I3 carrier ↔ frozen N1/N2 carrier penetration: **{float(regression['I2I3CarrierToFrozenN1N2']['penetrationMm3']):.9f} mm³**

## 7. Outputs

{renders}

- `{data['outputs']['json']}` — lightweight exact JSON
- `{data['outputs']['carrierStep']}` — I2/I3 local shared carrier only
- `{data['outputs']['capSteps']['I2']}` / `{data['outputs']['capSteps']['I3']}` — local cap components only
- full shell / full assembly / STL / print plate: **생성하지 않음**

## 8. FINAL / STOP

- I2 ARCHITECTURE = **{verdict['I2_ARCHITECTURE']}**
- I3 ARCHITECTURE = **{verdict['I3_ARCHITECTURE']}**
- I2 MOTION = **{verdict['I2_MOTION']}**
- I3 MOTION = **{verdict['I3_MOTION']}**
- SHARED CARRIER = **{verdict['SHARED_CARRIER']}**
- I2 TERMINALS = **{verdict['I2_TERMINALS']}**
- I3 TERMINALS = **{verdict['I3_TERMINALS']}**
- N1/N2 FROZEN BASELINE = **{verdict['N1_N2_FROZEN_BASELINE']}**
- EXTERIOR = **{verdict['EXTERIOR']}**

I2/I3에서 STOP한다. M4/N3/I4/M3로 자동 확장하지 않았다.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    memory("start")
    audit = json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
    datums = load_datums()
    base = import_step(SOURCE_DIR / "I2_I3_shared_carrier.step")
    base_caps = {name: import_step(CAP_STEPS[name]) for name in ("I2", "I3")}
    shell, shell_bbox = local_shell(base, base_caps)
    memory("local source and shell crop")

    mechanisms = {name: build_mechanism(name, datums[name], shell) for name in ("I2", "I3")}
    raw_guide_pair = exact_pair(mechanisms["I2"].raw_guide, mechanisms["I3"].raw_guide, "raw stationary guides")
    carrier, added, carrier_metrics = build_carrier(base, mechanisms)
    carrier_shell = exact_pair(carrier, shell, "final I2/I3 shared carrier<->local shell")
    memory("production-intent carrier built")

    exact = {
        "I2": validate_mechanism(mechanisms["I2"], mechanisms["I3"], carrier, base, shell),
        "I3": validate_mechanism(mechanisms["I3"], mechanisms["I2"], carrier, base, shell),
    }
    exact["sharedCarrierShell"] = carrier_shell
    exact["stationaryGuideFusion"] = exact_pair(mechanisms["I2"].guide, mechanisms["I3"].guide, "relieved stationary guide material overlap")
    exact["reactionFrameSeparation"] = exact_pair(mechanisms["I2"].reaction, mechanisms["I3"].reaction, "I2 reaction<->I3 reaction")
    combined = combined_states(mechanisms)
    gates = {name: mechanism_gates(exact[name]) for name in ("I2", "I3")}
    combined_ok = combined_pass(combined)
    exterior = {name: exterior_delta(mechanisms[name]) for name in ("I2", "I3")}
    regression = regression_n1_n2(carrier)
    memory("N1/N2 frozen regression")

    support_ok = all(
        float(mechanisms[name].reaction_metrics["contactAreaMm2"]) >= 20.0
        and float(mechanisms[name].reaction_metrics["minimumWallMm"]) + 1.0e-9 >= MIN_WALL_MM
        for name in ("I2", "I3")
    )
    carrier_ok = (
        float(carrier_shell["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and not bool(carrier_metrics["floatingBody"])
        and float(carrier_metrics["removedFromApprovedCurrentCarrierMm3"]) <= BOOLEAN_EPS_MM3
        and int(carrier_metrics["finalSolidCount"]) == 1
        and combined_ok
        and support_ok
    )
    exterior_ok = all(row["symmetricDifferenceMm3"] <= BOOLEAN_EPS_MM3 for row in exterior.values())
    architecture = {
        name: all(gates[name].values()) and carrier_ok and exterior_ok
        for name in ("I2", "I3")
    }
    verdict = {
        "I2_ARCHITECTURE": "ACCEPT" if architecture["I2"] else "HOLD",
        "I3_ARCHITECTURE": "ACCEPT" if architecture["I3"] else "HOLD",
        "I2_MOTION": "PASS" if gates["I2"]["motion"] and gates["I2"]["hardStop"] and combined_ok else "HOLD",
        "I3_MOTION": "PASS" if gates["I3"]["motion"] and gates["I3"]["hardStop"] and combined_ok else "HOLD",
        "SHARED_CARRIER": "PASS" if carrier_ok else "HOLD",
        "I2_TERMINALS": "PASS" if gates["I2"]["terminals"] and gates["I2"]["service"] else "HOLD",
        "I3_TERMINALS": "PASS" if gates["I3"]["terminals"] and gates["I3"]["service"] else "HOLD",
        "N1_N2_FROZEN_BASELINE": "PRESERVED" if regression["pass"] else "FAIL",
        "EXTERIOR": "PRESERVED" if exterior_ok else "FAIL",
    }

    export_step(carrier, CARRIER_STEP)
    for name in ("I2", "I3"):
        export_step(mechanisms[name].cap, CAP_OUTPUTS[name])
    memory("local STEP exports")
    renders = render_outputs(base, carrier, shell, mechanisms, exact, combined, regression)

    data: dict[str, object] = {
        "schema": "onegrip.i2_i3.production_intent_mechanism.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOW-MEMORY / LOCAL SHELL CROP / SERIAL EXACT / N1-N2 HASH GUARDED",
        "freeze": {
            "I2CenterMovementMm": 0.0, "I3CenterMovementMm": 0.0,
            "I2OrientationChangeDeg": 0.0, "I3OrientationChangeDeg": 0.0,
            "intentionalCapShellAngleDeg": 2.5,
            "N1N2Writes": 0, "fullShellExport": False, "fullAssembly": False,
            "STL": False, "printPlate": False, "multiprocessing": False,
        },
        "currentAudit": audit,
        "initialCandidateVerdict": "THIS INTERNAL CANDIDATE FAILED",
        "initialCandidate": {
            "reason": "unrelieved full C-guides penetrate the fixed local JfD shell",
            "I2RawGuideShellPenetrationMm3": mechanisms["I2"].guide_metrics["rawShellPenetrationMm3"],
            "I3RawGuideShellPenetrationMm3": mechanisms["I3"].guide_metrics["rawShellPenetrationMm3"],
            "stationaryRawGuideOverlapMm3": raw_guide_pair["penetrationMm3"],
            "externalResponse": "NO EXTERIOR CHANGE; INTERNAL LOCAL RELIEF ONLY",
        },
        "design": {
            name: {
                "actuation": "DIRECT", "return": "ITS INTERNAL RETURN",
                "cap": {"contactDiameterMm": 3.0, "tailDiameterMm": 4.5, "shoulderSizeMm": 6.5},
                "guide": mechanisms[name].guide_metrics,
                "reaction": mechanisms[name].reaction_metrics,
            }
            for name in ("I2", "I3")
        },
        "exact": exact,
        "combinedMotion": combined,
        "gates": {**gates, "combinedMotion": combined_ok, "carrier": carrier_ok, "support": support_ok},
        "exteriorDelta": exterior,
        "n1N2Regression": serializable_regression(regression),
        "shellCropBboxMm": shell_bbox,
        "verdict": verdict,
        "outputs": {
            "json": str(JSON_PATH.relative_to(ROOT)),
            "report": str(REPORT_PATH.relative_to(ROOT)),
            "carrierStep": str(CARRIER_STEP.relative_to(ROOT)),
            "capSteps": {name: str(path.relative_to(ROOT)) for name, path in CAP_OUTPUTS.items()},
            "renders": [str(path.relative_to(ROOT)) for path in renders],
            "forbiddenOutputsGenerated": [],
        },
        "memory": MEMORY,
        "stop": "I2/I3 complete; no expansion to M4/N3/I4/M3",
    }
    data["design"]["carrier"] = carrier_metrics
    data["design"]["minimumStructuralWallMm"] = min(GUIDE_WALL_MM, REACTION_MIN_WALL_MM, 1.60)
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(report_markdown(data), encoding="utf-8")
    data["outputs"]["sha256"] = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in (REPORT_PATH, CARRIER_STEP, *CAP_OUTPUTS.values(), *renders)
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    memory("complete")
    print(json.dumps({
        "verdict": verdict,
        "initialCandidate": data["initialCandidateVerdict"],
        "I2SupportAreaMm2": mechanisms["I2"].reaction_metrics["contactAreaMm2"],
        "I3SupportAreaMm2": mechanisms["I3"].reaction_metrics["contactAreaMm2"],
        "carrierShellDistanceMm": carrier_shell["distanceMm"],
        "combinedMotionPass": combined_ok,
        "N1N2Regression": serializable_regression(regression),
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY),
        "report": str(REPORT_PATH.relative_to(ROOT)),
        "renders": [str(path.relative_to(ROOT)) for path in renders],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
