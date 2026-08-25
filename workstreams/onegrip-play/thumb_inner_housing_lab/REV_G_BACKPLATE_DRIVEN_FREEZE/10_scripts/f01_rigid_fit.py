"""F01 - can ONE rigid pose of the ORIGINAL Backplate fit the current geometry?

REV_F sections 1 and 2.  No geometry is cut here; this is the gate.

Two things must hold simultaneously:
  (a) the plate keeps its functional registration to the nine FROZEN controls
  (b) the plate sits at roughly 1.0 mm inside the exact approved shell

Baseline fact, already established and re-checked here: the whole Thumb
cartridge was moved as ONE rigid body by THUMB_DELTA, so the control-aligned
pose is exactly THUMB_DELTA with zero registration residual.  REV_D measured
that pose at gap p50 = +8.948 mm.  So the question is whether some OTHER rigid
pose can hold registration and still reach ~1 mm.

Method
  * sample the plate's outer face once, in its own frame
  * build the approved shell's inner-surface height field n_shell(u, v) once
  * optimise a 6-DOF rigid perturbation about THUMB_DELTA to drive the gap to
    1.0 mm, then report what that pose costs in control registration
  * registration is measured on each control's own TRUE axis:
      lateral   distance from the control axis to the plate seat point
      angular   angle between the control axis and the plate seating normal
      axial     offset along the control axis (absorbed by the switch stack,
                which is still an open choice in CLAUDE.md section 3)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, true_axis  # noqa: E402
from d02_housing_vs_exact import BP_STEP, Field, approved_shell  # noqa: E402

OUT = L.LAB / "01_rigidfit"
OUTWARD = -L.DATUM_N
ORIG_P = L.DATUM_P - L.THUMB_DELTA
TARGET_GAP = 1.00
PITCH = 0.25


def rot(a):
    """Small-angle rotation matrix from a 3-vector of angles (rad)."""
    ax, ay, az = a
    Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    Rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def shell_height_field(shell, U, V):
    """n of the Thumb wall's INNER surface per (u, v) column, else NaN."""
    f = Field(L.local_triangles(shell, tol=0.06, ang=0.12))
    h = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            hits = f.hits(u, v)
            if hits.size == 0 or hits.size % 2:
                continue
            slabs = [(hits[k], hits[k + 1]) for k in range(0, hits.size, 2)]
            out = [s for s in slabs if s[1] > 0.0]
            if out:
                h[i, j] = min(s[0] for s in out)
    return h


def sample_field(h, U, V, uv):
    i = np.round((uv[:, 0] - U[0]) / (U[1] - U[0])).astype(int)
    j = np.round((uv[:, 1] - V[0]) / (V[1] - V[0])).astype(int)
    ok = (i >= 0) & (i < len(U)) & (j >= 0) & (j < len(V))
    out = np.full(len(uv), np.nan)
    out[ok] = h[i[ok], j[ok]]
    return out


