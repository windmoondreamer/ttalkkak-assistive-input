"""Functional comparator mechanisms for OneGrip Play finger cartridges.

This module deliberately lives beside, rather than inside,
``finger_module_common.py``.  It imports the common switch and finger
parameters but does not change the production-candidate Variant B geometry.

Coordinate system
-----------------
X is the lateral LEFT/RIGHT direction, Y is distal/proximal, and +Z points
toward the finger pad.  All dimensions are millimetres.

Important prototype assumptions
-------------------------------
* The Panasonic EVQ-P0E07K operating travel is specified only as a maximum.
  Therefore no fixed stop can guarantee both actuation and safe overtravel for
  every switch.  The models provide a nominal 0.80 mm mechanical stop gap and
  a replaceable calibration shim.  Measure each physical switch, then choose
  ``shim = 0.80 - (measured operating travel + desired overtravel)``.  The
  default 0.18 mm shim produces 0.62 mm total travel and is a *drawing
  reference for PET/polyester shim stock*, not a reliable single-layer FDM
  print.  A 0.20 mm coarse FDM coupon is also returned.
* The switch terminal model assumes two axial terminals on 5.0 mm pitch.  The
  terminal relief is intentionally generous and must be checked against the
  purchased switch lot before committing a production enclosure.
* Variant C uses a removable 2.0 mm steel shaft through two vertical slots.
  The switch springs provide return force in P0; a thin TPU dust/return boot
  may be added after the kinematic test but is intentionally not relied upon.
* These are comparator cartridges for bench evaluation.  They are not a
  medical-device claim and require physical force/travel and pinch-point tests.

The public entry point :func:`build_functional_comparators` returns separated
printable parts, per-state component dictionaries, and neutral/LEFT/CENTER/
RIGHT compounds for both variants.  Nothing is exported or generated merely
by importing this file.
"""

from __future__ import annotations

from math import cos, degrees, radians, sin
from typing import Dict, Mapping

import cadquery as cq

from finger_module_common import (
    FingerPreset,
    SWITCH,
    _box,
    _concave_ellipse,
    _cyl_x,
    _cyl_y,
    _cyl_z,
    _safe_fillet,
    build_switch_placeholder,
    compound,
    mechanism_layout,
    module_dimensions,
)


# Both comparator mechanisms use the same measurable stop architecture.
BASE_STOP_GAP = 0.80
NOMINAL_SHIM_THICKNESS = 0.18
NOMINAL_TOTAL_TRAVEL = BASE_STOP_GAP - NOMINAL_SHIM_THICKNESS

# Shared dimensional conventions.  The values leave 0.35 mm clearance on
# each side of a 2.8 x 3.6 mm follower in a 3.5 x 4.3 mm printed guide.
GUIDE_STEM_X = 2.80
GUIDE_STEM_Y = 3.60
GUIDE_HOLE_X = 3.50
GUIDE_HOLE_Y = 4.30
COLLAR_X = 5.90
COLLAR_Y = 6.20
COLLAR_TOP_Z = 12.00
FOLLOWER_FLANGE_BOTTOM_Z = COLLAR_TOP_Z + BASE_STOP_GAP
FOLLOWER_TOP_Z = 13.40
RETAINING_PIN_Z = 8.35


Shape = cq.Workplane | cq.Shape
Parts = Dict[str, Shape]


def _switch_positions(p: FingerPreset) -> Mapping[str, tuple[float, float]]:
    """Return the common three-switch coordinates in a stable name order."""
    layout = mechanism_layout(p)
    return {
        "left": tuple(layout["left_switch"]),
        "center": tuple(layout["center_switch"]),
        "right": tuple(layout["right_switch"]),
    }


def _switch_model(x: float, y: float, travel: float = 0.0) -> cq.Workplane:
    """Reference-only EVQ-P0 solid with a visibly compressing cap and pins."""
    body = _box(SWITCH.width, SWITCH.depth, SWITCH.body_height, x, y, 0.0)
    cap_h = max(0.08, SWITCH.total_height - SWITCH.body_height - travel)
    cap = _box(3.4, 3.4, cap_h, x, y, SWITCH.body_height)
    # Datasheet nominal terminal pitch; pins are reference geometry, not holes.
    pins = _cyl_z(0.50, 3.0, x - 2.50, y, -3.0).union(
        _cyl_z(0.50, 3.0, x + 2.50, y, -3.0)
    )
    return body.union(cap).union(pins)


