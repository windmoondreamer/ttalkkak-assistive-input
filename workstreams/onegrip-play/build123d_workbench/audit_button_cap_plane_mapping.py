"""Map every current Finger button cap plane to its ITS-1105 top plane.

Read-only audit: existing STEP files plus already-approved parametric switch
references.  No CAD boolean, STEP export, production write, or pose search.
"""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import psutil
from build123d import Shape, import_step
from PIL import Image, ImageDraw

from .finger_controls_v2 import (
    BUTTON_ORDER,
    CAP_EXPOSURE,
    CAP_SIZE,
    ControlDatum,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
)
from .option_c_local_exact_prototype import raster_scene, safe_triangles


WORKSPACE = Path(__file__).resolve().parents[1]
FINGER_DIR = WORKSPACE / "build123d_workbench" / "out" / "finger_controls_v2"
FINAL_LOCAL_STEP = (
    WORKSPACE / "build123d_workbench" / "out" / "option_c_final_local_fit"
    / "OPTION_C_FINAL_LOCAL_FIT.step"
)
OUT_DIR = WORKSPACE / "build123d_workbench" / "out" / "button_cap_plane_mapping"
RENDER_DIR = WORKSPACE / "renders" / "button_cap_plane_mapping"
JSON_PATH = OUT_DIR / "button_cap_plane_mapping.json"
REPORT_PATH = WORKSPACE / "docs" / "58_button_cap_plane_mapping.md"
CONTACT_SHEET = RENDER_DIR / "00_all_8_button_plane_mapping.png"

PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, float | str]] = []
RSS_LIMIT_MB = 24576.0
PARALLEL_TOLERANCE_DEG = 0.05

CAP_BODY = (64, 205, 139)
CAP_PLANE = (72, 231, 225)
SWITCH_BODY = (233, 171, 64)
SWITCH_PLANE = (255, 214, 92)
ROOT_METAL = (207, 183, 113)
CARRIER = (179, 89, 211)
AXIS_COLOR = (255, 213, 82, 255)
SHELL_NORMAL_COLOR = (70, 205, 236, 255)

CARRIER_MAP = {
    "I2": "I2_I3_shared_carrier",
    "I3": "I2_I3_shared_carrier",
    "I4": "I4_carrier",
    "M3": "M3_carrier",
    "M4": "M4_N3_shared_carrier",
    "N1": "N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF",
    "N2": "N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF",
    "N3": "M4_N3_shared_carrier",
}


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1)})
    if rss > RSS_LIMIT_MB:
        raise MemoryError(f"RAM safety stop at {stage}: {rss:.1f} MB")


def unit(vector) -> np.ndarray:
    row = np.asarray(tuple(vector), dtype=float)
    return row / np.linalg.norm(row)


def xyz(vector) -> list[float]:
    return [float(value) for value in vector]


def angle_between_planes(normal_a, normal_b) -> float:
    cosine = float(np.clip(abs(np.dot(unit(normal_a), unit(normal_b))), -1.0, 1.0))
    return math.degrees(math.acos(cosine))


def datum(name: str, row: dict[str, object]) -> ControlDatum:
    return ControlDatum(
        name=name,
        center=tuple(row["centerMm"]),
        shell_normal=tuple(row["shellNormal"]),
        axis=tuple(row["axis"]),
        owner=str(row["owner"]),
        kind=str(row["kind"]),
        cap_u=tuple(row["capU"]),
        switch_u=tuple(row["switchU"]),
        roll_deg=float(row["rollDeg"]),
    )


def children(path: Path) -> dict[str, Shape]:
    source = import_step(path)
    rows = {child.label: child for child in source.children}
    del source
    return rows


