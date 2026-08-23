"""§12 분할 프리뷰 — 전역 깊이 정렬 렌더.

SPLIT_SIDE / SPLIT_ISOMETRIC / SPLIT_EXPLODED
MAIN_PRINT_ORIENTATION / ARMREST_PRINT_ORIENTATION
JOINT_DETAIL / JOINT_SECTION
"""
from __future__ import annotations
import os
import sys
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
STL = os.path.join(LOCAL, "export", "stl")
PREVIEW = os.path.join(LOCAL, "preview")

UP = np.array([0.0, 0.3420201433256687, 0.9396926207859084])
UH = np.array([0.0, 0.9396926207859084, -0.3420201433256687])
C_MAIN, C_ARM = "#4a72a8", "#d98a3a"

# joint 파라미터 (split_build 와 동일 — 도면 주기용)
Y_UP, Y_LO, LAP_D, DBL_T, CLR = -140.0, -112.0, 7.0, 14.0, 0.275
PB_SLOPE, PB_Y0, PB_Z0 = 0.0875, -121.0, -70.81


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
        t = np.empty((n, 3, 3))
        for i in range(n):
            d = struct.unpack("<12fH", f.read(50))
            t[i] = np.array(d[3:12]).reshape(3, 3)
        return t


def frame(w):
    w = np.array(w, float)
    w /= np.linalg.norm(w)
    up = UP if abs(w @ UP) < 0.95 else np.array([1.0, 0, 0])
    u = np.cross(up, w)
    u /= np.linalg.norm(u)
    return u, np.cross(w, u), w


def render(ax, sets, wd, clip=None, zoom=None):
    u, v, w = frame(wd)
    T, C = [], []
    for t, col in sets:
        if clip is not None:
            ax_i, val, keep_neg = clip
            vx = t[:, :, ax_i]
            t = t[(vx < val).all(1)] if keep_neg else t[(vx > val).all(1)]
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
    if zoom:
        cu, cv, r = zoom
        ax.set_xlim(cu - r, cu + r)
        ax.set_ylim(cv - r * 0.8, cv + r * 0.8)
    else:
        ax.set_xlim(pu.min() - 8, pu.max() + 8)
        ax.set_ylim(pv.min() - 8, pv.max() + 8)
    ax.set_aspect("equal")
    ax.axis("off")
    return u, v


