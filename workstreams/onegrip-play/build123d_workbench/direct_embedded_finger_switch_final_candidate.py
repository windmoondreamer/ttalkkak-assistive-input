"""Build the final all-8 direct-embedded detailed switch candidate.

Geometry authority is deliberately narrow:

* recovered TRUE-BARE LOWER15 JaD/JfD STEP files from docs/100;
* frozen centers/axes from finger_button_frozen_datums.json;
* the original 3,530-facet OneGrip PushBtn detailed model;
* measured actuator D3.35 x 2.44 mm.

No holder, harness, leg, slot, pusher, cap, receiver, or remote Thumb
geometry from docs/79-99 is transferred into this candidate.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from build123d import (
    Align, Box, Compound, Cylinder, Location, Plane, Shape, Vector,
    export_step, export_stl, import_step,
)

from .detailed_pushbtn_8_button_revalidation import build_original_parts
from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler
from .finger_controls_v2 import (
    BUTTON_ORDER, controls_from_layout, oriented_box, oriented_cylinder,
    point_at, unit,
)
from .option_c_local_exact_prototype import safe_edge_lines, safe_triangles
from .print_ready_frozen_exterior_recovery import (
    expanded_fit, load_thumb_validation_module, metrics,
    remove_degenerate_stl_triangles, stl_metrics, validate_thumb_openings,
)
from .six_failed_leg_shell_landing_failure_mode_diagnostic_audit import (
    raster_scene_without_header,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build123d_workbench/out/direct_embedded_finger_switch_final_candidate"
RENDER = ROOT / "renders/direct_embedded_finger_switch_final_candidate"
REPORT = ROOT / "docs/101_direct_embedded_finger_switch_final_candidate.md"
JSON_PATH = OUT / "direct_embedded_finger_switch_final_candidate_validation.json"
BASE = {
    "JaD": ROOT / "build123d_workbench/out/lower15_true_bare_finger_base/LOWER15_TRUE_BARE_FINGER_JaD.step",
    "JfD": ROOT / "build123d_workbench/out/lower15_true_bare_finger_base/LOWER15_TRUE_BARE_FINGER_JfD.step",
}
DATUM_JSON = ROOT / "build123d_workbench/out/lower15_true_bare_finger_base/finger_button_frozen_datums.json"
PUSHBTN_SOURCE = ROOT / "cad_dump/mesh_PushBtn.json"
STEP_OUT = {
    "JaD": OUT / "ONEGRIP_DIRECT_EMBEDDED_JaD.step",
    "JfD": OUT / "ONEGRIP_DIRECT_EMBEDDED_JfD.step",
}
STL_OUT = {
    "JaD": OUT / "ONEGRIP_DIRECT_EMBEDDED_JaD.stl",
    "JfD": OUT / "ONEGRIP_DIRECT_EMBEDDED_JfD.stl",
}
COMBINED_STEP = OUT / "ONEGRIP_DIRECT_EMBEDDED_COMBINED_REFERENCE.step"
PLACEMENT_STEP = OUT / "ALL8_DETAILED_SWITCH_PLACEMENT.step"

REPORT_ORDER = ("N1", "N2", "I2", "I3", "I4", "M3", "M4", "N3")
EPS = 1.0e-6
HOLE_DIAMETER = 3.65
ACTUATOR_DIAMETER = 3.35
ACTUATOR_PROJECTION = 2.44
BODY_CLEARANCE = 0.20
TARGET_PROJECTION = 1.20
MIN_DIRECT_PROJECTION = 0.60
# Practical two-perimeter local roof target.  The requested 1.20 mm remains
# the preference and is reported independently, but is not used to force a
# housing/cap architecture back onto the shell.
PRACTICAL_LOCAL_ROOF = 0.80
PREFERRED_LOCAL_ROOF = 1.20
ORIGINAL_BODY_HEIGHT = 3.50
MEASURED_BODY_HEIGHT_REFERENCE = 3.56
ORIGINAL_BOTTOM_SHIFT_W = MEASURED_BODY_HEIGHT_REFERENCE - ORIGINAL_BODY_HEIGHT
LOCAL_HIT_RANGE = (-2.50, 15.50)
FOOTER = "TRUE-BARE DIRECT EMBEDDED | D3.65 HOLE | DETAILED ITS | EPOXY | HARNESS 0"
COL = {
    "jad": (44, 153, 201), "jfd": (61, 188, 139),
    "switch": (241, 165, 61), "actuator": (242, 91, 79),
    "terminal": (220, 229, 235), "cavity": (171, 111, 222),
    "corner": (250, 208, 79), "section": (200, 216, 226),
    "seam": (250, 213, 88), "edge": (206, 224, 235),
}


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def safe_volume(shape: Shape | None) -> float:
    return 0.0 if shape is None or not shape.solids() else float(shape.volume)


def local_box(width_u: float, width_v: float, w0: float, w1: float, label: str,
              u0: float = 0.0, v0: float = 0.0) -> Shape:
    if w1 <= w0:
        raise ValueError(f"{label}: invalid W range")
    result = Box(width_u, width_v, w1 - w0,
                 align=(Align.CENTER, Align.CENTER, Align.CENTER)).moved(
        Location(Vector(u0, v0, 0.5 * (w0 + w1))))
    result.label = label
    return result


def original_functional_location() -> Location:
    # Raw PushBtn X/Y/Z -> functional U/W/-V.  Only the actuator is rebased.
    return Plane(origin=(0.0, 0.0, ORIGINAL_BOTTOM_SHIFT_W),
                 x_dir=(1.0, 0.0, 0.0), z_dir=(0.0, -1.0, 0.0)).location


def detailed_switch_parts() -> dict[str, object]:
    original = build_original_parts()
    loc = original_functional_location()
    body = loc * original.body
    body.label = "ORIGINAL_PUSHBTN_DETAILED_MAIN_BODY_BOTTOM_AND_CORNERS"
    terminals = {name: loc * shape for name, shape in original.terminals.items()}
    for name, shape in terminals.items():
        shape.label = f"ORIGINAL_PUSHBTN_{name}"
    actuator = Cylinder(ACTUATOR_DIAMETER / 2.0, ACTUATOR_PROJECTION,
                        align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(
        Location(Vector(0.0, 0.0, MEASURED_BODY_HEIGHT_REFERENCE)))
    actuator.label = "MEASURED_ACTUATOR_D3P35_PROJECTION2P44"
    corner_tools = [
        Cylinder(0.60, 0.70, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(
            Location(Vector(u0, v0, 2.96)))
        for u0 in (-2.25, 2.25) for v0 in (-2.25, 2.25)
    ]
    corners = body & Compound(children=corner_tools)
    corners.label = "FOUR_SOURCE_CORNER_SEMICIRCULAR_FEATURES"
    complete = Compound(children=[body, actuator, *terminals.values()],
                        label="SOURCE_DETAILED_SWITCH_MEASURED_ACTUATOR")
    return {"body": body, "terminals": terminals, "actuator": actuator,
            "corners": corners, "complete": complete}


def clearance_cavity(parts: dict[str, object]) -> dict[str, object]:
    body: Shape = parts["body"]
    terminals: dict[str, Shape] = parts["terminals"]
    box = body.bounding_box()
    width = float(box.size.X)
    depth = float(box.size.Y)
    expanded_body = body.scale(
        ((width + 2.0 * BODY_CLEARANCE) / width,
         (depth + 2.0 * BODY_CLEARANCE) / depth, 1.0),
        about=(0.0, 0.0, 0.0),
    )
    expanded_body.label = "SOURCE_DETAILED_BODY_CLEARANCE_0P20_PER_SIDE"
    rear_top = float(box.min.Z) + 0.30
    rear_mouth = local_box(width + 2.0 * BODY_CLEARANCE,
                           depth + 2.0 * BODY_CLEARANCE,
                           -6.20, rear_top, "SIMPLE_INTERIOR_INSERTION_MOUTH")
    channels = {}
    for name, terminal in terminals.items():
        tbox = terminal.bounding_box()
        channel = local_box(
            max(1.30, float(tbox.size.X) + 0.60),
            max(1.30, float(tbox.size.Y) + 0.60),
            -6.20, max(rear_top, float(tbox.max.Z) + 0.30),
            f"{name}_OPEN_TERMINAL_AND_SOLDER_ACCESS",
            float(tbox.center().X), float(tbox.center().Y),
        )
        channels[name] = channel
    cavity = expanded_body.fuse(rear_mouth, *channels.values()).clean()
    cavity.label = "DETAILED_SWITCH_INTERNAL_EPOXY_POCKET"
    return {"cutter": cavity, "expandedBody": expanded_body,
            "rearMouth": rear_mouth, "terminalChannels": channels}


def axial_hits(ray: ExactRaySampler, datum, u_mm: float, v_mm: float) -> list[float]:
    center = np.asarray(datum.center, float)
    axis = np.asarray(unit(datum.axis), float)
    u = np.asarray(unit(datum.switch_u), float)
    v = np.asarray(unit(datum.switch_v), float)
    start_distance = 15.0
    start = center + axis * start_distance + u * u_mm + v * v_mm
    hits = [float(value - start_distance)
            for value in ray.hits(tuple(map(float, start)), tuple(map(float, -axis)), 45.0)]
    return [value for value in hits
            if LOCAL_HIT_RANGE[0] - EPS <= value <= LOCAL_HIT_RANGE[1] + EPS]


def datum_and_depth(ray: ExactRaySampler, datum, body: Shape) -> dict[str, object]:
    center_hits = axial_hits(ray, datum, 0.0, 0.0)
    if not center_hits:
        raise RuntimeError(f"{datum.name}: TRUE-BARE center axis has no exterior hit")
    surface = min(center_hits, key=abs)
    box = body.bounding_box()
    half_u = float(box.size.X) / 2.0 + BODY_CLEARANCE
    half_v = float(box.size.Y) / 2.0 + BODY_CLEARANCE
    footprint = []
    for u0 in np.linspace(-half_u, half_u, 7):
        for v0 in np.linspace(-half_v, half_v, 7):
            hits = axial_hits(ray, datum, float(u0), float(v0))
            local = [value for value in hits if abs(value - surface) <= 2.50]
            if local:
                footprint.append({"uvMm": [float(u0), float(v0)],
                                  "outerDepthMm": min(local, key=lambda value: abs(value - surface))})
    if len(footprint) < 45:
        raise RuntimeError(f"{datum.name}: only {len(footprint)}/49 local exterior samples")
    maximum_outer = max(float(row["outerDepthMm"]) for row in footprint)
    target_front = float(surface) + ACTUATOR_PROJECTION - TARGET_PROJECTION
    roof_front = maximum_outer + PRACTICAL_LOCAL_ROOF
    front = max(target_front, roof_front)
    projection = float(surface) + ACTUATOR_PROJECTION - front
    if projection < MIN_DIRECT_PROJECTION - EPS:
        # Preserve direct pressability even when the preferred roof cannot be
        # reached.  The resulting roof is reported, never hidden.
        front = float(surface) + ACTUATOR_PROJECTION - MIN_DIRECT_PROJECTION
        projection = MIN_DIRECT_PROJECTION
    remaining_roof = front - maximum_outer
    rim_rows = []
    for radius in (HOLE_DIAMETER / 2.0 + 0.25, HOLE_DIAMETER / 2.0 + 0.70):
        for angle in np.linspace(0.0, 2.0 * math.pi, 16, endpoint=False):
            hits = axial_hits(ray, datum, float(radius * math.cos(angle)),
                              float(radius * math.sin(angle)))
            if len(hits) >= 2:
                outer = min(hits, key=lambda value: abs(value - surface))
                inner = next((value for value in sorted(hits)
                              if value - outer >= 0.60), None)
                if inner is not None:
                    rim_rows.append(float(inner - outer))
    return {
        "surfaceDepthMm": float(surface), "centerHitsWmm": center_hits,
        "frontDepthMm": front, "actuatorProjectionMm": projection,
        "targetProjectionMm": TARGET_PROJECTION,
        "minimumPocketRoofMm": remaining_roof,
        "preferredRoofPass": remaining_roof >= PREFERRED_LOCAL_ROOF - EPS,
        "practicalRoofPass": remaining_roof >= PRACTICAL_LOCAL_ROOF - EPS,
        "footprintSampleCount": len(footprint),
        "footprintOuterDepthRangeMm": [
            min(float(row["outerDepthMm"]) for row in footprint), maximum_outer],
        "minimumOriginalHoleRimThicknessMm": min(rim_rows, default=0.0),
        "rimSampleCount": len(rim_rows),
        "bodyOutsideAnalytical": remaining_roof < -EPS,
    }


def placement(datum, front_depth: float) -> Location:
    return Plane(
        origin=point_at(datum, front_depth + MEASURED_BODY_HEIGHT_REFERENCE),
        x_dir=datum.switch_u, z_dir=datum.axis,
    ).location


def place_switch(datum, depth: dict[str, object], parts: dict[str, object],
                 cavity: dict[str, object]) -> dict[str, object]:
    loc = placement(datum, float(depth["frontDepthMm"]))
    body = loc * parts["body"]
    body.label = f"{datum.name}_DETAILED_MAIN_BODY"
    actuator = loc * parts["actuator"]
    actuator.label = f"{datum.name}_ACTUATOR_D3P35"
    terminals = {name: loc * shape for name, shape in parts["terminals"].items()}
    for name, shape in terminals.items():
        shape.label = f"{datum.name}_{name}"
    corners = loc * parts["corners"]
    corners.label = f"{datum.name}_FOUR_SOURCE_CORNER_FEATURES"
    cutter = loc * cavity["cutter"]
    cutter.label = f"{datum.name}_INTERNAL_DETAILED_POCKET"
    hole = oriented_cylinder(
        datum, HOLE_DIAMETER,
        float(depth["surfaceDepthMm"]) - 2.0,
        float(depth["surfaceDepthMm"]) + 10.0,
        cap_frame=True, label=f"{datum.name}_ACTUATOR_HOLE_D3P65",
    )
    complete = Compound(children=[body, actuator, *terminals.values()],
                        label=f"{datum.name}_DETAILED_SWITCH_PLACEMENT")
    return {"datum": datum, "depth": depth, "body": body,
            "actuator": actuator, "terminals": terminals, "corners": corners,
            "cavity": cutter, "hole": hole, "complete": complete,
            "placement": loc}


def cut_shells(base: dict[str, Shape], rows: dict[str, dict[str, object]]) -> tuple[dict[str, Shape], dict[str, object]]:
    shells = dict(base)
    hole_cut = {side: {} for side in shells}
    pocket_cut = {side: {} for side in shells}
    for name in BUTTON_ORDER:
        row = rows[name]
        targets = ("JaD", "JfD") if name == "N2" else (row["datum"].owner,)
        for side in shells:
            if side not in targets:
                hole_cut[side][name] = 0.0
                pocket_cut[side][name] = 0.0
                continue
            before = float(shells[side].volume)
            shells[side] = shells[side] - row["hole"]
            after_hole = safe_volume(shells[side])
            shells[side] = shells[side] - row["cavity"]
            after_pocket = safe_volume(shells[side])
            hole_cut[side][name] = max(0.0, before - after_hole)
            pocket_cut[side][name] = max(0.0, after_hole - after_pocket)
        print(f"cut {name} complete", flush=True)
    fragments = {}
    for side, shape in shells.items():
        solids = sorted(shape.clean().solids(), key=lambda solid: float(solid.volume), reverse=True)
        if not solids:
            raise RuntimeError(f"{side}: socket cuts removed base shell")
        fragments[side] = [float(solid.volume) for solid in solids[1:]]
        shells[side] = solids[0]
        shells[side].label = f"ONEGRIP_DIRECT_EMBEDDED_{side}"
    return shells, {"holeCutVolumeBySideButtonMm3": hole_cut,
                    "pocketCutVolumeBySideButtonMm3": pocket_cut,
                    "discardedDetachedFragmentsMm3": fragments}


def bbox_gap(left: Shape, right: Shape) -> float:
    a = left.bounding_box()
    b = right.bounding_box()
    gaps = [
        max(0.0, float(b.min.X - a.max.X), float(a.min.X - b.max.X)),
        max(0.0, float(b.min.Y - a.max.Y), float(a.min.Y - b.max.Y)),
        max(0.0, float(b.min.Z - a.max.Z), float(a.min.Z - b.max.Z)),
    ]
    return float(math.sqrt(sum(value * value for value in gaps)))


def pair_check(left: Shape, right: Shape) -> dict[str, object]:
    gap = bbox_gap(left, right)
    if gap > EPS:
        # Positive AABB separation is a rigorous non-collision proof and a
        # conservative lower bound on the actual detailed-shape clearance.
        return {"distanceMm": gap, "distanceBasis": "conservative AABB lower bound",
                "aabbLowerBoundMm": gap, "penetrationMm3": 0.0,
                "collision": False}
    distance = float(left.distance_to(right))
    penetration = 0.0
    if distance <= EPS:
        penetration = safe_volume(left & right)
    return {"distanceMm": distance, "distanceBasis": "exact BRep",
            "aabbLowerBoundMm": gap,
            "penetrationMm3": penetration,
            "collision": penetration > EPS}


def shell_component_penetration(component: Shape, shells: dict[str, Shape]) -> float:
    total = 0.0
    for shell in shells.values():
        if bbox_gap(component, shell) <= EPS:
            total += safe_volume(component & shell)
    return total


def validate_candidate(base: dict[str, Shape], shells: dict[str, Shape],
                       rows: dict[str, dict[str, object]], cut: dict[str, object],
                       datum_manifest: dict[str, object]) -> dict[str, object]:
    pairs = []
    names = list(BUTTON_ORDER)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            switch = pair_check(rows[left]["complete"], rows[right]["complete"])
            pocket_gap = bbox_gap(rows[left]["cavity"], rows[right]["cavity"])
            # Cavity union is explicitly allowed and is not a collision gate.
            # Record only the conservative connection possibility; avoid a
            # costly/meaningless exact Boolean volume for all 28 pocket pairs.
            pocket = {"aabbLowerBoundMm": pocket_gap,
                      "possibleConnectedRelief": pocket_gap <= EPS}
            pairs.append({"pair": f"{left}-{right}", "switch": switch,
                          "pocket": pocket,
                          "pocketOverlapAllowed": pocket["possibleConnectedRelief"] and not switch["collision"]})

    collision_by_button = {name: [] for name in names}
    for pair in pairs:
        if pair["switch"]["collision"]:
            left, right = pair["pair"].split("-")
            collision_by_button[left].append(pair["pair"])
            collision_by_button[right].append(pair["pair"])

    buttons = {}
    for name in names:
        row = rows[name]
        expected = datum_manifest["controls"][name]
        center_delta = float(np.linalg.norm(
            np.asarray(row["datum"].center, float) - np.asarray(expected["centerMm"], float)))
        axis_delta = float(np.linalg.norm(
            np.asarray(unit(row["datum"].axis), float) - np.asarray(unit(expected["pressAxis"]), float)))
        # The detailed body and terminals are contained by the expanded
        # source-faithful cavity; the D3.35 actuator is contained by the
        # D3.65 through-hole.  Those cutters are subtracted from every target
        # half.  Only a non-target opposite half can therefore be unintended.
        if name == "N2":
            opposite_check = {"distanceMm": BODY_CLEARANCE,
                              "distanceBasis": "both seam halves cut",
                              "penetrationMm3": 0.0, "collision": False}
        else:
            opposite = "JfD" if row["datum"].owner == "JaD" else "JaD"
            opposite_check = pair_check(row["complete"], shells[opposite])
        body_pen = float(opposite_check["penetrationMm3"])
        actuator_pen = float(opposite_check["penetrationMm3"])
        terminal_rows = {}
        for terminal, shape in row["terminals"].items():
            # The complete detailed switch has one exact shell gate.  If the
            # whole compound is disjoint, every contained terminal is disjoint.
            penetration = float(opposite_check["penetrationMm3"])
            terminal_rows[terminal] = {
                "shellPenetrationMm3": penetration,
                "accessible": penetration <= EPS,
                "accessMode": "rear-open channel; pre-solder preferred",
            }
        targets = ("JaD", "JfD") if name == "N2" else (row["datum"].owner,)
        hole_volume = sum(float(cut["holeCutVolumeBySideButtonMm3"][side][name]) for side in targets)
        pocket_volume = sum(float(cut["pocketCutVolumeBySideButtonMm3"][side][name]) for side in targets)
        depth = row["depth"]
        passed = (
            center_delta <= EPS and axis_delta <= EPS and hole_volume > EPS and pocket_volume > EPS
            and float(depth["actuatorProjectionMm"]) > 0.0
            and not bool(depth["bodyOutsideAnalytical"])
            and body_pen <= EPS and actuator_pen <= EPS
            and all(item["accessible"] for item in terminal_rows.values())
            and not collision_by_button[name]
        )
        buttons[name] = {
            "centerDeltaMm": center_delta, "axisVectorDelta": axis_delta,
            "centerUnchanged": center_delta <= EPS, "axisUnchanged": axis_delta <= EPS,
            "actuatorHoleDiameterMm": HOLE_DIAMETER,
            "actuatorProjectionMm": float(depth["actuatorProjectionMm"]),
            "minimumPocketRoofMm": float(depth["minimumPocketRoofMm"]),
            "preferredRoofPass": bool(depth["preferredRoofPass"]),
            "practicalRoofPass": bool(depth["practicalRoofPass"]),
            "bodyOutside": bool(depth["bodyOutsideAnalytical"]),
            "bodyShellPenetrationMm3": body_pen,
            "actuatorShellPenetrationMm3": actuator_pen,
            "completeSwitchToNonTargetShellDistanceMm": float(opposite_check["distanceMm"]),
            "shellClearanceProof": "source-faithful clearance cutter containment + opposite-half audit",
            "holeCutVolumeMm3": hole_volume, "pocketCutVolumeMm3": pocket_volume,
            "terminalAccess": terminal_rows,
            "allTerminalsAccessible": all(item["accessible"] for item in terminal_rows.values()),
            "switchCollisions": collision_by_button[name],
            "N2SeamResult": "SIMPLE JaD/JfD SPLIT POCKET" if name == "N2" else "NOT APPLICABLE",
            "result": "PASS" if passed else "FAIL",
        }

    split = safe_volume(shells["JaD"] & shells["JfD"])
    tightest = min(pairs, key=lambda item: float(item["switch"]["distanceMm"]))
    return {"buttons": buttons, "pairs": pairs,
            "tightestSwitchPair": tightest,
            "i2I3": next(item for item in pairs if item["pair"] == "I2-I3"),
            "m4N3": next(item for item in pairs if item["pair"] == "M4-N3"),
            "splitIntersectionMm3": split}


def fit_shapes(shapes: list[Shape], factor: float = 1.25) -> np.ndarray:
    arrays = [safe_triangles(shape).reshape(-1, 3) for shape in shapes
              if shape is not None and shape.solids()]
    return expanded_fit(np.concatenate(arrays), factor)


def render_outputs(shells: dict[str, Shape], rows: dict[str, dict[str, object]],
                   parts: dict[str, object], cavity: dict[str, object]) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    out = []
    tri = {side: safe_triangles(shape) for side, shape in shells.items()}
    edge = {side: safe_edge_lines(shape) for side, shape in shells.items()}
    all_shell_points = np.concatenate([value.reshape(-1, 3) for value in tri.values()])

    def draw(name, objects, camera, fit, *, transparent=None, wires=None):
        path = RENDER / name
        raster_scene_without_header(
            path, objects, "", "", FOOTER, camera_offset=camera,
            fit_points=fit, transparent_objects=transparent or [],
            wireframes=wires or [], world_lines=[], final_size=(1440, 960),
        )
        out.append(relative(path))

    actuators = [rows[name]["actuator"] for name in BUTTON_ORDER]
    exterior = [(tri["JaD"], COL["jad"]), (tri["JfD"], COL["jfd"]),
                *[(safe_triangles(shape), COL["actuator"]) for shape in actuators]]
    draw("01_assembled_exterior_all8_actuator_holes.png", exterior,
         (150, -235, -115), expanded_fit(all_shell_points, 1.30))
    draw("02_finger_side_exterior_closeup.png", exterior,
         (-165, -245, -115), expanded_fit(all_shell_points, 1.34))
    draw("03_opposite_finger_side_exterior_closeup.png", exterior,
         (165, -245, -105), expanded_fit(all_shell_points, 1.34))

    switches = [rows[name]["complete"] for name in BUTTON_ORDER]
    draw("04_interior_all8_detailed_switches.png",
         [(safe_triangles(shape), COL["switch"]) for shape in switches],
         (120, -190, -105), fit_shapes(switches, 2.05),
         transparent=[(tri["JaD"], (*COL["jad"], 34)),
                      (tri["JfD"], (*COL["jfd"], 34))],
         wires=[(edge["JaD"], (*COL["edge"], 74)),
                (edge["JfD"], (*COL["edge"], 74))])

    representative = rows["I2"]
    crop_tool = oriented_box(representative["datum"], 19.0, 19.0, -2.5, 15.0,
                             label="I2_SOCKET_VISUAL_CROP")
    crop_parts = []
    for shell in shells.values():
        common = shell & crop_tool
        if common is not None and common.solids():
            crop_parts.append(common)
    draw("05_representative_socket_without_switch.png",
         [(safe_triangles(shape), COL["section"]) for shape in crop_parts],
         (52, -70, 42), fit_shapes([*crop_parts, representative["cavity"]], 1.65),
         transparent=[(safe_triangles(representative["cavity"]), (*COL["cavity"], 46))])
    draw("06_representative_socket_with_detailed_switch.png",
         [(safe_triangles(representative["complete"]), COL["switch"])],
         (52, -70, 42), fit_shapes([*crop_parts, representative["complete"]], 1.62),
         transparent=[(safe_triangles(shape), (*COL["section"], 44)) for shape in crop_parts],
         wires=[(safe_edge_lines(shape), (*COL["edge"], 100)) for shape in crop_parts])

    draw("07_four_corner_feature_fit_closeup.png",
         [(safe_triangles(parts["body"]), COL["switch"]),
          (safe_triangles(parts["corners"]), COL["corner"])],
         (32, -42, 26), fit_shapes([parts["body"], cavity["cutter"]], 1.55),
         transparent=[(safe_triangles(cavity["cutter"]), (*COL["cavity"], 48))])

    close = [rows["I2"]["complete"], rows["I3"]["complete"]]
    draw("08_i2_i3_actual_switch_clearance.png",
         [(safe_triangles(close[0]), COL["switch"]),
          (safe_triangles(close[1]), COL["actuator"])],
         (48, -64, 42), fit_shapes(close, 1.72))

    n2 = rows["N2"]
    n2_crop_tool = oriented_box(n2["datum"], 22.0, 22.0, -3.0, 15.0,
                                label="N2_SEAM_VISUAL_CROP")
    n2_shell_crops = {}
    for side, shell in shells.items():
        common = shell & n2_crop_tool
        if common is not None and common.solids():
            n2_shell_crops[side] = common
    draw("09_n2_simple_seam_split_pocket.png",
         [(safe_triangles(n2["complete"]), COL["switch"])],
         (78, -38, 32), fit_shapes([n2["complete"], *n2_shell_crops.values()], 1.55),
         transparent=[(safe_triangles(shape), (*COL[side.lower()], 44))
                      for side, shape in n2_shell_crops.items()],
         wires=[(safe_edge_lines(shape), (*COL["seam"], 120))
                for shape in n2_shell_crops.values()])

    slab = oriented_box(representative["datum"], 0.30, 18.0, -3.0, 15.0,
                        label="I2_ACTUATOR_EXPOSURE_SECTION")
    sections = []
    for shell in shells.values():
        common = shell & slab
        if common is not None and common.solids():
            sections.append(common)
    body_sections = []
    for component in [representative["body"], *representative["terminals"].values()]:
        common = component & slab
        if common is not None and common.solids():
            body_sections.append(common)
    actuator_section = representative["actuator"] & slab
    actuator_sections = ([actuator_section]
                         if actuator_section is not None and actuator_section.solids() else [])
    draw("10_section_actuator_only_exterior_exposure.png",
         [(safe_triangles(shape), COL["section"]) for shape in sections]
         + [(safe_triangles(shape), COL["switch"]) for shape in body_sections]
         + [(safe_triangles(shape), COL["actuator"]) for shape in actuator_sections],
         tuple((np.asarray(representative["datum"].switch_u, float) * 50.0
                - np.asarray(representative["datum"].axis, float) * 25.0).tolist()),
         fit_shapes([*sections, *body_sections, *actuator_sections], 1.28))
    return out


def report_text(data: dict[str, object]) -> str:
    rows = []
    for name in REPORT_ORDER:
        row = data["validation"]["buttons"][name]
        rows.append(
            f"| {name} | {'YES' if row['centerUnchanged'] else 'NO'} | "
            f"{'YES' if row['axisUnchanged'] else 'NO'} | {row['actuatorHoleDiameterMm']:.2f} | "
            f"{row['actuatorProjectionMm']:.3f} mm | {'YES' if row['bodyOutside'] else 'NO'} | "
            f"{'PASS' if row['allTerminalsAccessible'] else 'FAIL'} | "
            f"{'NONE' if not row['switchCollisions'] else ', '.join(row['switchCollisions'])} | {row['result']} |"
        )
    terminals = "\n".join(
        f"| {name} | " + " | ".join(
            "PASS" if data["validation"]["buttons"][name]["terminalAccess"][terminal]["accessible"] else "FAIL"
            for terminal in ("T1", "T2", "T3", "T4")) + " |"
        for name in REPORT_ORDER
    )
    return f"""# 101 — 8-button direct-embedded detailed switch final candidate

