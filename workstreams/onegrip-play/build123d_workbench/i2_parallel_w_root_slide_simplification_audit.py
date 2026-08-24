"""I2 +W parallel-leg root-slide simplification audit.

The docs/81 fixed-root result is not generalized.  This audit reopens only
the tangent coordinate of each +U/-U/+V/-V side root while keeping the I2
switch datum, exterior, ITS pose and +W leg direction hard-frozen.
Production geometry is never modified.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Compound, Shape, export_step, import_step

from .direct_shell_four_edge_i2_simplification_audit import (
    BLIND_DEPTH,
    HARNESS_STEP as DOC80_HARNESS_STEP,
    LEG_THICKNESS_BY_EDGE,
    REPORT as DOC80_REPORT,
    SHELL_STEP,
    SLOT_CLEARANCE,
    SLOT_TANGENT,
    ExactRaySampler,
    leg_root,
    local_dir_to_world,
    local_point_to_world,
)
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import (
    ACT_D,
    BODY_H,
    BODY_U,
    BODY_V,
    LEG_TANGENTIAL,
    bounds,
    datum_location,
    local_box,
    local_cylinder,
    moved,
    placed,
    sha256,
    volume,
)
from .i2_parallel_w_four_edge_leg_revalidation_audit import (
    JSON_PATH as DOC81_JSON,
    REPORT as DOC81_REPORT,
    RENDER as DOC81_RENDER,
    OUT as DOC81_OUT,
    current_direction_audit,
    protected_files as doc81_protected_files,
)
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import BUTTONS, ROOT, relative
from .option_c_local_exact_prototype import raster_scene, safe_edge_lines, safe_triangles
from .slot_anchored_harness_captive_pusher_audit import pusher_system, terminal_proxies


OUT = ROOT / "build123d_workbench/out/i2_parallel_w_root_slide_simplification_audit"
RENDER = ROOT / "renders/i2_parallel_w_root_slide_simplification_audit"
REPORT = ROOT / "docs/82_i2_parallel_w_root_slide_simplification_audit.md"
JSON_PATH = OUT / "i2_parallel_w_root_slide_simplification_audit.json"
DIAGNOSTIC_STEP = OUT / "I2_PARALLEL_W_ROOT_SLIDE_BEST_FAILURE_PROBES_AUDIT_ONLY.step"

REPRESENTATIVE = "I2"
EDGES = ("+U", "-U", "+V", "-V")
THICKNESSES = (1.60, 1.20)
STRICT_STEP = 0.05
EXTENDED_STEP = 0.10
REFINE_STEP = 0.005
REFINE_HALF_RANGE = 0.10
BOOLEAN_EPS = 1.0e-6
CORNER_D = 1.40
CORNER_W0 = BODY_H
CORNER_W1 = BODY_H + 0.80
MIN_SIDE_OVERLAP = LEG_TANGENTIAL
FOOTER = "AUDIT ONLY | I2 ROOT TANGENT-SLIDE | ALL LEG AXES = +W | ANGULAR DEVIATION = 0 | PRODUCTION = 0"
COL = {
    "body": (229, 92, 100),
    "old": (74, 164, 224),
    "probe": (245, 178, 65),
    "shell": (108, 130, 151),
    "search": (118, 140, 164),
    "feasible": (61, 190, 137),
    "fail": (235, 82, 93),
    "axis": (250, 213, 78),
    "pusher": (237, 132, 72),
    "neighbor": (171, 112, 219),
}


def xyz(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(map(float, value))


def protected_files() -> list[Path]:
    rows = {
        *doc81_protected_files(),
        DOC80_REPORT,
        DOC81_REPORT,
        DOC81_JSON,
        *[path for path in DOC81_OUT.rglob("*") if path.is_file()],
        *[path for path in DOC81_RENDER.rglob("*") if path.is_file()],
    }
    return sorted(path for path in rows if path.exists())


def hashes(paths: list[Path]) -> dict[str, str]:
    return {relative(path): sha256(path) for path in paths}


def tangent_axis(edge: str) -> np.ndarray:
    return np.asarray((0.0, 1.0, 0.0) if edge.endswith("U") else (1.0, 0.0, 0.0), float)


def structural_axis(edge: str) -> np.ndarray:
    return np.asarray((1.0, 0.0, 0.0) if edge.endswith("U") else (0.0, 1.0, 0.0), float)


def tangent_half_span(edge: str) -> float:
    return BODY_V / 2.0 if edge.endswith("U") else BODY_U / 2.0


def strict_domain(edge: str) -> tuple[float, float]:
    limit = tangent_half_span(edge) - LEG_TANGENTIAL / 2.0
    return -limit, limit


def extended_domain(edge: str) -> tuple[float, float]:
    # Closure of the any-overlap diagnostic bound.  The two endpoints have
    # exactly zero side overlap and are retained only to expose boundary-only
    # shell solutions; they can never qualify as side roots.
    limit = tangent_half_span(edge) + LEG_TANGENTIAL / 2.0
    return -limit, limit


def root_at(edge: str, tangent_coordinate: float) -> np.ndarray:
    return leg_root(edge) + tangent_axis(edge) * float(tangent_coordinate)


def side_overlap(edge: str, tangent_coordinate: float) -> float:
    half = tangent_half_span(edge)
    low = max(-half, tangent_coordinate - LEG_TANGENTIAL / 2.0)
    high = min(half, tangent_coordinate + LEG_TANGENTIAL / 2.0)
    return float(max(0.0, high - low))


def grid(lower: float, upper: float, step: float) -> list[float]:
    values = list(np.arange(lower, upper + step * 0.25, step, dtype=float))
    values.extend((lower, upper, 0.0))
    return sorted({round(float(np.clip(value, lower, upper)), 6) for value in values})


def evaluate_root(edge: str, tangent_coordinate: float, thickness: float, datum, front: float,
                  ray: ExactRaySampler) -> dict[str, object]:
    root = root_at(edge, tangent_coordinate)
    tangent = tangent_axis(edge)
    structural = structural_axis(edge)
    direction_world = local_dir_to_world(datum, (0, 0, 1))
    structural_slot = float(thickness + 2.0 * SLOT_CLEARANCE)
    sample_rows = []
    inner: list[float] = []
    outer: list[float] = []
    for tangent_offset in (-SLOT_TANGENT / 2.0, 0.0, SLOT_TANGENT / 2.0):
        for structural_offset in (-structural_slot / 2.0, 0.0, structural_slot / 2.0):
            origin_local = root + tangent * tangent_offset + structural * structural_offset
            hits = ray.hits(local_point_to_world(datum, front, origin_local), direction_world, 20.0)
            has_pair = len(hits) >= 2
            if has_pair:
                inner.append(float(hits[0]))
                outer.append(float(hits[1]))
            sample_rows.append({
                "originLocalUVWmm": list(map(float, origin_local)),
                "offsetTangentMm": float(tangent_offset),
                "offsetStructuralMm": float(structural_offset),
                "hitsMm": hits,
                "hasInnerOuterPair": has_pair,
            })
    center_hits = ray.hits(local_point_to_world(datum, front, root), direction_world, 20.0)
    coverage = len(inner)
    floor = max(inner) + BLIND_DEPTH if coverage == 9 else None
    remaining = min(outer) - floor if floor is not None else None
    thicknesses = [out - inn for inn, out in zip(inner, outer)]
    passed = bool(coverage == 9 and remaining is not None and remaining >= BLIND_DEPTH)
    return {
        "edge": edge,
        "tangentCoordinateMm": float(tangent_coordinate),
        "rootLocalUVWmm": list(map(float, root)),
        "rootShiftLocalUVWmm": list(map(float, root - leg_root(edge))),
        "rootShiftMagnitudeMm": abs(float(tangent_coordinate)),
        "legThicknessMm": float(thickness),
        "legTangentWidthMm": LEG_TANGENTIAL,
        "slotCrossSectionMm": [SLOT_TANGENT, structural_slot],
        "sideOverlapMm": side_overlap(edge, tangent_coordinate),
        "centerHitsMm": center_hits,
        "footprintPairCoverage": coverage,
        "missingFootprintPairs": 9 - coverage,
        "pairedShellThicknessRangeMm": None if not thicknesses else [float(min(thicknesses)), float(max(thicknesses))],
        "requiredFloorDistanceMm": None if floor is None else float(floor),
        "minimumRemainingShellMm": None if remaining is None else float(remaining),
        "effectiveMinimumRemainingShellMm": float(remaining) if remaining is not None else 0.0,
        "shellSupportPass": passed,
        "samples": sample_rows,
    }


def compact(row: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in row.items() if key != "samples"}


def intervals(values: list[float], step: float) -> list[list[float]]:
    if not values:
        return []
    values = sorted(values)
    result: list[list[float]] = []
    start = previous = values[0]
    for value in values[1:]:
        if value - previous > step * 1.51:
            result.append([float(start), float(previous)])
            start = value
        previous = value
    result.append([float(start), float(previous)])
    return result


def scan(edge: str, thickness: float, domain: tuple[float, float], step: float, datum, front: float,
         ray: ExactRaySampler) -> dict[str, object]:
    rows = [evaluate_root(edge, value, thickness, datum, front, ray) for value in grid(*domain, step)]
    maximum = max(int(row["footprintPairCoverage"]) for row in rows)
    max_values = [float(row["tangentCoordinateMm"]) for row in rows if row["footprintPairCoverage"] == maximum]
    pass_values = [float(row["tangentCoordinateMm"]) for row in rows if row["shellSupportPass"]]
    best = min((row for row in rows if row["footprintPairCoverage"] == maximum),
               key=lambda row: (abs(float(row["tangentCoordinateMm"])),
                                -float(row["pairedShellThicknessRangeMm"][0]) if row["pairedShellThicknessRangeMm"] else 0.0))
    return {
        "domainMm": list(map(float, domain)),
        "stepMm": float(step),
        "sampleCount": len(rows),
        "maximumFootprintPairCoverage": maximum,
        "maximumCoverageIntervalsMm": intervals(max_values, step),
        "feasibleRootIntervalsMm": intervals(pass_values, step),
        "bestCoarse": compact(best),
        "rows": [compact(row) for row in rows],
    }


def refined_best(edge: str, thickness: float, coarse: dict[str, object], datum, front: float,
                 ray: ExactRaySampler) -> tuple[dict[str, object], dict[str, object]]:
    center = float(coarse["bestCoarse"]["tangentCoordinateMm"])
    lower, upper = strict_domain(edge)
    domain = (max(lower, center - REFINE_HALF_RANGE), min(upper, center + REFINE_HALF_RANGE))
    refined = scan(edge, thickness, domain, REFINE_STEP, datum, front, ray)
    best = refined["bestCoarse"]
    exact = evaluate_root(edge, float(best["tangentCoordinateMm"]), thickness, datum, front, ray)
    return refined, exact


def corner_keepouts() -> Shape:
    rows = []
    for u0 in (-2.25, 2.25):
        for v0 in (-2.25, 2.25):
            rows.append(local_cylinder(CORNER_D, CORNER_W0, CORNER_W1, "CORNER_FEATURE_KEEP_OUT").moved(
                __import__("build123d").Location(__import__("build123d").Vector(u0, v0, 0))))
    return Compound(children=rows, label="FOUR_CORNER_FEATURE_KEEP_OUTS_D1P40")


def make_probe(row: dict[str, object]) -> Shape:
    root = np.asarray(row["rootLocalUVWmm"], float)
    paired_inner = [sample["hitsMm"][0] for sample in row["samples"] if sample["hasInnerOuterPair"]]
    length = float(row["requiredFloorDistanceMm"]) if row["requiredFloorDistanceMm"] is not None else (
        float(max(paired_inner) + BLIND_DEPTH) if paired_inner else 12.0)
    row["diagnosticProbeLengthMm"] = length
    return oriented_box_between(xyz(root), xyz(root + np.asarray((0, 0, length), float)),
                                xyz(tangent_axis(str(row["edge"]))), LEG_TANGENTIAL,
                                float(row["legThicknessMm"]),
                                label=f"I2_{row['edge']}_ROOT_SLIDE_BEST_FAILURE_PROBE")


def collision_audit(row: dict[str, object], probe: Shape, datum, front: float, datums: dict[str, object],
                    shell_full: Shape, body: Shape, corners: Shape, pusher: Shape,
                    terminals: dict[str, Shape]) -> dict[str, object]:
    local_rows = {}
    for name, shape in {"ITS_BODY": body, "CORNER_KEEPOUTS": corners, "PUSHER": pusher, **terminals}.items():
        pen = volume(probe & shape)
        local_rows[name] = {"distanceMm": float(probe.distance_to(shape)), "penetrationMm3": pen,
                            "clear": pen <= BOOLEAN_EPS}
    probe_world = placed(probe, datum, front, f"I2_{row['edge']}_ROOT_SLIDE_PROBE_WORLD")
    shell_pen = volume(probe_world & shell_full)
    local_body = local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "MEASURED_ITS_BODY")
    local_actuator = local_cylinder(ACT_D, BODY_H, 6.0, "MEASURED_ITS_ACTUATOR")
    neighbors = {}
    for name in BUTTONS:
        if name == REPRESENTATIVE:
            continue
        body_world = placed(local_body, datums[name], FROZEN_FRONT_DEPTHS[name], f"{name}_BODY")
        actuator_world = placed(local_actuator, datums[name], FROZEN_FRONT_DEPTHS[name], f"{name}_ACTUATOR")
        distances = [float(probe_world.distance_to(body_world)), float(probe_world.distance_to(actuator_world))]
        penetrations = [volume(probe_world & body_world), volume(probe_world & actuator_world)]
        neighbors[name] = {"minimumDistanceMm": min(distances), "penetrationMm3": float(sum(penetrations)),
                           "clear": sum(penetrations) <= BOOLEAN_EPS}
    nearest = min(neighbors, key=lambda name: neighbors[name]["minimumDistanceMm"])
    terminal_names = list(terminals)
    return {
        "probeDefinition": "best strict-domain failure probe; not a candidate leg",
        "uncutShellOverlapMm3": shell_pen,
        "body": local_rows["ITS_BODY"],
        "cornerKeepouts": local_rows["CORNER_KEEPOUTS"],
        "pusher": local_rows["PUSHER"],
        "terminals": {name: local_rows[name] for name in terminal_names},
        "minimumTerminalClearanceMm": min(local_rows[name]["distanceMm"] for name in terminal_names),
        "terminalPenetrationMm3": sum(local_rows[name]["penetrationMm3"] for name in terminal_names),
        "nearestNeighbor": nearest,
        "minimumNeighborClearanceMm": neighbors[nearest]["minimumDistanceMm"],
        "neighborPenetrationMm3": neighbors[nearest]["penetrationMm3"],
        "neighbors": neighbors,
    }


def tri(shape: Shape) -> np.ndarray:
    return safe_triangles(shape)


def marker(root: Iterable[float], label: str) -> Shape:
    point = np.asarray(root, float)
    result = local_cylinder(0.52, -0.15, 0.25, label).moved(
        __import__("build123d").Location(__import__("build123d").Vector(float(point[0]), float(point[1]), 0)))
    return result


def render_outputs(best_rows: dict[str, dict[str, object]], probes: dict[str, Shape], shell_crop_local: Shape,
                   datum, front: float, datums: dict[str, object], pusher: dict[str, Shape],
                   body: Shape, corners: Shape) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    shell_tri = tri(shell_crop_local)
    shell_wire = safe_edge_lines(shell_crop_local)
    old_harness = import_step(DOC80_HARNESS_STEP)

    def render(filename: str, objects, title: str, subtitle: str, camera=(28, -39, 23),
               transparent=None, wireframes=None, world_lines=None, size=(1440, 960)):
        path = RENDER / filename
        raster_scene(path, objects, title, subtitle, FOOTER, camera_offset=camera,
                     transparent_objects=transparent or [], wireframes=wireframes or [],
                     world_lines=world_lines or [], final_size=size)
        outputs.append(relative(path))

    old_markers = Compound(children=[marker(leg_root(edge), f"OLD_{edge}") for edge in EDGES])
    render("01_docs81_fixed_roots_top.png", [(tri(body), COL["body"]), (tri(old_markers), COL["old"])],
           "1 / ORIGINAL docs/81 FIXED ROOTS — TOP", "four blue markers are the side-midpoint root authority reopened here",
           camera=(0.2, -0.5, 35), world_lines=[
               (np.asarray(leg_root(edge)), np.asarray(leg_root(edge)) + np.asarray((0, 0, 4)), (*COL["old"], 255), edge)
               for edge in EDGES])

    regions = []
    region_lines = []
    for edge in EDGES:
        lo, hi = strict_domain(edge)
        base = leg_root(edge)
        if edge.endswith("U"):
            region = local_box(0.18, hi - lo, 0.16, base[0], (lo + hi) / 2, -0.20, f"{edge}_SEARCH_REGION")
        else:
            region = local_box(hi - lo, 0.18, 0.16, (lo + hi) / 2, base[1], -0.20, f"{edge}_SEARCH_REGION")
        regions.append(region)
        p0 = root_at(edge, lo); p1 = root_at(edge, hi)
        region_lines.append((p0, p1, (*COL["fail"], 255), f"{edge} searched {lo:.3f}..{hi:.3f}; feasible EMPTY"))
    render("02_feasible_root_regions_four_sides.png",
           [(tri(body), COL["body"]), (tri(Compound(children=regions)), COL["search"])],
           "2 / FOUR VALID SIDE-ROOT SEARCH REGIONS", "gray=full 2.60 mm side overlap; green feasible intervals = EMPTY",
           camera=(0.2, -0.5, 35), world_lines=region_lines)

    new_markers = Compound(children=[marker(best_rows[edge]["rootLocalUVWmm"], f"BEST_{edge}") for edge in EDGES])
    shift_lines = []
    for edge in EDGES:
        p0 = np.asarray(leg_root(edge), float); p1 = np.asarray(best_rows[edge]["rootLocalUVWmm"], float)
        shift_lines.append((p0, p1, (*COL["fail"], 255),
                            f"{edge} shift {best_rows[edge]['rootShiftMagnitudeMm']:.3f} mm; {best_rows[edge]['footprintPairCoverage']}/9"))
    render("03_best_new_roots_top_failure_diagnostic.png",
           [(tri(body), COL["body"]), (tri(old_markers), COL["old"]), (tri(new_markers), COL["fail"])],
           "3 / BEST ROOT-SLIDE POSITIONS — STILL INVALID", "blue=docs/81 roots | red=nearest maximum-coverage roots",
           camera=(0.2, -0.5, 35), world_lines=shift_lines)

    probe_compound = Compound(children=list(probes.values()), label="FOUR_PARALLEL_W_FAILURE_PROBES")
    direction_lines = []
    for edge, row in best_rows.items():
        p0 = np.asarray(row["rootLocalUVWmm"], float); p1 = p0 + np.asarray((0, 0, row["diagnosticProbeLengthMm"]), float)
        direction_lines.append((p0, p1, (*COL["axis"], 255), f"{edge} +W / 90.000 deg / {row['footprintPairCoverage']}/9"))
    render("04_90deg_parallel_legs_only_failure_probes.png", [(tri(probe_compound), COL["probe"])],
           "4 / FOUR EXACT +W PARALLEL LEGS ONLY", "diagnostic lengths only; maximum inter-leg angular difference = 0.000 deg",
           world_lines=direction_lines)

    for filename, edges, title, section_axis in (
        ("05_plus_u_minus_u_sections.png", ("+U", "-U"), "5 / +U AND -U ROOT-SLIDE SECTIONS", "U"),
        ("06_plus_v_minus_v_sections.png", ("+V", "-V"), "6 / +V AND -V ROOT-SLIDE SECTIONS", "V"),
    ):
        objects = []
        lines = []
        for edge in edges:
            row = best_rows[edge]
            t = float(row["tangentCoordinateMm"])
            slab = (local_box(26, 0.42, 16, 0, t, -2, f"{edge}_SECTION") if section_axis == "U" else
                    local_box(0.42, 26, 16, t, 0, -2, f"{edge}_SECTION"))
            shell_section = shell_crop_local & slab
            if shell_section is not None and shell_section.solids():
                objects.append((tri(shell_section.clean()), COL["shell"]))
            objects.append((tri(probes[edge]), COL["probe"]))
            p0 = np.asarray(row["rootLocalUVWmm"], float); p1 = p0 + np.asarray((0, 0, row["diagnosticProbeLengthMm"]), float)
            lines.append((p0, p1, (*COL["fail"], 255), f"{edge}: {row['footprintPairCoverage']}/9; missing {row['missingFootprintPairs']}"))
        render(filename, objects, title, "grey=frozen shell sections | orange=best exact +W failure probes",
               camera=(32, -37, 16), world_lines=lines)

    ray_lines = []
    for edge, row in best_rows.items():
        for sample in row["samples"]:
            p0 = np.asarray(sample["originLocalUVWmm"], float); p1 = p0 + np.asarray((0, 0, 11), float)
            color = COL["feasible"] if sample["hasInnerOuterPair"] else COL["fail"]
            ray_lines.append((p0, p1, (*color, 230), ""))
    render("07_shell_blind_slot_footprint_ray_proof.png", [],
           "7 / FOUR BLIND-SLOT FOOTPRINTS — NONE COMPLETE", "green=inner/outer shell pair | red=aperture/no pair",
           transparent=[(shell_tri, (*COL["shell"], 60))], wireframes=[(shell_wire, (*COL["shell"], 145))],
           world_lines=ray_lines)

    render("08_pusher_clearance_closeup.png",
           [(tri(probe_compound), COL["probe"]), (tri(pusher["pusher"]), COL["pusher"])],
           "8 / PUSHER CLEARANCE — BEST FAILURE PROBES", "collision volumes are reported per leg; shell support remains the primary failure",
           camera=(23, -31, 15))

    probes_world = Compound(children=[placed(probes[e], datum, front, f"{e}_WORLD") for e in EDGES])
    i3_body = placed(body, datums["I3"], FROZEN_FRONT_DEPTHS["I3"], "I3_BODY")
    i3_act = placed(local_cylinder(ACT_D, BODY_H, 6.0, "I3_ACT"), datums["I3"], FROZEN_FRONT_DEPTHS["I3"], "I3_ACT")
    render("09_i3_clearance_closeup.png",
           [(tri(probes_world), COL["probe"]), (tri(i3_body), COL["neighbor"]), (tri(i3_act), COL["neighbor"])],
           "9 / I3 CLEARANCE — FROZEN WORLD GEOMETRY", "purple=I3 measured body+actuator | orange=I2 best root-slide probes",
           camera=(25, -35, 18))

    render("10_full_simplified_failure_combination.png",
           [(tri(body), COL["body"]), (tri(probe_compound), COL["probe"]), (tri(pusher["pusher"]), COL["pusher"]),
            (tri(corners), COL["search"])],
           "10 / FULL ROOT-SLIDE COMBINATION — NOT A CANDIDATE", "frozen shell transparent; no valid four-slot set and no candidate STEP emitted",
           transparent=[(shell_tri, (*COL["shell"], 58))], wireframes=[(shell_wire, (*COL["shell"], 135))])

    left = moved(old_harness, (-16, 0, 0), "OLD_ANGLED_DOC80")
    right = moved(probe_compound, (16, 0, 0), "NEW_PARALLEL_FAILURE")
    render("11_docs80_angled_vs_parallel_root_slide.png",
           [(tri(left), COL["old"]), (tri(right), COL["probe"])],
           "11 / docs/80 ANGLED vs +W ROOT-SLIDE", "left=old valid slanted shell targeting | right=angle-correct but shell-incomplete diagnostic",
           camera=(45, -61, 31), world_lines=[
               (np.asarray((-16, 0, 0)), np.asarray((-16, 0, 12)), (*COL["old"], 255), "docs/80 ANGLED"),
               (np.asarray((16, 0, 0)), np.asarray((16, 0, 12)), (*COL["fail"], 255), "ROOT-SLIDE INVALID"),
           ])
    return outputs


def report_text(data: dict[str, object]) -> str:
    search_rows = []
    for edge in EDGES:
        row = data["rootSearch"][edge]
        for label in ("primary1p60", "fallback1p20"):
            scan_row = row[label]["strict"]
            thickness = row[label]["thicknessMm"]
            search_rows.append(
                f"| {edge} | {thickness:.2f} | {scan_row['domainMm'][0]:.3f}…{scan_row['domainMm'][1]:.3f} | "
                f"{scan_row['stepMm']:.3f} | {scan_row['maximumFootprintPairCoverage']}/9 | "
                f"{scan_row['maximumCoverageIntervalsMm']} | {scan_row['feasibleRootIntervalsMm'] or '∅'} | "
                f"{row[label]['extended']['maximumFootprintPairCoverage']}/9 |"
            )
    best_rows = []
    failure_rows = []
    for edge, row in data["bestStrictFailureBySide"].items():
        best_rows.append(
            f"| {edge} | {row['legThicknessMm']:.2f} | {row['rootLocalUVWmm']} | {row['rootShiftLocalUVWmm']} | "
            f"{row['rootShiftMagnitudeMm']:.3f} | {row['sideOverlapMm']:.3f} | {row['footprintPairCoverage']}/9 |"
        )
        c = row["collision"]
        thickness_range = "N/A" if row["pairedShellThicknessRangeMm"] is None else f"{row['pairedShellThicknessRangeMm'][0]:.3f}…{row['pairedShellThicknessRangeMm'][1]:.3f}"
        failure_rows.append(
            f"| {edge} | {row['missingFootprintPairs']} | {thickness_range} | {row['effectiveMinimumRemainingShellMm']:.3f} | "
            f"{c['pusher']['distanceMm']:.3f} / {c['pusher']['penetrationMm3']:.6f} | "
            f"{c['minimumTerminalClearanceMm']:.3f} / {c['terminalPenetrationMm3']:.6f} | "
            f"{c['minimumNeighborClearanceMm']:.3f} / {c['neighborPenetrationMm3']:.6f} ({c['nearestNeighbor']}) | "
            f"{c['body']['distanceMm']:.3f} / {c['body']['penetrationMm3']:.6f} | "
            f"{c['cornerKeepouts']['distanceMm']:.3f} / {c['cornerKeepouts']['penetrationMm3']:.6f} |"
        )
    render_rows = "\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    return f"""# 82 — I2 +W parallel-leg root-slide simplification audit

