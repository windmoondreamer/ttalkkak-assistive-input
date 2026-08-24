"""Audit-only slot-anchored ITS harness + captive pusher architecture.

This generator supersedes docs/77 as a *production direction* without
deleting or editing it.  It derives local inner-housing surface bands from
the frozen shell meshes, adds only keyed tongue receptacles, keeps the switch
cage open, and separates pusher retention from the structural hard stop.
No production shell, inner housing, carrier, cap, or pusher source is edited.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gc
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import (
    Align, Box, Compound, Cylinder, Location, Plane, Shape, Vector,
    export_step, export_stl,
)

from .detailed_pushbtn_8_button_revalidation import mesh_to_faceted_solid
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, point_at, unit
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import (
    ACT_D, BODY_H, BODY_U, BODY_V, BUTTONS, OWNER_MESH, ROOT,
    TOTAL_H, load_mesh, near_mesh, overlap_aabb, relative, sha256,
    triangle_wireframes,
)
from .option_c_local_exact_prototype import raster_scene, safe_triangles


OUT = ROOT / "build123d_workbench/out/slot_anchored_harness_captive_pusher_audit"
RENDER = ROOT / "renders/slot_anchored_harness_captive_pusher_audit"
REPORT = ROOT / "docs/78_slot_anchored_harness_and_captive_pusher_audit.md"
JSON_PATH = OUT / "slot_anchored_harness_and_captive_pusher_audit.json"
CORE_STEP = OUT / "STANDARD_SLOT_ANCHORED_OPEN_FRAME_HARNESS_AUDIT_ONLY.step"
REP_STEP = OUT / "I2_SLOT_ANCHORED_HARNESS_CAPTIVE_PUSHER_AUDIT_ONLY.step"
ALL8_STEP = OUT / "ALL8_SLOT_ANCHORED_HARNESS_VIRTUAL_AUDIT_ONLY.step"
COUPON_STEP = OUT / "SLOT_ANCHORED_HARNESS_CAPTIVE_PUSHER_COUPON_V2_AUDIT_ONLY.step"
COUPON_STL = OUT / "SLOT_ANCHORED_HARNESS_CAPTIVE_PUSHER_COUPON_V2_AUDIT_ONLY.stl"

REPRESENTATIVE = "I2"
STRUCTURAL_MIN = 1.20
STRUCTURAL_PREFERRED = 1.60
SHELL_BAND_THICKNESS = 1.60
SHELL_BAND_BASE_CLEARANCE = 0.30
SLOT_DEPTH = 2.40
SLOT_CLEARANCE = 0.25
TONGUE_LENGTH = 3.20
TONGUE_V = 2.00
TONGUE_A_U = 2.40
TONGUE_B_U = 3.20
T_CLICK = 0.33
T_DESIGN_FULL = 0.38
T_STOP = 0.38
REST_GAP = 0.08
PUSHER_TIP_D = 2.60
PUSHER_SHAFT_D = 4.60
PUSHER_GUIDE_D = 5.00
PUSHER_SHOULDER_D = 6.40
GUIDE_CAVITY_D = 6.80
GUIDE_OD = 7.60
GROOVE_ROOT_D = 3.80
GROOVE_WIDTH = 0.60
CLIP_OD = 7.00
GUIDE_INNER_W = 7.20
STOP_PLANE_W = 7.30
SHOULDER_BOTTOM_REST_W = STOP_PLANE_W + T_STOP

TRIM_DECISIONS = {
    "N1": "T1/T2/T3/T4 available", "N2": "T1/T3 active; T2/T4 unused trim",
    "I2": "T1/T2/T3/T4 open", "I3": "T1/T2/T3/T4 open",
    "I4": "T1/T2/T3/T4 open", "M3": "T1/T2/T3/T4 open",
    "M4": "T2 unused; remaining terminals open", "N3": "T3 unused; remaining terminals open",
}

PROTECTED = [
    ROOT / "build123d_workbench/finger_controls_v2.py",
    ROOT / "build123d_workbench/n1_production_intent_mechanism.py",
    ROOT / "build123d_workbench/n2_production_intent_mechanism.py",
    ROOT / "build123d_workbench/i2_i3_production_intent_mechanism.py",
    ROOT / "build123d_workbench/i4_m3_production_intent_mechanisms.py",
    ROOT / "build123d_workbench/m4_n3_production_intent_mechanism.py",
    ROOT / "build123d_workbench/open_frame_glued_switch_harness_candidate.py",
    ROOT / "build123d_workbench/out/button_fdm_coupon/BUTTON_FDM_TEST_COUPON.step",
    ROOT / "docs/76_source_faithful_button_mechanism_and_fdm_rebase_audit.md",
    ROOT / "docs/77_open_frame_glued_switch_harness_candidate.md",
    ROOT / "cad_dump/mesh_ITS_LIVE_JaD.json",
    ROOT / "cad_dump/mesh_ITS_LIVE_JfD.json",
]

C = {
    "shell": (113, 132, 151), "housing": (66, 184, 131), "slot": (112, 211, 164),
    "harness": (57, 153, 220), "tongue": (155, 108, 217), "switch": (232, 92, 99),
    "pusher": (246, 184, 66), "clip": (218, 226, 235), "guide": (70, 169, 227),
    "stop": (239, 80, 83), "glue": (246, 132, 61), "axis": (44, 190, 218),
}
FOOTER = "AUDIT/CANDIDATE ONLY | docs/77 PRESERVED AS SUPERSEDED ALTERNATIVE | PRODUCTION MODIFICATION = 0"


def local_box(u: float, v: float, w: float, u0: float, v0: float, w0: float, label: str) -> Shape:
    result = Box(u, v, w, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(u0, v0, w0)))
    result.label = label
    return result


def local_cylinder(diameter: float, w0: float, w1: float, label: str) -> Shape:
    result = Cylinder(diameter / 2.0, w1 - w0, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, w0)))
    result.label = label
    return result


def volume(shape: Shape | None) -> float:
    return 0.0 if shape is None or not shape.solids() else float(shape.volume)


def bounds(shape: Shape) -> tuple[np.ndarray, np.ndarray]:
    box = shape.bounding_box()
    return np.asarray((box.min.X, box.min.Y, box.min.Z), float), np.asarray((box.max.X, box.max.Y, box.max.Z), float)


def slot_layout(name: str) -> list[dict[str, float | str]]:
    # N2 is centred on X=0.  Its bosses are shifted farther into JfD and away
    # from the active negative-U terminal pair; the common switch cage itself
    # stays on the frozen actuator axis.
    u_shift = -4.20 if name == "N2" else 0.0
    v_abs = 5.50 if name == "N2" else 5.00
    return [
        {"id": "A", "u": u_shift, "v": -v_abs, "tongueU": TONGUE_A_U, "tongueV": TONGUE_V},
        {"id": "B", "u": u_shift, "v": +v_abs, "tongueU": TONGUE_B_U, "tongueV": TONGUE_V},
    ]


def terminal_proxies() -> dict[str, Shape]:
    rows: dict[str, Shape] = {}
    for su, tag_u in ((-1, "N"), (1, "P")):
        for sv, tag_v in ((-1, "N"), (1, "P")):
            p0 = (su * 3.05, sv * 2.25, -0.30)
            p1 = (su * 4.10, sv * 2.25, -1.80)
            rows[f"T{tag_u}{tag_v}"] = oriented_box_between(
                p0, p1, (0, 1, 0), 0.70, 0.50, label=f"T{tag_u}{tag_v}_TERMINAL_ACCESS_PROXY")
    return rows


def open_frame_harness(name: str = "I2", slot_clearance: float = SLOT_CLEARANCE) -> dict[str, Shape]:
    """Common switch cage plus one of two broad insert-tab layouts."""
    base = local_box(9.60, 1.60, 1.20, 0, 0, -1.20, "OPEN_BASE_U_RAIL").fuse(
        local_box(1.60, 12.00, 1.20, 0, 0, -1.20, "OPEN_BASE_V_RAIL"))
    u_neg = -(BODY_U / 2 + 0.20 + 0.80)
    v_neg = -(BODY_V / 2 + 0.22 + 0.80)
    v_pos = +(BODY_V / 2 + 0.22 + 0.80)
    fixed = base
    for cheek in (
        local_box(1.60, 1.80, 3.00, u_neg, 0, 0, "NEG_U_LOCATOR_CHEEK"),
        local_box(1.80, 1.60, 3.00, 0, v_neg, 0, "NEG_V_LOCATOR_CHEEK"),
        local_box(1.80, 1.60, 3.00, 0, v_pos, 0, "POS_V_CLEARANCE_CHEEK"),
    ):
        fixed = fixed.fuse(cheek)
    tongues: list[Shape] = []
    shoulders: list[Shape] = []
    for row in slot_layout(name):
        tu, tv = float(row["tongueU"]), float(row["tongueV"])
        tongue = local_box(tu, tv, TONGUE_LENGTH, float(row["u"]), float(row["v"]), -4.40,
                           f"KEYED_TONGUE_{row['id']}_{tu:.2f}x{tv:.2f}")
        shoulder = local_box(tu + 2.40, tv + 2.00, 0.60, float(row["u"]), float(row["v"]), -1.20,
                             f"BROAD_LOAD_SHOULDER_{row['id']}")
        fixed = fixed.fuse(tongue).fuse(shoulder)
        tongues.append(tongue); shoulders.append(shoulder)
    fixed = fixed.clean(); fixed.label = "STANDARD_OPEN_FRAME_CAGE_WITH_KEYED_INSERT_TABS"
    keeper = local_box(1.60, 2.40, 2.60, BODY_U / 2 + 1.15, 0, 0.20, "BROAD_POS_U_SERVICE_KEEPER")
    body = local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "ITS1105_MEASURED_BODY")
    actuator = local_cylinder(ACT_D, BODY_H, TOTAL_H, "ITS1105_MEASURED_ACTUATOR")
    lug_parts = []
    for u0 in (-2.25, 2.25):
        for v0 in (-2.25, 2.25):
            lug_parts.append(local_cylinder(1.40, BODY_H, BODY_H + 0.80, "CORNER_FEATURE_FREE_KEEP_OUT").moved(
                Location(Vector(u0, v0, 0))))
    return {"core": fixed, "keeper": keeper, "tongues": Compound(children=tongues),
            "shoulders": Compound(children=shoulders), "body": body, "actuator": actuator,
            "lugs": Compound(children=lug_parts), "family": "N2 SAME-HALF TAB MODULE" if name == "N2" else "STANDARD TAB MODULE"}


def pusher_system() -> dict[str, Shape]:
    lower = local_cylinder(PUSHER_SHAFT_D, 6.08, 6.55, "PUSHER_LOWER_SHAFT_D4P60")
    groove = local_cylinder(GROOVE_ROOT_D, 6.55, 7.15, "PUSHER_RETENTION_GROOVE_ROOT_D3P80")
    upper = local_cylinder(PUSHER_SHAFT_D, 7.15, 9.10, "PUSHER_UPPER_SHAFT_D4P60")
    tip = local_cylinder(PUSHER_TIP_D, 6.08, 6.22, "PUSHER_TIP_D2P60")
    shoulder = local_cylinder(PUSHER_SHOULDER_D, SHOULDER_BOTTOM_REST_W, SHOULDER_BOTTOM_REST_W + 0.50,
                              "PUSHER_BROAD_HARD_STOP_SHOULDER_D6P40")
    head = local_cylinder(7.20, 8.55, 9.10, "PUSHER_CAP_CONTACT_HEAD_D7P20")
    pusher = lower.fuse(groove).fuse(upper).fuse(tip).fuse(shoulder).fuse(head).clean()
    pusher.label = "SEPARATE_CAPTIVE_PUSHER_PIN"

    clip_blank = local_cylinder(CLIP_OD, 6.55, 7.15, "E_CLIP_BLANK")
    clip_bore = local_cylinder(GROOVE_ROOT_D, 6.45, 7.25, "E_CLIP_GROOVE_BORE")
    mouth = local_box(4.20, 2.60, 0.80, 2.80, 0, 6.45, "E_CLIP_RADIAL_INSTALL_MOUTH")
    clip = (clip_blank - clip_bore - mouth).clean(); clip.label = "METAL_E_CLIP_REPRESENTATION_RETENTION_ONLY"

    guide_outer = local_cylinder(GUIDE_OD, GUIDE_INNER_W, 8.95, "OUTER_SHELL_LOCAL_GUIDE_OD7P60")
    guide_bore = local_cylinder(PUSHER_GUIDE_D, GUIDE_INNER_W - 0.10, 9.05, "PUSHER_GUIDE_BORE_D5P00")
    shoulder_cavity = local_cylinder(GUIDE_CAVITY_D, STOP_PLANE_W, 8.30, "HARD_STOP_SHOULDER_CAVITY_D6P80")
    guide = (guide_outer - guide_bore - shoulder_cavity).clean(); guide.label = "AUDIT_OUTER_SHELL_GUIDE_AND_STOP_INTERFACE"
    stop = local_cylinder(GUIDE_CAVITY_D, STOP_PLANE_W - 0.035, STOP_PLANE_W + 0.035, "STRUCTURAL_STOP_PLANE")
    stop = (stop - local_cylinder(PUSHER_GUIDE_D, STOP_PLANE_W - 0.10, STOP_PLANE_W + 0.10, "x")).clean()
    return {"pusher": pusher, "clip": clip, "guide": guide, "stop": stop, "shoulder": shoulder}


def shell_samples(shell: np.ndarray, datum) -> np.ndarray:
    centers = shell.mean(axis=1)
    rel = centers - np.asarray(datum.center, float)
    u, v, axis = unit(datum.switch_u), unit(datum.switch_v), unit(datum.axis)
    return np.c_[rel @ u, rel @ v, -(rel @ axis)]


def robust_panel_fit(samples: np.ndarray, panel_bounds: tuple[float, float, float, float]) -> dict[str, object]:
    u0, u1, v0, v1 = panel_bounds
    mask = ((samples[:, 0] >= u0) & (samples[:, 0] <= u1) &
            (samples[:, 1] >= v0) & (samples[:, 1] <= v1) &
            (samples[:, 2] >= 1.0) & (samples[:, 2] <= 6.5))
    rows = samples[mask]
    if len(rows) < 8:
        mask = ((np.abs(samples[:, 0]) <= 9.0) & (np.abs(samples[:, 1]) <= 8.0) &
                (samples[:, 2] >= 1.0) & (samples[:, 2] <= 6.5))
        rows = samples[mask]
    if len(rows) < 8:
        raise RuntimeError("insufficient frozen-shell samples for conformal panel")
    design = np.c_[np.ones(len(rows)), rows[:, :2]]
    keep = np.abs(rows[:, 2] - np.median(rows[:, 2])) <= 1.60
    coef = np.linalg.lstsq(design[keep], rows[keep, 2], rcond=None)[0]
    for _ in range(4):
        residual = rows[:, 2] - design @ coef
        median = float(np.median(residual[keep]))
        next_keep = np.abs(residual - median) <= 0.65
        if int(next_keep.sum()) < 8:
            break
        keep = next_keep
        coef = np.linalg.lstsq(design[keep], rows[keep, 2], rcond=None)[0]
    residual = rows[:, 2] - design @ coef
    q05, q50, q95 = np.quantile(residual[keep], [0.05, 0.50, 0.95])
    clearance = SHELL_BAND_BASE_CLEARANCE + max(0.0, float(q95))
    gaps = clearance - residual[keep]
    return {"coef": coef, "sampleCount": int(len(rows)), "inlierCount": int(keep.sum()),
            "residualP05P50P95Mm": [float(q05), float(q50), float(q95)],
            "clearanceAppliedMm": clearance,
            "robustGapP05P50P95Mm": [float(x) for x in np.quantile(gaps, [0.05, 0.50, 0.95])],
            "boundsUVmm": list(panel_bounds)}


def panel_solid(fit: dict[str, object], seat_depth: float, label: str) -> Shape:
    u0, u1, v0, v1 = map(float, fit["boundsUVmm"])
    coef = np.asarray(fit["coef"], float); clearance = float(fit["clearanceAppliedMm"])
    corners = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    top = np.asarray([(u, v, seat_depth - float(coef @ np.asarray((1.0, u, v))) - clearance) for u, v in corners])
    bottom = top.copy(); bottom[:, 2] -= SHELL_BAND_THICKNESS
    tris = [
        (top[0], top[1], top[2]), (top[0], top[2], top[3]),
        (bottom[0], bottom[2], bottom[1]), (bottom[0], bottom[3], bottom[2]),
    ]
    for i, j in ((0, 1), (1, 2), (2, 3), (3, 0)):
        tris.extend(((top[i], bottom[i], bottom[j]), (top[i], bottom[j], top[j])))
    solid = mesh_to_faceted_solid(np.asarray(tris, float)); solid.label = label
    return solid


def conformal_inner_housing(name: str, shell: np.ndarray, datum, front: float,
                            slot_clearance: float = SLOT_CLEARANCE) -> tuple[dict[str, Shape], dict[str, object]]:
    samples = shell_samples(shell, datum)
    if name == "N2":
        panel_bounds = [(-7.5, -0.6, -7.0, -4.2), (-7.5, -0.6, 4.2, 7.0), (-7.5, -4.5, -4.2, 4.2)]
    else:
        panel_bounds = [(-7.5, 7.5, -7.0, -4.2), (-7.5, 7.5, 4.2, 7.0),
                        (-7.5, -4.5, -4.2, 4.2), (4.5, 7.5, -4.2, 4.2)]
    fits = [robust_panel_fit(samples, bounds_uv) for bounds_uv in panel_bounds]
    seat_depth = front + BODY_H
    panels = [panel_solid(fit, seat_depth, f"{name}_FROZEN_SHELL_DERIVED_PANEL_{i}") for i, fit in enumerate(fits, 1)]

    bosses: list[Shape] = []
    slots: list[Shape] = []
    columns: list[Shape] = []
    for row in slot_layout(name):
        su = float(row["tongueU"]) + 2.0 * slot_clearance
        sv = float(row["tongueV"]) + 2.0 * slot_clearance
        boss_u, boss_v = su + 2.0 * STRUCTURAL_MIN, sv + 2.0 * STRUCTURAL_MIN
        boss = local_box(boss_u, boss_v, SLOT_DEPTH, float(row["u"]), float(row["v"]), -3.60,
                         f"{name}_SLOT_BOSS_{row['id']}")
        slot = local_box(su, sv, SLOT_DEPTH + 0.40, float(row["u"]), float(row["v"]), -3.80,
                         f"{name}_KEYED_THROUGH_SLOT_{row['id']}")
        boss = (boss - slot).clean(); boss.label = f"{name}_OPEN_RECEPTACLE_{row['id']}_WALL1P20"
        bosses.append(boss); slots.append(slot)
        fit = fits[0] if float(row["v"]) < 0 else fits[1]
        coef = np.asarray(fit["coef"], float)
        band_w = seat_depth - float(coef @ np.asarray((1.0, float(row["u"]), float(row["v"])))) - float(fit["clearanceAppliedMm"]) - SHELL_BAND_THICKNESS
        p0 = (float(row["u"]), float(row["v"]), -1.20)
        p1 = (float(row["u"]), float(row["v"]), band_w)
        columns.append(oriented_box_between(p0, p1, (1, 0, 0), boss_u, STRUCTURAL_PREFERRED,
                                             label=f"{name}_BROAD_SLOT_LOAD_COLUMN_{row['id']}"))
    housing = Compound(children=[*panels, *bosses, *columns], label=f"{name}_CONFORMAL_INNER_HOUSING_WITH_KEYED_SLOTS")
    all_gaps = [value for fit in fits for value in fit["robustGapP05P50P95Mm"]]
    metrics = {
        "derivation": "frozen owner-shell triangle centroids -> robust local depth planes -> controlled inward clearance",
        "panelCount": len(panels), "panels": [{k: v for k, v in fit.items() if k != "coef"} for fit in fits],
        "minimumReportedRobustGapMm": min(all_gaps), "maximumReportedRobustGapMm": max(all_gaps),
        "localThicknessMm": SHELL_BAND_THICKNESS, "slotDepthMm": SLOT_DEPTH,
        "slotClearancePerSideMm": slot_clearance, "minimumSlotWallMm": STRUCTURAL_MIN,
        "loadSupport": "two broad shoulder bosses + two 1.60 mm columns into shell-derived band",
        "productionAuthority": "AUDIT MESH-DERIVED; exact frozen BRep offset/loft required before apply",
    }
    return {"housing": housing, "panels": Compound(children=panels), "bosses": Compound(children=bosses),
            "slots": Compound(children=slots), "columns": Compound(children=columns)}, metrics


def adhesive_regions(name: str) -> Shape:
    beads: list[Shape] = []
    for row in slot_layout(name):
        u, v = float(row["u"]), float(row["v"])
        tu, tv = float(row["tongueU"]), float(row["tongueV"])
        beads.extend([
            local_box(0.40, tv + 0.60, 0.45, u - tu / 2 - 0.20, v, -4.05, f"{name}_REAR_GLUE_BEAD_L"),
            local_box(0.40, tv + 0.60, 0.45, u + tu / 2 + 0.20, v, -4.05, f"{name}_REAR_GLUE_BEAD_R"),
        ])
    return Compound(children=beads, label=f"{name}_SECONDARY_RETENTION_GLUE_REGIONS")


def datum_location(datum, front: float) -> Location:
    return Plane(origin=point_at(datum, front + BODY_H), x_dir=datum.switch_u, z_dir=datum.axis).location


def placed(shape: Shape, datum, front: float, label: str) -> Shape:
    result = datum_location(datum, front) * shape; result.label = label
    return result


def terminal_access(harness: dict[str, Shape], housing: dict[str, Shape]) -> dict[str, object]:
    obstacle = Compound(children=[harness["core"], harness["keeper"], housing["bosses"], housing["columns"]])
    rows = {}
    for name, terminal in terminal_proxies().items():
        pen = volume(terminal & obstacle)
        rows[name] = {"penetrationMm3": pen, "open": pen <= 1.0e-6}
    return {"terminals": rows, "allOpen": all(row["open"] for row in rows.values())}


def local_candidate(name: str, shell: np.ndarray, datum, front: float,
                    slot_clearance: float = SLOT_CLEARANCE) -> tuple[dict[str, Shape], dict[str, object]]:
    harness = open_frame_harness(name, slot_clearance)
    housing, housing_metrics = conformal_inner_housing(name, shell, datum, front, slot_clearance)
    pusher = pusher_system(); glue = adhesive_regions(name)
    access = terminal_access(harness, housing)
    children = [housing["housing"], harness["core"], harness["keeper"], harness["body"], harness["actuator"],
                pusher["guide"], pusher["pusher"], pusher["clip"], glue]
    assembly = Compound(children=children, label=f"{name}_SLOT_ANCHORED_FULL_STACK_AUDIT_ONLY")
    metrics = {"housing": housing_metrics, "terminalAccess": access, "family": harness["family"]}
    return {**harness, **housing, **pusher, "glue": glue, "assembly": assembly}, metrics


def virtual_all(datums: dict[str, object], shells: dict[str, np.ndarray]) -> tuple[dict[str, object], dict[str, dict[str, Shape]]]:
    rows: dict[str, object] = {}; world: dict[str, dict[str, Shape]] = {}
    for name in BUTTONS:
        datum = datums[name]; front = float(FROZEN_FRONT_DEPTHS[name])
        local, metrics = local_candidate(name, shells[datum.owner], datum, front)
        keys = ("assembly", "housing", "panels", "bosses", "slots", "columns", "core", "keeper", "tongues",
                "shoulders", "body", "actuator", "guide", "pusher", "clip", "stop", "glue")
        world[name] = {key: placed(local[key], datum, front, f"{name}_{key.upper()}") for key in keys}
        layouts = []
        same_half = True
        for row in slot_layout(name):
            center = np.asarray(point_at(datum, front + BODY_H, u_offset=float(row["u"]), v_offset=float(row["v"])), float)
            slot_u = float(row["tongueU"]) + 2 * SLOT_CLEARANCE
            slot_v = float(row["tongueV"]) + 2 * SLOT_CLEARANCE
            layouts.append({"id": row["id"], "centerMm": center.tolist(), "localUVmm": [row["u"], row["v"]],
                            "widthUmm": slot_u, "heightVmm": slot_v, "depthWmm": SLOT_DEPTH,
                            "clearancePerSideMm": SLOT_CLEARANCE, "insertionDirection": "local -W into through-slot",
                            "minimumWallMm": STRUCTURAL_MIN})
        if name == "N2":
            _, upper = bounds(world[name]["bosses"])
            same_half = bool(upper[0] <= -0.20)
        rows[name] = {
            "coreFamily": metrics["family"], "slots": layouts, "slotSameOwnerHalf": same_half,
            "owner": datum.owner, "axis": list(map(float, unit(datum.axis))),
            "guideBoreMm": PUSHER_GUIDE_D, "shaftMm": PUSHER_SHAFT_D,
            "guideRadialClearanceMm": (PUSHER_GUIDE_D - PUSHER_SHAFT_D) / 2,
            "terminalAccess": metrics["terminalAccess"], "terminalPlan": TRIM_DECISIONS[name],
            "housing": metrics["housing"], "loadPath": "PUSHER->ITS->OPEN SEAT->2 SHOULDERS->2 COLUMNS->CONFORMAL BAND->SHELL",
            "clipInPressLoadPath": False, "gluePrimaryPressReaction": False,
            "seamVerdict": "CONDITIONAL / BOTH SLOT BOSSES JfD-SIDE" if name == "N2" else "NOT N2 SPECIAL",
            "verdict": "CONDITIONAL / COUPON + EXACT BREP HOUSING REQUIRED",
        }
        gc.collect()
    neighbors = {}
    for i, left in enumerate(BUTTONS):
        for right in BUTTONS[i + 1:]:
            gap, overlap = overlap_aabb(world[left]["assembly"], world[right]["assembly"])
            neighbors[f"{left}-{right}"] = {"aabbGapMm": gap, "aabbOverlapProxyMm3": overlap,
                                            "status": "LOCAL TRIM REVIEW" if overlap > 0 else "CLEAR"}
    for name in BUTTONS:
        related = [value for pair, value in neighbors.items() if name in pair.split("-")]
        rows[name]["neighborClearanceMm"] = min((row["aabbGapMm"] for row in related), default=999.0)
        rows[name]["neighborReview"] = any(row["status"] != "CLEAR" for row in related)
    return {"buttons": rows, "neighborPairs": neighbors}, world


def moved(shape: Shape, xyz: Iterable[float], label: str) -> Shape:
    x, y, z = map(float, xyz); result = shape.moved(Location(Vector(x, y, z))); result.label = label; return result


def at_state(shape: Shape, travel: float, label: str) -> Shape:
    return moved(shape, (0, 0, -travel), label)


def coupon_v2() -> Shape:
    children: list[Shape] = []
    for index, clearance in enumerate((0.15, 0.25, 0.35)):
        fake_datum = load_all_datums()[REPRESENTATIVE]
        shell = load_mesh(OWNER_MESH[fake_datum.owner])
        local, _ = local_candidate(REPRESENTATIVE, shell, fake_datum, float(FROZEN_FRONT_DEPTHS[REPRESENTATIVE]), clearance)
        shift = (index * 20.0, 0, 4.4)
        for key in ("bosses", "core", "keeper", "body"):
            children.append(moved(local[key], shift, f"COUPON_{index+1}_{key.upper()}_CLR{clearance:.2f}"))
    p = pusher_system()
    for key in ("guide", "pusher", "clip", "stop"):
        children.append(moved(p[key], (20, 22, 0), f"COUPON_PUSHER_{key.upper()}"))
    access_plate = local_box(18, 10, 2.4, 0, 0, 0, "COUPON_ADHESIVE_ACCESS_PLATE")
    access_slot_a = local_box(TONGUE_A_U + 0.50, TONGUE_V + 0.50, 3.0, -4, 0, -0.3, "ACCESS_SLOT_A")
    access_slot_b = local_box(TONGUE_B_U + 0.50, TONGUE_V + 0.50, 3.0, 4, 0, -0.3, "ACCESS_SLOT_B")
    children.append(moved((access_plate - access_slot_a - access_slot_b).clean(), (44, 22, 0), "COUPON_GLUE_ACCESS_AND_SQUEEZE_OUT"))
    return Compound(children=children, label="SLOT_ANCHORED_HARNESS_CAPTIVE_PUSHER_COUPON_V2")


def clip_half(shape: Shape) -> np.ndarray:
    tool = Box(100, 50, 100, align=(Align.CENTER, Align.MAX, Align.CENTER))
    result = shape & tool
    return safe_triangles(result.clean()) if result.solids() else np.empty((0, 3, 3))


def clip_w(shape: Shape, w0: float, w1: float) -> np.ndarray:
    tool = local_box(20, 20, w1 - w0, 0, 0, w0, "RENDER_W_CLIP")
    result = shape & tool
    return safe_triangles(result.clean()) if result.solids() else np.empty((0, 3, 3))


def render_outputs(rep: dict[str, Shape], world: dict[str, dict[str, Shape]], datums: dict[str, object],
                   shells: dict[str, np.ndarray], coupon: Shape) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True); outputs: list[str] = []
    def render(filename, objects, title, subtitle, camera=(25, -34, 22), fit=None, transparent=None, wireframes=None):
        path = RENDER / filename
        raster_scene(path, objects, title, subtitle, FOOTER, camera_offset=camera, fit_points=fit,
                     transparent_objects=transparent or [], wireframes=wireframes or [])
        outputs.append(relative(path))
    tri = lambda key: safe_triangles(rep[key])

    exploded = [
        (safe_triangles(moved(rep["housing"], (-18, 0, 0), "EXP_HOUSING")), C["housing"]),
        (safe_triangles(moved(rep["core"], (-6, 0, 0), "EXP_HARNESS")), C["harness"]),
        (safe_triangles(moved(rep["body"], (5, 0, 0), "EXP_ITS")), C["switch"]),
        (safe_triangles(moved(rep["pusher"], (15, 0, 0), "EXP_PUSHER")), C["pusher"]),
        (safe_triangles(moved(rep["guide"], (25, 0, 0), "EXP_GUIDE")), C["guide"]),
    ]
    render("01_exploded_architecture.png", exploded, "1 / EXPLODED SLOT-ANCHORED ARCHITECTURE",
           "conformal inner housing → keyed slot/shoulder → open cage → ITS → captive pusher", camera=(45, -55, 30))

    d = datums[REPRESENTATIVE]; shell_crop = near_mesh(shells[d.owner], d.center, 14.0)
    shell_wire = [(triangle_wireframes(shell_crop, 130), (*C["shell"], 88))]
    render("02_outer_shell_and_pusher_guide.png", [(safe_triangles(world[REPRESENTATIVE]["guide"]), C["guide"]),
                                                    (safe_triangles(world[REPRESENTATIVE]["pusher"]), C["pusher"])],
           "2 / FROZEN OUTER SHELL + SMALL PUSHER GUIDE", "D5.00 bore in D7.60 local guide envelope; shell shown as wireframe",
           camera=(70, -95, 55), wireframes=shell_wire)
    render("03_pusher_and_retaining_groove.png", [(tri("pusher"), C["pusher"])],
           "3 / SEPARATE PUSHER + RETAINING GROOVE", "D4.60 shaft | D3.80 groove root | printed groove remains conditional", camera=(18, -25, 10))
    render("04_e_clip_closeup.png", [(tri("clip"), C["clip"]), (clip_w(rep["pusher"], 6.30, 7.45), C["pusher"])],
           "4 / E-CLIP REPRESENTATION — RETENTION ONLY", "clip sits below guide inner face; press motion moves it away from the guide", camera=(13, -18, 8))
    render("05_pusher_hard_stop_shoulder.png", [(clip_half(rep["guide"]), C["guide"]),
                                                 (clip_half(rep["pusher"]), C["pusher"]),
                                                 (tri("stop"), C["stop"])],
           "5 / BROAD PUSHER HARD-STOP SHOULDER", "D6.40 shoulder → D6.80 cavity floor | T_STOP=0.38; clip excluded", camera=(16, -24, 7))
    render("06_its_and_open_frame_harness.png", [(tri("core"), C["harness"]), (tri("keeper"), C["tongue"]),
                                                  (tri("body"), C["switch"]), (tri("actuator"), C["switch"])],
           "6 / MEASURED ITS + OPEN-FRAME HARNESS", "bottom cross + three cheeks + broad keeper; T1–T4 quadrants remain open")
    render("07_harness_tongue_and_shoulders.png", [(tri("tongues"), C["tongue"]), (tri("shoulders"), C["stop"])],
           "7 / ASYMMETRIC BROAD TONGUES + LOAD SHOULDERS", "A=2.40 mm wide; B=3.20 mm wide; no tiny snap or key")
    render("08_inner_housing_slots.png", [(tri("panels"), C["housing"]), (tri("bosses"), C["slot"]),
                                          (tri("columns"), C["housing"])],
           "8 / CONFORMAL INNER HOUSING + TWO KEYED SLOTS", "1.20 mm slot walls | 2.40 mm depth | broad load columns", camera=(34, -44, 28))
    render("09_harness_inserted_into_slots.png", [(tri("bosses"), C["slot"]), (tri("columns"), C["housing"]),
                                                   (tri("core"), C["harness"])],
           "9 / HARNESS INSERTED AND SHOULDER-SEATED", "slot fixes U/V/roll/depth before adhesive cure", camera=(30, -42, 20))
    render("10_secondary_adhesive_region.png", [(tri("bosses"), C["slot"]), (tri("tongues"), C["tongue"]), (tri("glue"), C["glue"])],
           "10 / REAR-ACCESS SECONDARY ADHESIVE", "anti-pullout/anti-slip only | rear squeeze-out path | central terminal keep-out")
    full_section = [(clip_half(rep[key]), color) for key, color in (
        ("housing", C["housing"]), ("core", C["harness"]), ("body", C["switch"]),
        ("actuator", C["switch"]), ("guide", C["guide"]), ("pusher", C["pusher"]), ("clip", C["clip"]))]
    render("11_full_button_to_shell_section.png", full_section, "11 / FULL LOAD-STACK SECTION",
           "button interface → pusher → ITS → open seat → shoulders → inner housing → shell band", camera=(22, -31, 9))

    for index, (label, travel) in enumerate((("REST", 0.0), ("CLICK", T_CLICK), ("FULL / HARD STOP", T_STOP)), 12):
        pusher = at_state(rep["pusher"], travel, f"PUSHER_{label}")
        clip = at_state(rep["clip"], travel, f"CLIP_{label}")
        clip_relation = "clip retained below guide; no press load" if travel == 0 else "clip moves inward away from guide"
        render(f"{index:02d}_{label.lower().replace(' / ', '_').replace(' ', '_')}.png",
               [(clip_half(rep["guide"]), C["guide"]), (clip_half(pusher), C["pusher"]),
                (safe_triangles(clip), C["clip"]), (clip_half(rep["actuator"]), C["switch"])],
               f"{index} / {label}", f"pusher travel {travel:.3f} mm | {clip_relation} | structural stop={'CONTACT' if travel == T_STOP else 'OPEN'}",
               camera=(16, -24, 7))

    split = Box(0.20, 80, 80, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    n2_fit = np.vstack((safe_triangles(world["N2"]["bosses"]).reshape(-1, 3),
                        safe_triangles(world["N2"]["shoulders"]).reshape(-1, 3)))
    render("15_n2_seam_closeup.png", [(safe_triangles(world["N2"]["bosses"]), C["slot"]),
                                      (safe_triangles(world["N2"]["shoulders"]), C["stop"]),
                                      (safe_triangles(split), C["stop"])],
           "15 / N2 SAME-HALF SLOT ANCHOR AT JaD/JfD SEAM",
           "both N2 slot bosses/shoulders remain on JfD side; core may occupy seam clearance but does not anchor both halves",
           camera=(52, -72, 42), fit=n2_fit, transparent=[(safe_triangles(split), (*C["stop"], 55))])
    all_objects = [(safe_triangles(world[name]["assembly"]), C["harness"] if name != "N2" else C["tongue"]) for name in BUTTONS]
    render("16_all8_virtual_arrangement.png", all_objects, "16 / ALL-EIGHT VIRTUAL SLOT-ANCHORED ARRANGEMENT",
           "one switch cage | standard tab module at 7 positions | N2 same-half tab module", camera=(95, -140, 95))
    render("17_inner_housing_outer_shell_conformal_section.png",
           [(safe_triangles(world[REPRESENTATIVE]["panels"]), C["housing"]),
            (safe_triangles(world[REPRESENTATIVE]["columns"]), C["slot"])],
           "17 / INNER HOUSING ↔ FROZEN OUTER SHELL CONFORMAL SECTION",
           "mesh-derived robust local panels; exact BRep controlled offset/loft remains production gate",
           camera=(72, -98, 58), wireframes=shell_wire)
    render("18_coupon_v2_preview.png", [(safe_triangles(coupon), C["housing"])],
           "18 / SLOT/TONGUE + PUSHER/CLIP/HARD-STOP COUPON V2",
           "0.15/0.25/0.35 per-side slot clearance stations + clip access + glue access", camera=(95, -110, 72))
    return outputs


def report_text(data: dict[str, object]) -> str:
    rows = []
    for name in BUTTONS:
        row = data["virtualFit"]["buttons"][name]
        slots = "; ".join(f"{slot['id']} {slot['widthUmm']:.2f}×{slot['heightVmm']:.2f}×{slot['depthWmm']:.2f}" for slot in row["slots"])
        rows.append(f"| {name} | {row['coreFamily']} | {slots} | {row['housing']['minimumReportedRobustGapMm']:.2f}…{row['housing']['maximumReportedRobustGapMm']:.2f} | "
                    f"{row['terminalAccess']['allOpen']} | {row['neighborClearanceMm']:.2f} | {row['slotSameOwnerHalf']} | **{row['verdict']}** |")
    render_rows = "\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    return f"""# 78 — Slot-anchored harness and captive pusher audit

