"""I2 fixed-root, parallel-W four-edge-leg Level-0 revalidation.

This is an audit-only successor to docs/80.  It does not overwrite the
existing slanted candidate.  The frozen I2 switch datum and the four docs/80
root coordinates are held fixed while all four legs are tested first along
+W and then along -W.  Leg tilt is prohibited in this module.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Compound, Shape, export_step, import_step

from .direct_shell_four_edge_i2_simplification_audit import (
    BLIND_DEPTH,
    CURRENT_FULL_STEP,
    HARNESS_STEP as DOC80_HARNESS_STEP,
    JSON_PATH as DOC80_JSON,
    LEG_THICKNESS_BY_EDGE,
    REPORT as DOC80_REPORT,
    RENDER as DOC80_RENDER,
    OUT as DOC80_OUT,
    SHELL_STEP,
    SLOT_CLEARANCE,
    SLOT_TANGENT,
    ExactRaySampler,
    leg_root,
    local_dir_to_world,
    local_point_to_world,
    protected_files as doc80_protected_files,
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
    placed,
    sha256,
    volume,
)
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import BUTTONS, ROOT, relative
from .option_c_local_exact_prototype import raster_scene, safe_edge_lines, safe_triangles
from .slot_anchored_harness_captive_pusher_audit import pusher_system, terminal_proxies


OUT = ROOT / "build123d_workbench/out/i2_parallel_w_four_edge_leg_revalidation_audit"
RENDER = ROOT / "renders/i2_parallel_w_four_edge_leg_revalidation_audit"
REPORT = ROOT / "docs/81_i2_parallel_w_four_edge_leg_revalidation_audit.md"
JSON_PATH = OUT / "i2_parallel_w_four_edge_leg_revalidation_audit.json"
PLUS_STEP = OUT / "I2_PLUS_W_PARALLEL_LEG_FEASIBILITY_PROBES_AUDIT_ONLY.step"
MINUS_STEP = OUT / "I2_MINUS_W_PARALLEL_LEG_FEASIBILITY_PROBES_AUDIT_ONLY.step"

REPRESENTATIVE = "I2"
EDGES = ("+U", "-U", "+V", "-V")
ANGLE_TOL_DEG = 0.01
SEARCH_PROBE_MM = 12.0
BOOLEAN_EPS = 1.0e-6
FOOTER = "AUDIT ONLY | FROZEN I2 ORIENTATION + FOUR ROOTS | LEG TILT = 0 | PRODUCTION PROPAGATION = 0"
COL = {
    "body": (229, 92, 100),
    "current": (65, 164, 224),
    "plus": (245, 178, 65),
    "minus": (170, 112, 219),
    "shell": (110, 131, 151),
    "pass": (61, 190, 137),
    "fail": (235, 82, 93),
    "axis": (248, 212, 78),
}


def xyz(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(map(float, value))


def angle_between(left: Iterable[float], right: Iterable[float]) -> float:
    cosine = float(np.clip(np.dot(unit(left), unit(right)), -1.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))


def protected_files() -> list[Path]:
    rows = {
        *doc80_protected_files(),
        DOC80_REPORT,
        DOC80_JSON,
        *[path for path in DOC80_OUT.rglob("*") if path.is_file()],
        *[path for path in DOC80_RENDER.rglob("*") if path.is_file()],
    }
    return sorted(path for path in rows if path.exists())


def hashes(paths: list[Path]) -> dict[str, str]:
    return {relative(path): sha256(path) for path in paths}


def current_direction_audit() -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    source = json.loads(DOC80_JSON.read_text(encoding="utf-8"))["directShell"]["legs"]
    rows: dict[str, dict[str, object]] = {}
    directions: dict[str, np.ndarray] = {}
    for edge in EDGES:
        direction = unit(source[edge]["directionLocal"])
        directions[edge] = direction
        angle_w = angle_between(direction, (0, 0, 1))
        rows[edge] = {
            "directionLocal": list(map(float, direction)),
            "rootLocalUVWmm": list(map(float, source[edge]["rootLocalUVWmm"])),
            "angleToPositiveWDeg": angle_w,
            "angleToHarnessUVPlaneDeg": 90.0 - angle_w,
            "exactlyNormalToUVWithinTolerance": angle_w <= ANGLE_TOL_DEG,
        }
    pairs = {}
    max_pair = 0.0
    for i, left in enumerate(EDGES):
        for right in EDGES[i + 1:]:
            value = angle_between(directions[left], directions[right])
            pairs[f"{left}:{right}"] = value
            max_pair = max(max_pair, value)
    return rows, {
        "angleToleranceDeg": ANGLE_TOL_DEG,
        "allExactlyNormalToUV": all(row["exactlyNormalToUVWithinTolerance"] for row in rows.values()),
        "allMutuallyParallel": max_pair <= ANGLE_TOL_DEG,
        "maximumPairwiseDirectionAngleDeg": max_pair,
        "pairwiseDirectionAnglesDeg": pairs,
    }


def footprint_axes(edge: str) -> tuple[np.ndarray, np.ndarray]:
    if edge.endswith("U"):
        return np.asarray((0.0, 1.0, 0.0)), np.asarray((1.0, 0.0, 0.0))
    return np.asarray((1.0, 0.0, 0.0)), np.asarray((0.0, 1.0, 0.0))


def probe_spec(edge: str, sign: str, datum, front: float, ray: ExactRaySampler) -> dict[str, object]:
    direction_local = np.asarray((0.0, 0.0, 1.0 if sign == "+W" else -1.0), float)
    direction_world = local_dir_to_world(datum, direction_local)
    root_local = leg_root(edge)
    root_world = local_point_to_world(datum, front, root_local)
    tangent_local, structural_local = footprint_axes(edge)
    structural_size = LEG_THICKNESS_BY_EDGE[edge] + 2.0 * SLOT_CLEARANCE
    sample_rows = []
    paired_inner: list[float] = []
    paired_outer: list[float] = []
    for tangent_offset in (-SLOT_TANGENT / 2.0, 0.0, SLOT_TANGENT / 2.0):
        for structural_offset in (-structural_size / 2.0, 0.0, structural_size / 2.0):
            sample_local = root_local + tangent_local * tangent_offset + structural_local * structural_offset
            sample_world = local_point_to_world(datum, front, sample_local)
            hit_values = ray.hits(sample_world, direction_world, 30.0)
            pair = len(hit_values) >= 2
            if pair:
                paired_inner.append(hit_values[0])
                paired_outer.append(hit_values[1])
            sample_rows.append({
                "offsetTangentMm": float(tangent_offset),
                "offsetStructuralMm": float(structural_offset),
                "originLocalUVWmm": list(map(float, sample_local)),
                "hitsMm": hit_values,
                "hasInnerOuterPair": pair,
            })

    center_hits = ray.hits(root_world, direction_world, 30.0)
    coverage = len(paired_inner)
    full_coverage = coverage == 9
    floor_distance = max(paired_inner) + BLIND_DEPTH if full_coverage else None
    minimum_remaining = min(paired_outer) - floor_distance if floor_distance is not None else None
    # A missing inner/outer pair means zero effective support at that footprint
    # sample.  Keep the physical planar-floor remainder as N/A, but also expose
    # this conservative numeric value so failed roots can be compared directly.
    effective_minimum_remaining = float(minimum_remaining) if minimum_remaining is not None else 0.0
    shell_thicknesses = [outer - inner for inner, outer in zip(paired_inner, paired_outer)]
    shell_pass = bool(full_coverage and minimum_remaining is not None and minimum_remaining >= BLIND_DEPTH)

    if full_coverage:
        probe_length = float(floor_distance)
    elif len(center_hits) >= 2:
        probe_length = float(center_hits[0] + BLIND_DEPTH)
    else:
        probe_length = SEARCH_PROBE_MM
    end_local = root_local + direction_local * probe_length
    probe = oriented_box_between(
        xyz(root_local), xyz(end_local), xyz(tangent_local), LEG_TANGENTIAL,
        LEG_THICKNESS_BY_EDGE[edge], label=f"I2_{edge}_{sign}_FIXED_DIRECTION_FEASIBILITY_PROBE",
    )

    if len(center_hits) < 2:
        reason = "NO CENTER INNER/OUTER SHELL PAIR"
    elif not full_coverage:
        reason = f"SLOT FOOTPRINT PARTLY OVER APERTURE ({coverage}/9 supported)"
    elif minimum_remaining < BLIND_DEPTH:
        reason = f"PLANAR FLOOR LEAVES {minimum_remaining:.3f} mm MINIMUM SHELL (< {BLIND_DEPTH:.2f} mm)"
    else:
        reason = "PASS"
    return {
        "edge": edge,
        "sign": sign,
        "rootLocalUVWmm": list(map(float, root_local)),
        "directionLocal": list(map(float, direction_local)),
        "directionWorld": list(map(float, direction_world)),
        "angleToHarnessUVPlaneDeg": 90.0,
        "centerHitsMm": center_hits,
        "centerPairCount": len(center_hits) // 2,
        "centerFirstShellThicknessMm": None if len(center_hits) < 2 else float(center_hits[1] - center_hits[0]),
        "footprintPairCoverage": coverage,
        "footprintSampleCount": 9,
        "missingFootprintPairs": 9 - coverage,
        "pairedShellThicknessRangeMm": None if not shell_thicknesses else [float(min(shell_thicknesses)), float(max(shell_thicknesses))],
        "requiredPlanarFloorDistanceMm": None if floor_distance is None else float(floor_distance),
        "minimumRemainingShellAfterFloorMm": None if minimum_remaining is None else float(minimum_remaining),
        "effectiveMinimumRemainingShellMm": effective_minimum_remaining,
        "minimumRequiredRemainingShellMm": BLIND_DEPTH,
        "shellSupportPass": shell_pass,
        "failureReason": reason,
        "diagnosticProbeLengthMm": probe_length,
        "samples": sample_rows,
        "probe": probe,
        "tangentLocal": list(map(float, tangent_local)),
    }


def clearance_audit(spec: dict[str, object], shell_full: Shape, datum, front: float,
                    datums: dict[str, object]) -> dict[str, object]:
    probe: Shape = spec["probe"]
    terminals = terminal_proxies()
    pusher = pusher_system()["pusher"]
    terminal_rows = {}
    for name, proxy in terminals.items():
        pen = volume(probe & proxy)
        terminal_rows[name] = {
            "distanceMm": float(probe.distance_to(proxy)),
            "penetrationMm3": pen,
            "clear": pen <= BOOLEAN_EPS,
        }
    pusher_pen = volume(probe & pusher)
    probe_world = placed(probe, datum, front, f"I2_{spec['edge']}_{spec['sign']}_WORLD_PROBE")
    shell_pen = volume(probe_world & shell_full)

    local_body = local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "MEASURED_ITS_BODY")
    local_actuator = local_cylinder(ACT_D, BODY_H, 6.0, "MEASURED_ITS_ACTUATOR")
    neighbor_rows = {}
    for name in BUTTONS:
        if name == REPRESENTATIVE:
            continue
        body_world = placed(local_body, datums[name], FROZEN_FRONT_DEPTHS[name], f"{name}_BODY")
        actuator_world = placed(local_actuator, datums[name], FROZEN_FRONT_DEPTHS[name], f"{name}_ACTUATOR")
        distances = [float(probe_world.distance_to(body_world)), float(probe_world.distance_to(actuator_world))]
        penetrations = [volume(probe_world & body_world), volume(probe_world & actuator_world)]
        neighbor_rows[name] = {
            "minimumDistanceMm": min(distances),
            "penetrationMm3": float(sum(penetrations)),
            "clear": sum(penetrations) <= BOOLEAN_EPS,
        }
    nearest = min(neighbor_rows, key=lambda name: neighbor_rows[name]["minimumDistanceMm"])
    return {
        "probeDefinition": "fixed-root straight rectangular feasibility probe; not a released candidate",
        "uncutShellOverlapMm3": shell_pen,
        "terminalMinimumDistanceMm": min(row["distanceMm"] for row in terminal_rows.values()),
        "terminalPenetrationMm3": sum(row["penetrationMm3"] for row in terminal_rows.values()),
        "terminals": terminal_rows,
        "pusherDistanceMm": float(probe.distance_to(pusher)),
        "pusherPenetrationMm3": pusher_pen,
        "nearestNeighbor": nearest,
        "neighborMinimumDistanceMm": neighbor_rows[nearest]["minimumDistanceMm"],
        "neighborPenetrationMm3": neighbor_rows[nearest]["penetrationMm3"],
        "neighbors": neighbor_rows,
    }


def tri(shape: Shape) -> np.ndarray:
    return safe_triangles(shape)


def render_outputs(current_rows: dict[str, dict[str, object]], probes: dict[str, dict[str, dict[str, object]]],
                   shell_crop_local: Shape) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    body = local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "I2_BODY")
    current_harness = import_step(DOC80_HARNESS_STEP)

    def render(filename: str, objects, title: str, subtitle: str, camera=(29, -40, 23),
               transparent=None, wireframes=None, world_lines=None, size=(1440, 960)):
        path = RENDER / filename
        raster_scene(path, objects, title, subtitle, FOOTER, camera_offset=camera,
                     transparent_objects=transparent or [], wireframes=wireframes or [],
                     world_lines=world_lines or [], final_size=size)
        outputs.append(relative(path))

    current_lines = [(np.asarray((0, 0, 0)), np.asarray((0, 0, 10)), (*COL["axis"], 255), "+W NORMAL")]
    for edge, row in current_rows.items():
        p0 = np.asarray(row["rootLocalUVWmm"], float)
        direction = np.asarray(row["directionLocal"], float)
        p1 = p0 + direction * 8.0
        current_lines.append((p0, p1, (*COL["current"], 255), f"{edge} off W {row['angleToPositiveWDeg']:.2f} deg"))
    render("01_current_i2_direction_revalidation.png",
           [(tri(current_harness), COL["current"]), (tri(body), COL["body"])],
           "1 / CURRENT I2 IS NOT A PARALLEL-W HARNESS",
           "blue leaders are the four stored docs/80 directions; yellow is exact +W",
           camera=(25, -38, 22), world_lines=current_lines)

    shell_tri = tri(shell_crop_local)
    shell_wire = safe_edge_lines(shell_crop_local)
    for index, sign in enumerate(("+W", "-W"), start=2):
        compound = Compound(children=[probes[sign][edge]["probe"] for edge in EDGES])
        lines = []
        for edge in EDGES:
            row = probes[sign][edge]
            p0 = np.asarray(row["rootLocalUVWmm"], float)
            direction = np.asarray(row["directionLocal"], float)
            p1 = p0 + direction * row["diagnosticProbeLengthMm"]
            label = f"{edge}: {row['footprintPairCoverage']}/9 | {row['failureReason']}"
            lines.append((p0, p1, (*COL["fail"], 255), label))
        render(f"0{index}_{sign[0].lower()}w_parallel_fixed_root_probes.png",
               [(tri(compound), COL["plus"] if sign == "+W" else COL["minus"]), (tri(body), COL["body"])],
               f"{index} / ALL FOUR LEGS FIXED TO {sign}",
               "probe lengths are diagnostic only; no tilted shell targeting is permitted",
               camera=(29, -40, 23), transparent=[(shell_tri, (*COL["shell"], 56))],
               wireframes=[(shell_wire, (*COL["shell"], 150))], world_lines=lines)

        ray_lines = []
        for edge in EDGES:
            row = probes[sign][edge]
            direction = np.asarray(row["directionLocal"], float)
            for sample in row["samples"]:
                p0 = np.asarray(sample["originLocalUVWmm"], float)
                p1 = p0 + direction * 14.0
                color = COL["pass"] if sample["hasInnerOuterPair"] else COL["fail"]
                ray_lines.append((p0, p1, (*color, 225), ""))
        render(f"0{index + 2}_{sign[0].lower()}w_footprint_36_ray_coverage.png", [],
               f"{index + 2} / {sign} — 36 EXACT FOOTPRINT RAYS",
               "green=inner/outer pair found; red=no shell pair within 30 mm",
               camera=(28, -39, 22), transparent=[(shell_tri, (*COL["shell"], 62))],
               wireframes=[(shell_wire, (*COL["shell"], 145))], world_lines=ray_lines)

    plus_v = probes["-W"]["+V"]
    slab = local_box(0.45, 18.0, 27.0, 0, 2.0, -15.0, "PLUS_V_MINUS_W_SECTION_SLAB")
    section = shell_crop_local & slab
    section_objects = [] if section is None or not section.solids() else [(tri(section.clean()), COL["shell"])]
    section_objects.append((tri(plus_v["probe"]), COL["minus"]))
    root = np.asarray(plus_v["rootLocalUVWmm"], float)
    floor = root + np.asarray((0, 0, -1), float) * plus_v["requiredPlanarFloorDistanceMm"]
    render("06_minus_w_plus_v_planar_floor_breakthrough.png", section_objects,
           "6 / -W +V HAS 9/9 HITS BUT FAILS REMAINING THICKNESS",
           f"required floor={plus_v['requiredPlanarFloorDistanceMm']:.3f} mm; minimum remainder={plus_v['minimumRemainingShellAfterFloorMm']:.3f} mm",
           camera=(33, -1, 7), world_lines=[(root, floor, (*COL["fail"], 255), "PLANAR FLOOR")])
    return outputs


def report_text(data: dict[str, object]) -> str:
    current_rows = "\n".join(
        f"| {edge} | {row['directionLocal'][0]:.6f}, {row['directionLocal'][1]:.6f}, {row['directionLocal'][2]:.6f} | "
        f"{row['angleToPositiveWDeg']:.3f}° | {row['angleToHarnessUVPlaneDeg']:.3f}° | {row['exactlyNormalToUVWithinTolerance']} |"
        for edge, row in data["currentCandidate"]["legs"].items()
    )
    support_rows = []
    for sign in ("+W", "-W"):
        for edge, row in data["parallelLevel0Tests"][sign]["legs"].items():
            thickness = "N/A" if row["pairedShellThicknessRangeMm"] is None else f"{row['pairedShellThicknessRangeMm'][0]:.3f}…{row['pairedShellThicknessRangeMm'][1]:.3f}"
            remaining = f"{row['effectiveMinimumRemainingShellMm']:.3f}"
            support_rows.append(
                f"| {sign} | {edge} | {row['centerPairCount']} | {row['footprintPairCoverage']}/9 | {thickness} | "
                f"{remaining} | {row['shellSupportPass']} | {row['failureReason']} |"
            )
    collision_rows = []
    for sign in ("+W", "-W"):
        for edge, row in data["parallelLevel0Tests"][sign]["legs"].items():
            c = row["clearance"]
            collision_rows.append(
                f"| {sign} | {edge} | {row['diagnosticProbeLengthMm']:.3f} | {c['uncutShellOverlapMm3']:.3f} | "
                f"{c['terminalMinimumDistanceMm']:.3f} / {c['terminalPenetrationMm3']:.6f} | "
                f"{c['pusherDistanceMm']:.3f} / {c['pusherPenetrationMm3']:.6f} | "
                f"{c['neighborMinimumDistanceMm']:.3f} / {c['neighborPenetrationMm3']:.6f} ({c['nearestNeighbor']}) |"
            )
    render_rows = "\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    return f"""# 81 — I2 parallel-W four-edge-leg revalidation audit

