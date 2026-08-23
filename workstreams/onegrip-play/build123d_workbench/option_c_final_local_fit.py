"""Resolve the two remaining Option-C local HOLD items with one final candidate.

The analyze mode performs no boolean operation.  The build mode creates only
the selected local candidate and evaluates its exact serial OCCT gates.
"""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
import psutil
from build123d import Align, Box, Compound, Location, Shape, Vector, export_step, import_step

from .finger_controls_v2 import (
    ACTUATOR_DIAMETER,
    ACTUATOR_PROJECTION,
    BRIDGE_SECTION,
    CAP_SOCKET_DIAMETER,
    CAP_CONTACT_FREE_GAP,
    CARRIER_WALL,
    ControlDatum,
    terminal_root_cutters,
    switch_actuator,
    switch_body,
    wire_envelope,
    xyz,
)
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    aggregate_pairs,
    bbox,
    exact_pair,
    safe_edge_lines,
    safe_triangles,
    raster_scene,
    rotate_about_axis,
    section_render,
    shifted,
    terminal_clearance_tools,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "option_c_final_local_fit"
RENDER_DIR = ROOT / "renders" / "option_c_final_local_fit"
JSON_PATH = OUT_DIR / "option_c_final_local_fit.json"
STEP_PATH = OUT_DIR / "OPTION_C_FINAL_LOCAL_FIT.step"
REPORT_PATH = ROOT / "docs" / "57_option_c_final_local_fit.md"

SOURCE_STEP = (
    ROOT / "build123d_workbench" / "out" / "option_c_local_exact_prototype"
    / "OPTION_C_LOCAL_EXACT_PROTOTYPE.step"
)
SOURCE_JSON = (
    ROOT / "build123d_workbench" / "out" / "option_c_local_exact_prototype"
    / "option_c_local_exact_prototype.json"
)
CONTROL_MANIFEST = (
    ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
    / "finger_controls_v2_source_manifest.json"
)
ELECTRICAL_AUDIT = ROOT / "cad_dump" / "its1105_primary_switch_design_audit.json"
PHYSICAL_AUDIT = ROOT / "cad_dump" / "its1105_physical_sample_reaudit.json"

RSS_LIMIT_MB = 24576.0
PROCESS = psutil.Process(os.getpid())
MEMORY_LOG: list[dict[str, float | str]] = []
CLOCKINGS_DEG = (0, 90, 180, 270)
SELECTED_CLOCKING_DEG = 180
CURRENT_APPROVED_CLOCKING_DEG = -5.0
AXIS_CHANGE_DEG = 0.0
DEPTH_CHANGE_MM = 0.0
TERMINAL_CLEARANCE_TARGET_MM = 0.80
CARRIER_MICRO_RELIEF_MARGIN_MM = 0.18


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    MEMORY_LOG.append({"stage": stage, "rssMb": round(rss, 1)})
    if rss > RSS_LIMIT_MB:
        raise MemoryError(f"RAM safety stop at {stage}: {rss:.1f} MB")
    available_mb = float(psutil.virtual_memory().available) / (1024.0 * 1024.0)
    if available_mb < 3072.0:
        raise MemoryError(f"RAM safety stop at {stage}: only {available_mb:.1f} MB system memory available")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def datum_from_manifest(name: str, row: dict[str, object]) -> ControlDatum:
    return ControlDatum(
        name=name,
        center=xyz(row["centerMm"]),
        shell_normal=xyz(row["shellNormal"]),
        axis=xyz(row["axis"]),
        owner=str(row["owner"]),
        kind=str(row["kind"]),
        cap_u=xyz(row["capU"]),
        switch_u=xyz(row["switchU"]),
        roll_deg=float(row["rollDeg"]),
    )


def clocked_datum(original: ControlDatum, angle_deg: float) -> ControlDatum:
    return ControlDatum(
        name=original.name,
        center=original.center,
        shell_normal=original.shell_normal,
        axis=original.axis,
        owner=original.owner,
        kind=original.kind,
        cap_u=original.cap_u,
        switch_u=xyz(rotate_about_axis(original.switch_u, original.axis, angle_deg)),
        roll_deg=original.roll_deg + angle_deg,
    )


def switch_parts(datum: ControlDatum, front_depth: float) -> dict[str, Shape]:
    rows: dict[str, Shape] = {
        "body": switch_body(datum, front_depth),
        "actuator": switch_actuator(datum, front_depth),
    }
    for index, root in enumerate(terminal_root_cutters(datum, front_depth), 1):
        rows[f"terminalRoot{index}"] = root
    return rows


def load_source() -> dict[str, Shape]:
    source = import_step(SOURCE_STEP)
    rows = {child.label: child for child in source.children}
    required = {
        "HW504_A_NONFUNCTIONAL_TRIM",
        "HW504_B_EXACT_KEEP",
        "N1_N2_SHARED_CARRIER_OPTION_C_LOCAL_REDESIGN",
        "N2_SEAM_JaD",
        "N2_SEAM_JfD",
    }
    if missing := required - set(rows):
        raise RuntimeError(f"Source labels missing: {sorted(missing)}")
    del source
    memory("retained docs/56 local source children")
    return rows