ARCHITECTURE
= **SLOT-ANCHORED HARNESS + CAPTIVE PUSHER**

INNER HOUSING
= **CONDITIONAL — frozen-shell-derived 1.60 mm local conformal bands + open two-slot load columns; exact BRep offset/loft required**

HARNESS CORE
= **COMMON OPEN-FRAME SWITCH CAGE + STANDARD TAB MODULE; N2 USES SAME-HALF TAB MODULE**

HARNESS RETENTION
= **SLOT/SHOULDER + ADHESIVE**

PUSHER
= **SEPARATE D2.60 TIP / D4.60 SHAFT / D6.40 STOP SHOULDER / D7.20 CAP-CONTACT HEAD**

PUSHER RETENTION
= **METAL E/C-CLIP REPRESENTATION; PRINTED GROOVE CONDITIONAL, METAL PIN OR SEPARATE COLLAR PREFERRED IF COUPON CRACKS**

CLIP LOAD-BEARING
= **NO**

HARD STOP
= **PUSHER D6.40 SHOULDER → GUIDE D6.80 CAVITY FLOOR; T_STOP=0.38 mm PROVISIONAL**

N2 SEAM
= **CONDITIONAL — BOTH SLOT BOSSES/SHOULDERS ON JfD SIDE; PHYSICAL CLOSURE TRIAL REQUIRED**

