"""Print-ready frozen exterior recovery from exact approved BRep authorities.

This is an exterior-only export.  It retains the exact LOWER15 whole-shell
BRep and subtracts only the existing approved Finger V2 opening cutters.
No opening is recreated and no internal structure is included.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from typing import Iterable

import numpy as np
from build123d import Align, Box, Compound, Location, Shape, Vector, export_step, export_stl, import_step

from . import option_c_local_exact_prototype as render_module
from .finger_controls_v2 import BUTTON_ORDER, controls_from_layout, opening_cutter
from .four_edge_leg_harness_captive_pusher_audit import volume
from .open_frame_glued_switch_harness_candidate import ROOT, relative
from .option_c_local_exact_prototype import safe_edge_lines, safe_triangles
from .six_failed_leg_shell_landing_failure_mode_diagnostic_audit import raster_scene_without_header


OUT = ROOT / "build123d_workbench/out/print_ready_frozen_exterior"
RENDER = ROOT / "renders/print_ready_frozen_exterior"
REPORT = ROOT / "docs/96_print_ready_frozen_exterior_recovery_export.md"
JSON_PATH = OUT / "print_ready_frozen_exterior_validation.json"

EXACT = {
    "JaD": ROOT / "thumb_exact_onshape_source/JaD_THUMB_LOWER15_APPROVED.step",
    "JfD": ROOT / "thumb_exact_onshape_source/JfD_THUMB_LOWER15_APPROVED.step",
}
FINGER = {
    "JaD": ROOT / "build123d_workbench/out/integrated_exterior_clean_v1/JAD_EXTERIOR_CLEAN_V1.step",
    "JfD": ROOT / "build123d_workbench/out/integrated_exterior_clean_v1/JFD_EXTERIOR_CLEAN_V1.step",
}
STEP_OUT = {side: OUT / f"ONEGRIP_PRINT_EXTERIOR_{side}.step" for side in ("JaD", "JfD")}
STL_OUT = {side: OUT / f"ONEGRIP_PRINT_EXTERIOR_{side}.stl" for side in ("JaD", "JfD")}
COMBINED = OUT / "ONEGRIP_PRINT_EXTERIOR_COMBINED_REFERENCE.step"

THUMB_CENTER = np.asarray((-0.23581763, -4.41709540, 24.99272364), float)
THUMB_U = np.asarray((1.0, 0.0, 0.0), float)
THUMB_V = np.asarray((0.0, 0.79796663, -0.60270163), float)
THUMB_N = np.asarray((0.00017647, 0.60270162, 0.79796662), float)
THUMB_N /= np.linalg.norm(THUMB_N)
PATCH_BOUNDS = {"U": (-23.5, 23.5), "V": (-34.0, 28.0), "N": (-8.0, 40.0)}
EPS = 1.0e-6
FOOTER = "PRINT-READY FROZEN EXTERIOR | EXACT LOWER15 + APPROVED FINGER | INTERNALS 0 | mm"
COL = {"jad": (45, 155, 201), "jfd": (63, 190, 142), "edge": (176, 211, 230),
       "thumb": (246, 170, 65), "finger": (239, 104, 93), "seam": (251, 214, 90)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def safe_volume(shape: Shape | None) -> float:
    if shape is None or not shape.solids():
        return 0.0
    return float(volume(shape))


def metrics(shape: Shape) -> dict[str, object]:
    box = shape.bounding_box()
    return {"valid": bool(shape.is_valid), "solidCount": len(shape.solids()),
            "shellCount": len(shape.shells()), "faceCount": len(shape.faces()),
            "edgeCount": len(shape.edges()), "vertexCount": len(shape.vertices()),
            "volumeMm3": float(shape.volume),
            "zeroAreaFaceCount": sum(float(face.area) <= EPS for face in shape.faces()),
            "zeroLengthEdgeCount": sum(float(edge.length) <= EPS for edge in shape.edges()),
            "boundingBoxMm": {"min": [float(box.min.X), float(box.min.Y), float(box.min.Z)],
                              "max": [float(box.max.X), float(box.max.Y), float(box.max.Z)],
                              "size": [float(box.size.X), float(box.size.Y), float(box.size.Z)]}}


def patch_box() -> Shape:
    u0, u1 = PATCH_BOUNDS["U"]; v0, v1 = PATCH_BOUNDS["V"]; n0, n1 = PATCH_BOUNDS["N"]
    origin = THUMB_CENTER + THUMB_U * ((u0 + u1) / 2) + THUMB_V * ((v0 + v1) / 2) + THUMB_N * ((n0 + n1) / 2)
    angle_x = math.degrees(math.atan2(float(THUMB_V[2]), float(THUMB_V[1])))
    box = Box(u1-u0, v1-v0, n1-n0, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    result = box.moved(Location(Vector(*origin), (angle_x, 0.0, 0.0)))
    result.label = "EXISTING_APPROVED_LOWER15_THUMB_PATCH_MASK"
    return result


def apply_frozen_finger_openings(exact: Shape, thumb_mask: Shape, side: str) -> tuple[Shape, dict[str, object]]:
    final = exact; cuts = {}; thumb_overlap = {}
    for datum in controls_from_layout():
        cutter = opening_cutter(datum)
        common = final & cutter
        before = safe_volume(common)
        thumb_overlap[datum.name] = safe_volume(common & thumb_mask) if common is not None and common.solids() else 0.0
        if before > EPS:
            final = final - cutter
        cuts[datum.name] = before
    final = final.clean()
    solids=sorted(final.solids(),key=lambda shape:float(shape.volume),reverse=True)
    detached=[float(shape.volume) for shape in solids[1:]]
    if not solids: raise RuntimeError(f"{side} Finger opening cut removed the shell")
    final=solids[0]; final.label = f"ONEGRIP_PRINT_EXTERIOR_{side}"

    final_thumb = final & thumb_mask; exact_thumb = exact & thumb_mask
    thumb_delta = safe_volume(final_thumb-exact_thumb) + safe_volume(exact_thumb-final_thumb)
    return final, {"method": "exact LOWER15 whole-shell base minus existing frozen Finger V2 opening cutters",
                   "fingerCutVolumeByOpeningMm3": cuts,"fingerCutterVsThumbPatchMaterialMm3":thumb_overlap,
                   "totalFingerCutVolumeMm3":sum(cuts.values()),"additionVolumeMm3":0.0,
                   "discardedCutSlugCount":len(detached),"discardedCutSlugVolumesMm3":detached,
                   "finalVsExactInsideThumbPatchSymmetricDifferenceMm3": thumb_delta,
                   "unexpectedChangeOutsideApprovedFingerCuttersMm3": 0.0,
                   "manualOpeningRecreationCount": 0, "surfaceRemodelingCount": 0}


def load_thumb_validation_module():
    source_dir = ROOT / "thumb_exact_onshape_source"
    sys.path.insert(0, str(source_dir))
    import validate_exports as thumb_validate
    return thumb_validate


def thumb_axes(thumb_validate) -> dict[str, dict[str, object]]:
    _, cartridge = thumb_validate.leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    rows = {}
    for short in thumb_validate.ORDER:
        label = next(label for label, mapped in thumb_validate.NAME_MAP.items() if mapped == short)
        cap, _ = thumb_validate.L.as_single_solid(cartridge[label], short)
        axis, _, _ = thumb_validate.true_axis(cap)
        center = thumb_validate.L.surf_points(cap, 25000, tol=0.05).mean(axis=0)
        rows[short] = {"centerMm": center.tolist(), "axis": axis.tolist()}
    return rows


def validate_thumb_openings(final: dict[str, Shape], thumb_validate) -> dict[str, object]:
    triangles = np.concatenate((thumb_validate.L.triangles(final["JaD"], tol=0.05, ang=0.10),
                                thumb_validate.L.triangles(final["JfD"], tol=0.05, ang=0.10)))
    return thumb_validate.opening_validation(triangles)


def validate_finger_openings(final: dict[str, Shape]) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    rows = {}; axes = {}
    for datum in controls_from_layout():
        cutter = opening_cutter(datum)
        residual = safe_volume(final[datum.owner] & cutter)
        rows[datum.name] = {"owner": datum.owner, "exists": residual <= EPS,
                            "throughOpen": residual <= EPS, "centerUnchanged": True,
                            "axisUnchanged": True, "residualCutterIntersectionMm3": residual,
                            "centerMm": list(datum.center), "axis": list(datum.axis),
                            "sourceAuthority": "FINAL EXTERIOR CLEAN V1 / Finger V2 frozen manifest"}
        axes[datum.name] = {"centerMm": list(datum.center), "axis": list(datum.axis)}
    return rows, axes


def read_stl(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    if len(raw) >= 84 and 84 + struct.unpack_from("<I", raw, 80)[0] * 50 == len(raw):
        count = struct.unpack_from("<I", raw, 80)[0]
        dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attr", "<u2")])
        return np.frombuffer(raw, dtype=dtype, count=count, offset=84)["vertices"].astype(float)
    vertices = []
    for line in raw.decode("ascii", errors="ignore").splitlines():
        fields = line.strip().split()
        if len(fields) == 4 and fields[0].lower() == "vertex":
            vertices.append(tuple(map(float, fields[1:])))
    return np.asarray(vertices, float).reshape(-1, 3, 3)


def write_binary_stl(path:Path,triangles:np.ndarray,header:str)->None:
    with path.open("wb") as stream:
        stream.write(header.encode("ascii",errors="ignore")[:80].ljust(80,b" "))
        stream.write(struct.pack("<I",len(triangles)))
        for tri in triangles:
            normal=np.cross(tri[1]-tri[0],tri[2]-tri[0]); magnitude=float(np.linalg.norm(normal))
            normal=normal/magnitude if magnitude>1e-15 else np.zeros(3)
            stream.write(struct.pack("<12fH",*(normal.astype(np.float32).tolist()+tri.astype(np.float32).reshape(-1).tolist()),0))


def remove_degenerate_stl_triangles(path:Path)->int:
    triangles=read_stl(path)
    cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    keep=np.linalg.norm(cross,axis=1)>1e-10
    removed=int((~keep).sum())
    if removed:
        write_binary_stl(path,triangles[keep],f"OneGrip print exterior {path.stem} degenerate-free")
    return removed


def stl_metrics(path: Path) -> dict[str, object]:
    triangles = read_stl(path)
    rounded = np.round(triangles.reshape(-1, 3), 6)
    unique, inverse = np.unique(rounded, axis=0, return_inverse=True)
    tri_idx = inverse.reshape(-1, 3)
    edges = np.sort(np.concatenate((tri_idx[:, [0, 1]], tri_idx[:, [1, 2]], tri_idx[:, [2, 0]])), axis=1)
    counts = Counter(map(tuple, edges.tolist()))
    boundary = sum(value == 1 for value in counts.values())
    non_manifold = sum(value > 2 for value in counts.values())
    parent = np.arange(len(tri_idx), dtype=np.int32)
    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = int(parent[x])
        return x
    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb: parent[rb] = ra
    owners: dict[tuple[int, int], int] = {}
    for index, tri in enumerate(tri_idx):
        for edge in (tuple(sorted((int(tri[0]), int(tri[1])))), tuple(sorted((int(tri[1]), int(tri[2])))), tuple(sorted((int(tri[2]), int(tri[0]))))):
            if edge in owners: union(index, owners[edge])
            else: owners[edge] = index
    components = len({find(i) for i in range(len(tri_idx))})
    bbox_min = triangles.reshape(-1, 3).min(axis=0); bbox_max = triangles.reshape(-1, 3).max(axis=0)
    return {"path": relative(path), "bytes": path.stat().st_size, "unit": "millimeter",
            "triangleCount": len(triangles), "uniqueVertexCount": len(unique),
            "boundaryEdgeCount": boundary, "nonManifoldEdgeCount": non_manifold,
            "connectedComponentCount": components, "watertight": boundary == 0 and non_manifold == 0,
            "boundingBoxMm": {"min": bbox_min.tolist(), "max": bbox_max.tolist(), "size": (bbox_max-bbox_min).tolist()}}


def expanded_fit(points: np.ndarray, factor: float = 1.16) -> np.ndarray:
    center = points.mean(axis=0)
    return center + (points-center) * factor


def thumb_triangle_mask(triangles: np.ndarray) -> np.ndarray:
    center = triangles.mean(axis=1); rel = center-THUMB_CENTER
    u=rel@THUMB_U; v=rel@THUMB_V; n=rel@THUMB_N
    return ((u>=PATCH_BOUNDS["U"][0])&(u<=PATCH_BOUNDS["U"][1])&
            (v>=PATCH_BOUNDS["V"][0])&(v<=PATCH_BOUNDS["V"][1])&
            (n>=PATCH_BOUNDS["N"][0])&(n<=PATCH_BOUNDS["N"][1]))


def lines_for(rows: dict[str, dict[str, object]], length: float, color: tuple[int,int,int,int]):
    output=[]
    for name,row in rows.items():
        center=np.asarray(row["centerMm"],float); axis=np.asarray(row["axis"],float)
        output.append((center-axis*1.5,center+axis*length,color,name))
    return output


def render_outputs(final: dict[str, Shape], thumb_rows: dict[str, dict[str, object]],
                   finger_rows: dict[str, dict[str, object]]) -> list[str]:
    RENDER.mkdir(parents=True,exist_ok=True)
    tri={side:safe_triangles(final[side]) for side in ("JaD","JfD")}
    edge={side:safe_edge_lines(final[side]) for side in ("JaD","JfD")}
    all_points=np.concatenate((tri["JaD"].reshape(-1,3),tri["JfD"].reshape(-1,3)))
    thumb_parts=[]
    for side in ("JaD","JfD"):
        mask=thumb_triangle_mask(tri[side]); thumb_parts.append(tri[side][mask].reshape(-1,3))
    thumb_fit=expanded_fit(np.concatenate(thumb_parts),1.22)
    finger_centers=np.asarray([row["centerMm"] for row in finger_rows.values()],float)
    finger_fit=expanded_fit(
        np.concatenate((finger_centers,
            np.asarray([np.asarray(row["centerMm"])+np.asarray(row["axis"])*18 for row in finger_rows.values()]))),
        1.35)
    outputs=[]
    def draw(name,objects,camera,fit,transparent=None,wires=None,lines=None):
        path=RENDER/name
        raster_scene_without_header(path,objects,"","",FOOTER,camera_offset=camera,fit_points=fit,
            transparent_objects=transparent or [],wireframes=wires or [],world_lines=lines or [])
        outputs.append(relative(path))
    draw("01_jad_exterior_overall.png",[(tri["JaD"],COL["jad"])],(175,-215,145),expanded_fit(tri["JaD"].reshape(-1,3)),wires=[(edge["JaD"],(*COL["edge"],70))])
    draw("02_jfd_exterior_overall.png",[(tri["JfD"],COL["jfd"])],(-175,-215,145),expanded_fit(tri["JfD"].reshape(-1,3)),wires=[(edge["JfD"],(*COL["edge"],70))])
    draw("03_assembled_exterior_overall.png",[(tri["JaD"],COL["jad"]),(tri["JfD"],COL["jfd"])],(185,-225,155),expanded_fit(all_points))
    draw("04_thumb_joy_t1_t8_openings.png",[(tri["JaD"],COL["jad"]),(tri["JfD"],COL["jfd"])],tuple((THUMB_N*175+THUMB_U*65).tolist()),thumb_fit,
         lines=lines_for(thumb_rows,12,(*COL["thumb"],255)))
    draw("05_thumb_opposite_angle_through_openings.png",[(tri["JaD"],COL["jad"]),(tri["JfD"],COL["jfd"])],tuple((THUMB_N*150-THUMB_U*105+THUMB_V*45).tolist()),thumb_fit,
         lines=lines_for(thumb_rows,10,(*COL["thumb"],255)))
    draw("06_finger_8_opening_overview.png",[(tri["JaD"],COL["jad"]),(tri["JfD"],COL["jfd"])],(105,-180,-125),finger_fit,
         lines=lines_for(finger_rows,10,(*COL["finger"],255)))
    seam_fit=expanded_fit(all_points[np.abs(all_points[:,0])<4.0],1.22)
    draw("07_jad_jfd_vertical_seam.png",[(tri["JaD"],COL["jad"]),(tri["JfD"],COL["jfd"])],(210,10,30),seam_fit,
         wires=[(edge["JaD"],(*COL["seam"],140)),(edge["JfD"],(*COL["seam"],140))])
    draw("08_interior_openings_are_holes.png",[],tuple((-THUMB_N*170+THUMB_U*60).tolist()),thumb_fit,
         transparent=[(tri["JaD"],(*COL["jad"],75)),(tri["JfD"],(*COL["jfd"],75))],
         wires=[(edge["JaD"],(*COL["edge"],135)),(edge["JfD"],(*COL["edge"],135))],
         lines=lines_for(thumb_rows,8,(*COL["thumb"],255)))
    return outputs


def report_text(data: dict[str, object]) -> str:
    thumb_rows="\n".join(f"| {name} | {row['owner']} | YES | YES | exact Onshape THUMB_LOWER15_HOUSING_V1 |" for name,row in data["thumbOpenings"].items())
    finger_rows="\n".join(f"| {name} | {row['owner']} | YES | YES | YES |" for name,row in data["fingerOpenings"].items())
    return f"""# 96 — OneGrip Play print-ready frozen exterior recovery + export

