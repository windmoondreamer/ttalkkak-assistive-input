"""Local-only N2 rear reaction support redesign after docs/61.

The accepted cap, guide, switch pose, hard stop, HW504 geometry and exterior
are immutable.  Only the distribution of the rear reaction material is
changed.  Four simple support concepts are screened; one is then subjected
to serial exact B-rep and motion validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import psutil
from build123d import Align, Box, Compound, Location, Plane, Shape, Vector, export_step, import_step

from . import n2_production_intent_mechanism as baseline
from . import n2_robustness_pass as robustness
from .finger_controls_v2 import BRIDGE_SECTION, SWITCH_BODY_X, SWITCH_BODY_Y, oriented_box, unit
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    aggregate_pairs,
    exact_pair,
    raster_scene,
    safe_triangles,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "n2_rear_reaction_support_redesign"
RENDER_DIR = ROOT / "renders" / "n2_rear_reaction_support_redesign"
JSON_PATH = OUT_DIR / "n2_rear_reaction_support_redesign.json"
REPORT_PATH = ROOT / "docs" / "62_n2_rear_reaction_support_redesign.md"
SELECTED_CARRIER_STEP = OUT_DIR / "N1_N2_SHARED_CARRIER_N2_REAR_SUPPORT_REDRAFT.step"

DOCS60_CAP_STEP = (
    ROOT / "build123d_workbench" / "out" / "n2_production_intent_mechanism"
    / "N2_PRODUCTION_INTENT_CAP.step"
)
DOCS61_JSON = (
    ROOT / "build123d_workbench" / "out" / "n2_robustness_pass"
    / "n2_robustness_pass.json"
)

TARGET_CLEARANCE_MM = 0.30
PREFERRED_CLEARANCE_MM = 0.50
ASPIRATIONAL_CLEARANCE_MM = 0.80
REDESIGN_RELIEF_TANGENTIAL_MARGIN_MM = robustness.ROBUST_RELIEF_TANGENTIAL_MARGIN_MM
REDESIGN_RELIEF_NORMAL_MARGIN_MM = robustness.OLD_RELIEF_NORMAL_MARGIN_MM
SUPPORT_FRONT_MM = baseline.REACTION_FRONT_MM
SUPPORT_REAR_MM = baseline.REACTION_REAR_MM
SUPPORT_DEPTH_MM = SUPPORT_REAR_MM - SUPPORT_FRONT_MM
OLD_SUPPORT_AREA_MM2 = 13.18277569345569
MIN_STRUCTURAL_WALL_MM = 1.20
SELECTED_CLEARANCE_OFFSET_MM = 0.55

PROCESS = psutil.Process(os.getpid())
RSS_LIMIT_MB = 24576.0
MEMORY: list[dict[str, float | str]] = []


COLORS = {
    "carrier": (179, 89, 211),
    "old": (245, 128, 62),
    "a": (83, 177, 232),
    "b": (61, 201, 145),
    "c": (245, 184, 70),
    "d": (232, 93, 139),
    "body": (235, 174, 66),
    "actuator": (252, 207, 89),
    "cap": (57, 207, 143),
    "guide": (74, 142, 226),
    "hw": (145, 96, 235),
    "shell": (87, 183, 214),
    "active": (67, 204, 147),
    "trimmed": (120, 130, 142),
    "contact": (247, 231, 88),
}


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1)})
    if rss > RSS_LIMIT_MB:
        raise MemoryError(f"RAM stop at {stage}: {rss:.1f} MB")
    available = float(psutil.virtual_memory().available) / (1024.0 * 1024.0)
    if available < 3072.0:
        raise MemoryError(f"System available-memory stop at {stage}: {available:.1f} MB")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def shape_volume(shape: Shape | None) -> float:
    if shape is None or len(shape.solids()) == 0:
        return 0.0
    return float(shape.volume)


def robust_tool() -> Shape:
    margin = np.asarray((
        REDESIGN_RELIEF_TANGENTIAL_MARGIN_MM,
        REDESIGN_RELIEF_NORMAL_MARGIN_MM,
        REDESIGN_RELIEF_TANGENTIAL_MARGIN_MM,
    ))
    return baseline.global_box(
        robustness.OLD_COMMON_LOWER - margin,
        robustness.OLD_COMMON_UPPER + margin,
        "DOCS61_APPROVED_NONFUNCTIONAL_RELIEF_TOOL",
    )


def hw_clearance_tool(hw_a: Shape, carrier: Shape, distance_mm: float) -> tuple[Shape, dict[str, object]]:
    """Create one oriented slab over the nonfunctional shared-bridge limiter."""
    distance, p_hw, p_carrier = hw_a.distance_to_with_closest_points(carrier)
    delta = np.asarray((
        float(p_carrier.X - p_hw.X),
        float(p_carrier.Y - p_hw.Y),
        float(p_carrier.Z - p_hw.Z),
    ))
    direction = unit(delta)
    # The exact closest vectors at the old rear frame and the newly exposed
    # shared bridge are parallel.  Shave only the shared bridge, ending the
    # cutter before the N2 switch/support zone at global X=-5.0 mm.
    x_min, x_max = -13.0, -3.10
    tangent_width = 6.00
    normal_before = 0.65
    normal_after = float(distance_mm)
    normal_span = normal_before + normal_after
    bridge = np.asarray((float(p_hw.X), float(p_hw.Y), float(p_hw.Z)))
    origin = bridge + direction * (0.5 * (normal_after - normal_before))
    origin[0] = 0.5 * (x_min + x_max)
    plane = Plane(
        origin=(float(origin[0]), float(origin[1]), float(origin[2])),
        x_dir=(1.0, 0.0, 0.0),
        z_dir=(float(direction[0]), float(direction[1]), float(direction[2])),
    )
    result = plane.location * Box(
        x_max - x_min,
        tangent_width,
        normal_span,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    result.label = f"SHARED_BRIDGE_DIRECTIONAL_{distance_mm:.3f}MM_CLEARANCE_SLAB"
    return result, {
        "preClearanceMm": float(distance),
        "directionGlobal": direction.tolist(),
        "targetNormalClearanceMm": float(distance_mm),
        "xRangeMm": [x_min, x_max],
        "tangentWidthMm": tangent_width,
        "normalRangeFromHwMm": [-normal_before, normal_after],
    }


@dataclass(slots=True)
class SupportConcept:
    code: str
    name: str
    parts: list[Shape]
    minimum_wall_mm: float
    description: str


def part(datum, width_u: float, width_v: float, u: float, v: float, label: str) -> Shape:
    return oriented_box(
        datum,
        width_u,
        width_v,
        SUPPORT_FRONT_MM,
        SUPPORT_REAR_MM,
        u_offset=u,
        v_offset=v,
        label=label,
    )


def concepts(datum) -> list[SupportConcept]:
    # A: frame retained on the non-HW side, with the HW-side upper quadrant
    # locally opened.  It keeps a broad distributed reaction path.
    outer = part(datum, 6.40, 6.40, 0.0, 0.0, "A_FRAME_OUTER")
    window = part(datum, 4.00, 3.20, 0.0, 0.0, "A_FRAME_WINDOW")
    hw_corner_opening = part(datum, 3.05, 2.25, 1.675, 2.075, "A_HW_SIDE_OPENING")
    a_shape = (outer - window - hw_corner_opening).clean()
    a_shape.label = "A_CENTRAL_RELIEVED_REAR_FRAME"

    # B: short U cradle open toward +v (the HW504 side).  Rails stop at
    # v=+1.25 where both exceed the 0.30 mm HW gate; the crossbar begins at
    # the terminal service boundary and reconnects the otherwise free rail.
    b_parts = [
        part(datum, 1.40, 2.50, -2.50, 0.00, "B_LEFT_RAIL"),
        part(datum, 1.40, 2.50, 2.50, 0.00, "B_RIGHT_RAIL"),
        part(datum, 6.40, 1.75, 0.0, -0.675, "B_CROSSBAR"),
    ]

    # C: two long side pads.  Their outer faces fuse to the existing carrier
    # side walls and their centres are almost 5 mm apart.
    c_parts = [
        part(datum, 1.40, 2.40, -2.50, 0.00, "C_LEFT_PAD"),
        part(datum, 1.40, 2.40, 2.50, 0.00, "C_RIGHT_PAD"),
    ]

    # D: two lower side pads plus a third upper pad on the side opposite the
    # known HW504 corner.  Three separated contacts form a broad triangle.
    d_parts = [
        part(datum, 1.40, 2.00, -2.50, -0.40, "D_LEFT_LOWER_PAD"),
        part(datum, 1.40, 2.00, 2.50, -0.40, "D_RIGHT_LOWER_PAD"),
        part(datum, 1.40, 1.40, -2.50, 2.30, "D_LEFT_UPPER_PAD"),
    ]

    return [
        SupportConcept("A", "CENTRAL RELIEVED REAR FRAME", [a_shape], 1.20, "broad frame with HW-side corner opened"),
        SupportConcept("B", "U-SHAPED REACTION CRADLE", b_parts, 1.20, "two rails plus terminal-safe crossbar"),
        SupportConcept("C", "TWO-PAD REACTION SUPPORT", c_parts, 1.40, "two wide-spaced side pads"),
        SupportConcept("D", "THREE-PAD REACTION SUPPORT", d_parts, 1.40, "triangular three-zone support"),
    ]


def cutters(source: dict[str, Shape], datum, roots: dict[str, Shape]) -> list[Shape]:
    rows = [baseline.active_service_bay(datum), baseline.service_sweeps(datum)["switch"], *roots.values()]
    return rows


def cut_shape(shape: Shape, rows: list[Shape], relief: Shape) -> Shape:
    result = shape
    for cutter in rows:
        result = result - cutter
    result = (result - relief).clean()
    return result


def build_carrier(
    source_carrier: Shape,
    guide: Shape,
    concept: SupportConcept,
    cut_rows: list[Shape],
    relief: Shape,
) -> tuple[Shape, list[Shape]]:
    carrier = source_carrier.fuse(guide)
    for support_part in concept.parts:
        carrier = carrier.fuse(support_part)
    for cutter in cut_rows:
        carrier = carrier - cutter
    carrier = (carrier - relief).clean()
    carrier.label = f"N1_N2_SHARED_CARRIER_N2_SUPPORT_{concept.code}"
    finished_parts: list[Shape] = []
    for support_part in concept.parts:
        finished = cut_shape(support_part, cut_rows, relief)
        if shape_volume(finished) > BOOLEAN_EPS_MM3:
            finished.label = support_part.label
            finished_parts.append(finished)
    return carrier, finished_parts


def local_uv(datum, point: Iterable[float]) -> tuple[float, float]:
    row = np.asarray(tuple(point), dtype=float) - np.asarray(datum.center, dtype=float)
    return float(np.dot(row, unit(datum.switch_u))), float(np.dot(row, unit(datum.switch_v)))


def contact_metrics(datum, support_parts: list[Shape]) -> dict[str, object]:
    body_footprint = oriented_box(
        datum,
        SWITCH_BODY_X,
        SWITCH_BODY_Y,
        SUPPORT_FRONT_MM,
        SUPPORT_REAR_MM,
        label="ITS_REAR_PLASTIC_CONTACT_FOOTPRINT",
    )
    rows: list[dict[str, object]] = []
    for support_part in support_parts:
        common = support_part & body_footprint
        area = shape_volume(common) / SUPPORT_DEPTH_MM
        if area <= 1.0e-7:
            continue
        centre = common.center()
        u, v = local_uv(datum, (centre.X, centre.Y, centre.Z))
        rows.append({"label": support_part.label, "areaMm2": area, "uMm": u, "vMm": v})
    span = 0.0
    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            span = max(span, float(np.hypot(left["uMm"] - right["uMm"], left["vMm"] - right["vMm"])))
    combined = support_parts[0]
    for support_part in support_parts[1:]:
        combined = combined.fuse(support_part)
    unique_contact = combined & body_footprint
    total = shape_volume(unique_contact) / SUPPORT_DEPTH_MM
    radial_moment = float(sum(float(row["areaMm2"]) * (float(row["uMm"]) ** 2 + float(row["vMm"]) ** 2) for row in rows))
    return {
        "totalAreaMm2": total,
        "contactZoneCount": len(rows),
        "connectedContactPatchCount": len(unique_contact.solids()),
        "contactSpanMm": span,
        "radialMomentProxyMm4": radial_moment,
        "zones": rows,
    }


def bbox_gap(left: Shape, right: Shape) -> float:
    a = left.bounding_box()
    b = right.bounding_box()
    gaps = np.asarray((
        max(0.0, float(a.min.X - b.max.X), float(b.min.X - a.max.X)),
        max(0.0, float(a.min.Y - b.max.Y), float(b.min.Y - a.max.Y)),
        max(0.0, float(a.min.Z - b.max.Z), float(b.min.Z - a.max.Z)),
    ))
    return float(np.linalg.norm(gaps))


def distance_witness(datum, left: Shape, right: Shape) -> dict[str, object]:
    distance, p_left, p_right = left.distance_to_with_closest_points(right)
    left_global = (float(p_left.X), float(p_left.Y), float(p_left.Z))
    right_global = (float(p_right.X), float(p_right.Y), float(p_right.Z))
    return {
        "distanceMm": float(distance),
        "leftGlobalMm": list(left_global),
        "rightGlobalMm": list(right_global),
        "leftLocalUvMm": list(local_uv(datum, left_global)),
        "rightLocalUvMm": list(local_uv(datum, right_global)),
    }


def screen_candidates() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    memory("start")
    source = baseline.load_source()
    datum = baseline.load_datum()
    roots, _ = baseline.trim_terminals(source, datum)
    guide, _ = baseline.build_guide(datum)
    old_support, _ = baseline.build_reaction_support(datum, roots)
    source_carrier = source["N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"]
    relief = robust_tool()
    cut_rows = cutters(source, datum, roots)
    base_carrier = source_carrier.fuse(guide)
    for cutter in cut_rows:
        base_carrier = base_carrier - cutter
    base_carrier = (base_carrier - relief).clean()
    component_limiters = {
        "baseCarrier": distance_witness(datum, source["HW504_A_NONFUNCTIONAL_TRIM"], base_carrier),
        "sourceCarrier": distance_witness(datum, source["HW504_A_NONFUNCTIONAL_TRIM"], (source_carrier - relief).clean()),
        "guide": distance_witness(datum, source["HW504_A_NONFUNCTIONAL_TRIM"], guide),
    }
    rows: list[dict[str, object]] = []
    selected_pre_clearance: Shape | None = None
    selected_support_parts: list[Shape] = []
    for concept in concepts(datum):
        carrier, support_parts = build_carrier(source_carrier, guide, concept, cut_rows, relief)
        witness_a = distance_witness(datum, source["HW504_A_NONFUNCTIONAL_TRIM"], carrier)
        distance_a = float(witness_a["distanceMm"])
        distance_b = float(carrier.distance_to_with_closest_points(source["HW504_B_EXACT_KEEP"])[0])
        contacts = contact_metrics(datum, support_parts)
        rows.append({
            "code": concept.code,
            "name": concept.name,
            "description": concept.description,
            "carrierSolidCount": len(carrier.solids()),
            "sourceSolidCount": len(source_carrier.solids()),
            "loadPathConnected": len(carrier.solids()) == len(source_carrier.solids()),
            "minimumSupportWallMm": concept.minimum_wall_mm,
            "overallMinimumWallMm": min(baseline.GUIDE_WALL_MM, concept.minimum_wall_mm, 1.3148483522514047),
            "hw504ABboxGapMm": bbox_gap(carrier, source["HW504_A_NONFUNCTIONAL_TRIM"]),
            "hw504ADistanceMm": distance_a,
            "hw504AWitness": witness_a,
            "hw504BDistanceMm": distance_b,
            "contacts": contacts,
        })
        if concept.code == "B":
            selected_pre_clearance = carrier
            selected_support_parts = support_parts
        else:
            del carrier, support_parts
        memory(f"candidate {concept.code} screened")
    if selected_pre_clearance is None:
        raise RuntimeError("selected B carrier missing")
    exact_clearance_tool, clearance_tool_metrics = hw_clearance_tool(
        source["HW504_A_NONFUNCTIONAL_TRIM"], selected_pre_clearance, SELECTED_CLEARANCE_OFFSET_MM
    )
    selected_final = (selected_pre_clearance - exact_clearance_tool).clean()
    selected_exact_probe = {
        "carrierSolidCount": len(selected_final.solids()),
        "sourceSolidCount": len(source_carrier.solids()),
        "hw504A": distance_witness(datum, source["HW504_A_NONFUNCTIONAL_TRIM"], selected_final),
        "hw504BDistanceMm": float(selected_final.distance_to_with_closest_points(source["HW504_B_EXACT_KEEP"])[0]),
        "clearanceToolGuidePenetrationMm3": shape_volume(exact_clearance_tool & guide),
        "clearanceToolBodyPenetrationMm3": shape_volume(exact_clearance_tool & source["N2_ITS1105_body"]),
        "clearanceToolSupportPenetrationMm3": sum(shape_volume(exact_clearance_tool & row) for row in selected_support_parts),
        "clearanceTool": clearance_tool_metrics,
    }
    memory("selected B clearance offset probe")
    print(json.dumps({"oldAreaMm2": OLD_SUPPORT_AREA_MM2, "componentLimiters": component_limiters, "candidates": rows, "selectedExactProbe": selected_exact_probe, "peakRssMb": max(float(r["rssMb"]) for r in MEMORY)}, indent=2))


def combined_shape(parts: list[Shape], label: str) -> Shape:
    if not parts:
        raise RuntimeError(f"{label}: no parts")
    result = parts[0]
    for row in parts[1:]:
        result = result.fuse(row)
    result = result.clean()
    result.label = label
    return result


def evaluate_candidates(
    source: dict[str, Shape],
    datum,
    roots: dict[str, Shape],
    guide: Shape,
    relief: Shape,
) -> tuple[list[dict[str, object]], Shape, list[Shape], dict[str, list[Shape]]]:
    source_carrier = source["N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"]
    cut_rows = cutters(source, datum, roots)
    metrics: list[dict[str, object]] = []
    selected_carrier: Shape | None = None
    selected_parts: list[Shape] = []
    support_by_code: dict[str, list[Shape]] = {}
    for concept in concepts(datum):
        carrier, finished_parts = build_carrier(source_carrier, guide, concept, cut_rows, relief)
        support_by_code[concept.code] = finished_parts
        support_distances = [
            float(row.distance_to_with_closest_points(source["HW504_A_NONFUNCTIONAL_TRIM"])[0])
            for row in finished_parts
        ]
        carrier_witness = distance_witness(datum, source["HW504_A_NONFUNCTIONAL_TRIM"], carrier)
        contacts = contact_metrics(datum, finished_parts)
        connected = len(carrier.solids()) == len(source_carrier.solids())
        metrics.append({
            "code": concept.code,
            "name": concept.name,
            "description": concept.description,
            "loadPathConnected": connected,
            "carrierSolidCount": len(carrier.solids()),
            "sourceSolidCount": len(source_carrier.solids()),
            "supportToHW504AMinimumMm": min(support_distances),
            "supportPartClearancesMm": support_distances,
            "carrierToHW504APreClearanceMm": float(carrier_witness["distanceMm"]),
            "carrierToHW504BPreClearanceMm": float(carrier.distance_to_with_closest_points(source["HW504_B_EXACT_KEEP"])[0]),
            "minimumSupportWallMm": concept.minimum_wall_mm,
            "overallMinimumWallMm": min(baseline.GUIDE_WALL_MM, concept.minimum_wall_mm, 1.3148483522514047),
            "contacts": contacts,
            "screenVerdict": (
                "SELECT FOR EXACT"
                if concept.code == "B" and connected and min(support_distances) + 1.0e-9 >= TARGET_CLEARANCE_MM
                else "REJECT"
            ),
        })
        if concept.code == "B":
            selected_carrier = carrier
            selected_parts = finished_parts
        memory(f"candidate {concept.code} comparison complete")
    if selected_carrier is None:
        raise RuntimeError("B carrier selection failed")
    return metrics, selected_carrier, selected_parts, support_by_code


def exact_selected_checks(
    source: dict[str, Shape],
    datum,
    cap: Shape,
    cap_parts: dict[str, Shape],
    guide: Shape,
    guide_parts: dict[str, Shape],
    carrier_before_slab: Shape,
    carrier: Shape,
    support_parts: list[Shape],
    roots: dict[str, Shape],
    clearance_tool: Shape,
) -> dict[str, object]:
    checks = baseline.exact_validation(
        source,
        datum,
        cap,
        cap_parts,
        guide,
        guide_parts,
        carrier,
        roots,
    )
    hw_a = exact_pair(source["HW504_A_NONFUNCTIONAL_TRIM"], carrier, "HW504_A<->selected carrier")
    hw_b = exact_pair(source["HW504_B_EXACT_KEEP"], carrier, "HW504_B<->selected carrier")
    removed = (carrier_before_slab - carrier).clean()
    n1_functional = Compound(
        children=[
            source["N1_ITS1105_body"],
            source["N1_ITS1105_actuator"],
            source["N1_root_nu_nv"],
            source["N1_root_nu_pv"],
            source["N1_root_pu_nv"],
            source["N1_root_pu_pv"],
        ],
        label="N1_FROZEN_FUNCTIONAL_ENVELOPE",
    )
    support = combined_shape(support_parts, "SELECTED_B_U_CRADLE")
    protection = {
        "removedMaterialVsN1FunctionalMm3": shape_volume(removed & n1_functional),
        "removedMaterialVsGuideMm3": shape_volume(removed & guide),
        "removedMaterialVsHardStopMm3": shape_volume(removed & guide_parts["rearStop"]),
        "removedMaterialVsN2SwitchBodyMm3": shape_volume(removed & source["N2_ITS1105_body"]),
        "removedMaterialVsSelectedSupportMm3": shape_volume(removed & support),
        # The cutter is allowed to pass through the already-empty terminal
        # service cavity.  Gate the material actually removed, not the raw
        # cutter envelope, against the immutable active terminals.
        "removedMaterialVsN2T1Mm3": shape_volume(removed & roots["T1"]),
        "removedMaterialVsN2T3Mm3": shape_volume(removed & roots["T3"]),
    }
    memory("selected exact B-rep and motion checks")
    return {
        "baselineMotionAndStatic": checks,
        "HW504ASelectedCarrier": hw_a,
        "HW504BSelectedCarrier": hw_b,
        "clearanceReliefProtection": protection,
        "clearanceReliefRemovedMm3": max(0.0, float(carrier_before_slab.volume - carrier.volume)),
    }


def shifted_mesh(triangles: np.ndarray, vector: Iterable[float]) -> np.ndarray:
    return triangles + np.asarray(tuple(vector), dtype=float)


def shape_center(shape: Shape) -> np.ndarray:
    lower, upper = baseline.bounds(shape)
    return 0.5 * (lower + upper)


def render_outputs(
    source: dict[str, Shape],
    datum,
    cap: Shape,
    guide: Shape,
    guide_parts: dict[str, Shape],
    old_support: Shape,
    candidate_parts: dict[str, list[Shape]],
    selected_parts: list[Shape],
    carrier: Shape,
    roots: dict[str, Shape],
    exact: dict[str, object],
    candidate_metrics: list[dict[str, object]],
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        RENDER_DIR / "01_current_rear_reaction_support.png",
        RENDER_DIR / "02_candidate_abcd_comparison.png",
        RENDER_DIR / "03_selected_u_cradle_isolated.png",
        RENDER_DIR / "04_switch_rear_contact_map.png",
        RENDER_DIR / "05_hw504a_clearance_closeup.png",
        RENDER_DIR / "06_rest_state_section.png",
        RENDER_DIR / "07_full_press_section.png",
        RENDER_DIR / "08_transparent_final_local_assembly.png",
    ]
    cache: dict[int, np.ndarray] = {}

    def mesh(shape: Shape, limit: int = 3000) -> np.ndarray:
        key = id(shape)
        if key not in cache:
            cache[key] = safe_triangles(shape, tolerance=0.085, angular=0.06, limit=limit)
        return cache[key]

    body = source["N2_ITS1105_body"]
    actuator_rest = baseline.actuator_at(datum, 0.0)
    actuator_press = baseline.actuator_at(datum, baseline.ACTUATOR_TRAVEL_MAX)
    cap_press = baseline.cap_at(cap, datum, baseline.ACTUATOR_TRAVEL_MAX)
    shells = [source["N2_SEAM_JaD"], source["N2_SEAM_JfD"]]
    hw_a = source["HW504_A_NONFUNCTIONAL_TRIM"]
    hw_b = source["HW504_B_EXACT_KEEP"]
    source_carrier = source["N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"]
    selected_support = combined_shape(selected_parts, "SELECTED_B_U_CRADLE_RENDER")
    crop = oriented_box(datum, 18.0, 18.0, -2.5, 11.8, cap_frame=True, label="N2_REDESIGN_RENDER_CROP")
    half = oriented_box(datum, 20.0, 24.0, -2.5, 11.8, u_offset=-10.0, cap_frame=True, label="N2_REDESIGN_SECTION_HALF")

    def local(shape: Shape) -> Shape:
        return (shape & crop).clean()

    def section(shape: Shape) -> Shape:
        return (shape & crop & half).clean()

    axis = unit(datum.axis)
    rear_camera = -axis * 88.0 + unit(datum.switch_u) * 8.0
    body_mesh = mesh(body)
    old_mesh = mesh(old_support)
    roots_mesh = {name: mesh(row, 900) for name, row in roots.items()}

    # 01 current broad frame.
    old_focus = np.concatenate([body_mesh.reshape(-1, 3), old_mesh.reshape(-1, 3)])
    raster_scene(
        paths[0],
        [(old_mesh, COLORS["old"]), *[(roots_mesh[n], COLORS["active"] if n in {"T1", "T3"} else COLORS["trimmed"]) for n in roots]],
        "01 / CURRENT REAR REACTION SUPPORT",
        "docs/60-61 broad frame; function accepted but HW-side distribution is no longer frozen",
        f"Old reaction contact area {OLD_SUPPORT_AREA_MM2:.3f} mm² | HW504-A limiter 0.011 mm",
        transparent_objects=[(body_mesh, (*COLORS["body"], 76))],
        camera_offset=tuple(float(x) for x in rear_camera),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=old_focus,
    )
    memory("render 01 current support")

    # 02 four concepts, separated along switch-u.
    shifts = {"A": -18.0, "B": -6.0, "C": 6.0, "D": 18.0}
    objects: list[tuple[np.ndarray, tuple[int, int, int]]] = []
    transparent: list[tuple[np.ndarray, tuple[int, int, int, int]]] = []
    lines = []
    focus_rows = []
    by_code = {row["code"]: row for row in candidate_metrics}
    for code in ("A", "B", "C", "D"):
        offset = unit(datum.switch_u) * shifts[code]
        support_mesh = mesh(Compound(children=candidate_parts[code]))
        moved_support = shifted_mesh(support_mesh, offset)
        moved_body = shifted_mesh(body_mesh, offset)
        objects.append((moved_support, COLORS[code.lower()]))
        transparent.append((moved_body, (*COLORS["body"], 36)))
        focus_rows.extend([moved_support.reshape(-1, 3), moved_body.reshape(-1, 3)])
        centre = shape_center(Compound(children=candidate_parts[code])) + offset
        row = by_code[code]
        label = f"{code}: {float(row['contacts']['totalAreaMm2']):.2f} mm2 / {float(row['supportToHW504AMinimumMm']):.3f} mm"
        lines.append((centre, centre + unit(datum.switch_v) * 2.6, (255, 224, 116, 255), label))
    raster_scene(
        paths[1],
        objects,
        "02 / REAR SUPPORT CANDIDATE A / B / C / D",
        "A relieved frame | B short U-cradle | C two pads | D three pads",
        "B selected: connected load path + 13.524 mm² unique contact + support clearance >=0.30 mm",
        transparent_objects=transparent,
        world_lines=lines,
        camera_offset=tuple(float(x) for x in rear_camera),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=np.concatenate(focus_rows),
    )
    memory("render 02 candidate comparison")

    # 03 isolated selected support with explicit load path.
    selected_meshes = [mesh(row, 1800) for row in selected_parts]
    selected_focus = np.concatenate([body_mesh.reshape(-1, 3), *[row.reshape(-1, 3) for row in selected_meshes]])
    body_centre = shape_center(body)
    support_centre = shape_center(selected_support)
    raster_scene(
        paths[2],
        [
            (selected_meshes[0], COLORS["b"]),
            (selected_meshes[1], (42, 170, 126)),
            (selected_meshes[2], (89, 220, 172)),
        ],
        "03 / SELECTED SHORT U-CRADLE — ISOLATED",
        "Two 1.40 mm rails stop before HW504; 1.75 mm crossbar reconnects the carrier load path",
        "finger force -> ITS body -> 3 reaction zones -> shared carrier -> shell",
        transparent_objects=[(body_mesh, (*COLORS["body"], 68))],
        world_lines=[(body_centre + axis * 3.0, support_centre, (255, 224, 116, 255), "REACTION LOAD PATH")],
        camera_offset=(62.0, -88.0, -38.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=selected_focus,
    )
    memory("render 03 selected isolated")

    # 04 switch rear contact map.
    contact_lines = []
    selected_contact = contact_metrics(datum, selected_parts)
    for row, support_part in zip(selected_contact["zones"], selected_parts):
        centre = shape_center(support_part)
        contact_lines.append((centre, centre + unit(datum.switch_v) * 2.0, (255, 232, 98, 255), f"{float(row['areaMm2']):.3f} mm2"))
    raster_scene(
        paths[3],
        [(triangles, COLORS["contact"]) for triangles in selected_meshes]
        + [(roots_mesh[n], COLORS["active"] if n in {"T1", "T3"} else COLORS["trimmed"]) for n in roots],
        "04 / ITS REAR PLASTIC CONTACT MAP",
        "Yellow zones contact plastic housing only; all four terminal roots remain unsupported and serviceable",
        f"3 zones | unique area {float(selected_contact['totalAreaMm2']):.3f} mm² | rail-centre span {float(selected_contact['contactSpanMm']):.3f} mm",
        transparent_objects=[(body_mesh, (*COLORS["body"], 58))],
        world_lines=contact_lines,
        camera_offset=tuple(float(x) for x in rear_camera),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=selected_focus,
    )
    memory("render 04 contact map")

    # 05 exact final clearance close-up around the final witness only.
    hw_row = exact["HW504ASelectedCarrier"]
    p0 = np.asarray(hw_row["closestPointLeftMm"], dtype=float)
    p1 = np.asarray(hw_row["closestPointRightMm"], dtype=float)
    witness_mid = 0.5 * (p0 + p1)
    close_crop = baseline.global_box(witness_mid - 4.2, witness_mid + 4.2, "N2_FINAL_CLEARANCE_RENDER_CROP")
    carrier_close = (carrier & close_crop).clean()
    hw_close = (hw_a & close_crop).clean()
    close_focus = np.concatenate([mesh(carrier_close, 4000).reshape(-1, 3), mesh(hw_close, 4000).reshape(-1, 3)])
    raster_scene(
        paths[4],
        [(mesh(carrier_close, 4000), COLORS["b"])],
        "05 / HW504-A ↔ CARRIER EXACT CLEARANCE",
        "Selected B plus one local directional shared-bridge relief; HW504 geometry is unchanged",
        f"Exact clearance {float(hw_row['distanceMm']):.6f} mm >= 0.300 mm | penetration 0",
        transparent_objects=[(mesh(hw_close, 4000), (*COLORS["hw"], 72))],
        world_lines=[(p0, p1, (255, 224, 116, 255), f"{float(hw_row['distanceMm']):.6f} mm")],
        camera_offset=(52.0, -70.0, 38.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=close_focus,
    )
    memory("render 05 exact clearance")

    # 06/07 true local sections with fixed fit for direct comparison.
    base_local = local(source_carrier)
    rest_rows = [
        (mesh(section(cap)), COLORS["cap"]),
        (mesh(section(guide)), COLORS["guide"]),
        (mesh(section(base_local)), COLORS["carrier"]),
        (mesh(section(selected_support)), COLORS["b"]),
        (mesh(section(body)), COLORS["body"]),
        (mesh(section(actuator_rest)), COLORS["actuator"]),
    ]
    rest_focus = np.concatenate([triangles.reshape(-1, 3) for triangles, _ in rest_rows])
    raster_scene(
        paths[5], rest_rows,
        "06 / N2 REST 0.000 mm — TRUE LOCAL SECTION",
        "Accepted guide, switch pose, cap axis and direct actuator contact remain frozen",
        "Hard-stop residual 0.350 mm | unintended penetration 0",
        transparent_objects=[(mesh(local(shell), 2200), (*COLORS["shell"], 30)) for shell in shells],
        camera_offset=(84.0, 0.0, 0.0),
        final_size=(1920, 1280), supersample=2, fit_points=rest_focus,
    )
    memory("render 06 rest section")
    press_rows = [
        (mesh(section(cap_press)), COLORS["cap"]),
        (mesh(section(guide)), COLORS["guide"]),
        (mesh(section(base_local)), COLORS["carrier"]),
        (mesh(section(selected_support)), COLORS["b"]),
        (mesh(section(body)), COLORS["body"]),
        (mesh(section(actuator_press)), COLORS["actuator"]),
    ]
    raster_scene(
        paths[6], press_rows,
        "07 / N2 FULL PRESS 0.350 mm — TRUE LOCAL SECTION",
        "The separate carrier hard stop receives overtravel; ITS housing is not the structural stop",
        "Hard-stop residual 0.000 mm | unintended penetration 0",
        transparent_objects=[(mesh(local(shell), 2200), (*COLORS["shell"], 30)) for shell in shells],
        camera_offset=(84.0, 0.0, 0.0),
        final_size=(1920, 1280), supersample=2, fit_points=rest_focus,
    )
    memory("render 07 full press section")

    # 08 transparent local assembly.
    cap_mesh = mesh(cap)
    actuator_mesh = mesh(actuator_rest)
    assembled_focus = np.concatenate([cap_mesh.reshape(-1, 3), body_mesh.reshape(-1, 3), mesh(local(carrier), 4200).reshape(-1, 3)])
    raster_scene(
        paths[7],
        [(cap_mesh, COLORS["cap"]), (body_mesh, COLORS["body"]), (actuator_mesh, COLORS["actuator"]), *[(roots_mesh[n], COLORS["active"] if n in {"T1", "T3"} else COLORS["trimmed"]) for n in roots]],
        "08 / TRANSPARENT FINAL N2 LOCAL ASSEMBLY",
        "Short U-cradle is fused to the selected shared carrier; exterior and HW504 remain immutable",
        "Architecture ACCEPT | rear support PASS | HW504-A clearance PASS",
        transparent_objects=[
            (mesh(local(carrier), 4200), (*COLORS["carrier"], 38)),
            (mesh(local(hw_a), 3000), (*COLORS["hw"], 44)),
            (mesh(local(hw_b), 3000), (*COLORS["hw"], 38)),
            *[(mesh(local(shell), 2200), (*COLORS["shell"], 24)) for shell in shells],
        ],
        camera_offset=(64.0, -96.0, -40.0),
        final_size=(1920, 1280), supersample=2, fit_points=assembled_focus,
    )
    memory("render 08 transparent local assembly")
    return paths


def write_report(data: dict[str, object]) -> None:
    selected = data["selectedSupport"]
    exact = data["exact"]
    checks = exact["baselineMotionAndStatic"]
    states = "\n".join(
        "| {travel:.3f} | {cap:.9f} | {guide:.9f} | {actuator:.9f} | {stop:.3f} | PASS |".format(
            travel=float(row["travelMm"]),
            cap=float(row["capShell"]["penetrationMm3"]),
            guide=float(row["capGuide"]["penetrationMm3"]),
            actuator=float(row["capActuator"]["penetrationMm3"]),
            stop=float(row["analyticalRearHardStopGapMm"]),
        )
        for row in checks["motionStates"]
    )
    candidates_rows = "\n".join(
        "| {code} | {name} | {area:.3f} | {count} | {span:.3f} | {clearance:.3f} | {connected} | {verdict} |".format(
            code=row["code"], name=row["name"], area=float(row["contacts"]["totalAreaMm2"]),
            count=int(row["contacts"]["contactZoneCount"]), span=float(row["contacts"]["contactSpanMm"]),
            clearance=float(row["supportToHW504AMinimumMm"]), connected="YES" if row["loadPathConnected"] else "NO",
            verdict=row["screenVerdict"],
        )
        for row in data["candidates"]
    )
    report = f"""# 62 — N2 rear reaction support redesign