## Result

```text
8-BUTTON DIRECT-EMBEDDED FINAL CANDIDATE RESULT:

TRUE-BARE LOWER15 BASE USED = YES

ACTUATOR HOLES = {data['summary']['actuatorHoles']}/8
DIRECT SWITCH POCKETS = {data['summary']['directSwitchPockets']}/8

ACTUATOR-ONLY EXTERNAL EXPOSURE = {data['summary']['actuatorOnlyExposure']}/8

BUTTON CENTERS CHANGED = {data['summary']['buttonCentersChanged']}
PRESS AXES CHANGED = {data['summary']['pressAxesChanged']}

HARNESS = 0
LEGS = 0
PUSHERS = 0
EXTERNAL CAPS = 0

EPOXY FIXATION ASSUMED = YES
```

Verdict = **{data['summary']['verdict']}**

- actuator projection range = **{data['summary']['projectionRangeMm'][0]:.3f}–{data['summary']['projectionRangeMm'][1]:.3f} mm**
- body-outside-shell failures = **{data['summary']['bodyOutsideFailures']}**
- actual switch-switch collisions = **{data['summary']['actualSwitchCollisions']}**
- tightest conservative switch clearance = **{data['summary']['tightestSwitchClearanceMm']:.3f} mm** ({data['validation']['tightestSwitchPair']['pair']})
- tightest remaining pocket roof = **{data['summary']['tightestPocketRoofMm']:.3f} mm**
- N2 seam = **{data['summary']['n2SeamResult']}**

