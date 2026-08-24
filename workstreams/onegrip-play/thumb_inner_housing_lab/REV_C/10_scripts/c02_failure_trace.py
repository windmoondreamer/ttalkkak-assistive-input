"""C02 - why the exact STEP lost T2/T4/T6/T7/T8 (REV_C section 4).

Both cutter families used by the production generator are reconstructed here
exactly as the generator builds them, then measured against the wall they were
supposed to cut.  Nothing is patched.

Family 1  translated original opening VOIDS
    integrated_exterior_clean_v1.build():
        restore_original_thumb_openings()  -> fill the old openings
        opening_voids()                    -> defeature(shell, faces) - shell
                                              i.e. a PLUG the thickness of the
                                              wall AT THE ORIGINAL LOCATION
        move(void, (0, +12.25, -21))       -> rigid translation
        cut_shapes(restored, voids)

Family 2  world-axis AABB service boxes
    integrated_exterior_lowered_thumb_v1.build():
        thumb_user_side_service_box(control, 0.80)
          = Box(world AABB of the CAP + 0.80 mm)  &  slab(THUMB_SEAT plane)

Constants copied from build123d_workbench/finger_thumb_integrated_v3.py
(read, not imported, so nothing production-side can run).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import Align, Box, Location, Plane, Vector, export_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, ray_intervals, true_axis  # noqa: E402

OUT = L.LAB / "02_failure_trace"
OUTWARD = -L.DATUM_N

THUMB_SEAT_CENTER = np.asarray((-0.23581763, -4.41709540, 24.99272364), float)
THUMB_SEAT_U = np.asarray((1.0, 0.0, 0.0), float)
THUMB_SEAT_N = L.unit(np.asarray((0.00017647, 0.60270162, 0.79796662), float))
THUMB_OPENING_CLEARANCE = 0.80
SLAB_WU, SLAB_WV, SLAB_DN = 100.0, 120.0, 23.0


def aabb_service_box(shape, clearance, label):
    b = shape.bounding_box()
    r = Box(float(b.size.X) + 2 * clearance, float(b.size.Y) + 2 * clearance,
            float(b.size.Z) + 2 * clearance,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)).moved(
        Location(Vector(0.5 * (float(b.min.X) + float(b.max.X)),
                        0.5 * (float(b.min.Y) + float(b.max.Y)),
                        0.5 * (float(b.min.Z) + float(b.max.Z)))))
    r.label = label
    return r


def user_side_slab():
    c = THUMB_SEAT_CENTER + THUMB_SEAT_N * 5.5
    pl = Plane(origin=L.xyz(c), x_dir=L.xyz(THUMB_SEAT_U), z_dir=L.xyz(THUMB_SEAT_N))
    s = pl.location * Box(SLAB_WU, SLAB_WV, SLAB_DN,
                          align=(Align.CENTER, Align.CENTER, Align.CENTER))
    s.label = "USER_SIDE_SLAB"
    return s


def extent_along(shape, origin, axis):
    """Extent over ALL vertices.  Only valid for a box aligned with `axis`."""
    v = np.asarray([[p.X, p.Y, p.Z] for p in shape.vertices()], float)
    t = (v - origin) @ axis
    return float(t.min()), float(t.max())


def reach_on_ray(shape, origin, axis):
    """How far the tool actually extends ALONG THE RAY through `origin`.

    A world-axis AABB around a tilted cap has corners far up the tilted axis
    while the box itself stops much earlier on the axis line.  Measuring over
    all vertices (the first pass did) overstates the reach by several mm and
    makes the cutter look adequate when it is not.
    """
    T = L.triangles(shape, tol=0.02, ang=0.05)
    iv = ray_intervals(T, origin, axis, -60.0, 60.0)
    if not iv:
        return None
    return max(iv, key=lambda p: p[1])


def wall_on_axis(T, origin, axis, t_from):
    iv = ray_intervals(T, origin, axis)
    out = [p for p in (iv or []) if p[1] > t_from]
    if not out:
        return None
    return max(out, key=lambda p: p[1] - p[0])


def main() -> int:
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    Tfz = L.triangles(frozen, tol=0.05, ang=0.10)
    del frozen
    clean = combined_shell("JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER", box, "CLEAN")
    Tcl = L.triangles(clean, tol=0.05, ang=0.10)
    del clean
    L.memory("shells")

    _, cartL = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    _, cartO = leaf_parts("ORIGINAL_THUMB_CARTRIDGE")
    slab = user_side_slab()
    sl_lo, sl_hi = extent_along(slab, L.DATUM_P, OUTWARD)
    print("USER_SIDE_SLAB spans local n = [%.3f, %.3f]  (not the limiting factor)"
          % (sl_lo, sl_hi))

    rows = {}
    print("\n%-5s %8s %9s %9s %10s %10s %10s"
          % ("ctrl", "capTop", "AABBmax", "voidMax", "wallInner", "AABBshort", "voidShort"))
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        capL, _ = L.as_single_solid(cartL[label], short)
        capO, _ = L.as_single_solid(cartO[label], short + "_o")
        w, _, tilt = true_axis(capL)
        pts = L.surf_points(capL, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        t_cap = float(((pts - cen) @ w).max())

        # ---- family 2 : the AABB service box, built exactly -------------
        raw = aabb_service_box(capL, THUMB_OPENING_CLEARANCE, short + "_raw")
        tool = (raw & slab).clean()
        t_corner_lo, t_corner_hi = extent_along(tool, cen, w)
        seg = reach_on_ray(tool, cen, w)
        t_lo, t_hi = (seg if seg else (float("nan"), float("nan")))
        aabb_vol = float(tool.volume)

        # ---- family 1 : the translated original void --------------------
        # the plug spans the wall AT THE ORIGINAL LOCATION; measure that wall on
        # the original control's own axis, then apply the same rigid translation
        wO, _, _ = true_axis(capO)
        ptsO = L.surf_points(capO, 40000, tol=0.05)
        cenO = ptsO.mean(axis=0)
        t_capO = float(((ptsO - cenO) @ wO).max())
        # the original wall around the opening: probe a ring just outside the cap
        ring_t = []
        for ang in range(0, 360, 30):
            r = 6.0
            ex = L.unit(L.DATUM_U - wO * float(np.dot(wO, L.DATUM_U)))
            ey = np.cross(wO, ex)
            p = cenO + ex * (r * np.cos(np.radians(ang))) + ey * (r * np.sin(np.radians(ang)))
            s = wall_on_axis(Tcl, p, wO, -6.0)
            if s:
                ring_t.append(s)
        if ring_t:
            void_lo = float(np.median([s[0] for s in ring_t]))
            void_hi = float(np.median([s[1] for s in ring_t]))
        else:
            void_lo = void_hi = float("nan")
        # the plug travels with the cartridge, so in the LOWERED control's own
        # frame it occupies the same t interval it had in the original frame
        t_void_lo, t_void_hi = void_lo, void_hi

        # ---- the wall it had to cut, in the RESTORED shell ---------------
        # restored = CLEAN with the old openings filled.  At the lowered control
        # the old opening is 22.38 mm away in v, EXCEPT for T7/T8 where the old
        # T1/T3 opening sits almost on top of the new position.
        wall_clean = wall_on_axis(Tcl, cen, w, t_cap)
        wall_frozen = wall_on_axis(Tfz, cen, w, t_cap)
        wall_inner = wall_clean[0] if wall_clean else None

        row = {"tiltDeg": tilt, "capTopAlongAxisMm": t_cap,
               "aabbToolReachOnAxisRayMm": [t_lo, t_hi],
               "aabbToolCornerExtentMm": [t_corner_lo, t_corner_hi],
               "aabbToolVolumeMm3": aabb_vol,
               "translatedVoidExtentAlongAxisMm": [t_void_lo, t_void_hi],
               "cleanWallOnAxisMm": list(wall_clean) if wall_clean else None,
               "frozenWallOnAxisMm": list(wall_frozen) if wall_frozen else None}
        if wall_inner is not None:
            row["aabbShortfallMm"] = wall_inner - t_hi
            row["voidShortfallMm"] = wall_inner - t_void_hi
        rows[short] = row
        print("%-5s %8.3f %9.3f %9.3f %10s %10s %10s"
              % (short, t_cap, t_hi, t_void_hi,
                 ("%.3f" % wall_inner) if wall_inner is not None else "OPEN",
                 ("%+.3f" % row["aabbShortfallMm"]) if "aabbShortfallMm" in row else "-",
                 ("%+.3f" % row["voidShortfallMm"]) if "voidShortfallMm" in row else "-"))
        del capL, capO, raw, tool
        L.memory("trace " + short)

    export_step(slab, str(OUT / "USER_SIDE_SLAB.step"))
    print("\n(positive shortfall = the cutter stops that many mm SHORT of the wall)")
    L.write_json(OUT / "c02_failure_trace.json",
                 {"slabLocalNExtent": [sl_lo, sl_hi],
                  "thumbOpeningClearanceMm": THUMB_OPENING_CLEARANCE,
                  "controls": rows, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
