"""Build a deterministic manifest of local OneGrip CAD references.

This module is intentionally local-only.  It never imports an Onshape client,
opens a browser, or mutates upstream reference geometry.  STEP files are read
with OCCT through build123d; STL files are treated as triangulated references
and are never promoted to editable B-rep source geometry.
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from build123d import import_step


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "local_cad" / "manifests" / "local_reference_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def vector(row: Any) -> list[float]:
    return [float(row.X), float(row.Y), float(row.Z)]


def step_metrics(path: Path) -> dict[str, Any]:
    shape = import_step(path)
    bbox = shape.bounding_box()
    solids = list(shape.solids())
    return {
        "geometryKernel": "OCCT via build123d",
        "valid": bool(shape.is_valid),
        "solidCount": len(solids),
        "connectedComponentCount": len(solids),
        "watertight": bool(solids) and all(bool(s.is_valid) for s in solids),
        "volumeMm3": float(shape.volume),
        "bboxMm": {"min": vector(bbox.min), "max": vector(bbox.max)},
    }


def read_stl(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if len(data) >= 84:
        triangle_count = struct.unpack_from("<I", data, 80)[0]
        if 84 + triangle_count * 50 == len(data):
            triangles = np.empty((triangle_count, 3, 3), dtype=np.float64)
            offset = 84
            for index in range(triangle_count):
                values = struct.unpack_from("<12fH", data, offset)
                triangles[index] = np.asarray(values[3:12], dtype=float).reshape(3, 3)
                offset += 50
            return triangles

    vertices: list[list[float]] = []
    for line in data.decode("utf-8", errors="ignore").splitlines():
        words = line.strip().split()
        if len(words) == 4 and words[0].lower() == "vertex":
            vertices.append([float(words[1]), float(words[2]), float(words[3])])
    if not vertices or len(vertices) % 3:
        raise ValueError(f"Unsupported or malformed STL: {path}")
    return np.asarray(vertices, dtype=float).reshape(-1, 3, 3)


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        a, b = self.find(left), self.find(right)
        if a == b:
            return
        if self.rank[a] < self.rank[b]:
            a, b = b, a
        self.parent[b] = a
        if self.rank[a] == self.rank[b]:
            self.rank[a] += 1


def stl_topology(triangles: np.ndarray, tolerance: float = 1e-5) -> tuple[int, bool]:
    quantized = np.rint(triangles / tolerance).astype(np.int64)
    owners: dict[tuple[int, int, int], int] = {}
    edges: dict[tuple[tuple[int, int, int], tuple[int, int, int]], int] = defaultdict(int)
    components = UnionFind(len(triangles))

    for triangle_index, triangle in enumerate(quantized):
        keys = [tuple(int(v) for v in vertex) for vertex in triangle]
        for key in keys:
            previous = owners.setdefault(key, triangle_index)
            components.union(triangle_index, previous)
        for start, end in ((keys[0], keys[1]), (keys[1], keys[2]), (keys[2], keys[0])):
            edge = (start, end) if start <= end else (end, start)
            edges[edge] += 1

    component_count = len({components.find(i) for i in range(len(triangles))})
    watertight = bool(edges) and all(count == 2 for count in edges.values())
    return component_count, watertight


def stl_metrics(path: Path) -> dict[str, Any]:
    triangles = read_stl(path)
    flat = triangles.reshape(-1, 3)
    components, watertight = stl_topology(triangles)
    signed = np.einsum(
        "ij,ij->i",
        triangles[:, 0],
        np.cross(triangles[:, 1], triangles[:, 2]),
    ).sum() / 6.0
    return {
        "geometryKernel": "triangulated STL audit",
        "valid": bool(len(triangles)),
        "triangleCount": int(len(triangles)),
        "solidCount": int(components),
        "connectedComponentCount": int(components),
        "watertight": bool(watertight),
        "volumeMm3Approx": abs(float(signed)),
        "bboxMm": {
            "min": [float(v) for v in flat.min(axis=0)],
            "max": [float(v) for v in flat.max(axis=0)],
        },
    }


def role_for(path: Path) -> str:
    name = path.name.lower()
    relative = path.relative_to(ROOT).as_posix().lower()
    if name == "jad_clean_pre_finger.step":
        return "JaD shell reference"
    if name == "jfd_clean_pre_finger.step":
        return "JfD shell reference"
    if name == "thumb_original_pre_finger_reference.step":
        return "original THUMB component reference"
    if "joystick_1_jad" in name or name == "joystick - joystick_1.stl":
        return "JaD shell reference"
    if "joystick_2_jfd" in name or name == "joystick - joystick_2.stl":
        return "JfD shell reference"
    if "part 17" in name:
        return "RWID reference"
    if "part 18" in name:
        return "RZKD reference"
    if any(f"part {number}" in name for number in (13, 14, 15, 16)):
        return "INDEX cap/reference geometry"
    if "middle_redesign" in relative or name.startswith("middle_") or name.startswith("m1_") or name.startswith("m2_") or name.startswith("m3_") or name.startswith("m4_"):
        return "approved build123d MIDDLE output"
    if any(token in name for token in ("button_", "backplate", "small_joystick_attachment")):
        return "original THUMB component reference"
    if "stage_d" in relative:
        return "prior translated JaD shell study"
    if "lower_adapter" in relative:
        return "lower-adapter local CAD reference/output"
    return "local CAD reference"


def source_tier(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix().lower()
    if path.suffix.lower() in {".step", ".stp"}:
        if "build123d_workbench/out" in relative or "local_cad/export" in relative:
            return "generated_exact_brep"
        return "immutable_exact_brep"
    return "immutable_mesh_only" if "source_stl" in relative or "thumb_lower15_housing_mockup" in relative else "generated_mesh"


def selected_paths() -> list[Path]:
    steps = [
        path for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".step", ".stp"}
        and not any(part.startswith(".venv") for part in path.parts)
    ]

    stls: list[Path] = []
    source_dir = ROOT / "exports" / "full_exterior_minimal_mockup" / "source_stl"
    if source_dir.exists():
        stls.extend(source_dir.glob("*.stl"))
    for path in (
        ROOT / "exports" / "thumb_lower15_housing_mockup" / "OneGrip_lower15_housing_Joystick_1_JaD.stl",
        ROOT / "exports" / "thumb_lower15_housing_mockup" / "OneGrip_lower15_housing_Joystick_2_JfD.stl",
        ROOT / "cad_dump" / "thumb_reseat_stage_d" / "Joystick_1_stage_d.stl",
    ):
        if path.exists():
            stls.append(path)
    middle_out = ROOT / "build123d_workbench" / "out" / "middle_redesign"
    if middle_out.exists():
        stls.extend(
            path for path in middle_out.glob("*.stl")
            if "print_ready" not in path.name
        )
    return sorted(set(steps + stls), key=lambda p: p.relative_to(ROOT).as_posix().lower())


def entry(path: Path) -> dict[str, Any]:
    stat = path.stat()
    metrics = step_metrics(path) if path.suffix.lower() in {".step", ".stp"} else stl_metrics(path)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "format": path.suffix.lower().lstrip("."),
        "role": role_for(path),
        "sourceTier": source_tier(path),
        "sizeBytes": stat.st_size,
        "modifiedUtc": iso_mtime(path),
        "sha256": sha256(path),
        **metrics,
    }


def build_manifest(paths: Iterable[Path]) -> dict[str, Any]:
    rows = [entry(path) for path in paths]
    step_paths = [row["path"] for row in rows if row["format"] in {"step", "stp"}]
    # A carrier extension whose filename contains JaD/JfD is not a shell.
    # Require the semantic shell role as well as an exact B-rep format so the
    # STOP gate cannot be accidentally cleared by a small generated helper.
    jad_steps = [
        row["path"] for row in rows
        if row["format"] in {"step", "stp"} and row["role"] == "JaD shell reference"
    ]
    jfd_steps = [
        row["path"] for row in rows
        if row["format"] in {"step", "stp"} and row["role"] == "JfD shell reference"
    ]
    return {
        "schema": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOCAL-FIRST / filesystem-only / Onshape calls 0 / CAD write 0",
        "projectRoot": str(ROOT),
        "policy": {
            "step": "immutable editable B-rep interface; never overwritten",
            "stl": "triangulated reference or manufacturing output; not an editable shell baseline",
            "generatedGeometry": "build123d Python source is parametric source of truth",
        },
        "requiredBaselineStatus": {
            "JaDShellStep": {
                "status": "FOUND" if jad_steps else "MISSING",
                "paths": jad_steps,
            },
            "JfDShellStep": {
                "status": "FOUND" if jfd_steps else "MISSING",
                "paths": jfd_steps,
            },
            "separateScrewBrep": {
                "status": "MISSING",
                "paths": [],
                "note": "Screw keep-outs exist in validation data, but no separate editable screw STEP was found.",
            },
            "approvedMiddleBrep": {
                "status": "FOUND" if any("MIDDLE_reference_with_ITS1105.step" in path for path in step_paths) else "MISSING",
                "paths": [path for path in step_paths if "middle_redesign" in path.lower()],
            },
        },
        "summary": {
            "entryCount": len(rows),
            "stepCount": sum(row["format"] in {"step", "stp"} for row in rows),
            "stlCount": sum(row["format"] == "stl" for row in rows),
            "exactBrepCount": sum("brep" in row["sourceTier"] for row in rows),
            "meshOnlyCount": sum(row["sourceTier"] == "immutable_mesh_only" for row in rows),
        },
        "entries": rows,
    }


def main() -> None:
    manifest = build_manifest(selected_paths())
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "manifest": str(MANIFEST_PATH),
        "summary": manifest["summary"],
        "requiredBaselineStatus": manifest["requiredBaselineStatus"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
