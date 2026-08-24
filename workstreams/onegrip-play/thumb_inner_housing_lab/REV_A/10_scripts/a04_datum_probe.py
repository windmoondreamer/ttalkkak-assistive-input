"""A04 - is DATUM_P (used by docs/71 and the docs/72 fixture) the ORIGINAL or
the LOWERED joystick centre, and where are the shell surfaces along that axis?

Also measures, for each shell, the inner/outer surface crossings on a ray
family around the joystick axis, which is the raw material for the conformal
inner-surface work later.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402

OUT = L.LAB / "01_source_map"
CROP_LO = (-30.0, -36.0, -34.0)
CROP_HI = (30.0, 30.0, 14.0)


def leaf_parts(key: str) -> dict:
    root = import_step(L.SRC[key])
    parts = {}

    def walk(shape):
        kids = list(getattr(shape, "children", []) or [])
        if kids:
            for k in kids:
                walk(k)
            return
        if shape.solids():
            parts[str(shape.label)] = shape
    walk(root)
    return root, parts


def ray_hits(T: np.ndarray, u: float, v: float) -> np.ndarray:
    """All n-values where the column (u, v) crosses the triangle soup."""
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    e1, e2 = b - a, c - a
    det = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
    ok = np.abs(det) > 1.0e-14
    du = u - a[:, 0]
    dv = v - a[:, 1]
    s = np.where(ok, (du * e2[:, 1] - dv * e2[:, 0]) / np.where(ok, det, 1.0), -1.0)
    t = np.where(ok, (e1[:, 0] * dv - e1[:, 1] * du) / np.where(ok, det, 1.0), -1.0)
    good = ok & (s >= 0.0) & (t >= 0.0) & (s + t <= 1.0)
    if not good.any():
        return np.zeros(0)
    hits = np.sort(a[good, 2] + s[good] * e1[good, 2] + t[good] * e2[good, 2])
    keep = np.ones(hits.size, bool)
    keep[1:] = np.diff(hits) > 1.0e-7
    return hits[keep]


def main() -> int:
    print("DATUM_P (world) =", np.round(L.DATUM_P, 6))
    print("THUMB_DELTA     =", L.THUMB_DELTA)

    rows = {}
    for key, tag in (("ORIGINAL_THUMB_CARTRIDGE", "ORIGINAL"),
                     ("LOWERED_ORIGINAL_THUMB_CARTRIDGE", "LOWERED")):
        root, parts = leaf_parts(key)
        att = next(s for n, s in parts.items() if "ATTACHMENT" in n.upper())
        solid, _ = L.as_single_solid(att, "ATT")
        bb = solid.bounding_box()
        c = np.asarray([(bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2,
                        (bb.min.Z + bb.max.Z) / 2], float)
        lc = L.to_local(c)[0]
        d = float(np.linalg.norm(c - L.DATUM_P))
        rows[tag] = {"attachmentCentreWorld": c.tolist(), "attachmentCentreLocal": lc.tolist(),
                     "distanceToDatumPmm": d}
        print("%-9s attachment centre world=%s local(u,v,n)=%s  |centre-DATUM_P|=%.4f mm"
              % (tag, np.round(c, 4), np.round(lc, 4), d))
        del root, parts, att, solid
        L.memory("attachment " + tag)

    # --- shell surface crossings along the joystick axis and a small fan ----
    box = L.local_box(CROP_LO, CROP_HI, "CROP")
    probe = {}
    for tag, key in (("JAD_FROZEN", "JAD_LOWERED_THUMB"), ("JFD_FROZEN", "JFD_LOWERED_THUMB"),
                     ("JAD_FV2", "JAD_FINGER_V2"), ("JFD_FV2", "JFD_FINGER_V2")):
        full = L.load(key)
        sec, _ = L.as_single_solid((full & box).clean(), tag)
        # NOTE: do NOT filter out crop-box faces.  Dropping them opens the mesh
        # and destroys ray parity (odd crossing counts).  The crop solid is
        # closed; crossings near n=CROP_LO[2]/CROP_HI[2] are crop caps and are
        # reported as-is.
        Tin = L.local_triangles(sec, tol=0.12, ang=0.20)
        col = {}
        for (u, v) in [(0.0, 0.0), (6.0, 0.0), (-6.0, 0.0), (0.0, 6.0), (0.0, -6.0),
                       (12.0, 0.0), (-12.0, 0.0), (0.0, 12.0), (0.0, -12.0),
                       (0.0, -20.0), (0.0, -28.0), (0.0, 20.0)]:
            h = ray_hits(Tin, u, v)
            col["u%+05.1f_v%+05.1f" % (u, v)] = [round(float(x), 4) for x in h]
        probe[tag] = col
        print("\n%s  column crossings in n (material between alternate pairs):" % tag)
        for k in col:
            print("   %-16s %s" % (k, col[k]))
        del full, sec, Tin
        L.memory("probe " + tag)

    L.write_json(OUT / "a04_datum_probe.json",
                 {"attachment": rows, "shellColumns": probe, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
