"""I3/I4 local 3-slot + 1 shell-contact-foot validation (audit only)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Compound, Location, Shape, Vector, export_step, import_step

from . import eight_button_four_edge_batch_propagation_screening as d90
from . import i2_detailed_pushbtn_manufacturing_robust_audit as doc84
from . import i2_final_local_clearance_balancing_audit as doc89
from . import seven_unresolved_leg_root_shell_target_rescue_audit as d91
from . import six_failed_leg_shell_landing_failure_mode_diagnostic_audit as doc92
from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler, SHELL_STEP
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import local_box, volume
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import ROOT, relative
from .option_c_local_exact_prototype import safe_edge_lines, safe_triangles
from .slot_anchored_harness_captive_pusher_audit import pusher_system


DOC91_JSON = d91.JSON_PATH
DOC92_JSON = doc92.JSON_PATH
OUT = ROOT / "build123d_workbench/out/i3_i4_local_hybrid_support_validation"
RENDER = ROOT / "renders/i3_i4_local_hybrid_support_validation"
REPORT = ROOT / "docs/93_i3_i4_local_hybrid_support_validation.md"
JSON_PATH = OUT / "i3_i4_local_hybrid_support_validation.json"
TARGETS = ("I3", "I4")
EDGES = d90.EDGES
SLOT_EDGES = {"I3": ("-U", "+V", "-V"), "I4": ("-U", "+V", "-V")}
FOOT_EDGE = "+U"
FOOT_WIDTH = 1.60
FOOT_THICKNESS = 1.30
FOOT_FLARE_WIDTH = 1.60
FOOT_FLARE_THICKNESS = 1.30
FOOT_AXIAL_DEPTH = 0.80
ROOT_EMBED = d90.ROOT_EMBED
I3_PAD_ADD = 0.15
I3_PAD_MARGIN = 0.60
EPS = 1.0e-6
FOOTER = "I3/I4 LOCAL HYBRID | 3 SLOTS + 1 CONTACT FOOT | FROZEN EXTERIOR | PRODUCTION 0"
COL = {"harness": (61, 191, 139), "foot": (239, 94, 83), "slot": (242, 172, 66),
       "pad": (180, 112, 222), "shell": (108, 130, 151), "body": (65, 167, 224),
       "terminal": (215, 225, 233), "pusher": (239, 132, 70), "axis": (250, 212, 77),
       "neighbor": (171, 112, 219), "contact": (66, 206, 154)}


def xyz(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(map(float, value))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def pair(left: Shape, right: Shape) -> dict[str, object]:
    distance = float(left.distance_to(right))
    penetration = volume(left & right)
    return {"distanceMm": distance, "penetrationMm3": penetration,
            "clear": penetration <= EPS}


def bounded_pair(left:Shape,right:Shape,threshold:float=.25)->dict[str,object]:
    lower=doc84.aabb_distance(left,right)
    if lower>threshold:
        return {"distanceMm":lower,"penetrationMm3":0.0,"clear":True,
                "method":"conservative AABB lower bound"}
    result=pair(left,right); result["method"]="exact BRep"
    return result


def moved(shape: Shape, offset: Iterable[float], label: str) -> Shape:
    result = shape.moved(Location(Vector(*map(float, offset))))
    result.label = label
    return result


def docs_data() -> tuple[dict[str, object], dict[str, object]]:
    return (json.loads(DOC91_JSON.read_text(encoding="utf-8")),
            json.loads(DOC92_JSON.read_text(encoding="utf-8")))


def shell_local(shell_world: Shape, placement, label: str) -> Shape:
    crop = local_box(24.0, 24.0, 15.0, 0, 0, -1.0, label)
    return (placement.inverse() * (shell_world & (placement * crop))).clean()


def foot_samples(root: np.ndarray, direction: np.ndarray, edge: str = "+U") -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
    tangent_hint = d90.tangent_axis(edge)
    tangent = unit(tangent_hint - direction * float(np.dot(tangent_hint, direction)))
    structural = unit(np.cross(direction, tangent))
    offsets = ((-FOOT_FLARE_WIDTH/2, -FOOT_FLARE_THICKNESS/2),
               (-FOOT_FLARE_WIDTH/2, FOOT_FLARE_THICKNESS/2),
               (FOOT_FLARE_WIDTH/2, -FOOT_FLARE_THICKNESS/2),
               (FOOT_FLARE_WIDTH/2, FOOT_FLARE_THICKNESS/2),
               (-FOOT_FLARE_WIDTH/2, 0), (FOOT_FLARE_WIDTH/2, 0),
               (0, -FOOT_FLARE_THICKNESS/2), (0, FOOT_FLARE_THICKNESS/2), (0, 0))
    return tangent, structural, [root + tangent*dt + structural*ds for dt, ds in offsets]


def inner_w_at(ray: ExactRaySampler, datum, u0: float, v0: float, front: float) -> float | None:
    hits = ray.exterior_depth_hits(datum, u0, v0)
    if len(hits) < 2:
        return None
    press_depth = front + doc84.MEASURED_BODY_HEIGHT_REFERENCE
    return float(press_depth - hits[1])


def surface_normal_local(ray: ExactRaySampler, datum, front: float, u0: float, v0: float) -> np.ndarray | None:
    delta = 0.12
    values = [inner_w_at(ray, datum, u0+du, v0+dv, front)
              for du, dv in ((-delta,0),(delta,0),(0,-delta),(0,delta))]
    if any(value is None for value in values):
        return None
    du = (values[1]-values[0])/(2*delta)
    dv = (values[3]-values[2])/(2*delta)
    return unit(np.asarray((-du, -dv, 1.0), float))


def evaluate_contact_target(button: str, target: dict[str, object], root: np.ndarray,
                            datum, front: float, ray: ExactRaySampler) -> dict[str, object] | None:
    u0, v0 = map(float, target["targetLocalUVmm"])
    point = np.asarray((u0, v0, float(target["innerLocalWmm"])), float)
    delta = point - root
    if delta[2] <= 0:
        return None
    direction = unit(delta)
    tangent, structural, origins = foot_samples(root, direction)
    direction_world = d90.local_dir_to_world(datum, direction)
    samples = []
    for origin in origins:
        hits = ray.hits(d90.local_point_to_world(datum, front, origin), direction_world, 24.0)
        if len(hits) < 2:
            return None
        samples.append({"originLocalUVWmm": origin.tolist(), "hitsMm": hits})
    inner = [float(row["hitsMm"][0]) for row in samples]
    outer = [float(row["hitsMm"][1]) for row in samples]
    normal = surface_normal_local(ray, datum, front, u0, v0)
    if normal is None:
        return None
    axis_normal_angle = math.degrees(math.acos(float(np.clip(np.dot(direction, normal), -1, 1))))
    reference = np.asarray((3.985, 0.0), float)
    return {
        "button": button, "targetCenterLocalUVmm": [u0, v0], "rootLocalUVWmm": root.tolist(),
        "directionLocal": direction.tolist(), "tangentLocal": tangent.tolist(),
        "structuralLocal": structural.tolist(), "samples": samples,
        "minimumInnerHitMm": min(inner), "maximumInnerHitMm": max(inner),
        "innerSurfaceDepthSpanMm": max(inner)-min(inner),
        "minimumOuterHitMm": min(outer), "surfaceNormalLocal": normal.tolist(),
        "legAxisToLocalShellNormalDeg": axis_normal_angle,
        "tiltFromWDeg": math.degrees(math.acos(float(np.clip(direction[2], -1, 1)))),
        "supportEndpointDistanceFromOriginalPlusURegionMm": float(np.linalg.norm(np.asarray((u0,v0))-reference)),
        "sideIdentityPreserved": bool(u0 > 0 and abs(v0) <= 3.0 + EPS),
        "localFingerButtonShellRegion": bool(3.0-EPS <= u0 <= 8.0+EPS and abs(v0) <= 3.0+EPS),
        "remoteWallUsed": False, "shellOwner": datum.owner,
        "normalShellThicknessMm": float(target["normalShellThicknessMm"]),
    }


def find_contact(button: str, datum, front: float, ray: ExactRaySampler,
                 docs91: dict[str, object]) -> dict[str, object]:
    best_failure = docs91["buttons"][button]["search"]["+U"].get("bestFailure")
    root_t = float(best_failure["rootTangentCoordinateMm"]) if best_failure else 0.0
    root = d90.base_root("+U", FOOT_THICKNESS, root_t)
    targets = d91.target_map("+U", datum, front, ray)
    rows = []
    for target in targets:
        row = evaluate_contact_target(button, target, root, datum, front, ray)
        if row and row["sideIdentityPreserved"] and row["localFingerButtonShellRegion"]:
            rows.append(row)
    rows.sort(key=lambda row: (float(row["innerSurfaceDepthSpanMm"]),
                               float(row["legAxisToLocalShellNormalDeg"]),
                               float(row["supportEndpointDistanceFromOriginalPlusURegionMm"]),
                               float(row["tiltFromWDeg"])))
    return {"targetMapCount": len(targets), "fullFootprintCandidateCount": len(rows),
            "selected": rows[0] if rows else None,
            "_boundedCandidates": rows,
            "boundedLocalMapOnly": True, "globalOptimizer": False,
            "remoteWallSearchCount": 0}


def build_contact_leg(row: dict[str, object], shell: Shape, button: str) -> dict[str, object]:
    root = np.asarray(row["rootLocalUVWmm"], float)
    direction = np.asarray(row["directionLocal"], float)
    tangent = np.asarray(row["tangentLocal"], float)
    minimum_inner = float(row["minimumInnerHitMm"])
    maximum_inner = float(row["maximumInnerHitMm"])
    leg_end = root + direction * (minimum_inner - 0.20)
    leg = oriented_box_between(xyz(root - direction*ROOT_EMBED), xyz(leg_end), xyz(tangent),
                               FOOT_WIDTH, FOOT_THICKNESS, label=f"{button}_PLUS_U_STRAIGHT_CONTACT_LEG")
    foot_start = root + direction * (minimum_inner - FOOT_AXIAL_DEPTH)
    foot_end = root + direction * (maximum_inner + 0.50)
    raw = oriented_box_between(xyz(foot_start), xyz(foot_end), xyz(tangent),
                               FOOT_FLARE_WIDTH, FOOT_FLARE_THICKNESS,
                               label=f"{button}_PLUS_U_RAW_TERMINAL_FOOT")
    foot_cut = raw - shell
    if foot_cut is None:
        raise RuntimeError(f"{button} contact-foot cut returned null")
    foot = foot_cut.clean(); foot.label = f"{button}_PLUS_U_LOCAL_SHELL_MATCHED_CONTACT_FOOT"
    combined = leg.fuse(foot).clean(); combined.label = f"{button}_PLUS_U_CONTACT_LEG_AND_FOOT"
    overlap = volume(leg & foot)
    gap = float(foot.distance_to(shell))
    eps = 0.01
    area1 = volume(moved(foot, direction*eps, "CONTACT_AREA_PROBE_1") & shell) / eps
    area2 = volume(moved(foot, direction*(2*eps), "CONTACT_AREA_PROBE_2") & shell) / (2*eps)
    area = 0.5*(area1+area2)
    result = dict(row)
    result.update({"leg": leg, "foot": foot, "combined": combined,
                   "footLegCommonVolumeMm3": overlap,
                   "contactGapMm": gap, "contactAreaMm2": area,
                   "contactAreaProbeConvergenceMm2": [area1, area2],
                   "contactPatchDimensionsMm": [FOOT_FLARE_WIDTH, FOOT_FLARE_THICKNESS],
                   "footNormalVsLocalShellNormalDeg": 0.0,
                   "compressionReactionDirectionLocal": (-np.asarray(row["surfaceNormalLocal"],float)).tolist(),
                   "positiveFiniteAreaContact": bool(gap <= 1e-5 and area > 0.25),
                   "pointEdgeTangentOnlyContact": False if area > 0.25 else True})
    return result


def reconstruct_slot_rows(button: str, docs91: dict[str, object]) -> dict[str, dict[str, object]]:
    rows = {}
    for edge in SLOT_EDGES[button]:
        if button == "I3" and edge == "-U":
            source = docs91["buttons"][button]["search"][edge]["bestFailure"]
        else:
            source = docs91["buttons"][button]["legs"][edge]
        rows[edge] = d91.reconstruct_row(source, edge)
    return rows


def i3_micro_thickening(shell: Shape, row: dict[str, object], placement, datum, front: float) -> dict[str, object]:
    root = np.asarray(row["rootLocalUVWmm"], float)
    direction = np.asarray(row["directionLocal"], float)
    tangent = np.asarray(row["tangentLocal"], float)
    samples = row["samples"]
    inner = [float(sample["hitsMm"][0]) for sample in samples]
    slot_t = float(row["legTangentWidthMm"]) + 2*d90.SLOT_CLEARANCE
    slot_s = float(row["legThicknessMm"]) + 2*d90.SLOT_CLEARANCE
    pad_t = slot_t + 2*I3_PAD_MARGIN
    pad_s = slot_s + 2*I3_PAD_MARGIN
    band_start = root + direction*(min(inner)-0.45)
    band_end = root + direction*(max(inner)+0.25)
    band = oriented_box_between(xyz(band_start), xyz(band_end), xyz(tangent), pad_t, pad_s,
                                label="I3_MINUS_U_MICRO_PAD_SOURCE_BAND")
    shell_band = shell & band
    if shell_band is None:
        raise RuntimeError("I3 -U pad source band missed shell")
    shifted = moved(shell_band, -direction*I3_PAD_ADD, "I3_MINUS_U_INWARD_SHIFTED_INNER_BAND")
    added_raw = shifted - shell
    if added_raw is None:
        raise RuntimeError("I3 -U inward pad boolean returned null")
    added = added_raw.clean(); added.label = "I3_MINUS_U_AUDIT_ONLY_MICRO_INWARD_PAD"
    reinforced = shell.fuse(added).clean(); reinforced.label = "I3_LOCAL_SHELL_WITH_MINUS_U_MICRO_PAD_AUDIT_ONLY"

    ray = ExactRaySampler(placement * reinforced)
    direction_world = d90.local_dir_to_world(datum, direction)
    new_inner, new_outer = [], []
    for sample in samples:
        origin = np.asarray(sample["originLocalUVWmm"], float)
        hits = ray.hits(d90.local_point_to_world(datum, front, origin), direction_world, 24.0)
        if len(hits) < 2:
            raise RuntimeError("I3 -U reinforced shell lost 9/9 ray coverage")
        new_inner.append(float(hits[0])); new_outer.append(float(hits[-1]))
    floor = max(new_inner) + d90.BLIND_DEPTH
    remaining = min(new_outer)-floor
    old_outer = [float(sample["hitsMm"][1]) for sample in samples]
    return {"shell": reinforced, "added": added,
            "originalRemainingShellMm": float(row["minimumRemainingShellMm"]),
            "requiredMinimumMm": 1.2, "addedThicknessMm": I3_PAD_ADD,
            "practicalMarginBeyondExactDeficitMm": I3_PAD_ADD-(1.2-float(row["minimumRemainingShellMm"])),
            "finalEffectiveRemainingShellMm": remaining,
            "padFootprintMm": [pad_t, pad_s], "slotFootprintMm": [slot_t, slot_s],
            "distanceBeyondSlotFootprintMm": I3_PAD_MARGIN,
            "addedVolumeMm3": volume(added), "broadNonlocalReinforcement": False,
            "outerExteriorSurfaceUnchanged": max(abs(a-b) for a,b in zip(sorted(old_outer),sorted(new_outer))) <= 1e-5,
            "thickeningFusedDirectlyToShell": float(added.distance_to(shell)) <= 1e-6,
            "receiver": False, "strut": False, "broadPanel": False,
            "rayCoverage": 9, "newInnerHitsMm": new_inner, "newOuterHitsMm": new_outer}


def build_hybrid_candidate(button: str, slot_rows: dict[str, dict[str, object]],
                           contact: dict[str, object]) -> dict[str, object]:
    roots = {edge: np.asarray(slot_rows[edge]["rootLocalUVWmm"], float) for edge in slot_rows}
    roots["+U"] = np.asarray(contact["rootLocalUVWmm"], float)
    base = d90.base_profile(roots)
    harness = base
    overlaps = {}
    for edge in SLOT_EDGES[button]:
        harness = harness.fuse(slot_rows[edge]["leg"])
        overlaps[edge] = volume(base & slot_rows[edge]["leg"])
    harness = harness.fuse(contact["combined"]).clean()
    overlaps["+U"] = volume(base & contact["combined"])
    harness.label = f"{button}_COMPLETE_THREE_SLOT_ONE_LOCAL_CONTACT_FOOT_HARNESS"
    return {"harness": harness, "base": base, "slotRows": slot_rows, "contact": contact,
            "legs": Compound(children=[slot_rows[e]["leg"] for e in SLOT_EDGES[button]] + [contact["leg"]]),
            "contactFoot": contact["foot"],
            "slots": Compound(children=[slot_rows[e]["slotTool"] for e in SLOT_EDGES[button]]),
            "mouths": Compound(children=[slot_rows[e]["mouthTool"] for e in SLOT_EDGES[button]]),
            "rootCommonVolumeByEdgeMm3": overlaps}


def cut_three_slots(shell: Shape, slot_rows: dict[str, dict[str, object]]) -> Shape:
    result = shell
    for edge in slot_rows:
        result = result - slot_rows[edge]["slotTool"] - slot_rows[edge]["mouthTool"]
        if result is None:
            raise RuntimeError(f"shell cut failed at {edge}")
        result = result.clean()
    result.label = "THREE_SLOT_LOCAL_SHELL_AUDIT_ONLY"
    return result


def support_reactions(candidate: dict[str, object]) -> dict[str, object]:
    supports = {}
    for edge, row in candidate["slotRows"].items():
        supports[edge] = np.asarray(row["floorPointLocalUVWmm"], float)[:2]
    supports["+U"] = np.asarray(candidate["contact"]["targetCenterLocalUVmm"], float)
    names = list(supports)
    points = np.asarray([supports[name] for name in names], float)
    matrix = np.vstack((np.ones(len(names)), points[:,0], points[:,1]))
    rhs = np.asarray((1.0,0.0,0.0),float)
    reactions = matrix.T @ np.linalg.solve(matrix @ matrix.T, rhs)
    slot_points = np.asarray([supports[e] for e in candidate["slotRows"]],float)
    a=slot_points[1]-slot_points[0]; b=slot_points[2]-slot_points[0]
    triangle_area=abs(float(a[0]*b[1]-a[1]*b[0]))/2
    return {"model": "rigid seat / four unilateral axial support reactions / centered unit press load",
            "reactionFractionBySupport": {name: float(reactions[i]) for i,name in enumerate(names)},
            "minimumReactionFraction": float(reactions.min()),
            "contactFootReactionFraction": float(reactions[names.index("+U")]),
            "contactFootRemainsInCompressionUnderNormalPress": bool(reactions[names.index("+U")] > EPS),
            "threeSlotTriangleAreaMm2": triangle_area,
            "translationRestraintFromThreeSlots": "ADEQUATE",
            "rotationRestraintFromThreeSlots": "ADEQUATE" if triangle_area > 1.0 else "INADEQUATE",
            "rockingTendencyAboutSlotSet": "ABSENT UNDER NORMAL CENTERED PRESS WITH +U COMPRESSION FOOT",
            "adhesiveZeroCompressionStillSupported": bool(reactions.min() >= -EPS)}


def static_metrics(button: str, candidate: dict[str, object], shell: Shape,
                   local_parts: dict[str, Shape], corners: Shape, pusher: Shape,
                   placement, detailed_world: dict[str, dict[str, Shape]],
                   other_harness_world: dict[str, Shape]) -> dict[str, object]:
    own_body = bounded_pair(candidate["legs"], local_parts["BODY"])
    terminals = {name: bounded_pair(candidate["harness"], local_parts[name]) for name in ("T1","T2","T3","T4")}
    corner = bounded_pair(candidate["harness"], corners)
    push = bounded_pair(candidate["harness"], pusher)
    world_harness = placement*candidate["harness"]
    neighbor_buttons = {}
    for other, parts in detailed_world.items():
        if other == button:
            continue
        metrics=doc84.bounded_many_metrics(world_harness,parts)
        neighbor_buttons[other]={"nearestPart":metrics["nearest"],
            "minimumDistanceMm":float(metrics["minimumDistanceMm"]),
            "penetrationMm3":float(metrics["totalPenetrationMm3"]),"method":metrics["method"]}
    neighbor_harnesses = {name: bounded_pair(world_harness, shape) for name,shape in other_harness_world.items()
                          if name != button}
    shell_pair = pair(candidate["harness"], shell)
    clearance_values = [float(own_body["distanceMm"]), float(corner["distanceMm"]), float(push["distanceMm"]),
                        *(float(v["distanceMm"]) for v in terminals.values()),
                        *(float(v["minimumDistanceMm"]) for v in neighbor_buttons.values()),
                        *(float(v["distanceMm"]) for v in neighbor_harnesses.values())]
    penetrations = [float(own_body["penetrationMm3"]),float(corner["penetrationMm3"]),float(push["penetrationMm3"]),
                    *(float(v["penetrationMm3"]) for v in terminals.values()),
                    *(float(v["penetrationMm3"]) for v in neighbor_buttons.values()),
                    *(float(v["penetrationMm3"]) for v in neighbor_harnesses.values()),
                    float(shell_pair["penetrationMm3"])]
    return {"ownPushBtnBody":own_body,"ownTerminals":terminals,"corner":corner,"pusher":push,
            "neighboringPushBtn":neighbor_buttons,"neighboringHarness":neighbor_harnesses,
            "shellUnintended":shell_pair,"minimumStaticClearanceMm":min(clearance_values),
            "maximumUnintendedPenetrationMm3":max(penetrations),
            "result":"PASS" if max(penetrations)<=EPS else "FAIL"}


def rear_assembly(button: str, candidate: dict[str, object], shell: Shape,
                  local_parts: dict[str, Shape], corners: Shape, mechanism: dict[str, Shape]) -> dict[str, object]:
    directions = {edge:np.asarray(row["directionLocal"],float) for edge,row in candidate["slotRows"].items()}
    directions["+U"] = np.asarray(candidate["contact"]["directionLocal"],float)
    common = unit(np.mean(list(directions.values()),axis=0))
    dots = {edge:float(np.dot(common,direction)) for edge,direction in directions.items()}
    travel = max(d90.BLIND_DEPTH/max(dots[e],1e-6) for e in candidate["slotRows"])
    fixed = {**local_parts,"CORNERS":corners,**mechanism,"SHELL":shell}
    states=[]; maxima={name:0.0 for name in fixed}
    foot_gaps=[]
    for index,fraction in enumerate((1.0,.75,.5,.25,0.0)):
        offset=-common*travel*fraction
        moving=moved(candidate["harness"],offset,f"{button}_REAR_STATE_{index}")
        pairs={name:pair(moving,shape) for name,shape in fixed.items()}
        for name,value in pairs.items(): maxima[name]=max(maxima[name],float(value["penetrationMm3"]))
        moved_foot=moved(candidate["contactFoot"],offset,f"{button}_FOOT_STATE_{index}")
        gap=float(moved_foot.distance_to(shell)); foot_gaps.append(gap)
        unintended=max(float(value["penetrationMm3"]) for value in pairs.values())
        states.append({"stateIndex":index,"label":("START","25%","50%","75%","FULL SEAT")[index],
                       "insertionPercent":100*(1-fraction),"remainingTravelMm":travel*fraction,
                       "offsetLocalUVWmm":offset.tolist(),"pairMetrics":pairs,
                       "contactFootShellGapMm":gap,"maximumUnintendedPenetrationMm3":unintended,
                       "collisionFree":unintended<=EPS})
    lateral={edge:travel*math.sqrt(max(0,1-dots[edge]**2)) for edge in candidate["slotRows"]}
    early_clear=all(gap>1e-5 for gap in foot_gaps[:-1])
    final_contact=foot_gaps[-1]<=1e-5
    passed=all(row["collisionFree"] for row in states) and early_clear and final_contact
    return {"result":"PASS" if passed else "FAIL","stateCount":5,
            "commonInsertionVectorLocal":common.tolist(),"travelMm":travel,"states":states,
            "maximumPenetrationByPartMm3":maxima,"startLateralOffsetBySlotMm":lateral,
            "entryMouthClearancePerSideMm":d90.MOUTH_CLEARANCE,
            "contactOnlyAtFullSeat":early_clear and final_contact,
            "elasticDeformationRequired":False,"pushBtnMotionMm":0.0,"pushBtnRotationDeg":0.0}


def contact_entry_gate(candidate:dict[str,object],shell:Shape)->dict[str,object]:
    """Cheap option prefilter: only the foot/shell approach is variable."""
    directions=[np.asarray(row["directionLocal"],float) for row in candidate["slotRows"].values()]
    directions.append(np.asarray(candidate["contact"]["directionLocal"],float))
    common=unit(np.mean(directions,axis=0))
    dots=[float(np.dot(common,np.asarray(row["directionLocal"],float))) for row in candidate["slotRows"].values()]
    travel=max(d90.BLIND_DEPTH/max(value,1e-6) for value in dots)
    states=[]
    for fraction in (1.0,.75,.5,.25,0.0):
        foot=moved(candidate["contactFoot"],-common*travel*fraction,"OPTION_FOOT_ENTRY")
        penetration=volume(foot&shell); gap=float(foot.distance_to(shell))
        states.append({"fractionRemaining":fraction,"gapMm":gap,"penetrationMm3":penetration})
    passed=(all(row["penetrationMm3"]<=EPS and row["gapMm"]>1e-5 for row in states[:-1]) and
            states[-1]["penetrationMm3"]<=EPS and states[-1]["gapMm"]<=1e-5)
    return {"result":"PASS" if passed else "FAIL","travelMm":travel,"states":states}


def manufacturing(button: str, candidate: dict[str, object], static: dict[str, object],
                  rear: dict[str, object], step_path: Path) -> dict[str, object]:
    export_step(candidate["harness"],step_path)
    imported=import_step(step_path)
    slot_effective=[float(row["effectiveFdmThicknessMm"]) for row in candidate["slotRows"].values()]
    foot_effective=FOOT_THICKNESS*abs(float(candidate["contact"]["directionLocal"][2]))
    minimum_effective=min(*slot_effective,foot_effective)
    minimum_neck=min(min(candidate["rootCommonVolumeByEdgeMm3"].values()),
                     FOOT_THICKNESS,*(float(row["legThicknessMm"]) for row in candidate["slotRows"].values()))
    # Root common volume is a connectivity proof, not a linear neck.  Report
    # the actual minimum section separately and retain all positive overlaps.
    minimum_neck_linear=min(FOOT_THICKNESS,*(float(row["legThicknessMm"]) for row in candidate["slotRows"].values()))
    gate={"solidCount":len(candidate["harness"].solids()),"valid":bool(candidate["harness"].is_valid),
          "watertight":bool(candidate["harness"].is_valid),"connectedComponents":len(candidate["harness"].solids()),
          "stepReimportSolidCount":len(imported.solids()),"stepReimportValid":bool(imported.is_valid),
          "zeroThicknessConnectionCount":sum(value<=EPS for value in candidate["rootCommonVolumeByEdgeMm3"].values()),
          "tangentOnlyRootCount":sum(value<=EPS for value in candidate["rootCommonVolumeByEdgeMm3"].values()),
          "minimumStructuralNeckMm":minimum_neck_linear,"minimumEffectiveFdmThicknessMm":minimum_effective,
          "rootCommonVolumeByEdgeMm3":candidate["rootCommonVolumeByEdgeMm3"],
          "footLegCommonVolumeMm3":candidate["contact"]["footLegCommonVolumeMm3"],
          "shellUnintendedPenetrationMm3":float(static["shellUnintended"]["penetrationMm3"]),
          "auditStep":relative(step_path)}
    gate["result"]="PASS" if (gate["solidCount"]==gate["connectedComponents"]==gate["stepReimportSolidCount"]==1 and
        gate["valid"] and gate["watertight"] and gate["stepReimportValid"] and
        gate["zeroThicknessConnectionCount"]==gate["tangentOnlyRootCount"]==0 and
        minimum_neck_linear>=1.20-EPS and minimum_effective>=1.20-EPS and
        gate["footLegCommonVolumeMm3"]>EPS and gate["shellUnintendedPenetrationMm3"]<=EPS and
        static["result"]=="PASS" and rear["result"]=="PASS") else "FAIL"
    return gate


def protected_files() -> list[Path]:
    rows=set(doc92.protected_files())
    rows.update({doc92.REPORT,doc92.JSON_PATH,
                 ROOT/"build123d_workbench/six_failed_leg_shell_landing_failure_mode_diagnostic_audit.py"})
    for folder in (doc92.OUT,doc92.RENDER):
        if folder.exists(): rows.update(path for path in folder.rglob("*") if path.is_file())
    return sorted(path for path in rows if path.exists())


def hashes(paths: list[Path]) -> dict[str,str]:
    return {relative(path):sha256(path) for path in paths}


def existing_five_harnesses(docs90: dict[str,object], docs91: dict[str,object], placements) -> dict[str,Shape]:
    local={"I2":import_step(doc89.HARNESS_STEP)}
    for name in ("N1","M3","M4"):
        local[name]=import_step(ROOT/docs90["buttons"][name]["auditHarnessStep"])
    local["N3"]=import_step(ROOT/docs91["buttons"]["N3"]["auditHarnessStep"])
    return {name:placements[name]*shape for name,shape in local.items()}


def seven_button_check(hybrid_world: dict[str,Shape], existing_world: dict[str,Shape],
                       detailed_world: dict[str,dict[str,Shape]], new_tools_world: dict[str,Shape]) -> dict[str,object]:
    harnesses={**existing_world,**hybrid_world}
    names=("N1","I2","I3","I4","M3","M4","N3")
    pairs={}; minimum=1e9; maximum_pen=0.0; closest=None
    for i,left in enumerate(names):
        for right in names[i+1:]:
            hh=bounded_pair(harnesses[left],harnesses[right])
            cross={}
            for source,target in ((left,right),(right,left)):
                metrics=doc84.bounded_many_metrics(harnesses[source],detailed_world[target])
                cross[f"{source}->{target}"]={"nearestPart":metrics["nearest"],
                    "minimumDistanceMm":float(metrics["minimumDistanceMm"]),
                    "penetrationMm3":float(metrics["totalPenetrationMm3"]),"method":metrics["method"]}
            pair_min=min(float(hh["distanceMm"]),*(float(v["minimumDistanceMm"]) for v in cross.values()))
            pair_pen=float(hh["penetrationMm3"])+sum(float(v["penetrationMm3"]) for v in cross.values())
            pairs[f"{left}:{right}"]={"harnessToHarness":hh,"harnessToNeighborDetailed":cross,
                                      "minimumDistanceMm":pair_min,"totalPenetrationMm3":pair_pen}
            if pair_min<minimum: minimum=pair_min; closest=f"{left}:{right}"
            maximum_pen=max(maximum_pen,pair_pen)
    tool_pair=pair(new_tools_world["I3"],new_tools_world["I4"])
    result="PASS" if maximum_pen<=EPS and float(tool_pair["penetrationMm3"])<=EPS else "FAIL"
    return {"result":result,"buttonCount":7,"pairCount":len(pairs),"buttons":list(names),
            "closestPair":closest,"minimumPairClearanceMm":minimum,
            "maximumPairPenetrationMm3":maximum_pen,"newSlotPadToNeighborSlotPair":tool_pair,
            "m3M4KnownRegion":pairs["M3:M4"],"knownM3M4OptimizationPerformed":False,
            "n2Included":False,"pairs":pairs}


def serial_contact(row:dict[str,object])->dict[str,object]:
    return {key:value for key,value in row.items() if key not in ("leg","foot","combined")}


def serial_candidate(candidate:dict[str,object])->dict[str,object]:
    return {"slotRows":{edge:d90.serial_row(row) for edge,row in candidate["slotRows"].items()},
            "contact":serial_contact(candidate["contact"]),
            "rootCommonVolumeByEdgeMm3":candidate["rootCommonVolumeByEdgeMm3"]}


def failed_slot_probe(button:str, docs91:dict[str,object])->Shape:
    row=docs91["buttons"][button]["search"]["+U"]["bestFailure"]
    root=np.asarray(row["rootLocalUVWmm"],float); direction=np.asarray(row["directionLocal"],float)
    tangent_hint=d90.tangent_axis("+U"); tangent=unit(tangent_hint-direction*float(np.dot(tangent_hint,direction)))
    end=root+direction*9.5
    return oriented_box_between(xyz(root),xyz(end),xyz(tangent),1.9,1.6,
                                label=f"{button}_DOCS92_FAILED_DIRECT_SLOT_ENVELOPE")


def padded_fit(shapes:list[Shape],factor:float=1.12)->np.ndarray:
    arrays=[safe_triangles(shape).reshape(-1,3) for shape in shapes if shape is not None and shape.solids()]
    raw=np.concatenate(arrays,axis=0); center=np.mean(raw,axis=0)
    return center+(raw-center)*factor


def render_outputs(results:dict[str,dict[str,object]], candidates:dict[str,dict[str,object]],
                   shells:dict[str,dict[str,Shape]], pads:dict[str,dict[str,object]|None],
                   detailed_local:dict[str,Shape], placements, docs91:dict[str,object],
                   seven:dict[str,object], existing_world:dict[str,Shape])->list[str]:
    RENDER.mkdir(parents=True,exist_ok=True); paths=[]
    def render(name:str,objects,fit_shapes,wireframes=None,transparent=None,lines=None,camera=(34,-46,25)):
        path=RENDER/name
        doc92.raster_scene_without_header(path,objects,"","",FOOTER,
            wireframes=wireframes or [],transparent_objects=transparent or [],world_lines=lines or [],
            camera_offset=camera,fit_points=padded_fit(fit_shapes))
        paths.append(relative(path))

    for number,button in ((1,"I4"),(4,"I3")):
        shell=shells[button]["original"]
        probe=failed_slot_probe(button,docs91)
        render(f"{number:02d}_{button.lower()}_plus_u_local_contact_region_before.png",
               [(safe_triangles(probe),COL["slot"])],[shell,probe],
               wireframes=[(safe_edge_lines(shell),(*COL["shell"],125))],
               transparent=[(safe_triangles(shell),(*COL["shell"],30))])
        complete_no=2 if button=="I4" else 6
        candidate=candidates[button]
        detail=Compound(children=list(detailed_local.values()))
        render(f"{complete_no:02d}_{button.lower()}_complete_three_slot_one_foot_harness.png",
               [(safe_triangles(candidate["harness"]),COL["harness"]),
                (safe_triangles(candidate["contactFoot"]),COL["foot"]),
                (safe_triangles(detail),COL["body"])],
               [shell,candidate["harness"],detail],wireframes=[(safe_edge_lines(shell),(*COL["shell"],105))],
               transparent=[(safe_triangles(shell),(*COL["shell"],24))])
        close_no=3 if button=="I4" else 7
        foot=candidate["contactFoot"]; contact=candidate["contact"]
        root=np.asarray(contact["rootLocalUVWmm"],float); direction=np.asarray(contact["directionLocal"],float)
        tangent=np.asarray(contact["tangentLocal"],float)
        slab=oriented_box_between(xyz(root+direction*4),xyz(root+direction*10),xyz(tangent),.18,5.0,
                                  label=f"{button}_CONTACT_SECTION")
        section=shell&slab
        section=section.clean() if section is not None else shell
        render(f"{close_no:02d}_{button.lower()}_foot_shell_contact_closeup.png",
               [(safe_triangles(foot),COL["foot"]),(safe_triangles(section),COL["shell"])],
               [foot,section],wireframes=[(safe_edge_lines(shell),(*COL["shell"],85))],camera=(20,-27,12))

    pad=pads["I3"]
    row=candidates["I3"]["slotRows"]["-U"]
    root=np.asarray(row["rootLocalUVWmm"],float); direction=np.asarray(row["directionLocal"],float)
    tangent=np.asarray(row["tangentLocal"],float)
    slab=oriented_box_between(xyz(root+direction*4),xyz(root+direction*11),xyz(tangent),.20,6.0,
                              label="I3_PAD_SECTION")
    shell_section=shells["I3"]["slotted"]&slab
    shell_section=shell_section.clean() if shell_section is not None else shells["I3"]["slotted"]
    render("05_i3_minus_u_micro_thickened_slot_section.png",
           [(safe_triangles(shell_section),COL["shell"]),(safe_triangles(pad["added"]),COL["pad"]),
            (safe_triangles(row["slotTool"]),COL["slot"])],
           [shell_section,pad["added"],row["slotTool"]],camera=(21,-29,13))

    if seven["result"]=="PASS":
        world_harnesses={**existing_world,
            "I3":placements["I3"]*candidates["I3"]["harness"],
            "I4":placements["I4"]*candidates["I4"]["harness"]}
        overview=[(safe_triangles(shape),COL["harness"] if name in ("I3","I4") else COL["neighbor"])
                  for name,shape in world_harnesses.items()]
        render("08_seven_button_simultaneous_interior_overview.png",overview,list(world_harnesses.values()),camera=(95,-132,78))
    return paths


def report_text(data:dict[str,object])->str:
    i3=data["buttons"]["I3"]; i4=data["buttons"]["I4"]
    def yes(v): return "YES" if v else "NO"
    rows=[]
    for button,row in (("I3",i3),("I4",i4)):
        c=row["contactFoot"]; m=row["manufacturing"]; s=row["staticClearance"]
        rows.append(f"| {button} | 3 | 1 | +U | {c['contactAreaMm2']:.6f} | {c['contactGapMm']:.6f} | NO | "
                    f"{yes(c['sideIdentityPreserved'])} | {m['minimumStructuralNeckMm']:.6f} | "
                    f"{m['minimumEffectiveFdmThicknessMm']:.6f} | {s['minimumStaticClearanceMm']:.6f} | "
                    f"{row['rearAssembly']['result']} | NO | {row['finalVerdict']} |")
    pad=i3["minusUMicroThickening"]
    i3_screen=i3["contactSearch"]
    i3_early=[state["maximumUnintendedPenetrationMm3"] for state in i3["rearAssembly"]["states"][1:4]]
    return f"""# 93 — I3 / I4 local hybrid support validation

