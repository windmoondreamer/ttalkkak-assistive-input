"""Audit-only open-frame glued ITS-1105 harness candidate.

Creates one standard mechanical core, position-specific shell-derived glue
feet, an opening-datum alignment jig, an all-eight virtual placement, and an
OPEN_FRAME_HARNESS_FDM_COUPON_V2.  Frozen production geometry is read-only.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gc
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import (
    Align, Box, Compound, Cylinder, Location, Plane, Shape, Vector,
    export_step, export_stl,
)
from scipy.spatial import cKDTree

from .detailed_pushbtn_8_button_revalidation import mesh_to_faceted_solid
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, point_at, unit
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .option_c_local_exact_prototype import raster_scene, safe_edge_lines, safe_triangles
from .source_faithful_button_mechanism_fdm_rebase_audit import (
    ACTUAL, BUTTONS, load_mesh, sha256,
)
from .szh_ek056_provisional_thumb_integration_audit import placement as szh_placement
from .szh_ek056_web_reference import build_reference as build_szh_reference


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build123d_workbench/out/open_frame_glued_switch_harness_candidate"
RENDER = ROOT / "renders/open_frame_glued_switch_harness_candidate"
REPORT = ROOT / "docs/77_open_frame_glued_switch_harness_candidate.md"
JSON_PATH = OUT / "open_frame_glued_switch_harness_candidate.json"
CORE_STEP = OUT / "STANDARD_OPEN_FRAME_HARNESS_CORE_AUDIT_ONLY.step"
I2_STEP = OUT / "I2_OPEN_FRAME_GLUED_HARNESS_AUDIT_ONLY.step"
JIG_STEP = OUT / "I2_OPENING_DATUM_ALIGNMENT_JIG_AUDIT_ONLY.step"
ALL8_STEP = OUT / "ALL8_VIRTUAL_OPEN_FRAME_HARNESS_AUDIT_ONLY.step"
COUPON_STEP = OUT / "OPEN_FRAME_HARNESS_FDM_COUPON_V2_AUDIT_ONLY.step"
COUPON_STL = OUT / "OPEN_FRAME_HARNESS_FDM_COUPON_V2_AUDIT_ONLY.stl"

REPRESENTATIVE = "I2"
BODY_U = 6.12
BODY_V = 6.05
BODY_H = 3.56
ACT_D = 3.35
ACT_PROJ = 2.44
TOTAL_H = 6.00
GUIDE_OD = 7.40
GUIDE_BORE_D = 4.40
GUIDE_CAVITY_D = 5.00
PUSHER_SHAFT_D = 4.00
PUSHER_TIP_D = 2.60
PUSHER_SHOULDER_D = 4.80
REST_GAP = 0.08
T_CLICK = 0.33
T_DESIGN_FULL = 0.38
T_HARD_STOP = 0.38
BONDLINE = 0.30
FOOT_THICKNESS = 1.60
STRUCTURAL_MIN = 1.20
STRUCTURAL_PREFERRED = 1.60
OPENING = 8.00

OWNER_MESH = {"JaD": "ITS_LIVE_JaD", "JfD": "ITS_LIVE_JfD"}
TRIM_DECISIONS = {
    "N1": "T1/T2/T3/T4 available",
    "N2": "T1/T3 active; T2/T4 unused trim",
    "I2": "T1/T2/T3/T4 open",
    "I3": "T1/T2/T3/T4 open",
    "I4": "T1/T2/T3/T4 open",
    "M3": "T1/T2/T3/T4 open",
    "M4": "T2 unused; other terminals open",
    "N3": "T3 unused; other terminals open",
}

PROTECTED = [
    ROOT / "build123d_workbench/finger_controls_v2.py",
    ROOT / "build123d_workbench/n1_production_intent_mechanism.py",
    ROOT / "build123d_workbench/n2_production_intent_mechanism.py",
    ROOT / "build123d_workbench/i2_i3_production_intent_mechanism.py",
    ROOT / "build123d_workbench/i4_m3_production_intent_mechanisms.py",
    ROOT / "build123d_workbench/m4_n3_production_intent_mechanism.py",
    ROOT / "build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JAD_EXTERIOR_LOWERED_THUMB_V1.step",
    ROOT / "build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JFD_EXTERIOR_LOWERED_THUMB_V1.step",
    ROOT / "build123d_workbench/out/button_fdm_coupon/BUTTON_FDM_TEST_COUPON.step",
    ROOT / "cad_dump/mesh_ITS_LIVE_JaD.json",
    ROOT / "cad_dump/mesh_ITS_LIVE_JfD.json",
    ROOT / "cad_dump/its1105_physical_sample_reaudit.json",
    ROOT / "docs/76_source_faithful_button_mechanism_and_fdm_rebase_audit.md",
]

C = {
    "core": (59, 195, 139), "switch": (231, 94, 102), "pusher": (245, 184, 66),
    "guide": (68, 165, 224), "foot": (155, 107, 218), "glue": (245, 132, 62),
    "shell": (120, 137, 155), "jig": (242, 202, 76), "terminal": (205, 213, 222),
    "axis": (46, 188, 218), "stop": (239, 83, 84), "szh": (190, 118, 221),
}
FOOTER = "AUDIT/CANDIDATE ONLY | EXTERIOR + JaD/JfD SPLIT PRESERVED | PRODUCTION MODIFICATION = 0"


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def bounds(shape: Shape) -> tuple[np.ndarray, np.ndarray]:
    b = shape.bounding_box()
    return np.asarray((b.min.X, b.min.Y, b.min.Z), float), np.asarray((b.max.X, b.max.Y, b.max.Z), float)


def volume(shape: Shape | None) -> float:
    return 0.0 if shape is None or not shape.solids() else float(shape.volume)


def local_box(u: float, v: float, w: float, u0: float, v0: float, w0: float, label: str) -> Shape:
    shape = Box(u, v, w, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(u0, v0, w0)))
    shape.label = label
    return shape


def local_cylinder(diameter: float, z0: float, z1: float, label: str) -> Shape:
    shape = Cylinder(diameter / 2.0, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, z0)))
    shape.label = label
    return shape


def standard_core(*, gap_u: float = 0.20, gap_v: float = 0.22,
                  tip_d: float = PUSHER_TIP_D, stop_travel: float = T_HARD_STOP) -> dict[str, Shape]:
    """One standard core in local U/V/W coordinates, +W outward."""
    # A plus-shaped 1.20 mm seating cross leaves all four terminal quadrants open.
    base_u = local_box(9.60, 1.60, 1.20, 0, 0, -1.20, "OPEN_BASE_U_RAIL_1P20")
    base_v = local_box(1.60, 9.60, 1.20, 0, 0, -1.20, "OPEN_BASE_V_RAIL_1P20")
    base = base_u.fuse(base_v).clean(); base.label = "MAIN_BODY_BOTTOM_OPEN_CROSS_SEAT"

    # Three fixed cheeks; +U is intentionally open for switch insertion.
    u_neg = -(BODY_U / 2 + gap_u + 0.80)
    v_neg = -(BODY_V / 2 + gap_v + 0.80)
    v_pos = +(BODY_V / 2 + gap_v + 0.80)
    cheeks = [
        local_box(1.60, 1.80, 3.00, u_neg, 0, 0, "NEG_U_CONTROLLED_LOCATOR_CHEEK"),
        local_box(1.80, 1.60, 3.00, 0, v_neg, 0, "NEG_V_CONTROLLED_LOCATOR_CHEEK"),
        local_box(1.80, 1.60, 3.00, 0, v_pos, 0, "POS_V_CLEARANCE_CHEEK"),
    ]
    fixed = base
    for cheek in cheeks:
        fixed = fixed.fuse(cheek)

    # Broad removable keeper closes +U only at V=0, between the four terminal exits.
    keeper_u = BODY_U / 2 + 0.35 + 0.80
    keeper = local_box(1.60, 2.40, 2.60, keeper_u, 0, 0.20, "BROAD_POS_U_SERVICE_KEEPER")

    # Guide is fully inside the 8 mm opening: 0.30 mm nominal radial opening clearance.
    guide_outer = local_cylinder(GUIDE_OD, 5.75, 7.05, "STANDARD_GUIDE_OUTER_D7P40")
    bore = local_cylinder(GUIDE_BORE_D, 5.65, 7.15, "PUSHER_BORE_D4P40")
    cavity_bottom = 6.25 - stop_travel
    cavity = local_cylinder(GUIDE_CAVITY_D, cavity_bottom, 6.75, "PUSHER_SHOULDER_CAVITY_D5P00")
    guide = (guide_outer - bore - cavity).clean(); guide.label = "HARNESS_GUIDE_RETENTION_HARD_STOP"

    # Three 1.60 mm diagonal ribs connect the lower locator frame to the guide.
    rib_specs = [(u_neg, 0.0), (0.0, v_neg), (0.0, v_pos)]
    ribs = []
    for index, (u0, v0) in enumerate(rib_specs, 1):
        radial = np.asarray((u0, v0), float)
        radial /= np.linalg.norm(radial)
        p0 = (u0, v0, 2.70)
        p1 = (radial[0] * 3.45, radial[1] * 3.45, 5.90)
        ribs.append(oriented_box_between(p0, p1, (0, 0, 1), 1.60, 1.60, label=f"CORE_RIB_{index}_1P60"))
    core = fixed.fuse(guide)
    for rib in ribs:
        core = core.fuse(rib)
    core = core.clean(); core.label = "STANDARD_OPEN_FRAME_HARNESS_CORE"

    # Captured pusher: separate service part driven by the frozen cap underside.
    shaft = local_cylinder(PUSHER_SHAFT_D, 6.08, 7.20, "PUSHER_SHAFT_D4P00")
    tip = local_cylinder(tip_d, 6.08 - 0.14, 6.16, f"PUSHER_TIP_D{tip_d:.2f}")
    shoulder = local_cylinder(PUSHER_SHOULDER_D, 6.25, 6.65, "PUSHER_HARD_STOP_SHOULDER_D4P80")
    pusher = shaft.fuse(tip).fuse(shoulder).clean(); pusher.label = "CAP_DRIVEN_CAPTURED_PUSHER"

    body = local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "ITS1105_MEASURED_BODY")
    actuator = local_cylinder(ACT_D, BODY_H, TOTAL_H, "ITS1105_MEASURED_ACTUATOR")
    lug_parts = []
    for u0 in (-2.25, 2.25):
        for v0 in (-2.25, 2.25):
            lug = Cylinder(0.70, 0.80, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(u0, v0, BODY_H)))
            lug.label = "ACTUAL_CORNER_FEATURE_UNKNOWN_KEEP_OUT"
            lug_parts.append(lug)
    lugs = Compound(children=lug_parts, label="FOUR_CORNER_FEATURE_KEEP_OUTS_D1P40")

    hard_stop = local_cylinder(GUIDE_OD, cavity_bottom - 0.03, cavity_bottom + 0.03, "STRUCTURAL_STOP_PLANE")
    hard_stop = (hard_stop - local_cylinder(GUIDE_BORE_D, cavity_bottom - 0.10, cavity_bottom + 0.10, "x")).clean()
    return {"core": core, "keeper": keeper, "guide": guide, "pusher": pusher,
            "body": body, "actuator": actuator, "lugs": lugs, "hardStop": hard_stop,
            "cavityBottom": cavity_bottom}


def terminal_proxies() -> dict[str, Shape]:
    rows: dict[str, Shape] = {}
    for su, tag_u in ((-1, "N"), (1, "P")):
        for sv, tag_v in ((-1, "N"), (1, "P")):
            u0, u1 = su * 3.05, su * 4.10
            p0, p1 = (u0, sv * 2.25, -0.30), (u1, sv * 2.25, -1.80)
            shape = oriented_box_between(p0, p1, (0, 1, 0), 0.70, 0.50,
                                         label=f"T{tag_u}{tag_v}_OPEN_TERMINAL_PROXY")
            rows[f"T{tag_u}{tag_v}"] = shape
    return rows


def alignment_jig() -> Shape:
    flange = local_box(13.0, 13.0, 1.60, 0, 0, 8.45, "JIG_EXTERIOR_DEPTH_FLANGE")
    opening_key = local_box(7.72, 7.72, 1.60, 0, 0, 7.05, "JIG_OPENING_CENTER_KEY_7P72")
    pilot = local_cylinder(4.16, 5.60, 8.65, "JIG_AXIS_PILOT_D4P16")
    handle = local_cylinder(8.0, 10.05, 13.05, "JIG_REMOVAL_HANDLE")
    jig = flange.fuse(opening_key).fuse(pilot).fuse(handle).clean()
    jig.label = "TEMPORARY_OPENING_DATUM_ALIGNMENT_JIG"
    return jig


def datum_location(datum, front: float) -> Location:
    seat = point_at(datum, front + BODY_H)
    return Plane(origin=seat, x_dir=datum.switch_u, z_dir=datum.axis).location


def placed_local(shape: Shape, datum, front: float, label: str) -> Shape:
    result = datum_location(datum, front) * shape
    result.label = label
    return result


def ray_hits(triangles: np.ndarray, origin: np.ndarray, direction: np.ndarray) -> np.ndarray:
    e1 = triangles[:, 1] - triangles[:, 0]
    e2 = triangles[:, 2] - triangles[:, 0]
    p = np.cross(direction, e2)
    det = np.einsum("ij,ij->i", e1, p)
    valid = np.abs(det) > 1.0e-11
    inv = np.zeros(len(triangles)); inv[valid] = 1.0 / det[valid]
    tv = origin - triangles[:, 0]
    uu = np.einsum("ij,ij->i", tv, p) * inv
    q = np.cross(tv, e1)
    vv = np.einsum("j,ij->i", direction, q) * inv
    tt = np.einsum("ij,ij->i", e2, q) * inv
    mask = valid & (uu >= -1e-7) & (vv >= -1e-7) & (uu + vv <= 1 + 1e-7) & (tt >= 0)
    hits = np.sort(tt[mask])
    if not len(hits):
        return hits
    # Remove edge/coplanar duplicate intersections.
    keep = np.r_[True, np.diff(hits) > 0.02]
    return hits[keep]


def sample_inner_depth(shell: np.ndarray, datum, u0: float, v0: float) -> float | None:
    axis = unit(datum.axis); u = unit(datum.switch_u); v = unit(datum.switch_v)
    origin = np.asarray(datum.center, float) + u * u0 + v * v0
    hits = ray_hits(shell, origin, -axis)
    candidates = hits[(hits > 0.05) & (hits < 12.0)]
    return float(candidates[1]) if len(candidates) >= 2 else None


def patch_fit(shell: np.ndarray, datum, uc: float, vc: float,
              width: float = 3.0, height: float = 2.4) -> dict[str, object] | None:
    rows = []
    for vv in np.linspace(vc - height / 2, vc + height / 2, 5):
        for uu in np.linspace(uc - width / 2, uc + width / 2, 5):
            depth = sample_inner_depth(shell, datum, float(uu), float(vv))
            if depth is not None:
                rows.append((float(uu), float(vv), depth))
    if len(rows) < 18:
        return None
    array = np.asarray(rows, float)
    design = np.c_[np.ones(len(array)), array[:, :2]]
    keep = np.ones(len(array), bool)
    coef = np.linalg.lstsq(design, array[:, 2], rcond=None)[0]
    for _ in range(3):
        residual = array[:, 2] - design @ coef
        median = float(np.median(residual))
        keep = np.abs(residual - median) <= 0.60
        if int(keep.sum()) < 16:
            break
        coef = np.linalg.lstsq(design[keep], array[keep, 2], rcond=None)[0]
    if int(keep.sum()) < 16:
        return None
    residual = array[:, 2] - design @ coef
    q05, q95 = np.quantile(residual[keep], [0.05, 0.95])
    score = float(q95 - q05 + 0.04 * (25 - len(array)) + 0.02 * (25 - keep.sum()))
    return {"centerUV": [uc, vc], "widthMm": width, "heightMm": height,
            "samples": array, "fit": coef, "inliers": keep,
            "residualP05P95Mm": [float(q05), float(q95)], "score": score}


def seam_ok(datum, uc: float, vc: float, width=3.0, height=2.4) -> bool:
    u = unit(datum.switch_u); v = unit(datum.switch_v); center = np.asarray(datum.center, float)
    corners = np.asarray([center + u * (uc + su * width / 2) + v * (vc + sv * height / 2)
                          for su in (-1, 1) for sv in (-1, 1)])
    if datum.owner == "JfD":
        return bool(corners[:, 0].max() <= -0.20)
    return bool(corners[:, 0].min() >= 0.20)


def select_patches(shell: np.ndarray, datum) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    # Start with broad patches on a coarse grid, then search a finer grid with
    # a still-FDM-practical patch.  The fine pass is important on the strongly
    # curved I2/I4 walls, where a 3 mm sampling stride can jump over a stable
    # inner-surface region.  N2 deliberately remains allowed to return only one
    # patch: inventing two more across its seam would be less honest than a
    # position-specific HOLD verdict.
    for uc in (-6.0, -3.0, 0.0, 3.0, 6.0):
        for vc in (-6.0, -3.0, 0.0, 3.0, 6.0):
            if max(abs(uc), abs(vc)) < 4.0 or not seam_ok(datum, uc, vc):
                continue
            row = patch_fit(shell, datum, uc, vc)
            if row is not None:
                candidates.append(row)
    for uc in range(-10, 11):
        for vc in range(-10, 11):
            if max(abs(uc), abs(vc)) < 3.0 or not seam_ok(datum, float(uc), float(vc), 2.4, 1.8):
                continue
            row = patch_fit(shell, datum, float(uc), float(vc), 2.4, 1.8)
            if row is not None:
                candidates.append(row)
    candidates.sort(key=lambda row: (float(row["score"]) + 0.04 * (7.20 - float(row["widthMm"]) * float(row["heightMm"])),
                                      abs(row["centerUV"][0]) + abs(row["centerUV"][1])))
    selected: list[dict[str, object]] = []
    for row in candidates:
        c = np.asarray(row["centerUV"], float)
        if all(float(np.linalg.norm(c - np.asarray(old["centerUV"], float))) >= 3.2 for old in selected):
            selected.append(row)
        if len(selected) == 3:
            break
    return selected


def foot_solid(shell: np.ndarray, datum, front: float, patch: dict[str, object], index: int) -> tuple[Shape, dict[str, object]]:
    uc, vc = patch["centerUV"]
    width, height = float(patch["widthMm"]), float(patch["heightMm"])
    fit = np.asarray(patch["fit"], float)
    seat_depth = front + BODY_H
    us = np.linspace(uc - width / 2, uc + width / 2, 5)
    vs = np.linspace(vc - height / 2, vc + height / 2, 5)
    top = np.zeros((len(vs), len(us), 3), float)
    used_actual = 0
    for j, vv in enumerate(vs):
        for i, uu in enumerate(us):
            predicted = float(fit @ np.asarray((1.0, uu, vv)))
            actual = sample_inner_depth(shell, datum, float(uu), float(vv))
            if actual is not None and abs(actual - predicted) <= 0.60:
                depth = actual; used_actual += 1
            else:
                depth = predicted
            top[j, i] = (uu, vv, seat_depth - depth - BONDLINE)
    bottom = top.copy(); bottom[:, :, 2] -= FOOT_THICKNESS
    triangles = []
    for j in range(len(vs) - 1):
        for i in range(len(us) - 1):
            a, b, c, d = top[j, i], top[j, i + 1], top[j + 1, i + 1], top[j + 1, i]
            triangles.extend(((a, b, c), (a, c, d)))
            aa, bb, cc, dd = bottom[j, i], bottom[j, i + 1], bottom[j + 1, i + 1], bottom[j + 1, i]
            triangles.extend(((aa, cc, bb), (aa, dd, cc)))
    # Four closed side strips.
    loops = [
        [(0, i) for i in range(len(us))],
        [(len(vs)-1, i) for i in range(len(us)-1, -1, -1)],
        [(j, 0) for j in range(len(vs)-1, -1, -1)],
        [(j, len(us)-1) for j in range(len(vs))],
    ]
    for loop in loops:
        for (j0, i0), (j1, i1) in zip(loop[:-1], loop[1:]):
            a, b = top[j0, i0], top[j1, i1]
            aa, bb = bottom[j0, i0], bottom[j1, i1]
            triangles.extend(((a, aa, bb), (a, bb, b)))
    tri = np.asarray(triangles, float)
    solid = mesh_to_faceted_solid(tri)
    solid.label = f"{datum.name}_CONFORMAL_GLUE_FOOT_{index}"
    contact_tri = np.asarray([row for k, row in enumerate(tri) if k % 4 in (0, 1)], float)[:32]
    # Normal distribution from the actual top grid triangles.
    top_tri = []
    for j in range(4):
        for i in range(4):
            a, b, c, d = top[j, i], top[j, i+1], top[j+1, i+1], top[j+1, i]
            top_tri.extend(((a, b, c), (a, c, d)))
    top_tri = np.asarray(top_tri, float)
    normals = np.cross(top_tri[:, 1] - top_tri[:, 0], top_tri[:, 2] - top_tri[:, 0])
    areas = np.linalg.norm(normals, axis=1) / 2
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
    nz = np.abs(normals[:, 2])
    metrics = {
        "centerUVmm": [float(uc), float(vc)], "planarAreaMm2": width * height,
        "contactSurfaceAreaMm2": float(areas.sum()), "bondlineNominalMm": BONDLINE,
        "bondlineAuditRangeMm": [0.20, 0.50], "actualGridSamplesUsed": used_actual,
        "fitResidualP05P95Mm": patch["residualP05P95Mm"],
        "surfaceNormalFromWMinMaxDeg": [float(np.degrees(np.arccos(np.clip(nz.max(), 0, 1)))),
                                         float(np.degrees(np.arccos(np.clip(nz.min(), 0, 1))))],
        "pressCompressionFractionAreaWeighted": float(np.average(nz, weights=areas)),
        "pressShearFractionAreaWeighted": float(np.average(np.sqrt(np.maximum(0, 1-nz*nz)), weights=areas)),
        "pressPeelFraction": 0.0,
    }
    return solid, metrics


def feet_and_wings(shell: np.ndarray, datum, front: float, core: Shape) -> tuple[list[Shape], list[Shape], dict[str, object]]:
    patches = select_patches(shell, datum)
    feet: list[Shape] = []
    wings: list[Shape] = []
    metrics = []
    for index, patch in enumerate(patches, 1):
        foot, row = foot_solid(shell, datum, front, patch, index)
        feet.append(foot); metrics.append(row)
        uc, vc = patch["centerUV"]
        radial = np.asarray((uc, vc), float); radial /= np.linalg.norm(radial)
        foot_center = np.asarray((uc, vc, np.mean([v.center().Z for v in foot.vertices()])), float)
        p0 = np.asarray((radial[0] * 3.45, radial[1] * 3.45, 5.85), float)
        p1 = foot_center.copy(); p1[2] -= FOOT_THICKNESS * 0.45
        direction = p1 - p0; direction /= np.linalg.norm(direction)
        wing = oriented_box_between(tuple(p0 - direction * 0.35), tuple(p1 + direction * 0.35),
                                    (0, 0, 1), 1.60, 1.60,
                                    label=f"{datum.name}_BROAD_GLUE_WING_{index}_1P60")
        wings.append(wing)
    attach = []
    for wing in wings:
        attach.append(float(wing.distance_to(core)))
    for wing, foot in zip(wings, feet):
        attach.append(float(wing.distance_to(foot)))
    total_area = sum(float(row["contactSurfaceAreaMm2"]) for row in metrics)
    return feet, wings, {
        "patchCount": len(feet), "feet": metrics, "totalGlueContactAreaMm2": total_area,
        "minimumAttachmentDistanceMm": min(attach, default=999.0),
        "maximumAttachmentDistanceMm": max(attach, default=999.0),
        "floatingOrTangentOnly": (not feet or max(attach, default=999.0) > 1e-5),
        "bondlineParameterMm": [0.20, 0.30, 0.50],
        "glueKeepOut": "central 8 x 8 guide/switch/terminal prism + all T1-T4 solder cones",
    }


def terminal_access(core: Shape, keeper: Shape) -> dict[str, object]:
    rows = {}
    for name, terminal in terminal_proxies().items():
        common = terminal & core
        pen = volume(common)
        common_keeper = terminal & keeper
        pen += volume(common_keeper)
        rows[name] = {"penetrationMm3": pen, "open": pen <= 1e-6,
                      "solderIronAccess": "OPEN U-SIDE / V-separated from mid-side cheeks"}
    return {"terminals": rows, "allOpen": all(row["open"] for row in rows.values())}


def overlap_aabb(left: Shape, right: Shape) -> tuple[float, float]:
    la, ua = bounds(left); lb, ub = bounds(right)
    gaps = np.maximum(0.0, np.maximum(la - ub, lb - ua))
    overlap = np.maximum(0.0, np.minimum(ua, ub) - np.maximum(la, lb))
    return float(np.linalg.norm(gaps)), float(np.prod(overlap))


def virtual_rows(datums: dict[str, object], shells: dict[str, np.ndarray], local: dict[str, Shape]) -> tuple[dict[str, object], dict[str, dict[str, Shape]]]:
    rows: dict[str, object] = {}
    shapes: dict[str, dict[str, Shape]] = {}
    for name in BUTTONS:
        datum = datums[name]; front = float(FROZEN_FRONT_DEPTHS[name])
        feet, wings, glue = feet_and_wings(shells[datum.owner], datum, front, local["core"])
        core_world = placed_local(local["core"], datum, front, f"{name}_STANDARD_CORE")
        keeper_world = placed_local(local["keeper"], datum, front, f"{name}_SERVICE_KEEPER")
        pusher_world = placed_local(local["pusher"], datum, front, f"{name}_PUSHER")
        foot_world = [placed_local(foot, datum, front, f"{name}_FOOT_{i}") for i, foot in enumerate(feet, 1)]
        wing_world = [placed_local(wing, datum, front, f"{name}_WING_{i}") for i, wing in enumerate(wings, 1)]
        compound = Compound(children=[core_world, keeper_world, *foot_world, *wing_world], label=f"{name}_VIRTUAL_HARNESS")
        axis = unit(datum.axis)
        rear_projection = front + BODY_H + 1.20
        seam_distance = abs(float(datum.center[0]))
        seam = "HIGH" if name in ("N1", "N2") else ("MEDIUM" if seam_distance < 7.0 else "LOW")
        rows[name] = {
            "coreType": "STANDARD OPEN FRAME V1",
            "footType": f"{len(feet)}-PATCH SHELL-DERIVED FACETED CONFORMAL FOOT",
            "glueAreaMm2": glue["totalGlueContactAreaMm2"],
            "axis": list(map(float, axis)), "rearProjectionDepthMm": rear_projection,
            "rearProjectionReductionVs9p96Mm": (9.96 - rear_projection) if name in ("N1", "N2") else None,
            "terminalAccess": TRIM_DECISIONS[name], "wireExit": "±U SIDE / four terminal quadrants open",
            "seamSensitivity": seam, "assemblyJigAccess": "YES / opening pilot D4.16 + 7.72 key",
            "glue": glue, "verdict": "LOCAL FOOT VALIDATION REQUIRED" if len(feet) >= 2 else "HOLD / FOOT PATCH INSUFFICIENT",
        }
        shapes[name] = {"compound": compound, "core": core_world, "keeper": keeper_world,
                        "pusher": pusher_world, "feet": Compound(children=foot_world, label=f"{name}_FEET"),
                        "wings": Compound(children=wing_world, label=f"{name}_WINGS")}
        gc.collect()
    # Candidate-to-candidate neighbor screen.
    neighbor = {}
    names = list(BUTTONS)
    for i, left in enumerate(names):
        for right in names[i+1:]:
            gap, aabb_overlap = overlap_aabb(shapes[left]["compound"], shapes[right]["compound"])
            neighbor[f"{left}-{right}"] = {"aabbGapMm": gap, "aabbOverlapProxyMm3": aabb_overlap,
                                           "status": "REVIEW" if aabb_overlap > 0 else "CLEAR"}
    for name in BUTTONS:
        related = [row for pair, row in neighbor.items() if name in pair.split("-")]
        rows[name]["neighborClearanceMm"] = min((row["aabbGapMm"] for row in related), default=999.0)
        if any(row["status"] == "REVIEW" for row in related):
            rows[name]["verdict"] = "LOCAL FOOT/WING VARIANT REQUIRED"
    return {"buttons": rows, "neighborPairs": neighbor}, shapes


def coupon_v2() -> Shape:
    variants = [
        (0.12, 0.14, 2.40, 0.34),
        (0.20, 0.22, 2.60, 0.38),
        (0.32, 0.35, 2.80, 0.42),
    ]
    children: list[Shape] = []
    for i, (gu, gv, tip, stop) in enumerate(variants):
        parts = standard_core(gap_u=gu, gap_v=gv, tip_d=tip, stop_travel=stop)
        shift = Location(Vector(i * 17.0, 0, 2.0))
        for key in ("core", "keeper", "pusher"):
            shape = parts[key].moved(shift); shape.label = f"COUPON_{i+1}_{key.upper()}_GU{gu:.2f}_GV{gv:.2f}_TIP{tip:.2f}_STOP{stop:.2f}"
            children.append(shape)
        body = parts["body"].moved(shift); body.label = f"COUPON_{i+1}_ITS_INSERTION_REFERENCE"; children.append(body)
    # Shell-like curved glue strip and a 0.30 mm separated mating foot.
    outer = Cylinder(22.0, 3.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    inner = Cylinder(18.0, 3.2, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, -0.1)))
    crop = local_box(8, 12, 3.4, 20, 0, -0.2, "GLUE_CURVE_CROP")
    shell_like = ((outer - inner) & crop).clean().moved(Location(Vector(-3, 22, 0)))
    shell_like.label = "SHELL_LIKE_CURVED_GLUE_TEST_SURFACE"
    children.append(shell_like)
    # Opening plate + jig repetition test.
    plate = local_box(14, 14, 2.0, 48, 22, 0, "JIG_REPEATABILITY_OPENING_PLATE")
    opening = local_box(8.0, 8.0, 3.0, 48, 22, -0.5, "JIG_8MM_OPENING_TOOL")
    plate = (plate - opening).clean(); children.append(plate)
    jig = alignment_jig().moved(Location(Vector(48, 22, -7.05))); jig.label = "COUPON_ALIGNMENT_JIG"; children.append(jig)
    return Compound(children=children, label="OPEN_FRAME_HARNESS_FDM_COUPON_V2")


def near_mesh(triangles: np.ndarray, center: Iterable[float], radius: float) -> np.ndarray:
    d = np.linalg.norm(triangles - np.asarray(tuple(center), float), axis=2)
    return triangles[(d <= radius).all(axis=1)]


def mesh_near_points(triangles: np.ndarray, points: np.ndarray, radius: float) -> np.ndarray:
    if not len(triangles) or not len(points):
        return np.empty((0, 3, 3), float)
    distance, _ = cKDTree(np.asarray(points, float).reshape(-1, 3)).query(np.mean(triangles, axis=1), k=1)
    return triangles[distance <= radius]


def triangle_wireframes(triangles: np.ndarray, maximum: int = 160) -> list[np.ndarray]:
    if not len(triangles):
        return []
    stride = max(1, int(math.ceil(len(triangles) / maximum)))
    return [np.vstack((triangle, triangle[0])) for triangle in triangles[::stride]]


def clip_half_shape(shape: Shape) -> np.ndarray:
    tool = Box(100, 50, 100, align=(Align.CENTER, Align.MAX, Align.CENTER))
    cut = (shape & tool).clean()
    return safe_triangles(cut) if cut.solids() else np.empty((0, 3, 3))


def render_outputs(local: dict[str, Shape], rep_shapes: dict[str, Shape], all_shapes: dict[str, dict[str, Shape]],
                   datums: dict[str, object], shells: dict[str, np.ndarray], coupon: Shape) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    def render(name, objects, title, subtitle, camera=(24, -32, 20), fit=None, transparent=None, wireframes=None):
        path = RENDER / name
        raster_scene(path, objects, title, subtitle, FOOTER, camera_offset=camera, fit_points=fit,
                     transparent_objects=transparent or [], wireframes=wireframes or [])
        outputs.append(relative(path))

    core_t = safe_triangles(local["core"]); keeper_t = safe_triangles(local["keeper"])
    pusher_t = safe_triangles(local["pusher"]); body_t = safe_triangles(local["body"]); actuator_t = safe_triangles(local["actuator"])
    lugs_t = safe_triangles(local["lugs"])
    render("01_open_frame_harness_isolated.png", [(core_t, C["core"]), (keeper_t, C["foot"]), (pusher_t, C["pusher"])],
           "1 / STANDARD OPEN-FRAME HARNESS CORE", "one common core | +U service keeper | no closed switch box", fit=core_t.reshape(-1, 3))
    render("02_its_inserted_in_harness.png", [(core_t, C["core"]), (keeper_t, C["foot"]), (pusher_t, C["pusher"]),
                                                (body_t, C["switch"]), (actuator_t, C["switch"])],
           "2 / ACTUAL ITS ENVELOPE INSERTED", "6.12 x 6.05 body | +U insertion before broad keeper | all terminal quadrants open")
    render("03_bottom_seating_closeup.png", [(clip_half_shape(local["core"]), C["core"]), (clip_half_shape(local["body"]), C["switch"])],
           "3 / MAIN-BODY BOTTOM SEATING", "1.20 mm plus-cross support | broad compression path | no full bottom plate", camera=(18, -24, 5))
    render("04_corner_feature_clearance.png", [(core_t, C["core"]), (body_t, C["switch"]), (lugs_t, C["glue"])],
           "4 / CORNER-FEATURE FREE CLEARANCE", "orange D1.40 x 0.80 UNKNOWN keep-outs | no clamping or precision location")
    term_objs = [(core_t, C["core"]), (keeper_t, C["foot"]), (body_t, C["switch"])]
    term_objs += [(safe_triangles(t), C["terminal"]) for t in terminal_proxies().values()]
    render("05_open_terminal_access.png", term_objs, "5 / T1–T4 TERMINAL + SOLDER ACCESS",
           "four U-side terminal corridors remain open; keeper lies between V-separated terminal pairs", camera=(18, -30, -10))
    render("06_pusher_actuator_section.png", [(clip_half_shape(local["core"]), C["guide"]),
                                               (clip_half_shape(local["pusher"]), C["pusher"]),
                                               (clip_half_shape(local["body"]), C["switch"]),
                                               (clip_half_shape(local["actuator"]), C["switch"])],
           "6 / PUSHER → ACTUATOR SECTION", "D2.60 tip | D4.00 shaft | 0.08 nominal gap | centered W stack", camera=(17, -26, 7))
    render("07_hard_stop_section.png", [(clip_half_shape(local["core"]), C["guide"]),
                                         (clip_half_shape(local["pusher"]), C["pusher"]),
                                         (clip_half_shape(local["hardStop"]), C["stop"])],
           "7 / HARNESS-INTERNAL STRUCTURAL HARD STOP", "D4.80 shoulder → guide cavity floor | T_HARD_STOP=0.38 provisional", camera=(16, -24, 7))

    feet_t = safe_triangles(rep_shapes["feet"]); wings_t = safe_triangles(rep_shapes["wings"])
    rep_foot_count = len(rep_shapes["feet"].solids())
    render("08_glue_wings_isolated.png", [(feet_t, C["foot"]), (wings_t, C["glue"])],
           "8 / I2 SHELL-DERIVED FEET + 1.60 mm WINGS",
           f"{rep_foot_count} position-specific bond patches | bondline parameter 0.20/0.30/0.50")

    rep = datums[REPRESENTATIVE]; shell_local = near_mesh(shells[rep.owner], rep.center, 15.0)
    shell_contact = mesh_near_points(shell_local, feet_t.reshape(-1, 3), 3.5)
    shell_wire = [(triangle_wireframes(shell_local), (*C["shell"], 90))]
    shell_contact_wire = [(triangle_wireframes(shell_contact, 120), (*C["shell"], 105))]
    render("09_conformal_foot_on_shell_inner_surface.png",
           [(shell_contact, C["shell"]), (feet_t, C["foot"]), (wings_t, C["glue"])],
           "9 / I2 CONFORMAL FEET ON FROZEN JfD INNER SURFACE", "local contact patches + shell wireframe; nominal 0.30 mm adhesive bondline",
           camera=(70, -95, 58), wireframes=shell_contact_wire)
    jig_world = rep_shapes["jig"]
    render("10_alignment_jig_installed.png", [(safe_triangles(jig_world), C["jig"]),
                                               (safe_triangles(rep_shapes["core"]), C["core"])],
           "10 / OPENING-DATUM ALIGNMENT JIG INSTALLED", "7.72 square key + D4.16 axis pilot + exterior depth flange; shell shown as wireframe", camera=(70, -95, 58),
           wireframes=shell_wire)
    render("11_jig_shell_harness_section.png", [(safe_triangles(jig_world), C["jig"]),
                                                 (safe_triangles(rep_shapes["compound"]), C["core"])],
           "11 / JIG + SHELL + HARNESS SECTION", "jig fixes center / W axis / depth / roll; local shell wireframe retained", camera=(64, -100, 20),
           wireframes=shell_wire)

    # Load path arrows are cylinders along the representative W axis.
    arrows = []
    for depth0, length, col in ((-1.0, 3.0, C["pusher"]), (2.0, 3.0, C["axis"]), (5.0, 3.0, C["glue"])):
        origin = np.asarray(point_at(rep, depth0), float)
        axis_shape = Plane(origin=origin, z_dir=tuple(-unit(rep.axis))).location * Cylinder(0.45, length, align=(Align.CENTER, Align.CENTER, Align.MIN))
        arrows.append((safe_triangles(axis_shape), col))
    render("12_glue_load_path_visualization.png", [(safe_triangles(rep_shapes["compound"]), C["core"]), *arrows],
           "12 / PRESS LOAD PATH INTO GLUE FEET", "cap → pusher → switch → open seat → wings → shell; press is compression/shear, not peel",
           camera=(52, -78, 38))
    render("13_representative_harness_in_shell.png", [(safe_triangles(rep_shapes["compound"]), C["core"]),
                                                       (safe_triangles(rep_shapes["pusher"]), C["pusher"])],
           "13 / REPRESENTATIVE I2 HARNESS IN SHELL", "standard core + I2-only feet; frozen shell wireframe unchanged", camera=(70, -100, 55),
           wireframes=shell_wire)
    all_objs = [(safe_triangles(all_shapes[name]["compound"]), C["core"]) for name in BUTTONS]
    render("14_all8_virtual_harness_placement.png", all_objs, "14 / ALL-EIGHT VIRTUAL HARNESS PLACEMENT",
           "same core at N1 N2 I2 I3 I4 M3 M4 N3 | only glue feet + transforms vary", camera=(90, -135, 95))

    # N1/N2 with the existing LOW-confidence SZH web reference.
    szh_compound, _, _, _ = build_szh_reference(); loc, _ = szh_placement()
    szh_world = loc * szh_compound
    n_objs = [(safe_triangles(all_shapes[n]["compound"]), C["core"]) for n in ("N1", "N2")]
    n_objs.append((safe_triangles(szh_world), C["szh"]))
    render("15_n1_n2_thumb_szh_closeup.png", n_objs, "15 / N1/N2 NEAR THUMB / SZH REGION",
           "open rear frame removes bulky chamber; SZH web reference remains LOW-confidence", camera=(90, -130, 80),
           transparent=[(safe_triangles(szh_world), (*C["szh"], 95))])
    split = Box(0.20, 80, 80, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    render("16_jad_jfd_split_relationship.png", all_objs + [(safe_triangles(split), C["stop"])],
           "16 / JaD/JfD SPLIT RELATIONSHIP", "feet constrained to one owner half; N2 core still seam-sensitive and needs a local cure trial",
           camera=(95, -135, 90), transparent=[(safe_triangles(split), (*C["stop"], 75))])
    render("17_coupon_v2_preview.png", [(safe_triangles(coupon), C["core"])],
           "17 / OPEN_FRAME_HARNESS_FDM_COUPON V2", "3 clearance/pusher/stop stations + curved glue surface + jig repetition opening",
           camera=(95, -105, 70))
    return outputs


def report_text(data: dict[str, object]) -> str:
    rows = []
    for name in BUTTONS:
        r = data["virtualFit"]["buttons"][name]
        axis = ", ".join(f"{x:+.3f}" for x in r["axis"])
        rows.append(f"| {name} | STANDARD V1 | {r['footType']} | {r['glueAreaMm2']:.2f} | `{axis}` | "
                    f"{r['rearProjectionDepthMm']:.2f} | {r['terminalAccess']} | {r['wireExit']} | "
                    f"{r['neighborClearanceMm']:.2f} | {r['seamSensitivity']} | {r['assemblyJigAccess']} | **{r['verdict']}** |")
    renders = "\n".join(f"- [{Path(p).name}](../{p})" for p in data["outputs"]["renders"])
    rep_fit = data["virtualFit"]["buttons"][REPRESENTATIVE]
    rep_foot_count = int(rep_fit["glue"]["patchCount"])
    rep_rear_depth = float(rep_fit["rearProjectionDepthMm"])
    return f"""# 77 — Open-frame glued switch harness candidate

