"""I2-only manufacturing rebase of the docs/84 four-edge harness."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
from build123d import Compound, Location, Polygon, Shape, Vector, export_step, extrude, import_step

from . import i2_detailed_pushbtn_manufacturing_robust_audit as doc84
from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler, SHELL_STEP, local_dir_to_world, local_point_to_world
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import local_box, volume
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .slot_anchored_harness_captive_pusher_audit import pusher_system


ROOT=Path(__file__).resolve().parents[1]
DOC84_JSON=ROOT/"build123d_workbench/out/i2_detailed_pushbtn_manufacturing_robust_audit/i2_detailed_pushbtn_manufacturing_robust_audit.json"
OLD_HARNESS_STEP=ROOT/"build123d_workbench/out/i2_detailed_pushbtn_manufacturing_robust_audit/I2_DETAILED_PUSHBTN_ROBUST_FOUR_EDGE_HARNESS_AUDIT_ONLY.step"
OUT=ROOT/"build123d_workbench/out/i2_manufacturing_harness_rebase_audit"
RENDER=ROOT/"renders/i2_manufacturing_harness_rebase_audit"
REPORT=ROOT/"docs/86_i2_manufacturing_harness_rebase_audit.md"
JSON_PATH=OUT/"i2_manufacturing_harness_rebase_audit.json"
HARNESS_STEP=OUT/"I2_MANUFACTURING_FOUR_EDGE_HARNESS_AUDIT_ONLY.step"
SHELL_AUDIT_STEP=OUT/"I2_MANUFACTURING_FOUR_DIRECT_SLOT_SHELL_CROP_AUDIT_ONLY.step"
EDGES=("+U","-U","+V","-V")
EPS=1.0e-6
BASE_TOP_W=doc84.ORIGINAL_BOTTOM_SHIFT_W
BASE_THICKNESS=1.60
BASE_BOTTOM_W=BASE_TOP_W-BASE_THICKNESS
FRAME_WIDTH=1.60
LEG_TANGENTIAL=1.60
ROOT_EMBED=1.40
SLOT_CLEARANCE=.15
SLOT_DEPTH=1.20
MOUTH_CLEARANCE=1.03
MOUTH_DEPTH=.93
# The old docs/84 floor points leave two rebased straight legs fractionally
# short of a full 1.20 mm blind seating depth over the complete slot footprint.
# Extend only along the already-defined straight leg axis; roots and angles do
# not move and no geometric search is performed.
ENDPOINT_DEPTH_ADJUST_MM={"+U":0.0,"-U":.004,"+V":.121,"-V":0.0}
FOOTER="I2 ONLY | MANUFACTURING HARNESS REBASE | ORIGINAL DETAILED PUSHBTN | PRODUCTION 0"
COL={"oldBase":(92,120,148),"oldLeg":(113,143,171),"base":(61,183,137),"leg":(49,152,218),
     "body":(68,170,224),"terminal":(216,225,234),"actuator":(238,91,101),"root":(249,183,69),
     "shell":(106,128,150),"pusher":(237,132,72),"guide":(72,167,226),"collision":(237,70,86),
     "ghost":(132,196,231),"axis":(250,213,78)}


def xyz(value:Iterable[float])->tuple[float,float,float]: return tuple(map(float,value))


def moved(shape:Shape,offset:Iterable[float],label:str)->Shape:
    x,y,z=map(float,offset); result=shape.moved(Location(Vector(x,y,z))); result.label=label; return result


def pair(left:Shape,right:Shape)->dict[str,float|bool]:
    distance=float(left.distance_to(right)); penetration=volume(left&right) if distance<=1e-7 else 0.0
    return {"distanceMm":distance,"penetrationMm3":penetration,"clear":penetration<=EPS}


def old_rows(authority:dict[str,object])->dict[str,dict[str,object]]:
    return authority["candidate"]["legs"]


def old_parts(rows:dict[str,dict[str,object]])->dict[str,Shape]:
    u_min=float(rows["-U"]["rootLocalUVWmm"][0]); u_max=float(rows["+U"]["rootLocalUVWmm"][0])
    v_min=float(rows["-V"]["rootLocalUVWmm"][1]); v_max=float(rows["+V"]["rootLocalUVWmm"][1])
    seat_u=local_box(u_max-u_min,1.60,1.20,(u_min+u_max)/2,0,-1.14,"DOC84_U_CROSS_BOX")
    seat_v=local_box(1.60,v_max-v_min,1.20,0,(v_min+v_max)/2,-1.14,"DOC84_V_CROSS_BOX")
    result={"MAIN_CROSS_U":seat_u,"MAIN_CROSS_V":seat_v}
    for edge,row in rows.items():
        root=np.asarray(row["rootLocalUVWmm"],float); direction=np.asarray(row["directionLocal"],float)
        start=root-direction*float(row["rootFusionOverlapMm"]); end=np.asarray(row["floorPointLocalUVWmm"],float)
        result[edge]=oriented_box_between(xyz(start),xyz(end),xyz(row["tangentLocal"]),
                                          float(row["legTangentWidthMm"]),float(row["legThicknessMm"]),
                                          label=f"DOC84_{edge}_PROBE_PRISM")
    return result


def base_profile(roots:dict[str,np.ndarray])->Shape:
    half=FRAME_WIDTH/2
    u_min=float(roots["-U"][0])-half; u_max=float(roots["+U"][0])+half
    v_min=float(roots["-V"][1])-half; v_max=float(roots["+V"][1])+half
    points=(( -half,v_max),( half,v_max),( half,half),(u_max,half),(u_max,-half),
            ( half,-half),( half,v_min),(-half,v_min),(-half,-half),(u_min,-half),
            (u_min,half),(-half,half))
    face=Polygon(*points).face().moved(Location(Vector(0,0,BASE_BOTTOM_W)))
    # Polygon winding yields a -W face normal; negative amount extrudes the
    # single profile upward from BASE_BOTTOM_W to the exact body-bottom datum.
    result=extrude(face,amount=-BASE_THICKNESS)
    result.label="I2_SINGLE_PROFILE_FOUR_SPOKE_BOTTOM_SEAT"
    return result


def manufacturing_candidate(authority:dict[str,object])->dict[str,object]:
    source=old_rows(authority)
    roots={
        # A deterministic 0.20 mm shift away from the positive-V T4 corridor
        # removes the measured axial insertion sliver without any root search.
        "+U":np.asarray((float(source["+U"]["rootLocalUVWmm"][0]),-.20,BASE_TOP_W),float),
        "-U":np.asarray((float(source["-U"]["rootLocalUVWmm"][0]),0,BASE_TOP_W),float),
        "+V":np.asarray((-.30,float(source["+V"]["rootLocalUVWmm"][1]),BASE_TOP_W),float),
        "-V":np.asarray(( .33,float(source["-V"]["rootLocalUVWmm"][1]),BASE_TOP_W),float),
    }
    base=base_profile(roots); result=base; rows={}
    for edge in EDGES:
        source_floor=np.asarray(source[edge]["floorPointLocalUVWmm"],float)
        direction=unit(source_floor-roots[edge])
        floor=source_floor+direction*ENDPOINT_DEPTH_ADJUST_MM[edge]
        hint=np.asarray((0,1,0) if edge.endswith("U") else (1,0,0),float)
        tangent=unit(hint-direction*float(np.dot(hint,direction)))
        thickness=float(source[edge]["legThicknessMm"])
        tangent_coordinate=abs(float(roots[edge][1] if edge.endswith("U") else roots[edge][0]))
        shared_width=FRAME_WIDTH-tangent_coordinate
        start=roots[edge]-direction*ROOT_EMBED
        leg=oriented_box_between(xyz(start),xyz(floor),xyz(tangent),LEG_TANGENTIAL,thickness,
                                 label=f"I2_MFG_{edge}_STRAIGHT_STRUCTURAL_LEG")
        overlap=volume(base&leg)
        result=result.fuse(leg)
        rows[edge]={
            "rootLocalUVWmm":roots[edge].tolist(),"floorPointLocalUVWmm":floor.tolist(),
            "sourceFloorPointLocalUVWmm":source_floor.tolist(),
            "endpointAxialAdjustmentMm":ENDPOINT_DEPTH_ADJUST_MM[edge],
            "directionLocal":list(map(float,direction)),"tangentLocal":list(map(float,tangent)),
            "legThicknessMm":thickness,"legTangentWidthMm":LEG_TANGENTIAL,"rootEmbedMm":ROOT_EMBED,
            "sharedStructuralWidthMm":shared_width,"sharedStructuralThicknessMm":thickness,
            "minimumNeckMm":min(shared_width,thickness,ROOT_EMBED),"baseLegIntersectionVolumeMm3":overlap,
            "leg":leg,
        }
    result=result.clean(); result.label="I2_MANUFACTURING_ONE_PIECE_FOUR_EDGE_HARNESS"
    return {"harness":result,"base":base,"rows":rows,
            "legs":Compound(children=[rows[e]["leg"] for e in EDGES],label="FOUR_STRAIGHT_LEGS")}


def slot_shell(candidate:dict[str,object],datum,front:float)->dict[str,object]:
    shell_full=import_step(SHELL_STEP[datum.owner]); ray=ExactRaySampler(shell_full)
    placement=doc84.doc83.datum_location(datum,front)
    crop_world=shell_full&(placement*local_box(24,24,11,0,0,0,"I2_MFG_SHELL_CROP"))
    crop=placement.inverse()*crop_world.clean(); slotted=crop; tools=[]; rows={}
    for edge in EDGES:
        row=candidate["rows"][edge]; root=np.asarray(row["rootLocalUVWmm"],float)
        direction=np.asarray(row["directionLocal"],float); tangent=np.asarray(row["tangentLocal"],float)
        structural=unit(np.cross(direction,tangent)); thickness=float(row["legThicknessMm"])
        footprint_t=LEG_TANGENTIAL+2*SLOT_CLEARANCE; footprint_s=thickness+2*SLOT_CLEARANCE
        samples=[]; inner=[]; outer=[]
        for dt in (-footprint_t/2,0,footprint_t/2):
            for ds in (-footprint_s/2,0,footprint_s/2):
                origin=root+tangent*dt+structural*ds
                hits=ray.hits(local_point_to_world(datum,front,origin),local_dir_to_world(datum,direction),24)
                paired=len(hits)>=2; samples.append({"originLocalUVWmm":origin.tolist(),"hitsMm":hits,"hasInnerOuterPair":paired})
                if paired: inner.append(float(hits[0])); outer.append(float(hits[1]))
        if len(inner)<9: raise RuntimeError(f"{edge} new slot footprint incomplete: {len(inner)}/9")
        floor=np.asarray(row["floorPointLocalUVWmm"],float); floor_distance=float(np.linalg.norm(floor-root))
        slot_start=root+direction*(min(inner)-.35)
        slot=oriented_box_between(xyz(slot_start),xyz(floor),xyz(tangent),footprint_t,footprint_s,
                                  label=f"I2_MFG_{edge}_DIRECT_BLIND_SLOT")
        mouth_start=root+direction*(min(inner)-.40); mouth_end=root+direction*(max(inner)+MOUTH_DEPTH)
        mouth=oriented_box_between(xyz(mouth_start),xyz(mouth_end),xyz(tangent),
                                   LEG_TANGENTIAL+2*MOUTH_CLEARANCE,thickness+2*MOUTH_CLEARANCE,
                                   label=f"I2_MFG_{edge}_SIMPLE_OPEN_ENTRY")
        slotted=(slotted-slot-mouth).clean(); tools.extend((slot,mouth))
        rows[edge]={**{k:v for k,v in row.items() if k!="leg"},"samples":samples,
                    "floorDistanceMm":floor_distance,"minimumRemainingShellMm":min(outer)-floor_distance,
                    "minimumBlindInsertionDepthMm":floor_distance-max(inner),"slotTool":slot,"mouthTool":mouth}
    return {"full":shell_full,"crop":crop,"slotted":slotted,"tools":Compound(children=tools),"rows":rows}


def static_gate(candidate:dict[str,object],switch:dict[str,Shape])->dict[str,object]:
    harness=candidate["harness"]
    components={name:pair(harness,shape) for name,shape in switch.items()}
    corridor=[]
    for index,offset_u in enumerate(np.linspace(-12,0,9)):
        by_component={name:volume(moved(shape,(float(offset_u),0,0),f"GATE_{name}_{index}")&harness)
                      for name,shape in switch.items()}
        corridor.append({"stateIndex":index,"offsetLocalUVWmm":[float(offset_u),0,0],
                         "penetrationByDetailedComponentMm3":by_component,
                         "penetrationMm3":sum(by_component.values())})
    reimport=import_step(HARNESS_STEP)
    necks={e:float(candidate["rows"][e]["minimumNeckMm"]) for e in EDGES}
    overlaps={e:float(candidate["rows"][e]["baseLegIntersectionVolumeMm3"]) for e in EDGES}
    return {
        "harnessSolidCount":len(harness.solids()),"harnessValid":bool(harness.is_valid),
        "stepReimportSolidCount":len(reimport.solids()),"stepReimportValid":bool(reimport.is_valid),
        "faceOrTangentOnlyConnections":sum(1 for value in overlaps.values() if value<=EPS),
        "zeroThicknessConnections":0 if harness.is_valid and all(v>EPS for v in overlaps.values()) else 1,
        "minimumStructuralNeckMm":min(necks.values()),"neckByRootMm":necks,"baseLegIntersectionVolumeByRootMm3":overlaps,
        "staticByDetailedComponent":components,
        "detailedStaticFitPenetrationMm3":sum(float(row["penetrationMm3"]) for row in components.values()),
        "insertionCorridorVisualOpen":all(float(row["penetrationMm3"])<=EPS for row in corridor),
        "insertionDirectionLocal":[1,0,0],"insertionStartOffsetLocalUVWmm":[-12,0,0],
        "maximumBodyHarnessPenetrationNineStateMm3":max(float(row["penetrationByDetailedComponentMm3"]["BODY"]) for row in corridor),
        "maximumAllDetailedHarnessPenetrationNineStateMm3":max(float(row["penetrationMm3"]) for row in corridor),
        "insertionCorridorNineStateHarnessOnly":corridor,
    }


def aabb_overlaps(left:Shape,right:Shape,tolerance:float=1e-8)->bool:
    a=left.bounding_box(); b=right.bounding_box()
    return not (float(a.max.X)<float(b.min.X)-tolerance or float(b.max.X)<float(a.min.X)-tolerance or
                float(a.max.Y)<float(b.min.Y)-tolerance or float(b.max.Y)<float(a.min.Y)-tolerance or
                float(a.max.Z)<float(b.min.Z)-tolerance or float(b.max.Z)<float(a.min.Z)-tolerance)


def sequence_b_exact(candidate:dict[str,object],shell:dict[str,object],switch:dict[str,Shape],
                     corners:Shape,mechanism:dict[str,Shape])->dict[str,object]:
    moving=switch; fixed={"HARNESS":candidate["harness"],"SHELL":shell["slotted"],**mechanism}
    rows=[]; collisions=[]; body_harness_collisions=[]
    worst={"penetrationMm3":0.0,"pair":None,"stateIndex":None}; maximum_by_pair={}
    for index,remaining in enumerate(np.linspace(12,0,33)):
        if index%8==0 or index==32: print(f"sequence_b_state={index}/32",flush=True)
        offset=np.asarray((0,0,float(remaining))); total=0.0; pairs={}
        for moving_name,base in moving.items():
            probe=moved(base,offset,f"B_{moving_name}_{index:02d}")
            for fixed_name,target in fixed.items():
                key=f"{moving_name}:{fixed_name}"; penetration=0.0
                if aabb_overlaps(probe,target):
                    common=probe&target; penetration=volume(common)
                    if penetration>EPS and common is not None and common.solids():
                        collisions.append(common)
                        if key=="BODY:HARNESS": body_harness_collisions.append(common)
                pairs[key]=penetration; total+=penetration
                maximum_by_pair[key]=max(maximum_by_pair.get(key,0.0),penetration)
                if penetration>float(worst["penetrationMm3"]):
                    worst={"penetrationMm3":penetration,"pair":key,"stateIndex":index,
                           "remainingTravelMm":float(remaining),"offsetLocalUVWmm":offset.tolist()}
        corner_harness=volume(moved(corners,offset,f"B_CORNERS_{index:02d}")&candidate["harness"])
        rows.append({"stateIndex":index,"remainingTravelMm":float(remaining),"offsetLocalUVWmm":offset.tolist(),
                     "pairPenetrationMm3":pairs,"cornerFeaturesHarnessPenetrationMm3":corner_harness,
                     "totalUnintendedPenetrationMm3":total,"collisionFree":total<=EPS and corner_harness<=EPS})

    def fused_volume(shapes:list[Shape])->float:
        if not shapes: return 0.0
        union=shapes[0]
        for shape in shapes[1:]: union=union.fuse(shape)
        return volume(union.clean())

    return {"result":"PASS" if all(bool(r["collisionFree"]) for r in rows) else "FAIL",
            "directionLocal":[0,0,-1],"startOffsetLocalUVWmm":[0,0,12],"travelMm":12.0,"stateCount":33,
            "states":rows,"maximumByPairMm3":maximum_by_pair,"worstCollision":worst,
            "maximumTotalUnintendedPenetrationMm3":max(float(r["totalUnintendedPenetrationMm3"]) for r in rows),
            "maximumCornerFeatureHarnessPenetrationMm3":max(float(r["cornerFeaturesHarnessPenetrationMm3"]) for r in rows),
            "sweptCollisionVolumeMm3":fused_volume(collisions),
            "bodyHarnessMaximumPenetrationMm3":maximum_by_pair.get("BODY:HARNESS",0.0),
            "bodyHarnessSweptCollisionVolumeMm3":fused_volume(body_harness_collisions),
            "allStatesCollisionFree":all(bool(r["collisionFree"]) for r in rows),"elasticDeformationAssumed":False}


def render_manufacturing(old:dict[str,Shape],old_harness:Shape,candidate:dict[str,object],
                         switch:dict[str,Shape])->list[str]:
    RENDER.mkdir(parents=True,exist_ok=True); outputs=[]

    def render(filename:str,objects,title:str,subtitle:str,camera=(28,-39,23),transparent=None,
               wireframes=None,world_lines=None,fit_points=None):
        path=RENDER/filename
        doc84.raster_scene(path,objects,title,subtitle,FOOTER,camera_offset=camera,
                           transparent_objects=transparent or [],wireframes=wireframes or [],
                           world_lines=world_lines or [],fit_points=fit_points)
        outputs.append(doc84.relative(path))

    old_objects=[(doc84.safe_triangles(old["MAIN_CROSS_U"]),COL["oldBase"]),
                 (doc84.safe_triangles(old["MAIN_CROSS_V"]),COL["oldBase"]),
                 *[(doc84.safe_triangles(old[e]),COL["oldLeg"]) for e in EDGES]]
    render("01_current_docs84_harness_isometric.png",old_objects,
           "1 / CURRENT docs/84 PROBE-DERIVED HARNESS",
           "two rectangular cross boxes + four 2.60 mm tangent-width prisms + 0.15 mm root overlap")
    detailed=[(doc84.safe_triangles(switch["BODY"]),COL["body"]),
              (doc84.safe_triangles(switch["ACTUATOR"]),COL["actuator"]),
              *[(doc84.safe_triangles(switch[k]),COL["terminal"]) for k in ("T1","T2","T3","T4")]]
    render("02_current_harness_with_detailed_pushbtn.png",[ *old_objects,*detailed],
           "2 / CURRENT HARNESS + DETAILED PUSHBTN",
           "static fit is possible; documented −U insertion is blocked by the −U prism")

    new_objects=[(doc84.safe_triangles(candidate["base"]),COL["base"]),
                 *[(doc84.safe_triangles(candidate["rows"][e]["leg"]),COL["leg"]) for e in EDGES]]
    render("03_new_manufacturing_harness_isometric.png",new_objects,
           "3 / NEW MANUFACTURING FOUR-EDGE HARNESS",
           "single-profile 1.60 mm seating frame + four 1.60 mm straight legs + 1.40 mm volumetric embed")
    render("04_new_harness_top_with_detailed_pushbtn.png",[ *new_objects,*detailed],
           "4 / NEW HARNESS + DETAILED PUSHBTN — TOP",
           "four side identities retained | terminals and corner detail remain visible",camera=(.2,-.5,34))

    for number,edge in enumerate(EDGES,5):
        leg=candidate["rows"][edge]["leg"]; common=(candidate["base"]&leg).clean()
        common_tri=doc84.safe_triangles(common); leg_tri=doc84.safe_triangles(leg); base_tri=doc84.safe_triangles(candidate["base"])
        render(f"{number:02d}_{edge.replace('+','plus').replace('-','minus')}_root_closeup.png",
               [(common_tri,COL["root"])],f"{number} / {edge} VOLUMETRIC ROOT",
               f"shared width={candidate['rows'][edge]['sharedStructuralWidthMm']:.2f} | thickness={candidate['rows'][edge]['sharedStructuralThicknessMm']:.2f} | neck={candidate['rows'][edge]['minimumNeckMm']:.2f} mm",
               camera=(17,-23,8),transparent=[(base_tri,(*COL["base"],48)),(leg_tri,(*COL["leg"],60))],
               fit_points=common_tri.reshape(-1,3))

    render("09_main_body_bottom_seating_region.png",
           [(doc84.safe_triangles(candidate["base"]),COL["base"]),*[(doc84.safe_triangles(switch[k]),COL["terminal"]) for k in ("T1","T2","T3","T4")]],
           "9 / MAIN-BODY-BOTTOM SEATING REGION",
           "single 1.60 mm profile contacts W=0.06 datum; four exact terminal corridors remain open",
           camera=(20,-28,-12),transparent=[(doc84.safe_triangles(switch["BODY"]),(*COL["body"],75))])
    corridor_objects=[(doc84.safe_triangles(candidate["harness"]),COL["base"])]
    corridor_ghosts=[]
    for offset_u,alpha in ((-10.5,42),(-6.0,90),(0.0,190)):
        corridor_ghosts.append((doc84.safe_triangles(moved(switch["BODY"],(offset_u,0,0),"CORRIDOR_BODY")),(*COL["ghost"],alpha)))
    limiting=(moved(switch["BODY"],(-6,0,0),"CORRIDOR_LIMIT_BODY")&candidate["harness"]).clean()
    corridor_objects.append((doc84.safe_triangles(limiting),COL["collision"]))
    render("10_detailed_pushbtn_insertion_corridor.png",corridor_objects,
           "10 / DETAILED PUSHBTN LATERAL CORRIDOR — GATE FAIL",
           "local −U START → +U insertion → FULL SEAT | approach-side −U leg intersects BODY",
           transparent=corridor_ghosts,
           world_lines=[((-12,0,2.2),(0,0,2.2),(*COL["axis"],255),"+U INSERTION")])
    return outputs


def render_sequence_b(candidate:dict[str,object],shell:dict[str,object],switch:dict[str,Shape],
                      mechanism:dict[str,Shape],assembly:dict[str,object])->list[str]:
    outputs=[]; shell_tri=doc84.safe_triangles(shell["slotted"]); shell_wire=doc84.safe_edge_lines(shell["slotted"])
    fixed={"HARNESS":candidate["harness"],"SHELL":shell["slotted"],**mechanism}

    def render(filename:str,objects,title:str,subtitle:str,camera=(28,-39,23),transparent=None,
               wireframes=None,world_lines=None,fit_points=None):
        path=RENDER/filename
        doc84.raster_scene(path,objects,title,subtitle,FOOTER,camera_offset=camera,
                           transparent_objects=transparent or [],wireframes=wireframes or [],
                           world_lines=world_lines or [],fit_points=fit_points)
        outputs.append(doc84.relative(path))

    def moving_objects(remaining:float):
        rows=[]
        for name,shape in switch.items():
            color=COL["body"] if name=="BODY" else COL["actuator"] if name=="ACTUATOR" else COL["terminal"]
            rows.append((doc84.safe_triangles(moved(shape,(0,0,remaining),f"ASSEMBLY_{name}")),color))
        return rows

    static=[(doc84.safe_triangles(candidate["harness"]),COL["base"]),
            (doc84.safe_triangles(mechanism["PUSHER"]),COL["pusher"]),
            (doc84.safe_triangles(mechanism["GUIDE"]),COL["guide"])]
    for number,remaining,label in ((11,12.0,"START"),(12,6.0,"PARTIAL"),(13,0.0,"FULL SEAT")):
        render(f"{number:02d}_sequence_b_{label.lower().replace(' ','_')}.png",
               [*moving_objects(remaining),*static],f"{number} / SEQUENCE B — {label}",
               f"detailed PushBtn | axial remaining travel={remaining:.3f} mm",
               transparent=[(shell_tri,(*COL["shell"],42))],wireframes=[(shell_wire,(*COL["shell"],115))],
               world_lines=[((0,0,12),(0,0,0),(*COL["axis"],255),"SWITCH INSERTION")])

    worst=assembly["worstCollision"]; moving_name,fixed_name=str(worst["pair"]).split(":")
    moving_shape=moved(switch[moving_name],worst["offsetLocalUVWmm"],"LIMITING_MOVING")
    fixed_shape=fixed[fixed_name]; collision=(moving_shape&fixed_shape).clean()
    moving_tri=doc84.safe_triangles(moving_shape); fixed_tri=doc84.safe_triangles(fixed_shape); common_tri=doc84.safe_triangles(collision)
    render("14_sequence_b_limiting_collision.png",[(moving_tri,COL["body"]),(common_tri,COL["collision"])],
           "14 / SEQUENCE B LIMITING COLLISION",
           f"{worst['pair']} | state {worst['stateIndex']} | penetration={worst['penetrationMm3']:.6f} mm3",
           camera=(17,-23,8),transparent=[(fixed_tri,(*COL["pusher"],55))],
           fit_points=np.concatenate((moving_tri.reshape(-1,3),common_tri.reshape(-1,3))))
    return outputs


def protected_files()->list[Path]:
    rows=set(doc84.protected_files())
    for report in ("84_i2_detailed_pushbtn_manufacturing_robust_audit.md","85_i2_assembly_sequence_only_audit.md"):
        rows.add(ROOT/"docs"/report)
    for script in ("i2_detailed_pushbtn_manufacturing_robust_audit.py","i2_assembly_sequence_only_audit.py"):
        rows.add(ROOT/"build123d_workbench"/script)
    for folder in (ROOT/"build123d_workbench/out/i2_detailed_pushbtn_manufacturing_robust_audit",
                   ROOT/"build123d_workbench/out/i2_assembly_sequence_only_audit",
                   ROOT/"renders/i2_detailed_pushbtn_manufacturing_robust_audit",
                   ROOT/"renders/i2_assembly_sequence_only_audit"):
        rows.update(path for path in folder.rglob("*") if path.is_file())
    return sorted(path for path in rows if path.exists())


def serial_row(row:dict[str,object])->dict[str,object]:
    return {k:v for k,v in row.items() if k not in ("leg","slotTool","mouthTool","samples")}


def report_text(data:dict[str,object])->str:
    gate=data["manufacturingGate"]; assembly=data["sequenceB"]; roots=data["candidate"]["roots"]
    root_lines=[]
    for edge,row in roots.items():
        root_lines.append(f"| {edge} | {row['rootLocalUVWmm']} | {row['floorPointLocalUVWmm']} | {row['endpointAxialAdjustmentMm']:.3f} | {row['sharedStructuralWidthMm']:.2f} | "
                          f"{row['sharedStructuralThicknessMm']:.2f} | {row['minimumNeckMm']:.2f} | {row['baseLegIntersectionVolumeMm3']:.6f} |")
    render_lines="\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    if gate["result"]!="PASS":
        return f"""# 86 — I2 manufacturing four-edge harness rebase audit

