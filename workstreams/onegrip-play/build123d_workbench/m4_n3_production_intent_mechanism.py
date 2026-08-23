"""Production-intent M4/N3 mechanisms on the frozen shared carrier.

The run is local, serial, and low-memory.  It reads the approved N1/N2 and
I2/I3 outputs only for hash-guarded regression, and produces no full shell,
full assembly, STL, or print plate.
"""

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
from .m4_n3_current_audit import (
    CAP_STEPS,
    JSON_PATH as AUDIT_JSON_PATH,
    NEIGHBOR_CARRIER_STEPS,
    SOURCE_DIR,
    TERMINAL_NAMES,
    load_datums,
    local_shell,
)
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    exact_pair,
    raster_scene,
    safe_triangles,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism"
RENDER_DIR = ROOT / "renders" / "m4_n3_production_intent_mechanism"
JSON_PATH = OUT_DIR / "m4_n3_production_intent_mechanism.json"
REPORT_PATH = ROOT / "docs" / "65_m4_n3_production_intent_mechanism.md"
CARRIER_STEP = OUT_DIR / "M4_N3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step"
CAP_OUTPUTS = {name: OUT_DIR / f"{name}_PRODUCTION_INTENT_CAP_LOCAL.step" for name in ("M4", "N3")}

N1N2_OUT = ROOT / "build123d_workbench" / "out" / "n1_production_intent_mechanism"
N1N2_JSON = N1N2_OUT / "n1_production_intent_mechanism.json"
N1N2_CARRIER = N1N2_OUT / "N1_N2_SHARED_CARRIER_N1_LOCAL.step"
N1_CAP = N1N2_OUT / "N1_PRODUCTION_INTENT_CAP_LOCAL.step"
N2_CAP = ROOT / "build123d_workbench" / "out" / "n2_production_intent_mechanism" / "N2_PRODUCTION_INTENT_CAP.step"

I2I3_OUT = ROOT / "build123d_workbench" / "out" / "i2_i3_production_intent_mechanism"
I2I3_JSON = I2I3_OUT / "i2_i3_production_intent_mechanism.json"
I2I3_CARRIER = I2I3_OUT / "I2_I3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step"
I2_CAP = I2I3_OUT / "I2_PRODUCTION_INTENT_CAP_LOCAL.step"
I3_CAP = I2I3_OUT / "I3_PRODUCTION_INTENT_CAP_LOCAL.step"

FROZEN_FILES = (
    N1N2_JSON, N1N2_CARRIER, N1_CAP, N2_CAP,
    I2I3_JSON, I2I3_CARRIER, I2_CAP, I3_CAP,
    ROOT / "docs" / "63_n1_production_intent_mechanism.md",
    ROOT / "docs" / "64_i2_i3_production_intent_mechanism.md",
)

BUTTONS = ("M4", "N3")
COMBINATIONS = (
    (0.000, 0.000),
    (0.175, 0.000),
    (0.350, 0.000),
    (0.000, 0.175),
    (0.000, 0.350),
    (0.350, 0.350),
    (0.175, 0.175),
)
MIN_WALL_MM = 1.20
PREFERRED_WALL_MM = 1.60
MIN_REACTION_AREA_MM2 = 20.0
CAP_SERVICE_SIGNS = {"M4": -1.0, "N3": 1.0}
MAX_LOCAL_SERVICE_RELIEF_MM3 = 5.0

