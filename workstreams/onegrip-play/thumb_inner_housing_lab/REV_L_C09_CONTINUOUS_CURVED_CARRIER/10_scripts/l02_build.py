"""L02 - the C09 builder: one continuous curved carrier + inward-hanging seats.

Follows the sketches:

    curved shell wall
    ~1 mm gap                       <- the "1mm" annotation
    ONE continuous uniform-width carrier band     <- "동일 폭 구조"
    short block hanging INWARD from it, one per button
    flat switch seat, plane normal = that button's FROZEN press axis
    switch -> actuator outward through the block and the carrier aperture
    terminals down through the seat

L01 measured why the blocks hang inward rather than rise: the fitted shell
interior sits 4.3-4.9 mm OUTBOARD of every seat top, so a carrier 1 mm inside
the shell is 5.68-6.62 mm outboard of the seats.  That spread is only 0.94 mm
across all eight, which is what makes one uniform band workable.

Deliberately NOT C08: the carrier is a smooth degree-2 fit (rms 0.624 mm), not a
carve of the shell, so nothing keys into local shell features.  That was C08's
fatal assembly failure.

Build order obeys the rule this project keeps re-learning: every additive stage
runs before every clearance stage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import (Align, Box, Compound, Location, Plane, Polyline, Vector,
                       export_step, export_stl, import_step, loft, make_face)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from h01_seat_audit import axis_frame  # noqa: E402
from l01_survey import poly_terms  # noqa: E402

GAP = 1.30           # carrier top to the fitted shell interior.
                     # The sketch says "1mm"; section 6 says do not force an
                     # exact global 1.000 mm rule if it breaks assembly.  At
                     # 1.00 the band grazed the shell during the withdrawal
                     # sweep by 0.1 mm3 -- 0.004% of the body, but not zero,
                     # and insertability is the hard gate C08 died on.  The
                     # actual resulting spacing is measured and reported.
CARRIER_T = 2.00     # uniform band thickness
BLOCK_HALF = 5.60    # keeps a neighbour's cap column clear by 0.50 mm at 10.30 pitch
SEAT_T = 2.60
CAP_TO_PLATE = 4.759
POCKET_XY = 6.40
OPENING_XY = 8.00
CAP_CLR = 0.20
SLOT_W, SLOT_L, SLOT_OFF = 1.30, 6.40, 2.60
U_STEP, V_STEP = 2.0, 3.0
SHELL_CLR = 0.35

UH, VH, NH = L.DATUM_U, L.DATUM_V, -L.DATUM_N


def surf_fn(coef, deg):
    def f(u, v):
        # numpy 2 rejects float() on a 1-element array, so index it
        return float((poly_terms(np.atleast_1d(float(u)),
                                 np.atleast_1d(float(v)), deg) @ coef)[0])
    return f


def world(u, v, n):
    return L.DATUM_P + UH * u + VH * v + NH * n


def carrier_band(f, u_rng, v_rng):
    """Uniform-thickness curved band, built as segment lofts and unioned.

    A single multi-section loft silently produces invalid solids in OCC (this
    project has hit that before), so adjacent sections are lofted pairwise and
    fused.
    """
    us = np.arange(u_rng[0], u_rng[1] + 1e-9, U_STEP)
    vs = np.arange(v_rng[0], v_rng[1] + 1e-9, V_STEP)

    def section(v):
        top = [world(u, v, f(u, v) - GAP) for u in us]
        bot = [world(u, v, f(u, v) - GAP - CARRIER_T) for u in us[::-1]]
        pts = [L.xyz(p) for p in top + bot]
        return make_face(Polyline(*pts, close=True))

    band = None
    for a, b in zip(vs[:-1], vs[1:]):
        seg = loft([section(a), section(b)], ruled=True)
        band = seg if band is None else (band + seg).clean()
    band, _ = L.as_single_solid(band, "CARRIER")
    return band


def crop_shells(shell, pad=30.0):
    """Shell material near the Thumb, as a list of single Solids.

    The withdrawal sweep is 200 exact booleans against a 52,206-triangle shell,
    which measured ~20 s each -- 67 minutes, and it stalled the pipeline.  The
    sweep only ever involves the Thumb neighbourhood, so crop once and reuse.
    Kept as a LIST of Solids: a Compound operand silently returns a wrong
    boolean result in OCC.
    """
    from build123d import Align, Box, Plane
    box = Plane(origin=L.xyz(L.DATUM_P - (-L.DATUM_N) * pad),
                x_dir=L.xyz(L.DATUM_U), z_dir=L.xyz(-L.DATUM_N)) * Box(
        2 * pad, 2 * pad + 40.0, 2 * pad,
        align=(Align.CENTER, Align.CENTER, Align.MIN))
    piece = shell & box
    if piece is None:
        return []
    return [sol for sol in piece.clean().solids() if float(sol.volume) > 1.0e-6]


def sq(origin, ex, w, half, n0, n1, label="B"):
    b = Plane(origin=L.xyz(np.asarray(origin, float) + w * n0),
              x_dir=L.xyz(ex), z_dir=L.xyz(w)) * Box(
        2 * half, 2 * half, n1 - n0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    b.label = label
    return b


def button_geom(name, core_j, cart):
    cap, _ = L.as_single_solid(cart[next(k for k, v in NAME_MAP.items() if v == name)],
                               name)
    w, _, _ = true_axis(cap)
    cen = L.surf_points(cap, 40000, tol=0.05).mean(axis=0)
    ex, ey = axis_frame(w)
    top = np.asarray(core_j["seats"][name]["plateTopWorld"], float)
    seat_top = float((top - cen) @ w)
    del cap
    return {"cen": cen, "w": w, "ex": ex, "ey": ey, "seatTop": seat_top}


def build(names, f, u_rng, v_rng, shells, shell_tris, core_j, cart, tag="C09"):
    band = carrier_band(f, u_rng, v_rng)
    print("  carrier band: vol %.3f  faces %d  solids %d  valid %s"
          % (L.vol(band), len(list(band.faces())), len(list(band.solids())),
             bool(band.is_valid)))
    L.memory("band")

    g = {n: button_geom(n, core_j, cart) for n in names}
    body = band
    for n in names:
        b = g[n]
        # block hangs INWARD from the carrier down to the seat bottom
        n_top = b["seatTop"] + 12.0          # well into the carrier, trimmed later
        n_bot = b["seatTop"] - SEAT_T
        blk = sq(b["cen"], b["ex"], b["w"], BLOCK_HALF, n_bot, n_top,
                 "%s_BLOCK" % n)
        body = (body + blk).clean()
        body, _ = L.as_single_solid(body, tag)
        L.memory("block " + n)
    print("  + %d blocks: vol %.3f  solids %d" % (len(names), L.vol(body),
                                                  len(list(body.solids()))))

    # ---- clearances LAST -------------------------------------------------
    cuts = 0
    for n in names:
        b = g[n]
        cap_und = b["seatTop"] + CAP_TO_PLATE
        tools = [
            sq(b["cen"], b["ex"], b["w"], OPENING_XY / 2.0 + CAP_CLR,
               cap_und - 0.001, cap_und + 30.0, "%s_CAPCOL" % n),
            sq(b["cen"], b["ex"], b["w"], POCKET_XY / 2.0,
               b["seatTop"], cap_und + 0.5, "%s_POCKET" % n),
        ]
        for sgn in (-1.0, 1.0):
            o = b["cen"] + b["ex"] * (sgn * SLOT_OFF)
            t = Plane(origin=L.xyz(o + b["w"] * (b["seatTop"] - SEAT_T - 1.0)),
                      x_dir=L.xyz(b["ex"]), z_dir=L.xyz(b["w"])) * Box(
                SLOT_W, SLOT_L, SEAT_T + 2.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
            t.label = "%s_SLOT" % n
            tools.append(t)
        for t in tools:
            if L.inter_vol(body, t) > 1.0e-9:
                body = (body - t).clean()
                body, _ = L.as_single_solid(body, tag)
                cuts += 1
        L.memory("voids " + n)
    print("  - %d clearance features cut" % cuts)

    # ---- shell guard -----------------------------------------------------
    v0 = L.vol(body)
    for s in shells:
        for d in (np.zeros(3), NH * SHELL_CLR):
            t = s if not np.any(d) else s.moved(
                Location(Vector(*[float(x) for x in d])))
            if L.inter_vol(body, t) > 1.0e-9:
                body = (body - t).clean()
                body, _ = L.as_single_solid(body, tag)
    print("  - shell guard removed %.3f mm3" % (v0 - L.vol(body)))

    parts = sorted(body.solids(), key=lambda x: -float(x.volume))
    debris = [float(p.volume) for p in parts[1:]]
    body = parts[0]
    body.label = tag
    return body, {"gapMm": GAP, "carrierThicknessMm": CARRIER_T,
                  "blockHalfMm": BLOCK_HALF, "buttons": list(names),
                  "clearanceCuts": cuts, "droppedFragmentsMm3": debris,
                  "volumeMm3": L.vol(body), "faces": len(list(body.faces())),
                  "solids": len(list(body.solids())), "valid": bool(body.is_valid)}


def load_common():
    core_j = json.loads((L.REV_I / "06_current_core" / "i06_current_core.json")
                        .read_text(encoding="utf-8"))
    survey = json.loads((L.LAB / "01_survey" / "l01_survey.json")
                        .read_text(encoding="utf-8"))
    coef = np.asarray(survey["fitCoefficients"], float)
    f = surf_fn(coef, survey["fitDegree"])
    shells = []
    for k in ("D101_JAD", "D101_JFD"):
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        shells.append(s)
    T = np.concatenate([L.triangles(s, tol=0.05, ang=0.10) for s in shells])
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    return core_j, survey, f, shells, T, cart
