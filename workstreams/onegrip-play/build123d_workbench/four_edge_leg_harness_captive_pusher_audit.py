"""Audit-only four-edge-leg ITS harness + four receivers + captive pusher.

The four structural legs wrap the +U/-U/+V/-V *side mid-regions* of the
measured switch body.  They are not vertex posts and not two broad tongues.
Local inner-housing panels are derived from exact frozen-shell BRep ray
intersections; only a representative local shell crop is booleaned.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import (
    Align, Box, Compound, Cylinder, Location, Plane, Shape, Vector,
    export_step, export_stl, import_step,
)
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt

from .detailed_pushbtn_8_button_revalidation import canonical_original_triangles, mesh_to_faceted_solid
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, point_at, unit
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import (
    ACT_D, BODY_H, BODY_U, BODY_V, BUTTONS, OWNER_MESH, ROOT, TOTAL_H,
    load_mesh, overlap_aabb, relative, sha256, triangle_wireframes,
)
from .option_c_local_exact_prototype import raster_scene, safe_triangles
from .slot_anchored_harness_captive_pusher_audit import (
    clip_half, clip_w, pusher_system, terminal_proxies,
)


OUT = ROOT / "build123d_workbench/out/four_edge_leg_harness_captive_pusher_audit"
RENDER = ROOT / "renders/four_edge_leg_harness_captive_pusher_audit"
REPORT = ROOT / "docs/79_four_edge_leg_switch_harness_and_captive_pusher_audit.md"
JSON_PATH = OUT / "four_edge_leg_harness_and_captive_pusher_audit.json"
CORE_STEP = OUT / "STANDARD_FOUR_EDGE_LEG_HARNESS_AUDIT_ONLY.step"
REP_STEP = OUT / "I2_FOUR_EDGE_LEG_FULL_STACK_AUDIT_ONLY.step"
ALL8_STEP = OUT / "ALL8_FOUR_EDGE_LEG_VIRTUAL_AUDIT_ONLY.step"
COUPON_STEP = OUT / "FOUR_EDGE_LEG_RECEIVER_PUSHER_COUPON_V3_AUDIT_ONLY.step"
COUPON_STL = OUT / "FOUR_EDGE_LEG_RECEIVER_PUSHER_COUPON_V3_AUDIT_ONLY.stl"

SHELL_STEP = {
    "JaD": ROOT / "build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JAD_EXTERIOR_LOWERED_THUMB_V1.step",
    "JfD": ROOT / "build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JFD_EXTERIOR_LOWERED_THUMB_V1.step",
}

REPRESENTATIVE = "I2"
LEG_STRUCTURAL = 1.60
LEG_TANGENTIAL = 2.60
LEG_INSERTION = 3.20
RECEIVER_DEPTH = 2.40
RECEIVER_WALL = 1.20
RECEIVER_CLEARANCE = 0.25
LANDING_EXTENSION = 0.60
LANDING_THICKNESS = 0.60
PANEL_THICKNESS = 1.60
PANEL_BASE_GAP = 0.30
LOCATING_GAP = 0.18
CLEARANCE_GAP = 0.35
REST_GAP = 0.08
T_CLICK = 0.33
T_DESIGN_FULL = 0.38
T_STOP = 0.38

PROTECTED = [
    ROOT / "build123d_workbench/finger_controls_v2.py",
    ROOT / "build123d_workbench/n1_production_intent_mechanism.py",
    ROOT / "build123d_workbench/n2_production_intent_mechanism.py",
    ROOT / "build123d_workbench/i2_i3_production_intent_mechanism.py",
    ROOT / "build123d_workbench/i4_m3_production_intent_mechanisms.py",
    ROOT / "build123d_workbench/m4_n3_production_intent_mechanism.py",
    ROOT / "build123d_workbench/open_frame_glued_switch_harness_candidate.py",
    ROOT / "build123d_workbench/slot_anchored_harness_captive_pusher_audit.py",
    ROOT / "docs/76_source_faithful_button_mechanism_and_fdm_rebase_audit.md",
    ROOT / "docs/77_open_frame_glued_switch_harness_candidate.md",
    ROOT / "docs/78_slot_anchored_harness_and_captive_pusher_audit.md",
    ROOT / "build123d_workbench/out/button_fdm_coupon/BUTTON_FDM_TEST_COUPON.step",
    *SHELL_STEP.values(),
]

C = {
    "original": (190, 204, 217), "actual": (228, 91, 99), "seat": (55, 154, 220),
    "legU": (108, 207, 246), "legV": (157, 112, 219), "collar": (245, 180, 65),
    "receiver": (69, 184, 132), "panel": (112, 211, 163), "shell": (111, 132, 151),
    "terminal": (214, 223, 231), "guide": (65, 164, 224), "pusher": (245, 181, 65),
    "clip": (218, 225, 234), "stop": (239, 81, 84), "glue": (245, 131, 61),
}
FOOTER = "AUDIT/CANDIDATE ONLY | docs/77+78 PRESERVED AS SUPERSEDED ALTERNATIVES | PRODUCTION MODIFICATION = 0"


def local_box(u: float, v: float, w: float, u0: float, v0: float, w0: float, label: str) -> Shape:
    result = Box(u, v, w, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(u0, v0, w0)))
    result.label = label
    return result


def local_cylinder(diameter: float, w0: float, w1: float, label: str) -> Shape:
    result = Cylinder(diameter / 2, w1 - w0, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, w0)))
    result.label = label
    return result


def volume(shape: Shape | None) -> float:
    return 0.0 if shape is None or not shape.solids() else float(shape.volume)


def bounds(shape: Shape) -> tuple[np.ndarray, np.ndarray]:
    box = shape.bounding_box()
    return np.asarray((box.min.X, box.min.Y, box.min.Z), float), np.asarray((box.max.X, box.max.Y, box.max.Z), float)


def datum_location(datum, front: float) -> Location:
    return Plane(origin=point_at(datum, front + BODY_H), x_dir=datum.switch_u, z_dir=datum.axis).location


def placed(shape: Shape, datum, front: float, label: str) -> Shape:
    result = datum_location(datum, front) * shape; result.label = label
    return result


def moved(shape: Shape, xyz: Iterable[float], label: str) -> Shape:
    x, y, z = map(float, xyz); result = shape.moved(Location(Vector(x, y, z))); result.label = label; return result


def edge_centers() -> dict[str, tuple[float, float]]:
    u_loc = BODY_U / 2 + LOCATING_GAP + LEG_STRUCTURAL / 2
    u_clr = BODY_U / 2 + CLEARANCE_GAP + LEG_STRUCTURAL / 2
    v_loc = BODY_V / 2 + LOCATING_GAP + LEG_STRUCTURAL / 2
    v_clr = BODY_V / 2 + CLEARANCE_GAP + LEG_STRUCTURAL / 2
    return {"+U": (u_clr, 0), "-U": (-u_loc, 0), "+V": (0, v_clr), "-V": (0, -v_loc)}


def receiver_layout(name: str) -> dict[str, dict[str, object]]:
    upper = edge_centers()
    if name != "N2":
        receiver = dict(upper)
        support = {
            "+U": (upper["+U"][0] + 2.0, 0), "-U": (upper["-U"][0] - 2.0, 0),
            "+V": (0, upper["+V"][1] + 2.0), "-V": (0, upper["-V"][1] - 2.0),
        }
    else:
        # All receiver openings and shell-support panels stay on JfD (global
        # -X / local -U).  Four short/broad rear transitions retain the four
        # distinct edge contacts; only +U needs the longer compensated route.
        receiver = {"+U": (-3.30, 0), "-U": (-7.00, 0), "+V": (-4.20, 5.00), "-V": (-4.20, -5.00)}
        support = {"+U": (-6.00, -2.00), "-U": (-6.00, 2.50), "+V": (-6.00, 6.20), "-V": (-6.00, -6.20)}
    result = {}
    for edge in ("+U", "-U", "+V", "-V"):
        if edge.endswith("U"):
            leg_u, leg_v = LEG_STRUCTURAL, LEG_TANGENTIAL
        else:
            leg_u, leg_v = LEG_TANGENTIAL, LEG_STRUCTURAL
        result[edge] = {"upperUV": upper[edge], "receiverUV": receiver[edge], "supportUV": support[edge],
                        "legU": leg_u, "legV": leg_v}
    return result


def four_edge_leg_harness(name: str = "I2", receiver_clearance: float = RECEIVER_CLEARANCE) -> dict[str, Shape]:
    layout = receiver_layout(name)
    seat_u = local_box(9.80, 1.60, 1.20, 0, 0, -1.20, "MAIN_BODY_BOTTOM_U_SEAT")
    seat_v = local_box(1.60, 9.80, 1.20, 0, 0, -1.20, "MAIN_BODY_BOTTOM_V_SEAT")
    seat = seat_u.fuse(seat_v).clean(); seat.label = "MAIN_BODY_BOTTOM_OPEN_CROSS_DATUM"
    core = seat
    upper_parts: list[Shape] = []; lower_parts: list[Shape] = []; transitions: list[Shape] = []; collars: list[Shape] = []
    upper_by_edge: dict[str, Shape] = {}
    path_rows = []
    for edge, row in layout.items():
        uu, uv = map(float, row["upperUV"]); ru, rv = map(float, row["receiverUV"])
        leg_u, leg_v = float(row["legU"]), float(row["legV"])
        upper = local_box(leg_u, leg_v, 3.20, uu, uv, -0.20, f"EDGE_{edge}_WRAPPING_UPPER_LEG")
        lower = local_box(leg_u, leg_v, LEG_INSERTION, ru, rv, -4.40, f"EDGE_{edge}_RECEIVER_INSERT_LEG")
        transition = oriented_box_between((ru, rv, -1.20), (uu, uv, 0.0), (1, 0, 0),
                                          leg_u if edge.endswith("V") else leg_v,
                                          LEG_STRUCTURAL, label=f"EDGE_{edge}_BROAD_ROOT_TRANSITION")
        collar = local_box(leg_u + 2 * LANDING_EXTENSION, leg_v + 2 * LANDING_EXTENSION,
                           LANDING_THICKNESS, ru, rv, -1.20, f"EDGE_{edge}_MINIMAL_RECEIVER_LANDING")
        core = core.fuse(upper).fuse(lower).fuse(transition).fuse(collar)
        upper_parts.append(upper); upper_by_edge[edge] = upper
        lower_parts.append(lower); transitions.append(transition); collars.append(collar)
        path_len = float(np.linalg.norm(np.asarray((uu - ru, uv - rv, 1.20))))
        path_rows.append({"edge": edge, "transitionLengthMm": path_len, "sectionAreaMm2": leg_u * leg_v,
                          "stiffnessProxy": leg_u * leg_v / max(path_len, 1.20)})
    core = core.clean(); core.label = f"{name}_FOUR_EDGE_LEG_STRUCTURAL_HARNESS"
    total_k = sum(row["stiffnessProxy"] for row in path_rows)
    for row in path_rows:
        row["nominalLoadSharePercent"] = 100 * row["stiffnessProxy"] / total_k
    body = local_box(BODY_U, BODY_V, BODY_H, 0, 0, 0, "ITS1105_MEASURED_BODY")
    actuator = local_cylinder(ACT_D, BODY_H, TOTAL_H, "ITS1105_MEASURED_ACTUATOR")
    lug_parts = []
    for u0 in (-2.25, 2.25):
        for v0 in (-2.25, 2.25):
            lug_parts.append(local_cylinder(1.40, BODY_H, BODY_H + 0.80, "CORNER_FEATURE_FREE_KEEP_OUT").moved(
                Location(Vector(u0, v0, 0))))
    return {"core": core, "seat": seat, "upperLegs": Compound(children=upper_parts),
            "lowerLegs": Compound(children=lower_parts), "transitions": Compound(children=transitions),
            "collars": Compound(children=collars), "body": body, "actuator": actuator,
            "lugs": Compound(children=lug_parts), "layout": layout, "loadDistribution": path_rows,
            "upperByEdge": upper_by_edge,
            "family": "N2 SAME-HALF FOUR-RECEIVER ROUTE" if name == "N2" else "STANDARD FOUR-EDGE-LEG"}


class ExactShellSampler:
    def __init__(self, shape: Shape):
        self.shape = shape
        self.intersector = IntCurvesFace_ShapeIntersector()
        self.intersector.Load(shape.wrapped, 1.0e-7)

    def inner_depth(self, datum, u0: float, v0: float, maximum: float = 12.0) -> float | None:
        axis, u, v = unit(datum.axis), unit(datum.switch_u), unit(datum.switch_v)
        # A tangent-plane offset can start inside a curved shell.  Start a
        # fixed 3 mm outside along +W so the first exact crossing is the outer
        # face and the second is the inner face, then report depth from the
        # original frozen datum plane.
        outward = 3.0
        origin = np.asarray(datum.center, float) + axis * outward + u * u0 + v * v0
        line = gp_Lin(gp_Pnt(*map(float, origin)), gp_Dir(*map(float, -axis)))
        try:
            self.intersector.Perform(line, 0.0, maximum + outward)
        except Exception:
            self.intersector = IntCurvesFace_ShapeIntersector()
            self.intersector.Load(self.shape.wrapped, 1.0e-7)
            try:
                self.intersector.Perform(line, 0.0, maximum + outward)
            except Exception:
                return None
        hits = sorted(float(self.intersector.WParameter(i)) - outward for i in range(1, self.intersector.NbPnt() + 1)
                      if -2.5 < float(self.intersector.WParameter(i)) - outward < maximum)
        unique: list[float] = []
        for value in hits:
            if not unique_or_close(value, unique):
                unique.append(value)
        return unique[1] if len(unique) >= 2 else None


def unique_or_close(value: float, values: list[float]) -> bool:
    return bool(values and abs(value - values[-1]) <= 0.02)


def exact_depth_grid(sampler: ExactShellSampler, datum, support_uv: tuple[float, float],
                     size_u: float, size_v: float) -> dict[str, object]:
    uc, vc = support_uv
    us = np.linspace(uc - size_u / 2, uc + size_u / 2, 3)
    vs = np.linspace(vc - size_v / 2, vc + size_v / 2, 3)
    depths = np.full((3, 3), np.nan)
    for j, vv in enumerate(vs):
        for i, uu in enumerate(us):
            value = sampler.inner_depth(datum, float(uu), float(vv))
            if value is not None:
                depths[j, i] = value
    missing_initial = int(np.isnan(depths).sum())
    if np.isfinite(depths).sum() < 4:
        # Small deterministic exact-BRep fallback search around the local pad,
        # not a brute-force shell scan.
        fallback = []
        for du in (-1.0, 0.0, 1.0):
            for dv in (-1.0, 0.0, 1.0):
                value = sampler.inner_depth(datum, uc + du, vc + dv)
                if value is not None:
                    fallback.append(value)
        if not fallback:
            raise RuntimeError("exact BRep inner-surface intersections unavailable at receiver panel")
        depths[np.isnan(depths)] = float(np.median(fallback))
    else:
        finite = np.argwhere(np.isfinite(depths))
        for j, i in np.argwhere(np.isnan(depths)):
            nearest = finite[np.argmin(np.sum((finite - np.asarray((j, i))) ** 2, axis=1))]
            depths[j, i] = depths[tuple(nearest)]

    # Validate between the construction nodes with an exact 5x5 BRep sample.
    test_us = np.linspace(us[0], us[-1], 5); test_vs = np.linspace(vs[0], vs[-1], 5)
    residuals = []
    for vv in test_vs:
        row_interp = np.asarray([np.interp(vv, vs, depths[:, i]) for i in range(3)])
        for uu in test_us:
            actual = sampler.inner_depth(datum, float(uu), float(vv))
            if actual is not None:
                predicted = float(np.interp(uu, us, row_interp))
                residuals.append(predicted - actual)
    correction = max(0.0, -min(residuals, default=0.0) + 0.20 - PANEL_BASE_GAP)
    applied_gap = PANEL_BASE_GAP + correction
    gaps = [applied_gap + residual for residual in residuals]
    area = size_u * size_v
    unsupported = area * (sum(gap > 1.0 for gap in gaps) / max(len(gaps), 1))
    return {"us": us, "vs": vs, "depths": depths, "missingConstructionNodes": missing_initial,
            "exactValidationSamples": len(gaps), "appliedGapMm": applied_gap,
            "minimumGapMm": min(gaps, default=applied_gap), "maximumGapMm": max(gaps, default=applied_gap),
            "unsupportedAreaProxyGt1mmMm2": unsupported, "planarAreaMm2": area}


def panel_solid(grid: dict[str, object], seat_depth: float, label: str) -> Shape:
    us, vs, depths = np.asarray(grid["us"]), np.asarray(grid["vs"]), np.asarray(grid["depths"])
    gap = float(grid["appliedGapMm"])
    top = np.zeros((3, 3, 3), float)
    for j, vv in enumerate(vs):
        for i, uu in enumerate(us):
            top[j, i] = (uu, vv, seat_depth - depths[j, i] - gap)
    bottom = top.copy(); bottom[:, :, 2] -= PANEL_THICKNESS
    tris = []
    for j in range(2):
        for i in range(2):
            a, b, c, d = top[j, i], top[j, i + 1], top[j + 1, i + 1], top[j + 1, i]
            aa, bb, cc, dd = bottom[j, i], bottom[j, i + 1], bottom[j + 1, i + 1], bottom[j + 1, i]
            tris.extend(((a, b, c), (a, c, d), (aa, cc, bb), (aa, dd, cc)))
    boundaries = [
        [(0, i) for i in range(3)], [(2, i) for i in range(2, -1, -1)],
        [(j, 0) for j in range(2, -1, -1)], [(j, 2) for j in range(3)],
    ]
    for boundary in boundaries:
        for p, q in zip(boundary[:-1], boundary[1:]):
            a, b = top[p], top[q]; aa, bb = bottom[p], bottom[q]
            tris.extend(((a, aa, bb), (a, bb, b)))
    result = mesh_to_faceted_solid(np.asarray(tris, float)); result.label = label
    return result


def receiver_walls(edge: str, ru: float, rv: float, leg_u: float, leg_v: float,
                   clearance: float, label: str) -> tuple[Shape, Shape, float, float]:
    """Two structural walls form a small tangentially open receiver slot.

    A closed rectangular boss would occupy the four terminal corners.  The
    opposed radial walls control the leg while the four-receiver pattern
    controls roll/rocking; open tangent ends preserve solder/wire access.
    """
    slot_u, slot_v = leg_u + 2 * clearance, leg_v + 2 * clearance
    walls: list[Shape] = []
    if edge.endswith("U"):
        for sign in (-1, 1):
            walls.append(local_box(RECEIVER_WALL, slot_v, RECEIVER_DEPTH,
                                   ru + sign * (slot_u / 2 + RECEIVER_WALL / 2), rv, -3.60,
                                   f"{label}_{'INNER' if sign < 0 else 'OUTER'}_U_WALL"))
    else:
        for sign in (-1, 1):
            walls.append(local_box(slot_u, RECEIVER_WALL, RECEIVER_DEPTH,
                                   ru, rv + sign * (slot_v / 2 + RECEIVER_WALL / 2), -3.60,
                                   f"{label}_{'INNER' if sign < 0 else 'OUTER'}_V_WALL"))
    compound = Compound(children=walls, label=label)
    slot = local_box(slot_u, slot_v, RECEIVER_DEPTH + 0.40, ru, rv, -3.80, f"{label}_OPEN_SLOT_REFERENCE")
    return compound, slot, slot_u, slot_v


def four_receiver_inner_housing(name: str, sampler: ExactShellSampler, datum, front: float,
                                clearance: float = RECEIVER_CLEARANCE) -> tuple[dict[str, Shape], dict[str, object]]:
    layout = receiver_layout(name); seat_depth = front + BODY_H
    panels: list[Shape] = []; bosses: list[Shape] = []; slots: list[Shape] = []; struts: list[Shape] = []
    struts_by_edge: dict[str, Shape] = {}
    panel_metrics = []; receiver_metrics = []
    for edge, row in layout.items():
        ru, rv = map(float, row["receiverUV"]); su, sv = map(float, row["supportUV"])
        leg_u, leg_v = float(row["legU"]), float(row["legV"])
        panel_u = 3.2 if edge.endswith("U") else 4.2
        panel_v = 4.2 if edge.endswith("U") else 3.2
        grid = exact_depth_grid(sampler, datum, (su, sv), panel_u, panel_v)
        panel = panel_solid(grid, seat_depth, f"{name}_{edge}_EXACT_BREP_DERIVED_CONFORMAL_PANEL")
        panels.append(panel)
        panel_metrics.append({"edge": edge, **{k: v for k, v in grid.items() if k not in ("us", "vs", "depths")}})

        boss, slot, slot_u, slot_v = receiver_walls(
            edge, ru, rv, leg_u, leg_v, clearance, f"{name}_{edge}_TWIN_WALL_RECEIVER")
        bosses.append(boss); slots.append(slot)

        depth_center = sampler.inner_depth(datum, su, sv)
        if depth_center is None:
            depth_center = float(np.median(grid["depths"]))
        panel_inner_w = seat_depth - depth_center - float(grid["appliedGapMm"]) - PANEL_THICKNESS
        radial = np.asarray((su - ru, sv - rv), float); radial /= max(np.linalg.norm(radial), 1.0e-9)
        p0 = (ru + radial[0] * 1.40, rv + radial[1] * 1.40, -1.20)
        p1 = (su, sv, panel_inner_w)
        # Keep the load strut at the same robust 2.6 mm tangential width as
        # the edge leg.  Broadening this to 2.8 mm only grazes N2/TNN and adds
        # no required section thickness in the press direction.
        tangent_width = 2.40 if name == "N2" and edge == "+U" else LEG_TANGENTIAL
        strut = oriented_box_between(p0, p1, (1, 0, 0), tangent_width, LEG_STRUCTURAL,
                                     label=f"{name}_{edge}_OUTBOARD_RECEIVER_LOAD_STRUT")
        struts.append(strut); struts_by_edge[edge] = strut
        receiver_metrics.append({"edge": edge, "centerLocalUVmm": [ru, rv], "slotUmm": slot_u,
                                 "slotVmm": slot_v, "depthWmm": RECEIVER_DEPTH,
                                 "clearancePerSideMm": clearance, "minimumWallMm": RECEIVER_WALL,
                                 "insertionDirection": "local -W", "supportLocalUVmm": [su, sv],
                                 "receiverShape": "two opposed structural walls; tangent ends open",
                                 "loadStrutTangentialWidthMm": tangent_width,
                                 "loadStrutPressThicknessMm": LEG_STRUCTURAL})
    housing = Compound(children=[*panels, *bosses, *struts], label=f"{name}_FOUR_RECEIVER_LOCAL_CONFORMAL_INNER_HOUSING")
    metrics = {
        "authority": "exact frozen-shell BRep line/face intersections; faceted ruled audit panels",
        "panelCount": len(panels), "panels": panel_metrics, "receivers": receiver_metrics,
        "minimumGapMm": min(row["minimumGapMm"] for row in panel_metrics),
        "maximumGapMm": max(row["maximumGapMm"] for row in panel_metrics),
        "localThicknessMm": PANEL_THICKNESS,
        "unsupportedAreaProxyGt1mmMm2": sum(row["unsupportedAreaProxyGt1mmMm2"] for row in panel_metrics),
        "totalPanelPlanarAreaMm2": sum(row["planarAreaMm2"] for row in panel_metrics),
    }
    return {"housing": housing, "panels": Compound(children=panels), "bosses": Compound(children=bosses),
            "slots": Compound(children=slots), "struts": Compound(children=struts),
            "strutsByEdge": struts_by_edge}, metrics


def glue_regions(name: str) -> Shape:
    beads = []
    for edge, row in receiver_layout(name).items():
        ru, rv = map(float, row["receiverUV"]); leg_u, leg_v = float(row["legU"]), float(row["legV"])
        if edge.endswith("U"):
            beads.extend([local_box(0.35, leg_v + 0.5, 0.45, ru - leg_u/2 - 0.18, rv, -4.05, f"{edge}_GLUE_A"),
                          local_box(0.35, leg_v + 0.5, 0.45, ru + leg_u/2 + 0.18, rv, -4.05, f"{edge}_GLUE_B")])
        else:
            beads.extend([local_box(leg_u + 0.5, 0.35, 0.45, ru, rv - leg_v/2 - 0.18, -4.05, f"{edge}_GLUE_A"),
                          local_box(leg_u + 0.5, 0.35, 0.45, ru, rv + leg_v/2 + 0.18, -4.05, f"{edge}_GLUE_B")])
    return Compound(children=beads, label=f"{name}_RECEIVER_EXIT_SECONDARY_ADHESIVE")


def terminal_access(harness: dict[str, Shape], housing: dict[str, Shape]) -> dict[str, object]:
    components = {"harnessCore": harness["core"], "receiverWalls": housing["bosses"],
                  "loadStruts": housing["struts"]}
    obstacle = Compound(children=list(components.values()))
    rows = {}
    for name, proxy in terminal_proxies().items():
        pen = volume(proxy & obstacle)
        rows[name] = {"penetrationMm3": pen, "open": pen <= 1.0e-6,
                      "componentPenetrationMm3": {
                          component: volume(proxy & shape) for component, shape in components.items()
                      }, "strutPenetrationMm3": {
                          edge: volume(proxy & shape) for edge, shape in housing["strutsByEdge"].items()
                      }}
    return {"terminals": rows, "allOpen": all(row["open"] for row in rows.values())}


def corner_clearance(harness: dict[str, Shape]) -> dict[str, object]:
    distance = float(harness["upperLegs"].distance_to(harness["lugs"]))
    penetration = volume(harness["upperLegs"] & harness["lugs"])
    return {"minimumDistanceMm": distance, "penetrationMm3": penetration,
            "clear": penetration <= 1.0e-6, "cornerFeaturesUsedForLocation": False}


def local_candidate(name: str, sampler: ExactShellSampler, datum, front: float,
                    receiver_clearance: float = RECEIVER_CLEARANCE) -> tuple[dict[str, Shape], dict[str, object]]:
    harness = four_edge_leg_harness(name, receiver_clearance)
    housing, housing_metrics = four_receiver_inner_housing(name, sampler, datum, front, receiver_clearance)
    pusher = pusher_system(); glue = glue_regions(name)
    access = terminal_access(harness, housing); corner = corner_clearance(harness)
    assembly = Compound(children=[housing["housing"], harness["core"], harness["body"], harness["actuator"],
                                  pusher["guide"], pusher["pusher"], pusher["clip"], glue],
                        label=f"{name}_FOUR_EDGE_LEG_FULL_STACK_AUDIT_ONLY")
    metrics = {"housing": housing_metrics, "terminalAccess": access, "cornerClearance": corner,
               "family": harness["family"], "loadDistribution": harness["loadDistribution"]}
    return {**harness, **housing, **pusher, "glue": glue, "assembly": assembly}, metrics


def load_shell_breps() -> dict[str, Shape]:
    return {owner: import_step(path) for owner, path in SHELL_STEP.items()}


def virtual_all(datums: dict[str, object], shell_shapes: dict[str, Shape]) -> tuple[dict[str, object], dict[str, dict[str, Shape]]]:
    samplers = {owner: ExactShellSampler(shape) for owner, shape in shell_shapes.items()}
    rows: dict[str, object] = {}; world: dict[str, dict[str, Shape]] = {}
    for name in BUTTONS:
        datum = datums[name]; front = float(FROZEN_FRONT_DEPTHS[name])
        local, metrics = local_candidate(name, samplers[datum.owner], datum, front)
        keys = ("assembly", "housing", "panels", "bosses", "slots", "struts", "core", "seat", "upperLegs",
                "lowerLegs", "transitions", "collars", "body", "actuator", "lugs", "guide", "pusher", "clip", "stop", "glue")
        world[name] = {key: placed(local[key], datum, front, f"{name}_{key.upper()}") for key in keys}
        same_half = True
        if name == "N2":
            _, upper = bounds(world[name]["bosses"]); same_half = bool(upper[0] <= -0.20)
        load_values = [row["nominalLoadSharePercent"] for row in metrics["loadDistribution"]]
        rows[name] = {
            "family": metrics["family"], "legCount": 4, "legLocations": ["+U", "-U", "+V", "-V"],
            "vertexPosts": False, "receivers": metrics["housing"]["receivers"],
            "receiverSameOwnerHalf": same_half, "terminalAccess": metrics["terminalAccess"],
            "cornerClearance": metrics["cornerClearance"], "housing": metrics["housing"],
            "loadDistribution": metrics["loadDistribution"], "loadShareRangePercent": [min(load_values), max(load_values)],
            "pusherAxis": list(map(float, unit(datum.axis))), "guideRadialClearanceMm": 0.20,
            "clipLoadBearing": False, "adhesivePrimaryLoadBearing": False,
            "loadPath": "ITS BODY->OPEN CROSS->4 EDGE LEGS->4 MINIMAL LANDINGS->4 RECEIVERS/STRUTS->PANELS->SHELL",
            "seamVerdict": "CONDITIONAL / FOUR RECEIVERS JfD-SIDE" if name == "N2" else "NOT N2 SPECIAL",
            "verdict": "CONDITIONAL / PHYSICAL COUPON + LOCAL NEIGHBOR REVIEW",
        }
    neighbors = {}
    for i, left in enumerate(BUTTONS):
        for right in BUTTONS[i+1:]:
            gap, overlap = overlap_aabb(world[left]["assembly"], world[right]["assembly"])
            neighbors[f"{left}-{right}"] = {"aabbGapMm": gap, "aabbOverlapProxyMm3": overlap,
                                            "status": "LOCAL REVIEW" if overlap > 0 else "CLEAR"}
    for name in BUTTONS:
        related = [row for pair, row in neighbors.items() if name in pair.split("-")]
        rows[name]["neighborClearanceMm"] = min((row["aabbGapMm"] for row in related), default=999.0)
        rows[name]["neighborReview"] = any(row["status"] != "CLEAR" for row in related)
    return {"buttons": rows, "neighborPairs": neighbors}, world


def exact_local_shell_crop(shell: Shape, datum, front: float) -> Shape:
    crop_local = local_box(22, 22, 8.0, 0, 0, 2.0, "I2_EXACT_LOCAL_CROP_TOOL")
    crop_world = placed(crop_local, datum, front, "I2_EXACT_LOCAL_CROP_TOOL_WORLD")
    crop = (shell & crop_world).clean(); crop.label = "I2_FROZEN_SHELL_EXACT_LOCAL_BREP_CROP"
    return crop


def coupon_v3() -> Shape:
    children = []
    for i, clearance in enumerate((0.15, 0.25, 0.35)):
        harness = four_edge_leg_harness("I2", clearance)
        # Lightweight planar receiver coupon: exact shell panels are not needed
        # to calibrate leg/slot fit.
        bosses = []
        for edge, row in receiver_layout("I2").items():
            ru, rv = map(float, row["receiverUV"]); leg_u, leg_v = float(row["legU"]), float(row["legV"])
            boss, _, _, _ = receiver_walls(edge, ru, rv, leg_u, leg_v, clearance, "COUPON_TWIN_WALL_RECEIVER")
            bosses.append(boss)
        station = Compound(children=[harness["core"], harness["body"], *bosses], label=f"FOUR_LEG_CLEARANCE_{clearance:.2f}")
        children.append(moved(station, (i*20, 0, 4.4), f"COUPON_LEG_STATION_{i+1}"))
    p = pusher_system()
    for i, bore in enumerate((4.80, 5.00, 5.20)):
        guide_outer = local_cylinder(7.60, 7.20, 8.95, "COUPON_GUIDE")
        guide_bore = local_cylinder(bore, 7.10, 9.05, "COUPON_BORE")
        cavity = local_cylinder(6.80, 7.30 + (i-1)*0.04, 8.30, "COUPON_STOP_CAVITY")
        guide = (guide_outer-guide_bore-cavity).clean()
        children.append(moved(guide, (i*14, 24, 0), f"PUSHER_GUIDE_{bore:.2f}"))
        children.append(moved(p["pusher"], (i*14, 24, 0), f"PUSHER_IN_GUIDE_{bore:.2f}"))
        children.append(moved(p["clip"], (i*14, 24, 0), f"CLIP_MOCKUP_{bore:.2f}"))
    glue_plate = local_box(18, 12, 2.4, 48, 24, 0, "FOUR_RECEIVER_GLUE_ACCESS_PLATE")
    children.append(glue_plate)
    return Compound(children=children, label="FOUR_EDGE_LEG_RECEIVER_PUSHER_COUPON_V3")


def render_outputs(rep: dict[str, Shape], world: dict[str, dict[str, Shape]], datums: dict[str, object],
                   shell_crop: Shape, coupon: Shape) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True); outputs = []
    def render(filename, objects, title, subtitle, camera=(25,-34,22), fit=None, transparent=None, wireframes=None):
        path = RENDER/filename
        raster_scene(path, objects, title, subtitle, FOOTER, camera_offset=camera, fit_points=fit,
                     transparent_objects=transparent or [], wireframes=wireframes or [])
        outputs.append(relative(path))
    tri = lambda key: safe_triangles(rep[key])
    original = canonical_original_triangles(load_mesh("PushBtn"))
    actual = np.concatenate((tri("body"), tri("actuator"), tri("lugs")), axis=0)
    render("01_original_actual_its_detailed.png", [(original, C["original"])],
           "1 / ORIGINAL DETAILED PUSHBTN + MEASURED ITS AUTHORITY",
           "original 3,530-facet reference; measured 6.12×6.05×3.56 body overlay in red",
           camera=(22,-28,18), fit=np.vstack((original.reshape(-1,3),actual.reshape(-1,3))),
           transparent=[(actual, (*C["actual"],115))])
    render("02_four_edge_leg_harness_top.png", [(tri("seat"),C["seat"]),(tri("upperLegs"),C["legU"]),
                                                 (tri("body"),C["actual"])],
           "2 / FOUR-EDGE-LEG HARNESS — TOP", "+U / -U / +V / -V side-midpoint members; corners intentionally open",
           camera=(0.2,-0.5,30), fit=np.vstack((tri("core").reshape(-1,3),tri("body").reshape(-1,3))))
    render("03_four_edge_leg_harness_isometric.png", [(tri("core"),C["seat"]),(tri("collars"),C["collar"])],
           "3 / FOUR-EDGE-LEG HARNESS — ISOMETRIC", "minimal open cross + four side legs + four small landing collars")
    render("04_leg_plus_u_closeup.png", [(tri("body"),C["actual"]),(safe_triangles(rep["upperByEdge"]["+U"]),C["legU"])],
           "4 / LEG +U WRAPS THE +U SWITCH EDGE", "2.60 mm tangent width at side midpoint; not a corner post", camera=(16,-22,9))
    render("05_leg_plus_v_closeup.png", [(tri("body"),C["actual"]),(safe_triangles(rep["upperByEdge"]["+V"]),C["legV"])],
           "5 / LEG +V WRAPS THE +V SWITCH EDGE", "independent +V side member; all four vertices remain free", camera=(20,14,9))
    render("06_corner_feature_edge_leg_clearance.png", [(tri("upperLegs"),C["legU"]),(tri("lugs"),C["collar"]),
                                                         (tri("body"),C["actual"])],
           "6 / CORNER FEATURES VS EDGE-LEG CLEARANCE", "D1.40 audit keep-outs at ±2.25; no leg precision contact")
    term_objects=[(tri("core"),C["seat"]),(tri("body"),C["actual"])]
    term_objects += [(safe_triangles(shape),C["terminal"]) for shape in terminal_proxies().values()]
    render("07_terminal_corridors.png", term_objects, "7 / T1–T4 TERMINAL CORRIDORS",
           "mid-edge legs leave four corner terminal/solder/wire corridors open", camera=(22,-30,-8))
    render("08_its_inserted_into_harness.png", [(tri("core"),C["seat"]),(tri("body"),C["actual"]),(tri("actuator"),C["actual"])],
           "8 / MEASURED ITS INSERTED INTO FOUR-EDGE CAGE", "main-body bottom seats on open cross; no closed pocket")
    render("09_four_inner_housing_receivers.png", [(tri("bosses"),C["receiver"]),(tri("struts"),C["panel"]),
                                                    (tri("panels"),C["panel"])],
           "9 / FOUR SMALL INNER-HOUSING RECEIVERS", "one receiver per +U/-U/+V/-V leg; 1.20 mm walls; no switch pocket", camera=(35,-45,28))
    render("10_four_legs_inserted_into_inner_housing.png", [(tri("bosses"),C["receiver"]),(tri("lowerLegs"),C["legU"]),
                                                            (tri("collars"),C["collar"]),(tri("struts"),C["panel"])],
           "10 / FOUR LEGS INSERTED + MINIMAL LANDINGS SEATED",
           "0.60 mm local landing extension is the required press-direction stop; adhesive is secondary")
    shell_t=safe_triangles(shell_crop); shell_wire=[(triangle_wireframes(shell_t,150),(*C["shell"],95))]
    render("11_conformal_inner_housing_frozen_shell_section.png", [(tri("panels"),C["panel"])],
           "11 / EXACT LOCAL BREP-DERIVED INNER HOUSING VS FROZEN SHELL",
           "3×3 exact face-intersection panels; representative shell crop shown as wireframe",
           camera=(70,-95,55), wireframes=shell_wire)
    full=[(clip_half(rep[key]),col) for key,col in (("housing",C["panel"]),("core",C["seat"]),("body",C["actual"]),
          ("actuator",C["actual"]),("guide",C["guide"]),("pusher",C["pusher"]),("clip",C["clip"]))]
    render("12_full_button_pusher_harness_housing_stack.png", full, "12 / FULL BUTTON → PUSHER → ITS → FOUR-LEG → HOUSING STACK",
           "clip outside press load; four minimal landings feed four receivers and shell panels", camera=(24,-32,9))
    render("13_outer_shell_pusher_guide.png", [(tri("guide"),C["guide"]),(tri("pusher"),C["pusher"])],
           "13 / SMALL OUTER-SHELL PUSHER GUIDE", "D5.00 bore / D4.60 shaft / 0.20 radial clearance / frozen W axis")
    render("14_retaining_clip.png", [(tri("clip"),C["clip"]),(clip_w(rep["pusher"],6.3,7.45),C["pusher"])],
           "14 / E-CLIP REPRESENTATION — RETENTION ONLY", "press motion moves clip away from guide; printed groove remains coupon gate")
    render("15_independent_hard_stop.png", [(clip_half(rep["guide"]),C["guide"]),(clip_half(rep["pusher"]),C["pusher"]),
                                             (tri("stop"),C["stop"])],
           "15 / INDEPENDENT STRUCTURAL HARD STOP", "D6.40 pusher shoulder → D6.80 guide cavity floor at T_STOP=0.38")
    split=Box(0.20,80,80,align=(Align.CENTER,Align.CENTER,Align.CENTER)); n2=world["N2"]
    n2_fit=np.vstack((safe_triangles(n2["bosses"]).reshape(-1,3),safe_triangles(n2["lowerLegs"]).reshape(-1,3)))
    render("16_n2_seam_closeup.png", [(safe_triangles(n2["bosses"]),C["receiver"]),(safe_triangles(n2["lowerLegs"]),C["legU"]),
                                      (safe_triangles(n2["transitions"]),C["collar"])],
           "16 / N2 FOUR RECEIVERS ON JfD SAME HALF", "four edge contacts retained; rear transitions route every receiver to JfD",
           camera=(55,-75,45),fit=n2_fit,transparent=[(safe_triangles(split),(*C["stop"],55))])
    all_objs=[(safe_triangles(world[name]["assembly"]),C["legV"] if name=="N2" else C["seat"]) for name in BUTTONS]
    render("17_all8_virtual_placement.png",all_objs,"17 / ALL-EIGHT FOUR-EDGE-LEG VIRTUAL PLACEMENT",
           "standard harness at 7 positions; one N2 same-half receiver-route family",camera=(95,-140,95))
    exp=[(safe_triangles(moved(rep["housing"],(-20,0,0),"E_H")),C["panel"]),
         (safe_triangles(moved(rep["core"],(-7,0,0),"E_C")),C["seat"]),
         (safe_triangles(moved(rep["body"],(5,0,0),"E_S")),C["actual"]),
         (safe_triangles(moved(rep["pusher"],(16,0,0),"E_P")),C["pusher"]),
         (safe_triangles(moved(rep["guide"],(27,0,0),"E_G")),C["guide"])]
    render("18_exploded_assembly.png",exp,"18 / EXPLODED ASSEMBLY",
           "four-receiver conformal housing → four-leg cage → ITS → captive pusher → guide",camera=(48,-58,32))
    render("19_coupon_v3_preview.png",[(safe_triangles(coupon),C["receiver"])],
           "19 / FOUR-LEG / RECEIVER / PUSHER COUPON V3", "leg slots 0.15/0.25/0.35 per side + guide 4.80/5.00/5.20 + clip/stop",camera=(95,-115,75))
    return outputs


def report_text(data: dict[str, object]) -> str:
    rows=[]
    for name in BUTTONS:
        row=data["virtualFit"]["buttons"][name]
        load=f"{row['loadShareRangePercent'][0]:.1f}…{row['loadShareRangePercent'][1]:.1f}%"
        rows.append(f"| {name} | {row['family']} | {row['terminalAccess']['allOpen']} | {row['cornerClearance']['minimumDistanceMm']:.2f} | "
                    f"{row['housing']['minimumGapMm']:.2f}…{row['housing']['maximumGapMm']:.2f} | {row['housing']['unsupportedAreaProxyGt1mmMm2']:.2f} | "
                    f"{load} | {row['receiverSameOwnerHalf']} | {row['neighborClearanceMm']:.2f} | **{row['verdict']}** |")
    renders="\n".join(f"- [{Path(path).name}](../{path})" for path in data["outputs"]["renders"])
    return f"""# 79 — Four-edge-leg switch harness and captive pusher audit

