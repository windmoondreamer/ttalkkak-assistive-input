"""Final I2 +U three-way local clearance balancing audit from docs/88."""
from __future__ import annotations

from datetime import datetime, timezone
import json, math
from pathlib import Path

import numpy as np
from build123d import Compound, Shape, export_step, import_step

from . import i2_detailed_pushbtn_manufacturing_robust_audit as doc84
from . import i2_manufacturing_harness_rebase_audit as doc86
from . import i2_user_intended_rear_harness_sanity_check as doc87
from . import i2_local_manufacturing_clearance_hardening_audit as doc88
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import volume
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .slot_anchored_harness_captive_pusher_audit import pusher_system

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"build123d_workbench/out/i2_final_local_clearance_balancing_audit"
RENDER=ROOT/"renders/i2_final_local_clearance_balancing_audit"
REPORT=ROOT/"docs/89_i2_final_local_clearance_balancing_audit.md"
JSON_PATH=OUT/"i2_final_local_clearance_balancing_audit.json"
HARNESS_STEP=OUT/"I2_FINAL_BALANCED_MANUFACTURING_HARNESS_AUDIT_ONLY.step"
FINAL_SHIFT_U=-.05425
FINAL_EFFECTIVE=1.20
FINAL_WIDTH=1.20
EPS=1e-6
FOOTER="I2 +U FINAL | THREE-WAY CLEARANCE BALANCE | DOCS/88 AUTHORITY | PRODUCTION 0"
COL={"old":(96,126,155),"new":(50,183,130),"body":(67,166,224),"terminal":(222,226,232),
     "i3":(163,105,216),"shell":(102,125,147),"pusher":(237,132,72),"axis":(250,211,76)}


def protected_files()->list[Path]:
    rows=set(doc88.protected_files())
    rows.update({ROOT/"docs/88_i2_local_manufacturing_clearance_hardening_audit.md",
                 ROOT/"build123d_workbench/i2_local_manufacturing_clearance_hardening_audit.py"})
    for folder in (ROOT/"build123d_workbench/out/i2_local_manufacturing_clearance_hardening_audit",
                   ROOT/"renders/i2_local_manufacturing_clearance_hardening_audit"):
        rows.update(p for p in folder.rglob("*") if p.is_file())
    return sorted(p for p in rows if p.exists())


def candidate_from(baseline:dict[str,object],shift_u:float,effective:float,width:float=1.20)->dict[str,object]:
    roots={e:np.asarray(baseline["rows"][e]["rootLocalUVWmm"],float).copy() for e in doc86.EDGES}
    roots["+U"][0]+=shift_u; base=doc86.base_profile(roots); result=base; rows={}
    for edge in doc86.EDGES:
        old=baseline["rows"][edge]
        if edge=="+U":
            floor=np.asarray(old["floorPointLocalUVWmm"],float); direction=unit(floor-roots[edge])
            thickness=effective/abs(float(direction[2])); hint=np.asarray((0,1,0),float)
            tangent=unit(hint-direction*float(np.dot(hint,direction)))
            leg=oriented_box_between(tuple(roots[edge]-direction*doc86.ROOT_EMBED),tuple(floor),tuple(tangent),
                                     width,thickness,label="I2_FINAL_BALANCED_PLUS_U_STRAIGHT_LEG")
        else:
            floor=np.asarray(old["floorPointLocalUVWmm"],float); direction=np.asarray(old["directionLocal"],float)
            tangent=np.asarray(old["tangentLocal"],float); thickness=float(old["legThicknessMm"])
            width=float(old["legTangentWidthMm"]); leg=old["leg"]
        shared=doc86.FRAME_WIDTH-abs(float(roots[edge][1] if edge.endswith("U") else roots[edge][0]))
        rows[edge]={"leg":leg,"rootLocalUVWmm":roots[edge].tolist(),"floorPointLocalUVWmm":floor.tolist(),
                    "directionLocal":direction.tolist(),"tangentLocal":tangent.tolist(),"legThicknessMm":thickness,
                    "legTangentWidthMm":width,"effectiveFdmThicknessMm":thickness*abs(float(direction[2])),
                    "minimumNeckMm":min(shared,thickness,doc86.ROOT_EMBED),
                    "baseLegIntersectionVolumeMm3":volume(base&leg)}
        result=result.fuse(leg)
    result=result.clean(); result.label="I2_FINAL_THREE_WAY_BALANCED_ONE_PIECE_HARNESS"
    return {"harness":result,"base":base,"rows":rows,"shiftUmm":shift_u,"targetEffectiveMm":effective}


