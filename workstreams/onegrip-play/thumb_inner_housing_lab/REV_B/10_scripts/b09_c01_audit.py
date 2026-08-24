"""B09 - (5) C01 thin-region audit   (6) C01 shell-gap audit.

Reads REV_A's C01 STEP read-only.  C01 itself is not modified.

Section 5 classifies every column whose plate thickness is below 1.20 mm as
    BUTTON_APERTURE_EDGE   within EDGE_BAND of one of the 9 control apertures
    PLAN_TRIM_EDGE         within EDGE_BAND of the plate's outer plan boundary
    BOOLEAN_SLIVER         isolated cluster below SLIVER_AREA
    STRUCTURAL_LOAD_PATH   interior, and inside a shell contact band
    NONSTRUCTURAL_REGION   interior, not in a contact band

Section 6 bands the shell gap and separates intended contact from clearance
bottlenecks by asking whether the low-gap zone is a broad band (load transfer)
or an isolated pinch (assembly bottleneck).
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
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI  # noqa: E402

OUT5 = L.LAB / "05_c01_wall_audit"
OUT6 = L.LAB / "06_c01_gap_audit"
C01_STEP = L.REV_A / "09_exports" / "C01_SOURCE_FAITHFUL_REBASE.step"

PITCH = 0.25
MIN_WALL = 1.20
EDGE_BAND = 1.00          # mm from a free edge
SLIVER_AREA = 2.00        # mm2
CONTACT_GAP = 0.40        # mm: below this the plate is effectively touching
GAP_BANDS = [(0.0, 0.20), (0.20, 0.40), (0.40, 0.80), (0.80, 1.20), (1.20, 1e9)]


class Field:
    def __init__(self, T):
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        self.a, self.e1, self.e2 = a, b - a, c - a
        self.tu0, self.tu1 = T[:, :, 0].min(axis=1), T[:, :, 0].max(axis=1)
        self.tv0, self.tv1 = T[:, :, 1].min(axis=1), T[:, :, 1].max(axis=1)
        self.det = self.e1[:, 0] * self.e2[:, 1] - self.e1[:, 1] * self.e2[:, 0]
        self.ok = np.abs(self.det) > 1.0e-14
        self.order = np.argsort(self.tu0)
        self.tu0s = self.tu0[self.order]

    def hits(self, u, v):
        cand = self.order[:np.searchsorted(self.tu0s, u, side="right")]
        cand = cand[self.tu1[cand] >= u]
        if cand.size == 0:
            return np.zeros(0)
        sel = cand[(self.tv0[cand] <= v) & (self.tv1[cand] >= v)]
        if sel.size == 0:
            return np.zeros(0)
        A, E1, E2 = self.a[sel], self.e1[sel], self.e2[sel]
        d, o = self.det[sel], self.ok[sel]
        du, dv = u - A[:, 0], v - A[:, 1]
        s = np.where(o, (du * E2[:, 1] - dv * E2[:, 0]) / np.where(o, d, 1.0), -1.0)
        t = np.where(o, (E1[:, 0] * dv - E1[:, 1] * du) / np.where(o, d, 1.0), -1.0)
        g = o & (s >= 0) & (t >= 0) & (s + t <= 1)
        if not g.any():
            return np.zeros(0)
        h = np.sort(A[g, 2] + s[g] * E1[g, 2] + t[g] * E2[g, 2])
        keep = np.ones(h.size, bool)
        keep[1:] = np.diff(h) > 1.0e-7
        return h[keep]


def main() -> int:
    c01 = import_step(str(C01_STEP))
    c01, _ = L.as_single_solid(c01, "C01")
    print("C01 (read-only from REV_A): vol=%.3f  faces=%d"
          % (L.vol(c01), len(list(c01.faces()))))

    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    shell = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    fp = Field(L.local_triangles(c01, tol=0.05, ang=0.10))
    fs = Field(L.local_triangles(shell, tol=0.06, ang=0.12))
    del shell
    L.memory("fields")

    U = np.arange(-21.0, 21.0 + 1e-9, PITCH)
    V = np.arange(-50.0, 15.0 + 1e-9, PITCH)
    thick = np.zeros((len(U), len(V)))
    gap = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            hp = fp.hits(u, v)
            if hp.size == 0 or hp.size % 2:
                continue
            thick[i, j] = float(sum(hp[k + 1] - hp[k] for k in range(0, hp.size, 2)))
            hs = fs.hits(u, v)
            if hs.size and hs.size % 2 == 0:
                cand = [hs[k] for k in range(0, hs.size, 2) if hs[k] > hp.max() - 1e-3]
                if cand:
                    gap[i, j] = min(cand) - hp.max()
    L.memory("maps")

    plate = thick > 1.0e-6
    cell = PITCH * PITCH
    print("plate columns = %d  (%.2f mm2 plan area)" % (int(plate.sum()), plate.sum() * cell))

    # ---------------- SECTION 5 -----------------------------------------
    # Pad with a ring of background before the EDT.  Without it the array
    # border is not treated as a free edge, so plate material clipped exactly at
    # the blank boundary (u = +-21, v = -50) reports a large edge distance and
    # a genuine trim edge is misclassified as an interior region.
    _pad = np.pad(plate, 1, mode="constant", constant_values=False)
    edge_dist = ndimage.distance_transform_edt(_pad, sampling=PITCH)[1:-1, 1:-1]
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    ap_mask = np.zeros_like(plate)
    ap_boxes = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        lb = L.local_bbox(cap, 20000)
        ap_boxes[short] = {"u": [lb["min"][0], lb["max"][0]], "v": [lb["min"][1], lb["max"][1]]}
        m = ((U[:, None] >= lb["min"][0] - 1.2) & (U[:, None] <= lb["max"][0] + 1.2) &
             (V[None, :] >= lb["min"][1] - 1.2) & (V[None, :] <= lb["max"][1] + 1.2))
        ap_mask |= m
        del cap

    thin = plate & (thick < MIN_WALL)
    lab, n = ndimage.label(thin)
    print("\n=== SECTION 5 : C01 thin-region audit (< %.2f mm) ===" % MIN_WALL)
    print("thin columns = %d of %d plate columns (%.2f %%)  area %.2f mm2"
          % (int(thin.sum()), int(plate.sum()), 100 * thin.sum() / max(1, plate.sum()),
             thin.sum() * cell))
    print("connected thin regions = %d" % n)
    contact = np.isfinite(gap) & (gap < CONTACT_GAP)
    regions = []
    counts = {}
    for r in range(1, n + 1):
        m = lab == r
        area = float(m.sum()) * cell
        iu, iv = np.nonzero(m)
        on_edge = float((edge_dist[m] <= EDGE_BAND).mean())
        in_ap = float(ap_mask[m].mean())
        in_contact = float(contact[m].mean())
        if area < SLIVER_AREA and on_edge > 0.5:
            cls = "BOOLEAN_SLIVER"
        elif on_edge > 0.6 and in_ap > 0.5:
            cls = "BUTTON_APERTURE_EDGE"
        elif on_edge > 0.6:
            cls = "PLAN_TRIM_EDGE"
        elif in_contact > 0.3:
            cls = "STRUCTURAL_LOAD_PATH"
        else:
            cls = "NONSTRUCTURAL_REGION"
        counts[cls] = counts.get(cls, 0.0) + area
        regions.append({"id": int(r), "areaMm2": area, "class": cls,
                        "minThicknessMm": float(thick[m].min()),
                        "meanThicknessMm": float(thick[m].mean()),
                        "fractionWithinEdgeBand": on_edge,
                        "fractionInApertureBand": in_ap,
                        "fractionInContactBand": in_contact,
                        "uRange": [float(U[iu.min()]), float(U[iu.max()])],
                        "vRange": [float(V[iv.min()]), float(V[iv.max()])]})
    regions.sort(key=lambda r: -r["areaMm2"])
    print("\n%-4s %9s %-22s %9s %9s %9s" % ("id", "area mm2", "class", "min t",
                                            "edge frac", "aper frac"))
    for r in regions[:20]:
        print("%-4d %9.2f %-22s %9.3f %9.2f %9.2f"
              % (r["id"], r["areaMm2"], r["class"], r["minThicknessMm"],
                 r["fractionWithinEdgeBand"], r["fractionInApertureBand"]))
    print("\narea by class:")
    for k in sorted(counts, key=lambda k: -counts[k]):
        print("   %-24s %8.2f mm2  (%.1f %% of thin area)"
              % (k, counts[k], 100 * counts[k] / max(1e-9, thin.sum() * cell)))
    structural = counts.get("STRUCTURAL_LOAD_PATH", 0.0) + counts.get("NONSTRUCTURAL_REGION", 0.0)
    print("\ninterior (non-edge) thin area = %.2f mm2" % structural)

    # ---------------- SECTION 6 -----------------------------------------
    print("\n=== SECTION 6 : C01 shell-gap audit ===")
    valid = np.isfinite(gap)
    bands = []
    print("%-14s %10s %10s %10s" % ("band (mm)", "columns", "area mm2", "share"))
    for lo, hi in GAP_BANDS:
        m = valid & (gap >= lo) & (gap < hi)
        a = float(m.sum()) * cell
        bands.append({"loMm": lo, "hiMm": None if hi > 1e8 else hi,
                      "columns": int(m.sum()), "areaMm2": a,
                      "share": float(m.sum()) / max(1, valid.sum())})
        print("%-14s %10d %10.2f %9.1f%%"
              % (("%.2f - %s" % (lo, "inf" if hi > 1e8 else "%.2f" % hi)),
                 int(m.sum()), a, 100 * m.sum() / max(1, valid.sum())))

    low = valid & (gap < CONTACT_GAP)
    lab2, n2 = ndimage.label(low)
    print("\nlow-gap (< %.2f mm) connected zones = %d" % (CONTACT_GAP, n2))
    zones = []
    for r in range(1, n2 + 1):
        m = lab2 == r
        area = float(m.sum()) * cell
        if area < 0.5:
            continue
        iu, iv = np.nonzero(m)
        pu, pv = float(np.ptp(U[iu])), float(np.ptp(V[iv]))
        elong = max(pu, pv) / max(0.25, min(pu, pv))
        cls = "LOAD_TRANSFER_CONTACT" if area >= 4.0 else "ASSEMBLY_CLEARANCE_BOTTLENECK"
        zones.append({"id": int(r), "areaMm2": area, "minGapMm": float(gap[m].min()),
                      "meanGapMm": float(gap[m].mean()), "elongation": float(elong),
                      "class": cls,
                      "uRange": [float(U[iu.min()]), float(U[iu.max()])],
                      "vRange": [float(V[iv.min()]), float(V[iv.max()])]})
    zones.sort(key=lambda r: -r["areaMm2"])
    print("%-4s %9s %9s %9s %-30s" % ("id", "area mm2", "min gap", "mean gap", "class"))
    for z in zones[:16]:
        print("%-4d %9.2f %9.3f %9.3f %-30s"
              % (z["id"], z["areaMm2"], z["minGapMm"], z["meanGapMm"], z["class"]))
    lt = sum(z["areaMm2"] for z in zones if z["class"] == "LOAD_TRANSFER_CONTACT")
    bn = sum(z["areaMm2"] for z in zones if z["class"] == "ASSEMBLY_CLEARANCE_BOTTLENECK")
    print("\nload-transfer contact area   = %8.2f mm2 in %d zones"
          % (lt, sum(1 for z in zones if z["class"] == "LOAD_TRANSFER_CONTACT")))
    print("clearance-bottleneck area   = %8.2f mm2 in %d zones"
          % (bn, sum(1 for z in zones if z["class"] == "ASSEMBLY_CLEARANCE_BOTTLENECK")))
    print("original design reference   : contact band <= 0.30 mm on 6.4 %% of columns")
    print("C01 gap < 0.30 mm on %.2f %% of columns"
          % (100 * float((valid & (gap < 0.30)).sum()) / max(1, valid.sum())))

    np.savez_compressed(OUT5 / "b09_c01_maps.npz", U=U, V=V, thick=thick, gap=gap,
                        plate=plate, thin=thin, edge_dist=edge_dist, ap_mask=ap_mask)
    L.write_json(OUT5 / "b09_c01_wall_audit.json",
                 {"pitchMm": PITCH, "minWallMm": MIN_WALL, "edgeBandMm": EDGE_BAND,
                  "plateColumns": int(plate.sum()), "plateAreaMm2": plate.sum() * cell,
                  "thinColumns": int(thin.sum()), "thinAreaMm2": thin.sum() * cell,
                  "regionCount": int(n), "regions": regions, "areaByClass": counts,
                  "interiorThinAreaMm2": structural, "apertureBoxes": ap_boxes})
    L.write_json(OUT6 / "b09_c01_gap_audit.json",
                 {"bands": bands, "contactGapMm": CONTACT_GAP, "zones": zones,
                  "loadTransferAreaMm2": lt, "bottleneckAreaMm2": bn,
                  "fractionBelow0p30": float((valid & (gap < 0.30)).sum()) / max(1, valid.sum()),
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