def _build_service_cover(p: FingerPreset) -> cq.Workplane:
    """Bottom cover with M2 service screws and EVQ terminal/wire relief."""
    dims = module_dimensions(p)
    outer_w = float(dims["outer_width"])
    depth = float(dims["depth"])
    thickness = 2.40
    cover = _box(outer_w, depth, thickness)

    for x, y in (
        (-outer_w / 2 + 2.4, -depth / 2 + 2.5),
        (outer_w / 2 - 2.4, -depth / 2 + 2.5),
        (-outer_w / 2 + 2.4, depth / 2 - 2.5),
        (outer_w / 2 - 2.4, depth / 2 - 2.5),
    ):
        cover = cover.cut(_cyl_z(1.15, thickness + 0.4, x, y, -0.2))
        cover = cover.cut(_cyl_z(2.15, 0.85, x, y, thickness - 0.65))

    # Two 1.6 mm holes per switch clear the nominal 1.0 mm terminals.  Shallow
    # underside channels lead all six leads to a common rear strain-relief gap.
    for x, y in _switch_positions(p).values():
        for px in (x - 2.50, x + 2.50):
            cover = cover.cut(_cyl_z(0.80, thickness + 0.4, px, y, -0.2))
            run_y = depth / 2 - y - 1.0
            cover = cover.cut(
                _box(1.65, run_y, 0.90, px, y + run_y / 2, 0.0)
            )
    cover = cover.cut(_box(11.0, 3.2, 1.4, 0, depth / 2 - 0.7, 0.0))
    return _safe_fillet(cover, "|Z", 0.65)


def _base_shell(p: FingerPreset, *, rocker_ears: bool = False) -> cq.Workplane:
    """Shared bottom-loaded shell with three independent vertical guides."""
    dims = module_dimensions(p)
    outer_w = float(dims["outer_width"])
    depth = float(dims["depth"])
    shell = _box(outer_w, depth, 10.0)

    for x, y in _switch_positions(p).values():
        shell = shell.cut(
            _box(SWITCH.pocket_width, SWITCH.pocket_depth, 7.15, x, y, -0.10)
        )
        shell = shell.cut(_box(GUIDE_HOLE_X, GUIDE_HOLE_Y, 5.50, x, y, 6.80))
        shell = shell.union(
            _box(COLLAR_X, COLLAR_Y, COLLAR_TOP_Z - 10.0, x, y, 10.0)
        )
        shell = shell.cut(
            _box(GUIDE_HOLE_X, GUIDE_HOLE_Y, 5.50, x, y, 6.80)
        )
        run_y = depth / 2 - y - 1.2
        shell = shell.cut(_box(2.2, run_y, 1.25, x, y + run_y / 2, -0.05))

    shell = shell.cut(_box(10.0, 3.0, 2.2, 0, depth / 2 - 0.6, -0.05))

    for x, y in (
        (-outer_w / 2 + 2.4, -depth / 2 + 2.5),
        (outer_w / 2 - 2.4, -depth / 2 + 2.5),
        (-outer_w / 2 + 2.4, depth / 2 - 2.5),
        (outer_w / 2 - 2.4, depth / 2 - 2.5),
    ):
        shell = shell.cut(_cyl_z(1.55, 4.4, x, y, -0.10))

    if rocker_ears:
        # The 2 mm shaft travels in a 0.62 mm vertical slot for CENTER and
        # rotates within the same slot for LEFT/RIGHT.  Front and rear ears
        # suppress yaw without constraining intended lateral tilt.
        pivot_z = C_PIVOT_Z
        slot_travel = NOMINAL_TOTAL_TRAVEL
        for ear_y in (-7.40, 7.40):
            # Start below the 10 mm shell roof so each ear fuses into the body.
            ear = _box(5.0, 2.4, 8.2, 0, ear_y, 9.55)
            upper = _cyl_y(1.25, 3.0, 0, ear_y, pivot_z)
            lower = _cyl_y(1.25, 3.0, 0, ear_y, pivot_z - slot_travel)
            bridge = _box(2.50, 3.0, slot_travel, 0, ear_y, pivot_z - slot_travel)
            shell = shell.union(ear).cut(upper.union(lower).union(bridge))
    else:
        # Variant A plungers are retained below by the removable bottom cover;
        # omitting fragile cross-window cuts keeps this comparator shell a
        # single valid FDM solid.  The service cover must be installed in use.
        pass

    tongue = _box(outer_w - 4.0, 5.0, 5.0, 0, depth / 2 + 2.0, 2.0)
    shell = shell.union(tongue)
    for x in (-5.0, 5.0):
        shell = shell.cut(_cyl_z(1.70, 7.0, x, depth / 2 + 2.0, 1.0))
    # Some OCC builds produce an invalid seam when filleting the many guide and
    # terminal-pocket vertical edges together.  The unfilleted comparator shell
    # is valid, printable, and intentionally kept as the audit reference.
    return shell