RECOMMENDED ARCHITECTURE
= **STANDARD OPEN-FRAME ITS HARNESS + POSITION-SPECIFIC CONFORMAL GLUE FEET + OPENING-DATUM JIG**

STANDARD CORE FEASIBLE
= **CONDITIONAL — common mechanical core works; +U broad service keeper and physical retention test remain**

CONFORMAL GLUE FOOT
= **REVISE — shell-derived candidate exists, but adhesive/cure coupon is required at every foot family**

ALIGNMENT JIG
= **PASS AS AUDIT GEOMETRY — center, axis, depth and roll are mechanically constrained**

SWITCH LOCATING
= **MAIN-BODY BOTTOM OPEN CROSS + −U/−V CONTROLLED CHEEKS + +V CLEARANCE CHEEK + BROAD +U KEEPER**

PUSHER
= **D2.60 TIP / D4.00 SHAFT / D4.80 SHOULDER / 0.08 GAP — PARAMETRIC, COUPON REQUIRED**

HARD STOP
= **HARNESS GUIDE SHOULDER, T_HARD_STOP=0.38 mm PROVISIONAL**

GLUE LOAD PATH
= **PRESS LOAD PRIMARILY COMPRESSION/SHEAR; PEEL DURING USER PRESS=0 BY CONSTRUCTION**

