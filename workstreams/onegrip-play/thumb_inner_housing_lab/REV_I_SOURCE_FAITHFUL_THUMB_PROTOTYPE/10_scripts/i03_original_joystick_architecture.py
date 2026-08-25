"""I03 - ORIGINAL joystick as a COMPLETE stack (REV_I section 6, 10).

Section 6 is explicit that the joystick must not be treated as an internal
keep-out.  The original designer's packaging scale, protrusion scale and
button/joystick relationship are design references, so all three are measured
here from exact geometry, on the JOY true axis.

Original joystick parts in ORIGINAL_THUMB_CARTRIDGE:
    THUMB_JOYSTICK_HW504_COMPONENT_1   1461.114 mm3   module body
    THUMB_JOYSTICK_HW504_COMPONENT_2    767.126 mm3   moving stick
    THUMB_JOYSTICK_SMALL_ATTACHMENT     284.541 mm3   knob the user touches

The SZH-EK056 web reference is measured alongside, but it is tagged
PROVISIONAL throughout: section 11 makes the received hardware the authority and
forbids letting uncertain sub-mm web geometry drive a redesign.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from i02_original_external_stack import frame, skin_reference  # noqa: E402

OUT = L.LAB / "03_original_joystick"
JOY_LABEL = "THUMB_JOYSTICK_SMALL_ATTACHMENT"
MODULE = "THUMB_JOYSTICK_HW504_COMPONENT_1"
STICK = "THUMB_JOYSTICK_HW504_COMPONENT_2"
PLATE = "THUMB_BACKPLATE"

# SZH web reference, classified per section 11
SZH_CLASS = {
    "PCB_34P5_X_26_PHOTO_PATTERN": "PROVISIONAL STATIC",
    "CENTRAL_GIMBAL_ENVELOPE": "PROVISIONAL STATIC",
    "X_AXIS_POT_HOUSING": "PROVISIONAL STATIC",
    "Y_AXIS_POT_HOUSING": "PROVISIONAL STATIC",
    "PUSH_SWITCH_HOUSING": "PROVISIONAL STATIC",
    "JOYSTICK_SHAFT_INFERRED": "PROVISIONAL MOVING",
    "REMOVABLE_CAP_NOMINAL_ENVELOPE": "REMOVABLE HARDWARE",
    "HEADER_INSULATOR": "REMOVABLE HARDWARE",
    "HEADER_PIN_1": "REMOVABLE HARDWARE",
    "HEADER_PIN_2": "REMOVABLE HARDWARE",
    "HEADER_PIN_3": "REMOVABLE HARDWARE",
    "HEADER_PIN_4": "REMOVABLE HARDWARE",
    "HEADER_PIN_5": "REMOVABLE HARDWARE",
    "STATIC_BASE_BOUND": "PROVISIONAL STATIC",
    "STATIC_NEUTRAL_HANDLE_BOUND": "PROVISIONAL MOVING",
    "MOVING_CLEARANCE_ENVELOPE_25DEG_INFERRED": "PROVISIONAL MOVING ENVELOPE",
}


def span(P, cen, w):
    s = (P - cen) @ w
    return float(s.min()), float(s.max())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sh = []
    for k in ("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER"):
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        sh.append(s)
    Tsh = np.concatenate([L.triangles(s, tol=0.08, ang=0.15) for s in sh])
    Psh = np.concatenate([L.surf_points(s, 700000, tol=0.08) for s in sh])
    orig_c = L.DATUM_P - L.THUMB_DELTA
    Psh = Psh[np.linalg.norm(Psh - orig_c, axis=1) < 60.0]
    print("original shell: %d triangles, %d samples" % (len(Tsh), len(Psh)))
    L.memory("shell")

    _, cart = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    knob, _ = L.as_single_solid(cart[JOY_LABEL], "KNOB")
    w, _, _ = true_axis(knob)
    Pk = L.surf_points(knob, 80000, tol=0.03)
    cen = Pk.mean(axis=0)
    ex, ey = frame(w)
    r_k = float(np.hypot((Pk - cen) @ ex, (Pk - cen) @ ey).max())
    ref = skin_reference(Tsh, cen, w, ex, ey, r_k)
    skin = ref["referenceMm"]
    print("JOY axis %s" % np.round(w, 6))
    print("JOY outer skin reference on axis: %.4f (ring %.2f-%.2f mm)"
          % (skin, ref["ringMm"][0], ref["ringMm"][1]))

    parts = {}
    for tag, lab in (("KNOB", JOY_LABEL), ("MODULE", MODULE), ("STICK", STICK),
                     ("BACKPLATE", PLATE)):
        s, _ = L.as_single_solid(cart[lab], tag)
        P = L.surf_points(s, 120000, tol=0.04)
        lo, hi = span(P, cen, w)
        d = P - cen
        rad = np.hypot(d @ ex, d @ ey)
        parts[tag] = {"volumeMm3": L.vol(s),
                      "axialLowAboveSkinMm": lo - skin,
                      "axialHighAboveSkinMm": hi - skin,
                      "axialLengthMm": hi - lo,
                      "maxRadiusFromAxisMm": float(rad.max()),
                      "bboxMm": [float(v) for v in
                                 (s.bounding_box().size.X, s.bounding_box().size.Y,
                                  s.bounding_box().size.Z)]}
        parts[tag]["_pts"] = P
        del s

    print("")
    print("=== ORIGINAL joystick, external stack on the JOY true axis ===")
    print("%-10s %12s %12s %10s %10s"
          % ("part", "low vs skin", "high vs skin", "length", "maxRadius"))
    for tag in ("KNOB", "STICK", "MODULE", "BACKPLATE"):
        p = parts[tag]
        print("%-10s %12.3f %12.3f %10.3f %10.3f"
              % (tag, p["axialLowAboveSkinMm"], p["axialHighAboveSkinMm"],
                 p["axialLengthMm"], p["maxRadiusFromAxisMm"]))

    knob_top = parts["KNOB"]["axialHighAboveSkinMm"]
    knob_base = parts["KNOB"]["axialLowAboveSkinMm"]
    mod_top = parts["MODULE"]["axialHighAboveSkinMm"]
    mod_bot = parts["MODULE"]["axialLowAboveSkinMm"]
    shaft_exposed = knob_base - mod_top

    # opening the knob passes through
    prof = []
    for z in np.arange(skin - 12.0, skin + 0.5, 0.25):
        o = cen + w * z
        rr = []
        for a in np.arange(0.0, 2 * np.pi - 1e-9, np.pi / 18.0):
            h = ray_intervals(Tsh, o, ex * np.cos(a) + ey * np.sin(a), 0.0, 26.0)
            if h:
                rr.append(float(h[0][0]))
        prof.append((float(z - skin), float(min(rr)) if len(rr) > 18 else float("nan")))
    bore = [r for z, r in prof if -6.0 < z < -1.0 and np.isfinite(r)]
    joy_bore = float(min(bore)) if bore else float("nan")

    # nearest cap and seat relationships
    caps = {}
    tree_k = cKDTree(np.concatenate([parts["KNOB"]["_pts"], parts["STICK"]["_pts"],
                                     parts["MODULE"]["_pts"]]))
    print("")
    print("=== ORIGINAL button / joystick relationship ===")
    print("%-5s %12s %14s %16s" % ("cap", "centre gap", "surface gap", "capTop-knobTop"))
    for short in ORDER:
        if short == "JOY":
            continue
        lab = next(k for k, v in NAME_MAP.items() if v == short)
        c, _ = L.as_single_solid(cart[lab], short)
        Pc = L.surf_points(c, 40000, tol=0.05)
        cc = Pc.mean(axis=0)
        top = float(((Pc - cen) @ w).max()) - skin
        gap = float(tree_k.query(Pc)[0].min())
        caps[short] = {"centreDistanceMm": float(np.linalg.norm(cc - cen)),
                       "surfaceGapToJoystickMm": gap,
                       "capTopAboveSkinMm": top,
                       "capTopMinusKnobTopMm": top - knob_top}
        print("%-5s %12.3f %14.3f %16.3f"
              % (short, caps[short]["centreDistanceMm"], gap, top - knob_top))
        del c
        L.memory("cap " + short)

    print("")
    print("=== ORIGINAL joystick internal package ===")
    print("  knob top above skin              %+8.3f" % knob_top)
    print("  knob base above skin             %+8.3f" % knob_base)
    print("  exposed shaft between them       %8.3f" % shaft_exposed)
    print("  module top above skin            %+8.3f" % mod_top)
    print("  module bottom above skin         %+8.3f" % mod_bot)
    print("  module axial length              %8.3f" % parts["MODULE"]["axialLengthMm"])
    print("  internal depth used, skin->module bottom  %8.3f" % (-mod_bot))
    print("  JOY opening half-width in the shell       %8.3f" % joy_bore)
    print("  knob max radius                           %8.3f"
          % parts["KNOB"]["maxRadiusFromAxisMm"])
    print("  module max radius from axis               %8.3f"
          % parts["MODULE"]["maxRadiusFromAxisMm"])
    print("  nearest cap surface to joystick           %8.3f"
          % min(v["surfaceGapToJoystickMm"] for v in caps.values()))
    print("  knob top stands %.3f mm above the tallest cap top"
          % (knob_top - max(v["capTopAboveSkinMm"] for v in caps.values())))

    # backplate relationship
    Pb = parts["BACKPLATE"]["_pts"]
    db = Pb - cen
    rb = np.hypot(db @ ex, db @ ey)
    nb = db @ w
    near = rb < 16.0
    print("")
    print("=== ORIGINAL joystick / support-plate relationship ===")
    if near.sum():
        print("  plate material within 16 mm of the JOY axis spans %+.3f to %+.3f above skin"
              % (float(nb[near].min() - skin), float(nb[near].max() - skin)))
        hole = rb[np.abs(nb - (mod_top + skin)) < 1.0]
        print("  closest plate material to the axis at the module top plane: %s"
              % ("%.3f mm" % float(hole.min()) if hole.size else "none in that band"))
    print("  module bottom to plate: %.3f mm"
          % float(cKDTree(Pb).query(parts["MODULE"]["_pts"])[0].min()))

    # SZH provisional reference
    _, szh = leaf_parts("SZH_WEB_REFERENCE")
    sz = {}
    print("")
    print("=== SZH-EK056 web reference (PROVISIONAL, section 11) ===")
    print("%-42s %11s  %s" % ("part", "volume", "class"))
    for lab, node in szh.items():
        s, _ = L.as_single_solid(node, lab)
        bb = s.bounding_box()
        sz[lab] = {"volumeMm3": L.vol(s), "class": SZH_CLASS.get(lab, "UNCLASSIFIED"),
                   "bboxMm": [float(bb.size.X), float(bb.size.Y), float(bb.size.Z)]}
        print("%-42s %11.3f  %s" % (lab[:42], sz[lab]["volumeMm3"], sz[lab]["class"]))
        del s

    for v in parts.values():
        v.pop("_pts", None)
    L.write_json(OUT / "i03_original_joystick_architecture.json",
                 {"joyAxisWorld": w.tolist(), "knobCentreWorld": cen.tolist(),
                  "outerSkinReference": ref, "parts": parts,
                  "externalStack": {"knobTopAboveSkinMm": knob_top,
                                    "knobBaseAboveSkinMm": knob_base,
                                    "exposedShaftMm": shaft_exposed,
                                    "moduleTopAboveSkinMm": mod_top,
                                    "moduleBottomAboveSkinMm": mod_bot,
                                    "internalDepthUsedMm": -mod_bot,
                                    "joyBoreHalfWidthMm": joy_bore},
                  "openingProfile": [{"aboveSkinMm": z, "halfWidthMm": r} for z, r in prof],
                  "capRelationship": caps,
                  "szhWebReference": sz,
                  "szhQuality": "PROVISIONAL - web model, docs/71 quality LOW",
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