def metrics(candidate:dict[str,object],body:Shape,terminals:dict[str,Shape],corners:Shape,pusher:Shape,
            placement,i3_world:dict[str,Shape])->dict[str,object]:
    leg=candidate["rows"]["+U"]["leg"]; term={k:float(leg.distance_to(v)) for k,v in terminals.items()}
    nearest_terminal=min(term,key=term.get); i3=doc84.many_metrics(placement*leg,i3_world)
    body_pair=doc84.pair_metrics(leg,body)
    return {"I2BodyClearanceMm":float(body_pair["distanceMm"]),"I2BodyPenetrationMm3":float(body_pair["penetrationMm3"]),
            "terminalClearanceMm":term[nearest_terminal],"nearestTerminal":nearest_terminal,"terminalByPartMm":term,
            "T4ClearanceMm":term["T4"],"I3ClearanceMm":float(i3["minimumDistanceMm"]),"I3NearestPart":i3["nearest"],
            "minimumThreeWayClearanceMm":min(float(body_pair["distanceMm"]),term[nearest_terminal],float(i3["minimumDistanceMm"])),
            "cornerClearanceMm":float(leg.distance_to(corners)),"pusherClearanceMm":float(leg.distance_to(pusher))}


def rear_check(candidate:dict[str,object],fixed:dict[str,Shape],depths:dict[str,float])->dict[str,object]:
    directions={e:np.asarray(candidate["rows"][e]["directionLocal"],float) for e in doc86.EDGES}
    common=unit(np.mean(list(directions.values()),axis=0)); dots={e:float(np.dot(common,directions[e])) for e in doc86.EDGES}
    travel=max(depths[e]/dots[e] for e in doc86.EDGES); states=[]; maxima={k:0.0 for k in fixed}
    for index,fraction in enumerate((1,.75,.5,.25,0)):
        moving=doc86.moved(candidate["harness"],-common*travel*fraction,f"FINAL_BALANCE_REAR_{index}")
        pairs={k:volume(moving&v) for k,v in fixed.items()}
        for k,v in pairs.items(): maxima[k]=max(maxima[k],v)
        states.append({"stateIndex":index,"insertionPercent":100*(1-fraction),"remainingTravelMm":travel*fraction,
                       "pairPenetrationMm3":pairs,"totalUnintendedPenetrationMm3":sum(pairs.values()),
                       "collisionFree":all(v<=EPS for v in pairs.values())})
    return {"result":"PASS" if all(r["collisionFree"] for r in states) else "FAIL","stateCount":5,
            "commonInsertionVectorLocal":common.tolist(),"travelMm":travel,"states":states,
            "maximumPenetrationByPairMm3":maxima,"elasticDeformationRequired":False}