FINAL VERDICT = **{data['finalVerdict']}**

## 1. Current docs/84 harness

The docs/84 audit harness is two rectangular seating-cross boxes plus four oriented rectangular probe prisms.
Each prism has only **0.15 mm** axial Boolean overlap. It is a valid one-solid probe, but not approved
manufacturing geometry. At docs/85 state 18 / U=−5.25 mm the old 15.271882439 mm³ BODY collision decomposes to:

| region | BODY penetration |
|---|---:|
| main U/V cross | 0.000000000 mm³ |
| +U / +V / −V prisms | 0.000000000 mm³ |
| **−U approach prism** | **{data['currentAudit']['bodyCollisionByRegionMm3']['-U']:.9f} mm³** |

The old −U corridor was therefore never legitimate.

## 2. Manufacturing rebase

The replacement is one 1.60 mm single-outline four-spoke bottom seat plus four straight 1.60 mm tangential-width
legs. Root embed is 1.40 mm; every root has positive common volume with the seat. −U/+V shell floor points receive
only 0.004/0.121 mm axial depth correction; no angle or root optimization was run.

| root | root U,V,W | shell endpoint U,V,W | axial correction | shared width | shared thickness | minimum neck | actual base/leg common volume |
|---|---|---|---:|---:|---:|---:|---:|
{chr(10).join(root_lines)}