def build_calibration_shim(thickness: float = NOMINAL_SHIM_THICKNESS) -> cq.Workplane:
    """Open shim that slides around a guide stem without dismantling it.

    Thicknesses below roughly 0.20 mm should be cut from PET/polyester sheet;
    they are returned as CAD calibration references, not asserted to be
    reliably printable by a 0.4 mm FDM nozzle.
    """
    if not 0.0 < thickness < BASE_STOP_GAP:
        raise ValueError("shim thickness must be between zero and base stop gap")
    shim = _box(5.55, 5.85, thickness)
    shim = shim.cut(_box(GUIDE_HOLE_X + 0.20, GUIDE_HOLE_Y + 0.20, thickness + 0.2, z0=-0.1))
    # 1.6 mm mouth makes the ring a removable U-shaped gauge/stop.
    shim = shim.cut(_box(1.60, 3.0, thickness + 0.2, 0, -2.6, -0.1))
    return shim


def _variant_a_plunger(p: FingerPreset, name: str) -> cq.Workplane:
    """One vertically guided Variant-A plunger at its assembled coordinate."""
    if name not in ("left", "center", "right"):
        raise ValueError(name)
    x, y = _switch_positions(p)[name]
    layout = mechanism_layout(p)

    stem = _box(
        GUIDE_STEM_X,
        GUIDE_STEM_Y,
        FOLLOWER_TOP_Z - SWITCH.total_height,
        x,
        y,
        SWITCH.total_height,
    )
    flange = _box(5.25, 5.55, 0.55, x, y, FOLLOWER_FLANGE_BOTTOM_Z)
    neck = _box(3.8, 4.2, 1.40, x, y, 13.20)

    if name == "center":
        cap_w = p.center_width
        cap = _concave_ellipse(cap_w, 10.4, 2.0, x, y, 14.25, 0.55)
    else:
        cap_w = float(layout["side_width"])
        # Only the upper contact cap is angled; the guide stem and stop flange
        # remain vertical.  This avoids the binding of an angled switch body.
        cap = _concave_ellipse(cap_w, 10.0, 1.60, x, y, 14.35, 0.45)
        contact_angle = 12.0 if name == "left" else -12.0
        cap = cap.rotate((x, y, 15.15), (x, y + 1.0, 15.15), contact_angle)

    plunger = stem.union(flange).union(neck).union(cap)
    return _safe_fillet(plunger, "|Z", 0.28)


def build_variant_a_parts(p: FingerPreset) -> Parts:
    """Return separated Variant-A printable comparator parts.

    Three independent direct plungers each press one top-actuated EVQ-P0
    switch.  The screwed service cover retains the switch/plunger stack; the
    switch models are reference hardware and are not printable parts.
    """
    return {
        "shell": _base_shell(p, rocker_ears=False),
        "bottom_cover": _build_service_cover(p),
        "left_plunger": _variant_a_plunger(p, "left"),
        "center_plunger": _variant_a_plunger(p, "center"),
        "right_plunger": _variant_a_plunger(p, "right"),
        "stop_shim_0p18_reference": build_calibration_shim(0.18),
        "stop_shim_0p20_coarse_fdm": build_calibration_shim(0.20),
    }