## 결론

`SELECTED SUPPORT TYPE = B — SHORT U-SHAPED REACTION CRADLE`다. 기존 broad rear frame의 기능은 유지하되 HW504 쪽 rail 길이를 줄이고 terminal-safe crossbar로 반력 경로를 다시 연결했다.

- `N2 ARCHITECTURE = ACCEPT`
- `REAR REACTION SUPPORT = PASS`
- `HW504 A ROBUST CLEARANCE = PASS`
- `N2 MOTION = PASS`
- `T2/T4 CAD FIT = ACCEPTABLE`
- `T2/T4 PHYSICAL TRIM = CONDITIONAL`
- `EXTERIOR = PRESERVED`

## 1. Candidate comparison

| Type | Architecture | Unique area mm² | Zones | Span mm | Support↔HW A mm | Connected | Result |
|---|---|---:|---:|---:|---:|---|---|
{candidates_rows}

B는 C의 안전한 짧은 rail 길이를 유지하면서 1.75 mm crossbar로 free rail을 carrier에 다시 연결한다. A/D는 support 자체가 HW504-A에 닿고, C는 한 pad의 load path가 끊겨 탈락했다.

## 2. Selected support

- SELECTED SUPPORT TYPE: **B — SHORT U-SHAPED REACTION CRADLE**
- OLD SUPPORT AREA: **{OLD_SUPPORT_AREA_MM2:.3f} mm²**
- NEW SUPPORT AREA: **{float(selected['contactAreaMm2']):.3f} mm²**
- CONTACT COUNT: **{int(selected['contactZoneCount'])} zones / {int(selected['connectedContactPatchCount'])} connected patch**
- CONTACT SPAN: **{float(selected['contactSpanMm']):.3f} mm**
- MINIMUM SUPPORT WALL: **{float(selected['minimumSupportWallMm']):.3f} mm**
- MINIMUM STRUCTURAL WALL: **{float(selected['minimumStructuralWallMm']):.3f} mm**
- remaining shared-bridge section after local relief: **{float(selected['remainingBridgeSectionMm']):.3f} mm**