8-POSITION VIRTUAL FIT
= **CONDITIONAL — same core places at all eight; some feet/wings require local variants**

N1/N2 PACKAGING
= **IMPROVED REAR VOLUME; N2 SEAM CURE/CLOSURE TRIAL REQUIRED**

FDM
= **CONDITIONAL — all structural members ≥1.20 mm, preferred ribs/keeper/feet 1.60 mm; V2 coupon required**

SHELL SPLIT
= **PRESERVED**

EXTERIOR
= **PRESERVED**

PRODUCTION MODIFICATION
= **0**

## 1. Final verdict

**B. OPEN-FRAME HARNESS WORKS, BUT SOME POSITIONS NEED LOCAL VARIANTS.**

형님의 스케치처럼 switch 주위를 큰 상자로 막지 않고, rear cross-seat·세 개의 local cheek·세 개의
상부 rib·개구부 안쪽 원형 guide만 남겼다. 동일 core를 8개 W축에 놓을 수 있으며, 달라지는 것은
shell-derived foot와 wing 경로다. 다만 접착제/실물 ITS/경화 jig를 아직 물리 검증하지 않았으므로
`A preferred → production`으로 바로 승격하지 않는다.

## 2. Representative choice and architecture

대표는 **I2**다. N1/N2의 seam·Thumb 특수성에 치우치지 않으면서 실제 JfD 곡면, shared-carrier
각도, 네 terminal을 모두 대표한다.

