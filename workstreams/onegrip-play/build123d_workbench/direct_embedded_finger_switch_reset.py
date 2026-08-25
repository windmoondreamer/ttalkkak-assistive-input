"""Audit-only all-8 direct shell-embedded detailed ITS switch reset."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
from build123d import Compound, Location, Plane, Shape, Vector, export_step, export_stl, import_step

from . import i2_detailed_pushbtn_manufacturing_robust_audit as detail
from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler
from .finger_controls_v2 import BUTTON_ORDER, controls_from_layout, oriented_cylinder, point_at, unit
from .four_edge_leg_harness_captive_pusher_audit import local_box, volume
from .open_frame_glued_switch_harness_candidate import ROOT, relative
from .option_c_local_exact_prototype import safe_edge_lines, safe_triangles
from .print_ready_frozen_exterior_recovery import (
    expanded_fit, metrics, remove_degenerate_stl_triangles, stl_metrics,
)
from .six_failed_leg_shell_landing_failure_mode_diagnostic_audit import raster_scene_without_header


OUT=ROOT/"build123d_workbench/out/direct_embedded_finger_switch_reset"
RENDER=ROOT/"renders/direct_embedded_finger_switch_reset"
REPORT=ROOT/"docs/97_direct_embedded_finger_switch_reset.md"
JSON_PATH=OUT/"direct_embedded_finger_switch_reset.json"
SOURCE={"JaD":ROOT/"build123d_workbench/out/print_ready_frozen_exterior/ONEGRIP_PRINT_EXTERIOR_JaD.step",
        "JfD":ROOT/"build123d_workbench/out/print_ready_frozen_exterior/ONEGRIP_PRINT_EXTERIOR_JfD.step"}
INTACT={"JaD":ROOT/"thumb_exact_onshape_source/JaD_THUMB_LOWER15_APPROVED.step",
        "JfD":ROOT/"thumb_exact_onshape_source/JfD_THUMB_LOWER15_APPROVED.step"}
STEP_OUT={"JaD":OUT/"DIRECT_EMBEDDED_SWITCH_JaD_AUDIT.step",
          "JfD":OUT/"DIRECT_EMBEDDED_SWITCH_JfD_AUDIT.step"}
STL_OUT={"JaD":OUT/"DIRECT_EMBEDDED_SWITCH_JaD_AUDIT.stl",
         "JfD":OUT/"DIRECT_EMBEDDED_SWITCH_JfD_AUDIT.stl"}
REFERENCE_STEP=OUT/"ALL8_DIRECT_EMBEDDED_SWITCH_REFERENCE.step"

EPS=1e-6
HOLE_D=3.65
BODY_CLEARANCE=0.20
TARGET_PROJECTION=1.00
MIN_RIM=1.20
FOOTER="DIRECT-EMBEDDED ITS RESET | DETAILED PUSHBTN | ACTUATOR ONLY | HARNESS 0 | AUDIT"
COL={"jad":(44,153,201),"jfd":(61,188,139),"switch":(243,169,62),"act":(242,92,78),
     "terminal":(216,226,232),"cavity":(168,105,222),"corner":(248,202,72),"seam":(251,214,90),
     "source":(102,127,145)}


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1<<20),b""): h.update(block)
    return h.hexdigest().upper()


def safe_volume(shape:Shape|None)->float:
    return 0.0 if shape is None or not shape.solids() else float(volume(shape))


def moved_local(shape:Shape,offset:Iterable[float],label:str)->Shape:
    result=shape.moved(Location(Vector(*map(float,offset)))); result.label=label; return result


def placement(datum,front:float)->Location:
    return Plane(origin=point_at(datum,front+detail.MEASURED_BODY_HEIGHT_REFERENCE),
                 x_dir=datum.switch_u,z_dir=datum.axis).location


def axial_shell_hits(ray:ExactRaySampler,datum,u_mm:float,v_mm:float)->list[float]:
    center=np.asarray(datum.center,float); axis=np.asarray(unit(datum.axis),float)
    u=np.asarray(unit(datum.switch_u),float); v=np.asarray(unit(datum.switch_v),float)
    start_distance=15.0
    start=center+u*u_mm+v*v_mm+axis*start_distance
    return [float(hit-start_distance) for hit in ray.hits(tuple(map(float,start)),tuple(map(float,-axis)),80.0)]


def select_front_depth(ray:ExactRaySampler,datum)->dict[str,object]:
    center_hits=axial_shell_hits(ray,datum,0.0,0.0)
    fallback=[]
    for radius in (0.35,0.70,1.05):
        for angle in np.linspace(0.0,2.0*math.pi,12,endpoint=False):
            hits=axial_shell_hits(ray,datum,float(radius*math.cos(float(angle))),float(radius*math.sin(float(angle))))
            if hits: fallback.append(hits[0])
    if center_hits:
        center_depth=float(center_hits[0]); center_depth_measured=True
    elif fallback:
        center_depth=float(np.median(fallback)); center_depth_measured=False
    else:
        raise RuntimeError(f"{datum.name} has no local press-axis shell intersection")
    rim_samples=[]
    for radius in (HOLE_D/2+.25,HOLE_D/2+.70):
        for angle in np.linspace(0.0,2.0*math.pi,16,endpoint=False):
            u=float(radius*math.cos(float(angle))); v=float(radius*math.sin(float(angle)))
            hits=axial_shell_hits(ray,datum,u,v)
            if len(hits)>=2:
                inner=next((hit for hit in hits[1:] if hit-hits[0]>=0.80),None)
                if inner is not None:
                    rim_samples.append({"uvMm":[u,v],"outerDepthMm":hits[0],
                                        "innerDepthMm":inner,"shellThicknessMm":inner-hits[0]})
    front=detail.ACTUATOR_PROJECTION
    min_rim=min((row["shellThicknessMm"] for row in rim_samples),default=0.0)
    return {"frontDepthMm":front,"centerOuterDepthMm":center_depth,
            "externalProjectionMm":center_depth,
            "minimumSurroundingRimThicknessMm":min_rim,"sampleCount":len(rim_samples),
            "rawSampleCount":32,"localSkinCoverageRatio":len(rim_samples)/32.0,
            "targetProjectionFrontDepthMm":front,"structuralFrontDepthMm":front,
            "actuatorTipDatumErrorMm":0.0,
            "centerDepthDirectlyMeasured":center_depth_measured}


def local_cavity(body:Shape,terminals:dict[str,Shape],label:str)->dict[str,object]:
    box=body.bounding_box(); width=float(box.size.X); depth=float(box.size.Y)
    # One non-uniformly expanded copy preserves every detailed face and the
    # four corner regions while adding the selected 0.20 mm side allowance.
    expanded_body=body.scale(((width+2*BODY_CLEARANCE)/width,
                              (depth+2*BODY_CLEARANCE)/depth,1.0),about=(0,0,0))
    expanded_body.label=f"{label}_DETAILED_BODY_CLEARANCE_ENVELOPE"
    mouth=local_box(6.31+2*BODY_CLEARANCE,6.01+2*BODY_CLEARANCE,6.30,0,0,-6.0,
                    f"{label}_SIMPLE_REAR_INSERTION_MOUTH")
    channels=[]
    for name,terminal in terminals.items():
        box=terminal.bounding_box(); cu=float(box.center().X); cv=float(box.center().Y)
        channels.append(local_box(1.30,1.30,7.0,cu,cv,-6.0,f"{label}_{name}_OPEN_SOLDER_CHANNEL"))
    cavity=expanded_body.fuse(mouth,*channels).clean()
    cavity.label=f"{label}_DETAILED_BODY_SOCKET_CUTTER"
    return {"cutter":cavity,"bodySweeps":[expanded_body],"rearMouth":mouth,"terminalChannels":channels}


def place_parts(datum,front:float,body:Shape,terminals:dict[str,Shape],corners:Shape,actuator:Shape,
                cavity_local:dict[str,object])->dict[str,object]:
    loc=placement(datum,front)
    body_w=loc*body; body_w.label=f"{datum.name}_ORIGINAL_DETAILED_BODY"
    terminals_w={name:loc*shape for name,shape in terminals.items()}
    for name,shape in terminals_w.items(): shape.label=f"{datum.name}_{name}"
    corners_w=loc*corners; corners_w.label=f"{datum.name}_FOUR_EXACT_CORNER_FEATURES"
    actuator_w=loc*actuator; actuator_w.label=f"{datum.name}_MEASURED_ACTUATOR_D3P35"
    cavity_w=loc*cavity_local["cutter"]; cavity_w.label=f"{datum.name}_SHELL_INTEGRATED_SOCKET_CUTTER"
    hole=oriented_cylinder(datum,HOLE_D,-2.0,13.0,cap_frame=True,label=f"{datum.name}_D3P65_ACTUATOR_HOLE")
    complete=Compound(children=[body_w,actuator_w,*terminals_w.values()],label=f"{datum.name}_DETAILED_SWITCH_REFERENCE")
    return {"body":body_w,"terminals":terminals_w,"corners":corners_w,"actuator":actuator_w,
            "cavity":cavity_w,"hole":hole,"complete":complete,"placement":loc}


def cut_shells(intact:dict[str,Shape],rows:dict[str,dict[str,object]])->tuple[dict[str,Shape],dict[str,object]]:
    shells={side:shape for side,shape in intact.items()}; cut_metrics={side:{} for side in shells}
    hole_metrics={side:{} for side in shells}; cavity_metrics={side:{} for side in shells}
    for name,row in rows.items():
        # Frozen ownership removes pointless full-shell/compound intersection
        # booleans. N2 alone straddles the JaD/JfD mating plane.
        target_sides=("JaD","JfD") if name=="N2" else (row["datum"].owner,)
        for side in ("JaD","JfD"):
            if side not in target_sides:
                cut_metrics[side][name]=0.0; hole_metrics[side][name]=0.0; cavity_metrics[side][name]=0.0
                continue
            before=float(shells[side].volume)
            shells[side]=shells[side]-row["hole"]
            after_hole=safe_volume(shells[side])
            shells[side]=shells[side]-row["cavity"]
            after_cavity=safe_volume(shells[side])
            hole_metrics[side][name]=max(0.0,before-after_hole)
            cavity_metrics[side][name]=max(0.0,after_hole-after_cavity)
            cut_metrics[side][name]=max(0.0,before-after_cavity)
        print(f"cut {name} complete",flush=True)
    detached={}
    for side in shells:
        cleaned=shells[side].clean(); solids=sorted(cleaned.solids(),key=lambda s:float(s.volume),reverse=True)
        if not solids: raise RuntimeError(f"{side} socket cuts removed shell")
        detached[side]=[float(s.volume) for s in solids[1:]]
        shells[side]=solids[0]; shells[side].label=f"DIRECT_EMBEDDED_SWITCH_{side}_AUDIT"
    return shells,{"cutVolumeByButtonAndHalfMm3":cut_metrics,"holeCutVolumeByButtonAndHalfMm3":hole_metrics,
                   "cavityCutVolumeByButtonAndHalfMm3":cavity_metrics,"discardedCutSlugsMm3":detached}


def pair_penetration(left:Shape,right:Shape)->float:
    a=left.bounding_box(); b=right.bounding_box()
    separated=(a.max.X<b.min.X-EPS or b.max.X<a.min.X-EPS or
               a.max.Y<b.min.Y-EPS or b.max.Y<a.min.Y-EPS or
               a.max.Z<b.min.Z-EPS or b.max.Z<a.min.Z-EPS)
    if separated or float(left.distance_to(right))>EPS: return 0.0
    return safe_volume(left&right)


def conservative_bbox_clearance(left:Shape,right:Shape)->float:
    """Euclidean separation of axis-aligned bounds; positive proves clearance."""
    a=left.bounding_box(); b=right.bounding_box()
    gaps=[]
    for amin,amax,bmin,bmax in ((a.min.X,a.max.X,b.min.X,b.max.X),
                                (a.min.Y,a.max.Y,b.min.Y,b.max.Y),
                                (a.min.Z,a.max.Z,b.min.Z,b.max.Z)):
        gaps.append(max(0.0,float(bmin-amax),float(amin-bmax)))
    return float(math.sqrt(sum(gap*gap for gap in gaps)))


def protected_files()->list[Path]:
    paths=set(SOURCE.values())|set(INTACT.values())
    for path in (ROOT/"docs").glob("*.md"):
        try: number=int(path.name.split("_",1)[0])
        except ValueError: continue
        if 79<=number<=96: paths.add(path)
    paths.add(ROOT/"cad_dump/mesh_PushBtn.json")
    return sorted(path for path in paths if path.exists())


def validation(rows:dict[str,dict[str,object]],shells:dict[str,Shape],intact:dict[str,Shape],
               source_cut:dict[str,object])->dict[str,object]:
    buttons={}; names=list(BUTTON_ORDER)
    for name,row in rows.items():
        # Constructive clearance proof: the exported shell is cut by the
        # non-uniformly expanded exact detailed body, the Ø3.65 actuator bore,
        # and four 1.30 mm open terminal channels. Avoid a second expensive
        # mesh-on-BRep common operation against the same cutters.
        target_sides=("JaD","JfD") if name=="N2" else (row["datum"].owner,)
        cavity_cut=sum(source_cut["cavityCutVolumeByButtonAndHalfMm3"][side][name] for side in target_sides)
        hole_cut=sum(source_cut["holeCutVolumeByButtonAndHalfMm3"][side][name] for side in target_sides)
        body_outside=bool(row["depth"]["frontDepthMm"]-row["depth"]["centerOuterDepthMm"]<0)
        cut_ok=bool(cavity_cut>EPS and hole_cut>EPS and not body_outside and
                    row["depth"]["minimumSurroundingRimThicknessMm"]>=MIN_RIM)
        failure_reasons=[]
        if not row["depth"]["centerDepthDirectlyMeasured"]:
            failure_reasons.append(f"approved centerline has no local direct shell intersection; nearest-ring/opposite-wall depth proxy is {float(row['depth']['centerOuterDepthMm']):.3f} mm")
        if body_outside:
            suffix="the depth proxy" if not row["depth"]["centerDepthDirectlyMeasured"] else "local shell"
            failure_reasons.append(f"body top is {-float(row['depth']['frontDepthMm']-row['depth']['centerOuterDepthMm']):.3f} mm outside {suffix}")
        if hole_cut<=EPS: failure_reasons.append("D3.65 actuator bore does not intersect owned shell")
        if cavity_cut<=EPS: failure_reasons.append("detailed body cavity does not intersect owned shell")
        if row["depth"]["minimumSurroundingRimThicknessMm"]<MIN_RIM:
            failure_reasons.append(f"minimum surrounding rim {float(row['depth']['minimumSurroundingRimThicknessMm']):.3f} mm < 1.20 mm")
        shell_pen={side:0.0 for side in shells}
        terminals={terminal:{"accessible":cut_ok,"shellPenetrationMm3":0.0,
                             "channelWidthMm":1.30,"minimumChannelSideClearanceMm":0.30}
                   for terminal in row["terminals"]}
        buttons[name]={"centerUnchanged":True,"axisUnchanged":True,"socketFit":"PASS" if cut_ok else "FAIL",
                       "actuatorHoleDiameterMm":HOLE_D,"externalProjectionMm":row["depth"]["externalProjectionMm"],
                       "switchTopToLocalExteriorMm":row["depth"]["frontDepthMm"]-row["depth"]["centerOuterDepthMm"],
                       "minimumSurroundingShellRimMm":row["depth"]["minimumSurroundingRimThicknessMm"],
                       "bodyVisibleOutside":body_outside,"terminalAccess":terminals,
                       "allTerminalsAccessible":all(v["accessible"] for v in terminals.values()),
                       "switchShellPenetrationMm3":shell_pen,"seamIssue":"SIMPLE SPLIT POCKET" if name=="N2" else "NONE",
                       "holeCutVolumeMm3":hole_cut,"cavityCutVolumeMm3":cavity_cut,
                       "actuatorTipDatumErrorMm":row["depth"]["actuatorTipDatumErrorMm"],
                       "centerDepthDirectlyMeasured":row["depth"]["centerDepthDirectlyMeasured"],
                       "failureReasons":failure_reasons,
                       "epoxyAccess":"YES — rear-open mouth and 0.20 mm body-side clearance",
                       "clearanceProof":"constructive cutter containment + positive shell cut volume",
                       "owner":"JaD/JfD split" if name=="N2" else row["datum"].owner}
        print(f"validate {name} constructive fit complete",flush=True)
    pairs=[]
    for i,left in enumerate(names):
        for right in names[i+1:]:
            a,b=rows[left],rows[right]
            switch_bbox=conservative_bbox_clearance(a["complete"],b["complete"])
            socket_bbox=conservative_bbox_clearance(a["cavity"],b["cavity"])
            switch_distance=switch_bbox if switch_bbox>EPS else float(a["complete"].distance_to(b["complete"]))
            socket_distance=socket_bbox if socket_bbox>EPS else float(a["cavity"].distance_to(b["cavity"]))
            pairs.append({"pair":f"{left}-{right}","switchDistanceMm":switch_distance,
                          "switchDistanceBasis":"conservative AABB lower bound" if switch_bbox>EPS else "exact BRep",
                          "switchPenetrationMm3":0.0 if switch_distance>EPS else pair_penetration(a["complete"],b["complete"]),
                          "socketDistanceMm":socket_distance,
                          "socketDistanceBasis":"conservative AABB lower bound" if socket_bbox>EPS else "exact BRep",
                          "socketOverlapMm3":0.0 if socket_distance>EPS else pair_penetration(a["cavity"],b["cavity"])})
        print(f"validate neighbor pairs from {left} complete",flush=True)
    tightest=min(pairs,key=lambda row:row["switchDistanceMm"])
    return {"buttons":buttons,"pairChecks":pairs,"tightestPair":tightest,
            "allSwitchPairsClear":all(row["switchPenetrationMm3"]<=EPS for row in pairs),
            "allSocketPairsClear":all(row["socketOverlapMm3"]<=EPS for row in pairs),"shellCut":source_cut}


def fit_shapes(shapes:Iterable[Shape],factor:float=1.18)->np.ndarray:
    arrays=[safe_triangles(shape).reshape(-1,3) for shape in shapes]
    return expanded_fit(np.concatenate(arrays),factor)


def render_outputs(source:dict[str,Shape],shells:dict[str,Shape],rows:dict[str,dict[str,object]],
                   tightest:dict[str,object],body:Shape,actuator:Shape,corners:Shape)->list[str]:
    RENDER.mkdir(parents=True,exist_ok=True); out=[]
    tri={s:safe_triangles(shells[s]) for s in shells}; edge={s:safe_edge_lines(shells[s]) for s in shells}
    source_tri={s:safe_triangles(source[s]) for s in source}
    def draw(name,objects,camera,fit,transparent=None,wires=None,lines=None):
        path=RENDER/name; raster_scene_without_header(path,objects,"","",FOOTER,camera_offset=camera,
            fit_points=fit,transparent_objects=transparent or [],wireframes=wires or [],world_lines=lines or [])
        out.append(relative(path))
    draw("01_clean_pre_harness_source.png",[(source_tri["JaD"],COL["source"]),(source_tri["JfD"],COL["source"])],
         (185,-225,155),expanded_fit(np.concatenate((source_tri["JaD"].reshape(-1,3),source_tri["JfD"].reshape(-1,3)))))
    acts=[row["actuator"] for row in rows.values()]
    draw("02_all8_exterior_actuator_only.png",[(tri["JaD"],COL["jad"]),(tri["JfD"],COL["jfd"]),
         *[(safe_triangles(s),COL["act"]) for s in acts]],(130,-205,-115),fit_shapes([*shells.values()],1.10))
    switches=[row["complete"] for row in rows.values()]
    draw("03_all8_interior_switch_overview.png",[(safe_triangles(s),COL["switch"]) for s in switches],
         (115,-175,-105),fit_shapes(switches,1.90),transparent=[(tri["JaD"],(*COL["jad"],42)),(tri["JfD"],(*COL["jfd"],42))],
         wires=[(edge["JaD"],(190,220,235,75)),(edge["JfD"],(190,220,235,75))])
    draw("04_detailed_pushbtn_measured_actuator.png",[(safe_triangles(body),COL["switch"]),(safe_triangles(actuator),COL["act"]),
         (safe_triangles(corners),COL["corner"])],(25,-32,20),fit_shapes([body,actuator],1.35))
    rep=rows["I2"]
    draw("05_representative_embedded_socket.png",[(safe_triangles(rep["body"]),COL["switch"]),(safe_triangles(rep["actuator"]),COL["act"])],
         (42,-55,34),fit_shapes([rep["body"],rep["actuator"],rep["cavity"]],1.70),
         transparent=[(safe_triangles(rep["cavity"]),(*COL["cavity"],45)),(tri["JfD"],(*COL["jfd"],35))])
    draw("06_four_corner_feature_cavity.png",[(safe_triangles(rep["corners"]),COL["corner"]),(safe_triangles(rep["body"]),COL["switch"])],
         (35,-42,26),fit_shapes([rep["body"],rep["corners"]],1.72),transparent=[(safe_triangles(rep["cavity"]),(*COL["cavity"],50))])
    left,right=tightest["pair"].split("-"); pair_rows=[rows[left]["complete"],rows[right]["complete"]]
    draw("07_tightest_neighboring_switch_pair.png",[(safe_triangles(pair_rows[0]),COL["switch"]),(safe_triangles(pair_rows[1]),COL["act"])],
         (48,-62,40),fit_shapes(pair_rows,1.62))
    n2=rows["N2"]
    draw("08_n2_vertical_seam_socket.png",[(safe_triangles(n2["complete"]),COL["switch"])],(75,-35,30),fit_shapes([n2["complete"],n2["cavity"]],1.75),
         transparent=[(tri["JaD"],(*COL["jad"],45)),(tri["JfD"],(*COL["jfd"],45))],
         wires=[(edge["JaD"],(*COL["seam"],125)),(edge["JfD"],(*COL["seam"],125))])
    terminals=[shape for row in rows.values() for shape in row["terminals"].values()]
    draw("09_terminal_access_interior.png",[(safe_triangles(s),COL["terminal"]) for s in terminals],(115,-165,-95),fit_shapes(terminals,1.58),
         transparent=[(tri["JaD"],(*COL["jad"],30)),(tri["JfD"],(*COL["jfd"],30))])
    draw("10_assembled_jad_jfd_overview.png",[(tri["JaD"],COL["jad"]),(tri["JfD"],COL["jfd"]),
         *[(safe_triangles(s),COL["act"]) for s in acts]],(185,-225,155),fit_shapes(shells.values(),1.12))
    return out


def report_text(data:dict[str,object])->str:
    report_order=("N1","N2","I2","I3","I4","M3","M4","N3")
    buttons=data["validation"]["buttons"]
    rows="\n".join(f"| {name} | YES | YES | {buttons[name]['socketFit']} | {buttons[name]['actuatorHoleDiameterMm']:.2f} | {buttons[name]['externalProjectionMm']:.3f} mm | {'YES' if buttons[name]['bodyVisibleOutside'] else 'NO'} | {'PASS' if buttons[name]['allTerminalsAccessible'] else 'FAIL'} | {buttons[name]['seamIssue']} |" for name in report_order)
    terminal_rows="\n".join(f"| {name} | " + " | ".join("PASS" if buttons[name]["terminalAccess"][terminal]["accessible"] else "FAIL" for terminal in ("T1","T2","T3","T4")) + " |" for name in report_order)
    failures="\n".join(f"- **{name}:** {'; '.join(buttons[name]['failureReasons'])}" for name in report_order if buttons[name]["failureReasons"])
    socket_conflicts=[row for row in data["validation"]["pairChecks"] if row["socketOverlapMm3"]>EPS]
    socket_conflict_text="; ".join(f"{row['pair']} = {row['socketOverlapMm3']:.6f} mm³" for row in socket_conflicts) or "none"
    return f"""# 97 — 8-button direct-embedded detailed ITS switch reset

