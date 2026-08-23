"""Production-oriented local finger-control V2 geometry.

This module is intentionally local-only.  It consumes the immutable clean
AP242 shell references and the user-approved marker transforms from
``finger_layout_reset``.  It contains no Onshape client, API or browser code.

The exterior button centres are frozen.  Every ITS-1105 actuator axis is
coincident with its cap travel axis; switch roll is chosen independently from
the exterior square-cap orientation so the housing can slide into a broad
shell-closure-captured C-channel without small hooks or snap fingers.
"""

from __future__ import annotations

from dataclasses import dataclass
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
)

from .finger_layout_reset import LayoutDatum, build_layout
from .model import oriented_box_between


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent / "out" / "finger_controls_v2"

# ---------------------------------------------------------------------------
# Hardware and user-facing language (millimetres)
# ---------------------------------------------------------------------------

SWITCH_BODY_X = 6.18
SWITCH_BODY_Y = 6.12
SWITCH_BODY_H = 3.56
SWITCH_POCKET_X = 6.40
SWITCH_POCKET_Y = 6.40
ACTUATOR_DIAMETER = 3.35
ACTUATOR_PROJECTION = 2.44
ACTUATOR_TRAVEL_NOMINAL = 0.25
ACTUATOR_TRAVEL_MAX = 0.35

CAP_SIZE = 7.60
CAP_THICKNESS = 1.20
CAP_EXPOSURE = 1.00
CAP_BOSS_DIAMETER = 4.50
CAP_SOCKET_DIAMETER = 3.45
CAP_CONTACT_FREE_GAP = 0.05
OPENING_SIZE = 8.00
N2_SEAM_OPENING_SIZE = 8.40
OPENING_CHAMFER_ALLOWANCE = 0.20

CARRIER_WALL = 1.60
CARRIER_OUTER_X = SWITCH_POCKET_X + 2.0 * CARRIER_WALL
CARRIER_OUTER_Y = SWITCH_POCKET_Y + 2.0 * CARRIER_WALL
CARRIER_REAR_PLATE = 1.60
CARRIER_SHELL_GAP = 0.20
CARRIER_FRONT_SEED = 4.40
CARRIER_FRONT_STEP = 0.20
CARRIER_FRONT_LIMIT = 9.00
SIDE_ACCESS_EXTRA = 0.40
BRIDGE_SECTION = 3.20
BRIDGE_PENETRATION = 1.00

TERMINAL_ROOT_OUTER = 7.90
TERMINAL_ROOT_PITCH = 4.50
TERMINAL_METAL_U = 0.30
TERMINAL_METAL_V = 0.70
TERMINAL_ROOT_DEPTH = 1.80
TERMINAL_CLEARANCE = 0.12
WIRE_EXIT_U = 4.00
WIRE_EXIT_V = 3.20
WIRE_STRAIGHT_LENGTH = 7.00

MIN_SWITCH_CLEARANCE = 1.20
PREFERRED_SWITCH_CLEARANCE = 1.30
MIN_STRUCTURAL_WALL = 1.20
MIN_DIVIDER = 0.80
MIN_SCREW_CLEARANCE = 2.50
BOOLEAN_VOLUME_EPS = 1.0e-6
SPLIT_CARRIER_CLEARANCE = 0.20

# Existing M3 shell screw keep-outs from the authenticated clean-shell audit.
SCREW_KEEP_OUTS = {
    "A": ((0.0, -41.87, 45.98), (-6.0, 10.0), 3.50),
    "B": ((0.0, -14.45, 23.07), (-6.0, 10.0), 3.50),
    "C": ((0.0, 15.80, -21.35), (-6.0, 10.0), 3.50),
}

BUTTON_ORDER = ("I2", "I3", "I4", "M3", "M4", "N1", "N2", "N3")
JFD_BUTTONS = frozenset(("I2", "I3", "M3", "N1", "N2"))
JAD_BUTTONS = frozenset(("I4", "M4", "N3"))
OUTER_LOAD_BUTTONS = frozenset(("I2", "N1", "N3"))

