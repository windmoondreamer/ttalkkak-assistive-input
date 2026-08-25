"""Diagnostic-only failure classification for the six unresolved docs/91 legs.

This module intentionally creates no solution geometry.  It replays the exact
docs/91 best-failure rays, measures the nearest continuous shell material for
the two incomplete-footprint cases, and renders one section per failed leg.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
from build123d import Compound, Shape, import_step
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
from PIL import ImageDraw

from . import eight_button_four_edge_batch_propagation_screening as d90
from . import i2_detailed_pushbtn_manufacturing_robust_audit as doc84
from . import option_c_local_exact_prototype as render_module
from . import seven_unresolved_leg_root_shell_target_rescue_audit as d91
from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler, SHELL_STEP
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, opening_cutter, unit
from .four_edge_leg_harness_captive_pusher_audit import local_box
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import ROOT, relative
from .option_c_local_exact_prototype import safe_edge_lines, safe_triangles


DOC91_JSON = d91.JSON_PATH
OUT = ROOT / "build123d_workbench/out/six_failed_leg_shell_landing_failure_mode_diagnostic_audit"
RENDER = ROOT / "renders/six_failed_leg_shell_landing_failure_mode_diagnostic_audit"
REPORT = ROOT / "docs/92_six_failed_leg_shell_landing_failure_mode_diagnostic_audit.md"
JSON_PATH = OUT / "six_failed_leg_shell_landing_failure_mode_diagnostic_audit.json"

TARGETS = (("N2", "+U"), ("N2", "+V"), ("N2", "-V"),
           ("I3", "+U"), ("I3", "-U"), ("I4", "+U"))
GROUP_A = {("N2", "+U"), ("I3", "+U")}
GROUP_B = set(TARGETS) - GROUP_A
BLIND_DEPTH = 1.20
REMAINING_TARGET = 1.20
SLOT_TANGENT = 1.90
SLOT_STRUCTURAL = 1.60
REINFORCEMENT_MARGIN = 0.60
REINFORCEMENT_DIMS = (SLOT_TANGENT + 2 * REINFORCEMENT_MARGIN,
                      SLOT_STRUCTURAL + 2 * REINFORCEMENT_MARGIN)
REINFORCEMENT_AREA = REINFORCEMENT_DIMS[0] * REINFORCEMENT_DIMS[1]
EPS = 1.0e-6
FOOTER = "6-LEG FAILURE DIAGNOSTIC ONLY | docs/91 AUTHORITY | NO SOLUTION GEOMETRY | PRODUCTION 0"
COL = {"owner": (111, 132, 151), "opposite": (72, 173, 208), "probe": (236, 84, 94),
       "axis": (250, 207, 81), "good": (56, 192, 137), "void": (176, 110, 220)}


def xyz(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(map(float, value))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def protected_files() -> list[Path]:
    rows = set(d91.protected_files())
    rows.update({d91.REPORT, d91.JSON_PATH,
                 ROOT / "build123d_workbench/seven_unresolved_leg_root_shell_target_rescue_audit.py"})
    for folder in (d91.OUT, d91.RENDER):
        if folder.exists():
            rows.update(path for path in folder.rglob("*") if path.is_file())
    return sorted(path for path in rows if path.exists())


def hashes(paths: list[Path]) -> dict[str, str]:
    return {relative(path): sha256(path) for path in paths}


def key_name(button: str, edge: str) -> str:
    return f"{button} {edge}"


def footprint_offsets() -> tuple[tuple[float, float], ...]:
    return ((-SLOT_TANGENT / 2, -SLOT_STRUCTURAL / 2),
            (-SLOT_TANGENT / 2, SLOT_STRUCTURAL / 2),
            (SLOT_TANGENT / 2, -SLOT_STRUCTURAL / 2),
            (SLOT_TANGENT / 2, SLOT_STRUCTURAL / 2),
            (-SLOT_TANGENT / 2, 0.0), (SLOT_TANGENT / 2, 0.0),
            (0.0, -SLOT_STRUCTURAL / 2), (0.0, SLOT_STRUCTURAL / 2), (0.0, 0.0))


def reference_row(edge: str, best: dict[str, object] | None) -> dict[str, object]:
    if best:
        root = np.asarray(best["rootLocalUVWmm"], float)
        direction = unit(best["directionLocal"])
        tangent = unit(d90.tangent_axis(edge) - direction * float(np.dot(d90.tangent_axis(edge), direction)))
        structural = unit(np.cross(direction, tangent))
        center = np.asarray(best["targetSeedLocalUVmm"], float)
    else:
        root = d90.base_root(edge, 1.30, 0.0)
        direction = np.asarray((0.0, 0.0, 1.0), float)
        tangent = d90.tangent_axis(edge)
        structural = unit(np.cross(direction, tangent))
        center = root[:2].copy()
    return {"root": root, "direction": direction, "tangent": tangent,
            "structural": structural, "referenceCenterUVmm": center}


def complete_reference_samples(reference: dict[str, object]) -> list[np.ndarray]:
    root = np.asarray(reference["root"], float)
    tangent = np.asarray(reference["tangent"], float)
    structural = np.asarray(reference["structural"], float)
    return [root + tangent * dt + structural * ds for dt, ds in footprint_offsets()]


def pair_hits(ray: ExactRaySampler, datum, front: float, origin: np.ndarray,
              direction: np.ndarray) -> list[float]:
    return ray.hits(d90.local_point_to_world(datum, front, origin),
                    d90.local_dir_to_world(datum, direction), 24.0)


class ReusableMeasurementRaySampler:
    """Fast BRep mapper; every reported nearest result is rechecked fresh below."""

    def __init__(self, shape: Shape):
        self.shape = shape
        self._load()

    def _load(self) -> None:
        self.intersector = IntCurvesFace_ShapeIntersector()
        self.intersector.Load(self.shape.wrapped, 1.0e-7)

    def hits(self, origin: Iterable[float], direction: Iterable[float], maximum: float = 30.0) -> list[float]:
        o = tuple(map(float, origin)); d = tuple(map(float, unit(direction)))
        try:
            self.intersector.Perform(gp_Lin(gp_Pnt(*o), gp_Dir(*d)), 0.0, maximum)
        except Exception:
            self._load()
            try:
                self.intersector.Perform(gp_Lin(gp_Pnt(*o), gp_Dir(*d)), 0.0, maximum)
            except Exception:
                return []
        values = sorted(float(self.intersector.WParameter(i)) for i in range(1, self.intersector.NbPnt() + 1))
        unique: list[float] = []
        for value in values:
            if value >= -1.0e-6 and (not unique or abs(value - unique[-1]) > 0.02):
                unique.append(value)
        return unique


def missing_occupancy(datum, front: float, reference: dict[str, object],
                      owner_ray: ExactRaySampler, opposite_ray: ExactRaySampler,
                      cutter_ray: ExactRaySampler) -> dict[str, object]:
    direction = np.asarray(reference["direction"], float)
    rows = []
    for index, origin in enumerate(complete_reference_samples(reference), 1):
        owner = pair_hits(owner_ray, datum, front, origin, direction)
        opposite = pair_hits(opposite_ray, datum, front, origin, direction)
        cutter = cutter_ray.hits(d90.local_point_to_world(datum, front, origin),
                                 d90.local_dir_to_world(datum, direction), 24.0)
        if len(owner) >= 2:
            category = "owning-shell material"
        elif len(opposite) >= 2:
            category = "opposite shell half"
        elif len(owner) == 1:
            category = "owning-shell edge / open surface"
        elif cutter:
            category = "button-opening void"
        else:
            category = "outside actual shell BRep"
        rows.append({"sample": index, "originLocalUVWmm": origin.tolist(),
                     "ownerHitsMm": owner, "oppositeHitsMm": opposite,
                     "openingCutterHitsMm": cutter, "category": category,
                     "ownerPair": len(owner) >= 2})
    counts = Counter(row["category"] for row in rows)
    return {"samples": rows, "counts": dict(counts),
            "ownerCoverageCount": sum(row["ownerPair"] for row in rows),
            "ownerCoveragePercent": 100.0 * sum(row["ownerPair"] for row in rows) / 9.0,
            "missingCount": sum(not row["ownerPair"] for row in rows),
            "missingPercent": 100.0 * sum(not row["ownerPair"] for row in rows) / 9.0}


def center_samples(edge: str, center: np.ndarray, w0: float = 0.06) -> list[np.ndarray]:
    # At a shell landing, +U/-U slots are tangent in V and structural in U.
    # +V/-V swap those axes.  The rectangle is measured, never cut.
    rows = []
    for dt, ds in footprint_offsets():
        if edge.endswith("U"):
            rows.append(np.asarray((center[0] + ds, center[1] + dt, w0), float))
        else:
            rows.append(np.asarray((center[0] + dt, center[1] + ds, w0), float))
    return rows


def measure_center(edge: str, center: np.ndarray, datum, front: float,
                   ray: ExactRaySampler) -> dict[str, object]:
    direction = np.asarray((0.0, 0.0, 1.0), float)
    inner, outer, samples = [], [], []
    for origin in center_samples(edge, center):
        hit = pair_hits(ray, datum, front, origin, direction)
        samples.append({"originLocalUVWmm": origin.tolist(), "hitsMm": hit,
                        "paired": len(hit) >= 2})
        if len(hit) < 2:
            return {"centerLocalUVmm": center.tolist(), "fullFootprint": False,
                    "coverageCount": len(inner), "samples": samples}
        inner.append(float(hit[0])); outer.append(float(hit[1]))
    floor = max(inner) + BLIND_DEPTH
    remaining = min(outer) - floor
    return {"centerLocalUVmm": center.tolist(), "fullFootprint": True,
            "coverageCount": 9, "minimumRemainingShellMm": remaining,
            "shellThicknessRangeMm": [min(o-i for i, o in zip(inner, outer)),
                                       max(o-i for i, o in zip(inner, outer))],
            "usableBlindSlot": remaining >= REMAINING_TARGET - EPS, "samples": samples}


def scan_nearest(edge: str, reference_center: np.ndarray, datum, front: float,
                 ray: ExactRaySampler, shell_half: str) -> dict[str, object]:
    cache: dict[tuple[float, float], dict[str, object]] = {}
    mapper = ReusableMeasurementRaySampler(ray.shape)

    def evaluate(center: np.ndarray) -> dict[str, object]:
        key = (round(float(center[0]), 5), round(float(center[1]), 5))
        if key not in cache:
            cache[key] = measure_center(edge, center, datum, front, mapper)
        return cache[key]

    best_full = None
    best_usable = None
    coarse = []
    for iu in range(-28, 29):
        for iv in range(-28, 29):
            delta = np.asarray((iu * 0.25, iv * 0.25), float)
            distance = float(np.linalg.norm(delta))
            if distance <= 7.0 + EPS:
                coarse.append((distance, delta))
    coarse.sort(key=lambda row: row[0])
    for distance, delta in coarse:
        if best_full is not None and best_usable is not None and distance > max(best_full[0], best_usable[0]) + 0.36:
            break
        row = evaluate(reference_center + delta)
        if row.get("fullFootprint") and best_full is None:
            best_full = (distance, delta.copy(), row)
        if row.get("usableBlindSlot") and best_usable is None:
            best_usable = (distance, delta.copy(), row)

    def refine(best, usable: bool):
        if best is None:
            return None
        _, coarse_delta, _ = best
        candidates = []
        for iu in range(-6, 7):
            for iv in range(-6, 7):
                delta = coarse_delta + np.asarray((iu * 0.05, iv * 0.05), float)
                candidates.append((float(np.linalg.norm(delta)), delta))
        candidates.sort(key=lambda row: row[0])
        for distance, delta in candidates:
            row = evaluate(reference_center + delta)
            predicate = row.get("usableBlindSlot") if usable else row.get("fullFootprint")
            if predicate:
                best = (distance, delta.copy(), row)
                break
        # Fresh-intersector verification is the authority for the reported
        # position. Search a 0.40 mm neighborhood in increasing displacement
        # order so a reusable-intersector state cannot create a false nearest.
        _, candidate_delta, _ = best
        exact_candidates = []
        for iu in range(-8, 9):
            for iv in range(-8, 9):
                delta = candidate_delta + np.asarray((iu * 0.05, iv * 0.05), float)
                exact_candidates.append((float(np.linalg.norm(delta)), delta))
        exact_candidates.sort(key=lambda row: row[0])
        verified = None
        for distance, delta in exact_candidates:
            exact_row = measure_center(edge, reference_center + delta, datum, front, ray)
            predicate = exact_row.get("usableBlindSlot") if usable else exact_row.get("fullFootprint")
            if predicate:
                verified = (distance, delta.copy(), exact_row)
                break
        if verified is None:
            return None
        best = verified
        distance, delta, row = best
        center = np.asarray(row["centerLocalUVmm"], float)
        radial = center[0] if edge.endswith("U") else center[1]
        tangent = center[1] if edge.endswith("U") else center[0]
        expected_positive = edge.startswith("+")
        side = (radial > 0) if expected_positive else (radial < 0)
        return {"shellHalf": shell_half, "distanceMm": distance,
                "shiftLocalUVmm": delta.tolist(), **row,
                "assignedSideIdentityPreserved": bool(side and abs(tangent) <= 3.0 + EPS),
                "assignedSideTangentCoordinateMm": float(tangent)}

    return {"referenceCenterLocalUVmm": reference_center.tolist(),
            "grid": {"coarseStepMm": 0.25, "refinementStepMm": 0.05,
                     "maximumRadiusMm": 7.0, "evaluatedUniqueCenters": len(cache)},
            "nearestContinuousFullFootprint": refine(best_full, False),
            "nearestUsableBlindSlotLand": refine(best_usable, True)}


def thickness_diagnostic(best: dict[str, object], cutter_ray: ExactRaySampler,
                         datum, front: float) -> dict[str, object]:
    samples = best["samples"]
    inner = np.asarray([float(row["hitsMm"][0]) for row in samples], float)
    outer = np.asarray([float(row["hitsMm"][1]) for row in samples], float)
    thickness = outer - inner
    floor = float(inner.max() + BLIND_DEPTH)
    remaining = outer - floor
    critical = int(np.argmin(remaining))
    origin = np.asarray(samples[critical]["originLocalUVWmm"], float)
    direction = np.asarray(best["directionLocal"], float)
    cutter_hits = cutter_ray.hits(d90.local_point_to_world(datum, front, origin),
                                  d90.local_dir_to_world(datum, direction), 24.0)
    deficit = max(0.0, REMAINING_TARGET - float(remaining.min()))
    sliver_count = int(np.sum(thickness < 0.50))
    conventional = sliver_count == 0 and float(inner.max() - inner.min()) < 1.0
    if conventional:
        cause = "continuous local wall; common-floor curvature/thickness deficit"
    else:
        cause = "footprint straddles an opening/shell edge; short hit pairs are grazing shell slivers"
    return {
        "rayCount": 9, "floorDistanceFromRootMm": floor,
        "innerHitRangeMm": [float(inner.min()), float(inner.max())],
        "innerSurfaceDepthSpanMm": float(inner.max() - inner.min()),
        "outerHitRangeMm": [float(outer.min()), float(outer.max())],
        "shellThicknessMm": {"minimum": float(thickness.min()), "maximum": float(thickness.max()),
                             "mean": float(thickness.mean()), "median": float(np.median(thickness)),
                             "values": thickness.tolist()},
        "remainingShellAfterCommonFloorMm": {"minimum": float(remaining.min()),
                                              "maximum": float(remaining.max()),
                                              "mean": float(remaining.mean()),
                                              "values": remaining.tolist()},
        "criticalSample": critical + 1,
        "criticalOriginLocalUVWmm": origin.tolist(),
        "criticalInnerOuterHitsMm": samples[critical]["hitsMm"],
        "criticalRayIntersectsOpeningCutter": bool(cutter_hits),
        "grazingSliverRayCountBelow0p50mm": sliver_count,
        "uniformContinuousWall": conventional, "cause": cause,
        "requiredMinimumInwardThickeningMm": deficit,
        "reinforcementOnlyDiagnosticEstimate": {
            "assumption": "full 1.90 x 1.60 mm slot footprint plus 0.60 mm structural margin on every side",
            "minimumFootprintDimensionsMm": list(REINFORCEMENT_DIMS),
            "minimumFootprintAreaMm2": REINFORCEMENT_AREA,
            "minimumAddedVolumeMm3": deficit * REINFORCEMENT_AREA,
            "withinRequested2p5mmSweep": deficit <= 2.5 + EPS,
        },
    }


def classify(button: str, edge: str, thickness: dict[str, object] | None) -> tuple[str, str]:
    if (button, edge) in GROUP_A:
        return "A", "no usable land / incomplete footprint"
    assert thickness is not None
    deficit = float(thickness["requiredMinimumInwardThickeningMm"])
    if thickness["uniformContinuousWall"] and deficit <= 0.25 + EPS:
        return "B", "micro/small local shell-thickness deficit"
    if thickness["uniformContinuousWall"] and deficit <= 2.5 + EPS:
        return "C", "major but local shell-thickness deficit"
    return "D", "opening/edge-straddling or architecture-level landing"


def load_path_statement(category: str) -> str:
    if category in ("B", "C"):
        return "YES, conditional on sufficient continuous shell material; the straight leg axis itself is not the failure."
    return "CONDITIONAL ONLY: the straight member is structurally direct, but the current endpoint has no continuous reaction land."


def section_slab(reference: dict[str, object]) -> Shape:
    root = np.asarray(reference["root"], float)
    direction = np.asarray(reference["direction"], float)
    tangent = np.asarray(reference["tangent"], float)
    return oriented_box_between(xyz(root - direction * 1.0), xyz(root + direction * 14.0),
                                xyz(tangent), 0.20, 12.0, label="DIAGNOSTIC_AXIS_SECTION_SLAB")


def draw_footer_only(image, _title: str, _subtitle: str, footer: str) -> None:
    """Keep the authority footer while intentionally omitting the top banner."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import render_index_its_audit as raster

    draw = ImageDraw.Draw(image, "RGBA")
    large = image.width >= 1200
    inset = 26 if large else 18
    footer_h = 76 if large else 58
    draw.rounded_rectangle((inset, image.height - footer_h, image.width - inset, image.height - 18),
                           radius=14, fill=(7, 12, 19, 238), outline=(77, 105, 122, 235), width=2)
    draw.text((inset + 24, image.height - footer_h + 19), footer,
              font=raster.font(18 if large else 13, True), fill=(245, 205, 116, 255))