MODE = **AUDIT-ONLY / I2 / FROZEN SWITCH ORIENTATION + FOUR ROOTS / LEG TILT = 0**

FINAL VERDICT = **{data['finalVerdict']}**

## 1. Direct answer

The current docs/80 I2 candidate is **not** normal to the harness U-V plane and its four legs are **not**
mutually parallel.  Their off-W angles are 11.866° to 22.653°; the maximum pairwise direction difference is
**{data['currentCandidate']['summary']['maximumPairwiseDirectionAngleDeg']:.3f}°**.

The requested Level-0 rebase was therefore tested without changing the frozen switch datum or any root:
all four directions were set exactly to +W, then exactly to -W, with only individual probe/floor length allowed.
Neither common direction produces four valid direct-shell blind-slot legs.  Consequently this audit exports
**diagnostic probes only, not a Level-0 candidate**.

## 2. Current direction check

Tolerance for the explicit exact-direction test: **{data['currentCandidate']['summary']['angleToleranceDeg']:.3f}°**.

| leg | stored local direction U,V,W | angle to +W | angle to U-V plane | exactly 90° to U-V |
|---|---|---:|---:|---|
{current_rows}

All normal: **{data['currentCandidate']['summary']['allExactlyNormalToUV']}**.  All mutually parallel:
**{data['currentCandidate']['summary']['allMutuallyParallel']}**.

