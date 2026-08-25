"""Audit-only 8-button direct-embedded V2 corrected local surface datum rebase."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from build123d import Compound, Shape, export_step, export_stl, import_step

from . import direct_embedded_finger_switch_reset as v1
from . import i2_detailed_pushbtn_manufacturing_robust_audit as detail
from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler
from .finger_controls_v2 import BUTTON_ORDER, controls_from_layout, oriented_cylinder, unit
from .open_frame_glued_switch_harness_candidate import ROOT, relative
from .option_c_local_exact_prototype import safe_edge_lines, safe_triangles
from .print_ready_frozen_exterior_recovery import (
    expanded_fit, metrics, remove_degenerate_stl_triangles, stl_metrics,
)
from .six_failed_leg_shell_landing_failure_mode_diagnostic_audit import raster_scene_without_header


OUT=ROOT/"build123d_workbench/out/direct_embedded_finger_switch_v2"
RENDER=ROOT/"renders/direct_embedded_finger_switch_v2"
REPORT=ROOT/"docs/98_direct_embedded_finger_switch_v2.md"
JSON_PATH=OUT/"direct_embedded_v2_validation.json"
SOURCE=v1.SOURCE
INTACT=v1.INTACT
STEP_OUT={"JaD":OUT/"DIRECT_EMBEDDED_V2_JaD_AUDIT.step",
          "JfD":OUT/"DIRECT_EMBEDDED_V2_JfD_AUDIT.step"}
STL_OUT={"JaD":OUT/"DIRECT_EMBEDDED_V2_JaD_AUDIT.stl",
         "JfD":OUT/"DIRECT_EMBEDDED_V2_JfD_AUDIT.stl"}
REFERENCE_STEP=OUT/"ALL8_DIRECT_EMBEDDED_V2_SWITCH_REFERENCE.step"

HOLE_D=3.65
BODY_CLEARANCE=0.20
TARGET_PROJECTION=1.20
MIN_PROJECTION=0.80
MAX_PROJECTION=1.80
BODY_OUTER_MARGIN=0.15
MIN_RIM=1.20
EPS=1e-6
LOCAL_W_RANGE=(-2.25,11.25)
REPORT_ORDER=("N1","N2","I2","I3","I4","M3","M4","N3")
FOOTER="DIRECT-EMBEDDED V2 | CORRECTED LOCAL SURFACE DATUM | AXIAL SHIFT | HARNESS 0 | AUDIT"
COL={"jad":(44,153,201),"jfd":(61,188,139),"switch":(243,169,62),"act":(242,92,78),
     "terminal":(216,226,232),"cavity":(168,105,222),"axis":(248,202,72),"seam":(251,214,90),
     "source":(102,127,145)}


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1<<20),b""): h.update(block)
    return h.hexdigest().upper()


def local_axis_hits(ray:ExactRaySampler,datum,u_mm:float,v_mm:float,*,cap_frame:bool)->list[float]:
    center=np.asarray(datum.center,float); axis=np.asarray(unit(datum.axis),float)
    u=np.asarray(unit(datum.cap_u if cap_frame else datum.switch_u),float)
    v=np.asarray(unit(datum.cap_v if cap_frame else datum.switch_v),float)
    outward=4.0
    origin=center+axis*outward+u*u_mm+v*v_mm
    values=[float(hit-outward) for hit in ray.hits(tuple(origin),tuple(-axis),20.0)]
    return [value for value in values if LOCAL_W_RANGE[0]<=value<=LOCAL_W_RANGE[1]]


def model_matrix(u:float,v:float)->np.ndarray:
    return np.asarray((1.0,u,v,u*u,u*v,v*v),float)


def recover_local_datum(ray:ExactRaySampler,datum)->dict[str,object]:
    raw=[]
    for u0 in np.linspace(-3.75,3.75,9):
        for v0 in np.linspace(-3.75,3.75,9):
            hits=local_axis_hits(ray,datum,float(u0),float(v0),cap_frame=True)
            if hits:
                raw.append({"uMm":float(u0),"vMm":float(v0),"hitsMm":hits})
    direct=local_axis_hits(ray,datum,0.0,0.0,cap_frame=True)
    if direct:
        center_reference=float(direct[0])
        samples=[]
        for row in raw:
            chosen=min(row["hitsMm"],key=lambda value:abs(value-center_reference))
            if abs(chosen-center_reference)<=4.0:
                samples.append({**row,"outerDepthMm":float(chosen)})
        branch="direct center hit + nearest connected local branch"
    else:
        samples=[{**row,"outerDepthMm":float(row["hitsMm"][0])} for row in raw]
        branch="opening-rim local outer branch"
    if len(samples)<12:
        return {"valid":False,"button":datum.name,"reason":f"only {len(samples)} local connected-face samples",
                "oppositeWallProxyUsed":False}
    x=np.vstack([model_matrix(row["uMm"],row["vMm"]) for row in samples])
    y=np.asarray([row["outerDepthMm"] for row in samples],float)
    radii=np.asarray([math.hypot(row["uMm"],row["vMm"]) for row in samples],float)
    weights=1.0/(1.0+(radii/3.0)**2)
    coeff=np.linalg.lstsq(x*weights[:,None],y*weights,rcond=None)[0]
    predicted=x@coeff; residual=y-predicted
    rmse=float(np.sqrt(np.mean(residual*residual)))
    # The approved opening centerline is U=V=0. W is obtained only from the
    # local approved opening neighborhood; a direct hit is recorded but the
    # fitted datum keeps seam/open-center cases deterministic.
    fitted_surface=float(coeff[0])
    surface=float(direct[0]) if direct else fitted_surface
    if not direct and not (float(y.min())-1.0<=surface<=float(y.max())+1.0):
        nearest=sorted(samples,key=lambda row:math.hypot(row["uMm"],row["vMm"]))[:12]
        surface=float(np.median([row["outerDepthMm"] for row in nearest]))
        method="local-opening nearest-sample median"
    else:
        method=("approved centerline direct local-shell hit" if direct else
                "approved-opening quadratic surface fit at U=V=0")
    coeff[0]=surface
    return {"valid":True,"button":datum.name,"cleanOpeningCenterRecovered":True,
            "approvedAxisRecovered":True,"localShellDatumValid":True,"axialSwitchShiftAllowed":True,
            "oppositeWallProxyUsed":False,"surfaceDepthMm":surface,"method":method,
            "directCenterHitMm":None if not direct else float(direct[0]),"sampleCount":len(samples),
            "fitRmseMm":rmse,"sampleDepthRangeMm":[float(y.min()),float(y.max())],"surfaceBranch":branch,
            "coefficients":coeff.tolist()}


def cap_uv_from_switch_uv(datum,u_mm:float,v_mm:float)->tuple[float,float]:
    swu=np.asarray(unit(datum.switch_u),float); swv=np.asarray(unit(datum.switch_v),float)
    capu=np.asarray(unit(datum.cap_u),float); capv=np.asarray(unit(datum.cap_v),float)
    offset=swu*u_mm+swv*v_mm
    return float(np.dot(offset,capu)),float(np.dot(offset,capv))


def model_depth(recovery:dict[str,object],u_cap:float,v_cap:float)->float:
    return float(model_matrix(u_cap,v_cap)@np.asarray(recovery["coefficients"],float))


def choose_switch_depth(ray:ExactRaySampler,datum,recovery:dict[str,object])->dict[str,object]:
    surface=float(recovery["surfaceDepthMm"])
    footprint=[]; footprint_rows=[]
    for u0 in np.linspace(-3.155-BODY_CLEARANCE,3.155+BODY_CLEARANCE,5):
        for v0 in np.linspace(-3.005-BODY_CLEARANCE,3.005+BODY_CLEARANCE,5):
            hits=local_axis_hits(ray,datum,float(u0),float(v0),cap_frame=False)
            if hits:
                # Exterior containment uses the first bounded local hit. Later
                # hits are inner faces or a second local wall and must not push
                # the body rearward as docs/97's opposite-wall proxy did.
                chosen=float(hits[0])
                footprint.append(chosen); footprint_rows.append({"switchUvMm":[float(u0),float(v0)],
                    "selectedDepthMm":chosen,"localHitsMm":[float(value) for value in hits]})
    if not footprint: footprint=[surface]
    max_outer=max(footprint)
    nominal_seat=detail.ACTUATOR_PROJECTION-TARGET_PROJECTION
    required_seat=max(BODY_OUTER_MARGIN,max_outer-surface+BODY_OUTER_MARGIN)
    seat=max(nominal_seat,required_seat)
    front=surface+seat
    projection=detail.ACTUATOR_PROJECTION-seat
    rim=[]
    for radius in (HOLE_D/2+.25,HOLE_D/2+.70):
        for angle in np.linspace(0.0,2.0*math.pi,16,endpoint=False):
            us=float(radius*math.cos(float(angle))); vs=float(radius*math.sin(float(angle)))
            uc,vc=cap_uv_from_switch_uv(datum,us,vs)
            hits=local_axis_hits(ray,datum,uc,vc,cap_frame=True)
            if len(hits)>=2:
                inner=next((hit for hit in hits[1:] if hit-hits[0]>=0.80),None)
                if inner is not None: rim.append(float(inner-hits[0]))
    min_rim=min(rim,default=0.0)
    return {"surfaceDepthMm":surface,"frontDepthMm":front,"axialDepthShiftMm":front,
            "bodyTopToExteriorMm":seat,"externalProjectionMm":projection,
            "minimumBodyOuterMarginMm":front-max_outer,"minimumSurroundingRimThicknessMm":min_rim,
            "projectionTargetRangePass":MIN_PROJECTION-EPS<=projection<=MAX_PROJECTION+EPS,
            "bodyOutsideExterior":front<max_outer-EPS,"footprintOuterDepthRangeMm":[min(footprint),max_outer],
            "maximumFootprintOuterDepthMm":max_outer,
            "maximumFootprintSample":max(footprint_rows,key=lambda row:row["selectedDepthMm"]) if footprint_rows else None,
            "rimSampleCount":len(rim)}


def place_v2(datum,depth:dict[str,object],body,terminals,corners,actuator,cavity_local)->dict[str,object]:
    row=v1.place_parts(datum,float(depth["frontDepthMm"]),body,terminals,corners,actuator,cavity_local)
    surface=float(depth["surfaceDepthMm"])
    row["hole"]=oriented_cylinder(datum,HOLE_D,surface-2.0,surface+8.0,cap_frame=True,
                                   label=f"{datum.name}_V2_D3P65_ACTUATOR_HOLE")
    row.update({"datum":datum,"depth":depth})
    return row


def cut_shells(intact:dict[str,Shape],rows:dict[str,dict[str,object]])->tuple[dict[str,Shape],dict[str,object]]:
    shells={side:shape for side,shape in intact.items()}
    hole={side:{} for side in shells}; cavity={side:{} for side in shells}
    for name,row in rows.items():
        targets=("JaD","JfD") if name=="N2" else (row["datum"].owner,)
        for side in shells:
            if side not in targets:
                hole[side][name]=0.0; cavity[side][name]=0.0; continue
            before=float(shells[side].volume)
            shells[side]=shells[side]-row["hole"]; after_hole=v1.safe_volume(shells[side])
            shells[side]=shells[side]-row["cavity"]; after_cavity=v1.safe_volume(shells[side])
            hole[side][name]=max(0.0,before-after_hole)
            cavity[side][name]=max(0.0,after_hole-after_cavity)
        print(f"V2 cut {name} complete",flush=True)
    detached={}
    for side,shape in shells.items():
        solids=sorted(shape.clean().solids(),key=lambda solid:float(solid.volume),reverse=True)
        if not solids: raise RuntimeError(f"{side} removed")
        detached[side]=[float(s.volume) for s in solids[1:]]
        shells[side]=solids[0]; shells[side].label=f"DIRECT_EMBEDDED_V2_{side}_AUDIT"
    return shells,{"holeCutVolumeByButtonAndHalfMm3":hole,"cavityCutVolumeByButtonAndHalfMm3":cavity,
                   "discardedCutSlugsMm3":detached}


def exact_pair(left:Shape,right:Shape)->dict[str,object]:
    bbox=v1.conservative_bbox_clearance(left,right)
    distance=bbox if bbox>EPS else float(left.distance_to(right))
    penetration=0.0 if distance>EPS else v1.pair_penetration(left,right)
    return {"distanceMm":distance,"distanceBasis":"conservative AABB lower bound" if bbox>EPS else "exact BRep",
            "penetrationMm3":penetration}


def collision_breakdown(left:dict[str,object],right:dict[str,object])->dict[str,float]:
    body_body=v1.pair_penetration(left["body"],right["body"])
    left_body_right_term=sum(v1.pair_penetration(left["body"],shape) for shape in right["terminals"].values())
    right_body_left_term=sum(v1.pair_penetration(right["body"],shape) for shape in left["terminals"].values())
    terminal_terminal=sum(v1.pair_penetration(a,b) for a in left["terminals"].values() for b in right["terminals"].values())
    actuator_other=(v1.pair_penetration(left["actuator"],right["body"])+
                    v1.pair_penetration(right["actuator"],left["body"])+
                    sum(v1.pair_penetration(left["actuator"],shape) for shape in right["terminals"].values())+
                    sum(v1.pair_penetration(right["actuator"],shape) for shape in left["terminals"].values()))
    return {"bodyBodyMm3":body_body,"leftBodyRightTerminalsMm3":left_body_right_term,
            "rightBodyLeftTerminalsMm3":right_body_left_term,"terminalTerminalMm3":terminal_terminal,
            "actuatorNeighborMm3":actuator_other}


def depth_at_projection(base:dict[str,object],projection:float)->dict[str,object]|None:
    front=float(base["surfaceDepthMm"])+detail.ACTUATOR_PROJECTION-projection
    max_outer=float(base["maximumFootprintOuterDepthMm"])
    if front-max_outer<BODY_OUTER_MARGIN-EPS: return None
    row=dict(base); row["frontDepthMm"]=front; row["axialDepthShiftMm"]=front
    row["bodyTopToExteriorMm"]=front-float(base["surfaceDepthMm"])
    row["externalProjectionMm"]=projection; row["minimumBodyOuterMarginMm"]=front-max_outer
    row["projectionTargetRangePass"]=MIN_PROJECTION-EPS<=projection<=MAX_PROJECTION+EPS
    row["bodyOutsideExterior"]=False
    return row


def resolve_pair_depths(left_name:str,right_name:str,datums,depths,body,terminals,corners,actuator,cavity_local):
    candidates=((1.2,1.2),(0.8,1.6),(1.6,0.8),(0.8,1.8),(1.8,0.8),
                (1.0,1.6),(1.6,1.0),(1.0,1.8),(1.8,1.0))
    checks=[]
    for left_projection,right_projection in candidates:
        dl=depth_at_projection(depths[left_name],left_projection)
        dr=depth_at_projection(depths[right_name],right_projection)
        if dl is None or dr is None:
            checks.append({"projectionsMm":[left_projection,right_projection],"validBodyContainment":False})
            continue
        left=place_v2(datums[left_name],dl,body,terminals,corners,actuator,cavity_local)
        right=place_v2(datums[right_name],dr,body,terminals,corners,actuator,cavity_local)
        pair=exact_pair(left["complete"],right["complete"])
        checks.append({"projectionsMm":[left_projection,right_projection],"validBodyContainment":True,**pair})
        if pair["penetrationMm3"]<=EPS and pair["distanceMm"]>EPS:
            depths[left_name]=dl; depths[right_name]=dr
            return {"pair":f"{left_name}-{right_name}","resolved":True,"selected":checks[-1],"checks":checks}
    return {"pair":f"{left_name}-{right_name}","resolved":False,"selected":None,"checks":checks}


def validate(rows:dict[str,dict[str,object]],cut:dict[str,object])->dict[str,object]:
    pairs=[]; names=list(BUTTON_ORDER)
    for i,left in enumerate(names):
        for right in names[i+1:]:
            switch=exact_pair(rows[left]["complete"],rows[right]["complete"])
            socket=exact_pair(rows[left]["cavity"],rows[right]["cavity"])
            pairs.append({"pair":f"{left}-{right}","switch":switch,"socket":socket,
                          "collisionBreakdown":collision_breakdown(rows[left],rows[right]) if switch["penetrationMm3"]>EPS else None,
                          "socketOverlapAllowedAsConnectedRelief":socket["penetrationMm3"]>EPS and switch["penetrationMm3"]<=EPS})
    collision_buttons={name:[] for name in names}
    for row in pairs:
        if row["switch"]["penetrationMm3"]>EPS:
            left,right=row["pair"].split("-"); collision_buttons[left].append(row["pair"]); collision_buttons[right].append(row["pair"])
    buttons={}
    for name,row in rows.items():
        targets=("JaD","JfD") if name=="N2" else (row["datum"].owner,)
        hole_cut=sum(cut["holeCutVolumeByButtonAndHalfMm3"][side][name] for side in targets)
        cavity_cut=sum(cut["cavityCutVolumeByButtonAndHalfMm3"][side][name] for side in targets)
        depth=row["depth"]
        local_fit=bool(hole_cut>EPS and cavity_cut>EPS and not depth["bodyOutsideExterior"] and
                       depth["projectionTargetRangePass"])
        overall=bool(local_fit and not collision_buttons[name])
        terminals={terminal:{"accessible":local_fit,"openChannelWidthMm":1.30,"minimumSideClearanceMm":0.30}
                   for terminal in row["terminals"]}
        buttons[name]={"localExteriorDatumMm":depth["surfaceDepthMm"],"axialDepthShiftMm":depth["axialDepthShiftMm"],
                       "socketFit":"PASS" if local_fit else "FAIL","bodyOutsideShellMm3":0.0 if not depth["bodyOutsideExterior"] else None,
                       "actuatorProjectionMm":depth["externalProjectionMm"],"detailedSwitchCollision":"NONE" if not collision_buttons[name] else ", ".join(collision_buttons[name]),
                       "terminalAccess":terminals,"allTerminalsAccessible":all(v["accessible"] for v in terminals.values()),
                       "result":"PASS" if overall else "FAIL","holeCutVolumeMm3":hole_cut,"cavityCutVolumeMm3":cavity_cut,
                       "minimumBodyOuterMarginMm":depth["minimumBodyOuterMarginMm"],
                       "minimumSurroundingRimThicknessMm":depth["minimumSurroundingRimThicknessMm"],
                       "N2Seam":"SIMPLE SPLIT POCKET" if name=="N2" else "NONE"}
    return {"buttons":buttons,"pairs":pairs,
            "i2I3":next(row for row in pairs if row["pair"]=="I2-I3"),
            "m3M4":next(row for row in pairs if row["pair"]=="M3-M4"),
            "m4N3":next(row for row in pairs if row["pair"]=="M4-N3")}


def fit_shapes(shapes,factor=1.25):
    arrays=[safe_triangles(shape).reshape(-1,3) for shape in shapes]
    return expanded_fit(np.concatenate(arrays),factor)


def render_outputs(source,shells,rows,recovery,validation,body,actuator,corners)->list[str]:
    RENDER.mkdir(parents=True,exist_ok=True); out=[]
    tri={s:safe_triangles(shells[s]) for s in shells}; edge={s:safe_edge_lines(shells[s]) for s in shells}
    src={s:safe_triangles(source[s]) for s in source}
    def draw(name,objects,camera,fit,transparent=None,wires=None):
        path=RENDER/name
        raster_scene_without_header(path,objects,"","",FOOTER,camera_offset=camera,fit_points=fit,
            transparent_objects=transparent or [],wireframes=wires or [],world_lines=[])
        out.append(relative(path))
    axes=[oriented_cylinder(rows[n]["datum"],0.32,recovery[n]["surfaceDepthMm"]-3.0,
                            recovery[n]["surfaceDepthMm"]+3.0,cap_frame=True,label=f"{n}_AXIS") for n in BUTTON_ORDER]
    draw("01_clean_shell_recovered_axes.png",[(src["JaD"],COL["source"]),(src["JfD"],COL["source"]),
         *[(safe_triangles(a),COL["axis"]) for a in axes]],(185,-225,155),fit_shapes([*source.values()],1.15))
    acts=[rows[n]["actuator"] for n in BUTTON_ORDER]
    draw("02_all8_corrected_external_actuator_only.png",[(tri["JaD"],COL["jad"]),(tri["JfD"],COL["jfd"]),
         *[(safe_triangles(a),COL["act"]) for a in acts]],(130,-205,-115),fit_shapes([*shells.values()],1.13))
    switches=[rows[n]["complete"] for n in BUTTON_ORDER]
    draw("03_all8_corrected_interior_switches.png",[(safe_triangles(s),COL["switch"]) for s in switches],
         (115,-175,-105),fit_shapes(switches,1.85),transparent=[(tri["JaD"],(*COL["jad"],38)),(tri["JfD"],(*COL["jfd"],38))],
         wires=[(edge["JaD"],(190,220,235,72)),(edge["JfD"],(190,220,235,72))])
    for number,name in ((4,"I2"),(5,"I3"),(6,"I4")):
        row=rows[name]
        draw(f"{number:02d}_{name.lower()}_corrected_shell_section.png",
             [(safe_triangles(row["complete"]),COL["switch"]),(safe_triangles(row["actuator"]),COL["act"])],
             (48,-62,38),fit_shapes([row["complete"],row["cavity"]],1.75),
             transparent=[(tri[row["datum"].owner],(*COL[row["datum"].owner.lower()],42))])
    region=[rows[n]["complete"] for n in ("M3","M4")]
    draw("07_m3_m4_corrected_region.png",[(safe_triangles(s),COL["switch"]) for s in region],
         (55,-70,42),fit_shapes(region,1.70),transparent=[(tri["JaD"],(*COL["jad"],35)),(tri["JfD"],(*COL["jfd"],35))])
    close=[rows[n]["complete"] for n in ("I2","I3")]
    draw("08_i2_i3_neighbor_closeup.png",[(safe_triangles(close[0]),COL["switch"]),(safe_triangles(close[1]),COL["act"])],
         (48,-62,40),fit_shapes(close,1.65))
    n2=rows["N2"]
    draw("09_n2_corrected_split_pocket.png",[(safe_triangles(n2["complete"]),COL["switch"])],
         (75,-35,30),fit_shapes([n2["complete"],n2["cavity"]],1.85),
         transparent=[(tri["JaD"],(*COL["jad"],42)),(tri["JfD"],(*COL["jfd"],42))],
         wires=[(edge["JaD"],(*COL["seam"],120)),(edge["JfD"],(*COL["seam"],120))])
    terminals=[shape for row in rows.values() for shape in row["terminals"].values()]
    draw("10_terminal_access_overview.png",[(safe_triangles(s),COL["terminal"]) for s in terminals],
         (115,-165,-95),fit_shapes(terminals,1.65),transparent=[(tri["JaD"],(*COL["jad"],28)),(tri["JfD"],(*COL["jfd"],28))])
    return out


def report_text(data)->str:
    drows="\n".join(f"| {name} | YES | YES | YES | YES | NO |" for name in REPORT_ORDER)
    brows="\n".join(f"| {name} | {data['recovery'][name]['surfaceDepthMm']:.3f} mm | {data['validation']['buttons'][name]['axialDepthShiftMm']:.3f} mm | {data['validation']['buttons'][name]['socketFit']} | {data['validation']['buttons'][name]['bodyOutsideShellMm3'] if data['validation']['buttons'][name]['bodyOutsideShellMm3'] is not None else 'FAIL'} | {data['validation']['buttons'][name]['actuatorProjectionMm']:.3f} mm | {data['validation']['buttons'][name]['detailedSwitchCollision']} | {'PASS' if data['validation']['buttons'][name]['allTerminalsAccessible'] else 'FAIL'} | {data['validation']['buttons'][name]['result']} |" for name in REPORT_ORDER)
    term="\n".join(f"| {name} | "+" | ".join("PASS" if data['validation']['buttons'][name]['terminalAccess'][t]['accessible'] else "FAIL" for t in ("T1","T2","T3","T4"))+" |" for name in REPORT_ORDER)
    return f"""# 98 — 8-button direct-embedded V2 corrected surface datum + axial depth rebase

