"""I06b - CURRENT joystick stack against the ORIGINAL law (REV_I sections 6, 10, 15).

I03 measured what the original designer actually built:

    knob top        +7.607 mm above the skin
    knob base       -3.393 mm  (guided 3.4 mm inside a 14.20 mm opening)
    exposed shaft    1.400 mm
    module top      -4.793 mm
    module bottom   -19.043 mm, sitting on the support plate with a 0.011 mm gap
    knob top stands  6.556 mm above the tallest button cap

Section 10 says the external joystick relationship is a functional requirement
and the SZH must not simply be dropped wherever it fits internally.  So this
measures the CURRENT JOY opening, places the provisional SZH the way the
original module was placed -- static base bearing on the seat plane -- and
reports what knob height that produces against the original +7.607 mm.

Everything SZH is PROVISIONAL (section 11).  Nothing here is cut from anything.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from h03_placement import KEEPOUTS  # noqa: E402
from i02_original_external_stack import frame, skin_reference  # noqa: E402
from i06_current_core_with_joystick import classify  # noqa: E402

OUT = L.LAB / "06_current_core"
JOY_LABEL = "THUMB_JOYSTICK_SMALL_ATTACHMENT"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    orig = json.loads((L.LAB / "03_original_joystick" /
                       "i03_original_joystick_architecture.json").read_text(encoding="utf-8"))
    core = json.loads((OUT / "i06_current_core.json").read_text(encoding="utf-8"))

    T = []
    for k in ("JAD_APPROVED", "JFD_APPROVED"):
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        T.append(L.triangles(s, tol=0.06, ang=0.12))
        del s
    T = np.concatenate(T)
    L.memory("shell")

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    knob, _ = L.as_single_solid(cart[JOY_LABEL], "KNOB")
    w, _, _ = true_axis(knob)
    P = L.surf_points(knob, 80000, tol=0.03)
    cen = P.mean(axis=0)
    ex, ey = frame(w)
    r_k = float(np.hypot((P - cen) @ ex, (P - cen) @ ey).max())
    ref = skin_reference(T, cen, w, ex, ey, r_k)
    skin = ref["referenceMm"]
    print("CURRENT JOY skin reference on axis: %.4f" % skin)

    # current JOY opening
    prof = []
    for z in np.arange(skin - 14.0, skin + 0.5, 0.25):
        o = cen + w * z
        rr = []
        for a in np.arange(0.0, 2 * np.pi - 1e-9, np.pi / 18.0):
            h = ray_intervals(T, o, ex * np.cos(a) + ey * np.sin(a), 0.0, 30.0)
            if h:
                rr.append(float(h[0][0]))
        prof.append((float(z - skin), float(min(rr)) if len(rr) > 18 else float("nan")))
    guided = [r for z, r in prof if -6.0 < z < -1.5 and np.isfinite(r)]
    joy_bore = float(min(guided)) if guided else float("nan")
    o_bore = orig["externalStack"]["joyBoreHalfWidthMm"]
    print("  current JOY opening half-width %.3f mm  (original %.3f)" % (joy_bore, o_bore))
    print("  inherited knob max radius      %.3f mm" % r_k)

    # where the inherited knob sits now
    s = (P - cen) @ w
    print("  inherited knob top  %+.3f above skin  (original %+.3f)"
          % (float(s.max()) - skin, orig["externalStack"]["knobTopAboveSkinMm"]))
    print("  inherited knob base %+.3f above skin  (original %+.3f)"
          % (float(s.min()) - skin, orig["externalStack"]["knobBaseAboveSkinMm"]))

    # the seat plane the restored buttons define, projected onto the JOY axis
    plate_pts = np.array([core["seats"][k]["plateTopWorld"] for k in core["seats"]])
    plate_n = np.array([float((p - cen) @ w) for p in plate_pts])
    seat_plane = float(np.median(plate_n))
    print("")
    print("=== seat plane shared with the buttons ===")
    print("  restored button plate planes project to %.3f .. %.3f on the JOY axis"
          % (plate_n.min() - skin, plate_n.max() - skin))
    print("  median seat plane = %.3f mm below the skin" % (skin - seat_plane))
    print("  ORIGINAL module bottom was %.3f mm below the skin"
          % (-orig["externalStack"]["moduleBottomAboveSkinMm"]))

    # SZH provisional parts, as placed by REV_A, measured on the JOY axis
    keep = import_step(str(KEEPOUTS))
    szh = {}
    print("")
    print("=== provisional SZH parts on the JOY axis (nothing is cut) ===")
    print("%-34s %10s %10s %9s  %s"
          % ("part", "low", "high", "maxRad", "class"))
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if not ch.solids() or not lab.startswith("SZH"):
            continue
        ks, _ = L.as_single_solid(ch, lab)
        Q = L.surf_points(ks, 60000, tol=0.05)
        d = Q - cen
        n = d @ w
        rad = np.hypot(d @ ex, d @ ey)
        szh[lab] = {"lowAboveSkinMm": float(n.min() - skin),
                    "highAboveSkinMm": float(n.max() - skin),
                    "maxRadiusMm": float(rad.max()), "class": classify(lab)}
        print("%-34s %10.3f %10.3f %9.3f  %s"
              % (lab[:34], szh[lab]["lowAboveSkinMm"], szh[lab]["highAboveSkinMm"],
                 szh[lab]["maxRadiusMm"], szh[lab]["class"]))
        del ks
        L.memory("szh " + lab)

    base = szh.get("SZH_pcb") or szh.get("SZH_gimbal")
    shaft = szh.get("SZH_shaft")
    target_top = orig["externalStack"]["knobTopAboveSkinMm"]
    res = {"currentSkinOnAxisMm": skin, "joyAxisWorld": w.tolist(),
           "knobCentreWorld": cen.tolist(),
           "currentJoyBoreHalfWidthMm": joy_bore,
           "originalJoyBoreHalfWidthMm": o_bore,
           "inheritedKnobMaxRadiusMm": r_k,
           "inheritedKnobTopAboveSkinMm": float(s.max()) - skin,
           "inheritedKnobBaseAboveSkinMm": float(s.min()) - skin,
           "originalKnobTopAboveSkinMm": target_top,
           "seatPlaneBelowSkinMm": skin - seat_plane,
           "buttonPlatePlaneRangeMm": [float(plate_n.min() - skin), float(plate_n.max() - skin)],
           "szhParts": szh, "openingProfile": [{"aboveSkinMm": z, "halfWidthMm": r}
                                               for z, r in prof]}

    print("")
    print("=== section 10 comparison ===")
    print("  ORIGINAL knob top target            %+8.3f mm above skin" % target_top)
    print("  inherited knob as placed            %+8.3f mm above skin"
          % (float(s.max()) - skin))
    print("  deficit to make up with a new knob  %8.3f mm"
          % (target_top - (float(s.max()) - skin)))
    if shaft:
        print("  provisional SZH shaft spans         %+8.3f .. %+8.3f above skin"
              % (shaft["lowAboveSkinMm"], shaft["highAboveSkinMm"]))
        print("  shaft top to the original knob top  %8.3f mm  <- custom knob adapter"
              % (target_top - shaft["highAboveSkinMm"]))
        res["knobAdapterReachMm"] = target_top - shaft["highAboveSkinMm"]
    if base:
        print("  provisional SZH base bottom         %+8.3f mm above skin"
              % base["lowAboveSkinMm"])
        print("  vs the button seat plane            %+8.3f mm above skin"
              % (seat_plane - skin))
        res["szhBaseVsSeatPlaneMm"] = base["lowAboveSkinMm"] - (seat_plane - skin)
        print("  SZH base sits %.3f mm %s the button seat plane"
              % (abs(res["szhBaseVsSeatPlaneMm"]),
                 "below" if res["szhBaseVsSeatPlaneMm"] < 0 else "above"))

    L.write_json(OUT / "i06b_joystick_current_stack.json", dict(res, memory=L.MEMORY_LOG))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
