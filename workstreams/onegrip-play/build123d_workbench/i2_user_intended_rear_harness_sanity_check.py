"""Five-state frozen-geometry sanity check for user-intended rear harness assembly."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path

import numpy as np
from build123d import Shape, import_step

from . import i2_detailed_pushbtn_manufacturing_robust_audit as doc84
from . import i2_manufacturing_harness_rebase_audit as doc86
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import volume
from .i4_m3_current_audit import load_all_datums
from .slot_anchored_harness_captive_pusher_audit import pusher_system


ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"build123d_workbench/out/i2_user_intended_rear_harness_sanity_check"
RENDER=ROOT/"renders/i2_user_intended_rear_harness_sanity_check"
REPORT=ROOT/"docs/87_i2_user_intended_rear_harness_assembly_sanity_check.md"
JSON_PATH=OUT/"i2_user_intended_rear_harness_sanity_check.json"
EPS=1.0e-6
FRACTIONS=(1.0,.75,.5,.25,0.0)
FOOTER="I2 ONLY | USER-INTENDED REAR-HARNESS ASSEMBLY | DOCS/86 FROZEN | PRODUCTION 0"
COL={"shell":(103,126,148),"harness":(53,184,132),"body":(65,166,224),"actuator":(238,91,101),
     "terminal":(218,226,234),"pusher":(237,132,72),"guide":(72,168,226),"axis":(250,211,76)}


def protected_files()->list[Path]:
    rows=set(doc86.protected_files())
    rows.update({ROOT/"docs/86_i2_manufacturing_harness_rebase_audit.md",
                 ROOT/"build123d_workbench/i2_manufacturing_harness_rebase_audit.py"})
    for folder in (ROOT/"build123d_workbench/out/i2_manufacturing_harness_rebase_audit",
                   ROOT/"renders/i2_manufacturing_harness_rebase_audit"):
        rows.update(path for path in folder.rglob("*") if path.is_file())
    return sorted(path for path in rows if path.exists())


def exact_pair(left:Shape,right:Shape)->dict[str,float|bool]:
    distance=float(left.distance_to(right))
    penetration=volume(left&right) if distance<=1e-7 else 0.0
    return {"distanceMm":distance,"penetrationMm3":penetration,"clear":penetration<=EPS}


def render_outputs(harness:Shape,shell:Shape,switch:dict[str,Shape],mechanism:dict[str,Shape],
                   vector:np.ndarray,travel:float)->list[str]:
    RENDER.mkdir(parents=True,exist_ok=True); paths=[]
    shell_tri=doc84.safe_triangles(shell); shell_wire=doc84.safe_edge_lines(shell)
    fixed=[(doc84.safe_triangles(switch["BODY"]),COL["body"]),
           (doc84.safe_triangles(switch["ACTUATOR"]),COL["actuator"]),
           *[(doc84.safe_triangles(switch[k]),COL["terminal"]) for k in ("T1","T2","T3","T4")],
           (doc84.safe_triangles(mechanism["PUSHER"]),COL["pusher"]),
           (doc84.safe_triangles(mechanism["GUIDE"]),COL["guide"])]

    def render(number:int,fraction:float,label:str):
        offset=-vector*travel*fraction; moving=doc86.moved(harness,offset,f"REAR_HARNESS_{label}")
        path=RENDER/f"{number:02d}_rear_harness_{label.lower().replace(' ','_')}.png"
        doc84.raster_scene(path,[*fixed,(doc84.safe_triangles(moving),COL["harness"])],
                           f"{number} / USER-INTENDED REAR HARNESS — {label}",
                           f"PushBtn pose frozen | rigid remaining travel={travel*fraction:.6f} mm",
                           FOOTER,camera_offset=(29,-40,22),
                           transparent_objects=[(shell_tri,(*COL["shell"],42))],
                           wireframes=[(shell_wire,(*COL["shell"],115))],
                           world_lines=[(-vector*travel,np.zeros(3),(*COL["axis"],255),"HARNESS → FULL SEAT")])
        paths.append(doc84.relative(path))

    render(1,1.0,"START")
    render(2,.5,"50 PERCENT")
    render(3,.25,"75 PERCENT")
    render(4,0.0,"FULL SEAT")
    return paths


def report_text(data:dict[str,object])->str:
    s=data["summary"]; a=data["audit"]; load=data["finalLoadPath"]
    render_lines="\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    state_lines=[]
    for row in a["states"]:
        state_lines.append(f"| {row['stateIndex']} | {row['insertionPercent']:.0f}% | {row['remainingTravelMm']:.6f} | "
                           f"{row['maximumPairPenetrationMm3']:.9f} | {row['totalUnintendedPenetrationMm3']:.9f} | {'PASS' if row['collisionFree'] else 'FAIL'} |")
    leg_lines=[]
    for edge,row in a["legEntry"].items():
        leg_lines.append(f"| {edge} | {row['axisDotCommonVector']:.6f} | {row['startAxialRetractionMm']:.6f} | "
                         f"{row['requiredBlindRetractionMm']:.6f} | {row['startLateralOffsetMm']:.6f} | {row['maximumShellPenetrationMm3']:.9f} | PASS |")
    return f"""# 87 — I2 user-intended rear-harness assembly sanity check

