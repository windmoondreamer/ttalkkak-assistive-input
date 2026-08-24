"""Frozen-geometry assembly-sequence-only audit continuing docs/84."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Location, Shape, Vector, import_step

from . import i2_detailed_pushbtn_manufacturing_robust_audit as doc84
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, unit
from .four_edge_leg_harness_captive_pusher_audit import volume
from .i4_m3_current_audit import load_all_datums
from .slot_anchored_harness_captive_pusher_audit import pusher_system


ROOT = Path(__file__).resolve().parents[1]
DOC84_OUT = ROOT / "build123d_workbench/out/i2_detailed_pushbtn_manufacturing_robust_audit"
HARNESS_STEP = DOC84_OUT / "I2_DETAILED_PUSHBTN_ROBUST_FOUR_EDGE_HARNESS_AUDIT_ONLY.step"
SHELL_STEP = DOC84_OUT / "I2_ROBUST_FOUR_DIRECT_SLOT_SHELL_CROP_AUDIT_ONLY.step"
EPS = 1.0e-6
OUT = ROOT / "build123d_workbench/out/i2_assembly_sequence_only_audit"
RENDER = ROOT / "renders/i2_assembly_sequence_only_audit"
REPORT = ROOT / "docs/85_i2_assembly_sequence_only_audit.md"
JSON_PATH = OUT / "i2_assembly_sequence_only_audit.json"
DOC84_JSON = DOC84_OUT / "i2_detailed_pushbtn_manufacturing_robust_audit.json"
SEQUENCE_A_VECTOR = np.asarray((0.3415514166060052, -0.017899951255297575, 0.9396926207859084), float)
FOOTER = "ASSEMBLY SEQUENCE ONLY | DOCS/84 GEOMETRY FROZEN | ORIGINAL DETAILED PUSHBTN | PRODUCTION 0"
COL = {
    "shell": (104, 127, 149), "harness": (64, 194, 143), "body": (63, 163, 222),
    "terminal": (217, 225, 234), "actuator": (238, 91, 101), "pusher": (237, 132, 72),
    "guide": (70, 169, 227), "collision": (238, 69, 86), "axis": (250, 213, 78),
}


def moved(shape: Shape, offset: Iterable[float], label: str) -> Shape:
    x, y, z = map(float, offset)
    result = shape.moved(Location(Vector(x, y, z)))
    result.label = label
    return result


def pair(left: Shape, right: Shape) -> tuple[float, float]:
    distance = float(left.distance_to(right))
    penetration = volume(left & right) if distance <= 1.0e-7 else 0.0
    return distance, penetration


def aabb_overlaps(left: Shape, right: Shape, tolerance: float = 1.0e-8) -> bool:
    a = left.bounding_box(); b = right.bounding_box()
    return not (float(a.max.X) < float(b.min.X)-tolerance or float(b.max.X) < float(a.min.X)-tolerance or
                float(a.max.Y) < float(b.min.Y)-tolerance or float(b.max.Y) < float(a.min.Y)-tolerance or
                float(a.max.Z) < float(b.min.Z)-tolerance or float(b.max.Z) < float(a.min.Z)-tolerance)


def translation_probe(name: str, moving: dict[str, Shape], fixed: dict[str, Shape],
                      start_offset: Iterable[float], states: int = 33,
                      compute_swept: bool = False) -> dict[str, object]:
    start = np.asarray(start_offset, float)
    print(f"probe_start={name}", flush=True)
    rows = []
    worst = {"penetrationMm3": 0.0, "moving": None, "fixed": None, "stateIndex": None}
    collisions = []
    for index, fraction in enumerate(np.linspace(1.0, 0.0, states)):
        if index % 8 == 0 or index == states-1:
            print(f"probe_state={name}:{index}/{states-1}", flush=True)
        offset = start * float(fraction)
        total = 0.0
        for moving_name, base in moving.items():
            probe = moved(base, offset, f"{name}_{moving_name}_{index:02d}")
            for fixed_name, target in fixed.items():
                if not aabb_overlaps(probe, target):
                    continue
                distance, penetration = pair(probe, target)
                total += penetration
                if penetration > float(worst["penetrationMm3"]):
                    worst = {"penetrationMm3": penetration, "moving": moving_name,
                             "fixed": fixed_name, "stateIndex": index,
                             "distanceMm": distance, "offsetMm": offset.tolist()}
                if compute_swept and penetration > EPS:
                    common = probe & target
                    if common is not None and common.solids():
                        collisions.append(common)
        rows.append({"stateIndex": index, "fractionRemaining": float(fraction),
                     "offsetMm": offset.tolist(), "penetrationMm3": total,
                     "collisionFree": total <= EPS})
    swept = 0.0
    if compute_swept and collisions:
        union = collisions[0]
        for common in collisions[1:]:
            union = union.fuse(common)
        swept = volume(union.clean())
    return {"name": name, "stateCount": states, "startOffsetMm": start.tolist(),
            "travelMm": float(np.linalg.norm(start)), "states": rows,
            "maximumPenetrationMm3": max(float(row["penetrationMm3"]) for row in rows),
            "sweptCollisionVolumeMm3": swept if compute_swept else None, "worstCollision": worst,
            "pass": all(bool(row["collisionFree"]) for row in rows)}


def exact_translation_audit(name: str, moving: dict[str, Shape], fixed: dict[str, Shape],
                            start_offset: Iterable[float], states: int = 33,
                            compute_swept: bool = True) -> dict[str, object]:
    """Exact component-pair penetration at discrete rigid translation states."""
    start = np.asarray(start_offset, float)
    state_rows = []; collisions = []
    maximum_by_fixed = {fixed_name: 0.0 for fixed_name in fixed}
    worst = {"penetrationMm3": 0.0, "moving": None, "fixed": None, "stateIndex": None}
    for index, fraction in enumerate(np.linspace(1.0, 0.0, states)):
        if index % 8 == 0 or index == states-1:
            print(f"audit_state={name}:{index}/{states-1}", flush=True)
        offset = start * float(fraction); by_fixed = {fixed_name: 0.0 for fixed_name in fixed}
        pair_rows = {}; total = 0.0
        for moving_name, base in moving.items():
            probe = moved(base, offset, f"{name}_{moving_name}_{index:02d}")
            for fixed_name, target in fixed.items():
                key = f"{moving_name}:{fixed_name}"
                if not aabb_overlaps(probe, target):
                    pair_rows[key] = 0.0
                    continue
                common = probe & target
                penetration = volume(common)
                pair_rows[key] = penetration
                by_fixed[fixed_name] += penetration; total += penetration
                if penetration > float(worst["penetrationMm3"]):
                    worst = {"penetrationMm3": penetration, "moving": moving_name,
                             "fixed": fixed_name, "pair": key, "stateIndex": index,
                             "offsetMm": offset.tolist()}
                if compute_swept and penetration > EPS and common is not None and common.solids():
                    collisions.append(common)
        for fixed_name, penetration in by_fixed.items():
            maximum_by_fixed[fixed_name] = max(maximum_by_fixed[fixed_name], penetration)
        state_rows.append({"stateIndex": index, "fractionRemaining": float(fraction),
                           "offsetMm": offset.tolist(), "penetrationByFixedMm3": by_fixed,
                           "pairPenetrationMm3": pair_rows, "totalPenetrationMm3": total,
                           "collisionFree": total <= EPS})
    swept = 0.0
    if compute_swept and collisions:
        print(f"audit_swept_fuse={name}:{len(collisions)}", flush=True)
        union = collisions[0]
        for common in collisions[1:]:
            union = union.fuse(common)
        swept = volume(union.clean())
    return {"name": name, "stateCount": states, "startOffsetMm": start.tolist(),
            "travelMm": float(np.linalg.norm(start)), "states": state_rows,
            "maximumPenetrationByFixedMm3": maximum_by_fixed,
            "maximumUnintendedPenetrationMm3": max(float(row["totalPenetrationMm3"]) for row in state_rows),
            "sweptCollisionVolumeMm3": swept, "worstCollision": worst,
            "allStatesCollisionFree": all(bool(row["collisionFree"]) for row in state_rows),
            "elasticDeformationAssumed": False}


def protected_files() -> list[Path]:
    rows = set(doc84.protected_files())
    rows.update({ROOT / "docs/84_i2_detailed_pushbtn_manufacturing_robust_audit.md",
                 ROOT / "build123d_workbench/i2_detailed_pushbtn_manufacturing_robust_audit.py",
                 ROOT / "cad_dump/mesh_PushBtn.json"})
    rows.update(path for path in DOC84_OUT.rglob("*") if path.is_file())
    prior_render = ROOT / "renders/i2_detailed_pushbtn_manufacturing_robust_audit"
    rows.update(path for path in prior_render.rglob("*") if path.is_file())
    return sorted(path for path in rows if path.exists())


def render_outputs(harness: Shape, shell: Shape, mechanism: dict[str, Shape],
                   switch: dict[str, Shape], sequence_a: dict[str, object],
                   sequence_b: dict[str, object]) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    paths = []
    shell_tri = doc84.safe_triangles(shell); shell_wire = doc84.safe_edge_lines(shell)

    def render(filename: str, objects, title: str, subtitle: str, camera=(28,-39,23),
               transparent=None, wireframes=None, world_lines=None, fit_points=None):
        path = RENDER / filename
        doc84.raster_scene(path, objects, title, subtitle, FOOTER, camera_offset=camera,
                           transparent_objects=transparent or [], wireframes=wireframes or [],
                           world_lines=world_lines or [], fit_points=fit_points)
        paths.append(doc84.relative(path))

    pusher_objects = [(doc84.safe_triangles(mechanism["PUSHER"]), COL["pusher"]),
                      (doc84.safe_triangles(mechanism["GUIDE"]), COL["guide"])]
    for number, fraction, label in ((1,1.0,"START"),(2,0.5,"PARTIAL"),(3,0.0,"FULL SEAT")):
        offset = -SEQUENCE_A_VECTOR * 1.60 * fraction
        moving_harness = moved(harness, offset, f"A_{label}")
        render(f"{number:02d}_sequence_a_i2_harness_{label.lower().replace(' ','_')}.png",
               [(doc84.safe_triangles(moving_harness),COL["harness"]),*pusher_objects],
               f"{number} / SEQUENCE A — {label}",
               f"I3 absent | I2 switch absent | rigid remaining travel={1.60*fraction:.3f} mm",
               transparent=[(shell_tri,(*COL["shell"],52))], wireframes=[(shell_wire,(*COL["shell"],135))],
               world_lines=[(-SEQUENCE_A_VECTOR*1.60,np.zeros(3),(*COL["axis"],255),"I2 HARNESS INSERTION")])

    def switch_objects(offset: np.ndarray):
        rows=[]
        for part, shape in switch.items():
            color = COL["body"] if part == "BODY" else COL["actuator"] if part == "ACTUATOR" else COL["terminal"]
            rows.append((doc84.safe_triangles(moved(shape,offset,f"B_{part}")),color))
        return rows

    start_offset=np.asarray((-12.0,0.0,0.0))
    start_objects=switch_objects(start_offset)
    start_fit=np.concatenate([tri.reshape(-1,3) for tri,_ in start_objects] +
                             [doc84.safe_triangles(harness).reshape(-1,3)])
    render("04_sequence_b_detailed_i2_pushbtn_start.png",
           [*start_objects,(doc84.safe_triangles(harness),COL["harness"]),*pusher_objects],
           "4 / DETAILED I2 SWITCH START",
           "documented open-side preload | local −U | 12.000 mm remaining",
           transparent=[(shell_tri,(*COL["shell"],38))], wireframes=[(shell_wire,(*COL["shell"],105))],
           world_lines=[(start_offset,np.zeros(3),(*COL["axis"],255),"DOCUMENTED −U PRELOAD")], fit_points=start_fit)
    final_objects=switch_objects(np.zeros(3))
    render("05_sequence_b_detailed_i2_pushbtn_full_seat.png",
           [*final_objects,(doc84.safe_triangles(harness),COL["harness"]),*pusher_objects],
           "5 / SEQUENCE B — STATIC FULL SEAT",
           "static penetration=0 per docs/84 | this position is not reachable by the tested rigid path",
           transparent=[(shell_tri,(*COL["shell"],45))], wireframes=[(shell_wire,(*COL["shell"],115))])

    worst=sequence_b["worstCollision"]; collision_offset=np.asarray(worst["offsetMm"],float)
    moving_body=moved(switch["BODY"],collision_offset,"B_LIMITING_BODY")
    collision=(moving_body & harness).clean(); collision_tri=doc84.safe_triangles(collision)
    body_tri=doc84.safe_triangles(moving_body); harness_tri=doc84.safe_triangles(harness)
    render("06_sequence_b_limiting_body_harness_collision.png",
           [(body_tri,COL["body"]),(collision_tri,COL["collision"])],
           "6 / LIMITING BODY–HARNESS COLLISION",
           f"state {worst['stateIndex']} | offset U={collision_offset[0]:.3f} mm | pair penetration={worst['penetrationMm3']:.6f} mm3",
           camera=(17,-24,8), transparent=[(harness_tri,(*COL["harness"],48))],
           fit_points=np.concatenate((body_tri.reshape(-1,3),collision_tri.reshape(-1,3))))
    return paths


def report_text(data: dict[str, object]) -> str:
    a=data["sequences"]["A"]; b=data["sequences"]["B"]; c=data["sequences"]["C"]
    renders="\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    return f"""# 85 — I2 assembly-sequence-only audit

