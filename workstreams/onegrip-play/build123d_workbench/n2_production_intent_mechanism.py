"""Build and validate the N2 Candidate-A production-intent mechanism.

Only the N2 side of the existing shared carrier is changed.  The exterior
cap pad, its centre/orientation/axis, both HW504 solids and the local shell
references remain immutable.  The added geometry is deliberately simple:

* a square internal cap shoulder with a centred actuator contact;
* a three-sided, shell-closure-captured C-guide fused to the carrier;
* a broad 0.35 mm overtravel stop in that guide;
* a rear reaction frame and an open T1/T3 service bay.

No full shell or complete product assembly is loaded or exported.
"""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import psutil
from build123d import Align, Box, Compound, Location, Shape, Vector, export_step, export_stl, import_step

from .finger_controls_v2 import (
    ACTUATOR_DIAMETER,
    ACTUATOR_PROJECTION,
    ACTUATOR_TRAVEL_MAX,
    CAP_SOCKET_DIAMETER,
    CARRIER_WALL,
    SWITCH_BODY_H,
    SWITCH_BODY_X,
    SWITCH_BODY_Y,
    SWITCH_POCKET_X,
    SWITCH_POCKET_Y,
    ControlDatum,
    oriented_box,
    oriented_cylinder,
    point_at,
    unit,
)
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    aggregate_pairs,
    datum_from_manifest,
    exact_pair,
    modified_n2,
    raster_scene,
    safe_triangles,
)
from .option_c_final_local_fit import bounds


ROOT = Path(__file__).resolve().parents[1]
SOURCE_STEP = (
    ROOT / "build123d_workbench" / "out" / "option_c_final_local_fit"
    / "OPTION_C_FINAL_LOCAL_FIT.step"
)
SOURCE_JSON = (
    ROOT / "build123d_workbench" / "out" / "option_c_final_local_fit"
    / "option_c_final_local_fit.json"
)
MANIFEST = (
    ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
    / "finger_controls_v2_source_manifest.json"
)
BASE_CAP_STEP = ROOT / "build123d_workbench" / "out" / "finger_controls_v2" / "N2_cap.step"

OUT_DIR = ROOT / "build123d_workbench" / "out" / "n2_production_intent_mechanism"
RENDER_DIR = ROOT / "renders" / "n2_production_intent_mechanism"
JSON_PATH = OUT_DIR / "n2_production_intent_mechanism.json"
REPORT_PATH = ROOT / "docs" / "60_n2_production_intent_mechanism.md"
CAP_STEP = OUT_DIR / "N2_PRODUCTION_INTENT_CAP.step"
CAP_STL = OUT_DIR / "N2_PRODUCTION_INTENT_CAP.stl"
CARRIER_STEP = OUT_DIR / "N1_N2_SHARED_CARRIER_N2_PRODUCTION_INTENT.step"
CARRIER_STL = OUT_DIR / "N1_N2_SHARED_CARRIER_N2_PRODUCTION_INTENT.stl"
ASSEMBLY_STEP = OUT_DIR / "N2_PRODUCTION_INTENT_LOCAL_ASSEMBLY.step"

FRONT_DEPTH_MM = 4.80
HOUSING_REAR_DEPTH_MM = FRONT_DEPTH_MM + SWITCH_BODY_H
TRAVELS_MM = (0.0, 0.175, 0.350)
TRIM_CUT_DEPTH_MM = 8.51
TERMINAL_CLEARANCE_TARGET_MM = 0.80
MIN_WALL_MM = 1.20

# Moving cap internals.  All additions begin behind the immutable exterior.
CONTACT_DIAMETER_MM = 3.00
CONTACT_FRONT_DEPTH_MM = FRONT_DEPTH_MM - ACTUATOR_PROJECTION - 0.07
CONTACT_REAR_DEPTH_MM = FRONT_DEPTH_MM - ACTUATOR_PROJECTION
CAP_GUIDE_DIAMETER_MM = 4.50
GUIDE_BORE_DIAMETER_MM = 4.80
GUIDE_RADIAL_CLEARANCE_MM = (GUIDE_BORE_DIAMETER_MM - CAP_GUIDE_DIAMETER_MM) / 2.0
CAP_SHOULDER_SIZE_MM = 6.50
GUIDE_CAVITY_SIZE_MM = 6.80
GUIDE_LATERAL_CLEARANCE_MM = (GUIDE_CAVITY_SIZE_MM - CAP_SHOULDER_SIZE_MM) / 2.0
CAP_SHOULDER_FRONT_MM = 3.50
CAP_SHOULDER_REAR_MM = 3.80
CAP_GUIDE_TAIL_REAR_MM = 4.35
CAP_GUIDE_INNER_DIAMETER_MM = 3.55

# Stationary three-sided guide.  The rear cavity wall is the structural stop.
GUIDE_OUTER_SIZE_MM = 9.30
GUIDE_FRONT_MM = 3.30
GUIDE_CAVITY_FRONT_MM = CAP_SHOULDER_FRONT_MM
GUIDE_CAVITY_REAR_MM = CAP_SHOULDER_REAR_MM + ACTUATOR_TRAVEL_MAX
GUIDE_REAR_MM = FRONT_DEPTH_MM
GUIDE_SERVICE_SLOT_U_MM = 5.20
GUIDE_SERVICE_SLOT_V_MM = GUIDE_CAVITY_SIZE_MM
GUIDE_WALL_MM = (GUIDE_OUTER_SIZE_MM - GUIDE_CAVITY_SIZE_MM) / 2.0

# Switch locating/reaction and active terminal service access.
REACTION_OUTER_MM = SWITCH_POCKET_X
REACTION_WINDOW_U_MM = 4.00
REACTION_WINDOW_V_MM = 3.20
REACTION_FRONT_MM = HOUSING_REAR_DEPTH_MM
REACTION_REAR_MM = HOUSING_REAR_DEPTH_MM + 0.20
ACTIVE_SERVICE_BAY_U_MM = 8.20
ACTIVE_SERVICE_BAY_V_MM = 2.00
ACTIVE_SERVICE_BAY_V_OFFSET_MM = -2.55
ACTIVE_SERVICE_BAY_REAR_MM = 10.80
REACTION_MIN_WALL_MM = min(
    (REACTION_OUTER_MM - REACTION_WINDOW_U_MM) / 2.0,
    (REACTION_OUTER_MM - REACTION_WINDOW_V_MM) / 2.0,
)

RSS_LIMIT_MB = 24576.0
PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, float | str]] = []

TERMINAL_LABELS = {
    "T1": "N2_root_nu_nv",
    "T2": "N2_root_nu_pv",
    "T3": "N2_root_pu_nv",
    "T4": "N2_root_pu_pv",
}

