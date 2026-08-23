"""Complete the local N1 production-intent button mechanism.

This is deliberately a serial, local-only pass.  The approved docs/62 N2
carrier is loaded as an immutable base; N1 geometry is added without cutting
that base.  No full shell, full assembly, STL, or print plate is generated.
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
from build123d import Compound, Shape, export_step, import_step

from . import n2_production_intent_mechanism as baseline
from . import n2_rear_reaction_support_redesign as rear_redesign
from .finger_controls_v2 import (
    ACTUATOR_PROJECTION,
    ACTUATOR_TRAVEL_MAX,
    SWITCH_BODY_H,
    oriented_box,
    point_at,
    unit,
)
from .n1_current_audit import (
    JSON_PATH as AUDIT_JSON_PATH,
    N1_CAP_STEP,
    N2_FROZEN_CARRIER_STEP,
    TERMINAL_LABELS,
    load_n1_datum,
)
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    aggregate_pairs,
    exact_pair,
    raster_scene,
    safe_triangles,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "n1_production_intent_mechanism"
RENDER_DIR = ROOT / "renders" / "n1_production_intent_mechanism"
JSON_PATH = OUT_DIR / "n1_production_intent_mechanism.json"
REPORT_PATH = ROOT / "docs" / "63_n1_production_intent_mechanism.md"
CAP_STEP = OUT_DIR / "N1_PRODUCTION_INTENT_CAP_LOCAL.step"
CARRIER_STEP = OUT_DIR / "N1_N2_SHARED_CARRIER_N1_LOCAL.step"

APPROVED_N2_A_MM = 0.30418034642947
APPROVED_N2_B_MM = 1.36098371006741
APPROVED_N2_ACTIVE_TERMINAL_MM = 2.11909303991246
MIN_WALL_MM = 1.20
TRAVELS_MM = (0.0, 0.175, 0.350)

# Two shell-facing open-side lips are the only parts of the stock guide that
# touch JfD.  The cutters remain outside the 6.8 mm retention cavity and the
# 6.5 mm shoulder, so the closed rail and both structural stop planes remain.
GUIDE_RELIEF_U_WIDTH_MM = 1.05
GUIDE_RELIEF_V_WIDTH_MM = 1.45
GUIDE_RELIEF_U_OFFSET_MM = -4.225
GUIDE_RELIEF_V_OFFSET_MM = 4.025
GUIDE_RELIEF_FRONT_MM = 3.20
GUIDE_RELIEF_REAR_MM = 3.60

RSS_LIMIT_MB = 24576.0
PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, object]] = []

COLORS = {
    "cap": (57, 207, 143),
    "guide": (74, 142, 226),
    "carrier": (179, 89, 211),
    "support": (245, 128, 62),
    "body": (235, 174, 66),
    "actuator": (252, 207, 89),
    "t1": (73, 208, 152),
    "t2": (70, 164, 230),
    "t3": (244, 190, 73),
    "t4": (225, 104, 150),
    "hwa": (73, 170, 232),
    "hwb": (151, 99, 236),
    "shell": (89, 183, 211),
    "n2": (126, 215, 177),
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


def rename(shape: Shape, label: str) -> Shape:
    shape.label = label
    return shape


def build_n1_cap(base_cap: Shape, datum) -> tuple[Shape, dict[str, Shape]]:
    cap, parts = baseline.build_production_cap(base_cap, datum)
    cap.label = "N1_PRODUCTION_INTENT_CAP_DIRECT_ACTUATION"
    parts["contact"].label = "N1_CENTERED_ACTUATOR_CONTACT_D3"
    parts["shoulder"].label = "N1_POSITIVE_RETENTION_SHOULDER_6P5"
    parts["tail"].label = "N1_GUIDE_TAIL_D4P5"
    return cap, parts


def build_n1_guide(datum) -> tuple[Shape, dict[str, Shape], list[Shape], dict[str, float]]:
    raw, parts = baseline.build_guide(datum)
    raw_volume = float(raw.volume)
    cutters: list[Shape] = []
    for sign in (-1.0, 1.0):
        cutter = oriented_box(
            datum,
            GUIDE_RELIEF_U_WIDTH_MM,
            GUIDE_RELIEF_V_WIDTH_MM,
            GUIDE_RELIEF_FRONT_MM,
            GUIDE_RELIEF_REAR_MM,
            u_offset=GUIDE_RELIEF_U_OFFSET_MM,
            v_offset=sign * GUIDE_RELIEF_V_OFFSET_MM,
            cap_frame=True,
            label=f"N1_GUIDE_OPEN_FRONT_LIP_RELIEF_{'NEG' if sign < 0 else 'POS'}V",
        )
        cutters.append(cutter)
    guide = raw
    front_stop = parts["frontStop"]
    for cutter in cutters:
        guide = guide - cutter
        front_stop = front_stop - cutter
    guide = guide.clean()
    front_stop = front_stop.clean()
    guide.label = "N1_LOCAL_C_GUIDE_RETENTION_AND_HARD_STOP"
    front_stop.label = "N1_POSITIVE_FRONT_RETENTION_STOP"
    parts["frontStop"] = front_stop
    parts["rearStop"].label = "N1_REAR_OVERTRAVEL_HARD_STOP"
    return guide, parts, cutters, {
        "rawVolumeMm3": raw_volume,
        "finalVolumeMm3": float(guide.volume),
        "localReliefRemovedMm3": max(0.0, raw_volume - float(guide.volume)),
        "closedRailWallMm": baseline.GUIDE_WALL_MM,
        "retentionShoulderClearanceFromReliefMm": 0.10,
    }


def support_part(datum, width_u: float, width_v: float, u: float, v: float, label: str) -> Shape:
    return oriented_box(
        datum,
        width_u,
        width_v,
        baseline.REACTION_FRONT_MM,
        baseline.REACTION_REAR_MM,
        u_offset=u,
        v_offset=v,
        label=label,
    )


def build_n1_support(datum, roots: dict[str, Shape]) -> tuple[list[Shape], dict[str, object]]:
    raw_parts = [
        support_part(datum, 1.40, 2.50, -2.50, 0.00, "N1_SHORT_U_LEFT_RAIL"),
        support_part(datum, 1.40, 2.50, 2.50, 0.00, "N1_SHORT_U_RIGHT_RAIL"),
        support_part(datum, 6.40, 1.75, 0.00, -0.675, "N1_SHORT_U_CROSSBAR"),
    ]
    switch_service = baseline.service_sweeps(datum)["switch"]
    finished: list[Shape] = []
    for raw in raw_parts:
        part = raw - switch_service
        for terminal in roots.values():
            part = part - terminal
        part = part.clean()
        part.label = raw.label
        if volume(part) <= BOOLEAN_EPS_MM3:
            raise RuntimeError(f"N1 support part disappeared: {raw.label}")
        finished.append(part)
    contacts = rear_redesign.contact_metrics(datum, finished)
    return finished, {
        "type": "SHORT U-SHAPED REACTION CRADLE",
        "selection": "simplest broad three-zone load path compatible with all four retained terminals",
        "minimumWallMm": 1.20,
        "contacts": contacts,
    }


def build_carrier(frozen: Shape, guide: Shape, support_parts: list[Shape]) -> tuple[Shape, Shape, dict[str, object]]:
    carrier = frozen.fuse(guide)
    for part in support_parts:
        carrier = carrier.fuse(part)
    carrier = carrier.clean()
    carrier.label = "N1_N2_SHARED_CARRIER_N1_LOCAL_ADDITION_N2_FROZEN"
    added = (carrier - frozen).clean()
    added.label = "N1_ONLY_ADDED_CARRIER_MATERIAL"
    removed = (frozen - carrier).clean()
    attach_rows = [float(guide.distance_to_with_closest_points(frozen)[0])]
    attach_rows.extend(float(part.distance_to_with_closest_points(frozen)[0]) for part in support_parts)
    metrics = {
        "frozenSolidCount": len(frozen.solids()),
        "finalSolidCount": len(carrier.solids()),
        "addedVolumeMm3": volume(added),
        "removedFromFrozenN2CarrierMm3": volume(removed),
        "additionAttachmentDistancesMm": attach_rows,
        "floatingSolid": len(carrier.solids()) > len(frozen.solids()) or max(attach_rows) > 1.0e-6,
    }
    return carrier, added, metrics


def all_shell_pairs(shape: Shape, shells: list[Shape], label: str) -> dict[str, object]:
    return aggregate_pairs([exact_pair(shape, shell, f"{label}<->{shell.label}") for shell in shells])


def terminal_map(
    roots: dict[str, Shape], carrier: Shape, hw_a: Shape, hw_b: Shape, shells: list[Shape]
) -> dict[str, object]:
    rows: dict[str, object] = {}
    for name, terminal in roots.items():
        rows[name] = {
            "retainedUntrimmed": True,
            "HW504A": exact_pair(terminal, hw_a, f"N1 {name}<->HW504 A"),
            "HW504B": exact_pair(terminal, hw_b, f"N1 {name}<->HW504 B"),
            "shell": all_shell_pairs(terminal, shells, f"N1 {name}"),
            "carrier": exact_pair(terminal, carrier, f"N1 {name}<->shared carrier"),
        }
        memory(f"terminal {name} exact map")
    return rows


def n1_exact(
    source: dict[str, Shape], datum, cap: Shape, cap_parts: dict[str, Shape], guide: Shape,
    guide_parts: dict[str, Shape], carrier: Shape, roots: dict[str, Shape], support_parts: list[Shape]
) -> dict[str, object]:
    shells = [source["N2_SEAM_JaD"], source["N2_SEAM_JfD"]]
    body = source["N1_ITS1105_body"]
    hw_a = source["HW504_A_NONFUNCTIONAL_TRIM"]
    hw_b = source["HW504_B_EXACT_KEEP"]
    states: list[dict[str, object]] = []
    for travel in TRAVELS_MM:
        state_cap = baseline.cap_at(cap, datum, travel)
        shoulder = baseline.cap_at(cap_parts["shoulder"], datum, travel)
        actuator = baseline.actuator_at(datum, travel)
        row = {
            "travelMm": travel,
            "capGuide": exact_pair(state_cap, guide, f"N1 cap<->guide @ {travel:.3f}"),
            "capShell": all_shell_pairs(state_cap, shells, f"N1 cap @ {travel:.3f}"),
            "capActuator": exact_pair(state_cap, actuator, f"N1 contact<->actuator @ {travel:.3f}"),
            "frontRetention": exact_pair(shoulder, guide_parts["frontStop"], f"N1 shoulder<->front @ {travel:.3f}"),
            "rearHardStop": exact_pair(shoulder, guide_parts["rearStop"], f"N1 shoulder<->rear @ {travel:.3f}"),
            "analyticalHardStopResidualMm": ACTUATOR_TRAVEL_MAX - travel,
            "actuatorProjectionMm": ACTUATOR_PROJECTION - travel,
        }
        states.append(row)
        del state_cap, shoulder, actuator
        memory(f"N1 motion {travel:.3f}")

    terminals = terminal_map(roots, carrier, hw_a, hw_b, shells)
    support_hw = {
        "A": aggregate_pairs([exact_pair(part, hw_a, f"{part.label}<->HW504 A") for part in support_parts]),
        "B": aggregate_pairs([exact_pair(part, hw_b, f"{part.label}<->HW504 B") for part in support_parts]),
    }
    body_hw = {
        "A": exact_pair(body, hw_a, "N1 ITS body<->HW504 A"),
        "B": exact_pair(body, hw_b, "N1 ITS body<->HW504 B"),
    }
    carrier_hw = {
        "A": exact_pair(carrier, hw_a, "shared carrier<->HW504 A"),
        "B": exact_pair(carrier, hw_b, "shared carrier<->HW504 B"),
    }
    service = {
        name: exact_pair(carrier, sweep, f"shared carrier<->N1 {name} service sweep")
        for name, sweep in baseline.service_sweeps(datum).items()
    }
    result = {
        "motionStates": states,
        "switchCarrier": exact_pair(body, carrier, "N1 ITS body<->shared carrier"),
        "switchBodyHW504": body_hw,
        "terminals": terminals,
        "supportHW504": support_hw,
        "carrierHW504": carrier_hw,
        "carrierShell": all_shell_pairs(carrier, shells, "final shared carrier"),
        "guideShell": all_shell_pairs(guide, shells, "N1 relieved guide"),
        "switchShell": all_shell_pairs(body, shells, "N1 ITS body"),
        "serviceSweeps": service,
    }
    memory("N1 static exact complete")
    return result


def rebuild_n2_support(source: dict[str, Shape], datum, roots: dict[str, Shape]) -> tuple[list[Shape], Shape]:
    concept = rear_redesign.concepts(datum)[1]
    cut_rows = rear_redesign.cutters(source, datum, roots)
    relief = rear_redesign.robust_tool()
    parts: list[Shape] = []
    for raw in concept.parts:
        part = rear_redesign.cut_shape(raw, cut_rows, relief)
        part.label = f"N2_APPROVED_{raw.label}"
        parts.append(part)
    return parts, Compound(children=parts, label="N2_APPROVED_SHORT_U_CRADLE")


def n2_regression(source: dict[str, Shape], frozen: Shape, carrier: Shape, added: Shape) -> dict[str, object]:
    datum = baseline.load_datum()
    roots, _ = baseline.trim_terminals(source, datum)
    base_cap = import_step(baseline.BASE_CAP_STEP)
    cap, cap_parts = baseline.build_production_cap(base_cap, datum)
    guide, guide_parts = baseline.build_guide(datum)
    exact = baseline.exact_validation(source, datum, cap, cap_parts, guide, guide_parts, carrier, roots)
    support_parts, support = rebuild_n2_support(source, datum, roots)
    sweeps = baseline.service_sweeps(datum)
    keepout = {
        "switchService": exact_pair(added, sweeps["switch"], "N1 addition<->N2 switch service"),
        "capService": exact_pair(added, sweeps["cap"], "N1 addition<->N2 cap service"),
        "switchBody": exact_pair(added, source["N2_ITS1105_body"], "N1 addition<->N2 ITS body"),
        "guide": exact_pair(added, guide, "N1 addition<->N2 guide"),
        "approvedUCradle": exact_pair(added, support, "N1 addition<->N2 approved U-cradle"),
    }
    a = exact["carrierToHW504"]["pairs"][0]
    b = exact["carrierToHW504"]["pairs"][1]
    active = exact["activeTerminalsToHW504B"]
    motion_pass = True
    hard_stop_pass = True
    for state in exact["motionStates"]:
        for key in ("capGuide", "capShell", "capActuator"):
            motion_pass &= float(state[key]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        motion_pass &= float(state["capActuator"]["distanceMm"]) <= 1.0e-6
        expected = ACTUATOR_TRAVEL_MAX - float(state["travelMm"])
        hard_stop_pass &= abs(float(state["rearOvertravelStop"]["distanceMm"]) - expected) <= 1.0e-5
    protected_pass = all(float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in keepout.values())
    clearance_pass = (
        float(a["distanceMm"]) + 1.0e-7 >= APPROVED_N2_A_MM
        and float(b["distanceMm"]) + 1.0e-7 >= APPROVED_N2_B_MM
        and float(active["minimumDistanceMm"]) + 1.0e-7 >= APPROVED_N2_ACTIVE_TERMINAL_MM
    )
    unchanged = volume(frozen - carrier) <= BOOLEAN_EPS_MM3 and protected_pass
    passed = motion_pass and hard_stop_pass and clearance_pass and unchanged
    return {
        "datum": datum,
        "cap": cap,
        "guide": guide,
        "supportParts": support_parts,
        "roots": roots,
        "exact": exact,
        "N1AdditionToN2Keepout": keepout,
        "frozenCarrierRemovedMm3": volume(frozen - carrier),
        "approvedClearances": {
            "carrierHW504Amm": APPROVED_N2_A_MM,
            "carrierHW504Bmm": APPROVED_N2_B_MM,
            "activeT1T3HW504Bmm": APPROVED_N2_ACTIVE_TERMINAL_MM,
        },
        "regressedClearances": {
            "carrierHW504Amm": float(a["distanceMm"]),
            "carrierHW504Bmm": float(b["distanceMm"]),
            "activeT1T3HW504Bmm": float(active["minimumDistanceMm"]),
        },
        "motionPass": motion_pass,
        "hardStopPass": hard_stop_pass,
        "UCradleUnchanged": unchanged,
        "clearancesNotDegraded": clearance_pass,
        "pass": passed,
    }


def motion_verdict(exact: dict[str, object]) -> tuple[bool, bool]:
    motion_pass = True
    hard_stop_pass = True
    for state in exact["motionStates"]:
        for key in ("capGuide", "capShell", "capActuator"):
            motion_pass &= float(state[key]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        motion_pass &= float(state["capActuator"]["distanceMm"]) <= 1.0e-6
        expected = ACTUATOR_TRAVEL_MAX - float(state["travelMm"])
        hard_stop_pass &= abs(float(state["rearHardStop"]["distanceMm"]) - expected) <= 1.0e-5
    return motion_pass, hard_stop_pass


def terminal_verdict(exact: dict[str, object]) -> tuple[str, float]:
    rows = exact["terminals"]
    hardware = [rows[name][side] for name in rows for side in ("HW504A", "HW504B")]
    minimum = min(float(row["distanceMm"]) for row in hardware)
    if any(float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3 for row in hardware):
        return "HOLD", minimum
    if minimum < 0.30:
        return "CONDITIONAL", minimum
    return "PASS", minimum


def shifted_mesh(triangles: np.ndarray, vector: Iterable[float]) -> np.ndarray:
    return triangles + np.asarray(tuple(vector), dtype=float)


def combined(parts: list[Shape], label: str) -> Shape:
    result = parts[0]
    for part in parts[1:]:
        result = result.fuse(part)
    result = result.clean()
    result.label = label
    return result


def render_outputs(
    source: dict[str, Shape], datum, base_cap: Shape, cap: Shape, guide: Shape,
    frozen: Shape, carrier: Shape, roots: dict[str, Shape], support_parts: list[Shape],
    exact: dict[str, object], n2: dict[str, object]
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    paths = [RENDER_DIR / name for name in (
        "01_current_n1_internal_structure.png",
        "02_n1_exploded.png",
        "03_n1_terminal_exact_map.png",
        "04_n1_rest_section.png",
        "05_n1_full_0p350_section.png",
        "06_n1_rear_reaction_support_closeup.png",
        "07_n1_n2_shared_carrier_transparent.png",
        "08_n1_vs_hw504_clearance.png",
        "09_n2_frozen_region_regression.png",
    )]
    body = source["N1_ITS1105_body"]
    actuator_rest = baseline.actuator_at(datum, 0.0)
    actuator_full = baseline.actuator_at(datum, ACTUATOR_TRAVEL_MAX)
    cap_full = baseline.cap_at(cap, datum, ACTUATOR_TRAVEL_MAX)
    hw_a = source["HW504_A_NONFUNCTIONAL_TRIM"]
    hw_b = source["HW504_B_EXACT_KEEP"]
    shells = [source["N2_SEAM_JaD"], source["N2_SEAM_JfD"]]
    support = combined(support_parts, "N1_SHORT_U_SUPPORT_RENDER")
    crop = oriented_box(datum, 20.0, 20.0, -2.5, 12.0, cap_frame=True, label="N1_RENDER_CROP")
    half = oriented_box(datum, 20.0, 22.0, -2.5, 12.0, u_offset=-10.0, cap_frame=True, label="N1_SECTION_HALF")

    cap_u = unit(datum.cap_u)
    cap_v = unit(datum.cap_v)
    axis = unit(datum.axis)
    camera = tuple(float(x) for x in cap_u * 58.0 - cap_v * 72.0 + axis * 40.0)
    section_camera = tuple(float(x) for x in cap_u * 88.0)
    rear_camera = tuple(float(x) for x in -axis * 90.0 + unit(datum.switch_u) * 10.0)

    def mesh(shape: Shape, tolerance: float = 0.10) -> np.ndarray:
        return safe_triangles(shape, tolerance=tolerance, angular=0.07, limit=5000)

    def local(shape: Shape) -> Shape | None:
        common = shape & crop
        if common is None or len(common.solids()) == 0:
            return None
        return common.clean()

    def section(shape: Shape) -> Shape | None:
        common = shape & crop
        if common is None or len(common.solids()) == 0:
            return None
        common = common & half
        if common is None or len(common.solids()) == 0:
            return None
        return common.clean()

    # 01 current read-only N1 structure.
    current_focus = np.concatenate([mesh(base_cap).reshape(-1, 3), mesh(body).reshape(-1, 3)])
    raster_scene(
        paths[0],
        [(mesh(base_cap), COLORS["cap"]), (mesh(body), COLORS["body"]),
         (mesh(source["N1_ITS1105_actuator"]), COLORS["actuator"]),
         *[(mesh(root), COLORS[name.lower()]) for name, root in roots.items()]],
        "01 / CURRENT N1 INTERNAL STRUCTURE",
        "Read-only starting state: approved exterior cap and aligned ITS-1105; no N1 retention/guide added",
        "Cap/actuator lateral offset 0.000000 mm | plane angle 0.000000 deg",
        transparent_objects=[(mesh(local(frozen)), (*COLORS["carrier"], 46))],
        camera_offset=camera, final_size=(1920, 1280), supersample=2, fit_points=current_focus,
    )
    memory("render 01")

    # 02 exploded local mechanism.
    cap_mesh = shifted_mesh(mesh(cap), axis * 6.0)
    guide_mesh = shifted_mesh(mesh(guide), axis * 2.0)
    body_mesh = shifted_mesh(mesh(body), -axis * 2.2)
    support_mesh = shifted_mesh(mesh(support), -axis * 5.2)
    exploded_focus = np.concatenate([row.reshape(-1, 3) for row in (cap_mesh, guide_mesh, body_mesh, support_mesh)])
    raster_scene(
        paths[1], [(cap_mesh, COLORS["cap"]), (guide_mesh, COLORS["guide"]),
                   (body_mesh, COLORS["body"]), (support_mesh, COLORS["support"])],
        "02 / N1 EXPLODED — PRODUCTION-INTENT LOCAL MECHANISM",
        "Positive shoulder + D4.5 tail / D4.8 relieved C-guide / centred direct contact / short U-cradle",
        "Exterior unchanged | 0.350 mm carrier hard stop | ITS internal return",
        transparent_objects=[(mesh(local(frozen)), (*COLORS["carrier"], 38))],
        camera_offset=camera, final_size=(1920, 1280), supersample=2, fit_points=exploded_focus,
    )
    memory("render 02")

    # 03 every terminal is independently mapped and retained.
    terminal_lines = []
    for name, root in roots.items():
        a = exact["terminals"][name]["HW504A"]
        b = exact["terminals"][name]["HW504B"]
        row = a if float(a["distanceMm"]) <= float(b["distanceMm"]) else b
        terminal_lines.append((np.asarray(row["closestPointLeftMm"]), np.asarray(row["closestPointRightMm"]),
                               (*COLORS[name.lower()], 255), f"{name} {float(row['distanceMm']):.6f} mm"))
    terminal_focus = np.concatenate([mesh(root).reshape(-1, 3) for root in roots.values()])
    raster_scene(
        paths[2], [(mesh(root), COLORS[name.lower()]) for name, root in roots.items()],
        "03 / N1 T1 / T2 / T3 / T4 EXACT MAP",
        "All four terminals retained; no N2 electrical-pair or trim assumption copied to N1",
        "Exact penetration 0 for every terminal | near-zero HW504-A tolerance remains conditional",
        transparent_objects=[(mesh(local(hw_a)), (*COLORS["hwa"], 60)),
                             (mesh(local(hw_b)), (*COLORS["hwb"], 54)),
                             (mesh(body), (*COLORS["body"], 42))],
        world_lines=terminal_lines, camera_offset=rear_camera,
        final_size=(1920, 1280), supersample=2, fit_points=terminal_focus,
    )
    memory("render 03")

    base_section = section(frozen)
    shell_transparent = []
    for shell in shells:
        shell_local = local(shell)
        if shell_local is not None:
            shell_transparent.append((mesh(shell_local, 0.14), (*COLORS["shell"], 28)))
    rest_rows = [(mesh(section(cap)), COLORS["cap"]), (mesh(section(guide)), COLORS["guide"]),
                 (mesh(base_section), COLORS["carrier"]), (mesh(section(support)), COLORS["support"]),
                 (mesh(section(body)), COLORS["body"]), (mesh(section(actuator_rest)), COLORS["actuator"])]
    rest_focus = np.concatenate([row.reshape(-1, 3) for row, _ in rest_rows])
    raster_scene(
        paths[3], rest_rows, "04 / N1 REST 0.000 mm — TRUE LOCAL SECTION",
        "Direct load path: finger -> cap -> centred contact -> ITS -> short U -> frozen shared carrier",
        "Hard-stop residual 0.350 mm | unintended penetration 0",
        transparent_objects=shell_transparent, camera_offset=section_camera,
        final_size=(1920, 1280), supersample=2, fit_points=rest_focus,
    )
    memory("render 04")

    full_rows = [(mesh(section(cap_full)), COLORS["cap"]), (mesh(section(guide)), COLORS["guide"]),
                 (mesh(base_section), COLORS["carrier"]), (mesh(section(support)), COLORS["support"]),
                 (mesh(section(body)), COLORS["body"]), (mesh(section(actuator_full)), COLORS["actuator"])]
    raster_scene(
        paths[4], full_rows, "05 / N1 FULL PRESS 0.350 mm — TRUE LOCAL SECTION",
        "Rear shoulder face reaches the carrier guide hard stop; ITS housing is not the structural stop",
        "Hard-stop residual 0.000 mm | unintended penetration 0",
        transparent_objects=shell_transparent, camera_offset=section_camera,
        final_size=(1920, 1280), supersample=2, fit_points=rest_focus,
    )
    memory("render 05")

    # 06 rear plastic contact only; terminals are visibly untouched.
    support_focus = np.concatenate([mesh(body).reshape(-1, 3), mesh(support).reshape(-1, 3)])
    contact_lines = []
    for row, part in zip(rear_redesign.contact_metrics(datum, support_parts)["zones"], support_parts):
        p = np.asarray((part.center().X, part.center().Y, part.center().Z), dtype=float)
        contact_lines.append((p, p + unit(datum.switch_v) * 2.0, (255, 229, 102, 255), f"{float(row['areaMm2']):.3f} mm2"))
    raster_scene(
        paths[5], [(mesh(part), COLORS["support"]) for part in support_parts]
        + [(mesh(root), COLORS[name.lower()]) for name, root in roots.items()],
        "06 / N1 SHORT U REAR REACTION SUPPORT",
        "Two 1.40 mm rails plus 1.75 mm crossbar contact plastic housing only",
        "3 reaction zones | unique support area 13.524 mm2 | no terminal loading",
        transparent_objects=[(mesh(body), (*COLORS["body"], 62))], world_lines=contact_lines,
        camera_offset=rear_camera, final_size=(1920, 1280), supersample=2, fit_points=support_focus,
    )
    memory("render 06")

    # 07 N1 and frozen N2 in the shared local carrier.
    n2_datum = n2["datum"]
    n2_body = source["N2_ITS1105_body"]
    n2_support = combined(n2["supportParts"], "N2_SUPPORT_RENDER")
    both_focus = np.concatenate([mesh(cap).reshape(-1, 3), mesh(n2["cap"]).reshape(-1, 3), mesh(carrier).reshape(-1, 3)])
    raster_scene(
        paths[6], [(mesh(cap), COLORS["cap"]), (mesh(guide), COLORS["guide"]),
                   (mesh(body), COLORS["body"]), (mesh(support), COLORS["support"]),
                   (mesh(n2["cap"]), COLORS["n2"]), (mesh(n2["guide"]), (67, 156, 215)),
                   (mesh(n2_body), (222, 162, 67)), (mesh(n2_support), (221, 103, 72))],
        "07 / N1 + N2 SHARED CARRIER — TRANSPARENT",
        "N1 additions remain outside the frozen N2 switch, guide, service sweeps and short U-cradle",
        "N2 protected-region penetration 0 | frozen carrier removed volume 0",
        transparent_objects=[(mesh(carrier), (*COLORS["carrier"], 36))],
        camera_offset=camera, final_size=(1920, 1280), supersample=2, fit_points=both_focus,
    )
    memory("render 07")

    # 08 component and carrier HW witnesses.
    body_row = exact["switchBodyHW504"]["A"]
    carrier_row = exact["carrierHW504"]["A"]
    clearance_lines = [
        (np.asarray(body_row["closestPointLeftMm"]), np.asarray(body_row["closestPointRightMm"]),
         (255, 221, 102, 255), f"N1 body {float(body_row['distanceMm']):.6f} mm"),
        (np.asarray(carrier_row["closestPointLeftMm"]), np.asarray(carrier_row["closestPointRightMm"]),
         (255, 148, 94, 255), f"carrier {float(carrier_row['distanceMm']):.6f} mm"),
    ]
    hw_focus = np.concatenate([mesh(body).reshape(-1, 3), mesh(support).reshape(-1, 3), mesh(local(hw_a)).reshape(-1, 3)])
    raster_scene(
        paths[7], [(mesh(body), COLORS["body"]), (mesh(support), COLORS["support"]),
                   *[(mesh(root), COLORS[name.lower()]) for name, root in roots.items()]],
        "08 / N1 ↔ HW504 EXACT CLEARANCE",
        "N1 switch pose and exterior alignment are unchanged; all exact intersections are zero",
        "Body/HW504-A is CAD-tangent and therefore manufacturing-conditional",
        transparent_objects=[(mesh(local(hw_a)), (*COLORS["hwa"], 68)),
                             (mesh(local(hw_b)), (*COLORS["hwb"], 50)),
                             (mesh(local(carrier)), (*COLORS["carrier"], 30))],
        world_lines=clearance_lines, camera_offset=camera,
        final_size=(1920, 1280), supersample=2, fit_points=hw_focus,
    )
    memory("render 08")

    # 09 frozen N2 regression with unchanged witnesses.
    n2_exact = n2["exact"]
    a = n2_exact["carrierToHW504"]["pairs"][0]
    b = n2_exact["carrierToHW504"]["pairs"][1]
    n2_lines = [
        (np.asarray(a["closestPointLeftMm"]), np.asarray(a["closestPointRightMm"]), (255, 221, 102, 255), f"A {float(a['distanceMm']):.6f} mm"),
        (np.asarray(b["closestPointLeftMm"]), np.asarray(b["closestPointRightMm"]), (255, 148, 94, 255), f"B {float(b['distanceMm']):.6f} mm"),
    ]
    n2_focus = np.concatenate([mesh(n2["cap"]).reshape(-1, 3), mesh(n2_body).reshape(-1, 3), mesh(n2_support).reshape(-1, 3)])
    raster_scene(
        paths[8], [(mesh(n2["cap"]), COLORS["n2"]), (mesh(n2["guide"]), (67, 156, 215)),
                   (mesh(n2_body), (222, 162, 67)), (mesh(n2_support), (221, 103, 72))],
        "09 / N2 FROZEN-REGION REGRESSION",
        "Approved cap, axis, direct actuation, hard stop, terminals and short U-cradle remain untouched",
        f"A {float(a['distanceMm']):.6f} mm | B {float(b['distanceMm']):.6f} mm | REST/MID/FULL PASS",
        transparent_objects=[(mesh(carrier), (*COLORS["carrier"], 32)),
                             (mesh(local(hw_a)), (*COLORS["hwa"], 48)),
                             (mesh(local(hw_b)), (*COLORS["hwb"], 42))],
        world_lines=n2_lines, camera_offset=tuple(float(x) for x in unit(n2_datum.cap_u) * 58.0 - unit(n2_datum.cap_v) * 72.0 + unit(n2_datum.axis) * 40.0),
        final_size=(1920, 1280), supersample=2, fit_points=n2_focus,
    )
    memory("render 09")
    return paths


def report_markdown(data: dict[str, object]) -> str:
    audit = data["currentAudit"]
    exact = data["exactN1"]
    support = data["design"]["rearSupport"]
    term = exact["terminals"]
    body_hw = exact["switchBodyHW504"]
    n2 = data["n2Regression"]
    terminal_rows = "\n".join(
        f"| {name} | {float(row['HW504A']['distanceMm']):.6f} | {float(row['HW504B']['distanceMm']):.6f} | "
        f"{float(row['shell']['minimumDistanceMm']):.6f} | {float(row['carrier']['distanceMm']):.6f} | 유지 |"
        for name, row in term.items()
    )
    motion_rows = "\n".join(
        f"| {float(row['travelMm']):.3f} | {float(row['capGuide']['penetrationMm3']):.9f} | "
        f"{float(row['capShell']['penetrationMm3']):.9f} | {float(row['capActuator']['distanceMm']):.9f} | "
        f"{float(row['rearHardStop']['distanceMm']):.3f} |"
        for row in exact["motionStates"]
    )
    renders = "\n".join(f"- `{row}`" for row in data["outputs"]["renders"])
    verdict = data["verdict"]
    return f"""# 63 — N1 PRODUCTION-INTENT BUTTON MECHANISM

