"""Render the finalized 4 INDEX + 4 MIDDLE ITS-1105 implementation.

This is a network-free audit render.  It combines the last captured live shell
tessellation (which already contains INDEX and M1..M3 work) with the exact M4
positive primitives and all eight design-envelope switch/cap/spacer overlays.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_middle_prewrite as geom  # noqa: E402
import audit_its1105_physical_sample as physical  # noqa: E402
import audit_middle_its1105_design as middle  # noqa: E402
import audit_stock_6x6_switch as stock  # noqa: E402
import render_index_its_audit as render  # noqa: E402


EXPLODE = 10.0
INDEX_ROLLS = (0, 0, 90, 90)
MIDDLE_ROLLS = (90, 90, 0, 0)
INDEX_AXES = np.asarray([
    (-0.847667872, -0.506166919, -0.158915794),
    (-0.387542111, -0.574231284, -0.721158474),
    (-0.068454195, -0.997609880, 0.009410170),
    (0.024161000, -0.968017000, -0.249718000),
])
MIDDLE_POINTS = np.asarray([
    (-19.835372272, -0.614991709, -11.125000000),
    (-12.899418190, -8.744828192, -14.125000000),
    (-3.537874175, -14.413708840, -11.125000000),
    (7.444327590, -13.569623472, -11.125000000),
])
MIDDLE_NORMALS = np.asarray([
    (-0.961658811, -0.158356278, -0.223909849),
    (-0.486144819, -0.708160212, -0.512027664),
    (-0.103551539, -0.791264502, -0.602642155),
    (0.224859127, -0.772792774, -0.593489428),
])
MIDDLE_AXES = np.asarray([
    (-0.837518998, -0.499950062, -0.220480981),
    (-0.601521153, -0.782846337, -0.159134899),
    (0.320428890, -0.733472608, -0.599452466),
    (0.224859127, -0.772792774, -0.593489428),
])


def shift_for(index: int) -> float:
    return -EXPLODE if index < 3 else EXPLODE


def add_box(objects, box, dx, color):
    objects.append((render.shifted(render.obb_triangles(box), dx), color))


def add_cylinder(objects, point, axis, radius, front, rear, dx, color, segments=28):
    tris = render.cylinder_triangles(point, axis, radius, front, rear, segments)
    objects.append((render.shifted(tris, dx), color))


def m4_positive_support(objects):
    """Exact uncut visible M4 frame/rail primitives from the committed FS."""
    point = MIDDLE_POINTS[3]
    axis = geom.unit(MIDDLE_AXES[3])
    axes = geom.frame(axis)
    dx = EXPLODE
    color = (82, 151, 181)
    depth = 8.839587617 + 0.40 - 2.20
    # 10.0 outer / 8.4 opening -> four 0.8 mm frame bars.
    for sign in (-1.0, 1.0):
        add_box(objects, middle.obb_rect(point + axes[1] * (sign * 4.60), axes,
                                        10.00, 0.80, depth, 2.20), dx, color)
        add_box(objects, middle.obb_rect(point + axes[0] * (sign * 4.60), axes,
                                        0.80, 8.40, depth, 2.20), dx, color)
    spacer_rear = 11.279587617
    for sign in (-1.0, 1.0):
        rail_u = -3.80 if sign < 0 else 4.60
        hook_u = -2.50 if sign < 0 else 2.75
        add_box(objects, middle.obb_rect(point + axes[0] * rail_u, axes,
                                        0.80, 3.20, spacer_rear + 0.40 - 2.20, 2.20),
                dx, color)
        add_box(objects, middle.obb_rect(point + axes[0] * hook_u, axes,
                                        3.10, 3.20, 0.70, spacer_rear), dx, color)


def main(handedness: str = "left"):
    objects = []
    labels = []
    shell_left = render.load_mesh("ITS_LIVE_JfD")
    shell_right = render.load_mesh("ITS_LIVE_JaD")
    objects.append((render.shifted(shell_left, -EXPLODE), (65, 124, 164)))
    objects.append((render.shifted(shell_right, EXPLODE), (83, 148, 181)))
    objects.append((render.shifted(render.load_mesh("ITS_LIVE_RWID"), -EXPLODE), (198, 208, 215)))
    objects.append((render.shifted(render.load_mesh("ITS_LIVE_RZKD"), EXPLODE), (217, 153, 55)))
    m4_positive_support(objects)

    # INDEX: physical housings, actuators, rigid roots, spacers, and frozen caps.
    for index in range(4):
        dx = shift_for(index)
        point = np.asarray(geom.INDEX_CENTERS[index], dtype=float)
        axis = geom.unit(INDEX_AXES[index])
        index_axes = middle.rotated_axes(axis, INDEX_ROLLS[index])
        body = middle.obb_rect(point, index_axes, physical.BODY_X, physical.BODY_Y,
                               physical.HOUSING_H, stock.INDEX_FRONT)
        add_box(objects, body, dx, (224, 91, 48))
        add_cylinder(objects, point, axis, physical.ACTUATOR_D / 2.0,
                     stock.INDEX_FRONT - physical.ACTUATOR_PROJECTION,
                     stock.INDEX_FRONT, dx, (244, 133, 65))
        for root in physical.physical_root_boxes(index, INDEX_ROLLS[index], physical.BODY_X):
            add_box(objects, root, dx, (205, 166, 75))
        add_cylinder(objects, point, axis, 1.80, 8.86,
                     8.86 + (2.4403 if index < 3 else 2.44), dx, (190, 199, 207))
        cap = geom.obb(point, geom.unit(np.asarray(stock.INDEX_NORMALS[index])), 7.6, 4.0, -1.4)
        add_box(objects, cap, dx, (42, 48, 58))
        labels.append((f"I{index + 1}", point + np.asarray((dx, 0, 0))))

    # MIDDLE: exact 6.18 x 6.12 envelope, actuator, spacer, 8 mm cap/stem/lugs.
    for index in range(4):
        dx = shift_for(index)
        point = MIDDLE_POINTS[index]
        axis = geom.unit(MIDDLE_AXES[index])
        normal = geom.unit(MIDDLE_NORMALS[index])
        axes = middle.rotated_axes(axis, MIDDLE_ROLLS[index])
        body = middle.obb_rect(point, axes, 6.18, 6.12, 3.56, 5.279587617)
        add_box(objects, body, dx, (227, 93, 47))
        add_cylinder(objects, point, axis, 3.35 / 2.0, 2.839587617,
                     5.279587617, dx, (246, 137, 68))
        add_cylinder(objects, point, axis, 1.80, 8.839587617,
                     11.279587617, dx, (190, 199, 207))
        cap = geom.obb(point, normal, 8.0, 1.8, -0.20)
        add_box(objects, cap, dx, (39, 46, 57))
        cosine = float(np.dot(normal, axis))
        add_cylinder(objects, point, axis, 1.50, -0.80,
                     2.839587617 - 0.05 * cosine, dx, (53, 61, 72))
        cap_u = geom.unit(np.cross((0.0, 0.0, 1.0), normal))
        for sign in (-1.0, 1.0):
            add_cylinder(objects, point + cap_u * (sign * 3.0), normal,
                         0.45, 1.55, 2.35, dx, (63, 71, 82), segments=20)
        labels.append((f"M{index + 1}", point + np.asarray((dx, 0, 0))))

    is_right = handedness == "right"
    if is_right:
        mirrored = []
        for triangles, color in objects:
            triangles = triangles.copy()
            triangles[:, :, 0] *= -1.0
            mirrored.append((triangles, color))
        objects = mirrored
        labels = [
            (name, np.asarray((-point[0], point[1], point[2]), dtype=float))
            for name, point in labels
        ]

    image, projection = render.rasterize(objects)
    draw = ImageDraw.Draw(image)
    title_font = render.font(40, True)
    sub_font = render.font(22, False)
    label_font = render.font(17, True)
    small_font = render.font(18, False)
    title = (
        "ONEGRIP PLAY  /  ITS-1105 RIGHT-HAND MIRROR"
        if is_right
        else "ONEGRIP PLAY  /  ITS-1105 SAME-SKU FINAL"
    )
    draw.text((48, 38), title,
              font=title_font, fill=(239, 244, 248, 255))
    draw.text((50, 88), "INDEX 4 + MIDDLE 4  /  6.18 x 6.12 DESIGN ENVELOPE",
              font=sub_font, fill=(168, 187, 201, 255))

    for name, point in labels:
        xy = render.project(np.asarray([point]), projection)[0]
        fill = (255, 208, 187, 255) if name.startswith("I") else (255, 221, 178, 255)
        draw.rounded_rectangle((xy[0] - 18, xy[1] - 14, xy[0] + 18, xy[1] + 14),
                               radius=7, fill=(12, 18, 26, 220), outline=fill, width=2)
        bbox = draw.textbbox((0, 0), name, font=label_font)
        draw.text((xy[0] - (bbox[2] - bbox[0]) / 2,
                   xy[1] - (bbox[3] - bbox[1]) / 2 - 2), name,
                  font=label_font, fill=fill)

    y0 = render.HEIGHT - 108
    draw.rounded_rectangle((48, y0, 1005, render.HEIGHT - 42), radius=14,
                           fill=(10, 15, 22, 210), outline=(88, 104, 118, 220), width=2)
    legend = [
        ((224, 91, 48), "ITS-1105 housing"),
        ((205, 166, 75), "rigid roots"),
        ((190, 199, 207), "2.44 spacer"),
        ((217, 153, 55), "RZKD"),
    ]
    x = 72
    for color, text in legend:
        draw.ellipse((x, y0 + 24, x + 22, y0 + 46), fill=(*color, 255))
        draw.text((x + 34, y0 + 18), text, font=small_font, fill=(225, 232, 238, 255))
        x += 225
    footer = (
        "30 SOLIDS  |  X=0 MIRROR  |  ERROR 0"
        if is_right
        else "30 SOLIDS  |  M4 COMMITTED  |  ERROR 0"
    )
    draw.text((render.WIDTH - 420, render.HEIGHT - 64), footer,
              font=small_font, fill=(158, 178, 191, 255))

    filename = (
        "its1105_right_hand_8button_final.png"
        if is_right
        else "its1105_same_sku_8button_final.png"
    )
    output = ROOT / "renders" / filename
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, quality=96)
    print(f"wrote {output} {image.size}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hand", choices=("left", "right"), default="left")
    args = parser.parse_args()
    main(args.hand)