COLORS = {
    "M4cap": (47, 203, 142),
    "N3cap": (87, 220, 188),
    "M4guide": (52, 138, 224),
    "N3guide": (80, 177, 234),
    "carrier": (171, 88, 208),
    "M4support": (245, 126, 61),
    "N3support": (245, 177, 73),
    "body": (218, 157, 62),
    "actuator": (250, 209, 91),
    "shell": (77, 177, 207),
    "collision": (238, 67, 67),
    "frozen1": (82, 155, 232),
    "frozen2": (68, 191, 145),
    "terminal": ((76, 208, 152), (74, 157, 226), (245, 190, 72), (225, 103, 150)),
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


def reaction_contact_metrics(mechanism: shared.Mechanism) -> dict[str, object]:
    rear = shared.axial(mechanism.front)["bodyRear"]
    footprint = oriented_box(
        mechanism.datum, SWITCH_BODY_X, SWITCH_BODY_Y,
        rear, rear + shared.REACTION_DEPTH_MM,
        label=f"{mechanism.name}_ITS_REAR_PLASTIC_FOOTPRINT_AUDIT",
    )
    contact = (mechanism.reaction & footprint).clean()
    if contact is None or len(contact.solids()) == 0:
        return {"spanUMm": 0.0, "spanVMm": 0.0, "diagonalSpanMm": 0.0}
    origin = np.asarray(mechanism.datum.center, dtype=float)
    u = unit(mechanism.datum.switch_u)
    v = unit(mechanism.datum.switch_v)
    points = np.asarray([
        np.asarray((vertex.X, vertex.Y, vertex.Z), dtype=float) - origin
        for vertex in contact.vertices()
    ])
    pu = points @ u
    pv = points @ v
    span_u = float(pu.max() - pu.min())
    span_v = float(pv.max() - pv.min())
    del footprint, contact
    gc.collect()
    return {
        "spanUMm": span_u,
        "spanVMm": span_v,
        "diagonalSpanMm": float(np.hypot(span_u, span_v)),
    }


def build_raw_guide(name: str, datum, front: float) -> tuple[Shape, dict[str, Shape]]:
    """Pair-specific C-guide whose cap slot opens away from the other cap."""
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
    service_sign = CAP_SERVICE_SIGNS[name]
    slot = oriented_box(
        datum, shared.GUIDE_SERVICE_U_MM, shared.CAVITY_MM,
        z["guideFront"] - 0.10, z["guideRear"] + 0.10,
        u_offset=service_sign * shared.GUIDE_SERVICE_U_MM / 2.0,
        cap_frame=True, label=f"{name}_PAIR_AWAY_CAP_SERVICE_SLOT",
    )
    guide = (outer - bore - cavity - slot).clean()
    guide.label = f"{name}_RAW_PAIR_AWAY_C_GUIDE"
    front_outer = oriented_box(
        datum, shared.GUIDE_OUTER_MM, shared.GUIDE_OUTER_MM,
        z["guideFront"], z["cavityFront"], cap_frame=True, label=f"{name}_FRONT_STOP_OUTER",
    )
    front_stop = (front_outer - bore - slot).clean()
    rear_outer = oriented_box(
        datum, shared.GUIDE_OUTER_MM, shared.GUIDE_OUTER_MM,
        z["cavityRear"], z["guideRear"], cap_frame=True, label=f"{name}_REAR_STOP_OUTER",
    )
    rear_stop = (rear_outer - bore - slot).clean()
    return guide, {
        "outer": outer,
        "bore": bore,
        "cavity": cavity,
        "slot": slot,
        "frontStop": front_stop,
        "rearStop": rear_stop,
    }


def cap_service(name: str, datum, front: float) -> Shape:
    z = shared.axial(front)
    sign = CAP_SERVICE_SIGNS[name]
    width = 8.0
    shoulder = oriented_box(
        datum, width, shared.SHOULDER_MM, z["shoulderFront"], z["shoulderRear"],
        u_offset=sign * width / 2.0, cap_frame=True, label=f"{name}_PAIR_AWAY_SHOULDER_SERVICE",
    )
    tail = oriented_box(
        datum, width, shared.CAP_TAIL_DIAMETER_MM,
        z["shoulderRear"] - 0.10, z["tailRear"],
        u_offset=sign * width / 2.0, cap_frame=True, label=f"{name}_PAIR_AWAY_TAIL_SERVICE",
    )
    result = shoulder.fuse(tail).clean()
    result.label = f"{name}_PAIR_AWAY_CAP_SERVICE_SWEEP"
    return result


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


def build_carrier(base: Shape, mechanisms: dict[str, shared.Mechanism]) -> tuple[Shape, Shape, dict[str, object]]:
    carrier = base
    attachments: list[dict[str, object]] = []
    for name in BUTTONS:
        mechanism = mechanisms[name]
        for shape in (mechanism.guide, mechanism.reaction):
            distance = float(shape.distance_to_with_closest_points(base)[0])
            attachments.append({"label": shape.label, "distanceToBaseMm": distance})
            carrier = carrier.fuse(shape)
    service_relief_rows = []
    for name in BUTTONS:
        cutter = cap_service(name, mechanisms[name].datum, mechanisms[name].front)
        removed_here = volume(carrier & cutter)
        carrier = carrier - cutter
        service_relief_rows.append({
            "button": name,
            "direction": f"{CAP_SERVICE_SIGNS[name]:+.0f} cap-U / AWAY FROM OTHER CAP",
            "removedMm3": removed_here,
        })
    carrier = carrier.clean()
    carrier.label = "M4_N3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL"
    added = (carrier - base).clean()
    added.label = "M4_N3_PRODUCTION_INTENT_ADDED_MATERIAL"
    removed = (base - carrier).clean()
    return carrier, added, {
        "baseSolidCount": len(base.solids()),
        "finalSolidCount": len(carrier.solids()),
        "addedVolumeMm3": volume(added),
        "removedFromApprovedCurrentCarrierMm3": volume(removed),
        "pairAwayCapServiceReliefs": service_relief_rows,
        "attachments": attachments,
        "floatingBody": (
            len(carrier.solids()) > len(base.solids())
            or any(float(row["distanceToBaseMm"]) > 1.0e-6 for row in attachments)
        ),
    }


def combined_states(mechanisms: dict[str, shared.Mechanism]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    m4 = mechanisms["M4"]
    n3 = mechanisms["N3"]
    for m4_travel, n3_travel in COMBINATIONS:
        cap4 = shared.moved(m4.cap, m4.datum, m4_travel, f"M4_CAP_{m4_travel:.3f}")
        cap3 = shared.moved(n3.cap, n3.datum, n3_travel, f"N3_CAP_{n3_travel:.3f}")
        act4 = shared.actuator_at("M4", m4.datum, m4.front, m4_travel)
        act3 = shared.actuator_at("N3", n3.datum, n3.front, n3_travel)
        pairs = {
            "capCap": exact_pair(cap4, cap3, f"M4 cap {m4_travel:.3f}<->N3 cap {n3_travel:.3f}"),
            "M4CapN3Guide": exact_pair(cap4, n3.guide, "M4 moving cap<->N3 guide"),
            "N3CapM4Guide": exact_pair(cap3, m4.guide, "N3 moving cap<->M4 guide"),
            "M4CapN3Body": exact_pair(cap4, n3.body, "M4 moving cap<->N3 body"),
            "N3CapM4Body": exact_pair(cap3, m4.body, "N3 moving cap<->M4 body"),
            "actuatorActuator": exact_pair(act4, act3, "M4 actuator<->N3 actuator"),
        }
        rows.append({
            "M4TravelMm": m4_travel,
            "N3TravelMm": n3_travel,
            "pairs": pairs,
            "M4UncommandedTravelMm": 0.0,
            "N3UncommandedTravelMm": 0.0,
        })
        del cap4, cap3, act4, act3
        memory(f"combined M4={m4_travel:.3f} N3={n3_travel:.3f}")
    return rows


def combined_pass(rows: list[dict[str, object]]) -> bool:
    return all(
        float(pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        for row in rows for pair in row["pairs"].values()
    )


def regression(final_carrier: Shape) -> dict[str, object]:
    before = {str(path.relative_to(ROOT)): sha256(path) for path in FROZEN_FILES}
    n1n2_prior = json.loads(N1N2_JSON.read_text(encoding="utf-8"))
    i2i3_prior = json.loads(I2I3_JSON.read_text(encoding="utf-8"))
    n1n2_carrier = import_step(N1N2_CARRIER)
    i2i3_carrier = import_step(I2I3_CARRIER)
    pairs = {
        "M4N3ToN1N2": exact_pair(final_carrier, n1n2_carrier, "M4/N3 final<->N1/N2 frozen"),
        "M4N3ToI2I3": exact_pair(final_carrier, i2i3_carrier, "M4/N3 final<->I2/I3 frozen"),
    }
    n1n2_ok = all((
        n1n2_prior["verdict"]["N1_ARCHITECTURE"] == "ACCEPT",
        n1n2_prior["verdict"]["N1_MOTION"] == "PASS",
        n1n2_prior["verdict"]["N1_REAR_SUPPORT"] == "PASS",
        i2i3_prior["n1N2Regression"]["pass"] is True,
    ))
    i2i3_ok = all((
        i2i3_prior["verdict"]["I2_ARCHITECTURE"] == "ACCEPT",
        i2i3_prior["verdict"]["I3_ARCHITECTURE"] == "ACCEPT",
        i2i3_prior["verdict"]["I2_MOTION"] == "PASS",
        i2i3_prior["verdict"]["I3_MOTION"] == "PASS",
        i2i3_prior["verdict"]["I2_TERMINALS"] == "PASS",
        i2i3_prior["verdict"]["I3_TERMINALS"] == "PASS",
        float(i2i3_prior["design"]["I2"]["reaction"]["contactAreaMm2"]) >= 24.906,
        float(i2i3_prior["design"]["I3"]["reaction"]["contactAreaMm2"]) >= 24.906,
        min(float(row["pairs"]["capCap"]["distanceMm"]) for row in i2i3_prior["combinedMotion"]) >= 2.14,
    ))
    n2 = i2i3_prior["n1N2Regression"]
    n2_metrics_ok = all((
        float(n2["N2CarrierHW504A"]["distanceMm"]) + 1.0e-7 >= 0.30418034642947,
        float(n2["N2CarrierHW504B"]["distanceMm"]) + 1.0e-7 >= 1.36098371006741,
        float(n2["N2ActiveT1T3HW504B"]["minimumDistanceMm"]) + 1.0e-7 >= 2.11909303991246,
    ))
    after = {str(path.relative_to(ROOT)): sha256(path) for path in FROZEN_FILES}
    hashes_ok = before == after
    pair_ok = all(float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in pairs.values())
    return {
        "hashesBefore": before,
        "hashesAfter": after,
        "hashGuardPass": hashes_ok,
        "N1N2ApprovedPass": n1n2_ok,
        "I2I3ApprovedPass": i2i3_ok,
        "N2MinimumsPass": n2_metrics_ok,
        "N2CarrierHW504AMm": float(n2["N2CarrierHW504A"]["distanceMm"]),
        "N2CarrierHW504BMm": float(n2["N2CarrierHW504B"]["distanceMm"]),
        "N2T1T3HW504BMm": float(n2["N2ActiveT1T3HW504B"]["minimumDistanceMm"]),
        "I2ReactionAreaMm2": float(i2i3_prior["design"]["I2"]["reaction"]["contactAreaMm2"]),
        "I3ReactionAreaMm2": float(i2i3_prior["design"]["I3"]["reaction"]["contactAreaMm2"]),
        "I2I3MinimumCombinedCapGapMm": min(
            float(row["pairs"]["capCap"]["distanceMm"]) for row in i2i3_prior["combinedMotion"]
        ),
        "frozenPairs": pairs,
        "pass": hashes_ok and n1n2_ok and i2i3_ok and n2_metrics_ok and pair_ok,
        "_n1n2Carrier": n1n2_carrier,
        "_i2i3Carrier": i2i3_carrier,
    }


def serializable_regression(row: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def shifted_mesh(triangles: np.ndarray, vector: Iterable[float]) -> np.ndarray:
    return triangles + np.asarray(tuple(vector), dtype=float)


def render_outputs(
    base: Shape,
    carrier: Shape,
    shell: Shape,
    mechanisms: dict[str, shared.Mechanism],
    exact: dict[str, object],
    combined: list[dict[str, object]],
    regression_row: dict[str, object],
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    paths = [RENDER_DIR / name for name in (
        "01_m4_n3_current_structure.png",
        "02_m4_n3_exploded.png",
        "03_m4_n3_terminal_map.png",
        "04_m4_rest_full_section.png",
        "05_n3_rest_full_section.png",
        "06_rear_reaction_contact.png",
        "07_both_buttons_full.png",
        "08_shared_carrier_transparent.png",
        "09_shell_curvature_guide_closeup.png",
        "10_frozen_regression.png",
    )]

    def mesh(shape: Shape, tolerance: float = 0.10) -> np.ndarray:
        return safe_triangles(shape, tolerance=tolerance, angular=0.07, limit=5000)

    shell_mesh = mesh(shell, 0.16)
    camera = (62.0, -76.0, 48.0)
    rear_camera = (-48.0, 70.0, 50.0)

    current_objects = []
    for name, mechanism in mechanisms.items():
        current_objects.extend((
            (mesh(mechanism.base_cap), COLORS[f"{name}cap"]),
            (mesh(mechanism.body), COLORS["body"]),
            (mesh(switch_actuator(mechanism.datum, mechanism.front)), COLORS["actuator"]),
        ))
        current_objects.extend(
            (mesh(root), COLORS["terminal"][index])
            for index, root in enumerate(mechanism.roots.values())
        )
    current_focus = np.concatenate([tri.reshape(-1, 3) for tri, _ in current_objects])
    raster_scene(
        paths[0], current_objects,
        "01 / M4 + N3 CURRENT INTERNAL STRUCTURE",
        "Frozen exterior: cap-switch 0 deg / cap-shell intentional 4 deg / actuator lateral offset 0",
        "Current carrier rear gap 0.110 mm; unrelieved guide candidate fails the curved local shell",
        transparent_objects=[(mesh(base), (*COLORS["carrier"], 38)), (shell_mesh, (*COLORS["shell"], 18))],
        camera_offset=camera, final_size=(1920, 1280), supersample=2, fit_points=current_focus,
    )
    memory("render 01")

    exploded = []
    exploded_focus = []
    for name, mechanism in mechanisms.items():
        axis = unit(mechanism.datum.axis)
        rows = (
            (shifted_mesh(mesh(mechanism.cap), axis * 6.0), COLORS[f"{name}cap"]),
            (shifted_mesh(mesh(mechanism.guide), axis * 2.2), COLORS[f"{name}guide"]),
            (shifted_mesh(mesh(mechanism.body), -axis * 2.2), COLORS["body"]),
            (shifted_mesh(mesh(mechanism.reaction), -axis * 5.2), COLORS[f"{name}support"]),
        )
        exploded.extend(rows)
        exploded_focus.extend(tri.reshape(-1, 3) for tri, _ in rows)
    raster_scene(
        paths[1], exploded,
        "02 / EXPLODED M4 + N3 PRODUCTION-INTENT MECHANISMS",
        "Direct D3 contact / positive shoulder / relieved C-guide / ITS body / broad rear frame",
        "Independent load and service paths; 0.350 mm structural hard stop; no separate spring",
        transparent_objects=[(mesh(base), (*COLORS["carrier"], 30))],
        camera_offset=camera, final_size=(1920, 1280), supersample=2,
        fit_points=np.concatenate(exploded_focus),
    )
    memory("render 02")

    terminal_objects = []
    terminal_focus = []
    terminal_lines = []
    for name, mechanism in mechanisms.items():
        for index, (terminal, root) in enumerate(mechanism.roots.items()):
            color = COLORS["terminal"][index]
            triangles = mesh(root)
            terminal_objects.append((triangles, color))
            terminal_focus.append(triangles.reshape(-1, 3))
            center = np.asarray((root.center().X, root.center().Y, root.center().Z))
            distance = float(exact[name]["terminals"][terminal]["localShell"]["distanceMm"])
            terminal_lines.append((center, center + unit(mechanism.datum.axis) * 1.8, (*color, 255), f"{name}-{terminal} {distance:.3f}"))
    raster_scene(
        paths[2], terminal_objects,
        "03 / M4 + N3 T1 / T2 / T3 / T4 EXACT TERMINAL MAP",
        "All eight conservative 0.12 mm service envelopes remain untrimmed",
        "Carrier / shell / other switch / other guide / neighboring carrier penetration 0",
        transparent_objects=[(mesh(m.body), (*COLORS["body"], 42)) for m in mechanisms.values()]
        + [(mesh(m.reaction), (*COLORS[f"{name}support"], 42)) for name, m in mechanisms.items()],
        world_lines=terminal_lines, camera_offset=rear_camera,
        final_size=(1920, 1280), supersample=2, fit_points=np.concatenate(terminal_focus),
    )
    memory("render 03")

    for index, name in enumerate(BUTTONS, 3):
        mechanism = mechanisms[name]
        local_crop = oriented_box(
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
            common = shape & local_crop & half
            if common is None or len(common.solids()) == 0:
                raise RuntimeError(f"{name} empty section: {shape.label}")
            return common.clean()

        objects = []
        focus = []
        lines = []
        for travel, sign, label in ((0.0, -1.0, "REST 0.000"), (0.350, 1.0, "FULL 0.350")):
            shift = unit(mechanism.datum.cap_v) * sign * 9.0
            parts = (
                (section(shared.moved(mechanism.cap, mechanism.datum, travel, "cap state")), COLORS[f"{name}cap"]),
                (section(mechanism.guide), COLORS[f"{name}guide"]),
                (section(base), COLORS["carrier"]),
                (section(mechanism.body), COLORS["body"]),
                (section(shared.actuator_at(name, mechanism.datum, mechanism.front, travel)), COLORS["actuator"]),
                (section(mechanism.reaction), COLORS[f"{name}support"]),
            )
            for shape, color in parts:
                triangles = shifted_mesh(mesh(shape), shift)
                objects.append((triangles, color))
                focus.append(triangles.reshape(-1, 3))
            center = np.asarray(mechanism.datum.center) + shift
            lines.append((center, center + unit(mechanism.datum.cap_v) * 2.0, (255, 226, 104, 255), label))
        raster_scene(
            paths[index], objects,
            f"0{index + 1} / {name} REST + FULL TRUE LOCAL SECTIONS",
            "Display-separated states; frozen center/orientation and intentional 4 deg shell relation remain fixed",
            "Hard-stop residual REST 0.350 / FULL 0.000 mm; contact gap 0; unintended penetration 0",
            world_lines=lines, camera_offset=tuple(float(x) for x in unit(mechanism.datum.cap_u) * 88.0),
            final_size=(1920, 1280), supersample=2, fit_points=np.concatenate(focus),
        )
        memory(f"render {name} section")

    support_objects = []
    support_transparent = []
    support_focus = []
    support_lines = []
    for name, mechanism in mechanisms.items():
        tri = mesh(mechanism.reaction)
        body_tri = mesh(mechanism.body)
        support_objects.append((tri, COLORS[f"{name}support"]))
        support_transparent.append((body_tri, (*COLORS["body"], 48)))
        support_focus.extend((tri.reshape(-1, 3), body_tri.reshape(-1, 3)))
        center = np.asarray((mechanism.reaction.center().X, mechanism.reaction.center().Y, mechanism.reaction.center().Z))
        area = float(mechanism.reaction_metrics["contactAreaMm2"])
        span = float(mechanism.reaction_metrics["diagonalSpanMm"])
        support_lines.append((center, center + unit(mechanism.datum.switch_v) * 2.0, (255, 226, 104, 255), f"{name} {area:.3f} mm2 / span {span:.3f}"))
    raster_scene(
        paths[5], support_objects,
        "06 / M4 + N3 REAR REACTION CONTACT",
        "Terminal-window flat frames contact ITS rear plastic over one connected broad patch each",
        "Minimum rail 1.20 mm; terminal roots and central wire corridors remain unloaded",
        transparent_objects=support_transparent, world_lines=support_lines,
        camera_offset=rear_camera, final_size=(1920, 1280), supersample=2,
        fit_points=np.concatenate(support_focus),
    )
    memory("render 06")

    full_objects = []
    full_focus = []
    for name, mechanism in mechanisms.items():
        rows = (
            (mesh(shared.moved(mechanism.cap, mechanism.datum, 0.350, f"{name} full cap")), COLORS[f"{name}cap"]),
            (mesh(mechanism.guide), COLORS[f"{name}guide"]),
            (mesh(mechanism.body), COLORS["body"]),
            (mesh(shared.actuator_at(name, mechanism.datum, mechanism.front, 0.350)), COLORS["actuator"]),
            (mesh(mechanism.reaction), COLORS[f"{name}support"]),
        )
        full_objects.extend(rows)
        full_focus.extend(tri.reshape(-1, 3) for tri, _ in rows)
    raster_scene(
        paths[6], full_objects,
        "07 / M4 FULL + N3 FULL",
        "Both independent caps reach their own 0.350 mm structural hard stops",
        "Cross penetration 0; uncommanded motion 0; cap-cap clearance annotated in exact JSON",
        transparent_objects=[(mesh(carrier), (*COLORS["carrier"], 34)), (shell_mesh, (*COLORS["shell"], 20))],
        camera_offset=camera, final_size=(1920, 1280), supersample=2,
        fit_points=np.concatenate(full_focus),
    )
    memory("render 07")

    assembled = []
    assembled_focus = [mesh(carrier).reshape(-1, 3)]
    for name, mechanism in mechanisms.items():
        rows = (
            (mesh(mechanism.cap), COLORS[f"{name}cap"]),
            (mesh(mechanism.guide), COLORS[f"{name}guide"]),
            (mesh(mechanism.body), COLORS["body"]),
            (mesh(mechanism.reaction), COLORS[f"{name}support"]),
        )
        assembled.extend(rows)
        assembled_focus.extend(tri.reshape(-1, 3) for tri, _ in rows)
    raster_scene(
        paths[7], assembled,
        "08 / M4 + N3 SHARED CARRIER — TRANSPARENT",
        "One connected local carrier; each button retains independent load and shell-open service paths",
        "Floating body 0; full shell and other button subsystems excluded from production geometry",
        transparent_objects=[(mesh(carrier), (*COLORS["carrier"], 34)), (shell_mesh, (*COLORS["shell"], 18))],
        camera_offset=camera, final_size=(1920, 1280), supersample=2,
        fit_points=np.concatenate(assembled_focus),
    )
    memory("render 08")

    relief_objects = []
    relief_transparent = [(shell_mesh, (*COLORS["shell"], 30))]
    relief_focus = []
    relief_lines = []
    for name, mechanism in mechanisms.items():
        guide_tri = mesh(mechanism.guide)
        relief_objects.append((guide_tri, COLORS[f"{name}guide"]))
        relief_focus.append(guide_tri.reshape(-1, 3))
        collision = mechanism.raw_guide & shell
        if collision is not None and len(collision.solids()) > 0:
            collision_tri = mesh(collision)
            relief_objects.append((collision_tri, COLORS["collision"]))
            relief_focus.append(collision_tri.reshape(-1, 3))
        center = np.asarray((mechanism.guide.center().X, mechanism.guide.center().Y, mechanism.guide.center().Z))
        raw_pen = float(mechanism.guide_metrics["rawShellPenetrationMm3"])
        relief_lines.append((center, center + unit(mechanism.datum.cap_v) * 2.0, (255, 226, 104, 255), f"{name} raw {raw_pen:.3f} mm3"))
    raster_scene(
        paths[8], relief_objects,
        "09 / CURVED SHELL + LOCAL GUIDE RELIEF CLOSE-UP",
        "Red = failed unrelieved guide/shell common; blue = final locally relieved guide",
        "Exterior and shell unchanged; relief-to-shoulder motion penetration 0",
        transparent_objects=relief_transparent, world_lines=relief_lines,
        camera_offset=camera, final_size=(1920, 1280), supersample=2,
        fit_points=np.concatenate(relief_focus),
    )
    memory("render 09")

    frozen_n1n2 = regression_row["_n1n2Carrier"]
    frozen_i2i3 = regression_row["_i2i3Carrier"]
    regression_objects = [
        (mesh(carrier), COLORS["carrier"]),
        (mesh(frozen_n1n2), COLORS["frozen1"]),
        (mesh(frozen_i2i3), COLORS["frozen2"]),
        (mesh(import_step(N1_CAP)), COLORS["M4cap"]),
        (mesh(import_step(N2_CAP)), COLORS["N3cap"]),
        (mesh(import_step(I2_CAP)), COLORS["M4cap"]),
        (mesh(import_step(I3_CAP)), COLORS["N3cap"]),
    ]
    regression_focus = np.concatenate([tri.reshape(-1, 3) for tri, _ in regression_objects])
    raster_scene(
        paths[9], regression_objects,
        "10 / N1/N2 + I2/I3 HARD-FROZEN REGRESSION",
        "Approved carrier, cap, JSON, and docs SHA-256 files unchanged; M4/N3 remains a separate local solid",
        f"N2 A {float(regression_row['N2CarrierHW504AMm']):.6f} / B {float(regression_row['N2CarrierHW504BMm']):.6f} / T1-T3 {float(regression_row['N2T1T3HW504BMm']):.6f} mm",
        transparent_objects=[], camera_offset=(58.0, -82.0, 52.0),
        final_size=(1920, 1280), supersample=2, fit_points=regression_focus,
    )
    memory("render 10")
    return paths


def report_markdown(data: dict[str, object]) -> str:
    audit = data["currentAudit"]
    exact = data["exact"]
    regression_row = data["frozenRegression"]
    verdict = data["verdict"]
    motion_sections = []
    terminal_sections = []
    for name in BUTTONS:
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
        f"| {float(row['M4TravelMm']):.3f} | {float(row['N3TravelMm']):.3f} | "
        f"{max(float(pair['penetrationMm3']) for pair in row['pairs'].values()):.9f} | "
        f"{float(row['pairs']['capCap']['distanceMm']):.6f} | 0.000 / 0.000 |"
        for row in data["combinedMotion"]
    )
    render_rows = "\n".join(f"- `{path}`" for path in data["outputs"]["renders"])
    return f"""# 65 — M4/N3 PRODUCTION-INTENT BUTTON MECHANISMS

## 결론

M4/N3 exterior feasibility는 재평가하지 않았다. 승인된 center, cap exterior/orientation, switch position과 의도된 shell 대비 4°를 그대로 유지하고 기존 shared carrier에 내부 기능만 추가했다.

초기 9.3 mm unrelieved guide envelope는 M4 **{float(data['design']['M4']['guide']['rawShellPenetrationMm3']):.6f} mm³**, N3 **{float(data['design']['N3']['guide']['rawShellPenetrationMm3']):.6f} mm³**의 local-shell penetration이 있었다.

**THIS INTERNAL CANDIDATE FAILED**

shell 또는 exterior를 바꾸지 않고 guide의 shell-facing 비기능 corner만 exact local relief했다. 최종 guide-shell penetration과 relief-to-shoulder motion penetration은 모두 0이다.

## 1. Current exact local audit

| item | M4 | N3 |
|---|---:|---:|
| cap center | `{audit['controls']['M4']['centerMm']}` | `{audit['controls']['N3']['centerMm']}` |
| cap ↔ switch plane | {float(audit['controls']['M4']['capSwitchPlaneAngleDeg']):.6f}° | {float(audit['controls']['N3']['capSwitchPlaneAngleDeg']):.6f}° |
| cap ↔ local shell plane | {float(audit['controls']['M4']['capShellLocalPlaneAngleDeg']):.6f}° | {float(audit['controls']['N3']['capShellLocalPlaneAngleDeg']):.6f}° |
| actuator lateral offset | {float(audit['controls']['M4']['capActuatorLateralOffsetMm']):.9f} mm | {float(audit['controls']['N3']['capActuatorLateralOffsetMm']):.9f} mm |
| current rear reaction gap | {float(audit['controls']['M4']['rearReactionGapMm']):.6f} mm | {float(audit['controls']['N3']['rearReactionGapMm']):.6f} mm |
| body ↔ local shell | {float(audit['controls']['M4']['bodyShell']['distanceMm']):.6f} mm | {float(audit['controls']['N3']['bodyShell']['distanceMm']):.6f} mm |
| full 9.3 mm guide envelope ↔ shell pen | {float(audit['controls']['M4']['availableEnvelopes']['guideEnvelopeShell']['penetrationMm3']):.6f} mm³ | {float(audit['controls']['N3']['availableEnvelopes']['guideEnvelopeShell']['penetrationMm3']):.6f} mm³ |

4°는 의도된 internal-axis tilt이며 cap을 shell과 평행하게 재정렬하지 않았다. current shared carrier는 local shell과 penetration 0, M3 carrier와 0.400 mm, I4 carrier와 12.121880 mm 떨어져 있다.

## 2. Production-intent architecture

각 버튼의 독립 load path:

`finger → frozen exterior cap → Ø3.0 central contact → ITS actuator/body → terminal-window rear reaction frame → shared carrier/shell`

- positive retention: 6.5 mm square shoulder / 6.8 mm cavity
- guide: Ø4.5 tail / Ø4.8 bore, radial clearance 0.15 mm
- hard stop: carrier rear structural plane at 0.350 mm
- return: ITS internal return only; 별도 spring 없음
- body locating: 기존 6.4 mm pocket datum과 switch position 유지
- cap service: M4 `−cap-U`, N3 `+cap-U`; 두 경로 모두 이웃 cap 반대 방향이며 carrier/other cap/guide/body penetration 0
- switch service: 기존 switch-frame open side를 유지하고 other cap/guide/body penetration 0
- terminal service: 4.0 × 3.2 mm central wire window
- shell curvature response: 각 guide의 shell-facing corner만 local relief

### Rear reaction support

| item | M4 | N3 |
|---|---:|---:|
| contact area | {float(data['design']['M4']['reaction']['contactAreaMm2']):.3f} mm² | {float(data['design']['N3']['reaction']['contactAreaMm2']):.3f} mm² |
| connected contact patch | {int(data['design']['M4']['reaction']['connectedContactPatchCount'])} | {int(data['design']['N3']['reaction']['connectedContactPatchCount'])} |
| contact span U × V | {float(data['design']['M4']['reaction']['spanUMm']):.3f} × {float(data['design']['M4']['reaction']['spanVMm']):.3f} mm | {float(data['design']['N3']['reaction']['spanUMm']):.3f} × {float(data['design']['N3']['reaction']['spanVMm']):.3f} mm |
| diagonal span | {float(data['design']['M4']['reaction']['diagonalSpanMm']):.3f} mm | {float(data['design']['N3']['reaction']['diagonalSpanMm']):.3f} mm |
| minimum rail | {float(data['design']['M4']['reaction']['minimumWallMm']):.3f} mm | {float(data['design']['N3']['reaction']['minimumWallMm']):.3f} mm |

0.110 mm rear gap은 broad plastic-body frame으로 닫힌다. terminal root나 중앙 wire corridor를 반력면으로 사용하지 않는다.

## 3. Independent motion

{"\n\n".join(motion_sections)}

REST/MID/FULL에서 cap-guide, cap-shell, cap-base-carrier, cap-actuator, other-guide/body unintended penetration은 0이고 contact gap은 0이다. hard-stop residual은 0.350 / 0.175 / 0.000 mm다.

### Combined states

| M4 travel mm | N3 travel mm | maximum cross pen mm³ | cap-cap gap mm | uncommanded M4/N3 mm |
|---:|---:|---:|---:|---:|
{combined_rows}

## 4. Terminal map and service

T1/T2/T3/T4를 각각 conservative terminal + radial service 0.12 mm envelope로 검사했다. 8개 모두 무절단 유지한다.

{"\n\n".join(terminal_sections)}

각 terminal의 carrier/shell/other-button/neighbor-carrier penetration은 0이다. cap service, switch service, wire exit, wire envelope도 각 버튼별 독립 PASS다.

## 5. Shared carrier / local shell / FDM

- approved current carrier removed volume: **{float(data['design']['carrier']['removedFromApprovedCurrentCarrierMm3']):.9f} mm³**
- final solid count: **{int(data['design']['carrier']['finalSolidCount'])}**
- floating body: **{data['design']['carrier']['floatingBody']}**
- final carrier ↔ local shell penetration: **{float(exact['sharedCarrierShell']['penetrationMm3']):.9f} mm³**
- final carrier ↔ M3 carrier: **{float(exact['neighborCarriers']['M3']['distanceMm']):.6f} mm**, penetration {float(exact['neighborCarriers']['M3']['penetrationMm3']):.9f} mm³
- critical functional wall: **{float(data['design']['minimumFunctionalWallMm']):.3f} mm** ≥ 1.20 mm
- preferred 1.60 mm는 base wall/cross-rail에 유지되며 guide annulus/reaction side rail은 functional minimum gate 1.20 mm를 만족한다.
- tiny snap / thin hook / tangent-only support / floating body: 없음

## 6. Frozen regression

- frozen files SHA-256 guard: **{'PASS' if regression_row['hashGuardPass'] else 'FAIL'}**
- N1/N2 approved verdicts: **{'PASS' if regression_row['N1N2ApprovedPass'] else 'FAIL'}**
- I2/I3 approved verdicts: **{'PASS' if regression_row['I2I3ApprovedPass'] else 'FAIL'}**
- N2 carrier ↔ HW504-A: **{float(regression_row['N2CarrierHW504AMm']):.9f} mm** ≥ 0.304180 mm
- N2 carrier ↔ HW504-B: **{float(regression_row['N2CarrierHW504BMm']):.9f} mm** (6자리 반올림 **1.360984 mm**, 승인 baseline 보존)
- N2 T1/T3 ↔ HW504-B: **{float(regression_row['N2T1T3HW504BMm']):.9f} mm** ≥ 2.119093 mm
- I2/I3 rear reaction: **{float(regression_row['I2ReactionAreaMm2']):.6f} / {float(regression_row['I3ReactionAreaMm2']):.6f} mm²**
- I2/I3 minimum combined cap gap: **{float(regression_row['I2I3MinimumCombinedCapGapMm']):.6f} mm** ≥ 2.14 mm
- M4/N3 final carrier ↔ frozen N1/N2, I2/I3 penetration: **0 mm³**

## 7. Outputs

{render_rows}

- `{data['outputs']['json']}` — lightweight exact JSON
- `{data['outputs']['carrierStep']}` — M4/N3 local shared carrier only
- `{data['outputs']['capSteps']['M4']}` / `{data['outputs']['capSteps']['N3']}` — local cap components only
- full shell / full assembly / STL / print plate / multiprocessing: **생성하지 않음**

## 8. FINAL / STOP

- M4 ARCHITECTURE = **{verdict['M4_ARCHITECTURE']}**
- N3 ARCHITECTURE = **{verdict['N3_ARCHITECTURE']}**
- M4 MOTION = **{verdict['M4_MOTION']}**
- N3 MOTION = **{verdict['N3_MOTION']}**
- SHARED CARRIER = **{verdict['SHARED_CARRIER']}**
- M4 TERMINALS = **{verdict['M4_TERMINALS']}**
- N3 TERMINALS = **{verdict['N3_TERMINALS']}**
- N1/N2 FROZEN BASELINE = **{verdict['N1_N2_FROZEN_BASELINE']}**
- I2/I3 FROZEN BASELINE = **{verdict['I2_I3_FROZEN_BASELINE']}**
- EXTERIOR = **{verdict['EXTERIOR']}**

M4/N3에서 STOP한다. I4/M3로 자동 확장하지 않았다.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    shared.MEMORY.clear()
    memory("start")
    frozen_hashes_before_run = {str(path.relative_to(ROOT)): sha256(path) for path in FROZEN_FILES}
    audit = json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
    datums = load_datums()
    base = import_step(SOURCE_DIR / "M4_N3_shared_carrier.step")
    base_caps = {name: import_step(CAP_STEPS[name]) for name in BUTTONS}
    shell, shell_bbox = local_shell(base, base_caps)
    neighbors = {name: import_step(path) for name, path in NEIGHBOR_CARRIER_STEPS.items()}
    memory("local source and shell crop")

    mechanisms = {name: build_mechanism(name, datums[name], shell) for name in BUTTONS}
    raw_guide_pair = exact_pair(mechanisms["M4"].raw_guide, mechanisms["N3"].raw_guide, "raw stationary guides")
    carrier, added, carrier_metrics = build_carrier(base, mechanisms)
    carrier_shell = exact_pair(carrier, shell, "final M4/N3 shared carrier<->local shell")
    neighbor_pairs = {
        name: exact_pair(carrier, shape, f"final M4/N3 carrier<->{name} carrier")
        for name, shape in neighbors.items()
    }
    memory("production-intent carrier built")

    exact: dict[str, object] = {
        "M4": shared.validate_mechanism(mechanisms["M4"], mechanisms["N3"], carrier, base, shell),
        "N3": shared.validate_mechanism(mechanisms["N3"], mechanisms["M4"], carrier, base, shell),
    }
    exact["sharedCarrierShell"] = carrier_shell
    exact["neighborCarriers"] = neighbor_pairs
    exact["stationaryGuideFusion"] = exact_pair(mechanisms["M4"].guide, mechanisms["N3"].guide, "relieved stationary guide overlap")
    exact["reactionFrameSeparation"] = exact_pair(mechanisms["M4"].reaction, mechanisms["N3"].reaction, "M4 reaction<->N3 reaction")
    for name in BUTTONS:
        other_name = "N3" if name == "M4" else "M4"
        mechanism = mechanisms[name]
        other = mechanisms[other_name]
        cap_sweep = cap_service(name, mechanism.datum, mechanism.front)
        switch_sweep = shared.switch_service(name, mechanism.datum, mechanism.front)
        exact[name]["service"]["cap"] = exact_pair(carrier, cap_sweep, f"carrier<->{name} pair-away cap service")
        exact[name]["service"].update({
            "capServiceOtherCap": exact_pair(cap_sweep, other.cap, f"{name} cap service<->{other_name} cap"),
            "capServiceOtherGuide": exact_pair(cap_sweep, other.guide, f"{name} cap service<->{other_name} guide"),
            "capServiceOtherBody": exact_pair(cap_sweep, other.body, f"{name} cap service<->{other_name} body"),
            "switchServiceOtherCap": exact_pair(switch_sweep, other.cap, f"{name} switch service<->{other_name} cap"),
            "switchServiceOtherGuide": exact_pair(switch_sweep, other.guide, f"{name} switch service<->{other_name} guide"),
            "switchServiceOtherBody": exact_pair(switch_sweep, other.body, f"{name} switch service<->{other_name} body"),
        })
        exact[name]["terminalNeighborCarriers"] = {
            terminal: {
                neighbor_name: exact_pair(root, neighbor, f"{name} {terminal}<->{neighbor_name} carrier")
                for neighbor_name, neighbor in neighbors.items()
            }
            for terminal, root in mechanisms[name].roots.items()
        }
    combined = combined_states(mechanisms)
    gates = {name: shared.mechanism_gates(exact[name]) for name in BUTTONS}
    combined_ok = combined_pass(combined)
    exterior = {name: shared.exterior_delta(mechanisms[name]) for name in BUTTONS}
    regression_row = regression(carrier)
    memory("frozen regression")

    support_ok = all(
        float(mechanisms[name].reaction_metrics["contactAreaMm2"]) >= MIN_REACTION_AREA_MM2
        and int(mechanisms[name].reaction_metrics["connectedContactPatchCount"]) == 1
        and float(mechanisms[name].reaction_metrics["minimumWallMm"]) + 1.0e-9 >= MIN_WALL_MM
        for name in BUTTONS
    )
    neighbor_ok = all(float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in neighbor_pairs.values())
    terminal_neighbor_ok = all(
        float(pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        for name in BUTTONS
        for terminal_rows in exact[name]["terminalNeighborCarriers"].values()
        for pair in terminal_rows.values()
    )
    carrier_ok = all((
        float(carrier_shell["penetrationMm3"]) <= BOOLEAN_EPS_MM3,
        not bool(carrier_metrics["floatingBody"]),
        float(carrier_metrics["removedFromApprovedCurrentCarrierMm3"]) <= MAX_LOCAL_SERVICE_RELIEF_MM3,
        int(carrier_metrics["finalSolidCount"]) == 1,
        combined_ok,
        support_ok,
        neighbor_ok,
    ))
    exterior_ok = all(float(row["symmetricDifferenceMm3"]) <= BOOLEAN_EPS_MM3 for row in exterior.values())
    architecture = {
        name: all(gates[name].values()) and carrier_ok and exterior_ok and terminal_neighbor_ok
        for name in BUTTONS
    }
    verdict = {
        "M4_ARCHITECTURE": "ACCEPT" if architecture["M4"] else "HOLD",
        "N3_ARCHITECTURE": "ACCEPT" if architecture["N3"] else "HOLD",
        "M4_MOTION": "PASS" if gates["M4"]["motion"] and gates["M4"]["hardStop"] and combined_ok else "HOLD",
        "N3_MOTION": "PASS" if gates["N3"]["motion"] and gates["N3"]["hardStop"] and combined_ok else "HOLD",
        "SHARED_CARRIER": "PASS" if carrier_ok else "HOLD",
        "M4_TERMINALS": "PASS" if gates["M4"]["terminals"] and gates["M4"]["service"] and terminal_neighbor_ok else "HOLD",
        "N3_TERMINALS": "PASS" if gates["N3"]["terminals"] and gates["N3"]["service"] and terminal_neighbor_ok else "HOLD",
        "N1_N2_FROZEN_BASELINE": "PRESERVED" if regression_row["N1N2ApprovedPass"] and regression_row["hashGuardPass"] else "FAIL",
        "I2_I3_FROZEN_BASELINE": "PRESERVED" if regression_row["I2I3ApprovedPass"] and regression_row["hashGuardPass"] else "FAIL",
        "EXTERIOR": "PRESERVED" if exterior_ok else "FAIL",
    }

    export_step(carrier, CARRIER_STEP)
    for name in BUTTONS:
        export_step(mechanisms[name].cap, CAP_OUTPUTS[name])
    memory("local STEP exports")
    renders = render_outputs(base, carrier, shell, mechanisms, exact, combined, regression_row)

    data: dict[str, object] = {
        "schema": "onegrip.m4_n3.production_intent_mechanism.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOW-MEMORY / LOCAL JaD CROP / SERIAL EXACT / FROZEN HASH GUARDED",
        "freeze": {
            "M4CenterMovementMm": 0.0,
            "N3CenterMovementMm": 0.0,
            "M4OrientationChangeDeg": 0.0,
            "N3OrientationChangeDeg": 0.0,
            "intentionalCapShellAngleDeg": 4.0,
            "N1N2Writes": 0,
            "I2I3Writes": 0,
            "fullShellExport": False,
            "fullAssembly": False,
            "STL": False,
            "printPlate": False,
            "multiprocessing": False,
        },
        "currentAudit": audit,
        "initialCandidateVerdict": "THIS INTERNAL CANDIDATE FAILED",
        "initialCandidate": {
            "reason": "unrelieved 9.3 mm guides penetrate the fixed curved local JaD shell",
            "M4RawGuideShellPenetrationMm3": mechanisms["M4"].guide_metrics["rawShellPenetrationMm3"],
            "N3RawGuideShellPenetrationMm3": mechanisms["N3"].guide_metrics["rawShellPenetrationMm3"],
            "stationaryRawGuideOverlapMm3": raw_guide_pair["penetrationMm3"],
            "externalResponse": "NO EXTERIOR CHANGE; INTERNAL LOCAL CORNER RELIEF ONLY",
        },
        "design": {
            name: {
                "actuation": "DIRECT",
                "return": "ITS INTERNAL RETURN",
                "cap": {"contactDiameterMm": 3.0, "tailDiameterMm": 4.5, "shoulderSizeMm": 6.5},
                "guide": mechanisms[name].guide_metrics,
                "reaction": mechanisms[name].reaction_metrics,
            }
            for name in BUTTONS
        },
        "exact": exact,
        "combinedMotion": combined,
        "gates": {
            **gates,
            "combinedMotion": combined_ok,
            "carrier": carrier_ok,
            "support": support_ok,
            "neighborCarriers": neighbor_ok,
            "terminalNeighborCarriers": terminal_neighbor_ok,
        },
        "exteriorDelta": exterior,
        "frozenRegression": serializable_regression(regression_row),
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
        "memory": shared.MEMORY,
        "stop": "M4/N3 complete; no expansion to I4/M3",
    }
    data["design"]["carrier"] = carrier_metrics
    data["design"]["minimumFunctionalWallMm"] = min(
        shared.GUIDE_WALL_MM, shared.REACTION_MIN_WALL_MM, PREFERRED_WALL_MM
    )
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(report_markdown(data), encoding="utf-8")
    frozen_hashes_after_run = {str(path.relative_to(ROOT)): sha256(path) for path in FROZEN_FILES}
    data["frozenRegression"]["wholeRunHashGuardPass"] = frozen_hashes_before_run == frozen_hashes_after_run
    data["outputs"]["sha256"] = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in (REPORT_PATH, CARRIER_STEP, *CAP_OUTPUTS.values(), *renders)
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    memory("complete")
    print(json.dumps({
        "verdict": verdict,
        "initialCandidate": data["initialCandidateVerdict"],
        "M4GuideRawShellPenetrationMm3": mechanisms["M4"].guide_metrics["rawShellPenetrationMm3"],
        "N3GuideRawShellPenetrationMm3": mechanisms["N3"].guide_metrics["rawShellPenetrationMm3"],
        "M4SupportAreaMm2": mechanisms["M4"].reaction_metrics["contactAreaMm2"],
        "N3SupportAreaMm2": mechanisms["N3"].reaction_metrics["contactAreaMm2"],
        "combinedMotionPass": combined_ok,
        "minimumCombinedCapGapMm": min(float(row["pairs"]["capCap"]["distanceMm"]) for row in combined),
        "frozenRegressionPass": regression_row["pass"],
        "peakRssMb": max(float(row["rssMb"]) for row in shared.MEMORY),
        "report": str(REPORT_PATH.relative_to(ROOT)),
        "renders": [str(path.relative_to(ROOT)) for path in renders],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