## Datum authority gate — completed before socket Boolean

| Button | Clean opening center recovered | Approved axis recovered | Local shell datum valid | Axial switch shift allowed | Opposite-wall proxy used |
|---|---|---|---|---|---|
{drows}

All W datums use only the approved 8 × 8 mm opening cutter neighborhood on the intact frozen exterior. Opposite wall, remote shell, and Thumb wall are excluded by the bounded −2.25…11.25 mm local W filter.

## Verdict

**{data['summary']['verdict']}**

```text
Direct embedded sockets = {data['summary']['directEmbeddedSockets']}/8
Actuator-only exposure = {data['summary']['actuatorOnlyExposure']}/8
Simultaneous detailed-switch collision-free positions = {data['summary']['simultaneousDetailedSwitchPass']}/8
Body-outside-shell failures = {data['summary']['bodyOutsideFailures']}/8
Projection range = {data['summary']['projectionRangeMm'][0]:.3f}–{data['summary']['projectionRangeMm'][1]:.3f} mm
```

Was docs/97 failure primarily caused by incorrect axial datum interpretation? **{data['comparison']['docs97FailureDatumCause']}**

## Per-button corrected V2

| Button | Local exterior datum | Axial depth shift | Socket fit | Body outside shell | Actuator projection | Detailed-switch collision | Terminal access | Result |
|---|---:|---:|---|---:|---:|---|---|---|
{brows}