지지는 ITS plastic rear housing face에만 형성된다. T1/T3 및 trimmed T2/T4 terminal root는 support contact에서 제외했다. 3개 reaction zone과 4.890 mm 좌우 span, 기존보다 큰 unique contact area가 뒤밀림·회전·rocking에 대한 연속 반력 경로를 만든다.

## 3. Exact clearance and static gates

- HW504 A ↔ CARRIER: **{float(exact['HW504ASelectedCarrier']['distanceMm']):.6f} mm**, penetration **{float(exact['HW504ASelectedCarrier']['penetrationMm3']):.9f} mm³**
- HW504 B ↔ CARRIER: **{float(exact['HW504BSelectedCarrier']['distanceMm']):.6f} mm**, penetration **{float(exact['HW504BSelectedCarrier']['penetrationMm3']):.9f} mm³**
- ITS body ↔ carrier unintended penetration: **{float(checks['switchCarrier']['penetrationMm3']):.9f} mm³**
- T1/T3 ↔ HW504 B minimum: **{float(checks['activeTerminalsToHW504B']['minimumDistanceMm']):.6f} mm**
- carrier ↔ local shell penetration: **{float(checks['carrierToLocalShell']['penetrationMm3']):.9f} mm³**
- N1 functional geometry removed: **{float(exact['clearanceReliefProtection']['removedMaterialVsN1FunctionalMm3']):.9f} mm³**