def one(name, sets, wd, title, clip=None, zoom=None, figsize=(12, 9)):
    fig, ax = plt.subplots(figsize=figsize)
    render(ax, sets, wd, clip, zoom)
    ax.set_title(title, fontsize=13)
    p = os.path.join(PREVIEW, name + ".png")
    fig.savefig(p, dpi=115, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved", os.path.relpath(p, LOCAL))


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def main():
    M = read_stl(os.path.join(STL, "HOUSING_V4_MAIN_PRINT.stl"))
    A = read_stl(os.path.join(STL, "HOUSING_V4_ARMREST_PRINT.stl"))
    ISO = np.array([-0.72, -0.50, -0.48])
    sets = [(M, C_MAIN), (A, C_ARM)]

    one("SPLIT_SIDE", sets, np.array([-1.0, 0, 0]),
        "SPLIT — SIDE   파랑 MAIN / 주황 ARMREST")
    one("SPLIT_ISOMETRIC", sets, ISO, "SPLIT — ISOMETRIC")
    Ax = A.copy()
    Ax[:, :, 1] -= 90.0                       # -Y 로 분해
    one("SPLIT_EXPLODED", [(M, C_MAIN), (Ax, C_ARM)], ISO,
        "SPLIT — EXPLODED (ARMREST 를 -Y 로 90mm 이동)")

    # 두 파트 다 Rx -90 이지만 절단면 법선이 반대라 라벨이 다르다:
    #   MAIN 절단면 법선 -Y -> Rx-90 에서 +Z (위)   = CUT FACE UP
    #   ARMREST      +Y -> Rx-90 에서 -Z (아래) = CUT FACE DOWN
    for nm, T, ang, col, lab_o in (("MAIN", M, -90.0, C_MAIN, "CUT FACE UP"),
                                   ("ARMREST", A, -90.0, C_ARM, "CUT FACE DOWN")):
        Tp = T @ rot_x(ang).T
        Tp[:, :, 2] -= Tp.reshape(-1, 3)[:, 2].min()
        bb = Tp.reshape(-1, 3).max(0) - Tp.reshape(-1, 3).min(0)
        fig, axes = plt.subplots(1, 2, figsize=(15, 8))
        for ax, (lab, wd) in zip(axes, (("ISO", np.array([-0.72, -0.5, -0.48])),
                                        ("FRONT", np.array([0.0, -1.0, 0.0])))):
            render(ax, [(Tp, col)], wd)
            ax.set_title(f"{lab}", fontsize=11)
            if lab == "FRONT":
                ax.axhline(0, color="#444", lw=1.2, ls="--")
                ax.text(0, -6, "build plate", fontsize=9, color="#444", ha="center")
        fig.suptitle(f"{nm} PRINT ORIENTATION ({lab_o}, Rx {ang:+.0f}deg)   "
                     f"bbox {bb[0]:.1f} x {bb[1]:.1f} x {bb[2]:.1f} mm   "
                     f"P1S 256 이내", fontsize=13)
        p = os.path.join(PREVIEW, f"{nm}_PRINT_ORIENTATION.png")
        fig.savefig(p, dpi=115, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print("  saved", os.path.relpath(p, LOCAL))

    # ---- JOINT DETAIL / SECTION ----------------------------------------
    u, v, _ = frame(ISO)
    ctr = np.array([0.0, -126.0, -74.0])
    one("JOINT_DETAIL", sets, ISO, "JOINT DETAIL — 랩 / 리브 / 나사",
        zoom=(float(ctr @ u), float(ctr @ v), 62.0), figsize=(11, 9))

    # 단면: X<0 제거 -> YZ 평면 단면을 옆에서 본다
    wd = np.array([-1.0, 0.0, 0.0])
    u2, v2, _ = frame(wd)
    fig, ax = plt.subplots(figsize=(14, 8))
    render(ax, sets, wd, clip=(0, 0.0, False),
           zoom=(float(ctr @ u2), float(ctr @ v2), 46.0))
    pbz = lambda y: PB_Z0 + PB_SLOPE * (y - PB_Y0)
    n = np.array([0.0, -PB_SLOPE, 1.0])
    n /= np.linalg.norm(n)

    def pt(y, off):
        p3 = np.array([0.0, y, pbz(y)]) - n * off
        return float(p3 @ u2), float(p3 @ v2)

    ann = [
        ((Y_UP, 0.0), (Y_UP - 16, -14), "상판 6mm (원본 skin)"),
        ((Y_LO, LAP_D), (Y_LO + 14, LAP_D + 16), f"랩 평면 (상판 밑 {LAP_D}mm)"),
        (((Y_UP + Y_LO) / 2, DBL_T), ((Y_UP + Y_LO) / 2, DBL_T + 20),
         f"internal doubler {DBL_T}mm"),
        ((-133.0, DBL_T), (-133.0 - 22, DBL_T + 12), "M4 관통 + 카운터보어"),
        ((-119.0, LAP_D - 4), (-119.0 + 20, LAP_D - 20), "heat-set insert 5.6x8"),
    ]
    for (y, off), (ty, toff), txt in ann:
        xy = pt(y, off)
        xt = pt(ty, toff)
        ax.annotate(txt, xy=xy, xytext=xt, fontsize=9.5, color="#12305e",
                    arrowprops=dict(arrowstyle="->", color="#12305e", lw=1.4))
    a1 = pt(Y_UP, -3.0)
    a2 = pt(Y_LO, -3.0)
    ax.annotate("", xy=a2, xytext=a1,
                arrowprops=dict(arrowstyle="<->", color="#b03030", lw=2.0))
    mid = pt((Y_UP + Y_LO) / 2, -7.0)
    ax.text(*mid, f"overlap {Y_LO - Y_UP:.0f} mm", fontsize=11, color="#b03030",
            ha="center", weight="bold")
    ax.set_title("JOINT SECTION (X<0 제거)   파랑 MAIN / 주황 ARMREST   "
                 f"clearance {CLR} mm/side", fontsize=13)
    p = os.path.join(PREVIEW, "JOINT_SECTION.png")
    fig.savefig(p, dpi=115, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved", os.path.relpath(p, LOCAL))
    return 0


if __name__ == "__main__":
    sys.exit(main())
