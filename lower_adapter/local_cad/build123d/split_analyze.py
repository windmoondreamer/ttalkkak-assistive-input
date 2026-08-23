"""§2 분할 위치 탐색 (읽기 전용).

V4 를 Y 방향으로 훑어 단면 성질을 재고, P1S build volume 과 굽힘 모멘트를
동시에 만족하는 분할 Y 를 찾는다. CAD 쓰기 0건.
"""
from __future__ import annotations
import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402
import build123d as bd                                    # noqa: E402
from OCP.BRepTools import BRepTools                       # noqa: E402

LOCAL = os.path.dirname(HERE)
DECK = -61.878507
UP = np.array(P.FROZEN_UP_LOCAL)
UH = np.array(P.FROZEN_U_HAT)
GH = P.FROZEN_GROUND_WORLD_H
SRC = "ERGO_HOUSING_25_WRAP_FINAL_V4"

# Bambu Lab P1S
BUILD = 256.0
TARGET = 235.0          # 21 mm margin


def load():
    s = bd.import_step(os.path.join(P.EXPORT_STEP, SRC + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    return sh


def tris(sh, tol=0.05):
    f = os.path.join(P.EXPORT_STL, "_sp.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.3)
    T = G.read_stl_tris(f)
    os.remove(f)
    return T


def section_at(T, y, half=0.75):
    V = T.reshape(-1, 3)
    m = np.abs(V[:, 1] - y) < half
    return V[m]


def solid_span(T, y, x, ax=2):
    """(y,x) 에서 Z 광선 교차 -> 재료 구간 목록."""
    d = np.zeros(3)
    d[ax] = 1.0
    v0, v1, v2 = T[:, 0], T[:, 1], T[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    pv = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, pv)
    m = np.abs(det) > 1e-12
    inv = np.zeros(len(T))
    inv[m] = 1.0 / det[m]
    o = np.array([x, y, -400.0])
    tv = o - v0
    u = np.einsum("ij,ij->i", tv, pv) * inv
    qv = np.cross(tv, e1)
    w = np.einsum("j,ij->i", d, qv) * inv
    t = np.einsum("ij,ij->i", e2, qv) * inv
    ok = m & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 0)
    return np.sort(np.unique(np.round(-400.0 + t[ok], 3)))


def main():
    sh = load()
    T = tris(sh)
    b = sh.bounding_box()
    print("=== V4 원본 ===")
    print(f"  bbox  X[{float(b.min.X):8.3f},{float(b.max.X):8.3f}] "
          f"Y[{float(b.min.Y):9.3f},{float(b.max.Y):8.3f}] "
          f"Z[{float(b.min.Z):9.3f},{float(b.max.Z):8.3f}]")
    print(f"  size  {float(b.size.X):.3f} x {float(b.size.Y):.3f} x {float(b.size.Z):.3f}")
    print(f"  volume {float(sh.volume):,.3f} mm3")
    y0, y1 = float(b.min.Y), float(b.max.Y)

    print("")
    print("=== Y 별 단면 (X 폭 / Z 범위 / 재료 구간 수 @X=0) ===")
    print("     Y      X폭     Z범위(min..max)     두께(Z)   재료구간@X=0   비고")
    rows = []
    for y in np.arange(np.ceil(y0) + 2, y1 - 2, 5.0):
        s = section_at(T, float(y))
        if len(s) < 20:
            continue
        xr = s[:, 0].max() - s[:, 0].min()
        zmin, zmax = s[:, 2].min(), s[:, 2].max()
        sp = solid_span(T, float(y), 0.0)
        nseg = len(sp) // 2
        rows.append((float(y), xr, zmin, zmax, nseg))
    for y, xr, zmin, zmax, nseg in rows:
        note = ""
        if -150 <= y <= -125:
            note = "  <- 초기 탐색 구간"
        if nseg == 1:
            note += "  통짜"
        print(f"  {y:7.1f}  {xr:7.2f}  {zmin:8.2f}..{zmax:8.2f}  {zmax - zmin:7.2f}"
              f"  {nseg:6d}{note}")

    print("")
    print("=== 분할 후보별 두 조각 bbox (원좌표계) ===")
    print("   split Y    FRONT (X x Y x Z)              MAIN (X x Y x Z)")
    cand = {}
    V = T.reshape(-1, 3)
    for ys in np.arange(-150.0, -119.9, 2.5):
        f = V[V[:, 1] <= ys]
        m = V[V[:, 1] >= ys]
        if len(f) < 100 or len(m) < 100:
            continue
        fb = f.max(0) - f.min(0)
        mb = m.max(0) - m.min(0)
        cand[float(ys)] = (fb.tolist(), mb.tolist())
        print(f"   {ys:8.1f}   {fb[0]:6.1f} x {fb[1]:6.1f} x {fb[2]:6.1f}"
              f"        {mb[0]:6.1f} x {mb[1]:6.1f} x {mb[2]:6.1f}")

    print("")
    print("=== CUT FACE DOWN 배치 시 인쇄 bbox ===")
    print("  분할면(등Y 평면)을 베드에 놓으면 원래 Y 가 Z 로 선다.")
    print("   split Y    FRONT  W x D x H(=Y길이)     MAIN  W x D x H(=Y길이)   판정")
    for ys, (fb, mb) in cand.items():
        fw, fd, fh = fb[0], fb[2], fb[1]
        mw, md, mh = mb[0], mb[2], mb[1]
        ok = max(fw, fd, fh) <= TARGET and max(mw, md, mh) <= TARGET
        print(f"   {ys:8.1f}   {fw:6.1f} x {fd:6.1f} x {fh:6.1f}"
              f"      {mw:6.1f} x {md:6.1f} x {mh:6.1f}   "
              f"{'OK' if ok else 'OVER'}")

    print("")
    print("=== 팔받침 root / 굽힘 기준 ===")
    hb_front = -81.8    # 하우징 본체 앞끝 (팔받침 램프가 붙는 root)
    print(f"  하우징 본체 앞끝(= 팔받침 root)   Y = {hb_front:.1f}")
    print(f"  팔받침 앞끝                        Y = {y0:.1f}")
    print(f"  팔받침 길이                        {hb_front - y0:.1f} mm")
    print("  root 에서 자르면 굽힘 모멘트 최대 지점에 이음매가 온다 -> 금지")

    json.dump({"bbox": [float(b.size.X), float(b.size.Y), float(b.size.Z)],
               "volume": float(sh.volume),
               "y_range": [y0, y1],
               "armrest_root_y": hb_front,
               "candidates": cand},
              open(os.path.join(LOCAL, "reports", "14_split_analyze.json"), "w",
                   encoding="utf-8"), ensure_ascii=False, indent=1)
    print("")
    print("saved: reports/14_split_analyze.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
