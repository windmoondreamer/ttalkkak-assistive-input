"""25deg + wrap skirt 최종화 — 시각 감사 / 측정 / 제조 export.

형상은 만들지 않는다. SLOPE25_A 를 FINAL 로 내보내고
(1) 실제 void 감사 (2) 팔 지지면 측정 (3) 캐리어 여유 (4) STL 검사 를 한다.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402
import finalize_b as F                                    # noqa: E402

UP = np.array(P.FROZEN_UP_LOCAL)
UH = np.array(P.FROZEN_U_HAT)
GH = P.FROZEN_GROUND_WORLD_H
SRC = "ERGO_HOUSING_25_WRAP_W134_M15"
FINAL = "ERGO_HOUSING_25_WRAP_FINAL_V4"


def void_audit(tris, du=2.5, dh=2.5):
    """SIDE 투영 광선 점유 -> 내부 void 탐지.

    렌더는 은면 처리 때문에 실제 구멍과 아티팩트를 구분하지 못한다
    (앞서 실제 void 를 아티팩트로 오판한 전력이 있다). 광선으로 판정한다.
    바깥에서 flood fill 한 뒤 남는 빈칸이 내부 void 다.
    """
    tu = tris @ UH
    th = (tris @ UP) - GH
    tumin, tumax = tu.min(1), tu.max(1)
    thmin, thmax = th.min(1), th.max(1)
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    d = np.array([1.0, 0.0, 0.0])
    pv = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, pv)
    gu = np.arange(tu.min() - du, tu.max() + du, du)
    gh = np.arange(-2.0, th.max() + dh, dh)
    occ = np.zeros((len(gh), len(gu)), bool)
    for i, hh in enumerate(gh):
        hg = hh + GH
        for j, uu in enumerate(gu):
            sel = (tumin <= uu) & (tumax >= uu) & (thmin <= hh) & (thmax >= hh)
            if not sel.any():
                continue
            yy = 0.9396926207859084 * uu + 0.3420201433256687 * hg
            zz = -0.3420201433256687 * uu + 0.9396926207859084 * hg
            o = np.array([-400.0, yy, zz])
            idx = np.where(sel)[0]
            m = np.abs(det[idx]) > 1e-9
            if not m.any():
                continue
            idx = idx[m]
            inv = 1.0 / det[idx]
            tv = o - v0[idx]
            a = np.einsum("ij,ij->i", tv, pv[idx]) * inv
            qv = np.cross(tv, e1[idx])
            b = np.einsum("j,ij->i", d, qv) * inv
            tt = np.einsum("ij,ij->i", e2[idx], qv) * inv
            if ((a >= -1e-9) & (b >= -1e-9) & (a + b <= 1 + 1e-9) & (tt > 0)).any():
                occ[i, j] = True
    H, W = occ.shape
    seen = np.zeros_like(occ)
    st = []
    for i in range(H):
        for j in (0, W - 1):
            if not occ[i, j] and not seen[i, j]:
                seen[i, j] = True
                st.append((i, j))
    for j in range(W):
        for i in (0, H - 1):
            if not occ[i, j] and not seen[i, j]:
                seen[i, j] = True
                st.append((i, j))
    while st:
        i, j = st.pop()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a2, b2 = i + di, j + dj
            if 0 <= a2 < H and 0 <= b2 < W and not occ[a2, b2] and not seen[a2, b2]:
                seen[a2, b2] = True
                st.append((a2, b2))
    void = (~occ) & (~seen)
    idx = np.argwhere(void)
    return {"grid": "%dx%d @ %.1fmm" % (len(gu), len(gh), du),
            "interior_void_cells": int(void.sum()),
            "locations": [{"u": round(float(gu[j]), 1),
                           "h": round(float(gh[i]), 1)} for i, j in idx[:10]]}


def arm_support(tris, n_thr=0.70, u_max=-50.0):
    """ARM_SUPPORT_SURFACE_AREA — 25도 팔받침의 실제 접촉 가능 상면.

    기존 wrist_area_mm2 는 7도 평면 face 를 찾는 방식이라 현재 구조에서
    0 이 나온다. 폐기하고 이 지표로 대체한다.
    """
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    mg = np.linalg.norm(n, axis=1)
    ok = mg > 1e-12
    ar = mg[ok] / 2.0
    nn = n[ok] / mg[ok, None]
    ctr = tris[ok].mean(1)
    cu = ctr @ UH
    ch = ctr @ UP - GH
    dot = nn @ UP
    m = (dot > n_thr) & (cu < u_max) & (ch > 3.0)
    if not m.any():
        return {"area_mm2": 0.0}
    return {"area_mm2": float(ar[m].sum()),
            "projected_area_mm2": float((ar[m] * dot[m]).sum()),
            "triangles": int(m.sum()),
            "u_range": [round(float(cu[m].min()), 1),
                        round(float(cu[m].max()), 1)],
            "mean_tilt_deg": float(np.degrees(np.arccos(np.clip(
                float(np.average(dot[m], weights=ar[m])), -1.0, 1.0))))}


def carrier_clearance(tris, car_tris, travel=100.0):
    """캐리어 XY 발자국과 하우징 재료의 최소 수평 여유 (스윕 Z 구간)."""
    cv = car_tris.reshape(-1, 3)
    x0, x1 = float(cv[:, 0].min()), float(cv[:, 0].max())
    y0, y1 = float(cv[:, 1].min()), float(cv[:, 1].max())
    z0, z1 = float(cv[:, 2].min()) - travel, float(cv[:, 2].max())
    V = tris.reshape(-1, 3)
    m = (V[:, 2] >= z0) & (V[:, 2] <= z1)
    if not m.any():
        return None
    Q = V[m]
    dx = np.maximum(x0 - Q[:, 0], Q[:, 0] - x1)
    dy = np.maximum(y0 - Q[:, 1], Q[:, 1] - y1)
    out = (dx > 0) | (dy > 0)
    d = np.sqrt(np.maximum(dx, 0.0) ** 2 + np.maximum(dy, 0.0) ** 2)
    return {"min_horizontal_clearance_mm":
            float(d[out].min()) if out.any() else None,
            "points_inside_footprint": int((~out).sum()),
            "z_range": [round(z0, 2), round(z1, 2)]}


def main():
    bd = G.b3d()
    from OCP.BRepTools import BRepTools
    sp = os.path.join(P.EXPORT_STEP, SRC + ".step")
    if not os.path.exists(sp):
        print("STOP - 원본 없음:", sp)
        return 2
    s0 = bd.import_step(sp).solids()[0]
    BRepTools.Clean_s(s0.wrapped)
    print("=" * 78)
    print("25deg + WRAP SKIRT 최종화")
    print("=" * 78)

    bb = s0.bounding_box()
    print("\n[1] BREP 게이트")
    print("  solid 1  shells %d  faces %d  edges %d  valid %s"
          % (len(list(s0.shells())), len(list(s0.faces())),
             len(list(s0.edges())), G.shape_valid(s0)))
    print("  vol %.4f   bbox %.4f x %.4f x %.4f"
          % (float(s0.volume), bb.size.X, bb.size.Y, bb.size.Z))
    if len(list(s0.shells())) != 1 or not G.shape_valid(s0):
        print("  [FAIL] BREP 게이트")
        return 1
    print("  [PASS] BREP 게이트")

    print("\n[2] 제조용 export")
    # 경사면 상단을 덱에 **정확히** 맞춰 잘랐기 때문에 코어 상면과 동일 평면이
    # 되고, 그 이음매에서 tessellation 이 갈라진다 (실측: Z=-61.88 / Y=-18 에
    # 경계 모서리 6개). tol 0.030 부터 watertight 가 된다. 0.03mm chord 편차는
    # FDM 레이어(0.1~0.2mm) 보다 훨씬 작아 제조 품질에 영향이 없다.
    out = G.export_all(s0, FINAL, tolerance=0.030, angular_tolerance=0.15)
    for k, v in out.items():
        print("  %-5s %s  (%.2f MB)"
              % (k, os.path.relpath(v, P.LOCAL_CAD),
                 os.path.getsize(v) / 1048576))

    tris = G.read_stl_tris(out["stl"])
    me = F.mesh_edges_report(tris, 5)
    deg = int((np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0],
                                       tris[:, 2] - tris[:, 0]), axis=1)
               / 2.0 < 1e-9).sum())
    print("\n[3] STL  삼각형 %d  degenerate %d" % (len(tris), deg))
    for k, v in me.items():
        print("  %-20s %s" % (k, v))

    print("\n[4] 실제 void 감사 (SIDE 광선 투영)")
    va = void_audit(tris)
    print("  격자 %s   내부 void 칸 %d"
          % (va["grid"], va["interior_void_cells"]))
    for L in va["locations"]:
        print("    u %8.1f  h %7.1f" % (L["u"], L["h"]))

    print("\n[5] 팔 지지면 (ARM_SUPPORT_SURFACE_AREA)")
    asf = arm_support(tris)
    for k, v in asf.items():
        print("  %-24s %s" % (k, v))

    print("\n[6] 캐리어 여유")
    cst = os.path.join(P.EXPORT_STL, "BOTTOM_CARRIER_FINAL.stl")
    cc = carrier_clearance(tris, G.read_stl_tris(cst)) \
        if os.path.exists(cst) else None
    if cc:
        for k, v in cc.items():
            print("  %-28s %s" % (k, v))

    print("\n[7] 구조 수치")
    V = tris.reshape(-1, 3)
    u = V @ UH
    h = V @ UP - GH
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    mg = np.linalg.norm(n, axis=1)
    ok = mg > 1e-12
    ar, nn, ctr = mg[ok] / 2.0, n[ok] / mg[ok, None], tris[ok].mean(1)
    ch = ctr @ UP - GH
    gm = (ch < 0.5) & ((nn @ UP) < -0.9)
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    cr = np.cross(v1, v2)
    s6 = np.einsum("ij,ij->i", v0, cr)
    Vol = abs(s6.sum() / 6.0)
    C = ((v0 + v1 + v2) * s6[:, None]).sum(0) / (4 * s6.sum())
    cu = float(C @ UH)
    g = h < 0.5
    ur, uf = float(u[g].max()), float(u[g].min())
    mh = Vol * 1.24e-3 * 0.25
    dims = {"L_mm": float(V[:, 1].max() - V[:, 1].min()),
            "W_mm": float(V[:, 0].max() - V[:, 0].min()),
            "H_world_mm": float(h.max() - h.min()),
            "volume_mm3": Vol,
            "ground_area_mm2": float(ar[gm].sum()),
            "front_most_support_u": uf,
            "rear_most_ground_u": ur,
            "centroid_u": cu,
            "rear_lever_arm_mm": ur - cu,
            "mass_25pct_infill_g": mh}
    for k, v in dims.items():
        print("  %-26s %14.3f" % (k, v))

    json.dump({"brep": {"faces": len(list(s0.faces())),
                        "edges": len(list(s0.edges())),
                        "shells": len(list(s0.shells())),
                        "volume_mm3": float(s0.volume)},
               "stl": {**me, "triangles": int(len(tris)), "degenerate": deg},
               "void_audit": va, "arm_support": asf, "carrier": cc,
               "dims": dims, "paths": out},
              open(os.path.join(P.REPORTS_DIR, "13_25wrap_final_v4.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n저장: reports/13_25wrap_final_v4.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
