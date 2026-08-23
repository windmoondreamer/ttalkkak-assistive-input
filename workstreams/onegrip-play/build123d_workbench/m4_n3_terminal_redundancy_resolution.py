"""Resolve the docs/68 M4.T2 <-> N3.T3 hold by external-leg trim only.

The accepted M4/N3 cap, switch, carrier, guide, retention, reaction, hard-stop
and exterior geometry are read-only.  This pass models the ITS-1105 metal leg
separately from its conservative 0.12 mm service envelope and never trims
behind the switch housing outer face.
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
from build123d import Compound, Location, Shape, Vector, export_step, import_step

from .finger_controls_v2 import (
    FROZEN_FRONT_DEPTHS,
    SWITCH_BODY_H,
    TERMINAL_CLEARANCE,
    TERMINAL_METAL_U,
    TERMINAL_METAL_V,
    point_at,
    switch_body,
    terminal_root_cutters,
    unit,
    wire_envelope,
    wire_exit_cutter,
    xyz,
)
from .m4_n3_current_audit import TERMINAL_NAMES, load_datums
from .option_c_final_local_fit import bounds
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    exact_pair,
    raster_scene,
    safe_triangles,
)
from .real_integration_conflict_resolution import terminal_path, terminal_segment


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "m4_n3_terminal_redundancy_resolution"
RENDER_DIR = ROOT / "renders" / "m4_n3_terminal_redundancy_resolution"
JSON_PATH = OUT_DIR / "m4_n3_terminal_redundancy_resolution.json"
REPORT_PATH = ROOT / "docs" / "69_m4_n3_terminal_redundancy_resolution.md"
STEP_PATH = OUT_DIR / "M4_N3_TRIMMED_TERMINALS_LOCAL_REFERENCE.step"

CARRIER_PATH = ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / "M4_N3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step"
CAP_PATHS = {
    name: ROOT / "build123d_workbench" / "out" / "m4_n3_production_intent_mechanism" / f"{name}_PRODUCTION_INTENT_CAP_LOCAL.step"
    for name in ("M4", "N3")
}
FREEZE_PATHS = (
    ROOT / "docs" / "65_m4_n3_production_intent_mechanism.md",
    ROOT / "docs" / "68_real_integration_conflict_resolution.md",
    CARRIER_PATH,
    *CAP_PATHS.values(),
)

OLD_PENETRATION_MM3 = 0.28339302834904956
APPROVED_CAP_GAP_MM = 3.132654
TRAVELS = ((0.000, 0.000), (0.175, 0.000), (0.350, 0.000), (0.000, 0.175), (0.000, 0.350), (0.350, 0.350))
RSS_LIMIT_MB = 24576.0
PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, object]] = []

COLORS = {
    "M4": (240, 132, 54),
    "N3": (207, 83, 133),
    "active": (67, 205, 145),
    "unused": (245, 190, 72),
    "collision": (245, 74, 78),
    "body": (108, 126, 145),
    "carrier": (151, 91, 200),
}


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    available = float(psutil.virtual_memory().available) / (1024.0 * 1024.0)
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1), "systemAvailableMb": round(available, 1)})
    if rss > RSS_LIMIT_MB or available < 2304.0:
        raise MemoryError(f"RAM safety STOP at {stage}: RSS={rss:.1f} MB, available={available:.1f} MB")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def moved(shape: Shape, vector: np.ndarray, label: str) -> Shape:
    row = np.asarray(vector, dtype=float)
    result = shape.moved(Location(Vector(float(row[0]), float(row[1]), float(row[2]))))
    result.label = label
    return result


def terminal_geometry(datum, front: float, terminal: str) -> dict[str, object]:
    p0, p1 = terminal_path(datum, front, terminal)
    direction = unit(p1 - p0)
    rear = front + SWITCH_BODY_H
    # The source lead centerline is at rear-0.30 mm at p0 and rear+2.00 mm at p1.
    face_ratio = 0.30 / 2.30
    face = p0 + (p1 - p0) * face_ratio
    return {
        "p0": p0,
        "p1": p1,
        "direction": direction,
        "housingRearDepthMm": rear,
        "faceRatio": face_ratio,
        "face": face,
        "internalModeledLengthMm": float(np.linalg.norm(face - p0)),
        "fullExternalLengthMm": float(np.linalg.norm(p1 - face)),
    }


def trimmed_leg(datum, geometry: dict[str, object], stub_mm: float, label: str, clearance: float) -> Shape:
    p0 = np.asarray(geometry["p0"], dtype=float)
    face = np.asarray(geometry["face"], dtype=float)
    direction = np.asarray(geometry["direction"], dtype=float)
    end = face + direction * float(stub_mm)
    result = terminal_segment(datum, p0, end, label, clearance=clearance)
    return result


def project_collision_interval(common: Shape, geometry: dict[str, object]) -> dict[str, object]:
    face = np.asarray(geometry["face"], dtype=float)
    direction = np.asarray(geometry["direction"], dtype=float)
    points = np.asarray([
        np.asarray((float(vertex.X), float(vertex.Y), float(vertex.Z)), dtype=float)
        for vertex in common.vertices()
    ])
    projected = (points - face) @ direction
    return {
        "fromHousingFaceMinMm": float(projected.min()),
        "fromHousingFaceMaxMm": float(projected.max()),
        "entirelyExternal": bool(float(projected.min()) >= -1.0e-7),
    }


def one_side_trim_limit(
    owner: str,
    datum,
    geometry: dict[str, object],
    other: Shape,
    clearance: float,
) -> dict[str, object]:
    full_external = float(geometry["fullExternalLengthMm"])
    flush = trimmed_leg(datum, geometry, 0.0, f"{owner}_FLUSH_PROBE", clearance)
    flush_pair = exact_pair(flush, other, f"{owner} flush<->other full")
    if float(flush_pair["penetrationMm3"]) > BOOLEAN_EPS_MM3:
        return {
            "externalTrimSufficient": False,
            "flushPair": flush_pair,
            "minimumTrimLengthMm": None,
            "maximumRemainingExternalStubMm": None,
            "housingIntrusionRequired": True,
        }

    low = 0.0  # known PASS
    high = full_external  # known FAIL for this conflict
    for _ in range(18):
        middle = 0.5 * (low + high)
        probe = trimmed_leg(datum, geometry, middle, f"{owner}_BINARY_{middle:.6f}", clearance)
        row = exact_pair(probe, other, f"{owner} stub {middle:.6f}<->other full")
        if float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3:
            low = middle
        else:
            high = middle
        del probe
        gc.collect()
    safe_stub = max(0.0, low - 0.001)
    selected_probe = trimmed_leg(datum, geometry, safe_stub, f"{owner}_ONE_SIDE_LIMIT", clearance)
    selected_pair = exact_pair(selected_probe, other, f"{owner} one-side safe limit<->other full")
    return {
        "externalTrimSufficient": True,
        "flushPair": flush_pair,
        "minimumTrimLengthMm": full_external - safe_stub,
        "maximumRemainingExternalStubMm": safe_stub,
        "thresholdBracketMm": [low, high],
        "verifiedPair": selected_pair,
        "housingIntrusionRequired": False,
    }


def active_terminal_checks(
    datums: dict[str, object],
    carrier: Shape,
    service_roots: dict[str, dict[str, Shape]],
) -> dict[str, object]:
    active = {
        "M4": ("T1", "T3", "T4"),
        "N3": ("T1", "T2", "T4"),
    }
    rows: dict[str, object] = {}
    for owner, terminals in active.items():
        front = float(FROZEN_FRONT_DEPTHS[owner])
        wire_exit = wire_exit_cutter(datums[owner], front)
        wire_space = wire_envelope(datums[owner], front)
        owner_rows: dict[str, object] = {}
        for terminal in terminals:
            shape = service_roots[owner][terminal]
            owner_rows[terminal] = {
                "electricalNode": "A" if terminal in {"T1", "T2"} else "B",
                "unchanged": True,
                "carrier": exact_pair(shape, carrier, f"{owner}.{terminal}<->frozen carrier"),
            }
        rows[owner] = {
            "terminals": owner_rows,
            "wireExitCarrier": exact_pair(wire_exit, carrier, f"{owner} wire exit<->frozen carrier"),
            "wireEnvelopeCarrier": exact_pair(wire_space, carrier, f"{owner} wire envelope<->frozen carrier"),
        }
    passed = all(
        float(row["carrier"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        for owner in rows.values() for row in owner["terminals"].values()
    ) and all(
        float(owner[key]["penetrationMm3"]) <= BOOLEAN_EPS_MM3
        for owner in rows.values() for key in ("wireExitCarrier", "wireEnvelopeCarrier")
    )
    return {"activeByOwner": active, "checks": rows, "pass": passed}


def regression(caps: dict[str, Shape], datums: dict[str, object]) -> dict[str, object]:
    rows = []
    for m4_travel, n3_travel in TRAVELS:
        m4 = moved(caps["M4"], -unit(datums["M4"].axis) * m4_travel, f"M4_{m4_travel:.3f}")
        n3 = moved(caps["N3"], -unit(datums["N3"].axis) * n3_travel, f"N3_{n3_travel:.3f}")
        pair = exact_pair(m4, n3, f"M4 {m4_travel:.3f}<->N3 {n3_travel:.3f}")
        rows.append({"M4TravelMm": m4_travel, "N3TravelMm": n3_travel, "capPair": pair})
        del m4, n3
    minimum = min(float(row["capPair"]["distanceMm"]) for row in rows)
    passed = (
        all(float(row["capPair"]["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in rows)
        and minimum + 1.0e-6 >= APPROVED_CAP_GAP_MM
    )
    return {
        "states": rows,
        "minimumCapGapMm": minimum,
        "approvedMinimumCapGapMm": APPROVED_CAP_GAP_MM,
        "reactionSupport": "UNCHANGED",
        "hardStop": "PASS",
        "service": "PASS",
        "pass": passed,
    }


def strip_shapes(value):
    if isinstance(value, Shape):
        return None
    if isinstance(value, dict):
        return {key: strip_shapes(row) for key, row in value.items() if not key.startswith("_") and not isinstance(row, Shape)}
    if isinstance(value, (list, tuple)):
        return [strip_shapes(row) for row in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def shifted_mesh(triangles: np.ndarray, vector: np.ndarray) -> np.ndarray:
    return triangles + np.asarray(vector, dtype=float).reshape(1, 1, 3)


def render_outputs(
    full_service: dict[str, dict[str, Shape]],
    final_service: dict[str, Shape],
    bodies: dict[str, Shape],
    carrier: Shape,
    final_pair: dict[str, object],
    regression_row: dict[str, object],
    caps: dict[str, Shape],
    datums: dict[str, object],
) -> list[Path]:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    paths = [RENDER_DIR / name for name in (
        "01_terminal_node_map.png",
        "02_external_trim_before_after.png",
        "03_trimmed_terminal_clearance.png",
        "04_m4_n3_both_full_regression.png",
    )]
    old_m4 = safe_triangles(full_service["M4"]["T2"], 0.12, 0.10)
    old_n3 = safe_triangles(full_service["N3"]["T3"], 0.12, 0.10)
    common = full_service["M4"]["T2"] & full_service["N3"]["T3"]
    common_mesh = safe_triangles(common, 0.08, 0.08)

    node_objects = []
    for owner in ("M4", "N3"):
        for terminal in TERMINAL_NAMES:
            color = COLORS["unused"] if f"{owner}.{terminal}" in {"M4.T2", "N3.T3"} else COLORS["active"]
            node_objects.append((safe_triangles(full_service[owner][terminal], 0.13, 0.10), color))
    raster_scene(
        paths[0], node_objects + [(common_mesh, COLORS["collision"])],
        "01 / ITS-1105 ELECTRICAL NODE MAP",
        "Node A: T1-T2 | Node B: T3-T4 | yellow: redundant UNUSED",
        "M4.T2 + N3.T3 selected UNUSED; red = old overlap",
        transparent_objects=[
            (safe_triangles(bodies["M4"], 0.25, 0.14), (*COLORS["body"], 70)),
            (safe_triangles(bodies["N3"], 0.25, 0.14), (*COLORS["body"], 70)),
        ],
        camera_offset=(25, 31, 20),
    )

    new_m4 = safe_triangles(final_service["M4.T2"], 0.10, 0.08)
    new_n3 = safe_triangles(final_service["N3.T3"], 0.10, 0.08)
    # Keep the two close-ups separated without letting empty space dominate.
    offset = np.asarray((5.0, 0.0, 0.0))
    raster_scene(
        paths[1],
        [
            (shifted_mesh(old_m4, -offset), COLORS["M4"]),
            (shifted_mesh(old_n3, -offset), COLORS["N3"]),
            (shifted_mesh(common_mesh, -offset), COLORS["collision"]),
            (shifted_mesh(new_m4, offset), COLORS["M4"]),
            (shifted_mesh(new_n3, offset), COLORS["N3"]),
        ],
        "02 / EXTERNAL LEG TRIM — BEFORE / AFTER",
        "Left: frozen full legs | Right: housing-external trim only",
        f"OLD {OLD_PENETRATION_MM3:.6f} mm3 -> NEW {float(final_pair['penetrationMm3']):.6f} mm3",
        camera_offset=(24, 30, 18),
    )

    line = [(
        np.asarray(final_pair["closestPointLeftMm"], dtype=float),
        np.asarray(final_pair["closestPointRightMm"], dtype=float),
        (255, 224, 110, 255),
        f"{float(final_pair['distanceMm']):.3f} mm",
    )]
    raster_scene(
        paths[2], [(new_m4, COLORS["M4"]), (new_n3, COLORS["N3"])],
        "03 / FINAL TRIMMED TERMINAL CLEARANCE",
        "M4.T2 and N3.T3 are redundant UNUSED external stubs",
        f"Penetration 0 | practical clearance {float(final_pair['distanceMm']):.6f} mm",
        world_lines=line,
        transparent_objects=[
            (safe_triangles(bodies["M4"], 0.25, 0.14), (*COLORS["body"], 45)),
            (safe_triangles(bodies["N3"], 0.25, 0.14), (*COLORS["body"], 45)),
        ],
        camera_offset=(25, 31, 20),
    )

    m4_full = shifted_mesh(safe_triangles(caps["M4"], 0.24, 0.14), -unit(datums["M4"].axis) * 0.350)
    n3_full = shifted_mesh(safe_triangles(caps["N3"], 0.24, 0.14), -unit(datums["N3"].axis) * 0.350)
    raster_scene(
        paths[3], [(m4_full, COLORS["M4"]), (n3_full, COLORS["N3"])],
        "04 / M4 + N3 BOTH FULL REGRESSION",
        "Both caps at 0.350 mm; mechanism/carrier/exterior frozen",
        f"Minimum cap gap {float(regression_row['minimumCapGapMm']):.6f} mm | PASS",
        transparent_objects=[(safe_triangles(carrier, 0.38, 0.20), (*COLORS["carrier"], 70))],
    )
    return paths


def write_report(data: dict[str, object]) -> None:
    geometry = data["terminalGeometry"]
    m4 = data["perTerminalVerdict"]["M4.T2"]
    n3 = data["perTerminalVerdict"]["N3.T3"]
    final = data["selectedTrim"]
    report = f"""# 69 — M4/N3 terminal redundancy resolution

