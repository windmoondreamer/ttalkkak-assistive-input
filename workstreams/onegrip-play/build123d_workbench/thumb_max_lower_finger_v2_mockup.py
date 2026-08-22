"""External placement mockup: max-lowered original thumb + latest Finger V2.

This is intentionally a multi-body visual study.  It does not claim that the
lower-15 housing contains the latest Finger V2 openings or internals.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from build123d import Location, Vector, import_step
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
LOWER_DIR = ROOT / "exports" / "thumb_lower15_housing_mockup"
OUT_DIR = ROOT / "build123d_workbench" / "out" / "thumb_max_lower_finger_v2_mockup"
RENDER_DIR = OUT_DIR / "renders"

LOWER_JAD = LOWER_DIR / "OneGrip_lower15_housing_Joystick_1_JaD.stl"
LOWER_JFD = LOWER_DIR / "OneGrip_lower15_housing_Joystick_2_JfD.stl"
VISUAL_STL = OUT_DIR / "THUMB_MAX_LOWER_PLUS_FINGER_V2_VISUAL_MOCKUP.stl"
MANIFEST = OUT_DIR / "thumb_max_lower_finger_v2_mockup.json"

# Stage-D was already -6 mm; the accepted later housing seed moved a further
# -15 mm and +6.75 mm Y.  Total relative to the historical Start thumb is:
THUMB_TOTAL_TRANSLATION = np.asarray((0.0, 12.25, -21.0), dtype=float)

sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import read_binary_stl, write_binary_stl  # noqa: E402
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
        (28, 18), "MAX-LOWER THUMB + LATEST FINGER V2 / EXTERNAL MOCKUP",
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

    lower_shells = [read_binary_stl(LOWER_JAD), read_binary_stl(LOWER_JFD)]
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

    all_meshes = [*lower_shells, *moved_thumb_meshes, *cap_meshes.values()]
    visual_mesh = np.concatenate(all_meshes)
    write_binary_stl(VISUAL_STL, visual_mesh, "VISUAL ONLY: max-lower thumb + latest Finger V2")

    external = [
        (lower_shells[0], SHELL_A),
        (lower_shells[1], SHELL_B),
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
        ("lower-15 housing source", SHELL_B),
    )
    paths = []

    _image, _projection, path = save_scene(
        "01_thumb_control_side.png", external,
        "MAX-LOWER THUMB + LATEST FINGER V2 / THUMB SIDE",
        "ORIGINAL THUMB CLUSTER RIGIDLY LOWERED / TOTAL DELTA (0,+12.25,-21.00) mm",
        legend, thumb_side,
    )
    paths.append(path)

    image, projection, path = save_scene(
        "02_finger_control_side.png", external,
        "MAX-LOWER THUMB + LATEST FINGER V2 / FINGER SIDE",
        "EXTERNAL POSITION MOCKUP / THUMB DELTA (0,+12.25,-21.00) mm / INTERNALS NOT VALIDATED",
        legend, rear,
    )
    label_centers(image, projection, controls, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    image, projection, path = save_scene(
        "03_finger_layout_wireframe.png", controls_only,
        "CONTROL LAYOUT / SHELL WIREFRAME",
        "ORANGE = MAX-LOWER THUMB / GREEN = LATEST I2 I3 I4 M3 M4 N1 N2 N3",
        legend, rear,
    )
    wire_shell(image, projection, lower_shells, rear)
    label_centers(image, projection, controls, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    image, projection, path = save_scene(
        "04_side_oblique.png", external,
        "MAX-LOWER THUMB + LATEST FINGER V2 / OBLIQUE",
        "MULTI-BODY VISUAL STUDY / NOT A PRINTABLE MERGED SHELL",
        legend, oblique,
    )
    paths.append(path)

    contact = make_contact_sheet(paths)

    cross_count = sum(row["intersectingThumbComponentCount"] > 0 for row in collisions.values())
    manifest = {
        "schema": 1,
        "mode": "LOCAL build123d/mesh render only; Onshape 0; production CAD write 0",
        "scope": "external multi-body placement mockup",
        "thumbTotalTranslationFromOriginalMm": THUMB_TOTAL_TRANSLATION.tolist(),
        "latestFingerButtons": list(BUTTON_ORDER),
        "sources": {
            "lower15JaD": {"path": str(LOWER_JAD.relative_to(ROOT)), "sha256": sha256(LOWER_JAD)},
            "lower15JfD": {"path": str(LOWER_JFD.relative_to(ROOT)), "sha256": sha256(LOWER_JFD)},
            "originalThumb": {"path": str(THUMB_STEP.relative_to(ROOT)), "sha256": sha256(THUMB_STEP)},
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
        "thumbToLatestFingerCapIntersection": collisions,
        "latestFingerCapsWithAnyExactThumbIntersection": cross_count,
        "renders": [str(path.relative_to(ROOT)) for path in [contact, *paths]],
        "verdict": {
            "EXTERNAL_POSITION_MOCKUP": "GENERATED",
            "LATEST_FINGER_V2_LAYOUT": "PRESERVED",
            "MAX_LOWER_THUMB_POSITION": "APPLIED",
            "INTERNAL_COMPATIBILITY": "NOT VALIDATED",
            "PRINTABLE_MERGED_SHELL": "NOT PROVIDED",
        },
        "warning": (
            "The lower-15 shell source predates the latest Finger V2 shell booleans. "
            "The visual STL intentionally combines independent source bodies and is not production CAD."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "contactSheet": str(contact),
        "visualSTL": str(VISUAL_STL),
        "manifest": str(MANIFEST),
        "fingerCapsWithThumbIntersection": cross_count,
        "verdict": manifest["verdict"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
