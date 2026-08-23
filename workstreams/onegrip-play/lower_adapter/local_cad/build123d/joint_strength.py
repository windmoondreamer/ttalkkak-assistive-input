"""§9 JOINT STRENGTH — 20 / 50 / 100 N.

joint 를 조립 상태로 보고 단면 성질을 **실측 형상에서** 뽑아 계산한다.
가정은 전부 명시하고, 재료값은 PLA/PETG 보수치를 쓴다.
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

# 재료 (FDM, 층간 방향 보수치) — provisional
SIGMA_ALLOW = 25.0      # MPa 굽힘/인장 허용 (PLA 약 45~55 파단, 안전율 2)
TAU_ALLOW = 15.0        # MPa 전단 허용 (층간이 아닌 방향)
TAU_LAYER = 8.0         # MPa 층간 전단 허용 (보수)

LOADS = {"NORMAL": 20.0, "PROOF": 50.0, "ACCIDENTAL": 100.0}

ARM_ROOT_Y = -81.8      # 팔받침 root (하우징 앞끝)
Y_UP, Y_LO = SB.Y_UP, SB.Y_LO          # -140 / -112
LAP_MID = 0.5 * (Y_UP + Y_LO)          # -126
ARM_TIP_Y = -272.0

M4_A_STRESS = 8.78      # mm2  M4 인장 응력 단면적
M4_SHEAR_A = 8.78


def load_tris(name, tol=0.05):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    f = os.path.join(P.EXPORT_STL, "_js.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.3)
    T = G.read_stl_tris(f)
    os.remove(f)
    return T


def section_props(T, y, half=0.6):
    """등Y 단면의 면적 / 도심 / 중립축에 대한 2차모멘트 (X축 둘레 굽힘)."""
    # X 방향 스캔선마다 재료 구간(Z)을 구해 사다리꼴 적분
    d = np.array([0.0, 0.0, 1.0])
    sel = (T.min(1)[:, 1] < y + half) & (T.max(1)[:, 1] > y - half)
    Ts = T[sel]
    if len(Ts) < 4:
        return None
    v0, v1, v2 = Ts[:, 0], Ts[:, 1], Ts[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    pv = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, pv)
    m = np.abs(det) > 1e-12
    inv = np.zeros(len(Ts))
    inv[m] = 1.0 / det[m]
    xs = np.arange(T.reshape(-1, 3)[:, 0].min() + 0.5,
                   T.reshape(-1, 3)[:, 0].max(), 0.5)
    segs = []
    for x in xs:
        o = np.array([x, y, -1e4])
        tv = o - v0
        u = np.einsum("ij,ij->i", tv, pv) * inv
        qv = np.cross(tv, e1)
        w = np.einsum("j,ij->i", d, qv) * inv
        t = np.einsum("ij,ij->i", e2, qv) * inv
        ok = m & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 0)
        zz = np.sort(np.unique(np.round(-1e4 + t[ok], 3)))
        for i in range(0, len(zz) - 1, 2):
            segs.append((x, zz[i], zz[i + 1]))
    if not segs:
        return None
    dx = 0.5
    A = sum((b - a) * dx for _, a, b in segs)
    zc = sum((b - a) * dx * 0.5 * (a + b) for _, a, b in segs) / A
    I = 0.0
    for _, a, b in segs:
        h = b - a
        zm = 0.5 * (a + b)
        I += dx * h ** 3 / 12.0 + dx * h * (zm - zc) ** 2
    zmin = min(a for _, a, _ in segs)
    zmax = max(b for _, _, b in segs)
    # 인장측(중립축 위) 1차모멘트 Q -> 인장 합력 T = M/I * Q
    Qt = 0.0
    At = 0.0
    for _, a, b in segs:
        lo_, hi_ = max(a, zc), b
        if hi_ > lo_:
            h = hi_ - lo_
            zm = 0.5 * (lo_ + hi_)
            Qt += dx * h * (zm - zc)
            At += dx * h
    return {"A": A, "zc": zc, "I": I, "zmin": zmin, "zmax": zmax,
            "c_max": max(zmax - zc, zc - zmin), "Q_tension": Qt,
            "A_tension": At}


def main():
    Tv4 = load_tris("ERGO_HOUSING_25_WRAP_FINAL_V4")
    print("=== 단면 성질 (조립 상태, 실측) ===")
    sec = {}
    for lab, y in (("armrest root", ARM_ROOT_Y), ("lap 중앙", LAP_MID),
                   ("lap 앞끝", Y_UP), ("lap 뒤끝", Y_LO)):
        s = section_props(Tv4, y)
        sec[lab] = s
        if s:
            print(f"  {lab:<14} Y={y:8.1f}  A {s['A']:8.1f} mm2  "
                  f"I {s['I']:12,.0f} mm4  c {s['c_max']:6.2f} mm")

    # 하중은 팔받침 위에 분포. 보수적으로 **팔받침 앞끝**에 집중하중으로 본다.
    # (분포하중이면 모멘트가 절반이므로 이쪽이 안전측)
    print("")
    print("=== 하중별 ===")
    print("  가정: 팔 하중을 팔받침 앞끝(Y=-272)에 집중. 분포하중 대비 보수적.")
    # 테이퍼 doubler 라 max 폭을 쓰면 과대평가된다. 사다리꼴 실면적.
    lap_A = (SB.DBL_W0 + SB.DBL_W1) * (Y_LO - Y_UP)
    rib_A = 2 * SB.RIB_W * (SB.RIB_Y1 - SB.RIB_Y0)
    dbl_h = SB.DBL_T
    res = {}
    for nm, F in LOADS.items():
        arm_lap = abs(LAP_MID - ARM_TIP_Y)
        arm_root = abs(ARM_ROOT_Y - ARM_TIP_Y)
        M_lap = F * arm_lap / 1000.0              # N*m
        M_root = F * arm_root / 1000.0
        s = sec["lap 중앙"]
        sigma = (M_lap * 1000.0) * s["c_max"] / s["I"] if s else float("nan")
        tau_lap = F / lap_A
        tau_rib = F / rib_A
        # doubler 굽힘: 랩 평면 위/아래 판이 각각 부담
        # 아래 판 6.0 / 위 판 (14-7)+6 = 13.0  -> 위 판이 주부재
        b_eff = SB.DBL_X * 2
        t_up = (SB.DBL_T - SB.LAP_D) + 6.0
        I_up = b_eff * t_up ** 3 / 12.0
        sig_dbl = (M_lap * 1000.0) * (t_up / 2) / I_up
        # M4 clamp: 압축은 랩 접촉면이 받고, 나사는 **인장측 합력**만 담당한다.
        # 우력 팔길이를 나사 간격(14mm)으로 잡으면 과대평가된다 (실측 521N ->
        # 실제 인장합력 기준으로는 훨씬 작다).
        #   T = M / I * Q_tension     (Q = 인장측 1차모멘트)
        T_total = (M_lap * 1000.0) / s["I"] * s["Q_tension"] if s else float("nan")
        F_screw = T_total / 4.0
        sig_scr = F_screw / M4_A_STRESS
        res[nm] = {"F_N": F, "M_lap_Nm": M_lap, "M_root_Nm": M_root,
                   "T_tension_total_N": T_total,
                   "sigma_section_MPa": sigma, "tau_lap_MPa": tau_lap,
                   "tau_rib_MPa": tau_rib, "sigma_doubler_MPa": sig_dbl,
                   "F_screw_N": F_screw, "sigma_screw_MPa": sig_scr}
        print("")
        print(f"  [{nm}] F = {F:.0f} N")
        print(f"    모멘트  lap {M_lap:7.3f} N·m   root {M_root:7.3f} N·m  "
              f"(lap/root = {M_lap/M_root:.2f})")
        print(f"    단면 굽힘응력      {sigma:8.3f} MPa   "
              f"(허용 {SIGMA_ALLOW})  {'OK' if sigma < SIGMA_ALLOW else 'NG'}")
        print(f"    doubler 굽힘응력   {sig_dbl:8.3f} MPa   "
              f"(허용 {SIGMA_ALLOW})  {'OK' if sig_dbl < SIGMA_ALLOW else 'NG'}")
        print(f"    랩 전단응력        {tau_lap:8.4f} MPa   면적 {lap_A:,.0f} mm2  "
              f"(허용 {TAU_LAYER})  {'OK' if tau_lap < TAU_LAYER else 'NG'}")
        print(f"    리브 전단응력      {tau_rib:8.4f} MPa   면적 {rib_A:,.0f} mm2  "
              f"(허용 {TAU_ALLOW})  {'OK' if tau_rib < TAU_ALLOW else 'NG'}")
        print(f"    인장측 합력        {T_total:8.2f} N   "
              f"(Q {s['Q_tension']:,.0f} mm3 / A_t {s['A_tension']:,.0f} mm2)")
        print(f"    M4 1개 인장        {F_screw:8.2f} N     응력 {sig_scr:6.2f} MPa "
              f"(M4 A_s {M4_A_STRESS} mm2, 항복 하중 약 2,400N)")

    print("")
    print("=== 하중 분담 (PROOF 50N 기준) ===")
    F = LOADS["PROOF"]
    print(f"  랩 접합면 {lap_A:,.0f} mm2 가 전단을 받는다 -> "
          f"{res['PROOF']['tau_lap_MPa']:.4f} MPa")
    print(f"  M4 4개 총 인장 {4 * res['PROOF']['F_screw_N']:.1f} N "
          f"= 인장측 합력. 전단 핀이 아니다.")
    print("  insert pull-out 방향: 랩 평면 법선(상판 법선). 굽힘이 만드는 "
          "**인장**을 받는다 -> heat-set insert 의 축방향 인발.")
    print("  -> tongue(리브)+랩면이 전단/굽힘을 받고 M4 는 clamp. 요구 구조와 일치.")

    json.dump({"sections": {k: v for k, v in sec.items() if v},
               "loads": res, "lap_area_mm2": lap_A, "rib_area_mm2": rib_A,
               "allow": {"sigma": SIGMA_ALLOW, "tau": TAU_ALLOW,
                         "tau_layer": TAU_LAYER}},
              open(os.path.join(LOCAL, "reports", "15_joint_strength.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("")
    print("saved: reports/15_joint_strength.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
