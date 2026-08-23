"""Read-only exact local audit for the frozen-exterior M4/N3 pair."""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import json
from pathlib import Path

import numpy as np
from build123d import Compound, Shape, import_step

from .finger_controls_v2 import (
    ACTUATOR_PROJECTION,
    FROZEN_FRONT_DEPTHS,
    oriented_box,
    point_at,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    unit,
)
from .option_c_final_local_fit import bounds
from .option_c_local_exact_prototype import datum_from_manifest, exact_pair
from .n2_production_intent_mechanism import global_box


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
OUT_DIR = ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism"
JSON_PATH = OUT_DIR / "m4_n3_current_audit.json"
MANIFEST = SOURCE_DIR / "finger_controls_v2_source_manifest.json"
PLANE_JSON = ROOT / "build123d_workbench" / "out" / "button_cap_plane_mapping" / "button_cap_plane_mapping.json"
CARRIER_STEP = SOURCE_DIR / "M4_N3_shared_carrier.step"
SHELL_STEP = SOURCE_DIR / "JAD_FINGER_V2.step"
CAP_STEPS = {name: SOURCE_DIR / f"{name}_cap.step" for name in ("M4", "N3")}
NEIGHBOR_CARRIER_STEPS = {
    "I4": SOURCE_DIR / "I4_carrier.step",
    "M3": SOURCE_DIR / "M3_carrier.step",
}
TERMINAL_NAMES = ("T1", "T2", "T3", "T4")


def load_datums() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {name: datum_from_manifest(name, manifest["controls"][name]) for name in ("M4", "N3")}


def angle_deg(left, right) -> float:
    cosine = float(np.clip(abs(np.dot(unit(left), unit(right))), -1.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))


def local_shell(carrier: Shape, caps: dict[str, Shape]) -> tuple[Shape, dict[str, list[float]]]:
    focus = Compound(children=[carrier, *caps.values()], label="M4_N3_AUDIT_FOCUS")
    lower, upper = bounds(focus)
    lower = lower - 8.0
    upper = upper + 10.0
    crop = global_box(lower, upper, "M4_N3_LOCAL_SHELL_CROP_TOOL")
    shell_full = import_step(SHELL_STEP)
    shell = shell_full & crop
    if shell is None or len(shell.solids()) == 0:
        raise RuntimeError("M4/N3 local shell crop is empty")
    shell = shell.clean()
    shell.label = "M4_N3_LOCAL_JAD_SHELL_CROP"
    del shell_full, focus, crop
    gc.collect()
    return shell, {"min": lower.tolist(), "max": upper.tolist()}


def terminal_map(datum, front: float) -> dict[str, Shape]:
    roots = terminal_root_cutters(datum, front)
    return {name: root for name, root in zip(TERMINAL_NAMES, roots)}