```text
frozen 8 mm opening / cap
→ captured local pusher
→ D7.40 guide + internal shoulder stop
→ actual ITS actuator/body
→ 1.20 mm open cross seating datum
→ 1.60 mm ribs/wings
→ {rep_foot_count} shell-derived conformal feet
→ 0.20 / 0.30 / 0.50 mm adhesive bondline
→ frozen shell inner surface
```

- closed 6.4 pocket: 없음
- full bottom plate: 없음
- tiny snap/hook: 없음
- terminal quadrant closure: 없음
- +U insertion: broad keeper를 빼고 side insertion, keeper 설치 후 cure
- corner features: D1.40×0.80 UNKNOWN keep-out만 적용, locating/clamping 0

## 3. Standard core details

| item | value |
|---|---:|
| measured body authority | 6.12 × 6.05 × 3.56 mm |
| guide OD / opening | 7.40 / 8.00 mm |
| opening radial nominal clearance | 0.30 mm/side |
| guide bore / pusher shaft | 4.40 / 4.00 mm |
| structural guide radial wall | 1.20 mm |
| seat/rib/keeper/foot thickness | 1.20 / 1.60 / 1.60 / 1.60 mm |
| representative I2 rear depth | {rep_rear_depth:.2f} mm from frozen exterior datum |
| N1/N2 rear depth | 9.56 mm from frozen exterior datum |
| N1/N2 reduction vs current 9.96 | 0.40 mm |
| core material volume | {data['standardCore']['coreVolumeMm3']:.2f} mm³ |
| current closed-pocket candidate material | {data['architectureComparison']['closedPocketMaterialMm3']:.2f} mm³ |