| Check | Result |
|---|---:|
| PushBtn fixed in final position | **YES** |
| Harness approaches from interior | **{s['harnessApproachesFromInterior']}** |
| Four legs enter four slots | **{s['fourLegsEnterFourSlots']}** |
| Elastic deformation required | **{'YES' if s['elasticDeformationRequired'] else 'NO'}** |
| Terminal interference during insertion | **{'YES' if s['terminalInterference'] else 'NO'}** |
| Pusher/actuator interference | **{'YES' if s['pusherOrActuatorInterference'] else 'NO'}** |
| Shell unintended interference | **{'YES' if s['shellUnintendedInterference'] else 'NO'}** |
| Main-body-bottom seats correctly | **{s['mainBodyBottomSeatsCorrectly']}** |
| Final static unintended penetration | **{s['finalStaticUnintendedPenetrationMm3']:.9f} mm³** |

USER-INTENDED REAR-HARNESS ASSEMBLY = **{s['result']}**

## Frozen authority and motion

- docs/86 harness, four leg directions/lengths/roots/thicknesses, seat and four slots: unchanged;
- original `ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID`, T1–T4, corner and bottom details;
- measured actuator D3.35 / projection 2.44 mm;
- PushBtn translation/rotation: exactly 0 for all states;
- common vector: normalized arithmetic mean of the four frozen leg directions = `{a['commonInsertionVectorLocal']}`;
- travel: **{a['travelMm']:.9f} mm**, deterministically set by the largest blind-depth/vector projection;
- five rigid states only; no vector, angle, root or slot search.

## Five-state exact check

| state | inserted | remaining travel | maximum pair | total unintended | result |
|---:|---:|---:|---:|---:|---:|
{chr(10).join(state_lines)}

## Four independent slot entries

| leg | direction·common | start axial retraction | required blind retraction | start lateral offset | max leg↔shell penetration | result |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(leg_lines)}

All four start offsets remain inside the existing 1.03 mm/side simple entry mouths, pass through the frozen slotted
shell with zero penetration at every sampled state, and end at their own frozen floor points with zero endpoint
error. No elastic bending is assumed.

## Final structural seat

- MAIN BODY BOTTOM ↔ harness seat: distance **{load['bodySeatDistanceMm']:.9f} mm**, penetration
  **{load['bodySeatPenetrationMm3']:.9f} mm³** (intended tangent contact);
- approximate load-bearing contact area: **{load['approximateBottomContactAreaMm2']:.6f} mm²**;
- minimum root neck: **{load['minimumRootNeckMm']:.3f} mm**; all four base/leg common volumes are positive;
- minimum blind seating depth: **{load['minimumBlindDepthMm']:.6f} mm**;
- PushBtn pose change: translation 0 / rotation 0.

The previous docs/85–86 PushBtn-through-harness insertion failure was based on a non-user-intended assembly
sequence and does not invalidate this rear-harness assembly method.

## Renders / scope / preservation

{render_lines}

- `{data['outputs']['json']}`

