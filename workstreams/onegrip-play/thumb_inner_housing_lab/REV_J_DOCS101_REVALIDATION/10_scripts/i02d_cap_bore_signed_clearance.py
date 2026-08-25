"""I02d - signed cap-to-bore clearance at the restored protrusion (REV_I section 9, 18).

I02c showed the ORIGINAL caps, slid outward 5.57 - 8.38 mm to restore the
ORIGINAL protrusion law, overlap the CURRENT shell by 0.89 - 9.47 mm3.  A volume
does not say whether that is a 0.05 mm rub (CLASS B, hand-finishable) or a
1 mm interference (CLASS A, must be solved in CAD), so this measures the signed
gap directly.

Method, per button, at several depths inside the opening:
  * shell side  -- cast a ray from the axis outward in 72 directions and take
    the first hit.  The origin is inside the hole, so it is in free space.
  * cap side    -- take the cap surface points, bin by angle in the SAME frame
    and take the max radius per bin.  Casting at the cap does not work: the
    origin is inside the cap solid, so ray_intervals sees an odd number of
    crossings and returns None.
  * clearance   -- shell radius minus cap radius, per direction.

Depths start 1.0 mm below the skin.  Closer than that, a lateral ray can start
outside the material on a curved panel and return the OUTER skin instead of the
bore wall, which is what made an earlier bore measurement report a hole narrower
than the cap that visibly passes through it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402

OUT = L.LAB / "02_original_external_stack"
NDIR = 72
SKIN_MARGIN = 1.0
HAND_FINISH_LIMIT = 0.60   # section 18: local sub-mm non-structural rub


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pl = json.loads((OUT / "i02c_source_faithful_cap_placement.json").read_text(encoding="utf-8"))

    T = []
    for k in ("JAD_APPROVED", "JFD_APPROVED"):
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        T.append(L.triangles(s, tol=0.06, ang=0.12))
        del s
    T = np.concatenate(T)
    print("approved shell: %d triangles" % len(T))
    L.memory("shell")

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    ang = np.arange(0.0, 2 * np.pi - 1e-9, 2 * np.pi / NDIR)
    rows = {}
    print("")
    print("=== signed cap-to-bore clearance at the restored protrusion ===")
    print("%-5s %10s %10s %10s %10s %9s  %s"
          % ("ctrl", "minClr", "p05Clr", "medianClr", "worstDepth", "negFrac", "class"))
    for short in ORDER:
        if short == "JOY":
            continue
        b = pl["buttons"][short]
        lab = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[lab], short)
        w = np.asarray(b["axisWorld"], float)
        cen = np.asarray(b["capCentreWorld"], float)
        ex, ey = frame(w)
        P = L.surf_points(cap, 120000, tol=0.03) + w * b["axialShiftOutwardMm"]
        d = P - cen
        s = d @ w
        x, y = d @ ex, d @ ey
        r = np.hypot(x, y)
        pa = np.arctan2(y, x)
        skin = b["currentSkinOnAxisMm"]
        cap_top, cap_und = float(s.max()), float(s.min())

        lo = cap_und + 0.25
        hi = min(cap_top - 0.25, skin - SKIN_MARGIN)
        if hi <= lo:
            hi = lo + 0.25
        clr, detail = [], []
        for z in np.arange(lo, hi + 1e-9, 0.30):
            o = cen + w * z
            m = np.abs(s - z) < 0.30
            if m.sum() < 200:
                continue
            ab = np.floor((pa[m] + np.pi) / (2 * np.pi) * NDIR).astype(int) % NDIR
            rm = r[m]
            for i, a in enumerate(ang):
                sel = ab == i
                if sel.sum() < 3:
                    continue
                h = ray_intervals(T, o, ex * np.cos(a) + ey * np.sin(a), 0.0, 20.0)
                if not h:
                    continue
                g = float(h[0][0]) - float(rm[sel].max())
                clr.append(g)
                detail.append((float(z), float(np.degrees(a)), g))
        if not clr:
            print("%-5s   no samples" % short)
            del cap
            continue
        c = np.asarray(clr)
        worst = min(detail, key=lambda t: t[2])
        cls = ("CLASS B - HAND FINISHABLE" if c.min() >= -HAND_FINISH_LIMIT
               else "CLASS A - MUST SOLVE IN CAD")
        rows[short] = {"minClearanceMm": float(c.min()),
                       "p05ClearanceMm": float(np.percentile(c, 5)),
                       "medianClearanceMm": float(np.median(c)),
                       "maxClearanceMm": float(c.max()),
                       "negativeFraction": float((c < 0).mean()),
                       "worstDepthBelowSkinMm": skin - worst[0],
                       "worstAngleDeg": worst[1], "samples": int(c.size),
                       "classification": cls}
        print("%-5s %10.4f %10.4f %10.4f %10.3f %8.1f%%  %s"
              % (short, c.min(), np.percentile(c, 5), np.median(c),
                 skin - worst[0], 100 * (c < 0).mean(), cls))
        del cap
        L.memory("clr " + short)

    mn = np.array([rows[k]["minClearanceMm"] for k in rows])
    print("")
    print("=== summary ===")
    print("  worst signed clearance over all eight buttons: %.4f mm" % mn.min())
    print("  buttons with any overlap: %d of %d"
          % (int(sum(1 for k in rows if rows[k]["minClearanceMm"] < 0)), len(rows)))
    verdict = ("CAP-SIDE CLEARANCE IS CLASS B - HAND FINISHABLE"
               if mn.min() >= -HAND_FINISH_LIMIT else
               "CAP-SIDE CLEARANCE IS CLASS A - MUST SOLVE IN CAD")
    print("  -> %s (limit %.2f mm)" % (verdict, HAND_FINISH_LIMIT))
    print("  note: the OPENING is frozen, so the fix is on the CAP, which is a")
    print("  printed part and is not frozen (docs/73 allows cap-side changes).")

    L.write_json(OUT / "i02d_cap_bore_signed_clearance.json",
                 {"directions": NDIR, "skinMarginMm": SKIN_MARGIN,
                  "handFinishLimitMm": HAND_FINISH_LIMIT,
                  "buttons": rows, "worstClearanceMm": float(mn.min()),
                  "verdict": verdict, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
