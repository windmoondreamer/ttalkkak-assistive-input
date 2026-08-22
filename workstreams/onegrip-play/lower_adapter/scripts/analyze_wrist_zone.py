"""손목 받침 외피 설계를 위한 사전 실측 (CAD WRITE 없음).

현재 코어(CONFORMAL_STOCK_EMBED_V1)를 그대로 두고,
- 그립(손이 잡는 부분)이 월드에서 어디에 있는지
- 현재 상부 외피면이 그 아래 얼마나 떨어져 있는지
- 손목이 놓일 -Y 구간에 무엇이 있는지 (전장 꼬리 / 스커트)
- 조작 영역(±10도 그립 스윕) keep-out
를 잰다.
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

import stock_geom as sg                                  # noqa: E402

OUT = sg.OUT
C = json.load(io.open(os.path.join(OUT, "cartridge_constants.json"), encoding="utf-8"))
K = json.load(io.open(os.path.join(OUT, "conformal_constants.json"), encoding="utf-8"))
UP = np.array(C["UP_LOCAL"])
HAND = np.array(C["HAND_REF"])
DECK_Z = C["DECK_Z"]
GROUND = K["GROUND"]

GRIP = ("Joystick_1 <1>", "Joystick_2 <1>", "Backplate <1>",
        "Small_joystick_attachment <1>")


def uhat():
    y = np.array([0.0, 1.0, 0.0])
    u = y - (y @ UP) * UP
    return u / np.linalg.norm(u)


def main():
    N = sg.load(neutral=True)
    U = uhat()                      # 월드 수평, grip +Y 쪽
    G = np.concatenate([N[k].reshape(-1, 3) for k in GRIP])
    gu, gw = G @ U, G @ UP
    hu, hw = float(HAND @ U), float(HAND @ UP)

    print("=" * 84)
    print("1. 월드 프레임 좌표계")
    print("=" * 84)
    print(f"  UP_LOCAL = {np.round(UP, 6).tolist()}   (월드 수직, grip 좌표)")
    print(f"  u_hat    = {np.round(U, 6).tolist()}   (월드 수평, grip +Y 쪽)")
    print(f"  HAND_REF world = (u {hu:.2f}, h {hw:.2f})   grip={np.round(HAND, 3).tolist()}")
    print(f"  지면 world h   = {GROUND:.4f}")
    print(f"  경사 외피(덱) 평면: grip Z = {DECK_Z:.4f}  -> world h = "
          f"{0.342020 * 0:.0f} + ...")

    print("\n" + "=" * 84)
    print("2. 그립 실루엣 (월드 측면, u = -Y쪽이 음수)")
    print("=" * 84)
    print(f"  그립 u 범위  {gu.min():8.2f} .. {gu.max():8.2f}   (폭 {gu.max()-gu.min():.1f})")
    print(f"  그립 h 범위  {gw.min():8.2f} .. {gw.max():8.2f}")
    print(f"\n  {'u':>8s} {'그립 하단 h':>12s} {'그립 상단 h':>12s} {'덱 평면 h':>11s} "
          f"{'그립하단-덱':>12s}")
    rows = []
    for u0 in np.arange(-90, 61, 5.0):
        m = np.abs(gu - u0) < 2.5
        if m.sum() < 5:
            continue
        lo, hi = float(gw[m].min()), float(gw[m].max())
        # 덱 평면(그립 Z=DECK_Z) 의 world h: 그 평면 위 점 (0, y, DECK_Z)
        # u0 = y*U[1] + DECK_Z*U[2]  ->  y = (u0 - DECK_Z*U[2]) / U[1]
        y = (u0 - DECK_Z * U[2]) / U[1]
        dh = y * UP[1] + DECK_Z * UP[2]
        rows.append((u0, lo, hi, dh, lo - dh, y))
        print(f"  {u0:8.1f} {lo:12.2f} {hi:12.2f} {dh:11.2f} {lo - dh:12.2f}")

    print("\n" + "=" * 84)
    print("3. 손이 잡는 구간 / 손목이 나오는 구간")
    print("=" * 84)
    # 손가락 버튼 행 = HAND_REF. 손바닥 힐은 그보다 -u 쪽 아래.
    print(f"  HAND_REF (중지 버튼행 도심)     u {hu:7.2f}  h {hw:7.2f}")
    m = np.abs(gu - hu) < 4.0
    print(f"  같은 u 에서 그립 하단           h {float(gw[m].min()):7.2f}  "
          f"(HAND_REF 아래 {hw - float(gw[m].min()):.2f} mm)")
    # 그립의 -u 최저단 = 손바닥 힐이 빠져나오는 지점
    k = int(np.argmin(gu))
    print(f"  그립 -u 끝점                   u {gu.min():7.2f}  h {gw[k]:7.2f}")
    lowest = int(np.argmin(gw))
    print(f"  그립 최저점                    u {gu[lowest]:7.2f}  h {gw.min():7.2f}")

    print("\n" + "=" * 84)
    print("4. 현재 하우징이 -Y(손목) 쪽에 가진 것")
    print("=" * 84)
    for name, r4, z in (("본체 스커트", K["SKIRT"], K["CAR_TOP"]),
                        ("꼬리 외피", K["TAIL_OUT"], K["TAIL_OUT_Z"][1]),
                        ("꼬리 스커트", K["TAIL_SKIRT"], K["CAR_TOP"])):
        y0 = r4[2]
        u0 = y0 * U[1] + z * U[2]
        print(f"  {name:<12s} grip Y {y0:8.2f} .. {r4[3]:7.2f}   폭 {r4[1]-r4[0]:6.1f}"
              f"   -Y 끝 world u {u0:7.2f}")
    ob = K["outer"]
    top = ob[-1]
    u_top = top["y0"] * U[1] + DECK_Z * U[2]
    print(f"  상부 외피 -Y 끝  grip Y {top['y0']:.2f}  -> world u {u_top:7.2f}  "
          f"h {top['y0'] * UP[1] + DECK_Z * UP[2]:7.2f}")

    print("\n" + "=" * 84)
    print("5. 조작 영역 keep-out (덱 부근 ±10도 그립 스윕)")
    print("=" * 84)
    cav = K["cav"]
    for m2 in cav[-3:]:
        print(f"  Z {m2['z0']:8.2f}..{m2['z1']:8.2f}  X {m2['x0']:6.1f}..{m2['x1']:6.1f}"
              f"  Y {m2['y0']:6.1f}..{m2['y1']:6.1f}   {m2['x1']-m2['x0']:.1f} x "
              f"{m2['y1']-m2['y0']:.1f}")
    print("  -> 외피는 이 영역을 평면상 침범하면 안 된다 (그립이 지나간다)")

    json.dump({"u_hat": U.tolist(), "hand_world": [hu, hw],
               "grip_u": [float(gu.min()), float(gu.max())],
               "grip_h": [float(gw.min()), float(gw.max())],
               "profile": [[float(x) for x in r] for r in rows],
               "ground": GROUND},
              io.open(os.path.join(OUT, "wrist_zone.json"), "w", encoding="utf-8"),
              indent=1)
    print("\n저장: wrist_zone.json")


if __name__ == "__main__":
    main()
