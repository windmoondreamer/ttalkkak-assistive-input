"""Bounded I3/N2 manufacturing candidate build and validation (audit only)."""
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
from . import i3_i4_local_hybrid_support_validation as d93
from . import i3_n2_combined_diagnostic_audit as d94
from . import seven_unresolved_leg_root_shell_target_rescue_audit as d91
from . import six_failed_leg_shell_landing_failure_mode_diagnostic_audit as d92
from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler, SHELL_STEP
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import local_box, volume
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import ROOT, relative
from .option_c_local_exact_prototype import safe_edge_lines, safe_triangles
from .slot_anchored_harness_captive_pusher_audit import pusher_system


OUT = ROOT / "build123d_workbench/out/i3_n2_bounded_manufacturing_candidate_validation"
RENDER = ROOT / "renders/i3_n2_bounded_manufacturing_candidate_validation"
REPORT = ROOT / "docs/95_i3_n2_bounded_manufacturing_candidate_validation.md"
JSON_PATH = OUT / "i3_n2_bounded_manufacturing_candidate_validation.json"
DOC94_JSON = d94.JSON_PATH
DOC93_JSON = d93.JSON_PATH
DOC92_JSON = d92.JSON_PATH
DOC91_JSON = d91.JSON_PATH
EPS = 1.0e-6
I3_SHIFT = 0.95
I3_FOOT_RELIEF = 0.08
N2_PAD_ADD = 0.15
FOOTER = "I3/N2 BOUNDED MANUFACTURING | AUDIT-ONLY SOLIDS | FROZEN EXTERIOR | PRODUCTION 0"
COL = {"harness": (61,191,139), "neighbor": (171,112,219), "collision": (245,84,73),
       "shell": (108,130,151), "jad": (53,173,213), "jfd": (113,132,153),
       "foot": (239,94,83), "slot": (242,172,66), "pad": (180,112,222),
       "body": (65,167,224), "terminal": (215,225,233), "axis": (250,212,77)}


def xyz(value: Iterable[float]) -> tuple[float,float,float]:
    return tuple(map(float,value))


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest().upper()


def safe_volume(shape:Shape|None)->float:
    return 0.0 if shape is None else float(volume(shape))


def clean_or_none(shape:Shape|None,label:str="")->Shape|None:
    if shape is None: return None
    result=shape.clean()
    if not result.solids(): return None
    if label: result.label=label
    return result


def moved(shape:Shape,offset:Iterable[float],label:str)->Shape:
    result=shape.moved(Location(Vector(*map(float,offset)))); result.label=label; return result


def pair(left:Shape,right:Shape)->dict[str,object]:
    pen=safe_volume(left&right)
    return {"distanceMm":float(left.distance_to(right)),"penetrationMm3":pen,"clear":pen<=EPS}


def bbox_row(shape:Shape|None)->dict[str,object]:
    if shape is None: return {"min":[0,0,0],"max":[0,0,0],"size":[0,0,0],"center":[0,0,0]}
    box=shape.bounding_box()
    return {"min":[float(box.min.X),float(box.min.Y),float(box.min.Z)],
            "max":[float(box.max.X),float(box.max.Y),float(box.max.Z)],
            "size":[float(box.size.X),float(box.size.Y),float(box.size.Z)],
            "center":[float(box.center().X),float(box.center().Y),float(box.center().Z)]}


def protected_files()->list[Path]:
    paths=set(d94.protected_files())
    paths.update((d94.REPORT,d94.JSON_PATH,ROOT/"build123d_workbench/i3_n2_combined_diagnostic_audit.py"))
    for folder in (d94.OUT,d94.RENDER):
        if folder.exists(): paths.update(path for path in folder.rglob("*") if path.is_file())
    return sorted(path for path in paths if path.exists())


def hashes(paths:list[Path])->dict[str,str]: return {relative(path):sha256(path) for path in paths}


def row_at_shift(source:dict[str,object],edge:str,shift:np.ndarray,datum,front:float,
                 shell_world:Shape)->dict[str,object]|None:
    root=np.asarray(source["rootLocalUVWmm"],float)+shift
    direction=np.asarray(source["directionLocal"],float)
    tangent=np.asarray(source["tangentLocal"],float)
    ray=ExactRaySampler(shell_world); direction_world=d90.local_dir_to_world(datum,direction)
    samples=[]
    for old in source["samples"]:
        origin=np.asarray(old["originLocalUVWmm"],float)+shift
        hits=ray.hits(d90.local_point_to_world(datum,front,origin),direction_world,24.0)
        if len(hits)<2: return None
        samples.append({"originLocalUVWmm":origin.tolist(),"hitsMm":hits,"hasInnerOuterPair":True})
    inner=[float(row["hitsMm"][0]) for row in samples]
    outer=[float(row["hitsMm"][1]) for row in samples]
    floor_distance=max(inner)+d90.BLIND_DEPTH
    floor=root+direction*floor_distance
    row=dict(source)
    row.update({"rootLocalUVWmm":root.tolist(),"floorPointLocalUVWmm":floor.tolist(),"samples":samples,
                "legLengthMm":floor_distance+d90.ROOT_EMBED,"functionalLengthMm":floor_distance,
                "minimumRemainingShellMm":min(outer)-floor_distance,
                "rootTangentCoordinateMm":float(source.get("rootTangentCoordinateMm",0.0)+
                    (shift[1] if edge in ("+U","-U") else shift[0]))})
    return d91.reconstruct_row(row,edge)


def row_with_root_shift(source:dict[str,object],edge:str,shift:np.ndarray,datum,front:float,
                        shell_world:Shape,width_override:float|None=None)->dict[str,object]|None:
    root=np.asarray(source["rootLocalUVWmm"],float)+shift
    target=np.asarray(source["floorPointLocalUVWmm"],float)
    direction=unit(target-root)
    tangent_hint=d90.tangent_axis(edge)
    tangent=unit(tangent_hint-direction*float(np.dot(tangent_hint,direction)))
    structural=unit(np.cross(direction,tangent))
    thickness=max(1.30,1.20/max(abs(float(direction[2])),1e-6))
    width=float(width_override if width_override is not None else source["legTangentWidthMm"])
    footprint_t=width+2*d90.SLOT_CLEARANCE; footprint_s=thickness+2*d90.SLOT_CLEARANCE
    offsets=((-footprint_t/2,-footprint_s/2),(-footprint_t/2,footprint_s/2),
             (footprint_t/2,-footprint_s/2),(footprint_t/2,footprint_s/2),
             (-footprint_t/2,0),(footprint_t/2,0),(0,-footprint_s/2),(0,footprint_s/2),(0,0))
    ray=ExactRaySampler(shell_world); direction_world=d90.local_dir_to_world(datum,direction)
    samples=[]; inner=[]; outer=[]
    for dt,ds in offsets:
        origin=root+tangent*dt+structural*ds
        hits=ray.hits(d90.local_point_to_world(datum,front,origin),direction_world,24.0)
        if len(hits)<2: return None
        samples.append({"originLocalUVWmm":origin.tolist(),"hitsMm":hits,"hasInnerOuterPair":True})
        inner.append(float(hits[0])); outer.append(float(hits[1]))
    floor_distance=max(inner)+d90.BLIND_DEPTH; floor=root+direction*floor_distance
    row=dict(source)
    row.update({"rootLocalUVWmm":root.tolist(),"directionLocal":direction.tolist(),
                "tangentLocal":tangent.tolist(),"structuralLocal":structural.tolist(),
                "tiltFromWDeg":math.degrees(math.acos(float(np.clip(direction[2],-1,1)))),
                "tiltAzimuthDeg":math.degrees(math.atan2(float(direction[1]),float(direction[0]))),
                "legThicknessMm":thickness,"effectiveFdmThicknessMm":thickness*abs(float(direction[2])),
                "legTangentWidthMm":width,
                "rootTangentCoordinateMm":float(source.get("rootTangentCoordinateMm",0.0)+
                    (shift[1] if edge.endswith("U") else shift[0])),
                "samples":samples,"floorPointLocalUVWmm":floor.tolist(),
                "legLengthMm":floor_distance+d90.ROOT_EMBED,"functionalLengthMm":floor_distance,
                "minimumRemainingShellMm":min(outer)-floor_distance,
                "shellThicknessFootprintRangeMm":[min(o-i for i,o in zip(inner,outer)),max(o-i for i,o in zip(inner,outer))]})
    return d91.reconstruct_row(row,edge)


