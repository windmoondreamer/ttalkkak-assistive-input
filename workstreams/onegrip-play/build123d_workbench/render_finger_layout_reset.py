"""Render the clean-shell eight-button external marker proposal.

Rendering is local and consumes only the immutable AP242 references plus the
marker-only build from ``finger_layout_reset``.  It does not create shell cuts
or contact Onshape.
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

from .finger_layout_reset import MARKER_EXPOSURE, LayoutBuild, build_layout, triangles, unit


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_index_its_audit as render  # noqa: E402


OUT_DIR = ROOT / "renders" / "finger_layout_reset"
SHELL_JAD = (49, 78, 97)
SHELL_JFD = (57, 91, 111)
THUMB = (83, 103, 116)
RETAINED = (47, 165, 224)
NEW = (239, 76, 55)
REMOVED = (242, 48, 59)


def rotate_z(points: np.ndarray, degrees: float, center: np.ndarray) -> np.ndarray:
    angle = np.deg2rad(degrees)
    matrix = np.asarray(
        ((np.cos(angle), -np.sin(angle), 0.0),
         (np.sin(angle), np.cos(angle), 0.0),
         (0.0, 0.0, 1.0)),
        dtype=float,
    )
    return (np.asarray(points) - center) @ matrix.T + center


def label(draw: ImageDraw.ImageDraw, xy: np.ndarray, name: str, color: tuple[int, int, int], offset: tuple[int, int]) -> None:
    x, y = float(xy[0]), float(xy[1])
    ox, oy = offset
    tx, ty = x + ox, y + oy
    font = render.font(21, True)
    box = draw.textbbox((0, 0), name, font=font)
    width = box[2] - box[0] + 18
    height = box[3] - box[1] + 12
    draw.line((x, y, tx, ty + height / 2), fill=(*color, 220), width=3)
    draw.rounded_rectangle((tx, ty, tx + width, ty + height), radius=8,
                           fill=(8, 14, 22, 230), outline=(*color, 255), width=2)
    draw.text((tx + 9, ty + 3), name, font=font, fill=(244, 248, 250, 255))


def render_scene(layout: LayoutBuild, angle: float, title: str, show_removed: bool = False) -> Image.Image:
    shell_triangles = [triangles(layout.jad), triangles(layout.jfd)]
    shell_points = np.concatenate([item.reshape(-1, 3) for item in shell_triangles])
    center = 0.5 * (shell_points.min(axis=0) + shell_points.max(axis=0))

    objects: list[tuple[np.ndarray, tuple[int, int, int]]] = [
        (shell_triangles[0], SHELL_JAD),
        (shell_triangles[1], SHELL_JFD),
    ]
    objects.extend((triangles(shape), THUMB) for shape in layout.visible_thumb)
    for datum, shape in zip(layout.datums, layout.markers):
        objects.append((triangles(shape), RETAINED if datum.kind == "retained" else NEW))

    rotated = [(rotate_z(mesh, angle, center), color) for mesh, color in objects]
    image, projection = render.rasterize(rotated)
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")

    retained_offsets = {
        "I2": (-86, -54), "I3": (-36, -74), "I4": (24, -62),
        "M3": (-76, 25), "M4": (22, 32),
    }
    new_offsets = {"N1": (-74, -74), "N2": (24, -72), "N3": (25, 18)}
    for datum in layout.datums:
        point = np.asarray(datum.center) + unit(datum.normal) * (MARKER_EXPOSURE + 0.5)
        point = rotate_z(point[None, :], angle, center)[0]
        screen = render.project(point[None, :], projection)[0]
        color = RETAINED if datum.kind == "retained" else NEW
        offset = retained_offsets.get(datum.name, new_offsets.get(datum.name, (18, -20)))
        label(draw, screen, datum.name, color, offset)

    if show_removed:
        for index, datum in enumerate(layout.removed):
            point = np.asarray(datum.center) + unit(datum.normal) * 0.8
            point = rotate_z(point[None, :], angle, center)[0]
            screen = render.project(point[None, :], projection)[0]
            x, y = float(screen[0]), float(screen[1])
            radius = 22
            draw.line((x - radius, y - radius, x + radius, y + radius), fill=(*REMOVED, 255), width=8)
            draw.line((x - radius, y + radius, x + radius, y - radius), fill=(*REMOVED, 255), width=8)
            label(draw, screen, f"REMOVE {datum.name}", REMOVED, (-132, 40 + index * 6))

    title_font = render.font(34, True)
    subtitle_font = render.font(18)
    draw.rounded_rectangle((28, 24, 770, 104), radius=14, fill=(6, 11, 18, 218),
                           outline=(95, 115, 129, 210), width=2)
    draw.text((49, 36), title, font=title_font, fill=(242, 247, 250, 255))
    draw.text((50, 78), "BLUE = retained/recreated   RED = new marker   no cuts / no pockets",
              font=subtitle_font, fill=(194, 208, 217, 255))
    return image.convert("RGB")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    layout = build_layout()
    views = (
        ("01_button_facing_rear.png", 140.0, "BUTTON-FACING REAR / INITIAL 8-BUTTON LAYOUT", False),
        ("02_left_oblique.png", 112.0, "LEFT OBLIQUE", False),
        ("03_right_oblique.png", 168.0, "RIGHT OBLIQUE", False),
        ("04_side_profile.png", 50.0, "SIDE PROFILE", False),
        ("05_removed_comparison.png", 140.0, "REMOVED I1 / M1 / M2 COMPARISON", True),
    )
    images: list[tuple[str, Image.Image]] = []
    for filename, angle, title, show_removed in views:
        image = render_scene(layout, angle, title, show_removed)
        path = OUT_DIR / filename
        image.save(path, quality=96)
        images.append((title, image))
        print(path)

    panel_w, panel_h = 700, 525
    canvas = Image.new("RGB", (panel_w * 2, panel_h * 3 + 90), (8, 13, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((34, 20), "ONEGRIP CLEAN-SHELL EXTERNAL FINGER LAYOUT — ERGONOMIC REVIEW",
              font=render.font(30, True), fill=(239, 245, 248))
    for index, (_title, image) in enumerate(images):
        x = (index % 2) * panel_w
        y = 78 + (index // 2) * panel_h
        canvas.paste(image.resize((panel_w, panel_h), Image.Resampling.LANCZOS), (x, y))
    legend_y = 78 + 2 * panel_h + 30
    draw.rounded_rectangle((panel_w + 30, legend_y, panel_w * 2 - 30, legend_y + 250), radius=16,
                           fill=(13, 21, 31), outline=(86, 108, 123), width=2)
    draw.text((panel_w + 58, legend_y + 28), "LAYOUT GATE", font=render.font(25, True), fill=(240, 245, 248))
    rows = (
        "KEEP: I2 I3 I4 M3 M4",
        "ADD:  N1 N2 N3",
        "REMOVE REFERENCE: I1 M1 M2",
        "SHELL CUT / POCKET / CARRIER / WIRING: 0",
        "NEXT: USER ERGONOMIC APPROVAL",
    )
    for row_index, row in enumerate(rows):
        draw.text((panel_w + 58, legend_y + 75 + row_index * 32), row,
                  font=render.font(17, row_index == 4),
                  fill=(204, 217, 226) if row_index < 4 else (244, 114, 88))
    contact = OUT_DIR / "00_contact_sheet.png"
    canvas.save(contact, quality=96)
    print(contact)


if __name__ == "__main__":
    main()
