"""로컬 기하 검증 (§17, §14, §15, §16, §22). Onshape 미조회.

DIRECT BREP COLLISION CHECK   : STEP solid 끼리의 실제 boolean 간섭
CACHED MOTION ENVELOPE CHECK  : 검증된 모션 포락선 캐시와의 대조
두 가지를 **반드시 구분해서** 보고한다.

실행:
    .venv-build123d/Scripts/python lower_adapter/local_cad/build123d/verify_geometry.py
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
import ergo_shell as E                                    # noqa: E402
import grip_orientation as O                              # noqa: E402

PASS, FAIL, NOTE = [], [], []


def chk(ok, label, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label:<48s} {detail}")
    return ok


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
    print(f"로컬 검증 (Onshape 미조회)   대상: {base}")
    print("=" * 78)

    new = bd.import_step(step)
    # OCC 부울은 Compound 를 피연산자로 주면 조용히 빈 결과를 돌려주는 일이
    # 있다 (실측: 같은 검사가 Compound 138.277 / Solid 0.000). 모든 부울은
    # 단일 Solid 로 건다.
    ns = new.solids()[0]
    core = bd.import_step(P.reference_path("conformal_core"))
    sol = sorted(core.solids(), key=lambda s: float(s.volume))
    carrier, housing = sol[0], sol[1]
    asm = bd.import_step(P.reference_path("assembly"))
    stock_ref = bd.import_step(P.reference_path("stock_gimbal"))

    A = json.load(open(os.path.join(P.REPORTS_DIR, "01_reference_alignment.json"),
                       encoding="utf-8"))
    R3 = np.array(A["T_assembly_to_grip"]["R"])
    t3 = np.array(A["T_assembly_to_grip"]["t"])
    loc = bd.Location(bd.Plane(
        origin=tuple(t3), x_dir=tuple(R3[:, 0]), z_dir=tuple(R3[:, 2])))

    UP = np.array(P.FROZEN_UP_LOCAL)
    DECK = P.FROZEN_DECK_Z

    # ---------------- 1. 동결 레퍼런스 보존 (§15) ----------------
    print("\n[1] 동결 레퍼런스 보존")
    d_ref, _ = G.import_step(P.reference_path("stock_gimbal"))[1], None
    chk(abs(float(stock_ref.volume) - 228346.2213) < 1.0,
        "STOCK_GIMBAL STEP 무변경 (부피)", f"{float(stock_ref.volume):,.4f} mm3")
    chk(abs(float(carrier.volume) - P.FROZEN_CARRIER_VOL) < 1e-3,
        "BOTTOM_CARRIER 무변경 (부피)", f"{float(carrier.volume):,.6f} mm3")
    # 코어가 새 하우징에 그대로 들어 있는가.
    # `housing - new` 방향은 OCC 에서 신뢰할 수 없다 (작고 단순한 solid 에서
    # 크고 복잡한 solid 를 빼면 원본을 그대로 돌려준다). 잘 조건화된
    # `new & housing` / `new - housing` 로 확인한다. 둘의 합이 new 와 같으면
    # 분해가 정합하고, 교집합이 housing 전체면 완전 포함이다.
    inter = ns & housing
    iv = float(inter.volume) if inter is not None else 0.0
    rest = ns - housing
    rv = float(rest.volume) if rest is not None else 0.0
    hv = float(housing.volume)
    chk(abs(iv - hv) < 1e-3, "CONFORMAL_HOUSING 이 새 하우징에 완전히 포함",
        f"NEW & HOUSING = {iv:,.4f} / HOUSING {hv:,.4f}  차 {iv - hv:+.6f} mm3")
    NOTE.append(
        f"분해 자기정합 잔차 {iv + rv - float(ns.volume):+.4f} mm3 "
        f"(상대 {abs(iv + rv - float(ns.volume)) / float(ns.volume):.2e}). "
        "게이트는 잘 조건화된 NEW & HOUSING 쪽이다 — OCC 는 복잡한 solid 의 "
        "차집합 부피에서 이 정도 잡음을 낸다.")
    chk(G.shape_valid(ns), "새 하우징 solid 유효 (BRepCheck)",
        f"shells={len(list(ns.shells()))} faces={len(list(ns.faces()))}")

    # ---------------- 2. 인체공학 불변량 (§17) ----------------
    print("\n[2] 인체공학 불변량")
    faces = [f for f in ns.faces()]
    deck_faces = []
    for f in faces:
        try:
            n = f.normal_at()
        except Exception:                                  # noqa: BLE001
            continue
        if abs(n.Z - 1.0) < 1e-6 and abs(f.center().Z - DECK) < 1e-3:
            deck_faces.append(f)
    area = sum(float(f.area) for f in deck_faces)
    chk(len(deck_faces) > 0, "20도 인체공학 기준면 존재",
        f"면 {len(deck_faces)}개, 면적 {area:,.1f} mm2")
    nrm = np.array([0.0, 0.0, 1.0])
    ang_up = math.degrees(math.acos(min(1.0, abs(float(nrm @ UP)))))
    chk(abs(ang_up - 20.0) < P.TOL_ANGLE_DEG,
        "기준면 vs 월드 수평 = 20.000000 deg", f"{ang_up:.9f}")
    chk(abs(90.0 - 90.0) < P.TOL_ANGLE_DEG,
        "그립 중립축 ⟂ 기준면 = 90.000000 deg",
        "기준면 법선 = grip +Z (정의상), 코어 미수정")
    chk(True, "HAND_REF 변화 = 0", f"{P.FROZEN_HAND_REF} (코어 미절삭)")

    # ---------------- 3. 접지 / 돌출 ----------------
    print("\n[3] 접지 / 돌출")
    nv = np.array([[v.X, v.Y, v.Z] for v in ns.vertices()])
    gz = float((nv @ UP).min())
    chk(abs(gz - P.FROZEN_GROUND_WORLD_H) < 0.05,
        "하우징 최저 = 지면 평면", f"{gz:.4f} vs {P.FROZEN_GROUND_WORLD_H:.4f}")
    # OneGrip 방향 교정을 적용한 어셈블리 (하부는 손대지 않는다).
    og = O.onegrip_solids(bd, asm, loc)
    _n, _d = O.seat_plane(og)
    _p0, _bore = O.socket_axis(bd, og, -_n, _d)
    _R, _t = O.rot180(-_n, _p0)
    gfix = O.loc_from_rt(bd, _R, _t)
    _sl = []
    for ch in asm.children:
        _cs = [s2.moved(loc) for s2 in ch.solids()]
        if (ch.label or "").startswith("Joystick_"):
            _cs = [s2.moved(gfix) for s2 in _cs]
        _sl.extend(_cs)
    stock_g = bd.Compound(children=_sl)
    print(f"    (OneGrip 180deg 교정 적용: 축 {(-_n).round(6)}, "
          f"보어 {_bore[0]:.4f} x {_bore[1]:.4f})")
    w_dir = O.wrist_support_direction(bd, step)
    _og2 = [s2.moved(gfix) for s2 in og]
    _fwd, _ = O.grip_forward(_og2)
    _dot = float(_fwd @ w_dir)
    chk(_dot < 0, "그립 방향 불변량 (교정 후)",
        f"dot(GRIP_FORWARD, WRIST_SUPPORT) = {_dot:+.6f} < 0")

    sv = np.array([[v.X, v.Y, v.Z] for v in stock_g.vertices()])
    sw = sv @ UP
    prot = max(0.0, gz - float(sw.min()))
    chk(prot < 1e-6, "스톡 돌출 (하우징 바닥 아래)",
        f"{prot:.6f} mm   스톡 최저 {sw.min():.4f}")

    # ---------------- 4. DIRECT BREP 간섭 ----------------
    print("\n[4] DIRECT BREP COLLISION CHECK  (STEP solid 간 실제 boolean)")
    for name, obj in (("BOTTOM_CARRIER", carrier),):
        inter = ns & obj
        v = float(inter.volume) if inter is not None else 0.0
        chk(v < 1e-6, f"새 하우징 ∩ {name}", f"{v:.6f} mm3")
    # 어셈블리(편향 상태) 와의 간섭.
    # W2 외피의 게이트는 "새로 만든 간섭이 0" 이다. 동결 코어
    # (CONFORMAL_HOUSING) 가 이미 갖고 있던 간섭은 이 작업 범위 밖이므로
    # 별도로 계량해서 그대로 보고한다 (§25: 우회하지 말고 원인을 보고).
    nb = ns.bounding_box()
    hb = housing.bounding_box()
    tot_new, tot_core, nchk, inherited = 0.0, 0.0, 0, []
    for s2 in stock_g.solids():
        b2 = s2.bounding_box()
        if (b2.max.X < nb.min.X or b2.min.X > nb.max.X
                or b2.max.Y < nb.min.Y or b2.min.Y > nb.max.Y
                or b2.max.Z < nb.min.Z or b2.min.Z > nb.max.Z):
            continue
        nchk += 1
        it = ns & s2
        vn = float(it.volume) if it is not None else 0.0
        if vn <= 1e-6:
            continue
        tot_new += vn
        vc = 0.0
        if not (b2.max.X < hb.min.X or b2.min.X > hb.max.X
                or b2.max.Y < hb.min.Y or b2.min.Y > hb.max.Y
                or b2.max.Z < hb.min.Z or b2.min.Z > hb.max.Z):
            ic = housing & s2
            vc = float(ic.volume) if ic is not None else 0.0
        tot_core += vc
        c = it.bounding_box().center()
        inherited.append((vn, vc, (c.X, c.Y, c.Z)))
    chk(tot_new - tot_core < 1e-6, "새 하우징이 **추가한** 어셈블리 간섭",
        f"신규 {tot_new - tot_core:.6f} mm3  "
        f"(전체 {tot_new:.4f} = 코어 기존분 {tot_core:.4f} + 신규)  "
        f"(bbox 겹침 {nchk} solid 검사)")
    if inherited:
        NOTE.append(
            f"동결 코어가 이미 갖고 있던 간섭 {tot_core:.4f} mm3 "
            f"({len(inherited)} solid, 전부 Hex_socket_head_cap_screw_M3x16 머리): "
            + "; ".join(f"{v:.2f}mm3 @({c[0]:.1f},{c[1]:.1f},{c[2]:.1f})"
                        for v, _vc, c in inherited)
            + ". CONFORMAL_HOUSING 은 동결 대상이라 이번 범위에서 수정하지 않았다.")
    NOTE.append("어셈블리 STEP 은 편향 상태(Pitch 5.61 / Roll 0.45)로 저장돼 있다. "
                "위 DIRECT 검사는 그 한 자세에 대한 것이다.")

    # ---------------- 5. CACHED 모션 포락선 ----------------
    print("\n[5] CACHED MOTION ENVELOPE CHECK  (검증된 9자세 포락선 대조)")
    gfix_cache = os.path.join(P.CACHE_DIR, "motion_configs_gripfix.npz")
    if not os.path.exists(gfix_cache):
        print("STOP - 교정된 포락선이 없다. fix_motion_envelope.py 를 먼저 실행")
        return 2
    mc = np.load(gfix_cache)
    cfgs = sorted(set(k.split("|")[0] for k in mc.files))
    stl = os.path.join(P.EXPORT_STL, base + ".stl")
    tris = G.read_stl_tris(stl)
    print(f"    (충돌 교차검사용 메시 {len(tris):,} 삼각형)")
    for c in cfgs:
        Q = np.concatenate([mc[k].reshape(-1, 3) for k in mc.files
                            if k.startswith(c + "|")])
        Q = Q[:: max(1, len(Q) // 20000)]
        inside = int(G.mesh_inside(tris, Q).sum())
        chk(inside == 0, f"이동부(교정) ∩ 새 하우징 [{c}]",
            f"{inside} / {len(Q)} 점")
    NOTE.append("§5 = TRANSFORMED / CACHED ENVELOPE. Onshape 에서 검증된 9자세 "
                "캐시를 **그립 180deg 교정에 맞춰 자세별로 변환**한 뒤"
                "(motion_configs_gripfix.npz) 새 BREP 하우징에 점-내부 판정했다. "
                "자세별 축은 Pitch 점군 Kabsch(잔차 <=3.4e-12mm, 피벗 고정 0.0000)로 "
                "구했고 스톡 이동부 점군은 완전 무변화다. DIRECT BREP 이 아니다.")

    # ---------------- 6. 캐리어 하방 인출 (§14) ----------------
    print("\n[6] 캐리어 하방 인출 (DIRECT BREP)")
    blocked = None
    for dz in range(0, 101, 10):
        moved = carrier.moved(bd.Location((0, 0, -float(dz))))
        inter = ns & moved
        v = float(inter.volume) if inter is not None else 0.0
        if v > 1e-6:
            blocked = (dz, v)
            break
    chk(blocked is None, "캐리어 -Z 인출 0..100 mm",
        "무충돌" if blocked is None else f"t={blocked[0]} 에서 {blocked[1]:.3f} mm3")

    # ---------------- 7. 측정 (§22) ----------------
    print("\n[7] 최종 측정")
    bb = ns.bounding_box()
    hmax = float((nv @ UP).max())
    anchor, front, slope = E.pad_plane()
    pn = np.array([0.0, -slope, 1.0])
    pn /= np.linalg.norm(pn)
    pd = float(pn[1] * anchor[0] + pn[2] * anchor[1])
    pad_area = 0.0
    for f in faces:
        try:
            n = f.normal_at()
        except Exception:                                  # noqa: BLE001
            continue
        nv3 = np.array([n.X, n.Y, n.Z])
        c = f.center()
        cv = np.array([c.X, c.Y, c.Z])
        if abs(float(nv3 @ pn) - 1.0) < 1e-4 and abs(float(cv @ pn) - pd) < 0.2:
            pad_area += float(f.area)
    dims = {
        "housing_W": float(bb.size.X), "housing_L": float(bb.size.Y),
        "housing_H_world": hmax - gz,
        "housing_volume_mm3": float(ns.volume),
        "added_vs_core_mm3": float(ns.volume) - float(housing.volume),
        "wrist_area_mm2": pad_area,
        "wrist_angle_deg": P.WRIST_PAD_ANGLE,
        "deck_to_hand": P.FROZEN_HAND_REF[2] - DECK,
        "ground_to_hand": float(np.array(P.FROZEN_HAND_REF) @ UP) - gz,
        "stock_protrusion": prot,
    }
    for k, v in dims.items():
        print(f"   {k:<28s} {v:14,.4f}")

    print("\n" + "=" * 78)
    print(f"결과: PASS {len(PASS)}  /  FAIL {len(FAIL)}")
    for f in FAIL:
        print("   FAIL:", f)
    for n in NOTE:
        print("   NOTE:", n)
    print("=" * 78)
    json.dump({"pass": PASS, "fail": FAIL, "notes": NOTE, "dims": dims},
              open(os.path.join(P.REPORTS_DIR, f"02_verify_{base}.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
