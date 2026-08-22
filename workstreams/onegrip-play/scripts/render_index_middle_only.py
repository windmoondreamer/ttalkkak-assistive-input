"""Render only the exact independent INDEX and MIDDLE solids."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from PIL import ImageDraw


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402


SOURCE = ROOT / "exports" / "full_exterior_minimal_mockup" / "source_stl"
OUT = ROOT / "renders" / "index_middle_only.png"

INDEX_CAPS = (13, 14, 15, 16)
INDEX_RETAINERS = (17, 18)
INDEX_SPACERS = (19, 20, 21, 22)
MIDDLE_SPACERS = (23, 25, 27, 29)
MIDDLE_CAPS = (24, 26, 28, 30)


def load(number: int) -> np.ndarray:
    return read_binary_stl(SOURCE / f"Joystick - Part {number}.stl")


def centroid(meshes: list[np.ndarray]) -> np.ndarray:
    return np.concatenate([mesh.reshape(-1, 3) for mesh in meshes]).mean(axis=0)


def main() -> None:
    index_caps = [load(number) for number in INDEX_CAPS]
    index_retainers = [load(number) for number in INDEX_RETAINERS]
    index_spacers = [load(number) for number in INDEX_SPACERS]
    middle_spacers = [load(number) for number in MIDDLE_SPACERS]
    middle_caps = [load(number) for number in MIDDLE_CAPS]

    objects = []
    objects += [(mesh, (47, 150, 204)) for mesh in index_caps]
    objects += [(mesh, (226, 152, 43)) for mesh in index_retainers]
    objects += [(mesh, (93, 190, 225)) for mesh in index_spacers]
    objects += [(mesh, (109, 187, 139)) for mesh in middle_spacers]
    objects += [(mesh, (55, 151, 104)) for mesh in middle_caps]
    image, projection = render.rasterize(objects)
    draw = ImageDraw.Draw(image)

    draw.text((48, 35), "ONEGRIP PLAY / INDEX + MIDDLE ONLY", font=render.font(40, True), fill=(241, 246, 249, 255))
    draw.text((50, 86), "18 EXACT INDEPENDENT SOLIDS / SHELL AND THUMB HIDDEN", font=render.font(21), fill=(175, 194, 208, 255))

    groups = [
        ("INDEX", centroid(index_caps + index_spacers), (47, 168, 224, 255), (1035, 240)),
        ("RWID / RZKD", centroid(index_retainers), (226, 152, 43, 255), (1035, 315)),
        ("MIDDLE", centroid(middle_caps + middle_spacers), (74, 174, 120, 255), (1035, 390)),
    ]
    for text, world, color, box in groups:
        point = render.project(np.asarray([world]), projection)[0]
        draw.line((tuple(point), box), fill=color, width=4)
        draw.ellipse((point[0]-6, point[1]-6, point[0]+6, point[1]+6), fill=color)
        draw.rounded_rectangle((box[0]-14, box[1]-13, box[0]+315, box[1]+34), radius=10, fill=(9, 14, 21, 225), outline=color, width=2)
        draw.text((box[0], box[1]-5), text, font=render.font(20, True), fill=(239, 244, 247, 255))

    draw.rounded_rectangle((48, render.HEIGHT-108, 1050, render.HEIGHT-42), radius=14, fill=(9, 14, 21, 220), outline=(83, 105, 121, 230), width=2)
    draw.text((70, render.HEIGHT-89), "INDEX: CAPS 4 + SPACERS 4 + RETAINERS 2   /   MIDDLE: CAPS 4 + SPACERS 4", font=render.font(18, True), fill=(224, 190, 91, 255))
    draw.text((70, render.HEIGHT-63), "INTEGRATED HOLDERS REMAIN FUSED TO JaD/JfD SHELLS AND ARE NOT SHOWN", font=render.font(16), fill=(160, 181, 195, 255))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(OUT, quality=96)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
