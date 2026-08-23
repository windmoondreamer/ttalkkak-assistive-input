"""Render the current index/middle button caps seated in the latest exterior.

This is a render-only consumer.  It imports existing local STEP results,
tessellates only the button-neighbourhood shell triangles, and performs no CAD
boolean, STEP export, full assembly build, or production write.
"""

from __future__ import annotations

import gc
import json
import os
from pathlib import Path

import numpy as np
import psutil
from build123d import Shape, import_step

from .finger_controls_v2 import (
    BUTTON_ORDER,
    ControlDatum,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
)
from .option_c_local_exact_prototype import raster_scene, safe_triangles


ROOT = Path(__file__).resolve().parents[1]
FINGER_DIR = ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
EXTERIOR_DIR = ROOT / "build123d_workbench" / "out" / "integrated_exterior_lowered_thumb_v1"
FINAL_LOCAL_STEP = (
    ROOT / "build123d_workbench" / "out" / "option_c_final_local_fit"
    / "OPTION_C_FINAL_LOCAL_FIT.step"
)
RENDER_DIR = ROOT / "renders" / "current_index_middle_buttons_inserted"
EXTERIOR_RENDER = RENDER_DIR / "01_buttons_inserted_exterior_closeup.png"
INTERNAL_RENDER = RENDER_DIR / "02_buttons_inserted_transparent_internal.png"
SUMMARY_PATH = RENDER_DIR / "render_summary.json"

PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, float | str]] = []
RSS_LIMIT_MB = 24576.0

INDEX = (55, 203, 222)
MIDDLE = (247, 166, 65)
ADDED = (72, 211, 137)
SHELL_JAD = (42, 76, 97)
SHELL_JFD = (52, 91, 112)
SWITCH = (236, 185, 80)
ROOT_METAL = (207, 183, 113)
CARRIER = (183, 91, 213)


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / (1024.0 * 1024.0)
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1)})
    if rss > RSS_LIMIT_MB:
        raise MemoryError(f"render RAM safety stop: {rss:.1f} MB at {stage}")


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


def focus_box(meshes: list[np.ndarray], margin: tuple[float, float, float]) -> np.ndarray:
    points = np.concatenate([mesh.reshape(-1, 3) for mesh in meshes], axis=0)
    lower = points.min(axis=0) - np.asarray(margin, dtype=float)
    upper = points.max(axis=0) + np.asarray(margin, dtype=float)
    return np.asarray([
        (x, y, z)
        for x in (lower[0], upper[0])
        for y in (lower[1], upper[1])
        for z in (lower[2], upper[2])
    ], dtype=float)


def cap_color(name: str) -> tuple[int, int, int]:
    if name.startswith("I"):
        return INDEX
    if name.startswith("M"):
        return MIDDLE
    return ADDED


def source_children(path: Path) -> dict[str, Shape]:
    source = import_step(path)
    rows = {child.label: child for child in source.children}
    del source
    return rows