HARNESS TYPE
= **FOUR-EDGE-LEG STRUCTURAL HARNESS**

LEG COUNT
= **4**

LEG LOCATIONS
= **+U / -U / +V / -V SWITCH EDGES**

VERTEX/CORNER POSTS
= **NO**

LARGE SWITCH POCKET
= **NO**

INNER-HOUSING RECEIVERS
= **4 SMALL HOLES/SLOTS**

HARNESS LOAD-BEARING
= **YES**

ADHESIVE PRIMARY LOAD-BEARING
= **NO**

PUSHER
= **SEPARATE D2.60 TIP / D4.60 SHAFT / D6.40 HARD-STOP SHOULDER**

CLIP
= **RETENTION ONLY**

HARD STOP
= **PUSHER SHOULDER → GUIDE CAVITY FLOOR; T_STOP=0.38 mm PROVISIONAL**

N2
= **CONDITIONAL — FOUR RECEIVERS ON JfD; REAR ROUTE FAMILY + PHYSICAL CLOSURE TEST REQUIRED**

8-POSITION VIRTUAL FIT
= **CONDITIONAL — ONE STANDARD CORE + ONE N2 REAR-ROUTE VARIANT**

FDM COUPON
= **READY**

EXTERIOR
= **PRESERVED**

JaD/JfD SPLIT
= **PRESERVED**

