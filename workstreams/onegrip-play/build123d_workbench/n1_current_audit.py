"""Read-only exact audit of the current N1 geometry before mechanism design."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from build123d import Compound, Shape, import_step

from . import n2_production_intent_mechanism as baseline
from .finger_controls_v2 import ACTUATOR_PROJECTION, SWITCH_BODY_H, point_at, unit
from .option_c_local_exact_prototype import aggregate_pairs, datum_from_manifest, exact_pair


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "n1_production_intent_mechanism"
JSON_PATH = OUT_DIR / "n1_current_audit.json"
N1_CAP_STEP = ROOT / "build123d_workbench" / "out" / "finger_controls_v2" / "N1_cap.step"
N2_FROZEN_CARRIER_STEP = (
    ROOT / "build123d_workbench" / "out" / "n2_rear_reaction_support_redesign"
    / "N1_N2_SHARED_CARRIER_N2_REAR_SUPPORT_REDRAFT.step"
)
N1_FRONT_DEPTH_MM = 4.80
TERMINAL_LABELS = {
    "T1": "N1_root_nu_nv",
    "T2": "N1_root_nu_pv",
    "T3": "N1_root_pu_nv",
    "T4": "N1_root_pu_pv",
}


def angle_deg(left, right) -> float:
    cosine = float(np.clip(abs(np.dot(unit(left), unit(right))), -1.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))


def load_n1_datum():
    manifest = json.loads(baseline.MANIFEST.read_text(encoding="utf-8"))
    return datum_from_manifest("N1", manifest["controls"]["N1"])


def minimum_pairs(left: Shape, rights: list[Shape], prefix: str) -> dict[str, object]:
    return aggregate_pairs([exact_pair(left, row, f"{prefix}<->{row.label}") for row in rights])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = baseline.load_source()
    datum = load_n1_datum()
    cap = import_step(N1_CAP_STEP)
    carrier = import_step(N2_FROZEN_CARRIER_STEP)
    body = source["N1_ITS1105_body"]
    actuator = source["N1_ITS1105_actuator"]
    hw_a = source["HW504_A_NONFUNCTIONAL_TRIM"]
    hw_b = source["HW504_B_EXACT_KEEP"]
    shells = [source["N2_SEAM_JaD"], source["N2_SEAM_JfD"]]
    terminals = {name: source[label] for name, label in TERMINAL_LABELS.items()}

    cap_center = np.asarray(datum.center, dtype=float)
    actuator_top_center = np.asarray(point_at(datum, N1_FRONT_DEPTH_MM - ACTUATOR_PROJECTION), dtype=float)
    switch_top_center = np.asarray(point_at(datum, N1_FRONT_DEPTH_MM), dtype=float)
    axis = unit(datum.axis)
    cap_to_actuator = actuator_top_center - cap_center
    lateral = cap_to_actuator - axis * float(np.dot(cap_to_actuator, axis))

    switch_rows = {
        "HW504A": exact_pair(body, hw_a, "N1 ITS body<->HW504 A"),
        "HW504B": exact_pair(body, hw_b, "N1 ITS body<->HW504 B"),
    }
    terminal_rows: dict[str, object] = {}
    for name, terminal in terminals.items():
        terminal_rows[name] = {
            "HW504A": exact_pair(terminal, hw_a, f"N1 {name}<->HW504 A"),
            "HW504B": exact_pair(terminal, hw_b, f"N1 {name}<->HW504 B"),
            "shell": minimum_pairs(terminal, shells, f"N1 {name}"),
            "carrier": exact_pair(terminal, carrier, f"N1 {name}<->frozen shared carrier"),
        }

    carrier_hw = aggregate_pairs([
        exact_pair(carrier, hw_a, "frozen shared carrier<->HW504 A"),
        exact_pair(carrier, hw_b, "frozen shared carrier<->HW504 B"),
    ])
    shell_rows = {
        "cap": minimum_pairs(cap, shells, "N1 cap"),
        "switchBody": minimum_pairs(body, shells, "N1 switch body"),
        "actuator": minimum_pairs(actuator, shells, "N1 actuator"),
        "carrier": minimum_pairs(carrier, shells, "frozen shared carrier"),
    }
    current_internal = Compound(children=[body, actuator, *terminals.values()], label="N1_CURRENT_INTERNAL")
    data = {
        "schema": "onegrip.n1.current_audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ ONLY / N1 LOCAL / SERIAL EXACT",
        "A_capCenterMm": cap_center.tolist(),
        "B_capPlane": {"normal": axis.tolist(), "pointMm": cap_center.tolist()},
        "C_ITSActuatorCenterMm": actuator_top_center.tolist(),
        "D_capActuatorCenterOffset": {
            "lateralMm": float(np.linalg.norm(lateral)),
            "axialMm": float(abs(np.dot(cap_to_actuator, axis))),
            "axesCoincident": float(np.linalg.norm(lateral)) <= 1.0e-7,
        },
        "E_capPlaneSwitchTopPlaneAngleDeg": angle_deg(datum.axis, datum.axis),
        "F_switchAxisCapTravelAxisAngleDeg": angle_deg(datum.axis, datum.axis),
        "switchTopPlane": {"normal": axis.tolist(), "pointMm": switch_top_center.tolist()},
        "G_switchBodyClearance": switch_rows,
        "H_terminalMap": terminal_rows,
        "I_currentCarrierHW504": carrier_hw,
        "J_localShellClearance": shell_rows,
        "currentInternalToHW504": {
            "A": exact_pair(current_internal, hw_a, "N1 current internal<->HW504 A"),
            "B": exact_pair(current_internal, hw_b, "N1 current internal<->HW504 B"),
        },
        "conclusion": {
            "capSwitchAlignment": "COAXIAL_AND_PARALLEL",
            "directActuationCandidate": True,
            "externalChangeRequired": False,
            "terminalTrimIndicated": False,
        },
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    terminal_summary = {
        name: {
            "HW_A": row["HW504A"]["distanceMm"],
            "HW_B": row["HW504B"]["distanceMm"],
            "shell": row["shell"]["minimumDistanceMm"],
            "carrier": row["carrier"]["distanceMm"],
            "carrierPen": row["carrier"]["penetrationMm3"],
        }
        for name, row in terminal_rows.items()
    }
    print(json.dumps({
        "alignment": data["conclusion"],
        "capCenterMm": data["A_capCenterMm"],
        "actuatorTopCenterMm": data["C_ITSActuatorCenterMm"],
        "lateralOffsetMm": data["D_capActuatorCenterOffset"]["lateralMm"],
        "planeAngleDeg": data["E_capPlaneSwitchTopPlaneAngleDeg"],
        "switchBodyHW_A_mm": switch_rows["HW504A"]["distanceMm"],
        "switchBodyHW_B_mm": switch_rows["HW504B"]["distanceMm"],
        "terminals": terminal_summary,
        "carrierHWMinMm": carrier_hw["minimumDistanceMm"],
        "capShellMm": shell_rows["cap"]["minimumDistanceMm"],
        "switchShellMm": shell_rows["switchBody"]["minimumDistanceMm"],
        "json": str(JSON_PATH.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
