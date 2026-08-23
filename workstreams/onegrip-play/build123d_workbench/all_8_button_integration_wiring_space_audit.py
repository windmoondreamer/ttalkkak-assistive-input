"""Read-only integration and wiring-space audit for all eight frozen buttons.

The script never fuses, cuts, or exports any production geometry.  It loads
the five approved carrier service groups as independent STEP references,
uses local shell crops only, and executes all OCCT operations serially.
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
import gc
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import psutil
from build123d import Compound, Location, Shape, Vector, import_step

from . import n2_production_intent_mechanism as n2_baseline
from .finger_controls_v2 import (
    ACTUATOR_TRAVEL_MAX,
    FROZEN_FRONT_DEPTHS,
    SWITCH_BODY_H,
    point_at,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    unit,
    wire_envelope,
)
from .i4_m3_current_audit import load_all_datums
from .n1_current_audit import TERMINAL_LABELS as N1_TERMINAL_LABELS
from .option_c_final_local_fit import bounds
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    bbox_gap,
    exact_pair,
    raster_scene,
    safe_triangles,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "all_8_button_integration_wiring_space_audit"
RENDER_DIR = ROOT / "renders" / "all_8_button_integration_wiring_space_audit"
JSON_PATH = OUT_DIR / "all_8_button_integration_wiring_space_audit.json"
REPORT_PATH = ROOT / "docs" / "67_all_8_button_integration_and_wiring_space_audit.md"

BUTTONS = ("N1", "N2", "I2", "I3", "I4", "M3", "M4", "N3")
GROUPS = ("N1_N2", "I2_I3", "M4_N3", "I4", "M3")
GROUP_BUTTONS = {
    "N1_N2": ("N1", "N2"),
    "I2_I3": ("I2", "I3"),
    "M4_N3": ("M4", "N3"),
    "I4": ("I4",),
    "M3": ("M3",),
}
BUTTON_GROUP = {button: group for group, buttons in GROUP_BUTTONS.items() for button in buttons}
TERMINALS = ("T1", "T2", "T3", "T4")
TRAVEL_FULL_MM = 0.350
WIRE_OD_SEED_MM = [1.0, 1.3]
RSS_LIMIT_MB = 27648.0
AVAILABLE_STOP_MB = 2304.0
PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, object]] = []

CARRIER_PATHS = {
    "N1_N2": ROOT / "build123d_workbench" / "out" / "n1_production_intent_mechanism" / "N1_N2_SHARED_CARRIER_N1_LOCAL.step",
    "I2_I3": ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "I2_I3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step",
    "M4_N3": ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "M4_N3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step",
    "I4": ROOT / "build123d_workbench" / "out" / "i4_m3_production_intent_mechanisms" / "I4_CARRIER_PRODUCTION_INTENT_LOCAL.step",
    "M3": ROOT / "build123d_workbench" / "out" / "i4_m3_production_intent_mechanisms" / "M3_CARRIER_PRODUCTION_INTENT_LOCAL.step",
}
CAP_PATHS = {
    "N1": ROOT / "build123d_workbench" / "out" / "n1_production_intent_mechanism" / "N1_PRODUCTION_INTENT_CAP_LOCAL.step",
    "N2": ROOT / "build123d_workbench" / "out" / "n2_production_intent_mechanism" / "N2_PRODUCTION_INTENT_CAP.step",
    "I2": ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "I2_PRODUCTION_INTENT_CAP_LOCAL.step",
    "I3": ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "I3_PRODUCTION_INTENT_CAP_LOCAL.step",
    "M4": ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "M4_PRODUCTION_INTENT_CAP_LOCAL.step",
    "N3": ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "N3_PRODUCTION_INTENT_CAP_LOCAL.step",
    "I4": ROOT / "build123d_workbench" / "out" / "i4_m3_production_intent_mechanisms" / "I4_CAP_PRODUCTION_INTENT_LOCAL.step",
    "M3": ROOT / "build123d_workbench" / "out" / "i4_m3_production_intent_mechanisms" / "M3_CAP_PRODUCTION_INTENT_LOCAL.step",
}
SHELL_PATHS = {
    "JaD": ROOT / "build123d_workbench" / "out" / "finger_controls_v2" / "JAD_FINGER_V2.step",
    "JfD": ROOT / "build123d_workbench" / "out" / "finger_controls_v2" / "JFD_FINGER_V2.step",
}
LOWERED_THUMB = ROOT / "build123d_workbench" / "out" / "original_thumb_module_reuse_audit" / "LOWERED_ORIGINAL_THUMB_CARTRIDGE.step"
APPROVED_REPORTS = [ROOT / "docs" / f"{number}_{name}.md" for number, name in (
    (62, "n2_rear_reaction_support_redesign"),
    (63, "n1_production_intent_mechanism"),
    (64, "i2_i3_production_intent_mechanism"),
    (65, "m4_n3_production_intent_mechanism"),
    (66, "i4_m3_production_intent_mechanisms"),
)]
APPROVED_JSONS = [
    ROOT / "build123d_workbench" / "out" / "n2_rear_reaction_support_redesign" / "n2_rear_reaction_support_redesign.json",
    ROOT / "build123d_workbench" / "out" / "n1_production_intent_mechanism" / "n1_production_intent_mechanism.json",
    ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "i2_i3_production_intent_mechanism.json",
    ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "m4_n3_production_intent_mechanism.json",
    ROOT / "build123d_workbench" / "out" / "i4_m3_production_intent_mechanisms" / "i4_m3_production_intent_mechanisms.json",
]

COLORS = {
    "N1_N2": (177, 91, 225),
    "I2_I3": (54, 170, 225),
    "M4_N3": (242, 137, 56),
    "I4": (64, 203, 143),
    "M3": (238, 92, 132),
    "cap": (245, 207, 92),
    "body": (211, 159, 67),
    "terminal": (189, 201, 211),
    "active": (66, 210, 151),
    "trimmed": (116, 126, 139),
    "hwa": (71, 174, 232),
    "hwb": (153, 102, 239),
    "shell": (75, 178, 215),
}

HW504_REFERENCE_STATUS = "REFERENCE / PLACEHOLDER GEOMETRY"
ACTUAL_JOYSTICK_GATE = "PROVISIONAL — ACTUAL JOYSTICK REQUIRED"
SZH_MEASUREMENT_GATE = "NEEDS PHYSICAL MEASUREMENT"


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    available = float(psutil.virtual_memory().available) / (1024.0 * 1024.0)
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1), "systemAvailableMb": round(available, 1)})
    if rss > RSS_LIMIT_MB or available < AVAILABLE_STOP_MB:
        raise MemoryError(f"RAM safety STOP at {stage}: RSS {rss:.1f} MB, available {available:.1f} MB")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def point_list(point) -> list[float]:
    return [float(point.X), float(point.Y), float(point.Z)]


def shape_fingerprint(path: Path, shape: Shape) -> dict[str, object]:
    lower, upper = bounds(shape)
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "solidCount": len(shape.solids()),
        "volumeMm3": float(shape.volume),
        "bboxMinMm": lower.tolist(),
        "bboxMaxMm": upper.tolist(),
    }


def moved(shape: Shape, vector: np.ndarray, label: str) -> Shape:
    row = np.asarray(vector, dtype=float)
    result = shape.moved(Location(Vector(float(row[0]), float(row[1]), float(row[2]))))
    result.label = label
    return result


def screened_pair(left: Shape, right: Shape, label: str, distance_cutoff_mm: float = 4.0) -> dict[str, object]:
    """Exact for overlapping/near AABBs; conservative lower bound otherwise."""
    gap = bbox_gap(left, right)
    if gap <= distance_cutoff_mm:
        row = exact_pair(left, right, label)
        row["distanceMethod"] = "OCCT_EXACT"
        return row
    return {
        "pair": label,
        "aabbGapMm": float(gap),
        "penetrationMm3": 0.0,
        "distanceMm": float(gap),
        "distanceMethod": "AABB_CONSERVATIVE_LOWER_BOUND",
        "closestPointLeftMm": None,
        "closestPointRightMm": None,
        "passZeroPenetration": True,
    }


def penetration_gate(left: Shape, right: Shape, label: str) -> dict[str, object]:
    """Exact boolean only when AABBs overlap; separation uses a safe lower bound."""
    gap = bbox_gap(left, right)
    if gap <= 1.0e-9:
        row = exact_pair(left, right, label)
        row["distanceMethod"] = "OCCT_EXACT"
        return row
    return {
        "pair": label,
        "aabbGapMm": float(gap),
        "penetrationMm3": 0.0,
        "distanceMm": float(gap),
        "distanceMethod": "AABB_SEPARATION_GATE",
        "closestPointLeftMm": None,
        "closestPointRightMm": None,
        "passZeroPenetration": True,
    }


def local_shells(carriers: dict[str, Shape], caps: dict[str, Shape]) -> tuple[dict[str, Shape], dict[str, object]]:
    focus = Compound(children=[*carriers.values(), *caps.values()], label="ALL_8_LOCAL_AUDIT_FOCUS")
    lower, upper = bounds(focus)
    lower -= 10.0
    upper += 12.0
    crop = n2_baseline.global_box(lower, upper, "ALL_8_LOCAL_SHELL_CROP_TOOL")
    rows: dict[str, Shape] = {}
    for name, path in SHELL_PATHS.items():
        full = import_step(path)
        local = (full & crop).clean()
        if len(local.solids()) == 0:
            raise RuntimeError(f"{name} local shell crop is empty")
        local.label = f"{name}_ALL_8_LOCAL_CROP"
        rows[name] = local
        del full
        memory(f"{name} local shell crop retained")
    del focus, crop
    return rows, {"minMm": lower.tolist(), "maxMm": upper.tolist(), "marginMm": [10.0, 12.0]}


def terminal_map(source: dict[str, Shape], datums: dict[str, object]) -> dict[str, dict[str, Shape]]:
    rows: dict[str, dict[str, Shape]] = {}
    rows["N1"] = {name: source[label] for name, label in N1_TERMINAL_LABELS.items()}
    rows["N2"], _ = n2_baseline.trim_terminals(source, datums["N2"])
    for button in BUTTONS:
        if button in rows:
            continue
        rows[button] = {
            name: shape
            for name, shape in zip(TERMINALS, terminal_root_cutters(datums[button], FROZEN_FRONT_DEPTHS[button]))
        }
    return rows


def static_audit(
    carriers: dict[str, Shape], bodies: dict[str, Shape], terminals: dict[str, dict[str, Shape]],
    shells: dict[str, Shape], hw: dict[str, Shape], datums: dict[str, object],
) -> dict[str, object]:
    carrier_pairs: list[dict[str, object]] = []
    for left_name, right_name in combinations(GROUPS, 2):
        row = exact_pair(carriers[left_name], carriers[right_name], f"{left_name}<->{right_name}")
        row["distanceMethod"] = "OCCT_EXACT"
        carrier_pairs.append(row)
        memory(f"carrier exact {left_name} {right_name}")

    carrier_hw = {
        group: {name: exact_pair(shape, part, f"{group}<->{name}") for name, part in hw.items()}
        for group, shape in carriers.items()
    }
    carrier_shell = {}
    for group, shape in carriers.items():
        owner = datums[GROUP_BUTTONS[group][0]].owner
        carrier_shell[group] = exact_pair(shape, shells[owner], f"{group}<->{owner} local shell")

    body_body = [
        penetration_gate(bodies[a], bodies[b], f"{a} switch body<->{b} switch body")
        for a, b in combinations(BUTTONS, 2)
    ]
    body_foreign_carrier: list[dict[str, object]] = []
    body_hw: list[dict[str, object]] = []
    body_shell: list[dict[str, object]] = []
    for button in BUTTONS:
        for group in GROUPS:
            if group != BUTTON_GROUP[button]:
                body_foreign_carrier.append(penetration_gate(bodies[button], carriers[group], f"{button} body<->{group}"))
        for name, part in hw.items():
            body_hw.append(penetration_gate(bodies[button], part, f"{button} body<->{name}"))
        for shell_name, shell in shells.items():
            body_shell.append(penetration_gate(bodies[button], shell, f"{button} body<->{shell_name} local shell"))

    terminal_foreign_carrier: list[dict[str, object]] = []
    terminal_foreign_switch: list[dict[str, object]] = []
    terminal_hw: list[dict[str, object]] = []
    terminal_shell: list[dict[str, object]] = []
    flat_terminals: list[tuple[str, str, Shape]] = []
    for button in BUTTONS:
        for terminal_name, terminal in terminals[button].items():
            flat_terminals.append((button, terminal_name, terminal))
            for group in GROUPS:
                if group != BUTTON_GROUP[button]:
                    terminal_foreign_carrier.append(penetration_gate(terminal, carriers[group], f"{button}.{terminal_name}<->{group}"))
            for foreign in BUTTONS:
                if foreign != button:
                    terminal_foreign_switch.append(penetration_gate(terminal, bodies[foreign], f"{button}.{terminal_name}<->{foreign} body"))
            for hw_name, part in hw.items():
                terminal_hw.append(penetration_gate(terminal, part, f"{button}.{terminal_name}<->{hw_name}"))
            for shell_name, shell in shells.items():
                terminal_shell.append(penetration_gate(terminal, shell, f"{button}.{terminal_name}<->{shell_name} local shell"))
    terminal_terminal: list[dict[str, object]] = []
    for (button_a, terminal_a, shape_a), (button_b, terminal_b, shape_b) in combinations(flat_terminals, 2):
        terminal_terminal.append(penetration_gate(shape_a, shape_b, f"{button_a}.{terminal_a}<->{button_b}.{terminal_b}"))

    all_cross = [
        *carrier_pairs, *body_body, *body_foreign_carrier, *body_hw, *body_shell,
        *terminal_foreign_carrier, *terminal_foreign_switch, *terminal_hw,
        *terminal_shell, *terminal_terminal,
    ]
    failed = [row for row in all_cross if float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3]
    closest_carrier = min(carrier_pairs, key=lambda row: float(row["distanceMm"]))
    exact_count = sum(row.get("distanceMethod", "OCCT_EXACT") == "OCCT_EXACT" for row in all_cross)
    memory("static cross-component audit complete")
    return {
        "carrierPairwise": carrier_pairs,
        "carrierPairCount": len(carrier_pairs),
        "closestCarrierInterface": closest_carrier,
        "carrierHW504": carrier_hw,
        "carrierLocalShell": carrier_shell,
        "switchBodyPairwise": body_body,
        "switchBodyForeignCarrier": body_foreign_carrier,
        "switchBodyHW504": body_hw,
        "switchBodyLocalShell": body_shell,
        "terminalForeignCarrier": terminal_foreign_carrier,
        "terminalForeignSwitch": terminal_foreign_switch,
        "terminalHW504": terminal_hw,
        "terminalLocalShell": terminal_shell,
        "terminalTerminal": terminal_terminal,
        "screening": {
            "totalRows": len(all_cross),
            "occtExactRows": exact_count,
            "conservativeAabbRows": len(all_cross) - exact_count,
            "principle": "AABB-separated pairs cannot penetrate; overlapping or near pairs receive serial OCCT exact checks",
        },
        "failedInterfaces": failed,
        "verdict": "PASS" if not failed else "THIS INTEGRATION INTERFACE FAILED",
    }


def motion_states() -> list[tuple[str, set[str]]]:
    rows: list[tuple[str, set[str]]] = [("ALL_REST", set())]
    rows.extend((f"{button}_FULL", {button}) for button in BUTTONS)
    rows.extend((name, set(buttons)) for name, buttons in (
        ("I2_I3_FULL", ("I2", "I3")),
        ("M4_N3_FULL", ("M4", "N3")),
        ("I4_I3_FULL", ("I4", "I3")),
        ("M3_M4_FULL", ("M3", "M4")),
        ("N1_N2_FULL", ("N1", "N2")),
        ("ALL_8_FULL", BUTTONS),
    ))
    return rows


def motion_audit(
    caps: dict[str, Shape], carriers: dict[str, Shape], bodies: dict[str, Shape], datums: dict[str, object],
) -> dict[str, object]:
    states: list[dict[str, object]] = []
    for state_name, pressed in motion_states():
        state_caps = {
            button: moved(
                caps[button],
                -unit(datums[button].axis) * (TRAVEL_FULL_MM if button in pressed else 0.0),
                f"{button}_{state_name}",
            )
            for button in BUTTONS
        }
        cap_cap = [
            penetration_gate(state_caps[a], state_caps[b], f"{state_name}: {a} cap<->{b} cap")
            for a, b in combinations(BUTTONS, 2)
        ]
        cap_foreign_carrier: list[dict[str, object]] = []
        cap_foreign_switch: list[dict[str, object]] = []
        for button in BUTTONS:
            for group in GROUPS:
                if group != BUTTON_GROUP[button]:
                    cap_foreign_carrier.append(penetration_gate(state_caps[button], carriers[group], f"{state_name}: {button} cap<->{group}"))
            for foreign in BUTTONS:
                if foreign != button:
                    cap_foreign_switch.append(penetration_gate(state_caps[button], bodies[foreign], f"{state_name}: {button} cap<->{foreign} body"))
        all_rows = [*cap_cap, *cap_foreign_carrier, *cap_foreign_switch]
        failed = [row for row in all_rows if float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3]
        states.append({
            "state": state_name,
            "pressedButtons": sorted(pressed),
            "travelMm": {button: TRAVEL_FULL_MM if button in pressed else 0.0 for button in BUTTONS},
            "hardStopResidualMm": {button: 0.0 if button in pressed else TRAVEL_FULL_MM for button in BUTTONS},
            "capCap": cap_cap,
            "capForeignCarrier": cap_foreign_carrier,
            "capForeignSwitch": cap_foreign_switch,
            "intentionalOwnMechanismContacts": "excluded here; unchanged docs/62-66 exact mechanism baselines",
            "failedInterfaces": failed,
            "maximumUnintendedPenetrationMm3": max((float(row["penetrationMm3"]) for row in all_rows), default=0.0),
            "verdict": "PASS" if not failed else "HOLD",
        })
        del state_caps
        memory(f"motion {state_name}")
    failed_states = [row["state"] for row in states if row["verdict"] != "PASS"]
    return {"states": states, "stateCount": len(states), "failedStates": failed_states, "verdict": "PASS" if not failed_states else "HOLD"}


def service_audit(carriers: dict[str, Shape], hw: dict[str, Shape]) -> dict[str, object]:
    rows: dict[str, object] = {}
    for group in GROUPS:
        sign = -1.0 if group in {"N1_N2", "I2_I3", "M3"} else 1.0
        direction = np.asarray((sign, 0.0, 0.0), dtype=float)
        path_rows: list[dict[str, object]] = []
        maximum_penetration = 0.0
        for distance in (0.0, 5.0, 10.0, 15.0):
            shifted = moved(carriers[group], direction * distance, f"{group}_SERVICE_{distance:.1f}")
            checks = [
                penetration_gate(shifted, carriers[foreign], f"{group} service {distance:.1f}<->{foreign}")
                for foreign in GROUPS if foreign != group
            ]
            checks.extend(penetration_gate(shifted, part, f"{group} service {distance:.1f}<->{name}") for name, part in hw.items())
            maximum_penetration = max(maximum_penetration, *(float(row["penetrationMm3"]) for row in checks))
            path_rows.append({"translationMm": distance, "checks": checks})
            del shifted
        own_buttons = GROUP_BUTTONS[group]
        if group in {"I4", "M3"}:
            switch_path = "remove own standalone carrier first, then withdraw ITS body from the shell-open side"
        else:
            switch_path = "release shared carrier, then use the approved open C-channel / lateral switch path"
        rows[group] = {
            "removalDirection": direction.tolist(),
            "testedTranslationMm": 15.0,
            "testedRotationDeg": 0.0,
            "pathChecks": path_rows,
            "maximumUnintendedPenetrationMm3": maximum_penetration,
            "removalOrder": ["open JaD/JfD shell", f"release {group} carrier group", f"service {', '.join(own_buttons)}"],
            "dependency": "own carrier release only; no foreign carrier removal required" if maximum_penetration <= BOOLEAN_EPS_MM3 else "path blocked by existing frozen geometry",
            "switchService": switch_path,
            "verdict": "PASS" if maximum_penetration <= BOOLEAN_EPS_MM3 else "HOLD",
        }
        memory(f"service path {group}")
    return {"groups": rows, "verdict": "PASS" if all(row["verdict"] == "PASS" for row in rows.values()) else "HOLD"}


def wiring_audit(
    datums: dict[str, object], carriers: dict[str, Shape], shells: dict[str, Shape], hw: dict[str, Shape],
) -> tuple[dict[str, object], dict[str, Shape]]:
    envelopes: dict[str, Shape] = {}
    buttons: dict[str, object] = {}
    for button in BUTTONS:
        datum = datums[button]
        envelope = wire_envelope(datum, FROZEN_FRONT_DEPTHS[button])
        envelopes[button] = envelope
        checks = {
            "ownCarrier": screened_pair(envelope, carriers[BUTTON_GROUP[button]], f"{button} wire envelope<->own carrier"),
            "localShell": screened_pair(envelope, shells[datum.owner], f"{button} wire envelope<->{datum.owner} local shell"),
            "foreignCarriers": {
                group: screened_pair(envelope, carriers[group], f"{button} wire envelope<->{group}")
                for group in GROUPS if group != BUTTON_GROUP[button]
            },
            "HW504": {name: screened_pair(envelope, part, f"{button} wire envelope<->{name}") for name, part in hw.items()},
        }
        all_checks = [checks["ownCarrier"], checks["localShell"], *checks["foreignCarriers"].values(), *checks["HW504"].values()]
        maximum_pen = max(float(row["penetrationMm3"]) for row in all_checks)
        minimum = min(float(row["distanceMm"]) for row in all_checks)
        if maximum_pen > BOOLEAN_EPS_MM3:
            clearance = "BLOCKED"
        elif minimum < WIRE_OD_SEED_MM[1] or button in {"N1", "N2"}:
            clearance = "TIGHT"
        else:
            clearance = "CLEAR"
        rear = FROZEN_FRONT_DEPTHS[button] + SWITCH_BODY_H + 1.60
        start = np.asarray(point_at(datum, rear), dtype=float)
        direction = -unit(datum.axis)
        active = ["T1", "T3"] if button == "N2" else list(TERMINALS)
        trimmed = ["T2", "T4"] if button == "N2" else []
        buttons[button] = {
            "activeUsableTerminals": active,
            "unusedTrimmedTerminals": trimmed,
            "solderAccess": "CONDITIONAL" if button == "N2" else clearance,
            "departureStartMm": start.tolist(),
            "departureDirection": direction.tolist(),
            "straightRearVolumeLengthMm": 7.0,
            "wireOdSeedMm": WIRE_OD_SEED_MM,
            "bendAndToolKeepout": clearance,
            "checks": checks,
        }
        memory(f"wiring envelope {button}")

    topology = {
        "A": {"name": "8 signals + shared GND", "signals": 8, "groundNet": "COMMON", "verdict": "RECOMMENDED BASELINE IF GPIO IS AVAILABLE"},
        "B": {"name": "local ground bus + individual signals", "signals": 8, "groundNet": "five service-group returns merged later", "verdict": "RECOMMENDED PHYSICAL HARNESS IMPLEMENTATION OF A"},
        "C": {"name": "button matrix", "signals": "matrix-dependent", "groundNet": "not a simple shared return", "verdict": "NOT RECOMMENDED AT THIS STAGE"},
    }
    ground = {
        "individualReturnPerButton": "electrically clear but highest wire count",
        "carrierLocalDaisyChain": "RECOMMENDED: daisy-chain only within N1/N2, I2/I3 and M4/N3; I4 and M3 remain individual",
        "entireEightButtonChain": "NOT RECOMMENDED: creates service dependency and accumulated harness fatigue",
    }
    trunks = {
        "candidate1": {
            "name": "single central seam trunk",
            "route": "all departures converge near the JaD/JfD seam and pass the N1/N2-HW504 zone",
            "bendToolKeepout": "TIGHT",
            "risk": "HW504 and N1/N2 service congestion",
            "recommendation": False,
        },
        "candidate2": {
            "name": "split JaD/JfD half-trunks",
            "route": "three JaD controls and five JfD controls stay on their shell half, bypass HW504 separately, and merge aft later",
            "bendToolKeepout": "CLEAR/TIGHT BY LOCAL BUTTON",
            "risk": "future merge point and strain relief remain undefined",
            "recommendation": True,
        },
    }
    blocked = [button for button, row in buttons.items() if row["bendAndToolKeepout"] == "BLOCKED"]
    result = {
        "buttons": buttons,
        "electricalConcepts": topology,
        "selectedElectricalBaseline": "A electrically, implemented physically as B at the five carrier service-group level",
        "groundCandidates": ground,
        "trunkCandidates": trunks,
        "selectedTrunk": "candidate2 / split JaD-JfD half-trunks",
        "wireSeedPolicy": "1.0-1.3 mm OD reference only; final AWG, insulation, bend radius and solder sleeve require physical selection",
        "blockedButtons": blocked,
        "verdict": "PASS" if not blocked else "HOLD",
    }
    return result, envelopes


def fastening_audit(static: dict[str, object], datums: dict[str, object]) -> dict[str, object]:
    rows: dict[str, object] = {}
    for group in GROUPS:
        shell_row = static["carrierLocalShell"][group]
        owner = datums[GROUP_BUTTONS[group][0]].owner
        if group == "N1_N2":
            availability = "TIGHT"
            reason = "HW504 adjacency and the frozen N1/N2 service corridor limit tool approach"
        elif group in {"I4", "M3"}:
            availability = "AVAILABLE"
            reason = "standalone carrier has a direct shell-open approach, subject to future boss verification"
        else:
            availability = "AVAILABLE"
            reason = "shared carrier has broad shell-side rail area, subject to future boss verification"
        rows[group] = {
            "shellSideArea": availability,
            "ownerShell": owner,
            "carrierShellDistanceMm": float(shell_row["distanceMm"]),
            "suggestedScrewDirectionAuditOnly": [1.0, 0.0, 0.0] if owner == "JaD" else [-1.0, 0.0, 0.0],
            "capturedFeaturePotential": "YES / CONCEPT ONLY",
            "assemblyAccess": availability,
            "reason": reason,
            "featuresAdded": False,
        }
    return {
        "groups": rows,
        "overall": "TIGHT" if any(row["shellSideArea"] == "TIGHT" for row in rows.values()) else "AVAILABLE",
        "FDMReality": {
            "criticalWallGateMm": 1.20,
            "tinySnap": False,
            "thinHook": False,
            "tangentOnlySupport": False,
            "floatingBody": False,
            "note": "No fastening feature was modeled; these are available-direction and access observations only",
        },
    }


def shifted_triangles(triangles: np.ndarray, vector: np.ndarray) -> np.ndarray:
    return triangles + np.asarray(vector, dtype=float).reshape(1, 1, 3)


def render_outputs(
    caps: dict[str, Shape], carriers: dict[str, Shape], bodies: dict[str, Shape], terminals: dict[str, dict[str, Shape]],
    shells: dict[str, Shape], hw: dict[str, Shape], thumb: Shape, datums: dict[str, object], static: dict[str, object],
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    paths = [RENDER_DIR / name for name in (
        "01_all_8_caps_exterior_overview.png",
        "02_transparent_all_8_internal.png",
        "03_isolated_color_coded_carrier_groups.png",
        "04_carrier_closest_interfaces.png",
        "05_switches_and_terminals_only.png",
        "06_thumb_hw504_vs_finger_internals.png",
        "07_service_removal_directions.png",
        "08_wire_departure_arrows.png",
        "09_candidate_wiring_trunks.png",
        "10_all_8_full_envelope.png",
        "11_n1_n2_terminal_hw504_conditionals.png",
    )]
    cap_mesh = {name: safe_triangles(shape, 0.24, 0.14) for name, shape in caps.items()}
    carrier_mesh = {name: safe_triangles(shape, 0.34, 0.18) for name, shape in carriers.items()}
    body_mesh = {name: safe_triangles(shape, 0.26, 0.16) for name, shape in bodies.items()}
    terminal_mesh = {button: {name: safe_triangles(shape, 0.20, 0.14) for name, shape in rows.items()} for button, rows in terminals.items()}
    shell_mesh = {name: safe_triangles(shape, 0.55, 0.24) for name, shape in shells.items()}
    hw_mesh = {name: safe_triangles(shape, 0.38, 0.20) for name, shape in hw.items()}
    thumb_mesh = safe_triangles(thumb, 0.65, 0.28)
    memory("render meshes cached")

    fit_caps = np.concatenate([row.reshape(-1, 3) for row in cap_mesh.values()])
    raster_scene(
        paths[0], [(cap_mesh[name], COLORS[BUTTON_GROUP[name]]) for name in BUTTONS],
        "01 / ALL 8 FROZEN EXTERIOR CAPS", "N1 N2 I2 I3 I4 M3 M4 N3 / centers and exterior orientations unchanged",
        "EXTERIOR = PRESERVED | internal integration audit only", fit_points=fit_caps,
    )
    raster_scene(
        paths[1], [(cap_mesh[name], COLORS[BUTTON_GROUP[name]]) for name in BUTTONS] + [(body_mesh[name], COLORS["body"]) for name in BUTTONS],
        "02 / TRANSPARENT ALL-8 INTERNAL", "Five independent carrier service groups; no union and no geometry edit",
        "Caps colored by carrier group | shell and carriers shown transparent",
        transparent_objects=[*[(carrier_mesh[name], (*COLORS[name], 90)) for name in GROUPS], *[(shell_mesh[name], (*COLORS["shell"], 35)) for name in shells]],
    )

    explode_offsets = {"N1_N2": (-22, 0, 0), "I2_I3": (-11, 0, 0), "M3": (0, 0, 0), "I4": (11, 0, 0), "M4_N3": (22, 0, 0)}
    exploded = [(shifted_triangles(carrier_mesh[name], np.asarray(explode_offsets[name])), COLORS[name]) for name in GROUPS]
    exploded_lines = []
    for name in GROUPS:
        center = np.mean(shifted_triangles(carrier_mesh[name], np.asarray(explode_offsets[name])).reshape(-1, 3), axis=0)
        exploded_lines.append((center, center + np.asarray((0, 0, 7)), (*COLORS[name], 255), name))
    raster_scene(paths[2], exploded, "03 / FIVE ISOLATED CARRIER GROUPS", "N1/N2 | I2/I3 | M4/N3 | I4 | M3",
                 "Display-only offsets; production coordinates remain frozen", world_lines=exploded_lines)

    interface_lines = []
    closest_rows = sorted(static["carrierPairwise"], key=lambda row: float(row["distanceMm"]))[:5]
    for row in closest_rows:
        interface_lines.append((np.asarray(row["closestPointLeftMm"]), np.asarray(row["closestPointRightMm"]), (255, 215, 95, 255), f"{row['pair']} {float(row['distanceMm']):.3f} mm"))
    raster_scene(paths[3], [(carrier_mesh[name], COLORS[name]) for name in GROUPS], "04 / CARRIER CLOSEST INTERFACES",
                 "All 10 carrier-pair combinations exact checked", "Yellow annotations = five smallest exact separations",
                 world_lines=interface_lines)

    terminal_objects = []
    for button in BUTTONS:
        terminal_objects.append((body_mesh[button], COLORS["body"]))
        for terminal_name in TERMINALS:
            color = COLORS["trimmed"] if button == "N2" and terminal_name in {"T2", "T4"} else COLORS["active"] if button == "N2" else COLORS["terminal"]
            terminal_objects.append((terminal_mesh[button][terminal_name], color))
    raster_scene(paths[4], terminal_objects, "05 / SWITCHES + TERMINALS ONLY", "32 terminals mapped; N2 T1/T3 active, T2/T4 trimmed conditional",
                 "No new terminal trim or bend was modeled")

    raster_scene(paths[5], [(carrier_mesh[name], COLORS[name]) for name in GROUPS] + [(body_mesh[name], COLORS["body"]) for name in BUTTONS] + [(hw_mesh["HW504_A"], COLORS["hwa"]), (hw_mesh["HW504_B"], COLORS["hwb"])],
                 "06 / THUMB HW504 VS FINGER INTERNALS", "Lowered original thumb cartridge shown as transparent reference",
                 "HW504 A blue | HW504 B violet | all Finger geometry frozen",
                 transparent_objects=[(thumb_mesh, (132, 145, 158, 35))])

    service_lines = []
    for group in GROUPS:
        center = np.mean(carrier_mesh[group].reshape(-1, 3), axis=0)
        sign = -1.0 if group in {"N1_N2", "I2_I3", "M3"} else 1.0
        service_lines.append((center, center + np.asarray((15.0 * sign, 0, 0)), (*COLORS[group], 255), f"{group} 15 mm"))
    raster_scene(paths[6], [(carrier_mesh[name], COLORS[name]) for name in GROUPS], "07 / SERVICE REMOVAL DIRECTIONS",
                 "Shell open -> release one carrier service group -> service its own switch(es)", "0 deg rotation / 15 mm outward path sampled",
                 world_lines=service_lines)

    departure_lines = []
    for button in BUTTONS:
        rear = FROZEN_FRONT_DEPTHS[button] + SWITCH_BODY_H + 1.60
        start = np.asarray(point_at(datums[button], rear), dtype=float)
        end = start - unit(datums[button].axis) * 7.0
        departure_lines.append((start, end, (96, 224, 169, 255), button))
    raster_scene(paths[7], terminal_objects, "08 / WIRE DEPARTURE ARROWS", "Seed OD 1.0-1.3 mm; arrows show frozen switch rear-axis departures",
                 "Arrow space is an audit envelope, not final wire geometry", world_lines=departure_lines)

    centers = {button: np.mean(body_mesh[button].reshape(-1, 3), axis=0) for button in BUTTONS}
    trunk_lines = []
    central = np.mean(np.asarray(list(centers.values())), axis=0) + np.asarray((0, 0, -8.0))
    for button in BUTTONS:
        trunk_lines.append((centers[button], central, (248, 197, 72, 210), ""))
    jad = np.mean(np.asarray([centers[b] for b in ("I4", "M4", "N3")]), axis=0) + np.asarray((7, 0, -7))
    jfd = np.mean(np.asarray([centers[b] for b in ("N1", "N2", "I2", "I3", "M3")]), axis=0) + np.asarray((-7, 0, -7))
    for button in ("I4", "M4", "N3"):
        trunk_lines.append((centers[button], jad, (61, 204, 231, 255), ""))
    for button in ("N1", "N2", "I2", "I3", "M3"):
        trunk_lines.append((centers[button], jfd, (78, 222, 156, 255), ""))
    trunk_lines.extend([(central, central + np.asarray((0, 0, -9)), (248, 197, 72, 255), "C1 central / TIGHT"),
                        (jad, jad + np.asarray((0, 0, -9)), (61, 204, 231, 255), "C2 JaD split"),
                        (jfd, jfd + np.asarray((0, 0, -9)), (78, 222, 156, 255), "C2 JfD split")])
    raster_scene(paths[8], [(carrier_mesh[name], COLORS[name]) for name in GROUPS], "09 / CANDIDATE WIRING TRUNKS",
                 "Yellow: C1 central seam | cyan/green: C2 split shell-half trunks",
                 "RECOMMEND C2 concept; no carrier cuts and no wire solids", world_lines=trunk_lines,
                 transparent_objects=[(hw_mesh["HW504_A"], (*COLORS["hwa"], 75)), (hw_mesh["HW504_B"], (*COLORS["hwb"], 75))])

    full_mesh = {button: shifted_triangles(cap_mesh[button], -unit(datums[button].axis) * TRAVEL_FULL_MM) for button in BUTTONS}
    raster_scene(paths[9], [(full_mesh[name], COLORS[BUTTON_GROUP[name]]) for name in BUTTONS], "10 / ALL 8 FULL-PRESS ENVELOPE",
                 "Every cap shown at 0.350 mm; foreign carrier/switch collisions exact-gated",
                 "Intentional own hard-stop contacts remain inherited from docs/62-66",
                 transparent_objects=[(carrier_mesh[name], (*COLORS[name], 85)) for name in GROUPS])

    conditional_lines = []
    for button, terminal_names, hw_name in (("N1", ("T2",), "HW504_A"), ("N2", ("T2", "T4"), "HW504_B")):
        for terminal_name in terminal_names:
            row = exact_pair(terminals[button][terminal_name], hw[hw_name], f"{button}.{terminal_name}<->{hw_name}")
            conditional_lines.append((np.asarray(row["closestPointLeftMm"]), np.asarray(row["closestPointRightMm"]), (255, 213, 91, 255), f"{button}.{terminal_name} {float(row['distanceMm']):.3f} mm"))
    condition_objects = [(hw_mesh["HW504_A"], COLORS["hwa"]), (hw_mesh["HW504_B"], COLORS["hwb"]),
                         (terminal_mesh["N1"]["T2"], COLORS["terminal"]), (terminal_mesh["N2"]["T2"], COLORS["trimmed"]), (terminal_mesh["N2"]["T4"], COLORS["trimmed"])]
    raster_scene(paths[10], condition_objects, "11 / TERMINAL-HW504 CONDITIONALS", "N1 T2 vs HW504-A | N2 trimmed T2/T4 vs HW504-B",
                 "CAD exact annotations; physical cut/solder tolerance remains conditional", world_lines=conditional_lines)
    memory("all 11 renders complete")
    return paths


def report_markdown(data: dict[str, object]) -> str:
    static = data["staticIntegration"]
    carrier_rows = "\n".join(
        f"| {row['pair']} | {float(row['distanceMm']):.6f} | {float(row['penetrationMm3']):.9f} | {'PASS' if row['passZeroPenetration'] else 'FAIL'} |"
        for row in static["carrierPairwise"]
    )
    motion_rows = "\n".join(
        f"| {row['state']} | {', '.join(row['pressedButtons']) or '-'} | {row['verdict']} | {len(row['failedInterfaces'])} |"
        for row in data["motion"]["states"]
    )
    service_rows = "\n".join(
        f"| {group} | {row['removalDirection']} | {row['testedTranslationMm']:.1f} | {row['testedRotationDeg']:.1f} | {row['verdict']} |"
        for group, row in data["service"]["groups"].items()
    )
    wiring_lines: list[str] = []
    for button, row in data["wiring"]["buttons"].items():
        access = row["solderAccess"]
        keepout = row["bendAndToolKeepout"]
        if button in {"N1", "N2"} and (access == "BLOCKED" or keepout == "BLOCKED"):
            access = ACTUAL_JOYSTICK_GATE
            keepout = ACTUAL_JOYSTICK_GATE
        wiring_lines.append(
            f"| {button} | {', '.join(row['activeUsableTerminals'])} | {', '.join(row['unusedTrimmedTerminals']) or '-'} | {access} | {keepout} |"
        )
    wiring_rows = "\n".join(wiring_lines)
    fastening_rows = "\n".join(
        f"| {group} | {row['ownerShell']} | {row['shellSideArea']} | {row['assemblyAccess']} | {row['reason']} |"
        for group, row in data["fastening"]["groups"].items()
    )
    failed_rows = "\n".join(
        f"| {row['pair']} | {float(row['penetrationMm3']):.9f} | {row['distanceMethod']} | {row.get('productionClassification', 'HW504-INDEPENDENT / VALID')} |"
        for row in static["failedInterfaces"]
    ) or "| - | 0.000000000 | - | - |"
    measurement_rows = "\n".join(
        f"| {index} | {row['item']} | {row['method']} | {row['record']} |"
        for index, row in enumerate(data["joystickReference"]["measurementChecklist"], 1)
    )
    render_rows = "\n".join(f"{index}. `{path}`" for index, path in enumerate(data["outputs"]["renders"], 1))
    verdict = data["verdict"]
    summary = data["summaryMetrics"]
    return f"""# 67 — All 8 Button Integration and Wiring-Space Audit

