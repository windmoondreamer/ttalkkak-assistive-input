"""A. 돌출 0 검증 — joint 영역 **포함** 4방향 실루엣 + 3D 외곽 비교.

정점 샘플은 큰 평면 내부에 정점이 없어 nan 을 낸다 (실측). 두 가지로 본다.
  1) 실루엣 bbox 델타 (SIDE / TOP / FRONT / oblique shoulder)
  2) **X 광선 외곽 반폭** 을 joint 구간 전체에서 V4 와 직접 비교
"""
from __future__ import annotations
import os
import sys
import json
import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402
import build123d as bd                                    # noqa: E402
from OCP.BRepTools import BRepTools                       # noqa: E402
import split_build as SB                                  # noqa: E402

LOCAL = os.path.dirname(HERE)
UP = np.array(P.FROZEN_UP_LOCAL)
UH = np.array(P.FROZEN_U_HAT)


def tris(name, tol=0.005):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    f = os.path.join(P.EXPORT_STL, "_sc.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.05)
    T = G.read_stl_tris(f)
    os.remove(f)
    return T


def frame(w):
    w = np.array(w, float)
    w /= np.linalg.norm(w)
    up = UP if abs(w @ UP) < 0.95 else np.array([1.0, 0, 0])
    u = np.cross(up, w)
    u /= np.linalg.norm(u)
    return u, np.cross(w, u), w


def sil_bbox(T, w, ysel=None):
    V = T.reshape(-1, 3)
    if ysel is not None:
        V = V[(V[:, 1] > ysel[0]) & (V[:, 1] < ysel[1])]
    u, v, _ = frame(w)
    return (float((V @ u).min()), float((V @ u).max()),
            float((V @ v).min()), float((V @ v).max()))


def xmax_at(T, y, z):
    d = np.array([1.0, 0.0, 0.0])
    v0, v1, v2 = T[:, 0], T[:, 1], T[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    pv = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, pv)
    m = np.abs(det) > 1e-12
    inv = np.zeros(len(T))
    inv[m] = 1.0 / det[m]
    o = np.array([-500.0, y, z])
    tv = o - v0
    u = np.einsum("ij,ij->i", tv, pv) * inv
    qv = np.cross(tv, e1)
    w = np.einsum("j,ij->i", d, qv) * inv
    t = np.einsum("ij,ij->i", e2, qv) * inv
    ok = m & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 0)
    x = np.unique(np.round(-500.0 + t[ok], 3))
    return float(x.max()) if len(x) else float("nan")


def main():
    V4 = tris("ERGO_HOUSING_25_WRAP_FINAL_V4")
    M = tris("HOUSING_V4_MAIN_PRINT")
    A = tris("HOUSING_V4_ARMREST_PRINT")
    AS = np.vstack([M, A])

    print("=== 1) 실루엣 bbox 델타 (조립본 vs V4) ===")
    views = {"SIDE": np.array([-1.0, 0, 0]), "TOP": -UP, "FRONT": UH,
             "OBLIQUE SHOULDER": -(np.array([0.62, 0, 0]) + UH * 0.50 + UP * 0.60)}
    out = {}
    for nm, w in views.items():
        for zone, ysel in (("전체", None), ("joint 구간", (-150.0, -102.0))):
            a = sil_bbox(V4, w, ysel)
            b = sil_bbox(AS, w, ysel)
            d = max(abs(x - y) for x, y in zip(a, b))
            tag = "PASS" if d < 1e-3 else "FAIL"
            print(f"  [{tag}] {nm:<18} {zone:<10} 델타 {d:.6f} mm")
            out[f"{nm}|{zone}"] = d

    print("")
    print("=== 2) X 광선 외곽 반폭 (joint 구간 전체, 깊이 0~16mm) ===")
    print("     Y    깊이  V4반폭   조립본   차이")
    worst = -1e9
    worst_at = None
    rows = []
    for y in np.arange(-148.0, -103.9, 2.0):
        for off in (0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0):
            z = SB.pb_z(float(y)) - off
            a = xmax_at(V4, float(y), float(z))
            b = xmax_at(AS, float(y), float(z))
            if math.isnan(a) or math.isnan(b):
                continue
            d = b - a
            rows.append((float(y), off, a, b, d))
            if d > worst:
                worst, worst_at = d, (float(y), off, a, b)
    for y, off, a, b, d in rows:
        if abs(d) > 0.02 or off in (0.0, 14.0):
            if off in (0.0, 14.0) and abs(d) <= 0.02 and y % 8 != 0:
                continue
            print(f"  {y:6.0f}  {off:4.0f}  {a:7.2f}  {b:7.2f}  {d:+7.3f}"
                  + ("   <-- 돌출" if d > 0.02 else ""))
    print("")
    print(f"  최대 초과 {worst:+.4f} mm @ Y {worst_at[0]:.0f} 깊이 {worst_at[1]:.0f} "
          f"(V4 {worst_at[2]:.2f} / 조립 {worst_at[3]:.2f})")
    ok = worst <= 0.02
    print(f"  [{'PASS' if ok else 'FAIL'}] visible external protrusion = 0")

    json.dump({"silhouette_delta": out, "max_protrusion_mm": worst,
               "at": {"y": worst_at[0], "depth": worst_at[1]},
               "pass": bool(ok)},
              open(os.path.join(LOCAL, "reports", "16_shoulder_check.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved: reports/16_shoulder_check.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