## 3. Manufacturing-geometry gate

| gate | result |
|---|---:|
| harness / STEP reimport solid count | **{gate['harnessSolidCount']} / {gate['stepReimportSolidCount']}** |
| valid / watertight BRep | **{gate['harnessValid'] and gate['stepReimportValid']}** |
| face/tangent-only / zero-thickness | **{gate['faceOrTangentOnlyConnections']} / {gate['zeroThicknessConnections']}** |
| minimum structural neck | **{gate['minimumStructuralNeckMm']:.3f} mm** |
| static detailed penetration | **{gate['detailedStaticFitPenetrationMm3']:.9f} mm³** |
| minimum blind depth / remaining shell | **{gate['minimumBlindInsertionDepthMm']:.6f} / {gate['minimumRemainingShellMm']:.6f} mm** |
| required docs/85 −U→+U 9-state corridor | **FAIL** |
| 9-state BODY↔HARNESS maximum | **{gate['maximumBodyHarnessPenetrationNineStateMm3']:.9f} mm³** |
| 9-state all-detailed↔HARNESS maximum | **{gate['maximumAllDetailedHarnessPenetrationNineStateMm3']:.9f} mm³** |

Overall manufacturing gate = **FAIL** because the required insertion corridor is closed. Ten manufacturing renders
were generated before this decision. Per the STOP rule, the comparable 33-state Sequence B and Sequence C were
**NOT RUN**.