def main() -> None:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((FINGER_DIR / "finger_controls_v2_source_manifest.json").read_text(encoding="utf-8"))
    controls = {name: datum(name, manifest["controls"][name]) for name in BUTTON_ORDER}
    depths = {name: float(manifest["frontDepthsMm"][name]) for name in BUTTON_ORDER}
    jad = import_step(EXTERIOR_DIR / "JAD_EXTERIOR_LOWERED_THUMB_V1.step")
    jfd = import_step(EXTERIOR_DIR / "JFD_EXTERIOR_LOWERED_THUMB_V1.step")
    jad_mesh = safe_triangles(jad, tolerance=0.14, angular=0.10, limit=12000)
    jfd_mesh = safe_triangles(jfd, tolerance=0.14, angular=0.10, limit=12000)
    del jad, jfd
    memory("latest exterior full render mesh")

    caps = {name: import_step(FINGER_DIR / f"{name}_cap.step") for name in BUTTON_ORDER}
    cap_meshes = {name: safe_triangles(shape, tolerance=0.08, angular=0.06, limit=1800) for name, shape in caps.items()}
    exterior_focus = focus_box(list(cap_meshes.values()), (9.0, 7.0, 9.0))
    memory("eight seated cap meshes")

    exterior_objects = [
        (jad_mesh, SHELL_JAD),
        (jfd_mesh, SHELL_JFD),
        *[(cap_meshes[name], cap_color(name)) for name in BUTTON_ORDER],
    ]
    raster_scene(
        EXTERIOR_RENDER,
        exterior_objects,
        "INDEX / MIDDLE BUTTONS — CAPS INSTALLED",
        "Current frozen centers; all eight 7.60 mm caps seated at nominal rest position",
        "Cyan = I2/I3/I4 | Orange = M3/M4 | Green = N1/N2/N3 added positions",
        camera_offset=(58.0, -105.0, -32.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=exterior_focus,
    )
    memory("exterior close-up render")

    current = source_children(FINAL_LOCAL_STEP)
    carrier_shapes: list[Shape] = [
        current["N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"],
        import_step(FINGER_DIR / "I2_I3_shared_carrier.step"),
        import_step(FINGER_DIR / "M4_N3_shared_carrier.step"),
        import_step(FINGER_DIR / "I4_carrier.step"),
        import_step(FINGER_DIR / "M3_carrier.step"),
    ]

    switch_meshes: dict[str, np.ndarray] = {}
    root_meshes: dict[str, np.ndarray] = {}
    for name in BUTTON_ORDER:
        if name in {"N1", "N2"}:
            body = current[f"{name}_ITS1105_body"]
            actuator = current[f"{name}_ITS1105_actuator"]
            roots = [shape for label, shape in current.items() if label.startswith(f"{name}_root_")]
        else:
            body = switch_body(controls[name], depths[name])
            actuator = switch_actuator(controls[name], depths[name])
            roots = list(terminal_root_cutters(controls[name], depths[name]))
        switch_meshes[name] = np.concatenate((
            safe_triangles(body, tolerance=0.10, angular=0.08, limit=900),
            safe_triangles(actuator, tolerance=0.10, angular=0.08, limit=900),
        ))
        root_meshes[name] = np.concatenate([
            safe_triangles(root, tolerance=0.10, angular=0.08, limit=500)
            for root in roots
        ])
    carrier_meshes = [safe_triangles(shape, tolerance=0.12, angular=0.08, limit=2400) for shape in carrier_shapes]
    memory("current carriers and eight switch references")

    internal_objects = [
        *[(mesh, CARRIER) for mesh in carrier_meshes],
        *[(switch_meshes[name], SWITCH) for name in BUTTON_ORDER],
        *[(root_meshes[name], ROOT_METAL) for name in BUTTON_ORDER],
        *[(cap_meshes[name], cap_color(name)) for name in BUTTON_ORDER],
    ]
    raster_scene(
        INTERNAL_RENDER,
        internal_objects,
        "BUTTON FIT — CAP / ACTUATOR / SWITCH / CARRIER",
        "Current N1/N2 local carrier plus frozen I/M carriers; latest full shell mesh shown transparent",
        "Caps are seated, not exploded | N2 internal terminal fit remains HOLD from docs/57",
        transparent_objects=[
            (jad_mesh, (74, 153, 185, 30)),
            (jfd_mesh, (91, 174, 200, 30)),
        ],
        camera_offset=(64.0, -102.0, -42.0),
        final_size=(1920, 1280),
        supersample=2,
        fit_points=focus_box([*cap_meshes.values(), *carrier_meshes], (8.0, 7.0, 8.0)),
    )
    memory("transparent internal render")

    result = {
        "mode": "RENDER ONLY / EXISTING STEP READ ONLY / BOOLEAN 0",
        "latestExterior": "integrated_exterior_lowered_thumb_v1",
        "buttonsInstalled": list(BUTTON_ORDER),
        "capPosition": "nominal rest / frozen external centers",
        "N1N2Carrier": "OPTION_C_FINAL_LOCAL_FIT local STEP (carrier PASS, N2 terminal HOLD)",
        "productionGeometryChanged": False,
        "outputs": [str(EXTERIOR_RENDER.relative_to(ROOT)), str(INTERNAL_RENDER.relative_to(ROOT))],
        "memory": MEMORY,
    }
    SUMMARY_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "outputs": result["outputs"],
        "peakRssMb": max(float(row["rssMb"]) for row in MEMORY),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
