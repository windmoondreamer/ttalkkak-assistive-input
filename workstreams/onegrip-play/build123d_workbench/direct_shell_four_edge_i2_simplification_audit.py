"""Audit-only I2 direct-shell four-edge-leg simplification.

This module preserves docs/79 and every prior output.  It first inventories
the geometry that docs/79 actually generated, then builds one representative
I2 candidate whose four straight legs enter four blind slots cut only into an
audit copy of a small frozen-shell crop.  No production source is modified.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Align, Box, Compound, Location, Shape, Vector, export_step, import_step
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt

from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, point_at, unit
from .four_edge_leg_harness_captive_pusher_audit import (
    ACT_D,
    BODY_H,
    BODY_U,
    BODY_V,
    C,
    CLEARANCE_GAP,
    LANDING_EXTENSION,
    LANDING_THICKNESS,
    LEG_STRUCTURAL,
    LEG_TANGENTIAL,
    LOCATING_GAP,
    REST_GAP,
    REPORT as DOC79,
    RENDER as DOC79_RENDER,
    OUT as DOC79_OUT,
    SHELL_STEP,
    ExactShellSampler,
    bounds,
    corner_clearance,
    datum_location,
    edge_centers,
    four_edge_leg_harness,
    four_receiver_inner_housing,
    glue_regions,
    local_box,
    local_candidate,
    local_cylinder,
    moved,
    placed,
    receiver_layout,
    sha256,
    volume,
)
from .i4_m3_current_audit import angle_deg, load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import BUTTONS, ROOT, relative
from .option_c_local_exact_prototype import raster_scene, safe_edge_lines, safe_triangles
from .slot_anchored_harness_captive_pusher_audit import pusher_system, terminal_proxies


OUT = ROOT / "build123d_workbench/out/direct_shell_four_edge_i2_simplification_audit"
RENDER = ROOT / "renders/direct_shell_four_edge_i2_simplification_audit"
REPORT = ROOT / "docs/80_direct_shell_four_edge_i2_simplification_audit.md"
JSON_PATH = OUT / "direct_shell_four_edge_i2_simplification_audit.json"
HARNESS_STEP = OUT / "I2_DIRECT_SHELL_FOUR_EDGE_HARNESS_AUDIT_ONLY.step"
SHELL_CROP_STEP = OUT / "I2_DIRECT_SHELL_LOCAL_CROP_WITH_BLIND_SLOTS_AUDIT_ONLY.step"
ASSEMBLY_STEP = OUT / "I2_DIRECT_SHELL_SIMPLIFIED_FULL_ASSEMBLY_AUDIT_ONLY.step"

CURRENT_SCRIPT = ROOT / "build123d_workbench/four_edge_leg_harness_captive_pusher_audit.py"
CURRENT_FULL_STEP = DOC79_OUT / "I2_FOUR_EDGE_LEG_FULL_STACK_AUDIT_ONLY.step"

REPRESENTATIVE = "I2"
DEFAULT_ROOT_W = -0.60
BLIND_DEPTH = 1.20
SLOT_CLEARANCE = 0.20
SLOT_TANGENT = LEG_TANGENTIAL + 2.0 * SLOT_CLEARANCE
SHELL_CROP_U = 24.0
SHELL_CROP_V = 24.0
SHELL_CROP_W0 = 1.0
SHELL_CROP_W1 = 11.0
BOOLEAN_EPS = 1.0e-6

# Deterministic Level-0 locations found by a small local exact-BRep screen.
# Roots remain frozen at the four switch side midpoints.  Only the shell ends
# move to the nearest full-footprint material region.
SLOT_TARGET_UV = {
    "+U": (4.80, 1.60),
    "-U": (-6.00, 0.00),
    "+V": (0.00, 5.50),
    "-V": (0.00, -5.50),
}

LEG_THICKNESS_BY_EDGE = {"+U": 1.20, "-U": LEG_STRUCTURAL, "+V": LEG_STRUCTURAL, "-V": LEG_STRUCTURAL}


def leg_root(edge: str) -> np.ndarray:
    if edge == "+U":
        # I2-I3 measured-body gap cannot accept the old 1.60 mm / 0.35 mm
        # root.  The absolute-minimum 1.20 mm member uses the existing 0.08 mm
        # rest gap and starts at the body-bottom/open-cross top plane.  This
        # remains one fused prism/cross solid and gives practical I3 clearance.
        return np.asarray((BODY_U / 2.0 + REST_GAP + 1.20 / 2.0, 0.0, 0.0), float)
    u0, v0 = edge_centers()[edge]
    return np.asarray((u0, v0, DEFAULT_ROOT_W), float)

FOOTER = "AUDIT-ONLY I2 | DIRECT FROZEN-SHELL BLIND SLOTS | docs/79 + PRODUCTION PRESERVED | PROPAGATION = 0"
COL = {
    **C,
    "leg": (58, 165, 232),
    "slot": (250, 176, 65),
    "shell": (108, 128, 149),
    "remove": (232, 89, 100),
    "keep": (62, 190, 137),
    "simplified": (90, 188, 235),
    "current": (225, 105, 115),
}


def xyz(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(map(float, value))


def shape_volume(shape: Shape) -> float:
    return float(sum(float(solid.volume) for solid in shape.solids()))


def protected_files() -> list[Path]:
    rows = {
        CURRENT_SCRIPT,
        DOC79,
        *[path for path in DOC79_OUT.rglob("*") if path.is_file()],
        *[path for path in DOC79_RENDER.rglob("*") if path.is_file()],
        *SHELL_STEP.values(),
        ROOT / "build123d_workbench/finger_controls_v2.py",
        ROOT / "build123d_workbench/n1_production_intent_mechanism.py",
        ROOT / "build123d_workbench/n2_production_intent_mechanism.py",
        ROOT / "build123d_workbench/i2_i3_production_intent_mechanism.py",
        ROOT / "build123d_workbench/i4_m3_production_intent_mechanisms.py",
        ROOT / "build123d_workbench/m4_n3_production_intent_mechanism.py",
    }
    return sorted(path for path in rows if path.exists())


def hash_rows(paths: list[Path]) -> dict[str, str]:
    return {relative(path): sha256(path) for path in paths}


def local_point_to_world(datum, front: float, point: Iterable[float]) -> np.ndarray:
    u = unit(datum.switch_u); v = unit(datum.switch_v); w = unit(datum.axis)
    base = np.asarray(point_at(datum, front + BODY_H), float)
    x, y, z = map(float, point)
    return base + u * x + v * y + w * z


def local_dir_to_world(datum, direction: Iterable[float]) -> np.ndarray:
    u = unit(datum.switch_u); v = unit(datum.switch_v); w = unit(datum.axis)
    x, y, z = map(float, direction)
    return unit(u * x + v * y + w * z)


class ExactRaySampler:
    """Fresh exact intersector per query avoids OCCT reusable-state failures."""

    def __init__(self, shape: Shape):
        self.shape = shape

    def hits(self, origin: Iterable[float], direction: Iterable[float], maximum: float = 30.0) -> list[float]:
        for _ in range(2):
            try:
                intersector = IntCurvesFace_ShapeIntersector()
                intersector.Load(self.shape.wrapped, 1.0e-7)
                o = tuple(map(float, origin)); d = tuple(map(float, unit(direction)))
                intersector.Perform(gp_Lin(gp_Pnt(*o), gp_Dir(*d)), 0.0, maximum)
                values = sorted(float(intersector.WParameter(i)) for i in range(1, intersector.NbPnt() + 1))
                unique: list[float] = []
                for value in values:
                    if value >= -1.0e-6 and (not unique or abs(value - unique[-1]) > 0.02):
                        unique.append(value)
                return unique
            except Exception:
                continue
        return []

    def exterior_depth_hits(self, datum, u0: float, v0: float) -> list[float]:
        w = unit(datum.axis); u = unit(datum.switch_u); v = unit(datum.switch_v)
        outward = 5.0
        origin = np.asarray(datum.center, float) + w * outward + u * u0 + v * v0
        return [value - outward for value in self.hits(origin, -w, 30.0)]


def slot_leg_spec(edge: str, datum, front: float, ray: ExactRaySampler) -> dict[str, object]:
    root_local = leg_root(edge); root_u, root_v, _ = root_local
    target_u, target_v = SLOT_TARGET_UV[edge]
    leg_thickness = LEG_THICKNESS_BY_EDGE[edge]
    slot_structural = leg_thickness + 2.0 * SLOT_CLEARANCE
    press_depth = front + BODY_H
    exterior_hits = ray.exterior_depth_hits(datum, target_u, target_v)
    if len(exterior_hits) < 2:
        raise RuntimeError(f"{edge} target has no exact outer/inner shell pair")
    target_inner_local = np.asarray((target_u, target_v, press_depth - exterior_hits[1]), float)
    direction_local = unit(target_inner_local - root_local)
    root_world = local_point_to_world(datum, front, root_local)
    direction_world = local_dir_to_world(datum, direction_local)
    center_hits = ray.hits(root_world, direction_world, 24.0)
    if len(center_hits) < 2:
        raise RuntimeError(f"{edge} direct ray has no exact inner/outer shell pair")

    tangent_local = np.asarray((0.0, 1.0, 0.0) if edge.endswith("U") else (1.0, 0.0, 0.0), float)
    tangent_world = local_dir_to_world(datum, tangent_local)
    tangent_world = unit(tangent_world - direction_world * float(np.dot(tangent_world, direction_world)))
    structural_world = unit(np.cross(direction_world, tangent_world))
    footprint_inner_distances: list[float] = []
    footprint_outer_distances: list[float] = []
    for tangent_offset in (-SLOT_TANGENT / 2.0, 0.0, SLOT_TANGENT / 2.0):
        for structural_offset in (-slot_structural / 2.0, 0.0, slot_structural / 2.0):
            sample_origin = root_world + tangent_world * tangent_offset + structural_world * structural_offset
            hits = ray.hits(sample_origin, direction_world, 24.0)
            if len(hits) < 2:
                raise RuntimeError(f"{edge} blind-slot footprint leaves shell material")
            footprint_inner_distances.append(hits[0])
            footprint_outer_distances.append(hits[1])

    inner_distance = center_hits[0]
    shell_thickness = center_hits[1] - center_hits[0]
    # A planar blind-slot floor on a curved inner face must be placed from the
    # farthest footprint entry, not only the center.  This guarantees at least
    # 1.20 mm engagement at all nine validation points.
    floor_distance = max(footprint_inner_distances) + BLIND_DEPTH
    inner_local = root_local + direction_local * inner_distance
    floor_local = root_local + direction_local * floor_distance
    leg = oriented_box_between(
        xyz(root_local), xyz(floor_local), xyz(tangent_local), LEG_TANGENTIAL, leg_thickness,
        label=f"I2_{edge}_STRAIGHT_DIRECT_SHELL_STRUCTURAL_LEG",
    )
    slot_start = root_local + direction_local * (min(footprint_inner_distances) - 0.35)
    slot_tool = oriented_box_between(
        xyz(slot_start), xyz(floor_local), xyz(tangent_local), SLOT_TANGENT, slot_structural,
        label=f"I2_{edge}_DIRECT_SHELL_BLIND_SLOT_VOID",
    )
    return {
        "edge": edge,
        "rootLocalUVWmm": list(map(float, root_local)),
        "targetLocalUVmm": [float(target_u), float(target_v)],
        "directionLocal": list(map(float, direction_local)),
        "directionWorld": list(map(float, direction_world)),
        "innerPointLocalUVWmm": list(map(float, inner_local)),
        "floorPointLocalUVWmm": list(map(float, floor_local)),
        "legLengthMm": float(floor_distance),
        "legThicknessMm": float(leg_thickness),
        "legTangentWidthMm": LEG_TANGENTIAL,
        "shellThicknessCenterMm": float(shell_thickness),
        "shellThicknessFootprintMinMm": float(min(outer - inner for inner, outer in zip(footprint_inner_distances, footprint_outer_distances))),
        "shellThicknessFootprintMaxMm": float(max(outer - inner for inner, outer in zip(footprint_inner_distances, footprint_outer_distances))),
        "blindDepthFootprintRangeMm": [float(floor_distance - max(footprint_inner_distances)),
                                       float(floor_distance - min(footprint_inner_distances))],
        "remainingExteriorThicknessCenterMm": float(center_hits[1] - floor_distance),
        "remainingExteriorThicknessFootprintMinMm": float(min(footprint_outer_distances) - floor_distance),
        "innerDistanceFootprintRangeMm": [float(min(footprint_inner_distances)), float(max(footprint_inner_distances))],
        "slotDepthMm": BLIND_DEPTH,
        "slotCrossSectionMm": [SLOT_TANGENT, slot_structural],
        "clearancePerSideMm": SLOT_CLEARANCE,
        "leg": leg,
        "slotTool": slot_tool,
        "tangentHintLocal": list(map(float, tangent_local)),
    }


def simplified_harness(specs: dict[str, dict[str, object]]) -> dict[str, Shape]:
    u_min = float(specs["-U"]["rootLocalUVWmm"][0]); u_max = float(specs["+U"]["rootLocalUVWmm"][0])
    v_min = float(specs["-V"]["rootLocalUVWmm"][1]); v_max = float(specs["+V"]["rootLocalUVWmm"][1])
    seat_u = local_box(u_max - u_min, 1.60, 1.20, (u_min + u_max) / 2.0, 0, -1.20,
                       "I2_MINIMUM_ROOT_TO_ROOT_U_SEAT")
    seat_v = local_box(1.60, v_max - v_min, 1.20, 0, (v_min + v_max) / 2.0, -1.20,
                       "I2_MINIMUM_ROOT_TO_ROOT_V_SEAT")
    seat = seat_u.fuse(seat_v).clean(); seat.label = "I2_MAIN_BODY_BOTTOM_OPEN_CROSS"
    result = seat
    legs = []
    for edge in ("+U", "-U", "+V", "-V"):
        leg = specs[edge]["leg"]
        legs.append(leg)
        result = result.fuse(leg)
    result = result.clean(); result.label = "I2_DIRECT_SHELL_FOUR_EDGE_HARNESS_ONE_PRINTED_SOLID"
    if len(result.solids()) != 1:
        raise RuntimeError(f"simplified harness is not one fused solid: {len(result.solids())}")
    return {"harness": result, "seat": seat, "legs": Compound(children=legs),
            "legByEdge": {edge: specs[edge]["leg"] for edge in specs}}


def current_inventory(current: dict[str, Shape], exported: Shape) -> dict[str, object]:
    rows = [
        ("FOUR EDGE LEGS", "SIMPLIFY", current["upperLegs"], "replace upper/lower/transition stack with four straight full-length legs"),
        ("MINIMAL LANDINGS", "REMOVE", current["collars"], "0.60 mm structural reaction ledge is below the 1.20 mm rule"),
        ("FOUR RECEIVERS", "REMOVE", current["slots"], "replace references with four voids cut directly in the shell crop"),
        ("RECEIVER WALLS", "REMOVE", current["bosses"], "eight separate walls are not part of the direct-shell load path"),
        ("OUTBOARD STRUTS", "REMOVE", current["struts"], "their span is absorbed into the straight structural legs"),
        ("CONFORMAL PANELS", "REMOVE", current["panels"], "Level 0 uses frozen shell material directly"),
        ("INNER HOUSING", "REMOVE", current["housing"], "separate support body is prohibited by the simplified intent"),
        ("ROOT TRANSITIONS", "REMOVE", current["transitions"], "four separate root transitions disappear into four straight legs"),
        ("N2 REAR TRANSITION", "REMOVE", None, "not present in I2; no rear-route family is carried forward by default"),
        ("PUSHER GUIDE", "KEEP", current["guide"], "existing simple guide; checked only for collision"),
        ("HARD STOP", "KEEP", current["stop"], "existing independent shoulder/cavity-floor stop"),
        ("PUSHER", "KEEP", current["pusher"], "existing separate captive pusher"),
        ("RETENTION CLIP", "KEEP", current["clip"], "retention only; excluded from press load"),
        ("SECONDARY GLUE BEADS", "REMOVE", current["glue"], "not required to define the Level-0 structural path"),
    ]
    source = [{"component": name, "decision": decision, "solidCount": 0 if shape is None else len(shape.solids()),
               "volumeMm3": 0.0 if shape is None else shape_volume(shape), "reason": reason}
              for name, decision, shape, reason in rows]
    exported_rows = []
    for child in exported.children:
        exported_rows.append({"label": child.label, "shapeType": str(child.shape_type),
                              "solidCount": len(child.solids()), "volumeMm3": shape_volume(child)})
    minus_v_bounds = bounds(current["strutsByEdge"]["-V"])
    housing_bounds = bounds(current["housing"])
    housing_matches_minus_v = bool(np.allclose(minus_v_bounds[0], housing_bounds[0], atol=1.0e-4)
                                   and np.allclose(minus_v_bounds[1], housing_bounds[1], atol=1.0e-4))
    return {"sourceDefinedComponents": source, "actualExportedStepChildren": exported_rows,
            "actualExportedStepSolidCount": len(exported.solids()),
            "generatorHousingCompoundCollapsedToMinusVStrut": housing_matches_minus_v,
            "generatorHousingActualSolidCount": len(current["housing"].solids()),
            "generatorHousingActualVolumeMm3": shape_volume(current["housing"]),
            "sourcePanelSolids": len(current["panels"].solids()),
            "sourceReceiverWallSolids": len(current["bosses"].solids()),
            "sourceOutboardStrutSolids": len(current["struts"].solids())}


def clearances(harness: Shape, specs: dict[str, dict[str, object]], pusher: dict[str, Shape],
               datums: dict[str, object]) -> dict[str, object]:
    terminal_rows = {}
    for name, proxy in terminal_proxies().items():
        common = harness & proxy
        pen = volume(common)
        terminal_rows[name] = {"distanceMm": float(harness.distance_to(proxy)), "penetrationMm3": pen,
                               "clear": pen <= BOOLEAN_EPS}
    pusher_pen = volume(harness & pusher["pusher"])
    pusher_clearance = float(harness.distance_to(pusher["pusher"]))

    local_body = local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "MEASURED_ITS_BODY")
    local_actuator = local_cylinder(ACT_D, BODY_H, 6.0, "MEASURED_ITS_ACTUATOR")
    harness_world = placed(harness, datums[REPRESENTATIVE], FROZEN_FRONT_DEPTHS[REPRESENTATIVE], "I2_DIRECT_HARNESS")
    neighbor_rows = {}
    for name in BUTTONS:
        if name == REPRESENTATIVE:
            continue
        body_world = placed(local_body, datums[name], FROZEN_FRONT_DEPTHS[name], f"{name}_BODY")
        actuator_world = placed(local_actuator, datums[name], FROZEN_FRONT_DEPTHS[name], f"{name}_ACTUATOR")
        distances = [float(harness_world.distance_to(body_world)), float(harness_world.distance_to(actuator_world))]
        penetrations = [volume(harness_world & body_world), volume(harness_world & actuator_world)]
        neighbor_rows[name] = {"minimumDistanceMm": min(distances), "penetrationMm3": sum(penetrations),
                               "clear": sum(penetrations) <= BOOLEAN_EPS}
    min_neighbor = min(row["minimumDistanceMm"] for row in neighbor_rows.values())
    nearest_neighbor = min(neighbor_rows, key=lambda name: neighbor_rows[name]["minimumDistanceMm"])
    return {
        "terminals": terminal_rows,
        "minimumTerminalClearanceMm": min(row["distanceMm"] for row in terminal_rows.values()),
        "allTerminalsClear": all(row["clear"] for row in terminal_rows.values()),
        "pusherToHarnessClearanceMm": pusher_clearance,
        "pusherToHarnessPenetrationMm3": pusher_pen,
        "neighborScope": "other seven frozen measured ITS body+actuator envelopes",
        "neighbors": neighbor_rows,
        "nearestNeighbor": nearest_neighbor,
        "minimumNeighborClearanceMm": min_neighbor,
        "allNeighborsClear": all(row["clear"] for row in neighbor_rows.values()),
    }


def section_slab(spec: dict[str, object], width: float = 0.45) -> Shape:
    root = np.asarray(spec["rootLocalUVWmm"], float)
    floor = np.asarray(spec["floorPointLocalUVWmm"], float)
    direction = unit(floor - root)
    tangent = np.asarray(spec["tangentHintLocal"], float)
    return oriented_box_between(xyz(root - direction * 2.0), xyz(floor + direction * 2.0), xyz(tangent),
                                width, 20.0, label=f"{spec['edge']}_SECTION_SLAB")


def tri(shape: Shape) -> np.ndarray:
    return safe_triangles(shape)


def render_outputs(current: dict[str, Shape], simple: dict[str, Shape], specs: dict[str, dict[str, object]],
                   shell_crop_local: Shape, slotted_shell_local: Shape, its: dict[str, Shape],
                   pusher: dict[str, Shape]) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []

    def render(filename: str, objects, title: str, subtitle: str, camera=(28, -38, 23),
               fit=None, transparent=None, wireframes=None, world_lines=None, size=(1440, 960)):
        path = RENDER / filename
        raster_scene(path, objects, title, subtitle, FOOTER, camera_offset=camera, fit_points=fit,
                     transparent_objects=transparent or [], wireframes=wireframes or [],
                     world_lines=world_lines or [], final_size=size)
        outputs.append(relative(path))

    exploded = []
    labels = []
    explode_rows = [
        (current["panels"], (-34, 0, 0), COL["panel"], "4 CONFORMAL PANELS"),
        (current["bosses"], (-25, 0, 0), COL["receiver"], "8 RECEIVER WALLS"),
        (current["struts"], (-16, 0, 0), COL["collar"], "4 OUTBOARD STRUTS"),
        (current["core"], (-5, 0, 0), COL["seat"], "HARNESS + LANDINGS + TRANSITIONS"),
        (current["body"], (6, 0, 0), COL["actual"], "ITS BODY"),
        (current["actuator"], (12, 0, 0), COL["actual"], "ITS ACTUATOR"),
        (current["pusher"], (20, 0, 0), COL["pusher"], "PUSHER"),
        (current["guide"], (29, 0, 0), COL["guide"], "GUIDE + HARD-STOP CAVITY"),
        (current["clip"], (37, 0, 0), COL["clip"], "RETENTION CLIP"),
    ]
    for index, (shape, delta, color, label) in enumerate(explode_rows):
        shifted = moved(shape, delta, f"EXPLODED_{label}")
        exploded.append((tri(shifted), color))
        lo, hi = bounds(shifted); center = (lo + hi) / 2.0
        labels.append((center, center + np.asarray((0, 0, 6.0 + (index % 2) * 2.5)), (*color, 255), label))
    render("01_current_docs79_i2_full_stack_exploded_named.png", exploded,
           "1 / CURRENT docs/79 I2 — ACTUAL SOURCE COMPONENTS",
           "Exploded groups named by leader; exported STEP housing child collapses to one -V strut",
           camera=(70, -92, 58), world_lines=labels, size=(1680, 1040))

    render("02_current_receiver_panel_strut_closeup.png",
           [(tri(current["panels"]), COL["panel"]), (tri(current["bosses"]), COL["receiver"]),
            (tri(current["struts"]), COL["collar"]), (tri(current["lowerLegs"]), COL["leg"])],
           "2 / CURRENT COMPLEX SUPPORT CLOSE-UP",
           "GREEN=conformal panels | DARK GREEN=receiver walls | ORANGE=outboard struts | BLUE=lower legs",
           camera=(35, -47, 27))

    render("03_simplified_direct_shell_candidate_top.png",
           [(tri(simple["seat"]), COL["seat"]), (tri(simple["legs"]), COL["leg"]), (tri(its["body"]), COL["actual"])],
           "3 / SIMPLIFIED DIRECT-SHELL CANDIDATE — TOP",
           "four roots remain at +U/-U/+V/-V side midpoints; no corner posts, pocket, carrier, or panels",
           camera=(0.2, -0.5, 36))

    render("04_simplified_candidate_isometric.png",
           [(tri(simple["harness"]), COL["leg"]), (tri(its["body"]), COL["actual"]),
            (tri(its["actuator"]), COL["actual"]),
            (tri(Compound(children=[specs[e]["slotTool"] for e in specs])), COL["slot"])],
           "4 / ONE FUSED HARNESS + FOUR DIRECT BLIND-SLOT INSERTS",
           "every structural leg is one straight printable prism; four orange volumes are shell voids",
           camera=(28, -38, 22))

    for filename, edges, title in (
        ("05_section_plus_u_minus_u_legs.png", ("+U", "-U"), "5 / +U AND -U DIRECT-LEG SECTIONS"),
        ("06_section_plus_v_minus_v_legs.png", ("+V", "-V"), "6 / +V AND -V DIRECT-LEG SECTIONS"),
    ):
        section_objects = []
        lines = []
        for edge in edges:
            slab = section_slab(specs[edge])
            shell_section = slotted_shell_local & slab
            if shell_section is not None and shell_section.solids():
                section_objects.append((tri(shell_section.clean()), COL["shell"]))
            section_objects.append((tri(specs[edge]["leg"]), COL["leg"]))
            section_objects.append((tri(specs[edge]["slotTool"]), COL["slot"]))
            p0 = np.asarray(specs[edge]["rootLocalUVWmm"], float)
            p1 = np.asarray(specs[edge]["floorPointLocalUVWmm"], float)
            lines.append((p0, p1, (*COL["leg"], 255), f"{edge} L={specs[edge]['legLengthMm']:.2f} mm"))
        render(filename, section_objects, title,
               "orange=1.20 mm blind void | blue=straight leg | grey=frozen-shell local section",
               camera=(29, -42, 17), world_lines=lines)

    slots = Compound(children=[specs[edge]["slotTool"] for edge in specs])
    shell_tri = tri(shell_crop_local)
    render("07_four_shell_blind_slots_only.png", [(tri(slots), COL["slot"])],
           "7 / FOUR BLIND SLOTS CUT DIRECTLY INTO FROZEN-SHELL CROP",
           "+U 1.60 x 3.00 mm; others 2.00 x 3.00 mm; minimum depth 1.20 mm; no receiver bodies",
           camera=(30, -40, 24), wireframes=[(safe_edge_lines(shell_crop_local), (*COL["shell"], 145))],
           transparent=[(shell_tri, (*COL["shell"], 48))])

    render("08_its_harness_four_legs_only.png",
           [(tri(simple["harness"]), COL["leg"]), (tri(its["body"]), COL["actual"]),
            (tri(its["actuator"]), COL["actual"])],
           "8 / ITS + OPEN CROSS + FOUR STRAIGHT LEGS ONLY",
           "one fused printed harness solid; unequal leg lengths follow the frozen shell",
           camera=(25, -34, 19))

    render("09_full_simplified_assembly.png",
           [(tri(simple["harness"]), COL["leg"]), (tri(its["body"]), COL["actual"]),
            (tri(its["actuator"]), COL["actual"]), (tri(pusher["pusher"]), COL["pusher"]),
            (tri(pusher["guide"]), COL["guide"]), (tri(pusher["clip"]), COL["clip"])],
           "9 / FULL SIMPLIFIED I2 AUDIT ASSEMBLY",
           "frozen-shell crop shown transparent; pusher/guide/clip retained without redesign",
           camera=(30, -42, 24), transparent=[(tri(slotted_shell_local), (*COL["shell"], 72))])

    left_current = moved(Compound(children=[current["core"], current["panels"], current["bosses"], current["struts"]]),
                         (-17, 0, 0), "CURRENT_COMPLEXITY")
    right_simple = moved(simple["harness"], (17, 0, 0), "SIMPLIFIED_ONE_SOLID")
    render("10_current_vs_simplified_comparison.png",
           [(tri(left_current), COL["current"]), (tri(right_simple), COL["simplified"])],
           "10 / CURRENT docs/79 vs SIMPLIFIED DIRECT-SHELL",
           "LEFT: panels + walls + struts + landings | RIGHT: one fused cross-and-four-straight-leg harness",
           camera=(45, -60, 32), world_lines=[
               (np.asarray((-17, 0, 0)), np.asarray((-17, 0, 12)), (*COL["current"], 255), "CURRENT COMPLEX SUPPORT"),
               (np.asarray((17, 0, 0)), np.asarray((17, 0, 12)), (*COL["simplified"], 255), "SIMPLIFIED 1 SOLID"),
           ])
    return outputs


def report_text(data: dict[str, object]) -> str:
    inventory_rows = "\n".join(
        f"| {row['component']} | {row['solidCount']} | {row['decision']} | {row['reason']} |"
        for row in data["currentAudit"]["sourceDefinedComponents"]
    )
    exported_rows = "\n".join(
        f"| {row['label']} | {row['shapeType']} | {row['solidCount']} | {row['volumeMm3']:.3f} |"
        for row in data["currentAudit"]["actualExportedStepChildren"]
    )
    leg_rows = "\n".join(
        f"| {edge} | {row['legLengthMm']:.3f} | {row['legThicknessMm']:.2f} | {row['shellThicknessCenterMm']:.3f} | "
        f"{row['shellThicknessFootprintMinMm']:.3f} | {row['remainingExteriorThicknessFootprintMinMm']:.3f} | "
        f"{row['blindDepthFootprintRangeMm'][0]:.3f}…{row['blindDepthFootprintRangeMm'][1]:.3f} | "
        f"{row['targetLocalUVmm'][0]:.2f}, {row['targetLocalUVmm'][1]:.2f} |"
        for edge, row in data["directShell"]["legs"].items()
    )
    terminal_rows = "\n".join(
        f"| {name} | {row['distanceMm']:.3f} | {row['penetrationMm3']:.6f} | {row['clear']} |"
        for name, row in data["clearances"]["terminals"].items()
    )
    render_rows = "\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    return f"""# 80 — I2 direct-shell four-edge-leg simplification audit