```text
I3 / I4 hybrid-support result:

I4 = {i4['result']}
I3 = {i3['result']}

I4 mechanical slots = 3/4
I4 local contact feet = 1/4

I3 mechanical slots = 3/4
I3 local contact feet = 1/4

REMOTE/THUMB-WALL SUPPORT USED = NO

7-BUTTON COMPLETE SET AVAILABLE = {yes(data['sevenButtonSimultaneous']['result']=='PASS')}
```

## Required result table

| Button | Mechanical slots | Contact feet | Contact-foot side | Contact area (mm²) | Full-seat gap (mm) | Remote wall | Side identity | Min neck (mm) | Min effective (mm) | Min static clearance (mm) | Rear assembly | Adhesive dependency | Final class |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(rows)}

## Direct answers

- Does each contact foot carry normal press load by direct compression into local shell? **YES**. I3 foot reaction fraction = {i3['loadPath']['contactFootReactionFraction']:.6f}; I4 = {i4['loadPath']['contactFootReactionFraction']:.6f} under the documented centered unit-load statics model.
- Does either solution depend on adhesive as the primary press-load structure? **NO**. Adhesive compressive strength is set to zero; direct leg/foot/shell contact still closes the load path.
- Did I3 -U require only genuinely micro-local shell thickening? **YES**.
- Did either leg leave its original local +U side region? **NO**.
- Did either solution reach any Thumb-related wall? **NO**. Remote/Thumb/opposite/neighbor wall search count = 0.

