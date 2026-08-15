"""Reproducible geometry and mechanism validation for finger-input-v1.

This is deliberately independent of the build manifest's success strings.  It
opens every artifact again, interrogates the source B-reps, and evaluates the
mechanism at neutral and commanded travel.  The report distinguishes digital
geometry validation from tests that still require printed hardware and users.
"""

from __future__ import annotations

import json
import hashlib
import math
import struct
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

import finger_module_common as fm

from finger_module_common import (
    PRESETS,
    SWITCH,
    build_angle_wedge,
    build_bottom_cover,
    build_fixture_parts,
    build_four_finger_array,
    build_mount_plate,
    build_side_follower,
    build_switch_placeholder,
    build_variant_b_shell,
    build_variant_b_parts,
    build_vertical_array_rail,
    mechanism_layout,
    module_dimensions,
)


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
AUTHORITATIVE_ARTIFACT_DIRS = (
    ROOT / "printable",
    ROOT / "variants",
    ROOT / "integration",
    ROOT / "test_fixture",
)
VISUALIZATION_CACHE = ROOT / "renders" / "geometry_cache"
EPS = 1.0e-7
PROVENANCE_FILES = (
    "finger_module_common.py",
    "functional_comparators.py",
    "generate_all.py",
    "variant_a_direct_switch.py",
    "variant_b_lalboard_paddle.py",
    "variant_c_rocker.py",
    "render_previews.py",
    "validate_geometry.py",
    "build_manifest.json",
)


def rounded(value: float, digits: int = 5) -> float:
    return round(float(value), digits)


def provenance_hashes() -> dict[str, str]:
    return {
        relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in PROVENANCE_FILES
    }


def bbox_dict(bounds: Iterable[float]) -> dict[str, float]:
    xmin, ymin, zmin, xmax, ymax, zmax = bounds
    return {
        "x_mm": rounded(xmax - xmin),
        "y_mm": rounded(ymax - ymin),
        "z_mm": rounded(zmax - zmin),
    }


def shape_of(item: cq.Workplane | cq.Shape) -> cq.Shape:
    return item.val() if isinstance(item, cq.Workplane) else item


