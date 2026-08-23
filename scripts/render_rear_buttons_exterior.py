"""Render the button-facing rear/control exterior straight-on."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pack_right_hand_handle_stl import read_binary_stl
from render_index_middle_rear_protrusion_audit import SHELL, scene


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "renders" / "rear_buttons_exterior_full.png"


def main() -> None:
    jad = read_binary_stl(SHELL / "OneGrip_lower15_housing_Joystick_1_JaD.stl")
    jfd = read_binary_stl(SHELL / "OneGrip_lower15_housing_Joystick_2_JfD.stl")
    points = np.concatenate((jad.reshape(-1, 3), jfd.reshape(-1, 3)))
    center = (points.min(axis=0) + points.max(axis=0)) / 2.0

    # The shared software camera looks from an XY azimuth near +50 degrees.
    # A +140 degree model rotation faces the exterior INDEX/MIDDLE button side
    # straight into the camera (the user's product-rear/control face).
    image = scene(140.0, center)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, quality=96)
    print(OUT)


if __name__ == "__main__":
    main()