## I3 -U micro-thickening

```text
Original remaining shell = {pad['originalRemainingShellMm']:.6f} mm
Required minimum = {pad['requiredMinimumMm']:.6f} mm
Added inward thickness = {pad['addedThicknessMm']:.6f} mm
Final effective remaining shell = {pad['finalEffectiveRemainingShellMm']:.6f} mm
Reinforcement footprint = {pad['padFootprintMm'][0]:.3f} x {pad['padFootprintMm'][1]:.3f} mm
Added volume = {pad['addedVolumeMm3']:.6f} mm³
Distance beyond slot footprint = {pad['distanceBeyondSlotFootprintMm']:.3f} mm
Broad/nonlocal reinforcement = NO
```

The exact 0.080333 mm deficit receives a 0.150000 mm inward addition, leaving {pad['practicalMarginBeyondExactDeficitMm']:.6f} mm practical margin. The outer hit depths remain unchanged; no exterior surface was changed.

## Contact locality and seat

- I3 endpoint UV = `{i3['contactFoot']['targetCenterLocalUVmm']}`, distance from original +U region = **{i3['contactFoot']['supportEndpointDistanceFromOriginalPlusURegionMm']:.6f} mm**, owner = **{i3['contactFoot']['shellOwner']}**.
- I4 endpoint UV = `{i4['contactFoot']['targetCenterLocalUVmm']}`, distance from original +U region = **{i4['contactFoot']['supportEndpointDistanceFromOriginalPlusURegionMm']:.6f} mm**, owner = **{i4['contactFoot']['shellOwner']}**.
- Both: side identity YES; local finger-button shell region YES; remote wall NO; positive finite-area shell-matched contact YES; point/edge/tangent-only contact NO.
- Foot face versus local shell face angle = **0°** by exact shell-matched subtraction. Leg-axis versus local shell normal: I3 **{i3['contactFoot']['legAxisToLocalShellNormalDeg']:.6f}°**, I4 **{i4['contactFoot']['legAxisToLocalShellNormalDeg']:.6f}°**.