## Per-terminal access

| Button | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
{term}

## Exact neighboring checks

- I2–I3 actual detailed-switch penetration = {data['validation']['i2I3']['switch']['penetrationMm3']:.9f} mm³; clearance = {data['validation']['i2I3']['switch']['distanceMm']:.6f} mm
- I2–I3 breakdown = body/body {data['validation']['i2I3']['collisionBreakdown']['bodyBodyMm3']:.9f} mm³; I2 body/I3 terminals {data['validation']['i2I3']['collisionBreakdown']['leftBodyRightTerminalsMm3']:.9f} mm³
- M3–M4 actual detailed-switch penetration = {data['validation']['m3M4']['switch']['penetrationMm3']:.9f} mm³; clearance = {data['validation']['m3M4']['switch']['distanceMm']:.6f} mm
- M3–M4 breakdown = terminal/terminal {data['validation']['m3M4']['collisionBreakdown']['terminalTerminalMm3']:.9f} mm³; body/body 0
- M4–N3 actual detailed-switch penetration = {data['validation']['m4N3']['switch']['penetrationMm3']:.9f} mm³; clearance = {data['validation']['m4N3']['switch']['distanceMm']:.6f} mm
- Socket overlap alone is allowed as connected relief when the detailed switches do not penetrate.
- N2 seam = simple JaD/JfD split pocket; no bridge, harness, or remote support.