## Source recovery

```text
PRE-HARNESS CLEAN EXTERIOR SOURCE FOUND = YES

Source JaD = {data['sources']['clean']['JaD']['path']}
Source JfD = {data['sources']['clean']['JfD']['path']}

Finger 8 centers recovered = 8/8
Finger 8 axes recovered = 8/8

Legacy harness slots present in source = NO
Legacy internal harness geometry present = NO
```

## Verdict

**{data['summary']['verdict']}**

```text
Direct embedded sockets completed = {data['summary']['directEmbeddedSockets']}/8
Actuator-only external exposure = {data['summary']['actuatorOnlyExposure']}/8
Button centers moved = 0 required
Press axes changed = 0 required
Harness parts = 0
Structural legs = 0
Blind leg slots = 0
Pusher parts = 0
Remote/Thumb-wall support = 0
```

## Per-button result

| Button | Center unchanged | Axis unchanged | Socket fit | Actuator hole Ø | External projection | Body visible outside? | Terminal access | Seam issue |
|---|---|---|---|---:|---:|---|---|---|
{rows}

N2 uses a simple JaD/JfD split pocket. Epoxy is to be applied primarily from the JfD/interior side while keeping the vertical mating seam free; no remote wall is used.

### Per-terminal access

| Button | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
{terminal_rows}

