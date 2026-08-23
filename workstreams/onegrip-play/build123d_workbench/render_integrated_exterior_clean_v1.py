"""Render the FINAL EXTERIOR CLEAN V1 validation/HOLD set."""

from __future__ import annotations

import math
from pathlib import Path
import sys

import numpy as np
from build123d import import_step
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_Orientation
from OCP.TopLoc import TopLoc_Location
from PIL import Image, ImageDraw

from .finger_controls_v2 import BUTTON_ORDER
from .finger_layout_reset import TESSELLATION_ANGLE, TESSELLATION_TOLERANCE
from .integrated_exterior_clean_v1 import (
    JAD_OUTPUT,
    JFD_OUTPUT,
    JAD_SOURCE,
    JFD_SOURCE,
    THUMB_TARGET_SOURCE,
)
from .render_finger_controls_v2 import rot_z


ROOT = Path(__file__).resolve().parents[1]
RENDER_DIR = ROOT / "renders" / "integrated_exterior_clean_v1"
FINGER_DIR = ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
V3_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_integrated_v3"
ORIGINAL_THUMB = ROOT / "local_cad" / "reference" / "THUMB_ORIGINAL_PRE_FINGER_REFERENCE.step"

sys.path.insert(0, str(ROOT / "scripts"))
import render_index_its_audit as render  # noqa: E402


SHELL_A = (50, 89, 111)
SHELL_B = (59, 101, 124)
CAP = (50, 207, 136)
THUMB = (238, 143, 45)
OLD = (225, 71, 132)
V3_REMOVED = (220, 76, 68)
TEXT = (239, 244, 247)
MUTED = (174, 194, 205)


def safe_triangles(shape) -> np.ndarray:
    """Tessellate while skipping zero-area internal faces with no OCCT mesh."""
    shape.mesh(TESSELLATION_TOLERANCE, TESSELLATION_ANGLE)
    rows = []
    for face in shape.faces():
        location = TopLoc_Location()
        poly = BRep_Tool.Triangulation_s(face.wrapped, location)
        if poly is None:
            continue
        transform = location.Transformation()
        points = [poly.Node(i).Transformed(transform) for i in range(1, poly.NbNodes() + 1)]
        reverse = face.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
        for triangle in poly.Triangles():
            indices = [triangle.Value(i) - 1 for i in (1, 2, 3)]
            if reverse:
                indices[1], indices[2] = indices[2], indices[1]
            rows.append([[points[index].X(), points[index].Y(), points[index].Z()] for index in indices])
    if not rows:
        raise RuntimeError("shape produced no renderable triangles")
    return np.asarray(rows, dtype=float)


def meshes(path: Path) -> list[tuple[np.ndarray, str]]:
    source = import_step(path)
    if source.children:
        return [(safe_triangles(child.clean()), child.label) for child in source.children]
    return [(safe_triangles(source.clean()), source.label)]


def selected_thumb(path: Path, *, target: bool) -> list[np.ndarray]:
    source = import_step(path)
    rows = []
    for child in source.children:
        allowed = (
            child.label == "Backplate"
            or child.label.startswith("Button_")
            or (target and child.label == "HW504_B")
            or (target and child.label == "Small_joystick_attachment")
        )
        if not allowed:
            continue
        if not target and child.bounding_box().max.X > 50.0:
            continue
        rows.append(safe_triangles(child))
    return rows


def rotate(objects, matrix):
    return [(mesh @ matrix.T, color) for mesh, color in objects]


def annotate(image: Image.Image, title: str, subtitle: str, legend=()) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle(
        (28, 22, 1265, 112), radius=14,
        fill=(7, 12, 19, 230), outline=(77, 102, 118, 230), width=2,
    )
    draw.text((48, 34), title, font=render.font(34, True), fill=(*TEXT, 255))
    draw.text((50, 79), subtitle, font=render.font(17), fill=(*MUTED, 255))
    if legend:
        draw.rounded_rectangle(
            (28, render.HEIGHT - 104, render.WIDTH - 28, render.HEIGHT - 30),
            radius=14, fill=(7, 12, 19, 226), outline=(67, 91, 107, 220), width=2,
        )
        x = 45
        for label, color in legend:
            draw.ellipse((x, render.HEIGHT - 81, x + 18, render.HEIGHT - 63), fill=(*color, 255))
            draw.text((x + 27, render.HEIGHT - 86), label, font=render.font(15), fill=(224, 233, 238, 255))
            x += max(225, 55 + len(label) * 8)