def main() -> int:
    approved = approved_shell()
    bp = import_step(str(BP_STEP))
    bp, _ = L.as_single_solid(bp, "BACKPLATE")
    print("ORIGINAL Backplate: vol=%.4f mm3  faces=%d" % (L.vol(bp), len(list(bp.faces()))))
    L.memory("loaded")

    # plate outer-face sample points, in world coords at the ORIGINAL pose
    pts = L.surf_points(bp, 120000, tol=0.06)
    T = L.triangles(bp, tol=0.06, ang=0.12)
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(nrm, axis=1)
    ok = ln > 1e-12
    nrm[ok] /= ln[ok][:, None]
    # outer face = triangles whose normal points outward (+n in the original frame)
    outer = nrm @ OUTWARD > 0.55
    Touter = T[outer]
    # Area-weighted samples, NOT triangle vertices.  Vertices cluster at corners
    # and leave large planar faces almost unsampled - the first run had only 540
    # points for the whole outer face.
    a3, b3, c3 = Touter[:, 0], Touter[:, 1], Touter[:, 2]
    area = 0.5 * np.linalg.norm(np.cross(b3 - a3, c3 - a3), axis=1)
    tot = float(area.sum())
    rng = np.random.default_rng(20260825)
    counts = np.maximum(1, np.round(area / tot * 20000).astype(int))
    ii = np.repeat(np.arange(len(Touter)), counts)
    r1_ = rng.random(len(ii))
    r2_ = rng.random(len(ii))
    sq = np.sqrt(r1_)
    outer_pts = ((1 - sq)[:, None] * a3[ii] + (sq * (1 - r2_))[:, None] * b3[ii]
                 + (sq * r2_)[:, None] * c3[ii])
    print("outer face area %.2f mm2" % tot)
    seat_n = L.unit((nrm[~outer] * 0).sum(axis=0) if False else
                    (nrm[nrm @ OUTWARD < -0.55]).mean(axis=0))
    print("outer-face samples %d   plate seating normal (inboard) = %s"
          % (len(outer_pts), np.round(seat_n, 6)))

    U = np.arange(-24.0, 24.0 + 1e-9, PITCH)
    V = np.arange(-52.0, 16.0 + 1e-9, PITCH)
    hfield = shell_height_field(approved, U, V)
    print("shell inner-surface field: %d of %d columns defined"
          % (int(np.isfinite(hfield).sum()), hfield.size))
    L.memory("height field")

    centre = outer_pts.mean(axis=0)

    def place(par):
        R = rot(par[:3])
        t = np.asarray(par[3:], float)
        p = (outer_pts - centre) @ R.T + centre + L.THUMB_DELTA + t
        d = p - L.DATUM_P
        return np.stack([d @ L.DATUM_U, d @ L.DATUM_V, d @ OUTWARD], axis=1)

    def cost(par):
        uvn = place(par)
        hs = sample_field(hfield, U, V, uvn[:, :2])
        g = hs - uvn[:, 2]
        m = np.isfinite(g)
        if m.sum() < 200:
            return 1e6
        return float(np.mean((g[m] - TARGET_GAP) ** 2))

    def report(par, tag):
        uvn = place(par)
        hs = sample_field(hfield, U, V, uvn[:, :2])
        g = hs - uvn[:, 2]
        m = np.isfinite(g)
        gg = g[m]
        row = {"params": list(np.asarray(par, float)),
               "coveredSamples": int(m.sum()), "totalSamples": int(len(g)),
               "gapPercentilesMm": {str(q): float(np.percentile(gg, q))
                                    for q in (5, 25, 50, 75, 95)},
               "gapMinMm": float(gg.min()), "gapMaxMm": float(gg.max()),
               "rmsFromTargetMm": float(np.sqrt(np.mean((gg - TARGET_GAP) ** 2))),
               "fractionInterfering": float((gg < 0).mean())}
        print("\n%s" % tag)
        print("  covered samples %d / %d" % (m.sum(), len(g)))
        print("  gap p05/p25/p50/p75/p95 = %+.3f / %+.3f / %+.3f / %+.3f / %+.3f mm"
              % tuple(row["gapPercentilesMm"][k] for k in ("5", "25", "50", "75", "95")))
        print("  gap min/max = %+.3f / %+.3f   rms from %.2f mm = %.3f   interfering %.1f %%"
              % (row["gapMinMm"], row["gapMaxMm"], TARGET_GAP, row["rmsFromTargetMm"],
                 100 * row["fractionInterfering"]))
        return row

    res = {}
    res["POSE_A_CONTROL_ALIGNED"] = report(np.zeros(6),
                                           "POSE A - pure THUMB_DELTA (control-aligned, zero residual)")

    # translation only, along the plate's own seating normal
    def cost_1d(x):
        return cost(np.concatenate([np.zeros(3), -seat_n * float(x[0])]))
    r1 = minimize(cost_1d, [7.0], method="Nelder-Mead",
                  options={"xatol": 1e-3, "fatol": 1e-6, "maxiter": 200})
    d1 = float(r1.x[0])
    par_b = np.concatenate([np.zeros(3), -seat_n * d1])
    res["POSE_B_TRANSLATION_ONLY"] = report(par_b,
                                            "POSE B - translated %.3f mm along the seating normal" % d1)
    res["POSE_B_TRANSLATION_ONLY"]["translationAlongSeatNormalMm"] = d1
    L.memory("pose B")

    # POSE D: get as close to TARGET as possible WITHOUT interfering.
    # One-sided penalty on gaps below TARGET, light penalty on drifting above.
    def cost_noint(par):
        uvn = place(par)
        hs = sample_field(hfield, U, V, uvn[:, :2])
        g = hs - uvn[:, 2]
        m = np.isfinite(g)
        if m.sum() < 200:
            return 1e6
        gg = g[m]
        under = np.maximum(0.0, TARGET_GAP - gg)
        return float(np.mean(under ** 2) * 40.0 + np.mean(np.maximum(0.0, gg - TARGET_GAP) ** 2))

    r3 = minimize(cost_noint, np.zeros(6), method="Nelder-Mead",
                  options={"xatol": 1e-4, "fatol": 1e-7, "maxiter": 4000, "maxfev": 6000})
    par_d = np.asarray(r3.x, float)
    res["POSE_D_NO_INTERFERENCE"] = report(par_d,
                                           "POSE D - closest pose that avoids driving the plate into the shell")
    res["POSE_D_NO_INTERFERENCE"]["rotationDeg"] = list(np.degrees(par_d[:3]))
    res["POSE_D_NO_INTERFERENCE"]["translationMm"] = list(par_d[3:])
    print("  rotation %s deg   translation %s mm"
          % (np.round(np.degrees(par_d[:3]), 4), np.round(par_d[3:], 4)))
    L.memory("pose D")

    # full 6-DOF
    r2 = minimize(cost, par_b, method="Nelder-Mead",
                  options={"xatol": 1e-4, "fatol": 1e-7, "maxiter": 4000, "maxfev": 6000})
    par_c = np.asarray(r2.x, float)
    res["POSE_C_FULL_6DOF"] = report(par_c, "POSE C - full 6-DOF rigid fit")
    res["POSE_C_FULL_6DOF"]["rotationDeg"] = list(np.degrees(par_c[:3]))
    res["POSE_C_FULL_6DOF"]["translationMm"] = list(par_c[3:])
    print("  rotation %s deg   extra translation %s mm"
          % (np.round(np.degrees(par_c[:3]), 4), np.round(par_c[3:], 4)))
    L.memory("pose C")

    # ---- what does each pose cost in control registration? --------------
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    axes, cens = {}, {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, _ = true_axis(cap)
        axes[short] = w
        cens[short] = L.surf_points(cap, 30000, tol=0.06).mean(axis=0)
        del cap

    print("\n=== control registration cost of each pose ===")
    print("%-22s %12s %12s %12s" % ("pose", "max lateral", "max angular", "axial shift"))
    reg = {}
    for tag, par in (("POSE_A_CONTROL_ALIGNED", np.zeros(6)),
                     ("POSE_B_TRANSLATION_ONLY", par_b),
                     ("POSE_D_NO_INTERFERENCE", par_d),
                     ("POSE_C_FULL_6DOF", par_c)):
        R = rot(np.asarray(par)[:3])
        t = np.asarray(par)[3:]
        seat_now = R @ seat_n
        rows = {}
        for short in ORDER:
            w = axes[short]
            c = cens[short]
            # the seat point under this control: the control centre displaced by
            # the rigid motion, expressed relative to the unmoved control axis
            p0 = c                                   # pose A puts the seat here
            p1 = (c - (centre + L.THUMB_DELTA)) @ R.T + (centre + L.THUMB_DELTA) + t
            dv = p1 - p0
            axial = float(dv @ w)
            lateral = float(np.linalg.norm(dv - w * axial))
            ang = float(np.degrees(np.arccos(np.clip(
                abs(float(seat_now @ w)) / (np.linalg.norm(seat_now)), -1, 1))))
            ang0 = float(np.degrees(np.arccos(np.clip(abs(float(seat_n @ w)), -1, 1))))
            rows[short] = {"lateralErrorMm": lateral, "axialShiftMm": axial,
                           "seatAxisAngleDeg": ang, "baselineSeatAxisAngleDeg": ang0,
                           "angleChangeDeg": ang - ang0}
        reg[tag] = rows
        print("%-22s %12.4f %12.4f %12.4f"
              % (tag, max(r["lateralErrorMm"] for r in rows.values()),
                 max(abs(r["angleChangeDeg"]) for r in rows.values()),
                 max(abs(r["axialShiftMm"]) for r in rows.values())))

    print("\nper-control detail, POSE C:")
    print("%-5s %12s %12s %14s %14s" % ("ctrl", "lateral mm", "axial mm",
                                        "seat-axis deg", "change deg"))
    for short in ORDER:
        r = reg["POSE_C_FULL_6DOF"][short]
        print("%-5s %12.4f %12.4f %14.4f %14.4f"
              % (short, r["lateralErrorMm"], r["axialShiftMm"],
                 r["seatAxisAngleDeg"], r["angleChangeDeg"]))

    L.write_json(OUT / "f01_rigid_fit.json",
                 {"targetGapMm": TARGET_GAP,
                  "plateSeatingNormalOriginalFrame": seat_n.tolist(),
                  "poses": res, "registration": reg, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