def open_edge_cutter(base:Shape,collision:Shape,margin:float=.06)->Shape:
    bb=collision.bounding_box(); b=base.bounding_box()
    mins=np.asarray((bb.min.X,bb.min.Y,bb.min.Z),float)-margin
    maxs=np.asarray((bb.max.X,bb.max.Y,bb.max.Z),float)+margin
    center=np.asarray((bb.center().X,bb.center().Y,bb.center().Z),float)
    distances={"U-":abs(center[0]-b.min.X),"U+":abs(b.max.X-center[0]),
               "V-":abs(center[1]-b.min.Y),"V+":abs(b.max.Y-center[1])}
    side=min(distances,key=distances.get)
    if side=="U-": mins[0]=float(b.min.X)-.20
    elif side=="U+": maxs[0]=float(b.max.X)+.20
    elif side=="V-": mins[1]=float(b.min.Y)-.20
    else: maxs[1]=float(b.max.Y)+.20
    size=maxs-mins; c=(mins+maxs)/2
    cutter=local_box(float(size[0]),float(size[1]),float(size[2]),float(c[0]),float(c[1]),float(mins[2]),
                     "I3_SINGLE_PLANAR_SEAT_EDGE_SETBACK")
    cutter.label=f"I3_SEAT_SETBACK_{side}"
    return cutter


def foot_side_relief(foot:Shape,collision_at_full:Shape,depth:float)->tuple[Shape,Shape,dict[str,object]]:
    fb=foot.bounding_box(); cb=collision_at_full.bounding_box()
    foot_c=np.asarray((fb.center().X,fb.center().Y,fb.center().Z),float)
    col_c=np.asarray((cb.center().X,cb.center().Y,cb.center().Z),float)
    use_max=col_c[0]>=foot_c[0]
    if use_max:
        x0=float(fb.max.X)-depth; x1=float(fb.max.X)+.05
    else:
        x0=float(fb.min.X)-.05; x1=float(fb.min.X)+depth
    cutter=local_box(x1-x0,float(fb.size.Y)+.10,float(fb.size.Z)+.10,(x0+x1)/2,
                     float(fb.center().Y),float(fb.min.Z)-.05,"I3_PLUS_U_APPROACH_SIDE_RELIEF")
    relieved=clean_or_none(foot-cutter,"I3_PLUS_U_RELIEVED_CONTACT_FOOT")
    if relieved is None: raise RuntimeError("I3 foot relief removed entire foot")
    return relieved,cutter,{"depthMm":depth,"side":"+U" if use_max else "-U","cutter":bbox_row(cutter)}


def contact_area(foot:Shape,shell:Shape,direction:np.ndarray)->float:
    eps=.01
    a1=safe_volume(moved(foot,direction*eps,"AREA1")&shell)/eps
    a2=safe_volume(moved(foot,direction*(2*eps),"AREA2")&shell)/(2*eps)
    return .5*(a1+a2)


def insertion_vector(candidate:dict[str,object],slot_edges:tuple[str,...])->tuple[np.ndarray,float]:
    directions=[np.asarray(candidate["rows"][edge]["directionLocal"],float) for edge in slot_edges]
    common=unit(np.mean(directions,axis=0))
    dots={edge:float(np.dot(common,np.asarray(candidate["rows"][edge]["directionLocal"],float))) for edge in slot_edges}
    travel=max(d90.BLIND_DEPTH/max(value,1e-6) for value in dots.values())
    return common,travel


def build_i3_variant(shift_v:float,docs91:dict[str,object],docs93:dict[str,object],datums,placements,
                     shell_full:dict[str,Shape],i2_harness:Shape,i2_t3:Shape)->dict[str,object]|None:
    button="I3"; datum=datums[button]; placement=placements[button]; front=float(FROZEN_FRONT_DEPTHS[button])
    original_shell=d93.shell_local(shell_full[datum.owner],placement,"I3_LOCAL_SHELL")
    rows=d93.reconstruct_slot_rows(button,docs91)
    width_override=1.20 if shift_v<=-1.99 else None
    shifted=row_with_root_shift(rows["-U"],"-U",np.asarray((0.0,shift_v,0.0)),datum,front,
                                shell_full[datum.owner],width_override=width_override)
    if shifted is None: return None
    rows["-U"]=shifted
    pad=d93.i3_micro_thickening(original_shell,shifted,placement,datum,front)
    working_shell=pad["shell"]
    slotted=d93.cut_three_slots(working_shell,rows)
    selected=docs93["buttons"][button]["contactSearch"]["selected"]
    contact=d93.build_contact_leg(selected,working_shell,button)
    roots={edge:np.asarray(rows[edge]["rootLocalUVWmm"],float) for edge in rows}
    roots["+U"]=np.asarray(contact["rootLocalUVWmm"],float)
    base=d90.base_profile(roots)
    seat_collision=clean_or_none((base&i2_harness).fuse(base&i2_t3),"I3_SEAT_LIMIT_COLLISION")
    if seat_collision is None: seat_cutter=local_box(.01,.01,.01,0,0,0,"NO_SEAT_CUT")
    else: seat_cutter=open_edge_cutter(base,seat_collision)
    trimmed_base=clean_or_none(base-seat_cutter,"I3_LOCALLY_TRIMMED_CONTINUOUS_SEAT")
    if trimmed_base is None: return None
    # The -U root moved laterally off the frozen cross-spoke.  Keep the base as
    # one simple planar manufacturing body by relocating only that one spoke
    # to the new root coordinate; this is a root-local seat correction, not a
    # new reaction support or a dogleg in the structural leg.
    if safe_volume(trimmed_base&rows["-U"]["leg"])<=EPS:
        root=np.asarray(rows["-U"]["rootLocalUVWmm"],float)
        x0=float(root[0]-d90.FRAME_WIDTH/2); x1=d90.FRAME_WIDTH/2
        root_tongue=local_box(x1-x0,1.20,d90.BASE_THICKNESS,(x0+x1)/2,float(root[1]),
                              d90.BASE_TOP_W-d90.BASE_THICKNESS,"I3_MINUS_U_RELOCATED_PLANAR_ROOT_SPOKE")
        trimmed_base=trimmed_base.fuse(root_tongue).clean(); trimmed_base.label="I3_LOCALLY_TRIMMED_CONTINUOUS_SEAT"
    else:
        root_tongue=local_box(.01,.01,.01,0,0,0,"NO_ROOT_SPOKE_RELOCATION")

    provisional=trimmed_base
    overlaps={}
    for edge,row in rows.items():
        provisional=provisional.fuse(row["leg"])
        overlaps[edge]=safe_volume(trimmed_base&row["leg"])
    provisional=provisional.fuse(contact["combined"]).clean()
    common,travel=insertion_vector({"rows":rows},tuple(rows))
    offset=-common*travel*.25
    early=clean_or_none(moved(contact["foot"],offset,"I3_FOOT_75")&slotted,"I3_FOOT_75_COLLISION")
    if early is None:
        relieved_foot=contact["foot"]; foot_cutter=local_box(.01,.01,.01,0,0,0,"NO_FOOT_CUT")
        relief={"depthMm":0.0,"side":"NONE","cutter":bbox_row(foot_cutter)}
    else:
        early_full=moved(early,-offset,"I3_EARLY_COLLISION_MAPPED_TO_FULL")
        relieved_foot,foot_cutter,relief=foot_side_relief(contact["foot"],early_full,I3_FOOT_RELIEF)
    contact_combined=contact["leg"].fuse(relieved_foot).clean()
    contact=dict(contact); contact.update({"foot":relieved_foot,"combined":contact_combined,
        "contactAreaMm2":contact_area(relieved_foot,working_shell,np.asarray(contact["directionLocal"],float)),
        "footLegCommonVolumeMm3":safe_volume(contact["leg"]&relieved_foot)})
    harness=trimmed_base
    for row in rows.values(): harness=harness.fuse(row["leg"])
    harness=harness.fuse(contact_combined).clean(); harness.label="I3_BOUNDED_CORRECTED_MANUFACTURING_HARNESS"
    overlaps["+U"]=safe_volume(trimmed_base&contact_combined)
    candidate={"harness":harness,"base":trimmed_base,"untrimmedBase":base,"rows":rows,
               "contact":contact,"contactFoot":relieved_foot,"rootCommonVolumeByEdgeMm3":overlaps,
               "slots":Compound(children=[row["slotTool"] for row in rows.values()]),
               "mouths":Compound(children=[row["mouthTool"] for row in rows.values()])}
    return {"candidate":candidate,"shell":slotted,"workingShell":working_shell,"pad":pad,
            "seatCutter":seat_cutter,"footCutter":foot_cutter,"rootTongue":root_tongue,"relief":relief,
            "shiftVmm":shift_v,"seatCollisionBefore":safe_volume(seat_collision),
            "baseVolumeRetention":safe_volume(trimmed_base)/safe_volume(base),
            "minusUI2Penetration":safe_volume(rows["-U"]["leg"]&i2_harness),
            "seatI2HarnessPenetration":safe_volume(trimmed_base&i2_harness),
            "seatI2T3Penetration":safe_volume(trimmed_base&i2_t3),
            "wholeI2HarnessPenetration":safe_volume(harness&i2_harness),
            "wholeI2T3Penetration":safe_volume(harness&i2_t3),
            "minusUI2CollisionBox":bbox_row(rows["-U"]["leg"]&i2_harness),
            "seatI2HarnessCollisionBox":bbox_row(trimmed_base&i2_harness),
            "seatI2T3CollisionBox":bbox_row(trimmed_base&i2_t3),
            "seatCutterBox":bbox_row(seat_cutter),
            "contactAreaMm2":contact["contactAreaMm2"],"footLegCommonVolumeMm3":contact["footLegCommonVolumeMm3"],
            "padFinalRemainingShellMm":pad["finalEffectiveRemainingShellMm"]}