def raw_scene(objects, matrix):
    return render.rasterize(rotate(objects, matrix))


def save_scene(name: str, objects, matrix, title: str, subtitle: str, legend=()) -> Path:
    image, _projection = raw_scene(objects, matrix)
    annotate(image, title, subtitle, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / name
    image.convert("RGB").save(path, quality=96)
    return path


def crop_scene(name: str, objects, matrix, focus_meshes, title: str, subtitle: str, legend=()) -> Path:
    image, projection = raw_scene(objects, matrix)
    focus = np.concatenate([mesh @ matrix.T for mesh in focus_meshes]).reshape(-1, 3)
    projected = render.project(focus, projection)
    x0, y0 = projected.min(axis=0)
    x1, y1 = projected.max(axis=0)
    pad_x = max(90.0, 0.35 * (x1 - x0))
    pad_y = max(90.0, 0.40 * (y1 - y0))
    box = (
        max(0, int(x0 - pad_x)), max(0, int(y0 - pad_y)),
        min(render.WIDTH, int(x1 + pad_x)), min(render.HEIGHT, int(y1 + pad_y)),
    )
    cropped = image.crop(box).resize((render.WIDTH, render.HEIGHT), Image.Resampling.LANCZOS)
    annotate(cropped, title, subtitle, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / name
    cropped.convert("RGB").save(path, quality=96)
    return path


def side_by_side(name: str, left_objects, right_objects, matrix, title: str, subtitle: str) -> Path:
    left, _ = raw_scene(left_objects, matrix)
    right, _ = raw_scene(right_objects, matrix)
    left.thumbnail((720, 540), Image.Resampling.LANCZOS)
    right.thumbnail((720, 540), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (render.WIDTH, render.HEIGHT), (9, 15, 23))
    canvas.paste(left.convert("RGB"), (18, 220))
    canvas.paste(right.convert("RGB"), (762, 220))
    draw = ImageDraw.Draw(canvas)
    draw.text((245, 770), "BEFORE / original Thumb openings", font=render.font(18, True), fill=(*OLD, 255))
    draw.text((930, 770), "CLEAN V1 HOLD / lowered openings missing", font=render.font(18, True), fill=(231, 186, 80))
    annotate(canvas, title, subtitle, (("old position", OLD), ("clean shell", SHELL_B), ("approved Finger", CAP)))
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / name
    canvas.save(path, quality=96)
    return path


def contact_sheet(paths: list[Path]) -> Path:
    width, cell_w, cell_h = 1500, 465, 395
    rows = math.ceil(len(paths) / 3)
    sheet = Image.new("RGB", (width, 90 + rows * cell_h), (8, 14, 22))
    draw = ImageDraw.Draw(sheet)
    draw.text((28, 18), "FINAL EXTERIOR CLEAN V1 / VISUAL GATE = HOLD", font=render.font(30, True), fill=TEXT)
    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((cell_w - 20, cell_h - 65), Image.Resampling.LANCZOS)
        x = 18 + (index % 3) * 493
        y = 80 + (index // 3) * cell_h
        sheet.paste(image, (x, y))
        draw.text((x + 5, y + cell_h - 55), path.name, font=render.font(14), fill=(205, 219, 227))
    result = RENDER_DIR / "00_contact_sheet.png"
    sheet.save(result, quality=96)
    return result


def main() -> None:
    clean_shells = [meshes(JAD_OUTPUT)[0][0], meshes(JFD_OUTPUT)[0][0]]
    source_shells = [meshes(JAD_SOURCE)[0][0], meshes(JFD_SOURCE)[0][0]]
    v3_shells = [
        meshes(V3_DIR / "JAD_FINGER_THUMB_INTEGRATED_V3.step")[0][0],
        meshes(V3_DIR / "JFD_FINGER_THUMB_INTEGRATED_V3.step")[0][0],
    ]
    finger_caps = [meshes(FINGER_DIR / f"{name}_cap.step")[0][0] for name in BUTTON_ORDER]
    target_thumb = selected_thumb(THUMB_TARGET_SOURCE, target=True)
    original_thumb = selected_thumb(ORIGINAL_THUMB, target=False)

    clean = [
        (clean_shells[0], SHELL_A), (clean_shells[1], SHELL_B),
        *[(mesh, CAP) for mesh in finger_caps],
        *[(mesh, THUMB) for mesh in target_thumb],
    ]
    original = [
        (source_shells[0], SHELL_A), (source_shells[1], SHELL_B),
        *[(mesh, OLD) for mesh in original_thumb],
    ]
    rear = rot_z(140.0)
    front = rot_z(-40.0)
    left = rot_z(90.0)
    right = rot_z(-90.0)
    left_oblique = rot_z(65.0)
    right_oblique = rot_z(-65.0)
    legend = (("clean shell", SHELL_B), ("approved Finger 8", CAP), ("lowered Thumb target", THUMB))

    paths = [
        save_scene("01_front_clean_exterior.png", clean, front, "FRONT / CLEAN EXTERIOR V1", "EXTERIOR-ONLY REBUILD / LOWERED THUMB OPENING GATE = HOLD", legend),
        save_scene("02_rear_clean_exterior.png", clean, rear, "REAR / CLEAN EXTERIOR V1", "LATEST I2 I3 I4 M3 M4 N1 N2 N3 PRESERVED", legend),
        save_scene("03_left_clean_exterior.png", clean, left, "LEFT / CLEAN EXTERIOR V1", "NO V3 BOSS / TUBE / EXTERNAL FASTENING IMPORTED", legend),
        save_scene("04_right_clean_exterior.png", clean, right, "RIGHT / CLEAN EXTERIOR V1", "BASE SILHOUETTE FROM IMMUTABLE CLEAN SHELL", legend),
        save_scene("05_left_oblique.png", clean, left_oblique, "LEFT OBLIQUE / CLEAN EXTERIOR V1", "OLD THUMB OPENINGS RESTORED WITH EXACT SURFACE EXTENSION", legend),
        save_scene("06_right_oblique.png", clean, right_oblique, "RIGHT OBLIQUE / CLEAN EXTERIOR V1", "FINAL BASELINE HELD UNTIL EXACT LOWERED OPENING STEP IS AVAILABLE", legend),
        crop_scene("07_thumb_region_closeup.png", clean, np.eye(3), target_thumb, "THUMB REGION / HOLD", "OLD OPENINGS GONE / TARGET CONTROLS SHOWN / EXACT LOWERED OPENINGS NOT CUT", legend),
        crop_scene("08_finger_region_closeup.png", clean, rear, finger_caps, "FINGER REGION / PASS", "ONLY APPROVED 8 OPENINGS AND CAPS / LEGACY I1 M1 M2 ABSENT", legend),
        side_by_side("09_before_after_exterior.png", original, clean, np.eye(3), "BEFORE / AFTER EXTERIOR", "EXACT OLD-THUMB RESTORATION PASS / LOWERED-THUMB OPENING CREATION HOLD"),
        save_scene(
            "10_removed_legacy_features.png",
            [(clean_shells[0], SHELL_A), (clean_shells[1], SHELL_B), *[(mesh, V3_REMOVED) for mesh in v3_shells]],
            left_oblique,
            "REMOVED LEGACY / V3 EXTERIOR FEATURES",
            "RED GHOST = V3 SHELL ONLY / CLEAN OUTPUT IMPORTS ZERO V3 FASTENING GEOMETRY",
            (("clean output", SHELL_B), ("discarded V3 ghost", V3_REMOVED)),
        ),
    ]
    sheet = contact_sheet(paths)
    print({"renders": [str(path) for path in paths], "contactSheet": str(sheet)})


if __name__ == "__main__":
    main()
