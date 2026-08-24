"""Read-only validation for immutable Onshape LOWER15 STEP exports.

No healing, cleaning, booleans, transforms, or geometry exports are performed.
The STEP solids are imported as-is, tessellated in memory, and sampled along
the already-audited frozen Thumb control axes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from build123d import import_step
from scipy import ndimage


OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
REV_C_SCRIPTS = ROOT / "thumb_inner_housing_lab" / "REV_C" / "10_scripts"
sys.path.insert(0, str(REV_C_SCRIPTS))

import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import true_axis  # noqa: E402
from c01_approved_openings import RayGrid, axis_frame, scan  # noqa: E402


FILES = {
    "JaD_STEP": OUT / "JaD_THUMB_LOWER15_APPROVED.step",
    "JfD_STEP": OUT / "JfD_THUMB_LOWER15_APPROVED.step",
    "JaD_PARASOLID": OUT / "JaD_THUMB_LOWER15_APPROVED.x_t",
    "JfD_PARASOLID": OUT / "JfD_THUMB_LOWER15_APPROVED.x_t",
}
PATCH = 11.0
PITCH = 0.15
BAND = (-8.0, 26.0)
OPEN_EPS_MM = 0.05


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def shape_stats(path: Path):
    shape = import_step(path)
    solids = list(shape.solids())
    box = shape.bounding_box()
    return shape, {
        "importSucceeded": True,
        "isValid": bool(shape.is_valid),
        "solidCount": len(solids),
        "faceCount": len(list(shape.faces())),
        "edgeCount": len(list(shape.edges())),
        "vertexCount": len(list(shape.vertices())),
        "volumeMm3": float(shape.volume),
        "boundingBoxMm": {
            "min": [float(box.min.X), float(box.min.Y), float(box.min.Z)],
            "max": [float(box.max.X), float(box.max.Y), float(box.max.Z)],
            "size": [float(box.size.X), float(box.size.Y), float(box.size.Z)],
        },
    }


def opening_validation(shell_triangles: np.ndarray) -> dict:
    _, cartridge = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    x_axis = np.arange(-PATCH, PATCH + 1.0e-9, PITCH)
    y_axis = np.arange(-PATCH, PATCH + 1.0e-9, PITCH)
    cell_area = PITCH * PITCH
    rows = {}

    for short in ORDER:
        label = next(label for label, mapped in NAME_MAP.items() if mapped == short)
        cap, _ = L.as_single_solid(cartridge[label], short)
        press_axis, _, _ = true_axis(cap)
        points = L.surf_points(cap, 25000, tol=0.05)
        center = points.mean(axis=0)
        ex, ey = axis_frame(press_axis)

        grid = RayGrid(shell_triangles, center, press_axis, ex, ey)
        thickness, _, _, mapped = scan(grid, x_axis, y_axis, BAND)
        open_mask = mapped & (thickness < OPEN_EPS_MM)
        labels, count = ndimage.label(open_mask)
        ix = int(np.argmin(np.abs(x_axis)))
        iy = int(np.argmin(np.abs(y_axis)))
        component_id = int(labels[ix, iy])
        axis_column_open = component_id != 0
        if component_id == 0 and count:
            sizes = ndimage.sum(open_mask, labels, range(1, count + 1))
            component_id = int(np.argmax(sizes)) + 1
        component = labels == component_id if component_id else np.zeros_like(open_mask)
        area = float(component.sum()) * cell_area
        ui, vi = np.nonzero(component)
        centroid = [float(x_axis[ui].mean()), float(y_axis[vi].mean())] if ui.size else [None, None]
        centroid_norm = float(np.linalg.norm(centroid)) if ui.size else None
        eroded = ndimage.binary_erosion(component, np.ones((3, 3), bool))
        boundary_points = int((component & ~eroded).sum())
        passed = bool(
            axis_column_open
            and area > 20.0
            and centroid_norm is not None
            and centroid_norm < 2.5
            and boundary_points > 0
        )
        rows[short] = {
            "throughOpeningExists": passed,
            "axisColumnOpen": axis_column_open,
            "sampledOpenAreaMm2": area,
            "sampledCentroidLocalXYmm": centroid,
            "sampledCentroidOffsetMm": centroid_norm,
            "boundaryPointCount": boundary_points,
            "rayPitchMm": PITCH,
            "wallBandAlongAxisMm": list(BAND),
        }
    return rows


def main() -> None:
    missing = [str(path) for path in FILES.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing exports: " + ", ".join(missing))

    jad, jad_stats = shape_stats(FILES["JaD_STEP"])
    jfd, jfd_stats = shape_stats(FILES["JfD_STEP"])
    triangles = np.concatenate((
        L.triangles(jad, tol=0.05, ang=0.10),
        L.triangles(jfd, tol=0.05, ang=0.10),
    ))
    openings = opening_validation(triangles)

    files = {
        key: {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for key, path in FILES.items()
    }
    result = {
        "mode": "READ_ONLY_NO_HEAL_NO_GEOMETRY_MODIFICATION",
        "source": {
            "documentId": "a21e64f36bc61df760d4587c",
            "versionId": "50dfe4e752e447375b95493a",
            "elementId": "425d9199b59cfb1efd9ddc35",
            "configuration": "default",
        },
        "files": files,
        "stepValidation": {
            "JaD": jad_stats,
            "JfD": jfd_stats,
            "separateValidSolids": bool(
                jad_stats["isValid"]
                and jfd_stats["isValid"]
                and jad_stats["solidCount"] == 1
                and jfd_stats["solidCount"] == 1
            ),
        },
        "openings": openings,
        "allNineThroughOpeningsPass": all(row["throughOpeningExists"] for row in openings.values()),
    }
    path = OUT / "EXPORT_VALIDATION.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
