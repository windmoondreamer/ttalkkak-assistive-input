"""L01 - cavity survey and the smooth carrier surface fit (C09 §5, §6).

C09's carrier must "generally follow" the shell interior WITHOUT keying into it.
That distinction is the whole reason C08 failed its assembly gate: an exactly
conformal collar is a mechanical lock.

So the carrier surface here is a smooth POLYNOMIAL FIT of the shell interior,
not a carve of it.  A degree-2/3 surface tracks the gentle Thumb-panel curvature
while ignoring every local feature -- openings, bosses, rims -- which is exactly
what makes the finished part withdrawable.

Rays are cast outward from deep inside the cavity, so the first hit is the
interior surface.  Rays that escape through an opening are rejected, then the
fit is re-run with residual trimming so the surviving openings cannot drag it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from h01_seat_audit import axis_frame  # noqa: E402

OUT = L.LAB / "01_survey"
STEP_UV = 1.5
# The carrier only has to span the button field.  Sampling out to u = +-24 /
# v = +16 walks off the Thumb panel onto the grip flanks, where a ray along N
# hits a completely different surface -- that mixture is what produced a 14 mm
# rms "fit".  The eight seats live in u [-10.8, +10.8], v [-41.3, -18.2].
U_RANGE = (-16.0, 16.0)
V_RANGE = (-48.0, -12.0)
N_BAND = (-2.0, 20.0)     # plausible interior-surface band, in +NH terms
SEAT_T = 2.60


def poly_terms(u, v, deg):
    t = [np.ones_like(u)]
    for d in range(1, deg + 1):
        for i in range(d + 1):
            t.append((u ** (d - i)) * (v ** i))
    return np.stack(t, axis=1)


def fit_surface(u, v, n, deg=3, trim=2.0):
    A = poly_terms(u, v, deg)
    c, *_ = np.linalg.lstsq(A, n, rcond=None)
    for _ in range(4):
        r = n - A @ c
        keep = np.abs(r - np.median(r)) < trim * (np.percentile(np.abs(r), 75) + 1e-9)
        if keep.sum() < len(c) * 3:
            break
        c, *_ = np.linalg.lstsq(A[keep], n[keep], rcond=None)
    r = n - A @ c
    return c, r


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core_j = json.loads((L.REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    T = []
    for k in ("D101_JAD", "D101_JFD"):
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        T.append(L.triangles(s, tol=0.05, ang=0.10))
        del s
    T = np.concatenate(T)
    print("docs/101 shell: %d triangles" % len(T))
    L.memory("shell")

    # ---- 1 shell interior, sampled on a (u, v) grid ----------------------
    UH, VH, NH = L.DATUM_U, L.DATUM_V, -L.DATUM_N
    # Cast from OUTSIDE, inward.  The FIRST material interval is the outer
    # wall, so its far boundary IS the interior surface -- no guessing.
    # Casting outward from deep inside and taking the first hit instead threw
    # away 1217 of 1485 samples and left a degree-4 fit with 4.42 mm rms that
    # put T7's "interior" below its own seat.
    # Cast OUTWARD from inside the cavity, below the seats: the first hit is
    # the panel interior.  Keep only hits inside a plausible band, which drops
    # rays that escape through an opening and reach the far side.
    us, vs, ns, wall = [], [], [], []
    holes = 0
    START = -12.0
    for u in np.arange(U_RANGE[0], U_RANGE[1] + 1e-9, STEP_UV):
        for v in np.arange(V_RANGE[0], V_RANGE[1] + 1e-9, STEP_UV):
            o = L.DATUM_P + UH * u + VH * v + NH * START
            h = ray_intervals(T, o, NH, 0.0, 60.0)
            if not h:
                holes += 1
                continue
            n_in = START + float(h[0][0])
            n_out = START + float(h[0][1])
            if not (N_BAND[0] <= n_in <= N_BAND[1]):
                holes += 1
                continue
            us.append(u)
            vs.append(v)
            ns.append(n_in)
            wall.append(float(n_out - n_in))
    us, vs, ns, wall = (np.asarray(us), np.asarray(vs), np.asarray(ns),
                        np.asarray(wall))
    print("interior samples: %d kept, %d rejected as opening / not-a-wall"
          % (len(us), holes))
    print("  first material slab beyond the interior: p05 %.3f  p50 %.3f  p95 %.3f mm"
          % (np.percentile(wall, 5), np.percentile(wall, 50), np.percentile(wall, 95)))
    L.memory("sampled")

    best = None
    for deg in (2, 3):
        c, r = fit_surface(us, vs, ns, deg=deg)
        rms = float(np.sqrt((r ** 2).mean()))
        p95 = float(np.percentile(np.abs(r), 95))
        print("  degree %d fit: rms %.4f mm, p95 |residual| %.4f mm, %d terms"
              % (deg, rms, p95, len(c)))
        if best is None or rms < best[1] * 0.85:
            best = (deg, rms, c, p95)
    deg, rms, coef, p95 = best
    print("  -> using degree %d (rms %.4f mm)" % (deg, rms))

    def surf(u, v):
        return poly_terms(np.atleast_1d(u), np.atleast_1d(v), deg) @ coef

    # ---- 2 seat geometry, in the same local frame ------------------------
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    seats = {}
    print("")
    print("=== seats in the DATUM local frame ===")
    print("%-4s %9s %9s %9s %9s %9s"
          % ("btn", "u", "v", "seatTop n", "seatBot n", "shellFit n"))
    for s in names:
        top = np.asarray(core_j["seats"][s]["plateTopWorld"], float)
        w = np.asarray(core_j["seats"][s]["axisWorld"], float)
        d = top - L.DATUM_P
        u, v, n = float(d @ UH), float(d @ VH), float(d @ NH)
        bot = n - SEAT_T
        fit_n = float(surf(u, v)[0])
        seats[s] = {"uMm": u, "vMm": v, "seatTopN": n, "seatBotN": bot,
                    "shellFitN": fit_n, "axisWorld": w.tolist(),
                    "plateTopWorld": top.tolist()}
        print("%-4s %9.3f %9.3f %9.3f %9.3f %9.3f" % (s, u, v, n, bot, fit_n))
    L.memory("seats")

    # ---- 3 where can the carrier sit? ------------------------------------
    lo_seat = min(seats[s]["seatBotN"] for s in names)
    print("")
    print("=== carrier placement ===")
    print("  lowest seat bottom      n = %+8.3f" % lo_seat)
    print("  shell fit under seats   n = %+8.3f .. %+8.3f"
          % (min(seats[s]["shellFitN"] for s in names),
             max(seats[s]["shellFitN"] for s in names)))
    depths = {}
    # The sketches put the carrier CLOSE to the shell (the "1 mm" annotation)
    # with the seat blocks hanging inward from it, so the shallow offsets are
    # the ones that matter; the deep ones are kept for contrast.
    for D in (1.0, 1.5, 2.0, 2.5, 3.0, 6.0, 8.0, 10.0):
        top_at_seats = np.array([seats[s]["shellFitN"] - D for s in names])
        posts = np.array([seats[s]["seatBotN"] - t for s, t in zip(names, top_at_seats)])
        depths[D] = {"carrierTopRangeN": [float(top_at_seats.min()),
                                          float(top_at_seats.max())],
                     "postHeightsMm": {s: float(p) for s, p in zip(names, posts)},
                     "minPostMm": float(posts.min()), "maxPostMm": float(posts.max())}
        sign = "blocks hang INWARD" if posts.max() < 0 else (
            "posts rise OUTWARD" if posts.min() > 0 else "mixed")
        print("  offset %.1f mm below the fitted interior -> seat offset %+.2f .. %+.2f mm  (%s)"
              % (D, posts.min(), posts.max(), sign))

    # ---- 4 how much room is there under the carrier? ---------------------
    print("")
    print("=== free depth below the fitted surface, on a coarse grid ===")
    free = []
    for u in np.arange(-20.0, 20.01, 4.0):
        for v in np.arange(-46.0, 12.01, 4.0):
            f0 = float(surf(u, v)[0])
            o = L.DATUM_P + UH * u + VH * v + NH * f0
            h = ray_intervals(T, o - NH * 0.5, -NH, 0.0, 60.0)
            d = float(min([a for a, _ in (h or [])], default=60.0))
            free.append(d)
    free = np.asarray(free)
    print("  free depth inward from the fitted surface: p05 %.2f  p50 %.2f  min %.2f mm"
          % (np.percentile(free, 5), np.percentile(free, 50), free.min()))

    # ---- 5 gate case selection -------------------------------------------
    jw = L.unit(np.asarray(joyj["joyAxisWorld"], float))
    jc = np.asarray(joyj["knobCentreWorld"], float)
    survey = json.loads((L.REV_K / "01_site_survey" / "k01_site_survey.json")
                        .read_text(encoding="utf-8")) if (
        L.REV_K / "01_site_survey" / "k01_site_survey.json").exists() else None
    print("")
    print("=== gate case selection ===")
    print("%-4s %10s %10s %10s %10s  %s"
          % ("btn", "post", "nearSZH", "nearT", "tiltToN", "note"))
    score = {}
    for s in names:
        D0 = 1.0
        post = depths[D0]["postHeightsMm"][s]
        w = np.asarray(seats[s]["axisWorld"], float)
        tilt = float(np.degrees(np.arccos(abs(float(w @ NH)))))
        nsz = survey["buttons"][s]["nearestSzhStaticMm"] if survey else float("nan")
        nt = survey["buttons"][s]["nearestThumbMm"] if survey else float("nan")
        # a hard case = short post (little room to build a support) plus a
        # tight neighbourhood plus a large tilt off the carrier normal
        score[s] = min(nsz, nt) - 2.0 * tilt + post
        print("%-4s %10.3f %10.3f %10.3f %10.3f  score %.2f"
              % (s, post, nsz, nt, tilt, score[s]))
    easy = max(names, key=lambda s: score[s])
    hard = min(names, key=lambda s: score[s])
    mid = sorted(names, key=lambda s: score[s])[len(names) // 2]
    print("  CASE EASY = %s   CASE MID = %s   CASE HARD = %s" % (easy, mid, hard))

    L.write_json(OUT / "l01_survey.json",
                 {"gridStepMm": STEP_UV, "uRange": list(U_RANGE), "vRange": list(V_RANGE),
                  "interiorSamples": int(len(us)), "rejected": holes,
                  "panelWallMm": {"p05": float(np.percentile(wall, 5)),
                                  "p50": float(np.percentile(wall, 50)),
                                  "p95": float(np.percentile(wall, 95))},
                  "fitDegree": deg, "fitRmsMm": rms, "fitP95Mm": p95,
                  "fitCoefficients": coef.tolist(),
                  "seats": seats, "lowestSeatBottomN": lo_seat,
                  "depthOptions": depths,
                  "freeDepthBelowFit": {"p05": float(np.percentile(free, 5)),
                                        "p50": float(np.percentile(free, 50)),
                                        "min": float(free.min())},
                  "caseEasy": easy, "caseMid": mid, "caseHard": hard,
                  "caseScore": score, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