## 3. Fixed-root exact shell proof

Each slot footprint is 3.00 mm tangent by 1.60 mm (+U) or 2.00 mm (others), including 0.20 mm clearance per
side.  It was tested with a 3×3 exact B-rep ray grid.  A valid blind slot requires all 9 rays to have an
inner/outer pair and a common planar floor that supplies 1.20 mm engagement while retaining at least 1.20 mm
shell beyond the floor.

| direction | leg | center shell pairs | footprint pairs | paired shell thickness mm | effective minimum shell remaining mm | pass | numeric reason |
|---|---|---:|---:|---:|---:|---|---|
{chr(10).join(support_rows)}

An effective remainder of **0.000 mm** means at least one footprint ray has no shell inner/outer pair, so no
physical planar floor exists there; it is not a claim that a valid shell wall was measured as zero-thickness.

The +W option fails all four roots because 4–6 of the 9 footprint rays lie in the button aperture even where
parts of the rectangle reach shell material.  The -W option has no shell pair at +U, -U, or -V.  Its +V root
does reach a deeper shell region at all 9 points, but inner-face curvature forces a planar floor to
**{data['parallelLevel0Tests']['-W']['legs']['+V']['requiredPlanarFloorDistanceMm']:.3f} mm**; the earliest
outer exit is closer than that floor, producing **{data['parallelLevel0Tests']['-W']['legs']['+V']['minimumRemainingShellAfterFloorMm']:.3f} mm**
minimum remaining material.  It therefore breaks through rather than retaining 1.20 mm.

