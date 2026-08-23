"""매립형(embedded) 짐벌 패키징 한계 계산 — READ ONLY, CAD WRITE 0건.

    python lower_adapter/scripts/analyze_embedded_gimbal.py

로컬 메시 + 625ZZ 실제 치수만 사용한다. Onshape 접근 없음.
질문 1~10 (사용자 지정) 에 필요한 수치를 전부 생성한다.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
OUT = os.path.join(ROOT, "lower_adapter", "cad_dump")
SHARED = os.path.join(ROOT, "cad_dump")

# ---- 확정 인터페이스 (lower_adapter/docs/00) ----
FLANGE_Z = -67.878507          # 착좌 평면 = 손 높이 기준면
BOSS_Z = -73.878507
AXIS = np.array([0.0, 27.269160])   # 중심축 (plan)
BOSS_HALF = np.array([15.536, 17.836])
SOCKET_TOP = -52.878507

# ---- 625ZZ 실물 ----
BR_OD, BR_ID, BR_W = 16.0, 5.0, 5.0
BR_FIT = 0.15                  # 원본 #bearing_tolerance
YOKE_WALL = 3.0                # 베어링 시트 둘레 살
BOSS_OD = BR_OD + BR_FIT + 2 * YOKE_WALL      # 22.15
H_BOSS = BOSS_OD / 2                           # 축 기준 상하 반경

# ---- 원본 짐벌 실측 (asm_gimbal.json 에서) ----
ORIG_PIVOT_DEPTH = 46.982
ORIG_TOTAL_H = 82.078   # 정정 2026-08-21 (docs/05 §0). 구값 122.47 = 서브어셈블리 transform 오적용
ORIG_FOOTPRINT = (100.0, 143.0)  # 정정 2026-08-21 (docs/05 §0)


def load(n, shared=True):
    d = SHARED if shared else OUT
    return np.asarray(json.load(io.open(os.path.join(d, f"mesh_{n}.json"),
                                        encoding="utf-8"))["tris"], dtype=float)


def head(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def main():
    G = np.vstack([load("INDEX_FINAL_JaD"), load("INDEX_FINAL_JfD"),
                   load("Backplate")]).reshape(-1, 3)
    G = np.unique(np.round(G, 3), axis=0)
    r = np.linalg.norm(G[:, :2] - AXIS, axis=1)
    z = G[:, 2] - FLANGE_Z                      # 착좌면 기준 높이 (+ = 위)

    head("Q1. 그립 자체가 강제하는 반경 (중심축 기준)")
    band = np.abs(z) < 0.02
    rf = r[band].max()
    print(f"  착좌 평면(z=0) 최대 반경 r_f      = {rf:.3f} mm")
    for h in (2.0, 4.0, 6.0, 8.0, 10.0, 14.0, 20.0):
        m = np.abs(z - h) < 0.4
        print(f"  z=+{h:4.1f} mm 에서 본체 최대 반경  = {r[m].max():.3f} mm" if m.any() else
              f"  z=+{h:4.1f} mm  (샘플 없음)")
    below = z < -0.02
    print(f"  착좌면 아래 그립 재료: 최저 {z[below].min():.3f} mm (보스), "
          f"최대 반경 {r[below].max():.3f} mm")

    head("Q2. 베어링 기하가 강제하는 최소 피벗 깊이")
    print(f"  625ZZ  OD {BR_OD} / ID {BR_ID} / W {BR_W},  끼움 여유 {BR_FIT}")
    print(f"  요크 살 {YOKE_WALL} mm  ->  베어링 보스 OD {BOSS_OD:.2f} mm, "
          f"축 기준 상하 {H_BOSS:.3f} mm")
    print()
    print("  베어링 축은 반드시 피벗을 지나므로, 보스는 항상 피벗 ±%.2f mm 를 차지한다." % H_BOSS)
    print("  -> 옆으로 밀어도 '수직' 점유는 줄지 않는다. 줄이는 방법은 두 가지뿐:")
    print("     (a) 베어링을 플랜지 반경 밖(r > r_f)으로 빼서 플랜지 밑을 비운다")
    print("     (b) 착좌면을 경사면보다 아래(well)로 내려 보스를 표면 밑에 숨긴다")

    head("Q3. 피벗 깊이 p vs 베어링 반경 a  (트레이드 커브)")
    print("  조건 A (보스가 플랜지 밑에 있을 때): p >= H_BOSS + a*sin(theta) + 여유")
    print("  조건 B (보스가 플랜지 밖일 때)   : p >= H_BOSS - g + skin      (g = well 깊이)")
    C = 1.5
    print()
    print("   a[mm]  플랜지밑?   p_min(10deg)  p_min(15deg)   비고")
    for a in (22, 26, 30, 34, 38, 42, 46, 50, 54):
        out = []
        for th in (10.0, 15.0):
            s = np.sin(np.radians(th))
            inner_edge = a - H_BOSS
            outside = inner_edge > rf + 0 * s + C          # 보스가 플랜지 밖인가
            if outside:
                p = H_BOSS + C                              # well 없이 표면 밑 (g=0)
            else:
                p = H_BOSS + a * s + C
            out.append((p, outside))
        tag = "밖" if out[0][1] else "밑"
        note = "베어링이 플랜지 반경 밖 -> 깊이 자유" if out[0][1] else ""
        print(f"   {a:4.0f}    {tag}        {out[0][0]:8.2f}      {out[1][0]:8.2f}    {note}")
    print(f"  (r_f = {rf:.2f}, 여유 {C})")

    head("Q4. well(오목부) 치수 — 그립이 실제로 쓸어내는 부피")
    print("  well 은 원통형이어야 한다 (아래가 넓으면 그립을 넣을 수 없다).")
    print()
    print("  theta   p[mm]   well 반경 R   well 깊이 D   (착좌면 기준)")
    rows = []
    for th in (10.0, 15.0):
        for p in (8.0, 11.0, 14.0, 18.0):
            piv = np.array([AXIS[0], AXIS[1], FLANGE_Z - p])
            c, s = np.cos(np.radians(th)), np.sin(np.radians(th))
            best_R, best_D = 0.0, 0.0
            for ax in (0, 1):                      # u 축 / v 축 회전 각각
                R3 = np.eye(3)
                if ax == 0:
                    R3 = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
                else:
                    R3 = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
                for sign in (1, -1):
                    Rr = R3 if sign > 0 else R3.T
                    W = (G - piv) @ Rr.T + piv
                    zz = W[:, 2] - FLANGE_Z
                    rr = np.linalg.norm(W[:, :2] - AXIS, axis=1)
                    m = zz < 0.5                    # 착좌면 부근 이하만
                    if m.any():
                        best_R = max(best_R, rr[m].max())
                        best_D = max(best_D, -zz[m].min())
            rows.append((th, p, best_R, best_D))
            print(f"   {th:4.1f}   {p:5.1f}    {best_R:8.2f}     {best_D:8.2f}")
    print("  (깊이는 보스 6.0 mm 포함. 보스만 들어갈 중앙 포켓은 별도)")

    head("Q5. 이동 질량 추정")
    vol_grip = 107465.0
    print(f"  OneGrip (frozen, 14 solid)      {vol_grip:9.1f} mm3   -> PLA 약 {vol_grip*1.24e-3:5.1f} g")
    cr = load("CRADLE", False)
    a, b, c2 = cr[:, 0], cr[:, 1], cr[:, 2]
    v = np.einsum("ij,ij->i", a, np.cross(b, c2)) / 6.0
    print(f"  V1 CRADLE (참고, 크다)          {v.sum():9.1f} mm3   -> 약 {v.sum()*1.24e-3:5.1f} g")
    hub_plan = (2 * BOSS_HALF + 2 * 5.0)
    hub_t = 6.2 + 3.5
    hub_v = hub_plan[0] * hub_plan[1] * hub_t * 0.75
    print(f"  축소 HUB 안 ({hub_plan[0]:.1f} x {hub_plan[1]:.1f} x {hub_t:.1f}, 75%%충전) "
          f"{hub_v:9.1f} mm3   -> 약 {hub_v*1.24e-3:5.1f} g")
    for a_ring in (26, 34, 46):
        per = 2 * np.pi * a_ring
        sec = 10.0 * BOSS_OD
        rv = per * sec * 0.55
        print(f"  외측 링 a={a_ring:2d}mm (10 x {BOSS_OD:.1f} 단면, 55%%) "
              f"{rv:9.1f} mm3   -> 약 {rv*1.24e-3:5.1f} g")
    print(f"  베어링 4개 (스틸 625ZZ 약 9 g/개)             -> 약  36.0 g  (고정 2 / 이동 2)")

    head("Q6. 높이 비교")
    print(f"  [원본 DIY] 착좌면 -> 베이스 바닥        {ORIG_TOTAL_H:7.2f} mm   "
          f"피벗 깊이 {ORIG_PIVOT_DEPTH:.2f} mm   풋프린트 {ORIG_FOOTPRINT[0]:.0f} x {ORIG_FOOTPRINT[1]:.0f}")
    print(f"  [A 적층]  V1 웨지 위 착좌면            {33.900:7.2f} mm (지면 기준)")
    print(f"            + 원본형 짐벌을 웨지 밑에 : 짐벌 상면->바닥 {ORIG_TOTAL_H - ORIG_PIVOT_DEPTH + ORIG_PIVOT_DEPTH:.1f} 중"
          f" 상면->피벗 31.60 / 피벗->바닥 {ORIG_TOTAL_H-46.982-15.383:.2f}")
    stackA = 33.900 + 31.60 + (ORIG_TOTAL_H - 46.982 - 15.383)
    print(f"            => 지면 -> 착좌면 총 약 {stackA:7.2f} mm")
    for p in (8.0, 11.0, 14.0):
        print(f"  [B 매립]  피벗 깊이 {p:4.1f} -> 착좌면 아래 기구 {p + H_BOSS + 3.0:5.1f} mm, "
              f"지면->착좌면 약 {p + H_BOSS + 3.0 + 3.0:5.1f} mm (하우징 바닥살 3)")
    print()
    print("  * B 는 well 로 착좌면을 경사면보다 아래로 내릴 수 있어")
    print("    '경사면 기준 손 높이' 는 0 또는 음수까지 내려간다.")


if __name__ == "__main__":
    main()