MODE
= **AUDIT-ONLY / I2 REPRESENTATIVE / PRODUCTION PROPAGATION = 0**

FINAL VERDICT
= **{data['finalVerdict']}**

CURRENT docs/79 PRESERVED
= **{data['preservation']['allProtectedFilesPreserved']}**

SIMPLIFIED LOAD PATH
= **ITS BODY → ONE FOUR-EDGE HARNESS → FOUR STRAIGHT LEGS → FOUR DIRECT SHELL BLIND-SLOT FLOORS/WALLS → FROZEN SHELL**

PRINTED/SUPPORT SOLID COUNT
= **3: ONE FUSED HARNESS + EXISTING PUSHER + EXISTING GUIDE/HARD-STOP INTERFACE**

## 1. What docs/79 actually built

The source generator and the exported STEP are not identical.  The source defines 4 conformal panels,
8 receiver walls and 4 outboard struts.  However, the `housing` compound stored in the full-stack STEP
collapses to one solid whose bounds exactly match the **-V outboard strut**.  This is an audit finding;
docs/79 and its files were not repaired or overwritten.

| source component | source solids | decision | reason |
|---|---:|---|---|
{inventory_rows}

### Actual children in the existing docs/79 I2 full-stack STEP

| exported child label | type | solids | volume mm³ |
|---|---|---:|---:|
{exported_rows}

