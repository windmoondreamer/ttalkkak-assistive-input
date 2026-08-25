"""I02b - opening bore profile per control, ORIGINAL and CURRENT (REV_I sections 5, 9).

I02 produced the finding that drives this whole revision: the inherited
"lowered" caps sit 4.12 - 7.18 mm BELOW the current outer skin instead of
1.07 - 1.46 mm above it.  Before any seat depth can be fixed, the shape of the
CURRENT opening has to be known -- specifically how deep the guided bore runs
before it opens into the cavity, because that is the only depth range in which
a cap is supported laterally.

Measurement method: from a point ON the axis at a given depth -- which is inside
the hole, i.e. in free space -- cast rays outward in the (ex, ey) plane and take
the first shell hit.

A rejected method is recorded because it produced a plausible-looking wrong
answer: taking the closest shell SAMPLE POINT in a thin slab perpendicular to
the axis.  On a curved panel with a tilted axis, outer-skin points a few mm to
the side share the same axial depth as the bore wall, so the "bore" came out at
2.59 - 3.01 mm half-width on the two corner buttons -- narrower than the cap
that demonstrably fits through it.  It was measuring the skin, not the bore.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from i02_original_external_stack import frame, skin_reference  # noqa: E402

OUT = L.LAB / "02_original_external_stack"
STEP = 0.25
NDIR = 72
BORE_LIMIT = 6.0     # a min half-width above this is cavity, not a guiding bore
DEPTH = 14.0


def bore_profile(T, cen, w, ex, ey, skin):
    """Bore half-width vs depth, by lateral ray casting from the axis."""
    dirs = [(float(np.cos(a)), float(np.sin(a)))
            for a in np.arange(0.0, 2 * np.pi - 1e-9, 2 * np.pi / NDIR)]
    rows = []
    for z in np.arange(skin - DEPTH, skin - 0.10 + 1e-9, STEP):
        o = cen + w * z
        rr = []
        for cx, cy in dirs:
            h = ray_intervals(T, o, ex * cx + ey * cy, 0.0, 20.0)
            if h:
                rr.append(float(h[0][0]))
        if len(rr) < NDIR // 2:
            rows.append((float(z), float("nan"), float("nan")))
            continue
        rr = np.asarray(rr)
        rows.append((float(z), float(rr.min()), float(np.median(rr))))
    return rows


def run(keys, cart_key, centre, tag):
    T = []
    for k in keys:
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        T.append(L.triangles(s, tol=0.06, ang=0.12))
        del s
    T = np.concatenate(T)
    print("%-9s shell: %d triangles" % (tag, len(T)))
    L.memory(tag + " shell")

    _, cart = leaf_parts(cart_key)
    res = {}
    print("")
    print("=== %s opening bore, down each true press axis ===" % tag)
    print("%-5s %9s %9s %9s %9s %9s"
          % ("ctrl", "skin", "boreDeep", "minHalfW", "medHalfW", "capHalfW"))
    for short in ORDER:
        if short == "JOY":
            continue
        lab = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[lab], short)
        w, _, tilt = true_axis(cap)
        Pc = L.surf_points(cap, 40000, tol=0.05)
        cen = Pc.mean(axis=0)
        ex, ey = frame(w)
        cx, cy = (Pc - cen) @ ex, (Pc - cen) @ ey
        r_cap = float(np.hypot(cx, cy).max())
        cap_half = float(max(np.abs(cx).max(), np.abs(cy).max()))
        skin = skin_reference(T, cen, w, ex, ey, r_cap)["referenceMm"]
        prof = bore_profile(T, cen, w, ex, ey, skin)

        end = None
        for z, mn, _md in sorted(prof, key=lambda t: -t[0]):
            if not np.isfinite(mn) or mn > BORE_LIMIT:
                end = float(z)
                break
        depth = (skin - end) if end is not None else DEPTH
        band = [(mn, md) for z, mn, md in prof
                if (end if end is not None else skin - DEPTH) < z < skin - 0.2
                and np.isfinite(mn)]
        mn = float(min(b[0] for b in band)) if band else float("nan")
        md = float(np.median([b[1] for b in band])) if band else float("nan")
        s = (Pc - cen) @ w
        res[short] = {"tiltDeg": tilt, "axisWorld": w.tolist(),
                      "capCentreWorld": cen.tolist(),
                      "outerSkinOnAxisMm": skin,
                      "guidedBoreDepthMm": depth, "boreEndAxisMm": end,
                      "minBoreHalfWidthMm": mn, "medianBoreHalfWidthMm": md,
                      "capHalfWidthMm": cap_half,
                      "capHeightMm": float(s.max() - s.min()),
                      "profile": [{"nMm": z, "minHalfWidthMm": a,
                                   "medianHalfWidthMm": b} for z, a, b in prof]}
        print("%-5s %9.3f %9.3f %9.3f %9.3f %9.3f"
              % (short, skin, depth, mn, md, cap_half))
        del cap
        L.memory("%s bore %s" % (tag, short))
    return res


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    orig = run(("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER"),
               "ORIGINAL_THUMB_CARTRIDGE", L.DATUM_P - L.THUMB_DELTA, "ORIGINAL")
    cur = run(("JAD_APPROVED", "JFD_APPROVED"),
              "LOWERED_ORIGINAL_THUMB_CARTRIDGE", L.DATUM_P, "CURRENT")

    print("")
    print("=== bore comparison ===")
    print("%-5s %10s %10s %10s %10s"
          % ("ctrl", "orig deep", "curr deep", "orig halfW", "curr halfW"))
    for k in [x for x in ORDER if x != "JOY"]:
        print("%-5s %10.3f %10.3f %10.3f %10.3f"
              % (k, orig[k]["guidedBoreDepthMm"], cur[k]["guidedBoreDepthMm"],
                 orig[k]["minBoreHalfWidthMm"], cur[k]["minBoreHalfWidthMm"]))
    od = np.array([orig[k]["guidedBoreDepthMm"] for k in orig])
    cd = np.array([cur[k]["guidedBoreDepthMm"] for k in cur])
    oh = np.array([orig[k]["minBoreHalfWidthMm"] for k in orig])
    ch = np.array([cur[k]["minBoreHalfWidthMm"] for k in cur])
    cw = np.array([cur[k]["capHalfWidthMm"] for k in cur])
    print("  guided depth  ORIGINAL %.3f-%.3f   CURRENT %.3f-%.3f"
          % (od.min(), od.max(), cd.min(), cd.max()))
    print("  min half-width ORIGINAL %.3f-%.3f   CURRENT %.3f-%.3f   cap %.3f-%.3f"
          % (oh.min(), oh.max(), ch.min(), ch.max(), cw.min(), cw.max()))
    print("  CURRENT side clearance to the original cap: min %.3f  max %.3f"
          % ((ch - cw).min(), (ch - cw).max()))

    L.write_json(OUT / "i02b_opening_bore_profile.json",
                 {"stepMm": STEP, "directions": NDIR, "boreLimitMm": BORE_LIMIT,
                  "ORIGINAL": orig, "CURRENT": cur,
                  "currentSideClearanceMm": {"minMm": float((ch - cw).min()),
                                             "maxMm": float((ch - cw).max())},
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