PRODUCTION MODIFICATION
= **0**

## 1. Final verdict

**B. FOUR-EDGE-LEG HARNESS WORKS WITH LIMITED LOCAL VARIANTS.**

Top view에서 네 structural member는 switch corner가 아니라 +U/−U/+V/−V side midpoint를 각각 감싼다.
docs/77 glue-foot와 docs/78 two-tongue/large-shoulder 후보는 삭제하지 않고 **SUPERSEDED ALTERNATIVE
ARCHITECTURES**로 보존했다.

```text
FINGER → PUSHER → ITS ACTUATOR/BODY
→ MAIN-BODY-BOTTOM OPEN CROSS
→ +U / -U / +V / -V EDGE LEGS
→ FOUR MINIMAL LANDINGS
→ FOUR SMALL RECEIVERS + OUTBOARD STRUTS
→ EXACT-BREP-DERIVED CONFORMAL PANELS
→ FROZEN OUTER SHELL
```

## 2. Why four minimal landings exist

Through receiver에 stop이 없으면 press 때 leg가 계속 −W로 밀려 들어가 adhesive가 primary reaction을 받는다.
따라서 각 leg root에 **0.60 mm extension × 0.60 mm thickness**의 작은 landing만 추가했다. 이는 docs/78의
broad shoulder/block가 아니며 receiver rim 위에서 insertion depth와 press reaction만 등록한다.

