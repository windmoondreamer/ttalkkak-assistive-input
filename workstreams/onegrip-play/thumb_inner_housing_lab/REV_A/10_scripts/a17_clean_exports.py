"""A17 - RETIRED.  The hypothesis it tested was wrong.

Hypothesis: the 22 MB C01 STEP was fat because tessellation had been serialised
into it (a trap already recorded in CLAUDE.md), so BRepTools.Clean_s before
export would shrink it.

Measured result: FALSE for this Lab.
  * export_step on the imported shape fails outright ("Failed to write STEP
    file"); it only succeeds after the shape is rebuilt via as_single_solid.
  * after Clean_s AND a successful rebuild the file is 21.85 MB, i.e.
    essentially unchanged from 22.40 MB.

So the size is genuine B-rep weight, not a mesh: the C01 outer face is inherited
from the grip's lofted NURBS surfaces, and 291 such faces carry a lot of pole
data.  Nothing to fix.  Kept as a record so the same hypothesis is not retried.
"""
from __future__ import annotations

import sys
from pathlib import Path

from build123d import export_step, export_stl, import_step
from OCP.BRepTools import BRepTools

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402

TARGETS = [
    L.LAB / "09_exports" / "C01_SOURCE_FAITHFUL_REBASE.step",
    L.LAB / "07_candidates" / "C01_stage3_conformal_plate.step",
    L.LAB / "07_candidates" / "C01_stage1_cleared_gap.step",
    L.LAB / "02_reference_copies" / "FROZEN_THUMB_LOCAL_CROP_SOLID.step",
    L.LAB / "02_reference_copies" / "COMBINED_FROZEN_THUMB_CROP.step",
    L.LAB / "02_reference_copies" / "COMBINED_CLEAN_THUMB_CROP.step",
    L.LAB / "02_reference_copies" / "COMBINED_FINGER_V2_THUMB_CROP.step",
    L.LAB / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step",
]


def main() -> int:
    for p in TARGETS:
        if not p.exists():
            print("  skip (missing) %s" % p.name)
            continue
        before = p.stat().st_size
        shape = import_step(str(p))
        v0 = float(sum(float(s.volume) for s in shape.solids()))
        f0 = len(list(shape.faces()))
        e0 = len(list(shape.edges()))
        BRepTools.Clean_s(shape.wrapped)
        # Never write straight back over the source path: export_step raised
        # "Failed to write STEP file" doing that.  Write a sibling temp, verify
        # it, then replace.  The original is only removed after the check passes.
        tmp = p.with_suffix(".step.tmp")
        export_step(shape, str(tmp))
        after = tmp.stat().st_size
        chk = import_step(str(tmp))
        v1 = float(sum(float(s.volume) for s in chk.solids()))
        f1 = len(list(chk.faces()))
        e1 = len(list(chk.edges()))
        ok = abs(v1 - v0) < 1.0e-6 and f1 == f0 and e1 == e0
        print("  %-44s %8.1f MB -> %6.2f MB  dVol=%.3e  faces %d->%d edges %d->%d  %s"
              % (p.name[:44], before / 1e6, after / 1e6, abs(v1 - v0), f0, f1, e0, e1,
                 "OK" if ok else "MISMATCH"))
        if not ok:
            tmp.unlink(missing_ok=True)
            raise RuntimeError("cleaning changed the geometry of " + p.name)
        del shape, chk
        p.unlink()
        tmp.replace(p)
        L.memory("cleaned " + p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
