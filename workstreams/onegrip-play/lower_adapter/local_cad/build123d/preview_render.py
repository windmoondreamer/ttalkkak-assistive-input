"""로컬 프리뷰 렌더 (§21) — STL 을 읽어 실루엣/음영 뷰를 만든다.

Onshape 미조회. 시스템 python(matplotlib) 으로 실행해도 되고 venv 로 실행해도 된다.
    python lower_adapter/local_cad/build123d/preview_render.py
"""
from __future__ import annotations

import os
import struct
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                           # noqa: E402
from matplotlib.collections import PolyCollection         # noqa: E402

matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL = os.path.dirname(HERE)
PREVIEW = os.path.join(LOCAL, "preview")
STL_DIR = os.path.join(LOCAL, "export", "stl")

UP = np.array([0.0, 0.3420201433256687, 0.9396926207859084])
UH = np.array([0.0, 0.9396926207859084, -0.3420201433256687])
XH = np.array([1.0, 0.0, 0.0])


def read_stl(path):
    with open(path, "rb") as f:
        head = f.read(5)
        f.seek(0)
        if head == b"solid":
            v = []
            for line in f:
                s = line.split()
                if s and s[0] == b"vertex":
                    v.append([float(x) for x in s[1:4]])
            t = np.array(v, dtype=float).reshape(-1, 3, 3)
        else:
            f.seek(80)
            n = struct.unpack("<I", f.read(4))[0]
            t = np.empty((n, 3, 3))
            for i in range(n):
                d = struct.unpack("<12fH", f.read(50))
                t[i] = np.array(d[3:12]).reshape(3, 3)
    return t


def shade(ax, tris, u, v, w, color, alpha=1.0, light=(0.4, -0.6, 0.7)):
    """w = 시선 방향(깊이). 뒤에서 앞으로 그려 은면 처리."""
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(n, axis=1)
    nn = n / np.maximum(ln[:, None], 1e-12)
    facing = nn @ w
    keep = facing < 0                      # 카메라를 향한 면만
    t = tris[keep]
    nn = nn[keep]
    if len(t) == 0:
        return
    depth = t.mean(1) @ w
    order = np.argsort(-depth)
    t, nn = t[order], nn[order]
    L = np.array(light, dtype=float)
    L /= np.linalg.norm(L)
    sh = np.clip(0.35 + 0.65 * np.abs(nn @ L), 0, 1)
    base = np.array(matplotlib.colors.to_rgb(color))
    cols = np.clip(base[None, :] * sh[:, None], 0, 1)
    poly = np.stack([t.reshape(-1, 3) @ u, t.reshape(-1, 3) @ v], 1).reshape(-1, 3, 2)
    ax.add_collection(PolyCollection(poly, facecolors=cols, edgecolors="none",
                                     alpha=alpha, linewidths=0))


VIEWS = {
    "ISOMETRIC": (np.array([-0.75, -0.62, 0.23]), None),
    "SIDE":      (np.array([-1.0, 0.0, 0.0]), None),
    "FRONT":     (-UH, None),
    "TOP":       (-UP, None),
    "BOTTOM":    (UP, None),
}


def frame(wdir):
    w = np.array(wdir, dtype=float)
    w /= np.linalg.norm(w)
    up = UP if abs(w @ UP) < 0.95 else XH
    u = np.cross(up, w)
    u /= np.linalg.norm(u)
    v = np.cross(w, u)
    return u, v, w


def render(sets, name, wdir, title, section=None):
    u, v, w = frame(wdir)
    fig, ax = plt.subplots(figsize=(9, 9))
    for tris, color, alpha in sets:
        t = tris
        if section is not None:
            axis, val, keep_neg = section
            c = t.mean(1)[:, axis]
            t = t[c < val] if keep_neg else t[c > val]
        shade(ax, t, u, v, w, color, alpha)
    allp = np.vstack([s[0].reshape(-1, 3) for s in sets])
    pu, pv = allp @ u, allp @ v
    m = 8
    ax.set_xlim(pu.min() - m, pu.max() + m)
    ax.set_ylim(pv.min() - m, pv.max() + m)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=13)
    os.makedirs(PREVIEW, exist_ok=True)
    p = os.path.join(PREVIEW, f"{name}.png")
    fig.savefig(p, dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved", os.path.relpath(p, LOCAL))


def main():
    stl = os.path.join(STL_DIR, "ERGO_HOUSING_W2.stl")
    if not os.path.exists(stl):
        print("STL 없음:", stl)
        return 2
    house = read_stl(stl)
    print(f"ERGO_HOUSING_W2.stl  삼각형 {len(house):,}")
    sets = [(house, "#5b7fa6", 1.0)]

    extra = []
    for nm, col in (("BOTTOM_CARRIER_REFERENCE", "#2b6cb0"),
                    ("STOCK_GIMBAL_IN_GRIP", "#2e9e5b"),
                    ("ONEGRIP_IN_GRIP", "#9aa7b4")):
        p = os.path.join(STL_DIR, nm + ".stl")
        if os.path.exists(p):
            extra.append((read_stl(p), col, 1.0))

    for name, (wd, _s) in VIEWS.items():
        render(sets + extra, name, wd, f"OneGrip Play — ERGO_HOUSING_W2  [{name}]")

    # CUTAWAY: X<0 절반 제거해 내부 매립 상태를 보인다
    render(sets + extra, "CUTAWAY", np.array([-0.75, -0.62, 0.23]),
           "CUTAWAY (X<0 제거) — 스톡 짐벌 매립 상태",
           section=(0, 0.0, False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