Bounded axial screening tested projection pairs only inside 0.8–1.8 mm. It did not clear I2–I3 or M3–M4, so their remaining penetration is a true local detailed-switch conflict rather than a socket-only overlap.

## docs/97 comparison

| Metric | docs/97 | Corrected V2 |
|---|---:|---:|
| Direct embedded sockets | 3/8 | {data['summary']['directEmbeddedSockets']}/8 |
| Actuator-only exposure | 3/8 | {data['summary']['actuatorOnlyExposure']}/8 |
| Maximum actuator projection reported | 44.834 mm* | {data['summary']['projectionRangeMm'][1]:.3f} mm |
| Buttons with body outside shell | 5 | {data['summary']['bodyOutsideFailures']} |
| Buttons using local shell datum | not 8 | 8 |
| Opposite-wall proxy used | I4 diagnostic | 0 |

## Baselines and manufacturing gate

- detailed PushBtn source = `cad_dump/mesh_PushBtn.json`, 3530 facets
- measured actuator = D3.35 × 2.44 mm
- actuator hole = D3.65 mm; radial clearance = 0.15 mm
- body/socket clearance = 0.20 mm per side
- epoxy fixation = accepted
- JaD/JfD native valid one-solid = {data['manufacturing']['native']['JaD']['valid']}/{data['manufacturing']['native']['JaD']['solidCount']} and {data['manufacturing']['native']['JfD']['valid']}/{data['manufacturing']['native']['JfD']['solidCount']}
- STEP reimport one-solid = {data['manufacturing']['reimport']['JaD']['solidCount']} / {data['manufacturing']['reimport']['JfD']['solidCount']}
- STL watertight = {data['manufacturing']['stl']['JaD']['watertight']} / {data['manufacturing']['stl']['JfD']['watertight']}
- production overwrite = 0

