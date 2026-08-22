"""Validate the two binary STL housing shells without third-party mesh tools."""
from __future__ import annotations

from collections import Counter, defaultdict, deque
import json
from pathlib import Path
import struct
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "exports" / "thumb_lower15_housing_mockup"
ZIP = OUT / "OneGrip_lower15_external_housing_mockup_STL.zip"


def load_binary_stl(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if len(data) < 84:
        raise RuntimeError(f"{path.name}: binary STL header missing")
    count = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + count * 50:
        raise RuntimeError(f"{path.name}: binary STL length mismatch")
    record = np.dtype([
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attribute", "<u2"),
    ])
    return np.frombuffer(data, dtype=record, offset=84, count=count)["vertices"].astype(float)


def vertex_key(vertex: np.ndarray) -> tuple[int, int, int]:
    # 1 nm integer grid in the declared millimetre unit.  STL coordinates from
    # the same Onshape tessellation edge should match exactly; the tiny grid
    # also protects against signed-zero representation differences.
    return tuple(np.rint(vertex * 1_000_000.0).astype(np.int64).tolist())


def analyze(path: Path) -> dict:
    triangles = load_binary_stl(path)
    edge_counts: Counter = Counter()
    edge_orientation: Counter = Counter()
    edge_triangles: dict[tuple, list[int]] = defaultdict(list)
    degenerate = 0
    signed_volume = 0.0

    for index, tri in enumerate(triangles):
        cross = np.cross(tri[1] - tri[0], tri[2] - tri[0])
        if float(np.dot(cross, cross)) <= 1e-20:
            degenerate += 1
        signed_volume += float(np.dot(tri[0], np.cross(tri[1], tri[2]))) / 6.0
        keys = [vertex_key(vertex) for vertex in tri]
        for first, second in ((keys[0], keys[1]), (keys[1], keys[2]), (keys[2], keys[0])):
            canonical = (first, second) if first <= second else (second, first)
            edge_counts[canonical] += 1
            edge_orientation[canonical] += 1 if first <= second else -1
            edge_triangles[canonical].append(index)

    adjacency = [[] for _ in range(len(triangles))]
    for owners in edge_triangles.values():
        if len(owners) == 2:
            first, second = owners
            adjacency[first].append(second)
            adjacency[second].append(first)
    seen = set()
    components = 0
    for seed in range(len(triangles)):
        if seed in seen:
            continue
        components += 1
        queue = deque((seed,))
        seen.add(seed)
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)

    points = triangles.reshape(-1, 3)
    boundary = sum(1 for value in edge_counts.values() if value != 2)
    orientation_bad = sum(
        1 for edge, value in edge_counts.items()
        if value == 2 and edge_orientation[edge] != 0
    )
    result = {
        "file": path.name,
        "triangles": int(len(triangles)),
        "uniqueEdges": int(len(edge_counts)),
        "nonTwoManifoldEdges": int(boundary),
        "inconsistentSharedEdgeOrientation": int(orientation_bad),
        "degenerateTriangles": int(degenerate),
        "connectedComponents": int(components),
        "watertight": bool(boundary == 0),
        "windingConsistent": bool(orientation_bad == 0),
        "volumeMm3": abs(signed_volume),
        "boundsMm": [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
        "extentsMm": (points.max(axis=0) - points.min(axis=0)).tolist(),
    }
    result["printMeshGate"] = "PASS" if (
        result["watertight"]
        and result["windingConsistent"]
        and result["degenerateTriangles"] == 0
        and result["connectedComponents"] == 1
        and result["volumeMm3"] > 0
    ) else "HOLD"
    return result


def main() -> None:
    files = sorted(OUT.glob("*.stl"))
    if len(files) != 2:
        raise RuntimeError(f"expected exactly two shell STL files, got {len(files)}")
    report = {
        "scope": "two external housing shells only",
        "unit": "millimeter",
        "results": [analyze(path) for path in files],
    }
    report["overall"] = (
        "PASS" if all(row["printMeshGate"] == "PASS" for row in report["results"])
        else "HOLD"
    )
    path = OUT / "mesh_validation.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["overall"] != "PASS":
        raise RuntimeError(json.dumps(report, indent=2))
    package_files = files + [
        OUT / "manifest.json",
        path,
        OUT / "README.md",
        ROOT / "renders" / "thumb_lower15_final_housing_assembled.png",
        ROOT / "renders" / "thumb_lower15_final_housing_exploded.png",
    ]
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for package_file in package_files:
            if package_file.exists():
                archive.write(package_file, package_file.name)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