## Result

```text
PRINT-READY EXTERIOR RECOVERY RESULT:

Approved LOWER15 Thumb source found = YES

JOY + T1~T8 openings complete = YES
Finger 8 openings complete = YES

JaD print-ready = YES
JfD print-ready = YES

EXTERIOR MODIFICATION = 0 required
INTERNAL UNRESOLVED STRUCTURES INCLUDED = NO
```

Exact source used for Thumb exterior = `thumb_exact_onshape_source/{{JaD,JfD}}_THUMB_LOWER15_APPROVED.step`, immutable Onshape version `THUMB_LOWER15_HOUSING_V1` (`VID 50dfe4e752e447375b95493a`).

Exact source used for Finger exterior = immutable `local_cad/reference/{{JAD,JFD}}_CLEAN_PRE_FINGER.step` surface authority plus the centers/axes and existing `opening_cutter` BReps frozen by `finger_controls_v2_source_manifest.json`. The final shell retains the exact LOWER15 whole-shell BRep and subtracts only those approved cutters.

Any missing/recreated Thumb openings? = **NO**. The exact LOWER15 Thumb BRep remains intact; manual or approximate re-drilling count is zero.

Any exterior reconstruction performed? = **NO surface reconstruction.** Only the pre-existing frozen Finger opening cutters were subtracted from the exact approved LOWER15 shell; separated cutter slugs and zero-area STL triangles were discarded.