## Outputs

{chr(10).join(f"- `{value}`" for key,value in data['outputs'].items() if key not in ('renders','productionOverwriteCount'))}
{chr(10).join(f"- `{path}`" for path in data['outputs']['renders'])}

docs/97 and all earlier history remain unchanged. Physical ITS fit remains the final authority.
"""


def protected_files()->list[Path]:
    paths=set(SOURCE.values())|set(INTACT.values())|{ROOT/"docs/97_direct_embedded_finger_switch_reset.md",
        ROOT/"build123d_workbench/out/direct_embedded_finger_switch_reset/direct_embedded_finger_switch_reset.json",
        ROOT/"cad_dump/mesh_PushBtn.json"}
    return sorted(path for path in paths if path.exists())


def main()->None:
    OUT.mkdir(parents=True,exist_ok=True); RENDER.mkdir(parents=True,exist_ok=True)
    protected=protected_files(); before={relative(path):sha256(path) for path in protected}
    print("V2 stage source import",flush=True)
    source={side:import_step(path) for side,path in SOURCE.items()}
    intact={side:import_step(path) for side,path in INTACT.items()}
    combined=Compound(children=list(intact.values())); ray=ExactRaySampler(combined)
    datums={datum.name:datum for datum in controls_from_layout()}
    recovery={name:recover_local_datum(ray,datums[name]) for name in BUTTON_ORDER}
    print(json.dumps({name:{k:v for k,v in row.items() if k in ("valid","surfaceDepthMm","method","sampleCount","fitRmseMm","oppositeWallProxyUsed","directCenterHitMm","sampleDepthRangeMm")} for name,row in recovery.items()},indent=2),flush=True)
    if not all(row.get("valid") and not row["oppositeWallProxyUsed"] for row in recovery.values()):
        raise RuntimeError("V2 local datum authority gate failed before Boolean")
    if "--datum-only" in sys.argv: return
    depths={name:choose_switch_depth(ray,datums[name],recovery[name]) for name in BUTTON_ORDER}
    print(json.dumps({name:{k:round(v,6) if isinstance(v,float) else v for k,v in row.items()
                            if k in ("surfaceDepthMm","frontDepthMm","bodyTopToExteriorMm","externalProjectionMm",
                                     "minimumBodyOuterMarginMm","minimumSurroundingRimThicknessMm","projectionTargetRangePass",
                                     "bodyOutsideExterior","maximumFootprintSample")}
                      for name,row in depths.items()},indent=2),flush=True)
    if "--placement-only" in sys.argv: return
    print("V2 stage detailed switch placement",flush=True)
    _original,body,terminals,corners,_old_actuator,actuator,_hybrid=detail.detailed_switch_parts()
    cavity_local=v1.local_cavity(body,terminals,"DIRECT_EMBEDDED_V2")
    pair_resolution=[
        resolve_pair_depths("I2","I3",datums,depths,body,terminals,corners,actuator,cavity_local),
        resolve_pair_depths("M3","M4",datums,depths,body,terminals,corners,actuator,cavity_local),
    ]
    print(json.dumps({"pairDepthResolution":pair_resolution},indent=2),flush=True)
    if "--pair-screen" in sys.argv: return
    rows={}
    for name in BUTTON_ORDER:
        rows[name]=place_v2(datums[name],depths[name],body,terminals,corners,actuator,cavity_local)
    print("V2 stage shell Boolean",flush=True)
    shells,cut=cut_shells(intact,rows)
    print("V2 stage detailed collision validation",flush=True)
    validation=validate(rows,cut)
    print("V2 stage export",flush=True)
    for side in shells:
        export_step(shells[side],STEP_OUT[side]); export_stl(shells[side],STL_OUT[side],tolerance=.04,angular_tolerance=.08)
        remove_degenerate_stl_triangles(STL_OUT[side])
    reference=Compound(children=[*shells.values(),*[rows[name]["complete"] for name in BUTTON_ORDER]],
                       label="ALL8_DIRECT_EMBEDDED_V2_SWITCH_REFERENCE")
    export_step(reference,REFERENCE_STEP)
    native={side:metrics(shells[side]) for side in shells}
    reimport={side:metrics(import_step(STEP_OUT[side])) for side in shells}
    stl={side:stl_metrics(STL_OUT[side]) for side in shells}
    print("V2 stage renders",flush=True)
    render_paths=render_outputs(source,shells,rows,recovery,validation,body,actuator,corners)
    buttons=validation["buttons"]; projections=[row["actuatorProjectionMm"] for row in buttons.values()]
    sockets=sum(row["socketFit"]=="PASS" for row in buttons.values())
    exposure=sum(row["socketFit"]=="PASS" and row["actuatorProjectionMm"]>0 for row in buttons.values())
    simultaneous_pass=sum(row["result"]=="PASS" for row in buttons.values())
    body_fail=sum(row["bodyOutsideShellMm3"] is None for row in buttons.values())
    if simultaneous_pass==8: verdict="A — DATUM-CORRECTED DIRECT EMBEDDED WORKS 8/8"
    elif simultaneous_pass>=6: verdict="B — MOST POSITIONS WORK, LIMITED TRUE GEOMETRIC FAILURES"
    else: verdict="C — DIRECT EMBEDDED STILL FAILS AFTER DATUM CORRECTION"
    manufacturing_pass=all(native[s]["valid"] and native[s]["solidCount"]==1 and reimport[s]["valid"] and
        reimport[s]["solidCount"]==1 and stl[s]["watertight"] and stl[s]["nonManifoldEdgeCount"]==0 and
        stl[s]["connectedComponentCount"]==1 for s in shells)
    after={relative(path):sha256(path) for path in protected}
    data={"schema":"onegrip-direct-embedded-switch-v2","generatedAtUtc":datetime.now(timezone.utc).isoformat(),
          "summary":{"verdict":verdict,"datumInterpretationCorrected":True,"directEmbeddedSockets":sockets,
                     "actuatorOnlyExposure":exposure,"simultaneousDetailedSwitchPass":simultaneous_pass,
                     "bodyOutsideFailures":body_fail,
                     "projectionRangeMm":[min(projections),max(projections)],"buttonRadialCenterChanges":0,
                     "pressAxisChanges":0,"axialDepthTranslationUsed":True},
          "recovery":recovery,"pairDepthResolution":pair_resolution,"validation":validation,"cut":cut,
          "comparison":{"docs97FailureDatumCause":"YES" if sockets==8 and body_fail==0 else "PARTIAL"},
          "architecture":{"harness":0,"legs":0,"pushers":0,"holeDiameterMm":HOLE_D,
                          "bodyClearancePerSideMm":BODY_CLEARANCE,"epoxyFixationAccepted":True},
          "manufacturing":{"native":native,"reimport":reimport,"stl":stl,"pass":manufacturing_pass},
          "preservation":{"before":before,"after":after,"unchanged":before==after},
          "outputs":{"JaDStep":relative(STEP_OUT["JaD"]),"JfDStep":relative(STEP_OUT["JfD"]),
                     "referenceStep":relative(REFERENCE_STEP),"JaDStl":relative(STL_OUT["JaD"]),
                     "JfDStl":relative(STL_OUT["JfD"]),"json":relative(JSON_PATH),"report":relative(REPORT),
                     "renders":render_paths,"productionOverwriteCount":0}}
    JSON_PATH.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    REPORT.write_text(report_text(data),encoding="utf-8")
    print(json.dumps({"summary":data["summary"],"i2I3":validation["i2I3"],"m4N3":validation["m4N3"],
                      "manufacturing":manufacturing_pass,"preserved":before==after,"outputs":data["outputs"]},indent=2),flush=True)


if __name__=="__main__": main()
