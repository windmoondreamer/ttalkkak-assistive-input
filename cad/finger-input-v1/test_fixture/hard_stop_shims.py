"""Export 0.1/0.2/0.3 mm laser-cut or shim-stock hard-stop gauges.

These are primarily dimensional references. FDM cannot reliably produce a
single 0.1 mm layer, so 0.1/0.2 mm versions should be cut from PET shim stock;
the 0.3 mm version may be printed with a 0.1 mm profile.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import cadquery as cq

from finger_module_common import export_bundle


def shim(thickness: float) -> cq.Workplane:
    """Universal U-shim for B side followers and CENTER guide posts.

    The 5.7 x 5.9 mm outside lands on either printed collar.  The 3.0 x 3.8
    mm opening clears the largest 2.8 x 3.6 mm guide post, and the side mouth
    lets the shim be changed without removing the key or its retaining pin.
    """
    outer = cq.Workplane("XY").box(5.7, 5.9, thickness, centered=(True, True, False))
    inner = cq.Workplane("XY").box(3.0, 3.8, thickness + 0.2, centered=(True, True, False)).translate((0, 0, -0.1))
    mouth = cq.Workplane("XY").box(1.7, 3.0, thickness + 0.2, centered=(True, True, False)).translate((0, -2.7, -0.1))
    return outer.cut(inner).cut(mouth)


if __name__ == "__main__":
    for value in (0.1, 0.2, 0.3):
        export_bundle(shim(value), HERE / f"hard_stop_shim_{value:.1f}mm")
    # DXF is the practical artifact for 0.1/0.2 mm PET shim stock; STL/STEP/3MF
    # remain dimensional references and the 0.3 mm version can be FDM printed.
    # DXF export may not be available in every CadQuery build.  The STEP/STL/
    # 3MF profiles above remain the authoritative dimensional artifacts.
    try:
        profile = shim(0.20).faces(">Z")
        cq.exporters.exportDXF(profile, str(HERE / "hard_stop_shim_profile.dxf"))
    except Exception as exc:
        print(f"DXF export skipped: {type(exc).__name__}: {exc}")