| Sequence | Result | Limiting collision | Swept collision |
|---|---|---|---:|
| A. I2 harness first | **PASS** | none | {a['sweptCollisionVolumeMm3']:.9f} mm³ |
| B. I2 detailed PushBtn second | **FAIL** | BODY ↔ HARNESS, {b['worstCollision']['penetrationMm3']:.9f} mm³ | {b['sweptCollisionVolumeMm3']:.9f} mm³ |
| C. I3 installed afterward | **FAIL (prerequisite)** | B prevents a legitimately completed I2 state | N/A |

Can assembly order alone solve docs/84 rigid-assembly failure? = **NO**

FINAL VERDICT = **B — ASSEMBLY ORDER PARTIALLY HELPS BUT ONE INSTALLATION STEP STILL FAILS**

## 1. Frozen authority

docs/84의 I2 one-piece harness, four straight legs, roots, tilts, lengths, thicknesses, direct slots,
1.03 mm/side × 0.93 mm mouths, shell, pusher, guide/hard stop, I2/I3 poses를 변경하지 않았다.
원본 `cad_dump/mesh_PushBtn.json`의 **3,530-facet one-solid detailed PushBtn**을 사용했고,
body/bottom/T1–T4/corner features를 유지했다. Actuator만 **D3.35 × projection 2.44 mm**이다.
Final collision verdict에 simplified proxy 사용 = **NO**. 새 STEP/geometry 생성 = **0**.

