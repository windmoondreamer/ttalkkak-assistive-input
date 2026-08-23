"""Orient the six MIDDLE service parts and place them on one safe STL plate."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pack_right_hand_handle_stl import (  # noqa: E402
    connected_component_count,
    orient_for_print,
    read_binary_stl,
    write_binary_stl,
)


OUT_DIR = ROOT / "build123d_workbench" / "out" / "middle_redesign"
PARTS = (
    "M1_M2_M3_shared_carrier",
    "M4_single_carrier",
    "M1_cap",
    "M2_cap",
    "M3_cap",
    "M4_cap",
)
PLATE_GAP = 5.0
PLATE_MARGIN = 6.0
SHELF_WIDTH = 90.0


def overhang_metrics(triangles: np.ndarray) -> dict:
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    area = np.linalg.norm(cross, axis=1) / 2.0
    normal_z = np.divide(
        cross[:, 2],
        2.0 * area,
        out=np.zeros(len(area), dtype=float),
        where=area > 1e-12,
    )
    centroid_z = triangles.mean(axis=1)[:, 2]
    downward = (normal_z < -np.cos(np.deg2rad(45.0))) & (centroid_z > 0.25)
    support_area = float(area[downward].sum())
    total_area = float(area.sum())
    return {
        "surfaceAreaMm2": total_area,
        "downwardOverhangAreaMm2": support_area,
        "downwardOverhangPercent": 100.0 * support_area / max(total_area, 1e-12),
        "downwardTriangleCount": int(downward.sum()),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = {}
    oriented_rows = []
    for name in PARTS:
        source = read_binary_stl(OUT_DIR / f"{name}.stl")
        result = orient_for_print(source, 220.0)
        triangles = result["triangles"]
        path = OUT_DIR / f"{name}_print_ready.stl"
        write_binary_stl(path, triangles, f"OneGrip {name} print-ready")
        metrics = {
            "path": str(path),
            "dimensionsMm": [float(value) for value in result["dims"]],
            "contactAreaMm2": float(result["contactArea"]),
            "contactRatio": float(result["contactRatio"]),
            "orientationScore": float(result["orientationScore"]),
            "basisRows": np.asarray(result["basis"]).tolist(),
            "solidMeshComponents": connected_component_count(triangles),
            **overhang_metrics(triangles),
        }
        records[name] = metrics
        oriented_rows.append((name, triangles, np.asarray(result["dims"], dtype=float)))

    # Deterministic shelf layout with a generous 5 mm XY gap.  This STL is a
    # print arrangement only; the six meshes intentionally remain disconnected.
    placed = []
    x = y = PLATE_MARGIN
    shelf_height = 0.0
    placements = {}
    for name, triangles, dims in oriented_rows:
        if x > PLATE_MARGIN and x + dims[0] + PLATE_MARGIN > SHELF_WIDTH:
            x = PLATE_MARGIN
            y += shelf_height + PLATE_GAP
            shelf_height = 0.0
        moved = triangles.copy()
        moved[:, :, 0] += x
        moved[:, :, 1] += y
        placed.append(moved)
        placements[name] = {
            "xyOriginMm": [float(x), float(y)],
            "xyMaximumMm": [float(x + dims[0]), float(y + dims[1])],
        }
        x += dims[0] + PLATE_GAP
        shelf_height = max(shelf_height, float(dims[1]))

    plate = np.concatenate(placed, axis=0)
    plate_path = OUT_DIR / "MIDDLE_6_parts_one_plate_print_ready.stl"
    write_binary_stl(plate_path, plate, "OneGrip MIDDLE 6 parts / 5 mm gap")
    report = {
        "mode": "local STL orientation and packing; CAD WRITE 0",
        "nozzleMm": 0.4,
        "plateGapMm": PLATE_GAP,
        "printablePartCount": 6,
        "plateMeshConnectedComponents": connected_component_count(plate),
        "plateDimensionsMm": (
            plate.reshape(-1, 3).max(axis=0) - plate.reshape(-1, 3).min(axis=0)
        ).tolist(),
        "platePath": str(plate_path),
        "placements": placements,
        "parts": records,
    }
    report_path = OUT_DIR / "middle_redesign_printability.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

