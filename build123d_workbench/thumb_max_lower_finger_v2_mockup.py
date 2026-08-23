"""Clean exterior V4: max-lowered original thumb + latest Finger V2.

The earlier visual mockup used the old lower-15 STL housing as a background.
That mesh predated the approved Finger V2 booleans and therefore carried old
finger-opening scars.  V4 deliberately retires that source and consumes the
exact Integrated V3 STEP shell halves, whose finger geometry derives from the
immutable clean pre-finger AP242 baseline plus only the approved eight V2
opening cutters.

This remains an exterior-review derivative.  It does not change the approved
button centres or thumb rigid transform and it does not approve the currently
REVISE-status Integrated V3 internal architecture for printing.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from build123d import Location, Vector, export_stl, import_step
from PIL import Image, ImageDraw

from .finger_controls_v2 import BUTTON_ORDER
from .finger_layout_reset import THUMB_STEP, triangles
from .render_finger_controls_v2 import (
    CAP,
    SHELL_A,
    SHELL_B,
    THUMB_TARGET,
    label_centers,
    load_controls,
    rot_z,
    rotate_objects,
    translated,
)


ROOT = Path(__file__).resolve().parents[1]
FINGER_DIR = ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
INTEGRATED_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_integrated_v3"
OUT_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_exterior_clean_v4"
RENDER_DIR = ROOT / "renders" / "finger_thumb_exterior_clean_v4"

SHELL_JAD_STEP = INTEGRATED_DIR / "JAD_FINGER_THUMB_INTEGRATED_V3.step"
SHELL_JFD_STEP = INTEGRATED_DIR / "JFD_FINGER_THUMB_INTEGRATED_V3.step"
CLEAN_BASELINE_MANIFEST = ROOT / "local_cad" / "reference" / "clean_pre_finger_baseline_manifest.json"
VISUAL_STL = OUT_DIR / "FINGER_THUMB_CLEAN_EXTERIOR_V4_VISUAL_MOCKUP.stl"
CLEAN_JAD_STL = OUT_DIR / "JAD_FINGER_THUMB_CLEAN_EXTERIOR_V4.stl"
CLEAN_JFD_STL = OUT_DIR / "JFD_FINGER_THUMB_CLEAN_EXTERIOR_V4.stl"
MANIFEST = OUT_DIR / "finger_thumb_exterior_clean_v4.json"

# Stage-D was already -6 mm; the accepted later housing seed moved a further
# -15 mm and +6.75 mm Y.  Total relative to the historical Start thumb is:
THUMB_TOTAL_TRANSLATION = np.asarray((0.0, 12.25, -21.0), dtype=float)

sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import write_binary_stl  # noqa: E402
from validate_thumb_housing_stl import analyze as analyze_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402


CONTROL_THUMB = (235, 103, 61)
CONTROL_FINGER = (54, 211, 139)
SHELL_GHOST = (78, 129, 158)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def intersection_volume(a, b) -> float:
    try:
        common = a & b
        return float(sum(solid.volume for solid in common.solids()))
    except Exception:
        return 0.0


def annotate(image: Image.Image, title: str, subtitle: str, legend=()) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle(
        (28, 22, 1260, 112), radius=14,
        fill=(7, 12, 19, 228), outline=(80, 105, 120, 220), width=2,
    )
    draw.text((48, 34), title, font=render.font(34, True), fill=(244, 248, 250, 255))
    draw.text((50, 79), subtitle, font=render.font(18), fill=(181, 199, 210, 255))
    if legend:
        x = 45
        y = render.HEIGHT - 82
        draw.rounded_rectangle(
            (28, render.HEIGHT - 105, render.WIDTH - 28, render.HEIGHT - 30),
            radius=14, fill=(7, 12, 19, 224), outline=(70, 94, 110, 220), width=2,
        )
        for label, color in legend:
            draw.ellipse((x, y, x + 18, y + 18), fill=(*color, 255))
            draw.text((x + 27, y - 5), label, font=render.font(16), fill=(228, 236, 241, 255))
            x += max(230, len(label) * 9 + 62)


def save_scene(filename: str, objects, title: str, subtitle: str, legend, matrix):
    work = rotate_objects(objects, matrix)
    image, projection = render.rasterize(work)
    annotate(image, title, subtitle, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / filename
    image.convert("RGB").save(path, quality=96)
    return image, projection, path


def wire_shell(image: Image.Image, projection, shell_meshes, matrix) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    for mesh in shell_meshes:
        work = mesh @ matrix.T
        stride = max(1, len(work) // 520)
        for triangle in work[::stride]:
            points = render.project(triangle, projection)
            draw.line(
                [tuple(points[0]), tuple(points[1]), tuple(points[2]), tuple(points[0])],
                fill=(*SHELL_GHOST, 55), width=1,
            )


def make_contact_sheet(paths: list[Path]) -> Path:
    cells = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        image.thumbnail((585, 439), Image.Resampling.LANCZOS)
        cells.append((path.name, image.copy()))
    sheet = Image.new("RGB", (1220, 525 * math.ceil(len(cells) / 2) + 80), (10, 16, 24))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (28, 18), "CLEAN EXTERIOR V4 / MAX-LOWER THUMB + LATEST FINGER V2",
        font=render.font(28, True), fill=(242, 247, 250),
    )
    for index, (name, image) in enumerate(cells):
        x = 15 + (index % 2) * 605
        y = 72 + (index // 2) * 525
        sheet.paste(image, (x, y))
        draw.text((x + 8, y + 452), name, font=render.font(16), fill=(205, 218, 226))
    result = RENDER_DIR / "00_contact_sheet.png"
    sheet.save(result, quality=96)
    return result


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    controls, _depths = load_controls()

    shell_shapes = [import_step(SHELL_JAD_STEP), import_step(SHELL_JFD_STEP)]
    shell_meshes = [triangles(shape) for shape in shell_shapes]
    export_stl(shell_shapes[0], CLEAN_JAD_STL)
    export_stl(shell_shapes[1], CLEAN_JFD_STL)
    shell_mesh_validation = [analyze_stl(CLEAN_JAD_STL), analyze_stl(CLEAN_JFD_STL)]

    thumb_source = import_step(THUMB_STEP)
    thumb_solids = [solid for solid in thumb_source.solids() if solid.bounding_box().max.X < 50.0]
    moved_thumb_solids = [
        solid.moved(Location(Vector(*THUMB_TOTAL_TRANSLATION))) for solid in thumb_solids
    ]
    moved_thumb_meshes = [translated(triangles(solid), THUMB_TOTAL_TRANSLATION) for solid in thumb_solids]

    cap_shapes = {name: import_step(FINGER_DIR / f"{name}_cap.step") for name in BUTTON_ORDER}
    cap_meshes = {name: triangles(shape) for name, shape in cap_shapes.items()}

    collisions = {}
    for name, cap in cap_shapes.items():
        rows = [intersection_volume(cap, thumb) for thumb in moved_thumb_solids]
        collisions[name] = {
            "maximumThumbComponentIntersectionMm3": max(rows, default=0.0),
            "totalThumbComponentIntersectionMm3": sum(rows),
            "intersectingThumbComponentCount": sum(volume > 1e-7 for volume in rows),
        }

    all_meshes = [*shell_meshes, *moved_thumb_meshes, *cap_meshes.values()]
    visual_mesh = np.concatenate(all_meshes)
    write_binary_stl(VISUAL_STL, visual_mesh, "VISUAL ONLY: clean V4 shell + max-lower thumb + latest Finger V2")

    external = [
        (shell_meshes[0], SHELL_A),
        (shell_meshes[1], SHELL_B),
        *[(mesh, CONTROL_THUMB) for mesh in moved_thumb_meshes],
        *[(mesh, CONTROL_FINGER) for mesh in cap_meshes.values()],
    ]
    controls_only = [
        *[(mesh, CONTROL_THUMB) for mesh in moved_thumb_meshes],
        *[(mesh, CONTROL_FINGER) for mesh in cap_meshes.values()],
    ]
    thumb_side = np.eye(3)
    rear = rot_z(140.0)
    oblique = rot_z(72.0)
    legend = (
        ("max-lowered original thumb cluster", CONTROL_THUMB),
        ("latest Finger V2 caps", CONTROL_FINGER),
        ("clean V4 shell / legacy holes removed", SHELL_B),
    )
    paths = []

    _image, _projection, path = save_scene(
        "01_thumb_control_side.png", external,
        "CLEAN EXTERIOR V4 / THUMB SIDE",
        "LATEST 8-BUTTON SHELL / LEGACY FINGER HOLE SOURCE REMOVED / THUMB DELTA (0,+12.25,-21.00) mm",
        legend, thumb_side,
    )
    paths.append(path)

    image, projection, path = save_scene(
        "02_finger_control_side.png", external,
        "CLEAN EXTERIOR V4 / FINGER SIDE",
        "ONLY APPROVED I2 I3 I4 M3 M4 N1 N2 N3 OPENINGS / LEGACY FINGER SCARS REMOVED",
        legend, rear,
    )
    label_centers(image, projection, controls, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    image, projection, path = save_scene(
        "03_finger_layout_wireframe.png", controls_only,
        "CLEAN V4 CONTROL LAYOUT / SHELL WIREFRAME",
        "ORANGE = MAX-LOWER THUMB / GREEN = APPROVED I2 I3 I4 M3 M4 N1 N2 N3",
        legend, rear,
    )
    wire_shell(image, projection, shell_meshes, rear)
    label_centers(image, projection, controls, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    image, projection, path = save_scene(
        "04_side_oblique.png", external,
        "CLEAN EXTERIOR V4 / OBLIQUE",
        "CLEAN INTEGRATED STEP SHELLS / EXTERIOR REVIEW ONLY / INTERNAL V3 REMAINS REVISE",
        legend, oblique,
    )
    paths.append(path)

    contact = make_contact_sheet(paths)

    cross_count = sum(row["intersectingThumbComponentCount"] > 0 for row in collisions.values())
    manifest = {
        "schema": 2,
        "mode": "LOCAL build123d/OCCT clean exterior derivative; Onshape 0; production CAD write 0",
        "scope": "clean exterior V4 / legacy finger-hole source removal",
        "thumbTotalTranslationFromOriginalMm": THUMB_TOTAL_TRANSLATION.tolist(),
        "latestFingerButtons": list(BUTTON_ORDER),
        "sources": {
            "integratedV3JaD": {"path": str(SHELL_JAD_STEP.relative_to(ROOT)), "sha256": sha256(SHELL_JAD_STEP)},
            "integratedV3JfD": {"path": str(SHELL_JFD_STEP.relative_to(ROOT)), "sha256": sha256(SHELL_JFD_STEP)},
            "originalThumb": {"path": str(THUMB_STEP.relative_to(ROOT)), "sha256": sha256(THUMB_STEP)},
            "cleanPreFingerBaselineManifest": {
                "path": str(CLEAN_BASELINE_MANIFEST.relative_to(ROOT)),
                "sha256": sha256(CLEAN_BASELINE_MANIFEST),
            },
            "fingerV2Manifest": {
                "path": str((FINGER_DIR / "finger_controls_v2_source_manifest.json").relative_to(ROOT)),
                "sha256": sha256(FINGER_DIR / "finger_controls_v2_source_manifest.json"),
            },
        },
        "visualMesh": {
            "path": str(VISUAL_STL.relative_to(ROOT)),
            "triangleCount": int(len(visual_mesh)),
            "declaredComponentCount": 2 + len(moved_thumb_meshes) + len(cap_meshes),
            "finite": bool(np.isfinite(visual_mesh).all()),
            "purpose": "viewer/reference only; do not slice as one validated assembly",
        },
        "cleanShellExports": {
            "JaDSourceStep": str(SHELL_JAD_STEP.relative_to(ROOT)),
            "JfDSourceStep": str(SHELL_JFD_STEP.relative_to(ROOT)),
            "JaDStl": str(CLEAN_JAD_STL.relative_to(ROOT)),
            "JfDStl": str(CLEAN_JFD_STL.relative_to(ROOT)),
            "solidCount": [len(shell_shapes[0].solids()), len(shell_shapes[1].solids())],
            "valid": [bool(shell_shapes[0].is_valid), bool(shell_shapes[1].is_valid)],
            "meshValidation": shell_mesh_validation,
        },
        "fingerOpeningProvenance": {
            "cleanBaselineHasFingerOpenings": False,
            "approvedCurrentOpenings": list(BUTTON_ORDER),
            "approvedCurrentOpeningCount": len(BUTTON_ORDER),
            "legacyLower15ShellGeometryUsed": False,
            "legacyFingerHoleSourceCount": 0,
        },
        "thumbToLatestFingerCapIntersection": collisions,
        "latestFingerCapsWithAnyExactThumbIntersection": cross_count,
        "renders": [str(path.relative_to(ROOT)) for path in [contact, *paths]],
        "verdict": {
            "CLEAN_EXTERIOR_V4": "GENERATED",
            "LATEST_FINGER_V2_LAYOUT": "PRESERVED",
            "MAX_LOWER_THUMB_POSITION": "APPLIED",
            "LEGACY_LOWER15_FINGER_HOLE_SOURCE": "REMOVED",
            "LEGACY_FINGER_OPENING_SCARS": "ABSENT_BY_SOURCE_CHAIN",
            "INTEGRATED_V3_INTERNAL_ARCHITECTURE": "REVISE / NOT PRINT APPROVED",
        },
        "warning": (
            "This derivative fixes the exterior source mismatch only. The clean shell STL files "
            "retain the Integrated V3 internal geometry, whose internal-design review is REVISE. "
            "Do not treat these files as production-print approval."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "contactSheet": str(contact),
        "visualSTL": str(VISUAL_STL),
        "cleanShellSTL": [str(CLEAN_JAD_STL), str(CLEAN_JFD_STL)],
        "manifest": str(MANIFEST),
        "fingerCapsWithThumbIntersection": cross_count,
        "verdict": manifest["verdict"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