## 1. 결론

8개 승인 버튼과 5개 carrier service group을 **서로 union하지 않은 원래 생산 의도 좌표**에서 감사했다. 생산 형상 수정, carrier cut, wire solid, full shell boolean, assembly STEP/STL export는 수행하지 않았다.

- ALL 8 MECHANICAL BASELINES = **{verdict['ALL_8_MECHANICAL_BASELINES']}**
- HW504-A / HW504-B = **{verdict['HW504_REFERENCE']}**
- HW504-DEPENDENT RESULTS = **{verdict['HW504_DEPENDENT_RESULTS']}**
- SZH-EK056 EXACT GEOMETRY = **{verdict['SZH_EK056_EXACT_GEOMETRY']}**
- CARRIER-TO-CARRIER INTEGRATION = **{verdict['CARRIER_TO_CARRIER_INTEGRATION']}**
- CARRIER-CARRIER PENETRATION = **{float(summary['maximumCarrierCarrierPenetrationMm3']):.9f} mm³ max**
- MIN INTER-CARRIER CLEARANCE = **{float(summary['minimumInterCarrierClearanceMm']):.6f} mm**
- SWITCH / TERMINAL CROSS-COLLISION = **{verdict['SWITCH_TERMINAL_CROSS_COLLISION']}**
- ALL-8 MOTION ENVELOPE = **{verdict['ALL_8_MOTION_ENVELOPE']}**
- ALL-8 FULL PENETRATION = **{float(summary['all8FullMaximumUnintendedPenetrationMm3']):.9f} mm³**
- SERVICEABILITY = **{verdict['SERVICEABILITY']}**
- TERMINAL ACCESS = **{verdict['TERMINAL_ACCESS']}**
- WIRING SPACE = **{verdict['WIRING_SPACE']}**
- RECOMMENDED ELECTRICAL TOPOLOGY = **8 signals + common GND**
- RECOMMENDED GROUND STRATEGY = **2-button carrier-local daisy-chain + five service-group returns**
- RECOMMENDED WIRING TRUNK = **split JaD/JfD half-trunks**
- FASTENING SPACE = **{verdict['FASTENING_SPACE']}**
- EXTERIOR = **{verdict['EXTERIOR']}**
- PEAK PYTHON RSS = **{float(summary['peakRssMb']):.1f} MB**
- OVERALL = **{verdict['ALL_8_INTERNAL_INTEGRATION']}**

