"""Clean-shell external finger-layout markers (no shell cuts or internals).

The two AP242 shell exports are immutable inputs.  This module creates eight
independent, shallow external marker solids only:

    retained/recreated: I2 I3 I4 M3 M4
    new physical IDs:   N1 N2 N3

It intentionally creates no opening, pocket, carrier, retention or wiring
geometry.  N1/N2/N3 remain ergonomic review seeds until the user approves the
rendered locations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
from build123d import (
    Align,
    Box,
    BuildPart,
    Compound,
    Plane,
    Shape,
    export_step,
    import_step,
)

from .middle_redesign import MIDDLE_DATUMS
from .source_of_truth import INDEX


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "local_cad" / "reference"
OUT_DIR = Path(__file__).resolve().parent / "out" / "finger_layout_reset"

JAD_STEP = REFERENCE_DIR / "JAD_CLEAN_PRE_FINGER.step"
JFD_STEP = REFERENCE_DIR / "JFD_CLEAN_PRE_FINGER.step"
THUMB_STEP = REFERENCE_DIR / "THUMB_ORIGINAL_PRE_FINGER_REFERENCE.step"

# External language only.  Marker depth is visual cap exposure, not a future
# shell opening or switch travel definition.
CAP_SIZE = 7.60
MARKER_EXPOSURE = 1.20

# User-markup ergonomic seeds.  Arc station is measured along the button-facing
# (-Y) shell contour, with positive station toward +X.
N1_Z = 25.0
N1_ARC_STATION = -11.0
N2_Z = 25.0
N2_ARC_STATION = 0.0
N3_Z = -11.125
N3_ARC_STATION = 20.0

TESSELLATION_TOLERANCE = 0.06
TESSELLATION_ANGLE = 0.08


Vec3 = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class LayoutDatum:
    name: str
    center: Vec3
    normal: Vec3
    kind: str
    owner: str
    source: str


@dataclass(frozen=True, slots=True)
class LayoutBuild:
    jad: Shape
    jfd: Shape
    visible_thumb: tuple[Shape, ...]
    parked_thumb: tuple[Shape, ...]
    datums: tuple[LayoutDatum, ...]
    removed: tuple[LayoutDatum, ...]
    markers: tuple[Shape, ...]

    @property
    def marker_compound(self) -> Compound:
        return Compound(children=list(self.markers), label="FINGER_LAYOUT_EXTERNAL_MARKERS_8")

    @property
    def review_compound(self) -> Compound:
        children = [*self.jad.solids(), *self.jfd.solids(), *self.visible_thumb, *self.markers]
        return Compound(children=children, label="CLEAN_SHELL_EXTERNAL_LAYOUT_REVIEW")


def unit(vector: Iterable[float]) -> np.ndarray:
    value = np.asarray(tuple(vector), dtype=float)
    return value / np.linalg.norm(value)


def vec(vector) -> Vec3:
    return (float(vector.X), float(vector.Y), float(vector.Z))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def triangles(shape: Shape) -> np.ndarray:
    vertices, faces = shape.tessellate(TESSELLATION_TOLERANCE, TESSELLATION_ANGLE)
    points = np.asarray([[v.X, v.Y, v.Z] for v in vertices], dtype=float)
    return points[np.asarray(faces, dtype=int)]


class TriangleMesh:
    """Small ray-cast helper for contour sampling of the exact STEP shells."""

    def __init__(self, triangle_array: np.ndarray):
        self.T = np.asarray(triangle_array, dtype=float)
        self.v0 = self.T[:, 0]
        self.e1 = self.T[:, 1] - self.v0
        self.e2 = self.T[:, 2] - self.v0
        raw = np.cross(self.e1, self.e2)
        lengths = np.linalg.norm(raw, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        self.normals = raw / lengths
        self._arc_cache: dict[float, tuple[list[tuple[float, np.ndarray, np.ndarray]], np.ndarray]] = {}

    def hits(self, origin: np.ndarray, direction: np.ndarray) -> list[tuple[float, int]]:
        direction = unit(direction)
        cross = np.cross(direction, self.e2)
        determinant = np.einsum("ij,ij->i", self.e1, cross)
        valid = np.abs(determinant) > 1e-12
        inverse = np.zeros_like(determinant)
        inverse[valid] = 1.0 / determinant[valid]
        offset = origin - self.v0
        u = np.einsum("ij,ij->i", offset, cross) * inverse
        q = np.cross(offset, self.e1)
        v = np.einsum("ij,ij->i", np.broadcast_to(direction, self.e1.shape), q) * inverse
        t = np.einsum("ij,ij->i", self.e2, q) * inverse
        mask = valid & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1.0 + 1e-9) & (t > 1e-7)
        indices = np.nonzero(mask)[0]
        indices = indices[np.argsort(t[indices])]
        result: list[tuple[float, int]] = []
        for index in indices:
            distance = float(t[index])
            if result and abs(distance - result[-1][0]) < 1e-4:
                continue
            result.append((distance, int(index)))
        return result

    def axis_center(self, z_value: float) -> np.ndarray:
        z = self.T[:, :, 2]
        selected = (z.min(axis=1) <= z_value) & (z.max(axis=1) >= z_value)
        points = self.T[selected].reshape(-1, 3)
        return np.asarray((0.0, 0.5 * (points[:, 1].min() + points[:, 1].max()), z_value))

    def outer_point(self, center: np.ndarray, theta: float) -> tuple[np.ndarray, np.ndarray]:
        direction = np.asarray((math.sin(theta), -math.cos(theta), 0.0))
        hit_rows = self.hits(center, direction)
        if not hit_rows:
            raise RuntimeError(f"No exterior hit at theta={theta}")
        distance, triangle_index = hit_rows[-1]
        point = center + direction * distance
        normal = self.normals[triangle_index].copy()
        if float(np.dot(normal, direction)) < 0:
            normal = -normal
        return point, unit(normal)

    def at_arc_station(self, z_value: float, target: float) -> tuple[np.ndarray, np.ndarray, float]:
        cache_key = round(float(z_value), 6)
        if cache_key not in self._arc_cache:
            center = self.axis_center(z_value)
            rows: list[tuple[float, np.ndarray, np.ndarray]] = []
            for theta in np.linspace(-math.pi * 0.60, math.pi * 0.60, 1201):
                try:
                    point, normal = self.outer_point(center, float(theta))
                except RuntimeError:
                    continue
                rows.append((float(theta), point, normal))
            zero = min(range(len(rows)), key=lambda index: abs(rows[index][0]))
            station = np.zeros(len(rows), dtype=float)
            for index in range(zero + 1, len(rows)):
                station[index] = station[index - 1] + np.linalg.norm(rows[index][1] - rows[index - 1][1])
            for index in range(zero - 1, -1, -1):
                station[index] = station[index + 1] - np.linalg.norm(rows[index][1] - rows[index + 1][1])
            self._arc_cache[cache_key] = (rows, station)
        rows, station = self._arc_cache[cache_key]
        selected = int(np.argmin(np.abs(station - target)))
        return rows[selected][1], rows[selected][2], float(station[selected])


def closest_surface_point(shape: Shape, point: Iterable[float]) -> tuple[Vec3, float]:
    rows = [face.distance_to_with_closest_points(tuple(point)) for face in shape.faces()]
    distance, on_face, _on_point = min(rows, key=lambda row: row[0])
    return vec(on_face), float(distance)


def marker(datum: LayoutDatum) -> Shape:
    normal = unit(datum.normal)
    local_x = np.cross((0.0, 0.0, 1.0), normal)
    if np.linalg.norm(local_x) < 1e-9:
        local_x = np.cross((0.0, 1.0, 0.0), normal)
    local_x = unit(local_x)
    plane = Plane(origin=datum.center, x_dir=tuple(local_x), z_dir=tuple(normal))
    with BuildPart(plane) as build:
        Box(
            CAP_SIZE,
            CAP_SIZE,
            MARKER_EXPOSURE,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    result = build.part
    result.label = f"BTN_{datum.name}_EXTERNAL_MARKER"
    return result


def build_layout() -> LayoutBuild:
    jad = import_step(JAD_STEP)
    jfd = import_step(JFD_STEP)
    thumb = import_step(THUMB_STEP)
    shells = {"JaD": jad, "JfD": jfd}

    shell_mesh = TriangleMesh(np.concatenate((triangles(jad), triangles(jfd))))

    retained: list[LayoutDatum] = []
    index_by_name = {datum.name: datum for datum in INDEX}
    for name in ("I2", "I3", "I4"):
        source = index_by_name[name]
        owner = "JfD" if source.dominant_side else "JaD"
        center, _distance = closest_surface_point(shells[owner], source.center)
        retained.append(LayoutDatum(name, center, source.normal, "retained", owner, "validated INDEX datum"))

    middle_by_name = {datum.name: datum for datum in MIDDLE_DATUMS}
    for name in ("M3", "M4"):
        source = middle_by_name[name]
        center, _distance = closest_surface_point(shells[source.shell_owner], source.center)
        retained.append(
            LayoutDatum(name, center, source.shell_normal, "retained", source.shell_owner,
                        "approved build123d MIDDLE datum")
        )

    new_rows = (
        ("N1", N1_Z, N1_ARC_STATION, "JfD"),
        ("N2", N2_Z, N2_ARC_STATION, "SPLIT_REVIEW"),
        ("N3", N3_Z, N3_ARC_STATION, "JaD"),
    )
    new_datums: list[LayoutDatum] = []
    for name, z_value, station, owner in new_rows:
        point, normal, actual_station = shell_mesh.at_arc_station(z_value, station)
        new_datums.append(
            LayoutDatum(
                name,
                tuple(float(value) for value in point),
                tuple(float(value) for value in normal),
                "new",
                owner,
                f"user-markup seed; z={z_value:.3f}; arc={actual_station:.3f}",
            )
        )

    removed: list[LayoutDatum] = []
    i1 = index_by_name["I1"]
    i1_center, _distance = closest_surface_point(jfd, i1.center)
    removed.append(LayoutDatum("I1", i1_center, i1.normal, "removed", "JfD", "former INDEX datum"))
    for name in ("M1", "M2"):
        source = middle_by_name[name]
        center, _distance = closest_surface_point(jfd, source.center)
        removed.append(
            LayoutDatum(name, center, source.shell_normal, "removed", "JfD", "former MIDDLE datum")
        )

    datums = tuple((*retained, *new_datums))
    marker_shapes = tuple(marker(datum) for datum in datums)

    # The tenth thumb solid (Small_joystick_attachment) is intentionally parked
    # at X~103 mm in the source Part Studio.  Preserve it in the reference STEP
    # but keep it out of the in-place visual review until an assembly transform
    # is needed.
    visible_thumb: list[Shape] = []
    parked_thumb: list[Shape] = []
    for solid in thumb.solids():
        if solid.bounding_box().max.X < 50.0:
            visible_thumb.append(solid)
        else:
            parked_thumb.append(solid)

    return LayoutBuild(
        jad=jad,
        jfd=jfd,
        visible_thumb=tuple(visible_thumb),
        parked_thumb=tuple(parked_thumb),
        datums=datums,
        removed=tuple(removed),
        markers=marker_shapes,
    )


def shape_metrics(shape: Shape) -> dict[str, object]:
    bbox = shape.bounding_box()
    return {
        "valid": bool(shape.is_valid),
        "solidCount": len(shape.solids()),
        "volumeMm3": float(shape.volume),
        "bboxMm": {"min": list(vec(bbox.min)), "max": list(vec(bbox.max))},
        "topology": {
            "vertices": len(shape.vertices()),
            "edges": len(shape.edges()),
            "faces": len(shape.faces()),
        },
    }


def export_layout(out_dir: Path = OUT_DIR) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    layout = build_layout()
    marker_path = out_dir / "FINGER_LAYOUT_EXTERNAL_MARKERS_8.step"
    review_path = out_dir / "CLEAN_SHELL_EXTERNAL_LAYOUT_REVIEW.step"
    export_step(layout.marker_compound, marker_path)
    export_step(layout.review_compound, review_path)

    manifest = {
        "schema": 1,
        "mode": "LOCAL build123d / external markers only / shell boolean 0 / Onshape write 0",
        "baseline": {
            "document": "OneGrip_Play_V1",
            "historicalState": "Start",
            "historicalVersionId": "4342e7db262cbced58bf16b8",
            "format": "STEP AP242",
            "units": "mm",
            "yAxisUpTransform": False,
            "files": {
                "JaD": {"path": str(JAD_STEP.relative_to(ROOT)), "sha256": sha256(JAD_STEP), **shape_metrics(layout.jad)},
                "JfD": {"path": str(JFD_STEP.relative_to(ROOT)), "sha256": sha256(JFD_STEP), **shape_metrics(layout.jfd)},
                "thumb": {
                    "path": str(THUMB_STEP.relative_to(ROOT)),
                    "sha256": sha256(THUMB_STEP),
                    "visibleInPlaceSolidCount": len(layout.visible_thumb),
                    "parkedSourceSolidCount": len(layout.parked_thumb),
                    **shape_metrics(import_step(THUMB_STEP)),
                },
            },
        },
        "parametersMm": {
            "capSize": CAP_SIZE,
            "markerExposure": MARKER_EXPOSURE,
            "N1": {"z": N1_Z, "arcStation": N1_ARC_STATION},
            "N2": {"z": N2_Z, "arcStation": N2_ARC_STATION},
            "N3": {"z": N3_Z, "arcStation": N3_ARC_STATION},
        },
        "datums": {datum.name: asdict(datum) for datum in layout.datums},
        "removedReferences": {datum.name: asdict(datum) for datum in layout.removed},
        "exports": {
            "markers": {"path": str(marker_path.relative_to(ROOT)), **shape_metrics(layout.marker_compound)},
            "review": {"path": str(review_path.relative_to(ROOT)), **shape_metrics(layout.review_compound)},
        },
        "gates": {
            "buttonCount": len(layout.datums),
            "retainedCount": sum(datum.kind == "retained" for datum in layout.datums),
            "newCount": sum(datum.kind == "new" for datum in layout.datums),
            "removedReferenceCount": len(layout.removed),
            "shellCutCount": 0,
            "openingCount": 0,
            "pocketCount": 0,
            "carrierCount": 0,
            "wiringGeometryCount": 0,
        },
    }
    manifest_path = out_dir / "finger_layout_reset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    manifest = export_layout()
    print(json.dumps(manifest["gates"], ensure_ascii=False))
    for name, datum in manifest["datums"].items():
        print(name, datum["center"], datum["normal"], datum["kind"])
    print(OUT_DIR)


if __name__ == "__main__":
    main()
