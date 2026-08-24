"""Export named solids from the immutable stock-gimbal open-source STEP.

This is an inspection helper only.  It does not modify the source geometry.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import cadquery as cq


HERE = Path(__file__).resolve().parent
OPTION_C = HERE.parent / "stock-cartridge-option-c"
SOURCE = OPTION_C / "source" / "stock_gimbal_base_source_all_parts.step"
BUILDER = OPTION_C / "build_option_c.py"
OUT = HERE / "stock_gimbal_named_parts"


def main() -> None:
    spec = importlib.util.spec_from_file_location("option_c_builder", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    names = module.step_solid_names(SOURCE)
    solids = cq.importers.importStep(str(SOURCE)).solids().vals()
    if len(names) != len(solids):
        raise RuntimeError("STEP name/solid count mismatch")

    OUT.mkdir(parents=True, exist_ok=True)
    for name, solid in zip(names, solids, strict=True):
        cq.exporters.export(
            solid,
            str(OUT / f"{name}.stl"),
            tolerance=0.05,
            angularTolerance=0.20,
        )
        cq.exporters.export(solid, str(OUT / f"{name}.step"))
        box = solid.BoundingBox()
        print(
            f"{name}: {box.xlen:.3f} x {box.ylen:.3f} x {box.zlen:.3f} mm"
        )


if __name__ == "__main__":
    main()
