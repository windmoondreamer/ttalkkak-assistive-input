"""P1S 전용 CAD-INTEGRATED SACRIFICIAL SUPPORT.

REV D PRODUCT BODY 는 **읽기만** 한다. support 는 완전히 별개 solid 다.

--- 구조 --------------------------------------------------------------------
solid block 금지. print X 방향으로 달리는 **얇은 수직 리브(vertical rib wall)**
를 print Y 로 등간격 배치한다. 리브는 수직벽이므로 그 자체가 support 를
요구하지 않는다 (SUPPORT_FOR_SUPPORT = 0 이 구조적으로 보장된다).

리브 윗면에 주기적 노치를 넣어 **teeth/contact rail** 을 만든다 — 천장에 닿는
구간을 짧게 끊어 떼어내기 쉽게 한다.

--- 간극 --------------------------------------------------------------------
  vertical Z gap     PLA 0.20 / PETG 0.28   (천장 아래)
  lateral clearance  0.40                   (리브 옆면 <-> 제품)
    -> 리브가 y_k 중심 두께 RIB_T 이므로 y_k ± (RIB_T/2 + LAT) 에서도
       같은 구간이 비어 있어야 한다. 3줄 광선으로 교집합을 취한다.

--- 금지 영역 ----------------------------------------------------------------
외부 팔접촉면 / lap mating plane / rib·groove mating / M4 insert pilot 내부 /
insert seating / counterbore seating 은 천장이라도 support 를 붙이지 않는다.
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
DUMP = os.path.join(os.path.dirname(LOCAL), "cad_dump")

# ---- 재료별 파라미터 -------------------------------------------------------
MATERIAL = {
    "PLA": {"gap_z": 0.20},
    "PETG": {"gap_z": 0.28},          # 코드에 남겨둔다. STL 은 지금 안 만든다.
}

RIB_T = 0.8            # 리브 두께 = 천장 접촉 폭 (0.6~0.8 / rail 0.8~1.2)
RIB_PITCH = 10.0       # 리브 간격 (8~12)
LAT_CLR = 0.40         # 측면 여유 (0.35~0.45)
DX = 0.5               # X 표본 간격 (바닥 추종 정밀도)
BOT_CLR = 0.0          # 바닥은 붙어야 인쇄된다
MIN_H = 1.2            # 이보다 낮은 구간은 리브를 세우지 않는다
NOTCH_D = 1.2          # teeth 노치 깊이
NOTCH_L = 3.0          # 노치 길이
TOOTH_PITCH = 9.0      # 이빨 주기 -> 접촉 6.0 / 비접촉 3.0
DOWN_COS = math.sin(math.radians(45.0))   # 0.7071

PARTS = {
    "MAIN": ("HOUSING_V4_MAIN_PRINT_REV_D", -90.0),
    "ARMREST": ("HOUSING_V4_ARMREST_PRINT_REV_D", -90.0),
}


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def load(name):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    return sh


def tris_of(sh, tol=0.05):
    f = os.path.join(P.EXPORT_STL, "_cs.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.3)
    T = G.read_stl_tris(f)
    os.remove(f)
    return T


class Ray:
    """XY 버킷 수직 광선 — 교차 z 와 그 면의 법선 z 성분을 같이 준다."""

    def __init__(self, T, cell=6.0):
        self.T = T
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        mg = np.linalg.norm(n, axis=1)
        self.nz = np.where(mg > 1e-12, n[:, 2] / np.maximum(mg, 1e-12), 0.0)
        self.cell = cell
        self.lo = T.reshape(-1, 3).min(0)[:2]
        i0 = np.floor((T.min(1)[:, :2] - self.lo) / cell).astype(int)
        i1 = np.floor((T.max(1)[:, :2] - self.lo) / cell).astype(int)
        self.b = {}
        for k in range(len(T)):
            for i in range(i0[k, 0], i1[k, 0] + 1):
                for j in range(i0[k, 1], i1[k, 1] + 1):
                    self.b.setdefault((i, j), []).append(k)

    def hit(self, x, y):
        i = int(math.floor((x - self.lo[0]) / self.cell))
        j = int(math.floor((y - self.lo[1]) / self.cell))
        idx = self.b.get((i, j))
        if not idx:
            return np.zeros(0), np.zeros(0)
        t = self.T[idx]
        nz = self.nz[idx]
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
        z = -1e4 + tt[ok]
        s = np.argsort(z)
        z, nn = z[s], nz[ok][s]
        if len(z) == 0:
            return z, nn
        keep = np.concatenate(([True], np.diff(z) > 1e-4))
        return z[keep], nn[keep]


def free_intervals(z):
    """광선이 아래에서 올라올 때의 빈 구간 [(a,b,ceil_idx)] — b 는 천장."""
    out = []
    if len(z) == 0:
        return out
    out.append((0.0, float(z[0]), 0))
    for i in range(1, len(z) - 1, 2):
        out.append((float(z[i]), float(z[i + 1]), i + 1))
    return out


def main():
    mat = sys.argv[1] if len(sys.argv) > 1 else "PLA"
    GAP = MATERIAL[mat]["gap_z"]
    print(f"=== CAD SACRIFICIAL SUPPORT  ({mat}, gap {GAP} mm) ===")
    print(f"  rib {RIB_T} mm / pitch {RIB_PITCH} mm / lateral {LAT_CLR} mm / "
          f"teeth {TOOTH_PITCH - NOTCH_L}:{NOTCH_L} @ {TOOTH_PITCH} mm")
    summary = {}

    for nm, (fn, ang) in PARTS.items():
        prod = load(fn)
        T = tris_of(prod)
        R = rot_x(ang)
        Tp = T @ R.T
        z0 = Tp.reshape(-1, 3)[:, 2].min()
        Tp[:, :, 2] -= z0
        Rt = R                                     # print -> grip : p @ R (z 복원 후)

        def to_grip(px, py, pz):
            v = np.array([px, py, pz + z0])
            return v @ Rt

        ray = Ray(Tp)
        V = Tp.reshape(-1, 3)
        xlo, xhi = V[:, 0].min() + 0.5, V[:, 0].max() - 0.5
        ylo, yhi = V[:, 1].min() + 0.5, V[:, 1].max() - 0.5
        xs = np.arange(xlo, xhi, DX)
        ys = np.arange(ylo + RIB_PITCH / 2, yhi, RIB_PITCH)
        print("")
        print(f"--- {nm}  (Rx {ang:+.0f})  리브 {len(ys)}줄 x X표본 {len(xs)} ---")

        forb = FORBIDDEN[nm]
        ribs = []
        n_forb = 0
        for yk in ys:
            open_runs = []          # [(x_last, [(x,a,b), ...])]
            done = []
            for x in xs:
                cols = []
                for dy in (-(RIB_T / 2 + LAT_CLR), 0.0, +(RIB_T / 2 + LAT_CLR)):
                    z, nz = ray.hit(float(x), float(yk + dy))
                    cols.append((z, nz))
                zc, nzc = cols[1]
                side = [free_intervals(cols[0][0]), free_intervals(cols[2][0])]
                cand = []
                for (a, b, ci) in free_intervals(zc):
                    if b - a < MIN_H + GAP:
                        continue
                    if nzc[ci] > -DOWN_COS:        # 천장이 아래를 보지 않는다
                        continue
                    # 천장(접촉면) 과 바닥(앵커면) 둘 다 금지영역이면 안 된다
                    if forb(to_grip(float(x), float(yk), b)):
                        n_forb += 1
                        continue
                    if a > 0.05 and forb(to_grip(float(x), float(yk), a)):
                        n_forb += 1
                        continue
                    ok = True
                    for fi in side:               # 측면 여유
                        if not any(aa - 0.05 <= a + 0.3 and bb + 0.05 >= b - 0.3
                                   for (aa, bb, _c) in fi):
                            ok = False
                            break
                    if ok:
                        cand.append((a, b))
                # x 방향 run 에 붙이기 (z 구간이 겹치면 같은 run)
                nxt = []
                used = [False] * len(cand)
                for (xl, run) in open_runs:
                    if x - xl > DX * 1.6:
                        done.append(run)
                        continue
                    la, lb = run[-1][1], run[-1][2]
                    best, bd_ = -1, 1e9
                    for i, (a, b) in enumerate(cand):
                        if used[i]:
                            continue
                        if min(lb, b) - max(la, a) <= 0.2:
                            continue
                        if abs(a - la) > 0.8:     # 바닥이 튀면 run 을 끊는다
                            continue              # -> 리브 밑면이 뜨지 않는다
                        if abs(b - lb) > 2.0:     # 천장이 튀면 run 을 끊는다
                            continue              # -> 윗면 대각선이 재료를 안 뚫는다
                        d = abs(a - la) + abs(b - lb)
                        if d < bd_:
                            bd_, best = d, i
                    if best < 0:
                        done.append(run)
                    else:
                        used[best] = True
                        run.append((float(x), cand[best][0], cand[best][1]))
                        nxt.append((float(x), run))
                for i, (a, b) in enumerate(cand):
                    if not used[i]:
                        nxt.append((float(x), [(float(x), a, b)]))
                open_runs = nxt
            done += [r for (_x, r) in open_runs]
            for r in done:
                ribs.append((yk, r))

        print(f"  ceiling run {len(ribs)}개  (forbidden 제외 표본 {n_forb})")

        parts = []
        meta = []
        for yk, run in ribs:
            if len(run) < 3:
                continue
            # 유효 표본이 끊기면 폴리곤을 **끊는다**. 이어붙이면 직선이 재료를
            # 관통한다 (실제로 12.5mm 침범이 났던 원인).
            segs, cur = [], []
            for (x, a, b) in run:
                zt = b - GAP
                if (x % TOOTH_PITCH) < NOTCH_L:     # teeth: 접촉 끊기
                    zt -= NOTCH_D
                zb = a + BOT_CLR
                if zt - zb < MIN_H:
                    if len(cur) >= 3:
                        segs.append(cur)
                    cur = []
                    continue
                cur.append((x, zb, zt))
            if len(cur) >= 3:
                segs.append(cur)
            for seg in segs:
                pb_ = [(x, zb) for (x, zb, _zt) in seg]
                pt_ = [(x, zt) for (x, _zb, zt) in seg]
                sk = bd.Plane.XZ * bd.Polygon(*(pb_ + pt_[::-1]), align=None)
                sol = (bd.extrude(sk, amount=RIB_T / 2)
                       + bd.extrude(sk, amount=-RIB_T / 2))
                parts.append(sol.moved(bd.Location((0, yk, 0))))
                zb0 = min(q[1] for q in seg)
                meta.append({"y": float(yk),
                             "x0": float(seg[0][0]),
                             "x1": float(seg[-1][0]),
                             "len": float(seg[-1][0] - seg[0][0]),
                             "z_bottom": float(zb0),
                             "z_top": float(max(q[2] for q in seg)),
                             "start": "BED" if zb0 < 0.05
                                      else "MODEL_ANCHOR"})

        if not parts:
            print("  support 없음")
            continue
        sup = parts[0]
        for q in parts[1:]:
            sup = sup + q
        sol = sup.solids()
        vol = sum(float(s.volume) for s in sol)
        print(f"  rib {len(parts)}개 -> support solid {len(sol)}개   "
              f"총 부피 {vol:,.1f} mm3 = {vol / 1000:.2f} cm3   "
              f"질량 약 {vol * 1.24e-3:.1f} g")
        summary[nm] = {"material": mat, "gap_z": GAP, "rib_t": RIB_T,
                       "rib_pitch": RIB_PITCH, "lateral": LAT_CLR,
                       "n_rib": len(parts), "chunks": len(sol),
                       "ribs": meta,
                       "volume_mm3": vol, "mass_g": vol * 1.24e-3,
                       "z0": float(z0), "rot_x": ang}
        np.save(os.path.join(DUMP, f"_sup_z0_{nm}.npy"), np.array([z0, ang]))
        BRepTools.Clean_s(sup.wrapped)
        bd.export_step(sup, os.path.join(P.EXPORT_STEP,
                                         f"{nm}_CUSTOM_SUPPORT_{mat}.step"))
        bd.export_stl(sup, os.path.join(P.EXPORT_STL,
                                        f"{nm}_CUSTOM_SUPPORT_{mat}.stl"),
                      tolerance=0.02, angular_tolerance=0.15)
        nb = sum(1 for m in meta if m["start"] == "BED")
        na = len(meta) - nb
        print(f"  build-plate-start {nb}개 / MODEL_ANCHOR {na}개")
        if na:
            am = [m for m in meta if m["start"] == "MODEL_ANCHOR"]
            am.sort(key=lambda m: -m["len"])
            print(f"    anchor neck = {RIB_T} mm x 접촉길이 "
                  f"{min(m['len'] for m in am):.1f}~{max(m['len'] for m in am):.1f} mm")
            for m in am[:6]:
                print(f"      y {m['y']:+7.1f}  x {m['x0']:+7.1f}~{m['x1']:+7.1f}  "
                      f"neck {RIB_T:.1f} x {m['len']:.1f} mm  z {m['z_bottom']:.1f}"
                      f"->{m['z_top']:.1f}")
        print(f"  저장 {nm}_CUSTOM_SUPPORT_{mat}.step / .stl")

    json.dump(summary, open(os.path.join(LOCAL, "reports",
                                         f"16_custom_support_{mat}.json"),
                            "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("")
    print(f"saved: reports/16_custom_support_{mat}.json")
    return 0


# ---- 금지 영역 (원본 grip frame) -------------------------------------------
def _main_forbidden(g):
    x, y, z = g
    # 외부 팔접촉면 (상판 윗면) — 램프 평면 근처 위쪽
    if y < -95.0 and (SB.pb_z(y) + 6.5) > z > (SB.pb_z(y) - 0.5):
        return True
    # lap mating plane
    if SB.Y_UP - 1 < y < SB.Y_LO + 1 and abs((SB.pb_z(y) - z) - SB.LAP_D) < 1.5:
        return True
    # rib / groove
    if (abs(abs(x) - 12.0) < 4.0 and SB.RIB_Y0 - 1 < y < SB.RIB_Y1 + 1
            and SB.LAP_D - 2.5 < (SB.pb_z(y) - z) < SB.LAP_D + 4.5):
        return True
    # M4 insert pilot / seating
    if (abs(abs(x) - 40.0) < 5.0 and abs(abs(y + 126.0) - 7.0) < 4.0):
        return True
    return False


def _arm_forbidden(g):
    x, y, z = g
    if y < -95.0 and (SB.pb_z(y) + 6.5) > z > (SB.pb_z(y) - 0.5):
        return True
    if SB.Y_UP - 1 < y < SB.Y_LO + 1 and abs((SB.pb_z(y) - z) - SB.LAP_D) < 1.5:
        return True
    if (abs(abs(x) - 12.0) < 4.0 and SB.RIB_Y0 - 1 < y < SB.RIB_Y1 + 1
            and SB.LAP_D - 2.5 < (SB.pb_z(y) - z) < SB.LAP_D + 4.5):
        return True
    # counterbore seating
    if (abs(abs(x) - 40.0) < 6.0 and abs(abs(y + 126.0) - 7.0) < 4.0):
        return True
    return False


FORBIDDEN = {"MAIN": _main_forbidden, "ARMREST": _arm_forbidden}


if __name__ == "__main__":
    sys.exit(main())