## 3. Switch fit and edge-leg geometry

| item | value |
|---|---:|
| measured body | 6.12 × 6.05 × 3.56 mm |
| leg structural thickness | 1.60 mm |
| side-wrap tangent width | 2.60 mm |
| locating-side gap −U/−V | 0.18 mm |
| clearance-side gap +U/+V | 0.35 mm |
| receiver insertion length | 3.20 mm |
| landing extension / thickness | 0.60 / 0.60 mm |
| corner feature minimum clearance | {data['representativeMetrics']['cornerClearance']['minimumDistanceMm']:.3f} mm |

Four corner features는 D1.40×0.80 UNKNOWN keep-out로 검사했고 locating/seating에 사용하지 않았다. Main-body
bottom만 open cross에 앉는다. Switch는 exterior 쪽에서 W축으로 삽입하며 all-wall press fit가 아니다.

## 4. Four receivers and conformal inner housing

| parameter | value |
|---|---:|
| receiver clearance | 0.25 mm/side |
| receiver depth | 2.40 mm |
| receiver wall | 1.20 mm |
| conformal panel thickness | 1.60 mm |
| exact validation | frozen STEP face intersections, 3×3 build + 5×5 check |
| all-eight min/max gap | {data['housingSummary']['minimumGapMm']:.3f}…{data['housingSummary']['maximumGapMm']:.3f} mm |
| unsupported area proxy >1 mm | {data['housingSummary']['unsupportedAreaProxyGt1mmMm2']:.2f} mm² |