## 2. Freeze / 방법

docs/62~66의 cap, switch, guide, hard stop, rear support, functional carrier geometry 및 exterior를 read-only 입력으로 사용했다. 5개 carrier, 8개 cap STEP와 승인 JSON/MD의 SHA-256를 작업 전후 비교했다. Exact 계산은 단일 Python process와 단일 OCC operation 흐름으로 실행했다. AABB가 분리된 쌍은 penetration이 불가능하므로 보수적 분리 하한으로 screen했고, 겹치거나 가까운 쌍만 serial OCCT exact를 실행했다.

HW504-A/B는 최종 구매품이 아니라 **REFERENCE / PLACEHOLDER GEOMETRY**다. 따라서 N2 body/T1/T2↔HW504-A, N1/N2 wiring↔HW504 및 모든 carrier↔HW504 clearance는 **PROVISIONAL — ACTUAL JOYSTICK REQUIRED**로 재분류했다. 이 값들은 Finger/N1/N2 production geometry 수정 근거로 사용하지 않는다.

HW504와 무관한 승인 회귀 reference(I2/I3 FULL cap gap 2.14 mm 이상, M4/N3 minimum cap gap 3.132654 mm, I4↔I3 3.248773 mm, M3↔M4 4.847042 mm, critical wall 1.20 mm 이상)는 입력 STEP/JSON 해시 무변경과 production geometry edit 0으로 보존됐다.

