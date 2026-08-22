"""Audited OneGrip dimensions and datums used by the build123d baseline.

All numeric geometry is in millimetres. These values mirror
``cad/OneGrip_Simplified_Finger_Internals.fs`` at the immutable Onshape
version below; local experiments should derive from these constants instead
of modifying them in-place.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias


Vec3: TypeAlias = tuple[float, float, float]

ONSHAPE_DOCUMENT_ID = "a21e64f36bc61df760d4587c"
ONSHAPE_ELEMENT_ID = "425d9199b59cfb1efd9ddc35"
ONSHAPE_VERSION_NAME = "FINGER_SIMPLIFIED_CARRIER_V1"
ONSHAPE_VERSION_ID = "f51e9d9a868db9ef0fcd4b06"
ONSHAPE_URL = (
    "https://cad.onshape.com/documents/"
    f"{ONSHAPE_DOCUMENT_ID}/v/{ONSHAPE_VERSION_ID}/e/{ONSHAPE_ELEMENT_ID}"
)


@dataclass(frozen=True, slots=True)
class ButtonDatum:
    name: str
    center: Vec3
    axis: Vec3
    normal: Vec3
    dominant_side: bool
    roll_90: bool = False


INDEX: tuple[ButtonDatum, ...] = (
    ButtonDatum("I1", (-22.224, -17.494, 9.000),
                (-0.847667872, -0.506166919, -0.158915794),
                (-0.9291, -0.2385, -0.2828), True),
    ButtonDatum("I2", (-15.970, -26.208, 9.000),
                (-0.387542111, -0.574231284, -0.721158474),
                (-0.4724, -0.7368, -0.4838), True),
    ButtonDatum("I3", (-5.496, -29.325, 9.000),
                (-0.068454195, -0.997609880, 0.009410170),
                (-0.0383, -0.9556, -0.2921), True),
    ButtonDatum("I4", (5.496, -29.325, 9.000),
                (0.024161000, -0.968017000, -0.249718000),
                (0.0383, -0.9556, -0.2921), False),
)

MIDDLE: tuple[ButtonDatum, ...] = (
    ButtonDatum("M1", (-19.835372272, -0.614991709, -11.125),
                (-0.837518998, -0.499950062, -0.220480981),
                (-0.961658811, -0.158356278, -0.223909849), True, True),
    ButtonDatum("M2", (-12.899418190, -8.744828192, -14.125),
                (-0.601521153, -0.782846337, -0.159134899),
                (-0.486144819, -0.708160212, -0.512027664), True, True),
    ButtonDatum("M3", (-3.537874175, -14.413708840, -11.125),
                (0.320428890, -0.733472608, -0.599452466),
                (-0.103551539, -0.791264502, -0.602642155), True),
    ButtonDatum("M4", (7.444327590, -13.569623472, -11.125),
                (0.224859127, -0.772792774, -0.593489428),
                (0.224859127, -0.772792774, -0.593489428), False),
)

BACKPLANE = 14.50
POST_SIZE = 3.60
BEAM_WIDTH = 3.20
BEAM_THICKNESS = 4.00
INDEX_REAR = 8.86
MIDDLE_REAR = 8.839587617
DOGLEG: Vec3 = (-3.181, 5.414, -1.125)

MIDDLE_POCKET = 6.40
CAP_OPENING = 8.00
CAP_SIZE = 7.60
CAP_EXPOSURE = 1.40
HOLDER_FRONT_TRIM = 2.20

SHARED_LINKS: tuple[tuple[str, str, Vec3], ...] = (
    ("I3", "M3", (0.211301290, 0.731289520, 0.648511680)),
    ("M3", "DOGLEG", (-0.843215940, 0.490299570, -0.220438680)),
    ("DOGLEG", "M2", (0.995963070, -0.022796690, -0.086820900)),
    ("M2", "M1", (0.847015100, 0.382384410, 0.369252730)),
)

I4_LINK_X_HINT: Vec3 = (0.041113690, 0.761210510, 0.647200300)

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_MESHES: dict[str, Path] = {
    "JaD_shell": REPO_ROOT / "exports" / "thumb_lower15_housing_mockup"
    / "OneGrip_lower15_housing_Joystick_1_JaD.stl",
    "JfD_shell": REPO_ROOT / "exports" / "thumb_lower15_housing_mockup"
    / "OneGrip_lower15_housing_Joystick_2_JfD.stl",
    "RWID_retainer": REPO_ROOT / "exports" / "full_exterior_minimal_mockup"
    / "source_stl" / "Joystick - Part 17.stl",
    "RZKD_retainer": REPO_ROOT / "exports" / "full_exterior_minimal_mockup"
    / "source_stl" / "Joystick - Part 18.stl",
}
