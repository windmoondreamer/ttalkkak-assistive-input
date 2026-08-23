"""TRAPPED SUPPORT 확정 판정 — voxel connectivity.

수평 8방향 등고면 광선만으로는 사선/꺾인 제거 경로를 못 본다.
support 체적을 복셀로 잡고, 각 chunk 가 **실제 removal opening** 까지
연결되는지를 3D flood fill 로 본다. 좁은 목은 침식(erosion) 반경으로 잰다.

removal opening (MAIN, CUT FACE DOWN = Rx +90deg, 베드에 앉힘):
  grip (x,y,z) -> print (x, -z, y - z0)
  1) 덱 개구부 92.9 x 89.8  : grip +Z 를 향함 -> print **-Y 면**
  2) carrier 하방 인출 통로  : grip -Z 를 향함 -> print **+Y 면**
  3) 하우징 하부 개방부      : 동일하게 print +Y 면
  4) joint 분할 개방면       : grip Y=-140 -> print **z = 0 (베드면)**
"""
from __future__ import annotations
import os
import sys
import json
import math

import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402
import build123d as bd                                    # noqa: E402
from OCP.BRepTools import BRepTools                       # noqa: E402

LOCAL = os.path.dirname(HERE)
ADAPTER = os.path.dirname(LOCAL)
VOX = 2.0                    # 복셀 크기 mm
PAD = 8.0                    # bbox 여유
DECK_Z = -61.878507


