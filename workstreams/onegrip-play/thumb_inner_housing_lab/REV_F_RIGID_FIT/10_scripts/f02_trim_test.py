"""F02 - concrete trim outcome at the two candidate poses (REV_F sections 3-5).

F01 showed the trade-off as point statistics.  This measures it as solid volume:
place the ORIGINAL Backplate rigidly, subtract the exact approved shell grown by
the design clearance, and report what actually survives.

POSE A  pure THUMB_DELTA            registration exact, gap p50 +9.153
POSE B  + 7.109 mm along the seat   registration 0.89 mm lateral, gap p50 +1.963
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, export_step, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import true_axis  # noqa: E402
from d02_housing_vs_exact import BP_STEP, Field, approved_shell  # noqa: E402
from e01_probe import ZONES  # noqa: E402

OUT = L.LAB / "02_candidate"
OUTWARD = -L.DATUM_N
TRIM_CLEARANCE = 1.00
PITCH = 0.25


def rotmat(a):
    ax, ay, az = a
    Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    Rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def main() -> int:
    fit = json.loads((L.LAB / "01_rigidfit" / "f01_rigid_fit.json").read_text(encoding="utf-8"))
    approved = approved_shell()
    bp0 = import_step(str(BP_STEP))
    bp0, _ = L.as_single_solid(bp0, "BACKPLATE")
    v0 = L.vol(bp0)
    print("ORIGINAL Backplate volume = %.4f mm3" % v0)
    L.memory("loaded")

    poses = [("POSE_A_CONTROL_ALIGNED", fit["poses"]["POSE_A_CONTROL_ALIGNED"]["params"]),
             ("POSE_B_TRANSLATION_ONLY", fit["poses"]["POSE_B_TRANSLATION_ONLY"]["params"])]

    U = np.arange(-24.0, 24.0 + 1e-9, PITCH)
    V = np.arange(-52.0, 16.0 + 1e-9, PITCH)
    cell = PITCH * PITCH
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")

    rows = {}
    for tag, par in poses:
        par = np.asarray(par, float)
        if np.any(np.abs(par[:3]) > 1e-9):
            raise RuntimeError("rotation not supported in this simple placement path")
        moved = bp0.moved(Location(Vector(*[float(x) for x in (L.THUMB_DELTA + par[3:])])))
        inter = L.inter_vol(moved, approved)
        print("\n=== %s ===" % tag)
        print("  interference with the exact approved shell BEFORE trim = %.4f mm3  (%.1f %% of the plate)"
              % (inter, 100 * inter / v0))

        # trim: subtract the shell grown by the design clearance, in every direction
        cur = moved
        for d in (np.zeros(3), L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V,
                  -L.DATUM_N, L.DATUM_N):
            tool = approved if not np.any(d) else approved.moved(
                Location(Vector(*[float(x) for x in (d * TRIM_CLEARANCE)])))
            iv = L.inter_vol(cur, tool)
            if iv > 1e-9:
                cur = (cur - tool).clean()
                if not cur.solids():
                    break
        pieces = list(cur.solids()) if cur.solids() else []
        vsurv = float(sum(float(s.volume) for s in pieces))
        print("  after trim: %d solids, volume %.4f mm3 = %.1f %% of the original"
              % (len(pieces), vsurv, 100 * vsurv / v0))
        if pieces:
            big = sorted(pieces, key=lambda s: -float(s.volume))
            print("  largest piece %.4f mm3 (%.1f %% of the original)"
                  % (float(big[0].volume), 100 * float(big[0].volume) / v0))
            print("  piece sizes: %s"
                  % ", ".join("%.2f" % float(s.volume) for s in big[:8]))
            keep, _ = L.as_single_solid(cur, tag + "_TRIMMED")
            export_step(keep, str(OUT / ("C03_%s_TRIMMED.step" % tag)))
        else:
            keep = None
            print("  nothing survives the trim")

        row = {"interferenceBeforeTrimMm3": inter,
               "interferenceFractionOfPlate": inter / v0,
               "survivingVolumeMm3": vsurv,
               "survivingFraction": vsurv / v0,
               "pieceCount": len(pieces),
               "pieceVolumesMm3": sorted([float(s.volume) for s in pieces], reverse=True)[:12]}

        # do the controls still have plate under them, and do the load zones survive?
        if keep is not None:
            f = Field(L.local_triangles(keep, tol=0.06, ang=0.12))
            t = np.zeros((len(U), len(V)))
            for i, u in enumerate(U):
                for j, v in enumerate(V):
                    h = f.hits(u, v)
                    if h.size and h.size % 2 == 0:
                        t[i, j] = float(sum(h[k + 1] - h[k] for k in range(0, h.size, 2)))
            plate = t > 1e-6
            row["planAreaMm2"] = plate.sum() * cell
            print("  surviving plan area %.2f mm2" % row["planAreaMm2"])
            zr = {}
            for name, zn in ZONES.items():
                m = ((U[:, None] >= zn["u"][0]) & (U[:, None] <= zn["u"][1]) &
                     (V[None, :] >= zn["v"][0]) & (V[None, :] <= zn["v"][1]))
                zr[name] = {"survivingAreaMm2": float((m & plate).sum()) * cell,
                            "footprintMm2": float(m.sum()) * cell,
                            "originalTargetMm2": zn["targetMm2"]}
                print("     %-6s load zone: %7.2f mm2 of %7.2f footprint (original target %.2f)"
                      % (name, zr[name]["survivingAreaMm2"], zr[name]["footprintMm2"],
                         zn["targetMm2"]))
            row["loadZones"] = zr
            cov = {}
            for short in ORDER:
                label = next(k for k, v in NAME_MAP.items() if v == short)
                cap, _ = L.as_single_solid(cart[label], short)
                c = L.surf_points(cap, 20000, tol=0.06).mean(axis=0)
                lc = L.to_local(c)[0]
                i = int(round((lc[0] - U[0]) / PITCH))
                j = int(round((lc[1] - V[0]) / PITCH))
                near = plate[max(0, i - 12):i + 13, max(0, j - 12):j + 13]
                cov[short] = float(near.mean()) if near.size else 0.0
                del cap
            row["controlSeatCoverage"] = cov
            print("  plate present within 3 mm of each control centre:")
            print("     " + "  ".join("%s %.0f%%" % (s, 100 * cov[s]) for s in ORDER))
        rows[tag] = row
        L.memory("trim " + tag)

    L.write_json(OUT / "f02_trim_test.json",
                 {"trimClearanceMm": TRIM_CLEARANCE, "originalVolumeMm3": v0,
                  "poses": rows, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
