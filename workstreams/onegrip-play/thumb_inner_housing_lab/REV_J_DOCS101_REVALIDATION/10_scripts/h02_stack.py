"""H02 - the ORIGINAL button stack, all parts in ONE common frame.

H01 measured the PushBtn about its own centroid, so its n values were not
comparable with the plate and cap intervals.  Everything here is expressed in
the SAME frame: origin at the T8 cap centroid, axis = T8's TRUE press axis.
T8 is used because the cartridge STEP carries exactly one PushBtn solid and it
belongs to that button.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, leaf_parts  # noqa: E402
from b03_axis_authority import true_axis  # noqa: E402
from d02_housing_vs_exact import BP_STEP, Field  # noqa: E402
from h01_seat_audit import axis_frame, local_tris  # noqa: E402

OUT = L.LAB / "01_seat_audit"


def span(shape, origin, w, tol=0.03):
    p = L.surf_points(shape, 60000, tol=tol)
    n = (p - origin) @ w
    return float(n.min()), float(n.max()), p


def main() -> int:
    bp = import_step(str(BP_STEP))
    bp, _ = L.as_single_solid(bp, "BACKPLATE")
    root, cart = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    lab8 = next(k for k, v in NAME_MAP.items() if v == "T8")
    cap, _ = L.as_single_solid(cart[lab8], "T8_CAP")
    pb, _ = L.as_single_solid([v for k, v in cart.items() if "PUSHBTN" in k.upper()][0], "PUSHBTN")

    w, _, tilt = true_axis(cap)
    cpts = L.surf_points(cap, 60000, tol=0.03)
    O = cpts.mean(axis=0)
    ex, ey = axis_frame(w)
    print("common frame: origin = T8 cap centroid, axis = T8 TRUE press axis (tilt %.3f deg)" % tilt)

    cap_lo, cap_hi, _ = span(cap, O, w)
    pb_lo, pb_hi, ppts = span(pb, O, w)
    print("\n%-26s %10s %10s %10s" % ("part", "n min", "n max", "height"))
    print("%-26s %10.3f %10.3f %10.3f" % ("button cap", cap_lo, cap_hi, cap_hi - cap_lo))
    print("%-26s %10.3f %10.3f %10.3f" % ("PushBtn (whole)", pb_lo, pb_hi, pb_hi - pb_lo))

    # PushBtn cross-section profile in the COMMON frame
    d = ppts - O
    a_, b_, n_ = d @ ex, d @ ey, d @ w
    bins = np.linspace(n_.min(), n_.max(), 40)
    prof = []
    for k in range(len(bins) - 1):
        m = (n_ >= bins[k]) & (n_ < bins[k + 1])
        if m.sum() < 15:
            continue
        prof.append((float(0.5 * (bins[k] + bins[k + 1])),
                     float(a_[m].max() - a_[m].min()), float(b_[m].max() - b_[m].min())))
    # classify: body = the 6 x 6 plateau, actuator = the ~3.5 plateau above it
    body = [p for p in prof if 5.6 < p[1] < 6.6 and 5.6 < p[2] < 6.6]
    body_lo = min(p[0] for p in body) if body else None
    body_hi = max(p[0] for p in body) if body else None
    # The actuator is the small section ABOVE the body and the terminals the
    # section BELOW it.  Keying those on the sign of n (the first attempt) is
    # wrong: in this common frame the whole PushBtn sits at negative n.
    act = [p for p in prof if body_hi is not None and p[0] > body_hi and p[1] < 4.6]
    term = [p for p in prof if body_lo is not None and p[0] < body_lo]
    act_lo = min(p[0] for p in act) if act else body_hi
    term_hi = max(p[0] for p in term) if term else body_lo

    # plate on the T8 axis
    Tb = local_tris(bp, O, ex, ey, w)
    f = Field(Tb)
    h = f.hits(0.0, 0.0)
    iv = [(float(h[k]), float(h[k + 1])) for k in range(0, h.size, 2)] if h.size % 2 == 0 else []
    seat = max(iv, key=lambda p: p[1]) if iv else None

    print("%-26s %10.3f %10.3f %10.3f" % ("  switch body (6x6)", body_lo, body_hi,
                                          (body_hi - body_lo) if body else 0))
    print("%-26s %10.3f %10.3f %10.3f" % ("  actuator (~3.5)", act_lo, pb_hi, pb_hi - act_lo))
    print("%-26s %10.3f %10.3f %10.3f" % ("  terminals (below body)", pb_lo, term_hi,
                                          term_hi - pb_lo))
    if seat:
        print("%-26s %10.3f %10.3f %10.3f" % ("Backplate on this axis", seat[0], seat[1],
                                              seat[1] - seat[0]))

    print("\n=== the ORIGINAL stack, measured ===")
    res = {"frame": {"originWorld": O.tolist(), "axisWorld": w.tolist(),
                     "tiltFromJoystickAxisDeg": tilt},
           "capNMm": [cap_lo, cap_hi], "pushBtnNMm": [pb_lo, pb_hi],
           "bodyNMm": [body_lo, body_hi], "actuatorNMm": [act_lo, pb_hi],
           "terminalNMm": [pb_lo, term_hi],
           "plateNMm": list(seat) if seat else None,
           "profile": [{"n": p[0], "sizeX": p[1], "sizeY": p[2]} for p in prof]}
    if body and seat:
        res["bodyBottomToPlateTopMm"] = body_lo - seat[1]
        res["terminalTipBelowPlateBottomMm"] = seat[0] - pb_lo
        res["terminalTravelThroughPlateMm"] = seat[1] - seat[0]
        res["actuatorProjectionAboveBodyMm"] = pb_hi - body_hi
        res["capUndersideToActuatorTipMm"] = cap_lo - pb_hi
        res["capUndersideToPlateTopMm"] = cap_lo - seat[1]
        print("  switch body sits %+.3f mm from the plate top face" % res["bodyBottomToPlateTopMm"])
        print("  terminal tip reaches %+.3f mm below the plate bottom face"
              % res["terminalTipBelowPlateBottomMm"])
        print("  actuator projects %+.3f mm above the body top" % res["actuatorProjectionAboveBodyMm"])
        print("  cap underside is %+.3f mm from the actuator tip" % res["capUndersideToActuatorTipMm"])
        print("  cap underside is %+.3f mm from the plate top face" % res["capUndersideToPlateTopMm"])
        print("  plate thickness on this axis = %.3f mm" % (seat[1] - seat[0]))

    print("\n  PushBtn cross-section in the common frame:")
    for p in prof:
        tagp = ""
        if body and body_lo <= p[0] <= body_hi:
            tagp = "  <- BODY"
        elif act and p[0] >= act_lo:
            tagp = "  <- ACTUATOR"
        elif p[0] < 0 and term and p[0] <= term_hi:
            tagp = "  <- TERMINAL"
        print("     n=%+7.3f   %6.3f x %6.3f mm%s" % (p[0], p[1], p[2], tagp))

    L.write_json(OUT / "h02_stack.json", res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