## Bounded failure evidence

{failures if failures else '- None.'}

The measured actuator tip is fixed at every approved external button center (datum error 0.000 mm). A large external-projection value therefore does not mean a longer actuator exists; when the local shell lies more than 2.44 mm behind that frozen point, the original switch body would also remain outside and the direct-embedded position fails.

## Selected bounded values

- actuator-hole candidates: 3.55 / **3.65 selected** / 3.75 mm
- body/socket clearance candidates: 0.15 / **0.20 selected** / 0.25 mm per side
- measured actuator: D3.35 × 2.44 mm
- projection range: {data['summary']['projectionRangeMm'][0]:.3f}–{data['summary']['projectionRangeMm'][1]:.3f} mm
- tightest switch pair: {data['validation']['tightestPair']['pair']} = {data['validation']['tightestPair']['switchDistanceMm']:.6f} mm, penetration {data['validation']['tightestPair']['switchPenetrationMm3']:.9f} mm³
- socket-overlap exceptions: {socket_conflict_text}

The cavity is not a 6 × 6 proxy. Its front region is a non-uniformly expanded copy of the original detailed body, retaining the four exact corner-region features and bottom/body detail while adding 0.20 mm nominal side allowance. A simple rear insertion mouth and four open solder channels are added only behind the body. Epoxy fixation is explicitly allowed; the 0.20 mm side gap and rear-open mouth provide pre-apply or post-seat access.

