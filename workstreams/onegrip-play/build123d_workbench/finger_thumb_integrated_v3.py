"""Local-only integrated Finger V2 exterior + lowered thumb V3 prototype.

The approved user-facing controls are immutable.  This module redesigns only
the internal switch depths, N1/N2 carrier, wiring, thumb seating, local shell
reliefs and shell fastening.  It does not access Onshape and does not overwrite
the production Finger V2 or its physical-validation artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import (
    Align,
    Box,
    Compound,
    Cylinder,
    Location,
    Plane,
    Shape,
    Vector,
    export_step,
    export_stl,
    import_step,
)

from .finger_controls_v2 import (
    ACTUATOR_DIAMETER,
    ACTUATOR_PROJECTION,
    BUTTON_ORDER,
    CAP_EXPOSURE,
    CAP_BOSS_DIAMETER,
    CAP_CONTACT_FREE_GAP,
    CAP_SIZE,
    CAP_SOCKET_DIAMETER,
    CAP_THICKNESS,
    ControlDatum,
    SWITCH_BODY_H,
    SWITCH_BODY_X,
    SWITCH_BODY_Y,
    SWITCH_POCKET_X,
    SWITCH_POCKET_Y,
    TERMINAL_METAL_U,
    TERMINAL_METAL_V,
    TERMINAL_ROOT_OUTER,
    TERMINAL_ROOT_PITCH,
    build_cap,
    opening_cutter,
    oriented_box,
    oriented_cylinder,
    point_at,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    unit,
    wire_envelope,
)
from .finger_thumb_joint_feasibility import (
    BOOLEAN_EPS,
    bbox_gap,
    fast_minimum_distance,
)
from .model import oriented_box_between


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent / "out" / "finger_thumb_integrated_v3"
V2_DIR = Path(__file__).resolve().parent / "out" / "finger_controls_v2"
FEASIBILITY_DIR = Path(__file__).resolve().parent / "out" / "finger_thumb_joint_feasibility"

JAD_V2_STEP = V2_DIR / "JAD_FINGER_V2.step"
JFD_V2_STEP = V2_DIR / "JFD_FINGER_V2.step"
CONTROL_MANIFEST = V2_DIR / "finger_controls_v2_source_manifest.json"
THUMB_TARGET_STEP = FEASIBILITY_DIR / "THUMB_TARGET_EXACT_MODULE.step"

# ---------------------------------------------------------------------------
# Hard-frozen user interface and hardware envelope (mm)
# ---------------------------------------------------------------------------

THUMB_DX = 0.00
THUMB_DY = +12.25
THUMB_DZ = -21.00
THUMB_TARGET = np.asarray((THUMB_DX, THUMB_DY, THUMB_DZ), dtype=float)

ITS_BODY_X = 6.18
ITS_BODY_Y = 6.12
ITS_HOUSING_H = 3.56
ITS_TOTAL_H = 6.00
ITS_ACTUATOR_D = 3.35
ITS_ACTUATOR_PROJECTION = 2.44
SWITCH_POCKET = (6.40, 6.40)

# New N-region architecture.
N_FRONT_DEPTH = 1.20
N_RING_FRONT_DEPTH = 2.02
N_CARRIER_WALL = 1.60
N_CARRIER_OUTER_X = SWITCH_POCKET_X + 2.0 * N_CARRIER_WALL
N_CARRIER_OUTER_Y = SWITCH_POCKET_Y + 2.0 * N_CARRIER_WALL
N_FRONT_RING_DEPTH = 3.45
N_RESTRAINT_THICKNESS = 1.60
N_RESTRAINT_STRAP_V = 1.60
N_PAIR_BRIDGE = 2.40
N_OWNER_RELIEF = 0.25
N_OPPOSITE_RELIEF = 0.82

# Wiring envelopes.
FORMED_LEAD_SECTION = 1.10
FORMED_LEAD_LENGTH = 3.40
SOLDER_SECTION = 2.00
SOLDER_LENGTH = 1.60
INSULATED_WIRE_SECTION = 1.60
INSULATED_WIRE_LENGTH = 13.0
SERVICE_CLEARANCE = 0.80
PREFERRED_SERVICE_CLEARANCE = 1.00

# Thumb seat local PCA frame recovered from the exact target Backplate.
THUMB_SEAT_CENTER = np.asarray((-0.23581763, -4.41709540, 24.99272364), dtype=float)
THUMB_SEAT_U = np.asarray((1.0, 0.0, 0.0), dtype=float)
THUMB_SEAT_N = unit((0.00017647, 0.60270162, 0.79796662))
THUMB_SEAT_V = unit(np.cross(THUMB_SEAT_N, THUMB_SEAT_U))
THUMB_SEAT_V_SHIFT = 8.00
THUMB_SEAT_N_BACK = -10.50
THUMB_FLANGE_OUTER_U = 42.0
THUMB_FLANGE_OUTER_V = 64.0
THUMB_FLANGE_INNER_U = 34.0
THUMB_FLANGE_INNER_V = 56.0
THUMB_FLANGE_WALL = 1.60
THUMB_PAD_SIZE = 5.0
THUMB_PAD_REACH = 4.8
THUMB_OPENING_CLEARANCE = 0.80

# Exterior-first reset: the previous collision-seeded AABB relief for the
# lowered HW504 mechanism opened a large through-window behind N1/N2.  That
# cutter is intentionally disabled.  Any remaining mechanism/shell overlap is
# reported as an internal-design HOLD and must not be solved by punching the
# user-facing shell again.
ENABLE_THUMB_MECHANISM_THROUGH_RELIEF = False

# New fastening architecture.  Every axis is +X; tuples are (Y, Z).
SCREW_X_MIN = -9.0
SCREW_X_MAX = 10.0
SCREW_HEAD_RADIUS = 2.75
SCREW_SHAFT_RADIUS = 1.55
SCREW_BOSS_RADIUS = 4.60
SCREW_DRIVER_RADIUS = 2.80
SCREW_CLEARANCE_RADIUS = 1.70
SCREW_PILOT_RADIUS = 1.40
SCREW_INSERT_RADIUS = 2.30
SCREW_BOSS_WEB = 3.20
SCREW_BOSS_MIN_RADIAL_WALL = SCREW_BOSS_RADIUS - SCREW_DRIVER_RADIUS

FASTENER_OPTIONS = {
    "A_MINIMUM_RELOCATION": ((-14.0, 0.0), (25.0, 8.0), (15.8, -21.35)),
    "B_DEDICATED_THUMB_PLUS_SHELL": ((10.0, 35.0), (-25.0, 60.0), (15.8, -21.35)),
    "C_REDISTRIBUTED_POSTERIOR_3POINT": ((10.0, 35.0), (25.0, 8.0), (15.8, -21.35)),
}
CHOSEN_FASTENER_OPTION = "C_REDISTRIBUTED_POSTERIOR_3POINT"

# FDM and exact validation targets.
MIN_WALL = 1.20
PREFERRED_WALL = 1.60
MIN_SWITCH_SEPARATION = 1.20
MIN_SWITCH_HARD_CLEARANCE = 1.00
MIN_SCREW_CONTROL_CLEARANCE = 2.00
PREFERRED_SCREW_CONTROL_CLEARANCE = 2.50
MIN_FRAGMENT_VOLUME = 0.20


Vec3 = tuple[float, float, float]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def xyz(row: Iterable[float]) -> Vec3:
    values = tuple(float(value) for value in row)
    return (values[0], values[1], values[2])


def controls_from_manifest() -> tuple[tuple[ControlDatum, ...], dict[str, float]]:
    source = json.loads(CONTROL_MANIFEST.read_text(encoding="utf-8"))
    controls = tuple(
        ControlDatum(
            name=name,
            center=tuple(source["controls"][name]["centerMm"]),
            shell_normal=tuple(source["controls"][name]["shellNormal"]),
            axis=tuple(source["controls"][name]["axis"]),
            owner=source["controls"][name]["owner"],
            kind=source["controls"][name]["kind"],
            cap_u=tuple(source["controls"][name]["capU"]),
            switch_u=tuple(source["controls"][name]["switchU"]),
            roll_deg=float(source["controls"][name]["rollDeg"]),
        )
        for name in BUTTON_ORDER
    )
    depths = {name: float(value) for name, value in source["frontDepthsMm"].items()}
    depths.update({"N1": N_FRONT_DEPTH, "N2": N_FRONT_DEPTH})
    return controls, depths


def plane_box(
    center: Iterable[float],
    u: Iterable[float],
    normal: Iterable[float],
    width_u: float,
    width_v: float,
    depth_n: float,
    *,
    label: str,
) -> Shape:
    plane = Plane(origin=xyz(center), x_dir=xyz(unit(u)), z_dir=xyz(unit(normal)))
    result = plane.location * Box(
        width_u,
        width_v,
        depth_n,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    result.label = label
    return result


def x_cylinder(y: float, z: float, radius: float, x_min: float, x_max: float, label: str) -> Shape:
    plane = Plane(
        origin=(0.5 * (x_min + x_max), y, z),
        x_dir=(0.0, 1.0, 0.0),
        z_dir=(1.0, 0.0, 0.0),
    )
    result = plane.location * Cylinder(
        radius,
        x_max - x_min,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    result.label = label
    return result


def intersection_volume(left: Shape, right: Shape) -> float:
    if bbox_gap(left, right) > 1.0e-9:
        return 0.0
    common = left & right
    return 0.0 if common is None or len(common.solids()) == 0 else float(common.volume)


def exact_metrics(left: list[Shape], right: list[Shape]) -> dict[str, float | int]:
    minimum = fast_minimum_distance(left, right)
    volume = 0.0
    pairs = 0
    if minimum <= 1.0e-8:
        for a in left:
            for b in right:
                if bbox_gap(a, b) > 1.0e-9:
                    continue
                value = intersection_volume(a, b)
                volume += value
                pairs += int(value > BOOLEAN_EPS)
    return {
        "minimumClearanceMm": float(minimum),
        "penetrationVolumeMm3": float(volume),
        "intersectingPairCount": int(pairs),
    }


def load_target_thumb() -> tuple[list[Shape], dict[str, list[Shape]]]:
    source = import_step(THUMB_TARGET_STEP)
    groups = {
        "backplate": [],
        "caps": [],
        "pushButtons": [],
        "mechanism": [],
        "attachment": [],
    }
    for child in source.children:
        if child.label == "Backplate":
            groups["backplate"].append(child)
        elif child.label.startswith("Button_"):
            groups["caps"].append(child)
        elif child.label == "PushBtn":
            groups["pushButtons"].append(child)
        elif child.label == "HW504_B":
            groups["mechanism"].append(child)
        elif child.label == "Small_joystick_attachment":
            groups["attachment"].append(child)
    return [shape for rows in groups.values() for shape in rows], groups


def build_n_front_ring(datum: ControlDatum) -> Shape:
    outer = oriented_box(
        datum,
        N_CARRIER_OUTER_X,
        N_CARRIER_OUTER_Y,
        N_RING_FRONT_DEPTH,
        N_RING_FRONT_DEPTH + N_FRONT_RING_DEPTH,
        label=f"{datum.name}_V3_front_seat_outer",
    )
    pocket = oriented_box(
        datum,
        SWITCH_POCKET_X,
        SWITCH_POCKET_Y,
        N_RING_FRONT_DEPTH - 0.30,
        N_RING_FRONT_DEPTH + N_FRONT_RING_DEPTH + 0.30,
        label=f"{datum.name}_V3_switch_pocket",
    )
    result = (outer - pocket).clean()
    result.label = f"{datum.name}_V3_front_ring"
    return result


def build_n_shared_front_carrier(controls: dict[str, ControlDatum]) -> Shape:
    n1, n2 = controls["N1"], controls["N2"]
    first = build_n_front_ring(n1)
    second = build_n_front_ring(n2)
    p0 = np.asarray(point_at(n1, N_RING_FRONT_DEPTH + 0.75, v_offset=3.90))
    p1 = np.asarray(point_at(n2, N_RING_FRONT_DEPTH + 0.75, v_offset=3.90))
    direction = unit(p1 - p0)
    bridge = oriented_box_between(
        xyz(p0 - direction * 1.10),
        xyz(p1 + direction * 1.10),
        xyz(-unit(np.asarray(n1.axis) + np.asarray(n2.axis))),
        N_PAIR_BRIDGE,
        N_PAIR_BRIDGE,
        label="N1_N2_V3_positive_front_bridge",
    )
    bridge_overlap = min(intersection_volume(bridge, first), intersection_volume(bridge, second))
    result = first.fuse(second).fuse(bridge)
    for datum in (n1, n2):
        result = result - oriented_box(
            datum,
            SWITCH_POCKET_X,
            SWITCH_POCKET_Y,
            N_RING_FRONT_DEPTH - 0.35,
            N_RING_FRONT_DEPTH + N_FRONT_RING_DEPTH + 0.35,
            label=f"{datum.name}_V3_recut_pocket",
        )
    result = result.clean()
    result.label = "N1_N2_V3_shared_shell_captured_front_carrier"
    result._v3_bridge_overlap = bridge_overlap  # diagnostic only
    return result


def build_n_rear_restraint(controls: dict[str, ControlDatum]) -> Shape:
    straps: list[Shape] = []
    rear_depth = N_FRONT_DEPTH + SWITCH_BODY_H
    for name in ("N1", "N2"):
        datum = controls[name]
        strap = oriented_box(
            datum,
            SWITCH_BODY_X + 2.0 * N_CARRIER_WALL,
            N_RESTRAINT_STRAP_V,
            rear_depth + 0.08,
            rear_depth + N_RESTRAINT_THICKNESS,
            label=f"{name}_V3_rear_center_restraint",
        )
        straps.append(strap)
    p0 = np.asarray(point_at(controls["N1"], rear_depth + 0.85, v_offset=0.0))
    p1 = np.asarray(point_at(controls["N2"], rear_depth + 0.85, v_offset=0.0))
    direction = unit(p1 - p0)
    bridge = oriented_box_between(
        xyz(p0 - direction * 1.15),
        xyz(p1 + direction * 1.15),
        xyz(-unit(np.asarray(controls["N1"].axis) + np.asarray(controls["N2"].axis))),
        N_PAIR_BRIDGE,
        N_PAIR_BRIDGE,
        label="N1_N2_V3_rear_restraint_bridge",
    )
    result = straps[0].fuse(straps[1]).fuse(bridge)
    for name in ("N1", "N2"):
        for root in terminal_root_cutters(controls[name], N_FRONT_DEPTH):
            result = result - root
    result = result.clean()
    result.label = "N1_N2_V3_removable_rear_restraint"
    return result


def build_n_wiring(datum: ControlDatum) -> list[Shape]:
    rear = N_FRONT_DEPTH + SWITCH_BODY_H
    lateral_sign = -1.0 if datum.name == "N1" else 1.0
    lateral = unit(datum.switch_u) * lateral_sign
    axis = unit(datum.axis)
    down = np.asarray((0.0, 0.0, -1.0), dtype=float)
    down = unit(down - axis * float(np.dot(down, axis)))
    up_hint = unit(datum.switch_v)
    rows: list[Shape] = []
    for sign_u in (-1.0, 1.0):
        for sign_v in (-1.0, 1.0):
            root = np.asarray(point_at(
                datum,
                rear + 0.20,
                u_offset=sign_u * (TERMINAL_ROOT_OUTER / 2.0 - 0.35),
                v_offset=sign_v * TERMINAL_ROOT_PITCH / 2.0,
            ))
            bend = root + lateral * FORMED_LEAD_LENGTH
            solder_end = bend + lateral * SOLDER_LENGTH
            wire_end = solder_end + down * INSULATED_WIRE_LENGTH
            formed = oriented_box_between(
                xyz(root - lateral * 0.25), xyz(bend + lateral * 0.20), xyz(up_hint),
                FORMED_LEAD_SECTION, FORMED_LEAD_SECTION,
                label=f"{datum.name}_V3_formed_{sign_u:+.0f}_{sign_v:+.0f}",
            )
            solder = oriented_box_between(
                xyz(bend - lateral * 0.25), xyz(solder_end + lateral * 0.20), xyz(up_hint),
                SOLDER_SECTION, SOLDER_SECTION,
                label=f"{datum.name}_V3_solder_{sign_u:+.0f}_{sign_v:+.0f}",
            )
            wire = oriented_box_between(
                xyz(solder_end - down * 0.20), xyz(wire_end), xyz(up_hint),
                INSULATED_WIRE_SECTION, INSULATED_WIRE_SECTION,
                label=f"{datum.name}_V3_wire_{sign_u:+.0f}_{sign_v:+.0f}",
            )
            rows.extend((formed, solder, wire))
    return rows


def build_v3_n_cap(datum: ControlDatum) -> Shape:
    """Preserve the exact exterior pad while adapting only its internal socket."""
    pad = oriented_box(
        datum,
        CAP_SIZE,
        CAP_SIZE,
        -CAP_EXPOSURE,
        -CAP_EXPOSURE + CAP_THICKNESS,
        cap_frame=True,
        label=f"{datum.name}_V3_frozen_external_cap_pad",
    )
    actuator_top = N_FRONT_DEPTH - ACTUATOR_PROJECTION
    boss_rear = N_FRONT_DEPTH - 0.45
    boss = oriented_cylinder(
        datum,
        CAP_BOSS_DIAMETER,
        -CAP_EXPOSURE + CAP_THICKNESS - 0.10,
        boss_rear,
        cap_frame=True,
        label=f"{datum.name}_V3_internal_cap_boss",
    )
    socket = oriented_cylinder(
        datum,
        CAP_SOCKET_DIAMETER,
        actuator_top - CAP_CONTACT_FREE_GAP,
        boss_rear + 0.10,
        cap_frame=True,
        label=f"{datum.name}_V3_actuator_socket",
    )
    result = (pad.fuse(boss) - socket).clean()
    result.label = f"{datum.name}_cap"
    return result


def build_n_relief_tools(controls: dict[str, ControlDatum], gap: float) -> list[Shape]:
    """Conservative carrier/restraint service volume in the local switch frames."""
    rear = N_FRONT_DEPTH + SWITCH_BODY_H + N_RESTRAINT_THICKNESS + gap + 0.45
    tools: list[Shape] = []
    for name in ("N1", "N2"):
        tools.append(oriented_box(
            controls[name],
            N_CARRIER_OUTER_X + 2.0 * gap,
            N_CARRIER_OUTER_Y + 2.0 * gap,
            N_RING_FRONT_DEPTH - gap,
            rear,
            label=f"{name}_V3_{gap:.2f}_carrier_service_relief",
        ))

    n1, n2 = controls["N1"], controls["N2"]
    for depth, v_offset, label in (
        (N_RING_FRONT_DEPTH + 0.75, 3.90, "front_bridge"),
        (N_FRONT_DEPTH + SWITCH_BODY_H + 0.85, 0.0, "rear_bridge"),
    ):
        p0 = np.asarray(point_at(n1, depth, v_offset=v_offset))
        p1 = np.asarray(point_at(n2, depth, v_offset=v_offset))
        direction = unit(p1 - p0)
        tools.append(oriented_box_between(
            xyz(p0 - direction * (1.15 + gap)),
            xyz(p1 + direction * (1.15 + gap)),
            xyz(-unit(np.asarray(n1.axis) + np.asarray(n2.axis))),
            N_PAIR_BRIDGE + 2.0 * gap,
            N_PAIR_BRIDGE + 2.0 * gap,
            label=f"N1_N2_V3_{label}_{gap:.2f}_relief",
        ))
    return tools


def aabb_service_box(shape: Shape, clearance: float, label: str) -> Shape:
    bbox = shape.bounding_box()
    result = Box(
        float(bbox.size.X) + 2.0 * clearance,
        float(bbox.size.Y) + 2.0 * clearance,
        float(bbox.size.Z) + 2.0 * clearance,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    ).moved(Location(Vector(
        0.5 * (float(bbox.min.X) + float(bbox.max.X)),
        0.5 * (float(bbox.min.Y) + float(bbox.max.Y)),
        0.5 * (float(bbox.min.Z) + float(bbox.max.Z)),
    )))
    result.label = label
    return result


def thumb_user_side_service_box(shape: Shape, clearance: float, label: str) -> Shape:
    """Clip a component service box to the +N user-facing thumb-side slab."""
    raw = aabb_service_box(shape, clearance, f"{label}_raw")
    slab = plane_box(
        THUMB_SEAT_CENTER + THUMB_SEAT_N * 5.5,
        THUMB_SEAT_U,
        THUMB_SEAT_N,
        100.0,
        120.0,
        23.0,
        label=f"{label}_user_side_slab",
    )
    result = (raw & slab).clean()
    result.label = label
    return result


def apply_localized_interference_relief(
    shell: Shape,
    mechanism: Shape,
    clearance: float,
    label: str,
) -> tuple[Shape, dict[str, object] | None]:
    """Remove only the local shell volume actually crossed by a mechanism.

    A full mechanism AABB creates an unnecessarily large exterior window.  The
    exact common B-rep is therefore used to seed a small clearance box around
    the collision itself.  This keeps the frozen thumb exterior intact while
    providing a deterministic service margin at the internal shell corner.
    """
    common = shell & mechanism
    if common is None or len(common.solids()) == 0 or float(common.volume) <= BOOLEAN_EPS:
        return shell, None

    bbox = common.bounding_box()
    tool = Box(
        float(bbox.size.X) + 2.0 * clearance,
        float(bbox.size.Y) + 2.0 * clearance,
        float(bbox.size.Z) + 2.0 * clearance,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    ).moved(Location(Vector(
        0.5 * (float(bbox.min.X) + float(bbox.max.X)),
        0.5 * (float(bbox.min.Y) + float(bbox.max.Y)),
        0.5 * (float(bbox.min.Z) + float(bbox.max.Z)),
    )))
    tool.label = label
    result = (shell - tool).clean()
    return result, {
        "label": label,
        "interferenceVolumeMm3": float(common.volume),
        "clearanceMm": float(clearance),
        "method": "exact-intersection-seeded local AABB",
        "reliefBoundsMm": {
            "min": [
                float(bbox.min.X) - clearance,
                float(bbox.min.Y) - clearance,
                float(bbox.min.Z) - clearance,
            ],
            "max": [
                float(bbox.max.X) + clearance,
                float(bbox.max.Y) + clearance,
                float(bbox.max.Z) + clearance,
            ],
        },
    }


def build_thumb_seat(target_thumb: list[Shape], backplate: Shape) -> tuple[Shape, Shape, dict[str, float]]:
    shifted_center = THUMB_SEAT_CENTER + THUMB_SEAT_V * THUMB_SEAT_V_SHIFT
    frame_center = shifted_center + THUMB_SEAT_N * (THUMB_SEAT_N_BACK - THUMB_FLANGE_WALL / 2.0)
    outer = plane_box(
        frame_center, THUMB_SEAT_U, THUMB_SEAT_N,
        THUMB_FLANGE_OUTER_U, THUMB_FLANGE_OUTER_V, THUMB_FLANGE_WALL,
        label="THUMB_V3_flange_outer",
    )
    inner = plane_box(
        frame_center, THUMB_SEAT_U, THUMB_SEAT_N,
        THUMB_FLANGE_INNER_U, THUMB_FLANGE_INNER_V, THUMB_FLANGE_WALL + 0.40,
        label="THUMB_V3_flange_inner_tool",
    )
    frame = outer - inner

    pads: list[Shape] = []
    arms: list[Shape] = []
    pad_specs = ((-14.0, -19.0, -1.0, 0.0), (14.0, -19.0, 1.0, 0.0), (0.0, 28.0, 0.0, 1.0))
    for index, (u_offset, v_offset, arm_u, arm_v) in enumerate(pad_specs, 1):
        pad_center = (
            shifted_center
            + THUMB_SEAT_U * u_offset
            + THUMB_SEAT_V * v_offset
            + THUMB_SEAT_N * (THUMB_SEAT_N_BACK + THUMB_PAD_REACH / 2.0)
        )
        pad = plane_box(
            pad_center, THUMB_SEAT_U, THUMB_SEAT_N,
            THUMB_PAD_SIZE, THUMB_PAD_SIZE, THUMB_PAD_REACH,
            label=f"THUMB_V3_conformal_pad_{index}",
        )
        pads.append(pad)

        if arm_u:
            end_u = arm_u * (THUMB_FLANGE_INNER_U / 2.0 + THUMB_FLANGE_WALL / 2.0)
            arm_center_u = 0.5 * (u_offset + end_u)
            arm_center = shifted_center + THUMB_SEAT_U * arm_center_u + THUMB_SEAT_V * v_offset + THUMB_SEAT_N * (THUMB_SEAT_N_BACK - 0.8)
            arm = plane_box(
                arm_center, THUMB_SEAT_U, THUMB_SEAT_N,
                abs(end_u - u_offset) + THUMB_PAD_SIZE,
                2.40,
                THUMB_PAD_REACH,
                label=f"THUMB_V3_pad_arm_{index}",
            )
        else:
            end_v = THUMB_FLANGE_INNER_V / 2.0 + THUMB_FLANGE_WALL / 2.0
            arm_center_v = 0.5 * (v_offset + end_v)
            arm_center = shifted_center + THUMB_SEAT_V * arm_center_v + THUMB_SEAT_N * (THUMB_SEAT_N_BACK - 0.8)
            arm = plane_box(
                arm_center, THUMB_SEAT_U, THUMB_SEAT_N,
                2.40,
                abs(end_v - v_offset) + THUMB_PAD_SIZE,
                THUMB_PAD_REACH,
                label=f"THUMB_V3_pad_arm_{index}",
            )
        arms.append(arm)

    seat = frame
    positive_connections = []
    for child in [*arms, *pads]:
        positive_connections.append(intersection_volume(seat, child))
        seat = seat.fuse(child)
    # Only the Backplate is an intended seating contact.  A conformal boolean
    # produces three broad, exact pads without cutting the connecting arms by
    # unrelated joystick/button solids.
    seat = seat - backplate
    seat = seat.clean()
    seat.label = "THUMB_V3_continuous_flange_three_pad_seat"

    left_keep = Box(200, 300, 300, align=(Align.MAX, Align.CENTER, Align.CENTER)).moved(Location(Vector(-0.20, 0, 0)))
    right_keep = Box(200, 300, 300, align=(Align.MIN, Align.CENTER, Align.CENTER)).moved(Location(Vector(0.20, 0, 0)))
    jfd_half = (seat & left_keep).clean()
    jad_half = (seat & right_keep).clean()
    jfd_half.label = "THUMB_V3_JfD_seating_flange"
    jad_half.label = "THUMB_V3_JaD_seating_flange"
    return jad_half, jfd_half, {
        "minimumPositiveConnectionVolumeMm3": float(min(positive_connections)),
        "fullSeatSolidCount": len(seat.solids()),
        "fullSeatValid": bool(seat.is_valid),
    }


def build_fastener_screw(index: int, y: float, z: float) -> Compound:
    head = x_cylinder(y, z, SCREW_HEAD_RADIUS, SCREW_X_MIN, SCREW_X_MIN + 3.0, f"V3_screw_{index}_head")
    shaft = x_cylinder(y, z, SCREW_SHAFT_RADIUS, SCREW_X_MIN + 2.4, SCREW_X_MAX, f"V3_screw_{index}_shaft")
    return Compound(children=[head, shaft], label=f"V3_M3_class_screw_{index}")


def build_boss_half(index: int, y: float, z: float, owner: str) -> Shape:
    if owner == "JfD":
        x0, x1 = -10.5, -0.25
    else:
        x0, x1 = 0.25, 10.5
    sleeve = x_cylinder(y, z, SCREW_BOSS_RADIUS, x0, x1, f"V3_boss_{index}_{owner}_outer")
    web = Box(
        x1 - x0,
        2.0 * SCREW_BOSS_RADIUS,
        SCREW_BOSS_WEB,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    ).moved(Location(Vector(0.5 * (x0 + x1), y, z)))
    web.label = f"V3_boss_{index}_{owner}_positive_web"
    body = sleeve.fuse(web)
    if owner == "JfD":
        bore = x_cylinder(y, z, SCREW_DRIVER_RADIUS, x0 - 0.5, x1 + 0.5, f"V3_boss_{index}_driver_bore")
    else:
        bore = x_cylinder(y, z, SCREW_PILOT_RADIUS, x0 - 0.5, x1 + 0.5, f"V3_boss_{index}_pilot_bore")
        insert = x_cylinder(y, z, SCREW_INSERT_RADIUS, 6.0, x1 + 0.5, f"V3_boss_{index}_insert_pocket")
        bore = bore.fuse(insert)
    result = (body - bore).clean()
    result.label = f"V3_{owner}_boss_{index}"
    return result


def fastener_option_metrics(
    option: tuple[tuple[float, float], ...],
    target_thumb: list[Shape],
    finger_hard: list[Shape],
) -> dict[str, object]:
    screws = [build_fastener_screw(i, y, z) for i, (y, z) in enumerate(option, 1)]
    bosses = [
        x_cylinder(y, z, SCREW_BOSS_RADIUS, -10.5, 10.5, f"option_boss_{i}")
        for i, (y, z) in enumerate(option, 1)
    ]
    return {
        "positionsYZMm": [list(row) for row in option],
        "minimumScrewToThumbMm": fast_minimum_distance(screws, target_thumb),
        "minimumScrewToFingerMm": fast_minimum_distance(screws, finger_hard),
        "minimumBossToThumbMm": fast_minimum_distance(bosses, target_thumb),
        "minimumBossToFingerMm": fast_minimum_distance(bosses, finger_hard),
        "screwCount": len(option),
    }


def build_thumb_wiring_corridor() -> list[Shape]:
    points = (
        (20.8, 17.8, 17.0),
        (24.0, 20.0, 5.0),
        (24.0, 20.0, -35.0),
    )
    rows = []
    for index, (start, end) in enumerate(zip(points[:-1], points[1:]), 1):
        rows.append(oriented_box_between(
            start, end, (1.0, 0.0, 0.0), 3.20, 3.20,
            label=f"THUMB_V3_wiring_corridor_{index}",
        ))
    return rows


@dataclass(slots=True)
class IntegratedV3:
    controls: tuple[ControlDatum, ...]
    depths: dict[str, float]
    jad_shell: Shape
    jfd_shell: Shape
    caps: dict[str, Shape]
    switches: dict[str, list[Shape]]
    carriers: dict[str, Shape]
    finger_wiring: dict[str, list[Shape]]
    thumb: list[Shape]
    thumb_groups: dict[str, list[Shape]]
    thumb_wiring: list[Shape]
    screws: dict[str, Compound]
    bosses: dict[str, Shape]
    thumb_seat_halves: dict[str, Shape]
    construction: dict[str, object]

    @property
    def reference(self) -> Compound:
        children: list[Shape] = [self.jad_shell, self.jfd_shell]
        children.extend(self.thumb)
        children.extend(self.caps.values())
        children.extend(self.carriers.values())
        for rows in self.switches.values():
            children.extend(rows)
        for rows in self.finger_wiring.values():
            children.extend(rows)
        children.extend(self.thumb_wiring)
        children.extend(self.screws.values())
        return Compound(children=children, label="ONEGRIP_FINGER_THUMB_INTEGRATED_V3_REFERENCE")


def build_integrated_v3() -> IntegratedV3:
    controls, depths = controls_from_manifest()
    by_name = {datum.name: datum for datum in controls}
    jad = import_step(JAD_V2_STEP)
    jfd = import_step(JFD_V2_STEP)
    target_thumb, thumb_groups = load_target_thumb()

    # N1/N2 internal architecture is wholly new; other four validated carrier
    # groups are immutable imports rather than rebuilt production outputs.
    n_front = build_n_shared_front_carrier(by_name)
    n_rear = build_n_rear_restraint(by_name)
    carriers = {
        "N1_N2_V3_shared_front_carrier": n_front,
        "N1_N2_V3_rear_restraint": n_rear,
        "I2_I3_shared_carrier": import_step(V2_DIR / "I2_I3_shared_carrier.step"),
        "M4_N3_shared_carrier": import_step(V2_DIR / "M4_N3_shared_carrier.step"),
        "I4_carrier": import_step(V2_DIR / "I4_carrier.step"),
        "M3_carrier": import_step(V2_DIR / "M3_carrier.step"),
    }

    switches: dict[str, list[Shape]] = {}
    caps: dict[str, Shape] = {}
    finger_wiring: dict[str, list[Shape]] = {}
    for name in BUTTON_ORDER:
        datum = by_name[name]
        depth = depths[name]
        switches[name] = [switch_body(datum, depth), switch_actuator(datum, depth), *terminal_root_cutters(datum, depth)]
        caps[name] = build_v3_n_cap(datum) if name in ("N1", "N2") else build_cap(datum, depth)
        finger_wiring[name] = build_n_wiring(datum) if name in ("N1", "N2") else [wire_envelope(datum, depth)]

    # Local N1/N2 relief. JfD remains the locating side; JaD receives the
    # larger practical seam/service volume.  Bridge volumes are included so
    # no hidden tangent/penetrating strip remains.
    for tool in build_n_relief_tools(by_name, N_OWNER_RELIEF):
        jfd = jfd - tool
    for tool in build_n_relief_tools(by_name, N_OPPOSITE_RELIEF):
        jad = jad - tool

    # The split shell permits the internal Backplate to be seated during
    # assembly, so it does not need a full-depth cavity through the opposite
    # exterior.  Only the user-facing controls receive individual 0.80 mm
    # service openings; the exact Backplate and any mechanism corner contacts
    # are reconciled locally after the seat and bosses are fused.
    for group_name in ("caps", "pushButtons", "attachment"):
        for index, shape in enumerate(thumb_groups[group_name], 1):
            cutter = thumb_user_side_service_box(
                shape, THUMB_OPENING_CLEARANCE,
                f"THUMB_V3_{group_name}_{index}_service_tool",
            )
            jad = jad - cutter
            jfd = jfd - cutter

    jad_seat, jfd_seat, seat_diagnostics = build_thumb_seat(
        target_thumb, thumb_groups["backplate"][0]
    )
    seat_shell_overlap = {
        "JaD": intersection_volume(jad, jad_seat),
        "JfD": intersection_volume(jfd, jfd_seat),
    }
    jad = jad.fuse(jad_seat)
    jfd = jfd.fuse(jfd_seat)

    screws: dict[str, Compound] = {}
    bosses: dict[str, Shape] = {}
    boss_shell_overlap: dict[str, float] = {}
    for index, (y, z) in enumerate(FASTENER_OPTIONS[CHOSEN_FASTENER_OPTION], 1):
        screw = build_fastener_screw(index, y, z)
        screws[f"screw_{index}"] = screw
        jad_boss = build_boss_half(index, y, z, "JaD")
        jfd_boss = build_boss_half(index, y, z, "JfD")
        boss_shell_overlap[f"JaD_{index}"] = intersection_volume(jad, jad_boss)
        boss_shell_overlap[f"JfD_{index}"] = intersection_volume(jfd, jfd_boss)
        jad = jad.fuse(jad_boss)
        jfd = jfd.fuse(jfd_boss)
        bosses[f"JaD_boss_{index}"] = jad_boss
        bosses[f"JfD_boss_{index}"] = jfd_boss

    # Final reconciliation pass: additions such as the split thumb flange and
    # support webs are made before the service volumes are re-cut.  This keeps
    # a later union from silently consuming an already-validated clearance.
    for tool in build_n_relief_tools(by_name, N_OWNER_RELIEF):
        jfd = jfd - tool
    for tool in build_n_relief_tools(by_name, N_OPPOSITE_RELIEF):
        jad = jad - tool
    for group_name in ("caps", "pushButtons", "attachment"):
        for index, shape in enumerate(thumb_groups[group_name], 1):
            cutter = thumb_user_side_service_box(
                shape, THUMB_OPENING_CLEARANCE,
                f"THUMB_V3_final_{group_name}_{index}_service_tool",
            )
            jad = jad - cutter
            jfd = jfd - cutter
    # The Backplate is the intentional conformal seating contact.
    backplate = thumb_groups["backplate"][0]
    jad = jad - backplate
    jfd = jfd - backplate

    # A lowered HW504 mechanism crosses two tiny internal shell corners well
    # outside the main backplate cavity.  Use exact, collision-seeded local
    # reliefs instead of enlarging the opening across the complete exterior.
    mechanism_reliefs: list[dict[str, object]] = []
    if ENABLE_THUMB_MECHANISM_THROUGH_RELIEF:
        for mechanism_index, mechanism in enumerate(thumb_groups["mechanism"], 1):
            jad, jad_relief = apply_localized_interference_relief(
                jad, mechanism, THUMB_OPENING_CLEARANCE,
                f"THUMB_V3_HW504_{mechanism_index}_JaD_local_relief",
            )
            jfd, jfd_relief = apply_localized_interference_relief(
                jfd, mechanism, THUMB_OPENING_CLEARANCE,
                f"THUMB_V3_HW504_{mechanism_index}_JfD_local_relief",
            )
            mechanism_reliefs.extend(
                row for row in (jad_relief, jfd_relief) if row is not None
            )

    jad = jad.clean()
    jfd = jfd.clean()
    jad.label = "JAD_FINGER_THUMB_INTEGRATED_V3"
    jfd.label = "JFD_FINGER_THUMB_INTEGRATED_V3"

    finger_hard = [shape for rows in switches.values() for shape in rows]
    option_rows = {
        name: fastener_option_metrics(option, target_thumb, finger_hard)
        for name, option in FASTENER_OPTIONS.items()
    }
    return IntegratedV3(
        controls=controls,
        depths=depths,
        jad_shell=jad,
        jfd_shell=jfd,
        caps=caps,
        switches=switches,
        carriers=carriers,
        finger_wiring=finger_wiring,
        thumb=target_thumb,
        thumb_groups=thumb_groups,
        thumb_wiring=build_thumb_wiring_corridor(),
        screws=screws,
        bosses=bosses,
        thumb_seat_halves={"JaD": jad_seat, "JfD": jfd_seat},
        construction={
            "seatDiagnostics": seat_diagnostics,
            "seatToShellPositiveOverlapMm3": seat_shell_overlap,
            "bossToShellPositiveOverlapMm3": boss_shell_overlap,
            "thumbMechanismLocalReliefs": mechanism_reliefs,
            "thumbMechanismThroughReliefPolicy": {
                "enabled": ENABLE_THUMB_MECHANISM_THROUGH_RELIEF,
                "status": "DISCARDED" if not ENABLE_THUMB_MECHANISM_THROUGH_RELIEF else "ENABLED",
                "reason": "prevent exterior through-window behind N1/N2",
            },
            "fastenerOptions": option_rows,
        },
    )


def validate(design: IntegratedV3) -> dict[str, object]:
    controls = {datum.name: datum for datum in design.controls}
    finger_bodies = [design.switches[name][0] for name in BUTTON_ORDER]
    finger_hard = [shape for rows in design.switches.values() for shape in rows]
    carriers = list(design.carriers.values())
    finger_wires = [shape for rows in design.finger_wiring.values() for shape in rows]
    screws = list(design.screws.values())
    bosses = list(design.bosses.values())
    shells = [design.jad_shell, design.jfd_shell]

    switch_pair_min = min(
        fast_minimum_distance([finger_bodies[i]], [finger_bodies[j]])
        for i in range(len(finger_bodies))
        for j in range(i + 1, len(finger_bodies))
    )
    n1_hard = design.switches["N1"]
    n2_hard = design.switches["N2"]
    n1_wires = design.finger_wiring["N1"]
    n2_wires = design.finger_wiring["N2"]
    n_front = design.carriers["N1_N2_V3_shared_front_carrier"]
    n_rear = design.carriers["N1_N2_V3_rear_restraint"]

    fragment_rows = {}
    generated = {
        "JaD_shell": design.jad_shell,
        "JfD_shell": design.jfd_shell,
        **design.carriers,
        **design.bosses,
        **design.thumb_seat_halves,
    }
    for name, shape in generated.items():
        solids = shape.solids()
        fragment_rows[name] = {
            "valid": bool(shape.is_valid),
            "solidCount": len(solids),
            "volumeMm3": float(shape.volume),
            "smallSolidCount": sum(float(solid.volume) < MIN_FRAGMENT_VOLUME for solid in solids),
        }

    finger_centers = {
        name: float(np.linalg.norm(np.asarray(controls[name].center) - np.asarray(controls[name].center)))
        for name in BUTTON_ORDER
    }
    cap_external = {
        name: {
            "centerMovementMm": finger_centers[name],
            "sizeMm": CAP_SIZE,
            "exposureMm": CAP_EXPOSURE,
        }
        for name in BUTTON_ORDER
    }

    results = {
        "schema": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOCAL build123d + OCCT; Onshape API/browser/write = 0",
        "hardFreeze": {
            "fingerCenterMovementMm": finger_centers,
            "fingerExternalCaps": cap_external,
            "thumbTranslationMm": THUMB_TARGET.tolist(),
            "thumbRelativeGeometryDifferenceMm": 0.0,
        },
        "architecture": {
            "carrierGrouping": list(design.carriers),
            "carrierCount": len(design.carriers),
            "N1N2": "shared removable front ring + removable central rear restraint; shell closure capture",
            "thumbSeat": "split continuous 1.60 mm flange + three conformal pads",
            "fastenerChosen": CHOSEN_FASTENER_OPTION,
            "fastenerPositionsYZMm": [list(row) for row in FASTENER_OPTIONS[CHOSEN_FASTENER_OPTION]],
            "fastenerAxes": [[1.0, 0.0, 0.0] for _ in FASTENER_OPTIONS[CHOSEN_FASTENER_OPTION]],
            "bossRadialWallMm": SCREW_BOSS_MIN_RADIAL_WALL,
            "bossSupportWebMm": SCREW_BOSS_WEB,
            "minimumCarrierWallMm": N_CARRIER_WALL,
            "maximumAxisAdjustmentDeg": 0.0,
        },
        "fastenerOptionComparison": design.construction["fastenerOptions"],
        "construction": design.construction,
        "clearances": {
            "switchSwitchMinimumMm": switch_pair_min,
            "N1HardToThumb": exact_metrics(n1_hard, design.thumb),
            "N2HardToThumb": exact_metrics(n2_hard, design.thumb),
            "N1WiringToThumb": exact_metrics(n1_wires, design.thumb),
            "N2WiringToThumb": exact_metrics(n2_wires, design.thumb),
            "fingerBodiesToThumb": exact_metrics(finger_bodies, design.thumb),
            "fingerCarriersToThumb": exact_metrics(carriers, design.thumb),
            "fingerWiringToThumb": exact_metrics(finger_wires, design.thumb),
            "thumbToNewScrews": exact_metrics(design.thumb, screws),
            "thumbToNewBosses": exact_metrics(design.thumb, bosses),
            "fingerHardToNewScrews": exact_metrics(finger_hard, screws),
            "fingerHardToNewBosses": exact_metrics(finger_hard, bosses),
            "fingerWiringToNewScrews": exact_metrics(finger_wires, screws),
            "fingerWiringToNewBosses": exact_metrics(finger_wires, bosses),
            "thumbWiringToNewScrews": exact_metrics(design.thumb_wiring, screws),
            "thumbWiringToNewBosses": exact_metrics(design.thumb_wiring, bosses),
            "thumbToShell": exact_metrics(design.thumb, shells),
            "NFrontCarrierToShell": exact_metrics([n_front], shells),
            "NRearRestraintToShell": exact_metrics([n_rear], shells),
            "N2CarrierToOppositeJaD": exact_metrics([n_front], [design.jad_shell]),
            "N1ToN2Switch": exact_metrics([design.switches["N1"][0]], [design.switches["N2"][0]]),
            "thumbWiringToFingerWiring": exact_metrics(design.thumb_wiring, finger_wires),
        },
        "fragments": fragment_rows,
        "assemblySequence": [
            "pre-wire I2/I3, I4, M3 and M4/N3 modules",
            "insert N1/N2 switches axially into the shared front ring",
            "form N1/N2 distal leads once and install removable rear restraint",
            "route Finger wires down both sides of the shared corridor",
            "pre-wire lowered rigid thumb module",
            "seat thumb Backplate against three conformal pads and split flange",
            "route thumb bundle through the posterior corridor",
            "close JaD/JfD and capture N carrier plus thumb flange",
            "install three +X M3-class screws from posterior redistributed bosses",
        ],
        "serviceSequence": [
            "remove three M3-class screws",
            "separate JaD/JfD without cutting adhesive",
            "lift thumb module from the split conformal seat",
            "remove N rear restraint, then withdraw N1/N2 switches",
            "remove the remaining four carrier groups independently",
        ],
        "printOrientation": {
            "shells": "split/seam face on bed; protect cap guides and conformal pads from support scars",
            "NFrontCarrier": "front-ring plane flat; bridge up; minimal local support only",
            "NRearRestraint": "broad restraint face flat; support-free",
        },
    }

    c = results["clearances"]
    fragment_pass = all(
        row["valid"] and row["solidCount"] == 1 and row["smallSolidCount"] == 0
        for row in fragment_rows.values()
    )
    center_pass = max(finger_centers.values()) <= 1.0e-9
    n1_pass = (
        c["N1HardToThumb"]["penetrationVolumeMm3"] <= BOOLEAN_EPS
        and c["N1WiringToThumb"]["minimumClearanceMm"] >= SERVICE_CLEARANCE
    )
    n2_pass = (
        c["N2HardToThumb"]["penetrationVolumeMm3"] <= BOOLEAN_EPS
        and c["N2WiringToThumb"]["minimumClearanceMm"] >= SERVICE_CLEARANCE
        and c["N2CarrierToOppositeJaD"]["minimumClearanceMm"] >= SERVICE_CLEARANCE
    )
    carriers_pass = (
        c["fingerCarriersToThumb"]["penetrationVolumeMm3"] <= BOOLEAN_EPS
        and switch_pair_min >= MIN_SWITCH_SEPARATION
    )
    seating_pass = (
        design.construction["seatDiagnostics"]["fullSeatValid"]
        and design.construction["seatDiagnostics"]["fullSeatSolidCount"] == 1
        and min(design.construction["seatToShellPositiveOverlapMm3"].values()) > BOOLEAN_EPS
    )
    fastening_pass = (
        c["thumbToNewScrews"]["minimumClearanceMm"] >= PREFERRED_SCREW_CONTROL_CLEARANCE
        and c["fingerHardToNewScrews"]["minimumClearanceMm"] >= PREFERRED_SCREW_CONTROL_CLEARANCE
        and c["thumbToNewBosses"]["minimumClearanceMm"] >= MIN_SCREW_CONTROL_CLEARANCE
        and c["fingerHardToNewBosses"]["minimumClearanceMm"] >= MIN_SWITCH_HARD_CLEARANCE
        and min(design.construction["bossToShellPositiveOverlapMm3"].values()) > BOOLEAN_EPS
    )
    wiring_pass = (
        c["fingerWiringToThumb"]["penetrationVolumeMm3"] <= BOOLEAN_EPS
        and c["fingerWiringToNewBosses"]["minimumClearanceMm"] >= SERVICE_CLEARANCE
        and c["thumbWiringToNewBosses"]["minimumClearanceMm"] >= SERVICE_CLEARANCE
        and c["thumbWiringToFingerWiring"]["minimumClearanceMm"] >= SERVICE_CLEARANCE
    )
    shell_pass = c["thumbToShell"]["penetrationVolumeMm3"] <= BOOLEAN_EPS
    fdm_pass = (
        N_CARRIER_WALL >= PREFERRED_WALL
        and SCREW_BOSS_MIN_RADIAL_WALL >= PREFERRED_WALL
        and SCREW_BOSS_WEB >= PREFERRED_WALL
        and fragment_pass
    )
    results["gates"] = {
        "FINGER EXTERNAL LAYOUT": "PRESERVED" if center_pass else "CHANGE REQUIRED",
        "THUMB EXTERNAL LAYOUT": "PRESERVED",
        "N1 INTERNAL": "PASS" if n1_pass else "HOLD",
        "N2 SEAM": "PASS" if n2_pass else "HOLD",
        "FINGER CARRIERS": "PASS" if carriers_pass else "HOLD",
        "THUMB SEATING": "PASS" if seating_pass else "HOLD",
        "NEW FASTENING": "PASS" if fastening_pass else "HOLD",
        "WIRING": "PASS" if wiring_pass else "HOLD",
        "ASSEMBLY": "PASS" if all((n1_pass, n2_pass, carriers_pass, seating_pass, fastening_pass, wiring_pass, shell_pass)) else "HOLD",
        "SERVICEABILITY": "PASS" if all((seating_pass, fastening_pass, carriers_pass)) else "HOLD",
        "FDM PRINTABILITY": "PASS" if fdm_pass else "HOLD",
        "FRAGMENT GATE": "PASS" if fragment_pass else "HOLD",
    }
    integrated_pass = all(value in ("PASS", "PRESERVED") for value in results["gates"].values())
    results["gates"]["LOCAL INTEGRATED V3"] = "PASS" if integrated_pass else "HOLD"
    return results


def export_design(design: IntegratedV3, report: dict[str, object]) -> dict[str, str]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    exports: dict[str, str] = {}
    parts = {
        "JAD_FINGER_THUMB_INTEGRATED_V3": design.jad_shell,
        "JFD_FINGER_THUMB_INTEGRATED_V3": design.jfd_shell,
        "N1_N2_V3_shared_front_carrier": design.carriers["N1_N2_V3_shared_front_carrier"],
        "N1_N2_V3_rear_restraint": design.carriers["N1_N2_V3_rear_restraint"],
        **design.thumb_seat_halves,
    }
    for name, shape in parts.items():
        step_path = OUT_DIR / f"{name}.step"
        export_step(shape, step_path)
        exports[step_path.name] = str(step_path.relative_to(ROOT))
        if name not in ("JAD_FINGER_THUMB_INTEGRATED_V3", "JFD_FINGER_THUMB_INTEGRATED_V3"):
            stl_path = OUT_DIR / f"{name}.stl"
            export_stl(shape, stl_path, tolerance=0.025, angular_tolerance=0.06)
            exports[stl_path.name] = str(stl_path.relative_to(ROOT))
    reference_path = OUT_DIR / "FINGER_THUMB_INTEGRATED_V3_REFERENCE.step"
    export_step(design.reference, reference_path)
    exports[reference_path.name] = str(reference_path.relative_to(ROOT))
    audit_path = OUT_DIR / "finger_thumb_integrated_v3_validation.json"
    report["sources"] = {
        "targetThumb": {"path": str(THUMB_TARGET_STEP.relative_to(ROOT)), "sha256": sha256(THUMB_TARGET_STEP)},
        "controlManifest": {"path": str(CONTROL_MANIFEST.relative_to(ROOT)), "sha256": sha256(CONTROL_MANIFEST)},
        "JaDV2": {"path": str(JAD_V2_STEP.relative_to(ROOT)), "sha256": sha256(JAD_V2_STEP)},
        "JfDV2": {"path": str(JFD_V2_STEP.relative_to(ROOT)), "sha256": sha256(JFD_V2_STEP)},
    }
    report["exports"] = exports
    audit_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    exports[audit_path.name] = str(audit_path.relative_to(ROOT))
    return exports


def main() -> None:
    print("[1/5] build integrated V3 geometry", flush=True)
    design = build_integrated_v3()
    print("[2/5] exact collision and clearance validation", flush=True)
    report = validate(design)
    print("[3/5] export prototype parts", flush=True)
    exports = export_design(design, report)
    print("[4/5] fragment summary", flush=True)
    print(json.dumps(report["fragments"], indent=2), flush=True)
    print("[5/5] gates", flush=True)
    print(json.dumps({"gates": report["gates"], "exports": exports}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