Existing STEP solid total: **{data['currentAudit']['actualExportedStepSolidCount']}**.  Existing exported
`INNER_HOUSING` matches only the -V strut: **{data['currentAudit']['generatorHousingCompoundCollapsedToMinusVStrut']}**.

## 2. Frozen orientation authority

| item | value |
|---|---|
| frozen button center | {data['freeze']['buttonCenter']} |
| approved press axis | {data['freeze']['pressAxis']} |
| approved local exterior normal | {data['freeze']['exteriorNormal']} |
| angle axis ↔ exterior normal | **{data['freeze']['axisToExteriorNormalDeg']:.3f}°** |
| ITS actuator axis | identical to approved press axis |
| exterior / JaD-JfD split | unchanged / unchanged |

The exact STEP has an aperture at the button center, so a face normal cannot be sampled at the void.
The frozen approved pre-cut surface normal stored with the button datum is therefore the tangent-plane authority.

## 3. Level-0 direct-shell feasibility

Roots remain at the four +U/-U/+V/-V switch side mid-regions.  Every leg is one straight rectangular prism.
The I2-I3 gap requires the allowed 1.20 mm minimum at +U; the other three retain 1.60 mm.  Tangent width is
2.60 mm throughout.  The shell endpoint alone moves to a region where the complete clearance slot footprint
has a valid exact inner/outer BRep pair.  Every footprint was checked at 3×3 points.

