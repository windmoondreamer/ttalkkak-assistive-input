"""Read-only local exact audit for the frozen-exterior I4 and M3 controls."""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import json
from pathlib import Path

import numpy as np
from build123d import Compound, Shape, import_step

from .finger_controls_v2 import (
    ACTUATOR_PROJECTION,
    ACTUATOR_TRAVEL_MAX,
    FROZEN_FRONT_DEPTHS,
    SWITCH_BODY_H,
    oriented_box,
    point_at,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    unit,
)
from .n2_production_intent_mechanism import global_box
from .option_c_final_local_fit import bounds
from .option_c_local_exact_prototype import datum_from_manifest, exact_pair


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
OUT_DIR = ROOT / "build123d_workbench" / "out" / "i4_m3_production_intent_mechanisms"
JSON_PATH = OUT_DIR / "i4_m3_current_audit.json"
MANIFEST = SOURCE_DIR / "finger_controls_v2_source_manifest.json"
PLANE_JSON = ROOT / "build123d_workbench" / "out" / "button_cap_plane_mapping" / "button_cap_plane_mapping.json"
BUTTONS = ("I4", "M3")
TERMINAL_NAMES = ("T1", "T2", "T3", "T4")
CARRIER_STEPS = {name: SOURCE_DIR / f"{name}_carrier.step" for name in BUTTONS}
CAP_STEPS = {name: SOURCE_DIR / f"{name}_cap.step" for name in BUTTONS}
SHELL_STEPS = {
    "I4": SOURCE_DIR / "JAD_FINGER_V2.step",
    "M3": SOURCE_DIR / "JFD_FINGER_V2.step",
}
FROZEN_CARRIERS = {
    "N1_N2": ROOT / "build123d_workbench" / "out" / "n1_production_intent_mechanism" / "N1_N2_SHARED_CARRIER_N1_LOCAL.step",
    "I2_I3": ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "I2_I3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step",
    "M4_N3": ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "M4_N3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step",
}
FROZEN_CAPS = {
    "N1": ROOT / "build123d_workbench" / "out" / "n1_production_intent_mechanism" / "N1_PRODUCTION_INTENT_CAP_LOCAL.step",
    "N2": ROOT / "build123d_workbench" / "out" / "n2_production_intent_mechanism" / "N2_PRODUCTION_INTENT_CAP.step",
    "I2": ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "I2_PRODUCTION_INTENT_CAP_LOCAL.step",
    "I3": ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "I3_PRODUCTION_INTENT_CAP_LOCAL.step",
    "M4": ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "M4_PRODUCTION_INTENT_CAP_LOCAL.step",
    "N3": ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "N3_PRODUCTION_INTENT_CAP_LOCAL.step",
}


def load_all_datums() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {
        name: datum_from_manifest(name, row)
        for name, row in manifest["controls"].items()
    }


def load_datums() -> dict[str, object]:
    rows = load_all_datums()
    return {name: rows[name] for name in BUTTONS}


def angle_deg(left, right) -> float:
    cosine = float(np.clip(abs(np.dot(unit(left), unit(right))), -1.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))


def local_shell(name: str, carrier: Shape, cap: Shape) -> tuple[Shape, dict[str, list[float]]]:
    focus = Compound(children=[carrier, cap], label=f"{name}_AUDIT_FOCUS")
    lower, upper = bounds(focus)
    lower = lower - 8.0
    upper = upper + 10.0
    crop = global_box(lower, upper, f"{name}_LOCAL_SHELL_CROP_TOOL")
    shell_full = import_step(SHELL_STEPS[name])
    shell = shell_full & crop
    if shell is None or len(shell.solids()) == 0:
        raise RuntimeError(f"{name} local shell crop is empty")
    shell = shell.clean()
    shell.label = f"{name}_LOCAL_SHELL_CROP"
    del shell_full, focus, crop
    gc.collect()
    return shell, {"min": lower.tolist(), "max": upper.tolist()}


def terminal_map(datum, front: float) -> dict[str, Shape]:
    return {
        name: shape
        for name, shape in zip(TERMINAL_NAMES, terminal_root_cutters(datum, front))
    }


