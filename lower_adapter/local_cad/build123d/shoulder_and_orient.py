"""(1) joint 구간 V4 외곽 프로파일 실측  (2) orientation 별 support 면적 비교.

(1) 정점 샘플은 큰 평면 내부에 정점이 없어 nan/음수를 낸다 (실측). **X 광선**으로 잰다.
(2) support 면적 = 아래보기 face 면적. orientation 후보를 실제로 회전시켜 비교한다.
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

LOCAL = os.path.dirname(HERE)
BUILD = 256.0
SELF_SUP = math.sin(math.radians(45.0))


def tris(name, tol=0.05):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    f = os.path.join(P.EXPORT_STL, "_so.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.3)
    T = G.read_stl_tris(f)
    os.remove(f)
    return T


def xmax_at(T, y, z):
    """(y,z) 에서 +X 광선의 최대 교차 X = 외곽 반폭."""
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


PB_SLOPE, PB_Y0, PB_Z0 = 0.0875, -121.0, -70.81


def pb_z(y):
    return PB_Z0 + PB_SLOPE * (y - PB_Y0)


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def support_area(T, R):
    Tp = T @ R.T
    Tp[:, :, 2] -= Tp.reshape(-1, 3)[:, 2].min()
    n = np.cross(Tp[:, 1] - Tp[:, 0], Tp[:, 2] - Tp[:, 0])
    mg = np.linalg.norm(n, axis=1)
    ok = mg > 1e-12
    nn = n[ok] / mg[ok, None]
    ar = mg[ok] / 2.0
    s = -nn[:, 2]
    V = Tp.reshape(-1, 3)
    bb = V.max(0) - V.min(0)
    c = Tp[ok].mean(1)
    base = Tp[ok][c[:, 2] < 0.4]
    bedA = 0.0
    if len(base):
        a1 = base[:, 1, :2] - base[:, 0, :2]
        b1 = base[:, 2, :2] - base[:, 0, :2]
        bedA = float(np.abs(a1[:, 0] * b1[:, 1] - a1[:, 1] * b1[:, 0]).sum() / 2)
    return {"bbox": bb.tolist(), "fits": bool(np.all(bb <= BUILD)),
            "down_area": float(ar[s > SELF_SUP].sum()),
            "total_area": float(ar.sum()),
            "bed_contact": bedA,
            "slender": float(bb[2] / math.sqrt(max(bedA, 1e-9)))}


def main():
    V4 = tris("ERGO_HOUSING_25_WRAP_FINAL_V4")
    print("=== (1) joint 구간 V4 외곽 반폭 (X 광선, 상판 밑 0~14mm) ===")
    print("     Y    상판밑0   밑4    밑8    밑12   밑14   최소")
    prof = {}
    for y in np.arange(-148.0, -104.9, 4.0):
        row = []
        for off in (0.0, 4.0, 8.0, 12.0, 14.0):
            z = pb_z(y) - off
            row.append(xmax_at(V4, float(y), float(z)))
        mn = np.nanmin(row)
        prof[float(y)] = row
        print("  %6.0f  " % y + "  ".join("%6.2f" % r for r in row) + "  %6.2f" % mn)
    mins = {y: float(np.nanmin(r)) for y, r in prof.items()}
    worst = min(mins.values())
    print(f"\n  joint 구간 최소 외곽 반폭 = {worst:.2f} mm   현재 DBL_X = 63.0")
    print(f"  -> 안전한 상수 DBL_X <= {worst - 2.0:.2f} (2mm 여유)")

    print("")
    print("=== (2) MAIN orientation 별 support 면적 ===")
    M = tris("HOUSING_V4_MAIN_PRINT")
    cands = {
        "CUT FACE DOWN (Rx+90) [현재]": rot_x(90),
        "CUT FACE UP   (Rx-90)": rot_x(-90),
        "DECK DOWN     (Rz0,  그대로)": np.eye(3),
        "DECK UP       (Rx180)": rot_x(180),
        "SIDE          (Ry+90)": rot_y(90),
        "SIDE          (Ry-90)": rot_y(-90),
        "CUT DOWN +기울임 (Rx90,Ry20)": rot_y(20) @ rot_x(90),
        "CUT DOWN +기울임 (Rx90,Rz20)": rot_z(20) @ rot_x(90),
    }
    print("  방향                              bbox(W x D x H)         P1S  "
          "아래보기면적  베드접지  세장비")
    out = {}
    for nm, R in cands.items():
        r = support_area(M, R)
        bb = r["bbox"]
        out[nm] = r
        print(f"  {nm:<32} {bb[0]:6.1f} x{bb[1]:6.1f} x{bb[2]:6.1f}   "
              f"{'OK ' if r['fits'] else 'OVER'}  {r['down_area']:10,.0f}  "
              f"{r['bed_contact']:8,.0f}  {r['slender']:6.2f}")

    print("")
    print("=== ARMREST orientation 별 ===")
    A = tris("HOUSING_V4_ARMREST_PRINT")
    cands2 = {
        "CUT FACE DOWN (Rx-90) [현재]": rot_x(-90),
        "CUT FACE UP   (Rx+90)": rot_x(90),
        "상판 아래     (그대로)": np.eye(3),
        "상판 위       (Rx180)": rot_x(180),
    }
    for nm, R in cands2.items():
        r = support_area(A, R)
        bb = r["bbox"]
        out["ARM " + nm] = r
        print(f"  {nm:<32} {bb[0]:6.1f} x{bb[1]:6.1f} x{bb[2]:6.1f}   "
              f"{'OK ' if r['fits'] else 'OVER'}  {r['down_area']:10,.0f}  "
              f"{r['bed_contact']:8,.0f}  {r['slender']:6.2f}")

    json.dump({"outer_profile": {str(k): v for k, v in prof.items()},
               "min_halfwidth": worst, "orientations": out},
              open(os.path.join(LOCAL, "reports", "16_shoulder_orient.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("")
    print("saved: reports/16_shoulder_orient.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
