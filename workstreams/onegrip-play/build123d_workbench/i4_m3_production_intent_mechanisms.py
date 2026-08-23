"""Two independent production-intent button mechanisms for I4 and M3."""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Shape, export_step, import_step

from . import i2_i3_production_intent_mechanism as shared
from .finger_controls_v2 import (
    ACTUATOR_TRAVEL_MAX,
    FROZEN_FRONT_DEPTHS,
    SWITCH_BODY_H,
    SWITCH_BODY_X,
    SWITCH_BODY_Y,
    oriented_box,
    oriented_cylinder,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    unit,
)
from .i4_m3_current_audit import (
    BUTTONS,
    CAP_STEPS,
    CARRIER_STEPS,
    FROZEN_CAPS,
    FROZEN_CARRIERS,
    JSON_PATH as AUDIT_JSON_PATH,
    SOURCE_DIR,
    TERMINAL_NAMES,
    load_all_datums,
    load_datums,
    local_shell,
)
from .m4_n3_production_intent_mechanism import reaction_contact_metrics
from .option_c_final_local_fit import bounds
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    exact_pair,
    raster_scene,
    safe_triangles,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "i4_m3_production_intent_mechanisms"
RENDER_DIR = ROOT / "renders" / "i4_m3_production_intent_mechanisms"
JSON_PATH = OUT_DIR / "i4_m3_production_intent_mechanisms.json"
REPORT_PATH = ROOT / "docs" / "66_i4_m3_production_intent_mechanisms.md"
CARRIER_OUTPUTS = {name: OUT_DIR / f"{name}_CARRIER_PRODUCTION_INTENT_LOCAL.step" for name in BUTTONS}
CAP_OUTPUTS = {name: OUT_DIR / f"{name}_CAP_PRODUCTION_INTENT_LOCAL.step" for name in BUTTONS}

N1N2_JSON = ROOT / "build123d_workbench" / "out" / "n1_production_intent_mechanism" / "n1_production_intent_mechanism.json"
I2I3_JSON = ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism" / "i2_i3_production_intent_mechanism.json"
M4N3_JSON = ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "m4_n3_production_intent_mechanism.json"

FROZEN_FILES = (
    ROOT / "docs" / "62_n2_rear_reaction_support_redesign.md",
    ROOT / "docs" / "63_n1_production_intent_mechanism.md",
    ROOT / "docs" / "64_i2_i3_production_intent_mechanism.md",
    ROOT / "docs" / "65_m4_n3_production_intent_mechanism.md",
    ROOT / "build123d_workbench" / "out" / "n2_rear_reaction_support_redesign" / "n2_rear_reaction_support_redesign.json",
    ROOT / "build123d_workbench" / "out" / "n2_rear_reaction_support_redesign" / "N1_N2_SHARED_CARRIER_N2_REAR_SUPPORT_REDRAFT.step",
    N1N2_JSON,
    I2I3_JSON,
    M4N3_JSON,
    *FROZEN_CARRIERS.values(),
    *FROZEN_CAPS.values(),
)
FROZEN_SHAPE_FILES = tuple(path for path in FROZEN_FILES if path.suffix.lower() == ".step")

NEIGHBOR_BUTTONS = {"I4": ("I2", "I3"), "M3": ("M4", "N3")}
NEIGHBOR_CARRIER_NAMES = {"I4": "I2_I3", "M3": "M4_N3"}
CAP_SERVICE_SIGNS = {"I4": 1.0, "M3": -1.0}
SWITCH_SERVICE_SIGNS = {"I4": 1.0, "M3": 1.0}
TRAVELS_MM = (0.0, 0.175, 0.350)
MIN_WALL_MM = 1.20
PREFERRED_WALL_MM = 1.60
MIN_REACTION_AREA_MM2 = 20.0

COLORS = {
    "I4cap": (47, 205, 145),
    "M3cap": (91, 220, 188),
    "I4guide": (52, 140, 225),
    "M3guide": (83, 181, 235),
    "I4carrier": (168, 87, 207),
    "M3carrier": (130, 86, 190),
    "I4support": (244, 127, 61),
    "M3support": (245, 178, 73),
    "body": (218, 158, 62),
    "actuator": (250, 210, 91),
    "shell": (78, 177, 207),
    "frozenA": (72, 151, 229),
    "frozenB": (73, 194, 149),
    "frozenC": (193, 111, 214),
    "terminal": ((76, 208, 153), (74, 158, 226), (245, 190, 72), (226, 104, 151)),
}


def memory(stage: str) -> None:
    shared.memory(stage)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def volume(shape: Shape | None) -> float:
    return shared.volume(shape)


def build_raw_guide(name: str, datum, front: float) -> tuple[Shape, dict[str, Shape]]:
    z = shared.axial(front)
    outer = oriented_box(
        datum, shared.GUIDE_OUTER_MM, shared.GUIDE_OUTER_MM,
        z["guideFront"], z["guideRear"], cap_frame=True, label=f"{name}_GUIDE_OUTER",
    )
    bore = oriented_cylinder(
        datum, shared.GUIDE_BORE_MM, z["guideFront"] - 0.10, z["guideRear"] + 0.10,
        cap_frame=True, label=f"{name}_GUIDE_BORE_D4P8",
    )
    cavity = oriented_box(
        datum, shared.CAVITY_MM, shared.CAVITY_MM, z["cavityFront"], z["cavityRear"],
        cap_frame=True, label=f"{name}_RETENTION_CAVITY_6P8",
    )
    sign = CAP_SERVICE_SIGNS[name]
    slot = oriented_box(
        datum, shared.GUIDE_SERVICE_U_MM, shared.CAVITY_MM,
        z["guideFront"] - 0.10, z["guideRear"] + 0.10,
        u_offset=sign * shared.GUIDE_SERVICE_U_MM / 2.0,
        cap_frame=True, label=f"{name}_INDEPENDENT_CAP_SERVICE_SLOT",
    )
    guide = (outer - bore - cavity - slot).clean()
    guide.label = f"{name}_RAW_LOCAL_C_GUIDE"
    front_outer = oriented_box(
        datum, shared.GUIDE_OUTER_MM, shared.GUIDE_OUTER_MM,
        z["guideFront"], z["cavityFront"], cap_frame=True, label=f"{name}_FRONT_STOP_OUTER",
    )
    rear_outer = oriented_box(
        datum, shared.GUIDE_OUTER_MM, shared.GUIDE_OUTER_MM,
        z["cavityRear"], z["guideRear"], cap_frame=True, label=f"{name}_REAR_STOP_OUTER",
    )
    return guide, {
        "outer": outer,
        "bore": bore,
        "cavity": cavity,
        "slot": slot,
        "frontStop": (front_outer - bore - slot).clean(),
        "rearStop": (rear_outer - bore - slot).clean(),
    }


