"""A08 - where are the FROZEN exterior Thumb openings, really?

Builds a (u, v) map of the Thumb wall: for every column, is the wall
  OPEN        (no material in the Thumb wall band)
  FULL        (a wall slab >= 2.0 mm)
  PARTIAL     (a thinned slab)
and overlays the 9 lowered control footprints.

Also reports, per control, the fraction of its footprint that is actually open,
which is the honest measure of whether that control has a usable opening.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from a07_conformity_map import ColumnField, combined_shell, tri_frame, ORIG_P  # noqa: E402

OUT = L.LAB / "05_sections"
CROP_LO = (-32.0, -54.0, -60.0)
CROP_HI = (32.0, 24.0, 60.0)
PITCH = 0.25

# lowered cap footprints in local (u, v) from A03 (exact bboxes)
FOOTPRINTS = {
    "T1_corner_1": (7.21, 14.80, -45.38, -37.50),
    "T2_middle_1": (-3.79, 3.81, -34.34, -26.43),
    "T3_corner_2": (-14.79, -7.20, -45.38, -37.50),
    "T4_side_1": (7.21, 14.81, -34.35, -26.43),
    "T5_middle_2": (-3.79, 3.81, -45.31, -37.40),
    "T6_side_2": (-14.79, -7.19, -34.35, -26.43),
    "T7_wide_1": (3.36, 12.96, -21.58, -14.66),
    "T8_wide_2": (-12.95, -3.35, -21.58, -14.66),
    "JOYSTICK": (-7.00, 7.00, -6.98, 6.98),
}
# n band that contains the Thumb wall in each frame
BAND_CURRENT = (2.0, 22.0)
BAND_ORIGINAL = (2.0, 22.0)


def wall_state(field: ColumnField, U, V, band):
    """0 = no wall (OPEN), else total material thickness inside the band."""
    thick = np.zeros((len(U), len(V)))
    inner = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            h = field.hits(u, v, field.candidates(u, v))
            if h.size == 0 or h.size % 2:
                continue
            tot = 0.0
            first = np.nan
            for k in range(0, h.size, 2):
                lo, hi = h[k], h[k + 1]
                a, b = max(lo, band[0]), min(hi, band[1])
                if b > a:
                    tot += b - a
                    if not np.isfinite(first):
                        first = lo
            thick[i, j] = tot
            inner[i, j] = first
    return thick, inner


def main() -> int:
    U = np.arange(-26.0, 26.0 + 1e-9, PITCH)
    V = np.arange(-50.0, 14.0 + 1e-9, PITCH)

    box_cur = L.local_box(CROP_LO, CROP_HI, "CUR")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box_cur, "FROZEN")
    f_cur = ColumnField(tri_frame(frozen, L.DATUM_P))
    t_cur, i_cur = wall_state(f_cur, U, V, BAND_CURRENT)
    del frozen, f_cur
    L.memory("frozen wall state")

    lo_o = np.asarray(CROP_LO, float)
    hi_o = np.asarray(CROP_HI, float)
    world = np.asarray([ORIG_P + p[0] * L.DATUM_U + p[1] * L.DATUM_V + p[2] * (-L.DATUM_N)
                        for p in (lo_o, hi_o)])
    loc = L.to_local(world)
    box_orig = L.local_box(loc[0], loc[1], "ORIG")
    clean = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER", box_orig, "CLEAN")
    f_org = ColumnField(tri_frame(clean, ORIG_P))
    t_org, i_org = wall_state(f_org, U, V, BAND_ORIGINAL)
    del clean, f_org
    L.memory("clean wall state")

    rows = {}
    print("\n%-14s | %-28s | %-28s" % ("control", "FROZEN (lowered exterior)", "CLEAN (original exterior)"))
    print("-" * 78)
    for name, (u0, u1, v0, v1) in FOOTPRINTS.items():
        m = ((U[:, None] >= u0) & (U[:, None] <= u1) &
             (V[None, :] >= v0) & (V[None, :] <= v1))
        cells = int(m.sum())
        row = {"footprintCells": cells}
        for tag, t in (("FROZEN", t_cur), ("CLEAN", t_org)):
            open_frac = float((t[m] < 0.05).mean())
            row[tag] = {"openFraction": open_frac,
                        "meanWallThicknessMm": float(t[m].mean()),
                        "maxWallThicknessMm": float(t[m].max())}
        rows[name] = row
        print("%-14s | open %6.1f%%  meanWall %5.2f mm | open %6.1f%%  meanWall %5.2f mm"
              % (name, 100.0 * row["FROZEN"]["openFraction"], row["FROZEN"]["meanWallThicknessMm"],
                 100.0 * row["CLEAN"]["openFraction"], row["CLEAN"]["meanWallThicknessMm"]))

    np.savez_compressed(OUT / "a08_opening_map.npz", U=U, V=V,
                        frozen_thick=t_cur, frozen_inner=i_cur,
                        clean_thick=t_org, clean_inner=i_org)
    L.write_json(OUT / "a08_opening_map.json",
                 {"gridPitchMm": PITCH, "band": {"current": list(BAND_CURRENT),
                                                 "original": list(BAND_ORIGINAL)},
                  "footprints": FOOTPRINTS, "controls": rows, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