def raster_scene_without_header(*args, **kwargs) -> None:
    """Call the shared renderer without changing its default banner behavior."""
    original = render_module.draw_banner
    render_module.draw_banner = draw_footer_only
    try:
        render_module.raster_scene(*args, **kwargs)
    finally:
        render_module.draw_banner = original


def render_sections(results: dict[str, dict[str, object]], shell_full: dict[str, Shape],
                    datums, placements) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    outputs = []
    for number, (button, edge) in enumerate(TARGETS, 1):
        row = results[key_name(button, edge)]
        reference = row["_reference"]
        placement = placements[button]
        owner = datums[button].owner
        opposite = "JaD" if owner == "JfD" else "JfD"
        crop_tool = local_box(24, 24, 16, 0, 0, -1.5, "DIAGNOSTIC_LOCAL_CROP")
        owner_local = placement.inverse() * (shell_full[owner] & (placement * crop_tool)).clean()
        opposite_local = placement.inverse() * (shell_full[opposite] & (placement * crop_tool)).clean()
        slab = section_slab(reference)
        owner_cut = owner_local & slab
        opposite_cut = opposite_local & slab
        owner_section = owner_cut.clean() if owner_cut is not None else None
        opposite_section = opposite_cut.clean() if opposite_cut is not None else None
        root = np.asarray(reference["root"], float)
        direction = np.asarray(reference["direction"], float)
        tangent = np.asarray(reference["tangent"], float)
        best = row.get("docs91BestFailure")
        if best and best.get("floorPointLocalUVWmm"):
            probe_end = np.asarray(best["floorPointLocalUVWmm"], float)
        else:
            probe_end = root + direction * 9.5
        probe = oriented_box_between(xyz(root), xyz(probe_end), xyz(tangent),
                                     SLOT_TANGENT, SLOT_STRUCTURAL, label="FAILED_SLOT_ENVELOPE_DIAGNOSTIC_ONLY")
        objects = []
        if owner_section is not None and owner_section.solids():
            objects.append((safe_triangles(owner_section), COL["owner"]))
        if opposite_section is not None and opposite_section.solids():
            objects.append((safe_triangles(opposite_section), COL["opposite"]))
        objects.append((safe_triangles(probe), COL["probe"]))
        axis_end = root + direction * 11.5
        category = row["classification"]["category"]
        if row.get("thicknessDiagnostic"):
            metric = row["thicknessDiagnostic"]
            subtitle = (f"{category} | min remaining={metric['remainingShellAfterCommonFloorMm']['minimum']:.6f} mm | "
                        f"required inward={metric['requiredMinimumInwardThickeningMm']:.6f} mm")
        else:
            metric = row["missingFootprintOccupancy"]
            subtitle = (f"{category} | owning-shell footprint={metric['ownerCoverageCount']}/9 | "
                        f"missing={metric['missingPercent']:.1f}%")
        # Fit to the complete unchanged local shell crop, not only the failed
        # slot envelope.  A 15% synthetic padding gives the requested wider
        # camera framing without changing any diagnostic geometry.
        owner_tri = safe_triangles(owner_local)
        opposite_tri = safe_triangles(opposite_local) if opposite_local.solids() else np.empty((0, 3, 3))
        fit_arrays = [tri.reshape(-1, 3) for tri in (owner_tri, opposite_tri, safe_triangles(probe)) if tri.size]
        fit_raw = np.concatenate(fit_arrays, axis=0)
        fit_center = np.mean(fit_raw, axis=0)
        fit = fit_center + (fit_raw - fit_center) * 1.15
        filename = f"{number:02d}_{button.lower()}_{edge.replace('+','plus_').replace('-','minus_').lower()}section.png"
        raster_scene_without_header(RENDER / filename, objects,
                                    f"{number} / {button} {edge} EXACT FAILED-LANDING SECTION", subtitle, FOOTER,
                                    wireframes=[(safe_edge_lines(owner_local), (*COL["owner"], 95))],
                                    transparent_objects=[(owner_tri, (*COL["owner"], 25))],
                                    world_lines=[(root, axis_end, (*COL["axis"], 255), "")],
                                    camera_offset=(34, -46, 25), fit_points=fit)
        outputs.append(relative(RENDER / filename))
    return outputs


