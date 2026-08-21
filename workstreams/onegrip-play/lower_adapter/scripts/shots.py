"""하부 어댑터 뷰 생성 (GET only).

    python lower_adapter/scripts/shots.py

1) Onshape shadedviews 로 실제 CAD 렌더 (isometric / side / front)
2) 로컬 matplotlib 로 그립+어댑터 측면 합성도 (20도 관계를 직접 보여준다)

출력: lower_adapter/cad_dump/shot_*.png
"""
import base64
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from onshape.client import BASE, session          # noqa: E402
from onshape import write_client as wc            # noqa: E402

OUT = os.path.join(ROOT, "lower_adapter", "cad_dump")
SHARED = os.path.join(ROOT, "cad_dump")
C = json.load(io.open(os.path.join(OUT, "adapter_constants.json"), encoding="utf-8"))
UP = np.array(C["UP_LOCAL"])
E2 = np.array(C["E2"])
E1 = np.array([1.0, 0.0, 0.0])
BASE_PT = np.array(C["BASE_PT"])
FLANGE_Z = C["FLANGE_Z"]
PARTS = ["CRADLE", "WEDGE", "RING_F", "RING_B"]


def view_matrix(right, up, toward):
    m = np.zeros((3, 4))
    m[0, :3], m[1, :3], m[2, :3] = right, up, toward
    return ",".join("%.6f" % v for v in m.reshape(-1))


def shaded(name, vm, w=1400, h=1000):
    t = json.load(io.open(os.path.join(OUT, "adapter_target.json"), encoding="utf-8"))
    r = session().get(
        f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{t['ps_eid']}/shadedviews",
        params={"viewMatrix": vm, "outputHeight": h, "outputWidth": w,
                "pixelSize": 0, "edges": "show", "showAllParts": "true",
                "useAntiAliasing": "true", "configuration": "default"}, timeout=300)
    if r.status_code != 200:
        print(f"  {name}: HTTP {r.status_code} {r.text[:160]}")
        return
    imgs = r.json().get("images", [])
    if not imgs:
        print(f"  {name}: 이미지 없음")
        return
    p = os.path.join(OUT, f"shot_{name}.png")
    with open(p, "wb") as f:
        f.write(base64.b64decode(imgs[0]))
    print(f"  {name}: {p}  ({os.path.getsize(p)} bytes)")


def load(name, shared=False):
    d = SHARED if shared else OUT
    return np.asarray(json.load(io.open(os.path.join(d, f"mesh_{name}.json"),
                                        encoding="utf-8"))["tris"], dtype=float)


