"""Render the exact exported lower-15 external housing STL pair."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from PIL import ImageDraw


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402


SOURCE = ROOT / "exports" / "thumb_lower15_housing_mockup"
JA_D = SOURCE / "OneGrip_lower15_housing_Joystick_1_JaD.stl"
JF_D = SOURCE / "OneGrip_lower15_housing_Joystick_2_JfD.stl"


def shifted(mesh: np.ndarray, x: float) -> np.ndarray:
    result = mesh.copy()
    result[:, :, 0] += x
    return result


def label(image, title: str, subtitle: str, footer: str) -> None:
    draw = ImageDraw.Draw(image)
    draw.text((48, 34), title, font=render.font(39, True), fill=(242, 247, 250, 255))
    draw.text((50, 84), subtitle, font=render.font(20), fill=(176, 195, 209, 255))
    draw.rounded_rectangle(
        (48, render.HEIGHT - 103, 1030, render.HEIGHT - 42),
        radius=14,
        fill=(9, 14, 21, 220),
        outline=(89, 110, 125, 230),
        width=2,
    )
    draw.text((70, render.HEIGHT - 85), footer, font=render.font(18, True), fill=(229, 190, 88, 255))


def main() -> None:
    jad = read_binary_stl(JA_D)
    jfd = read_binary_stl(JF_D)

    assembled, _ = render.rasterize([
        (jad, (70, 128, 160)),
        (jfd, (82, 145, 174)),
    ])
    label(
        assembled,
        "ONEGRIP PLAY / LOWER-15 EXTERNAL HOUSING",
        "EXACT ONSHAPE STL / ASSEMBLED SHELL MOCKUP",
        "JaD + JfD / CONTROLS AND INTERNAL PARTS EXCLUDED",
    )
    assembled_path = ROOT / "renders" / "thumb_lower15_final_housing_assembled.png"
    assembled.convert("RGB").save(assembled_path, quality=96)

    exploded, _ = render.rasterize([
        (shifted(jad, +24.0), (75, 135, 167)),
        (shifted(jfd, -24.0), (91, 154, 181)),
    ])
    label(
        exploded,
        "ONEGRIP PLAY / LOWER-15 EXTERNAL HOUSING",
        "EXACT ONSHAPE STL / TWO PRINTABLE SHELLS",
        "LEFT: JfD  /  RIGHT: JaD  /  2 WATERTIGHT COMPONENTS",
    )
    exploded_path = ROOT / "renders" / "thumb_lower15_final_housing_exploded.png"
    exploded.convert("RGB").save(exploded_path, quality=96)
    print(f"wrote {assembled_path}")
    print(f"wrote {exploded_path}")


if __name__ == "__main__":
    main()
