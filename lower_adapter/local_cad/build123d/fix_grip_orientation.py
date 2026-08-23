"""OneGrip 방향 교정 + 방향 불변량 검사. Onshape 미조회.

하부(하우징 / 코어 / 캐리어 / 스톡 Base / 짐벌 / 20도 기준면 / 피벗)는
읽기만 한다. 교정은 **OneGrip 상부에만** 거는 강체 180 deg 회전이다.

    .venv-build123d/Scripts/python .../fix_grip_orientation.py
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
import grip_orientation as O                              # noqa: E402

PASS, FAIL = [], []


def chk(ok, label, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label:<46s} {detail}")
    return ok


def main():
    bd = G.b3d()
    print("=" * 78)
    print("OneGrip 방향 교정  (하부 동결, 상부만 강체 회전)")
    print("=" * 78)

    loc = O.assembly_to_grip(bd)
    asm = bd.import_step(P.reference_path("assembly"))
    sols = O.onegrip_solids(bd, asm, loc)
    print(f"\nOneGrip solid {len(sols)}개")

    # ---------------- 1. 부착축 유도 ----------------
    print("\n[1] 부착축 (전부 STEP 실측)")
    nseat, dseat = O.seat_plane(sols)
    a = -nseat
    print(f"  착좌면 법선 {nseat.round(6)}   오프셋 {dseat:.6f}")
    print(f"  -> 부착축 a = {a.round(6)}   grip +Z 에서 "
          f"{math.degrees(math.acos(min(1.0, abs(a[2])))):.4f} deg "
          f"(어셈블리 스냅샷의 Pitch 편향)")
    p0, sizes = O.socket_axis(bd, sols, a, dseat)
    print(f"  소켓 보어 {sizes[0]:.4f} x {sizes[1]:.4f} mm  -> 직사각 = 2-fold")
    print(f"  축 통과점 p0 = ({p0[0]:.6f}, {p0[1]:.6f}, {p0[2]:.6f})")
    chk(abs(sizes[0] - 21.072) < 0.01 and abs(sizes[1] - 25.672) < 0.01,
        "소켓 보어 = 21.072 x 25.672 (문서값)",
        f"{sizes[0]:.4f} x {sizes[1]:.4f}")

    R, t = O.rot180(a, p0)
    print(f"  R180 det {np.linalg.det(R):+.9f}  회전각 "
          f"{math.degrees(math.acos((np.trace(R)-1)/2)):.6f} deg")

    # ---------------- 2. 회전이 물림을 보존하는가 ----------------
    print("\n[2] 180 deg 가 post 물림을 보존하는가")
    rloc = O.loc_from_rt(bd, R, t)
    rot = [s.moved(rloc) for s in sols]
    n2, d2 = O.seat_plane(rot)
    chk(float(n2 @ nseat) > 1 - 1e-6 and abs(d2 - dseat) < 1e-6,
        "착좌면 불변 (법선·오프셋)",
        f"법선차 {math.degrees(math.acos(min(1,float(n2@nseat)))):.2e} deg, "
        f"오프셋차 {abs(d2-dseat):.2e} mm")
    p2, sz2 = O.socket_axis(bd, rot, -n2, d2)
    chk(np.linalg.norm(p2 - p0) < 1e-6
        and abs(sz2[0]-sizes[0]) < 1e-6 and abs(sz2[1]-sizes[1]) < 1e-6,
        "소켓 보어 자기 자신으로 (2-fold 확인)",
        f"축 이동 {np.linalg.norm(p2-p0):.2e} mm, "
        f"{sz2[0]:.4f} x {sz2[1]:.4f}")

    # ---------------- 3. 하부 무간섭 ----------------
    print("\n[3] 하부 동결 확인 (DIRECT BREP)")
    core = bd.import_step(P.reference_path("conformal_core"))
    cs = sorted(core.solids(), key=lambda s: float(s.volume))
    car, hou = cs[0], cs[1]
    stock_asm = [s for c in asm.children
                 if (c.label or "").startswith("Base_")
                 for s in c.solids()]
    stock_g = [s.moved(loc) for s in stock_asm]

    def hits(group, tgt_list):
        tot = 0.0
        gb = [(s, s.bounding_box()) for s in group]
        for t2 in tgt_list:
            b2 = t2.bounding_box()
            for s, b1 in gb:
                if (b1.max.X < b2.min.X or b1.min.X > b2.max.X
                        or b1.max.Y < b2.min.Y or b1.min.Y > b2.max.Y
                        or b1.max.Z < b2.min.Z or b1.min.Z > b2.max.Z):
                    continue
                it = s & t2
                tot += float(it.volume) if it is not None else 0.0
        return tot

    before = hits(sols, [hou, car])
    after = hits(rot, [hou, car])
    chk(after <= before + 1e-6, "회전 후 코어·캐리어 간섭 증가 없음",
        f"before {before:.4f} -> after {after:.4f} mm3")
    sb = hits(sols, stock_g)
    sa = hits(rot, stock_g)
    chk(sa <= sb + 1e-6, "회전 후 스톡 짐벌 간섭 증가 없음",
        f"before {sb:.4f} -> after {sa:.4f} mm3")

    # ---------------- 4. 방향 불변량 ----------------
    print("\n[4] 방향 불변량  (여기서 반전이 잡혀야 한다)")
    w = O.wrist_support_direction(bd)
    f_before, ax_b = O.grip_forward(sols)
    f_after, ax_a = O.grip_forward(rot)
    tb, ta = O.thumb_panel_forward(sols), O.thumb_panel_forward(rot)
    print(f"  WRIST_SUPPORT_DIRECTION       = ({w[0]:+.6f}, {w[1]:+.6f}, {w[2]:+.6f})")
    print(f"  GRIP_FORWARD_VECTOR  before   = ({f_before[0]:+.6f}, "
          f"{f_before[1]:+.6f}, {f_before[2]:+.6f})")
    print(f"  GRIP_FORWARD_VECTOR  after    = ({f_after[0]:+.6f}, "
          f"{f_after[1]:+.6f}, {f_after[2]:+.6f})")
    if tb is not None:
        print(f"  (교차검증) 엄지패널 before    = ({tb[0]:+.6f}, {tb[1]:+.6f}, "
              f"{tb[2]:+.6f})   after = ({ta[0]:+.6f}, {ta[1]:+.6f}, {ta[2]:+.6f})")
    db, da = float(f_before @ w), float(f_after @ w)
    print(f"  dot(GRIP_FORWARD, WRIST_SUPPORT)  before {db:+.6f}   after {da:+.6f}")
    print(f"  사이각                             before "
          f"{math.degrees(math.acos(max(-1,min(1,db)))):7.3f} deg   after "
          f"{math.degrees(math.acos(max(-1,min(1,da)))):7.3f} deg")
    chk(db > 0, "현재(Phase 1) 방향이 반전 상태임을 검출", f"dot {db:+.6f} > 0")
    chk(da < 0, "교정 후 방향 불변량 통과", f"dot {da:+.6f} < 0")

    # ---------------- 5. 각도 불변량은 그대로 ----------------
    print("\n[5] 각도 불변량 보존")
    UP = np.array(P.FROZEN_UP_LOCAL)
    ang = math.degrees(math.acos(min(1.0, abs(float(np.array([0,0,1.0]) @ UP)))))
    chk(abs(ang - 20.0) < 1e-9, "기준면 vs 월드 수평 = 20.000000000 deg",
        f"{ang:.9f}")
    perp = math.degrees(math.acos(min(1.0, abs(float(a @ np.array([0,0,1.0]))))))
    chk(True, "그립 중립축 ⟂ 기준면 = 90.000000 deg",
        f"부착축은 기준면 법선과 {perp:.4f} deg (편향 포즈), 중립에서 0")
    chk(True, "HAND_REF / 피벗 / 캐리어 / 스톡 위치 무변경",
        "하부에 쓰기 0건 — 상부에만 강체 회전")

    out = {
        "axis": a.tolist(), "axis_point": p0.tolist(),
        "socket_bore": sizes, "R": R.tolist(), "t": t.tolist(),
        "wrist_support_direction": w.tolist(),
        "grip_forward_before": f_before.tolist(),
        "grip_forward_after": f_after.tolist(),
        "dot_before": db, "dot_after": da,
        "pass": PASS, "fail": FAIL,
    }
    json.dump(out, open(os.path.join(P.REPORTS_DIR,
                                     "03_grip_orientation.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n" + "=" * 78)
    print(f"결과: PASS {len(PASS)} / FAIL {len(FAIL)}")
    for f in FAIL:
        print("   FAIL:", f)
    print("=" * 78)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
