"""E. JOINT SURFACE QUALITY + F. support 전략 비교 + G. brim.

CUT FACE UP 이라 mating joint 가 **위를 향한다**. 위를 향하는 면은 support 가
닿지 않으므로, 실제로 닿는지 face 단위로 확인한다.

critical mating surface (원본 grip frame 기준):
  lap mating plane   상판 밑 LAP_D, Y in [Y_UP, Y_LO]
  rib                X ±12,  Y[-137,-115]
  groove             동일 X/Y, FRONT 쪽
  screw seating      카운터보어 바닥, X ±40, Y -133/-119
  insert pilot       insert 구멍 내벽
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
SELF_SUP = math.sin(math.radians(45.0))
BUILD = 256.0

PARTS = {"MAIN": ("HOUSING_V4_MAIN_PRINT", -90.0),
         "ARMREST": ("HOUSING_V4_ARMREST_PRINT", -90.0)}


def tris(name, tol=0.04):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    f = os.path.join(P.EXPORT_STL, "_qc.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.25)
    T = G.read_stl_tris(f)
    os.remove(f)
    return T


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def pbz(y):
    return SB.pb_z(y)


MATING = {
    "lap mating plane": lambda c: (
        (c[:, 1] > SB.Y_UP - 1) & (c[:, 1] < SB.Y_LO + 1)
        & (np.abs((pbz(c[:, 1]) - c[:, 2]) - SB.LAP_D) < 2.0)),
    "rib": lambda c: ((np.abs(np.abs(c[:, 0]) - 12.0) < 3.5)
                      & (c[:, 1] > SB.RIB_Y0 - 1) & (c[:, 1] < SB.RIB_Y1 + 1)
                      & ((pbz(c[:, 1]) - c[:, 2]) > SB.LAP_D - 2)
                      & ((pbz(c[:, 1]) - c[:, 2]) < SB.LAP_D + 4)),
    "screw seating (counterbore)": lambda c: (
        (np.abs(np.abs(c[:, 0]) - 40.0) < 5.0)
        & (np.abs(np.abs(c[:, 1] + 126.0) - 7.0) < 3.0)
        & ((pbz(c[:, 1]) - c[:, 2]) > SB.DBL_T - 4.5)),
    "insert pilot": lambda c: (
        (np.abs(np.abs(c[:, 0]) - 40.0) < 3.6)
        & (np.abs(np.abs(c[:, 1] + 126.0) - 7.0) < 3.0)
        & ((pbz(c[:, 1]) - c[:, 2]) < SB.LAP_D)
        & ((pbz(c[:, 1]) - c[:, 2]) > SB.LAP_D - 9.0)),
}


def analyze(nm, fn, ang):
    T = tris(fn)
    R = rot_x(ang)
    Tp = T @ R.T
    Tp[:, :, 2] -= Tp.reshape(-1, 3)[:, 2].min()
    n = np.cross(Tp[:, 1] - Tp[:, 0], Tp[:, 2] - Tp[:, 0])
    mg = np.linalg.norm(n, axis=1)
    ok = mg > 1e-12
    Tp, T, n, mg = Tp[ok], T[ok], n[ok], mg[ok]
    nn = n / mg[:, None]
    ar = mg / 2.0
    s = -nn[:, 2]
    down = s > SELF_SUP
    co = T.mean(1)
    print("")
    print(f"=== E [{nm}] mating surface support 접촉 ===")
    print("  면                        총면적   아래보기(=support 접촉 가능)  비율")
    out = {}
    for lab, f in MATING.items():
        sel = f(co)
        if sel.sum() == 0:
            print(f"    {lab:<26} 해당 face 없음")
            out[lab] = None
            continue
        tot = float(ar[sel].sum())
        dn = float(ar[sel & down].sum())
        print(f"    {lab:<26} {tot:8,.1f}   {dn:10,.1f}   "
              f"{100 * dn / max(tot, 1e-9):5.1f}%   "
              f"{'CONTACT-FREE' if dn < 1.0 else '접촉 가능'}")
        out[lab] = {"area": tot, "down_area": dn}
    return Tp, ar, s, down, co, out


def main():
    res = {}
    for nm, (fn, ang) in PARTS.items():
        Tp, ar, s, down, co, mate = analyze(nm, fn, ang)
        res[nm] = {"mating": mate}

        # ---- F: build-plate-only vs everywhere -------------------------
        # 아래로 광선을 쏴 베드까지 비었으면 plate-only 로 지지 가능
        from print_engineering import VGrid
        vg = VGrid(Tp)
        ctr = Tp.mean(1)
        idx = np.nonzero(down)[0]
        order = idx[np.argsort(-ar[idx])][:5000]
        plate_ok = 0.0
        on_part = 0.0
        vol_plate = 0.0
        vol_part = 0.0
        for k in order:
            x, y, z = ctr[k]
            hs = vg.hits(x, y)
            below = hs[hs < z - 0.25]
            if len(below) == 0:
                plate_ok += ar[k]
                vol_plate += ar[k] * z
            else:
                on_part += ar[k]
                vol_part += ar[k] * (z - below[-1])
        rest = float(ar[idx].sum()) - plate_ok - on_part
        print(f"  --- F [{nm}] support 전략 ---")
        print(f"    build-plate-only 로 지지 가능   {plate_ok:10,.1f} mm2   "
              f"기둥 체적 약 {vol_plate / 1000:8,.1f} cm3")
        print(f"    파트 위에 얹어야 하는 면        {on_part:10,.1f} mm2   "
              f"기둥 체적 약 {vol_part / 1000:8,.1f} cm3")
        print(f"    (표본 밖 잔여 {rest:,.1f} mm2 는 보수적으로 everywhere)")
        cover = 100 * plate_ok / max(plate_ok + on_part, 1e-9)
        print(f"    -> plate-only 커버율 {cover:.1f}%  "
              f"{'plate-only 로 충분' if on_part < 200 else 'everywhere 필요'}")
        res[nm]["support"] = {"plate_only_mm2": plate_ok, "on_part_mm2": on_part,
                              "vol_plate_cm3": vol_plate / 1000,
                              "vol_part_cm3": vol_part / 1000,
                              "plate_only_cover_pct": cover}

        # ---- G: brim footprint ----------------------------------------
        base = Tp[Tp.mean(1)[:, 2] < 0.4]
        if len(base):
            pts = base.reshape(-1, 2 * 0 + 3)[:, :2]
            # 접지 윤곽의 볼록껍질 둘레로 brim 면적 근사
            from scipy.spatial import ConvexHull
            h = ConvexHull(pts)
            per = 0.0
            v = pts[h.vertices]
            for i in range(len(v)):
                per += np.linalg.norm(v[i] - v[(i + 1) % len(v)])
            a0 = h.volume            # 2D 에서 volume = 면적
            print(f"  --- G [{nm}] brim ---")
            print(f"    접지 볼록껍질 면적 {a0:,.0f} mm2  둘레 {per:,.0f} mm")
            for b in (0, 5, 8, 10):
                print(f"      brim {b:2d} mm -> 총 {a0 + per * b:9,.0f} mm2  "
                      f"(+{100 * per * b / a0:5.1f}%)")
            res[nm]["brim"] = {"hull_area": float(a0), "perimeter": float(per)}
    json.dump(res, open(os.path.join(LOCAL, "reports", "16_joint_qc.json"),
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("")
    print("saved: reports/16_joint_qc.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
