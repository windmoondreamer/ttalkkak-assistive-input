"""Parameterized build123d-first MIDDLE carrier redesign.

This module deliberately contains no Onshape client or mutation code.  The
geometry is developed as exact OCC solids first; the immutable INDEX and
shell data are consumed only by the separate validation script as obstacles.

All dimensions are millimetres.  ``axis`` points out of the shell and depth
is measured inward along ``-axis`` from the exterior shell surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
from pathlib import Path
from typing import Iterable

from build123d import Align, Box, Compound, Cylinder, Plane, Shape

from .model import add, cross, dot, norm, normalize, oriented_box_between, scale, subtract
from .source_of_truth import Vec3


# ---------------------------------------------------------------------------
# Manufacturing and hardware parameters
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
OPENING_SIZE = 8.00
CAP_EXPOSURE = 1.00
CAP_PAD_THICKNESS = 1.20
CAP_SKIRT_OUTER = 7.20
CAP_SKIRT_INNER = 4.40
CAP_SKIRT_REAR = 3.80
CAP_TAB_OUTER = 9.60
CAP_TAB_INNER = 7.20
CAP_TAB_SPAN = 3.20
CAP_TAB_FRONT = 3.05
CAP_TAB_REAR = 4.25
CAP_CONTACT_DIAMETER = 3.80
CAP_CONTACT_FREE_GAP = 0.05

SHELL_WALL_NOMINAL = 3.00
SWITCH_FRONT_DEPTH = 4.40
SWITCH_REAR_DEPTH = SWITCH_FRONT_DEPTH + SWITCH_BODY_H

CARRIER_WALL = 1.60
CARRIER_OUTER_X = SWITCH_POCKET_X + 2.0 * CARRIER_WALL
CARRIER_OUTER_Y = SWITCH_POCKET_Y + 2.0 * CARRIER_WALL
FRONT_RING_FRONT = 4.85
FRONT_RING_REAR = 6.45
COLUMN_REAR = 12.40
STOP_FRONT = SWITCH_REAR_DEPTH
STOP_REAR = 8.90
STOP_WIDTH = CARRIER_OUTER_X
STOP_DEPTH = 1.60
BACKBONE_SECTION = 3.20
BACKBONE_DEPTH = 11.50
BACKBONE_SIDE_OFFSET = 4.00

TERMINAL_ROOT_DEPTH = 1.80
TERMINAL_ROOT_OUTER = 7.90
TERMINAL_ROOT_PITCH = 4.50
TERMINAL_METAL_U = 0.30
TERMINAL_METAL_V = 0.70
TERMINAL_CLEARANCE = 0.08
WIRE_EXIT_DEPTH = 12.00
WIRE_ENVELOPE_U = 4.00
WIRE_ENVELOPE_V = 3.20

MIN_SWITCH_SAT = 1.20
MIN_DIVIDER = 0.80
MIN_SPLIT_OWNERSHIP = 1.50
MIN_STRUCTURAL_WEB = 1.20
PREFERRED_CARRIER_WALL = 1.60
MIN_SCREW_CLEARANCE = 2.50


# The new continuous shell row is sampled at Z=-11.125 mm.  Its arc stations
# are (-32.0, -19.5, -7.0 | +7.5) mm.  M4 is deliberately separated because
# it belongs to the opposite shell half and its carrier remains independent.


@dataclass(frozen=True, slots=True)
class MiddleDatum:
    name: str
    center: Vec3
    shell_normal: Vec3
    roll_deg: int
    shell_owner: str
    arc_station: float

    @property
    def axis(self) -> Vec3:
        # Primary architecture rule: cap travel, shell normal and switch axis
        # are coincident.  This removes the former 20--25 degree side load.
        return normalize(self.shell_normal)


MIDDLE_DATUMS: tuple[MiddleDatum, ...] = (
    MiddleDatum(
        "M1",
        (-20.441891909778107, 4.808880134986816, -11.125),
        (-0.992161445973124, -0.028542071086963765, -0.12165942340232677),
        90,
        "JfD",
        -32.0,
    ),
    MiddleDatum(
        "M2",
        (-17.213379782242022, -7.0844962813799075, -11.125),
        (-0.7163604291732192, -0.5283578070189137, -0.45570359146810097),
        90,
        "JfD",
        -19.5,
    ),
    MiddleDatum(
        "M3",
        (-6.893458811961845, -13.725680237329435, -11.125),
        (-0.22425959856820332, -0.7717941811500879, -0.5950137598349249),
        0,
        "JfD",
        -7.0,
    ),
    MiddleDatum(
        "M4",
        (7.383060988607427, -13.587450184483213, -11.125),
        (0.22485912746543743, -0.7727927739559164, -0.5934894281425763),
        0,
        "JaD",
        7.5,
    ),
)


def frame(datum: MiddleDatum) -> tuple[Vec3, Vec3, Vec3]:
    """Return roll-adjusted (u, v, outward axis) world directions."""
    z = datum.axis
    u0 = cross((0.0, 0.0, 1.0), z)
    if norm(u0) <= 1e-9:
        u0 = cross((0.0, 1.0, 0.0), z)
    u0 = normalize(u0)
    v0 = normalize(cross(z, u0))
    angle = radians(datum.roll_deg)
    u = add(scale(u0, cos(angle)), scale(v0, sin(angle)))
    v = add(scale(u0, -sin(angle)), scale(v0, cos(angle)))
    return normalize(u), normalize(v), z


def point_at(
    datum: MiddleDatum,
    *,
    depth: float,
    u_offset: float = 0.0,
    v_offset: float = 0.0,
) -> Vec3:
    u, v, axis = frame(datum)
    return add(
        subtract(datum.center, scale(axis, depth)),
        add(scale(u, u_offset), scale(v, v_offset)),
    )


def oriented_box(
    datum: MiddleDatum,
    width_u: float,
    width_v: float,
    front_depth: float,
    rear_depth: float,
    *,
    u_offset: float = 0.0,
    v_offset: float = 0.0,
    label: str,
) -> Shape:
    """Create a centered box in a button's local (u, v, inward) frame."""
    if rear_depth <= front_depth:
        raise ValueError(f"{label}: rear_depth must exceed front_depth")
    u, _v, axis = frame(datum)
    origin = point_at(
        datum,
        depth=(front_depth + rear_depth) / 2.0,
        u_offset=u_offset,
        v_offset=v_offset,
    )
    plane = Plane(origin=origin, x_dir=u, z_dir=scale(axis, -1.0))
    result = plane.location * Box(
        width_u,
        width_v,
        rear_depth - front_depth,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    result.label = label
    return result


def oriented_cylinder(
    datum: MiddleDatum,
    diameter: float,
    front_depth: float,
    rear_depth: float,
    *,
    label: str,
) -> Shape:
    u, _v, axis = frame(datum)
    origin = point_at(datum, depth=(front_depth + rear_depth) / 2.0)
    plane = Plane(origin=origin, x_dir=u, z_dir=scale(axis, -1.0))
    result = plane.location * Cylinder(
        diameter / 2.0,
        rear_depth - front_depth,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    result.label = label
    return result


def fuse_all(shapes: Iterable[Shape], *, label: str) -> Shape:
    rows = list(shapes)
    if not rows:
        raise ValueError(f"{label}: cannot fuse an empty sequence")
    result = rows[0]
    for row in rows[1:]:
        result = result.fuse(row)
    result = result.clean()
    result.label = label
    return result


@dataclass(slots=True)
class Cradle:
    datum: MiddleDatum
    components: dict[str, Shape]
    solid: Shape


def build_cradle(datum: MiddleDatum) -> Cradle:
    outer = oriented_box(
        datum,
        CARRIER_OUTER_X,
        CARRIER_OUTER_Y,
        FRONT_RING_FRONT,
        FRONT_RING_REAR,
        label=f"{datum.name}_front_ring_outer",
    )
    passage = oriented_box(
        datum,
        SWITCH_POCKET_X,
        SWITCH_POCKET_Y,
        FRONT_RING_FRONT - 0.20,
        FRONT_RING_REAR + 0.20,
        label=f"{datum.name}_pocket_tool",
    )
    ring = (outer - passage).clean()
    ring.label = f"{datum.name}_front_ring"
    components: dict[str, Shape] = {"front_ring": ring}

    corner_offset_u = SWITCH_POCKET_X / 2.0 + CARRIER_WALL / 2.0
    corner_offset_v = SWITCH_POCKET_Y / 2.0 + CARRIER_WALL / 2.0
    for sign_u in (-1.0, 1.0):
        for sign_v in (-1.0, 1.0):
            key = f"column_{'p' if sign_u > 0 else 'n'}u_{'p' if sign_v > 0 else 'n'}v"
            components[key] = oriented_box(
                datum,
                CARRIER_WALL,
                CARRIER_WALL,
                FRONT_RING_REAR - 0.20,
                COLUMN_REAR,
                u_offset=sign_u * corner_offset_u,
                v_offset=sign_v * corner_offset_v,
                label=f"{datum.name}_{key}",
            )

    # Two broad rear ledges support the switch housing while leaving both
    # terminal sides and the central solder/wiring volume open.
    # The 0.44 mm inward bearing lip supports the body.  The resulting bar
    # starts at |v|=2.76 mm, leaving 0.08 mm around the conservative terminal
    # root channel whose outer edge is |v|=2.68 mm.
    stop_v = CARRIER_OUTER_Y / 2.0 - STOP_DEPTH / 2.0 - 0.44
    for sign_v in (-1.0, 1.0):
        key = f"rear_stop_{'p' if sign_v > 0 else 'n'}v"
        components[key] = oriented_box(
            datum,
            STOP_WIDTH,
            STOP_DEPTH,
            STOP_FRONT,
            STOP_REAR,
            v_offset=sign_v * stop_v,
            label=f"{datum.name}_{key}",
        )

    solid = fuse_all(components.values(), label=f"{datum.name}_cradle")
    return Cradle(datum, components, solid)


def terminal_root_cutters(datum: MiddleDatum) -> tuple[Shape, ...]:
    """Return conservative rigid-root clearance tools for all four pins.

    Only the factory-fixed root is treated as rigid.  The distal pin and wire
    are permitted to be pre-formed and routed through the open rear cavity.
    """
    u, v, _axis = frame(datum)
    start_u = SWITCH_BODY_X / 2.0 + TERMINAL_METAL_U / 2.0
    knee_u = (TERMINAL_ROOT_OUTER - TERMINAL_METAL_U) / 2.0
    channel_v = TERMINAL_METAL_V + 2.0 * TERMINAL_CLEARANCE
    channel_t = TERMINAL_METAL_U + 2.0 * TERMINAL_CLEARANCE
    rows: list[Shape] = []
    for sign_u in (-1.0, 1.0):
        for sign_v in (-1.0, 1.0):
            p0 = point_at(
                datum,
                depth=SWITCH_REAR_DEPTH - 0.10,
                u_offset=sign_u * start_u,
                v_offset=sign_v * TERMINAL_ROOT_PITCH / 2.0,
            )
            p1 = point_at(
                datum,
                depth=SWITCH_REAR_DEPTH + TERMINAL_ROOT_DEPTH + 0.10,
                u_offset=sign_u * knee_u,
                v_offset=sign_v * TERMINAL_ROOT_PITCH / 2.0,
            )
            rows.append(
                oriented_box_between(
                    p0,
                    p1,
                    v,
                    channel_v,
                    channel_t,
                    label=(
                        f"{datum.name}_root_clearance_"
                        f"{'p' if sign_u > 0 else 'n'}u_"
                        f"{'p' if sign_v > 0 else 'n'}v"
                    ),
                )
            )
    return tuple(rows)


def pocket_cutter(datum: MiddleDatum) -> Shape:
    return oriented_box(
        datum,
        SWITCH_POCKET_X,
        SWITCH_POCKET_Y,
        SWITCH_FRONT_DEPTH - 0.20,
        SWITCH_REAR_DEPTH,
        label=f"{datum.name}_complete_pocket_tool",
    )


@dataclass(slots=True)
class Carrier:
    name: str
    shell_owner: str
    cradles: tuple[Cradle, ...]
    components: dict[str, Shape]
    solid: Shape


def backbone_node(datum: MiddleDatum) -> Vec3:
    _u, v, _axis = frame(datum)
    return add(
        point_at(datum, depth=BACKBONE_DEPTH),
        scale(v, BACKBONE_SIDE_OFFSET),
    )


def build_shared_carrier() -> Carrier:
    cradles = tuple(build_cradle(datum) for datum in MIDDLE_DATUMS[:3])
    components: dict[str, Shape] = {
        cradle.datum.name: cradle.solid for cradle in cradles
    }
    # The bridge is on the non-wiring side.  Each end penetrates the robust
    # outer column, guaranteeing a positive-volume union rather than a
    # tangent-only connection.
    for left, right in zip(cradles, cradles[1:]):
        p0 = backbone_node(left.datum)
        p1 = backbone_node(right.datum)
        delta = subtract(p1, p0)
        extension = min(0.90, norm(delta) * 0.08)
        direction = normalize(delta)
        bridge = oriented_box_between(
            subtract(p0, scale(direction, extension)),
            add(p1, scale(direction, extension)),
            scale(add(left.datum.axis, right.datum.axis), -1.0),
            BACKBONE_SECTION,
            BACKBONE_SECTION,
            label=f"{left.datum.name}_{right.datum.name}_backbone",
        )
        components[f"{left.datum.name}_{right.datum.name}_backbone"] = bridge
    solid = fuse_all(components.values(), label="M1_M2_M3_shared_carrier_raw")
    # The independently oriented cradle envelopes overlap by design.  Carve
    # every complete pocket and rigid terminal root after the union so the
    # shared divider is the actual remaining material, not overlapping tool
    # bodies that intrude into a neighbouring switch.
    for cradle in cradles:
        solid = solid - pocket_cutter(cradle.datum)
        for cutter in terminal_root_cutters(cradle.datum):
            solid = solid - cutter
    solid = solid.clean()
    solid.label = "M1_M2_M3_shared_carrier"
    return Carrier("M1_M2_M3_shared_carrier", "JfD", cradles, components, solid)


def build_m4_carrier() -> Carrier:
    cradle = build_cradle(MIDDLE_DATUMS[3])
    # Two broad keyed pads replace a fragile snap hook.  They remain part of
    # the single carrier solid and provide the future shell-interface faces.
    datum = cradle.datum
    keys: dict[str, Shape] = {}
    for sign_u in (-1.0, 1.0):
        key = f"keyed_stop_{'p' if sign_u > 0 else 'n'}u"
        keys[key] = oriented_box(
            datum,
            3.20,
            CARRIER_WALL,
            9.80,
            12.20,
            u_offset=sign_u * 4.20,
            v_offset=BACKBONE_SIDE_OFFSET,
            label=f"M4_{key}",
        )
    components = {"M4": cradle.solid, **keys}
    solid = fuse_all(components.values(), label="M4_single_carrier_raw")
    solid = solid - pocket_cutter(datum)
    for cutter in terminal_root_cutters(datum):
        solid = solid - cutter
    solid = solid.clean()
    solid.label = "M4_single_carrier"
    return Carrier("M4_single_carrier", "JaD", (cradle,), components, solid)


def build_cap(datum: MiddleDatum) -> Shape:
    pad = oriented_box(
        datum,
        CAP_SIZE,
        CAP_SIZE,
        -CAP_EXPOSURE,
        -CAP_EXPOSURE + CAP_PAD_THICKNESS,
        label=f"{datum.name}_cap_pad",
    )
    skirt_outer = oriented_box(
        datum,
        CAP_SKIRT_OUTER,
        CAP_SKIRT_OUTER,
        0.10,
        CAP_SKIRT_REAR,
        label=f"{datum.name}_cap_skirt_outer",
    )
    skirt_inner = oriented_box(
        datum,
        CAP_SKIRT_INNER,
        CAP_SKIRT_INNER,
        0.00,
        CAP_SKIRT_REAR + 0.10,
        label=f"{datum.name}_cap_skirt_tool",
    )
    skirt = (skirt_outer - skirt_inner).clean()
    skirt.label = f"{datum.name}_cap_skirt"

    tab_width = (CAP_TAB_OUTER - CAP_TAB_INNER) / 2.0
    tab_offset = CAP_TAB_INNER / 2.0 + tab_width / 2.0
    tabs = [
        oriented_box(
            datum,
            tab_width,
            CAP_TAB_SPAN,
            CAP_TAB_FRONT,
            CAP_TAB_REAR,
            u_offset=sign * tab_offset,
            label=f"{datum.name}_cap_tab_{'p' if sign > 0 else 'n'}u",
        )
        for sign in (-1.0, 1.0)
    ]
    actuator_top_depth = SWITCH_FRONT_DEPTH - ACTUATOR_PROJECTION
    contact_rear = actuator_top_depth - CAP_CONTACT_FREE_GAP
    contact = oriented_cylinder(
        datum,
        CAP_CONTACT_DIAMETER,
        -CAP_EXPOSURE + CAP_PAD_THICKNESS - 0.10,
        contact_rear,
        label=f"{datum.name}_broad_contact",
    )
    return fuse_all((pad, skirt, *tabs, contact), label=f"{datum.name}_cap")


def build_switch_envelope(datum: MiddleDatum) -> Shape:
    body = oriented_box(
        datum,
        SWITCH_BODY_X,
        SWITCH_BODY_Y,
        SWITCH_FRONT_DEPTH,
        SWITCH_REAR_DEPTH,
        label=f"{datum.name}_ITS1105_body",
    )
    actuator = oriented_cylinder(
        datum,
        ACTUATOR_DIAMETER,
        SWITCH_FRONT_DEPTH - ACTUATOR_PROJECTION,
        SWITCH_FRONT_DEPTH,
        label=f"{datum.name}_ITS1105_actuator",
    )
    return fuse_all((body, actuator), label=f"{datum.name}_ITS1105_envelope")


@dataclass(slots=True)
class MiddleRedesign:
    shared_carrier: Carrier
    m4_carrier: Carrier
    caps: tuple[Shape, ...]
    switches: tuple[Shape, ...]

    @property
    def printable_parts(self) -> tuple[Shape, ...]:
        return (self.shared_carrier.solid, self.m4_carrier.solid, *self.caps)

    @property
    def assembly_reference(self) -> Compound:
        return Compound(
            children=[*self.printable_parts, *self.switches],
            label="MIDDLE_build123d_design_reference",
        )


def build_middle_redesign() -> MiddleRedesign:
    return MiddleRedesign(
        shared_carrier=build_shared_carrier(),
        m4_carrier=build_m4_carrier(),
        caps=tuple(build_cap(datum) for datum in MIDDLE_DATUMS),
        switches=tuple(build_switch_envelope(datum) for datum in MIDDLE_DATUMS),
    )


OUT_DIR = Path(__file__).resolve().parent / "out" / "middle_redesign"