def envelope_map(name: str, datum, front: float, shell: Shape, carrier: Shape) -> dict[str, object]:
    guide = oriented_box(
        datum, 9.30, 9.30, front - 1.50, front,
        cap_frame=True, label=f"{name}_AUDIT_GUIDE_ENVELOPE",
    )
    rear = oriented_box(
        datum, 6.40, 6.40, front + SWITCH_BODY_H, front + SWITCH_BODY_H + 0.20,
        label=f"{name}_AUDIT_REACTION_ENVELOPE",
    )
    hard_stop = oriented_box(
        datum, 9.30, 9.30,
        front - 1.00 + ACTUATOR_TRAVEL_MAX,
        front,
        cap_frame=True, label=f"{name}_AUDIT_HARD_STOP_ENVELOPE",
    )
    return {
        "guide": {
            "sizeMm": [9.30, 9.30, 1.50],
            "shell": exact_pair(guide, shell, f"{name} guide envelope<->shell"),
            "currentCarrier": exact_pair(guide, carrier, f"{name} guide envelope<->current carrier"),
        },
        "rearReaction": {
            "sizeMm": [6.40, 6.40, 0.20],
            "shell": exact_pair(rear, shell, f"{name} rear envelope<->shell"),
            "currentCarrier": exact_pair(rear, carrier, f"{name} rear envelope<->current carrier"),
        },
        "hardStop": {
            "sizeMm": [9.30, 9.30, front - (front - 1.00 + ACTUATOR_TRAVEL_MAX)],
            "shell": exact_pair(hard_stop, shell, f"{name} hard-stop envelope<->shell"),
            "currentCarrier": exact_pair(hard_stop, carrier, f"{name} hard-stop envelope<->current carrier"),
        },
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_datums = load_all_datums()
    plane_rows = {
        row["name"]: row
        for row in json.loads(PLANE_JSON.read_text(encoding="utf-8"))["buttons"]
        if row["name"] in set(BUTTONS)
    }
    frozen_carriers = {name: import_step(path) for name, path in FROZEN_CARRIERS.items()}
    frozen_caps = {name: import_step(path) for name, path in FROZEN_CAPS.items()}
    frozen_bodies = {
        name: switch_body(all_datums[name], FROZEN_FRONT_DEPTHS[name])
        for name in FROZEN_CAPS
    }

    controls: dict[str, object] = {}
    for name in BUTTONS:
        datum = all_datums[name]
        front = float(FROZEN_FRONT_DEPTHS[name])
        carrier = import_step(CARRIER_STEPS[name])
        cap = import_step(CAP_STEPS[name])
        shell, shell_bbox = local_shell(name, carrier, cap)
        body = switch_body(datum, front)
        actuator = switch_actuator(datum, front)
        actuator_center = np.asarray(point_at(datum, front - ACTUATOR_PROJECTION), dtype=float)
        cap_center = np.asarray(datum.center, dtype=float)
        offset = actuator_center - cap_center
        lateral = offset - unit(datum.axis) * float(np.dot(offset, unit(datum.axis)))
        terminals = terminal_map(datum, front)

        neighbor_carriers = {
            frozen_name: exact_pair(carrier, frozen, f"{name} carrier<->{frozen_name} frozen carrier")
            for frozen_name, frozen in frozen_carriers.items()
        }
        neighbor_caps = {
            frozen_name: exact_pair(cap, frozen, f"{name} cap<->{frozen_name} frozen cap")
            for frozen_name, frozen in frozen_caps.items()
        }
        neighbor_bodies = {
            frozen_name: exact_pair(body, frozen, f"{name} body<->{frozen_name} frozen body")
            for frozen_name, frozen in frozen_bodies.items()
        }
        terminal_rows = {}
        for terminal_name, terminal in terminals.items():
            terminal_rows[terminal_name] = {
                "carrier": exact_pair(terminal, carrier, f"{name} {terminal_name}<->current carrier"),
                "shell": exact_pair(terminal, shell, f"{name} {terminal_name}<->local shell"),
                "frozenCarriers": {
                    frozen_name: exact_pair(terminal, frozen, f"{name} {terminal_name}<->{frozen_name} carrier")
                    for frozen_name, frozen in frozen_carriers.items()
                },
                "frozenBodies": {
                    frozen_name: exact_pair(terminal, frozen, f"{name} {terminal_name}<->{frozen_name} body")
                    for frozen_name, frozen in frozen_bodies.items()
                },
            }

        controls[name] = {
            "owner": datum.owner,
            "centerMm": cap_center.tolist(),
            "axis": list(datum.axis),
            "shellNormal": list(datum.shell_normal),
            "frontDepthMm": front,
            "shellCropBboxMm": shell_bbox,
            "capPlaneNormal": list(plane_rows[name]["capTopFaceNormal"]),
            "switchPlaneNormal": list(plane_rows[name]["switchTopFaceNormal"]),
            "actuatorCenterMm": actuator_center.tolist(),
            "capActuatorLateralOffsetMm": float(np.linalg.norm(lateral)),
            "travelActuatorAxisAngleDeg": angle_deg(datum.axis, plane_rows[name]["switchTopFaceNormal"]),
            "capSwitchPlaneAngleDeg": angle_deg(
                plane_rows[name]["capTopFaceNormal"], plane_rows[name]["switchTopFaceNormal"]
            ),
            "capShellPlaneAngleDeg": angle_deg(datum.axis, datum.shell_normal),
            "capShell": exact_pair(cap, shell, f"{name} cap<->local shell"),
            "bodyShell": exact_pair(body, shell, f"{name} body<->local shell"),
            "bodyCarrier": exact_pair(body, carrier, f"{name} body<->current carrier"),
            "actuatorCarrier": exact_pair(actuator, carrier, f"{name} actuator<->current carrier"),
            "rearReactionGapMm": float(body.distance_to_with_closest_points(carrier)[0]),
            "neighborCarriers": neighbor_carriers,
            "neighborCaps": neighbor_caps,
            "neighborBodies": neighbor_bodies,
            "terminals": terminal_rows,
            "availableEnvelopes": envelope_map(name, datum, front, shell, carrier),
            "currentCarrierShell": exact_pair(carrier, shell, f"{name} current carrier<->local shell"),
            "currentCarrierSolidCount": len(carrier.solids()),
            "currentCarrierVolumeMm3": float(carrier.volume),
        }
        del carrier, cap, shell, body, actuator
        gc.collect()

    data = {
        "schema": "onegrip.i4_m3.current_audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ ONLY / TWO INDEPENDENT LOCAL SHELL CROPS / SERIAL EXACT",
        "controls": controls,
        "conclusion": {
            "exteriorFeasibilityReopened": False,
            "capOrientationsFrozen": True,
            "capSwitchAngleDeg": 0.0,
            "capShellAngleDeg": 0.0,
            "directActuationCandidate": True,
            "allTerminalsInitiallyRetained": True,
            "sharedCarrierBetweenI4M3": False,
        },
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "controls": {
            name: {
                "owner": row["owner"],
                "frontDepthMm": row["frontDepthMm"],
                "capActuatorLateralOffsetMm": row["capActuatorLateralOffsetMm"],
                "capSwitchPlaneAngleDeg": row["capSwitchPlaneAngleDeg"],
                "capShellPlaneAngleDeg": row["capShellPlaneAngleDeg"],
                "bodyShellDistanceMm": row["bodyShell"]["distanceMm"],
                "rearReactionGapMm": row["rearReactionGapMm"],
                "guideEnvelopeShellPenetrationMm3": row["availableEnvelopes"]["guide"]["shell"]["penetrationMm3"],
                "rearEnvelopeShellPenetrationMm3": row["availableEnvelopes"]["rearReaction"]["shell"]["penetrationMm3"],
                "hardStopEnvelopeShellPenetrationMm3": row["availableEnvelopes"]["hardStop"]["shell"]["penetrationMm3"],
                "nearestFrozenCapMm": min(float(pair["distanceMm"]) for pair in row["neighborCaps"].values()),
                "nearestFrozenCarrierMm": min(float(pair["distanceMm"]) for pair in row["neighborCarriers"].values()),
                "terminalShellMinMm": min(float(t["shell"]["distanceMm"]) for t in row["terminals"].values()),
            }
            for name, row in controls.items()
        },
        "json": str(JSON_PATH.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