8-POSITION FIT
= **CONDITIONAL — COMMON CAGE, TWO TAB MODULES, LOCAL CONFORMAL HOUSING PANELS; NEIGHBOR TRIM REVIEW REMAINS**

FDM COUPON
= **REQUIRED**

EXTERIOR
= **PRESERVED**

JaD/JfD SPLIT
= **PRESERVED**

PRODUCTION MODIFICATION
= **0**

## 1. Architecture correction and verdict

**B — SLOT-ANCHORED ARCHITECTURE IS MECHANICALLY COHERENT, BUT EXACT BREP HOUSING AND PHYSICAL COUPON ARE REQUIRED.**

docs/77의 glue-foot 방식은 삭제하지 않았으며 **SUPERSEDED ARCHITECTURE CANDIDATE / ALTERNATIVE**로 보존했다.
이번 후보는 접착면이 press reaction을 받지 않는다. 두 broad shoulder가 slot boss에 앉고, 두 1.60 mm
load column이 shell-derived inner-housing band로 하중을 전달한다.

```text
FINGER / FROZEN CAP
→ separate captive pusher
→ ITS actuator/body
→ open cross seat
→ two broad harness shoulders
→ keyed slot bosses + broad load columns
→ conformal inner-housing band
→ frozen outer shell
```

