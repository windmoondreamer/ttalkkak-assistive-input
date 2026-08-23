"""P1S 출력용 2분할 파생 모델 — 분할 + joint + fastener 만. 형상 재설계 없음.

원본 `ERGO_HOUSING_25_WRAP_FINAL_V4` 는 읽기만 한다.

--- 실측으로 확정한 단면 (Y = -121) -----------------------------------------
  |X| <= 56     Z -70.81..-64.81   6.00 mm    상판
  |X| ~ 58..62  Z -138.28..-72.43  65.85 mm   좌우 측벽
  |X| > 64      없음
팔받침은 **U 형 채널**이다. 밑이 열려 있어 joint 구간에만 상판 밑에 doubler 를
덧댈 수 있고, 측벽 안쪽이라 외부 실루엣은 변하지 않는다.

  (앞선 실패: 17.50mm 통짜 슬래브로 오독 -> Z half-lap 3+3mm 불가능,
   지면 평행 랩 평면은 슬래브보다 43mm 아래를 지나 butt 절단이 됐다.)

--- JOINT -------------------------------------------------------------------
상판은 지면이 아니라 **램프에 평행**하다 (grip frame 에서 z = 0.0875*y + c, 5.0deg).
랩 평면도 그 면에 평행하게 잡는다.

  DOUBLER   상판 밑 14mm, X[-58,58], Y[-146,-106]  (채널 안, 숨은 보강)
  Z_LAP     상판 밑면에서 7mm 아래
  upper zone (랩 평면 위)  경계 Y = Y_UP = -140  -> FRONT 는 Y <= -140
  lower zone (랩 평면 아래) 경계 Y = Y_LO = -112  -> FRONT 는 Y <= -112
  겹침 28mm 구간에서 아래=FRONT / 위=MAIN 로 교차 적층

  **FRONT 가 뒤로 물린다.** 반대면 MAIN 이 앞으로 늘어나 CUT FACE DOWN 높이가
  256mm 를 넘는다 (실측 228.8 -> 256.8).

  나사는 아래에서 위로 — FRONT 아래 블록 관통 -> MAIN 위 블록+상판 insert.
  채널이 아래로 열려 있어 공구가 그대로 들어간다.
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
import build123d as bd                                    # noqa: E402
from OCP.BRepTools import BRepTools                       # noqa: E402
from OCP.BRepCheck import BRepCheck_Analyzer              # noqa: E402

LOCAL = os.path.dirname(HERE)
SRC = "ERGO_HOUSING_25_WRAP_FINAL_V4"

# ---- 상판 밑면 평면 (실측) -------------------------------------------------
#   Y=-135 -> z=-72.03,  Y=-107 -> z=-69.58   =>  dz/dy = 0.0875
PB_SLOPE = 0.0875
PB_Y0, PB_Z0 = -121.0, -70.81          # 기준점
PB_N = np.array([0.0, -PB_SLOPE, 1.0])
PB_N = PB_N / np.linalg.norm(PB_N)


def pb_z(y):
    return PB_Z0 + PB_SLOPE * (y - PB_Y0)


# ---- joint 파라미터 -------------------------------------------------------
Y_UP = -140.0          # 랩 평면 위 경계 (MAIN 이 앞으로 나오는 한계)
Y_LO = -112.0          # 랩 평면 아래 경계 (FRONT 가 뒤로 물리는 한계)
OVERLAP = Y_LO - Y_UP                   # 28.0
DBL_Y0, DBL_Y1 = -146.0, -106.0         # doubler 범위 (랩보다 6mm 여유)
# --- doubler 폭: **테이퍼** ---------------------------------------------
# 상수 63.0 은 joint 앞쪽 외피를 최대 7.2mm 뚫고 나온다 (실측).
# V4 외곽 반폭을 X 광선으로 재면 앞으로 갈수록 **그리고 위로 갈수록** 좁아지고
# 상판 밑면(off 0)이 가장 좁다:
#     Y -148 -> 55.81 / Y -108 -> 60.30   (0.11225 mm per mm)
# 각 Y 에서 그 최솟값 - 2.0 을 doubler 반폭으로 쓴다.
DBL_W0 = 55.81 + (-146.0 + 148.0) * 0.11225 - 2.0     # Y=-146  약 54.03
DBL_W1 = 55.81 + (-106.0 + 148.0) * 0.11225 - 2.0     # Y=-106  약 58.53
DBL_X = max(DBL_W0, DBL_W1)   # 하위 호환 (참조용)
DBL_TOP_OVER = 1.0      # 원본 6mm 상판 **안쪽**으로 물려 융합 (바깥으로 안 키운다)
DBL_T = 14.0                            # doubler 두께 (상판 밑면 기준)
LAP_D = 7.0                             # 상판 밑면 -> 랩 평면
# joint clearance — **CONFIRMED 0.30 mm/side** (REV D)
#   실물 clearance 쿠폰 없이 확정. 근거: P1S 일반 FDM 치수 편차 +
#   M4 4개 clamp 체결 구조. press-fit 이 아니라 조립성 + rib/lap 위치결정용이며
#   0.30 의 소량 유격은 나사가 최종 clamp 하므로 허용한다.
#   male/female nominal total clearance = 0.60 mm
CLR = 0.30

RIB_X = (-12.0, 12.0)
RIB_W, RIB_H = 5.0, 2.5
RIB_Y0, RIB_Y1 = -137.0, -115.0

SCREW = [(-40.0, -133.0), (-40.0, -119.0), (40.0, -133.0), (40.0, -119.0)]
# M4 counterbore — **CONFIRMED Ø8.0 x 4.2** (REV D)
#   DIN912 / ISO4762 M4 socket-cap head = Ø7.0 x 4.0 -> 깊이 3.0 은 1.0 부족했다.
D_CLEAR, D_CBORE, L_CBORE = 4.5, 8.0, 4.2
# M4 heat-set insert pilot — **CONFIRMED 5.2mm** (REV C)
#   근거: 기존 Galaxy Tab housing 약 5.15 사용 / 동일 M4 insert /
#         JOINT_FIT_COUPON 실물 출력 확인 -> 5.2 채택 (5.6 은 provisional 이었다)
D_INSERT, L_INSERT = 5.2, 8.0

BIG = 900.0


def load(name=SRC):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    return sh


def plate_plane(offset, y_ref=-121.0):
    """상판 밑면에서 offset 만큼 **아래**로 내린 평행 평면."""
    o = np.array([0.0, y_ref, pb_z(y_ref)]) - PB_N * offset
    return bd.Plane(origin=tuple(o), z_dir=tuple(PB_N))


def halfspace(offset, below=True, y_ref=-121.0):
    pl = plate_plane(offset, y_ref)
    return bd.extrude(pl * bd.Rectangle(BIG, BIG), amount=-BIG if below else BIG)


def ybox(y_max=None, y_min=None):
    lo = -BIG if y_min is None else y_min
    hi = BIG if y_max is None else y_max
    return bd.Box(BIG, hi - lo, BIG).locate(bd.Location((0, 0.5 * (lo + hi), 0)))


def doubler():
    """상판 밑 doubler — 테이퍼 사다리꼴 프리즘.

    상단을 상판 안쪽으로 DBL_TOP_OVER 만큼 물려 융합을 보장한다.
    (예전엔 폭을 63 으로 키워 융합시켰는데 그게 외피를 뚫었다.)
    """
    slab = halfspace(-DBL_TOP_OVER, below=True) - halfspace(DBL_T, below=True)
    pts = [(-DBL_W0, DBL_Y0), (DBL_W0, DBL_Y0),
           (DBL_W1, DBL_Y1), (-DBL_W1, DBL_Y1)]
    sk = bd.Plane.XY * bd.Polygon(*pts, align=None)
    lim = bd.extrude(sk, amount=BIG / 2) + bd.extrude(sk, amount=-BIG / 2)
    return slab & lim


def ribs(grow=0.0):
    """랩 평면에서 **아래로** 내려가는 종방향 리브 (MAIN 소유).

    함정 2건을 실측으로 확인하고 축을 명시한 Box 로 만든다:
      1) `bd.Plane(origin, z_dir=PB_N)` 의 **자동 x_dir 이 예상과 반대**라
         Rectangle(5, 22) 의 축이 뒤바뀌었다 (실측 X 폭 22 / Y 폭 5.33).
      2) `.moved(Location((x, y_mid, 0)))` 는 **상대 이동**이라 평면 원점
         y_ref=-121 에 -126 이 더해져 Y=-247 로 날아갔다.
    그 결과 리브가 팔받침 한가운데에 파묻혀 MAIN 에서 분리되고(440mm3 x2),
    FRONT 에는 갇힌 내부 공동 2개가 생겼다.
    """
    EMB = 1.5                                   # MAIN 살 안으로 물리는 깊이
    ang = math.degrees(math.atan(PB_SLOPE))     # 상판 기울기 (약 5.0deg)
    h = EMB + RIB_H + grow
    w = RIB_W + 2 * grow
    ln = (RIB_Y1 - RIB_Y0) + 2 * grow
    y_mid = 0.5 * (RIB_Y0 + RIB_Y1)
    out = None
    for x in RIB_X:
        # 리브 상단이 랩 평면에서 EMB 만큼 **위**, 하단이 RIB_H 만큼 아래
        top = np.array([x, y_mid, pb_z(y_mid)]) - PB_N * (LAP_D - EMB)
        ctr = top - PB_N * (h / 2.0)
        r = bd.Box(w, ln, h).locate(bd.Location(tuple(ctr), (ang, 0, 0)))
        out = r if out is None else out + r
    return out


def part_front(clr=0.0):
    """FRONT 조각이 차지하는 영역."""
    upper = ybox(y_max=Y_UP - clr) & halfspace(LAP_D + clr, below=False)
    lower = ybox(y_max=Y_LO - clr) & halfspace(LAP_D + clr, below=True)
    reg = upper + lower
    r = ribs(grow=clr)
    if r is not None:
        reg = reg - r
    return reg


def screw_tools():
    """축은 상판 법선. 아래에서 위로."""
    clear = cbore = ins = None
    for x, y in SCREW:
        # 랩 평면 위의 점
        base = np.array([x, y, pb_z(y)]) - PB_N * LAP_D
        pl_lap = bd.Plane(origin=tuple(base), z_dir=tuple(PB_N))
        # 아래 블록 바닥
        pl_bot = bd.Plane(origin=tuple(base - PB_N * (DBL_T - LAP_D)),
                          z_dir=tuple(PB_N))
        c = bd.extrude(pl_bot * bd.Circle(D_CLEAR / 2), amount=DBL_T)
        b = bd.extrude(pl_bot * bd.Circle(D_CBORE / 2), amount=L_CBORE)
        i = bd.extrude(pl_lap * bd.Circle(D_INSERT / 2), amount=L_INSERT)
        clear = c if clear is None else clear + c
        cbore = b if cbore is None else cbore + b
        ins = i if ins is None else ins + i
    return clear, cbore, ins


def biggest(sh, label):
    sol = sh.solids()
    big = max(sol, key=lambda s: float(s.volume))
    drop = [float(s.volume) for s in sol if s is not big]
    if drop:
        print(f"  [{label}] solid {len(sol)} - 부스러기 {len(drop)}개 제거 "
              f"{['%.3f' % d for d in drop]}")
    return big


def main():
    v4 = load()
    v4v = float(v4.volume)
    print(f"[원본] {SRC}  vol {v4v:,.3f} mm3")
    print(f"[joint] Y_UP {Y_UP} / Y_LO {Y_LO} / overlap {OVERLAP} mm / "
          f"lap_depth {LAP_D} / doubler {DBL_T} / clr {CLR}")

    dbl = doubler()
    print(f"  doubler vol(자유) {float(dbl.volume):,.1f}")
    base = v4 + dbl
    base = biggest(base, "BASE")
    addv = float(base.volume) - v4v
    print(f"  V4 + doubler  vol {float(base.volume):,.3f}  (+{addv:,.3f})")
    if addv < 100.0:
        print("  [경고] doubler 가 거의 안 붙었다 - 위치 재확인 필요")

    pf_nom = part_front(0.0)
    pf_clr = part_front(CLR)
    main_p = base - pf_nom
    front_p = base & pf_clr
    mv, fv = float(main_p.volume), float(front_p.volume)
    print(f"  분할 직후  MAIN {mv:,.1f}  FRONT {fv:,.1f}  합 {mv + fv:,.1f}  "
          f"(틈 {float(base.volume) - mv - fv:,.1f})")

    clear, cbore, ins = screw_tools()
    m2 = main_p - ins
    f2 = front_p - clear - cbore
    print(f"  나사 후    MAIN {float(m2.volume):,.1f} (-{mv - float(m2.volume):,.1f})"
          f"   FRONT {float(f2.volume):,.1f} (-{fv - float(f2.volume):,.1f})")
    if (mv - float(m2.volume)) < 10.0 or (fv - float(f2.volume)) < 10.0:
        print("  [경고] 나사 도구가 재료를 거의 안 잘랐다 - 위치 재확인 필요")

    out = {}
    for nm, sh, fn in (("MAIN", m2, "HOUSING_V4_MAIN_PRINT"),
                       ("ARMREST", f2, "HOUSING_V4_ARMREST_PRINT")):
        sh = biggest(sh, nm)
        bb = sh.bounding_box()
        valid = BRepCheck_Analyzer(sh.wrapped).IsValid()
        nsh = len(sh.shells())
        print(f"  [{nm}] solids 1  shells {nsh}  valid {valid}  "
              f"vol {float(sh.volume):,.3f}")
        if nsh != 1:
            print(f"  [경고] {nm} shells {nsh} - 내부 공동 {nsh - 1}개")
        print(f"        bbox {float(bb.size.X):.3f} x {float(bb.size.Y):.3f} x "
              f"{float(bb.size.Z):.3f}   Y[{float(bb.min.Y):.2f},{float(bb.max.Y):.2f}]")
        BRepTools.Clean_s(sh.wrapped)
        bd.export_step(sh, os.path.join(P.EXPORT_STEP, fn + ".step"))
        bd.export_stl(sh, os.path.join(P.EXPORT_STL, fn + ".stl"),
                      tolerance=0.030, angular_tolerance=0.15)
        print(f"        저장 {fn}.step / .stl")
        out[nm] = {"volume": float(sh.volume), "file": fn,
                   "bbox": [float(bb.size.X), float(bb.size.Y), float(bb.size.Z)],
                   "y": [float(bb.min.Y), float(bb.max.Y)],
                   "valid": bool(valid), "shells": len(sh.shells())}

    out["joint"] = {"y_up": Y_UP, "y_lo": Y_LO, "overlap": OVERLAP,
                    "lap_depth": LAP_D, "doubler_t": DBL_T,
                    "doubler_x": DBL_X, "doubler_y": [DBL_Y0, DBL_Y1],
                    "clearance_per_side": CLR,
                    "ribs": {"x": list(RIB_X), "w": RIB_W, "h": RIB_H,
                             "y": [RIB_Y0, RIB_Y1]},
                    "screws": {"pos": SCREW, "size": "M4",
                               "clear_d": D_CLEAR, "cbore": [D_CBORE, L_CBORE],
                               "insert": [D_INSERT, L_INSERT]}}
    out["base_volume"] = float(base.volume)
    out["v4_volume"] = v4v
    json.dump(out, open(os.path.join(LOCAL, "reports", "14_split_build.json"),
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved: reports/14_split_build.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
