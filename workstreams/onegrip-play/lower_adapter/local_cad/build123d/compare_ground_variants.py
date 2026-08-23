"""전면 지면 블렌드 변형 A/B 비교 (§18~§20). Onshape 미조회.

동일 카메라·스케일로 SIDE/ISOMETRIC 을 그리고, 두 SIDE 실루엣을 한 장에
겹쳐 비교한다. 측정은 전부 실제 메시에서 뽑는다.

    python lower_adapter/local_cad/build123d/compare_ground_variants.py
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

UP = np.array([0.0, 0.3420201433256687, 0.9396926207859084])
UH = np.array([0.0, 0.9396926207859084, -0.3420201433256687])
GH = -171.326109
CORE_VOL = 495615.470393

CASES = [("W2", "ERGO_HOUSING_W2"),
         ("A", "ERGO_HOUSING_W2_GROUND_A"),
         ("B", "ERGO_HOUSING_W2_GROUND_B")]


def surf_points(tris, n=4):
    """삼각형 **면 위** 균등 샘플. 정점만 쓰면 큰 평면 구간이 비어
    실루엣이 0 으로 튄다 (실제로 그랬다)."""
    pts = [tris.reshape(-1, 3)]
    for i in range(n + 1):
        for j in range(n + 1 - i):
            a, b = i / n, j / n
            pts.append(tris[:, 0] * a + tris[:, 1] * b + tris[:, 2] * (1 - a - b))
    return np.vstack(pts)


def silhouette_low(tris, step=2.0):
    """월드 (u, h) **하단** 실루엣."""
    V = surf_points(tris)
    u, h = V @ UH, V @ UP - GH
    us = np.arange(u.min(), u.max() + step, step)
    out = []
    for uu in us:
        m = (u >= uu - step) & (u < uu + step)
        if m.sum() >= 3:
            out.append((float(uu), float(h[m].min())))
    return np.array(out)


def silhouette(tris, step=2.0):
    """월드 (u, h) 상단 실루엣."""
    V = surf_points(tris)
    u, h = V @ UH, V @ UP - GH
    us = np.arange(u.min(), u.max() + step, step)
    out = []
    for uu in us:
        m = (u >= uu - step) & (u < uu + step)
        if m.sum() >= 3:
            out.append((float(uu), float(h[m].max())))
    return np.array(out)


def metrics(tris):
    V = tris.reshape(-1, 3)
    u, h = V @ UH, V @ UP - GH
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    mag = np.linalg.norm(n, axis=1)
    ok = mag > 1e-12
    area = mag[ok] / 2.0
    nn = n[ok] / mag[ok, None]
    ctr = tris[ok].mean(1)
    ch = ctr @ UP - GH
    # 접지: 지면 근처 + 아래를 보는 면
    gm = (ch < 0.5) & ((nn @ UP) < -0.9)
    # 서포트 필요: 빌드방향(월드 up) 기준 45도 초과 오버행
    sup = (nn @ UP) < -0.7071
    vol = float(np.einsum("ij,ij->i",
                          tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum() / 6.0)
    sil = silhouette(tris)
    lo = silhouette_low(tris)
    # **블렌드 구간만** 잰다: 앞끝 ~ 첫 접지.
    # 전 구간을 재면 u=-35.9 의 국소 노치(동결 코어의 전장 꼬리 관통 슬롯)가
    # 84.4도로 잡혀 실제 하부 경사를 가린다.
    _u, _h = lo[:, 0], lo[:, 1]
    _ug = float(_u[_h < 0.5].min()) if (_h < 0.5).any() else float(_u.max())
    lw = lo[(_u >= _u.min() - 1e-9) & (_u <= _ug + 2.0)]
    lsl = []
    for i in range(1, len(lw)):
        du = lw[i, 0] - lw[i - 1, 0]
        if du > 1e-6:
            lsl.append(math.degrees(math.atan2(-(lw[i, 1] - lw[i - 1, 1]), du)))
    lsl = np.array(lsl) if lsl else np.array([0.0])
    wr = sil[sil[:, 0] < 20.0]                 # 손목 쪽
    slopes = []
    for i in range(1, len(wr)):
        du = wr[i, 0] - wr[i - 1, 0]
        dh = wr[i, 1] - wr[i - 1, 1]
        if du > 1e-6:
            slopes.append(math.degrees(math.atan2(dh, du)))
    slopes = np.array(slopes) if slopes else np.array([0.0])
    # 전면 오버행: 최전방(u 최소) 지점의 h 와, 지면 접지 최전방 u
    u_tip = float(u.min())
    u_ground = float(u[h < 0.5].min()) if (h < 0.5).any() else float("nan")
    return {
        "volume_mm3": abs(vol),
        "added_vs_core_mm3": abs(vol) - CORE_VOL,
        "length_Y_mm": float(V[:, 1].max() - V[:, 1].min()),
        "width_X_mm": float(V[:, 0].max() - V[:, 0].min()),
        "height_world_mm": float(h.max() - h.min()),
        "u_extent_mm": float(u.max() - u.min()),
        "ground_area_mm2": float(area[gm].sum()),
        "ground_u_front_mm": u_ground,
        "tip_u_mm": u_tip,
        "front_overhang_mm": float(u_ground - u_tip),
        "front_max_slope_deg": float(np.abs(slopes).max()),
        "front_mean_slope_deg": float(np.abs(slopes[np.abs(slopes) > 20]).mean())
        if (np.abs(slopes) > 20).any() else 0.0,
        "support_area_frac": float(area[sup].sum() / area.sum()),
        "max_lower_slope_deg": float(np.abs(lsl).max()),
        "mean_lower_slope_deg": float(np.abs(lsl).mean()),
        "floating_span_mm": float(abs(u_ground - u_tip)),
        "tip_height_mm": float(h[u < u_tip + 2.0].max() - h[u < u_tip + 2.0].min()),
        "_sil": sil,
    }


def main():
    data, tri = {}, {}
    for key, name in CASES:
        p = os.path.join(STL, name + ".stl")
        if not os.path.exists(p):
            print(f"  [건너뜀] {name}.stl 없음")
            continue
        tri[key] = PR.read_stl(p)
        data[key] = metrics(tri[key])
        print(f"  {key:<3s} {name}  삼각형 {len(tri[key]):,}")

    # ---- 동일 카메라/스케일 렌더 ----
    allv = np.vstack([t.reshape(-1, 3) for t in tri.values()])
    for view, wd in (("SIDE", np.array([-1.0, 0.0, 0.0])),
                     ("ISOMETRIC", np.array([-0.75, -0.62, 0.23]))):
        uu, vv, w = PR.frame(wd)
        pu, pv = allv @ uu, allv @ vv
        lim = (pu.min() - 8, pu.max() + 8, pv.min() - 8, pv.max() + 8)
        for key in tri:
            if key == "W2":
                continue
            fig, ax = plt.subplots(figsize=(9, 9))
            PR.shade(ax, tri[key], uu, vv, w, "#5b7fa6", 1.0)
            ax.set_xlim(lim[0], lim[1]); ax.set_ylim(lim[2], lim[3])
            ax.set_aspect("equal"); ax.axis("off")
            ax.set_title(f"OneGrip Play — GROUND {key}  [{view}]", fontsize=13)
            out = os.path.join(PREVIEW, f"GROUND_{key}_{view}.png")
            fig.savefig(out, dpi=110, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            print("  saved", os.path.relpath(out, LOCAL))

    # ---- 실루엣 비교 1장 ----
    fig, axes = plt.subplots(1, 3, figsize=(21, 7))
    cols = {"W2": "#9aa7b4", "A": "#2b6cb0", "B": "#c05621"}
    for k in data:
        s = data[k]["_sil"]
        axes[0].plot(s[:, 0], s[:, 1], lw=1.6, color=cols[k], alpha=0.55)
        lo = silhouette_low(tri[k])
        axes[0].plot(lo[:, 0], lo[:, 1], lw=2.6, color=cols[k],
                     label=f"{k}  하부: 접지 u={data[k]['ground_u_front_mm']:.1f}  "
                           f"float={data[k]['floating_span_mm']:.1f}mm  "
                           f"최대각={data[k]['max_lower_slope_deg']:.1f}deg")
    axes[0].axhline(0, color="k", lw=1.0)
    axes[0].set_aspect("equal"); axes[0].legend(fontsize=10, loc="upper right")
    axes[0].set_title("SIDE 실루엣 — 굵은선=하부, 옅은선=상부", fontsize=13)
    axes[0].set_xlim(-95, 25)
    axes[0].set_ylim(-4, 145)
    axes[0].set_xlabel("u  [mm]  (왼쪽 = 손목 방향)"); axes[0].set_ylabel("지면 위 높이 [mm]")
    axes[0].grid(alpha=0.3)
    uu, vv, w = PR.frame(np.array([-1.0, 0.0, 0.0]))
    pu, pv = allv @ uu, allv @ vv
    for ax, (k, col) in zip(axes[1:], (("A", "#2b6cb0"), ("B", "#c05621"))):
        if k not in tri:
            continue
        PR.shade(ax, tri[k], uu, vv, w, col, 1.0)
        ax.set_xlim(pu.min() - 8, pu.max() + 8)
        ax.set_ylim(pv.min() - 8, pv.max() + 8)
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(f"Variant {k}  SIDE   L={data[k]['length_Y_mm']:.1f}mm  "
                     f"오버행={data[k]['front_overhang_mm']:+.1f}mm", fontsize=13)
    out = os.path.join(PREVIEW, "GROUND_AB_SIDE_COMPARISON.png")
    fig.savefig(out, dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved", os.path.relpath(out, LOCAL))

    keys = ["length_Y_mm", "width_X_mm", "height_world_mm", "volume_mm3",
            "added_vs_core_mm3", "ground_area_mm2", "ground_u_front_mm",
            "floating_span_mm", "max_lower_slope_deg", "mean_lower_slope_deg",
            "support_area_frac"]
    print(f"\n{'항목':<24s}" + "".join(f"{k:>16s}" for k in data))
    for m in keys:
        print(f"{m:<24s}" + "".join(f"{data[k][m]:16,.3f}" for k in data))
    json.dump({k: {m: v[m] for m in keys} for k, v in data.items()},
              open(os.path.join(REPORTS, "05_ground_variants.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