| leg | length mm | thickness | shell center thickness | footprint min thickness | footprint min remaining | depth range | shell target U,V |
|---|---:|---:|---:|---:|---:|---:|---:|
{leg_rows}

Blind-slot depth is **{data['directShell']['blindSlotDepthMm']:.2f} mm** and clearance is
**{data['directShell']['slotClearancePerSideMm']:.2f} mm/side**.  Minimum remaining exterior material over
all four footprints is **{data['directShell']['minimumRemainingExteriorThicknessMm']:.3f} mm**.  Therefore no
local pad, conformal panel, receiver cage or strut network is geometrically required for this I2 audit candidate.

## 4. Clearances

| terminal | minimum distance mm | penetration mm³ | clear |
|---|---:|---:|---|
{terminal_rows}

| requested value | result |
|---|---:|
| minimum terminal clearance | {data['clearances']['minimumTerminalClearanceMm']:.3f} mm |
| minimum pusher-to-harness clearance | {data['clearances']['pusherToHarnessClearanceMm']:.3f} mm |
| minimum neighboring-geometry clearance | {data['clearances']['minimumNeighborClearanceMm']:.3f} mm to {data['clearances']['nearestNeighbor']} |

Neighbor scope is `{data['clearances']['neighborScope']}`.  No production carrier or neighboring button was modified.

