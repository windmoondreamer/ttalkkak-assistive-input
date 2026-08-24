"""Read-only geometric audit of the OneGrip right-hand STL print set.

Uses only NumPy so it can run in the bundled Codex Python runtime.  The audit
checks binary STL integrity, manifold edge incidence, degenerate triangles,
bed contact and downward-facing overhang area in the packed orientation.
"""
from __future__ import annotations

import json
import importlib.util
import argparse
import math
from pathlib import Path
import struct

import numpy as np


ROOT = Path(
    r"C:\Users\guest2\Desktop\ttalkkak-assistive-input-c194592cfffbde7b4ba161408b12d322893853a4"
) / "workstreams" / "onegrip-play"
STL_DIR = ROOT / "exports" / "right_hand_handle_parts" / "individual_stl"
MANIFEST = ROOT / "exports" / "right_hand_handle_parts" / "plates" / "layout_manifest.json"
PACKER_PATH = ROOT / "scripts" / "pack_right_hand_handle_stl.py"


def read_binary_stl(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    if len(raw) < 84:
        raise ValueError(f"short STL: {path}")
    count = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) != 84 + count * 50:
        raise ValueError(f"invalid binary STL length: {path}")
    dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attribute", "<u2"),
    ])
    return np.frombuffer(raw, dtype=dtype, count=count, offset=84)["vertices"].astype(np.float64)


def edge_audit(triangles: np.ndarray, tolerance: float = 1e-4) -> tuple[int, int, int]:
    vertices = np.rint(triangles.reshape(-1, 3) / tolerance).astype(np.int64)
    keys: dict[tuple[int, int, int], int] = {}
    indexed = np.empty(len(vertices), dtype=np.int64)
    for index, vertex in enumerate(vertices):
        key = tuple(int(value) for value in vertex)
        indexed[index] = keys.setdefault(key, len(keys))
    faces = indexed.reshape(-1, 3)
    edge_counts: dict[tuple[int, int], int] = {}
    for face in faces:
        for first, second in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge = (int(min(first, second)), int(max(first, second)))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    boundary = sum(count == 1 for count in edge_counts.values())
    nonmanifold = sum(count > 2 for count in edge_counts.values())
    return len(keys), boundary, nonmanifold


def apply_manifest_orientation(triangles: np.ndarray, record: dict) -> np.ndarray:
    basis = np.asarray(record["orientationBasis"], dtype=np.float64)
    points = triangles.reshape(-1, 3)
    centered = triangles - points.mean(axis=0)
    transformed = centered @ basis
    transformed -= transformed.reshape(-1, 3).min(axis=0)
    if record["rotated90OnPlate"]:
        old_x = transformed[:, :, 0].copy()
        transformed[:, :, 0] = -transformed[:, :, 1]
        transformed[:, :, 1] = old_x
        transformed -= transformed.reshape(-1, 3).min(axis=0)
    return transformed


def mesh_metrics(triangles: np.ndarray) -> dict:
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    twice_area = np.linalg.norm(cross, axis=1)
    area = twice_area * 0.5
    valid = twice_area > 1e-10
    normal = np.zeros_like(cross)
    normal[valid] = cross[valid] / twice_area[valid, None]
    centroids = triangles.mean(axis=1)
    above_first_layers = centroids[:, 2] > 0.6
    severe = valid & above_first_layers & (normal[:, 2] < -math.cos(math.radians(45)))
    moderate = valid & above_first_layers & (normal[:, 2] < -math.cos(math.radians(60)))
    downward = valid & above_first_layers & (normal[:, 2] < -0.01)
    footprint_contact = valid & (np.max(np.abs(triangles[:, :, 2]), axis=1) <= 0.20)
    _, boundary, nonmanifold = edge_audit(triangles)
    bbox = np.ptp(triangles.reshape(-1, 3), axis=0)
    return {
        "triangles": int(len(triangles)),
        "degenerate": int((~valid).sum()),
        "boundary_edges": int(boundary),
        "nonmanifold_edges": int(nonmanifold),
        "bbox_mm": [round(float(value), 3) for value in bbox],
        "contact_area_mm2": round(float(area[footprint_contact].sum()), 2),
        "severe_overhang_area_mm2": round(float(area[severe].sum()), 2),
        "moderate_overhang_area_mm2": round(float(area[moderate].sum()), 2),
        "all_downward_area_mm2": round(float(area[downward].sum()), 2),
        "surface_area_mm2": round(float(area[valid].sum()), 2),
        "severe_overhang_ratio_pct": round(float(area[severe].sum() / max(area[valid].sum(), 1e-12) * 100), 2),
    }


