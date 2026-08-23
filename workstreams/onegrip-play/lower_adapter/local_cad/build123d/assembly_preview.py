"""조립 프리뷰 STEP (§22) — 부품을 **분리 유지**한 채 한 파일로.

    Ergo Housing / Bottom Carrier / Stock Gimbal / OneGrip

fuse 하지 않는다. 제조용 단일 solid 가 아니라 시각 확인용이다.
Onshape 미조회.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402
import grip_orientation as O                              # noqa: E402


def assembly_to_grip(bd):
    """01_reference_alignment.json 의 변환을 build123d Location 으로."""
    p = os.path.join(P.REPORTS_DIR, "01_reference_alignment.json")
    if not os.path.exists(p):
        raise SystemExit("먼저 align_reference.py 를 실행할 것")
    A = json.load(open(p, encoding="utf-8"))
    R = np.array(A["T_assembly_to_grip"]["R"])
    t = np.array(A["T_assembly_to_grip"]["t"])
    return bd.Location(bd.Plane(origin=tuple(t), x_dir=tuple(R[:, 0]),
                                z_dir=tuple(R[:, 2])))


def main():
    bd = G.b3d()
    req, _ = P.missing_references()
    if req:
        print("STOP - 레퍼런스 없음:", req)
        return 2

    base = sys.argv[1] if len(sys.argv) > 1 else "ERGO_HOUSING_W2"
    step = os.path.join(P.EXPORT_STEP, base + ".step")
    if not os.path.exists(step):
        print("먼저 ergo_shell.py 를 실행할 것")
        return 2

    print("=" * 78)
    print("조립 프리뷰 (부품 분리 유지)")
    print("=" * 78)

    ergo = bd.import_step(step)
    core = bd.import_step(P.reference_path("conformal_core"))
    sol = sorted(core.solids(), key=lambda s: float(s.volume))
    carrier = sol[0]
    # 주의: `Compound.moved(loc)` 의 위치는 `.solids()` 에는 반영되지만
    # `.children` 에는 반영되지 않는다. children 을 그대로 쓰면 프리뷰가
    # 원본 어셈블리 좌표로 나가 하우징과 따로 논다 (실제로 그렇게 나왔다).
    # 그래서 자식마다 명시적으로 옮긴다.
    loc = assembly_to_grip(bd)
    asm = bd.import_step(P.reference_path("assembly"))

    # 어셈블리에서 스톡 / 그립 을 분리
    # OneGrip 방향 교정: post 축 둘레 180 deg (상부에만). 근거는
    # grip_orientation.py / reports/03_grip_orientation.json 참조.
    og = O.onegrip_solids(bd, asm, loc)
    nseat, dseat = O.seat_plane(og)
    axis = -nseat
    p0, bore = O.socket_axis(bd, og, axis, dseat)
    Rf, tf = O.rot180(axis, p0)
    fix = O.loc_from_rt(bd, Rf, tf)
    print(f"  OneGrip 교정: 축 {axis.round(6)} @ ({p0[0]:.4f},{p0[1]:.4f},"
          f"{p0[2]:.4f})  보어 {bore[0]:.4f} x {bore[1]:.4f}")

    parts = []
    for ch in asm.children:
        lab = (ch.label or "").strip()
        sl = [s.moved(loc) for s in ch.solids()]
        if lab.startswith("Joystick_"):
            sl = [s.moved(fix) for s in sl]      # 상부만 회전
        moved = bd.Compound(children=sl)
        print(f"  {lab:<28s} solid {len(list(moved.solids()))}"
              f"{'   <- 180deg 교정' if lab.startswith('Joystick_') else ''}")
        parts.append((lab, moved))

    comps = []

    def add(label, shape):
        s = bd.Compound(children=list(shape.solids()))
        s.label = label
        comps.append(s)
        bb = s.bounding_box()
        print(f"  + {label:<24s} solid {len(list(s.solids())):>3d}  "
              f"{bb.size.X:7.2f} x {bb.size.Y:7.2f} x {bb.size.Z:7.2f}")

    add(base, ergo)
    add("BOTTOM_CARRIER", carrier)
    for lab, ch in parts:
        if lab.startswith("Base_"):
            add("STOCK_GIMBAL", ch)
        elif lab.startswith("Joystick_"):
            add("ONEGRIP", ch)
        elif lab.startswith("ARDUINO"):
            add("ELECTRONICS", ch)

    prev = bd.Compound(children=comps)
    pname = ("ONEGRIP_" + base[len("ERGO_HOUSING_"):] + "_PREVIEW"
             if base.startswith("ERGO_HOUSING_") and "FINAL" in base
             else "ONEGRIP_LOCAL_PREVIEW")
    prev.label = pname
    out = os.path.join(P.EXPORT_STEP, pname + ".step")
    try:
        bd.export_step(prev, out)
        print(f"\n저장: {out}  ({os.path.getsize(out)/1048576:.1f} MB)")
    except RuntimeError as e:
        # build123d 0.11.1 은 중첩 Compound export 에 제약이 있다 -> 1단으로
        print(f"  중첩 export 실패 ({e}) -> 1단 평탄화")
        flat = []
        for c in comps:
            for s in c.solids():
                s.label = c.label
                flat.append(s)
        prev = bd.Compound(children=flat)
        prev.label = pname
        bd.export_step(prev, out)
        print(f"\n저장: {out}  ({os.path.getsize(out)/1048576:.1f} MB)  (평탄화)")

    # 개별 STL (프리뷰 렌더용)
    for c in comps:
        if c.label in ("BOTTOM_CARRIER",):
            bd.export_stl(c, os.path.join(P.EXPORT_STL,
                                          "BOTTOM_CARRIER_REFERENCE.stl"))
        elif c.label == "STOCK_GIMBAL":
            bd.export_stl(c, os.path.join(P.EXPORT_STL, "STOCK_GIMBAL_IN_GRIP.stl"))
        elif c.label == "ONEGRIP":
            bd.export_stl(c, os.path.join(P.EXPORT_STL, "ONEGRIP_IN_GRIP.stl"))
    # 캐리어 STEP 도 별도 출력 (§20)
    bd.export_step(carrier, os.path.join(P.EXPORT_STEP,
                                         "BOTTOM_CARRIER_REFERENCE.step"))
    print("저장: export/step/BOTTOM_CARRIER_REFERENCE.step + 개별 STL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
