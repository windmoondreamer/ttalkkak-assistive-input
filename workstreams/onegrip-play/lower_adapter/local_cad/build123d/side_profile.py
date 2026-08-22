"""SIDE 2D 하부 프로파일 설계·검증 (3D 이전 단계).

좌표계:
    u = p . UH      길이방향 (작을수록 손목 앞쪽)
    h = p . UP - GH 지면 위 높이

핵심 관계 (등Y 단면을 (u,h) 로 보낸 것):
    h = 2.92397*y - 2.74766*u + 171.326109
    z = (0.9397*y - u) / 0.342
즉 등Y 평면은 (u,h) 에서 기울기 -2.74766 (=70.0도) 인 직선이다.
그래서 하부 프로파일을 u 로 주면 각 단면의 bottom Z 를 **직접 계산**할 수 있다 (§12).

실행:
    python lower_adapter/local_cad/build123d/side_profile.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

UP = np.array([0.0, 0.3420201433256687, 0.9396926207859084])
UH = np.array([0.0, 0.9396926207859084, -0.3420201433256687])
GH = -171.326109

LOCAL = os.path.dirname(HERE)
STL = os.path.join(LOCAL, "export", "stl")
PREVIEW = os.path.join(LOCAL, "preview")
REPORTS = os.path.join(LOCAL, "reports")

# 하부 프로파일 제어점 (u, h).  마지막 두 점은 h=0 을 두 번 둬서
# 지면 접촉부의 기울기가 0 이 되게 한다 (§7 near-tangent).
U_TIP = -81.89          # 현재 W2 손목 앞끝 (실측). 전면 수직 절단면 위치.
LIP_H = 5.0             # 앞끝 립이 지면에서 뜨는 높이

LOWER_PROFILES = {
    "A": [(-81.89, 5.0), (-76.0, 3.2), (-70.0, 1.6), (-64.0, 0.5),
          (-60.0, 0.0), (-50.0, 0.0)],
    "B": [(-81.89, 5.0), (-78.0, 3.6), (-73.0, 2.0), (-69.0, 0.8),
          (-67.0, 0.0), (-55.0, 0.0)],
}


def pchip(xs, ys):
    """단조 3차 Hermite (Fritsch-Carlson). scipy 없이.

    단조성을 보장해야 하부 프로파일이 도중에 되올라가지 않는다.
    """
    x = np.asarray(xs, float)
    y = np.asarray(ys, float)
    n = len(x)
    dk = np.diff(y) / np.diff(x)
    m = np.zeros(n)
    m[0], m[-1] = dk[0], dk[-1]
    for i in range(1, n - 1):
        if dk[i - 1] * dk[i] <= 0:
            m[i] = 0.0
        else:
            w1 = 2 * (x[i + 1] - x[i]) + (x[i] - x[i - 1])
            w2 = (x[i + 1] - x[i]) + 2 * (x[i] - x[i - 1])
            m[i] = (w1 + w2) / (w1 / dk[i - 1] + w2 / dk[i])

    def f(q):
        q = np.atleast_1d(np.asarray(q, float))
        out = np.empty_like(q)
        for k, qq in enumerate(q):
            if qq <= x[0]:
                out[k] = y[0]
                continue
            if qq >= x[-1]:
                out[k] = y[-1]
                continue
            i = int(np.searchsorted(x, qq) - 1)
            hh = x[i + 1] - x[i]
            t = (qq - x[i]) / hh
            h00 = 2 * t ** 3 - 3 * t ** 2 + 1
            h10 = t ** 3 - 2 * t ** 2 + t
            h01 = -2 * t ** 3 + 3 * t ** 2
            h11 = t ** 3 - t ** 2
            out[k] = (h00 * y[i] + h10 * hh * m[i]
                      + h01 * y[i + 1] + h11 * hh * m[i + 1])
        return out if out.size > 1 else float(out[0])
    return f


def lower_fn(kind):
    """하부 프로파일 h(u). 제어점 앞은 상수, 뒤는 0 (지면)."""
    cps = LOWER_PROFILES[kind]
    base = pchip([c[0] for c in cps], [c[1] for c in cps])

    def f(u):
        arr = np.atleast_1d(np.asarray(u, float))
        out = np.array([float(base(min(max(uu, cps[0][0]), cps[-1][0])))
                        for uu in arr])
        out[arr > cps[-1][0]] = 0.0
        out[arr < cps[0][0]] = cps[0][1]
        return out if out.size > 1 else float(out[0])
    return f


def zbot_for_y(y, kind, u_lo=-140.0, u_hi=40.0):
    """등Y 단면의 bottom Z 를 하부 프로파일에서 **직접** 푼다 (§12).

    등Y 직선  h(u) = 2.92397y - 2.74766u + 171.326109  와
    하부 프로파일 h = f(u) 의 교점. 왼쪽으로 단조 감소라 이분법이 안전하다.
    """
    f = lower_fn(kind) if isinstance(kind, str) else kind

    def g(u):
        return (2.92397 * y - 2.74766 * u + 171.326109) - float(f(u))
    a, b = u_lo, u_hi
    ga, gb = g(a), g(b)
    if ga * gb > 0:
        return None
    for _ in range(80):
        mid = 0.5 * (a + b)
        if ga * g(mid) <= 0:
            b = mid
        else:
            a, ga = mid, g(mid)
    u = 0.5 * (a + b)
    return (0.9396926207859084 * y - u) / 0.3420201433256687, u


def read_stl(path):
    import struct
    with open(path, "rb") as fh:
        head = fh.read(5)
        fh.seek(0)
        if head == b"solid":
            v = [ [float(x) for x in s[1:4]]
                  for s in (ln.split() for ln in fh) if s and s[0] == b"vertex"]
            return np.array(v).reshape(-1, 3, 3)
        fh.seek(80)
        n = struct.unpack("<I", fh.read(4))[0]
        t = np.empty((n, 3, 3))
        for i in range(n):
            d = struct.unpack("<12fH", fh.read(50))
            t[i] = np.array(d[3:12]).reshape(3, 3)
        return t


def surf_points(tris, n=5):
    pts = [tris.reshape(-1, 3)]
    for i in range(n + 1):
        for j in range(n + 1 - i):
            a, b = i / n, j / n
            pts.append(tris[:, 0] * a + tris[:, 1] * b + tris[:, 2] * (1 - a - b))
    return np.vstack(pts)


def silhouettes(tris, step=1.5):
    V = surf_points(tris)
    u, h = V @ UH, V @ UP - GH
    us = np.arange(u.min(), u.max() + step, step)
    up_, lo_ = [], []
    for uu in us:
        m = (u >= uu - step) & (u < uu + step)
        if m.sum() >= 3:
            up_.append((uu, h[m].max()))
            lo_.append((uu, h[m].min()))
    return np.array(up_), np.array(lo_)


# ------------------------------------------------------------------ 측정 / 플롯

def profile_metrics(kind, up_sil, lo_sil):
    f = lower_fn(kind)
    cps = LOWER_PROFILES[kind]
    u_tip = float(up_sil[:, 0].min())
    u_ground = cps[-2][0]
    us = np.linspace(cps[0][0], cps[-1][0], 400)
    hs = np.array([float(f(x)) for x in us])
    sl = np.degrees(np.arctan2(-np.diff(hs), np.diff(us)))
    # 하부 최전방 3D 위치 (립 앞끝) 와 첫 접지 Y
    y_lip = 0.9396926207859084 * cps[0][0] + 0.3420201433256687 * (cps[0][1] + GH)
    y_gnd = (u_ground - 62.36) / 1.0642
    return {
        "first_ground_contact_u": u_ground,
        "floating_span_mm": u_tip - u_ground,
        "front_lip_h_mm": cps[0][1],
        "max_lower_slope_deg": float(np.abs(sl).max()),
        "mean_lower_slope_deg": float(np.abs(sl).mean()),
        "ground_contact_slope_deg": float(abs(sl[-1])),
        "lip_front_Y_mm": float(y_lip),
        "first_contact_Y_mm": float(y_gnd),
        "support_length_mm": float(up_sil[:, 0].max() - u_tip),
    }


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams["font.family"] = "Malgun Gothic"
    matplotlib.rcParams["axes.unicode_minus"] = False

    tris = read_stl(os.path.join(STL, "ERGO_HOUSING_W2.stl"))
    up_sil, lo_sil = silhouettes(tris)
    u_tip = float(up_sil[:, 0].min())
    cur_gnd = float(lo_sil[lo_sil[:, 1] < 0.5][:, 0].min())
    print(f"현재 W2: 앞끝 u {u_tip:.2f}   첫 접지 u {cur_gnd:.2f}   "
          f"floating span {u_tip - cur_gnd:.2f} mm")
    m = (lo_sil[:, 0] > -85) & (lo_sil[:, 0] < -20)
    seg = lo_sil[m]
    sl = np.degrees(np.arctan2(-np.diff(seg[:, 1]), np.diff(seg[:, 0])))
    print(f"현재 하부 최대 상승각 {float(np.abs(sl).max()):.1f} deg")

    res = {"CURRENT": {"first_ground_contact_u": cur_gnd,
                       "floating_span_mm": u_tip - cur_gnd,
                       "max_lower_slope_deg": float(np.abs(sl).max()),
                       "support_length_mm": float(up_sil[:, 0].max() - u_tip)}}

    def panel(ax, kinds, title):
        ax.plot(up_sil[:, 0], up_sil[:, 1], color="#2d3748", lw=2.0,
                label="현재 상부 실루엣 (유지)")
        ax.plot(lo_sil[:, 0], lo_sil[:, 1], color="#a0aec0", lw=2.0, ls="--",
                label="현재 하부 실루엣")
        cols = {"A": "#2b6cb0", "B": "#c05621"}
        for k in kinds:
            f = lower_fn(k)
            us = np.linspace(-90, -20, 500)
            ax.plot(us, [float(f(x)) for x in us], color=cols[k], lw=2.6,
                    label=f"새 하부 프로파일 {k}")
            ax.plot([LOWER_PROFILES[k][-2][0]], [0], "o", color=cols[k], ms=7)
        ax.axhline(0, color="k", lw=1.2)
        ax.axvline(u_tip, color="#e53e3e", lw=1.0, ls=":")
        ax.text(u_tip, 0.95, " 손목 앞끝", color="#e53e3e", fontsize=9,
                transform=ax.get_xaxis_transform(), va="top")
        ax.set_xlim(-100, 60); ax.set_ylim(-6, 120)
        ax.set_aspect("equal"); ax.grid(alpha=0.3)
        ax.set_xlabel("u [mm]  (작을수록 손목 앞쪽)")
        ax.set_ylabel("지면 위 높이 h [mm]")
        ax.legend(fontsize=9, loc="upper right")
        ax.set_title(title, fontsize=13)

    for name, kinds, title in (("SIDE_PROFILE_CURRENT", [], "현재 W2 SIDE 실루엣"),
                               ("SIDE_PROFILE_A", ["A"], "PROFILE A — 20도 CHARACTER"),
                               ("SIDE_PROFILE_B", ["B"], "PROFILE B — SMOOTH GROUND BLEND")):
        fig, ax = plt.subplots(figsize=(11, 6))
        panel(ax, kinds, title)
        fig.savefig(os.path.join(PREVIEW, name + ".png"), dpi=110,
                    bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print("  saved preview/" + name + ".png")
    fig, ax = plt.subplots(figsize=(13, 7))
    panel(ax, ["A", "B"], "SIDE 하부 프로파일 비교 — 현재 / A / B")
    ax.set_xlim(-95, -10); ax.set_ylim(-4, 60)
    fig.savefig(os.path.join(PREVIEW, "SIDE_PROFILE_COMPARISON.png"), dpi=110,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved preview/SIDE_PROFILE_COMPARISON.png")

    print("")
    print(f"{'항목':<26s}{'CURRENT':>12s}{'A':>12s}{'B':>12s}")
    for k in ("A", "B"):
        res[k] = profile_metrics(k, up_sil, lo_sil)
    rows = ["first_ground_contact_u", "floating_span_mm", "front_lip_h_mm",
            "max_lower_slope_deg", "ground_contact_slope_deg",
            "lip_front_Y_mm", "first_contact_Y_mm", "support_length_mm"]
    for r in rows:
        line = f"{r:<26s}"
        for k in ("CURRENT", "A", "B"):
            v = res[k].get(r)
            line += f"{v:12.2f}" if isinstance(v, float) else f"{'-':>12s}"
        print(line)
    json.dump(res, open(os.path.join(REPORTS, "06_side_profiles.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