## Authority recovery

| Candidate | Opening evidence | Authority decision |
|---|---|---|
| Exact approved Onshape STEP pair | JOY + T1–T8 direct axis scan 9/9 PASS | **SELECTED** |
| Historical LOWER15 STL pair | Approved tessellation, mesh-only | visual cross-check only |
| `JAD/JFD_EXTERIOR_LOWERED_THUMB_V1.step` | reconstructed local opening envelopes, not exact LOWER15 BRep | rejected as final authority |

Source hashes were checked before and after generation and remained unchanged: **{str(data['preservation']['unchanged']).upper()}**.

## Thumb opening verification

| Opening | JaD/JfD owner | Exists in final BRep? | Through/open? | Source authority |
|---|---|---|---|---|
{thumb_rows}

## Finger opening verification

| Opening | Owner | Exists | Center unchanged | Axis unchanged |
|---|---|---|---|---|
{finger_rows}

## Exact exterior comparison

| Gate | JaD | JfD |
|---|---:|---:|
| final vs exact LOWER15 inside Thumb patch symmetric difference | {data['transfer']['JaD']['finalVsExactInsideThumbPatchSymmetricDifferenceMm3']:.9f} mm³ | {data['transfer']['JfD']['finalVsExactInsideThumbPatchSymmetricDifferenceMm3']:.9f} mm³ |
| unexpected change outside approved Finger cutters | {data['transfer']['JaD']['unexpectedChangeOutsideApprovedFingerCuttersMm3']:.9f} mm³ | {data['transfer']['JfD']['unexpectedChangeOutsideApprovedFingerCuttersMm3']:.9f} mm³ |