Full shell boolean이나 mesh nearest-plane을 사용하지 않았다. Owner shell STEP의 exact face intersections로 local
inner depth를 얻고, representative I2에서는 exact 22×22×8 mm local BRep crop section을 별도로 생성했다.
Audit panel은 exact sample을 잇는 faceted ruled solid이며 production에서는 동일 BRep authority로 smooth
offset/loft와 fastening/merge detail을 확정해야 한다.

## 5. Terminal corridors and load distribution

Leg가 side midpoint에 있으므로 T1–T4 corner corridor가 열린다. CAD boolean proxy 결과 all-eight terminal
access는 **{data['allTerminalsOpen']}**다.

Standard family는 nominal 25%/leg다. N2 rear route는 transition section/length stiffness proxy로
{data['n2LoadShareRangePercent'][0]:.1f}…{data['n2LoadShareRangePercent'][1]:.1f}%/leg이며 한 leg가 majority를 받지 않는다.
이는 FEA가 아니라 sizing screen이며 coupon의 네 landing witness mark와 rocking 검사로 확인한다.

## 6. Pusher, clip and hard stop

| item | value |
|---|---:|
| guide / shaft | D5.00 / D4.60 mm |
| radial clearance | 0.20 mm/side |
| nominal angular clearance proxy | {data['pusher']['angularClearanceDeg']:.2f}° |
| groove root / shaft | D3.80 / D4.60 mm |
| remaining groove area | {100*data['pusher']['grooveAreaFraction']:.1f}% |
| clip press-load bearing | NO |
| T_CLICK / T_DESIGN_FULL / T_STOP | 0.33 / 0.38 / 0.38 mm provisional |

