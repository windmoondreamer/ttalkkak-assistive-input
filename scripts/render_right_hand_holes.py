"""Render the drilled/fastened regions of the final right-hand handle STL set."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from PIL import ImageDraw


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402


STL_DIR = ROOT / "exports" / "right_hand_handle_parts" / "individual_stl"
EXPLODE = 24.0


def load(name: str) -> np.ndarray:
    return read_binary_stl(STL_DIR / name)


def shifted(triangles: np.ndarray, dx=0.0, dy=0.0, dz=0.0) -> np.ndarray:
    result = triangles.copy()
    result += np.asarray((dx, dy, dz), dtype=float)
    return result


def main() -> None:
    # Keep switch caps/spacers out of this render so the actual cut bores and
    # retainer screw passages remain readable.
    jad = shifted(load("Joystick - Joystick_1.stl"), dx=-EXPLODE)
    jfd = shifted(load("Joystick - Joystick_2.stl"), dx=EXPLODE)
    rwid = shifted(load("Joystick - Part 17.stl"), dx=EXPLODE)
    rzkd = shifted(load("Joystick - Part 18.stl"), dx=-EXPLODE)
    backplate = shifted(load("Joystick - Backplate.stl"), dy=10.0, dz=7.0)

    objects = [
        (jad, (67, 126, 163)),
        (jfd, (88, 154, 184)),
        (backplate, (111, 124, 136)),
        (rwid, (213, 171, 70)),
        (rzkd, (231, 133, 56)),
    ]
    image, projection = render.rasterize(objects)
    draw = ImageDraw.Draw(image)
    title_font = render.font(40, True)
    sub_font = render.font(22, False)
    label_font = render.font(18, True)
    small_font = render.font(18, False)

    draw.text((48, 36), "ONEGRIP RIGHT HAND  /  DRILLED HOLES",
              font=title_font, fill=(241, 245, 248, 255))
    draw.text((50, 86), "EXPLODED INTERNAL VIEW  /  FINAL STL GEOMETRY",
              font=sub_font, fill=(170, 189, 202, 255))

    labels = [
        ("JaD / I4 side", jad.reshape(-1, 3).mean(axis=0), (255, 190, 155, 255)),
        ("JfD / shared side", jfd.reshape(-1, 3).mean(axis=0), (180, 220, 245, 255)),
        ("RWID", rwid.reshape(-1, 3).mean(axis=0), (255, 221, 135, 255)),
        ("RZKD", rzkd.reshape(-1, 3).mean(axis=0), (255, 174, 120, 255)),
    ]
    for name, point, color in labels:
        xy = render.project(np.asarray([point]), projection)[0]
        bbox = draw.textbbox((0, 0), name, font=label_font)
        width = bbox[2] - bbox[0] + 22
        height = bbox[3] - bbox[1] + 14
        box = (xy[0] - width / 2, xy[1] - height / 2,
               xy[0] + width / 2, xy[1] + height / 2)
        draw.rounded_rectangle(box, radius=8, fill=(11, 17, 24, 220), outline=color, width=2)
        draw.text((xy[0] - (bbox[2] - bbox[0]) / 2,
                   xy[1] - (bbox[3] - bbox[1]) / 2 - 2),
                  name, font=label_font, fill=color)

    legend_y = render.HEIGHT - 93
    draw.rounded_rectangle((48, legend_y, 1055, render.HEIGHT - 38), radius=13,
                           fill=(10, 15, 22, 215), outline=(86, 105, 118, 220), width=2)
    legend = [
        ((67, 126, 163), "JaD shell"),
        ((88, 154, 184), "JfD shell"),
        ((213, 171, 70), "shared retainer"),
        ((231, 133, 56), "I4 retainer"),
    ]
    x = 70
    for color, text in legend:
        draw.ellipse((x, legend_y + 16, x + 22, legend_y + 38), fill=(*color, 255))
        draw.text((x + 32, legend_y + 12), text, font=small_font, fill=(225, 233, 239, 255))
        x += 235
    draw.text((render.WIDTH - 390, render.HEIGHT - 63),
              "BORES ARE OPEN  |  PARTS SEPARATED",
              font=small_font, fill=(157, 181, 197, 255))

    output = ROOT / "renders" / "right_hand_handle_holes_exploded.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, quality=96)
    print(f"wrote {output} {image.size}")


if __name__ == "__main__":
    main()