def assembly_parts_variant_a(
    p: FingerPreset,
    state: str = "neutral",
    *,
    include_switches: bool = True,
) -> Parts:
    """Return positioned Variant-A components for a requested press state."""
    if state not in ("neutral", "left", "center", "right"):
        raise ValueError(state)

    parts = build_variant_a_parts(p)
    # Standalone shim templates are replaced by three positioned nominal shims.
    parts.pop("stop_shim_0p18_reference")
    parts.pop("stop_shim_0p20_coarse_fdm")
    parts["bottom_cover"] = parts["bottom_cover"].translate((0, 0, -2.40))

    positions = _switch_positions(p)
    for name, (x, y) in positions.items():
        parts[f"{name}_stop_shim"] = build_calibration_shim().translate(
            (x, y, COLLAR_TOP_Z)
        )

    active = state if state != "neutral" else None
    if active:
        parts[f"{active}_plunger"] = parts[f"{active}_plunger"].translate(
            (0, 0, -NOMINAL_TOTAL_TRAVEL)
        )

    if include_switches:
        for name, (x, y) in positions.items():
            travel = NOMINAL_TOTAL_TRAVEL if name == active else 0.0
            parts[f"switch_{name}_reference_only"] = _switch_model(x, y, travel)
    return parts


# Variant C has the same three followers but intentionally introduces side
# clearance so a CENTER translation does not close the LEFT and RIGHT switches.
C_PIVOT_Z = 15.20
C_SIDE_CLEARANCE = 0.75
C_CENTER_FOOT_BOTTOM_Z = 13.40
C_SIDE_FOOT_BOTTOM_Z = C_CENTER_FOOT_BOTTOM_Z + C_SIDE_CLEARANCE
C_FOLLOWER_TOP_Z = C_CENTER_FOOT_BOTTOM_Z
C_FOOT_RADIUS = 1.20
C_CENTER_FOOT_CENTER_Z = C_CENTER_FOOT_BOTTOM_Z + C_FOOT_RADIUS
C_SIDE_FOOT_CENTER_Z = C_SIDE_FOOT_BOTTOM_Z + C_FOOT_RADIUS


def _variant_c_side_angle_deg(p: FingerPreset) -> float:
    """Solve the exact rocker angle that closes clearance plus switch travel."""
    desired = C_SIDE_CLEARANCE + NOMINAL_TOTAL_TRAVEL
    z_rel = C_SIDE_FOOT_CENTER_Z - C_PIVOT_Z
    contact_x = abs(_switch_positions(p)["right"][0])

    # For either symmetric side, downward travel of the spherical foot is
    # r*sin(a) + z_rel*(1-cos(a)).  Bisection avoids a small-angle shortcut.
    low, high = radians(0.1), radians(35.0)
    for _ in range(80):
        angle = (low + high) / 2
        down = contact_x * sin(angle) + z_rel * (1.0 - cos(angle))
        if down < desired:
            low = angle
        else:
            high = angle
    return degrees((low + high) / 2)


def _variant_c_follower(p: FingerPreset, name: str) -> cq.Workplane:
    """One C follower; the large flange is both retention and hard stop."""
    x, y = _switch_positions(p)[name]
    stem_top = 12.80 if name == "center" else C_FOLLOWER_TOP_Z
    stem = _box(
        GUIDE_STEM_X,
        GUIDE_STEM_Y,
        stem_top - SWITCH.total_height,
        x,
        y,
        SWITCH.total_height,
    )
    flange = _box(5.25, 5.55, 0.20, x, y, FOLLOWER_FLANGE_BOTTOM_Z)
    # A small circular crown provides a well-defined point/patch contact.  The
    # CENTER crown is intentionally much narrower: the shared rocker swings
    # past it on LEFT/RIGHT without inadvertently pressing CENTER.
    crown_radius = 0.03 if name == "center" else 0.82
    if name == "center":
        neck = _cyl_z(crown_radius, C_FOLLOWER_TOP_Z - stem_top, x, y, stem_top)
        follower = stem.union(flange).union(neck)
    else:
        top = _cyl_z(crown_radius, 0.40, x, y, C_FOLLOWER_TOP_Z - 0.40)
        follower = stem.union(flange).union(top)
    return _safe_fillet(follower, "|Z", 0.25)