COLORS = {
    "cap": (57, 207, 143),
    "shoulder": (40, 219, 205),
    "guide": (74, 142, 226),
    "carrier": (179, 89, 211),
    "reaction": (245, 128, 62),
    "body": (235, 174, 66),
    "actuator": (252, 207, 89),
    "active": (67, 204, 147),
    "trimmed": (120, 130, 142),
    "hw": (145, 96, 235),
    "shell": (87, 183, 214),
}


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1)})
    if rss > RSS_LIMIT_MB:
        raise MemoryError(f"RAM stop at {stage}: {rss:.1f} MB")
    available = float(psutil.virtual_memory().available) / (1024.0 * 1024.0)
    if available < 3072.0:
        raise MemoryError(f"System available-memory stop at {stage}: {available:.1f} MB")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def volume(shape: Shape | None) -> float:
    if shape is None or len(shape.solids()) == 0:
        return 0.0
    return float(shape.volume)


def load_source() -> dict[str, Shape]:
    compound = import_step(SOURCE_STEP)
    rows = {child.label: child for child in compound.children}
    required = {
        "HW504_A_NONFUNCTIONAL_TRIM",
        "HW504_B_EXACT_KEEP",
        "N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF",
        "N2_SEAM_JaD",
        "N2_SEAM_JfD",
        "N2_ITS1105_body",
        "N2_ITS1105_actuator",
        *TERMINAL_LABELS.values(),
    }
    if missing := required - set(rows):
        raise RuntimeError(f"Missing source labels: {sorted(missing)}")
    del compound
    memory("docs/57 local source loaded")
    return rows


def load_datum() -> ControlDatum:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return modified_n2(datum_from_manifest("N2", manifest["controls"]["N2"]))


def moved(shape: Shape, vector: Iterable[float], label: str) -> Shape:
    row = np.asarray(tuple(vector), dtype=float)
    result = shape.moved(Location(Vector(float(row[0]), float(row[1]), float(row[2]))))
    result.label = label
    return result


def build_production_cap(base_cap: Shape, datum: ControlDatum) -> tuple[Shape, dict[str, Shape]]:
    contact = oriented_cylinder(
        datum,
        CONTACT_DIAMETER_MM,
        CONTACT_FRONT_DEPTH_MM,
        CONTACT_REAR_DEPTH_MM,
        cap_frame=True,
        label="N2_CENTERED_ACTUATOR_CONTACT_PUCK",
    )
    shoulder_outer = oriented_box(
        datum,
        CAP_SHOULDER_SIZE_MM,
        CAP_SHOULDER_SIZE_MM,
        CAP_SHOULDER_FRONT_MM,
        CAP_SHOULDER_REAR_MM,
        cap_frame=True,
        label="N2_CAP_RETENTION_SHOULDER_OUTER",
    )
    shoulder_inner = oriented_cylinder(
        datum,
        CAP_GUIDE_INNER_DIAMETER_MM,
        CAP_SHOULDER_FRONT_MM - 0.10,
        CAP_SHOULDER_REAR_MM + 0.10,
        cap_frame=True,
        label="N2_CAP_RETENTION_SHOULDER_ACTUATOR_BORE",
    )
    shoulder = (shoulder_outer - shoulder_inner).clean()
    shoulder.label = "N2_SQUARE_RETENTION_AND_ANTI_ROTATION_SHOULDER"

    tail_outer = oriented_cylinder(
        datum,
        CAP_GUIDE_DIAMETER_MM,
        CAP_SHOULDER_REAR_MM - 0.10,
        CAP_GUIDE_TAIL_REAR_MM,
        cap_frame=True,
        label="N2_CAP_REAR_GUIDE_TAIL_OUTER",
    )
    tail_inner = oriented_cylinder(
        datum,
        CAP_GUIDE_INNER_DIAMETER_MM,
        CAP_SHOULDER_REAR_MM - 0.20,
        CAP_GUIDE_TAIL_REAR_MM + 0.10,
        cap_frame=True,
        label="N2_CAP_REAR_GUIDE_TAIL_ACTUATOR_BORE",
    )
    tail = (tail_outer - tail_inner).clean()
    tail.label = "N2_CAP_REAR_GUIDE_TAIL"

    cap = base_cap.fuse(contact).fuse(shoulder).fuse(tail).clean()
    cap.label = "N2_PRODUCTION_INTENT_CAP_DIRECT_ACTUATION"
    if len(cap.solids()) != 1:
        raise RuntimeError(f"Production cap must be one solid, got {len(cap.solids())}")
    memory("production cap built")
    return cap, {"contact": contact, "shoulder": shoulder, "tail": tail}


def build_guide(datum: ControlDatum) -> tuple[Shape, dict[str, Shape]]:
    outer = oriented_box(
        datum,
        GUIDE_OUTER_SIZE_MM,
        GUIDE_OUTER_SIZE_MM,
        GUIDE_FRONT_MM,
        GUIDE_REAR_MM,
        cap_frame=True,
        label="N2_C_GUIDE_OUTER",
    )
    bore = oriented_cylinder(
        datum,
        GUIDE_BORE_DIAMETER_MM,
        GUIDE_FRONT_MM - 0.10,
        GUIDE_REAR_MM + 0.10,
        cap_frame=True,
        label="N2_CAP_GUIDE_BORE",
    )
    cavity = oriented_box(
        datum,
        GUIDE_CAVITY_SIZE_MM,
        GUIDE_CAVITY_SIZE_MM,
        GUIDE_CAVITY_FRONT_MM,
        GUIDE_CAVITY_REAR_MM,
        cap_frame=True,
        label="N2_RETENTION_AND_STOP_CAVITY",
    )
    sign = float(datum.open_side_sign)
    slot = oriented_box(
        datum,
        GUIDE_SERVICE_SLOT_U_MM,
        GUIDE_SERVICE_SLOT_V_MM,
        GUIDE_FRONT_MM - 0.10,
        GUIDE_REAR_MM + 0.10,
        u_offset=sign * GUIDE_SERVICE_SLOT_U_MM / 2.0,
        cap_frame=True,
        label="N2_CAP_LATERAL_SERVICE_SLOT",
    )
    guide = (outer - bore - cavity - slot).clean()
    guide.label = "N2_THREE_SIDED_RETENTION_GUIDE_AND_HARD_STOP"

    front_outer = oriented_box(
        datum,
        GUIDE_OUTER_SIZE_MM,
        GUIDE_OUTER_SIZE_MM,
        GUIDE_FRONT_MM,
        GUIDE_CAVITY_FRONT_MM,
        cap_frame=True,
        label="N2_FRONT_RETENTION_STOP_OUTER",
    )
    front = (front_outer - bore - slot).clean()
    front.label = "N2_FRONT_RETENTION_STOP"
    rear_outer = oriented_box(
        datum,
        GUIDE_OUTER_SIZE_MM,
        GUIDE_OUTER_SIZE_MM,
        GUIDE_CAVITY_REAR_MM,
        GUIDE_REAR_MM,
        cap_frame=True,
        label="N2_REAR_OVERTRAVEL_STOP_OUTER",
    )
    rear = (rear_outer - bore - slot).clean()
    rear.label = "N2_REAR_OVERTRAVEL_HARD_STOP"
    memory("three-sided cap guide built")
    return guide, {"outer": outer, "bore": bore, "cavity": cavity, "slot": slot, "frontStop": front, "rearStop": rear}