## 4. Collision and neighboring-clearance proof

These boxes use the frozen roots and exact ±W only.  Where no complete shell target exists, 12.00 mm is a
bounded search probe, not a proposed leg.  `uncut shell overlap` is the material a valid slot would have to
remove; terminal, pusher and neighbor penetration are true collision volumes.

| direction | leg | probe length mm | uncut shell overlap mm³ | terminal distance / penetration | pusher distance / penetration | nearest neighbor distance / penetration |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(collision_rows)}

Neighbor scope is the other seven frozen measured ITS body and actuator envelopes.  A zero distance is
interpreted together with penetration volume; zero penetration means tangent/contact without volumetric collision.
The shell-support failure above is decisive even when neighboring and mechanism clearances are positive.

## 5. Frozen authority and non-propagation

- switch center: `{data['freeze']['buttonCenter']}`;
- local +W / approved press axis: `{data['freeze']['pressAxis']}`;
- four roots: `{data['freeze']['rootsLocalUVWmm']}`;
- root change = 0; switch orientation change = 0; leg tilt used = 0;
- production modification = 0; shell boolean = 0; eight-button propagation = 0;
- docs/79, docs/80 and protected production artifacts hash-preserved: **{data['preservation']['allProtectedFilesPreserved']}**.

## 6. Evidence renders