def _variant_c_rocker(p: FingerPreset) -> cq.Workplane:
    """Shared rocker with a shaft barrel and three geometrically separated feet."""
    outer_w = min(float(module_dimensions(p)["outer_width"]) - 2.0, p.effective_width + 1.5)
    pad = _concave_ellipse(outer_w, 11.4, 2.40, 0, 0, 16.00, 0.85)
    barrel = _cyl_y(2.30, 11.60, 0, 0, C_PIVOT_Z)
    barrel = barrel.cut(_cyl_y(1.15, 13.0, 0, 0, C_PIVOT_Z))
    # Remove the lower central quadrant so the barrel can swing past the
    # CENTER follower crown without driving it during LEFT/RIGHT input.  The
    # remaining upper/side wall still fully surrounds the 2 mm steel shaft.
    barrel = barrel.cut(_box(1.8, 6.2, 2.2, 0, 0, 12.4))
    positions = _switch_positions(p)
    left_x, left_y = positions["left"]
    right_x, right_y = positions["right"]

    # The side feet start 0.75 mm above their followers.  CENTER translation
    # is only 0.62 mm, leaving 0.13 mm residual clearance; lateral tilt first
    # consumes the clearance, then moves exactly one follower by 0.62 mm.
    # A narrow rounded CENTER tip is elongated along Y but only 0.6 mm wide in
    # X.  That preserves vertical center contact while clearing the follower's
    # lateral corner when the rocker tilts.
    # 0.18 mm lateral blade is wider than the 0.06 mm follower crown at
    # neutral, yet clears it by about 0.03 mm after either 7.8° rocker tilt.
    center_foot = _box(0.18, 2.40, 2.40, 0, 0, C_CENTER_FOOT_BOTTOM_Z)
    left_foot = cq.Workplane("XY").sphere(C_FOOT_RADIUS).translate(
        (left_x, left_y, C_SIDE_FOOT_CENTER_Z)
    )
    right_foot = cq.Workplane("XY").sphere(C_FOOT_RADIUS).translate(
        (right_x, right_y, C_SIDE_FOOT_CENTER_Z)
    )
    # Narrow necks make each spherical contact a single printable rocker part
    # while leaving the follower stop flanges clear during tilt.
    center_neck = _box(1.20, 1.50, 1.00, 0, 0, 15.35)
    left_neck = _box(1.20, 1.50, 1.00, left_x, left_y, 15.45)
    right_neck = _box(1.20, 1.50, 1.00, right_x, right_y, 15.45)
    rocker = (
        pad.union(barrel)
        .union(center_foot)
        .union(left_foot)
        .union(right_foot)
        .union(center_neck)
        .union(left_neck)
        .union(right_neck)
    )
    # The center follower lies below the Y-axis barrel.  Removing this local
    # underside window prevents the barrel body from occupying the follower's
    # travel corridor; the 2 mm steel shaft remains 0.10 mm above the neutral
    # follower and the center foot begins exactly at the follower top.
    rocker = rocker.cut(_box(5.80, 6.10, 2.10, 0, 0, 11.30))
    return _safe_fillet(rocker, "|Z", 0.32)


def build_variant_c_parts(p: FingerPreset) -> Parts:
    """Return separated parts for the functional shared-rocker comparator.

    The two shell ears contain vertical shaft slots.  The shaft translates for
    CENTER and acts as a Y-axis pivot for LEFT/RIGHT.  Followers stay vertical,
    so the EVQ-P0 plungers never receive the side load generated by the rocker.
    """
    return {
        "shell": _base_shell(p, rocker_ears=True),
        "bottom_cover": _build_service_cover(p),
        "shared_rocker": _variant_c_rocker(p),
        "left_follower": _variant_c_follower(p, "left"),
        "center_follower": _variant_c_follower(p, "center"),
        "right_follower": _variant_c_follower(p, "right"),
        "stop_shim_0p18_reference": build_calibration_shim(0.18),
        "stop_shim_0p20_coarse_fdm": build_calibration_shim(0.20),
    }


