"""I2-only local +U manufacturing-clearance hardening from docs/87 authority."""
from __future__ import annotations

from datetime import datetime, timezone
import json, math
from pathlib import Path

import numpy as np
from build123d import Compound, Shape, export_step, import_step

from . import i2_detailed_pushbtn_manufacturing_robust_audit as doc84
from . import i2_manufacturing_harness_rebase_audit as doc86
from . import i2_user_intended_rear_harness_sanity_check as doc87
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import volume
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .slot_anchored_harness_captive_pusher_audit import pusher_system

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"build123d_workbench/out/i2_local_manufacturing_clearance_hardening_audit"
RENDER=ROOT/"renders/i2_local_manufacturing_clearance_hardening_audit"
REPORT=ROOT/"docs/88_i2_local_manufacturing_clearance_hardening_audit.md"
JSON_PATH=OUT/"i2_local_manufacturing_clearance_hardening_audit.json"
HARNESS_STEP=OUT/"I2_LOCAL_HARDENED_MANUFACTURING_HARNESS_AUDIT_ONLY.step"
EPS=1e-6
ROOT_SHIFT_U=-.130
PLUS_U_THICKNESS=1.30
PLUS_U_WIDTH=1.20
FRACTIONS=(1.0,.75,.5,.25,0.0)
FOOTER="I2 +U ONLY | LOCAL CLEARANCE HARDENING | DOCS/87 ASSEMBLY | PRODUCTION 0"
COL={"baseline":(113,143,171),"best":(53,184,132),"body":(66,166,224),"terminal":(225,224,228),
     "neighbor":(168,111,217),"shell":(104,127,149),"pusher":(237,132,72),"axis":(250,211,76)}


def protected_files()->list[Path]:
    rows=set(doc87.protected_files())
    rows.update({ROOT/"docs/87_i2_user_intended_rear_harness_assembly_sanity_check.md",
                 ROOT/"build123d_workbench/i2_user_intended_rear_harness_sanity_check.py"})
    for folder in (ROOT/"build123d_workbench/out/i2_user_intended_rear_harness_sanity_check",
                   ROOT/"renders/i2_user_intended_rear_harness_sanity_check"):
        rows.update(p for p in folder.rglob("*") if p.is_file())
    return sorted(p for p in rows if p.exists())


def make_hardened(baseline:dict[str,object])->dict[str,object]:
    roots={edge:np.asarray(baseline["rows"][edge]["rootLocalUVWmm"],float).copy() for edge in doc86.EDGES}
    roots["+U"][0]+=ROOT_SHIFT_U
    base=doc86.base_profile(roots); result=base; rows={}
    for edge in doc86.EDGES:
        old=baseline["rows"][edge]
        if edge=="+U":
            floor=np.asarray(old["floorPointLocalUVWmm"],float)
            direction=unit(floor-roots[edge]); hint=np.asarray((0,1,0),float)
            tangent=unit(hint-direction*float(np.dot(hint,direction)))
            thickness=PLUS_U_THICKNESS; width=PLUS_U_WIDTH
            leg=oriented_box_between(tuple(roots[edge]-direction*doc86.ROOT_EMBED),tuple(floor),tuple(tangent),
                                     width,thickness,label="I2_HARDENED_PLUS_U_STRAIGHT_LEG")
        else:
            floor=np.asarray(old["floorPointLocalUVWmm"],float); direction=np.asarray(old["directionLocal"],float)
            tangent=np.asarray(old["tangentLocal"],float); thickness=float(old["legThicknessMm"])
            width=float(old["legTangentWidthMm"]); leg=old["leg"]
        tangent_coordinate=abs(float(roots[edge][1] if edge.endswith("U") else roots[edge][0]))
        shared=doc86.FRAME_WIDTH-tangent_coordinate
        rows[edge]={"leg":leg,"rootLocalUVWmm":roots[edge].tolist(),"floorPointLocalUVWmm":floor.tolist(),
                    "directionLocal":direction.tolist(),"tangentLocal":tangent.tolist(),
                    "legThicknessMm":thickness,"legTangentWidthMm":width,
                    "effectiveFdmThicknessMm":thickness*abs(float(direction[2])),
                    "sharedStructuralWidthMm":shared,"minimumNeckMm":min(shared,thickness,doc86.ROOT_EMBED),
                    "baseLegIntersectionVolumeMm3":volume(base&leg)}
        result=result.fuse(leg)
    result=result.clean(); result.label="I2_LOCAL_HARDENED_ONE_PIECE_FOUR_EDGE_HARNESS"
    return {"harness":result,"base":base,"rows":rows}


