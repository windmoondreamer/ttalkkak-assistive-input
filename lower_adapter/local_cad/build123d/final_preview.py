"""최종 B 프리뷰 6종 (§10). 동일 카메라/스케일. Onshape 미조회.

    python lower_adapter/local_cad/build123d/final_preview.py
"""
from __future__ import annotations

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
UP = PR.UP
UH = PR.UH

VIEWS = {
    "SIDE":      np.array([-1.0, 0.0, 0.0]),
    "ISOMETRIC": np.array([-0.75, -0.62, 0.23]),
    "TOP":       -UP,
    "FRONT":     -UH,
    "BOTTOM":    UP,
}


def main():
    house = PR.read_stl(os.path.join(STL, "ERGO_HOUSING_W2_FINAL.stl"))
    print(f"ERGO_HOUSING_W2_FINAL.stl  삼각형 {len(house):,}")
    sets = [(house, "#5b7fa6", 1.0)]
    for nm, col in (("BOTTOM_CARRIER_FINAL", "#2b6cb0"),
                    ("STOCK_GIMBAL_IN_GRIP", "#2e9e5b"),
                    ("ONEGRIP_IN_GRIP", "#9aa7b4")):
        p = os.path.join(STL, nm + ".stl")
        if os.path.exists(p):
            sets.append((PR.read_stl(p), col, 1.0))
            print(f"  + {nm}")
    allp = np.vstack([s[0].reshape(-1, 3) for s in sets])

    def draw(name, wdir, title, section=None, only_house=False):
        u, v, w = PR.frame(wdir)
        fig, ax = plt.subplots(figsize=(10, 10))
        use = sets[:1] if only_house else sets
        for tris, color, alpha in use:
            t = tris
            if section is not None:
                axis, val, keep_neg = section
                c = t.mean(1)[:, axis]
                t = t[c < val] if keep_neg else t[c > val]
            if len(t):
                PR.shade(ax, t, u, v, w, color, alpha)
        pu, pv = allp @ u, allp @ v
        ax.set_xlim(pu.min() - 8, pu.max() + 8)
        ax.set_ylim(pv.min() - 8, pv.max() + 8)
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(title, fontsize=13)
        p = os.path.join(PREVIEW, name + ".png")
        fig.savefig(p, dpi=115, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print("  saved", os.path.relpath(p, LOCAL))

    for k, wd in VIEWS.items():
        draw(f"FINAL_B_{k}", wd,
             f"OneGrip Play — ERGO_HOUSING_W2_FINAL (GROUND B)  [{k}]")
    draw("FINAL_B_CUTAWAY", np.array([-0.75, -0.62, 0.23]),
         "CUTAWAY (X<0 제거) — 스톡 짐벌 / 코어 / 캐리어 / 최종 외피",
         section=(0, 0.0, False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