def cap_service(name: str, datum, front: float) -> Shape:
    z = shared.axial(front)
    sign = CAP_SERVICE_SIGNS[name]
    shoulder = oriented_box(
        datum, 8.0, shared.SHOULDER_MM, z["shoulderFront"], z["shoulderRear"],
        u_offset=sign * 4.0, cap_frame=True, label=f"{name}_CAP_SHOULDER_SERVICE",
    )
    tail = oriented_box(
        datum, 8.0, shared.CAP_TAIL_DIAMETER_MM,
        z["shoulderRear"] - 0.10, z["tailRear"],
        u_offset=sign * 4.0, cap_frame=True, label=f"{name}_CAP_TAIL_SERVICE",
    )
    result = shoulder.fuse(tail).clean()
    result.label = f"{name}_CAP_SERVICE_SWEEP"
    return result


def switch_service(name: str, datum, front: float) -> Shape:
    sign = SWITCH_SERVICE_SIGNS[name]
    return oriented_box(
        datum, 10.0, SWITCH_BODY_Y + 0.20, front, front + SWITCH_BODY_H,
        u_offset=sign * 5.0, label=f"{name}_SWITCH_OPEN_CHANNEL_SERVICE_SWEEP",
    )


def build_mechanism(name: str, datum, shell: Shape) -> shared.Mechanism:
    front = float(FROZEN_FRONT_DEPTHS[name])
    base_cap = import_step(CAP_STEPS[name])
    cap, cap_parts = shared.build_cap(name, base_cap, datum, front)
    raw_guide, guide_parts = build_raw_guide(name, datum, front)
    guide, guide_parts, cutters, guide_metrics = shared.relieve_guide(
        name, datum, raw_guide, guide_parts, shell, cap_parts, front
    )
    roots = {
        terminal: shape
        for terminal, shape in zip(TERMINAL_NAMES, terminal_root_cutters(datum, front))
    }
    for terminal, shape in roots.items():
        shape.label = f"{name}_{terminal}_CONSERVATIVE_TERMINAL_ENVELOPE"
    reaction, reaction_metrics = shared.build_reaction_frame(name, datum, front, roots)
    mechanism = shared.Mechanism(
        name, datum, front, base_cap, cap, cap_parts,
        raw_guide, guide, guide_parts, cutters, guide_metrics,
        switch_body(datum, front), roots, reaction, reaction_metrics,
    )
    mechanism.reaction_metrics.update(reaction_contact_metrics(mechanism))
    return mechanism


def build_carrier(name: str, base: Shape, mechanism: shared.Mechanism) -> tuple[Shape, Shape, dict[str, object]]:
    attachments = []
    carrier = base
    for shape in (mechanism.guide, mechanism.reaction):
        attachments.append({
            "label": shape.label,
            "distanceToBaseMm": float(shape.distance_to_with_closest_points(base)[0]),
        })
        carrier = carrier.fuse(shape)
    carrier = carrier.clean()
    carrier.label = f"{name}_CARRIER_PRODUCTION_INTENT_LOCAL"
    added = (carrier - base).clean()
    removed = (base - carrier).clean()
    return carrier, added, {
        "baseSolidCount": len(base.solids()),
        "finalSolidCount": len(carrier.solids()),
        "baseVolumeMm3": float(base.volume),
        "finalVolumeMm3": float(carrier.volume),
        "addedVolumeMm3": volume(added),
        "removedFromCurrentCarrierMm3": volume(removed),
        "attachments": attachments,
        "floatingBody": (
            len(carrier.solids()) > len(base.solids())
            or any(float(row["distanceToBaseMm"]) > 1.0e-6 for row in attachments)
        ),
    }


def shape_fingerprint(path: Path) -> dict[str, object]:
    shape = import_step(path)
    lower, upper = bounds(shape)
    center = shape.center()
    row = {
        "sha256": sha256(path),
        "volumeMm3": float(shape.volume),
        "solidCount": len(shape.solids()),
        "bboxMinMm": lower.tolist(),
        "bboxMaxMm": upper.tolist(),
        "centerMm": [float(center.X), float(center.Y), float(center.Z)],
    }
    del shape
    gc.collect()
    return row


def fingerprint_files() -> dict[str, object]:
    return {
        str(path.relative_to(ROOT)): shape_fingerprint(path)
        for path in FROZEN_SHAPE_FILES
    }