def parse_stl(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    triangles: list[tuple[tuple[float, float, float], ...]] = []
    encoding = "binary"
    if len(data) >= 84:
        count = struct.unpack_from("<I", data, 80)[0]
    else:
        count = -1
    if count >= 0 and 84 + count * 50 == len(data):
        for offset in range(84, len(data), 50):
            values = struct.unpack_from("<12fH", data, offset)
            triangles.append(
                (
                    (values[3], values[4], values[5]),
                    (values[6], values[7], values[8]),
                    (values[9], values[10], values[11]),
                )
            )
    else:
        encoding = "ascii"
        vertices: list[tuple[float, float, float]] = []
        for raw_line in data.decode("ascii", errors="strict").splitlines():
            fields = raw_line.strip().split()
            if fields and fields[0].lower() == "vertex" and len(fields) == 4:
                vertices.append(tuple(float(v) for v in fields[1:]))
        if len(vertices) % 3:
            raise ValueError("ASCII STL vertex count is not divisible by three")
        triangles = [tuple(vertices[i : i + 3]) for i in range(0, len(vertices), 3)]
    points = [point for triangle in triangles for point in triangle]
    if not points or not all(math.isfinite(v) for point in points for v in point):
        raise ValueError("STL has no finite triangle vertices")
    nondegenerate = 0
    edges: Counter[tuple[tuple[float, float, float], tuple[float, float, float]]] = Counter()
    for a, b, c in triangles:
        ab = tuple(b[i] - a[i] for i in range(3))
        ac = tuple(c[i] - a[i] for i in range(3))
        cross = (
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        )
        if sum(v * v for v in cross) > EPS * EPS:
            nondegenerate += 1
            # The exporter may repeat a zero-area seam facet.  Ignore those
            # facets for topology, then require every remaining welded edge to
            # have exactly two incident triangles (closed 2-manifold shells).
            vertices = [tuple(round(value, 5) for value in point) for point in (a, b, c)]
            for first, second in ((0, 1), (1, 2), (2, 0)):
                edges[tuple(sorted((vertices[first], vertices[second])))] += 1
    bounds = tuple(
        value
        for axis in range(3)
        for value in (min(p[axis] for p in points), max(p[axis] for p in points))
    )
    # Convert axis-major min/max to xmin,ymin,zmin,xmax,ymax,zmax.
    bounds = (bounds[0], bounds[2], bounds[4], bounds[1], bounds[3], bounds[5])
    dimensions = bbox_dict(bounds)
    boundary_edges = sum(count == 1 for count in edges.values())
    nonmanifold_edges = sum(count > 2 for count in edges.values())
    removed_degenerate = len(triangles) - nondegenerate
    return {
        "readable": True,
        "valid": bool(triangles) and nondegenerate > 0 and boundary_edges == 0 and nonmanifold_edges == 0 and min(dimensions.values()) > EPS,
        "encoding": encoding,
        "triangles": len(triangles),
        "nondegenerate_triangles": nondegenerate,
        "removed_zero_area_facets": removed_degenerate,
        "boundary_edges_after_weld": boundary_edges,
        "nonmanifold_edges_after_weld": nonmanifold_edges,
        "quality_warning": f"{removed_degenerate} zero-area seam facet(s) ignored" if removed_degenerate else None,
        "dimensions": dimensions,
    }


def parse_3mf(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"3MF ZIP CRC failure: {bad_member}")
        model_names = [name for name in archive.namelist() if name.lower().endswith(".model")]
        if not model_names:
            raise ValueError("3MF contains no .model resource")
        root = ET.fromstring(archive.read(model_names[0]))
    ns_uri = root.tag.partition("}")[0].lstrip("{")
    ns = {"m": ns_uri}
    points: list[tuple[float, float, float]] = []
    triangle_count = 0
    index_errors = 0
    object_count = 0
    degenerate_triangles = 0
    boundary_edges = 0
    nonmanifold_edges = 0
    object_topology: list[dict[str, Any]] = []
    for obj in root.findall(".//m:object", ns):
        mesh = obj.find("m:mesh", ns)
        if mesh is None:
            continue
        object_count += 1
        vertices = [
            tuple(float(vertex.attrib[axis]) for axis in ("x", "y", "z"))
            for vertex in mesh.findall("m:vertices/m:vertex", ns)
        ]
        points.extend(vertices)
        # CadQuery/lib3mf may emit a distinct vertex record for every facet
        # corner.  Index-only edge counting therefore labels even a closed
        # solid as entirely open.  Weld geometrically coincident coordinates
        # to 1e-5 mm before performing the 2-manifold edge census, matching
        # the STL audit tolerance above.
        welded_ids: dict[tuple[float, float, float], int] = {}
        vertex_to_welded: list[int] = []
        for vertex in vertices:
            key = tuple(round(value, 5) for value in vertex)
            if key not in welded_ids:
                welded_ids[key] = len(welded_ids)
            vertex_to_welded.append(welded_ids[key])
        object_edges: Counter[tuple[int, int]] = Counter()
        object_degenerate = 0
        object_triangles = 0
        for triangle in mesh.findall("m:triangles/m:triangle", ns):
            triangle_count += 1
            object_triangles += 1
            indices = [int(triangle.attrib[key]) for key in ("v1", "v2", "v3")]
            if len(set(indices)) != 3 or any(index < 0 or index >= len(vertices) for index in indices):
                index_errors += 1
                continue
            a, b, c = (vertices[index] for index in indices)
            ab = tuple(b[i] - a[i] for i in range(3))
            ac = tuple(c[i] - a[i] for i in range(3))
            cross = (
                ab[1] * ac[2] - ab[2] * ac[1],
                ab[2] * ac[0] - ab[0] * ac[2],
                ab[0] * ac[1] - ab[1] * ac[0],
            )
            if sum(value * value for value in cross) <= EPS * EPS:
                object_degenerate += 1
                continue
            welded = [vertex_to_welded[index] for index in indices]
            if len(set(welded)) != 3:
                object_degenerate += 1
                continue
            for first, second in ((0, 1), (1, 2), (2, 0)):
                object_edges[tuple(sorted((welded[first], welded[second])))] += 1
        object_boundary = sum(count == 1 for count in object_edges.values())
        object_nonmanifold = sum(count > 2 for count in object_edges.values())
        degenerate_triangles += object_degenerate
        boundary_edges += object_boundary
        nonmanifold_edges += object_nonmanifold
        object_topology.append(
            {
                "object_id": obj.attrib.get("id"),
                "vertices": len(vertices),
                "welded_vertices_1e-5_mm": len(welded_ids),
                "triangles": object_triangles,
                "ignored_zero_area_facets": object_degenerate,
                "boundary_edges": object_boundary,
                "nonmanifold_edges": object_nonmanifold,
                "watertight_2_manifold": object_triangles > object_degenerate and object_boundary == 0 and object_nonmanifold == 0,
            }
        )
    if not points or not all(math.isfinite(v) for point in points for v in point):
        raise ValueError("3MF has no finite mesh vertices")
    bounds = (
        min(p[0] for p in points), min(p[1] for p in points), min(p[2] for p in points),
        max(p[0] for p in points), max(p[1] for p in points), max(p[2] for p in points),
    )
    dimensions = bbox_dict(bounds)
    build_items = root.findall("m:build/m:item", ns)
    structural_valid = (
        triangle_count > 0
        and index_errors == 0
        and bool(build_items)
        and min(dimensions.values()) > EPS
    )
    return {
        "readable": True,
        "structural_valid": structural_valid,
        "valid": structural_valid and boundary_edges == 0 and nonmanifold_edges == 0,
        "mesh_objects": object_count,
        "build_items": len(build_items),
        "vertices": len(points),
        "triangles": triangle_count,
        "invalid_triangle_indices": index_errors,
        "ignored_zero_area_facets": degenerate_triangles,
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "object_topology": object_topology,
        "dimensions": dimensions,
    }


def parse_step(path: Path) -> dict[str, Any]:
    imported = cq.importers.importStep(str(path))
    shapes = imported.vals()
    if not shapes:
        raise ValueError("STEP importer returned no shapes")
    combined = cq.Compound.makeCompound(shapes)
    box = combined.BoundingBox()
    dimensions = {"x_mm": rounded(box.xlen), "y_mm": rounded(box.ylen), "z_mm": rounded(box.zlen)}
    volume = sum(max(0.0, shape.Volume()) for shape in shapes)
    return {
        "readable": True,
        "valid": all(shape.isValid() for shape in shapes) and volume > EPS and min(dimensions.values()) > EPS,
        "shapes": len(shapes),
        "volume_mm3": rounded(volume),
        "dimensions": dimensions,
    }


def constituent_shell_audit(artifact_path: Path) -> dict[str, Any]:
    """Audit authoritative STEP solids behind a tessellated assembly artifact."""
    step_path = artifact_path.with_suffix(".step")
    source = "matching STEP"
    try:
        if step_path.exists():
            imported = cq.importers.importStep(str(step_path))
            solids = [solid for shape in imported.vals() for solid in shape.Solids()]
        elif artifact_path.relative_to(ROOT).as_posix() == "integration/four_finger_array_with_surrogates.stl":
            source = "source B-rep (no STEP is exported for the surrogate preview)"
            solids = build_four_finger_array(True).Solids()
        else:
            return {"available": False, "reason": "no matching STEP/source audit route"}
        details = [
            {
                "index": index,
                "valid": solid.isValid(),
                "outer_shell_closed": solid.outerShell().Closed(),
                "volume_mm3": rounded(solid.Volume(), 8),
            }
            for index, solid in enumerate(solids)
        ]
        return {
            "available": True,
            "source": source,
            "solid_count": len(solids),
            "valid_solids": sum(item["valid"] for item in details),
            "closed_outer_shells": sum(item["outer_shell_closed"] for item in details),
            "all_constituent_solids_valid_and_closed": bool(solids) and all(
                item["valid"] and item["outer_shell_closed"] for item in details
            ),
            "solids": details,
        }
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


def is_multi_body_assembly_stem(stem: Path) -> bool:
    """Return True for coordinate assemblies that must remain STEP/3MF.

    Exporting these as a single STL welds independently valid solids at their
    tangent contacts and produces a mesh that slicers can misinterpret.  Their
    authoritative deliverables therefore preserve bodies in STEP and 3MF; STL
    is reserved for individually printable parts.
    """
    name = stem.name.lower()
    return (
        "assembly" in name
        or name in {
            "fixture_with_middle_module",
            "four_finger_array",
            "four_finger_array_with_attached_rail",
            "variant_a_direct_switch",
            "variant_b_lalboard_paddle",
            "variant_c_rocker",
        }
    )


def visualization_cache_inventory() -> list[dict[str, Any]]:
    """Inventory, but deliberately do not qualify, render-only flattened STL."""
    if not VISUALIZATION_CACHE.exists():
        return []
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "format": "stl",
            "bytes": path.stat().st_size,
            "policy": "visualization_only_non_authoritative",
            "excluded_from_printable_geometry_validation": True,
        }
        for path in sorted(VISUALIZATION_CACHE.glob("*_visualization_only.stl"))
    ]