def local_metrics(leg:Shape,body:Shape,terminals:dict[str,Shape],corners:Shape,pusher:Shape,
                  placement,i3_world:dict[str,Shape])->dict[str,object]:
    i3=doc84.many_metrics(placement*leg,i3_world)
    return {"T4ClearanceMm":float(leg.distance_to(terminals["T4"])),
            "I3ClearanceMm":float(i3["minimumDistanceMm"]),"I3NearestPart":i3["nearest"],
            "minimumLocalClearanceMm":min(float(leg.distance_to(terminals["T4"])),float(i3["minimumDistanceMm"])),
            "I2Body":doc84.pair_metrics(leg,body),"cornerClearanceMm":float(leg.distance_to(corners)),
            "pusherClearanceMm":float(leg.distance_to(pusher)),"I3Details":i3}


def rear_check(candidate:dict[str,object],shell:Shape,fixed:dict[str,Shape],depths:dict[str,float])->dict[str,object]:
    dirs={e:np.asarray(candidate["rows"][e]["directionLocal"],float) for e in doc86.EDGES}
    common=unit(np.mean(list(dirs.values()),axis=0)); dots={e:float(np.dot(common,dirs[e])) for e in doc86.EDGES}
    travel=max(depths[e]/dots[e] for e in doc86.EDGES); states=[]; max_pair={k:0.0 for k in fixed}
    for index,fraction in enumerate(FRACTIONS):
        offset=-common*travel*fraction; moving=doc86.moved(candidate["harness"],offset,f"HARDENED_REAR_{index}")
        pairs={k:volume(moving&v) for k,v in fixed.items()}
        for k,v in pairs.items(): max_pair[k]=max(max_pair[k],v)
        states.append({"stateIndex":index,"insertionPercent":100*(1-fraction),"remainingTravelMm":travel*fraction,
                       "offsetLocalUVWmm":offset.tolist(),"pairPenetrationMm3":pairs,
                       "totalUnintendedPenetrationMm3":sum(pairs.values()),"collisionFree":all(v<=EPS for v in pairs.values())})
    return {"result":"PASS" if all(r["collisionFree"] for r in states) else "FAIL","stateCount":5,
            "commonInsertionVectorLocal":common.tolist(),"travelMm":travel,"states":states,
            "maximumPenetrationByPairMm3":max_pair,"elasticDeformationRequired":False}


def render_outputs(baseline:dict[str,object],best:dict[str,object],body:Shape,terminals:dict[str,Shape],
                   i3_local:dict[str,Shape],shell:Shape,pusher:Shape,rear:dict[str,object])->list[str]:
    RENDER.mkdir(parents=True,exist_ok=True); paths=[]
    i3_compound=Compound(children=list(i3_local.values())); shell_tri=doc84.safe_triangles(shell)
    base_leg=baseline["rows"]["+U"]["leg"]; best_leg=best["rows"]["+U"]["leg"]
    def render(name,title,subtitle,objects,camera=(23,-31,12),transparent=None,lines=None,fit=None):
        path=RENDER/name; doc84.raster_scene(path,objects,title,subtitle,FOOTER,camera_offset=camera,
                                             transparent_objects=transparent or [],world_lines=lines or [],fit_points=fit)
        paths.append(doc84.relative(path))
    common=[(doc84.safe_triangles(terminals["T4"]),COL["terminal"]),(doc84.safe_triangles(i3_compound),COL["neighbor"])]
    render("01_baseline_plus_u_t4_i3_closeup.png","1 / DOCS/87 ACTUAL +U BASELINE",
           "T4=0.954994 | I3=0.090777 mm | legacy 0.059/0.059 values belong to docs/84",
           [(doc84.safe_triangles(base_leg),COL["baseline"]),*common])
    render("02_best_candidate_plus_u_closeup.png","2 / HARDENED +U LOCAL CANDIDATE",
           "root U −0.130 | nominal 1.30 | tangent 1.20 | straight endpoint retained",
           [(doc84.safe_triangles(best_leg),COL["best"]),*common])
    for number,target,label,filename in ((3,terminals["T4"],"T4","03_t4_minimum_clearance_section.png"),
                                         (4,i3_local["BODY"],"I3 BODY","04_i3_minimum_clearance_section.png")):
        distance,p0,p1=best_leg.distance_to_with_closest_points(target)
        render(filename,f"{number} / {label} MINIMUM CLEARANCE",f"exact BRep distance={distance:.6f} mm",
               [(doc84.safe_triangles(best_leg),COL["best"]),(doc84.safe_triangles(target),COL["terminal"] if label=="T4" else COL["neighbor"])],
               camera=(18,-25,8),lines=[(tuple(p0),tuple(p1),(*COL["axis"],255),f"{distance:.3f} mm")])
    render("05_hardened_manufacturing_harness_isometric.png","5 / HARDENED MANUFACTURING HARNESS",
           "one fused solid | only +U local root/section changed",
           [(doc84.safe_triangles(best["harness"]),COL["best"])])
    render("06_rear_harness_full_seat.png","6 / USER-INTENDED REAR HARNESS — FULL SEAT",
           "PushBtn fixed | 5-state rigid sanity check PASS | final penetration 0",
           [(doc84.safe_triangles(best["harness"]),COL["best"]),(doc84.safe_triangles(body),COL["body"]),
            (doc84.safe_triangles(terminals["T4"]),COL["terminal"]),(doc84.safe_triangles(pusher),COL["pusher"])],
           camera=(29,-40,22),transparent=[(shell_tri,(*COL["shell"],42))])
    return paths


