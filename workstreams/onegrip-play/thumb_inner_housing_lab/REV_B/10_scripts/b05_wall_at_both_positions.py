"""B05 - the unambiguous authority test.

B04's "rays on the ORIGINAL control axes" pass turned out to be VACUOUS: the
original cap centroids sit at local n = 13.3 .. 20.8, while the Thumb wall of
every shell is at n ~ 11 .. 16.  A ray cast outward from a point that is already
at or beyond the outer skin finds no material outboard and is scored
C_THROUGH_OPENING no matter what the shell contains.

This script avoids ray origins entirely.  It reads the wall-thickness maps
computed in B03 (material inside the Thumb wall band per (u, v) column, no caps
involved) and samples them over each control footprint at BOTH the ORIGINAL and
the LOWERED control positions.

A shell that carries an opening at a position shows ~0 mm wall there.
A shell that has filled that opening shows a full ~3 mm wall there.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402

OUT = L.LAB / "01_axis_authority"
ORDER = ("JOY", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8")
HALF = 3.0          # sample a 6 x 6 mm patch centred on each control
OPEN_EPS = 0.05
FULL_WALL = 2.00


def sample(thick, any_mat, U, V, cu, cv, half=HALF):
    iu = np.nonzero((U >= cu - half) & (U <= cu + half))[0]
    iv = np.nonzero((V >= cv - half) & (V <= cv + half))[0]
    if iu.size == 0 or iv.size == 0:
        return None
    sub = thick[np.ix_(iu, iv)]
    msk = any_mat[np.ix_(iu, iv)]
    if not msk.any():
        return None
    vals = sub[msk]
    return {"cells": int(msk.sum()),
            "meanWallMm": float(vals.mean()),
            "medianWallMm": float(np.median(vals)),
            "maxWallMm": float(vals.max()),
            "openFraction": float((vals < OPEN_EPS).mean()),
            "fullWallFraction": float((vals >= FULL_WALL).mean())}


def main() -> int:
    meta = json.loads((OUT / "b04_true_axis_matrix.json").read_text(encoding="utf-8"))
    pos = {
        "ORIGINAL": {s: meta["originalControlFrames"][s]["capCentroidLocal"][:2] for s in ORDER},
        "LOWERED": {s: meta["loweredControlFrames"][s]["capCentroidLocal"][:2] for s in ORDER},
    }

    result = {}
    for tag in ("CLEAN", "FINGER_V2", "FROZEN"):
        z = np.load(OUT / ("b03_wallmap_%s.npz" % tag))
        U, V, thick, any_mat = z["U"], z["V"], z["thick"], z["any_mat"]
        if tag == "CLEAN":
            # B03 translated CLEAN by +THUMB_DELTA before mapping, so its map is
            # expressed in a frame shifted by the delta.  Undo that here by
            # shifting the axes back, rather than re-running the map.
            dv = float(L.THUMB_DELTA @ L.DATUM_V)
            du = float(L.THUMB_DELTA @ L.DATUM_U)
            U = U - du
            V = V - dv
        rows = {}
        print("\n=== %s : Thumb-wall thickness over each control footprint ===" % tag)
        print("%-5s | %-38s | %-38s" % ("ctrl", "at ORIGINAL position", "at LOWERED position"))
        print("%-5s | %-12s %-12s %-11s | %-12s %-12s %-11s"
              % ("", "mean wall", "open frac", "full frac", "mean wall", "open frac", "full frac"))
        for s in ORDER:
            a = sample(thick, any_mat, U, V, *pos["ORIGINAL"][s])
            b = sample(thick, any_mat, U, V, *pos["LOWERED"][s])
            rows[s] = {"atOriginal": a, "atLowered": b}
            fmt = lambda r: ("%-12.3f %-12.1f%% %-11.1f%%" % (r["meanWallMm"],
                             100 * r["openFraction"], 100 * r["fullWallFraction"])
                             if r else "%-38s" % "outside mapped region")
            print("%-5s | %s | %s" % (s, fmt(a), fmt(b)))
        result[tag] = rows

    print("\n\n=== VERDICT ===")
    print("%-11s | %-28s | %-28s" % ("shell", "openings at ORIGINAL pos", "openings at LOWERED pos"))
    verdict = {}
    for tag in ("CLEAN", "FINGER_V2", "FROZEN"):
        no = sum(1 for s in ORDER if result[tag][s]["atOriginal"]
                 and result[tag][s]["atOriginal"]["openFraction"] > 0.25)
        nl = sum(1 for s in ORDER if result[tag][s]["atLowered"]
                 and result[tag][s]["atLowered"]["openFraction"] > 0.25)
        mo = float(np.mean([result[tag][s]["atOriginal"]["meanWallMm"] for s in ORDER
                            if result[tag][s]["atOriginal"]]))
        ml = float(np.mean([result[tag][s]["atLowered"]["meanWallMm"] for s in ORDER
                            if result[tag][s]["atLowered"]]))
        verdict[tag] = {"controlsOpenAtOriginal": no, "controlsOpenAtLowered": nl,
                        "meanWallAtOriginalMm": mo, "meanWallAtLoweredMm": ml}
        print("%-11s | %d of 9 open, mean wall %5.3f mm | %d of 9 open, mean wall %5.3f mm"
              % (tag, no, mo, nl, ml))

    L.write_json(OUT / "b05_wall_at_both_positions.json",
                 {"controlPositionsLocalUV": pos, "sampleHalfWidthMm": HALF,
                  "perShell": result, "verdict": verdict})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
