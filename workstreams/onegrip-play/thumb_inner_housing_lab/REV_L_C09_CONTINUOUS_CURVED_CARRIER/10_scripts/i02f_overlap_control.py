"""I02f - control experiment for the cap/shell overlap (REV_I sections 9, 18).

I02d and I02e both concluded CLASS A from measurements that compared a ray cast
from the axis against the maximum cap radius inside an angular bin.  A polar dump
showed why that is not trustworthy: on a square cap the radius swings from
3.80 mm on an axis to 5.37 mm at a corner, so the ray and the cap maximum are at
different angles inside the same bin.  Run on the ORIGINAL cap in the ORIGINAL
shell -- an assembly that demonstrably works -- the same metric reports
clearances of -0.51, -1.07, -1.65 mm.  A metric that condemns the known-good
reference is measuring itself, not the geometry.

So this is the control: the SAME exact boolean test applied to three cases.

  A  ORIGINAL cap   in ORIGINAL shell   -- the design reference
  B  LOWERED cap    in CURRENT shell    -- what REV_H inherited
  C  RESTORED cap   in CURRENT shell    -- the source-faithful proposal

Case C is only a problem if it is materially worse than case A.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402

OUT = L.LAB / "02_original_external_stack"


def shell_solids(keys):
    out = []
    for k in keys:
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        out.append(s)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pl = json.loads((OUT / "i02c_source_faithful_cap_placement.json").read_text(encoding="utf-8"))

    orig_sh = shell_solids(("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER"))
    cur_sh = shell_solids(("JAD_APPROVED", "JFD_APPROVED"))
    L.memory("shells")
    _, orig_cart = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    _, cur_cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")

    rows = {}
    print("")
    print("=== control: exact cap/shell overlap in three configurations ===")
    print("%-5s %14s %14s %14s %12s"
          % ("ctrl", "A orig/orig", "B lowered/cur", "C restored/cur", "C - A"))
    for short in ORDER:
        if short == "JOY":
            continue
        lab = next(k for k, v in NAME_MAP.items() if v == short)
        co, _ = L.as_single_solid(orig_cart[lab], short + "_o")
        cc, _ = L.as_single_solid(cur_cart[lab], short + "_c")
        b = pl["buttons"][short]
        w = np.asarray(b["axisWorld"], float)
        mv = cc.moved(Location(Vector(*[float(x) for x in (w * b["axialShiftOutwardMm"])])))

        a = sum(L.inter_vol(co, s) for s in orig_sh)
        bb = sum(L.inter_vol(cc, s) for s in cur_sh)
        c = sum(L.inter_vol(mv, s) for s in cur_sh)
        rows[short] = {"A_originalCap_originalShellMm3": a,
                       "B_loweredCap_currentShellMm3": bb,
                       "C_restoredCap_currentShellMm3": c,
                       "C_minus_A_Mm3": c - a,
                       "axialShiftOutwardMm": b["axialShiftOutwardMm"]}
        print("%-5s %14.4f %14.4f %14.4f %12.4f" % (short, a, bb, c, c - a))
        del co, cc, mv
        L.memory("control " + short)

    A = np.array([rows[k]["A_originalCap_originalShellMm3"] for k in rows])
    B = np.array([rows[k]["B_loweredCap_currentShellMm3"] for k in rows])
    C = np.array([rows[k]["C_restoredCap_currentShellMm3"] for k in rows])
    print("")
    print("=== summary ===")
    print("  A  ORIGINAL cap in ORIGINAL shell : total %8.4f  max %7.4f mm3" % (A.sum(), A.max()))
    print("  B  LOWERED  cap in CURRENT  shell : total %8.4f  max %7.4f mm3" % (B.sum(), B.max()))
    print("  C  RESTORED cap in CURRENT  shell : total %8.4f  max %7.4f mm3" % (C.sum(), C.max()))
    worse = float((C - A).max())
    print("  worst button-level excess of C over the design reference A: %+.4f mm3" % worse)
    if C.max() <= max(1.0, A.max() * 3.0):
        verdict = "RESTORED CAP FIT IS COMPARABLE TO THE ORIGINAL - CLASS B AT WORST"
    else:
        verdict = "RESTORED CAP FIT IS MATERIALLY WORSE THAN THE ORIGINAL - CLASS A"
    print("  -> %s" % verdict)

    L.write_json(OUT / "i02f_overlap_control.json",
                 {"buttons": rows,
                  "totals": {"A": float(A.sum()), "B": float(B.sum()), "C": float(C.sum())},
                  "maxima": {"A": float(A.max()), "B": float(B.max()), "C": float(C.max())},
                  "worstExcessOverReferenceMm3": worse,
                  "verdict": verdict, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