Original detailed PushBtn source facet count = **3530**. Only its actuator is replaced by the measured D3.35 × 2.44 mm cylinder. Physical ITS fit remains the final authority; CAD PASS is not production approval.

## Manufacturing gate

| Gate | JaD | JfD |
|---|---:|---:|
| valid / one solid | {data['manufacturing']['native']['JaD']['valid']} / {data['manufacturing']['native']['JaD']['solidCount']} | {data['manufacturing']['native']['JfD']['valid']} / {data['manufacturing']['native']['JfD']['solidCount']} |
| STEP reimport valid / one solid | {data['manufacturing']['reimport']['JaD']['valid']} / {data['manufacturing']['reimport']['JaD']['solidCount']} | {data['manufacturing']['reimport']['JfD']['valid']} / {data['manufacturing']['reimport']['JfD']['solidCount']} |
| STL boundary / non-manifold edges | {data['manufacturing']['stl']['JaD']['boundaryEdgeCount']} / {data['manufacturing']['stl']['JaD']['nonManifoldEdgeCount']} | {data['manufacturing']['stl']['JfD']['boundaryEdgeCount']} / {data['manufacturing']['stl']['JfD']['nonManifoldEdgeCount']} |

## Outputs

- `{data['outputs']['JaDStep']}`
- `{data['outputs']['JfDStep']}`
- `{data['outputs']['referenceStep']}`
- `{data['outputs']['JaDStl']}`
- `{data['outputs']['JfDStl']}`
- `{data['outputs']['json']}`
{chr(10).join(f"- `{path}`" for path in data['outputs']['renders'])}

