"""C08 - where were the ORIGINAL load-transfer bands? (REV_C section 11)

Reads REV_A's original-pair gap map read-only and locates the contact band, so
C01R can reproduce intentional pads in analogous places instead of being pushed
flat against the shell.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402

OUT = L.LAB / "07_c01r"
CONTACT = 0.30


def main() -> int:
    z = np.load(L.REV_A / "03_original_thumb_analysis" / "a11_backplate_anatomy.npz")
    U, V, gap, thick = z["U"], z["V"], z["gap"], z["thick"]
    cell = float(U[1] - U[0]) * float(V[1] - V[0])
    valid = np.isfinite(gap)
    band = valid & (gap <= CONTACT)
    print("ORIGINAL Backplate contact band (gap <= %.2f mm)" % CONTACT)
    print("  overlap columns      : %d" % int(valid.sum()))
    print("  contact columns      : %d  = %.2f mm2  = %.2f %% of overlap"
          % (int(band.sum()), band.sum() * cell, 100.0 * band.sum() / valid.sum()))

    lab, n = ndimage.label(band)
    sizes = ndimage.sum(band, lab, range(1, n + 1)) if n else []
    print("  connected contact zones: %d" % n)
    zones = []
    for r in range(1, n + 1):
        m = lab == r
        a = float(m.sum()) * cell
        if a < 1.0:
            continue
        iu, iv = np.nonzero(m)
        zones.append({"id": int(r), "areaMm2": a,
                      "centroidUV": [float(U[iu].mean()), float(V[iv].mean())],
                      "uRange": [float(U[iu.min()]), float(U[iu.max()])],
                      "vRange": [float(V[iv.min()]), float(V[iv.max()])],
                      "minGapMm": float(gap[m].min()), "meanGapMm": float(gap[m].mean())})
    zones.sort(key=lambda r: -r["areaMm2"])
    print("\n%-4s %9s %-20s %-20s %9s %9s"
          % ("id", "area mm2", "u range", "v range", "min gap", "mean gap"))
    for zn in zones[:14]:
        print("%-4d %9.2f %-20s %-20s %9.3f %9.3f"
              % (zn["id"], zn["areaMm2"],
                 "[%.2f, %.2f]" % tuple(zn["uRange"]),
                 "[%.2f, %.2f]" % tuple(zn["vRange"]),
                 zn["minGapMm"], zn["meanGapMm"]))

    # relate the zones to the control cluster: are they around the buttons or
    # around the perimeter?
    _, cart = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    ctr = {}
    ORIG_P = L.DATUM_P - L.THUMB_DELTA
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        p = L.surf_points(cap, 20000, tol=0.06).mean(axis=0) - ORIG_P
        ctr[short] = [float(p @ L.DATUM_U), float(p @ L.DATUM_V)]
        del cap
    print("\nnearest control to each significant contact zone:")
    for zn in zones[:14]:
        cu, cv = zn["centroidUV"]
        best = min(ORDER, key=lambda s: np.hypot(cu - ctr[s][0], cv - ctr[s][1]))
        d = float(np.hypot(cu - ctr[best][0], cv - ctr[best][1]))
        zn["nearestControl"] = best
        zn["distanceToControlMm"] = d
        print("   zone %-3d area %7.2f  ->  %-4s  d = %5.2f mm" % (zn["id"], zn["areaMm2"], best, d))

    total = sum(z["areaMm2"] for z in zones)
    big = [z for z in zones if z["areaMm2"] >= 4.0]
    print("\n  significant zones (>= 4 mm2): %d, total %.2f mm2"
          % (len(big), sum(z["areaMm2"] for z in big)))
    print("  all zones total: %.2f mm2" % total)

    L.write_json(OUT / "c08_contact_band_study.json",
                 {"contactThresholdMm": CONTACT, "cellMm2": cell,
                  "overlapColumns": int(valid.sum()), "contactColumns": int(band.sum()),
                  "contactAreaMm2": band.sum() * cell,
                  "contactFraction": float(band.sum() / valid.sum()),
                  "zones": zones, "controlCentresLocalUV": ctr})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
