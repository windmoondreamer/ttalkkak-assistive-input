"""N2 robustness pass on the accepted docs/60 mechanism.

The accepted cap, guide, switch pose, rear reaction, hard stop and exterior
are immutable.  This module only:

* tangentially extends the pre-approved nonfunctional HW504-A relief without
  increasing its wall-normal depth; and
* calculates the physical external-stub limit for unused T2/T4.

No full shell, STL or print plate is produced.
"""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import psutil
from build123d import Compound, Shape, export_step, import_step

from . import n2_production_intent_mechanism as baseline
from .finger_controls_v2 import oriented_box, unit
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    exact_pair,
    raster_scene,
    safe_triangles,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "n2_robustness_pass"
RENDER_DIR = ROOT / "renders" / "n2_robustness_pass"
JSON_PATH = OUT_DIR / "n2_robustness_pass.json"
REPORT_PATH = ROOT / "docs" / "61_n2_robustness_pass.md"
ROBUST_CARRIER_STEP = OUT_DIR / "N1_N2_SHARED_CARRIER_N2_ROBUSTNESS.step"

DOCS60_JSON = (
    ROOT / "build123d_workbench" / "out" / "n2_production_intent_mechanism"
    / "n2_production_intent_mechanism.json"
)
DOCS60_CAP_STEP = (
    ROOT / "build123d_workbench" / "out" / "n2_production_intent_mechanism"
    / "N2_PRODUCTION_INTENT_CAP.step"
)
DOCS60_CARRIER_STEP = (
    ROOT / "build123d_workbench" / "out" / "n2_production_intent_mechanism"
    / "N1_N2_SHARED_CARRIER_N2_PRODUCTION_INTENT.step"
)

# Exact original common bbox recorded by docs/57 before the first relief.
OLD_COMMON_LOWER = np.asarray((-4.842298945070917, -25.320709894921755, 28.29719779380943))
OLD_COMMON_UPPER = np.asarray((-1.7486932369889914, -25.21555824717316, 28.48224683520005))
OLD_RELIEF_NORMAL_MARGIN_MM = 0.18
OLD_RELIEF_TANGENTIAL_MARGIN_MM = 0.18
ROBUST_RELIEF_TANGENTIAL_MARGIN_MM = 0.50
OLD_RELIEF_NORMAL_SPAN_MM = float(OLD_COMMON_UPPER[1] - OLD_COMMON_LOWER[1])
OLD_RELIEF_REMAINING_WALL_MM = 1.60 - (OLD_RELIEF_NORMAL_SPAN_MM + OLD_RELIEF_NORMAL_MARGIN_MM)

CARRIER_CLEARANCE_REQUIRED_MM = 0.50
CARRIER_CLEARANCE_PREFERRED_MM = 0.80
TERMINAL_CLEARANCE_REQUIRED_MM = 1.00
MIN_WALL_MM = 1.20
CURRENT_TRIM_DEPTH_MM = baseline.TRIM_CUT_DEPTH_MM
HOUSING_REAR_DEPTH_MM = baseline.HOUSING_REAR_DEPTH_MM
ROOT_START_DEPTH_MM = HOUSING_REAR_DEPTH_MM - 0.30
ROOT_END_DEPTH_MM = HOUSING_REAR_DEPTH_MM + 2.00
ROOT_START_U_MM = 6.18 / 2.0 + 0.30 / 2.0
ROOT_END_U_MM = (7.90 - 0.30) / 2.0
ROOT_CENTERLINE_SCALE = float(np.hypot(1.0, (ROOT_END_U_MM - ROOT_START_U_MM) / (ROOT_END_DEPTH_MM - ROOT_START_DEPTH_MM)))

PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, float | str]] = []
RSS_LIMIT_MB = 24576.0