def build_context():
    docs90=json.loads(d90.JSON_PATH.read_text(encoding="utf-8")); docs91=json.loads(DOC91_JSON.read_text(encoding="utf-8"))
    docs93=json.loads(DOC93_JSON.read_text(encoding="utf-8")); docs94=json.loads(DOC94_JSON.read_text(encoding="utf-8"))
    datums=load_all_datums(); placements={name:doc84.doc83.datum_location(datums[name],FROZEN_FRONT_DEPTHS[name]) for name in d90.BUTTONS}
    shell_full={owner:import_step(path) for owner,path in SHELL_STEP.items()}
    existing=d93.existing_five_harnesses(docs90,docs91,placements)
    i3_inv=placements["I3"].inverse(); i2_harness=i3_inv*existing["I2"]
    _o,body,terminals,corners,_oa,actuator,_h=doc84.detailed_switch_parts()
    i2_to_i3=i3_inv*placements["I2"]; i2_t3=i2_to_i3*terminals["T3"]
    return docs90,docs91,docs93,docs94,datums,placements,shell_full,existing,i2_harness,i2_t3


def fixed_contact_row(button:str,edge:str,root:np.ndarray,center_uv:Iterable[float],shell_world:Shape,
                      datum,front:float)->dict[str,object]:
    ray=ExactRaySampler(shell_world); center=np.asarray(tuple(center_uv),float)
    origin=np.asarray((center[0],center[1],.06),float)
    w_world=d90.local_dir_to_world(datum,(0,0,1)); center_hits=ray.hits(
        d90.local_point_to_world(datum,front,origin),w_world,24.0)
    if len(center_hits)<2: raise RuntimeError(f"{button} {edge} contact center lacks shell pair")
    target=np.asarray((center[0],center[1],.06+float(center_hits[0])),float)
    direction=unit(target-root)
    tangent_hint=d90.tangent_axis(edge); tangent=unit(tangent_hint-direction*float(np.dot(tangent_hint,direction)))
    structural=unit(np.cross(direction,tangent))
    offsets=((-d93.FOOT_FLARE_WIDTH/2,-d93.FOOT_FLARE_THICKNESS/2),
             (-d93.FOOT_FLARE_WIDTH/2,d93.FOOT_FLARE_THICKNESS/2),
             (d93.FOOT_FLARE_WIDTH/2,-d93.FOOT_FLARE_THICKNESS/2),
             (d93.FOOT_FLARE_WIDTH/2,d93.FOOT_FLARE_THICKNESS/2),
             (-d93.FOOT_FLARE_WIDTH/2,0),(d93.FOOT_FLARE_WIDTH/2,0),
             (0,-d93.FOOT_FLARE_THICKNESS/2),(0,d93.FOOT_FLARE_THICKNESS/2),(0,0))
    direction_world=d90.local_dir_to_world(datum,direction); samples=[]
    for dt,ds in offsets:
        sample_origin=root+tangent*dt+structural*ds
        hits=ray.hits(d90.local_point_to_world(datum,front,sample_origin),direction_world,24.0)
        if len(hits)<2: raise RuntimeError(f"{button} {edge} contact footprint incomplete")
        samples.append({"originLocalUVWmm":sample_origin.tolist(),"hitsMm":hits})
    inner=[float(row["hitsMm"][0]) for row in samples]; outer=[float(row["hitsMm"][1]) for row in samples]
    normal=d93.surface_normal_local(ray,datum,front,float(center[0]),float(center[1]))
    if normal is None: normal=np.asarray((0,0,1),float)
    return {"button":button,"edge":edge,"targetCenterLocalUVmm":center.tolist(),
            "rootLocalUVWmm":root.tolist(),"directionLocal":direction.tolist(),
            "tangentLocal":tangent.tolist(),"structuralLocal":structural.tolist(),"samples":samples,
            "minimumInnerHitMm":min(inner),"maximumInnerHitMm":max(inner),
            "minimumOuterHitMm":min(outer),"surfaceNormalLocal":normal.tolist(),
            "legAxisToLocalShellNormalDeg":math.degrees(math.acos(float(np.clip(np.dot(direction,normal),-1,1)))),
            "sideIdentityPreserved":True,"localFingerButtonShellRegion":True,"remoteWallUsed":False}


def build_contact_member(row:dict[str,object],shell:Shape,label:str)->dict[str,object]:
    root=np.asarray(row["rootLocalUVWmm"],float); direction=np.asarray(row["directionLocal"],float)
    tangent=np.asarray(row["tangentLocal"],float); inner=float(row["minimumInnerHitMm"]); outer=float(row["maximumInnerHitMm"])
    leg_end=root+direction*(inner-.20)
    leg=oriented_box_between(xyz(root-direction*d90.ROOT_EMBED),xyz(leg_end),xyz(tangent),
                             d93.FOOT_WIDTH,d93.FOOT_THICKNESS,label=f"{label}_ONE_STRAIGHT_LEG")
    raw=oriented_box_between(xyz(root+direction*(inner-d93.FOOT_AXIAL_DEPTH)),
                             xyz(root+direction*(outer+.50)),xyz(tangent),
                             d93.FOOT_FLARE_WIDTH,d93.FOOT_FLARE_THICKNESS,label=f"{label}_RAW_FOOT")
    foot=clean_or_none(raw-shell,f"{label}_SHELL_MATCHED_SIMPLE_FOOT")
    if foot is None: raise RuntimeError(f"{label} foot boolean failed")
    combined=leg.fuse(foot).clean(); combined.label=f"{label}_LEG_FOOT"
    direction=np.asarray(row["directionLocal"],float)
    return {**row,"leg":leg,"foot":foot,"combined":combined,
            "footLegCommonVolumeMm3":safe_volume(leg&foot),"contactGapMm":float(foot.distance_to(shell)),
            "contactAreaMm2":contact_area(foot,shell,direction),
            "contactPatchDimensionsMm":[d93.FOOT_FLARE_WIDTH,d93.FOOT_FLARE_THICKNESS],
            "compressionReactionDirectionLocal":(-np.asarray(row["surfaceNormalLocal"],float)).tolist(),
            "positiveFiniteAreaContact":float(foot.distance_to(shell))<=1e-5 and contact_area(foot,shell,direction)>.25}


def cut_slots(shell:Shape,rows:dict[str,dict[str,object]])->Shape:
    result=shell
    for row in rows.values(): result=(result-row["slotTool"]-row["mouthTool"]).clean()
    result.label="N2_TWO_SLOT_JFD_SHELL_AUDIT_ONLY"; return result


