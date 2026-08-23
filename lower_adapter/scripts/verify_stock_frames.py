"""중립 복원 검증 + 애매한 부품(베어링/마그넷/홀/전장)의 프레임 귀속 판정.

이름으로 단정하지 않고 **기하로 확인**한다.
GET 없음 (캐시만 사용).
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import stock_geom as sg                                    # noqa: E402

OUT = sg.OUT


def bbox(P):
    Q = P.reshape(-1, 3)
    return Q.min(0), Q.max(0)


def main():
    m = sg.meta()
    D = sg.load(neutral=False)             # 편향 상태
    N = sg.load(neutral=True)              # 이름 기반 중립화

    # ---- 1. 중립 검증: Base 최대 평면의 법선 ----
    P = N["Base <1>"]
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    a = np.linalg.norm(n, axis=1)
    n = n / np.maximum(a[:, None], 1e-12)
    # 가장 넓은 방향 클러스터
    down = a[(n[:, 2] < -0.99)].sum()
    nb = (n * a[:, None]).sum(0) / a.sum()
    lo, hi = bbox(P)
    print("[1] 중립 검증")
    print(f"    Base bottom 법선 클러스터 면적  = {down:9.2f} mm^2")
    idx = np.argmax(a)
    print(f"    Base 최대 단일 facet 법선       = {np.round(n[idx], 6).tolist()}")
    print(f"    Base bbox X[{lo[0]:8.3f},{hi[0]:8.3f}] Y[{lo[1]:8.3f},{hi[1]:8.3f}] "
          f"Z[{lo[2]:9.3f},{hi[2]:9.3f}]")
    print(f"    Base 크기 {hi[0]-lo[0]:.3f} x {hi[1]-lo[1]:.3f} x {hi[2]-lo[2]:.3f} mm")
    print(f"    착좌면 -> Base 밑면 = {sg.SEAT_Z - lo[2]:.3f} mm")

    # 밑면 평면 최적합
    zmin = lo[2]
    V = P.reshape(-1, 3)
    sel = V[V[:, 2] < zmin + 0.05]
    print(f"    밑면 정점 {len(sel)}개, Z 범위 {sel[:,2].min():.6f} ~ {sel[:,2].max():.6f}")

    # ---- 2. 이전 감사 결과와 대조 ----
    prev = json.load(io.open(os.path.join(OUT, "stock_neutral.json"), encoding="utf-8"))
    print("\n[2] 이전 감사(stock_neutral.json) 대조")
    keymap = {"Base": "Base <1>", "Roll_holder": "Roll_holder <1>",
              "Roll_holder_2": "Roll_holder_2 <1>", "Spacer": "Spacer <1>",
              "Roll": "Roll <1>", "Pitch": "Pitch <1>",
              "Spring_holder": "Spring_holder <1>"}
    for pk, nk in keymap.items():
        A = np.array(prev["parts"][pk], dtype=float)
        B = N[nk]
        la, ha = bbox(A)
        lb, hb = bbox(B)
        d = max(np.abs(la - lb).max(), np.abs(ha - hb).max())
        print(f"    {pk:<16s} bbox 최대차 {d:8.4f} mm   {'OK' if d < 0.02 else 'DIFF'}")

    # ---- 3. 애매한 부품 귀속 판정 ----
    # 판정법: 편향 상태에서 각 부품 도심이 어느 구조물 안/근처에 있는가.
    print("\n[3] 애매 부품 프레임 귀속 (기하 판정)")
    fixed = np.concatenate([D[k].reshape(-1, 3) for k in
                            ("Base <1>", "Roll_holder <1>", "Roll_holder_2 <1>",
                             "Spacer <1>")])
    moving = np.concatenate([D[k].reshape(-1, 3) for k in
                             ("Pitch <1>", "Joystick_1 <1>", "Joystick_2 <1>")])
    rollp = D["Roll <1>"].reshape(-1, 3)

    def near(Q, S, cap=4000):
        s = S[:: max(1, len(S) // cap)]
        q = Q[:: max(1, len(Q) // 400)]
        return np.sqrt(((q[:, None, :] - s[None, :, :]) ** 2).sum(-1)).min()

    amb = [k for k in D if any(k.startswith(p) for p in
                               ("Inner_racing", "Outer_racing", "Magnet", "Part ",
                                "micro", "atmega", "MICRO_"))]
    rows = []
    for k in sorted(amb):
        Q = D[k].reshape(-1, 3)
        c = Q.mean(0)
        df, dm, dr = near(Q, fixed), near(Q, moving), near(Q, rollp)
        best = min([("BASE", df), ("GRIP", dm), ("ROLL", dr)], key=lambda x: x[1])
        rows.append((k, c, df, dm, dr, best[0]))
        print(f"    {k:<34s} c=({c[0]:7.2f},{c[1]:7.2f},{c[2]:8.2f}) "
              f"dFix={df:6.2f} dGrip={dm:6.2f} dRoll={dr:6.2f} -> {best[0]}")

    json.dump({k: b for k, _, _, _, _, b in rows},
              io.open(os.path.join(OUT, "stock_frame_guess.json"), "w",
                      encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