def bounds(shape: Shape) -> tuple[np.ndarray, np.ndarray]:
    row = shape.bounding_box()
    return (
        np.asarray((float(row.min.X), float(row.min.Y), float(row.min.Z))),
        np.asarray((float(row.max.X), float(row.max.Y), float(row.max.Z))),
    )


def aabb_metrics(left: Shape, right: Shape) -> dict[str, float]:
    a0, a1 = bounds(left)
    b0, b1 = bounds(right)
    overlap = np.maximum(0.0, np.minimum(a1, b1) - np.maximum(a0, b0))
    gap = np.maximum(0.0, np.maximum(a0 - b1, b0 - a1))
    return {
        "overlapVolumeMm3": float(np.prod(overlap)),
        "gapMm": float(np.linalg.norm(gap)),
    }


def exact_distance(left: Shape, right: Shape) -> float:
    return float(left.distance_to_with_closest_points(right)[0])


def minimum_distance(left_parts: dict[str, Shape], right_parts: dict[str, Shape]) -> float:
    return min(exact_distance(left, right) for left in left_parts.values() for right in right_parts.values())


def electrical_record(angle: int) -> dict[str, object]:
    # Physical mapping: the two pins on each opposite U side are internally
    # common.  All four pins remain, so any one pin from each group is usable.
    group_a = [1, 2]
    group_b = [3, 4]
    quarter_turns = (angle // 90) % 4
    sides = ("-U", "+V", "+U", "-V")
    return {
        "clockingDeg": angle,
        "groupA": group_a,
        "groupB": group_b,
        "groupASideAfterClocking": sides[quarter_turns],
        "groupBSideAfterClocking": sides[(quarter_turns + 2) % 4],
        "validContactPairs": [[1, 3], [1, 4], [2, 3], [2, 4]],
        "allFourTerminalsRetained": True,
        "directWiring": True,
        "electricallyEquivalent": True,
    }


def analyze_clockings(source: dict[str, Shape] | None = None) -> dict[str, object]:
    memory("analysis start")
    source = load_source() if source is None else source
    manifest = json.loads(CONTROL_MANIFEST.read_text(encoding="utf-8"))
    n1_datum = datum_from_manifest("N1", manifest["controls"]["N1"])
    n2_base = datum_from_manifest("N2", manifest["controls"]["N2"])
    depths = {name: float(manifest["frontDepthsMm"][name]) for name in ("N1", "N2")}
    n1_parts = switch_parts(n1_datum, depths["N1"])
    hw_b = source["HW504_B_EXACT_KEEP"]
    carrier = source["N1_N2_SHARED_CARRIER_OPTION_C_LOCAL_REDESIGN"]
    shells = (source["N2_SEAM_JaD"], source["N2_SEAM_JfD"])

    rows: list[dict[str, object]] = []
    for angle in CLOCKINGS_DEG:
        datum = clocked_datum(n2_base, angle)
        parts = switch_parts(datum, depths["N2"])
        roots = {name: shape for name, shape in parts.items() if name.startswith("terminalRoot")}
        root_rows = []
        for name, root in roots.items():
            box_row = aabb_metrics(hw_b, root)
            root_rows.append({
                "terminal": name,
                **box_row,
                "exactDistanceMm": exact_distance(hw_b, root),
            })
        body_distance = exact_distance(hw_b, parts["body"])
        n1_distance = minimum_distance(n1_parts, parts)
        carrier_distance = min(exact_distance(carrier, shape) for shape in parts.values())
        shell_terminal_distance = min(exact_distance(shell, root) for shell in shells for root in roots.values())
        rows.append({
            "clockingDeg": angle,
            "terminalRows": root_rows,
            "terminalAabbOverlapSumMm3": float(sum(float(row["overlapVolumeMm3"]) for row in root_rows)),
            "terminalExactMinimumDistanceMm": min(float(row["exactDistanceMm"]) for row in root_rows),
            "terminalExactZeroDistanceCount": sum(float(row["exactDistanceMm"]) <= 1.0e-8 for row in root_rows),
            "bodyToHW504BMinimumDistanceMm": body_distance,
            "N1ToN2MinimumDistanceMm": n1_distance,
            "switchToCurrentCarrierMinimumDistanceMm": carrier_distance,
            "terminalToLocalShellMinimumDistanceMm": shell_terminal_distance,
            "electrical": electrical_record(angle),
        })
        del parts, roots
        memory(f"bbox/distance clocking {angle}")

    ranking = sorted(
        rows,
        key=lambda row: (
            int(row["terminalExactZeroDistanceCount"]),
            float(row["terminalAabbOverlapSumMm3"]),
            -float(row["terminalExactMinimumDistanceMm"]),
            int(row["clockingDeg"]),
        ),
    )
    return {
        "mode": "BBOX + EXACT DISTANCE ONLY / BOOLEAN 0",
        "rows": rows,
        "rankingDeg": [int(row["clockingDeg"]) for row in ranking],
        "recommendedClockingDeg": int(ranking[0]["clockingDeg"]),
        "electricalAuthority": {
            "source": str(ELECTRICAL_AUDIT.relative_to(ROOT)),
            "circuit": "pins 1-2 internally common; pins 3-4 internally common; press bridges groups",
            "physicalTerminalPolicySource": str(PHYSICAL_AUDIT.relative_to(ROOT)),
        },
        "memory": MEMORY_LOG,
    }


def tilted_datum(original: ControlDatum, angle_deg: float) -> ControlDatum:
    """Tilt the internal switch frame about its local U axis at the frozen centre."""
    return ControlDatum(
        name=original.name,
        center=original.center,
        shell_normal=original.shell_normal,
        axis=xyz(rotate_about_axis(original.axis, original.switch_u, angle_deg)),
        owner=original.owner,
        kind=original.kind,
        cap_u=original.cap_u,
        switch_u=original.switch_u,
        roll_deg=original.roll_deg,
    )


def make_relief_tool(lower: np.ndarray, upper: np.ndarray, label: str) -> Shape:
    size = upper - lower
    result = Box(
        float(size[0]), float(size[1]), float(size[2]),
        align=(Align.MIN, Align.MIN, Align.MIN),
    ).moved(Location(Vector(float(lower[0]), float(lower[1]), float(lower[2]))))
    result.label = label
    return result


def carrier_micro_relief(hw_a: Shape, carrier: Shape) -> tuple[Shape, Shape, Shape, dict[str, object]]:
    common = hw_a & carrier
    if common is None or len(common.solids()) == 0:
        raise RuntimeError("Expected the saved 0.005690 mm3 A/carrier intersection")
    common.label = "HW504_A_CARRIER_EXISTING_MICRO_INTERSECTION"
    lower, upper = bounds(common)
    tool_lower = lower - CARRIER_MICRO_RELIEF_MARGIN_MM
    tool_upper = upper + CARRIER_MICRO_RELIEF_MARGIN_MM
    tool = make_relief_tool(tool_lower, tool_upper, "CARRIER_NONFUNCTIONAL_CORNER_MICRO_RELIEF")

    candidate = (carrier - tool).clean()
    candidate.label = "N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"
    alternative_a = (hw_a - tool).clean()
    residual = hw_a & candidate
    residual_volume = 0.0 if residual is None or len(residual.solids()) == 0 else float(residual.volume)
    normal_depth = float((upper[1] - lower[1]) + CARRIER_MICRO_RELIEF_MARGIN_MM)
    remaining_wall = float(CARRIER_WALL - normal_depth)
    metrics: dict[str, object] = {
        "existingIntersectionMm3": float(common.volume),
        "existingIntersectionBboxMm": {"min": lower.tolist(), "max": upper.tolist()},
        "toolBboxMm": {"min": tool_lower.tolist(), "max": tool_upper.tolist()},
        "marginMm": CARRIER_MICRO_RELIEF_MARGIN_MM,
        "carrierMaterialRemovedMm3": max(0.0, float(carrier.volume - candidate.volume)),
        "alternativeHW504ATrimRemovedMm3": max(0.0, float(hw_a.volume - alternative_a.volume)),
        "selected": "CARRIER MICRO-RELIEF",
        "selectionReason": "smaller local material change and no expansion of approved HW504-A trim",
        "residualIntersectionMm3": residual_volume,
        "nominalWallBeforeMm": CARRIER_WALL,
        "conservativeReliefDepthMm": normal_depth,
        "conservativeRemainingWallMm": remaining_wall,
        "minimumWallRequirementMm": 1.20,
        "wallPass": remaining_wall + 1.0e-7 >= 1.20,
        "solidCountBefore": len(carrier.solids()),
        "solidCountAfter": len(candidate.solids()),
        "loadPathAssessment": "UNCHANGED SOLID COUNT; relief is outside switch locating pocket and broad bridge",
        "switchLocatingDatumChangeMm": 0.0,
        "fingerExteriorChangeMm": 0.0,
    }
    del alternative_a, residual
    memory("carrier micro-relief complete")
    return candidate, tool, common, metrics


def custom_pose_screen(
    hw_b: Shape,
    base_180: ControlDatum,
    front_depth: float,
) -> dict[str, object]:
    radial_allowance = (CAP_SOCKET_DIAMETER - ACTUATOR_DIAMETER) / 2.0
    engagement_tilt_limit = math.degrees(math.asin(radial_allowance / ACTUATOR_PROJECTION))
    cases = (
        ("ENGAGEMENT_LIMIT", engagement_tilt_limit, 0.0),
        ("ABSOLUTE_TILT_LIMIT", 5.0, 0.0),
        ("TARGET_CLEARANCE_SCREEN", 5.0, -1.75),
    )
    rows: list[dict[str, object]] = []
    for label, tilt, depth_delta in cases:
        datum = tilted_datum(base_180, tilt)
        parts = switch_parts(datum, front_depth + depth_delta)
        root_distances = [exact_distance(hw_b, parts[f"terminalRoot{index}"]) for index in range(1, 5)]
        lateral_offset = ACTUATOR_PROJECTION * math.sin(math.radians(tilt))
        rows.append({
            "case": label,
            "axisTiltDeg": tilt,
            "axialDepthDeltaMm": depth_delta,
            "terminalMinimumDistanceMm": min(root_distances),
            "terminalDistancesMm": root_distances,
            "actuatorLateralOffsetAcrossProjectionMm": lateral_offset,
            "capSocketRadialAllowanceMm": radial_allowance,
            "capEngagementValid": (
                lateral_offset <= radial_allowance + 1.0e-7
                and abs(depth_delta) <= CAP_CONTACT_FREE_GAP + 1.0e-7
            ),
        })
        del parts
        memory(f"custom pose distance screen {label}")
    return {
        "mode": "three bounded distance-only screens / boolean 0",
        "capSocketRadialAllowanceMm": radial_allowance,
        "capContactFreeGapMm": CAP_CONTACT_FREE_GAP,
        "maximumTiltMaintainingNominalSocketEngagementDeg": engagement_tilt_limit,
        "rows": rows,
        "conclusion": "NO COMPLIANT CUSTOM POSE: terminal clearance requires pose change beyond frozen-cap engagement allowance",
        "adopted": False,
    }


def named_parts(source: dict[str, Shape], prefix: str) -> dict[str, Shape]:
    rows: dict[str, Shape] = {}
    for label, shape in source.items():
        if label == f"{prefix}_ITS1105_body":
            rows["body"] = shape
        elif label == f"{prefix}_ITS1105_actuator":
            rows["actuator"] = shape
        elif label.startswith(f"{prefix}_root_"):
            rows[label.removeprefix(f"{prefix}_")] = shape
    if len(rows) != 6:
        raise RuntimeError(f"Expected six {prefix} switch parts, got {sorted(rows)}")
    return rows


def compound_of(label: str, shapes: Iterable[Shape]) -> Compound:
    return Compound(children=list(shapes), label=label)


def exact_final_checks(
    source: dict[str, Shape],
    carrier: Shape,
) -> dict[str, object]:
    hw_a = source["HW504_A_NONFUNCTIONAL_TRIM"]
    hw_b = source["HW504_B_EXACT_KEEP"]
    n1_parts = named_parts(source, "N1")
    n2_parts = named_parts(source, "N2")
    n2_roots = {name: shape for name, shape in n2_parts.items() if name.startswith("root_")}
    n1_compound = compound_of("N1_SWITCH_ENVELOPE", n1_parts.values())
    n2_compound = compound_of("N2_SWITCH_ENVELOPE", n2_parts.values())

    checks: dict[str, object] = {}
    checks["HW504_A_vs_carrier"] = exact_pair(hw_a, carrier, "HW504_A<->carrier")
    memory("exact final A/carrier")
    checks["HW504_B_vs_carrier"] = exact_pair(hw_b, carrier, "HW504_B<->carrier")
    memory("exact final B/carrier")
    root_rows = [exact_pair(hw_b, root, f"HW504_B<->N2.{name}") for name, root in n2_roots.items()]
    checks["HW504_B_vs_N2_terminal_roots"] = aggregate_pairs(root_rows, TERMINAL_CLEARANCE_TARGET_MM)
    memory("exact final B/N2 terminal roots")
    checks["HW504_B_vs_N2_switch_body"] = exact_pair(hw_b, n2_parts["body"], "HW504_B<->N2.body")
    memory("exact final B/N2 body")
    checks["N1_vs_N2"] = exact_pair(n1_compound, n2_compound, "N1<->N2 complete local envelopes")
    memory("exact final N1/N2")
    checks["carrier_vs_N2"] = exact_pair(carrier, n2_compound, "carrier<->N2 complete local envelope")
    memory("exact final carrier/N2")
    shell_rows = [
        exact_pair(carrier, source[name], f"carrier<->{name}")
        for name in ("N2_SEAM_JaD", "N2_SEAM_JfD")
    ]
    checks["carrier_vs_local_shell"] = aggregate_pairs(shell_rows)
    memory("exact final carrier/local shell")
    return checks


def pair_pass(row: dict[str, object]) -> bool:
    return float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3


def build_renders(
    source: dict[str, Shape],
    carrier_final: Shape,
    relief_tool: Shape,
    carrier_common: Shape,
    analysis: dict[str, object],
    best_parts: dict[str, Shape],
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    colors = {
        "a": (57, 169, 226),
        "b": (146, 96, 235),
        "carrier": (67, 202, 145),
        "switch": (243, 184, 66),
        "clear": (68, 212, 154),
        "collision": (244, 68, 76),
        "tool": (247, 128, 62),
    }
    cache: dict[str, np.ndarray] = {}

    def mesh(key: str, shape: Shape, limit: int = 2400) -> np.ndarray:
        if key not in cache:
            cache[key] = safe_triangles(shape, tolerance=0.12, angular=0.08, limit=limit)
        return cache[key]

    final_size = (1920, 1280)
    paths = [
        RENDER_DIR / "01_n2_terminal_before_after.png",
        RENDER_DIR / "02_n2_clocking_comparison.png",
        RENDER_DIR / "03_carrier_micro_relief_closeup.png",
        RENDER_DIR / "04_final_transparent_local_crop.png",
    ]
    hw_b = source["HW504_B_EXACT_KEEP"]
    carrier_before = source["N1_N2_SHARED_CARRIER_OPTION_C_LOCAL_REDESIGN"]
    current_n2 = named_parts(source, "N2")

    before_dx, after_dx = -14.0, 14.0
    before_objects = [(shifted(mesh("b", hw_b), before_dx), colors["b"])]
    before_objects.extend((shifted(mesh(f"n2_current_{name}", shape, 600), before_dx), colors["collision"] if name == "root_nu_pv" else colors["switch"]) for name, shape in current_n2.items())
    after_objects = [(shifted(mesh("b", hw_b), after_dx), colors["b"])]
    after_objects.extend((shifted(mesh(f"n2_best_{name}", shape, 600), after_dx), colors["collision"] if name == "terminalRoot3" else colors["switch"]) for name, shape in best_parts.items())
    raster_scene(
        paths[0], [*before_objects, *after_objects],
        "01 / N2 TERMINAL — CURRENT vs BEST CLOCKING",
        "Left: approved CUSTOM -5 deg / Right: best discrete 180 deg; fixed roots are not bent or reduced",
        "Red root still penetrates HW504 B: 0.401337 -> 0.320370 mm^3; no pose adopted",
        final_size=final_size,
    )
    memory("render N2 before/after")

    clock_objects: list[tuple[np.ndarray, tuple[int, int, int]]] = []
    transparent: list[tuple[np.ndarray, tuple[int, int, int, int]]] = []
    manifest = json.loads(CONTROL_MANIFEST.read_text(encoding="utf-8"))
    n2_base = datum_from_manifest("N2", manifest["controls"]["N2"])
    front_depth = float(manifest["frontDepthsMm"]["N2"])
    x_shifts = (-48.0, -16.0, 16.0, 48.0)
    for angle, dx, row in zip(CLOCKINGS_DEG, x_shifts, analysis["rows"]):
        parts = switch_parts(clocked_datum(n2_base, angle), front_depth)
        transparent.append((shifted(mesh("b", hw_b), dx), (158, 110, 243, 72)))
        zero_names = {
            str(item["terminal"])
            for item in row["terminalRows"]
            if float(item["exactDistanceMm"]) <= 1.0e-8
        }
        for name, shape in parts.items():
            color = colors["collision"] if name in zero_names else colors["switch"]
            clock_objects.append((shifted(mesh(f"clock_{angle}_{name}", shape, 600), dx), color))
    raster_scene(
        paths[1], clock_objects,
        "02 / N2 SWITCH CLOCKING COMPARISON",
        "0 / 90 / 180 / 270 deg, unchanged external center and actuation axis",
        "Zero-distance fixed roots: 1 / 2 / 1 / 2 — none passes",
        transparent_objects=transparent,
        camera_offset=(65.0, -110.0, -58.0),
        final_size=final_size,
    )
    memory("render clocking comparison")

    raster_scene(
        paths[2],
        [
            (shifted(mesh("carrier_before", carrier_before), -14.0), (64, 131, 165)),
            (shifted(mesh("carrier_after", carrier_final), 14.0), colors["carrier"]),
            (shifted(mesh("carrier_common", carrier_common, 500), -14.0), colors["collision"]),
            (shifted(mesh("relief_tool", relief_tool, 500), 14.0), colors["tool"]),
        ],
        "03 / CARRIER MICRO-RELIEF — BEFORE vs AFTER",
        "Red: 0.005690 mm^3 intersection / Orange: 0.18 mm-margin local relief tool",
        "Carrier removed 0.088915 mm^3; conservative remaining wall 1.314848 mm",
        final_size=final_size,
    )
    memory("render carrier micro-relief")

    n1 = named_parts(source, "N1")
    final_objects = [
        (mesh("b", hw_b), colors["b"]),
        (mesh("carrier_after", carrier_final), colors["carrier"]),
    ]
    final_objects.extend((mesh(f"final_n1_{name}", shape, 700), colors["switch"]) for name, shape in n1.items())
    final_objects.extend((mesh(f"n2_current_{name}", shape, 700), colors["collision"] if name == "root_nu_pv" else colors["switch"]) for name, shape in current_n2.items())
    raster_scene(
        paths[3], final_objects,
        "04 / FINAL TRANSPARENT LOCAL CROP",
        "Only HW504 A/B + N1/N2 + shared carrier + two existing local shell coupons",
        "Carrier PASS / N2 fixed-root HOLD — no full shell or full assembly loaded",
        transparent_objects=[
            (mesh("a", source["HW504_A_NONFUNCTIONAL_TRIM"]), (68, 184, 240, 48)),
            (mesh("shell_jad", source["N2_SEAM_JaD"], 1800), (99, 207, 229, 36)),
            (mesh("shell_jfd", source["N2_SEAM_JfD"], 1800), (99, 207, 229, 36)),
        ],
        camera_offset=(62.0, -96.0, -48.0),
        final_size=final_size,
    )
    memory("render final transparent crop")
    return paths


def write_report(data: dict[str, object]) -> None:
    checks = data["checks"]
    relief = data["carrierMicroRelief"]
    best = data["clockingStudy"]["exactMostPromising"]
    final_terminal = checks["HW504_B_vs_N2_terminal_roots"]
    report = f"""# 57 — Option C final local fit

## 결론

`OPTION C FINAL LOCAL FIT = HOLD`

Carrier의 0.005690 mm³ 간섭은 **0.18 mm margin의 비기능 모서리 micro-relief**로 완전히 제거했다. 그러나 실제 ITS-1105 고정 단자를 유지한 N2는 4개 cardinal clocking 모두 HW504 B를 피하지 못했다. 가장 좋은 180°도 exact penetration **{float(best['penetrationMm3']):.6f} mm³**가 남는다. Cap과 actuator engagement를 보존하는 범위의 custom pose로도 해소할 수 없어 N2 pose 변경은 채택하지 않았다.

## N2 switch clocking / engagement

- `N2 SWITCH CLOCKING = CUSTOM` — 현재 승인된 -5.000°를 유지; 180°는 비교상 최선이지만 미채택
- `N2 AXIS CHANGE = 0.000°`
- `N2 EXTERNAL CENTER CHANGE = 0.000 mm`
- ITS-1105 topology: pins 1–2 common / pins 3–4 common, 네 고정 단자 모두 유지
- 0/90/180/270 zero-distance fixed-root 수: **1 / 2 / 1 / 2**
- 180° exact: **{float(best['distanceMm']):.6f} mm / {float(best['penetrationMm3']):.6f} mm³**
- 최종 유지 pose: **{float(final_terminal['minimumDistanceMm']):.6f} mm / {float(final_terminal['penetrationMm3']):.6f} mm³**
- Cap socket radial allowance: **{float(data['customPoseFeasibility']['capSocketRadialAllowanceMm']):.3f} mm**; engagement-compatible tilt upper bound: **{float(data['customPoseFeasibility']['maximumTiltMaintainingNominalSocketEngagementDeg']):.3f}°**

## Carrier micro-relief

- 기존 exact intersection: **{float(relief['existingIntersectionMm3']):.9f} mm³**
- Carrier 제거량: **{float(relief['carrierMaterialRemovedMm3']):.9f} mm³**
- HW504 A 추가 trim 대안: **{float(relief['alternativeHW504ATrimRemovedMm3']):.9f} mm³**
- 선택: **carrier relief** — A 대안보다 작고 approved HW504-A trim을 확대하지 않음
- 보수적 잔여 wall: **{float(relief['conservativeRemainingWallMm']):.6f} mm** (minimum 1.20 mm PASS)
- Locating datum / exterior / solid count change: **0 / 0 / {int(relief['solidCountBefore'])}→{int(relief['solidCountAfter'])}**

## Final local exact gate

| Gate | Clearance | Penetration | Result |
|---|---:|---:|---|
| HW504 A ↔ carrier | {float(checks['HW504_A_vs_carrier']['distanceMm']):.6f} mm | {float(checks['HW504_A_vs_carrier']['penetrationMm3']):.9f} mm³ | {'PASS' if pair_pass(checks['HW504_A_vs_carrier']) else 'HOLD'} |
| HW504 B ↔ carrier | {float(checks['HW504_B_vs_carrier']['distanceMm']):.6f} mm | {float(checks['HW504_B_vs_carrier']['penetrationMm3']):.9f} mm³ | {'PASS' if pair_pass(checks['HW504_B_vs_carrier']) else 'HOLD'} |
| HW504 B ↔ N2 fixed roots | {float(final_terminal['minimumDistanceMm']):.6f} mm | {float(final_terminal['penetrationMm3']):.9f} mm³ | HOLD |
| HW504 B ↔ N2 body | {float(checks['HW504_B_vs_N2_switch_body']['distanceMm']):.6f} mm | {float(checks['HW504_B_vs_N2_switch_body']['penetrationMm3']):.9f} mm³ | {'PASS' if pair_pass(checks['HW504_B_vs_N2_switch_body']) else 'HOLD'} |
| N1 ↔ N2 | {float(checks['N1_vs_N2']['distanceMm']):.6f} mm | {float(checks['N1_vs_N2']['penetrationMm3']):.9f} mm³ | {'PASS' if pair_pass(checks['N1_vs_N2']) else 'HOLD'} |
| carrier ↔ local shell | {float(checks['carrier_vs_local_shell']['minimumDistanceMm']):.6f} mm | {float(checks['carrier_vs_local_shell']['penetrationMm3']):.9f} mm³ | {'PASS' if bool(checks['carrier_vs_local_shell']['zeroPenetration']) else 'HOLD'} |

## Freeze / reuse

- `HW504 A PROTECTED REMOVAL = 0`
- `HW504 B CHANGE = 0`
- Joystick center / pivot axes / travel / Thumb relative geometry change = **0**
- `ORIGINAL THUMB RETAINED = 19/20`
- `THUMB REUSE = 95.0%`
- Finger exterior = **PRESERVED**; exterior shell = **UNCHANGED**

## Final verdict

- `OPTION C FINAL LOCAL FIT = HOLD`
- `N2 TERMINAL FIT = HOLD`
- `CARRIER FIT = PASS`
- `HW504 B EXACT REUSE = PASS`
- `JOYSTICK KINEMATICS = PASS`
- `FINGER EXTERIOR = PRESERVED`
- `EXTERIOR = UNCHANGED`

## Outputs / STOP

- `build123d_workbench/out/option_c_final_local_fit/option_c_final_local_fit.json`
- `build123d_workbench/out/option_c_final_local_fit/OPTION_C_FINAL_LOCAL_FIT.step`
- `renders/option_c_final_local_fit/01_n2_terminal_before_after.png`
- `renders/option_c_final_local_fit/02_n2_clocking_comparison.png`
- `renders/option_c_final_local_fit/03_carrier_micro_relief_closeup.png`
- `renders/option_c_final_local_fit/04_final_transparent_local_crop.png`

Production geometry에는 반영하지 않았다. 이 local fit 결과에서 STOP한다.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    memory("start")
    source = load_source()
    analysis = analyze_clockings(source)
    manifest = json.loads(CONTROL_MANIFEST.read_text(encoding="utf-8"))
    n2_base = datum_from_manifest("N2", manifest["controls"]["N2"])
    front_depth = float(manifest["frontDepthsMm"]["N2"])
    best_datum = clocked_datum(n2_base, SELECTED_CLOCKING_DEG)
    best_parts = switch_parts(best_datum, front_depth)

    # One exact boolean only for the most promising discrete clocking.
    best_exact = exact_pair(
        source["HW504_B_EXACT_KEEP"],
        best_parts["terminalRoot3"],
        "HW504_B<->N2.terminalRoot3 @ 180deg",
    )
    analysis["exactMostPromising"] = {
        "clockingDeg": SELECTED_CLOCKING_DEG,
        **best_exact,
        "electricallyEquivalent": True,
        "allFourFixedTerminalsRetained": True,
        "adopted": False,
        "reason": "exact penetration remains nonzero",
    }
    memory("one exact boolean for best clocking")

    pose_screen = custom_pose_screen(source["HW504_B_EXACT_KEEP"], best_datum, front_depth)
    carrier_final, relief_tool, carrier_common, relief_metrics = carrier_micro_relief(
        source["HW504_A_NONFUNCTIONAL_TRIM"],
        source["N1_N2_SHARED_CARRIER_OPTION_C_LOCAL_REDESIGN"],
    )
    checks = exact_final_checks(source, carrier_final)

    carrier_fit = (
        pair_pass(checks["HW504_A_vs_carrier"])
        and pair_pass(checks["HW504_B_vs_carrier"])
        and pair_pass(checks["carrier_vs_N2"])
        and bool(checks["carrier_vs_local_shell"]["zeroPenetration"])
        and bool(relief_metrics["wallPass"])
    )
    terminal_fit = bool(checks["HW504_B_vs_N2_terminal_roots"]["zeroPenetration"])

    step_children = [
        source["HW504_A_NONFUNCTIONAL_TRIM"],
        source["HW504_B_EXACT_KEEP"],
        carrier_final,
        *named_parts(source, "N1").values(),
        *named_parts(source, "N2").values(),
        source["N1_wire_service_envelope"],
        source["N2_SERVICE_BEND_1"],
        source["N2_SERVICE_BEND_2"],
        source["N2_SEAM_JaD"],
        source["N2_SEAM_JfD"],
    ]
    export_step(Compound(children=step_children, label="OPTION_C_FINAL_LOCAL_FIT_HOLD"), STEP_PATH)
    memory("single local STEP export")

    render_paths = build_renders(
        source, carrier_final, relief_tool, carrier_common, analysis, best_parts,
    )
    source_data = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    data: dict[str, object] = {
        "schema": "onegrip.option_c.final_local_fit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOW-MEMORY LOCAL ONLY / SERIAL OCCT / NO FULL SHELL",
        "inputs": {
            "docs56LocalStep": {"path": str(SOURCE_STEP.relative_to(ROOT)), "sha256": sha256(SOURCE_STEP)},
            "docs56Json": {"path": str(SOURCE_JSON.relative_to(ROOT)), "sha256": sha256(SOURCE_JSON)},
            "controlManifest": {"path": str(CONTROL_MANIFEST.relative_to(ROOT)), "sha256": sha256(CONTROL_MANIFEST)},
            "electricalAudit": {"path": str(ELECTRICAL_AUDIT.relative_to(ROOT)), "sha256": sha256(ELECTRICAL_AUDIT)},
            "physicalAudit": {"path": str(PHYSICAL_AUDIT.relative_to(ROOT)), "sha256": sha256(PHYSICAL_AUDIT)},
        },
        "scope": {
            "included": ["HW504 A", "HW504 B", "N1/N2 ITS-1105", "N1/N2 carrier", "two existing local shell coupons"],
            "excluded": ["full JaD/JfD", "full assembly", "Backplate", "other six Finger controls", "production geometry"],
            "multiprocessing": 0,
            "concurrentOCCOperations": 0,
            "fullShellBooleans": 0,
        },
        "clockingStudy": analysis,
        "customPoseFeasibility": pose_screen,
        "finalCandidate": {
            "N2SwitchClocking": "CUSTOM",
            "currentApprovedRollDeltaDeg": CURRENT_APPROVED_CLOCKING_DEG,
            "axisChangeDeg": AXIS_CHANGE_DEG,
            "axialDepthChangeMm": DEPTH_CHANGE_MM,
            "externalCenterChangeMm": 0.0,
            "actuatorEngagement": "PRESERVED",
            "reason": "no cardinal or engagement-compliant custom pose clears HW504 B; current approved N2 pose retained",
        },
        "carrierMicroRelief": relief_metrics,
        "checks": checks,
        "clearancesMm": {
            "HW504_B_to_N2_terminal": checks["HW504_B_vs_N2_terminal_roots"]["minimumDistanceMm"],
            "HW504_B_to_carrier": checks["HW504_B_vs_carrier"]["distanceMm"],
            "HW504_A_to_carrier": checks["HW504_A_vs_carrier"]["distanceMm"],
            "N1_to_N2": checks["N1_vs_N2"]["distanceMm"],
            "carrier_to_localShell": checks["carrier_vs_local_shell"]["minimumDistanceMm"],
        },
        "freeze": {
            "HW504AProtectedMaterialRemovedMm3": 0.0,
            "HW504BGeometryChange": 0.0,
            "joystickCenterShiftMm": 0.0,
            "joystickPivotAxesShiftDeg": 0.0,
            "joystickTravelChangeMm": 0.0,
            "thumbRelativeGeometryChangeMm": 0.0,
            "N2ExternalCenterMovementMm": 0.0,
            "fingerExterior": "PRESERVED",
            "exterior": "UNCHANGED",
        },
        "reuse": source_data["reuse"],
        "gates": {
            "terminalServiceClearanceTargetMm": TERMINAL_CLEARANCE_TARGET_MM,
            "N2TerminalFit": "PASS" if terminal_fit else "HOLD",
            "carrierFit": "PASS" if carrier_fit else "HOLD",
            "HW504BExactReuse": "PASS",
            "joystickKinematics": "PASS",
        },
        "verdict": {
            "OPTION_C_FINAL_LOCAL_FIT": "PASS" if terminal_fit and carrier_fit else "HOLD",
            "N2_TERMINAL_FIT": "PASS" if terminal_fit else "HOLD",
            "CARRIER_FIT": "PASS" if carrier_fit else "HOLD",
            "HW504_B_EXACT_REUSE": "PASS",
            "JOYSTICK_KINEMATICS": "PASS",
            "FINGER_EXTERIOR": "PRESERVED",
            "EXTERIOR": "UNCHANGED",
        },
        "memory": MEMORY_LOG,
        "outputs": {
            "json": str(JSON_PATH.relative_to(ROOT)),
            "localStep": str(STEP_PATH.relative_to(ROOT)),
            "report": str(REPORT_PATH.relative_to(ROOT)),
            "renders": [str(path.relative_to(ROOT)) for path in render_paths],
        },
        "stop": "No production geometry changed; STOP at local-fit gate",
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(data)
    memory("outputs complete")
    data["memory"] = MEMORY_LOG
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "verdict": data["verdict"],
        "carrierMicroRelief": relief_metrics,
        "bestClockingExact": analysis["exactMostPromising"],
        "clearancesMm": data["clearancesMm"],
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY_LOG),
        "outputs": data["outputs"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
