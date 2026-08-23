"""얇은 살 판독의 성격 판별 — 접선 쐐기 vs 진짜 리브.

접선으로 만나는 두 면 사이에서는 살두께가 연속적으로 0 으로 수렴한다.
그런 구간은 **선(線)** 을 이루고, 조금만 옆으로 가면 급격히 두꺼워진다.
진짜 리브는 **면(面)** 을 이루고 넓은 영역에서 계속 얇다.

각 얇은 지점의 3mm 이웃에서 살두께 분포를 재서 둘을 가른다.
"""
from __future__ import annotations
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402
import build123d as bd                                    # noqa: E402
from OCP.BRepTools import BRepTools                       # noqa: E402
import v4_audit as VA                                     # noqa: E402


def load_tris(name, tol=0.03):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    f = os.path.join(P.EXPORT_STL, "_tc.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.2)
    T = G.read_stl_tris(f)
    os.remove(f)
    return T


def cluster(pts, cell=3.0):
    """격자 기반 연결 성분. 인접 27칸을 잇는다."""
    if len(pts) == 0:
        return []
    key = np.floor(np.asarray(pts) / cell).astype(int)
    buckets = {}
    for i, k in enumerate(map(tuple, key)):
        buckets.setdefault(k, []).append(i)
    seen = set()
    out = []
    for k in buckets:
        if k in seen:
            continue
        stack = [k]
        seen.add(k)
        members = []
        while stack:
            c = stack.pop()
            members.extend(buckets[c])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        n = (c[0] + dx, c[1] + dy, c[2] + dz)
                        if n in buckets and n not in seen:
                            seen.add(n)
                            stack.append(n)
        out.append(members)
    out.sort(key=len, reverse=True)
    return out


def main():
    names = sys.argv[1:] or ["ERGO_HOUSING_25_WRAP_W134_BLEND",
                             "ERGO_HOUSING_25_WRAP_FINAL_V4"]
    for nm in names:
        T = load_tris(nm)
        allg = []
        for ax in (0, 1, 2):
            allg += VA.slabs(T, ax, step=1.5, thr=2.5)
        gs = np.array([g for g, p in allg])
        pts = np.array([p for g, p in allg])
        thin = gs < 1.5
        print("")
        print(f"[{nm}]")
        print(f"  slabs <2.5mm {len(allg)}   <1.5mm {int(thin.sum())}")
        if thin.sum() == 0:
            continue
        cl = cluster(pts[thin], cell=3.0)
        tg = gs[thin]
        tp = pts[thin]
        print(f"  얇은 지점 군집 {len(cl)}개")
        print("    크기  최소두께   확장 X x Y x Z (mm)          성격")
        for m in cl[:8]:
            q = tp[m]
            ext = q.max(0) - q.min(0)
            # 선형(접선) 이면 한 방향으로만 길다. 면적형(리브)이면 두 방향이 넓다.
            e = np.sort(ext)[::-1]
            kind = "접선(선형)" if e[1] < 4.0 else "면적형(리브 의심)"
            c = q.mean(0)
            print(f"    {len(m):4d}  {tg[m].min():7.3f}   "
                  f"{ext[0]:6.1f} x {ext[1]:6.1f} x {ext[2]:6.1f}   {kind}")
            print(f"          중심 ({c[0]:7.2f},{c[1]:7.2f},{c[2]:8.2f})  "
                  f"덱기준 dz {c[2]-(-61.878507):+7.2f}   "
                  f"X[{q[:,0].min():7.2f},{q[:,0].max():7.2f}] "
                  f"Y[{q[:,1].min():7.2f},{q[:,1].max():7.2f}] "
                  f"Z[{q[:,2].min():8.2f},{q[:,2].max():8.2f}]")
        big = [m for m in cl if np.sort(tp[m].max(0) - tp[m].min(0))[::-1][1] >= 4.0]
        print(f"  -> 면적형(리브 의심) 군집 {len(big)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