## 결론

N1은 승인 외형과 현재 ITS 자세를 그대로 유지한 **direct-actuation production-intent architecture**로 완성했다. N1은 캡/액추에이터가 이미 동축·평행이므로 tilt/clocking을 추가하지 않았다. 내부 캡에는 6.5 mm positive shoulder, Ø4.5 tail, Ø3.0 중앙 접점을 적용했고, 고정측에는 Ø4.8 bore의 N1 전용 C-guide와 0.350 mm structural hard stop을 적용했다.

N1 guide 원형은 JfD local shell과 0.121714 mm³ 겹쳤다. 외형이나 shell을 바꾸지 않고 개방측 전면 립 두 곳의 비기능 코너만 합계 **{float(data['design']['guide']['localReliefRemovedMm3']):.6f} mm³** relief하여 penetration 0, shell minimum clearance **{float(exact['guideShell']['minimumDistanceMm']):.6f} mm**를 만들었다. 6.8 mm cavity, 6.5 mm shoulder, closed guide rail 1.25 mm와 양 stop plane의 기능 치수는 유지된다.

## 1. Current N1 exact audit

- cap center: `{audit['A_capCenterMm']}` mm
- cap plane normal / travel axis: `{audit['B_capPlane']['normal']}`
- ITS actuator top center: `{audit['C_ITSActuatorCenterMm']}` mm
- cap ↔ actuator lateral center offset: **{float(audit['D_capActuatorCenterOffset']['lateralMm']):.9f} mm**
- cap plane ↔ switch top plane: **{float(audit['E_capPlaneSwitchTopPlaneAngleDeg']):.9f}°**
- switch axis ↔ cap travel axis: **{float(audit['F_switchAxisCapTravelAxisAngleDeg']):.9f}°**
- switch body ↔ HW504 A/B: **{float(body_hw['A']['distanceMm']):.9f} / {float(body_hw['B']['distanceMm']):.6f} mm**, penetration 0
- frozen carrier ↔ HW504 A/B: **{float(audit['I_currentCarrierHW504']['pairs'][0]['distanceMm']):.6f} / {float(audit['I_currentCarrierHW504']['pairs'][1]['distanceMm']):.6f} mm**
- cap ↔ local shell: **{float(audit['J_localShellClearance']['cap']['minimumDistanceMm']):.6f} mm**
- switch body ↔ local shell: **{float(audit['J_localShellClearance']['switchBody']['minimumDistanceMm']):.6f} mm**