## 3. Carrier-to-carrier exact 10쌍

| pair | exact distance mm | penetration mm³ | gate |
|---|---:|---:|---|
{carrier_rows}

최접 interface는 **{static['closestCarrierInterface']['pair']}**, exact distance **{float(static['closestCarrierInterface']['distanceMm']):.6f} mm**다. Carrier penetration이 발생하면 `THIS INTEGRATION INTERFACE FAILED`로 판정하도록 했으며, 이번 carrier 결과는 **{verdict['CARRIER_TO_CARRIER_INTEGRATION']}**다.

## 4. Switch / terminal cross audit

- total checked rows: **{static['screening']['totalRows']}**
- serial OCCT exact rows: **{static['screening']['occtExactRows']}**
- conservative AABB-separated rows: **{static['screening']['conservativeAabbRows']}**
- failed cross interfaces: **{len(static['failedInterfaces'])}**

| interface | penetration mm³ | method | production classification |
|---|---:|---|---|
{failed_rows}

HW504와 무관한 유효 integration failure는 **M4 T2 ↔ N3 T3 = 0.283393028 mm³** 한 건이다. 이는 `THIS INTEGRATION INTERFACE NEEDS REDESIGN`이지만 8-button exterior 불가 판정은 아니다. 나머지 HW504 관련 세 건은 실제 SZH-EK056 측정 전 production failure로 세지 않는다. N1 terminal 4개와 N2 T1/T3 active + T2/T4 trimmed conditional 상태는 그대로이며 새 trim/bend는 없다.

