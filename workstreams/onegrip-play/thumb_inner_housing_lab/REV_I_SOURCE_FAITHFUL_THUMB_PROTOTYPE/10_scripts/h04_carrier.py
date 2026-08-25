"""H04 - seat-first common carrier (REV_H sections 10-13).

Construction order is seat-first, never shell-offset-first:

    CURRENT FROZEN OPENINGS -> ORIGINAL-STYLE SEATS -> seat islands
    -> structural webs -> common carrier -> shell connection regions

Each island reproduces the ORIGINAL plate locally: 2.003 mm thick, its top face
4.759 mm below that button's cap underside, with the original two terminal slots.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import (Align, Box, Compound, Location, Plane, Vector,
                       export_step, export_stl, import_step)
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import true_axis  # noqa: E402
from d02_housing_vs_exact import Field, approved_shell  # noqa: E402
from h01_seat_audit import axis_frame  # noqa: E402
from h03_placement import (ACT_D, BODY_HI, BODY_LO, CAP_TO_PLATE, HARNESS_MM,
                           KEEPOUTS, PLATE_T, POCKET_XY, SEAT_PATCH, TERM_LO,
                           TERM_XY)  # noqa: E402

OUT = L.LAB / "04_carrier"
OUTWARD = -L.DATUM_N
ISLAND = 11.0
WEB_W = 4.0
SLOT_OFFSET = 2.60           # H01: terminal slots at +-2.6 mm from the axis
SLOT_W, SLOT_L = 1.30, 6.40  # H01 measured slot size
KEEPOUT_CLR = 0.50
SCREW_CLR = 1.00
PITCH = 0.25


def plane_box(origin, ex, w, sx, sy, n0, n1, label):
    pl = Plane(origin=L.xyz(origin + w * n0), x_dir=L.xyz(ex), z_dir=L.xyz(w))
    s = pl * Box(sx, sy, n1 - n0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s.label = label
    return s


def main() -> int:
    stage = int(sys.argv[sys.argv.index("--stage") + 1]) if "--stage" in sys.argv else 99
    approved = approved_shell()
    pl = json.loads((L.LAB / "03_placement" / "h03_placement.json").read_text(encoding="utf-8"))
    names = [s for s in ORDER if s != "JOY"]

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    seats = {}
    for short in names:
        r = pl["buttons"][short]
        w = np.asarray(r["axisWorld"], float)
        top = np.asarray(r["plateTopWorld"], float)
        ex, ey = axis_frame(w)
        seats[short] = {"w": w, "top": top, "ex": ex, "ey": ey}

    # ---- 1 : seat islands ------------------------------------------------
    isl = []
    for short in names:
        s = seats[short]
        isl.append(plane_box(s["top"], s["ex"], s["w"], ISLAND, ISLAND,
                             -PLATE_T, 0.0, "ISL_" + short))
    car = isl[0]
    for x in isl[1:]:
        car = (car + x).clean()
    car, n0 = L.as_single_solid(car, "CARRIER")
    print("stage 1 islands: vol=%.3f  solids=%d" % (L.vol(car), len(list(car.solids()))))
    L.memory("islands")
    if stage < 2:
        return 0

    # ---- 2 : structural webs where islands do not already meet ----------
    pieces = list(car.solids())
    if len(pieces) > 1:
        print("  islands form %d groups -> adding webs" % len(pieces))
    webs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = seats[names[i]], seats[names[j]]
            d = float(np.linalg.norm(a["top"] - b["top"]))
            if d > 26.0:
                continue
            if L.inter_vol(isl[i], isl[j]) > 1.0:
                continue
            mid = 0.5 * (a["top"] + b["top"])
            axis = L.unit(b["top"] - a["top"])
            w = L.unit(a["w"] + b["w"])
            ex = L.unit(axis - w * float(axis @ w))
            ey = np.cross(w, ex)
            pw = Plane(origin=L.xyz(mid - w * PLATE_T), x_dir=L.xyz(ex), z_dir=L.xyz(w))
            box = pw * Box(d, WEB_W, PLATE_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
            box.label = "WEB_%s_%s" % (names[i], names[j])
            webs.append(box)
    print("stage 2 webs: %d" % len(webs))
    for b in webs:
        car = (car + b).clean()
    car, _ = L.as_single_solid(car, "CARRIER")
    print("  vol=%.3f  solids=%d" % (L.vol(car), len(list(car.solids()))))
    L.memory("webs")
    if stage < 3:
        return 0

    # ---- 3 : original terminal slots ------------------------------------
    slots = 0
    for short in names:
        s = seats[short]
        for sgn in (-1.0, 1.0):
            o = s["top"] + s["ex"] * (sgn * SLOT_OFFSET)
            tool = plane_box(o, s["ex"], s["w"], SLOT_W, SLOT_L,
                             -PLATE_T - 1.0, 1.0, "SLOT")
            if L.inter_vol(car, tool) > 1e-9:
                car = (car - tool).clean()
                car, _ = L.as_single_solid(car, "CARRIER")
                slots += 1
    print("stage 3 terminal slots cut: %d" % slots)
    L.memory("slots")
    if stage < 4:
        return 0

    # ---- 4 : keep-outs and the rear harness corridor --------------------
    keep = import_step(str(KEEPOUTS))
    ko = {}
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if not ch.solids() or lab.startswith("CAP_"):
            continue
        s, _ = L.as_single_solid(ch, lab)
        clr = SCREW_CLR if "SCREW" in lab.upper() else KEEPOUT_CLR
        removed = 0.0
        tools = [s] + [s.moved(Location(Vector(*[float(x) for x in (d * clr)])))
                       for d in (L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V,
                                 -L.DATUM_N, L.DATUM_N)]
        if "CARRIER" in lab.upper() or "N1_N2" in lab.upper():
            tools += [s.moved(Location(Vector(*[float(x) for x in (L.DATUM_N * float(k))])))
                      for k in range(1, int(HARNESS_MM) + 1)]
        for t in tools:
            v = L.inter_vol(car, t)
            if v > 1e-9:
                removed += v
                car = (car - t).clean()
                car, _ = L.as_single_solid(car, "CARRIER")
        ko[lab] = removed
        if removed > 1e-9:
            print("   keep-out %-34s removed %9.4f mm3" % (lab[:34], removed))
        del s

    # shell guard
    before = L.vol(car)
    for d in (np.zeros(3), L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V):
        t = approved if not np.any(d) else approved.moved(
            Location(Vector(*[float(x) for x in (d * 0.30)])))
        v = L.inter_vol(car, t)
        if v > 1e-9:
            car = (car - t).clean()
            car, _ = L.as_single_solid(car, "CARRIER")
    print("   shell guard removed %.4f mm3" % (before - L.vol(car)))

    sl = sorted(car.solids(), key=lambda x: -float(x.volume))
    chips = [float(x.volume) for x in sl[1:]]
    if chips:
        print("   dropped %d chips: %s" % (len(chips), ", ".join("%.3f" % c for c in chips)))
    car = sl[0]
    car.label = "C05_SEAT_FIRST_CARRIER"
    print("\nC05 carrier: vol=%.3f  faces=%d  solids=%d  valid=%s"
          % (L.vol(car), len(list(car.faces())), len(list(car.solids())), bool(car.is_valid)))
    export_step(car, str(OUT / "C05_SEAT_FIRST_CARRIER.step"))
    export_stl(car, str(OUT / "C05_SEAT_FIRST_CARRIER.stl"), tolerance=0.03,
               angular_tolerance=0.10)

    # ---- 5 : where can it reach the shell? ------------------------------
    print("\n=== shell connection opportunities ===")
    f = Field(L.local_triangles(car, tol=0.05, ang=0.10))
    fs = Field(L.local_triangles(approved, tol=0.06, ang=0.12))
    U = np.arange(-24.0, 24.0 + 1e-9, PITCH)
    V = np.arange(-52.0, 16.0 + 1e-9, PITCH)
    gap = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            h = f.hits(u, v)
            if h.size == 0 or h.size % 2:
                continue
            hs = fs.hits(u, v)
            if hs.size and hs.size % 2 == 0:
                c = [hs[k] for k in range(0, hs.size, 2) if hs[k] > h.max() - 1e-3]
                if c:
                    gap[i, j] = min(c) - h.max()
    g = gap[np.isfinite(gap)]
    cell = PITCH * PITCH
    print("  carrier-to-shell gap p05/p25/p50/p75/p95 = %+.3f / %+.3f / %+.3f / %+.3f / %+.3f mm"
          % tuple(float(np.percentile(g, q)) for q in (5, 25, 50, 75, 95)))
    print("  min %+.3f   area within 3 mm of the shell = %.2f mm2"
          % (float(g.min()), float((g <= 3.0).sum()) * cell))
    near = np.isfinite(gap) & (gap <= 3.0)
    lab2, n2 = ndimage.label(near)
    regions = []
    for r in range(1, n2 + 1):
        m = lab2 == r
        a = float(m.sum()) * cell
        if a < 2.0:
            continue
        iu, iv = np.nonzero(m)
        regions.append({"areaMm2": a, "minGapMm": float(gap[m].min()),
                        "uRange": [float(U[iu.min()]), float(U[iu.max()])],
                        "vRange": [float(V[iv.min()]), float(V[iv.max()])]})
    regions.sort(key=lambda r: -r["areaMm2"])
    for rr in regions[:8]:
        print("     %8.2f mm2  min gap %+6.3f  u[%6.2f,%6.2f] v[%7.2f,%7.2f]"
              % (rr["areaMm2"], rr["minGapMm"], rr["uRange"][0], rr["uRange"][1],
                 rr["vRange"][0], rr["vRange"][1]))
    if not regions:
        print("     none within 3 mm")

    L.write_json(OUT / "h04_carrier.json",
                 {"islandMm": ISLAND, "webWidthMm": WEB_W, "plateThicknessMm": PLATE_T,
                  "slotOffsetMm": SLOT_OFFSET, "slotMm": [SLOT_W, SLOT_L],
                  "slotsCut": slots, "keepOuts": ko, "droppedChipsMm3": chips,
                  "volumeMm3": L.vol(car), "faces": len(list(car.faces())),
                  "solids": len(list(car.solids())),
                  "shellGapPercentiles": {str(q): float(np.percentile(g, q))
                                          for q in (5, 25, 50, 75, 95)},
                  "shellGapMinMm": float(g.min()),
                  "connectionRegions": regions, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