Core는 switch main-body bottom을 plus-shaped cross로 받는다. 네 terminal은 V=±2.25 side corridor로
빠지고 cross는 U/V 중앙선에만 있어 solder iron과 wire departure를 막지 않는다. +U keeper도 두
terminal 사이 V=0에만 위치한다.

## 4. Pusher and simultaneous stack solver

| parameter | audit value | status |
|---|---:|---|
| REST_GAP | 0.08 | coupon variants required |
| T_CLICK | 0.33 cap travel | inferred from 0.08 + nominal 0.25 |
| T_DESIGN_FULL | 0.38 | provisional |
| T_HARD_STOP | 0.38 | provisional |
| actuator compression at stop | 0.30 | below recorded 0.35 upper bound, not a final spec |

```text
FIXED cap pose + W axis
+ measured body/actuator
+ body-bottom seat
+ pusher gap/diameter
+ captured shoulder cavity
+ structural stop
→ solve REST / CLICK / FULL together
→ then verify shell opening + foot + FDM
```

Shell-clearance-first `choose_front_depths()`는 packaging check로만 남고 pusher/travel authority가 아니다.

## 5. Glue feet and bondline

I2 및 나머지 위치에서 owner shell mesh를 local U/V ray로 표본화하고, local inner surface를 따라가는
faceted foot를 생성했다. 각 foot는 nominal 0.30 mm bondline만큼 안쪽에 있고 두께 1.60 mm다.
foot가 seam 반대 half로 넘어가는 candidate는 선택 단계에서 제외했다.

