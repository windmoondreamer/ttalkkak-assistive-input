"""매립 짐벌 치수 설계기 — (PIVOT_DEPTH, GIMBAL_TRAVEL) 조합별 성립 검사.

    python lower_adapter/scripts/design_embedded.py [--emit]

READ ONLY. Onshape 접근 없음. 로컬 frozen 그립 메시만 쓴다.
--emit 을 주면 FeatureScript 용 상수를 lower_adapter/cad_dump/embedded_constants.json 에 쓴다.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "lower_adapter", "cad_dump")
SHARED = os.path.join(ROOT, "cad_dump")

# ---- 상체 확정 인터페이스 ----
FLANGE_Z = -67.878507
AXIS = np.array([0.0, 27.269160])
BOSS_W, BOSS_D = 31.072, 35.672          # 그립 보스 외형
POST_W, POST_D = 20.272, 25.272
POST_TOP = -53.878507
POCKET_CLR = 0.30
POCKET_DEPTH = 6.20
POST_WALL = 4.00
MIDDLE_ROW_Z = -6.000                    # 중지 버튼 행 (손 기준면)
INDEX_ROW_Z = 9.000

# ---- 하드웨어 ----
BR_OD, BR_ID, BR_W, BR_FIT = 16.0, 5.0, 5.0, 0.15
YOKE_WALL = 2.5        # 스캔 결과 채택 (3.0 이면 p=15/th=10 여유가 0.28 로 부족)
BOSS_OD = BR_OD + BR_FIT + 2 * YOKE_WALL      # 22.15
H_BOSS = BOSS_OD / 2                           # 11.075
SHAFT_D = 5.0                                  # M5 (원본 BOM 과 동일)
TAP_PILOT = 4.2
CLR = 1.5                                      # 구조 여유

# ---- 설계 선택값 ----
A1 = 29.0        # 축1(하우징) 베어링 반경. r 27~33 의 "선반" 중앙
A2 = 32.0        # 축2(링) 베어링 반경, v 방향
SEAT_RECESS = 6.0    # 착좌면을 경사 외피보다 이만큼 아래로
HUB_WALL = 4.0
HUB_FLOOR = 3.5
RING_BAND_H = 12.0
RING_SEC_W = 10.0
HOUSE_WALL = 4.0
HOUSE_FLOOR = 3.5


def load(n):
    return np.asarray(json.load(io.open(os.path.join(SHARED, f"mesh_{n}.json"),
                                        encoding="utf-8"))["tris"], dtype=float)


def rot_u(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_v(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


_G = None


def grip():
    global _G
    if _G is None:
        V = np.vstack([load("INDEX_FINAL_JaD"), load("INDEX_FINAL_JfD")]).reshape(-1, 3)
        V = np.unique(np.round(V, 3), axis=0)
        _G = V[V[:, 2] - FLANGE_Z < 30]
    return _G


def envelope(p, th, ndir=32, combined=True):
    """착좌면 기준 하부 포락선 z_min(r). combined=False 면 축2 회전만(링 기준)."""
    G = grip()
    P = np.array([AXIS[0], AXIS[1], FLANGE_Z - p])
    bins = np.arange(0, 56, 1.0)
    zmin = np.zeros(len(bins) - 1)
    rmax = 0.0
    dirs = np.linspace(0, 360, ndir, endpoint=False) if combined else [90.0, 270.0]
    for A in dirs:
        a = np.radians(A)
        M = rot_u(np.radians(th) * np.cos(a)) @ rot_v(np.radians(th) * np.sin(a))
        W = (G - P) @ M.T + P
        zz = W[:, 2] - FLANGE_Z
        rr = np.linalg.norm(W[:, :2] - AXIS, axis=1)
        m = zz < 0.2
        if m.any():
            rmax = max(rmax, rr[m].max())
        idx = np.clip(np.digitize(rr, bins) - 1, 0, len(bins) - 2)
        for b in range(len(bins) - 1):
            k = idx == b
            if k.any():
                zmin[b] = min(zmin[b], zz[k].min())
    return bins, zmin, rmax


def zmin_at(bins, zmin, r):
    i = int(np.clip(np.digitize(r, bins) - 1, 0, len(zmin) - 1))
    return min(zmin[max(i - 1, 0)], zmin[i], zmin[min(i + 1, len(zmin) - 1)])


def evaluate(p, th, a1=None, verbose=False):
    a1 = A1 if a1 is None else a1
    b, z, rmax = envelope(p, th)
    b2, z2, _ = envelope(p, th, combined=False)
    top = -p + H_BOSS                       # 두 보스 모두 같은 높이 (공통 피벗)
    need1 = zmin_at(b, z, a1) - CLR          # 하우징 보스는 여기보다 아래
    need2 = zmin_at(b2, z2, A2) - CLR        # 링 보스
    d_well = -zmin_at(b, z, 0) if False else -z.min()
    r_well = rmax
    return {
        "p": p, "th": th,
        "boss_top": top,
        "z_axis1": zmin_at(b, z, a1), "margin1": need1 - top,
        "z_axis2": zmin_at(b2, z2, A2), "margin2": need2 - top,
        "well_r": r_well, "well_d": d_well,
        "ring_sweep": (A2 + RING_SEC_W / 2 + H_BOSS) * np.sin(np.radians(th)),
    }


def head(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def main():
    head("A. (PIVOT_DEPTH, GIMBAL_TRAVEL) 조합 성립 검사   a1=%.0f a2=%.0f" % (A1, A2))
    print("  보스 top = -p + %.3f 가  z_min - %.1f  이하여야 한다" % (H_BOSS, CLR))
    print()
    print("   p   th   보스top   축1 z_min  여유1     축2 z_min  여유2    well R   well D   판정")
    rows = []
    for p in (15.0, 16.0, 17.0):
        for th in (10.0, 12.0, 15.0):
            r = evaluate(p, th)
            ok = r["margin1"] >= 0 and r["margin2"] >= 0
            rows.append(r)
            print("  %4.1f %4.1f  %7.2f   %8.2f  %+7.2f    %8.2f  %+7.2f   %6.2f  %6.2f   %s"
                  % (p, th, r["boss_top"], r["z_axis1"], r["margin1"],
                     r["z_axis2"], r["margin2"], r["well_r"], r["well_d"],
                     "OK" if ok else "간섭"))
    head("B. a1 을 줄이면 +-15deg 가 p=15 에서도 되는가")
    for a1 in (30.0, 28.0, 26.0, 24.0, 22.0):
        r = evaluate(15.0, 15.0, a1=a1)
        hub_half_u = BOSS_W / 2 + POCKET_CLR + HUB_WALL
        clash = a1 - (BR_W / 2 + YOKE_WALL) - hub_half_u
        print("   a1=%4.1f  여유1 %+6.2f   허브벽(%.1f)까지 %+6.2f  %s"
              % (a1, r["margin1"], hub_half_u, clash,
                 "OK" if r["margin1"] >= 0 and clash >= 1.0 else "불가"))

    head("C. 최종 치수표 (설계점 p=15, th=10 / 최악 p=17, th=15)")
    for p, th in ((15.0, 10.0), (17.0, 15.0)):
        r = evaluate(p, th)
        hub_half = np.array([BOSS_W / 2 + POCKET_CLR + HUB_WALL,
                             BOSS_D / 2 + POCKET_CLR + HUB_WALL])
        hub_bot = -(POCKET_DEPTH + HUB_FLOOR)
        ring_out_v = A2 + BR_W / 2 + YOKE_WALL
        ring_out_u = A1 - BR_W / 2 - 0.5 + RING_SEC_W / 2
        cav_bot = -p - H_BOSS - r["ring_sweep"] - CLR
        house_bot = cav_bot - HOUSE_FLOOR
        print("  --- p=%.1f  th=%.1f ---" % (p, th))
        print("   허브 plan            %.2f x %.2f mm  (바닥 %.2f)" % (2 * hub_half[0], 2 * hub_half[1], hub_bot))
        print("   허브 팔 끝 v         %.2f  (축2 베어링 안쪽면)" % (A2 - BR_W / 2 - 0.3))
        print("   링 외형 u/v          %.2f x %.2f mm" % (2 * ring_out_u, 2 * ring_out_v))
        print("   링 스윕(수직)        %.2f mm" % r["ring_sweep"])
        print("   well 개구 지름       %.2f mm   깊이 %.2f mm" % (2 * (r["well_r"] + CLR), r["well_d"] + 0.5))
        print("   내부 공동 바닥       %.2f  (착좌면 아래 %.2f)" % (cav_bot, -cav_bot))
        print("   하우징 바닥          %.2f  (착좌면 아래 %.2f)" % (house_bot, -house_bot))
        print("   경사 외피 (착좌면 +) %.2f" % SEAT_RECESS)
        print("   하우징 총 두께(중앙) %.2f mm" % (SEAT_RECESS - house_bot))
        print("   하우징 최소 외형     %.2f mm 각" % (2 * (r["well_r"] + CLR + HOUSE_WALL + 2)))

    head("D. 손 높이 기준면")
    print("  착좌 평면          그립 Z = %.6f" % FLANGE_Z)
    print("  중지 버튼 행       그립 Z = %.3f  -> 착좌면 위 %.3f mm" % (MIDDLE_ROW_Z, MIDDLE_ROW_Z - FLANGE_Z))
    print("  검지 버튼 행       그립 Z = %.3f  -> 착좌면 위 %.3f mm" % (INDEX_ROW_Z, INDEX_ROW_Z - FLANGE_Z))
    print("  -> HAND_REF 는 중지 행(손이 실제로 감기는 최저 위치)으로 정의한다")

    if "--emit" in sys.argv:
        r = evaluate(15.0, 10.0)
        cons = {
            "FLANGE_Z": FLANGE_Z, "AXIS_Y": float(AXIS[1]),
            "PIVOT_DEPTH": 15.0, "GIMBAL_TRAVEL": 10.0,
            "A1": A1, "A2": A2, "BR_OD": BR_OD, "BR_W": BR_W, "BR_FIT": BR_FIT,
            "BOSS_OD": BOSS_OD, "H_BOSS": H_BOSS, "SHAFT_D": SHAFT_D, "TAP_PILOT": TAP_PILOT,
            "YOKE_WALL": YOKE_WALL, "HUB_WALL": HUB_WALL, "HUB_FLOOR": HUB_FLOOR,
            "RING_BAND_H": RING_BAND_H, "RING_SEC_W": RING_SEC_W,
            "HOUSE_WALL": HOUSE_WALL, "HOUSE_FLOOR": HOUSE_FLOOR,
            "SEAT_RECESS": SEAT_RECESS,
            "POCKET_W": BOSS_W + 2 * POCKET_CLR, "POCKET_D": BOSS_D + 2 * POCKET_CLR,
            "POCKET_DEPTH": POCKET_DEPTH, "POST_W": POST_W, "POST_D": POST_D,
            "POST_TOP": POST_TOP, "POST_WALL": POST_WALL,
            "well_r": r["well_r"], "well_d": r["well_d"], "ring_sweep": r["ring_sweep"],
        }
        with io.open(os.path.join(OUT, "embedded_constants.json"), "w", encoding="utf-8") as f:
            json.dump(cons, f, indent=1)
        print("\n  -> embedded_constants.json 기록")


if __name__ == "__main__":
    main()