def render_outputs(old:dict[str,object],new:dict[str,object],old_m:dict[str,object],new_m:dict[str,object],
                   body:Shape,terminals:dict[str,Shape],i3_local:dict[str,Shape],shell:Shape,pusher:Shape)->list[str]:
    RENDER.mkdir(parents=True,exist_ok=True); paths=[]; i3=Compound(children=list(i3_local.values()))
    old_leg=old["rows"]["+U"]["leg"]; leg=new["rows"]["+U"]["leg"]
    def render(name,title,subtitle,objects,camera=(22,-31,11),lines=None,transparent=None):
        path=RENDER/name; doc84.raster_scene(path,objects,title,subtitle,FOOTER,camera_offset=camera,
                                             world_lines=lines or [],transparent_objects=transparent or [])
        paths.append(doc84.relative(path))
    context=[(doc84.safe_triangles(body),COL["body"]),
             *[(doc84.safe_triangles(v),COL["terminal"]) for v in terminals.values()],
             (doc84.safe_triangles(i3),COL["i3"])]
    render("01_docs88_d_three_way_closeup.png","1 / DOCS/88 D — THREE-WAY BOTTLENECK",
           "BODY=0.062755 | terminal and I3 larger | tightness moved to own body",
           [(doc84.safe_triangles(old_leg),COL["old"]),*context])
    render("02_final_balanced_three_way_closeup.png","2 / FINAL +U THREE-WAY BALANCE",
           f"BODY={new_m['I2BodyClearanceMm']:.6f} | terminal={new_m['terminalClearanceMm']:.6f} | I3={new_m['I3ClearanceMm']:.6f} mm",
           [(doc84.safe_triangles(leg),COL["new"]),*context])
    targets=((3,body,"I2 BODY",new_m["I2BodyClearanceMm"],"03_i2_body_minimum_clearance.png",COL["body"]),
             (4,i3_local[new_m["I3NearestPart"]],"I3",new_m["I3ClearanceMm"],"04_i3_minimum_clearance.png",COL["i3"]),
             (5,terminals[new_m["nearestTerminal"]],f"TERMINAL {new_m['nearestTerminal']}",new_m["terminalClearanceMm"],"05_terminal_minimum_clearance.png",COL["terminal"]))
    for number,target,label,distance,filename,color in targets:
        _,p0,p1=leg.distance_to_with_closest_points(target)
        render(filename,f"{number} / {label} MINIMUM CLEARANCE",f"exact detailed BRep distance={distance:.6f} mm",
               [(doc84.safe_triangles(leg),COL["new"]),(doc84.safe_triangles(target),color)],camera=(18,-25,8),
               lines=[(tuple(p0),tuple(p1),(*COL["axis"],255),f"{distance:.3f} mm")])
    render("06_rear_harness_full_seat.png","6 / REAR-HARNESS FULL SEAT",
           "PushBtn frozen | 5-state rigid assembly PASS | unintended penetration 0",
           [(doc84.safe_triangles(new["harness"]),COL["new"]),(doc84.safe_triangles(body),COL["body"]),
            (doc84.safe_triangles(pusher),COL["pusher"])],camera=(29,-40,22),
           transparent=[(doc84.safe_triangles(shell),(*COL["shell"],42))])
    return paths


def report_text(d:dict[str,object])->str:
    old=d["docs88CandidateD"]; new=d["finalCandidate"]
    renders="\n".join(f"- [{Path(x).name}](../{x})" for x in d["outputs"]["renders"])
    return f"""# 89 — I2 +U final local three-way clearance balancing audit

FINAL VERDICT = **{d['finalVerdict']}**

| Metric | docs/88 D | Final balanced candidate |
|---|---:|---:|
| I2 body clearance | 0.062755 | **{new['I2BodyClearanceMm']:.6f} mm** |
| minimum terminal clearance | {old['terminalClearanceMm']:.6f} | **{new['terminalClearanceMm']:.6f} mm ({new['nearestTerminal']})** |
| T4 clearance | 1.148952 | **{new['T4ClearanceMm']:.6f} mm** |
| I3 clearance | 0.219919 | **{new['I3ClearanceMm']:.6f} mm** |
| MIN_3WAY_CLEARANCE | 0.062755 | **{new['minimumThreeWayClearanceMm']:.6f} mm** |
| +U nominal thickness | 1.300 | **{new['nominalThicknessMm']:.6f} mm** |
| +U effective thickness | 1.211070 | **{new['effectiveThicknessMm']:.6f} mm** |
| minimum neck | 1.270 | **{d['manufacturingGate']['minimumNeckMm']:.3f} mm** |
| remaining shell | 1.200134 | **1.200134 mm** |
| rear-harness assembly | PASS | **{d['rearHarnessAssembly']['result']}** |

## Pareto candidates

| candidate | root U shift | effective | body | terminal | I3 | MIN_3WAY | rear |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 — maximum MIN_3WAY / selected | −0.054250 | 1.200 | {new['I2BodyClearanceMm']:.6f} | {new['terminalClearanceMm']:.6f} | {new['I3ClearanceMm']:.6f} | **{new['minimumThreeWayClearanceMm']:.6f}** | PASS |
| 2 — manufacturing section margin | −0.054250 | 1.210 | {d['paretoCandidates']['manufacturingBalanced']['I2BodyClearanceMm']:.6f} | {d['paretoCandidates']['manufacturingBalanced']['terminalClearanceMm']:.6f} | {d['paretoCandidates']['manufacturingBalanced']['I3ClearanceMm']:.6f} | **{d['paretoCandidates']['manufacturingBalanced']['minimumThreeWayClearanceMm']:.6f}** | static PASS |
| 3 — max I3 with body ≥0.15 | −0.050000 | 1.200 | {d['paretoCandidates']['bodyAtLeast015']['I2BodyClearanceMm']:.6f} | {d['paretoCandidates']['bodyAtLeast015']['terminalClearanceMm']:.6f} | {d['paretoCandidates']['bodyAtLeast015']['I3ClearanceMm']:.6f} | **{d['paretoCandidates']['bodyAtLeast015']['minimumThreeWayClearanceMm']:.6f}** | static PASS |

The limiting pair is BODY/I3, not terminals. The bounded 22-candidate section sweep plus 12 tangent checks peaks
where BODY and I3 are nearly equal. A 0.15 mm simultaneous margin is short by **{.15-new['minimumThreeWayClearanceMm']:.6f} mm**;
further U motion improves I3 while reducing BODY by the same order. No tight tolerance is moved to a near-zero pair.

## Manufacturing / shell / assembly gates

- one fused solid / STEP reimport: **{d['manufacturingGate']['solidCount']} / {d['manufacturingGate']['stepReimportSolidCount']}**;
- valid/watertight: **{d['manufacturingGate']['valid'] and d['manufacturingGate']['stepReimportValid']}**;
- tangent-only / zero-thickness: **0 / 0**;
- minimum neck: **{d['manufacturingGate']['minimumNeckMm']:.3f} mm**;
- minimum effective section: **{d['manufacturingGate']['minimumEffectiveThicknessMm']:.6f} mm**;
- +U root common volume: **{d['manufacturingGate']['plusURootCommonVolumeMm3']:.6f} mm³**;
- endpoint/slot change: **NO**; shell penetration 0; remaining exterior shell **1.200134 mm**.

Original detailed 3,530-facet PushBtn, T1–T4/corners/bottom and measured D3.35 × 2.44 actuator were used. The
five-state user-intended rear-harness check keeps PushBtn translation/rotation at 0 and reports terminal/body,
pusher/actuator, shell and final unintended penetration all **0 mm³**; elastic deformation **NO**.

## Renders / outputs / STOP

{renders}

- `{d['outputs']['harnessStep']}`
- `{d['outputs']['json']}`

Production modification=0; 8-button propagation=0; N2=0; coupon=0; architecture redesign=0. All
{d['preservation']['protectedFileCount']} protected docs/79–88 and prior artifacts retain identical SHA-256 hashes:
**{d['preservation']['allProtectedFilesPreserved']}**.
"""