- bondline parameter: **0.20 / 0.30 / 0.50 mm**
- glue keep-out: central 8×8 guide/switch column + T1–T4 solder cones
- press force: shell normal 방향 성분은 compression, tangent 성분은 shear로 전달
- user press의 intentional peel: **0**
- cure shrink, shell flex, removal peel: **physical coupon gate**

CAD zero gap을 접착 PASS로 쓰지 않았다. 표면 표본/foot tessellation은 candidate이고, production에서는
chosen adhesive의 최소/최대 bondline, primer, cure fixture, shell material compatibility를 다시 잠가야 한다.

## 6. Alignment jig

Jig는 exterior opening을 datum으로 사용한다.

- 7.72 mm square key: opening center + roll
- D4.16 pilot: pusher/guide W axis
- 13 mm flange: exterior depth
- long exterior handle: cure 후 outward removal

따라서 조립자가 shell 안쪽에서 눈대중으로 center/angle/depth를 맞추지 않는다. 실제 반복정밀도는
V2 coupon의 opening plate에서 10회 설치/제거 후 측정한다.

## 7. Per-position virtual fit

| button | CORE TYPE | FOOT TYPE | GLUE AREA mm² | AXIS | REAR PROJECTION | TERMINAL ACCESS | WIRE EXIT | NEIGHBOR CLEARANCE | SEAM | JIG | VERDICT |
|---|---|---|---:|---|---:|---|---|---:|---|---|---|
{chr(10).join(rows)}

