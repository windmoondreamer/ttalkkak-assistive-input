"""§8 JOINT_FIT_COUPON — insert pilot 5종 + joint clearance 5종.

--- 대형 파트의 layer orientation 을 재현한다 ---------------------------------
대형 파트는 CUT FACE DOWN 이다. 그 결과 print 좌표에서:
  * joint 랩 평면        -> **수직면** (적층면과 나란하지 않고 직교)
  * heat-set insert 축   -> grip +Z 가 print -Y 로 가므로 **수평**
  * 리브(tongue)         -> 길이 방향이 grip Y = print Z 라 **수직으로 길고**,
                            돌출 방향은 print -Y 라 **수평으로 튀어나온다**
쿠폰도 같은 관계로 만든다: insert 축 수평, tongue 는 수직으로 길고 수평 돌출.

대형 MAIN/ARMREST 치수는 이 쿠폰 실물 결과 전에는 변경하지 않는다.
"""
from __future__ import annotations
import os
import sys

import build123d as bd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parameters as P                                    # noqa: E402
from OCP.BRepTools import BRepTools                       # noqa: E402

LOCAL = os.path.dirname(HERE)

PILOT = [5.2, 5.3, 5.4, 5.5, 5.6]        # heat-set insert 하부 구멍 지름
CLR = [0.20, 0.25, 0.275, 0.30, 0.35]    # joint clearance per side

INSERT_L = 8.0        # 대형 파트와 동일
CELL = 13.0           # 열 간 피치
WALL_T = 12.0         # insert 블록 두께 (축 방향)
H = 16.0              # 쿠폰 높이 (적층 방향)

TONGUE_W = 5.0        # 대형 리브 폭과 동일
TONGUE_H = 2.5        # 대형 리브 돌출 높이와 동일
TONGUE_L = 10.0       # 수직 길이
BASE_T = 6.0          # 원본 상판 두께와 동일


def main():
    n = len(PILOT)
    w = n * CELL
    # ---- A열: insert pilot (축 수평 +Y) ---------------------------------
    a = bd.Box(w, WALL_T, H).locate(bd.Location((0, 0, H / 2)))
    for i, d in enumerate(PILOT):
        x = -w / 2 + CELL / 2 + i * CELL
        c = bd.Cylinder(d / 2, INSERT_L + 1.0).locate(
            bd.Location((x, WALL_T / 2 + 0.5, H / 2), (90, 0, 0)))
        a = a - c
        # 식별 노치: (지름-5.1)*10 개
        k = int(round((d - 5.1) * 10))
        for j in range(k):
            a = a - bd.Box(0.8, 2.5, 1.2).locate(
                bd.Location((x - 3.2 + j * 1.6, -WALL_T / 2 + 1.25, H - 0.6)))

    # ---- B열: tongue / groove (수직으로 길고 수평 돌출) ------------------
    yb = WALL_T / 2 + 10.0
    b = bd.Box(w, BASE_T, H).locate(bd.Location((0, yb + BASE_T / 2, H / 2)))
    for i, c in enumerate(CLR):
        x = -w / 2 + CELL / 2 + i * CELL
        # tongue: -Y 로 돌출, Z 로 길다
        t = bd.Box(TONGUE_W, TONGUE_H, TONGUE_L).locate(
            bd.Location((x, yb - TONGUE_H / 2, H / 2)))
        b = b + t
        # groove: 같은 열 위쪽에 clearance 만큼 큰 홈 (짝 맞대기용)
        g = bd.Box(TONGUE_W + 2 * c, TONGUE_H + c, TONGUE_L + 2 * c).locate(
            bd.Location((x, yb + BASE_T - (TONGUE_H + c) / 2, H / 2 + TONGUE_L + 3.0)))
        b = b - g
        k = i + 1
        for j in range(k):
            b = b - bd.Box(0.8, 2.5, 1.2).locate(
                bd.Location((x - 3.2 + j * 1.6, yb + BASE_T - 1.25, H - 0.6)))

    # ---- 두 열을 얇은 브리지로 이어 1 solid 로 --------------------------
    br = bd.Box(w * 0.55, (yb - WALL_T / 2) + 0.2, 3.0).locate(
        bd.Location((0, WALL_T / 2 + (yb - WALL_T / 2) / 2, 1.5)))
    cp = a + b + br

    sol = cp.solids()
    print(f"[COUPON] solids {len(sol)}  shells {len(cp.shells())}  "
          f"vol {float(cp.volume):,.1f} mm3")
    if len(sol) != 1:
        print(f"  [경고] solid {len(sol)}개 - 브리지 확인 필요")
    bb = cp.bounding_box()
    mx = max(float(bb.size.X), float(bb.size.Y), float(bb.size.Z))
    print(f"  bbox {float(bb.size.X):.2f} x {float(bb.size.Y):.2f} x "
          f"{float(bb.size.Z):.2f} mm   최대 {mx:.1f}")
    print(f"  [{'PASS' if mx <= 80.0 else 'FAIL'}] 50~80mm 이내")
    print(f"  insert pilot  {PILOT}  (축 **수평**, 깊이 {INSERT_L}mm, 노치 개수 = (d-5.1)x10)")
    print(f"  clearance     {CLR}  per side  (노치 개수 = 순번)")
    BRepTools.Clean_s(cp.wrapped)
    bd.export_stl(cp, os.path.join(P.EXPORT_STL, "JOINT_FIT_COUPON.stl"),
                  tolerance=0.020, angular_tolerance=0.1)
    bd.export_step(cp, os.path.join(P.EXPORT_STEP, "JOINT_FIT_COUPON.step"))
    print("  저장 JOINT_FIT_COUPON.stl / .step")
    return 0


if __name__ == "__main__":
    sys.exit(main())