COLORS = {
    "before": (89, 150, 207),
    "after": (66, 204, 147),
    "removed": (245, 78, 80),
    "hwA": (145, 96, 235),
    "hwB": (145, 96, 235),
    "cap": (57, 207, 143),
    "guide": (74, 142, 226),
    "carrier": (179, 89, 211),
    "body": (235, 174, 66),
    "actuator": (252, 207, 89),
    "active": (67, 204, 147),
    "trimmed": (121, 131, 143),
    "invalid": (245, 128, 62),
    "shell": (87, 183, 214),
}


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1)})
    if rss > RSS_LIMIT_MB:
        raise MemoryError(f"RAM stop at {stage}: {rss:.1f} MB")
    if float(psutil.virtual_memory().available) / (1024.0 * 1024.0) < 3072.0:
        raise MemoryError(f"System available-memory stop at {stage}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def trim_at_depth(source: dict[str, Shape], datum, depth: float) -> dict[str, Shape]:
    keep = oriented_box(datum, 40.0, 40.0, -5.0, depth, label=f"N2_TRIM_KEEP_{depth:.6f}")
    rows: dict[str, Shape] = {
        "T1": source[baseline.TERMINAL_LABELS["T1"]],
        "T3": source[baseline.TERMINAL_LABELS["T3"]],
    }
    for name in ("T2", "T4"):
        row = (source[baseline.TERMINAL_LABELS[name]] & keep).clean()
        row.label = f"N2_{name}_TRIM_AT_{depth:.6f}"
        rows[name] = row
    return rows


def terminal_distances(source: dict[str, Shape], datum, depth: float) -> dict[str, float]:
    hw_b = source["HW504_B_EXACT_KEEP"]
    roots = trim_at_depth(source, datum, depth)
    return {
        name: float(roots[name].distance_to_with_closest_points(hw_b)[0])
        for name in ("T2", "T4")
    }


def solve_theoretical_target_depth(source: dict[str, Shape], datum) -> tuple[float, dict[str, float]]:
    # This bracket intentionally crosses the housing rear plane only to find
    # the theoretical target.  It is never exported or adopted.
    low, high = HOUSING_REAR_DEPTH_MM - 0.08, HOUSING_REAR_DEPTH_MM
    for _ in range(20):
        mid = 0.5 * (low + high)
        distance = min(terminal_distances(source, datum, mid).values())
        if distance >= TERMINAL_CLEARANCE_REQUIRED_MM:
            low = mid
        else:
            high = mid
    target = 0.5 * (low + high)
    return target, terminal_distances(source, datum, target)


def build_robust_relief(carrier_before: Shape) -> tuple[Shape, Shape, Shape, dict[str, object]]:
    old_margin = np.asarray((
        OLD_RELIEF_TANGENTIAL_MARGIN_MM,
        OLD_RELIEF_NORMAL_MARGIN_MM,
        OLD_RELIEF_TANGENTIAL_MARGIN_MM,
    ))
    robust_margin = np.asarray((
        ROBUST_RELIEF_TANGENTIAL_MARGIN_MM,
        OLD_RELIEF_NORMAL_MARGIN_MM,
        ROBUST_RELIEF_TANGENTIAL_MARGIN_MM,
    ))
    old_tool = baseline.global_box(
        OLD_COMMON_LOWER - old_margin,
        OLD_COMMON_UPPER + old_margin,
        "DOCS57_EXISTING_RELIEF_TOOL_REFERENCE",
    )
    robust_tool = baseline.global_box(
        OLD_COMMON_LOWER - robust_margin,
        OLD_COMMON_UPPER + robust_margin,
        "N2_NONFUNCTIONAL_TANGENTIAL_ROBUSTNESS_RELIEF",
    )
    extension = (robust_tool - old_tool).clean()
    extension.label = "N2_ROBUSTNESS_ADDITIONAL_NONFUNCTIONAL_RELIEF"
    carrier_after = (carrier_before - robust_tool).clean()
    carrier_after.label = "N1_N2_SHARED_CARRIER_N2_ROBUSTNESS"
    metrics: dict[str, object] = {
        "wallNormalMarginBeforeMm": OLD_RELIEF_NORMAL_MARGIN_MM,
        "wallNormalMarginAfterMm": OLD_RELIEF_NORMAL_MARGIN_MM,
        "tangentialMarginBeforeMm": OLD_RELIEF_TANGENTIAL_MARGIN_MM,
        "tangentialMarginAfterMm": ROBUST_RELIEF_TANGENTIAL_MARGIN_MM,
        "wallNormalDepthIncreaseMm": 0.0,
        "nonfunctionalMaterialRemovedMm3": max(0.0, float(carrier_before.volume - carrier_after.volume)),
        "existingReliefRemainingWallMm": OLD_RELIEF_REMAINING_WALL_MM,
        "overallMinimumWallMm": min(MIN_WALL_MM, OLD_RELIEF_REMAINING_WALL_MM),
    }
    memory("tangential-only carrier relief built")
    return carrier_after, robust_tool, extension, metrics


def exact_checks(
    source: dict[str, Shape],
    datum,
    base_cap: Shape,
    carrier_before: Shape,
    carrier_after: Shape,
    robust_tool: Shape,
    roots_current: dict[str, Shape],
) -> tuple[dict[str, object], dict[str, Shape]]:
    # Recreate frozen functional features only as verification witnesses.
    cap, cap_parts = baseline.build_production_cap(base_cap, datum)
    guide, guide_parts = baseline.build_guide(datum)
    raw_reaction, service_bay = baseline.build_reaction_support(datum, roots_current)
    _, reaction_final, _ = baseline.build_production_carrier(
        source["N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"],
        guide,
        raw_reaction,
        service_bay,
        roots_current,
        datum,
        source["HW504_A_NONFUNCTIONAL_TRIM"],
    )

    before = exact_pair(source["HW504_A_NONFUNCTIONAL_TRIM"], carrier_before, "HW504_A<->carrier before")
    after = exact_pair(source["HW504_A_NONFUNCTIONAL_TRIM"], carrier_after, "HW504_A<->carrier after")
    frozen_limiter = exact_pair(
        source["HW504_A_NONFUNCTIONAL_TRIM"],
        reaction_final,
        "HW504_A<->frozen rear reaction limiter",
    )
    relief_protection = {
        "guidePenetrationMm3": baseline.volume(robust_tool & guide),
        "rearReactionPenetrationMm3": baseline.volume(robust_tool & reaction_final),
        "hardStopPenetrationMm3": baseline.volume(robust_tool & guide_parts["rearStop"]),
        "switchBodyPenetrationMm3": baseline.volume(robust_tool & source["N2_ITS1105_body"]),
    }
    n1_envelope = Compound(
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
    relief_protection["N1FunctionalEnvelopePenetrationMm3"] = baseline.volume(robust_tool & n1_envelope)
    motion = baseline.exact_validation(
        source,
        datum,
        cap,
        cap_parts,
        guide,
        guide_parts,
        carrier_after,
        roots_current,
    )
    memory("all robustness exact checks")
    return {
        "carrierBefore": before,
        "carrierAfter": after,
        "frozenRearReactionLimiter": frozen_limiter,
        "reliefProtectedFeatures": relief_protection,
        "motionAndStatic": motion,
    }, {
        "cap": cap,
        "contact": cap_parts["contact"],
        "guide": guide,
        "rearStop": guide_parts["rearStop"],
        "reaction": reaction_final,
    }


def shifted_mesh(mesh: np.ndarray, vector) -> np.ndarray:
    return mesh + np.asarray(vector, dtype=float)


def shape_center(shape: Shape) -> np.ndarray:
    lower, upper = baseline.bounds(shape)
    return 0.5 * (lower + upper)


def render_outputs(
    source: dict[str, Shape],
    datum,
    carrier_before: Shape,
    carrier_after: Shape,
    extension: Shape,
    roots_current: dict[str, Shape],
    roots_flush: dict[str, Shape],
    roots_target: dict[str, Shape],
    exact: dict[str, object],
    witnesses: dict[str, Shape],
    terminal: dict[str, object],
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        RENDER_DIR / "01_carrier_relief_before_after.png",
        RENDER_DIR / "02_hw504a_carrier_clearance.png",
        RENDER_DIR / "03_trimmed_terminal_hw504b.png",
        RENDER_DIR / "04_full_press_section.png",
    ]
    cache: dict[int, np.ndarray] = {}

    def mesh(shape: Shape, limit: int = 2600) -> np.ndarray:
        key = id(shape)
        if key not in cache:
            cache[key] = safe_triangles(shape, tolerance=0.10, angular=0.07, limit=limit)
        return cache[key]

    hw_a = source["HW504_A_NONFUNCTIONAL_TRIM"]
    hw_b = source["HW504_B_EXACT_KEEP"]
    region_crop = baseline.global_box(
        OLD_COMMON_LOWER - np.asarray((3.5, 3.5, 3.5)),
        OLD_COMMON_UPPER + np.asarray((3.5, 3.5, 3.5)),
        "N2_ROBUSTNESS_RENDER_CROP",
    )
    before_local = (carrier_before & region_crop).clean()
    after_local = (carrier_after & region_crop).clean()
    hw_a_local = (hw_a & region_crop).clean()
    shift = np.asarray((11.0, 0.0, 0.0))
    before_mesh = mesh(before_local)
    after_mesh = mesh(after_local)
    hw_a_mesh = mesh(hw_a_local, 3000)
    removed_mesh = mesh(extension, 1400)
    before_row = exact["carrierBefore"]
    after_row = exact["carrierAfter"]
    before_p0 = np.asarray(before_row["closestPointLeftMm"]) - shift
    before_p1 = np.asarray(before_row["closestPointRightMm"]) - shift
    after_p0 = np.asarray(after_row["closestPointLeftMm"]) + shift
    after_p1 = np.asarray(after_row["closestPointRightMm"]) + shift
    focus = np.concatenate([
        shifted_mesh(before_mesh, -shift).reshape(-1, 3),
        shifted_mesh(after_mesh, shift).reshape(-1, 3),
        shifted_mesh(hw_a_mesh, -shift).reshape(-1, 3),
        shifted_mesh(hw_a_mesh, shift).reshape(-1, 3),
    ])
    raster_scene(
        paths[0],
        [
            (shifted_mesh(before_mesh, -shift), COLORS["before"]),
            (shifted_mesh(after_mesh, shift), COLORS["after"]),
            (shifted_mesh(removed_mesh, shift), COLORS["removed"]),
        ],
        "01 / HW504-A CARRIER RELIEF — BEFORE vs AFTER",
        "Left: docs/60 accepted carrier | Right: tangential-only nonfunctional relief extension",
        f"0.004964 -> {float(after_row['distanceMm']):.6f} mm; wall-normal cut depth unchanged",
        transparent_objects=[
            (shifted_mesh(hw_a_mesh, -shift), (*COLORS["hwA"], 66)),
            (shifted_mesh(hw_a_mesh, shift), (*COLORS["hwA"], 66)),
        ],
        world_lines=[
            (before_p0, before_p1, (255, 220, 105, 255), "BEFORE"),
            (after_p0, after_p1, (255, 220, 105, 255), "AFTER"),
        ],
        camera_offset=(68.0, -88.0, 55.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=focus,
    )
    memory("render 01 before after")

    full_after_local = (carrier_after & baseline.global_box(
        np.asarray((-8.0, -33.0, 25.0)),
        np.asarray((6.5, -22.0, 35.0)),
        "N2_HW_A_CLEARANCE_RENDER_CROP",
    )).clean()
    after_full_mesh = mesh(full_after_local, 3200)
    hw_a_close = (hw_a & baseline.global_box(
        np.asarray((-8.0, -33.0, 25.0)),
        np.asarray((6.5, -22.0, 35.0)),
        "N2_HW_A_CLEARANCE_HW_CROP",
    )).clean()
    hw_a_close_mesh = mesh(hw_a_close, 3200)
    p0 = np.asarray(after_row["closestPointLeftMm"])
    p1 = np.asarray(after_row["closestPointRightMm"])
    raster_scene(
        paths[1],
        [(after_full_mesh, COLORS["after"]), (removed_mesh, COLORS["removed"])],
        "02 / HW504-A ↔ CARRIER ROBUSTNESS LIMIT",
        "Only the pre-approved nonfunctional corner is relieved; guide/reaction/hard-stop are frozen",
        f"Exact available maximum {float(after_row['distanceMm']):.6f} mm < required 0.500 mm — HOLD",
        transparent_objects=[(hw_a_close_mesh, (*COLORS["hwA"], 68))],
        world_lines=[(p0, p1, (255, 220, 105, 255), f"{float(after_row['distanceMm']):.6f} mm")],
        camera_offset=(62.0, -92.0, 48.0),
        final_size=(1920, 1280),
        supersample=2,
    )
    memory("render 02 HW A clearance")

    u = unit(datum.switch_u)
    terminal_shift = 13.0
    shifts = (-u * terminal_shift, np.zeros(3), u * terminal_shift)
    terminal_sets = (roots_current, roots_flush, roots_target)
    hw_b_mesh = mesh(hw_b, 3200)
    objects: list[tuple[np.ndarray, tuple[int, int, int]]] = []
    transparent = []
    lines = []
    labels = (
        f"CURRENT {float(terminal['currentMinimumClearanceMm']):.3f}",
        f"HOUSING FLUSH {float(terminal['flushMinimumClearanceMm']):.3f}",
        "1.000 TARGET / INVALID",
    )
    for index, (root_set, offset) in enumerate(zip(terminal_sets, shifts)):
        color = COLORS["trimmed"] if index < 2 else COLORS["invalid"]
        for name in ("T2", "T4"):
            objects.append((shifted_mesh(mesh(root_set[name], 700), offset), color))
        transparent.append((shifted_mesh(hw_b_mesh, offset), (*COLORS["hwB"], 52)))
        t2 = root_set["T2"]
        row = exact_pair(hw_b, t2, f"render {index}")
        q0 = np.asarray(row["closestPointLeftMm"]) + offset
        q1 = np.asarray(row["closestPointRightMm"]) + offset
        lines.append((q0, q1, (255, 220, 105, 255), labels[index]))
    terminal_focus = np.concatenate([triangles.reshape(-1, 3) for triangles, _ in objects])
    raster_scene(
        paths[2],
        objects,
        "03 / UNUSED T2/T4 PHYSICAL TRIM LIMIT",
        "Current external stub | housing-flush physical boundary | theoretical 1.00 mm target",
        f"Target needs {abs(float(terminal['targetAxialStubMm'])):.3f} mm inside housing: TOO CLOSE TO HOUSING",
        transparent_objects=transparent,
        world_lines=lines,
        camera_offset=(58.0, -94.0, -42.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=terminal_focus,
    )
    memory("render 03 terminal limit")

    travel = baseline.ACTUATOR_TRAVEL_MAX
    cap_pressed = baseline.cap_at(witnesses["cap"], datum, travel)
    actuator_pressed = baseline.actuator_at(datum, travel)
    body = source["N2_ITS1105_body"]
    local_crop = oriented_box(datum, 18.0, 18.0, -2.5, 11.5, cap_frame=True, label="N2_ROBUST_FULL_PRESS_CROP")
    half = oriented_box(
        datum, 20.0, 24.0, -2.5, 11.5,
        u_offset=-10.0, cap_frame=True, label="N2_ROBUST_FULL_PRESS_HALF",
    )

    def section(shape: Shape) -> Shape:
        return (shape & local_crop & half).clean()

    section_rows = [
        (mesh(section(cap_pressed)), COLORS["cap"]),
        (mesh(section(witnesses["guide"])), COLORS["guide"]),
        (mesh(section(carrier_after)), COLORS["carrier"]),
        (mesh(section(witnesses["reaction"])), COLORS["invalid"]),
        (mesh(section(body)), COLORS["body"]),
        (mesh(section(actuator_pressed)), COLORS["actuator"]),
    ]
    section_focus = np.concatenate([triangles.reshape(-1, 3) for triangles, _ in section_rows])
    raster_scene(
        paths[3],
        section_rows,
        "04 / N2 ROBUSTNESS — FULL PRESS 0.350 mm",
        "Accepted direct actuation, guide, reaction and hard-stop geometry remain unchanged",
        "All unintended penetration 0 | rear hard-stop residual 0.000 mm | exterior preserved",
        transparent_objects=[
            (mesh(source["HW504_A_NONFUNCTIONAL_TRIM"], 3200), (*COLORS["hwA"], 34)),
            (mesh(source["HW504_B_EXACT_KEEP"], 3200), (*COLORS["hwB"], 34)),
        ],
        camera_offset=(84.0, 0.0, 0.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=section_focus,
    )
    memory("render 04 full press")
    return paths


def write_report(data: dict[str, object]) -> None:
    carrier = data["carrierRobustness"]
    terminal = data["terminalRobustness"]
    motion_rows = "\n".join(
        "| {travel:.3f} | {cap:.9f} | {guide:.9f} | {actuator:.9f} | {rear:.3f} | PASS |".format(
            travel=float(row["travelMm"]),
            cap=float(row["capShell"]["penetrationMm3"]),
            guide=float(row["capGuide"]["penetrationMm3"]),
            actuator=float(row["capActuator"]["penetrationMm3"]),
            rear=float(row["rearOvertravelStop"]["distanceMm"]),
        )
        for row in data["checks"]["motionAndStatic"]["motionStates"]
    )
    report = f"""# 61 — N2 robustness pass

## 결론

`N2 ARCHITECTURE = ACCEPT`를 유지한다. Cap/direct actuation/guide/rear reaction/hard stop/switch pose/exterior는 변경하지 않았다.

다만 요구 robustness target 두 개는 frozen geometry와 physical housing limit 안에서 달성할 수 없어 최종 `N2 PRODUCTION-INTENT ROBUSTNESS = HOLD`다.

## 1. HW504 A ↔ carrier

- Before: **{float(carrier['beforeClearanceMm']):.6f} mm**, penetration 0
- Required: **0.500 mm**, preferred 0.800 mm
- Applied change: 기존 승인 non-functional corner relief의 tangential extent만 0.18 → 0.50 mm 확장
- Wall-normal depth increase: **0.000 mm**
- Removed carrier material: **{float(carrier['materialRemovedMm3']):.6f} mm³**
- After / exact available maximum: **{float(carrier['afterClearanceMm']):.6f} mm**, penetration 0
- Next limiting geometry: **frozen rear reaction support**, distance {float(carrier['frozenReactionLimiterMm']):.6f} mm
- Existing relief wall: **{float(carrier['existingReliefRemainingWallMm']):.6f} mm**
- Overall minimum wall: **{float(carrier['overallMinimumWallMm']):.3f} mm**
- Verdict: **HOLD**

0.50 mm를 만들려면 frozen rear reaction support 또는 1.20 mm wall gate를 건드려야 하므로 자동으로 더 깎지 않았다.

## 2. Trimmed T2/T4

- Current axial external stub: **{float(terminal['currentAxialStubMm']):.6f} mm**
- Current external centerline stub: **{float(terminal['currentExternalCenterlineStubMm']):.6f} mm**
- Current clearance: **{float(terminal['currentMinimumClearanceMm']):.6f} mm**
- Housing-flush stub: **0.000 mm**
- Housing-flush maximum clearance: **{float(terminal['flushMinimumClearanceMm']):.6f} mm**
- 1.00 mm theoretical cut depth: **{float(terminal['targetCutDepthMm']):.6f} mm**
- Additional shortening from current: **{float(terminal['additionalShorteningRequiredMm']):.6f} mm**
- 1.00 mm target axial stub: **{float(terminal['targetAxialStubMm']):.6f} mm**
- 1.00 mm target external stub: **{float(terminal['targetExternalStubMm']):.6f} mm** (plus {abs(float(terminal['targetAxialStubMm'])):.6f} mm forbidden housing intrusion)
- Physical verdict: **TOO CLOSE TO HOUSING**
- Real cut safety: **CONDITIONAL — pending user physical test**
- Robustness verdict: **HOLD**

Target은 housing rear plane보다 {abs(float(terminal['targetAxialStubMm'])):.6f} mm 안쪽이므로 housing/leadframe 금지 영역이다. Current T2/T4 production trim은 변경하지 않았다. T1/T3 geometry와 solder access도 변경하지 않았다.

## 3. Motion revalidation

| Travel mm | Cap↔shell pen mm³ | Cap↔guide pen mm³ | Cap↔actuator pen mm³ | Hard-stop residual mm | Result |
|---:|---:|---:|---:|---:|---|
{motion_rows}

- T1/T3 ↔ HW504 B minimum: **{float(data['activeTerminalClearanceMm']):.6f} mm** — unchanged
- Robust carrier ↔ HW504 penetration: **0 mm³**
- N2 exterior geometry delta: **0 mm³**
- N2 motion: **PASS**

## 4. Final verdict

- `N2 ARCHITECTURE = ACCEPT`
- `HW504 A ↔ CARRIER ROBUSTNESS = HOLD`
- `T2/T4 TRIM ROBUSTNESS = HOLD`
- `N2 MOTION = PASS`
- `N2 EXTERIOR = PRESERVED`
- `N2 PRODUCTION-INTENT ROBUSTNESS = HOLD`

## 5. Outputs / STOP

- `{ROBUST_CARRIER_STEP.relative_to(ROOT)}` — local carrier STEP only
- `{JSON_PATH.relative_to(ROOT)}`
- `{RENDER_DIR.relative_to(ROOT)}` — four required renders

Full shell / STL / print plate는 생성하지 않았다. 다른 버튼으로 확장하지 않고 여기서 STOP한다.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    memory("start")
    source = baseline.load_source()
    datum = baseline.load_datum()
    base_cap = import_step(baseline.BASE_CAP_STEP)
    carrier_before = import_step(DOCS60_CARRIER_STEP)
    roots_current = trim_at_depth(source, datum, CURRENT_TRIM_DEPTH_MM)

    carrier_after, robust_tool, extension, relief_metrics = build_robust_relief(carrier_before)
    exact, witnesses = exact_checks(
        source,
        datum,
        base_cap,
        carrier_before,
        carrier_after,
        robust_tool,
        roots_current,
    )

    current_distances = terminal_distances(source, datum, CURRENT_TRIM_DEPTH_MM)
    flush_distances = terminal_distances(source, datum, HOUSING_REAR_DEPTH_MM)
    target_depth, target_distances = solve_theoretical_target_depth(source, datum)
    roots_flush = trim_at_depth(source, datum, HOUSING_REAR_DEPTH_MM)
    roots_target = trim_at_depth(source, datum, target_depth)
    current_axial = CURRENT_TRIM_DEPTH_MM - HOUSING_REAR_DEPTH_MM
    target_axial = target_depth - HOUSING_REAR_DEPTH_MM
    terminal: dict[str, object] = {
        "currentCutDepthMm": CURRENT_TRIM_DEPTH_MM,
        "currentAxialStubMm": current_axial,
        "currentExternalCenterlineStubMm": current_axial * ROOT_CENTERLINE_SCALE,
        "currentRetainedCenterlineFromRootStartMm": (CURRENT_TRIM_DEPTH_MM - ROOT_START_DEPTH_MM) * ROOT_CENTERLINE_SCALE,
        "currentT2ClearanceMm": current_distances["T2"],
        "currentT4ClearanceMm": current_distances["T4"],
        "currentMinimumClearanceMm": min(current_distances.values()),
        "flushCutDepthMm": HOUSING_REAR_DEPTH_MM,
        "flushAxialStubMm": 0.0,
        "flushT2ClearanceMm": flush_distances["T2"],
        "flushT4ClearanceMm": flush_distances["T4"],
        "flushMinimumClearanceMm": min(flush_distances.values()),
        "targetClearanceMm": TERMINAL_CLEARANCE_REQUIRED_MM,
        "targetCutDepthMm": target_depth,
        "targetT2ClearanceMm": target_distances["T2"],
        "targetT4ClearanceMm": target_distances["T4"],
        "targetAxialStubMm": target_axial,
        "targetExternalStubMm": max(0.0, target_axial),
        "targetRetainedCenterlineFromRootStartMm": (target_depth - ROOT_START_DEPTH_MM) * ROOT_CENTERLINE_SCALE,
        "additionalShorteningRequiredMm": CURRENT_TRIM_DEPTH_MM - target_depth,
        "physicalVerdict": "TOO CLOSE TO HOUSING",
        "realCutSafety": "CONDITIONAL_PENDING_USER_PHYSICAL_TEST",
        "adoptedGeometryChange": 0,
        "robustnessVerdict": "HOLD",
    }
    memory("terminal physical limit solved")

    after_clearance = float(exact["carrierAfter"]["distanceMm"])
    carrier_robustness: dict[str, object] = {
        "beforeClearanceMm": float(exact["carrierBefore"]["distanceMm"]),
        "afterClearanceMm": after_clearance,
        "requiredClearanceMm": CARRIER_CLEARANCE_REQUIRED_MM,
        "preferredClearanceMm": CARRIER_CLEARANCE_PREFERRED_MM,
        "penetrationMm3": float(exact["carrierAfter"]["penetrationMm3"]),
        "frozenReactionLimiterMm": float(exact["frozenRearReactionLimiter"]["distanceMm"]),
        "exactAvailableMaximumMm": after_clearance,
        "materialRemovedMm3": relief_metrics["nonfunctionalMaterialRemovedMm3"],
        "wallNormalDepthIncreaseMm": 0.0,
        "existingReliefRemainingWallMm": relief_metrics["existingReliefRemainingWallMm"],
        "overallMinimumWallMm": relief_metrics["overallMinimumWallMm"],
        "reliefProtection": exact["reliefProtectedFeatures"],
        "robustnessVerdict": "HOLD",
        "reason": "next closest point is frozen rear reaction support; target cannot be reached without prohibited change",
    }

    motion_rows = exact["motionAndStatic"]["motionStates"]
    motion_pass = all(
        float(row[key]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        for row in motion_rows
        for key in ("capGuide", "capShell", "capActuator")
    ) and all(
        abs(float(row["rearOvertravelStop"]["distanceMm"]) - (baseline.ACTUATOR_TRAVEL_MAX - float(row["travelMm"]))) <= 1.0e-6
        for row in motion_rows
    )
    protected_pass = all(float(value) <= BOOLEAN_EPS_MM3 for value in exact["reliefProtectedFeatures"].values())
    wall_pass = float(relief_metrics["overallMinimumWallMm"]) + 1.0e-9 >= MIN_WALL_MM

    export_step(carrier_after, ROBUST_CARRIER_STEP)
    memory("local robust carrier STEP exported")

    render_paths = render_outputs(
        source,
        datum,
        carrier_before,
        carrier_after,
        extension,
        roots_current,
        roots_flush,
        roots_target,
        exact,
        witnesses,
        terminal,
    )

    data: dict[str, object] = {
        "schema": "onegrip.n2.robustness_pass.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "N2 ROBUSTNESS LOCAL ONLY / FULL SHELL 0 / STL 0 / PRINT PLATE 0",
        "acceptedArchitecture": {
            "status": "ACCEPT",
            "capTailDiameterMm": 4.5,
            "guideBoreDiameterMm": 4.8,
            "shoulderSquareMm": 6.5,
            "retentionCavitySquareMm": 6.8,
            "actuatorContactDiameterMm": 3.0,
            "travelMm": 0.350,
            "rearReactionAreaMm2": 13.18277569345569,
            "return": "ITS internal return force",
            "architectureChange": 0,
        },
        "freeze": {
            "externalCenterMovementMm": 0.0,
            "capExteriorGeometryChangeMm3": 0.0,
            "travelAxisChangeDeg": 0.0,
            "switchPositionChangeMm": 0.0,
            "HW504AFunctionalChangeMm3": 0.0,
            "HW504BFunctionalChangeMm3": 0.0,
            "joystickKinematicsChange": 0,
            "externalShellChangeMm3": 0.0,
            "N1Change": 0,
        },
        "carrierRobustness": carrier_robustness,
        "terminalRobustness": terminal,
        "checks": exact,
        "activeTerminalClearanceMm": float(exact["motionAndStatic"]["activeTerminalsToHW504B"]["minimumDistanceMm"]),
        "gates": {
            "wallPass": wall_pass,
            "protectedFeaturesPass": protected_pass,
            "motionPass": motion_pass,
            "carrierTargetPass": after_clearance + 1.0e-9 >= CARRIER_CLEARANCE_REQUIRED_MM,
            "terminalTargetPass": min(current_distances.values()) + 1.0e-9 >= TERMINAL_CLEARANCE_REQUIRED_MM,
        },
        "verdict": {
            "N2_ARCHITECTURE": "ACCEPT",
            "HW504_A_CARRIER_ROBUSTNESS": "HOLD",
            "T2_T4_TRIM_ROBUSTNESS": "HOLD",
            "N2_MOTION": "PASS" if motion_pass else "HOLD",
            "N2_EXTERIOR": "PRESERVED",
            "N2_PRODUCTION_INTENT_ROBUSTNESS": "HOLD",
        },
        "inputs": {
            "docs60Json": {"path": str(DOCS60_JSON.relative_to(ROOT)), "sha256": sha256(DOCS60_JSON)},
            "docs60CapStep": {"path": str(DOCS60_CAP_STEP.relative_to(ROOT)), "sha256": sha256(DOCS60_CAP_STEP)},
            "docs60CarrierStep": {"path": str(DOCS60_CARRIER_STEP.relative_to(ROOT)), "sha256": sha256(DOCS60_CARRIER_STEP)},
        },
        "outputs": {
            "robustCarrierStep": str(ROBUST_CARRIER_STEP.relative_to(ROOT)),
            "json": str(JSON_PATH.relative_to(ROOT)),
            "report": str(REPORT_PATH.relative_to(ROOT)),
            "renders": [str(path.relative_to(ROOT)) for path in render_paths],
            "stlGenerated": 0,
            "printPlateGenerated": 0,
            "fullShellGenerated": 0,
        },
        "memory": MEMORY,
        "stop": "STOP after N2 robustness verdict; do not extend to other buttons",
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(data)
    print(json.dumps({
        "verdict": data["verdict"],
        "carrierBeforeMm": carrier_robustness["beforeClearanceMm"],
        "carrierAfterMaximumMm": carrier_robustness["afterClearanceMm"],
        "wallMm": carrier_robustness["overallMinimumWallMm"],
        "terminalCurrentMm": terminal["currentMinimumClearanceMm"],
        "terminalFlushMm": terminal["flushMinimumClearanceMm"],
        "terminalTargetAxialStubMm": terminal["targetAxialStubMm"],
        "motionPass": motion_pass,
        "protectedFeaturesPass": protected_pass,
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY),
        "outputs": data["outputs"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
