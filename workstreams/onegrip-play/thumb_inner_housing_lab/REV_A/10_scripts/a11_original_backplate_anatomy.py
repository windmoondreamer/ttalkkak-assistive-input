"""A11 - anatomy of the ORIGINAL Thumb inner housing (the swept Backplate).

Measures the design rules C01 must inherit:
  * plate thickness distribution along the local normal
  * plan extent in (u, v)
  * where it actually touches / nearly touches the shell (load transfer band)
  * relation of its outer face to the shell inner surface (the conformal law)
  * button seat / PushBtn interface geometry
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import export_step, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from a07_conformity_map import ColumnField, combined_shell, tri_frame, ORIG_P, backplate  # noqa: E402
from a09_cap_axis_exposure import leaf_parts  # noqa: E402

OUT = L.LAB / "03_original_thumb_analysis"
REFS = L.LAB / "02_reference_copies"
CROP_LO = (-32.0, -54.0, -60.0)
CROP_HI = (32.0, 24.0, 60.0)
PITCH = 0.5


def main() -> int:
    bp = backplate("ORIGINAL_THUMB_CARTRIDGE")
    export_step(bp, str(REFS / "ORIGINAL_THUMB_BACKPLATE.step"))
    bpl = backplate("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    export_step(bpl, str(REFS / "LOWERED_ORIGINAL_THUMB_BACKPLATE.step"))
    print("Backplate volume = %.4f mm3" % L.vol(bp))
    print("Backplate faces  = %d" % len(list(bp.faces())))

    Tb = tri_frame(bp, ORIG_P, tol=0.06, ang=0.12)
    fb = ColumnField(Tb)

    lo_o, hi_o = np.asarray(CROP_LO, float), np.asarray(CROP_HI, float)
    world = np.asarray([ORIG_P + p[0] * L.DATUM_U + p[1] * L.DATUM_V + p[2] * (-L.DATUM_N)
                        for p in (lo_o, hi_o)])
    loc = L.to_local(world)
    clean = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER",
                           L.local_box(loc[0], loc[1], "ORIG"), "CLEAN")
    fs = ColumnField(tri_frame(clean, ORIG_P))
    del clean
    L.memory("clean field")

    U = np.arange(-26.0, 26.0 + 1e-9, PITCH)
    V = np.arange(-50.0, 14.0 + 1e-9, PITCH)
    thick = np.full((len(U), len(V)), np.nan)
    pouter = np.full((len(U), len(V)), np.nan)
    winner = np.full((len(U), len(V)), np.nan)
    nslab = np.zeros((len(U), len(V)), int)
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            hp = fb.hits(u, v, fb.candidates(u, v))
            if hp.size and hp.size % 2 == 0:
                nslab[i, j] = hp.size // 2
                pouter[i, j] = hp.max()
                thick[i, j] = float(sum(hp[k + 1] - hp[k] for k in range(0, hp.size, 2)))
            hs = fs.hits(u, v, fs.candidates(u, v))
            if hs.size and hs.size % 2 == 0:
                slab = [(hs[k], hs[k + 1]) for k in range(0, hs.size, 2)]
                cand = [p for p in slab if p[1] > -3.0]
                if cand:
                    winner[i, j] = min(cand, key=lambda q: abs(q[0] - 9.0))[0]

    m = np.isfinite(thick)
    t = thick[m]
    print("\nplan extent (columns with material) : %d of %d" % (int(m.sum()), thick.size))
    iu, iv = np.nonzero(m)
    print("plan bbox  u[%.2f, %.2f]  v[%.2f, %.2f]"
          % (U[iu.min()], U[iu.max()], V[iv.min()], V[iv.max()]))
    for q in (1, 5, 25, 50, 75, 95, 99):
        print("  thickness p%02d = %6.3f mm" % (q, float(np.percentile(t, q))))
    print("  thickness min/max = %.3f / %.3f mm" % (t.min(), t.max()))
    print("  columns with 1 slab / 2 / 3+ : %d / %d / %d"
          % (int((nslab == 1).sum()), int((nslab == 2).sum()), int((nslab >= 3).sum())))

    gap = winner - pouter
    g = gap[np.isfinite(gap)]
    print("\nconformal law (shell inner - plate outer), original pair:")
    for q in (1, 5, 10, 25, 50, 75, 90, 99):
        print("  gap p%02d = %+6.3f mm" % (q, float(np.percentile(g, q))))
    print("  contact band (gap <= 0.30 mm) : %d columns = %.1f %% of overlap"
          % (int((g <= 0.30).sum()), 100.0 * float((g <= 0.30).mean())))

    np.savez_compressed(OUT / "a11_backplate_anatomy.npz", U=U, V=V, thick=thick,
                        pouter=pouter, winner=winner, nslab=nslab, gap=gap)

    root, parts = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    push = {n: s for n, s in parts.items() if "PUSHBTN" in n.upper()}
    print("\nPushBtn occurrences: %d" % len(push))
    rows = {}
    for n in sorted(push):
        s, _ = L.as_single_solid(push[n], n)
        lb = L.local_bbox(s, 20000)
        rows[n] = {"volumeMm3": L.vol(s), "localBbox": lb}
        print("  %-28s vol=%8.3f  u[%7.2f,%7.2f] v[%7.2f,%7.2f] n[%7.2f,%7.2f]"
              % (n[:28], L.vol(s), lb["min"][0], lb["max"][0], lb["min"][1], lb["max"][1],
                 lb["min"][2], lb["max"][2]))
        del s

    L.write_json(OUT / "a11_original_backplate_anatomy.json", {
        "backplateVolumeMm3": L.vol(bp),
        "backplateFaceCount": len(list(bp.faces())),
        "thicknessPercentilesMm": {str(q): float(np.percentile(t, q))
                                   for q in (1, 5, 25, 50, 75, 95, 99)},
        "thicknessMinMaxMm": [float(t.min()), float(t.max())],
        "planBboxLocal": {"u": [float(U[iu.min()]), float(U[iu.max()])],
                          "v": [float(V[iv.min()]), float(V[iv.max()])]},
        "conformalGapPercentilesMm": {str(q): float(np.percentile(g, q))
                                      for q in (1, 5, 10, 25, 50, 75, 90, 99)},
        "contactBandColumns": int((g <= 0.30).sum()),
        "contactBandFraction": float((g <= 0.30).mean()),
        "pushButtons": rows, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
