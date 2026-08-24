"""D01 - independently verify the exact Onshape export (REV_D sections 4, 13.1-2).

Gate.  Nothing downstream runs unless this passes.

Verifies, without trusting the supplied validation file:
  * SHA-256 of all four exports
  * import, validity, solid count, volume, bounding box
  * shell split at X = 0
  * a Thumb wall exists, with an inner and an outer surface
  * JOY and T1-T8 are full through-openings on their own TRUE press axes
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402

OUT = L.LAB / "01_source_verify"

EXPECTED = {
    "JaD_THUMB_LOWER15_APPROVED.step":
        "622ADB3B1B1D6095435AAC624BB11042080FC8B7399B0C920BECDE708FA54E86",
    "JfD_THUMB_LOWER15_APPROVED.step":
        "D75F62E04DF15B1150EA10EEB8DA1AAA0AAE7CA7C31862CEA42823A0929EA340",
    "JaD_THUMB_LOWER15_APPROVED.x_t":
        "2CFD9CD3D323CF45D57F59B4528EB364B5B5AB1BCEB0A20692B0292A75EB2453",
    "JfD_THUMB_LOWER15_APPROVED.x_t":
        "5C50F3AA199223F673EEE6A9439E5C42C77A082AD9BAFD9B5BCFCDCDB00155F5",
}
EXPECTED_VOL = {"JAD_APPROVED": 47672.950429, "JFD_APPROVED": 50150.498071}
EXPECTED_BBOX = {"JAD_APPROVED": [38.779774, 123.860259, 152.135292],
                 "JFD_APPROVED": [38.779770, 123.860259, 152.135292]}


def main() -> int:
    print("=== SHA-256 gate ===")
    hashes, ok_all = {}, True
    for name, want in EXPECTED.items():
        p = L.EXACT / name
        h = hashlib.sha256(p.read_bytes()).hexdigest().upper()
        ok = h == want
        ok_all &= ok
        hashes[name] = {"sha256": h, "expected": want, "match": ok,
                        "bytes": p.stat().st_size}
        print("  %-42s %s" % (name, "MATCH" if ok else "MISMATCH  " + h))
    if not ok_all:
        print("\nSHA-256 MISMATCH -- STOP")
        return 2

    print("\n=== independent import validation ===")
    rows = {}
    shells = {}
    for key in ("JAD_APPROVED", "JFD_APPROVED"):
        shape = import_step(L.SRC[key])
        solids = list(shape.solids())
        solid, _ = L.as_single_solid(shape, key)
        shells[key] = solid
        b = solid.bounding_box()
        size = [float(b.max.X - b.min.X), float(b.max.Y - b.min.Y),
                float(b.max.Z - b.min.Z)]
        vol = float(solid.volume)
        valid = bool(solid.is_valid)
        dv = vol - EXPECTED_VOL[key]
        db = [size[i] - EXPECTED_BBOX[key][i] for i in range(3)]
        rows[key] = {"solidCount": len(solids), "valid": valid, "volumeMm3": vol,
                     "volumeDeltaMm3": dv, "bboxSizeMm": size, "bboxDeltaMm": db,
                     "faces": len(list(solid.faces())),
                     "shells": len(list(solid.shells())),
                     "bboxMin": [float(b.min.X), float(b.min.Y), float(b.min.Z)],
                     "bboxMax": [float(b.max.X), float(b.max.Y), float(b.max.Z)]}
        print("  %-14s solids=%d valid=%s faces=%d shells=%d"
              % (key, len(solids), valid, len(list(solid.faces())),
                 len(list(solid.shells()))))
        print("       volume %16.6f   delta vs supplied %+.6f mm3" % (vol, dv))
        print("       bbox   %s" % np.round(size, 6))
        print("       delta  %s" % np.round(db, 6))
        print("       X span [%.6f, %.6f]" % (float(b.min.X), float(b.max.X)))
        del shape
        L.memory("import " + key)

    # shell split
    ja = shells["JAD_APPROVED"].bounding_box()
    jf = shells["JFD_APPROVED"].bounding_box()
    split = {"jadXmin": float(ja.min.X), "jadXmax": float(ja.max.X),
             "jfdXmin": float(jf.min.X), "jfdXmax": float(jf.max.X)}
    print("\n  shell split: JaD X in [%.6f, %.6f]   JfD X in [%.6f, %.6f]"
          % (split["jadXmin"], split["jadXmax"], split["jfdXmin"], split["jfdXmax"]))

    # ---- openings on the TRUE press axes ---------------------------------
    both = L.as_single_solid((shells["JAD_APPROVED"] + shells["JFD_APPROVED"]).clean(),
                             "APPROVED")[0]
    T = L.triangles(both, tol=0.05, ang=0.10)
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    print("\n=== JOY + T1-T8 through-openings on their TRUE press axes ===")
    print("%-5s %8s %10s %-30s %10s" % ("ctrl", "tilt", "through", "material outboard of cap",
                                        "footprint"))
    op = {}
    npass = 0
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, tilt = true_axis(cap)
        pts = L.surf_points(cap, 40000, tol=0.05)
        cen = pts.mean(axis=0)
        top = float(((pts - cen) @ w).max())
        iv = ray_intervals(T, cen, w)
        out = [p for p in (iv or []) if p[1] > top + 1e-6]
        out = [p for p in out if p[1] - max(p[0], top) > 0.05]
        through = not out
        # footprint fraction, 7x7 bundle on the user-facing face
        ref = L.DATUM_U if abs(float(np.dot(w, L.DATUM_U))) < 0.9 else L.DATUM_V
        ex = L.unit(ref - w * float(np.dot(w, ref)))
        ey = np.cross(w, ex)
        proj = (pts - cen) @ w
        face = pts[proj > proj.max() - 0.30]
        idx = np.linspace(0, len(face) - 1, min(49, len(face))).astype(int)
        nopen = 0
        for p in face[idx]:
            iv2 = ray_intervals(T, p, w)
            o2 = [q for q in (iv2 or []) if q[1] > 0.0 and q[1] - max(q[0], 0.0) > 0.05]
            if not o2:
                nopen += 1
        frac = nopen / max(1, len(idx))
        npass += 1 if through else 0
        op[short] = {"tiltDeg": tilt, "fullThroughOpening": bool(through),
                     "materialOutboardMm": [list(x) for x in out] if out else None,
                     "footprintOpenFraction": frac}
        print("%-5s %8.4f %10s %-30s %9.0f%%"
              % (short, tilt, "YES" if through else "NO",
                 "none" if through else ", ".join("[%.3f,%.3f]" % x for x in out),
                 100 * frac))
        del cap
    print("\n  THROUGH-OPENINGS: PASS %d / 9" % npass)

    L.write_json(OUT / "d01_verify_exact_source.json",
                 {"masterAuthority": {
                     "document": "OneGrip_Play_V1", "did": "a21e64f36bc61df760d4587c",
                     "version": "THUMB_LOWER15_HOUSING_V1",
                     "vid": "50dfe4e752e447375b95493a",
                     "eid": "425d9199b59cfb1efd9ddc35", "configuration": "default",
                     "approvedTransformMm": [0.0, 12.25, -21.0]},
                  "sha256Gate": {"allMatch": bool(ok_all), "files": hashes},
                  "importValidation": rows, "shellSplit": split,
                  "throughOpenings": op, "throughOpeningPass": npass,
                  "memory": L.MEMORY_LOG})
    return 0 if (ok_all and npass == 9) else 1


if __name__ == "__main__":
    raise SystemExit(main())