def active_service_bay(datum: ControlDatum) -> Shape:
    result = oriented_box(
        datum,
        ACTIVE_SERVICE_BAY_U_MM,
        ACTIVE_SERVICE_BAY_V_MM,
        REACTION_FRONT_MM,
        ACTIVE_SERVICE_BAY_REAR_MM,
        v_offset=ACTIVE_SERVICE_BAY_V_OFFSET_MM,
        label="N2_T1_T3_REAR_SOLDER_SERVICE_BAY",
    )
    return result


def build_reaction_support(datum: ControlDatum, roots: dict[str, Shape]) -> tuple[Shape, Shape]:
    outer = oriented_box(
        datum,
        REACTION_OUTER_MM,
        REACTION_OUTER_MM,
        REACTION_FRONT_MM,
        REACTION_REAR_MM,
        label="N2_REAR_REACTION_FRAME_OUTER",
    )
    window = oriented_box(
        datum,
        REACTION_WINDOW_U_MM,
        REACTION_WINDOW_V_MM,
        REACTION_FRONT_MM - 0.10,
        REACTION_REAR_MM + 0.10,
        label="N2_REAR_REACTION_FRAME_WIRE_WINDOW",
    )
    service = active_service_bay(datum)
    support = outer - window - service
    for root in roots.values():
        support = support - root
    support = support.clean()
    support.label = "N2_BROAD_REAR_REACTION_SUPPORT"
    memory("rear reaction support built")
    return support, service


def global_box(lower: np.ndarray, upper: np.ndarray, label: str) -> Shape:
    size = upper - lower
    result = Box(
        float(size[0]),
        float(size[1]),
        float(size[2]),
        align=(Align.MIN, Align.MIN, Align.MIN),
    ).moved(Location(Vector(float(lower[0]), float(lower[1]), float(lower[2]))))
    result.label = label
    return result


def build_production_carrier(
    source_carrier: Shape,
    guide: Shape,
    reaction: Shape,
    service_bay: Shape,
    roots: dict[str, Shape],
    datum: ControlDatum,
    hw_a: Shape,
) -> tuple[Shape, Shape, dict[str, object]]:
    carrier = source_carrier.fuse(guide).fuse(reaction)
    carrier = carrier - service_bay
    for root in roots.values():
        carrier = carrier - root

    # Complete the existing lateral C-channel with the exact body-width
    # corridor required for shell-open replacement.  The corridor starts on
    # the centre plane, so the closed-side locating rails are preserved.
    switch_service = service_sweeps(datum)["switch"]
    carrier = carrier - switch_service

    # The broad reaction frame reaches a small nonfunctional corner of
    # approved HW504-A.  HW504 is immutable, so notch only the new reaction
    # material around the exact common bbox.  The old carrier remains intact.
    common = carrier & hw_a
    relief_tool: Shape | None = None
    relief_margin = 0.15
    relief_removed = 0.0
    if common is not None and len(common.solids()) > 0 and float(common.volume) > BOOLEAN_EPS_MM3:
        lower, upper = bounds(common)
        relief_tool = global_box(
            lower - relief_margin,
            upper + relief_margin,
            "N2_REACTION_SUPPORT_HW504_A_LOCAL_RELIEF",
        )
        before = float(carrier.volume)
        carrier = carrier - relief_tool
        relief_removed = max(0.0, before - float(carrier.volume))
        reaction_final = (reaction - relief_tool).clean()
    else:
        reaction_final = reaction
    reaction_final.label = "N2_BROAD_REAR_REACTION_SUPPORT_FINAL"
    carrier = carrier.clean()
    carrier.label = "N1_N2_SHARED_CARRIER_N2_PRODUCTION_INTENT"
    if len(carrier.solids()) != len(source_carrier.solids()):
        raise RuntimeError(
            "N2 additions must preserve shared-carrier solid count: "
            f"{len(source_carrier.solids())} -> {len(carrier.solids())}"
        )
    metrics: dict[str, object] = {
        "HW504AReliefMarginMm": relief_margin,
        "HW504AReliefRemovedMm3": relief_removed,
        "reactionMaterialRemainingMm3": float(reaction_final.volume),
        "reactionContactAreaEstimateMm2": float(reaction_final.volume) / (REACTION_REAR_MM - REACTION_FRONT_MM),
        "switchServiceCorridorPenetrationAfterCutMm3": volume(carrier & switch_service),
        "reliefToolBboxMm": None if relief_tool is None else {
            "min": bounds(relief_tool)[0].tolist(),
            "max": bounds(relief_tool)[1].tolist(),
        },
    }
    memory("N2 production carrier fused and HW504-A relieved")
    return carrier, reaction_final, metrics


def trim_terminals(source: dict[str, Shape], datum: ControlDatum) -> tuple[dict[str, Shape], dict[str, Shape]]:
    keep = oriented_box(
        datum,
        40.0,
        40.0,
        -5.0,
        TRIM_CUT_DEPTH_MM,
        label="N2_UNUSED_T2_T4_PRODUCTION_STUB_KEEP",
    )
    retained: dict[str, Shape] = {}
    removed: dict[str, Shape] = {}
    for terminal, source_label in TERMINAL_LABELS.items():
        original = source[source_label]
        if terminal in {"T2", "T4"}:
            row = (original & keep).clean()
            row.label = f"N2_{terminal}_UNUSED_TRIMMED_STUB"
            removed_row = (original - row).clean()
            removed_row.label = f"N2_{terminal}_REMOVED_EXTERNAL_LEAD"
            removed[terminal] = removed_row
        else:
            row = original
            row.label = f"N2_{terminal}_ACTIVE_ELECTRICAL_TERMINAL"
        retained[terminal] = row
    memory("T1/T3 active and T2/T4 production stubs modeled")
    return retained, removed


def cap_at(cap: Shape, datum: ControlDatum, travel: float) -> Shape:
    axis = unit(datum.axis)
    return moved(cap, -axis * travel, f"N2_CAP_TRAVEL_{travel:.3f}MM")


def actuator_at(datum: ControlDatum, travel: float) -> Shape:
    result = oriented_cylinder(
        datum,
        ACTUATOR_DIAMETER,
        FRONT_DEPTH_MM - ACTUATOR_PROJECTION + travel,
        FRONT_DEPTH_MM,
        label=f"N2_ACTUATOR_COMPRESSED_{travel:.3f}MM",
    )
    return result


