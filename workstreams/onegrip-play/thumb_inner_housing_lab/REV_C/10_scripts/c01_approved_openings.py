"""C01 - characterise every APPROVED Thumb opening (REV_C section 3).

Source authority for opening topology is THUMB_LOWER15_HOUSING_V1, which exists
only as STL.  That is marked NON-EXACT throughout and is never converted into
geometry; it is used to MEASURE the intended opening, and the reconciled cutter
is then built analytically from exact inputs (frozen control transform + the
original OneGrip opening construction).

Method, per control:
  * local frame  origin = frozen cap centroid, w = frozen TRUE press axis
  * cast a dense grid of rays parallel to w over a patch around the control
  * a ray is OPEN if it finds no wall material in the Thumb wall band
  * the OPEN set gives area / centroid / boundary contour
  * rays adjacent to the OPEN set give the wall entry and exit contours
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, true_axis  # noqa: E402
from b07_lineage_and_visual import LOWER15_JAD, LOWER15_JFD, read_stl  # noqa: E402

OUT = L.LAB / "01_approved_openings"
OUTWARD = -L.DATUM_N

PATCH = 11.0          # half-width of the sampling patch, mm
PITCH = 0.10          # ray pitch, mm
BAND = (-8.0, 26.0)   # w-range searched for wall material, from the cap centroid
MIN_WALL_FRAC = 0.05  # mm of material below which a ray counts as OPEN


def axis_frame(w):
    ref = L.DATUM_U if abs(float(np.dot(w, L.DATUM_U))) < 0.9 else L.DATUM_V
    ex = L.unit(ref - w * float(np.dot(w, ref)))
    ey = np.cross(w, ex)
    return ex, ey


class RayGrid:
    """All crossings of a triangle soup along a fixed direction, on a grid."""

    def __init__(self, T, origin, w, ex, ey):
        d = T.reshape(-1, 3) - origin
        loc = np.stack([d @ ex, d @ ey, d @ w], axis=1).reshape(-1, 3, 3)
        self.a, b, c = loc[:, 0], loc[:, 1], loc[:, 2]
        self.e1, self.e2 = b - self.a, c - self.a
        self.tu0, self.tu1 = loc[:, :, 0].min(axis=1), loc[:, :, 0].max(axis=1)
        self.tv0, self.tv1 = loc[:, :, 1].min(axis=1), loc[:, :, 1].max(axis=1)
        self.det = self.e1[:, 0] * self.e2[:, 1] - self.e1[:, 1] * self.e2[:, 0]
        self.ok = np.abs(self.det) > 1.0e-14
        self.order = np.argsort(self.tu0)
        self.tu0s = self.tu0[self.order]

    def hits(self, x, y):
        cand = self.order[:np.searchsorted(self.tu0s, x, side="right")]
        cand = cand[self.tu1[cand] >= x]
        if cand.size == 0:
            return np.zeros(0)
        sel = cand[(self.tv0[cand] <= y) & (self.tv1[cand] >= y)]
        if sel.size == 0:
            return np.zeros(0)
        A, E1, E2 = self.a[sel], self.e1[sel], self.e2[sel]
        d, o = self.det[sel], self.ok[sel]
        dx, dy = x - A[:, 0], y - A[:, 1]
        s = np.where(o, (dx * E2[:, 1] - dy * E2[:, 0]) / np.where(o, d, 1.0), -1.0)
        t = np.where(o, (E1[:, 0] * dy - E1[:, 1] * dx) / np.where(o, d, 1.0), -1.0)
        g = o & (s >= 0) & (t >= 0) & (s + t <= 1)
        if not g.any():
            return np.zeros(0)
        h = np.sort(A[g, 2] + s[g] * E1[g, 2] + t[g] * E2[g, 2])
        keep = np.ones(h.size, bool)
        keep[1:] = np.diff(h) > 1.0e-7
        return h[keep]


def scan(grid, X, Y, band):
    """Per-ray total material inside `band`, plus first/last crossing there."""
    thick = np.zeros((len(X), len(Y)))
    entry = np.full((len(X), len(Y)), np.nan)
    exitw = np.full((len(X), len(Y)), np.nan)
    mapped = np.zeros((len(X), len(Y)), bool)
    for i, x in enumerate(X):
        for j, y in enumerate(Y):
            h = grid.hits(x, y)
            if h.size % 2:
                continue          # broken parity: leave this ray unmapped
            mapped[i, j] = True
            if h.size == 0:
                continue          # no material at all IS the most open case;
                                  # excluding it (the first pass did) scores a
                                  # fully open control as 0 open area
            tot, first, last = 0.0, np.nan, np.nan
            for k in range(0, h.size, 2):
                lo, hi = max(h[k], band[0]), min(h[k + 1], band[1])
                if hi > lo:
                    tot += hi - lo
                    if not np.isfinite(first):
                        first = lo
                    last = hi
            thick[i, j] = tot
            entry[i, j] = first
            exitw[i, j] = last
    return thick, entry, exitw, mapped


def contour(mask, X, Y):
    er = ndimage.binary_erosion(mask, np.ones((3, 3), bool))
    b = mask & ~er
    iu, iv = np.nonzero(b)
    return np.stack([X[iu], Y[iv]], axis=1) if iu.size else np.zeros((0, 2))


def main() -> int:
    T15 = np.concatenate([read_stl(LOWER15_JAD), read_stl(LOWER15_JFD)])
    print("LOWER15 source: STL, %d triangles  [NON-EXACT / MESH ONLY]" % len(T15))
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    Tex = L.triangles(frozen, tol=0.05, ang=0.10)
    del frozen
    clean = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER", box, "CLEAN")
    Tcl = L.triangles(clean, tol=0.05, ang=0.10)
    del clean
    L.memory("sources")

    _, cartL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    _, cartO = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")

    X = np.arange(-PATCH, PATCH + 1e-9, PITCH)
    Y = np.arange(-PATCH, PATCH + 1e-9, PITCH)
    cellA = PITCH * PITCH
    rows = {}
    print("\n%-5s %10s %10s %12s %10s %10s %10s"
          % ("ctrl", "openArea", "capArea", "clearance", "wall t", "entry w", "exit w"))
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        capL, _ = L.as_single_solid(cartL[label], short)
        w, _, tilt = true_axis(capL)
        pts = L.surf_points(capL, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        ex, ey = axis_frame(w)
        d = pts - cen
        capx, capy = d @ ex, d @ ey
        cap_area = float((capx.max() - capx.min()) * (capy.max() - capy.min()))

        g15 = RayGrid(T15, cen, w, ex, ey)
        t15, e15, x15, m15 = scan(g15, X, Y, BAND)
        open15 = m15 & (t15 < MIN_WALL_FRAC)
        # keep only the component containing the axis
        lab, n = ndimage.label(open15)
        cx = int(np.argmin(np.abs(X)))
        cy = int(np.argmin(np.abs(Y)))
        cid = lab[cx, cy]
        if cid == 0 and n:
            sizes = ndimage.sum(open15, lab, range(1, n + 1))
            cid = int(np.argmax(sizes)) + 1
        main_open = lab == cid if cid else np.zeros_like(open15)
        area = float(main_open.sum()) * cellA
        iu, iv = np.nonzero(main_open)
        if iu.size:
            cxm = float(X[iu].mean())
            cym = float(Y[iv].mean())
        else:
            cxm = cym = float("nan")
        wall = m15 & ~open15
        ring = ndimage.binary_dilation(main_open, np.ones((7, 7), bool)) & wall
        wall_t = float(t15[ring].mean()) if ring.any() else float("nan")
        entry_w = float(np.nanmean(e15[ring])) if ring.any() else float("nan")
        exit_w = float(np.nanmean(x15[ring])) if ring.any() else float("nan")
        cont = contour(main_open, X, Y)
        # equivalent square side, and a clearance estimate vs the cap footprint
        side = float(np.sqrt(area)) if area > 0 else float("nan")
        cap_side = float(np.sqrt(cap_area))
        clr = 0.5 * (side - cap_side)

        # the same measurements on the exact STEP and on CLEAN at ORIGINAL pose
        gex = RayGrid(Tex, cen, w, ex, ey)
        tex, _, _, mex = scan(gex, X, Y, BAND)
        openex = mex & (tex < MIN_WALL_FRAC)
        lab2, n2 = ndimage.label(openex)
        cid2 = lab2[cx, cy]
        ex_area = float((lab2 == cid2).sum()) * cellA if cid2 else 0.0

        capO, _ = L.as_single_solid(cartO[label], short + "_o")
        wO, _, _ = true_axis(capO)
        ptsO = L.surf_points(capO, 40000, tol=0.05)
        cenO = ptsO.mean(axis=0)
        exO, eyO = axis_frame(wO)
        gcl = RayGrid(Tcl, cenO, wO, exO, eyO)
        tcl, _, _, mcl = scan(gcl, X, Y, BAND)
        opencl = mcl & (tcl < MIN_WALL_FRAC)
        lab3, n3 = ndimage.label(opencl)
        cid3 = lab3[cx, cy]
        orig_area = float((lab3 == cid3).sum()) * cellA if cid3 else 0.0

        rows[short] = {
            "source": "THUMB_LOWER15_HOUSING_V1 STL  [NON-EXACT / MESH ONLY]",
            "trueAxisWorld": w.tolist(), "tiltFromJoystickAxisDeg": tilt,
            "capCentroidWorld": cen.tolist(),
            "frameExWorld": ex.tolist(), "frameEyWorld": ey.tolist(),
            "approvedOpeningAreaMm2": area,
            "approvedOpeningCentroidLocalXY": [cxm, cym],
            "approvedOpeningEquivalentSideMm": side,
            "capFootprintBboxAreaMm2": cap_area, "capFootprintSideMm": cap_side,
            "impliedPerSideClearanceMm": clr,
            "surroundingWallThicknessMm": wall_t,
            "wallEntryWMm": entry_w, "wallExitWMm": exit_w,
            "openingBoundaryPointCount": int(len(cont)),
            "openingBoundaryLocalXY": cont[::4].tolist(),
            "exactStepOpeningAreaMm2": ex_area,
            "originalCleanOpeningAreaMm2": orig_area,
        }
        print("%-5s %10.3f %10.3f %12.4f %10.3f %10.3f %10.3f"
              % (short, area, cap_area, clr, wall_t, entry_w, exit_w))
        del capL, capO
        L.memory("opening " + short)

    print("\n%-5s %14s %14s %14s %12s"
          % ("ctrl", "approved(L15)", "exact STEP", "original(CLEAN)", "recovered"))
    for short in ORDER:
        r = rows[short]
        rec = (100.0 * r["exactStepOpeningAreaMm2"] / r["approvedOpeningAreaMm2"]
               if r["approvedOpeningAreaMm2"] > 0 else float("nan"))
        print("%-5s %14.3f %14.3f %14.3f %11.1f%%"
              % (short, r["approvedOpeningAreaMm2"], r["exactStepOpeningAreaMm2"],
                 r["originalCleanOpeningAreaMm2"], rec))

    L.write_json(OUT / "c01_approved_openings.json",
                 {"sourceQuality": {"LOWER15": "STL mesh only - NON-EXACT",
                                    "frozenStep": "exact B-rep",
                                    "cleanStep": "exact B-rep",
                                    "controlTransforms": "exact B-rep (frozen cartridge)"},
                  "patchHalfWidthMm": PATCH, "rayPitchMm": PITCH, "bandW": list(BAND),
                  "controls": rows, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