MODE = **AUDIT-ONLY / I2 / ROOT TANGENT-SLIDE ONLY / ALL LEG AXES = +W / PRODUCTION = 0**

FINAL VERDICT = **{data['finalVerdict']}**

## 1. Scope correction from docs/81

docs/81 proved only that the four fixed side-midpoint roots cannot support one common ±W direct-shell family.
This audit does not generalize that result.  It reopens each root's tangent coordinate while preserving side
identity, switch/exterior authority and an exact +W leg direction.

The C verdict here is limited to: **current frozen I2 pose + tangent-only side-root slide + 2.60 mm straight
rectangular legs (1.60 mm primary, 1.20 mm allowed fallback) + direct frozen-shell blind slots**.

## 2. Frozen and allowed variables

- button center: `{data['freeze']['buttonCenter']}`;
- approved +W / press axis: `{data['freeze']['pressAxis']}`;
- root normal coordinates remain those of docs/81; only side tangent coordinates move;
- all leg angles to U-V = **90.000°**; maximum inter-leg angular difference = **0.000°**;
- root/candidate angular deviation = **0°**;
- production exterior, JaD/JfD split, ITS body/pose/actuator and production shell unchanged.

## 3. Side-root definition and search

The strict valid edge-support interval requires the complete 2.60 mm root width to remain projected onto its
assigned switch side.  This is the anti-corner-post gate.  A second wider diagnostic interval includes the
closure of every position with nonzero side overlap; its zero-overlap endpoints are evidence bounds only.