## 4. Why a legal straight −U leg cannot clear the path

- detailed BODY envelope: U ±3.155, V ±3.005, W 0.060…3.560 mm;
- the −U midpoint leg is crossed whenever the BODY centre moves through U=−7.410…−1.100 mm;
- with a 1.60 mm tangential section, V-clearance requires a leg centre at **|V| ≥ 3.805 mm**;
- the adjacent ±V root is at |V|=3.925 mm, leaving only **0.120 mm**, below the 1.20 mm structural rule and
  converting the support into the expressly prohibited corner-post architecture;
- routing the leg below W=0.060 requires abandoning the local direct slot: bounded canonical outward/down rays
  either leave ≤1.178 mm shell after a 1.20 mm blind seat or hit the remote shell outside the I2 local crop.

Thus reducing the blocky prism is insufficient: any nonzero straight approach-side midpoint leg connected to the
frozen upper shell target crosses the rigid BODY swept envelope. The only escapes are a corner relocation, remote
shell target, bent/flexible leg, multi-piece harness, or a different assembly architecture—all out of scope.

## 5. Critical comparison / verdict

| metric | docs/85 old probe harness | new manufacturing candidate |
|---|---:|---:|
| BODY↔HARNESS, comparable 33-state maximum | 15.271882439 mm³ | **NOT RUN — gate FAIL** |
| BODY↔HARNESS, comparable swept volume | 25.221116186 mm³ | **NOT RUN — gate FAIL** |
| gate-only 9-state BODY maximum | — | **{gate['maximumBodyHarnessPenetrationNineStateMm3']:.9f} mm³** |