def load_packer_module():
    spec = importlib.util.spec_from_file_location("onegrip_packer", PACKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to import packer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def best_support_orientation(triangles: np.ndarray, candidate_bases) -> dict:
    points = triangles.reshape(-1, 3)
    center = points.mean(axis=0)
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    twice_area = np.linalg.norm(cross, axis=1)
    area = twice_area * 0.5
    valid = twice_area > 1e-10
    original_normals = np.zeros_like(cross)
    original_normals[valid] = cross[valid] / twice_area[valid, None]
    surface_area = float(area[valid].sum())
    candidates = []
    for basis in candidate_bases(triangles):
        oriented = (triangles - center) @ basis
        oriented -= oriented.reshape(-1, 3).min(axis=0)
        bbox = np.ptp(oriented.reshape(-1, 3), axis=0)
        normal = original_normals @ basis
        centroids = oriented.mean(axis=1)
        above = centroids[:, 2] > 0.6
        severe = valid & above & (normal[:, 2] < -math.cos(math.radians(45)))
        moderate = valid & above & (normal[:, 2] < -math.cos(math.radians(60)))
        downward = valid & above & (normal[:, 2] < -0.01)
        contact = valid & (np.max(np.abs(oriented[:, :, 2]), axis=1) <= 0.20)
        metrics = {
            "bbox_mm": [round(float(value), 3) for value in bbox],
            "contact_area_mm2": round(float(area[contact].sum()), 2),
            "severe_overhang_area_mm2": round(float(area[severe].sum()), 2),
            "moderate_overhang_area_mm2": round(float(area[moderate].sum()), 2),
            "all_downward_area_mm2": round(float(area[downward].sum()), 2),
            "surface_area_mm2": round(surface_area, 2),
            "severe_overhang_ratio_pct": round(float(area[severe].sum() / max(surface_area, 1e-12) * 100), 2),
        }
        if max(metrics["bbox_mm"][:2]) > 240.0:
            continue
        # Reject point/edge-balanced orientations; require at least 10 mm2 of
        # first-layer contact for tiny parts and 40 mm2 for larger parts.
        minimum_contact = 40.0 if metrics["surface_area_mm2"] > 1000 else 10.0
        if metrics["contact_area_mm2"] < minimum_contact:
            continue
        candidates.append((
            metrics["severe_overhang_area_mm2"],
            metrics["moderate_overhang_area_mm2"],
            metrics["bbox_mm"][2],
            -metrics["contact_area_mm2"],
            metrics,
        ))
    if not candidates:
        return {}
    candidates.sort(key=lambda item: item[:4])
    return candidates[0][4]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--focus", nargs="*", default=[])
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = {part["source"]: part for plate in manifest["plates"] for part in plate["parts"]}
    results = []
    packer = load_packer_module()
    for source, record in sorted(records.items(), key=lambda item: item[1]["name"]):
        if args.focus and record["name"] not in set(args.focus):
            continue
        triangles = read_binary_stl(STL_DIR / source)
        oriented = apply_manifest_orientation(triangles, record)
        current = mesh_metrics(oriented)
        best = best_support_orientation(triangles, packer.candidate_bases)
        results.append({
            "name": record["name"],
            "source": source,
            **current,
            "best_support_orientation": best,
        })
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