def available_envelopes(name: str, datum, front: float, shell: Shape, carrier: Shape) -> dict[str, object]:
    # Read-only probes only: they do not alter or export production geometry.
    guide_probe = oriented_box(
        datum, 9.30, 9.30, front - 1.50, front,
        cap_frame=True, label=f"{name}_AUDIT_GUIDE_ENVELOPE_9P3",
    )
    rear_probe = oriented_box(
        datum, 6.40, 6.40, front + 3.56, front + 3.76,
        label=f"{name}_AUDIT_REAR_FRAME_ENVELOPE",
    )
    return {
        "guideEnvelopeMm": [9.30, 9.30, 1.50],
        "guideEnvelopeShell": exact_pair(guide_probe, shell, f"{name} guide envelope<->local shell"),
        "guideEnvelopeCurrentCarrier": exact_pair(guide_probe, carrier, f"{name} guide envelope<->current carrier"),
        "rearEnvelopeMm": [6.40, 6.40, 0.20],
        "rearEnvelopeShell": exact_pair(rear_probe, shell, f"{name} rear envelope<->local shell"),
        "rearEnvelopeCurrentCarrier": exact_pair(rear_probe, carrier, f"{name} rear envelope<->current carrier"),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    datums = load_datums()
    caps = {name: import_step(path) for name, path in CAP_STEPS.items()}
    carrier = import_step(CARRIER_STEP)
    neighbors = {name: import_step(path) for name, path in NEIGHBOR_CARRIER_STEPS.items()}
    shell, shell_crop = local_shell(carrier, caps)
    plane_rows = {
        row["name"]: row
        for row in json.loads(PLANE_JSON.read_text(encoding="utf-8"))["buttons"]
        if row["name"] in {"M4", "N3"}
    }

    controls: dict[str, object] = {}
    for name in ("M4", "N3"):
        datum = datums[name]
        front = float(FROZEN_FRONT_DEPTHS[name])
        body = switch_body(datum, front)
        actuator = switch_actuator(datum, front)
        terminals = terminal_map(datum, front)
        actuator_center = np.asarray(point_at(datum, front - ACTUATOR_PROJECTION), dtype=float)
        cap_center = np.asarray(datum.center, dtype=float)
        offset = actuator_center - cap_center
        lateral = offset - unit(datum.axis) * float(np.dot(offset, unit(datum.axis)))
        other_name = "N3" if name == "M4" else "M4"
        other_datum = datums[other_name]
        other_front = float(FROZEN_FRONT_DEPTHS[other_name])
        other_body = switch_body(other_datum, other_front)

        terminal_rows = {}
        for terminal_name, terminal in terminals.items():
            terminal_rows[terminal_name] = {
                "carrier": exact_pair(terminal, carrier, f"{name} {terminal_name}<->current shared carrier"),
                "localShell": exact_pair(terminal, shell, f"{name} {terminal_name}<->local shell"),
                "otherSwitchBody": exact_pair(terminal, other_body, f"{name} {terminal_name}<->{other_name} body"),
                "neighborCarriers": {
                    neighbor_name: exact_pair(terminal, neighbor, f"{name} {terminal_name}<->{neighbor_name} carrier")
                    for neighbor_name, neighbor in neighbors.items()
                },
            }

        controls[name] = {
            "centerMm": cap_center.tolist(),
            "axis": list(datum.axis),
            "shellNormal": list(datum.shell_normal),
            "frontDepthMm": front,
            "capPlaneNormal": list(plane_rows[name]["capTopFaceNormal"]),
            "switchPlaneNormal": list(plane_rows[name]["switchTopFaceNormal"]),
            "actuatorTopCenterMm": actuator_center.tolist(),
            "capActuatorLateralOffsetMm": float(np.linalg.norm(lateral)),
            "actuatorAxisAngleDeg": angle_deg(datum.axis, plane_rows[name]["switchTopFaceNormal"]),
            "capSwitchPlaneAngleDeg": angle_deg(
                plane_rows[name]["capTopFaceNormal"], plane_rows[name]["switchTopFaceNormal"]
            ),
            "capShellLocalPlaneAngleDeg": angle_deg(datum.axis, datum.shell_normal),
            "mappedCapSwitchPlaneAngleDeg": float(plane_rows[name]["capToSwitchPlaneAngleDeg"]),
            "mappedCapShellAngleDeg": float(plane_rows[name]["capToShellTangentAngleDeg"]),
            "capShell": exact_pair(caps[name], shell, f"{name} cap<->local shell"),
            "bodyShell": exact_pair(body, shell, f"{name} body<->local shell"),
            "bodyCarrier": exact_pair(body, carrier, f"{name} body<->current shared carrier"),
            "actuatorCarrier": exact_pair(actuator, carrier, f"{name} actuator<->current shared carrier"),
            "bodyNeighborCarriers": {
                neighbor_name: exact_pair(body, neighbor, f"{name} body<->{neighbor_name} carrier")
                for neighbor_name, neighbor in neighbors.items()
            },
            "terminals": terminal_rows,
            "rearReactionGapMm": float(body.distance_to_with_closest_points(carrier)[0]),
            "availableEnvelopes": available_envelopes(name, datum, front, shell, carrier),
        }
        del body, actuator, other_body
        gc.collect()

    m4_body = switch_body(datums["M4"], FROZEN_FRONT_DEPTHS["M4"])
    n3_body = switch_body(datums["N3"], FROZEN_FRONT_DEPTHS["N3"])
    m4_actuator = switch_actuator(datums["M4"], FROZEN_FRONT_DEPTHS["M4"])
    n3_actuator = switch_actuator(datums["N3"], FROZEN_FRONT_DEPTHS["N3"])
    pair_rows = {
        "caps": exact_pair(caps["M4"], caps["N3"], "M4 cap<->N3 cap"),
        "bodies": exact_pair(m4_body, n3_body, "M4 body<->N3 body"),
        "actuators": exact_pair(m4_actuator, n3_actuator, "M4 actuator<->N3 actuator"),
    }
    neighbor_rows = {
        neighbor_name: exact_pair(carrier, neighbor, f"M4/N3 carrier<->{neighbor_name} carrier")
        for neighbor_name, neighbor in neighbors.items()
    }
    data = {
        "schema": "onegrip.m4_n3.current_audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ ONLY / LOCAL SHELL CROP / SERIAL EXACT",
        "shellCropBboxMm": shell_crop,
        "controls": controls,
        "pairSeparation": pair_rows,
        "sharedCarrierLocalShell": exact_pair(carrier, shell, "current M4/N3 shared carrier<->local shell"),
        "neighborCarrierSeparation": neighbor_rows,
        "sharedCarrierSolidCount": len(carrier.solids()),
        "sharedCarrierVolumeMm3": float(carrier.volume),
        "conclusion": {
            "exteriorFeasibilityReopened": False,
            "capOrientationsFrozen": True,
            "intentionalShellAngleDeg": 4.0,
            "directActuationCandidate": True,
            "allTerminalsInitiallyRetained": True,
        },
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "controls": {
            name: {
                "frontDepthMm": row["frontDepthMm"],
                "capActuatorLateralOffsetMm": row["capActuatorLateralOffsetMm"],
                "capSwitchPlaneAngleDeg": row["capSwitchPlaneAngleDeg"],
                "capShellAngleDeg": row["capShellLocalPlaneAngleDeg"],
                "rearReactionGapMm": row["rearReactionGapMm"],
                "rawGuideShellPenetrationMm3": row["availableEnvelopes"]["guideEnvelopeShell"]["penetrationMm3"],
                "terminalCarrierMinMm": min(float(t["carrier"]["distanceMm"]) for t in row["terminals"].values()),
                "terminalShellMinMm": min(float(t["localShell"]["distanceMm"]) for t in row["terminals"].values()),
            }
            for name, row in controls.items()
        },
        "pairSeparation": {key: value["distanceMm"] for key, value in pair_rows.items()},
        "carrierShell": data["sharedCarrierLocalShell"],
        "neighborCarrierDistancesMm": {key: value["distanceMm"] for key, value in neighbor_rows.items()},
        "json": str(JSON_PATH.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
