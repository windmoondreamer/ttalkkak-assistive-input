"""GROUND B 최종 마감 — 검사 / 제조용 export / 최종 측정.

형상은 만들지 않는다. `ERGO_HOUSING_W2_GROUND_B` 를 그대로 FINAL 로 내보내고
제조 관점 검사(watertight / non-manifold / 최소 살두께)를 수행한다.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402
import side_profile as SP                                 # noqa: E402

UP = np.array(P.FROZEN_UP_LOCAL)
UH = np.array(P.FROZEN_U_HAT)
GH = P.FROZEN_GROUND_WORLD_H
SRC = "ERGO_HOUSING_W2_GROUND_B"
FINAL = "ERGO_HOUSING_W2_FINAL"


def mesh_edges_report(tris, nd=4):
    """watertight / non-manifold 검사. 모든 모서리가 정확히 2회 공유돼야 한다."""
    key = np.round(tris, nd)
    cnt = {}
    for t in key:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = (tuple(t[a]), tuple(t[b]))
            e = e if e[0] <= e[1] else (e[1], e[0])
            cnt[e] = cnt.get(e, 0) + 1
    vals = np.array(list(cnt.values()))
    return {"edges": int(len(vals)),
            "boundary_edges": int((vals == 1).sum()),
            "nonmanifold_edges": int((vals > 2).sum()),
            "watertight": bool((vals == 2).all())}


def min_wall(tris, n_sample=700, seed=0, off=0.05, tmin=0.2):
    """국소 살두께 = 표면점에서 안쪽 법선 방향 첫 교차까지 거리 (Möller–Trumbore)."""
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    mag = np.linalg.norm(n, axis=1)
    ok = mag > 1e-12
    T = tris[ok]
    N = n[ok] / mag[ok, None]
    A = np.random.default_rng(seed).choice(len(T), size=min(n_sample, len(T)),
                                           replace=False)
    v0, v1, v2 = T[:, 0], T[:, 1], T[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    out = []
    for i in A:
        o = T[i].mean(0) - N[i] * off
        d = -N[i]
        pv = np.cross(d, e2)
        det = np.einsum("ij,ij->i", e1, pv)
        m = np.abs(det) > 1e-9
        if not m.any():
            continue
        inv = 1.0 / det[m]
        tv = o - v0[m]
        u = np.einsum("ij,ij->i", tv, pv[m]) * inv
        qv = np.cross(tv, e1[m])
        w = np.einsum("j,ij->i", d, qv) * inv
        t = np.einsum("ij,ij->i", e2[m], qv) * inv
        hit = (u >= -1e-9) & (w >= -1e-9) & (u + w <= 1 + 1e-9) & (t > tmin)
        if hit.any():
            out.append(float(t[hit].min()))
    a = np.array(out)
    return {"samples": int(len(a)), "min_mm": float(a.min()),
            "p01_mm": float(np.percentile(a, 1)),
            "p05_mm": float(np.percentile(a, 5)),
            "median_mm": float(np.median(a))}


def measure(tris):
    V = tris.reshape(-1, 3)
    u, h = V @ UH, V @ UP - GH
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    mag = np.linalg.norm(n, axis=1)
    ok = mag > 1e-12
    ar, nn, ctr = mag[ok] / 2.0, n[ok] / mag[ok, None], tris[ok].mean(1)
    ch = ctr @ UP - GH
    gm = (ch < 0.5) & ((nn @ UP) < -0.9)
    vol = abs(float(np.einsum("ij,ij->i", tris[:, 0],
                              np.cross(tris[:, 1], tris[:, 2])).sum() / 6.0))
    # 하부 실루엣 (블렌드 구간)
    step = 2.0
    us = np.arange(u.min(), u.max() + step, step)
    lo = []
    for uu in us:
        m = (u >= uu - step) & (u < uu + step)
        if m.sum() >= 3:
            lo.append((float(uu), float(h[m].min())))
    lo = np.array(lo)
    # **bin 중심이 아니라 실제 점의 u** 를 쓴다. bin 좌표를 그대로 쓰면
    # step 2.0 만큼 어긋난다 (실측: -69.89 vs 실제 -68.11).
    ug = float(u[h < 0.5].min())
    seg = lo[lo[:, 0] <= ug + 2.0]
    sl = [math.degrees(math.atan2(-(seg[i, 1] - seg[i - 1, 1]),
                                  seg[i, 0] - seg[i - 1, 0]))
          for i in range(1, len(seg)) if seg[i, 0] - seg[i - 1, 0] > 1e-6]
    sl = np.abs(np.array(sl)) if sl else np.array([0.0])
    return {"W_mm": float(V[:, 0].max() - V[:, 0].min()),
            "L_mm": float(V[:, 1].max() - V[:, 1].min()),
            "H_world_mm": float(h.max() - h.min()),
            "volume_mm3": vol,
            "first_ground_contact_u": ug,
            "floating_span_mm": float(ug - u.min()),
            "u_tip": float(u.min()),
            "max_blend_slope_deg": float(sl.max()),
            "mean_blend_slope_deg": float(sl.mean()),
            "ground_area_mm2": float(ar[gm].sum())}


def main():
    bd = G.b3d()
    src = os.path.join(P.EXPORT_STEP, SRC + ".step")
    if not os.path.exists(src):
        print("STOP - 원본 없음:", src)
        return 2
    print("=" * 78)
    print("GROUND B 최종 마감")
    print("=" * 78)

    sol = bd.import_step(src).solids()
    print(f"\n[1] BREP 게이트")
    ok = len(sol) == 1
    s0 = sol[0]
    valid = G.shape_valid(s0)
    shells = len(list(s0.shells()))
    print(f"  solid {len(sol)}  shells {shells}  faces {len(list(s0.faces()))}"
          f"  edges {len(list(s0.edges()))}")
    print(f"  valid={valid}  vol={float(s0.volume):,.4f}")
    bb = s0.bounding_box()
    print(f"  bbox {bb.size.X:.4f} x {bb.size.Y:.4f} x {bb.size.Z:.4f}")
    sv = G.shell_volumes(s0)
    sliver = [v for _s, v in sv if v < 1.0]
    print(f"  sliver shell {len(sliver)}개")
    if not (ok and valid and shells == 1 and not sliver):
        print("  [FAIL] BREP 게이트 - export 중단")
        return 1
    print("  [PASS] BREP 게이트")

    print(f"\n[2] 제조용 export")
    # OCC 는 shape 에 저장된 기존 tessellation 을 재사용한다.
    # Clean_s 로 지우지 않으면 tolerance 를 바꿔도 삼각형 수가 안 변한다
    # (실측: 0.010 과 0.030 이 둘 다 300,635).
    from OCP.BRepTools import BRepTools
    BRepTools.Clean_s(s0.wrapped)
    chosen = (0.015, 0.08)
    out = G.export_all(s0, FINAL, tolerance=chosen[0],
                       angular_tolerance=chosen[1])
    print(f"  tolerance {chosen[0]:.3f} / angular {chosen[1]:.2f}")
    for k, v in out.items():
        print(f"  {k:<5s} {os.path.relpath(v, P.LOCAL_CAD)}  "
              f"({os.path.getsize(v)/1048576:.2f} MB)")

    tris = G.read_stl_tris(out["stl"])
    print(f"\n[3] STL 검사  삼각형 {len(tris):,}")
    me = mesh_edges_report(tris, 5)
    for k, v in me.items():
        print(f"  {k:<20s} {v}")
    mw = min_wall(tris)
    V = tris.reshape(-1, 3)
    skirt = tris[(tris.mean(1) @ UH) < -20.0]
    mw_skirt = min_wall(skirt, n_sample=500) if len(skirt) > 50 else None
    # 경계/비다양체 모서리 위치
    key = np.round(tris, 5)
    cnt = {}
    for tr in key:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = (tuple(tr[a]), tuple(tr[b]))
            e = e if e[0] <= e[1] else (e[1], e[0])
            cnt[e] = cnt.get(e, 0) + 1
    bad = [(k, v) for k, v in cnt.items() if v != 2]
    for k, v in bad[:4]:
        c = 0.5 * (np.array(k[0]) + np.array(k[1]))
        print(f"  결함 모서리 (공유 {v}회) @ ({c[0]:.2f},{c[1]:.2f},{c[2]:.2f})"
              f"  u {float(c @ UH):.2f}  h {float(c @ UP) - GH:.2f}")
    print(f"  최소 살두께 {mw['min_mm']:.3f} mm  (1% {mw['p01_mm']:.3f} / "
          f"5% {mw['p05_mm']:.3f} / 중앙 {mw['median_mm']:.3f}, "
          f"표본 {mw['samples']})")
    if mw_skirt:
        print(f"  신규 스커트(u<-20) 최소 {mw_skirt['min_mm']:.3f} mm  "
              f"(1% {mw_skirt['p01_mm']:.3f} / 중앙 {mw_skirt['median_mm']:.3f})")

    print(f"\n[4] BOTTOM_CARRIER 제조용 export (형상 무수정)")
    core = bd.import_step(P.reference_path("conformal_core"))
    car = sorted(core.solids(), key=lambda s: float(s.volume))[0]
    cout = G.export_all(car, "BOTTOM_CARRIER_FINAL", tolerance=0.01,
                        angular_tolerance=0.05)
    ctris = G.read_stl_tris(cout["stl"])
    cme = mesh_edges_report(ctris, 5)
    print(f"  vol {float(car.volume):,.6f} mm3 (동결값 {P.FROZEN_CARRIER_VOL:,.6f})"
          f"  watertight={cme['watertight']}  삼각형 {len(ctris):,}")

    print(f"\n[5] 최종 측정")
    ms = measure(tris)
    for k, v in ms.items():
        print(f"  {k:<26s} {v:14,.4f}")

    rep = {"brep": {"solids": len(sol), "shells": shells,
                    "faces": len(list(s0.faces())),
                    "edges": len(list(s0.edges())), "valid": valid,
                    "volume_mm3": float(s0.volume)},
           "stl": {**me, "tolerance": chosen[0], "angular_tolerance": chosen[1]}, "min_wall": mw, "min_wall_skirt": mw_skirt, "measure": ms,
           "carrier": {"volume_mm3": float(car.volume),
                       "watertight": cme["watertight"]},
           "paths": {**out, **{"carrier_" + k: v for k, v in cout.items()}}}
    json.dump(rep, open(os.path.join(P.REPORTS_DIR, "08_final_b.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n저장: reports/08_final_b.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