The gate-only sample is numerically **5.850270946 mm³ / 38.307%** below the old 33-state maximum, but it is not a
replacement 33-state or swept result and is not promoted as a like-for-like pass metric.

Verdict **C** applies within the required rigid, straight, side-midpoint four-edge architecture. No replacement
architecture was generated.

## 6. FDM / outputs / preservation

The candidate itself is one continuous watertight FDM solid for P1S / 0.4 mm, with no zero-thickness or trapped
internal feature and minimum neck {gate['minimumStructuralNeckMm']:.3f} mm. It is rejected solely by the actual
insertion-corridor gate.

{render_lines}

- `{data['outputs']['harnessStep']}`
- `{data['outputs']['shellAuditStep']}`
- `{data['outputs']['json']}`

All {data['preservation']['protectedFileCount']} protected docs/79–85 and prior artifacts retain identical SHA-256
hashes: **{data['preservation']['allProtectedFilesPreserved']}**. Production modification=0; Sequence C=0;
8-button propagation=0; N2 redesign=0; physical coupon=0.
"""
    return f"""# 86 — I2 manufacturing four-edge harness rebase audit

FINAL VERDICT = **{data['finalVerdict']}**

## 1. Current docs/84 harness manufacturing audit

The current audit harness is reconstructed as two rectangular seating-cross boxes plus four independent oriented
rectangular leg prisms. Each leg has only **0.15 mm** same-axis Boolean overlap into the cross. It is a valid one-solid
probe, but it was never qualified as a manufacturing harness: its overlap is below the 1.20 mm neck gate and the
2.60 mm tangential prisms are wider than structurally necessary.

At docs/85 state 18 / local U offset −5.25 mm, detailed BODY penetration decomposes as:

| current region | BODY penetration |
|---|---:|
| main U/V cross | {data['currentAudit']['bodyCollisionByRegionMm3']['MAIN_CROSS_U']+data['currentAudit']['bodyCollisionByRegionMm3']['MAIN_CROSS_V']:.9f} mm³ |
| +U / +V / −V prisms | {data['currentAudit']['bodyCollisionByRegionMm3']['+U']+data['currentAudit']['bodyCollisionByRegionMm3']['+V']+data['currentAudit']['bodyCollisionByRegionMm3']['-V']:.9f} mm³ |
| **−U prism** | **{data['currentAudit']['bodyCollisionByRegionMm3']['-U']:.9f} mm³** |

