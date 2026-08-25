"""G02 - how much lowering can be kept, and what does it cost?

G01's unconstrained solve returned the ORIGINAL pre-lowering position: it undoes
95.0 % of the approved 24.312 mm lowering, because the original Backplate only
conforms to the grip shell where it was designed to sit.

A binary answer is not useful, so this sweeps the retained-lowering fraction f
and, at each f, optimises everything else (rotation + up to +-3 mm of tangential
slack).  net displacement from the ORIGINAL position = f * THUMB_DELTA + s.

    f = 1.00   the approved maximum-lowered Thumb
    f = 0.00   the original Thumb position
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from d02_housing_vs_exact import BP_STEP, approved_shell  # noqa: E402
from e01_probe import ZONES  # noqa: E402
from f01_rigid_fit import rot, sample_field, shell_height_field  # noqa: E402

OUT = L.LAB / "01_pose"
OUTWARD = -L.DATUM_N
ORIG_P = L.DATUM_P - L.THUMB_DELTA
PITCH = 0.25
GEN_LO, GEN_HI = 0.80, 1.60
ZONE_TARGET = 0.075
SLACK = 3.0
FRACTIONS = [1.00, 0.90, 0.80, 0.70, 0.60, 0.50, 0.35, 0.20, 0.10, 0.00]


def main() -> int:
    approved = approved_shell()
    bp = import_step(str(BP_STEP))
    bp, _ = L.as_single_solid(bp, "BACKPLATE")

    T = L.triangles(bp, tol=0.06, ang=0.12)
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(nrm, axis=1)
    ok = ln > 1e-12
    nrm[ok] /= ln[ok][:, None]
    To = T[nrm @ OUTWARD > 0.55]
    a3, b3, c3 = To[:, 0], To[:, 1], To[:, 2]
    area = 0.5 * np.linalg.norm(np.cross(b3 - a3, c3 - a3), axis=1)
    rng = np.random.default_rng(20260825)
    counts = np.maximum(1, np.round(area / area.sum() * 16000).astype(int))
    ii = np.repeat(np.arange(len(To)), counts)
    r1 = rng.random(len(ii))
    r2 = rng.random(len(ii))
    sq = np.sqrt(r1)
    pts = ((1 - sq)[:, None] * a3[ii] + (sq * (1 - r2))[:, None] * b3[ii]
           + (sq * r2)[:, None] * c3[ii])
    w = np.repeat(area / counts, counts)
    d0 = pts - ORIG_P
    ou, ov = d0 @ L.DATUM_U, d0 @ L.DATUM_V
    tag = np.zeros(len(pts), int)
    for k, (name, zn) in enumerate(ZONES.items(), start=1):
        tag[(ou >= zn["u"][0]) & (ou <= zn["u"][1]) &
            (ov >= zn["v"][0]) & (ov <= zn["v"][1])] = k

    U = np.arange(-30.0, 30.0 + 1e-9, PITCH)
    V = np.arange(-56.0, 20.0 + 1e-9, PITCH)
    hf = shell_height_field(approved, U, V)
    L.memory("field")
    centre = pts.mean(axis=0)

    def gaps(par, f):
        R = rot(np.asarray(par)[:3])
        s = np.asarray(par)[3:]
        t = (f - 1.0) * L.THUMB_DELTA + s
        q = (pts - centre) @ R.T + centre + L.THUMB_DELTA + t
        d = q - L.DATUM_P
        uvn = np.stack([d @ L.DATUM_U, d @ L.DATUM_V, d @ OUTWARD], axis=1)
        return sample_field(hf, U, V, uvn[:, :2]) - uvn[:, 2]

    def cost(par, f):
        if np.linalg.norm(par[3:]) > SLACK:
            return 1e9
        g = gaps(par, f)
        cov = np.isfinite(g)
        if cov.sum() < 500:
            return 1e9
        gg = np.where(cov, g, np.nan)
        gen = cov & (tag == 0)
        zone = cov & (tag > 0)
        dev = np.maximum(0.0, GEN_LO - gg[gen]) + np.maximum(0.0, gg[gen] - GEN_HI)
        c_gen = float(np.sum(w[gen] * dev ** 2) / max(1e-9, w[gen].sum()))
        c_zone = (float(np.sum(w[zone] * (gg[zone] - ZONE_TARGET) ** 2)
                        / max(1e-9, w[zone].sum())) if zone.any() else 0.0)
        under = np.maximum(0.0, -gg[cov])
        c_int = float(np.sum(w[cov] * under ** 2) / max(1e-9, w[cov].sum()))
        c_cov = float(1.0 - w[cov].sum() / w.sum())
        return c_gen + 2.0 * c_zone + 6.0 * c_int + 30.0 * c_cov ** 2

    def pct(x, ww, q):
        o = np.argsort(x)
        cw = np.cumsum(ww[o]) / ww.sum()
        return float(x[o][np.searchsorted(cw, q / 100.0)])

    print("%6s %9s %9s %9s %9s %10s %10s %10s %9s"
          % ("keep", "lowering", "gap p25", "gap p50", "gap p75", "in 0.8-1.6",
             "LEFT ct", "RIGHT ct", "interf"))
    print("%6s %9s %9s %9s %9s %10s %10s %10s %9s"
          % ("f", "mm", "mm", "mm", "mm", "% of gen", "mm2", "mm2", "mm2"))
    rows = {}
    for f in FRACTIONS:
        best, bc = None, 1e18
        for s0 in (np.zeros(6),
                   np.array([0, 0, 0, 0.0, 0.0, 1.5]),
                   np.array([0, 0, 0, 0.0, -1.5, 0.0])):
            r = minimize(cost, s0, args=(f,), method="Nelder-Mead",
                         options={"xatol": 1e-4, "fatol": 1e-8,
                                  "maxiter": 3000, "maxfev": 4500})
            if r.fun < bc:
                bc, best = float(r.fun), np.asarray(r.x, float)
        g = gaps(best, f)
        cov = np.isfinite(g)
        gg, ww, tg = g[cov], w[cov], tag[cov]
        genm = tg == 0
        inband = ww[genm & (gg >= GEN_LO) & (gg <= GEN_HI)].sum()
        lz = ww[(tg == 1) & (gg >= -0.05) & (gg <= 0.30)].sum()
        rz = ww[(tg == 2) & (gg >= -0.05) & (gg <= 0.30)].sum()
        net = f * np.linalg.norm(L.THUMB_DELTA)
        rows[str(f)] = {"retainedFraction": f, "loweringKeptMm": net,
                        "params": list(best), "cost": bc,
                        "gapP25": pct(gg, ww, 25), "gapP50": pct(gg, ww, 50),
                        "gapP75": pct(gg, ww, 75), "gapMin": float(gg.min()),
                        "generalInBandPct": 100 * inband / max(1e-9, ww[genm].sum()),
                        "leftContactMm2": float(lz), "rightContactMm2": float(rz),
                        "interferingAreaMm2": float(ww[gg < 0].sum()),
                        "coveredFraction": float(ww.sum() / w.sum())}
        r_ = rows[str(f)]
        print("%6.2f %9.2f %9.3f %9.3f %9.3f %10.1f %10.2f %10.2f %9.2f"
              % (f, net, r_["gapP25"], r_["gapP50"], r_["gapP75"],
                 r_["generalInBandPct"], r_["leftContactMm2"], r_["rightContactMm2"],
                 r_["interferingAreaMm2"]))
        L.memory("f=%.2f" % f)

    print("\nreference - ORIGINAL Backplate against its OWN shell:")
    print("   gap p25/p50/p75 = 0.796 / 1.230 / 1.443 mm")
    print("   LEFT contact 71.69 mm2   RIGHT contact 23.38 mm2   interference ~0")
    L.write_json(OUT / "g02_tradeoff.json",
                 {"slackMm": SLACK, "generalBandMm": [GEN_LO, GEN_HI],
                  "zoneTargetMm": ZONE_TARGET, "sweep": rows,
                  "thumbDeltaMagnitudeMm": float(np.linalg.norm(L.THUMB_DELTA)),
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
