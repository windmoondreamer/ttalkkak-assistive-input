"""Audit-only rescue of the seven unresolved docs/90 four-edge legs."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Compound, Location, Shape, Vector, export_step, import_step

from . import eight_button_four_edge_batch_propagation_screening as d90
from . import i2_detailed_pushbtn_manufacturing_robust_audit as doc84
from . import i2_final_local_clearance_balancing_audit as doc89
from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler, SHELL_STEP
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import local_box, volume
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import ROOT, relative
from .option_c_local_exact_prototype import raster_scene, safe_edge_lines, safe_triangles
from .slot_anchored_harness_captive_pusher_audit import pusher_system


DOC90_JSON = ROOT / "build123d_workbench/out/eight_button_four_edge_batch_propagation_screening/eight_button_four_edge_batch_propagation_screening.json"
OUT = ROOT / "build123d_workbench/out/seven_unresolved_leg_root_shell_target_rescue_audit"
RENDER = ROOT / "renders/seven_unresolved_leg_root_shell_target_rescue_audit"
REPORT = ROOT / "docs/91_seven_unresolved_leg_root_shell_target_rescue_audit.md"
JSON_PATH = OUT / "seven_unresolved_leg_root_shell_target_rescue_audit.json"
RESCUED_ALL8_STEP = OUT / "ALL8_RESCUED_FOUR_EDGE_HARNESSES_AUDIT_ONLY.step"
RESCUED_SLOT_STEP = OUT / "ALL8_RESCUED_DIRECT_SHELL_SLOTS_AUDIT_ONLY.step"

TARGETS = {"N2": ("+U", "+V", "-V"), "I3": ("+U", "-U"), "I4": ("+U",), "N3": ("+V",)}
FAIL_BUTTONS = tuple(TARGETS)
EDGES = d90.EDGES
ROOT_T_VALUES = (-0.40, -0.20, 0.0, 0.20, 0.40)
RADIAL_VALUES = tuple(float(x) for x in np.arange(3.0, 8.01, 0.50))
TANGENT_VALUES = tuple(float(x) for x in np.arange(-3.0, 3.01, 0.50))
# The largest bounded side map in this audit produces 390 root/target
# proposals across both angle bands.  A cap of 400 therefore exhausts every
# local proposal without approaching the prohibited thousands-per-leg regime.
MAX_EXACT_PER_BAND = 400
EPS = 1.0e-6
FOOTER = "7-LEG ROOT/TARGET RESCUE | STRAIGHT FOUR-EDGE | FROZEN EXTERIOR | PRODUCTION 0"
COL = {"rescued": (54, 190, 132), "hardening": (247, 177, 62), "fail": (235, 74, 88),
       "body": (66, 166, 225), "terminal": (218, 225, 232), "shell": (102, 125, 148),
       "slot": (239, 126, 65), "frozen": (160, 104, 215), "axis": (250, 212, 76)}


def xyz(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(map(float, value))


def protected_files() -> list[Path]:
    rows = set(d90.protected_files())
    rows.update({ROOT / "docs/90_eight_button_four_edge_batch_propagation_screening.md",
                 ROOT / "build123d_workbench/eight_button_four_edge_batch_propagation_screening.py"})
    for folder in (ROOT / "build123d_workbench/out/eight_button_four_edge_batch_propagation_screening",
                   ROOT / "renders/eight_button_four_edge_batch_propagation_screening"):
        rows.update(path for path in folder.rglob("*") if path.is_file())
    return sorted(path for path in rows if path.exists())


def side_target_uv(edge: str, radial: float, tangent: float) -> tuple[float, float]:
    signed = radial if edge.startswith("+") else -radial
    return (signed, tangent) if edge.endswith("U") else (tangent, signed)


def target_map(edge: str, datum, front: float, ray: ExactRaySampler) -> list[dict[str, object]]:
    press_depth = front + doc84.MEASURED_BODY_HEIGHT_REFERENCE
    rows = []
    for radial in RADIAL_VALUES:
        for tangent in TANGENT_VALUES:
            u0, v0 = side_target_uv(edge, radial, tangent)
            hits = ray.exterior_depth_hits(datum, u0, v0)
            if len(hits) < 2:
                continue
            rows.append({"targetLocalUVmm": [u0, v0],
                         "innerLocalWmm": float(press_depth - hits[1]),
                         "normalShellThicknessMm": float(hits[1] - hits[0]),
                         "sideIdentityPreserved": True})
    return rows


def proposal_rows(edge: str, targets: list[dict[str, object]], tilt_min: float, tilt_max: float) -> list[dict[str, object]]:
    proposals = []
    for root_t in ROOT_T_VALUES:
        preliminary_root = d90.base_root(edge, 1.30, root_t)
        for target in targets:
            target_point = np.asarray((*target["targetLocalUVmm"], target["innerLocalWmm"]), float)
            delta = target_point - preliminary_root
            if delta[2] <= 0.0:
                continue
            vector = unit(delta)
            tilt = math.degrees(math.acos(float(np.clip(vector[2], -1.0, 1.0))))
            if tilt < tilt_min - 1.0e-8 or tilt > tilt_max + 1.0e-8:
                continue
            azimuth = math.degrees(math.atan2(float(vector[1]), float(vector[0])))
            target_shift = float(np.linalg.norm(delta[:2]))
            proposals.append({"rootT": root_t, "tiltDeg": tilt, "azimuthDeg": azimuth,
                              "targetLocalUVmm": list(map(float, target["targetLocalUVmm"])),
                              "targetInnerLocalWmm": float(target["innerLocalWmm"]),
                              "targetShiftMagnitudeMm": target_shift,
                              "normalShellThicknessMm": float(target["normalShellThicknessMm"])})
    proposals.sort(key=lambda row: (float(row["tiltDeg"]), abs(float(row["rootT"])),
                                    float(row["targetShiftMagnitudeMm"])))
    unique = []
    seen = set()
    for row in proposals:
        key = (round(float(row["rootT"]), 2), round(float(row["tiltDeg"]), 2),
               round(float(row["azimuthDeg"]), 1))
        if key in seen:
            continue
        seen.add(key); unique.append(row)
    return unique


def rescue_leg(button: str, edge: str, datum, front: float, ray: ExactRaySampler,
               local_parts: dict[str, Shape], corners: Shape, pusher: Shape, placement,
               detailed_world: dict[str, dict[str, Shape]]) -> tuple[dict[str, object] | None, dict[str, object]]:
    targets = target_map(edge, datum, front, ray)
    diagnostics = {"targetMapCount": len(targets), "rootValuesMm": list(ROOT_T_VALUES),
                   "exactEvaluationsLe30": 0, "exactEvaluations31To45": 0,
                   "globalOptimizer": False, "sideIdentityRule": "root on assigned side; endpoint tangent |t|<=3.0 mm"}
    best_failure = None
    for band_name, lower, upper in (("le30", 0.0, 30.0), ("31to45", 30.000001, 45.0)):
        proposals = proposal_rows(edge, targets, lower, upper)
        diagnostics[f"proposalCount{band_name}"] = len(proposals)
        passed = []
        first_pass_tilt = None
        for proposal in proposals[:MAX_EXACT_PER_BAND]:
            row = d90.evaluate_leg(edge, float(proposal["rootT"]), float(proposal["tiltDeg"]),
                                   float(proposal["azimuthDeg"]), datum, front, ray)
            diagnostics["exactEvaluationsLe30" if band_name == "le30" else "exactEvaluations31To45"] += 1
            row["targetSeedLocalUVmm"] = proposal["targetLocalUVmm"]
            row["targetSeedInnerLocalWmm"] = proposal["targetInnerLocalWmm"]
            row["targetSeedNormalShellThicknessMm"] = proposal["normalShellThicknessMm"]
            row["searchBand"] = "<=30" if band_name == "le30" else "30<tilt<=45"
            if not row.get("feasible"):
                if best_failure is None or int(row.get("footprintPairCoverage", 0)) > int(best_failure.get("footprintPairCoverage", 0)):
                    best_failure = row
                continue
            static = d90.leg_static(row, local_parts, corners, pusher, placement, detailed_world, button)
            row["static"] = static
            if not static["allClear"]:
                continue
            root = np.asarray(row["rootLocalUVWmm"], float)
            floor = np.asarray(row["floorPointLocalUVWmm"], float)
            row["rootShiftLocalUVWmm"] = (root - d90.base_root(edge, float(row["legThicknessMm"]), 0.0)).tolist()
            row["rootShiftMagnitudeMm"] = abs(float(row["rootTangentCoordinateMm"]))
            row["shellTargetShiftLocalUVmm"] = (floor[:2] - root[:2]).tolist()
            row["shellTargetShiftMagnitudeMm"] = float(np.linalg.norm(floor[:2] - root[:2]))
            row["rootSharedWidthMm"] = d90.FRAME_WIDTH - abs(float(row["rootTangentCoordinateMm"]))
            row["rootSharedThicknessMm"] = float(row["legThicknessMm"])
            row["minimumRootNeckMm"] = min(float(row["rootSharedWidthMm"]),
                                            float(row["rootSharedThicknessMm"]), d90.ROOT_EMBED)
            row["sideIdentityPreserved"] = True
            row["cornerPost"] = False
            row["fullSlotFootprintSupportPercent"] = 100.0
            passed.append(row)
            if first_pass_tilt is None:
                first_pass_tilt = float(row["tiltFromWDeg"])
            if float(row["tiltFromWDeg"]) > first_pass_tilt + 1.0:
                break
        if passed:
            selected = max(passed, key=lambda row: (
                -float(row["tiltFromWDeg"]),
                min(float(row["minimumRemainingShellMm"]),
                    float(row["static"]["body"]["distanceMm"]),
                    min(float(v["distanceMm"]) for v in row["static"]["terminals"].values()),
                    float(row["static"]["minimumNeighborClearanceMm"])),
                -float(row["rootShiftMagnitudeMm"])))
            diagnostics["selectedBand"] = selected["searchBand"]
            diagnostics["result"] = "RESCUED"
            return selected, diagnostics
    diagnostics["result"] = "FAIL — NO USABLE SIDE-REGION SHELL LANDING"
    diagnostics["bestFailure"] = d90.serial_row(best_failure) if best_failure else None
    return None, diagnostics


def reconstruct_row(row: dict[str, object], edge: str) -> dict[str, object]:
    root = np.asarray(row["rootLocalUVWmm"], float)
    floor = np.asarray(row["floorPointLocalUVWmm"], float)
    vector = np.asarray(row["directionLocal"], float)
    tangent = np.asarray(row["tangentLocal"], float)
    thickness = float(row["legThicknessMm"]); width = float(row["legTangentWidthMm"])
    leg = oriented_box_between(xyz(root - vector * d90.ROOT_EMBED), xyz(floor), xyz(tangent), width,
                               thickness, label=f"{edge}_FROZEN_DOC90_STRAIGHT_LEG")
    samples = row.get("samples", [])
    inner = [float(sample["hitsMm"][0]) for sample in samples if len(sample.get("hitsMm", [])) >= 2]
    outer = [float(sample["hitsMm"][1]) for sample in samples if len(sample.get("hitsMm", [])) >= 2]
    if len(inner) != 9:
        raise RuntimeError(f"{edge} frozen resolved row lost 9/9 shell samples")
    structural = np.asarray(row["structuralLocal"], float)
    slot_start = root + vector * (min(inner) - 0.35)
    slot = oriented_box_between(xyz(slot_start), xyz(floor), xyz(tangent),
                                width + 2 * d90.SLOT_CLEARANCE, thickness + 2 * d90.SLOT_CLEARANCE,
                                label=f"{edge}_FROZEN_DOC90_SLOT")
    mouth_start = root + vector * (min(inner) - 0.40)
    mouth_end = root + vector * (max(inner) + d90.MOUTH_DEPTH)
    mouth = oriented_box_between(xyz(mouth_start), xyz(mouth_end), xyz(tangent),
                                 width + 2 * d90.MOUTH_CLEARANCE, thickness + 2 * d90.MOUTH_CLEARANCE,
                                 label=f"{edge}_FROZEN_DOC90_MOUTH")
    result = dict(row); result.update({"leg": leg, "slotTool": slot, "mouthTool": mouth,
                                      "structuralLocal": structural.tolist()})
    return result


def manufacturing_gate(button: str, candidate: dict[str, object], shell: dict[str, Shape],
                       step_path: Path, rear: dict[str, object]) -> dict[str, object]:
    export_step(candidate["harness"], step_path); imported = import_step(step_path)
    neck = min(d90.FRAME_WIDTH - abs(float(candidate["rows"][edge]["rootTangentCoordinateMm"])) for edge in EDGES)
    effective = min(float(candidate["rows"][edge]["effectiveFdmThicknessMm"]) for edge in EDGES)
    shell_pen = volume(candidate["harness"] & shell["slotted"])
    gate = {"solidCount": len(candidate["harness"].solids()), "valid": bool(candidate["harness"].is_valid),
            "stepReimportSolidCount": len(imported.solids()), "stepReimportValid": bool(imported.is_valid),
            "minimumStructuralNeckMm": neck, "minimumEffectiveFdmThicknessMm": effective,
            "rootCommonVolumeByEdgeMm3": candidate["rootCommonVolumeByEdgeMm3"],
            "shellUnintendedPenetrationMm3": shell_pen}
    gate["result"] = "PASS" if (gate["solidCount"] == gate["stepReimportSolidCount"] == 1 and
        gate["valid"] and gate["stepReimportValid"] and neck >= 1.20 - EPS and effective >= 1.20 - EPS and
        all(float(value) > EPS for value in gate["rootCommonVolumeByEdgeMm3"].values()) and
        shell_pen <= EPS and rear["result"] == "PASS") else "FAIL"
    return gate


def world_frozen_harnesses(d90_data: dict[str, object], placements: dict[str, Location]) -> dict[str, Shape]:
    rows = {"I2": import_step(doc89.HARNESS_STEP)}
    for name in ("N1", "M3", "M4"):
        rows[name] = import_step(ROOT / d90_data["buttons"][name]["auditHarnessStep"])
    return {name: placements[name] * shape for name, shape in rows.items()}


def nearest_harness_metrics(name: str, world_harness: Shape, other_harnesses: dict[str, Shape]) -> dict[str, object]:
    values = {other: d90.pair(world_harness, shape) for other, shape in other_harnesses.items() if other != name}
    nearest = min(values, key=lambda key: float(values[key]["distanceMm"]))
    return {"nearestHarness": nearest, "minimumDistanceMm": float(values[nearest]["distanceMm"]),
            "penetrationMm3": sum(float(row["penetrationMm3"]) for row in values.values()), "items": values}


def render_outputs(results: dict[str, dict[str, object]], world: dict[str, dict[str, Shape]],
                   detailed_world: dict[str, dict[str, Shape]], all8: dict[str, object] | None) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True); outputs = []
    def render(name, title, subtitle, objects, camera=(42, -58, 30), transparent=None,
               wireframes=None, world_lines=None, fit_points=None):
        path = RENDER / name
        raster_scene(path, objects, title, subtitle, FOOTER, camera_offset=camera,
                     transparent_objects=transparent or [], wireframes=wireframes or [],
                     world_lines=world_lines or [], fit_points=fit_points)
        outputs.append(relative(path))
    overview = []
    for button, edges in TARGETS.items():
        overview.append((safe_triangles(Compound(children=list(detailed_world[button].values()))), COL["body"]))
        for edge in edges:
            overview.append((safe_triangles(world[button][f"leg_{edge}"]),
                             COL["rescued"] if results[button]["legResults"][edge]["result"] == "RESCUED" else COL["fail"]))
    render("01_all7_unresolved_locations_overview.png", "1 / ALL 7 DOCS/90 UNRESOLVED LOCATIONS",
           "green=rescued straight leg; red=no valid side-region landing", overview, camera=(100, -140, 85))
    number = 2
    for button in FAIL_BUTTONS:
        row = results[button]; color = COL["rescued"] if row["newResult"].startswith("RESCUED") else COL["fail"]
        detail = Compound(children=list(detailed_world[button].values()))
        fit = safe_triangles(detail).reshape(-1, 3)
        render(f"0{number}_{button.lower()}_rescue_geometry.png", f"{number} / {button} RESCUE GEOMETRY",
               f"{row['newResult']} | max tilt={row['maximumTiltDeg'] if row['maximumTiltDeg'] is not None else 'N/A'}",
               [(safe_triangles(world[button]["harness"]), color), (safe_triangles(detail), COL["body"]),
                (safe_triangles(world[button]["slots"]), COL["slot"])], camera=(32, -44, 23), fit_points=fit,
               transparent=[(safe_triangles(world[button]["shellCrop"]), (*COL["shell"], 48))])
        number += 1
    rescued = [name for name in FAIL_BUTTONS if results[name]["newResult"].startswith("RESCUED")]
    if rescued:
        tight = min(rescued, key=lambda name: float(results[name]["minimumClearanceMm"]))
        render("06_tightest_rescued_clearance.png", "6 / TIGHTEST RESCUED CLEARANCE",
               f"{tight} minimum={results[tight]['minimumClearanceMm']:.6f} mm",
               [(safe_triangles(world[tight]["harness"]), COL["hardening"]),
                (safe_triangles(Compound(children=list(detailed_world[tight].values()))), COL["body"])],
               camera=(30, -42, 22))
        worst = min(((name, edge) for name in rescued for edge in TARGETS[name]
                     if results[name]["legResults"][edge]["result"] == "RESCUED"),
                    key=lambda item: float(results[item[0]]["legs"][item[1]]["minimumRemainingShellMm"]))
        name, edge = worst
        render("07_worst_shell_landing.png", "7 / WORST RESCUED SHELL LANDING",
               f"{name} {edge} remaining shell={results[name]['legs'][edge]['minimumRemainingShellMm']:.6f} mm",
               [(safe_triangles(world[name][f"leg_{edge}"]), COL["rescued"]),
                (safe_triangles(world[name][f"slot_{edge}"]), COL["slot"])], camera=(28, -39, 21),
               transparent=[(safe_triangles(world[name]["shellCrop"]), (*COL["shell"], 52))])
    if all8 is not None and all8["result"] == "PASS":
        render("08_all8_complete_interior_overview.png", "8 / ALL-8 COMPLETE INTERIOR OVERVIEW",
               f"all harnesses complete | max unintended penetration={all8['maximumPairPenetrationMm3']:.9f} mm³",
               [(safe_triangles(world[name]["harness"]), COL["frozen"] if name in ("I2","N1","M3","M4") else COL["rescued"])
                for name in d90.BUTTONS], camera=(-110, 150, -80),
               wireframes=[(safe_edge_lines(world["I2"]["shellOwnerFull"]), (*COL["shell"], 100))])
    return outputs


def report_text(data: dict[str, object]) -> str:
    leg_lines = []
    for button, edges in TARGETS.items():
        for edge in edges:
            row = data["buttons"][button]["legs"].get(edge)
            result = data["buttons"][button]["legResults"][edge]["result"]
            if row is None:
                leg_lines.append(f"| {button} | {edge} | unresolved ≤30° | N/A | N/A | N/A | NO | N/A | {result} |")
            else:
                leg_lines.append(f"| {button} | {edge} | unresolved ≤30° | {row['rootShiftMagnitudeMm']:.3f} mm | "
                                 f"{row['shellTargetShiftMagnitudeMm']:.3f} mm | {row['tiltFromWDeg']:.3f}° | "
                                 f"YES / {row['fullSlotFootprintSupportPercent']:.0f}% | {row['minimumRemainingShellMm']:.6f} | {result} |")
    button_lines = []
    for button in FAIL_BUTTONS:
        row = data["buttons"][button]
        button_lines.append(f"| {button} | FAIL | {row['newResult']} | "
                            f"{('N/A' if row['maximumTiltDeg'] is None else format(row['maximumTiltDeg'], '.3f')+'°')} | "
                            f"{('N/A' if row['minimumClearanceMm'] is None else format(row['minimumClearanceMm'], '.6f'))} | "
                            f"{('N/A' if row['minimumShellMm'] is None else format(row['minimumShellMm'], '.6f'))} | "
                            f"{row['rearAssembly']['result']} |")
    failure_lines = []
    for button, edges in TARGETS.items():
        for edge in edges:
            search = data["buttons"][button]["search"][edge]
            if search["result"] == "RESCUED":
                continue
            best = search.get("bestFailure")
            coverage = "N/A" if best is None else f"{best.get('footprintPairCoverage', 0)}/9"
            failure = "NO_SHELL_TARGET" if best is None else str(best.get("failure"))
            remaining = ("N/A" if best is None or best.get("minimumRemainingShellMm") is None
                         else f"{float(best['minimumRemainingShellMm']):.6f}")
            failure_lines.append(f"| {button} | {edge} | {search['targetMapCount']} | "
                                 f"{search['exactEvaluationsLe30']} | {search['exactEvaluations31To45']} | "
                                 f"{coverage} | {failure} | {remaining} |")
    renders = "\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    s = data["summary"]
    return f"""# 91 — 7-unresolved-leg root / shell-target placement rescue audit