E/C clip은 guide inner face 바깥 이탈만 제한한다. 누를 때 clip은 guide에서 멀어지며 hard-stop 접촉에는
참여하지 않는다.

## 2. Frozen authority and representative

N1/N2/I2/I3/I4/M3/M4/N3 center·W axis, visible layout, exterior, maximum-lowered Thumb, JaD/JfD split은
모두 읽기 전용이다. 대표는 seam 특수성이 없는 곡면 JfD 위치 **I2**이고, N2는 별도 same-half
tab layout으로 재검토했다.

## 3. Conformal inner housing

각 owner shell mesh의 local U/V triangle-centroid depth를 panel별 robust plane으로 맞춘 뒤, residual
상한을 포함한 controlled inward clearance와 1.60 mm thickness를 적용했다. 이는 audit solid이며 production
BRep의 exact offset/loft가 아니다.

| metric | result |
|---|---:|
| original OneGrip median local housing/shell gap | {data['referenceHousing']['original']['medianLocalGapMm']:.3f} mm |
| current lowered median local gap | {data['referenceHousing']['currentLowered']['medianLocalGapMm']:.3f} mm |
| candidate robust gap range across 8 | {data['housingSummary']['minimumRobustGapMm']:.3f}…{data['housingSummary']['maximumRobustGapMm']:.3f} mm |
| candidate local band thickness | 1.60 mm |
| load support | two slot bosses + two broad columns per button |