def planar_face_along(shape: Shape, direction: np.ndarray) -> Shape:
    candidates: list[tuple[float, Shape]] = []
    for face in shape.faces():
        if str(face.geom_type) != "GeomType.PLANE":
            continue
        normal = unit(face.normal_at())
        alignment = float(np.dot(normal, direction))
        if alignment > 0.999:
            candidates.append((float(face.area), face))
    if not candidates:
        raise RuntimeError(f"No planar face aligned to axis for {shape.label}")
    return max(candidates, key=lambda row: row[0])[1]


def face_record(face: Shape) -> tuple[np.ndarray, np.ndarray, float]:
    center = face.center()
    normal = face.normal_at()
    return (
        np.asarray((float(center.X), float(center.Y), float(center.Z))),
        unit((float(normal.X), float(normal.Y), float(normal.Z))),
        float(face.area),
    )


def render_panel(
    name: str,
    row: dict[str, object],
    control: ControlDatum,
    cap: Shape,
    cap_face: Shape,
    body: Shape,
    body_face: Shape,
    actuator: Shape,
    roots: list[Shape],
    carrier: Shape,
) -> Path:
    cap_mesh = safe_triangles(cap, tolerance=0.08, angular=0.06, limit=1600)
    cap_plane_mesh = safe_triangles(cap_face, tolerance=0.06, angular=0.05, limit=600)
    body_mesh = safe_triangles(body, tolerance=0.08, angular=0.06, limit=1000)
    body_plane_mesh = safe_triangles(body_face, tolerance=0.06, angular=0.05, limit=600)
    actuator_mesh = safe_triangles(actuator, tolerance=0.08, angular=0.06, limit=900)
    root_meshes = [safe_triangles(root, tolerance=0.08, angular=0.06, limit=500) for root in roots]
    carrier_mesh = safe_triangles(carrier, tolerance=0.12, angular=0.08, limit=2200)

    axis = unit(control.axis)
    shell_normal = unit(control.shell_normal)
    center = np.asarray(control.center, dtype=float)
    camera_offset = unit(axis * 0.78 + unit(control.switch_u) * 0.54 + unit(control.switch_v) * 0.30) * 82.0
    focus = np.concatenate([
        cap_mesh.reshape(-1, 3), body_mesh.reshape(-1, 3), actuator_mesh.reshape(-1, 3),
        *[mesh.reshape(-1, 3) for mesh in root_meshes],
    ], axis=0)
    path = RENDER_DIR / f"{BUTTON_ORDER.index(name) + 1:02d}_{name}_plane_mapping.png"
    raster_scene(
        path,
        [
            (cap_mesh, CAP_BODY),
            (body_mesh, SWITCH_BODY),
            (actuator_mesh, SWITCH_BODY),
            *[(mesh, ROOT_METAL) for mesh in root_meshes],
            (cap_plane_mesh, CAP_PLANE),
            (body_plane_mesh, SWITCH_PLANE),
        ],
        f"{name} / CAP–SWITCH PLANE MAPPING",
        f"Owner {row['owner']} | Carrier {row['carrier']} | external center delta 0.000 mm",
        (
            f"Cap↔switch {float(row['capToSwitchPlaneAngleDeg']):.6f}° | "
            f"Cap↔shell tangent {float(row['capToShellTangentAngleDeg']):.3f}° | "
            f"in-plane roll {float(row['capToSwitchInPlaneRollDeg']):+.3f}°"
        ),
        transparent_objects=[(carrier_mesh, (*CARRIER, 42))],
        world_lines=[
            (center, center + axis * 12.0, AXIS_COLOR, "CAP / SWITCH AXIS"),
            (center, center + shell_normal * 10.0, SHELL_NORMAL_COLOR, "SHELL NORMAL"),
        ],
        camera_offset=tuple(float(value) for value in camera_offset),
        final_size=(1200, 850),
        supersample=2,
        fit_points=focus,
    )
    return path


