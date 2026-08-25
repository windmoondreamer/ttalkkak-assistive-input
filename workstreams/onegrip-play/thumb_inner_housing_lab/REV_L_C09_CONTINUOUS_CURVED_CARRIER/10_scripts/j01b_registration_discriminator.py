"""J01b - decide the registration question properly (REV_I section 7).

J01 returned MEDIUM because four of the nine Thumb control axes showed a
0.001-0.034 mm skin delta and several showed a different NUMBER of material
intervals.  Neither of those is evidence of a frame shift, and the confidence
rule that produced MEDIUM could not tell the difference between:

    a rigid displacement of the Thumb region        -- would be fatal
    new Finger cuts intersecting a Thumb probe ray  -- expected, docs/101 adds 8
    a different tessellation of the same surface    -- 25204 vs 44924 triangles

So this measures the thing that actually discriminates: the point-to-surface
distance from a dense sample of the AUTHORITY Thumb surface to the docs/101
surface, restricted to the Thumb region, plus the same comparison against the
docs/101 BARE base which has no Finger cuts at all.

A rigid shift of even 0.05 mm shows up immediately in the median. Tessellation
noise shows up only in the tail.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402

OUT = L.LAB / "02_registration"
RADIUS = 40.0          # Thumb region around DATUM_P
FINGER_KEEP = 12.0     # ignore points this close to a frozen Finger centre


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    dat = json.loads((L.ROOT / "build123d_workbench/out/lower15_true_bare_finger_base"
                      / "finger_button_frozen_datums.json").read_text(encoding="utf-8"))
    fing = {k: np.asarray(v["centerMm"], float) for k, v in dat["controls"].items()}

    # EXACT ray probes.  A nearest-neighbour query between two independent
    # surface SAMPLINGS measures sample spacing, not surface displacement: run
    # against the docs/101 BARE base -- a shell whose own validation certifies
    # the Thumb region is untouched -- it still reported p50 0.090 / p90 0.190 /
    # max 9.18 mm.  Ray-to-triangle intersection has no such floor.
    def tris(keys, tag):
        T = []
        for k in keys:
            s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
            T.append(L.triangles(s, tol=0.05, ang=0.10))
            del s
        T = np.concatenate(T)
        print("  %-26s %8d triangles" % (tag, len(T)))
        return T

    Ta = tris(("JAD_APPROVED", "JFD_APPROVED"), "frozen authority")
    Tb = tris(("D101_JAD", "D101_JFD"), "docs/101 shell")
    Tc = tris(("D101_BASE_JAD", "D101_BASE_JFD"), "docs/101 bare base")
    L.memory("tris")

    u1, u2 = L.DATUM_U, L.DATUM_V
    d = -L.DATUM_N
    probes = []
    for a1 in np.arange(-22.0, 22.01, 2.0):
        for a2 in np.arange(-48.0, 14.01, 2.0):
            probes.append(L.DATUM_P + u1 * a1 + u2 * a2)
    probes = np.asarray(probes)
    print("  %d parallel probes across the Thumb panel, along -DATUM_N" % len(probes))

    out = {}
    for tag, T in (("docs101_shell", Tb), ("docs101_bare_base", Tc)):
        da, n_both, n_only = [], 0, 0
        for p0 in probes:
            o = p0 + d * 60.0
            ha = ray_intervals(Ta, o, -d, 0.0, 120.0)
            hb = ray_intervals(T, o, -d, 0.0, 120.0)
            if not ha or not hb:
                if bool(ha) != bool(hb):
                    n_only += 1
                continue
            n_both += 1
            da.append(abs(float(ha[0][0]) - float(hb[0][0])))
        da = np.asarray(da) if da else np.zeros(1)
        far = 0
        for p0, e in zip(probes[:len(da)], da):
            if min(np.linalg.norm(p0 - c) for c in fing.values()) > FINGER_KEEP:
                far += 1
        out[tag] = {"probes": int(len(probes)), "bothHit": n_both,
                    "oneSideOnly": n_only,
                    "firstHitDeltaMm": {str(q): float(np.percentile(da, q))
                                        for q in (50, 90, 99)},
                    "firstHitMaxMm": float(da.max()),
                    "exactZeroFraction": float((da < 1.0e-9).mean())}
        print("")
        print("  authority -> %s (exact first-hit position on the outer skin)" % tag)
        print("    p50 %.9f  p90 %.9f  p99 %.9f  max %.9f mm"
              % (*[np.percentile(da, q) for q in (50, 90, 99)], da.max()))
        print("    exactly zero on %.2f%% of %d probes; %d probes hit one shell only"
              % (100 * (da < 1.0e-9).mean(), n_both, n_only))
        L.memory(tag)

    # where do the Thumb control axes pick up an EXTRA interval?  If registration
    # is sound, every extra crossing must sit inside a Finger pocket.
    print("")
    print("=== extra axis intervals attributed to Finger geometry ===")
    Ta = []
    for k in ("JAD_APPROVED", "JFD_APPROVED"):
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        Ta.append(L.triangles(s, tol=0.06, ang=0.12))
        del s
    Ta = np.concatenate(Ta)
    Tb = []
    for k in ("D101_JAD", "D101_JFD"):
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        Tb.append(L.triangles(s, tol=0.06, ang=0.12))
        del s
    Tb = np.concatenate(Tb)
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    attrib = {}
    print("%-5s %-34s %s" % ("ctrl", "boundaries that moved", "nearest frozen Finger"))
    for short in ORDER:
        lab = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[lab], short)
        w, _, _ = true_axis(cap)
        cen = L.surf_points(cap, 30000, tol=0.06).mean(axis=0)
        ia = ray_intervals(Ta, cen, w, -45.0, 45.0) or []
        ib = ray_intervals(Tb, cen, w, -45.0, 45.0) or []
        ba = sorted([x for p in ia for x in p])
        bb = sorted([x for p in ib for x in p])
        moved = []
        for t in set(np.round(ba, 3)).symmetric_difference(set(np.round(bb, 3))):
            moved.append(float(t))
        near = []
        for t in moved:
            p = cen + w * t
            k, d = min(((k, float(np.linalg.norm(p - c))) for k, c in fing.items()),
                       key=lambda z: z[1])
            near.append((k, d))
        attrib[short] = {"movedBoundariesMm": moved,
                         "nearestFinger": [{"button": k, "distanceMm": d} for k, d in near]}
        txt = ", ".join("%.2f" % t for t in sorted(moved)[:4]) or "none"
        nn = ", ".join("%s %.1f" % (k, d) for k, d in near[:3]) or "-"
        print("%-5s %-34s %s" % (short, txt, nn))
        del cap

    worst_far = max(out[k]["firstHitDeltaMm"]["99"] for k in out)
    conf = "HIGH" if worst_far < 0.01 else "MEDIUM" if worst_far < 0.20 else "LOW"
    print("")
    print("  worst p99 exact first-hit delta = %.9f mm" % worst_far)
    print("  COORDINATE REGISTRATION CONFIDENCE = %s" % conf)

    L.write_json(OUT / "j01b_registration_discriminator.json",
                 {"radiusMm": RADIUS, "fingerKeepMm": FINGER_KEEP,
                  "method": "exact ray first-hit comparison on the outer skin",
                  "rejectedMethod": ("nearest-neighbour between two independent surface "
                                     "samplings -- measures sample spacing, gave p50 0.090 mm "
                                     "even against a shell certified unchanged"),
                  "firstHitDeltas": out, "axisBoundaryAttribution": attrib,
                  "registrationConfidence": conf, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