Gap은 coincident zero가 아니라 shell tessellation residual을 흡수한 audit clearance다. 실제 생산에서는 shell
material, fastening/merge 방식, 최소 벽, cure/assembly datum을 BRep에서 다시 잠가야 한다.

## 4. Harness and keyed slots

공통 cage는 body-bottom plus cross, −U/−V controlled cheeks, +V clearance cheek, removable broad +U keeper로
구성된다. switch를 둘러싼 6.4 closed pocket은 없다. 비대칭 A/B tongue 폭은 2.40/3.20 mm이며 tiny key가 아니다.

| parameter | nominal |
|---|---:|
| tongue A / B | 2.40×2.00 / 3.20×2.00 mm |
| tongue insertion length | 3.20 mm |
| slot A / B | 2.90×2.50 / 3.70×2.50 mm |
| slot depth | 2.40 mm |
| clearance | 0.25 mm/side |
| minimum slot wall | 1.20 mm |
| broad shoulder margin | +1.20 mm U / +1.00 mm V per side |

Slot은 U/V translation, roll, depth를 glue 전에 기계적으로 등록한다. Adhesive는 rear slot exit에서 도포하며
anti-pullout, anti-vibration, anti-slip, tolerance fill만 담당한다. 중앙 actuator/pusher 및 T1–T4가 glue keep-out이다.