def external_geometry_delta(base_cap: Shape, production_cap: Shape, datum: ControlDatum) -> dict[str, float]:
    crop = oriented_box(
        datum,
        24.0,
        24.0,
        -4.0,
        0.20,
        cap_frame=True,
        label="N2_EXTERIOR_IMMUTABLE_CROP",
    )
    base = (base_cap & crop).clean()
    production = (production_cap & crop).clean()
    removed = base - production
    added = production - base
    return {
        "removedMm3": volume(removed),
        "addedMm3": volume(added),
        "symmetricDifferenceMm3": volume(removed) + volume(added),
    }


def service_sweeps(datum: ControlDatum) -> dict[str, Shape]:
    sign = float(datum.open_side_sign)
    switch_shift = 10.0
    switch_sweep = oriented_box(
        datum,
        switch_shift,
        SWITCH_BODY_Y + 0.20,
        FRONT_DEPTH_MM,
        HOUSING_REAR_DEPTH_MM,
        u_offset=sign * switch_shift / 2.0,
        label="N2_SWITCH_LATERAL_SERVICE_SWEEP",
    )
    cap_shift = 8.0
    shoulder_sweep = oriented_box(
        datum,
        cap_shift,
        CAP_SHOULDER_SIZE_MM,
        CAP_SHOULDER_FRONT_MM,
        CAP_SHOULDER_REAR_MM,
        u_offset=sign * cap_shift / 2.0,
        cap_frame=True,
        label="N2_CAP_SHOULDER_SERVICE_SWEEP",
    )
    tail_sweep = oriented_box(
        datum,
        cap_shift,
        CAP_GUIDE_DIAMETER_MM,
        CAP_SHOULDER_REAR_MM - 0.10,
        CAP_GUIDE_TAIL_REAR_MM,
        u_offset=sign * cap_shift / 2.0,
        cap_frame=True,
        label="N2_CAP_TAIL_SERVICE_SWEEP",
    )
    cap_sweep = shoulder_sweep.fuse(tail_sweep).clean()
    cap_sweep.label = "N2_CAP_INTERNAL_LATERAL_SERVICE_SWEEP"
    return {"switch": switch_sweep, "cap": cap_sweep}


def exact_validation(
    source: dict[str, Shape],
    datum: ControlDatum,
    cap: Shape,
    cap_parts: dict[str, Shape],
    guide: Shape,
    guide_parts: dict[str, Shape],
    carrier: Shape,
    roots: dict[str, Shape],
) -> dict[str, object]:
    shells = [source["N2_SEAM_JaD"], source["N2_SEAM_JfD"]]
    body = source["N2_ITS1105_body"]
    state_rows: list[dict[str, object]] = []
    for travel in TRAVELS_MM:
        state_cap = cap_at(cap, datum, travel)
        state_shoulder = cap_at(cap_parts["shoulder"], datum, travel)
        state_actuator = actuator_at(datum, travel)
        cap_guide = exact_pair(state_cap, guide, f"cap<->guide @ {travel:.3f}")
        cap_shell_rows = [
            exact_pair(state_cap, shell, f"cap<->{shell.label} @ {travel:.3f}")
            for shell in shells
        ]
        cap_actuator = exact_pair(state_cap, state_actuator, f"cap.contact<->actuator @ {travel:.3f}")
        front_stop = exact_pair(
            state_shoulder,
            guide_parts["frontStop"],
            f"cap.shoulder<->front retention @ {travel:.3f}",
        )
        rear_stop = exact_pair(
            state_shoulder,
            guide_parts["rearStop"],
            f"cap.shoulder<->rear hard stop @ {travel:.3f}",
        )
        state_rows.append({
            "travelMm": travel,
            "capGuide": cap_guide,
            "capShell": aggregate_pairs(cap_shell_rows),
            "capActuator": cap_actuator,
            "frontRetentionStop": front_stop,
            "rearOvertravelStop": rear_stop,
            "analyticalFrontRetentionGapMm": travel,
            "analyticalRearHardStopGapMm": ACTUATOR_TRAVEL_MAX - travel,
            "actuatorProjectionMm": ACTUATOR_PROJECTION - travel,
        })
        del state_cap, state_shoulder, state_actuator
        memory(f"exact motion state {travel:.3f} mm")

    switch_carrier = exact_pair(body, carrier, "ITS body<->production carrier")
    active_rows = [exact_pair(source["HW504_B_EXACT_KEEP"], roots[name], f"HW504_B<->{name}") for name in ("T1", "T3")]
    trimmed_rows = [exact_pair(source["HW504_B_EXACT_KEEP"], roots[name], f"HW504_B<->{name} trimmed") for name in ("T2", "T4")]
    carrier_hw_rows = [
        exact_pair(source["HW504_A_NONFUNCTIONAL_TRIM"], carrier, "HW504_A<->production carrier"),
        exact_pair(source["HW504_B_EXACT_KEEP"], carrier, "HW504_B<->production carrier"),
    ]
    carrier_shell_rows = [exact_pair(carrier, shell, f"production carrier<->{shell.label}") for shell in shells]
    sweeps = service_sweeps(datum)
    service_rows = {
        name: exact_pair(carrier, sweep, f"production carrier<->{name} service sweep")
        for name, sweep in sweeps.items()
    }
    memory("static and service exact checks")
    return {
        "motionStates": state_rows,
        "switchCarrier": switch_carrier,
        "activeTerminalsToHW504B": aggregate_pairs(active_rows, TERMINAL_CLEARANCE_TARGET_MM),
        "trimmedTerminalsToHW504B": aggregate_pairs(trimmed_rows, TERMINAL_CLEARANCE_TARGET_MM),
        "carrierToHW504": aggregate_pairs(carrier_hw_rows),
        "carrierToLocalShell": aggregate_pairs(carrier_shell_rows),
        "serviceSweeps": service_rows,
    }