## 2. Sequence A — I2 harness before I3

- path: single straight docs/84 vector `{a['directionLocal']}`;
- travel / states: **{a['travelMm']:.3f} mm / {a['stateCount']}**;
- shell penetration: **{a['maximumPenetrationByFixedMm3']['SHELL']:.9f} mm³**;
- pusher penetration: **{a['maximumPenetrationByFixedMm3']['PUSHER']:.9f} mm³**;
- guide / hard stop / clip penetration: **{a['maximumPenetrationByFixedMm3']['GUIDE']:.9f} / {a['maximumPenetrationByFixedMm3']['HARD_STOP']:.9f} / {a['maximumPenetrationByFixedMm3']['CLIP']:.9f} mm³**;
- swept collision volume: **{a['sweptCollisionVolumeMm3']:.9f} mm³**;
- elastic bending assumed: **NO**.

따라서 I3 T2가 아직 없으면 현재 I2 one-piece harness는 현재 four slots에 먼저 설치할 수 있다.

## 3. Sequence B — detailed I2 PushBtn after seated harness

우선 기존 정상 switch preload authority인 **local −U open-side lateral path**를 사용했다.

- travel / states: **{b['travelMm']:.3f} mm / {b['stateCount']}**;
- maximum total unintended penetration: **{b['maximumUnintendedPenetrationMm3']:.9f} mm³**;
- limiting pair: **{b['worstCollision']['moving']} ↔ {b['worstCollision']['fixed']}**;
- limiting state / offset: **{b['worstCollision']['stateIndex']} / {b['worstCollision']['offsetMm']} mm**;
- limiting pair penetration: **{b['worstCollision']['penetrationMm3']:.9f} mm³**;
- swept collision volume: **{b['sweptCollisionVolumeMm3']:.9f} mm³**;
- shell / pusher / guide / hard-stop / clip maximum penetration on the documented path: **0 mm³**;
- I2 PushBtn insertion possible: **NO**.