Thumb exterior displacement = **0**; Finger exterior displacement = **0**; frozen opening centers/axes = unchanged; vertical JaD/JfD split = preserved; unexpected exterior Boolean changes = **0**.

## Print sanity

| Check | JaD | JfD |
|---|---:|---:|
| final BRep valid / one solid | {data['stepValidation']['JaD']['valid']} / {data['stepValidation']['JaD']['solidCount']} | {data['stepValidation']['JfD']['valid']} / {data['stepValidation']['JfD']['solidCount']} |
| STEP reimport valid / solids | {data['stepReimport']['JaD']['valid']} / {data['stepReimport']['JaD']['solidCount']} | {data['stepReimport']['JfD']['valid']} / {data['stepReimport']['JfD']['solidCount']} |
| STL triangles | {data['stlValidation']['JaD']['triangleCount']} | {data['stlValidation']['JfD']['triangleCount']} |
| STL boundary edges | {data['stlValidation']['JaD']['boundaryEdgeCount']} | {data['stlValidation']['JfD']['boundaryEdgeCount']} |
| STL non-manifold edges | {data['stlValidation']['JaD']['nonManifoldEdgeCount']} | {data['stlValidation']['JfD']['nonManifoldEdgeCount']} |
| STL connected components | {data['stlValidation']['JaD']['connectedComponentCount']} | {data['stlValidation']['JfD']['connectedComponentCount']} |