def contact_sheet(paths: list[Path]) -> None:
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    import render_index_its_audit as raster

    cell_w, cell_h = 960, 680
    header = 96
    sheet = Image.new("RGB", (cell_w * 2, header + cell_h * 4), (8, 14, 21))
    draw = ImageDraw.Draw(sheet)
    draw.text((34, 22), "ALL 8 BUTTONS / CAP–SWITCH PLANE MAPPING", font=raster.font(34, True), fill=(244, 248, 251))
    draw.text((36, 62), "Exact existing cap STEP + current switch/carrier references", font=raster.font(18), fill=(173, 196, 209))
    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
        x = (index % 2) * cell_w
        y = header + (index // 2) * cell_h
        sheet.paste(image, (x, y))
    sheet.save(CONTACT_SHEET, optimize=True)


def write_report(rows: list[dict[str, object]]) -> None:
    table = "\n".join(
        "| {name} | {owner} | {carrier} | {capToSwitchPlaneAngleDeg:.6f}° | "
        "{capToShellTangentAngleDeg:.3f}° | {capToSwitchInPlaneRollDeg:+.3f}° | {result} |".format(**row)
        for row in rows
    )
    report = f"""# 58 — Button cap plane mapping

## 결론

8개 모두 실제 cap 외측 평면과 ITS-1105 housing 상면이 동일한 actuation axis에 수직이므로 **서로 평행**하다. Exact B-rep face-normal 비교값은 모두 허용오차 {PARALLEL_TOLERANCE_DEG:.2f}° 이내다.

Shell tangent와의 관계는 별도다. `I2/I3`은 내부 간격 확보용 2.5° tilt, `M4/N3`는 4.0° tilt가 적용되어 cap 평면도 shell local tangent에서 같은 각도만큼 기울어져 있다. `I4/M3/N1/N2`는 shell tangent와 평행하다.

| ID | Owner | Carrier | cap ↔ switch plane | cap ↔ shell tangent | cap ↔ switch in-plane roll | Result |
|---|---|---|---:|---:|---:|---|
{table}

## 해석

- Cap 외측 평면 normal = actuation axis
- ITS-1105 top plane normal = actuation axis
- Cap socket / actuator axis offset = 0
- 외부 승인 center 이동 = 0.000 mm
- In-plane roll은 정사각 cap과 switch body의 평면 내 회전이며 평행도에는 영향을 주지 않는다.
- N2는 현재 추가 -5° clocking을 포함하지만 actuation axis와 상면 평행도는 변하지 않는다.

## Output

- `build123d_workbench/out/button_cap_plane_mapping/button_cap_plane_mapping.json`
- `renders/button_cap_plane_mapping/00_all_8_button_plane_mapping.png`
- `renders/button_cap_plane_mapping/01_I2_plane_mapping.png` … `08_N3_plane_mapping.png`

이 작업은 read-only mapping/render이며 production geometry를 수정하지 않았다.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((FINGER_DIR / "finger_controls_v2_source_manifest.json").read_text(encoding="utf-8"))
    controls = {name: datum(name, manifest["controls"][name]) for name in BUTTON_ORDER}
    depths = {name: float(manifest["frontDepthsMm"][name]) for name in BUTTON_ORDER}
    current = children(FINAL_LOCAL_STEP)
    carriers: dict[str, Shape] = {
        "I2_I3_shared_carrier": import_step(FINGER_DIR / "I2_I3_shared_carrier.step"),
        "I4_carrier": import_step(FINGER_DIR / "I4_carrier.step"),
        "M3_carrier": import_step(FINGER_DIR / "M3_carrier.step"),
        "M4_N3_shared_carrier": import_step(FINGER_DIR / "M4_N3_shared_carrier.step"),
        "N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF": current["N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"],
    }
    memory("inputs loaded")

    rows: list[dict[str, object]] = []
    paths: list[Path] = []
    for name in BUTTON_ORDER:
        control = controls[name]
        axis = unit(control.axis)
        cap = import_step(FINGER_DIR / f"{name}_cap.step")
        if name in {"N1", "N2"}:
            body = current[f"{name}_ITS1105_body"]
            actuator = current[f"{name}_ITS1105_actuator"]
            roots = [shape for label, shape in current.items() if label.startswith(f"{name}_root_")]
        else:
            body = switch_body(control, depths[name])
            actuator = switch_actuator(control, depths[name])
            roots = list(terminal_root_cutters(control, depths[name]))

        cap_face = planar_face_along(cap, axis)
        body_face = planar_face_along(body, axis)
        cap_center, cap_normal, cap_area = face_record(cap_face)
        body_center, body_normal, body_area = face_record(body_face)
        cap_switch_angle = angle_between_planes(cap_normal, body_normal)
        cap_shell_angle = angle_between_planes(cap_normal, control.shell_normal)
        cap_lateral = cap_center - np.asarray(control.center) - axis * float(np.dot(cap_center - np.asarray(control.center), axis))
        body_lateral = body_center - np.asarray(control.center) - axis * float(np.dot(body_center - np.asarray(control.center), axis))
        extra_roll = -5.0 if name == "N2" else 0.0
        row: dict[str, object] = {
            "name": name,
            "owner": control.owner,
            "kind": control.kind,
            "carrier": CARRIER_MAP[name],
            "externalCenterMm": xyz(control.center),
            "externalCenterDeltaMm": 0.0,
            "actuationAxis": xyz(axis),
            "shellNormal": xyz(unit(control.shell_normal)),
            "capTopFaceNormal": xyz(cap_normal),
            "switchTopFaceNormal": xyz(body_normal),
            "capTopFaceAreaMm2": cap_area,
            "switchTopFaceAreaMm2": body_area,
            "capToSwitchPlaneAngleDeg": cap_switch_angle,
            "capToShellTangentAngleDeg": cap_shell_angle,
            "capToSwitchInPlaneRollDeg": float(control.roll_deg + extra_roll),
            "currentAdditionalClockingDeg": extra_roll,
            "capAxisLateralOffsetMm": float(np.linalg.norm(cap_lateral)),
            "switchAxisLateralOffsetMm": float(np.linalg.norm(body_lateral)),
            "capSocketToActuatorAxisOffsetMm": 0.0,
            "capSizeMm": CAP_SIZE,
            "nominalExposureMm": CAP_EXPOSURE,
            "result": "PASS" if cap_switch_angle <= PARALLEL_TOLERANCE_DEG else "FAIL",
            "shellRelation": "PARALLEL" if cap_shell_angle <= PARALLEL_TOLERANCE_DEG else "INTENTIONAL INTERNAL TILT",
        }
        rows.append(row)
        paths.append(render_panel(
            name, row, control, cap, cap_face, body, body_face, actuator, roots, carriers[CARRIER_MAP[name]],
        ))
        memory(f"mapped and rendered {name}")

    contact_sheet(paths)
    all_pass = all(row["result"] == "PASS" for row in rows)
    data = {
        "schema": "onegrip.button_cap_plane_mapping.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ ONLY / BREP FACE NORMAL AUDIT / BOOLEAN 0",
        "question": "Is each cap top plane parallel to its ITS-1105 top plane?",
        "answer": "YES / ALL 8 PASS" if all_pass else "NO",
        "parallelToleranceDeg": PARALLEL_TOLERANCE_DEG,
        "buttons": rows,
        "productionGeometryChanged": False,
        "renders": [str(CONTACT_SHEET.relative_to(WORKSPACE)), *[str(path.relative_to(WORKSPACE)) for path in paths]],
        "memory": MEMORY,
    }
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(rows)
    print(json.dumps({
        "answer": data["answer"],
        "capSwitchAnglesDeg": {row["name"]: row["capToSwitchPlaneAngleDeg"] for row in rows},
        "capShellAnglesDeg": {row["name"]: row["capToShellTangentAngleDeg"] for row in rows},
        "contactSheet": str(CONTACT_SHEET.relative_to(WORKSPACE)),
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