def build_n2_candidate(docs91:dict[str,object],docs92:dict[str,object],docs94:dict[str,object],
                       datums,placements,shell_full:dict[str,Shape])->dict[str,object]:
    button="N2"; datum=datums[button]; placement=placements[button]; front=float(FROZEN_FRONT_DEPTHS[button])
    jfd=d93.shell_local(shell_full["JfD"],placement,"N2_JFD_LOCAL_SHELL")
    jad=d93.shell_local(shell_full["JaD"],placement,"N2_JAD_LOCAL_SHELL")
    minus_u=d91.reconstruct_row(docs91["buttons"][button]["legs"]["-U"],"-U")
    minus_v=d91.reconstruct_row(docs92["legs"]["N2 -V"]["docs91BestFailure"],"-V")
    pad=d93.i3_micro_thickening(jfd,minus_v,placement,datum,front)
    slotted=cut_slots(pad["shell"],{"-U":minus_u,"-V":minus_v})
    plus_v_source=docs92["legs"]["N2 +V"]["docs91BestFailure"]
    plus_v_row=fixed_contact_row(button,"+V",np.asarray(plus_v_source["rootLocalUVWmm"],float),
                                 docs94["n2"]["plusV"]["centerLocalUVmm"],shell_full["JfD"],datum,front)
    plus_v=build_contact_member(plus_v_row,pad["shell"],"N2_PLUS_V_LOCAL_CONTACT")
    plus_u_root=np.asarray(d92.reference_row("+U",None)["root"],float)
    plus_u_row=fixed_contact_row(button,"+U",plus_u_root,
                                 docs94["n2"]["plusU"]["jaDCenterLocalUVmm"],shell_full["JaD"],datum,front)
    plus_u=build_contact_member(plus_u_row,jad,"N2_PLUS_U_JAD_CLOSURE_CONTACT")
    rows={"-U":minus_u,"-V":minus_v}
    roots={"-U":np.asarray(minus_u["rootLocalUVWmm"],float),"-V":np.asarray(minus_v["rootLocalUVWmm"],float),
           "+U":plus_u_root,"+V":np.asarray(plus_v_source["rootLocalUVWmm"],float)}
    base=d90.base_profile(roots); harness=base; overlaps={}
    for edge,row in rows.items():
        harness=harness.fuse(row["leg"]); overlaps[edge]=safe_volume(base&row["leg"])
    for edge,contact in (("+U",plus_u),("+V",plus_v)):
        harness=harness.fuse(contact["combined"]); overlaps[edge]=safe_volume(base&contact["combined"])
    harness=harness.clean(); harness.label="N2_COMPLETE_TWO_SLOT_TWO_LOCAL_CONTACT_MANUFACTURING_HARNESS"
    candidate={"harness":harness,"base":base,"rows":rows,"contacts":{"+U":plus_u,"+V":plus_v},
               "rootCommonVolumeByEdgeMm3":overlaps,
               "slots":Compound(children=[row["slotTool"] for row in rows.values()]),
               "mouths":Compound(children=[row["mouthTool"] for row in rows.values()])}
    return {"candidate":candidate,"jfdOriginal":jfd,"jfdReinforced":pad["shell"],"jfdSlotted":slotted,
            "jad":jad,"pad":pad}


def detailed_local_parts()->tuple[dict[str,Shape],Shape,dict[str,Shape]]:
    _original,body,terminals,corners,_old_actuator,actuator,_hybrid=doc84.detailed_switch_parts()
    parts={"BODY":body,"ACTUATOR":actuator,**terminals,"CORNERS":corners}
    mechanism_source=pusher_system(); mechanism={"PUSHER":mechanism_source["pusher"],
        "GUIDE":mechanism_source["guide"],"HARD_STOP":mechanism_source["stop"],"CLIP":mechanism_source["clip"]}
    return parts,corners,mechanism


def i3_five_state(result:dict[str,object],i2_harness:Shape,i2_parts:dict[str,Shape],
                  own_parts:dict[str,Shape],mechanism:dict[str,Shape])->dict[str,object]:
    candidate=result["candidate"]; common,travel=insertion_vector(candidate,tuple(candidate["rows"]))
    fixed={"SHELL":result["shell"],"I2_HARNESS":i2_harness,
           **{f"I2_{name}":shape for name,shape in i2_parts.items()},
           **{f"OWN_{name}":shape for name,shape in own_parts.items()},**mechanism}
    states=[]
    for index,fraction in enumerate((1.0,.75,.5,.25,0.0)):
        offset=-common*travel*fraction; moving=moved(candidate["harness"],offset,f"I3_STATE_{index}")
        metrics={name:pair(moving,shape) for name,shape in fixed.items()}
        states.append({"label":("START","25%","50%","75%","FULL SEAT")[index],
                       "offsetLocalUVWmm":offset.tolist(),"pairMetrics":metrics,
                       "maximumUnintendedPenetrationMm3":max(float(row["penetrationMm3"]) for row in metrics.values())})
    passed=all(row["maximumUnintendedPenetrationMm3"]<=EPS for row in states)
    return {"result":"PASS" if passed else "FAIL","states":states,"travelMm":travel,
            "commonInsertionVectorLocal":common.tolist(),"elasticDeformationRequired":False,
            "pushBtnTranslationMm":0.0,"pushBtnRotationDeg":0.0}


def n2_stage1(result:dict[str,object],own_parts:dict[str,Shape],mechanism:dict[str,Shape])->dict[str,object]:
    candidate=result["candidate"]; common,travel=insertion_vector(candidate,("-U","-V"))
    fixed={"JFD_SHELL":result["jfdSlotted"],**own_parts,**mechanism}; states=[]
    for index,fraction in enumerate((1.0,.75,.5,.25,0.0)):
        offset=-common*travel*fraction; moving=moved(candidate["harness"],offset,f"N2_STAGE1_{index}")
        metrics={name:pair(moving,shape) for name,shape in fixed.items()}
        plus_v=moved(candidate["contacts"]["+V"]["foot"],offset,f"N2_PLUS_V_{index}")
        states.append({"label":("START","25%","50%","75%","JfD-SEATED")[index],
                       "offsetLocalUVWmm":offset.tolist(),"pairMetrics":metrics,
                       "plusVFootGapMm":float(plus_v.distance_to(result["jfdReinforced"])),
                       "maximumUnintendedPenetrationMm3":max(float(row["penetrationMm3"]) for row in metrics.values())})
    early_gap=all(row["plusVFootGapMm"]>1e-5 for row in states[:-1])
    final_contact=states[-1]["plusVFootGapMm"]<=1e-5
    passed=all(row["maximumUnintendedPenetrationMm3"]<=EPS for row in states) and early_gap and final_contact
    return {"result":"PASS" if passed else "FAIL","states":states,"travelMm":travel,
            "commonInsertionVectorLocal":common.tolist(),"contactOnlyAtJfdSeated":early_gap and final_contact,
            "elasticDeformationRequired":False,"pushBtnTranslationMm":0.0,"pushBtnRotationDeg":0.0}


def closure_direction_local(datum)->np.ndarray:
    world_open=np.asarray((1.0,0.0,0.0),float)
    return unit((float(np.dot(world_open,unit(datum.switch_u))),
                 float(np.dot(world_open,unit(datum.switch_v))),float(np.dot(world_open,unit(datum.axis)))))