## 5. Captive pusher, clip safety, hard stop

| item | value / verdict |
|---|---|
| guide bore / shaft | 5.00 / 4.60 mm |
| radial clearance | 0.20 mm/side |
| guide length | 1.75 mm |
| nominal angular clearance proxy | {data['pusher']['angularClearanceDeg']:.2f}° |
| groove root / shaft | 3.80 / 4.60 mm |
| remaining cross-section | {100*data['pusher']['grooveAreaFraction']:.1f}% |
| clip outward retention travel | {data['pusher']['clipOutwardRetentionFloatMm']:.2f} mm |
| clip gap from guide at FULL | {data['pusher']['clipGuideGapAtFullMm']:.2f} mm |
| hard-stop gap REST / FULL | 0.38 / 0.00 mm |

Printed groove의 단면 68%는 자동 PASS가 아니다. Axis-on-build-Z coupon에서 100-cycle, clip installation 10회,
pullout, whitening/crack을 검사한다. 실패하면 D4.6 printed pin을 키우는 대신 **metal pin 또는 separate retained
collar**를 우선한다.

## 6. REST / CLICK / FULL simultaneous stack

| state | pusher travel | actuator compression after 0.08 gap | shoulder-stop | clip press load |
|---|---:|---:|---|---|
| REST | 0.000 | 0.000 | 0.380 open | NO |
| CLICK | 0.330 | 0.250 | 0.050 open | NO |
| FULL | 0.380 | 0.300 | CONTACT | NO |