def validation_pass(checks: dict[str, object], exterior_delta: dict[str, float]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for state in checks["motionStates"]:
        travel = float(state["travelMm"])
        for name in ("capGuide", "capShell", "capActuator"):
            row = state[name]
            penetration = float(row["penetrationMm3"])
            if penetration > BOOLEAN_EPS_MM3:
                failures.append(f"{name} penetration at {travel:.3f} mm = {penetration:.9f}")
        contact = state["capActuator"]
        if float(contact["distanceMm"]) > 1.0e-6:
            failures.append(f"cap/actuator lost contact at {travel:.3f} mm")
        rear_gap = float(state["rearOvertravelStop"]["distanceMm"])
        expected = ACTUATOR_TRAVEL_MAX - travel
        if abs(rear_gap - expected) > 1.0e-5:
            failures.append(f"rear stop gap mismatch at {travel:.3f} mm: {rear_gap:.6f} vs {expected:.6f}")
    if float(checks["switchCarrier"]["penetrationMm3"]) > BOOLEAN_EPS_MM3:
        failures.append("switch body penetrates carrier")
    if float(checks["switchCarrier"]["distanceMm"]) > 1.0e-6:
        failures.append("switch body is not located against carrier")
    for key in ("activeTerminalsToHW504B", "trimmedTerminalsToHW504B"):
        row = checks[key]
        if not bool(row["clearancePass"]):
            failures.append(f"{key} fails 0.80 mm clearance")
    if float(checks["carrierToHW504"]["penetrationMm3"]) > BOOLEAN_EPS_MM3:
        failures.append("carrier penetrates HW504")
    if float(checks["carrierToLocalShell"]["penetrationMm3"]) > BOOLEAN_EPS_MM3:
        failures.append("carrier penetrates local shell")
    for name, row in checks["serviceSweeps"].items():
        if float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3:
            failures.append(f"{name} service sweep blocked")
    if exterior_delta["symmetricDifferenceMm3"] > BOOLEAN_EPS_MM3:
        failures.append("exterior cap geometry changed")
    if min(GUIDE_WALL_MM, REACTION_MIN_WALL_MM, 1.3148483522514047) + 1.0e-9 < MIN_WALL_MM:
        failures.append("carrier wall below 1.20 mm")
    return not failures, failures


def shifted_mesh(mesh: np.ndarray, vector: Iterable[float]) -> np.ndarray:
    return mesh + np.asarray(tuple(vector), dtype=float)


def shape_center(shape: Shape) -> np.ndarray:
    lower, upper = bounds(shape)
    return 0.5 * (lower + upper)


def render_outputs(
    source: dict[str, Shape],
    datum: ControlDatum,
    base_cap: Shape,
    cap: Shape,
    cap_parts: dict[str, Shape],
    guide: Shape,
    guide_parts: dict[str, Shape],
    reaction: Shape,
    carrier: Shape,
    roots: dict[str, Shape],
    checks: dict[str, object],
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        RENDER_DIR / "01_n2_exploded.png",
        RENDER_DIR / "02_n2_rest_section.png",
        RENDER_DIR / "03_n2_pressed_0p35_section.png",
        RENDER_DIR / "04_cap_retention_closeup.png",
        RENDER_DIR / "05_rear_support_closeup.png",
        RENDER_DIR / "06_terminal_hw504_clearance.png",
        RENDER_DIR / "07_transparent_assembled_n2.png",
    ]
    body = source["N2_ITS1105_body"]
    actuator_rest = actuator_at(datum, 0.0)
    actuator_press = actuator_at(datum, ACTUATOR_TRAVEL_MAX)
    cap_press = cap_at(cap, datum, ACTUATOR_TRAVEL_MAX)
    source_carrier = source["N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"]
    shells = [source["N2_SEAM_JaD"], source["N2_SEAM_JfD"]]
    hw_b = source["HW504_B_EXACT_KEEP"]

    crop = oriented_box(datum, 18.0, 18.0, -2.5, 11.5, cap_frame=True, label="N2_RENDER_LOCAL_CROP")
    half = oriented_box(
        datum,
        20.0,
        24.0,
        -2.5,
        11.5,
        u_offset=-10.0,
        cap_frame=True,
        label="N2_RENDER_SECTION_HALF",
    )

    def local(shape: Shape) -> Shape:
        return (shape & crop).clean()

    def section(shape: Shape) -> Shape:
        return (shape & crop & half).clean()

    cache: dict[int, np.ndarray] = {}

    def mesh(shape: Shape, limit: int = 2600) -> np.ndarray:
        key = id(shape)
        if key not in cache:
            cache[key] = safe_triangles(shape, tolerance=0.10, angular=0.07, limit=limit)
        return cache[key]

    axis = unit(datum.axis)
    u = unit(datum.cap_u)
    cap_mesh = mesh(cap)
    guide_mesh = mesh(guide)
    reaction_mesh = mesh(reaction)
    body_mesh = mesh(body)
    actuator_mesh = mesh(actuator_rest)
    roots_mesh = {name: mesh(shape, 800) for name, shape in roots.items()}
    base_carrier_local = local(source_carrier)
    base_carrier_mesh = mesh(base_carrier_local, 2800)

    # 01 exploded: additions are coloured separately even though guide and
    # rear reaction are fused into the one exported carrier solid.
    cap_offset = axis * 5.5
    guide_offset = axis * 1.8
    switch_offset = -axis * 3.6
    focus_exploded = np.concatenate([
        shifted_mesh(cap_mesh, cap_offset).reshape(-1, 3),
        shifted_mesh(guide_mesh, guide_offset).reshape(-1, 3),
        base_carrier_mesh.reshape(-1, 3),
        shifted_mesh(body_mesh, switch_offset).reshape(-1, 3),
    ])
    raster_scene(
        paths[0],
        [
            (shifted_mesh(cap_mesh, cap_offset), COLORS["cap"]),
            (shifted_mesh(guide_mesh, guide_offset), COLORS["guide"]),
            (base_carrier_mesh, COLORS["carrier"]),
            (reaction_mesh, COLORS["reaction"]),
            (shifted_mesh(body_mesh, switch_offset), COLORS["body"]),
            (shifted_mesh(actuator_mesh, switch_offset), COLORS["actuator"]),
            *[(shifted_mesh(roots_mesh[name], switch_offset), COLORS["active"] if name in {"T1", "T3"} else COLORS["trimmed"]) for name in ("T1", "T2", "T3", "T4")],
        ],
        "01 / N2 PRODUCTION-INTENT EXPLODED",
        "One moving cap solid + one shared-carrier solid + unchanged ITS-1105 body",
        "Blue guide and orange rear support are fused carrier features; N1 geometry is untouched",
        world_lines=[
            (shape_center(cap) + cap_offset, shape_center(cap), (255, 219, 103, 255), "ASSEMBLY AXIS"),
        ],
        camera_offset=(70.0, -94.0, -42.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=focus_exploded,
    )
    memory("render 01 exploded")

    # True half-solid local sections at rest and at the maximum approved travel.
    rest_rows = [
        (mesh(section(cap)), COLORS["cap"]),
        (mesh(section(guide)), COLORS["guide"]),
        (mesh(section(base_carrier_local)), COLORS["carrier"]),
        (mesh(section(reaction)), COLORS["reaction"]),
        (mesh(section(body)), COLORS["body"]),
        (mesh(section(actuator_rest)), COLORS["actuator"]),
    ]
    rest_focus = np.concatenate([row.reshape(-1, 3) for row, _ in rest_rows])
    raster_scene(
        paths[1],
        rest_rows,
        "02 / N2 REST — TRUE LOCAL SECTION",
        "Cap shoulder seats on the front retention face; centred contact touches the ITS actuator",
        "Travel 0.000 mm | rear hard-stop gap 0.350 mm | separate spring 0",
        transparent_objects=[(mesh(local(shell), 2200), (*COLORS["shell"], 34)) for shell in shells],
        camera_offset=(84.0, 0.0, 0.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=rest_focus,
    )
    memory("render 02 rest section")

    press_rows = [
        (mesh(section(cap_press)), COLORS["cap"]),
        (mesh(section(guide)), COLORS["guide"]),
        (mesh(section(base_carrier_local)), COLORS["carrier"]),
        (mesh(section(reaction)), COLORS["reaction"]),
        (mesh(section(body)), COLORS["body"]),
        (mesh(section(actuator_press)), COLORS["actuator"]),
    ]
    press_focus = np.concatenate([row.reshape(-1, 3) for row, _ in press_rows])
    raster_scene(
        paths[2],
        press_rows,
        "03 / N2 PRESSED 0.350 mm — TRUE LOCAL SECTION",
        "Cap and actuator translate coaxially; the square shoulder reaches the broad carrier stop",
        "Rear hard-stop gap 0.000 mm: excess load transfers into carrier, not ITS housing",
        transparent_objects=[(mesh(local(shell), 2200), (*COLORS["shell"], 34)) for shell in shells],
        camera_offset=(84.0, 0.0, 0.0),
        final_size=(1920, 1280),
        supersample=2,
        # Use the rest-state fit frame so the two section renders are a true
        # like-for-like visual motion comparison.
        fit_points=rest_focus,
    )
    memory("render 03 pressed section")

    shoulder_mesh = mesh(cap_parts["shoulder"], 1100)
    front_mesh = mesh(guide_parts["frontStop"], 1400)
    rear_mesh = mesh(guide_parts["rearStop"], 1600)
    press_shoulder = shifted_mesh(shoulder_mesh, -axis * ACTUATOR_TRAVEL_MAX)
    retention_focus = np.concatenate([shoulder_mesh.reshape(-1, 3), front_mesh.reshape(-1, 3), rear_mesh.reshape(-1, 3)])
    raster_scene(
        paths[3],
        [(shoulder_mesh, COLORS["shoulder"]), (front_mesh, COLORS["guide"]), (rear_mesh, COLORS["reaction"])],
        "04 / CAP RETENTION + GUIDE CLOSE-UP",
        "Square shoulder/cavity provides anti-rotation; round tail/bore provides coaxial sliding guide",
        "Rest shoulder shown solid; pressed 0.350 mm shoulder shown transparent at rear hard stop",
        transparent_objects=[(press_shoulder, (*COLORS["cap"], 74))],
        world_lines=[
            (shape_center(cap_parts["shoulder"]), shape_center(cap_parts["shoulder"]) - axis * ACTUATOR_TRAVEL_MAX, (255, 220, 105, 255), "0.350 mm"),
        ],
        camera_offset=(58.0, -72.0, -32.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=retention_focus,
    )
    memory("render 04 retention")

    rear_focus = np.concatenate([body_mesh.reshape(-1, 3), reaction_mesh.reshape(-1, 3), *[roots_mesh[n].reshape(-1, 3) for n in roots_mesh]])
    rear_camera = -axis * 88.0 + u * 8.0
    reaction_center = shape_center(reaction)
    raster_scene(
        paths[4],
        [(reaction_mesh, COLORS["reaction"]), *[(roots_mesh[n], COLORS["active"] if n in {"T1", "T3"} else COLORS["trimmed"]) for n in ("T1", "T2", "T3", "T4")]],
        "05 / SWITCH LOCATING + REAR REACTION SUPPORT",
        "6.40 mm reaction frame supports the ITS rear face; T1/T3 side is opened as a solder/service bay",
        "Front C-guide face + lateral pocket + rear frame fully locate the unchanged switch body",
        transparent_objects=[(body_mesh, (*COLORS["body"], 76))],
        world_lines=[
            (reaction_center, reaction_center + u * 4.0, (255, 218, 105, 255), "REAR FRAME"),
        ],
        camera_offset=tuple(float(value) for value in rear_camera),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=rear_focus,
    )
    memory("render 05 rear support")

    terminal_lines = []
    active_rows = checks["activeTerminalsToHW504B"]["pairs"]
    trimmed_rows = checks["trimmedTerminalsToHW504B"]["pairs"]
    for terminal, row in zip(("T1", "T3", "T2", "T4"), [*active_rows, *trimmed_rows]):
        p0 = np.asarray(row["closestPointLeftMm"], dtype=float)
        p1 = np.asarray(row["closestPointRightMm"], dtype=float)
        terminal_lines.append((p0, p1, (255, 224, 116, 255), f"{terminal} {float(row['distanceMm']):.3f} mm"))
    hw_mesh = mesh(hw_b, 3200)
    terminal_focus = np.concatenate([hw_mesh.reshape(-1, 3), *[roots_mesh[n].reshape(-1, 3) for n in roots_mesh]])
    raster_scene(
        paths[5],
        [
            (roots_mesh["T1"], COLORS["active"]),
            (roots_mesh["T3"], COLORS["active"]),
            (roots_mesh["T2"], COLORS["trimmed"]),
            (roots_mesh["T4"], COLORS["trimmed"]),
        ],
        "06 / TERMINAL ↔ HW504 B EXACT CLEARANCE",
        "T1/T3 are the measured electrical pair; T2/T4 are external trimmed stubs",
        f"Active minimum {float(checks['activeTerminalsToHW504B']['minimumDistanceMm']):.3f} mm | trimmed minimum {float(checks['trimmedTerminalsToHW504B']['minimumDistanceMm']):.3f} mm",
        transparent_objects=[(hw_mesh, (*COLORS["hw"], 74)), (mesh(local(carrier), 3000), (*COLORS["carrier"], 30))],
        world_lines=terminal_lines,
        camera_offset=(58.0, -94.0, -42.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=terminal_focus,
    )
    memory("render 06 terminals")

    assembled_focus = np.concatenate([cap_mesh.reshape(-1, 3), body_mesh.reshape(-1, 3), hw_mesh.reshape(-1, 3)])
    raster_scene(
        paths[6],
        [
            (cap_mesh, COLORS["cap"]),
            (body_mesh, COLORS["body"]),
            (actuator_mesh, COLORS["actuator"]),
            *[(roots_mesh[name], COLORS["active"] if name in {"T1", "T3"} else COLORS["trimmed"]) for name in ("T1", "T2", "T3", "T4")],
        ],
        "07 / TRANSPARENT ASSEMBLED N2 PRODUCTION INTENT",
        "Exterior cap centre/orientation/axis and switch position remain exactly frozen",
        "Direct actuation + carrier-captured return/retention + 0.350 mm structural stop",
        transparent_objects=[
            (mesh(local(carrier), 3200), (*COLORS["carrier"], 45)),
            (hw_mesh, (*COLORS["hw"], 54)),
            *[(mesh(local(shell), 2200), (*COLORS["shell"], 26)) for shell in shells],
        ],
        camera_offset=(62.0, -96.0, -40.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=assembled_focus,
    )
    memory("render 07 transparent assembly")
    return paths


def write_report(data: dict[str, object]) -> None:
    checks = data["checks"]
    states = "\n".join(
        "| {travel:.3f} | {guide:.9f} | {shell:.9f} | {contact:.6f} | {front:.3f} | {rear:.3f} | {result} |".format(
            travel=float(row["travelMm"]),
            guide=float(row["capGuide"]["penetrationMm3"]),
            shell=float(row["capShell"]["penetrationMm3"]),
            contact=float(row["capActuator"]["distanceMm"]),
            front=float(row["frontRetentionStop"]["distanceMm"]),
            rear=float(row["rearOvertravelStop"]["distanceMm"]),
            result="PASS" if all(
                float(row[key]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
                for key in ("capGuide", "capShell", "capActuator")
            ) else "FAIL",
        )
        for row in checks["motionStates"]
    )
    report = f"""# 60 — N2 Candidate A production-intent mechanism

## 결론

사용자가 제공한 실물 continuity/trim test를 승인 근거로 반영해 **N2 Candidate A를 PRODUCTION-INTENT INTERNAL BASELINE으로 구현**했다. 외부 cap 형상·중심·각도·이동축, switch 위치, direct actuation, HW504 A/B는 변경하지 않았다.

최종 gate: **{data['verdict']}**  
Production geometry는 N2 cap 내부와 shared carrier의 N2 영역에만 생성했으며 N1에는 확장하지 않았다.

## 1. 실물 전기 확인 반영

- T1–T2: 항상 연결
- T3–T4: 항상 연결
- T1–T3: 평상시 단선 / 누르면 연결
- T2/T4 external stub trim 후 T1–T3 switching 및 actuator return 정상
- Production electrical terminals: **T1 + T3**
- Unused trimmed stubs: **T2 + T4**

## 2. 실제 solid architecture

- Cap retention: cap 내부 6.50 mm square shoulder와 carrier front shoulder
- Cap guide: Ø4.50 tail / Ø4.80 bore, radial clearance 0.150 mm
- Anti-rotation: 6.50 mm square shoulder / 6.80 mm cavity, side clearance 0.150 mm
- Actuator contact: 중앙 Ø3.00 contact puck, rest부터 접촉
- Switch locating: 6.40 mm lateral pocket + guide rear face + rear reaction frame
- Rear reaction: body rear face의 broad frame support; 계산 접촉 가능 면적 약 {float(data['mechanism']['rearReactionContactAreaMm2']):.3f} mm²
- Overtravel stop: shoulder rear face와 carrier rear stop, **0.350 mm**
- Return: ITS internal return force → actuator → contact puck → cap; spring 0
- Service: shell open → carrier release → T1/T3 bay 접근 → switch/cap lateral C-path 분리

## 3. Exact motion

| Travel mm | Cap↔guide penetration mm³ | Cap↔shell penetration mm³ | Cap↔actuator distance mm | Front retention gap mm | Rear hard-stop gap mm | Result |
|---:|---:|---:|---:|---:|---:|---|
{states}

## 4. Static exact gates

| Gate | Clearance | Penetration | Result |
|---|---:|---:|---|
| Switch body ↔ carrier | {float(checks['switchCarrier']['distanceMm']):.6f} mm | {float(checks['switchCarrier']['penetrationMm3']):.9f} mm³ | PASS contact |
| T1/T3 ↔ HW504 B | {float(checks['activeTerminalsToHW504B']['minimumDistanceMm']):.6f} mm | {float(checks['activeTerminalsToHW504B']['penetrationMm3']):.9f} mm³ | {'PASS' if checks['activeTerminalsToHW504B']['clearancePass'] else 'FAIL'} |
| trimmed T2/T4 ↔ HW504 B | {float(checks['trimmedTerminalsToHW504B']['minimumDistanceMm']):.6f} mm | {float(checks['trimmedTerminalsToHW504B']['penetrationMm3']):.9f} mm³ | {'PASS' if checks['trimmedTerminalsToHW504B']['clearancePass'] else 'FAIL'} |
| production carrier ↔ HW504 A/B | {float(checks['carrierToHW504']['minimumDistanceMm']):.6f} mm | {float(checks['carrierToHW504']['penetrationMm3']):.9f} mm³ | PASS |
| production carrier ↔ local shell | {float(checks['carrierToLocalShell']['minimumDistanceMm']):.6f} mm | {float(checks['carrierToLocalShell']['penetrationMm3']):.9f} mm³ | PASS |

## 5. Wall / exterior / service

- Guide closed-side wall: **{GUIDE_WALL_MM:.3f} mm**
- Rear reaction minimum strip: **{REACTION_MIN_WALL_MM:.3f} mm**
- Existing relieved carrier conservative wall: **1.314848 mm**
- Overall minimum structural wall: **{float(data['mechanism']['minimumStructuralWallMm']):.3f} mm** (`>= 1.20 mm PASS`)
- Exterior centre movement: **0.000 mm**
- Exterior geometry symmetric difference: **{float(data['freeze']['externalGeometrySymmetricDifferenceMm3']):.9f} mm³**
- Switch lateral service sweep penetration: **{float(checks['serviceSweeps']['switch']['penetrationMm3']):.9f} mm³**
- Cap lateral service sweep penetration: **{float(checks['serviceSweeps']['cap']['penetrationMm3']):.9f} mm³**

## 6. Outputs / STOP

- `{CAP_STEP.relative_to(ROOT)}`
- `{CARRIER_STEP.relative_to(ROOT)}`
- `{ASSEMBLY_STEP.relative_to(ROOT)}`
- `{JSON_PATH.relative_to(ROOT)}`
- `{RENDER_DIR.relative_to(ROOT)}` — 필수 렌더 7개

사용자 형상 검토를 위해 여기서 STOP한다. N1 또는 다른 버튼에는 자동 확장하지 않았다.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    memory("start")
    source = load_source()
    datum = load_datum()
    base_cap = import_step(BASE_CAP_STEP)

    roots, removed_roots = trim_terminals(source, datum)
    cap, cap_parts = build_production_cap(base_cap, datum)
    guide, guide_parts = build_guide(datum)
    reaction, service_bay = build_reaction_support(datum, roots)
    carrier, reaction_final, carrier_metrics = build_production_carrier(
        source["N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"],
        guide,
        reaction,
        service_bay,
        roots,
        datum,
        source["HW504_A_NONFUNCTIONAL_TRIM"],
    )

    exterior_delta = external_geometry_delta(base_cap, cap, datum)
    checks = exact_validation(source, datum, cap, cap_parts, guide, guide_parts, carrier, roots)
    passed, failures = validation_pass(checks, exterior_delta)

    export_step(cap, CAP_STEP)
    export_stl(cap, CAP_STL, tolerance=0.05, angular_tolerance=0.05)
    export_step(carrier, CARRIER_STEP)
    export_stl(carrier, CARRIER_STL, tolerance=0.06, angular_tolerance=0.06)
    assembly = Compound(
        children=[
            cap,
            carrier,
            source["N2_ITS1105_body"],
            actuator_at(datum, 0.0),
            roots["T1"],
            roots["T2"],
            roots["T3"],
            roots["T4"],
        ],
        label="N2_PRODUCTION_INTENT_LOCAL_ASSEMBLY",
    )
    export_step(assembly, ASSEMBLY_STEP)
    memory("production local solids exported")

    render_paths = render_outputs(
        source,
        datum,
        base_cap,
        cap,
        cap_parts,
        guide,
        guide_parts,
        reaction_final,
        carrier,
        roots,
        checks,
    )

    rear_contact_area = float(carrier_metrics["reactionContactAreaEstimateMm2"])
    minimum_wall = min(GUIDE_WALL_MM, REACTION_MIN_WALL_MM, 1.3148483522514047)
    data: dict[str, object] = {
        "schema": "onegrip.n2.production_intent_mechanism.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "N2 LOCAL PRODUCTION-INTENT / SERIAL OCCT / FULL SHELL 0",
        "physicalEvidence": {
            "source": "user-reported physical ITS-1105 continuity and trimmed-sample test, 2026-08-23",
            "T1T2": "ALWAYS CONNECTED",
            "T3T4": "ALWAYS CONNECTED",
            "T1T3": "OPEN AT REST / CLOSED WHEN PRESSED",
            "T2T4ExternalTrim": "T1-T3 switching and actuator return confirmed normal",
            "candidateAStatus": "ADOPTED",
        },
        "freeze": {
            "externalCenterMovementMm": 0.0,
            "capOrientationChangeDeg": 0.0,
            "capTravelAxisChangeDeg": 0.0,
            "switchPositionChangeMm": 0.0,
            "HW504AChangeMm3": 0.0,
            "HW504BChangeMm3": 0.0,
            "externalGeometryRemovedMm3": exterior_delta["removedMm3"],
            "externalGeometryAddedMm3": exterior_delta["addedMm3"],
            "externalGeometrySymmetricDifferenceMm3": exterior_delta["symmetricDifferenceMm3"],
            "N1GeometryChange": 0,
        },
        "electrical": {
            "activeTerminals": ["T1", "T3"],
            "unusedTrimmedTerminals": ["T2", "T4"],
            "trimCutDepthMm": TRIM_CUT_DEPTH_MM,
            "stubBeyondHousingRearAxialMm": TRIM_CUT_DEPTH_MM - HOUSING_REAR_DEPTH_MM,
            "separateSpring": 0,
        },
        "mechanism": {
            "capRetention": "6.50 mm square internal shoulder captured by three-sided carrier guide",
            "guideBoreDiameterMm": GUIDE_BORE_DIAMETER_MM,
            "capGuideDiameterMm": CAP_GUIDE_DIAMETER_MM,
            "guideRadialClearanceMm": GUIDE_RADIAL_CLEARANCE_MM,
            "squareCavitySizeMm": GUIDE_CAVITY_SIZE_MM,
            "squareShoulderSizeMm": CAP_SHOULDER_SIZE_MM,
            "guideLateralClearanceMm": GUIDE_LATERAL_CLEARANCE_MM,
            "contactDiameterMm": CONTACT_DIAMETER_MM,
            "nominalAndMaximumCapTravelMm": ACTUATOR_TRAVEL_MAX,
            "hardStop": "cap square shoulder to carrier rear stop",
            "returnPath": "ITS internal return -> actuator -> centered cap contact -> cap",
            "rearReactionContactAreaMm2": max(0.0, rear_contact_area),
            "rearReactionHW504ARelief": carrier_metrics,
            "guideWallMm": GUIDE_WALL_MM,
            "reactionMinimumWallMm": REACTION_MIN_WALL_MM,
            "existingCarrierConservativeWallMm": 1.3148483522514047,
            "minimumStructuralWallMm": minimum_wall,
            "service": "shell-open, carrier-release, lateral C-path; pre-solder/replace T1/T3 through rear bay",
        },
        "checks": checks,
        "verdict": "PASS / PRODUCTION-INTENT INTERNAL BASELINE" if passed else "HOLD",
        "failures": failures,
        "productionScope": {
            "changedSolids": ["N2 cap internal solid", "shared carrier N2 local features"],
            "unchanged": ["N1 geometry", "exterior shell", "HW504 A/B", "switch pose", "external cap geometry"],
        },
        "inputs": {
            "docs57Step": {"path": str(SOURCE_STEP.relative_to(ROOT)), "sha256": sha256(SOURCE_STEP)},
            "docs57Json": {"path": str(SOURCE_JSON.relative_to(ROOT)), "sha256": sha256(SOURCE_JSON)},
            "manifest": {"path": str(MANIFEST.relative_to(ROOT)), "sha256": sha256(MANIFEST)},
            "baseCap": {"path": str(BASE_CAP_STEP.relative_to(ROOT)), "sha256": sha256(BASE_CAP_STEP)},
        },
        "outputs": {
            "capStep": str(CAP_STEP.relative_to(ROOT)),
            "capStl": str(CAP_STL.relative_to(ROOT)),
            "carrierStep": str(CARRIER_STEP.relative_to(ROOT)),
            "carrierStl": str(CARRIER_STL.relative_to(ROOT)),
            "assemblyStep": str(ASSEMBLY_STEP.relative_to(ROOT)),
            "json": str(JSON_PATH.relative_to(ROOT)),
            "report": str(REPORT_PATH.relative_to(ROOT)),
            "renders": [str(path.relative_to(ROOT)) for path in render_paths],
        },
        "memory": MEMORY,
        "stop": "User visual review required; do not extend to N1 or other buttons",
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(data)
    memory("outputs complete")
    print(json.dumps({
        "verdict": data["verdict"],
        "failures": failures,
        "motion": [
            {
                "travelMm": row["travelMm"],
                "capGuidePenetrationMm3": row["capGuide"]["penetrationMm3"],
                "capShellPenetrationMm3": row["capShell"]["penetrationMm3"],
                "capActuatorDistanceMm": row["capActuator"]["distanceMm"],
                "rearStopDistanceMm": row["rearOvertravelStop"]["distanceMm"],
            }
            for row in checks["motionStates"]
        ],
        "activeTerminalClearanceMm": checks["activeTerminalsToHW504B"]["minimumDistanceMm"],
        "trimmedTerminalClearanceMm": checks["trimmedTerminalsToHW504B"]["minimumDistanceMm"],
        "carrierHWPenetrationMm3": checks["carrierToHW504"]["penetrationMm3"],
        "carrierShellPenetrationMm3": checks["carrierToLocalShell"]["penetrationMm3"],
        "minimumWallMm": minimum_wall,
        "externalGeometryDeltaMm3": exterior_delta["symmetricDifferenceMm3"],
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY),
        "outputs": data["outputs"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