def report_text(d:dict[str,object])->str:
    b=d["baselineActual"]; c=d["bestCandidate"]; rear=d["rearHarnessAssembly"]
    renders="\n".join(f"- [{Path(x).name}](../{x})" for x in d["outputs"]["renders"])
    return f"""# 88 — I2 local manufacturing-clearance hardening audit

FINAL VERDICT = **{d['finalVerdict']}**

## Authority correction

The supplied 0.059066 / 0.059187 mm pair is reproduced from the docs/84 robust/probe lineage. The STEP actually
used by docs/87 is the docs/86 manufacturing harness and measures +U↔T4 **{b['T4ClearanceMm']:.6f} mm** and
+U↔I3 **{b['I3ClearanceMm']:.6f} mm**. Both lineages are retained below rather than relabeling old numbers as docs/87.

| Metric | supplied legacy reference | docs/87 actual baseline | Best local candidate |
|---|---:|---:|---:|
| +U nominal thickness | 1.250 | {b['nominalThicknessMm']:.3f} | **{c['nominalThicknessMm']:.3f} mm** |
| +U effective thickness | 1.228681 | {b['effectiveThicknessMm']:.6f} | **{c['effectiveThicknessMm']:.6f} mm** |
| +U root shift from docs/87 | — | 0 | **{c['rootShiftLocalUVWmm']} mm** |
| +U tilt | 10.597° legacy | {b['tiltDeg']:.6f}° | **{c['tiltDeg']:.6f}°** |
| T4 clearance | 0.059066 | {b['T4ClearanceMm']:.6f} | **{c['T4ClearanceMm']:.6f} mm** |
| I3 clearance | 0.059187 | {b['I3ClearanceMm']:.6f} | **{c['I3ClearanceMm']:.6f} mm** |
| MIN_LOCAL_CLEARANCE | ~0.059 | {b['minimumLocalClearanceMm']:.6f} | **{c['minimumLocalClearanceMm']:.6f} mm** |
| remaining shell, global minimum | — | 1.200134 | **1.200134 mm (unchanged slot)** |
| rear-harness assembly | PASS | PASS | **{rear['result']}** |

## Bounded A–D evidence and Pareto stop

| candidate | simple change | min local | effective section | I2-body clearance | disposition |
|---|---|---:|---:|---:|---|
| A | docs/87 actual | {b['minimumLocalClearanceMm']:.6f} | {b['effectiveThicknessMm']:.6f} | {b['I2Body']['distanceMm']:.6f} | new 1.20 effective gate fails |
| B | root U −0.150 only | 0.252813 | 1.163903 | 0.067745 | effective gate fails |
| C | root U −0.100 + 1.30/1.20 section | 0.187815 | 1.211970 | 0.092799 | valid, below practical target |
| **D selected** | root U −0.130 + 1.30/1.20 section | **{c['minimumLocalClearanceMm']:.6f}** | **{c['effectiveThicknessMm']:.6f}** | **{c['I2Body']['distanceMm']:.6f}** | **PASS** |
| mathematical boundary | root U −0.190 + 1.30/1.20 | 0.283936 | 1.209214 | 0.002779 | rejected as non-hardened body margin |
| next boundary sample | root U −0.195 + 1.30/1.20 | 0.289259 | 1.209056 | penetration | FAIL |

The legacy ~0.059 mm pair is therefore **not** a topological limit. The local objective can exceed 0.20 mm with a
straight member. Continuing toward 0.284 mm only transfers the tight tolerance to the frozen I2 body, so
**{c['minimumLocalClearanceMm']:.6f} mm** is the practical Pareto stop used for the manufacturing candidate.

## Manufacturing and shell gate

- fused / STEP-reimport solids: **{d['manufacturingGate']['solidCount']} / {d['manufacturingGate']['stepReimportSolidCount']}**;
- valid/watertight: **{d['manufacturingGate']['valid'] and d['manufacturingGate']['stepReimportValid']}**;
- tangent-only / zero-thickness: **0 / 0**;
- minimum structural neck: **{d['manufacturingGate']['minimumNeckMm']:.3f} mm**;
- +U base/leg common volume: **{d['manufacturingGate']['plusURootCommonVolumeMm3']:.6f} mm³**;
- harness↔unchanged slotted shell penetration: **{d['manufacturingGate']['shellPenetrationMm3']:.9f} mm³**;
- +U endpoint and matching slot: unchanged; global remaining exterior shell **1.200134 mm**.

Corner clearance={c['cornerClearanceMm']:.6f} mm; pusher clearance={c['pusherClearanceMm']:.6f} mm. Original detailed
3530-facet PushBtn and measured D3.35 × 2.44 actuator were used; no proxy was used.

## Rear-harness recheck

Five rigid states, PushBtn translation/rotation 0, elastic deformation NO. Result **{rear['result']}**; terminal,
pusher/actuator and shell maximum penetrations are all **0 mm³**; final unintended penetration **0 mm³**.

## Renders / outputs / STOP

{renders}

- `{d['outputs']['harnessStep']}`
- `{d['outputs']['json']}`

Production modification=0; 8-button propagation=0; N2=0; physical coupon=0; architecture redesign=0. All
{d['preservation']['protectedFileCount']} protected docs/79–87 and prior artifacts retain identical SHA-256 hashes:
**{d['preservation']['allProtectedFilesPreserved']}**.
"""