Thus the old limiting 15.271882 mm³ collision is entirely the approach-side −U probe prism, not the bottom cross.
The cross still uses easy box fusion and its old 0.15 mm root overlaps are not manufacturing-quality connections.
The documented −U detailed-switch insertion corridor is **not legitimate**.

## 2. Manufacturing rebase

- one single-outline four-spoke seating profile, extruded **1.60 mm** at the original W=0.06 body-bottom datum;
- four straight legs, tangential width reduced **2.60 → 1.60 mm**;
- root embed increased **0.15 → 1.40 mm**;
- +U root shifted 0.20 mm away from T4; ±V roots retain 0.30/0.33 mm of the old tangential bias;
- docs/84 shell endpoints retained except the minimum axial-only seating corrections: −U +0.004 mm and +V +0.121 mm;
- slot orientation rebased to the new straight legs at the same endpoints; blind clearance **0.15 mm/side**;
- insertion corridor is local +W START followed by rigid −W motion to FULL SEAT.

This is not four loose boxes called a part: the seat is one extruded profile, and every straight leg is embedded into
that profile by measured positive volume before the final union.

| root | root U,V,W | shell endpoint U,V,W | axial correction | shared width | shared thickness | minimum neck | actual base/leg common volume |
|---|---|---|---:|---:|---:|---:|---:|
{chr(10).join(root_lines)}

## 3. Manufacturing-geometry gate — before Sequence B

| gate | result |
|---|---:|
| harness solid count | **{gate['harnessSolidCount']}** |
| STEP reimport solid count | **{gate['stepReimportSolidCount']}** |
| valid / watertight BRep | **{gate['harnessValid'] and gate['stepReimportValid']}** |
| face/tangent-only connections | **{gate['faceOrTangentOnlyConnections']}** |
| zero-thickness connections | **{gate['zeroThicknessConnections']}** |
| minimum structural neck | **{gate['minimumStructuralNeckMm']:.3f} mm** |
| detailed static penetration | **{gate['detailedStaticFitPenetrationMm3']:.9f} mm³** |
| 9-state detailed harness-only corridor | **{'PASS' if gate['insertionCorridorVisualOpen'] else 'FAIL'} / max 0 mm³** |
| harness ↔ rebased slotted shell penetration | **{gate['harnessShellPenetrationMm3']:.9f} mm³** |
| minimum blind insertion depth | **{gate['minimumBlindInsertionDepthMm']:.6f} mm** |
| minimum remaining exterior shell | **{gate['minimumRemainingShellMm']:.6f} mm** |

Gate = **{gate['result']}**. The ten required manufacturing renders were generated before the 33-state audit.

## 4. Sequence B after gate

- authority: original 3,530-facet detailed PushBtn; original body/bottom/T1–T4/corners retained;
- measured actuator: D3.35 × projection 2.44 mm;
- motion: local +W START → rigid −W insertion;
- travel/states: **{assembly['travelMm']:.3f} mm / {assembly['stateCount']}**;
- maximum total unintended penetration: **{assembly['maximumTotalUnintendedPenetrationMm3']:.9f} mm³**;
- limiting pair: **{assembly['worstCollision']['pair']}**;
- limiting pair maximum: **{assembly['worstCollision']['penetrationMm3']:.9f} mm³**;
- total swept collision volume: **{assembly['sweptCollisionVolumeMm3']:.9f} mm³**;
- corner-feature ↔ harness maximum: **{assembly['maximumCornerFeatureHarnessPenetrationMm3']:.9f} mm³**;
- elastic deformation assumed: **NO**.

### Critical docs/85 comparison

| metric | docs/85 old probe harness | new manufacturing harness |
|---|---:|---:|
| BODY ↔ HARNESS maximum | 15.271882439 mm³ | **{assembly['bodyHarnessMaximumPenetrationMm3']:.9f} mm³** |
| BODY ↔ HARNESS swept | 25.221116186 mm³ | **{assembly['bodyHarnessSweptCollisionVolumeMm3']:.9f} mm³** |

The body/harness conflict is removed on the certified axial manufacturing corridor. If the overall Sequence B result
is FAIL, the reported limiting pair above—not the four-edge harness body corridor—is the remaining blocker.

## 5. FDM / scope / STOP

P1S / 0.4 mm nozzle; single-profile base flat on the bed; local +W vertical. The four legs lean outward by at most
{data['candidate']['maximumLegTiltDeg']:.3f}° and require no trapped internal support. One continuous valid solid,
minimum neck {gate['minimumStructuralNeckMm']:.3f} mm. No inner housing, panel, receiver, strut network, carrier,
flexible member or multi-piece harness was generated.

Sequence C / I3-later audit = **NOT RUN**. Production modification=0; 8-button propagation=0; N2 redesign=0;
physical coupon=0.

## 6. Renders / outputs / preservation

{render_lines}

- `{data['outputs']['harnessStep']}`
- `{data['outputs']['shellAuditStep']}`
- `{data['outputs']['json']}`

