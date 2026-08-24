"""C06 - containment proof by sampling, and attribution of the opening excess.

C05's containment test used vol(REC & FROZEN) and OCC returned -44.899 mm3, a
negative volume.  That is the same ill-conditioned near-coincident shell boolean
already documented in REV_A (identical -44.8986 figure).  Booleans between these
two shells are unusable in either direction, so containment is proved by point
membership instead.

Attribution answers: of the excess opening area, how much did the frozen STEP
already have (inherited, unfixable by cutting) and how much did the reconciled
cutter add?
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, true_axis  # noqa: E402
from b07_lineage_and_visual import LOWER15_JAD, LOWER15_JFD, read_stl  # noqa: E402
from c01_approved_openings import PATCH, PITCH, axis_frame  # noqa: E402
from c04_validate import RECON, open_set  # noqa: E402

OUT = L.LAB / "04_validation"


def main() -> int:
    rec = import_step(str(RECON))
    rec, _ = L.as_single_solid(rec, "RECON")
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    L.memory("sources")

    # ---- containment by point membership --------------------------------
    print("=== containment by point membership (booleans are unusable here) ===")
    occ_r = L.Occupancy(rec, tol=0.05, ang=0.10)
    occ_f = L.Occupancy(frozen, tol=0.05, ang=0.10)
    U, V, N = L.grid_axes((-26.0, -52.0, -34.0), (26.0, 16.0, 20.0), 0.5)
    inside_r = occ_r.inside(U, V, N)
    inside_f = occ_f.inside(U, V, N)
    cell = 0.5 ** 3
    added = inside_r & ~inside_f
    removed = inside_f & ~inside_r
    print("  cells inside RECONCILED        : %8d  (%10.3f mm3)"
          % (int(inside_r.sum()), inside_r.sum() * cell))
    print("  cells inside FROZEN            : %8d  (%10.3f mm3)"
          % (int(inside_f.sum()), inside_f.sum() * cell))
    print("  cells in RECONCILED not FROZEN : %8d  (%10.3f mm3)  <- material ADDED"
          % (int(added.sum()), added.sum() * cell))
    print("  cells in FROZEN not RECONCILED : %8d  (%10.3f mm3)  <- material REMOVED"
          % (int(removed.sum()), removed.sum() * cell))
    print("  exact volume difference        : %10.3f mm3" % (L.vol(frozen) - L.vol(rec)))
    # Are the "added" cells real, or 0.5 mm cells straddling a surface?
    # A real added blob survives erosion; boundary noise does not.
    eroded = ndimage.binary_erosion(added, np.ones((3, 3, 3), bool))
    lab_a, n_a = ndimage.label(added)
    print("  ADDED cells surviving 3x3x3 erosion : %d  (a real blob would survive)"
          % int(eroded.sum()))
    print("  ADDED connected components          : %d, largest %d cells"
          % (n_a, int(max(ndimage.sum(added, lab_a, range(1, n_a + 1))) if n_a else 0)))
    if added.any():
        iu, iv, inn = np.nonzero(added)
        print("  ADDED cells local bbox: u[%.2f,%.2f] v[%.2f,%.2f] n[%.2f,%.2f]"
              % (U[iu.min()], U[iu.max()], V[iv.min()], V[iv.max()],
                 N[inn.min()], N[inn.max()]))
    L.memory("containment")

    # ---- attribution ----------------------------------------------------
    T15 = np.concatenate([read_stl(LOWER15_JAD), read_stl(LOWER15_JFD)])
    Trc = L.triangles(rec, tol=0.05, ang=0.10)
    Tfz = L.triangles(frozen, tol=0.05, ang=0.10)
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    X = np.arange(-PATCH, PATCH + 1e-9, PITCH)
    Y = np.arange(-PATCH, PATCH + 1e-9, PITCH)
    cellA = PITCH * PITCH

    print("\n=== where does the excess come from? ===")
    print("%-5s %11s %11s %11s %11s %11s"
          % ("ctrl", "excess REC", "excess FZ", "inherited", "added by cut", "deficit REC"))
    rows = {}
    tot = {"exc": 0.0, "inh": 0.0, "new": 0.0, "dfc": 0.0}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, _ = true_axis(cap)
        pts = L.surf_points(cap, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        ex, ey = axis_frame(w)
        m_r, _, _, _, _ = open_set(Trc, cen, w, ex, ey, X, Y)
        m_f, _, _, _, _ = open_set(Tfz, cen, w, ex, ey, X, Y)
        # open_set falls back to the LARGEST component when the axis itself is
        # sealed.  In the frozen shell T2/T4/T6/T7/T8 are sealed, so the fallback
        # returns a NEIGHBOURING control's hole and the "excess FZ" column
        # becomes meaningless.  Require the axis to be open for the frozen pass.
        cxi = int(np.argmin(np.abs(X)))
        cyi = int(np.argmin(np.abs(Y)))
        if not m_f[cxi, cyi]:
            m_f = np.zeros_like(m_f)
        m_a, _, _, _, _ = open_set(T15, cen, w, ex, ey, X, Y)
        e_r = (m_r & ~m_a)
        e_f = (m_f & ~m_a)
        inherited = float((e_r & e_f).sum()) * cellA
        newly = float((e_r & ~e_f).sum()) * cellA
        dfc = float((m_a & ~m_r).sum()) * cellA
        rows[short] = {"excessReconciledMm2": float(e_r.sum()) * cellA,
                       "excessFrozenMm2": float(e_f.sum()) * cellA,
                       "excessInheritedFromFrozenMm2": inherited,
                       "excessAddedByReconciledCutMm2": newly,
                       "deficitMm2": dfc}
        for k, v in (("exc", float(e_r.sum()) * cellA), ("inh", inherited),
                     ("new", newly), ("dfc", dfc)):
            tot[k] += v
        print("%-5s %11.3f %11.3f %11.3f %11.3f %11.3f"
              % (short, float(e_r.sum()) * cellA, float(e_f.sum()) * cellA,
                 inherited, newly, dfc))
        del cap
    print("%-5s %11.3f %11s %11.3f %11.3f %11.3f"
          % ("TOTAL", tot["exc"], "", tot["inh"], tot["new"], tot["dfc"]))
    print("\n  %.1f %% of the excess is inherited from the frozen STEP's own over-cut"
          % (100.0 * tot["inh"] / max(1e-9, tot["exc"])))

    L.write_json(OUT / "c06_containment_attribution.json",
                 {"containment": {"cellMm": 0.5,
                                  "reconciledCells": int(inside_r.sum()),
                                  "frozenCells": int(inside_f.sum()),
                                  "addedCells": int(added.sum()),
                                  "addedVolumeMm3": float(added.sum()) * cell,
                                  "removedCells": int(removed.sum()),
                                  "removedVolumeMm3": float(removed.sum()) * cell,
                                  "exactVolumeDifferenceMm3": L.vol(frozen) - L.vol(rec)},
                  "attribution": rows, "totals": tot,
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