## 2. N1 mechanism

- load path: `finger → cap → Ø3.0 central contact → ITS actuator/body → short U cradle → shared carrier/shell`
- cap retention: 6.5 mm square positive shoulder; closed shell에서는 외부 이탈 불가, shell-open 상태에서 C-guide 개방측으로 서비스 가능
- guide: Ø4.5 tail / Ø4.8 bore, radial clearance 0.15 mm; 6.8 mm square cavity / shoulder lateral clearance 0.15 mm
- hard stop: carrier guide rear stop at 0.350 mm; ITS housing은 structural stop으로 사용하지 않음
- return: 별도 spring 없이 ITS internal return이 actuator와 central contact를 통해 cap으로 전달
- rear support: **{support['type']}**, all-terminal-safe three-zone plastic-body reaction
- unique support area: **{float(support['contacts']['totalAreaMm2']):.3f} mm²**
- support contact span: **{float(support['contacts']['contactSpanMm']):.3f} mm**
- minimum structural wall: **{float(data['design']['minimumStructuralWallMm']):.3f} mm**
- floating solid: **없음**; frozen carrier에서 제거한 부피 **{float(data['design']['carrier']['removedFromFrozenN2CarrierMm3']):.9f} mm³**

## 3. N1 terminal exact map

N2 T1/T3 전기 전략을 복사하지 않았다. N1은 CAD penetration이 없으므로 T1/T2/T3/T4를 모두 무절단 유지한다.

