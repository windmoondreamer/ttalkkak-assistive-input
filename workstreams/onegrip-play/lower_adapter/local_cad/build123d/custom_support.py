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

# ---- CONSERVATIVE (V2) -----------------------------------------------------
# V1 실물 출력에서 **천장 첫 레이어가 처졌다**. 원인은 브리지 거리:
#   V1  pitch 10.0 - rib 0.8  =  9.2 mm 를 0.2mm 레이어가 건너야 했다.
# 두 축으로 줄인다 — 간격을 좁히고, 리브 머리를 넓혀 착지 폭을 키운다.
#   V2  MAIN     pitch 6.0 - head 2.0 = 4.0 mm
#       ARMREST  pitch 4.0 - head 2.0 = 2.0 mm
RIB_T = 0.8            # 리브 몸통 두께 (벽 0.6~0.8)
HEAD_W = 2.0           # 천장 접촉 머리 폭 (착지 패드)
HEAD_H = 2.0           # 머리 높이
HEAD_STEPS = 4         # 계단 테이퍼 단수 -> 단 폭 0.15mm (노즐 0.4 미만 = 자립)
RIB_PITCH = {"MAIN": 6.0, "ARMREST": 4.0}
LAT_CLR = 0.40         # 목표 측면 여유 (0.35~0.45)
LAT_TRY = (0.40, 0.25, 0.12)   # 넓은 쪽부터 시도 — 좁혀서라도 받친다
DX = 0.5               # X 표본 간격 (바닥 추종 정밀도)
BOT_CLR = 0.0          # 바닥은 붙어야 인쇄된다
MIN_H = 1.2            # 이보다 낮은 구간은 리브를 세우지 않는다
NOTCH_D = 1.0          # teeth 노치 깊이
NOTCH_L = 2.0          # 노치 길이
TOOTH_PITCH = 12.0     # 이빨 주기 -> 접촉 10.0 : 비접촉 2.0 (V1 은 6:3)
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
    print(f"  rib {RIB_T} mm / head {HEAD_W}x{HEAD_H} ({HEAD_STEPS}단) / "
          f"lateral {LAT_CLR} mm / teeth {TOOTH_PITCH - NOTCH_L}:{NOTCH_L} "
          f"@ {TOOTH_PITCH} mm")
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
        pitch = RIB_PITCH[nm]
        xs = np.arange(xlo, xhi, DX)
        ys = list(np.arange(ylo + pitch / 2, yhi, pitch))
        # 끝단이 pitch/2 넘게 비면 캔틸레버가 된다 -> 가장자리 행을 보강
        if ys and (yhi - ys[-1]) > pitch * 0.55:
            ys.append(yhi - 0.6)
        if ys and (ys[0] - ylo) > pitch * 0.55:
            ys.insert(0, ylo + 0.6)
        ys = np.array(sorted(ys))
        print(f"  pitch {pitch} mm -> 브리지 자유거리 {pitch - HEAD_W:.1f} mm")
        print("")
        print(f"--- {nm}  (Rx {ang:+.0f})  리브 {len(ys)}줄 x X표본 {len(xs)} ---")

        zone = ZONE[nm]
        ribs = []
        n_forb = 0
        n_narrow = 0
        n_tight = 0
        lat_min = LAT_CLR
        for yk in ys:
            open_runs = []          # [(x_last, [(x,a,b), ...])]
            done = []
            for x in xs:
                cols = []
                # 머리는 가장자리(±W/2) 와 여유선(±W/2+LAT) 둘 다 본다.
                # (여유선만 보면 오목 곡면이 그 사이로 파고들어 최대 0.32mm
                #  침범했다 — 실측으로 잡은 결함.)
                dHe = HEAD_W / 2
                dH = HEAD_W / 2 + LAT_CLR
                offs = [-(RIB_T / 2 + c) for c in LAT_TRY] + [0.0]                     + [+(RIB_T / 2 + c) for c in LAT_TRY]                     + [-dH, +dH, -dHe, +dHe]
                for dy in offs:
                    z, nz = ray.hit(float(x), float(yk + dy))
                    cols.append((z, nz))
                nL = len(LAT_TRY)
                zc, nzc = cols[nL]
                lft = [free_intervals(cols[nL - 1 - i][0]) for i in range(nL)]
                rgt = [free_intervals(cols[nL + 1 + i][0]) for i in range(nL)]
                wide = [free_intervals(cols[-4][0]), free_intervals(cols[-3][0]),
                        free_intervals(cols[-2][0]), free_intervals(cols[-1][0])]
                cand = []
                for (a, b, ci) in free_intervals(zc):
                    if b - a < MIN_H + GAP:
                        continue
                    if nzc[ci] > -DOWN_COS:        # 천장이 아래를 보지 않는다
                        continue
                    # 천장(접촉면) 과 바닥(앵커면) 둘 다 검사한다
                    zt_ = zone(to_grip(float(x), float(yk), b))
                    if zt_ == "FORBID":
                        n_forb += 1
                        continue
                    if a > 0.05 and zone(to_grip(float(x), float(yk), a))                             == "FORBID":
                        n_forb += 1
                        continue
                    if zt_ == "NARROW":
                        n_narrow += 1
                    # 측면 여유를 넓은 쪽부터 시도해 **가능한 최대**를 쓴다.
                    # (V2 정정: 고정 0.40 으로만 보면 가장자리 행이 통째로
                    #  버려져 천장 끝단이 캔틸레버로 남는다 — 실제 처짐 원인.)
                    def _fits(fi, a=a, b=b):
                        return any(aa - 0.05 <= a + 0.3 and bb + 0.05 >= b - 0.3
                                   for (aa, bb, _c) in fi)
                    got = -1.0
                    for i, c in enumerate(LAT_TRY):
                        if _fits(lft[i]) and _fits(rgt[i]):
                            got = c
                            break
                    if got < 0:
                        continue
                    lat_min = min(lat_min, got)
                    if got < LAT_CLR - 1e-9:
                        n_tight += 1
                    # 머리(2.0mm)가 들어갈 자리가 있나 — 없으면 몸통만 세운다
                    hok = (zt_ != "NARROW") and all(
                        any(aa - 0.05 <= a + 0.3 and bb + 0.05 >= b - 0.3
                            for (aa, bb, _c) in fi) for fi in wide)
                    cand.append((a, b, hok))
                # x 방향 run 에 붙이기 (z 구간이 겹치면 같은 run)
                nxt = []
                used = [False] * len(cand)
                for (xl, run) in open_runs:
                    if x - xl > DX * 1.6:
                        done.append(run)
                        continue
                    la, lb = run[-1][1], run[-1][2]
                    best, bd_ = -1, 1e9
                    for i, (a, b, _h) in enumerate(cand):
                        if used[i]:
                            continue
                        if min(lb, b) - max(la, a) <= 0.2:
                            continue
                        # 표본 사이 단차 허용치. 크게 두면 폴리곤 **현**이
                        # 모서리를 가로질러 재료를 파고든다 (실측 0.32mm).
                        # dx 0.5 에서 0.6 = 기울기 1.2 (50도) 까지 추종하고
                        # 그보다 급하면 run 을 끊는다.
                        if abs(a - la) > 0.6:
                            continue
                        if abs(b - lb) > 0.6:
                            continue
                        d = abs(a - la) + abs(b - lb)
                        if d < bd_:
                            bd_, best = d, i
                    if best < 0:
                        done.append(run)
                    else:
                        used[best] = True
                        run.append((float(x),) + cand[best])
                        nxt.append((float(x), run))
                for i, c_ in enumerate(cand):
                    if not used[i]:
                        nxt.append((float(x), [(float(x),) + c_]))
                open_runs = nxt
            done += [r for (_x, r) in open_runs]
            for r in done:
                ribs.append((yk, r))

        print(f"  ceiling run {len(ribs)}개  "
              f"(FORBID 제외 {n_forb} / NARROW {n_narrow} / "
              f"측면축소 {n_tight}, 최소 측면여유 {lat_min:.2f}mm)")

        parts = []
        meta = []
        n_head = 0
        for yk, run in ribs:
            if len(run) < 3:
                continue
            # 유효 표본이 끊기면 폴리곤을 **끊는다**. 이어붙이면 직선이 재료를
            # 관통한다 (실제로 12.5mm 침범이 났던 원인).
            segs, cur = [], []
            for (x, a, b, hok) in run:
                zt = b - GAP
                if (x % TOOTH_PITCH) < NOTCH_L:     # teeth: 접촉 끊기
                    zt -= NOTCH_D
                zb = a + BOT_CLR
                if zt - zb < MIN_H:
                    if len(cur) >= 3:
                        segs.append(cur)
                    cur = []
                    continue
                cur.append((x, zb, zt, hok))
            if len(cur) >= 3:
                segs.append(cur)
            for seg in segs:
                pb_ = [(x, zb) for (x, zb, _zt, _h) in seg]
                pt_ = [(x, zt) for (x, _zb, zt, _h) in seg]
                sk = bd.Plane.XZ * bd.Polygon(*(pb_ + pt_[::-1]), align=None)
                sol = (bd.extrude(sk, amount=RIB_T / 2)
                       + bd.extrude(sk, amount=-RIB_T / 2))
                # ---- 계단 테이퍼 머리 --------------------------------------
                # 단 j 는 폭 w_j, 위는 zt 고정, 아래는 j 가 클수록 높다
                # -> 합집합이 아래로 좁아지는 피라미드가 된다 (자립)
                hruns, hc = [], []
                for q in seg:
                    if q[3]:
                        hc.append(q)
                    else:
                        if len(hc) >= 3:
                            hruns.append(hc)
                        hc = []
                if len(hc) >= 3:
                    hruns.append(hc)
                for hr in hruns:
                    n_head += 1
                    for j in range(1, HEAD_STEPS + 1):
                        w = RIB_T + (HEAD_W - RIB_T) * j / HEAD_STEPS
                        drop = HEAD_H * (HEAD_STEPS - j + 1) / HEAD_STEPS
                        hb = [(x, max(zb, zt - drop)) for (x, zb, zt, _h) in hr]
                        ht = [(x, zt) for (x, _zb, zt, _h) in hr]
                        if any(t[1] - b_[1] < 0.05 for b_, t in zip(hb, ht)):
                            continue
                        hk = bd.Plane.XZ * bd.Polygon(*(hb + ht[::-1]),
                                                      align=None)
                        sol = (sol + bd.extrude(hk, amount=w / 2)
                               + bd.extrude(hk, amount=-w / 2))
                parts.append(sol.moved(bd.Location((0, yk, 0))))
                zb0 = min(q[1] for q in seg)
                meta.append({"y": float(yk),
                             "x0": float(seg[0][0]),
                             "x1": float(seg[-1][0]),
                             "len": float(seg[-1][0] - seg[0][0]),
                             "z_bottom": float(zb0),
                             "z_top": float(max(q[2] for q in seg)),
                             "head_runs": len(hruns),
                             "start": "BED" if zb0 < 0.05
                                      else "MODEL_ANCHOR"})

        if not parts:
            print("  support 없음")
            continue
        sup = bd.Compound(children=parts)
        sol = sup.solids()
        vol = sum(float(s.volume) for s in sol)
        print(f"  rib {len(parts)}개 (머리 구간 {n_head}) -> solid {len(sol)}개   "
              f"총 부피 {vol:,.1f} mm3 = {vol / 1000:.2f} cm3   "
              f"질량 약 {vol * 1.24e-3:.1f} g")
        summary[nm] = {"material": mat, "gap_z": GAP, "rib_t": RIB_T,
                       "rib_pitch": pitch, "head_w": HEAD_W, "head_h": HEAD_H,
                       "free_span": pitch - HEAD_W, "lateral": LAT_CLR,
                       "lateral_min": lat_min, "n_tight": n_tight,
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


# ---- 금지 / 제한 영역 (원본 grip frame) -----------------------------------
#   "FORBID" = support 를 아예 붙이지 않는다
#   "NARROW" = 붙이되 **넓은 머리 없이** 0.8mm 선접촉만 (mating 면 흠집 최소화)
#   ""       = 제한 없음
#
# V2 정정: lap mating plane 을 FORBID 로 두었더니, ARMREST 는 CUT FACE DOWN
# 이라 stepped lap 의 상단 mating 면이 **공중 28mm 의 수평 아래보기**가 되어
# 589mm2 가 무지지로 남았고 실물에서 그 면이 처졌다. mating 면은 처지면
# 조립이 안 되고 긁어서 복구도 안 된다 -> NARROW 로 바꿔 받친다.
def _main_zone(g):
    x, y, z = g
    # 외부 팔접촉면 = 램프 평면의 얇은 외피만 (V1 은 7mm 슬래브라 과했다)
    if y < -95.0 and abs(z - SB.pb_z(y)) <= 0.8:
        return "FORBID"
    # M4 insert pilot / seating — 지시대로 CAD support 없이 브리지 출력
    if abs(abs(x) - 40.0) < 5.0 and abs(abs(y + 126.0) - 7.0) < 4.0:
        return "FORBID"
    if SB.Y_UP - 1 < y < SB.Y_LO + 1 and abs((SB.pb_z(y) - z) - SB.LAP_D) < 1.5:
        return "NARROW"
    if (abs(abs(x) - 12.0) < 4.0 and SB.RIB_Y0 - 1 < y < SB.RIB_Y1 + 1
            and SB.LAP_D - 2.5 < (SB.pb_z(y) - z) < SB.LAP_D + 4.5):
        return "NARROW"
    return ""


def _arm_zone(g):
    x, y, z = g
    if y < -95.0 and abs(z - SB.pb_z(y)) <= 0.8:
        return "FORBID"
    # 나사 머리 안착면 — 거칠어지면 안 된다. Ø8 은 브리지로 뽑힌다
    if abs(abs(x) - 40.0) < 6.0 and abs(abs(y + 126.0) - 7.0) < 4.0:
        return "FORBID"
    if SB.Y_UP - 1 < y < SB.Y_LO + 1 and abs((SB.pb_z(y) - z) - SB.LAP_D) < 1.5:
        return "NARROW"
    if (abs(abs(x) - 12.0) < 4.0 and SB.RIB_Y0 - 1 < y < SB.RIB_Y1 + 1
            and SB.LAP_D - 2.5 < (SB.pb_z(y) - z) < SB.LAP_D + 4.5):
        return "NARROW"
    return ""


ZONE = {"MAIN": _main_zone, "ARMREST": _arm_zone}
FORBIDDEN = {k: (lambda g, f=v: f(g) == "FORBID") for k, v in ZONE.items()}


if __name__ == "__main__":
    sys.exit(main())