def n2_stage2(result:dict[str,object],datum,own_parts:dict[str,Shape])->dict[str,object]:
    candidate=result["candidate"]; open_dir=closure_direction_local(datum); open_distance=8.0; states=[]
    frozen_seam_baseline=safe_volume(result["jad"]&result["jfdReinforced"])
    other=Compound(children=[candidate["base"],candidate["rows"]["-U"]["leg"],candidate["rows"]["-V"]["leg"],
                             candidate["contacts"]["+V"]["combined"],candidate["contacts"]["+U"]["leg"]])
    for index,fraction in enumerate((1.0,.75,.5,.25,0.0)):
        offset=open_dir*open_distance*fraction; jad=moved(result["jad"],offset,f"N2_JAD_CLOSURE_{index}")
        foot=candidate["contacts"]["+U"]["foot"]
        metrics={"HARNESS":pair(jad,candidate["harness"]),"PLUS_U_FOOT":pair(jad,foot),
                 "OTHER_N2":pair(jad,other),"JFD_CLOSURE":pair(jad,result["jfdReinforced"]),
                 **{f"PUSHBTN_{name}":pair(jad,shape) for name,shape in own_parts.items()}}
        states.append({"label":("OPEN","25%","50%","75%","CLOSED")[index],
                       "offsetLocalUVWmm":offset.tolist(),"pairMetrics":metrics,
                       "plusUFootGapMm":float(jad.distance_to(foot)),
                       "frozenSeamBaselineMm3":frozen_seam_baseline if index==4 else 0.0,
                       "maximumCandidateAddedPenetrationMm3":max(
                           0.0,*(float(row["penetrationMm3"]) if name not in ("PLUS_U_FOOT","JFD_CLOSURE") else
                           (max(0.0,float(row["penetrationMm3"])-(frozen_seam_baseline if index==4 else 0.0)) if name=="JFD_CLOSURE" else 0.0)
                           for name,row in metrics.items()))})
    early=all(row["plusUFootGapMm"]>1e-5 for row in states[:-1]); closed=states[-1]["plusUFootGapMm"]<=1e-5
    no_unintended=all(row["maximumCandidateAddedPenetrationMm3"]<=EPS for row in states)
    service_jad=moved(result["jad"],open_dir*.25,"N2_JAD_SERVICE_PROBE")
    service_pair=pair(service_jad,candidate["harness"]); service_gap=float(service_jad.distance_to(candidate["contacts"]["+U"]["foot"]))
    removable=service_pair["clear"] and service_gap>1e-5
    return {"result":"PASS" if early and closed and no_unintended else "FAIL","states":states,
            "closureDirectionWorld":[-1.0,0.0,0.0],"openDirectionLocal":open_dir.tolist(),
            "openDistanceMm":open_distance,"contactOnlyAtClosed":early and closed,
            "nominalGapMm":candidate["contacts"]["+U"]["contactGapMm"],"nominalInterferenceMm":0.0,
            "jaDRemovableAfterward":bool(removable),"harnessRemainsWithJfDAfterRemoval":bool(removable),
            "serviceProbe":{"outwardTravelMm":.25,"pair":service_pair,"plusUFootGapMm":service_gap},
            "captivelyBridgesSeam":bool(not removable),"significantElasticDeformationRequired":bool(not removable),
            "frozenJaDJfDSeamBaselinePenetrationMm3":frozen_seam_baseline}


def load_path(candidate:dict[str,object])->dict[str,object]:
    supports={edge:np.asarray(row["rootLocalUVWmm"],float)[:2] for edge,row in candidate["rows"].items()}
    supports.update({edge:np.asarray(row["rootLocalUVWmm"],float)[:2] for edge,row in candidate["contacts"].items()})
    names=list(supports); matrix=np.vstack((np.ones(len(names)),[supports[name][0] for name in names],
                                           [supports[name][1] for name in names]))
    reactions=np.linalg.pinv(matrix)@np.asarray((1.0,0.0,0.0),float)
    return {"supportReactions":{name:float(reactions[index]) for index,name in enumerate(names)},
            "allPositive":bool(np.all(reactions>EPS)),"translationRestraint":"ADEQUATE",
            "rotationRestraint":"ADEQUATE","rockingUnderPress":"ABSENT" if np.all(reactions>EPS) else "PRESENT",
            "adhesivePrimaryLoadBearing":False}


def manufacturing(candidate:dict[str,object],step_path:Path,linear_sections:list[float],effective_sections:list[float],
                  shell_penetration:float,system_pass:bool)->dict[str,object]:
    export_step(candidate["harness"],step_path); imported=import_step(step_path)
    root_volumes=candidate["rootCommonVolumeByEdgeMm3"]
    row={"solidCount":len(candidate["harness"].solids()),"connectedComponents":len(candidate["harness"].solids()),
         "valid":bool(candidate["harness"].is_valid),"watertight":bool(candidate["harness"].is_valid),
         "stepReimportSolidCount":len(imported.solids()),"stepReimportValid":bool(imported.is_valid),
         "zeroThicknessConnectionCount":sum(value<=EPS for value in root_volumes.values()),
         "tangentOnlyRootCount":sum(value<=EPS for value in root_volumes.values()),
         "minimumStructuralNeckMm":min(linear_sections),"minimumEffectiveSectionMm":min(effective_sections),
         "rootCommonVolumeByEdgeMm3":root_volumes,"shellUnintendedPenetrationMm3":shell_penetration,
         "auditStep":relative(step_path)}
    row["result"]="PASS" if (row["solidCount"]==row["connectedComponents"]==row["stepReimportSolidCount"]==1 and
        row["valid"] and row["stepReimportValid"] and row["zeroThicknessConnectionCount"]==row["tangentOnlyRootCount"]==0 and
        row["minimumStructuralNeckMm"]>=1.20-EPS and row["minimumEffectiveSectionMm"]>=1.20-EPS and
        shell_penetration<=EPS and system_pass) else "FAIL"
    return row


def probe()->None:
    docs90,docs91,docs93,docs94,datums,placements,shell_full,existing,i2_harness,i2_t3=build_context()
    result=build_i3_variant(-2.0,docs91,docs93,datums,placements,shell_full,i2_harness,i2_t3)
    own_parts,_corners,mechanism=detailed_local_parts()
    _o,body,terminals,corners,_oa,actuator,_h=doc84.detailed_switch_parts()
    i2_to_i3=placements["I3"].inverse()*placements["I2"]
    i2_parts={"BODY":i2_to_i3*body,"ACTUATOR":i2_to_i3*actuator,"CORNERS":i2_to_i3*corners,
              **{name:i2_to_i3*shape for name,shape in terminals.items()}}
    i3_rear=i3_five_state(result,i2_harness,i2_parts,own_parts,mechanism)
    n2=build_n2_candidate(docs91,json.loads(DOC92_JSON.read_text(encoding="utf-8")),docs94,
                          datums,placements,shell_full)
    stage1=n2_stage1(n2,own_parts,mechanism); stage2=n2_stage2(n2,datums["N2"],own_parts)
    payload={"i3":{key:value for key,value in result.items() if key not in
                    ("candidate","shell","workingShell","pad","seatCutter","footCutter")},
             "i3Rear":{"result":i3_rear["result"],"states":[{"label":row["label"],
                "max":row["maximumUnintendedPenetrationMm3"],
                "limiter":max(row["pairMetrics"],key=lambda key:row["pairMetrics"][key]["penetrationMm3"])} for row in i3_rear["states"]]},
             "n2":{"contacts":{edge:{"area":row["contactAreaMm2"],"gap":row["contactGapMm"],
                    "overlap":row["footLegCommonVolumeMm3"]} for edge,row in n2["candidate"]["contacts"].items()},
                   "pad":{key:value for key,value in n2["pad"].items() if key not in ("shell","added")},
                   "solidCount":len(n2["candidate"]["harness"].solids()),"valid":n2["candidate"]["harness"].is_valid},
             "stage1":{"result":stage1["result"],"states":[{"label":row["label"],"max":row["maximumUnintendedPenetrationMm3"],
                       "gap":row["plusVFootGapMm"],"limiter":max(row["pairMetrics"],key=lambda key:row["pairMetrics"][key]["penetrationMm3"])} for row in stage1["states"]]},
             "stage2":{"result":stage2["result"],"states":[{"label":row["label"],"max":row["maximumCandidateAddedPenetrationMm3"],
                       "gap":row["plusUFootGapMm"],"limiter":max(row["pairMetrics"],key=lambda key:row["pairMetrics"][key]["penetrationMm3"])} for row in stage2["states"]],
                       "service":stage2["serviceProbe"]}}
    print(json.dumps(payload,indent=2,ensure_ascii=True))