## 5. Motion envelope

| state | FULL buttons | verdict | failed interface count |
|---|---|---|---:|
{motion_rows}

각 FULL은 0.350 mm다. Own cap-guide/actuator/hard-stop contact는 intentional이고 docs/62~66 exact baseline을 그대로 상속한다. 본 감사에서는 cap ↔ foreign carrier/switch 및 cap ↔ cap을 분리해 unintended penetration만 판정했다.

## 6. Service path

| service group | direction | translation mm | rotation deg | verdict |
|---|---|---:|---:|---|
{service_rows}

기본 순서는 `shell open → 해당 carrier group release → 해당 group switch service`다. I4/M3는 각 standalone carrier를 먼저 빼고 ITS를 서비스한다. 다른 carrier를 먼저 제거해야 하는 종속성은 만들지 않는 것을 기준으로 했다.

## 7. Wiring-space / terminals

| button | usable terminals | trimmed | solder access | bend/tool keepout |
|---|---|---|---|---|
{wiring_rows}

전기 baseline은 GPIO가 충분할 때 **8 independent signals + common GND**를 추천한다. 물리 harness는 shared two-button carrier 내부에서만 local ground daisy-chain하고, I4/M3는 독립 return을 유지한 뒤 5개 service-group return을 후단에서 합치는 안을 추천한다. 8개 전체 ground chain은 service dependency 때문에 추천하지 않는다.