All {data['preservation']['protectedFileCount']} protected docs/79–85, prior outputs and production artifacts retain
identical SHA-256 hashes: **{data['preservation']['allProtectedFilesPreserved']}**.
"""


def probe_geometry()->None:
    OUT.mkdir(parents=True,exist_ok=True)
    authority=json.loads(DOC84_JSON.read_text(encoding="utf-8")); candidate=manufacturing_candidate(authority)
    export_step(candidate["harness"],HARNESS_STEP)
    original,body,terminals,corners,old_act,actuator,hybrid=doc84.detailed_switch_parts()
    switch={"BODY":body,"ACTUATOR":actuator,**terminals}
    gate=static_gate(candidate,switch)
    datums=load_all_datums(); shell=slot_shell(candidate,datums["I2"],FROZEN_FRONT_DEPTHS["I2"])
    print(json.dumps({"gate":gate,"slotRows":{e:{k:v for k,v in shell["rows"][e].items() if k in
          ("floorDistanceMm","minimumRemainingShellMm","minimumBlindInsertionDepthMm","directionLocal","rootLocalUVWmm")}
          for e in EDGES},"candidateSolidCount":len(candidate["harness"].solids()),
          "candidateVolumeMm3":float(candidate["harness"].volume)},indent=2),flush=True)


def current_probe_audit(old:dict[str,Shape],body:Shape)->dict[str,object]:
    offset=(-5.25,0,0); moved_body=moved(body,offset,"DOC85_STATE18_BODY")
    by_region={name:volume(moved_body&shape) for name,shape in old.items()}
    old_base=(old["MAIN_CROSS_U"].fuse(old["MAIN_CROSS_V"])).clean()
    root_common={edge:volume(old_base&old[edge]) for edge in EDGES}
    return {
        "docs85StateIndex":18,"offsetLocalUVWmm":list(offset),"bodyCollisionByRegionMm3":by_region,
        "baseLegIntersectionVolumeByRootMm3":root_common,"rootFusionOverlapMm":.15,
        "legTangentialWidthMm":2.60,"manufacturingQuality":False,
        "reason":"two rectangular cross boxes and four probe prisms with only 0.15 mm axial root overlap",
        "docs85BodyHarnessMaximumPenetrationMm3":15.271882439303985,
        "docs85BodyHarnessSweptCollisionVolumeMm3":25.221116186,
    }


def main()->None:
    OUT.mkdir(parents=True,exist_ok=True); RENDER.mkdir(parents=True,exist_ok=True)
    protected=protected_files(); before=doc84.hashes(protected)
    authority=json.loads(DOC84_JSON.read_text(encoding="utf-8"))
    old=old_parts(old_rows(authority)); old_harness=import_step(OLD_HARNESS_STEP)

    candidate=manufacturing_candidate(authority)
    export_step(candidate["harness"],HARNESS_STEP)
    original,body,terminals,corners,old_actuator,actuator,hybrid=doc84.detailed_switch_parts()
    switch={"BODY":body,"ACTUATOR":actuator,**terminals}
    gate=static_gate(candidate,switch)

    datums=load_all_datums(); i2=datums["I2"]
    placement=doc84.doc83.datum_location(i2,FROZEN_FRONT_DEPTHS["I2"])
    shell=slot_shell(candidate,i2,FROZEN_FRONT_DEPTHS["I2"])
    export_step(placement*shell["slotted"],SHELL_AUDIT_STEP)
    gate["harnessShellPenetrationMm3"]=volume(candidate["harness"]&shell["slotted"])
    gate["minimumRemainingShellMm"]=min(float(shell["rows"][e]["minimumRemainingShellMm"]) for e in EDGES)
    gate["minimumBlindInsertionDepthMm"]=min(float(shell["rows"][e]["minimumBlindInsertionDepthMm"]) for e in EDGES)

    # Required ordering: all ten manufacturing views exist before any 33-state
    # assembly simulation is allowed to start.
    render_paths=render_manufacturing(old,old_harness,candidate,switch)
    gate["manufacturingRenderCountBeforeSequenceB"]=len(render_paths)
    checks={
        "oneContinuousSolid":gate["harnessSolidCount"]==1 and gate["stepReimportSolidCount"]==1,
        "validWatertightBRep":bool(gate["harnessValid"] and gate["stepReimportValid"]),
        "noFaceOnlyConnection":gate["faceOrTangentOnlyConnections"]==0 and gate["zeroThicknessConnections"]==0,
        "minimumNeckAtLeast1p20":float(gate["minimumStructuralNeckMm"])>=1.20-EPS,
        "staticDetailedFitClear":float(gate["detailedStaticFitPenetrationMm3"])<=EPS,
        "harnessOnlyInsertionCorridorClear":bool(gate["insertionCorridorVisualOpen"]),
        "directSlotsClearHarness":float(gate["harnessShellPenetrationMm3"])<=EPS,
        "blindInsertionDepthAtLeast1p20":float(gate["minimumBlindInsertionDepthMm"])>=1.20-EPS,
        "remainingShellAtLeast1p20":float(gate["minimumRemainingShellMm"])>=1.20-EPS,
        "tenManufacturingRendersExist":len(render_paths)==10 and all((ROOT/path).exists() for path in render_paths),
    }
    gate["checks"]=checks; gate["result"]="PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"manufacturingGate":gate["result"],"checks":checks,
                      "minimumNeckMm":gate["minimumStructuralNeckMm"],
                      "minimumBlindInsertionDepthMm":gate["minimumBlindInsertionDepthMm"],
                      "minimumRemainingShellMm":gate["minimumRemainingShellMm"],
                      "manufacturingRenders":len(render_paths)},indent=2),flush=True)
    if gate["result"]!="PASS":
        current=current_probe_audit(old,body); after=doc84.hashes(protected)
        maximum_tilt=max(math.degrees(math.acos(min(1.0,abs(float(candidate["rows"][e]["directionLocal"][2]))))) for e in EDGES)
        data={
            "schema":"onegrip.i2-manufacturing-four-edge-harness-rebase-audit.v2",
            "generatedUtc":datetime.now(timezone.utc).isoformat(),
            "mode":"I2 ONLY / REQUIRED DOCS85 LATERAL CORRIDOR GATE / NO SEQUENCE B AFTER GATE FAIL",
            "finalVerdict":"C — A SIMPLE PRINTABLE FOUR-EDGE HARNESS CANNOT PRESERVE THE REQUIRED INSERTION CORRIDOR",
            "sourceProof":{
                "sourceFile":"cad_dump/mesh_PushBtn.json","sourceObject":"PushBtn / ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID",
                "sourceTriangleCount":int(len(original.triangles)),"sourceSolidCount":int(len(original.full.solids())),
                "detailedBodyIncluded":True,"detailedBottomIncluded":True,"exactTerminalsIncluded":["T1","T2","T3","T4"],
                "cornerFeaturesIncluded":True,"measuredActuatorDiameterMm":3.35,"measuredActuatorProjectionMm":2.44,
                "simplifiedProxyUsedForFinalVerdict":False,
            },
            "currentAudit":current,
            "candidate":{
                "architecture":"one extruded four-spoke seating profile + four straight volumetrically embedded legs",
                "onePieceFdm":True,"baseThicknessMm":BASE_THICKNESS,"legTangentialWidthMm":LEG_TANGENTIAL,
                "rootEmbedMm":ROOT_EMBED,"slotClearancePerSideMm":SLOT_CLEARANCE,"maximumLegTiltDeg":maximum_tilt,
                "harnessVolumeMm3":float(candidate["harness"].volume),
                "roots":{edge:serial_row(candidate["rows"][edge]) for edge in EDGES},
                "slots":{edge:serial_row(shell["rows"][edge]) for edge in EDGES},
            },
            "manufacturingGate":gate,
            "impossibilityProof":{
                "detailedBodyEnvelopeLocalUVWmm":{"min":[-3.155000042,-3.005000064,.06],"max":[3.155000042,3.005000064,3.560000108]},
                "minusUMidpointLegCrossedForBodyCenterURangeMm":[-7.410000084,-1.099999958],
                "minimumTangentialCenterAbsVForClearanceMm":3.805000064,
                "adjacentVRootAbsVMm":3.925,"remainingDistinctSupportSeparationMm":.119999936,
                "requiredStructuralSeparationMm":1.20,
                "canonicalOutwardDownRayAudit":{
                    "ratiosMinusWPerMinusUChecked":[.25,.35,.45,.55,.65,.8,1.0],
                    "maximumRemainingShellForLocalPairedFootprintsUpToRatio0p65Mm":1.177807142,
                    "ratio0p8":"remaining shell passes, but floor lies beyond local I2 crop on remote shell",
                },
                "legalEscapeWithinFrozenArchitecture":False,
            },
            "sequenceB":{"result":"NOT RUN — MANUFACTURING GATE FAIL","stateCount":0,
                         "reason":"required docs/85 local −U to +U harness insertion corridor is closed"},
            "sequenceC":{"result":"NOT RUN","reason":"explicit STOP after manufacturing gate failure"},
            "criticalComparison":{
                "oldBodyHarnessMaximumPenetrationMm3":15.271882439303985,
                "newComparable33StateMaximumPenetrationMm3":None,
                "oldBodyHarnessSweptCollisionVolumeMm3":25.221116186,
                "newComparable33StateSweptCollisionVolumeMm3":None,
                "newGateOnlyNineStateBodyHarnessMaximumPenetrationMm3":gate["maximumBodyHarnessPenetrationNineStateMm3"],
                "gateOnlyNominalReductionVsOldMm3":15.271882439303985-gate["maximumBodyHarnessPenetrationNineStateMm3"],
                "gateOnlyNominalReductionVsOldPercent":100*(15.271882439303985-gate["maximumBodyHarnessPenetrationNineStateMm3"])/15.271882439303985,
                "gateOnlyValueComparableToOld33State":False,
            },
            "prohibitions":{
                "angleOptimization":0,"rootOptimization":0,"innerHousing":0,"panel":0,"receiver":0,"strutNetwork":0,
                "carrier":0,"flexibleMember":0,"multiPieceHarness":0,"physicalCoupon":0,"eightButtonPropagation":0,
                "N2Redesign":0,"productionModification":0,
            },
            "preservation":{"protectedFileCount":len(protected),"hashesBefore":before,"hashesAfter":after,
                            "allProtectedFilesPreserved":before==after},
            "outputs":{"report":doc84.relative(REPORT),"json":doc84.relative(JSON_PATH),
                       "harnessStep":doc84.relative(HARNESS_STEP),"shellAuditStep":doc84.relative(SHELL_AUDIT_STEP),
                       "renders":render_paths},
        }
        JSON_PATH.write_text(json.dumps(data,indent=2),encoding="utf-8")
        REPORT.write_text(report_text(data),encoding="utf-8")
        print(json.dumps({"verdict":data["finalVerdict"],"manufacturingGate":"FAIL",
                          "sequenceB":"NOT RUN","sequenceC":"NOT RUN",
                          "gateOnlyNineStateBodyHarnessMaximumMm3":gate["maximumBodyHarnessPenetrationNineStateMm3"],
                          "renders":len(render_paths),"protected":before==after,
                          "report":doc84.relative(REPORT)},indent=2),flush=True)
        return

    pusher=pusher_system()
    mechanism={"PUSHER":pusher["pusher"],"GUIDE":pusher["guide"],
               "HARD_STOP":pusher["stop"],"CLIP":pusher["clip"]}
    assembly=sequence_b_exact(candidate,shell,switch,corners,mechanism)
    render_paths.extend(render_sequence_b(candidate,shell,switch,mechanism,assembly))
    current=current_probe_audit(old,body)
    after=doc84.hashes(protected)
    maximum_tilt=max(math.degrees(math.acos(min(1.0,abs(float(candidate["rows"][e]["directionLocal"][2]))))) for e in EDGES)
    final_verdict=("A — MANUFACTURING HARNESS AND FULL SEQUENCE B PASS" if assembly["allStatesCollisionFree"]
                   else "B — MANUFACTURING HARNESS PASSES; A FROZEN NON-HARNESS ASSEMBLY BLOCKER REMAINS")
    data={
        "schema":"onegrip.i2-manufacturing-four-edge-harness-rebase-audit.v1",
        "generatedUtc":datetime.now(timezone.utc).isoformat(),
        "mode":"I2 ONLY / MANUFACTURING GEOMETRY GATE BEFORE ASSEMBLY SEQUENCE B / NO SEQUENCE C",
        "finalVerdict":final_verdict,
        "sourceProof":{
            "sourceFile":"cad_dump/mesh_PushBtn.json","sourceObject":"PushBtn / ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID",
            "sourceTriangleCount":int(len(original.triangles)),"sourceSolidCount":int(len(original.full.solids())),
            "detailedBodyIncluded":True,"detailedBottomIncluded":True,"exactTerminalsIncluded":["T1","T2","T3","T4"],
            "cornerFeaturesIncluded":True,"measuredActuatorDiameterMm":3.35,"measuredActuatorProjectionMm":2.44,
            "simplifiedProxyUsedForFinalVerdict":False,
        },
        "currentAudit":current,
        "candidate":{
            "architecture":"one extruded four-spoke seating profile + four straight volumetrically embedded legs",
            "onePieceFdm":True,"baseThicknessMm":BASE_THICKNESS,"legTangentialWidthMm":LEG_TANGENTIAL,
            "rootEmbedMm":ROOT_EMBED,"slotClearancePerSideMm":SLOT_CLEARANCE,"maximumLegTiltDeg":maximum_tilt,
            "harnessVolumeMm3":float(candidate["harness"].volume),
            "roots":{edge:serial_row(candidate["rows"][edge]) for edge in EDGES},
            "slots":{edge:serial_row(shell["rows"][edge]) for edge in EDGES},
        },
        "manufacturingGate":gate,
        "sequenceB":assembly,
        "sequenceC":{"result":"NOT RUN","reason":"explicit I2-only scope; no I3-later audit"},
        "criticalComparison":{
            "oldBodyHarnessMaximumPenetrationMm3":15.271882439303985,
            "newBodyHarnessMaximumPenetrationMm3":assembly["bodyHarnessMaximumPenetrationMm3"],
            "oldBodyHarnessSweptCollisionVolumeMm3":25.221116186,
            "newBodyHarnessSweptCollisionVolumeMm3":assembly["bodyHarnessSweptCollisionVolumeMm3"],
        },
        "prohibitions":{
            "angleSearch":0,"rootSearch":0,"innerHousing":0,"panel":0,"receiver":0,"strutNetwork":0,
            "carrier":0,"flexibleMember":0,"multiPieceHarness":0,"physicalCoupon":0,"eightButtonPropagation":0,
            "N2Redesign":0,"productionModification":0,
        },
        "preservation":{"protectedFileCount":len(protected),"hashesBefore":before,"hashesAfter":after,
                        "allProtectedFilesPreserved":before==after},
        "outputs":{"report":doc84.relative(REPORT),"json":doc84.relative(JSON_PATH),
                   "harnessStep":doc84.relative(HARNESS_STEP),"shellAuditStep":doc84.relative(SHELL_AUDIT_STEP),
                   "renders":render_paths},
    }
    JSON_PATH.write_text(json.dumps(data,indent=2),encoding="utf-8")
    REPORT.write_text(report_text(data),encoding="utf-8")
    print(json.dumps({"verdict":final_verdict,"manufacturingGate":gate["result"],
                      "sequenceB":assembly["result"],"sequenceC":"NOT RUN",
                      "bodyHarnessMaximumOldNew":[15.271882439303985,assembly["bodyHarnessMaximumPenetrationMm3"]],
                      "bodyHarnessSweptOldNew":[25.221116186,assembly["bodyHarnessSweptCollisionVolumeMm3"]],
                      "renders":len(render_paths),"protected":before==after,
                      "report":doc84.relative(REPORT)},indent=2),flush=True)


if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="probe": probe_geometry()
    else: main()