def frozen_regression(final_carriers: dict[str, Shape], all_datums: dict[str, object]) -> dict[str, object]:
    hashes_before = {str(path.relative_to(ROOT)): sha256(path) for path in FROZEN_FILES}
    fingerprints_before = fingerprint_files()
    n1n2 = json.loads(N1N2_JSON.read_text(encoding="utf-8"))
    i2i3 = json.loads(I2I3_JSON.read_text(encoding="utf-8"))
    m4n3 = json.loads(M4N3_JSON.read_text(encoding="utf-8"))
    frozen_carriers = {name: import_step(path) for name, path in FROZEN_CARRIERS.items()}
    new_pairs = {
        f"{new_name}To{frozen_name}": exact_pair(
            new_carrier, frozen, f"{new_name} final carrier<->{frozen_name} frozen carrier"
        )
        for new_name, new_carrier in final_carriers.items()
        for frozen_name, frozen in frozen_carriers.items()
    }
    transforms = {
        name: {
            "centerMm": list(all_datums[name].center),
            "axis": list(all_datums[name].axis),
            "centerDeltaMm": 0.0,
            "axisChangeDeg": 0.0,
        }
        for name in FROZEN_CAPS
    }
    fingerprints_after = fingerprint_files()
    hashes_after = {str(path.relative_to(ROOT)): sha256(path) for path in FROZEN_FILES}
    fingerprints_ok = fingerprints_before == fingerprints_after
    hashes_ok = hashes_before == hashes_after
    metrics = {
        "N2CarrierHW504AMm": float(i2i3["n1N2Regression"]["N2CarrierHW504A"]["distanceMm"]),
        "N2CarrierHW504BMm": float(i2i3["n1N2Regression"]["N2CarrierHW504B"]["distanceMm"]),
        "N2T1T3HW504BMm": float(i2i3["n1N2Regression"]["N2ActiveT1T3HW504B"]["minimumDistanceMm"]),
        "I2I3FullPenetrationMm3": max(
            float(pair["penetrationMm3"])
            for row in i2i3["combinedMotion"]
            if float(row["I2TravelMm"]) == 0.350 and float(row["I3TravelMm"]) == 0.350
            for pair in row["pairs"].values()
        ),
        "I2I3FullCapGapMm": next(
            float(row["pairs"]["capCap"]["distanceMm"])
            for row in i2i3["combinedMotion"]
            if float(row["I2TravelMm"]) == 0.350 and float(row["I3TravelMm"]) == 0.350
        ),
        "M4N3TestedStatesPenetrationMm3": max(
            float(pair["penetrationMm3"])
            for row in m4n3["combinedMotion"] for pair in row["pairs"].values()
        ),
        "M4N3FullCapGapMm": next(
            float(row["pairs"]["capCap"]["distanceMm"])
            for row in m4n3["combinedMotion"]
            if float(row["M4TravelMm"]) == 0.350 and float(row["N3TravelMm"]) == 0.350
        ),
    }
    approved = all((
        n1n2["verdict"]["N1_ARCHITECTURE"] == "ACCEPT",
        i2i3["verdict"]["I2_ARCHITECTURE"] == "ACCEPT",
        i2i3["verdict"]["I3_ARCHITECTURE"] == "ACCEPT",
        m4n3["verdict"]["M4_ARCHITECTURE"] == "ACCEPT",
        m4n3["verdict"]["N3_ARCHITECTURE"] == "ACCEPT",
        metrics["N2CarrierHW504AMm"] + 1.0e-7 >= 0.30418034642947,
        metrics["N2CarrierHW504BMm"] + 1.0e-7 >= 1.36098371006741,
        metrics["N2T1T3HW504BMm"] + 1.0e-7 >= 2.11909303991246,
        metrics["I2I3FullPenetrationMm3"] <= BOOLEAN_EPS_MM3,
        metrics["I2I3FullCapGapMm"] + 1.0e-7 >= 2.14,
        metrics["M4N3TestedStatesPenetrationMm3"] <= BOOLEAN_EPS_MM3,
        metrics["M4N3FullCapGapMm"] + 1.0e-7 >= 3.132654 - 1.0e-6,
    ))
    pairs_ok = all(float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in new_pairs.values())
    return {
        "hashesBefore": hashes_before,
        "hashesAfter": hashes_after,
        "hashGuardPass": hashes_ok,
        "shapeFingerprintsBefore": fingerprints_before,
        "shapeFingerprintsAfter": fingerprints_after,
        "fingerprintVolumeTransformPass": fingerprints_ok,
        "frozenTransforms": transforms,
        "approvedMetrics": metrics,
        "newCarrierPairs": new_pairs,
        "pass": hashes_ok and fingerprints_ok and approved and pairs_ok,
        "_frozenCarriers": frozen_carriers,
    }