Clip은 outward anti-loss만 담당하고 press 때 guide에서 멀어진다. D6.40 pusher shoulder가 D6.80 guide cavity
floor에 닿아 destructive overtravel 전에 reaction을 받는다. Printed groove가 coupon에서 crack/whitening이면
metal pin 또는 separate retained collar로 바꾼다.

## 7. Per-button virtual propagation

| button | family | terminals open | corner gap | housing gap | unsupported >1 | load share | same-half | neighbor gap | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(rows)}

AABB overlap은 full collision verdict가 아니라 local receiver/strut trim screen이다. Frozen center/axis/exterior를
움직이지 않고 inner support만 다듬는다.

## 8. N2 seam

N2의 upper four edge contacts는 frozen switch sides에 유지한다. Receiver centers는 local
`(-3.30,0), (-7.00,0), (-4.20,+5.00), (-4.20,-5.00)`으로 route하여 네 boss 모두 JfD에 남긴다.
Harness는 양 shell half에 anchor하지 않는다. Rear transition 길이 보정으로 load-share proxy도 majority-free지만
JaD/JfD closure, T1/T3 wire, flex, adhesive tool access는 physical gate다.

## 9. Adhesive and assembly

Adhesive는 receiver rear exit에서 leg 양쪽에 도포해 pull-out/vibration/tolerance만 제어한다. Central switch,
pusher, actuator, corner terminal corridor는 keep-out이고 squeeze-out은 rearward open이다.

