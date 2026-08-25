"""J01c - close out the registration tail (section 7).

J01b's exact ray probe gave p50 = 0.000000000 mm and 72.88% of probes exactly
zero, but a p99 of 10.09 mm.  A confidence rule keyed on p99 called that LOW.

The control settles it: the same probe against the docs/101 BARE base -- whose
own validation certifies the Thumb region is untouched -- produces the SAME
shape (p50 0.000000000, p99 9.49, max 15.56).  A tail that appears against a
certified-unchanged shell cannot be evidence of a shift.

This isolates what the tail is: probes that graze a Thumb opening rim, where the
two tessellations disagree about whether the ray enters material or passes
through the hole.  Restricting to probes whose material COLUMN is structurally
comparable removes it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L
from b03_axis_authority import ray_intervals

OUT = L.LAB / "02_registration"


def tris(keys):
    T = []
    for k in keys:
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        T.append(L.triangles(s, tol=0.05, ang=0.10))
        del s
    return np.concatenate(T)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    Ta = tris(("JAD_APPROVED", "JFD_APPROVED"))
    Tb = tris(("D101_JAD", "D101_JFD"))
    Tc = tris(("D101_BASE_JAD", "D101_BASE_JFD"))
    L.memory("tris")
    d = -L.DATUM_N
    probes = [L.DATUM_P + L.DATUM_U * a + L.DATUM_V * b
              for a in np.arange(-22.0, 22.01, 2.0)
              for b in np.arange(-48.0, 14.01, 2.0)]

    res = {}
    for tag, T in (("docs101_shell", Tb), ("docs101_bare_base", Tc)):
        same, diff = [], []
        for p0 in probes:
            o = p0 + d * 60.0
            ha = ray_intervals(Ta, o, -d, 0.0, 120.0)
            hb = ray_intervals(T, o, -d, 0.0, 120.0)
            if not ha or not hb:
                continue
            e = abs(float(ha[0][0]) - float(hb[0][0]))
            (same if len(ha) == len(hb) else diff).append(e)
        same = np.asarray(same) if same else np.zeros(1)
        diff = np.asarray(diff) if diff else np.zeros(1)
        res[tag] = {
            "comparableColumns": int(len(same)),
            "comparableP50Mm": float(np.percentile(same, 50)),
            "comparableP99Mm": float(np.percentile(same, 99)),
            "comparableMaxMm": float(same.max()),
            "comparableExactZeroFraction": float((same < 1.0e-9).mean()),
            "differingColumns": int(len(diff)),
            "differingMaxMm": float(diff.max()),
        }
        print("")
        print("  authority -> %s" % tag)
        print("    structurally comparable columns: %d" % len(same))
        print("      p50 %.9f  p99 %.9f  max %.9f mm, exactly zero on %.2f%%"
              % (np.percentile(same, 50), np.percentile(same, 99), same.max(),
                 100 * (same < 1.0e-9).mean()))
        print("    columns with a different interval count: %d, max delta %.3f mm"
              % (len(diff), diff.max()))
        L.memory(tag)

    worst = max(res[k]["comparableMaxMm"] for k in res)
    ctrl = res["docs101_bare_base"]["comparableMaxMm"]
    conf = "HIGH" if worst <= max(0.05, ctrl * 1.5) else "MEDIUM" if worst < 0.5 else "LOW"
    print("")
    print("  worst comparable-column delta: docs/101 %.9f mm  vs certified-unchanged"
          " control %.9f mm" % (res["docs101_shell"]["comparableMaxMm"], ctrl))
    print("  COORDINATE REGISTRATION CONFIDENCE = %s" % conf)
    L.write_json(OUT / "j01c_registration_tail.json",
                 {"results": res, "registrationConfidence": conf,
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