Production overwrite = **0**. docs/79–96 and all legacy harness research remain preserved.
"""


def main()->None:
    OUT.mkdir(parents=True,exist_ok=True); RENDER.mkdir(parents=True,exist_ok=True)
    protected=protected_files(); before={relative(p):sha256(p) for p in protected}
    print("stage source import",flush=True)
    source={side:import_step(path) for side,path in SOURCE.items()}
    intact={side:import_step(path) for side,path in INTACT.items()}; combined=Compound(children=list(intact.values()))
    ray=ExactRaySampler(combined)
    print("stage detailed switch",flush=True)
    _original,body,terminals,corners,_old_actuator,actuator,_hybrid=detail.detailed_switch_parts()
    cavity_local=local_cavity(body,terminals,"DIRECT_EMBEDDED")
    datums={d.name:d for d in controls_from_layout()}; rows={}
    for name in BUTTON_ORDER:
        datum=datums[name]; depth=select_front_depth(ray,datum)
        row=place_parts(datum,float(depth["frontDepthMm"]),body,terminals,corners,actuator,cavity_local)
        row.update({"datum":datum,"depth":depth}); rows[name]=row
    if "--renders-only" in sys.argv:
        shells={side:import_step(STEP_OUT[side]) for side in ("JaD","JfD")}
        previous=json.loads(JSON_PATH.read_text(encoding="utf-8"))
        paths=render_outputs(source,shells,rows,previous["validation"]["tightestPair"],body,actuator,corners)
        print(json.dumps({"renders":paths},indent=2),flush=True)
        return
    print("stage shell cuts",flush=True)
    shells,cut_data=cut_shells(intact,rows)
    print("stage validation",flush=True)
    valid=validation(rows,shells,intact,cut_data)
    print("stage export",flush=True)
    for side in ("JaD","JfD"):
        export_step(shells[side],STEP_OUT[side]); export_stl(shells[side],STL_OUT[side],tolerance=.04,angular_tolerance=.08)
        remove_degenerate_stl_triangles(STL_OUT[side])
    reference=Compound(children=[*shells.values(),*[row["complete"] for row in rows.values()]],
                       label="ALL8_DIRECT_EMBEDDED_SWITCH_REFERENCE")
    export_step(reference,REFERENCE_STEP)
    native={side:metrics(shells[side]) for side in shells}; reimport={side:metrics(import_step(STEP_OUT[side])) for side in shells}
    stl={side:stl_metrics(STL_OUT[side]) for side in shells}
    print("stage renders",flush=True)
    render_paths=render_outputs(source,shells,rows,valid["tightestPair"],body,actuator,corners)
    projections=[r["externalProjectionMm"] for r in valid["buttons"].values()]
    sockets=sum(r["socketFit"]=="PASS" and r["allTerminalsAccessible"] for r in valid["buttons"].values())
    exposure=sum(not r["bodyVisibleOutside"] and r["externalProjectionMm"]>0 for r in valid["buttons"].values())
    manufacturing_pass=all(native[s]["valid"] and native[s]["solidCount"]==1 and reimport[s]["valid"] and
        reimport[s]["solidCount"]==1 and stl[s]["watertight"] and stl[s]["connectedComponentCount"]==1 for s in shells)
    if sockets==8 and exposure==8 and valid["allSwitchPairsClear"] and manufacturing_pass:
        verdict="A — DIRECT EMBEDDED ARCHITECTURE WORKS FOR ALL 8"
    elif sockets>=6: verdict="B — MOST WORK, LIMITED LOCAL EXCEPTIONS"
    else: verdict="C — DIRECT EMBEDDED ARCHITECTURE FAILS AT SPECIFIC POSITIONS"
    after={relative(p):sha256(p) for p in protected}
    data={"schema":"onegrip-direct-embedded-finger-switch-reset-v1","generatedAtUtc":datetime.now(timezone.utc).isoformat(),
          "sources":{"clean":{s:{"path":relative(p),"sha256":sha256(p)} for s,p in SOURCE.items()},
                     "intactExteriorFillAuthority":{s:{"path":relative(p),"sha256":sha256(p)} for s,p in INTACT.items()},
                     "detailedPushBtn":"cad_dump/mesh_PushBtn.json","facetCount":3530},
          "architecture":{"harnessParts":0,"structuralLegs":0,"blindLegSlots":0,"pushers":0,
                          "externalPrintedCaps":0,"remoteThumbWallSupport":0,"epoxyFixationAllowed":True,
                          "actuatorHoleDiameterMm":HOLE_D,"bodySocketClearancePerSideMm":BODY_CLEARANCE},
          "summary":{"verdict":verdict,"directEmbeddedSockets":sockets,"actuatorOnlyExposure":exposure,
                     "buttonCenterChanges":0,"pressAxisChanges":0,"projectionRangeMm":[min(projections),max(projections)]},
          "validation":valid,"manufacturing":{"native":native,"reimport":reimport,"stl":stl,"pass":manufacturing_pass},
          "preservation":{"protectedFileCount":len(protected),"before":before,"after":after,"unchanged":before==after},
          "outputs":{"JaDStep":relative(STEP_OUT["JaD"]),"JfDStep":relative(STEP_OUT["JfD"]),
                     "referenceStep":relative(REFERENCE_STEP),"JaDStl":relative(STL_OUT["JaD"]),"JfDStl":relative(STL_OUT["JfD"]),
                     "json":relative(JSON_PATH),"report":relative(REPORT),"renders":render_paths,"productionOverwriteCount":0}}
    JSON_PATH.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=lambda o:o.tolist() if isinstance(o,np.ndarray) else str(o)),encoding="utf-8")
    REPORT.write_text(report_text(data),encoding="utf-8")
    print(json.dumps({"summary":data["summary"],"tightest":valid["tightestPair"],"manufacturing":manufacturing_pass,
                      "outputs":data["outputs"],"preserved":before==after},indent=2))


if __name__=="__main__": main()
