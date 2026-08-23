"""READ-ONLY rear-envelope audit for INDEX/MIDDLE independent solids."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402


SHELL = ROOT / "exports" / "thumb_lower15_housing_mockup"
PARTS = ROOT / "exports" / "full_exterior_minimal_mockup" / "source_stl"
OUT = ROOT / "renders" / "index_middle_rear_protrusion_audit.png"


def part(number: int) -> np.ndarray:
    return read_binary_stl(PARTS / f"Joystick - Part {number}.stl")


def rotate_z(mesh: np.ndarray, degrees: float, center: np.ndarray) -> np.ndarray:
    angle = np.deg2rad(degrees)
    matrix = np.asarray(
        ((np.cos(angle), -np.sin(angle), 0.0),
         (np.sin(angle), np.cos(angle), 0.0),
         (0.0, 0.0, 1.0)),
        dtype=float,
    )
    return (mesh - center) @ matrix.T + center


def scene(angle: float, center: np.ndarray) -> Image.Image:
    jad = read_binary_stl(SHELL / "OneGrip_lower15_housing_Joystick_1_JaD.stl")
    jfd = read_binary_stl(SHELL / "OneGrip_lower15_housing_Joystick_2_JfD.stl")
    objects = [
        (jad, (44, 76, 98)),
        (jfd, (52, 91, 114)),
        *[(part(number), (48, 171, 224)) for number in (13, 14, 15, 16)],
        *[(part(number), (61, 183, 115)) for number in (24, 26, 28, 30)],
        (part(17), (231, 70, 191)),  # RWID
        (part(18), (239, 77, 54)),   # RZKD
        *[(part(number), (236, 174, 48)) for number in (19, 20, 21, 22, 23, 25, 27, 29)],
    ]
    rotated = [(rotate_z(mesh, angle, center), color) for mesh, color in objects]
    image, _ = render.rasterize(rotated)
    return image.convert("RGB")


def main() -> None:
    jad = read_binary_stl(SHELL / "OneGrip_lower15_housing_Joystick_1_JaD.stl")
    jfd = read_binary_stl(SHELL / "OneGrip_lower15_housing_Joystick_2_JfD.stl")
    shell_points = np.concatenate((jad.reshape(-1, 3), jfd.reshape(-1, 3)))
    center = (shell_points.min(axis=0) + shell_points.max(axis=0)) / 2.0

    # The shared rasterizer camera has an XY azimuth of about +50 degrees.
    # Rotate the model to obtain effective +Y, +X and -Y inspection views.
    panels = [scene(-40.0, center), scene(50.0, center), scene(140.0, center)]
    panel_w, panel_h = 720, 540
    canvas = Image.new("RGB", (panel_w * 3, panel_h + 150), (10, 17, 26))
    labels = ("REAR (+Y)", "SIDE PROFILE (+X)", "CONTROL SIDE (-Y)")
    for index, (panel, label) in enumerate(zip(panels, labels)):
        panel = panel.resize((panel_w, panel_h), Image.Resampling.LANCZOS)
        canvas.paste(panel, (index * panel_w, 70))
        draw = ImageDraw.Draw(canvas)
        draw.text((index * panel_w + 24, 20), label, font=render.font(27, True), fill=(239, 244, 248))

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((28, panel_h + 82, panel_w * 3 - 28, panel_h + 135), radius=12,
                           fill=(7, 12, 19), outline=(78, 99, 114), width=2)
    legend = [
        ("INDEX caps", (48, 171, 224)),
        ("MIDDLE caps", (61, 183, 115)),
        ("RWID", (231, 70, 191)),
        ("RZKD", (239, 77, 54)),
        ("spacers", (236, 174, 48)),
    ]
    x = 55
    for label, color in legend:
        draw.ellipse((x, panel_h + 98, x + 18, panel_h + 116), fill=color)
        draw.text((x + 26, panel_h + 92), label, font=render.font(16), fill=(225, 233, 238))
        x += 250
    draw.text((panel_w * 3 - 455, panel_h + 92), "READ-ONLY / CAD WRITE 0",
              font=render.font(16, True), fill=(177, 192, 202))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, quality=96)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
