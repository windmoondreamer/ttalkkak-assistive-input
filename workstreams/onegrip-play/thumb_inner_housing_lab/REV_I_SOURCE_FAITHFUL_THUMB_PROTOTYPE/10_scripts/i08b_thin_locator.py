"""I08b - locate the thin regions the validator flags (REV_I sections 20, 29).

I08 reports an interior area below 1.20 mm but not where it is, and "thin" in a
column sum can mean several different things.  This attributes every thin cell
to a feature so the fix is aimed at the right place.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import ORDER  # noqa: E402
from d02_housing_vs_exact import Field  # noqa: E402
from h03_placement import seat_solids  # noqa: E402

OUT = L.LAB / "08_validation"
MIN_WALL = 1.20
PITCH = 0.20


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core = json.loads((L.LAB / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.LAB / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    car, _ = L.as_single_solid(import_step(
        str(L.LAB / "07_prototype" / (sys.argv[sys.argv.index("--cand") + 1]
            if "--cand" in sys.argv else "C06_SOURCE_FAITHFUL_THUMB_CORE.step"))), "CAND")
    f = Field(L.local_triangles(car, tol=0.05, ang=0.10))
    U = np.arange(-26.0, 26.0 + 1e-9, PITCH)
    V = np.arange(-54.0, 18.0 + 1e-9, PITCH)
    t = np.zeros((len(U), len(V)))
    nseg = np.zeros((len(U), len(V)), int)
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            h = f.hits(u, v)
            if h.size and h.size % 2 == 0:
                t[i, j] = float(sum(h[k + 1] - h[k] for k in range(0, h.size, 2)))
                nseg[i, j] = h.size // 2
    plan = t > 1e-6
    cell = PITCH * PITCH
    pad = np.pad(plan, 1, mode="constant", constant_values=False)
    ed = ndimage.distance_transform_edt(pad, sampling=PITCH)[1:-1, 1:-1]
    thin = plan & (t < MIN_WALL) & (ed > 1.0)
    print("plan %.1f mm2, interior thin %.2f mm2, %d cells"
          % (plan.sum() * cell, thin.sum() * cell, int(thin.sum())))

    lab, n = ndimage.label(thin)
    names = [x for x in ORDER if x != "JOY"]
    seats = {}
    for s in names:
        r = core["seats"][s]
        u = seat_solids(np.asarray(r["capUndersideWorld"], float),
                        np.asarray(r["axisWorld"], float), s)
        seats[s] = L.to_local(np.asarray([r["plateTopWorld"]], float))[0]
    jl = L.to_local(np.asarray([joyj["knobCentreWorld"]], float))[0]

    print("")
    print("%-4s %9s %9s %8s %8s %9s %7s  %s"
          % ("id", "area", "minT", "u", "v", "segments", "edge", "nearest feature"))
    rows = []
    for k in range(1, n + 1):
        m = lab == k
        a = float(m.sum()) * cell
        if a < 0.20:
            continue
        iu, iv = np.nonzero(m)
        cu, cv = float(U[iu].mean()), float(V[iv].mean())
        best, bd = "joystick deck", float(np.hypot(cu - jl[0], cv - jl[1]))
        for s, p in seats.items():
            d = float(np.hypot(cu - p[0], cv - p[1]))
            if d < bd:
                best, bd = "seat " + s, d
        rows.append({"areaMm2": a, "minThicknessMm": float(t[m].min()),
                     "uMm": cu, "vMm": cv, "segments": int(np.median(nseg[m])),
                     "edgeDistanceMm": float(ed[m].max()),
                     "nearestFeature": best, "featureDistanceMm": bd})
        print("%-4d %9.2f %9.3f %8.2f %8.2f %9d %7.2f  %s (%.1f mm)"
              % (k, a, t[m].min(), cu, cv, int(np.median(nseg[m])),
                 float(ed[m].max()), best, bd))
    rows.sort(key=lambda r: -r["areaMm2"])
    tot = sum(r["areaMm2"] for r in rows)
    print("")
    print("  %d clusters >= 0.20 mm2, total %.2f mm2" % (len(rows), tot))
    if rows:
        print("  largest cluster %.2f mm2 at u %.2f v %.2f, %d material segment(s)"
              % (rows[0]["areaMm2"], rows[0]["uMm"], rows[0]["vMm"], rows[0]["segments"]))
        print("  a single-segment thin column is genuinely thin material;")
        print("  a multi-segment column is two thin skins stacked, e.g. a standoff")
        print("  pad over the plate, and is not a wall-thickness problem.")
    L.write_json(OUT / "i08b_thin_locator.json",
                 {"pitchMm": PITCH, "minWallMm": MIN_WALL,
                  "planAreaMm2": float(plan.sum()) * cell,
                  "interiorThinMm2": float(thin.sum()) * cell,
                  "clusters": rows, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