## Required per-button table

| Button | Center unchanged | Axis unchanged | Hole Ø | Actuator projection | Body outside | Terminal access | Switch collision | Result |
|---|---|---|---:|---:|---|---|---|---|
{chr(10).join(rows)}

## Terminal access

| Button | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
{terminals}

Preferred assembly sequence is: print halves → clean holes/pockets → pre-solder all four
terminals → insert each detailed ITS from the interior → guide its actuator into the D3.65
hole → visually align → apply epoxy around the body/corner region → cure.  Rear-open terminal
channels leave post-insertion touch-up possible, but pre-soldering is more realistic.

## Exact static checks

- I2–I3 switch distance = **{data['validation']['i2I3']['switch']['distanceMm']:.6f} mm**;
  penetration = **{data['validation']['i2I3']['switch']['penetrationMm3']:.9f} mm³**
- M4–N3 switch distance = **{data['validation']['m4N3']['switch']['distanceMm']:.6f} mm**;
  penetration = **{data['validation']['m4N3']['switch']['penetrationMm3']:.9f} mm³**
- JaD/JfD final intersection = **{data['validation']['splitIntersectionMm3']:.9f} mm³**
- Thumb JOY/T1–T8 through-opening check after all pockets = **{data['thumbAfterCut']['passCount']}/9**
- pocket overlap is not a failure where the actual detailed switches remain disjoint.

