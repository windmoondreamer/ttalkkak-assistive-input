"""H05 - validate the seat-first carrier (REV_H section 18)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import ORDER  # noqa: E402
from d02_housing_vs_exact import Field, approved_shell  # noqa: E402
from h01_seat_audit import axis_frame  # noqa: E402
from h03_placement import (BODY_HI, BODY_LO, HARNESS_MM, KEEPOUTS, PLATE_T,
                           POCKET_XY, TERM_LO, TERM_XY)  # noqa: E402
from h04_carrier import SLOT_L, SLOT_OFFSET, SLOT_W  # noqa: E402

OUT = L.LAB / "05_validation"
CAND = L.LAB / "04_carrier" / "C05_SEAT_FIRST_CARRIER.step"
MIN_WALL, PREF_WALL = 1.20, 1.60
PITCH = 0.20


def main() -> int:
    approved = approved_shell()
    car = import_step(str(CAND))
    car, _ = L.as_single_solid(car, "C05")
    pl = json.loads((L.LAB / "03_placement" / "h03_placement.json").read_text(encoding="utf-8"))
    names = [s for s in ORDER if s != "JOY"]
    print("C05: solids %d  valid %s  faces %d  vol %.3f mm3"
          % (len(list(car.solids())), bool(car.is_valid), len(list(car.faces())), L.vol(car)))
    print("interference with the exact approved shell = %.6f mm3" % L.inter_vol(car, approved))

    # ---- per-seat bearing area still present ----------------------------
    print("\n=== per-seat support after all cuts ===")
    print("%-5s %12s %12s %12s %10s" % ("ctrl", "bearing mm2", "of 6.04x6.04",
                                        "slots open", "verdict"))
    rows = {}
    Tc = L.triangles(car, tol=0.05, ang=0.10)
    for short in names:
        r = pl["buttons"][short]
        w = np.asarray(r["axisWorld"], float)
        top = np.asarray(r["plateTopWorld"], float)
        ex, ey = axis_frame(w)
        d = L.triangles(car, tol=0.05, ang=0.10).reshape(-1, 3) - top
        loc = np.stack([d @ ex, d @ ey, d @ w], axis=1).reshape(-1, 3, 3)
        f = Field(loc)
        # bearing area: material immediately under the switch body footprint
        X = np.arange(-3.2, 3.2001, 0.1)
        Y = np.arange(-3.2, 3.2001, 0.1)
        bear = 0
        cellb = 0.1 * 0.1
        for x in X:
            for y in Y:
                h = f.hits(float(x), float(y))
                if h.size and h.size % 2 == 0 and h.max() > -0.05:
                    bear += 1
        bearing = bear * cellb
        # terminal slots still open?
        openslots = 0
        for sgn in (-1.0, 1.0):
            cnt = 0
            for yy in np.linspace(-SLOT_L / 2 + 0.4, SLOT_L / 2 - 0.4, 9):
                h = f.hits(sgn * SLOT_OFFSET, float(yy))
                if h.size == 0:
                    cnt += 1
            if cnt >= 7:
                openslots += 1
        full = 6.04 * 6.04
        v = ("OK" if bearing >= 0.5 * full and openslots == 2 else
             "REDUCED" if bearing > 0.2 * full else "LOST")
        rows[short] = {"bearingAreaMm2": bearing, "fullFootprintMm2": full,
                       "bearingFraction": bearing / full, "openSlots": openslots,
                       "verdict": v}
        print("%-5s %12.2f %11.1f%% %12d %10s"
              % (short, bearing, 100 * bearing / full, openslots, v))
        L.memory("seat " + short)

    # ---- thickness ------------------------------------------------------
    U = np.arange(-24.0, 24.0 + 1e-9, PITCH)
    V = np.arange(-52.0, 16.0 + 1e-9, PITCH)
    f = Field(L.local_triangles(car, tol=0.05, ang=0.10))
    t = np.zeros((len(U), len(V)))
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            h = f.hits(u, v)
            if h.size and h.size % 2 == 0:
                t[i, j] = float(sum(h[k + 1] - h[k] for k in range(0, h.size, 2)))
    plate = t > 1e-6
    cell = PITCH * PITCH
    _p = np.pad(plate, 1, mode="constant", constant_values=False)
    ed = ndimage.distance_transform_edt(_p, sampling=PITCH)[1:-1, 1:-1]
    thin = plate & (t < MIN_WALL)
    print("\n=== structural thickness ===")
    print("  plan area %.2f mm2   thickness p25/p50/p75 = %.3f / %.3f / %.3f mm"
          % (plate.sum() * cell, *[float(np.percentile(t[plate], q)) for q in (25, 50, 75)]))
    print("  area below %.2f mm : %.2f mm2   below %.2f mm : %.2f mm2"
          % (MIN_WALL, thin.sum() * cell, PREF_WALL,
             float((plate & (t < PREF_WALL)).sum()) * cell))
    print("  minimum %.4f mm   interior (>1 mm from an edge) thin area %.2f mm2"
          % (float(t[plate].min()), float((thin & (ed > 1.0)).sum()) * cell))

    # ---- keep-outs ------------------------------------------------------
    print("\n=== keep-outs ===")
    keep = import_step(str(KEEPOUTS))
    ko, harness = {}, 0.0
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if not ch.solids() or lab.startswith("CAP_"):
            continue
        s, _ = L.as_single_solid(ch, lab)
        v = L.inter_vol(car, s)
        ko[lab] = v
        if v > 1e-6:
            print("  !! %-34s %12.6f mm3" % (lab[:34], v))
        if "CARRIER" in lab.upper() or "N1_N2" in lab.upper():
            for k in range(1, int(HARNESS_MM) + 1):
                harness += L.inter_vol(car, s.moved(Location(Vector(
                    *[float(x) for x in (L.DATUM_N * float(k))]))))
        del s
    if all(v <= 1e-6 for v in ko.values()):
        print("  all keep-outs clear (0.000000 mm3)")
    print("  rear four-edge-harness corridor (%.0f mm) = %.6f mm3" % (HARNESS_MM, harness))

    L.write_json(OUT / "h05_validate.json",
                 {"solids": len(list(car.solids())), "valid": bool(car.is_valid),
                  "volumeMm3": L.vol(car), "faces": len(list(car.faces())),
                  "shellInterferenceMm3": L.inter_vol(car, approved),
                  "seats": rows,
                  "planAreaMm2": plate.sum() * cell,
                  "thicknessPercentiles": {str(q): float(np.percentile(t[plate], q))
                                           for q in (25, 50, 75)},
                  "areaBelowMinWallMm2": thin.sum() * cell,
                  "areaBelowPrefWallMm2": float((plate & (t < PREF_WALL)).sum()) * cell,
                  "minThicknessMm": float(t[plate].min()),
                  "interiorThinMm2": float((thin & (ed > 1.0)).sum()) * cell,
                  "keepOutMm3": ko, "harnessCorridorMm3": harness,
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
