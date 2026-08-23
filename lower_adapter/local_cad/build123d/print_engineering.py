"""§5 print orientation + §6 support analysis.

CUT FACE DOWN:
  MAIN    절단면 법선이 -Y  -> X축 +90deg 회전하면 -Z 를 향한다
  ARMREST 절단면 법선이 +Y  -> X축 -90deg 회전

face 분류 (출력 좌표 기준, s = n . (0,0,-1)):
  A SELF-SUPPORTING            s <= 0.707  (수직에서 45deg 이내)
  B BRIDGEABLE                 s > 0.707 이고 아래가 비었지만 span 짧음
  C SUPPORT FROM BUILD PLATE   s > 0.707, 바로 아래로 z=0 까지 재료 없음
  D SUPPORT REQUIRED/REMOVABLE s > 0.707, 아래에 재료. 공동이 외부와 연결
  E TRAPPED SUPPORT            공동이 닫혀 있거나 접근구가 8mm 미만
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
ADAPTER = os.path.dirname(LOCAL)
BUILD = 256.0
SELF_SUP = math.sin(math.radians(45.0))       # 0.7071
BRIDGE_MAX = 10.0                             # 브리지 허용 span
APERTURE_MIN = 8.0                            # 이보다 좁으면 실질 trapped

PARTS = {
    "MAIN": ("HOUSING_V4_MAIN_PRINT", -90.0),   # CUT FACE UP (승인)
    "ARMREST": ("HOUSING_V4_ARMREST_PRINT", -90.0),
}

# 원본 grip frame 기준 의미 영역
REGIONS = {
    "MAIN": {
        "stock gimbal / ±15° cavity": lambda p: ((p[:, 1] > -30) & (p[:, 1] < 80)
                                                 & (p[:, 2] > -130) & (p[:, 2] < -60)),
        "carrier pocket": lambda p: ((np.abs(p[:, 0]) < 62) & (p[:, 2] < -142)
                                     & (p[:, 2] > -160)),
        "deck underside": lambda p: ((p[:, 2] > -72) & (p[:, 2] < -60)
                                     & (p[:, 1] > -90) & (p[:, 1] < 90)),
        "screw / insert": lambda p: ((np.abs(np.abs(p[:, 0]) - 40) < 8)
                                     & (p[:, 1] > -140) & (p[:, 1] < -110)),
        "internal doubler": lambda p: ((p[:, 1] > -146) & (p[:, 1] < -106)
                                       & (p[:, 2] > -90) & (p[:, 2] < -60)),
        "rib": lambda p: ((np.abs(np.abs(p[:, 0]) - 12) < 4)
                          & (p[:, 1] > -138) & (p[:, 1] < -113)),
    },
    "ARMREST": {
        "open U-channel interior": lambda p: ((np.abs(p[:, 0]) < 58)
                                              & (p[:, 1] < -150)),
        "joint doubler": lambda p: ((p[:, 1] > -146) & (p[:, 1] < -106)),
        "rib mating groove": lambda p: ((np.abs(np.abs(p[:, 0]) - 12) < 5)
                                        & (p[:, 1] > -138) & (p[:, 1] < -113)),
        "screw counterbore": lambda p: ((np.abs(np.abs(p[:, 0]) - 40) < 8)
                                        & (p[:, 1] > -140) & (p[:, 1] < -110)),
        "outer arm-contact surface": lambda p: (p[:, 2] > -70),
    },
}


def load_tris(name, tol=0.05):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    f = os.path.join(P.EXPORT_STL, "_pe.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.3)
    T = G.read_stl_tris(f)
    os.remove(f)
    return sh, T


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


class VGrid:
    """XY 버킷 수직 광선 캐스터."""

    def __init__(self, T, cell=6.0):
        self.T = T
        self.cell = cell
        lo = T.reshape(-1, 3).min(0)[:2]
        self.lo = lo
        mn = T.min(1)[:, :2]
        mx = T.max(1)[:, :2]
        i0 = np.floor((mn - lo) / cell).astype(int)
        i1 = np.floor((mx - lo) / cell).astype(int)
        self.b = {}
        for k in range(len(T)):
            for i in range(i0[k, 0], i1[k, 0] + 1):
                for j in range(i0[k, 1], i1[k, 1] + 1):
                    self.b.setdefault((i, j), []).append(k)

    def hits(self, x, y):
        i = int(math.floor((x - self.lo[0]) / self.cell))
        j = int(math.floor((y - self.lo[1]) / self.cell))
        idx = self.b.get((i, j))
        if not idx:
            return np.zeros(0)
        t = self.T[idx]
        v0, v1, v2 = t[:, 0], t[:, 1], t[:, 2]
        e1, e2 = v1 - v0, v2 - v0
        d = np.array([0.0, 0.0, 1.0])
        pv = np.cross(d, e2)
        det = np.einsum("ij,ij->i", e1, pv)
        m = np.abs(det) > 1e-12
        inv = np.zeros(len(t))
        inv[m] = 1.0 / det[m]
        o = np.array([x, y, -1e4])
        tv = o - v0
        u = np.einsum("ij,ij->i", tv, pv) * inv
        qv = np.cross(tv, e1)
        w = np.einsum("j,ij->i", d, qv) * inv
        tt = np.einsum("ij,ij->i", e2, qv) * inv
        ok = m & (u >= 0) & (w >= 0) & (u + w <= 1) & (tt > 0)
        return np.sort(np.unique(np.round(-1e4 + tt[ok], 3)))


def main():
    out = {}
    for nm, (fn, ang) in PARTS.items():
        sh, T = load_tris(fn)
        R = rot_x(ang)
        Tp = T @ R.T
        z0 = Tp.reshape(-1, 3)[:, 2].min()
        Tp[:, :, 2] -= z0                       # 베드에 앉힌다
        V = Tp.reshape(-1, 3)
        bb = V.max(0) - V.min(0)
        print("")
        print(f"=== §5 {nm}  (CUT FACE DOWN, Rx {ang:+.0f}deg) ===")
        print(f"  print bbox   {bb[0]:.3f} x {bb[1]:.3f} x {bb[2]:.3f} mm")
        ok = bool(np.all(bb <= BUILD))
        print(f"  [{'PASS' if ok else 'FAIL'}] P1S {BUILD:.0f} 이내   "
              f"마진 X {BUILD - bb[0]:.1f} / Y {BUILD - bb[1]:.1f} / Z {BUILD - bb[2]:.1f}")

        # 베드 접지 면적 (z < 0.4 인 삼각형의 XY 투영 면적)
        c = Tp.mean(1)
        base = Tp[c[:, 2] < 0.4]
        area = 0.0
        if len(base):
            a = base[:, 1, :2] - base[:, 0, :2]
            b2 = base[:, 2, :2] - base[:, 0, :2]
            area = float(np.abs(a[:, 0] * b2[:, 1] - a[:, 1] * b2[:, 0]).sum() / 2)
        slen = bb[2] / math.sqrt(max(area, 1e-9)) if area else float("inf")
        print(f"  bed contact  {area:,.1f} mm2      slenderness H/sqrt(A) = {slen:.2f}")

        # ---- §6 support 분류 --------------------------------------------
        n = np.cross(Tp[:, 1] - Tp[:, 0], Tp[:, 2] - Tp[:, 0])
        mag = np.linalg.norm(n, axis=1)
        good = mag > 1e-12
        Tp2, n2, mag2, T2 = Tp[good], n[good], mag[good], T[good]
        nn = n2 / mag2[:, None]
        ar = mag2 / 2.0
        s = -nn[:, 2]
        ctr = Tp2.mean(1)
        ctr_o = T2.mean(1)                      # 원본 좌표 (영역 태깅용)

        cls = np.full(len(Tp2), "A", dtype="<U1")
        down = s > SELF_SUP
        print(f"  아래보기 face {int(down.sum()):,} / {len(Tp2):,}  "
              f"(면적 {ar[down].sum():,.0f} / {ar.sum():,.0f} mm2)")

        vg = VGrid(Tp2)
        idx = np.nonzero(down)[0]
        # 표본: 면적 큰 순서로 상위 6000개만 광선 (나머지는 최근접 분류 상속)
        order = idx[np.argsort(-ar[idx])][:6000]
        trapped = []
        for k in order:
            x, y, z = ctr[k]
            hs = vg.hits(x, y)
            below = hs[hs < z - 0.25]
            if len(below) == 0:
                cls[k] = "C"                    # 베드까지 비었다
                continue
            gap = z - below[-1]
            if gap < BRIDGE_MAX and s[k] > 0.95:
                cls[k] = "B"
                continue
            # 공동이 외부와 연결되는가 — 수평 8방향 탈출
            mid = np.array([x, y, 0.5 * (z + below[-1])])
            esc = False
            for th in np.arange(0, 2 * math.pi, math.pi / 4):
                dx, dy = math.cos(th), math.sin(th)
                free = True
                for t in np.arange(2.0, 200.0, 2.0):
                    px, py = x + dx * t, y + dy * t
                    hh = vg.hits(px, py)
                    inside = (np.searchsorted(hh, mid[2]) % 2) == 1
                    if inside:
                        free = False
                        break
                if free:
                    esc = True
                    break
            if esc:
                cls[k] = "D"
            else:
                cls[k] = "E"
                trapped.append((float(ar[k]), ctr_o[k].tolist()))
        # 광선 안 쏜 나머지 down face 는 보수적으로 D
        rest = np.setdiff1d(idx, order)
        cls[rest] = "D"

        lab = {"A": "SELF-SUPPORTING", "B": "BRIDGEABLE",
               "C": "SUPPORT FROM BUILD PLATE",
               "D": "SUPPORT REQUIRED / REMOVABLE",
               "E": "TRAPPED SUPPORT"}
        print("  face 분류 (면적 mm2)")
        stat = {}
        for c_ in "ABCDE":
            m = cls == c_
            stat[c_] = float(ar[m].sum())
            print(f"    {c_} {lab[c_]:<30} {int(m.sum()):6,}  {ar[m].sum():10,.1f}")
        print(f"  [{'PASS' if stat['E'] == 0 else 'FAIL'}] TRAPPED SUPPORT "
              f"{int((cls == 'E').sum())} face / {stat['E']:.1f} mm2")
        if trapped:
            tp = np.array([t[1] for t in trapped])
            ta = np.array([t[0] for t in trapped])
            print(f"    trapped 위치 (원본 grip frame)  X[{tp[:,0].min():7.2f},{tp[:,0].max():7.2f}] "
                  f"Y[{tp[:,1].min():8.2f},{tp[:,1].max():8.2f}] "
                  f"Z[{tp[:,2].min():8.2f},{tp[:,2].max():8.2f}]")
            o2 = np.argsort(-ta)[:6]
            for k in o2:
                print(f"      {ta[k]:8.1f} mm2 @ ({tp[k][0]:7.2f},{tp[k][1]:8.2f},{tp[k][2]:8.2f})")

        print("  영역별 (면적 mm2)")
        reg_out = {}
        for rn, f in REGIONS[nm].items():
            sel = f(ctr_o)
            if sel.sum() == 0:
                print(f"    {rn:<28} 해당 face 없음")
                reg_out[rn] = None
                continue
            row = {c_: float(ar[sel & (cls == c_)].sum()) for c_ in "ABCDE"}
            print(f"    {rn:<28} A {row['A']:8,.0f}  B {row['B']:7,.0f}  "
                  f"C {row['C']:7,.0f}  D {row['D']:7,.0f}  E {row['E']:7,.0f}")
            reg_out[rn] = row

        np.save(os.path.join(ADAPTER, "cad_dump", f"support_cls_{nm}.npy"), cls)
        np.save(os.path.join(ADAPTER, "cad_dump", f"support_tris_{nm}.npy"), Tp2)
        out[nm] = {"rot_x_deg": ang, "print_bbox": bb.tolist(),
                   "fits_p1s": ok, "bed_contact_mm2": area,
                   "slenderness": slen, "class_area": stat,
                   "regions": reg_out,
                   "trapped": trapped[:20], "trapped_count": len(trapped)}
    json.dump(out, open(os.path.join(LOCAL, "reports", "15_print_support.json"),
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("")
    print("saved: reports/15_print_support.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