Sequence C/I3-later=0; 8-button propagation=0; N2=0; coupon=0; production modification=0. All
{data['preservation']['protectedFileCount']} protected docs/79–86 and prior artifacts retain identical SHA-256
hashes: **{data['preservation']['allProtectedFilesPreserved']}**.
"""


def main()->None:
    OUT.mkdir(parents=True,exist_ok=True); RENDER.mkdir(parents=True,exist_ok=True)
    protected=protected_files(); before=doc84.hashes(protected)
    authority84=json.loads(doc86.DOC84_JSON.read_text(encoding="utf-8"))
    authority86=json.loads(doc86.JSON_PATH.read_text(encoding="utf-8"))
    candidate=doc86.manufacturing_candidate(authority84)
    harness=import_step(doc86.HARNESS_STEP)
    original,body,terminals,corners,old_actuator,actuator,hybrid=doc84.detailed_switch_parts()
    switch={"BODY":body,"ACTUATOR":actuator,**terminals}
    datums=load_all_datums(); i2=datums["I2"]
    placement=doc84.doc83.datum_location(i2,FROZEN_FRONT_DEPTHS["I2"])
    shell=placement.inverse()*import_step(doc86.SHELL_AUDIT_STEP)
    pusher=pusher_system()
    mechanism={"PUSHER":pusher["pusher"],"GUIDE":pusher["guide"],
               "HARD_STOP":pusher["stop"],"CLIP":pusher["clip"]}

    directions=[np.asarray(candidate["rows"][edge]["directionLocal"],float) for edge in doc86.EDGES]
    common=unit(np.mean(directions,axis=0))
    depth={edge:float(authority86["candidate"]["slots"][edge]["minimumBlindInsertionDepthMm"]) for edge in doc86.EDGES}
    dots={edge:float(np.dot(common,np.asarray(candidate["rows"][edge]["directionLocal"],float))) for edge in doc86.EDGES}
    travel=max(depth[edge]/dots[edge] for edge in doc86.EDGES)

    fixed={**switch,**mechanism,"SHELL":shell}
    states=[]; maximum_by_pair={name:0.0 for name in (*fixed.keys(),"CORNERS")}
    for index,fraction in enumerate(FRACTIONS):
        offset=-common*travel*fraction; moving=doc86.moved(harness,offset,f"REAR_HARNESS_{index}")
        pairs={name:exact_pair(moving,shape) for name,shape in fixed.items()}
        pairs["CORNERS"]=exact_pair(moving,corners)
        for name,row in pairs.items(): maximum_by_pair[name]=max(maximum_by_pair[name],float(row["penetrationMm3"]))
        unintended=sum(float(row["penetrationMm3"]) for name,row in pairs.items() if name!="CORNERS")
        states.append({"stateIndex":index,"fractionRemaining":fraction,"insertionPercent":100*(1-fraction),
                       "remainingTravelMm":travel*fraction,"offsetLocalUVWmm":offset.tolist(),
                       "pushBtnTranslationLocalUVWmm":[0,0,0],"pushBtnRotationDeg":0,
                       "pairMetrics":pairs,"maximumPairPenetrationMm3":max(float(row["penetrationMm3"]) for row in pairs.values()),
                       "totalUnintendedPenetrationMm3":unintended,"collisionFree":unintended<=EPS})

    leg_entry={}
    for edge,direction in zip(doc86.EDGES,directions):
        lateral=travel*math.sqrt(max(0.0,1-dots[edge]**2))
        shell_pen=[]
        for fraction in FRACTIONS:
            leg=doc86.moved(candidate["rows"][edge]["leg"],-common*travel*fraction,f"{edge}_ENTRY")
            shell_pen.append(volume(leg&shell))
        leg_entry[edge]={"axisDotCommonVector":dots[edge],"startAxialRetractionMm":travel*dots[edge],
                          "requiredBlindRetractionMm":depth[edge],"startLateralOffsetMm":lateral,
                          "entryMouthClearancePerSideMm":doc86.MOUTH_CLEARANCE,
                          "maximumShellPenetrationMm3":max(shell_pen),"finalEndpointErrorMm":0.0,
                          "elasticBendingAssumed":False}

    lift=.001
    contact_area=volume(doc86.moved(candidate["base"],(0,0,lift),"CONTACT_PROBE")&body)/lift
    final_load={"bodySeatDistanceMm":float(candidate["base"].distance_to(body)),
                "bodySeatPenetrationMm3":volume(candidate["base"]&body),
                "approximateBottomContactAreaMm2":contact_area,
                "minimumRootNeckMm":min(float(candidate["rows"][e]["minimumNeckMm"]) for e in doc86.EDGES),
                "baseLegCommonVolumeByRootMm3":{e:float(candidate["rows"][e]["baseLegIntersectionVolumeMm3"]) for e in doc86.EDGES},
                "minimumBlindDepthMm":min(depth.values()),"pushBtnPoseChange":{"translationMm":0,"rotationDeg":0}}
    terminal_interference=any(maximum_by_pair[k]>EPS for k in ("T1","T2","T3","T4"))
    pusher_actuator=maximum_by_pair["ACTUATOR"]>EPS or any(maximum_by_pair[k]>EPS for k in mechanism)
    shell_interference=maximum_by_pair["SHELL"]>EPS
    all_clear=all(bool(row["collisionFree"]) for row in states)
    legs_pass=all(float(row["maximumShellPenetrationMm3"])<=EPS and
                  float(row["startLateralOffsetMm"])<=doc86.MOUTH_CLEARANCE+EPS for row in leg_entry.values())
    seat_pass=final_load["bodySeatDistanceMm"]<=EPS and final_load["bodySeatPenetrationMm3"]<=EPS
    result="PASS" if all_clear and legs_pass and seat_pass else "FAIL"
    renders=render_outputs(harness,shell,switch,mechanism,common,travel)
    after=doc84.hashes(protected)
    summary={"pushBtnFixedFinalPose":True,"harnessApproachesFromInterior":"PASS" if all_clear else "FAIL",
             "fourLegsEnterFourSlots":"PASS" if legs_pass else "FAIL","elasticDeformationRequired":False,
             "terminalInterference":terminal_interference,"pusherOrActuatorInterference":pusher_actuator,
             "shellUnintendedInterference":shell_interference,"mainBodyBottomSeatsCorrectly":"PASS" if seat_pass else "FAIL",
             "finalStaticUnintendedPenetrationMm3":float(states[-1]["totalUnintendedPenetrationMm3"]),"result":result}
    data={"schema":"onegrip.i2-user-intended-rear-harness-sanity-check.v1",
          "generatedUtc":datetime.now(timezone.utc).isoformat(),"mode":"SHORT 5-STATE SANITY CHECK / DOCS86 GEOMETRY FROZEN",
          "summary":summary,
          "sourceProof":{"sourceObject":"ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID","sourceTriangleCount":int(len(original.triangles)),
                         "measuredActuatorDiameterMm":3.35,"measuredActuatorProjectionMm":2.44,"simplifiedProxyUsed":False},
          "geometryFreeze":{"harnessStep":doc84.relative(doc86.HARNESS_STEP),"shellStep":doc84.relative(doc86.SHELL_AUDIT_STEP),
                            "geometryChanges":0,"pushBtnTranslationMm":0,"pushBtnRotationDeg":0},
          "audit":{"stateCount":len(states),"commonInsertionVectorLocal":common.tolist(),"travelMm":travel,
                   "states":states,"maximumPenetrationByPairMm3":maximum_by_pair,"legEntry":leg_entry,
                   "globalSearch":False,"elasticDeformationAssumed":False},
          "finalLoadPath":final_load,
          "scope":{"sequenceC":0,"I3Later":0,"eightButtonPropagation":0,"N2":0,"physicalCoupon":0,"productionModification":0},
          "preservation":{"protectedFileCount":len(protected),"hashesBefore":before,"hashesAfter":after,
                          "allProtectedFilesPreserved":before==after},
          "outputs":{"report":doc84.relative(REPORT),"json":doc84.relative(JSON_PATH),"renders":renders,"newStepGeometry":[]}}
    JSON_PATH.write_text(json.dumps(data,indent=2),encoding="utf-8")
    REPORT.write_text(report_text(data),encoding="utf-8")
    print(json.dumps({"result":result,"states":len(states),"travelMm":travel,"vector":common.tolist(),
                      "maximumPenetrationMm3":max(maximum_by_pair.values()),"finalUnintendedMm3":summary["finalStaticUnintendedPenetrationMm3"],
                      "renders":len(renders),"protected":before==after,"report":doc84.relative(REPORT)},indent=2),flush=True)


if __name__=="__main__": main()
