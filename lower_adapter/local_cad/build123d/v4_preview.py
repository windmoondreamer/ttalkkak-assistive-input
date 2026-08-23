"""§12 V4 프리뷰 7종 + V3/V4 공동 비교.

전 부품 **전역 깊이 정렬** 렌더 (부품별로 그리면 뒤 부품이 덧칠된다).
FRONT 는 팔받침 쪽(-Y)에서 본 방향이다 — `w = -UH` 는 반대쪽이라 이름을 믿으면 안 된다.
"""
from __future__ import annotations
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                          # noqa: E402
from matplotlib.collections import PolyCollection        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import preview_render as PR                              # noqa: E402

matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False
LOCAL = os.path.dirname(HERE)
STL = os.path.join(LOCAL, "export", "stl")
PREVIEW = os.path.join(LOCAL, "preview")
UP, UH = PR.UP, PR.UH
BASE = "ERGO_HOUSING_25_WRAP_FINAL_V4"

PARTS = [(BASE, "#5b7fa6"), ("BOTTOM_CARRIER_FINAL", "#2b6cb0"),
         ("STOCK_GIMBAL_IN_GRIP", "#2e9e5b"), ("ONEGRIP_IN_GRIP", "#9aa7b4")]

VIEWS = {
    "SIDE": np.array([-1.0, 0, 0]),
    "ISOMETRIC": UH * 0.70 - UP * 0.45 - np.array([0.55, 0.0, 0.0]),
    "TOP": -UP,
    "FRONT_ARMSIDE": UH,          # 팔받침 쪽에서 뒤를 본다
    "REAR": -UH,
    "BOTTOM": UP,
}


def collect(parts, section=None):
    T, C = [], []
    for nm, col in parts:
        p = os.path.join(STL, nm + ".stl")
        if not os.path.exists(p):
            print("   없음:", nm)
            continue
        t = PR.read_stl(p)
        if section is not None:
            ax, val, keep_neg = section
            vx = t[:, :, ax]
            t = t[(vx < val).all(1)] if keep_neg else t[(vx > val).all(1)]
        if len(t) == 0:
            continue
        T.append(t)
        C.append(np.repeat([matplotlib.colors.to_rgb(col)], len(t), axis=0))
    return np.vstack(T), np.vstack(C)


def draw(name, wdir, title, parts=None, section=None):
    parts = parts or PARTS
    u, v, w = PR.frame(np.array(wdir, dtype=float))
    T, C = collect(parts, section)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    nn = n / np.maximum(np.linalg.norm(n, axis=1)[:, None], 1e-12)
    k = (nn @ w) < 0
    T, C, nn = T[k], C[k], nn[k]
    o = np.argsort(-(T.mean(1) @ w))            # 전역 정렬
    T, C, nn = T[o], C[o], nn[o]
    L = np.array([0.4, -0.6, 0.7])
    L /= np.linalg.norm(L)
    sh = np.clip(0.35 + 0.65 * np.abs(nn @ L), 0, 1)
    poly = np.stack([T.reshape(-1, 3) @ u, T.reshape(-1, 3) @ v], 1).reshape(-1, 3, 2)
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.add_collection(PolyCollection(poly, facecolors=np.clip(C * sh[:, None], 0, 1),
                                     edgecolors="none", linewidths=0))
    pu, pv = poly[:, :, 0].ravel(), poly[:, :, 1].ravel()
    ax.set_xlim(pu.min() - 8, pu.max() + 8)
    ax.set_ylim(pv.min() - 8, pv.max() + 8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=13)
    p = os.path.join(PREVIEW, name + ".png")
    fig.savefig(p, dpi=115, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved", os.path.relpath(p, LOCAL))


def main():
    for k, wd in VIEWS.items():
        draw(f"V4_{k}", wd, f"OneGrip Play — 25deg WRAP + ±15deg motion clearance  [{k}]")
    draw("V4_CUTAWAY", UH * 0.70 - UP * 0.45 - np.array([0.55, 0.0, 0.0]),
         "CUTAWAY (X<0 제거) — 스톡짐벌(초록) / 캐리어(진파랑) / 하우징(파랑)",
         section=(0, 0.0, False))
    # V3 vs V4 공동 비교: 절삭된 체적만 주황으로 강조
    cmp_parts = [("ERGO_HOUSING_25_WRAP_FINAL_V4", "#5b7fa6"),
                 ("MOTION15_REMOVED", "#e0761a"),
                 ("STOCK_GIMBAL_IN_GRIP", "#2e9e5b")]
    if os.path.exists(os.path.join(STL, "MOTION15_REMOVED.stl")):
        draw("V3_V4_CAVITY_COMPARE", UH * 0.70 - UP * 0.45 - np.array([0.55, 0.0, 0.0]),
             "V3 -> V4 절삭 체적 (주황) — ±15deg 모션 확보분 44,885 mm3",
             parts=cmp_parts, section=(0, 0.0, False))
    else:
        print("  MOTION15_REMOVED.stl 없음 - 비교도 건너뜀")
    return 0


if __name__ == "__main__":
    sys.exit(main())