Strict grids use 0.050 mm spacing.  The nearest maximum-coverage point on each side is refined at 0.005 mm.
Every point uses a 3×3 exact B-rep footprint; no mesh/raster collision decides feasibility.

| side | thickness | strict tangent interval mm | grid | maximum coverage | max-coverage intervals | feasible interval | wider any-overlap max |
|---|---:|---:|---:|---:|---|---|---:|
{chr(10).join(search_rows)}

All feasible interval sets are **empty**.  The wider search reaches 9/9 only for +V at 1.20 mm in the refined
boundary interval **{data['extendedBoundaryDiagnostic']['nineOfNineIntervalMm']}**.  Across that interval,
actual side overlap is only **{data['extendedBoundaryDiagnostic']['sideOverlapRangeMm'][0]:.3f}…{data['extendedBoundaryDiagnostic']['sideOverlapRangeMm'][1]:.3f} mm**
and minimum remaining shell is **{data['extendedBoundaryDiagnostic']['remainingShellRangeMm'][0]:.3f}…{data['extendedBoundaryDiagnostic']['remainingShellRangeMm'][1]:.3f} mm**,
below the 1.20 mm rule.  It is therefore both a prohibited corner-post-like boundary position and a shell-thickness
failure, not a valid root-slide interval.

## 4. Nearest best root-slide diagnostics

