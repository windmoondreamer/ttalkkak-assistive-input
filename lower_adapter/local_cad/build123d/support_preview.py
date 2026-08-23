"""PRINT_READY / CAD support 프리뷰 — 전역 깊이 정렬 렌더 (system python).

부품별로 따로 그리면 나중 부품이 덧칠돼 거짓말을 한다 (기록된 함정).
전 삼각형을 합쳐 한 번만 정렬한다.
"""
from __future__ import annotations
import os
import sys
import json
import math
import struct

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                          # noqa: E402
from matplotlib.collections import PolyCollection        # noqa: E402

matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL = os.path.dirname(HERE)
DUMP = os.path.join(os.path.dirname(LOCAL), "cad_dump")
STL = os.path.join(LOCAL, "export", "stl")
PREVIEW = os.path.join(LOCAL, "preview")
C_PROD, C_SUP = "#5f6b7a", "#d2453a"


def read_stl(path):
    with open(path, "rb") as f:
        h = f.read(5)
        f.seek(0)
        if h == b"solid":
            v = [l.split()[1:4] for l in f
                 if l.split() and l.split()[0] == b"vertex"]
            return np.array(v, dtype=float).reshape(-1, 3, 3)
        f.seek(80)
        n = struct.unpack("<I", f.read(4))[0]
        d = np.frombuffer(f.read(50 * n), dtype=np.uint8).reshape(n, 50)
        return d[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(float)


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def frame(w):
    w = np.array(w, float)
    w /= np.linalg.norm(w)
    up = np.array([0.0, 0.0, 1.0])
    if abs(w @ up) > 0.95:
        up = np.array([0.0, 1.0, 0.0])
    u = np.cross(up, w)
    u /= np.linalg.norm(u)
    return u, np.cross(w, u), w


def render(ax, sets, wd, clip=None):
    u, v, w = frame(wd)
    T, C = [], []
    for t, col in sets:
        if clip is not None:
            ai, val, neg = clip
            t = t[(t[:, :, ai] < val).all(1)] if neg else t[(t[:, :, ai] > val).all(1)]
        if len(t) == 0:
            continue
        T.append(t)
        C.append(np.repeat([matplotlib.colors.to_rgb(col)], len(t), axis=0))
    T, C = np.vstack(T), np.vstack(C)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    nn = n / np.maximum(np.linalg.norm(n, axis=1)[:, None], 1e-12)
    k = (nn @ w) < 0
    T, C, nn = T[k], C[k], nn[k]
    o = np.argsort(-(T.mean(1) @ w))
    T, C, nn = T[o], C[o], nn[o]
    L = np.array([0.4, -0.6, 0.7])
    L /= np.linalg.norm(L)
    sh = np.clip(0.38 + 0.62 * np.abs(nn @ L), 0, 1)
    poly = np.stack([T.reshape(-1, 3) @ u, T.reshape(-1, 3) @ v],
                    1).reshape(-1, 3, 2)
    ax.add_collection(PolyCollection(poly, facecolors=np.clip(C * sh[:, None], 0, 1),
                                     edgecolors="none", linewidths=0))
    pu, pv = poly[:, :, 0].ravel(), poly[:, :, 1].ravel()
    ax.set_xlim(pu.min() - 8, pu.max() + 8)
    ax.set_ylim(pv.min() - 8, pv.max() + 8)
    ax.set_aspect("equal")
    ax.axis("off")
    return u, v


def save(fig, name):
    p = os.path.join(PREVIEW, name + ".png")
    fig.savefig(p, dpi=115, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved", os.path.relpath(p, LOCAL))


def main():
    mat = sys.argv[1] if len(sys.argv) > 1 else "PLA"
    val = json.load(open(os.path.join(LOCAL, "reports",
                                      "16_support_validate_%s.json" % mat),
                         encoding="utf-8"))
    cfg = json.load(open(os.path.join(LOCAL, "reports",
                                      "16_custom_support_%s.json" % mat),
                         encoding="utf-8"))
    ISO = np.array([-0.72, -0.50, -0.48])
    for nm, fn, lab in (("MAIN", "HOUSING_V4_MAIN_PRINT_REV_D", "CUT FACE UP"),
                        ("ARMREST", "HOUSING_V4_ARMREST_PRINT_REV_D",
                         "CUT FACE DOWN")):
        z0, ang = np.load(os.path.join(DUMP, "_sup_z0_%s.npy" % nm))
        Pd = read_stl(os.path.join(STL, fn + ".stl")) @ rot_x(ang).T
        Pd[:, :, 2] -= z0
        Sp = read_stl(os.path.join(STL, "%s_CUSTOM_SUPPORT_%s.stl" % (nm, mat)))
        r = val.get(nm, {})
        sv = r.get("support_volume_mm3", 0.0)
        bb = Pd.reshape(-1, 3).max(0) - Pd.reshape(-1, 3).min(0)

        # 1. CUSTOM_SUPPORT (iso + front)
        fig, axes = plt.subplots(1, 2, figsize=(15, 8))
        for ax, (t, wd) in zip(axes, (("ISO", ISO), ("FRONT", np.array([0.0, -1.0, 0.0])))):
            render(ax, [(Pd, C_PROD), (Sp, C_SUP)], wd)
            ax.set_title(t, fontsize=11)
            if t == "FRONT":
                ax.axhline(0, color="#333", lw=1.3, ls="--")
                ax.text(0, -8, "build plate", fontsize=9, color="#333", ha="center")
        c0 = cfg.get(nm, {})
        fig.suptitle("%s CAD SACRIFICIAL SUPPORT (%s, %s)   회색 제품 / 빨강 support\n"
                     "리브 %.1f + 머리 %.1f x 피치 %.1f mm → 브리지 %.1f mm · "
                     "Z gap %.2f · 측면 %.2f~%.2f · support %.1f cm3 (%.0f g)"
                     % (nm, lab, mat, c0.get("rib_t", 0.8), c0.get("head_w", 0.0),
                        c0.get("rib_pitch", 0.0), c0.get("free_span", 0.0),
                        c0.get("gap_z", 0.2), c0.get("lateral_min", 0.4),
                        c0.get("lateral", 0.4), sv / 1000.0, sv * 1.24e-3),
                     fontsize=12)
        save(fig, "%s_CUSTOM_SUPPORT" % nm)

        # 2. CUTAWAY (MAIN 만)
        if nm == "MAIN":
            fig, axes = plt.subplots(1, 2, figsize=(16, 8))
            render(axes[0], [(Pd, C_PROD), (Sp, C_SUP)],
                   np.array([1.0, 0.0, 0.0]), clip=(0, 0.0, False))
            axes[0].set_title("SECTION X=0 (절단면에서 +X 쪽 내부를 본다)",
                              fontsize=11)
            render(axes[1], [(Pd, C_PROD), (Sp, C_SUP)],
                   np.array([0.0, 0.0, -1.0]))
            axes[1].set_title("TOP (리브 %d개 / 피치 %.1fmm)"
                              % (cfg.get(nm, {}).get("n_rib", 0),
                                 cfg.get(nm, {}).get("rib_pitch", 0)), fontsize=11)
            fig.suptitle("MAIN CUSTOM SUPPORT — CUTAWAY   "
                         "리브가 천장 아래 0.20mm 에서 끊긴다", fontsize=13)
            save(fig, "MAIN_CUSTOM_SUPPORT_CUTAWAY")

        # 3. REMOVAL
        rows = r.get("chunk_rows", [])
        fig, ax = plt.subplots(figsize=(13, 9))
        u, v = render(ax, [(Pd, C_PROD), (Sp, C_SUP)], ISO)
        c = Sp.reshape(-1, 3).mean(0)
        ops = {}
        for q in rows:
            ops.setdefault(q["opening"] or "TRAPPED", []).append(q)
        lines = []
        for k, (o, qs) in enumerate(sorted(ops.items())):
            d = np.array([0.0, 1.0, 0.0]) if "DECK" in o or "UNDER" in o else (
                np.array([0.0, 0.0, 1.0]) if "TOP" in o or "CUT" in o
                else np.array([0.0, -1.0, 0.0]))
            dv = np.array([float(d @ u), float(d @ v)])
            dv /= max(np.linalg.norm(dv), 1e-9)
            a0 = np.array([0.72, 0.86 - 0.10 * k])
            ax.annotate("", xy=tuple(a0 + dv * 0.11), xytext=tuple(a0),
                        xycoords="axes fraction", textcoords="axes fraction",
                        arrowprops=dict(arrowstyle="-|>", color="#b02a1f", lw=3.0),
                        zorder=20)
            ax.text(a0[0] - 0.02, a0[1], o, transform=ax.transAxes, fontsize=10.5,
                    color="#b02a1f", ha="right", va="center", zorder=20)
            lines.append("%s : chunk %d개 / %.1f cm3 / 최소 통과여유 %.1f mm"
                         % (o, len(qs), sum(q["vol"] for q in qs) / 1000.0,
                            min(q["clear"] for q in qs)))
        lines.append("TRUE TRAPPED SUPPORT = %d" % r.get("trapped", -1))
        ax.text(0.02, 0.02, "\n".join(lines), transform=ax.transAxes,
                fontsize=11, color="#12305e", va="bottom", zorder=20,
                bbox=dict(fc="white", ec="#12305e", alpha=0.92, pad=6))
        ax.set_title("%s SUPPORT REMOVAL — 인출 개구부 / 방향" % nm, fontsize=13)
        save(fig, "%s_SUPPORT_REMOVAL" % nm)

        # 4. PRINT_READY ISOMETRIC
        fig, ax = plt.subplots(figsize=(12, 9))
        render(ax, [(Pd, C_PROD), (Sp, C_SUP)], ISO)
        ax.axhline(0, color="#333", lw=1.0, ls=":")
        ax.set_title("PRINT_READY %s (%s / %s)   슬라이서 투입 그대로\n"
                     "brim 5mm 는 CAD 가 아니라 Bambu Studio 설정으로 준다"
                     % (nm, lab, mat), fontsize=12.5)
        save(fig, "PRINT_READY_%s_ISOMETRIC" % nm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
