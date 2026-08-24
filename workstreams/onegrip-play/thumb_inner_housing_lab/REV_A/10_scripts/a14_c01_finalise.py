"""A14 - finalise and evaluate C01_SOURCE_FAITHFUL_REBASE.

Takes the stage-3 conformal band and:
  1. enforces the standoff laterally too (the band was cut along n only)
  2. cuts the control apertures at the frozen cap/joystick axes
  3. cuts the keep-outs (SZH static + 25 deg moving envelope, N1/N2 carrier,
     the three original shell-side M3 screws)
  4. evaluates it against the section 18 checklist

Button seats are deliberately NOT generated.  Two upstream items must be closed
first: the Thumb switch is still an open question in CLAUDE.md section 3
(PushBtn vs ITS-1105), and A09 shows the frozen exterior does not currently
expose the Thumb buttons at all, so no seat height can be validated.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Compound, Location, Plane, Vector, Cylinder, Box, Align, export_step, export_stl, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from a07_conformity_map import ColumnField, combined_shell, tri_frame  # noqa: E402
from a09_cap_axis_exposure import NAME_MAP, leaf_parts, press_axis  # noqa: E402

OUT = L.LAB / "07_candidates"
EXP = L.LAB / "09_exports"
CROP_LO = (-32.0, -54.0, -60.0)
CROP_HI = (32.0, 24.0, 60.0)
CONFORMAL_GAP = 1.20
APERTURE_CLEARANCE = 0.60     # around each cap footprint
KEEPOUT_CLEARANCE = 0.50
SCREW_CLEARANCE = 1.00
MIN_WALL = 1.20               # section 17 absolute minimum


def axis_prism(cap, axis, grow, length, label):
    """Prism swept along the control axis around the cap footprint."""
    pts = L.surf_points(cap, 30000, tol=0.06)
    c = pts.mean(axis=0)
    ref = L.DATUM_U if abs(float(np.dot(axis, L.DATUM_U))) < 0.9 else L.DATUM_V
    ex = L.unit(ref - axis * float(np.dot(axis, ref)))
    ey = np.cross(axis, ex)
    d = pts - c
    a = d @ ex
    b = d @ ey
    plane = Plane(origin=L.xyz(c - axis * (length * 0.5)), x_dir=L.xyz(ex), z_dir=L.xyz(axis))
    box = plane * Box(float(a.max() - a.min()) + 2 * grow,
                      float(b.max() - b.min()) + 2 * grow, length,
                      align=(Align.CENTER, Align.CENTER, Align.MIN))
    box = box.moved(Location(Vector(*[float(x) for x in (ex * (a.max() + a.min()) * 0.5
                                                        + ey * (b.max() + b.min()) * 0.5)])))
    box.label = label
    return box


def main() -> int:
    plate = import_step(str(OUT / "C01_stage3_conformal_plate.step"))
    plate, _ = L.as_single_solid(plate, "C01")
    print("input plate: vol=%.3f faces=%d" % (L.vol(plate), len(list(plate.faces()))))

    box = L.local_box(CROP_LO, CROP_HI, "CUR")
    shell = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")

    # ---- 1. lateral standoff --------------------------------------------
    before = L.inter_vol(plate, shell)
    for d in (L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V, np.zeros(3)):
        v = d * CONFORMAL_GAP
        tool = shell if not np.any(v) else shell.moved(Location(Vector(*[float(x) for x in v])))
        plate = (plate - tool).clean()
    plate, npc = L.as_single_solid(plate, "C01")
    after = L.inter_vol(plate, shell)
    print("lateral standoff: shell intersection %.6f -> %.6f mm3 (pieces after: %d)"
          % (before, after, npc))
    L.memory("standoff")

    # ---- 2. control apertures -------------------------------------------
    root, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    apertures = {}
    for label, short in NAME_MAP.items():
        cap, _ = L.as_single_solid(cart[label], short)
        ax, _, _, _ = press_axis(cap)
        tool = axis_prism(cap, ax, APERTURE_CLEARANCE, 60.0, "APERTURE_" + short)
        iv = L.inter_vol(plate, tool)
        apertures[short] = {"removedMm3": iv}
        if iv > 1.0e-6:
            plate = (plate - tool).clean()
        print("  aperture %-14s removed %9.3f mm3" % (short, iv))
        del cap
    plate, npa = L.as_single_solid(plate, "C01")
    print("  after apertures: vol=%.3f pieces=%d" % (L.vol(plate), npa))
    L.memory("apertures")

    # ---- 3. keep-outs ----------------------------------------------------
    keep = import_step(str(L.LAB / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    ko_rows = {}
    for child in (list(getattr(keep, "children", []) or []) or [keep]):
        lab = str(child.label)
        if not child.solids():
            continue
        if lab.startswith("CAP_"):
            continue                      # already handled as swept apertures
        s, _ = L.as_single_solid(child, lab)
        clr = SCREW_CLEARANCE if "SCREW" in lab.upper() else KEEPOUT_CLEARANCE
        removed = 0.0
        for d in (np.zeros(3), L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V,
                  -L.DATUM_N, L.DATUM_N):
            v = d * clr
            tool = s if not np.any(v) else s.moved(Location(Vector(*[float(x) for x in v])))
            iv = L.inter_vol(plate, tool)
            if iv > 1.0e-6:
                removed += iv
                plate = (plate - tool).clean()
                plate, _ = L.as_single_solid(plate, "C01")
        ko_rows[lab] = {"clearanceMm": clr, "removedMm3": removed}
        if removed > 1.0e-6:
            print("  keep-out %-34s removed %9.3f mm3 (clr %.2f)" % (lab[:34], removed, clr))
    plate, npk = L.as_single_solid(plate, "C01_SOURCE_FAITHFUL_REBASE")
    L.memory("keepouts")

    pieces = list(plate.solids())
    print("\nC01 final: vol=%.3f faces=%d solids=%d" % (L.vol(plate), len(list(plate.faces())), len(pieces)))
    for s in pieces:
        lb = L.local_bbox(s, 20000)
        print("   piece vol=%10.3f  u[%7.2f,%7.2f] v[%7.2f,%7.2f] n[%7.2f,%7.2f]"
              % (float(s.volume), lb["min"][0], lb["max"][0], lb["min"][1], lb["max"][1],
                 lb["min"][2], lb["max"][2]))

    # ---- 4. evaluation ---------------------------------------------------
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
                cand = [hs[k] for k in range(0, hs.size, 2) if hs[k] > hp.max() - 1e-3]
                if cand:
                    gap[i, j] = min(cand) - hp.max()
    g = gap[np.isfinite(gap)]
    t = thick[np.isfinite(thick)]
    t_real = t[t > 0.30]     # ignore the knife edges at the plan boundary
    ev = {
        "plateVolumeMm3": L.vol(plate), "faces": len(list(plate.faces())),
        "solidCount": len(pieces),
        "shellIntersectionMm3": L.inter_vol(plate, shell),
        "gapPercentilesMm": {str(q): float(np.percentile(g, q)) for q in (1, 5, 25, 50, 75, 95, 99)},
        "gapMinMaxMm": [float(g.min()), float(g.max())],
        "thicknessPercentilesMm": {str(q): float(np.percentile(t_real, q)) for q in (1, 5, 25, 50, 75, 95, 99)},
        "thicknessMinMaxMm": [float(t_real.min()), float(t_real.max())],
        "columnsBelowMinWall": int((t_real < MIN_WALL).sum()),
        "columnsTotal": int(t_real.size),
        "apertures": apertures, "keepOuts": ko_rows,
    }
    print("\nEVALUATION")
    print("  shell intersection          = %.6f mm3" % ev["shellIntersectionMm3"])
    print("  conformal gap p25/p50/p75   = %+.3f / %+.3f / %+.3f mm"
          % (ev["gapPercentilesMm"]["25"], ev["gapPercentilesMm"]["50"], ev["gapPercentilesMm"]["75"]))
    print("  conformal gap min/max       = %+.3f / %+.3f mm" % tuple(ev["gapMinMaxMm"]))
    print("  wall thickness p05/p50/p95  = %.3f / %.3f / %.3f mm"
          % (ev["thicknessPercentilesMm"]["5"], ev["thicknessPercentilesMm"]["50"],
             ev["thicknessPercentilesMm"]["95"]))
    print("  columns below %.2f mm wall   = %d of %d (%.2f %%)"
          % (MIN_WALL, ev["columnsBelowMinWall"], ev["columnsTotal"],
             100.0 * ev["columnsBelowMinWall"] / max(1, ev["columnsTotal"])))

    # keep-out clearance verification
    keep2 = import_step(str(L.LAB / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    viol = {}
    for child in (list(getattr(keep2, "children", []) or []) or [keep2]):
        lab = str(child.label)
        if not child.solids() or lab.startswith("CAP_"):
            continue
        s, _ = L.as_single_solid(child, lab)
        iv = L.inter_vol(plate, s)
        viol[lab] = iv
        if iv > 1.0e-6:
            print("  !! keep-out residual %-30s %.6f mm3" % (lab[:30], iv))
    ev["keepOutResidualMm3"] = viol
    if all(v <= 1.0e-6 for v in viol.values()):
        print("  keep-out residual           = 0.000000 mm3 for all items")

    export_step(plate, str(EXP / "C01_SOURCE_FAITHFUL_REBASE.step"))
    export_stl(plate, str(EXP / "C01_SOURCE_FAITHFUL_REBASE.stl"), tolerance=0.03, angular_tolerance=0.10)
    np.savez_compressed(OUT / "c01_final_check.npz", U=U, V=V, gap=gap, thick=thick)
    L.write_json(OUT / "c01_evaluation.json", {"evaluation": ev, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