1. ITS를 exterior/W 방향에서 four-edge cage에 삽입해 bottom cross에 seat한다.
2. Pusher를 frozen outer guide에 넣고 내부에서 E/C clip을 설치한다.
3. Four legs를 four receivers에 동시에 삽입하고 네 landing flush를 확인한다.
4. Pusher/actuator center와 REST return을 확인한다.
5. Receiver rear exit에 secondary adhesive를 도포하고 squeeze-out을 제거한다.
6. T1–T4 검사/납땜/배선 후 REST/CLICK/FULL을 확인하고 shell을 닫는다.

## 10. Architecture comparison

| criterion | old pocket | docs/77 glue-foot | docs/78 two-tongue | new four-edge-leg |
|---|---|---|---|---|
| packaging | closed/bulky | low core, broad feet | two large blocks | **four small side receivers** |
| load path | pocket walls | adhesive-dependent | two shoulders | **four structural legs/landings** |
| switch locating | all-wall sensitive | three cheeks | common cage | **four side regions + bottom cross** |
| FDM robustness | pocket shrink risk | foot fit risk | large tabs robust | **1.60 legs + 1.20 receiver walls** |
| housing removal | high | none in audit | two large slots | **four small slots** |
| terminal access | restricted | open | locally open | **corner corridors open** |
| adhesive | low | primary | secondary | **secondary** |
| N2 | seam-sensitive | HOLD | same-half two slot | **same-half four receiver variant** |
| service | pocket extraction | adhesive-limited | pusher serviceable | pusher serviceable; harness adhesive-limited |

## 11. Coupon V3

Coupon includes four-leg cage/receiver stations at 0.15/0.25/0.35 mm per-side clearance, measured-body insertion,
anti-rock/landing witness checks, D4.80/D5.00/D5.20 guide bores, clip mockup, 0.34/0.38/0.42 stop comparison,
and rear adhesive access.

Required tests: ITS insertion, four landing flushness, leg insertion force, rocking, terminal tool access, adhesive
application/squeeze-out, pusher slide/return, 10× clip install/remove, pullout, hard-stop witness, 100-cycle actuation.

## 12. Required renders

{renders}

## 13. Outputs / preservation / STOP