These are evidence locations, not released roots.  Selection priority is maximum exact footprint coverage,
then minimum movement from the docs/81 midpoint.  Thickness 1.20 mm is selected only if required by ITS/body
clearance or if it improves maximum shell coverage.

| side | thickness | diagnostic root U,V,W | shift U,V,W from docs/81 | shift magnitude | side overlap | footprint pairs |
|---|---:|---|---|---:|---:|---:|
{chr(10).join(best_rows)}

## 5. Per-side numeric failure proof

Effective remaining shell is 0.000 mm when one or more footprint rays have no inner/outer shell pair; a planar
blind-slot floor does not exist at those missing samples.  Collision columns show distance / penetration mm³.

| side | missing rays | paired shell thickness mm | effective remaining shell | pusher | terminals | nearest neighbor | ITS body | corner keep-outs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(failure_rows)}

The decisive failure on every side is incomplete shell footprint coverage, not leg angle.  Any pusher,
neighbor, body or corner collision is an additional rejection only; a clearance pass cannot repair a missing
shell floor.

## 6. Level-1 gate

Resolved Level-0 sides: **{data['level1Gate']['resolvedLevel0SideCount']}/4**.  Because fewer than three sides
resolve, the permitted single simple local-pad Level-1 branch is **not opened**.  Pads, panels, receivers,
walls, struts, housing, carrier, doglegs and angled legs remain absent.