`AABB overlap proxy`가 있는 pair는 production collision 판정이 아니라 **wing/foot route local variant**
표시다. Core 중심/axis를 움직이지 않고 해당 foot 또는 wing만 다시 route해야 한다.

## 8. N1/N2 and shell split

N1/N2 rear depth는 9.56 mm로 current carrier 9.96보다 0.40 mm 줄었다. 폐쇄 rear wall과 wiring chamber가
없어 terminal은 ±U side departure가 가능하다. 그러나 N2는 center가 split에 놓이므로 core는 기하학상
양 half 공간을 통과한다. Feet는 JfD 한쪽에만 제한했지만 **shell closure가 core를 밀지 않는지 cure
trial이 필수**다. Split 삭제/bridge는 제안하지 않았다.

SZH render의 보라색 모델은 기존 LOW-confidence web reference다. 0.5 mm 이하 판정에는 쓰지 않는다.

## 9. Architecture comparison

| criterion | closed / large pocket | bulky cartridge | open-frame glued harness |
|---|---|---|---|
| material / envelope | medium / closed walls | highest | **lowest material, open quadrants** |
| rear projection | current N1/N2 9.96 class | ≥9.96, often longer | **N1/N2 9.56; position follows frozen front depth** |
| switch locating | all-wall tolerance sensitive | deterministic | 3 cheeks + keeper, conditional |
| FDM repeatability | shell angle coupled | separately printable | **same core, best orientation** |
| terminal/wire access | restricted | chamber dependent | **four open corridors** |
| serviceability | pocket extraction | cartridge removal | keeper removal; adhesive foot is destructive |
| assembly complexity | low/medium | medium | **highest: adhesive + jig + cure** |
| alignment sensitivity | shell CAD | cartridge datum | jig-controlled but bondline-sensitive |
| shell modification | possible pocket | mounts required | **0 / broad adhesive feet** |
| adhesive dependence | none/low | none/low | **primary dependency** |

따라서 packaging/FDM/terminal 면에서는 open frame가 우세하지만 assembly와 adhesive durability 때문에
물리 coupon 전에는 **B**가 맞다.

## 10. OPEN_FRAME_HARNESS_FDM_COUPON_V2

V1 `BUTTON_FDM_TEST_COUPON`은 그대로 보존했다. V2는 세 station을 포함한다.

| station | U/V locating gap | tip | hard stop |
|---|---|---|---|
| 1 | 0.12 / 0.14 | D2.40 | 0.34 |
| 2 | 0.20 / 0.22 | D2.60 | 0.38 |
| 3 | 0.32 / 0.35 | D2.80 | 0.42 |

검사항목: actual insertion, bottom seating, side clearance, corner keep-out, pusher, REST/click/return,
hard stop, T1–T4 access, removal, 100-cycle actuation. 같은 STEP에 curved shell-like glue surface와
8 mm opening/jig 반복성 test도 넣었다.