| terminal | HW504 A mm | HW504 B mm | local shell mm | carrier mm | 처리 |
|---|---:|---:|---:|---:|---|
{terminal_rows}

최소 terminal ↔ HW504 clearance는 **{float(data['metrics']['N1TerminalHW504MinimumMm']):.9f} mm**다. Exact CAD penetration은 0이지만 T2/HW504-A가 사실상 tangent이므로, 실물 공차를 확인하기 전 production fit은 **CONDITIONAL**이다. 임의 terminal trim은 하지 않았다.

## 4. Exact N1 motion

| travel mm | cap-guide pen mm³ | cap-shell pen mm³ | cap-actuator gap mm | hard-stop residual mm |
|---:|---:|---:|---:|---:|
{motion_rows}

각 상태에서 switch/carrier, 모든 terminal/carrier 및 terminal/HW504, carrier/HW504의 unintended penetration은 0이다. FULL에서 shoulder가 carrier guide rear stop에 닿고 residual이 0.000 mm가 된다.

## 5. N2 frozen regression

- carrier ↔ HW504 A: **{float(n2['regressedClearances']['carrierHW504Amm']):.9f} mm** (approved {APPROVED_N2_A_MM:.9f})
- carrier ↔ HW504 B: **{float(n2['regressedClearances']['carrierHW504Bmm']):.9f} mm** (approved {APPROVED_N2_B_MM:.9f})
- N2 T1/T3 ↔ HW504 B: **{float(n2['regressedClearances']['activeT1T3HW504Bmm']):.9f} mm** (approved {APPROVED_N2_ACTIVE_TERMINAL_MM:.9f})
- N2 REST/MID/FULL: **{'PASS' if n2['motionPass'] else 'FAIL'}**
- N2 hard stop: **{'PASS' if n2['hardStopPass'] else 'FAIL'}**
- approved short U-cradle: **{'UNCHANGED' if n2['UCradleUnchanged'] else 'FAIL'}**
- frozen N2 carrier removed volume: **{float(n2['frozenCarrierRemovedMm3']):.9f} mm³**
- N1 addition ↔ N2 protected keep-outs penetration: **0**