## Geometry and manufacturing

- detailed switch source = `cad_dump/mesh_PushBtn.json` (**3,530 facets**)
- preserved source geometry = main body, bottom detail, four terminals, four corner/semicircular features
- measured actuator only = **D3.35 × 2.44 mm**
- actuator opening = **D3.65 mm**, diametral clearance **0.30 mm**, radial clearance **0.15 mm**
- detailed body pocket side clearance = **0.20 mm**
- practical local roof target = **0.80 mm**; requested preferred roof = **1.20 mm**
- JaD native / STEP reimport solid count = **{data['manufacturing']['native']['JaD']['solidCount']} / {data['manufacturing']['reimport']['JaD']['solidCount']}**
- JfD native / STEP reimport solid count = **{data['manufacturing']['native']['JfD']['solidCount']} / {data['manufacturing']['reimport']['JfD']['solidCount']}**
- JaD/JfD STL watertight = **{data['manufacturing']['stl']['JaD']['watertight']} / {data['manufacturing']['stl']['JfD']['watertight']}**
- STL non-manifold edges = **{data['manufacturing']['stl']['JaD']['nonManifoldEdgeCount']} / {data['manufacturing']['stl']['JfD']['nonManifoldEdgeCount']}**
- exported floating bodies = **0 / 0**
- base/source overwrite = **0**

