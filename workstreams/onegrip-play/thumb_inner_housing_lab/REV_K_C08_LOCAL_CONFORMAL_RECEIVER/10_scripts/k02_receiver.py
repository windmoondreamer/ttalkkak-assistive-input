"""K02 - the C08 local conformal switch receiver, and the two-button gate.

One receiver is ONE tapered square collar minus the shell.  That single
subtraction produces all three C08 layers at once:

    top face      = the exact shell inner surface, so the landing is conformal
                    by construction, not approximated by a flat pad
    side walls    = a ruled square frustum about the FROZEN press axis, so every
                    wall is a straight self-supporting taper
    bottom        = a flat plate whose normal IS the frozen press axis

Then three voids are removed: the cap column (the frozen 8.00 mm opening), the
switch pocket (6.40 mm, the original clearance law) and the two original
1.30 x 6.40 mm terminal slots at +-2.60 mm.

K01 measured the whole transition at 3.886-4.747 mm, so this is a short local
load path rather than a remote carrier.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import (Align, Box, Compound, Location, Plane, Solid, Vector,
                       export_step, export_stl, import_step)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from h01_seat_audit import axis_frame  # noqa: E402

OUT = L.LAB / "02_gate"

CAP_TO_PLATE = 4.759     # REV_H/REV_I law, preserved
SEAT_T = 2.60            # flat seat plate thickness
WALL = 2.15              # -> collar half-size 5.35 with FLARE 0.  Chosen from the
                         # 10.30 mm neighbour spacing, not picked: at 5.35 the
                         # collars overlap 0.40 mm so they FUSE (no tangent
                         # union, no rib needed), while a neighbour collar still
                         # clears this button's cap column by 0.75 mm, its
                         # pocket by 1.75 mm and its slot edge by 1.70 mm.
                         # The earlier 6.60 landing broke exactly those three.
POCKET_XY = 6.40         # switch body + 0.2 mm per side, the original law
OPENING_XY = 8.00        # frozen external opening
CAP_CLR = 0.20
SLOT_W, SLOT_L, SLOT_OFF = 1.30, 6.40, 2.60
LAND_CLR = 0.10          # gap to the shell so the part can be assembled
FLARE = 0.00             # Adjacent Thumb centres are 10.30 mm apart, so any
                         # half-size above 5.15 makes neighbouring receivers
                         # overlap.  They then either fill each other's pockets
                         # (12 of 16 slots blocked) or, if each one's voids are
                         # cross-cut into its neighbours, one button's cap
                         # column saws through the next button's seat plate
                         # (T1-T4 destroyed).  At 0.00 the collar is a straight
                         # self-supporting prism and every receiver is
                         # independent, which is what section 16 wants anyway.
TOP_OVERSHOOT = 3.0      # push the blank into the shell so the cut is clean


def sq(origin, ex, ey, w, half, n0, n1, label="B"):
    b = Plane(origin=L.xyz(np.asarray(origin, float) + w * n0),
              x_dir=L.xyz(ex), z_dir=L.xyz(w)) * Box(
        2 * half, 2 * half, n1 - n0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    b.label = label
    return b


def frustum(origin, ex, ey, w, h0, h1, n0, n1, label="F"):
    """Square frustum about w: half-size h0 at n0, growing to h1 at n1."""
    from build123d import Polyline, loft, make_face

    def face(h, n):
        p = [L.xyz(np.asarray(origin, float) + w * n + ex * (sx * h) + ey * (sy * h))
             for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        return make_face(Polyline(*p, close=True))

    s = loft([face(h0, n0), face(h1, n1)], ruled=True)
    s.label = label
    return s


def receiver_voids(name, cen, w, ex, ey, seat_top, top_n):
    """Cap column, switch pocket and the two terminal slots for one receiver."""
    seat_bot = seat_top - SEAT_T
    cap_und = seat_top + CAP_TO_PLATE
    v = [sq(cen, ex, ey, w, OPENING_XY / 2.0 + CAP_CLR, cap_und - 0.001,
            top_n + 2.0, name + "_CAPCOL"),
         sq(cen, ex, ey, w, POCKET_XY / 2.0, seat_top, cap_und + 0.5, name + "_POCKET")]
    for sgn in (-1.0, 1.0):
        o = cen + ex * (sgn * SLOT_OFF)
        b = Plane(origin=L.xyz(o + w * (seat_bot - 1.0)), x_dir=L.xyz(ex),
                  z_dir=L.xyz(w)) * Box(SLOT_W, SLOT_L, SEAT_T + 2.0,
                                        align=(Align.CENTER, Align.CENTER, Align.MIN))
        b.label = name + "_SLOT"
        v.append(b)
    return v


def build_receiver(name, cen, w, ex, ey, seat_top, shell_solids, shell_tris,
                   land_w=None, cut_voids=True):
    """One C08 receiver.  Returns (solid, record)."""
    a_seat = POCKET_XY / 2.0 + WALL                      # 5.00
    a_land = a_seat + (FLARE if land_w is None else land_w)
    seat_bot = seat_top - SEAT_T
    cap_und = seat_top + CAP_TO_PLATE

    # how far above the seat does the shell inner surface sit here?
    inner = []
    for r in (a_seat, a_land):
        for t in np.arange(0.0, 2 * np.pi - 1e-9, np.pi / 12.0):
            o = cen + ex * (r * np.cos(t)) + ey * (r * np.sin(t)) + w * (seat_bot - 12.0)
            h = ray_intervals(shell_tris, o, w, 0.0, 40.0)
            if h:
                inner.append(seat_bot - 12.0 + float(h[0][0]))
    inner_med = float(np.median(inner)) if inner else seat_top + 4.0

    blank = frustum(cen, ex, ey, w, a_seat, a_land, seat_bot,
                    inner_med + TOP_OVERSHOOT, name + "_BLANK")

    # Crop the shell to this button before subtracting.  Subtracting the whole
    # 52k-triangle shell seven times per receiver is minutes of boolean work for
    # a result that only depends on the material within ~15 mm of the axis.
    crop = sq(cen, ex, ey, w, a_land + 6.0, seat_bot - 8.0,
              inner_med + TOP_OVERSHOOT + 8.0, name + "_CROP")
    # Keep the crop as a LIST of single Solids and subtract them one at a time.
    # Unioning them first made `local` a Compound, and a Compound used as a
    # boolean operand silently returns a wrong result in OCC -- the EASY case
    # came out as a 3-face, zero-volume shard while HARD built correctly.
    local = []
    for s in shell_solids:
        # OCC returns None, not an empty shape, when the two do not meet at all.
        # T7's crop misses one half entirely.
        piece = s & crop
        if piece is None:
            continue
        piece = piece.clean()
        for sol in piece.solids():
            if float(sol.volume) > 1.0e-6:
                local.append(sol)
    # Clearance along the PRESS AXIS only.  An isotropic +-0.10 mm cut in six
    # global directions destroyed the T2 blank outright (1399 mm3 -> 0) while
    # T8 survived; it is also seven booleans per shell piece instead of two.
    # The receiver is pressed against the shell along w, so that is the
    # direction the gap belongs in.
    body = blank
    for sol in local:
        for d in (np.zeros(3), w * LAND_CLR):
            t = sol if not np.any(d) else sol.moved(
                Location(Vector(*[float(x) for x in d])))
            if L.inter_vol(body, t) > 1.0e-9:
                body = (body - t).clean()
                body, _ = L.as_single_solid(body, name)
    body, _ = L.as_single_solid(body, name)
    if L.vol(body) < 1.0:
        raise RuntimeError("%s: receiver collapsed to %.4f mm3 after the shell cut"
                           % (name, L.vol(body)))

    voids = receiver_voids(name, cen, w, ex, ey, seat_top,
                           inner_med + TOP_OVERSHOOT) if cut_voids else []
    slots = 0
    for v in voids:
        if L.inter_vol(body, v) > 1.0e-9:
            body = (body - v).clean()
            body, _ = L.as_single_solid(body, name)
            if "SLOT" in str(v.label):
                slots += 1

    parts = sorted(body.solids(), key=lambda x: -float(x.volume))
    debris = [float(x.volume) for x in parts[1:]]
    body = parts[0]
    body.label = name
    rec = {"topNOnAxis": inner_med + TOP_OVERSHOOT, "shellCropSolids": len(local), "seatTopOnAxis": seat_top, "seatBottomOnAxis": seat_bot,
           "capUndersideOnAxis": cap_und, "shellInnerMedianOnAxis": inner_med,
           "transitionLengthMm": inner_med - seat_top,
           "seatHalfSizeMm": a_seat, "landingHalfSizeMm": a_land,
           "landingWidthMm": a_land - POCKET_XY / 2.0,
           "wallMm": WALL, "slotsCut": slots,
           "volumeMm3": L.vol(body), "faces": len(list(body.faces())),
           "solids": len(list(body.solids())), "valid": bool(body.is_valid),
           "droppedFragmentsMm3": debris}
    return body, rec


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    site = json.loads((L.LAB / "01_site_survey" / "k01_site_survey.json").read_text(encoding="utf-8"))
    core_j = json.loads((L.REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    easy, hard = site["caseEasy"], site["caseHard"]
    print("CASE EASY = %s   CASE HARD = %s" % (easy, hard))

    shells = []
    for key in ("D101_JAD", "D101_JFD"):
        s, _ = L.as_single_solid(import_step(L.SRC[key]), key)
        shells.append(s)
    SHELL_T = np.concatenate([L.triangles(s, tol=0.05, ang=0.10) for s in shells])
    L.memory("shell")

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    made, recs = [], {}
    for name in (easy, hard):
        lab = next(k for k, v in NAME_MAP.items() if v == name)
        cap, _ = L.as_single_solid(cart[lab], name)
        w, _, _ = true_axis(cap)
        P = L.surf_points(cap, 40000, tol=0.05)
        cen = P.mean(axis=0)
        # h01.axis_frame, NOT i02.frame.  The two differ by 90.06 deg about the
        # press axis, and seat_solids / the whole REV_H-REV_I terminal-slot
        # convention is written in axis_frame.  Building the slots in the other
        # frame put them across the seat instead of along it -- the gate caught
        # it as "0 of 2 slots open" on both buttons.
        ex, ey = axis_frame(w)
        seat_top = float((np.asarray(core_j["seats"][name]["plateTopWorld"], float) - cen) @ w)
        body, rec = build_receiver(name, cen, w, ex, ey, seat_top, shells, SHELL_T)
        rec["role"] = "EASY" if name == easy else "HARD"
        rec["capCentreWorld"] = cen.tolist()
        rec["axisWorld"] = w.tolist()
        made.append(body)
        recs[name] = rec
        print("")
        print("  %s (%s): vol %.3f  faces %d  solids %d  valid %s"
              % (name, rec["role"], rec["volumeMm3"], rec["faces"], rec["solids"],
                 rec["valid"]))
        print("     transition %.3f mm   landing width %.3f mm   seat half %.2f  slots %d"
              % (rec["transitionLengthMm"], rec["landingWidthMm"],
                 rec["seatHalfSizeMm"], rec["slotsCut"]))
        if rec["droppedFragmentsMm3"]:
            print("     dropped fragments: %s"
                  % ", ".join("%.3f" % d for d in rec["droppedFragmentsMm3"]))
        del cap
        L.memory("build " + name)

    export_step(Compound(children=made, label="C08_GATE_RECEIVERS"),
                str(OUT / "C08_GATE_RECEIVERS.step"))
    for b in made:
        export_step(Compound(children=[b], label=str(b.label)),
                    str(OUT / ("C08_RECEIVER_%s.step" % b.label)))
    L.write_json(OUT / "k02_receiver.json",
                 {"caseEasy": easy, "caseHard": hard,
                  "params": {"capToPlateMm": CAP_TO_PLATE, "seatThicknessMm": SEAT_T,
                             "wallMm": WALL, "pocketXY": POCKET_XY,
                             "openingXY": OPENING_XY, "landClearanceMm": LAND_CLR,
                             "flareMm": FLARE, "slot": [SLOT_W, SLOT_L, SLOT_OFF]},
                  "receivers": recs, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