Static FULL SEAT는 docs/84대로 penetration 0이지만, 실제 경로 중 body가 four-edge harness를 통과하지 못한다.
Static PASS를 Assembly PASS로 사용하지 않았다.

### Simple-path exclusion, without geometry search

| final approach | limiting pair | maximum sampled penetration |
|---|---|---:|
| documented −U lateral, 33 states | BODY ↔ HARNESS | 15.271882439 mm³ |
| rear axial −W, 33 states | BODY ↔ HARNESS | 20.006400668 mm³ |
| exterior axial +W, 33 states | BODY ↔ PUSHER | 63.086473062 mm³ |
| +U / +V / −V cardinal coarse gates | BODY ↔ HARNESS | 10.252846 / 13.010331 / 13.524522 mm³ |
| four UV diagonals, coarse gates | BODY ↔ HARNESS | minimum 9.923647 mm³ |

따라서 APPROACH→SHORT ALIGNMENT의 마지막 단순 translation도 어느 side/diagonal/axis로 진입하든 현재
harness 또는 pusher를 통과한다. 이를 회전과 세 번째 translation으로 우회하면 practical three-plus-DOF
puzzle motion이므로 지시 기준 practical FAIL이다. 회전 자동탐색이나 geometry optimization은 하지 않았다.

## 4. Sequence C — I3 afterward

