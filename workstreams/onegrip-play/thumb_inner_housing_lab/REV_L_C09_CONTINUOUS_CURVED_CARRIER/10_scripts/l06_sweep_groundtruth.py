"""L06 - ground-truth withdrawal sweep against the FULL docs/101 shells.

L04's sweep used a Thumb-local crop for speed.  A crop can only ever UNDER-report
obstruction: if the body leaves the cropped region it looks free when it is not.
That does not threaten the FAIL verdict -- more obstruction cannot rescue it --
but it does threaten the "free from 18.0 mm" characterisation, so the number is
re-measured here with no crop at all.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from build123d import Location, Vector, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L

OUT = L.LAB / "04_validation"


def main() -> int:
    body, _ = L.as_single_solid(import_step(
        str(L.LAB / "03_full_c09" / "C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE.step")), "C09")
    sh = {}
    for t, k in (("JaD", "D101_JAD"), ("JfD", "D101_JFD")):
        sh[t], _ = L.as_single_solid(import_step(L.SRC[k]), t)
    print("C09 %.3f mm3 vs the FULL shells (no crop)" % L.vol(body))
    res = {}
    for dn, dv in (("+U", L.DATUM_U), ("-U", -L.DATUM_U)):
        for t, s in sh.items():
            v = []
            for k in np.arange(1.0, 25.01, 1.0):
                v.append(L.inter_vol(body.moved(Location(Vector(
                    *[float(x) for x in (dv * float(k))]))), s))
            v = np.asarray(v)
            free = None
            for i in range(len(v)):
                if v[i:].max() <= 1.0e-9:
                    free = float(i + 1.0)
                    break
            res["%s vs %s" % (dn, t)] = {
                "peakMm3": float(v.max()), "totalMm3": float(v.sum()),
                "obstructedSteps": int((v > 1.0e-9).sum()), "freeFromMm": free}
            print("  %-3s vs %-3s  peak %10.4f  total %11.4f  steps %2d  free from %s"
                  % (dn, t, v.max(), v.sum(), (v > 1.0e-9).sum(),
                     ("%.1f mm" % free) if free else "never"))
            L.memory("%s %s" % (dn, t))
    viable = [k for k, r in res.items()
              if r["peakMm3"] <= 0.05 and r["freeFromMm"] is not None
              and r["freeFromMm"] <= 8.0]
    print("  viable one-piece paths: %s" % (", ".join(viable) or "none"))
    L.write_json(OUT / "l06_sweep_groundtruth.json",
                 {"method": "full docs/101 shells, no crop, 1.0 mm steps",
                  "sweeps": res, "viablePaths": viable, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
