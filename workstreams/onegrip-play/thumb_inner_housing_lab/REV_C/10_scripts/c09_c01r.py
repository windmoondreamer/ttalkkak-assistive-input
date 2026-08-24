"""C09 - C01R_RECONCILED_SOURCE_FAITHFUL (REV_C sections 10, 11, 12).

C01 is NOT modified; this is a new candidate built against the reconciled shell.

Changes vs C01, each for a stated reason:
  * conformal band unchanged in principle (one swept plate, ~1.2 mm standoff)
  * PLAN TRIM: the boundary is cut back to where the plate is at least 1.60 mm
    thick, removing C01's ~80 mm2 of 0.00-0.01 mm knife edge (section 12)
  * LOAD-TRANSFER PADS: intentional local pads at the two perimeter zones where
    the ORIGINAL Backplate actually landed on the shell (C08: 72.50 mm2 at
    u[-20,-11.5] v[-49,-32] and 23.75 mm2 at u[12.5,19] v[-49,-44]), rather
    than pressing the whole plate against the shell (section 11)
  * apertures taken from the RECONCILED opening prisms
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import (Align, Location, Plane, Polyline, Vector, export_step,
                       export_stl, extrude, import_step, make_face)
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, true_axis  # noqa: E402
from c03_reconcile import prism  # noqa: E402
from c04_validate import RECON  # noqa: E402
from c07_docs71_and_c01 import Field  # noqa: E402

OUT = L.LAB / "07_c01r"
CONFORMAL_GAP = 1.20
SKIN_DEPTH_N = 2.40
MIN_STRUCTURAL_WALL = 1.60      # section 12 preferred minimum
APERTURE_EXTRA = 0.40           # plate aperture beyond the shell opening
KEEPOUT_CLEARANCE = 0.50
SCREW_CLEARANCE = 1.00
PAD_GAP = 0.10                  # designed contact standoff at a load pad
BLANK_LO = (-21.0, -50.0, 2.0)
BLANK_HI = (21.0, 15.0, 18.0)
# Pad centres are the ORIGINAL Backplate contact-zone centroids (C08).
# Radii are chosen to reproduce the original zone areas (72.50 / 23.75 mm2).
PADS = [{"name": "PAD_LEFT_PERIMETER", "centre": (-15.75, -40.5), "radius": 4.80},
        {"name": "PAD_RIGHT_PERIMETER", "centre": (15.75, -46.5), "radius": 2.75}]
PITCH = 0.25


def shifted(shell, d):
    v = -(-L.DATUM_N) * d
    return shell.moved(Location(Vector(*[float(x) for x in v])))


def star_polygon(mask, U, V, n_ang=192, shrink=0.15):
    """Outer boundary of a star-shaped raster region, as a polygon."""
    iu, iv = np.nonzero(mask)
    cu, cv = float(U[iu].mean()), float(V[iv].mean())
    pts = []
    for a in np.linspace(0, 2 * np.pi, n_ang, endpoint=False):
        dx, dy = np.cos(a), np.sin(a)
        r_ok = 0.0
        r = 0.0
        while r < 60.0:
            r += PITCH
            u, v = cu + dx * r, cv + dy * r
            i = int(round((u - U[0]) / (U[1] - U[0])))
            j = int(round((v - V[0]) / (V[1] - V[0])))
            if not (0 <= i < len(U) and 0 <= j < len(V)) or not mask[i, j]:
                break
            r_ok = r
        pts.append((cu + dx * max(0.0, r_ok - shrink), cv + dy * max(0.0, r_ok - shrink)))
    return np.asarray(pts, float)


def local_prism(poly_uv, n0, n1, label):
    pl = L.local_plane((0.0, 0.0, n0))
    pts = [(float(p[1]), float(p[0])) for p in poly_uv]      # plane axes are (v, u)
    solid = extrude(pl * make_face(Polyline(*pts, close=True)), amount=float(n1 - n0))
    solid.label = label
    return solid


def thickness_map(solid, U, V):
    f = Field(L.local_triangles(solid, tol=0.05, ang=0.10))
    t = np.zeros((len(U), len(V)))
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            h = f.hits(u, v)
            if h.size and h.size % 2 == 0:
                t[i, j] = float(sum(h[k + 1] - h[k] for k in range(0, h.size, 2)))
    return t


def main() -> int:
    stage = int(sys.argv[sys.argv.index("--stage") + 1]) if "--stage" in sys.argv else 99
    rec = import_step(str(RECON))
    rec, _ = L.as_single_solid(rec, "RECONCILED")
    print("reconciled shell: vol=%.3f faces=%d" % (L.vol(rec), len(list(rec.faces()))))

    # ---- 1 : conformal band ---------------------------------------------
    # The band is built from the FROZEN shell, not the reconciled one.  Building
    # it from the reconciled shell was tried first and the difference of the two
    # translated copies SILENTLY FAILED along the plate edges: it returned
    # shifted(gap+t) unchanged, so the plate came out 3.29 mm thick with a
    # 0.30 mm gap instead of 2.40 mm at 1.20 mm.  The two shells are identical
    # outside the openings, and the plate has apertures at every opening, so the
    # frozen shell is the correct and better-conditioned source here.
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    src = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    band = (shifted(src, CONFORMAL_GAP + SKIN_DEPTH_N) - shifted(src, CONFORMAL_GAP)).clean()
    blank = L.local_box(BLANK_LO, BLANK_HI, "BLANK")
    sel = (band & blank).clean()
    keep = [s for s in sel.solids() if float(s.volume) > 20.0]
    plate, _ = L.as_single_solid(
        __import__("build123d").Compound(children=keep, label="P"), "C01R")
    print("stage 1 conformal band: vol=%.3f pieces=%d" % (L.vol(plate), len(keep)))
    del band, sel
    L.memory("band")
    if stage < 2:
        return 0

    # ---- 2 : plan trim to >= MIN_STRUCTURAL_WALL -------------------------
    U = np.arange(BLANK_LO[0], BLANK_HI[0] + 1e-9, PITCH)
    V = np.arange(BLANK_LO[1], BLANK_HI[1] + 1e-9, PITCH)
    t0 = thickness_map(plate, U, V)
    thick_ok = t0 >= MIN_STRUCTURAL_WALL
    lab, n = ndimage.label(thick_ok)
    if n:
        sizes = ndimage.sum(thick_ok, lab, range(1, n + 1))
        thick_ok = lab == (int(np.argmax(sizes)) + 1)
    thick_ok = ndimage.binary_fill_holes(thick_ok)
    poly = star_polygon(thick_ok, U, V)
    trim = local_prism(poly, BLANK_LO[2] - 2.0, BLANK_HI[2] + 2.0, "PLAN_TRIM")
    plate = (plate & trim).clean()
    plate, _ = L.as_single_solid(plate, "C01R")
    print("stage 2 plan trim: vol=%.3f  (C01 knife edge removed)" % L.vol(plate))
    L.memory("trim")
    if stage < 3:
        return 0

    # ---- 3 : load-transfer pads ------------------------------------------
    # The ORIGINAL contact zones sit at v = -49 .. -32; the trimmed plate only
    # reaches v ~ -37 on the right, so a pad at the original right centroid
    # lands on nothing (verified: 0 mm3).  Pad centres are therefore snapped to
    # the nearest position that is INSIDE the trimmed plate and at least
    # PAD_EDGE_MARGIN from its boundary, keeping the original intent (perimeter,
    # -v end, one left one right) and reporting the shift.
    PAD_EDGE_MARGIN = 1.5
    t_now = thickness_map(plate, U, V)
    pmask = t_now > 1e-6
    _pp = np.pad(pmask, 1, mode="constant", constant_values=False)
    edist = ndimage.distance_transform_edt(_pp, sampling=PITCH)[1:-1, 1:-1]

    def snap(cu, cv, r):
        ok = pmask & (edist >= r + PAD_EDGE_MARGIN) & (V[None, :] < -25.0)
        ok = ok & ((U[:, None] < 0) if cu < 0 else (U[:, None] > 0))
        if not ok.any():
            return None
        iu, iv = np.nonzero(ok)
        d = np.hypot(U[iu] - cu, V[iv] - cv)
        k = int(np.argmin(d))
        return float(U[iu[k]]), float(V[iv[k]]), float(d[k])

    pad_solids = []
    pad_rows = []
    pad_band = (shifted(src, CONFORMAL_GAP) - shifted(src, PAD_GAP)).clean()
    for p in PADS:
        cu0, cv0 = p["centre"]
        r = p["radius"]
        sn = snap(cu0, cv0, r)
        if sn is None:
            print("   %s : no valid position inside the trimmed plate" % p["name"])
            continue
        cu, cv, shift = sn
        p = dict(p)
        p["snappedCentre"] = [cu, cv]
        p["snapShiftMm"] = shift
        disc = np.stack([[cu + r * np.cos(a), cv + r * np.sin(a)]
                         for a in np.linspace(0, 2 * np.pi, 40, endpoint=False)])
        fp = local_prism(disc, BLANK_LO[2] - 2.0, BLANK_HI[2] + 2.0, p["name"])
        piece = (pad_band & fp & trim).clean()
        sol = [s for s in piece.solids() if float(s.volume) > 1.0]
        if not sol:
            print("   %s : no material" % p["name"])
            continue
        pad, _ = L.as_single_solid(
            __import__("build123d").Compound(children=sol, label="pp"), p["name"])
        pad_solids.append(pad)
        pad_rows.append({"name": p["name"], "originalZoneCentroidUV": list(p["centre"]),
                         "snappedCentreUV": p["snappedCentre"],
                         "snapShiftMm": p["snapShiftMm"], "radiusMm": p["radius"],
                         "volumeMm3": L.vol(pad), "designedGapMm": PAD_GAP})
        print("   %-20s centre (%6.2f,%7.2f) -> (%6.2f,%7.2f)  shift %5.2f mm  vol=%7.3f mm3"
              % (p["name"], p["centre"][0], p["centre"][1], p["snappedCentre"][0],
                 p["snappedCentre"][1], p["snapShiftMm"], L.vol(pad)))
    for pad in pad_solids:
        plate = (plate + pad).clean()
    plate, npc = L.as_single_solid(plate, "C01R")
    print("stage 3 with pads: vol=%.3f solids=%d" % (L.vol(plate), len(list(plate.solids()))))
    del pad_band
    L.memory("pads")
    if stage < 4:
        return 0

    # ---- 4 : apertures from the reconciled openings ----------------------
    cutters = json.loads((L.LAB / "03_reconciled" / "c03_reconcile.json")
                         .read_text(encoding="utf-8"))["cutters"]
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    ap_rows = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, _ = true_axis(cap)
        pts = L.surf_points(cap, 30000, tol=0.05)
        cen = pts.mean(axis=0)
        ref = L.DATUM_U if abs(float(np.dot(w, L.DATUM_U))) < 0.9 else L.DATUM_V
        ex = L.unit(ref - w * float(np.dot(w, ref)))
        ey = np.cross(w, ex)
        pg = np.asarray(cutters[short]["polygonVertices"], float)
        c = pg.mean(axis=0)
        pg = c + (pg - c) * (1.0 + APERTURE_EXTRA / max(1e-6, np.abs(pg - c).mean()))
        tool = prism(pg, cen, ex, ey, w, -8.0, 20.0, "AP_" + short)
        iv = L.inter_vol(plate, tool)
        if iv > 1.0e-9:
            plate = (plate - tool).clean()
            plate, _ = L.as_single_solid(plate, "C01R")
        ap_rows[short] = {"removedMm3": iv}
        print("   aperture %-5s removed %9.4f mm3" % (short, iv))
        del cap
    L.memory("apertures")
    if stage < 5:
        return 0

    # ---- 5 : keep-outs ----------------------------------------------------
    keepc = import_step(str(L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    ko = {}
    for child in list(getattr(keepc, "children", []) or []):
        lab2 = str(child.label)
        if not child.solids() or lab2.startswith("CAP_"):
            continue
        s, _ = L.as_single_solid(child, lab2)
        clr = SCREW_CLEARANCE if "SCREW" in lab2.upper() else KEEPOUT_CLEARANCE
        removed = 0.0
        for d in (np.zeros(3), L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V,
                  -L.DATUM_N, L.DATUM_N):
            v = d * clr
            tool = s if not np.any(v) else s.moved(Location(Vector(*[float(x) for x in v])))
            iv = L.inter_vol(plate, tool)
            if iv > 1.0e-9:
                removed += iv
                plate = (plate - tool).clean()
                plate, _ = L.as_single_solid(plate, "C01R")
        ko[lab2] = removed
        if removed > 1.0e-9:
            print("   keep-out %-32s removed %9.4f mm3" % (lab2[:32], removed))
    # Guard: the pad band boolean can overshoot, leaving the pad closer to the
    # wall than PAD_GAP (measured 7.067 mm3 of interference on the first try).
    # Subtracting the shell shifted inward by PAD_GAP makes the designed contact
    # standoff exact by construction rather than by hope.
    # Subtracting only the n-shifted copy leaves ~0.77 mm3 of overlap where the
    # wall normal is oblique to n, so the shell is also subtracted shifted in
    # +-u and +-v.  That enforces the designed 0.10 mm standoff in every
    # direction, not just along the sampling axis.
    before_guard = L.vol(plate)
    for d in (np.zeros(3), L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V):
        tool = shifted(src, PAD_GAP)
        if np.any(d):
            v = d * PAD_GAP
            tool = tool.moved(Location(Vector(*[float(x) for x in v])))
        plate = (plate - tool).clean()
        plate, _ = L.as_single_solid(plate, "C01R")
    print("   pad-gap guard removed %.4f mm3" % (before_guard - L.vol(plate)))

    # drop trim debris: the plan trim leaves a couple of sub-0.1 mm3 chips on
    # the boundary.  They are not structure and would not print.
    sl = sorted(plate.solids(), key=lambda x: -float(x.volume))
    debris = [float(x.volume) for x in sl[1:]]
    if debris:
        print("   dropped %d trim chips: %s mm3"
              % (len(debris), ", ".join("%.4f" % d for d in debris)))
    plate = sl[0]
    plate.label = "C01R_RECONCILED_SOURCE_FAITHFUL"
    L.memory("keepouts")

    print("\nC01R final: vol=%.3f faces=%d solids=%d"
          % (L.vol(plate), len(list(plate.faces())), len(list(plate.solids()))))
    export_step(plate, str(OUT / "C01R_RECONCILED_SOURCE_FAITHFUL.step"))
    export_stl(plate, str(OUT / "C01R_RECONCILED_SOURCE_FAITHFUL.stl"),
               tolerance=0.03, angular_tolerance=0.10)
    L.write_json(OUT / "c09_c01r_build.json",
                 {"conformalGapMm": CONFORMAL_GAP, "skinDepthAlongNMm": SKIN_DEPTH_N,
                  "minStructuralWallMm": MIN_STRUCTURAL_WALL,
                  "padDesignedGapMm": PAD_GAP, "pads": pad_rows,
                  "apertures": ap_rows, "keepOutsRemovedMm3": ko,
                  "volumeMm3": L.vol(plate), "faces": len(list(plate.faces())),
                  "solids": len(list(plate.solids())),
                  "droppedTrimChipsMm3": debris,
                  "planTrimPolygonUV": poly.tolist(),
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