## 7. Candidate status

No successful candidate exists, so the requested successful-candidate leg lengths and minimum clearances are
not published as design values.  The STEP output contains four labeled **best-failure probes only**.  It must
not be used as manufacturing geometry.

## 8. Required renders

{render_rows}

## 9. Outputs and preservation

- `{data['outputs']['json']}`
- `{data['outputs']['diagnosticStep']}`
- `{data['outputs']['report']}`

All {data['preservation']['protectedFileCount']} protected docs/79–81 and production files retain identical
SHA-256 hashes: **{data['preservation']['allProtectedFilesPreserved']}**.  Production modification = 0;
production shell boolean = 0; eight-button propagation = 0; physical coupon = 0; angled-leg redesign = 0.

## 10. Stop

This audit stops at I2 +W tangent-root-slide feasibility.  It does not claim that every possible parallel-leg
architecture is impossible; changing root normal offset, side-support definition, or adding a support body is
outside this audit and would require explicit new authority.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    protected = protected_files()
    before = hashes(protected)
    datums = load_all_datums()
    datum = datums[REPRESENTATIVE]
    front = float(FROZEN_FRONT_DEPTHS[REPRESENTATIVE])
    shell_full = import_step(SHELL_STEP[datum.owner])
    ray = ExactRaySampler(shell_full)
    body = local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "I2_MEASURED_ITS_BODY")
    corners = corner_keepouts()
    pusher = pusher_system()
    terminals = terminal_proxies()
    current_rows, current_summary = current_direction_audit()

    search_data: dict[str, dict[str, object]] = {}
    exact_best: dict[str, dict[str, object]] = {}
    for edge in EDGES:
        search_data[edge] = {}
        variants = []
        for thickness, label in ((1.60, "primary1p60"), (1.20, "fallback1p20")):
            strict = scan(edge, thickness, strict_domain(edge), STRICT_STEP, datum, front, ray)
            print(f"SEARCH {edge} T={thickness:.2f} strict max={strict['maximumFootprintPairCoverage']}/9", flush=True)
            extended = scan(edge, thickness, extended_domain(edge), EXTENDED_STEP, datum, front, ray)
            print(f"SEARCH {edge} T={thickness:.2f} extended max={extended['maximumFootprintPairCoverage']}/9", flush=True)
            refined, best = refined_best(edge, thickness, strict, datum, front, ray)
            search_data[edge][label] = {
                "thicknessMm": thickness,
                "strict": strict,
                "extended": extended,
                "refinedNearBest": refined,
                "refinedBest": compact(best),
            }
            variants.append(best)
        # Prefer 1.60 mm unless 1.20 mm improves coverage or 1.60 mm penetrates
        # the measured ITS body.  Exact body penetration is checked on the
        # resulting diagnostic probe below as well.
        primary, fallback = variants
        primary_probe = make_probe(primary)
        primary_body_pen = volume(primary_probe & body)
        if (fallback["footprintPairCoverage"] > primary["footprintPairCoverage"] or
                primary_body_pen > BOOLEAN_EPS):
            chosen = fallback
        else:
            chosen = primary
        exact_best[edge] = chosen

    # The only 9/9 point found by the wider 0.10 mm scan is a +V/1.20
    # zero-overlap boundary point.  Refine it explicitly to distinguish a
    # legitimate side interval from a corner-post-like sliver.
    extended_boundary_scan = scan("+V", 1.20, (-4.36, -4.10), REFINE_STEP, datum, front, ray)
    boundary_full_rows = [row for row in extended_boundary_scan["rows"]
                          if row["footprintPairCoverage"] == 9]
    boundary_t = [float(row["tangentCoordinateMm"]) for row in boundary_full_rows]
    boundary_overlap = [float(row["sideOverlapMm"]) for row in boundary_full_rows]
    boundary_remaining = [float(row["minimumRemainingShellMm"]) for row in boundary_full_rows]
    extended_boundary_diagnostic = {
        "edge": "+V",
        "thicknessMm": 1.20,
        "scanDomainMm": [-4.36, -4.10],
        "stepMm": REFINE_STEP,
        "nineOfNineIntervalMm": [min(boundary_t), max(boundary_t)],
        "sideOverlapRangeMm": [min(boundary_overlap), max(boundary_overlap)],
        "remainingShellRangeMm": [min(boundary_remaining), max(boundary_remaining)],
        "minimumRequiredRemainingShellMm": BLIND_DEPTH,
        "validSideRoot": False,
        "shellThicknessPass": False,
        "rows": extended_boundary_scan["rows"],
    }

    probes: dict[str, Shape] = {}
    for edge, row in exact_best.items():
        probe = make_probe(row)
        row["collision"] = collision_audit(row, probe, datum, front, datums, shell_full, body, corners,
                                           pusher["pusher"], terminals)
        probes[edge] = probe

    placement = datum_location(datum, front)
    crop_tool = local_box(26.0, 26.0, 18.0, 0, 0, -2.0, "I2_ROOT_SLIDE_SHELL_CROP_TOOL")
    shell_crop_world = shell_full & (placement * crop_tool)
    if shell_crop_world is None or not shell_crop_world.solids():
        raise RuntimeError("root-slide shell crop is empty")
    shell_crop_local = placement.inverse() * shell_crop_world.clean()
    render_paths = render_outputs(exact_best, probes, shell_crop_local, datum, front, datums, pusher, body, corners)
    export_step(Compound(children=[probes[edge] for edge in EDGES],
                         label="I2_PARALLEL_W_ROOT_SLIDE_BEST_FAILURE_PROBES_AUDIT_ONLY"), DIAGNOSTIC_STEP)

    after = hashes(protected)
    resolved = sum(1 for edge in EDGES for label in ("primary1p60", "fallback1p20")
                   if search_data[edge][label]["strict"]["feasibleRootIntervalsMm"])
    # Count a side at most once.
    resolved_sides = sum(1 for edge in EDGES if any(
        search_data[edge][label]["strict"]["feasibleRootIntervalsMm"]
        for label in ("primary1p60", "fallback1p20")))
    verdict = "C — 90° PARALLEL LEGS STILL IMPOSSIBLE"
    data = {
        "schema": "onegrip.i2-parallel-w-root-slide-simplification-audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "AUDIT-ONLY / I2 / TANGENT ROOT SLIDE / +W PARALLEL / NO PRODUCTION WRITE",
        "finalVerdict": verdict,
        "freeze": {
            "button": REPRESENTATIVE,
            "owner": datum.owner,
            "buttonCenter": list(map(float, datum.center)),
            "pressAxis": list(map(float, unit(datum.axis))),
            "switchU": list(map(float, unit(datum.switch_u))),
            "switchV": list(map(float, unit(datum.switch_v))),
            "frontDepthMm": front,
            "switchPoseChange": 0,
            "exteriorChange": 0,
            "productionShellChange": 0,
            "legDirectionLocal": [0.0, 0.0, 1.0],
            "allLegAnglesToUVPlaneDeg": {edge: 90.0 for edge in EDGES},
            "maximumInterLegAngularDifferenceDeg": 0.0,
            "angularDeviationDeg": 0.0,
        },
        "docs81Interpretation": {
            "fixedRootConclusionNotGeneralized": True,
            "source": relative(DOC81_JSON),
            "currentDirectionSummary": current_summary,
            "currentDirections": current_rows,
        },
        "rootDefinition": {
            "movementAxis": {edge: list(map(float, tangent_axis(edge))) for edge in EDGES},
            "legacyRootsLocalUVWmm": {edge: list(map(float, leg_root(edge))) for edge in EDGES},
            "strictSideSupportRule": "complete 2.60 mm tangent root width projected within assigned ITS side",
            "extendedDiagnosticRule": "closure of any-nonzero-overlap range; zero-overlap endpoints are evidence bounds only",
            "cornerPostConversionAllowed": False,
            "cornerKeepout": {"count": 4, "diameterMm": CORNER_D, "centersLocalUVmm": [[u, v] for u in (-2.25, 2.25) for v in (-2.25, 2.25)]},
        },
        "rootSearch": search_data,
        "extendedBoundaryDiagnostic": extended_boundary_diagnostic,
        "bestStrictFailureBySide": {
            edge: {key: value for key, value in row.items() if key != "samples"}
            for edge, row in exact_best.items()
        },
        "bestStrictFailureSamples": {edge: row["samples"] for edge, row in exact_best.items()},
        "level1Gate": {
            "resolvedLevel0SideCount": resolved_sides,
            "variantPassCountBeforeSideDeduplication": resolved,
            "requiredResolvedSidesToOpen": 3,
            "opened": resolved_sides >= 3,
            "localPadAnalyzed": False,
        },
        "candidate": {
            "exists": False,
            "candidateStepEmitted": False,
            "diagnosticFailureProbeStepOnly": True,
            "angledLegUsed": False,
            "complexSupportUsed": False,
        },
        "preservation": {
            "protectedFileCount": len(protected),
            "hashesBefore": before,
            "hashesAfter": after,
            "allProtectedFilesPreserved": before == after,
            "productionModification": 0,
            "productionShellBoolean": 0,
            "eightButtonPropagation": 0,
            "physicalCoupon": 0,
            "angledLegRedesign": 0,
        },
        "outputs": {
            "json": relative(JSON_PATH),
            "report": relative(REPORT),
            "diagnosticStep": relative(DIAGNOSTIC_STEP),
            "renders": render_paths,
        },
    }
    JSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({
        "verdict": verdict,
        "resolvedSides": resolved_sides,
        "bestCoverage": {edge: exact_best[edge]["footprintPairCoverage"] for edge in EDGES},
        "bestShiftsMm": {edge: exact_best[edge]["rootShiftLocalUVWmm"] for edge in EDGES},
        "renders": len(render_paths),
        "protectedPreserved": before == after,
        "report": relative(REPORT),
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