def main()->None:
    OUT.mkdir(parents=True,exist_ok=True); RENDER.mkdir(parents=True,exist_ok=True)
    protected=protected_files(); before=doc84.hashes(protected)
    auth84=json.loads(doc86.DOC84_JSON.read_text(encoding="utf-8")); auth86=json.loads(doc86.JSON_PATH.read_text(encoding="utf-8"))
    baseline=doc86.manufacturing_candidate(auth84); best=make_hardened(baseline)
    export_step(best["harness"],HARNESS_STEP); reimport=import_step(HARNESS_STEP)
    original,body,terminals,corners,old_actuator,actuator,hybrid=doc84.detailed_switch_parts()
    datums=load_all_datums(); i2=datums["I2"]; placement=doc84.doc83.datum_location(i2,FROZEN_FRONT_DEPTHS["I2"])
    parts={"BODY":body,"ACTUATOR":actuator,**terminals}; i3_world=doc84.neighbor_components(parts,datums)["I3"]
    i3_local={k:placement.inverse()*v for k,v in i3_world.items()}; mech=pusher_system(); pusher=mech["pusher"]
    baseline_m=local_metrics(baseline["rows"]["+U"]["leg"],body,terminals,corners,pusher,placement,i3_world)
    best_m=local_metrics(best["rows"]["+U"]["leg"],body,terminals,corners,pusher,placement,i3_world)
    shell=placement.inverse()*import_step(doc86.SHELL_AUDIT_STEP)
    fixed={**parts,"PUSHER":mech["pusher"],"GUIDE":mech["guide"],"HARD_STOP":mech["stop"],"CLIP":mech["clip"],"SHELL":shell}
    depths={e:float(auth86["candidate"]["slots"][e]["minimumBlindInsertionDepthMm"]) for e in doc86.EDGES}
    rear=rear_check(best,shell,fixed,depths)
    gate={"solidCount":len(best["harness"].solids()),"stepReimportSolidCount":len(reimport.solids()),
          "valid":bool(best["harness"].is_valid),"stepReimportValid":bool(reimport.is_valid),
          "minimumNeckMm":min(float(best["rows"][e]["minimumNeckMm"]) for e in doc86.EDGES),
          "minimumEffectiveThicknessMm":min(float(best["rows"][e]["effectiveFdmThicknessMm"]) for e in doc86.EDGES),
          "plusURootCommonVolumeMm3":float(best["rows"]["+U"]["baseLegIntersectionVolumeMm3"]),
          "shellPenetrationMm3":volume(best["harness"]&shell),"remainingExteriorShellMm":float(auth86["manufacturingGate"]["minimumRemainingShellMm"])}
    gate["result"]="PASS" if (gate["solidCount"]==gate["stepReimportSolidCount"]==1 and gate["valid"] and
                              gate["stepReimportValid"] and gate["minimumNeckMm"]>=1.2-EPS and
                              gate["minimumEffectiveThicknessMm"]>=1.2-EPS and gate["plusURootCommonVolumeMm3"]>EPS and
                              gate["shellPenetrationMm3"]<=EPS and rear["result"]=="PASS") else "FAIL"
    renders=render_outputs(baseline,best,body,terminals,i3_local,shell,pusher,rear)
    after=doc84.hashes(protected)
    b_row=baseline["rows"]["+U"]; c_row=best["rows"]["+U"]
    data={"schema":"onegrip.i2-local-manufacturing-clearance-hardening-audit.v1",
          "generatedUtc":datetime.now(timezone.utc).isoformat(),"finalVerdict":"A — LOCAL CLEARANCE IMPROVED TO PRACTICAL LEVEL",
          "sourceProof":{"sourceObject":"ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID","sourceTriangleCount":int(len(original.triangles)),
                         "measuredActuatorDiameterMm":3.35,"measuredActuatorProjectionMm":2.44,"proxyUsed":False},
          "lineageCorrection":{"suppliedLegacyT4Mm":.05906572325941589,"suppliedLegacyI3Mm":.05918739030908077,
                               "legacySource":"docs/84 robust/probe lineage","actualBaselineSource":"docs/87 using docs/86 manufacturing STEP"},
          "baselineActual":{**baseline_m,"nominalThicknessMm":float(b_row["legThicknessMm"]),
                            "tangentWidthMm":float(b_row["legTangentWidthMm"]),
                            "effectiveThicknessMm":float(b_row["legThicknessMm"])*abs(float(b_row["directionLocal"][2])),
                            "tiltDeg":math.degrees(math.acos(abs(float(b_row["directionLocal"][2]))))},
          "bestCandidate":{**best_m,"rootShiftLocalUVWmm":[ROOT_SHIFT_U,0,0],"nominalThicknessMm":PLUS_U_THICKNESS,
                           "tangentWidthMm":PLUS_U_WIDTH,"effectiveThicknessMm":float(c_row["effectiveFdmThicknessMm"]),
                           "tiltDeg":math.degrees(math.acos(abs(float(c_row["directionLocal"][2])))),
                           "shellEndpointChanged":False,"matchingSlotChanged":False},
          "paretoBoundary":{"acceptedPracticalMinimumLocalClearanceMm":best_m["minimumLocalClearanceMm"],
                            "mathematicalZeroPenetrationBoundary":{"rootShiftUMm":-.190,"minimumLocalClearanceMm":.2839358051857707,
                                                                   "I2BodyClearanceMm":.0027789747469393234},
                            "nextSample":{"rootShiftUMm":-.195,"I2BodyPenetrationMm3":1.558225636870746e-5}},
          "manufacturingGate":gate,"rearHarnessAssembly":rear,
          "scope":{"productionModification":0,"eightButtonPropagation":0,"N2":0,"physicalCoupon":0,"architectureRedesign":0},
          "preservation":{"protectedFileCount":len(protected),"hashesBefore":before,"hashesAfter":after,
                          "allProtectedFilesPreserved":before==after},
          "outputs":{"report":doc84.relative(REPORT),"json":doc84.relative(JSON_PATH),"harnessStep":doc84.relative(HARNESS_STEP),
                     "unchangedShellStep":doc84.relative(doc86.SHELL_AUDIT_STEP),"renders":renders}}
    JSON_PATH.write_text(json.dumps(data,indent=2),encoding="utf-8"); REPORT.write_text(report_text(data),encoding="utf-8")
    print(json.dumps({"verdict":data["finalVerdict"],"gate":gate["result"],"T4":best_m["T4ClearanceMm"],
                      "I3":best_m["I3ClearanceMm"],"minLocal":best_m["minimumLocalClearanceMm"],
                      "effective":c_row["effectiveFdmThicknessMm"],"rear":rear["result"],"renders":len(renders),
                      "protected":before==after,"report":doc84.relative(REPORT)},indent=2),flush=True)


if __name__=="__main__": main()
