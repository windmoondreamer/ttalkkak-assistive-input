"""C11 - REV_C renders (section 13).

Matched camera for APPROVED / OLD EXACT / RECONCILED, then axis sections through
JOY, T2, T4, T6, T7, T8 with all three walls overlaid, then the housing trio
ORIGINAL / C01 / C01R on the same section planes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
import labrender as R  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, ray_intervals, true_axis  # noqa: E402
from b07_lineage_and_visual import LOWER15_JAD, LOWER15_JFD, read_stl  # noqa: E402
from c04_validate import RECON  # noqa: E402

OUT = L.LAB / "08_renders"
OUTWARD = -L.DATUM_N
C_APPROVED = (146, 176, 128)
C_OLD = (128, 152, 172)
C_RECON = (196, 150, 96)
C_CAP = (56, 62, 72)
C_ORIGH = (232, 168, 74)
C_C01 = (86, 186, 132)
C_C01R = (96, 150, 226)
FOOT = "Thumb Inner Housing Lab REV_C | audit only | reconciled reference is LAB geometry, not production"
FIT_LOCAL = np.asarray([[a, b, c] for a in (-26.0, 26.0)
                        for b in (-52.0, 18.0) for c in (-20.0, 22.0)], float)


def main() -> int:
    # --from N : skip renders numbered below N.  The first full run exited 0
    # after 07_section_T6 without writing 08-12 and without an error, so the
    # remainder is produced by re-running from that point rather than by
    # repeating the eight minutes of work already done.
    start = int(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 0
    OUT.mkdir(parents=True, exist_ok=True)
    fit = L.from_local(FIT_LOCAL)
    box = L.local_box(CROP_LO, CROP_HI, "COMMON")

    old = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    Told = L.triangles(old, tol=0.08, ang=0.15)
    rec = import_step(str(RECON))
    rec, _ = L.as_single_solid(rec, "RECON")
    Trec = L.triangles(rec, tol=0.08, ang=0.15)
    T15 = np.concatenate([read_stl(LOWER15_JAD), read_stl(LOWER15_JFD)])
    l15 = L.to_local(T15.reshape(-1, 3)).reshape(-1, 3, 3)
    keep = ((np.abs(l15[:, :, 0]) < 30) & (l15[:, :, 1] > -54) & (l15[:, :, 1] < 24)
            & (np.abs(l15[:, :, 2]) < 60)).all(axis=1)
    T15c = T15[keep]
    L.memory("shells")

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    caps, axes, cens, tops = {}, {}, {}, {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        w, _, _ = true_axis(cap)
        pts = L.surf_points(cap, 30000, tol=0.05)
        cen = pts.mean(axis=0)
        caps[short] = L.triangles(cap, tol=0.05, ang=0.10)
        axes[short], cens[short] = w, cen
        tops[short] = float(((pts - cen) @ w).max())
        del cap
    Tcaps = np.concatenate([caps[s] for s in ORDER])

    # ---- 1..3 : matched camera -----------------------------------------
    cam = tuple(OUTWARD * -1.0)
    for name, T, col, title, sub in () if start > 3 else (
        ("01_APPROVED_LOWER15.png", T15c, C_APPROVED,
         "APPROVED  --  THUMB_LOWER15_HOUSING (opening-topology authority)",
         "9 of 9 controls open; mesh source, marked NON-EXACT"),
        ("02_OLD_EXACT_FROZEN_STEP.png", Told, C_OLD,
         "OLD EXACT  --  JAD/JFD_EXTERIOR_LOWERED_THUMB_V1",
         "T2 / T4 / T6 / T7 / T8 sealed or partial; outer skin correct to 0.09 mm"),
        ("03_RECONCILED_REFERENCE.png", Trec, C_RECON,
         "RECONCILED  --  FROZEN_THUMB_EXTERIOR_RECONCILED_REFERENCE  (LAB ONLY)",
         "9 of 9 through-openings recovered; material only removed, never added"),
    ):
        R.render(OUT / name, [(T, col, 1.0, title.split("  --  ")[0]),
                              (Tcaps, C_CAP, 1.0, "frozen Thumb caps")],
                 cam, L.DATUM_V, title, sub, FOOT, fit=fit)

    # ---- 4..9 : axis sections ------------------------------------------
    meta = json.loads((L.LAB / "04_validation" / "c05_validate2.json")
                      .read_text(encoding="utf-8"))["openings"]
    for idx, short in [x for x in (("04", "JOY"), ("05", "T2"), ("06", "T4"),
                                   ("07", "T6"), ("08", "T7"), ("09", "T8"))
                       if int(x[0]) >= start]:
        w, cen, top = axes[short], cens[short], tops[short]
        cut_n = np.cross(w, L.DATUM_U)
        if float(np.linalg.norm(cut_n)) < 0.2:
            cut_n = np.cross(w, L.DATUM_V)
        cut_n = L.unit(cut_n)
        ln = [(cen - w * 16.0, cen + w * 24.0, (226, 86, 86, 255), 3,
               "%s TRUE press axis" % short)]
        lb = [(cen + w * top, "cap outermost point", (20, 20, 20))]
        for tag, T, rgb in (("OLD EXACT", Told, (20, 90, 160)),
                            ("APPROVED", T15c, (30, 110, 40)),
                            ("RECONCILED", Trec, (150, 90, 20))):
            iv = ray_intervals(T, cen, w)
            out = [p for p in (iv or []) if p[1] > top]
            if out:
                s = max(out, key=lambda p: p[1] - p[0])
                lb.append((cen + w * s[0], "%s inner skin" % tag, rgb))
                lb.append((cen + w * s[1], "%s outer skin  wall %.3f mm" % (tag, s[1] - s[0]), rgb))
            else:
                lb.append((cen + w * (top + 5.0 + 2.0 * len(lb)),
                           "%s : OPEN" % tag, rgb))
        m = meta[short]
        sub = ("reconciled area %.2f mm2 vs approved %.2f  |  excess %.2f  deficit %.2f  "
               "|  ligament %s mm"
               % (m["reconciledAreaMm2"], m["approvedAreaMm2"], m["excessMm2"],
                  m["deficitMm2"],
                  ("%.3f" % m["minSurroundingLigamentMm"]) if m["minSurroundingLigamentMm"] else "n/a"))
        layers = [(R.clip_half(Told, cen, cut_n), C_OLD, 1.0, "old exact frozen STEP"),
                  (R.clip_half(T15c, cen, cut_n), C_APPROVED, 0.45, "approved LOWER15"),
                  (R.clip_half(Trec, cen, cut_n), C_RECON, 0.55, "reconciled reference"),
                  (R.clip_half(Tcaps, cen, cut_n), C_CAP, 1.0, "Thumb caps")]
        # ln / lb were built above but the first run never passed them, so the
        # sections rendered without the press axis or the skin callouts that
        # section 13 asks for.
        R.render(OUT / ("%s_section_%s.png" % (idx, short)),
                 [x for x in layers if len(x[0])], tuple(-cut_n), tuple(L.unit(w)),
                 "SECTION through %s on its TRUE press axis" % short, sub, FOOT,
                 fit=fit, world_lines=ln, world_labels=lb)
        L.memory("section " + short)

    if "--sections-only" in sys.argv:
        return 0

    # ---- 10..12 : housing trio -----------------------------------------
    dx = Location(Vector(*[float(x) for x in L.THUMB_DELTA]))
    bp = import_step(str(L.REV_A / "02_reference_copies" / "ORIGINAL_THUMB_BACKPLATE.step"))
    bp, _ = L.as_single_solid(bp, "BP")
    Tbp = L.triangles(bp.moved(dx), tol=0.06, ang=0.12)
    c01 = import_step(str(L.REV_A / "09_exports" / "C01_SOURCE_FAITHFUL_REBASE.step"))
    Tc01 = L.triangles(L.as_single_solid(c01, "C01")[0], tol=0.06, ang=0.12)
    c01r = import_step(str(L.LAB / "07_c01r" / "C01R_RECONCILED_SOURCE_FAITHFUL.step"))
    Tc01r = L.triangles(L.as_single_solid(c01r, "C01R")[0], tol=0.06, ang=0.12)

    cen = cens["T2"]
    cut_n = L.DATUM_V
    cam = tuple(-L.DATUM_V)
    for name, Th, col, title, sub in (
        ("10_housing_ORIGINAL.png", Tbp, C_ORIGH,
         "ORIGINAL inner housing (Backplate), translated for comparison",
         "gap median +1.292 mm, contact band 6.39 % of columns"),
        ("11_housing_C01.png", Tc01, C_C01,
         "C01_SOURCE_FAITHFUL_REBASE  (REV_A, unmodified)",
         "gap median +1.199 mm, contact 0.59 %, 100.12 mm2 below 1.20 mm"),
        ("12_housing_C01R.png", Tc01r, C_C01R,
         "C01R_RECONCILED_SOURCE_FAITHFUL  (REV_C)",
         "contact 3.53 % in two designed pads, 20.56 mm2 below 1.20 mm, interior thin 0.00"),
    ):
        R.render(OUT / name,
                 [(R.clip_half(Trec, cen, cut_n), C_RECON, 1.0, "reconciled shell"),
                  (R.clip_half(Th, cen, cut_n), col, 1.0, title.split("  (")[0])],
                 cam, OUTWARD, title, sub, FOOT, fit=fit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