MODE = **LOCAL 7-LEG RESCUE / DOCS90 RESOLVED LEGS FROZEN / PRODUCTION 0**

## Required unresolved-leg table

| Button | Leg | docs/90 status | Root shift | Shell-target shift | Final tilt | Full footprint | Min shell | Result |
|---|---|---|---:|---:|---:|---|---:|---|
{chr(10).join(leg_lines)}

## Required button summary

| Button | docs/90 | New result | Max tilt | Min clearance | Min shell | Rear assembly |
|---|---|---|---:|---:|---:|---|
{chr(10).join(button_lines)}

## Numeric result

- RESCUED LEGS = **{s['rescuedLegs']}/7**
- STILL UNRESOLVED = **{s['stillUnresolved']}/7**
- rescued buttons = **{s['rescuedButtons']}/4**
- legs requiring >30° = **{s['legsOver30Deg']}**
- maximum selected tilt = **{('N/A' if s['maximumSelectedTiltDeg'] is None else format(s['maximumSelectedTiltDeg'], '.3f')+'°')}**
- corner-post solutions = **0**
- shell/exterior redesigns = **0**
- bounded exact candidate evaluations = **{s['exactCandidateEvaluations']}**, global optimizer = **NO**

## Unresolved failure evidence

| Button | leg | shell targets | exact ≤30° | exact 30–45° | best footprint | limiting reason | best remaining shell |
|---|---|---:|---:|---:|---:|---|---:|
{chr(10).join(failure_lines)}

