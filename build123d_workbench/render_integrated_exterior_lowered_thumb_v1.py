"""Render the exterior-first maximum-lowered Thumb mockup."""

from __future__ import annotations

import math
import json
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
from .integrated_exterior_clean_v1 import JAD_OUTPUT as CLEAN_JAD, JFD_OUTPUT as CLEAN_JFD
from .integrated_exterior_lowered_thumb_v1 import (
    EXTERNAL_THUMB_LABELS,
    JAD_OUTPUT,
    JFD_OUTPUT,
    LOWER15_JAD_MESH,
    LOWER15_JFD_MESH,
    OUT_DIR,
    THUMB_TARGET_SOURCE,
)
from .render_finger_controls_v2 import rot_z


ROOT = Path(__file__).resolve().parents[1]
RENDER_DIR = ROOT / "renders" / "integrated_exterior_lowered_thumb_v1"
FINGER_DIR = ROOT / "build123d_workbench" / "out" / "finger_controls_v2"

sys.path.insert(0, str(ROOT / "scripts"))
import render_index_its_audit as render  # noqa: E402
from pack_right_hand_handle_stl import read_binary_stl, write_binary_stl  # noqa: E402


SHELL_A = (50, 89, 111)
SHELL_B = (59, 101, 124)
FINGER = (49, 209, 136)
THUMB = (239, 139, 42)
TEXT = (240, 245, 248)
MUTED = (176, 195, 206)
THUMB_SURFACE_NORMAL = np.asarray((0.00017647, 0.60270162, 0.79796662), dtype=float)
RENDER_CAMERA_DIRECTION = np.asarray((155.0, 185.0, 105.0), dtype=float)
THUMB_PATCH_CENTER = np.asarray((-0.23581763, -4.41709540, 24.99272364), dtype=float)
THUMB_PATCH_U = np.asarray((1.0, 0.0, 0.0), dtype=float)
THUMB_PATCH_V = np.asarray((0.0, 0.79796663, -0.60270163), dtype=float)
THUMB_PATCH_N = THUMB_SURFACE_NORMAL / np.linalg.norm(THUMB_SURFACE_NORMAL)
VISUAL_STL = OUT_DIR / "EXTERIOR_FIRST_LOWERED_THUMB_VISUAL_REFERENCE.stl"
VISUAL_MANIFEST = OUT_DIR / "exterior_first_lowered_thumb_visual_manifest.json"