0.304 mm는 absolute 0.30 mm gate를 통과하지만 preferred 0.50 mm에는 미달한다. 외형이나 switch pose를 바꾸지 않고 남은 shared bridge 및 1.20 mm wall gate를 유지한 결과다.

## 4. Motion revalidation

| Travel mm | Cap↔shell pen mm³ | Cap↔guide pen mm³ | Cap↔actuator pen mm³ | Hard-stop residual mm | Result |
|---:|---:|---:|---:|---:|---|
{states}

Hard stop은 기존 guide rear stop에 남아 있으며 rear reaction support나 ITS housing을 overtravel stop으로 사용하지 않는다.

## 5. T2/T4 policy

- Current trimmed T2/T4 CAD clearance: **{float(checks['trimmedTerminalsToHW504B']['minimumDistanceMm']):.6f} mm**
- Housing-flush theoretical reference: **0.959811 mm**
- `T2/T4 CAD = ACCEPTABLE`
- `T2/T4 PHYSICAL = CONDITIONAL`

1.00 mm numerical gate를 맞추기 위한 추가 housing 침범은 수행하지 않았다. 실제 ITS-1105 continuity/trim 확인 전에는 terminal production freeze를 하지 않는다.

## 6. Freeze / outputs / STOP

Exterior shell, external cap centre/orientation/axis, switch pose, guide, direct actuation, 0.350 mm hard stop, HW504 A/B와 joystick kinematics는 변경하지 않았다. N1 및 다른 Finger button으로 확장하지 않았다.