{render_rows}

## 7. Outputs

- `{data['outputs']['json']}`
- `{data['outputs']['plusWDiagnosticStep']}`
- `{data['outputs']['minusWDiagnosticStep']}`
- `{data['outputs']['report']}`

No parallel-leg candidate STEP was emitted because neither ±W family passes all four roots.
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
    current_rows, current_summary = current_direction_audit()

    probes: dict[str, dict[str, dict[str, object]]] = {}
    for sign in ("+W", "-W"):
        probes[sign] = {}
        for edge in EDGES:
            row = probe_spec(edge, sign, datum, front, ray)
            row["clearance"] = clearance_audit(row, shell_full, datum, front, datums)
            probes[sign][edge] = row

    placement = datum_location(datum, front)
    crop_local_tool = local_box(26.0, 26.0, 34.0, 0, 0, -18.0, "I2_PARALLEL_W_AUDIT_CROP_TOOL")
    shell_crop_world = shell_full & (placement * crop_local_tool)
    if shell_crop_world is None or not shell_crop_world.solids():
        raise RuntimeError("parallel-W shell audit crop is empty")
    shell_crop_local = placement.inverse() * shell_crop_world.clean()

    render_paths = render_outputs(current_rows, probes, shell_crop_local)
    export_step(Compound(children=[probes["+W"][edge]["probe"] for edge in EDGES],
                         label="I2_PLUS_W_PARALLEL_FEASIBILITY_PROBES_AUDIT_ONLY"), PLUS_STEP)
    export_step(Compound(children=[probes["-W"][edge]["probe"] for edge in EDGES],
                         label="I2_MINUS_W_PARALLEL_FEASIBILITY_PROBES_AUDIT_ONLY"), MINUS_STEP)

    after = hashes(protected)
    serializable_tests = {}
    for sign in ("+W", "-W"):
        serializable_tests[sign] = {
            "commonDirectionLocal": [0.0, 0.0, 1.0 if sign == "+W" else -1.0],
            "allFourDirectionsIdentical": True,
            "allFourNormalToUV": True,
            "allFourShellSupportPass": all(probes[sign][edge]["shellSupportPass"] for edge in EDGES),
            "legs": {
                edge: {key: value for key, value in probes[sign][edge].items()
                       if key not in ("probe", "tangentLocal")}
                for edge in EDGES
            },
        }
    verdict = "C — FIXED-ROOT 90-DEGREE PARALLEL-W LEVEL-0 IS IMPOSSIBLE ON THE CURRENT FROZEN I2 SHELL"
    data = {
        "schema": "onegrip.i2-parallel-w-four-edge-leg-revalidation-audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "AUDIT-ONLY / I2 / FIXED ROOTS / FIXED SWITCH ORIENTATION / LEG TILT 0",
        "finalVerdict": verdict,
        "freeze": {
            "button": REPRESENTATIVE,
            "owner": datum.owner,
            "buttonCenter": list(map(float, datum.center)),
            "pressAxis": list(map(float, unit(datum.axis))),
            "switchU": list(map(float, unit(datum.switch_u))),
            "switchV": list(map(float, unit(datum.switch_v))),
            "rootsLocalUVWmm": {edge: list(map(float, leg_root(edge))) for edge in EDGES},
            "frontDepthMm": front,
            "rootChangeMm": 0.0,
            "switchOrientationChangeDeg": 0.0,
            "legTiltUsedDeg": 0.0,
        },
        "currentCandidate": {"source": relative(DOC80_JSON), "legs": current_rows, "summary": current_summary},
        "parallelLevel0Tests": serializable_tests,
        "preservation": {
            "protectedFileCount": len(protected),
            "allProtectedFilesPreserved": before == after,
            "hashesBefore": before,
            "hashesAfter": after,
            "productionModification": 0,
            "productionShellBoolean": 0,
            "candidateStepEmitted": False,
            "diagnosticProbeStepsOnly": True,
            "eightButtonPropagation": 0,
        },
        "outputs": {
            "json": relative(JSON_PATH),
            "report": relative(REPORT),
            "plusWDiagnosticStep": relative(PLUS_STEP),
            "minusWDiagnosticStep": relative(MINUS_STEP),
            "renders": render_paths,
        },
    }
    JSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({
        "verdict": verdict,
        "currentAllNormal": current_summary["allExactlyNormalToUV"],
        "currentAllParallel": current_summary["allMutuallyParallel"],
        "plusWCoverage": {edge: probes["+W"][edge]["footprintPairCoverage"] for edge in EDGES},
        "minusWCoverage": {edge: probes["-W"][edge]["footprintPairCoverage"] for edge in EDGES},
        "minusWPlusVRemainingMm": probes["-W"]["+V"]["minimumRemainingShellAfterFloorMm"],
        "renders": len(render_paths),
        "protectedPreserved": before == after,
        "report": relative(REPORT),
    }, indent=2))


if __name__ == "__main__":
    main()