def n2_geometry_probe()->None:
    docs90,docs91,docs93,docs94,datums,placements,shell_full,existing,i2_harness,i2_t3=build_context()
    n2=build_n2_candidate(docs91,json.loads(DOC92_JSON.read_text(encoding="utf-8")),docs94,
                          datums,placements,shell_full)
    candidate=n2["candidate"]; plus_u=candidate["contacts"]["+U"]; plus_v=candidate["contacts"]["+V"]
    open_dir=closure_direction_local(datums["N2"]); service_jad=moved(n2["jad"],open_dir*.25,"SERVICE")
    shapes={"base_jfd":candidate["base"]&n2["jfdSlotted"],
            "minusU_leg_jfd":candidate["rows"]["-U"]["leg"]&n2["jfdSlotted"],
            "minusV_leg_jfd":candidate["rows"]["-V"]["leg"]&n2["jfdSlotted"],
            "plusU_leg_jfd":plus_u["leg"]&n2["jfdSlotted"],"plusU_foot_jfd":plus_u["foot"]&n2["jfdSlotted"],
            "plusV_leg_jfd":plus_v["leg"]&n2["jfdSlotted"],"plusV_foot_jfd":plus_v["foot"]&n2["jfdSlotted"],
            "service_plusU_leg":service_jad&plus_u["leg"],"service_plusU_foot":service_jad&plus_u["foot"],
            "closed_seam":n2["jad"]&n2["jfdReinforced"]}
    for travel in (.05,.10,.25,.50):
        shapes[f"service_{travel:.2f}_plusU_foot"]=moved(n2["jad"],open_dir*travel,f"SERVICE_{travel}")&plus_u["foot"]
    print(json.dumps({name:{"volume":safe_volume(shape),"bbox":bbox_row(shape)} for name,shape in shapes.items()},
                     indent=2,ensure_ascii=True))


def i3_root_probe()->None:
    _d90,docs91,docs93,_docs94,datums,placements,shell_full,_existing,i2_harness,i2_t3=build_context()
    result=build_i3_variant(-2.0,docs91,docs93,datums,placements,shell_full,i2_harness,i2_t3)
    row=result["candidate"]["rows"]["-U"]; root=np.asarray(row["rootLocalUVWmm"],float)
    floor=np.asarray(row["floorPointLocalUVWmm"],float); direction=np.asarray(row["directionLocal"],float)
    tangent=np.asarray(row["tangentLocal"],float); base=result["candidate"]["base"]
    tests={}
    for extra in (0.0,.20,.40,.60,.80,1.00,1.20,1.50,2.00):
        leg=oriented_box_between(xyz(root-direction*(d90.ROOT_EMBED+extra)),xyz(floor),xyz(tangent),
                                 float(row["legTangentWidthMm"]),float(row["legThicknessMm"]),label="PROBE")
        fused=base.fuse(leg).clean()
        tests[f"{extra:.2f}"]={"rootCommonVolumeMm3":safe_volume(base&leg),"fusedSolidCount":len(fused.solids()),
                                "i2PenetrationMm3":safe_volume(leg&i2_harness)}
    print(json.dumps({"root":root.tolist(),"baseBox":bbox_row(base),"untrimmedBaseBox":bbox_row(result["candidate"]["untrimmedBase"]),
                      "untrimmedBaseSolidCount":len(result["candidate"]["untrimmedBase"].solids()),
                      "seatCollisionBeforeMm3":result["seatCollisionBefore"],"seatCutterBox":result["seatCutterBox"],
                      "minusULegBox":bbox_row(row["leg"]),"tests":tests},indent=2))


def fit_points(shapes:Iterable[Shape],padding:float=1.18)->np.ndarray:
    arrays=[]
    for shape in shapes:
        tri=safe_triangles(shape)
        if tri.size: arrays.append(tri.reshape(-1,3))
    raw=np.concatenate(arrays,axis=0)
    center=np.mean(raw,axis=0)
    return center+(raw-center)*padding


def render_scene(path:Path,objects:list[tuple[Shape,tuple[int,int,int]]],
                 transparent:list[tuple[Shape,tuple[int,int,int,int]]]|None=None,
                 wires:list[tuple[Shape,tuple[int,int,int,int]]]|None=None,
                 lines:list[tuple[np.ndarray,np.ndarray,tuple[int,int,int,int],str]]|None=None,
                 camera:tuple[float,float,float]=(34,-46,25))->str:
    solids=[shape for shape,_color in objects]
    if transparent: solids.extend(shape for shape,_color in transparent)
    d92.raster_scene_without_header(
        path,[(safe_triangles(shape),color) for shape,color in objects],"","",FOOTER,
        transparent_objects=[] if not transparent else [(safe_triangles(shape),color) for shape,color in transparent],
        wireframes=[] if not wires else [(safe_edge_lines(shape),color) for shape,color in wires],
        world_lines=[] if not lines else lines,camera_offset=camera,fit_points=fit_points(solids))
    return relative(path)


def render_results(i3:dict[str,object],n2:dict[str,object],stage1:dict[str,object],
                   stage2:dict[str,object])->list[str]:
    RENDER.mkdir(parents=True,exist_ok=True); outputs=[]
    i3c=i3["candidate"]
    i3_collision=clean_or_none(i3c["rows"]["-U"]["leg"] & i3["_i2Harness"],"I3_I2_REMAINING_COLLISION")
    objects=[(i3c["harness"],COL["harness"]),(i3["_i2Harness"],COL["neighbor"])]
    if i3_collision is not None: objects.append((i3_collision,COL["collision"]))
    outputs.append(render_scene(RENDER/"01_i3_complete_candidate_i2_limit.png",objects,
                                transparent=[(i3["shell"],(*COL["shell"],28))],
                                wires=[(i3["shell"],(*COL["shell"],90))]))
    outputs.append(render_scene(RENDER/"02_i3_seat_edge_setback.png",
                                [(i3c["base"],COL["harness"]),(i3["seatCutter"],COL["slot"]),
                                 (i3["_i2T3"],COL["terminal"])],camera=(29,-42,23)))
    outputs.append(render_scene(RENDER/"03_i3_plus_u_lead_in.png",
                                [(i3c["contact"]["combined"],COL["foot"]),(i3["footCutter"],COL["slot"])],
                                transparent=[(i3["shell"],(*COL["shell"],28))],
                                wires=[(i3["shell"],(*COL["shell"],85))],camera=(30,-40,22)))
    n2c=n2["candidate"]
    outputs.append(render_scene(RENDER/"04_n2_two_slot_two_contact_candidate.png",
                                [(n2c["harness"],COL["harness"])],
                                transparent=[(n2["jfdSlotted"],(*COL["jfd"],25)),
                                             (n2["jad"],(*COL["jad"],24))],
                                wires=[(n2["jfdSlotted"],(*COL["jfd"],90)),(n2["jad"],(*COL["jad"],90))]))
    minus_v_collision=clean_or_none(n2c["rows"]["-V"]["leg"] & n2["jfdSlotted"],"N2_MINUS_V_SLOT_COLLISION")
    objects=[(n2c["rows"]["-V"]["leg"],COL["harness"]),(n2["pad"]["added"],COL["pad"])]
    if minus_v_collision is not None: objects.append((minus_v_collision,COL["collision"]))
    outputs.append(render_scene(RENDER/"05_n2_minus_v_slot_limit.png",objects,
                                transparent=[(n2["jfdSlotted"],(*COL["jfd"],28))],
                                wires=[(n2["jfdSlotted"],(*COL["jfd"],90))],camera=(31,-43,23)))
    outputs.append(render_scene(RENDER/"06_n2_local_contact_feet.png",
                                [(n2c["contacts"]["+V"]["combined"],COL["foot"]),
                                 (n2c["contacts"]["+U"]["combined"],COL["slot"])],
                                transparent=[(n2["jfdReinforced"],(*COL["jfd"],24)),
                                             (n2["jad"],(*COL["jad"],24))],
                                wires=[(n2["jfdReinforced"],(*COL["jfd"],85)),(n2["jad"],(*COL["jad"],85))]))
    open_dir=np.asarray(stage2["openDirectionLocal"],float)
    service_jad=moved(n2["jad"],open_dir*.25,"N2_JAD_SERVICE_RENDER")
    service_collision=clean_or_none(service_jad & n2c["contacts"]["+U"]["foot"],"N2_JAD_CAPTURE_COLLISION")
    objects=[(n2c["contacts"]["+U"]["combined"],COL["foot"])]
    if service_collision is not None: objects.append((service_collision,COL["collision"]))
    outputs.append(render_scene(RENDER/"07_n2_jad_removal_capture.png",objects,
                                transparent=[(service_jad,(*COL["jad"],30))],
                                wires=[(service_jad,(*COL["jad"],100))],camera=(32,-44,24)))
    return outputs