0.350 mm는 final truth로 고정하지 않았다. T_CLICK/T_DESIGN_FULL/T_STOP는 실물 force-travel coupon 뒤 다시 잠근다.

## 7. Per-position virtual propagation

| button | family | slots U×V×W mm | housing robust gap mm | terminals open | neighbor gap | same owner half | verdict |
|---|---|---|---:|---:|---:|---:|---|
{chr(10).join(rows)}

AABB overlap은 collision 확정이 아니라 local housing band/column trim 요청이다. Frozen center/axis를 움직이지 않고
inner-housing panel 또는 column만 조정해야 한다.

## 8. N2 seam correction

N2의 두 slot center를 local U=−4.20, V=±5.50으로 옮겼다. 따라서 두 slot boss와 shoulder는 JfD 쪽에
남고 큰 glue foot나 양 shell-half anchor가 필요 없다. Switch cage 자체는 seam clearance 공간을 사용할 수 있지만
mechanical anchor는 JfD 한쪽뿐이다. JaD/JfD closure, active T1/T3 wire access, shell flex는 physical trial gate다.

## 9. Assembly and service sequence

1. Frozen outer opening 바깥에서 pusher를 guide로 삽입한다.
2. Shell 내부에서 E/C clip을 groove에 장착하고 {data['pusher']['clipOutwardRetentionFloatMm']:.2f} mm retention float를 확인한다.
3. ITS를 open-frame cage의 +U 쪽으로 넣고 broad keeper를 설치한다.
4. A/B tongue를 keyed slot에 삽입해 shoulder 두 곳을 완전히 seat한다.
5. Rear slot exit에서 secondary adhesive를 도포하고 squeeze-out을 제거한다.
6. Terminal을 검사·납땜하고 open side corridor로 배선한다.
7. REST/CLICK/FULL과 pusher return을 확인한 뒤 JaD/JfD를 닫는다.

Shell을 열면 clip 제거 후 pusher 교환이 가능하다. Harness는 접착 때문에 완전 비파괴 serviceable이 아니지만
terminal inspection/solder access는 유지한다.

## 10. Architecture comparison

| criterion | old closed pocket | docs/77 glue-foot | slot-anchored + captive pusher |
|---|---|---|---|
| packaging | closed 6.4 pocket + walls | low core, broad feet | **open cage + two small slots/columns** |
| N1/N2 | carrier/seam sensitive | N2 one-foot HOLD | **N2 same-half slots; conditional** |
| press load | pocket walls/rear seat | adhesive foot dependent | **shoulder → inner housing** |
| FDM repeatability | all-wall tolerance sensitive | shell-foot fit sensitive | **keyed slot coupon-calibrated** |
| assembly | simplest | jig + broad glue | clip + keyed insertion + small glue bead |
| adhesive dependence | low | primary | **secondary only** |
| pusher alignment | legacy guide | harness guide | **frozen shell guide + keyed harness datum** |
| serviceability | pocket extraction | adhesive destructive | pusher clip-removable; harness adhesive-limited |
| terminal access | restricted | open | **open quadrants; local N2 trial** |
| shell modification | pocket/carrier | none in audit | **small guide bore only; production edit still 0** |

## 11. FDM coupon V2

Coupon contains 0.15/0.25/0.35 mm-per-side slot stations, actual-body insertion references, shoulder seating,
rear glue access/squeeze-out, D5.00 guide/D4.60 pusher, E-clip access, groove inspection, and structural stop.

Required physical checks: insertion force, shoulder flushness, adhesive access, clip tool access, pullout, REST/CLICK/FULL,
return, hard-stop witness, 100-cycle actuation, 10× clip install/remove, groove crack/whitening, and terminal tool clearance.

## 12. Required renders

{render_rows}

## 13. Outputs, preservation, STOP

- standard harness STEP: `{data['outputs']['standardCoreStep']}`
- representative full-stack STEP: `{data['outputs']['representativeStep']}`
- all-eight virtual STEP: `{data['outputs']['all8Step']}`
- coupon STEP/STL: `{data['outputs']['couponStep']}` / `{data['outputs']['couponStl']}`
- audit JSON: `{data['outputs']['json']}`
- docs/77 preserved hash: `{data['docs77PreservedSha256']}`
- protected inputs preserved: **{data['protectedInputsPreserved']}**
- production modification: **0**