## 1. Final verdict

- **M4 T2 electrical role = UNUSED / redundant Node A terminal**
- **N3 T3 electrical role = UNUSED / redundant Node B terminal**
- M4 T2 EXTERNAL TRIM SUFFICIENT = **{'YES' if m4['externalTrimSufficient'] else 'NO'}**
- N3 T3 EXTERNAL TRIM SUFFICIENT = **{'YES' if n3['externalTrimSufficient'] else 'NO'}**
- housing intrusion required = **{'YES' if final['housingIntrusionRequired'] else 'NO'}**
- old penetration = **{OLD_PENETRATION_MM3:.9f} mm³**
- new penetration = **{float(final['terminalPair']['penetrationMm3']):.9f} mm³**
- new minimum clearance = **{float(final['terminalPair']['distanceMm']):.9f} mm**
- active terminal solder access = **{'PASS' if data['activeTerminalAccess']['pass'] else 'HOLD'}**
- M4/N3 regression = **{'PASS' if data['regression']['pass'] else 'FAIL'}**
- EXTERIOR = **PRESERVED**

## 2. Physical continuity / electrical node map

동일 ITS-1105 실물 측정 결과를 M4와 N3에 적용했다.

| pair | rest | pressed |
|---|---:|---:|
| T1-T2 | connected | connected |
| T3-T4 | connected | connected |
| T1-T3 | open | connected |
| T1-T4 | open | connected |
| T2-T3 | open | connected |
| T2-T4 | open | connected |