Sequence C는 A와 B가 모두 PASS할 때만 실행하도록 명시되어 있다. B가 FAIL했으므로 legitimately completed
I2 assembly가 존재하지 않으며, I3를 teleport 배치해 C를 PASS시키는 검사를 하지 않았다.
결과는 **FAIL (prerequisite) / NOT EXECUTED**이다. 따라서 조립 순서 전체에서 I3 후설치는 성립하지 않는다.

## 5. Static manufacturing margin remains provisional

docs/84 reference를 변경 없이 유지한다:

- detailed terminal clearance: **{data['docs84Reference']['minimumDetailedTerminalClearanceMm']:.6f} mm**;
- detailed I3 clearance: **{data['docs84Reference']['minimumDetailedI3ClearanceMm']:.6f} mm**;
- effective FDM section: **{data['docs84Reference']['minimumEffectiveFdmSectionMm']:.6f} mm**;
- minimum remaining shell: **{data['docs84Reference']['minimumRemainingShellMm']:.6f} mm**.

Sequence A가 PASS해도 이 약 0.059 mm manufacturing margin은 provisional이다.

## 6. Renders and preservation

Sequence C 렌더는 prerequisite FAIL/STOP condition 때문에 생성하지 않았다. Teleport된 허위 조립 상태도 만들지 않았다.

{renders}