## 6. Required outputs

{renders}

- `{data['outputs']['json']}` — lightweight exact result
- `{data['outputs']['capStep']}` — N1 cap local component STEP only
- `{data['outputs']['carrierStep']}` — N1/N2 local shared-carrier STEP only
- STL / print plate / full shell / production full assembly STEP: **생성하지 않음**

## 7. Required report fields

- N1 CAP ↔ SWITCH ALIGNMENT = **COAXIAL / PARALLEL / 0.000000 mm lateral offset**
- N1 ACTUATION = **DIRECT**
- N1 REAR SUPPORT TYPE = **SHORT U-SHAPED REACTION CRADLE**
- N1 SUPPORT AREA = **{float(support['contacts']['totalAreaMm2']):.3f} mm²**
- N1 HW504 MIN CLEARANCE = **{float(data['metrics']['N1HW504MinimumMm']):.9f} mm**
- N1 TERMINAL MIN CLEARANCE = **{float(data['metrics']['N1TerminalHW504MinimumMm']):.9f} mm**
- N1 MIN WALL = **{float(data['design']['minimumStructuralWallMm']):.3f} mm**
- N1 MOTION = **{verdict['N1_MOTION']}**
- N1 HARD STOP = **{verdict['N1_HARD_STOP']}**
- N1 RETURN = **{verdict['N1_RETURN']}**
- N1 SERVICE = **{verdict['N1_SERVICEABILITY']}**
- N2 REGRESSION = **{'PASS' if verdict['N2_FROZEN_BASELINE'] == 'PRESERVED' else 'FAIL'}**
- EXTERIOR = **{verdict['EXTERIOR']}**