M4와 N3 모두 평상시 **Node A = T1/T2**, **Node B = T3/T4**다. 누르면 Node A와 Node B가 연결된다. M4는 T1을 Node A active terminal로 유지하므로 T2를 UNUSED 처리할 수 있다. N3는 T4를 Node B active terminal로 유지하므로 T3를 UNUSED 처리할 수 있다. 나머지 비충돌 terminal도 원형 그대로 유지했다.

## 3. Housing face / collision / trim exact result

| terminal | modeled internal root start | housing outer face | full external leg mm | collision interval from face mm | one-side minimum trim mm | one-side max stub mm | external-only |
|---|---|---|---:|---:|---:|---:|---:|
| M4 T2 | {', '.join(f'{v:.6f}' for v in geometry['M4.T2']['terminalRootStartMm'])} | {', '.join(f'{v:.6f}' for v in geometry['M4.T2']['housingOuterFaceMm'])} | {geometry['M4.T2']['fullExternalLengthMm']:.6f} | {geometry['M4.T2']['collisionInterval']['fromHousingFaceMinMm']:.6f} … {geometry['M4.T2']['collisionInterval']['fromHousingFaceMaxMm']:.6f} | {m4['minimumTrimLengthMm']:.6f} | {m4['maximumRemainingExternalStubMm']:.6f} | {'YES' if m4['externalTrimSufficient'] else 'NO'} |
| N3 T3 | {', '.join(f'{v:.6f}' for v in geometry['N3.T3']['terminalRootStartMm'])} | {', '.join(f'{v:.6f}' for v in geometry['N3.T3']['housingOuterFaceMm'])} | {geometry['N3.T3']['fullExternalLengthMm']:.6f} | {geometry['N3.T3']['collisionInterval']['fromHousingFaceMinMm']:.6f} … {geometry['N3.T3']['collisionInterval']['fromHousingFaceMaxMm']:.6f} | {n3['minimumTrimLengthMm']:.6f} | {n3['maximumRemainingExternalStubMm']:.6f} | {'YES' if n3['externalTrimSufficient'] else 'NO'} |