def composite():
    """월드 좌표(수평 기준면이 수평으로 보이는) 측면 합성도."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    def to_world(V):
        d = V - BASE_PT
        return np.column_stack([d @ E2, d @ UP])       # (수평, 수직)

    fig, ax = plt.subplots(figsize=(9, 11), dpi=140)
    grip = np.vstack([load("INDEX_FINAL_JaD", True), load("INDEX_FINAL_JfD", True)])
    sets = [("OneGrip (frozen, unmodified)", grip, "#9aa7b4", 0.55),
            ("CRADLE", load("CRADLE"), "#2f7bd6", 0.95),
            ("WEDGE", load("WEDGE"), "#d1682a", 0.95),
            ("CLAMP RING", np.vstack([load("RING_F"), load("RING_B")]), "#2aa06a", 0.95)]
    from matplotlib.collections import PolyCollection
    for zi, (label, T, col, a) in enumerate(sets):
        tri = np.stack([to_world(T[:, 0]), to_world(T[:, 1]), to_world(T[:, 2])], axis=1)
        ax.add_collection(PolyCollection(tri, facecolors=col, edgecolors="none",
                                         alpha=a, zorder=2 + zi))
        ax.plot([], [], color=col, lw=6, alpha=a, label=label)   # 범례용

    # ---- 주석: 전부 실제 방향 벡터를 투영해서 그린다 ----
    seatO = to_world(np.array([[0.0, C["AXIS_Y"], FLANGE_Z]]))[0]
    # 착좌면 in-plane 방향 = grip +Y 를 투영한 것
    dSeat = np.array([np.dot(np.array([0, 1.0, 0]), E2), np.dot(np.array([0, 1.0, 0]), UP)])
    # 중심축 방향 = grip +Z 를 투영한 것
    dAxis = np.array([np.dot(np.array([0, 0, 1.0]), E2), np.dot(np.array([0, 0, 1.0]), UP)])

    ax.axhline(0, color="#111", lw=2.2, zorder=6)
    L = 52
    ax.plot([seatO[0] - L * dSeat[0], seatO[0] + L * dSeat[0]],
            [seatO[1] - L * dSeat[1], seatO[1] + L * dSeat[1]],
            color="#1565c0", lw=1.8, ls="--", zorder=7)
    ax.plot([seatO[0], seatO[0] + 92 * dAxis[0]], [seatO[1], seatO[1] + 92 * dAxis[1]],
            color="#c0392b", lw=2.0, zorder=7)
    ax.text(seatO[0] + 96 * dAxis[0] - 6, seatO[1] + 96 * dAxis[1],
            "GRIP AXIS", fontsize=10, color="#c0392b", ha="right")
    ax.text(seatO[0] + (L + 3) * dSeat[0], seatO[1] + (L + 3) * dSeat[1] - 3,
            "TILT SURFACE\n(seat plane)", fontsize=9, color="#1565c0")
    # 90도 사각 표시
    q = 9.0
    p0 = seatO + q * dSeat
    p1 = seatO + q * dSeat + q * dAxis
    p2 = seatO + q * dAxis
    ax.plot([p0[0], p1[0], p2[0]], [p0[1], p1[1], p2[1]], color="#c0392b", lw=1.2, zorder=7)
    ax.text(seatO[0] + 12 * (dSeat[0] + dAxis[0]) / 2, seatO[1] + 12 * (dSeat[1] + dAxis[1]) / 2,
            "90.000°", fontsize=10, color="#c0392b")
    # 20도 (수평 기준선 대비 착좌면)
    ax.plot([seatO[0], seatO[0] + 40], [seatO[1], seatO[1]], color="#1565c0",
            lw=1.0, ls=":", zorder=7)
    ax.text(seatO[0] + 22, seatO[1] - 5.5, "20.000°", fontsize=10, color="#1565c0")
    # 스택 높이
    xs = seatO[0] + 62
    ax.annotate("", xy=(xs, seatO[1]), xytext=(xs, 0),
                arrowprops=dict(arrowstyle="<->", color="#555"))
    ax.text(xs + 2, seatO[1] / 2, "stack\n%.1f mm" % C["STACK_H"], fontsize=9, color="#555")

    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_xlim(-135, 95)
    ax.set_ylim(-14, 160)
    ax.set_xlabel("world horizontal  [mm]    (+ = uphill = +Y grip)")
    ax.set_ylabel("world vertical  [mm]")
    ax.set_title("OneGrip Play — 20° modular lower adapter (side view, world frame)\n"
                 "GRIP AXIS ⊥ TILT SURFACE = 90.000°,   TILT SURFACE ∠ horizontal = 20.000°",
                 fontsize=11)
    ax.text(-133, -11, "HORIZONTAL GIMBAL INTERFACE (world horizontal, wedge underside)",
            fontsize=9, color="#111")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(alpha=0.25)
    p = os.path.join(OUT, "shot_composite_side.png")
    fig.tight_layout()
    fig.savefig(p)
    print(f"  composite: {p}")


if __name__ == "__main__":
    print("Onshape shadedviews:")
    shaded("side", view_matrix(E2, UP, E1))
    shaded("front", view_matrix(E1, UP, -E2))
    v = E1 - E2 + UP
    v /= np.linalg.norm(v)
    rgt = np.cross(UP, v)
    rgt /= np.linalg.norm(rgt)
    shaded("iso", view_matrix(rgt, np.cross(v, rgt), v))
    print("local composite:")
    composite()
