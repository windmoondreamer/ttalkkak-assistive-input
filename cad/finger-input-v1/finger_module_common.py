"""Parametric OneGrip Play three-direction finger cartridge.

Coordinate system used by the cartridge:
    X  fingertip roll direction (LEFT/RIGHT)
    Y  distal/proximal direction
    Z  fingertip pressure direction (positive points toward the finger)

The production candidate is Variant B: three independently hinged paddles.
No Lalboard geometry or source code is copied here.  Lalboard is an ergonomic
and mechanism reference only; see THIRD_PARTY_NOTICES.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import asin, degrees, radians, tan
from pathlib import Path
from typing import Dict, Iterable, Mapping, Tuple
import json
import os

import cadquery as cq
from cadquery import exporters


ROOT = Path(__file__).resolve().parent
PRINTABLE = ROOT / "printable"
VARIANTS = ROOT / "variants"
INTEGRATION = ROOT / "integration"
FIXTURE = ROOT / "test_fixture"
REPORTS = ROOT / "reports"
RENDER_GEOMETRY = ROOT / "renders" / "geometry_cache"


@dataclass(frozen=True)
class SwitchSpec:
    name: str = "Panasonic EVQ-P0E07K"
    width: float = 6.20
    depth: float = 6.20
    body_height: float = 6.70
    total_height: float = 7.45
    force_n: float = 0.74
    pretravel_max: float = 0.50
    overtravel_min: float = 0.20
    pocket_clearance_xy: float = 0.20
    hard_stop_after_click: float = 0.12
    terminal_pitch: float = 5.00
    terminal_diameter: float = 1.00
    terminal_length: float = 3.50

    @property
    def pocket_width(self) -> float:
        return self.width + 2 * self.pocket_clearance_xy

    @property
    def pocket_depth(self) -> float:
        return self.depth + 2 * self.pocket_clearance_xy


@dataclass(frozen=True)
class FingerPreset:
    name: str
    effective_width: float
    center_width: float
    depth_offset: float
    vertical_center: float
    side_lever_ratio: float
    target_force_n: Tuple[float, float]
    fingertip_length: float
    fingertip_thickness: float
    distal_length: float


SWITCH = SwitchSpec()

PRESETS: Mapping[str, FingerPreset] = {
    "index": FingerPreset("index", 21.0, 9.5, -3.0, 116.0, 1.35, (0.45, 0.70), 25.0, 12.0, 31.0),
    "middle": FingerPreset("middle", 22.0, 9.5, 0.0, 86.0, 1.40, (0.45, 0.70), 27.0, 12.5, 33.0),
    "ring": FingerPreset("ring", 20.5, 8.5, -3.0, 57.0, 1.50, (0.40, 0.60), 24.0, 11.5, 29.0),
    "pinky": FingerPreset("pinky", 18.5, 7.5, -8.0, 30.0, 1.65, (0.35, 0.55), 21.0, 10.5, 25.0),
}


def _box(w: float, d: float, h: float, x: float = 0, y: float = 0, z0: float = 0) -> cq.Workplane:
    return cq.Workplane("XY").box(w, d, h, centered=(True, True, False)).translate((x, y, z0))


def _cyl_z(r: float, h: float, x: float = 0, y: float = 0, z0: float = 0) -> cq.Workplane:
    return cq.Workplane("XY").circle(r).extrude(h).translate((x, y, z0))


def _cyl_y(r: float, length: float, x: float, y: float, z: float) -> cq.Workplane:
    return cq.Workplane("XZ").circle(r).extrude(length / 2, both=True).translate((x, y, z))


def _cyl_x(r: float, length: float, x: float, y: float, z: float) -> cq.Workplane:
    return cq.Workplane("YZ").circle(r).extrude(length / 2, both=True).translate((x, y, z))


def _safe_fillet(wp: cq.Workplane, selector: str, radius: float) -> cq.Workplane:
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


def _concave_ellipse(
    width: float,
    depth: float,
    thickness: float,
    x: float,
    y: float,
    z0: float,
    dish_depth: float = 0.55,
) -> cq.Workplane:
    pad = cq.Workplane("XY").ellipse(width / 2, depth / 2).extrude(thickness).translate((x, y, z0))
    radius = max(18.0, width * 1.25)
    cutter = cq.Workplane("XY").sphere(radius).translate((x, y, z0 + thickness + radius - dish_depth))
    return pad.cut(cutter)


def _shape_list(items: Iterable[cq.Workplane | cq.Shape]) -> list[cq.Shape]:
    shapes: list[cq.Shape] = []
    for item in items:
        if isinstance(item, cq.Workplane):
            shapes.extend(item.vals())
        else:
            shapes.append(item)
    return shapes


def compound(items: Iterable[cq.Workplane | cq.Shape]) -> cq.Compound:
    return cq.Compound.makeCompound(_shape_list(items))


def export_shape(shape: cq.Workplane | cq.Shape, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exporters.export(shape, str(path), tolerance=0.045, angularTolerance=0.12)


def export_bundle(
    shape: cq.Workplane | cq.Shape,
    stem: Path,
    *,
    include_stl: bool = True,
) -> Dict[str, str]:
    written: Dict[str, str] = {}
    suffixes = (".stl", ".step", ".3mf") if include_stl else (".step", ".3mf")
    if not include_stl:
        stale_stl = stem.parent / f"{stem.name}.stl"
        # This exact path is a generated composite from an older revision.
        # Remove it so users cannot mistake a tangent multi-body render mesh
        # for a printable watertight part.
        if stale_stl.exists():
            stale_stl.unlink()
    for suffix in suffixes:
        # ``Path.with_suffix`` treats the calibration value in names such as
        # ``hard_stop_shim_0.1mm`` as an existing suffix and silently collapses
        # 0.1/0.2/0.3 into the same file.  Appending keeps dotted part names
        # unique and makes the exporter safe for revision/calibration labels.
        path = stem.parent / f"{stem.name}{suffix}"
        if os.getenv("ONEGRIP_SKIP_EXISTING") == "1" and path.exists() and path.stat().st_size > 1024:
            written[suffix[1:]] = str(path.relative_to(ROOT))
            continue
        try:
            export_shape(shape, path)
            written[suffix[1:]] = str(path.relative_to(ROOT))
        except Exception as exc:
            written[suffix[1:]] = f"EXPORT_FAILED: {type(exc).__name__}: {exc}"
    return written


def module_dimensions(p: FingerPreset) -> Dict[str, float]:
    return {
        # 35 mm provides the physical lever arm needed to keep the side switch
        # follower clear of the Ø4.3 mm pivot barrel while preserving the
        # finger-force ratios.  The active fingertip surface remains 18.5--22 mm.
        "outer_width": max(35.0, p.effective_width + 13.0),
        "depth": 32.0,
        "shell_height": 10.0,
        "pivot_height": 13.2,
        "contact_height": 15.5,
        "cover_thickness": 2.0,
    }


def mechanism_layout(p: FingerPreset) -> Dict[str, float | Tuple[float, float]]:
    gap = 0.70
    side_width = (p.effective_width - p.center_width - 2 * gap) / 2
    contact_abs_x = p.center_width / 2 + gap + side_width / 2
    # A 4.6 mm cam radius is the minimum that physically clears the pivot
    # barrel, follower stop wings and 0.35 mm FDM running gap.  The pivot is
    # moved outward (not the fingertip pad inward) to retain the requested
    # leverage and low operating force.
    switch_lever = 4.60
    contact_lever = switch_lever * p.side_lever_ratio
    pivot_abs_x = contact_abs_x + contact_lever
    switch_abs_x = pivot_abs_x - switch_lever
    click_motion = SWITCH.pretravel_max + SWITCH.hard_stop_after_click
    side_angle = degrees(asin(min(0.95, click_motion / switch_lever)))
    return {
        "gap": gap,
        "side_width": side_width,
        "contact_abs_x": contact_abs_x,
        "pivot_abs_x": pivot_abs_x,
        "contact_lever": contact_lever,
        "switch_lever": switch_lever,
        "switch_abs_x": switch_abs_x,
        "side_press_angle_deg": side_angle,
        "side_contact_travel": click_motion * p.side_lever_ratio,
        "side_finger_force": SWITCH.force_n / p.side_lever_ratio,
        "left_switch": (-switch_abs_x, -0.5),
        "center_switch": (0.0, 0.0),
        "right_switch": (switch_abs_x, -0.5),
        "center_contact_y": 0.0,
        "center_guide_y": 5.4,
    }


def build_switch_placeholder(
    x: float,
    y: float,
    transparent_clearance: bool = False,
    pressed_travel: float = 0.0,
) -> cq.Workplane:
    extra = SWITCH.pocket_clearance_xy if transparent_clearance else 0.0
    body = _box(SWITCH.width + 2 * extra, SWITCH.depth + 2 * extra, SWITCH.body_height, x, y, 0.0)
    free_plunger = SWITCH.total_height - SWITCH.body_height
    exposed = max(0.05, free_plunger - pressed_travel)
    plunger = _box(3.4, 3.4, exposed, x, y, SWITCH.body_height)
    # The EVQ-P0E07K is a two-terminal DIP part.  These reference pins are
    # included so cover clearance and solder access can be checked in CAD.
    pins = [
        _cyl_z(SWITCH.terminal_diameter / 2, SWITCH.terminal_length, x + sx, y, -SWITCH.terminal_length)
        for sx in (-SWITCH.terminal_pitch / 2, SWITCH.terminal_pitch / 2)
    ]
    return body.union(plunger).union(pins[0]).union(pins[1])


def build_variant_b_shell(p: FingerPreset) -> cq.Workplane:
    dims = module_dimensions(p)
    layout = mechanism_layout(p)
    outer_w = dims["outer_width"]
    depth = dims["depth"]
    body = _box(outer_w, depth, dims["shell_height"])

    # Bottom-loaded switch pockets.  A screw-fastened cover, not a snap fit,
    # retains the switches.  The 6.6 mm roof span is printable as a short bridge.
    for x, y in (layout["left_switch"], layout["center_switch"], layout["right_switch"]):
        # 0.15 mm vertical body clearance; the screwed cover positively seats
        # the switch against this roof instead of leaving it free to rattle.
        cavity = _box(SWITCH.pocket_width, SWITCH.pocket_depth, 6.95, x, y, -0.10)
        plunger_hole = _box(3.9, 4.2, 3.65, x, y, 6.55)
        body = body.cut(cavity).cut(plunger_hole)

        # 1.2 mm-deep underside wiring groove leading to the common rear exit.
        run_y = depth / 2 - y - 1.2
        wire_run = _box(2.2, run_y, 1.25, x, y + run_y / 2, -0.05)
        body = body.cut(wire_run)

    rear_exit = _box(10.0, 3.0, 2.2, 0, depth / 2 - 0.6, -0.05)
    body = body.cut(rear_exit)

    # Four M2 heat-set insert pilots for the serviceable bottom cover.
    cover_screws = [
        (-outer_w / 2 + 2.4, -depth / 2 + 2.5),
        (outer_w / 2 - 2.4, -depth / 2 + 2.5),
        (-outer_w / 2 + 2.4, depth / 2 - 2.5),
        (outer_w / 2 - 2.4, depth / 2 - 2.5),
    ]
    for x, y in cover_screws:
        body = body.cut(_cyl_z(1.55, 4.4, x, y, -0.10))

    # Side-paddle pivot ears: 2 mm stainless rods run along Y.
    pivot_z = dims["pivot_height"]
    pivot_abs_x = layout["pivot_abs_x"]
    for sign in (-1, 1):
        px = sign * pivot_abs_x
        for ey in (-7.0, 7.0):
            body = body.union(_box(3.6, 2.8, 6.3, px, ey, 9.7))
        body = body.cut(_cyl_y(1.20, 18.0, px, 0, pivot_z))

    # LEFT/RIGHT use short rotating cams, but the switch is loaded only by an
    # independent vertical follower.  The shell guides take all lateral load;
    # this replaces the earlier long actuator post that swept into the shell.
    for x, y in (layout["left_switch"], layout["right_switch"]):
        collar = _box(4.2, 5.4, 0.60, x, y, 10.0)
        guide_hole = _box(3.0, 3.8, 5.9, x, y, 6.6)
        body = body.union(collar).cut(guide_hole)

    # CENTER follows the Lalboard ergonomic principle more closely than a
    # shared rocker: two separate guide posts suppress yaw while the cap moves
    # straight down.  The posts flank the switch body in Y, so no PCB or hidden
    # guide plate is required.
    guide_y = float(layout["center_guide_y"])
    for gy in (-guide_y, guide_y):
        collar = _box(5.8, 6.0, 2.5, 0, gy, 10.0)
        guide_hole = _box(3.4, 4.2, 5.9, 0, gy, 6.8)
        # Through slot for a removable 1 mm anti-loss pin.  The pin slides with
        # the key over its 0.62 mm stroke and is not a flexing snap joint.
        # 3.0 mm vertical window leaves >=0.27 mm clearance around the 1 mm
        # anti-loss pin at both neutral and the full 0.62 mm calibrated stroke.
        retention_slot = _box(6.4, 4.4, 3.0, 0, gy, 6.90)
        body = body.union(collar).cut(guide_hole).cut(retention_slot)

    # Rear mounting tongue: two M3 holes mate to the adjustable slotted plate.
    tongue = _box(outer_w - 4.0, 5.0, 5.0, 0, depth / 2 + 2.0, 2.0)
    body = body.union(tongue)
    for x in (-5.0, 5.0):
        body = body.cut(_cyl_z(1.7, 7.0, x, depth / 2 + 2.0, 1.0))

    return _safe_fillet(body, "|Z", 0.8)


def build_bottom_cover(p: FingerPreset) -> cq.Workplane:
    dims = module_dimensions(p)
    outer_w = dims["outer_width"]
    depth = dims["depth"]
    cover = _box(outer_w, depth, dims["cover_thickness"], z0=0)
    screw_xy = [
        (-outer_w / 2 + 2.4, -depth / 2 + 2.5),
        (outer_w / 2 - 2.4, -depth / 2 + 2.5),
        (-outer_w / 2 + 2.4, depth / 2 - 2.5),
        (outer_w / 2 - 2.4, depth / 2 - 2.5),
    ]
    for x, y in screw_xy:
        cover = cover.cut(_cyl_z(1.15, 2.4, x, y, -0.2))
        # Flat M2 counterbore is deliberately used instead of a steep printed
        # countersink; it is repeatable with a 0.4 mm nozzle.
        cover = cover.cut(_cyl_z(2.15, 0.95, x, y, 1.15))
    # Two through holes per switch let the DIP terminals pass without bending.
    # Shallow underside grooves lead soldered 28 AWG wires to the rear exit;
    # heat-shrink at each joint is the electrical insulation for the P0 build.
    layout = mechanism_layout(p)
    for sx, sy in (layout["left_switch"], layout["center_switch"], layout["right_switch"]):
        for pin_x in (sx - SWITCH.terminal_pitch / 2, sx + SWITCH.terminal_pitch / 2):
            cover = cover.cut(_cyl_z(0.75, 2.4, pin_x, sy, -0.2))
            run_y = depth / 2 - sy - 0.8
            cover = cover.cut(_box(1.8, run_y, 0.85, pin_x, sy + run_y / 2, -0.05))
    cover = cover.cut(_box(10.0, 3.2, 1.3, 0, depth / 2 - 0.8, 0.9))
    return _safe_fillet(cover, "|Z", 0.7)


def _side_key(p: FingerPreset, side: str) -> cq.Workplane:
    if side not in ("left", "right"):
        raise ValueError(side)
    sign = -1 if side == "left" else 1
    layout = mechanism_layout(p)
    pivot_x = sign * float(layout["pivot_abs_x"])
    contact_x = sign * float(layout["contact_abs_x"])
    switch_x = sign * float(layout["switch_abs_x"])
    side_w = float(layout["side_width"])
    pivot_z = module_dimensions(p)["pivot_height"]

    pad = _concave_ellipse(side_w, 10.0, 2.0, contact_x, -0.5, 13.55, 0.55)
    tilt = 18.0 if side == "left" else -18.0
    pad = pad.rotate((contact_x, -0.5, 14.55), (contact_x, 0.5, 14.55), tilt)

    span_x = abs(pivot_x - contact_x) + 1.8
    arm_x = (pivot_x + contact_x) / 2
    arm = _box(span_x, 3.0, 1.65, arm_x, -0.5, 12.70)
    barrel = _cyl_y(2.15, 11.0, pivot_x, 0, pivot_z)
    # A compact round cam remains close to the pivot.  At full rotation its
    # centre drops 0.62 mm and shifts laterally <0.2 mm over the follower face.
    # The 1.00 mm cam is tangent to the follower at neutral and remains tangent
    # through the commanded stroke; the independent guide absorbs its <0.05 mm
    # lateral sweep while the switch sees vertical motion only.
    cam = _cyl_y(1.00, 3.0, switch_x, -0.5, pivot_z)
    bridge_x = (pivot_x + switch_x) / 2
    bridge = _box(abs(pivot_x - switch_x) + 2.2, 3.0, 1.8, bridge_x, -0.5, 12.35)

    key = pad.union(arm).union(barrel).union(cam).union(bridge)
    key = key.cut(_cyl_y(1.20, 13.5, pivot_x, 0, pivot_z))
    return _safe_fillet(key, "|Z", 0.35)


def build_side_follower(p: FingerPreset, side: str) -> cq.Workplane:
    """Vertical cam follower for a LEFT or RIGHT hinged paddle.

    The 2.8 x 3.6 mm stem is guided by the cartridge, and a split stop flange
    lands on the 11.2 mm shell collar.  Its nominal 0.62 mm gap is reduced with
    a measured shim so each real switch stops 0.10--0.12 mm after its measured
    operating point; the datasheet maximum alone is not used as calibration.
    """
    if side not in ("left", "right"):
        raise ValueError(side)
    sign = -1 if side == "left" else 1
    layout = mechanism_layout(p)
    x = sign * float(layout["switch_abs_x"])
    y = -0.5
    stem = _box(2.4, 3.2, 4.75, x, y, SWITCH.total_height)
    # A solid flange (not a disconnected ring) joins the guide stem and lands
    # on the shell collar after the calibrated travel.
    stop_flange = _box(4.0, 4.8, 0.40, x, y, 11.22)
    follower = stem.union(stop_flange)
    return _safe_fillet(follower, "|Z", 0.20)


def build_center_key(p: FingerPreset) -> cq.Workplane:
    layout = mechanism_layout(p)
    contact_y = float(layout["center_contact_y"])
    guide_y = float(layout["center_guide_y"])

    # Neutral gap to the 12.5 mm collar is 0.62 mm: 0.50 mm maximum switch
    # pretravel plus 0.12 mm controlled overtravel.  The collar, not the switch,
    # carries any force applied after activation.
    pad = _concave_ellipse(p.center_width, 11.2, 2.0, 0, contact_y, 13.12, 0.60)
    actuator = _box(2.8, 2.8, 5.67, 0, 0, 7.45)
    posts = []
    for gy in (-guide_y, guide_y):
        post = _box(2.8, 3.6, 5.67, 0, gy, 7.45)
        # A 1 mm stainless pin is inserted after the key is slid into the
        # guides.  This leaves 0.85 mm PETG on each side of the post and avoids
        # a fragile M2 cross-hole or a final snap-only retention joint.
        post = post.cut(_cyl_x(0.55, 4.0, 0, gy, 8.35))
        posts.append(post)
    key = pad.union(actuator).union(posts[0]).union(posts[1])
    return _safe_fillet(key, "|Z", 0.35)


def build_tpu_pad(p: FingerPreset, key: str) -> cq.Workplane:
    layout = mechanism_layout(p)
    if key == "center":
        pad = _concave_ellipse(p.center_width - 0.5, 10.2, 0.9, 0, float(layout["center_contact_y"]), 15.05, 0.35)
    else:
        side = -1 if key == "left" else 1
        contact_x = side * float(layout["contact_abs_x"])
        side_w = float(layout["side_width"])
        pad = _concave_ellipse(side_w - 0.45, 10.2, 0.9, contact_x, -0.5, 15.40, 0.30)
        tilt = 18.0 if key == "left" else -18.0
        pad = pad.rotate((contact_x, -0.5, 15.85), (contact_x, 0.5, 15.85), tilt)
    return pad


def build_shaft_set(p: FingerPreset) -> cq.Compound:
    layout = mechanism_layout(p)
    z = module_dimensions(p)["pivot_height"]
    parts = [
        _cyl_y(1.0, 14.5, -float(layout["pivot_abs_x"]), 0, z),
        _cyl_y(1.0, 14.5, float(layout["pivot_abs_x"]), 0, z),
        _cyl_x(0.48, 4.0, 0, -float(layout["center_guide_y"]), 8.35),
        _cyl_x(0.48, 4.0, 0, float(layout["center_guide_y"]), 8.35),
    ]
    return compound(parts)


def build_variant_b_parts(p: FingerPreset) -> Dict[str, cq.Workplane | cq.Shape]:
    return {
        "cartridge": build_variant_b_shell(p),
        "bottom_cover": build_bottom_cover(p),
        "left_key": _side_key(p, "left"),
        "left_follower": build_side_follower(p, "left"),
        "center_key": build_center_key(p),
        "right_key": _side_key(p, "right"),
        "right_follower": build_side_follower(p, "right"),
        "left_tpu_pad": build_tpu_pad(p, "left"),
        "center_tpu_pad": build_tpu_pad(p, "center"),
        "right_tpu_pad": build_tpu_pad(p, "right"),
        "shafts_reference_only": build_shaft_set(p),
    }


def assembly_parts_variant_b(p: FingerPreset, state: str = "neutral", include_switches: bool = True) -> Dict[str, cq.Workplane | cq.Shape]:
    parts = build_variant_b_parts(p)
    # Cover is modeled in its printable coordinates and translated below shell.
    parts["bottom_cover"] = parts["bottom_cover"].translate((0, 0, -2.0))
    layout = mechanism_layout(p)
    travel = SWITCH.pretravel_max + SWITCH.hard_stop_after_click
    side_angle = float(layout["side_press_angle_deg"])
    if state == "left":
        px = -float(layout["pivot_abs_x"])
        parts["left_key"] = parts["left_key"].rotate((px, 0, 13.2), (px, 1, 13.2), side_angle)
        parts["left_tpu_pad"] = parts["left_tpu_pad"].rotate((px, 0, 13.2), (px, 1, 13.2), side_angle)
        parts["left_follower"] = parts["left_follower"].translate((0, 0, -travel))
    elif state == "right":
        px = float(layout["pivot_abs_x"])
        parts["right_key"] = parts["right_key"].rotate((px, 0, 13.2), (px, 1, 13.2), -side_angle)
        parts["right_tpu_pad"] = parts["right_tpu_pad"].rotate((px, 0, 13.2), (px, 1, 13.2), -side_angle)
        parts["right_follower"] = parts["right_follower"].translate((0, 0, -travel))
    elif state == "center":
        parts["center_key"] = parts["center_key"].translate((0, 0, -travel))
        parts["center_tpu_pad"] = parts["center_tpu_pad"].translate((0, 0, -travel))
    elif state != "neutral":
        raise ValueError(state)

    if include_switches:
        for name, (x, y) in {
            "switch_left": layout["left_switch"],
            "switch_center": layout["center_switch"],
            "switch_right": layout["right_switch"],
        }.items():
            pressed = travel if state == name.removeprefix("switch_") else 0.0
            parts[name] = build_switch_placeholder(x, y, pressed_travel=pressed)
    return parts


def _scaled_sphere(rx: float, ry: float, rz: float, center: Tuple[float, float, float]) -> cq.Shape:
    sphere = cq.Workplane("XY").sphere(1.0).val()
    matrix = cq.Matrix([
        [rx, 0, 0, 0],
        [0, ry, 0, 0],
        [0, 0, rz, 0],
        [0, 0, 0, 1],
    ])
    return sphere.transformGeometry(matrix).translate(cq.Vector(*center))


def build_finger_surrogate(p: FingerPreset) -> cq.Compound:
    fingertip = _scaled_sphere(
        p.effective_width * 0.46,
        p.fingertip_length * 0.48,
        p.fingertip_thickness * 0.50,
        (0, -0.5, 21.5),
    )
    distal = _scaled_sphere(
        p.effective_width * 0.43,
        p.distal_length * 0.50,
        p.fingertip_thickness * 0.45,
        (0, -12.0, 23.0),
    ).rotate((0, -12, 23), (1, -12, 23), -8.0)
    return compound([fingertip, distal])


def build_mount_plate(p: FingerPreset) -> cq.Workplane:
    # Separate plate gives +/-8 mm depth and +/-8 degree angle without making
    # the replaceable cartridge itself fragile or difficult to print.
    plate = _box(30.0, 52.0, 4.0, y=8.0)
    for x in (-5.0, 5.0):
        # CadQuery slot2D length includes the end radii.  19.4 mm overall gives
        # a true 16.0 mm bolt-centre range, i.e. +/-8 mm depth adjustment.
        slot = cq.Workplane("XY").center(x, 18.0).slot2D(19.4, 3.4, 90).extrude(4.4).translate((0, 0, -0.2))
        plate = plate.cut(slot)
    plate = plate.cut(_cyl_z(1.7, 4.4, 0, -12.0, -0.2))
    # Arc endpoints for an M3 friction screw; discrete holes are more reliable
    # than a thin printed arc slot at this scale.
    # Pivot-to-clamp spacing is 24 mm; +/-3.37 mm corresponds to +/-8 degrees.
    for x in (-3.37, 0.0, 3.37):
        plate = plate.cut(_cyl_z(1.7, 4.4, x, 12.0, -0.2))
    return _safe_fillet(plate, "|Z", 1.0)


def build_angle_wedge(angle_deg: float, width: float = 22.0, depth: float = 18.0) -> cq.Workplane:
    """Printable fixed-angle P0 shim; continuous clamp adjustment follows P1."""
    rise = depth * tan(radians(abs(angle_deg)))
    if angle_deg < 0:
        points = [(-depth / 2, 0), (depth / 2, rise), (depth / 2, rise + 2.0), (-depth / 2, 2.0)]
    elif angle_deg > 0:
        points = [(-depth / 2, rise), (depth / 2, 0), (depth / 2, 2.0), (-depth / 2, rise + 2.0)]
    else:
        points = [(-depth / 2, 0), (depth / 2, 0), (depth / 2, 2.0), (-depth / 2, 2.0)]
    wedge = cq.Workplane("YZ").polyline(points).close().extrude(width / 2, both=True)
    for x in (-5.0, 5.0):
        wedge = wedge.cut(_cyl_z(1.7, 6.0, x, 0, -1.0))
    return wedge


def build_variant_a(p: FingerPreset) -> cq.Compound:
    """Backward-compatible accessor for functional Variant A neutral state."""
    from functional_comparators import build_functional_comparators
    return build_functional_comparators(p)["variant_a"]["state_assemblies"]["neutral"]


def build_variant_c(p: FingerPreset) -> cq.Compound:
    """Backward-compatible accessor for functional Variant C neutral state."""
    from functional_comparators import build_functional_comparators
    return build_functional_comparators(p)["variant_c"]["state_assemblies"]["neutral"]


def build_fixture_parts(p: FingerPreset) -> Dict[str, cq.Workplane | cq.Shape]:
    base = _safe_fillet(_box(110.0, 72.0, 6.0), "|Z", 3.0)
    for x in (-45.0, 45.0):
        base = base.cut(_cyl_z(3.2, 6.4, x, 0, -0.2))
    # Parallel uprights with vertical M4 slots.  The carrier is clamped by two
    # bolts and can slide 24 mm and rotate at least +/-15 degrees by friction.
    for x in (-23.0, 23.0):
        upright = _box(4.0, 24.0, 46.0, x, 0, 6.0)
        slot = _box(5.0, 4.4, 24.0, x, 0, 17.0)
        slot = slot.union(_cyl_x(2.2, 6.0, x, 0, 17.0)).union(_cyl_x(2.2, 6.0, x, 0, 41.0))
        base = base.union(upright).cut(slot)

    carrier = _box(40.0, 48.0, 4.0, 0, -2.0, 0)
    axle = _cyl_x(6.0, 46.0, 0, 10.0, 0).cut(_cyl_x(2.15, 49.0, 0, 10.0, 0))
    carrier = carrier.union(axle)
    for x in (-5.0, 5.0):
        slot = cq.Workplane("XY").center(x, 9.0).slot2D(19.4, 3.4, 90).extrude(4.4).translate((0, 0, -0.2))
        carrier = carrier.cut(slot)

    return {"fixture_base": base, "fixture_carrier": carrier}


def _transform_for_integration(shape: cq.Workplane | cq.Shape, p: FingerPreset) -> cq.Workplane | cq.Shape:
    # Local +Z contact normal becomes global -X on the finger side of the grip.
    # The module back face lands near x=-23 mm, matching the measured M-grip
    # finger-side surface instead of floating 20 mm beside it.
    return shape.rotate((0, 0, 0), (0, 1, 0), -90).translate((-24.0, p.depth_offset, p.vertical_center))


def build_four_finger_array(include_surrogates: bool = False) -> cq.Compound:
    items: list[cq.Workplane | cq.Shape] = []
    for p in PRESETS.values():
        assembly = assembly_parts_variant_b(p, include_switches=False)
        for name, shape in assembly.items():
            if "tpu" in name or name == "shafts_reference_only":
                continue
            items.append(_transform_for_integration(shape, p))
        if include_surrogates:
            items.append(_transform_for_integration(build_finger_surrogate(p), p))
    return compound(items)


def build_vertical_array_rail() -> cq.Workplane:
    """P1 carrier rail in the same coordinates as ``build_four_finger_array``.

    The rail occupies the finger-side M-grip wall at X=-26..-18 mm.  Each
    cartridge mounting tongue ends at X=-26 mm, and its two M3 hole axes are
    coaxial with the corresponding through-slots below.  Thus the preview is
    an actual bolted interface, not a module merely placed beside a grip.
    """
    rail_x = -22.0
    rail = _box(8.0, 34.0, 130.0, x=rail_x, y=14.0, z0=12.0)
    for p in PRESETS.values():
        # Local cartridge X=+/-5 becomes global Z=vertical_center+/-5 after
        # integration rotation.  Local rear Y=18 becomes global
        # Y=depth_offset+18.  Horizontal 19.4 mm slots provide a true +/-8 mm
        # fore/aft adjustment while remaining coaxial with the M3 holes.
        for z_offset in (-5.0, 5.0):
            slot = (
                cq.Workplane("YZ")
                .center(p.depth_offset + 18.0, p.vertical_center + z_offset)
                .slot2D(19.4, 3.4, 0)
                .extrude(4.2, both=True)
                .translate((rail_x, 0, 0))
            )
            rail = rail.cut(slot)
    # Four 4-wire bundles enter a grip-side covered vertical trunk.  The 2.6 mm
    # groove depth leaves 5.4 mm structure at the cartridge bolt interface.
    trunk = _box(2.6, 6.0, 126.0, -18.7, 27.0, 14.0)
    rail = rail.cut(trunk)
    for p in PRESETS.values():
        branch_y = 27.0 - (p.depth_offset + 16.0)
        rail = rail.cut(
            _box(2.6, branch_y, 3.2, -18.7, p.depth_offset + 16.0 + branch_y / 2, p.vertical_center - 1.6)
        )
    return _safe_fillet(rail, "|Z", 1.0)


def generate_preset(p: FingerPreset) -> Dict[str, object]:
    parts = build_variant_b_parts(p)
    result: Dict[str, object] = {"preset": asdict(p), "layout": mechanism_layout(p), "files": {}}
    for name, shape in parts.items():
        if name == "shafts_reference_only":
            continue
        stem = PRINTABLE / f"{p.name}_{name}"
        result["files"][name] = export_bundle(shape, stem)

    # Requested short name: `index_cartridge.stl` etc. is already generated.
    neutral = compound(assembly_parts_variant_b(p, include_switches=False).values())
    # Multi-part/tangent assemblies are reference data, not printable meshes.
    # STEP/3MF preserve separate bodies; omitting STL avoids a misleading
    # welded non-manifold mesh at exact cam/follower/switch contact surfaces.
    result["files"]["assembly"] = export_bundle(
        neutral, PRINTABLE / f"{p.name}_assembly", include_stl=False
    )
    result["files"]["states"] = {}
    for state in ("neutral", "left", "center", "right"):
        state_shape = compound(assembly_parts_variant_b(p, state=state, include_switches=True).values())
        result["files"]["states"][state] = export_bundle(
            state_shape,
            PRINTABLE / f"{p.name}_state_{state}_assembly",
            include_stl=False,
        )
    result["files"]["mount_plate"] = export_bundle(build_mount_plate(p), PRINTABLE / f"{p.name}_adjustable_mount")
    export_shape(build_finger_surrogate(p), INTEGRATION / f"{p.name}_finger_surrogate.stl")
    return result


def generate_all() -> Dict[str, object]:
    for folder in (PRINTABLE, VARIANTS, INTEGRATION, FIXTURE, REPORTS, RENDER_GEOMETRY):
        folder.mkdir(parents=True, exist_ok=True)

    manifest: Dict[str, object] = {
        "schema": "onegrip-finger-input-v1",
        "units": "mm",
        "switch": asdict(SWITCH),
        "presets": {},
        "variants": {},
    }
    for p in PRESETS.values():
        manifest["presets"][p.name] = generate_preset(p)

    for angle in (-8, 0, 8):
        label = f"angle_wedge_{angle:+d}deg".replace("+", "plus").replace("-", "minus")
        export_bundle(build_angle_wedge(float(angle)), PRINTABLE / label)

    middle = PRESETS["middle"]
    # Functional A/C comparators are isolated in their own editable module so
    # the production-candidate B source remains easy to audit.
    from functional_comparators import build_functional_comparators

    comparators = build_functional_comparators(middle)
    for variant_key in ("variant_a", "variant_c"):
        for part_name, part_shape in comparators[variant_key]["printable_parts"].items():
            export_bundle(part_shape, VARIANTS / f"{variant_key}_{part_name}")
        for state_name, state_shape in comparators[variant_key]["state_assemblies"].items():
            export_bundle(
                state_shape,
                VARIANTS / f"{variant_key}_{state_name}_assembly",
                include_stl=False,
            )
            export_shape(
                state_shape,
                RENDER_GEOMETRY / f"{variant_key}_{state_name}_visualization_only.stl",
            )
    variant_shapes = {
        "variant_a_direct_switch": comparators["variant_a"]["state_assemblies"]["neutral"],
        "variant_b_lalboard_paddle": compound(assembly_parts_variant_b(middle, include_switches=False).values()),
        "variant_c_rocker": comparators["variant_c"]["state_assemblies"]["neutral"],
    }
    for name, shape in variant_shapes.items():
        manifest["variants"][name] = export_bundle(shape, VARIANTS / name, include_stl=False)

    fixture_parts = build_fixture_parts(middle)
    for name, shape in fixture_parts.items():
        export_bundle(shape, FIXTURE / name)
    fixture_assembly = compound([
        fixture_parts["fixture_base"],
        fixture_parts["fixture_carrier"].translate((0, 0, 34.0)),
        compound(assembly_parts_variant_b(middle, include_switches=False).values()).translate((0, -9.0, 38.0)),
    ])
    export_bundle(fixture_assembly, FIXTURE / "fixture_with_middle_module", include_stl=False)

    # Calibrated hard-stop shims.  0.1/0.2 mm are PET-stock dimensional
    # references; 0.3 mm may be FDM printed at 0.1 mm layers.
    # ``test_fixture`` is an artifact directory, not a Python package; load its
    # small generator explicitly so regeneration also works from a clean clone.
    import importlib.util
    shim_spec = importlib.util.spec_from_file_location(
        "onegrip_hard_stop_shims", FIXTURE / "hard_stop_shims.py"
    )
    if shim_spec is None or shim_spec.loader is None:
        raise RuntimeError("cannot load test_fixture/hard_stop_shims.py")
    shim_module = importlib.util.module_from_spec(shim_spec)
    shim_spec.loader.exec_module(shim_module)
    shim = shim_module.shim
    for thickness in (0.1, 0.2, 0.3):
        export_bundle(shim(thickness), FIXTURE / f"hard_stop_shim_{thickness:.1f}mm")

    four = build_four_finger_array(False)
    four_surrogate = build_four_finger_array(True)
    manifest["four_finger_array"] = export_bundle(
        four, INTEGRATION / "four_finger_array", include_stl=False
    )
    stale_surrogate = INTEGRATION / "four_finger_array_with_surrogates.stl"
    if stale_surrogate.exists():
        stale_surrogate.unlink()
    export_shape(four, RENDER_GEOMETRY / "four_finger_array_visualization_only.stl")
    export_shape(
        four_surrogate,
        RENDER_GEOMETRY / "four_finger_array_with_surrogates_visualization_only.stl",
    )
    manifest["vertical_array_rail"] = export_bundle(build_vertical_array_rail(), INTEGRATION / "vertical_array_rail")
    manifest["array_rail_hardware_assembly"] = export_bundle(
        compound([four, build_vertical_array_rail()]),
        INTEGRATION / "four_finger_array_with_attached_rail",
        include_stl=False,
    )
    export_shape(
        compound([four, build_vertical_array_rail()]),
        RENDER_GEOMETRY / "four_finger_array_with_attached_rail_visualization_only.stl",
    )

    # B state render meshes are kept outside printable/.  Exact tangent contact
    # surfaces can be non-manifold after STL vertex welding, but STEP/3MF above
    # remain the authoritative multi-body assemblies.
    for state in ("neutral", "left", "center", "right"):
        export_shape(
            compound(assembly_parts_variant_b(middle, state=state, include_switches=True).values()),
            RENDER_GEOMETRY / f"variant_b_{state}_visualization_only.stl",
        )

    (ROOT / "build_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    generated = generate_all()
    print(json.dumps({"generated_presets": list(generated["presets"]), "root": str(ROOT)}, indent=2))
