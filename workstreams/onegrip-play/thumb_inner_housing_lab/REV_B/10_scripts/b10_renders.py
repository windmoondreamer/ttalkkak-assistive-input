"""B10 - the seven required REV_B renders.

Axis sections show, for the same control, the EXACT frozen STEP beside the
LOWER15 housing (the geometry whose Thumb patch was grafted into the exterior
the user reviewed), with the press axis, the cap, and the material interval
drawn from the measured numbers rather than eyeballed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
import labrender as R  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, combined_shell, leaf_parts  # noqa: E402
from b03_axis_authority import CROP_LO, CROP_HI, ray_intervals, true_axis  # noqa: E402
from b07_lineage_and_visual import LOWER15_JAD, LOWER15_JFD, read_stl  # noqa: E402

OUT = L.LAB / "08_renders"
OUTWARD = -L.DATUM_N
C_SHELL = (128, 152, 172)
C_L15 = (146, 176, 128)
C_CAP = (56, 62, 72)
C_AXIS = (226, 86, 86, 255)

FIT_LOCAL = np.asarray([[a, b, c] for a in (-26.0, 26.0)
                        for b in (-52.0, 18.0) for c in (-20.0, 22.0)], float)


def font(sz):
    return R._font(sz)


def section_render(path, title, subtitle, layers, cut_normal, cut_point, cam, up,
                   world_lines, world_labels, fit):
    clipped = [(R.clip_half(T, cut_point, cut_normal), c, a, lab) for T, c, a, lab in layers]
    clipped = [x for x in clipped if len(x[0])]
    R.render(path, clipped, cam, up, title, subtitle,
             "Thumb Inner Housing Lab REV_B | audit only | no production geometry written",
             fit=fit, world_lines=world_lines, world_labels=world_labels)


def heatmap(path, U, V, Z, mask, title, subtitle, bands, colors, unit="mm"):
    W, H = 1500, 1000
    img = Image.new("RGB", (W, H), (250, 250, 250))
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 120, 110, W - 330, H - 90
    su = (x1 - x0) / (U[-1] - U[0])
    sv = (y1 - y0) / (V[-1] - V[0])
    cw = max(1, int(np.ceil((U[1] - U[0]) * su)))
    ch = max(1, int(np.ceil((V[1] - V[0]) * sv)))
    for i in range(len(U)):
        for j in range(len(V)):
            if not mask[i, j]:
                continue
            z = Z[i, j]
            col = colors[-1]
            for k, (lo, hi) in enumerate(bands):
                if lo <= z < hi:
                    col = colors[k]
                    break
            px = x0 + (U[i] - U[0]) * su
            py = y1 - (V[j] - V[0]) * sv
            d.rectangle([px, py, px + cw, py + ch], fill=col)
    d.rectangle([x0, y0, x1, y1], outline=(60, 60, 60))
    d.rectangle([0, 0, W, 78], fill=(24, 28, 34))
    d.text((18, 12), title, font=font(26), fill=(255, 255, 255))
    d.text((18, 46), subtitle, font=font(15), fill=(178, 190, 205))
    ly = y0
    for k, (lo, hi) in enumerate(bands):
        d.rectangle([x1 + 30, ly, x1 + 62, ly + 20], fill=colors[k], outline=(40, 40, 40))
        lab = ("%.2f - %s %s" % (lo, "inf" if hi > 1e8 else "%.2f" % hi, unit))
        d.text((x1 + 72, ly + 2), lab, font=font(15), fill=(28, 32, 38))
        ly += 28
    d.text((x0, y1 + 12), "u  %.0f .. %.0f mm   (horizontal)" % (U[0], U[-1]),
           font=font(14), fill=(60, 60, 60))
    d.text((x0, y1 + 32), "v  %.0f .. %.0f mm   (vertical, +v up)" % (V[0], V[-1]),
           font=font(14), fill=(60, 60, 60))
    d.rectangle([0, H - 42, W, H], fill=(24, 28, 34))
    d.text((18, H - 34), "Thumb Inner Housing Lab REV_B | audit only | C01 read-only from REV_A",
           font=font(14), fill=(178, 190, 205))
    img.save(path)
    print("  render -> %s" % path.name)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fit = L.from_local(FIT_LOCAL)

    box = L.local_box(CROP_LO, CROP_HI, "COMMON")
    frozen = combined_shell("JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB", box, "FROZEN")
    Tex = L.triangles(frozen, tol=0.08, ang=0.15)
    T15 = np.concatenate([read_stl(LOWER15_JAD), read_stl(LOWER15_JFD)])
    l15 = L.to_local(T15.reshape(-1, 3)).reshape(-1, 3, 3)
    keep = ((np.abs(l15[:, :, 0]) < 30) & (l15[:, :, 1] > -54) & (l15[:, :, 1] < 24)
            & (np.abs(l15[:, :, 2]) < 60)).all(axis=1)
    T15c = T15[keep]
    print("LOWER15 triangles in the Thumb window: %d of %d" % (len(T15c), len(T15)))
    L.memory("shells")

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    caps, axes, cens, tops = {}, {}, {}, {}
    for short in ORDER:
        label = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[label], short)
        ax, _, _ = true_axis(cap)
        pts = L.surf_points(cap, 30000, tol=0.05)
        cen = pts.mean(axis=0)
        caps[short] = L.triangles(cap, tol=0.05, ang=0.10)
        axes[short], cens[short] = ax, cen
        tops[short] = float(((pts - cen) @ ax).max())
        del cap
    Tcaps = np.concatenate([caps[s] for s in ORDER])

    # ---- 1 : exterior with all 9 control axes ---------------------------
    lines, labels = [], []
    for short in ORDER:
        p0 = cens[short]
        p1 = cens[short] + axes[short] * 26.0
        lines.append((p0, p1, C_AXIS, 3, short))
        labels.append((p0, short, (30, 40, 60)))
    R.render(OUT / "01_frozen_exterior_with_axes.png",
             [(Tex, C_SHELL, 1.0, "frozen exterior (exact STEP)"),
              (Tcaps, C_CAP, 1.0, "frozen Thumb control caps")],
             tuple(OUTWARD * -1.0), L.DATUM_V,
             "FROZEN EXTERIOR with all nine TRUE control axes",
             "axes are each cap's user-facing face normal; tilt 0.00 / 1.84 / 4.00 / "
             "7.06 / 9.36 deg from the joystick axis",
             "Thumb Inner Housing Lab REV_B | audit only | no production geometry written",
             fit=fit, world_lines=lines, world_labels=labels)

    # ---- 2..5 : axis sections, exact STEP vs LOWER15 --------------------
    meta = json.loads((L.LAB / "03_lineage" / "b08_lower15_vs_exact.json")
                      .read_text(encoding="utf-8"))
    for idx, short in (("02", "JOY"), ("03", "T2"), ("04", "T7"), ("05", "T4")):
        ax, cen, top = axes[short], cens[short], tops[short]
        cut_n = np.cross(ax, L.DATUM_U)
        if float(np.linalg.norm(cut_n)) < 0.2:
            cut_n = np.cross(ax, L.DATUM_V)
        cut_n = L.unit(cut_n)
        cam = tuple(-cut_n)
        up = tuple(L.unit(ax))
        ln = [(cen - ax * 16.0, cen + ax * 24.0, (226, 86, 86, 255), 3, "%s press axis" % short)]
        lb = [(cen + ax * top, "cap outermost point", (20, 20, 20))]
        for tag, T, col, nm in (("EXACT", Tex, C_SHELL, "exact frozen STEP"),
                                ("LOWER15", T15c, C_L15, "LOWER15 housing (approved source)")):
            iv = ray_intervals(T, cen, ax)
            out = [p for p in (iv or []) if p[1] > top]
            if out:
                w = max(out, key=lambda p: p[1] - p[0])
                lb.append((cen + ax * w[0], "%s inner skin  t=%+.3f" % (tag, w[0] - top),
                           (20, 90, 160) if tag == "EXACT" else (30, 110, 40)))
                lb.append((cen + ax * w[1], "%s outer skin  wall=%.3f mm" % (tag, w[1] - w[0]),
                           (20, 90, 160) if tag == "EXACT" else (30, 110, 40)))
            else:
                lb.append((cen + ax * (top + 6.0), "%s: OPEN (no material outboard)" % tag,
                           (20, 90, 160) if tag == "EXACT" else (30, 110, 40)))
        e = meta["capVsSkins"][short]
        sub = ("exact STEP wall %.3f mm | LOWER15 %s"
               % (e["EXACT"]["wallThicknessMm"],
                  "OPEN" if e["LOWER15"]["wallThicknessMm"] == 0.0
                  else "%.3f mm" % e["LOWER15"]["wallThicknessMm"]))
        section_render(OUT / ("%s_section_%s.png" % (idx, short)),
                       "SECTION through %s on its TRUE press axis" % short, sub,
                       [(Tex, C_SHELL, 1.0, "exact frozen STEP"),
                        (T15c, C_L15, 0.55, "LOWER15 housing (the approved surface)"),
                        (Tcaps, C_CAP, 1.0, "Thumb caps")],
                       cut_n, cen, cam, up, ln, lb, fit)
        L.memory("section " + short)

    # ---- 6, 7 : C01 heatmaps -------------------------------------------
    z = np.load(L.LAB / "05_c01_wall_audit" / "b09_c01_maps.npz")
    U, V, thick, gap, plate = z["U"], z["V"], z["thick"], z["gap"], z["plate"]
    heatmap(OUT / "06_c01_thin_wall_heatmap.png", U, V, thick, plate,
            "C01 plate thickness  --  every column below 1.20 mm highlighted",
            "interior (non-edge) thin area = 0.00 mm2; all 100.12 mm2 is plan trim edge, "
            "aperture edge or sliver",
            [(0.0, 0.40), (0.40, 0.80), (0.80, 1.20), (1.20, 2.20), (2.20, 1e9)],
            [(200, 30, 40), (240, 120, 50), (245, 200, 70), (150, 200, 130), (70, 150, 100)])
    gmask = plate & np.isfinite(gap)
    gz = np.where(np.isfinite(gap), gap, -1.0)
    heatmap(OUT / "07_c01_shell_gap_heatmap.png", U, V, gz, gmask,
            "C01 shell gap  --  banded",
            "99.3 % of the plate is at >= 0.80 mm; only 8.87 mm2 lies below 0.40 mm",
            [(0.0, 0.20), (0.20, 0.40), (0.40, 0.80), (0.80, 1.20), (1.20, 1e9)],
            [(200, 30, 40), (240, 120, 50), (245, 200, 70), (110, 175, 220), (60, 110, 175)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
