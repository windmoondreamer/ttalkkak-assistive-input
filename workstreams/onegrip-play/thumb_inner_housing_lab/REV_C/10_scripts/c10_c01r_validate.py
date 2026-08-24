"""C10 - validate C01R: thin-wall status, gap bands, contact classification."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import true_axis  # noqa: E402
from c04_validate import RECON  # noqa: E402
from c07_docs71_and_c01 import Field  # noqa: E402

OUT = L.LAB / "07_c01r"
C01R = OUT / "C01R_RECONCILED_SOURCE_FAITHFUL.step"
C01 = L.REV_A / "09_exports" / "C01_SOURCE_FAITHFUL_REBASE.step"
PITCH = 0.25
MIN_WALL = 1.20
PREF_WALL = 1.60
BANDS = [(0.0, 0.20), (0.20, 0.40), (0.40, 0.80), (0.80, 1.20), (1.20, 1e9)]
PAD_FOOTPRINTS = json.loads((OUT / "c09_c01r_build.json").read_text(encoding="utf-8"))["pads"]


def maps(solid, shell, U, V):
    fp = Field(L.local_triangles(solid, tol=0.05, ang=0.10))
    fs = Field(L.local_triangles(shell, tol=0.06, ang=0.12))
    t = np.zeros((len(U), len(V)))
    g = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            hp = fp.hits(u, v)
            if hp.size == 0 or hp.size % 2:
                continue
            t[i, j] = float(sum(hp[k + 1] - hp[k] for k in range(0, hp.size, 2)))
            hs = fs.hits(u, v)
            if hs.size and hs.size % 2 == 0:
                cand = [hs[k] for k in range(0, hs.size, 2) if hs[k] > hp.max() - 1e-3]
                if cand:
                    g[i, j] = min(cand) - hp.max()
    return t, g


def main() -> int:
    rec = import_step(str(RECON))
    rec, _ = L.as_single_solid(rec, "RECONCILED")
    c01r = import_step(str(C01R))
    c01r, _ = L.as_single_solid(c01r, "C01R")
    c01 = import_step(str(C01))
    c01, _ = L.as_single_solid(c01, "C01")
    print("C01R : vol=%.3f faces=%d solids=%d" % (L.vol(c01r), len(list(c01r.faces())),
                                                  len(list(c01r.solids()))))
    print("C01  : vol=%.3f faces=%d" % (L.vol(c01), len(list(c01.faces()))))
    print("C01R interference with the reconciled shell = %.6f mm3"
          % L.inter_vol(c01r, rec))
    L.memory("load")

    U = np.arange(-21.0, 21.0 + 1e-9, PITCH)
    V = np.arange(-50.0, 15.0 + 1e-9, PITCH)
    cell = PITCH * PITCH
    t, g = maps(c01r, rec, U, V)
    plate = t > 1e-6
    print("\nC01R plan area = %.2f mm2  (C01 was 1503.19)" % (plate.sum() * cell))

    # ---- thin-wall status ------------------------------------------------
    pad = np.zeros((len(U), len(V)), bool)
    for p in PAD_FOOTPRINTS:
        cu, cv = p["snappedCentreUV"]
        r = p["radiusMm"] + 0.30
        pad |= ((U[:, None] - cu) ** 2 + (V[None, :] - cv) ** 2) <= r * r
    _pd = np.pad(plate, 1, mode="constant", constant_values=False)
    edge = ndimage.distance_transform_edt(_pd, sampling=PITCH)[1:-1, 1:-1]
    thin = plate & (t < MIN_WALL)
    pref = plate & (t < PREF_WALL)
    print("\n=== SECTION 12 : thin-wall status ===")
    print("  columns below %.2f mm : %d  = %8.3f mm2   (C01: 1602 = 100.12 mm2)"
          % (MIN_WALL, int(thin.sum()), thin.sum() * cell))
    print("  columns below %.2f mm : %d  = %8.3f mm2" % (PREF_WALL, int(pref.sum()),
                                                          pref.sum() * cell))
    print("  minimum plate thickness anywhere : %.4f mm" % float(t[plate].min()))
    interior_thin = thin & (edge > 1.0)
    print("  interior (non-edge) thin area    : %8.3f mm2" % (interior_thin.sum() * cell))
    if thin.any():
        lab, n = ndimage.label(thin)
        print("  thin regions: %d" % n)
        for r in range(1, n + 1):
            m = lab == r
            a = float(m.sum()) * cell
            if a < 0.3:
                continue
            iu, iv = np.nonzero(m)
            print("     area %7.3f  min t %6.3f  edgeFrac %4.2f  u[%6.2f,%6.2f] v[%7.2f,%7.2f]"
                  % (a, float(t[m].min()), float((edge[m] <= 1.0).mean()),
                     U[iu.min()], U[iu.max()], V[iv.min()], V[iv.max()]))

    # ---- gap bands and contact classification ---------------------------
    valid = np.isfinite(g)
    print("\n=== SECTION 11 : shell-gap bands and contact classification ===")
    print("%-14s %10s %10s %10s %-28s" % ("band (mm)", "columns", "area mm2", "share", "class"))
    band_rows = []
    for lo, hi in BANDS:
        m = valid & (g >= lo) & (g < hi)
        in_pad = float(pad[m].mean()) if m.any() else 0.0
        cls = ("INTENTIONAL LOAD TRANSFER" if (hi <= 0.40 and in_pad > 0.5)
               else ("ASSEMBLY CLEARANCE" if lo >= 0.40 else
                     ("INTENTIONAL LOAD TRANSFER" if in_pad > 0.5 else "review")))
        band_rows.append({"loMm": lo, "hiMm": None if hi > 1e8 else hi,
                          "columns": int(m.sum()), "areaMm2": float(m.sum()) * cell,
                          "fractionInsidePadFootprint": in_pad, "class": cls})
        print("%-14s %10d %10.3f %9.1f%% %-28s"
              % ("%.2f - %s" % (lo, "inf" if hi > 1e8 else "%.2f" % hi),
                 int(m.sum()), float(m.sum()) * cell,
                 100.0 * m.sum() / max(1, valid.sum()), cls))

    lowg = valid & (g < 0.40)
    lab2, n2 = ndimage.label(lowg)
    zones = []
    print("\n  low-gap zones:")
    for r in range(1, n2 + 1):
        m = lab2 == r
        a = float(m.sum()) * cell
        if a < 0.3:
            continue
        iu, iv = np.nonzero(m)
        inp = float(pad[m].mean())
        cls = "INTENTIONAL LOAD TRANSFER" if inp > 0.5 else "ASSEMBLY CLEARANCE"
        zones.append({"areaMm2": a, "minGapMm": float(g[m].min()),
                      "meanGapMm": float(g[m].mean()),
                      "fractionInsidePad": inp, "class": cls,
                      "uRange": [float(U[iu.min()]), float(U[iu.max()])],
                      "vRange": [float(V[iv.min()]), float(V[iv.max()])]})
        print("     area %7.3f  min %6.3f  mean %6.3f  inPad %4.2f  %-26s u[%6.2f,%6.2f] v[%7.2f,%7.2f]"
              % (a, float(g[m].min()), float(g[m].mean()), inp, cls,
                 U[iu.min()], U[iu.max()], V[iv.min()], V[iv.max()]))
    lt = sum(z["areaMm2"] for z in zones if z["class"].startswith("INTENTIONAL"))
    ac = sum(z["areaMm2"] for z in zones if z["class"] == "ASSEMBLY CLEARANCE")
    print("\n  INTENTIONAL LOAD TRANSFER : %8.3f mm2" % lt)
    print("  ASSEMBLY CLEARANCE        : %8.3f mm2" % ac)
    print("  gap <= 0.30 mm on %.2f %% of columns   (ORIGINAL 6.39 %%, C01 0.59 %%)"
          % (100.0 * float((valid & (g <= 0.30)).sum()) / max(1, valid.sum())))

    np.savez_compressed(OUT / "c10_c01r_maps.npz", U=U, V=V, thick=t, gap=g,
                        plate=plate, pad=pad)
    L.write_json(OUT / "c10_c01r_validate.json",
                 {"volumeMm3": L.vol(c01r), "faces": len(list(c01r.faces())),
                  "solids": len(list(c01r.solids())),
                  "interferenceWithReconciledMm3": L.inter_vol(c01r, rec),
                  "planAreaMm2": plate.sum() * cell,
                  "thinBelowMinWallMm2": thin.sum() * cell,
                  "thinBelowPreferredMm2": pref.sum() * cell,
                  "minThicknessMm": float(t[plate].min()),
                  "interiorThinAreaMm2": interior_thin.sum() * cell,
                  "gapBands": band_rows, "lowGapZones": zones,
                  "intentionalLoadTransferMm2": lt, "assemblyClearanceMm2": ac,
                  "contactFractionAt0p30": float((valid & (g <= 0.30)).sum()) / max(1, valid.sum()),
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