def align_vector(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Return a rotation matrix that maps source onto target."""
    a = source / np.linalg.norm(source)
    b = target / np.linalg.norm(target)
    cross = np.cross(a, b)
    sine = float(np.linalg.norm(cross))
    cosine = float(np.dot(a, b))
    if sine <= 1.0e-12:
        return np.eye(3) if cosine > 0.0 else rot_z(180.0)
    skew = np.asarray(
        (
            (0.0, -cross[2], cross[1]),
            (cross[2], 0.0, -cross[0]),
            (-cross[1], cross[0], 0.0),
        )
    )
    return np.eye(3) + skew + skew @ skew * ((1.0 - cosine) / (sine * sine))


def safe_triangles(shape) -> np.ndarray:
    shape.mesh(TESSELLATION_TOLERANCE, TESSELLATION_ANGLE)
    rows = []
    for face in shape.faces():
        location = TopLoc_Location()
        poly = BRep_Tool.Triangulation_s(face.wrapped, location)
        if poly is None:
            continue
        transform = location.Transformation()
        points = [
            poly.Node(index).Transformed(transform)
            for index in range(1, poly.NbNodes() + 1)
        ]
        reverse = face.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
        for triangle in poly.Triangles():
            indices = [triangle.Value(index) - 1 for index in (1, 2, 3)]
            if reverse:
                indices[1], indices[2] = indices[2], indices[1]
            rows.append([
                [points[index].X(), points[index].Y(), points[index].Z()]
                for index in indices
            ])
    if not rows:
        raise RuntimeError("shape produced no renderable triangles")
    return np.asarray(rows, dtype=float)


def load_shape(path: Path) -> np.ndarray:
    return safe_triangles(import_step(path).clean())


def load_thumb() -> list[np.ndarray]:
    source = import_step(THUMB_TARGET_SOURCE)
    rows = [
        safe_triangles(child.clean())
        for child in source.children
        if child.label in EXTERNAL_THUMB_LABELS
    ]
    if len(rows) != 9:
        raise RuntimeError("render Thumb exterior inventory mismatch")
    return rows


def thumb_patch_mask(mesh: np.ndarray) -> np.ndarray:
    """Select only the Thumb-facing lower-15 exterior neighborhood.

    The N bound rejects the opposite/rear surface, so historical Finger holes
    in the lower-15 full-shell STL cannot enter the visual composite.
    """
    center = mesh.mean(axis=1)
    relative = center - THUMB_PATCH_CENTER
    u = relative @ THUMB_PATCH_U
    v = relative @ THUMB_PATCH_V
    n = relative @ THUMB_PATCH_N
    return (
        (np.abs(u) <= 23.5)
        & (v >= -34.0)
        & (v <= 28.0)
        & (n >= -8.0)
        & (n <= 40.0)
    )


def graft_lower15_thumb_patch(clean_mesh: np.ndarray, lower15_mesh: np.ndarray) -> tuple[np.ndarray, dict[str, int]]:
    clean_mask = thumb_patch_mask(clean_mesh)
    lower_mask = thumb_patch_mask(lower15_mesh)
    hybrid = np.concatenate((clean_mesh[~clean_mask], lower15_mesh[lower_mask]))
    return hybrid, {
        "cleanTrianglesRemovedInThumbMask": int(clean_mask.sum()),
        "lower15ThumbPatchTrianglesInserted": int(lower_mask.sum()),
        "hybridTriangleCount": int(len(hybrid)),
    }


def rotate(objects, matrix):
    return [(mesh @ matrix.T, color) for mesh, color in objects]


def annotate(image: Image.Image, title: str, subtitle: str, legend=()) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle(
        (28, 22, 1265, 112),
        radius=14,
        fill=(7, 12, 19, 230),
        outline=(77, 102, 118, 230),
        width=2,
    )
    draw.text((48, 34), title, font=render.font(34, True), fill=(*TEXT, 255))
    draw.text((50, 79), subtitle, font=render.font(17), fill=(*MUTED, 255))
    if legend:
        draw.rounded_rectangle(
            (28, render.HEIGHT - 104, render.WIDTH - 28, render.HEIGHT - 30),
            radius=14,
            fill=(7, 12, 19, 226),
            outline=(67, 91, 107, 220),
            width=2,
        )
        x = 45
        for label, color in legend:
            draw.ellipse(
                (x, render.HEIGHT - 81, x + 18, render.HEIGHT - 63),
                fill=(*color, 255),
            )
            draw.text(
                (x + 27, render.HEIGHT - 86),
                label,
                font=render.font(15),
                fill=(224, 233, 238, 255),
            )
            x += max(250, 55 + len(label) * 8)


def raw_scene(objects, matrix):
    return render.rasterize(rotate(objects, matrix))


def save_scene(name: str, objects, matrix, title: str, subtitle: str, legend) -> Path:
    image, _projection = raw_scene(objects, matrix)
    annotate(image, title, subtitle, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / name
    image.convert("RGB").save(path, quality=96)
    return path


def closeup(name: str, objects, matrix, focus_meshes, title: str, subtitle: str, legend) -> Path:
    image, projection = raw_scene(objects, matrix)
    focus = np.concatenate([mesh @ matrix.T for mesh in focus_meshes]).reshape(-1, 3)
    projected = render.project(focus, projection)
    x0, y0 = projected.min(axis=0)
    x1, y1 = projected.max(axis=0)
    pad_x = max(100.0, 0.25 * (x1 - x0))
    pad_y = max(100.0, 0.30 * (y1 - y0))
    box = (
        max(0, int(x0 - pad_x)),
        max(0, int(y0 - pad_y)),
        min(render.WIDTH, int(x1 + pad_x)),
        min(render.HEIGHT, int(y1 + pad_y)),
    )
    crop = image.crop(box).resize((render.WIDTH, render.HEIGHT), Image.Resampling.LANCZOS)
    annotate(crop, title, subtitle, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / name
    crop.convert("RGB").save(path, quality=96)
    return path


def comparison(name: str, before_objects, after_objects, matrix) -> Path:
    before, _ = raw_scene(before_objects, matrix)
    after, _ = raw_scene(after_objects, matrix)
    before.thumbnail((710, 540), Image.Resampling.LANCZOS)
    after.thumbnail((710, 540), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (render.WIDTH, render.HEIGHT), (8, 14, 22))
    canvas.paste(before.convert("RGB"), (18, 220))
    canvas.paste(after.convert("RGB"), (760, 220))
    draw = ImageDraw.Draw(canvas)
    draw.text((220, 775), "CLEAN SHELL / openings absent", font=render.font(18, True), fill=(190, 207, 217))
    draw.text((915, 775), "EXTERIOR-FIRST / openings applied", font=render.font(18, True), fill=(*THUMB, 255))
    annotate(
        canvas,
        "BEFORE / AFTER MAX-LOWER THUMB EXTERIOR",
        "SAME (0,+12.25,-21.00) mm CONTROL LOCATION / ONLY HOUSING OPENINGS CHANGED",
        (("shell", SHELL_B), ("maximum-lowered Thumb", THUMB)),
    )
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / name
    canvas.save(path, quality=96)
    return path


def contact_sheet(paths: list[Path]) -> Path:
    cell_w, cell_h = 585, 470
    rows = math.ceil(len(paths) / 2)
    sheet = Image.new("RGB", (1220, 82 + rows * cell_h), (8, 14, 22))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (28, 18),
        "EXTERIOR-FIRST / MAXIMUM-LOWERED THUMB + LATEST FINGER 8",
        font=render.font(28, True),
        fill=TEXT,
    )
    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((cell_w - 15, cell_h - 60), Image.Resampling.LANCZOS)
        x = 15 + (index % 2) * 605
        y = 72 + (index // 2) * cell_h
        sheet.paste(image, (x, y))
        draw.text((x + 8, y + cell_h - 48), path.name, font=render.font(15), fill=(205, 219, 227))
    result = RENDER_DIR / "00_contact_sheet.png"
    sheet.save(result, quality=96)
    return result


def main() -> None:
    exact_shells = [load_shape(JAD_OUTPUT), load_shape(JFD_OUTPUT)]
    clean_shells = [load_shape(CLEAN_JAD), load_shape(CLEAN_JFD)]
    lower15_shells = [read_binary_stl(LOWER15_JAD_MESH), read_binary_stl(LOWER15_JFD_MESH)]
    grafted = [
        graft_lower15_thumb_patch(clean_shells[index], lower15_shells[index])
        for index in range(2)
    ]
    shells = [row[0] for row in grafted]
    patch_metrics = {"JaD": grafted[0][1], "JfD": grafted[1][1]}
    finger_caps = [load_shape(FINGER_DIR / f"{name}_cap.step") for name in BUTTON_ORDER]
    thumb = load_thumb()

    exterior = [
        (shells[0], SHELL_A),
        (shells[1], SHELL_B),
        *[(mesh, FINGER) for mesh in finger_caps],
        *[(mesh, THUMB) for mesh in thumb],
    ]
    before = [
        (clean_shells[0], SHELL_A),
        (clean_shells[1], SHELL_B),
        *[(mesh, THUMB) for mesh in thumb],
    ]
    shell_only = [(shells[0], SHELL_A), (shells[1], SHELL_B)]
    legend = (
        ("clean exterior shell", SHELL_B),
        ("latest Finger 8", FINGER),
        ("maximum-lowered Thumb exterior", THUMB),
    )
    thumb_side = align_vector(THUMB_SURFACE_NORMAL, RENDER_CAMERA_DIRECTION)
    thumb_oblique = rot_z(-28.0)
    rear = rot_z(140.0)
    front = rot_z(-40.0)
    finger_oblique = rot_z(65.0)

    paths = [
        save_scene(
            "01_thumb_side.png",
            exterior,
            thumb_side,
            "THUMB SIDE / EXTERIOR-FIRST V1",
            "MAXIMUM LOWER (0,+12.25,-21.00) mm / INTERNAL STRUCTURE DELIBERATELY EXCLUDED",
            legend,
        ),
        save_scene(
            "02_thumb_oblique.png",
            exterior,
            thumb_oblique,
            "THUMB OBLIQUE / LOWERED HOUSING APPLIED",
            "8 ORIGINAL BUTTON CAPS + JOYSTICK ATTACHMENT / THROUGH RELIEF = 0",
            legend,
        ),
        save_scene(
            "03_rear_latest_finger.png",
            exterior,
            rear,
            "REAR / LATEST FINGER 8 PRESERVED",
            "I2 I3 I4 M3 M4 N1 N2 N3 / LEGACY OPENINGS NOT REINTRODUCED",
            legend,
        ),
        save_scene(
            "04_front_exterior.png",
            exterior,
            front,
            "FRONT / EXTERIOR-ONLY COMBINATION",
            "NO BACKPLATE / PUSHBUTTON / HW504 BODY / CARRIER / WIRE / FASTENING EXPORTED",
            legend,
        ),
        save_scene(
            "05_full_oblique.png",
            exterior,
            finger_oblique,
            "FULL OBLIQUE / USER REVIEW MOCKUP",
            "EXTERIOR READY FOR REVIEW / PRODUCTION AND INTERNAL GATES NOT EVALUATED",
            legend,
        ),
        closeup(
            "06_thumb_region_closeup.png",
            exterior,
            thumb_side,
            thumb,
            "THUMB REGION CLOSE-UP",
            "ONLY USER-FACING CONTROL GEOMETRY / 0.80 mm LOCAL OPENING CLEARANCE",
            legend,
        ),
        comparison(
            "07_clean_vs_lowered_openings.png",
            before,
            exterior,
            thumb_side,
        ),
        closeup(
            "08_thumb_housing_shell_only.png",
            shell_only,
            thumb_side,
            thumb,
            "THUMB HOUSING ONLY / LOWER-15 EXTERIOR PATCH",
            "ACTUAL THUMB_LOWER15_HOUSING_V1 MESH SURFACE / INTERNALS AND CONTROLS HIDDEN",
            (("clean Finger shell", SHELL_B), ("lower-15 Thumb housing patch", SHELL_A)),
        ),
    ]
    sheet = contact_sheet(paths)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    visual_mesh = np.concatenate((shells[0], shells[1], *finger_caps, *thumb))
    write_binary_stl(
        VISUAL_STL,
        visual_mesh,
        "VISUAL ONLY: clean Finger exterior + lower15 Thumb patch; not printable",
    )
    VISUAL_MANIFEST.write_text(
        json.dumps(
            {
                "schema": 1,
                "purpose": "exterior-first visual composite only",
                "thumbTranslationMm": [0.0, 12.25, -21.0],
                "surfaceSources": {
                    "outsideThumbMask": "FINAL EXTERIOR CLEAN V1 exact-shell tessellation",
                    "insideThumbMask": "THUMB_LOWER15_HOUSING_V1 shell STL",
                },
                "thumbPatchLocalMask": {
                    "uMm": [-23.5, 23.5],
                    "vMm": [-34.0, 28.0],
                    "nMm": [-8.0, 40.0],
                    "rejectsOppositeRearFingerSurface": True,
                },
                "patchMetrics": patch_metrics,
                "exactEnvelopeShellTriangleCount": [len(exact_shells[0]), len(exact_shells[1])],
                "visualReferenceStl": str(VISUAL_STL.relative_to(ROOT)),
                "printApproval": False,
                "reason": "regional mesh graft is for exterior review; internal and watertight production gates are deferred",
                "renders": [str(path.relative_to(ROOT)) for path in [sheet, *paths]],
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    print({
        "renders": [str(path) for path in paths],
        "contactSheet": str(sheet),
        "visualReferenceStl": str(VISUAL_STL),
        "visualManifest": str(VISUAL_MANIFEST),
        "patchMetrics": patch_metrics,
    })


if __name__ == "__main__":
    main()