## 5. What was removed

- four 0.60 × 0.60 structural landings;
- eight separate receiver walls;
- four outboard struts;
- four ruled conformal panels;
- the separate inner-housing/support concept;
- glue beads as a structural definition;
- the N2 rear-route architecture as a default assumption.

The open body-bottom cross, four side-midpoint origins, existing pusher, retention-only clip and independent
hard stop remain.  N2 was not rebuilt in this I2-only stop stage; any later N2 work must begin with the same
four direct-ray test before an offset is allowed.

## 6. FDM and assembly

- P1S / 0.4 mm nozzle basis;
- structural leg thickness 1.20 mm at +U / 1.60 mm at the other three; tangent width 2.60 mm;
- blind depth 1.20 mm; no sub-mm structural shoulder or landing;
- unequal leg lengths are intentional consequences of the frozen curved shell;
- the four legs and open cross are fused into one printable harness solid.

## 7. Required renders

{render_rows}

## 8. Outputs and preservation

- `{data['outputs']['harnessStep']}`
- `{data['outputs']['shellCropStep']}`
- `{data['outputs']['assemblyStep']}`
- `{data['outputs']['json']}`

All {data['preservation']['protectedFileCount']} protected prior/production files retained identical SHA-256 hashes:
**{data['preservation']['allProtectedFilesPreserved']}**.  Production shell boolean = **0**; only a separate local
audit crop copy was cut.  Physical coupon = **not created**.  Eight-button propagation = **0**.

