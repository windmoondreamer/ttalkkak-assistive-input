"""§7 SUPPORT MAP + 제거 방향.

face 색: 초록 = no support(A) / 노랑 = bridge·conditional(B) / 빨강 = support(C,D)
         자홍 = TRAPPED(E)  — 현재 0

제거 방향은 **측지 거리**로 정한다. bbox 면 전체를 seed 로 쓰면 세 opening 이
모두 같은 외부 공간이라 전부 "연결"로 나와 구분이 안 된다 (실측). 각 opening
에서 free 공간을 따라 BFS 해 chunk 에 먼저 닿는 쪽을 권장 경로로 본다.
"""
from __future__ import annotations
import os
import sys
import json
import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODE = sys.argv[1] if len(sys.argv) > 1 else "all"
# venv 에는 matplotlib 이 없고 시스템 python 에는 build123d 가 없다.
# ROUTES 단계(venv)와 DRAW 단계(시스템 python)를 나눈다.
if MODE in ("routes", "all"):
    import parameters as P                               # noqa: E402
    import geometry_utils as G                           # noqa: E402
    import build123d as bd                               # noqa: E402
    from OCP.BRepTools import BRepTools                  # noqa: E402
    from scipy import ndimage as ndi                     # noqa: E402
if MODE in ("draw", "all"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt                      # noqa: E402
    from matplotlib.collections import PolyCollection    # noqa: E402
    matplotlib.rcParams["font.family"] = "Malgun Gothic"
    matplotlib.rcParams["axes.unicode_minus"] = False
LOCAL = os.path.dirname(HERE)
ADAPTER = os.path.dirname(LOCAL)
PREVIEW = os.path.join(LOCAL, "preview")
VOX = 2.5
PAD = 8.0

COLOR = {"A": "#2e9e5b", "B": "#e8c33a", "C": "#d64545", "D": "#d64545",
         "E": "#c13ec1"}
PARTS = {"MAIN": ("HOUSING_V4_MAIN_PRINT", -90.0),
         "ARMREST": ("HOUSING_V4_ARMREST_PRINT", -90.0)}


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def load_tris(name, tol=0.05):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    f = os.path.join(P.EXPORT_STL, "_sm.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.3)
    T = G.read_stl_tris(f)
    os.remove(f)
    return T


def frame(w):
    w = np.array(w, float)
    w /= np.linalg.norm(w)
    up = np.array([0.0, 0.0, 1.0])
    if abs(w @ up) > 0.95:
        up = np.array([0.0, 1.0, 0.0])
    u = np.cross(up, w)
    u /= np.linalg.norm(u)
    v = np.cross(w, u)
    return u, v, w


def geodesic_routes(Tp, chunks_needed=True):
    """opening 별 측지 BFS 로 support chunk 의 권장 제거 경로를 구한다."""
    V = Tp.reshape(-1, 3)
    lo = V.min(0) - PAD
    hi = V.max(0) + PAD
    dims = np.ceil((hi - lo) / VOX).astype(int)
    gx = lo[0] + (np.arange(dims[0]) + 0.5) * VOX
    gy = lo[1] + (np.arange(dims[1]) + 0.5) * VOX
    gz = lo[2] + (np.arange(dims[2]) + 0.5) * VOX
    X, Y, Z = np.meshgrid(gx, gy, gz, indexing="ij")
    pts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    solid = G.mesh_inside(Tp, pts).reshape(dims)
    free = ~solid
    above = np.cumsum(solid[:, :, ::-1], axis=2)[:, :, ::-1] > 0
    below = np.cumsum(solid, axis=2) > 0
    sup = free & above & below
    ero = ndi.binary_erosion(free, np.ones((3, 3, 3)), iterations=1)
    seeds = {}
    for key, sl in (("DECK (-Y)", (slice(None), slice(0, 2), slice(None))),
                    ("CARRIER/LOWER (+Y)", (slice(None), slice(-2, None), slice(None))),
                    ("SPLIT/BED (z=0)", (slice(None), slice(None), slice(0, 2)))):
        m = np.zeros(dims, bool)
        m[sl] = True
        seeds[key] = m & ero
    lab, n = ndi.label(sup, structure=np.ones((3, 3, 3)))
    sizes = ndi.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
    keep = [i + 1 for i in range(n) if sizes[i] * VOX ** 3 > 2000.0]
    st = np.ones((3, 3, 3))
    out = []
    for li in keep:
        cm = ndi.binary_dilation(lab == li, st)
        best, bestd = None, 10 ** 9
        for key, sd in seeds.items():
            cur = sd.copy()
            d = 0
            while d < 400:
                if (cur & cm).any():
                    break
                nxt = ndi.binary_dilation(cur, st) & ero
                if nxt.sum() == cur.sum():
                    d = 10 ** 9
                    break
                cur = nxt
                d += 1
            if d < bestd:
                best, bestd = key, d
        idx = np.argwhere(lab == li)
        ctr = lo + (idx.mean(0) + 0.5) * VOX
        if best is None or bestd >= 10 ** 9:
            best, bestd = "NARROW (<2mm neck)", -1
        out.append({"label": int(li),
                    "volume_mm3": float((lab == li).sum() * VOX ** 3),
                    "print_centroid": ctr.tolist(),
                    "route": best, "geodesic_steps": int(bestd),
                    "geodesic_mm": float(bestd * VOX)})
    out.sort(key=lambda r: -r["volume_mm3"])
    return out


ARROW = {"DECK (-Y)": (0.0, -1.0), "CARRIER/LOWER (+Y)": (0.0, 1.0),
         "SPLIT/BED (z=0)": (0.0, -1.0)}


def draw(nm, Tp, cls, routes):
    views = [("ISO", np.array([-0.72, -0.50, -0.48])),
             ("SIDE (-X)", np.array([-1.0, 0.0, 0.0]))]
    fig, axes = plt.subplots(1, 2, figsize=(15, 8.5))
    for ax, (lab, wd) in zip(axes, views):
        u, v, w = frame(wd)
        n = np.cross(Tp[:, 1] - Tp[:, 0], Tp[:, 2] - Tp[:, 0])
        mg = np.linalg.norm(n, axis=1)
        nn = n / np.maximum(mg[:, None], 1e-12)
        k = (nn @ w) < 0
        T2, c2, n2 = Tp[k], cls[k], nn[k]
        o = np.argsort(-(T2.mean(1) @ w))
        T2, c2, n2 = T2[o], c2[o], n2[o]
        L = np.array([0.4, -0.6, 0.7])
        L /= np.linalg.norm(L)
        sh = np.clip(0.45 + 0.55 * np.abs(n2 @ L), 0, 1)
        base = np.array([matplotlib.colors.to_rgb(COLOR[c]) for c in c2])
        poly = np.stack([T2.reshape(-1, 3) @ u, T2.reshape(-1, 3) @ v],
                        1).reshape(-1, 3, 2)
        ax.add_collection(PolyCollection(poly, facecolors=np.clip(base * sh[:, None], 0, 1),
                                         edgecolors="none", linewidths=0))
        pu, pv = poly[:, :, 0].ravel(), poly[:, :, 1].ravel()
        ax.set_xlim(pu.min() - 10, pu.max() + 10)
        ax.set_ylim(pv.min() - 10, pv.max() + 10)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{nm}  [{lab}]", fontsize=12)
        for r in routes[:6]:
            c = np.array(r["print_centroid"])
            a2 = np.array([c @ u, c @ v])
            d3 = np.zeros(3)
            if r["route"] and r["route"].startswith("DECK"):
                d3[1] = -1
            elif r["route"] and r["route"].startswith("CARRIER"):
                d3[1] = 1
            else:
                d3[2] = -1
            d2 = np.array([d3 @ u, d3 @ v])
            if np.linalg.norm(d2) < 1e-6:
                continue
            d2 = d2 / np.linalg.norm(d2) * 34
            ax.annotate("", xy=tuple(a2 + d2), xytext=tuple(a2),
                        arrowprops=dict(arrowstyle="-|>", color="#1b3a6b", lw=2.2))
            ax.text(*(a2 + d2 * 1.12), f"{r['volume_mm3']/1000:.1f}cm3\n{r['route']}",
                    fontsize=8, color="#1b3a6b", ha="center")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=COLOR["A"], label="A 초록 = no support"),
                        Patch(color=COLOR["B"], label="B 노랑 = bridge / conditional"),
                        Patch(color=COLOR["C"], label="C·D 빨강 = support required"),
                        Patch(color=COLOR["E"], label="E 자홍 = TRAPPED (0)")],
               loc="lower center", ncol=4, fontsize=10, frameon=False)
    fig.suptitle(f"SUPPORT MAP — {nm}  (CUT FACE DOWN, 화살표 = 제거 방향)",
                 fontsize=13)
    p = os.path.join(PREVIEW, f"SUPPORT_MAP_{nm}.png")
    fig.savefig(p, dpi=115, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved", os.path.relpath(p, LOCAL))


RJ = os.path.join(LOCAL, "reports", "15_support_routes.json")


def main():
    if MODE in ("routes", "all"):
        out = {}
        for nm, (fn, ang) in PARTS.items():
            Tp = np.load(os.path.join(ADAPTER, "cad_dump", f"support_tris_{nm}.npy"))
            print(f"[{nm}] 삼각형 {len(Tp):,}")
            routes = geodesic_routes(Tp)
            print("  chunk 권장 제거 경로 (측지)")
            for r in routes[:6]:
                print(f"    {r['volume_mm3']/1000:8.2f} cm3   {r['route']:<22} "
                      f"측지 {r['geodesic_mm']:6.1f} mm"
                      if r["geodesic_mm"] >= 0 else "측지 도달불가(2mm 침식)")
            out[nm] = routes
        json.dump(out, open(RJ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("saved: reports/15_support_routes.json")
    if MODE in ("draw", "all"):
        allr = json.load(open(RJ, encoding="utf-8"))
        for nm, (fn, ang) in PARTS.items():
            Tp = np.load(os.path.join(ADAPTER, "cad_dump", f"support_tris_{nm}.npy"))
            cls = np.load(os.path.join(ADAPTER, "cad_dump", f"support_cls_{nm}.npy"))
            draw(nm, Tp, cls, allr[nm])
    return 0


if __name__ == "__main__":
    sys.exit(main())