# Result of the first exact clean-shell depth search.  Keeping this table in
# the parameter section makes normal rebuilds deterministic and fast; the
# search function remains available for an explicit re-audit.
FROZEN_FRONT_DEPTHS = {
    "I2": 5.40,
    "I3": 5.80,
    "I4": 5.80,
    "M3": 5.20,
    "M4": 4.80,
    "N1": 4.80,
    "N2": 4.80,
    "N3": 5.60,
}

# Small internal-axis tilts increase the conservative ITS housing separation
# without changing any approved exterior centre.  Each axis is tilted toward
# its close neighbour at the surface, which moves the inward housing centre
# away from that neighbour.  Every value remains below the absolute 5 deg
# design limit.
AXIS_TILT_TARGETS = {
    "I2": ("I3", 2.50),
    "I3": ("I2", 2.50),
    "M4": ("N3", 4.00),
    "N3": ("M4", 4.00),
}


Vec3 = tuple[float, float, float]


def unit(value: Iterable[float]) -> np.ndarray:
    row = np.asarray(tuple(value), dtype=float)
    magnitude = float(np.linalg.norm(row))
    if magnitude <= 1.0e-12:
        raise ValueError("zero-length direction")
    return row / magnitude


def xyz(value: Iterable[float]) -> Vec3:
    row = tuple(float(item) for item in value)
    return (row[0], row[1], row[2])


def vector_xyz(value) -> Vec3:
    return (float(value.X), float(value.Y), float(value.Z))


def intersection_volume(left: Shape, right: Shape) -> float:
    if left is None or right is None:
        return 0.0
    if len(left.solids()) == 0 or len(right.solids()) == 0:
        return 0.0
    common = left & right
    return 0.0 if common is None or len(common.solids()) == 0 else float(common.volume)


def exact_distance(left: Shape, right: Shape) -> float:
    return float(left.distance_to_with_closest_points(right)[0])


@dataclass(frozen=True, slots=True)
class ControlDatum:
    name: str
    center: Vec3
    shell_normal: Vec3
    axis: Vec3
    owner: str
    kind: str
    cap_u: Vec3
    switch_u: Vec3
    roll_deg: float

    @property
    def cap_v(self) -> Vec3:
        return xyz(unit(np.cross(unit(self.shell_normal), unit(self.cap_u))))

    @property
    def switch_v(self) -> Vec3:
        return xyz(unit(np.cross(unit(self.axis), unit(self.switch_u))))

    @property
    def open_side_sign(self) -> float:
        seam_direction = np.asarray((1.0, 0.0, 0.0)) if self.owner == "JfD" else np.asarray((-1.0, 0.0, 0.0))
        sign = 1.0 if float(np.dot(unit(self.switch_u), seam_direction)) >= 0.0 else -1.0
        # The outer member of each close pair loads from the curved-wall side
        # so its insertion sweep never passes through the inner member.  Once
        # the preloaded carrier is seated, that broad shell wall closes the
        # open C-channel side.
        return -sign if self.name in OUTER_LOAD_BUTTONS else sign


def _projected_tangent(axis: np.ndarray, hint: np.ndarray) -> np.ndarray:
    projected = hint - axis * float(np.dot(axis, hint))
    if np.linalg.norm(projected) < 1.0e-9:
        projected = np.cross((0.0, 0.0, 1.0), axis)
    return unit(projected)