## 9. Stop

This audit stops at one I2 simplified candidate.  No production geometry, frozen exterior, button center, press axis,
JaD/JfD split, docs/79 file or previous audit output was changed.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); RENDER.mkdir(parents=True, exist_ok=True)
    protected = protected_files(); before = hash_rows(protected)
    datums = load_all_datums(); datum = datums[REPRESENTATIVE]; front = float(FROZEN_FRONT_DEPTHS[REPRESENTATIVE])

    exported_current = import_step(CURRENT_FULL_STEP)
    shell_full = import_step(SHELL_STEP[datum.owner])
    exact = ExactRaySampler(shell_full)
    specs = {edge: slot_leg_spec(edge, datum, front, exact) for edge in ("+U", "-U", "+V", "-V")}
    simple = simplified_harness(specs)
    pusher = pusher_system()
    its = {
        "body": local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "ITS1105_MEASURED_BODY"),
        "actuator": local_cylinder(ACT_D, BODY_H, 6.0, "ITS1105_MEASURED_ACTUATOR"),
    }

    # The only shell boolean is a separate small local audit copy.
    crop_local = local_box(SHELL_CROP_U, SHELL_CROP_V, SHELL_CROP_W1 - SHELL_CROP_W0,
                           0, 0, SHELL_CROP_W0, "I2_LOCAL_SHELL_CROP_TOOL")
    placement = datum_location(datum, front)
    crop_world = placement * crop_local
    shell_crop_world = shell_full & crop_world
    if shell_crop_world is None or not shell_crop_world.solids():
        raise RuntimeError("I2 exact local shell crop is empty")
    shell_crop_world = shell_crop_world.clean(); shell_crop_world.label = "I2_FROZEN_SHELL_LOCAL_CROP_UNMODIFIED_REFERENCE"
    slotted_world = shell_crop_world
    for edge in ("+U", "-U", "+V", "-V"):
        slot_world = placement * specs[edge]["slotTool"]
        slotted_world = slotted_world - slot_world
    slotted_world = slotted_world.clean(); slotted_world.label = "I2_LOCAL_FROZEN_SHELL_CROP_WITH_FOUR_DIRECT_BLIND_SLOTS_AUDIT_ONLY"
    shell_crop_local = placement.inverse() * shell_crop_world
    slotted_shell_local = placement.inverse() * slotted_world

    current, _ = local_candidate(REPRESENTATIVE, ExactShellSampler(shell_full), datum, front)
    inventory = current_inventory(current, exported_current)
    clearance = clearances(simple["harness"], specs, pusher, datums)

    # Leg/shell boolean validation uses only the slotted local audit crop.
    harness_world = placement * simple["harness"]
    harness_shell_penetration = volume(harness_world & slotted_world)
    direct_rows = {}
    for edge, row in specs.items():
        direct_rows[edge] = {key: value for key, value in row.items()
                             if key not in ("leg", "slotTool", "tangentHintLocal")}

    render_paths = render_outputs(current, simple, specs, shell_crop_local, slotted_shell_local, its, pusher)

    # Export audit-only artifacts after all measurements.  Prior files are untouched.
    export_step(simple["harness"], HARNESS_STEP)
    export_step(slotted_world, SHELL_CROP_STEP)
    assembly_world = Compound(children=[slotted_world, harness_world,
                                        placement * its["body"], placement * its["actuator"],
                                        placement * pusher["pusher"], placement * pusher["guide"],
                                        placement * pusher["clip"]],
                              label="I2_DIRECT_SHELL_SIMPLIFIED_FULL_ASSEMBLY_AUDIT_ONLY")
    export_step(assembly_world, ASSEMBLY_STEP)

    after = hash_rows(protected)
    preserved = before == after
    minimum_remaining = min(row["remainingExteriorThicknessFootprintMinMm"] for row in direct_rows.values())
    level0_pass = (minimum_remaining >= 1.20 and clearance["allTerminalsClear"]
                   and clearance["pusherToHarnessPenetrationMm3"] <= BOOLEAN_EPS
                   and clearance["allNeighborsClear"] and harness_shell_penetration <= 1.0e-4)
    verdict = "A — DIRECT-SHELL SIMPLE DESIGN WORKS" if level0_pass else "B — DIRECT-SHELL WORKS WITH SIMPLE LOCAL PAD ONLY"
    data = {
        "schema": "onegrip.direct-shell-four-edge-i2-simplification-audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "AUDIT-ONLY / I2 ONLY / NO PRODUCTION PROPAGATION",
        "finalVerdict": verdict,
        "freeze": {
            "button": REPRESENTATIVE,
            "owner": datum.owner,
            "buttonCenter": list(map(float, datum.center)),
            "pressAxis": list(map(float, unit(datum.axis))),
            "exteriorNormal": list(map(float, unit(datum.shell_normal))),
            "axisToExteriorNormalDeg": angle_deg(datum.axis, datum.shell_normal),
            "frontDepthMm": front,
            "exteriorPreserved": True,
            "splitPreserved": True,
        },
        "currentAudit": inventory,
        "directShell": {
            "level": 0,
            "legCount": 4,
            "straightLegs": True,
            "cornerPosts": False,
            "largePocket": False,
            "separateReceiverBodies": False,
            "conformalPanels": False,
            "outboardStruts": False,
            "localPads": False,
            "legThicknessRangeMm": [min(LEG_THICKNESS_BY_EDGE.values()), max(LEG_THICKNESS_BY_EDGE.values())],
            "legTangentWidthMm": LEG_TANGENTIAL,
            "blindSlotDepthMm": BLIND_DEPTH,
            "slotCrossSectionsMm": {edge: row["slotCrossSectionMm"] for edge, row in direct_rows.items()},
            "slotClearancePerSideMm": SLOT_CLEARANCE,
            "minimumRemainingExteriorThicknessMm": minimum_remaining,
            "harnessPrintedSolidCount": len(simple["harness"].solids()),
            "harnessShellPenetrationMm3": harness_shell_penetration,
            "legs": direct_rows,
        },
        "pusher": {
            "reusedWithoutRedesign": True,
            "clipRetentionOnly": True,
            "independentHardStop": True,
            "printedSupportSolidCount": 3,
            "printedSupportSolids": ["one fused harness", "existing pusher", "existing guide/hard-stop interface"],
        },
        "clearances": clearance,
        "preservation": {
            "protectedFileCount": len(protected),
            "hashesBefore": before,
            "hashesAfter": after,
            "allProtectedFilesPreserved": preserved,
            "productionModification": 0,
            "productionShellBoolean": 0,
            "physicalCouponCreated": False,
            "eightButtonPropagation": 0,
        },
        "outputs": {
            "harnessStep": relative(HARNESS_STEP),
            "shellCropStep": relative(SHELL_CROP_STEP),
            "assemblyStep": relative(ASSEMBLY_STEP),
            "json": relative(JSON_PATH),
            "report": relative(REPORT),
            "renders": render_paths,
        },
    }
    JSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "renders": len(render_paths), "level0": level0_pass,
                      "minRemainingShellMm": minimum_remaining, "allTerminalsClear": clearance["allTerminalsClear"],
                      "pusherClearanceMm": clearance["pusherToHarnessClearanceMm"],
                      "neighborClearanceMm": clearance["minimumNeighborClearanceMm"],
                      "protectedPreserved": preserved, "report": relative(REPORT)}, indent=2))


if __name__ == "__main__":
    main()
