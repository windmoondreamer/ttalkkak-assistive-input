"""Opaque-shell visibility audit for INDEX/MIDDLE independent solids."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from PIL import ImageDraw


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402


SHELL = ROOT / "exports" / "thumb_lower15_housing_mockup"
PARTS = ROOT / "exports" / "full_exterior_minimal_mockup" / "source_stl"
OUT = ROOT / "renders" / "index_middle_exterior_exposure_audit.png"


def part(number: int) -> np.ndarray:
    return read_binary_stl(PARTS / f"Joystick - Part {number}.stl")


def main() -> None:
    jad = read_binary_stl(SHELL / "OneGrip_lower15_housing_Joystick_1_JaD.stl")
    jfd = read_binary_stl(SHELL / "OneGrip_lower15_housing_Joystick_2_JfD.stl")

    objects = [
        (jad, (45, 80, 102)),
        (jfd, (53, 92, 115)),
    ]
    # Intended user-facing caps.
    objects += [(part(number), (50, 173, 225)) for number in (13, 14, 15, 16)]
    objects += [(part(number), (64, 184, 117)) for number in (24, 26, 28, 30)]
    # Internal-only solids. Any broad red/yellow external patch is a defect.
    objects += [(part(number), (224, 67, 60)) for number in (17, 18)]
    objects += [(part(number), (231, 166, 56)) for number in (19, 20, 21, 22, 23, 25, 27, 29)]

    image, _ = render.rasterize(objects)
    draw = ImageDraw.Draw(image)
    draw.text((48, 35), "INDEX / MIDDLE EXTERIOR EXPOSURE AUDIT", font=render.font(38, True), fill=(241, 246, 249, 255))
    draw.text((50, 84), "OPAQUE FINAL SHELL / EXACT INDEPENDENT PART POSITIONS", font=render.font(20), fill=(175, 194, 208, 255))
    draw.rounded_rectangle((48, render.HEIGHT-115, 1165, render.HEIGHT-42), radius=14, fill=(9, 14, 21, 225), outline=(83, 105, 121, 230), width=2)
    legend = [
        ("INDEX caps", (50, 173, 225)),
        ("MIDDLE caps", (64, 184, 117)),
        ("retainers = internal", (224, 67, 60)),
        ("spacers = internal", (231, 166, 56)),
    ]
    x = 70
    for text, color in legend:
        draw.ellipse((x, render.HEIGHT-92, x+20, render.HEIGHT-72), fill=color)
        draw.text((x+28, render.HEIGHT-98), text, font=render.font(17), fill=(225, 233, 238, 255))
        x += 260
    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(OUT, quality=96)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