def controls_from_layout() -> tuple[ControlDatum, ...]:
    layout = build_layout()
    by_name = {datum.name: datum for datum in layout.datums}
    rows: list[ControlDatum] = []
    for name in BUTTON_ORDER:
        source: LayoutDatum = by_name[name]
        shell_normal = unit(source.normal)
        axis = shell_normal.copy()
        if name in AXIS_TILT_TARGETS:
            neighbor_name, tilt_deg = AXIS_TILT_TARGETS[name]
            neighbor = by_name[neighbor_name]
            toward = np.asarray(neighbor.center) - np.asarray(source.center)
            tangent = _projected_tangent(shell_normal, toward)
            angle = np.radians(tilt_deg)
            axis = unit(shell_normal * np.cos(angle) + tangent * np.sin(angle))
        cap_u = _projected_tangent(axis, np.cross((0.0, 0.0, 1.0), axis))
        owner = "JfD" if name in JFD_BUTTONS else "JaD"
        seam_hint = np.asarray((1.0, 0.0, 0.0)) if owner == "JfD" else np.asarray((-1.0, 0.0, 0.0))
        switch_u = _projected_tangent(axis, seam_hint)
        signed = float(np.dot(np.cross(cap_u, switch_u), axis))
        cosine = float(np.clip(np.dot(cap_u, switch_u), -1.0, 1.0))
        roll = float(np.degrees(np.arctan2(signed, cosine)))
        rows.append(
            ControlDatum(
                name=name,
                center=source.center,
                shell_normal=source.normal,
                axis=xyz(axis),
                owner=owner,
                kind=source.kind,
                cap_u=xyz(cap_u),
                switch_u=xyz(switch_u),
                roll_deg=roll,
            )
        )
    return tuple(rows)


def point_at(
    datum: ControlDatum,
    depth: float,
    *,
    u_offset: float = 0.0,
    v_offset: float = 0.0,
    cap_frame: bool = False,
) -> Vec3:
    axis = unit(datum.axis)
    u = unit(datum.cap_u if cap_frame else datum.switch_u)
    v = unit(datum.cap_v if cap_frame else datum.switch_v)
    point = np.asarray(datum.center) - axis * depth + u * u_offset + v * v_offset
    return xyz(point)