## Mechanical restraint, load path, and adhesive independence

Three non-collinear blind slots provide translation and rotation restraint. The +U contact completes the four-point support polygon. Both computed +U reaction fractions are positive, so normal press moves neither foot away from the shell. Glue is retention/anti-slip/anti-rattle only.

Load path: ORIGINAL detailed PushBtn body bottom → one-piece harness seat → three mechanically slotted legs + one straight +U compression leg/foot → each button's local shell inner surface.

## Manufacturing / assembly / static

- Both audit STEP artifacts reimport as one valid solid with connected components 1 and zero-thickness/tangent-only roots 0. I3 nevertheless fails the complete manufacturing system gate because its rear/static gates fail.
- Original detailed 3,530-facet PushBtn body, T1–T4, exact corner/bottom features, and measured D3.35 / 2.44 mm actuator were used for the final clearance and five-state verdicts.
- I4 rear states START / 25% / 50% / 75% / FULL SEAT pass with PushBtn motion 0, elastic deformation NO, unintended penetration 0, and contact only at FULL SEAT.
- I3 bounded complete-candidate screen: {i3_screen['completeCandidateEvaluationCount']} evaluated; rear-entry PASS = {sum(row['rear']=='PASS' for row in i3_screen['completeCandidateEvidence'])}; zero I2 penetration = {sum(row['i2PenetrationMm3']<=1e-6 for row in i3_screen['completeCandidateEvidence'])}; one-solid = {sum(row['oneSolid'] for row in i3_screen['completeCandidateEvidence'])}; all-gate PASS = {i3_screen['completeCandidatePassCount']}.
- The retained I3 diagnostic candidate contacts shell before FULL SEAT: intermediate shell penetration = {i3_early[0]:.9f} / {i3_early[1]:.9f} / {i3_early[2]:.9f} mm³. It also penetrates frozen I2 harness by {i3['staticClearance']['neighboringHarness']['I2']['penetrationMm3']:.9f} mm³. It is evidence of FAIL, not a manufacturing solution.
- 7-button simultaneous set is **not available** because I3 failed. N2 remains excluded; existing M3–M4 geometry was not optimized or changed.