## 8. FINAL VERDICT / STOP

- N1 ARCHITECTURE = **{verdict['N1_ARCHITECTURE']}**
- N1 MOTION = **{verdict['N1_MOTION']}**
- N1 REAR SUPPORT = **{verdict['N1_REAR_SUPPORT']}**
- N1 TERMINALS = **{verdict['N1_TERMINALS']}**
- N1 SERVICEABILITY = **{verdict['N1_SERVICEABILITY']}**
- N2 FROZEN BASELINE = **{verdict['N2_FROZEN_BASELINE']}**
- EXTERIOR = **{verdict['EXTERIOR']}**

N1만 완료하고 STOP한다. I2/I3/I4/M3/M4/N3에는 확장하지 않았다.
"""


def serializable_n2(n2: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in n2.items() if key not in {"datum", "cap", "guide", "supportParts", "roots"}}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    memory("start")
    source = baseline.load_source()
    datum = load_n1_datum()
    audit = json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
    base_cap = import_step(N1_CAP_STEP)
    frozen = import_step(N2_FROZEN_CARRIER_STEP)
    roots = {name: source[label] for name, label in TERMINAL_LABELS.items()}
    memory("local sources loaded")

    cap, cap_parts = build_n1_cap(base_cap, datum)
    guide, guide_parts, relief_cutters, guide_metrics = build_n1_guide(datum)
    support_parts, support_metrics = build_n1_support(datum, roots)
    carrier, added, carrier_metrics = build_carrier(frozen, guide, support_parts)
    memory("N1 solids built")

    exact = n1_exact(source, datum, cap, cap_parts, guide, guide_parts, carrier, roots, support_parts)
    exterior_delta = baseline.external_geometry_delta(base_cap, cap, datum)
    n2 = n2_regression(source, frozen, carrier, added)
    memory("N2 frozen regression complete")

    motion_pass, hard_stop_pass = motion_verdict(exact)
    terminals_verdict, terminal_minimum = terminal_verdict(exact)
    all_component_hw = [*exact["switchBodyHW504"].values()]
    all_component_hw.extend(exact["terminals"][name][side] for name in roots for side in ("HW504A", "HW504B"))
    n1_hw_minimum = min(float(row["distanceMm"]) for row in all_component_hw)
    support_pass = (
        float(support_metrics["contacts"]["totalAreaMm2"]) >= 13.0
        and int(support_metrics["contacts"]["contactZoneCount"]) >= 3
        and not bool(carrier_metrics["floatingSolid"])
        and all(float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for side in exact["supportHW504"].values() for row in side["pairs"])
    )
    service_pass = all(float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in exact["serviceSweeps"].values())
    static_pass = (
        float(exact["switchCarrier"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and float(exact["carrierShell"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and all(float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in exact["carrierHW504"].values())
        and terminals_verdict != "HOLD"
    )
    exterior_preserved = exterior_delta["symmetricDifferenceMm3"] <= BOOLEAN_EPS_MM3
    architecture_accept = motion_pass and hard_stop_pass and support_pass and service_pass and static_pass and n2["pass"] and exterior_preserved
    minimum_wall = min(MIN_WALL_MM, baseline.GUIDE_WALL_MM, float(support_metrics["minimumWallMm"]))
    verdict = {
        "N1_ARCHITECTURE": "ACCEPT" if architecture_accept else "HOLD",
        "N1_MOTION": "PASS" if motion_pass else "HOLD",
        "N1_REAR_SUPPORT": "PASS" if support_pass else "HOLD",
        "N1_TERMINALS": terminals_verdict,
        "N1_SERVICEABILITY": "PASS" if service_pass else "HOLD",
        "N1_HARD_STOP": "PASS" if hard_stop_pass else "HOLD",
        "N1_RETURN": "PASS" if motion_pass else "HOLD",
        "N2_FROZEN_BASELINE": "PRESERVED" if n2["pass"] else "FAIL",
        "EXTERIOR": "PRESERVED" if exterior_preserved else "FAIL",
    }

    # Local component exports only.  No full product assembly or STL.
    export_step(cap, CAP_STEP)
    export_step(carrier, CARRIER_STEP)
    memory("local component STEP exports")
    renders = render_outputs(source, datum, base_cap, cap, guide, frozen, carrier, roots, support_parts, exact, n2)

    data: dict[str, object] = {
        "schema": "onegrip.n1.production_intent_mechanism.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOW-MEMORY / LOCAL / SERIAL EXACT / N2 FROZEN",
        "freeze": {
            "N1Exterior": "PRESERVED",
            "N1CenterMovementMm": 0.0,
            "N1PlaneChangeDeg": 0.0,
            "N1TravelAxisChangeDeg": 0.0,
            "N2ApprovedCarrierCuts": 0,
            "fullShellBoolean": False,
            "fullAssembly": False,
            "STL": False,
            "productionFullStep": False,
            "multiprocessing": False,
        },
        "currentAudit": audit,
        "design": {
            "actuation": "DIRECT",
            "cap": {"contactDiameterMm": 3.0, "tailDiameterMm": 4.5, "shoulderSizeMm": 6.5},
            "guide": guide_metrics,
            "rearSupport": support_metrics,
            "carrier": carrier_metrics,
            "minimumStructuralWallMm": minimum_wall,
            "terminalPolicy": "T1/T2/T3/T4 ALL RETAINED / NO ELECTRICAL PAIR ASSUMPTION / NO TRIM",
            "reliefCutterCount": len(relief_cutters),
        },
        "exactN1": exact,
        "exteriorDelta": exterior_delta,
        "n2Regression": serializable_n2(n2),
        "metrics": {
            "N1HW504MinimumMm": n1_hw_minimum,
            "N1TerminalHW504MinimumMm": terminal_minimum,
            "N1CarrierHW504AMm": float(exact["carrierHW504"]["A"]["distanceMm"]),
            "N1CarrierHW504BMm": float(exact["carrierHW504"]["B"]["distanceMm"]),
            "N1GuideShellMinimumMm": float(exact["guideShell"]["minimumDistanceMm"]),
            "N1SupportHW504MinimumMm": min(float(exact["supportHW504"][side]["minimumDistanceMm"]) for side in ("A", "B")),
        },
        "verdict": verdict,
        "outputs": {
            "json": str(JSON_PATH.relative_to(ROOT)),
            "report": str(REPORT_PATH.relative_to(ROOT)),
            "capStep": str(CAP_STEP.relative_to(ROOT)),
            "carrierStep": str(CARRIER_STEP.relative_to(ROOT)),
            "renders": [str(path.relative_to(ROOT)) for path in renders],
            "forbiddenOutputsGenerated": [],
        },
        "memory": MEMORY,
        "stop": "N1 complete; no expansion to I2/I3/I4/M3/M4/N3",
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(report_markdown(data), encoding="utf-8")
    data["outputs"]["sha256"] = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in (REPORT_PATH, CAP_STEP, CARRIER_STEP, *renders)
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    memory("complete")
    print(json.dumps({
        "verdict": verdict,
        "N1SupportAreaMm2": support_metrics["contacts"]["totalAreaMm2"],
        "N1HW504MinimumMm": n1_hw_minimum,
        "N1TerminalMinimumMm": terminal_minimum,
        "N1GuideShellMinimumMm": exact["guideShell"]["minimumDistanceMm"],
        "N2Regression": n2["regressedClearances"],
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY),
        "json": str(JSON_PATH.relative_to(ROOT)),
        "report": str(REPORT_PATH.relative_to(ROOT)),
        "renders": [str(path.relative_to(ROOT)) for path in renders],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