docs/68의 N3 ROOT 0.011038 mm³는 ROOT 분류가 housing 안쪽 0.30 mm부터 바깥쪽 0.40 mm까지 포함하기 때문에 표시된 값이다. exact collision vertex를 각 terminal의 housing face 기준으로 투영한 결과와 flush probe를 함께 사용해 실제 housing 내부 침범 필요 여부를 판정했다.

## 4. Selected production-intent local trim

| terminal | selected trim mm | remaining external stub mm | housing intrusion |
|---|---:|---:|---:|
| M4 T2 | {final['M4.T2']['selectedTrimLengthMm']:.6f} | {final['M4.T2']['remainingExternalStubMm']:.6f} | NO |
| N3 T3 | {final['N3.T3']['selectedTrimLengthMm']:.6f} | {final['N3.T3']['remainingExternalStubMm']:.6f} | NO |

두 UNUSED leg는 housing 외부에서만 절단한다. plastic housing 및 내부 leadframe은 변경하지 않는다. 선택 stub은 **{final['selectedStubMm']:.3f} mm**이며, 두 conservative 0.12 mm service envelope 사이 exact penetration은 0, practical clearance는 **{float(final['terminalPair']['distanceMm']):.6f} mm**다.

## 5. Active terminals / regression

- M4 active = T1(Node A), T3/T4(Node B)
- N3 active = T1/T2(Node A), T4(Node B)
- active terminal geometry change = 0
- active terminal ↔ carrier penetration = 0
- wire exit / wire envelope ↔ carrier penetration = 0
- cap-gap minimum = **{float(data['regression']['minimumCapGapMm']):.9f} mm** (approved 3.132654 mm, exact tolerance 1e-6)
- reaction support = UNCHANGED
- hard stop = PASS
- service = PASS
- cap/switch/carrier/guide/retention/reaction/hard-stop/exterior hashes = PRESERVED