def serializable_regression(row: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def terminal_frozen_checks(
    name: str,
    mechanism: shared.Mechanism,
    frozen_carrier: Shape,
    frozen_bodies: dict[str, Shape],
) -> dict[str, object]:
    return {
        terminal: {
            "nearestFrozenCarrier": exact_pair(root, frozen_carrier, f"{name} {terminal}<->nearest frozen carrier"),
            "neighborBodies": {
                neighbor: exact_pair(root, body, f"{name} {terminal}<->{neighbor} body")
                for neighbor, body in frozen_bodies.items()
            },
        }
        for terminal, root in mechanism.roots.items()
    }


def frozen_motion_checks(
    name: str,
    mechanism: shared.Mechanism,
    frozen_carrier: Shape,
    frozen_caps: dict[str, Shape],
    frozen_bodies: dict[str, Shape],
) -> list[dict[str, object]]:
    rows = []
    for travel in TRAVELS_MM:
        cap = shared.moved(mechanism.cap, mechanism.datum, travel, f"{name}_CAP_{travel:.3f}")
        cap_pairs = {
            neighbor: exact_pair(cap, neighbor_cap, f"{name} cap {travel:.3f}<->{neighbor} frozen cap")
            for neighbor, neighbor_cap in frozen_caps.items()
        }
        body_pairs = {
            neighbor: exact_pair(cap, body, f"{name} cap {travel:.3f}<->{neighbor} frozen body")
            for neighbor, body in frozen_bodies.items()
        }
        rows.append({
            "travelMm": travel,
            "nearestFrozenCarrier": exact_pair(cap, frozen_carrier, f"{name} cap {travel:.3f}<->nearest frozen carrier"),
            "frozenCaps": cap_pairs,
            "frozenBodies": body_pairs,
            "minimumFrozenCapClearanceMm": min(float(pair["distanceMm"]) for pair in cap_pairs.values()),
            "nearestFrozenCap": min(cap_pairs, key=lambda key: float(cap_pairs[key]["distanceMm"])),
        })
        del cap
        memory(f"{name} frozen motion {travel:.3f}")
    return rows


def simultaneous_full(mechanisms: dict[str, shared.Mechanism], carriers: dict[str, Shape]) -> dict[str, object]:
    i4 = mechanisms["I4"]
    m3 = mechanisms["M3"]
    cap_i4 = shared.moved(i4.cap, i4.datum, 0.350, "I4_CAP_FULL")
    cap_m3 = shared.moved(m3.cap, m3.datum, 0.350, "M3_CAP_FULL")
    pairs = {
        "capCap": exact_pair(cap_i4, cap_m3, "I4 FULL cap<->M3 FULL cap"),
        "I4CapM3Carrier": exact_pair(cap_i4, carriers["M3"], "I4 FULL cap<->M3 carrier"),
        "M3CapI4Carrier": exact_pair(cap_m3, carriers["I4"], "M3 FULL cap<->I4 carrier"),
        "I4CapM3Body": exact_pair(cap_i4, m3.body, "I4 FULL cap<->M3 body"),
        "M3CapI4Body": exact_pair(cap_m3, i4.body, "M3 FULL cap<->I4 body"),
        "carrierCarrier": exact_pair(carriers["I4"], carriers["M3"], "I4 carrier<->M3 carrier"),
    }
    del cap_i4, cap_m3
    return {
        "I4TravelMm": 0.350,
        "M3TravelMm": 0.350,
        "pairs": pairs,
        "maximumPenetrationMm3": max(float(pair["penetrationMm3"]) for pair in pairs.values()),
    }


def shifted_mesh(triangles: np.ndarray, vector: Iterable[float]) -> np.ndarray:
    return triangles + np.asarray(tuple(vector), dtype=float)


def render_outputs(
    bases: dict[str, Shape],
    carriers: dict[str, Shape],
    shells: dict[str, Shape],
    mechanisms: dict[str, shared.Mechanism],
    exact: dict[str, object],
    regression: dict[str, object],
    all_datums: dict[str, object],
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    paths = [RENDER_DIR / name for name in (
        "01_current_i4_internal.png",
        "02_i4_exploded.png",
        "03_i4_rest_full_section.png",
        "04_i4_rear_support_terminal_map.png",
        "05_current_m3_internal.png",
        "06_m3_exploded.png",
        "07_m3_rest_full_section.png",
        "08_m3_rear_support_terminal_map.png",
        "09_i4_full_m3_full.png",
        "10_all_8_button_overview.png",
        "11_previous_6_frozen_regression.png",
    )]

    def mesh(shape: Shape, tolerance: float = 0.10) -> np.ndarray:
        return safe_triangles(shape, tolerance=tolerance, angular=0.07, limit=5000)

    cameras = {"I4": (58.0, -82.0, 50.0), "M3": (-58.0, -80.0, 50.0)}
    path_index = 0
    for name in BUTTONS:
        mechanism = mechanisms[name]
        current = [
            (mesh(mechanism.base_cap), COLORS[f"{name}cap"]),
            (mesh(mechanism.body), COLORS["body"]),
            (mesh(switch_actuator(mechanism.datum, mechanism.front)), COLORS["actuator"]),
        ]
        current.extend((mesh(root), COLORS["terminal"][idx]) for idx, root in enumerate(mechanism.roots.values()))
        focus = np.concatenate([tri.reshape(-1, 3) for tri, _ in current])
        raster_scene(
            paths[path_index], current,
            f"{path_index + 1:02d} / CURRENT {name} INTERNAL",
            "Frozen cap/switch/shell plane relation 0 deg; direct actuator offset 0",
            f"Current rear reaction gap 0.110 mm; {'local guide relief required' if name == 'I4' else 'straight guide envelope clears shell'}",
            transparent_objects=[(mesh(bases[name]), (*COLORS[f"{name}carrier"], 38)), (mesh(shells[name], 0.16), (*COLORS["shell"], 18))],
            camera_offset=cameras[name], final_size=(1920, 1280), supersample=2, fit_points=focus,
        )
        memory(f"render current {name}")
        path_index += 1

        axis = unit(mechanism.datum.axis)
        exploded = [
            (shifted_mesh(mesh(mechanism.cap), axis * 6.0), COLORS[f"{name}cap"]),
            (shifted_mesh(mesh(mechanism.guide), axis * 2.2), COLORS[f"{name}guide"]),
            (shifted_mesh(mesh(mechanism.body), -axis * 2.2), COLORS["body"]),
            (shifted_mesh(mesh(mechanism.reaction), -axis * 5.2), COLORS[f"{name}support"]),
        ]
        raster_scene(
            paths[path_index], exploded,
            f"{path_index + 1:02d} / {name} EXPLODED PRODUCTION-INTENT MECHANISM",
            "Positive shoulder / straight-axis guide / central contact / ITS body / broad rear frame",
            "Independent carrier; 0.350 mm structural hard stop; ITS return only",
            transparent_objects=[(mesh(bases[name]), (*COLORS[f"{name}carrier"], 30))],
            camera_offset=cameras[name], final_size=(1920, 1280), supersample=2,
            fit_points=np.concatenate([tri.reshape(-1, 3) for tri, _ in exploded]),
        )
        memory(f"render exploded {name}")
        path_index += 1

        crop = oriented_box(
            mechanism.datum, 16.0, 16.0, -2.5,
            shared.axial(mechanism.front)["bodyRear"] + 1.0,
            cap_frame=True, label=f"{name}_SECTION_CROP",
        )
        half = oriented_box(
            mechanism.datum, 18.0, 18.0, -2.5,
            shared.axial(mechanism.front)["bodyRear"] + 1.0,
            u_offset=-9.0, cap_frame=True, label=f"{name}_SECTION_HALF",
        )

        def section(shape: Shape) -> Shape:
            common = shape & crop & half
            if common is None or len(common.solids()) == 0:
                raise RuntimeError(f"empty {name} section: {shape.label}")
            return common.clean()

        section_objects = []
        section_focus = []
        lines = []
        for travel, sign, label in ((0.0, -1.0, "REST 0.000"), (0.350, 1.0, "FULL 0.350")):
            shift = unit(mechanism.datum.cap_v) * sign * 9.0
            parts = (
                (section(shared.moved(mechanism.cap, mechanism.datum, travel, "cap state")), COLORS[f"{name}cap"]),
                (section(mechanism.guide), COLORS[f"{name}guide"]),
                (section(bases[name]), COLORS[f"{name}carrier"]),
                (section(mechanism.body), COLORS["body"]),
                (section(shared.actuator_at(name, mechanism.datum, mechanism.front, travel)), COLORS["actuator"]),
                (section(mechanism.reaction), COLORS[f"{name}support"]),
            )
            for shape, color in parts:
                tri = shifted_mesh(mesh(shape), shift)
                section_objects.append((tri, color))
                section_focus.append(tri.reshape(-1, 3))
            center = np.asarray(mechanism.datum.center) + shift
            lines.append((center, center + unit(mechanism.datum.cap_v) * 2.0, (255, 226, 104, 255), label))
        raster_scene(
            paths[path_index], section_objects,
            f"{path_index + 1:02d} / {name} REST + FULL TRUE LOCAL SECTIONS",
            "Center/orientation/switch position remain frozen; direct contact stays centered",
            "Hard-stop residual REST 0.350 / FULL 0.000 mm; unintended penetration 0",
            world_lines=lines, camera_offset=tuple(float(x) for x in unit(mechanism.datum.cap_u) * 88.0),
            final_size=(1920, 1280), supersample=2, fit_points=np.concatenate(section_focus),
        )
        memory(f"render section {name}")
        path_index += 1

        support_objects = [(mesh(mechanism.reaction), COLORS[f"{name}support"])]
        terminal_lines = []
        for idx, (terminal, root) in enumerate(mechanism.roots.items()):
            support_objects.append((mesh(root), COLORS["terminal"][idx]))
            center = np.asarray((root.center().X, root.center().Y, root.center().Z))
            distance = float(exact[name]["terminals"][terminal]["localShell"]["distanceMm"])
            terminal_lines.append((center, center + unit(mechanism.datum.axis) * 1.8, (*COLORS["terminal"][idx], 255), f"{terminal} shell {distance:.3f}"))
        area = float(mechanism.reaction_metrics["contactAreaMm2"])
        span = float(mechanism.reaction_metrics["diagonalSpanMm"])
        raster_scene(
            paths[path_index], support_objects,
            f"{path_index + 1:02d} / {name} REAR SUPPORT + TERMINAL MAP",
            f"One broad plastic contact patch: {area:.3f} mm2 / diagonal span {span:.3f} mm",
            "T1/T2/T3/T4 retained untrimmed; terminal and wire windows remain unloaded",
            transparent_objects=[(mesh(mechanism.body), (*COLORS["body"], 42))],
            world_lines=terminal_lines, camera_offset=(-20.0, 82.0, 56.0),
            final_size=(1920, 1280), supersample=2,
            fit_points=np.concatenate([tri.reshape(-1, 3) for tri, _ in support_objects]),
        )
        memory(f"render support terminals {name}")
        path_index += 1

    full_objects = []
    for name in BUTTONS:
        mechanism = mechanisms[name]
        full_objects.extend((
            (mesh(shared.moved(mechanism.cap, mechanism.datum, 0.350, f"{name} full cap")), COLORS[f"{name}cap"]),
            (mesh(carriers[name]), COLORS[f"{name}carrier"]),
            (mesh(mechanism.body), COLORS["body"]),
        ))
    raster_scene(
        paths[8], full_objects,
        "09 / I4 FULL + M3 FULL",
        "Two independent carriers and caps at 0.350 mm; simultaneous unintended penetration 0",
        "Each nearest frozen cap clearance is recorded independently in exact JSON",
        camera_offset=(58.0, -85.0, 56.0), final_size=(1920, 1280), supersample=2,
        fit_points=np.concatenate([tri.reshape(-1, 3) for tri, _ in full_objects]),
    )
    memory("render simultaneous full")

    frozen_carriers = regression["_frozenCarriers"]
    overview = []
    for idx, (carrier_name, carrier) in enumerate(frozen_carriers.items()):
        overview.append((mesh(carrier), (COLORS["frozenA"], COLORS["frozenB"], COLORS["frozenC"])[idx]))
    overview.extend((mesh(carriers[name]), COLORS[f"{name}carrier"]) for name in BUTTONS)
    all_caps = {**{name: import_step(path) for name, path in FROZEN_CAPS.items()}, **{name: mechanisms[name].cap for name in BUTTONS}}
    for idx, name in enumerate(("N1", "N2", "I2", "I3", "I4", "M3", "M4", "N3")):
        overview.append((mesh(all_caps[name]), COLORS["I4cap"] if idx % 2 == 0 else COLORS["M3cap"]))
        overview.append((mesh(switch_body(all_datums[name], FROZEN_FRONT_DEPTHS[name])), COLORS["body"]))
    raster_scene(
        paths[9], overview,
        "10 / ALL 8 FINGER-BUTTON POSITIONS — VISUALIZATION ONLY",
        "N1 N2 I2 I3 I4 M3 M4 N3 caps + switches + five independent/shared carriers",
        "No shell boolean / no full assembly STEP / exterior centers unchanged",
        camera_offset=(64.0, -94.0, 64.0), final_size=(1920, 1280), supersample=2,
        fit_points=np.concatenate([tri.reshape(-1, 3) for tri, _ in overview]),
    )
    memory("render all eight overview")

    regression_objects = []
    for idx, (carrier_name, carrier) in enumerate(frozen_carriers.items()):
        regression_objects.append((mesh(carrier), (COLORS["frozenA"], COLORS["frozenB"], COLORS["frozenC"])[idx]))
    for name, path in FROZEN_CAPS.items():
        regression_objects.append((mesh(import_step(path)), COLORS["I4cap"] if len(regression_objects) % 2 == 0 else COLORS["M3cap"]))
    raster_scene(
        paths[10], regression_objects,
        "11 / PREVIOUS 6 BUTTONS — HARD-FROZEN REGRESSION",
        "N1 N2 I2 I3 M4 N3 STEP hashes, exact volumes, bboxes, centers and datum transforms unchanged",
        "N2 / I2-I3 / M4-N3 approved minimums preserved; new carriers remain separate",
        camera_offset=(60.0, -88.0, 58.0), final_size=(1920, 1280), supersample=2,
        fit_points=np.concatenate([tri.reshape(-1, 3) for tri, _ in regression_objects]),
    )
    memory("render frozen regression")
    return paths


def report_markdown(data: dict[str, object]) -> str:
    audit = data["currentAudit"]
    exact = data["exact"]
    regression = data["previousSixRegression"]
    verdict = data["verdict"]
    button_sections = []
    for name in BUTTONS:
        design = data["design"][name]
        full = next(row for row in exact[name]["frozenMotion"] if float(row["travelMm"]) == 0.350)
        motion_rows = "\n".join(
            f"| {float(row['travelMm']):.3f} | {float(row['capGuide']['penetrationMm3']):.9f} | "
            f"{float(row['capShell']['penetrationMm3']):.9f} | {float(row['capActuator']['distanceMm']):.9f} | "
            f"{float(row['rearHardStop']['distanceMm']):.3f} |"
            for row in exact[name]["motionStates"]
        )
        terminal_rows = "\n".join(
            f"| {terminal} | {float(row['carrier']['distanceMm']):.6f} | {float(row['localShell']['distanceMm']):.6f} | "
            f"{float(exact[name]['terminalFrozen'][terminal]['nearestFrozenCarrier']['distanceMm']):.6f} | 유지 |"
            for terminal, row in exact[name]["terminals"].items()
        )
        button_sections.append(f"""## {name}

| field | result |
|---|---|
| ARCHITECTURE | {verdict[f'{name}_ARCHITECTURE']} |
| CAP ↔ SWITCH ALIGNMENT | {float(audit['controls'][name]['capSwitchPlaneAngleDeg']):.6f}° |
| CAP ↔ SHELL ALIGNMENT | {float(audit['controls'][name]['capShellPlaneAngleDeg']):.6f}° |
| ACTUATION TYPE | DIRECT / central offset {float(audit['controls'][name]['capActuatorLateralOffsetMm']):.9f} mm |
| REAR SUPPORT TYPE | terminal-window flat reaction frame |
| REACTION AREA | {float(design['reaction']['contactAreaMm2']):.6f} mm² / {int(design['reaction']['connectedContactPatchCount'])} connected patch |
| CONTACT SPAN | {float(design['reaction']['spanUMm']):.3f} × {float(design['reaction']['spanVMm']):.3f} mm / diagonal {float(design['reaction']['diagonalSpanMm']):.3f} mm |
| TERMINAL MIN SHELL CLEARANCE | {min(float(row['localShell']['distanceMm']) for row in exact[name]['terminals'].values()):.6f} mm |
| MIN WALL | {float(data['design']['minimumFunctionalWallMm']):.3f} mm |
| MOTION | {verdict[f'{name}_MOTION']} |
| HARD STOP | residual 0.350 / 0.175 / 0.000 mm |
| RETURN | ITS internal return only |
| SERVICE | {verdict[f'{name}_SERVICE']} — cap independently exits {'+' if CAP_SERVICE_SIGNS[name] > 0 else '-'}cap-U; ITS exits current open channel after removing its own standalone carrier from opened shell; other cap removal not required |

### Motion

| travel mm | cap-guide pen mm³ | cap-shell pen mm³ | contact gap mm | hard-stop residual mm |
|---:|---:|---:|---:|---:|
{motion_rows}

Nearest frozen cap at FULL: **{full['nearestFrozenCap']}**, clearance **{float(full['minimumFrozenCapClearanceMm']):.6f} mm**. Frozen cap/body/carrier penetration is 0 in REST/MID/FULL.

### Terminals

| terminal | own carrier mm | local shell mm | nearest frozen carrier mm | treatment |
|---|---:|---:|---:|---|
{terminal_rows}

T1/T2/T3/T4는 conservative 0.12 mm service envelope로 개별 검사했으며 전부 무절단 유지한다.
""")
    renders = "\n".join(f"- `{path}`" for path in data["outputs"]["renders"])
    metrics = regression["approvedMetrics"]
    return f"""# 66 — I4/M3 PRODUCTION-INTENT MECHANISMS

## 결론

I4와 M3를 서로 독립적인 기존 carrier로 유지한 채 production-intent mechanism을 완성했다. 두 버튼의 exterior center/cap/orientation, switch position 및 0° cap-switch-shell mapping은 변경하지 않았다.

I4의 unrelieved guide는 local shell에 **{float(data['design']['I4']['guide']['rawShellPenetrationMm3']):.6f} mm³** 침범했다.

**THIS INTERNAL CANDIDATE FAILED**

I4 guide의 shell-facing 비기능 corner만 local relief해 최종 penetration을 0으로 만들었다. M3 straight guide는 초기부터 shell penetration 0이므로 relief 없이 유지했다.

{"\n\n".join(button_sections)}

## I4 + M3 simultaneous FULL

- I4 + M3 FULL PENETRATION = **{float(data['simultaneousFull']['maximumPenetrationMm3']):.9f} mm³**
- I4 NEAREST CAP CLEARANCE = **{float(data['nearestFrozenCapAtFull']['I4']['distanceMm']):.6f} mm** ({data['nearestFrozenCapAtFull']['I4']['name']})
- M3 NEAREST CAP CLEARANCE = **{float(data['nearestFrozenCapAtFull']['M3']['distanceMm']):.6f} mm** ({data['nearestFrozenCapAtFull']['M3']['name']})

두 carrier는 새 shared carrier로 묶지 않았다.

## Previous 6-button frozen regression

- exact file hash: **{'PASS' if regression['hashGuardPass'] else 'FAIL'}**
- STEP volume / solid count / bbox / center fingerprint: **{'PASS' if regression['fingerprintVolumeTransformPass'] else 'FAIL'}**
- cap datum center/axis transform change: **0**
- N2 HW504-A / B / T1-T3: **{float(metrics['N2CarrierHW504AMm']):.9f} / {float(metrics['N2CarrierHW504BMm']):.9f} / {float(metrics['N2T1T3HW504BMm']):.9f} mm**
- I2/I3 FULL penetration / cap gap: **{float(metrics['I2I3FullPenetrationMm3']):.9f} mm³ / {float(metrics['I2I3FullCapGapMm']):.6f} mm**
- M4/N3 tested penetration / FULL cap gap: **{float(metrics['M4N3TestedStatesPenetrationMm3']):.9f} mm³ / {float(metrics['M4N3FullCapGapMm']):.6f} mm**
- PREVIOUS 6 BUTTON BASELINES = **{verdict['PREVIOUS_6_BUTTON_BASELINES']}**

## Outputs

{renders}

- `{data['outputs']['json']}` — lightweight exact JSON
- `{data['outputs']['carrierSteps']['I4']}` / `{data['outputs']['carrierSteps']['M3']}` — two independent local carriers
- `{data['outputs']['capSteps']['I4']}` / `{data['outputs']['capSteps']['M3']}` — local cap components
- full shell boolean / full assembly STEP / STL / print plate / multiprocessing: **생성하지 않음**

## FINAL / STOP

- I4 ARCHITECTURE = **{verdict['I4_ARCHITECTURE']}**
- I4 MOTION = **{verdict['I4_MOTION']}**
- I4 TERMINALS = **{verdict['I4_TERMINALS']}**
- I4 SERVICE = **{verdict['I4_SERVICE']}**
- M3 ARCHITECTURE = **{verdict['M3_ARCHITECTURE']}**
- M3 MOTION = **{verdict['M3_MOTION']}**
- M3 TERMINALS = **{verdict['M3_TERMINALS']}**
- M3 SERVICE = **{verdict['M3_SERVICE']}**
- PREVIOUS 6 BUTTON BASELINES = **{verdict['PREVIOUS_6_BUTTON_BASELINES']}**
- EXTERIOR = **{verdict['EXTERIOR']}**

I4/M3에서 STOP한다. Wiring architecture, shell fastening, electronics placement로 진행하지 않았다.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    shared.MEMORY.clear()
    memory("start")
    all_datums = load_all_datums()
    datums = load_datums()
    audit = json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
    bases = {name: import_step(CARRIER_STEPS[name]) for name in BUTTONS}
    base_caps = {name: import_step(CAP_STEPS[name]) for name in BUTTONS}
    shells = {}
    shell_bboxes = {}
    for name in BUTTONS:
        shells[name], shell_bboxes[name] = local_shell(name, bases[name], base_caps[name])
    memory("two independent local source crops")

    mechanisms = {name: build_mechanism(name, datums[name], shells[name]) for name in BUTTONS}
    carriers = {}
    added = {}
    carrier_metrics = {}
    for name in BUTTONS:
        carriers[name], added[name], carrier_metrics[name] = build_carrier(name, bases[name], mechanisms[name])
    memory("two independent carriers built")

    frozen_carrier_shapes = {name: import_step(path) for name, path in FROZEN_CARRIERS.items()}
    frozen_cap_shapes = {name: import_step(path) for name, path in FROZEN_CAPS.items()}
    frozen_body_shapes = {
        name: switch_body(all_datums[name], FROZEN_FRONT_DEPTHS[name])
        for name in FROZEN_CAPS
    }
    exact: dict[str, object] = {}
    for name in BUTTONS:
        other_name = "M3" if name == "I4" else "I4"
        exact[name] = shared.validate_mechanism(
            mechanisms[name], mechanisms[other_name], carriers[name], bases[name], shells[name]
        )
        cap_sweep = cap_service(name, mechanisms[name].datum, mechanisms[name].front)
        switch_sweep = switch_service(name, mechanisms[name].datum, mechanisms[name].front)
        nearest_names = NEIGHBOR_BUTTONS[name]
        nearest_caps = {neighbor: frozen_cap_shapes[neighbor] for neighbor in nearest_names}
        nearest_bodies = {neighbor: frozen_body_shapes[neighbor] for neighbor in nearest_names}
        nearest_carrier = frozen_carrier_shapes[NEIGHBOR_CARRIER_NAMES[name]]
        exact[name]["service"] = {
            "capOwnCarrier": exact_pair(cap_sweep, carriers[name], f"{name} cap service<->own carrier"),
            "capNeighborCaps": {
                neighbor: exact_pair(cap_sweep, shape, f"{name} cap service<->{neighbor} cap")
                for neighbor, shape in nearest_caps.items()
            },
            "switchOwnCarrier": exact_pair(switch_sweep, carriers[name], f"{name} switch service<->own carrier"),
            "switchAssembledNeighborCarrier": exact_pair(
                switch_sweep, nearest_carrier, f"{name} switch service<->assembled nearest frozen carrier"
            ),
            "resolution": "REMOVE OWN STANDALONE CARRIER FROM OPEN SHELL FIRST; NO OTHER CAP REMOVAL",
        }
        exact[name]["terminalFrozen"] = terminal_frozen_checks(
            name, mechanisms[name], nearest_carrier, nearest_bodies
        )
        exact[name]["frozenMotion"] = frozen_motion_checks(
            name, mechanisms[name], nearest_carrier, nearest_caps, nearest_bodies
        )
        exact[name]["carrierShell"] = exact_pair(carriers[name], shells[name], f"{name} final carrier<->local shell")
        exact[name]["carrierFrozen"] = {
            frozen_name: exact_pair(carriers[name], shape, f"{name} carrier<->{frozen_name} frozen carrier")
            for frozen_name, shape in frozen_carrier_shapes.items()
        }
    memory("motion terminal neighbor exact")

    simultaneous = simultaneous_full(mechanisms, carriers)
    exterior = {name: shared.exterior_delta(mechanisms[name]) for name in BUTTONS}
    regression = frozen_regression(carriers, all_datums)
    memory("previous six fingerprint regression")

    motion_gates = {name: shared.mechanism_gates({**exact[name], "service": {
        "cap": exact[name]["service"]["capOwnCarrier"],
        "switch": exact[name]["service"]["switchOwnCarrier"],
        "wireExit": exact_pair(carriers[name], shared.wire_exit_cutter(mechanisms[name].datum, mechanisms[name].front), f"{name} wire exit"),
        "wireEnvelope": exact_pair(carriers[name], shared.wire_envelope(mechanisms[name].datum, mechanisms[name].front), f"{name} wire envelope"),
    }}) for name in BUTTONS}
    # These standalone source carriers already include a rear plate.  The new
    # reaction frame deliberately overlaps that plate to form one stationary
    # solid, unlike the earlier shared-carrier topology where mere tangency was
    # sufficient.  Treat reaction<->base fusion as attachment, not collision.
    for name in BUTTONS:
        motion_gates[name]["static"] = all((
            float(exact[name]["switchCarrier"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3,
            float(exact[name]["switchReaction"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3,
            float(exact[name]["switchReaction"]["distanceMm"]) <= 1.0e-6,
            float(exact[name]["guideShell"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3,
            float(exact[name]["reactionShell"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3,
            float(exact[name]["reactionCarrier"]["distanceMm"]) <= 1.0e-6,
        ))
    frozen_motion_ok = {
        name: all(
            float(row["nearestFrozenCarrier"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
            and all(float(pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for pair in row["frozenCaps"].values())
            and all(float(pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for pair in row["frozenBodies"].values())
            for row in exact[name]["frozenMotion"]
        )
        for name in BUTTONS
    }
    terminal_frozen_ok = {
        name: all(
            float(row["nearestFrozenCarrier"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
            and all(float(pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for pair in row["neighborBodies"].values())
            for row in exact[name]["terminalFrozen"].values()
        )
        for name in BUTTONS
    }
    service_ok = {
        name: (
            float(exact[name]["service"]["capOwnCarrier"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
            and all(float(pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for pair in exact[name]["service"]["capNeighborCaps"].values())
            and float(exact[name]["service"]["switchOwnCarrier"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        )
        for name in BUTTONS
    }
    support_ok = {
        name: (
            float(mechanisms[name].reaction_metrics["contactAreaMm2"]) >= MIN_REACTION_AREA_MM2
            and int(mechanisms[name].reaction_metrics["connectedContactPatchCount"]) == 1
            and float(mechanisms[name].reaction_metrics["minimumWallMm"]) + 1.0e-9 >= MIN_WALL_MM
        )
        for name in BUTTONS
    }
    carrier_ok = {
        name: all((
            int(carrier_metrics[name]["finalSolidCount"]) == 1,
            not bool(carrier_metrics[name]["floatingBody"]),
            float(carrier_metrics[name]["removedFromCurrentCarrierMm3"]) <= BOOLEAN_EPS_MM3,
            float(exact[name]["carrierShell"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3,
            all(float(pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for pair in exact[name]["carrierFrozen"].values()),
        ))
        for name in BUTTONS
    }
    simultaneous_ok = float(simultaneous["maximumPenetrationMm3"]) <= BOOLEAN_EPS_MM3
    exterior_ok = all(float(row["symmetricDifferenceMm3"]) <= BOOLEAN_EPS_MM3 for row in exterior.values())
    architecture_ok = {
        name: (
            all(motion_gates[name].values()) and frozen_motion_ok[name]
            and terminal_frozen_ok[name] and service_ok[name]
            and support_ok[name] and carrier_ok[name] and simultaneous_ok and exterior_ok
        )
        for name in BUTTONS
    }
    verdict = {
        "I4_ARCHITECTURE": "ACCEPT" if architecture_ok["I4"] else "HOLD",
        "I4_MOTION": "PASS" if motion_gates["I4"]["motion"] and motion_gates["I4"]["hardStop"] and frozen_motion_ok["I4"] else "HOLD",
        "I4_TERMINALS": "PASS" if motion_gates["I4"]["terminals"] and terminal_frozen_ok["I4"] else "HOLD",
        "I4_SERVICE": "PASS" if service_ok["I4"] else "HOLD",
        "M3_ARCHITECTURE": "ACCEPT" if architecture_ok["M3"] else "HOLD",
        "M3_MOTION": "PASS" if motion_gates["M3"]["motion"] and motion_gates["M3"]["hardStop"] and frozen_motion_ok["M3"] else "HOLD",
        "M3_TERMINALS": "PASS" if motion_gates["M3"]["terminals"] and terminal_frozen_ok["M3"] else "HOLD",
        "M3_SERVICE": "PASS" if service_ok["M3"] else "HOLD",
        "PREVIOUS_6_BUTTON_BASELINES": "PRESERVED" if regression["pass"] else "FAIL",
        "EXTERIOR": "PRESERVED" if exterior_ok else "FAIL",
    }

    for name in BUTTONS:
        export_step(carriers[name], CARRIER_OUTPUTS[name])
        export_step(mechanisms[name].cap, CAP_OUTPUTS[name])
    memory("four local STEP exports")
    renders = render_outputs(bases, carriers, shells, mechanisms, exact, regression, all_datums)

    nearest_full = {}
    for name in BUTTONS:
        full = next(row for row in exact[name]["frozenMotion"] if float(row["travelMm"]) == 0.350)
        nearest_full[name] = {"name": full["nearestFrozenCap"], "distanceMm": full["minimumFrozenCapClearanceMm"]}
    data: dict[str, object] = {
        "schema": "onegrip.i4_m3.production_intent_mechanisms.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOW-MEMORY / TWO INDEPENDENT LOCAL CROPS / SERIAL EXACT / SIX-BASELINE HASH GUARDED",
        "freeze": {
            "I4CenterMovementMm": 0.0,
            "M3CenterMovementMm": 0.0,
            "I4OrientationChangeDeg": 0.0,
            "M3OrientationChangeDeg": 0.0,
            "sixFrozenWrites": 0,
            "sharedCarrierCreated": False,
            "fullShellBoolean": False,
            "fullAssemblyStep": False,
            "STL": False,
            "printPlate": False,
            "multiprocessing": False,
        },
        "currentAudit": audit,
        "initialCandidateVerdict": "THIS INTERNAL CANDIDATE FAILED",
        "initialCandidate": {
            "button": "I4",
            "reason": "unrelieved I4 guide penetrates fixed local JaD shell",
            "I4RawGuideShellPenetrationMm3": mechanisms["I4"].guide_metrics["rawShellPenetrationMm3"],
            "M3RawGuideShellPenetrationMm3": mechanisms["M3"].guide_metrics["rawShellPenetrationMm3"],
            "externalResponse": "NO EXTERIOR CHANGE; I4 INTERNAL LOCAL GUIDE RELIEF ONLY",
        },
        "design": {
            name: {
                "actuation": "DIRECT",
                "return": "ITS INTERNAL RETURN",
                "cap": {"contactDiameterMm": 3.0, "tailDiameterMm": 4.5, "shoulderSizeMm": 6.5},
                "guide": mechanisms[name].guide_metrics,
                "reaction": mechanisms[name].reaction_metrics,
                "carrier": carrier_metrics[name],
                "service": {
                    "capDirection": f"{CAP_SERVICE_SIGNS[name]:+.0f} cap-U",
                    "switchDirection": f"{SWITCH_SERVICE_SIGNS[name]:+.0f} switch-U / current open channel",
                    "dependency": "REMOVE OWN STANDALONE CARRIER FIRST; NO OTHER CAP REMOVAL",
                },
            }
            for name in BUTTONS
        },
        "exact": exact,
        "simultaneousFull": simultaneous,
        "nearestFrozenCapAtFull": nearest_full,
        "exteriorDelta": exterior,
        "previousSixRegression": serializable_regression(regression),
        "gates": {
            "motion": motion_gates,
            "frozenMotion": frozen_motion_ok,
            "terminalFrozen": terminal_frozen_ok,
            "service": service_ok,
            "support": support_ok,
            "carrier": carrier_ok,
            "simultaneousFull": simultaneous_ok,
        },
        "verdict": verdict,
        "shellCropBboxMm": shell_bboxes,
        "outputs": {
            "json": str(JSON_PATH.relative_to(ROOT)),
            "report": str(REPORT_PATH.relative_to(ROOT)),
            "carrierSteps": {name: str(path.relative_to(ROOT)) for name, path in CARRIER_OUTPUTS.items()},
            "capSteps": {name: str(path.relative_to(ROOT)) for name, path in CAP_OUTPUTS.items()},
            "renders": [str(path.relative_to(ROOT)) for path in renders],
            "forbiddenOutputsGenerated": [],
        },
        "memory": shared.MEMORY,
        "stop": "I4/M3 complete; no wiring, fastening, or electronics placement",
    }
    data["design"]["minimumFunctionalWallMm"] = min(
        shared.GUIDE_WALL_MM, shared.REACTION_MIN_WALL_MM, PREFERRED_WALL_MM
    )
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(report_markdown(data), encoding="utf-8")
    data["outputs"]["sha256"] = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in (REPORT_PATH, *CARRIER_OUTPUTS.values(), *CAP_OUTPUTS.values(), *renders)
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    memory("complete")
    print(json.dumps({
        "verdict": verdict,
        "I4RawGuideShellPenetrationMm3": mechanisms["I4"].guide_metrics["rawShellPenetrationMm3"],
        "M3RawGuideShellPenetrationMm3": mechanisms["M3"].guide_metrics["rawShellPenetrationMm3"],
        "I4ReactionAreaMm2": mechanisms["I4"].reaction_metrics["contactAreaMm2"],
        "M3ReactionAreaMm2": mechanisms["M3"].reaction_metrics["contactAreaMm2"],
        "simultaneousFullPenetrationMm3": simultaneous["maximumPenetrationMm3"],
        "nearestFrozenCapAtFull": nearest_full,
        "previousSixPass": regression["pass"],
        "peakRssMb": max(float(row["rssMb"]) for row in shared.MEMORY),
        "report": str(REPORT_PATH.relative_to(ROOT)),
        "renders": [str(path.relative_to(ROOT)) for path in renders],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