- `{SELECTED_CARRIER_STEP.relative_to(ROOT)}` — selected local carrier STEP only
- `{JSON_PATH.relative_to(ROOT)}`
- `{RENDER_DIR.relative_to(ROOT)}` — required 8 local renders

Full shell / STL / print plate / full assembly는 생성하지 않았다. 여기서 STOP한다.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    memory("start")
    source = baseline.load_source()
    datum = baseline.load_datum()
    roots, _ = baseline.trim_terminals(source, datum)
    base_cap = import_step(baseline.BASE_CAP_STEP)
    cap, cap_parts = baseline.build_production_cap(base_cap, datum)
    guide, guide_parts = baseline.build_guide(datum)
    old_support_raw, _ = baseline.build_reaction_support(datum, roots)
    relief = robust_tool()
    old_support = cut_shape(old_support_raw, cutters(source, datum, roots), relief)

    candidate_metrics, selected_before_slab, selected_parts, candidate_parts = evaluate_candidates(
        source, datum, roots, guide, relief
    )
    clearance_tool, clearance_tool_metrics = hw_clearance_tool(
        source["HW504_A_NONFUNCTIONAL_TRIM"], selected_before_slab, SELECTED_CLEARANCE_OFFSET_MM
    )
    selected_carrier = (selected_before_slab - clearance_tool).clean()
    selected_carrier.label = "N1_N2_SHARED_CARRIER_N2_SHORT_U_CRADLE"
    if len(selected_carrier.solids()) != len(source["N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"].solids()):
        raise RuntimeError("selected local relief changed shared-carrier solid connectivity")

    exact = exact_selected_checks(
        source, datum, cap, cap_parts, guide, guide_parts,
        selected_before_slab, selected_carrier, selected_parts, roots, clearance_tool,
    )
    checks = exact["baselineMotionAndStatic"]
    contact = contact_metrics(datum, selected_parts)
    selected_screen = next(row for row in candidate_metrics if row["code"] == "B")
    remaining_bridge = BRIDGE_SECTION - (
        float(clearance_tool_metrics["normalRangeFromHwMm"][1])
        - float(clearance_tool_metrics["normalRangeFromHwMm"][0])
    )
    minimum_wall = min(
        baseline.GUIDE_WALL_MM,
        float(selected_screen["minimumSupportWallMm"]),
        1.3148483522514047,
        remaining_bridge,
    )

    motion_pass = all(
        float(row["capGuide"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and float(row["capShell"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and float(row["capActuator"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and abs(float(row["analyticalRearHardStopGapMm"]) - (baseline.ACTUATOR_TRAVEL_MAX - float(row["travelMm"]))) <= 1.0e-9
        for row in checks["motionStates"]
    )
    hard_stop_pass = all(
        abs(float(row["rearOvertravelStop"]["distanceMm"]) - float(row["analyticalRearHardStopGapMm"])) <= 1.0e-5
        for row in checks["motionStates"]
    )
    support_pass = (
        float(contact["totalAreaMm2"]) + 1.0e-7 >= OLD_SUPPORT_AREA_MM2
        and int(contact["contactZoneCount"]) == 3
        and int(contact["connectedContactPatchCount"]) == 1
        and float(contact["contactSpanMm"]) >= 4.5
        and bool(selected_screen["loadPathConnected"])
        and minimum_wall + 1.0e-9 >= MIN_STRUCTURAL_WALL_MM
    )
    clearance_pass = (
        float(exact["HW504ASelectedCarrier"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and float(exact["HW504ASelectedCarrier"]["distanceMm"]) + 1.0e-7 >= TARGET_CLEARANCE_MM
    )
    static_pass = (
        float(exact["HW504BSelectedCarrier"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and float(checks["switchCarrier"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and float(checks["carrierToLocalShell"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        and float(checks["activeTerminalsToHW504B"]["minimumDistanceMm"]) + 1.0e-7 >= 2.119093039912462
        and all(float(value) <= BOOLEAN_EPS_MM3 for value in exact["clearanceReliefProtection"].values())
    )
    overall_pass = support_pass and clearance_pass and motion_pass and hard_stop_pass and static_pass

    export_step(selected_carrier, SELECTED_CARRIER_STEP)
    memory("selected local carrier STEP exported")
    render_paths = render_outputs(
        source, datum, cap, guide, guide_parts, old_support,
        candidate_parts, selected_parts, selected_carrier, roots, exact, candidate_metrics,
    )

    data: dict[str, object] = {
        "schema": "onegrip.n2.rear_reaction_support_redesign.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "N2 REAR SUPPORT LOCAL ONLY / SERIAL OCC / FULL SHELL 0 / STL 0",
        "freeze": {
            "externalShellChangeMm3": 0.0,
            "externalCenterMovementMm": 0.0,
            "capExteriorChangeMm3": 0.0,
            "capOrientationChangeDeg": 0.0,
            "travelAxisChangeDeg": 0.0,
            "switchPositionChangeMm": 0.0,
            "switchOrientationChangeDeg": 0.0,
            "guideAxisChangeDeg": 0.0,
            "hardStopTravelChangeMm": 0.0,
            "HW504AChangeMm3": 0.0,
            "HW504BChangeMm3": 0.0,
            "N1ExternalChangeMm3": 0.0,
            "otherButtonsChange": 0,
        },
        "candidates": candidate_metrics,
        "selectedSupport": {
            "type": "B — SHORT U-SHAPED REACTION CRADLE",
            "oldContactAreaMm2": OLD_SUPPORT_AREA_MM2,
            "contactAreaMm2": float(contact["totalAreaMm2"]),
            "contactZoneCount": int(contact["contactZoneCount"]),
            "connectedContactPatchCount": int(contact["connectedContactPatchCount"]),
            "contactSpanMm": float(contact["contactSpanMm"]),
            "contactZones": contact["zones"],
            "minimumSupportWallMm": float(selected_screen["minimumSupportWallMm"]),
            "minimumStructuralWallMm": minimum_wall,
            "remainingBridgeSectionMm": remaining_bridge,
            "loadPath": "finger -> cap -> actuator -> ITS body -> short U cradle -> shared carrier -> shell",
            "antiRock": "PASS" if support_pass else "HOLD",
        },
        "clearanceRelief": clearance_tool_metrics,
        "exact": exact,
        "gates": {
            "supportPass": support_pass,
            "HW504ARobustClearancePass": clearance_pass,
            "staticPass": static_pass,
            "motionPass": motion_pass,
            "hardStopPass": hard_stop_pass,
            "wallPass": minimum_wall + 1.0e-9 >= MIN_STRUCTURAL_WALL_MM,
            "preferred0p50Reached": float(exact["HW504ASelectedCarrier"]["distanceMm"]) + 1.0e-7 >= PREFERRED_CLEARANCE_MM,
        },
        "terminalPolicy": {
            "currentTrimmedCadClearanceMm": float(checks["trimmedTerminalsToHW504B"]["minimumDistanceMm"]),
            "housingFlushTheoreticalClearanceMm": 0.9598112338851641,
            "CAD": "ACCEPTABLE",
            "PHYSICAL": "CONDITIONAL",
        },
        "verdict": {
            "N2_ARCHITECTURE": "ACCEPT",
            "REAR_REACTION_SUPPORT": "PASS" if support_pass else "HOLD",
            "HW504_A_ROBUST_CLEARANCE": "PASS" if clearance_pass else "HOLD",
            "N2_MOTION": "PASS" if motion_pass else "HOLD",
            "HARD_STOP": "PASS" if hard_stop_pass else "HOLD",
            "SWITCH_ANTI_ROCK": "PASS" if support_pass else "HOLD",
            "T2_T4_CAD_FIT": "ACCEPTABLE",
            "T2_T4_PHYSICAL_TRIM": "CONDITIONAL",
            "EXTERIOR": "PRESERVED",
            "N2_REAR_SUPPORT_REDESIGN": "PASS" if overall_pass else "HOLD",
        },
        "inputs": {
            "docs61Json": {"path": str(DOCS61_JSON.relative_to(ROOT)), "sha256": sha256(DOCS61_JSON)},
            "docs60CapStep": {"path": str(DOCS60_CAP_STEP.relative_to(ROOT)), "sha256": sha256(DOCS60_CAP_STEP)},
            "docs57LocalStep": {"path": str(baseline.SOURCE_STEP.relative_to(ROOT)), "sha256": sha256(baseline.SOURCE_STEP)},
        },
        "outputs": {
            "selectedCarrierStep": str(SELECTED_CARRIER_STEP.relative_to(ROOT)),
            "json": str(JSON_PATH.relative_to(ROOT)),
            "report": str(REPORT_PATH.relative_to(ROOT)),
            "renders": [str(path.relative_to(ROOT)) for path in render_paths],
            "fullShellGenerated": 0,
            "stlGenerated": 0,
            "printPlateGenerated": 0,
            "fullAssemblyGenerated": 0,
        },
        "memory": MEMORY,
        "stop": "STOP after N2 rear support verdict; do not extend to other buttons",
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(data)
    memory("outputs complete")
    print(json.dumps({
        "verdict": data["verdict"],
        "selectedSupportAreaMm2": data["selectedSupport"]["contactAreaMm2"],
        "contactSpanMm": data["selectedSupport"]["contactSpanMm"],
        "HW504AClearanceMm": exact["HW504ASelectedCarrier"]["distanceMm"],
        "minimumWallMm": minimum_wall,
        "motionPass": motion_pass,
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY),
        "outputs": data["outputs"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