## 11. Required renders

{renders}

## 12. Outputs / verification / STOP

- standard core: `{data['outputs']['standardCoreStep']}`
- I2 harness: `{data['outputs']['representativeStep']}`
- alignment jig: `{data['outputs']['jigStep']}`
- all-8 virtual: `{data['outputs']['all8Step']}`
- V2 coupon STEP/STL: `{data['outputs']['couponStep']}` / `{data['outputs']['couponStl']}`
- JSON: `{data['outputs']['json']}`
- protected production hashes preserved: **{data['protectedInputsPreserved']}**
- production modification: **0**

**STOP.** 사용자 승인 전 production shell cut, harness placement, cap/center/Thumb 변경을 하지 않는다.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); RENDER.mkdir(parents=True, exist_ok=True)
    before = {relative(path): sha256(path) for path in PROTECTED if path.exists()}
    datums = {name: datum for name, datum in load_all_datums().items() if name in BUTTONS}
    shells = {owner: load_mesh(mesh) for owner, mesh in OWNER_MESH.items()}
    local = standard_core()
    access = terminal_access(local["core"], local["keeper"])
    if not access["allOpen"]:
        raise RuntimeError("Standard core blocks a terminal corridor")

    virtual, all_shapes = virtual_rows(datums, shells, local)
    rep_datum = datums[REPRESENTATIVE]; rep_front = float(FROZEN_FRONT_DEPTHS[REPRESENTATIVE])
    rep_shapes = dict(all_shapes[REPRESENTATIVE])
    rep_shapes["jig"] = placed_local(alignment_jig(), rep_datum, rep_front, "I2_OPENING_DATUM_ALIGNMENT_JIG")
    rep_assembly = Compound(children=[rep_shapes["compound"], rep_shapes["pusher"],
                                      placed_local(local["body"], rep_datum, rep_front, "I2_ITS_BODY"),
                                      placed_local(local["actuator"], rep_datum, rep_front, "I2_ITS_ACTUATOR"),
                                      rep_shapes["jig"]], label="I2_OPEN_FRAME_GLUED_HARNESS_AUDIT_ONLY")

    export_step(Compound(children=[local["core"], local["keeper"], local["pusher"]],
                         label="STANDARD_OPEN_FRAME_HARNESS_CORE_AUDIT_ONLY"), CORE_STEP)
    export_step(rep_assembly, I2_STEP)
    export_step(alignment_jig(), JIG_STEP)
    export_step(Compound(children=[all_shapes[name]["compound"] for name in BUTTONS],
                         label="ALL8_VIRTUAL_OPEN_FRAME_HARNESSES"), ALL8_STEP)
    coupon = coupon_v2(); export_step(coupon, COUPON_STEP)
    export_stl(coupon, COUPON_STL, tolerance=0.04, angular_tolerance=0.10)
    renders = render_outputs(local, rep_shapes, all_shapes, datums, shells, coupon)

    local_min, local_max = bounds(local["core"])
    comparison = {
        "closedPocketMaterialMm3": 235.759,
        "bulkyCartridgeEnvelopeMm3": 9.6 * 9.6 * 10.0,
        "openFrameCoreMaterialMm3": volume(local["core"]) + volume(local["keeper"]),
        "openFrameEnvelopeMm3": float(np.prod(local_max - local_min)),
        "verdict": "OPEN FRAME LOWEST MATERIAL / ADHESIVE AND ASSEMBLY HIGHEST DEPENDENCY",
    }
    data: dict[str, object] = {
        "schema": "onegrip.open_frame_glued_switch_harness_candidate.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "AUDIT/CANDIDATE ONLY / SERIAL / LOCAL SHELL RAY SAMPLES / PRODUCTION EDIT 0",
        "representative": {"button": REPRESENTATIVE, "reason": "non-seam-special JfD curved wall + shared-family + all terminals"},
        "freeze": {"exterior": "PRESERVED", "buttonCentersAxes": "PRESERVED", "loweredThumb": "PRESERVED",
                   "JaDJfDSplit": "PRESERVED", "productionModificationCount": 0},
        "standardCore": {
            "bodyAuthorityMm": [BODY_U, BODY_V, BODY_H], "guideOdMm": GUIDE_OD,
            "openingMm": OPENING, "minimumStructuralMm": STRUCTURAL_MIN,
            "preferredStructuralMm": STRUCTURAL_PREFERRED,
            "coreVolumeMm3": volume(local["core"]) + volume(local["keeper"]),
            "terminalAccess": access,
            "switchRetention": "broad removable +U keeper; no snap; physical retention/cure test required",
        },
        "actuation": {"pusherTipMm": PUSHER_TIP_D, "shaftMm": PUSHER_SHAFT_D,
                      "shoulderMm": PUSHER_SHOULDER_D, "restGapMm": REST_GAP,
                      "T_CLICK": T_CLICK, "T_DESIGN_FULL": T_DESIGN_FULL,
                      "T_HARD_STOP": T_HARD_STOP,
                      "solver": "simultaneous cap/seat/pusher/travel/stop stack; shell clearance verified after closure",
                      "authority": "PROVISIONAL / physical force-travel coupon required"},
        "adhesive": {"bondlineParametersMm": [0.20, 0.30, 0.50],
                     "primaryLoad": "compression + shear", "pressPeel": 0.0,
                     "unknowns": ["adhesive chemistry", "shell material compatibility", "primer", "cure shrink", "fatigue"]},
        "alignmentJig": {"openingKeyMm": 7.72, "axisPilotMm": 4.16, "flangeMm": 13.0,
                         "constrains": ["center", "W axis", "depth", "roll"], "verdict": "PASS AS AUDIT GEOMETRY"},
        "virtualFit": virtual,
        "architectureComparison": comparison,
        "couponV2": {"stations": [
            {"gapUmm": 0.12, "gapVmm": 0.14, "tipDmm": 2.40, "stopMm": 0.34},
            {"gapUmm": 0.20, "gapVmm": 0.22, "tipDmm": 2.60, "stopMm": 0.38},
            {"gapUmm": 0.32, "gapVmm": 0.35, "tipDmm": 2.80, "stopMm": 0.42}],
            "tests": ["ITS insertion", "bottom seating", "side clearance", "corner feature", "pusher",
                      "REST/click/return", "hard stop", "terminal access", "removal", "100-cycle", "glue", "jig repeatability"]},
        "finalVerdict": "B / OPEN-FRAME HARNESS WORKS, BUT SOME POSITIONS NEED LOCAL VARIANTS",
        "outputs": {"standardCoreStep": relative(CORE_STEP), "representativeStep": relative(I2_STEP),
                    "jigStep": relative(JIG_STEP), "all8Step": relative(ALL8_STEP),
                    "couponStep": relative(COUPON_STEP), "couponStl": relative(COUPON_STL),
                    "json": relative(JSON_PATH), "report": relative(REPORT), "renders": renders},
    }
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    after = {relative(path): sha256(path) for path in PROTECTED if path.exists()}
    data["inputHashesBefore"] = before; data["inputHashesAfter"] = after
    data["protectedInputsPreserved"] = before == after
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"verdict": data["finalVerdict"], "buttons": len(virtual["buttons"]),
                      "renders": len(renders), "coreVolumeMm3": data["standardCore"]["coreVolumeMm3"],
                      "inputsPreserved": data["protectedInputsPreserved"], "report": relative(REPORT)},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