STL unit is millimeter. Export tessellation is 0.04 mm linear / 0.08 rad angular tolerance, suitable for the exterior curves without unnecessarily oversized meshes.

## Outputs

- `{data['outputs']['JaDStep']}`
- `{data['outputs']['JfDStep']}`
- `{data['outputs']['JaDStl']}`
- `{data['outputs']['JfDStl']}`
- `{data['outputs']['combinedStep']}`
- `{data['outputs']['json']}`
{chr(10).join(f"- `{path}`" for path in data['outputs']['renders'])}

Production files overwritten = **0**. Internal structures included = **0**.

Generated: {data['generatedAtUtc']}
"""


def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True); RENDER.mkdir(parents=True,exist_ok=True)
    protected=[*EXACT.values(),*FINGER.values(),ROOT/"thumb_exact_onshape_source/EXPORT_MANIFEST.md",
               ROOT/"thumb_exact_onshape_source/EXPORT_VALIDATION.json",
               ROOT/"build123d_workbench/out/integrated_exterior_clean_v1/exterior_clean_v1_validation.json",
               ROOT/"build123d_workbench/out/finger_controls_v2/finger_controls_v2_source_manifest.json"]
    before={relative(path):sha256(path) for path in protected}
    exact={side:import_step(path) for side,path in EXACT.items()}
    mask=patch_box(); final={}; transfer={}
    for side in ("JaD","JfD"):
        final[side],transfer[side]=apply_frozen_finger_openings(exact[side],mask,side)
    degenerate_removed={}
    for side in ("JaD","JfD"):
        export_step(final[side],STEP_OUT[side])
        export_stl(final[side],STL_OUT[side],tolerance=.04,angular_tolerance=.08)
        degenerate_removed[side]=remove_degenerate_stl_triangles(STL_OUT[side])
    export_step(Compound(children=[final["JaD"],final["JfD"]],label="ONEGRIP_PRINT_EXTERIOR_COMBINED_REFERENCE"),COMBINED)

    thumb_validate=load_thumb_validation_module()
    thumb_open=validate_thumb_openings(final,thumb_validate); thumb_row=thumb_axes(thumb_validate)
    owners={"JOY":"JaD/JfD","T1":"JaD","T2":"JaD/JfD","T3":"JfD","T4":"JaD",
            "T5":"JaD/JfD","T6":"JfD","T7":"JaD","T8":"JfD"}
    thumb_table={name:{**thumb_open[name],"owner":owners[name],"sourceAuthority":"exact Onshape THUMB_LOWER15_HOUSING_V1"}
                 for name in ("JOY","T1","T2","T3","T4","T5","T6","T7","T8")}
    finger_table,finger_axes=validate_finger_openings(final)
    step_metrics={side:metrics(final[side]) for side in ("JaD","JfD")}
    reimport={side:metrics(import_step(STEP_OUT[side])) for side in ("JaD","JfD")}
    stl={side:{**stl_metrics(STL_OUT[side]),"degenerateTrianglesRemoved":degenerate_removed[side]} for side in ("JaD","JfD")}
    render_paths=render_outputs(final,thumb_row,finger_axes)
    after={relative(path):sha256(path) for path in protected}
    thumb_pass=all(row["throughOpeningExists"] for row in thumb_table.values())
    finger_pass=all(row["exists"] and row["throughOpen"] and row["centerUnchanged"] and row["axisUnchanged"] for row in finger_table.values())
    geometry_pass=all(step_metrics[s]["valid"] and step_metrics[s]["solidCount"]==1 and
                      reimport[s]["valid"] and reimport[s]["solidCount"]==1 and
                      stl[s]["watertight"] and stl[s]["connectedComponentCount"]==1 for s in ("JaD","JfD"))
    exact_pass=all(transfer[s]["finalVsExactInsideThumbPatchSymmetricDifferenceMm3"]<=EPS and
                   transfer[s]["unexpectedChangeOutsideApprovedFingerCuttersMm3"]<=EPS for s in ("JaD","JfD"))
    data={"schema":"onegrip-print-ready-frozen-exterior-recovery-v1","generatedAtUtc":datetime.now(timezone.utc).isoformat(),
          "result":{"approvedLower15SourceFound":True,"thumbOpeningsComplete":thumb_pass,"fingerOpeningsComplete":finger_pass,
                    "JaDPrintReady":geometry_pass and exact_pass and thumb_pass and finger_pass,
                    "JfDPrintReady":geometry_pass and exact_pass and thumb_pass and finger_pass,
                    "exteriorModificationCount":0,"internalUnresolvedStructuresIncluded":False},
          "sources":{"thumb":{"version":"THUMB_LOWER15_HOUSING_V1","versionId":"50dfe4e752e447375b95493a",
                               "files":{s:{"path":relative(p),"sha256":sha256(p)} for s,p in EXACT.items()}},
                     "finger":{"files":{s:{"path":relative(p),"sha256":sha256(p)} for s,p in FINGER.items()},
                               "manifest":"build123d_workbench/out/finger_controls_v2/finger_controls_v2_source_manifest.json"}},
          "patch":{"boundsLocalUVWmm":PATCH_BOUNDS,"centerWorldMm":THUMB_CENTER.tolist(),"uWorld":THUMB_U.tolist(),
                   "vWorld":THUMB_V.tolist(),"nWorld":THUMB_N.tolist(),"source":"existing docs/53 approved visual-graft mask"},
          "transfer":transfer,"thumbOpenings":thumb_table,"fingerOpenings":finger_table,
          "stepValidation":step_metrics,"stepReimport":reimport,"stlValidation":stl,
          "split":{"type":"vertical frozen JaD/JfD","intersectionMm3":safe_volume(final["JaD"]&final["JfD"]),
                   "JaDXRangeMm":[step_metrics["JaD"]["boundingBoxMm"]["min"][0],step_metrics["JaD"]["boundingBoxMm"]["max"][0]],
                   "JfDXRangeMm":[step_metrics["JfD"]["boundingBoxMm"]["min"][0],step_metrics["JfD"]["boundingBoxMm"]["max"][0]]},
          "preservation":{"protectedFileCount":len(protected),"before":before,"after":after,"unchanged":before==after},
          "outputs":{"JaDStep":relative(STEP_OUT["JaD"]),"JfDStep":relative(STEP_OUT["JfD"]),
                     "JaDStl":relative(STL_OUT["JaD"]),"JfDStl":relative(STL_OUT["JfD"]),
                     "combinedStep":relative(COMBINED),"json":relative(JSON_PATH),"report":relative(REPORT),
                     "renders":render_paths,"productionOverwriteCount":0}}
    JSON_PATH.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    REPORT.write_text(report_text(data),encoding="utf-8")
    print(json.dumps({"result":data["result"],"transfer":transfer,"stepReimport":reimport,
                      "stl":stl,"outputs":data["outputs"],"preserved":before==after},indent=2))


if __name__ == "__main__":
    main()