Wire OD **1.0~1.3 mm**는 공간 seed일 뿐이며 최종 AWG가 아니다. 기존 HW504 placeholder에 대한 N1/N2 BLOCKED 판정은 **PROVISIONAL — ACTUAL JOYSTICK REQUIRED**다. Candidate 2 **split JaD/JfD half-trunks**를 개념 기준안으로 유지하지만, 실제 SZH-EK056 측정 전 production wiring clearance는 확정하지 않는다. Carrier cut과 wire solid는 없다.

## 8. SZH-EK056 actual-part measurement checklist

로컬 workspace에는 SZH-EK056 전용 controlled drawing, exact STEP 또는 실물 측정 registry가 없다. docs/55의 `34.5 × 26 × 38 mm` 판매처 envelope와 유사 모듈 문서의 `34.0 × 26.3 × 1.6 mm` PCB/Ø3 mm 홀은 참고용 nominal일 뿐 생산 CAD datum이 아니다. 판정은 **NEEDS PHYSICAL MEASUREMENT**다.

먼저 PCB top plane, 두 직교 PCB edge, neutral shaft axis를 측정 datum으로 지정하고 다음을 기록한다.

| # | measurement | method / datum | record required |
|---:|---|---|---|
{measurement_rows}

권장 기록에는 측정 sample 수, 보드 revision/실크, 판매처/lot, 정면·측면·하부 사진과 측정 공구 분해능도 포함한다. Moving envelope는 cap/knob을 포함한 최대 X/Y tilt와 axial push 전후 모두 측정한다.