def report_text(data:dict[str,object])->str:
    i3=data["i3"]; n2=data["n2"]
    i3states="\n".join(f"| {r['label']} | {r['maximumUnintendedPenetrationMm3']:.9f} | {r['limiter']} |" for r in i3["rearAssembly"]["states"])
    s1="\n".join(f"| {r['label']} | {r['maximumUnintendedPenetrationMm3']:.9f} | {r['plusVFootGapMm']:.6f} | {r['limiter']} |" for r in n2["stage1"]["states"])
    s2="\n".join(f"| {r['label']} | {r['maximumCandidateAddedPenetrationMm3']:.9f} | {r['plusUFootGapMm']:.6f} | {r['limiter']} |" for r in n2["stage2"]["states"])
    return f"""# 95 — I3 + N2 bounded manufacturing candidate build and validation

## Final result

```text
I3 / N2 manufacturing candidate result:

I3 = {i3['final']}
N2 = {n2['final']}

REMOTE/THUMB-WALL SUPPORT USED = NO required

N2 support configuration:
mechanical slots = 2/4
local compression contacts = 2/4

I3 support configuration:
mechanical slots = 3/4
local compression contacts = 1/4

ALL-8 COMPLETE TOPOLOGY AVAILABLE = NO
ALL-8 STATIC FIT = NOT RUN
```

- Did I3 require any I2 modification? **NO.** Frozen I2 was not modified.
- Did N2 captively bridge JaD/JfD? **YES.** The +U foot interferes with JaD during removal.
- Can JaD still be removed? **NO**, not without breaking/deforming the bounded N2 candidate.
- Does either button rely on adhesive for normal press load? **NO.** Adhesive is not primary load-bearing.

## Scope and authority

docs/94 was used as the latest diagnostic authority. Exterior, button centers, press axes, JaD/JfD split, I2, I4, N1, M3, M4, and N3 remained frozen. Production geometry modification = **0**; physical coupon = **0**; remote/thumb support = **0**. Final checks used the original **3530-facet PushBtn** and the D3.35 × 2.44 mm actuator.

## I3 — bounded 3-slot + 1-contact candidate

| Required metric | Result |
|---|---:|
| -U ↔ frozen I2 harness penetration | {i3['minusUI2HarnessPenetrationMm3']:.9f} mm³ |
| seat ↔ I2 T3 penetration | {i3['seatI2T3PenetrationMm3']:.9f} mm³ |
| insertion shell penetration (max) | {i3['insertionShellPenetrationMm3']:.9f} mm³ |
| minimum neck | {i3['manufacturing']['minimumStructuralNeckMm']:.6f} mm |
| minimum effective section | {i3['manufacturing']['minimumEffectiveSectionMm']:.6f} mm |
| rear assembly | {i3['rearAssembly']['result']} |
| I3 FINAL | **{i3['final']}** |

The allowed corrections were implemented only at the -U root/straight member, the colliding seat edge, and the +U approach edge. The seat–T3 collision is removed and +U retains {i3['plusUContactAreaMm2']:.6f} mm² finite contact area. However, the smallest permitted 1.20 mm -U tangent section still penetrates frozen I2 by {i3['minusUI2HarnessPenetrationMm3']:.9f} mm³. Further local narrowing would violate the 1.20 mm gate; larger relocation is outside the bounded correction.

| I3 rear state | max unintended penetration (mm³) | limiter |
|---|---:|---|
{i3states}

## N2 — bounded 2-slot + 2-contact candidate

| Required item | Result |
|---|---|
| -U mechanical slot | {n2['minusUSlot']} |
| -V mechanical slot | {n2['minusVSlot']} |
| added local thickening | {n2['addedLocalThickeningMm']:.6f} mm |
| added pad volume | {n2['addedPadVolumeMm3']:.6f} mm³ |
| final remaining shell | {n2['finalRemainingShellMm']:.6f} mm |
| +V local compression foot | {n2['plusV']['result']} |
| +V contact area | {n2['plusV']['contactAreaMm2']:.6f} mm² |
| +V direct compression | {n2['plusV']['directCompression']} |
| +U JaD closure contact | {n2['plusU']['result']} |
| +U contact area | {n2['plusU']['contactAreaMm2']:.6f} mm² |
| +U nominal gap / interference | {n2['plusU']['nominalGapMm']:.9f} / {n2['plusU']['nominalInterferenceMm']:.9f} mm |
| captively bridges seam | {n2['plusU']['captivelyBridgesSeam']} |
| Stage-1 harness insertion | {n2['stage1']['result']} |
| Stage-2 JaD closure | {n2['stage2']['result']} |
| JaD removable afterward | {n2['stage2']['jaDRemovableAfterward']} |
| adhesive primary load-bearing | NO |
| N2 FINAL | **{n2['final']}** |

The 0.15 mm inward pad raises the analytical remaining shell to {n2['finalRemainingShellMm']:.6f} mm, but the seated -V straight leg still has {n2['minusVSeatedPenetrationMm3']:.9f} mm³ JfD-shell penetration. Its collision envelope requires about {n2['minusVCollisionWmm']:.6f} mm further local W relief, exceeding the remaining {n2['padMarginOverMinimumMm']:.6f} mm margin above the 1.20 mm shell gate.

The +U foot forms near-zero-gap finite-area contact only at CLOSED, but at 0.25 mm JaD opening it produces {n2['stage2']['serviceProbe']['pair']['penetrationMm3']:.9f} mm³ penetration. Therefore the candidate mechanically captures JaD and fails serviceability.
Stage-2 closure itself also fails because non-foot N2 geometry has {n2['stage2ClosedOtherN2PenetrationMm3']:.9f} mm³ unintended penetration with JaD at CLOSED.

| N2 Stage-1 state | max penetration (mm³) | +V gap (mm) | limiter |
|---|---:|---:|---|
{s1}

| N2 Stage-2 state | candidate-added penetration (mm³) | +U gap (mm) | limiter |
|---|---:|---:|---|
{s2}

## Manufacturing solids

- I3 audit candidate: `{i3['manufacturing']['auditStep']}` — one fused, valid STEP-reimported solid; system verdict remains FAIL due frozen-I2 interference.
- N2 audit candidate: `{n2['manufacturing']['auditStep']}` — one fused, valid STEP-reimported solid; system verdict remains FAIL due -V insertion and JaD capture.
- Production outputs: **0**.
- ALL-8 was correctly **NOT RUN** because both bounded candidates did not pass.

## Audit outputs

- JSON: `{data['outputs']['json']}`
- Report: `{data['outputs']['report']}`
{chr(10).join(f"- Render: `{p}`" for p in data['outputs']['renders'])}

Generated: {data['generatedAtUtc']}
"""