def load_tris(name, tol=0.05):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    f = os.path.join(P.EXPORT_STL, "_ta.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.3)
    T = G.read_stl_tris(f)
    os.remove(f)
    return T


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "HOUSING_V4_MAIN_PRINT"
    ang = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
    T = load_tris(name)
    R = rot_x(ang)
    Tp = T @ R.T
    z0 = Tp.reshape(-1, 3)[:, 2].min()
    Tp[:, :, 2] -= z0
    V = Tp.reshape(-1, 3)
    lo = V.min(0) - PAD
    hi = V.max(0) + PAD
    dims = np.ceil((hi - lo) / VOX).astype(int)
    print(f"[{name}] Rx {ang:+.0f}   격자 {dims[0]}x{dims[1]}x{dims[2]} @ {VOX}mm "
          f"= {np.prod(dims):,} 복셀")

    gx = lo[0] + (np.arange(dims[0]) + 0.5) * VOX
    gy = lo[1] + (np.arange(dims[1]) + 0.5) * VOX
    gz = lo[2] + (np.arange(dims[2]) + 0.5) * VOX
    X, Y, Z = np.meshgrid(gx, gy, gz, indexing="ij")
    pts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    print("  point-in-mesh ...")
    solid = G.mesh_inside(Tp, pts).reshape(dims)
    free = ~solid
    print(f"  solid {int(solid.sum()):,} / free {int(free.sum()):,}")

    # ---- support 체적: 같은 칼럼에서 위쪽에 재료가 있는 free 칸 ----------
    above = np.cumsum(solid[:, :, ::-1], axis=2)[:, :, ::-1] > 0
    below = np.cumsum(solid, axis=2) > 0
    sup = free & above & below          # 위/아래 모두 재료 -> 지지 필요 구간
    print(f"  support 후보 복셀 {int(sup.sum()):,} "
          f"= {sup.sum() * VOX ** 3 / 1000:,.1f} cm3")

    # ---- removal opening seed -------------------------------------------
    # print 좌표에서 각 opening 이 향하는 면의 **바깥 패드 영역**을 seed 로 쓴다
    # 회전 부호에 따라 opening 이 향하는 면이 바뀐다.
    #   Rx +90 : grip +Z -> print -Y (덱),  grip -Z -> print +Y,  절단면 -> z=0
    #   Rx -90 : grip +Z -> print +Y (덱),  grip -Z -> print -Y,  절단면 -> z=max
    seeds = {}
    if ang > 0:
        deck_sl = (slice(None), slice(0, 2), slice(None))
        carr_sl = (slice(None), slice(-2, None), slice(None))
        split_sl = (slice(None), slice(None), slice(0, 2))
        split_lab = "SPLIT / BED FACE (print z=0)"
    else:
        deck_sl = (slice(None), slice(-2, None), slice(None))
        carr_sl = (slice(None), slice(0, 2), slice(None))
        split_sl = (slice(None), slice(None), slice(-2, None))
        split_lab = "SPLIT FACE (print z=max, 위를 향함)"
    for lab, sl in (("DECK OPENING", deck_sl),
                    ("CARRIER / LOWER OPENING", carr_sl),
                    (split_lab, split_sl)):
        m = np.zeros(dims, bool)
        m[sl] = True
        seeds[lab] = m & free

    # ---- chunk 분리 -------------------------------------------------------
    lab, n = ndi.label(sup, structure=np.ones((3, 3, 3)))
    print(f"  support chunk {n}개")
    sizes = ndi.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
    order = np.argsort(-sizes) + 1

    # ---- 목 반경별 연결성 -------------------------------------------------
    # free 를 k 번 침식하면 반경 k*VOX 짜리 구가 지날 수 있는 통로만 남는다
    ero = {0: free}
    for k in (1, 2, 3):
        ero[k] = ndi.binary_erosion(free, np.ones((3, 3, 3)), iterations=k)

    res = []
    print("")
    print("  chunk  체적(cm3)   grip 좌표 bbox                        판정")
    for li in order[:12]:
        cm = lab == li
        vol = cm.sum() * VOX ** 3
        if vol < 200.0:
            continue
        idx = np.argwhere(cm)
        pc = lo + (idx + 0.5) * VOX                     # print 좌표
        gp = pc.copy()
        gp[:, 2] += z0
        gp = gp @ R                                     # print -> grip (R^T^T)
        # 경로를 **전부** 열거한다. 먼저 맞는 것 하나만 쓰면 테스트 순서가
        # 그대로 라벨이 되어 캐리어 chunk 도 DECK 로 찍힌다 (실측).
        routes, rmax = [], -1
        for k in (3, 2, 1, 0):
            hit = []
            for nmo, sd in seeds.items():
                reach = ndi.binary_propagation(sd & ero[k], mask=ero[k])
                if (ndi.binary_dilation(cm, np.ones((3, 3, 3))) & reach).any():
                    hit.append(nmo)
            if hit:
                routes, rmax = hit, k * VOX
                break
        if not routes:
            cls = "TRUE TRAPPED"
        elif rmax < 2.0:
            cls = "NARROW (<2mm neck) via " + " + ".join(r.split(" (")[0] for r in routes)
        else:
            cls = "REMOVABLE THROUGH " + " + ".join(r.split(" (")[0] for r in routes)
        print(f"   #{li:<4d} {vol / 1000:8.2f}   "
              f"X[{gp[:, 0].min():7.1f},{gp[:, 0].max():7.1f}] "
              f"Y[{gp[:, 1].min():7.1f},{gp[:, 1].max():7.1f}] "
              f"Z[{gp[:, 2].min():7.1f},{gp[:, 2].max():7.1f}]")
        print(f"          목반경 >= {rmax:.0f}mm   {cls}")
        res.append({"label": int(li), "volume_mm3": float(vol),
                    "grip_bbox": [[float(gp[:, i].min()), float(gp[:, i].max())]
                                  for i in range(3)],
                    "class": cls, "routes": routes, "neck_radius_mm": float(rmax)})

    ntrap = sum(1 for r in res if r["class"] == "TRUE TRAPPED")
    tvol = sum(r["volume_mm3"] for r in res if r["class"] == "TRUE TRAPPED")
    print("")
    print(f"  [{'PASS' if ntrap == 0 else 'FAIL'}] TRUE TRAPPED chunk {ntrap}개 "
          f"/ {tvol / 1000:.2f} cm3")

    json.dump({"part": name, "rot_x": ang, "voxel": VOX, "chunks": res,
               "true_trapped": ntrap, "true_trapped_mm3": tvol},
              open(os.path.join(LOCAL, "reports",
                                f"15_trapped_{name}.json"), "w",
                   encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"saved: reports/15_trapped_{name}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
