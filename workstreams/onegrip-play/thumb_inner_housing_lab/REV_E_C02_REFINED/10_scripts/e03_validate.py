"""E03 - validate C02_C01_EXACT_REFINED against the exact approved shell (section 9)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from d02_housing_vs_exact import C01_STEP, Field, approved_shell  # noqa: E402
from e01_probe import ZONES  # noqa: E402
from e02_build_c02 import (HARNESS_INSERTION_MM, KEEPOUTS, MIN_STRUCTURAL_WALL,
                           PAD_GAP, PITCH)  # noqa: E402

OUT = L.LAB / "03_validation"
OUTWARD = -L.DATUM_N
CONTACT = 0.30
CAND = L.LAB / "02_candidate" / "C02_C01_EXACT_REFINED.step"


def main() -> int:
    approved = approved_shell()
    Tap = L.triangles(approved, tol=0.05, ang=0.10)
    c02 = import_step(str(CAND))
    c02, _ = L.as_single_solid(c02, "C02")
    c01 = import_step(str(C01_STEP))
    c01, _ = L.as_single_solid(c01, "C01")
    z = np.load(L.LAB / "01_probe" / "e01_maps.npz")
    Uc, Vc, cos = z["U"], z["V"], z["cos"]
    L.memory("loaded")

    print("=== solid ===")
    print("  solids %d   valid %s   faces %d   volume %.3f mm3"
          % (len(list(c02.solids())), bool(c02.is_valid), len(list(c02.faces())),
             L.vol(c02)))
    inter = L.inter_vol(c02, approved)
    print("  interference with the exact approved shell = %.6f mm3" % inter)

    U = np.arange(-22.0, 22.0 + 1e-9, PITCH)
    V = np.arange(-52.0, 16.0 + 1e-9, PITCH)
    cell = PITCH * PITCH
    fp = Field(L.local_triangles(c02, tol=0.05, ang=0.10))
    fs = Field(L.local_triangles(approved, tol=0.06, ang=0.12))
    tn = np.zeros((len(U), len(V)))
    gap = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            h = fp.hits(u, v)
            if h.size == 0 or h.size % 2:
                continue
            tn[i, j] = float(sum(h[k + 1] - h[k] for k in range(0, h.size, 2)))
            hs = fs.hits(u, v)
            if hs.size and hs.size % 2 == 0:
                cand = [hs[k] for k in range(0, hs.size, 2) if hs[k] > h.max() - 1e-3]
                if cand:
                    gap[i, j] = min(cand) - h.max()
    cosr = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        ii = int(round((u - Uc[0]) / (Uc[1] - Uc[0])))
        for j, v in enumerate(V):
            jj = int(round((v - Vc[0]) / (Vc[1] - Vc[0])))
            if 0 <= ii < len(Uc) and 0 <= jj < len(Vc):
                cosr[i, j] = cos[ii, jj]
    tnorm = tn * np.nan_to_num(cosr, nan=1.0)
    plate = tn > 1e-6
    valid = np.isfinite(gap)
    gg = gap[valid]

    print("\n=== gap ===")
    print("  plan area %.2f mm2   overlap columns %d" % (plate.sum() * cell, int(valid.sum())))
    for q in (25, 50, 75):
        print("  gap p%-3d = %+.3f mm" % (q, float(np.percentile(gg, q))))
    print("  gap min / max = %+.3f / %+.3f mm" % (float(gg.min()), float(gg.max())))

    print("\n=== structural thickness (NORMAL to the plate) ===")
    a12 = float((plate & (tnorm < 1.20)).sum()) * cell
    a16 = float((plate & (tnorm < MIN_STRUCTURAL_WALL)).sum()) * cell
    print("  area below 1.20 mm : %8.3f mm2   (C01: 100.12)" % a12)
    print("  area below 1.60 mm : %8.3f mm2" % a16)
    print("  minimum structural thickness : %.4f mm" % float(tnorm[plate].min()))
    print("  thickness p25/p50/p75 : %.3f / %.3f / %.3f mm"
          % tuple(float(np.percentile(tnorm[plate], q)) for q in (25, 50, 75)))

    print("\n=== contact / clearance law ===")
    padm = np.zeros((len(U), len(V)), bool)
    for name, zn in ZONES.items():
        padm |= ((U[:, None] >= zn["u"][0]) & (U[:, None] <= zn["u"][1]) &
                 (V[None, :] >= zn["v"][0]) & (V[None, :] <= zn["v"][1]))
    band = valid & (gap <= CONTACT)
    lt = float((band & padm).sum()) * cell
    ac = float((band & ~padm).sum()) * cell
    print("  INTENTIONAL LOAD TRANSFER : %8.3f mm2   (original 95.06, C01 20.81)" % lt)
    print("  ASSEMBLY CLEARANCE low-gap: %8.3f mm2" % ac)
    zones_out = {}
    for name, zn in ZONES.items():
        m = ((U[:, None] >= zn["u"][0]) & (U[:, None] <= zn["u"][1]) &
             (V[None, :] >= zn["v"][0]) & (V[None, :] <= zn["v"][1]))
        b = m & band
        cov = m & plate
        zones_out[name] = {"contactAreaMm2": float(b.sum()) * cell,
                           "targetMm2": zn["targetMm2"],
                           "plateCoverageMm2": float(cov.sum()) * cell,
                           "minGapMm": float(gap[b].min()) if b.any() else None,
                           "meanGapMm": float(gap[b].mean()) if b.any() else None}
        r = zones_out[name]
        print("  %-6s contact %8.3f mm2 (target %.2f)  plate coverage %8.3f mm2  "
              "min gap %s  mean %s"
              % (name, r["contactAreaMm2"], r["targetMm2"], r["plateCoverageMm2"],
                 ("%+.3f" % r["minGapMm"]) if r["minGapMm"] is not None else "-",
                 ("%+.3f" % r["meanGapMm"]) if r["meanGapMm"] is not None else "-"))
    lab, n = ndimage.label(band)
    print("  low-gap zones: %d" % n)
    zl = []
    for r in range(1, n + 1):
        m = lab == r
        a = float(m.sum()) * cell
        if a < 0.5:
            continue
        iu, iv = np.nonzero(m)
        inp = float(padm[m].mean())
        cls = "INTENTIONAL LOAD TRANSFER" if inp > 0.5 else "ASSEMBLY CLEARANCE"
        zl.append({"areaMm2": a, "minGapMm": float(gap[m].min()),
                   "fractionInPadZone": inp, "class": cls,
                   "uRange": [float(U[iu.min()]), float(U[iu.max()])],
                   "vRange": [float(V[iv.min()]), float(V[iv.max()])]})
        print("     %8.3f mm2  min %6.3f  inZone %4.2f  %-26s u[%6.2f,%6.2f] v[%7.2f,%7.2f]"
              % (a, float(gap[m].min()), inp, cls, U[iu.min()], U[iu.max()],
                 V[iv.min()], V[iv.max()]))

    print("\n=== JOY + T1-T8 blocking ===")
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    Tc = L.triangles(c02, tol=0.05, ang=0.10)
    blk = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, _ = true_axis(cap)
        pts = L.surf_points(cap, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        proj = (pts - cen) @ w
        face = pts[proj > proj.max() - 0.30]
        idx = np.linspace(0, len(face) - 1, min(81, len(face))).astype(int)
        nb = 0
        for p in face[idx]:
            iv2 = ray_intervals(Tc, p, w)
            if [q for q in (iv2 or []) if q[1] > 0.0 and q[1] - max(q[0], 0.0) > 0.05]:
                nb += 1
        blk[short] = nb / max(1, len(idx))
        print("  %-5s blocked by C02 : %5.1f %%" % (short, 100 * blk[short]))
        del cap

    print("\n=== keep-outs ===")
    keepc = import_step(str(KEEPOUTS))
    ko = {}
    harness = None
    for child in list(getattr(keepc, "children", []) or []):
        lab2 = str(child.label)
        if not child.solids() or lab2.startswith("CAP_"):
            continue
        s, _ = L.as_single_solid(child, lab2)
        iv = L.inter_vol(c02, s)
        ko[lab2] = iv
        print("  %-38s %12.6f mm3" % (lab2[:38], iv))
        if "N1_N2" in lab2.upper() or "CARRIER" in lab2.upper():
            tot = 0.0
            for k in range(1, int(HARNESS_INSERTION_MM) + 1):
                tot += L.inter_vol(c02, s.moved(Location(Vector(
                    *[float(x) for x in (L.DATUM_N * float(k))]))))
            harness = tot
        del s
    print("  N1/N2 rear harness insertion corridor (%.0f mm, PROVISIONAL) = %.6f mm3"
          % (HARNESS_INSERTION_MM, harness if harness is not None else -1))

    np.savez_compressed(OUT / "e03_maps.npz", U=U, V=V, tn=tn, tnorm=tnorm, gap=gap,
                        plate=plate, padm=padm)
    L.write_json(OUT / "e03_validate.json",
                 {"solids": len(list(c02.solids())), "valid": bool(c02.is_valid),
                  "faces": len(list(c02.faces())), "volumeMm3": L.vol(c02),
                  "interferenceMm3": inter, "planAreaMm2": plate.sum() * cell,
                  "gapPercentilesMm": {str(q): float(np.percentile(gg, q))
                                       for q in (5, 25, 50, 75, 95)},
                  "gapMinMm": float(gg.min()), "gapMaxMm": float(gg.max()),
                  "areaBelow1p20Mm2": a12, "areaBelow1p60Mm2": a16,
                  "minStructuralThicknessMm": float(tnorm[plate].min()),
                  "intentionalLoadTransferMm2": lt, "assemblyClearanceLowGapMm2": ac,
                  "zones": zones_out, "lowGapZones": zl,
                  "openingBlockedFraction": blk, "keepOutMm3": ko,
                  "harnessCorridorMm3": harness, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
