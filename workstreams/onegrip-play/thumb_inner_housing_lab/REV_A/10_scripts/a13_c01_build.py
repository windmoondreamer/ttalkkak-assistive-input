"""A13 - C01_SOURCE_FAITHFUL_REBASE: conformal Thumb inner housing candidate.

Design law inherited from the ORIGINAL (measured in A11):
    * ONE swept plate spanning the whole Thumb cluster (no per-button parts)
    * constant nominal thickness 2.00 mm
    * outer face rides 0.8 - 1.6 mm off the shell inner surface (median 1.29)
    * captured by shell closure, crosses the split seam
Rebased onto the FROZEN lowered shell inner surface instead of the original one.

Construction is exact-boolean only.  Shape.offset_3d fails on this shell
(verified), so the standoff is produced by subtracting translated copies of the
shell from a blank: subtracting shell + d for d over a direction set is exactly
subtracting the Minkowski dilation by that set, without ever building the union.

Stages are numbered so a failure can be bisected (--stage N).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Compound, Location, Vector, export_step, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from a07_conformity_map import ColumnField, combined_shell, tri_frame  # noqa: E402
from a09_cap_axis_exposure import NAME_MAP, leaf_parts  # noqa: E402

OUT = L.LAB / "07_candidates"
REFS = L.LAB / "02_reference_copies"

CROP_LO = (-32.0, -54.0, -60.0)
CROP_HI = (32.0, 24.0, 60.0)

CONFORMAL_GAP = 1.20      # A11: original median 1.292, p25 0.829
PLATE_T = 2.00            # A11: original p50 thickness 2.004
# skin is cut along local n; normal thickness = SKIN_DEPTH_N * cos(theta)
SKIN_DEPTH_N = 2.40
BLANK_LO = (-21.0, -50.0, 2.0)
BLANK_HI = (21.0, 15.0, 18.0)

# Minkowski structuring set: identity + 6 axis directions (local u, v, n).
def dirs(r: float):
    axes = [L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V, -L.DATUM_N, L.DATUM_N]
    return [np.zeros(3)] + [a * r for a in axes]


def erode(body, shell, r: float, tag: str):
    """body minus the Minkowski dilation of shell by the r-octahedron.

    Returns the list of resulting solids.  They are deliberately NOT fused:
    the shell walls fragment the blank into 20+ chunks and fusing disjoint
    chunks yields a body whose next boolean returns a Null TopoDS_Shape
    (observed).  Selection happens on the fragment list instead.
    """
    out = body
    for k, d in enumerate(dirs(r)):
        tool = shell if k == 0 else shell.moved(Location(Vector(*[float(x) for x in d])))
        out = (out - tool).clean()
        if not out.solids():
            raise RuntimeError("body fully consumed at %s step %d" % (tag, k))
    pieces = list(out.solids())
    L.memory("%s -> %d fragments" % (tag, len(pieces)))
    return pieces


def pick_cavity(pieces, tag: str):
    """The Thumb cavity void: the largest fragment reaching the Thumb wall."""
    best, best_v, rows = None, -1.0, []
    for s in pieces:
        lb = L.local_bbox(s, 15000)
        v = float(s.volume)
        rows.append({"volumeMm3": v, "localBbox": lb})
        if lb["max"][2] > 6.0 and v > best_v:
            best, best_v = s, v
    if best is None:
        raise RuntimeError("no cavity fragment reaching the Thumb wall in " + tag)
    best.label = tag
    print("  %s: %d fragments, cavity piece vol=%.3f mm3" % (tag, len(pieces), best_v))
    return best, rows


def main() -> int:
    stage = int(sys.argv[sys.argv.index("--stage") + 1]) if "--stage" in sys.argv else 99
    OUT.mkdir(parents=True, exist_ok=True)

    box = L.local_box(CROP_LO, CROP_HI, "CUR")
    shell = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    print("frozen local crop: faces=%d vol=%.3f" % (len(list(shell.faces())), L.vol(shell)))

    # HW504 depth budget, for the report
    root, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    hw = [cart[k] for k in cart if "HW504" in k.upper()]
    hws, _ = L.as_single_solid(Compound(children=hw, label="HW"), "HW504")
    hb = L.local_bbox(hws, 40000)
    print("HW504 (original joystick) local n range = [%.3f, %.3f]  depth below pivot = %.3f mm"
          % (hb["min"][2], hb["max"][2], -hb["min"][2]))
    del hw, hws
    if stage < 1:
        return 0

    # ---- stage 1: conformal band from translated wall copies -------------
    # Earlier attempts and why they were rejected (all verified, not guessed):
    #   (a) Shape.offset_3d(1.2)          -> OCC "offset Error"
    #   (b) blank - dilate(shell, r)      -> the blank also contains the air
    #       OUTSIDE the grip (it is connected to the cavity through the Thumb
    #       openings), so the "cavity" fragment was 74,591 mm3 of mixed
    #       inside/outside air and the skin came out on the blank's top face.
    #   (c) c1 - c2                       -> Null TopoDS_Shape (coincident
    #       blank faces)
    #   (d) explicit 7-copy dilation fuse -> did not finish in 10 min
    # Correct and cheap: shell material spans [wi, wo] along n.  Translating
    # the shell inward by g puts it at [wi-g, wo-g]; by g+t at [wi-g-t, wo-g-t].
    # Their difference is exactly the band [wi-g-t, wi-g]: a conformal skin of
    # thickness t along n, standing off g from the wall inner surface.
    def shifted(d):
        v = -L.DATUM_N * -d          # inward along -n by d
        return shell.moved(Location(Vector(*[float(x) for x in v])))

    s_a = shifted(CONFORMAL_GAP)
    s_b = shifted(CONFORMAL_GAP + SKIN_DEPTH_N)
    band = (s_b - s_a).clean()
    print("stage 1  raw band solids = %d  vol=%.3f"
          % (len(list(band.solids())), float(sum(float(x.volume) for x in band.solids()))))
    L.memory("band")

    blank = L.local_box(BLANK_LO, BLANK_HI, "BLANK")
    sel = (band & blank).clean()
    sl = list(sel.solids())
    print("stage 2  band within Thumb plan window: %d solids" % len(sl))
    keep, frag1 = [], []
    for x in sl:
        lb = L.local_bbox(x, 20000)
        v = float(x.volume)
        ok = v > 20.0
        frag1.append({"volumeMm3": v, "localBbox": lb, "kept": ok})
        print("     piece vol=%10.3f  u[%7.2f,%7.2f] v[%7.2f,%7.2f] n[%7.2f,%7.2f]  %s"
              % (v, lb["min"][0], lb["max"][0], lb["min"][1], lb["max"][1],
                 lb["min"][2], lb["max"][2], "KEEP" if ok else "drop"))
        if ok:
            keep.append(x)
    if not keep:
        raise RuntimeError("no conformal band piece survived selection")
    frag2 = {"method": "translated wall copies, difference, clipped to plan window",
             "skinDepthAlongNmm": SKIN_DEPTH_N, "conformalGapMm": CONFORMAL_GAP}
    del band, s_a, s_b, sel
    if stage < 3:
        return 0

    # ---- stage 3: the candidate plate ------------------------------------
    plate, _ = L.as_single_solid(Compound(children=keep, label="P"), "C01_CONFORMAL_PLATE")
    export_step(plate, str(OUT / "C01_stage3_conformal_plate.step"))
    print("stage 3  conformal plate  vol=%12.3f  faces=%d  solids=%d  pieces=%d"
          % (L.vol(plate), len(list(plate.faces())), len(list(plate.solids())), len(keep)))
    L.memory("plate")
    if stage < 4:
        return 0

    # ---- stage 4: verify the conformal law ------------------------------
    fs = ColumnField(tri_frame(shell, L.DATUM_P))
    fp = ColumnField(tri_frame(plate, L.DATUM_P, tol=0.06, ang=0.12))
    U = np.arange(-20.0, 20.0 + 1e-9, 0.5)
    V = np.arange(-49.0, 14.0 + 1e-9, 0.5)
    gap = np.full((len(U), len(V)), np.nan)
    thick = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            hp = fp.hits(u, v, fp.candidates(u, v))
            if not hp.size or hp.size % 2:
                continue
            thick[i, j] = float(sum(hp[k + 1] - hp[k] for k in range(0, hp.size, 2)))
            hs = fs.hits(u, v, fs.candidates(u, v))
            if hs.size and hs.size % 2 == 0:
                slab = [(hs[k], hs[k + 1]) for k in range(0, hs.size, 2)]
                cand = [p for p in slab if p[0] > hp.max() - 0.001]
                if cand:
                    gap[i, j] = min(p[0] for p in cand) - hp.max()
    g = gap[np.isfinite(gap)]
    t = thick[np.isfinite(thick)]
    if g.size == 0 or t.size == 0:
        raise RuntimeError("verification found no overlapping columns: gap=%d thick=%d"
                           % (g.size, t.size))
    print("\nstage 4  conformal verification (%d columns)" % g.size)
    for q in (1, 5, 10, 25, 50, 75, 90, 99):
        print("   gap p%02d = %+6.3f mm   thickness p%02d = %6.3f mm"
              % (q, float(np.percentile(g, q)), q, float(np.percentile(t, q))))
    print("   gap min/max = %+.3f / %+.3f    thickness min/max = %.3f / %.3f"
          % (g.min(), g.max(), t.min(), t.max()))
    inter = L.inter_vol(plate, shell)
    print("   plate INTERSECT frozen shell = %.6f mm3" % inter)

    np.savez_compressed(OUT / "c01_conformal_check.npz", U=U, V=V, gap=gap, thick=thick)
    L.write_json(OUT / "c01_build.json", {
        "conformalGapMm": CONFORMAL_GAP, "plateThicknessMm": PLATE_T,
        "blankLocal": {"min": list(BLANK_LO), "max": list(BLANK_HI)},
        "hw504LocalN": [hb["min"][2], hb["max"][2]],
        "plateVolumeMm3": L.vol(plate), "plateFaces": len(list(plate.faces())),
        "gapPercentilesMm": {str(q): float(np.percentile(g, q)) for q in (1, 5, 10, 25, 50, 75, 90, 99)},
        "gapMinMaxMm": [float(g.min()), float(g.max())],
        "thicknessPercentilesMm": {str(q): float(np.percentile(t, q)) for q in (1, 5, 25, 50, 75, 95, 99)},
        "thicknessMinMaxMm": [float(t.min()), float(t.max())],
        "plateShellIntersectionMm3": inter,
        "stage1Fragments": frag1, "stage2Fragments": frag2,
        "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