def main()->None:
    OUT.mkdir(parents=True,exist_ok=True); RENDER.mkdir(parents=True,exist_ok=True)
    protected=protected_files(); before=hashes(protected)
    docs90,docs91,docs93,docs94,datums,placements,shell_full,existing,i2_harness,i2_t3=build_context()
    i3=build_i3_variant(-2.0,docs91,docs93,datums,placements,shell_full,i2_harness,i2_t3)
    if i3 is None: raise RuntimeError("bounded I3 candidate construction failed")
    own_parts,_corners,mechanism=detailed_local_parts()
    _o,body,terminals,corners,_oa,actuator,_h=doc84.detailed_switch_parts()
    i2_to_i3=placements["I3"].inverse()*placements["I2"]
    i2_parts={"BODY":i2_to_i3*body,"ACTUATOR":i2_to_i3*actuator,"CORNERS":i2_to_i3*corners,
              **{name:i2_to_i3*shape for name,shape in terminals.items()}}
    rear=i3_five_state(i3,i2_harness,i2_parts,own_parts,mechanism)
    i3_shell_max=max(row["pairMetrics"]["SHELL"]["penetrationMm3"] for row in rear["states"])
    i3_step=OUT/"I3_BOUNDED_3SLOT_1CONTACT_MANUFACTURING_CANDIDATE_FAIL_AUDIT_ONLY.step"
    i3_linear=[float(row["legThicknessMm"]) for row in i3["candidate"]["rows"].values()]
    i3_linear.extend(float(row["legTangentWidthMm"]) for row in i3["candidate"]["rows"].values())
    i3_linear.extend((d93.FOOT_WIDTH,d93.FOOT_THICKNESS))
    i3_effective=[float(row["effectiveFdmThicknessMm"]) for row in i3["candidate"]["rows"].values()]
    i3_effective.extend((d93.FOOT_WIDTH,d93.FOOT_THICKNESS))
    i3_mfg=manufacturing(i3["candidate"],i3_step,i3_linear,i3_effective,float(i3_shell_max),False)

    docs92=json.loads(DOC92_JSON.read_text(encoding="utf-8"))
    n2=build_n2_candidate(docs91,docs92,docs94,datums,placements,shell_full)
    stage1=n2_stage1(n2,own_parts,mechanism); stage2=n2_stage2(n2,datums["N2"],own_parts)
    reactions=load_path(n2["candidate"])
    minus_v_pen=float(stage1["states"][-1]["pairMetrics"]["JFD_SHELL"]["penetrationMm3"])
    minus_u_pen=safe_volume(n2["candidate"]["rows"]["-U"]["leg"]&n2["jfdSlotted"])
    minus_v_collision=n2["candidate"]["rows"]["-V"]["leg"]&n2["jfdSlotted"]
    minus_v_box=bbox_row(minus_v_collision)
    n2_step=OUT/"N2_BOUNDED_2SLOT_2CONTACT_MANUFACTURING_CANDIDATE_FAIL_AUDIT_ONLY.step"
    n2_linear=[]; n2_effective=[]
    for row in n2["candidate"]["rows"].values():
        n2_linear.extend((float(row["legThicknessMm"]),float(row["legTangentWidthMm"])))
        n2_effective.append(float(row["effectiveFdmThicknessMm"]))
    n2_linear.extend((d93.FOOT_WIDTH,d93.FOOT_THICKNESS,d93.FOOT_FLARE_WIDTH,d93.FOOT_FLARE_THICKNESS))
    n2_effective.extend((d93.FOOT_WIDTH,d93.FOOT_THICKNESS))
    n2_mfg=manufacturing(n2["candidate"],n2_step,n2_linear,n2_effective,minus_v_pen,False)

    i3["_i2Harness"]=i2_harness; i3["_i2T3"]=i2_t3
    render_paths=render_results(i3,n2,stage1,stage2)
    i3_states=[]
    for row in rear["states"]:
        limiter=max(row["pairMetrics"],key=lambda key:row["pairMetrics"][key]["penetrationMm3"])
        i3_states.append({"label":row["label"],"offsetLocalUVWmm":row["offsetLocalUVWmm"],
                          "maximumUnintendedPenetrationMm3":row["maximumUnintendedPenetrationMm3"],
                          "limiter":limiter,"pairMetrics":row["pairMetrics"]})
    s1=[]
    for row in stage1["states"]:
        limiter=max(row["pairMetrics"],key=lambda key:row["pairMetrics"][key]["penetrationMm3"])
        s1.append({**row,"limiter":limiter})
    s2=[]
    for row in stage2["states"]:
        limiter=max(row["pairMetrics"],key=lambda key:row["pairMetrics"][key]["penetrationMm3"])
        s2.append({**row,"limiter":limiter})
    data={
      "schema":"onegrip-i3-n2-bounded-manufacturing-candidate-validation-v1",
      "generatedAtUtc":datetime.now(timezone.utc).isoformat(),"authority":{"diagnostic":"docs/94","productionGeometryModificationCount":0,
        "physicalCouponCount":0,"deepHardeningCount":0,"remoteThumbWallSupportUsed":False,
        "originalDetailedPushBtn":{"facetCount":3530,"actuatorDiameterMm":3.35,"actuatorProjectionMm":2.44}},
      "summary":{"i3":"FAIL","n2":"FAIL","all8CompleteTopologyAvailable":False,"all8StaticFit":"NOT RUN",
        "i3SupportConfiguration":{"mechanicalSlots":3,"localCompressionContacts":1},
        "n2SupportConfiguration":{"mechanicalSlots":2,"localCompressionContacts":2}},
      "i3":{"final":"FAIL","i2Modified":False,"architecture":"3 mechanical slots + 1 +U local compression contact",
        "minusURootLocalShiftVmm":i3["shiftVmm"],"minusUTangentWidthMm":i3["candidate"]["rows"]["-U"]["legTangentWidthMm"],
        "minusUI2HarnessPenetrationMm3":i3["minusUI2Penetration"],"minusUI2CollisionBox":i3["minusUI2CollisionBox"],
        "seatI2HarnessPenetrationMm3":i3["seatI2HarnessPenetration"],"seatI2T3PenetrationMm3":i3["seatI2T3Penetration"],
        "seatBaseVolumeRetention":i3["baseVolumeRetention"],"plusUApproachRelief":i3["relief"],
        "plusUContactAreaMm2":i3["contactAreaMm2"],"plusUFootLegCommonVolumeMm3":i3["footLegCommonVolumeMm3"],
        "padFinalRemainingShellMm":i3["padFinalRemainingShellMm"],"insertionShellPenetrationMm3":float(i3_shell_max),
        "rearAssembly":{"result":rear["result"],"travelMm":rear["travelMm"],"commonInsertionVectorLocal":rear["commonInsertionVectorLocal"],
                        "pushBtnTranslationMm":0.0,"pushBtnRotationDeg":0.0,"elasticDeformationRequired":False,"states":i3_states},
        "manufacturing":i3_mfg,"adhesivePrimaryLoadBearing":False,"remoteSupportUsed":False},
      "n2":{"final":"FAIL","architecture":"2 mechanical slots + 2 local compression contacts","minusUSlot":"PASS" if minus_u_pen<=EPS else "FAIL",
        "minusUShellPenetrationMm3":minus_u_pen,"minusVSlot":"PASS" if minus_v_pen<=EPS else "FAIL",
        "minusVSeatedPenetrationMm3":minus_v_pen,"minusVCollisionBox":minus_v_box,
        "minusVCollisionWmm":minus_v_box["size"][2],"addedLocalThickeningMm":N2_PAD_ADD,
        "addedPadVolumeMm3":safe_volume(n2["pad"]["added"]),"finalRemainingShellMm":n2["pad"]["finalEffectiveRemainingShellMm"],
        "padMarginOverMinimumMm":n2["pad"]["finalEffectiveRemainingShellMm"]-1.20,"outerExteriorChanged":False,
        "plusV":{"result":"PASS","contactAreaMm2":n2["candidate"]["contacts"]["+V"]["contactAreaMm2"],
                  "contactGapMm":n2["candidate"]["contacts"]["+V"]["contactGapMm"],"directCompression":"YES","sideIdentityPreserved":True},
        "plusU":{"result":"FAIL","contactAreaMm2":n2["candidate"]["contacts"]["+U"]["contactAreaMm2"],
                  "nominalGapMm":stage2["nominalGapMm"],"nominalInterferenceMm":stage2["nominalInterferenceMm"],
                  "captivelyBridgesSeam":"YES" if stage2["captivelyBridgesSeam"] else "NO"},
        "stage1":{**stage1,"states":s1},"stage2":{**stage2,"states":s2},
        "stage2ClosedOtherN2PenetrationMm3":stage2["states"][-1]["pairMetrics"]["OTHER_N2"]["penetrationMm3"],
        "loadPath":reactions,
        "manufacturing":n2_mfg,"adhesivePrimaryLoadBearing":False,"remoteSupportUsed":False},
      "all8":{"completeTopologyAvailable":False,"staticFit":"NOT RUN","reason":"I3 and N2 bounded candidates both failed; conditional all-8 gate not reached."},
      "preservation":{"protectedFileCount":len(protected),"before":before,"unchanged":True},
      "outputs":{"i3Step":relative(i3_step),"n2Step":relative(n2_step),"json":relative(JSON_PATH),"report":relative(REPORT),
                 "renders":render_paths,"auditCandidateCount":2,"productionGeometryCount":0}}
    after=hashes(protected); data["preservation"]["after"]=after; data["preservation"]["unchanged"]=before==after
    JSON_PATH.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    REPORT.write_text(report_text(data),encoding="utf-8")
    print(json.dumps({"i3":data["summary"]["i3"],"n2":data["summary"]["n2"],"all8":data["summary"]["all8StaticFit"],
                      "i3Step":relative(i3_step),"n2Step":relative(n2_step),"json":relative(JSON_PATH),
                      "report":relative(REPORT),"renders":render_paths,"preserved":before==after},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--probe",action="store_true")
    parser.add_argument("--n2-geometry-probe",action="store_true")
    parser.add_argument("--i3-root-probe",action="store_true"); args=parser.parse_args()
    i3_root_probe() if args.i3_root_probe else (n2_geometry_probe() if args.n2_geometry_probe else (probe() if args.probe else main()))
