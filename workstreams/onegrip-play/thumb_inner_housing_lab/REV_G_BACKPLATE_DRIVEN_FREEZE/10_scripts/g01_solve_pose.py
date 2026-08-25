"""G01 - solve the Backplate-driven pose (REV_G sections 5, 6).

The OLD JOY/T1-T8 positions are no longer constraints.  The pose is driven by
the ORIGINAL shell-to-Backplate relationship instead:

    general plate area      0.8 - 1.6 mm clearance
    LEFT / RIGHT load zones 0.00 - 0.15 mm  (intentional structural contact)
    interference            only what can honestly be trimmed
    N1/N2 + rear harness    clear

The plate is never deformed.  Only a 6-DOF rigid transform is searched, seeded
from THUMB_DELTA.  Load-zone membership travels with the plate: each outer-face
sample is tagged GENERAL / LEFT / RIGHT once, in the plate's own original frame.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import true_axis  # noqa: E402
from d02_housing_vs_exact import BP_STEP, Field, approved_shell  # noqa: E402
from e01_probe import ZONES  # noqa: E402
from f01_rigid_fit import rot, sample_field, shell_height_field  # noqa: E402

OUT = L.LAB / "01_pose"
OUTWARD = -L.DATUM_N
ORIG_P = L.DATUM_P - L.THUMB_DELTA
PITCH = 0.25
GEN_LO, GEN_HI = 0.80, 1.60          # desired general clearance band
ZONE_TARGET = 0.075                  # midpoint of the 0.00 - 0.15 contact band
KEEPOUTS = L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"
HARNESS_MM = 15.0


def main() -> int:
    approved = approved_shell()
    bp = import_step(str(BP_STEP))
    bp, _ = L.as_single_solid(bp, "BACKPLATE")
    print("ORIGINAL Backplate vol=%.4f mm3  faces=%d" % (L.vol(bp), len(list(bp.faces()))))

    # ---- outer-face samples, tagged by original-frame (u, v) -------------
    T = L.triangles(bp, tol=0.06, ang=0.12)
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(nrm, axis=1)
    ok = ln > 1e-12
    nrm[ok] /= ln[ok][:, None]
    outer = nrm @ OUTWARD > 0.55
    To = T[outer]
    a3, b3, c3 = To[:, 0], To[:, 1], To[:, 2]
    area = 0.5 * np.linalg.norm(np.cross(b3 - a3, c3 - a3), axis=1)
    rng = np.random.default_rng(20260825)
    counts = np.maximum(1, np.round(area / area.sum() * 24000).astype(int))
    ii = np.repeat(np.arange(len(To)), counts)
    r1 = rng.random(len(ii))
    r2 = rng.random(len(ii))
    sq = np.sqrt(r1)
    pts = ((1 - sq)[:, None] * a3[ii] + (sq * (1 - r2))[:, None] * b3[ii]
           + (sq * r2)[:, None] * c3[ii])
    w_pt = np.repeat(area / counts, counts)          # per-sample area weight
    d0 = pts - ORIG_P
    ou, ov = d0 @ L.DATUM_U, d0 @ L.DATUM_V
    tag = np.zeros(len(pts), int)                    # 0 general, 1 left, 2 right
    for k, (name, zn) in enumerate(ZONES.items(), start=1):
        m = (ou >= zn["u"][0]) & (ou <= zn["u"][1]) & (ov >= zn["v"][0]) & (ov <= zn["v"][1])
        tag[m] = k
    print("outer-face samples %d   area %.2f mm2   LEFT %d   RIGHT %d"
          % (len(pts), area.sum(), int((tag == 1).sum()), int((tag == 2).sum())))
    print("  zone sample area: LEFT %.2f mm2   RIGHT %.2f mm2"
          % (w_pt[tag == 1].sum(), w_pt[tag == 2].sum()))

    U = np.arange(-30.0, 30.0 + 1e-9, PITCH)
    V = np.arange(-56.0, 20.0 + 1e-9, PITCH)
    hfield = shell_height_field(approved, U, V)
    print("shell inner-surface field: %d of %d columns defined"
          % (int(np.isfinite(hfield).sum()), hfield.size))
    L.memory("field")

    centre = pts.mean(axis=0)

    def place(par, P=None):
        R = rot(np.asarray(par)[:3])
        t = np.asarray(par)[3:]
        p = (pts if P is None else P)
        q = (p - centre) @ R.T + centre + L.THUMB_DELTA + t
        d = q - L.DATUM_P
        return np.stack([d @ L.DATUM_U, d @ L.DATUM_V, d @ OUTWARD], axis=1)

    def gaps(par):
        uvn = place(par)
        hs = sample_field(hfield, U, V, uvn[:, :2])
        return hs - uvn[:, 2]

    def cost(par):
        g = gaps(par)
        cov = np.isfinite(g)
        if cov.sum() < 500:
            return 1e9
        w = w_pt.copy()
        gg = np.where(cov, g, np.nan)
        gen = cov & (tag == 0)
        zone = cov & (tag > 0)
        # general band: only penalise outside [GEN_LO, GEN_HI]
        dev = np.zeros(len(g))
        dev[gen] = np.maximum(0.0, GEN_LO - gg[gen]) + np.maximum(0.0, gg[gen] - GEN_HI)
        c_gen = float(np.sum(w[gen] * dev[gen] ** 2) / max(1e-9, w[gen].sum()))
        c_zone = (float(np.sum(w[zone] * (gg[zone] - ZONE_TARGET) ** 2)
                        / max(1e-9, w[zone].sum())) if zone.any() else 0.0)
        # interference: heavy, one-sided
        under = np.maximum(0.0, -gg[cov])
        c_int = float(np.sum(w[cov] * under ** 2) / max(1e-9, w[cov].sum()))
        # keep the plate under the shell
        c_cov = float(1.0 - w[cov].sum() / w.sum())
        return c_gen + 2.0 * c_zone + 6.0 * c_int + 30.0 * c_cov ** 2

    def report(par, tag_str):
        g = gaps(par)
        cov = np.isfinite(g)
        gg = g[cov]
        w = w_pt[cov]
        tg = tag[cov]
        def pct(x, ww, q):
            o = np.argsort(x)
            cw = np.cumsum(ww[o]) / ww.sum()
            return float(x[o][np.searchsorted(cw, q / 100.0)])
        row = {"params": list(np.asarray(par, float)),
               "coveredAreaFraction": float(w.sum() / w_pt.sum()),
               "gapPercentilesMm": {str(q): pct(gg, w, q) for q in (5, 25, 50, 75, 95)},
               "gapMinMm": float(gg.min()), "gapMaxMm": float(gg.max()),
               "interferingAreaMm2": float(w[gg < 0].sum()),
               "generalInBandAreaMm2": float(w[(tg == 0) & (gg >= GEN_LO) & (gg <= GEN_HI)].sum()),
               "generalAreaMm2": float(w[tg == 0].sum())}
        for k, name in enumerate(ZONES, start=1):
            m = tg == k
            row["zone" + name] = {
                "areaMm2": float(w[m].sum()),
                "contactAreaMm2": float(w[m & (gg >= -0.05) & (gg <= 0.30)].sum()),
                "gapP50": pct(gg[m], w[m], 50) if m.any() else None,
                "gapMin": float(gg[m].min()) if m.any() else None}
        print("\n%s" % tag_str)
        print("  covered area %.1f %%   gap p05/p25/p50/p75/p95 = %+.3f / %+.3f / %+.3f / %+.3f / %+.3f"
              % (100 * row["coveredAreaFraction"],
                 *[row["gapPercentilesMm"][k] for k in ("5", "25", "50", "75", "95")]))
        print("  gap min/max = %+.3f / %+.3f   interfering area %.2f mm2"
              % (row["gapMinMm"], row["gapMaxMm"], row["interferingAreaMm2"]))
        print("  general area in 0.8-1.6 band: %.2f of %.2f mm2 (%.1f %%)"
              % (row["generalInBandAreaMm2"], row["generalAreaMm2"],
                 100 * row["generalInBandAreaMm2"] / max(1e-9, row["generalAreaMm2"])))
        for name in ZONES:
            zr = row["zone" + name]
            print("  %-6s zone %7.2f mm2   contact(-0.05..0.30) %7.2f mm2   gap p50 %s  min %s"
                  % (name, zr["areaMm2"], zr["contactAreaMm2"],
                     ("%+.3f" % zr["gapP50"]) if zr["gapP50"] is not None else "-",
                     ("%+.3f" % zr["gapMin"]) if zr["gapMin"] is not None else "-"))
        return row

    res = {}
    res["SEED_THUMB_DELTA"] = report(np.zeros(6), "SEED - pure THUMB_DELTA (old control-aligned pose)")

    best, bestc = None, 1e18
    starts = [np.zeros(6)]
    for dv in (-6.0, -12.0, -18.0):
        for dn in (4.0, 8.0, 12.0):
            starts.append(np.array([0, 0, 0, 0.0, dv, dn]))
    for s0 in starts:
        r = minimize(cost, s0, method="Nelder-Mead",
                     options={"xatol": 1e-4, "fatol": 1e-8, "maxiter": 6000, "maxfev": 9000})
        if r.fun < bestc:
            bestc, best = float(r.fun), np.asarray(r.x, float)
    print("\nbest cost %.6f from %d starts" % (bestc, len(starts)))
    res["SOLVED"] = report(best, "SOLVED backplate-driven pose")
    res["SOLVED"]["rotationDeg"] = list(np.degrees(best[:3]))
    res["SOLVED"]["translationMm"] = list(best[3:])
    print("  rotation %s deg   translation %s mm"
          % (np.round(np.degrees(best[:3]), 4), np.round(best[3:], 4)))
    L.memory("solved")

    # ---- the pose as a world transform, and the new control geometry -----
    R = rot(best[:3])
    t = np.asarray(best[3:], float)
    off = centre + L.THUMB_DELTA + t - centre @ R.T
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = off
    print("\nworld transform of the ORIGINAL Backplate (row-major 4x4):")
    for r_ in M:
        print("   [%12.6f %12.6f %12.6f %12.6f]" % tuple(r_))

    _, cartO = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    _, cartL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    ctrl = {}
    print("\n=== NEW control geometry, derived rigidly from the pose ===")
    print("%-5s %-34s %-34s %10s" % ("ctrl", "new centre (world)", "new axis (world)", "|d| old"))
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        capO, _ = L.as_single_solid(cartO[label], short)
        wO, _, _ = true_axis(capO)
        cO = L.surf_points(capO, 30000, tol=0.06).mean(axis=0)
        capL, _ = L.as_single_solid(cartL[label], short)
        wL, _, _ = true_axis(capL)
        cL = L.surf_points(capL, 30000, tol=0.06).mean(axis=0)
        cN = R @ cO + off
        wN = R @ wO
        dv = cN - cL
        ang = float(np.degrees(np.arccos(np.clip(abs(float(wN @ wL)), -1, 1))))
        ctrl[short] = {"newCentreWorld": cN.tolist(), "newAxisWorld": wN.tolist(),
                       "oldCentreWorld": cL.tolist(), "oldAxisWorld": wL.tolist(),
                       "deltaXYZ": dv.tolist(),
                       "centreDisplacementMm": float(np.linalg.norm(dv)),
                       "axisAngularChangeDeg": ang,
                       "displacementAlongOldAxisMm": float(dv @ wL),
                       "newCentreLocal": L.to_local(cN)[0].tolist()}
        print("%-5s %-34s %-34s %10.4f"
              % (short, np.array2string(np.round(cN, 4)), np.array2string(np.round(wN, 5)),
                 float(np.linalg.norm(dv))))
        del capO, capL

    L.write_json(OUT / "g01_solve_pose.json",
                 {"generalBandMm": [GEN_LO, GEN_HI], "zoneTargetMm": ZONE_TARGET,
                  "poses": res, "worldTransform4x4": M.tolist(),
                  "rotationDeg": list(np.degrees(best[:3])),
                  "translationMm": list(best[3:]),
                  "newControls": ctrl, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