def fmt(value: object, digits: int = 6) -> str:
    return "N/A" if value is None else f"{float(value):.{digits}f}"


def report_text(data: dict[str, object]) -> str:
    rows = data["legs"]
    cats = data["summary"]["categories"]
    opening_table = []
    for button, edge in TARGETS:
        row = rows[key_name(button, edge)]
        if not row.get("missingFootprintOccupancy"):
            continue
        occ = row["missingFootprintOccupancy"]
        own_near = row["nearestLandMeasurement"]["owningHalf"]
        opp_near = row["nearestLandMeasurement"]["oppositeHalf"]
        own_use = own_near["nearestUsableBlindSlotLand"]
        opp_use = opp_near["nearestUsableBlindSlotLand"]
        opening_table.append(
            f"| {button} | {edge} | {occ['ownerCoverageCount']}/9 ({occ['ownerCoveragePercent']:.1f}%) | "
            f"{occ['missingCount']}/9 ({occ['missingPercent']:.1f}%) | {json.dumps(occ['counts'], ensure_ascii=False)} | "
            f"{fmt(own_use['distanceMm'] if own_use else None)} | {str(own_use['assignedSideIdentityPreserved'] if own_use else False).upper()} | "
            f"{fmt(opp_use['distanceMm'] if opp_use else None)} | "
            f"{row['classification']['interpretation']} |")

    thick_table = []
    for button, edge in TARGETS:
        row = rows[key_name(button, edge)]
        metric = row.get("thicknessDiagnostic")
        if not metric:
            continue
        shell = metric["shellThicknessMm"]
        remaining = metric["remainingShellAfterCommonFloorMm"]
        reinf = metric["reinforcementOnlyDiagnosticEstimate"]
        thick_table.append(
            f"| {button} | {edge} | {shell['minimum']:.6f} / {shell['maximum']:.6f} / {shell['mean']:.6f} | "
            f"{remaining['minimum']:.6f} | {metric['innerSurfaceDepthSpanMm']:.6f} | "
            f"{metric['grazingSliverRayCountBelow0p50mm']}/9 | {metric['cause']} | "
            f"{metric['requiredMinimumInwardThickeningMm']:.6f} | {reinf['minimumFootprintDimensionsMm'][0]:.2f} x {reinf['minimumFootprintDimensionsMm'][1]:.2f} | "
            f"{reinf['minimumAddedVolumeMm3']:.3f} | {row['classification']['category']} |")

    leg_lines = []
    for button, edge in TARGETS:
        row = rows[key_name(button, edge)]
        leg_lines.append(f"- **{button} {edge}: {row['classification']['category']}** — {row['classification']['interpretation']}; {row['loadPathIfMaterialExisted']}")

    cat_line = lambda key: ", ".join(cats[key]) if cats[key] else "NONE"
    return f"""# 92 — Six failed-leg shell-landing failure-mode diagnostic audit

## Authority and scope

- Latest rescue authority: `docs/91` and its exact best-failure evidence.
- Scope: only N2 +U/+V/-V, I3 +U/-U, and I4 +U.
- Mode: **failure classification and measurement only**. No endpoint optimization, no slot, shell, harness, or assembly solution was generated.
- Frozen controls: original detailed switch orientation, four edge roots, existing 26/32 viable legs, N3 +V rescue, shell halves, exterior, apertures, seam, and production files.
- Production modification count: **0**.

## Required headline

```text
6 failed-leg diagnostic result:

NO-USABLE-LAND = {cat_line('A')}
MICRO/SMALL-THICKNESS = {cat_line('B')}
MAJOR-LOCAL-THICKNESS = {cat_line('C')}
NONLOCAL/ARCHITECTURE-LEVEL = {cat_line('D')}
```

## Group A — footprint occupancy and nearest land

The nearest-land scan is measurement-only. It probes the unchanged BRep with a straight-W 1.90 x 1.60 mm rectangular footprint, first at 0.25 mm spacing and then at 0.05 mm refinement. A usable land must have 9/9 inner/outer pairs and leave at least 1.20 mm after a 1.20 mm common-depth blind slot. It does not generate a moved slot.

| Button | leg | owner footprint | missing | missing-sample occupancy | nearest usable owner shift (mm) | assigned side kept | nearest usable opposite-half shift (mm) | classification |
|---|---:|---:|---:|---|---:|---:|---:|---|
{chr(10).join(opening_table)}

## Group B — exact docs/91 thickness map

The slot floor is the docs/91 common floor: deepest inner hit + 1.20 mm. The reinforcement footprint estimate is deliberately minimal and diagnostic: full 1.90 x 1.60 mm footprint plus 0.60 mm margin on all sides = 3.10 x 2.80 mm (8.68 mm²). It is not a proposed part or shell edit.

| Button | leg | shell min/max/mean (mm) | min remaining (mm) | inner-depth span (mm) | <0.50-mm slivers | failure geometry | inward add (mm) | min patch (mm) | add volume (mm³) | class |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
{chr(10).join(thick_table)}

## Leg-by-leg judgment

{chr(10).join(leg_lines)}

## Four required decisions

1. **Thickness-only future candidates:** N2 -V and I3 -U. Their continuous 9/9 wall needs only 0.120359 mm and 0.080334 mm additional inward thickness respectively. This is a diagnostic classification, not authorization to modify the shell.
2. **Root/target research:** N2 +U and I3 +U are the only no-land cases, but repeating the same bounded docs/91 side-region search is not justified: docs/91 exhausted that search. Any future endpoint study must first relax or replace the same-side/edge reaction architecture. N2 +V and I4 +U are not endpoint-placement-only failures.
3. **Existing four-edge architecture without exterior redesign:** only the two Class-B legs have a credible reinforcement-only path in principle. The audit does not claim a production solution.
4. **Architecture issue:** the strict Class-D legs are N2 +V and I4 +U because their footprints straddle an opening/shell edge and use grazing shell slivers rather than one continuous wall. The two Class-A legs are also architecture constraints if their frozen assigned-side identity remains mandatory.

## Cross-sections

One exact diagnostic section was generated per failed leg (six total). Red is the failed docs/91 footprint envelope, grey is the owning shell, cyan is the opposite shell half when intersected, and yellow is the frozen failed-leg axis. These are evidence views, not solution geometry.

{chr(10).join(f'- `{path}`' for path in data['outputs']['renders'])}

## Preservation

- Protected-file hash equality: **{str(data['preservation']['protectedFilesUnchanged']).upper()}**.
- Protected files checked: {data['preservation']['protectedFileCount']}.
- New STEP solution artifacts: **0**.
- Shell/exterior/harness/assembly modifications: **0**.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    protected = protected_files()
    before = hashes(protected)
    docs91 = json.loads(DOC91_JSON.read_text(encoding="utf-8"))
    datums = load_all_datums()
    placements = {name: doc84.doc83.datum_location(datums[name], FROZEN_FRONT_DEPTHS[name]) for name in d90.BUTTONS}
    shell_full = {name: import_step(path) for name, path in SHELL_STEP.items()}
    shell_rays = {name: ExactRaySampler(shape) for name, shape in shell_full.items()}
    cutter_rays = {name: ExactRaySampler(opening_cutter(datums[name])) for name, _ in TARGETS}

    results: dict[str, dict[str, object]] = {}
    for button, edge in TARGETS:
        datum = datums[button]
        front = float(FROZEN_FRONT_DEPTHS[button])
        owner = datum.owner
        opposite = "JaD" if owner == "JfD" else "JfD"
        search = docs91["buttons"][button]["search"][edge]
        best = search.get("bestFailure")
        reference = reference_row(edge, best)
        row: dict[str, object] = {
            "button": button, "edge": edge, "shellOwner": owner,
            "docs91SearchResult": search["result"],
            "docs91TargetMapCount": search["targetMapCount"],
            "docs91ExactEvaluationCount": int(search["exactEvaluationsLe30"] + search["exactEvaluations31To45"]),
            "docs91BestFailure": best, "_reference": reference,
        }
        thickness = None
        if (button, edge) in GROUP_A:
            occupancy = missing_occupancy(datum, front, reference, shell_rays[owner],
                                          shell_rays[opposite], cutter_rays[button])
            center = np.asarray(reference["referenceCenterUVmm"], float)
            row["missingFootprintOccupancy"] = occupancy
            row["nearestLandMeasurement"] = {
                "owningHalf": scan_nearest(edge, center, datum, front, shell_rays[owner], owner),
                "oppositeHalf": scan_nearest(edge, center, datum, front, shell_rays[opposite], opposite),
            }
        else:
            thickness = thickness_diagnostic(best, cutter_rays[button], datum, front)
            row["thicknessDiagnostic"] = thickness
        category, interpretation = classify(button, edge, thickness)
        row["classification"] = {"category": category, "interpretation": interpretation}
        row["loadPathIfMaterialExisted"] = load_path_statement(category)
        results[key_name(button, edge)] = row

    category_rows = {key: [] for key in "ABCD"}
    for name, row in results.items():
        category_rows[row["classification"]["category"]].append(name)

    render_paths = render_sections(results, shell_full, datums, placements)
    for row in results.values():
        row.pop("_reference", None)
    after = hashes(protected)
    data = {
        "schema": "onegrip-six-failed-leg-shell-landing-failure-mode-diagnostic-v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "authority": {"latest": relative(d91.REPORT), "sourceJson": relative(DOC91_JSON)},
        "scope": {"diagnosticOnly": True, "solutionGeometryGenerated": False,
                  "optimizerOrEndpointSearch": False, "assemblyAudit": False,
                  "productionModificationCount": 0, "targetLegs": [key_name(*row) for row in TARGETS]},
        "summary": {"categories": category_rows,
                    "noUsableLandCount": len(category_rows["A"]),
                    "microSmallThicknessCount": len(category_rows["B"]),
                    "majorLocalThicknessCount": len(category_rows["C"]),
                    "nonlocalArchitectureCount": len(category_rows["D"])},
        "legs": results,
        "outputs": {"renders": render_paths, "report": relative(REPORT), "json": relative(JSON_PATH),
                    "stepSolutionArtifactCount": 0},
        "preservation": {"protectedFilesUnchanged": before == after,
                         "protectedFileCount": len(protected), "hashesBefore": before, "hashesAfter": after},
    }
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"summary": data["summary"], "report": relative(REPORT),
                      "json": relative(JSON_PATH), "renders": render_paths,
                      "protectedFilesUnchanged": before == after}, indent=2, ensure_ascii=False))


def render_only() -> None:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    results = data["legs"]
    for button, edge in TARGETS:
        row = results[key_name(button, edge)]
        row["_reference"] = reference_row(edge, row.get("docs91BestFailure"))
    datums = load_all_datums()
    placements = {name: doc84.doc83.datum_location(datums[name], FROZEN_FRONT_DEPTHS[name]) for name in d90.BUTTONS}
    shell_full = {name: import_step(path) for name, path in SHELL_STEP.items()}
    paths = render_sections(results, shell_full, datums, placements)
    print(json.dumps({"renderOnly": True, "renders": paths, "topBanner": False,
                      "fitToCompleteLocalShellCrop": True, "fitPaddingPercent": 15},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()
    render_only() if args.render_only else main()
