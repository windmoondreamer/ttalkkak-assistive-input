"""전면 램프 2D 실루엣 비교 (45 / 40 / 35 / 30 deg). 3D 생성 전 검토용.

램프는 **현재 패드 앞끝에서 앞으로 덧붙이는 새 면**이다.
손목 접촉면 / HAND_REF / 20도 기준면은 건드리지 않는다.

    python lower_adapter/local_cad/build123d/front_ramp_2d.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                           # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import preview_render as PR                               # noqa: E402

matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False

LOCAL = os.path.dirname(HERE)
STL = os.path.join(LOCAL, "export", "stl")
PREVIEW = os.path.join(LOCAL, "preview")
REPORTS = os.path.join(LOCAL, "reports")
UP, UH, GH = PR.UP, PR.UH, -171.326109
LIP_H = 5.0
ANGLES = [45.0, 40.0, 35.0, 30.0]
COLS = {45.0: "#2b6cb0", 40.0: "#2f855a", 35.0: "#c05621", 30.0: "#805ad5"}


def surf_points(tris, n=4):
    pts = [tris.reshape(-1, 3)]
    for i in range(n + 1):
        for j in range(n + 1 - i):
            a, b = i / n, j / n
            pts.append(tris[:, 0] * a + tris[:, 1] * b + tris[:, 2] * (1 - a - b))
    return np.vstack(pts)


def sils(tris, step=1.5):
    V = surf_points(tris)
    u, h = V @ UH, V @ UP - GH
    us = np.arange(u.min(), u.max() + step, step)
    up_, lo_ = [], []
    for uu in us:
        m = (u >= uu - step) & (u < uu + step)
        if m.sum() >= 3:
            up_.append((uu, h[m].max()))
            lo_.append((uu, h[m].min()))
    return np.array(up_), np.array(lo_), float(u.min()), float(u.max())


def ramp(theta, u_tip, h_tip):
    """직선 램프 (u,h) 와 파생 수치."""
    drop = h_tip - LIP_H
    run = drop / math.tan(math.radians(theta))
    # 현재 최전방 **Y** 는 립 바닥(h=LIP_H)이지 상단 코너가 아니다.
    # 램프 끝도 h=LIP_H 이므로 Δh=0 -> s = run / 1.0642.
    # (기준점을 상단으로 잡아 drop 을 넣으면 30~40mm 과대 산출된다)
    s_y = run / 1.0642                           # Y 방향 추가 길이
    u_end = u_tip - run
    pts = np.array([[u_tip, h_tip], [u_end, LIP_H], [u_end + 6.0, 0.0]])
    return pts, {"theta": theta, "drop_mm": drop, "run_u_mm": run,
                 "added_len_Y_mm": s_y, "u_new_tip": u_end}


def main():
    tris = PR.read_stl(os.path.join(STL, "ERGO_HOUSING_W2_PRINT_FINAL.stl"))
    up_, lo_, umin, umax = sils(tris)
    u_tip = umin
    h_tip = float(up_[up_[:, 0] < u_tip + 3.0][:, 1].max())
    L_now = 227.6362
    print(f"현재 앞끝 u {u_tip:.2f}  상단 h {h_tip:.2f}   전장 {L_now:.1f} mm")

    res = {}
    for th in ANGLES:
        pts, m = ramp(th, u_tip, h_tip)
        m["total_L_mm"] = L_now + m["added_len_Y_mm"]
        m["ground_span_u_mm"] = float(umax - m["u_new_tip"])
        res[str(th)] = m
        res[str(th)]["_pts"] = pts

    def panel(ax, angles, title, xlim=(-260, 100)):
        ax.plot(up_[:, 0], up_[:, 1], color="#2d3748", lw=2.0, label="현재 상단")
        ax.plot(lo_[:, 0], lo_[:, 1], color="#a0aec0", lw=1.8, ls="--",
                label="현재 하단")
        for th in angles:
            p = res[str(th)]["_pts"]
            m = res[str(th)]
            ax.plot(p[:, 0], p[:, 1], color=COLS[th], lw=2.8,
                    label=f"{th:.0f}deg  전장 {m['total_L_mm']:.0f}mm "
                          f"(+{m['added_len_Y_mm']:.0f})")
            ax.plot([p[1, 0]], [p[1, 1]], "o", color=COLS[th], ms=6)
        ax.axhline(0, color="k", lw=1.2)
        ax.axvline(u_tip, color="#e53e3e", lw=1.0, ls=":")
        ax.text(u_tip, 0.97, " 현재 앞끝", color="#e53e3e", fontsize=9,
                transform=ax.get_xaxis_transform(), va="top")
        ax.set_xlim(*xlim); ax.set_ylim(-6, 150)
        ax.set_aspect("equal"); ax.grid(alpha=0.3)
        ax.set_xlabel("u [mm]  (왼쪽 = 앞쪽)")
        ax.set_ylabel("지면 위 높이 h [mm]")
        ax.legend(fontsize=9, loc="upper right")
        ax.set_title(title, fontsize=13)

    for th in ANGLES:
        fig, ax = plt.subplots(figsize=(13, 6))
        panel(ax, [th], f"전면 램프 {th:.0f}deg — 전장 "
                        f"{res[str(th)]['total_L_mm']:.0f} mm")
        fig.savefig(os.path.join(PREVIEW, f"RAMP_{int(th)}.png"), dpi=110,
                    bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"  saved preview/RAMP_{int(th)}.png")
    fig, ax = plt.subplots(figsize=(15, 7))
    panel(ax, ANGLES, "전면 램프 각도 비교 — 45 / 40 / 35 / 30 deg")
    fig.savefig(os.path.join(PREVIEW, "RAMP_COMPARISON.png"), dpi=110,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved preview/RAMP_COMPARISON.png")

    print(f"\n{'각도':>6s} {'강하[mm]':>9s} {'수평런':>8s} {'추가길이Y':>10s}"
          f" {'전장L':>8s} {'새 앞끝u':>9s} {'접지길이':>9s}")
    for th in ANGLES:
        m = res[str(th)]
        print(f"{th:6.0f} {m['drop_mm']:9.1f} {m['run_u_mm']:8.1f}"
              f" {m['added_len_Y_mm']:10.1f} {m['total_L_mm']:8.1f}"
              f" {m['u_new_tip']:9.1f} {m['ground_span_u_mm']:9.1f}")
    json.dump({k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
               for k, v in res.items()},
              open(os.path.join(REPORTS, "10_front_ramp_2d.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