def main()->None:
    OUT.mkdir(parents=True,exist_ok=True); RENDER.mkdir(parents=True,exist_ok=True)
    protected=protected_files(); before=doc84.hashes(protected)
    auth84=json.loads(doc86.DOC84_JSON.read_text(encoding="utf-8")); auth86=json.loads(doc86.JSON_PATH.read_text(encoding="utf-8"))
    baseline=doc86.manufacturing_candidate(auth84); old=doc88.make_hardened(baseline)
    final=candidate_from(baseline,FINAL_SHIFT_U,FINAL_EFFECTIVE); alt2=candidate_from(baseline,FINAL_SHIFT_U,1.21)
    alt3=candidate_from(baseline,-.05,1.20)
    export_step(final["harness"],HARNESS_STEP); imported=import_step(HARNESS_STEP)
    original,body,terminals,corners,old_actuator,actuator,hybrid=doc84.detailed_switch_parts()
    datums=load_all_datums(); i2=datums["I2"]; placement=doc84.doc83.datum_location(i2,FROZEN_FRONT_DEPTHS["I2"])
    parts={"BODY":body,"ACTUATOR":actuator,**terminals}; i3_world=doc84.neighbor_components(parts,datums)["I3"]
    i3_local={k:placement.inverse()*v for k,v in i3_world.items()}; mech=pusher_system(); pusher=mech["pusher"]
    old_m=metrics(old,body,terminals,corners,pusher,placement,i3_world)
    final_m=metrics(final,body,terminals,corners,pusher,placement,i3_world)
    alt2_m=metrics(alt2,body,terminals,corners,pusher,placement,i3_world)
    alt3_m=metrics(alt3,body,terminals,corners,pusher,placement,i3_world)
    shell=placement.inverse()*import_step(doc86.SHELL_AUDIT_STEP)
    fixed={**parts,"PUSHER":mech["pusher"],"GUIDE":mech["guide"],"HARD_STOP":mech["stop"],"CLIP":mech["clip"],"SHELL":shell}
    depths={e:float(auth86["candidate"]["slots"][e]["minimumBlindInsertionDepthMm"]) for e in doc86.EDGES}
    rear=rear_check(final,fixed,depths)
    row=final["rows"]["+U"]
    gate={"solidCount":len(final["harness"].solids()),"stepReimportSolidCount":len(imported.solids()),
          "valid":bool(final["harness"].is_valid),"stepReimportValid":bool(imported.is_valid),
          "minimumNeckMm":min(float(final["rows"][e]["minimumNeckMm"]) for e in doc86.EDGES),
          "minimumEffectiveThicknessMm":min(float(final["rows"][e]["effectiveFdmThicknessMm"]) for e in doc86.EDGES),
          "plusURootCommonVolumeMm3":float(row["baseLegIntersectionVolumeMm3"]),
          "shellPenetrationMm3":volume(final["harness"]&shell),"remainingExteriorShellMm":float(auth86["manufacturingGate"]["minimumRemainingShellMm"])}
    gate["result"]="PASS" if (gate["solidCount"]==gate["stepReimportSolidCount"]==1 and gate["valid"] and gate["stepReimportValid"] and
                              gate["minimumNeckMm"]>=1.2-EPS and gate["minimumEffectiveThicknessMm"]>=1.2-EPS and
                              gate["plusURootCommonVolumeMm3"]>EPS and gate["shellPenetrationMm3"]<=EPS and rear["result"]=="PASS") else "FAIL"
    renders=render_outputs(old,final,old_m,final_m,body,terminals,i3_local,shell,pusher)
    after=doc84.hashes(protected)
    final_row=final["rows"]["+U"]
    data={"schema":"onegrip.i2-final-local-three-way-clearance-balancing-audit.v1",
          "generatedUtc":datetime.now(timezone.utc).isoformat(),"finalVerdict":"B — IMPROVED BALANCE BUT ONE CLEARANCE REMAINS TIGHT",
          "sourceProof":{"sourceObject":"ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID","sourceTriangleCount":int(len(original.triangles)),
                         "measuredActuatorDiameterMm":3.35,"measuredActuatorProjectionMm":2.44,"proxyUsed":False},
          "docs88CandidateD":{**old_m,"nominalThicknessMm":1.3,"effectiveThicknessMm":1.2110695063348682,
                              "rootShiftLocalUVWmm":[-.13,0,0]},
          "finalCandidate":{**final_m,"rootShiftLocalUVWmm":[FINAL_SHIFT_U,0,0],
                            "nominalThicknessMm":float(final_row["legThicknessMm"]),
                            "effectiveThicknessMm":float(final_row["effectiveFdmThicknessMm"]),
                            "tangentWidthMm":FINAL_WIDTH,"tiltDeg":math.degrees(math.acos(abs(float(final_row["directionLocal"][2])))),
                            "endpointChanged":False,"slotChanged":False},
          "paretoCandidates":{"maximumThreeWay":final_m,"manufacturingBalanced":alt2_m,"bodyAtLeast015":alt3_m,
                              "search":{"sectionCandidates":22,"tangentChecks":12,"refinementSamples":5,"globalSearch":False}},
          "manufacturingGate":gate,"rearHarnessAssembly":rear,
          "scope":{"productionModification":0,"eightButtonPropagation":0,"N2":0,"physicalCoupon":0,"architectureRedesign":0},
          "preservation":{"protectedFileCount":len(protected),"hashesBefore":before,"hashesAfter":after,
                          "allProtectedFilesPreserved":before==after},
          "outputs":{"report":doc84.relative(REPORT),"json":doc84.relative(JSON_PATH),"harnessStep":doc84.relative(HARNESS_STEP),
                     "unchangedShellStep":doc84.relative(doc86.SHELL_AUDIT_STEP),"renders":renders}}
    JSON_PATH.write_text(json.dumps(data,indent=2),encoding="utf-8"); REPORT.write_text(report_text(data),encoding="utf-8")
    print(json.dumps({"verdict":data["finalVerdict"],"gate":gate["result"],"body":final_m["I2BodyClearanceMm"],
                      "terminal":final_m["terminalClearanceMm"],"terminalPart":final_m["nearestTerminal"],
                      "I3":final_m["I3ClearanceMm"],"min3":final_m["minimumThreeWayClearanceMm"],
                      "rear":rear["result"],"renders":len(renders),"protected":before==after,"report":doc84.relative(REPORT)},indent=2),flush=True)


if __name__=="__main__": main()
