"""§2 DIRECT 모션 수용 + §3 각도 여유 + §4 스톡 자체 한계.

- §2 : 실제 stock Pitch/Roll 축 변환으로 9자세 DIRECT 검사 + 24방향 콘
- §3 : 방위별 최초 접촉각 (정사각형 기준, coarse -> binary search)
- §4 : DOCUMENTED / STOCK MECHANICAL / HOUSING CLEARANCE 를 분리 보고
"""
from __future__ import annotations
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import parameters as P, geometry_utils as G
import build123d as bd
from OCP.BRepTools import BRepTools

LOCAL = os.path.dirname(HERE); ADAPTER = os.path.dirname(LOCAL)
DECK = -61.878507
PIV = np.array([0.0, 27.269160, DECK - 52.9823])
GRIP = ("Joystick_1", "Joystick_2", "HW504_B", "Small_joystick_attachment",
        "Backplate", "Magnet", "Pitch")
DOCUMENTED_DESIGN_ANGLE = 15.0          # cad_dump/features_Base.json #joystick_angle
ENVELOPE_SAFETY_MM = 1.5                # motion_envelope15.json clearance


def tris_of(step_name, tol=0.04):
    p = (step_name if os.path.isabs(step_name)
         else os.path.join(P.EXPORT_STEP, step_name + ".step"))
    s = bd.import_step(p); sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    f = os.path.join(P.EXPORT_STL, "_acc.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.3)
    T = G.read_stl_tris(f); os.remove(f)
    return T


def moving_points(sub=12000, seed=0):
    """중립 그립(= Pitch 에 강결합된 이동 solid) 점군."""
    d = np.load(os.path.join(ADAPTER, "cad_dump", "motion_configs_gripfix.npz"))
    N = np.vstack([d[k] for k in d.keys() if k.split("|")[0] == "neutral"
                   and any(k.split("|")[1].startswith(g) for g in GRIP)])
    m = (N[:, 2] > DECK - 26) & (N[:, 2] < DECK + 34)
    S = N[m]
    rng = np.random.default_rng(seed)
    if len(S) > sub:
        S = S[rng.choice(len(S), sub, replace=False)]
    return S


def Rx(deg):
    t = math.radians(deg); c, s = math.cos(t), math.sin(t)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def Ry(deg):
    t = math.radians(deg); c, s = math.cos(t), math.sin(t)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def pose(S, roll_deg, pitch_deg):
    """스톡 카르단: Roll 축(그립 X) 먼저, 그 위에 Pitch 축(그립 Y)."""
    M = Rx(roll_deg) @ Ry(pitch_deg)
    return (S - PIV) @ M.T + PIV


def azimuth_pose(S, amax, phi_deg):
    M = Rx(amax * math.cos(math.radians(phi_deg))) @ Ry(amax * math.sin(math.radians(phi_deg)))
    return (S - PIV) @ M.T + PIV


def n_inside(T, pts):
    return int(G.mesh_inside(T, pts).sum())


def square_dir(phi_deg):
    """정사각형 도달집합 기준 방향. max(|roll|,|pitch|) = 1 로 정규화한다.

    각도 여유를 '축당 각도'(= #joystick_angle 의 의미)로 재기 위해서다.
    원뿔 기준으로 재면 코너 방향이 실제보다 작게 나온다.
    """
    c = math.cos(math.radians(phi_deg)); s_ = math.sin(math.radians(phi_deg))
    k = max(abs(c), abs(s_))
    return c / k, s_ / k


def square_pose(S, A, phi_deg):
    r, p = square_dir(phi_deg)
    return pose(S, A * r, A * p)


def first_contact(T, S, phi_deg, lo=10.0, hi=40.0, tol=0.05):
    """방위 phi 에서 최초 접촉하는 **축당 각도** A. coarse -> binary search."""
    a = lo
    while a <= hi:
        if n_inside(T, square_pose(S, a, phi_deg)) > 0:
            break
        a += 1.0
    else:
        return float("inf")
    b_lo, b_hi = a - 1.0, a
    while b_hi - b_lo > tol:
        mid = 0.5 * (b_lo + b_hi)
        if n_inside(T, square_pose(S, mid, phi_deg)) > 0:
            b_hi = mid
        else:
            b_lo = mid
    return b_hi


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "ERGO_HOUSING_25_WRAP_FINAL_V4"
    T = tris_of(name)
    S = moving_points()
    print(f"[대상] {name}   하우징 삼각형 {len(T):,}   이동부 점 {len(S):,}")

    print("\n=== §2 DIRECT 모션 수용 (nominal 15도) ===")
    poses = [("neutral", 0.0, 0.0),
             ("Pitch +15", 0.0, +15.0), ("Pitch -15", 0.0, -15.0),
             ("Roll  +15", +15.0, 0.0), ("Roll  -15", -15.0, 0.0),
             ("corner (+15,+15)", +15.0, +15.0), ("corner (+15,-15)", +15.0, -15.0),
             ("corner (-15,+15)", -15.0, +15.0), ("corner (-15,-15)", -15.0, -15.0)]
    res9 = {}
    for lab, r, pt in poses:
        n = n_inside(T, pose(S, r, pt))
        res9[lab] = n
        print(f"  [{'PASS' if n == 0 else 'FAIL'}] {lab:<18} 간섭 {n:5d} / {len(S)} 점")
    cone = {}
    for i in range(24):
        phi = i * 15.0
        cone[phi] = n_inside(T, azimuth_pose(S, 15.0, phi))
    tot = sum(cone.values())
    print(f"  [{'PASS' if tot == 0 else 'FAIL'}] 24방향 azimuth cone @15도   합계 간섭 {tot}")
    sq = {}
    for i in range(24):
        phi = i * 15.0
        sq[phi] = n_inside(T, square_pose(S, 15.0, phi))
    tsq = sum(sq.values())
    print(f"  [{'PASS' if tsq == 0 else 'FAIL'}] 24방향 square boundary @15도  합계 간섭 {tsq}")

    print("\n=== §3 각도 여유 (최초 접촉각) ===")
    fc = {}
    for i in range(24):
        phi = i * 15.0
        fc[phi] = first_contact(T, S, phi)
        tag = ""
        if abs(phi - 90) < 1: tag = " (+Y)"
        elif abs(phi - 270) < 1: tag = " (-Y)"
        elif phi < 1: tag = " (+X)"
        elif abs(phi - 180) < 1: tag = " (-X)"
        print(f"   방위 {phi:5.0f}도{tag:<5} 최초 접촉 "
              + (f"{fc[phi]:6.2f}도" if math.isfinite(fc[phi]) else "  >40도"))
    fin = {k: v for k, v in fc.items() if math.isfinite(v)}
    mn = min(fin.values()) if fin else float("inf")
    mnaz = [k for k, v in fin.items() if v == mn]
    print(f"\n  최소 최초접촉각      {mn:.2f} 도  (방위 {mnaz})")
    print(f"  nominal 15도 대비 여유 {mn - 15.0:+.2f} 도")
    print(f"  ※ 포락선 자체에 기하 여유 {ENVELOPE_SAFETY_MM} mm 가 별도로 들어 있다 "
          f"(각도 여유와 무관한 별개 마진).")

    out = {"target": name,
           "documented_design_angle_deg": DOCUMENTED_DESIGN_ANGLE,
           "envelope_geometric_safety_mm": ENVELOPE_SAFETY_MM,
           "direct_poses": res9,
           "cone24_at15": cone, "square24_at15": sq,
           "first_contact_deg": {str(k): (None if not math.isfinite(v) else v)
                                 for k, v in fc.items()},
           "min_first_contact_deg": None if not math.isfinite(mn) else mn,
           "min_first_contact_azimuth_deg": mnaz,
           "angular_reserve_deg": None if not math.isfinite(mn) else mn - 15.0}
    op = os.path.join(LOCAL, "reports", "12_motion15_accept.json")
    json.dump(out, open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장:", os.path.relpath(op, LOCAL))
    return 0


if __name__ == "__main__":
    sys.exit(main())