## Search policy and structural proof

Every target starts from an exact-W shell material map on its assigned side. Reported shell-target shift is the
local UV displacement from the final root's straight-W projection to the selected slot floor. Root tangent shift is bounded to
±0.40 mm, leaving shared cross width ≥1.20 mm. Endpoint tangent coordinate is bounded to ±3.00 mm and the
radial coordinate remains on the assigned side; no candidate uses a corner-only root. Candidates ≤30° are
exhausted first. Only unresolved legs enter the 30–45° diagnostic band.

Final candidates use the original 3,530-facet PushBtn body/T1–T4/corner/bottom authority and the measured
D3.35×2.44 actuator. A rescue requires 9/9 footprint support, remaining shell ≥1.20 mm, one fused valid solid,
STEP reimport=1 solid, root neck/effective FDM section ≥1.20 mm, positive volumetric roots and 5-state rear
assembly PASS. Existing docs/90 resolved legs are reconstructed from their frozen root/floor/direction data.

## ALL-8 status

ALL-8 COMPLETE HARNESS SET AVAILABLE = **{'YES' if data['all8CompleteHarnessSetAvailable'] else 'NO'}**.
{('ALL-8 exact simultaneous result = **'+data['all8Simultaneous']['result']+'**, closest pair '+data['all8Simultaneous']['closestPair']+', minimum '+format(data['all8Simultaneous']['minimumPairClearanceMm'], '.6f')+' mm, max penetration '+format(data['all8Simultaneous']['maximumPairPenetrationMm3'], '.9f')+' mm³.' if data['all8Simultaneous'] else 'The ALL-8 build gate was not opened because at least one FAIL button remained unresolved.')}