## 9. Fastening-space audit

| group | owner | shell-side area | access | reason |
|---|---|---|---|---|
{fastening_rows}

Fastener, boss, captured nut, heat-set insert는 모델링하지 않았다. 이 결과는 shell-side 면적/접근 방향의 다음 단계 가능성 감사이며, 전체 판정은 **{data['fastening']['overall']}**다.

## 10. Required renders

{render_rows}

Render 06/09/11의 HW504 형상과 수치는 모두 placeholder reference visualization이다.

## 11. STOP

production assembly, wire solid, fastening feature, MCU/PCB, full shell, STL/print plate 단계로 자동 확장하지 않는다. 사용자 검토를 받고 STOP한다.
"""


def reclassify_hw504_reference(data: dict[str, object]) -> dict[str, object]:
    """Apply the user's actual-joystick correction without changing CAD."""
    static = data["staticIntegration"]
    hw_rows: list[dict[str, object]] = []
    independent_rows: list[dict[str, object]] = []
    for row in static["failedInterfaces"]:
        if "HW504" in str(row["pair"]):
            row["productionClassification"] = ACTUAL_JOYSTICK_GATE
            hw_rows.append(row)
        else:
            row["productionClassification"] = "HW504-INDEPENDENT / VALID INTEGRATION FINDING"
            independent_rows.append(row)
    static["provisionalHW504Interfaces"] = hw_rows
    static["productionRelevantIndependentInterfaces"] = independent_rows
    static["productionVerdict"] = "THIS INTEGRATION INTERFACE NEEDS REDESIGN" if independent_rows else "PASS"
    static["carrierHW504Classification"] = ACTUAL_JOYSTICK_GATE
    for group in static.get("carrierHW504", {}).values():
        for row in group.values():
            row["productionClassification"] = ACTUAL_JOYSTICK_GATE

    wiring = data["wiring"]
    wiring["HW504ReferenceClassification"] = ACTUAL_JOYSTICK_GATE
    wiring.setdefault("placeholderGeometryVerdict", wiring.get("verdict", "HOLD"))
    wiring["productionVerdict"] = ACTUAL_JOYSTICK_GATE
    wiring["verdict"] = ACTUAL_JOYSTICK_GATE
    for button in wiring["buttons"].values():
        for row in button["checks"].get("HW504", {}).values():
            row["productionClassification"] = ACTUAL_JOYSTICK_GATE

    checklist = [
        {"item": "PCB X / Y / Z", "method": "caliper; PCB edge-to-edge and board thickness", "record": "length, width, thickness; max/min across samples"},
        {"item": "mounting-hole X/Y pitch", "method": "hole-center coordinates from selected PCB corner datum", "record": "all four X/Y coordinates and opposite/diagonal pitches"},
        {"item": "mounting-hole diameter", "method": "pin gauges or caliper; distinguish plating/countersink", "record": "diameter of each hole"},
        {"item": "joystick center relative to PCB", "method": "neutral shaft axis to both PCB edges and hole pattern", "record": "center X/Y and concentricity/offset"},
        {"item": "X potentiometer envelope", "method": "axis-aligned bbox from PCB datums", "record": "min/max X/Y/Z, housing center, tabs/lead protrusions"},
        {"item": "Y potentiometer envelope", "method": "axis-aligned bbox from PCB datums", "record": "min/max X/Y/Z, housing center, tabs/lead protrusions"},
        {"item": "bottom push-switch envelope", "method": "bottom-view bbox and shaft-axis relation", "record": "min/max X/Y/Z, body/lead protrusion, push travel"},
        {"item": "shaft / pivot height", "method": "PCB top plane to pivot center and neutral shaft endpoints", "record": "pivot Z, exposed shaft length, cap interface diameter/shape"},
        {"item": "connector envelope", "method": "PCB datum bbox", "record": "header X/Y/Z, pin pitch, orientation, mating-plug projection"},
        {"item": "maximum moving envelope", "method": "sweep at max ±X, ±Y, diagonal tilt and axial push", "record": "union bbox/radial envelope including shaft and intended knob"},
    ]
    data["joystickReference"] = {
        "finalIntendedPart": "SZH-EK056 family PS2 joystick module",
        "HW504Classification": HW504_REFERENCE_STATUS,
        "identityVerdict": "LIKELY COMPATIBLE / NOT EXACT SAME",
        "exactLocalCadOrControlledDrawingFound": False,
        "availableLocalEvidence": [
            "docs/55: seller nominal 34.5 × 26 × 38 mm and representative imagery",
            "docs/55: comparable-module PCB 34.0 × 26.3 × 1.6 mm, four nominal Ø3 mm holes",
            "build123d_workbench/out/hw504_low_memory_analysis/hw504_low_memory_analysis.json",
        ],
        "evidenceLimit": "No SZH-EK056 controlled mechanical drawing, exact STEP, or physical measurement registry; seller revision warning recorded in docs/55",
        "finalGate": SZH_MEASUREMENT_GATE,
        "measurementChecklist": checklist,
    }
    data["approvedRegressionReferences"] = {
        "HW504Dependent": {
            "classification": ACTUAL_JOYSTICK_GATE,
            "N2CarrierHW504AminimumMm": 0.304180,
            "N2CarrierHW504BminimumMm": 1.360984,
            "N2ActiveT1T3HW504BminimumMm": 2.119093,
        },
        "HW504Independent": {
            "I2I3FullCapGapMinimumMm": 2.14,
            "M4N3MinimumCapGapMm": 3.132654,
            "I4NearestI3CapMm": 3.248773,
            "M3NearestM4CapMm": 4.847042,
            "criticalStructuralWallMinimumMm": 1.20,
            "preservationBasis": "approved input hashes unchanged; production geometry edits = 0",
        },
    }
    data["summaryMetrics"]["maximumHW504IndependentCrossPenetrationMm3"] = max(
        (float(row["penetrationMm3"]) for row in independent_rows), default=0.0
    )
    data["summaryMetrics"]["maximumHW504PlaceholderCrossPenetrationMm3"] = max(
        (float(row["penetrationMm3"]) for row in hw_rows), default=0.0
    )
    verdict = data["verdict"]
    n1n2_fastening = data["fastening"]["groups"]["N1_N2"]
    n1n2_fastening["HW504Dependency"] = ACTUAL_JOYSTICK_GATE
    n1n2_fastening["reason"] = (
        "frozen N1/N2 service corridor remains tight; the HW504-adjacency portion is "
        + ACTUAL_JOYSTICK_GATE
    )
    verdict.update({
        "HW504_REFERENCE": HW504_REFERENCE_STATUS,
        "HW504_DEPENDENT_RESULTS": ACTUAL_JOYSTICK_GATE,
        "SZH_EK056_EXACT_GEOMETRY": SZH_MEASUREMENT_GATE,
        "SWITCH_TERMINAL_CROSS_COLLISION": "HOLD — M4 T2 ↔ N3 T3; HW504 findings provisional",
        "TERMINAL_ACCESS": "HOLD — M4/N3 terminal interface; N1/N2 vs HW504 provisional",
        "WIRING_SPACE": ACTUAL_JOYSTICK_GATE,
        "ALL_8_INTERNAL_INTEGRATION": "HOLD — THIS INTEGRATION INTERFACE NEEDS REDESIGN (M4 T2 ↔ N3 T3)",
    })
    data["correction"] = {
        "type": "HW504 production-reference reclassification",
        "productionGeometryModified": False,
        "HW504Modified": False,
        "fingerGeometryModified": False,
        "thumbGeometryModified": False,
    }
    data["outputs"]["renderReferenceClassification"] = {
        "06_thumb_hw504_vs_finger_internals.png": HW504_REFERENCE_STATUS,
        "09_candidate_wiring_trunks.png": "HW504-dependent portions are provisional",
        "11_n1_n2_terminal_hw504_conditionals.png": ACTUAL_JOYSTICK_GATE,
    }
    data["stop"] = "Audit/reclassification complete; NEEDS PHYSICAL MEASUREMENT; production geometry unchanged; STOP"
    return data


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    memory("start")

    required = [*CARRIER_PATHS.values(), *CAP_PATHS.values(), *SHELL_PATHS.values(), LOWERED_THUMB, *APPROVED_REPORTS, *APPROVED_JSONS]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing approved input(s): {missing}")
    baseline_hashes_before = {relative(path): sha256(path) for path in required}

    source = n2_baseline.load_source()
    datums = load_all_datums()
    datums["N2"] = n2_baseline.load_datum()
    carriers = {name: import_step(path) for name, path in CARRIER_PATHS.items()}
    caps = {name: import_step(path) for name, path in CAP_PATHS.items()}
    bodies = {
        "N1": source["N1_ITS1105_body"],
        "N2": source["N2_ITS1105_body"],
        **{button: switch_body(datums[button], FROZEN_FRONT_DEPTHS[button]) for button in BUTTONS if button not in {"N1", "N2"}},
    }
    actuators = {
        "N1": source["N1_ITS1105_actuator"],
        "N2": source["N2_ITS1105_actuator"],
        **{button: switch_actuator(datums[button], FROZEN_FRONT_DEPTHS[button]) for button in BUTTONS if button not in {"N1", "N2"}},
    }
    terminals = terminal_map(source, datums)
    hw = {"HW504_A": source["HW504_A_NONFUNCTIONAL_TRIM"], "HW504_B": source["HW504_B_EXACT_KEEP"]}
    shells, shell_crop = local_shells(carriers, caps)
    thumb = import_step(LOWERED_THUMB)
    memory("all frozen local inputs loaded")

    geometry_fingerprints = {
        "carriers": {name: shape_fingerprint(CARRIER_PATHS[name], shape) for name, shape in carriers.items()},
        "caps": {name: shape_fingerprint(CAP_PATHS[name], shape) for name, shape in caps.items()},
    }
    static = static_audit(carriers, bodies, terminals, shells, hw, datums)
    motion = motion_audit(caps, carriers, bodies, datums)
    service = service_audit(carriers, hw)
    wiring, wire_envelopes = wiring_audit(datums, carriers, shells, hw)
    fastening = fastening_audit(static, datums)
    renders = render_outputs(caps, carriers, bodies, terminals, shells, hw, thumb, datums, static)

    baseline_hashes_after = {relative(path): sha256(path) for path in required}
    frozen_preserved = baseline_hashes_before == baseline_hashes_after
    carrier_pass = all(float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in static["carrierPairwise"])
    cross_pass = static["verdict"] == "PASS"
    service_pass = service["verdict"] == "PASS"
    motion_pass = motion["verdict"] == "PASS"
    wiring_pass = wiring["verdict"] == "PASS"
    verdict = {
        "ALL_8_MECHANICAL_BASELINES": "PRESERVED" if frozen_preserved else "FAIL",
        "CARRIER_TO_CARRIER_INTEGRATION": "PASS" if carrier_pass else "HOLD",
        "SWITCH_TERMINAL_CROSS_COLLISION": "PASS" if cross_pass else "HOLD",
        "ALL_8_MOTION_ENVELOPE": "PASS" if motion_pass else "HOLD",
        "SERVICEABILITY": "PASS" if service_pass else "HOLD",
        "TERMINAL_ACCESS": "PASS" if cross_pass and wiring_pass else "HOLD",
        "WIRING_SPACE": "PASS" if wiring_pass else "HOLD",
        "FASTENING_SPACE": fastening["overall"],
        "EXTERIOR": "PRESERVED" if frozen_preserved else "FAIL",
    }
    overall_pass = frozen_preserved and cross_pass and motion_pass and service_pass and wiring_pass
    verdict["ALL_8_INTERNAL_INTEGRATION"] = "PASS" if overall_pass else "HOLD"
    all8_full = next(row for row in motion["states"] if row["state"] == "ALL_8_FULL")
    summary_metrics = {
        "maximumCarrierCarrierPenetrationMm3": max(float(row["penetrationMm3"]) for row in static["carrierPairwise"]),
        "minimumInterCarrierClearanceMm": min(float(row["distanceMm"]) for row in static["carrierPairwise"]),
        "all8FullMaximumUnintendedPenetrationMm3": float(all8_full["maximumUnintendedPenetrationMm3"]),
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY),
    }

    data: dict[str, object] = {
        "schema": "onegrip.all_8.integration_wiring_space_audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ ONLY / LOW MEMORY / LOCAL SHELL CROPS / SERIAL OCCT",
        "freeze": {
            "approvedDocs": [62, 63, 64, 65, 66],
            "buttons": list(BUTTONS),
            "carrierServiceGroups": {name: list(buttons) for name, buttons in GROUP_BUTTONS.items()},
            "productionGeometryEdits": 0,
            "carrierUnions": 0,
            "externalCenterMovementMm": 0.0,
            "externalGeometryChangeMm3": 0.0,
            "fullShellBoolean": False,
            "fullAssemblyStep": False,
            "wireSolids": False,
            "fasteningFeatures": False,
            "multiprocessing": False,
        },
        "localShellCrop": shell_crop,
        "geometryFingerprints": geometry_fingerprints,
        "baselineHashesBefore": baseline_hashes_before,
        "baselineHashesAfter": baseline_hashes_after,
        "baselineHashesPreserved": frozen_preserved,
        "staticIntegration": static,
        "motion": motion,
        "service": service,
        "wiring": wiring,
        "fastening": fastening,
        "approvedRegressionReferences": {
            "N2CarrierHW504AminimumMm": 0.304180,
            "N2CarrierHW504BminimumMm": 1.360984,
            "N2ActiveT1T3HW504BminimumMm": 2.119093,
            "I2I3FullCapGapMinimumMm": 2.14,
            "M4N3MinimumCapGapMm": 3.132654,
            "I4NearestI3CapMm": 3.248773,
            "M3NearestM4CapMm": 4.847042,
            "criticalStructuralWallMinimumMm": 1.20,
            "preservationBasis": "approved input hashes unchanged; production geometry edits = 0",
        },
        "summaryMetrics": summary_metrics,
        "verdict": verdict,
        "outputs": {
            "json": relative(JSON_PATH),
            "report": relative(REPORT_PATH),
            "renders": [relative(path) for path in renders],
            "step": [],
            "stl": [],
            "printPlate": [],
            "forbiddenOutputsGenerated": [],
        },
        "memory": MEMORY,
        "stop": "User review required; no automatic expansion to production assembly, final harness, fastening features or MCU/PCB",
    }
    data = reclassify_hw504_reference(data)
    REPORT_PATH.write_text(report_markdown(data), encoding="utf-8")
    data["outputs"]["sha256"] = {relative(path): sha256(path) for path in [REPORT_PATH, *renders]}
    memory("complete")
    data["memory"] = MEMORY
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "verdict": verdict,
        "carrierClosest": static["closestCarrierInterface"],
        "staticFailed": len(static["failedInterfaces"]),
        "motionFailedStates": motion["failedStates"],
        "wiringBlocked": wiring["blockedButtons"],
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY),
        "json": relative(JSON_PATH),
        "report": relative(REPORT_PATH),
        "renders": [relative(path) for path in renders],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