def assembly_parts_variant_c(
    p: FingerPreset,
    state: str = "neutral",
    *,
    include_switches: bool = True,
) -> Parts:
    """Return positioned Variant-C components for neutral/L/C/R states."""
    if state not in ("neutral", "left", "center", "right"):
        raise ValueError(state)

    parts = build_variant_c_parts(p)
    parts.pop("stop_shim_0p18_reference")
    parts.pop("stop_shim_0p20_coarse_fdm")
    parts["bottom_cover"] = parts["bottom_cover"].translate((0, 0, -2.40))
    positions = _switch_positions(p)
    for name, (x, y) in positions.items():
        parts[f"{name}_stop_shim"] = build_calibration_shim().translate(
            (x, y, COLLAR_TOP_Z)
        )

    active = state if state != "neutral" else None
    switch_travel = {"left": 0.0, "center": 0.0, "right": 0.0}
    shaft = _cyl_y(1.00, 18.0, 0, 0, C_PIVOT_Z)
    if state == "center":
        parts["shared_rocker"] = parts["shared_rocker"].translate(
            (0, 0, -NOMINAL_TOTAL_TRAVEL)
        )
        shaft = shaft.translate((0, 0, -NOMINAL_TOTAL_TRAVEL))
        parts["center_follower"] = parts["center_follower"].translate(
            (0, 0, -NOMINAL_TOTAL_TRAVEL)
        )
        switch_travel["center"] = NOMINAL_TOTAL_TRAVEL
    elif state in ("left", "right"):
        angle = _variant_c_side_angle_deg(p)
        signed_angle = -angle if state == "left" else angle
        parts["shared_rocker"] = parts["shared_rocker"].rotate(
            (0, 0, C_PIVOT_Z), (0, 1, C_PIVOT_Z), signed_angle
        )
        parts[f"{state}_follower"] = parts[f"{state}_follower"].translate(
            (0, 0, -NOMINAL_TOTAL_TRAVEL)
        )
        switch_travel[state] = NOMINAL_TOTAL_TRAVEL
        # The center sphere is on X=0.  Tilting raises it slightly because its
        # center is above the shaft, so the CENTER follower remains neutral.

    parts["pivot_shaft_reference_only"] = shaft

    if include_switches:
        for name, (x, y) in positions.items():
            parts[f"switch_{name}_reference_only"] = _switch_model(
                x, y, switch_travel[name]
            )
    return parts


def _state_compounds(
    state_parts: Mapping[str, Parts],
) -> Dict[str, cq.Compound]:
    return {state: compound(parts.values()) for state, parts in state_parts.items()}


def build_functional_comparators(p: FingerPreset) -> Dict[str, object]:
    """Return editable parts and four real kinematic states for Variants A/C.

    Returned structure::

        {
          "variant_a": {
            "printable_parts": {name: shape, ...},
            "state_parts": {"neutral": {name: shape, ...}, ...},
            "state_assemblies": {"neutral": Compound, ...},
          },
          "variant_c": { ... },
          "assumptions": { ... },
        }

    The reference shaft and switch placeholders appear only
    in ``state_parts``/``state_assemblies`` and are not labelled printable.
    """
    states = ("neutral", "left", "center", "right")
    a_states = {state: assembly_parts_variant_a(p, state) for state in states}
    c_states = {state: assembly_parts_variant_c(p, state) for state in states}
    return {
        "variant_a": {
            "printable_parts": build_variant_a_parts(p),
            "state_parts": a_states,
            "state_assemblies": _state_compounds(a_states),
        },
        "variant_c": {
            "printable_parts": build_variant_c_parts(p),
            "state_parts": c_states,
            "state_assemblies": _state_compounds(c_states),
        },
        "assumptions": {
            "base_stop_gap_mm": BASE_STOP_GAP,
            "nominal_shim_mm": NOMINAL_SHIM_THICKNESS,
            "nominal_total_travel_mm": NOMINAL_TOTAL_TRAVEL,
            "variant_c_side_clearance_mm": C_SIDE_CLEARANCE,
            "variant_c_side_angle_deg": _variant_c_side_angle_deg(p),
            "shaft_diameter_mm": 2.0,
        },
    }


__all__ = [
    "BASE_STOP_GAP",
    "NOMINAL_SHIM_THICKNESS",
    "NOMINAL_TOTAL_TRAVEL",
    "build_calibration_shim",
    "build_variant_a_parts",
    "assembly_parts_variant_a",
    "build_variant_c_parts",
    "assembly_parts_variant_c",
    "build_functional_comparators",
]