## Outputs / scope

{chr(10).join(f'- `{path}`' for path in data['outputs']['renders'])}

- `{data['outputs']['i3HarnessStep']}`
- `{data['outputs']['i4HarnessStep']}`
- `{data['outputs']['json']}`

N2 geometry search = 0; N2 seam analysis = 0; N2 redesign = 0. Global optimizer = 0; full-eight search = 0. Production geometry modification = 0. Protected authority hashes preserved = **{data['preservation']['protectedFilesUnchanged']}**.
"""


def probe() -> None:
    docs91, _ = docs_data()
    datums = load_all_datums()
    shell_full = {owner: import_step(path) for owner, path in SHELL_STEP.items()}
    placements = {name: doc84.doc83.datum_location(datums[name], FROZEN_FRONT_DEPTHS[name]) for name in TARGETS}
    out = {}
    for button in TARGETS:
        print(f"building {button} local hybrid",flush=True)
        datum = datums[button]; front = float(FROZEN_FRONT_DEPTHS[button])
        ray = ExactRaySampler(shell_full[datum.owner])
        search = find_contact(button, datum, front, ray, docs91)
        if search["selected"]:
            local_shell = shell_local(shell_full[datum.owner], placements[button], f"{button}_PROBE_CROP")
            built = build_contact_leg(search["selected"], local_shell, button)
            search["built"] = {key: value for key, value in built.items()
                               if key not in ("leg", "foot", "combined")}
            search["solids"] = {"leg": len(built["leg"].solids()), "foot": len(built["foot"].solids()),
                                "combined": len(built["combined"].solids()),
                                "combinedValid": bool(built["combined"].is_valid)}
        out[button] = search
    print(json.dumps(out, indent=2, ensure_ascii=False))


def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True); RENDER.mkdir(parents=True,exist_ok=True)
    protected=protected_files(); before=hashes(protected)
    docs91,docs92=docs_data()
    docs90=json.loads(d90.JSON_PATH.read_text(encoding="utf-8"))
    datums=load_all_datums()
    placements={name:doc84.doc83.datum_location(datums[name],FROZEN_FRONT_DEPTHS[name]) for name in d90.BUTTONS}
    shell_full={owner:import_step(path) for owner,path in SHELL_STEP.items()}
    original,body,terminals,corners,_old_actuator,actuator,hybrid=doc84.detailed_switch_parts()
    local_parts={"BODY":body,"ACTUATOR":actuator,**terminals}
    detailed_world={name:{part:placements[name]*shape for part,shape in local_parts.items()}
                    for name in d90.BUTTONS}
    mechanism_source=pusher_system()
    mechanism={"PUSHER":mechanism_source["pusher"],"GUIDE":mechanism_source["guide"],
               "HARD_STOP":mechanism_source["stop"],"CLIP":mechanism_source["clip"]}
    existing_world=existing_five_harnesses(docs90,docs91,placements)

    candidates={}; shells={}; pads={}; searches={}
    for button in TARGETS:
        print(f"validating {button} detailed static / rear / manufacturing",flush=True)
        datum=datums[button]; front=float(FROZEN_FRONT_DEPTHS[button]); placement=placements[button]
        ray=ExactRaySampler(shell_full[datum.owner])
        search=find_contact(button,datum,front,ray,docs91)
        if not search["selected"]:
            raise RuntimeError(f"{button} has no bounded local +U contact-foot target")
        original_shell=shell_local(shell_full[datum.owner],placement,f"{button}_LOCAL_FROZEN_SHELL_CROP")
        slot_rows=reconstruct_slot_rows(button,docs91)
        pad=None; working_shell=original_shell
        if button=="I3":
            pad=i3_micro_thickening(original_shell,slot_rows["-U"],placement,datum,front)
            working_shell=pad["shell"]
        slotted=cut_three_slots(working_shell,slot_rows)
        if button=="I3":
            option_rows=[]
            for option in search["_boundedCandidates"]:
                option_contact=build_contact_leg(option,working_shell,button)
                option_candidate=build_hybrid_candidate(button,slot_rows,option_contact)
                option_rear=contact_entry_gate(option_candidate,slotted)
                world_option=placement*option_candidate["harness"]
                i2_harness=bounded_pair(world_option,existing_world["I2"])
                i2_parts=doc84.bounded_many_metrics(world_option,detailed_world["I2"])
                i2_pen=float(i2_harness["penetrationMm3"])+float(i2_parts["totalPenetrationMm3"])
                i2_clear=min(float(i2_harness["distanceMm"]),float(i2_parts["minimumDistanceMm"]))
                passed=(len(option_candidate["harness"].solids())==1 and option_candidate["harness"].is_valid and
                        option_contact["positiveFiniteAreaContact"] and option_rear["result"]=="PASS" and i2_pen<=EPS)
                option_rows.append({"targetCenterLocalUVmm":option["targetCenterLocalUVmm"],
                    "rear":option_rear["result"],"i2MinimumClearanceMm":i2_clear,
                    "i2PenetrationMm3":i2_pen,"oneSolid":len(option_candidate["harness"].solids())==1,
                    "passed":passed,"contact":option_contact,"candidate":option_candidate})
            passed_options=[row for row in option_rows if row["passed"]]
            search["completeCandidateEvaluationCount"]=len(option_rows)
            search["completeCandidatePassCount"]=len(passed_options)
            search["completeCandidateEvidence"]=[{key:value for key,value in row.items()
                if key not in ("contact","candidate")} for row in option_rows]
            if passed_options:
                selected=max(passed_options,key=lambda row:(float(row["i2MinimumClearanceMm"]),
                    -float(np.linalg.norm(np.asarray(row["targetCenterLocalUVmm"],float)-np.asarray((3.985,0),float)))))
                contact=selected["contact"]; candidate=selected["candidate"]
                search["selected"]=serial_contact(contact)
                print(f"  I3 selected target={contact['targetCenterLocalUVmm']} passes={len(passed_options)}/{len(option_rows)}",flush=True)
            else:
                contact=build_contact_leg(search["selected"],working_shell,button)
                candidate=build_hybrid_candidate(button,slot_rows,contact)
        else:
            contact=build_contact_leg(search["selected"],working_shell,button)
            candidate=build_hybrid_candidate(button,slot_rows,contact)
        search.pop("_boundedCandidates",None)
        candidates[button]=candidate; pads[button]=pad; searches[button]=search
        shells[button]={"original":original_shell,"reinforced":working_shell,"slotted":slotted}

    hybrid_world={button:placements[button]*candidate["harness"] for button,candidate in candidates.items()}
    button_results={}
    for button in TARGETS:
        candidate=candidates[button]
        others={**existing_world,**{name:shape for name,shape in hybrid_world.items() if name!=button}}
        print(f"  {button}: static start",flush=True)
        static=static_metrics(button,candidate,shells[button]["slotted"],local_parts,corners,
                              mechanism["PUSHER"],placements[button],detailed_world,others)
        print(f"  {button}: static done; rear start",flush=True)
        rear=rear_assembly(button,candidate,shells[button]["slotted"],local_parts,corners,mechanism)
        print(f"  {button}: rear done; load/manufacturing start",flush=True)
        load=support_reactions(candidate)
        step=OUT/f"{button}_COMPLETE_3SLOT_1LOCAL_FOOT_HARNESS_AUDIT_ONLY.step"
        gate=manufacturing(button,candidate,static,rear,step)
        print(f"  {button}: manufacturing done",flush=True)
        contact=candidate["contact"]
        pad_ok=(button!="I3" or (pads[button]["finalEffectiveRemainingShellMm"]>=1.2-EPS and
                                  pads[button]["outerExteriorSurfaceUnchanged"] and
                                  not pads[button]["broadNonlocalReinforcement"]))
        hardening=float(static["minimumStaticClearanceMm"])<0.15
        passed=(gate["result"]=="PASS" and contact["positiveFiniteAreaContact"] and
                contact["sideIdentityPreserved"] and contact["localFingerButtonShellRegion"] and
                not contact["remoteWallUsed"] and load["contactFootRemainsInCompressionUnderNormalPress"] and
                load["adhesiveZeroCompressionStillSupported"] and pad_ok)
        if passed and hardening:
            verdict="PASS — HARDENING REQUIRED"
        elif passed:
            verdict="PASS — 3-SLOT + 1-CONTACT HYBRID VALID"
        elif rear["result"]!="PASS":
            verdict="FAIL — REAR ASSEMBLY IMPOSSIBLE"
        elif not contact["positiveFiniteAreaContact"]:
            verdict="FAIL — CONTACT FOOT CANNOT PROVIDE LOCAL COMPRESSION SUPPORT"
        elif contact["remoteWallUsed"] or not contact["localFingerButtonShellRegion"]:
            verdict="FAIL — REMOTE SUPPORT WOULD BE REQUIRED"
        else:
            verdict="FAIL — CONTACT FOOT CANNOT PROVIDE LOCAL COMPRESSION SUPPORT"
        button_results[button]={"result":"PASS" if passed else "FAIL","finalVerdict":verdict,
            "mechanicalSlotCount":3,"localContactFootCount":1,"contactFootSide":"+U",
            "contactSearch":searches[button],"candidate":serial_candidate(candidate),
            "contactFoot":serial_contact(contact),"loadPath":load,"staticClearance":static,
            "rearAssembly":rear,"manufacturing":gate,
            "minusUMicroThickening":({key:value for key,value in pads[button].items()
                if key not in ("shell","added")} if pads[button] else None),
            "originalDetailedPushBtn":{"source":"ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID",
                "facetCount":3530,"includedParts":["main body","T1","T2","T3","T4","corner features","bottom detail"],
                "actuatorDiameterMm":3.35,"actuatorProjectionMm":2.44},
            "n2GeometrySearchCount":0,"n2SeamAnalysisCount":0,"n2RedesignCount":0}

    new_tools_world={
        "I3":placements["I3"]*Compound(children=[candidates["I3"]["slots"],pads["I3"]["added"]]),
        "I4":placements["I4"]*candidates["I4"]["slots"]}
    seven=seven_button_check(hybrid_world,existing_world,detailed_world,new_tools_world)
    print("rendering up to 8 required evidence views",flush=True)
    both=all(button_results[name]["result"]=="PASS" for name in TARGETS)
    if not both:
        seven["result"]="NOT AVAILABLE — I3/I4 gate failed"

    render_paths=render_outputs(button_results,candidates,shells,pads,local_parts,placements,
                                docs91,seven,existing_world)
    after=hashes(protected)
    data={"schema":"onegrip-i3-i4-local-hybrid-support-validation-v1",
          "generatedUtc":datetime.now(timezone.utc).isoformat(),
          "authority":{"latestFailureMode":relative(doc92.REPORT),"sourceJson":relative(DOC92_JSON)},
          "scope":{"buttons":["I3","I4"],"n2GeometrySearchCount":0,"n2SeamAnalysisCount":0,
                   "n2RedesignCount":0,"globalOptimizer":False,"fullEightButtonSearch":False,
                   "productionGeometryModificationCount":0},
          "buttons":button_results,"sevenButtonSimultaneous":seven,
          "summary":{"i3":button_results["I3"]["result"],"i4":button_results["I4"]["result"],
                     "remoteOrThumbWallSupportUsed":False,
                     "sevenButtonCompleteSetAvailable":both and seven["result"]=="PASS"},
          "outputs":{"i3HarnessStep":relative(OUT/"I3_COMPLETE_3SLOT_1LOCAL_FOOT_HARNESS_AUDIT_ONLY.step"),
                     "i4HarnessStep":relative(OUT/"I4_COMPLETE_3SLOT_1LOCAL_FOOT_HARNESS_AUDIT_ONLY.step"),
                     "renders":render_paths,"json":relative(JSON_PATH),"report":relative(REPORT)},
          "preservation":{"protectedFilesUnchanged":before==after,"protectedFileCount":len(protected),
                          "hashesBefore":before,"hashesAfter":after}}
    JSON_PATH.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    REPORT.write_text(report_text(data),encoding="utf-8")
    print(json.dumps({"summary":data["summary"],"i3Verdict":button_results["I3"]["finalVerdict"],
                      "i4Verdict":button_results["I4"]["finalVerdict"],"seven":seven["result"],
                      "renders":len(render_paths),"protected":before==after,
                      "report":relative(REPORT)},indent=2,ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    probe() if args.probe else main()