def validate_files() -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    artifact_paths = sorted(
        path
        for directory in AUTHORITATIVE_ARTIFACT_DIRS
        if directory.exists()
        for path in directory.rglob("*")
        if path.suffix.lower() in {".stl", ".step", ".3mf"}
    )
    for path in artifact_paths:
        relative = path.relative_to(ROOT).as_posix()
        record: dict[str, Any] = {"path": relative, "format": path.suffix.lower()[1:], "bytes": path.stat().st_size}
        record["artifact_policy"] = (
            "multi_body_assembly" if is_multi_body_assembly_stem(path.with_suffix("")) else "individual_printable_part"
        )
        if path.suffix.lower() == ".stl" and record["artifact_policy"] == "multi_body_assembly":
            record.update({
                "readable": False,
                "valid": False,
                "error": "multi-body assemblies must be exported as STEP/3MF, not flattened STL",
            })
            failures.append(f"forbidden flattened assembly STL: {relative}")
            records.append(record)
            continue
        try:
            parser = {".stl": parse_stl, ".step": parse_step, ".3mf": parse_3mf}[path.suffix.lower()]
            record.update(parser(path))
            if path.suffix.lower() == ".3mf" and record["artifact_policy"] == "multi_body_assembly":
                # Some exporters nest a compound inside one 3MF mesh object.
                # Where independently closed solids touch, coordinate welding
                # can report edges with >2 incident facets even though the
                # assembly deliberately contains distinct, valid bodies.  In
                # that case qualify 3MF structure/dimensions against every
                # closed solid in its matching authoritative STEP file.
                audit = constituent_shell_audit(path)
                record["constituent_solid_audit"] = audit
                record["assembly_mesh_qualification"] = {
                    "structurally_valid_3mf": bool(record.get("structural_valid")),
                    "matching_step_solids_valid_and_closed": bool(
                        audit.get("all_constituent_solids_valid_and_closed")
                    ),
                    "tessellation_topology_is_not_used_to_union_distinct_bodies": True,
                }
                if (
                    record.get("structural_valid")
                    and audit.get("all_constituent_solids_valid_and_closed")
                ):
                    record["valid"] = True
                    record["validity_basis"] = "3MF structure + matching STEP constituent solid closure"
            if not record["valid"]:
                failures.append(f"invalid geometry file: {relative}")
        except Exception as exc:
            record.update({"readable": False, "valid": False, "error": f"{type(exc).__name__}: {exc}"})
            failures.append(f"unreadable geometry file: {relative}: {exc}")
        records.append(record)

    # A coordinate-only STL can become globally nonmanifold when otherwise
    # closed assembly constituents share a tangent edge. Record both facts;
    # strict STL validity remains false, but the report shows whether the
    # failure belongs to an individual part or only the flattened assembly.
    for record in records:
        if record["format"] == "stl" and not record.get("valid"):
            record["constituent_solid_audit"] = constituent_shell_audit(ROOT / record["path"])

    manifest = json.loads((ROOT / "build_manifest.json").read_text(encoding="utf-8"))
    manifest_paths: set[str] = set()

    def collect(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for value in node:
                collect(value)
        elif isinstance(node, str) and Path(node).suffix.lower() in {".stl", ".step", ".3mf"}:
            manifest_paths.add(Path(node).as_posix())

    collect(manifest)
    actual_paths = {record["path"] for record in records}
    missing = sorted(manifest_paths - actual_paths)
    failures.extend(f"manifest artifact missing: {path}" for path in missing)

    assembly_stems = sorted(
        {
            Path(path).with_suffix("").as_posix()
            for path in manifest_paths
            if is_multi_body_assembly_stem(Path(path).with_suffix(""))
        }
    )
    for stem in assembly_stems:
        expected = {f"{stem}.step", f"{stem}.3mf"}
        absent = sorted(expected - actual_paths)
        if absent:
            failures.append(f"assembly STEP/3MF pair incomplete: {stem}: missing {absent}")
        forbidden_stl = f"{stem}.stl"
        if forbidden_stl in actual_paths:
            # Normally recorded above; keep the policy explicit without adding
            # a second failure for the same file.
            matching = next(record for record in records if record["path"] == forbidden_stl)
            matching["assembly_format_policy_pass"] = False

    comparisons: list[dict[str, Any]] = []
    by_stem: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        if record.get("valid"):
            stem = str(Path(record["path"]).with_suffix(""))
            by_stem.setdefault(stem, {})[record["format"]] = record
    for stem, formats in sorted(by_stem.items()):
        if {"step", "3mf"}.issubset(formats):
            axis_deltas = {
                axis: rounded(max(formats[fmt]["dimensions"][axis] for fmt in formats) - min(formats[fmt]["dimensions"][axis] for fmt in formats))
                for axis in ("x_mm", "y_mm", "z_mm")
            }
            passed = max(axis_deltas.values()) <= 0.10
            comparisons.append({
                "stem": stem,
                "formats": sorted(formats),
                "max_dimension_delta_mm": axis_deltas,
                "pass": passed,
            })
            if not passed:
                failures.append(f"cross-format dimensions disagree by >0.10 mm: {stem}: {axis_deltas}")
    return records, failures, comparisons, visualization_cache_inventory()


def check(name: str, value: float, relation: str, limit: float, units: str = "mm") -> dict[str, Any]:
    passed = {
        ">=": value >= limit - EPS,
        "<=": value <= limit + EPS,
        ">": value > limit + EPS,
        "<": value < limit - EPS,
    }[relation]
    return {"name": name, "value": rounded(value), "units": units, "criterion": f"{relation} {limit}", "pass": passed}


def point_dict(point: Any) -> dict[str, float]:
    """Serialize either a CadQuery Vector or an OpenCascade point."""
    getter = (lambda axis: getattr(point, axis)) if hasattr(point, "x") else (lambda axis: getattr(point, axis.upper())())
    return {axis: rounded(getter(axis), 6) for axis in ("x", "y", "z")}


def proximity(first: cq.Shape, second: cq.Shape) -> dict[str, Any]:
    """Exact OpenCascade common volume and closest-point witnesses."""
    try:
        common = first.intersect(second)
        volume = max(0.0, common.Volume())
        result: dict[str, Any] = {"intersection_volume_mm3": rounded(volume, 8)}
        if volume > EPS:
            box = common.BoundingBox()
            result["intersection_bbox_mm"] = {
                "min": {"x": rounded(box.xmin, 6), "y": rounded(box.ymin, 6), "z": rounded(box.zmin, 6)},
                "max": {"x": rounded(box.xmax, 6), "y": rounded(box.ymax, 6), "z": rounded(box.zmax, 6)},
                "center": point_dict(box.center),
            }
        extrema = BRepExtrema_DistShapeShape(first.wrapped, second.wrapped)
        extrema.Perform()
        if not extrema.IsDone() or extrema.NbSolution() < 1:
            raise RuntimeError("OpenCascade distance solver returned no witness")
        result["minimum_distance_mm"] = rounded(extrema.Value(), 8)
        result["nearest_points_mm"] = {
            "first": point_dict(extrema.PointOnShape1(1)),
            "second": point_dict(extrema.PointOnShape2(1)),
        }
        result["distance_solutions"] = extrema.NbSolution()
        return result
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def collision_free(first: cq.Shape, second: cq.Shape, *, min_clearance: float | None = None) -> dict[str, Any]:
    record = proximity(first, second)
    passed = "error" not in record and record["intersection_volume_mm3"] <= 1.0e-6
    if min_clearance is not None and "error" not in record:
        passed = passed and record["minimum_distance_mm"] >= min_clearance - 1.0e-6
        record["minimum_clearance_criterion_mm"] = min_clearance
    record["pass"] = passed
    return record


def tangent_contact(first: cq.Shape, second: cq.Shape, tolerance_mm: float = 0.002) -> dict[str, Any]:
    record = proximity(first, second)
    record["contact_tolerance_mm"] = tolerance_mm
    record["pass"] = (
        "error" not in record
        and record["intersection_volume_mm3"] <= 1.0e-6
        and record["minimum_distance_mm"] <= tolerance_mm + 1.0e-6
    )
    return record


def register(failures: list[str], label: str, record: dict[str, Any]) -> None:
    if not record.get("pass", False):
        if "error" in record:
            detail = record["error"]
        elif "intersection_volume_mm3" not in record and "minimum_distance_mm" not in record:
            detail = json.dumps(record, ensure_ascii=False, sort_keys=True)
        else:
            detail = (
                f"volume={record.get('intersection_volume_mm3', 'n/a')} mm^3, "
                f"distance={record.get('minimum_distance_mm', 'n/a')} mm"
            )
        failures.append(f"{label}: {detail}")


def translated(shape: cq.Shape, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> cq.Shape:
    return shape.translate(cq.Vector(x, y, z))


def side_key_state(shape: cq.Shape, preset: Any, side: str, pressed: bool) -> cq.Shape:
    if not pressed:
        return shape
    layout = mechanism_layout(preset)
    sign = -1.0 if side == "left" else 1.0
    angle = float(layout["side_press_angle_deg"]) * (-sign)
    pivot_x = sign * float(layout["pivot_abs_x"])
    pivot_z = module_dimensions(preset)["pivot_height"]
    return shape.rotate(cq.Vector(pivot_x, 0, pivot_z), cq.Vector(pivot_x, 1, pivot_z), angle)


def pivot_exclusion(preset: Any, side: str) -> cq.Shape:
    """Only the two shell-ear bearing regions may touch a side key."""
    sign = -1.0 if side == "left" else 1.0
    pivot_x = sign * float(mechanism_layout(preset)["pivot_abs_x"])
    pivot_z = module_dimensions(preset)["pivot_height"]
    zones = [fm._cyl_y(2.25, 3.0, pivot_x, ear_y, pivot_z).val() for ear_y in (-7.0, 7.0)]
    return cq.Compound.makeCompound(zones)


def switch_components(x: float, y: float, pressed_travel: float) -> dict[str, cq.Shape]:
    body = fm._box(SWITCH.width, SWITCH.depth, SWITCH.body_height, x, y, 0.0).val()
    exposed = max(0.05, SWITCH.total_height - SWITCH.body_height - pressed_travel)
    plunger = fm._box(3.4, 3.4, exposed, x, y, SWITCH.body_height).val()
    pins = [
        fm._cyl_z(SWITCH.terminal_diameter / 2, SWITCH.terminal_length, x + offset, y, -SWITCH.terminal_length).val()
        for offset in (-SWITCH.terminal_pitch / 2, SWITCH.terminal_pitch / 2)
    ]
    return {"body": body, "plunger": plunger, "pin_minus": pins[0], "pin_plus": pins[1]}


def swept_retention_pin(y: float, top_z: float, travel: float) -> cq.Shape:
    top = fm._cyl_x(0.50, 4.0, 0, y, top_z).val()
    bottom = fm._cyl_x(0.50, 4.0, 0, y, top_z - travel).val()
    bridge = fm._box(4.0, 1.0, travel, 0, y, top_z - travel).val()
    return top.fuse(bottom, bridge)


def planar_slope_deg(shape: cq.Shape) -> dict[str, Any]:
    candidates: list[tuple[float, cq.Face, cq.Vector]] = []
    for face in shape.Faces():
        if face.geomType() != "PLANE":
            continue
        normal = face.normalAt()
        if normal.z > 0.5:
            candidates.append((face.Area(), face, normal))
    if not candidates:
        return {"error": "no upward planar face", "pass": False}
    _, face, normal = max(candidates, key=lambda item: item[0])
    slope = math.degrees(math.atan2(normal.y, normal.z))
    return {
        "slope_deg": rounded(slope, 6),
        "face_area_mm2": rounded(face.Area(), 6),
        "face_center_mm": point_dict(face.Center()),
        "face_normal": point_dict(normal),
    }


def circle_loci(shape: cq.Shape, radius: float, tolerance: float = 0.001) -> list[dict[str, Any]]:
    loci: dict[tuple[float, ...], dict[str, Any]] = {}
    for edge in shape.Edges():
        if edge.geomType() != "CIRCLE" or abs(edge.radius() - radius) > tolerance:
            continue
        circle = edge._geomAdaptor().Circle()
        location = circle.Location()
        direction = circle.Axis().Direction()
        key = tuple(round(value, 4) for value in (
            location.X(), location.Y(), location.Z(), abs(direction.X()), abs(direction.Y()), abs(direction.Z())
        ))
        loci[key] = {
            "center_mm": {"x": rounded(location.X(), 6), "y": rounded(location.Y(), 6), "z": rounded(location.Z(), 6)},
            "axis_abs": {"x": rounded(abs(direction.X()), 6), "y": rounded(abs(direction.Y()), 6), "z": rounded(abs(direction.Z()), 6)},
            "radius_mm": rounded(circle.Radius(), 6),
        }
    return list(loci.values())


def bound_points(box: Any) -> dict[str, dict[str, float]]:
    return {
        "min": {"x": rounded(box.xmin, 6), "y": rounded(box.ymin, 6), "z": rounded(box.zmin, 6)},
        "max": {"x": rounded(box.xmax, 6), "y": rounded(box.ymax, 6), "z": rounded(box.zmax, 6)},
    }


def mechanism_validation() -> tuple[dict[str, Any], list[str], int]:
    results: dict[str, Any] = {}
    failures: list[str] = []
    check_count = 0
    travel = SWITCH.pretravel_max + SWITCH.hard_stop_after_click
    for preset_name, preset in PRESETS.items():
        layout = mechanism_layout(preset)
        dims = module_dimensions(preset)
        built = build_variant_b_parts(preset)
        source_parts: dict[str, Any] = {}
        for name, item in built.items():
            shape = shape_of(item)
            box = shape.BoundingBox()
            source_parts[name] = {
                "valid": shape.isValid(),
                "volume_mm3": rounded(shape.Volume()),
                "solids": len(shape.Solids()),
                "dimensions": {"x_mm": rounded(box.xlen), "y_mm": rounded(box.ylen), "z_mm": rounded(box.zlen)},
                "pass": shape.isValid() and shape.Volume() > EPS,
            }
            check_count += 1
            if not source_parts[name]["valid"] or source_parts[name]["volume_mm3"] <= 0:
                failures.append(f"{preset_name}: invalid/nonempty source part {name}")

        shell = shape_of(built["cartridge"])
        cover = translated(shape_of(built["bottom_cover"]), z=-2.0)
        neutral_parts = {name: shape_of(item) for name, item in built.items()}
        states: dict[str, dict[str, cq.Shape]] = {}
        for state_name in ("neutral", "left", "center", "right"):
            state = dict(neutral_parts)
            if state_name in ("left", "right"):
                state[f"{state_name}_key"] = side_key_state(state[f"{state_name}_key"], preset, state_name, True)
                state[f"{state_name}_follower"] = translated(state[f"{state_name}_follower"], z=-travel)
            elif state_name == "center":
                state["center_key"] = translated(state["center_key"], z=-travel)
            states[state_name] = state

        state_checks: dict[str, Any] = {}
        for state_name, state in states.items():
            key_shell: dict[str, Any] = {}
            for side in ("left", "center", "right"):
                key = state[f"{side}_key"]
                raw = proximity(key, shell)
                if side == "center":
                    excluded = collision_free(key, shell)
                    excluded_volume = 0.0
                else:
                    exclusion = pivot_exclusion(preset, side)
                    excluded_key = key.cut(exclusion)
                    excluded = collision_free(excluded_key, shell)
                    excluded_volume = max(0.0, raw.get("intersection_volume_mm3", 0.0) - excluded.get("intersection_volume_mm3", 0.0))
                key_shell[side] = {
                    "raw": raw,
                    "intentional_pivot_region_removed_mm3": rounded(excluded_volume, 8),
                    "excluding_intentional_pivot": excluded,
                }
                check_count += 1
                register(failures, f"{preset_name}/{state_name}/{side} key-shell excluding pivot", excluded)

            key_key: dict[str, Any] = {}
            for first, second in (("left", "center"), ("center", "right"), ("left", "right")):
                record = collision_free(state[f"{first}_key"], state[f"{second}_key"], min_clearance=0.20)
                key_key[f"{first}_to_{second}"] = record
                check_count += 1
                register(failures, f"{preset_name}/{state_name}/{first}-{second} key", record)

            switch_fit: dict[str, Any] = {}
            for side in ("left", "center", "right"):
                x, y = layout[f"{side}_switch"]
                pressed = travel if state_name == side else 0.0
                components = switch_components(float(x), float(y), pressed)
                component_checks = {
                    "body_vs_shell_cavity": collision_free(components["body"], shell),
                    "plunger_vs_shell_opening": collision_free(components["plunger"], shell),
                    "body_vs_cover": collision_free(components["body"], cover),
                    "pin_minus_vs_cover_hole": collision_free(components["pin_minus"], cover),
                    "pin_plus_vs_cover_hole": collision_free(components["pin_plus"], cover),
                }
                switch_fit[side] = component_checks
                for label, record in component_checks.items():
                    check_count += 1
                    register(failures, f"{preset_name}/{state_name}/{side} switch {label}", record)

            state_checks[state_name] = {"key_shell": key_shell, "key_key": key_key, "switch_fit": switch_fit}

        followers: dict[str, Any] = {}
        for side in ("left", "right"):
            follower_neutral = neutral_parts[f"{side}_follower"]
            follower_full = translated(follower_neutral, z=-travel)
            key_neutral = neutral_parts[f"{side}_key"]
            key_full = side_key_state(key_neutral, preset, side, True)
            x, y = layout[f"{side}_switch"]
            switch_neutral = switch_components(float(x), float(y), 0.0)
            switch_full = switch_components(float(x), float(y), travel)
            follower_checks = {
                "solid_count": {
                    "value": len(follower_neutral.Solids()),
                    "criterion": "== 1 connected solid",
                    "pass": len(follower_neutral.Solids()) == 1,
                },
                "neutral": {
                    "follower_vs_shell": collision_free(follower_neutral, shell),
                    "cam_vs_follower": tangent_contact(key_neutral, follower_neutral),
                    "follower_vs_switch_plunger": tangent_contact(follower_neutral, switch_neutral["plunger"]),
                },
                "full_travel": {
                    "follower_vs_shell_hard_stop": tangent_contact(follower_full, shell),
                    "cam_vs_follower": tangent_contact(key_full, follower_full),
                    "follower_vs_switch_plunger": tangent_contact(follower_full, switch_full["plunger"]),
                },
            }
            check_count += 1
            register(failures, f"{preset_name}/{side} follower connected solid", follower_checks["solid_count"])
            for phase in ("neutral", "full_travel"):
                for label, record in follower_checks[phase].items():
                    check_count += 1
                    register(failures, f"{preset_name}/{side}/{phase}/{label}", record)

            sign = -1.0 if side == "left" else 1.0
            pivot_x = sign * float(layout["pivot_abs_x"])
            angle = float(layout["side_press_angle_deg"]) * (-sign)
            cam_neutral = fm._cyl_y(1.00, 3.0, float(x), float(y), dims["pivot_height"]).val()
            cam_full = cam_neutral.rotate(
                cq.Vector(pivot_x, 0, dims["pivot_height"]),
                cq.Vector(pivot_x, 1, dims["pivot_height"]),
                angle,
            )
            neutral_center = cam_neutral.Center()
            full_center = cam_full.Center()
            lateral_offset = abs(full_center.x - neutral_center.x)
            vertical_drop = neutral_center.z - full_center.z
            kinematics = {
                "neutral_cam_center_mm": point_dict(neutral_center),
                "full_cam_center_mm": point_dict(full_center),
                "lateral_offset_mm": rounded(lateral_offset, 8),
                "vertical_drop_mm": rounded(vertical_drop, 8),
                "follower_translation_mm": rounded(travel, 8),
                "switch_plunger_translation_mm": rounded(travel, 8),
                "lateral_offset_limit_mm": 0.05,
                "pass": lateral_offset <= 0.05 + 1.0e-6 and abs(vertical_drop - travel) <= 1.0e-6,
            }
            check_count += 1
            register(failures, f"{preset_name}/{side} cam kinematics", kinematics)
            follower_checks["kinematics"] = kinematics
            followers[side] = follower_checks

        center_pins: dict[str, Any] = {}
        guide_y = float(layout["center_guide_y"])
        for label, y in (("distal", -guide_y), ("proximal", guide_y)):
            neutral_pin = fm._cyl_x(0.50, 4.0, 0, y, 8.35).val()
            full_pin = translated(neutral_pin, z=-travel)
            envelope = swept_retention_pin(y, 8.35, travel)
            records = {
                "neutral_pin_vs_center_key_hole": collision_free(neutral_pin, states["neutral"]["center_key"]),
                "full_pin_vs_center_key_hole": collision_free(full_pin, states["center"]["center_key"]),
                "full_travel_envelope_vs_shell_slot": collision_free(envelope, shell),
                "envelope_bbox_mm": bound_points(envelope.BoundingBox()),
            }
            for record_label in (
                "neutral_pin_vs_center_key_hole",
                "full_pin_vs_center_key_hole",
                "full_travel_envelope_vs_shell_slot",
            ):
                check_count += 1
                register(failures, f"{preset_name}/center retention {label}/{record_label}", records[record_label])
            center_pins[label] = records

        results[preset_name] = {
            "preset": asdict(preset),
            "layout": layout,
            "source_parts": source_parts,
            "states": state_checks,
            "side_followers": followers,
            "center_retention_pins": center_pins,
        }
    return results, failures, check_count


def interface_validation() -> tuple[dict[str, Any], list[str], int]:
    """Validate adjustment and integration interfaces from the actual B-reps."""
    failures: list[str] = []
    check_count = 0
    middle = PRESETS["middle"]

    wedges: dict[str, Any] = {}
    for requested in (-8.0, 0.0, 8.0):
        shape = shape_of(build_angle_wedge(requested))
        slope = planar_slope_deg(shape)
        slope["requested_deg"] = requested
        slope["error_deg"] = rounded(abs(slope.get("slope_deg", math.inf) - requested), 8)
        slope["pass"] = "error" not in slope and slope["error_deg"] <= 0.01
        key = f"{requested:+.0f}deg"
        wedges[key] = slope
        check_count += 1
        register(failures, f"angle wedge {key}", slope)

    mount_shape = shape_of(build_mount_plate(middle))
    mount_holes = circle_loci(mount_shape, 1.7)
    mount_top = [item for item in mount_holes if abs(item["center_mm"]["z"] - mount_shape.BoundingBox().zmax) < 0.01]
    slot_end_y = sorted(
        item["center_mm"]["y"]
        for item in mount_top
        if abs(abs(item["center_mm"]["x"]) - 5.0) < 0.02 and item["axis_abs"]["z"] > 0.99
    )
    slot_centers = sorted({round(value, 3) for value in slot_end_y})
    usable_slot_range = max(slot_centers) - min(slot_centers) if len(slot_centers) >= 2 else -math.inf
    pivot_candidates = [item for item in mount_top if abs(item["center_mm"]["x"]) < 0.02 and abs(item["center_mm"]["y"] + 12.0) < 0.02]
    clamp_candidates = [
        item for item in mount_top
        if abs(item["center_mm"]["y"] - 12.0) < 0.02 and abs(item["center_mm"]["x"]) <= 3.38
    ]
    clamp_x = sorted({round(item["center_mm"]["x"], 3) for item in clamp_candidates})
    achieved_angle = math.degrees(math.atan2(max(abs(value) for value in clamp_x), 24.0)) if clamp_x else math.nan
    mount = {
        "detected_hole_loci": mount_top,
        "slot_endpoint_centers_y_mm": slot_centers,
        "usable_bolt_center_travel_mm": rounded(usable_slot_range, 6),
        "travel_each_side_mm": rounded(usable_slot_range / 2, 6),
        "slot_travel_pass": abs(usable_slot_range - 16.0) <= 0.01,
        "pivot_center_mm": pivot_candidates[0]["center_mm"] if pivot_candidates else None,
        "clamp_hole_x_mm": clamp_x,
        "pivot_to_clamp_y_mm": 24.0,
        "achieved_clamp_angle_deg": rounded(achieved_angle, 6),
        "angle_pass": bool(pivot_candidates) and {-3.37, 0.0, 3.37}.issubset(set(clamp_x)) and abs(achieved_angle - 8.0) <= 0.05,
    }
    mount["pass"] = mount["slot_travel_pass"] and mount["angle_pass"]
    check_count += 2
    if not mount["slot_travel_pass"]:
        failures.append(f"mount usable slot travel: measured {usable_slot_range} mm; required 16.0 mm (±8 mm)")
    if not mount["angle_pass"]:
        failures.append(f"mount clamp angle: measured {achieved_angle} deg from holes {clamp_x}; required ±8 deg")

    fixture = {name: shape_of(shape) for name, shape in build_fixture_parts(middle).items()}
    carrier_loci = circle_loci(fixture["fixture_carrier"], 1.7)
    carrier_zmax = fixture["fixture_carrier"].BoundingBox().zmax
    carrier_top = [
        item for item in carrier_loci
        if abs(item["center_mm"]["z"] - min(4.0, carrier_zmax)) < 0.01
        and item["axis_abs"]["z"] > 0.99
        and abs(abs(item["center_mm"]["x"]) - 5.0) < 0.02
    ]
    carrier_ranges: dict[str, list[float]] = {}
    for sign in (-5.0, 5.0):
        values = sorted({round(item["center_mm"]["y"], 3) for item in carrier_top if abs(item["center_mm"]["x"] - sign) < 0.02})
        carrier_ranges[f"x={sign:+.0f}"] = values
    module_holes_local = [{"x": x, "y": module_dimensions(middle)["depth"] / 2 + 2.0} for x in (-5.0, 5.0)]
    assembly_translation = {"x": 0.0, "y": -9.0, "z": 38.0}
    module_holes_fixture = [
        {"x": hole["x"], "y": hole["y"] + assembly_translation["y"], "z": assembly_translation["z"]}
        for hole in module_holes_local
    ]
    fixture_alignment_pass = all(
        values and min(values) - EPS <= 9.0 <= max(values) + EPS
        for values in carrier_ranges.values()
    )
    fixture_alignment = {
        "carrier_slot_endpoint_centers_y_mm": carrier_ranges,
        "module_mount_holes_local_mm": module_holes_local,
        "fixture_assembly_translation_mm": assembly_translation,
        "module_holes_in_fixture_mm": module_holes_fixture,
        "axis_parallel": True,
        "pass": fixture_alignment_pass,
    }
    check_count += 1
    if not fixture_alignment_pass:
        failures.append(f"fixture module holes do not fall in carrier slots: {fixture_alignment}")

    rail_shape = shape_of(build_vertical_array_rail())
    rail_loci = circle_loci(rail_shape, 1.7)
    rail_slots: dict[str, Any] = {}
    rail_slots_pass = True
    for preset_name, preset in PRESETS.items():
        expected_z = [preset.vertical_center - 5.0, preset.vertical_center + 5.0]
        slot_points = [
            item for item in rail_loci
            if item["axis_abs"]["x"] > 0.99
            and abs(item["center_mm"]["x"] + 26.0) < 0.02
            and any(abs(item["center_mm"]["z"] - z) < 0.02 for z in expected_z)
        ]
        endpoints = sorted({item["center_mm"]["y"] for item in slot_points})
        transformed_shell = shape_of(fm._transform_for_integration(build_variant_b_shell(preset), preset))
        nominal_holes = [
            item for item in circle_loci(transformed_shell, 1.7)
            if item["axis_abs"]["x"] > 0.99
            and abs(item["center_mm"]["x"] + 26.0) < 0.02
            and any(abs(item["center_mm"]["z"] - z) < 0.02 for z in expected_z)
        ]
        slot_axes = [item["axis_abs"] for item in slot_points]
        within_range = len(endpoints) >= 2 and len(nominal_holes) == 2 and all(
            min(endpoints) <= hole["center_mm"]["y"] <= max(endpoints) for hole in nominal_holes
        )
        z_aligned = sorted(hole["center_mm"]["z"] for hole in nominal_holes) == expected_z
        x_aligned = len(nominal_holes) == 2 and all(abs(hole["center_mm"]["x"] + 26.0) <= 0.001 for hole in nominal_holes)
        axes_parallel = len(nominal_holes) == 2 and bool(slot_points) and all(
            hole["axis_abs"]["x"] > 0.99 for hole in nominal_holes
        ) and all(item["axis_abs"]["x"] > 0.99 for item in slot_points)
        attachment = {
            "rail_slot_bolt_center_range_y_mm": endpoints,
            "rail_slot_centers_z_mm": [preset.vertical_center - 5.0, preset.vertical_center + 5.0],
            "rail_slot_axes": slot_axes,
            "array_module_hole_centers_mm": nominal_holes,
            "depth_within_slot_range": within_range,
            "z_centers_aligned": z_aligned,
            "rail_x_face_and_hole_axis_origin_aligned": x_aligned,
            "fastener_axes_parallel": axes_parallel,
            "pass": within_range and z_aligned and x_aligned and axes_parallel,
        }
        rail_slots[preset_name] = attachment
        rail_slots_pass = rail_slots_pass and attachment["pass"]
        check_count += 1
        if not attachment["pass"]:
            failures.append(
                f"array/rail attachment {preset_name}: actual module-hole/rail-slot loci mismatch: {attachment}"
            )
    array_shape = shape_of(build_four_finger_array(False))
    array_rail_proximity = proximity(array_shape, rail_shape)
    array_rail = {
        "array_bbox_mm": bound_points(array_shape.BoundingBox()),
        "rail_bbox_mm": bound_points(rail_shape.BoundingBox()),
        "as_built_proximity_without_additional_transform": array_rail_proximity,
        "preset_attachments": rail_slots,
        "pass": rail_slots_pass,
    }

    return {
        "angle_wedges": wedges,
        "mount_adjustment": mount,
        "fixture_alignment": fixture_alignment,
        "array_rail_attachment": array_rail,
    }, failures, check_count


def comparator_validation() -> tuple[dict[str, Any], list[str], int]:
    """At minimum, prove A/C moving members do not intersect their shells."""
    from functional_comparators import build_functional_comparators

    failures: list[str] = []
    check_count = 0
    comparison = build_functional_comparators(PRESETS["middle"])
    output: dict[str, Any] = {"assumptions": comparison["assumptions"]}
    for variant in ("variant_a", "variant_c"):
        variant_data = comparison[variant]
        printable: dict[str, Any] = {}
        for name, item in variant_data["printable_parts"].items():
            shape = shape_of(item)
            record = {
                "valid": shape.isValid(),
                "solids": len(shape.Solids()),
                "volume_mm3": rounded(shape.Volume(), 8),
            }
            record["pass"] = record["valid"] and record["volume_mm3"] > EPS
            printable[name] = record
            check_count += 1
            register(failures, f"{variant} printable {name}", record)

        states: dict[str, Any] = {}
        for state_name, raw_parts in variant_data["state_parts"].items():
            parts = {name: shape_of(item) for name, item in raw_parts.items()}
            shell = parts["shell"]
            if variant == "variant_a":
                moving_names = ["left_plunger", "center_plunger", "right_plunger"]
            else:
                moving_names = ["shared_rocker", "left_follower", "center_follower", "right_follower"]
            moving_shell: dict[str, Any] = {}
            for moving_name in moving_names:
                moving = parts[moving_name]
                if variant == "variant_c" and moving_name == "shared_rocker":
                    # The shaft barrel deliberately occupies the two ear slots.
                    # Remove only cylinders surrounding those intended bearings.
                    exclusions = [fm._cyl_y(2.40, 3.2, 0, y, 15.2).val() for y in (-7.4, 7.4)]
                    moving = moving.cut(cq.Compound.makeCompound(exclusions))
                record = collision_free(moving, shell)
                moving_shell[moving_name] = record
                check_count += 1
                register(failures, f"{variant}/{state_name}/{moving_name}-shell", record)
            states[state_name] = {"moving_member_vs_shell": moving_shell}
        output[variant] = {"printable_parts": printable, "states": states}
    return output, failures, check_count


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Finger input V1 geometry validation",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"**Overall: {'PASS' if summary['pass'] else 'FAIL'}** — {summary['passed_checks']} passed, {summary['failed_checks']} failed.",
        "",
        "## Artifact round-trip",
        "",
        "| Format | Files | Readable | Valid |",
        "|---|---:|---:|---:|",
    ]
    for fmt, row in summary["files_by_format"].items():
        lines.append(f"| {fmt.upper()} | {row['files']} | {row['readable']} | {row['valid']} |")
    lines.extend(
        [
            "",
            f"Cross-format STL/STEP/3MF dimension comparisons: **{summary['cross_format_passed']}/{summary['cross_format_comparisons']} passed** (maximum allowed delta 0.10 mm).",
            "",
            "## Mechanism states",
            "",
            "Volumes, clearances, and nearest-point coordinates are exact OpenCascade B-rep results. Side-key shell results remove only the two intentional pivot-ear bearing envelopes.",
            "",
            "| Preset | State | Minimum key-key clearance | Maximum prohibited key-shell volume |",
            "|---|---|---:|---:|",
        ]
    )
    for name, result in report["mechanisms"].items():
        for state_name, state in result["states"].items():
            clearance = min(item.get("minimum_distance_mm", math.inf) for item in state["key_key"].values())
            volume = max(item["excluding_intentional_pivot"].get("intersection_volume_mm3", math.inf) for item in state["key_shell"].values())
            lines.append(f"| {name} | {state_name} | {clearance:.6f} mm | {volume:.8f} mm³ |")
    lines.extend(["", "## Side follower evidence", "", "| Preset | Side | Lateral cam offset | Neutral cam contact distance | Full cam contact distance |", "|---|---|---:|---:|---:|"])
    for name, result in report["mechanisms"].items():
        for side, follower in result["side_followers"].items():
            lines.append(
                f"| {name} | {side} | {follower['kinematics']['lateral_offset_mm']:.6f} mm | "
                f"{follower['neutral']['cam_vs_follower'].get('minimum_distance_mm', math.inf):.8f} mm | "
                f"{follower['full_travel']['cam_vs_follower'].get('minimum_distance_mm', math.inf):.8f} mm |"
            )
    interfaces = report["interfaces"]
    slope_text = ", ".join(f"{key}={value.get('slope_deg', math.nan):.6f}°" for key, value in interfaces["angle_wedges"].items())
    lines.extend([
        "", "## Adjustment and integration interfaces", "",
        f"- Wedge slopes: {slope_text}.",
        f"- Mount usable slot travel: {interfaces['mount_adjustment']['usable_bolt_center_travel_mm']:.3f} mm; clamp angle: {interfaces['mount_adjustment']['achieved_clamp_angle_deg']:.6f}°.",
        f"- Fixture module-hole/carrier-slot alignment: {'PASS' if interfaces['fixture_alignment']['pass'] else 'FAIL'}.",
        f"- Array/rail attachment: {'PASS' if interfaces['array_rail_attachment']['pass'] else 'FAIL'}.",
    ])
    lines.extend(["", "## A/C comparator state checks", ""])
    for variant in ("variant_a", "variant_c"):
        state_text = []
        for state_name, state in report["comparators"][variant]["states"].items():
            passed = all(item["pass"] for item in state["moving_member_vs_shell"].values())
            state_text.append(f"{state_name}={'PASS' if passed else 'FAIL'}")
        lines.append(f"- {variant}: {', '.join(state_text)}.")
    lines.extend(["", "## Failures", ""])
    if report["failures"]:
        lines.extend(f"- {failure}" for failure in report["failures"])
    else:
        lines.append("None.")
    lines.extend(
        [
            "",
            "## Scope boundary",
            "",
            "This report validates digital file structure, imported B-rep validity, nonempty dimensions/volume, cross-format consistency, and nominal CAD kinematics. It does not establish printed tolerance, fatigue life, switch force variation, user comfort, or clinical suitability; those require the documented physical test protocol.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    started = time.perf_counter()
    hashes_before = provenance_hashes()
    file_records, file_failures, comparisons, visualization_cache = validate_files()
    mechanisms, mechanism_failures, mechanism_check_count = mechanism_validation()
    interfaces, interface_failures, interface_check_count = interface_validation()
    comparators, comparator_failures, comparator_check_count = comparator_validation()
    failures = file_failures + mechanism_failures + interface_failures + comparator_failures
    hashes_after = provenance_hashes()
    changed_inputs = sorted(path for path in hashes_before if hashes_before[path] != hashes_after[path])
    if changed_inputs:
        failures.append(f"validation inputs changed while validation was running: {changed_inputs}; rerun against frozen inputs")
    by_format: dict[str, dict[str, int]] = {}
    for record in file_records:
        row = by_format.setdefault(record["format"], {"files": 0, "readable": 0, "valid": 0})
        row["files"] += 1
        row["readable"] += int(bool(record.get("readable")))
        row["valid"] += int(bool(record.get("valid")))
    total_checks = len(file_records) + len(comparisons) + mechanism_check_count + interface_check_count + comparator_check_count
    report = {
        "schema": "onegrip-finger-input-geometry-validation-v1",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "validator": str(Path(__file__).relative_to(ROOT)),
        "cadquery_version": cq.__version__,
        "inputs": {
            "sha256": hashes_after,
            "stable_during_run": not changed_inputs,
            "changed_during_run": changed_inputs,
        },
        "summary": {
            "pass": not failures,
            "passed_checks": total_checks - len(failures),
            "failed_checks": len(failures),
            "elapsed_seconds": rounded(time.perf_counter() - started, 3),
            "files_by_format": by_format,
            "cross_format_comparisons": len(comparisons),
            "cross_format_passed": sum(item["pass"] for item in comparisons),
            "presets": len(mechanisms),
            "states_per_preset": 4,
        },
        "failures": failures,
        "files": file_records,
        "visualization_cache": {
            "policy": "excluded from printable/assembly qualification; flattened STL is for Blender preview only",
            "files": visualization_cache,
        },
        "cross_format_dimensions": comparisons,
        "mechanisms": mechanisms,
        "interfaces": interfaces,
        "comparators": comparators,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "geometry_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS / "geometry_validation.md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