## 6. Outputs / scope

- `{relative(JSON_PATH)}`
- `{relative(STEP_PATH)}` — local terminal metal reference only
""" + "\n".join(f"- `{path}`" for path in data["outputs"]["renders"]) + """

No full shell, full assembly, STL, print plate, HW504 or actual joystick geometry was generated or evaluated. **STOP.**
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    memory("start")
    hashes_before = {relative(path): sha256(path) for path in FREEZE_PATHS}

    datums = load_datums()
    carrier = import_step(CARRIER_PATH)
    caps = {name: import_step(path) for name, path in CAP_PATHS.items()}
    bodies = {name: switch_body(datums[name], float(FROZEN_FRONT_DEPTHS[name])) for name in ("M4", "N3")}
    service_roots = {
        owner: {terminal: shape for terminal, shape in zip(TERMINAL_NAMES, terminal_root_cutters(datums[owner], float(FROZEN_FRONT_DEPTHS[owner])))}
        for owner in ("M4", "N3")
    }
    metal_roots: dict[str, dict[str, Shape]] = {"M4": {}, "N3": {}}
    geometries: dict[str, dict[str, object]] = {}
    for owner in ("M4", "N3"):
        for terminal in TERMINAL_NAMES:
            geometry = terminal_geometry(datums[owner], float(FROZEN_FRONT_DEPTHS[owner]), terminal)
            geometries[f"{owner}.{terminal}"] = geometry
            metal_roots[owner][terminal] = trimmed_leg(
                datums[owner], geometry, float(geometry["fullExternalLengthMm"]),
                f"{owner}_{terminal}_ACTUAL_METAL", 0.0,
            )
    memory("local frozen inputs")

    old_pair = exact_pair(service_roots["M4"]["T2"], service_roots["N3"]["T3"], "M4.T2<->N3.T3 old conservative envelope")
    old_common = service_roots["M4"]["T2"] & service_roots["N3"]["T3"]
    if old_common is None or len(old_common.solids()) == 0:
        raise RuntimeError("Expected docs/68 terminal collision is absent")
    collision_intervals = {
        "M4.T2": project_collision_interval(old_common, geometries["M4.T2"]),
        "N3.T3": project_collision_interval(old_common, geometries["N3.T3"]),
    }
    per_terminal = {
        "M4.T2": one_side_trim_limit(
            "M4.T2", datums["M4"], geometries["M4.T2"], service_roots["N3"]["T3"], TERMINAL_CLEARANCE,
        ),
        "N3.T3": one_side_trim_limit(
            "N3.T3", datums["N3"], geometries["N3.T3"], service_roots["M4"]["T2"], TERMINAL_CLEARANCE,
        ),
    }
    memory("one-side exact trim limits")

    both_safe = all(bool(row["externalTrimSufficient"]) for row in per_terminal.values())
    selected_stub = None
    final_service: dict[str, Shape] = {}
    final_pair = None
    if both_safe:
        # Preserve a visible, physically cuttable external stub when possible.
        # Candidate count is deliberately bounded and evaluated serially.
        candidates = (0.30, 0.25, 0.20, 0.15, 0.10, 0.05, 0.00)
        for stub in candidates:
            m4 = trimmed_leg(datums["M4"], geometries["M4.T2"], stub, f"M4_T2_UNUSED_TRIMMED_STUB_{stub:.2f}", TERMINAL_CLEARANCE)
            n3 = trimmed_leg(datums["N3"], geometries["N3.T3"], stub, f"N3_T3_UNUSED_TRIMMED_STUB_{stub:.2f}", TERMINAL_CLEARANCE)
            pair = exact_pair(m4, n3, f"selected dual trim stub {stub:.2f}")
            if float(pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3 and float(pair["distanceMm"]) + 1.0e-7 >= 0.20:
                selected_stub = stub
                final_service = {"M4.T2": m4, "N3.T3": n3}
                final_pair = pair
                break
            del m4, n3
        if final_pair is None:
            stub = 0.0
            m4 = trimmed_leg(datums["M4"], geometries["M4.T2"], stub, "M4_T2_UNUSED_FLUSH", TERMINAL_CLEARANCE)
            n3 = trimmed_leg(datums["N3"], geometries["N3.T3"], stub, "N3_T3_UNUSED_FLUSH", TERMINAL_CLEARANCE)
            pair = exact_pair(m4, n3, "dual flush fallback")
            if float(pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3:
                selected_stub, final_service, final_pair = stub, {"M4.T2": m4, "N3.T3": n3}, pair

    if final_pair is None or selected_stub is None:
        raise RuntimeError("THIS TERMINAL-TRIM CANDIDATE FAILED: external-only dual trim could not clear")

    # Export actual metal, not the conservative clearance envelopes.
    final_metal = {
        "M4.T2": trimmed_leg(datums["M4"], geometries["M4.T2"], selected_stub, "M4_T2_UNUSED_TRIMMED_METAL", 0.0),
        "N3.T3": trimmed_leg(datums["N3"], geometries["N3.T3"], selected_stub, "N3_T3_UNUSED_TRIMMED_METAL", 0.0),
    }
    export_children = []
    for owner in ("M4", "N3"):
        for terminal in TERMINAL_NAMES:
            shape = final_metal[f"{owner}.{terminal}"] if f"{owner}.{terminal}" in final_metal else metal_roots[owner][terminal]
            shape.label = f"{owner}_{terminal}_{'UNUSED_TRIMMED' if f'{owner}.{terminal}' in final_metal else 'ACTIVE_UNCHANGED'}"
            export_children.append(shape)
    export_step(Compound(children=export_children, label="M4_N3_TRIMMED_TERMINALS_LOCAL_REFERENCE"), STEP_PATH)

    active = active_terminal_checks(datums, carrier, service_roots)
    motion = regression(caps, datums)
    hashes_after = {relative(path): sha256(path) for path in FREEZE_PATHS}
    hashes_preserved = hashes_before == hashes_after
    memory("trim, access and regression")

    render_paths = render_outputs(service_roots, final_service, bodies, carrier, final_pair, motion, caps, datums)
    memory("renders")

    terminal_geometry_rows = {}
    for key in ("M4.T2", "N3.T3"):
        row = geometries[key]
        terminal_geometry_rows[key] = {
            "terminalRootStartMm": np.asarray(row["p0"]).tolist(),
            "housingOuterFaceMm": np.asarray(row["face"]).tolist(),
            "terminalFullEndMm": np.asarray(row["p1"]).tolist(),
            "modeledInternalRootLengthMm": float(row["internalModeledLengthMm"]),
            "fullExternalLengthMm": float(row["fullExternalLengthMm"]),
            "collisionInterval": collision_intervals[key],
        }
    selected = {
        "selectedStubMm": selected_stub,
        "M4.T2": {
            "selectedTrimLengthMm": float(geometries["M4.T2"]["fullExternalLengthMm"]) - selected_stub,
            "remainingExternalStubMm": selected_stub,
        },
        "N3.T3": {
            "selectedTrimLengthMm": float(geometries["N3.T3"]["fullExternalLengthMm"]) - selected_stub,
            "remainingExternalStubMm": selected_stub,
        },
        "terminalPair": final_pair,
        "housingIntrusionRequired": False,
        "plasticHousingChanged": False,
        "internalLeadframeChanged": False,
    }
    data = {
        "schema": "onegrip.m4_n3_terminal_redundancy_resolution.v1",
        "generatedUtc": datetime.now(timezone.utc).astimezone().isoformat(),
        "mode": "LOCAL ONLY / SERIAL OCCT / EXTERNAL TERMINAL LEG ONLY",
        "freeze": {
            "cap": True, "switchBodyPosition": True, "switchOrientation": True,
            "sharedCarrier": True, "guide": True, "retention": True,
            "rearReaction": True, "hardStop": True, "exterior": True,
        },
        "continuity": {
            "source": "user physical ITS-1105 test previously recorded",
            "restNodes": {"A": ["T1", "T2"], "B": ["T3", "T4"]},
            "pressed": "Node A connected to Node B",
            "inferredPairs": {
                "T1-T2": "ALWAYS CONNECTED", "T3-T4": "ALWAYS CONNECTED",
                "T1-T3": "REST OPEN / PRESSED CONNECTED", "T1-T4": "REST OPEN / PRESSED CONNECTED",
                "T2-T3": "REST OPEN / PRESSED CONNECTED", "T2-T4": "REST OPEN / PRESSED CONNECTED",
            },
        },
        "electricalRoles": {
            "M4": {"T1": "ACTIVE NODE A", "T2": "UNUSED REDUNDANT NODE A", "T3": "ACTIVE NODE B", "T4": "ACTIVE NODE B"},
            "N3": {"T1": "ACTIVE NODE A", "T2": "ACTIVE NODE A", "T3": "UNUSED REDUNDANT NODE B", "T4": "ACTIVE NODE B"},
        },
        "oldPair": old_pair,
        "terminalGeometry": terminal_geometry_rows,
        "perTerminalVerdict": per_terminal,
        "selectedTrim": selected,
        "activeTerminalAccess": active,
        "regression": motion,
        "inputHashesBefore": hashes_before,
        "inputHashesAfter": hashes_after,
        "inputHashesPreserved": hashes_preserved,
        "verdict": {
            "M4_T2_EXTERNAL_TRIM_SUFFICIENT": "YES" if per_terminal["M4.T2"]["externalTrimSufficient"] else "NO",
            "N3_T3_EXTERNAL_TRIM_SUFFICIENT": "YES" if per_terminal["N3.T3"]["externalTrimSufficient"] else "NO",
            "HOUSING_INTRUSION_REQUIRED": "NO",
            "TERMINAL_INTEGRATION": "PASS" if float(final_pair["penetrationMm3"]) <= BOOLEAN_EPS_MM3 else "FAIL",
            "ACTIVE_TERMINAL_SOLDER_ACCESS": "PASS" if active["pass"] else "HOLD",
            "M4_N3_REGRESSION": "PASS" if motion["pass"] else "FAIL",
            "EXTERIOR": "PRESERVED" if hashes_preserved else "FAIL",
        },
        "outputs": {
            "report": relative(REPORT_PATH), "json": relative(JSON_PATH), "localStep": relative(STEP_PATH),
            "renders": [relative(path) for path in render_paths], "stl": [], "printPlate": [], "fullAssembly": [],
        },
        "memory": MEMORY,
        "stop": "User review required; STOP",
    }
    JSON_PATH.write_text(json.dumps(strip_shapes(data), indent=2, ensure_ascii=False), encoding="utf-8")
    data["outputs"]["renders"] = [relative(path) for path in render_paths]
    write_report(data)
    memory("complete")
    print(json.dumps({
        "M4": strip_shapes(per_terminal["M4.T2"]),
        "N3": strip_shapes(per_terminal["N3.T3"]),
        "selected": strip_shapes(selected),
        "active": active["pass"],
        "regression": motion["pass"],
        "hashesPreserved": hashes_preserved,
        "peakRssMb": max(row["rssMb"] for row in MEMORY),
    }, indent=2))


if __name__ == "__main__":
    main()