**STOP.** Exact production shell/inner-housing BRep, carrier, cap, pusher sources에는 적용하지 않았다.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); RENDER.mkdir(parents=True, exist_ok=True)
    before = {relative(path): sha256(path) for path in PROTECTED if path.exists()}
    datums = {name: datum for name, datum in load_all_datums().items() if name in BUTTONS}
    shells = {owner: load_mesh(mesh) for owner, mesh in OWNER_MESH.items()}
    virtual, world = virtual_all(datums, shells)
    rep_local, rep_metrics = local_candidate(REPRESENTATIVE, shells[datums[REPRESENTATIVE].owner],
                                             datums[REPRESENTATIVE], float(FROZEN_FRONT_DEPTHS[REPRESENTATIVE]))
    coupon = coupon_v2()

    export_step(Compound(children=[rep_local["core"], rep_local["keeper"]],
                         label="STANDARD_SLOT_ANCHORED_OPEN_FRAME_HARNESS_AUDIT_ONLY"), CORE_STEP)
    export_step(rep_local["assembly"], REP_STEP)
    export_step(Compound(children=[world[name]["assembly"] for name in BUTTONS],
                         label="ALL8_SLOT_ANCHORED_HARNESS_VIRTUAL_AUDIT_ONLY"), ALL8_STEP)
    export_step(coupon, COUPON_STEP)
    export_stl(coupon, COUPON_STL, tolerance=0.04, angular_tolerance=0.10)
    renders = render_outputs(rep_local, world, datums, shells, coupon)

    ref_path = ROOT / "build123d_workbench/out/source_faithful_button_mechanism_fdm_rebase_audit/source_faithful_button_mechanism_and_fdm_rebase_audit.json"
    reference = json.loads(ref_path.read_text(encoding="utf-8"))["thumbHousing"]
    gap_mins = [virtual["buttons"][name]["housing"]["minimumReportedRobustGapMm"] for name in BUTTONS]
    gap_maxs = [virtual["buttons"][name]["housing"]["maximumReportedRobustGapMm"] for name in BUTTONS]
    shaft_area = math.pi * PUSHER_SHAFT_D ** 2 / 4
    groove_area = math.pi * GROOVE_ROOT_D ** 2 / 4
    clip_gap_full = (GUIDE_INNER_W - (6.55 + GROOVE_WIDTH)) + T_STOP
    data: dict[str, object] = {
        "schema": "onegrip.slot_anchored_harness_captive_pusher_audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "AUDIT/CANDIDATE ONLY / FROZEN MESH-DERIVED HOUSING / PRODUCTION EDIT 0",
        "architecture": "SLOT-ANCHORED OPEN-FRAME SWITCH HARNESS + CAPTIVE PUSHER",
        "supersedesAsProductionDirection": "docs/77 conformal glue-foot harness",
        "freeze": {"centersAxes": "PRESERVED", "visibleLayout": "PRESERVED", "exterior": "PRESERVED",
                   "maximumLoweredThumb": "PRESERVED", "JaDJfDSplit": "PRESERVED", "productionModificationCount": 0},
        "representative": {"button": REPRESENTATIVE, "reason": "non-seam-special curved JfD + all terminals"},
        "harness": {"bodyAuthorityMm": [BODY_U, BODY_V, BODY_H], "tongueAmm": [TONGUE_A_U, TONGUE_V, TONGUE_LENGTH],
                    "tongueBmm": [TONGUE_B_U, TONGUE_V, TONGUE_LENGTH], "slotClearancePerSideMm": SLOT_CLEARANCE,
                    "slotDepthMm": SLOT_DEPTH, "minimumWallMm": STRUCTURAL_MIN, "familyCount": 2,
                    "families": ["STANDARD TAB MODULE (7)", "N2 SAME-HALF TAB MODULE (1)"],
                    "retention": "slot/shoulder primary + adhesive secondary"},
        "pusher": {"tipDiameterMm": PUSHER_TIP_D, "shaftDiameterMm": PUSHER_SHAFT_D,
                   "guideBoreMm": PUSHER_GUIDE_D, "radialClearanceMm": (PUSHER_GUIDE_D-PUSHER_SHAFT_D)/2,
                   "guideLengthMm": 8.95-GUIDE_INNER_W,
                   "angularClearanceDeg": math.degrees(math.atan(((PUSHER_GUIDE_D-PUSHER_SHAFT_D)/2)/(8.95-GUIDE_INNER_W))),
                   "grooveRootDiameterMm": GROOVE_ROOT_D, "grooveWidthMm": GROOVE_WIDTH,
                   "grooveAreaFraction": groove_area/shaft_area, "clipLoadBearing": False,
                   "clipOutwardRetentionFloatMm": GUIDE_INNER_W-(6.55+GROOVE_WIDTH),
                   "clipGuideGapAtFullMm": clip_gap_full,
                   "preferredFallback": "metal pin or separate retained collar if printed-groove coupon fails"},
        "actuation": {"restGapMm": REST_GAP, "T_CLICK": T_CLICK, "T_DESIGN_FULL": T_DESIGN_FULL, "T_STOP": T_STOP,
                      "actuatorCompressionAtClickMm": T_CLICK-REST_GAP,
                      "actuatorCompressionAtStopMm": T_STOP-REST_GAP,
                      "hardStop": "pusher shoulder to guide cavity floor", "clipInLoadPath": False,
                      "authority": "PROVISIONAL / force-travel coupon required"},
        "adhesive": {"role": ["anti-pullout", "anti-vibration", "anti-slip", "tolerance fill"],
                     "primaryPressReaction": False, "access": "rear slot exits after shoulder seating",
                     "keepOut": "central pusher/actuator and T1-T4 terminal quadrants",
                     "squeezeOut": "rearward open path"},
        "referenceHousing": reference,
        "housingSummary": {"minimumRobustGapMm": min(gap_mins), "maximumRobustGapMm": max(gap_maxs),
                           "localThicknessMm": SHELL_BAND_THICKNESS,
                           "authority": "mesh-derived audit; exact BRep rebase pending"},
        "virtualFit": virtual,
        "couponV2": {"slotClearanceVariantsPerSideMm": [0.15, 0.25, 0.35],
                     "tests": ["ITS insertion", "tongue/slot", "shoulder seating", "adhesive access", "guide clearance",
                               "clip installation", "REST/CLICK/FULL", "hard stop", "100-cycle", "groove crack"]},
        "finalVerdict": "B / SLOT-ANCHORED ARCHITECTURE COHERENT; EXACT BREP HOUSING + PHYSICAL COUPON REQUIRED",
        "outputs": {"standardCoreStep": relative(CORE_STEP), "representativeStep": relative(REP_STEP),
                    "all8Step": relative(ALL8_STEP), "couponStep": relative(COUPON_STEP), "couponStl": relative(COUPON_STL),
                    "json": relative(JSON_PATH), "report": relative(REPORT), "renders": renders},
    }
    after = {relative(path): sha256(path) for path in PROTECTED if path.exists()}
    data["inputHashesBefore"] = before; data["inputHashesAfter"] = after
    data["protectedInputsPreserved"] = before == after
    data["docs77PreservedSha256"] = after.get("docs/77_open_frame_glued_switch_harness_candidate.md")
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"verdict": data["finalVerdict"], "buttons": len(virtual["buttons"]), "renders": len(renders),
                      "N2SameHalf": virtual["buttons"]["N2"]["slotSameOwnerHalf"],
                      "allTerminalsOpen": all(virtual["buttons"][n]["terminalAccess"]["allOpen"] for n in BUTTONS),
                      "protectedInputsPreserved": data["protectedInputsPreserved"], "report": relative(REPORT)},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