M3–M4 0.032405 mm was not optimized. New candidates were checked only for added penetration against frozen
neighbor harnesses.

## Renders / outputs / freeze

{renders}

- `{data['outputs']['json']}`
{chr(10).join('- `'+data['buttons'][name]['auditHarnessStep']+'`' for name in FAIL_BUTTONS if data['buttons'][name].get('auditHarnessStep'))}
{('- `'+data['outputs']['all8HarnessStep']+'`' if data['outputs'].get('all8HarnessStep') else '')}

production modification=0; frozen shell modification=0; button pose modification=0; I2 authority modification=0;
physical coupon=0. Protected docs/90 and prior authority hashes preserved: **{data['preservation']['allProtectedFilesPreserved']}**.
STOP after rescue classification.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); RENDER.mkdir(parents=True, exist_ok=True)
    protected = protected_files(); before = doc84.hashes(protected)
    d90_data = json.loads(DOC90_JSON.read_text(encoding="utf-8"))
    datums = load_all_datums(); placements = {name: doc84.doc83.datum_location(datums[name], FROZEN_FRONT_DEPTHS[name]) for name in d90.BUTTONS}
    shell_full = {owner: import_step(path) for owner, path in SHELL_STEP.items()}
    rays = {owner: ExactRaySampler(shape) for owner, shape in shell_full.items()}
    original, body, terminals, corners, _old_act, actuator, _hybrid = doc84.detailed_switch_parts()
    local_parts = {"BODY": body, "ACTUATOR": actuator, **terminals}
    mechanism_source = pusher_system(); mechanism = {"PUSHER": mechanism_source["pusher"],
        "GUIDE": mechanism_source["guide"], "HARD_STOP": mechanism_source["stop"], "CLIP": mechanism_source["clip"]}
    detailed_world = {name: {part: placements[name] * shape for part, shape in local_parts.items()} for name in d90.BUTTONS}

    results = {}; candidates = {}; shells = {}; exact_total = 0
    for button in FAIL_BUTTONS:
        print(f"rescue {button}", flush=True)
        datum = datums[button]; front = float(FROZEN_FRONT_DEPTHS[button]); placement = placements[button]
        rows = {}; leg_results = {}; searches = {}
        for edge in EDGES:
            if edge not in TARGETS[button]:
                rows[edge] = reconstruct_row(d90_data["buttons"][button]["legs"][edge], edge)
                leg_results[edge] = {"result": "FROZEN DOCS/90 RESOLVED"}
                continue
            rescued, search = rescue_leg(button, edge, datum, front, rays[datum.owner], local_parts,
                                          corners, mechanism["PUSHER"], placement, detailed_world)
            searches[edge] = search
            exact_total += int(search["exactEvaluationsLe30"]) + int(search["exactEvaluations31To45"])
            if rescued is None:
                leg_results[edge] = {"result": str(search["result"])}
                print(f"  {edge}: FAIL targets={search['targetMapCount']} eval={search['exactEvaluationsLe30']}+{search['exactEvaluations31To45']}", flush=True)
            else:
                rows[edge] = rescued; leg_results[edge] = {"result": "RESCUED"}
                print(f"  {edge}: RESCUED tilt={rescued['tiltFromWDeg']:.3f} root={rescued['rootShiftMagnitudeMm']:.3f} target={rescued['shellTargetShiftMagnitudeMm']:.3f}", flush=True)
        if len(rows) < 4:
            results[button] = {"docs90": "FAIL", "newResult": "FAIL — NO USABLE SIDE-REGION SHELL LANDING",
                "legs": {edge: d90.serial_row(rows[edge]) for edge in rows}, "legResults": leg_results,
                "search": searches, "maximumTiltDeg": None, "minimumClearanceMm": None,
                "minimumShellMm": None, "rearAssembly": {"result": "NOT RUN — INCOMPLETE FOUR-LEG SET"},
                "manufacturing": {"result": "NOT RUN"}}
            continue
        candidate = d90.build_candidate(button, rows)
        shell = d90.make_slotted_shell(candidate, shell_full[datum.owner], placement, button)
        metrics = d90.candidate_metrics(candidate, shell, local_parts, corners, mechanism["PUSHER"],
                                        placement, detailed_world, button)
        rear = d90.rear_check(candidate, shell, local_parts, corners, mechanism)
        step_path = OUT / f"{button}_RESCUED_FOUR_EDGE_HARNESS_AUDIT_ONLY.step"
        gate = manufacturing_gate(button, candidate, shell, step_path, rear)
        min_clear = float(metrics["minimumThreeWayClearanceMm"])
        result = "RESCUED — HARDENING REQUIRED" if min_clear < .15 else "RESCUED"
        if gate["result"] != "PASS": result = "FAIL — STRUCTURAL / ASSEMBLY LIMIT"
        results[button] = {"docs90": "FAIL", "newResult": result,
            "legs": {edge: d90.serial_row(rows[edge]) for edge in EDGES}, "legResults": leg_results,
            "search": searches, "maximumTiltDeg": max(float(rows[e]["tiltFromWDeg"]) for e in EDGES),
            "minimumClearanceMm": min_clear, "minimumShellMm": float(metrics["minimumRemainingShellMm"]),
            "static": {key: value for key, value in metrics.items() if key != "shellUnintended"},
            "rearAssembly": rear, "manufacturing": gate, "auditHarnessStep": relative(step_path)}
        candidates[button] = candidate; shells[button] = shell

    frozen_world = world_frozen_harnesses(d90_data, placements)
    rescue_world = {name: placements[name] * candidates[name]["harness"] for name in candidates}
    combined_world = {**frozen_world, **rescue_world}
    for name in candidates:
        neighbor = nearest_harness_metrics(name, rescue_world[name], combined_world)
        results[name]["nearestNeighborHarness"] = neighbor
        if neighbor["penetrationMm3"] > EPS:
            results[name]["newResult"] = "FAIL — STRUCTURAL / ASSEMBLY LIMIT"
        elif neighbor["minimumDistanceMm"] < .15 and results[name]["newResult"] == "RESCUED":
            results[name]["newResult"] = "RESCUED — HARDENING REQUIRED"

    all_rescued = all(results[name]["newResult"].startswith("RESCUED") for name in FAIL_BUTTONS)
    all8 = None; world = {}
    # World render records: complete candidates when available, otherwise resolved legs + red markers.
    for name in d90.BUTTONS:
        if name in candidates:
            candidate = candidates[name]; shell = shells[name]
            world[name] = {"harness": placements[name] * candidate["harness"],
                           "slots": placements[name] * candidate["slots"],
                           "shellCrop": placements[name] * shell["crop"],
                           "shellOwnerFull": shell_full[datums[name].owner]}
            for edge in EDGES:
                world[name][f"leg_{edge}"] = placements[name] * candidate["rows"][edge]["leg"]
                world[name][f"slot_{edge}"] = placements[name] * candidate["rows"][edge]["slotTool"]
        elif name in FAIL_BUTTONS:
            row_shapes = []
            world[name] = {"shellCrop": shell_full[datums[name].owner] & (placements[name] * local_box(24,24,13,0,0,0,"FAIL_CROP")),
                           "shellOwnerFull": shell_full[datums[name].owner]}
            for edge in EDGES:
                if edge in results[name]["legs"]:
                    reconstructed = reconstruct_row(results[name]["legs"][edge], edge)
                    shape = reconstructed["leg"]; slot = reconstructed["slotTool"]
                else:
                    root = d90.base_root(edge, 1.30, 0.0)
                    shape = local_box(.45,.45,.45,float(root[0]),float(root[1]),float(root[2]-.225),"UNRESOLVED")
                    slot = shape
                row_shapes.append(shape); world[name][f"leg_{edge}"] = placements[name] * shape
                world[name][f"slot_{edge}"] = placements[name] * slot
            world[name]["harness"] = placements[name] * Compound(children=row_shapes)
            world[name]["slots"] = placements[name] * Compound(children=[placements[name].inverse()*world[name][f"slot_{e}"] for e in EDGES])
        else:
            local_harness = import_step(doc89.HARNESS_STEP) if name == "I2" else import_step(ROOT / d90_data["buttons"][name]["auditHarnessStep"])
            world[name] = {"harness": placements[name] * local_harness, "slots": placements[name] * local_box(.1,.1,.1,0,0,0,"SLOT_REF"),
                           "shellCrop": shell_full[datums[name].owner] & (placements[name] * local_box(24,24,13,0,0,0,"CROP")),
                           "shellOwnerFull": shell_full[datums[name].owner]}

    if all_rescued:
        all8_world = {}
        for name in d90.BUTTONS:
            all8_world[name] = {"harness": world[name]["harness"], "legs": world[name]["harness"], "slots": world[name]["slots"]}
        all8 = d90.all8_check(all8_world, detailed_world)
        export_step(Compound(children=[world[name]["harness"] for name in d90.BUTTONS]), RESCUED_ALL8_STEP)
        export_step(Compound(children=[world[name]["slots"] for name in d90.BUTTONS]), RESCUED_SLOT_STEP)

    rescued_legs = sum(1 for button, edges in TARGETS.items() for edge in edges if results[button]["legResults"][edge]["result"] == "RESCUED")
    selected_tilts = [float(results[button]["legs"][edge]["tiltFromWDeg"]) for button, edges in TARGETS.items()
                      for edge in edges if edge in results[button]["legs"]]
    over30 = sum(1 for value in selected_tilts if value > 30.0 + 1e-8)
    summary = {"rescuedLegs": rescued_legs, "stillUnresolved": 7-rescued_legs,
        "rescuedButtons": sum(1 for name in FAIL_BUTTONS if results[name]["newResult"].startswith("RESCUED")),
        "legsOver30Deg": over30, "maximumSelectedTiltDeg": max(selected_tilts) if selected_tilts else None,
        "exactCandidateEvaluations": exact_total, "cornerPostSolutions": 0, "shellExteriorRedesigns": 0}
    renders = render_outputs(results, world, detailed_world, all8)
    after = doc84.hashes(protected)
    data = {"schema": "onegrip.7-unresolved-leg-root-shell-target-rescue-audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(), "authority": "docs/90",
        "sourceProof": {"sourceObject": "ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID",
                        "sourceTriangleCount": int(len(original.triangles)), "simplifiedProxyUsed": False,
                        "measuredActuatorDiameterMm": 3.35, "measuredActuatorProjectionMm": 2.44},
        "summary": summary, "buttons": results, "all8CompleteHarnessSetAvailable": all_rescued,
        "all8Simultaneous": all8,
        "scope": {"productionModification": 0, "frozenShellModification": 0, "buttonPoseModification": 0,
                  "I2AuthorityModification": 0, "physicalCoupon": 0, "deepPareto": 0},
        "preservation": {"protectedFileCount": len(protected), "hashesBefore": before, "hashesAfter": after,
                         "allProtectedFilesPreserved": before == after},
        "outputs": {"report": relative(REPORT), "json": relative(JSON_PATH), "renders": renders,
                    **({"all8HarnessStep": relative(RESCUED_ALL8_STEP), "all8SlotStep": relative(RESCUED_SLOT_STEP)} if all_rescued else {})}}
    JSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"summary": summary, "buttons": {name: results[name]["newResult"] for name in FAIL_BUTTONS},
                      "all8Available": all_rescued, "all8": None if all8 is None else all8["result"],
                      "renders": len(renders), "protected": before == after, "report": relative(REPORT)}, indent=2), flush=True)


if __name__ == "__main__": main()