All {data['preservation']['protectedFileCount']} protected docs/79–84, prior-audit and production artifacts retain identical SHA-256 hashes:
**{data['preservation']['allProtectedFilesPreserved']}**. Production modification=0; geometry optimization=0;
8-button propagation=0; N2 redesign=0; physical coupon=0.
"""


def probe() -> None:
    datums = load_all_datums(); i2 = datums["I2"]
    placement = doc84.doc83.datum_location(i2, FROZEN_FRONT_DEPTHS["I2"])
    harness = import_step(HARNESS_STEP)
    shell = placement.inverse() * import_step(SHELL_STEP)
    pusher = pusher_system()
    fixed_mechanism = {"SHELL": shell, "PUSHER": pusher["pusher"], "GUIDE": pusher["guide"],
                       "HARD_STOP": pusher["stop"], "CLIP": pusher["clip"]}
    original, body, terminals, corners, old_actuator, actuator, hybrid = doc84.detailed_switch_parts()
    switch = {"BODY": body, "ACTUATOR": actuator, **terminals}

    a_direction = np.asarray([0.3415514166060052, -0.017899951255297575, 0.9396926207859084])
    results = {"A_docs84Straight": translation_probe("A_DOC84_STRAIGHT", {"HARNESS": harness},
                                                       fixed_mechanism, -a_direction * 1.60)}
    fixed_b = {**fixed_mechanism, "HARNESS": harness}
    directions = {
        "B_documentedLateralMinusU": np.asarray((-12.0, 0.0, 0.0)),
        "B_axisFromRearMinusW": np.asarray((0.0, 0.0, -12.0)),
        "B_axisFromExteriorPlusW": np.asarray((0.0, 0.0, 12.0)),
    }
    for name, offset in directions.items():
        results[name] = translation_probe(name, switch, fixed_b, offset)
    print(json.dumps({name: {key: row[key] for key in ("pass", "travelMm", "maximumPenetrationMm3",
                                                        "sweptCollisionVolumeMm3", "worstCollision")}
                      for name, row in results.items()}, indent=2), flush=True)


def screen_harness_directions() -> None:
    harness = import_step(HARNESS_STEP)
    original, body, terminals, corners, old_actuator, actuator, hybrid = doc84.detailed_switch_parts()
    switch = {"BODY": body, "ACTUATOR": actuator, **terminals}
    raw = {
        "+U": (1,0,0), "-U": (-1,0,0), "+V": (0,1,0), "-V": (0,-1,0),
        "+U+V": (1,1,0), "+U-V": (1,-1,0), "-U+V": (-1,1,0), "-U-V": (-1,-1,0),
    }
    rows = {}
    for name, vector in raw.items():
        start = unit(vector) * 12.0
        result = translation_probe(f"SCREEN_{name}", switch, {"HARNESS": harness}, start, states=9)
        rows[name] = {key: result[key] for key in ("pass", "maximumPenetrationMm3", "worstCollision")}
    print(json.dumps(rows, indent=2), flush=True)


def compute_b_swept() -> None:
    datums = load_all_datums(); i2 = datums["I2"]
    placement = doc84.doc83.datum_location(i2, FROZEN_FRONT_DEPTHS["I2"])
    harness = import_step(HARNESS_STEP)
    shell = placement.inverse() * import_step(SHELL_STEP)
    pusher = pusher_system()
    fixed = {"SHELL": shell, "PUSHER": pusher["pusher"], "GUIDE": pusher["guide"],
             "HARD_STOP": pusher["stop"], "CLIP": pusher["clip"], "HARNESS": harness}
    original, body, terminals, corners, old_actuator, actuator, hybrid = doc84.detailed_switch_parts()
    moving = {"BODY": body, "ACTUATOR": actuator, **terminals}
    start = np.asarray((-12.0, 0.0, 0.0), float)
    collisions = []; pair_sums = {}; maximum_total = 0.0; worst = None
    for index, fraction in enumerate(np.linspace(1.0, 0.0, 33)):
        print(f"swept_state={index}/32", flush=True)
        offset = start * float(fraction); total = 0.0
        for moving_name, base in moving.items():
            probe = moved(base, offset, f"B_SWEPT_{moving_name}_{index:02d}")
            for fixed_name, target in fixed.items():
                if not aabb_overlaps(probe, target):
                    continue
                common = probe & target
                penetration = volume(common)
                if penetration <= EPS:
                    continue
                key = f"{moving_name}:{fixed_name}"
                pair_sums[key] = pair_sums.get(key, 0.0) + penetration
                total += penetration
                collisions.append(common)
                if worst is None or penetration > worst["penetrationMm3"]:
                    worst = {"pair": key, "stateIndex": index, "offsetMm": offset.tolist(),
                             "penetrationMm3": penetration}
        maximum_total = max(maximum_total, total)
    swept = 0.0
    if collisions:
        print(f"swept_fuse_count={len(collisions)}", flush=True)
        union = collisions[0]
        for index, common in enumerate(collisions[1:], 1):
            if index % 20 == 0:
                print(f"swept_fuse={index}/{len(collisions)-1}", flush=True)
            union = union.fuse(common)
        swept = volume(union.clean())
    print(json.dumps({"maximumTotalPenetrationMm3": maximum_total,
                      "sweptCollisionVolumeMm3": swept, "worst": worst,
                      "pairAccumulatedPenetrationMm3": pair_sums,
                      "collisionShapeCount": len(collisions)}, indent=2), flush=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); RENDER.mkdir(parents=True, exist_ok=True)
    protected=protected_files(); before=doc84.hashes(protected)
    authority=json.loads(DOC84_JSON.read_text(encoding="utf-8"))
    datums=load_all_datums(); i2=datums["I2"]
    placement=doc84.doc83.datum_location(i2,FROZEN_FRONT_DEPTHS["I2"])
    harness=import_step(HARNESS_STEP)
    shell=placement.inverse()*import_step(SHELL_STEP)
    pusher=pusher_system()
    fixed_mechanism={"SHELL":shell,"PUSHER":pusher["pusher"],"GUIDE":pusher["guide"],
                     "HARD_STOP":pusher["stop"],"CLIP":pusher["clip"]}
    original,body,terminals,corners,old_actuator,actuator,hybrid=doc84.detailed_switch_parts()
    switch={"BODY":body,"ACTUATOR":actuator,**terminals}

    sequence_a=exact_translation_audit("SEQUENCE_A",{"HARNESS":harness},fixed_mechanism,
                                       -SEQUENCE_A_VECTOR*1.60,states=33,compute_swept=True)
    sequence_a["directionLocal"]=SEQUENCE_A_VECTOR.tolist()
    if not sequence_a["allStatesCollisionFree"]:
        raise RuntimeError("Sequence A unexpectedly failed under frozen docs/84 geometry")
    print("sequence_a=PASS",flush=True)

    sequence_b=exact_translation_audit("SEQUENCE_B",switch,{**fixed_mechanism,"HARNESS":harness},
                                       (-12.0,0.0,0.0),states=33,compute_swept=True)
    sequence_b["directionLocal"]=[1.0,0.0,0.0]
    sequence_b["motionDescription"]="start at local -U 12 mm; translate +U to full seat"
    if sequence_b["allStatesCollisionFree"]:
        raise RuntimeError("Sequence B unexpectedly passed; conditional Sequence C would need execution")
    print("sequence_b=FAIL",flush=True)

    render_paths=render_outputs(harness,shell,fixed_mechanism,switch,sequence_a,sequence_b)
    after=doc84.hashes(protected)
    c84=authority["comparison"]["C_robustDetailed"]
    data={
        "schema":"onegrip.i2-assembly-sequence-only-audit.v1",
        "generatedUtc":datetime.now(timezone.utc).isoformat(),
        "mode":"ASSEMBLY SEQUENCE ONLY / DOCS 84 GEOMETRY FROZEN / NO REDESIGN",
        "finalVerdict":"B — ASSEMBLY ORDER PARTIALLY HELPS BUT ONE INSTALLATION STEP STILL FAILS",
        "canAssemblyOrderAloneSolveDocs84Failure":False,
        "geometryFrozen":True,
        "sourceProof":{
            "sourceFile":"cad_dump/mesh_PushBtn.json","sourceObject":"PushBtn / ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID",
            "sourceTriangleCount":int(len(original.triangles)),"sourceSolidCount":int(len(original.full.solids())),
            "detailedBodyIncluded":True,"detailedBottomIncluded":True,"exactTerminalsIncluded":["T1","T2","T3","T4"],
            "cornerFeaturesIncluded":True,"measuredActuatorDiameterMm":3.35,"measuredActuatorProjectionMm":2.44,
            "simplifiedProxyUsedForFinalVerdict":False,
        },
        "sequences":{
            "A":{**sequence_a,"result":"PASS","I3Present":False,"I2SwitchPresent":False},
            "B":{**sequence_b,"result":"FAIL","switchAuthority":"original detailed PushBtn + measured actuator"},
            "C":{"result":"FAIL (PREREQUISITE) / NOT EXECUTED","reason":"Sequence B failed; no legitimately completed I2 state",
                 "teleportPlacementUsed":False,"geometryIndependentlyTested":False},
        },
        "simplePathExclusion":{
            "documentedMinusU":{"states":33,"limitingPair":"BODY:HARNESS","maximumPairPenetrationMm3":15.271882439323985},
            "rearMinusW":{"states":33,"limitingPair":"BODY:HARNESS","maximumPairPenetrationMm3":20.006400668253583},
            "exteriorPlusW":{"states":33,"limitingPair":"BODY:PUSHER","maximumPairPenetrationMm3":63.08647306174155},
            "cardinalCoarse":{"states":9,"plusUMm3":10.252845575856414,"plusVMm3":13.010330574176434,
                              "minusVMm3":13.524522025374871},
            "diagonalCoarse":{"states":9,"minimumPairPenetrationMm3":9.9236467336283,
                              "allFourDirectionsFail":True},
            "twoStageConclusion":"no simple final translation remains; adding rotation and a third move is a practical puzzle motion",
        },
        "docs84Reference":{
            "minimumDetailedTerminalClearanceMm":float(c84["minimumTerminalClearanceMm"]),
            "minimumDetailedI3ClearanceMm":float(c84["minimumNeighborClearanceMm"]),
            "minimumEffectiveFdmSectionMm":float(c84["minimumEffectiveFdmThicknessMm"]),
            "minimumRemainingShellMm":float(c84["minimumRemainingExteriorShellMm"]),
            "staticFinalFitPenetrationMm3":0.0,"manufacturingMargin":"PROVISIONAL",
        },
        "prohibitions":{
            "geometryOptimization":0,"legRedesign":0,"angleSearch":0,"rootSearch":0,"slotRedesign":0,
            "mouthEnlargement":0,"shellRelief":0,"newSupport":0,"newHarnessArchitecture":0,
            "physicalCoupon":0,"eightButtonPropagation":0,"N2Redesign":0,"productionModification":0,
        },
        "preservation":{"protectedFileCount":len(protected),"hashesBefore":before,"hashesAfter":after,
                        "allProtectedFilesPreserved":before==after},
        "outputs":{"report":doc84.relative(REPORT),"json":doc84.relative(JSON_PATH),"renders":render_paths,
                   "newStepGeometry":[]},
    }
    JSON_PATH.write_text(json.dumps(data,indent=2),encoding="utf-8")
    REPORT.write_text(report_text(data),encoding="utf-8")
    print(json.dumps({"verdict":data["finalVerdict"],"sequenceA":sequence_a["allStatesCollisionFree"],
                      "sequenceB":sequence_b["allStatesCollisionFree"],"sequenceC":"NOT EXECUTED",
                      "bMaximumPenetrationMm3":sequence_b["maximumUnintendedPenetrationMm3"],
                      "bSweptCollisionMm3":sequence_b["sweptCollisionVolumeMm3"],
                      "renders":len(render_paths),"protected":before==after,
                      "report":doc84.relative(REPORT)},indent=2),flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "screen":
        screen_harness_directions()
    elif len(sys.argv) > 1 and sys.argv[1] == "swept":
        compute_b_swept()
    elif len(sys.argv) > 1 and sys.argv[1] == "probe":
        probe()
    else:
        main()
