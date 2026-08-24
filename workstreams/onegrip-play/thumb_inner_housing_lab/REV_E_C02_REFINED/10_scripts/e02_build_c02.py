"""E02 - C02_C01_EXACT_REFINED.

C01 architecture, unchanged in principle: one conformal swept plate against the
EXACT APPROVED shell.  Two targeted corrections only.

DEFECT 1  plan-boundary knife edge
    The band is cut by translating the shell along n, so a skin of depth t along
    n is only t*|m.n| thick along its own normal.  E01 measured |m.n| down to
    0.14 at the plate rim, which is where C01's 0.0004 mm edge comes from.
    Fix: build with a deeper skin (SKIN_DEPTH_N) and then TRIM the plan to the
    region where the NORMAL thickness is at least MIN_STRUCTURAL_WALL.

DEFECT 2  load-transfer area
    Raise the plate's outer face to PAD_GAP inside the two ORIGINAL perimeter
    zones.  The zones are used at their measured coordinates; nothing is shifted
    inward.  E01 confirmed the plate plan already spans both footprints (it just
    covers 27 % / 9 % of them at 1.19 mm standoff).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from build123d import (Compound, Location, Polyline, Vector, export_step,
                       export_stl, extrude, import_step, make_face)
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import true_axis  # noqa: E402
from d02_housing_vs_exact import Field, approved_shell  # noqa: E402
from e01_probe import ZONES  # noqa: E402

OUT = L.LAB / "02_candidate"
OUTWARD = -L.DATUM_N
KEEPOUTS = L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"

CONFORMAL_GAP = 1.20
SKIN_DEPTH_N = 2.60          # -> 1.60 mm normal thickness down to |m.n| = 0.615
MIN_STRUCTURAL_WALL = 1.60
PAD_GAP = 0.10
APERTURE_CLEARANCE = 0.60
KEEPOUT_CLEARANCE = 0.50
SCREW_CLEARANCE = 1.00
HARNESS_INSERTION_MM = 15.0  # PROVISIONAL rear corridor for the four-edge harness
BLANK_LO = (-21.5, -50.5, 1.5)
BLANK_HI = (21.5, 15.0, 19.0)
PITCH = 0.25


def shifted(shell, d):
    return shell.moved(Location(Vector(*[float(x) for x in (L.DATUM_N * d)])))


def normal_thickness_map(solid, shell_cos, U, V):
    f = Field(L.local_triangles(solid, tol=0.05, ang=0.10))
    t = np.zeros((len(U), len(V)))
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            h = f.hits(u, v)
            if h.size and h.size % 2 == 0:
                t[i, j] = float(sum(h[k + 1] - h[k] for k in range(0, h.size, 2)))
    return t, t * np.nan_to_num(shell_cos, nan=1.0)


def star_polygon(mask, U, V, n_ang=256, shrink=0.15):
    iu, iv = np.nonzero(mask)
    cu, cv = float(U[iu].mean()), float(V[iv].mean())
    pts = []
    for a in np.linspace(0, 2 * np.pi, n_ang, endpoint=False):
        dx, dy = np.cos(a), np.sin(a)
        r_ok, r = 0.0, 0.0
        while r < 70.0:
            r += PITCH
            i = int(round((cu + dx * r - U[0]) / (U[1] - U[0])))
            j = int(round((cv + dy * r - V[0]) / (V[1] - V[0])))
            if not (0 <= i < len(U) and 0 <= j < len(V)) or not mask[i, j]:
                break
            r_ok = r
        pts.append((cu + dx * max(0.0, r_ok - shrink), cv + dy * max(0.0, r_ok - shrink)))
    return np.asarray(pts, float)


def local_prism(poly_uv, n0, n1, label):
    pl = L.local_plane((0.0, 0.0, n0))
    pts = [(float(p[1]), float(p[0])) for p in poly_uv]      # plane axes are (v, u)
    s = extrude(pl * make_face(Polyline(*pts, close=True)), amount=float(n1 - n0))
    s.label = label
    return s


def axis_prism(cap, axis, grow, length, label):
    pts = L.surf_points(cap, 30000, tol=0.06)
    c = pts.mean(axis=0)
    ref = L.DATUM_U if abs(float(np.dot(axis, L.DATUM_U))) < 0.9 else L.DATUM_V
    ex = L.unit(ref - axis * float(np.dot(axis, ref)))
    ey = np.cross(axis, ex)
    d = pts - c
    a, b = d @ ex, d @ ey
    from build123d import Align, Box, Plane
    pl = Plane(origin=L.xyz(c - axis * (length * 0.5)), x_dir=L.xyz(ex), z_dir=L.xyz(axis))
    box = pl * Box(float(a.max() - a.min()) + 2 * grow,
                   float(b.max() - b.min()) + 2 * grow, length,
                   align=(Align.CENTER, Align.CENTER, Align.MIN))
    box = box.moved(Location(Vector(*[float(x) for x in
                                      (ex * (a.max() + a.min()) * 0.5
                                       + ey * (b.max() + b.min()) * 0.5)])))
    box.label = label
    return box


def main() -> int:
    stage = int(sys.argv[sys.argv.index("--stage") + 1]) if "--stage" in sys.argv else 99
    approved = approved_shell()
    print("exact approved shell: vol=%.3f faces=%d"
          % (L.vol(approved), len(list(approved.faces()))))
    z = np.load(L.LAB / "01_probe" / "e01_maps.npz")
    Uc, Vc, cos = z["U"], z["V"], z["cos"]

    # ---- 1 : conformal band ---------------------------------------------
    band = (shifted(approved, CONFORMAL_GAP + SKIN_DEPTH_N)
            - shifted(approved, CONFORMAL_GAP)).clean()
    blank = L.local_box(BLANK_LO, BLANK_HI, "BLANK")
    sel = (band & blank).clean()
    keep = [s for s in sel.solids() if float(s.volume) > 20.0]
    plate, _ = L.as_single_solid(Compound(children=keep, label="P"), "C02")
    print("stage 1 band: vol=%.3f pieces=%d" % (L.vol(plate), len(keep)))
    del band, sel
    L.memory("band")
    if stage < 2:
        return 0

    U = np.arange(BLANK_LO[0], BLANK_HI[0] + 1e-9, PITCH)
    V = np.arange(BLANK_LO[1], BLANK_HI[1] + 1e-9, PITCH)
    cosr = np.full((len(U), len(V)), np.nan)
    for i, u in enumerate(U):
        ii = int(round((u - Uc[0]) / (Uc[1] - Uc[0])))
        for j, v in enumerate(V):
            jj = int(round((v - Vc[0]) / (Vc[1] - Vc[0])))
            if 0 <= ii < len(Uc) and 0 <= jj < len(Vc):
                cosr[i, j] = cos[ii, jj]

    tn, tnorm = normal_thickness_map(plate, cosr, U, V)
    print("  along-n thickness p50 = %.3f   normal thickness p50 = %.3f mm"
          % (float(np.median(tn[tn > 0])), float(np.median(tnorm[tn > 0]))))
    if float(np.median(tn[tn > 0])) < SKIN_DEPTH_N - 0.25:
        raise RuntimeError("band boolean under-delivered: median along-n thickness "
                           "%.3f vs requested %.3f" % (float(np.median(tn[tn > 0])),
                                                       SKIN_DEPTH_N))

    # ---- 2 : plan trim on NORMAL thickness ------------------------------
    ok = tnorm >= MIN_STRUCTURAL_WALL
    lab, n = ndimage.label(ok)
    if n:
        sizes = ndimage.sum(ok, lab, range(1, n + 1))
        ok = lab == (int(np.argmax(sizes)) + 1)
    ok = ndimage.binary_fill_holes(ok)
    poly = star_polygon(ok, U, V)
    trim = local_prism(poly, BLANK_LO[2] - 3.0, BLANK_HI[2] + 3.0, "PLAN_TRIM")
    # The star polygon is cast from the plan centroid, so it cannot represent a
    # non-star outline.  Measured: it excluded BOTH perimeter load zones even
    # though the >=1.60 mask is a single connected component that contains them.
    # The two zone footprints are therefore unioned back in explicitly, and the
    # sub-minimum material inside them is removed afterwards by run-length
    # prisms rather than by the polygon.
    for name, zn in ZONES.items():
        trim = (trim + L.local_box((zn["u"][0], zn["v"][0], BLANK_LO[2] - 3.0),
                                   (zn["u"][1], zn["v"][1], BLANK_HI[2] + 3.0),
                                   "TRIM_KEEP_" + name)).clean()
    trim, _ = L.as_single_solid(trim, "PLAN_TRIM")
    plate = (plate & trim).clean()
    plate, _ = L.as_single_solid(plate, "C02")
    # remove sub-minimum material inside the re-added zone footprints
    tn2, tnorm2 = normal_thickness_map(plate, cosr, U, V)
    bad = (tn2 > 1e-6) & (tnorm2 < 1.20)
    zone_mask = np.zeros_like(bad)
    for name, zn in ZONES.items():
        zone_mask |= ((U[:, None] >= zn["u"][0]) & (U[:, None] <= zn["u"][1]) &
                      (V[None, :] >= zn["v"][0]) & (V[None, :] <= zn["v"][1]))
    bad &= zone_mask
    nrun = 0
    for i, u in enumerate(U):
        col = bad[i]
        if not col.any():
            continue
        j = 0
        while j < len(V):
            if col[j]:
                k = j
                while k + 1 < len(V) and col[k + 1]:
                    k += 1
                tool = L.local_box((u - PITCH / 2, V[j] - PITCH / 2, BLANK_LO[2] - 3.0),
                                   (u + PITCH / 2, V[k] + PITCH / 2, BLANK_HI[2] + 3.0),
                                   "THIN_CUT")
                if L.inter_vol(plate, tool) > 1e-9:
                    plate = (plate - tool).clean()
                    plate, _ = L.as_single_solid(plate, "C02")
                nrun += 1
                j = k + 1
            else:
                j += 1
    print("stage 2 plan trim: vol=%.3f  (%d sub-1.20 runs removed in the zones)"
          % (L.vol(plate), nrun))
    L.memory("trim")
    if stage < 3:
        return 0

    # ---- 3 : load-transfer pads at the ORIGINAL zone coordinates --------
    pad_band = (shifted(approved, CONFORMAL_GAP) - shifted(approved, PAD_GAP)).clean()
    pads, pad_rows = [], []
    for name, zn in ZONES.items():
        fp = L.local_box((zn["u"][0], zn["v"][0], BLANK_LO[2] - 3.0),
                         (zn["u"][1], zn["v"][1], BLANK_HI[2] + 3.0), "PAD_" + name)
        piece = (pad_band & fp & trim).clean()
        sol = [s for s in piece.solids() if float(s.volume) > 0.5]
        if not sol:
            print("   PAD_%s : no material" % name)
            continue
        pad, _ = L.as_single_solid(Compound(children=sol, label="pp"), "PAD_" + name)
        pads.append(pad)
        pad_rows.append({"name": "PAD_" + name, "u": list(zn["u"]), "v": list(zn["v"]),
                         "volumeMm3": L.vol(pad), "designedGapMm": PAD_GAP,
                         "originalTargetMm2": zn["targetMm2"],
                         "shiftedFromOriginal": False})
        print("   PAD_%-6s u[%6.1f,%6.1f] v[%6.1f,%6.1f]  vol=%8.3f mm3  (no inward shift)"
              % (name, zn["u"][0], zn["u"][1], zn["v"][0], zn["v"][1], L.vol(pad)))
    for p in pads:
        plate = (plate + p).clean()
    plate, _ = L.as_single_solid(plate, "C02")
    print("stage 3 with pads: vol=%.3f solids=%d" % (L.vol(plate), len(list(plate.solids()))))
    del pad_band
    L.memory("pads")
    if stage < 4:
        return 0

    # ---- 4 : control apertures ------------------------------------------
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    ap = {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, _ = true_axis(cap)
        tool = axis_prism(cap, w, APERTURE_CLEARANCE, 60.0, "AP_" + short)
        iv = L.inter_vol(plate, tool)
        if iv > 1.0e-9:
            plate = (plate - tool).clean()
            plate, _ = L.as_single_solid(plate, "C02")
        ap[short] = iv
        print("   aperture %-5s removed %9.4f mm3" % (short, iv))
        del cap
    L.memory("apertures")
    if stage < 5:
        return 0

    # ---- 5 : keep-outs, incl. the PROVISIONAL rear harness corridor -----
    keepc = import_step(str(KEEPOUTS))
    ko = {}
    for child in list(getattr(keepc, "children", []) or []):
        lab2 = str(child.label)
        if not child.solids() or lab2.startswith("CAP_"):
            continue
        s, _ = L.as_single_solid(child, lab2)
        clr = SCREW_CLEARANCE if "SCREW" in lab2.upper() else KEEPOUT_CLEARANCE
        removed = 0.0
        tools = []
        for d in (np.zeros(3), L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V,
                  -L.DATUM_N, L.DATUM_N):
            v = d * clr
            tools.append(s if not np.any(v) else
                         s.moved(Location(Vector(*[float(x) for x in v]))))
        if "N1_N2" in lab2.upper() or "CARRIER" in lab2.upper():
            # rear insertion corridor: sweep the carrier inward along -n.
            # PROVISIONAL coordination envelope for the four-edge-leg harness.
            for k in range(1, int(HARNESS_INSERTION_MM) + 1):
                tools.append(s.moved(Location(Vector(
                    *[float(x) for x in (L.DATUM_N * float(k))]))))
        for tool in tools:
            iv = L.inter_vol(plate, tool)
            if iv > 1.0e-9:
                removed += iv
                plate = (plate - tool).clean()
                plate, _ = L.as_single_solid(plate, "C02")
        ko[lab2] = removed
        if removed > 1.0e-9:
            print("   keep-out %-34s removed %9.4f mm3" % (lab2[:34], removed))
        del s

    # ---- guard: enforce the designed standoff in every direction --------
    before = L.vol(plate)
    for d in (np.zeros(3), L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V):
        tool = shifted(approved, PAD_GAP)
        if np.any(d):
            tool = tool.moved(Location(Vector(*[float(x) for x in (d * PAD_GAP)])))
        plate = (plate - tool).clean()
        plate, _ = L.as_single_solid(plate, "C02")
    print("   standoff guard removed %.4f mm3" % (before - L.vol(plate)))

    sl = sorted(plate.solids(), key=lambda x: -float(x.volume))
    debris = [float(x.volume) for x in sl[1:]]
    if debris:
        print("   dropped %d chips: %s mm3" % (len(debris), ", ".join("%.4f" % d for d in debris)))
    plate = sl[0]
    plate.label = "C02_C01_EXACT_REFINED"

    print("\nC02 final: vol=%.3f faces=%d solids=%d"
          % (L.vol(plate), len(list(plate.faces())), len(list(plate.solids()))))
    export_step(plate, str(OUT / "C02_C01_EXACT_REFINED.step"))
    export_stl(plate, str(OUT / "C02_C01_EXACT_REFINED.stl"),
               tolerance=0.03, angular_tolerance=0.10)
    L.write_json(OUT / "e02_build.json",
                 {"conformalGapMm": CONFORMAL_GAP, "skinDepthAlongNMm": SKIN_DEPTH_N,
                  "minStructuralWallMm": MIN_STRUCTURAL_WALL, "padGapMm": PAD_GAP,
                  "harnessInsertionCorridorMm": HARNESS_INSERTION_MM,
                  "pads": pad_rows, "apertures": ap, "keepOuts": ko,
                  "droppedChipsMm3": debris,
                  "volumeMm3": L.vol(plate), "faces": len(list(plate.faces())),
                  "solids": len(list(plate.solids())),
                  "planTrimPolygonUV": poly.tolist(), "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