def oriented_box(
    datum: ControlDatum,
    width_u: float,
    width_v: float,
    front_depth: float,
    rear_depth: float,
    *,
    u_offset: float = 0.0,
    v_offset: float = 0.0,
    cap_frame: bool = False,
    label: str,
) -> Shape:
    if rear_depth <= front_depth:
        raise ValueError(f"{label}: rear must be greater than front")
    u = unit(datum.cap_u if cap_frame else datum.switch_u)
    axis = unit(datum.axis)
    origin = point_at(
        datum,
        0.5 * (front_depth + rear_depth),
        u_offset=u_offset,
        v_offset=v_offset,
        cap_frame=cap_frame,
    )
    plane = Plane(origin=origin, x_dir=xyz(u), z_dir=xyz(-axis))
    result = plane.location * Box(
        width_u,
        width_v,
        rear_depth - front_depth,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    result.label = label
    return result


def oriented_cylinder(
    datum: ControlDatum,
    diameter: float,
    front_depth: float,
    rear_depth: float,
    *,
    cap_frame: bool = False,
    label: str,
) -> Shape:
    axis = unit(datum.axis)
    u = unit(datum.cap_u if cap_frame else datum.switch_u)
    origin = point_at(datum, 0.5 * (front_depth + rear_depth), cap_frame=cap_frame)
    plane = Plane(origin=origin, x_dir=xyz(u), z_dir=xyz(-axis))
    result = plane.location * Cylinder(
        diameter / 2.0,
        rear_depth - front_depth,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    result.label = label
    return result


def opening_cutter(datum: ControlDatum) -> Shape:
    size = N2_SEAM_OPENING_SIZE if datum.name == "N2" else OPENING_SIZE
    return oriented_box(
        datum,
        size,
        size,
        -2.0,
        11.0,
        cap_frame=True,
        label=f"{datum.name}_opening_tool",
    )


def switch_body(datum: ControlDatum, front_depth: float) -> Shape:
    return oriented_box(
        datum,
        SWITCH_BODY_X,
        SWITCH_BODY_Y,
        front_depth,
        front_depth + SWITCH_BODY_H,
        label=f"{datum.name}_ITS1105_body",
    )


def switch_actuator(datum: ControlDatum, front_depth: float) -> Shape:
    return oriented_cylinder(
        datum,
        ACTUATOR_DIAMETER,
        front_depth - ACTUATOR_PROJECTION,
        front_depth,
        label=f"{datum.name}_ITS1105_actuator",
    )


def terminal_root_cutters(datum: ControlDatum, front_depth: float) -> tuple[Shape, ...]:
    rear = front_depth + SWITCH_BODY_H
    start_u = SWITCH_BODY_X / 2.0 + TERMINAL_METAL_U / 2.0
    end_u = (TERMINAL_ROOT_OUTER - TERMINAL_METAL_U) / 2.0
    channel_v = TERMINAL_METAL_V + 2.0 * TERMINAL_CLEARANCE
    channel_t = TERMINAL_METAL_U + 2.0 * TERMINAL_CLEARANCE
    v_axis = unit(datum.switch_v)
    rows: list[Shape] = []
    for sign_u in (-1.0, 1.0):
        for sign_v in (-1.0, 1.0):
            p0 = point_at(
                datum,
                rear - 0.30,
                u_offset=sign_u * start_u,
                v_offset=sign_v * TERMINAL_ROOT_PITCH / 2.0,
            )
            p1 = point_at(
                datum,
                rear + TERMINAL_ROOT_DEPTH + 0.20,
                u_offset=sign_u * end_u,
                v_offset=sign_v * TERMINAL_ROOT_PITCH / 2.0,
            )
            rows.append(
                oriented_box_between(
                    p0,
                    p1,
                    xyz(v_axis),
                    channel_v,
                    channel_t,
                    label=f"{datum.name}_root_{'p' if sign_u > 0 else 'n'}u_{'p' if sign_v > 0 else 'n'}v",
                )
            )
    return tuple(rows)


def wire_exit_cutter(datum: ControlDatum, front_depth: float) -> Shape:
    rear = front_depth + SWITCH_BODY_H
    return oriented_box(
        datum,
        WIRE_EXIT_U,
        WIRE_EXIT_V,
        rear - 0.25,
        rear + CARRIER_REAR_PLATE + 0.30,
        label=f"{datum.name}_wire_exit_tool",
    )


def wire_envelope(datum: ControlDatum, front_depth: float) -> Shape:
    rear = front_depth + SWITCH_BODY_H
    return oriented_box(
        datum,
        WIRE_EXIT_U,
        WIRE_EXIT_V,
        rear + CARRIER_REAR_PLATE - 0.10,
        rear + CARRIER_REAR_PLATE + WIRE_STRAIGHT_LENGTH,
        label=f"{datum.name}_wire_service_envelope",
    )


def build_individual_carrier(datum: ControlDatum, front_depth: float) -> Shape:
    rear = front_depth + SWITCH_BODY_H
    outer = oriented_box(
        datum,
        CARRIER_OUTER_X,
        CARRIER_OUTER_Y,
        front_depth - 0.20,
        rear + CARRIER_REAR_PLATE,
        label=f"{datum.name}_carrier_outer",
    )
    pocket = oriented_box(
        datum,
        SWITCH_POCKET_X,
        SWITCH_POCKET_Y,
        front_depth - 0.40,
        rear + 0.12,
        label=f"{datum.name}_complete_pocket_tool",
    )
    result = outer - pocket

    # Open the seam-facing side through the housing length.  The rear plate
    # and two broad corner rails remain, so shell closure provides the fourth
    # lateral restraint without a hook or snap finger.
    access_width = CARRIER_WALL + SIDE_ACCESS_EXTRA
    access_offset = datum.open_side_sign * (SWITCH_POCKET_X / 2.0 + CARRIER_WALL / 2.0)
    access = oriented_box(
        datum,
        access_width,
        SWITCH_POCKET_Y + 2.0 * SIDE_ACCESS_EXTRA,
        front_depth - 0.45,
        rear + 0.18,
        u_offset=access_offset,
        label=f"{datum.name}_lateral_insertion_tool",
    )
    result = result - access
    for cutter in terminal_root_cutters(datum, front_depth):
        result = result - cutter
    result = result - wire_exit_cutter(datum, front_depth)
    result = result.clean()
    result.label = f"{datum.name}_C_channel_carrier"
    return result


def _complete_pocket_cutter(datum: ControlDatum, front_depth: float) -> Shape:
    rear = front_depth + SWITCH_BODY_H
    return oriented_box(
        datum,
        SWITCH_POCKET_X,
        SWITCH_POCKET_Y,
        front_depth - 0.45,
        rear + 0.20,
        label=f"{datum.name}_shared_complete_pocket_tool",
    )


def build_pair_carrier(
    label: str,
    left_name: str,
    right_name: str,
    controls: dict[str, ControlDatum],
    depths: dict[str, float],
) -> Shape:
    left = controls[left_name]
    right = controls[right_name]
    first = build_individual_carrier(left, depths[left_name])
    second = build_individual_carrier(right, depths[right_name])
    rear1 = depths[left_name] + SWITCH_BODY_H + 0.80
    rear2 = depths[right_name] + SWITCH_BODY_H + 0.80
    # Put the bridge on one broad outer rail, away from the central rear wire
    # exits.  The 3.8 mm v offset penetrates each 1.6 mm carrier wall.
    p0 = np.asarray(point_at(left, rear1, v_offset=3.80), dtype=float)
    p1 = np.asarray(point_at(right, rear2, v_offset=3.80), dtype=float)
    direction = unit(p1 - p0)
    bridge = oriented_box_between(
        xyz(p0 - direction * BRIDGE_PENETRATION),
        xyz(p1 + direction * BRIDGE_PENETRATION),
        xyz(-unit(np.asarray(left.axis) + np.asarray(right.axis))),
        BRIDGE_SECTION,
        BRIDGE_SECTION,
        label=f"{label}_broad_side_bridge",
    )
    result = first.fuse(second).fuse(bridge)
    # Re-cut every functional void after the union.  This prevents the bridge
    # from intruding into either switch, terminal root or wire service path.
    for datum in (left, right):
        result = result - _complete_pocket_cutter(datum, depths[datum.name])
        for cutter in terminal_root_cutters(datum, depths[datum.name]):
            result = result - cutter
        result = result - wire_exit_cutter(datum, depths[datum.name])
        result = result - wire_envelope(datum, depths[datum.name])
    result = result.clean()
    result.label = label
    return result


def build_cap(datum: ControlDatum, front_depth: float) -> Shape:
    pad = oriented_box(
        datum,
        CAP_SIZE,
        CAP_SIZE,
        -CAP_EXPOSURE,
        -CAP_EXPOSURE + CAP_THICKNESS,
        cap_frame=True,
        label=f"{datum.name}_cap_pad",
    )
    actuator_top = front_depth - ACTUATOR_PROJECTION
    boss_rear = min(front_depth - 0.45, actuator_top + 1.35)
    boss = oriented_cylinder(
        datum,
        CAP_BOSS_DIAMETER,
        -CAP_EXPOSURE + CAP_THICKNESS - 0.10,
        boss_rear,
        cap_frame=True,
        label=f"{datum.name}_cap_boss",
    )
    socket = oriented_cylinder(
        datum,
        CAP_SOCKET_DIAMETER,
        actuator_top - CAP_CONTACT_FREE_GAP,
        boss_rear + 0.10,
        cap_frame=True,
        label=f"{datum.name}_actuator_socket_tool",
    )
    result = pad.fuse(boss) - socket
    result = result.clean()
    result.label = f"{datum.name}_cap"
    return result


def build_switch_reference(datum: ControlDatum, front_depth: float) -> Compound:
    body = switch_body(datum, front_depth)
    actuator = switch_actuator(datum, front_depth)
    roots = terminal_root_cutters(datum, front_depth)
    return Compound(children=[body, actuator, *roots], label=f"{datum.name}_ITS1105_reference")


def cut_shells(layout, controls: tuple[ControlDatum, ...]) -> tuple[Shape, Shape, dict[str, Shape]]:
    jad = layout.jad
    jfd = layout.jfd
    cutters = {datum.name: opening_cutter(datum) for datum in controls}
    for cutter in cutters.values():
        if intersection_volume(jad, cutter) > BOOLEAN_VOLUME_EPS:
            jad = jad - cutter
        if intersection_volume(jfd, cutter) > BOOLEAN_VOLUME_EPS:
            jfd = jfd - cutter
    jad = jad.clean()
    jfd = jfd.clean()
    jad.label = "JAD_FINGER_V2"
    jfd.label = "JFD_FINGER_V2"
    return jad, jfd, cutters


def _carrier_collision(carrier: Shape, jad: Shape, jfd: Shape) -> float:
    return max(intersection_volume(carrier, jad), intersection_volume(carrier, jfd))


def choose_front_depths(
    controls: tuple[ControlDatum, ...],
    jad_cut: Shape,
    jfd_cut: Shape,
) -> dict[str, float]:
    depths: dict[str, float] = {}
    for datum in controls:
        selected = None
        for front in np.arange(CARRIER_FRONT_SEED, CARRIER_FRONT_LIMIT + 0.001, CARRIER_FRONT_STEP):
            candidate = build_individual_carrier(datum, float(front))
            body = switch_body(datum, float(front))
            collision = max(
                _carrier_collision(candidate, jad_cut, jfd_cut),
                intersection_volume(body, jad_cut),
                intersection_volume(body, jfd_cut),
            )
            if collision <= BOOLEAN_VOLUME_EPS:
                distances = [
                    exact_distance(candidate, jad_cut),
                    exact_distance(candidate, jfd_cut),
                    exact_distance(body, jad_cut),
                    exact_distance(body, jfd_cut),
                ]
                if min(distances) >= CARRIER_SHELL_GAP - 0.01:
                    selected = float(front)
                    break
        if selected is None:
            raise RuntimeError(f"{datum.name}: no collision-free carrier depth through {CARRIER_FRONT_LIMIT:.2f} mm")
        depths[datum.name] = selected

    # The N1/N2 bridge is evaluated as a real fused body.  Move both switches
    # inward together only if the bridge needs more clean-shell clearance.
    while True:
        shared = build_pair_carrier(
            "N1_N2_shared_C_channel_carrier",
            "N1",
            "N2",
            {row.name: row for row in controls},
            depths,
        )
        if _carrier_collision(shared, jad_cut, jfd_cut) <= BOOLEAN_VOLUME_EPS:
            break
        depths["N1"] += CARRIER_FRONT_STEP
        depths["N2"] += CARRIER_FRONT_STEP
        if max(depths["N1"], depths["N2"]) > CARRIER_FRONT_LIMIT:
            raise RuntimeError("N1/N2 shared carrier cannot clear the clean shells")
    return depths


def screw_keep_out_solids() -> dict[str, Shape]:
    rows: dict[str, Shape] = {}
    for name, (center, x_range, radius) in SCREW_KEEP_OUTS.items():
        x0, x1 = x_range
        origin = (0.5 * (x0 + x1), center[1], center[2])
        plane = Plane(origin=origin, x_dir=(0.0, 1.0, 0.0), z_dir=(1.0, 0.0, 0.0))
        solid = plane.location * Cylinder(
            radius,
            x1 - x0,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
        solid.label = f"screw_{name}_keep_out"
        rows[name] = solid
    return rows


def trim_carrier_to_split(shape: Shape, owner: str) -> Shape:
    """Keep a 0.20 mm setback on each side of the nominal X=0 split.

    N2's purpose-designed JfD carrier is intentionally not passed through
    this helper; its separate opposite-shell clearance gate remains primary.
    """
    if owner == "JfD":
        keep = Box(
            200.0,
            400.0,
            400.0,
            align=(Align.MAX, Align.CENTER, Align.CENTER),
        ).moved(Location(Vector(-SPLIT_CARRIER_CLEARANCE, 0.0, 0.0)))
    elif owner == "JaD":
        keep = Box(
            200.0,
            400.0,
            400.0,
            align=(Align.MIN, Align.CENTER, Align.CENTER),
        ).moved(Location(Vector(SPLIT_CARRIER_CLEARANCE, 0.0, 0.0)))
    else:
        raise ValueError(owner)
    result = (shape & keep).clean()
    result.label = shape.label
    return result


@dataclass(slots=True)
class FingerControlsV2:
    layout: object
    controls: tuple[ControlDatum, ...]
    front_depths: dict[str, float]
    jad_shell: Shape
    jfd_shell: Shape
    opening_cutters: dict[str, Shape]
    carriers: dict[str, Shape]
    caps: dict[str, Shape]
    switch_references: dict[str, Compound]
    wire_envelopes: dict[str, Shape]
    screw_keep_outs: dict[str, Shape]

    @property
    def printable_parts(self) -> dict[str, Shape]:
        return {**self.carriers, **{f"{name}_cap": shape for name, shape in self.caps.items()}}

    @property
    def assembly_reference(self) -> Compound:
        children: list[Shape] = [self.jad_shell, self.jfd_shell]
        children.extend(self.layout.visible_thumb)
        children.extend(self.carriers.values())
        children.extend(self.caps.values())
        children.extend(self.switch_references.values())
        return Compound(children=children, label="ONEGRIP_FINGER_CONTROLS_V2_ASSEMBLY")


def build_finger_controls_v2(*, rederive_depths: bool = False) -> FingerControlsV2:
    layout = build_layout()
    controls = controls_from_layout()
    jad_cut, jfd_cut, cutters = cut_shells(layout, controls)
    depths = (
        choose_front_depths(controls, jad_cut, jfd_cut)
        if rederive_depths
        else dict(FROZEN_FRONT_DEPTHS)
    )
    by_name = {datum.name: datum for datum in controls}
    carriers: dict[str, Shape] = {
        "N1_N2_shared_carrier": build_pair_carrier(
            "N1_N2_shared_C_channel_carrier", "N1", "N2", by_name, depths
        ),
        "I2_I3_shared_carrier": build_pair_carrier(
            "I2_I3_shared_C_channel_carrier", "I2", "I3", by_name, depths
        ),
        "M4_N3_shared_carrier": trim_carrier_to_split(
            build_pair_carrier(
                "M4_N3_shared_C_channel_carrier", "M4", "N3", by_name, depths
            ),
            "JaD",
        ),
    }
    carriers["I4_carrier"] = build_individual_carrier(by_name["I4"], depths["I4"])
    carriers["M3_carrier"] = trim_carrier_to_split(
        build_individual_carrier(by_name["M3"], depths["M3"]),
        "JfD",
    )
    caps = {datum.name: build_cap(datum, depths[datum.name]) for datum in controls}
    switches = {
        datum.name: build_switch_reference(datum, depths[datum.name]) for datum in controls
    }
    wires = {datum.name: wire_envelope(datum, depths[datum.name]) for datum in controls}
    return FingerControlsV2(
        layout=layout,
        controls=controls,
        front_depths=depths,
        jad_shell=jad_cut,
        jfd_shell=jfd_cut,
        opening_cutters=cutters,
        carriers=carriers,
        caps=caps,
        switch_references=switches,
        wire_envelopes=wires,
        screw_keep_outs=screw_keep_out_solids(),
    )


def _shift_to_plate(shape: Shape, x_cursor: float, y_cursor: float) -> Shape:
    bbox = shape.bounding_box()
    dx = x_cursor - float(bbox.min.X)
    dy = y_cursor - float(bbox.min.Y)
    dz = -float(bbox.min.Z)
    return shape.moved(Location(Vector(dx, dy, dz)))


def make_print_plate(design: FingerControlsV2, spacing: float = 6.0) -> Compound:
    # Local-frame reorientation makes each cap face-down and each C-channel
    # rear plate flat.  The N1/N2 carrier uses N1's nearly parallel frame.
    controls = {row.name: row for row in design.controls}
    local_parts: list[tuple[str, Shape]] = []
    for name, shape in design.carriers.items():
        datum_name = name.split("_")[0]
        datum = controls[datum_name]
        plane = Plane(origin=datum.center, x_dir=datum.switch_u, z_dir=tuple(-unit(datum.axis)))
        local_parts.append((name, plane.to_local_coords(shape)))
    for name, shape in design.caps.items():
        datum = controls[name]
        plane = Plane(origin=datum.center, x_dir=datum.cap_u, z_dir=datum.axis)
        local_parts.append((f"{name}_cap", plane.to_local_coords(shape)))

    rows: list[Shape] = []
    x_cursor = 0.0
    y_cursor = 0.0
    row_height = 0.0
    plate_width = 105.0
    for name, shape in local_parts:
        bbox = shape.bounding_box()
        width = float(bbox.size.X)
        depth = float(bbox.size.Y)
        if x_cursor > 0.0 and x_cursor + width > plate_width:
            x_cursor = 0.0
            y_cursor += row_height + spacing
            row_height = 0.0
        moved = _shift_to_plate(shape, x_cursor, y_cursor)
        moved.label = name
        rows.append(moved)
        x_cursor += width + spacing
        row_height = max(row_height, depth)
    return Compound(children=rows, label="FINGER_V2_PRINT_PLATE")


def export_design(design: FingerControlsV2, out_dir: Path = OUT_DIR) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    exports: dict[str, str] = {}

    for name, shell in (("JAD_FINGER_V2", design.jad_shell), ("JFD_FINGER_V2", design.jfd_shell)):
        path = out_dir / f"{name}.step"
        export_step(shell, path)
        exports[name] = str(path)

    for name, shape in design.carriers.items():
        for suffix, exporter in (("step", export_step), ("stl", export_stl)):
            path = out_dir / f"{name}.{suffix}"
            if suffix == "step":
                exporter(shape, path)
            else:
                exporter(shape, path, tolerance=0.025, angular_tolerance=0.06)
            exports[f"{name}.{suffix}"] = str(path)

    for name, shape in design.caps.items():
        for suffix, exporter in (("step", export_step), ("stl", export_stl)):
            path = out_dir / f"{name}_cap.{suffix}"
            if suffix == "step":
                exporter(shape, path)
            else:
                exporter(shape, path, tolerance=0.025, angular_tolerance=0.06)
            exports[f"{name}_cap.{suffix}"] = str(path)

    assembly = out_dir / "FINGER_V2_ASSEMBLY_REFERENCE.step"
    export_step(design.assembly_reference, assembly)
    exports["assembly"] = str(assembly)

    plate = make_print_plate(design)
    plate_path = out_dir / "FINGER_V2_PRINT_PLATE.stl"
    export_stl(plate, plate_path, tolerance=0.025, angular_tolerance=0.06)
    exports["printPlate"] = str(plate_path)

    source_manifest = {
        "schema": 1,
        "mode": "LOCAL build123d + OCCT / Onshape 0",
        "externalLayout": "APPROVED / FROZEN",
        "buttonOrder": list(BUTTON_ORDER),
        "frontDepthsMm": design.front_depths,
        "controls": {
            row.name: {
                "centerMm": list(row.center),
                "shellNormal": list(row.shell_normal),
                "axis": list(row.axis),
                "owner": row.owner,
                "kind": row.kind,
                "capU": list(row.cap_u),
                "switchU": list(row.switch_u),
                "rollDeg": row.roll_deg,
            }
            for row in design.controls
        },
        "carrierParts": list(design.carriers),
        "exports": exports,
    }
    manifest_path = out_dir / "finger_controls_v2_source_manifest.json"
    manifest_path.write_text(
        json.dumps(source_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    exports["sourceManifest"] = str(manifest_path)
    return exports


def main() -> None:
    design = build_finger_controls_v2()
    exports = export_design(design)
    print("front depths", design.front_depths)
    print("carriers", list(design.carriers))
    print("exports", len(exports), OUT_DIR)


if __name__ == "__main__":
    main()
