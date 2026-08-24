"""A12 - lightweight keep-out assembly for the Thumb cavity.

Everything is placed in the frozen world frame and reported in the local Thumb
frame.  Only the pieces the Thumb inner housing can actually touch are loaded.

SZH-EK056 placement reproduces szh_ek056_provisional_thumb_integration_audit.py
exactly: local (JOY_X, JOY_Y, PIVOT_Z) -> DATUM_P, frame (DATUM_V, DATUM_U,
OUTWARD).  The web reference is PROVISIONAL (docs/71 quality = LOW).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Compound, Cylinder, Location, Plane, Shape, Vector, export_step, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from a09_cap_axis_exposure import NAME_MAP, leaf_parts, press_axis  # noqa: E402

sys.path.insert(0, str(L.ROOT))
from build123d_workbench.szh_ek056_web_reference import (  # noqa: E402
    JOY_X, JOY_Y, PIVOT_Z, MAX_TILT_DEG, MOUNT_HOLE_CENTRES, MOUNT_HOLE_D,
    STATIC_BASE_MIN, STATIC_BASE_MAX, build_reference,
)

OUT = L.LAB / "06_keepouts"
OUTWARD = -L.DATUM_N


def szh_location():
    pivot = np.asarray((JOY_X, JOY_Y, PIVOT_Z), float)
    origin = (L.DATUM_P - L.DATUM_V * pivot[0] - L.DATUM_U * pivot[1] - OUTWARD * pivot[2])
    plane = Plane(origin=L.xyz(origin), x_dir=L.xyz(L.DATUM_V), z_dir=L.xyz(OUTWARD))
    return Location(plane), origin


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    loc, origin = szh_location()
    print("SZH placement origin (world) =", np.round(origin, 6))

    ref, parts, moving_world, moving_local = build_reference()
    keep = []
    rows = {}
    for name, shape in parts.items():
        s = shape.moved(loc)
        try:
            solid, _ = L.as_single_solid(s, "SZH_" + name)
        except RuntimeError:
            continue
        lb = L.local_bbox(solid, 20000)
        rows["SZH_" + name] = {"volumeMm3": L.vol(solid), "localBbox": lb}
        keep.append(solid)
        print("  SZH %-34s vol=%9.2f u[%7.2f,%7.2f] v[%7.2f,%7.2f] n[%7.2f,%7.2f]"
              % (name[:34], L.vol(solid), lb["min"][0], lb["max"][0],
                 lb["min"][1], lb["max"][1], lb["min"][2], lb["max"][2]))
    mv = moving_world.moved(loc)
    mv_solid, _ = L.as_single_solid(mv, "SZH_MOVING_ENVELOPE_%gdeg" % MAX_TILT_DEG)
    lb = L.local_bbox(mv_solid, 40000)
    rows["SZH_MOVING_ENVELOPE"] = {"volumeMm3": L.vol(mv_solid), "localBbox": lb,
                                   "maxTiltDeg": MAX_TILT_DEG}
    keep.append(mv_solid)
    print("  SZH MOVING ENVELOPE (%.0f deg)     vol=%9.2f u[%7.2f,%7.2f] v[%7.2f,%7.2f] n[%7.2f,%7.2f]"
          % (MAX_TILT_DEG, L.vol(mv_solid), lb["min"][0], lb["max"][0],
             lb["min"][1], lb["max"][1], lb["min"][2], lb["max"][2]))
    L.memory("szh placed")

    # mounting holes, expressed in the local Thumb frame, for the C01 mount
    mount = []
    for (x, y) in MOUNT_HOLE_CENTRES:
        w = origin + L.DATUM_V * x + L.DATUM_U * y
        mount.append(L.to_local(w)[0].tolist())
    rows["SZH_MOUNT_HOLE_CENTRES_LOCAL"] = {"holeDiameterMm": MOUNT_HOLE_D, "centres": mount}
    print("  SZH mount holes local (u,v,n):")
    for m in mount:
        print("     %s" % np.round(m, 4))

    # ---- frozen N1/N2 shared carrier ------------------------------------
    carrier = import_step(L.SRC["N1_N2_CARRIER"])
    csolid, ncs = L.as_single_solid(carrier, "N1_N2_SHARED_CARRIER")
    lb = L.local_bbox(csolid, 40000)
    rows["N1_N2_SHARED_CARRIER"] = {"volumeMm3": L.vol(csolid), "inputSolids": ncs,
                                    "localBbox": lb}
    keep.append(csolid)
    print("\n  N1/N2 carrier                      vol=%9.2f u[%7.2f,%7.2f] v[%7.2f,%7.2f] n[%7.2f,%7.2f]"
          % (L.vol(csolid), lb["min"][0], lb["max"][0], lb["min"][1], lb["max"][1],
             lb["min"][2], lb["max"][2]))

    # ---- original shell-side M3 screws ----------------------------------
    scr = import_step(L.SRC["ORIGINAL_FASTENING"])
    n = 0
    for child in (list(getattr(scr, "children", []) or []) or [scr]):
        if not child.solids():
            continue
        s, _ = L.as_single_solid(child, "ORIGINAL_SCREW_%d" % (n + 1))
        lb = L.local_bbox(s, 12000)
        rows["ORIGINAL_SCREW_%d" % (n + 1)] = {"label": str(child.label),
                                               "volumeMm3": L.vol(s), "localBbox": lb}
        keep.append(s)
        print("  screw %-28s vol=%9.2f u[%7.2f,%7.2f] v[%7.2f,%7.2f] n[%7.2f,%7.2f]"
              % (str(child.label)[:28], L.vol(s), lb["min"][0], lb["max"][0],
                 lb["min"][1], lb["max"][1], lb["min"][2], lb["max"][2]))
        n += 1

    # ---- frozen Thumb caps + press axes ---------------------------------
    root, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    axes = {}
    for label, short in NAME_MAP.items():
        cap, _ = L.as_single_solid(cart[label], "CAP_" + short)
        ax, cen, _, tilt = press_axis(cap)
        axes[short] = {"axisWorld": ax.tolist(), "capCentreWorld": cen.tolist(),
                       "capCentreLocal": L.to_local(cen)[0].tolist(),
                       "axisLocal": [float(np.dot(ax, L.DATUM_U)), float(np.dot(ax, L.DATUM_V)),
                                     float(np.dot(ax, OUTWARD))],
                       "tiltFromJoystickAxisDeg": tilt}
        keep.append(cap)
    rows["FROZEN_CONTROL_AXES"] = axes

    asm = Compound(children=keep, label="THUMB_KEEPOUT_ASSEMBLY")
    export_step(asm, str(OUT / "THUMB_KEEPOUT_ASSEMBLY.step"))
    print("\nkeep-out assembly: %d solids -> 06_keepouts/THUMB_KEEPOUT_ASSEMBLY.step" % len(keep))
    L.write_json(OUT / "a12_keepouts.json",
                 {"szhPlacementOriginWorld": origin.tolist(),
                  "szhReferenceQuality": "PROVISIONAL / WEB / docs71 quality LOW",
                  "staticBaseLocalMinMax": [list(STATIC_BASE_MIN), list(STATIC_BASE_MAX)],
                  "items": rows, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
