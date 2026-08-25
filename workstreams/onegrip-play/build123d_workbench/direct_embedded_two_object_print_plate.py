"""Package final direct-embedded JaD/JfD as two independent plate objects."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import lib3mf

from .print_ready_frozen_exterior_recovery import (
    expanded_fit, read_stl, stl_metrics, write_binary_stl,
)
from .six_failed_leg_shell_landing_failure_mode_diagnostic_audit import (
    raster_scene_without_header,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build123d_workbench/out/direct_embedded_finger_switch_final_candidate"
RENDER = ROOT / "renders/direct_embedded_finger_switch_final_candidate"
SOURCE = {
    "JaD": OUT / "ONEGRIP_DIRECT_EMBEDDED_JaD.stl",
    "JfD": OUT / "ONEGRIP_DIRECT_EMBEDDED_JfD.stl",
}
ORIENTED = {
    "JaD": OUT / "ONEGRIP_DIRECT_EMBEDDED_JaD_PLATE_ORIENTED.stl",
    "JfD": OUT / "ONEGRIP_DIRECT_EMBEDDED_JfD_PLATE_ORIENTED.stl",
}
THREEMF = OUT / "ONEGRIP_DIRECT_EMBEDDED_JaD_JfD_TWO_OBJECT_PLATE.3mf"
MANIFEST = OUT / "two_object_print_plate_manifest.json"
PREVIEW = RENDER / "11_jad_jfd_two_object_print_plate.png"
GAP = 12.0
BED = 256.0
FOOTER = "P1S PLATE | JaD + JfD | 2 INDEPENDENT OBJECTS | GAP 12 mm | NO FUSE"


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def plate_transform(triangles: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], dict[str, list[float]]]:
    transformed = {}
    moves = {}
    for side, mesh in triangles.items():
        points = mesh.reshape(-1, 3)
        lo = points.min(axis=0)
        hi = points.max(axis=0)
        if side == "JfD":
            tx = -GAP / 2.0 - float(hi[0])
        else:
            tx = GAP / 2.0 - float(lo[0])
        ty = -0.5 * float(lo[1] + hi[1])
        tz = -float(lo[2])
        move = np.asarray((tx, ty, tz), float)
        transformed[side] = mesh + move
        moves[side] = move.tolist()
    return transformed, moves


def indexed_mesh(triangles: np.ndarray):
    rounded = np.round(triangles.reshape(-1, 3), 6)
    vertices, inverse = np.unique(rounded, axis=0, return_inverse=True)
    indices = inverse.reshape(-1, 3).astype(np.uint32)
    positions = [lib3mf.Position((tuple(map(float, vertex)))) for vertex in vertices]
    faces = [lib3mf.Triangle((tuple(map(int, face)))) for face in indices]
    return positions, faces, len(vertices), len(indices)


def identity_transform():
    transform = lib3mf.Transform()
    rows = ((1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            (0.0, 0.0, 0.0))
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            transform.Fields[row_index][column_index] = value
    return transform


def write_two_object_3mf(triangles: dict[str, np.ndarray]) -> dict[str, object]:
    wrapper = lib3mf.get_wrapper()
    model = wrapper.CreateModel()
    model.SetUnit(lib3mf.ModelUnit.MilliMeter)
    object_rows = {}
    for side in ("JaD", "JfD"):
        positions, faces, vertex_count, triangle_count = indexed_mesh(triangles[side])
        mesh = model.AddMeshObject()
        mesh.SetName(f"ONEGRIP_DIRECT_EMBEDDED_{side}")
        mesh.SetPartNumber(side)
        mesh.SetGeometry(positions, faces)
        item = model.AddBuildItem(mesh, identity_transform())
        item.SetPartNumber(side)
        object_rows[side] = {
            "objectName": f"ONEGRIP_DIRECT_EMBEDDED_{side}",
            "vertexCount": vertex_count, "triangleCount": triangle_count,
            "manifoldAndOriented": bool(mesh.IsManifoldAndOriented()),
        }
    writer = model.QueryWriter("3mf")
    writer.WriteToFile(str(THREEMF))

    check = wrapper.CreateModel()
    reader = check.QueryReader("3mf")
    reader.ReadFromFile(str(THREEMF))
    mesh_count = int(check.GetMeshObjects().Count())
    build_count = int(check.GetBuildItems().Count())
    return {"meshObjectCount": mesh_count, "buildItemCount": build_count,
            "unit": str(check.GetUnit()), "objects": object_rows,
            "separateObjectsConfirmed": mesh_count == 2 and build_count == 2}


def main() -> None:
    RENDER.mkdir(parents=True, exist_ok=True)
    before = {side: sha256(path) for side, path in SOURCE.items()}
    raw = {side: read_stl(path) for side, path in SOURCE.items()}
    plate, moves = plate_transform(raw)
    for side in ("JaD", "JfD"):
        write_binary_stl(ORIENTED[side], plate[side],
                         f"OneGrip {side} independent two-object plate member")

    three_mf = write_two_object_3mf(plate)
    all_points = np.concatenate([mesh.reshape(-1, 3) for mesh in plate.values()])
    lo = all_points.min(axis=0)
    hi = all_points.max(axis=0)
    dimensions = (hi - lo).tolist()
    bed_fit = float(dimensions[0]) <= BED and float(dimensions[1]) <= BED
    separated = float(plate["JaD"][:, :, 0].min() - plate["JfD"][:, :, 0].max())

    raster_scene_without_header(
        PREVIEW,
        [(plate["JfD"], (61, 188, 139)), (plate["JaD"], (44, 153, 201))],
        "", "", FOOTER, camera_offset=(25.0, -35.0, 245.0),
        fit_points=expanded_fit(all_points, 1.28), transparent_objects=[],
        wireframes=[], world_lines=[], final_size=(1440, 960),
    )

    after = {side: sha256(path) for side, path in SOURCE.items()}
    data = {
        "schema": "onegrip-direct-embedded-two-object-print-plate-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "architecture": {
            "fused": False, "meshObjectCount": three_mf["meshObjectCount"],
            "buildItemCount": three_mf["buildItemCount"],
            "independentObjects": ["JaD", "JfD"], "gapMm": separated,
        },
        "plate": {"bedMm": [BED, BED], "dimensionsMm": dimensions,
                  "bedFit": bed_fit, "minimumZMm": float(lo[2]),
                  "maximumZMm": float(hi[2]), "translationsMm": moves},
        "threeMfValidation": three_mf,
        "stlValidation": {side: stl_metrics(path) for side, path in ORIENTED.items()},
        "preservation": {"sourceBefore": before, "sourceAfter": after,
                         "sourceUnchanged": before == after},
        "outputs": {
            "twoObject3mf": relative(THREEMF),
            "JaDIndependentStl": relative(ORIENTED["JaD"]),
            "JfDIndependentStl": relative(ORIENTED["JfD"]),
            "preview": relative(PREVIEW), "manifest": relative(MANIFEST),
        },
    }
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"separateObjects": three_mf["separateObjectsConfirmed"],
                      "plate": data["plate"], "outputs": data["outputs"],
                      "sourceUnchanged": before == after}, indent=2), flush=True)


if __name__ == "__main__":
    main()