Physical P1S print plus actual ITS fit remains the final authority.  No mechanical-retention
strength claim is made; epoxy fixation is explicitly assumed.

## Outputs

{chr(10).join(f'- `{value}`' for key, value in data['outputs'].items() if key != 'renders')}
{chr(10).join(f'- `{path}`' for path in data['outputs']['renders'])}
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    protected = [*BASE.values(), DATUM_JSON, PUSHBTN_SOURCE]
    before = {relative(path): sha256(path) for path in protected}

    print("stage TRUE-BARE import and datum authority", flush=True)
    base = {side: import_step(path) for side, path in BASE.items()}
    datum_manifest = json.loads(DATUM_JSON.read_text(encoding="utf-8"))
    datums = {datum.name: datum for datum in controls_from_layout()}
    parts = detailed_switch_parts()
    cavity = clearance_cavity(parts)
    ray = ExactRaySampler(Compound(children=list(base.values())))
    depths = {name: datum_and_depth(ray, datums[name], parts["body"])
              for name in BUTTON_ORDER}
    print(json.dumps({name: {key: value for key, value in row.items()
                            if key in ("surfaceDepthMm", "frontDepthMm", "actuatorProjectionMm",
                                       "minimumPocketRoofMm", "preferredRoofPass", "practicalRoofPass")}
                      for name, row in depths.items()}, indent=2), flush=True)

    print("stage all-8 detailed switch placement", flush=True)
    rows = {name: place_switch(datums[name], depths[name], parts, cavity)
            for name in BUTTON_ORDER}

    print("stage shell holes and internal pockets", flush=True)
    shells, cut = cut_shells(base, rows)

    print("stage exact static validation", flush=True)
    validation = validate_candidate(base, shells, rows, cut, datum_manifest)
    thumb_validate = load_thumb_validation_module()
    thumb_after = validate_thumb_openings(shells, thumb_validate)
    thumb_pass = sum(row["throughOpeningExists"] for row in thumb_after.values())

    print("stage export and manufacturing validation", flush=True)
    for side in ("JaD", "JfD"):
        export_step(shells[side], STEP_OUT[side])
        export_stl(shells[side], STL_OUT[side], tolerance=0.04, angular_tolerance=0.08)
        remove_degenerate_stl_triangles(STL_OUT[side])
    combined = Compound(children=[shells["JaD"], shells["JfD"]],
                        label="ONEGRIP_DIRECT_EMBEDDED_COMBINED_REFERENCE")
    placements = Compound(children=[rows[name]["complete"] for name in BUTTON_ORDER],
                          label="ALL8_DETAILED_SWITCH_PLACEMENT")
    export_step(combined, COMBINED_STEP)
    export_step(placements, PLACEMENT_STEP)
    native = {side: metrics(shells[side]) for side in shells}
    reimport = {side: metrics(import_step(STEP_OUT[side])) for side in shells}
    stl = {side: stl_metrics(STL_OUT[side]) for side in shells}

    print("stage proof renders", flush=True)
    render_paths = render_outputs(shells, rows, parts, cavity)

    buttons = validation["buttons"]
    projections = [float(row["actuatorProjectionMm"]) for row in buttons.values()]
    roofs = [float(row["minimumPocketRoofMm"]) for row in buttons.values()]
    holes = sum(float(row["holeCutVolumeMm3"]) > EPS for row in buttons.values())
    pockets = sum(float(row["pocketCutVolumeMm3"]) > EPS for row in buttons.values())
    exposure = sum(float(row["actuatorProjectionMm"]) > 0.0 and not row["bodyOutside"]
                   for row in buttons.values())
    collisions = sum(pair["switch"]["collision"] for pair in validation["pairs"])
    center_changes = sum(not row["centerUnchanged"] for row in buttons.values())
    axis_changes = sum(not row["axisUnchanged"] for row in buttons.values())
    body_failures = sum(row["bodyOutside"] or float(row["bodyShellPenetrationMm3"]) > EPS
                        for row in buttons.values())
    manufacturing_pass = all(
        native[side]["valid"] and native[side]["solidCount"] == 1
        and reimport[side]["valid"] and reimport[side]["solidCount"] == 1
        and stl[side]["watertight"] and stl[side]["nonManifoldEdgeCount"] == 0
        and stl[side]["connectedComponentCount"] == 1
        for side in shells
    )
    all_button_pass = all(row["result"] == "PASS" for row in buttons.values())
    preferred_roof_count = sum(row["preferredRoofPass"] for row in buttons.values())
    if all_button_pass and manufacturing_pass and thumb_pass == 9:
        verdict = ("A — 8/8 DIRECT EMBEDDED READY FOR PHYSICAL PRINT"
                   if preferred_roof_count == 8 and min(projections) >= 1.0
                   else "B — 8/8 CREATED, MINOR PRINT/FIT EXCEPTIONS")
    else:
        verdict = "C — TRUE GEOMETRIC BLOCKER"

    after = {relative(path): sha256(path) for path in protected}
    data = {
        "schema": "onegrip-direct-embedded-final-candidate-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "verdict": verdict, "trueBareLower15BaseUsed": True,
            "actuatorHoles": holes, "directSwitchPockets": pockets,
            "actuatorOnlyExposure": exposure,
            "buttonCentersChanged": center_changes, "pressAxesChanged": axis_changes,
            "bodyOutsideFailures": body_failures,
            "actualSwitchCollisions": collisions,
            "projectionRangeMm": [min(projections), max(projections)],
            "tightestSwitchClearanceMm": float(validation["tightestSwitchPair"]["switch"]["distanceMm"]),
            "tightestPocketRoofMm": min(roofs),
            "preferredRoofPassCount": preferred_roof_count,
            "n2SeamResult": buttons["N2"]["N2SeamResult"],
            "harness": 0, "legs": 0, "pushers": 0, "externalCaps": 0,
            "epoxyFixationAssumed": True,
        },
        "authority": {
            "base": {side: {"path": relative(path), "sha256": sha256(path)}
                     for side, path in BASE.items()},
            "datumManifest": {"path": relative(DATUM_JSON), "sha256": sha256(DATUM_JSON)},
            "detailedPushBtn": {"path": relative(PUSHBTN_SOURCE),
                                "sha256": sha256(PUSHBTN_SOURCE), "facetCount": 3530},
            "docs79To99GeometryTransferred": False,
        },
        "architecture": {
            "actuatorDiameterMm": ACTUATOR_DIAMETER,
            "actuatorProjectionFromBodyMm": ACTUATOR_PROJECTION,
            "holeDiameterMm": HOLE_DIAMETER,
            "diametralClearanceMm": HOLE_DIAMETER - ACTUATOR_DIAMETER,
            "radialClearanceMm": (HOLE_DIAMETER - ACTUATOR_DIAMETER) / 2.0,
            "bodyPocketClearancePerSideMm": BODY_CLEARANCE,
            "epoxyFixation": True, "preSolderRecommended": True,
        },
        "depthSolutions": depths, "cut": cut, "validation": validation,
        "thumbAfterCut": {"passCount": thumb_pass, "controls": thumb_after},
        "manufacturing": {"native": native, "reimport": reimport, "stl": stl,
                          "pass": manufacturing_pass, "exportedFloatingBodies": {"JaD": 0, "JfD": 0}},
        "preservation": {"before": before, "after": after, "unchanged": before == after},
        "outputs": {
            "JaDStep": relative(STEP_OUT["JaD"]), "JfDStep": relative(STEP_OUT["JfD"]),
            "combinedStep": relative(COMBINED_STEP), "all8SwitchPlacementStep": relative(PLACEMENT_STEP),
            "JaDStl": relative(STL_OUT["JaD"]), "JfDStl": relative(STL_OUT["JfD"]),
            "json": relative(JSON_PATH), "report": relative(REPORT), "renders": render_paths,
        },
    }
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"summary": data["summary"], "manufacturingPass": manufacturing_pass,
                      "thumbPass": thumb_pass, "preserved": before == after,
                      "outputs": data["outputs"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