- standard harness: `{data['outputs']['standardCoreStep']}`
- representative full stack: `{data['outputs']['representativeStep']}`
- all-eight virtual: `{data['outputs']['all8Step']}`
- coupon STEP/STL: `{data['outputs']['couponStep']}` / `{data['outputs']['couponStl']}`
- JSON: `{data['outputs']['json']}`
- docs/77 hash preserved: `{data['preservedHashes']['docs77']}`
- docs/78 hash preserved: `{data['preservedHashes']['docs78']}`
- protected inputs preserved: **{data['protectedInputsPreserved']}**
- production modification: **0**

**STOP.** Production shell, inner housing, pusher, harness에는 적용하지 않았다.
"""


def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True); RENDER.mkdir(parents=True,exist_ok=True)
    before={relative(path):sha256(path) for path in PROTECTED if path.exists()}
    # Export the pure common core before importing the large frozen STEP
    # shells.  OCCT's process-global STEP name table in this runtime reports a
    # malformed legacy name section after those imports and can reject an
    # otherwise valid later export.
    export_step(four_edge_leg_harness(REPRESENTATIVE)["core"],CORE_STEP)
    datums={name:datum for name,datum in load_all_datums().items() if name in BUTTONS}
    shell_shapes=load_shell_breps()
    virtual,world=virtual_all(datums,shell_shapes)
    rep_d=datums[REPRESENTATIVE]; rep_f=float(FROZEN_FRONT_DEPTHS[REPRESENTATIVE])
    rep,rep_metrics=local_candidate(REPRESENTATIVE,ExactShellSampler(shell_shapes[rep_d.owner]),rep_d,rep_f)
    shell_crop=exact_local_shell_crop(shell_shapes[rep_d.owner],rep_d,rep_f)
    coupon=coupon_v3()
    export_step(rep["assembly"],REP_STEP)
    export_step(Compound(children=[world[name]["assembly"] for name in BUTTONS],label="ALL8_FOUR_EDGE_LEG_VIRTUAL_AUDIT_ONLY"),ALL8_STEP)
    export_step(coupon,COUPON_STEP); export_stl(coupon,COUPON_STL,tolerance=0.04,angular_tolerance=0.10)
    renders=render_outputs(rep,world,datums,shell_crop,coupon)
    buttons=virtual["buttons"]
    gap_min=min(buttons[n]["housing"]["minimumGapMm"] for n in BUTTONS)
    gap_max=max(buttons[n]["housing"]["maximumGapMm"] for n in BUTTONS)
    unsupported=sum(buttons[n]["housing"]["unsupportedAreaProxyGt1mmMm2"] for n in BUTTONS)
    n2_load=buttons["N2"]["loadShareRangePercent"]
    pusher_base=pusher_system()
    shaft_area=math.pi*4.60**2/4; groove_area=math.pi*3.80**2/4
    data={
        "schema":"onegrip.four_edge_leg_harness_captive_pusher_audit.v1",
        "generatedUtc":datetime.now(timezone.utc).isoformat(),
        "mode":"AUDIT ONLY / EXACT LOCAL BREP RAYS / LIGHTWEIGHT PAIRWISE / PRODUCTION EDIT 0",
        "finalVerdict":"B / FOUR-EDGE-LEG HARNESS WORKS WITH LIMITED LOCAL VARIANTS",
        "supersededAlternatives":["docs/77 conformal glue-foot","docs/78 broad two-tongue/shoulder"],
        "freeze":{"centersAxes":"PRESERVED","visibleLayout":"PRESERVED","exterior":"PRESERVED",
                  "maximumLoweredThumb":"PRESERVED","JaDJfDSplit":"PRESERVED","productionModificationCount":0},
        "representative":{"button":REPRESENTATIVE,"reason":"non-seam-special curved JfD; exact local crop; all terminals"},
        "harness":{"type":"FOUR-EDGE-LEG STRUCTURAL HARNESS","legCount":4,"legLocations":["+U","-U","+V","-V"],
                   "vertexPosts":False,"largePocket":False,"legThicknessMm":LEG_STRUCTURAL,
                   "legTangentWidthMm":LEG_TANGENTIAL,"receiverClearancePerSideMm":RECEIVER_CLEARANCE,
                   "receiverDepthMm":RECEIVER_DEPTH,"receiverWallMm":RECEIVER_WALL,
                   "landingExtensionMm":LANDING_EXTENSION,"landingThicknessMm":LANDING_THICKNESS,
                   "familyCount":2,"families":["STANDARD FOUR-EDGE-LEG (7)","N2 SAME-HALF REAR ROUTE (1)"]},
        "representativeMetrics":rep_metrics,
        "housingSummary":{"authority":"exact frozen STEP face intersections","minimumGapMm":gap_min,"maximumGapMm":gap_max,
                          "unsupportedAreaProxyGt1mmMm2":unsupported,"localThicknessMm":PANEL_THICKNESS,
                          "representativeExactCropSolids":len(shell_crop.solids())},
        "pusher":{"tipDiameterMm":2.60,"shaftDiameterMm":4.60,"guideDiameterMm":5.00,"radialClearanceMm":0.20,
                  "angularClearanceDeg":math.degrees(math.atan(0.20/1.75)),"grooveRootDiameterMm":3.80,
                  "grooveAreaFraction":groove_area/shaft_area,"clipLoadBearing":False,
                  "hardStop":"D6.40 shoulder -> D6.80 guide cavity floor","T_CLICK":T_CLICK,
                  "T_DESIGN_FULL":T_DESIGN_FULL,"T_STOP":T_STOP},
        "adhesive":{"primaryLoadBearing":False,"roles":["pullout","anti-vibration","assembly retention","tolerance fill"],
                    "access":"receiver rear exits","keepOut":"ITS/actuator/pusher/four corner terminal corridors"},
        "virtualFit":virtual,"n2LoadShareRangePercent":n2_load,
        "allTerminalsOpen":all(buttons[n]["terminalAccess"]["allOpen"] for n in BUTTONS),
        "couponV3":{"legSlotClearanceVariantsPerSideMm":[0.15,0.25,0.35],"guideBoreVariantsMm":[4.80,5.00,5.20],
                    "stopVariantsMm":[0.34,0.38,0.42],"status":"READY FOR P1S PHYSICAL TEST"},
        "outputs":{"standardCoreStep":relative(CORE_STEP),"representativeStep":relative(REP_STEP),"all8Step":relative(ALL8_STEP),
                   "couponStep":relative(COUPON_STEP),"couponStl":relative(COUPON_STL),"json":relative(JSON_PATH),
                   "report":relative(REPORT),"renders":renders},
    }
    after={relative(path):sha256(path) for path in PROTECTED if path.exists()}
    data["inputHashesBefore"]=before; data["inputHashesAfter"]=after; data["protectedInputsPreserved"]=before==after
    data["preservedHashes"]={"docs77":after.get("docs/77_open_frame_glued_switch_harness_candidate.md"),
                             "docs78":after.get("docs/78_slot_anchored_harness_and_captive_pusher_audit.md")}
    JSON_PATH.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    REPORT.write_text(report_text(data),encoding="utf-8")
    print(json.dumps({"verdict":data["finalVerdict"],"buttons":len(buttons),"renders":len(renders),
                      "allTerminalsOpen":data["allTerminalsOpen"],"N2SameHalf":buttons["N2"]["receiverSameOwnerHalf"],
                      "cornerClear":all(buttons[n]["cornerClearance"]["clear"] for n in BUTTONS),
                      "protectedInputsPreserved":data["protectedInputsPreserved"],"report":relative(REPORT)},indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
